"""detect(root) → scan summary dict. Mirrors ARCHITECTURE.md `detect.py` row."""
from __future__ import annotations
from pathlib import Path

CODE = {".py"}            # teaching subset; graphify ships 37 grammars
DOCS = {".md", ".txt", ".rst"}
SKIP = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache"}


def detect(root: Path, **_ignored) -> dict:
    root = Path(root).resolve()
    files: dict[str, list[str]] = {"code": [], "document": [], "paper": [], "image": []}
    total_words = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP for part in p.parts):
            continue
        if p.suffix in CODE:
            files["code"].append(str(p))
        elif p.suffix in DOCS:
            files["document"].append(str(p))
        else:
            continue
        try:
            total_words += len(p.read_text(encoding="utf-8", errors="replace").split())
        except OSError:
            pass
    return {
        "files": files,
        "total_files": sum(len(v) for v in files.values()),
        "total_words": total_words,
        "scan_root": str(root),
        "warning": None,
    }
