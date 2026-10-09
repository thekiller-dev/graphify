"""to_json(G, communities, path) — NetworkX node-link, like the real exporter."""
from __future__ import annotations
import json
from pathlib import Path
import networkx as nx


def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str,
            *, community_labels: dict[int, str] | None = None, **_ignored) -> bool:
    H = G.copy()
    for cid, members in communities.items():
        for nid in members:
            H.nodes[nid]["community"] = cid
    data = nx.node_link_data(H, edges="links")
    data["communities"] = {str(c): {"label": (community_labels or {}).get(c, ""),
                                    "size": len(m)} for c, m in communities.items()}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(data, indent=1), encoding="utf-8")
    return True
