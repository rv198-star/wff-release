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
from pathlib import Path
from typing import Any

from common.cross_phase_surface_policy import find_cross_phase_surface_path
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

    if resolution_payload is None:
        blockers.append("p1_value_to_p2_operation_resolution_matrix_missing")
    if catalog_payload is None:
        blockers.append("implementation_component_catalog_missing")
    if obligation_payload is None:
        blockers.append("component_action_card_obligation_matrix_missing")

    resolutions = _index_rows((resolution_payload or {}).get("resolutions", []), "value_signal_id")
    catalog = _index_rows((catalog_payload or {}).get("components", []), "component_id")
    obligations = _index_rows((obligation_payload or {}).get("components", []), "component_id")
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
    source_scope = _join_values(available_source_ids)
    operation_scope = _join_values(upstream_operations)
    target_scope = target_path_hint or "review-bound"
    lines: list[str] = []
    for test_type in required_tests:
        normalized = test_type.strip().lower()
        if normalized == "unit":
            lines.append(f"- unit: verify component-local behavior from {source_scope}")
        elif normalized == "contract":
            lines.append(f"- contract: verify public operation contract {operation_scope}")
        elif normalized == "integration":
            lines.append(f"- integration: verify the {component_id} boundary at {target_scope}")
        else:
            lines.append(f"- {test_type}: verify evidence against source-backed claims")
    return lines or ["- review-bound: required tests were not declared by Phase-2"]


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
        f"- upstream_operation_ids: {_join_values(upstream_operations)}",
        f"- upstream_operation_claim_refs: {_join_values(operation_claim_refs)}",
        f"- upstream_p1_trace_ids: {_join_values(upstream_p1_traces)}",
        f"- business_value_weight: {obligation.get('business_value_weight', 'review-bound')}",
        f"- engineering_risk_tier: {engineering_risk_tier}",
        f"- implementation_complexity: {implementation_complexity}",
        "",
        "## Required Sources",
        f"- required_source_ids: {_join_values(required_source_ids)}",
        f"- available_source_ids: {_join_values(available_source_ids, 'none')}",
        f"- missing_source_types: {_join_values(missing_source_types, 'none')}",
        "",
        "## Contract To Preserve",
        f"- operation_contract: {_join_values(upstream_operations)}",
        f"- operation_claim_ref: {_join_values(operation_claim_refs)}",
        f"- component_contract: {component_id} remains the {component_type} implementation component",
        f"- target_path_hint: {target_path_hint}",
        "",
        "## Source-Bound Behavior Scope",
        f"- source-backed inputs: {_join_values(available_source_ids, 'none')}",
        f"- required inputs: {_join_values(required_source_ids)}",
        f"- review-bound gaps: {_join_values(missing_source_types, 'none')}",
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
