"""Run the teaching pipeline on a directory: python -m minigraph.selfdemo [dir]"""
from __future__ import annotations
import sys
from pathlib import Path

from minigraph.detect import detect
from minigraph.extract import extract, collect_files
from minigraph.build import build
from minigraph.cluster import cluster, cohesion_score
from minigraph.analyze import god_nodes, surprising_connections, suggest_questions
from minigraph.report import generate
from minigraph.export import to_json


def main(argv: list[str]) -> int:
    root = Path(argv[0] if argv else ".").resolve()
    summary = detect(root)
    files = [Path(p) for p in summary["files"]["code"]] or collect_files(root)
    if not files:
        print("no .py files found under", root)
        return 1
    extraction = extract(files, root=root)          # ARCHITECTURE.md: always pass root
    G = build([extraction], root=root)
    communities = cluster(G)
    cohesion = {c: cohesion_score(G, m) for c, m in communities.items()}
    labels = {c: (G.nodes[m[0]].get("label", m[0]) if m else "?") for c, m in communities.items()}
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)
    questions = suggest_questions(G, communities, labels)
    md = generate(G, communities, cohesion, labels, gods, surprises, summary,
                  {"input": 0, "output": 0}, str(root), suggested_questions=questions)
    out = Path("minigraph-out")
    to_json(G, communities, str(out / "graph.json"), community_labels=labels)
    (out / "GRAPH_REPORT.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"[minigraph] wrote {out / 'graph.json'} and {out / 'GRAPH_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
