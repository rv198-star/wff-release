#!/usr/bin/env python3
"""
Phase-2 first-version shared support layer.

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
from string import Template
from typing import Any

from common.complexity_classifier import INTEGRATION_PATTERNS, classify_phase1_prd, count_external_integrations
from common.claim_control_runtime import (
    emit_path_b_claim_control_sidecar,
)
from common.markdown_table_tools import render_markdown_table, sanitize_markdown_table_cell
from common.script_data_assets import load_script_json_asset
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
from phase2.projection_utils import to_snake, unique_preserve
from phase2.phase2_claim_authority import (
    audit_phase2_artifact_upstream_claim_refs,
    phase1_claims_for_phase2,
    phase2_claim_control_claim_ceiling,
    phase2_claim_control_report_status,
)
from phase2.phase2_quality_gate_specs import normalized_complexity_profile, profile_minimum
from phase2.scaffold_phase2_case import build_manifest, ensure_output_dir, infer_case_name, write_text
from phase2.interface_projection import (
    ServiceProjectionSpec,
    contract_schema_fields as projected_contract_schema_fields,
    enrich_request_example_with_request_mappings as enrich_projected_request_example_with_request_mappings,
    request_example as projected_request_example,
    response_example as projected_response_example,
    sample_request_example_value as projected_sample_request_example_value,
    semantic_service_key as projected_semantic_service_key,
    set_nested_request_example_path as set_projected_nested_request_example_path,
)
from phase2.schema_projection import (
    NULLABLE_SCHEMA_FIELD_TYPES,
    flatten_schema_fields as flatten_projected_schema_fields,
    infer_schema_field_type as infer_projected_schema_field_type,
)
from phase2.table_projection import (
    object_requires_persistent_table,
    persistent_business_objects,
    semantic_table_design_template,
    semantic_table_name,
    semantic_table_owner,
    table_design_template,
    unique_semantic_objects,
)
from phase2.technical_naming import (
    ascii_pascal as technical_ascii_pascal,
    ascii_slug as technical_ascii_slug,
    ascii_snake as technical_ascii_snake,
    ascii_words as technical_ascii_words,
    choose_technical_pascal as choose_technical_pascal_name,
    choose_technical_slug as choose_technical_slug_name,
    choose_technical_snake as choose_technical_snake_name,
    looks_like_generic_object_descriptor,
    short_stable_suffix,
    synthetic_technical_name_report,
    technical_candidate_order,
    technical_name_is_review_bound,
)
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path, write_cross_phase_profiled_surface
from common.output_language import resolve_output_locale
from phase2.existing_system_architecture_change import (
    materialize_existing_system_architecture_change_intake,
    render_existing_system_architecture_change_addendum,
    resolve_existing_system_architecture_change_intake,
)
from phase2.validate_fresh_first_pass_case import inspect_case

try:
    from common.human_review_surface import emit_human_review_surface as _emit_full_review_surface
except ModuleNotFoundError:  # profile pack may intentionally omit the full review surface runtime
    _emit_full_review_surface = None


WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase2/data/stage-01-architecture-definition.md.template",
    "scripts/phase2/data/stage-02-domain-decomposition.md.template",
    "scripts/phase2/data/stage-02-5-third-party-integration.md.template",
    "scripts/phase2/data/stage-03-data-interface-design.md.template",
    "scripts/phase2/data/stage-04-design-convergence.md.template",
    "scripts/phase2/data/stage-03-design-defaults.json",
    "scripts/phase2/data/phase2-first-version-runtime-rules.json",
)


def load_phase2_data_asset(asset_name: str) -> Any:
    return load_script_json_asset(__file__, asset_name)


def load_stage_03_design_defaults() -> dict[str, Any]:
    return load_phase2_data_asset("stage-03-design-defaults.json")


def load_phase2_text_asset(asset_name: str) -> str:
    return (Path(__file__).resolve().parent / "data" / asset_name).read_text(encoding="utf-8")


def render_phase2_template(asset_name: str, values: dict[str, object]) -> str:
    return Template(load_phase2_text_asset(asset_name)).safe_substitute(
        {key: str(value) for key, value in values.items()}
    )

_PHASE2_FIRST_VERSION_RUNTIME_RULES = load_phase2_data_asset("phase2-first-version-runtime-rules.json")

DEFAULT_ADR_TITLES = [
    str(title) for title in _PHASE2_FIRST_VERSION_RUNTIME_RULES.get("default_adr_titles", [])
]
_DEFAULT_GENERIC_ADR_TITLES = _PHASE2_FIRST_VERSION_RUNTIME_RULES.get("default_generic_adr_titles", {})
_DEFAULT_GENERIC_FORBIDDEN_ASSUMPTIONS = _PHASE2_FIRST_VERSION_RUNTIME_RULES.get(
    "default_generic_forbidden_assumptions",
    {},
)
DEFAULT_GENERIC_HANDOFF_ADR_TITLE = str(_DEFAULT_GENERIC_ADR_TITLES.get("handoff", ""))
DEFAULT_GENERIC_ASYNC_COMPLETION_ADR_TITLE = str(_DEFAULT_GENERIC_ADR_TITLES.get("async_completion", ""))
DEFAULT_GENERIC_EXTENSION_SEAM_ADR_TITLE = str(_DEFAULT_GENERIC_ADR_TITLES.get("extension_seam", ""))
DEFAULT_GENERIC_AUTO_EXECUTE_FORBIDDEN = str(_DEFAULT_GENERIC_FORBIDDEN_ASSUMPTIONS.get("auto_execute", ""))
DEFAULT_GENERIC_DEFERRED_SEAM_FORBIDDEN = str(_DEFAULT_GENERIC_FORBIDDEN_ASSUMPTIONS.get("deferred_seam", ""))
PHASE2_FIRST_VERSION_AUTHORITY: dict[str, Any] = dict(
    _PHASE2_FIRST_VERSION_RUNTIME_RULES.get("first_version_authority", {})
)

_STAGE_02_5_DEPENDENCY_ROW_TEMPLATES = {
    str(key): [str(item) for item in value]
    for key, value in _PHASE2_FIRST_VERSION_RUNTIME_RULES.get("stage_02_5_dependency_row_templates", {}).items()
    if isinstance(value, list)
}
_STAGE_02_5_FALLBACK_DEPENDENCY_ROW_TEMPLATE = [
    str(item)
    for item in _PHASE2_FIRST_VERSION_RUNTIME_RULES.get("stage_02_5_fallback_dependency_row_template", [])
]



def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit_review_surface(output_dir: Path, phase: str) -> dict[str, Any]:
    if _emit_full_review_surface is not None:
        return _emit_full_review_surface(output_dir, phase)
    surface_dir = output_dir / "human-review"
    surface_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "review-surface-fallback.v1",
        "phase": phase,
        "surface_dir": "human-review",
        "review_surface_dir": "human-review",
        "review_model": "AI / External Red-Team Review",
        "status": "review-bound",
        "claim_ceiling": "compact profile fallback only; full review surface runtime not shipped in this install profile",
        "claim_ceiling_blocks_ready": False,
    }
    (surface_dir / "HUMAN_REVIEW_SURFACE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (surface_dir / "RED_TEAM_FINDINGS.md").write_text(
        "# AI / External Red-Team Review Findings\n\n"
        "- status: `review-bound`\n"
        "- reason: `full review surface runtime not shipped in this install profile`\n"
        "- authority: review may confirm or lower machine claim ceilings; it must not upgrade them.\n",
        encoding="utf-8",
    )
    return manifest


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


def service_projection_spec(service: ServiceSpec) -> ServiceProjectionSpec:
    return ServiceProjectionSpec(
        service_name=service.service_name,
        domain=service.domain,
        home_module=service.home_module,
        service_type=service.service_type,
        owns_or_coordinates=service.owns_or_coordinates,
        primary_inbound=service.primary_inbound,
        primary_outbound=service.primary_outbound,
        purpose=service.purpose,
        public_contract=service.public_contract,
        endpoint_name=service.endpoint_name,
        method=service.method,
        path=service.path,
        technical_name=service.technical_name,
        technical_slug=service.technical_slug,
    )


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



def choose_technical_pascal(raw: str, *alias_candidates: str, prefix: str = "Entity") -> str:
    return choose_technical_pascal_name(raw, *alias_candidates, prefix=prefix)


def choose_technical_snake(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    return choose_technical_snake_name(raw, *alias_candidates, prefix=prefix)


def choose_technical_slug(raw: str, *alias_candidates: str, prefix: str = "entity") -> str:
    return choose_technical_slug_name(raw, *alias_candidates, prefix=prefix)


def slugify(raw: str) -> str:
    return choose_technical_slug(raw, prefix="item")


def split_inline_values(value: str) -> list[str]:
    return unique_preserve(
        [
            item.strip().strip("`")
            for item in re.split(r"[;,]", str(value or ""))
            if item.strip().strip("`") and item.strip().strip("`") != "—"
        ]
    )


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


def looks_like_encoded_identifier(value: str) -> bool:
    stripped = str(value or "").strip()
    return bool(re.search(r"(?:^|[A-Z])U[0-9A-F]{4}", stripped) or re.search(r"(?:^|[_-])u[0-9a-f]{4}", stripped))


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
        sanitized_module["home_namespace"] = str(
            module.get("home_namespace") or f"{root_namespace}.{slugify(name).replace('-', '.')}"
        )
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


def semantic_service_key(service: ServiceSpec) -> str:
    return projected_semantic_service_key(service_projection_spec(service))


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


__all__ = [name for name in globals() if not name.startswith("__")]
