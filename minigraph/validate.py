"""Schema gate before build(), mirroring ARCHITECTURE.md `validate.py` row.

validate_extraction(data) → list of error strings (empty == valid).
"""
from __future__ import annotations

CONFIDENCES = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}


def validate_extraction(data: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return ["extraction must be a dict"]
    nodes, edges = data.get("nodes"), data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["extraction needs 'nodes' and 'edges' lists"]
    ids = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or not n.get("id") or not n.get("label"):
            errs.append(f"node {i}: needs 'id' and 'label'")
            continue
        ids.add(n["id"])
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            errs.append(f"edge {i}: not a dict")
            continue
        for k in ("source", "target", "relation", "confidence"):
            if not e.get(k):
                errs.append(f"edge {i}: missing '{k}'")
        if e.get("confidence") not in CONFIDENCES:
            errs.append(f"edge {i}: confidence must be one of {sorted(CONFIDENCES)}")
        if e.get("source") not in ids or e.get("target") not in ids:
            errs.append(f"edge {i}: endpoints must exist in nodes")
    return errs


def assert_valid(data: dict) -> None:
    errs = validate_extraction(data)
    if errs:
        raise ValueError("invalid extraction: " + "; ".join(errs))
