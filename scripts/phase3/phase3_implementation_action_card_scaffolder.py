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


def render_implementation_action_card(obligation: dict[str, Any], catalog_row: dict[str, Any] | None = None) -> str:
    catalog_row = catalog_row or {}
    component_type = str(obligation.get("component_type") or catalog_row.get("component_type") or "Service")
    acd_level = str(obligation.get("acd_level", "review-bound"))
    required_card_type = str(obligation.get("required_card_type", "review-bound-card"))
    lines = [
        f"# {card_family(component_type)}",
        "",
        f"- component_id: {obligation.get('component_id') or catalog_row.get('component_id') or 'review-bound'}",
        f"- component_type: {component_type}",
        f"- acd_level: {acd_level}",
        f"- card_depth: {card_depth_label(acd_level, required_card_type)}",
        f"- source_sufficiency_status: {obligation.get('source_sufficiency_status', 'review-bound')}",
        f"- target_path_hint: {catalog_row.get('target_path_hint', 'review-bound')}",
        "",
        "## Upstream Binding",
        f"- upstream_operation_ids: {', '.join(str(item) for item in obligation.get('upstream_operation_ids', [])) or 'review-bound'}",
        f"- upstream_p1_trace_ids: {', '.join(str(item) for item in obligation.get('upstream_p1_trace_ids', [])) or 'review-bound'}",
        f"- business_value_weight: {obligation.get('business_value_weight', 'review-bound')}",
        f"- engineering_risk_tier: {obligation.get('engineering_risk_tier', 'review-bound')}",
        f"- implementation_complexity: {obligation.get('implementation_complexity', 'review-bound')}",
        "",
        "## Required Sources",
        f"- required_source_ids: {', '.join(str(item) for item in obligation.get('required_source_ids', [])) or 'review-bound'}",
        f"- available_source_ids: {', '.join(str(item) for item in obligation.get('available_source_ids', [])) or 'none'}",
        f"- missing_source_types: {', '.join(str(item) for item in obligation.get('missing_source_types', [])) or 'none'}",
        "",
        "## Implementation Steps",
        "- preserve public contract and component responsibility from the P2 catalog row",
        "- implement only source-backed behavior steps; keep missing design material review-bound",
        "- bind code targets and tests back to this action card id",
        "",
        "## Required Tests",
        *[f"- {item}" for item in obligation.get("required_tests", [])],
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
