"""generate(...) → GRAPH_REPORT.md string, mirroring `report.py` row."""
from __future__ import annotations
from datetime import date


def generate(G, communities, cohesion, labels, gods, surprises, detection,
             token_cost, root, suggested_questions=None, **_ignored) -> str:
    god_lines = [f"1. `{g['label']}` — degree {g['degree']}" for g in gods[:7]] or ["- none"]
    comm_lines = [
        f"- **#{c} {labels.get(c, '')}** — {len(m)} nodes, cohesion {cohesion.get(c, 0):.2f}"
        for c, m in sorted(communities.items())
    ] or ["- none"]
    surp_lines = [
        f"- `{s['source']}` --{s['relation']}--> `{s['target']}` ({s['confidence']})"
        for s in surprises
    ] or ["- none"]
    lines = [
        f"# Graph report — {root}",
        f"_generated {date.today().isoformat()} by minigraph (teaching pipeline)_",
        "",
        f"- Nodes: {G.number_of_nodes()} · Edges: {G.number_of_edges()}",
        f"- Communities: {len(communities)}",
        f"- Token cost: {token_cost.get('input', 0):,} input · {token_cost.get('output', 0):,} output",
        f"- Files scanned: {detection.get('total_files', 0)} ({detection.get('total_words', 0):,} words)",
        "",
        "## God nodes",
        "",
        *god_lines,
        "",
        "## Communities",
        "",
        *comm_lines,
        "",
        "## Surprising connections",
        "",
        *surp_lines,
    ]
    if suggested_questions:
        lines += ["", "## Suggested questions", "",
                  *[f"- {q['question']}" for q in suggested_questions]]
    return "\n".join(lines) + "\n"
