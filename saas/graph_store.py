"""Read-only graph service for the app.

Loads ``graphify-out/graph.json`` once through the library's own loader
(``graphify.paths.load_node_link_graph``) so stored edge direction survives —
a plain ``node_link_graph`` re-orders undirected edges and silently reverses
them (see ARCHITECTURE.md, #563/#2309). Everything the UI needs is answered
from in-memory indexes; the 19 MB graph is never shipped to the browser, only
the sliced subgraph a view asks for.
"""
from __future__ import annotations

import json
import math
import re
import threading
from collections import Counter, defaultdict, deque
from pathlib import Path

from graphify.paths import load_node_link_graph

_WORD = re.compile(r"[a-z0-9]+")

# Question words carry no graph signal; letting "the"/"what" seed a traversal
# pulls in whatever test file happens to be named …_the_… and drowns the real
# matches. Kept small on purpose — anything else is a potential symbol token.
STOPWORDS = frozenset({
    "the", "and", "for", "with", "what", "which", "who", "how", "why", "when",
    "where", "does", "do", "is", "are", "was", "were", "can", "could", "should",
    "would", "that", "this", "these", "those", "from", "into", "onto", "over",
    "under", "between", "about", "any", "all", "each", "per", "via", "use",
    "uses", "using", "used", "have", "has", "had", "not", "you", "your", "our",
    "them", "they", "there", "here", "will", "shall", "may", "might", "get",
    "gets", "make", "makes", "one", "two", "out", "than", "then", "its", "it",
})


class GraphStore:
    """Thread-safe (read-only after load) facade over one graph.json."""

    def __init__(self, graph_path: str | Path):
        self.path = Path(graph_path)
        if not self.path.exists():
            raise FileNotFoundError(f"graph.json not found: {self.path}")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.G = load_node_link_graph(raw)

        self.nodes: dict[str, dict] = {}
        self.by_label: dict[str, list[str]] = defaultdict(list)
        self.community_members: dict[int, list[str]] = defaultdict(list)
        self.degree: dict[str, int] = {}
        self.adj: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)

        for nid, data in self.G.nodes(data=True):
            d = dict(data)
            d["id"] = nid
            d.setdefault("label", nid)
            d["degree"] = self.G.degree(nid)
            self.nodes[nid] = d
            self.degree[nid] = d["degree"]
            self.by_label[str(d["label"]).lower()].append(nid)
            com = d.get("community")
            if isinstance(com, int):
                self.community_members[com].append(nid)

        # Adjacency with resolved direction: `_src`/`_tgt` win over arc order.
        for u, v, data in self.G.edges(data=True):
            src = data.get("_src", u)
            tgt = data.get("_tgt", v)
            self.adj[src].append((tgt, "out", data))
            self.adj[tgt].append((src, "in", data))

        self._label_index = self._build_label_index()

    # ------------------------------------------------------------------ indexes

    def _build_label_index(self) -> dict[str, list[str]]:
        """Token -> node ids, for question/keyword search."""
        idx: dict[str, list[str]] = defaultdict(list)
        for nid, d in self.nodes.items():
            for tok in set(_WORD.findall(str(d.get("label", "")).lower())):
                if len(tok) > 2:
                    idx[tok].append(nid)
        for tok in idx:
            idx[tok].sort(key=lambda n: -self.degree[n])
        return dict(idx)

    # ------------------------------------------------------------------- basics

    def stats(self) -> dict:
        rel = Counter(d.get("relation", "?") for _, _, d in self.G.edges(data=True))
        conf = Counter(d.get("confidence", "?") for _, _, d in self.G.edges(data=True))
        files = Counter(
            d.get("source_file") for d in self.nodes.values() if d.get("source_file")
        )
        degrees = sorted(self.degree.values())
        n = len(self.nodes)
        return {
            "graph": str(self.path),
            "nodes": n,
            "edges": self.G.number_of_edges(),
            "communities": len(self.community_members),
            "files": len(files),
            "avg_degree": round(sum(degrees) / n, 2) if n else 0,
            "median_degree": degrees[n // 2] if n else 0,
            "relations": rel.most_common(12),
            "confidence": dict(conf),
            "top_files": files.most_common(8),
            "built_at_commit": self.G.graph.get("built_at_commit"),
        }

    def god_nodes(self, limit: int = 15) -> list[dict]:
        top = sorted(self.nodes.values(), key=lambda d: -d["degree"])[: limit * 3]
        # Skip file-level containers: they accumulate edges mechanically.
        picked = [d for d in top if d.get("_origin") != "file"][:limit]
        return [self._card(d) for d in picked]

    def communities(self, limit: int = 24) -> list[dict]:
        out = []
        for cid, members in sorted(
            self.community_members.items(), key=lambda kv: -len(kv[1])
        )[:limit]:
            hub = max(members, key=lambda m: self.degree[m])
            rel = Counter()
            for m in members[:400]:
                for other, _dir, data in self.adj[m]:
                    if other in set(members):
                        rel[data.get("relation", "?")] += 1
            out.append(
                {
                    "id": cid,
                    "size": len(members),
                    "hub": self.nodes[hub].get("label", hub),
                    "hub_id": hub,
                    "sample": [
                        self.nodes[m].get("label", m)
                        for m in sorted(members, key=lambda m: -self.degree[m])[:6]
                    ],
                    "relations": rel.most_common(3),
                }
            )
        return out

    def _card(self, d: dict) -> dict:
        return {
            "id": d["id"],
            "label": d.get("label", d["id"]),
            "degree": d.get("degree", 0),
            "community": d.get("community"),
            "source_file": d.get("source_file"),
            "source_location": d.get("source_location"),
            "file_type": d.get("file_type"),
            "origin": d.get("_origin"),
        }

    # ------------------------------------------------------------------- search

    def resolve(self, needle: str) -> str | None:
        """Best node id for a user-supplied name: exact id, exact label, then
        case-insensitive substring ranked by degree."""
        if not needle:
            return None
        key = needle.strip()
        if key in self.nodes:
            return key
        low = key.lower()
        if low in self.by_label:
            return max(self.by_label[low], key=lambda n: self.degree[n])
        hits = [
            nid
            for nid, d in self.nodes.items()
            if low in str(d.get("label", "")).lower()
        ]
        if hits:
            return max(hits, key=lambda n: self.degree[n])
        return None

    def search(self, q: str, limit: int = 20) -> list[dict]:
        low = (q or "").strip().lower()
        if not low:
            return []
        exact = [self._card(self.nodes[n]) for n in self.by_label.get(low, [])]
        partial = [
            self._card(self.nodes[nid])
            for nid, d in self.nodes.items()
            if low in str(d.get("label", "")).lower() or low in nid
        ]
        seen: set[str] = set()
        out = []
        for card in sorted(exact + partial, key=lambda c: -c["degree"]):
            if card["id"] in seen:
                continue
            seen.add(card["id"])
            out.append(card)
            if len(out) >= limit:
                break
        return out

    def explain(self, needle: str, limit: int = 40) -> dict | None:
        nid = self.resolve(needle)
        if not nid:
            return None
        d = self.nodes[nid]
        conns = []
        for other, direction, data in self.adj[nid]:
            conns.append(
                {
                    "direction": direction,
                    "id": other,
                    "label": self.nodes.get(other, {}).get("label", other),
                    "relation": data.get("relation", "related"),
                    "confidence": data.get("confidence"),
                    "confidence_score": data.get("confidence_score"),
                    "context": data.get("context"),
                    "degree": self.degree.get(other, 0),
                    "community": self.nodes.get(other, {}).get("community"),
                }
            )
        conns.sort(key=lambda c: (-c["degree"], c["label"]))
        card = self._card(d)
        card["connections"] = conns[:limit]
        card["connection_count"] = len(conns)
        card["by_relation"] = Counter(c["relation"] for c in conns).most_common()
        return card

    def trace_path(self, a: str, b: str) -> dict:
        src, dst = self.resolve(a), self.resolve(b)
        if not src or not dst:
            return {"ok": False, "error": "unresolved endpoint", "a": a, "b": b}
        if src == dst:
            return {"ok": True, "hops": 0, "steps": [self._card(self.nodes[src])]}
        import networkx as nx

        try:
            nodes = nx.shortest_path(self.G, src, dst)
        except nx.NetworkXNoPath:
            return {"ok": False, "error": "no path", "a": src, "b": dst}
        steps = []
        for i, nid in enumerate(nodes):
            step = self._card(self.nodes[nid])
            if i + 1 < len(nodes):
                data = self.G.get_edge_data(nid, nodes[i + 1]) or {}
                step["edge"] = {
                    "relation": data.get("relation", "related"),
                    "confidence": data.get("confidence"),
                    "forward": data.get("_src", nid) == nid,
                }
            steps.append(step)
        return {"ok": True, "hops": len(nodes) - 1, "steps": steps}

    def query(self, question: str, budget: int = 2000, depth: int = 1) -> dict:
        """Keyword-seeded BFS, the cheap local cousin of `graphify query`.

        Seeds come from the question's tokens (highest-degree matches first),
        then we walk ``depth`` hops and trim to a token budget. No LLM, no
        network — this is the endpoint an IDE extension can hit on every
        keystroke.
        """
        tokens = [
            t for t in _WORD.findall((question or "").lower())
            if len(t) > 2 and t not in STOPWORDS
        ]
        # Rank candidates rather than taking the highest-degree ones raw: file
        # nodes and test corpora dominate by degree and would seed the traversal
        # with `tests/test_x_extractor.py` instead of the concept asked about
        # (same reasoning as analyze.god_nodes skipping file-level hubs).
        scores: dict[str, float] = {}
        for tok in sorted(tokens, key=len, reverse=True):
            for nid in self._label_index.get(tok, [])[:24]:
                d = self.nodes[nid]
                score = float(self.degree[nid]) + len(tok)
                if d.get("_origin") == "file":
                    score *= 0.35
                src = str(d.get("source_file") or "")
                if src.startswith("tests/") or "/fixtures/" in src:
                    score *= 0.2
                scores[nid] = max(scores.get(nid, 0.0), score)
        seeds = [nid for nid, _s in sorted(scores.items(), key=lambda kv: -kv[1])[:6]]
        if not seeds:
            return {"ok": False, "error": "no seed matched the question", "question": question}

        chosen: list[str] = list(seeds)
        seen = set(seeds)
        frontier = deque((s, 0) for s in seeds)
        while frontier and len(chosen) < 60:
            nid, d = frontier.popleft()
            if d >= depth:
                continue
            for other, _dir, _data in sorted(
                self.adj[nid], key=lambda e: -self.degree.get(e[0], 0)
            )[:12]:
                if other not in seen:
                    seen.add(other)
                    chosen.append(other)
                    frontier.append((other, d + 1))

        sub = self._slice(chosen)
        sub["ok"] = True
        sub["question"] = question
        sub["seeds"] = [self._card(self.nodes[s]) for s in seeds]
        sub["tokens"] = min(budget, self._estimate_tokens(sub))
        return sub

    # ------------------------------------------------------------------ subgraph

    def top_subgraph(self, limit: int = 250, community: int | None = None) -> dict:
        pool = (
            self.community_members.get(community, [])
            if community is not None
            else list(self.nodes)
        )
        chosen = sorted(pool, key=lambda n: -self.degree[n])[:limit]
        return self._slice(chosen)

    def focus_subgraph(self, needle: str, depth: int = 1, limit: int = 200) -> dict | None:
        root = self.resolve(needle)
        if not root:
            return None
        seen = {root}
        frontier = deque([(root, 0)])
        while frontier:
            nid, d = frontier.popleft()
            if d >= depth:
                continue
            for other, _dir, _data in sorted(
                self.adj[nid], key=lambda e: -self.degree.get(e[0], 0)
            )[:40]:
                if other not in seen:
                    seen.add(other)
                    frontier.append((other, d + 1))
        chosen = sorted(seen, key=lambda n: -self.degree[n])[:limit]
        if root not in chosen:
            chosen.append(root)
        out = self._slice(chosen)
        out["focus"] = root
        return out

    def _slice(self, node_ids: list[str]) -> dict:
        """Induced subgraph as node-link JSON the canvas can draw directly."""
        keep = set(node_ids)
        nodes = []
        for nid in node_ids:
            d = self.nodes.get(nid)
            if not d:
                continue
            nodes.append(
                {
                    "id": nid,
                    "label": str(d.get("label", nid))[:80],
                    "community": d.get("community"),
                    "degree": d.get("degree", 0),
                    "file": d.get("source_file"),
                    "loc": d.get("source_location"),
                    "origin": d.get("_origin"),
                    "size": 4 + min(22, math.sqrt(max(0, d.get("degree", 0))) * 1.5),
                }
            )
        links = []
        seen_pairs = set()
        for nid in node_ids:
            for other, direction, data in self.adj.get(nid, []):
                if other not in keep:
                    continue
                src, tgt = (nid, other) if direction == "out" else (other, nid)
                pair = (src, tgt, data.get("relation"))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                links.append(
                    {
                        "source": src,
                        "target": tgt,
                        "relation": data.get("relation", "related"),
                        "confidence": data.get("confidence"),
                    }
                )
        return {"nodes": nodes, "links": links}

    @staticmethod
    def _estimate_tokens(sub: dict) -> int:
        return int(len(json.dumps(sub, separators=(",", ":"))) / 4)


_STORE: GraphStore | None = None
_LOCK = threading.Lock()


def store(graph_path: str | Path | None = None) -> GraphStore:
    """Process-wide singleton: the graph is parsed once, then served from RAM."""
    global _STORE
    with _LOCK:
        if _STORE is None:
            path = graph_path or _default_graph()
            _STORE = GraphStore(path)
        return _STORE


def _default_graph() -> Path:
    return Path("graphify-out") / "graph.json"
