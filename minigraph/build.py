"""build(extractions) → nx.Graph, mirroring ARCHITECTURE.md `build.py` row."""
from __future__ import annotations
import networkx as nx
from minigraph.validate import assert_valid


def build(extractions: list[dict], *, root=None, **_ignored) -> nx.Graph:
    G = nx.Graph()
    for ex in extractions:
        assert_valid(ex)
        for n in ex["nodes"]:
            G.add_node(n["id"], **{k: v for k, v in n.items() if k != "id"})
        for e in ex["edges"]:
            G.add_edge(e["source"], e["target"],
                       relation=e["relation"], confidence=e["confidence"],
                       confidence_score=e.get("confidence_score"),
                       source_file=e.get("source_file"))
    return G
