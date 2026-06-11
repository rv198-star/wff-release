#!/usr/bin/env python3
"""Non-blocking reader translation lane for a completed release case.

Discovers PRD, ESP, and action card targets under a case root, runs
emit_reader_translation.py for each, and writes a manifest.  Failures are
recorded but never block the caller — this lane is always non-blocking.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_deps(release_root: Path) -> tuple[dict | None, str]:
    """Ensure openai is importable for the emit_reader_translation subprocess.

    Returns (error_or_None, python_path).  If system Python can't install
    packages (PEP 668 externally-managed), bootstraps a venv under
    release_root and returns its python path instead.
    """
    try:
        import openai  # noqa: F401
        return None, sys.executable
    except ImportError:
        pass

    req = release_root / "requirements.txt"
    if not req.exists():
        return {"error": "openai not installed and requirements.txt not found"}, sys.executable

    # Try system pip install first
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        capture_output=True, text=True,
    )
    if proc.returncode == 0:
        try:
            import openai  # noqa: F401
            return None, sys.executable
        except ImportError:
            return {"error": "openai still not importable after system pip install"}, sys.executable

    # System pip failed (likely PEP 668 externally-managed). Bootstrap a venv.
    venv_dir = release_root / ".reader-venv"
    venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        create_proc = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True, text=True,
        )
        if create_proc.returncode != 0:
            return {
                "error": (
                    f"system pip install failed ({proc.stderr.strip()[:150]}) "
                    f"and venv creation also failed ({create_proc.stderr.strip()[:150]})"
                )
            }, sys.executable

    install_proc = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(req)],
        capture_output=True, text=True,
    )
    if install_proc.returncode != 0:
        return {
            "error": (
                "system pip install failed and venv pip install also failed: "
                f"{install_proc.stderr.strip()[:300]}"
            )
        }, sys.executable

    return None, str(venv_python)


def discover_targets(case_root: Path, locale: str) -> list[tuple[str, str, Path]]:
    """Return (kind, label, canonical_path) for every translatable artifact."""
    targets: list[tuple[str, str, Path]] = []

    prd = case_root / "phase-1" / "phase-1-product-requirements-document-main-document.md"
    if prd.exists():
        targets.append(("p1-prd", "P1 PRD", prd))

    esp = case_root / "phase-2" / "engineering-spec-pack.md"
    if esp.exists():
        targets.append(("p2-esp", "P2 ESP", esp))

    ac_dir = case_root / "phase-3" / "action-cards"
    for ac in sorted(ac_dir.glob("*action-card.md")):
        targets.append(("p3-action-card", f"P3 {ac.stem}", ac))

    return targets


def run_one(kind: str, label: str, canonical: Path, *, emit_script: Path, locale: str,
            python: str) -> dict:
    """Run emit_reader_translation.py for a single target and return its entry."""
    reader = canonical.with_name(f"{canonical.stem}.reader.{locale}.md")
    integrity = canonical.with_name(f"{canonical.stem}.reader.{locale}.integrity.json")
    progress = canonical.with_name(f"{canonical.stem}.reader.{locale}.progress.jsonl")

    cmd = [
        python, str(emit_script),
        "--canonical", str(canonical),
        "--target-locale", locale,
        "--artifact-label", label,
        "--output", str(reader),
        "--integrity-json", str(integrity),
        "--progress-file", str(progress),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)

    payload: dict = {}
    stdout_text = proc.stdout.strip()
    if stdout_text:
        try:
            payload = json.loads(stdout_text)
        except json.JSONDecodeError:
            pass

    return {
        "kind": kind,
        "canonical": str(canonical),
        "reader": str(reader),
        "integrity_json": str(integrity),
        "status": "generated" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "verdict": payload.get("verdict", "translation-failed"),
        "detail": payload.get("detail", proc.stderr.strip() or stdout_text[:500]),
    }


def _write_manifest(case_root: Path, locale: str, entries: list[dict],
                    total_targets: int, manifest_status: str = "") -> dict:
    """Write the current manifest to disk.  Called incrementally after each target."""
    generated = sum(1 for e in entries if e["status"] == "generated")
    failed = sum(1 for e in entries if e["status"] == "failed")

    if total_targets == 0:
        evidence_state = "missing"
    elif failed > 0 or generated < total_targets:
        evidence_state = "failed" if failed > 0 else "in-progress"
    elif failed == 0 and generated > 0:
        evidence_state = "generated"
    else:
        evidence_state = "missing"

    manifest = {
        "generated_at": utc_now_iso(),
        "case_root": str(case_root),
        "target_locale": locale,
        "summary": {
            "total_targets": total_targets,
            "generated_count": generated,
            "failed_count": failed,
        },
        "reader_evidence_state": evidence_state,
        "non_blocking": True,
        "targets": entries,
    }
    if manifest_status:
        manifest["_status"] = manifest_status

    json_path = case_root / "reader-translation-manifest.json"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                     sort_keys=True) + "\n", encoding="utf-8")

    md_path = case_root / "reader-translation-manifest.md"
    md_lines = [
        "# Reader Translation Manifest",
        "",
        f"- generated_at: `{manifest['generated_at']}`",
        f"- case_root: `{manifest['case_root']}`",
        f"- target_locale: `{manifest['target_locale']}`",
        f"- reader_evidence_state: `{manifest['reader_evidence_state']}`",
    ]
    if manifest_status:
        md_lines.append(f"- lane_status: `{manifest_status}`")
    md_lines.append("")
    md_lines.append("## Summary")
    for k, v in manifest["summary"].items():
        md_lines.append(f"- {k}: `{v}`")
    md_lines.append("")
    md_lines.append("## Targets")
    for e in entries:
        md_lines.append(
            f"- {e['kind']}: `{e['status']}` verdict=`{e['verdict']}` "
            f"canonical=`{e['canonical']}` reader=`{e['reader']}`"
        )
    md_path.write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    return manifest


def run_lane(case_root: Path, *, emit_script: Path, locale: str) -> dict:
    # Ensure openai is available before attempting translations
    release_root = emit_script.resolve().parents[2]
    dep_error, python_path = _ensure_deps(release_root)

    targets = discover_targets(case_root, locale)
    total = len(targets)
    entries: list[dict] = []

    if dep_error:
        for kind, label, path in targets:
            entries.append({
                "kind": kind,
                "canonical": str(path),
                "reader": "",
                "integrity_json": "",
                "status": "failed",
                "returncode": None,
                "verdict": "dependency-failed",
                "detail": dep_error.get("error", str(dep_error)),
            })
        return _write_manifest(case_root, locale, entries, total_targets=total,
                               manifest_status="dependency-failed")

    # Write initial manifest so external observers see the lane is running
    _write_manifest(case_root, locale, entries, total_targets=total,
                    manifest_status="running")

    for kind, label, path in targets:
        entry = run_one(kind, label, path, emit_script=emit_script, locale=locale,
                        python=python_path)
        entries.append(entry)
        # Incremental progress — manifest is up-to-date after each file
        _write_manifest(case_root, locale, entries, total_targets=total,
                        manifest_status="running")

    return _write_manifest(case_root, locale, entries, total_targets=total,
                           manifest_status="done")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Non-blocking reader translation lane for a completed case"
    )
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--target-locale", default="zh-CN")
    parser.add_argument(
        "--emit-script", type=Path,
        default=Path(__file__).resolve().parents[1] / "common" / "emit_reader_translation.py",
    )
    args = parser.parse_args(argv)

    manifest = run_lane(
        args.case_root,
        emit_script=args.emit_script,
        locale=args.target_locale,
    )
    print(json.dumps(manifest, ensure_ascii=False))
    # Always exit 0 — reader lane is non-blocking
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
