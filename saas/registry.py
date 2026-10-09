"""Per-workspace graph + MCP registries (the multi-tenant half of the server).

A single-tenant process parses one graph.json at boot. A hosted one must serve
N tenants without holding N × 19 MB in RAM forever, and without re-parsing on
every request. So:

* ``GraphRegistry`` keeps a bounded LRU of :class:`GraphStore` keyed by the
  resolved graph path, and drops an entry when the file's mtime/size changes —
  which is what makes ``graphify update`` in a tenant's checkout show up here
  without a restart.
* ``McpRegistry`` builds one Streamable-HTTP session manager per workspace,
  lazily, entering each manager's task group into a process-wide
  ``AsyncExitStack`` (a manager's ``run()`` must wrap request handling, and a
  mounted sub-app's own lifespan never executes).
"""
from __future__ import annotations

import asyncio
import os
import threading
from collections import OrderedDict
from pathlib import Path

from saas.graph_store import GraphStore


def fingerprint(path: Path) -> tuple[float, int] | None:
    try:
        st = path.stat()
        return (st.st_mtime, st.st_size)
    except OSError:
        return None


class GraphRegistry:
    """Bounded LRU of parsed graphs, invalidated by (mtime, size)."""

    def __init__(self, max_entries: int | None = None):
        self.max_entries = int(
            max_entries or os.environ.get("GRAPHIFY_APP_MAX_GRAPHS") or 6
        )
        self._entries: OrderedDict[str, tuple[tuple[float, int] | None, GraphStore]] = OrderedDict()
        self._lock = threading.Lock()
        self.misses = 0

    def get(self, graph_path: str | Path) -> GraphStore:
        path = Path(graph_path)
        if not path.exists():
            raise FileNotFoundError(f"graph.json not found: {path}")
        key = str(path.resolve())
        fp = fingerprint(path)
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None and hit[0] == fp:
                self._entries.move_to_end(key)
                return hit[1]
            if hit is not None:
                del self._entries[key]  # stale: the graph was rebuilt
            self.misses += 1
        # Parse outside the lock: it is the slow part (seconds on a big repo) and
        # holding the lock would serialise every tenant behind it.
        store = GraphStore(path)
        with self._lock:
            self._entries[key] = (fp, store)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
        return store

    def peek(self, graph_path: str | Path) -> GraphStore | None:
        """Return the cached store without parsing — for cheap list views."""
        path = Path(graph_path)
        fp = fingerprint(path)
        with self._lock:
            hit = self._entries.get(str(path.resolve()))
            if hit is not None and hit[0] == fp:
                return hit[1]
        return None

    def evict(self, graph_path: str | Path) -> None:
        """Drop a cached entry — used when an upload is rolled back."""
        with self._lock:
            self._entries.pop(str(Path(graph_path).resolve()), None)

    def preload(self, graph_path: str | Path) -> GraphStore:
        """Warm one graph, used at boot so the first request is not the slow one."""
        return self.get(graph_path)

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [
                {"graph": k, "nodes": len(v[1].nodes), "edges": v[1].G.number_of_edges()}
                for k, v in self._entries.items()
            ]


class McpRegistry:
    """One MCP session manager per graph, created on first authenticated use.

    A ``StreamableHTTPSessionManager.run()`` opens an anyio cancel scope, and
    anyio refuses to close a scope from a different task than the one that
    opened it. Creating managers lazily inside a request handler therefore
    cannot work: the scope would be entered in the request's task and exited in
    the lifespan's task at shutdown. So each manager gets its own long-lived
    supervisor task that enters ``run()``, publishes the manager, and then waits
    on a stop event — the scope is opened *and* closed by that one task, and
    shutdown is a clean ``stop.set()`` rather than a cancellation.
    """

    def __init__(self) -> None:
        self._managers: dict[str, object] = {}
        self._ready: dict[str, asyncio.Event] = {}
        self._stop: dict[str, asyncio.Event] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._errors: dict[str, BaseException] = {}
        self._lock = asyncio.Lock()
        self.enabled = False

    async def manager_for(self, graph_path: str, timeout: float = 30.0):
        """Return the session manager serving *graph_path*, starting it if needed."""
        key = str(Path(graph_path).resolve())
        if key in self._managers:
            return self._managers[key]
        async with self._lock:
            if key in self._managers:
                return self._managers[key]
            if key in self._errors:
                raise self._errors[key]
            if key not in self._tasks:
                self._ready[key] = asyncio.Event()
                self._stop[key] = asyncio.Event()
                self._tasks[key] = asyncio.create_task(
                    self._supervise(key, graph_path), name=f"graphify-mcp-{key}"
                )
            ready = self._ready[key]
        try:
            await asyncio.wait_for(ready.wait(), timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(f"MCP manager for {graph_path} did not start in {timeout}s")
        if key in self._errors:
            raise self._errors[key]
        self.enabled = True
        return self._managers[key]

    async def _supervise(self, key: str, graph_path: str) -> None:
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from mcp.server.transport_security import TransportSecuritySettings

        from graphify.serve import _build_server

        try:
            manager = StreamableHTTPSessionManager(
                app=_build_server(graph_path),
                json_response=False,
                stateless=False,
                # Tenants reach us through a proxy hostname, so Host is not
                # pinned to the bind address.
                security_settings=TransportSecuritySettings(
                    enable_dns_rebinding_protection=False
                ),
                session_idle_timeout=3600.0,
            )
        except Exception as e:  # ImportError (no mcp extra) or a bad graph path
            self._errors[key] = e
            self._ready[key].set()
            return
        try:
            async with manager.run():
                self._managers[key] = manager
                self._ready[key].set()
                await self._stop[key].wait()
        except BaseException as e:
            self._errors.setdefault(key, e)
            self._ready[key].set()
            raise
        finally:
            self._managers.pop(key, None)

    async def aclose(self) -> None:
        """Stop every supervisor task; each closes its own cancel scope."""
        for stop in self._stop.values():
            stop.set()
        tasks = list(self._tasks.values())
        self._tasks.clear()
        self._stop.clear()
        self._ready.clear()
        self._managers.clear()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.enabled = False

    def snapshot(self) -> list[str]:
        return sorted(self._managers)


GRAPHS = GraphRegistry()
MCP = McpRegistry()
