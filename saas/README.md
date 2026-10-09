# graphify app

The hosted product surface on top of the `graphify` library: a web workspace for
humans, a JSON API for your own extension, and an MCP endpoint for agents —
one process, one origin, **multi-tenant**.

```
                    ┌───────────────────────────────────────────────────┐
   browser  ───────▶│  GET /            landing page (public)           │
                    │  GET /login       auth pages (public)             │
   browser  ───────▶│  GET /app         workspace UI (token-gated)      │
   IDE ext. ───────▶│  GET /api/*       JSON read API                   │  saas/server.py
   agent    ───────▶│  POST /mcp        MCP Streamable HTTP             │  (Starlette + uvicorn)
                    └───────┬───────────────────────────┬───────────────┘
                            │                           │
                 session / gf_… api key        one graph per workspace
                            │                           │
                    ┌───────▼────────┐        ┌─────────▼──────────┐
                    │ saas/auth.py   │        │ saas/registry.py   │
                    │ sqlite: users, │        │ LRU GraphStore     │
                    │ sessions,      │        │ + per-tenant MCP   │
                    │ workspaces,    │        │   supervisors      │
                    │ members, keys  │        └─────────┬──────────┘
                    └────────────────┘                  │
                                              ┌─────────▼──────────────────┐
                                              │ saas/data/graphs/<ws>/     │
                                              │   graph.json               │
                                              └─────────▲──────────────────┘
                                                        │ built by
                                        graphify extract . --code-only
```

## Run it

```bash
# 1. build a graph (local AST, no API key — ~26s on this repo)
graphify extract . --code-only

# 2. serve it, seeding a demo account on first boot
python -m saas.server --host 0.0.0.0 --port 8000 \
  --graph graphify-out/graph.json --demo
```

Open `http://localhost:8000` for the landing page, `/login` to sign in with the
credentials printed at boot
(default `demo@graphify.dev` / `graphify-demo`), create an API key under
**IDE & API**, and point your IDE at `/mcp`.

| Flag / env | Meaning |
|---|---|
| `--graph PATH` | bootstrap graph; also the one path a workspace may use outside the data root |
| `--demo` | seed the demo account + workspace when the DB has no users |
| `--host` / `--port` | bind address (`0.0.0.0` for containers/proxies) |
| `--no-mcp` | skip the MCP endpoint (also skipped without the `[mcp]` extra) |
| `GRAPHIFY_APP_DB` | sqlite file (default `saas/data/app.db`) |
| `GRAPHIFY_APP_DATA_ROOT` | where tenant graphs live (default `saas/data/graphs`) |
| `GRAPHIFY_APP_MAX_GRAPHS` | LRU size for parsed graphs (default 6) |
| `GRAPHIFY_DEMO_EMAIL` / `_PASSWORD` | override the seeded credentials |
| `GRAPHIFY_COOKIE_SAMESITE` | `none` (default, needed in iframes/webviews) or `lax` |

## Auth & tenancy

```
user ──< member >── workspace ──< api_key
                        └── graph_path (one graph.json)
```

* **Passwords** — PBKDF2-HMAC-SHA256, 210k rounds, per-user salt.
* **Sessions** — 30 days, `secrets.token_urlsafe`, stored **hashed**; accepted
  from the `gf_session` cookie *or* `Authorization: Bearer <token>`, because a
  cross-site iframe (the preview, an IDE webview) cannot rely on cookies.
* **API keys** — `gf_…`, stored hashed, workspace-scoped, shown once, revocable,
  `last_used_at` tracked. This is what an IDE or an agent uses.
* **Roles** — `owner` / `member` / `viewer`; keys are manageable by owner and
  member only.
* **Tenant isolation** — a key is welded to its workspace. Sending
  `X-Workspace` for a different one is a **403**, not a silent substitution, so
  a misconfigured client cannot believe it crossed tenants. A session may switch
  only among workspaces it is a member of.
* **Path jail** — `POST /api/workspaces` resolves the graph path and requires it
  to live under `GRAPHIFY_APP_DATA_ROOT` (or be the `--bootstrap-graph`), so the
  endpoint cannot be used to read arbitrary JSON off the host.

No ORM, no auth dependency: `saas/auth.py` is stdlib `sqlite3` + `hashlib` +
`secrets`, because this file is the security boundary and should stay readable.
OIDC/SSO slots in behind `Auth.user_from_token` without touching the routes.

## API

Pages: `/` (landing), `/login` and `/signup` (auth), `/app` (workspace; bounces
to `/login` when there is no token).
Public API: `/api/health`, `/api/theme`, `/theme.css`, `/static/*`, `/api/auth/*`.
Everything below requires a session or an API key, and is scoped to one workspace.

| Endpoint | Returns |
|---|---|
| `GET /api/auth/me` | user, workspaces, active workspace |
| `GET\|POST /api/workspaces` | list / create (owner-session only) |
| `GET\|POST /api/keys` | list / create keys for the active workspace |
| `DELETE /api/keys/{id}` | revoke |
| `GET /api/stats` | nodes, edges, communities, files, relation mix, confidence split |
| `GET /api/god-nodes?limit=15` | most-connected concepts (file-level hubs excluded) |
| `GET /api/communities?limit=24` | subsystems: size, hub, sample members, relation mix |
| `GET /api/search?q=&limit=20` | type-ahead symbol lookup, ranked by degree |
| `GET /api/explain?node=` | one node + connections, grouped and confidence-tagged |
| `GET /api/path?a=&b=` | shortest path, hop by hop with relations |
| `GET /api/query?q=&depth=&budget=` | question → scoped subgraph (local keyword-seeded BFS) |
| `GET /api/graph?mode=top\|focus\|community&limit=` | canvas payload, sliced server-side |
| `GET /api/ide-config?host=vscode` | copy-paste MCP config for that host |
| `POST /mcp` | MCP Streamable HTTP — 10 tools, bearer-key auth |

A real graph is ~19 MB; it never leaves the server. `/api/graph` returns an
induced subgraph capped at 1200 nodes, which keeps the payload and the
browser-side force simulation interactive.

## The SaaS surface

Plans are data in `saas/auth.py:PLANS`; every enforcement point reads the same
table, so changing a plan is a config edit, not a code path.

| Limit | Free | Pro | Enforced at |
|---|---|---|---|
| Workspaces per user | 3 | 50 | `POST /api/workspaces`, upload |
| Seats per workspace | 3 | 25 | invite create / accept |
| Nodes per graph | 250 k | 5 M | attach + upload, before the workspace row exists |
| API calls / month | 50 k | 2 M | `require()` — one gate, so no endpoint can forget it |
| Upload size | 100 MB | 1 GB | streamed, capped while reading |

* **Metering** — every served API call and every MCP request increments a
  per-workspace, per-month row (`usage`). Over quota is **402**, not 403: the
  credential is fine, the plan isn't. `/api/usage` returns the counters, the
  plan cards and the 12-month history the Billing view draws.
* **Upload** — `POST /api/workspaces/upload` (multipart) is the self-serve path:
  the file lands inside the data-root jail under its own slug, is validated
  structurally, parsed and measured against the node cap, and only then does
  the workspace row get created. A failed upload rolls the file back — no
  half-created tenant.
* **Teams** — `owner` / `member` / `viewer`. Invites are bound to one address,
  expire in 7 days, are single-use, and `/invite?token=…` is a public page that
  reveals nothing but the workspace name and role until you are signed in as
  the invitee.
* **Billing hook** — `POST /api/billing/plan` flips a workspace's plan today.
  A real deployment swaps its body for a Stripe checkout session + webhook;
  limits, usage rows and the UI already behave as if it were live. AST
  extraction stays unmetered on purpose: it is local and free, so it must not
  be the billable unit.
* **Live sync** — `GET /api/events` is an SSE feed: it stats the workspace's
  graph every 2 s and pushes `event: graph` when `(mtime, size)` changes, so a
  tab open on the workspace refreshes itself after `graphify update`.
  EventSource cannot set headers, so this one route also accepts `?token=`;
  every other route stays header/cookie-only to keep tokens out of proxy logs.

## Serving many graphs

`GraphRegistry` is a bounded LRU of parsed graphs keyed by resolved path, and it
drops an entry when `(mtime, size)` changes — so a tenant running
`graphify update` sees the new graph without a restart, and 50 tenants do not
mean 50 × 19 MB in RAM.

`McpRegistry` gives each graph its own `StreamableHTTPSessionManager`. A
manager's `run()` opens an anyio cancel scope, and anyio refuses to close a scope
from a different task than the one that opened it — so managers are **not**
created inside request handlers. Each gets a supervisor task that enters
`run()`, publishes the manager, and waits on a stop event; shutdown sets the
events and every scope closes in its own task.

## Typography & cache discipline

Sora (display) is self-hosted: latin woff2 vendored from `@fontsource/sora`
(SIL OFL) into `static/fonts/`, so titles render with no network at all —
including inside an IDE webview. Satoshi (text) is distributed exclusively by
Fontshare under the ITF Free Font License and exists on no registry this build
can reach, so it is linked from its official source at runtime and the stack
degrades to Sora, then to the platform UI face, when unreachable.

`/static/*`, `/theme.css` and `/fonts.css` are served with
`Cache-Control: no-cache, must-revalidate`. Without it a proxy or a browser
heuristic cache can pin an old `app.css` while `index.html` moves on — which is
exactly how the login gate once rendered unstyled in a browser holding a stale
stylesheet.

## Theming

`saas/theme.py` is the single source of truth for colour. It generates
`/theme.css` (one `html[data-theme="…"]` token block per palette) *and* the
categorical series colouring communities on the canvas, so the DOM and the graph
cannot drift. Re-branding is one edit; the switcher applies instantly.

Palettes: **Daylight** (default — light, `#4F46E5` accent), **Midnight Indigo**,
**Aurora**, **Sunset**. Add a `Palette(...)` to `PALETTES` and it appears in the
switcher, the CSS and `/api/theme` automatically.

This replaces the hard-coded scheme in `graphify/exporters/html.py`
(`#0f0f1a` background, Table-10 community colours), which still generates the
old look — unifying the two is next on the list.

## Frontend

No build step, no CDN, no framework: `static/index.html` + `app.css` + `app.js`.
The graph is drawn on a `<canvas>` with a hand-rolled force simulation
(repulsion + springs + gravity, alpha-cooled), plus zoom/pan/drag, hover
neighbourhood highlighting, click-to-inspect, double-click-to-expand. It runs
offline, which matters because the same code is meant to end up inside a VS Code
webview.

## Next

Ordered by how much they unblock the SaaS/IDE direction:

1. **VS Code extension** — the API is already extension-shaped (search / explain
   / path / query / theme, CORS open for webview origins, bearer-key auth). Ship
   a webview that reuses `app.js` plus an "explain symbol at cursor" command.
2. **Shared theme with the exporter** — make `graphify/exporters/html.py` read
   `saas/theme.py` so `graph.html` and the app cannot drift apart.
3. **Build jobs** — upload exists; the next rung is a worker queue that clones
   a repo and runs `graphify extract` server-side, so tenants never ship a
   graph.json at all.
4. **Postgres + object storage** — swap `sqlite3` for Postgres (six tables, no
   exotic queries) and graphs for S3; that is the single-VM → horizontally
   scaled step.
5. **Stripe** — replace the body of `POST /api/billing/plan` with a checkout
   session and a webhook; metering and limits are already in place.
6. **VS Code extension** — the API is extension-shaped (bearer keys, CORS open
   for webview origins, `/api/theme` to match colours): a webview reusing
   `app.js` plus an "explain symbol at cursor" command.

## Builds (pipeline hébergé)

`POST /api/builds` `{name, source}` ou `POST /api/builds/upload` (archive
.zip/.tar.*) lancent le pipeline documenté par `ARCHITECTURE.md`
(detect → extract → build → cluster → analyze → report → export) dans un
thread serveur ; progression via événements SSE `build`. Un build terminé
crée le workspace, avec `graph.json`, `GRAPH_REPORT.md` et wiki optionnel.
Passe 1 uniquement (AST tree-sitter, zéro LLM). Vues app : **Constructions**
et **Rapport & exports** (`GET /api/report`, `/api/export?kind=…`,
`/api/benchmark`).

`minigraph/` (racine du repo) est une réimplémentation pédagogique du même
pipeline, module par module : `python -m minigraph.selfdemo <dir>`.
