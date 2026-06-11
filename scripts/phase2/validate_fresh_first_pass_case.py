#!/usr/bin/env python3
"""
Audit a Phase-2 case root for fresh first-pass generation state.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path
from typing import Any

from common.cross_phase_surface_policy import phase_surface_exists


MANIFEST_NAME = "phase-2-first-pass-generation-manifest.md"
STAGE_FILES = (
    "stage-01-architecture-definition-and-boundary-setting.md",
    "stage-02-domain-module-service-decomposition.md",
    "stage-03-data-storage-and-interface-design.md",
    "stage-04-design-convergence-and-delivery-prototype.md",
)
OPTIONAL_STAGE_FILES = (
    "stage-02.5-third-party-integration-architecture-design.md",
)
WRAPPER_FILES = (
    "phase-2-execution-report.md",
    "engineering-spec-pack.md",
    "phase-3-implementation-entry.md",
    "quality-check-report.json",
)
SCAFFOLD_MARKERS = ("fresh-first-pass-target", "scaffolded_target:")


def inspect_case(output_dir: Path) -> dict[str, Any]:
    manifest_exists = phase_surface_exists(output_dir, "phase2", MANIFEST_NAME)

    stage_rows: list[dict[str, Any]] = []
    missing_stage_files: list[str] = []
    stub_stage_files: list[str] = []

    for filename in STAGE_FILES:
        path = output_dir / filename
        exists = path.exists()
        still_scaffold_target = False
        if exists:
            text = path.read_text(encoding="utf-8")
            still_scaffold_target = any(marker in text for marker in SCAFFOLD_MARKERS)
        else:
            missing_stage_files.append(filename)
        if still_scaffold_target:
            stub_stage_files.append(filename)
        stage_rows.append(
            {
                "file": filename,
                "exists": exists,
                "still_scaffold_target": still_scaffold_target,
                "required": True,
            }
        )

    optional_stage_rows: list[dict[str, Any]] = []
    optional_stub_stage_files: list[str] = []
    for filename in OPTIONAL_STAGE_FILES:
        path = output_dir / filename
        exists = path.exists()
        still_scaffold_target = False
        if exists:
            text = path.read_text(encoding="utf-8")
            still_scaffold_target = any(marker in text for marker in SCAFFOLD_MARKERS)
        if still_scaffold_target:
            optional_stub_stage_files.append(filename)
        optional_stage_rows.append(
            {
                "file": filename,
                "exists": exists,
                "still_scaffold_target": still_scaffold_target,
                "required": False,
            }
        )

    wrapper_artifacts_present = [name for name in WRAPPER_FILES if (output_dir / name).exists()]

    issues: list[str] = []
    if not manifest_exists:
        issues.append(f"missing {MANIFEST_NAME}")
    if missing_stage_files:
        issues.append("missing stage files: " + ", ".join(missing_stage_files))
    if stub_stage_files:
        issues.append("stage files still scaffold-only: " + ", ".join(stub_stage_files))
    if optional_stub_stage_files:
        issues.append("optional stage files still scaffold-only: " + ", ".join(optional_stub_stage_files))

    if issues:
        status = (
            "scaffold-only"
            if manifest_exists and not missing_stage_files and (stub_stage_files or optional_stub_stage_files)
            else "invalid-root"
        )
    elif wrapper_artifacts_present:
        status = "wrapper-closed"
    else:
        status = "authored-first-pass"

    passed = status in {"authored-first-pass", "wrapper-closed"}

    return {
        "output_dir": str(output_dir),
        "manifest_exists": manifest_exists,
        "stage_rows": stage_rows,
        "optional_stage_rows": optional_stage_rows,
        "missing_stage_files": missing_stage_files,
        "stub_stage_files": stub_stage_files,
        "optional_stub_stage_files": optional_stub_stage_files,
        "wrapper_artifacts_present": wrapper_artifacts_present,
        "status": status,
        "passed": passed,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a Phase-2 case root for fresh first-pass state")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    result = inspect_case(output_dir)

    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload.rstrip())
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
