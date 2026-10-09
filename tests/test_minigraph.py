"""minigraph: the teaching pipeline keeps its ARCHITECTURE.md contract."""
from __future__ import annotations

import json
from pathlib import Path

from minigraph.detect import detect
from minigraph.extract import extract
from minigraph.build import build
from minigraph.cluster import cluster, cohesion_score
from minigraph.analyze import god_nodes
from minigraph.report import generate
from minigraph.export import to_json
from minigraph.validate import validate_extraction

A = '''
class Foo:
    def bar(self):
        return helper()

def helper():
    return 41 + 1
'''
B = '''
from a import Foo

def use():
    f = Foo()
    return f.bar()
'''


def _tree(tmp: Path) -> Path:
    src = tmp / "src"
    src.mkdir()
    (src / "a.py").write_text(A, encoding="utf-8")
    (src / "b.py").write_text(B, encoding="utf-8")
    return src


def test_pipeline_end_to_end(tmp_path):
    src = _tree(tmp_path)
    summary = detect(src)
    assert summary["total_files"] == 2 and len(summary["files"]["code"]) == 2

    extraction = extract([src / "a.py", src / "b.py"], root=src)
    assert validate_extraction(extraction) == []

    G = build([extraction], root=src)
    assert G.has_node("a/Foo") and G.has_node("b/use")
    relations = {d["relation"] for _, _, d in G.edges(data=True)}
    assert "defines" in relations and "calls" in relations
    # pass 2: b imports Foo defined in a → INFERRED uses edge
    assert any(d["relation"] == "uses" and d["confidence"] == "INFERRED"
               for _, _, d in G.edges(data=True))

    communities = cluster(G)
    assert 0 in communities
    assert len(communities[0]) >= max(len(m) for m in communities.values())
    cohesion = {c: cohesion_score(G, m) for c, m in communities.items()}
    labels = {c: f"g{c}" for c in communities}
    gods = god_nodes(G)
    assert gods and gods[0]["degree"] >= 1

    md = generate(G, communities, cohesion, labels, gods, [], summary,
                  {"input": 0, "output": 0}, str(src))
    assert "## God nodes" in md and "## Communities" in md

    out = tmp_path / "graph.json"
    assert to_json(G, communities, str(out), community_labels=labels) is True
    data = json.loads(out.read_text())
    assert "links" in data and "communities" in data
    assert all("community" in n for n in data["nodes"])


def test_validate_rejects_bad_confidence():
    bad = {"nodes": [{"id": "x", "label": "X"}],
           "edges": [{"source": "x", "target": "x", "relation": "calls",
                      "confidence": "MAYBE"}]}
    errs = validate_extraction(bad)
    assert any("confidence" in e for e in errs)
