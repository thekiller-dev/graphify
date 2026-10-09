"""extract(paths, *, root) → {nodes, edges}. Stdlib-AST stand-in for tree-sitter.

Same two-pass idea as the real extractor:
  1. per-file structure: file/class/function nodes, `calls` + `defines` edges
  2. cross-file resolution: an imported name that a sibling file defines
     becomes an INFERRED `uses` edge (the doc's "call-graph second pass").
"""
from __future__ import annotations
import ast
from pathlib import Path


def _nid(rel: str, *parts: str) -> str:
    return "/".join([rel.replace("/", "::").removesuffix(".py")] + list(parts))


def extract_python(path: Path, *, root: Path | None = None) -> dict:
    root = Path(root) if root else path.parent
    rel = str(Path(path).resolve().relative_to(root.resolve()))
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(path))
    nodes = [{"id": _nid(rel), "label": rel, "source_file": rel,
              "source_location": "L1", "file_type": "code"}]
    edges: list[dict] = []
    defined: dict[str, str] = {}          # top-level name → node id
    calls: list[tuple[str, str, str]] = []  # (caller_id, name, location)
    imports: list[tuple[str, str]] = []     # (caller_id, imported name)

    for stmt in tree.body:
        if isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            nid = _nid(rel, stmt.name)
            kind = "class" if isinstance(stmt, ast.ClassDef) else "function"
            nodes.append({"id": nid, "label": stmt.name, "source_file": rel,
                          "source_location": f"L{stmt.lineno}", "file_type": "code",
                          "kind": kind})
            edges.append({"source": _nid(rel), "target": nid, "relation": "defines",
                          "confidence": "EXTRACTED", "source_file": rel})
            defined[stmt.name] = nid
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    calls.append((nid, sub.func.id, f"L{sub.lineno}"))
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    calls.append((nid, sub.func.attr, f"L{sub.lineno}"))
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in stmt.names]
            for nm in names:
                imports.append((_nid(rel), nm.split(".")[0]))
    for caller, name, loc in calls:
        if name in defined and defined[name] != caller:
            edges.append({"source": caller, "target": defined[name], "relation": "calls",
                          "confidence": "EXTRACTED", "source_file": rel,
                          "source_location": loc})
    ex = {"nodes": nodes, "edges": edges, "_defined": defined, "_imports": imports,
          "_rel": rel}
    return ex


def extract(paths: list[Path], *, root: Path | None = None, **_ignored) -> dict:
    per = [extract_python(p, root=root) for p in paths]
    defined_globally: dict[str, list[str]] = {}
    for ex in per:
        for name, nid in ex["_defined"].items():
            defined_globally.setdefault(name, []).append(nid)
    nodes, edges = [], []
    for ex in per:
        nodes.extend({k: v for k, v in n.items() if not k.startswith("_")} for n in ex["nodes"])
        edges.extend(ex["edges"])
        # pass 2: imported name defined elsewhere → INFERRED uses edge
        for caller, name in ex["_imports"]:
            for target in defined_globally.get(name, []):
                if target.split("::")[0] != caller.split("::")[0]:
                    edges.append({"source": caller, "target": target,
                                  "relation": "uses", "confidence": "INFERRED",
                                  "confidence_score": 0.85, "source_file": ex["_rel"]})
    return {"nodes": nodes, "edges": edges}


def collect_files(target: Path, **_ignored) -> list[Path]:
    from minigraph.detect import CODE, SKIP
    return sorted(p for p in Path(target).rglob("*")
                  if p.is_file() and p.suffix in CODE
                  and not any(part in SKIP for part in p.parts))
