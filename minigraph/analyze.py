"""Analyze helpers — same names as ARCHITECTURE.md `analyze.py` row."""
from __future__ import annotations
import networkx as nx


def god_nodes(G: nx.Graph, top_n: int = 10) -> list[dict]:
    return [{"id": nid, "label": G.nodes[nid].get("label", nid), "degree": d}
            for nid, d in sorted(G.degree(), key=lambda x: -x[1])[:top_n]]


def surprising_connections(G: nx.Graph, communities: dict[int, list[str]]) -> list[dict]:
    """Cross-community edges touching a god node: the doc's 'surprise' signal."""
    of = {nid: cid for cid, members in communities.items() for nid in members}
    gods = {g["id"] for g in god_nodes(G, top_n=max(5, G.number_of_nodes() // 10))}
    out = []
    for u, v, d in G.edges(data=True):
        if of.get(u) != of.get(v) and (u in gods or v in gods):
            out.append({"source": u, "target": v, "relation": d.get("relation"),
                        "confidence": d.get("confidence")})
    return out[:10]


def suggest_questions(G: nx.Graph, communities, labels: dict[int, str]) -> list[dict]:
    return [{"question": f"What holds community '{labels.get(c, c)}' together?",
             "type": "cohesion"} for c in list(communities)[:5]]
