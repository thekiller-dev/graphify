"""In-process smoke test for the app server: ``python -m saas.selftest``.

Exists because a handler returning a bare dict instead of a Response produced
a 500 on ``/api/auth/me`` that no curl-level check exercised — the browser
looped back to /login while every other endpoint looked healthy. This drives
the real ASGI app (no httpx, no port, no network) through the exact journey a
browser takes, and asserts the status of each hop.

Run:  .venv/bin/python -m saas.selftest [path/to/graph.json]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path


class AsgiClient:
    """Minimal ASGI driver: just enough HTTP to exercise JSON routes."""

    def __init__(self, app):
        self.app = app

    async def request(self, method: str, path: str, *, json_body=None, headers=None, cookie=None):
        headers = dict(headers or {})
        body = b""
        if json_body is not None:
            body = json.dumps(json_body).encode()
            headers.setdefault("content-type", "application/json")
        raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        if cookie:
            raw_headers.append((b"cookie", cookie.encode()))
        if body:
            raw_headers.append((b"content-length", str(len(body)).encode()))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path.split("?")[0],
            "raw_path": path.encode(),
            "query_string": path.split("?", 1)[1].encode() if "?" in path else b"",
            "headers": raw_headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        sent = {"body": b"", "status": None, "headers": {}}
        done = asyncio.Event()

        async def receive():
            if body:
                return {"type": "http.request", "body": body, "more_body": False}
            await done.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                sent["status"] = message["status"]
                sent["headers"] = {k.decode(): v.decode() for k, v in message.get("headers", [])}
            elif message["type"] == "http.response.body":
                sent["body"] += message.get("body", b"")
                if not message.get("more_body"):
                    done.set()

        await self.app(scope, receive, send)
        try:
            parsed = json.loads(sent["body"] or b"{}")
        except json.JSONDecodeError:
            parsed = {}
        return sent["status"], parsed, sent["headers"]


async def main() -> int:
    graph = Path(sys.argv[1] if len(sys.argv) > 1 else "worked/httpx/graph.json")
    if not graph.exists():
        print(f"skip: no graph at {graph}")
        return 0
    tmp = tempfile.mkdtemp(prefix="gf-selftest-")
    os.environ["GRAPHIFY_APP_DB"] = str(Path(tmp) / "app.db")
    os.environ["GRAPHIFY_APP_DATA_ROOT"] = str(Path(tmp) / "graphs")

    from saas.server import build_app
    from saas.auth import auth as get_auth

    app = build_app(str(graph), with_mcp=False)
    # Lifespan is only needed for MCP supervisors; the REST surface is
    # lifespan-free, so we can drive routes directly.
    client = AsgiClient(app)
    fails: list[str] = []

    def check(label: str, got, want):
        ok = got == want if not isinstance(want, tuple) else got in want
        print(f"  {'PASS' if ok else 'FAIL'}  {label:<38} {got}")
        if not ok:
            fails.append(f"{label}: {got} != {want}")

    print(f"selftest against {graph}")
    st, _, _ = await client.request("GET", "/api/health")
    check("health", st, 200)

    st, body, _ = await client.request(
        "POST", "/api/auth/signup",
        json_body={"email": "self@test.dev", "password": "password123", "name": "Self"},
    )
    check("signup", st, 200)
    token = body.get("token", "")

    # the regression that bounced real users: me must be 200 on a fresh session
    st, body, _ = await client.request("GET", "/api/auth/me", headers={"authorization": f"Bearer {token}"})
    check("me (bearer)", st, 200)
    st, body, _ = await client.request("GET", f"/api/auth/me?token={token}")
    check("me (query param)", st, 200)
    st, _, _ = await client.request("GET", "/api/auth/me")
    check("me (anonymous)", st, 401)

    # a brand-new account has no workspace: creating the first one must work.
    # The graph has to live under the data root (the path jail), like a real
    # upload puts it, so stage it there first.
    a = get_auth()
    import shutil
    staged_dir = Path(os.environ["GRAPHIFY_APP_DATA_ROOT"]) / "_staged"
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged = staged_dir / "graph.json"
    shutil.copy(graph, staged)
    st, body, _ = await client.request(
        "POST", "/api/workspaces",
        json_body={"name": "selftest", "graph": str(staged)},
        headers={"authorization": f"Bearer {token}"},
    )
    check("create workspace (fresh account)", st, 200)
    if st == 200:
        st, body, _ = await client.request("GET", "/api/stats", headers={"authorization": f"Bearer {token}"})
        check("stats", st, 200)
        check("stats has nodes", body.get("nodes", 0) > 0, True)
        st, body, _ = await client.request(
            "GET", "/api/graph?mode=top&limit=50", headers={"authorization": f"Bearer {token}"}
        )
        check("graph slice", st, 200)
        check("slice capped", len(body.get("nodes", [])) <= 50, True)

    st, body, _ = await client.request(
        "POST", "/api/keys", json_body={"name": "t"},
        headers={"authorization": f"Bearer {token}"},
    )
    check("create api key", st, 200)
    key = body.get("key", {}).get("secret", "")
    st, _, _ = await client.request("GET", "/api/stats", headers={"authorization": f"Bearer {key}"})
    check("stats via api key", st, 200)
    st, _, _ = await client.request("GET", "/api/stats", headers={"authorization": "Bearer gf_bogus"})
    check("bogus key rejected", st, 401)

    print("RESULT:", "all green" if not fails else f"{len(fails)} failure(s): {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
