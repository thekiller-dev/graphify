"""Hosted build jobs — the ARCHITECTURE.md pipeline, server-side.

The doc's contract, verbatim:

    detect() → extract() → build() → cluster() → analyze helpers
             → report.generate() → export.to_json()

A Grafik workspace used to require a ``graph.json`` brought by hand. These
jobs let a tenant hand over *sources* (a server path or an uploaded archive)
and get back a workspace: graph, GRAPH_REPORT.md, optional wiki — built by the
real engine, in a worker thread, with progress streamed over SSE.

Pass 1 only (tree-sitter AST: free, local, deterministic). Passes 2 and 3 of
``docs/how-it-works.md`` (faster-whisper transcription, LLM subagents over
docs/images) need backends a hosted default must never enable silently; when
they are wanted, they slot in between ``detect`` and ``build`` here.

Safety notes, earned the hard way elsewhere in this codebase:
  * archives unpack through a zip-slip / tar-slip guard into the data root;
  * ``extract()`` is always called with an explicit ``root`` (ARCHITECTURE.md:
    omitting it anchors node ids to the wrong directory);
  * jobs live in a process-local dict — a restart drops running jobs, which is
    honest: nothing half-built is ever registered as a workspace.
"""
from __future__ import annotations

import os
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path

MAX_ENTRIES = 20_000

_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()
_EVENT_SEQ = 0


def _bump() -> None:
    global _EVENT_SEQ
    _EVENT_SEQ += 1


def events_seq() -> int:
    """Monotonic counter the SSE stream polls to notice job transitions."""
    return _EVENT_SEQ


def jobs_for(user_id: str) -> list[dict]:
    with _LOCK:
        rows = [dict(j) for j in _JOBS.values() if j["owner"] == user_id]
    return sorted(rows, key=lambda j: j["created_at"], reverse=True)


def get(job_id: str) -> dict | None:
    with _LOCK:
        return dict(_JOBS.get(job_id, {})) or None


def _set_stage(job: dict, stage: str) -> None:
    with _LOCK:
        job["stage"] = stage
        job["updated_at"] = time.time()
        _bump()


# ------------------------------------------------------------------ archives


def unpack_archive(archive: Path, dest: Path, max_bytes: int) -> int:
    """Unpack .zip/.tar.* under ``dest``, refusing slips and plan overruns.

    Returns total bytes written. Every member path is resolved and checked
    against ``dest`` before a single byte lands (zip-slip / tar-slip), and
    symlinks are dropped rather than followed.
    """
    dest.mkdir(parents=True, exist_ok=True)
    base = dest.resolve()
    total = 0
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            if len(infos) > MAX_ENTRIES:
                raise ValueError(f"archive has more than {MAX_ENTRIES} entries")
            for info in infos:
                target = (base / info.filename).resolve()
                if target != base and not target.is_relative_to(base):
                    raise ValueError(f"unsafe archive path: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                total += info.file_size
                if total > max_bytes:
                    raise ValueError("archive exceeds the plan upload cap")
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        return total
    import tarfile

    with tarfile.open(archive, "r:*") as t:
        for member in t:
            target = (base / member.name).resolve()
            if target != base and not target.is_relative_to(base):
                raise ValueError(f"unsafe archive path: {member.name}")
            if member.issym() or member.islnk():
                continue
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            total += member.size
            if total > max_bytes:
                raise ValueError("archive exceeds the plan upload cap")
            target.parent.mkdir(parents=True, exist_ok=True)
            with t.extractfile(member) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    return total


# ------------------------------------------------------------------ pipeline


def _hub_label(G, members: list[str]) -> str:
    best, degree = None, -1
    for nid in members:
        d = G.degree(nid)
        if d > degree:
            degree, best = d, nid
    if best is None:
        return "groupe"
    return str(G.nodes[best].get("label") or best)[:60]


def run_pipeline(source: Path, out: Path, *, wiki: bool, on_stage) -> dict:
    """One documented pass over a source tree. ``on_stage(name)`` reports progress."""
    from graphify.detect import detect
    from graphify.extract import extract
    from graphify.build import build
    from graphify.cluster import cluster, cohesion_score
    from graphify.analyze import god_nodes, surprising_connections, suggest_questions
    from graphify.report import generate
    from graphify.export import to_json

    on_stage("detect")
    summary = detect(source)
    code = [Path(p) for p in summary["files"].get("code", [])]
    if not code:
        raise ValueError("aucun fichier code détecté dans la source")

    on_stage("extract")
    extraction = extract(code, root=source)  # root explicite, cf. ARCHITECTURE.md

    on_stage("build")
    G = build([extraction], root=source)
    if G.number_of_nodes() == 0:
        raise ValueError("le graphe construit est vide")

    on_stage("cluster")
    communities = cluster(G)
    cohesion = {cid: cohesion_score(G, members) for cid, members in communities.items()}
    labels = {cid: _hub_label(G, members) for cid, members in communities.items()}

    on_stage("analyze")
    gods = god_nodes(G)
    surprises = surprising_connections(G)
    questions = suggest_questions(G, communities, labels)

    on_stage("report")
    markdown = generate(
        G, communities, cohesion, labels, gods, surprises, summary,
        {"input": 0, "output": 0},  # pass 1 only: zero LLM tokens, by design
        str(source), suggested_questions=questions,
    )

    on_stage("export")
    out.mkdir(parents=True, exist_ok=True)
    graph_path = out / "graph.json"
    to_json(G, communities, str(graph_path), community_labels=labels)
    (out / "GRAPH_REPORT.md").write_text(markdown, encoding="utf-8")
    if wiki:
        from graphify.wiki import to_wiki
        to_wiki(G, communities, out / "wiki", labels, cohesion, gods)

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "communities": len(communities),
        "words": summary.get("total_words", 0),
        "files": len(code),
        "graph": str(graph_path),
        "report": str(out / "GRAPH_REPORT.md"),
        "wiki": str(out / "wiki") if wiki else None,
    }


# --------------------------------------------------------------------- jobs


def start_build(
    *,
    owner: str,
    name: str,
    source: Path,
    wiki: bool = False,
    workspace_factory=None,
    out_root: Path | None = None,
) -> dict:
    """Queue a build. ``workspace_factory(job, result) -> ws_id`` runs on success
    (plan caps checked by the caller) so a finished build becomes a workspace."""
    job = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "owner": owner,
        "source": str(source),
        "status": "running",
        "stage": "queued",
        "wiki": bool(wiki),
        "error": None,
        "workspace_error": None,
        "workspace_id": None,
        "result": None,
        "created_at": time.time(),
        "updated_at": time.time(),
        "out_root": str(out_root) if out_root else None,
    }
    with _LOCK:
        _JOBS[job["id"]] = job
        _bump()

    def worker() -> None:
        # Everything inside the try: a boot failure must mark the job failed,
        # never leave it "running" forever (that bug shipped once, briefly).
        try:
            base = Path(job["out_root"]) if job["out_root"] else Path.cwd() / "builds-out"
            out = base / job["id"]
            result = run_pipeline(Path(job["source"]), out, wiki=job["wiki"],
                                  on_stage=lambda st: _set_stage(job, st))
            job["result"] = result
            if workspace_factory is not None:
                try:
                    job["workspace_id"] = workspace_factory(job, result)
                except Exception as exc:  # plan caps & co: job succeeded, ws didn't
                    job["workspace_error"] = str(exc)
            job["status"] = "done"
            _set_stage(job, "done")
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            _set_stage(job, "failed")

    threading.Thread(target=worker, daemon=True, name=f"build-{job['id']}").start()
    return dict(job)
