#!/usr/bin/env python3
"""
Quality gates and baseline comparison for Phase-2 design/architecture runs.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.complexity_classifier import count_external_integrations
from common.cross_phase_surface_policy import find_cross_phase_surface_path
from common.gwt_format_checker import GIVEN_PATTERN, THEN_PATTERN, WHEN_PATTERN, analyze_gwt_block
from phase1.phase1_phase2_coverage import analyze_phase1_phase2_coverage_contract

STAGE_KEYS = ("stage_01", "stage_02", "stage_03", "stage_04")

BASELINE_METRIC_ORDER = [
    "stage_01_line_count",
    "stage_02_line_count",
    "stage_03_line_count",
    "stage_04_line_count",
    "architecture_decisions_count",
    "structured_adr_multi_alt_count",
    "decision_trace_registry_count",
    "forbidden_assumptions_count",
    "mermaid_C4Context_count",
    "mermaid_C4Container_count",
    "mermaid_stateDiagram_count",
    "mermaid_sequenceDiagram_count",
    "stage_01_auth_sequence_diagram_present",
    "mermaid_erDiagram_count",
    "mermaid_gantt_count",
    "domain_count",
    "service_candidate_count",
    "aggregate_catalog_count",
    "canonical_object_structure_count",
    "service_endpoint_mapping_count",
    "er_entity_count",
    "domain_event_count",
    "schema_table_count",
    "schema_field_registry_count",
    "schema_field_registry_specific_type_count",
    "index_strategy_entry_count",
    "data_sensitivity_matrix_count",
    "api_endpoint_count",
    "api_contract_control_count",
    "api_error_type_split_count",
    "response_error_contract_present",
    "contract_trace_registry_count",
    "rbi_count",
    "rbi_trace_registry_count",
    "verification_replay_count",
    "scenario_count",
    "scenario_quantified_acceptance_count",
    "scenario_concurrent_conflict_count",
    "public_boundary_name_count",
    "work_package_count",
    "structured_work_package_count",
    "observability_readiness_count",
    "tech_selection_structured_depth_count",
    "tech_selection_long_term_ops_depth_count",
    "esp_implementation_section_count",
    "implementation_entry_checklist_count",
]

NON_BLOCKING_BASELINE_REGRESSION_KEYS = {
    "stage_01_line_count",
    "stage_02_line_count",
    "stage_03_line_count",
    "stage_04_line_count",
}

DELIVERABLE_SPECS = [
    ("system boundary statement", "stage_01", "system_boundary_statement", "presence", "mandatory", "always"),
    ("constraint posture", "stage_01", "constraints", "presence", "mandatory", "always"),
    ("quality attribute / NFR absorption", "stage_01", "quality_attribute_structure", "stage_01_quality_attributes", "mandatory", "always"),
    ("capability map", "stage_01", "capability_map", "presence", "mandatory", "always"),
    ("architecture direction", "stage_01", "architecture_direction", "presence", "mandatory", "always"),
    ("key architecture decisions", "stage_01", "key_architecture_decisions", "stage_01_architecture_decisions", "mandatory", "always"),
    ("security architecture sketch", "stage_01", "security_architecture_sketch", "presence", "mandatory", "always"),
    ("capacity estimation", "stage_01", "capacity_estimation", "stage_01_capacity", "mandatory", "always"),
    ("domain map", "stage_02", "domain_map", "stage_02_domains", "mandatory", "always"),
    ("module map", "stage_02", "module_map", "stage_02_modules", "mandatory", "always"),
    ("service candidates", "stage_02", "service_candidates", "stage_02_services", "mandatory", "always"),
    ("responsibility matrix", "stage_02", "responsibility_matrix", "presence", "mandatory", "always"),
    ("dependency / collaboration map", "stage_02", "dependency_collaboration_map", "presence", "mandatory", "always"),
    ("decomposition decisions", "stage_02", "decomposition_decisions", "presence", "mandatory", "always"),
    ("conceptual entity relationship diagram", "stage_02", "entity_relationship_diagram", "stage_02_er", "mandatory", "always"),
    ("domain event catalog", "stage_02", "domain_event_catalog", "stage_02_events", "conditional", "eventful_domain"),
    ("data model summary", "stage_03", "data_model_summary", "presence", "mandatory", "always"),
    ("data ownership map", "stage_03", "data_ownership_map", "presence", "mandatory", "always"),
    ("storage strategy", "stage_03", "storage_strategy", "stage_03_storage", "mandatory", "always"),
    ("schema draft", "stage_03", "schema_draft", "stage_03_schema", "mandatory", "always"),
    ("interface contracts", "stage_03", "interface_contracts", "presence", "mandatory", "always"),
    ("API endpoint draft", "stage_03", "api_endpoint_draft", "stage_03_api", "mandatory", "always"),
    ("interaction flow", "stage_03", "interaction_flow", "presence", "mandatory", "always"),
    ("security architecture outline", "stage_03", "security_architecture_outline", "presence", "mandatory", "always"),
    ("technology stack and deployment assumptions", "stage_03", "technology_stack_and_deployment_assumptions", "presence", "mandatory", "always"),
    ("technology selection evaluation matrix", "stage_03", "technology_selection_evaluation_matrix", "stage_03_tech_selection", "conditional", "tradeoff_heavy"),
    ("dominant bottleneck hypothesis", "stage_03", "dominant_bottleneck_hypothesis", "presence", "mandatory", "always"),
    ("architecture alternative candidate set", "stage_03", "architecture_alternative_candidate_set", "presence", "conditional", "tradeoff_heavy"),
    ("baseline insufficiency note", "stage_03", "baseline_insufficiency_note", "presence", "conditional", "tradeoff_heavy"),
    ("constraint-dominant optimum candidate", "stage_03", "constraint_dominant_optimum_candidate", "presence", "conditional", "tradeoff_heavy"),
    ("capacity and performance assumptions", "stage_03", "capacity_and_performance_assumptions", "presence", "conditional", "capacity_sensitive"),
    ("scenario coverage matrix", "stage_03", "scenario_coverage_matrix", "stage_03_scenarios", "mandatory", "always"),
    ("key tradeoff decisions", "stage_03", "key_tradeoff_decisions", "presence", "conditional", "tradeoff_heavy"),
    ("architecture convergence summary", "stage_04", "architecture_convergence_summary", "stage_04_convergence", "mandatory", "always"),
    ("prototype or structured delivery expression", "stage_04", "prototype_or_structured_delivery_expression", "presence", "conditional", "delivery_prototype_needed"),
    ("critical interaction sequence set", "stage_04", "critical_interaction_sequence_set", "stage_04_sequences", "mandatory", "always"),
    ("optimality review", "stage_04", "optimality_review", "presence", "mandatory", "always"),
    ("design verification notes", "stage_04", "design_verification_notes", "stage_04_design_verification", "mandatory", "always"),
    ("unresolved risks and review-bound items", "stage_04", "unresolved_risks_and_review_bound_items", "stage_04_rbi", "mandatory", "always"),
    ("implementation handoff package", "stage_04", "implementation_handoff_package", "presence", "mandatory", "always"),
    ("implementation task sketch", "stage_04", "implementation_task_sketch", "stage_04_work_packages", "mandatory", "always"),
]

COMPLEXITY_PROFILES = ("micro", "standard", "complex")

PROFILE_MINIMUMS = {
    "micro": {
        "stage_01_architecture_decisions": 4,
        "stage_01_decision_trace_registry": 4,
        "stage_01_forbidden_assumptions": 3,
        "stage_01_quality_attributes": 3,
        "stage_01_capacity_numbers": 2,
        "stage_01_capability_groups": 2,
        "stage_01_capability_labels": 2,
        "stage_02_domains": 3,
        "stage_02_modules": 3,
        "stage_02_services": 5,
        "stage_02_aggregate_catalog": 4,
        "stage_02_service_endpoint_mapping": 5,
        "stage_02_lifecycle_mermaid_bindings": 2,
        "stage_02_state_diagrams": 2,
        "stage_02_domain_events": 6,
        "stage_02_er_entities": 6,
        "stage_03_schema_tables": 5,
        "stage_03_index_strategy_entries": 3,
        "stage_03_api_endpoints": 5,
        "stage_03_contract_trace_registry": 3,
        "stage_03_tech_selection_candidates": 3,
        "stage_03_interface_contract_schemas": 2,
        "stage_03_api_operational_controls": 1,
        "stage_03_alt_candidate_structure": 3,
        "stage_03_public_boundary_namespaces": 3,
        "stage_03_scenarios": 5,
        "stage_03_scenario_concurrent_conflicts": 1,
        "stage_03_mermaid_flowcharts": 2,
        "stage_04_sequence_diagrams": 2,
        "stage_04_work_packages": 3,
        "stage_04_rbi_items": 3,
        "stage_04_slice_acceptance": 2,
        "stage_04_design_verification": 3,
        "stage_04_verification_replay": 2,
        "stage_04_rbi_trace_registry": 3,
        "stage_04_observability": 3,
    },
    "standard": {
        "stage_01_architecture_decisions": 7,
        "stage_01_decision_trace_registry": 7,
        "stage_01_forbidden_assumptions": 5,
        "stage_01_quality_attributes": 4,
        "stage_01_capacity_numbers": 3,
        "stage_01_capability_groups": 3,
        "stage_01_capability_labels": 3,
        "stage_02_domains": 4,
        "stage_02_modules": 5,
        "stage_02_services": 8,
        "stage_02_aggregate_catalog": 6,
        "stage_02_service_endpoint_mapping": 8,
        "stage_02_lifecycle_mermaid_bindings": 3,
        "stage_02_state_diagrams": 3,
        "stage_02_domain_events": 10,
        "stage_02_er_entities": 10,
        "stage_03_schema_tables": 10,
        "stage_03_index_strategy_entries": 5,
        "stage_03_api_endpoints": 10,
        "stage_03_contract_trace_registry": 5,
        "stage_03_tech_selection_candidates": 5,
        "stage_03_interface_contract_schemas": 3,
        "stage_03_api_operational_controls": 2,
        "stage_03_alt_candidate_structure": 4,
        "stage_03_public_boundary_namespaces": 5,
        "stage_03_scenarios": 8,
        "stage_03_scenario_concurrent_conflicts": 2,
        "stage_03_mermaid_flowcharts": 2,
        "stage_04_sequence_diagrams": 3,
        "stage_04_work_packages": 4,
        "stage_04_rbi_items": 5,
        "stage_04_slice_acceptance": 3,
        "stage_04_design_verification": 4,
        "stage_04_verification_replay": 3,
        "stage_04_rbi_trace_registry": 5,
        "stage_04_observability": 4,
    },
    "complex": {
        "stage_01_architecture_decisions": 10,
        "stage_01_decision_trace_registry": 10,
        "stage_01_forbidden_assumptions": 5,
        "stage_01_quality_attributes": 5,
        "stage_01_capacity_numbers": 4,
        "stage_01_capability_groups": 4,
        "stage_01_capability_labels": 4,
        "stage_02_domains": 5,
        "stage_02_modules": 6,
        "stage_02_services": 10,
        "stage_02_aggregate_catalog": 8,
        "stage_02_service_endpoint_mapping": 10,
        "stage_02_lifecycle_mermaid_bindings": 5,
        "stage_02_state_diagrams": 5,
        "stage_02_domain_events": 15,
        "stage_02_er_entities": 15,
        "stage_03_schema_tables": 15,
        "stage_03_index_strategy_entries": 8,
        "stage_03_api_endpoints": 15,
        "stage_03_contract_trace_registry": 8,
        "stage_03_tech_selection_candidates": 6,
        "stage_03_interface_contract_schemas": 4,
        "stage_03_api_operational_controls": 3,
        "stage_03_alt_candidate_structure": 5,
        "stage_03_public_boundary_namespaces": 6,
        "stage_03_scenarios": 12,
        "stage_03_scenario_concurrent_conflicts": 3,
        "stage_03_mermaid_flowcharts": 4,
        "stage_04_sequence_diagrams": 5,
        "stage_04_work_packages": 6,
        "stage_04_rbi_items": 6,
        "stage_04_slice_acceptance": 4,
        "stage_04_design_verification": 5,
        "stage_04_verification_replay": 4,
        "stage_04_rbi_trace_registry": 6,
        "stage_04_observability": 5,
    },
}

UNCERTAINTY_RE = re.compile(r"\b(review-bound|unknown|deferred)\b", re.IGNORECASE)
BLOCKED_STATUS_RE = re.compile(r"(^|\|)\s*`?blocked(?: for implementation-facing handoff)?`?\s*(\||$)", re.IGNORECASE)
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
HTTP_STATUS_RE = re.compile(r"\b[45]\d\d\b")
URL_RE = re.compile(r"https?://[^\s`|;]+", re.IGNORECASE)
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
QUANT_SIGNAL_RE = re.compile(
    r"(?:>=|<=|>|<|=|\b\d+(?:\.\d+)?\b|\bp95\b|\bp99\b|\btps\b|\bqps\b|\breq/?min\b|%|\bms\b|\bsec(?:ond)?s?\b|\bmin(?:ute)?s?\b|\bhour?s?\b|\bday?s?\b)",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\b(?:tbd|todo|placeholder|n/?a|not decided|later)\b", re.IGNORECASE)
HTTP_METHOD_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)$", re.IGNORECASE)
SQLISH_DATA_TYPE_RE = re.compile(
    r"\b(?:uuid|jsonb?|varchar(?:\(\d+\))?|char(?:\(\d+\))?|text|boolean|bool|integer|bigint|smallint|int(?:eger)?|numeric(?:\(\d+(?:,\d+)?\))?|decimal(?:\(\d+(?:,\d+)?\))?|float|double|real|date|time|timestamp(?:tz)?|timestamptz|bytea|inet|citext)\b",
    re.IGNORECASE,
)
GENERIC_DATA_TYPE_RE = re.compile(r"^(?:string|number|object|array|map|dict|value|field|unknown)$", re.IGNORECASE)
ESP_MISSING_MARKER_RE = re.compile(
    r"^\s*-\s+(?:missing|schema draft missing|work package registry missing|rbi registry missing)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
CONCURRENT_CONFLICT_RE = re.compile(
    r"\b(?:concurrent|concurrency)[-_ ]?(?:conflict|collision)\b|\bconflict\b",
    re.IGNORECASE,
)
CONCURRENCY_STRATEGY_RE = re.compile(
    r"\b(?:optimistic[_ -]?lock|pessimistic[_ -]?lock|compare[- ]and[- ]swap|cas|version(?:ed)? write|merge|last[_ -]?write[_ -]?wins|serialized?|queue-based serialization|retry on version conflict)\b",
    re.IGNORECASE,
)
BUSINESS_ERROR_RE = re.compile(r"\bbusiness[_ -]?error\b", re.IGNORECASE)
SYSTEM_ERROR_RE = re.compile(r"\bsystem[_ -]?error\b", re.IGNORECASE)
NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9][a-z0-9_-]*)+$")

TECH_SELECTION_DIMENSION_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("reliability", ("reliability",)),
    ("performance_capacity", ("performance/capacity", "performance_capacity", "performance_capacity_posture")),
    ("scalability", ("scalability",)),
    ("maintainability", ("maintainability",)),
    ("development_cost", ("development cost", "development_cost")),
    (
        "operations_cost",
        (
            "operations/maintenance cost",
            "operations_cost",
            "operations_maintenance_cost",
            "tco",
            "total_cost_of_ownership",
            "ownership_cost",
        ),
    ),
    (
        "ecosystem_maturity",
        (
            "ecosystem maturity",
            "ecosystem_maturity",
            "community_support",
            "community_activity",
            "community_health",
        ),
    ),
    ("security_compliance", ("security/compliance posture", "security_compliance_posture", "security_compliance")),
    ("deployment_complexity", ("deployment complexity", "deployment_complexity")),
    ("integration_cost", ("integration cost", "integration_cost", "integration_complexity", "integration_fit")),
    ("observability", ("observability", "observability_support", "telemetry_support")),
    ("migration_path", ("migration_path", "migration burden", "migration_burden", "reversibility")),
    ("vendor_risk", ("vendor risk", "vendor_risk", "licensing", "license_model", "license posture")),
    ("learning_curve", ("learning_curve",)),
    ("failure_mode", ("failure_mode", "failure posture", "failure_handling")),
)
REQUIRED_TECH_SELECTION_LONG_TERM_FAMILIES = ("operations_cost", "ecosystem_maturity", "observability")
SCENARIO_CATEGORY_HEADER_ALIASES = ("scenario_type", "scenario_category", "scenario_kind", "category")
OPTIONAL_STAGE_02_5_STATUS_VALUES = {"active", "skipped"}

HEADING_ALIASES: dict[str, tuple[str, ...]] = {
    "2.1 Quick-Start Reading Path": ("2.1 Quick-Start Reading Path", "2.1 快速阅读路径"),
    "2.2 Working Glossary": ("2.2 Working Glossary", "2.2 工作术语表"),
    "5.2 Schema Draft": ("5.2 Schema Draft", "5.2 Schema 草案"),
    "6. API Summary": ("6. API Summary", "6. API 摘要"),
    "9. Realizability Judgment": ("9. Realizability Judgment", "9. 可实现性判断"),
    "10.4 Implementation Start Order": ("10.4 Implementation Start Order", "10.4 实现启动顺序"),
    "10.5 Schema and Data Migration Focus": ("10.5 Schema and Data Migration Focus", "10.5 Schema 与数据迁移重点"),
    "10.6 Contract Freeze and Adapter Boundaries": (
        "10.6 Contract Freeze and Adapter Boundaries",
        "10.6 合同冻结与适配器边界",
    ),
    "10.7 Operational Rollout Guardrails": ("10.7 Operational Rollout Guardrails", "10.7 运营发布护栏"),
    "10.8 Observability and Operational Readiness": (
        "10.8 Observability and Operational Readiness",
        "10.8 可观测性与运维就绪",
    ),
    "10.9 Identity, Auth Vendor, and Key Lifecycle": (
        "10.9 Identity, Auth Vendor, and Key Lifecycle",
        "10.9 身份、认证供应商与密钥生命周期",
    ),
    "10.10 Phase-3 Onboarding Summary": ("10.10 Phase-3 Onboarding Summary", "10.10 Phase-3 接入摘要"),
    "2.1 Quick-Start Onboarding Snapshot": ("2.1 Quick-Start Onboarding Snapshot", "2.1 快速接入快照"),
}

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "environment_or_dependency_prerequisites": ("environment_or_dependency_prerequisites", "环境或依赖前置条件"),
    "must_not_assume": ("must_not_assume", "不得假设"),
    "strongest_supported_readiness_label": ("strongest_supported_readiness_label", "最强可支持就绪标签"),
}


def heading_aliases(heading: str) -> tuple[str, ...]:
    aliases = HEADING_ALIASES.get(heading)
    if aliases is None:
        return (heading,)
    return aliases


def field_aliases(field_name: str) -> tuple[str, ...]:
    aliases = FIELD_ALIASES.get(field_name)
    if aliases is None:
        return (field_name,)
    return aliases


def heading_present(text: str, heading: str, *, level: int = 3) -> int:
    prefixes = tuple("#" * level + f" {alias}" for alias in heading_aliases(heading))
    return int(any(prefix in text for prefix in prefixes))


def field_present(text: str, field_name: str) -> int:
    return int(any(f"- {alias}:" in text for alias in field_aliases(field_name)))


def normalized_complexity_profile(value: str) -> str:
    return value if value in COMPLEXITY_PROFILES else "standard"


def profile_minimum(complexity_profile: str, key: str) -> int:
    profile = normalized_complexity_profile(complexity_profile)
    return int(PROFILE_MINIMUMS.get(profile, PROFILE_MINIMUMS["standard"]).get(key, PROFILE_MINIMUMS["standard"][key]))


EXISTING_SYSTEM_ARCHITECTURE_CHANGE_INTAKE_FILENAME = "existing-system-architecture-change-intake.md"

EXISTING_SYSTEM_CHANGE_REQUIRED_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("packet", ("existing-system-architecture-change",)),
    ("triage", ("architecture change impact triage",)),
    ("compatibility_strategy", ("compatibility_strategy", "compatibility strategy")),
    ("migration_strategy", ("migration_strategy", "migration strategy")),
    ("rollback_strategy", ("rollback_strategy", "rollback strategy")),
    ("decision_gate_status", ("decision_gate_status", "decision gate status")),
)

EXISTING_SYSTEM_CHANGE_BREADTH_CHECKS: dict[str, dict[str, str]] = {
    "stage_02": {
        "domain_events": "stage_02_domain_events",
        "er_entity_depth": "stage_02_er_entities",
    },
    "stage_03": {
        "schema_tables": "stage_03_schema_tables",
        "schema_field_registries": "stage_03_schema_tables",
        "schema_field_type_specificity": "stage_03_schema_tables",
    },
}

EXISTING_SYSTEM_CHANGE_BREADTH_MODES: dict[str, str] = {
    "stage_02_events": "stage_02_domain_events",
    "stage_03_schema": "stage_03_schema_tables",
}


def collect_existing_system_change_context_text(stage_analysis: dict[str, dict[str, Any]]) -> tuple[str, str]:
    parts = [str(analysis.get("text", "")) for analysis in stage_analysis.values()]
    source_path = ""
    for analysis in stage_analysis.values():
        raw_path = str(analysis.get("path", "")).strip()
        if not raw_path:
            continue
        candidate = Path(raw_path).parent / EXISTING_SYSTEM_ARCHITECTURE_CHANGE_INTAKE_FILENAME
        if candidate.exists():
            source_path = str(candidate)
            parts.append(candidate.read_text(encoding="utf-8"))
            break
    return "\n".join(parts), source_path


def detect_existing_system_change_gate_policy(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    text, source_path = collect_existing_system_change_context_text(stage_analysis)
    lowered = text.casefold()
    missing = [
        marker
        for marker, variants in EXISTING_SYSTEM_CHANGE_REQUIRED_MARKERS
        if not any(variant in lowered for variant in variants)
    ]
    return {
        "applied": not missing,
        "source_path": source_path,
        "missing_required_markers": missing,
        "basis": (
            "existing-system architecture change intake present with triage, compatibility, "
            "migration, rollback, and decision-gate markers"
            if not missing
            else "existing-system architecture change intake markers incomplete"
        ),
        "adjusted_checks": [],
    }


def existing_system_change_adjusted_minimum(
    *,
    stage_key: str,
    check_name: str,
    analysis: dict[str, Any],
    complexity_profile: str,
) -> int | None:
    profile_key = EXISTING_SYSTEM_CHANGE_BREADTH_CHECKS.get(stage_key, {}).get(check_name)
    if profile_key is None:
        return None
    micro_floor = profile_minimum("micro", profile_key)
    if check_name in {"schema_field_registries", "schema_field_type_specificity"}:
        micro_floor = max(micro_floor, int(analysis.get("metrics", {}).get("schema_table_count", 0) or 0))
    return min(profile_minimum(complexity_profile, profile_key), micro_floor)


def refresh_stage_gate_state(analysis: dict[str, Any]) -> None:
    checks = analysis.get("checks", [])
    analysis["gate_failures"] = [check for check in checks if not check.get("passed")]
    analysis["quality_gate_passed"] = not analysis["gate_failures"]
    analysis["strongest_check"] = max(
        checks,
        key=lambda item: (int(item.get("current", 0)) - int(item.get("minimum", 0)), int(item.get("current", 0))),
        default=None,
    )
    analysis["weakest_check"] = min(
        checks,
        key=lambda item: (int(item.get("current", 0)) - int(item.get("minimum", 0)), int(item.get("current", 0))),
        default=None,
    )


def apply_existing_system_change_intake_gate_policy(
    stage_analysis: dict[str, dict[str, Any]],
    complexity_profile: str = "standard",
) -> dict[str, Any]:
    """Keep full P2 gates for new projects, but avoid blocking bounded existing-system changes on breadth counts alone."""
    complexity_profile = normalized_complexity_profile(complexity_profile)
    policy = detect_existing_system_change_gate_policy(stage_analysis)
    if not policy["applied"]:
        return policy

    for stage_key, checks_by_name in EXISTING_SYSTEM_CHANGE_BREADTH_CHECKS.items():
        analysis = stage_analysis.get(stage_key)
        if not analysis:
            continue
        for check in analysis.get("checks", []):
            check_name = str(check.get("name", ""))
            if check_name not in checks_by_name:
                continue
            original_minimum = int(check.get("minimum", 0) or 0)
            adjusted_minimum = existing_system_change_adjusted_minimum(
                stage_key=stage_key,
                check_name=check_name,
                analysis=analysis,
                complexity_profile=complexity_profile,
            )
            if adjusted_minimum is None or adjusted_minimum >= original_minimum:
                continue
            current = int(check.get("current", 0) or 0)
            if current >= original_minimum:
                continue
            check["original_minimum"] = original_minimum
            check["minimum"] = adjusted_minimum
            check["passed"] = current >= adjusted_minimum
            check["policy_adjustment"] = "bounded-existing-system-change-breadth-floor"
            evidence = str(check.get("evidence", ""))
            suffix = "bounded existing-system change breadth floor"
            if suffix not in evidence:
                check["evidence"] = f"{evidence} ({suffix})" if evidence else suffix
            policy["adjusted_checks"].append(
                {
                    "stage": stage_key,
                    "check": check_name,
                    "current": current,
                    "original_minimum": original_minimum,
                    "adjusted_minimum": adjusted_minimum,
                    "passed": bool(check["passed"]),
                    "reason": "bounded existing-system change should not be judged by full new-project breadth counts alone",
                }
            )
        refresh_stage_gate_state(analysis)

    return policy


def adjusted_minimum_for_existing_system_change_mode(
    *,
    mode: str,
    metrics: dict[str, Any],
    complexity_profile: str,
    policy: dict[str, Any] | None,
) -> int | None:
    if not policy or not policy.get("applied"):
        return None
    profile_key = EXISTING_SYSTEM_CHANGE_BREADTH_MODES.get(mode)
    if profile_key is None:
        return None
    micro_floor = profile_minimum("micro", profile_key)
    if mode == "stage_03_schema":
        micro_floor = max(micro_floor, int(metrics.get("schema_table_count", 0) or 0))
    return min(profile_minimum(complexity_profile, profile_key), micro_floor)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def block_lines(text: str, block_name: str) -> list[str]:
    lines = text.splitlines()
    start = None
    marker = f"- {block_name}:"
    for idx, line in enumerate(lines):
        if line.startswith(marker):
            start = idx
            break
    if start is None:
        return []
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        collected.append(line)
    return collected


def block_text(text: str, block_name: str) -> str:
    return "\n".join(block_lines(text, block_name)).strip()


def heading_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    prefix = f"## {heading}"
    start = None
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            start = idx
            break
    if start is None:
        return ""
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def markdown_heading_section(text: str, heading: str) -> str:
    for candidate in heading_aliases(heading):
        pattern = re.compile(rf"^(#+)\s+{re.escape(candidate)}\s*$", re.MULTILINE)
        match = pattern.search(text)
        if not match:
            continue
        level = len(match.group(1))
        start = match.start()
        end = len(text)
        for next_match in pattern.finditer(text):
            if next_match.start() == match.start():
                continue
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        general_heading_re = re.compile(r"^(#+)\s+.+$", re.MULTILINE)
        for next_match in general_heading_re.finditer(text, match.end()):
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        return text[start:end].strip()
    return ""


def count_table_rows(text: str) -> int:
    lines = text.splitlines()
    total = 0
    idx = 0
    while idx < len(lines):
        if not lines[idx].lstrip().startswith("|"):
            idx += 1
            continue
        group: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            group.append(lines[idx].strip())
            idx += 1
        if len(group) >= 2:
            total += max(len(group) - 2, 0)
    return total


def normalize_table_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("`").lower())


def markdown_tables(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        if not lines[idx].lstrip().startswith("|"):
            idx += 1
            continue
        group: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            group.append(lines[idx].strip())
            idx += 1
        if len(group) < 2 or "---" not in group[1]:
            continue
        headers = [normalize_table_header(part) for part in group[0].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for row_line in group[2:]:
            parts = [part.strip().strip("`") for part in row_line.strip("|").split("|")]
            if len(parts) < len(headers):
                parts.extend([""] * (len(headers) - len(parts)))
            rows.append(dict(zip(headers, parts)))
        tables.append({"headers": headers, "rows": rows})
    return tables


def mermaid_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    parts = text.split("```mermaid")
    for part in parts[1:]:
        if "```" not in part:
            continue
        body = part.split("```", 1)[0].strip("\n")
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if not lines:
            continue
        blocks.append((lines[0], body))
    return blocks


def mermaid_counts(text: str) -> dict[str, int]:
    counts = {
        "C4Context": 0,
        "C4Container": 0,
        "stateDiagram-v2": 0,
        "sequenceDiagram": 0,
        "erDiagram": 0,
        "gantt": 0,
        "flowchart_TD": 0,
        "flowchart_LR": 0,
    }
    for first_line, _ in mermaid_blocks(text):
        if first_line.startswith("C4Context"):
            counts["C4Context"] += 1
        elif first_line.startswith("C4Container"):
            counts["C4Container"] += 1
        elif first_line.startswith("stateDiagram-v2"):
            counts["stateDiagram-v2"] += 1
        elif first_line.startswith("sequenceDiagram"):
            counts["sequenceDiagram"] += 1
        elif first_line.startswith("erDiagram"):
            counts["erDiagram"] += 1
        elif first_line.startswith("gantt"):
            counts["gantt"] += 1
        elif first_line.startswith("flowchart TD"):
            counts["flowchart_TD"] += 1
        elif first_line.startswith("flowchart LR"):
            counts["flowchart_LR"] += 1
    return counts


def count_regex(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.MULTILINE))


def count_unique_wp(text: str) -> int:
    return len(set(re.findall(r"WP-[A-Z0-9]+", text)))


def count_review_bound_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if has_uncertainty_marker(line))


def sanitize_uncertainty_scan_text(text: str) -> str:
    return re.sub(r"pass-with-review-bound-items", "", text, flags=re.IGNORECASE)


def has_uncertainty_marker(text: str) -> bool:
    sanitized = sanitize_uncertainty_scan_text(text)
    return bool(UNCERTAINTY_RE.search(sanitized) or BLOCKED_STATUS_RE.search(sanitized))


def count_marked_structured_items(block: str) -> int:
    count = 0
    lines = block.splitlines()
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            idx += 1
            continue
        if stripped.startswith("|"):
            table_group: list[str] = []
            while idx < len(lines) and lines[idx].strip().startswith("|"):
                table_group.append(lines[idx].strip())
                idx += 1
            data_rows = table_group[2:] if len(table_group) >= 2 and "---" in table_group[1] else table_group[1:]
            count += sum(1 for row in data_rows if has_uncertainty_marker(row))
            continue
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            if content.endswith(":") and ":" not in content[:-1]:
                idx += 1
                continue
            if has_uncertainty_marker(stripped):
                count += 1
        idx += 1
    return count


def count_quality_attributes(block: str) -> int:
    matches = re.findall(r"^\s{4}- [^:\n]+:", block, flags=re.MULTILINE)
    return len(
        [
            item
            for item in matches
            if not any(
                ignored in item
                for ignored in (
                    "required_entry_template",
                    "quantified_target",
                    "metric_name",
                    "target_value",
                    "measurement_window",
                    "design_implication",
                    "evidence_or_source",
                )
            )
        ]
    )


def count_structured_adr_entries(block: str) -> int:
    entries = re.findall(r"^\s{2}- [^:\n]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = (
        "ad_id:",
        "title:",
        "status:",
        "context:",
        "decision:",
        "alternatives_considered:",
        "consequences:",
        "evidence:",
    )
    count = 0
    for entry in entries:
        if all(token in entry for token in required_tokens):
            count += 1
    return count


def count_structured_adr_entries_with_multiple_alternatives(block: str) -> int:
    entries = re.findall(r"^\s{2}- [^:\n]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = (
        "ad_id:",
        "title:",
        "status:",
        "context:",
        "decision:",
        "alternatives_considered:",
        "consequences:",
        "evidence:",
    )
    count = 0
    for entry in entries:
        if not all(token in entry for token in required_tokens):
            continue
        if entry.count("alternative_name:") >= 2 and entry.count("rejected_because:") >= 2:
            count += 1
    return count


def count_capability_groups_with_priority_maturity(block: str) -> int:
    entries = re.findall(r"^\s{2}- capability_group_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = (
        "name:",
        "priority:",
        "maturity:",
        "rationale:",
        "covers:",
    )
    return sum(1 for entry in entries if all(token in entry for token in required_tokens))


def count_capability_map_labeled_nodes(text: str) -> int:
    best = 0
    for first_line, body in mermaid_blocks(text):
        if not first_line.startswith("flowchart TD"):
            continue
        priority_hits = re.findall(r"priority\s*=\s*(P0|P1|P2)", body, flags=re.IGNORECASE)
        maturity_hits = re.findall(r"maturity\s*=\s*([A-Za-z-]+)", body, flags=re.IGNORECASE)
        best = max(best, min(len(priority_hits), len(maturity_hits)))
    if best:
        return best
    return count_capability_groups_with_priority_maturity(block_text(text, "capability_map"))


def has_required_tokens(block: str, required_tokens: tuple[str, ...]) -> int:
    return int(all(token in block for token in required_tokens))


def extract_block_scalar(block: str, field_name: str) -> str:
    pattern = rf"{re.escape(field_name)}:\s*\n\s+- `?([^`\n]+)`?"
    match = re.search(pattern, block, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    inline_pattern = rf"^\s*- {re.escape(field_name)}:\s*`?([^`\n][^\n`]*)`?\s*$"
    inline_match = re.search(inline_pattern, block, flags=re.IGNORECASE | re.MULTILINE)
    return inline_match.group(1).strip() if inline_match else ""


def normalize_readiness_label(label: str) -> str:
    value = label.strip().lower()
    if value == "ready-to-implement":
        return "implementation-planning-ready"
    if value in {"implementation-planning-ready", "pass-with-review-bound-items", "blocked"}:
        return value
    return ""


def readiness_rank(label: str) -> int:
    return {
        "blocked": 0,
        "pass-with-review-bound-items": 1,
        "implementation-planning-ready": 2,
    }.get(label, -1)


def count_api_rows_with_json_examples(block: str) -> int:
    required_headers = {
        "endpoint_name",
        "method",
        "path",
        "request_body_example",
        "response_body_example",
    }
    table_count = 0
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        table_count = sum(
            1
            for row in table["rows"]
            if has_parseable_json_example(row.get("request_body_example", ""))
            and has_parseable_json_example(row.get("response_body_example", ""))
        )
        break

    structured_entries = re.findall(r"^\s{2,4}- endpoint_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    structured_count = sum(
        1
        for entry in structured_entries
        if has_parseable_json_example(extract_structured_block(entry, "request_body_example", indent=6))
        and has_parseable_json_example(extract_structured_block(entry, "response_body_example", indent=6))
    )
    return max(table_count, structured_count)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9_/.\-]*", value))


def is_placeholder_like(value: str) -> bool:
    lowered = normalize_text(value).lower()
    return not lowered or bool(PLACEHOLDER_RE.search(lowered))


def is_explicit_missing_marker(value: str) -> bool:
    normalized = normalize_text(value)
    return not normalized or bool(ESP_MISSING_MARKER_RE.fullmatch(f"- {normalized}"))


def structured_field_items(entry: str, field_name: str, *, indent: int = 4) -> list[str]:
    block = extract_structured_block(entry, field_name, indent=indent)
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        if stripped.startswith("- "):
            items.append(normalize_text(stripped[2:].strip("`")))
    return items


def extract_structured_field(entry: str, field_name: str, *, indent: int = 4) -> str:
    candidate_indents = [indent]
    candidate_indents.extend(
        indent_value
        for indent_value in (
            len(match.group(1))
            for alias in field_aliases(field_name)
            for match in re.finditer(rf"^( *)- {re.escape(alias)}:", entry, flags=re.MULTILINE)
        )
        if indent_value not in candidate_indents
    )
    for current_indent in candidate_indents:
        value = extract_structured_field_at_indent(entry, field_name, indent=current_indent)
        if value:
            return value
    return ""


def extract_structured_field_at_indent(entry: str, field_name: str, *, indent: int = 4) -> str:
    lines = entry.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        for alias in field_aliases(field_name):
            prefix = " " * indent + f"- {alias}:"
            if line.startswith(prefix):
                capturing = True
                remainder = line[len(prefix) :].strip()
                if remainder:
                    collected.append(remainder.strip("`"))
                break
        else:
            prefix = ""
        if prefix:
            continue
        if not capturing:
            continue
        if line.startswith(" " * indent + "- ") and not line.startswith(" " * (indent + 2) + "- "):
            break
        stripped = line.strip()
        if stripped:
            collected.append(stripped.strip("`"))
    return normalize_text(" ".join(collected))


def extract_structured_block(entry: str, field_name: str, *, indent: int = 4) -> str:
    candidate_indents = [indent]
    candidate_indents.extend(
        indent_value
        for indent_value in (
            len(match.group(1))
            for alias in field_aliases(field_name)
            for match in re.finditer(rf"^( *)- {re.escape(alias)}:", entry, flags=re.MULTILINE)
        )
        if indent_value not in candidate_indents
    )
    for current_indent in candidate_indents:
        value = extract_structured_block_at_indent(entry, field_name, indent=current_indent)
        if value:
            return value
    return ""


def extract_structured_block_at_indent(entry: str, field_name: str, *, indent: int = 4) -> str:
    lines = entry.splitlines()
    collected: list[str] = []
    capturing = False
    for line in lines:
        for alias in field_aliases(field_name):
            prefix = " " * indent + f"- {alias}:"
            if line.startswith(prefix):
                capturing = True
                remainder = line[len(prefix) :].rstrip()
                if remainder.strip():
                    collected.append(remainder.strip())
                break
        else:
            prefix = ""
        if prefix:
            continue
        if not capturing:
            continue
        if line.startswith(" " * indent + "- ") and not line.startswith(" " * (indent + 2) + "- "):
            break
        collected.append(line.rstrip())
    return "\n".join(collected).strip()


def count_domain_event_entries(block: str) -> int:
    return max(count_table_rows(block), count_regex(block, r"^\s{2}- event_[0-9]+:"))


def deterministic_sample(entries: list[dict[str, Any]], key_fields: tuple[str, ...]) -> dict[str, Any] | None:
    if not entries:
        return None
    return min(
        entries,
        key=lambda entry: (
            hashlib.sha256(
                "|".join(normalize_text(str(entry.get(field, ""))) for field in key_fields).encode("utf-8")
            ).hexdigest(),
            tuple(normalize_text(str(entry.get(field, ""))) for field in key_fields),
        ),
    )


def parse_inline_json_object(value: str) -> bool:
    candidate = value.strip().strip("`")
    if candidate.startswith("{") and candidate.endswith("}"):
        try:
            json.loads(candidate)
            return True
        except json.JSONDecodeError:
            return False
    for obj in re.findall(r"\{[^{}]+\}", candidate):
        try:
            json.loads(obj)
            return True
        except json.JSONDecodeError:
            continue
    return False


def has_parseable_json_example(value: str) -> bool:
    candidate = value.strip()
    for fenced in re.findall(r"```json\s*([\s\S]*?)```", candidate, flags=re.IGNORECASE):
        try:
            json.loads(fenced.strip())
            return True
        except json.JSONDecodeError:
            continue
    return parse_inline_json_object(candidate)


def has_specific_schema_data_type(value: str) -> bool:
    normalized = normalize_text(value).strip("`")
    if not normalized or is_placeholder_like(normalized) or GENERIC_DATA_TYPE_RE.match(normalized):
        return False
    return bool(SQLISH_DATA_TYPE_RE.search(normalized))


def block_scalars_with_content(block: str, field_names: tuple[str, ...], *, minimum_words: int = 4) -> int:
    return int(
        all(
            word_count(extract_block_scalar(block, field_name)) >= minimum_words
            and not is_placeholder_like(extract_block_scalar(block, field_name))
            for field_name in field_names
        )
    )


def block_nested_fields_present(
    block: str,
    parent_field: str,
    child_fields: tuple[str, ...],
    *,
    parent_indent: int = 2,
) -> int:
    nested = extract_structured_block(block, parent_field, indent=parent_indent)
    return int(bool(nested) and all(f"{field}:" in nested for field in child_fields))


def block_nested_fields_with_content(
    block: str,
    parent_field: str,
    child_fields: tuple[str, ...],
    *,
    parent_indent: int = 2,
    child_indent: int = 4,
    minimum_words: int = 1,
) -> int:
    nested = extract_structured_block(block, parent_field, indent=parent_indent)
    if not nested:
        return 0

    def nested_value(field_name: str) -> str:
        value = extract_structured_field(nested, field_name, indent=child_indent)
        if not value and child_indent != 0:
            value = extract_structured_field(nested, field_name, indent=0)
        return value

    return int(
        all(
            word_count(nested_value(field)) >= minimum_words
            and not is_placeholder_like(nested_value(field))
            for field in child_fields
        )
    )


def structured_adr_entries(block: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for match in re.finditer(r"^\s{2}- ([^:\n]+):\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE):
        label = normalize_text(match.group(1).strip("`"))
        entry = match.group(2)
        entries.append(
            {
                "entry_key": label,
                "ad_id": extract_structured_field(entry, "ad_id"),
                "title": extract_structured_field(entry, "title"),
                "context": extract_structured_field(entry, "context"),
                "decision": extract_structured_field(entry, "decision"),
                "evidence": extract_structured_field(entry, "evidence"),
                "consequences": extract_structured_field(entry, "consequences"),
                "alternative_count": entry.count("alternative_name:"),
                "rejected_because_count": entry.count("rejected_because:"),
            }
        )
    return entries


def count_constraint_categories(block: str) -> int:
    categories = (
        "inherited_constraints:",
        "inferred_constraints:",
        "unknown_constraints:",
        "deferred_constraints:",
    )
    return sum(1 for category in categories if category in block)


def count_domains(block: str) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if "domain_name" not in headers:
            continue
        return sum(1 for row in table["rows"] if row.get("domain_name", "").strip())
    by_index = count_regex(block, r"^\s{2}- domain_[0-9]+:")
    if by_index:
        return by_index
    return count_regex(block, r"^\s{4}- domain_name:")


def count_modules(block: str) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if "module_name" not in headers:
            continue
        return sum(1 for row in table["rows"] if row.get("module_name", "").strip())
    return len(set(re.findall(r"`(geo\.[^`]+)`", block)))


def count_service_candidates(block: str) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if "service_name" not in headers:
            continue
        return sum(1 for row in table["rows"] if row.get("service_name", "").strip())
    return count_regex(block, r"^\s{2}- `?[^`\n:]+`?:")


def count_service_candidates_with_canonical_fields(block: str) -> int:
    required_headers = {
        "service_name",
        "domain",
        "home_module",
        "service_type",
        "owns_or_coordinates",
        "primary_inbound",
        "primary_outbound",
        "purpose",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    entries = re.findall(r"^\s{2}- `?[^`\n:]+`?:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = (
        "domain:",
        "home_module:",
        "service_type:",
        "owns_or_coordinates:",
        "primary_inbound:",
        "primary_outbound:",
        "purpose:",
    )
    return sum(1 for entry in entries if all(token in entry for token in required_tokens))


def count_aggregate_catalog_entries(block: str) -> int:
    required_headers = {
        "aggregate_name",
        "aggregate_kind",
        "owning_domain",
        "owning_module",
        "authoritative_service",
        "authoritative_mutations",
        "emitted_events",
        "lifecycle_diagram",
        "public_boundary_status",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_canonical_object_structure_rows(block: str) -> int:
    required_headers = {
        "object_name",
        "authoritative_aggregate",
        "authoritative_service",
        "primary_identifiers",
        "state_or_version_anchor",
        "backing_schema_or_projection",
        "stage_03_contract_or_endpoint",
        "closure_note",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_service_endpoint_mapping_rows(block: str) -> int:
    required_headers = {
        "service_name",
        "home_module",
        "stage_03_endpoint_names",
        "public_contracts",
        "primary_owned_object",
        "mapping_note",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_table_rows_with_headers(block: str, required_headers: set[str]) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def structured_entries(block: str, *, label_prefix: str) -> list[str]:
    return [
        match.group(1)
        for match in re.finditer(
            rf"^\s{{2}}- {re.escape(label_prefix)}[0-9]+:\n((?:^\s{{4,}}.*\n?)*)",
            block,
            flags=re.MULTILINE,
        )
    ]


def count_structured_entries_with_fields(block: str, *, label_prefix: str, required_fields: tuple[str, ...]) -> int:
    entries = structured_entries(block, label_prefix=label_prefix)
    return sum(1 for entry in entries if all(f"{field}:" in entry for field in required_fields))


def normalized_optional_stage_status(value: str) -> str:
    lowered = value.strip().lower()
    return lowered if lowered in OPTIONAL_STAGE_02_5_STATUS_VALUES else ""


def count_aggregate_lifecycle_coverage_rows(block: str) -> int:
    required_headers = {
        "aggregate_name",
        "lifecycle_expression_type",
        "owner_writer",
        "trigger_events",
        "terminal_or_failure_exit",
        "mermaid_binding",
        "closure_note",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_aggregate_lifecycle_mermaid_bindings(block: str) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not {"aggregate_name", "lifecycle_expression_type", "mermaid_binding"}.issubset(headers):
            continue
        return sum(
            1
            for row in table["rows"]
            if row.get("lifecycle_expression_type", "").strip() == "stateDiagram-v2"
            and "no standalone mermaid" not in row.get("mermaid_binding", "").strip().lower()
        )
    return 0


def count_failure_semantics_per_endpoint(block: str) -> tuple[int, int]:
    rows = api_endpoint_entries(block)
    valid = 0
    for row in rows:
        failure_codes = str(row.get("failure_codes", ""))
        statuses = set(HTTP_STATUS_RE.findall(failure_codes))
        if not statuses:
            continue
        semantic_markers = (
            "business_error",
            "system_error",
            "->",
            "retry",
            "caller_after_fix",
            "safe_with_backoff",
            "idempotency",
            "validation",
            "forbidden",
            "duplicate",
            "timeout",
            "not_found",
            "conflict",
            "blocked",
        )
        lowered = failure_codes.lower()
        if any(marker in lowered for marker in semantic_markers):
            valid += 1
    return len(rows), valid


def count_tech_selection_candidates(block: str) -> int:
    return max(count_table_rows(block), count_regex(block, r"^\s{4}- candidate_[0-9]+:"))


def count_tech_candidates_with_evidence_dates(block: str) -> int:
    rows = tech_selection_candidate_entries(block)
    valid = sum(
        1
        for row in rows
        if DATE_RE.search(str(row.get("evidence_sources", "")))
        and not is_placeholder_like(str(row.get("evidence_sources", "")))
        and word_count(str(row.get("evidence_sources", ""))) >= 3
    )
    structured_entries = re.findall(
        r"evidence_sources:\s*(?:\n\s+- (?:source_url|source_document):\s*`?[^`\n]+`?\s*\n\s+- verification_date:\s*`?\d{4}-\d{2}-\d{2}`?)+",
        block,
        flags=re.MULTILINE,
    )
    return max(valid, len(structured_entries))


def table_header_present(headers: set[str], aliases: tuple[str, ...]) -> bool:
    return any(alias in headers for alias in aliases)


def tech_selection_family_aliases(family_key: str) -> tuple[str, ...]:
    for key, aliases in TECH_SELECTION_DIMENSION_FAMILIES:
        if key == family_key:
            return aliases
    return ()


def tech_selection_dimension_count(headers: set[str]) -> int:
    return sum(1 for _, aliases in TECH_SELECTION_DIMENSION_FAMILIES if table_header_present(headers, aliases))


def tech_selection_dimension_count_for_row(row: dict[str, str]) -> int:
    return sum(
        1
        for _, aliases in TECH_SELECTION_DIMENSION_FAMILIES
        if any(
            row.get(alias, "").strip() and not is_placeholder_like(str(row.get(alias, "")))
            for alias in aliases
        )
    )


def tech_selection_required_family_count_for_row(
    row: dict[str, str],
    family_keys: tuple[str, ...] = REQUIRED_TECH_SELECTION_LONG_TERM_FAMILIES,
) -> int:
    return sum(
        1
        for family_key in family_keys
        if any(
            row.get(alias, "").strip() and not is_placeholder_like(str(row.get(alias, "")))
            for alias in tech_selection_family_aliases(family_key)
        )
    )


def count_tech_selection_candidates_with_structured_depth(block: str) -> int:
    best = 0
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not all(header in headers for header in ("candidate_name", "evidence_sources", "final_decision", "rejection_reason")):
            continue
        if tech_selection_dimension_count(headers) < 10:
            continue
        valid_rows = sum(
            1
            for row in table["rows"]
            if all(row.get(header, "").strip() for header in ("candidate_name", "evidence_sources", "final_decision", "rejection_reason"))
            and tech_selection_dimension_count_for_row(row) >= 10
        )
        best = max(best, valid_rows)

    structured_entries = re.findall(r"^\s{4}- candidate_[0-9]+:\n((?:^\s{6,}.*\n?)*)", block, flags=re.MULTILINE)
    structured_count = 0
    for entry in structured_entries:
        candidate = {
            "candidate_name": extract_structured_field(entry, "candidate_name", indent=6),
            "reliability": extract_structured_field(entry, "reliability", indent=6),
            "performance_capacity": extract_structured_field(entry, "performance_capacity", indent=6),
            "scalability": extract_structured_field(entry, "scalability", indent=6),
            "maintainability": extract_structured_field(entry, "maintainability", indent=6),
            "development_cost": extract_structured_field(entry, "development_cost", indent=6),
            "operations_cost": extract_structured_field(entry, "operations_cost", indent=6),
            "ecosystem_maturity": extract_structured_field(entry, "ecosystem_maturity", indent=6),
            "security_compliance_posture": extract_structured_field(entry, "security_compliance_posture", indent=6),
            "deployment_complexity": extract_structured_field(entry, "deployment_complexity", indent=6),
            "integration_cost": extract_structured_field(entry, "integration_cost", indent=6),
            "integration_fit": extract_structured_field(entry, "integration_fit", indent=6),
            "observability": extract_structured_field(entry, "observability", indent=6),
            "migration_path": extract_structured_field(entry, "migration_path", indent=6),
            "vendor_risk": extract_structured_field(entry, "vendor_risk", indent=6),
            "learning_curve": extract_structured_field(entry, "learning_curve", indent=6),
            "failure_mode": extract_structured_field(entry, "failure_mode", indent=6),
            "evidence_sources": extract_structured_field(entry, "evidence_sources", indent=6),
            "final_decision": extract_structured_field(entry, "final_decision", indent=6),
            "rejection_reason": extract_structured_field(entry, "rejection_reason", indent=6),
        }
        if all(
            candidate[field] and not is_placeholder_like(candidate[field])
            for field in ("candidate_name", "evidence_sources", "final_decision", "rejection_reason")
        ) and tech_selection_dimension_count_for_row(candidate) >= 10:
            structured_count += 1
    return max(best, structured_count)


def count_tech_selection_candidates_with_long_term_ops_depth(block: str) -> int:
    rows = tech_selection_candidate_entries(block)
    return sum(
        1
        for row in rows
        if tech_selection_required_family_count_for_row(row) >= len(REQUIRED_TECH_SELECTION_LONG_TERM_FAMILIES)
    )


def tech_selection_candidate_entries(block: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if "candidate_name" in headers:
            return table["rows"]
    for match in re.finditer(r"^\s{4}- candidate_[0-9]+:\n((?:^\s{6,}.*\n?)*)", block, flags=re.MULTILINE):
        entry = match.group(1)
        entries.append(
            {
                "candidate_name": extract_structured_field(entry, "candidate_name", indent=6),
                "reliability": extract_structured_field(entry, "reliability", indent=6),
                "performance_capacity": extract_structured_field(entry, "performance_capacity", indent=6),
                "scalability": extract_structured_field(entry, "scalability", indent=6),
                "maintainability": extract_structured_field(entry, "maintainability", indent=6),
                "development_cost": extract_structured_field(entry, "development_cost", indent=6),
                "operations_cost": extract_structured_field(entry, "operations_cost", indent=6),
                "ecosystem_maturity": extract_structured_field(entry, "ecosystem_maturity", indent=6),
                "security_compliance_posture": extract_structured_field(entry, "security_compliance_posture", indent=6),
                "deployment_complexity": extract_structured_field(entry, "deployment_complexity", indent=6),
                "integration_cost": extract_structured_field(entry, "integration_cost", indent=6),
                "integration_fit": extract_structured_field(entry, "integration_fit", indent=6),
                "observability": extract_structured_field(entry, "observability", indent=6),
                "migration_path": extract_structured_field(entry, "migration_path", indent=6),
                "vendor_risk": extract_structured_field(entry, "vendor_risk", indent=6),
                "learning_curve": extract_structured_field(entry, "learning_curve", indent=6),
                "failure_mode": extract_structured_field(entry, "failure_mode", indent=6),
                "evidence_sources": extract_structured_field(entry, "evidence_sources", indent=6),
                "final_decision": extract_structured_field(entry, "final_decision", indent=6),
                "rejection_reason": extract_structured_field(entry, "rejection_reason", indent=6),
            }
        )
    return entries


def api_endpoint_entries(block: str) -> list[dict[str, str]]:
    required_headers = {
        "endpoint_name",
        "method",
        "path",
        "purpose",
        "request_body_example",
        "response_body_example",
        "rate_limit_policy",
        "pagination_rule",
        "failure_codes",
    }
    rows = matching_table_rows(block, required_headers)
    if rows:
        return rows
    entries: list[dict[str, str]] = []
    for match in re.finditer(r"^\s{2,4}- endpoint_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE):
        entry = match.group(1)
        entries.append(
            {
                "endpoint_name": extract_structured_field(entry, "endpoint_name", indent=6),
                "method": extract_structured_field(entry, "method", indent=6),
                "path": extract_structured_field(entry, "path", indent=6),
                "purpose": extract_structured_field(entry, "purpose", indent=6),
                "request_body_example": extract_structured_block(entry, "request_body_example", indent=6),
                "response_body_example": extract_structured_block(entry, "response_body_example", indent=6),
                "response_profile": extract_structured_field(entry, "response_profile", indent=6),
                "rate_limit_policy": extract_structured_field(entry, "rate_limit_policy", indent=6),
                "pagination_rule": extract_structured_field(entry, "pagination_rule", indent=6),
                "retryability_policy": extract_structured_field(entry, "retryability_policy", indent=6),
                "idempotency_rule": extract_structured_field(entry, "idempotency_rule", indent=6),
                "failure_codes": extract_structured_block(entry, "failure_codes", indent=6),
            }
        )
    return entries


def count_structured_contract_schemas(block: str) -> int:
    entries = re.findall(r"^\s{2,4}- contract_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = ("contract_name:", "producer:", "consumer:", "schema_form:", "failure_semantics:", "compatibility_rule:")
    count = 0
    for entry in entries:
        if all(token in entry for token in required_tokens) and ("json_schema:" in entry or "ts_interface:" in entry):
            count += 1
    return count


def count_api_rows_with_operational_controls(block: str) -> int:
    rows = api_endpoint_entries(block)
    return sum(
        1
        for row in rows
        if str(row.get("rate_limit_policy", "")).strip() and str(row.get("pagination_rule", "")).strip()
    )


def count_access_pattern_index_rows(block: str) -> int:
    required_headers = {
        "access_pattern",
        "touched_tables",
        "predicate_sort_join_keys",
        "expected_selectivity",
        "proposed_index",
        "write_cost_note",
        "validation_hook",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))

    entries = re.findall(r"^\s{2}- access_pattern_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    return sum(
        1
        for entry in entries
        if all(
            token in entry
            for token in (
                "access_pattern:",
                "touched_tables:",
                "predicate_sort_join_keys:",
                "expected_selectivity:",
                "proposed_index:",
                "write_cost_note:",
                "validation_hook:",
            )
        )
    )


def count_api_rows_with_contract_controls(block: str) -> int:
    required_headers = {
        "endpoint_name",
        "method",
        "path",
        "response_profile",
        "retryability_policy",
        "idempotency_rule",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))

    entries = re.findall(r"^\s{2,4}- endpoint_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    return sum(
        1
        for entry in entries
        if all(
            extract_structured_field(entry, field, indent=6)
            for field in ("endpoint_name", "method", "path", "response_profile", "retryability_policy", "idempotency_rule")
        )
    )


def count_api_rows_with_error_type_split(block: str) -> int:
    rows = api_endpoint_entries(block)
    return sum(
        1
        for row in rows
        if BUSINESS_ERROR_RE.search(str(row.get("failure_codes", "")))
        or SYSTEM_ERROR_RE.search(str(row.get("failure_codes", "")))
    )


def count_structured_alternative_candidates(block: str) -> int:
    entries = re.findall(r"^\s{2}- candidate_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = ("candidate_name:", "pros:", "cons:", "cost_burden:", "fit_scenario:", "reversibility:")
    return sum(1 for entry in entries if all(token in entry for token in required_tokens))


def count_public_namespace_entries(block: str) -> int:
    structured = count_regex(block, r"^\s{4}- namespace:")
    table_rows = 0
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [part.strip().strip("`") for part in stripped.strip("|").split("|")]
        if any(NAMESPACE_RE.match(cell) for cell in cells):
            table_rows += 1
    return max(structured, table_rows)


def has_public_boundary_namespace_rule(block: str) -> int:
    if "namespace_rule:" in block:
        return 1
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not {"public_name", "namespace"}.issubset(headers):
            continue
        rows = [row for row in table["rows"] if row.get("public_name", "").strip()]
        if rows and all(NAMESPACE_RE.match(str(row.get("namespace", "")).strip()) for row in rows):
            return 1
    return 0


def nested_block_list_item_count(block: str, field_name: str, *, indent: int = 2) -> int:
    nested = extract_structured_block(block, field_name, indent=indent)
    if not nested:
        return 0
    return sum(1 for line in nested.splitlines() if line.strip().startswith("- "))


def count_forbidden_assumptions_with_evidence(block: str) -> int:
    entries = re.findall(r"^\s{2}- fa_[0-9]+:\n((?:^\s{4,}.*\n?)*)", block, flags=re.MULTILINE)
    required_tokens = (
        "original_text:",
        "source:",
        "architecture_constraint_mapping:",
        "compliance_status:",
        "evidence_reference:",
        "evidence_strength:",
    )
    return sum(1 for entry in entries if all(token in entry for token in required_tokens))


def count_slice_entries_with_acceptance(block: str) -> int:
    entries = re.findall(
        r"^\s{4}- (?:slice_[0-9]+:|`?WP-[A-Z0-9]+[^`]*`?:)\n((?:^\s{6,}.*\n?)*)",
        block,
        flags=re.MULTILINE,
    )
    return sum(1 for entry in entries if "completion_signal:" in entry and "acceptance_criteria:" in entry)


def count_structured_work_package_rows(block: str) -> int:
    required_headers = {
        "wp_id",
        "scope",
        "acceptance_criteria",
        "estimated_effort",
        "depends_on",
        "linked_rbi_or_slice",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_schema_summary_rows(block: str) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if "table_name" not in headers or "pk" not in headers:
            continue
        if "ownership" not in headers:
            continue
        return sum(1 for row in table["rows"] if row.get("table_name", "").strip())
    return 0


def count_schema_field_registry_rows(block: str) -> int:
    required_headers = {
        "field_name",
        "data_type",
        "nullable",
        "constraints",
        "index_hint",
    }
    entries = re.findall(r"^\s{4}- table_[0-9]+:\n((?:^\s{6,}.*\n?)*)", block, flags=re.MULTILINE)
    count = 0
    for entry in entries:
        if not all(token in entry for token in ("table_name:", "unique_constraints:", "composite_indexes:")):
            continue
        field_table_present = False
        for table in markdown_tables(entry):
            headers = set(table["headers"])
            if not required_headers.issubset(headers):
                continue
            valid_rows = sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
            if valid_rows >= 3:
                field_table_present = True
                break
        if field_table_present:
            count += 1
    return count


def schema_field_registry_entries(block: str) -> list[dict[str, Any]]:
    required_headers = {
        "field_name",
        "data_type",
        "nullable",
        "constraints",
        "index_hint",
    }
    entries: list[dict[str, Any]] = []
    for match in re.finditer(r"^\s{4}- table_[0-9]+:\n((?:^\s{6,}.*\n?)*)", block, flags=re.MULTILINE):
        entry = match.group(1)
        field_rows: list[dict[str, str]] = []
        for table in markdown_tables(entry):
            headers = set(table["headers"])
            if required_headers.issubset(headers):
                field_rows = table["rows"]
                break
        entries.append(
            {
                "table_name": extract_structured_field(entry, "table_name", indent=6),
                "unique_constraints": extract_structured_field(entry, "unique_constraints", indent=6),
                "composite_indexes": extract_structured_field(entry, "composite_indexes", indent=6),
                "field_rows": field_rows,
            }
        )
    return entries


def count_schema_field_registries_with_specific_types(block: str) -> int:
    count = 0
    for entry in schema_field_registry_entries(block):
        valid_rows = [
            row
            for row in entry["field_rows"]
            if all(row.get(header, "").strip() for header in ("field_name", "data_type", "nullable", "constraints", "index_hint"))
        ]
        if len(valid_rows) < 3:
            continue
        specific_type_rows = sum(1 for row in valid_rows if has_specific_schema_data_type(row.get("data_type", "")))
        if specific_type_rows >= 3:
            count += 1
    return count


def count_data_sensitivity_matrix_rows(block: str) -> int:
    required_headers = {
        "table_name",
        "pii_level",
        "sensitive_fields",
        "masking_or_encryption",
        "retention_rule",
        "audit_access_rule",
        "compliance_note",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def has_quantitative_signal(text: str) -> bool:
    return bool(QUANT_SIGNAL_RE.search(text))


def count_quantified_scenario_rows(block: str) -> int:
    required_headers = {
        "scenario",
        "actors",
        "entities",
        "modules",
        "contracts / endpoints",
        "failure_note",
        "acceptance_criteria",
        "measurement_hook",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(
            1
            for row in table["rows"]
            if all(row.get(header, "").strip() for header in required_headers)
            and has_quantitative_signal(row.get("acceptance_criteria", ""))
        )
    return 0


def row_uses_gwt_language(value: str) -> bool:
    return bool(GIVEN_PATTERN.search(value) and WHEN_PATTERN.search(value) and THEN_PATTERN.search(value))


def count_gwt_compatible_scenario_rows(block: str) -> int:
    required_headers = {
        "scenario",
        "actors",
        "entities",
        "modules",
        "contracts / endpoints",
        "failure_note",
        "acceptance_criteria",
        "measurement_hook",
    }
    best = 0
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        explicit_gwt_headers = {"given", "when", "then"}.issubset(headers)
        compatible_rows = sum(
            1
            for row in table["rows"]
            if all(row.get(header, "").strip() for header in required_headers)
            and (
                (explicit_gwt_headers and all(row.get(header, "").strip() for header in ("given", "when", "then")))
                or row_uses_gwt_language(row.get("acceptance_criteria", ""))
            )
        )
        best = max(best, compatible_rows)

    gwt_block_result = analyze_gwt_block(
        block,
        id_headers=("scenario", "scenario_id"),
        gwt_headers=("given", "when", "then"),
        boundary_headers=("scenario_type", "scenario_category"),
    )
    return max(best, int(gwt_block_result.get("gwt_rows", 0)))


def count_concurrent_conflict_scenario_rows(block: str) -> int:
    required_headers = {
        "scenario",
        "actors",
        "entities",
        "modules",
        "contracts / endpoints",
        "failure_note",
        "acceptance_criteria",
        "measurement_hook",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        category_header = next((alias for alias in SCENARIO_CATEGORY_HEADER_ALIASES if alias in headers), "")
        if not required_headers.issubset(headers) or not category_header:
            continue
        return sum(
            1
            for row in table["rows"]
            if all(row.get(header, "").strip() for header in required_headers | {category_header})
            and CONCURRENT_CONFLICT_RE.search(row.get(category_header, ""))
            and CONCURRENCY_STRATEGY_RE.search(
                " ".join(
                    row.get(field, "")
                    for field in (
                        category_header,
                        "contracts / endpoints",
                        "failure_note",
                        "acceptance_criteria",
                        "measurement_hook",
                        "coordination_strategy",
                        "shared_resource",
                    )
                )
            )
        )
    return 0


def count_design_verification_detailed_rows(block: str) -> int:
    required_headers = {
        "check_item",
        "result",
        "verification_method",
        "evidence",
        "acceptance_rule",
        "residual_gap",
        "linked_rbi_or_wp",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_observability_readiness_rows(block: str) -> int:
    required_headers = {
        "surface",
        "service_or_flow",
        "key_metrics",
        "structured_logs",
        "alert_rule",
        "slo_or_threshold",
        "owner",
        "rollout_guardrail",
    }
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_trace_registry_rows(block: str, required_headers: set[str]) -> int:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
    return 0


def count_replay_rows(block: str) -> int:
    required_headers = {
        "replay_id",
        "scenario_or_contract",
        "replay_type",
        "source_artifacts",
        "expected_outcome",
        "observed_outcome",
        "verdict",
        "evidence_ref",
        "downstream_artifact_id",
        "linked_rbi_or_wp",
    }
    return count_trace_registry_rows(block, required_headers)


def count_rbi_binding_rows(block: str) -> tuple[int, int]:
    total = 0
    bound = 0
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "RBI-" not in stripped or "---" in stripped:
            continue
        total += 1
        if "WP-" in stripped or "out-of-current-phase-scope" in stripped:
            bound += 1
    return total, bound


def count_er_entities(text: str) -> int:
    entities: set[str] = set()
    for first_line, body in mermaid_blocks(text):
        if not first_line.startswith("erDiagram"):
            continue
        entities.update(re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", body))
    return len(entities)


def stage_block_counts(text: str) -> dict[str, int]:
    stage_01 = block_text(text, "quality_attribute_structure")
    stage_01_capacity = block_text(text, "capacity_estimation")
    stage_01_security = block_text(text, "security_architecture_sketch")
    return {
        "quality_attributes_count": count_quality_attributes(stage_01),
        "constraint_categories_count": count_constraint_categories(block_text(text, "constraints")),
        "capacity_number_count": len(NUMBER_RE.findall(stage_01_capacity)),
        "capability_groups_with_priority_maturity": count_capability_groups_with_priority_maturity(
            block_text(text, "capability_map")
        ),
        "capability_map_labeled_nodes": count_capability_map_labeled_nodes(text),
        "stage_01_security_detail_fields_present": int(
            has_required_tokens(
                stage_01_security,
                (
                    "trust_boundaries:",
                    "identity_and_access_posture:",
                    "auth_sequence_direction:",
                    "authentication_sequence:",
                    "key_management_posture:",
                    "audit_sensitive_edges:",
                ),
            )
            and block_nested_fields_present(
                stage_01_security,
                "authentication_sequence",
                ("sequence_diagram", "token_strategy", "token_lifetime", "refresh_mechanism", "revocation_approach"),
            )
            and block_nested_fields_present(
                stage_01_security,
                "key_management_posture",
                ("key_types", "storage", "rotation_policy", "access_control"),
            )
        ),
        "stage_01_security_specificity_present": int(
            block_scalars_with_content(
                stage_01_security,
                ("identity_and_access_posture", "auth_sequence_direction"),
            )
            and block_nested_fields_with_content(
                stage_01_security,
                "authentication_sequence",
                ("token_strategy", "token_lifetime", "refresh_mechanism", "revocation_approach"),
            )
            and block_nested_fields_with_content(
                stage_01_security,
                "key_management_posture",
                ("key_types", "storage", "rotation_policy", "access_control"),
            )
        ),
        "stage_03_security_detail_fields_present": has_required_tokens(
            block_text(text, "security_architecture_outline"),
            (
                "trust_boundaries:",
                "authn_authz_posture:",
                "auth_sequence_direction:",
                "token_posture:",
                "audit_logging_hooks:",
                "sensitive_data_handling:",
                "key_management_posture:",
            ),
        ),
        "stage_03_security_specificity_present": int(
            block_scalars_with_content(
                block_text(text, "security_architecture_outline"),
                ("authn_authz_posture", "auth_sequence_direction", "token_posture"),
            )
            and nested_block_list_item_count(block_text(text, "security_architecture_outline"), "key_management_posture") >= 2
        ),
        "stage_02_dependency_guard_fields_present": has_required_tokens(
            block_text(text, "dependency_collaboration_map"),
            (
                "anti_cycle_rules:",
                "violation_consequence:",
            ),
        ),
        "stage_02_lifecycle_conflict_rule_present": has_required_tokens(
            block_text(text, "lifecycle_ownership_closure"),
            ("conflict_detection_rule:",),
        ),
        "forbidden_assumptions_with_evidence": count_forbidden_assumptions_with_evidence(
            block_text(text, "forbidden_assumptions_registry")
        ),
        "structured_contract_schema_count": count_structured_contract_schemas(block_text(text, "interface_contracts")),
        "api_operational_controls_count": count_api_rows_with_operational_controls(block_text(text, "api_endpoint_draft")),
        "index_strategy_entry_count": count_access_pattern_index_rows(block_text(text, "access_pattern_and_index_strategy")),
        "api_contract_control_count": count_api_rows_with_contract_controls(block_text(text, "api_endpoint_draft")),
        "api_error_type_split_count": count_api_rows_with_error_type_split(block_text(text, "api_endpoint_draft")),
        "response_error_contract_present": int(
            has_required_tokens(
                block_text(text, "response_and_error_contract"),
                (
                    "canonical_success_response:",
                    "canonical_error_response:",
                    "classification_rule:",
                ),
            )
            and block_nested_fields_present(
                block_text(text, "response_and_error_contract"),
                "canonical_error_response",
                ("error_type", "error_code", "message", "retryability", "caller_action", "trace_id"),
                parent_indent=2,
            )
        ),
        "response_error_contract_specificity": int(
            block_nested_fields_with_content(
                block_text(text, "response_and_error_contract"),
                "canonical_error_response",
                ("error_type", "error_code", "message", "retryability", "caller_action", "trace_id"),
                parent_indent=2,
                child_indent=4,
            )
            and word_count(extract_structured_field(block_text(text, "response_and_error_contract"), "classification_rule", indent=2)) >= 6
        ),
        "bottleneck_validation_plan_present": has_required_tokens(
            block_text(text, "dominant_bottleneck_hypothesis"),
            ("measurement_plan:", "threshold:", "spike_scope:"),
        ),
        "structured_alternative_candidate_count": count_structured_alternative_candidates(
            block_text(text, "architecture_alternative_candidate_set")
        ),
        "public_boundary_namespace_entry_count": count_public_namespace_entries(
            block_text(text, "public_boundary_registry_closure")
        ),
        "public_boundary_namespace_rule_present": has_public_boundary_namespace_rule(
            block_text(text, "public_boundary_registry_closure")
        ),
        "scenario_concurrent_conflict_count": count_concurrent_conflict_scenario_rows(
            block_text(text, "scenario_coverage_matrix")
        ),
        "stage_04_optimality_structured_present": has_required_tokens(
            block_text(text, "optimality_review"),
            (
                "acceptable_baseline:",
                "optimal_candidate:",
                "acceptable_vs_optimal_verdict:",
                "why_optimal_not_just_acceptable:",
                "reversibility_posture:",
            ),
        ),
        "stage_04_slice_acceptance_count": count_slice_entries_with_acceptance(block_text(text, "implementation_task_sketch")),
    }


def matching_table_rows(block: str, required_headers: set[str]) -> list[dict[str, str]]:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if required_headers.issubset(headers):
            return table["rows"]
    return []


def semantic_sampling_check(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    adr_sample = deterministic_sample(
        structured_adr_entries(stage_analysis["stage_01"]["blocks"]["key_architecture_decisions"]),
        ("ad_id", "title", "entry_key"),
    )
    schema_sample = deterministic_sample(
        schema_field_registry_entries(stage_analysis["stage_03"]["blocks"]["schema_draft"]),
        ("table_name", "unique_constraints", "composite_indexes"),
    )
    endpoint_sample = deterministic_sample(
        api_endpoint_entries(stage_analysis["stage_03"]["blocks"]["api_endpoint_draft"]),
        ("endpoint_name", "method", "path"),
    )
    tech_candidate_sample = deterministic_sample(
        tech_selection_candidate_entries(stage_analysis["stage_03"]["blocks"]["technology_selection_evaluation_matrix"]),
        ("candidate_name", "final_decision", "rejection_reason"),
    )
    scenario_sample = deterministic_sample(
        matching_table_rows(
            stage_analysis["stage_03"]["blocks"]["scenario_coverage_matrix"],
            {
                "scenario",
                "actors",
                "entities",
                "modules",
                "contracts / endpoints",
                "failure_note",
                "acceptance_criteria",
                "measurement_hook",
            },
        ),
        ("scenario", "modules", "contracts / endpoints"),
    )

    items: list[dict[str, Any]] = []

    if adr_sample is not None:
        adr_checks = [
            {
                "name": "multiple_alternatives",
                "current": int(adr_sample["alternative_count"]),
                "minimum": 2,
                "passed": int(adr_sample["alternative_count"]) >= 2 and int(adr_sample["rejected_because_count"]) >= 2,
            },
            {
                "name": "context_depth",
                "current": word_count(str(adr_sample["context"])),
                "minimum": 8,
                "passed": word_count(str(adr_sample["context"])) >= 8 and not is_placeholder_like(str(adr_sample["context"])),
            },
            {
                "name": "decision_depth",
                "current": word_count(str(adr_sample["decision"])),
                "minimum": 8,
                "passed": word_count(str(adr_sample["decision"])) >= 8 and not is_placeholder_like(str(adr_sample["decision"])),
            },
            {
                "name": "evidence_specificity",
                "current": word_count(str(adr_sample["evidence"])),
                "minimum": 4,
                "passed": word_count(str(adr_sample["evidence"])) >= 4 and not is_placeholder_like(str(adr_sample["evidence"])),
            },
            {
                "name": "consequences_depth",
                "current": word_count(str(adr_sample["consequences"])),
                "minimum": 14,
                "passed": word_count(str(adr_sample["consequences"])) >= 14
                and not is_placeholder_like(str(adr_sample["consequences"])),
            },
        ]
        items.append(
            {
                "sample_type": "adr",
                "sample_key": adr_sample.get("ad_id") or adr_sample.get("entry_key", ""),
                "source": "stage_01 :: key_architecture_decisions",
                "checks": adr_checks,
                "passed": all(check["passed"] for check in adr_checks),
            }
        )

    if schema_sample is not None:
        field_rows = [
            row
            for row in schema_sample.get("field_rows", [])
            if all(row.get(header, "").strip() for header in ("field_name", "data_type", "nullable", "constraints", "index_hint"))
        ]
        specific_type_rows = sum(1 for row in field_rows if has_specific_schema_data_type(row.get("data_type", "")))
        schema_checks = [
            {
                "name": "table_name_present",
                "current": int(bool(normalize_text(str(schema_sample.get("table_name", ""))))),
                "minimum": 1,
                "passed": not is_placeholder_like(str(schema_sample.get("table_name", ""))),
            },
            {
                "name": "field_registry_depth",
                "current": len(field_rows),
                "minimum": 3,
                "passed": len(field_rows) >= 3,
            },
            {
                "name": "specific_data_types",
                "current": specific_type_rows,
                "minimum": 3,
                "passed": specific_type_rows >= 3,
            },
            {
                "name": "constraint_and_index_specificity",
                "current": int(
                    not is_placeholder_like(str(schema_sample.get("unique_constraints", "")))
                    and not is_placeholder_like(str(schema_sample.get("composite_indexes", "")))
                ),
                "minimum": 1,
                "passed": not is_placeholder_like(str(schema_sample.get("unique_constraints", "")))
                and not is_placeholder_like(str(schema_sample.get("composite_indexes", ""))),
            },
        ]
        items.append(
            {
                "sample_type": "schema_registry",
                "sample_key": schema_sample.get("table_name", ""),
                "source": "stage_03 :: schema_draft",
                "checks": schema_checks,
                "passed": all(check["passed"] for check in schema_checks),
            }
        )

    if endpoint_sample is not None:
        failure_code_count = len(set(HTTP_STATUS_RE.findall(str(endpoint_sample.get("failure_codes", "")))))
        endpoint_checks = [
            {
                "name": "method_and_path_shape",
                "current": int(
                    bool(HTTP_METHOD_RE.match(normalize_text(str(endpoint_sample.get("method", "")))))
                    and normalize_text(str(endpoint_sample.get("path", ""))).startswith("/")
                ),
                "minimum": 1,
                "passed": bool(HTTP_METHOD_RE.match(normalize_text(str(endpoint_sample.get("method", "")))))
                and normalize_text(str(endpoint_sample.get("path", ""))).startswith("/"),
            },
            {
                "name": "purpose_depth",
                "current": word_count(str(endpoint_sample.get("purpose", ""))),
                "minimum": 6,
                "passed": word_count(str(endpoint_sample.get("purpose", ""))) >= 6
                and not is_placeholder_like(str(endpoint_sample.get("purpose", ""))),
            },
            {
                "name": "json_examples_parse",
                "current": int(
                    parse_inline_json_object(str(endpoint_sample.get("request_body_example", "")))
                    and parse_inline_json_object(str(endpoint_sample.get("response_body_example", "")))
                ),
                "minimum": 1,
                "passed": parse_inline_json_object(str(endpoint_sample.get("request_body_example", "")))
                and parse_inline_json_object(str(endpoint_sample.get("response_body_example", ""))),
            },
            {
                "name": "failure_semantics_depth",
                "current": failure_code_count,
                "minimum": 3,
                "passed": failure_code_count >= 3 and word_count(str(endpoint_sample.get("failure_codes", ""))) >= 6,
            },
            {
                "name": "operational_controls_specificity",
                "current": word_count(
                    f"{endpoint_sample.get('rate_limit_policy', '')} {endpoint_sample.get('pagination_rule', '')}"
                ),
                "minimum": 3,
                "passed": not is_placeholder_like(str(endpoint_sample.get("rate_limit_policy", "")))
                and not is_placeholder_like(str(endpoint_sample.get("pagination_rule", "")))
                and word_count(
                    f"{endpoint_sample.get('rate_limit_policy', '')} {endpoint_sample.get('pagination_rule', '')}"
                )
                >= 3,
            },
            {
                "name": "response_profile_specificity",
                "current": word_count(str(endpoint_sample.get("response_profile", ""))),
                "minimum": 1,
                "passed": not is_placeholder_like(str(endpoint_sample.get("response_profile", ""))),
            },
            {
                "name": "retryability_and_idempotency",
                "current": word_count(
                    f"{endpoint_sample.get('retryability_policy', '')} {endpoint_sample.get('idempotency_rule', '')}"
                ),
                "minimum": 4,
                "passed": not is_placeholder_like(str(endpoint_sample.get("retryability_policy", "")))
                and not is_placeholder_like(str(endpoint_sample.get("idempotency_rule", "")))
                and word_count(
                    f"{endpoint_sample.get('retryability_policy', '')} {endpoint_sample.get('idempotency_rule', '')}"
                )
                >= 4,
            },
            {
                "name": "business_system_error_split",
                "current": int(
                    bool(BUSINESS_ERROR_RE.search(str(endpoint_sample.get("failure_codes", ""))))
                    and bool(SYSTEM_ERROR_RE.search(str(endpoint_sample.get("failure_codes", ""))))
                ),
                "minimum": 1,
                "passed": bool(BUSINESS_ERROR_RE.search(str(endpoint_sample.get("failure_codes", ""))))
                and bool(SYSTEM_ERROR_RE.search(str(endpoint_sample.get("failure_codes", "")))),
            },
        ]
        items.append(
            {
                "sample_type": "endpoint",
                "sample_key": endpoint_sample.get("endpoint_name", ""),
                "source": "stage_03 :: api_endpoint_draft",
                "checks": endpoint_checks,
                "passed": all(check["passed"] for check in endpoint_checks),
            }
        )

    if tech_candidate_sample is not None:
        dimension_count = tech_selection_dimension_count_for_row(
            {key: str(value) for key, value in tech_candidate_sample.items()}
        )
        tech_checks = [
            {
                "name": "candidate_named",
                "current": int(bool(normalize_text(str(tech_candidate_sample.get("candidate_name", ""))))),
                "minimum": 1,
                "passed": not is_placeholder_like(str(tech_candidate_sample.get("candidate_name", ""))),
            },
            {
                "name": "evaluation_dimensions_present",
                "current": dimension_count,
                "minimum": 10,
                "passed": dimension_count >= 10,
            },
            {
                "name": "evidence_specificity",
                "current": int(
                    bool(URL_RE.search(str(tech_candidate_sample.get("evidence_sources", ""))))
                    and bool(DATE_RE.search(str(tech_candidate_sample.get("evidence_sources", ""))))
                ),
                "minimum": 1,
                "passed": bool(URL_RE.search(str(tech_candidate_sample.get("evidence_sources", ""))))
                and bool(DATE_RE.search(str(tech_candidate_sample.get("evidence_sources", "")))),
            },
            {
                "name": "decision_and_rejection_reason",
                "current": int(
                    not is_placeholder_like(str(tech_candidate_sample.get("final_decision", "")))
                    and not is_placeholder_like(str(tech_candidate_sample.get("rejection_reason", "")))
                ),
                "minimum": 1,
                "passed": not is_placeholder_like(str(tech_candidate_sample.get("final_decision", "")))
                and not is_placeholder_like(str(tech_candidate_sample.get("rejection_reason", ""))),
            },
        ]
        items.append(
            {
                "sample_type": "tech_selection_candidate",
                "sample_key": tech_candidate_sample.get("candidate_name", ""),
                "source": "stage_03 :: technology_selection_evaluation_matrix",
                "checks": tech_checks,
                "passed": all(check["passed"] for check in tech_checks),
            }
        )

    if scenario_sample is not None:
        scenario_checks = [
            {
                "name": "acceptance_quantified",
                "current": word_count(str(scenario_sample.get("acceptance_criteria", ""))),
                "minimum": 10,
                "passed": has_quantitative_signal(str(scenario_sample.get("acceptance_criteria", "")))
                and word_count(str(scenario_sample.get("acceptance_criteria", ""))) >= 10,
            },
            {
                "name": "measurement_hook_specific",
                "current": word_count(str(scenario_sample.get("measurement_hook", ""))),
                "minimum": 4,
                "passed": word_count(str(scenario_sample.get("measurement_hook", ""))) >= 4
                and not is_placeholder_like(str(scenario_sample.get("measurement_hook", ""))),
            },
            {
                "name": "failure_note_specific",
                "current": word_count(str(scenario_sample.get("failure_note", ""))),
                "minimum": 4,
                "passed": word_count(str(scenario_sample.get("failure_note", ""))) >= 4
                and not is_placeholder_like(str(scenario_sample.get("failure_note", ""))),
            },
            {
                "name": "surface_bindings_present",
                "current": int(
                    bool(normalize_text(str(scenario_sample.get("modules", ""))))
                    and bool(normalize_text(str(scenario_sample.get("contracts / endpoints", ""))))
                ),
                "minimum": 1,
                "passed": not is_placeholder_like(str(scenario_sample.get("modules", "")))
                and not is_placeholder_like(str(scenario_sample.get("contracts / endpoints", ""))),
            },
        ]
        items.append(
            {
                "sample_type": "scenario",
                "sample_key": scenario_sample.get("scenario", ""),
                "source": "stage_03 :: scenario_coverage_matrix",
                "checks": scenario_checks,
                "passed": all(check["passed"] for check in scenario_checks),
            }
        )

    missing_sample_types = sorted(
        {"adr", "schema_registry", "endpoint", "tech_selection_candidate", "scenario"}
        - {str(item["sample_type"]) for item in items}
    )
    if missing_sample_types:
        return {
            "applied": True,
            "passed": False,
            "items": items,
            "missing_sample_types": missing_sample_types,
        }
    return {
        "applied": True,
        "passed": all(item["passed"] for item in items),
        "items": items,
        "missing_sample_types": [],
    }


def adr_depth_warning_report(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from phase2.adr_depth_validator import validate_adr_block

    return validate_adr_block(stage_analysis["stage_01"]["blocks"]["key_architecture_decisions"])


def scenario_gwt_warning_report(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    block = stage_analysis["stage_03"]["blocks"]["scenario_coverage_matrix"]
    required_headers = {
        "scenario",
        "actors",
        "entities",
        "modules",
        "contracts / endpoints",
        "failure_note",
        "acceptance_criteria",
        "measurement_hook",
    }
    rows = matching_table_rows(block, required_headers)
    scenario_count = int(stage_analysis["stage_03"]["metrics"].get("scenario_count", 0) or 0)
    gwt_compatible_rows = int(stage_analysis["stage_03"]["metrics"].get("scenario_gwt_compatible_count", 0) or 0)
    ratio = round((gwt_compatible_rows / scenario_count * 100.0), 2) if scenario_count else 0.0

    missing_examples: list[str] = []
    if rows:
        explicit_gwt_headers = {"given", "when", "then"}.issubset(set(rows[0].keys()))
        for row in rows:
            acceptance = row.get("acceptance_criteria", "")
            row_is_gwt = (
                explicit_gwt_headers
                and all(row.get(header, "").strip() for header in ("given", "when", "then"))
            ) or row_uses_gwt_language(acceptance)
            if not row_is_gwt:
                missing_examples.append(row.get("scenario", "") or "unnamed-scenario")
            if len(missing_examples) >= 3:
                break

    return {
        "applied": True,
        "severity": "warning",
        "scenario_count": scenario_count,
        "gwt_compatible_rows": gwt_compatible_rows,
        "ratio": ratio,
        "minimum_ratio": 50.0,
        "passed": scenario_count > 0 and ratio >= 50.0,
        "missing_examples": missing_examples,
        "note": "critical/failure/conflict scenarios should use explicit given/when/then columns or GWT wording inside acceptance_criteria",
    }


def build_semantic_warning_report(stage_analysis: dict[str, dict[str, Any]], *, stage_failures: dict[str, Any]) -> dict[str, Any]:
    if stage_failures:
        return {
            "applied": False,
            "severity": "warning",
            "passed": False,
            "skip_reason": "stage quantitative gates failed",
            "checks": {},
        }

    sampling = semantic_sampling_check(stage_analysis)
    adr_depth = adr_depth_warning_report(stage_analysis)
    scenario_gwt = scenario_gwt_warning_report(stage_analysis)
    checks = {
        "semantic_sampling": {**sampling, "severity": "warning"},
        "adr_depth": adr_depth,
        "scenario_gwt": scenario_gwt,
    }
    warning_count = sum(1 for check in checks.values() if check.get("applied") and not check.get("passed"))
    return {
        "applied": True,
        "severity": "warning",
        "passed": warning_count == 0,
        "warning_count": warning_count,
        "checks": checks,
    }


def analyze_stage(stage_key: str, path: Path, complexity_profile: str = "standard") -> dict[str, Any]:
    text = read_text(path)
    blocks = {
        name: block_text(text, name)
        for name in (
            "system_boundary_statement",
            "constraints",
            "quality_attribute_structure",
            "security_architecture_sketch",
            "capacity_estimation",
            "forbidden_assumptions_registry",
            "capability_map",
            "architecture_direction",
            "key_architecture_decisions",
            "decision_trace_registry",
            "domain_map",
            "module_map",
            "service_candidates",
            "canonical_object_structure",
            "aggregate_catalog",
            "responsibility_matrix",
            "service_endpoint_mapping",
            "lifecycle_ownership_closure",
            "aggregate_lifecycle_coverage",
            "dependency_collaboration_map",
            "entity_relationship_diagram",
            "domain_event_catalog",
            "decomposition_decisions",
            "data_model_summary",
            "data_ownership_map",
            "storage_strategy",
            "access_pattern_and_index_strategy",
            "schema_draft",
            "data_sensitivity_and_compliance_matrix",
            "interface_contracts",
            "response_and_error_contract",
            "api_endpoint_draft",
            "stage_02_event_name_carry_forward",
            "contract_trace_registry",
            "interaction_flow",
            "security_architecture_outline",
            "technology_stack_and_deployment_assumptions",
            "technology_selection_evaluation_matrix",
            "dominant_bottleneck_hypothesis",
            "architecture_alternative_candidate_set",
            "baseline_insufficiency_note",
            "constraint_dominant_optimum_candidate",
            "capacity_and_performance_assumptions",
            "scenario_coverage_matrix",
            "key_tradeoff_decisions",
            "public_boundary_registry_closure",
            "architecture_convergence_summary",
            "prototype_or_structured_delivery_expression",
            "critical_interaction_sequence_set",
            "optimality_review",
            "design_verification_notes",
            "verification_replay_evidence",
            "unresolved_risks_and_review_bound_items",
            "rbi_trace_registry",
            "observability_and_operational_readiness",
            "implementation_handoff_package",
            "implementation_task_sketch",
            "identity_and_key_management_choice_posture",
            "glossary_or_onboarding_summary",
        )
    }
    mermaid = mermaid_counts(text)
    api_rows, api_rows_with_3_failures = count_failure_semantics_per_endpoint(blocks["api_endpoint_draft"])
    rbi_matrix_count, rbi_binding_count = count_rbi_binding_rows(blocks["unresolved_risks_and_review_bound_items"])

    metrics = {
        "line_count": len(text.splitlines()),
        "architecture_decisions_count": len(set(re.findall(r"AD-[0-9]+", text))),
        "structured_adr_count": count_structured_adr_entries(blocks["key_architecture_decisions"]),
        "structured_adr_multi_alt_count": count_structured_adr_entries_with_multiple_alternatives(
            blocks["key_architecture_decisions"]
        ),
        "decision_trace_registry_count": count_trace_registry_rows(
            blocks["decision_trace_registry"],
            {"trace_id", "adr_id", "decision_title", "upstream_reference", "downstream_artifact_id", "verification_hook"},
        ),
        "forbidden_assumptions_count": count_regex(blocks["forbidden_assumptions_registry"], r"^\s{2}- fa_[0-9]+:"),
        "domain_count": count_domains(blocks["domain_map"]),
        "module_count": count_modules(blocks["module_map"]),
        "service_candidate_count": count_service_candidates(blocks["service_candidates"]),
        "service_candidates_with_canonical_fields": count_service_candidates_with_canonical_fields(blocks["service_candidates"]),
        "aggregate_catalog_count": count_aggregate_catalog_entries(blocks["aggregate_catalog"]),
        "canonical_object_structure_count": count_canonical_object_structure_rows(blocks["canonical_object_structure"]),
        "service_endpoint_mapping_count": count_service_endpoint_mapping_rows(blocks["service_endpoint_mapping"]),
        "aggregate_lifecycle_coverage_count": count_aggregate_lifecycle_coverage_rows(blocks["aggregate_lifecycle_coverage"]),
        "aggregate_lifecycle_mermaid_binding_count": count_aggregate_lifecycle_mermaid_bindings(blocks["aggregate_lifecycle_coverage"]),
        "domain_event_count": count_domain_event_entries(blocks["domain_event_catalog"]),
        "schema_table_count": count_schema_summary_rows(blocks["schema_draft"]),
        "schema_field_registry_count": count_schema_field_registry_rows(blocks["schema_draft"]),
        "schema_field_registry_specific_type_count": count_schema_field_registries_with_specific_types(
            blocks["schema_draft"]
        ),
        "data_sensitivity_matrix_count": count_data_sensitivity_matrix_rows(
            blocks["data_sensitivity_and_compliance_matrix"]
        ),
        "api_endpoint_count": api_rows,
        "api_endpoints_with_3_failure_codes": api_rows_with_3_failures,
        "api_rows_with_json_examples": count_api_rows_with_json_examples(blocks["api_endpoint_draft"]),
        "contract_trace_registry_count": count_trace_registry_rows(
            blocks["contract_trace_registry"],
            {"trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook"},
        ),
        "scenario_count": count_table_rows(blocks["scenario_coverage_matrix"]),
        "scenario_quantified_acceptance_count": count_quantified_scenario_rows(blocks["scenario_coverage_matrix"]),
        "scenario_gwt_compatible_count": count_gwt_compatible_scenario_rows(blocks["scenario_coverage_matrix"]),
        "rbi_count": count_table_rows(blocks["unresolved_risks_and_review_bound_items"]),
        "rbi_matrix_count": rbi_matrix_count,
        "rbi_binding_count": rbi_binding_count,
        "rbi_trace_registry_count": count_trace_registry_rows(
            blocks["rbi_trace_registry"],
            {"trace_id", "rbi_id", "bound_wp", "downstream_artifact_id", "verification_hook", "handoff_rule"},
        ),
        "verification_replay_count": count_replay_rows(blocks["verification_replay_evidence"]),
        "public_boundary_name_count": count_table_rows(blocks["public_boundary_registry_closure"]),
        "work_package_count": count_unique_wp(blocks["implementation_task_sketch"]),
        "structured_work_package_count": count_structured_work_package_rows(blocks["implementation_task_sketch"]),
        "observability_readiness_count": count_observability_readiness_rows(
            blocks["observability_and_operational_readiness"]
        ),
        "tech_selection_candidate_count": count_tech_selection_candidates(blocks["technology_selection_evaluation_matrix"]),
        "tech_selection_structured_depth_count": count_tech_selection_candidates_with_structured_depth(
            blocks["technology_selection_evaluation_matrix"]
        ),
        "tech_selection_long_term_ops_depth_count": count_tech_selection_candidates_with_long_term_ops_depth(
            blocks["technology_selection_evaluation_matrix"]
        ),
        "tech_selection_candidates_with_evidence_dates": count_tech_candidates_with_evidence_dates(
            blocks["technology_selection_evaluation_matrix"]
        ),
        "design_verification_item_count": count_table_rows(blocks["design_verification_notes"]),
        "design_verification_detailed_row_count": count_design_verification_detailed_rows(blocks["design_verification_notes"]),
        "review_bound_line_count": count_review_bound_lines(text),
        "review_bound_structured_count": sum(count_marked_structured_items(block) for block in blocks.values()),
        "event_detail_fields_present": int(
            all(token in blocks["domain_event_catalog"] for token in ("payload_shape", "ordering_semantics", "idempotency_rule"))
        ),
        "storage_capacity_fields_present": int(
            all(token in blocks["storage_strategy"] for token in ("initial", "one_year", "three_year", "partition_strategy", "archival_rule"))
        ),
        "rbi_structured_fields_present": int(
            all(token in blocks["unresolved_risks_and_review_bound_items"] for token in ("risk_level", "spike_wp", "responsible_party"))
        ),
        "convergence_c4container_present": int("C4Container" in blocks["architecture_convergence_summary"] or mermaid["C4Container"] > 0),
        "stage_04_readiness_label": normalize_readiness_label(
            extract_block_scalar(blocks["optimality_review"] + "\n" + heading_section(text, "4.1 Realizability Review"), "strongest_supported_readiness_label")
        ),
        "stage_04_realizability_judgment": extract_block_scalar(
            blocks["optimality_review"] + "\n" + heading_section(text, "4.1 Realizability Review"), "realizability_judgment"
        ),
        "stage_01_auth_sequence_diagram_present": int(
            mermaid["sequenceDiagram"] >= 1
            and "authentication_sequence:" in blocks["security_architecture_sketch"]
            and "sequence_diagram:" in extract_structured_block(blocks["security_architecture_sketch"], "authentication_sequence", indent=2)
        ),
    }
    metrics.update(stage_block_counts(text))
    metrics.update(
        {
            "mermaid_C4Context_count": mermaid["C4Context"],
            "mermaid_C4Container_count": mermaid["C4Container"],
            "mermaid_stateDiagram_count": mermaid["stateDiagram-v2"],
        "mermaid_sequenceDiagram_count": mermaid["sequenceDiagram"],
        "mermaid_erDiagram_count": mermaid["erDiagram"],
        "mermaid_gantt_count": mermaid["gantt"],
        "mermaid_flowchart_td_count": mermaid["flowchart_TD"],
        "mermaid_flowchart_lr_count": mermaid["flowchart_LR"],
        "er_entity_count": count_er_entities(text),
    }
    )

    checks: list[dict[str, Any]] = []
    complexity_profile = normalized_complexity_profile(complexity_profile)

    def add_check(name: str, current: int, minimum: int, evidence: str) -> None:
        checks.append(
            {
                "name": name,
                "current": current,
                "minimum": minimum,
                "passed": current >= minimum,
                "evidence": evidence,
            }
        )

    if stage_key == "stage_01":
        stage_01_architecture_min = profile_minimum(complexity_profile, "stage_01_architecture_decisions")
        add_check("architecture_decisions", metrics["architecture_decisions_count"], stage_01_architecture_min, "Section 3 `key_architecture_decisions`")
        add_check("structured_adr_entries", metrics["structured_adr_count"], stage_01_architecture_min, "Section 3 `key_architecture_decisions`")
        add_check(
            "adr_multi_alternative_depth",
            metrics["structured_adr_multi_alt_count"],
            stage_01_architecture_min,
            "Section 3 `key_architecture_decisions` alternatives depth",
        )
        add_check(
            "decision_trace_registry",
            metrics["decision_trace_registry_count"],
            profile_minimum(complexity_profile, "stage_01_decision_trace_registry"),
            "Section 3 `decision_trace_registry`",
        )
        add_check("forbidden_assumptions", metrics["forbidden_assumptions_count"], profile_minimum(complexity_profile, "stage_01_forbidden_assumptions"), "Section 3 `forbidden_assumptions_registry`")
        add_check("constraint_categories", metrics["constraint_categories_count"], 4, "Section 3 `constraints`")
        add_check("quality_attributes", metrics["quality_attributes_count"], profile_minimum(complexity_profile, "stage_01_quality_attributes"), "Section 3 `quality_attribute_structure`")
        add_check("capacity_specific_numbers", metrics["capacity_number_count"], profile_minimum(complexity_profile, "stage_01_capacity_numbers"), "Section 3 `capacity_estimation`")
        add_check("mermaid_C4Context", metrics["mermaid_C4Context_count"], 1, "Section 5 Mermaid system context")
        add_check("capability_map_diagram", metrics["mermaid_flowchart_td_count"], 1, "Section 5 Mermaid capability map")
        add_check(
            "forbidden_assumption_evidence",
            metrics["forbidden_assumptions_with_evidence"],
            3,
            "Section 3 `forbidden_assumptions_registry`",
        )
        add_check(
            "security_architecture_detail",
            metrics["stage_01_security_detail_fields_present"],
            1,
            "Section 3 `security_architecture_sketch`",
        )
        add_check(
            "security_architecture_specificity",
            metrics["stage_01_security_specificity_present"],
            1,
            "Section 3 `security_architecture_sketch` auth/key posture",
        )
        add_check(
            "auth_sequence_diagram",
            metrics["stage_01_auth_sequence_diagram_present"],
            1,
            "Section 3 `security_architecture_sketch` + Section 5 Mermaid auth sequence",
        )
        add_check(
            "capability_groups_priority_maturity",
            metrics["capability_groups_with_priority_maturity"],
            profile_minimum(complexity_profile, "stage_01_capability_groups"),
            "Section 3 `capability_map`",
        )
        add_check(
            "capability_map_labeled_nodes",
            metrics["capability_map_labeled_nodes"],
            profile_minimum(complexity_profile, "stage_01_capability_labels"),
            "Section 5 Mermaid capability map labels",
        )
    elif stage_key == "stage_02":
        add_check("domains", metrics["domain_count"], profile_minimum(complexity_profile, "stage_02_domains"), "Section 3 `domain_map`")
        add_check("modules", metrics["module_count"], profile_minimum(complexity_profile, "stage_02_modules"), "Section 3 `module_map`")
        add_check("service_candidates", metrics["service_candidate_count"], profile_minimum(complexity_profile, "stage_02_services"), "Section 3 `service_candidates`")
        add_check(
            "service_candidate_canonical_fields",
            metrics["service_candidates_with_canonical_fields"],
            profile_minimum(complexity_profile, "stage_02_services"),
            "Section 3 `service_candidates` canonical fields",
        )
        add_check(
            "aggregate_catalog_entries",
            metrics["aggregate_catalog_count"],
            profile_minimum(complexity_profile, "stage_02_aggregate_catalog"),
            "Section 3 `aggregate_catalog`",
        )
        add_check(
            "canonical_object_structure",
            int(
                metrics["aggregate_catalog_count"] > 0
                and metrics["canonical_object_structure_count"] >= metrics["aggregate_catalog_count"]
            ),
            1,
            "Section 3 `canonical_object_structure`",
        )
        add_check(
            "service_endpoint_mapping",
            metrics["service_endpoint_mapping_count"],
            profile_minimum(complexity_profile, "stage_02_service_endpoint_mapping"),
            "Section 3 `service_endpoint_mapping`",
        )
        add_check(
            "aggregate_lifecycle_coverage",
            int(
                metrics["aggregate_catalog_count"] > 0
                and metrics["aggregate_lifecycle_coverage_count"] == metrics["aggregate_catalog_count"]
            ),
            1,
            "Section 3 `aggregate_lifecycle_coverage`",
        )
        add_check(
            "aggregate_lifecycle_mermaid_bindings",
            metrics["aggregate_lifecycle_mermaid_binding_count"],
            profile_minimum(complexity_profile, "stage_02_lifecycle_mermaid_bindings"),
            "Section 3 `aggregate_lifecycle_coverage` Mermaid bindings",
        )
        add_check("state_diagrams", metrics["mermaid_stateDiagram_count"], profile_minimum(complexity_profile, "stage_02_state_diagrams"), "Section 5 Mermaid lifecycle diagrams")
        add_check("domain_events", metrics["domain_event_count"], profile_minimum(complexity_profile, "stage_02_domain_events"), "Section 3 `domain_event_catalog`")
        add_check("event_detail_fields", metrics["event_detail_fields_present"], 1, "Section 3 `domain_event_catalog`")
        add_check("er_diagram", metrics["mermaid_erDiagram_count"], 1, "Section 5 Mermaid ER")
        add_check("er_entity_depth", metrics["er_entity_count"], profile_minimum(complexity_profile, "stage_02_er_entities"), "Section 5 Mermaid ER entities")
        add_check(
            "dependency_anti_cycle_guard",
            metrics["stage_02_dependency_guard_fields_present"],
            1,
            "Section 3 `dependency_collaboration_map`",
        )
        add_check(
            "lifecycle_conflict_detection_rule",
            metrics["stage_02_lifecycle_conflict_rule_present"],
            1,
            "Section 3 `lifecycle_ownership_closure`",
        )
    elif stage_key == "stage_03":
        stage_03_schema_min = profile_minimum(complexity_profile, "stage_03_schema_tables")
        stage_03_api_min = profile_minimum(complexity_profile, "stage_03_api_endpoints")
        stage_03_scenario_min = profile_minimum(complexity_profile, "stage_03_scenarios")
        stage_03_tech_selection_min = profile_minimum(complexity_profile, "stage_03_tech_selection_candidates")
        add_check("schema_tables", metrics["schema_table_count"], stage_03_schema_min, "Section 3 `schema_draft`")
        add_check(
            "schema_field_registries",
            metrics["schema_field_registry_count"],
            max(stage_03_schema_min, metrics["schema_table_count"]),
            "Section 3 `schema_draft` table_field_registry",
        )
        add_check(
            "schema_field_type_specificity",
            metrics["schema_field_registry_specific_type_count"],
            max(stage_03_schema_min, metrics["schema_table_count"]),
            "Section 3 `schema_draft` typed field registry depth",
        )
        add_check(
            "index_strategy_entries",
            metrics["index_strategy_entry_count"],
            profile_minimum(complexity_profile, "stage_03_index_strategy_entries"),
            "Section 3 `access_pattern_and_index_strategy`",
        )
        add_check(
            "data_sensitivity_and_compliance_matrix",
            int(
                metrics["schema_table_count"] > 0
                and metrics["data_sensitivity_matrix_count"] >= metrics["schema_table_count"]
            ),
            1,
            "Section 3 `data_sensitivity_and_compliance_matrix`",
        )
        add_check("api_endpoints", metrics["api_endpoint_count"], stage_03_api_min, "Section 3 `api_endpoint_draft`")
        add_check("api_json_examples", metrics["api_rows_with_json_examples"], max(stage_03_api_min, metrics["api_endpoint_count"]), "Section 3 `api_endpoint_draft`")
        add_check("api_failure_semantics", metrics["api_endpoints_with_3_failure_codes"], max(stage_03_api_min, metrics["api_endpoint_count"]), "Section 3 `api_endpoint_draft`")
        add_check(
            "response_error_contract",
            metrics["response_error_contract_present"],
            1,
            "Section 3 `response_and_error_contract`",
        )
        add_check(
            "response_error_contract_specificity",
            metrics["response_error_contract_specificity"],
            1,
            "Section 3 `response_and_error_contract` canonical error fields",
        )
        add_check(
            "api_contract_controls",
            metrics["api_contract_control_count"],
            max(stage_03_api_min, metrics["api_endpoint_count"]),
            "Section 3 `api_endpoint_draft` response_profile / retryability / idempotency",
        )
        add_check(
            "api_error_type_split",
            metrics["api_error_type_split_count"],
            max(stage_03_api_min, metrics["api_endpoint_count"]),
            "Section 3 `api_endpoint_draft` business/system error split",
        )
        add_check(
            "contract_trace_registry",
            metrics["contract_trace_registry_count"],
            profile_minimum(complexity_profile, "stage_03_contract_trace_registry"),
            "Section 3 `contract_trace_registry`",
        )
        add_check("tech_selection_candidates", metrics["tech_selection_candidate_count"], stage_03_tech_selection_min, "Section 3 `technology_selection_evaluation_matrix`")
        add_check(
            "tech_selection_structured_depth",
            metrics["tech_selection_structured_depth_count"],
            stage_03_tech_selection_min,
            "Section 3 `technology_selection_evaluation_matrix` comparison dimensions",
        )
        add_check(
            "tech_selection_long_term_ops_depth",
            metrics["tech_selection_long_term_ops_depth_count"],
            stage_03_tech_selection_min,
            "Section 3 `technology_selection_evaluation_matrix` long-term ops depth (TCO/operations + ecosystem/community + observability)",
        )
        add_check(
            "tech_selection_evidence_dates",
            metrics["tech_selection_candidates_with_evidence_dates"],
            stage_03_tech_selection_min,
            "Section 3 `technology_selection_evaluation_matrix` evidence sources",
        )
        add_check("interface_contract_schemas", metrics["structured_contract_schema_count"], profile_minimum(complexity_profile, "stage_03_interface_contract_schemas"), "Section 3 `interface_contracts`")
        add_check("api_operational_controls", metrics["api_operational_controls_count"], profile_minimum(complexity_profile, "stage_03_api_operational_controls"), "Section 3 `api_endpoint_draft`")
        add_check(
            "bottleneck_validation_plan",
            metrics["bottleneck_validation_plan_present"],
            1,
            "Section 3 `dominant_bottleneck_hypothesis`",
        )
        add_check(
            "alternative_candidate_structure",
            metrics["structured_alternative_candidate_count"],
            profile_minimum(complexity_profile, "stage_03_alt_candidate_structure"),
            "Section 3 `architecture_alternative_candidate_set`",
        )
        add_check(
            "public_boundary_namespace_rule",
            metrics["public_boundary_namespace_rule_present"],
            1,
            "Section 3 `public_boundary_registry_closure`",
        )
        add_check(
            "public_boundary_namespaces",
            metrics["public_boundary_namespace_entry_count"],
            profile_minimum(complexity_profile, "stage_03_public_boundary_namespaces"),
            "Section 3 `public_boundary_registry_closure`",
        )
        add_check("scenarios", metrics["scenario_count"], stage_03_scenario_min, "Section 3 `scenario_coverage_matrix`")
        add_check(
            "scenario_quantified_acceptance",
            metrics["scenario_quantified_acceptance_count"],
            max(stage_03_scenario_min, metrics["scenario_count"]),
            "Section 3 `scenario_coverage_matrix` quantified acceptance_criteria",
        )
        add_check(
            "scenario_concurrent_conflict_coverage",
            metrics["scenario_concurrent_conflict_count"],
            profile_minimum(complexity_profile, "stage_03_scenario_concurrent_conflicts"),
            "Section 3 `scenario_coverage_matrix` concurrent_conflict coverage",
        )
        add_check("mermaid_diagrams", metrics["mermaid_flowchart_lr_count"], profile_minimum(complexity_profile, "stage_03_mermaid_flowcharts"), "Section 5 Mermaid data/deployment/trust diagrams")
        add_check("storage_strategy_fields", metrics["storage_capacity_fields_present"], 1, "Section 3 `storage_strategy`")
        add_check(
            "security_outline_detail",
            metrics["stage_03_security_detail_fields_present"],
            1,
            "Section 3 `security_architecture_outline`",
        )
        add_check(
            "security_outline_specificity",
            metrics["stage_03_security_specificity_present"],
            1,
            "Section 3 `security_architecture_outline` auth/key posture",
        )
    elif stage_key == "stage_04":
        stage_04_work_package_min = profile_minimum(complexity_profile, "stage_04_work_packages")
        add_check("sequence_diagrams", metrics["mermaid_sequenceDiagram_count"], profile_minimum(complexity_profile, "stage_04_sequence_diagrams"), "Section 5 Mermaid sequence diagrams")
        add_check("work_packages", metrics["work_package_count"], stage_04_work_package_min, "Section 3 `implementation_task_sketch`")
        add_check(
            "work_package_structured_depth",
            int(metrics["structured_work_package_count"] >= max(metrics["work_package_count"], stage_04_work_package_min)),
            1,
            "Section 3 `implementation_task_sketch` work_package_registry",
        )
        add_check("gantt_diagram", metrics["mermaid_gantt_count"], 1, "Section 5 Mermaid gantt")
        add_check("rbi_items", metrics["rbi_count"], profile_minimum(complexity_profile, "stage_04_rbi_items"), "Section 3 `unresolved_risks_and_review_bound_items`")
        add_check("rbi_structured_fields", metrics["rbi_structured_fields_present"], 1, "Section 3 `unresolved_risks_and_review_bound_items`")
        add_check(
            "rbi_spike_bindings",
            int(metrics["rbi_matrix_count"] > 0 and metrics["rbi_matrix_count"] == metrics["rbi_binding_count"]),
            1,
            "Section 3 `unresolved_risks_and_review_bound_items` rbi_matrix",
        )
        add_check(
            "slice_acceptance_criteria",
            metrics["stage_04_slice_acceptance_count"],
            profile_minimum(complexity_profile, "stage_04_slice_acceptance"),
            "Section 3 `implementation_task_sketch`",
        )
        add_check(
            "optimality_structured_verdict",
            metrics["stage_04_optimality_structured_present"],
            1,
            "Section 3 `optimality_review`",
        )
        add_check("convergence_diagram", metrics["convergence_c4container_present"], 1, "Section 3/5 convergence diagram")
        add_check(
            "design_verification",
            metrics["design_verification_detailed_row_count"],
            profile_minimum(complexity_profile, "stage_04_design_verification"),
            "Section 3 `design_verification_notes`",
        )
        add_check(
            "verification_replay_evidence",
            metrics["verification_replay_count"],
            profile_minimum(complexity_profile, "stage_04_verification_replay"),
            "Section 3 `verification_replay_evidence`",
        )
        add_check(
            "rbi_trace_registry",
            metrics["rbi_trace_registry_count"],
            profile_minimum(complexity_profile, "stage_04_rbi_trace_registry"),
            "Section 3 `rbi_trace_registry`",
        )
        add_check(
            "observability_operational_readiness",
            metrics["observability_readiness_count"],
            profile_minimum(complexity_profile, "stage_04_observability"),
            "Section 3 `observability_and_operational_readiness`",
        )

    failures = [check for check in checks if not check["passed"]]
    strongest = max(checks, key=lambda item: (item["current"] - item["minimum"], item["current"]), default=None)
    weakest = min(checks, key=lambda item: (item["current"] - item["minimum"], item["current"]), default=None)

    return {
        "path": str(path),
        "text": text,
        "blocks": blocks,
        "metrics": metrics,
        "checks": checks,
        "gate_failures": failures,
        "quality_gate_passed": not failures,
        "strongest_check": strongest,
        "weakest_check": weakest,
    }


def aggregate_metrics(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {
        "stage_01_line_count": stage_analysis["stage_01"]["metrics"]["line_count"],
        "stage_02_line_count": stage_analysis["stage_02"]["metrics"]["line_count"],
        "stage_03_line_count": stage_analysis["stage_03"]["metrics"]["line_count"],
        "stage_04_line_count": stage_analysis["stage_04"]["metrics"]["line_count"],
        "architecture_decisions_count": stage_analysis["stage_01"]["metrics"]["architecture_decisions_count"],
        "structured_adr_multi_alt_count": stage_analysis["stage_01"]["metrics"]["structured_adr_multi_alt_count"],
        "decision_trace_registry_count": stage_analysis["stage_01"]["metrics"]["decision_trace_registry_count"],
        "forbidden_assumptions_count": stage_analysis["stage_01"]["metrics"]["forbidden_assumptions_count"],
        "mermaid_C4Context_count": stage_analysis["stage_01"]["metrics"]["mermaid_C4Context_count"],
        "mermaid_C4Container_count": stage_analysis["stage_04"]["metrics"]["mermaid_C4Container_count"],
        "mermaid_stateDiagram_count": stage_analysis["stage_02"]["metrics"]["mermaid_stateDiagram_count"]
        + stage_analysis["stage_03"]["metrics"]["mermaid_stateDiagram_count"],
        "mermaid_sequenceDiagram_count": stage_analysis["stage_04"]["metrics"]["mermaid_sequenceDiagram_count"],
        "stage_01_auth_sequence_diagram_present": stage_analysis["stage_01"]["metrics"][
            "stage_01_auth_sequence_diagram_present"
        ],
        "mermaid_erDiagram_count": stage_analysis["stage_02"]["metrics"]["mermaid_erDiagram_count"],
        "mermaid_gantt_count": stage_analysis["stage_04"]["metrics"]["mermaid_gantt_count"],
        "domain_count": stage_analysis["stage_02"]["metrics"]["domain_count"],
        "service_candidate_count": stage_analysis["stage_02"]["metrics"]["service_candidate_count"],
        "aggregate_catalog_count": stage_analysis["stage_02"]["metrics"]["aggregate_catalog_count"],
        "canonical_object_structure_count": stage_analysis["stage_02"]["metrics"]["canonical_object_structure_count"],
        "service_endpoint_mapping_count": stage_analysis["stage_02"]["metrics"]["service_endpoint_mapping_count"],
        "er_entity_count": stage_analysis["stage_02"]["metrics"]["er_entity_count"],
        "domain_event_count": stage_analysis["stage_02"]["metrics"]["domain_event_count"],
        "schema_table_count": stage_analysis["stage_03"]["metrics"]["schema_table_count"],
        "schema_field_registry_count": stage_analysis["stage_03"]["metrics"]["schema_field_registry_count"],
        "schema_field_registry_specific_type_count": stage_analysis["stage_03"]["metrics"][
            "schema_field_registry_specific_type_count"
        ],
        "index_strategy_entry_count": stage_analysis["stage_03"]["metrics"]["index_strategy_entry_count"],
        "data_sensitivity_matrix_count": stage_analysis["stage_03"]["metrics"]["data_sensitivity_matrix_count"],
        "api_endpoint_count": stage_analysis["stage_03"]["metrics"]["api_endpoint_count"],
        "api_contract_control_count": stage_analysis["stage_03"]["metrics"]["api_contract_control_count"],
        "api_error_type_split_count": stage_analysis["stage_03"]["metrics"]["api_error_type_split_count"],
        "response_error_contract_present": stage_analysis["stage_03"]["metrics"]["response_error_contract_present"],
        "contract_trace_registry_count": stage_analysis["stage_03"]["metrics"]["contract_trace_registry_count"],
        "rbi_count": stage_analysis["stage_04"]["metrics"]["rbi_count"],
        "rbi_trace_registry_count": stage_analysis["stage_04"]["metrics"]["rbi_trace_registry_count"],
        "verification_replay_count": stage_analysis["stage_04"]["metrics"]["verification_replay_count"],
        "scenario_count": stage_analysis["stage_03"]["metrics"]["scenario_count"],
        "scenario_quantified_acceptance_count": stage_analysis["stage_03"]["metrics"]["scenario_quantified_acceptance_count"],
        "scenario_concurrent_conflict_count": stage_analysis["stage_03"]["metrics"]["scenario_concurrent_conflict_count"],
        "public_boundary_name_count": stage_analysis["stage_03"]["metrics"]["public_boundary_name_count"],
        "work_package_count": stage_analysis["stage_04"]["metrics"]["work_package_count"],
        "structured_work_package_count": stage_analysis["stage_04"]["metrics"]["structured_work_package_count"],
        "observability_readiness_count": stage_analysis["stage_04"]["metrics"]["observability_readiness_count"],
        "tech_selection_structured_depth_count": stage_analysis["stage_03"]["metrics"][
            "tech_selection_structured_depth_count"
        ],
        "tech_selection_long_term_ops_depth_count": stage_analysis["stage_03"]["metrics"][
            "tech_selection_long_term_ops_depth_count"
        ],
        "esp_implementation_section_count": 0,
        "implementation_entry_checklist_count": 0,
    }


def compute_review_bound_ratio(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total_structured_items = (
        stage_analysis["stage_01"]["metrics"]["architecture_decisions_count"]
        + stage_analysis["stage_01"]["metrics"]["forbidden_assumptions_count"]
        + stage_analysis["stage_01"]["metrics"]["decision_trace_registry_count"]
        + stage_analysis["stage_01"]["metrics"]["quality_attributes_count"]
        + stage_analysis["stage_02"]["metrics"]["domain_count"]
        + stage_analysis["stage_02"]["metrics"]["module_count"]
        + stage_analysis["stage_02"]["metrics"]["service_candidate_count"]
        + stage_analysis["stage_02"]["metrics"]["domain_event_count"]
        + stage_analysis["stage_03"]["metrics"]["schema_table_count"]
        + stage_analysis["stage_03"]["metrics"]["api_endpoint_count"]
        + stage_analysis["stage_03"]["metrics"]["contract_trace_registry_count"]
        + stage_analysis["stage_03"]["metrics"]["scenario_count"]
        + stage_analysis["stage_03"]["metrics"]["tech_selection_candidate_count"]
        + stage_analysis["stage_03"]["metrics"]["public_boundary_name_count"]
        + stage_analysis["stage_04"]["metrics"]["rbi_count"]
        + stage_analysis["stage_04"]["metrics"]["rbi_trace_registry_count"]
        + stage_analysis["stage_04"]["metrics"]["verification_replay_count"]
        + stage_analysis["stage_04"]["metrics"]["work_package_count"]
    )
    review_bound_items = sum(analysis["metrics"]["review_bound_structured_count"] for analysis in stage_analysis.values())
    review_bound_items = min(review_bound_items, total_structured_items) if total_structured_items else 0
    ratio = (review_bound_items / total_structured_items * 100.0) if total_structured_items else 0.0
    if ratio > 50:
        verdict = "blocked"
    elif ratio > 30:
        verdict = "over-uncertain"
    else:
        verdict = "within-ceiling"
    return {
        "total_structured_items": total_structured_items,
        "review_bound_or_unknown_or_deferred_items": review_bound_items,
        "ratio": round(ratio, 2),
        "ceiling": 30,
        "verdict": verdict,
        "computation_method": "heuristic count of structured unresolved items marked review-bound, unknown, or deferred; workflow blocked-state wording and header rows are excluded unless blocked is itself the explicit unresolved status",
    }


def load_baseline(path: Path | None) -> dict[str, int] | None:
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: int(data.get(key, 0)) for key in BASELINE_METRIC_ORDER}


def build_regression_rows(current: dict[str, int], baseline: dict[str, int] | None) -> list[dict[str, Any]]:
    rows = []
    for key in BASELINE_METRIC_ORDER:
        baseline_value = baseline.get(key) if baseline else None
        current_value = current.get(key, 0)
        blocking = key not in NON_BLOCKING_BASELINE_REGRESSION_KEYS
        if baseline_value is None:
            verdict = "baseline-created"
            delta = None
        elif current_value > baseline_value:
            verdict = "improved"
            delta = current_value - baseline_value
        elif current_value == baseline_value:
            verdict = "pass"
            delta = 0
        else:
            verdict = "regressed"
            delta = current_value - baseline_value
        rows.append(
            {
                "dimension": key,
                "baseline_value": baseline_value,
                "current_value": current_value,
                "delta": delta,
                "verdict": verdict,
                "blocking": blocking,
                "justification_if_negative": "",
            }
        )
    return rows


def deliverable_triggered(
    *,
    trigger_rule: str,
    stage_analysis: dict[str, dict[str, Any]],
    complexity_profile: str,
) -> tuple[bool, str]:
    complexity_profile = normalized_complexity_profile(complexity_profile)
    if trigger_rule == "always":
        return True, "always-on mandatory deliverable"
    if trigger_rule == "eventful_domain":
        triggered = complexity_profile != "micro" or stage_analysis["stage_02"]["metrics"]["domain_event_count"] > 0
        reason = (
            "domain-event depth expected for standard/complex cases or when eventful behavior is explicit"
            if triggered
            else "micro profile with no explicit event-driven surface"
        )
        return triggered, reason
    if trigger_rule == "tradeoff_heavy":
        triggered = complexity_profile != "micro" or (
            stage_analysis["stage_03"]["metrics"]["tech_selection_candidate_count"] > 0
            or stage_analysis["stage_03"]["metrics"]["structured_alternative_candidate_count"] > 0
        )
        reason = (
            "tradeoff-heavy evaluation remains in scope"
            if triggered
            else "micro profile without an explicit multi-candidate tradeoff surface"
        )
        return triggered, reason
    if trigger_rule == "capacity_sensitive":
        triggered = complexity_profile != "micro" or stage_analysis["stage_01"]["metrics"]["capacity_number_count"] > 0
        reason = (
            "capacity-sensitive assumptions are in scope"
            if triggered
            else "micro profile without an explicit capacity-sensitive posture"
        )
        return triggered, reason
    if trigger_rule == "delivery_prototype_needed":
        triggered = complexity_profile != "micro" or stage_analysis["stage_04"]["metrics"]["stage_04_slice_acceptance_count"] > 0
        reason = (
            "delivery prototype / slice expression remains in scope"
            if triggered
            else "micro profile without a separate prototype/slice expression requirement"
        )
        return triggered, reason
    return True, "unrecognized trigger rule defaulted to triggered"


def evaluate_block_verdict(
    stage_analysis: dict[str, Any],
    block_name: str,
    mode: str,
    complexity_profile: str = "standard",
    existing_system_change_policy: dict[str, Any] | None = None,
) -> tuple[str, str]:
    block = stage_analysis["blocks"].get(block_name, "")
    evidence = f"Section 3 `{block_name}`"
    if mode == "presence":
        if block:
            return "pass", evidence
        return "fail", evidence

    metrics = stage_analysis["metrics"]
    current = 0
    minimum = 1
    if mode == "stage_01_quality_attributes":
        current = metrics["quality_attributes_count"]
        minimum = profile_minimum(complexity_profile, "stage_01_quality_attributes")
    elif mode == "stage_01_architecture_decisions":
        current = min(
            metrics["architecture_decisions_count"],
            metrics["structured_adr_count"],
            metrics["structured_adr_multi_alt_count"],
        )
        minimum = profile_minimum(complexity_profile, "stage_01_architecture_decisions")
    elif mode == "stage_01_capacity":
        current = metrics["capacity_number_count"]
        minimum = profile_minimum(complexity_profile, "stage_01_capacity_numbers")
    elif mode == "stage_02_domains":
        current = metrics["domain_count"]
        minimum = profile_minimum(complexity_profile, "stage_02_domains")
    elif mode == "stage_02_modules":
        current = metrics["module_count"]
        minimum = profile_minimum(complexity_profile, "stage_02_modules")
    elif mode == "stage_02_services":
        current = metrics["service_candidates_with_canonical_fields"]
        minimum = profile_minimum(complexity_profile, "stage_02_services")
    elif mode == "stage_02_er":
        current = metrics["mermaid_erDiagram_count"]
        minimum = 1
        evidence = "Section 5 Mermaid ER"
    elif mode == "stage_02_events":
        current = metrics["domain_event_count"]
        minimum = profile_minimum(complexity_profile, "stage_02_domain_events")
    elif mode == "stage_03_storage":
        current = metrics["storage_capacity_fields_present"]
        minimum = 1
    elif mode == "stage_03_schema":
        current = min(
            metrics["schema_table_count"],
            metrics["schema_field_registry_count"],
            metrics["schema_field_registry_specific_type_count"],
        )
        minimum = profile_minimum(complexity_profile, "stage_03_schema_tables")
    elif mode == "stage_03_api":
        current = min(metrics["api_endpoint_count"], metrics["api_rows_with_json_examples"])
        minimum = profile_minimum(complexity_profile, "stage_03_api_endpoints")
    elif mode == "stage_03_tech_selection":
        current = min(metrics["tech_selection_candidate_count"], metrics["tech_selection_structured_depth_count"])
        minimum = profile_minimum(complexity_profile, "stage_03_tech_selection_candidates")
    elif mode == "stage_03_scenarios":
        current = min(metrics["scenario_count"], metrics["scenario_quantified_acceptance_count"])
        minimum = profile_minimum(complexity_profile, "stage_03_scenarios")
    elif mode == "stage_04_convergence":
        current = metrics["convergence_c4container_present"]
        minimum = 1
        evidence = "Section 3/5 convergence diagram"
    elif mode == "stage_04_sequences":
        current = metrics["mermaid_sequenceDiagram_count"]
        minimum = profile_minimum(complexity_profile, "stage_04_sequence_diagrams")
        evidence = "Section 5 Mermaid sequence diagrams"
    elif mode == "stage_04_design_verification":
        current = metrics["design_verification_detailed_row_count"]
        minimum = profile_minimum(complexity_profile, "stage_04_design_verification")
    elif mode == "stage_04_rbi":
        current = metrics["rbi_count"]
        minimum = profile_minimum(complexity_profile, "stage_04_rbi_items")
    elif mode == "stage_04_work_packages":
        current = min(metrics["work_package_count"], metrics["structured_work_package_count"])
        minimum = profile_minimum(complexity_profile, "stage_04_work_packages")
    else:
        current = int(bool(block))
        minimum = 1

    adjusted_minimum = adjusted_minimum_for_existing_system_change_mode(
        mode=mode,
        metrics=metrics,
        complexity_profile=complexity_profile,
        policy=existing_system_change_policy,
    )
    if adjusted_minimum is not None and adjusted_minimum < minimum and current < minimum:
        minimum = adjusted_minimum
        evidence = f"{evidence} (bounded existing-system change breadth floor)"

    if current >= minimum:
        return "pass", evidence
    if current > 0 or block:
        return "partial", evidence
    return "fail", evidence


def build_deliverable_matrix(
    stage_analysis: dict[str, dict[str, Any]],
    complexity_profile: str = "standard",
    existing_system_change_policy: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    rows = []
    for name, stage_key, block_name, mode, tier, trigger_rule in DELIVERABLE_SPECS:
        triggered, trigger_reason = deliverable_triggered(
            trigger_rule=trigger_rule,
            stage_analysis=stage_analysis,
            complexity_profile=complexity_profile,
        )
        if not triggered:
            rows.append(
                {
                    "deliverable_name": name,
                    "tier": tier,
                    "trigger_status": "not-triggered",
                    "trigger_reason": trigger_reason,
                    "verdict": "not-triggered",
                    "evidence_reference": f"{stage_key} :: {trigger_reason}",
                    "unresolved_truth": "none",
                    "next_action": "leave omitted unless case complexity or architecture shape activates this surface",
                }
            )
            continue
        analysis = stage_analysis[stage_key]
        verdict, evidence = evaluate_block_verdict(
            analysis,
            block_name,
            mode,
            complexity_profile,
            existing_system_change_policy=existing_system_change_policy,
        )
        block = analysis["blocks"].get(block_name, "")
        if verdict == "fail":
            if tier == "conditional":
                verdict = "partial"
                unresolved_truth = "review-bound"
                next_action = f"author `{block_name}` or explicitly justify omission for this triggered conditional surface in {stage_key}"
            else:
                unresolved_truth = "blocked"
                next_action = f"author or restore `{block_name}` in {stage_key}"
        elif has_uncertainty_marker(block):
            unresolved_truth = "review-bound"
            next_action = f"preserve unresolved truth in `{block_name}` and tighten evidence"
        else:
            unresolved_truth = "none"
            next_action = "preserve current semantics and evidence references"
        rows.append(
            {
                "deliverable_name": name,
                "tier": tier,
                "trigger_status": "triggered",
                "trigger_reason": trigger_reason,
                "verdict": verdict,
                "evidence_reference": f"{Path(analysis['path']).name} :: {evidence}",
                "unresolved_truth": unresolved_truth,
                "next_action": next_action,
            }
        )
    return rows


def summarize_deliverable_matrix(rows: list[dict[str, str]]) -> dict[str, int]:
    mandatory_rows = [row for row in rows if row.get("tier") == "mandatory"]
    conditional_rows = [row for row in rows if row.get("tier") == "conditional"]
    triggered_conditional_rows = [row for row in conditional_rows if row.get("trigger_status") == "triggered"]
    not_triggered_conditional_rows = [row for row in conditional_rows if row.get("trigger_status") == "not-triggered"]
    return {
        "mandatory_count": len(mandatory_rows),
        "mandatory_pass_like_count": sum(1 for row in mandatory_rows if row.get("verdict") in {"pass", "pass-with-review-bound", "partial"}),
        "mandatory_gap_count": sum(1 for row in mandatory_rows if row.get("verdict") in {"partial", "fail"}),
        "conditional_count": len(conditional_rows),
        "triggered_conditional_count": len(triggered_conditional_rows),
        "not_triggered_conditional_count": len(not_triggered_conditional_rows),
        "triggered_conditional_gap_count": sum(
            1 for row in triggered_conditional_rows if row.get("verdict") in {"partial", "fail"}
        ),
    }


def build_stage_summaries(stage_analysis: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    summaries: dict[str, dict[str, str]] = {}
    for stage_key, analysis in stage_analysis.items():
        strongest = analysis["strongest_check"]
        checks = analysis["checks"]
        failed_checks = [item for item in checks if not item["passed"]]
        passed_checks = [item for item in checks if item["passed"]]
        if failed_checks:
            weakest = min(
                failed_checks,
                key=lambda item: (
                    item["current"] / item["minimum"] if item["minimum"] else 0.0,
                    item["current"] - item["minimum"],
                ),
            )
            weakest_reason = "failing gate"
        elif passed_checks:
            weakest = min(
                passed_checks,
                key=lambda item: (
                    item["current"] - item["minimum"],
                    item["current"] / item["minimum"] if item["minimum"] else float("inf"),
                    item["minimum"],
                ),
            )
            weakest_reason = "thinnest passing margin"
        else:
            weakest = analysis["weakest_check"]
            weakest_reason = "no scored checks"
        strongest_text = (
            f"{Path(analysis['path']).name} :: {strongest['evidence']} — "
            f"{strongest['name']} = {strongest['current']} (gate {strongest['minimum']})"
            if strongest
            else "no strongest check computed"
        )
        weakest_text = (
            f"{Path(analysis['path']).name} :: {weakest['evidence']} — "
            f"{weakest['name']} = {weakest['current']} (gate {weakest['minimum']}; {weakest_reason})"
            if weakest
            else "no weakest check computed"
        )
        quality_gate_result = (
            "pass"
            if analysis["quality_gate_passed"]
            else "fail: "
            + ", ".join(
                f"{item['name']}={item['current']}/{item['minimum']}" for item in analysis["gate_failures"]
            )
        )
        summaries[stage_key] = {
            "strongest_output": strongest_text,
            "weakest_output": weakest_text,
            "quality_gate_result": quality_gate_result,
        }
    return summaries


def analyze_optional_stage_02_5(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None

    text = read_text(path)
    blocks = {
        "activation_decision": block_text(text, "activation_decision"),
        "third_party_dependency_manifest": block_text(text, "third_party_dependency_manifest"),
        "integration_decision_records": block_text(text, "integration_decision_records"),
        "integration_adapter_specifications": block_text(text, "integration_adapter_specifications"),
        "integration_test_strategy": block_text(text, "integration_test_strategy"),
        "integration_risk_register": block_text(text, "integration_risk_register"),
    }
    activation_state = normalized_optional_stage_status(
        extract_structured_field(blocks["activation_decision"], "stage_status", indent=2)
        or extract_block_scalar(blocks["activation_decision"], "stage_status")
    )
    skip_reason = (
        extract_structured_field(blocks["activation_decision"], "skip_reason", indent=2)
        or extract_block_scalar(blocks["activation_decision"], "skip_reason")
    )
    dependency_count = count_table_rows_with_headers(
        blocks["third_party_dependency_manifest"],
        {"dependency_id", "dependency_type", "capability", "consuming_module", "mvp_criticality"},
    )
    idr_count = count_structured_entries_with_fields(
        blocks["integration_decision_records"],
        label_prefix="idr_",
        required_fields=("idr_id", "dependency_id", "provider", "integration_pattern", "internal_interface"),
    )
    idr_auth_depth_count = count_structured_entries_with_fields(
        blocks["integration_decision_records"],
        label_prefix="idr_",
        required_fields=(
            "idr_id",
            "dependency_id",
            "provider",
            "authentication_method",
            "key_management",
        ),
    )
    idr_fault_tolerance_depth_count = count_structured_entries_with_fields(
        blocks["integration_decision_records"],
        label_prefix="idr_",
        required_fields=(
            "idr_id",
            "dependency_id",
            "provider",
            "timeout",
            "retry_policy",
            "fallback_strategy",
        ),
    )
    adapter_spec_count = count_table_rows_with_headers(
        blocks["integration_adapter_specifications"],
        {"dependency_id", "internal_port", "provider_endpoint", "error_mapping", "mock_strategy"},
    )
    test_strategy_count = count_table_rows_with_headers(
        blocks["integration_test_strategy"],
        {"dependency_id", "local_strategy", "ci_strategy", "staging_strategy", "production_guardrail", "negative_path_coverage"},
    )
    risk_register_count = count_table_rows_with_headers(
        blocks["integration_risk_register"],
        {"risk_id", "dependency_id", "risk_description", "impact", "likelihood", "mitigation", "owner"},
    )

    metrics = {
        "activation_declared": int(bool(activation_state)),
        "activation_state": activation_state or "missing",
        "skip_reason_present": int(word_count(skip_reason) >= 3 and not is_placeholder_like(skip_reason)),
        "dependency_count": dependency_count,
        "idr_count": idr_count,
        "idr_auth_depth_count": idr_auth_depth_count,
        "idr_fault_tolerance_depth_count": idr_fault_tolerance_depth_count,
        "adapter_spec_count": adapter_spec_count,
        "test_strategy_count": test_strategy_count,
        "risk_register_count": risk_register_count,
    }

    checks: list[dict[str, Any]] = []

    def add_check(name: str, current: int, minimum: int, evidence: str) -> None:
        checks.append(
            {
                "name": name,
                "current": current,
                "minimum": minimum,
                "passed": current >= minimum,
                "evidence": evidence,
            }
        )

    add_check("activation_declared", metrics["activation_declared"], 1, "Section 3 `activation_decision` stage_status")
    if activation_state == "active":
        dependency_min = max(1, dependency_count)
        add_check("dependency_manifest", dependency_count, 1, "Section 3 `third_party_dependency_manifest`")
        add_check("integration_decision_records", idr_count, dependency_min, "Section 3 `integration_decision_records`")
        add_check("auth_posture_depth", idr_auth_depth_count, dependency_min, "Section 3 `integration_decision_records` auth posture")
        add_check(
            "fault_tolerance_depth",
            idr_fault_tolerance_depth_count,
            dependency_min,
            "Section 3 `integration_decision_records` timeout/retry/fallback posture",
        )
        add_check(
            "adapter_specifications",
            adapter_spec_count,
            dependency_min,
            "Section 3 `integration_adapter_specifications`",
        )
        add_check(
            "integration_test_strategy",
            test_strategy_count,
            dependency_min,
            "Section 3 `integration_test_strategy`",
        )
        add_check("integration_risk_register", risk_register_count, 1, "Section 3 `integration_risk_register`")
    elif activation_state == "skipped":
        add_check("skip_reason_present", metrics["skip_reason_present"], 1, "Section 3 `activation_decision` skip_reason")

    failures = [check for check in checks if not check["passed"]]
    return {
        "path": str(path),
        "present": True,
        "metrics": metrics,
        "checks": checks,
        "gate_failures": failures,
        "quality_gate_passed": not failures,
    }


def esp_check(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    text = read_text(path)
    line_count = len(text.splitlines())
    section_count = count_regex(text, r"^## ")
    completeness_sections = {
        "quick_start_path": markdown_heading_section(text, "2.1 Quick-Start Reading Path"),
        "working_glossary": markdown_heading_section(text, "2.2 Working Glossary"),
        "schema_draft": markdown_heading_section(text, "5.2 Schema Draft"),
        "api_summary": markdown_heading_section(text, "6. API Summary"),
        "realizability_judgment": markdown_heading_section(text, "9. Realizability Judgment"),
        "implementation_start_order": markdown_heading_section(text, "10.4 Implementation Start Order"),
        "schema_migration_focus": markdown_heading_section(text, "10.5 Schema and Data Migration Focus"),
        "contract_freeze": markdown_heading_section(text, "10.6 Contract Freeze and Adapter Boundaries"),
        "operation_source_obligation_matrix": markdown_heading_section(text, "10.6A Operation Source Obligation Matrix"),
        "implementation_depth_obligation_matrix": markdown_heading_section(text, "10.6B Implementation Depth Obligation Matrix"),
        "implementation_component_catalog": markdown_heading_section(text, "10.6C Implementation Component Catalog"),
        "component_action_card_obligation_matrix": markdown_heading_section(text, "10.6D Component Action Card Obligation Matrix"),
        "operational_rollout": markdown_heading_section(text, "10.7 Operational Rollout Guardrails"),
        "observability": markdown_heading_section(text, "10.8 Observability and Operational Readiness"),
        "identity_auth_lifecycle": markdown_heading_section(text, "10.9 Identity, Auth Vendor, and Key Lifecycle"),
        "phase3_onboarding_summary": markdown_heading_section(text, "10.10 Phase-3 Onboarding Summary"),
    }
    phase3_onboarding_summary = completeness_sections["phase3_onboarding_summary"]
    missing_placeholder_sections = {
        name for name, section in completeness_sections.items() if not section or ESP_MISSING_MARKER_RE.search(section)
    }
    phase3_onboarding_environment_items = structured_field_items(
        phase3_onboarding_summary,
        "environment_or_dependency_prerequisites",
        indent=2,
    )
    if not phase3_onboarding_environment_items or is_explicit_missing_marker(phase3_onboarding_environment_items[0]):
        missing_placeholder_sections.add("phase3_onboarding_environment_prerequisites")
    checks = {
        "quick_start_present": heading_present(text, "2.1 Quick-Start Reading Path"),
        "working_glossary_present": heading_present(text, "2.2 Working Glossary"),
        "architecture_summary_present": int("## 3. Architecture Summary" in text or "## 3. 架构摘要" in text),
        "schema_summary_present": int("## 5. Schema Summary" in text or "## 5. Schema 摘要" in text),
        "data_sensitivity_summary_present": int(
            "### 5.1 Data Sensitivity and Compliance Matrix" in text or "### 5.1 数据敏感性与合规矩阵" in text
        ),
        "api_summary_present": heading_present(text, "6. API Summary", level=2),
        "decision_reference_present": int("## 7. Key Decisions Quick Reference" in text or "## 7. 关键决策速查" in text),
        "risk_summary_present": int("## 8. Risk Summary" in text or "## 8. 风险摘要" in text),
        "realizability_judgment_present": heading_present(text, "9. Realizability Judgment", level=2),
        "implementation_sequence_present": heading_present(text, "10.4 Implementation Start Order"),
        "migration_focus_present": heading_present(text, "10.5 Schema and Data Migration Focus"),
        "contract_freeze_present": heading_present(text, "10.6 Contract Freeze and Adapter Boundaries"),
        "operation_source_obligation_matrix_present": heading_present(text, "10.6A Operation Source Obligation Matrix"),
        "implementation_depth_obligation_matrix_present": heading_present(text, "10.6B Implementation Depth Obligation Matrix"),
        "implementation_component_catalog_present": heading_present(text, "10.6C Implementation Component Catalog"),
        "component_action_card_obligation_matrix_present": heading_present(text, "10.6D Component Action Card Obligation Matrix"),
        "operational_rollout_present": heading_present(text, "10.7 Operational Rollout Guardrails"),
        "observability_summary_present": heading_present(text, "10.8 Observability and Operational Readiness"),
        "identity_auth_present": heading_present(text, "10.9 Identity, Auth Vendor, and Key Lifecycle"),
        "phase3_onboarding_present": heading_present(text, "10.10 Phase-3 Onboarding Summary"),
        "phase3_onboarding_environment_present": int(bool(phase3_onboarding_environment_items)),
        "implementation_section_count": count_regex(text, r"^### 10\.(?:[4-9]|10|6[A-D]) "),
        "line_count": line_count,
        "section_count": section_count,
        "required_sections_without_missing_markers": int(not missing_placeholder_sections),
    }
    passed = (
        line_count >= 320
        and section_count >= 6
        and checks["implementation_section_count"] >= 7
        and all(checks[name] for name in checks if name.endswith("_present"))
        and not missing_placeholder_sections
    )
    return {
        "path": str(path),
        "checks": checks,
        "passed": passed,
        "missing_placeholder_sections": sorted(missing_placeholder_sections),
    }


ACD_REQUIRED_ARTIFACTS = {
    "p1-value-to-p2-operation-resolution-matrix.json": (
        "resolutions",
        "p1_value_to_p2_operation_resolution_matrix_missing",
    ),
    "implementation-depth-obligation-matrix.json": (
        "operations",
        "implementation_depth_obligation_matrix_missing",
    ),
    "implementation-component-catalog.json": (
        "components",
        "implementation_component_catalog_missing",
    ),
    "component-action-card-obligation-matrix.json": (
        "components",
        "component_action_card_obligation_matrix_missing",
    ),
}
VALID_ACD_LEVELS = {"ACD-0", "ACD-1", "ACD-2", "ACD-3"}
HIGH_ACD_LEVELS = {"ACD-2", "ACD-3"}
VALID_SOURCE_SUFFICIENCY = {"sufficient", "partial", "review-bound", "blocked"}


def acd_artifact_check(root: Path | None) -> dict[str, Any]:
    checks: dict[str, int] = {}
    payloads: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if root is None:
        root = Path("")

    for filename, (row_key, missing_code) in ACD_REQUIRED_ARTIFACTS.items():
        path = find_cross_phase_surface_path(root, "phase2", filename)
        check_name = filename.removesuffix(".json").replace("-", "_") + "_present"
        if not path.exists():
            checks[check_name] = 0
            failures.append({"code": missing_code, "path": str(path)})
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks[check_name] = 0
            failures.append({"code": missing_code, "path": str(path), "reason": f"invalid_json:{exc.msg}"})
            continue
        rows = payload.get(row_key)
        if not isinstance(rows, list) or not rows:
            checks[check_name] = 0
            failures.append({"code": missing_code, "path": str(path), "reason": f"{row_key}_missing_or_empty"})
            payloads[filename] = payload
            continue
        checks[check_name] = 1
        payloads[filename] = payload

    depth_rows = payloads.get("implementation-depth-obligation-matrix.json", {}).get("operations", [])
    component_catalog_rows = payloads.get("implementation-component-catalog.json", {}).get("components", [])
    component_obligation_rows = payloads.get("component-action-card-obligation-matrix.json", {}).get("components", [])
    catalog_ids = {str(row.get("component_id", "")).strip() for row in component_catalog_rows if isinstance(row, dict)}

    for row in depth_rows if isinstance(depth_rows, list) else []:
        if not isinstance(row, dict):
            continue
        acd_level = str(row.get("acd_level", "")).strip()
        if acd_level not in VALID_ACD_LEVELS:
            failures.append(
                {
                    "code": "acd_level_missing_or_invalid",
                    "artifact": "implementation-depth-obligation-matrix.json",
                    "operation_id": row.get("operation_id", ""),
                    "acd_level": acd_level,
                }
            )
        if acd_level in HIGH_ACD_LEVELS and not row.get("required_source_types") and not row.get("review_bound_missing_sources"):
            failures.append(
                {
                    "code": "high_acd_without_required_source_or_review_bound",
                    "artifact": "implementation-depth-obligation-matrix.json",
                    "operation_id": row.get("operation_id", ""),
                    "acd_level": acd_level,
                }
            )

    for row in component_obligation_rows if isinstance(component_obligation_rows, list) else []:
        if not isinstance(row, dict):
            continue
        component_id = str(row.get("component_id", "")).strip()
        acd_level = str(row.get("acd_level", "")).strip()
        source_status = str(row.get("source_sufficiency_status", "")).strip()
        if acd_level not in VALID_ACD_LEVELS:
            failures.append(
                {
                    "code": "acd_level_missing_or_invalid",
                    "artifact": "component-action-card-obligation-matrix.json",
                    "component_id": component_id,
                    "acd_level": acd_level,
                }
            )
        if acd_level in HIGH_ACD_LEVELS and not row.get("required_source_ids") and not row.get("review_bound_missing_sources"):
            failures.append(
                {
                    "code": "high_acd_without_required_source_or_review_bound",
                    "artifact": "component-action-card-obligation-matrix.json",
                    "component_id": component_id,
                    "acd_level": acd_level,
                }
            )
        if source_status not in VALID_SOURCE_SUFFICIENCY:
            failures.append(
                {
                    "code": "acd_source_material_status_missing",
                    "artifact": "component-action-card-obligation-matrix.json",
                    "component_id": component_id,
                    "source_sufficiency_status": source_status,
                }
            )
        elif source_status in {"partial", "review-bound", "blocked"} or row.get("review_bound_missing_sources"):
            warnings.append(
                {
                    "code": "component_obligation_review_bound",
                    "component_id": component_id,
                    "source_sufficiency_status": source_status,
                    "review_bound_missing_sources": row.get("review_bound_missing_sources", []),
                }
            )
        if component_id and component_id not in catalog_ids:
            failures.append(
                {
                    "code": "component_catalog_row_missing",
                    "artifact": "component-action-card-obligation-matrix.json",
                    "component_id": component_id,
                }
            )

    return {
        "path": str(root),
        "applied": True,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "passed": not failures,
    }


def implementation_entry_check(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    text = read_text(path)
    line_count = len(text.splitlines())
    section_count = count_regex(text, r"^## ")
    checklist_rows = 0
    readiness_label = normalize_readiness_label(
        extract_block_scalar(text, "strongest_supported_readiness_label")
        or extract_block_scalar(text, "最强可支持就绪标签")
    )
    may_start = (
        extract_block_scalar(text, "may_start")
        or extract_block_scalar(text, "是否可以开始")
    ).strip().lower()
    readiness_start_consistency = int(not (readiness_label == "blocked" and may_start in {"yes", "true"}))

    def heading_primary_missing(heading: str) -> bool:
        section = markdown_heading_section(text, heading)
        if not section:
            return True
        body_lines = [line.strip() for line in section.splitlines()[1:] if line.strip()]
        if not body_lines:
            return True
        return bool(ESP_MISSING_MARKER_RE.fullmatch(body_lines[0]))

    required_headers = {"checklist_item", "required_input", "pass_condition", "blocker_if_missing", "source_artifact"}
    for table in markdown_tables(text):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        checklist_rows = sum(1 for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers))
        break
    environment_prerequisites_items = structured_field_items(text, "environment_or_dependency_prerequisites", indent=0)
    missing_placeholder_sections = {
        heading
        for heading in ("onboarding_snapshot", "working_glossary")
        if (
            heading == "onboarding_snapshot"
            and heading_primary_missing("2.1 Quick-Start Onboarding Snapshot")
        )
        or (
            heading == "working_glossary"
            and heading_primary_missing("2.2 Working Glossary")
        )
    }
    if not environment_prerequisites_items or is_explicit_missing_marker(environment_prerequisites_items[0]):
        missing_placeholder_sections.add("environment_prerequisites")
    checks = {
        "intake_rule_present": int("## 3. Implementation Intake Rule" in text or "## 3. 实现接入规则" in text),
        "onboarding_snapshot_present": heading_present(text, "2.1 Quick-Start Onboarding Snapshot"),
        "working_glossary_present": heading_present(text, "2.2 Working Glossary"),
        "structured_checklist_present": int("## 4. Structured Intake Checklist" in text or "## 4. 结构化接入清单" in text),
        "start_sequence_present": int("## 5. Phase-3 Start Sequence" in text or "## 5. Phase-3 启动顺序" in text),
        "guardrail_section_present": int("## 6. Phase-2 Guardrails to Preserve" in text or "## 6. 需要保留的 Phase-2 护栏" in text),
        "must_not_assume_present": field_present(text, "must_not_assume"),
        "environment_prerequisites_present": field_present(text, "environment_or_dependency_prerequisites"),
        "environment_prerequisites_complete": int(
            bool(environment_prerequisites_items)
            and not is_explicit_missing_marker(environment_prerequisites_items[0])
        ),
        "checklist_row_count": checklist_rows,
        "line_count": line_count,
        "section_count": section_count,
        "required_sections_without_missing_markers": int(not missing_placeholder_sections),
        "strongest_supported_readiness_label": readiness_label or "missing",
        "may_start": may_start or "missing",
        "readiness_start_consistency": readiness_start_consistency,
    }
    passed = (
        line_count >= 45
        and section_count >= 5
        and checklist_rows >= 6
        and all(checks[name] for name in checks if name.endswith("_present"))
        and not missing_placeholder_sections
        and bool(readiness_start_consistency)
    )
    return {
        "path": str(path),
        "checks": checks,
        "passed": passed,
        "missing_placeholder_sections": sorted(missing_placeholder_sections),
    }


def analyze_phase2_case(
    *,
    stage_paths: dict[str, Path],
    complexity_profile: str = "standard",
    phase1_prd: Path | None = None,
    stage_02_5: Path | None = None,
    baseline_lock_path: Path | None = None,
    baseline_output_path: Path | None = None,
    engineering_spec_pack: Path | None = None,
    implementation_entry: Path | None = None,
    acd_artifact_root: Path | None = None,
) -> dict[str, Any]:
    complexity_profile = normalized_complexity_profile(complexity_profile)
    stage_analysis = {key: analyze_stage(key, stage_paths[key], complexity_profile) for key in STAGE_KEYS}
    existing_system_change_policy = apply_existing_system_change_intake_gate_policy(
        stage_analysis,
        complexity_profile,
    )
    current_metrics = aggregate_metrics(stage_analysis)
    esp_result = esp_check(engineering_spec_pack)
    acd_result = acd_artifact_check(acd_artifact_root) if acd_artifact_root is not None else None
    implementation_entry_result = implementation_entry_check(implementation_entry)
    current_metrics["esp_implementation_section_count"] = (
        int((esp_result or {}).get("checks", {}).get("implementation_section_count", 0))
    )
    current_metrics["implementation_entry_checklist_count"] = (
        int((implementation_entry_result or {}).get("checks", {}).get("checklist_row_count", 0))
    )
    review_bound = compute_review_bound_ratio(stage_analysis)
    deliverable_matrix = build_deliverable_matrix(
        stage_analysis,
        complexity_profile,
        existing_system_change_policy=existing_system_change_policy,
    )
    deliverable_matrix_summary = summarize_deliverable_matrix(deliverable_matrix)
    summaries = build_stage_summaries(stage_analysis)
    phase1_phase2_coverage = (
        {
            "applied": True,
            **analyze_phase1_phase2_coverage_contract(phase1_prd=phase1_prd, stage_paths=stage_paths),
        }
        if phase1_prd is not None
        else {
            "applied": False,
            "verdict": "not-run",
            "skip_reason": "phase1_prd not provided",
        }
    )
    optional_stage_02_5 = analyze_optional_stage_02_5(stage_02_5)
    optional_stage_02_5_expected = False
    optional_stage_02_5_expected_reason = "phase1_prd not provided"
    if phase1_prd is not None:
        external_integration_count = count_external_integrations(read_text(phase1_prd))
        optional_stage_02_5_expected = external_integration_count > 0
        optional_stage_02_5_expected_reason = (
            f"Phase-1 PRD indicates {external_integration_count} external integration category/categories"
            if optional_stage_02_5_expected
            else "Phase-1 PRD does not indicate material external integration categories"
        )
    if optional_stage_02_5 is None:
        optional_stage_02_5 = {
            "path": str(stage_02_5) if stage_02_5 else "",
            "present": False,
            "quality_gate_passed": True,
            "gate_failures": [],
            "metrics": {
                "activation_declared": 0,
                "activation_state": "not-provided",
            },
            "checks": [],
        }
    optional_stage_02_5["expected_from_phase1"] = optional_stage_02_5_expected
    optional_stage_02_5["expected_reason"] = optional_stage_02_5_expected_reason
    optional_stage_02_5["decision_status"] = (
        "active-or-skipped"
        if optional_stage_02_5.get("present")
        else "warning-missing-explicit-decision"
        if optional_stage_02_5_expected
        else "not-applicable"
    )

    baseline = load_baseline(baseline_lock_path)
    regression_rows = build_regression_rows(current_metrics, baseline)
    overall_regression_gate = (
        "fail"
        if any(row["verdict"] == "regressed" and row.get("blocking", True) for row in regression_rows)
        else "pass"
    )
    baseline_created = False
    baseline_rebased = False
    if baseline is None and baseline_output_path is not None:
        baseline_output_path.write_text(json.dumps(current_metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        baseline_created = True

    stage_failures = {
        key: analysis["gate_failures"] for key, analysis in stage_analysis.items() if analysis["gate_failures"]
    }
    semantic_sampling = (
        semantic_sampling_check(stage_analysis)
        if not stage_failures
        else {
            "applied": False,
            "passed": False,
            "items": [],
            "missing_sample_types": [],
            "skip_reason": "stage quantitative gates failed",
        }
    )
    semantic_warnings = build_semantic_warning_report(stage_analysis, stage_failures=stage_failures)
    closure_gate_failures: dict[str, dict[str, Any]] = {}
    deliverable_matrix_assessment = {
        "mandatory_gap_count": int(deliverable_matrix_summary.get("mandatory_gap_count", 0)),
        "triggered_conditional_gap_count": int(deliverable_matrix_summary.get("triggered_conditional_gap_count", 0)),
        "mandatory_gaps": [
            {
                "deliverable_name": row["deliverable_name"],
                "verdict": row["verdict"],
                "evidence_reference": row["evidence_reference"],
                "next_action": row["next_action"],
            }
            for row in deliverable_matrix
            if row.get("tier") == "mandatory" and row.get("verdict") in {"partial", "fail"}
        ],
        "triggered_conditional_gaps": [
            {
                "deliverable_name": row["deliverable_name"],
                "verdict": row["verdict"],
                "trigger_reason": row.get("trigger_reason", ""),
                "evidence_reference": row["evidence_reference"],
                "next_action": row["next_action"],
            }
            for row in deliverable_matrix
            if row.get("tier") == "conditional"
            and row.get("trigger_status") == "triggered"
            and row.get("verdict") in {"partial", "fail"}
        ],
    }
    if deliverable_matrix_assessment["mandatory_gap_count"] > 0:
        closure_gate_failures["mandatory_deliverable_matrix_gaps"] = deliverable_matrix_assessment
    if esp_result is not None and not esp_result["passed"]:
        closure_gate_failures["engineering_spec_pack"] = esp_result["checks"]
    if acd_result is not None and not acd_result["passed"]:
        closure_gate_failures["acd_artifacts"] = acd_result
    if implementation_entry_result is not None and not implementation_entry_result["passed"]:
        closure_gate_failures["implementation_entry"] = implementation_entry_result["checks"]
    if phase1_phase2_coverage["applied"] and phase1_phase2_coverage["verdict"] != "pass":
        closure_gate_failures["phase1_phase2_coverage_contract"] = phase1_phase2_coverage
    if optional_stage_02_5.get("present") and not optional_stage_02_5.get("quality_gate_passed", False):
        closure_gate_failures["optional_stage_02_5"] = optional_stage_02_5.get("gate_failures", [])
    if overall_regression_gate == "fail" and not stage_failures and not closure_gate_failures:
        overall_regression_gate = "pass"
        baseline_rebased = True
        if baseline_output_path is not None:
            baseline_output_path.write_text(json.dumps(current_metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stage_04_readiness_label = stage_analysis["stage_04"]["metrics"].get("stage_04_readiness_label", "")
    quality_based_formal_state = (
        "blocked"
        if (
            stage_failures
            or overall_regression_gate == "fail"
            or deliverable_matrix_assessment["mandatory_gap_count"] > 0
            or (esp_result is not None and not esp_result["passed"])
            or (implementation_entry_result is not None and not implementation_entry_result["passed"])
            or (phase1_phase2_coverage["applied"] and phase1_phase2_coverage["verdict"] != "pass")
        )
        else "pass-with-review-bound-items"
        if review_bound["verdict"] != "within-ceiling"
        or deliverable_matrix_assessment["triggered_conditional_gap_count"] > 0
        else "implementation-planning-ready"
    )
    stage_04_ready_rank = readiness_rank(stage_04_readiness_label)
    quality_rank = readiness_rank(quality_based_formal_state)
    if stage_04_ready_rank >= 0 and quality_rank > stage_04_ready_rank:
        recommended_formal_state = stage_04_readiness_label
        readiness_alignment = {
            "stage_04_label": stage_04_readiness_label,
            "quality_based_label": quality_based_formal_state,
            "final_label": recommended_formal_state,
            "verdict": "capped-by-stage-04",
        }
    else:
        recommended_formal_state = quality_based_formal_state
        readiness_alignment = {
            "stage_04_label": stage_04_readiness_label or "not-declared",
            "quality_based_label": quality_based_formal_state,
            "final_label": recommended_formal_state,
            "verdict": "aligned" if stage_04_readiness_label else "no-stage-04-label-found",
        }

    return {
        "generated_at": utc_now(),
        "complexity_profile": complexity_profile,
        "stage_metrics": {
            key: {
                "path": analysis["path"],
                "metrics": analysis["metrics"],
                "checks": analysis["checks"],
                "quality_gate_passed": analysis["quality_gate_passed"],
                "gate_failures": analysis["gate_failures"],
            }
            for key, analysis in stage_analysis.items()
        },
        "baseline_lock": {
            "reference_path": str(baseline_lock_path) if baseline_lock_path else "",
            "created_new_baseline": baseline_created,
            "rebased_existing_baseline": baseline_rebased,
            "current_metrics": current_metrics,
            "baseline_metrics": baseline,
            "regression_rows": regression_rows,
            "overall_regression_gate": overall_regression_gate,
        },
        "review_bound_ratio": review_bound,
        "deliverable_matrix": deliverable_matrix,
        "deliverable_matrix_summary": deliverable_matrix_summary,
        "deliverable_matrix_assessment": deliverable_matrix_assessment,
        "stage_summaries": summaries,
        "stage_gate_failures": stage_failures,
        "semantic_sampling_gate": semantic_sampling,
        "semantic_warning_checks": semantic_warnings,
        "closure_gate_failures": closure_gate_failures,
        "overall_quality_gate": "pass" if not stage_failures and not closure_gate_failures else "fail",
        "stage_04_readiness_alignment": readiness_alignment,
        "recommended_formal_state": recommended_formal_state,
        "existing_system_change_gate_policy": existing_system_change_policy,
        "phase1_phase2_coverage_contract": phase1_phase2_coverage,
        "optional_stage_02_5_check": optional_stage_02_5,
        "engineering_spec_pack_check": esp_result,
        "acd_artifact_check": acd_result,
        "implementation_entry_check": implementation_entry_result,
    }


def clamp_assessment_dimension(score: int) -> int:
    return max(0, min(5, score))


def render_phase2_scorecard_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Phase-2 Mainline Scorecard",
        "",
        f"- total_score: `{assessment['total_score']}` / 100",
        f"- verdict: `{assessment['verdict']}`",
        f"- recommended_formal_state: `{assessment['recommended_formal_state']}`",
        f"- overall_quality_gate: `{assessment['overall_quality_gate']}`",
        "",
        "| Dimension | Weight | Score | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in assessment["dimension_scores"]:
        notes = "; ".join(str(item) for item in row.get("notes", [])) or "-"
        lines.append(f"| {row['label']} | {row['weight']} | {row['score']} / 5 | {notes} |")
    return "\n".join(lines).rstrip() + "\n"


def render_phase2_acceptance_matrix_markdown(assessment: dict[str, Any]) -> str:
    lines = [
        "# Phase-2 Acceptance Matrix",
        "",
        f"- verdict: `{assessment['verdict']}`",
        f"- recommended_formal_state: `{assessment['recommended_formal_state']}`",
        "",
        "| Acceptance Item | Status | Why |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    return "\n".join(lines).rstrip() + "\n"


def build_phase2_mainline_assessment(
    *,
    quality_report: dict[str, Any],
    cross_stage_report: dict[str, Any],
    mermaid_report: dict[str, Any],
    effective_formal_state: str | None = None,
    closure_adjustment_reasons: list[str] | None = None,
) -> dict[str, Any]:
    stage_metrics = quality_report.get("stage_metrics", {})
    stage_failures = quality_report.get("stage_gate_failures", {})
    deliverable_matrix_assessment = quality_report.get("deliverable_matrix_assessment", {})
    readiness_alignment = quality_report.get("stage_04_readiness_alignment", {})
    phase1_phase2_coverage = quality_report.get("phase1_phase2_coverage_contract", {})
    semantic_sampling = quality_report.get("semantic_sampling_gate", {})
    review_bound_ratio = quality_report.get("review_bound_ratio", {})
    closure_gate_failures = quality_report.get("closure_gate_failures", {})
    baseline_lock = quality_report.get("baseline_lock", {})
    optional_stage_02_5 = quality_report.get("optional_stage_02_5_check", {})

    stage_pass_count = sum(
        1 for key in STAGE_KEYS if isinstance(stage_metrics.get(key), dict) and stage_metrics[key].get("quality_gate_passed")
    )
    mandatory_gap_count = int(deliverable_matrix_assessment.get("mandatory_gap_count", 0) or 0)
    triggered_conditional_gap_count = int(
        deliverable_matrix_assessment.get("triggered_conditional_gap_count", 0) or 0
    )
    esp_check = quality_report.get("engineering_spec_pack_check") or {}
    implementation_entry_check = quality_report.get("implementation_entry_check") or {}
    esp_passed = bool(esp_check.get("passed", False))
    implementation_entry_passed = bool(implementation_entry_check.get("passed", False))
    overall_quality_gate = str(quality_report.get("overall_quality_gate", "")).strip() or "fail"
    pre_closure_recommended_formal_state = str(quality_report.get("recommended_formal_state", "")).strip() or "blocked"
    closure_capped_state = normalize_readiness_label(str(effective_formal_state or "").strip())
    recommended_formal_state = closure_capped_state or pre_closure_recommended_formal_state
    closure_reason_list = [str(reason) for reason in (closure_adjustment_reasons or []) if str(reason).strip()]
    phase1_phase2_coverage_verdict = str(phase1_phase2_coverage.get("verdict", "")).strip() or "fail"
    mermaid_overall_passed = bool(mermaid_report.get("overall_passed", False))
    cross_stage_verdict = str(cross_stage_report.get("overall_consistency_verdict", "")).strip() or "unknown"
    semantic_sampling_passed = bool(semantic_sampling.get("passed", False))
    regression_gate = str(baseline_lock.get("overall_regression_gate", "")).strip() or "fail"
    readiness_alignment_verdict = str(readiness_alignment.get("verdict", "")).strip() or "unknown"
    review_bound_verdict = str(review_bound_ratio.get("verdict", "")).strip() or "unknown"
    optional_stage_status = str(optional_stage_02_5.get("decision_status", "")).strip() or "not-present"
    stage_failure_keys = sorted(str(key) for key in stage_failures.keys())

    dimension_rows = [
        {
            "key": "deliverable_fitness",
            "label": "主交付物完整度",
            "weight": 30,
            "score": clamp_assessment_dimension(
                int(stage_pass_count == len(STAGE_KEYS))
                + int(mandatory_gap_count == 0)
                + int(esp_passed)
                + int(implementation_entry_passed)
                + int(overall_quality_gate == "pass")
            ),
            "notes": [
                f"stage_pass_count={stage_pass_count}/{len(STAGE_KEYS)}",
                f"mandatory_gap_count={mandatory_gap_count}",
                f"engineering_spec_pack={'pass' if esp_passed else 'fail'}",
                f"implementation_entry={'pass' if implementation_entry_passed else 'fail'}",
            ],
        },
        {
            "key": "downstream_consumability",
            "label": "P3 可消费性",
            "weight": 25,
            "score": clamp_assessment_dimension(
                int(recommended_formal_state in {"implementation-planning-ready", "pass-with-review-bound-items"})
                + int(recommended_formal_state == "implementation-planning-ready")
                + int(phase1_phase2_coverage_verdict == "pass")
                + int(triggered_conditional_gap_count == 0)
                + int(readiness_alignment_verdict in {"aligned", "capped-by-stage-04"})
            ),
            "notes": [
                f"recommended_formal_state={recommended_formal_state}",
                f"pre_closure_recommended_formal_state={pre_closure_recommended_formal_state}",
                f"phase1_phase2_coverage={phase1_phase2_coverage_verdict}",
                f"triggered_conditional_gap_count={triggered_conditional_gap_count}",
                f"stage_04_readiness_alignment={readiness_alignment_verdict}",
            ],
        },
        {
            "key": "structural_quality_and_consistency",
            "label": "结构质量与一致性",
            "weight": 20,
            "score": clamp_assessment_dimension(
                int(stage_pass_count >= 3)
                + int(stage_pass_count == len(STAGE_KEYS))
                + int(mermaid_overall_passed)
                + int(cross_stage_verdict == "consistent")
                + int(semantic_sampling_passed)
            ),
            "notes": [
                f"stage_failures={','.join(stage_failure_keys) if stage_failure_keys else 'none'}",
                f"mermaid_overall_passed={str(mermaid_overall_passed).lower()}",
                f"cross_stage_verdict={cross_stage_verdict}",
                f"semantic_sampling={str(semantic_sampling.get('verdict') or semantic_sampling.get('passed') or 'n/a')}",
            ],
        },
        {
            "key": "verification_and_traceability",
            "label": "验证与可追溯性",
            "weight": 15,
            "score": clamp_assessment_dimension(
                int(regression_gate != "fail")
                + int(phase1_phase2_coverage_verdict == "pass")
                + int(mandatory_gap_count == 0)
                + int(implementation_entry_passed)
                + int(not closure_gate_failures)
            ),
            "notes": [
                f"regression_gate={regression_gate}",
                f"closure_gate_failures={len(closure_gate_failures)}",
                f"optional_stage_02_5={optional_stage_status}",
            ],
        },
        {
            "key": "gate_truthfulness",
            "label": "状态/门禁诚实度",
            "weight": 10,
            "score": clamp_assessment_dimension(
                int(overall_quality_gate in {"pass", "fail"})
                + int(bool(recommended_formal_state))
                + int(bool(readiness_alignment.get("final_label")))
                + int(review_bound_verdict != "unknown")
                + int(isinstance(closure_gate_failures, dict))
            ),
            "notes": [
                f"overall_quality_gate={overall_quality_gate}",
                f"review_bound_ratio={review_bound_verdict}",
                f"stage_04_final_label={readiness_alignment.get('final_label') or 'missing'}",
                f"closure_adjustment_reasons={len(closure_reason_list)}",
            ],
        },
    ]

    stage_bundle_status = "PASS" if not stage_failure_keys else "BLOCKED"
    stage_bundle_why = (
        "all Stage-01~04 quality gates passed"
        if not stage_failure_keys
        else "stage gates still fail for: " + ", ".join(stage_failure_keys)
    )
    deliverable_status = (
        "PASS"
        if mandatory_gap_count == 0 and esp_passed
        else "REVIEW-BOUND"
        if mandatory_gap_count == 0 and triggered_conditional_gap_count > 0 and esp_passed
        else "BLOCKED"
    )
    deliverable_why = (
        "mandatory deliverables and Engineering Spec Pack are complete"
        if deliverable_status == "PASS"
        else "mandatory deliverables are present, but triggered conditional branches still need explicit handling"
        if deliverable_status == "REVIEW-BOUND"
        else "mandatory deliverables or Engineering Spec Pack still contain blocking gaps"
    )
    implementation_status = (
        "PASS"
        if implementation_entry_passed and recommended_formal_state == "implementation-planning-ready"
        else "REVIEW-BOUND"
        if implementation_entry_passed and recommended_formal_state == "pass-with-review-bound-items"
        else "BLOCKED"
    )
    implementation_why = (
        "implementation entry is explicit and the pack is ready for implementation planning"
        if implementation_status == "PASS"
        else "implementation entry exists, but some downstream truth must stay review-bound"
        if implementation_status == "REVIEW-BOUND"
        else "implementation entry is missing or the pack is still blocked for safe implementation handoff"
    )
    trace_status = (
        "PASS"
        if phase1_phase2_coverage_verdict == "pass" and cross_stage_verdict == "consistent" and mermaid_overall_passed
        else "BLOCKED"
    )
    trace_why = (
        "coverage contract, cross-stage consistency, and Mermaid semantics all passed"
        if trace_status == "PASS"
        else "traceability or semantic consistency still fails and would force P3 to reconstruct architecture truth"
    )
    formal_state_status = (
        "PASS"
        if recommended_formal_state == "implementation-planning-ready"
        else "REVIEW-BOUND"
        if recommended_formal_state == "pass-with-review-bound-items"
        else "BLOCKED"
    )
    formal_state_why = (
        "recommended formal state matches an implementation-driving Phase-2 package"
        if formal_state_status == "PASS"
        else "formal state is usable but still explicitly review-bound"
        if formal_state_status == "REVIEW-BOUND"
        else "formal state remains blocked and should not be over-claimed as ready for implementation"
    )

    acceptance_rows = [
        {
            "key": "stage_bundle_quality_green",
            "label": "Stage-01~04 结构质量门禁通过",
            "status": stage_bundle_status,
            "why": stage_bundle_why,
        },
        {
            "key": "mandatory_deliverables_complete",
            "label": "必需交付物与 ESP 完整",
            "status": deliverable_status,
            "why": deliverable_why,
        },
        {
            "key": "implementation_entry_usable",
            "label": "Implementation Entry 可被 P3 直接消费",
            "status": implementation_status,
            "why": implementation_why,
        },
        {
            "key": "traceability_and_semantic_contract_hold",
            "label": "追踪链与语义一致性未断裂",
            "status": trace_status,
            "why": trace_why,
        },
        {
            "key": "formal_state_not_overclaimed",
            "label": "阶段状态没有被过度宣称",
            "status": formal_state_status,
            "why": formal_state_why,
        },
    ]

    total_score = round(sum((row["score"] / 5) * row["weight"] for row in dimension_rows), 1)
    blockers_count = sum(1 for row in acceptance_rows if row["status"] == "BLOCKED")
    review_bound_items_count = sum(1 for row in acceptance_rows if row["status"] == "REVIEW-BOUND")
    min_dimension_score = min((row["score"] for row in dimension_rows), default=0)

    if recommended_formal_state == "blocked":
        verdict = "BLOCKED"
    elif blockers_count > 0 or total_score < 70:
        verdict = "RETURN-REMEDIATE"
    elif total_score >= 85 and min_dimension_score >= 3 and review_bound_items_count == 0:
        verdict = "PASS"
    else:
        verdict = "PASS with review-bound items"

    return {
        "phase": "P2",
        "overall_quality_gate": overall_quality_gate,
        "recommended_formal_state": recommended_formal_state,
        "pre_closure_recommended_formal_state": pre_closure_recommended_formal_state,
        "closure_adjustment_reasons": closure_reason_list,
        "dimension_scores": dimension_rows,
        "acceptance_rows": acceptance_rows,
        "total_score": total_score,
        "verdict": verdict,
        "review_bound_items_count": review_bound_items_count,
        "blockers_count": blockers_count,
        "stage_pass_count": stage_pass_count,
        "mandatory_gap_count": mandatory_gap_count,
        "triggered_conditional_gap_count": triggered_conditional_gap_count,
        "cross_stage_verdict": cross_stage_verdict,
        "mermaid_overall_passed": mermaid_overall_passed,
        "phase1_phase2_coverage_verdict": phase1_phase2_coverage_verdict,
    }


def write_phase2_mainline_assessment_artifacts(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
) -> dict[str, str]:
    scorecard_path = output_dir / "phase-mainline-scorecard.md"
    acceptance_matrix_path = output_dir / "phase-acceptance-matrix.md"
    verdict_path = output_dir / "phase-verdict.json"
    scorecard_path.write_text(render_phase2_scorecard_markdown(assessment), encoding="utf-8")
    acceptance_matrix_path.write_text(render_phase2_acceptance_matrix_markdown(assessment), encoding="utf-8")
    verdict_path.write_text(json.dumps(assessment, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "scorecard_path": str(scorecard_path),
        "acceptance_matrix_path": str(acceptance_matrix_path),
        "verdict_path": str(verdict_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase-2 markdown quality checks")
    parser.add_argument("--stage-01", required=True)
    parser.add_argument("--stage-02", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--stage-02-5", default="")
    parser.add_argument("--complexity-profile", default="standard", choices=COMPLEXITY_PROFILES)
    parser.add_argument("--phase1-prd", default="")
    parser.add_argument("--baseline-lock", default="")
    parser.add_argument("--baseline-output", default="")
    parser.add_argument("--engineering-spec-pack", default="")
    parser.add_argument("--implementation-entry", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    stage_paths = {key: Path(getattr(args, key.replace("-", "_"), "")) for key in STAGE_KEYS}
    report = analyze_phase2_case(
        stage_paths=stage_paths,
        complexity_profile=args.complexity_profile,
        phase1_prd=Path(args.phase1_prd) if args.phase1_prd else None,
        stage_02_5=Path(args.stage_02_5) if args.stage_02_5 else None,
        baseline_lock_path=Path(args.baseline_lock) if args.baseline_lock else None,
        baseline_output_path=Path(args.baseline_output) if args.baseline_output else None,
        engineering_spec_pack=Path(args.engineering_spec_pack) if args.engineering_spec_pack else None,
        implementation_entry=Path(args.implementation_entry) if args.implementation_entry else None,
    )
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "overall_quality_gate": report["overall_quality_gate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
