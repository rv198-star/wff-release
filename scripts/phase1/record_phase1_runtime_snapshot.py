#!/usr/bin/env python3
"""
Record Phase-1 runtime snapshot hashes for reproducible trial runs.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from phase1.phase1_gate_authority import (
    BUNDLE_INTERNAL_COMPATIBILITY_SCRIPTS,
    CANONICAL_MAINLINE_GATE_SURFACE_SCRIPTS,
    script_surface_role,
)


RUNTIME_FILES = [
    "runtime-deps/mindthus/release/skills/3l5s/SKILL.md",
    "runtime-deps/mindthus/release/skills/3l5s/resources/three-layer-recursive-loop.md",
    "runtime-deps/mindthus/release/skills/using-mindthus/SKILL.md",
    "docs/governance/evidence-and-uncertainty-protocol-v0.1.md",
    "docs/governance/maturity-and-confidence-protocol-v0.1.md",
    "docs/governance/deepening-and-freeze-protocol-v0.1.md",
    "docs/governance/handoff-and-convergence-protocol-v0.1.md",
    "docs/phases/phase-1/phase-1-convergence-driver-v0.1.md",
    "docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md",
    "docs/phases/phase-1/phase-1-execution-report-template-v0.1.md",
    "reference-packages/phase1-product-requirements/stage-01-user-research/stage-sop.md",
    "reference-packages/phase1-product-requirements/stage-01-user-research/source-cards.md",
    "reference-packages/phase1-product-requirements/stage-02-requirements-analysis/stage-sop.md",
    "reference-packages/phase1-product-requirements/stage-02-requirements-analysis/source-cards.md",
    "reference-packages/phase1-product-requirements/stage-02b-requirements-specification/stage-sop.md",
    "reference-packages/phase1-product-requirements/stage-02b-requirements-specification/output-template.md",
    "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/stage-sop.md",
    "reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/source-cards.md",
    "reference-packages/phase1-product-requirements/stage-04-requirements-validation/stage-sop.md",
    "reference-packages/phase1-product-requirements/stage-04-requirements-validation/source-cards.md",
    "scripts/phase1/phase1_prd_quality_gate.py",
    "scripts/phase1/phase1_stage_artifact_depth_gate.py",
    "scripts/phase1/phase1_prd_analysis_delta_gate.py",
    "scripts/phase1/phase1_prd_assembly_integrity_gate.py",
    "scripts/phase1/phase1_prd_executability_gate.py",
    "scripts/phase1/phase1_prd_section_scoring_gate.py",
    "scripts/phase1/phase1_artifact_consistency_gate.py",
    "scripts/phase1/phase1_gate_authority.py",
    "scripts/phase1/phase1_reasoning_runtime.py",
    "scripts/phase1/phase1_generate_deep_stage_outputs.py",
    "scripts/phase1/phase1_assemble_prd.py",
    "scripts/phase1/phase1_converge_prd.py",
    "scripts/phase1/phase1_emit_depth_runtime_artifacts.py",
    "scripts/phase1/phase1_localize_prd_zh.py",
    "scripts/phase1/phase1_emit_execution_report.py",
    "scripts/phase1/phase1_material_library_coverage_audit.py",
    "scripts/phase1/run_phase1_full_trial.py",
    "scripts/phase1/run_phase1_convergence.py",
]

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()

def build_runtime_snapshot_payload(repo_root: Path, runtime_files: list[str] | None = None) -> dict[str, object]:
    runtime_files = runtime_files or RUNTIME_FILES
    files_data = []
    aggregate = hashlib.sha256()
    for rel in runtime_files:
        abs_path = repo_root / rel
        role = script_surface_role(rel)
        if not abs_path.exists():
            files_data.append(
                {
                    "path": rel,
                    "exists": False,
                    "sha256": None,
                    "script_surface_role": role,
                }
            )
            continue
        file_hash = sha256_file(abs_path)
        aggregate.update(rel.encode("utf-8"))
        aggregate.update(file_hash.encode("utf-8"))
        files_data.append(
            {
                "path": rel,
                "exists": True,
                "sha256": file_hash,
                "script_surface_role": role,
            }
        )

    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "runtime_snapshot_id": aggregate.hexdigest(),
        "script_surface": {
            "canonical_mainline_gate_surface_scripts": sorted(CANONICAL_MAINLINE_GATE_SURFACE_SCRIPTS),
            "bundle_internal_compatibility_scripts": sorted(BUNDLE_INTERNAL_COMPATIBILITY_SCRIPTS),
            "surface_truth_note": (
                "Phase-1 canonical mainline gate surface is run_phase1_full_trial/run_phase1_convergence plus "
                "stage_depth/quality/executability gates; the four bundle internals remain recorded here as "
                "compatibility scripts, not as peer mainline entrypoints."
            ),
        },
        "files": files_data,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Phase-1 runtime snapshot")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    payload = build_runtime_snapshot_payload(repo_root)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot written: {output}")
    print(f"runtime_snapshot_id: {payload['runtime_snapshot_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
