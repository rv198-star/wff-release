#!/usr/bin/env python3
"""
Phase-2 closure wrapper over authored Stage outputs.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from phase2.glossary_generator import build_glossary_entries, glossary_markdown
from common.output_language import (
    localize_phase2_engineering_spec_pack,
    localize_phase2_execution_report,
    localize_phase2_implementation_entry,
    resolve_output_locale,
)
from common.human_review_surface import emit_human_review_surface
from common.script_data_assets import load_script_text_asset
from common.claim_control_runtime import (
    emit_path_b_claim_control_sidecar,
)
from phase2.component_semantic_inventory import emit_component_semantic_inventory
from phase2.phase2_claim_authority import (
    audit_phase2_artifact_upstream_claim_refs,
    phase1_claims_for_phase2,
    phase2_claim_control_claim_ceiling,
)
from common.wff_runtime_paths import resolve_wff_base_trace_scripts
from common.cross_phase_surface_policy import (
    find_cross_phase_surface_path,
    phase_surface_exists,
    resolve_cross_phase_surface_path,
)
from common.contamination_boundary import build_contamination_report_for_path
from common.markdown_table_tools import render_markdown_table, table_rows_with_required_headers
from phase1.phase1_trace_units import (
    PHASE1_PRD_ARTIFACT_ID,
    PHASE1_TRACE_UNIT_TYPE_MAP,
    extract_phase1_trace_units,
)
from common.tvg_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES
from phase1.phase1_phase2_coverage import build_phase1_phase2_coverage_report, extract_fine_grained_trace_units
from phase2.phase2_onboarding_prereqs import (
    bullet_items_from_block,
    derive_environment_dependency_prerequisites,
    format_nested_bullets,
)
from phase2.phase2_trace_alignment import (
    build_phase2_phase1_resolution_report,
    canonicalize_phase2_trace_artifact_id,
)
from phase2.phase2_operation_semantic_payload import build_operation_semantic_payload
from phase2.run_phase2_first_version import _extract_page_map_from_prototype_spec
from phase3.operation_risk_tiering import classify_operation, derive_acd_level, normalize_business_value_weight
from common.complexity_classifier import classify_phase1_prd
from phase2.phase2_quality_check import (
    analyze_optional_stage_02_5,
    analyze_phase2_case,
    block_text,
    build_phase2_mainline_assessment,
    extract_block_scalar,
    extract_structured_field,
    extract_structured_block,
    markdown_heading_section,
    markdown_tables,
    write_phase2_mainline_assessment_artifacts,
)
from phase2.existing_system_architecture_change import (
    discover_existing_system_architecture_change_intake,
    materialize_existing_system_architecture_change_intake,
    render_existing_system_architecture_change_addendum,
    resolve_existing_system_architecture_change_intake,
)
from phase2.validate_fresh_first_pass_case import MANIFEST_NAME, SCAFFOLD_MARKERS, WRAPPER_FILES, inspect_case


STAGE_DEFAULTS = {
    "stage_01": "stage-01-architecture-definition-and-boundary-setting.md",
    "stage_02": "stage-02-domain-module-service-decomposition.md",
    "stage_03": "stage-03-data-storage-and-interface-design.md",
    "stage_04": "stage-04-design-convergence-and-delivery-prototype.md",
}

STAGE_IDS = {
    "stage_01": "ARCH-STG01-OUTPUT-0001",
    "stage_02": "ARCH-STG02-OUTPUT-0001",
    "stage_03": "ARCH-STG03-OUTPUT-0001",
    "stage_04": "ARCH-STG04-OUTPUT-0001",
}

OPTIONAL_STAGE_02_5_DEFAULT = "stage-02.5-third-party-integration-architecture-design.md"
OPTIONAL_STAGE_02_5_ID = "ARCH-STG025-OUTPUT-0001"
DEPLOYMENT_POSTURES = ("light", "standard", "heavy")
DEPLOYMENT_POSTURE_WARNING_CLASSES = ("constraint-backed-override", "preference-driven-override")

WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase2/data/engineering-spec-pack.md.template",
    "scripts/phase2/data/phase2-execution-report.md.template",
)

CHECKLIST_MAPPING = {
    "system boundary statement": ("1", "Stage-01"),
    "constraint posture": ("2", "Stage-01"),
    "quality attribute / NFR absorption": ("3", "Stage-01"),
    "capability map": ("4", "Stage-01"),
    "architecture direction": ("5", "Stage-01"),
    "key architecture decisions": ("6", "Stage-01"),
    "security architecture sketch": ("6A", "Stage-01"),
    "capacity estimation": ("6B", "Stage-01"),
    "domain map": ("7", "Stage-02"),
    "module map": ("8", "Stage-02"),
    "service candidates": ("9", "Stage-02"),
    "responsibility matrix": ("10", "Stage-02"),
    "dependency / collaboration map": ("11", "Stage-02"),
    "decomposition decisions": ("12", "Stage-02"),
    "conceptual entity relationship diagram": ("13", "Stage-02"),
    "domain event catalog": ("14", "Stage-02"),
    "data model summary": ("15", "Stage-03"),
    "data ownership map": ("16", "Stage-03"),
    "storage strategy": ("17", "Stage-03"),
    "schema draft": ("18", "Stage-03"),
    "interface contracts": ("19", "Stage-03"),
    "API endpoint draft": ("20", "Stage-03"),
    "interaction flow": ("21", "Stage-03"),
    "security architecture outline": ("22", "Stage-03"),
    "technology stack and deployment assumptions": ("23", "Stage-03"),
    "technology selection evaluation matrix": ("24", "Stage-03"),
    "dominant bottleneck hypothesis": ("25", "Stage-03"),
    "architecture alternative candidate set": ("26", "Stage-03"),
    "baseline insufficiency note": ("27", "Stage-03"),
    "constraint-dominant optimum candidate": ("28", "Stage-03"),
    "capacity and performance assumptions": ("29", "Stage-03"),
    "scenario coverage matrix": ("30", "Stage-03"),
    "key tradeoff decisions": ("31", "Stage-03"),
    "architecture convergence summary": ("32", "Stage-04"),
    "prototype or structured delivery expression": ("33", "Stage-04"),
    "critical interaction sequence set": ("34", "Stage-04"),
    "optimality review": ("35", "Stage-04"),
    "design verification notes": ("36", "Stage-04"),
    "unresolved risks and review-bound items": ("37", "Stage-04"),
    "implementation handoff package": ("38", "Stage-04"),
    "implementation task sketch": ("39", "Stage-04"),
}

FORMAL_STATE_RANK = {
    "blocked": 0,
    "pass-with-review-bound-items": 1,
    "implementation-planning-ready": 2,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_phase2_full_trial_timing_report_payload(
    *,
    started_at: str,
    finished_at: str,
    total_duration_seconds: float,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_segments: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(segments, start=1):
        name = str(raw.get("name") or f"segment_{index:02d}").strip()
        normalized_segments[name] = dict(raw)
    longest_segments = sorted(
        normalized_segments.values(),
        key=lambda row: float(row.get("duration_seconds") or 0.0),
        reverse=True,
    )
    return {
        "generated_at": utc_now_iso(),
        "started_at": started_at,
        "finished_at": finished_at,
        "total_duration_seconds": round(max(0.0, float(total_duration_seconds)), 3),
        "segments": normalized_segments,
        "longest_segments": longest_segments[:10],
    }


def append_phase2_full_trial_timing_segment(
    segments: list[dict[str, Any]],
    *,
    name: str,
    started_at: str,
    started_monotonic: float,
    status: str,
) -> None:
    segments.append(
        {
            "name": name,
            "started_at": started_at,
            "finished_at": utc_now_iso(),
            "duration_seconds": round(max(0.0, time.monotonic() - started_monotonic), 3),
            "status": status,
        }
    )


def phase2_full_trial_timed_segment(segments: list[dict[str, Any]], name: str, action):
    started_at = utc_now_iso()
    started_monotonic = time.monotonic()
    status = "fail"
    try:
        result = action()
        status = "pass"
        return result
    finally:
        append_phase2_full_trial_timing_segment(
            segments,
            name=name,
            started_at=started_at,
            started_monotonic=started_monotonic,
            status=status,
        )


def write_phase2_full_trial_timing_report(
    context: "Phase2FullTrialContext",
    *,
    started_at: str,
    started_monotonic: float,
    segments: list[dict[str, Any]],
) -> Path:
    payload = build_phase2_full_trial_timing_report_payload(
        started_at=started_at,
        finished_at=utc_now_iso(),
        total_duration_seconds=time.monotonic() - started_monotonic,
        segments=segments,
    )
    context.timing_report.parent.mkdir(parents=True, exist_ok=True)
    context.timing_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return context.timing_report


@dataclass(frozen=True)
class Phase2FullTrialContext:
    script_dir: Path
    python: str
    trace_dir: Path
    output_locale: str
    phase1_prd: Path
    existing_system_architecture_change_intake: Path | None
    output_dir: Path
    case_name: str
    project_key: str
    version: str
    profile: str
    owner: str
    thinking_value_gain_mode: str
    thinking_value_gain_output_profile: str
    formal_state_override: str
    realizability_judgment_override: str
    stage_01: Path
    stage_02: Path
    stage_02_5: Path | None
    stage_03: Path
    stage_04: Path
    stage_paths: dict[str, Path]
    execution_report: Path
    engineering_spec_pack: Path
    engineering_spec_pack_claim_control: Path
    implementation_entry: Path
    first_pass_audit_path: Path
    trace_validation: Path
    trace_report_text: Path
    trace_report_json: Path
    phase1_trace_resolution_path: Path
    phase1_phase2_coverage_path: Path
    contamination_report_path: Path
    complexity_classification_path: Path
    complexity_classification_report: dict[str, Any]
    selected_complexity_profile: str
    complexity_override_justification: str
    deployment_posture: dict[str, str]
    baseline_lock: Path
    quality_report_path: Path
    mermaid_report_path: Path
    cross_stage_report_path: Path
    timing_report: Path


@dataclass(frozen=True)
class Phase2TraceabilitySuiteResult:
    phase1_trace_resolution_report: dict[str, Any]
    phase1_phase2_coverage_report: dict[str, Any]
    trace_runtime_contract_verdict: str
    trace_runtime_contract_issues: list[str]
    trace_db_path: str
    trace_registry_root: str
    fine_grained_trace_summary: dict[str, int]
    mermaid_report: dict[str, Any]
    cross_stage_report: dict[str, Any]


@dataclass(frozen=True)
class Phase2ClosureResult:
    effective_formal_state: str
    effective_realizability_judgment: str
    closure_adjustment_reasons: list[str]
    mainline_assessment: dict[str, Any]
    mainline_artifacts: dict[str, str]


def command_option(command: list[str], option: str, default: str = "") -> str:
    try:
        index = command.index(option)
        return str(command[index + 1])
    except (ValueError, IndexError):
        return default


def trace_project_scope_id(*, project_key: str, project_root: Path) -> str:
    return f"{project_key}:{project_root.resolve()}"


def trace_registry_db_path(project_root: Path, explicit_db_path: str = "") -> Path:
    if explicit_db_path:
        return Path(explicit_db_path).resolve()
    return project_root / ".trace" / "trace.db"


def open_trace_registry_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def complete_direct_trace_command(
    command: list[str],
    *,
    capture: bool,
    stdout: str,
) -> subprocess.CompletedProcess[str]:
    if not capture and stdout:
        print(stdout.rstrip())
        return subprocess.CompletedProcess(command, 0, "", "")
    return subprocess.CompletedProcess(command, 0, stdout, "")


def run_bind_artifact_in_process(command: list[str], *, capture: bool) -> subprocess.CompletedProcess[str]:
    project_root = Path(command_option(command, "--project-root")).resolve()
    project_key = command_option(command, "--project-key")
    artifact_id = command_option(command, "--artifact-id")
    db_path = trace_registry_db_path(project_root, command_option(command, "--db-path"))
    scope_id = trace_project_scope_id(project_key=project_key, project_root=project_root)
    now = datetime.now(timezone.utc).isoformat()
    conn = open_trace_registry_db(db_path)
    try:
        existing = conn.execute(
            "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
            (scope_id, artifact_id),
        ).fetchone()
        values = (
            command_option(command, "--artifact-type"),
            command_option(command, "--stage-or-lane"),
            command_option(command, "--status", "draft"),
            command_option(command, "--source-path"),
            command_option(command, "--source-anchor"),
            command_option(command, "--language-role", "runtime-canonical-en"),
            command_option(command, "--canonical-of") or None,
            now,
            scope_id,
            artifact_id,
        )
        if existing:
            conn.execute(
                "UPDATE artifacts SET artifact_type=?, stage_or_lane=?, status=?, source_path=?, source_anchor=?, language_role=?, canonical_of=?, updated_at=? WHERE project_scope=? AND artifact_id=?",
                values,
            )
        else:
            conn.execute(
                "INSERT INTO artifacts (artifact_type, stage_or_lane, status, source_path, source_anchor, language_role, canonical_of, updated_at, project_scope, artifact_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*values, now),
            )
        conn.commit()
    finally:
        conn.close()
    stdout = f"bound {artifact_id} -> {command_option(command, '--source-path')}#{command_option(command, '--source-anchor')}\n"
    return complete_direct_trace_command(command, capture=capture, stdout=stdout)


def run_link_artifacts_in_process(command: list[str], *, capture: bool) -> subprocess.CompletedProcess[str]:
    project_root = Path(command_option(command, "--project-root")).resolve()
    project_key = command_option(command, "--project-key")
    from_artifact_id = command_option(command, "--from-artifact-id")
    to_artifact_id = command_option(command, "--to-artifact-id")
    link_type = command_option(command, "--link-type")
    if link_type not in {"depends_on", "feeds"}:
        raise SystemExit(f"unsupported link type: {link_type}")
    db_path = trace_registry_db_path(project_root, command_option(command, "--db-path"))
    scope_id = trace_project_scope_id(project_key=project_key, project_root=project_root)
    conn = open_trace_registry_db(db_path)
    try:
        for artifact_id in (from_artifact_id, to_artifact_id):
            row = conn.execute(
                "SELECT artifact_id FROM artifacts WHERE project_scope = ? AND artifact_id = ?",
                (scope_id, artifact_id),
            ).fetchone()
            if not row:
                raise SystemExit(f"Artifact not found in scope: {artifact_id}")
        existing = conn.execute(
            "SELECT id FROM links WHERE project_scope = ? AND from_artifact_id = ? AND to_artifact_id = ? AND link_type = ?",
            (scope_id, from_artifact_id, to_artifact_id, link_type),
        ).fetchone()
        if existing:
            stdout = f"link already exists: {from_artifact_id} -[{link_type}]-> {to_artifact_id}\n"
            return complete_direct_trace_command(command, capture=capture, stdout=stdout)
        conn.execute(
            "INSERT INTO links (project_scope, from_artifact_id, to_artifact_id, link_type, source_path, evidence_anchor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                scope_id,
                from_artifact_id,
                to_artifact_id,
                link_type,
                command_option(command, "--source-path") or None,
                command_option(command, "--evidence-anchor") or None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    stdout = f"linked {from_artifact_id} -[{link_type}]-> {to_artifact_id}\n"
    return complete_direct_trace_command(command, capture=capture, stdout=stdout)


def run_trace_registry_command_in_process(
    command: list[str],
    *,
    capture: bool,
) -> subprocess.CompletedProcess[str] | None:
    if len(command) < 2:
        return None
    script_name = Path(str(command[1])).name
    if script_name == "bind_artifact.py":
        return run_bind_artifact_in_process(command, capture=capture)
    if script_name == "link_artifacts.py":
        return run_link_artifacts_in_process(command, capture=capture)
    return None


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    direct_trace_proc = run_trace_registry_command_in_process(command, capture=capture)
    if direct_trace_proc is not None:
        return direct_trace_proc
    proc = subprocess.run(command, text=True, capture_output=capture)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc


def build_mermaid_validation_command(context: Phase2FullTrialContext, *, render: bool) -> list[str]:
    command = [
        context.python,
        str(context.script_dir / "validate_mermaid.py"),
        "--stage-01",
        str(context.stage_01),
        "--stage-02",
        str(context.stage_02),
        "--stage-03",
        str(context.stage_03),
        "--stage-04",
        str(context.stage_04),
        "--output",
        str(context.mermaid_report_path),
        "--complexity-profile",
        context.selected_complexity_profile,
    ]
    if render:
        command.append("--render")
    return command


def normalize_version(raw: str) -> str:
    value = raw.strip().lower()
    if value.startswith(("trial-v", "rerun-v")):
        return value
    if value.startswith("v") and value[1:].isdigit():
        return f"rerun-{value}"
    if value.isdigit():
        return f"rerun-v{value}"
    return value


def slugify(raw: str) -> str:
    chars: list[str] = []
    last_dash = False
    for ch in raw.strip().lower():
        if ch.isalnum():
            chars.append(ch)
            last_dash = False
            continue
        if not last_dash:
            chars.append("-")
            last_dash = True
    return "".join(chars).strip("-") or "phase2-case"


def derive_case_name(output_dir: Path, explicit: str) -> str:
    if explicit:
        return explicit
    if output_dir.name == "phase-2" and output_dir.parent.name:
        return output_dir.parent.name
    return output_dir.name


def default_realizability_judgment(formal_state: str) -> str:
    if formal_state == "implementation-planning-ready":
        return "realizable as designed for implementation-planning intake"
    if formal_state == "pass-with-review-bound-items":
        return "review-bound until source-stage semantic review confirms stronger readiness"
    return "blocked until quality, regression, or dependency issues are resolved for implementation-facing handoff"


def resolve_deployment_posture_selection(
    *,
    suggested: str,
    selected: str,
    warning_class: str,
    override_source: str,
    override_reason: str,
    added_risks: str,
) -> dict[str, str]:
    has_override = selected != suggested
    source = override_source.strip()
    reason = override_reason.strip()
    risks = added_risks.strip()

    if has_override:
        if warning_class not in DEPLOYMENT_POSTURE_WARNING_CLASSES:
            allowed = " | ".join(DEPLOYMENT_POSTURE_WARNING_CLASSES)
            raise ValueError(
                "deployment-posture override requires `--deployment-posture-warning-class` "
                f"with one of: {allowed}"
            )
        if not source:
            raise ValueError(
                "deployment-posture override requires `--deployment-posture-override-source` "
                "when selected posture differs from suggested posture"
            )
        if not reason:
            raise ValueError(
                "deployment-posture override requires `--deployment-posture-override-reason` "
                "when selected posture differs from suggested posture"
            )
        if not risks:
            raise ValueError(
                "deployment-posture override requires `--deployment-posture-added-risks` "
                "when selected posture differs from suggested posture"
            )
        return {
            "suggested": suggested,
            "selected": selected,
            "selection_mode": "human-override-warning",
            "warning_class": warning_class,
            "override_source": source,
            "override_reason": reason,
            "added_risks": risks,
            "warning_summary": (
                f"{warning_class}: suggested={suggested}, selected={selected}, "
                f"source={source}, added_risks={risks}"
            ),
        }

    if warning_class != "none" or source or reason or risks:
        raise ValueError(
            "deployment-posture override metadata is only allowed when selected posture differs "
            "from suggested posture"
        )

    return {
        "suggested": suggested,
        "selected": selected,
        "selection_mode": "default-light" if selected == "light" else "trigger-backed",
        "warning_class": "none",
        "override_source": "none",
        "override_reason": "none",
        "added_risks": "none",
        "warning_summary": "none",
    }


def weaker_formal_state(*states: str) -> str:
    ranked = [state for state in states if state in FORMAL_STATE_RANK]
    if not ranked:
        return "blocked"
    return min(ranked, key=lambda state: FORMAL_STATE_RANK[state])


def closure_capped_formal_state(
    base_state: str,
    *,
    cross_stage_verdict: str,
    mermaid_overall_passed: bool,
    validation_result: str,
    trace_runtime_contract_verdict: str,
    phase1_phase2_coverage_verdict: str = "pass",
) -> tuple[str, list[str]]:
    effective = base_state if base_state in FORMAL_STATE_RANK else "blocked"
    reasons: list[str] = []

    if cross_stage_verdict == "major-inconsistencies":
        effective = weaker_formal_state(effective, "blocked")
        reasons.append("major cross-stage inconsistencies block implementation-facing intake")
    elif cross_stage_verdict == "minor-inconsistencies":
        effective = weaker_formal_state(effective, "pass-with-review-bound-items")
        reasons.append("minor cross-stage inconsistencies cap the formal state at `pass-with-review-bound-items`")

    if not mermaid_overall_passed:
        effective = weaker_formal_state(effective, "blocked")
        reasons.append("Mermaid validation failed, so the package cannot retain an intake-ready formal state")

    if validation_result != "pass" or trace_runtime_contract_verdict != "pass":
        effective = weaker_formal_state(effective, "blocked")
        reasons.append("traceability validation/runtime contract failed, so downstream intake must remain blocked")

    if phase1_phase2_coverage_verdict != "pass":
        effective = weaker_formal_state(effective, "blocked")
        reasons.append("Phase-1 to Phase-2 coverage contract is not fully satisfied, so downstream intake must remain blocked")

    return effective, reasons


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def default_stage_path(output_dir: Path, explicit: str, fallback_name: str) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return (output_dir / fallback_name).resolve()


def default_optional_stage_path(output_dir: Path, explicit: str) -> Path | None:
    if explicit:
        return Path(explicit).resolve()
    candidate = (output_dir / OPTIONAL_STAGE_02_5_DEFAULT).resolve()
    return candidate if candidate.exists() else None


def require_files(label_to_path: dict[str, Path]) -> None:
    missing = [f"{label}: {path}" for label, path in label_to_path.items() if not path.exists()]
    if missing:
        print("[BLOCKED] missing required Phase-2 artifacts:")
        for item in missing:
            print(f"- {item}")
        raise SystemExit(2)


PHASE2_FULL_TRIAL_AUTHORITY: dict[str, Any] = {
    "surface_id": "phase2-full-trial-manual-closure",
    "validation_profile": "manual-closure",
    "default_status": "manual-closure",
    "fresh_generation_entrypoint": False,
    "manual_closure_only": True,
    "claim_ceiling": "closure evidence for supplied authored outputs only",
    "canonical_guidance": (
        "Use run_phase2_full_trial.py for manual closure over supplied authored outputs; "
        "it is not fresh default generation and does not replace run_phase2_first_version.py --run-wrapper."
    ),
}


def phase2_full_trial_authority() -> dict[str, Any]:
    return dict(PHASE2_FULL_TRIAL_AUTHORITY)


def build_phase2_full_trial_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Phase-2 compatibility/manual closure wrapper over existing authored Stage outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "validation profile: manual-closure; default status: manual closure over supplied authored outputs; "
            "claim ceiling: not the fresh default generation path or release proof."
        ),
    )
    parser.add_argument("--phase1-prd", required=True)
    parser.add_argument(
        "--existing-system-architecture-change-intake",
        default="",
        help=(
            "Optional P2 Existing-System Architecture Change Intake Packet. "
            "This sidecar does not replace --phase1-prd or the Stage artifacts."
        ),
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--profile", default="implementation-planning-ready-design-package")
    parser.add_argument("--complexity-profile", default="auto", choices=("auto", "micro", "standard", "complex"))
    parser.add_argument("--complexity-override-justification", default="")
    parser.add_argument("--deployment-posture", default="light", choices=DEPLOYMENT_POSTURES)
    parser.add_argument("--deployment-posture-suggested", default="light", choices=DEPLOYMENT_POSTURES)
    parser.add_argument(
        "--deployment-posture-warning-class",
        default="none",
        choices=("none",) + DEPLOYMENT_POSTURE_WARNING_CLASSES,
    )
    parser.add_argument("--deployment-posture-override-source", default="")
    parser.add_argument("--deployment-posture-override-reason", default="")
    parser.add_argument("--deployment-posture-added-risks", default="")
    parser.add_argument("--owner", default="Codex Phase-2 full runner")
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="Mindthus TVG strategy marker for Phase-2 closure metadata; defaults to off.",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
        help="Mindthus TVG output profile to record when TVG full-use is enabled.",
    )
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument("--case-name", default="")
    parser.add_argument("--project-key", default="")
    parser.add_argument("--stage-01", default="")
    parser.add_argument("--stage-02", default="")
    parser.add_argument("--stage-02-5", default="")
    parser.add_argument("--stage-03", default="")
    parser.add_argument("--stage-04", default="")
    parser.add_argument("--formal-state", default="")
    parser.add_argument("--realizability-judgment", default="")
    parser.add_argument("--baseline-lock", default="")
    return parser


def parse_phase2_full_trial_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_phase2_full_trial_parser().parse_args(argv)


def resolve_phase2_complexity_profile_selection(
    *,
    phase1_prd: Path,
    requested_profile: str,
    override_justification: str,
) -> tuple[dict[str, Any], str, str]:
    complexity_classification_report = classify_phase1_prd(phase1_prd)
    suggested_complexity_profile = str(complexity_classification_report.get("suggested_profile", "standard"))
    selected_complexity_profile = suggested_complexity_profile
    selection_mode = "auto"
    cleaned_override_justification = ""

    if requested_profile != "auto":
        selected_complexity_profile = requested_profile
        if selected_complexity_profile == suggested_complexity_profile:
            selection_mode = "manual-confirm"
        else:
            cleaned_override_justification = override_justification.strip()
            if not cleaned_override_justification:
                raise ValueError(
                    "complexity-profile override requires `--complexity-override-justification` "
                    f"when suggested={suggested_complexity_profile} and selected={selected_complexity_profile}"
                )
            selection_mode = "manual-override"

    complexity_classification_report["selected_profile"] = selected_complexity_profile
    complexity_classification_report["selection_mode"] = selection_mode
    complexity_classification_report["override_justification"] = cleaned_override_justification
    return complexity_classification_report, selected_complexity_profile, cleaned_override_justification


def build_phase2_full_trial_context(args: argparse.Namespace) -> Phase2FullTrialContext:
    output_locale = resolve_output_locale(args.output_locale)

    script_dir = Path(__file__).resolve().parent
    repo_root = SCRIPTS_ROOT.parent
    python = sys.executable

    phase1_prd = Path(args.phase1_prd).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    requested_existing_system_architecture_change_intake = resolve_existing_system_architecture_change_intake(
        str(getattr(args, "existing_system_architecture_change_intake", "") or "")
    )
    existing_system_architecture_change_intake = materialize_existing_system_architecture_change_intake(
        source=(
            requested_existing_system_architecture_change_intake
            or discover_existing_system_architecture_change_intake(output_dir)
        ),
        output_dir=output_dir,
    )
    trace_dir = resolve_wff_base_trace_scripts(project_root=output_dir, fallback_roots=[repo_root])

    case_name = derive_case_name(output_dir, args.case_name)
    project_key = args.project_key or slugify(case_name)
    version = normalize_version(args.version)

    stage_01 = default_stage_path(output_dir, args.stage_01, STAGE_DEFAULTS["stage_01"])
    stage_02 = default_stage_path(output_dir, args.stage_02, STAGE_DEFAULTS["stage_02"])
    stage_02_5 = default_optional_stage_path(output_dir, args.stage_02_5)
    stage_03 = default_stage_path(output_dir, args.stage_03, STAGE_DEFAULTS["stage_03"])
    stage_04 = default_stage_path(output_dir, args.stage_04, STAGE_DEFAULTS["stage_04"])

    required_inputs = {
        "phase1_prd": phase1_prd,
        "stage_01": stage_01,
        "stage_02": stage_02,
        "stage_03": stage_03,
        "stage_04": stage_04,
    }
    if args.stage_02_5:
        required_inputs["stage_02_5"] = stage_02_5 or Path(args.stage_02_5).resolve()
    require_files(required_inputs)

    execution_report = output_dir / "phase-2-execution-report.md"
    engineering_spec_pack = output_dir / "engineering-spec-pack.md"
    implementation_entry = output_dir / "phase-3-implementation-entry.md"
    first_pass_audit_path = resolve_cross_phase_surface_path(output_dir, "phase2", "phase-2-first-pass-audit.json")
    trace_validation = resolve_cross_phase_surface_path(output_dir, "phase2", "phase-2-traceability-validation.txt")
    trace_report_text = resolve_cross_phase_surface_path(output_dir, "phase2", "phase-2-traceability-report.txt")
    trace_report_json = resolve_cross_phase_surface_path(output_dir, "phase2", "phase-2-traceability-report.json")
    phase1_trace_resolution_path = resolve_cross_phase_surface_path(
        output_dir,
        "phase2",
        "phase-2-phase1-trace-resolution.json",
    )
    phase1_phase2_coverage_path = resolve_cross_phase_surface_path(
        output_dir,
        "phase2",
        "phase-1-to-phase-2-coverage.json",
    )
    contamination_report_path = resolve_cross_phase_surface_path(
        output_dir,
        "phase2",
        "p1-to-p2-contamination-report.json",
    )
    complexity_classification_path = resolve_cross_phase_surface_path(
        output_dir,
        "phase2",
        "phase-2-complexity-classification.json",
    )
    baseline_lock = Path(args.baseline_lock).resolve() if args.baseline_lock else (output_dir / "baseline-lock.json")
    quality_report_path = resolve_cross_phase_surface_path(output_dir, "phase2", "quality-check-report.json")
    mermaid_report_path = resolve_cross_phase_surface_path(output_dir, "phase2", "mermaid-validation-report.json")
    cross_stage_report_path = resolve_cross_phase_surface_path(output_dir, "phase2", "cross-stage-consistency.json")
    timing_report = resolve_cross_phase_surface_path(output_dir, "phase2", "phase2-full-trial-timing-report.json")

    complexity_classification_report, selected_complexity_profile, complexity_override_justification = (
        resolve_phase2_complexity_profile_selection(
            phase1_prd=phase1_prd,
            requested_profile=args.complexity_profile,
            override_justification=args.complexity_override_justification,
        )
    )
    write_json(complexity_classification_path, complexity_classification_report)

    deployment_posture = resolve_deployment_posture_selection(
        suggested=args.deployment_posture_suggested,
        selected=args.deployment_posture,
        warning_class=args.deployment_posture_warning_class,
        override_source=args.deployment_posture_override_source,
        override_reason=args.deployment_posture_override_reason,
        added_risks=args.deployment_posture_added_risks,
    )

    stage_paths = {
        "stage_01": stage_01,
        "stage_02": stage_02,
        "stage_03": stage_03,
        "stage_04": stage_04,
    }

    return Phase2FullTrialContext(
        script_dir=script_dir,
        python=python,
        trace_dir=trace_dir,
        output_locale=output_locale,
        phase1_prd=phase1_prd,
        existing_system_architecture_change_intake=existing_system_architecture_change_intake,
        output_dir=output_dir,
        case_name=case_name,
        project_key=project_key,
        version=version,
        profile=args.profile,
        owner=args.owner,
        thinking_value_gain_mode=str(getattr(args, "thinking_value_gain_mode", "off") or "off"),
        thinking_value_gain_output_profile=str(
            getattr(args, "thinking_value_gain_output_profile", "coverage_rich") or "coverage_rich"
        ),
        formal_state_override=args.formal_state,
        realizability_judgment_override=args.realizability_judgment,
        stage_01=stage_01,
        stage_02=stage_02,
        stage_02_5=stage_02_5,
        stage_03=stage_03,
        stage_04=stage_04,
        stage_paths=stage_paths,
        execution_report=execution_report,
        engineering_spec_pack=engineering_spec_pack,
        engineering_spec_pack_claim_control=engineering_spec_pack.with_name(
            f"{engineering_spec_pack.stem}.claim-control.json"
        ),
        implementation_entry=implementation_entry,
        first_pass_audit_path=first_pass_audit_path,
        trace_validation=trace_validation,
        trace_report_text=trace_report_text,
        trace_report_json=trace_report_json,
        phase1_trace_resolution_path=phase1_trace_resolution_path,
        phase1_phase2_coverage_path=phase1_phase2_coverage_path,
        contamination_report_path=contamination_report_path,
        complexity_classification_path=complexity_classification_path,
        complexity_classification_report=complexity_classification_report,
        selected_complexity_profile=selected_complexity_profile,
        complexity_override_justification=complexity_override_justification,
        deployment_posture=deployment_posture,
        baseline_lock=baseline_lock,
        quality_report_path=quality_report_path,
        mermaid_report_path=mermaid_report_path,
        cross_stage_report_path=cross_stage_report_path,
        timing_report=timing_report,
    )


def log_phase2_full_trial_start(context: Phase2FullTrialContext) -> None:
    suggested_complexity_profile = str(context.complexity_classification_report.get("suggested_profile", "standard"))

    print("== Phase-2 Full Trial ==", flush=True)
    print(f"phase1_prd: {context.phase1_prd}", flush=True)
    print(f"output_dir: {context.output_dir}", flush=True)
    print(f"version: {context.version}", flush=True)
    print(f"profile: {context.profile}", flush=True)
    print(f"complexity_profile_suggested: {suggested_complexity_profile}", flush=True)
    print(f"complexity_profile_selected: {context.selected_complexity_profile}", flush=True)
    if context.complexity_override_justification:
        print(
            f"complexity_profile_override_justification: {context.complexity_override_justification}",
            flush=True,
        )
    print(f"deployment_posture_suggested: {context.deployment_posture['suggested']}", flush=True)
    print(f"deployment_posture_selected: {context.deployment_posture['selected']}", flush=True)
    print(f"deployment_posture_selection_mode: {context.deployment_posture['selection_mode']}", flush=True)
    if context.deployment_posture["warning_class"] != "none":
        print(f"deployment_posture_warning_class: {context.deployment_posture['warning_class']}", flush=True)
        print(f"deployment_posture_override_source: {context.deployment_posture['override_source']}", flush=True)
        print(f"deployment_posture_override_reason: {context.deployment_posture['override_reason']}", flush=True)
        print(f"deployment_posture_added_risks: {context.deployment_posture['added_risks']}", flush=True)
    print(f"project_key: {context.project_key}", flush=True)
    print(f"baseline_lock: {context.baseline_lock}", flush=True)
    print(f"optional_stage_02_5: {context.stage_02_5 if context.stage_02_5 else 'not-present'}", flush=True)


def run_phase2_handoff_contamination_preflight(context: Phase2FullTrialContext) -> dict[str, Any]:
    return build_contamination_report_for_path(
        context.phase1_prd,
        boundary="p1-to-p2",
        output_path=context.contamination_report_path,
    )


def render_block(text: str, block_name: str, *, fallback: str = "- missing") -> str:
    block = block_text(text, block_name)
    return block if block else fallback


def render_key_decisions_quick_reference(stage_01_text: str) -> str:
    block = render_block(stage_01_text, "key_architecture_decisions", fallback="")
    if not block.strip():
        return "\n".join(
            [
                "- canonical_reference: `3.7 Key Architecture Decisions`",
                "- decision_count: `0`",
                "- editorial_boundary: Stage-01 key architecture decisions are not present; do not infer ADRs here.",
            ]
        )

    decision_ids = re.findall(
        r"^\s*(?:-\s+)?(?:decision_id|adr_id):\s*`?([^`\n]+?)`?\s*$",
        block,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    titles = [
        match.strip("` ").strip()
        for match in re.findall(r"^\s*(?:-\s+)?title:\s*(.+?)\s*$", block, flags=re.IGNORECASE | re.MULTILINE)
        if match.strip("` ").strip()
    ]
    decision_count = len(decision_ids) or len(titles)
    lines = [
        "- canonical_reference: `3.7 Key Architecture Decisions`",
        "- editorial_boundary: detailed ADR context, decisions, consequences, and evidence stay in Section 3.7; this quick reference avoids duplicating the canonical ADR block.",
        f"- decision_count: `{decision_count}`",
    ]
    if decision_ids:
        lines.append("- decision_ids:")
        lines.extend(f"  - `{decision_id.strip()}`" for decision_id in decision_ids[:8] if decision_id.strip())
    if titles:
        lines.append("- decision_titles:")
        lines.extend(f"  - {title}" for title in titles[:8])
    return "\n".join(lines)


def render_thesis_driven_architecture_handoff(
    stage_04_text: str,
    *,
    fallback_source_note: str = "Stage-04 did not emit a dedicated thesis handoff block.",
) -> str:
    block = render_block(stage_04_text, "thesis_driven_architecture_handoff", fallback="")
    if block.strip():
        return block
    return "\n".join(
        [
            "- thesis_driven_architecture_handoff:",
            "  - implementation_rule: implementation slices must preserve the proof loop before adding lower-proof reporting, CRUD, or record-only convenience surfaces.",
            "  - fallback_scope: bounded ESP fallback; no new architecture fact is introduced beyond the Stage-01 thesis translation and Phase-3 intake contract.",
            f"  - fallback_source_note: {fallback_source_note}",
        ]
    )


def compact_reader_memo_text(value: str, fallback: str, *, max_chars: int = 190) -> str:
    text = re.sub(r"`", "", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip(" -:")
    if not text or text.lower() in {"missing", "not-present", "not present"}:
        text = fallback
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip(" ,;:") + "..."


def first_reader_memo_scalar(block: str, field_names: list[str]) -> str:
    for field_name in field_names:
        value = extract_block_scalar(block, field_name)
        if value:
            return value
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or set(stripped) <= {"-", " "}:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if ":" in stripped:
            _, value = stripped.split(":", 1)
            if value.strip():
                return value.strip()
        return stripped
    return ""


def compact_reader_memo_list(items: list[str], fallback: str, *, limit: int = 4, max_chars: int = 190) -> str:
    cleaned: list[str] = []
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "")).strip(" -:`")
        if text and text not in cleaned:
            cleaned.append(text)
    if not cleaned:
        return fallback
    value = ", ".join(cleaned[:limit])
    if len(cleaned) > limit:
        value += ", ..."
    return compact_reader_memo_text(value, fallback, max_chars=max_chars)


def core_object_surface_from_schema_rows(rows: list[dict[str, str]]) -> str:
    return compact_reader_memo_list(
        [row.get("table_name", "") for row in rows],
        "public-boundary contracts and ownership statements from the ESP",
    )


def render_phase2_handoff_digest_lines(
    *,
    business_thesis: str,
    core_objects: str,
    p3_entry: str,
    wp_ids: str,
    rbi_ids: str,
    indent: str = "",
) -> list[str]:
    business_thesis = compact_reader_memo_text(
        business_thesis,
        "Preserve the Phase-1 business thesis through Phase-2 architecture decisions.",
    )
    core_objects = compact_reader_memo_text(
        core_objects,
        "public-boundary contracts and ownership statements from the ESP",
    )
    p3_entry = compact_reader_memo_text(
        p3_entry,
        "preserve the Phase-2 proof loop and trace obligations",
        max_chars=135,
    )
    return [
        f"{indent}- handoff_digest:",
        f"{indent}  - business_thesis: {business_thesis}",
        f"{indent}  - core_objects: {core_objects}",
        f"{indent}  - open_truths: preserve review-bound ownership for {rbi_ids}; do not convert unresolved RBI items into implementation claims.",
        f"{indent}  - p3_entry: start from {wp_ids}; {p3_entry}",
        f"{indent}  - non_claims: no UAT, owner sign-off, production readiness, budget approval, or external adoption proof is claimed here.",
    ]


def render_esp_reader_decision_brief(
    *,
    architecture_choice: str,
    business_proof_fit: str,
    p3_preserve: str,
    wp_ids: str,
    rbi_ids: str,
    has_optional_stage_02_5: bool,
    has_existing_system_change: bool,
) -> str:
    architecture_choice = compact_reader_memo_text(
        architecture_choice,
        "Preserve the Stage-01 boundary and key architecture decisions before schema/API detail.",
        max_chars=145,
    )
    business_proof_fit = compact_reader_memo_text(
        business_proof_fit,
        "Keep implementation tied to the Phase-1 business proof loop instead of reverting to CRUD or report-only slices.",
        max_chars=145,
    )
    p3_preserve = compact_reader_memo_text(
        p3_preserve,
        "Phase-3 must preserve the proof loop, operation obligations, traceability, and action-card inputs.",
        max_chars=145,
    )
    lines = [
        "### 2.0 Reader Decision Brief",
        "Read this page first; it is the short human route through the ESP, while the large tables remain contract evidence for runtime consumers.",
        f"- Architecture judgment: {architecture_choice}",
        f"- Business proof fit: {business_proof_fit}",
        f"- P3 entry: start from {wp_ids}; {p3_preserve}",
        f"- Open truths: keep {rbi_ids} review-bound until stronger evidence exists.",
        "- Evidence appendix: Sections 4-10 preserve decomposition, schema, API, risk, and implementation contract detail.",
        "- Non-claims: no UAT, owner sign-off, production readiness, budget approval, or external adoption proof is claimed here.",
    ]
    if has_optional_stage_02_5:
        lines.append("- Optional integration lane: read Stage-02.5 before changing provider/auth/adapter behavior.")
    if has_existing_system_change:
        lines.append("- existing-system change intake: read it before changing inherited storage, API, migration, rollback, or compatibility behavior.")
    return "\n".join(lines)


def render_esp_reader_memo(
    stage_01_text: str,
    stage_04_text: str,
    wp_registry: list[dict[str, str]],
    rbi_registry: list[dict[str, str]],
    *,
    core_object_surface: str = "",
    has_optional_stage_02_5: bool = False,
    has_existing_system_change: bool = False,
) -> str:
    boundary_block = render_block(stage_01_text, "system_boundary_statement", fallback="")
    pressure_block = render_block(stage_01_text, "chosen_thesis_architecture_pressure", fallback="")
    translation_block = render_block(stage_01_text, "thesis_driven_architecture_translation", fallback="")
    handoff_block = render_thesis_driven_architecture_handoff(stage_04_text)
    architecture_choice = compact_reader_memo_text(
        first_reader_memo_scalar(
            translation_block,
            ["architecture_posture", "architecture_choice", "design_implication", "technical_translation"],
        )
        or first_reader_memo_scalar(boundary_block, ["system_boundary_statement", "boundary_statement"]),
        "Preserve the Stage-01 boundary and key architecture decisions before schema/API detail.",
    )
    proof_loop = compact_reader_memo_text(
        first_reader_memo_scalar(
            pressure_block,
            ["commercial_proof_supported_by", "business_proof_loop", "design_implication"],
        ),
        "Keep implementation tied to the Phase-1 business proof loop instead of reverting to CRUD or report-only slices.",
    )
    p3_preserve = compact_reader_memo_text(
        first_reader_memo_scalar(
            handoff_block,
            ["implementation_rule", "phase3_entry", "handoff_rule", "fallback_scope"],
        ),
        "Phase-3 must preserve the proof loop, operation obligations, traceability, and action-card inputs.",
    )
    wp_ids = ", ".join(f"`{row['wp_id']}`" for row in wp_registry[:3] if row.get("wp_id")) or "`WP registry missing`"
    rbi_ids = ", ".join(f"`{row['rbi_id']}`" for row in rbi_registry[:3] if row.get("rbi_id")) or "`RBI registry missing`"
    core_objects = compact_reader_memo_text(
        core_object_surface,
        "public-boundary contracts and ownership statements from the ESP",
    )
    boundary_notes = [
        "Main reader path is the memo plus Section 3 decision posture; Sections 4-10 are contract/evidence surfaces for runtime consumers.",
        "Stage-03 tables remain contract/evidence surfaces; read them after the memo and Section 3 decision posture.",
        f"Start implementation planning from {wp_ids}; preserve review-bound ownership for {rbi_ids}.",
        "Do not promote UAT, owner sign-off, production readiness, or budget approval without upstream evidence.",
    ]
    if has_optional_stage_02_5:
        boundary_notes.append("Stage-02.5 provider/auth/adapter choices must be read before changing integration behavior.")
    if has_existing_system_change:
        boundary_notes.append("Existing-system change intake must be read before changing inherited compatibility behavior.")
    return "\n".join(
        [
            "- reader_memo:",
            f"  - architecture_choice: {architecture_choice}",
            f"  - business_proof_fit: {proof_loop}",
            f"  - p3_must_preserve: {p3_preserve}",
            *render_phase2_handoff_digest_lines(
                business_thesis=proof_loop,
                core_objects=core_objects,
                p3_entry=p3_preserve,
                wp_ids=wp_ids,
                rbi_ids=rbi_ids,
                indent="  ",
            ),
            "  - evidence_boundary:",
            *[f"    - {note}" for note in boundary_notes],
        ]
    )


def render_heading(text: str, heading: str, *, fallback: str = "- missing") -> str:
    section = markdown_heading_section(text, heading)
    if not section:
        return fallback
    body_lines = section.splitlines()[1:]
    body = "\n".join(body_lines).strip()
    return body if body else fallback


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return render_markdown_table(headers, rows)


def split_inline_items(value: str) -> list[str]:
    parts = re.split(r",|/|;|\band\b", value, flags=re.IGNORECASE)
    return [item.strip().strip("`") for item in parts if item.strip().strip("`")]


def work_package_rows(stage_04_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_04_text, "implementation_task_sketch"),
        {"wp_id", "scope", "acceptance_criteria", "estimated_effort", "depends_on", "linked_rbi_or_slice"},
    )


def rbi_rows(stage_04_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_04_text, "unresolved_risks_and_review_bound_items"),
        {"rbi_id", "item", "risk_level", "spike_wp", "responsible_party", "blocks_which_wp"},
    )


def contract_trace_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "contract_trace_registry"),
        {"trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook"},
    )


def schema_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "schema_draft"),
        {"table_name", "ownership", "pk", "fk"},
    )


def api_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "api_endpoint_draft"),
        {
            "endpoint_name",
            "method",
            "path",
            "purpose",
            "request_body_example",
            "response_body_example",
            "rate_limit_policy",
            "pagination_rule",
            "failure_codes",
        },
    )


def build_operation_design_source_rows(
    api_rows: list[dict[str, str]], contract_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    source_counters: dict[str, int] = {"P2-FLOW": 0, "P2-SEQ": 0, "P2-STATE": 0, "P2-RP": 0}
    for api in api_rows:
        operation_id = str(api.get("endpoint_name", "")).strip()
        if not operation_id:
            continue
        risk = classify_operation(
            {
                "operation_id": operation_id,
                "method": api.get("method", ""),
                "path": api.get("path", ""),
                "summary": api.get("purpose", ""),
            }
        )
        contract_trace_id = _find_contract_trace_id(operation_id, contract_rows)
        for source_type in risk["required_source_types"]:
            if source_type not in source_counters:
                continue
            source_counters[source_type] += 1
            rows.append(
                {
                    "source_id": f"{source_type}-{source_counters[source_type]:03d}",
                    "source_type": source_type,
                    "operation_id": operation_id,
                    "source_stage": "Stage-03" if source_type in {"P2-FLOW", "P2-STATE"} else "Stage-04",
                    "evidence_ref": f"{operation_id} {source_type} operation-bound design source",
                    "trace_status": "available",
                    "upstream_contract_trace_id": contract_trace_id,
                }
            )
    return rows


def operation_design_source_registry_markdown(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- operation_design_source_registry missing"
    return markdown_table(
        ["source_id", "source_type", "operation_id", "source_stage", "evidence_ref", "trace_status", "upstream_contract_trace_id"],
        [
            [
                row.get("source_id", ""),
                row.get("source_type", ""),
                row.get("operation_id", ""),
                row.get("source_stage", ""),
                row.get("evidence_ref", ""),
                row.get("trace_status", ""),
                row.get("upstream_contract_trace_id", ""),
            ]
            for row in rows
        ],
    )


def _find_contract_trace_id(operation_id: str, contract_rows: list[dict[str, str]]) -> str:
    row = _find_contract_row(operation_id, contract_rows)
    return row.get("trace_id", "").strip() if row else ""


def _find_contract_row(operation_id: str, contract_rows: list[dict[str, str]]) -> dict[str, str] | None:
    normalized = operation_id.strip().lower()
    for row in contract_rows:
        if row.get("trace_subject", "").strip().lower() == normalized:
            return row
    for row in contract_rows:
        subject = row.get("trace_subject", "").strip().lower()
        hook = row.get("verification_hook", "").strip().lower()
        downstream = row.get("downstream_artifact_id", "").strip().lower()
        haystack = " ".join(part for part in (subject, hook, downstream) if part)
        if normalized and haystack and (normalized in haystack or haystack in normalized):
            return row
    return None


def _field_items(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().strip("`") for item in value if str(item).strip().strip("`")]
    if isinstance(value, (tuple, set)):
        return [str(item).strip().strip("`") for item in value if str(item).strip().strip("`")]
    return split_inline_items(str(value or ""))


def _row_items(row: dict[str, object], keys: list[str]) -> list[str]:
    items: list[str] = []
    for key in keys:
        for item in _field_items(row.get(key, "")):
            if item and item not in items:
                items.append(item)
    return items


def _index_design_sources_by_operation(
    design_source_rows: list[dict[str, str]] | None,
) -> dict[tuple[str, str], list[dict[str, str]]]:
    indexed: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in design_source_rows or []:
        operation_id = str(row.get("operation_id", "")).strip().lower()
        source_type = str(row.get("source_type", "")).strip()
        source_id = str(row.get("source_id", "")).strip()
        if not operation_id or not source_type or not source_id:
            continue
        indexed.setdefault((operation_id, source_type), []).append(row)
    return indexed


def build_operation_source_obligation_rows(
    api_rows: list[dict[str, str]],
    contract_rows: list[dict[str, str]],
    design_source_rows: list[dict[str, str]] | None = None,
    contract_phase1_trace_map: dict[str, list[str]] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    design_sources = _index_design_sources_by_operation(design_source_rows)
    contract_phase1_trace_map = contract_phase1_trace_map or {}
    for api in api_rows:
        operation_id = api.get("endpoint_name", "").strip()
        if not operation_id:
            continue
        risk = classify_operation(
            {
                "operation_id": operation_id,
                "method": api.get("method", ""),
                "path": api.get("path", ""),
                "summary": api.get("purpose", ""),
            }
        )
        contract_row = _find_contract_row(operation_id, contract_rows) or {}
        contract_trace_id = str(contract_row.get("trace_id", "")).strip()
        upstream_p1_trace_ids = _row_items(
            api,
            ["upstream_trace_ids", "upstream_p1_trace_ids", "p1_trace_ids", "phase1_upstream_trace_ids"],
        )
        for item in _row_items(
            contract_row,
            ["upstream_trace_ids", "upstream_p1_trace_ids", "p1_trace_ids", "phase1_upstream_trace_ids"],
        ):
            if item not in upstream_p1_trace_ids:
                upstream_p1_trace_ids.append(item)
        for item in contract_phase1_trace_map.get(contract_trace_id, []):
            if item not in upstream_p1_trace_ids:
                upstream_p1_trace_ids.append(item)
        bound_source_ids = [contract_trace_id] if contract_trace_id else []
        review_bound_missing_sources: list[str] = []
        for source_type in risk["required_source_types"]:
            if source_type == "P2-CTR":
                if not contract_trace_id:
                    review_bound_missing_sources.append("P2-CTR")
                continue
            matches = design_sources.get((operation_id.lower(), source_type), [])
            if matches:
                bound_source_ids.extend(str(row.get("source_id", "")).strip() for row in matches if str(row.get("source_id", "")).strip())
            elif source_type in {"P2-FLOW", "P2-SEQ", "P2-STATE", "P2-RP"}:
                review_bound_missing_sources.append(source_type)
        rows.append(
            {
                "operation_id": operation_id,
                "api_endpoint": str(api.get("path", "")).strip(),
                "http_method": str(api.get("method", "")).strip().upper(),
                "contract_trace_id": contract_trace_id,
                "risk_tier": risk["risk_tier"],
                "risk_triggers": risk["risk_triggers"],
                "upstream_p1_trace_ids": upstream_p1_trace_ids,
                "required_source_types": risk["required_source_types"],
                "not_required_source_types": risk["not_required_source_types"],
                "bound_source_ids": list(dict.fromkeys(bound_source_ids)),
                "review_bound_missing_sources": review_bound_missing_sources,
                "source_files": ["stage-03-data-storage-and-interface-design.md", "stage-04-integration-and-delivery-design.md"],
                "source_anchors": [operation_id.lower()],
                "source_requirement_status": "review-bound" if review_bound_missing_sources else "sufficient",
                "classification_rationale": risk["classification_rationale"],
            }
        )
    return rows


def operation_source_obligation_markdown(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "- operation_source_obligation_matrix missing"
    return markdown_table(
        [
            "operation_id",
            "contract_trace_id",
            "risk_tier",
            "risk_triggers",
            "required_source_types",
            "not_required_source_types",
            "bound_source_ids",
            "review_bound_missing_sources",
            "classification_rationale",
        ],
        [
            [
                str(row.get("operation_id", "")),
                str(row.get("contract_trace_id", "")),
                str(row.get("risk_tier", "")),
                ", ".join(str(item) for item in row.get("risk_triggers", [])),
                ", ".join(str(item) for item in row.get("required_source_types", [])),
                ", ".join(str(item) for item in row.get("not_required_source_types", [])),
                ", ".join(str(item) for item in row.get("bound_source_ids", [])),
                ", ".join(str(item) for item in row.get("review_bound_missing_sources", [])),
                str(row.get("classification_rationale", "")),
            ]
            for row in rows
        ],
    )


def load_business_value_signal_registry(phase1_prd: Path) -> list[dict[str, str]]:
    if not phase1_prd.exists():
        return []
    text = phase1_prd.read_text(encoding="utf-8")
    section = markdown_heading_section(text, "Business Value Signal Registry") or text
    return table_rows_from_block(
        section,
        {
            "value_signal_id",
            "upstream_trace_id",
            "business_value_weight",
            "business_value_reason",
            "anti_demo_risk",
            "core_success_path",
            "downstream_depth_hint",
            "evidence_or_review_bound",
        },
    )


def _operation_text(row: dict[str, object]) -> str:
    return " ".join(str(row.get(key, "")) for key in ("operation_id", "contract_trace_id", "classification_rationale"))


def _first_non_empty_p1_trace_ids(value_registry: list[dict[str, str]]) -> list[str]:
    for value_row in value_registry:
        p1_trace_ids = split_inline_items(str(value_row.get("upstream_trace_id", "")))
        if p1_trace_ids:
            return p1_trace_ids
    return []


def _best_default_value_signal(value_registry: list[dict[str, str]]) -> dict[str, str]:
    if not value_registry:
        return {}
    ranked = sorted(
        enumerate(value_registry),
        key=lambda item: (normalize_business_value_weight(item[1].get("business_value_weight")), -item[0]),
        reverse=True,
    )
    return ranked[0][1]


def build_p1_value_to_p2_operation_resolution_rows(
    value_registry: list[dict[str, str]],
    operation_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    operations = [row for row in operation_rows if str(row.get("operation_id", "")).strip()]
    covered_operations: set[str] = set()

    def explicit_match(p1_trace_ids: list[str], value_row: dict[str, str]) -> dict[str, object]:
        p1_set = set(p1_trace_ids)
        value_contract_ids = set(_row_items(value_row, ["p2_contract_ids", "contract_trace_id", "p2_contract_trace_ids"]))
        for operation in operations:
            operation_trace_ids = set(
                _row_items(
                    operation,
                    ["upstream_p1_trace_ids", "upstream_trace_ids", "p1_trace_ids", "phase1_upstream_trace_ids"],
                )
            )
            operation_contract_ids = set(_row_items(operation, ["p2_contract_ids", "contract_trace_id"]))
            if p1_set and operation_trace_ids and p1_set.intersection(operation_trace_ids):
                return operation
            if value_contract_ids and operation_contract_ids and value_contract_ids.intersection(operation_contract_ids):
                return operation
        return {}

    for value_index, value_row in enumerate(value_registry, start=1):
        value_signal_id = str(value_row.get("value_signal_id") or f"BVS-{value_index:03d}").strip()
        p1_trace_ids = split_inline_items(str(value_row.get("upstream_trace_id", "")))
        weight = normalize_business_value_weight(value_row.get("business_value_weight"))
        reason = str(value_row.get("business_value_reason", "")).strip()
        chosen = explicit_match(p1_trace_ids, value_row)
        matched_by_explicit_trace = bool(chosen)
        if not chosen and operations:
            chosen = operations[min(value_index - 1, len(operations) - 1)]
        operation_id = str(chosen.get("operation_id", "")).strip()
        status = "mapped" if operation_id and matched_by_explicit_trace else "review-bound-fallback" if operation_id else "review-bound"
        if weight in {"BV2", "BV3"} and not operation_id:
            status = "p1_value_to_p2_operation_resolution_missing"
        if operation_id:
            covered_operations.add(operation_id)
        rows.append(
            {
                "value_signal_id": value_signal_id,
                "p1_trace_ids": p1_trace_ids,
                "business_value_weight": weight,
                "business_value_reason": reason,
                "operation_id": operation_id,
                "api_endpoint": str(chosen.get("api_endpoint", "")).strip(),
                "http_method": str(chosen.get("http_method", "")).strip(),
                "risk_tier": str(chosen.get("risk_tier", "")).strip(),
                "contract_trace_id": str(chosen.get("contract_trace_id", "")).strip(),
                "p2_contract_ids": [str(chosen.get("contract_trace_id", "")).strip()] if str(chosen.get("contract_trace_id", "")).strip() else [],
                "source_files": list(chosen.get("source_files", [])),
                "source_anchors": list(chosen.get("source_anchors", [])),
                "source_requirement_status": str(chosen.get("source_requirement_status", "")).strip(),
                "resolution_status": status,
                "review_bound_reason": "" if status == "mapped" else "semantic/order fallback only; no explicit P1 trace or P2 contract join",
            }
        )
    default_value = _best_default_value_signal(value_registry)
    default_trace_ids = _first_non_empty_p1_trace_ids(value_registry)
    default_weight = normalize_business_value_weight(default_value.get("business_value_weight"))
    default_reason = str(default_value.get("business_value_reason", "")).strip()
    default_signal_id = str(default_value.get("value_signal_id", "review-bound")).strip() or "review-bound"
    for op in operations:
        operation_id = str(op.get("operation_id", "")).strip()
        if operation_id in covered_operations:
            continue
        if default_trace_ids:
            rows.append(
                {
                    "value_signal_id": default_signal_id,
                    "p1_trace_ids": list(default_trace_ids),
                    "business_value_weight": default_weight,
                    "business_value_reason": default_reason or "P1 business value signal propagated as review-bound operation coverage",
                    "operation_id": operation_id,
                    "api_endpoint": str(op.get("api_endpoint", "")).strip(),
                    "http_method": str(op.get("http_method", "")).strip(),
                    "risk_tier": str(op.get("risk_tier", "")).strip(),
                    "contract_trace_id": str(op.get("contract_trace_id", "")),
                    "p2_contract_ids": [str(op.get("contract_trace_id", "")).strip()] if str(op.get("contract_trace_id", "")).strip() else [],
                    "source_files": list(op.get("source_files", [])),
                    "source_anchors": list(op.get("source_anchors", [])),
                    "source_requirement_status": str(op.get("source_requirement_status", "")).strip(),
                    "resolution_status": "review-bound-fallback",
                    "review_bound_reason": "operation_not_directly_mapped_to_value_signal; inherited nearest available P1 trace for review-bound continuity",
                }
            )
        else:
            rows.append(
                {
                    "value_signal_id": "review-bound",
                    "p1_trace_ids": [],
                    "business_value_weight": "review-bound",
                    "business_value_reason": "P1 business_value_signal_registry missing",
                    "operation_id": operation_id,
                    "api_endpoint": str(op.get("api_endpoint", "")).strip(),
                    "http_method": str(op.get("http_method", "")).strip(),
                    "risk_tier": str(op.get("risk_tier", "")).strip(),
                    "contract_trace_id": str(op.get("contract_trace_id", "")),
                    "p2_contract_ids": [str(op.get("contract_trace_id", "")).strip()] if str(op.get("contract_trace_id", "")).strip() else [],
                    "source_files": list(op.get("source_files", [])),
                    "source_anchors": list(op.get("source_anchors", [])),
                    "source_requirement_status": str(op.get("source_requirement_status", "")).strip(),
                    "resolution_status": "review-bound",
                    "review_bound_reason": "p1_value_signal_registry_missing",
                }
            )
    return rows


def contract_phase1_trace_map_from_report(report: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for row in report.get("rows", []):
        if str(row.get("row_group", "")).strip() != "contract_trace_units":
            continue
        artifact_id = str(row.get("artifact_id", "")).strip()
        if not artifact_id:
            continue
        trace_ids: list[str] = []
        for key in ("explicit_upstream_trace_ids", "phase1_upstream_trace_ids"):
            for item in row.get(key, []):
                value = str(item).strip()
                if value and value not in trace_ids:
                    trace_ids.append(value)
        if trace_ids:
            mapping[artifact_id] = trace_ids
    return mapping


def derive_implementation_complexity(operation_row: dict[str, object]) -> str:
    required = list(operation_row.get("required_source_types", []))
    missing = list(operation_row.get("review_bound_missing_sources", []))
    risk = str(operation_row.get("risk_tier", ""))
    if risk.startswith("HR-") and len(required) >= 4:
        return "IC3"
    if risk.startswith("HR-") or len(required) >= 3 or missing:
        return "IC2"
    if risk.startswith("MR-") or len(required) >= 2:
        return "IC1"
    return "IC0"


def required_card_type_for_acd(acd_level: str) -> str:
    return {
        "ACD-3": "deep-action-card",
        "ACD-2": "standard-action-card",
        "ACD-1": "compact-action-card",
        "ACD-0": "checklist-card",
    }.get(acd_level, "review-bound-card")


def build_implementation_depth_obligation_rows(
    operation_rows: list[dict[str, object]],
    resolution_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_operation = {str(row.get("operation_id", "")): row for row in resolution_rows if str(row.get("operation_id", ""))}
    rows: list[dict[str, object]] = []
    for op in operation_rows:
        operation_id = str(op.get("operation_id", "")).strip()
        resolution = by_operation.get(operation_id, {})
        weight = normalize_business_value_weight(resolution.get("business_value_weight"))
        complexity = derive_implementation_complexity(op)
        acd = derive_acd_level(weight, op.get("risk_tier"), complexity, list(op.get("risk_triggers", [])))
        rows.append(
            {
                "operation_id": operation_id,
                "contract_trace_id": str(op.get("contract_trace_id", "")),
                "upstream_p1_trace_ids": list(resolution.get("p1_trace_ids", [])),
                "business_value_weight": weight,
                "engineering_risk_tier": str(op.get("risk_tier", "")),
                "implementation_complexity": complexity,
                "acd_level": acd["acd_level"],
                "acd_triggers": acd["acd_triggers"],
                "required_card_type": required_card_type_for_acd(str(acd["acd_level"])),
                "required_reason": "; ".join(str(item) for item in acd["acd_triggers"]),
                "required_tests": ["unit", "contract", "integration"] if str(acd["acd_level"]) in {"ACD-2", "ACD-3"} else ["unit"],
                "required_source_types": list(op.get("required_source_types", [])),
                "bound_source_ids": list(op.get("bound_source_ids", [])),
                "review_bound_missing_sources": list(op.get("review_bound_missing_sources", [])),
            }
        )
    return rows


def _singular_relation_token(token: str) -> str:
    if len(token) > 3 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _relation_tokens(value: object) -> set[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    tokens = re.findall(r"[A-Za-z0-9]+", text.replace("_", " ").replace("-", " ").lower())
    return {_singular_relation_token(token) for token in tokens if token}


def _schema_related_operations(
    schema: dict[str, str],
    operation_rows: list[dict[str, object]],
    api_rows_by_operation: dict[str, dict[str, str]],
) -> list[str]:
    schema_tokens = _relation_tokens(schema.get("table_name", ""))
    if not schema_tokens:
        return []
    related: list[str] = []
    for operation in operation_rows:
        operation_id = str(operation.get("operation_id", "")).strip()
        if not operation_id:
            continue
        api = api_rows_by_operation.get(operation_id, {})
        operation_tokens = set()
        for value in (
            operation_id,
            operation.get("api_endpoint", ""),
            " ".join(str(item) for item in operation.get("source_anchors", [])),
            api.get("path", ""),
        ):
            operation_tokens.update(_relation_tokens(value))
        if schema_tokens.issubset(operation_tokens):
            related.append(operation_id)
    return list(dict.fromkeys(related))


def build_implementation_component_catalog_rows(
    api_rows: list[dict[str, str]],
    schema_rows: list[dict[str, str]],
    operation_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    component_index = 1
    op_by_name = {str(row.get("operation_id", "")): row for row in operation_rows}
    api_by_operation = {
        str(row.get("endpoint_name", "")).strip(): row
        for row in api_rows
        if str(row.get("endpoint_name", "")).strip()
    }
    seen_service_keys: set[tuple[str, str]] = set()
    for api in api_rows:
        operation_id = str(api.get("endpoint_name", "")).strip()
        if not operation_id:
            continue
        operation_row = op_by_name.get(operation_id, {})
        contract_trace_id = str(operation_row.get("contract_trace_id", ""))
        service_key = (operation_id, contract_trace_id)
        if service_key in seen_service_keys:
            continue
        seen_service_keys.add(service_key)
        module_hint = operation_id
        for suffix in ("Status", "Decision", "Finding", "Scope"):
            module_hint = module_hint.replace(suffix, "")
        rows.append(
            {
                "component_id": f"P2-CMP-{component_index:03d}",
                "component_type": "Service",
                "owning_module": module_hint or operation_id,
                "source_stage": "Stage-03",
                "source_ids": [contract_trace_id],
                "related_operations": [operation_id],
                "related_schema_or_domain_objects": [],
                "target_path_hint": f"service/{operation_id}",
                "catalog_status": "defined" if operation_row else "review-bound",
            }
        )
        component_index += 1
    for schema in schema_rows:
        table_name = str(schema.get("table_name", "")).strip()
        if not table_name:
            continue
        related_operations = _schema_related_operations(schema, operation_rows, api_by_operation)
        rows.append(
            {
                "component_id": f"P2-CMP-{component_index:03d}",
                "component_type": "Repository",
                "owning_module": str(schema.get("ownership", "")).strip() or table_name,
                "source_stage": "Stage-03",
                "source_ids": [table_name],
                "related_operations": related_operations,
                "related_schema_or_domain_objects": [table_name],
                "target_path_hint": f"repository/{table_name}",
                "catalog_status": "defined",
            }
        )
        component_index += 1
    return rows


def build_component_action_card_obligation_rows(
    catalog_rows: list[dict[str, object]],
    depth_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    depth_by_operation = {str(row.get("operation_id", "")): row for row in depth_rows}
    rows: list[dict[str, object]] = []
    for component in catalog_rows:
        related_operations = [str(item) for item in component.get("related_operations", []) if str(item)]
        related_depth = [depth_by_operation[item] for item in related_operations if item in depth_by_operation]
        selected = max(related_depth, key=lambda row: str(row.get("acd_level", "")), default={})
        missing = list(selected.get("review_bound_missing_sources", []))
        operation_source_ids = [item for item in selected.get("bound_source_ids", []) if str(item).strip()]
        p1_trace_ids = list(selected.get("upstream_p1_trace_ids", []))
        available = list(
            dict.fromkeys(
                [item for item in component.get("source_ids", []) if str(item).strip()]
                + operation_source_ids
                + p1_trace_ids
            )
        )
        status = "sufficient" if not missing and available and p1_trace_ids else "partial" if available else "review-bound"
        rows.append(
            {
                "component_id": str(component.get("component_id", "")),
                "component_type": str(component.get("component_type", "")),
                "upstream_operation_ids": related_operations,
                "upstream_p1_trace_ids": p1_trace_ids,
                "business_value_weight": str(selected.get("business_value_weight", "review-bound")),
                "engineering_risk_tier": str(selected.get("engineering_risk_tier", "review-bound")),
                "implementation_complexity": str(selected.get("implementation_complexity", "review-bound")),
                "acd_level": str(selected.get("acd_level", "review-bound")),
                "required_card_type": str(selected.get("required_card_type", "review-bound-card")),
                "required_reason": str(selected.get("required_reason", "component obligation derived from P2 depth row")),
                "required_tests": list(selected.get("required_tests", [])),
                "required_source_ids": list(dict.fromkeys(operation_source_ids + p1_trace_ids + list(selected.get("review_bound_missing_sources", [])))),
                "available_source_ids": available,
                "missing_source_types": missing,
                "source_sufficiency_status": status,
                "review_bound_missing_sources": missing,
            }
        )
    return rows


def generic_matrix_markdown(rows: list[dict[str, object]], columns: list[str], missing_label: str) -> str:
    if not rows:
        return f"- {missing_label} missing"
    return markdown_table(
        columns,
        [
            [
                ", ".join(str(item) for item in row.get(column, []))
                if isinstance(row.get(column), list)
                else str(row.get(column, ""))
                for column in columns
            ]
            for row in rows
        ],
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_validation_result(text: str) -> str:
    upper = text.upper()
    if "PASS" in upper:
        return "pass"
    if "FAIL" in upper:
        return "fail"
    return "unknown"


def evaluate_trace_runtime_contract(report: dict) -> tuple[str, list[str]]:
    issues: list[str] = []
    required_scalar_fields = (
        "registry_db_path",
        "trace_registry_root",
        "project_key",
        "project_root",
        "project_scope",
        "schema_version",
    )
    for field in required_scalar_fields:
        if not str(report.get(field, "")).strip():
            issues.append(f"missing {field}")
    if not isinstance(report.get("artifacts"), list):
        issues.append("missing artifacts list")
    if not isinstance(report.get("links"), list):
        issues.append("missing links list")
    if report.get("artifact_count") != len(report.get("artifacts", [])):
        issues.append("artifact_count does not match artifacts list")
    if report.get("link_count") != len(report.get("links", [])):
        issues.append("link_count does not match links list")
    verdict = "pass" if not issues else "fail"
    return verdict, issues


def summarize_first_pass_audit(audit_report: dict[str, Any]) -> str:
    status = str(audit_report.get("status", "invalid-root"))
    if status == "wrapper-closed":
        return "manifest, authored Stage outputs, and wrapper artifacts are all present in the case root"
    if status == "authored-first-pass":
        return "manifest and authored Stage outputs are present; wrapper closure can proceed"
    if status == "scaffold-only":
        return "Stage files are still scaffold targets, so the wrapper must not treat the case as authored design output"
    return "case-root hygiene is incomplete, so this run cannot be treated as clean fresh first-pass evidence"


def evaluate_first_pass_audit_gate(audit_report: dict[str, Any]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    missing_stage_files = [str(item) for item in audit_report.get("missing_stage_files", []) if str(item).strip()]
    stub_stage_files = [str(item) for item in audit_report.get("stub_stage_files", []) if str(item).strip()]
    optional_stub_stage_files = [
        str(item) for item in audit_report.get("optional_stub_stage_files", []) if str(item).strip()
    ]

    if missing_stage_files:
        blockers.append("missing stage files: " + ", ".join(missing_stage_files))
    if stub_stage_files:
        blockers.append("stage files still scaffold-only: " + ", ".join(stub_stage_files))
    if optional_stub_stage_files:
        blockers.append("optional stage files still scaffold-only: " + ", ".join(optional_stub_stage_files))
    if not blockers and not bool(audit_report.get("passed")):
        blockers.extend(str(item) for item in audit_report.get("issues", []) if str(item).strip())

    return not blockers, blockers


def table_rows_from_block(block: str, required_headers: set[str]) -> list[dict[str, str]]:
    return table_rows_with_required_headers(block, required_headers)


def resolve_phase1_prototype_spec_path(phase1_prd: Path) -> Path | None:
    for candidate in ("prototype-spec.md", "prototype_spec.md"):
        path = phase1_prd.parent / candidate
        if path.exists():
            return path
    return None


def section_by_heading_keyword(text: str, keyword: str) -> str:
    lines = text.splitlines()
    start = None
    level = 0
    for idx, line in enumerate(lines):
        match = re.match(r"^(#+)\s+.*" + re.escape(keyword) + r".*$", line, flags=re.IGNORECASE)
        if match:
            start = idx
            level = len(match.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        match = re.match(r"^(#+)\s+", lines[idx])
        if match and len(match.group(1)) <= level:
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def prototype_page_map_rows(prototype_spec_path: Path | None) -> list[dict[str, str]]:
    rows = _extract_page_map_from_prototype_spec(prototype_spec_path)
    normalized: list[dict[str, str]] = []
    for row in rows:
        normalized_row = dict(row)
        normalized_row["route_pattern"] = str(row.get("route_pattern") or row.get("route") or "").strip()
        normalized_row["parent_page"] = str(row.get("parent_page") or row.get("page_role") or "").strip()
        normalized.append(normalized_row)
    return normalized


def prototype_page_briefs(prototype_spec_path: Path | None) -> dict[str, dict[str, str | list[str]]]:
    if not prototype_spec_path or not prototype_spec_path.exists():
        return {}
    text = prototype_spec_path.read_text(encoding="utf-8")
    heading_pattern = re.compile(r"^### Page Brief:\s+(.+?)\s+\((P\d+)\)\s*$", flags=re.MULTILINE)
    matches = list(heading_pattern.finditer(text))
    briefs: dict[str, dict[str, str | list[str]]] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        page_id = match.group(2).strip()
        fields: dict[str, str | list[str]] = {
            "page_name": match.group(1).strip(),
            "secondary_support_regions": [],
            "core_information_blocks": [],
            "core_actions": [],
        }
        current_list_key = ""
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            field_match = re.match(r"^- \*\*(.+?)\*\*:\s*(.*)$", line)
            if field_match:
                key = field_match.group(1).strip()
                value = field_match.group(2).strip().strip("`")
                normalized_key = key.lower().replace(" ", "_")
                current_list_key = normalized_key
                if normalized_key in {"secondary_support_regions", "core_information_blocks", "core_actions"}:
                    fields.setdefault(normalized_key, [])
                else:
                    fields[normalized_key] = value
                continue
            list_match = re.match(r"^- `?(.+?)`?$", line)
            if list_match and current_list_key in {"secondary_support_regions", "core_information_blocks", "core_actions"}:
                existing = fields.setdefault(current_list_key, [])
                if isinstance(existing, list):
                    existing.append(list_match.group(1).strip())
        briefs[page_id] = fields
    return briefs


def interaction_pattern_for_blueprint(page_blueprint_type: str) -> str:
    mapping = {
        "dashboard": "Dashboard-Summary",
        "analysis-board": "Master-Detail",
        "decision-workbench": "Decision-Workbench",
        "execution-workbench": "List-Kanban",
        "setup-flow": "Setup-Flow",
        "review-decision": "Review-Board",
        "detail-view": "Detail-Form",
        "list-view": "List-Kanban",
    }
    return mapping.get(page_blueprint_type.strip().lower(), "Detail-Form")


def build_frontend_surface_architecture_section(phase1_prd: Path, stage_04_text: str) -> str:
    prototype_spec_path = resolve_phase1_prototype_spec_path(phase1_prd)
    page_rows = prototype_page_map_rows(prototype_spec_path)
    page_briefs = prototype_page_briefs(prototype_spec_path)
    if not page_rows:
        return "\n".join(
            [
                "### 10.1 Frontend Surface Architecture",
                "- missing",
                "- note: no Phase-1 `prototype-spec.md` page map was available, so frontend surface architecture could not be compiled into implementation-facing output",
            ]
        )

    page_component_rows: list[list[str]] = []
    interaction_rows: list[list[str]] = []
    state_rows: list[list[str]] = []
    adjacency_rows: list[list[str]] = []
    contract_rows: list[list[str]] = []
    page_name_by_id = {str(row["page_id"]).strip(): str(row["page_name"]).strip() for row in page_rows}
    child_map: dict[str, list[str]] = {}
    root_pages: list[str] = []
    for row in page_rows:
        page_id = str(row["page_id"]).strip()
        parent_page = str(row.get("parent_page", "")).strip()
        if parent_page and parent_page != "—":
            child_map.setdefault(parent_page, []).append(page_id)
        else:
            root_pages.append(page_id)

    def add_component_row(page_id: str, page_name: str, region: str, component_type: str) -> None:
        page_component_rows.append([page_id, page_name, region, component_type])

    for row in page_rows:
        page_id = str(row["page_id"]).strip()
        page_name = str(row["page_name"]).strip()
        page_blueprint_type = str(row["page_blueprint_type"]).strip()
        primary_action = str(row["primary_action"]).strip()
        brief = page_briefs.get(page_id, {})
        primary_region = str(brief.get("primary_work_region", "") or "TBD").strip() or "TBD"
        add_component_row(page_id, page_name, "primary_work_region", primary_region)
        secondary_regions = brief.get("secondary_support_regions", [])
        if isinstance(secondary_regions, list) and secondary_regions:
            for item in secondary_regions[:3]:
                add_component_row(page_id, page_name, "secondary_support_region", str(item).strip())
        else:
            add_component_row(page_id, page_name, "secondary_support_region", "TBD")
        core_blocks = brief.get("core_information_blocks", [])
        if isinstance(core_blocks, list) and core_blocks:
            for item in core_blocks[:3]:
                add_component_row(page_id, page_name, "information_block", str(item).strip())
        else:
            add_component_row(page_id, page_name, "information_block", "TBD")
        add_component_row(page_id, page_name, "action_region", primary_action or "TBD")

        interaction_pattern = interaction_pattern_for_blueprint(page_blueprint_type)
        justification_source = str(brief.get("why_it_exists", "") or primary_action or "supports the workflow step").strip()
        interaction_rows.append([page_id, page_name, interaction_pattern, justification_source])

        business_object = "TBD"
        data_objects = brief.get("key_data_objects", "")
        if isinstance(data_objects, str) and data_objects.strip():
            business_object = split_inline_items(data_objects)[0] if split_inline_items(data_objects) else data_objects.strip()
        transitions = str(brief.get("business_state_transitions", "") or "").strip()
        normalized_steps = [part.strip() for part in transitions.split("_then_") if part.strip()]
        route_pattern = str(row.get("route_pattern", "")).strip() or "TBD"
        primary_actor = str(row.get("primary_actor", "")).strip() or "TBD"
        contract_rows.append(
            [
                page_id,
                page_name,
                route_pattern,
                primary_actor,
                primary_action or "TBD",
                business_object,
                transitions or "current -> next",
                page_blueprint_type or "detail-view",
            ]
        )
        if len(normalized_steps) >= 2:
            for index in range(len(normalized_steps) - 1):
                state_from = normalized_steps[index]
                state_to = normalized_steps[index + 1]
                ui_feedback = (
                    "status indicator updates, relevant list/detail regions refresh, and the next workflow action becomes available"
                )
                state_rows.append([page_id, business_object, state_from, state_to, ui_feedback])
        else:
            state_rows.append(
                [
                    page_id,
                    business_object,
                    "current",
                    transitions or "next",
                    "surface state updates visibly in-page and preserves workflow continuity",
                ]
            )

    entry_page = root_pages[0] if root_pages else str(page_rows[0]["page_id"]).strip()
    primary_flow = []
    current = entry_page
    visited: set[str] = set()
    while current and current not in visited:
        visited.add(current)
        primary_flow.append(current)
        children = child_map.get(current, [])
        current = children[0] if children else ""
    for source, target in zip(primary_flow, primary_flow[1:]):
        adjacency_rows.append(
            [
                source,
                target,
                "primary_flow",
                "advance the first-wave workflow after the page's primary action succeeds",
            ]
        )
    for parent, children in child_map.items():
        for child in children[1:] if parent in primary_flow else children:
            adjacency_rows.append(
                [
                    parent,
                    child,
                    "secondary_flow",
                    "enter a supporting or detail surface while preserving the current business context",
                ]
            )
    for row in page_rows:
        page_id = str(row["page_id"]).strip()
        parent_page = str(row.get("parent_page", "")).strip()
        if parent_page and parent_page != "—" and all(
            not (existing[0] == parent_page and existing[1] == page_id) for existing in adjacency_rows
        ):
            adjacency_rows.append(
                [
                    parent_page,
                    page_id,
                    "secondary_flow",
                    "open the child page when the user needs supporting analysis or detail work",
                ]
            )

    mermaid_lines = ["```mermaid", "flowchart LR"]
    for row in page_rows:
        mermaid_lines.append(f'    {row["page_id"]}["{row["page_name"]}"]')
    for link in adjacency_rows:
        mermaid_lines.append(f"    {link[0]} -->|{link[2]}| {link[1]}")
    mermaid_lines.append("```")

    entry_name = page_name_by_id.get(entry_page, entry_page)
    primary_flow_blob = " -> ".join(f"`{page_id}`" for page_id in primary_flow) if primary_flow else "`TBD`"
    return "\n".join(
        [
            "### 10.1 Frontend Surface Architecture",
            "This section translates the Phase-1 page map and page briefs into implementation-facing frontend surface definitions so Phase-3 does not infer layout structure from endpoints alone.",
            "",
            "#### 10.1.1 Page Component Tree",
            markdown_table(
                ["page_id", "page_name", "component_region", "component_type"],
                page_component_rows,
            ),
            "",
            "#### 10.1.2 Navigation Graph",
            f"- entry_page: `{entry_page}` / `{entry_name}`",
            f"- primary_flow: {primary_flow_blob}",
            "- secondary_flow: supporting detail/review branches that preserve the current business context instead of resetting workflow state",
            "",
            *mermaid_lines,
            "",
            markdown_table(
                ["from_page", "to_page", "flow_type", "trigger_condition"],
                adjacency_rows,
            ),
            "",
            "#### 10.1.3 Interaction Pattern Assignment",
            markdown_table(
                ["page_id", "page_name", "interaction_pattern", "justification"],
                interaction_rows,
            ),
            "",
            "#### 10.1.4 State Transition Surface Map",
            markdown_table(
                ["page_id", "business_object", "state_from", "state_to", "ui_feedback"],
                state_rows,
            ),
            "",
            "#### 10.1.5 Page-Level Contract",
            markdown_table(
                [
                    "page_id",
                    "page_name",
                    "route_pattern",
                    "primary_actor",
                    "primary_action",
                    "business_object",
                    "state_contract",
                    "page_blueprint_type",
                ],
                contract_rows,
            ),
        ]
    )


def trace_anchor_for_id(artifact_id: str) -> str:
    chars: list[str] = []
    for ch in artifact_id.strip().lower():
        chars.append(ch if ch.isalnum() else "-")
    anchor = "".join(chars)
    return re.sub(r"-{2,}", "-", anchor).strip("-") or "trace-unit"


def artifact_id_list(value: str) -> list[str]:
    items = [item.strip().strip("`") for item in value.split(",")]
    return [item for item in items if item]


def artifact_type_for_phase1_trace_row(unit_group: str, row: dict[str, str]) -> str:
    if unit_group == "use_case_trace_units" and row.get("unit_type", "").strip() == "primary-user-story":
        return "USECASE"
    return PHASE1_TRACE_UNIT_TYPE_MAP[unit_group]


def bind_phase1_prd_trace_units(
    *,
    python: str,
    trace_dir: Path,
    output_dir: Path,
    project_key: str,
    phase1_prd: Path,
) -> None:
    phase1_text = phase1_prd.read_text(encoding="utf-8")
    relative_phase1_prd = relpath(phase1_prd, output_dir)
    run(
        [
            python,
            str(trace_dir / "bind_artifact.py"),
            "--project-root",
            str(output_dir),
            "--project-key",
            project_key,
            "--artifact-id",
            PHASE1_PRD_ARTIFACT_ID,
            "--artifact-type",
            "PRD",
            "--source-path",
            relative_phase1_prd,
            "--source-anchor",
            "traceability-naming-and-registry",
            "--stage-or-lane",
            "phase-1-prd",
            "--status",
            "reference",
        ]
    )

    phase1_units = extract_phase1_trace_units(phase1_text)
    for unit_group, rows in phase1_units.items():
        for row in rows:
            artifact_id = row["trace_id"].strip()
            source_anchor = row.get("source_anchor", "").strip() or trace_anchor_for_id(artifact_id)
            run(
                [
                    python,
                    str(trace_dir / "bind_artifact.py"),
                    "--project-root",
                    str(output_dir),
                    "--project-key",
                    project_key,
                    "--artifact-id",
                    artifact_id,
                    "--artifact-type",
                    artifact_type_for_phase1_trace_row(unit_group, row),
                    "--source-path",
                    relative_phase1_prd,
                    "--source-anchor",
                    source_anchor,
                    "--stage-or-lane",
                    "phase-1-prd-trace-unit",
                    "--status",
                    "reference",
                ]
            )
            run(
                [
                    python,
                    str(trace_dir / "link_artifacts.py"),
                    "--project-root",
                    str(output_dir),
                    "--project-key",
                    project_key,
                    "--from-artifact-id",
                    artifact_id,
                    "--to-artifact-id",
                    PHASE1_PRD_ARTIFACT_ID,
                    "--link-type",
                    "depends_on",
                    "--source-path",
                    relative_phase1_prd,
                    "--evidence-anchor",
                    source_anchor,
                ]
            )


def bind_trace_units(
    *,
    python: str,
    trace_dir: Path,
    output_dir: Path,
    project_key: str,
    source_path: Path,
    upstream_artifact_id: str,
    stage_or_lane: str,
    artifact_type: str,
    units: list[dict[str, str]],
    id_field: str,
) -> None:
    relative_source_path = relpath(source_path, output_dir)
    for unit in units:
        artifact_id = canonicalize_phase2_trace_artifact_id(unit[id_field].strip().strip("`"))
        source_anchor = trace_anchor_for_id(artifact_id)
        run(
            [
                python,
                str(trace_dir / "bind_artifact.py"),
                "--project-root",
                str(output_dir),
                "--project-key",
                project_key,
                "--artifact-id",
                artifact_id,
                "--artifact-type",
                artifact_type,
                "--source-path",
                relative_source_path,
                "--source-anchor",
                source_anchor,
                "--stage-or-lane",
                stage_or_lane,
                "--status",
                "review",
            ]
        )
        run(
            [
                python,
                str(trace_dir / "link_artifacts.py"),
                "--project-root",
                str(output_dir),
                "--project-key",
                project_key,
                "--from-artifact-id",
                artifact_id,
                "--to-artifact-id",
                upstream_artifact_id,
                "--link-type",
                "depends_on",
                "--source-path",
                relative_source_path,
                "--evidence-anchor",
                source_anchor,
            ]
        )
        for downstream_artifact_id in artifact_id_list(unit.get("downstream_artifact_id", "")):
            run(
                [
                    python,
                    str(trace_dir / "link_artifacts.py"),
                    "--project-root",
                    str(output_dir),
                    "--project-key",
                    project_key,
                    "--from-artifact-id",
                    artifact_id,
                    "--to-artifact-id",
                    downstream_artifact_id,
                    "--link-type",
                    "feeds",
                    "--source-path",
                    relative_source_path,
                    "--evidence-anchor",
                    source_anchor,
                ]
            )


def bind_stage03_interface_surfaces(
    *,
    python: str,
    trace_dir: Path,
    output_dir: Path,
    project_key: str,
    source_path: Path,
    upstream_artifact_id: str,
) -> None:
    stage_03_text = source_path.read_text(encoding="utf-8")
    relative_source_path = relpath(source_path, output_dir)
    seen: set[str] = set()

    def bind_surface(artifact_id: str, *, stage_or_lane: str) -> None:
        cleaned = canonicalize_phase2_trace_artifact_id(artifact_id.strip().strip("`"))
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        source_anchor = trace_anchor_for_id(cleaned)
        run(
            [
                python,
                str(trace_dir / "bind_artifact.py"),
                "--project-root",
                str(output_dir),
                "--project-key",
                project_key,
                "--artifact-id",
                cleaned,
                "--artifact-type",
                "INTERFACE",
                "--source-path",
                relative_source_path,
                "--source-anchor",
                source_anchor,
                "--stage-or-lane",
                stage_or_lane,
                "--status",
                "review",
            ]
        )
        run(
            [
                python,
                str(trace_dir / "link_artifacts.py"),
                "--project-root",
                str(output_dir),
                "--project-key",
                project_key,
                "--from-artifact-id",
                cleaned,
                "--to-artifact-id",
                upstream_artifact_id,
                "--link-type",
                "depends_on",
                "--source-path",
                relative_source_path,
                "--evidence-anchor",
                source_anchor,
            ]
        )

    for row in contract_trace_rows(stage_03_text):
        bind_surface(str(row.get("trace_subject", "")), stage_or_lane="stage-03-contract-surface")
        for downstream_artifact_id in artifact_id_list(str(row.get("downstream_artifact_id", ""))):
            bind_surface(downstream_artifact_id, stage_or_lane="stage-03-contract-operation")

    for row in api_rows(stage_03_text):
        bind_surface(str(row.get("endpoint_name", "")), stage_or_lane="stage-03-api")


def link_phase2_upstream_trace_units(
    *,
    python: str,
    trace_dir: Path,
    output_dir: Path,
    project_key: str,
    stage_paths: dict[str, Path],
    phase1_prd: Path,
    fine_grained_trace_units: dict[str, list[dict[str, str]]],
    resolution_report_path: Path,
) -> dict[str, Any]:
    resolution_report = build_phase2_phase1_resolution_report(
        phase1_prd=phase1_prd,
        fine_grained_trace_units=fine_grained_trace_units,
    )
    resolution_report_path.write_text(json.dumps(resolution_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    group_source_paths = {
        "decision_trace_units": stage_paths["stage_01"],
        "contract_trace_units": stage_paths["stage_03"],
        "rbi_trace_units": stage_paths["stage_04"],
        "replay_trace_units": stage_paths["stage_04"],
    }
    linked_pairs: set[tuple[str, str]] = set()
    for row in resolution_report["rows"]:
        artifact_id = str(row.get("artifact_id", "")).strip()
        if not artifact_id:
            continue
        upstream_ids = [str(item).strip() for item in row.get("explicit_upstream_trace_ids", []) if str(item).strip()]
        for phase1_id in row.get("phase1_upstream_trace_ids", []):
            value = str(phase1_id).strip()
            if value and value not in upstream_ids:
                upstream_ids.append(value)
        source_path = group_source_paths.get(str(row.get("row_group", "")))
        if source_path is None:
            continue
        for upstream_id in upstream_ids:
            if upstream_id.startswith(("RBI-", "WP-")):
                continue
            key = (artifact_id, upstream_id)
            if key in linked_pairs:
                continue
            run(
                [
                    python,
                    str(trace_dir / "link_artifacts.py"),
                    "--project-root",
                    str(output_dir),
                    "--project-key",
                    project_key,
                    "--from-artifact-id",
                    artifact_id,
                    "--to-artifact-id",
                    upstream_id,
                    "--link-type",
                    "depends_on",
                    "--source-path",
                    relpath(source_path, output_dir),
                    "--evidence-anchor",
                    trace_anchor_for_id(artifact_id),
                ]
            )
            linked_pairs.add(key)
    resolution_report["summary"]["linked_upstream_pairs"] = len(linked_pairs)
    resolution_report_path.write_text(json.dumps(resolution_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resolution_report


def summarize_fine_grained_trace_runtime(report: dict[str, Any]) -> dict[str, int]:
    summary = {
        "decision_trace_units": 0,
        "contract_trace_units": 0,
        "rbi_trace_units": 0,
        "replay_trace_units": 0,
    }
    for artifact in report.get("artifacts", []):
        lane = str(artifact.get("stage_or_lane", "")).strip()
        if lane == "stage-01-decision":
            summary["decision_trace_units"] += 1
        elif lane == "stage-03-contract":
            summary["contract_trace_units"] += 1
        elif lane == "stage-04-rbi":
            summary["rbi_trace_units"] += 1
        elif lane == "stage-04-replay":
            summary["replay_trace_units"] += 1
    return summary


def stage_paths_live_in_case_root(stage_paths: dict[str, Path], output_dir: Path) -> bool:
    return all(
        path.resolve() == (output_dir / STAGE_DEFAULTS[stage_key]).resolve()
        for stage_key, path in stage_paths.items()
    )


def inspect_case_for_runner(
    output_dir: Path,
    stage_paths: dict[str, Path],
    optional_stage_02_5: Path | None = None,
) -> dict[str, Any]:
    optional_default_path = (output_dir / OPTIONAL_STAGE_02_5_DEFAULT).resolve()
    optional_stage_candidate = optional_stage_02_5
    if optional_stage_candidate is None and optional_default_path.exists():
        optional_stage_candidate = optional_default_path

    if stage_paths_live_in_case_root(stage_paths, output_dir) and (
        optional_stage_candidate is None or optional_stage_candidate.resolve() == optional_default_path
    ):
        return inspect_case(output_dir)

    manifest_exists = phase_surface_exists(output_dir, "phase2", MANIFEST_NAME)
    wrapper_artifacts_present = [name for name in WRAPPER_FILES if (output_dir / name).exists()]
    stage_rows: list[dict[str, Any]] = []
    missing_stage_files: list[str] = []
    stub_stage_files: list[str] = []
    external_stage_bindings: list[str] = []
    optional_stage_rows: list[dict[str, Any]] = []
    optional_stub_stage_files: list[str] = []
    external_optional_stage_bindings: list[str] = []

    for stage_key, path in stage_paths.items():
        expected_path = (output_dir / STAGE_DEFAULTS[stage_key]).resolve()
        exists = path.exists()
        still_scaffold_target = False
        if exists:
            text = path.read_text(encoding="utf-8")
            still_scaffold_target = any(marker in text for marker in SCAFFOLD_MARKERS)
        else:
            missing_stage_files.append(STAGE_DEFAULTS[stage_key])
        if still_scaffold_target:
            stub_stage_files.append(STAGE_DEFAULTS[stage_key])
        if path.resolve() != expected_path:
            external_stage_bindings.append(f"{STAGE_DEFAULTS[stage_key]} -> {path.resolve()}")
        stage_rows.append(
            {
                "file": STAGE_DEFAULTS[stage_key],
                "exists": exists,
                "still_scaffold_target": still_scaffold_target,
                "source_path": str(path.resolve()),
                "expected_case_root_path": str(expected_path),
                "in_case_root": path.resolve() == expected_path,
            }
        )

    if optional_stage_candidate is not None:
        exists = optional_stage_candidate.exists()
        still_scaffold_target = False
        if exists:
            text = optional_stage_candidate.read_text(encoding="utf-8")
            still_scaffold_target = any(marker in text for marker in SCAFFOLD_MARKERS)
        if still_scaffold_target:
            optional_stub_stage_files.append(OPTIONAL_STAGE_02_5_DEFAULT)
        if optional_stage_candidate.resolve() != optional_default_path:
            external_optional_stage_bindings.append(
                f"{OPTIONAL_STAGE_02_5_DEFAULT} -> {optional_stage_candidate.resolve()}"
            )
        optional_stage_rows.append(
            {
                "file": OPTIONAL_STAGE_02_5_DEFAULT,
                "exists": exists,
                "still_scaffold_target": still_scaffold_target,
                "source_path": str(optional_stage_candidate.resolve()),
                "expected_case_root_path": str(optional_default_path),
                "in_case_root": optional_stage_candidate.resolve() == optional_default_path,
                "required": False,
            }
        )
    else:
        optional_stage_rows.append(
            {
                "file": OPTIONAL_STAGE_02_5_DEFAULT,
                "exists": False,
                "still_scaffold_target": False,
                "source_path": "",
                "expected_case_root_path": str(optional_default_path),
                "in_case_root": True,
                "required": False,
            }
        )

    issues: list[str] = []
    if not manifest_exists:
        issues.append(f"missing {MANIFEST_NAME}")
    if missing_stage_files:
        issues.append("missing stage files: " + ", ".join(missing_stage_files))
    if stub_stage_files:
        issues.append("stage files still scaffold-only: " + ", ".join(stub_stage_files))
    if optional_stub_stage_files:
        issues.append("optional stage files still scaffold-only: " + ", ".join(optional_stub_stage_files))
    if external_stage_bindings:
        issues.append("stage outputs are outside the case root: " + ", ".join(external_stage_bindings))
    if external_optional_stage_bindings:
        issues.append(
            "optional stage outputs are outside the case root: " + ", ".join(external_optional_stage_bindings)
        )

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


def preserve_initial_first_pass_audit(
    existing_audit: dict[str, Any] | None,
    current_audit: dict[str, Any],
) -> dict[str, Any]:
    if not existing_audit:
        return current_audit
    if str(existing_audit.get("status", "")) != "authored-first-pass" or not bool(existing_audit.get("passed")):
        return current_audit
    if not bool(current_audit.get("passed")):
        return current_audit

    preserved = dict(existing_audit)
    preserved["preserved_authored_first_pass_proof"] = True
    preserved["current_case_status"] = str(current_audit.get("status", "unknown"))
    preserved["current_wrapper_artifacts_present"] = list(current_audit.get("wrapper_artifacts_present", []))
    preserved["current_issues"] = [str(item) for item in current_audit.get("issues", []) if str(item).strip()]
    return preserved


def render_engineering_spec_pack_template(template_values: dict[str, object]) -> str:
    text = load_script_text_asset(__file__, "engineering-spec-pack.md.template")
    for placeholder, raw_value in template_values.items():
        value = str(raw_value or "")
        line_placeholder = f"{placeholder}\n"
        if line_placeholder in text:
            replacement = value if not value or value.endswith("\n") else f"{value}\n"
            text = text.replace(line_placeholder, replacement)
        else:
            text = text.replace(placeholder, value)
    return text.rstrip() + "\n"


def _resolve_phase2_execution_report_template_value(token: str, template_values: dict[str, object]) -> object:
    parts = token.split(".")
    if not parts or parts[0] not in template_values:
        raise KeyError(f"missing Phase-2 execution report template value: {token}")
    value: object = template_values[parts[0]]
    for part in parts[1:]:
        if isinstance(value, dict):
            if part not in value:
                raise KeyError(f"missing Phase-2 execution report template value: {token}")
            value = value[part]
        else:
            value = getattr(value, part)
    return value


def render_phase2_execution_report_template(
    template_values: dict[str, object],
    computed_values: dict[str, object] | None = None,
) -> str:
    values = dict(template_values)
    if computed_values:
        values.update(computed_values)
    text = load_script_text_asset(__file__, "phase2-execution-report.md.template")
    for token in sorted(set(re.findall(r"__([A-Za-z][A-Za-z0-9_.]*)__", text))):
        raw_value = values[token] if token in values else _resolve_phase2_execution_report_template_value(token, values)
        value = "" if raw_value is None else str(raw_value)
        placeholder = f"__{token}__"
        text = text.replace(placeholder, value)
    return text.rstrip() + "\n"


def write_engineering_spec_pack(
    *,
    output: Path,
    case_name: str,
    version: str,
    profile: str,
    run_owner: str,
    stage_01: Path,
    stage_02: Path,
    stage_02_5: Path | None,
    stage_03: Path,
    stage_04: Path,
    phase1_prd: Path,
    execution_report: Path,
    trace_validation: Path,
    trace_report_text: Path,
    existing_system_architecture_change_intake: Path | None = None,
    output_locale: str | None = None,
) -> None:
    stage_01_text = stage_01.read_text(encoding="utf-8")
    stage_02_text = stage_02.read_text(encoding="utf-8")
    stage_02_5_text = stage_02_5.read_text(encoding="utf-8") if stage_02_5 and stage_02_5.exists() else ""
    stage_03_text = stage_03.read_text(encoding="utf-8")
    stage_04_text = stage_04.read_text(encoding="utf-8")
    optional_stage_check = analyze_optional_stage_02_5(stage_02_5) if stage_02_5 else None
    wp_registry = work_package_rows(stage_04_text)
    rbi_registry = rbi_rows(stage_04_text)
    contract_registry = contract_trace_rows(stage_03_text)
    schema_registry = schema_rows(stage_03_text)
    endpoint_registry = api_rows(stage_03_text)
    operation_design_source_rows = build_operation_design_source_rows(endpoint_registry, contract_registry)
    operation_source_obligation_rows = build_operation_source_obligation_rows(endpoint_registry, contract_registry, operation_design_source_rows)
    business_value_signal_registry = load_business_value_signal_registry(phase1_prd)
    p1_value_to_p2_operation_resolution_rows = build_p1_value_to_p2_operation_resolution_rows(
        business_value_signal_registry, operation_source_obligation_rows
    )
    implementation_depth_obligation_rows = build_implementation_depth_obligation_rows(
        operation_source_obligation_rows, p1_value_to_p2_operation_resolution_rows
    )
    implementation_component_catalog_rows = build_implementation_component_catalog_rows(
        endpoint_registry, schema_registry, operation_source_obligation_rows
    )
    component_action_card_obligation_rows = build_component_action_card_obligation_rows(
        implementation_component_catalog_rows, implementation_depth_obligation_rows
    )
    glossary_entries = build_glossary_entries(
        stage_02_text=stage_02_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
    )
    environment_prerequisites = format_nested_bullets(
        derive_environment_dependency_prerequisites(stage_03_text, stage_02_5_text),
        indent=4,
    )
    boundary_block = render_block(stage_01_text, "system_boundary_statement", fallback="")
    pressure_block = render_block(stage_01_text, "chosen_thesis_architecture_pressure", fallback="")
    translation_block = render_block(stage_01_text, "thesis_driven_architecture_translation", fallback="")
    stage_04_handoff_block = render_thesis_driven_architecture_handoff(stage_04_text)
    quick_start_wp_ids = ", ".join(f"`{row['wp_id']}`" for row in wp_registry[:3]) or "`WP registry missing`"
    quick_start_rbi_ids = ", ".join(f"`{row['rbi_id']}`" for row in rbi_registry[:3]) or "`RBI registry missing`"
    reader_architecture_choice = (
        first_reader_memo_scalar(
            translation_block,
            ["architecture_posture", "architecture_choice", "design_implication", "technical_translation"],
        )
        or first_reader_memo_scalar(boundary_block, ["system_boundary_statement", "boundary_statement"])
    )
    reader_business_proof_fit = first_reader_memo_scalar(
        pressure_block,
        ["commercial_proof_supported_by", "business_proof_loop", "design_implication"],
    )
    reader_p3_preserve = first_reader_memo_scalar(
        stage_04_handoff_block,
        ["implementation_rule", "phase3_entry", "handoff_rule", "fallback_scope"],
    )
    reader_decision_brief = render_esp_reader_decision_brief(
        architecture_choice=reader_architecture_choice,
        business_proof_fit=reader_business_proof_fit,
        p3_preserve=reader_p3_preserve,
        wp_ids=quick_start_wp_ids,
        rbi_ids=quick_start_rbi_ids,
        has_optional_stage_02_5=bool(stage_02_5 and stage_02_5.exists()),
        has_existing_system_change=bool(existing_system_architecture_change_intake),
    )
    quick_start_items = [
        render_esp_reader_memo(
            stage_01_text,
            stage_04_text,
            wp_registry,
            rbi_registry,
            core_object_surface=core_object_surface_from_schema_rows(schema_registry),
            has_optional_stage_02_5=bool(stage_02_5 and stage_02_5.exists()),
            has_existing_system_change=bool(existing_system_architecture_change_intake),
        ),
        "",
        "- reading_order:",
        "- 1. Read `2.0 Reader Decision Brief`, then `3.1 System Boundary Statement` and `3.6 Key Architecture Decisions` to recover the immutable boundary and decision posture.",
        "- 2. Read `4.2 Module Map`, `4.3 Service Candidates`, and `4.4 Responsibility Matrix` to recover ownership and decomposition semantics.",
    ]
    if stage_02_5 and stage_02_5.exists():
        quick_start_items.append(
            "- 3. Read `4.8 Optional Stage-02.5 Activation` and the Stage-02.5 sections that follow before changing provider bindings, auth posture, adapter seams, or mock/sandbox behavior."
        )
        quick_start_items.append(
            "- 4. Read `5.1 Data Sensitivity and Compliance Matrix` plus `5.2 Schema Draft` before changing storage, migration, or retention posture."
        )
        quick_start_items.append(
            "- 5. Read `6.2 API Endpoint Draft` and `6.3` to `6.14` before changing bindings, traceability, boundary contracts, or technology-selection rationale."
        )
        quick_start_items.append(
            "- 6. Read `8 Risk Summary`, `9 Realizability Judgment`, and `10.5` to `10.11` before planning branches, staffing, rollout, or auth-provider work."
        )
        quick_start_items.append(
            f"- 7. Start implementation planning from {quick_start_wp_ids} and preserve RBI ownership for {quick_start_rbi_ids}."
        )
    else:
        quick_start_items.extend(
            [
                "- 3. Read `5.1 Data Sensitivity and Compliance Matrix` plus `5.2 Schema Draft` before changing storage, migration, or retention posture.",
                "- 4. Read `6.2 API Endpoint Draft` and `6.3` to `6.14` before changing bindings, traceability, boundary contracts, or technology-selection rationale.",
                "- 5. Read `8 Risk Summary`, `9 Realizability Judgment`, and `10.5` to `10.11` before planning branches, staffing, rollout, or auth-provider work.",
                f"- 6. Start implementation planning from {quick_start_wp_ids} and preserve RBI ownership for {quick_start_rbi_ids}.",
            ]
        )
    if existing_system_architecture_change_intake:
        quick_start_items.append(
            "- Read `3.8 Existing-System Architecture Change Addendum` before changing storage, API, service boundaries, migration, rollback, or compatibility behavior inherited from the existing system."
        )
    quick_start_path = "\n".join(quick_start_items)
    working_glossary = glossary_markdown(glossary_entries[:20])
    onboarding_summary_block = block_text(stage_04_text, "glossary_or_onboarding_summary")
    if "- environment_or_dependency_prerequisites:" not in onboarding_summary_block:
        onboarding_summary_block = (
            onboarding_summary_block.rstrip()
            + "\n  - environment_or_dependency_prerequisites:\n"
            + environment_prerequisites
        ).strip()
    optimality_review_block = block_text(stage_04_text, "optimality_review")
    stage_04_readiness_label = extract_block_scalar(optimality_review_block, "strongest_supported_readiness_label")
    stage_04_realizability_judgment = extract_block_scalar(optimality_review_block, "realizability_judgment")
    realizability_section = render_heading(stage_04_text, "4.1 Realizability Review", fallback="")
    if not realizability_section:
        realizability_lines = ["- strongest_supported_readiness_label:"]
        realizability_lines.append(
            f"  - `{stage_04_readiness_label}`" if stage_04_readiness_label else "  - `missing`"
        )
        realizability_lines.append("- realizability_judgment:")
        realizability_lines.append(
            f"  - {stage_04_realizability_judgment}" if stage_04_realizability_judgment else "  - missing"
        )
        realizability_section = "\n".join(realizability_lines)
    frontend_surface_architecture = build_frontend_surface_architecture_section(phase1_prd, stage_04_text)
    existing_system_architecture_change_addendum = render_existing_system_architecture_change_addendum(
        intake_path=existing_system_architecture_change_intake,
        relative_to=output.parent,
    )

    implementation_start_order = (
        markdown_table(
            ["wp_id", "depends_on", "implementation_scope", "acceptance_criteria", "linked_rbi_or_slice"],
            [
                [
                    row["wp_id"],
                    row["depends_on"] or "none",
                    row["scope"],
                    row["acceptance_criteria"],
                    row["linked_rbi_or_slice"],
                ]
                for row in wp_registry
            ],
        )
        if wp_registry
        else "- work package registry missing"
    )
    schema_migration_focus = (
        markdown_table(
            ["table_name", "owner", "creation_or_migration_focus", "first_build_guardrail"],
            [
                [
                    row["table_name"],
                    row["ownership"],
                    (
                        f"create and backfill `{row['table_name']}` before consumers depending on `{row['fk']}`"
                        if row["fk"].strip().lower() != "none"
                        else f"create `{row['table_name']}` before downstream workflow consumers bind to its public identifiers"
                    ),
                    f"preserve `{row['pk']}` identity and declared ownership boundary",
                ]
                for row in schema_registry[: min(len(schema_registry), 8)]
            ],
        )
        if schema_registry
        else "- schema draft missing"
    )
    contract_freeze = markdown_table(
        ["boundary_surface", "owner", "implementation_rule", "verification_hook"],
        [
            [
                row["trace_subject"],
                row["owning_module"],
                f"preserve `{row['subject_type']}` naming and do not drift downstream artifact `{row['downstream_artifact_id']}`",
                row["verification_hook"],
            ]
            for row in contract_registry
        ]
        + [
            [
                row["endpoint_name"],
                row["path"],
                f"preserve `{row['method']}` boundary, failure semantics, and pagination/rate posture during controller build",
                row["failure_codes"],
            ]
            for row in endpoint_registry[: min(len(endpoint_registry), 6)]
        ],
    )
    rollout_guardrails = (
        markdown_table(
            ["rbi_id", "risk_level", "spike_wp", "blocks_which_wp", "responsible_party", "implementation_guardrail"],
            [
                [
                    row["rbi_id"],
                    row["risk_level"],
                    row["spike_wp"],
                    row["blocks_which_wp"],
                    row["responsible_party"],
                    f"do not close `{row['blocks_which_wp']}` before `{row['spike_wp']}` resolves `{row['rbi_id']}`",
                ]
                for row in rbi_registry
            ],
        )
        if rbi_registry
        else "- RBI registry missing"
    )
    optional_stage_sections: list[str] = []
    if stage_02_5 and stage_02_5.exists():
        optional_metrics = (optional_stage_check or {}).get("metrics", {})
        activation_state = optional_metrics.get("activation_state", "missing")
        optional_stage_sections = [
            "### 4.8 Optional Stage-02.5 Activation",
            f"- stage_file: `{stage_02_5.name}`",
            f"- activation_state: `{activation_state}`",
            f"- quality_gate: `{'pass' if (optional_stage_check or {}).get('quality_gate_passed') else 'fail'}`",
            "",
            render_block(stage_02_5_text, "activation_decision"),
            "",
        ]
        if activation_state == "active":
            optional_stage_sections.extend(
                [
                    "### 4.9 Third-Party Dependency Manifest",
                    render_block(stage_02_5_text, "third_party_dependency_manifest"),
                    "",
                    "### 4.10 Integration Decision Records",
                    render_block(stage_02_5_text, "integration_decision_records"),
                    "",
                    "### 4.11 Integration Adapter Specifications",
                    render_block(stage_02_5_text, "integration_adapter_specifications"),
                    "",
                    "### 4.12 Integration Test Strategy",
                    render_block(stage_02_5_text, "integration_test_strategy"),
                    "",
                    "### 4.13 Integration Risk Register",
                    render_block(stage_02_5_text, "integration_risk_register"),
                    "",
                ]
            )

    template_values = {
        "__ESP_PART_001__": f"- case_name: `{case_name}`",
        "__ESP_PART_002__": f"- report_version: `{version}`",
        "__ESP_PART_003__": f"- run_owner: `{run_owner}`",
        "__ESP_PART_004__": f"- delivery_profile: `{profile}`",
        "__ESP_PART_005__": f"- upstream_phase1_prd: `{phase1_prd}`",
        "__ESP_PART_006__": f"- Stage-01 architecture entry: `{stage_01.name}`",
        "__ESP_PART_007__": f"- Stage-02 decomposition: `{stage_02.name}`",
        "__ESP_PART_008__": f"- Stage-02.5 third-party integration lane: `{stage_02_5.name}`"
                    if stage_02_5 and stage_02_5.exists()
                    else "- Stage-02.5 third-party integration lane: `not-present`",
        "__ESP_PART_009__": f"- Stage-03 data/interface design: `{stage_03.name}`",
        "__ESP_PART_010__": f"- Stage-04 convergence package: `{stage_04.name}`",
        "__ESP_PART_011__": f"- execution report target: `{execution_report.name}`",
        "__ESP_PART_012__": f"- existing-system architecture change intake: `{existing_system_architecture_change_intake.name}`"
                    if existing_system_architecture_change_intake
                    else "- existing-system architecture change intake: `not-present`",
        "__READER_DECISION_BRIEF__": reader_decision_brief,
        "__QUICK_START_PATH__": quick_start_path,
        "__WORKING_GLOSSARY__": working_glossary,
        "__SYSTEM_BOUNDARY_STATEMENT__": render_block(stage_01_text, "system_boundary_statement"),
        "__CONSTRAINTS__": render_block(stage_01_text, "constraints"),
        "__CHOSEN_THESIS_ARCHITECTURE_PRESSURE__": render_block(stage_01_text, "chosen_thesis_architecture_pressure"),
        "__THESIS_DRIVEN_ARCHITECTURE_TRANSLATION__": render_block(stage_01_text, "thesis_driven_architecture_translation"),
        "__ESP_PART_013__": render_thesis_driven_architecture_handoff(stage_04_text),
        "__QUALITY_ATTRIBUTE_STRUCTURE__": render_block(stage_01_text, "quality_attribute_structure"),
        "__SECURITY_ARCHITECTURE_SKETCH__": render_block(stage_01_text, "security_architecture_sketch"),
        "__CAPACITY_ESTIMATION__": render_block(stage_01_text, "capacity_estimation"),
        "__KEY_ARCHITECTURE_DECISIONS__": render_block(stage_01_text, "key_architecture_decisions"),
        "__ESP_BLOCK_001__": "\n".join([
                        "### 3.8 Existing-System Architecture Change Addendum",
                        existing_system_architecture_change_addendum,
                        "",
                    ]
                    if existing_system_architecture_change_addendum
                    else []),
        "__DOMAIN_MAP__": render_block(stage_02_text, "domain_map"),
        "__MODULE_MAP__": render_block(stage_02_text, "module_map"),
        "__SERVICE_CANDIDATES__": render_block(stage_02_text, "service_candidates"),
        "__RESPONSIBILITY_MATRIX__": render_block(stage_02_text, "responsibility_matrix"),
        "__DEPENDENCY_COLLABORATION_MAP__": render_block(stage_02_text, "dependency_collaboration_map"),
        "__ENTITY_RELATIONSHIP_DIAGRAM__": render_block(stage_02_text, "entity_relationship_diagram"),
        "__DOMAIN_EVENT_CATALOG__": render_block(stage_02_text, "domain_event_catalog"),
        "__OPTIONAL_STAGE_SECTIONS__": "\n".join(optional_stage_sections),
        "__DATA_SENSITIVITY_AND_COMPLIANCE_MATRIX__": render_block(stage_03_text, "data_sensitivity_and_compliance_matrix"),
        "__SCHEMA_DRAFT__": render_block(stage_03_text, "schema_draft"),
        "__INTERFACE_CONTRACTS__": render_block(stage_03_text, "interface_contracts"),
        "__API_ENDPOINT_DRAFT__": render_block(stage_03_text, "api_endpoint_draft"),
        "__DATA_SERVICE_BINDING_MATRIX__": render_block(stage_03_text, "data_service_binding_matrix"),
        "__INTERACTION_MATRIX_P2_ENRICHMENT__": render_block(stage_03_text, "interaction_matrix_p2_enrichment"),
        "__TRACEABILITY_MATRIX__": render_block(stage_03_text, "traceability_matrix"),
        "__INTERACTION_FLOW__": render_block(stage_03_text, "interaction_flow"),
        "__TECHNOLOGY_STACK_AND_DEPLOYMENT_ASSUMPTIONS__": render_block(stage_03_text, "technology_stack_and_deployment_assumptions"),
        "__TECHNOLOGY_SELECTION_EVALUATION_MATRIX__": render_block(stage_03_text, "technology_selection_evaluation_matrix"),
        "__DOMINANT_BOTTLENECK_HYPOTHESIS__": render_block(stage_03_text, "dominant_bottleneck_hypothesis"),
        "__ARCHITECTURE_ALTERNATIVE_CANDIDATE_SET__": render_block(stage_03_text, "architecture_alternative_candidate_set"),
        "__BASELINE_INSUFFICIENCY_NOTE__": render_block(stage_03_text, "baseline_insufficiency_note"),
        "__CONSTRAINT_DOMINANT_OPTIMUM_CANDIDATE__": render_block(stage_03_text, "constraint_dominant_optimum_candidate"),
        "__KEY_TRADEOFF_DECISIONS__": render_block(stage_03_text, "key_tradeoff_decisions"),
        "__CAPACITY_AND_PERFORMANCE_ASSUMPTIONS__": render_block(stage_03_text, "capacity_and_performance_assumptions"),
        "__ESP_PART_014__": render_key_decisions_quick_reference(stage_01_text),
        "__UNRESOLVED_RISKS_AND_REVIEW_BOUND_ITEMS__": render_block(stage_04_text, "unresolved_risks_and_review_bound_items"),
        "__REALIZABILITY_SECTION__": realizability_section,
        "__FRONTEND_SURFACE_ARCHITECTURE__": frontend_surface_architecture,
        "__PROTOTYPE_OR_STRUCTURED_DELIVERY_EXPRESSION__": render_block(stage_04_text, "prototype_or_structured_delivery_expression"),
        "__IMPLEMENTATION_HANDOFF_PACKAGE__": render_block(stage_04_text, "implementation_handoff_package"),
        "__IMPLEMENTATION_TASK_SKETCH__": render_block(stage_04_text, "implementation_task_sketch"),
        "__IMPLEMENTATION_START_ORDER__": implementation_start_order,
        "__SCHEMA_MIGRATION_FOCUS__": schema_migration_focus,
        "__CONTRACT_FREEZE__": contract_freeze,
        "__ESP_PART_015__": operation_source_obligation_markdown(operation_source_obligation_rows),
        "__ESP_PART_016__": operation_design_source_registry_markdown(operation_design_source_rows),
        "__ESP_PART_017__": generic_matrix_markdown(
                    implementation_depth_obligation_rows,
                    ["operation_id", "contract_trace_id", "upstream_p1_trace_ids", "business_value_weight", "engineering_risk_tier", "implementation_complexity", "acd_level", "required_card_type", "required_reason", "required_tests", "review_bound_missing_sources"],
                    "implementation_depth_obligation_matrix",
                ),
        "__ESP_PART_018__": generic_matrix_markdown(
                    implementation_component_catalog_rows,
                    ["component_id", "component_type", "owning_module", "source_stage", "source_ids", "related_operations", "related_schema_or_domain_objects", "target_path_hint", "catalog_status"],
                    "implementation_component_catalog",
                ),
        "__ESP_PART_019__": generic_matrix_markdown(
                    component_action_card_obligation_rows,
                    ["component_id", "component_type", "upstream_operation_ids", "upstream_p1_trace_ids", "business_value_weight", "engineering_risk_tier", "implementation_complexity", "acd_level", "required_card_type", "required_reason", "required_tests", "required_source_ids", "available_source_ids", "missing_source_types", "source_sufficiency_status", "review_bound_missing_sources"],
                    "component_action_card_obligation_matrix",
                ),
        "__ROLLOUT_GUARDRAILS__": rollout_guardrails,
        "__OBSERVABILITY_AND_OPERATIONAL_READINESS__": render_block(stage_04_text, "observability_and_operational_readiness"),
        "__IDENTITY_AND_KEY_MANAGEMENT_CHOICE_POSTURE__": render_block(stage_04_text, "identity_and_key_management_choice_posture"),
        "__ONBOARDING_SUMMARY_BLOCK__": onboarding_summary_block,
        "__ESP_PART_020__": f"- validation_reference: `{trace_validation.name}`",
        "__ESP_PART_021__": f"- registry_report_reference: `{trace_report_text.name}`",
    }
    text = render_engineering_spec_pack_template(template_values)
    output.write_text(localize_phase2_engineering_spec_pack(text, output_locale), encoding="utf-8")


def _phase1_claims_for_phase2_handoff(phase1_prd: Path) -> tuple[list[Any], str, Path | None]:
    return phase1_claims_for_phase2(phase1_prd)


def emit_phase2_handoff_claim_control_sidecar(context: Phase2FullTrialContext) -> dict[str, Any]:
    claims, source_mode, upstream_sidecar = _phase1_claims_for_phase2_handoff(context.phase1_prd)
    result = emit_path_b_claim_control_sidecar(
        artifact_path=context.engineering_spec_pack,
        artifact_id="p2:engineering-spec-pack",
        claims=claims,
        view_id="p2:engineering-spec-pack",
        source_count=2 if upstream_sidecar else 1,
        upstream_surface_paths=[path for path in [context.phase1_prd, upstream_sidecar] if path],
        sidecar_path=context.engineering_spec_pack_claim_control,
    )
    upstream_ref_audit = audit_phase2_artifact_upstream_claim_refs(
        context.engineering_spec_pack,
        accepted_phase1_claim_ids={claim.id for claim in claims},
    )
    acceptance_status = result["acceptance"]["overall_status"]
    overall_status = (
        "blocked"
        if acceptance_status == "blocked" or upstream_ref_audit["overall_status"] == "blocked"
        else "review_bound"
        if acceptance_status != "pass" or source_mode != "upstream-claim-control"
        else "pass"
    )
    report = {
        "artifact_kind": "phase2-handoff-claim-control-sidecar-report",
        "overall_status": overall_status,
        "claim_ceiling": phase2_claim_control_claim_ceiling(
            overall_status=overall_status,
            phase1_claim_source_mode=source_mode,
        ),
        "phase1_claim_source_mode": source_mode,
        "phase1_claim_control_sidecar": str(upstream_sidecar) if upstream_sidecar else "",
        "artifact_path": str(context.engineering_spec_pack),
        "sidecar_path": result["sidecar_path"],
        "claim_control_acceptance_status": acceptance_status,
        "classifications": sorted(
            set(result["acceptance"].get("classifications", []) + upstream_ref_audit["classifications"])
        ),
        "declared_upstream_p1_claim_refs": upstream_ref_audit["declared_upstream_p1_claim_refs"],
        "unknown_upstream_p1_claim_refs": upstream_ref_audit["unknown_upstream_p1_claim_refs"],
        "claim_count": len(result["surface"]["claim_index"]["claims"]),
    }
    write_json(resolve_cross_phase_surface_path(context.output_dir, "phase2", "phase2-handoff-claim-control-report.json"), report)
    return {"report": report, "sidecar_path": Path(result["sidecar_path"]), "acceptance": result["acceptance"]}


def write_implementation_entry(
    *,
    output: Path,
    case_name: str,
    version: str,
    engineering_spec_pack: Path,
    execution_report: Path,
    stage_02_5: Path | None,
    stage_04: Path,
    quality_report: Path,
    cross_stage_report: Path,
    trace_validation: Path,
    formal_state: str,
    output_locale: str | None = None,
) -> None:
    stage_04_text = stage_04.read_text(encoding="utf-8")
    esp_text = engineering_spec_pack.read_text(encoding="utf-8")
    normalized_formal_state = formal_state.strip().lower()
    phase3_start_allowed = normalized_formal_state != "blocked"
    may_start = "yes" if phase3_start_allowed else "no"
    wp_registry = work_package_rows(stage_04_text)
    rbi_registry = rbi_rows(stage_04_text)
    start_wp_ids = [row["wp_id"] for row in wp_registry[:3]]
    start_rbi_ids = [row["rbi_id"] for row in rbi_registry[:3]]
    onboarding_block = block_text(stage_04_text, "glossary_or_onboarding_summary")
    onboarding_summary = render_heading(esp_text, "10.10 Phase-3 Onboarding Summary", fallback="")
    environment_prerequisites = format_nested_bullets(
        bullet_items_from_block(
            extract_structured_block(onboarding_summary, "environment_or_dependency_prerequisites", indent=2)
        ),
        indent=2,
    )
    quick_start_snapshot = render_heading(esp_text, "2.1 Quick-Start Reading Path", fallback="- missing")
    working_glossary = render_heading(esp_text, "2.2 Working Glossary", fallback="- missing")
    stage_02_5_input_line = (
        f"- optional_stage_02_5_integration_lane:\n  - `{stage_02_5.name}`"
        if stage_02_5 and stage_02_5.exists()
        else "- optional_stage_02_5_integration_lane:\n  - `not-present`"
    )
    extra_start_sequence = (
        "5. Preserve Stage-02.5 provider/auth/timeout/fallback/mock-sandbox posture while opening adapter or integration slices."
        if stage_02_5 and stage_02_5.exists()
        else ""
    )
    start_wp_text = ", ".join(f"`{item}`" for item in start_wp_ids) or "`WP registry missing`"
    start_rbi_text = ", ".join(f"`{item}`" for item in start_rbi_ids) or "`RBI registry missing`"
    if "- handoff_digest:" not in quick_start_snapshot:
        stage_04_handoff_block = render_thesis_driven_architecture_handoff(stage_04_text)
        fallback_p3_entry = first_reader_memo_scalar(
            stage_04_handoff_block,
            ["implementation_rule", "phase3_entry", "handoff_rule", "fallback_scope"],
        )
        fallback_business_thesis = first_reader_memo_scalar(
            quick_start_snapshot,
            ["business_thesis", "business_proof_fit", "architecture_choice"],
        )
        quick_start_snapshot = (
            quick_start_snapshot.rstrip()
            + "\n"
            + "\n".join(
                render_phase2_handoff_digest_lines(
                    business_thesis=fallback_business_thesis
                    or "Preserve the Phase-2 business proof loop before implementation planning.",
                    core_objects="working glossary public-boundary terms and frozen ESP contracts",
                    p3_entry=fallback_p3_entry or "preserve the declared work-package order and RBI ownership",
                    wp_ids=start_wp_text,
                    rbi_ids=start_rbi_text,
                )
            )
        ).strip()
    if phase3_start_allowed:
        start_sequence = "\n".join(
            [
                f"1. Read `{engineering_spec_pack.name}` sections `10.5` to `10.11` before opening implementation slices.",
                f"2. Start with {start_wp_text} and preserve declared dependency order from Stage-04.",
                (
                    f"3. Carry unresolved review-bound ownership for {start_rbi_text} into implementation planning "
                    "instead of silently dropping the RBI chain."
                ),
                f"4. Bind new implementation artifacts to `IMPL-STG00-INPUT-0001` only after `{trace_validation.name}` remains `PASS`.",
                extra_start_sequence,
            ]
        ).rstrip()
    else:
        start_sequence = "\n".join(
            [
                "1. Do not start Phase-3 implementation slices while the strongest supported readiness label is `blocked`.",
                f"2. Resolve the closure caveats in `{execution_report.name}` and rerun Phase-2 closure before opening implementation work.",
                (
                    "3. Preserve the declared work-package and RBI chain as review references only; do not treat "
                    f"{', '.join(start_wp_ids) or 'the WP registry'} as executable intake yet."
                ),
                (
                    "4. Bind new implementation artifacts to `IMPL-STG00-INPUT-0001` only after the formal state is no longer "
                    f"`blocked` and `{trace_validation.name}` remains `PASS`."
                ),
            ]
        )

    checklist_rows = [
        [
            "Architecture baseline frozen",
            engineering_spec_pack.name,
            "boundary, ADR, and ownership posture are treated as authoritative implementation input",
            "do not start structural refactor or service split from memory",
            engineering_spec_pack.name,
        ],
        [
            "Execution report reviewed",
            execution_report.name,
            "formal state, closure adjustments, and weakest outputs are read before planning starts",
            "implementation team may ignore known weak spots and repeat avoidable drift",
            execution_report.name,
        ],
        [
            "Stage-04 sequencing accepted",
            stage_04.name,
            "first work packages and dependency chain are acknowledged before branch planning",
            "parallel work may violate declared WP dependencies",
            stage_04.name,
        ],
        [
            "Quality gate checked",
            quality_report.name,
            "overall quality gate is reviewed and closure-specific failures are not ignored",
            "implementation may start from a package that is not intake-safe",
            quality_report.name,
        ],
        [
            "Cross-stage consistency reviewed",
            cross_stage_report.name,
            "naming and chain inconsistencies are either absent or explicitly absorbed into work items",
            "module, contract, and RBI drift can be reintroduced during build",
            cross_stage_report.name,
        ],
        [
            "Quick-start and glossary reviewed",
            engineering_spec_pack.name,
            "the team reads the quick-start path and shared glossary before opening new implementation slices",
            "new contributors may recreate existing terminology drift or miss the intended reading order",
            engineering_spec_pack.name,
        ],
        [
            "Identity/auth lifecycle reviewed",
            engineering_spec_pack.name,
            "auth vendor, token lifecycle, and key-rotation posture are acknowledged before adapter/auth work starts",
            "implementation may silently choose a different auth/provider posture than the converged design",
            engineering_spec_pack.name,
        ],
        [
            "Trace validation preserved",
            trace_validation.name,
            "Phase-2 trace registry remains PASS before implementation bindings begin",
            "implementation artifacts may attach to an already-broken trace chain",
            trace_validation.name,
        ],
    ]
    if stage_02_5 and stage_02_5.exists():
        checklist_rows.insert(
            3,
            [
                "Third-party adapter posture reviewed",
                stage_02_5.name,
                "provider/auth/fallback/mock-sandbox rules are acknowledged before adapter or integration work starts",
                "implementation may silently redesign provider binding and break the approved adapter seam",
                stage_02_5.name,
            ],
        )

    checklist = markdown_table(
        ["checklist_item", "required_input", "pass_condition", "blocker_if_missing", "source_artifact"],
        checklist_rows,
    )

    text = f"""# Phase-3 Implementation Entry

## 1. Intake Metadata
- case_name:
  - `{case_name}`
- source_phase:
  - `Phase-2`
- report_version:
  - `{version}`
- strongest_supported_readiness_label:
  - `{formal_state}`

## 2. Required Upstream Inputs
- engineering_spec_pack:
  - `{engineering_spec_pack.name}`
- phase_2_execution_report:
  - `{execution_report.name}`
- current_convergence_package:
  - `{stage_04.name}`
{stage_02_5_input_line}

### 2.1 Quick-Start Onboarding Snapshot
{quick_start_snapshot}
- environment_or_dependency_prerequisites:
{environment_prerequisites}

### 2.2 Working Glossary
{working_glossary}

## 3. Implementation Intake Rule
- may_start:
  - `{may_start}`
- may_rely_on:
  - explicit public-boundary contracts, ownership statements, task-slice boundaries, and handoff usage rules already frozen in Phase-2 outputs
- must_not_assume:
  - unresolved review-bound items are resolved
  - substitute-boundary delivery paths are equivalent to direct production paths unless explicitly stated
  - missing external reality checks have already been completed
  - internal implementation convenience can rename public contracts or weaken failure semantics without Phase-2 re-approval

## 4. Structured Intake Checklist
{checklist}

## 5. Phase-3 Start Sequence
{start_sequence}

## 6. Phase-2 Guardrails to Preserve
- Preserve public-boundary names, endpoint failure semantics, and contract ids exactly as frozen in `{engineering_spec_pack.name}`.
- Preserve the work-package and RBI chain from `{stage_04.name}`; do not close blocked slices by narrative override.
- Preserve auth vendor, token lifecycle, and key-rotation posture if implementation work touches identity, secrets, or tenant isolation.
- {"Preserve Stage-02.5 provider bindings, internal port names, error mapping, and mock/sandbox strategy if implementation work touches third-party integrations." if stage_02_5 and stage_02_5.exists() else "When no Stage-02.5 lane exists, do not invent third-party provider posture silently; raise it as a new design input first."}
- Preserve all closure caveats from `{execution_report.name}` when translating Phase-2 design into implementation tasks.
"""
    output.write_text(localize_phase2_implementation_entry(text.rstrip() + "\n", output_locale), encoding="utf-8")


def write_execution_report(
    *,
    output: Path,
    case_name: str,
    phase1_prd: Path,
    version: str,
    profile: str,
    complexity_profile: str,
    complexity_classification_path: Path,
    complexity_classification_report: dict[str, Any],
    deployment_posture: dict[str, str],
    run_owner: str,
    stage_01: Path,
    stage_02: Path,
    stage_02_5: Path | None,
    stage_03: Path,
    stage_04: Path,
    engineering_spec_pack: Path,
    implementation_entry: Path,
    first_pass_audit_report: dict[str, Any],
    first_pass_audit_path: Path,
    trace_validation: Path,
    trace_report_text: Path,
    trace_registry_root: str,
    trace_db_path: str,
    trace_runtime_contract_verdict: str,
    trace_runtime_contract_issues: list[str],
    phase1_phase2_coverage_report: dict[str, Any],
    phase1_phase2_coverage_path: Path,
    fine_grained_trace_summary: dict[str, int],
    quality_report: dict,
    mermaid_report: dict,
    mermaid_report_path: Path,
    cross_stage_report: dict,
    cross_stage_report_path: Path,
    formal_state: str,
    realizability_judgment: str,
    baseline_reference: str,
    closure_adjustment_reasons: list[str],
    output_locale: str | None = None,
) -> None:
    run_date = date.today().isoformat()
    baseline_metrics = quality_report["baseline_lock"]["baseline_metrics"] or {}
    current_metrics = quality_report["baseline_lock"]["current_metrics"]
    regression_rows = quality_report["baseline_lock"]["regression_rows"]
    deliverable_rows = quality_report["deliverable_matrix"]
    deliverable_summary = quality_report.get("deliverable_matrix_summary") or {}
    deliverable_assessment = quality_report.get("deliverable_matrix_assessment") or {}
    review_bound = quality_report["review_bound_ratio"]
    stage_summaries = quality_report["stage_summaries"]
    esp_check = quality_report.get("engineering_spec_pack_check") or {"checks": {}, "passed": False}
    cross_stage_rows = cross_stage_report["rows"]
    readiness_alignment = quality_report.get("stage_04_readiness_alignment") or {}
    coverage_summary = phase1_phase2_coverage_report.get("summary", {})
    coverage_rows = phase1_phase2_coverage_report.get("rows", [])
    first_pass_status = str(first_pass_audit_report.get("status", "invalid-root"))
    first_pass_passed = bool(first_pass_audit_report.get("passed"))
    first_pass_summary = summarize_first_pass_audit(first_pass_audit_report)
    first_pass_issues = [str(item) for item in first_pass_audit_report.get("issues", []) if str(item).strip()]
    fine_grained_total = sum(int(value or 0) for value in fine_grained_trace_summary.values())
    semantic_warning_report = quality_report.get("semantic_warning_checks") or {}
    optional_stage_check = quality_report.get("optional_stage_02_5_check") or {
        "present": False,
        "quality_gate_passed": True,
        "gate_failures": [],
        "metrics": {"activation_state": "not-provided"},
        "decision_status": "not-applicable",
        "expected_from_phase1": False,
        "expected_reason": "not evaluated",
    }
    optional_stage_metrics = optional_stage_check.get("metrics", {})
    optional_stage_present = bool(optional_stage_check.get("present"))
    optional_stage_activation_state = str(optional_stage_metrics.get("activation_state", "not-provided"))
    optional_stage_decision_status = str(optional_stage_check.get("decision_status", "not-applicable"))
    optional_stage_expected = bool(optional_stage_check.get("expected_from_phase1"))
    optional_stage_expected_reason = str(optional_stage_check.get("expected_reason", "not evaluated"))
    optional_stage_gate_failures = optional_stage_check.get("gate_failures", [])
    optional_stage_quality_gate = bool(optional_stage_check.get("quality_gate_passed", True))
    optional_stage_file_name = stage_02_5.name if stage_02_5 and stage_02_5.exists() else "not-present"
    optional_stage_failure_names = ", ".join(item.get("name", "unknown") for item in optional_stage_gate_failures) or "none"
    optional_stage_quality_display = (
        "not-applicable"
        if not optional_stage_present
        else "pass"
        if optional_stage_quality_gate
        else f"fail ({optional_stage_failure_names})"
    )
    canonical_artifact_ids = ", ".join(
        [
            STAGE_IDS["stage_01"],
            STAGE_IDS["stage_02"],
            *([OPTIONAL_STAGE_02_5_ID] if optional_stage_present else []),
            STAGE_IDS["stage_03"],
            STAGE_IDS["stage_04"],
            "HANDOFF-0001",
            "IMPL-STG00-INPUT-0001",
            "VERIFY-0001",
        ]
    )
    coverage_table_md = markdown_table(
        [
            "phase1_trace_id",
            "unit_type",
            "expected_phase2_surfaces",
            "decision_trace_units",
            "contract_trace_units",
            "scenario_rows",
            "replay_trace_units",
            "rbi_trace_units",
            "coverage_status",
            "gap_note",
        ],
        [
            [
                row["phase1_trace_id"],
                row["unit_type"],
                row["expected_phase2_surfaces"],
                row["decision_trace_units"] or "-",
                row["contract_trace_units"] or "-",
                row["scenario_rows"] or "-",
                row["replay_trace_units"] or "-",
                row["rbi_trace_units"] or "-",
                row["coverage_status"],
                row["gap_note"],
            ]
            for row in coverage_rows
        ],
    )

    mandatory_rows = [row for row in deliverable_rows if row.get("tier") == "mandatory"]
    triggered_conditional_rows = [
        row for row in deliverable_rows if row.get("tier") == "conditional" and row.get("trigger_status") == "triggered"
    ]
    not_triggered_conditional_rows = [
        row for row in deliverable_rows if row.get("tier") == "conditional" and row.get("trigger_status") == "not-triggered"
    ]
    triggered_rows = mandatory_rows + triggered_conditional_rows

    mandatory_matrix_md = markdown_table(
        ["deliverable_name", "verdict", "evidence_reference", "unresolved_truth", "next_action"],
        [
            [
                row["deliverable_name"],
                row["verdict"],
                row["evidence_reference"],
                row["unresolved_truth"],
                row["next_action"],
            ]
            for row in mandatory_rows
        ],
    )
    conditional_matrix_md = markdown_table(
        ["deliverable_name", "verdict", "trigger_reason", "evidence_reference", "unresolved_truth", "next_action"],
        [
            [
                row["deliverable_name"],
                row["verdict"],
                row.get("trigger_reason", ""),
                row["evidence_reference"],
                row["unresolved_truth"],
                row["next_action"],
            ]
            for row in triggered_conditional_rows
        ],
    )
    conditional_not_triggered_md = markdown_table(
        ["deliverable_name", "trigger_status", "trigger_reason"],
        [
            [
                row["deliverable_name"],
                row.get("trigger_status", "not-triggered"),
                row.get("trigger_reason", ""),
            ]
            for row in not_triggered_conditional_rows
        ],
    )
    checklist_mapping_md = markdown_table(
        ["checklist_id", "stage", "deliverable_name", "matrix_verdict", "evidence_reference"],
        [
            [
                CHECKLIST_MAPPING.get(row["deliverable_name"], ("?", "?"))[0],
                CHECKLIST_MAPPING.get(row["deliverable_name"], ("?", "?"))[1],
                row["deliverable_name"],
                row["verdict"],
                row["evidence_reference"],
            ]
            for row in triggered_rows
        ],
    )
    mapping_complete = all(CHECKLIST_MAPPING.get(row["deliverable_name"]) for row in triggered_rows)
    baseline_md = markdown_table(
        ["dimension", "baseline_value", "current_value", "delta", "gate"],
        [
            [
                key,
                str(baseline_metrics.get(key, "")),
                str(current_metrics.get(key, "")),
                ""
                if baseline_metrics.get(key) is None
                else str(current_metrics.get(key, 0) - int(baseline_metrics.get(key, 0))),
                "",
            ]
            for key in current_metrics
        ],
    )
    regression_md = markdown_table(
        ["dimension", "baseline_value", "rerun_value", "delta", "verdict", "justification_if_negative"],
        [
            [
                row["dimension"],
                "" if row["baseline_value"] is None else str(row["baseline_value"]),
                str(row["current_value"]),
                "" if row["delta"] is None else str(row["delta"]),
                row["verdict"],
                row["justification_if_negative"],
            ]
            for row in regression_rows
        ],
    )
    validation_text = trace_validation.read_text(encoding="utf-8") if trace_validation.exists() else ""
    validation_result = extract_validation_result(validation_text)
    trace_runtime_issues_md = (
        "\n".join(f"  - `{issue}`" for issue in trace_runtime_contract_issues)
        if trace_runtime_contract_issues
        else "  - `none`"
    )
    first_pass_issues_md = (
        "\n".join(f"  - `{issue}`" for issue in first_pass_issues)
        if first_pass_issues
        else "  - `none`"
    )
    fine_grained_trace_md = "\n".join(
        [
            f"- decision_trace_units: `{fine_grained_trace_summary.get('decision_trace_units', 0)}`",
            f"- contract_trace_units: `{fine_grained_trace_summary.get('contract_trace_units', 0)}`",
            f"- rbi_trace_units: `{fine_grained_trace_summary.get('rbi_trace_units', 0)}`",
            f"- replay_trace_units: `{fine_grained_trace_summary.get('replay_trace_units', 0)}`",
            f"- fine_grained_trace_status: `{'present' if fine_grained_total else 'absent'}`",
        ]
    )
    warnings = [row for row in deliverable_rows if row["verdict"] in {"partial", "fail"} or row["unresolved_truth"] != "none"]
    mermaid_warnings = []
    for stage_key, report in mermaid_report.items():
        if stage_key in {"overall_passed", "render_validation"} or "missing_expected_types" not in report:
            continue
        for missing in report["missing_expected_types"]:
            mermaid_warnings.append(
                f"{stage_key} missing {missing['type']} ({missing['current']}/{missing['minimum']})"
            )
        for block in report["syntax_error_blocks"]:
            mermaid_warnings.append(
                f"{stage_key} Mermaid block #{block['index']} {block['type']} syntax warnings: {', '.join(block['syntax_errors'])}"
            )
        for block in report.get("semantic_error_blocks", []):
            mermaid_warnings.append(
                f"{stage_key} Mermaid block #{block['index']} {block['type']} semantic warnings: {', '.join(block['semantic_errors'])}"
            )
        for check in report.get("semantic_alignment_failures", []):
            mermaid_warnings.append(
                f"{stage_key} Mermaid semantic alignment failed: {check['check_name']} — {check['details']}"
            )
        render_validation = report.get("render_validation", {})
        if render_validation.get("requested") and not render_validation.get("passed", True):
            if render_validation.get("status") == "unavailable":
                mermaid_warnings.append(f"{stage_key} Mermaid render validation unavailable: {render_validation.get('error', 'mmdc unavailable')}")
            else:
                failed_renders = [
                    item for item in render_validation.get("results", []) if item.get("result") != "pass"
                ]
                for item in failed_renders:
                    mermaid_warnings.append(
                        f"{stage_key} Mermaid render failed for block #{item['index']} {item['type']}: {item.get('stderr', '') or 'unknown render error'}"
                    )
    warning_lines = "\n".join(
        f"- {row['deliverable_name']}: {row['verdict']} / {row['unresolved_truth']} — {row['next_action']}" for row in warnings
    )
    if mermaid_warnings:
        warning_lines = (warning_lines + "\n" if warning_lines else "") + "\n".join(f"- {item}" for item in mermaid_warnings)
    if first_pass_issues:
        warning_lines = (
            (warning_lines + "\n" if warning_lines else "")
            + f"- fresh_first_pass_audit: {first_pass_status} — {first_pass_summary}"
        )
    semantic_warning_lines: list[str] = []
    if semantic_warning_report.get("applied"):
        for check_name, check in (semantic_warning_report.get("checks") or {}).items():
            if check.get("passed"):
                continue
            if check_name == "semantic_sampling":
                sample_types = ", ".join(item["sample_type"] for item in check.get("items", []) if not item.get("passed"))
                semantic_warning_lines.append(
                    f"semantic warning / semantic_sampling: sampled content remained shallow for {sample_types or 'unknown sample types'}"
                )
            elif check_name == "adr_depth":
                failing_adrs = ", ".join(item.get("ad_id", item.get("entry_key", "")) for item in check.get("items", []) if not item.get("passed"))
                semantic_warning_lines.append(
                    f"semantic warning / adr_depth: deepen ADR alternatives/consequences for {failing_adrs or 'sampled ADRs'}"
                )
            elif check_name == "scenario_gwt":
                examples = ", ".join(f"`{item}`" for item in check.get("missing_examples", []))
                semantic_warning_lines.append(
                    f"semantic warning / scenario_gwt: only {check.get('ratio', 0)}% of scenario rows are GWT-compatible; examples without GWT structure: {examples or 'none listed'}"
                )
    if semantic_warning_lines:
        warning_lines = (warning_lines + "\n" if warning_lines else "") + "\n".join(f"- {item}" for item in semantic_warning_lines)
    if deployment_posture["warning_class"] != "none":
        warning_lines = (
            (warning_lines + "\n" if warning_lines else "")
            + (
                f"- deployment posture override warning: suggested={deployment_posture['suggested']}, "
                f"selected={deployment_posture['selected']}, class={deployment_posture['warning_class']}, "
                f"source={deployment_posture['override_source']}, added_risks={deployment_posture['added_risks']}"
            )
        )
    if optional_stage_decision_status == "warning-missing-explicit-decision":
        warning_lines = (
            (warning_lines + "\n" if warning_lines else "")
            + f"- optional Stage-02.5 decision missing even though Phase-1 indicates external integrations: {optional_stage_expected_reason}"
        )
    elif optional_stage_present and not optional_stage_quality_gate:
        warning_lines = (
            (warning_lines + "\n" if warning_lines else "")
            + f"- optional Stage-02.5 is present but incomplete: failing checks = {optional_stage_failure_names}"
        )
    if not warning_lines:
        warning_lines = "- none"

    mermaid_overall_passed = bool(mermaid_report.get("overall_passed"))
    cross_stage_verdict = cross_stage_report.get("overall_consistency_verdict", "unknown")
    review_bound_total = int(review_bound.get("total_structured_items", 0) or 0)
    review_bound_open = int(review_bound.get("review_bound_or_unknown_or_deferred_items", 0) or 0)
    review_bound_ceiling = int(review_bound.get("ceiling", 30) or 30)
    allowed_review_bound = math.floor(review_bound_total * review_bound_ceiling / 100) if review_bound_total else 0
    review_bound_resolution_gap = max(0, review_bound_open - allowed_review_bound)

    improvement_actions: list[str] = []
    if review_bound["verdict"] != "within-ceiling" and review_bound_resolution_gap > 0:
        improvement_actions.append(
            f"resolve or explicitly downgrade at least {review_bound_resolution_gap} review-bound structured items so `review_bound_ratio` can fall to {review_bound_ceiling}% or below"
        )
    if int(deliverable_assessment.get("triggered_conditional_gap_count", 0) or 0) > 0:
        improvement_actions.append(
            "close the triggered conditional deliverable gaps before upgrading the pack back to a clean implementation-planning-ready label"
        )
    if int(deliverable_assessment.get("mandatory_gap_count", 0) or 0) > 0:
        improvement_actions.append("close the remaining mandatory deliverable gaps; these are no longer advisory")
    if optional_stage_decision_status == "warning-missing-explicit-decision":
        improvement_actions.append(
            "record an explicit Stage-02.5 activation or skip decision whenever Phase-1 identifies material third-party dependencies"
        )
    elif optional_stage_present and not optional_stage_quality_gate:
        improvement_actions.append(
            "close the Stage-02.5 lane gaps so dependency manifest, IDRs, adapter specs, test strategy, and risk register all converge together"
        )
    if coverage_summary.get("overall_verdict") != "pass":
        improvement_actions.append(
            "close all Phase-1 to Phase-2 coverage gaps and replace inferred-only bindings with explicit `upstream_trace_ids`"
        )
    if cross_stage_verdict != "consistent":
        improvement_actions.append(
            f"close the failing cross-stage consistency items recorded in `{cross_stage_report_path.name}`"
        )
    if not mermaid_overall_passed:
        improvement_actions.append(
            f"close the failing Mermaid standard items recorded in `{mermaid_report_path.name}`"
        )
    if quality_report["overall_quality_gate"] != "pass":
        improvement_actions.append("close the remaining stage quality-gate failures before treating the pack as intake-ready")
    if semantic_warning_report.get("applied") and not semantic_warning_report.get("passed"):
        improvement_actions.append("close the warning-level semantic depth findings so strong structure is matched by deeper ADR/scenario content")
    if first_pass_passed:
        improvement_actions.append(
            "prove the upgraded templates on an independently authored fresh case so semantic confidence comes from generation evidence, not only case-root hygiene plus rerun closure"
        )
    else:
        improvement_actions.append(
            "re-scaffold a fresh case root and re-author Stage-01..04 before claiming fresh first-pass evidence"
        )
    if validation_result != "pass" or trace_runtime_contract_verdict != "pass":
        improvement_actions.append("repair the traceability runtime so validation passes before downstream intake")
    else:
        improvement_actions.append("add repeated-case trace/runtime evidence so the stronger readiness claim is supported beyond a single rerun")
    if fine_grained_total == 0:
        improvement_actions.append("bind fine-grained decision / contract / RBI / replay trace units instead of relying on coarse stage-artifact trace only")
    top_3_improvement_actions = "\n".join(f"- {item}" for item in improvement_actions[:3])

    gap_points: list[str] = []
    if coverage_summary.get("overall_verdict") != "pass":
        gap_points.append(
            f"Phase-1 to Phase-2 coverage remains incomplete: explicit={coverage_summary.get('pass_rows', 0)}, inferred-only={coverage_summary.get('inferred_only_rows', 0)}, missing={coverage_summary.get('missing_rows', 0)}"
        )
    if review_bound["verdict"] != "within-ceiling":
        gap_points.append(
            f"review-bound ratio remains {review_bound['ratio']}% over the {review_bound_ceiling}% ceiling"
        )
    if int(deliverable_assessment.get("triggered_conditional_gap_count", 0) or 0) > 0:
        gap_points.append(
            f"triggered conditional deliverable gaps remain open: {deliverable_assessment.get('triggered_conditional_gap_count', 0)}"
        )
    if int(deliverable_assessment.get("mandatory_gap_count", 0) or 0) > 0:
        gap_points.append(
            f"mandatory deliverable gaps remain open: {deliverable_assessment.get('mandatory_gap_count', 0)}"
        )
    if optional_stage_decision_status == "warning-missing-explicit-decision":
        gap_points.append("Stage-02.5 activation/skip decision is still implicit even though Phase-1 indicates external dependencies")
    elif optional_stage_present and not optional_stage_quality_gate:
        gap_points.append(f"Stage-02.5 remains incomplete: {optional_stage_failure_names}")
    if cross_stage_verdict != "consistent":
        gap_points.append("cross-stage alignment still has unresolved mismatches")
    if not mermaid_overall_passed:
        gap_points.append("Mermaid standard coverage/syntax still has unresolved gaps")
    if quality_report["overall_quality_gate"] != "pass":
        gap_points.append("stage quality gates have not fully converged")
    if semantic_warning_report.get("applied") and not semantic_warning_report.get("passed"):
        gap_points.append("warning-level semantic depth checks still flag ADR and/or scenario thinness")
    if validation_result != "pass" or trace_runtime_contract_verdict != "pass":
        gap_points.append("traceability runtime validation is not yet stable")
    if fine_grained_total == 0:
        gap_points.append("fine-grained trace units are not yet bound into the runtime registry")
    if not first_pass_passed:
        gap_points.append("fresh first-pass scaffold hygiene is incomplete for this case root")
    if not gap_points:
        gap_points.append(
            "no structural or semantic gate gaps remain in this case; the remaining distance to 9.5 is broader fresh-case evidence and repeated real-case validation rather than a current-case blocker"
        )
    gap_analysis_to_95 = "; ".join(gap_points)

    next_round_focus_items: list[str] = []
    if coverage_summary.get("overall_verdict") != "pass":
        next_round_focus_items.append("replace inferred-only/missing Phase-1 bindings with explicit `upstream_trace_ids` across decision, scenario, replay, and RBI rows")
    if review_bound["verdict"] != "within-ceiling":
        next_round_focus_items.append(
            f"reduce `review_bound_ratio` from {review_bound['ratio']}% to {review_bound_ceiling}% or below"
        )
    if optional_stage_decision_status == "warning-missing-explicit-decision":
        next_round_focus_items.append("record the missing Stage-02.5 activation/skip decision and bind it to the case root")
    elif optional_stage_present and not optional_stage_quality_gate:
        next_round_focus_items.append("finish the incomplete Stage-02.5 dependency / IDR / adapter / test-strategy / risk-register surfaces")
    if cross_stage_verdict != "consistent":
        next_round_focus_items.append("close the remaining cross-stage consistency mismatches")
    if not mermaid_overall_passed:
        next_round_focus_items.append("close the remaining Mermaid syntax/type coverage gaps")
    if semantic_warning_report.get("applied") and not semantic_warning_report.get("passed"):
        next_round_focus_items.append("close warning-level semantic depth findings in ADRs, endpoint samples, and scenario GWT structure")
    if first_pass_passed:
        next_round_focus_items.append(
            "run an independently authored fresh case directly on the upgraded templates instead of carrying forward a retrofitted baseline"
        )
    else:
        next_round_focus_items.append("re-scaffold a clean case root and author Stage-01..04 before rerunning wrapper closure")
    if validation_result == "pass" and trace_runtime_contract_verdict == "pass":
        next_round_focus_items.append("add repeated-case trace/runtime evidence to support a stronger implementation-ready claim")
    else:
        next_round_focus_items.append("repair traceability runtime validation")
    if fine_grained_total == 0:
        next_round_focus_items.append("bind decision / contract / RBI / replay trace units into the official registry")
    next_round_focus = "\n".join(f"  - {item}" for item in next_round_focus_items[:3])
    if validation_result == "pass" and trace_runtime_contract_verdict == "pass" and all(
        fine_grained_trace_summary.get(key, 0) > 0 for key in fine_grained_trace_summary
    ):
        traceability_integrity_score = "10"
        traceability_integrity_evidence = (
            f"traceability runtime validated with fine-grained units bound: decisions={fine_grained_trace_summary.get('decision_trace_units', 0)}, "
            f"contracts={fine_grained_trace_summary.get('contract_trace_units', 0)}, "
            f"rbis={fine_grained_trace_summary.get('rbi_trace_units', 0)}, "
            f"replays={fine_grained_trace_summary.get('replay_trace_units', 0)}"
        )
        traceability_integrity_gap = "add cross-case repeated evidence and deeper decision-to-contract link chains"
    else:
        traceability_integrity_score = "8"
        traceability_integrity_evidence = "traceability runtime initialized, bound, validated, and reported"
        traceability_integrity_gap = "add stronger trace/runtime evidence on repeated real cases"

    architecture_decision_depth_score = (
        9
        if current_metrics["architecture_decisions_count"] >= (4 if complexity_profile == "micro" else 7)
        and current_metrics.get("structured_adr_multi_alt_count", 0) >= (4 if complexity_profile == "micro" else 7)
        else 6
    )
    domain_decomposition_clarity_score = 8 if current_metrics["domain_count"] >= (3 if complexity_profile == "micro" else 4) else 6
    specification_completeness_score = (
        8
        if current_metrics["schema_table_count"] >= (5 if complexity_profile == "micro" else 10)
        and current_metrics["api_endpoint_count"] >= (5 if complexity_profile == "micro" else 10)
        else 6
    )
    visual_representation_quality_score = (
        5
        if current_metrics["mermaid_sequenceDiagram_count"]
        + current_metrics["mermaid_erDiagram_count"]
        + current_metrics["mermaid_C4Context_count"]
        + current_metrics["mermaid_C4Container_count"]
        + current_metrics["mermaid_gantt_count"]
        < 6
        else 8
    )
    process_governance_rigor_score = 8 if quality_report["baseline_lock"]["overall_regression_gate"] == "pass" else 5
    traceability_integrity_score_int = int(traceability_integrity_score)
    aggregate_self_assessment_score = round(
        (
            architecture_decision_depth_score
            + domain_decomposition_clarity_score
            + specification_completeness_score
            + visual_representation_quality_score
            + process_governance_rigor_score
            + traceability_integrity_score_int
        )
        / 6,
        1,
    )

    classification_selection_mode = str(complexity_classification_report.get("selection_mode", "unknown"))
    classification_suggested_profile = str(
        complexity_classification_report.get("suggested_profile", complexity_profile)
    )
    classification_confidence = str(
        complexity_classification_report.get("selection_confidence", "unknown")
    )
    classification_override_reason = str(
        complexity_classification_report.get("override_justification", "") or "none"
    )
    classification_indicator_lines = "\n".join(
        f"- {name}: `{details.get('value')}` -> `{details.get('profile_vote')}` ({details.get('reason', 'no reason')})"
        for name, details in (complexity_classification_report.get("indicators") or {}).items()
    )
    if not classification_indicator_lines:
        classification_indicator_lines = "- none"
    deployment_warning_summary = deployment_posture["warning_summary"]

    execution_report_computed_values = {
        "P2_EXEC_EXPR_001": deployment_warning_summary if deployment_warning_summary != 'none' else f"suggested={deployment_posture['suggested']}, selected={deployment_posture['selected']}, mode={deployment_posture['selection_mode']}",
        "P2_EXEC_EXPR_002": 'true' if optional_stage_expected else 'false',
        "P2_EXEC_EXPR_003": 'true' if first_pass_passed else 'false',
        "P2_EXEC_EXPR_004": deliverable_summary.get('mandatory_count', len(mandatory_rows)),
        "P2_EXEC_EXPR_005": deliverable_summary.get('triggered_conditional_count', len(triggered_conditional_rows)),
        "P2_EXEC_EXPR_006": deliverable_summary.get('not_triggered_conditional_count', len(not_triggered_conditional_rows)),
        "P2_EXEC_EXPR_007": len(triggered_rows),
        "P2_EXEC_EXPR_008": len(triggered_rows),
        "P2_EXEC_EXPR_009": 'complete' if mapping_complete else 'incomplete',
        "P2_EXEC_EXPR_010": coverage_summary.get('total_phase1_trace_units', 0),
        "P2_EXEC_EXPR_011": coverage_summary.get('pass_rows', 0),
        "P2_EXEC_EXPR_012": coverage_summary.get('inferred_only_rows', 0),
        "P2_EXEC_EXPR_013": coverage_summary.get('missing_rows', 0),
        "P2_EXEC_EXPR_014": coverage_summary.get('overall_verdict', 'fail'),
        "P2_EXEC_EXPR_015": 'present and evaluated' if optional_stage_present else 'not present in this run',
        "P2_EXEC_EXPR_016": 'true' if optional_stage_expected else 'false',
        "P2_EXEC_EXPR_017": 'provider/auth/fallback/mock-sandbox posture is now an explicit Stage-03 and Phase-3 input' if optional_stage_present else 'no optional third-party integration lane was consumed in this run',
        "P2_EXEC_EXPR_018": markdown_table(['check_category', 'check_item', 'result', 'inconsistency_found', 'resolution_or_justification'], [[row['check_category'], row['check_item'], row['result'], row['inconsistency_found'], row['resolution_or_justification']] for row in cross_stage_rows]),
        "P2_EXEC_EXPR_019": current_metrics.get('structured_adr_multi_alt_count', 0),
        "P2_EXEC_EXPR_020": format(aggregate_self_assessment_score, '.1f'),
        "P2_EXEC_EXPR_021": 'none' if formal_state != 'blocked' else 'quality-gate-fail or regression-gate-fail detected',
        "P2_EXEC_EXPR_022": readiness_alignment.get('stage_04_label', 'not-declared'),
        "P2_EXEC_EXPR_023": readiness_alignment.get('quality_based_label', 'unknown'),
        "P2_EXEC_EXPR_024": readiness_alignment.get('final_label', formal_state),
        "P2_EXEC_EXPR_025": readiness_alignment.get('verdict', 'unknown'),
        "P2_EXEC_EXPR_026": ''.join((f'  - {reason}\n' for reason in closure_adjustment_reasons)) if closure_adjustment_reasons else '  - none\n',
        "P2_EXEC_EXPR_027": 'yes' if esp_check.get('passed') else 'no',
    }
    text = render_phase2_execution_report_template(locals(), execution_report_computed_values)
    output.write_text(localize_phase2_execution_report(text.rstrip() + "\n", output_locale), encoding="utf-8")


def run_first_pass_audit_or_exit(context: Phase2FullTrialContext) -> dict[str, Any]:
    existing_first_pass_audit_path = find_cross_phase_surface_path(
        context.output_dir,
        "phase2",
        "phase-2-first-pass-audit.json",
    )
    existing_first_pass_audit = load_json(existing_first_pass_audit_path) if existing_first_pass_audit_path.exists() else None
    first_pass_audit_report = preserve_initial_first_pass_audit(
        existing_first_pass_audit,
        inspect_case_for_runner(context.output_dir, context.stage_paths, context.stage_02_5),
    )
    context.first_pass_audit_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(context.first_pass_audit_path, first_pass_audit_report)
    first_pass_audit_ok, first_pass_audit_blockers = evaluate_first_pass_audit_gate(first_pass_audit_report)
    print(
        f"first_pass_audit: {context.first_pass_audit_path} ({first_pass_audit_report.get('status', 'unknown')})",
        flush=True,
    )
    if not first_pass_audit_ok:
        print("[BLOCKED] fresh first-pass audit failed:")
        for blocker in first_pass_audit_blockers:
            print(f"- {blocker}")
        raise SystemExit(2)
    if first_pass_audit_report.get("issues"):
        print("[WARN] fresh first-pass audit issues detected:")
        for issue in first_pass_audit_report["issues"]:
            print(f"- {issue}")
    return first_pass_audit_report


def resolve_phase2_baseline_lock_path(context: Phase2FullTrialContext) -> Path | None:
    return context.baseline_lock if context.baseline_lock.exists() else None


def analyze_phase2_quality_report(
    context: Phase2FullTrialContext,
    *,
    include_engineering_spec_pack: bool = False,
    include_implementation_entry: bool = False,
) -> dict[str, Any]:
    quality_report = analyze_phase2_case(
        stage_paths=context.stage_paths,
        complexity_profile=context.selected_complexity_profile,
        phase1_prd=context.phase1_prd,
        stage_02_5=context.stage_02_5,
        baseline_lock_path=resolve_phase2_baseline_lock_path(context),
        baseline_output_path=context.baseline_lock,
        engineering_spec_pack=context.engineering_spec_pack if include_engineering_spec_pack else None,
        acd_artifact_root=context.output_dir if include_engineering_spec_pack else None,
        implementation_entry=context.implementation_entry if include_implementation_entry else None,
    )
    write_json(context.quality_report_path, quality_report)
    return quality_report


def resolve_phase2_formal_state_with_override(context: Phase2FullTrialContext, formal_state: str) -> str:
    if not context.formal_state_override:
        return formal_state
    return weaker_formal_state(formal_state, context.formal_state_override)


def write_phase2_implementation_entry_artifact(
    context: Phase2FullTrialContext,
    *,
    formal_state: str,
) -> None:
    write_implementation_entry(
        output=context.implementation_entry,
        case_name=context.case_name,
        version=context.version,
        engineering_spec_pack=context.engineering_spec_pack,
        execution_report=context.execution_report,
        stage_02_5=context.stage_02_5,
        stage_04=context.stage_04,
        quality_report=context.quality_report_path,
        cross_stage_report=context.cross_stage_report_path,
        trace_validation=context.trace_validation,
        formal_state=formal_state,
        output_locale=context.output_locale,
    )


def bootstrap_phase2_trace_registry(context: Phase2FullTrialContext) -> None:
    run(
        [
            context.python,
            str(context.trace_dir / "init_registry.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--project-label",
            context.case_name,
        ]
    )
    bind_phase1_prd_trace_units(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        phase1_prd=context.phase1_prd,
    )

    stage_bindings = [
        ("stage_01", context.stage_01, STAGE_IDS["stage_01"], "stage-01"),
        ("stage_02", context.stage_02, STAGE_IDS["stage_02"], "stage-02"),
        ("stage_03", context.stage_03, STAGE_IDS["stage_03"], "stage-03"),
        ("stage_04", context.stage_04, STAGE_IDS["stage_04"], "stage-04"),
    ]
    if context.stage_02_5 and context.stage_02_5.exists():
        stage_bindings.insert(2, ("stage_02_5", context.stage_02_5, OPTIONAL_STAGE_02_5_ID, "stage-02.5"))
    for _, path, artifact_id, stage_or_lane in stage_bindings:
        run(
            [
                context.python,
                str(context.trace_dir / "bind_artifact.py"),
                "--project-root",
                str(context.output_dir),
                "--project-key",
                context.project_key,
                "--artifact-id",
                artifact_id,
                "--artifact-type",
                "ARCH",
                "--source-path",
                relpath(path, context.output_dir),
                "--source-anchor",
                artifact_id.lower(),
                "--stage-or-lane",
                stage_or_lane,
                "--status",
                "review",
            ]
        )
    run(
        [
            context.python,
            str(context.trace_dir / "link_artifacts.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--from-artifact-id",
            STAGE_IDS["stage_01"],
            "--to-artifact-id",
            PHASE1_PRD_ARTIFACT_ID,
            "--link-type",
            "depends_on",
            "--source-path",
            relpath(context.stage_01, context.output_dir),
            "--evidence-anchor",
            "traceability-naming-and-registry",
        ]
    )
    if context.stage_02_5 and context.stage_02_5.exists():
        run(
            [
                context.python,
                str(context.trace_dir / "link_artifacts.py"),
                "--project-root",
                str(context.output_dir),
                "--project-key",
                context.project_key,
                "--from-artifact-id",
                OPTIONAL_STAGE_02_5_ID,
                "--to-artifact-id",
                STAGE_IDS["stage_02"],
                "--link-type",
                "depends_on",
                "--source-path",
                relpath(context.stage_02_5, context.output_dir),
                "--evidence-anchor",
                OPTIONAL_STAGE_02_5_ID.lower(),
            ]
        )
        run(
            [
                context.python,
                str(context.trace_dir / "link_artifacts.py"),
                "--project-root",
                str(context.output_dir),
                "--project-key",
                context.project_key,
                "--from-artifact-id",
                STAGE_IDS["stage_03"],
                "--to-artifact-id",
                OPTIONAL_STAGE_02_5_ID,
                "--link-type",
                "depends_on",
                "--source-path",
                relpath(context.stage_03, context.output_dir),
                "--evidence-anchor",
                STAGE_IDS["stage_03"].lower(),
            ]
        )


def assemble_preclosure_delivery_artifacts(
    context: Phase2FullTrialContext,
) -> tuple[dict[str, Any], str]:
    analyze_phase2_quality_report(context)

    stage_03_text = context.stage_03.read_text(encoding="utf-8")
    endpoint_rows = api_rows(stage_03_text)
    contract_rows = contract_trace_rows(stage_03_text)
    schema_registry_rows = schema_rows(stage_03_text)
    operation_design_source_rows = build_operation_design_source_rows(endpoint_rows, contract_rows)
    preliminary_phase1_trace_resolution_report = build_phase2_phase1_resolution_report(
        phase1_prd=context.phase1_prd,
        fine_grained_trace_units=extract_fine_grained_trace_units(context.stage_paths),
    )
    operation_source_obligation_rows = build_operation_source_obligation_rows(
        endpoint_rows,
        contract_rows,
        operation_design_source_rows,
        contract_phase1_trace_map=contract_phase1_trace_map_from_report(preliminary_phase1_trace_resolution_report),
    )
    business_value_signal_registry = load_business_value_signal_registry(context.phase1_prd)
    p1_value_resolution_rows = build_p1_value_to_p2_operation_resolution_rows(
        business_value_signal_registry, operation_source_obligation_rows
    )
    implementation_depth_rows = build_implementation_depth_obligation_rows(
        operation_source_obligation_rows, p1_value_resolution_rows
    )
    component_catalog_rows = build_implementation_component_catalog_rows(
        endpoint_rows, schema_registry_rows, operation_source_obligation_rows
    )
    component_obligation_rows = build_component_action_card_obligation_rows(component_catalog_rows, implementation_depth_rows)
    operation_ids = [str(row.get("operation_id", "")).strip() for row in p1_value_resolution_rows if str(row.get("operation_id", "")).strip()]
    operation_semantic_payload = build_operation_semantic_payload(context.output_dir, operation_ids)
    write_json(
        resolve_cross_phase_surface_path(context.output_dir, "phase2", "operation-design-source-registry.json"),
        {"sources": operation_design_source_rows},
    )
    write_json(
        resolve_cross_phase_surface_path(context.output_dir, "phase2", "operation-source-obligation-matrix.json"),
        {"operations": operation_source_obligation_rows},
    )
    write_json(
        resolve_cross_phase_surface_path(
            context.output_dir,
            "phase2",
            "p1-value-to-p2-operation-resolution-matrix.json",
        ),
        {"resolutions": p1_value_resolution_rows},
    )
    write_json(
        resolve_cross_phase_surface_path(context.output_dir, "phase2", "operation-behavior-semantics.json"),
        operation_semantic_payload,
    )
    write_json(
        resolve_cross_phase_surface_path(context.output_dir, "phase2", "implementation-depth-obligation-matrix.json"),
        {"operations": implementation_depth_rows},
    )
    write_json(
        resolve_cross_phase_surface_path(context.output_dir, "phase2", "implementation-component-catalog.json"),
        {"components": component_catalog_rows},
    )
    write_json(
        resolve_cross_phase_surface_path(context.output_dir, "phase2", "component-action-card-obligation-matrix.json"),
        {"components": component_obligation_rows},
    )
    _, _, upstream_sidecar = _phase1_claims_for_phase2_handoff(context.phase1_prd)
    emit_component_semantic_inventory(
        output_dir=context.output_dir,
        phase1_prd=context.phase1_prd,
        phase1_claim_control_sidecar=upstream_sidecar,
        component_catalog_rows=component_catalog_rows,
        component_obligation_rows=component_obligation_rows,
        operation_resolution_rows=p1_value_resolution_rows,
        operation_source_rows=operation_source_obligation_rows,
    )

    write_engineering_spec_pack(
        output=context.engineering_spec_pack,
        case_name=context.case_name,
        version=context.version,
        profile=context.profile,
        run_owner=context.owner,
        stage_01=context.stage_01,
        stage_02=context.stage_02,
        stage_02_5=context.stage_02_5,
        stage_03=context.stage_03,
        stage_04=context.stage_04,
        phase1_prd=context.phase1_prd,
        execution_report=context.execution_report,
        trace_validation=context.trace_validation,
        trace_report_text=context.trace_report_text,
        existing_system_architecture_change_intake=context.existing_system_architecture_change_intake,
        output_locale=context.output_locale,
    )
    emit_phase2_handoff_claim_control_sidecar(context)

    pre_entry_quality_report = analyze_phase2_quality_report(
        context,
        include_engineering_spec_pack=True,
    )
    pre_closure_formal_state = resolve_phase2_formal_state_with_override(
        context,
        pre_entry_quality_report["recommended_formal_state"],
    )
    write_phase2_implementation_entry_artifact(context, formal_state=pre_closure_formal_state)

    quality_report = analyze_phase2_quality_report(
        context,
        include_engineering_spec_pack=True,
        include_implementation_entry=True,
    )
    final_pre_closure_formal_state = resolve_phase2_formal_state_with_override(
        context,
        quality_report["recommended_formal_state"],
    )
    if final_pre_closure_formal_state != pre_closure_formal_state:
        pre_closure_formal_state = final_pre_closure_formal_state
        write_phase2_implementation_entry_artifact(context, formal_state=pre_closure_formal_state)

    run(
        [
            context.python,
            str(context.trace_dir / "bind_artifact.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--artifact-id",
            "HANDOFF-0001",
            "--artifact-type",
            "HANDOFF",
            "--source-path",
            relpath(context.engineering_spec_pack, context.output_dir),
            "--source-anchor",
            "engineering-spec-pack",
            "--stage-or-lane",
            "phase-2-engspec",
            "--status",
            "review",
        ]
    )
    run(
        [
            context.python,
            str(context.trace_dir / "bind_artifact.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--artifact-id",
            "IMPL-STG00-INPUT-0001",
            "--artifact-type",
            "HANDOFF",
            "--source-path",
            relpath(context.implementation_entry, context.output_dir),
            "--source-anchor",
            "phase-3-implementation-entry",
            "--stage-or-lane",
            "implementation-entry",
            "--status",
            "review",
        ]
    )

    return quality_report, pre_closure_formal_state


def run_phase2_traceability_validation_suite(context: Phase2FullTrialContext) -> Phase2TraceabilitySuiteResult:
    fine_grained_trace_units = extract_fine_grained_trace_units(context.stage_paths)
    bind_stage03_interface_surfaces(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        source_path=context.stage_03,
        upstream_artifact_id=STAGE_IDS["stage_03"],
    )
    bind_trace_units(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        source_path=context.stage_01,
        upstream_artifact_id=STAGE_IDS["stage_01"],
        stage_or_lane="stage-01-decision",
        artifact_type="DECISION",
        units=fine_grained_trace_units["decision_trace_units"],
        id_field="trace_id",
    )
    bind_trace_units(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        source_path=context.stage_03,
        upstream_artifact_id=STAGE_IDS["stage_03"],
        stage_or_lane="stage-03-contract",
        artifact_type="INTERFACE",
        units=fine_grained_trace_units["contract_trace_units"],
        id_field="trace_id",
    )
    bind_trace_units(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        source_path=context.stage_04,
        upstream_artifact_id=STAGE_IDS["stage_04"],
        stage_or_lane="stage-04-rbi",
        artifact_type="RISK",
        units=fine_grained_trace_units["rbi_trace_units"],
        id_field="trace_id",
    )
    bind_trace_units(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        source_path=context.stage_04,
        upstream_artifact_id=STAGE_IDS["stage_04"],
        stage_or_lane="stage-04-replay",
        artifact_type="VERIFY",
        units=fine_grained_trace_units["replay_trace_units"],
        id_field="replay_id",
    )
    phase1_trace_resolution_report = link_phase2_upstream_trace_units(
        python=context.python,
        trace_dir=context.trace_dir,
        output_dir=context.output_dir,
        project_key=context.project_key,
        stage_paths=context.stage_paths,
        phase1_prd=context.phase1_prd,
        fine_grained_trace_units=fine_grained_trace_units,
        resolution_report_path=context.phase1_trace_resolution_path,
    )
    phase1_phase2_coverage_report = build_phase1_phase2_coverage_report(
        phase1_prd=context.phase1_prd,
        stage_03=context.stage_03,
        resolution_report=phase1_trace_resolution_report,
    )
    write_json(context.phase1_phase2_coverage_path, phase1_phase2_coverage_report)

    upstream_stage_ids = [
        STAGE_IDS["stage_01"],
        STAGE_IDS["stage_02"],
        *([OPTIONAL_STAGE_02_5_ID] if context.stage_02_5 and context.stage_02_5.exists() else []),
        STAGE_IDS["stage_03"],
        STAGE_IDS["stage_04"],
    ]

    run(
        [
            context.python,
            str(context.trace_dir / "register_phase2_pilot.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--ids",
            ",".join(upstream_stage_ids),
            "--downstream-id",
            "IMPL-STG00-INPUT-0001",
        ]
    )

    for upstream_id in upstream_stage_ids:
        run(
            [
                context.python,
                str(context.trace_dir / "link_artifacts.py"),
                "--project-root",
                str(context.output_dir),
                "--project-key",
                context.project_key,
                "--from-artifact-id",
                "HANDOFF-0001",
                "--to-artifact-id",
                upstream_id,
                "--link-type",
                "depends_on",
            ]
        )
    run(
        [
            context.python,
            str(context.trace_dir / "link_artifacts.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--from-artifact-id",
            "HANDOFF-0001",
            "--to-artifact-id",
            "IMPL-STG00-INPUT-0001",
            "--link-type",
            "feeds",
        ]
    )

    run(
        [
            context.python,
            str(context.trace_dir / "bind_artifact.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--artifact-id",
            "VERIFY-0001",
            "--artifact-type",
            "VERIFY",
            "--source-path",
            relpath(context.execution_report, context.output_dir),
            "--source-anchor",
            "phase-2-execution-report",
            "--stage-or-lane",
            "phase-2-report",
            "--status",
            "review",
        ]
    )
    for upstream_id in (*STAGE_IDS.values(), "HANDOFF-0001"):
        run(
            [
                context.python,
                str(context.trace_dir / "link_artifacts.py"),
                "--project-root",
                str(context.output_dir),
                "--project-key",
                context.project_key,
                "--from-artifact-id",
                "VERIFY-0001",
                "--to-artifact-id",
                upstream_id,
                "--link-type",
                "depends_on",
            ]
        )

    validation_proc = run(
        [
            context.python,
            str(context.trace_dir / "validate_registry.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
        ],
        capture=True,
    )
    context.trace_validation.write_text(
        ((validation_proc.stdout or "") + (validation_proc.stderr or "")).rstrip() + "\n",
        encoding="utf-8",
    )

    report_text_proc = run(
        [
            context.python,
            str(context.trace_dir / "report_registry.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--format",
            "text",
        ],
        capture=True,
    )
    context.trace_report_text.write_text((report_text_proc.stdout or "").rstrip() + "\n", encoding="utf-8")
    report_json_proc = run(
        [
            context.python,
            str(context.trace_dir / "report_registry.py"),
            "--project-root",
            str(context.output_dir),
            "--project-key",
            context.project_key,
            "--format",
            "json",
        ],
        capture=True,
    )
    context.trace_report_json.write_text((report_json_proc.stdout or "").rstrip() + "\n", encoding="utf-8")

    trace_runtime_contract_verdict = "fail"
    trace_runtime_contract_issues = ["missing trace runtime report json"]
    trace_db_path = ""
    trace_registry_root = ""
    fine_grained_trace_summary = {
        "decision_trace_units": 0,
        "contract_trace_units": 0,
        "rbi_trace_units": 0,
        "replay_trace_units": 0,
    }
    try:
        trace_runtime_report = json.loads(report_json_proc.stdout or "{}")
        trace_runtime_contract_verdict, trace_runtime_contract_issues = evaluate_trace_runtime_contract(
            trace_runtime_report
        )
        trace_db_path = str(trace_runtime_report.get("registry_db_path", "")).strip()
        trace_registry_root = str(trace_runtime_report.get("trace_registry_root", "")).strip()
        fine_grained_trace_summary = summarize_fine_grained_trace_runtime(trace_runtime_report)
    except json.JSONDecodeError:
        trace_runtime_contract_verdict = "fail"
        trace_runtime_contract_issues = ["trace runtime report is not valid json"]
        trace_db_path = ""
        trace_registry_root = ""

    mermaid_cmd = build_mermaid_validation_command(context, render=bool(shutil.which("mmdc")))
    run(mermaid_cmd)
    run(
        [
            context.python,
            str(context.script_dir / "cross_stage_consistency.py"),
            "--phase1-prd",
            str(context.phase1_prd),
            "--stage-01",
            str(context.stage_01),
            "--stage-02",
            str(context.stage_02),
            "--stage-03",
            str(context.stage_03),
            "--stage-04",
            str(context.stage_04),
            "--output",
            str(context.cross_stage_report_path),
        ]
    )

    return Phase2TraceabilitySuiteResult(
        phase1_trace_resolution_report=phase1_trace_resolution_report,
        phase1_phase2_coverage_report=phase1_phase2_coverage_report,
        trace_runtime_contract_verdict=trace_runtime_contract_verdict,
        trace_runtime_contract_issues=trace_runtime_contract_issues,
        trace_db_path=trace_db_path,
        trace_registry_root=trace_registry_root,
        fine_grained_trace_summary=fine_grained_trace_summary,
        mermaid_report=json.loads(context.mermaid_report_path.read_text(encoding="utf-8")),
        cross_stage_report=json.loads(context.cross_stage_report_path.read_text(encoding="utf-8")),
    )


def finalize_phase2_closure(
    context: Phase2FullTrialContext,
    *,
    first_pass_audit_report: dict[str, Any],
    trace_suite: Phase2TraceabilitySuiteResult,
) -> Phase2ClosureResult:
    provisional_formal_state = context.formal_state_override or "implementation-planning-ready"
    write_phase2_implementation_entry_artifact(context, formal_state=provisional_formal_state)

    quality_report = analyze_phase2_quality_report(
        context,
        include_engineering_spec_pack=True,
        include_implementation_entry=True,
    )
    pre_closure_formal_state = resolve_phase2_formal_state_with_override(
        context,
        quality_report["recommended_formal_state"],
    )
    effective_formal_state, closure_adjustment_reasons = closure_capped_formal_state(
        pre_closure_formal_state,
        cross_stage_verdict=trace_suite.cross_stage_report.get("overall_consistency_verdict", "unknown"),
        mermaid_overall_passed=bool(trace_suite.mermaid_report.get("overall_passed")),
        validation_result=extract_validation_result(context.trace_validation.read_text(encoding="utf-8")),
        trace_runtime_contract_verdict=trace_suite.trace_runtime_contract_verdict,
        phase1_phase2_coverage_verdict=trace_suite.phase1_phase2_coverage_report.get("summary", {}).get(
            "overall_verdict",
            "fail",
        ),
    )
    effective_realizability_judgment = context.realizability_judgment_override or default_realizability_judgment(
        effective_formal_state
    )

    write_phase2_implementation_entry_artifact(context, formal_state=effective_formal_state)

    write_execution_report(
        output=context.execution_report,
        case_name=context.case_name,
        phase1_prd=context.phase1_prd,
        version=context.version,
        profile=context.profile,
        complexity_profile=context.selected_complexity_profile,
        complexity_classification_path=context.complexity_classification_path,
        complexity_classification_report=context.complexity_classification_report,
        deployment_posture=context.deployment_posture,
        run_owner=context.owner,
        stage_01=context.stage_01,
        stage_02=context.stage_02,
        stage_02_5=context.stage_02_5,
        stage_03=context.stage_03,
        stage_04=context.stage_04,
        engineering_spec_pack=context.engineering_spec_pack,
        implementation_entry=context.implementation_entry,
        first_pass_audit_report=first_pass_audit_report,
        first_pass_audit_path=context.first_pass_audit_path,
        trace_validation=context.trace_validation,
        trace_report_text=context.trace_report_text,
        trace_registry_root=trace_suite.trace_registry_root,
        trace_db_path=trace_suite.trace_db_path,
        trace_runtime_contract_verdict=trace_suite.trace_runtime_contract_verdict,
        trace_runtime_contract_issues=trace_suite.trace_runtime_contract_issues,
        phase1_phase2_coverage_report=trace_suite.phase1_phase2_coverage_report,
        phase1_phase2_coverage_path=context.phase1_phase2_coverage_path,
        fine_grained_trace_summary=trace_suite.fine_grained_trace_summary,
        quality_report=quality_report,
        mermaid_report=trace_suite.mermaid_report,
        mermaid_report_path=context.mermaid_report_path,
        cross_stage_report=trace_suite.cross_stage_report,
        cross_stage_report_path=context.cross_stage_report_path,
        formal_state=effective_formal_state,
        realizability_judgment=effective_realizability_judgment,
        baseline_reference=str(context.baseline_lock),
        closure_adjustment_reasons=closure_adjustment_reasons,
        output_locale=context.output_locale,
    )

    mainline_assessment = build_phase2_mainline_assessment(
        quality_report=quality_report,
        cross_stage_report=trace_suite.cross_stage_report,
        mermaid_report=trace_suite.mermaid_report,
        effective_formal_state=effective_formal_state,
        closure_adjustment_reasons=closure_adjustment_reasons,
    )
    mainline_artifacts = write_phase2_mainline_assessment_artifacts(
        output_dir=context.output_dir,
        assessment=mainline_assessment,
    )

    return Phase2ClosureResult(
        effective_formal_state=effective_formal_state,
        effective_realizability_judgment=effective_realizability_judgment,
        closure_adjustment_reasons=closure_adjustment_reasons,
        mainline_assessment=mainline_assessment,
        mainline_artifacts=mainline_artifacts,
    )


def main() -> int:
    timing_started_at = utc_now_iso()
    timing_started_monotonic = time.monotonic()
    timing_segments: list[dict[str, Any]] = []
    context: Phase2FullTrialContext | None = None
    args = parse_phase2_full_trial_args()
    try:
        context = phase2_full_trial_timed_segment(
            timing_segments,
            "build_context",
            lambda: build_phase2_full_trial_context(args),
        )
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        raise SystemExit(2)

    try:
        log_phase2_full_trial_start(context)

        contamination_report = phase2_full_trial_timed_segment(
            timing_segments,
            "p1_to_p2_contamination_preflight",
            lambda: run_phase2_handoff_contamination_preflight(context),
        )
        if contamination_report["overall_status"] == "blocked":
            print(f"[BLOCKED] p1-to-p2 contamination boundary failed: {context.contamination_report_path}")
            print(f"classifications: {', '.join(contamination_report['classifications'])}")
            return 2

        first_pass_audit_report = phase2_full_trial_timed_segment(
            timing_segments,
            "first_pass_audit",
            lambda: run_first_pass_audit_or_exit(context),
        )
        phase2_full_trial_timed_segment(
            timing_segments,
            "bootstrap_trace_registry",
            lambda: bootstrap_phase2_trace_registry(context),
        )
        phase2_full_trial_timed_segment(
            timing_segments,
            "assemble_preclosure_delivery_artifacts",
            lambda: assemble_preclosure_delivery_artifacts(context),
        )

        trace_suite = phase2_full_trial_timed_segment(
            timing_segments,
            "traceability_validation_suite",
            lambda: run_phase2_traceability_validation_suite(context),
        )
        closure_result = phase2_full_trial_timed_segment(
            timing_segments,
            "finalize_phase2_closure",
            lambda: finalize_phase2_closure(
                context,
                first_pass_audit_report=first_pass_audit_report,
                trace_suite=trace_suite,
            ),
        )
        phase2_full_trial_timed_segment(
            timing_segments,
            "human_review_surface",
            lambda: emit_human_review_surface(context.output_dir, "phase2"),
        )

        print(f"execution_report: {context.execution_report}")
        print(f"engineering_spec_pack: {context.engineering_spec_pack}")
        print(f"human_review_index: {context.output_dir / 'human-review' / 'INDEX.md'}")
        print(f"implementation_entry: {context.implementation_entry}")
        print(f"first_pass_audit: {context.first_pass_audit_path}")
        print(f"trace_validation: {context.trace_validation}")
        print(f"trace_report_text: {context.trace_report_text}")
        print(f"trace_report_json: {context.trace_report_json}")
        print(f"phase1_trace_resolution_report: {context.phase1_trace_resolution_path}")
        print(f"baseline_lock: {context.baseline_lock}")
        print(f"quality_report: {context.quality_report_path}")
        print(f"mermaid_report: {context.mermaid_report_path}")
        print(f"cross_stage_report: {context.cross_stage_report_path}")
        print(f"phase2_full_trial_timing_report: {context.timing_report}")
        print(f"phase_mainline_scorecard: {closure_result.mainline_artifacts['scorecard_path']}")
        print(f"phase_acceptance_matrix: {closure_result.mainline_artifacts['acceptance_matrix_path']}")
        print(f"phase_verdict: {closure_result.mainline_artifacts['verdict_path']}")
        print(f"phase_total_score: {closure_result.mainline_assessment['total_score']} / 100")
        print(f"phase_mainline_verdict: {closure_result.mainline_assessment['verdict']}")
        print(f"recommended_formal_state: {closure_result.effective_formal_state}")
        print("FINAL: PASS")
        return 0
    finally:
        write_phase2_full_trial_timing_report(
            context,
            started_at=timing_started_at,
            started_monotonic=timing_started_monotonic,
            segments=timing_segments,
        )


if __name__ == "__main__":
    raise SystemExit(main())
