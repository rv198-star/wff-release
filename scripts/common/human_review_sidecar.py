"""Non-blocking dispatch for the v1.6 Human Review sidecar."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable

from common.wff_core_runtime import capability_binding_report


SIDECAR_ENV = "WFF_HUMAN_REVIEW_SIDECAR"
JOB_SCHEMA = "wff.human-review-sidecar-job.v1"


def _release_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sidecar_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    configured = os.environ.get(SIDECAR_ENV, "").strip().lower()
    if configured in {"1", "true", "yes", "on"}:
        return True
    if configured in {"0", "false", "no", "off"}:
        return False
    return (_release_root() / "SKILL_INSTALL_PACK_MANIFEST.json").is_file()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _targets(case_root: Path) -> list[dict[str, str]]:
    from release.run_reader_translation_lane import discover_targets

    return [
        {
            "kind": kind,
            "label": label,
            "path": path.resolve().relative_to(case_root).as_posix(),
            "sha256": sha256_file(path),
        }
        for kind, label, path in discover_targets(case_root, "zh-CN")
    ]


def _map_sources(case_root: Path) -> list[dict[str, str]]:
    from common.human_semantic_projection import projection_source_refs
    from common.review_map_generation import review_map_sources

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for kind in ("p1", "p2"):
        for path in review_map_sources(case_root, kind, require=False):
            relative = path.resolve().relative_to(case_root).as_posix()
            if relative in seen:
                continue
            seen.add(relative)
            rows.append(
                {
                    "kind": kind,
                    "path": relative,
                    "sha256": sha256_file(path),
                }
            )
    try:
        projection_refs = projection_source_refs(case_root, "action-card-set")
    except ValueError:
        projection_refs = []
    for ref in projection_refs:
        if ref in seen:
            continue
        path = (case_root / ref).resolve()
        seen.add(ref)
        rows.append(
            {
                "kind": "p3-human-projection",
                "path": ref,
                "sha256": sha256_file(path),
            }
        )
    return rows


def _invalidate_stale_publication(case_root: Path, targets: list[dict[str, str]]) -> None:
    publication = case_root / ".wff" / "human-review-sidecar" / "publication.json"
    if not publication.is_file():
        return
    try:
        previous = json.loads(publication.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        previous = {}
    current = {row["path"]: row["sha256"] for row in targets}
    if previous.get("target_hashes") == current:
        return
    for path in (
        case_root / "human-review" / "index.html",
        case_root / "human-review" / "dossier-manifest.json",
    ):
        path.unlink(missing_ok=True)
    publication.unlink(missing_ok=True)


def dispatch_human_review_sidecar(
    output_dir: Path,
    phase: str,
    *,
    explicit: bool | None = None,
    launcher: Callable[..., Any] = subprocess.Popen,
) -> dict[str, Any]:
    """Queue current phase readers and return without waiting for generation."""
    if not sidecar_enabled(explicit):
        return {"status": "disabled", "phase": phase, "non_blocking": True}
    try:
        core_binding = capability_binding_report(
            "human-review",
            required_contracts=(
                "artifact-identity-contract",
                "evidence-contract",
                "claim-state-contract",
                "agentic-boundary-contract",
            ),
        )
        phase_root = output_dir.resolve()
        case_root = phase_root.parent
        targets = _targets(case_root)
        map_sources = _map_sources(case_root)
        if not targets:
            return {"status": "not-applicable", "phase": phase, "non_blocking": True}
        _invalidate_stale_publication(case_root, [*targets, *map_sources])
        identity = hashlib.sha256(
            json.dumps(
                {"phase": phase, "targets": targets, "map_sources": map_sources},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:20]
        queue_root = case_root / ".wff" / "human-review-sidecar"
        job_path = queue_root / "jobs" / f"{phase}-{identity}.json"
        if job_path.is_file():
            existing = json.loads(job_path.read_text(encoding="utf-8"))
            if existing.get("status") in {"pending", "running", "completed"}:
                return {
                    "status": "already-queued",
                    "phase": phase,
                    "job": str(job_path),
                    "non_blocking": True,
                }
        _atomic_json(
            job_path,
            {
                "schema_version": JOB_SCHEMA,
                "job_id": identity,
                "phase": phase,
                "case_root": str(case_root),
                "targets": targets,
                "map_sources": map_sources,
                "attempts": 0,
                "max_attempts": 3,
                "status": "pending",
                "core_contract_binding": core_binding,
            },
        )
        worker = _release_root() / "scripts" / "common" / "run_human_review_sidecar_worker.py"
        log_root = queue_root / "logs"
        log_root.mkdir(parents=True, exist_ok=True)
        stdout = (log_root / "worker.stdout.log").open("ab")
        stderr = (log_root / "worker.stderr.log").open("ab")
        try:
            process = launcher(
                [sys.executable, str(worker), "--case-root", str(case_root)],
                cwd=str(_release_root()),
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                close_fds=True,
            )
        finally:
            stdout.close()
            stderr.close()
        return {
            "status": "queued",
            "phase": phase,
            "job": str(job_path),
            "worker_pid": int(getattr(process, "pid", 0) or 0),
            "non_blocking": True,
            "core_contract_binding": core_binding,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "phase": phase,
            "detail": str(exc),
            "non_blocking": True,
        }
