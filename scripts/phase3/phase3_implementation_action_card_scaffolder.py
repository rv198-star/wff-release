#!/usr/bin/env python3
"""Scaffold Phase-3 implementation action cards from P2 ACD obligations."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from typing import Any

from common.action_card_authority_projection import (
    HIGH_SIGNAL_CONSUMER_INTERACTION_OBLIGATION_KINDS,
    apply_product_interaction_projection_to_component_obligations,
    build_action_card_semantic_convergence,
    render_durable_persistence_action_card_lines,
)
from common.cross_phase_surface_policy import find_cross_phase_surface_path
from phase2.agentic_architecture_authority import p2_agentic_architecture_authority_is_valid
from phase3.impl_context import p2_operation_claim_id


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _index_rows(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return indexed
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_key = str(row.get(key, "")).strip()
        if row_key:
            indexed[row_key] = row
    return indexed


def merge_product_interaction_projection(
    obligations: dict[str, dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
    architecture_authority: dict[str, Any],
) -> None:
    """Compatibility wrapper over the shared S1B/S2 in-memory projection helper."""
    apply_product_interaction_projection_to_component_obligations(
        component_obligations=obligations,
        component_catalog=catalog,
        authority=architecture_authority,
    )


def load_action_card_obligations(phase2_root: str | Path) -> dict[str, Any]:
    root = Path(phase2_root)
    blockers: list[str] = []
    resolution_payload = _read_json(
        find_cross_phase_surface_path(root, "phase2", "p1-value-to-p2-operation-resolution-matrix.json")
    )
    catalog_payload = _read_json(find_cross_phase_surface_path(root, "phase2", "implementation-component-catalog.json"))
    obligation_payload = _read_json(
        find_cross_phase_surface_path(root, "phase2", "component-action-card-obligation-matrix.json")
    )
    operation_source_payload = _read_json(
        find_cross_phase_surface_path(root, "phase2", "operation-source-obligation-matrix.json")
    )
    architecture_authority = _read_json(root / "p2-agentic-architecture-authority.json")

    if resolution_payload is None:
        blockers.append("p1_value_to_p2_operation_resolution_matrix_missing")
    if catalog_payload is None:
        blockers.append("implementation_component_catalog_missing")
    if obligation_payload is None:
        blockers.append("component_action_card_obligation_matrix_missing")

    resolutions = _index_rows((resolution_payload or {}).get("resolutions", []), "value_signal_id")
    catalog = _index_rows((catalog_payload or {}).get("components", []), "component_id")
    obligations = _index_rows((obligation_payload or {}).get("components", []), "component_id")
    merge_product_interaction_projection(obligations, catalog, architecture_authority or {})
    by_operation: dict[str, list[dict[str, Any]]] = {}
    for row in obligations.values():
        for operation_id in row.get("upstream_operation_ids", []):
            by_operation.setdefault(str(operation_id), []).append(row)
    return {
        "phase2_root": str(root),
        "blockers": blockers,
        "value_resolutions": resolutions,
        "component_catalog": catalog,
        "component_obligations": obligations,
        "component_obligations_by_operation": by_operation,
        "operation_source_rows": _index_rows((operation_source_payload or {}).get("operations", []), "operation_id"),
        "architecture_authority": architecture_authority or {},
    }


def validate_action_card_obligations(obligations: dict[str, Any]) -> dict[str, Any]:
    blockers = list(obligations.get("blockers", []))
    catalog: dict[str, dict[str, Any]] = obligations.get("component_catalog", {})
    component_obligations: dict[str, dict[str, Any]] = obligations.get("component_obligations", {})
    for component_id, row in component_obligations.items():
        if component_id not in catalog:
            blockers.append("implementation_component_catalog_missing")
        status = str(row.get("source_sufficiency_status", "")).strip()
        missing = [str(item) for item in row.get("missing_source_types", []) if str(item).strip()]
        upstream_operations = [str(item).strip() for item in row.get("upstream_operation_ids", []) if str(item).strip()]
        upstream_p1_traces = [str(item).strip() for item in row.get("upstream_p1_trace_ids", []) if str(item).strip()]
        required_source_ids = [str(item).strip() for item in row.get("required_source_ids", []) if str(item).strip()]
        abstract_source_labels = {"P2-CTR", "P2-FLOW", "P2-SEQ", "P2-STATE", "P2-RP"}
        if upstream_operations and not upstream_p1_traces:
            blockers.append("action_card_p1_trace_missing")
        if status in {"partial", "review-bound", "blocked"} or missing:
            blockers.append("action_card_source_material_missing")
        if any(source_id in abstract_source_labels for source_id in required_source_ids):
            blockers.append("action_card_concrete_source_id_missing")
        if not row.get("acd_level"):
            blockers.append("action_card_depth_mismatch")
    if catalog and not component_obligations:
        blockers.append("component_action_card_obligation_missing")
    return {"blockers": list(dict.fromkeys(blockers)), "passed": not blockers}


def validate_action_card_semantic_convergence(obligations: dict[str, Any]) -> dict[str, Any]:
    component_obligations: dict[str, dict[str, Any]] = obligations.get("component_obligations", {})
    authority = obligations.get("architecture_authority", {})
    if not authority and not any(
        str(row.get("semantic_projection_status") or "") == "authority-bound"
        for row in component_obligations.values()
    ):
        return {
            "artifact_kind": "phase3-action-card-semantic-convergence.v1",
            "status": "not-required",
            "passed": True,
            "conflict_count": 0,
            "conflicts": [],
            "claim_ceiling": "legacy/non-authority Action Card surface; no authority-bound semantic convergence claim",
        }
    if not p2_agentic_architecture_authority_is_valid(authority):
        return {
            "artifact_kind": "phase3-action-card-semantic-convergence.v1",
            "status": "blocked",
            "passed": False,
            "conflict_count": 1,
            "conflicts": [{"code": "action_card_semantic_authority_missing", "component_id": "", "detail": "accepted P2 architecture authority is missing or invalid"}],
            "claim_ceiling": "Action Card semantic convergence is blocked until accepted P2 authority is available.",
        }
    return build_action_card_semantic_convergence(
        component_catalog=obligations.get("component_catalog", {}),
        component_obligations=component_obligations,
        operation_source_rows=obligations.get("operation_source_rows", {}),
        authority=authority,
    )


def card_family(component_type: str) -> str:
    normalized = component_type.strip().lower()
    if normalized == "domain":
        return "Domain Action Card"
    if normalized == "repository":
        return "Repository Action Card"
    if normalized == "adapter":
        return "Adapter Action Card"
    return "Service Action Card"


def card_depth_label(acd_level: str, required_card_type: str) -> str:
    if acd_level == "ACD-3":
        return "split-required deep-action-card"
    return required_card_type or "review-bound-card"


def _clean_values(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _join_values(values: list[str], fallback: str = "review-bound") -> str:
    return ", ".join(values) if values else fallback


def _implementation_guardrails(
    *,
    engineering_risk_tier: str,
    implementation_complexity: str,
    acd_level: str,
    source_sufficiency_status: str,
) -> list[str]:
    guardrails = [
        "preserve the public operation contract and component responsibility from the P2 catalog row",
        "implement only source-backed behavior; keep missing design material review-bound",
    ]
    if engineering_risk_tier == "HR-MUTATION":
        guardrails.append("cover mutation/orchestration failure paths before adding convenience reads")
    elif engineering_risk_tier.startswith("HR-"):
        guardrails.append("cover the high-risk behavior path before lower-risk reporting or helper surfaces")
    if implementation_complexity in {"IC2", "IC3"}:
        guardrails.append(f"treat {implementation_complexity} as decomposition pressure; isolate contract, state, and failure proof")
    if acd_level == "ACD-3":
        guardrails.append("split the parent card before coding; the parent is not direct implementation-ready")
    if source_sufficiency_status in {"partial", "review-bound", "blocked"}:
        guardrails.append("do not implement behavior that depends on missing source material without a reviewed child claim")
    return guardrails


def _test_intent_lines(
    *,
    required_tests: list[str],
    component_id: str,
    target_path_hint: str,
    upstream_operations: list[str],
    available_source_ids: list[str],
) -> list[str]:
    operation_scope = _join_values(upstream_operations, "none; non-operation component")
    target_scope = target_path_hint or "review-bound"
    lines: list[str] = []
    for test_type in required_tests:
        normalized = test_type.strip().lower()
        if normalized == "unit":
            lines.append("- unit: verify component-local behavior against Required Sources plus component-owned semantic and interaction obligations")
        elif normalized == "contract":
            lines.append(f"- contract: verify public operation contract {operation_scope}")
        elif normalized == "integration":
            lines.append(f"- integration: verify the {component_id} boundary at {target_scope}")
        else:
            lines.append(f"- {test_type}: verify evidence against source-backed claims")
    return lines or ["- review-bound: required tests were not declared by Phase-2"]


def _dict_rows(obligation: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in obligation.get(key, []) if isinstance(row, dict)]


def _guardrail_lines(title: str, rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return ["", f"### {title}"] + [
        f"- `{row.get('realization_id', 'review-bound')}` [{row.get('realization_type', 'boundary')}] "
        f"{row.get('statement', 'review-bound')} | ceiling: {row.get('claim_ceiling', 'review-bound')}"
        for row in rows
    ]


def _product_interaction_obligation_lines(obligation: dict[str, Any]) -> list[str]:
    rows = _dict_rows(obligation, "product_interaction_obligations")
    contract = str(obligation.get("interaction_semantics_contract") or "").strip()
    if not rows and not contract:
        return []

    repository_context = bool(rows) and all(
        str(row.get("responsibility_mode") or "") == "persistence-context-only" for row in rows
    )
    heading = (
        "### Product Interaction Semantic Context (Trace Only; Persistence-Owned Constraints)"
        if repository_context
        else "### Product Interaction Obligations (P2 Semantics; P3 Presentation Unselected)"
    )
    lines = ["", heading, f"- interaction_semantics_contract: {contract or 'review-bound'}"]
    obligation_catalog: list[tuple[str, str]] = []
    verification_rows: list[tuple[str, str, str]] = []
    shared_verification_kinds = {
        "verify-error-cost-protection",
        "verify-privacy-or-sensitivity",
        "verify-persistence-semantic-context",
    }
    for row in rows:
        semantics = row.get("semantics") if isinstance(row.get("semantics"), dict) else {}
        resolved = row.get("resolved_p1_context") if isinstance(row.get("resolved_p1_context"), dict) else {}
        responsibility = str(row.get("responsibility_mode") or "review-bound")
        field = str(row.get("contract_field") or "review-bound")
        lines.append(
            f"- semantic=`{row.get('semantic_id', 'review-bound')}` operation=`{row.get('operation_id', 'review-bound')}` "
            f"interaction=`{row.get('interaction_id', 'review-bound')}` field=`{field}` binding=`{row.get('binding_source', 'review-bound')}` "
            f"responsibility=`{responsibility}` p1_contexts=`{_join_values(_clean_values(row.get('p1_context_refs', [])), 'none')}` "
            f"digest=`{row.get('semantic_contract_digest', 'review-bound')}` presentation_authority=`{row.get('presentation_authority', 'unselected-p3-agentic')}`"
        )
        lines.append(f"  - meaning: {semantics.get('user_meaning', 'review-bound')}")
        if repository_context:
            lines.append(
                f"  - persistence_facts: cardinality=`{semantics.get('cardinality', 'review-bound')}`; "
                f"validation=`{semantics.get('validation_semantics', 'review-bound')}`; "
                f"sensitivity=`{semantics.get('privacy_or_sensitivity', 'review-bound')}`; truth=`{semantics.get('truth_state', 'review-bound')}`"
            )
        else:
            candidate_source = semantics.get("candidate_source")
            candidate_text = json.dumps(candidate_source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            lines += [
                f"  - interaction_facts: source=`{semantics.get('value_source', 'review-bound')}`; cardinality=`{semantics.get('cardinality', 'review-bound')}`; "
                f"discovery=`{semantics.get('discovery_requirement', 'review-bound')}`; free_form={str(bool(semantics.get('free_form_allowed'))).lower()}; "
                f"truth=`{semantics.get('truth_state', 'review-bound')}`",
                f"  - candidate_source: {candidate_text}",
                f"  - free_form_rationale: {semantics.get('free_form_rationale', 'review-bound')}",
            ]
            task_frequencies = _clean_values(resolved.get("task_frequencies", []))
            low_step = _clean_values(resolved.get("low_step_requirements", []))
            lines.append(
                f"  - resolved_usage: frequency=`{_join_values(task_frequencies, str(semantics.get('usage_frequency', 'review-bound')))}`; "
                f"low_step=`{_join_values(low_step, 'none explicitly resolved')}`"
            )
            lines.append(
                f"  - continuity: context=`{semantics.get('context_carryover', 'review-bound')}`; "
                f"default_or_recent=`{semantics.get('default_or_recent_semantics', 'review-bound')}`"
            )
            gaps = _clean_values(semantics.get("unresolved_interaction_gaps", []))
            if gaps:
                lines.append(f"  - unresolved_interaction_gaps: {_join_values(gaps)}")

        for item in _dict_rows(row, "implementation_obligations"):
            kind = str(item.get("kind") or "review-bound")
            requirement = str(item.get("requirement") or "review-bound")
            if repository_context or kind in HIGH_SIGNAL_CONSUMER_INTERACTION_OBLIGATION_KINDS:
                pair = (kind, requirement)
                if pair not in obligation_catalog:
                    obligation_catalog.append(pair)
        for item in _dict_rows(row, "verification_obligations"):
            kind = str(item.get("kind") or "review-bound")
            requirement = str(item.get("requirement") or "review-bound")
            entry = ("shared" if kind in shared_verification_kinds else field, kind, requirement)
            if entry not in verification_rows:
                verification_rows.append(entry)

    if obligation_catalog:
        lines += ["", "## Interaction Obligation Catalog"]
        for kind, requirement in obligation_catalog:
            lines.append(f"- obligation=`{kind}`: {requirement}")
    if verification_rows:
        lines += ["", "### Product Interaction Verification"]
        for field, kind, requirement in verification_rows:
            lines.append(f"- field=`{field}` verify=`{kind}`: {requirement}")
    return lines


def _semantic_boundary_lines(obligation: dict[str, Any]) -> list[str]:
    if str(obligation.get("semantic_projection_status") or "") != "authority-bound":
        return []
    value = lambda key, fallback="review-bound": _join_values(_clean_values(obligation.get(key, [])), fallback)
    lines = [
        "", "## Accepted P2 Semantic Boundary",
        f"- accepted_contract_ids: {value('contract_ids', 'none; non-operation component')}",
        f"- aggregate_ids: {value('aggregate_ids')}", f"- aggregate_names: {value('aggregate_names')}",
        f"- service_ids: {value('service_ids')}", f"- owner_service_ids: {value('owner_service_ids')}",
        f"- writer_service_ids: {value('writer_service_ids')}",
        f"- topology_groups: {value('topology_groups', 'none; no operation topology group')}",
    ]
    lines += _guardrail_lines("Component Non-Operation Guardrails", _dict_rows(obligation, "non_operation_realizations"))
    project_guardrails = _dict_rows(obligation, "project_guardrails")
    if project_guardrails:
        lines += ["", "### Project Guardrails (Context Only; No Component Prerequisite)", f"- project_guardrail_p1_trace_ids: {value('project_guardrail_p1_trace_ids', 'none')}"]
        lines += _guardrail_lines("Project Guardrails", project_guardrails)[2:]
    terminal_role_bindings = _dict_rows(obligation, "terminal_role_bindings")
    terminal_roles = _clean_values(obligation.get("terminal_roles", []))
    terminal_role_status = str(obligation.get("terminal_role_authority_status") or "not-declared").strip()
    terminal_role_claim_ceilings = _clean_values(obligation.get("terminal_role_claim_ceilings", []))
    if terminal_roles or terminal_role_bindings or terminal_role_claim_ceilings or terminal_role_status != "not-declared":
        lines += [
            "",
            "### Terminal Role / Data Boundary",
            f"- terminal_roles: {_join_values(terminal_roles, 'none')}",
            f"- terminal_role_authority_status: {terminal_role_status}",
        ]
        for claim_ceiling in terminal_role_claim_ceilings:
            lines.append(f"- terminal_role_claim_ceiling: {claim_ceiling}")
        for row in terminal_role_bindings:
            visible_objects = _join_values(_clean_values(row.get("visible_business_objects", [])))
            lines.append(
                f"- role=`{row.get('terminal_role', 'review-bound')}` route=`{row.get('route', 'review-bound')}` "
                f"interaction=`{row.get('interaction_id', 'review-bound')}` method=`{row.get('http_method', 'review-bound')}` api=`{row.get('api_endpoint', 'review-bound')}` "
                f"visible_business_objects=`{visible_objects}` enforcement=`{row.get('enforcement_posture', 'review-bound')}` "
                f"denied_behavior=`{row.get('denied_behavior', 'review-bound')}`"
            )
    lines += _product_interaction_obligation_lines(obligation)
    states = _dict_rows(obligation, "state_constraints")
    if states:
        lines += ["", "### State / Failure Boundaries"] + [
            f"- `{row.get('decision_id', 'review-bound')}` states={_join_values(_clean_values(row.get('states', [])), 'review-bound')}; "
            f"events={_join_values(_clean_values(row.get('event_ids', [])), 'review-bound')}; guard={row.get('mutation_guard', 'review-bound')}; "
            f"failure_exit={row.get('terminal_or_failure_exit', 'review-bound')}; ceiling={row.get('claim_ceiling', 'review-bound')}"
            for row in states
        ]
    dependencies = _dict_rows(obligation, "dependency_constraints")
    if dependencies:
        lines += ["", "### Upstream Dependency Context (No Component Prerequisite Implied)"] + [
            f"- `{row.get('dependency_id', 'review-bound')}` disposition=`{row.get('disposition', 'review-bound')}`: "
            f"{row.get('statement', 'review-bound')} | ceiling: {row.get('claim_ceiling', 'review-bound')}"
            for row in dependencies
        ]
    lines += render_durable_persistence_action_card_lines(obligation.get("durable_persistence_decisions", []))
    decisions = _dict_rows(obligation, "architecture_decisions")
    if decisions:
        lines += ["", "### Architecture / Contract Decisions"] + [
            f"- `{row.get('decision_id', 'review-bound')}` {row.get('title') or row.get('statement') or row.get('operation_id') or row.get('aggregate_id') or 'accepted decision'} "
            f"| ceiling: {row.get('claim_ceiling', 'review-bound')}"
            for row in decisions
        ]
    ceilings = _clean_values(obligation.get("semantic_claim_ceilings", []))
    lines += ["", "### Semantic Claim Ceilings"] + ([f"- {item}" for item in ceilings] or ["- review-bound; accepted P2 semantic claim ceiling missing"])
    return lines

def render_implementation_action_card(obligation: dict[str, Any], catalog_row: dict[str, Any] | None = None) -> str:
    catalog_row = catalog_row or {}
    component_type = str(obligation.get("component_type") or catalog_row.get("component_type") or "Service")
    component_id = str(obligation.get("component_id") or catalog_row.get("component_id") or "review-bound")
    acd_level = str(obligation.get("acd_level", "review-bound"))
    required_card_type = str(obligation.get("required_card_type", "review-bound-card"))
    upstream_operations = _clean_values(obligation.get("upstream_operation_ids", []))
    upstream_p1_traces = _clean_values(obligation.get("upstream_p1_trace_ids", []))
    required_source_ids = _clean_values(obligation.get("required_source_ids", []))
    available_source_ids = _clean_values(obligation.get("available_source_ids", []))
    missing_source_types = _clean_values(obligation.get("missing_source_types", []))
    required_tests = _clean_values(obligation.get("required_tests", []))
    target_path_hint = str(catalog_row.get("target_path_hint", "review-bound")).strip() or "review-bound"
    source_sufficiency_status = str(obligation.get("source_sufficiency_status", "review-bound")).strip()
    engineering_risk_tier = str(obligation.get("engineering_risk_tier", "review-bound")).strip()
    implementation_complexity = str(obligation.get("implementation_complexity", "review-bound")).strip()
    operation_claim_refs = [
        p2_operation_claim_id(operation_id)
        for operation_id in upstream_operations
        if str(operation_id).strip()
    ]
    available_sources_text = (
        f"same-as-required (count={len(available_source_ids)})"
        if available_source_ids == required_source_ids and available_source_ids
        else _join_values(available_source_ids, "none")
    )
    authority_bound = str(obligation.get("semantic_projection_status") or "") == "authority-bound"
    operation_ids_text = _join_values(upstream_operations, "none; non-operation component" if authority_bound else "review-bound")
    operation_claim_refs_text = _join_values(operation_claim_refs, "none" if authority_bound and not upstream_operations else "review-bound")
    operation_contract_text = _join_values(upstream_operations) if upstream_operations else ("none; preserve accepted aggregate / writer / non-operation / state authority" if authority_bound else "review-bound")
    guardrails = _implementation_guardrails(
        engineering_risk_tier=engineering_risk_tier,
        implementation_complexity=implementation_complexity,
        acd_level=acd_level,
        source_sufficiency_status=source_sufficiency_status,
    )
    test_intent = _test_intent_lines(
        required_tests=required_tests,
        component_id=component_id,
        target_path_hint=target_path_hint,
        upstream_operations=upstream_operations,
        available_source_ids=available_source_ids,
    )
    lines = [
        f"# {card_family(component_type)}",
        "",
        f"- component_id: {component_id}",
        f"- component_type: {component_type}",
        f"- acd_level: {acd_level}",
        f"- card_depth: {card_depth_label(acd_level, required_card_type)}",
        f"- source_sufficiency_status: {source_sufficiency_status}",
        f"- target_path_hint: {target_path_hint}",
        "",
        "## Upstream Binding",
        f"- upstream_operation_ids: {operation_ids_text}",
        f"- upstream_operation_claim_refs: {operation_claim_refs_text}",
        f"- upstream_p1_trace_ids: {_join_values(upstream_p1_traces)}",
        f"- business_value_weight: {obligation.get('business_value_weight', 'review-bound')}",
        f"- engineering_risk_tier: {engineering_risk_tier}",
        f"- implementation_complexity: {implementation_complexity}",
        "",
        "## Required Sources",
        f"- required_source_ids: {_join_values(required_source_ids)}",
        f"- available_source_ids: {available_sources_text}",
        f"- missing_source_types: {_join_values(missing_source_types, 'none')}",
        "",
        "## Contract To Preserve",
        f"- operation_contract: {operation_contract_text}",
        f"- operation_claim_ref: {operation_claim_refs_text}",
        f"- component_contract: {component_id} remains the {component_type} implementation component",
        f"- target_path_hint: {target_path_hint}",
        "",
        "## Source-Bound Behavior Scope",
        f"- source-backed inputs: use Required Sources above; available_source_count={len(available_source_ids)}",
        f"- required inputs: use Required Sources above; required_source_count={len(required_source_ids)}",
        f"- {'source_material_gaps' if str(obligation.get('semantic_projection_status') or '') == 'authority-bound' else 'review-bound gaps'}: {_join_values(missing_source_types, 'none')}",
        *_semantic_boundary_lines(obligation),
        "",
        "## Implementation Steps",
        "- read Contract To Preserve before changing code targets",
        "- implement the Source-Bound Behavior Scope without introducing unstated business behavior",
        "- apply Implementation Guardrails before adding convenience surfaces",
        "- bind code targets and tests back to this action card id",
        "",
        "## Implementation Guardrails",
        *[f"- {item}" for item in guardrails],
        "",
        "## Test Intent",
        *test_intent,
        "",
        "## Required Tests",
        *[f"- {item}" for item in required_tests],
    ]
    if acd_level == "ACD-3":
        lines.extend([
            "",
            "## Split Required",
            "- split-required: yes",
            "- direct_implementation_blocked: parent ACD-3 card must be decomposed before coding",
        ])
    return "\n".join(lines).rstrip() + "\n"


def write_action_cards(phase2_root: str | Path, output_root: str | Path) -> list[Path]:
    loaded = load_action_card_obligations(phase2_root)
    catalog = loaded["component_catalog"]
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for component_id, obligation in loaded["component_obligations"].items():
        path = output / f"{component_id.lower()}-action-card.md"
        path.write_text(render_implementation_action_card(obligation, catalog.get(component_id)), encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate P3 implementation action cards from P2 ACD obligations")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    written = write_action_cards(args.phase2_root, args.output_root)
    print(json.dumps({"written": [str(path) for path in written]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
