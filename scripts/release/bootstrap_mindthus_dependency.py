#!/usr/bin/env python3
"""
Validate or bootstrap the pinned Mindthus runtime dependency.

Release packs carry a curated Mindthus release payload. The source checkout is
only a local cache/fallback for refreshing that payload.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_ROOT = REPO_ROOT / "runtime-deps" / "mindthus"
DEFAULT_LOCK_PATH = DEFAULT_REFERENCE_ROOT / "mindthus.lock.json"
DEFAULT_REPORT_PATH = DEFAULT_REFERENCE_ROOT / "bootstrap-report.json"

REQUIRED_LOCK_KEYS = ("name", "repo", "tag", "commit", "source_dir")
OPTIONAL_LOCK_KEYS = ("release_dir",)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def load_lock(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Mindthus lock must be a JSON object: {path}")

    missing = [key for key in REQUIRED_LOCK_KEYS if key not in data]
    if missing:
        raise ValueError(f"Mindthus lock is missing required keys: {', '.join(missing)}")

    lock: dict[str, str] = {}
    for key in (*REQUIRED_LOCK_KEYS, *OPTIONAL_LOCK_KEYS):
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Mindthus lock key must be a non-empty string: {key}")
        lock[key] = value
    return lock


def source_path(reference_root: Path, lock: Mapping[str, str]) -> Path:
    source_dir = lock["source_dir"]
    if source_dir in ("", ".", "..") or "/" in source_dir or "\\" in source_dir:
        raise ValueError("Mindthus lock source_dir must be a simple child directory name")
    return reference_root / source_dir


def release_path(reference_root: Path, lock: Mapping[str, str]) -> Path:
    release_dir = lock.get("release_dir", "release")
    if release_dir in ("", ".", "..") or "/" in release_dir or "\\" in release_dir:
        raise ValueError("Mindthus lock release_dir must be a simple child directory name")
    return reference_root / release_dir


def base_report(reference_root: Path, lock: Mapping[str, str]) -> dict[str, Any]:
    source_dir = source_path(reference_root, lock)
    release_dir = release_path(reference_root, lock)
    return {
        "name": lock["name"],
        "repo": lock["repo"],
        "tag": lock["tag"],
        "expected_commit": lock["commit"],
        "reference_root": str(reference_root),
        "source_dir": str(source_dir),
        "release_dir": str(release_dir),
        "checked_at": utc_now_iso(),
    }


def inspect_mindthus_release_payload(reference_root: Path, lock: Mapping[str, str]) -> dict[str, Any]:
    report = base_report(reference_root, lock)
    release_dir = Path(report["release_dir"])
    metadata_path = release_dir / "mindthus-release.json"

    if not release_dir.exists():
        report.update(
            {
                "status": "release_missing",
                "actual_commit": None,
                "message": "Mindthus release payload is missing.",
            }
        )
        return report

    if not release_dir.is_dir():
        report.update(
            {
                "status": "release_invalid",
                "actual_commit": None,
                "message": "Mindthus release payload path exists but is not a directory.",
            }
        )
        return report

    if (release_dir / ".git").exists():
        report.update(
            {
                "status": "release_invalid",
                "actual_commit": None,
                "message": "Mindthus release payload must not contain a git checkout.",
            }
        )
        return report

    if (release_dir / "tests").exists():
        report.update(
            {
                "status": "release_invalid",
                "actual_commit": None,
                "message": "Mindthus release payload must not contain upstream tests.",
            }
        )
        return report

    if not metadata_path.exists():
        report.update(
            {
                "status": "release_invalid",
                "actual_commit": None,
                "message": "Mindthus release payload metadata is missing.",
            }
        )
        return report

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.update(
            {
                "status": "release_invalid",
                "actual_commit": None,
                "message": f"Mindthus release payload metadata is invalid JSON: {exc}",
            }
        )
        return report

    actual_commit = str(metadata.get("commit", "")).strip()
    actual_tag = str(metadata.get("tag", "")).strip()
    if actual_tag != lock["tag"] or actual_commit != lock["commit"]:
        report.update(
            {
                "status": "release_mismatch",
                "actual_commit": actual_commit or None,
                "actual_tag": actual_tag or None,
                "message": "Mindthus release payload metadata does not match the lock file.",
            }
        )
        return report

    required_paths = [
        release_dir / "README.md",
        release_dir / "CHANGELOG.md",
        release_dir / "skills" / "using-mindthus" / "SKILL.md",
        release_dir / "skills" / "tvg" / "SKILL.md",
        release_dir / "scripts" / "install-skills.sh",
    ]
    missing = [path.relative_to(release_dir).as_posix() for path in required_paths if not path.exists()]
    if missing:
        report.update(
            {
                "status": "release_invalid",
                "actual_commit": actual_commit,
                "message": "Mindthus release payload is missing required files: " + ", ".join(missing),
            }
        )
        return report

    report.update(
        {
            "status": "ready",
            "actual_commit": actual_commit,
            "actual_tag": actual_tag,
            "payload_type": "release",
            "message": "Mindthus release payload matches the lock file.",
        }
    )
    return report


def inspect_mindthus_dependency(reference_root: Path, lock: Mapping[str, str]) -> dict[str, Any]:
    release_report = inspect_mindthus_release_payload(reference_root, lock)
    if release_report["status"] == "ready":
        return release_report
    if release_report["status"] != "release_missing":
        return release_report

    report = base_report(reference_root, lock)
    source_dir = Path(report["source_dir"])

    if not source_dir.exists():
        report.update(
            {
                "status": "missing",
                "actual_commit": None,
                "message": "Mindthus source checkout is missing.",
            }
        )
        return report

    if not source_dir.is_dir():
        report.update(
            {
                "status": "invalid",
                "actual_commit": None,
                "message": "Mindthus source path exists but is not a directory.",
            }
        )
        return report

    proc = run_git(["rev-parse", "HEAD"], cwd=source_dir)
    if proc.returncode != 0:
        report.update(
            {
                "status": "invalid",
                "actual_commit": None,
                "message": "Mindthus source directory is not a readable git checkout.",
                "stderr": proc.stderr.strip(),
            }
        )
        return report

    actual_commit = proc.stdout.strip()
    if actual_commit != lock["commit"]:
        report.update(
            {
                "status": "mismatch",
                "actual_commit": actual_commit,
                "message": "Mindthus checkout commit does not match the lock file.",
            }
        )
        return report

    report.update(
        {
            "status": "ready",
            "actual_commit": actual_commit,
            "message": "Mindthus checkout matches the lock file.",
        }
    )
    return report


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def remove_source_for_force(source_dir: Path, reference_root: Path) -> None:
    resolved_source = source_dir.resolve()
    resolved_root = reference_root.resolve()
    if resolved_source.parent != resolved_root:
        raise ValueError(f"Refusing to remove source outside reference root: {source_dir}")
    if source_dir.is_dir():
        shutil.rmtree(source_dir)
    elif source_dir.exists():
        source_dir.unlink()


def clone_mindthus(reference_root: Path, lock: Mapping[str, str]) -> dict[str, Any]:
    source_dir = source_path(reference_root, lock)
    reference_root.mkdir(parents=True, exist_ok=True)
    proc = run_git(
        [
            "clone",
            "--depth",
            "1",
            "--branch",
            lock["tag"],
            lock["repo"],
            str(source_dir),
        ]
    )
    if proc.returncode != 0:
        report = base_report(reference_root, lock)
        report.update(
            {
                "status": "clone_failed",
                "actual_commit": None,
                "message": "Mindthus clone failed.",
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
            }
        )
        return report

    return inspect_mindthus_dependency(reference_root, lock)


def bootstrap_mindthus_dependency(
    reference_root: Path,
    lock: Mapping[str, str],
    *,
    check_only: bool,
    force: bool,
) -> dict[str, Any]:
    report = inspect_mindthus_dependency(reference_root, lock)
    if report["status"] == "ready" or check_only:
        return report

    source_dir = source_path(reference_root, lock)
    if report["status"] == "missing":
        return clone_mindthus(reference_root, lock)

    if force:
        remove_source_for_force(source_dir, reference_root)
        return clone_mindthus(reference_root, lock)

    report["message"] = f"{report['message']} Re-run with --force to replace the local source checkout."
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", type=Path, default=DEFAULT_REFERENCE_ROOT)
    parser.add_argument("--lock-path", type=Path, default=DEFAULT_LOCK_PATH)
    parser.add_argument("--report-path", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true", help="Inspect only; never clone or modify source/.")
    parser.add_argument("--force", action="store_true", help="Replace an invalid or mismatched source/ checkout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    reference_root = args.reference_root
    report_path = args.report_path or reference_root / DEFAULT_REPORT_PATH.name

    try:
        lock = load_lock(args.lock_path)
        report = bootstrap_mindthus_dependency(
            reference_root=reference_root,
            lock=lock,
            check_only=args.check_only,
            force=args.force,
        )
    except Exception as exc:
        report = {
            "status": "error",
            "message": str(exc),
            "reference_root": str(reference_root),
            "checked_at": utc_now_iso(),
        }

    write_report(report_path, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("status") == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
