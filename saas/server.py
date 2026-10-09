"""graphify app server — multi-tenant web workspace, REST API and MCP endpoint.

One process, one origin, three surfaces:

* ``/``        the web workspace (login-gated in the browser)
* ``/api/*``   JSON read API for your own extension / scripts
* ``/mcp``     MCP Streamable HTTP for agents (Claude Code, Cursor, Codex…)

Every request resolves to a **principal** (session cookie, bearer session token
or ``gf_…`` API key) and to exactly one **workspace**; the graph is then served
from that workspace's ``graph.json`` via :mod:`saas.registry`. Nothing is
readable without one of those credentials.

Graph paths are the tenant-isolation boundary: a workspace may only point inside
``GRAPHIFY_APP_DATA_ROOT`` (default ``saas/data/graphs``) or at the single path
given with ``--bootstrap-graph``. That keeps ``POST /api/workspaces`` from being
used to read arbitrary JSON off the host filesystem.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from saas import theme as themes
from saas.auth import (
    PLANS,
    SESSION_COOKIE,
    ApiKey,
    Auth,
    AuthError,
    LimitExceeded,
    User,
    Workspace,
    auth as get_auth,
    plan_of,
)
from saas.graph_store import GraphStore
from saas.registry import GRAPHS, MCP, fingerprint as graph_fingerprint

STATIC_DIR = Path(__file__).parent / "static"

# Filled by build_app(): False without the mcp extra, so /api/ide-config can say
# the endpoint is unavailable rather than hand an IDE a dead URL.
MCP_AVAILABLE = False

# Set by --demo: enables POST /api/auth/demo (one-click login as the seeded
# account) and advertises it on /api/health so the login page can offer the
# button. Off by default: a production deploy has no demo account to log into.
DEMO_LOGIN = False
_DEMO_CREDS: tuple[str, str] | None = None

# Set by --bootstrap-graph: the one path outside the data root a workspace may
# use, so a local checkout can be served without copying 19 MB around.
_BOOTSTRAP_GRAPH: str | None = None


def data_root() -> Path:
    return Path(
        os.environ.get("GRAPHIFY_APP_DATA_ROOT") or Path("saas") / "data" / "graphs"
    ).resolve()


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": msg}, status_code=status)


def safe_graph_path(candidate: str | Path) -> Path:
    """Resolve a tenant-supplied graph path, refusing anything outside the jail.

    The check is on the *resolved* path, so ``../../etc/passwd`` and symlink
    escapes are both rejected; and it must be a ``.json`` file, because that is
    all the loader accepts anyway.
    """
    path = Path(candidate).expanduser().resolve()
    allowed = [data_root()]
    if _BOOTSTRAP_GRAPH:
        allowed.append(Path(_BOOTSTRAP_GRAPH).resolve().parent)
    for root in allowed:
        try:
            path.relative_to(root)
            break
        except ValueError:
            continue
    else:
        raise AuthError(
            f"graph path must live under {data_root()} (or the bootstrap path)", 400
        )
    if path.suffix != ".json":
        raise AuthError("graph path must be a .json file", 400)
    return path


class AccessLogMiddleware:
    """Log what matters: every auth attempt and every 4xx/5xx.

    uvicorn runs at warning level here, which left a failed browser login
    completely invisible server-side. One line per interesting request keeps
    the log readable and the debugging possible.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        interesting = path.startswith("/api/auth") or path == "/mcp"
        status_box = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_box["s"] = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, send_wrapper)
        status = status_box.get("s", 0)
        if interesting or status >= 400:
            print(f'[http] {scope.get("method")} {path} -> {status}', flush=True)


class RevalidateMiddleware:
    """Force revalidation for assets whose identity changes with each deploy.

    Pure ASGI on purpose: it only touches response headers. Without it a
    reverse proxy or a browser heuristic cache can pin an old app.css while
    index.html moves on, and the page renders half-styled.
    """

    REVALIDATE_PREFIXES = ("/static/",)
    REVALIDATE_EXACT = frozenset({"/", "/login", "/signup", "/app", "/invite", "/theme.css", "/fonts.css"})

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if not (path.startswith(self.REVALIDATE_PREFIXES) or path in self.REVALIDATE_EXACT):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers = [(k, v) for k, v in headers if k.lower() != b"cache-control"]
                headers.append((b"cache-control", b"no-cache, must-revalidate"))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


# --------------------------------------------------------------- principals


@dataclass
class Principal:
    user: User | None
    workspace: Workspace | None
    via: str  # "api_key" | "session" | "none"
    api_key: ApiKey | None = None

    @property
    def store(self) -> GraphStore:
        if self.workspace is None:
            raise AuthError("no workspace selected", 400)
        return GRAPHS.get(safe_graph_path(self.workspace.graph_path))


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.headers.get("x-api-key", "").strip() or None


def principal(request: Request) -> Principal:
    """Resolve credentials → user + workspace. Never raises; callers decide."""
    a: Auth = get_auth()
    token = _bearer(request) or request.cookies.get(SESSION_COOKIE)
    if token is None and request.url.path.startswith("/api/"):
        # Last-resort channel. Embedded previews have been observed stripping
        # the Authorization header at the proxy and blocking third-party
        # cookies in the iframe, which left a freshly-issued token with no way
        # to travel. A query parameter survives both. It is read only under
        # /api/*, never logged (AccessLogMiddleware logs paths without query
        # strings), and the header/cookie remain preferred everywhere else.
        token = request.query_params.get("token") or None
    wanted = request.headers.get("x-workspace") or request.query_params.get("ws")
    if token and token.startswith("gf_"):
        found = a.workspace_from_key(token)
        if not found:
            return Principal(None, None, "none")
        ws, key = found
        # A key is welded to its workspace. If the caller asked for a different
        # one, refuse loudly: silently serving the key's own graph would let a
        # misconfigured client believe it crossed tenants.
        if wanted and wanted not in (ws.id, ws.slug):
            raise AuthError(
                f"api key is scoped to workspace '{ws.slug}'; it cannot act on '{wanted}'",
                403,
            )
        return Principal(None, ws, "api_key", key)

    user = a.user_from_token(token)
    if user is None:
        return Principal(None, None, "none")

    workspaces = a.workspaces_for(user.id)
    if not workspaces:
        return Principal(user, None, "session")
    if wanted:
        ws = next((w for w in workspaces if w.id == wanted or w.slug == wanted), None)
        if ws is None:
            raise AuthError(f"not a member of workspace '{wanted}'", 403)
        return Principal(user, ws, "session")
    return Principal(user, workspaces[0], "session")


# Endpoints that need a signed-in user but not a workspace — otherwise a
# brand-new account could never create its first workspace (403 chicken-and-egg).
_NO_WORKSPACE_NEEDED = frozenset({"/api/auth/me", "/api/workspaces"})


def require(request: Request, *, meter: bool = True) -> Principal:
    p = principal(request)
    if p.via == "none":
        raise AuthError("authentication required", 401)
    if p.workspace is None and request.url.path not in _NO_WORKSPACE_NEEDED:
        raise AuthError("no workspace: create one first", 403)
    if p.workspace is not None:
        # The plan gate sits in one place so no new endpoint can forget it:
        # over quota is a 402 before any work happens, and every served call
        # is counted for the usage page and future invoicing.
        get_auth().check_api_quota(p.workspace)
        if meter:
            get_auth().meter(p.workspace.id, "api")
    return p


def require_role(p: Principal, *roles: str) -> None:
    if p.workspace is None or p.workspace.role not in roles:
        raise AuthError(f"needs role: {' or '.join(roles)}", 403)


def _best_plan(a: Auth, user_id: str) -> str:
    """The plan that gates *creating* things: the best plan among the user's
    workspaces, since a brand-new workspace has no plan of its own yet."""
    best = "free"
    for w in a.workspaces_for(user_id):
        if plan_of(w.plan)["price_month"] > plan_of(best)["price_month"]:
            best = w.plan
    return best


def _check_nodes(store: GraphStore, plan_id: str) -> None:
    cap = plan_of(plan_id)["max_nodes"]
    if len(store.nodes) > cap:
        raise LimitExceeded(
            f"graph has {len(store.nodes):,} nodes; plan '{plan_of(plan_id)['name']}' "
            f"caps at {cap:,}. Upgrade under Billing."
        )


def _ws_json(ws: Workspace, store: GraphStore | None = None) -> dict:
    out = {
        "id": ws.id,
        "slug": ws.slug,
        "name": ws.name,
        "role": ws.role,
        "plan": ws.plan,
        "graph": str(ws.graph_path),
        "graph_ready": ws.graph_exists,
        "created_at": ws.created_at,
    }
    if store is not None:
        out["nodes"] = len(store.nodes)
        out["edges"] = store.G.number_of_edges()
        out["communities"] = len(store.community_members)
    return out


def _guard(fn):
    """Turn AuthError/store failures into JSON responses instead of 500s."""

    async def wrapper(request: Request):
        try:
            return await fn(request)
        except AuthError as e:
            return _err(e.message, e.status)
        except FileNotFoundError as e:
            return _err(str(e), 404)
        except Exception as e:  # keep the API honest, and the stack in the log
            import traceback

            traceback.print_exc()
            return _err(f"{type(e).__name__}: {e}", 500)

    wrapper.__name__ = fn.__name__
    return wrapper


# ------------------------------------------------------------------- public


_ASSET_URL_RE = re.compile(r'((?:src|href)="/static/[^"?]+)"')
_asset_versions: dict[str, tuple[float, str]] = {}


def _asset_version(rel: str) -> str:
    """Content-hash cache-buster for one /static/ file, memoized by mtime."""
    path = STATIC_DIR / rel
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return "0"
    hit = _asset_versions.get(rel)
    if hit is not None and hit[0] == mtime:
        return hit[1]
    version = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
    _asset_versions[rel] = (mtime, version)
    return version


def _page(name: str) -> Response:
    """Render a static page, injecting the default theme and asset versions.

    Pages are re-read per request (they are tiny) so a deploy never serves a
    stale shell, and the shell itself is ``no-cache`` (see
    :class:`RevalidateMiddleware`). Every /static/ reference additionally gets
    ``?v=<content hash>``: users inside a preview iframe cannot hard-reload,
    and heuristic caching once pinned an old app.js/site.js against the new
    HTML — the stale script then authenticated without ``?token=`` and the
    workspace bounced back to /login. Fresh HTML now always pulls fresh JS.
    """
    html = (STATIC_DIR / name).read_text(encoding="utf-8")
    html = _ASSET_URL_RE.sub(
        lambda m: m.group(1)
        + "?v="
        + _asset_version(m.group(1).split("/static/", 1)[1])
        + '"',
        html,
    )
    return HTMLResponse(html.replace("__THEME__", themes.DEFAULT_THEME))


async def landing(request: Request) -> Response:
    return _page("landing.html")


async def auth_page(request: Request) -> Response:
    return _page("auth.html")


async def index(request: Request) -> Response:
    return _page("index.html")


async def theme_css(request: Request) -> Response:
    return Response(themes.theme_css(), media_type="text/css; charset=utf-8")


async def api_theme(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "default": themes.DEFAULT_THEME,
            "themes": [p.as_dict() for p in themes.PALETTES.values()],
        }
    )


async def api_health(request: Request) -> JSONResponse:
    """Liveness probe. Intentionally leaks nothing about tenants."""
    return JSONResponse(
        {
            "ok": True,
            "service": "graphify-app",
            "mcp": MCP_AVAILABLE,
            "demo_login": DEMO_LOGIN,
            "storage_note": None,
            "cached_graphs": len(GRAPHS.snapshot()),
            "time": int(time.time()),
        }
    )


async def api_demo_login(request: Request) -> JSONResponse:
    """One-click login as the seeded demo account. Only exists when the server
    was started with --demo; otherwise 404, so the route is not even a probe
    target in production."""
    if not DEMO_LOGIN or _DEMO_CREDS is None:
        return _err("demo login is not enabled on this deployment", 404)
    a = get_auth()
    try:
        user, token = a.login(_DEMO_CREDS[0], _DEMO_CREDS[1])
    except AuthError as e:
        return _err(e.message, e.status)
    resp = JSONResponse(
        {
            "ok": True,
            "token": token,
            "user": {"id": user.id, "email": user.email, "name": user.name},
            "workspaces": [_ws_json(w) for w in a.workspaces_for(user.id)],
        }
    )
    _set_cookie(resp, token)
    return resp


# --------------------------------------------------------------------- auth


@_guard
async def api_signup(request: Request) -> JSONResponse:
    body = await request.json()
    a = get_auth()
    first_user = a.user_count() == 0
    user, token = a.signup(
        body.get("email", ""), body.get("password", ""), body.get("name", "")
    )
    ws = None
    if first_user and _BOOTSTRAP_GRAPH:
        # The first account inherits the demo graph, so a fresh install has
        # something to look at instead of an empty workspace list.
        ws = a.create_workspace(
            user.id,
            body.get("workspace") or Path(_BOOTSTRAP_GRAPH).resolve().parent.parent.name,
            _BOOTSTRAP_GRAPH,
        )
        GRAPHS.preload(_BOOTSTRAP_GRAPH)
    resp = JSONResponse(
        {
            "ok": True,
            "token": token,
            "user": {"id": user.id, "email": user.email, "name": user.name},
            "workspaces": [_ws_json(w) for w in a.workspaces_for(user.id)],
        }
    )
    _set_cookie(resp, token)
    return resp


@_guard
async def api_login(request: Request) -> JSONResponse:
    body = await request.json()
    a = get_auth()
    user, token = a.login(body.get("email", ""), body.get("password", ""))
    resp = JSONResponse(
        {
            "ok": True,
            "token": token,
            "user": {"id": user.id, "email": user.email, "name": user.name},
            "workspaces": [_ws_json(w) for w in a.workspaces_for(user.id)],
        }
    )
    _set_cookie(resp, token)
    return resp


async def api_logout(request: Request) -> JSONResponse:
    token = _bearer(request) or request.cookies.get(SESSION_COOKIE)
    if token and not token.startswith("gf_"):
        get_auth().logout(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@_guard
async def api_me(request: Request) -> JSONResponse:
    p = principal(request)
    if p.user is None:
        return JSONResponse({"ok": False, "error": "unauthenticated"}, status_code=401)
    a = get_auth()
    workspaces = a.workspaces_for(p.user.id)
    out = {
        "ok": True,
        "user": {"id": p.user.id, "email": p.user.email, "name": p.user.name},
        "workspaces": [_ws_json(w) for w in workspaces],
        "active": p.workspace.id if p.workspace else None,
        "via": p.via,
    }
    if p.workspace is not None:
        out["workspace"] = _ws_json(p.workspace, p.store)
    return JSONResponse(out)


def _set_cookie(resp: Response, token: str) -> None:
    # SameSite=None is required for the workspace to run inside a cross-site
    # iframe (the preview, or an IDE webview); that in turn requires Secure.
    same_site = os.environ.get("GRAPHIFY_COOKIE_SAMESITE", "none").lower()
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=same_site == "none",
        samesite=same_site if same_site in ("lax", "strict", "none") else "lax",
        path="/",
    )


# --------------------------------------------------------------- workspaces


@_guard
async def api_workspaces(request: Request) -> JSONResponse:
    if request.method == "POST":
        p = require(request)
        if p.user is None:
            raise AuthError("api keys cannot create workspaces", 403)
        body = await request.json()
        name = (body.get("name") or "").strip()
        if not name:
            raise AuthError("name is required", 400)
        raw = body.get("graph") or body.get("graph_path")
        if not raw:
            raise AuthError("graph is required (path to graph.json)", 400)
        a = get_auth()
        owned = len(a.workspaces_for(p.user.id))
        cap = plan_of(_best_plan(a, p.user.id))["max_workspaces"]
        if owned >= cap:
            raise LimitExceeded(
                f"plan allows {cap} workspaces and you have {owned}. Upgrade under Billing."
            )
        path = safe_graph_path(raw)
        if not path.exists():
            raise AuthError(
                f"no graph at {path}. Build one with: graphify extract . --code-only", 404
            )
        store = GRAPHS.preload(path)
        _check_nodes(store, _best_plan(a, p.user.id))
        ws = a.create_workspace(p.user.id, name, str(path), body.get("slug"))
        return JSONResponse({"ok": True, "workspace": _ws_json(ws, store)})

    p = require(request)
    if p.user is None:
        raise AuthError("api keys are already scoped to one workspace", 403)
    return JSONResponse(
        {
            "ok": True,
            "workspaces": [
                _ws_json(w, GRAPHS.peek(w.graph_path))
                for w in get_auth().workspaces_for(p.user.id)
            ],
            "active": p.workspace.id if p.workspace else None,
        }
    )


@_guard
async def api_keys(request: Request) -> JSONResponse:
    """List/create API keys for the active workspace (browser sessions only)."""
    p = require(request)
    if p.user is None:
        raise AuthError("api keys cannot manage api keys", 403)
    require_role(p, "owner", "member")
    a = get_auth()
    if request.method == "POST":
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        assert p.workspace is not None
        key, raw = a.create_api_key(p.workspace.id, p.user.id, body.get("name", "default"))
        # The plaintext is returned exactly once; only its digest is stored.
        return JSONResponse(
            {
                "ok": True,
                "key": {"id": key.id, "name": key.name, "prefix": key.prefix, "secret": raw},
                "mcp_url": str(request.base_url).rstrip("/") + "/mcp",
            }
        )
    assert p.workspace is not None
    return JSONResponse(
        {
            "ok": True,
            "keys": [
                {
                    "id": k.id,
                    "name": k.name,
                    "prefix": k.prefix,
                    "created_at": k.created_at,
                    "last_used_at": k.last_used_at,
                    "revoked_at": k.revoked_at,
                }
                for k in a.api_keys(p.workspace.id)
            ],
            "mcp_url": str(request.base_url).rstrip("/") + "/mcp",
        }
    )


@_guard
async def api_key_revoke(request: Request) -> JSONResponse:
    p = require(request)
    if p.user is None:
        raise AuthError("api keys cannot manage api keys", 403)
    require_role(p, "owner", "member")
    assert p.workspace is not None
    ok = get_auth().revoke_api_key(request.path_params["key_id"], p.workspace.id)
    if not ok:
        raise AuthError("unknown or already-revoked key", 404)
    return JSONResponse({"ok": True})


# -------------------------------------------------------------------- graph


@_guard
async def api_stats(request: Request) -> JSONResponse:
    p = require(request)
    return JSONResponse({"ok": True, **p.store.stats()})


@_guard
async def api_god_nodes(request: Request) -> JSONResponse:
    p = require(request)
    limit = int(request.query_params.get("limit", 15))
    return JSONResponse({"ok": True, "nodes": p.store.god_nodes(limit=limit)})


@_guard
async def api_communities(request: Request) -> JSONResponse:
    p = require(request)
    limit = int(request.query_params.get("limit", 24))
    return JSONResponse({"ok": True, "communities": p.store.communities(limit=limit)})


@_guard
async def api_search(request: Request) -> JSONResponse:
    p = require(request)
    q = request.query_params.get("q", "")
    if not q.strip():
        return _err("q is required")
    limit = int(request.query_params.get("limit", 20))
    return JSONResponse({"ok": True, "results": p.store.search(q, limit=limit)})


@_guard
async def api_explain(request: Request) -> JSONResponse:
    p = require(request)
    node = request.query_params.get("node", "")
    if not node.strip():
        return _err("node is required")
    card = p.store.explain(node)
    if card is None:
        return _err(f"no node matches {node!r}", 404)
    return JSONResponse({"ok": True, "node": card})


@_guard
async def api_path(request: Request) -> JSONResponse:
    p = require(request)
    a = request.query_params.get("a", "")
    b = request.query_params.get("b", "")
    if not a.strip() or not b.strip():
        return _err("a and b are required")
    return JSONResponse({"ok": True, **p.store.trace_path(a, b)})


@_guard
async def api_query(request: Request) -> JSONResponse:
    p = require(request)
    q = request.query_params.get("q", "")
    if not q.strip():
        return _err("q is required")
    budget = int(request.query_params.get("budget", 2000))
    depth = int(request.query_params.get("depth", 1))
    return JSONResponse(p.store.query(q, budget=budget, depth=depth))


@_guard
async def api_graph(request: Request) -> JSONResponse:
    """Canvas payload. Always sliced server-side — a real graph is 19 MB."""
    p = require(request)
    st = p.store
    mode = request.query_params.get("mode", "top")
    limit = min(int(request.query_params.get("limit", 220)), 1200)
    if mode == "community":
        cid = request.query_params.get("community")
        if cid is None:
            return _err("community is required for mode=community")
        return JSONResponse({"ok": True, "mode": mode, **st.top_subgraph(limit, int(cid))})
    if mode == "focus":
        node = request.query_params.get("node", "")
        depth = min(int(request.query_params.get("depth", 1)), 3)
        sub = st.focus_subgraph(node, depth=depth, limit=limit)
        if sub is None:
            return _err(f"no node matches {node!r}", 404)
        return JSONResponse({"ok": True, "mode": mode, **sub})
    return JSONResponse({"ok": True, "mode": "top", **st.top_subgraph(limit)})


@_guard
async def api_ide_config(request: Request) -> JSONResponse:
    """Copy-paste MCP config for the hosts that already speak MCP."""
    p = require(request)
    host = (request.query_params.get("host") or "vscode").lower()
    base = str(request.base_url).rstrip("/")
    mcp_url = os.environ.get("GRAPHIFY_MCP_URL") or f"{base}/mcp"
    key = os.environ.get("GRAPHIFY_MCP_KEY") or "<YOUR_API_KEY>"
    entry = {
        "graphify": {
            "type": "http",
            "url": mcp_url,
            "headers": {"Authorization": f"Bearer {key}"},
        }
    }
    wrappers = {
        "vscode": {"servers": entry},
        "cursor": {"mcpServers": entry},
        "claude": {"mcpServers": entry},
        "windsurf": {"mcpServers": entry},
        "codex": {"mcp_servers": {"graphify": {"url": mcp_url}}},
    }
    assert p.workspace is not None
    return JSONResponse(
        {
            "ok": True,
            "host": host,
            "mcp_url": mcp_url,
            "mcp_enabled": MCP_AVAILABLE,
            "workspace": p.workspace.slug,
            "config": wrappers.get(host, wrappers["vscode"]),
        }
    )



# ------------------------------------------------------------------- upload


@_guard
async def api_upload(request: Request) -> JSONResponse:
    """Self-serve graph upload: a tenant never touches the host filesystem.

    The file lands inside the data-root jail under its own workspace slug, is
    validated structurally before anything references it, and is measured
    against the plan's node cap before the workspace row exists — so an
    over-limit upload leaves no partial state behind.
    """
    p = require(request, meter=False)
    if p.user is None:
        raise AuthError("upload needs a browser session", 403)
    a = get_auth()
    plan_id = _best_plan(a, p.user.id)
    plan = plan_of(plan_id)

    owned = len(a.workspaces_for(p.user.id))
    if owned >= plan["max_workspaces"]:
        raise LimitExceeded(f"plan allows {plan['max_workspaces']} workspaces and you have {owned}.")

    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise AuthError("multipart field 'file' is required", 400)
    name = (form.get("name") or "").strip() or Path(upload.filename or "graph").stem
    cap_bytes = int(plan["max_upload_mb"]) * 1024 * 1024

    chunks: list[bytes] = []
    size = 0
    while chunk := await upload.read(1024 * 1024):
        size += len(chunk)
        if size > cap_bytes:
            raise LimitExceeded(
                f"upload exceeds the {plan['max_upload_mb']} MB cap of plan '{plan['name']}'"
            )
        chunks.append(chunk)
    raw = b"".join(chunks)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise AuthError(f"not a valid JSON graph: {e}", 400)
    if not isinstance(data, dict) or "nodes" not in data or ("links" not in data and "edges" not in data):
        raise AuthError("graph.json must carry 'nodes' and 'links'", 400)

    from saas.auth import slugify

    slug = slugify(name)
    target_dir = data_root() / slug
    if (target_dir / "graph.json").exists():
        slug = f"{slug}-{uuid4hex()}"
        target_dir = data_root() / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "graph.json"
    target.write_bytes(raw)
    try:
        store = GRAPHS.preload(target)
        _check_nodes(store, plan_id)
    except Exception:
        # No half-created tenant: the file goes away with the failure.
        import shutil

        shutil.rmtree(target_dir, ignore_errors=True)
        GRAPHS.evict(target)
        raise
    ws = a.create_workspace(p.user.id, name, str(target), slug=slug)
    a.meter(ws.id, "upload", 1, bytes_=size)
    return JSONResponse({"ok": True, "workspace": _ws_json(ws, store), "bytes": size})


def uuid4hex() -> str:
    import uuid

    return uuid.uuid4().hex[:6]


# ------------------------------------------------------- teams & invitations


@_guard
async def api_members(request: Request) -> JSONResponse:
    p = require(request, meter=False)
    assert p.workspace is not None
    a = get_auth()
    if request.method == "DELETE":
        require_role(p, "owner")
        uid = request.path_params["user_id"]
        if p.user is not None and uid == p.user.id:
            raise AuthError("the owner cannot remove themselves", 400)
        if not a.remove_member(p.workspace.id, uid):
            raise AuthError("not a member", 404)
        return JSONResponse({"ok": True})
    require_role(p, "owner", "member", "viewer")
    return JSONResponse({"ok": True, "members": a.members(p.workspace.id)})


@_guard
async def api_invites(request: Request) -> JSONResponse:
    p = require(request, meter=False)
    assert p.workspace is not None
    a = get_auth()
    if request.method == "POST":
        require_role(p, "owner")
        plan = plan_of(p.workspace.plan)
        if len(a.members(p.workspace.id)) >= plan["max_members"]:
            raise LimitExceeded(
                f"plan '{plan['name']}' caps the team at {plan['max_members']} members."
            )
        body = await request.json()
        assert p.user is not None
        token, inv = a.create_invite(
            p.workspace.id, body.get("email", ""), body.get("role", "member"), p.user.id
        )
        base = str(request.base_url).rstrip("/")
        return JSONResponse(
            {"ok": True, "invite": inv, "token": token, "accept_url": f"{base}/invite?token={token}"}
        )
    require_role(p, "owner")
    return JSONResponse({"ok": True, "invites": a.invites(p.workspace.id)})


@_guard
async def api_invite_revoke(request: Request) -> JSONResponse:
    p = require(request, meter=False)
    require_role(p, "owner")
    assert p.workspace is not None
    if not get_auth().revoke_invite(request.path_params["invite_id"], p.workspace.id):
        raise AuthError("unknown or already-accepted invite", 404)
    return JSONResponse({"ok": True})


async def api_invite_lookup(request: Request) -> JSONResponse:
    """Public: what an invite token points at, without leaking anything else."""
    token = request.query_params.get("token", "")
    inv = get_auth().invite_by_token(token)
    if inv is None:
        return JSONResponse({"ok": False, "error": "invite not found, used, or expired"}, status_code=404)
    me = principal(request)
    return JSONResponse(
        {
            "ok": True,
            "invite": {k: inv[k] for k in ("email", "role", "workspace", "slug")},
            "signed_in": me.user is not None,
            "email": me.user.email if me.user else None,
        }
    )


@_guard
async def api_invite_accept(request: Request) -> JSONResponse:
    p = principal(request)
    if p.user is None:
        raise AuthError("sign in first", 401)
    body = await request.json()
    ws = get_auth().accept_invite(body.get("token", ""), p.user)
    if ws is None:
        raise AuthError("invite not found, used, or expired", 404)
    return JSONResponse({"ok": True, "workspace": _ws_json(ws)})


async def invite_page(request: Request) -> Response:
    return _page("invite.html")


# ---------------------------------------------------------- usage & billing


@_guard
async def api_usage(request: Request) -> JSONResponse:
    p = require(request, meter=False)
    assert p.workspace is not None
    a = get_auth()
    plan = plan_of(p.workspace.plan)
    use = a.usage(p.workspace.id)
    return JSONResponse(
        {
            "ok": True,
            "plan": {"id": p.workspace.plan, **plan},
            "plans": {k: v for k, v in PLANS.items()},
            "usage": use,
            "history": a.usage_history(p.workspace.id),
            "counts": {
                "members": len(a.members(p.workspace.id)),
                "workspaces": len(a.workspaces_for(p.user.id)) if p.user else 0,
            },
            "daily": a.daily_series(p.workspace.id, 9),
        }
    )


@_guard
async def api_billing_plan(request: Request) -> JSONResponse:
    """Plan change hook. A real deployment swaps the body of this function for
    a Stripe checkout session + webhook; the limits, usage rows and UI already
    behave as if it were live."""
    p = require(request, meter=False)
    require_role(p, "owner")
    assert p.workspace is not None
    body = await request.json()
    ws = get_auth().set_plan(p.workspace.id, body.get("plan", ""))
    if ws is None:
        raise AuthError("workspace gone", 404)
    return JSONResponse({"ok": True, "workspace": _ws_json(ws), "plan": plan_of(ws.plan)})


# ---------------------------------------------------------------- live sync


async def api_events(request: Request) -> Response:
    """SSE feed: tells open workspaces when their graph was rebuilt.

    ``graphify watch`` / ``graphify update`` rewrite graph.json in place; the
    registry notices via (mtime, size), and this stream turns that into a push
    so a browser tab never shows a stale graph. Polling the fingerprint is
    deliberately cheap (one stat per workspace per tick).
    """
    p = principal(request)
    if p.via == "none" or p.workspace is None:
        return _err("authentication required", 401)
    ws = p.workspace

    import asyncio as _asyncio

    async def stream():
        last = None
        yield f"event: hello\ndata: {json.dumps({'workspace': ws.slug})}\n\n"
        for _ in range(600):  # ~20 min cap; the client reconnects
            try:
                fp = graph_fingerprint(Path(ws.graph_path))
            except OSError:
                fp = None
            if fp != last:
                if last is not None:
                    try:
                        st = GRAPHS.get(ws.graph_path)
                        payload = {"nodes": len(st.nodes), "edges": st.G.number_of_edges()}
                    except Exception:
                        payload = {"nodes": None, "edges": None}
                    yield f"event: graph\ndata: {json.dumps(payload)}\n\n"
                last = fp
            await _asyncio.sleep(2)

    from starlette.responses import StreamingResponse

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache, no-transform", "x-accel-buffering": "no"},
    )



# ---------------------------------------------------------------------- mcp


class McpDispatch:
    """Raw-ASGI gate: authenticate, pick the tenant's session manager, hand over.

    Raw ASGI (not a Starlette endpoint) because the Streamable HTTP transport
    streams SSE — any middleware that buffers the response body would break it,
    which is the same reason ``graphify.serve._ApiKeyMiddleware`` is raw.
    """

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._deny(scope, receive, send, 500, "unsupported scope")
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        token = None
        authz = headers.get("authorization", "")
        if authz.lower().startswith("bearer "):
            token = authz[7:].strip()
        token = token or headers.get("x-api-key", "").strip() or None

        workspace = None
        wanted = headers.get("x-workspace", "")
        if token and token.startswith("gf_"):
            found = get_auth().workspace_from_key(token)
            if found:
                workspace = found[0]
                # Same rule as the REST surface: a key cannot cross tenants, and
                # asking it to is an error rather than a silent substitution.
                if wanted and wanted not in (workspace.id, workspace.slug):
                    await self._deny(
                        scope, receive, send, 403,
                        f"api key is scoped to workspace '{workspace.slug}'",
                    )
                    return
        else:
            # A logged-in browser session can reach MCP too (used by the
            # in-app "try it" panel); it must name its workspace explicitly.
            cookie = headers.get("cookie", "")
            session = next(
                (c.split("=", 1)[1].strip() for c in cookie.split(";") if c.strip().startswith(SESSION_COOKIE + "=")),
                None,
            )
            user = get_auth().user_from_token(session or token)
            if user:
                workspaces = get_auth().workspaces_for(user.id)
                workspace = next(
                    (w for w in workspaces if w.id == wanted or w.slug == wanted), None
                ) or (workspaces[0] if workspaces else None)

        if workspace is None:
            await self._deny(scope, receive, send, 401, "invalid or missing api key")
            return
        try:
            graph_path = safe_graph_path(workspace.graph_path)
        except AuthError as e:
            await self._deny(scope, receive, send, e.status, e.message)
            return
        if not graph_path.exists():
            await self._deny(scope, receive, send, 404, f"no graph for workspace {workspace.slug}")
            return
        try:
            get_auth().check_api_quota(workspace)
            get_auth().meter(workspace.id, "mcp")
            manager = await MCP.manager_for(str(graph_path))
        except ImportError as e:
            await self._deny(scope, receive, send, 503, f"mcp extra missing: {e}")
            return
        except AuthError as e:
            await self._deny(scope, receive, send, e.status, e.message)
            return
        await manager.handle_request(scope, receive, send)

    @staticmethod
    async def _deny(scope, receive, send, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


# ------------------------------------------------------------------- wiring


def build_app(graph_path: str | None = None, *, with_mcp: bool = True) -> Starlette:
    global MCP_AVAILABLE
    routes = [
        Route("/", landing),
        Route("/login", auth_page),
        Route("/signup", auth_page),
        Route("/app", index),
        Route("/theme.css", theme_css),
        Route("/api/health", api_health),
        Route("/api/theme", api_theme),
        Route("/api/auth/signup", api_signup, methods=["POST"]),
        Route("/api/auth/login", api_login, methods=["POST"]),
        Route("/api/auth/logout", api_logout, methods=["POST"]),
        Route("/api/auth/demo", api_demo_login, methods=["POST"]),
        Route("/api/auth/me", api_me),
        Route("/api/workspaces", api_workspaces, methods=["GET", "POST"]),
        Route("/api/keys", api_keys, methods=["GET", "POST"]),
        Route("/api/keys/{key_id}", api_key_revoke, methods=["DELETE"]),
        Route("/api/workspaces/upload", api_upload, methods=["POST"]),
        Route("/api/members", api_members, methods=["GET"]),
        Route("/api/members/{user_id}", api_members, methods=["DELETE"]),
        Route("/api/invites", api_invites, methods=["GET", "POST"]),
        Route("/api/invites/{invite_id}", api_invite_revoke, methods=["DELETE"]),
        Route("/api/invites/accept", api_invite_accept, methods=["POST"]),
        Route("/api/invites/lookup", api_invite_lookup),
        Route("/invite", invite_page),
        Route("/api/usage", api_usage),
        Route("/api/billing/plan", api_billing_plan, methods=["POST"]),
        Route("/api/events", api_events),
        Route("/api/stats", api_stats),
        Route("/api/god-nodes", api_god_nodes),
        Route("/api/communities", api_communities),
        Route("/api/search", api_search),
        Route("/api/explain", api_explain),
        Route("/api/path", api_path),
        Route("/api/query", api_query),
        Route("/api/graph", api_graph),
        Route("/api/ide-config", api_ide_config),
        Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
    ]
    if with_mcp:
        try:
            import mcp.server.streamable_http_manager  # noqa: F401
            from graphify.serve import _build_server  # noqa: F401

            routes.insert(-1, Route("/mcp", endpoint=McpDispatch()))
            MCP_AVAILABLE = True
        except ImportError as e:
            print(
                f"[graphify-app] MCP endpoint disabled ({e}); "
                'run: pip install "graphifyy[mcp]"',
                flush=True,
            )

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        try:
            yield
        finally:
            await MCP.aclose()

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # IDE webviews call from a null/vscode origin
            allow_credentials=False,  # tokens ride in Authorization, not cookies
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id"],
        )
    ]
    middleware.insert(0, Middleware(RevalidateMiddleware))
    middleware.insert(0, Middleware(AccessLogMiddleware))
    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


def _seed_demo(a: Auth, graph: str) -> tuple[str, str]:
    """Create the demo account so a fresh deployment is immediately usable."""
    email = os.environ.get("GRAPHIFY_DEMO_EMAIL", "demo@graphify.dev")
    password = os.environ.get("GRAPHIFY_DEMO_PASSWORD", "graphify-demo")
    try:
        user, _ = a.signup(email, password, "Demo")
    except AuthError:
        return email, password  # already there
    name = Path(graph).resolve().parent.parent.name or "graphify"
    a.create_workspace(user.id, name, graph, slug="graphify")
    GRAPHS.preload(graph)
    return email, password


def main(argv: list[str] | None = None) -> None:
    global _BOOTSTRAP_GRAPH
    ap = argparse.ArgumentParser(prog="python -m saas.server")
    ap.add_argument("--graph", default=os.environ.get("GRAPHIFY_GRAPH"), help="bootstrap graph.json")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--no-mcp", action="store_true", help="serve only the web app + REST API")
    ap.add_argument("--demo", action="store_true", help="seed a demo account on first boot")
    args = ap.parse_args(argv)

    if args.graph:
        _BOOTSTRAP_GRAPH = str(Path(args.graph).resolve())

    import uvicorn

    a = get_auth()
    demo: tuple[str, str] | None = None
    global DEMO_LOGIN, _DEMO_CREDS
    if _BOOTSTRAP_GRAPH and Path(_BOOTSTRAP_GRAPH).exists():
        if args.demo or a.user_count() == 0:
            demo = _seed_demo(a, _BOOTSTRAP_GRAPH)
        # Warm the graph even when the demo account already existed, so the
        # first request after a restart is not the one that pays the parse.
        GRAPHS.preload(_BOOTSTRAP_GRAPH)
        print(f"[graphify-app] bootstrap graph: {_BOOTSTRAP_GRAPH}", flush=True)

    app = build_app(_BOOTSTRAP_GRAPH, with_mcp=not args.no_mcp)
    base = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}"
    cached = GRAPHS.snapshot()
    loaded = f"{cached[0]['nodes']} nodes / {cached[0]['edges']} edges" if cached else "no graph loaded yet"
    print(f"[graphify-app] ready ({loaded}) on {base}", flush=True)
    if MCP_AVAILABLE:
        print(f"[graphify-app] MCP endpoint (Streamable HTTP, api-key auth): {base}/mcp", flush=True)
    if demo:
        DEMO_LOGIN = True
        _DEMO_CREDS = demo
        print(f"[graphify-app] demo login: {demo[0]} / {demo[1]} (one-click enabled)", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
