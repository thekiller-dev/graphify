"""cluster(G) → {community_id: [node_ids]}. Greedy modularity stand-in for Leiden.

Same contract as the doc: the graph is not mutated, ids are renumbered so that
0 is the largest community.
"""
from __future__ import annotations
import networkx as nx


def cluster(G: nx.Graph, **_ignored) -> dict[int, list[str]]:
    if G.number_of_nodes() == 0:
        return {}
    comms = list(nx.algorithms.community.greedy_modularity_communities(G))
    comms = [sorted(c) for c in comms]
    comms.sort(key=lambda c: (-len(c), c[0]))
    return {i: members for i, members in enumerate(comms)}


def cohesion_score(G: nx.Graph, members: list[str]) -> float:
    sub = G.subgraph(members)
    n = len(members)
    if n < 2:
        return 1.0
    return sub.number_of_edges() / (n * (n - 1) / 2)
