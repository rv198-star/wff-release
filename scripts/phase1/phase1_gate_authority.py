from __future__ import annotations

import os
import sys
from typing import Any


CANONICAL_MAINLINE_GATE_SURFACE_SCRIPTS = {
    "scripts/phase1/run_phase1_full_trial.py",
    "scripts/phase1/run_phase1_convergence.py",
    "scripts/phase1/phase1_stage_artifact_depth_gate.py",
    "scripts/phase1/phase1_prd_quality_gate.py",
    "scripts/phase1/phase1_prd_executability_gate.py",
}

BUNDLE_INTERNAL_COMPATIBILITY_SCRIPTS = {
    "scripts/phase1/phase1_prd_analysis_delta_gate.py",
    "scripts/phase1/phase1_prd_assembly_integrity_gate.py",
    "scripts/phase1/phase1_prd_section_scoring_gate.py",
    "scripts/phase1/phase1_artifact_consistency_gate.py",
}

PHASE1_CLOSURE_ENTRYPOINTS = {
    "scripts/phase1/run_phase1_full_trial.py",
    "scripts/phase1/run_phase1_convergence.py",
}

PHASE1_SUPPORT_GATE_SCRIPTS = CANONICAL_MAINLINE_GATE_SURFACE_SCRIPTS - PHASE1_CLOSURE_ENTRYPOINTS

SUPPRESS_COMPATIBILITY_WARNING_ENV = "WFF_PHASE1_CANONICAL_DRIVER"


def _closure_authority(relative_path: str) -> dict[str, Any]:
    return {
        "path": relative_path,
        "script_surface_role": "canonical-mainline-gate-surface",
        "validation_profile": "phase",
        "default_status": "default",
        "formal_p1_closure_authority": True,
        "claim_ceiling": "P1 phase closure evidence for the selected full-trial or convergence path under declared inputs",
    }


def _phase_support_authority(relative_path: str) -> dict[str, Any]:
    return {
        "path": relative_path,
        "script_surface_role": "canonical-mainline-gate-surface",
        "validation_profile": "phase",
        "default_status": "phase-support",
        "formal_p1_closure_authority": False,
        "claim_ceiling": "P1 support gate evidence only; formal P1 closure requires the canonical P1 runner",
    }


def _compatibility_authority(relative_path: str) -> dict[str, Any]:
    return {
        "path": relative_path,
        "script_surface_role": "bundle-internal-compatibility",
        "validation_profile": "compatibility",
        "default_status": "compatibility-only",
        "formal_p1_closure_authority": False,
        "claim_ceiling": "bundle-internal compatibility support evidence only; not canonical P1 closure",
    }


PHASE1_GATE_AUTHORITY: dict[str, dict[str, Any]] = {
    **{path: _closure_authority(path) for path in PHASE1_CLOSURE_ENTRYPOINTS},
    **{path: _phase_support_authority(path) for path in PHASE1_SUPPORT_GATE_SCRIPTS},
    **{path: _compatibility_authority(path) for path in BUNDLE_INTERNAL_COMPATIBILITY_SCRIPTS},
}


def script_surface_role(relative_path: str) -> str:
    if relative_path in CANONICAL_MAINLINE_GATE_SURFACE_SCRIPTS:
        return "canonical-mainline-gate-surface"
    if relative_path in BUNDLE_INTERNAL_COMPATIBILITY_SCRIPTS:
        return "bundle-internal-compatibility"
    if relative_path.startswith("scripts/"):
        return "supporting-phase1-runtime-script"
    return "runtime-asset"


def phase1_gate_authority_map() -> dict[str, dict[str, Any]]:
    return {path: dict(authority) for path, authority in PHASE1_GATE_AUTHORITY.items()}


def phase1_gate_authority(relative_path: str) -> dict[str, Any]:
    normalized = str(relative_path or "").strip()
    try:
        return dict(PHASE1_GATE_AUTHORITY[normalized])
    except KeyError as exc:
        known = ", ".join(sorted(PHASE1_GATE_AUTHORITY))
        raise SystemExit(f"Unknown Phase-1 gate authority surface '{normalized}'. Known surfaces: {known}") from exc


def authority_warning_text(relative_path: str) -> str:
    return (
        f"[WFF Phase-1 authority] {relative_path} is a bundle-internal compatibility script, "
        "not a canonical Phase-1 closure gate. Use run_phase1_full_trial.py or "
        "run_phase1_convergence.py for canonical Phase-1 mainline closure; direct results from "
        "this script are support evidence only."
    )


def emit_compatibility_warning(relative_path: str) -> None:
    if os.environ.get(SUPPRESS_COMPATIBILITY_WARNING_ENV):
        return
    if script_surface_role(relative_path) != "bundle-internal-compatibility":
        return
    print(authority_warning_text(relative_path), file=sys.stderr)
