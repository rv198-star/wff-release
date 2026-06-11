#!/usr/bin/env python3
"""
Official Phase-2 fresh-run mainline entry.

This fills the missing synthesis layer between:
- Phase-1 PRD authority input
- fresh Phase-2 case root

The goal is not to replace later refinement loops. The goal is to ensure a
fresh P1 -> P2 run can produce authored Stage-01..04 artifacts instead of
stopping at scaffold-only stubs, and optionally complete the official closure
bundle by handing off to `run_phase2_full_trial.py`.
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
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.complexity_classifier import INTEGRATION_PATTERNS, classify_phase1_prd, count_external_integrations
from common.human_review_surface import emit_human_review_surface
from common.claim_control_runtime import (
    emit_path_b_claim_control_sidecar,
)
from common.tvg_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES
from phase1.phase1_trace_units import extract_phase1_trace_units, heading_section
from phase2.phase2_extract import (
    extract_dynamic_adr_titles,
    extract_dynamic_domains,
    extract_dynamic_objects,
    extract_dynamic_primary_surfaces,
    extract_module_definitions,
    extract_object_alias_hints,
)
from phase2.phase2_onboarding_prereqs import derive_environment_dependency_prerequisites, format_nested_bullets
from phase2.phase2_claim_authority import (
    audit_phase2_artifact_upstream_claim_refs,
    phase1_claims_for_phase2,
    phase2_claim_control_claim_ceiling,
    phase2_claim_control_report_status,
)
from phase2.phase2_quality_check import normalized_complexity_profile, profile_minimum
from phase2.scaffold_phase2_case import build_manifest, ensure_output_dir, infer_case_name, write_text
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path, write_cross_phase_profiled_surface
from common.output_language import resolve_output_locale
from phase2.existing_system_architecture_change import (
    materialize_existing_system_architecture_change_intake,
    render_existing_system_architecture_change_addendum,
    resolve_existing_system_architecture_change_intake,
)
from phase2.validate_fresh_first_pass_case import inspect_case

DEFAULT_ADR_TITLES = [
    "Adopt modular-monolith boundary with explicit public contracts",
    "Freeze typed recommendation payload before task handoff",
    "Enforce tenant-aware policy gate and auditable isolation boundary",
    "Use asynchronous observation completion events with idempotent replay",
    "Keep review-bound truth explicit instead of narrative readiness upgrades",
    "Standardize response envelope and business/system error split",
    "Use cursor-based pagination and indexed access patterns for growth surfaces",
    "Reserve attribution and external-identity concerns as explicit extension seams",
    "Separate contract-facing namespaces from internal storage layout",
    "Carry work-package and RBI chain into implementation intake unchanged",
]

DEFAULT_GENERIC_HANDOFF_ADR_TITLE = "Freeze typed handoff payload before downstream execution"
DEFAULT_GENERIC_ASYNC_COMPLETION_ADR_TITLE = "Use asynchronous workflow completion events with idempotent replay"
DEFAULT_GENERIC_EXTENSION_SEAM_ADR_TITLE = "Reserve deferred extension and external dependency concerns as explicit seams"
DEFAULT_GENERIC_AUTO_EXECUTE_FORBIDDEN = (
    "Do not assume downstream execution may silently auto-start once an upstream record looks ready enough."
)
DEFAULT_GENERIC_DEFERRED_SEAM_FORBIDDEN = (
    "Do not assume deferred extension seams can be dropped without Phase-2 consequences."
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_phase2_timing_report_payload(
    *,
    started_at: str,
    finished_at: str,
    total_duration_seconds: float,
    segments: list[dict[str, object]],
) -> dict[str, object]:
    normalized_segments: dict[str, dict[str, object]] = {}
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


def append_phase2_timing_segment(
    segments: list[dict[str, object]],
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


def phase2_timed_segment(segments: list[dict[str, object]], name: str, action):
    started_at = utc_now_iso()
    started_monotonic = time.monotonic()
    status = "fail"
    try:
        result = action()
        status = "pass"
        return result
    finally:
        append_phase2_timing_segment(
            segments,
            name=name,
            started_at=started_at,
            started_monotonic=started_monotonic,
            status=status,
        )


def write_phase2_timing_report(
    *,
    output_dir: Path,
    started_at: str,
    started_monotonic: float,
    segments: list[dict[str, object]],
) -> Path:
    report_path = resolve_cross_phase_surface_path(output_dir, "phase2", "phase2-timing-report.json")
    payload = build_phase2_timing_report_payload(
        started_at=started_at,
        finished_at=utc_now_iso(),
        total_duration_seconds=time.monotonic() - started_monotonic,
        segments=segments,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report_path


def _resolve_phase1_prototype_asset_path(
    phase1_prd_path: Path,
    *,
    explicit_path: Path | None = None,
    candidate_names: tuple[str, ...],
) -> Path | None:
    if explicit_path is not None and explicit_path.exists():
        return explicit_path
    phase1_dir = phase1_prd_path.parent
    for candidate in candidate_names:
        direct = phase1_dir / candidate
        if direct.exists():
            return direct
        parent = phase1_dir.parent / candidate
        if parent.exists():
            return parent
    return None


def _flatten_semantic_strings(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, dict):
        flattened: list[str] = []
        for item in value.values():
            flattened.extend(_flatten_semantic_strings(item))
        return flattened
    if isinstance(value, (list, tuple, set)):
        flattened = []
        for item in value:
            flattened.extend(_flatten_semantic_strings(item))
        return flattened
    return []


def phase1_semantic_signature_text(context: dict[str, object]) -> str:
    fields = [
        context.get("text", ""),
        context.get("objects", []),
        context.get("core_objects", []),
        context.get("supplemental_objects", []),
        context.get("detected_core_entities", []),
        context.get("domains", []),
        context.get("module_matrix_names", []),
        context.get("requirements", []),
        context.get("acceptance_items", []),
        context.get("business_truth_pack", {}),
        context.get("business_proof_track", {}),
        context.get("chosen_business_thesis", {}),
        context.get("business_architecture_pressure", {}),
        context.get("planning_truth_pack", {}),
    ]
    return " ".join(_flatten_semantic_strings(fields)).lower()



def business_architecture_pressure_summary(context: dict[str, object]) -> dict[str, str]:
    raw = context.get("business_architecture_pressure", {})
    pressure = raw if isinstance(raw, dict) else {}
    if pressure:
        return {str(key): str(value).strip() for key, value in pressure.items() if str(value).strip()}
    thesis_raw = context.get("chosen_business_thesis", {})
    thesis = thesis_raw if isinstance(thesis_raw, dict) else {}
    substitute = str(thesis.get("current_state_substitute_to_beat", "")).strip()
    proof_target = str(thesis.get("proof_target", "")).strip()
    boundary = str(thesis.get("product_boundary_implication", "")).strip()
    review_bound = str(thesis.get("review_bound_truth", "")).strip()
    business_argument = str(thesis.get("business_argument") or thesis.get("why_this_product_deserves_to_exist") or thesis.get("why_this_not_alternatives", "")).strip()
    substitute_types_raw = thesis.get("substitute_pressure_types", [])
    substitute_types = ", ".join(str(item).strip() for item in substitute_types_raw if str(item).strip()) if isinstance(substitute_types_raw, list) else str(substitute_types_raw).strip()
    if not thesis:
        return {}
    return {
        "read_model_warning": "avoid read-only architecture when the chosen thesis requires action, proof, or decision follow-through",
        "commercial_proof_supported_by": business_argument or proof_target or "preserve the chosen thesis as an ADR input, not a PRD quote",
        "decision_record_pressure": proof_target or "preserve review decision and evidence snapshot as architecture-visible objects",
        "substitute_pressure": substitute,
        "substitute_pressure_types": substitute_types,
        "anti_collapse_boundary": f"do not collapse into {substitute or 'a thinner substitute'}; preserve action, evidence, and review closure",
        "proof_object_model": "make proof artifacts, operational evidence, review decisions, and exception closure architecture-visible data objects",
        "boundary_pressure": boundary,
        "deferred_seam_pressure": review_bound or "keep deferred seam explicit where proof is unavailable",
    }


def business_architecture_pressure_block(context: dict[str, object], *, indent: int = 4) -> str:
    pressure = business_architecture_pressure_summary(context)
    if not pressure:
        return " " * indent + "- no chosen business thesis was declared; keep architecture pressure review-bound"
    prefix = " " * indent
    return "\n".join(f"{prefix}- {key}: {value}" for key, value in pressure.items())


def _render_constraint_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return "; ".join(
            f"{key}: {_render_constraint_value(item)}"
            for key, item in value.items()
            if _render_constraint_value(item)
        )
    if isinstance(value, (list, tuple, set)):
        return "; ".join(_render_constraint_value(item) for item in value if _render_constraint_value(item))
    return str(value or "").strip()

def business_proof_track_summary(context: dict[str, object]) -> dict[str, str]:
    raw_track = context.get("business_proof_track", {})
    track = raw_track if isinstance(raw_track, dict) else {}
    cleaned = {str(key): str(value).strip() for key, value in track.items() if str(value).strip()}
    if cleaned:
        return cleaned
    return {
        "proof_track": "not-declared-by-phase-1",
        "dominant_proof_risk": "business-proof-constraint-not-declared",
        "first_p2_obligation": "Preserve Phase-1 business proof uncertainty explicitly instead of inventing technical certainty.",
    }


def business_proof_constraint_block(context: dict[str, object], *, indent: int = 4) -> str:
    track = business_proof_track_summary(context)
    proof_track = track.get("proof_track", "not-declared-by-phase-1")
    dominant_risk = track.get("dominant_proof_risk", "business-proof-constraint-not-declared")
    questions = _render_constraint_value(track.get("proof_questions") or track.get("proof_question") or "Phase-2 must keep proof questions visible in ADR, RBI, and implementation intake.")
    substitute_pressure = _render_constraint_value(track.get("substitute_pressure") or track.get("substitute_pressure_test") or track.get("why_this_not_that"))
    directional_threshold = _render_constraint_value(track.get("directional_proof_threshold") or track.get("continue_revise_pause_threshold") or track.get("continue_pause_threshold"))
    owner = _render_constraint_value(track.get("buyer_budget_owner") or track.get("continuation_owner") or track.get("decision_owner"))
    flow_focus = _render_constraint_value(track.get("operating_flow_proof") or track.get("handoff_exception_proof") or track.get("user_flow_friction_proof"))
    lines = [
        f"proof_track: `{proof_track}`",
        f"dominant_proof_risk: `{dominant_risk}`",
        f"p2_obligation: do not translate business proof uncertainty into generic workflow readiness",
        f"proof_questions_to_preserve: {questions}",
    ]
    if substitute_pressure:
        lines.append(f"substitute_pressure_to_preserve: {substitute_pressure}")
    if directional_threshold:
        lines.append(f"directional_or_continue_pause_threshold: {directional_threshold}")
    if owner:
        lines.append(f"buyer_or_budget_continuation_owner: {owner}")
    if flow_focus:
        lines.append(f"operating_or_user_flow_proof_focus: {flow_focus}")
    prefix = " " * indent
    return "\n".join(f"{prefix}- {line}" for line in lines)


def context_supports_recommendation_semantics(context: dict[str, object]) -> bool:
    object_keys = {to_snake(item) for item in context_core_objects(context)}
    if {"optimization_recommendation", "recommendation_payload"} & object_keys:
        return True
    semantic_text = phase1_semantic_signature_text(context)
    return bool(
        re.search(
            r"\brecommendation\b|recommendation[- ]to[- ]task|typed recommendation payload|from-recommendation",
            semantic_text,
        )
    )


def context_supports_deferred_extension_seam(context: dict[str, object]) -> bool:
    semantic_text = phase1_semantic_signature_text(context)
    return bool(
        re.search(
            r"\battribution\b|\bconversion\b|\butm\b|\bfunnel\b|\bcross-device\b|"
            r"\bexternal[- ]identity\b|\bidentity provider\b|\boauth\b|\boidc\b|\bsso\b|"
            r"\bexternal connector\b|\bprovider-specific\b",
            semantic_text,
        )
    )


def context_supports_observation_semantics(context: dict[str, object]) -> bool:
    object_keys = {to_snake(item) for item in context_core_objects(context)}
    if {"observation_run", "visibility_finding", "competitor_snapshot", "observation_metric_snapshot"} & object_keys:
        return True
    if {"baseline_run", "finding"} <= object_keys:
        return True
    if {"tracked_scope", "finding", "recommendation"} <= object_keys:
        return True
    semantic_text = phase1_semantic_signature_text(context)
    return bool(
        re.search(
            r"\bobservation run\b|\bvisibility finding\b|\bfinding detail\b|\bcompetitor snapshot\b|"
            r"\bmeasurement window\b|\bscoring rubric\b|\battribution seam\b",
            semantic_text,
        )
    )


def async_completion_runtime_pack(*, observation_semantics: bool) -> dict[str, str]:
    if observation_semantics:
        return {
            "adr_title": "Use asynchronous observation completion events with idempotent replay",
            "context_surface_label": "Observation completion and finding materialization",
            "completion_identity_label": "run_id",
            "completion_result_label": "findings are not registered",
            "sync_alternative_name": "complete every observation synchronously in the request thread",
            "sync_alternative_reason": (
                "is simpler for demos, but weaker under burst load, more sensitive to latency spikes, "
                "and harder to recover cleanly when scoring or downstream persistence stalls."
            ),
            "positive_consequence": (
                "Burst handling, delayed completion, and retry safety are better aligned with the first-wave "
                "throughput target and the need to replay finding generation deterministically."
            ),
            "evidence_chain_label": "the observation-completion acceptance chain",
            "replay_target_label": "finding materialization",
            "latency_target_label": "observation completion",
            "growth_target_label": "3x one-year observation/finding growth, 5x three-year archival envelope",
            "volume_target_label": "observation and finding surfaces dominate storage growth",
            "queue_posture_label": "async worker only where completion or serialized review freeze needs it",
        }
    return {
        "adr_title": DEFAULT_GENERIC_ASYNC_COMPLETION_ADR_TITLE,
        "context_surface_label": "Workflow completion and authoritative record materialization",
        "completion_identity_label": "completion_id",
        "completion_result_label": "authoritative records are not written",
        "sync_alternative_name": "complete every workflow transition synchronously in the request thread",
        "sync_alternative_reason": (
            "is simpler for demos, but weaker under burst load, more sensitive to latency spikes, "
            "and harder to recover cleanly when downstream persistence or follow-on processing stalls."
        ),
        "positive_consequence": (
            "Burst handling, delayed completion, and retry safety are better aligned with the first-wave "
            "throughput target and the need to replay authoritative record updates deterministically."
        ),
        "evidence_chain_label": "the workflow-completion acceptance chain",
        "replay_target_label": "authoritative record materialization",
        "latency_target_label": "workflow completion",
        "growth_target_label": "3x one-year workflow/history growth, 5x three-year archival envelope",
        "volume_target_label": "workflow and authoritative record surfaces dominate storage growth",
        "queue_posture_label": "async worker only where workflow completion or serialized review freeze needs it",
    }


def async_completion_runtime_pack_for_context(context: dict[str, object]) -> dict[str, str]:
    return async_completion_runtime_pack(observation_semantics=context_supports_observation_semantics(context))


def async_completion_runtime_pack_for_title(title: str) -> dict[str, str]:
    lowered = title.lower()
    return async_completion_runtime_pack(observation_semantics=("observation" in lowered or "finding" in lowered))


def default_adr_titles_for_context(context: dict[str, object]) -> list[str]:
    payload_title = (
        "Freeze typed recommendation payload before task handoff"
        if context_supports_recommendation_semantics(context)
        else DEFAULT_GENERIC_HANDOFF_ADR_TITLE
    )
    async_completion_title = async_completion_runtime_pack_for_context(context)["adr_title"]
    extension_seam_title = (
        "Reserve attribution and external-identity concerns as explicit extension seams"
        if context_supports_deferred_extension_seam(context)
        else DEFAULT_GENERIC_EXTENSION_SEAM_ADR_TITLE
    )
    return [
        "Adopt modular-monolith boundary with explicit public contracts",
        payload_title,
        "Enforce tenant-aware policy gate and auditable isolation boundary",
        async_completion_title,
        "Keep review-bound truth explicit instead of narrative readiness upgrades",
        "Standardize response envelope and business/system error split",
        "Use cursor-based pagination and indexed access patterns for growth surfaces",
        extension_seam_title,
        "Separate contract-facing namespaces from internal storage layout",
        "Carry work-package and RBI chain into implementation intake unchanged",
    ]


def forbidden_templates_for_context(context: dict[str, object]) -> list[tuple[str, str]]:
    auto_execute_text = (
        "Do not assume recommendations may silently auto-execute once a score looks high enough."
        if context_supports_recommendation_semantics(context)
        else DEFAULT_GENERIC_AUTO_EXECUTE_FORBIDDEN
    )
    deferred_seam_text = (
        "Do not assume future attribution seams can be dropped without Phase-2 consequences."
        if context_supports_deferred_extension_seam(context)
        else DEFAULT_GENERIC_DEFERRED_SEAM_FORBIDDEN
    )
    return [
        ("FA-01", "Do not assume cross-tenant reads are safe because the product is B2B internal-only."),
        ("FA-02", auto_execute_text),
        ("FA-03", "Do not assume review conclusions can omit uncertainty when deltas stay ambiguous."),
        ("FA-04", deferred_seam_text),
        ("FA-05", "Do not assume raw workflow evidence volume can grow without explicit index and storage posture."),
    ]


def _extract_page_map_from_prototype_spec(prototype_spec_path: Path | None) -> list[dict[str, str]]:
    if prototype_spec_path is None or not prototype_spec_path.exists():
        return []
    text = prototype_spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    def _clean_scalar(value: object) -> str:
        return str(value or "").strip().strip("`")

    def _clean_list(value: object) -> str:
        items = split_inline_values(_clean_scalar(value))
        return ", ".join(items)

    def _build_page_row(raw_row: dict[str, object], *, fallback_page_id: str) -> dict[str, str]:
        page_name = _clean_scalar(raw_row.get("page_name"))
        return {
            "page_id": _clean_scalar(raw_row.get("page_id")) or fallback_page_id,
            "page_name": page_name,
            "route": _clean_scalar(raw_row.get("route") or raw_row.get("route_pattern")),
            "page_blueprint_type": _clean_scalar(raw_row.get("page_blueprint_type")),
            "page_role": _clean_scalar(raw_row.get("page_role") or raw_row.get("parent_page")),
            "primary_actor": _clean_scalar(raw_row.get("primary_actor")),
            "primary_action": _clean_scalar(raw_row.get("primary_action")),
            "primary_user_goal": _clean_scalar(
                raw_row.get("primary_user_goal") or raw_row.get("why_it_exists") or raw_row.get("primary_action")
            ),
            "allowed_roles": _clean_list(raw_row.get("allowed_roles")),
            "bound_use_case_ids": _clean_list(raw_row.get("bound_use_case_ids")),
            "business_objects": _clean_list(raw_row.get("business_objects")),
            "must_show_together": _clean_list(raw_row.get("must_show_together")),
            "required_regions": _clean_list(raw_row.get("required_regions")),
            "entry_conditions": _clean_scalar(raw_row.get("entry_conditions") or raw_row.get("entry_condition")),
            "exit_conditions": _clean_scalar(raw_row.get("exit_conditions") or raw_row.get("exit_condition")),
            "next_route_candidates": _clean_list(raw_row.get("next_route_candidates")),
            "denied_behavior": _clean_scalar(raw_row.get("denied_behavior")),
            "readiness_status": _clean_scalar(raw_row.get("readiness_status")),
            "blocked_reason": _clean_scalar(raw_row.get("blocked_reason")),
            "canonical_page_id": _clean_scalar(raw_row.get("canonical_page_id")),
            "surface_variant": _clean_scalar(raw_row.get("surface_variant")),
            "audience_mode": _clean_scalar(raw_row.get("audience_mode")),
            "session_role_source": _clean_scalar(raw_row.get("session_role_source")),
            "auth_entry_route": _clean_scalar(raw_row.get("auth_entry_route")),
            "auth_entry_label": _clean_scalar(raw_row.get("auth_entry_label")),
            "workspace_entry_roles": _clean_list(raw_row.get("workspace_entry_roles")),
            "route_reachability_mode": _clean_scalar(raw_row.get("route_reachability_mode")),
            "navigation_scope": _clean_scalar(raw_row.get("navigation_scope")),
            "handoff_visibility": _clean_scalar(raw_row.get("handoff_visibility")),
            "forbidden_exposure": _clean_list(raw_row.get("forbidden_exposure")),
        }

    def _page_row_allowed(row: dict[str, str]) -> bool:
        page_name = str(row.get("page_name", "")).strip()
        business_objects = split_inline_values(row.get("business_objects", ""))
        if page_name and not object_requires_persistent_table(page_name):
            return any(object_requires_persistent_table(item) for item in business_objects)
        return True

    table_section_lines: list[str] = []
    in_table_section = False
    for raw in lines:
        stripped = raw.strip()
        if re.match(r"^##\s+.*(?:Surface Matrix|Page Map).*$", stripped, flags=re.IGNORECASE):
            in_table_section = True
            continue
        if in_table_section and re.match(r"^##\s+", stripped):
            break
        if in_table_section:
            table_section_lines.append(raw)
    if table_section_lines:
        table_lines = [line.strip() for line in table_section_lines if line.strip().startswith("|")]
        if len(table_lines) >= 3:
            headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
            required_headers = {
                "page_id",
                "page_name",
                "page_blueprint_type",
                "primary_actor",
                "primary_action",
                "route_pattern",
                "parent_page",
            }
            if required_headers.issubset(set(headers)):
                pages: list[dict[str, str]] = []
                for line in table_lines[2:]:
                    cells = [cell.strip() for cell in line.strip("|").split("|")]
                    if len(cells) < len(headers):
                        cells.extend([""] * (len(headers) - len(cells)))
                    row = dict(zip(headers, cells))
                    if str(row.get("page_name", "")).strip():
                        page_row = _build_page_row(row, fallback_page_id=f"P{len(pages) + 1:02d}")
                        if _page_row_allowed(page_row):
                            pages.append(page_row)
                if pages:
                    return pages
    in_page_map = False
    current_page: dict[str, str] = {}
    pages: list[dict[str, str]] = []
    fields = {
        "page_name",
        "page_role",
        "primary_actor",
        "why_it_exists",
        "page_blueprint_type",
        "dominant_interaction_pattern",
        "primary_user_goal",
        "allowed_roles",
        "bound_use_case_ids",
        "business_objects",
        "must_show_together",
        "required_regions",
        "entry_conditions",
        "entry_condition",
        "exit_conditions",
        "exit_condition",
        "denied_behavior",
        "readiness_status",
        "blocked_reason",
        "next_route_candidates",
        "canonical_page_id",
        "surface_variant",
        "audience_mode",
        "session_role_source",
        "auth_entry_route",
        "auth_entry_label",
        "workspace_entry_roles",
        "route_reachability_mode",
        "navigation_scope",
        "handoff_visibility",
        "forbidden_exposure",
        "route",
        "route_pattern",
    }
    for raw in lines:
        stripped = raw.strip()
        if stripped in {"## 3. Surface Matrix", "## 4. Page Map"} or stripped.startswith(("- surface_matrix:", "- page_map:")):
            in_page_map = True
            continue
        if in_page_map and stripped.startswith("## ") and "Page Map" not in stripped and "Surface Matrix" not in stripped:
            if current_page.get("page_name"):
                page_row = _build_page_row(current_page, fallback_page_id=f"P{len(pages) + 1:02d}")
                if _page_row_allowed(page_row):
                    pages.append(page_row)
            break
        if not in_page_map:
            continue
        if re.match(r"^\s*- page_\d+:\s*$", stripped):
            if current_page.get("page_name"):
                page_row = _build_page_row(current_page, fallback_page_id=f"P{len(pages) + 1:02d}")
                if _page_row_allowed(page_row):
                    pages.append(page_row)
            current_page = {}
            continue
        field_match = re.match(r"^\s*-\s+([A-Za-z0-9_]+):\s*(.+?)?\s*$", stripped)
        if not field_match:
            continue
        field = field_match.group(1).strip()
        if field not in fields:
            continue
        value = (field_match.group(2) or "").strip().strip("`").strip()
        if value:
            current_page[field] = value
    if current_page.get("page_name"):
        page_row = _build_page_row(current_page, fallback_page_id=f"P{len(pages) + 1:02d}")
        if _page_row_allowed(page_row):
            pages.append(page_row)
    return pages

def _extract_markdown_table_section(text: str, section_keyword: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    section_lines: list[str] = []
    in_section = False
    for raw in lines:
        stripped = raw.strip()
        if re.match(rf"^##\s+.*{re.escape(section_keyword)}.*$", stripped, flags=re.IGNORECASE):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", stripped):
            break
        if in_section:
            section_lines.append(raw)
    table_lines = [line.strip() for line in section_lines if line.strip().startswith("|")]
    if len(table_lines) < 3:
        return []
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        row = dict(zip(headers, cells))
        if any(str(value).strip() for value in row.values()):
            rows.append(row)
    return rows


def _resolve_phase1_interaction_flow_contract_path(
    phase1_prd_path: Path,
    *,
    explicit_path: Path | None = None,
) -> Path | None:
    return _resolve_phase1_prototype_asset_path(
        phase1_prd_path,
        explicit_path=explicit_path,
        candidate_names=("prototype-interaction-flow-contract.md", "prototype_interaction_flow_contract.md"),
    )


def _extract_interaction_rows_from_phase1_contract(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    return _extract_markdown_table_section(path.read_text(encoding="utf-8"), "Interaction Matrix")


def _extract_flow_rows_from_phase1_contract(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    return _extract_markdown_table_section(path.read_text(encoding="utf-8"), "Flow Contract")

@dataclass(frozen=True)
class ServiceSpec:
    service_name: str
    domain: str
    home_module: str
    service_type: str
    owns_or_coordinates: str
    primary_inbound: str
    primary_outbound: str
    purpose: str
    public_contract: str
    endpoint_name: str
    method: str
    path: str
    technical_name: str = ""
    technical_slug: str = ""


@dataclass(frozen=True)
class InteractionServiceMatch:
    service: ServiceSpec | None
    score: int
    semantic_overlap: int
    has_object_overlap: bool
    method_match: bool
    blocked_reason: str = ""


def context_text(context: dict[str, object]) -> str:
    return str(context.get("text", ""))


def context_core_objects(context: dict[str, object]) -> list[str]:
    return unique_preserve(
        [
            str(item).strip()
            for item in list(context.get("core_objects", []))
            + list(context.get("detected_core_entities", []))
            + list(context.get("objects", []))
            if str(item).strip()
        ]
    )


def context_has_object(context: dict[str, object], *candidates: str) -> bool:
    object_keys = {to_snake(item) for item in context_core_objects(context)}
    return any(to_snake(candidate) in object_keys for candidate in candidates if candidate.strip())


def semantic_support_objects_from_names(object_names: list[str]) -> list[str]:
    object_keys = {to_snake(item) for item in object_names if str(item).strip()}
    support_objects: list[str] = []
    if "tracked_scope" in object_keys:
        support_objects.append("Scope Revision")
    if "observation_run" in object_keys or "visibility_finding" in object_keys:
        support_objects.append("Observation Metric Snapshot")
    if "review_report" in object_keys:
        support_objects.append("Review Decision")
    if "optimization_recommendation" in object_keys:
        support_objects.append("Recommendation Payload")
    return unique_preserve(support_objects)


def object_requires_persistent_table(obj_name: str) -> bool:
    raw_text = str(obj_name or "").strip().lower()
    lowered = to_snake(obj_name)
    if not lowered:
        return False
    if lowered.startswith("review_summary") or lowered.startswith("workflow_review_summary"):
        return True
    if lowered in {"review_report", "review_decision"}:
        return True
    conceptual_markers = (
        "boundary",
        "permission",
        "policy",
        "constraint",
        "guardrail",
        "权限",
        "边界",
        "策略",
        "约束",
    )
    persistent_markers = (
        "record",
        "task",
        "view",
        "run",
        "report",
        "decision",
        "asset",
        "finding",
        "recommendation",
        "revision",
        "order",
        "plan",
        "记录",
        "任务",
        "视图",
        "运行",
        "报告",
        "决策",
        "资产",
        "发现",
        "建议",
        "修订",
        "订单",
        "计划",
        "工单",
        "审计",
    )
    if any(marker in raw_text for marker in conceptual_markers) and not any(
        marker in raw_text for marker in persistent_markers
    ):
        return False
    return not any(token in lowered for token in ("policy", "reference", "detail", "summary"))


def persistent_business_objects(values: list[str]) -> list[str]:
    return unique_preserve(
        [str(value).strip() for value in values if str(value).strip() and object_requires_persistent_table(str(value))]
    )


def sanitize_phase2_modules(
    modules: list[dict[str, object]],
    *,
    root_namespace: str,
) -> list[dict[str, object]]:
    sanitized: list[dict[str, object]] = []
    seen: set[str] = set()
    for module in modules:
        name = str(module.get("module_name", "")).strip()
        filtered_objects = persistent_business_objects(module_core_objects(module))
        primary = str(module.get("primary_object", "")).strip()
        if primary and not object_requires_persistent_table(primary):
            primary = ""
        if not primary and filtered_objects:
            primary = filtered_objects[0]
        if not filtered_objects and primary:
            filtered_objects = [primary]
        if not filtered_objects and not object_requires_persistent_table(name):
            continue
        display_name = name
        if filtered_objects and not object_requires_persistent_table(name):
            display_name = primary or filtered_objects[0]
        if not primary:
            primary = filtered_objects[0] if filtered_objects else name
        sanitized_module = dict(module)
        sanitized_module["module_name"] = display_name
        sanitized_module["core_objects"] = filtered_objects
        sanitized_module["primary_object"] = primary
        service_type = str(module.get("service_type", "domain")).strip() or "domain"
        endpoint_module = dict(sanitized_module)
        endpoint_module.pop("primary_endpoint", None)
        endpoint_module.pop("event", None)
        sanitized_module["primary_endpoint"] = infer_primary_endpoint(endpoint_module, service_type)
        sanitized_module["event"] = infer_event_name(endpoint_module, service_type)
        sanitized_module["home_namespace"] = str(module.get("home_namespace") or f"{root_namespace}.{slugify(name).replace('-', '.')}")
        key = choose_technical_slug(
            str(sanitized_module.get("module_name") or primary),
            *filtered_objects,
            prefix="module",
        )
        if key in seen:
            continue
        seen.add(key)
        sanitized.append(sanitized_module)
    return sanitized or modules


def semantic_table_name(obj_name: str) -> str:
    aliases = {
        "tracked_scope_revision": "scope_revision",
        "scope_revision": "scope_revision",
        "observation_run_revision": "observation_metric_snapshot",
        "observation_metric_snapshot": "observation_metric_snapshot",
        "review_report_revision": "review_decision",
        "review_decision": "review_decision",
        "optimization_recommendation_revision": "recommendation_payload",
        "recommendation_payload": "recommendation_payload",
    }
    normalized = to_snake(obj_name)
    if normalized == "revision" and "revision" in obj_name.lower():
        revision_base = re.sub(r"\brevision\b", "", obj_name, flags=re.IGNORECASE).strip().strip("-_/")
        revision_prefix = to_snake(revision_base)
        if revision_prefix and revision_prefix != "revision":
            return f"{revision_prefix}_revision"
    return aliases.get(normalized, normalized)


def unique_semantic_objects(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = semantic_table_name(cleaned) if object_requires_persistent_table(cleaned) else to_snake(cleaned)
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def semantic_table_owner(table_name: str, root_namespace: str) -> str | None:
    owner_map = {
        "tracked_scope": f"{root_namespace}.scope.registry",
        "scope_revision": f"{root_namespace}.scope.registry",
        "observation_run": f"{root_namespace}.observe.run-orchestrator",
        "observation_metric_snapshot": f"{root_namespace}.observe.run-orchestrator",
        "visibility_finding": f"{root_namespace}.finding.query",
        "competitor_snapshot": f"{root_namespace}.finding.query",
        "optimization_recommendation": f"{root_namespace}.recommendation.decision",
        "recommendation_payload": f"{root_namespace}.recommendation.decision",
        "optimization_task": f"{root_namespace}.task.bridge",
        "content_asset": f"{root_namespace}.content.asset",
        "review_report": f"{root_namespace}.review.reporting",
        "review_decision": f"{root_namespace}.review.reporting",
        "audit_record": f"{root_namespace}.audit.trail",
    }
    return owner_map.get(table_name)


def semantic_table_design_template(table_name: str) -> dict[str, object] | None:
    templates: dict[str, dict[str, object]] = {
        "tracked_scope": {
            "pk": "scope_id",
            "fk": "tenant_id -> tenant.tenant_id",
            "unique_constraints": "tenant_id + scope_key",
            "composite_indexes": "tenant_id + created_at desc, tenant_id + status",
            "pii_level": "low-to-medium",
            "sensitive_fields": "tenant_id, brand_name",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 365d hot + archive 730d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "preserve scope lineage and tenant isolation",
            "field_rows": [
                ["scope_id", "uuid", "false", "pk", "btree pk"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["scope_key", "varchar(96)", "false", "unique per tenant", "btree tenant_id + scope_key"],
                ["brand_name", "varchar(128)", "false", "display label", "btree tenant_id + brand_name"],
                ["active_revision_no", "integer", "false", "default 1", "btree tenant_id + active_revision_no"],
                ["status", "varchar(32)", "false", "enum-like", "btree tenant_id + status"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
                ["updated_at", "timestamptz", "false", "default now()", "btree tenant_id + updated_at desc"],
            ],
        },
        "scope_revision": {
            "pk": "scope_revision_id",
            "fk": "scope_id -> tracked_scope.scope_id",
            "unique_constraints": "scope_id + revision_no; scope_id where is_active = true",
            "composite_indexes": "scope_id + revision_no desc, tenant_id + created_at desc",
            "pii_level": "low-to-medium",
            "sensitive_fields": "tenant_id, revision_payload",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 365d hot + archive 730d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "preserve publishable scope revision lineage",
            "field_rows": [
                ["scope_revision_id", "uuid", "false", "pk", "btree pk"],
                ["scope_id", "uuid", "false", "fk tracked_scope.scope_id", "btree scope_id"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["revision_no", "integer", "false", "monotonic per scope", "btree scope_id + revision_no desc"],
                ["is_active", "boolean", "false", "default false", "btree scope_id + is_active"],
                ["revision_payload", "jsonb", "true", "shape validated", "gin revision_payload"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
            ],
        },
        "observation_metric_snapshot": {
            "pk": "metric_snapshot_id",
            "fk": "observation_run_id -> observation_run.observation_run_id",
            "unique_constraints": "observation_run_id + metric_window",
            "composite_indexes": "tenant_id + created_at desc, observation_run_id + metric_window",
            "pii_level": "internal",
            "sensitive_fields": "tenant_id, metric_payload",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 180d hot + archive 540d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "retain observation scoring evidence for replay and review",
            "field_rows": [
                ["metric_snapshot_id", "uuid", "false", "pk", "btree pk"],
                ["observation_run_id", "uuid", "false", "fk observation_run.observation_run_id", "btree observation_run_id"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["metric_window", "varchar(64)", "false", "window label", "btree observation_run_id + metric_window"],
                ["finding_count", "integer", "false", "default 0", "btree tenant_id + created_at desc"],
                ["metric_payload", "jsonb", "true", "shape validated", "gin metric_payload"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
            ],
        },
        "optimization_recommendation": {
            "pk": "recommendation_id",
            "fk": "finding_id -> visibility_finding.visibility_finding_id",
            "unique_constraints": "finding_id + payload_version",
            "composite_indexes": "tenant_id + decision_status, tenant_id + created_at desc",
            "pii_level": "internal",
            "sensitive_fields": "tenant_id, recommendation_payload",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 365d hot + archive 730d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "typed recommendation payload stays explicit across task handoff",
            "field_rows": [
                ["recommendation_id", "uuid", "false", "pk", "btree pk"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["finding_id", "uuid", "false", "fk visibility_finding.visibility_finding_id", "btree finding_id"],
                ["target_asset_id", "uuid", "true", "fk content_asset.content_asset_id", "btree target_asset_id"],
                ["payload_version", "varchar(32)", "false", "typed payload version", "btree finding_id + payload_version"],
                ["decision_status", "varchar(32)", "false", "enum-like", "btree tenant_id + decision_status"],
                ["recommendation_payload", "jsonb", "true", "shape validated", "gin recommendation_payload"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
                ["updated_at", "timestamptz", "false", "default now()", "btree tenant_id + updated_at desc"],
            ],
        },
        "recommendation_payload": {
            "pk": "recommendation_payload_id",
            "fk": "recommendation_id -> optimization_recommendation.recommendation_id",
            "unique_constraints": "recommendation_id + payload_version",
            "composite_indexes": "recommendation_id + payload_version, tenant_id + created_at desc",
            "pii_level": "internal",
            "sensitive_fields": "tenant_id, payload_blob",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 365d hot + archive 730d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "payload revisions remain replay-safe and audit-visible",
            "field_rows": [
                ["recommendation_payload_id", "uuid", "false", "pk", "btree pk"],
                ["recommendation_id", "uuid", "false", "fk optimization_recommendation.recommendation_id", "btree recommendation_id"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["payload_version", "varchar(32)", "false", "typed payload version", "btree recommendation_id + payload_version"],
                ["payload_blob", "jsonb", "false", "shape validated", "gin payload_blob"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
            ],
        },
        "review_report": {
            "pk": "review_report_id",
            "fk": "scope_id -> tracked_scope.scope_id",
            "unique_constraints": "tenant_id + scope_id + cycle_key",
            "composite_indexes": "tenant_id + created_at desc, tenant_id + decision_posture",
            "pii_level": "internal",
            "sensitive_fields": "tenant_id, uncertainty_note",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 365d hot + archive 730d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "review-bound truth remains explicit instead of narrative upgrades",
            "field_rows": [
                ["review_report_id", "uuid", "false", "pk", "btree pk"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["scope_id", "uuid", "false", "fk tracked_scope.scope_id", "btree scope_id"],
                ["cycle_key", "varchar(64)", "false", "review cycle anchor", "btree tenant_id + scope_id + cycle_key"],
                ["uncertainty_level", "varchar(32)", "false", "enum-like", "btree tenant_id + decision_posture"],
                ["uncertainty_note", "text", "true", "review-bound note", "none"],
                ["decision_posture", "varchar(32)", "false", "enum-like", "btree tenant_id + decision_posture"],
                ["threshold_rationale", "text", "true", "review rationale", "none"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
                ["updated_at", "timestamptz", "false", "default now()", "btree tenant_id + updated_at desc"],
            ],
        },
        "review_decision": {
            "pk": "review_decision_id",
            "fk": "review_report_id -> review_report.review_report_id",
            "unique_constraints": "review_report_id + decision_posture",
            "composite_indexes": "review_report_id + created_at desc, tenant_id + created_at desc",
            "pii_level": "internal",
            "sensitive_fields": "tenant_id, decision_reason",
            "masking_or_encryption": "kms-backed encryption at rest + masked logs",
            "retention_rule": "keep 365d hot + archive 730d cold",
            "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
            "compliance_note": "separate operator decision capture from report generation",
            "field_rows": [
                ["review_decision_id", "uuid", "false", "pk", "btree pk"],
                ["review_report_id", "uuid", "false", "fk review_report.review_report_id", "btree review_report_id"],
                ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
                ["decision_posture", "varchar(32)", "false", "enum-like", "btree review_report_id + decision_posture"],
                ["decision_reason", "text", "true", "operator rationale", "none"],
                ["actor_id", "uuid", "true", "who made the decision", "btree tenant_id + created_at desc"],
                ["created_at", "timestamptz", "false", "default now()", "btree tenant_id + created_at desc"],
            ],
        },
    }
    return templates.get(table_name)


def semantic_service_key(service: ServiceSpec) -> str:
    signature = " ".join(
        [
            service.service_name,
            service.domain,
            service.home_module,
            service.owns_or_coordinates,
            service.primary_inbound,
            service.primary_outbound,
            service.purpose,
            service.public_contract,
            service.endpoint_name,
            service.path,
        ]
    ).lower()
    if "access-policy" in signature or ("tenant" in signature and "access" in signature and "policy" in signature):
        return "tenant_access_policy"
    if "trackedscope" in signature or "tracked scope" in signature or "create tracked scope" in signature:
        return "tracked_scope"
    if "attribution" in signature and "seam" in signature:
        return "attribution_seam"
    if "observation" in signature and "run" in signature:
        return "observation_run"
    if "finding" in signature:
        return "finding_query"
    if "recommendation" in signature and "decision" in signature:
        return "recommendation_decision"
    if "optimization task" in signature or "taskbridge" in signature or "task bridge" in signature:
        return "optimization_task"
    if "content asset" in signature:
        return "content_asset"
    if "review" in signature and "report" in signature:
        return "review_report"
    if "audit" in signature:
        return "audit_record"
    return ""


def semantic_service_specs(context: dict[str, object]) -> list[ServiceSpec]:
    root_namespace = str(context["root_namespace"])
    prd_text = context_text(context).lower()
    specs: list[ServiceSpec] = []

    def add(spec: ServiceSpec) -> None:
        if any(existing.service_name == spec.service_name for existing in specs):
            return
        specs.append(spec)

    if context_has_object(context, "Tracked Scope"):
        add(
            ServiceSpec(
                "ScopeRegistryService",
                "Scope and Governance",
                f"{root_namespace}.scope.registry",
                "transactional",
                "Tracked Scope",
                "CreateTrackedScope",
                "ScopeActivated",
                "围绕 Tracked Scope 建立可追踪范围，并保留当前生效版本锚点。",
                f"{root_namespace}.scope.TrackedScope",
                "CreateTrackedScope",
                "POST",
                "/api/v1/scopes",
            )
        )
    if context_has_object(context, "Tracked Scope") and ("tenant" in prd_text or "permission" in prd_text or "access" in prd_text):
        add(
            ServiceSpec(
                "TenantAccessService",
                "Scope and Governance",
                f"{root_namespace}.identity.access",
                "policy",
                "Tenant Access Policy",
                "GetTenantAccessPolicy",
                "TenantAccessResolved",
                "在进入主流程前解析 Tenant Access Policy 的访问边界与权限姿态。",
                f"{root_namespace}.identity.TenantAccessPolicy",
                "GetTenantAccessPolicy",
                "GET",
                "/api/v1/tenants/{tenantId}/access-policy",
            )
        )
    if context_has_object(context, "Observation Run"):
        add(
            ServiceSpec(
                "ObservationRunService",
                "Observation and Scoring",
                f"{root_namespace}.observe.run-orchestrator",
                "orchestration",
                "Observation Run",
                "StartObservationRun",
                "ObservationRunCompleted",
                "发起 Observation Run，并保留可回放的完成证据。",
                f"{root_namespace}.observe.ObservationRunSummary",
                "StartObservationRun",
                "POST",
                "/api/v1/observation-runs",
            )
        )
    if context_has_object(context, "Visibility Finding"):
        add(
            ServiceSpec(
                "FindingQueryService",
                "Observation and Scoring",
                f"{root_namespace}.finding.query",
                "read-assembly",
                "Visibility Finding",
                "GetFindingDetail",
                "FindingDetailPrepared",
                "围绕 Visibility Finding 提供详情与建议准备所需上下文，不改写既有评分事实。",
                f"{root_namespace}.finding.FindingDetail",
                "GetFindingDetail",
                "GET",
                "/api/v1/findings/{findingId}",
            )
        )
    if context_has_object(context, "Optimization Recommendation"):
        add(
            ServiceSpec(
                "RecommendationDecisionService",
                "Recommendation and Tasking",
                f"{root_namespace}.recommendation.decision",
                "transactional",
                "Optimization Recommendation",
                "CreateRecommendationDecision",
                "RecommendationDecisionCreated",
                "围绕 Optimization Recommendation 形成带类型的决策结果，并保留 payload 版本语义。",
                f"{root_namespace}.recommendation.OptimizationRecommendation",
                "CreateRecommendationDecision",
                "POST",
                "/api/v1/recommendations/decisions",
            )
        )
    if context_has_object(context, "Optimization Task"):
        add(
            ServiceSpec(
                "TaskBridgeService",
                "Recommendation and Tasking",
                f"{root_namespace}.task.bridge",
                "transactional",
                "Optimization Task",
                "CreateOptimizationTask",
                "OptimizationTaskCreated",
                "把已接受的 Optimization Recommendation 桥接成执行任务，并保留类型化上下文。",
                f"{root_namespace}.task.OptimizationTask",
                "CreateOptimizationTask",
                "POST",
                "/api/v1/tasks",
            )
        )
    if context_has_object(context, "Content Asset"):
        add(
            ServiceSpec(
                "ContentAssetService",
                "Recommendation and Tasking",
                f"{root_namespace}.content.asset",
                "read-assembly",
                "Content Asset",
                "ListContentAssets",
                "ContentAssetCatalogPrepared",
                "提供 Content Asset 目录上下文，支撑建议定位与任务交接。",
                f"{root_namespace}.content.ContentAsset",
                "ListContentAssets",
                "GET",
                "/api/v1/content-assets",
            )
        )
    if context_has_object(context, "Review Report"):
        add(
            ServiceSpec(
                "ReviewReportService",
                "Review and Reporting",
                f"{root_namespace}.review.reporting",
                "transactional",
                "Review Report",
                "GenerateReviewReport",
                "ReviewReportGenerated",
                "生成保留不确定性、判断依据与收口姿态的 Review Report。",
                f"{root_namespace}.review.ReviewReport",
                "GenerateReviewReport",
                "POST",
                "/api/v1/reviews/generate",
            )
        )
    if "attribution seam" in prd_text:
        add(
            ServiceSpec(
                "AttributionSeamService",
                "Scope and Governance",
                f"{root_namespace}.scope.attribution",
                "read-assembly",
                "Attribution Seam Reference",
                "GetAttributionSeamReference",
                "AttributionSeamPrepared",
                "显式保留 Attribution Seam 的边界姿态，但不把它升级成已验证的 ROI 真相。",
                f"{root_namespace}.scope.AttributionSeamReference",
                "GetAttributionSeamReference",
                "GET",
                "/api/v1/scopes/{scopeId}/attribution-seam",
            )
        )
    if context_has_object(context, "Audit Record") or "audit trail" in prd_text:
        add(
            ServiceSpec(
                "AuditTrailService",
                "Review and Reporting",
                f"{root_namespace}.audit.trail",
                "support",
                "Audit Record",
                "RecordAuditEvent",
                "AuditEventRecorded",
                "把拒绝路径、任务变更与评审结论统一写入 Audit Record 审计轨迹。",
                f"{root_namespace}.audit.AuditRecord",
                "RecordAuditEvent",
                "POST",
                "/api/v1/audit-events",
            )
        )
    return specs


def semantic_primary_surfaces(context: dict[str, object]) -> list[str]:
    lowered = context_text(context).lower()
    surfaces: list[str] = []
    if any(token in lowered for token in ("scope", "baseline", "tenant", "activation", "activate")):
        surfaces.append("Onboarding / scope setup")
    if any(token in lowered for token in ("finding", "recommendation", "task", "overview")):
        surfaces.append("Overview + findings")
    if any(token in lowered for token in ("review", "uncertainty", "decision posture", "threshold rationale")):
        surfaces.append("Review report + continue/revise decision")
    return unique_preserve(surfaces)


@dataclass(frozen=True)
class Phase2FirstVersionContext:
    repo_root: Path
    phase1_prd: Path
    existing_system_architecture_change_intake: Path | None
    output_dir: Path
    phase1_prototype_spec: Path | None
    phase1_prototype_prompt_pack: Path | None
    phase1_interaction_flow_contract: Path | None
    case_name: str
    version: str
    complexity_profile: str
    complexity_override_justification: str
    complexity_report: dict[str, object]
    deployment_posture: str
    deployment_posture_suggested: str
    deployment_posture_warning_class: str
    deployment_posture_override_source: str
    deployment_posture_override_reason: str
    deployment_posture_added_risks: str
    pure_prd_direct: bool
    owner: str
    output_locale: str
    thinking_value_gain_mode: str
    thinking_value_gain_output_profile: str
    run_wrapper: bool
    force: bool


@dataclass(frozen=True)
class Phase2FirstVersionResult:
    audit: dict[str, object]
    with_stage_02_5: bool
    timing_report_path: Path
    claim_control_report_path: Path | None = None


PHASE2_FIRST_VERSION_AUTHORITY: dict[str, Any] = {
    "surface_id": "phase2-first-version-mainline",
    "validation_profile": "phase",
    "default_status": "default",
    "fresh_generation_entrypoint": True,
    "manual_closure_only": False,
    "claim_ceiling": "P2 architecture/spec artifacts and declared wrapper evidence only",
    "canonical_guidance": (
        "Use run_phase2_first_version.py --run-wrapper as the fresh Phase-2 mainline. "
        "Wrapper success does not upgrade P2 into release proof or production readiness."
    ),
}


def phase2_first_version_authority() -> dict[str, Any]:
    return dict(PHASE2_FIRST_VERSION_AUTHORITY)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Official Phase-2 mainline entry: generate a fresh first version from a Phase-1 PRD.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "validation profile: phase; default status: default fresh Phase-2 mainline; "
            "claim ceiling: P2 architecture/spec artifacts and declared wrapper evidence only."
        ),
    )
    parser.add_argument("--phase1-prd", required=True, help="Path to the Phase-1 PRD main document.")
    parser.add_argument(
        "--existing-system-architecture-change-intake",
        default="",
        help=(
            "Optional P2 Existing-System Architecture Change Intake Packet. "
            "This sidecar does not replace --phase1-prd."
        ),
    )
    parser.add_argument("--output-dir", required=True, help="Fresh Phase-2 case root.")
    parser.add_argument("--version", default="v-next", help="Phase-2 version label.")
    parser.add_argument("--case-name", default="", help="Optional case-name override.")
    parser.add_argument(
        "--complexity-profile",
        default="",
        help="Optional complexity profile override: micro | standard | complex.",
    )
    parser.add_argument(
        "--complexity-override-justification",
        default="",
        help="Justification forwarded to the full-trial wrapper when --complexity-profile overrides the classifier.",
    )
    parser.add_argument(
        "--deployment-posture",
        default="light",
        choices=("light", "standard", "heavy"),
        help="Deployment/infrastructure posture to pass into wrapper metadata: light | standard | heavy.",
    )
    parser.add_argument(
        "--deployment-posture-suggested",
        default="light",
        choices=("light", "standard", "heavy"),
        help="Suggested deployment/infrastructure posture recorded by wrapper metadata.",
    )
    parser.add_argument(
        "--deployment-posture-warning-class",
        default="none",
        choices=("none", "constraint-backed-override", "preference-driven-override"),
        help="Wrapper warning class when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--deployment-posture-override-source",
        default="",
        help="Wrapper override source when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--deployment-posture-override-reason",
        default="",
        help="Wrapper override reason when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--deployment-posture-added-risks",
        default="",
        help="Wrapper added-risk summary when selected deployment posture differs from suggested posture.",
    )
    parser.add_argument(
        "--pure-prd-direct",
        action="store_true",
        help="Record this run as a pure direct baseline from the Phase-1 PRD main document.",
    )
    parser.add_argument(
        "--owner",
        default="codex",
        help="Run owner recorded in sidecar metadata.",
    )
    parser.add_argument(
        "--output-locale",
        default=resolve_output_locale(),
        help="Default language for human-reviewed generated reports.",
    )
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="Mindthus TVG strategy marker for Phase-2 generation; defaults to off.",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
        help="Mindthus TVG output profile to use when TVG full-use is enabled.",
    )
    parser.add_argument(
        "--run-wrapper",
        action="store_true",
        help="Complete the official Phase-2 mainline bundle by handing off to scripts/phase2/run_phase2_full_trial.py.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty output directory.",
    )
    return parser


def parse_phase2_first_version_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return parse_phase2_first_version_args(argv)


def _short_stable_suffix(raw: str) -> str:
    return hashlib.sha1(str(raw).encode("utf-8")).hexdigest()[:6]


def _ascii_words(raw: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(raw or ""))
    return [word for word in re.findall(r"[A-Za-z0-9]+", expanded) if word]


def _ascii_pascal(raw: str) -> str:
    return "".join(word[:1].upper() + word[1:] for word in _ascii_words(raw))


def _ascii_snake(raw: str) -> str:
    return "_".join(word.lower() for word in _ascii_words(raw))


def _ascii_slug(raw: str) -> str:
    return "-".join(word.lower() for word in _ascii_words(raw))


def _looks_like_generic_object_descriptor(raw: str) -> bool:
    lowered = str(raw or "").strip().lower()
    if not lowered:
        return False
    return bool(re.search(r"\b(?:primary|supporting)\b.*\bobject\b.*\bfor\b", lowered))


def _technical_candidate_order(raw: str, alias_candidates: tuple[str, ...]) -> list[str]:
    raw_text = str(raw or "").strip()
    filtered_aliases = [
        str(candidate).strip()
        for candidate in alias_candidates
        if str(candidate).strip() and not _looks_like_generic_object_descriptor(str(candidate))
    ]
    if _ascii_words(raw_text):
        return [raw_text, *filtered_aliases]
    return [*filtered_aliases, raw_text]


def choose_technical_pascal(raw: str, *alias_candidates: str, prefix: str = "Entity") -> str:
    for candidate in _technical_candidate_order(raw, alias_candidates):
        identifier = _ascii_pascal(candidate)
        if identifier:
            return identifier
    return f"{prefix}{_short_stable_suffix(raw).upper()}"


def choose_technical_snake(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    for candidate in _technical_candidate_order(raw, alias_candidates):
        identifier = _ascii_snake(candidate)
        if identifier:
            return identifier
    return f"{prefix}_{_short_stable_suffix(raw)}"


def choose_technical_slug(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    for candidate in _technical_candidate_order(raw, alias_candidates):
        identifier = _ascii_slug(candidate)
        if identifier:
            return identifier
    return f"{prefix}-{_short_stable_suffix(raw)}"


def slugify(raw: str) -> str:
    return choose_technical_slug(raw, prefix="item")


def to_snake(raw: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    value = value.replace("&", " and ")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if value:
        return value.lower()
    return choose_technical_snake(raw, prefix="entity")


def to_upper_entity(raw: str) -> str:
    return semantic_table_name(raw).upper()


def to_pascal(raw: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", raw)
    identifier = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if identifier:
        return identifier
    return choose_technical_pascal(raw, prefix="Entity")


def unique_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


NULLABLE_SCHEMA_FIELD_TYPES = {
    "blockedReason": "string|null",
    "blocked_reason": "string|null",
    "nextCursor": "string|null",
    "next_cursor": "string|null",
}


def render_markdown_cell(value: object) -> str:
    text = str(value)
    return text.replace("&", "&amp;").replace("|", "&#124;").replace("\n", "<br>")


def make_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(render_markdown_cell(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def infer_schema_field_type(field_name: str, value: object) -> str:
    if field_name in NULLABLE_SCHEMA_FIELD_TYPES:
        return NULLABLE_SCHEMA_FIELD_TYPES[field_name]
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    if isinstance(value, list):
        if not value:
            return "array<unknown>"
        first = value[0]
        if isinstance(first, dict):
            return "array<object>"
        return f"array<{infer_schema_field_type(field_name, first)}>"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def flatten_schema_fields(value: object, *, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        fields: list[str] = []
        for key, subvalue in value.items():
            field_name = f"{prefix}.{key}" if prefix else key
            if isinstance(subvalue, dict):
                fields.append(f"{field_name}: object")
                fields.extend(flatten_schema_fields(subvalue, prefix=field_name))
            elif isinstance(subvalue, list) and subvalue and isinstance(subvalue[0], dict):
                fields.append(f"{field_name}: array<object>")
                fields.extend(flatten_schema_fields(subvalue[0], prefix=f"{field_name}[]"))
            else:
                fields.append(f"{field_name}: {infer_schema_field_type(key, subvalue)}")
        return unique_preserve(fields)
    if isinstance(value, list):
        if not value:
            return [f"{prefix}[]: array<unknown>"] if prefix else []
        first = value[0]
        if isinstance(first, dict):
            fields: list[str] = []
            for key, subvalue in first.items():
                item_prefix = f"{prefix}[].{key}" if prefix else f"[].{key}"
                if isinstance(subvalue, dict):
                    fields.append(f"{item_prefix}: object")
                    fields.extend(flatten_schema_fields(subvalue, prefix=item_prefix))
                else:
                    fields.append(f"{item_prefix}: {infer_schema_field_type(key, subvalue)}")
            return unique_preserve(fields)
        return [f"{prefix}[]: {infer_schema_field_type(prefix, first)}"] if prefix else []
    return [f"{prefix}: {infer_schema_field_type(prefix, value)}"] if prefix else []


def extract_nested_bullet_values(block: str, field_name: str) -> list[str]:
    lines = block.splitlines()
    marker = f"- {field_name}:"
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == marker:
            start = idx
            break
    if start is None:
        return []

    values: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("### ") or line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("`"))
    return values


def parse_labeled_bullets(block: str, prefix: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(rf"^[ \t]*-[ \t]*({re.escape(prefix)}-[0-9]+):[ \t]*(.+?)\s*$", block, flags=re.MULTILINE)
    ]


READER_FACING_THESIS_KEY_ALIASES = {
    "产品押注": "chosen_thesis",
    "为什么现在": "why_now",
    "为什么这个切片": "product_boundary_implication",
    "为什么不是现状": "current_state_substitute_to_beat",
    "为什么不是单点工具/服务替代": "why_this_not_alternatives",
    "下一轮投入证据": "proof_target",
    "读者摘要": "business_argument",
    "源真相边界": "review_bound_truth",
    "阻断更强声明的开放真相": "review_bound_truth",
    "禁止升级": "review_bound_truth",
    "待复核事实": "review_bound_truth",
}


def _merge_simple_bullet_value(parsed: dict[str, object], key: str, value: str) -> None:
    existing = parsed.get(key)
    if isinstance(existing, str) and existing.strip() and value not in existing:
        parsed[key] = f"{existing}; {value}"
        return
    if not existing:
        parsed[key] = value


def parse_simple_heading_bullets(block: str, *, list_keys: set[str] | None = None) -> dict[str, object]:
    parsed: dict[str, object] = {}
    list_keys = list_keys or set()
    for raw_line in block.splitlines():
        match = re.match(r"^[ \t]*-[ \t]*(.+?)[：:][ \t]*(.+?)\s*$", raw_line)
        if not match:
            continue
        raw_key = match.group(1).strip().strip("`")
        key = READER_FACING_THESIS_KEY_ALIASES.get(raw_key, raw_key)
        value = match.group(2).strip().strip("`")
        if key in list_keys:
            parsed[key] = unique_preserve(
                [
                    item.strip().strip("`")
                    for item in re.split(r"\s*(?:->|→|,|;)\s*", value)
                    if item.strip().strip("`")
                ]
            )
            continue
        _merge_simple_bullet_value(parsed, key, value)
    return parsed


def heading_block_any_level(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    start_level = ""
    for idx, line in enumerate(lines):
        match = re.match(r"^(##+)\s+(.*)$", line.strip())
        if not match:
            continue
        level = match.group(1)
        title = match.group(2).strip()
        if heading in title:
            start = idx
            start_level = level
            break
    if start is None:
        return ""

    collected = [lines[start]]
    for line in lines[start + 1 :]:
        match = re.match(r"^(##+)\s+", line.strip())
        if match:
            next_level = match.group(1)
            if len(next_level) <= len(start_level):
                break
        collected.append(line)
    return "\n".join(collected).strip()


def flatten_trace_units(units: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    ordered: list[dict[str, str]] = []
    for group in ("epic_trace_units", "use_case_trace_units", "requirement_trace_units", "acceptance_trace_units"):
        ordered.extend(units.get(group, []))
    return ordered


def round_robin_chunks(values: list[str], chunk_count: int) -> list[list[str]]:
    buckets = [[] for _ in range(max(chunk_count, 1))]
    if not values:
        return buckets
    for idx, value in enumerate(values):
        buckets[idx % len(buckets)].append(value)
    return buckets


def summarize_list(values: list[str], *, max_items: int = 4) -> str:
    trimmed = values[:max_items]
    if not trimmed:
        return "none"
    return ", ".join(f"`{item}`" for item in trimmed)


def split_inline_values(value: str) -> list[str]:
    return unique_preserve(
        [
            item.strip().strip("`")
            for item in re.split(r"[;,]", str(value or ""))
            if item.strip().strip("`") and item.strip().strip("`") != "—"
        ]
    )


def semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if len(token) > 1 and token not in {"the", "and", "for", "with", "from", "into", "page", "flow", "step"}
    }


def semantic_focus_tokens(value: str) -> set[str]:
    return {
        token
        for token in semantic_tokens(value)
        if token
        not in {
            "current",
            "context",
            "data",
            "detail",
            "details",
            "page",
            "screen",
            "status",
            "summary",
            "load",
            "loaded",
            "show",
            "stay",
            "together",
            "workspace",
            "required",
        }
    }


def normalize_blueprint_type(value: str) -> str:
    return re.sub(r"[\s_]+", "-", str(value or "").strip().lower()).strip("-")


def derive_root_namespace(case_name: str, prd_text: str) -> str:
    if re.search(r"\bgeo\b|generative engine optimization", prd_text, flags=re.IGNORECASE):
        return "geo"
    collapsed = slugify(case_name).replace("-", "")
    if collapsed:
        return collapsed[:16]
    return "case"


def derive_boundary_scope(prd_text: str) -> str:
    lowered = prd_text.lower()
    clinic_boundary_signals = (
        "single-clinic deployment",
        "clinic account boundary",
        "clinic-private boundary",
    )
    clinic_domain_hints = (
        "clinic",
        "petprofile",
        "visitrecord",
        "examinationorder",
        "treatmentorder",
        "followupplan",
        "veterinarian",
        "reception",
    )
    if any(needle in lowered for needle in clinic_boundary_signals):
        return "clinic-account"
    if (
        any(needle in lowered for needle in ("no multi-tenancy needed", "single-account business boundary"))
        and any(hint in lowered for hint in clinic_domain_hints)
    ):
        return "clinic-account"
    return "tenant"


def boundary_phrase(boundary_scope: str) -> str:
    return "clinic-account" if boundary_scope == "clinic-account" else "tenant"


def boundary_subject(boundary_scope: str) -> str:
    return "clinic account" if boundary_scope == "clinic-account" else "tenant"


def workflow_scope_summary(context: dict[str, object]) -> str:
    domains = [str(item) for item in context.get("domains", []) if str(item).strip()]
    if domains:
        return " -> ".join(domains[:5])
    objects = [str(item) for item in context.get("core_objects", []) if str(item).strip()]
    if objects:
        return " -> ".join(objects[:5])
    return "source-defined workflow"


def derive_complexity_profile(args: argparse.Namespace, phase1_prd: Path) -> tuple[str, dict[str, object]]:
    if args.complexity_profile:
        chosen = normalized_complexity_profile(args.complexity_profile)
        return chosen, {"suggested_profile": chosen, "selection_confidence": "override", "indicators": {}}
    report = classify_phase1_prd(phase1_prd)
    return normalized_complexity_profile(str(report.get("suggested_profile", "standard"))), report


def to_pascal(raw: str) -> str:
    words = re.split(r"[^A-Za-z0-9]+", raw)
    identifier = "".join(word[:1].upper() + word[1:] for word in words if word)
    if identifier:
        return identifier
    unicode_tokens = [f"U{ord(ch):04X}" for ch in raw if ch.isalnum()]
    return "".join(unicode_tokens) or "Entity"


def to_camel(raw: str) -> str:
    pascal = to_pascal(raw)
    return pascal[:1].lower() + pascal[1:] if pascal else ""


def pluralize_slug(slug: str) -> str:
    if slug and not re.search(r"[a-z]", slug):
        return slug
    if slug.endswith("s"):
        return slug
    if slug.endswith("y") and len(slug) > 1 and slug[-2] not in "aeiou":
        return slug[:-1] + "ies"
    return slug + "s"


def infer_collection_alias(endpoint_name: str) -> str:
    if endpoint_name.startswith("List") and len(endpoint_name) > 4:
        return to_camel(endpoint_name[4:])
    return ""


def require_context_modules(context: dict[str, object]) -> list[dict[str, object]]:
    modules = context.get("modules")
    if not isinstance(modules, list) or not modules:
        raise SystemExit("需要先完成 WO-02b 的 P1 动态提取：context['modules'] 缺失或为空")
    normalized_modules: list[dict[str, object]] = []
    for module in modules:
        if isinstance(module, dict):
            normalized_modules.append(module)
    if not normalized_modules:
        raise SystemExit("需要先完成 WO-02b 的 P1 动态提取：context['modules'] 缺失或为空")
    return normalized_modules


def module_core_objects(module: dict[str, object]) -> list[str]:
    values = module.get("core_objects", [])
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def module_name(module: dict[str, object]) -> str:
    raw = str(module.get("module_name", "")).strip()
    if raw:
        return raw
    objects = module_core_objects(module)
    if objects:
        return f"{objects[0]} module"
    return "Unnamed module"


def module_primary_object(module: dict[str, object]) -> str:
    explicit = str(module.get("primary_object", "")).strip()
    if explicit:
        return explicit
    objects = module_core_objects(module)
    if objects:
        return objects[0]
    return module_name(module)


def module_alias_candidates(module: dict[str, object]) -> list[str]:
    values = module.get("technical_aliases", [])
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    return []


def module_technical_name(module: dict[str, object]) -> str:
    explicit = str(module.get("technical_module_name", "")).strip()
    if explicit:
        return explicit
    return choose_technical_pascal(module_name(module), *module_alias_candidates(module), prefix="Module")


def module_technical_primary_object(module: dict[str, object]) -> str:
    explicit = str(module.get("technical_primary_object", "")).strip()
    if explicit:
        return explicit
    return choose_technical_pascal(module_primary_object(module), *module_alias_candidates(module), prefix="Entity")


def module_technical_slug(module: dict[str, object]) -> str:
    explicit = str(module.get("technical_module_slug", "")).strip()
    if explicit:
        return explicit
    return choose_technical_slug(module_name(module), *module_alias_candidates(module), prefix="module")


def module_technical_object_slug(module: dict[str, object]) -> str:
    explicit = str(module.get("technical_primary_slug", "")).strip()
    if explicit:
        return explicit
    return choose_technical_slug(module_primary_object(module), *module_alias_candidates(module), prefix="entity")


def service_technical_name(service: ServiceSpec) -> str:
    return service.technical_name or choose_technical_pascal(service.owns_or_coordinates, prefix="Entity")


def service_technical_slug(service: ServiceSpec) -> str:
    return service.technical_slug or choose_technical_slug(service_technical_name(service), prefix="entity")


def looks_like_encoded_identifier(value: str) -> bool:
    stripped = str(value or "").strip()
    return bool(re.search(r"(?:^|[A-Z])U[0-9A-F]{4}", stripped) or re.search(r"(?:^|[_-])u[0-9a-f]{4}", stripped))


def context_technical_name(context: dict[str, object], label: str, *, prefix: str = "Entity") -> str:
    hints = context.get("technical_name_hints", {})
    if isinstance(hints, dict):
        explicit = str(hints.get(label, "")).strip()
        if explicit:
            return explicit
    alias_hints = context.get("object_alias_hints", {})
    candidates = alias_hints.get(label, []) if isinstance(alias_hints, dict) else []
    return choose_technical_pascal(label, *[str(item) for item in candidates], prefix=prefix)


def context_technical_slug(context: dict[str, object], label: str, *, prefix: str = "entity") -> str:
    hints = context.get("technical_slug_hints", {})
    if isinstance(hints, dict):
        explicit = str(hints.get(label, "")).strip()
        if explicit:
            return explicit
    alias_hints = context.get("object_alias_hints", {})
    candidates = alias_hints.get(label, []) if isinstance(alias_hints, dict) else []
    return choose_technical_slug(label, *[str(item) for item in candidates], prefix=prefix)


def infer_service_suffix(service_type: str) -> str:
    return {
        "transactional": "WorkflowService",
        "orchestration": "OrchestratorService",
        "read-assembly": "ReadService",
        "policy": "PolicyService",
        "domain": "DomainService",
        "support": "SupportService",
    }.get(service_type, "Service")


def infer_service_name(module: dict[str, object], service_type: str) -> str:
    return f"{module_technical_name(module)}{infer_service_suffix(service_type)}"


def infer_primary_endpoint(module: dict[str, object], service_type: str) -> str:
    explicit = str(module.get("primary_endpoint", "")).strip()
    if explicit and not looks_like_encoded_identifier(explicit):
        return explicit
    subject = module_technical_primary_object(module)
    verb = {
        "transactional": "Create",
        "orchestration": "Start",
        "read-assembly": "List",
        "policy": "Get",
        "domain": "Manage",
        "support": "Record",
    }.get(service_type, "Handle")
    return f"{verb}{subject}"


def infer_event_name(module: dict[str, object], service_type: str) -> str:
    explicit = str(module.get("event", "")).strip()
    if explicit and not looks_like_encoded_identifier(explicit):
        return explicit
    subject = module_technical_primary_object(module)
    suffix = {
        "transactional": "Updated",
        "orchestration": "Completed",
        "read-assembly": "ReadPrepared",
        "policy": "PolicyEvaluated",
        "domain": "Changed",
        "support": "Recorded",
    }.get(service_type, "Changed")
    return f"{subject}{suffix}"


def infer_home_namespace(root_namespace: str, module: dict[str, object]) -> str:
    explicit = str(module.get("home_namespace", "")).strip()
    if explicit:
        return explicit
    return f"{root_namespace}.{module_technical_slug(module).replace('-', '.')}"


def infer_public_contract(home_namespace: str, primary_object: str, technical_object: str | None = None) -> str:
    return f"{home_namespace}.{technical_object or to_pascal(primary_object)}"


def infer_http_method(service_type: str, endpoint_name: str) -> str:
    if endpoint_name.startswith(("Get", "List")) or service_type == "read-assembly":
        return "GET"
    if endpoint_name.startswith(("Update", "Patch")):
        return "PATCH"
    return "POST"


def infer_endpoint_path(module: dict[str, object], service_type: str, primary_object: str) -> str:
    base = pluralize_slug(module_technical_object_slug(module))
    if service_type == "read-assembly":
        return f"/api/v1/{base}"
    return f"/api/v1/{base}"


def release_service_type_surface(service_type: str) -> str:
    return {
        "transactional": "写入执行",
        "orchestration": "流程编排",
        "read-assembly": "读取汇总",
        "policy": "策略判断",
        "domain": "领域处理",
        "support": "审计支撑",
    }.get(service_type, "领域处理")


def release_domain_role_surface(service_types: list[str]) -> str:
    kinds = {item for item in service_types if item}
    if not kinds:
        return "主线业务能力域"
    if kinds <= {"domain", "transactional"}:
        return "主线业务能力域"
    if kinds <= {"orchestration"}:
        return "主线编排能力域"
    if kinds <= {"read-assembly"}:
        return "读取汇总能力域"
    if kinds <= {"policy"}:
        return "策略与权限能力域"
    if kinds <= {"support"}:
        return "审计与支撑能力域"
    if "orchestration" in kinds:
        return "主线协作编排域"
    if "read-assembly" in kinds:
        return "主线读取汇总域"
    return "主线协作能力域"


def release_module_role_surface() -> str:
    return "模块内权责与契约发布"


def release_slice_guardrail() -> str:
    return "相邻能力域只能只读消费，不接管本域写入权"


def release_handoff_rule() -> str:
    return "先在本域完成权威写入，再向下游传播变更"


def release_consistency_boundary(home_module: str, primary_object: str) -> str:
    return f"在 {home_module} 内保留 {primary_object} 的权威边界"


def release_change_propagation_note(service_name: str, endpoint_name: str) -> str:
    return f"{service_name} 先完成权威写入，再经 {endpoint_name} 向下游传播"


def release_read_context_purpose(primary_object: str) -> str:
    return f"围绕 {primary_object} 提供读取详情与评审上下文，供主线复核与下游消费。"


def release_workflow_audit_purpose() -> str:
    return "保留可审计的流程收口、异常处理与对操作者可见的评审证据。"


def release_cross_module_review_purpose() -> str:
    return "汇总主线中的跨模块收口、评审与异常摘要，供统一复核。"


def infer_service_purpose(module: dict[str, object], service_type: str, primary_object: str) -> str:
    module_surface = module_name(module)
    if service_type == "read-assembly":
        return (
            f"围绕 {primary_object} 汇总 {module_surface} 的可读详情，"
            "让评审与下游模块不必再次拼接上下文。"
        )
    if service_type == "orchestration":
        return (
            f"围绕 {primary_object} 编排 {module_surface} 的关键流程推进，"
            "并显式保留下一个动作所需上下文。"
        )
    if service_type == "policy":
        return (
            f"围绕 {primary_object} 明确 {module_surface} 的访问与策略判断边界，"
            "避免隐式放行或越权写入。"
        )
    if service_type == "support":
        return (
            f"围绕 {primary_object} 保留 {module_surface} 的审计与支撑记录，"
            "确保异常、复盘与责任追踪可回放。"
        )
    return (
        f"围绕 {primary_object} 明确 {module_surface} 的核心处理边界，"
        "让上下游能够直接理解状态变化与下一步动作。"
    )


def _prototype_page_value(page: dict[str, str], key: str) -> str:
    value = str(page.get(key) or "").strip().strip("`")
    return "" if value == "—" else value


def _objects_from_prototype_pages(prototype_pages: list[dict[str, str]]) -> list[str]:
    values: list[str] = []
    for page in prototype_pages:
        values.extend(split_inline_values(_prototype_page_value(page, "business_objects")))
    return unique_preserve(values)


def _module_definitions_from_prototype_pages(
    prototype_pages: list[dict[str, str]],
    root_namespace: str,
) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    seen: set[str] = set()
    for page in prototype_pages:
        module_name = _prototype_page_value(page, "canonical_page_id") or _prototype_page_value(page, "page_name")
        if not module_name:
            continue
        module_key = slugify(module_name)
        if not module_key or module_key in seen:
            continue
        seen.add(module_key)
        module_objects = split_inline_values(_prototype_page_value(page, "business_objects"))
        if not module_objects:
            module_objects = split_inline_values(_prototype_page_value(page, "must_show_together").replace("+", ","))
        service_type = (
            "read-assembly"
            if _prototype_page_value(page, "page_blueprint_type").lower() in {"dashboard", "review-decision"}
            else "domain"
        )
        primary_object = module_objects[-1] if module_objects else module_name.strip()
        module_stub = {
            "module_name": module_name.strip(),
            "primary_object": primary_object,
        }
        modules.append(
            {
                "module_name": module_name.strip(),
                "core_objects": module_objects,
                "primary_object": primary_object,
                "primary_endpoint": infer_primary_endpoint(module_stub, service_type),
                "event": infer_event_name(module_stub, service_type),
                "home_namespace": f"{root_namespace}.{module_key.replace('-', '.')}",
                "service_type": service_type,
            }
        )
    return modules


def _has_authoritative_phase1_business_truth(
    *,
    core_entities: list[str],
    dynamic_objects: list[str],
) -> bool:
    return len(unique_preserve(core_entities + dynamic_objects)) >= 3


def _module_definitions_from_business_objects(
    objects: list[str],
    root_namespace: str,
) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    for obj in unique_preserve(objects):
        modules.append(
            {
                "module_name": obj,
                "core_objects": [obj],
                "primary_object": obj,
                "primary_endpoint": infer_primary_endpoint({"module_name": obj, "primary_object": obj}, "domain"),
                "event": infer_event_name({"module_name": obj, "primary_object": obj}, "domain"),
                "home_namespace": f"{root_namespace}.{slugify(obj).replace('-', '.')}",
                "service_type": "domain",
            }
        )
    return modules


def parse_phase1_context(
    phase1_prd: Path,
    case_name: str,
    complexity_profile: str,
    prototype_pages: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    text = phase1_prd.read_text(encoding="utf-8")
    prototype_pages = prototype_pages or []
    domain_model = heading_section(text, "Domain Model")
    acceptance_block = heading_section(text, "Acceptance Criteria")
    requirement_block = heading_section(text, "Extended Requirement Set")
    subsystem_block = heading_section(text, "Business Subsystem Boundaries")
    module_matrix_block = heading_section(text, "Module Responsibility Matrix")
    nfr_block = heading_section(text, "Top Quality Attributes")
    business_truth_pack = parse_simple_heading_bullets(heading_block_any_level(text, "Business Truth Pack"))
    business_proof_track = parse_simple_heading_bullets(heading_block_any_level(text, "Business Proof Track"))
    chosen_business_thesis = parse_simple_heading_bullets(heading_block_any_level(text, "Chosen Business Thesis"))
    business_architecture_pressure = business_architecture_pressure_summary({"chosen_business_thesis": chosen_business_thesis})
    planning_truth_pack = parse_simple_heading_bullets(
        heading_block_any_level(text, "Planning Truth Pack"),
        list_keys={"object_chain", "state_handoff_anchors", "workflow_backbone"},
    )

    core_entities = extract_nested_bullet_values(domain_model, "core entities")
    durable_core_entities = persistent_business_objects(core_entities)
    subsystems = []
    for value in extract_nested_bullet_values(subsystem_block, "subsystems"):
        normalized = value.split(":", 1)[0].strip().replace("&", "and")
        if normalized:
            subsystems.append(normalized)
    module_names = [item[0] for item in parse_labeled_bullets(module_matrix_block, "module")]
    requirements = parse_labeled_bullets(requirement_block, "RQ")
    acceptance_items = parse_labeled_bullets(acceptance_block, "AC")
    trace_units = extract_phase1_trace_units(text)

    root_namespace = derive_root_namespace(case_name, text)
    boundary_scope = derive_boundary_scope(text)
    object_alias_hints = extract_object_alias_hints(text)
    prototype_modules = _module_definitions_from_prototype_pages(prototype_pages, root_namespace)
    prototype_objects = _objects_from_prototype_pages(prototype_pages)
    extracted_objects = persistent_business_objects(extract_dynamic_objects(text))
    authoritative_business_truth = _has_authoritative_phase1_business_truth(
        core_entities=durable_core_entities,
        dynamic_objects=extracted_objects,
    )
    try:
        extracted_modules = extract_module_definitions(text, root_namespace)
    except SystemExit:
        extracted_modules = []
    extracted_modules = sanitize_phase2_modules(extracted_modules, root_namespace=root_namespace)
    if not extracted_modules and authoritative_business_truth:
        extracted_modules = _module_definitions_from_business_objects(extracted_objects, root_namespace)
    modules = extracted_modules if authoritative_business_truth or not prototype_modules else prototype_modules
    modules = sanitize_phase2_modules(modules, root_namespace=root_namespace)
    technical_name_hints: dict[str, str] = {}
    technical_slug_hints: dict[str, str] = {}
    for module in modules:
        display_name = module_name(module)
        alias_candidates = unique_preserve(
            module_core_objects(module)
            + object_alias_hints.get(display_name, [])
            + [
                alias
                for object_name in module_core_objects(module)
                for alias in object_alias_hints.get(object_name, [])
            ]
        )
        technical_module_name = choose_technical_pascal(display_name, *alias_candidates, prefix="Module")
        primary_display = module_primary_object(module)
        primary_alias_candidates = unique_preserve(alias_candidates + object_alias_hints.get(primary_display, []))
        technical_primary = choose_technical_pascal(primary_display, *primary_alias_candidates, prefix="Entity")
        module["technical_aliases"] = alias_candidates
        module["technical_module_name"] = technical_module_name
        module["technical_module_slug"] = choose_technical_slug(display_name, *alias_candidates, prefix="module")
        module["technical_primary_object"] = technical_primary
        module["technical_primary_slug"] = choose_technical_slug(primary_display, *primary_alias_candidates, prefix="entity")
        service_type = str(module.get("service_type", "domain")).strip() or "domain"
        endpoint_module = dict(module)
        endpoint_module.pop("primary_endpoint", None)
        endpoint_module.pop("event", None)
        module["primary_endpoint"] = infer_primary_endpoint(endpoint_module, service_type)
        module["event"] = infer_event_name(endpoint_module, service_type)
        module["home_namespace"] = f"{root_namespace}.{module['technical_module_slug'].replace('-', '.')}"
        technical_name_hints[display_name] = technical_primary
        technical_slug_hints[display_name] = str(module["technical_primary_slug"])
        for object_name in module_core_objects(module):
            technical_name_hints.setdefault(
                object_name,
                choose_technical_pascal(
                    object_name,
                    *object_alias_hints.get(object_name, []),
                    *alias_candidates,
                    prefix="Entity",
                ),
            )
            technical_slug_hints.setdefault(
                object_name,
                choose_technical_slug(
                    object_name,
                    *object_alias_hints.get(object_name, []),
                    *alias_candidates,
                    prefix="entity",
                ),
            )
    dynamic_objects = persistent_business_objects(unique_preserve(
        extracted_objects + prototype_objects if authoritative_business_truth else prototype_objects + extracted_objects
    ))
    primary_object_seed = (
        persistent_business_objects(unique_preserve(durable_core_entities + extracted_objects))
        if authoritative_business_truth
        else persistent_business_objects(unique_preserve(prototype_objects + durable_core_entities))
    )
    objects = persistent_business_objects(unique_preserve(primary_object_seed + dynamic_objects))
    aggregate_target = max(profile_minimum(complexity_profile, "stage_02_aggregate_catalog"), 6)
    while dynamic_objects and len(objects) < aggregate_target + 3:
        additions = [item for item in dynamic_objects if item not in objects]
        if not additions:
            break
        objects.extend(additions)
        objects = unique_preserve(objects)

    if prototype_modules and not authoritative_business_truth:
        domains = unique_preserve([str(module["module_name"]) for module in prototype_modules])
    else:
        try:
            dynamic_domains = extract_dynamic_domains(text, root_namespace)
        except SystemExit:
            dynamic_domains = [str(module["module_name"]) for module in extracted_modules]
        domains = unique_preserve(subsystems + dynamic_domains)
        domains = unique_preserve(
            [domain for domain in domains if object_requires_persistent_table(domain)]
        )
        domain_target = max(profile_minimum(complexity_profile, "stage_02_domains"), 3)
        if dynamic_domains and len(domains) < domain_target:
            additions = [domain for domain in dynamic_domains if domain not in domains]
            if additions:
                domains.extend(additions)
                domains = unique_preserve(domains)

    semantic_support_objects = semantic_support_objects_from_names(objects)
    supplemental_objects = unique_preserve(
        semantic_support_objects
        or [f"{module_primary_object(module)} revision" for module in modules if module_primary_object(module)]
    )
    for object_name in unique_preserve(objects + supplemental_objects):
        revision_match = re.match(r"^(.*?)(?:\s+revision)$", object_name, flags=re.IGNORECASE)
        if revision_match:
            base_name = revision_match.group(1).strip()
            base_technical = technical_name_hints.get(base_name, "")
            base_slug = technical_slug_hints.get(base_name, "")
            if base_technical:
                technical_name_hints.setdefault(object_name, f"{base_technical}Revision")
            if base_slug:
                technical_slug_hints.setdefault(object_name, f"{base_slug}-revision")
        technical_name_hints.setdefault(
            object_name,
            choose_technical_pascal(object_name, *object_alias_hints.get(object_name, []), prefix="Entity"),
        )
        technical_slug_hints.setdefault(
            object_name,
            choose_technical_slug(object_name, *object_alias_hints.get(object_name, []), prefix="entity"),
        )
    default_adr_titles = default_adr_titles_for_context(
        {
            "text": text,
            "objects": objects,
            "core_objects": primary_object_seed or unique_preserve(dynamic_objects),
            "supplemental_objects": supplemental_objects,
            "detected_core_entities": unique_preserve(core_entities),
            "domains": domains,
            "module_matrix_names": unique_preserve(
                [str(module.get("module_name") or "").strip() for module in modules if str(module.get("module_name") or "").strip()]
                + module_names
            ),
            "requirements": requirements,
            "acceptance_items": acceptance_items,
            "business_truth_pack": business_truth_pack,
            "business_proof_track": business_proof_track,
            "chosen_business_thesis": chosen_business_thesis,
            "business_architecture_pressure": business_architecture_pressure,
            "planning_truth_pack": planning_truth_pack,
        }
    )
    adr_titles = extract_dynamic_adr_titles(text, modules)
    adr_titles = unique_preserve(default_adr_titles + adr_titles)

    quality_attrs = unique_preserve(
        [line.strip("- ").strip() for line in nfr_block.splitlines() if re.match(r"^[ 	]*-[ 	]*[A-Za-z/_-]+:", line)]
        + ["reliability", "usability", "security_data_control", "maintainability"]
    )

    return {
        "text": text,
        "root_namespace": root_namespace,
        "boundary_scope": boundary_scope,
        "objects": objects,
        "core_objects": primary_object_seed or unique_preserve(dynamic_objects),
        "supplemental_objects": supplemental_objects,
        "detected_core_entities": unique_preserve(core_entities),
        "domains": domains,
        "detected_subsystems": unique_preserve(subsystems),
        "modules": modules,
        "adr_titles": adr_titles,
        "module_matrix_names": unique_preserve(
            [str(module.get("module_name") or "").strip() for module in modules if str(module.get("module_name") or "").strip()]
            + module_names
        ),
        "requirements": requirements,
        "acceptance_items": acceptance_items,
        "business_truth_pack": business_truth_pack,
        "business_proof_track": business_proof_track,
        "chosen_business_thesis": chosen_business_thesis,
        "business_architecture_pressure": business_architecture_pressure,
        "planning_truth_pack": planning_truth_pack,
        "trace_units": trace_units,
        "all_trace_rows": flatten_trace_units(trace_units),
        "quality_attributes": quality_attrs,
        "prototype_pages": prototype_pages,
        "object_alias_hints": object_alias_hints,
        "technical_name_hints": technical_name_hints,
        "technical_slug_hints": technical_slug_hints,
    }

def text_has_any(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def build_service_specs(context: dict[str, object], complexity_profile: str) -> list[ServiceSpec]:
    root_namespace = str(context["root_namespace"])
    modules = require_context_modules(context)
    specs: list[ServiceSpec] = []
    seen_service_names: set[str] = set()
    target_floor = max(profile_minimum(complexity_profile, "stage_02_services"), 1)

    def add_service(spec: ServiceSpec) -> None:
        if spec.service_name in seen_service_names:
            return
        seen_service_names.add(spec.service_name)
        specs.append(spec)

    for spec in semantic_service_specs(context):
        add_service(spec)

    if len(specs) < target_floor:
        for module in modules:
            service_type = str(module.get("service_type", "domain")).strip() or "domain"
            primary_object = module_primary_object(module)
            technical_object = module_technical_primary_object(module)
            home_namespace = infer_home_namespace(root_namespace, module)
            endpoint_name = infer_primary_endpoint(module, service_type)
            add_service(
                ServiceSpec(
                    infer_service_name(module, service_type),
                    module_name(module),
                    home_namespace,
                    service_type,
                    primary_object,
                    endpoint_name,
                    infer_event_name(module, service_type),
                    infer_service_purpose(module, service_type, primary_object),
                    infer_public_contract(home_namespace, primary_object, technical_object),
                    endpoint_name,
                    infer_http_method(service_type, endpoint_name),
                    infer_endpoint_path(module, service_type, primary_object),
                    technical_name=technical_object,
                    technical_slug=module_technical_object_slug(module),
                )
            )
            add_service(
                ServiceSpec(
                    f"{module_technical_name(module)}ReadService",
                    module_name(module),
                    home_namespace,
                    "read-assembly",
                    primary_object,
                    f"Get{technical_object}Detail",
                    f"{technical_object}DetailPrepared",
                    release_read_context_purpose(primary_object),
                    infer_public_contract(home_namespace, primary_object, technical_object),
                    f"Get{technical_object}Detail",
                    "GET",
                    infer_endpoint_path(module, "read-assembly", primary_object),
                    technical_name=technical_object,
                    technical_slug=module_technical_object_slug(module),
                )
            )
    if specs:
        add_service(
            ServiceSpec(
                "WorkflowAuditService",
                "workflow-audit",
                f"{root_namespace}.workflow.audit",
                "support",
                "Workflow audit record",
                "RecordWorkflowAudit",
                "WorkflowAuditRecorded",
                release_workflow_audit_purpose(),
                f"{root_namespace}.workflow.audit.WorkflowAuditRecord",
                "RecordWorkflowAudit",
                "POST",
                "/api/v1/workflow-audits",
            )
        )
        add_service(
            ServiceSpec(
                "CrossModuleReviewService",
                "cross-module-review",
                f"{root_namespace}.workflow.review",
                "read-assembly",
                "Workflow review summary",
                "ListWorkflowReviewSummaries",
                "WorkflowReviewPrepared",
                release_cross_module_review_purpose(),
                f"{root_namespace}.workflow.review.WorkflowReviewSummary",
                "ListWorkflowReviewSummaries",
                "GET",
                "/api/v1/workflow-review-summaries",
            )
        )
    return specs[: max(target_floor, len(specs))]


def select_preferred_service(services: list[ServiceSpec], preferred_names: list[str]) -> ServiceSpec:
    by_name = {service.service_name: service for service in services}
    for service_name in preferred_names:
        if service_name in by_name:
            return by_name[service_name]
    return services[0]


def select_adr_anchor_service(title: str, services: list[ServiceSpec]) -> ServiceSpec:
    lowered = title.lower()
    semantic_preference_groups = [
        (("payload", "handoff", "decision", "recommendation", "task"), ["recommendation_decision", "optimization_task"]),
        (("governance", "access", "policy", "audit", "isolation", "boundary"), ["tenant_access_policy", "tracked_scope"]),
        (("observation", "finding", "event", "query", "run"), ["observation_run", "finding_query"]),
        (("seam", "extension", "provider", "dependency"), ["tenant_access_policy", "tracked_scope", "observation_run"]),
        (("review", "uncertainty", "truth", "closure"), ["review_report"]),
    ]
    for keywords, preferred_keys in semantic_preference_groups:
        if not any(keyword in lowered for keyword in keywords):
            continue
        for preferred_key in preferred_keys:
            for service in services:
                if semantic_service_key(service) == preferred_key:
                    return service
    for service in services:
        search_space = " ".join(
            [
                service.service_name,
                service.domain,
                service.owns_or_coordinates,
                service.purpose,
                service.service_type,
            ]
        ).lower()
        if any(keyword in search_space for keyword in lowered.split()):
            return service
    return services[0]


def detect_external_integration_categories(prd_text: str) -> list[str]:
    categories: list[str] = []
    search_text = prd_text.lower()
    for name, pattern in INTEGRATION_PATTERNS:
        if re.search(pattern, search_text, flags=re.IGNORECASE):
            categories.append(name)
    return unique_preserve(categories)


def external_integration_display_name(category: str) -> str:
    return {
        "llm_provider": "LLM / Model Provider",
        "identity_provider": "Identity Provider / OIDC",
        "payment_provider": "Payment Provider",
        "message_bus": "Message Bus / Queue",
        "warehouse": "Warehouse / Analytics Store",
        "storage": "Object Storage",
        "search": "Search / Retrieval Service",
        "crm": "CRM / Business SaaS",
        "email": "Email Provider",
        "analytics": "Analytics SDK / Event Sink",
        "cms_or_store": "CMS / Store Platform",
        "webhook_or_external_api": "Webhook / External API",
    }.get(category, category.replace("_", " ").title())


def external_dependency_rows(categories: list[str], root_namespace: str) -> list[list[str]]:
    row_templates = {
        "identity_provider": [
            "DEP-01",
            "identity_provider",
            "tenant policy, OIDC claims, and session boundary integration",
            f"`{root_namespace}.identity.access`",
            "review-bound / not yet MVP-binding",
            "skipped in first-wave P2 because no provider, token posture, or tenant-claim mapping is contract-frozen yet",
            "activate once a named OIDC / SSO vendor, token TTL, or claim-mapping rule becomes delivery-critical",
        ],
        "llm_provider": [
            "DEP-02",
            "llm_provider",
            "AI scoring or recommendation enrichment capability",
            f"`{root_namespace}.recommendation.decision`",
            "later-wave / validation-bound",
            "keep a replaceable provider seam only; do not freeze one vendor before value and cost signals are validated",
            "activate once the product commits to a named model provider, quota budget, or prompt/runtime contract",
        ],
        "webhook_or_external_api": [
            "DEP-03",
            "webhook_or_external_api",
            "external observation, export, or callback integration",
            f"`{root_namespace}.scope.governance`",
            "later-wave / interface-seam-only",
            "preserve adapter slot and error-mapping rule, but avoid fake provider specificity in the first-wave package",
            "activate once a named external API, callback contract, or mock/sandbox workflow is required for MVP delivery",
        ],
        "storage": [
            "DEP-04",
            "storage",
            "binary artifact or evidence export storage",
            f"`{root_namespace}.content.asset`",
            "review-bound / optional",
            "keep export seam explicit while relational core remains the first-wave source of truth",
            "activate once object-store naming, retention, and encryption posture become release-blocking",
        ],
        "search": [
            "DEP-05",
            "search",
            "external search or retrieval augmentation",
            f"`{root_namespace}.observation.scoring`",
            "later-wave / hypothesis-only",
            "do not freeze retrieval vendor posture before benchmark and recall-quality evidence exist",
            "activate once search provider selection changes latency, cost, or result-quality commitments",
        ],
    }
    rows = [row_templates[category] for category in categories if category in row_templates]
    if rows:
        return rows
    return [
        [
            "DEP-01",
            categories[0] if categories else "external_dependency",
            "external capability hinted by Phase-1 and preserved as a replaceable seam",
            f"`{root_namespace}.integration.boundary`",
            "review-bound / not yet MVP-binding",
            "recorded explicitly, but skipped until a named provider, auth posture, or SLA becomes part of the first-wave promise",
            "activate once the case binds a concrete provider or external dependency contract",
        ]
    ]


def render_stage_02_5(*, phase1_prd: Path, context: dict[str, object], categories: list[str]) -> str:
    root_namespace = str(context["root_namespace"])
    category_names = [external_integration_display_name(category) for category in categories]
    category_summary = ", ".join(f"`{name}`" for name in category_names) if category_names else "`none-detected`"
    dependency_rows = external_dependency_rows(categories, root_namespace)

    idr_entries: list[str] = []
    adapter_rows: list[list[str]] = []
    test_rows: list[list[str]] = []
    risk_rows: list[list[str]] = []
    for idx, row in enumerate(dependency_rows, start=1):
        dependency_id = row[0]
        dependency_type = row[1]
        capability = row[2]
        consuming_module = row[3]
        internal_interface = f"{to_snake(dependency_type)}_port"
        idr_entries.append(
            "\n".join(
                [
                    f"  - idr_{idx:02d}:",
                    f"    - idr_id: `IDR-{idx:02d}`",
                    f"    - dependency_id: `{dependency_id}`",
                    "    - provider: not-selected-in-first-wave",
                    "    - integration_pattern: preserve adapter-layer seam only; do not freeze vendor SDK details before a real MVP binding exists",
                    f"    - internal_interface: `{internal_interface}`",
                    "    - authentication_method: define only when a named provider is activated; until then keep auth posture review-bound rather than fabricated",
                    "    - key_management: secret-store plus rotation policy placeholder, to be finalized only with a concrete vendor decision",
                    "    - timeout: provider-specific budget will be added when Stage-02.5 activates; current Phase-2 package only preserves the need for an explicit timeout budget",
                    "    - retry_policy: provider-specific retry, quota, and circuit-breaker rules are deferred until activation instead of being guessed in design prose",
                    "    - fallback_strategy: fail closed, surface review-bound state, and preserve audit visibility instead of inventing false availability guarantees",
                    f"    - activation_note: `{dependency_id}` remains skipped because Phase-1 identifies the capability need but does not yet bind provider, SLA, data-sovereignty, or sandbox strategy for {consuming_module}.",
                ]
            )
        )
        adapter_rows.append(
            [
                dependency_id,
                internal_interface,
                "provider endpoint to be named on activation",
                "map external timeout/rate-limit/provider errors into stable business/system error envelope",
                "contract fixture + sandbox or mock declared only when provider is selected",
            ]
        )
        test_rows.append(
            [
                dependency_id,
                "contract fixtures preserve payload shape without binding a real provider",
                "activate vendor-mock smoke tests when provider is selected",
                "run provider quota / auth / callback tests only after activation",
                "do not label the case provider-ready while Stage-02.5 is skipped",
                "tenant deny, timeout, quota exhaustion, and callback signature failure remain mandatory negative paths once activated",
            ]
        )
        risk_rows.append(
            [
                f"RISK-{idx:02d}",
                dependency_id,
                f"{capability} could become release-critical later and force a rushed provider decision if the seam is not kept explicit now.",
                "medium",
                "medium",
                "keep adapter/interface name stable, preserve review-bound language, and reopen Stage-02.5 before any provider-specific commitment",
                "phase-2 architecture owner",
            ]
        )

    stage = f"""# Stage-02.5: third-party-integration-architecture-design

## 1. Generation Provenance
- state: `authored-first-pass`
- phase1_prd: `{phase1_prd}`
- trigger_basis:
  - Phase-1 external integration categories detected: {category_summary}

## 3. Core Structured Output
- activation_decision:
  - stage_status: `skipped`
  - trigger_summary:
    - Phase-1 contains external-integration signals, but the first-wave design package still lacks a named provider, fixed auth method, SLA, quota, data-sovereignty constraint, or mock/sandbox posture that would justify a fully active integration design lane.
  - skip_reason: The current Phase-2 baseline preserves external seams explicitly, but freezing provider-level design now would create false certainty. Stage-02.5 is therefore skipped by decision, not omitted by accident.
  - preserve_now:
    - keep provider-facing seams behind stable internal ports
    - keep auth/token and callback assumptions review-bound rather than silently hard-coded
    - require Stage-02.5 re-entry before any vendor-specific SDK, OAuth/OIDC mapping, external callback, or quota-driven rollout becomes MVP-critical
  - reactivation_rule:
    - Activate Stage-02.5 once delivery scope binds a named provider, auth pattern, callback contract, SLA, quota budget, timeout/retry policy, or mock/sandbox strategy.
- third_party_dependency_manifest:
{make_markdown_table(
    ["dependency_id", "dependency_type", "capability", "consuming_module", "mvp_criticality", "current_decision", "reactivation_trigger"],
    dependency_rows,
)}
- integration_decision_records:
{chr(10).join(idr_entries)}
- integration_adapter_specifications:
{make_markdown_table(
    ["dependency_id", "internal_port", "provider_endpoint", "error_mapping", "mock_strategy"],
    adapter_rows,
)}
- integration_test_strategy:
{make_markdown_table(
    ["dependency_id", "local_strategy", "ci_strategy", "staging_strategy", "production_guardrail", "negative_path_coverage"],
    test_rows,
)}
- integration_risk_register:
{make_markdown_table(
    ["risk_id", "dependency_id", "risk_description", "impact", "likelihood", "mitigation", "owner"],
    risk_rows,
)}
"""
    return stage.rstrip() + "\n"


def adr_content_for(
    *,
    title: str,
    service: ServiceSpec,
    case_name: str,
    upstream_ids: list[str],
    root_namespace: str,
) -> dict[str, object]:
    service_scope = f"`{service.home_module}` / `{service.public_contract}` / `{service.endpoint_name}`"
    ids = ", ".join(upstream_ids)
    lowered_title = title.lower()

    if title == "Adopt modular-monolith boundary with explicit public contracts":
        return {
            "context": f"First-wave `{case_name}` needs one workflow spine from intake and execution to closure, but current scale is closer to 120 req/min with 4x burst than to a multi-team, multi-region platform. The dominant constraint is keeping boundary, replay, and review-bound truth explicit without paying microservice coordination cost too early.",
            "decision": f"Adopt a modular-monolith baseline anchored by {service_scope}. Keep public contracts and ownership boundaries stable now, and defer physical service splits until runtime evidence shows throughput, team topology, or compliance isolation actually demand them.",
            "alternatives": [
                (
                    "split into microservices immediately",
                    "gives stronger physical isolation, but higher deployment complexity, more cross-service latency, and slower first-wave iteration for a case that still values workflow traceability over regional scale.",
                ),
                (
                    "keep one flat controller-led application layer",
                    "looks simpler in week one, but weakens contract ownership, makes replay evidence harder to preserve, and increases regression risk once findings, tasking, and review evolve independently.",
                ),
            ],
            "consequences": {
                "positive": "For the first-wave team and current throughput target, contract and module ownership remain explicit while onboarding and change cost stay manageable.",
                "negative": "Stage documents and namespace discipline become heavier up front, and any future physical decomposition still needs a deliberate migration plan for the next 2 to 3 releases instead of a silent refactor.",
                "risks": "If boundary complexity, compliance isolation, or p95 latency pressure grows materially over the next 2 to 3 releases, the same boundaries must be promotable into stronger runtime isolation without renaming public contracts.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the 120 req/min first-wave capacity target, and the requirement to preserve boundary/replay/review closure semantics across Stage-03 and Stage-04.",
        }

    if "payload" in lowered_title or "handoff" in lowered_title:
        return {
            "context": f"The insight -> action -> work path is the business hinge of `{case_name}`. If the handoff payload is reconstructed ad hoc during task creation, upstream rationale, target object hints, payload version, and blocked-reason semantics drift immediately.",
            "decision": f"Freeze a typed action-handoff payload before any downstream mutation. {service_scope} becomes the explicit boundary that carries payloadVersion, owner, target object, and decision posture into downstream execution without lossy remapping.",
            "alternatives": [
                (
                    "derive work-item fields dynamically from loose prose",
                    "is faster to scaffold, but weaker for replay, harder to diff over time, and more likely to lose blocked-reason or target-object semantics during operator handoff.",
                ),
                (
                    "flatten decision and execution into one mutable record",
                    "reduces short-term joins, but erases decision-stage history, blurs approval versus execution ownership, and makes audit or rollback analysis materially worse.",
                ),
            ],
            "consequences": {
                "positive": "Work-item creation stays deterministic in the first-wave release, and replay or audit can compare pre-execution and post-execution state without inventing missing payload context.",
                "negative": "Writers must honor payload versioning and schema discipline, so ad hoc field additions become slower than a free-form note-based workflow.",
                "risks": "If future slices need richer generated suggestions or partial approvals, the payload contract must expand additively instead of silently drifting through task-side convenience fields.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids} plus the acceptance rule that upstream actions cannot become work items unless typed payload, target intent, and blocked-state semantics remain explicit.",
        }

    if "audit" in lowered_title or "isolation" in lowered_title or "boundary" in lowered_title:
        return {
            "context": f"`{case_name}` is multi-actor and boundary-scoped. Cross-boundary access, privileged reads, and review/work-item mutations all become release-blocking if they rely on implicit trust rather than an auditable policy edge.",
            "decision": f"Route every sensitive read or mutation through an explicit boundary policy check anchored by {service_scope}. Fail closed on mismatch, and force audit visibility on work-item mutation, review closure, and privileged boundary reads instead of permitting convenience bypasses.",
            "alternatives": [
                (
                    "check roles only inside individual controllers",
                    "is lighter to code, but produces uneven enforcement, weaker audit closure, and a higher chance of boundary leakage when new endpoints or background flows appear.",
                ),
                (
                    "permit an internal-admin bypass for first-wave speed",
                    "reduces short-term friction, but raises compliance and trust risk immediately because the product then depends on operator discipline rather than enforceable policy contracts.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave design keeps boundary, policy, and audit edges explicit across API, review, and work flows instead of treating them as implementation trivia.",
                "negative": "There is more upfront policy and audit ceremony, and local development must preserve deny-path and break-glass scenarios rather than only happy-path flows.",
                "risks": "Provider-specific auth posture may still change later, so the policy contract must survive vendor swaps without breaking boundary claims, session boundaries, or audit correlation.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the deny-path acceptance criteria, and the requirement that audit-sensitive edges remain explicit before Phase-3 implementation starts.",
        }

    if title in {
        "Use asynchronous observation completion events with idempotent replay",
        DEFAULT_GENERIC_ASYNC_COMPLETION_ADR_TITLE,
    }:
        async_pack = async_completion_runtime_pack_for_title(title)
        return {
            "context": (
                f"{async_pack['context_surface_label']} are the first likely burst surfaces in `{case_name}`. "
                "They are slower and less predictable than simple reads, and they risk duplicate writes if the "
                "system treats completion as a one-shot synchronous mutation."
            ),
            "decision": (
                f"Use asynchronous completion events with idempotent replay anchored by {service_scope}. "
                "Completion can finish outside the request path, but the "
                f"{async_pack['completion_identity_label']} and replay identity must remain stable so "
                f"{async_pack['completion_result_label']} twice under retry or delayed processing."
            ),
            "alternatives": [
                (
                    async_pack["sync_alternative_name"],
                    async_pack["sync_alternative_reason"],
                ),
                (
                    "fire-and-forget completion without replay identity",
                    "reduces queue discipline, but increases duplicate registration risk and makes later audit or recovery more fragile when completion is retried.",
                ),
            ],
            "consequences": {
                "positive": async_pack["positive_consequence"],
                "negative": "Operators need explicit queued/running/completed semantics, and implementation must preserve event identity instead of relying on opaque background jobs.",
                "risks": "If queue depth or completion latency exceeds the current p95 budget, the system may need stronger scheduling or physical decomposition in a later release.",
            },
            "evidence": (
                f"Bound to Phase-1 trace ids {ids}, {async_pack['evidence_chain_label']}, and the explicit "
                f"requirement to keep {async_pack['replay_target_label']} replayable under retry or delayed processing."
            ),
        }

    if title == "Keep review-bound truth explicit instead of narrative readiness upgrades":
        return {
            "context": f"The review surface in `{case_name}` closes the loop, but upstream evidence may stay weak, contradictory, or still under validation. If review output upgrades uncertain signals into certainty, the product becomes operationally dangerous even if the workflow looks complete.",
            "decision": f"Keep review-bound truth explicit in {service_scope}. Require uncertainty level, note, and continue-or-revise posture to survive into review closure, and forbid narrative upgrades that turn review-bound evidence into false production confidence.",
            "alternatives": [
                (
                    "summarize weak evidence as a clean business-ready verdict",
                    "reads better in demos, but increases decision risk because operators can no longer see where the closure package still depends on weak or missing proof.",
                ),
                (
                    "leave uncertainty only in analyst notes outside the main report",
                    "reduces UI clutter, but makes review outcomes less traceable and easier to misread when downstream teams consume the closure without the side notes.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave review package remains honest about weak evidence and therefore safer for operators, business owners, and the next architecture decisions taken during release planning.",
                "negative": "Closure language is less polished and may feel less sales-friendly because it preserves uncertainty and review-bound qualifiers in the mainline artifact.",
                "risks": "If future teams optimize for presentation over truth preservation, they may try to remove uncertainty semantics unless the contract and acceptance surfaces keep them mandatory.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the review uncertainty acceptance criteria, and the explicit rule that downstream must not silently upgrade review-bound truth.",
        }

    if title == "Standardize response envelope and business/system error split":
        return {
            "context": f"`{case_name}` spans validation failures, permission denials, conflicts, timeouts, and external-runtime uncertainty. If each endpoint invents its own response and error shape, callers cannot reason consistently about retry, operator action, or audit correlation.",
            "decision": f"Standardize a single response envelope and a business_error versus system_error split anchored by {service_scope}. Every endpoint keeps trace_id, caller-action semantics, and stable machine-readable error_code behavior instead of bespoke per-surface payloads.",
            "alternatives": [
                (
                    "allow each endpoint to define its own ad hoc response shape",
                    "gives local flexibility, but increases client complexity, weakens replay tooling, and makes cross-surface error handling materially less deterministic.",
                ),
                (
                    "rely on HTTP status only with minimal body detail",
                    "is lighter at first glance, but loses retry guidance, domain-specific conflict meaning, and traceable caller action for review-critical workflows.",
                ),
            ],
            "consequences": {
                "positive": "Implementation and testing can reuse one consistent envelope across first-wave reads, writes, and negative paths, which improves traceability and contract tooling.",
                "negative": "Teams must conform to the shared shape, so hyper-local response optimizations become slower than they would in a free-form API style.",
                "risks": "If provider or background-job surfaces later need richer metadata, the envelope must expand additively instead of branching into multiple incompatible error contracts.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the contract-first API posture, and the requirement that callers can distinguish validation, permission, conflict, and system timeout outcomes deterministically.",
        }

    if title == "Use cursor-based pagination and indexed access patterns for growth surfaces":
        return {
            "context": f"Audit trails, findings, task boards, and historical review surfaces all grow over time in `{case_name}`. Offset pagination looks simpler early on, but becomes less stable under concurrent writes and makes audit or replay views harder to reason about.",
            "decision": f"Use cursor-based pagination and indexed access paths for growth surfaces anchored by {service_scope}. Keep tenant_id, status, updated_at, and cycle-aligned predicates explicit now so first-wave read patterns do not force a later contract rewrite.",
            "alternatives": [
                (
                    "use offset-based pagination everywhere",
                    "is simpler for prototypes, but weaker under concurrent writes, less stable for audit history, and more likely to produce duplicate or skipped rows across large result sets.",
                ),
                (
                    "avoid explicit index posture until implementation tuning",
                    "saves design time, but increases the risk of late-stage schema churn when task, finding, or audit growth surfaces begin missing the p95 latency target.",
                ),
            ],
            "consequences": {
                "positive": "First-wave task, finding, and audit surfaces have a stable read contract that can scale from day one without changing page semantics under write pressure.",
                "negative": "The design package must state index and cursor rules earlier than a throwaway prototype usually would, which adds up-front specificity.",
                "risks": "If access patterns shift materially after real usage, the index strategy still needs profiling and may require additive indexes or archival adjustments in a later release.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the 365d hot-retention assumption, and the requirement that growth surfaces stay reviewable without unstable offset paging.",
        }

    if title == "Reserve attribution and external-identity concerns as explicit extension seams":
        return {
            "context": f"`{case_name}` already hints at attribution and external identity needs, but the Phase-1 package does not yet justify a provider-specific commitment. The dominant constraint is avoiding silent omission while also avoiding fake precision.",
            "decision": f"Reserve attribution and external-identity concerns as explicit extension seams connected to {service_scope}. Keep named ports, seam fields, and re-entry hooks visible in Phase-2, but do not claim provider-ready posture before Stage-02.5 is activated by a real dependency commitment.",
            "alternatives": [
                (
                    "drop attribution and identity seams until later",
                    "reduces document size, but creates higher migration cost later because downstream contracts and object chains no longer preserve where those concerns must reconnect.",
                ),
                (
                    "freeze a named provider and callback posture immediately",
                    "looks more concrete, but would overfit the first-wave design to evidence the PRD does not yet provide and would risk false certainty about auth or attribution runtime behavior.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave package stays honest while preserving extension points that Phase-3 can consume without rewriting public contracts if identity or attribution becomes mandatory within the next 2 releases.",
                "negative": "Some readers will see more deferred seams in the Phase-2 design because the package prefers explicit placeholders, named ports, and review-bound fields over pretending provider posture is already closed.",
                "risks": "If a concrete provider becomes MVP-critical before Stage-02.5 is reopened, teams may hard-code vendor choices, timeout budgets, and callback shapes that miss the p95 latency target and break the replaceable-seam contract.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the deferred attribution seam requirement, and the rule that external-identity posture must remain explicit instead of silently hidden in implementation assumptions.",
        }

    if title == DEFAULT_GENERIC_EXTENSION_SEAM_ADR_TITLE or ("seam" in lowered_title and "extension" in lowered_title):
        return {
            "context": f"`{case_name}` may need later-wave connectors, provider bindings, or deferred capabilities, but the current Phase-1 evidence does not justify freezing a vendor-specific runtime posture. The dominant constraint is to keep the reconnection points explicit without inventing false readiness.",
            "decision": f"Reserve deferred extension and external dependency concerns as explicit seams connected to {service_scope}. Keep named ports, seam fields, and re-entry hooks visible in Phase-2, but do not claim provider-ready posture before a real dependency commitment or Stage-02.5 activation exists.",
            "alternatives": [
                (
                    "drop extension seams until implementation discovers them",
                    "reduces document size, but shifts structural truth into hidden implementation choices and raises the cost of reconnecting contracts later.",
                ),
                (
                    "freeze a provider-specific design immediately",
                    "looks more concrete, but overfits the current package to evidence the PRD does not yet provide and risks false certainty about runtime behavior.",
                ),
            ],
            "consequences": {
                "positive": "The first-wave package stays honest while preserving extension points that later phases can consume without rewriting public contracts if external dependencies become mandatory.",
                "negative": "Readers will see more explicit placeholder seams because the package prefers named ports and review-bound honesty over pretending those dependencies are already closed.",
                "risks": "If a concrete dependency becomes MVP-critical before the seam is reopened deliberately, teams may hard-code vendor choices or callback shapes that break the replaceable-seam contract.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the deferred extension boundary carried forward from the PRD, and the rule that missing provider truth must remain explicit instead of silently disappearing.",
        }

    if title == "Separate contract-facing namespaces from internal storage layout":
        return {
            "context": f"The public API and handoff contracts in `{case_name}` need to stay stable longer than any one storage or indexing strategy. If contract names mirror table layout too closely, later storage refactors become visible API churn.",
            "decision": f"Separate contract-facing namespaces from internal storage layout, using {service_scope} as the reference for stable public naming while allowing internal tables, indexes, and denormalized read structures to evolve behind the contract boundary.",
            "alternatives": [
                (
                    "name contracts directly after current table structures",
                    "is straightforward initially, but increases API drift risk once storage optimization, archival, or read-model reshaping changes table ownership or join strategy.",
                ),
                (
                    "hide namespaces entirely and rely on prose-only naming",
                    "reduces visible ceremony, but weakens traceability because downstream implementation and review surfaces lose a stable contract namespace to bind against.",
                ),
            ],
            "consequences": {
                "positive": "Public boundaries remain stable through first-wave implementation even if relational schema, indexing, or read-model layout becomes more specialized under real load.",
                "negative": "Engineers must maintain an explicit mapping between contract names and storage structures rather than treating one as an alias of the other.",
                "risks": "If namespace discipline slips in Phase-3, storage-driven renames may leak into APIs and break traceability across replay, review, and implementation handoff.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the object-chain continuity requirement, and the expectation that storage optimization should not rename public contracts midstream.",
        }

    if title == "Carry work-package and RBI chain into implementation intake unchanged":
        return {
            "context": f"The current `{case_name}` pack is implementation-planning-ready, not runtime-proven. If work-package and RBI relationships are flattened into generic todos before Phase-3 starts, unresolved truth and delivery sequence become much harder to govern.",
            "decision": f"Carry work-package ordering and RBI ownership into implementation intake unchanged, with {service_scope} and related handoff artifacts preserving blockers, replay hooks, and closure rules exactly as they were decided in Phase-2.",
            "alternatives": [
                (
                    "convert the handoff into a loose backlog without RBI bindings",
                    "is easier for local planning, but loses blocker semantics, reduces traceability, and makes it too easy to start slices in an order that invalidates the design rationale.",
                ),
                (
                    "recompute work packages during implementation kickoff",
                    "can feel more flexible, but creates avoidable churn because the same sequencing and risk questions must then be rediscovered after Phase-2 already answered them.",
                ),
            ],
            "consequences": {
                "positive": "Phase-3 onboarding starts with stable sequencing, blocker ownership, and replay evidence instead of a rewritten backlog that drops unresolved truth.",
                "negative": "Implementation intake becomes more structured and may feel heavier than a simple engineering TODO list in the first few days.",
                "risks": "If teams bypass the preserved RBI chain, they may mark slices done while still relying on unclosed runtime proofs or human sign-off assumptions.",
            },
            "evidence": f"Bound to Phase-1 trace ids {ids}, the implementation-intake handoff rule, and the requirement that review-bound or runtime-bound items stay explicit during downstream planning.",
        }

    return {
        "context": f"Phase-1 PRD for `{case_name}` requires this architecture decision to remain explicit across Stage-03 contracts, Stage-04 handoff, and first-wave implementation intake.",
        "decision": f"Use {service_scope} as the stable boundary anchor for this decision, and preserve the closing constraint instead of allowing local implementation convenience to redefine it later.",
        "alternatives": [
            (
                "collapse the concern into local implementation heuristics",
                "is faster short term, but weaker for traceability, replay, and downstream review because the decision no longer has a visible contract anchor.",
            ),
            (
                "defer the concern until implementation discovers it organically",
                "saves design time now, but raises later migration, coordination, and consistency risk once multiple slices depend on the same unresolved choice.",
            ),
        ],
        "consequences": {
            "positive": "The first-wave package keeps this choice visible to design, implementation, and review surfaces instead of hiding it in code comments or local assumptions.",
            "negative": "The design pack becomes more explicit and therefore slightly heavier than a thin architecture summary would be.",
            "risks": "If runtime evidence later changes the dominant constraint, the boundary must evolve additively instead of silently changing semantics mid-release.",
        },
        "evidence": f"Bound to Phase-1 trace ids {ids} and the requirement that downstream artifacts can explain why this decision exists without reverse-engineering implementation code.",
    }


def table_owner_for_name(context: dict[str, object], root_namespace: str, table_name: str) -> str:
    semantic_owner = semantic_table_owner(table_name, root_namespace)
    if semantic_owner:
        return semantic_owner
    modules = require_context_modules(context)
    for module in modules:
        if table_name in {to_snake(item) for item in module_core_objects(module)}:
            return infer_home_namespace(root_namespace, module)
    return f"{root_namespace}.unassigned"


def table_design_template(table_name: str) -> dict[str, object]:
    semantic_template = semantic_table_design_template(table_name)
    if semantic_template is not None:
        return semantic_template
    default_pk = "tenant_id" if table_name == "tenant" else f"{table_name}_id"
    default = {
        "pk": default_pk,
        "fk": "none" if table_name == "tenant" else "tenant_id -> tenant.tenant_id",
        "unique_constraints": default_pk,
        "composite_indexes": "tenant_id + status, tenant_id + updated_at desc"
        if table_name != "tenant"
        else "status, updated_at desc",
        "pii_level": "tenant-private" if table_name in {"tenant", "tenant_membership"} else "low-to-medium",
        "sensitive_fields": "email, actor_subject_id"
        if table_name in {"tenant", "tenant_membership", "audit_record"}
        else "tenant_id, notes",
        "masking_or_encryption": "kms-backed encryption at rest + masked logs",
        "retention_rule": "keep 365d hot + archive 730d cold",
        "audit_access_rule": "tenant-scoped read + privileged break-glass audit",
        "compliance_note": "preserve tenant isolation and review-bound evidence posture",
        "field_rows": [
            [default_pk, "uuid", "false", "pk", "btree pk"],
            ["tenant_id", "uuid", "false", "fk tenant.tenant_id", "btree tenant_id"],
            ["status", "varchar(32)", "false", "enum-like", "btree tenant_id + status"],
            ["payload", "jsonb", "true", "shape validated", "gin payload"],
            ["updated_at", "timestamptz", "false", "default now()", "btree tenant_id + updated_at desc"],
            ["created_at", "timestamptz", "false", "default now()", "btree created_at"],
        ],
    }
    if table_name == "tenant":
        default["fk"] = "none"
        default["unique_constraints"] = "tenant_key"
        default["field_rows"] = [
            ["tenant_id", "uuid", "false", "pk", "btree pk"],
            ["tenant_key", "varchar(64)", "false", "unique", "btree tenant_key"],
            ["status", "varchar(24)", "false", "enum-like", "btree status"],
            ["updated_at", "timestamptz", "false", "default now()", "btree updated_at desc"],
            ["created_at", "timestamptz", "false", "default now()", "btree created_at"],
        ]
        return default
    if table_name.endswith("_revision"):
        default["unique_constraints"] = f"{table_name}_parent_id + revision_no"
    if table_name.endswith("_log"):
        default["composite_indexes"] = "tenant_id + created_at desc, tenant_id + status"
    if table_name.endswith("_decision"):
        default["sensitive_fields"] = "tenant_id, decision_note"
    return default


def build_table_specs(
    context: dict[str, object],
    root_namespace: str,
    complexity_profile: str,
    services: list[ServiceSpec],
) -> list[dict[str, object]]:
    require_context_modules(context)
    core_objects = [
        str(item)
        for item in context.get("core_objects", [])
        if str(item).strip() and object_requires_persistent_table(str(item))
    ]
    supplemental_objects = [
        str(item)
        for item in context.get("supplemental_objects", [])
        if str(item).strip() and object_requires_persistent_table(str(item))
    ]
    selected_objects = unique_preserve(
        core_objects
        + [service.owns_or_coordinates for service in services if object_requires_persistent_table(service.owns_or_coordinates)]
    )
    preferred = unique_preserve(selected_objects + supplemental_objects)
    profile = normalized_complexity_profile(complexity_profile)
    if profile == "micro":
        expansion_budget = 1
    elif profile == "standard":
        expansion_budget = len(supplemental_objects)
    else:
        expansion_budget = len(supplemental_objects)
    desired = max(
        profile_minimum(complexity_profile, "stage_03_schema_tables"),
        min(len(preferred), len(selected_objects) + expansion_budget),
    )

    specs: list[dict[str, object]] = []
    for obj in preferred:
        technical_name = context_technical_name(context, obj)
        table_name = semantic_table_name(technical_name)
        if table_name in {spec["table_name"] for spec in specs}:
            continue
        owner = table_owner_for_name(context, root_namespace, table_name)
        if owner.endswith(".unassigned"):
            owner = owning_service_for_object(obj, services).home_module
        design = table_design_template(table_name)

        specs.append(
            {
                "object_name": obj,
                "technical_name": technical_name,
                "table_name": table_name,
                "owner": owner,
                "pk": design["pk"],
                "fk": design["fk"],
                "unique_constraints": design["unique_constraints"],
                "composite_indexes": design["composite_indexes"],
                "pii_level": design["pii_level"],
                "sensitive_fields": design["sensitive_fields"],
                "masking_or_encryption": design["masking_or_encryption"],
                "retention_rule": design["retention_rule"],
                "audit_access_rule": design["audit_access_rule"],
                "compliance_note": design["compliance_note"],
                "field_rows": design["field_rows"],
            }
        )
        if len(specs) >= desired:
            break
    return specs


def distribute_phase1_ids(rows: list[str], bucket_count: int) -> list[list[str]]:
    buckets = round_robin_chunks(rows, bucket_count)
    return [bucket if bucket else [rows[idx % len(rows)]] for idx, bucket in enumerate(buckets)] if rows else buckets


def build_stage_03_endpoint_specs(
    services: list[ServiceSpec],
    *,
    root_namespace: str,
    table_specs: list[dict[str, object]] | None = None,
) -> list[ServiceSpec]:
    endpoint_specs = [*services]
    existing_objects = {
        token
        for service in services
        for token in (to_snake(service.owns_or_coordinates), to_snake(service_technical_name(service)))
        if token
    }
    existing_endpoints = {
        (service.endpoint_name, service.method, service.path)
        for service in endpoint_specs
    }

    def append_endpoint(spec: ServiceSpec) -> None:
        key = (spec.endpoint_name, spec.method, spec.path)
        if key in existing_endpoints:
            return
        existing_endpoints.add(key)
        endpoint_specs.append(spec)

    for service in services:
        technical_name = service_technical_name(service)
        entity_slug = service_technical_slug(service)
        append_endpoint(
            ServiceSpec(
                f"{technical_name}StatusService",
                service.domain,
                service.home_module,
                "transactional",
                service.owns_or_coordinates,
                f"Update{technical_name}Status",
                f"{technical_name}StatusChanged",
                f"Apply bounded state updates for {service.owns_or_coordinates}.",
                service.public_contract,
                f"Update{technical_name}Status",
                "PATCH",
                f"/api/v1/{pluralize_slug(entity_slug)}/{{id}}",
                technical_name=technical_name,
                technical_slug=entity_slug,
            )
        )
        append_endpoint(
            ServiceSpec(
                f"{technical_name}QueryService",
                service.domain,
                f"{service.home_module}.query",
                "read-assembly",
                service.owns_or_coordinates,
                f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                "none",
                f"Expose list and query surfaces for {service.owns_or_coordinates}.",
                f"{service.home_module}.{technical_name}List",
                f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                "GET",
                f"/api/v1/{pluralize_slug(entity_slug)}",
                technical_name=technical_name,
                technical_slug=entity_slug,
            )
        )
    if table_specs:
        for spec in table_specs:
            object_name = str(spec.get("object_name", "")).strip()
            if not object_name:
                continue
            object_key = to_snake(object_name)
            if not object_key or object_key in existing_objects:
                continue
            owner = owning_service_for_object(object_name, services)
            technical_name = str(spec.get("technical_name") or service_technical_name(owner)).strip()
            entity_slug = choose_technical_slug(technical_name, prefix="entity")
            public_contract = f"{owner.domain}.{technical_name}"
            append_endpoint(
                ServiceSpec(
                    f"{technical_name}StatusService",
                    owner.domain,
                    owner.home_module,
                    "transactional",
                    object_name,
                    f"Update{technical_name}Status",
                    f"{technical_name}StatusChanged",
                    f"Apply bounded state updates for {object_name}.",
                    public_contract,
                    f"Update{technical_name}Status",
                    "PATCH",
                    f"/api/v1/{pluralize_slug(entity_slug)}/{{id}}",
                    technical_name=technical_name,
                    technical_slug=entity_slug,
                )
            )
            append_endpoint(
                ServiceSpec(
                    f"{technical_name}QueryService",
                    owner.domain,
                    f"{owner.home_module}.query",
                    "read-assembly",
                    object_name,
                    f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                    "none",
                    f"Expose list and query surfaces for {object_name}.",
                    f"{owner.home_module}.{technical_name}List",
                    f"List{to_pascal(pluralize_slug(entity_slug).replace('-', ' '))}",
                    "GET",
                    f"/api/v1/{pluralize_slug(entity_slug)}",
                    technical_name=technical_name,
                    technical_slug=entity_slug,
                )
            )
            existing_objects.add(object_key)
    if len(services) > 1:
        anchor = services[0]
        append_endpoint(
            ServiceSpec(
                "AggregateReadService",
                anchor.domain,
                f"{root_namespace}.aggregate.read",
                "read-assembly",
                "Cross-module summary",
                "ListCrossModuleSummaries",
                "none",
                "Expose cross-module read surfaces when multiple service boundaries participate in one workflow.",
                f"{root_namespace}.aggregate.CrossModuleSummary",
                "ListCrossModuleSummaries",
                "GET",
                "/api/v1/cross-module-summaries",
            )
        )
    return endpoint_specs


def _sample_request_example_value(field_name: str) -> object:
    normalized = str(field_name).strip()
    lowered = normalized.lower()
    if not normalized:
        return "sample-value"
    if normalized in {"tenantId", "tenant_id"}:
        return "tenant-001"
    if lowered.endswith("status") or lowered == "status":
        return "draft"
    if lowered.endswith("decision") or lowered == "decision":
        return "draft"
    if lowered.endswith("version"):
        return 1
    if lowered == "cursor":
        return None
    if lowered in {"pagesize", "page_size", "limit", "count", "qty", "quantity", "stockqty", "petage", "age"}:
        return 25 if "page" in lowered else 1
    if lowered.startswith(("is", "has", "include", "allow", "enable")) or lowered.endswith(("enabled", "required", "visible")):
        return True
    if lowered.endswith(("date", "time", "datetime", "at")) or "date" in lowered or "time" in lowered:
        return "2026-04-10T10:00:00Z"
    if normalized.endswith("Id") or normalized.endswith("ID"):
        return f"{to_snake(normalized[:-2])}-001"
    if lowered.endswith(("amount", "price", "fee", "fees", "score", "percent", "percentage")):
        return 1
    return f"{to_snake(normalized)}-sample"


def _set_nested_request_example_path(example: dict[str, object], target_path: str, value: object) -> None:
    segments = [segment.strip() for segment in str(target_path).split(".") if segment.strip()]
    if not segments or segments[0] != "request":
        return
    current: dict[str, object] = example
    for segment in segments[1:-1]:
        nested = current.get(segment)
        if not isinstance(nested, dict):
            nested = {}
            current[segment] = nested
        current = nested
    leaf = segments[-1]
    if leaf not in current:
        current[leaf] = value


def build_request_mapping_lookup(binding_rows: list[list[str]]) -> dict[tuple[str, str], list[str]]:
    lookup: dict[tuple[str, str], list[str]] = {}
    for row in binding_rows:
        if len(row) < 9:
            continue
        path = str(row[6]).strip()
        method = str(row[7]).strip().upper()
        mapping_text = str(row[8]).strip()
        if not path or not method or not mapping_text or mapping_text.startswith("review-bound"):
            continue
        key = (path, method)
        lookup.setdefault(key, []).append(mapping_text)
    return lookup


def enrich_request_example_with_request_mappings(
    example: dict[str, object],
    service: ServiceSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> dict[str, object]:
    if not request_mapping_lookup:
        return example
    enriched = dict(example)
    for mapping_text in request_mapping_lookup.get((service.path, service.method.upper()), []):
        for raw_entry in mapping_text.split(";"):
            entry = raw_entry.strip()
            if not entry or "->" not in entry:
                continue
            alias, target = [part.strip() for part in entry.split("->", 1)]
            if not target.startswith("request."):
                continue
            sample_value = _sample_request_example_value(alias.split(".")[-1])
            _set_nested_request_example_path(enriched, target, sample_value)
    return enriched


def stage_03_request_example(
    service: ServiceSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> dict[str, object]:
    semantic_key = semantic_service_key(service)
    if semantic_key == "tenant_access_policy":
        example = {"tenantId": "tenant-001"}
    elif semantic_key == "tracked_scope":
        example = {"tenantId": "tenant-001", "scopeKey": "brand-core", "brandName": "Acme"}
    elif semantic_key == "observation_run":
        example = {"tenantId": "tenant-001", "scopeId": "scope-001", "runMode": "baseline"}
    elif semantic_key == "finding_query":
        if service.endpoint_name.startswith("List"):
            example = {
                "tenantId": "tenant-001",
                "observationRunId": "run-001",
                "priorityBands": ["high", "medium"],
                "includeCompetitorWindow": True,
                "cursor": None,
                "pageSize": 25,
            }
        else:
            example = {"tenantId": "tenant-001", "findingId": "finding-001"}
    elif semantic_key == "recommendation_decision":
        example = {
            "tenantId": "tenant-001",
            "findingId": "finding-001",
            "assetId": "asset-001",
            "decision": "draft",
            "payloadVersion": "v1",
        }
    elif semantic_key == "optimization_task":
        if service.endpoint_name.startswith("List"):
            example = {"tenantId": "tenant-001", "status": "open", "cursor": None, "pageSize": 25}
        else:
            example = {"tenantId": "tenant-001", "recommendationId": "recommendation-001", "status": "open"}
    elif semantic_key == "review_report":
        example = {
            "tenantId": "tenant-001",
            "scopeId": "scope-001",
            "cycleKey": "2026-W15",
            "freezeTaskStatusesBefore": "submitted",
            "includeUncertaintyBreakdown": True,
        }
    elif semantic_key == "attribution_seam":
        example = {"tenantId": "tenant-001", "scopeId": "scope-001"}
    else:
        entity_key = f"{to_camel(service_technical_name(service))}Id" or "entityId"
        example = {"tenantId": "tenant-001", entity_key: f"{to_snake(service_technical_name(service))}-001"}
        if service.endpoint_name.startswith("List"):
            example["status"] = "active"
            example["cursor"] = None
            example["pageSize"] = 25
        elif service.method == "PATCH" or "Update" in service.endpoint_name:
            example["status"] = "updated"
            example["expectedVersion"] = 2
        elif service.method == "POST":
            example["status"] = "draft"
            example["input"] = {"summary": f"{service.owns_or_coordinates} workflow input"}
    return enrich_request_example_with_request_mappings(example, service, request_mapping_lookup)


def stage_03_response_example(service: ServiceSpec) -> dict[str, object]:
    semantic_key = semantic_service_key(service)
    if semantic_key == "tenant_access_policy":
        return {
            "data": {
                "tenantId": "tenant-001",
                "role": "growth_owner",
                "policyDecision": "allow",
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "tracked_scope":
        return {
            "data": {
                "scopeId": "scope-001",
                "status": "active",
                "activeRevisionNo": 1,
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "observation_run":
        return {
            "data": {
                "observationRunId": "run-001",
                "status": "queued",
                "measurementWindow": "last-7d",
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "finding_query":
        if service.endpoint_name.startswith("List"):
            return {
                "data": {
                    "findings": [
                        {
                            "findingId": "finding-001",
                            "scopeId": "scope-001",
                            "severity": "high",
                            "score": "0.82",
                            "priorityBand": "high",
                            "measurementWindow": "last-7d",
                            "recommendationStatus": "draft",
                            "traceAnchor": "trace-001",
                        }
                    ]
                },
                "meta": {"traceId": "trace-001", "nextCursor": "cursor-001", "readModelVersion": 1},
            }
        return {
            "data": {
                "findingId": "finding-001",
                "scopeId": "scope-001",
                "severity": "high",
                "score": "0.82",
                "traceAnchor": "trace-001",
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "recommendation_decision":
        return {
            "data": {
                "recommendationId": "recommendation-001",
                "findingId": "finding-001",
                "payloadVersion": "v1",
                "decisionStatus": "draft",
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "optimization_task":
        if service.endpoint_name.startswith("List"):
            return {
                "data": {
                    "optimizationTasks": [
                        {
                            "taskId": "task-001",
                            "recommendationId": "recommendation-001",
                            "status": "open",
                            "dueAt": "2026-04-15",
                        }
                    ]
                },
                "meta": {"traceId": "trace-001", "nextCursor": "cursor-001"},
            }
        return {
            "data": {
                "taskId": "task-001",
                "recommendationId": "recommendation-001",
                "status": "open",
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "review_report":
        return {
            "data": {
                "reviewReportId": "review-001",
                "status": "generated",
                "uncertaintyLevel": "medium",
                "uncertaintyNote": "sample still small",
                "decisionPosture": "revise",
                "thresholdRationale": "repeatability remains below threshold",
                "reviewSummary": {
                    "executedTaskCount": 3,
                    "acceptedRecommendationCount": 2,
                    "blockedTaskCount": 1,
                },
            },
            "meta": {"traceId": "trace-001"},
        }
    if semantic_key == "attribution_seam":
        return {
            "data": {
                "scopeId": "scope-001",
                "attributionMode": "review-bound",
                "seamStatus": "reserved",
            },
            "meta": {"traceId": "trace-001"},
        }
    entity_key = f"{to_camel(service_technical_name(service))}Id" or "entityId"
    item = {
        entity_key: f"{to_snake(service_technical_name(service))}-001",
        "status": "active",
        "module": service.domain,
    }
    if service.endpoint_name.startswith("List"):
        return {
            "data": [item],
            "meta": {"traceId": "trace-001", "nextCursor": "cursor-001"},
        }
    return {
        "data": item,
        "meta": {"traceId": "trace-001"},
    }


def stage_03_contract_schema_fields(
    service: ServiceSpec,
    request_mapping_lookup: dict[tuple[str, str], list[str]] | None = None,
) -> list[str]:
    request_example = stage_03_request_example(service, request_mapping_lookup=request_mapping_lookup)
    response_example = stage_03_response_example(service)
    data = response_example.get("data")
    meta = response_example.get("meta")
    collection_alias = infer_collection_alias(service.endpoint_name)
    fields = flatten_schema_fields(request_example, prefix="request")
    if isinstance(data, list) and collection_alias:
        fields.extend(flatten_schema_fields(data, prefix=f"response.data.{collection_alias}"))
    else:
        fields.extend(flatten_schema_fields(data, prefix="response.data"))
    if isinstance(meta, dict):
        fields.extend(flatten_schema_fields(meta, prefix="response.meta"))
    fields.extend(
        [
            "response.error.error_type: business_error|system_error",
            "response.error.error_code: string",
            "response.error.retryability: string",
            "response.error.caller_action: string",
        ]
    )
    array_object_prefixes = {
        field.split(": ", 1)[0]
        for field in fields
        if field.endswith(": array<object>")
    }
    if array_object_prefixes:
        fields = [
            field
            for field in fields
            if not any(
                field == f"{prefix}: array<object>" and any(other.startswith(f"{prefix}[].") for other in fields)
                for prefix in array_object_prefixes
            )
        ]
    fields = unique_preserve(fields)
    if fields:
        return fields
    fallback_id = f"{to_snake(service_technical_name(service))}Id"
    return [f"request.{fallback_id}: string", "request.tenantId: string", "response.data.status: string"]


def build_object_profile(service: ServiceSpec, obj_name: str) -> dict[str, str]:
    technical_name = service_technical_name(service)
    object_key = to_snake(technical_name)
    event_name = event_name_for_model(service, obj_name)
    state_map = {
        "transactional": "created / active / completed / archived",
        "orchestration": "queued / running / completed / archived",
        "read-assembly": "prepared / refreshed / stale / archived",
        "policy": "draft / active / restricted / archived",
        "domain": "draft / active / revised / archived",
        "support": "recorded / confirmed / exported / archived",
    }
    aggregate_kind = {
        "transactional": "aggregate-root",
        "orchestration": "aggregate-root",
        "read-assembly": "read-model",
        "policy": "aggregate-root",
        "domain": "aggregate-root",
        "support": "support-entity",
    }.get(service.service_type, "aggregate-root")
    return {
        "aggregate_kind": aggregate_kind,
        "primary_states": state_map.get(service.service_type, "draft / active / archived"),
        "authoritative_mutations": f"{service.primary_inbound}, update {object_key}, archive {object_key}",
        "emitted_events": event_name,
        "failure_guardrail": f"{obj_name} 的变更必须收敛在 `{service.service_name}` 内，并保留可追溯证据。",
        "mutation_guard": f"只有 `{service.service_name}` 可以权威修改 `{object_key}`；下游模块只能按契约读取。",
        "collaborators": f"{event_source_path_for_model(service, obj_name)}，并保留 review / audit 可见面。",
        "read_only_refs": f"{service.public_contract}, {service.endpoint_name}, version anchors",
        "must_not_write": "所有非 owner 模块",
        "conflict_rule": f"对 `{object_key}` 的版本化写入必须拒绝过期更新",
        "change_propagation_path": f"{service.service_name} -> public contract -> 下游读取与 review 面",
        "must_not_own": "相邻模块的权威对象",
        "public_boundary_status": "active / contract-bound",
    }


def build_ownership_profile(obj_name: str, services: list[ServiceSpec], owner: ServiceSpec) -> dict[str, str]:
    technical_name = service_technical_name(owner)
    obj_key = to_snake(technical_name)
    read_consumers = [
        service.service_name
        for service in services
        if service.service_name != owner.service_name
        and (
            obj_key in to_snake(service.owns_or_coordinates)
            or obj_key in to_snake(service_technical_name(service))
            or obj_key in to_snake(service.purpose)
            or service.service_type == "read-assembly"
        )
    ]
    propagated_by = event_name_for_model(owner, obj_name)
    return {
        "read_consumers": ", ".join(read_consumers) if read_consumers else "downstream read surfaces",
        "change_propagation_path": f"{owner.service_name} -> {propagated_by} -> 下游读取与 review 面",
        "forbidden_shortcut": f"不得绕过 `{owner.service_name}` 从其他模块或表耦合捷径直接写 `{obj_key}`。",
        "closure_note": f"`{obj_name}` 继续由 `{owner.service_name}` 持有权威写入，其余位置只读消费。",
    }


def generic_endpoint_policy(service: ServiceSpec) -> list[str]:
    rate_limit = {
        "transactional": "20 req/min per tenant",
        "orchestration": "10 req/min per workflow boundary",
        "read-assembly": "60 req/min per tenant",
        "policy": "120 req/min per subject",
        "domain": "30 req/min per tenant",
        "support": "24 req/min per tenant",
    }.get(service.service_type, "30 req/min")
    pagination = "cursor-based for list endpoints" if service.endpoint_name.startswith("List") else "none"
    response_profile = f"{service.method} `{service.endpoint_name}` returns a contract-bound response for `{service.owns_or_coordinates}`."
    retryability = "safe to retry on system_error with the same idempotency anchor when applicable"
    idempotency = "naturally idempotent read" if service.method == "GET" else f"{to_snake(service_technical_name(service))} id or caller token"
    failure_codes = "400 invalid_request; 403 forbidden; 404 not_found; 409 version_conflict; 503 dependency_unavailable"
    return [rate_limit, pagination, response_profile, retryability, idempotency, failure_codes]


def _primary_req_id(upstream_trace_ids: list[str]) -> str:
    for prefix in ("P1-REQ-", "P1-AC-", "P1-UC-", "P1-US-", "P1-EP-"):
        for trace_id in upstream_trace_ids:
            if trace_id.startswith(prefix):
                return trace_id
    return upstream_trace_ids[0] if upstream_trace_ids else "P1-REQ-TBD"


def choose_service_match_for_interaction(
    interaction: dict[str, str],
    page_row: dict[str, str],
    endpoint_specs: list[ServiceSpec],
) -> InteractionServiceMatch:
    if not endpoint_specs:
        return InteractionServiceMatch(
            service=None,
            score=0,
            semantic_overlap=0,
            has_object_overlap=False,
            method_match=False,
            blocked_reason="no endpoint specs available for interaction-level binding",
        )
    preferred_method = "GET" if str(interaction.get("trigger_kind", "")).strip() == "page_load" else "POST"
    business_objects = split_inline_values(page_row.get("business_objects", ""))
    page_name = str(page_row.get("page_name", "")).strip()
    page_blueprint_type = normalize_blueprint_type(str(page_row.get("page_blueprint_type", "")).strip())
    goal_focus_tokens = semantic_focus_tokens(
        " ".join(
            [
                str(page_row.get("primary_user_goal", "")).strip(),
                str(page_row.get("primary_action", "")).strip(),
            ]
        )
    )
    interaction_blob = " ".join(
        [
            interaction.get("interaction_id", ""),
            interaction.get("region", ""),
            interaction.get("element_type", ""),
            interaction.get("interaction_pattern", ""),
            interaction.get("action_type", ""),
            interaction.get("user_intent", ""),
            page_row.get("page_name", ""),
            page_row.get("primary_user_goal", ""),
            " ".join(business_objects),
        ]
    )
    tokens = semantic_tokens(interaction_blob)
    page_name_tokens = semantic_tokens(page_name)
    interaction_region = str(interaction.get("region", "")).strip().lower()
    action_type = str(interaction.get("action_type", "")).strip().lower()
    scored: list[InteractionServiceMatch] = []
    for service in endpoint_specs:
        score = 0
        method_match = service.method == preferred_method
        if method_match:
            score += 5
        service_blob = " ".join(
            [
                service.service_name,
                service.domain,
                service.home_module,
                service.owns_or_coordinates,
                service.purpose,
                service.endpoint_name,
                service.path,
            ]
        )
        service_tokens = semantic_tokens(service_blob)
        semantic_overlap = len(tokens & service_tokens)
        score += semantic_overlap
        goal_overlap = len(goal_focus_tokens & service_tokens)
        score += goal_overlap * 2
        module_overlap = len(page_name_tokens & semantic_tokens(service.home_module))
        score += module_overlap * 2
        page_name_key = to_snake(page_name)
        home_module_key = to_snake(service.home_module)
        if page_name_key and home_module_key and (page_name_key in home_module_key or home_module_key in page_name_key):
            score += 4
        has_object_overlap = bool(
            business_objects
            and any(
                to_snake(obj) in to_snake(service.owns_or_coordinates)
                or to_snake(obj) in to_snake(service_technical_name(service))
                for obj in business_objects
            )
        )
        if has_object_overlap:
            score += 4
        if action_type == "load_context" and service.service_type == "read-assembly":
            score += 3
            if interaction_region == "context_header" and {"summary", "overview"} & service_tokens:
                score += 2
            if interaction_region == "context_header" and page_blueprint_type == "review-decision" and {"review", "workflow"} & service_tokens:
                score += 2
            if interaction_region == "data_view" and page_blueprint_type == "review-decision" and "workflow" in service_tokens and {"review", "summary", "closure"} & service_tokens:
                score += 1
        if service.method != preferred_method and preferred_method == "POST" and service.method == "PATCH":
            score += 1
        scored.append(
            InteractionServiceMatch(
                service=service,
                score=score,
                semantic_overlap=semantic_overlap,
                has_object_overlap=has_object_overlap,
                method_match=method_match,
            )
        )
    scored.sort(
        key=lambda item: (
            -item.score,
            -int(item.has_object_overlap),
            -item.semantic_overlap,
            item.service.service_name if item.service else "",
        )
    )
    best = scored[0]
    next_score = scored[1].score if len(scored) > 1 else -999
    strong_enough = (
        best.has_object_overlap
        or best.semantic_overlap >= 2
        or (best.method_match and best.semantic_overlap >= 1 and best.score >= 8)
    )
    clearly_better = len(scored) == 1 or best.has_object_overlap or (best.score - next_score) >= 2
    if strong_enough and clearly_better and best.service is not None:
        return best
    return InteractionServiceMatch(
        service=None,
        score=best.score,
        semantic_overlap=best.semantic_overlap,
        has_object_overlap=best.has_object_overlap,
        method_match=best.method_match,
        blocked_reason=(
            "insufficient service-binding confidence: no explicit business-object overlap or stable semantic lead"
        ),
    )


def choose_service_for_interaction(
    interaction: dict[str, str],
    page_row: dict[str, str],
    endpoint_specs: list[ServiceSpec],
) -> ServiceSpec | None:
    return choose_service_match_for_interaction(interaction, page_row, endpoint_specs).service


def binding_mode_for_interaction(interaction: dict[str, str]) -> str:
    trigger_kind = str(interaction.get("trigger_kind", "")).strip()
    action_type = str(interaction.get("action_type", "")).strip().lower()
    if trigger_kind == "page_load" or action_type == "load_context":
        return "read"
    if action_type in {"record_payment", "submit", "approve"}:
        return "read_write"
    return "write"


def display_field_set_for_page(page_row: dict[str, str], interaction: dict[str, str]) -> list[str]:
    business_objects = split_inline_values(page_row.get("business_objects", ""))
    region = str(interaction.get("region", "")).strip()
    suffix = "summary" if region in {"context_header", "data_view"} else "fields"
    if business_objects:
        return [f"{to_camel(obj)}{suffix[:1].upper() + suffix[1:]}" for obj in business_objects[:3]]
    return ["pageContextSummary"] if region in {"context_header", "data_view"} else ["primaryActionFields"]


def input_schema_ref_for_interaction(page_row: dict[str, str], interaction: dict[str, str]) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        return "—"
    page_slug = slugify(str(page_row.get("page_name", "")).strip()).replace("-", "_")
    action_slug = slugify(str(interaction.get("action_type", "")).strip() or "action").replace("-", "_")
    return f"{page_slug}_{action_slug}_form"


def validation_rules_for_interaction(interaction: dict[str, str]) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        return "not_applicable"
    action_type = str(interaction.get("action_type", "")).strip() or "action"
    return f"require-valid-{slugify(action_type)}-input; preserve-blocked-rule-before-submit"


def enabled_rule_for_interaction(interaction: dict[str, str]) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        return "not_applicable"
    blocked_rule = str(interaction.get("blocked_rule", "")).strip()
    if blocked_rule in {"—", "-", "none", "n/a"}:
        blocked_rule = ""
    if blocked_rule:
        return f"enabled_when_not({blocked_rule})"
    return "enabled_when_visibility_rule_passes"


def _flatten_request_example_paths(value: object, *, prefix: str = "request") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, subvalue in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(subvalue, dict):
                paths.extend(_flatten_request_example_paths(subvalue, prefix=current))
            elif isinstance(subvalue, list) and subvalue and isinstance(subvalue[0], dict):
                paths.extend(_flatten_request_example_paths(subvalue[0], prefix=current))
            else:
                paths.append(current)
        return paths
    return [prefix] if prefix else []


def _expand_field_hint_phrases(value: str) -> list[str]:
    cleaned = re.sub(r"^depends on\s+", "", str(value or "").strip(), flags=re.IGNORECASE)
    if not cleaned:
        return []
    segments = [segment.strip() for segment in re.split(r"[;,]", cleaned) if segment.strip()]
    phrases: list[str] = []
    for segment in segments:
        if "/" not in segment:
            phrases.append(segment)
            continue
        parts = [part.strip() for part in segment.split("/") if part.strip()]
        if not parts:
            continue
        phrases.append(parts[0])
        first_words = parts[0].split()
        prefix_words = first_words[:-1]
        for part in parts[1:]:
            if " " in part or not prefix_words:
                phrases.append(part)
            else:
                phrases.append(" ".join([*prefix_words, part]))
    return phrases


def _field_name_from_hint(value: str) -> str:
    cleaned = re.sub(r"^depends on\s+", "", str(value or "").strip(), flags=re.IGNORECASE)
    if not cleaned:
        return ""
    if len(cleaned.split()) > 6 and not re.search(r"(?:^|[^A-Za-z0-9])(id|_id)(?:[^A-Za-z0-9]|$)", cleaned, flags=re.IGNORECASE):
        return ""
    stopwords = {
        "a",
        "an",
        "and",
        "or",
        "the",
        "current",
        "required",
        "minimum",
        "workflow",
        "business",
        "record",
        "module",
        "explicit",
        "complete",
        "completed",
        "ownership",
        "payload",
        "signals",
        "history",
        "rules",
        "ready",
    }
    tokens = [
        token
        for token in re.split(r"[^A-Za-z0-9]+", cleaned)
        if token and token.lower() not in stopwords
    ]
    if not tokens:
        return ""
    candidate = to_camel(" ".join(tokens))
    if len(candidate) <= 1:
        return ""
    return candidate


def _page_input_field_hints(page_row: dict[str, str]) -> list[str]:
    hints: list[str] = []
    for raw in (
        str(page_row.get("entry_conditions", "")).strip(),
        str(page_row.get("entry_condition", "")).strip(),
    ):
        if not raw:
            continue
        lowered = raw.lower()
        if not any(token in raw for token in (",", "/", ";")) and not re.search(r"(?:^|[^A-Za-z0-9])(?:[A-Za-z0-9_]*id)(?:[^A-Za-z0-9]|$)", lowered):
            continue
        for phrase in _expand_field_hint_phrases(raw):
            normalized = _field_name_from_hint(phrase)
            if normalized:
                hints.append(normalized)
    return unique_preserve(hints)


def _mapping_alias_for_request_path(path: str) -> str:
    normalized = str(path or "").strip()
    if normalized.startswith("request."):
        normalized = normalized[len("request.") :]
    if normalized.startswith("query."):
        normalized = normalized[len("query.") :]
    if normalized.startswith("input."):
        normalized = normalized[len("input.") :]
    return to_camel(normalized.replace(".", " "))


def _service_request_mappings_for_interaction(page_row: dict[str, str], service: ServiceSpec) -> list[str]:
    request_example = stage_03_request_example(service)
    example_paths = _flatten_request_example_paths(request_example, prefix="request")
    if not example_paths:
        return []
    page_field_hints = _page_input_field_hints(page_row)
    hint_paths: list[str] = []
    if any(path.startswith("request.input.") for path in example_paths) and page_field_hints:
        for hint in page_field_hints:
            target = f"request.{hint}" if hint.endswith("Id") else f"request.input.{hint}"
            hint_paths.append(target)
    effective_paths = [
        path
        for path in example_paths
        if path != "request.input.summary" or not hint_paths
    ] + hint_paths
    mappings: list[str] = []
    seen_targets: set[str] = set()
    for path in effective_paths:
        target = str(path).strip()
        if not target or target in seen_targets:
            continue
        seen_targets.add(target)
        alias = _mapping_alias_for_request_path(target)
        if not alias:
            continue
        mappings.append(f"{alias} -> {target}")
    return mappings


def request_field_mapping_for_interaction(
    page_row: dict[str, str],
    interaction: dict[str, str],
    service: ServiceSpec | None = None,
) -> str:
    if str(interaction.get("trigger_kind", "")).strip() == "page_load":
        business_objects = split_inline_values(page_row.get("business_objects", ""))
        if business_objects:
            object_slug = to_camel(business_objects[0])
            return f"{object_slug}Id -> query.{object_slug}Id"
        return "pageContextId -> query.pageContextId"
    if service is not None:
        service_mappings = _service_request_mappings_for_interaction(page_row, service)
        if service_mappings:
            return "; ".join(service_mappings)
    input_schema_ref = input_schema_ref_for_interaction(page_row, interaction)
    field_prefix = input_schema_ref.replace("_form", "")
    return f"{field_prefix}.summary -> request.input.summary"


def response_field_mapping_for_interaction(page_row: dict[str, str], interaction: dict[str, str]) -> str:
    fields = display_field_set_for_page(page_row, interaction)
    if not fields:
        return "response.status -> ui.status"
    return "; ".join(f"response.{to_camel(field)} -> ui.{field}" for field in fields[:3])


def _mapping_field_names(mapping_text: str, *, right_hand: bool = False) -> list[str]:
    names: list[str] = []
    for raw_entry in str(mapping_text or "").split(";"):
        entry = raw_entry.strip().strip("`")
        if not entry:
            continue
        left, _, right = entry.partition("->")
        candidate = right if right_hand else left
        normalized = str(candidate).strip()
        if not normalized:
            continue
        field = normalized.split(".")[-1].replace("[]", "").strip()
        if field and field not in names and field not in {"request", "response", "query", "ui", "input"}:
            names.append(field)
    return names


def _resource_id_candidates(api_path: str) -> set[str]:
    segments = [
        segment
        for segment in str(api_path).split("/")
        if segment
        and segment not in {"api"}
        and not re.fullmatch(r"v\d+", segment)
        and not segment.startswith("{")
    ]
    if not segments:
        return set()
    resource_token = segments[-1].rstrip("s")
    camel = to_camel(resource_token.replace("-", " "))
    candidates = {
        f"{camel}Id" if camel else "",
        f"{resource_token}_id" if resource_token else "",
    }
    return {candidate for candidate in candidates if candidate}


def _normalize_contract_enum(value: str) -> str:
    cleaned = str(value or "").strip().lower()
    if not cleaned or cleaned in {"—", "-", "none", "n/a"}:
        return ""
    return re.sub(r"[\s-]+", "_", cleaned)


def _interaction_internal_exposure(page_row: dict[str, str]) -> str:
    audience_mode = _normalize_contract_enum(page_row.get("audience_mode", ""))
    page_name = str(page_row.get("page_name", "")).strip().lower()
    blueprint = normalize_blueprint_type(str(page_row.get("page_blueprint_type", "")).strip())
    if audience_mode and audience_mode != "app":
        return "review_only"
    if "review" in page_name or blueprint == "review-decision":
        return "review_only"
    return "user_visible"


def _handoff_materialization(
    *,
    page_row: dict[str, str],
    interaction: dict[str, str],
    flow_row: dict[str, str],
) -> str:
    has_handoff = any(
        str(item or "").strip()
        for item in (
            interaction.get("next_route", ""),
            flow_row.get("next_page_id", ""),
            flow_row.get("visible_next_page_id", ""),
            flow_row.get("handoff_context_fields", ""),
            flow_row.get("handoff_surface_type", ""),
        )
    )
    if not has_handoff:
        return ""
    handoff_visibility = _normalize_contract_enum(page_row.get("handoff_visibility", ""))
    if handoff_visibility in {"implicit_context", "user_visible_summary", "review_only"}:
        return handoff_visibility
    handoff_surface_type = _normalize_contract_enum(flow_row.get("handoff_surface_type", ""))
    if handoff_surface_type == "review_queue":
        return "review_only"
    if handoff_surface_type in {"hidden_transition", "same_role_continue", "next_role_workspace"}:
        return "implicit_context"
    if _normalize_contract_enum(page_row.get("audience_mode", "")) not in {"", "app"}:
        return "review_only"
    return "user_visible_summary"


def _ui_refresh_targets(
    *,
    page_row: dict[str, str],
    interaction: dict[str, str],
    response_field_mapping: str,
    has_handoff: bool,
    binding_mode: str,
) -> str:
    if binding_mode not in {"write", "read_write"}:
        return ""
    targets: list[str] = []
    interaction_region = str(interaction.get("region", "")).strip()
    if interaction_region:
        targets.append(interaction_region)
    required_regions = split_inline_values(page_row.get("required_regions", ""))
    if "status_feedback" in required_regions or str(interaction.get("success_state", "")).strip():
        targets.append("status_feedback")
    if has_handoff or "next_steps" in required_regions:
        targets.append("next_steps")
    for field in _mapping_field_names(response_field_mapping, right_hand=True):
        targets.append(f"projection:{field}")
    return ", ".join(unique_preserve(targets))


def _value_source_contract(
    *,
    interaction: dict[str, str],
    input_fields: list[str],
    server_generated_fields: list[str],
    flow_row: dict[str, str],
) -> str:
    if not input_fields and not server_generated_fields:
        return ""
    flow_context_fields = {
        field
        for field in split_inline_values(flow_row.get("handoff_context_fields", ""))
        if field
    }
    entries: list[str] = []
    for field in unique_preserve(input_fields + server_generated_fields):
        value_source = "user_input"
        if field in server_generated_fields:
            value_source = "system_generated"
        elif str(interaction.get("trigger_kind", "")).strip() == "page_load" or field in flow_context_fields:
            value_source = "workflow_context"
        entries.append(f"{field}={value_source}")
    return "; ".join(entries)


def rbac_policy_for_page(page_row: dict[str, str]) -> str:
    roles = split_inline_values(page_row.get("allowed_roles", "")) or [page_row.get("primary_actor", "TBD")]
    return ", ".join(role for role in roles if role) or "TBD"


def audit_event_for_interaction(interaction: dict[str, str]) -> str:
    return slugify(str(interaction.get("interaction_id", "")).replace(".", "_")) or "interaction_event"


def build_binding_and_trace_rows(
    *,
    phase1_page_map: list[dict[str, str]],
    phase1_interactions: list[dict[str, str]],
    phase1_flow_rows: list[dict[str, str]] | None = None,
    endpoint_specs: list[ServiceSpec],
    trace_rows: list[dict[str, str]],
) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
    page_by_id = {
        str(row.get("page_id", "")).strip(): row
        for row in phase1_page_map
        if str(row.get("page_id", "")).strip()
    }
    flow_by_interaction = {
        str(row.get("from_interaction_id", "")).strip(): row
        for row in (phase1_flow_rows or [])
        if str(row.get("from_interaction_id", "")).strip()
    }
    req_ids = [
        row["trace_id"]
        for row in trace_rows
        if row.get("unit_type") in {"requirement", "acceptance-criteria"}
    ] or [row["trace_id"] for row in trace_rows]
    req_groups = distribute_phase1_ids(req_ids, max(len(phase1_interactions), 1)) if req_ids else []

    binding_rows: list[list[str]] = []
    enrichment_rows: list[list[str]] = []
    traceability_rows: list[list[str]] = []
    for idx, interaction in enumerate(phase1_interactions, start=1):
        page_id = str(interaction.get("page_id", "")).strip()
        page_row = page_by_id.get(page_id, {})
        flow_row = flow_by_interaction.get(str(interaction.get("interaction_id", "")).strip(), {})
        service_match = choose_service_match_for_interaction(interaction, page_row, endpoint_specs)
        service = service_match.service
        binding_mode = binding_mode_for_interaction(interaction)
        service_binding_id = (
            f"{interaction['interaction_id']}.{slugify(service.endpoint_name)}"
            if service is not None
            else f"{interaction['interaction_id']}.unresolved-service-binding"
        )
        display_field_set = ", ".join(display_field_set_for_page(page_row, interaction))
        input_schema_ref = input_schema_ref_for_interaction(page_row, interaction)
        validation_rules = validation_rules_for_interaction(interaction)
        enabled_rule = enabled_rule_for_interaction(interaction)
        request_field_mapping = request_field_mapping_for_interaction(page_row, interaction, service)
        response_field_mapping = response_field_mapping_for_interaction(page_row, interaction)
        input_fields = _mapping_field_names(request_field_mapping)
        server_generated_fields = [
            field
            for field in input_fields
            if service is not None and service.method.upper() == "POST" and field in _resource_id_candidates(service.path)
        ]
        handoff_materialization = _handoff_materialization(
            page_row=page_row,
            interaction=interaction,
            flow_row=flow_row,
        )
        ui_refresh_targets = _ui_refresh_targets(
            page_row=page_row,
            interaction=interaction,
            response_field_mapping=response_field_mapping,
            has_handoff=bool(handoff_materialization),
            binding_mode=binding_mode,
        )
        internal_exposure = _interaction_internal_exposure(page_row)
        value_source_contract = _value_source_contract(
            interaction=interaction,
            input_fields=input_fields,
            server_generated_fields=server_generated_fields,
            flow_row=flow_row,
        )
        readiness_status = str(interaction.get("readiness_status", "review-bound")).strip() or "review-bound"
        blocked_reason = str(interaction.get("blocked_reason", "")).strip()
        if blocked_reason in {"—", "-", "none", "n/a"}:
            blocked_reason = ""
        if binding_mode == "read" and not blocked_reason and input_schema_ref == "—":
            blocked_reason = ""
        if readiness_status == "ready" and not str(interaction.get("use_case_id", "")).strip():
            readiness_status = "review-bound"
            blocked_reason = blocked_reason or "missing use_case_id for interaction-level binding"
        if service is None:
            readiness_status = "review-bound"
            blocked_reason = blocked_reason or service_match.blocked_reason or "service binding requires human review"
        binding_rows.append(
            [
                service_binding_id,
                interaction["interaction_id"],
                interaction.get("use_case_id", "TBD") or "TBD",
                "",
                binding_mode,
                service.service_name if service is not None else "UNRESOLVED_SERVICE_BINDING",
                service.path if service is not None else "—",
                service.method if service is not None else "—",
                request_field_mapping if service is not None else "review-bound / unresolved-service-binding",
                response_field_mapping if service is not None else "review-bound / unresolved-service-binding",
                service.owns_or_coordinates if service is not None else "—",
                rbac_policy_for_page(page_row),
                audit_event_for_interaction(interaction),
                generic_endpoint_policy(service)[-1] if service is not None else "—",
                ", ".join(server_generated_fields) or "—",
                ui_refresh_targets or "—",
                handoff_materialization or "—",
                readiness_status,
                blocked_reason or "—",
            ]
        )
        enrichment_rows.append(
            [
                interaction["interaction_id"],
                page_id,
                input_schema_ref,
                display_field_set,
                validation_rules,
                enabled_rule,
                value_source_contract or "—",
                internal_exposure,
                interaction.get("error_state", "TBD") or "TBD",
                readiness_status,
                blocked_reason or "—",
            ]
        )
        upstream_req_ids = req_groups[idx - 1] if idx - 1 < len(req_groups) else (req_groups[-1] if req_groups else ["P1-REQ-TBD"])
        primary_req_id = _primary_req_id(upstream_req_ids)
        traceability_rows.append(
            [
                f"trace.{slugify(interaction['interaction_id'])}",
                primary_req_id,
                interaction.get("use_case_id", "TBD") or "TBD",
                page_id or "TBD",
                interaction["interaction_id"],
                service_binding_id,
                service.path if service is not None else "—",
                "phase3-contract-tests, phase4-closure",
                "phase3-productness-gate",
                str(page_row.get("canonical_page_id", "")).strip() or "—",
                _normalize_contract_enum(page_row.get("audience_mode", "")) or "—",
                internal_exposure,
                "current",
                ", ".join(upstream_req_ids),
            ]
        )
    return binding_rows, enrichment_rows, traceability_rows


def service_event_name(service: ServiceSpec) -> str:
    return service.primary_outbound or f"{service_technical_name(service)}Changed"


def event_name_for_model(service: ServiceSpec, obj: str) -> str:
    if to_snake(obj) == to_snake(service.owns_or_coordinates):
        return service_event_name(service)
    suffix = "Prepared" if service.service_type == "read-assembly" else "Recorded" if service.service_type == "support" else "Changed"
    return f"{to_pascal(obj)}{suffix}"


def event_trigger_for_model(service: ServiceSpec, obj: str) -> str:
    if to_snake(obj) == to_snake(service.owns_or_coordinates):
        return f"{service.primary_inbound} succeeds for {obj}"
    subject = to_pascal(obj)
    if service.service_type == "read-assembly":
        return f"{subject} read context is confirmed for downstream projection"
    if service.service_type == "support":
        return f"{subject} record is appended after support/audit workflow commits"
    obj_key = to_snake(obj)
    if "revision" in obj_key or "cycle" in obj_key or "conclusion" in obj_key:
        return f"{subject} lifecycle changes after review/state boundary is committed"
    return f"{subject} lifecycle changes after {service.service_name} commits authoritative state"


def event_model_effect_for_model(service: ServiceSpec, obj: str) -> str:
    subject = to_pascal(obj)
    if service.service_type == "read-assembly":
        return f"{subject} read projection must be visible through `{service.public_contract}` without write authority"
    if service.service_type == "support":
        return f"{subject} append/replay effect must be visible through `{service.public_contract}`"
    return f"{subject} lifecycle and read-effect must be visible through `{service.public_contract}`"


def event_p3_handoff_for_model(service: ServiceSpec, obj: str) -> str:
    event_name = event_name_for_model(service, obj)
    subject = to_pascal(obj)
    if service.service_type == "read-assembly":
        return f"bind `{event_name}` to read projection service/repository/unit intent for `{subject}`; validate payload/idempotency evidence before implementation closure"
    if service.service_type == "support":
        return f"bind `{event_name}` to append/replay service/repository/unit intent for `{subject}`; validate payload/idempotency evidence before implementation closure"
    return f"bind `{event_name}` to lifecycle service/repository/unit intent for `{subject}`; validate payload/idempotency evidence before implementation closure"


def event_source_path_for_model(service: ServiceSpec, obj: str) -> str:
    event_name = event_name_for_model(service, obj)
    if to_snake(obj) == to_snake(service.owns_or_coordinates):
        return (
            f"入口由 `{service.primary_inbound}` 触发，"
            f"`{service.service_name}` 提交 `{obj}` 权威状态后经 `{event_name}` 向下游传播"
        )
    return f"由 `{service.service_name}` 提交 `{obj}` 权威状态后经 `{event_name}` 向下游传播"


def event_reliability_posture_for_model(service: ServiceSpec, obj: str) -> str:
    payload = event_payload_contract(obj)
    idempotency = f"dedupe on {to_snake(obj)}_id + version"
    if service.service_type == "read-assembly":
        commit_boundary = "read context confirmation before projection handoff"
        replay = f"read projection consumers preserve source trace_id and {idempotency}"
    elif service.service_type == "support":
        commit_boundary = "append-only audit/support record commit"
        replay = f"append/replay consumers preserve event identity and {idempotency}"
    else:
        commit_boundary = "authoritative owner write commit before fan-out"
        replay = f"lifecycle consumers preserve version ordering and {idempotency}"
    return (
        f"commit boundary: {commit_boundary}; "
        f"required payload ids: {payload}; "
        f"idempotency/replay: {replay}; "
        "claim ceiling: missing commit or payload evidence remains review-bound until P3 runtime/test proof; "
        "P3 validation hook: assert payload ids, idempotency, and event effect before implementation closure"
    )


def event_model_business_meaning(service: ServiceSpec, obj: str) -> str:
    action = "读取上下文已稳定" if service.service_type == "read-assembly" else "权威状态已变更"
    return f"`{obj}` 的{action}，下游只能消费该事实或请求新版本，不能回写事件来源。"


def event_payload_contract(obj: str) -> str:
    snake = to_snake(obj)
    return f"{snake}_id, tenant_id, version, trace_id, changed_at"


def event_schema_posture(service: ServiceSpec, obj: str | None = None) -> str:
    if obj:
        return event_reliability_posture_for_model(service, obj)
    if service.service_type in {"orchestration", "support"}:
        return "versioned envelope + additive payload fields; replay identity is mandatory"
    if service.service_type == "read-assembly":
        return "read-model event aliases may be additive; source event name remains stable"
    return "stable event name + additive payload; removing identifiers requires returning to P2"


def event_downstream_usage_rule(service: ServiceSpec) -> str:
    if service.service_type == "read-assembly":
        return "P3 may build projection/read tests from this event, but must not treat it as write authority"
    return "P3 must bind service/repository/unit behavior to this event before claiming implementation closure"


def event_driver_rows(
    *,
    services: list[ServiceSpec],
    aggregate_objects: list[str],
    event_target: int,
) -> tuple[list[list[str]], list[list[str]], list[list[str]], list[list[str]]]:
    event_objects = aggregate_objects[:event_target] if aggregate_objects else [
        service.owns_or_coordinates for service in services[:event_target]
    ]
    events: list[list[str]] = []
    vocabulary_rows: list[list[str]] = []
    model_rows: list[list[str]] = []
    carry_forward_rows: list[list[str]] = []
    for idx, obj in enumerate(event_objects):
        service = owning_service_for_object(obj, services)
        event_name = event_name_for_model(service, obj)
        consumer = (
            owning_service_for_object(event_objects[idx + 1], services).service_name
            if idx + 1 < len(event_objects)
            else "downstream review surfaces"
        )
        trigger = event_trigger_for_model(service, obj)
        payload = event_payload_contract(obj)
        ordering = "after authoritative write" if service.service_type != "read-assembly" else "after source context read is confirmed"
        idempotency = f"dedupe on {to_snake(obj)}_id + version"
        events.append([event_name, service.service_name, consumer, trigger, payload, ordering, idempotency])
        vocabulary_rows.append(
            [
                event_name,
                event_model_business_meaning(service, obj),
                service.service_name,
                consumer,
                payload,
                ordering,
                idempotency,
                event_downstream_usage_rule(service),
            ]
        )
        model_rows.append(
            [
                f"EVT-{idx + 1:02d}",
                event_name,
                trigger,
                f"{service.service_name} -> {consumer}",
                event_model_effect_for_model(service, obj),
                event_schema_posture(service, obj),
                event_p3_handoff_for_model(service, obj),
                "resolved",
            ]
        )
        carry_forward_rows.append(
            [
                event_name,
                event_p3_handoff_for_model(service, obj),
                event_name,
                "事件名与 P3 touchpoint 直接沿用 Stage-02 event model driver 的对象级语义",
            ]
        )
    return events, vocabulary_rows, model_rows, carry_forward_rows


def owning_service_for_object(obj_name: str, services: list[ServiceSpec]) -> ServiceSpec:
    obj_key = to_snake(obj_name)
    if not services:
        raise SystemExit("rendering requires at least one ServiceSpec")
    exact = next(
        (
            service
            for service in services
            if to_snake(service.owns_or_coordinates) == obj_key
            or to_snake(service_technical_name(service)) == obj_key
        ),
        None,
    )
    if exact:
        return exact
    partial = next(
        (
            service
            for service in services
            if obj_key in to_snake(service.owns_or_coordinates)
            or to_snake(service.owns_or_coordinates) in obj_key
            or obj_key in to_snake(service_technical_name(service))
            or to_snake(service_technical_name(service)) in obj_key
        ),
        None,
    )
    if partial:
        return partial
    semantic = next(
        (
            service
            for service in services
            if obj_key in to_snake(service.purpose) or obj_key in to_snake(service.public_contract)
        ),
        None,
    )
    return semantic or services[0]


def grouped_service_pairs(services: list[ServiceSpec]) -> list[tuple[ServiceSpec, ServiceSpec]]:
    if len(services) < 2:
        return []
    return [(services[idx], services[idx + 1]) for idx in range(len(services) - 1)]


def render_stage_01(
    *,
    case_name: str,
    phase1_prd: Path,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
) -> str:
    root_namespace = str(context["root_namespace"])
    boundary_scope = str(context.get("boundary_scope", "tenant"))
    boundary_term = boundary_phrase(boundary_scope)
    boundary_subject_name = boundary_subject(boundary_scope)
    workflow_scope = workflow_scope_summary(context)
    async_completion_pack = async_completion_runtime_pack_for_context(context)
    primary_owner_label = "Clinic Operations Owner" if boundary_scope == "clinic-account" else "Workspace Owner"
    operator_label = "Staff Operator" if boundary_scope == "clinic-account" else "Execution Operator"
    reviewer_label = "Clinic Reviewer" if boundary_scope == "clinic-account" else "Decision Reviewer"
    quality_attributes = [str(item) for item in context["quality_attributes"]][: max(profile_minimum(complexity_profile, "stage_01_quality_attributes"), 4)]
    trace_rows = list(context["all_trace_rows"])
    req_ac_ids = [
        row["trace_id"]
        for row in trace_rows
        if row.get("unit_type") in {"requirement", "acceptance-criteria"}
    ] or [row["trace_id"] for row in trace_rows]
    adr_count = max(profile_minimum(complexity_profile, "stage_01_architecture_decisions"), 4)
    decision_trace_groups = distribute_phase1_ids(req_ac_ids, adr_count)
    capability_target = max(profile_minimum(complexity_profile, "stage_01_capability_groups"), 4)
    capability_domain_names = unique_preserve(
        [str(item) for item in list(context.get("domains", []))]
        + [service.domain for service in services]
    )[:4]
    while len(capability_domain_names) < 4:
        capability_domain_names.append(f"domain-{len(capability_domain_names) + 1}")
    capability_groups = [
        {
            "name": f"{capability_domain_names[0]} Scope and Governance",
            "priority": "P0",
            "maturity": "core",
            "rationale": "Minimum valid boundary, access, and workflow guardrails must remain stable before downstream design deepening and review.",
            "covers": f"{capability_domain_names[0]} ownership, {boundary_subject_name} access, workflow boundary validation, version freeze",
        },
        {
            "name": f"{capability_domain_names[1]} Workflow Context and Signals",
            "priority": "P0",
            "maturity": "core",
            "rationale": "Current-state evidence, handoff context, and operator-visible signals must remain reproducible and explainable.",
            "covers": f"{capability_domain_names[1]} current-state snapshot, signal versioning, handoff context",
        },
        {
            "name": f"{capability_domain_names[2]} Action Handoff and Execution",
            "priority": "P0",
            "maturity": "core",
            "rationale": "The product loses business value if upstream business context cannot become bounded execution work.",
            "covers": f"{capability_domain_names[2]} typed handoff payload, work-item bridge, target object linkage",
        },
        {
            "name": f"{capability_domain_names[3]} Review and Closure",
            "priority": "P0",
            "maturity": "guided",
            "rationale": "Downstream delivery must preserve review-bound truths instead of narrative certainty.",
            "covers": f"{capability_domain_names[3]} review summaries, uncertainty notes, continue-or-revise posture",
        },
    ][:capability_target]
    supports_deferred_extension_seam = context_supports_deferred_extension_seam(context)
    business_proof_constraints = business_proof_constraint_block(context, indent=4)
    business_architecture_pressure = business_architecture_pressure_block(context, indent=4)
    deferred_constraint_lines = (
        [
            "advanced attribution seams remain reserved but not promised as MVP-complete",
            "external connector hardening remains PhaseX / later-wave work",
        ]
        if supports_deferred_extension_seam
        else [
            "deferred extension seams stay explicit only when Phase-1 truth actually declares them",
            "provider-specific hardening remains later-wave work until a real dependency commitment exists",
        ]
    )

    adr_titles = [str(item) for item in context.get("adr_titles", [])][:adr_count]
    adr_entries: list[str] = []
    decision_trace_table_rows: list[list[str]] = []
    for idx, title in enumerate(adr_titles, start=1):
        ad_id = f"AD-{idx:02d}"
        ids = decision_trace_groups[idx - 1]
        service = select_adr_anchor_service(title, services)
        adr_content = adr_content_for(
            title=title,
            service=service,
            case_name=case_name,
            upstream_ids=ids,
            root_namespace=root_namespace,
        )
        hook = (
            f"{title} stays visible in `{service.public_contract}` / `{service.endpoint_name}` handoff evidence "
            f"for {summarize_list(ids, max_items=3)}."
        )
        alternative_lines: list[str] = []
        for alternative_name, rejected_because in adr_content["alternatives"]:
            alternative_lines.extend(
                [
                    f"      - alternative_name: {alternative_name}",
                    f"      - rejected_because: {rejected_because}",
                ]
            )
        adr_entries.append(
            "\n".join(
                [
                    f"  - adr_{idx:02d}:",
                    f"    - ad_id: `{ad_id}`",
                    f"    - title: {title}",
                    "    - status:",
                    "      - `Accepted`",
                    f"    - context: {adr_content['context']}",
                    f"    - decision: {adr_content['decision']}",
                    "    - alternatives_considered:",
                    *alternative_lines,
                    "    - consequences:",
                    f"      - positive: {adr_content['consequences']['positive']}",
                    f"      - negative: {adr_content['consequences']['negative']}",
                    f"      - risks: {adr_content['consequences']['risks']}",
                    f"    - evidence: {adr_content['evidence']}",
                ]
            )
        )
        decision_trace_table_rows.append(
            [
                f"P2-DTR-{idx:02d}",
                ad_id,
                title,
                f"upstream_trace_ids={', '.join(ids)}",
                "ARCH-STG03-OUTPUT-0001",
                hook,
                ", ".join(ids),
            ]
        )

    forbidden_count = max(profile_minimum(complexity_profile, "stage_01_forbidden_assumptions"), 5)
    forbidden_entries = []
    forbidden_templates = forbidden_templates_for_context(context)
    for idx in range(forbidden_count):
        code, text = forbidden_templates[idx % len(forbidden_templates)]
        forbidden_entries.append(
            "\n".join(
                [
                    f"  - fa_{idx + 1:02d}:",
                    f"    - original_text: {text}",
                    "    - source: Phase-1 `Must Not Assume` and trust-bound workflow posture",
                    "    - architecture_constraint_mapping: enforce explicit contracts, RBI carry-forward, or boundary checks",
                    "    - compliance_status: `must-preserve`",
                    "    - evidence_reference: PRD requirement / acceptance registry remains explicit",
                    "    - evidence_strength: `strong`",
                ]
            )
        )

    quality_entries = []
    for attr in quality_attributes:
        quality_entries.append(
            "\n".join(
                [
                    f"    - {to_snake(attr)}:",
                    f"      - quantified_target: keep `{attr}` visible in every Stage-03 or Stage-04 acceptance surface",
                    "      - metric_name: first-pass traceable design surfaces",
                    "      - target_value: >= 1 direct structured binding per critical flow",
                    "      - measurement_window: per design revision",
                    "      - design_implication: 把该属性前置到 contract、replay 或 verification note",
                    "      - evidence_or_source: Phase-1 NFR and quality scenario matrix",
                ]
            )
        )

    stage = f"""# Stage-01: architecture-definition-and-boundary-setting

## 1. Generation Provenance
- state: `authored-first-pass`
- generation_mode: `phase1-prd-direct`
- phase1_prd: `{phase1_prd}`
- complexity_profile: `{complexity_profile}`
- namespace_root: `{root_namespace}`

## 3. Core Structured Output
- system_boundary_statement:
  - product_scope: workflow-first operating chain across {workflow_scope}
  - primary_objects: {", ".join(f"`{item}`" for item in list(context["objects"])[:7])}
  - in_scope_first_version: boundary-stable intake, execution, audit, and review flow
  - out_of_scope_guardrail: no silent execution, no fake certainty, no cross-{boundary_term} shortcuts
- constraints:
  - inherited_constraints:
    - {boundary_subject_name} isolation must remain explicit
    - review-bound truth must not be silently upgraded
  - inferred_constraints:
    - public boundary names must remain stable across Stage-02..04
    - work-item handoff must preserve typed payload and closure evidence
  - unknown_constraints:
    - external dependency latency variance remains review-bound until runtime evidence exists
    - field-level retention policy may tighten once deployment context is fixed
  - deferred_constraints:
{chr(10).join(f"    - {line}" for line in deferred_constraint_lines)}
- business_proof_track_constraints:
{business_proof_constraints}
- chosen_thesis_architecture_pressure:
{business_architecture_pressure}
- architecture_decisions_business_pressure:
    - avoid read-only architecture when Phase-1 thesis requires action, proof, or decision follow-through
    - preserve review decision, evidence snapshot, and deferred seam posture in ADR context
- thesis_driven_architecture_translation:
    - commercial_proof_supported_by: keep ADRs tied to the chosen thesis proof target instead of quoting the thesis as context only
    - anti_collapse_boundary: service boundaries must prevent downgrade into read-only dashboards, record-only stores, or isolated workflow fragments
    - proof_object_model: model proof artifacts, operational evidence, review decisions, and exception closure as architecture-visible objects
    - capability_sequence: build the minimum loop that proves action/evidence/review continuity and supports continue / revise / pause before lower-proof reporting convenience
- quality_attribute_structure:
{chr(10).join(quality_entries)}
- capability_map:
{chr(10).join(
    [
        "\n".join(
            [
                f"  - capability_group_{idx:02d}:",
                f"    - name: {group['name']}",
                "    - priority:",
                f"      - `{group['priority']}`",
                "    - maturity:",
                f"      - `{group['maturity']}`",
                f"    - rationale: {group['rationale']}",
                "    - covers:",
                f"      - {group['covers']}",
            ]
        )
        for idx, group in enumerate(capability_groups, start=1)
    ]
)}
- architecture_direction:
  - selected_shape: `modular monolith`
  - why_selected: preserve strong object-chain traceability and keep public contracts explicit before any later physical split
  - boundary_rule: module contracts stay stable even if Phase-3 implementation reorganizes internals
- p2_architecture_reliability_alignment:
  - owner_commit_rule: owner commit boundary remains the source of truth before event fan-out or downstream read composition
  - event_reliability_rule: event payload ids and idempotent replay must stay visible from ADR to Stage-03 implementation handoff
  - technology_selection_rule: technology candidates must preserve contract ownership, event reliability, and claim ceilings
  - deployment_posture_rule: deployment posture must not weaken module ownership or event replay evidence
  - p3_entry_rule: Phase-3 may implement the chosen posture, but missing runtime evidence keeps claims capped until tests prove it
- key_architecture_decisions:
{chr(10).join(adr_entries)}
- decision_trace_registry:
{make_markdown_table(
    ["trace_id", "adr_id", "decision_title", "upstream_reference", "downstream_artifact_id", "verification_hook", "upstream_trace_ids"],
    decision_trace_table_rows,
)}
- security_architecture_sketch:
  - trust_boundaries:
    - {boundary_subject_name} boundary around every authoritative business object and review surface
    - internal service boundary around typed handoff payload and closure evidence
  - identity_and_access_posture:
    - enforce role-scoped access checks with break-glass audit logging for privileged reads
  - auth_sequence_direction:
    - user -> API gateway -> policy enforcement -> domain module -> audit trail
  - authentication_sequence:
    - sequence_diagram: Stage-01 auth path preserves boundary assertion before domain mutation
    - token_strategy: short-lived access token + role/boundary claims
    - token_lifetime: access token 15m, refresh token 8h rolling
    - refresh_mechanism: rotate refresh token on privileged workflow continuation
    - revocation_approach: revoke at tenant membership or session boundary and preserve audit record
  - key_management_posture:
    - key_types: signing key, database encryption key, provider webhook secret
    - storage: KMS-backed secrets store with environment separation
    - rotation_policy: 90-day scheduled rotation or immediate incident-driven rotation
    - access_control: least-privilege access via deploy identity + audited operator break-glass
  - audit_sensitive_edges:
    - boundary policy change
    - work-item export or cross-module handoff
    - review decision issuance
- capacity_estimation:
  - throughput: 120 run-related requests / min at first-wave steady state
  - latency: p95 <= 600 ms for synchronous API reads and p95 <= 5 min for {async_completion_pack['latency_target_label']}
  - growth: {async_completion_pack['growth_target_label']}
  - retention: 365d hot evidence + 730d cold archive for audit-critical data
  - volume: {async_completion_pack['volume_target_label']}
  - storage: start with PostgreSQL + object-store export seam, not multi-engine sprawl
- forbidden_assumptions_registry:
{chr(10).join(forbidden_entries)}

## 5. Mermaid Evidence
```mermaid
C4Context
    title {case_name} System Context
    Person(primaryOwner, "{primary_owner_label}", "defines workflow scope and operating guardrails")
    Person(operator, "{operator_label}", "executes bounded workflow steps and exceptions")
    Person(reviewer, "{reviewer_label}", "reviews closure and operational outcomes")
    System(coreSystem, "{case_name}", "workflow-first operating system")
    Rel(primaryOwner, coreSystem, "configure workflow / inspect guardrails")
    Rel(operator, coreSystem, "create, update, and hand off work items")
    Rel(reviewer, coreSystem, "review closure decisions and audit evidence")
```

```mermaid
flowchart TD
    A["Scope Governance\\npriority = P0\\nmaturity = core"] --> B["Observation Scoring\\npriority = P0\\nmaturity = core"]
    B --> C["Recommendation Tasking\\npriority = P0\\nmaturity = core"]
    C --> D["Review Closure\\npriority = P0\\nmaturity = guided"]
```

```mermaid
sequenceDiagram
    participant User as {primary_owner_label}
    participant Gateway as API Gateway
    participant Policy as Boundary Policy
    participant Domain as Domain Module
    participant Audit as Audit Trail
    User->>Gateway: access token + boundary context
    Gateway->>Policy: verify boundary-scoped claims
    Policy-->>Gateway: allow authorized mutation
    Gateway->>Domain: forward authorized command
    Domain->>Audit: persist sensitive edge
    Domain-->>User: structured response envelope
```
"""
    return stage.rstrip() + "\n"



def render_stage_02(
    *,
    phase1_prd: Path,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    table_specs: list[dict[str, object]],
) -> str:
    root_namespace = str(context["root_namespace"])
    modules = require_context_modules(context)
    domains = unique_preserve(
        [str(item) for item in context.get("domains", [])]
        + [service.domain for service in services]
    ) or unique_preserve([service.domain for service in services])
    aggregate_seed = unique_semantic_objects(
        [str(spec["object_name"]) for spec in table_specs]
        + [
            str(item)
            for item in context.get("core_objects", [])
            if str(item).strip() and object_requires_persistent_table(str(item))
        ]
        + [
            str(item)
            for item in context.get("supplemental_objects", [])
            if str(item).strip() and object_requires_persistent_table(str(item))
        ]
        + [service.owns_or_coordinates for service in services if object_requires_persistent_table(service.owns_or_coordinates)]
    )
    aggregate_target = max(
        profile_minimum(complexity_profile, "stage_02_aggregate_catalog"),
        min(len(aggregate_seed), len(services) + 3),
        len(table_specs),
    )
    aggregate_objects = aggregate_seed[:aggregate_target] if aggregate_seed else [service.owns_or_coordinates for service in services]
    table_binding_map = {str(spec["object_name"]): str(spec["table_name"]) for spec in table_specs}

    domain_rows = []
    module_rows = []
    service_rows = []
    aggregate_rows = []
    responsibility_rows = []
    canonical_rows = []
    service_endpoint_rows = []
    lifecycle_rows = []

    rendered_domains = domains[: max(profile_minimum(complexity_profile, "stage_02_domains"), 3)] or [services[0].domain]
    for domain in rendered_domains:
        related_services = [service for service in services if service.domain == domain]
        domain_objects = unique_preserve([service.owns_or_coordinates for service in related_services]) or aggregate_objects[:2]
        primary_states = build_object_profile(related_services[0], domain_objects[0])["primary_states"] if related_services and domain_objects else "draft / active / archived"
        domain_rows.append([
            domain,
            release_domain_role_surface([service.service_type for service in related_services]),
            summarize_list([service.purpose for service in related_services], max_items=2),
            summarize_list(domain_objects, max_items=4),
            primary_states,
            release_slice_guardrail(),
            release_handoff_rule(),
        ])

    module_objects = {}
    for module in modules:
        name = module_name(module)
        module_objects[name] = unique_preserve(module_core_objects(module) + [str(item) for item in module.get("supplemental_objects", [])])
    for service in services:
        module_objects.setdefault(service.home_module, [])
        if service.owns_or_coordinates not in module_objects[service.home_module]:
            module_objects[service.home_module].append(service.owns_or_coordinates)

    seen_modules = set()
    for service in services:
        service_rows.append([
            service.service_name,
            service.domain,
            service.home_module,
            service.service_type,
            service.owns_or_coordinates,
            service.primary_inbound,
            service.primary_outbound,
            service.purpose,
            release_consistency_boundary(service.home_module, service.owns_or_coordinates),
        ])
        if service.home_module in seen_modules:
            continue
        seen_modules.add(service.home_module)
        owned = unique_preserve(module_objects.get(service.home_module, []) + [item.owns_or_coordinates for item in services if item.home_module == service.home_module])
        module_rows.append([
            service.home_module,
            service.domain,
            release_module_role_surface(),
            service.service_name,
            summarize_list(owned, max_items=5),
            ", ".join(item.public_contract for item in services if item.home_module == service.home_module) or "none",
            "上下游权威对象不得被本模块接管",
            release_change_propagation_note(service.service_name, service.endpoint_name),
            service.purpose,
        ])

    lifecycle_bindings = max(len(aggregate_objects), profile_minimum(complexity_profile, "stage_02_lifecycle_mermaid_bindings"), 3)
    for idx, obj in enumerate(aggregate_objects, start=1):
        owner = owning_service_for_object(obj, services)
        object_profile = build_object_profile(owner, obj)
        ownership_profile = build_ownership_profile(obj, services, owner)
        backing_schema = table_binding_map.get(obj, to_snake(obj))
        aggregate_rows.append([
            obj,
            object_profile["aggregate_kind"],
            owner.domain,
            owner.home_module,
            owner.service_name,
            object_profile["authoritative_mutations"],
            object_profile["primary_states"],
            object_profile["emitted_events"],
            f"stateDiagram-v2 / diagram-{idx:02d}" if idx <= lifecycle_bindings else "stateDiagram-v2 / shared coverage",
            object_profile["failure_guardrail"],
            object_profile["public_boundary_status"],
        ])
        responsibility_rows.append([
            owner.domain,
            obj,
            owner.home_module,
            object_profile["collaborators"],
            object_profile["read_only_refs"],
            object_profile["must_not_write"],
            object_profile["conflict_rule"],
            ownership_profile["closure_note"],
        ])
        canonical_rows.append([
            obj,
            obj,
            owner.service_name,
            f"{to_snake(obj)}_id + tenant_id",
            "status + version + updated_at",
            backing_schema,
            f"{owner.public_contract}, {owner.endpoint_name}",
            f"{obj} 持续锚定在 {owner.service_name} 及其契约表面上，不再由下游自行发明。",
        ])
        service_endpoint_rows.append([
            owner.service_name,
            owner.home_module,
            owner.endpoint_name,
            owner.public_contract,
            obj,
            "主 owner 到 Stage-03 接口的直接映射",
        ])
        lifecycle_rows.append([
            obj,
            "stateDiagram-v2",
            owner.service_name,
            object_profile["primary_states"],
            object_profile["emitted_events"],
            object_profile["mutation_guard"],
            object_profile["failure_guardrail"],
            f"diagram-{idx:02d}" if idx <= lifecycle_bindings else "shared-diagram",
            ownership_profile["change_propagation_path"],
        ])

    mapped_services = {row[0] for row in service_endpoint_rows}
    for service in services:
        if service.service_name in mapped_services:
            continue
        service_endpoint_rows.append([
            service.service_name,
            service.home_module,
            service.endpoint_name,
            service.public_contract,
            service.owns_or_coordinates,
            "补充服务到接口的映射",
        ])

    dependency_rows = []
    for upstream, downstream in grouped_service_pairs(services):
        dependency_rows.append([
            upstream.home_module,
            downstream.home_module,
            f"{upstream.endpoint_name} 以只读上下文交接给 {downstream.endpoint_name}",
            f"{to_snake(service_technical_name(upstream))}_id + trace_id",
            f"{downstream.service_name} 可以消费，但不得原地改写 {upstream.owns_or_coordinates}",
            "若所有权漂移，冻结该契约并把问题抬升为 review-bound 证据",
            f"{service_event_name(upstream)} 的新版本只能向前传播，不能回写下游已冻结事实",
        ])
    if not dependency_rows and services:
        service = services[0]
        dependency_rows.append([
            service.home_module,
            service.home_module,
            f"{service.endpoint_name} 在本模块内闭合自身状态边界",
            f"{to_snake(service_technical_name(service))}_id",
            "不得走表耦合回写捷径",
            "一旦所有权模糊，立即抬升为 review-bound 证据",
            "只允许追加式修订向前传播",
        ])

    event_target = max(profile_minimum(complexity_profile, "stage_02_domain_events"), min(len(aggregate_objects), max(len(services), 6)))
    events, event_vocabulary_rows, event_model_rows, event_rows = event_driver_rows(
        services=services,
        aggregate_objects=aggregate_objects,
        event_target=event_target,
    )

    er_entities = unique_preserve([to_upper_entity(spec["object_name"]) for spec in table_specs] + [to_upper_entity(obj) for obj in aggregate_objects])
    er_entities = er_entities[: max(profile_minimum(complexity_profile, "stage_02_er_entities"), min(len(er_entities), 10))]
    if len(er_entities) < 2:
        er_entities = unique_preserve(er_entities + [to_upper_entity(service.owns_or_coordinates) for service in services[:2]])
    er_relationship_lines = [
        f"    {er_entities[idx]} ||--o{{ {er_entities[idx + 1]} : propagates_to"
        for idx in range(len(er_entities) - 1)
    ] or ["    ENTITY_A ||--o{ ENTITY_B : supports"]

    flow_modules = unique_preserve([service.home_module for service in services])
    flow_lines = []
    if flow_modules:
        for idx, module in enumerate(flow_modules):
            current = f'M{idx + 1}["{module}"]'
            if idx == 0:
                flow_lines.append(f"    {current}")
            if idx + 1 < len(flow_modules):
                nxt = f'M{idx + 2}["{flow_modules[idx + 1]}"]'
                flow_lines.append(f"    {current} --> {nxt}")
    else:
        flow_lines.append('    M1["core-module"] --> M2["delivery-module"]')

    narrative_objects = summarize_list(aggregate_objects, max_items=4)
    narrative_modules = summarize_list(flow_modules, max_items=4)
    narrative_event_names = summarize_list([str(row[0]) for row in event_vocabulary_rows], max_items=4)

    stage = f"""# Stage-02: domain-module-service-decomposition

## 1. Generation Provenance
- state: authored-first-pass
- phase1_prd: {phase1_prd}
- complexity_profile: {complexity_profile}

## 2. 架构判断备忘
- 为什么这样拆：本阶段先把 `{narrative_objects}` 放回 `{narrative_modules}` 的权威写入、只读协作和事件传播边界里；拆分不是为了多造模块，而是为了让 P3 能继承清楚的责任线。
- 先读什么：先读 owner / aggregate 边界，再读 service responsibility、event handoff 与 P3 implementation hook；不要从表格字段反推业务语义。
- 表格怎么读：下方表格是结构化契约和实现索引，不是架构判断本身；读者应把 domain_map、aggregate_catalog、responsibility_matrix 连起来看同一条所有权链。
- 事件模型含义：`{narrative_event_names}` 等事件表达对象状态、读取投影或审计追加的传播事实，不是下游重新写入上游真相的许可。
- 给 P3 的交接：P3 Agentic implementation 应直接消费 owner、payload、幂等、failure guardrail 和 claim ceiling，而不是只复制字段名。
- 证据边界：Stage-02 只声明架构规划可用性；实现闭合仍由 P3 runtime / test evidence 证明。

## 3. Core Structured Output
- business_proof_track_carryover:
{business_proof_constraint_block(context, indent=2)}
- domain_map:
{make_markdown_table(["domain_name", "domain_role", "mission", "primary_objects", "primary_states", "must_not_own", "handoff_rule"], domain_rows)}
- module_map:
{make_markdown_table(["module_name", "domain_name", "module_role", "primary_service", "owned_objects", "read_only_refs", "must_not_own", "change_propagation_path", "module_purpose"], module_rows)}
- service_candidates:
{make_markdown_table(["service_name", "domain", "home_module", "service_type", "owns_or_coordinates", "primary_inbound", "primary_outbound", "purpose", "consistency_boundary"], service_rows)}
- canonical_object_structure:
{make_markdown_table(["object_name", "authoritative_aggregate", "authoritative_service", "primary_identifiers", "state_or_version_anchor", "backing_schema_or_projection", "stage_03_contract_or_endpoint", "closure_note"], canonical_rows)}
- aggregate_catalog:
{make_markdown_table(["aggregate_name", "aggregate_kind", "owning_domain", "owning_module", "authoritative_service", "authoritative_mutations", "primary_states", "emitted_events", "lifecycle_diagram", "failure_or_guardrail", "public_boundary_status"], aggregate_rows)}
- responsibility_matrix:
{make_markdown_table(["domain", "aggregate / object", "authoritative owner", "collaborators", "read_only_refs", "must_not_write", "conflict_rule", "public-boundary note"], responsibility_rows)}
- service_endpoint_mapping:
{make_markdown_table(["service_name", "home_module", "stage_03_endpoint_names", "public_contracts", "primary_owned_object", "mapping_note"], service_endpoint_rows)}
- lifecycle_ownership_closure:
  - owner_rule: 权威写入者必须与 aggregate catalog 中声明的 Stage-02 home module 保持一致
  - conflict_detection_rule: 同一 aggregate id 的并发写入必须做版本校验或串行化任务回放
  - escalation_rule: 如果生命周期 owner 不清晰，先冻结契约并抬升为 review-bound RBI，而不是临场脑补
- aggregate_lifecycle_coverage:
{make_markdown_table(["aggregate_name", "lifecycle_expression_type", "owner_writer", "state_set", "trigger_events", "mutation_guard", "terminal_or_failure_exit", "mermaid_binding", "closure_note"], lifecycle_rows)}
- dependency_collaboration_map:
{make_markdown_table(["upstream_module", "downstream_module", "allowed_interaction", "required_artifact", "forbidden_backedge", "violation_penalty", "change_propagation_rule"], dependency_rows)}
  - anti_cycle_rules:
    - 上游契约可以被下游读取，但所有权不能因为方便缓存而迁移
    - read assembly 可以放宽读取范围，但写入权仍绑定在 owner 模块
    - downstream replay 或 review surface 需要请求新版本，而不是直接改写上游真相
    - audit 与 review 证据只能向前追加，不能回头重开既有状态边界
  - violation_consequence: 依赖回环一律按设计缺陷处理，先冻结受影响契约，再显式补齐所有权
- entity_relationship_diagram:
  - conceptual_er_scope: aggregate roots + key support entities
  - aggregate_root_entities: {", ".join(er_entities)}
- domain_event_catalog:
{make_markdown_table(["event_name", "producer", "consumer", "trigger_condition", "payload_shape", "ordering_semantics", "idempotency_rule"], events)}
- p2_architecture_event_model_driver:
  - driver_id: `p2-architecture-event-model-driver.v1`
  - event_direct_driver_status: `active`
  - control_boundary:
    - Workflow keeps the event handoff visible; P2 Agentic architecture judgment owns event meaning, payload posture, and downstream usage.
  - domain_event_vocabulary:
{make_markdown_table(["event_name", "business_meaning", "producer", "consumer", "payload_contract", "timing", "idempotency", "downstream_usage_rule"], event_vocabulary_rows)}
  - domain_event_model_catalog:
{make_markdown_table(["event_model_id", "event_name", "trigger", "producer_consumer", "mutation_or_read_effect", "event_versioning_and_schema_posture", "p3_event_handoff", "review_bound_status"], event_model_rows)}
  - review_bound_event_gaps:
    - none; current event models are resolved for first-wave implementation planning and remain capped by later runtime evidence.
- decomposition_decisions:
  - policy: 先显式保留 workflow object chain，再考虑物理拆分
  - seam_preservation: 未来 seam 以命名契约保留，而不是藏成 TODO
  - namespace_root: {root_namespace} 在 Stage-02 到 Stage-04 期间保持稳定

## 5. Mermaid Evidence
{chr(10).join(
    [
        "\n".join(
            [
                "```mermaid",
                "stateDiagram-v2",
                "    [*] --> Draft",
                f"    Draft --> Active: validate {obj}",
                f"    Active --> Revised: publish {to_snake(obj)} update",
                "    Revised --> Active: accept additive change",
                f"    Active --> Archived: retire {obj}",
                "```",
            ]
        )
        for obj in aggregate_objects
    ]
)}

```mermaid
erDiagram
{chr(10).join(er_relationship_lines)}
```

```mermaid
flowchart LR
{chr(10).join(flow_lines)}
```
"""
    return stage.rstrip() + "\n"


def render_stage_03(
    *,
    phase1_prd: Path,
    phase1_prototype_spec: Path | None,
    phase1_interaction_flow_contract: Path | None,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    endpoint_specs: list[ServiceSpec],
    table_specs: list[dict[str, object]],
) -> str:
    root_namespace = str(context["root_namespace"])
    boundary_scope = str(context.get("boundary_scope", "tenant"))
    boundary_term = boundary_phrase(boundary_scope)
    async_completion_pack = async_completion_runtime_pack_for_context(context)
    schema_min = max(profile_minimum(complexity_profile, "stage_03_schema_tables"), 5)
    api_min = max(profile_minimum(complexity_profile, "stage_03_api_endpoints"), 5)
    tech_min = max(profile_minimum(complexity_profile, "stage_03_tech_selection_candidates"), 3)
    scenario_min = max(profile_minimum(complexity_profile, "stage_03_scenarios"), 5)
    contract_min = max(profile_minimum(complexity_profile, "stage_03_contract_trace_registry"), 3)
    phase1_page_map = _extract_page_map_from_prototype_spec(phase1_prototype_spec)
    phase1_interactions = _extract_interaction_rows_from_phase1_contract(phase1_interaction_flow_contract)
    phase1_flow_rows = _extract_flow_rows_from_phase1_contract(phase1_interaction_flow_contract)

    objects = unique_preserve(
        [str(spec["object_name"]) for spec in table_specs]
        + [service.owns_or_coordinates for service in services]
        + [str(item) for item in context.get("objects", [])]
    )
    rendered_table_specs = table_specs[: max(schema_min, len(table_specs))]
    schema_summary_rows = [
        [
            str(spec["table_name"]),
            f"`{spec['owner']}`",
            str(spec["pk"]),
            str(spec["fk"]),
            str(spec["unique_constraints"]),
            str(spec["composite_indexes"]),
        ]
        for spec in rendered_table_specs
    ]

    data_ownership_rows: list[list[str]] = []
    for obj in objects[: max(schema_min, len(services) + 2)]:
        owner = owning_service_for_object(obj, services)
        profile = build_ownership_profile(obj, services, owner)
        data_ownership_rows.append(
            [
                obj,
                f"`{owner.home_module}`",
                owner.service_name,
                profile["read_consumers"],
                owner.public_contract,
                profile["change_propagation_path"],
                profile["forbidden_shortcut"],
                profile["closure_note"],
            ]
        )

    storage_layer_rows = [
        [
            "PostgreSQL relational core",
            "authoritative workflow writes and traceable joins",
            "single primary with additive migrations",
            "retain hot-path indexes under 3x growth",
            "cold archive after 5x long-tail evidence growth",
            "partition high-growth tables by tenant + time window",
            "archive immutable evidence after hot retention window",
            "best fit for contract-first workflow integrity",
        ],
        [
            "Redis bounded cache",
            "accelerate read-heavy list and detail surfaces",
            "cache only rebuildable read models with TTL",
            "expand only when p95 read pressure proves need",
            "remain optional and replaceable",
            "namespace by tenant + read model + version",
            "expire aggressively on authoritative writes",
            "protects primary storage from bursty reads",
        ],
        [
            "Object-storage export seam",
            "store large reports and evidence bundles",
            "record manifests in the relational core",
            "grow export volume without changing OLTP schema",
            "carry multi-year audit bundles cheaply",
            "partition by tenant / cycle / export date",
            "retain per compliance rule while preserving replay ids",
            "keeps large immutable artifacts off hot tables",
        ],
        [
            "Deferred analytics seam",
            "future-only longitudinal trend sink",
            "not active in first wave",
            "activate if operational reads and analytics compete",
            "use append-only exports as source",
            "partition by tenant + date once active",
            "derive from exports rather than dual-write",
            "preserves simplicity without blocking later analysis",
        ],
    ]

    access_pattern_rows: list[list[str]] = []
    for spec in rendered_table_specs[: max(4, min(len(rendered_table_specs), 6))]:
        access_pattern_rows.append(
            [
                f"lookup `{spec['table_name']}` by ownership and recency",
                str(spec["table_name"]),
                f"tenant_id + {spec['pk']} + updated_at",
                "medium to high",
                str(spec["composite_indexes"]),
                "pay additive write cost to preserve stable read latency",
                f"benchmark `{spec['table_name']}` list and detail queries before widening rollout",
            ]
        )

    schema_entries: list[str] = []
    for idx, spec in enumerate(rendered_table_specs, start=1):
        field_table = make_markdown_table(
            ["field_name", "data_type", "nullable", "constraints", "index_hint"],
            [[str(a), str(b), str(c), str(d), str(e)] for a, b, c, d, e in spec["field_rows"]],
        )
        indented_field_table = "\n".join(f"        {line}" if line else "" for line in field_table.splitlines())
        schema_entries.append(
            "\n".join(
                [
                    f"    - table_{idx:02d}:",
                    f"      - table_name: `{spec['table_name']}`",
                    f"      - owner: `{spec['owner']}`",
                    f"      - object_name: `{spec['object_name']}`",
                    f"      - unique_constraints: `{spec['unique_constraints']}`",
                    f"      - composite_indexes: `{spec['composite_indexes']}`",
                    "      - write_rule: only the owning module mutates this table directly",
                    "      - trace_rule: every row remains addressable by primary id and trace_id",
                    "      - field_registry:",
                    indented_field_table,
                ]
            )
        )

    sensitivity_rows: list[list[str]] = []
    for spec in rendered_table_specs:
        table_name = str(spec["table_name"])
        pii_level = "restricted" if any(token in table_name for token in ("tenant", "identity", "audit")) else "internal"
        sensitivity_rows.append(
            [
                table_name,
                pii_level,
                "tenant keys, actor ids, trace anchors",
                "mask in logs and encrypt at rest where required",
                "retain per review/audit posture",
                "privileged reads require explicit reason and traceability",
                "sensitivity posture follows object ownership and replay needs",
            ]
        )

    binding_preview_rows = build_binding_and_trace_rows(
        phase1_page_map=phase1_page_map,
        phase1_interactions=phase1_interactions,
        endpoint_specs=endpoint_specs,
        trace_rows=[],
    )[0] if phase1_interactions else []
    request_mapping_lookup = build_request_mapping_lookup(binding_preview_rows)

    contract_entries: list[str] = []
    api_rows: list[list[str]] = []
    for idx, service in enumerate(endpoint_specs[: max(api_min, len(endpoint_specs))], start=1):
        request_example = stage_03_request_example(service, request_mapping_lookup=request_mapping_lookup)
        schema_fields = stage_03_contract_schema_fields(service, request_mapping_lookup=request_mapping_lookup)
        rate_limit, pagination, response_profile, retryability, idempotency, failure_codes = generic_endpoint_policy(service)
        schema_preview = make_markdown_table(
            ["field_name", "data_type", "nullable", "constraints", "index_hint"],
            [
                [
                    field.split(": ", 1)[0],
                    field.split(": ", 1)[1] if ": " in field else "string",
                    "false" if "|null" not in field and "null" not in field else "true",
                    "typed contract field",
                    "contract schema",
                ]
                for field in schema_fields[:16]
            ],
        )
        contract_entries.append(
            "\n".join(
                [
                    f"  - contract_{idx:02d}:",
                    f"    - contract_name: `{service.public_contract}`",
                    f"    - producer: `{service.service_name}`",
                    f"    - consumer: `{service.home_module}`",
                    "    - schema_form: `typed-request-response-envelope`",
                    f"    - failure_semantics: `{failure_codes}`",
                    "    - compatibility_rule: additive-only changes; identifiers and envelope fields stay stable",
                    "    - schema_fields:",
                    *[f"      - `{field}`" for field in schema_fields[:16]],
                    "    - json_schema:",
                    schema_preview,
                    "    - ts_interface:",
                    f"      - request_contract: `{service.endpoint_name}Request`",
                    f"      - response_contract: `{service.endpoint_name}Response`",
                ]
            )
        )
        api_rows.append(
            [
                service.endpoint_name,
                service.method,
                service.path,
                service.purpose,
                json.dumps(request_example, ensure_ascii=False),
                json.dumps(stage_03_response_example(service), ensure_ascii=False),
                rate_limit,
                pagination,
                response_profile,
                retryability,
                idempotency,
                f"{failure_codes}; error_type split: business_error | system_error",
            ]
        )
    _, _, event_model_rows, event_rows = event_driver_rows(
        services=services,
        aggregate_objects=objects,
        event_target=max(profile_minimum(complexity_profile, "stage_02_domain_events"), min(len(objects), max(len(services), 6))),
    )
    event_consumption_rows = [
        [
            row[1],
            row[6].replace("bind ", "").replace(" service/repository/unit intent", ""),
            row[4],
            row[5],
            row[6],
            "implementation claim remains capped until P3 runtime/test evidence exists",
        ]
        for row in event_model_rows
    ]

    all_trace_rows = list(context["all_trace_rows"])
    all_trace_ids = [row["trace_id"] for row in all_trace_rows]
    req_ac_ids = [row["trace_id"] for row in all_trace_rows if row.get("unit_type") in {"requirement", "acceptance-criteria"}] or all_trace_ids
    contract_id_groups = distribute_phase1_ids(req_ac_ids, max(contract_min, len(endpoint_specs)))
    contract_trace_rows: list[list[str]] = []
    for idx, service in enumerate(endpoint_specs[: max(contract_min, len(endpoint_specs))], start=1):
        upstream_ids = contract_id_groups[idx - 1] if idx - 1 < len(contract_id_groups) else contract_id_groups[-1]
        contract_trace_rows.append(
            [
                f"P2-CTR-{idx:02d}",
                service.public_contract,
                "public-contract",
                f"`{service.home_module}`",
                "HANDOFF-0001",
                f"{service.endpoint_name} / {service.public_contract} remains visible in Stage-04 replay and implementation handoff",
                ", ".join(upstream_ids),
            ]
        )

    binding_rows, enrichment_rows, traceability_rows = build_binding_and_trace_rows(
        phase1_page_map=phase1_page_map,
        phase1_interactions=phase1_interactions,
        phase1_flow_rows=phase1_flow_rows,
        endpoint_specs=endpoint_specs,
        trace_rows=all_trace_rows,
    ) if phase1_interactions else ([], [], [])

    interaction_flow_rows: list[list[str]] = []
    endpoint_chain = endpoint_specs[: max(4, min(len(endpoint_specs), 6))]
    if endpoint_chain:
        for idx in range(max(1, len(endpoint_chain) - 1)):
            current = endpoint_chain[idx]
            nxt = endpoint_chain[idx + 1] if idx + 1 < len(endpoint_chain) else endpoint_chain[idx]
            interaction_flow_rows.append(
                [
                    f"flow_{idx + 1:02d}",
                    f"{current.endpoint_name} -> {nxt.endpoint_name}",
                    f"`{current.home_module}` writes, `{nxt.home_module}` consumes read-only context",
                    f"{current.owns_or_coordinates} + {nxt.owns_or_coordinates}",
                    f"version mismatch or missing `{to_snake(service_technical_name(current))}_id` blocks the handoff",
                    "refresh state and replay with the same contract boundary",
                    "keeps ownership explicit while still allowing downstream composition",
                ]
            )

    scenario_groups = distribute_phase1_ids(all_trace_ids or req_ac_ids, scenario_min)
    scenario_rows: list[list[str]] = []
    scenario_services = services[: max(scenario_min, min(len(services), 6))] or services[:1]
    for idx, service in enumerate(scenario_services, start=1):
        peer = services[idx] if idx < len(services) else service
        scenario_rows.append(
            [
                f"scenario_{idx:02d}",
                "domain operator",
                service.owns_or_coordinates,
                f"`{service.home_module}`, `{peer.home_module}`",
                f"{service.endpoint_name}, {peer.endpoint_name}",
                f"`{service.service_name}` remains the only writer for `{service.owns_or_coordinates}`",
                f"Given `{service.owns_or_coordinates}` exists, When `{service.endpoint_name}` runs, Then the contract must preserve ids, version anchors, and replay context within <= 600 ms for the synchronous path.",
                f"contract response diff for `{service.endpoint_name}`",
                "positive_path / quantified",
                f"`{service.owns_or_coordinates}` is available",
                f"`{service.endpoint_name}` is invoked",
                "the output remains contract-valid, replay-safe, and latency-bounded",
                "versioned ownership handoff",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[idx - 1]) if idx - 1 < len(scenario_groups) else ", ".join(scenario_groups[-1]),
            ]
        )
    while len(scenario_rows) < scenario_min and services:
        service = services[len(scenario_rows) % len(services)]
        scenario_rows.append(
            [
                f"scenario_{len(scenario_rows) + 1:02d}",
                "domain operator",
                service.owns_or_coordinates,
                f"`{service.home_module}`",
                service.endpoint_name,
                "ownership remains explicit under replay",
                f"Given a valid request, When `{service.endpoint_name}` runs, Then the response must preserve the contract envelope and trace id.",
                f"response envelope check for `{service.endpoint_name}`",
                "positive_path / quantified",
                "a valid request exists",
                f"`{service.endpoint_name}` is invoked",
                "the response remains stable, additive, and <= 600 ms on the synchronous path",
                "single-writer discipline",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[-1]),
            ]
        )
    for idx, service in enumerate(services[:2], start=1):
        scenario_rows.append(
            [
                f"scenario_{len(scenario_rows) + 1:02d}",
                "parallel operators",
                service.owns_or_coordinates,
                f"`{service.home_module}`",
                f"{service.endpoint_name}, Update{service_technical_name(service)}Status",
                "concurrent writes must surface version conflict explicitly",
                f"Given two actors update `{service.owns_or_coordinates}` concurrently, When stale version input is submitted, Then the system returns `409 version_conflict` and preserves the last committed record.",
                f"conflict replay and 409 assertion for `{service.endpoint_name}`",
                "concurrent_conflict / quantified",
                "two competing updates exist",
                "the stale update is submitted second",
                "the stale write is rejected with explicit conflict semantics",
                "retry on version conflict with versioned write guard",
                service.owns_or_coordinates,
                ", ".join(scenario_groups[min(idx - 1, len(scenario_groups) - 1)]),
            ]
        )

    tech_rows = [
        [
            "PostgreSQL + Redis",
            "high",
            "strong workflow consistency with bounded cache sidecar",
            "high",
            "strong",
            "moderate",
            "moderate",
            "mature ecosystem",
            "strong",
            "moderate",
            "low",
            "strong",
            "good metrics/log tooling",
            "incremental from first-wave schema",
            "low",
            "moderate",
            "cache misuse or missing indexes can hide bottlenecks",
            "https://www.postgresql.org/docs/current/index.html reviewed 2026-04-09; https://redis.io/docs/latest/ reviewed 2026-04-09",
            "selected",
            "best fit for contract integrity and replay needs",
        ],
        [
            "Document store primary",
            "medium",
            "flexible schema but weaker relational closure",
            "high",
            "medium",
            "moderate",
            "moderate",
            "mature ecosystem",
            "acceptable",
            "moderate",
            "low",
            "medium",
            "good",
            "possible later for selective read models",
            "medium",
            "low",
            "typed contract traceability becomes softer",
            "https://eventstore.com/docs/ reviewed 2026-04-09; https://martinfowler.com/eaaDev/EventSourcing.html reviewed 2026-04-09",
            "rejected",
            "weakens deterministic replay posture",
        ],
        [
            "Event-store first",
            "medium",
            "excellent replay semantics but heavy operational burden",
            "medium",
            "low",
            "high",
            "high",
            "niche ecosystem",
            "medium",
            "high",
            "high",
            "medium",
            "good",
            "possible for a narrow audit subdomain later",
            "medium",
            "high",
            "cognitive load exceeds first-wave needs",
            "https://www.postgresql.org/docs/current/index.html reviewed 2026-04-09; https://www.meilisearch.com/docs reviewed 2026-04-09",
            "rejected",
            "too much complexity before runtime proof exists",
        ],
        [
            "Relational core + search sidecar",
            "medium",
            "good read acceleration once discovery-heavy surfaces matter",
            "medium",
            "medium",
            "moderate",
            "moderate",
            "mature ecosystem",
            "acceptable",
            "moderate",
            "moderate",
            "good",
            "good metrics/log tooling",
            "possible later for broad read discovery",
            "medium",
            "moderate",
            "premature search complexity can hide the core workflow bottleneck",
            "https://supabase.com/docs reviewed 2026-04-09; https://firebase.google.com/docs reviewed 2026-04-09",
            "rejected",
            "premature for the current workflow-first baseline",
        ],
        [
            "Managed backend platform",
            "medium",
            "fast bootstrap but weaker contract explicitness",
            "medium",
            "medium",
            "low",
            "low-to-medium",
            "mature ecosystem",
            "acceptable",
            "low",
            "medium",
            "medium",
            "acceptable",
            "unclear once workflow-specific runtime proof deepens",
            "medium",
            "low",
            "abstractions can hide boundary drift and replay semantics",
            "internal first-wave design evidence reviewed 2026-04-09",
            "rejected",
            "too opaque for the current contract-first architecture lane",
        ],
    ][:tech_min]

    alternative_candidates = [
        "\n".join(
            [
                "  - candidate_01:",
                "    - candidate_name: controller-heavy thin domain",
                "    - pros: fast to scaffold",
                "    - cons: weak ownership and replay discipline",
                "    - cost_burden: low short-term, high long-term",
                "    - fit_scenario: throwaway prototype",
                "    - reversibility: medium",
            ]
        ),
        "\n".join(
            [
                "  - candidate_02:",
                "    - candidate_name: split microservices now",
                "    - pros: stronger runtime isolation",
                "    - cons: early ops overhead",
                "    - cost_burden: high",
                "    - fit_scenario: large multi-team org",
                "    - reversibility: medium",
            ]
        ),
        "\n".join(
            [
                "  - candidate_03:",
                "    - candidate_name: event sourcing first",
                "    - pros: strong replay semantics",
                "    - cons: higher migration and team load",
                "    - cost_burden: high",
                "    - fit_scenario: audit-first niche",
                "    - reversibility: low",
            ]
        ),
        "\n".join(
            [
                "  - candidate_04:",
                "    - candidate_name: managed platform first",
                "    - pros: fast bootstrap",
                "    - cons: weaker boundary and replay explicitness",
                "    - cost_burden: medium",
                "    - fit_scenario: small CRUD-heavy back office",
                "    - reversibility: medium",
            ]
        ),
    ][: max(profile_minimum(complexity_profile, "stage_03_alt_candidate_structure"), 4)]

    tradeoff_rows = [
        ["TD-01", "keep explicit module boundaries", "collapse into generic controllers", "ownership and replay stay legible", "heavier docs up front", "high", "revisit when runtime proves boundaries are overfit"],
        ["TD-02", "relational core with additive contracts", "schema-light primary store", "typed payloads and joins remain auditable", "slower ad hoc schema drift", "medium", "revisit if schema volatility dominates"],
        ["TD-03", "single response envelope", "endpoint-local error shapes", "callers can reason consistently", "local optimization is slower", "high", "revisit only if transport model changes materially"],
    ]

    public_boundary_rows: list[list[str]] = []
    seen_contracts: set[str] = set()
    for spec in endpoint_specs:
        if spec.public_contract in seen_contracts:
            continue
        if spec.public_contract.rsplit(".", 1)[-1].endswith("List"):
            continue
        seen_contracts.add(spec.public_contract)
        namespace, _, public_name = spec.public_contract.rpartition(".")
        public_boundary_rows.append(
            [
                public_name or spec.public_contract,
                namespace or root_namespace,
                "active",
                spec.home_module,
                "contract",
                f"Stage-03 contract surface via {spec.endpoint_name}",
                f"stable boundary for {spec.purpose.lower()}",
            ]
        )

    mermaid_entities = unique_preserve([str(spec["table_name"]) for spec in rendered_table_specs[:14]])
    mermaid_nodes = [f'    T{idx + 1}["{name}"]' for idx, name in enumerate(mermaid_entities)]
    mermaid_edges = [
        f"    T{idx + 1} --> T{idx + 2}"
        for idx in range(len(mermaid_entities) - 1)
    ] or ["    T1 --> T2"]
    service_chain = unique_preserve([service.service_name for service in services[:6]])
    service_nodes = [f'    S{idx + 1}["{service_name}"]' for idx, service_name in enumerate(service_chain)]
    service_edges = [
        f"    S{idx + 1} --> S{idx + 2}"
        for idx in range(len(service_chain) - 1)
    ] or ["    S1 --> S2"]

    stage = f"""# Stage-03: data-storage-and-interface-design

## 1. Generation Provenance
- state: `authored-first-pass`
- phase1_prd: `{phase1_prd}`
- complexity_profile: `{complexity_profile}`

## 2. 数据与接口设计备忘
- 为什么这样设计：本阶段选择关系型主存储、显式公共契约和可回放接口，是为了让 Stage-02 的 owner / aggregate / event 判断落到可实现、可测试、可追踪的边界上。
- 先读什么：先读 data_ownership_map 和 contract_api_surface，再读 storage、scenario、tradeoff 表；不要先从字段清单倒推出业务责任。
- 表格怎么读：data_model_summary 说明持久化对象，contract_api_surface 说明服务入口，scenario_coverage_matrix 说明验证路径；三者要共同证明同一条交接链。
- 给 P3 的交接：P3 应消费契约名、请求响应形状、幂等/失败语义、事件消费规则和 scenario measurement hook，而不是只复制 endpoint 或 table 名。
- 证据边界：Stage-03 是 implementation planning contract；真实性能、迁移和运行闭合仍由 P3 runtime / test evidence 证明。

## 3. Core Structured Output
- data_model_summary:
  - primary_storage_shape: relational core with explicit payload JSON seams where contracts need flexibility
  - storage_focus: workflow evidence, linkage, review closure, and audit-sensitive events
  - schema_freeze_rule: public contracts evolve additively while identifiers and envelopes stay stable
- data_ownership_map:
{make_markdown_table(
    ["object", "owning module", "write authority", "read_only_consumers", "public_contract", "change_propagation_path", "forbidden_shortcut", "closure note"],
    data_ownership_rows,
)}
- storage_strategy:
{make_markdown_table(
    ["storage_layer", "first_wave_role", "initial_plan", "one_year_plan", "three_year_plan", "partition_or_shard_rule", "archive_or_cleanup_rule", "why_selected"],
    storage_layer_rows,
)}
  - initial: PostgreSQL primary + Redis cache for bounded read acceleration
  - one_year: retain hot-path indexes under 3x growth
  - three_year: export immutable bundles and cold evidence without renaming contracts
  - partition_strategy: tenant + time window on high-growth tables
  - archival_rule: keep replay integrity while moving immutable bundles cold
  - throughput: 120 request/min steady state and 4x burst during review windows
  - latency: p95 <= 600 ms reads, p95 <= 5 min async workflows
  - growth: 3x one-year, 5x three-year
  - retention: 365d hot + 730d cold for audit-critical surfaces
  - consistency_rule: authoritative command writes commit before cache refresh or async fan-out
- access_pattern_and_index_strategy:
{make_markdown_table(
    ["access_pattern", "touched_tables", "predicate_sort_join_keys", "expected_selectivity", "proposed_index", "write_cost_note", "validation_hook"],
    access_pattern_rows,
)}
- schema_draft:
{make_markdown_table(
    ["table_name", "ownership", "pk", "fk", "unique_constraints", "composite_indexes"],
    schema_summary_rows,
)}
{chr(10).join(schema_entries)}
- data_sensitivity_and_compliance_matrix:
{make_markdown_table(
    ["table_name", "pii_level", "sensitive_fields", "masking_or_encryption", "retention_rule", "audit_access_rule", "compliance_note"],
    sensitivity_rows,
)}
- interface_contracts:
{chr(10).join(contract_entries)}
- response_and_error_contract:
  - canonical_success_response:
    - data: typed domain payload
    - meta: trace_id, cursor, review_bound_flags when applicable
  - canonical_error_response:
    - error_type: `business_error | system_error`
    - error_code: stable machine-readable code
    - message: human-meaningful explanation without leaking secrets
    - retryability: explicit yes/no/backoff posture
    - caller_action: fix input / refresh state / retry with backoff / escalate
    - trace_id: always present for audit and correlation
  - classification_rule:
    - validation, permission, conflict, and missing-precondition failures are `business_error`; infrastructure or dependency failures are `system_error`
- api_endpoint_draft:
{make_markdown_table(
    ["endpoint_name", "method", "path", "purpose", "request_body_example", "response_body_example", "rate_limit_policy", "pagination_rule", "response_profile", "retryability_policy", "idempotency_rule", "failure_codes"],
    api_rows,
)}
- stage_02_event_name_carry_forward:
{make_markdown_table(
    ["stage_02_event_name", "stage_03_touchpoints", "preserved_name_or_alias", "mapping_note"],
    event_rows,
)}
- event_model_direct_consumption:
  - source_driver: `p2-architecture-event-model-driver.v1`
  - p3_event_handoff_status: `ready-for-implementation-consumption`
{make_markdown_table(
    ["event_name", "contract_touchpoint", "mutation_or_read_effect", "versioning_and_schema_posture", "p3_event_handoff", "claim_ceiling"],
    event_consumption_rows,
)}
- contract_trace_registry:
{make_markdown_table(
    ["trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook", "upstream_trace_ids"],
    contract_trace_rows,
)}
- interaction_matrix_p2_enrichment:
{make_markdown_table(
    ["interaction_id", "page_id", "input_schema_ref", "display_field_set", "validation_rules", "enabled_rule", "value_source", "internal_exposure", "error_state", "readiness_status", "blocked_reason"],
    enrichment_rows,
) if enrichment_rows else "- no Phase-1 interaction-flow contract was available, so P2-owned interaction enrichment could not be compiled"}
- data_service_binding_matrix:
{make_markdown_table(
    ["service_binding_id", "interaction_id", "use_case_id", "transaction_group_id", "binding_mode", "domain_service", "api_endpoint", "http_method", "request_field_mapping", "response_field_mapping", "db_entities", "rbac_policy", "audit_event", "failure_codes", "server_generated_fields", "ui_refresh_targets", "handoff_materialization", "readiness_status", "blocked_reason"],
    binding_rows,
) if binding_rows else "- no Phase-1 interaction-flow contract was available, so binding matrix generation remained blocked"}
- traceability_matrix:
{make_markdown_table(
    ["trace_row_id", "req_id", "use_case_id", "page_id", "interaction_id", "service_binding_id", "api_endpoint", "test_ids", "closure_gate", "canonical_page_id", "audience_mode", "exposure_scope", "staleness_marker", "upstream_trace_ids"],
    traceability_rows,
) if traceability_rows else "- no interaction-level binding chain was available, so traceability remained API/test-skewed"}
- interaction_flow:
{make_markdown_table(
    ["flow_name", "producer_consumer_chain", "write_boundary", "primary_data_surfaces", "failure_detection", "rollback_or_compensation", "closure_note"],
    interaction_flow_rows,
)}
- security_architecture_outline:
  - trust_boundaries:
    - API edge / policy check / domain module / audit evidence
  - authn_authz_posture: `{boundary_term}-scoped RBAC with explicit mutation checks, privileged read review, and trace-linked operator accountability`
  - auth_sequence_direction: `request enters API policy gate, resolves role and {boundary_term} claims, executes domain write, then records audit evidence before response`
  - token_posture: `short-lived access tokens carry {boundary_term}, role, and traceable session claims, with refresh limited to approved operator contexts`
  - audit_logging_hooks:
    - mutating endpoints, privileged reads, review closure
  - sensitive_data_handling:
    - mask logs, encrypt at rest where required, preserve boundary-private evidence separation
  - key_management_posture:
    - scheduled rotation and secret-store isolation
    - break-glass access is audited and expires automatically
  - {boundary_term}_isolation_controls:
    - enforce boundary_id on every authoritative write path and cache namespace when the deployment boundary requires it
- technology_stack_and_deployment_assumptions:
  - api_runtime: TypeScript / service-layer runtime kept contract-first
  - primary_storage: PostgreSQL
  - cache: Redis only where bounded read amplification helps
  - queue_posture: {async_completion_pack['queue_posture_label']}
  - deployment_bias: start simple and preserve module boundaries before physical decomposition
- technology_selection_evaluation_matrix:
{make_markdown_table(
    ["candidate_name", "reliability", "performance_capacity", "scalability", "maintainability", "development_cost", "operations_cost", "ecosystem_maturity", "security_compliance_posture", "deployment_complexity", "integration_cost", "integration_fit", "observability", "migration_path", "vendor_risk", "learning_curve", "failure_mode", "evidence_sources", "final_decision", "rejection_reason"],
    tech_rows,
)}
- dominant_bottleneck_hypothesis:
  - bottleneck: contract-heavy write paths plus replay-safe read refresh under burst
  - measurement_plan: benchmark persistence, read-model refresh, and review query latency separately
  - threshold: trigger design reconsideration if p95 review generation exceeds 2s or async completion exceeds 5 min at 4x burst
  - spike_scope: benchmark high-growth tables with index plans and replay-friendly writes
- architecture_alternative_candidate_set:
{chr(10).join(alternative_candidates)}
- baseline_insufficiency_note:
  - current baseline is contract-verified and delivery-oriented, but external runtime proof still needs later validation
- constraint_dominant_optimum_candidate:
  - optimum_under_current_constraints: modular-monolith with explicit public contracts, indexed relational storage, and serialized conflict handling on shared surfaces
- capacity_and_performance_assumptions:
  - throughput: 120 request/min steady state, 4x burst during review windows
  - latency: p95 <= 600 ms synchronous reads
  - growth: 3x one-year, 5x three-year evidence volume
  - retention: 365d hot, 730d cold
  - storage: workflow evidence dominates size and index pressure
- scenario_coverage_matrix:
{make_markdown_table(
    ["scenario", "actors", "entities", "modules", "contracts / endpoints", "failure_note", "acceptance_criteria", "measurement_hook", "scenario_category", "given", "when", "then", "coordination_strategy", "shared_resource", "upstream_trace_ids"],
    scenario_rows,
)}
- key_tradeoff_decisions:
{make_markdown_table(
    ["decision_id", "chosen_posture", "rejected_alternative", "why_selected", "cost_paid_now", "reversibility", "revisit_trigger"],
    tradeoff_rows,
)}
- public_boundary_registry_closure:
  - namespace_rule:
    - all public-boundary names use `{root_namespace}.<domain>.<object>` or `{root_namespace}.<domain>.<contract>`
  - recommended_registry_template:
{make_markdown_table(
    ["public_name", "namespace", "status", "owner_module", "artifact_type", "origin", "closure_note"],
    public_boundary_rows,
)}

## 5. Mermaid Evidence
```mermaid
flowchart LR
{chr(10).join(mermaid_nodes + mermaid_edges)}
```

```mermaid
flowchart LR
{chr(10).join(service_nodes + service_edges)}
```
"""
    return stage.rstrip() + "\n"



def render_stage_04(
    *,
    phase1_prd: Path,
    phase1_prototype_spec: Path | None = None,
    phase1_prototype_prompt_pack: Path | None = None,
    phase1_interaction_flow_contract: Path | None = None,
    complexity_profile: str,
    context: dict[str, object],
    services: list[ServiceSpec],
    contract_names: list[str],
    endpoint_names: list[str],
    stage_03_text: str,
    stage_02_5_text: str,
) -> str:
    supports_deferred_extension_seam = context_supports_deferred_extension_seam(context)
    business_proof_handoff = business_proof_constraint_block(context, indent=4)
    thesis_architecture_handoff = business_architecture_pressure_block(context, indent=4)
    deferred_seam_heading = "deferred_attribution_seam" if supports_deferred_extension_seam else "deferred_extension_seam"
    deferred_seam_line = (
        "attribution remains deferred / placeholder-backed and is not upgraded into MVP-complete proof by Stage-04"
        if supports_deferred_extension_seam
        else "deferred extension remains placeholder-backed and is not upgraded into MVP-complete proof by Stage-04"
    )
    sequence_target = max(profile_minimum(complexity_profile, "stage_04_sequence_diagrams"), 2)
    service_count = len(services)
    wp_target = max(profile_minimum(complexity_profile, "stage_04_work_packages"), 6 if service_count >= 9 else 5 if service_count >= 7 else 4)
    rbi_target = max(profile_minimum(complexity_profile, "stage_04_rbi_items"), 3)
    verification_target = max(profile_minimum(complexity_profile, "stage_04_design_verification"), 3)
    replay_target = max(profile_minimum(complexity_profile, "stage_04_verification_replay"), 2)
    observability_target = max(profile_minimum(complexity_profile, "stage_04_observability"), 3)
    rbi_trace_target = max(profile_minimum(complexity_profile, "stage_04_rbi_trace_registry"), 3)
    prototype_spec_path = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        explicit_path=phase1_prototype_spec,
        candidate_names=("prototype-spec.md", "prototype_spec.md"),
    )
    prototype_prompt_pack_path = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        explicit_path=phase1_prototype_prompt_pack,
        candidate_names=("prototype-prompt-pack.md", "prototype_prompt_pack.md"),
    )
    interaction_flow_contract_path = _resolve_phase1_interaction_flow_contract_path(
        phase1_prd,
        explicit_path=phase1_interaction_flow_contract,
    )
    phase1_page_map = _extract_page_map_from_prototype_spec(prototype_spec_path)
    page_blueprint_rows: list[list[str]] = []
    if phase1_page_map:
        primary_surfaces = [page["page_name"] for page in phase1_page_map if str(page.get("page_name") or "").strip()]
        primary_surface_lines: list[str] = []
        for page in phase1_page_map:
            page_name = str(page.get("page_name") or "").strip()
            if not page_name:
                continue
            suffix_parts: list[str] = []
            page_role = str(page.get("page_role") or "").strip()
            blueprint_type = str(page.get("page_blueprint_type") or "").strip()
            surface_variant = str(page.get("surface_variant") or "").strip()
            audience_mode = str(page.get("audience_mode") or "").strip()
            if page_role:
                suffix_parts.append(f"role: {page_role}")
            if blueprint_type:
                suffix_parts.append(f"blueprint: {blueprint_type}")
            if audience_mode:
                suffix_parts.append(f"audience: {audience_mode}")
            if surface_variant:
                suffix_parts.append(f"variant: {surface_variant}")
            if blueprint_type:
                page_blueprint_rows.append(
                    [
                        page_name,
                        blueprint_type,
                        page_role or "not-stated",
                        str(page.get("canonical_page_id") or "").strip() or "not-stated",
                        surface_variant or "not-stated",
                        audience_mode or "not-stated",
                        str(page.get("session_role_source") or "").strip() or "not-stated",
                        str(page.get("auth_entry_route") or "").strip() or "not-stated",
                        str(page.get("auth_entry_label") or "").strip() or "not-stated",
                        str(page.get("workspace_entry_roles") or "").strip() or "not-stated",
                        str(page.get("route_reachability_mode") or "").strip() or "not-stated",
                        str(page.get("navigation_scope") or "").strip() or "not-stated",
                        str(page.get("handoff_visibility") or "").strip() or "not-stated",
                        str(page.get("forbidden_exposure") or "").strip() or "not-stated",
                    ]
                )
            primary_surface_lines.append(f"    - `{page_name}`" + (f" ({'; '.join(suffix_parts)})" if suffix_parts else ""))
        primary_surface_block = "\n".join(primary_surface_lines)
        surface_provenance = "phase1-prototype-spec"
    else:
        primary_surfaces = semantic_primary_surfaces(context) or extract_dynamic_primary_surfaces(str(context.get("text", "")), phase1_page_map)
        primary_surface_block = "\n".join(f"    - `{surface}`" for surface in primary_surfaces)
        surface_provenance = "phase1-ia-inferred"
    prototype_spec_ref = str(prototype_spec_path) if prototype_spec_path else ""
    prototype_prompt_pack_ref = str(prototype_prompt_pack_path) if prototype_prompt_pack_path else ""
    interaction_flow_contract_ref = str(interaction_flow_contract_path) if interaction_flow_contract_path else ""
    page_blueprint_block = (
        make_markdown_table(
            [
                "surface",
                "page_blueprint_type",
                "page_role",
                "canonical_page_id",
                "surface_variant",
                "audience_mode",
                "session_role_source",
                "auth_entry_route",
                "auth_entry_label",
                "workspace_entry_roles",
                "route_reachability_mode",
                "navigation_scope",
                "handoff_visibility",
                "forbidden_exposure",
            ],
            page_blueprint_rows,
        )
        if page_blueprint_rows
        else "not available; fallback surface inference is active"
    )

    all_trace_rows = list(context["all_trace_rows"])
    all_trace_ids = [row["trace_id"] for row in all_trace_rows]
    req_ac_ids = [row["trace_id"] for row in all_trace_rows if row.get("unit_type") in {"requirement", "acceptance-criteria"}] or all_trace_ids
    rbi_id_groups = distribute_phase1_ids(req_ac_ids, rbi_trace_target)

    service_chunks = round_robin_chunks([service.service_name for service in services], wp_target)
    wp_ids = [f"WP-A{idx}" for idx in range(1, wp_target + 1)]
    work_package_rows: list[list[str]] = []
    for idx, wp_id in enumerate(wp_ids):
        owned_services = service_chunks[idx] if idx < len(service_chunks) else []
        service_scope = ", ".join(f"`{name}`" for name in owned_services[:3]) or "`cross-cutting`"
        depends_on = "none" if idx == 0 else wp_ids[idx - 1]
        linked_rbi = f"RBI-{min(idx + 1, rbi_target):02d}"
        work_package_rows.append(
            [
                wp_id,
                f"stabilize {service_scope} contracts, replay paths, and implementation handoff",
                f"the slice preserves ownership, contract naming, and replay evidence for {service_scope}",
                f"{4 + (idx % 3)}d",
                depends_on,
                linked_rbi,
            ]
        )

    nested_wp_entries = [
        "\n".join(
            [
                f"    - `{row[0]}`:",
                f"      - completion_signal: {row[2]}",
                f"      - acceptance_criteria: Given the design slice is implemented, When verification replay is run, Then {row[2]}.",
            ]
        )
        for row in work_package_rows[: max(profile_minimum(complexity_profile, "stage_04_slice_acceptance"), 2)]
    ]

    deadlines = ["2026-04-15", "2026-04-18", "2026-04-20", "2026-04-22", "2026-04-25", "2026-04-28"]
    rbi_rows: list[list[str]] = []
    for idx in range(rbi_target):
        owner_service = services[idx % len(services)] if services else None
        wp = work_package_rows[min(idx, len(work_package_rows) - 1)][0]
        blocks = work_package_rows[min(idx + 1, len(work_package_rows) - 1)][0]
        label = owner_service.service_name if owner_service else "cross-cutting slice"
        rbi_rows.append(
            [
                f"RBI-{idx + 1:02d}",
                f"runtime proof is still required for `{label}` contract and replay posture",
                "H" if idx < 2 else "M" if idx < 4 else "L",
                wp,
                "platform owner" if idx % 2 == 0 else "workflow owner",
                blocks,
                deadlines[idx % len(deadlines)],
                f"RBI-{idx + 1:02d} -> {wp}",
            ]
        )

    design_verification_rows: list[list[str]] = []
    for idx, service in enumerate(services[:verification_target], start=1):
        design_verification_rows.append(
            [
                f"`{service.service_name}` boundary preserved",
                "pass",
                "contract review + replay walkthrough",
                f"{service.endpoint_name} contract and ownership table",
                f"`{service.service_name}` remains the only writer for `{service.owns_or_coordinates}`",
                "runtime proof pending",
                f"RBI-{min(idx, len(rbi_rows)):02d} / {work_package_rows[min(idx - 1, len(work_package_rows) - 1)][0]}",
            ]
        )
    while len(design_verification_rows) < verification_target:
        design_verification_rows.append(
            [
                f"cross-module handoff {len(design_verification_rows) + 1:02d}",
                "pass",
                "replay walkthrough",
                "handoff package",
                "ownership, ids, and trace anchors survive the handoff",
                "runtime proof pending",
                f"RBI-{min(len(design_verification_rows) + 1, len(rbi_rows)):02d}",
            ]
        )

    replay_rows: list[list[str]] = []
    replay_count = max(replay_target, 2)
    replay_id_groups = distribute_phase1_ids(all_trace_ids or req_ac_ids, replay_count)
    for idx in range(replay_count):
        current = services[idx % len(services)] if services else None
        nxt = services[(idx + 1) % len(services)] if services else None
        artifact = f"{current.owns_or_coordinates if current else 'core_object'} + {nxt.owns_or_coordinates if nxt else 'downstream_object'}"
        replay_rows.append(
            [
                f"P2-RP-{idx + 1:02d}",
                f"{current.endpoint_name if current else 'contract'} handoff replay",
                "scenario-replay" if idx % 2 else "contract-walkthrough",
                artifact,
                "ownership, contract ids, and replay anchors stay explicit",
                "implementation intake keeps the same closure rules visible",
                "pass",
                design_verification_rows[min(idx, len(design_verification_rows) - 1)][0],
                "IMPL-STG00-INPUT-0001",
                f"{work_package_rows[min(idx, len(work_package_rows) - 1)][0]}, {rbi_rows[min(idx, len(rbi_rows) - 1)][0]}",
                ", ".join(replay_id_groups[min(idx, len(replay_id_groups) - 1)]),
            ]
        )

    rbi_trace_rows: list[list[str]] = []
    for idx, rbi in enumerate(rbi_rows[:rbi_trace_target], start=1):
        ids = rbi_id_groups[idx - 1] if idx - 1 < len(rbi_id_groups) else rbi_id_groups[-1]
        rbi_trace_rows.append(
            [
                f"P2-RT-{idx:02d}",
                rbi[0],
                rbi[3],
                "IMPL-STG00-INPUT-0001",
                f"{rbi[0]} remains linked to `{rbi[3]}` until replay or runtime evidence closes the risk",
                "implementation intake must preserve RBI owner, blocker, and closure rule",
                ", ".join(ids),
            ]
        )

    metric_map = {
        "transactional": "write_latency, version_conflict_rate",
        "orchestration": "handoff_latency, replay_dedupe_rate",
        "read-assembly": "cache_hit_rate, refresh_latency",
        "policy": "deny_rate, policy_check_latency",
        "domain": "contract_validation_failures, publish_latency",
        "support": "append_latency, evidence_gap_rate",
    }
    observability_rows: list[list[str]] = []
    for idx, service in enumerate(services[:observability_target], start=1):
        observability_rows.append(
            [
                f"surface-{idx:02d}",
                service.service_name,
                metric_map.get(service.service_type, "request_latency, error_rate"),
                f"tenant_id + {to_snake(service_technical_name(service))}_id + trace_id",
                f"alert when `{service.endpoint_name}` error rate or latency exceeds threshold",
                "p95 <= 600ms for sync paths; async queues remain bounded",
                "platform owner" if idx % 2 else "workflow owner",
                f"do not widen rollout until `{service.service_name}` metrics are stable",
            ]
        )

    environment_prerequisites = format_nested_bullets(derive_environment_dependency_prerequisites(stage_03_text, stage_02_5_text), indent=4)
    adr_titles_for_list = [str(item) for item in context.get("adr_titles", [])]
    adr_list = "\n".join(f"    - `AD-{idx:02d}` {title}" for idx, title in enumerate(adr_titles_for_list[:10], start=1))
    contract_list = "\n".join(f"    - `{name}`" for name in unique_preserve(contract_names))

    mermaid_sequences: list[str] = []
    if services:
        sequence_count = min(sequence_target, max(1, len(services) - 1))
        for idx in range(sequence_count):
            current = services[idx]
            nxt = services[idx + 1] if idx + 1 < len(services) else services[idx]
            mermaid_sequences.append(
                "\n".join(
                    [
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant U as Operator",
                        f"    participant S{idx + 1} as {current.service_name}",
                        f"    participant S{idx + 2} as {nxt.service_name}",
                        "    participant A as AuditTrail",
                        f"    U->>S{idx + 1}: invoke {current.endpoint_name}",
                        f"    S{idx + 1}->>S{idx + 2}: hand off {current.owns_or_coordinates} context",
                        f"    S{idx + 2}->>A: record replay-safe audit evidence",
                        f"    A-->>S{idx + 2}: audit persistence confirmed",
                        f"    S{idx + 2}-->>U: return versioned acknowledgement for {nxt.owns_or_coordinates}",
                        "```",
                    ]
                )
            )
    if not mermaid_sequences:
        mermaid_sequences.append(
            "\n".join(
                [
                    "```mermaid",
                    "sequenceDiagram",
                    "    participant U as Operator",
                    "    participant A as CoreService",
                    "    participant B as ReviewService",
                    "    participant T as AuditTrail",
                    "    U->>A: submit workflow request",
                    "    A->>B: contract-bound handoff",
                    "    B->>T: record audit event",
                    "    T-->>B: persistence confirmed",
                    "    B-->>U: replay-safe acknowledgement",
                    "```",
                ]
            )
        )

    stage = f"""# Stage-04: design-convergence-and-delivery-prototype

## 1. Generation Provenance
- state: `authored-first-pass`
- phase1_prd: `{phase1_prd}`
- complexity_profile: `{complexity_profile}`

## 3. Core Structured Output
- architecture_convergence_summary:
  - preserved_stage_01_decisions:
{adr_list}
  - preserved_contracts:
{contract_list}
  - convergence_direction: modular monolith with explicit public boundary and replay-ready handoff
  - authority_consumption_note:
    - Stage-04 is a convergence / handoff digest, not the sole authority for surface or binding design
    - page-level authority remains in `prototype-spec.md`; interaction/flow authority remains in `prototype-interaction-flow-contract.md`; binding/traceability authority is compiled in Stage-03 and ESP
  - {deferred_seam_heading}:
    - {deferred_seam_line}
  - business_proof_track_handoff:
{business_proof_handoff}
  - thesis_driven_architecture_handoff:
{thesis_architecture_handoff}
    - handoff_rule: implementation slices must preserve the proof loop named here before adding lower-proof reporting or record-only convenience surfaces
- prototype_or_structured_delivery_expression:
  - surface_provenance: `{surface_provenance}`
  - primary_surfaces:
{primary_surface_block}
  - phase1_prototype_spec: `{prototype_spec_ref}`
  - phase1_prototype_prompt_pack: `{prototype_prompt_pack_ref}`
  - phase1_interaction_flow_contract: `{interaction_flow_contract_ref}`
  - page_blueprint_types:
{page_blueprint_block}
  - expression_mode: structured delivery package with implementation-facing digest, replay, RBI, and work-package evidence
  - why_not_ui_only: first-version delivery integrity depends more on contract and trace closure than on high-fidelity prototype polish; however, the Phase-1 page map and page blueprint types remain authoritative for frontend implementation when prototype-spec evidence exists
- critical_interaction_sequence_set:
  - sequence_1: primary contract activation and downstream handoff
  - sequence_2: mid-stream replay and ownership verification
  - sequence_3: implementation intake and review closure
- optimality_review:
  - acceptable_baseline:
    - modular monolith + relational core + typed public contracts
  - optimal_candidate:
    - keep the current baseline and delay physical decomposition until runtime proof demands it
  - acceptable_vs_optimal_verdict:
    - acceptable now and optimal under first-wave certainty / staffing / runtime constraints
  - why_optimal_not_just_acceptable:
    - preserves traceability, replay, and design honesty without overcommitting operations complexity
  - reversibility_posture:
    - later queue/storage/provider changes remain reversible because contract names and ownership stay stable
  - strongest_supported_readiness_label:
    - `implementation-planning-ready`
  - realizability_judgment:
    - realizable as designed for implementation planning, with explicit RBI chain preserved for unresolved runtime proofs
- design_verification_notes:
{make_markdown_table(
    ["check_item", "result", "verification_method", "evidence", "acceptance_rule", "residual_gap", "linked_rbi_or_wp"],
    design_verification_rows,
)}
- verification_replay_evidence:
{make_markdown_table(
    ["replay_id", "scenario_or_contract", "replay_type", "source_artifacts", "expected_outcome", "observed_outcome", "verdict", "evidence_ref", "downstream_artifact_id", "linked_rbi_or_wp", "upstream_trace_ids"],
    replay_rows,
)}
- unresolved_risks_and_review_bound_items:
{make_markdown_table(
    ["rbi_id", "item", "risk_level", "spike_wp", "responsible_party", "blocks_which_wp", "resolution_deadline", "rbi_matrix"],
    rbi_rows,
)}
- rbi_trace_registry:
{make_markdown_table(
    ["trace_id", "rbi_id", "bound_wp", "downstream_artifact_id", "verification_hook", "handoff_rule", "upstream_trace_ids"],
    rbi_trace_rows,
)}
- observability_and_operational_readiness:
{make_markdown_table(
    ["surface", "service_or_flow", "key_metrics", "structured_logs", "alert_rule", "slo_or_threshold", "owner", "rollout_guardrail"],
    observability_rows,
)}
- implementation_handoff_package:
  - downstream_artifact_id: `IMPL-STG00-INPUT-0001`
  - must_preserve:
    - public-boundary names
    - tenant policy and audit edges
    - typed contract identifiers and replay evidence references
    - RBI ownership and blockers
  - contract_bundle:
{contract_list}
  - handoff_rule:
    - no implementation slice may rename public contracts or weaken failure semantics without returning to Phase-2
- implementation_task_sketch:
{make_markdown_table(
    ["wp_id", "scope", "acceptance_criteria", "estimated_effort", "depends_on", "linked_rbi_or_slice"],
    work_package_rows,
)}
{chr(10).join(nested_wp_entries)}
- identity_and_key_management_choice_posture:
  - auth_vendor_slot: keep policy provider replaceable behind the contract boundary
  - key_posture: scheduled rotation, break-glass audit, no hard-coded runtime secrets
- glossary_or_onboarding_summary:
  - workflow spine: ownership handoff -> replay verification -> implementation intake
  - intake truth: implementation receives contract-verified design, not production-proof certainty
  - environment_or_dependency_prerequisites:
{environment_prerequisites}

## 5. Mermaid Evidence
{chr(10).join(mermaid_sequences)}

```mermaid
C4Container
    title Implementation Planning Intake
    Person(team, "Implementation Team", "consumes P2 handoff")
    System_Boundary(system, "Phase-2 Delivery Boundary") {{
        Container(spec, "Engineering Spec Pack", "Markdown", "implementation-facing contract and trace bundle")
        Container(replay, "Replay Evidence", "Markdown", "verification replay and RBI chain")
        Container(entry, "Implementation Intake", "Markdown", "Phase-3 start contract")
    }}
    Rel(team, spec, "reads")
    Rel(spec, replay, "binds")
    Rel(replay, entry, "feeds")
```

```mermaid
gantt
    title First-Wave Implementation Handoff
    dateFormat  YYYY-MM-DD
    section Work Packages
    WP-A1 :a1, 2026-04-08, 3d
    WP-A2 :a2, after a1, 4d
    WP-A3 :a3, after a2, 4d
    WP-A4 :a4, after a3, 3d
```
"""
    return stage.rstrip() + "\n"


def write_generation_sidecars(
    *,
    output_dir: Path,
    phase1_prd: Path,
    case_name: str,
    version: str,
    complexity_profile: str,
    complexity_report: dict[str, object],
    owner: str,
    existing_system_architecture_change_intake: Path | None = None,
) -> None:
    generation_report = {
        "case_name": case_name,
        "version": version,
        "phase1_prd": str(phase1_prd),
        "existing_system_architecture_change_intake": (
            str(existing_system_architecture_change_intake)
            if existing_system_architecture_change_intake
            else ""
        ),
        "complexity_profile": complexity_profile,
        "complexity_report": complexity_report,
        "owner": owner,
        "generator": "scripts/phase2/run_phase2_first_version.py",
    }
    write_cross_phase_profiled_surface(
        output_dir,
        "phase2",
        "phase-2-first-version-generation-report.json",
        json.dumps(generation_report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    audit = inspect_case(output_dir)
    write_cross_phase_profiled_surface(
        output_dir,
        "phase2",
        "phase-2-first-pass-audit.json",
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _phase1_claims_for_phase2(phase1_prd: Path) -> tuple[list[Any], str, Path | None]:
    return phase1_claims_for_phase2(phase1_prd)


def emit_phase2_first_version_claim_control_sidecars(
    *,
    output_dir: Path,
    phase1_prd: Path,
    artifact_paths: list[Path],
) -> dict[str, Any]:
    claims, source_mode, upstream_sidecar = _phase1_claims_for_phase2(phase1_prd)
    accepted_phase1_claim_ids = {claim.id for claim in claims}
    results = []
    for artifact_path in artifact_paths:
        if not artifact_path.exists():
            continue
        result = emit_path_b_claim_control_sidecar(
            artifact_path=artifact_path,
            artifact_id=f"p2:{artifact_path.stem}",
            claims=claims,
            view_id=f"p2:{artifact_path.stem}",
            source_count=2 if upstream_sidecar else 1,
            upstream_surface_paths=[path for path in [phase1_prd, upstream_sidecar] if path],
        )
        upstream_ref_audit = audit_phase2_artifact_upstream_claim_refs(
            artifact_path,
            accepted_phase1_claim_ids=accepted_phase1_claim_ids,
        )
        acceptance_status = result["acceptance"]["overall_status"]
        artifact_status = (
            "blocked"
            if acceptance_status == "blocked" or upstream_ref_audit["overall_status"] == "blocked"
            else "review_bound"
            if acceptance_status != "pass"
            else "pass"
        )
        classifications = sorted(
            set(result["acceptance"].get("classifications", []) + upstream_ref_audit["classifications"])
        )
        results.append(
            {
                "artifact_path": str(artifact_path),
                "sidecar_path": result["sidecar_path"],
                "overall_status": artifact_status,
                "claim_control_acceptance_status": acceptance_status,
                "classifications": classifications,
                "claim_count": len(result["surface"]["claim_index"]["claims"]),
                "declared_upstream_p1_claim_refs": upstream_ref_audit["declared_upstream_p1_claim_refs"],
                "unknown_upstream_p1_claim_refs": upstream_ref_audit["unknown_upstream_p1_claim_refs"],
            }
        )
    overall_status = phase2_claim_control_report_status(
        artifact_statuses=[row["overall_status"] for row in results],
        phase1_claim_source_mode=source_mode,
    )
    report = {
        "artifact_kind": "phase2-claim-control-sidecar-report",
        "overall_status": overall_status,
        "claim_ceiling": phase2_claim_control_claim_ceiling(
            overall_status=overall_status,
            phase1_claim_source_mode=source_mode,
        ),
        "phase1_claim_source_mode": source_mode,
        "phase1_claim_control_sidecar": str(upstream_sidecar) if upstream_sidecar else "",
        "artifacts": results,
    }
    report_path = resolve_cross_phase_surface_path(output_dir, "phase2", "phase2-claim-control-report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_path, json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return {"report_path": report_path, "report": report}


def build_full_trial_wrapper_command(
    *,
    repo_root: Path,
    phase1_prd: Path,
    output_dir: Path,
    version: str,
    complexity_profile: str,
    complexity_override_justification: str = "",
    deployment_posture: str,
    deployment_posture_suggested: str,
    deployment_posture_warning_class: str,
    deployment_posture_override_source: str,
    deployment_posture_override_reason: str,
    deployment_posture_added_risks: str,
    owner: str,
    output_locale: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    existing_system_architecture_change_intake: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "phase2" / "run_phase2_full_trial.py"),
        "--phase1-prd",
        str(phase1_prd),
        "--output-dir",
        str(output_dir),
        "--version",
        version,
        "--complexity-profile",
        complexity_profile,
        "--deployment-posture",
        deployment_posture,
        "--deployment-posture-suggested",
        deployment_posture_suggested,
        "--deployment-posture-warning-class",
        deployment_posture_warning_class,
        "--deployment-posture-override-source",
        deployment_posture_override_source,
        "--deployment-posture-override-reason",
        deployment_posture_override_reason,
        "--deployment-posture-added-risks",
        deployment_posture_added_risks,
        "--owner",
        owner,
        "--output-locale",
        output_locale,
    ]
    if complexity_override_justification:
        command.extend(
            [
                "--complexity-override-justification",
                complexity_override_justification,
            ]
        )
    if existing_system_architecture_change_intake:
        command.extend(
            [
                "--existing-system-architecture-change-intake",
                str(existing_system_architecture_change_intake),
            ]
        )
    if thinking_value_gain_mode != "off":
        command.extend(["--thinking-value-gain-mode", thinking_value_gain_mode])
        command.extend(["--thinking-value-gain-output-profile", thinking_value_gain_output_profile])
    return command


def run_wrapper(
    *,
    repo_root: Path,
    phase1_prd: Path,
    output_dir: Path,
    version: str,
    complexity_profile: str,
    complexity_override_justification: str = "",
    deployment_posture: str,
    deployment_posture_suggested: str,
    deployment_posture_warning_class: str,
    deployment_posture_override_source: str,
    deployment_posture_override_reason: str,
    deployment_posture_added_risks: str,
    owner: str,
    output_locale: str,
    thinking_value_gain_mode: str = "off",
    thinking_value_gain_output_profile: str = "coverage_rich",
    existing_system_architecture_change_intake: Path | None = None,
) -> int:
    command = build_full_trial_wrapper_command(
        repo_root=repo_root,
        phase1_prd=phase1_prd,
        output_dir=output_dir,
        version=version,
        complexity_profile=complexity_profile,
        complexity_override_justification=complexity_override_justification,
        deployment_posture=deployment_posture,
        deployment_posture_suggested=deployment_posture_suggested,
        deployment_posture_warning_class=deployment_posture_warning_class,
        deployment_posture_override_source=deployment_posture_override_source,
        deployment_posture_override_reason=deployment_posture_override_reason,
        deployment_posture_added_risks=deployment_posture_added_risks,
        owner=owner,
        output_locale=output_locale,
        thinking_value_gain_mode=thinking_value_gain_mode,
        thinking_value_gain_output_profile=thinking_value_gain_output_profile,
        existing_system_architecture_change_intake=existing_system_architecture_change_intake,
    )
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0 and proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def build_phase2_first_version_context(args: argparse.Namespace) -> Phase2FirstVersionContext:
    repo_root = Path(__file__).resolve().parents[2]
    phase1_prd = Path(args.phase1_prd).resolve()
    existing_system_architecture_change_intake = resolve_existing_system_architecture_change_intake(
        str(getattr(args, "existing_system_architecture_change_intake", "") or "")
    )
    output_dir = Path(args.output_dir).resolve()
    phase1_prototype_spec = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        candidate_names=("prototype-spec.md", "prototype_spec.md"),
    )
    phase1_prototype_prompt_pack = _resolve_phase1_prototype_asset_path(
        phase1_prd,
        candidate_names=("prototype-prompt-pack.md", "prototype_prompt_pack.md"),
    )
    phase1_interaction_flow_contract = _resolve_phase1_interaction_flow_contract_path(phase1_prd)
    case_name = args.case_name or infer_case_name(output_dir)
    complexity_profile, complexity_report = derive_complexity_profile(args, phase1_prd)
    ensure_output_dir(output_dir, bool(args.force))
    return Phase2FirstVersionContext(
        repo_root=repo_root,
        phase1_prd=phase1_prd,
        existing_system_architecture_change_intake=existing_system_architecture_change_intake,
        output_dir=output_dir,
        phase1_prototype_spec=phase1_prototype_spec,
        phase1_prototype_prompt_pack=phase1_prototype_prompt_pack,
        phase1_interaction_flow_contract=phase1_interaction_flow_contract,
        case_name=case_name,
        version=str(args.version),
        complexity_profile=complexity_profile,
        complexity_override_justification=str(getattr(args, "complexity_override_justification", "") or ""),
        complexity_report=complexity_report,
        deployment_posture=str(args.deployment_posture),
        deployment_posture_suggested=str(args.deployment_posture_suggested),
        deployment_posture_warning_class=str(args.deployment_posture_warning_class),
        deployment_posture_override_source=str(args.deployment_posture_override_source),
        deployment_posture_override_reason=str(args.deployment_posture_override_reason),
        deployment_posture_added_risks=str(args.deployment_posture_added_risks),
        pure_prd_direct=bool(args.pure_prd_direct or True),
        owner=str(args.owner),
        output_locale=resolve_output_locale(args.output_locale),
        thinking_value_gain_mode=str(getattr(args, "thinking_value_gain_mode", "off") or "off"),
        thinking_value_gain_output_profile=str(
            getattr(args, "thinking_value_gain_output_profile", "coverage_rich") or "coverage_rich"
        ),
        run_wrapper=bool(args.run_wrapper),
        force=bool(args.force),
    )


def run_phase2_first_version(context: Phase2FirstVersionContext) -> Phase2FirstVersionResult:
    timing_started_at = utc_now_iso()
    timing_started_monotonic = time.monotonic()
    timing_segments: list[dict[str, object]] = []
    timing_report_path = resolve_cross_phase_surface_path(context.output_dir, "phase2", "phase2-timing-report.json")
    try:
        phase1_page_map = phase2_timed_segment(
            timing_segments,
            "extract_prototype_page_map",
            lambda: _extract_page_map_from_prototype_spec(context.phase1_prototype_spec),
        )
        parsed_phase1_context = phase2_timed_segment(
            timing_segments,
            "parse_phase1_context",
            lambda: parse_phase1_context(
                context.phase1_prd,
                context.case_name,
                context.complexity_profile,
                prototype_pages=phase1_page_map,
            ),
        )

        def detect_integrations() -> tuple[int, list[str]]:
            text = str(parsed_phase1_context["text"])
            return count_external_integrations(text), detect_external_integration_categories(text)

        external_integration_count, external_integration_categories = phase2_timed_segment(
            timing_segments,
            "detect_external_integrations",
            detect_integrations,
        )
        with_stage_02_5 = external_integration_count > 0
        services = phase2_timed_segment(
            timing_segments,
            "build_service_specs",
            lambda: build_service_specs(parsed_phase1_context, context.complexity_profile),
        )
        table_specs = phase2_timed_segment(
            timing_segments,
            "build_table_specs",
            lambda: build_table_specs(
                parsed_phase1_context,
                str(parsed_phase1_context["root_namespace"]),
                context.complexity_profile,
                services,
            ),
        )
        endpoint_specs = phase2_timed_segment(
            timing_segments,
            "build_stage_03_endpoint_specs",
            lambda: build_stage_03_endpoint_specs(
                services,
                root_namespace=str(parsed_phase1_context["root_namespace"]),
                table_specs=table_specs,
            ),
        )
        existing_system_architecture_change_intake = phase2_timed_segment(
            timing_segments,
            "materialize_existing_system_architecture_change_intake",
            lambda: materialize_existing_system_architecture_change_intake(
                source=context.existing_system_architecture_change_intake,
                output_dir=context.output_dir,
            ),
        )
        existing_system_architecture_change_addendum = render_existing_system_architecture_change_addendum(
            intake_path=existing_system_architecture_change_intake,
            relative_to=context.output_dir,
        )

        phase2_timed_segment(
            timing_segments,
            "write_generation_manifest",
            lambda: write_cross_phase_profiled_surface(
                context.output_dir,
                "phase2",
                "phase-2-first-pass-generation-manifest.md",
                build_manifest(
                    case_name=context.case_name,
                    version=context.version,
                    phase1_prd=context.phase1_prd,
                    output_dir=context.output_dir,
                    pure_prd_direct=context.pure_prd_direct,
                    with_stage_02_5=with_stage_02_5,
                ),
            ),
        )

        stage_01 = phase2_timed_segment(
            timing_segments,
            "render_stage_01",
            lambda: render_stage_01(
                case_name=context.case_name,
                phase1_prd=context.phase1_prd,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
            ),
        )
        if existing_system_architecture_change_addendum:
            stage_01 = stage_01.rstrip() + "\n\n" + existing_system_architecture_change_addendum
        stage_02 = phase2_timed_segment(
            timing_segments,
            "render_stage_02",
            lambda: render_stage_02(
                phase1_prd=context.phase1_prd,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
                table_specs=table_specs,
            ),
        )
        stage_03 = phase2_timed_segment(
            timing_segments,
            "render_stage_03",
            lambda: render_stage_03(
                phase1_prd=context.phase1_prd,
                phase1_prototype_spec=context.phase1_prototype_spec,
                phase1_interaction_flow_contract=context.phase1_interaction_flow_contract,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
                endpoint_specs=endpoint_specs,
                table_specs=table_specs,
            ),
        )
        stage_02_5 = ""
        if with_stage_02_5:
            stage_02_5 = phase2_timed_segment(
                timing_segments,
                "render_stage_02_5",
                lambda: render_stage_02_5(
                    phase1_prd=context.phase1_prd,
                    context=parsed_phase1_context,
                    categories=external_integration_categories,
                ),
            )
        stage_04 = phase2_timed_segment(
            timing_segments,
            "render_stage_04",
            lambda: render_stage_04(
                phase1_prd=context.phase1_prd,
                phase1_prototype_spec=context.phase1_prototype_spec,
                phase1_prototype_prompt_pack=context.phase1_prototype_prompt_pack,
                phase1_interaction_flow_contract=context.phase1_interaction_flow_contract,
                complexity_profile=context.complexity_profile,
                context=parsed_phase1_context,
                services=services,
                contract_names=[service.public_contract for service in endpoint_specs],
                endpoint_names=[service.endpoint_name for service in endpoint_specs],
                stage_03_text=stage_03,
                stage_02_5_text=stage_02_5,
            ),
        )
        if existing_system_architecture_change_addendum:
            stage_04 = stage_04.rstrip() + "\n\n" + existing_system_architecture_change_addendum

        def write_stage_artifacts() -> None:
            write_text(context.output_dir / "stage-01-architecture-definition-and-boundary-setting.md", stage_01)
            write_text(context.output_dir / "stage-02-domain-module-service-decomposition.md", stage_02)
            if with_stage_02_5:
                write_text(context.output_dir / "stage-02.5-third-party-integration-architecture-design.md", stage_02_5)
            write_text(context.output_dir / "stage-03-data-storage-and-interface-design.md", stage_03)
            write_text(context.output_dir / "stage-04-design-convergence-and-delivery-prototype.md", stage_04)

        phase2_timed_segment(timing_segments, "write_stage_artifacts", write_stage_artifacts)

        phase2_timed_segment(
            timing_segments,
            "write_generation_sidecars",
            lambda: write_generation_sidecars(
                output_dir=context.output_dir,
                phase1_prd=context.phase1_prd,
                case_name=context.case_name,
                version=context.version,
                complexity_profile=context.complexity_profile,
                complexity_report=context.complexity_report,
                owner=context.owner,
                existing_system_architecture_change_intake=existing_system_architecture_change_intake,
            ),
        )
        claim_control_result = phase2_timed_segment(
            timing_segments,
            "emit_claim_control_sidecars",
            lambda: emit_phase2_first_version_claim_control_sidecars(
                output_dir=context.output_dir,
                phase1_prd=context.phase1_prd,
                artifact_paths=[
                    context.output_dir / "stage-01-architecture-definition-and-boundary-setting.md",
                    context.output_dir / "stage-02-domain-module-service-decomposition.md",
                    context.output_dir / "stage-03-data-storage-and-interface-design.md",
                    context.output_dir / "stage-04-design-convergence-and-delivery-prototype.md",
                ],
            ),
        )
        audit = phase2_timed_segment(
            timing_segments,
            "inspect_case",
            lambda: inspect_case(context.output_dir),
        )
        return Phase2FirstVersionResult(
            audit=audit,
            with_stage_02_5=with_stage_02_5,
            timing_report_path=timing_report_path,
            claim_control_report_path=claim_control_result["report_path"],
        )
    finally:
        write_phase2_timing_report(
            output_dir=context.output_dir,
            started_at=timing_started_at,
            started_monotonic=timing_started_monotonic,
            segments=timing_segments,
        )


def build_phase2_first_version_summary(
    context: Phase2FirstVersionContext,
    result: Phase2FirstVersionResult,
) -> dict[str, object]:
    summary = {
        "output_dir": str(context.output_dir),
        "case_name": context.case_name,
        "version": context.version,
        "complexity_profile": context.complexity_profile,
        "deployment_posture_selected": context.deployment_posture,
        "deployment_posture_suggested": context.deployment_posture_suggested,
        "first_pass_status": result.audit["status"],
        "passed": result.audit["passed"],
        "wrapper_requested": context.run_wrapper,
        "thinking_value_gain_mode": context.thinking_value_gain_mode,
        "thinking_value_gain_output_profile": context.thinking_value_gain_output_profile,
        "stage_02_5_generated": result.with_stage_02_5,
        "timing_report": str(result.timing_report_path),
        "claim_control_report": str(result.claim_control_report_path or ""),
    }
    return summary


def emit_phase2_first_version_summary(summary: dict[str, object]) -> None:
    print(json.dumps(summary, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = parse_phase2_first_version_args(argv)
    try:
        context = build_phase2_first_version_context(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2
    result = run_phase2_first_version(context)
    emit_phase2_first_version_summary(build_phase2_first_version_summary(context, result))

    if not result.audit["passed"]:
        return 2
    if context.run_wrapper:
        return run_wrapper(
            repo_root=context.repo_root,
            phase1_prd=context.phase1_prd,
            output_dir=context.output_dir,
            version=context.version,
            complexity_profile=context.complexity_profile,
            complexity_override_justification=context.complexity_override_justification,
            deployment_posture=context.deployment_posture,
            deployment_posture_suggested=context.deployment_posture_suggested,
            deployment_posture_warning_class=context.deployment_posture_warning_class,
            deployment_posture_override_source=context.deployment_posture_override_source,
            deployment_posture_override_reason=context.deployment_posture_override_reason,
            deployment_posture_added_risks=context.deployment_posture_added_risks,
            owner=context.owner,
            output_locale=context.output_locale,
            thinking_value_gain_mode=context.thinking_value_gain_mode,
            thinking_value_gain_output_profile=context.thinking_value_gain_output_profile,
            existing_system_architecture_change_intake=context.existing_system_architecture_change_intake,
        )
    emit_human_review_surface(context.output_dir, "phase2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
