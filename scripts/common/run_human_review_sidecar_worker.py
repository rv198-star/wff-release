#!/usr/bin/env python3
"""Consume queued v1.6 Human Review jobs with bounded retries."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS_ROOT))

from common.human_review_sidecar import _atomic_json, _map_sources, sha256_file
from release.assemble_v16_human_review_dossier import AssemblyError, assemble_v16_dossier
from release.run_human_review_map_lane import run_map_lane
from release.run_human_semantic_projection_lane import run_projection_lane
from release.run_reader_translation_lane import run_lane


def _job_targets_current(case_root: Path, job: dict[str, Any]) -> bool:
    for row in [*job.get("targets", []), *job.get("map_sources", [])]:
        path = (case_root / str(row.get("path") or "")).resolve()
        if not path.is_file() or not path.is_relative_to(case_root):
            return False
        if sha256_file(path) != row.get("sha256"):
            return False
    return True


def _current_hashes(case_root: Path) -> dict[str, str]:
    from release.run_reader_translation_lane import discover_targets

    hashes = {
        path.resolve().relative_to(case_root).as_posix(): sha256_file(path)
        for _kind, _label, path in discover_targets(case_root, "zh-CN")
    }
    hashes.update({row["path"]: row["sha256"] for row in _map_sources(case_root)})
    return hashes


def _translation_succeeded(case_root: Path, job: dict[str, Any]) -> bool:
    manifest_path = case_root / "reader-translation-manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    accepted = {
        str(Path(str(row.get("canonical") or "")).resolve()): row
        for row in manifest.get("targets", [])
        if isinstance(row, dict)
        and row.get("status") == "generated"
        and row.get("verdict") == "pass"
    }
    return all(str((case_root / row["path"]).resolve()) in accepted for row in job.get("targets", []))


def _process_job(case_root: Path, job_path: Path) -> None:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if job.get("status") not in {"pending", "retry"}:
        return
    if not _job_targets_current(case_root, job):
        job["status"] = "obsolete"
        job["detail"] = "source snapshot changed before execution"
        _atomic_json(job_path, job)
        return

    while int(job.get("attempts", 0)) < int(job.get("max_attempts", 3)):
        job["attempts"] = int(job.get("attempts", 0)) + 1
        job["status"] = "running"
        _atomic_json(job_path, job)
        try:
            release_root = Path(__file__).resolve().parents[2]
            manifest = run_lane(
                case_root,
                emit_script=release_root / "scripts" / "common" / "emit_reader_translation.py",
                locale="zh-CN",
            )
            job["reader_evidence_state"] = manifest.get("reader_evidence_state")
        except Exception as exc:
            job["detail"] = str(exc)

        if not _job_targets_current(case_root, job):
            job["status"] = "obsolete"
            job["detail"] = "source snapshot changed during generation"
            _atomic_json(job_path, job)
            return
        if _translation_succeeded(case_root, job):
            release_root = Path(__file__).resolve().parents[2]
            try:
                map_manifest = run_map_lane(
                    case_root,
                    emit_script=release_root / "scripts" / "common" / "review_map_generation.py",
                    locale="zh-CN",
                )
            except Exception as exc:
                map_manifest = {"status": "failed"}
                job["detail"] = f"review-map lane failed: {exc}"
            try:
                projection_manifest = run_projection_lane(
                    case_root,
                    emit_script=release_root / "scripts" / "common" / "human_semantic_projection.py",
                    locale="zh-CN",
                )
            except Exception as exc:
                projection_manifest = {"status": "failed"}
                job["detail"] = f"human semantic projection lane failed: {exc}"
            job["review_map_status"] = map_manifest.get("status")
            job["semantic_projection_status"] = projection_manifest.get("status")
            job["semantic_projection_decision_quality_status"] = projection_manifest.get(
                "decision_quality_status"
            )
            if (
                map_manifest.get("status") == "generated"
                and projection_manifest.get("status") == "generated"
            ):
                dossier_status = "pending-later-phase"
                try:
                    report = assemble_v16_dossier(case_root)
                    dossier_status = "generated" if report.get("dossier_ready") else "not-ready"
                except AssemblyError as exc:
                    job["dossier_detail"] = str(exc)
                job["status"] = "completed"
                job["dossier_status"] = dossier_status
                _atomic_json(job_path, job)
                if dossier_status == "generated":
                    _atomic_json(
                        case_root / ".wff" / "human-review-sidecar" / "publication.json",
                        {
                            "schema_version": "wff.human-review-sidecar-publication.v1",
                            "target_hashes": _current_hashes(case_root),
                            "dossier": "human-review/index.html",
                            "decision_quality_status": projection_manifest.get(
                                "decision_quality_status"
                            ),
                        },
                    )
                return
            if map_manifest.get("status") != "generated":
                job.setdefault("detail", "Agentic P1/P2 review-map generation did not pass")
            else:
                job.setdefault("detail", "human semantic projection generation did not pass")
        job["status"] = "retry"
        _atomic_json(job_path, job)
        if int(job["attempts"]) < int(job.get("max_attempts", 3)):
            time.sleep(min(2 ** (int(job["attempts"]) - 1), 2))

    job["status"] = "failed"
    job.setdefault("detail", "reader translation did not pass within three attempts")
    _atomic_json(job_path, job)


def run_worker(case_root: Path) -> dict[str, Any]:
    root = case_root.resolve()
    queue_root = root / ".wff" / "human-review-sidecar"
    lock = queue_root / "worker.lock"
    queue_root.mkdir(parents=True, exist_ok=True)
    for _attempt in range(2):
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                owner_pid = int(lock.read_text(encoding="utf-8").strip())
                os.kill(owner_pid, 0)
            except (OSError, ValueError):
                lock.unlink(missing_ok=True)
                continue
            return {"status": "already-running", "worker_pid": owner_pid}
        else:
            os.write(descriptor, str(os.getpid()).encode("ascii"))
            os.close(descriptor)
            break
    else:
        return {"status": "lock-unavailable"}
    processed = 0
    try:
        idle_scans = 0
        while idle_scans < 2:
            pending = []
            for job_path in sorted((queue_root / "jobs").glob("*.json")):
                status = json.loads(job_path.read_text(encoding="utf-8")).get("status")
                if status in {"pending", "retry"}:
                    pending.append(job_path)
            if not pending:
                idle_scans += 1
                time.sleep(0.2)
                continue
            idle_scans = 0
            for job_path in pending:
                before = json.loads(job_path.read_text(encoding="utf-8")).get("status")
                _process_job(root, job_path)
                after = json.loads(job_path.read_text(encoding="utf-8")).get("status")
                if before != after:
                    processed += 1
        return {"status": "completed", "processed": processed}
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run_worker(args.case_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
