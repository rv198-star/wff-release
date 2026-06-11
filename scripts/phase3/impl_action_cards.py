from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from phase3.action_card_execution_map import build_action_card_execution_context
from common.claim_control_runtime import (
    CanonicalName,
    ClaimRecord,
    ClaimRelation,
    canonical_names_from_sidecar,
    claims_from_sidecar,
    emit_path_b_claim_control_sidecar,
)
from common.cross_phase_surface_policy import find_cross_phase_surface_path
from phase3.impl_context import p2_operation_claim_id
from phase3.impl_context import write_json
from phase3.phase3_implementation_action_card_scaffolder import (
    card_depth_label,
    load_action_card_obligations,
    render_implementation_action_card,
    validate_action_card_obligations,
)


ACTION_CARD_READINESS_CLAIM_CEILING = (
    "card-readiness classification only; direct implementation still requires runtime evidence, tests, and human review"
)
PROPOSED_CLAIM_REF_RE = re.compile(r"(?<![A-Za-z0-9_-])PROPOSED[-:][A-Za-z0-9_.:-]+(?![A-Za-z0-9_-])")


def build_action_card_readiness_summary(component_obligations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    counts_by_acd_level: dict[str, int] = {}
    readiness_counts = {
        "direct-implementation-ready": 0,
        "split-required-parent": 0,
        "review-bound": 0,
    }
    direct_ready_acd_levels = {"ACD-0", "ACD-1", "ACD-2"}

    for component_key, obligation in sorted(component_obligations.items()):
        component_id = str(obligation.get("component_id") or component_key or "review-bound").strip()
        acd_level = str(obligation.get("acd_level") or "review-bound").strip()
        required_card_type = str(obligation.get("required_card_type") or "").strip()
        source_status = str(obligation.get("source_sufficiency_status") or "review-bound").strip()
        source_status_normalized = source_status.lower()
        missing_sources = [
            str(item).strip()
            for item in obligation.get("missing_source_types", [])
            if str(item).strip()
        ]
        counts_by_acd_level[acd_level] = counts_by_acd_level.get(acd_level, 0) + 1

        if acd_level == "ACD-3":
            readiness = "split-required-parent"
            blocked = True
            reason = "ACD-3 parent card must be decomposed before direct coding"
        elif acd_level in direct_ready_acd_levels and source_status_normalized == "sufficient" and not missing_sources:
            readiness = "direct-implementation-ready"
            blocked = False
            reason = "non-ACD-3 card has sufficient source material and no missing source types"
        else:
            readiness = "review-bound"
            blocked = True
            if missing_sources:
                reason = "missing source material: " + ", ".join(missing_sources)
            elif source_status_normalized != "sufficient":
                reason = f"source_sufficiency_status={source_status}"
            else:
                reason = f"unsupported_acd_level={acd_level}"

        readiness_counts[readiness] += 1
        components.append(
            {
                "component_id": component_id,
                "component_type": str(obligation.get("component_type") or "review-bound").strip(),
                "acd_level": acd_level,
                "card_depth": card_depth_label(acd_level, required_card_type),
                "source_sufficiency_status": source_status,
                "missing_source_types": missing_sources,
                "readiness": readiness,
                "direct_implementation_blocked": blocked,
                "reason": reason,
            }
        )

    return {
        "artifact_kind": "phase3-action-card-readiness-summary",
        "claim_ceiling": ACTION_CARD_READINESS_CLAIM_CEILING,
        "total_action_card_count": len(components),
        "direct_implementation_ready_count": readiness_counts["direct-implementation-ready"],
        "split_required_parent_count": readiness_counts["split-required-parent"],
        "review_bound_count": readiness_counts["review-bound"],
        "counts_by_acd_level": dict(sorted(counts_by_acd_level.items())),
        "components": components,
    }


def run_impl_action_cards(
    *,
    phase2_root: Path,
    output_dir: Path,
    output_locale: str = "zh-CN",
) -> dict[str, Any]:
    del output_locale
    action_dir = output_dir / "action-cards"
    action_dir.mkdir(parents=True, exist_ok=True)
    intake_blockers = _phase2_intake_blockers(phase2_root)
    if intake_blockers:
        readiness_summary = build_action_card_readiness_summary({})
        validation = {
            "blockers": ["phase2_intake_blocked"],
            "intake_blockers": intake_blockers,
            "passed": False,
        }
        validation_payload = {
            **validation,
            "card_count": 0,
            "cards": [],
            "readiness_summary": readiness_summary,
        }
        write_json(action_dir / "validation.json", validation_payload)
        summary = {
            "artifact_kind": "phase3-impl-action-cards-report",
            "quality_gate": "blocked",
            "action_card_count": 0,
            "action_card_dir": str(action_dir),
            "execution_map_path": "",
            "human_audit_packet_path": "",
            "card_count": 0,
            "cards": [],
            "claim_control_sidecars": [],
            "readiness_summary": readiness_summary,
            "validation": validation,
            "validation_payload": validation_payload,
        }
        write_json(output_dir / "action-card-report.json", summary)
        return summary

    obligations = load_action_card_obligations(phase2_root)
    catalog = obligations.get("component_catalog", {})
    upstream_claims = _phase2_claims_for_action_cards(phase2_root)
    validation = _validate_action_card_upstream_claims(obligations, upstream_claims)
    if not validation.get("passed"):
        readiness_summary = build_action_card_readiness_summary({})
        validation_payload = {
            **validation,
            "card_count": 0,
            "cards": [],
            "readiness_summary": readiness_summary,
        }
        write_json(action_dir / "validation.json", validation_payload)
        summary = {
            "artifact_kind": "phase3-impl-action-cards-report",
            "quality_gate": "review-bound",
            "action_card_count": 0,
            "action_card_dir": str(action_dir),
            "execution_map_path": "",
            "human_audit_packet_path": "",
            "card_count": 0,
            "cards": [],
            "claim_control_sidecars": [],
            "readiness_summary": readiness_summary,
            "validation": validation,
            "validation_payload": validation_payload,
        }
        write_json(output_dir / "action-card-report.json", summary)
        return summary
    written: list[str] = []
    claim_control_sidecars: list[dict[str, Any]] = []
    for component_id, obligation in obligations.get("component_obligations", {}).items():
        card_path = action_dir / f"{str(component_id).lower()}-action-card.md"
        card_path.write_text(
            render_implementation_action_card(obligation, catalog.get(component_id)),
            encoding="utf-8",
        )
        written.append(str(card_path))
        claims = _claims_for_action_card(component_id, obligation, upstream_claims)
        relations = _relations_for_action_card(component_id)
        upstream_source_claim_refs = _upstream_source_claim_refs_for_action_card(obligation, upstream_claims)
        canonical_names = _canonical_names_for_action_card(phase2_root, component_id, obligation, upstream_claims)
        sidecar_result = emit_path_b_claim_control_sidecar(
            artifact_path=card_path,
            artifact_id=f"p3-action-card:{component_id}",
            claims=claims,
            view_id=f"p3-action-card:{component_id}",
            source_count=2,
            upstream_surface_paths=_phase2_claim_control_sidecar_paths(phase2_root),
            relations=relations,
            canonical_names=canonical_names,
            source_claim_refs=upstream_source_claim_refs,
        )
        claim_control_sidecars.append(
            {
                "artifact_path": str(card_path),
                "sidecar_path": sidecar_result["sidecar_path"],
                "overall_status": sidecar_result["acceptance"]["overall_status"],
                "claim_count": len(sidecar_result["surface"]["claim_index"]["claims"]),
            }
        )

    validation = validate_action_card_obligations(obligations)
    readiness_summary = build_action_card_readiness_summary(obligations.get("component_obligations", {}))
    validation_payload = {
        **validation,
        "card_count": len(written),
        "cards": written,
        "readiness_summary": readiness_summary,
    }
    write_json(action_dir / "validation.json", validation_payload)
    readiness_summary_path = output_dir / ".phase3-review" / "action-card-readiness-summary.json"
    write_json(readiness_summary_path, readiness_summary)
    execution_context = build_action_card_execution_context(
        component_obligations=obligations.get("component_obligations", {}),
        component_catalog=catalog,
    )
    execution_map_path = output_dir / ".phase3-review" / "action-card-execution-map.json"
    write_json(execution_map_path, execution_context["pointer_manifest"])
    audit_packet_path = output_dir / ".phase3-review" / "action-card-human-audit-packet.json"
    write_json(
        audit_packet_path,
        {
            "artifact_kind": "phase3-action-card-human-audit-packet",
            "action_cards": written,
            "validation": validation,
            "readiness_summary": readiness_summary,
            "claim_ceiling": "review packet only; human acceptance is not implied",
        },
    )
    summary = {
        "artifact_kind": "phase3-impl-action-cards-report",
        "quality_gate": "pass" if validation.get("passed") else "review-bound",
        "action_card_count": len(written),
        "action_card_dir": str(action_dir),
        "execution_map_path": str(execution_map_path),
        "human_audit_packet_path": str(audit_packet_path),
        "readiness_summary_path": str(readiness_summary_path),
        "card_count": len(written),
        "cards": written,
        "claim_control_sidecars": claim_control_sidecars,
        "readiness_summary": readiness_summary,
        "validation": validation,
        "validation_payload": validation_payload,
    }
    write_json(output_dir / "action-card-report.json", summary)
    return summary


def _phase2_claim_control_sidecar_paths(phase2_root: Path) -> list[Path]:
    paths = list(phase2_root.glob("*.claim-control.json"))
    component_inventory = find_cross_phase_surface_path(
        phase2_root,
        "phase2",
        "component-semantic-inventory.claim-control.json",
    )
    if component_inventory.exists():
        paths.append(component_inventory)
    return sorted({path.resolve(): path for path in paths}.values())


def _phase2_intake_blockers(phase2_root: Path) -> list[str]:
    blockers: list[str] = []
    verdict_path = phase2_root / "phase-verdict.json"
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            verdict = {}
        formal_state = str(verdict.get("recommended_formal_state", "")).strip().lower()
        verdict_label = str(verdict.get("verdict", "")).strip().lower()
        if formal_state == "blocked" or verdict_label == "blocked":
            blockers.append("phase2_formal_state_blocked")

    implementation_entry = phase2_root / "phase-3-implementation-entry.md"
    if implementation_entry.exists():
        text = implementation_entry.read_text(encoding="utf-8")
        may_start = _extract_nested_scalar(text, "may_start") or _extract_nested_scalar(text, "是否可以开始")
        readiness_label = (
            _extract_nested_scalar(text, "strongest_supported_readiness_label")
            or _extract_nested_scalar(text, "最强可支持就绪标签")
        )
        if may_start.strip().lower() in {"no", "false"}:
            blockers.append("phase2_implementation_entry_disallows_start")
        if readiness_label.strip().lower() == "blocked" and may_start.strip().lower() == "yes":
            blockers.append("phase2_implementation_entry_contradicts_blocked_state")
    return sorted(set(blockers))


def _extract_nested_scalar(text: str, field_name: str) -> str:
    pattern = rf"{re.escape(field_name)}:\s*\n\s+- `?([^`\n]+)`?"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    inline_pattern = rf"^\s*- {re.escape(field_name)}:\s*`?([^`\n][^\n`]*)`?\s*$"
    inline_match = re.search(inline_pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return inline_match.group(1).strip() if inline_match else ""


def _phase2_claims_for_action_cards(phase2_root: Path) -> list[ClaimRecord]:
    claims: list[ClaimRecord] = []
    for sidecar_path in _phase2_claim_control_sidecar_paths(phase2_root):
        claims.extend(claims_from_sidecar(sidecar_path, source_label="phase2-claim-control"))
    return claims


def _phase2_canonical_names_for_action_cards(phase2_root: Path) -> list[CanonicalName]:
    names: list[CanonicalName] = []
    for sidecar_path in _phase2_claim_control_sidecar_paths(phase2_root):
        names.extend(canonical_names_from_sidecar(sidecar_path))
    return names


def _validate_action_card_upstream_claims(
    obligations: dict[str, Any], upstream_claims: list[ClaimRecord]
) -> dict[str, Any]:
    validation = validate_action_card_obligations(obligations)
    accepted_upstream_ids = {claim.id for claim in upstream_claims}
    proposed_claim_refs = _proposed_claim_refs(obligations)
    declared_upstream_ids: set[str] = set()
    declared_component_ids: set[str] = set()
    declared_operation_claim_ids: set[str] = set()
    for obligation in obligations.get("component_obligations", {}).values():
        component_id = str(obligation.get("component_id") or "").strip()
        if component_id:
            declared_component_ids.add(component_id)
        declared_operation_claim_ids.update(
            p2_operation_claim_id(operation_id)
            for operation_id in obligation.get("upstream_operation_ids", [])
            if str(operation_id).strip()
        )
        declared_upstream_ids.update(
            str(item).strip()
            for item in obligation.get("upstream_p1_trace_ids", [])
            if str(item).strip()
        )
    missing = sorted(declared_upstream_ids - accepted_upstream_ids)
    missing_components = sorted(declared_component_ids - accepted_upstream_ids)
    missing_operations = sorted(declared_operation_claim_ids - accepted_upstream_ids)
    blockers = list(validation.get("blockers", []))
    if missing:
        blockers.append("action_card_upstream_claim_missing")
    if missing_components:
        blockers.append("action_card_component_claim_missing")
    if missing_operations:
        blockers.append("action_card_operation_claim_missing")
    if proposed_claim_refs:
        blockers.append("action_card_proposed_claim_ref")
    return {
        **validation,
        "blockers": list(dict.fromkeys(blockers)),
        "passed": not blockers,
        "missing_upstream_claim_refs": missing,
        "missing_component_claim_refs": missing_components,
        "missing_operation_claim_refs": missing_operations,
        "proposed_claim_refs": proposed_claim_refs,
    }


def _proposed_claim_refs(value: Any) -> list[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            refs.update(_proposed_claim_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_proposed_claim_refs(item))
    elif isinstance(value, str):
        refs.update(PROPOSED_CLAIM_REF_RE.findall(value))
    return sorted(refs)


def _claims_for_action_card(component_id: object, obligation: dict[str, Any], upstream_claims: list[ClaimRecord]) -> list[ClaimRecord]:
    component_claim_id = str(component_id or obligation.get("component_id") or "P2-CMP-UNKNOWN").strip()
    action_card_claim = _action_card_claim_for_component(component_claim_id)
    upstream_ids = {str(item).strip() for item in obligation.get("upstream_p1_trace_ids", []) if str(item).strip()}
    upstream_ids.add(component_claim_id)
    upstream_ids.update(
        p2_operation_claim_id(operation_id)
        for operation_id in obligation.get("upstream_operation_ids", [])
        if str(operation_id).strip()
    )
    selected = [claim for claim in upstream_claims if claim.id in upstream_ids]
    if selected:
        return [action_card_claim, *selected]
    return [action_card_claim]


def _upstream_source_claim_refs_for_action_card(obligation: dict[str, Any], upstream_claims: list[ClaimRecord]) -> list[str]:
    upstream_ids = {str(item).strip() for item in obligation.get("upstream_p1_trace_ids", []) if str(item).strip()}
    component_id = str(obligation.get("component_id") or "").strip()
    if component_id:
        upstream_ids.add(component_id)
    upstream_ids.update(
        p2_operation_claim_id(operation_id)
        for operation_id in obligation.get("upstream_operation_ids", [])
        if str(operation_id).strip()
    )
    accepted_upstream_ids = {claim.id for claim in upstream_claims}
    return sorted(upstream_ids & accepted_upstream_ids)


def _canonical_names_for_action_card(
    phase2_root: Path,
    component_id: object,
    obligation: dict[str, Any],
    upstream_claims: list[ClaimRecord],
) -> list[CanonicalName]:
    selected_ids = set(_upstream_source_claim_refs_for_action_card(obligation, upstream_claims))
    component_claim_id = str(component_id or obligation.get("component_id") or "").strip()
    action_card_claim_id = f"P3-ACTION-CARD:{component_claim_id}" if component_claim_id else ""
    names = [
        name
        for name in _phase2_canonical_names_for_action_cards(phase2_root)
        if name.id in selected_ids
    ]
    if action_card_claim_id:
        names.append(CanonicalName(id=action_card_claim_id, canonical=action_card_claim_id))
    return names


def _action_card_claim_for_component(component_id: str) -> ClaimRecord:
    claim_id = f"P3-ACTION-CARD:{component_id}"
    return ClaimRecord(
        id=claim_id,
        kind="implementation_action_card",
        text=f"Phase 3 Action Card realizing {component_id}",
        source_refs=["phase3:action-card"],
    )


def _relations_for_action_card(component_id: object) -> list[ClaimRelation]:
    component_claim_id = str(component_id or "P2-CMP-UNKNOWN").strip()
    action_card_claim_id = f"P3-ACTION-CARD:{component_claim_id}"
    return [
        ClaimRelation(
            subject=component_claim_id,
            predicate="realized_by",
            object=action_card_claim_id,
        )
    ]
