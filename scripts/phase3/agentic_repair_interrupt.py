from __future__ import annotations

import json
from typing import Any


INTERRUPT_VERDICTS = {"RETURN-REMEDIATE", "BLOCKED"}
MATERIAL_HUMAN_REVIEW_ACTIONS = {"要求修改", "要求返回", "提供干预输入"}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string(value: Any) -> str:
    return str(value).strip()


def _owner_phase(defect_key: str) -> str:
    normalized = defect_key.lower()
    if "api_contract" in normalized or "contract_frozen" in normalized:
        return "P2"
    if "source" in normalized or "business_truth" in normalized:
        return "P1"
    if normalized.startswith("frontend"):
        return "P3"
    return "P3"


def _repair_route(owner_phase: str) -> str:
    return "repair-in-phase" if owner_phase == "P3" else "return-upstream"


def _minimum_rerun_boundary(owner_phase: str) -> str:
    if owner_phase == "P1":
        return "phase1-to-phase3"
    if owner_phase == "P2":
        return "phase2-to-phase3"
    return "phase3-targeted-gate"


def _change_unit_types(defect_key: str, owner_phase: str) -> list[str]:
    normalized = defect_key.lower()
    if owner_phase != "P3":
        return ["source-or-contract", "evidence"]
    if "verification" in normalized:
        return ["test", "evidence", "code"]
    if "database" in normalized or "migration" in normalized or "persistence" in normalized:
        return ["code", "test", "evidence"]
    if "backend_service_boundary" in normalized:
        return ["code", "test", "evidence"]
    return ["code", "test", "evidence"]


def _required_agentic_actions(defect_key: str, owner_phase: str) -> list[str]:
    if owner_phase != "P3":
        return [
            f"route defect to {owner_phase} with evidence and minimum rerun boundary",
            "do not repair upstream truth inside P3",
            "cap P3 claims until upstream truth is regenerated and rerun",
        ]
    normalized = defect_key.lower()
    if "backend_service_boundary" in normalized:
        return [
            "inspect generated service/API boundary for scaffold-only behavior",
            "repair code so the selected backend behavior is executable through the service boundary",
            "add or deepen tests that prove behavior rather than transport shape",
            "rerun the targeted P3 gate before raising formal state",
        ]
    if "verification" in normalized:
        return [
            "identify the missing runtime-backed verification family",
            "add or repair targeted contract/scenario/replay/runtime evidence",
            "rerun the smallest verification gate that can prove the claim",
        ]
    return [
        "localize the generated artifact gap",
        "repair code, test, or evidence as needed",
        "rerun the minimum P3 gate before closure",
    ]


def _material_human_review_action(human_review: dict[str, Any] | None) -> str:
    if not isinstance(human_review, dict):
        return ""
    action = _string(human_review.get("action"))
    return action if action in MATERIAL_HUMAN_REVIEW_ACTIONS else ""


def _owner_phase_from_defect(defect: dict[str, Any], defect_key: str) -> str:
    explicit = _string(defect.get("owner_phase")).upper()
    if explicit in {"P1", "P2", "P3"}:
        return explicit
    combined_signal = " ".join(
        [
            defect_key,
            _string(defect.get("module_key")),
            _string(defect.get("finding")),
            _string(defect.get("rewrite_objective")),
        ]
    )
    return _owner_phase(combined_signal)


def _human_review_status(defect: dict[str, Any]) -> str:
    severity = _string(defect.get("severity")).lower()
    if severity in {"review-bound", "review_bound", "nonblocking", "reserved"}:
        return "REVIEW-BOUND"
    return "BLOCKED"


def _string_list(value: Any) -> list[str]:
    items: list[str] = []
    for item in _as_list(value):
        text = _string(item)
        if text:
            items.append(text)
    return items


def _human_review_required_actions(defect_key: str, owner_phase: str) -> list[str]:
    if owner_phase != "P3":
        return _required_agentic_actions(defect_key, owner_phase)
    return [
        "定位人工 Review 指出的模块质量缺陷",
        "在 repair workspace 内进行有边界的代码、测试或证据重写",
        "运行本地 P3 targeted gate",
        "需要关闭 P3 blocker 时运行 full-targeted evidence 和 closure refresh",
    ]


def _human_review_repair_packets(human_review: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(human_review, dict):
        return []
    if not _material_human_review_action(human_review):
        return []

    packets: list[dict[str, Any]] = []
    for index, defect in enumerate(_as_list(human_review.get("defects")), start=1):
        if not isinstance(defect, dict):
            continue
        defect_id = _string(defect.get("defect_id")) or f"HR-P3-{index:03d}"
        module_key = _string(defect.get("module_key"))
        defect_key = f"human_review_module_rewrite_{defect_id}"
        owner_phase = _owner_phase_from_defect(defect, defect_key)
        affected_files = _string_list(defect.get("affected_files"))
        packet = {
            "packet_id": f"P3-review-rewrite-{defect_id}",
            "packet_type": "human-review-module-rewrite",
            "source": f"human-rough-review.defects.{defect_id}",
            "defect_key": defect_key,
            "human_label": "人工 Review 模块强化重写",
            "status": _human_review_status(defect),
            "why": _string(defect.get("finding")),
            "owner_phase": owner_phase,
            "repair_route": _repair_route(owner_phase),
            "module_key": module_key,
            "affected_files": affected_files,
            "target_generated_units": affected_files,
            "rewrite_objective": _string(defect.get("rewrite_objective")),
            "change_unit_types": _change_unit_types(defect_key, owner_phase),
            "required_agentic_actions": _human_review_required_actions(defect_key, owner_phase),
            "minimum_rerun_boundary": _string(defect.get("evidence_gate")) or _minimum_rerun_boundary(owner_phase),
            "claim_ceiling": "implementation-in-progress",
        }
        if owner_phase != "P3":
            packet["minimum_rerun_boundary"] = _minimum_rerun_boundary(owner_phase)
        packets.append(packet)
    return packets


def _semantic_review_source(semantic_invariant_review: dict[str, Any] | None) -> str:
    if not isinstance(semantic_invariant_review, dict):
        return ""
    return _string(semantic_invariant_review.get("source")) or "semantic-invariant-detector"


def _semantic_drift_status(drift: dict[str, Any]) -> str:
    source_status = _string(drift.get("source_status")).lower().replace("_", "-")
    if source_status in {"resolved", "source-supported", "supported"}:
        return "BLOCKED"
    return "REVIEW-BOUND"


def _semantic_drift_owner_phase(status: str) -> str:
    return "P3" if status == "BLOCKED" else "P2"


def _semantic_invariant_required_actions(status: str) -> list[str]:
    if status != "BLOCKED":
        return [
            "route semantic source-truth gap upstream with evidence",
            "do not invent owner, aggregate, lifecycle, or mutation truth inside P3",
            "cap P3 claims until source-supported invariant is regenerated and rerun",
        ]
    return [
        "write or preserve RED semantic invariant tests before bounded rewrite",
        "repair generated code, tests, or evidence to satisfy the source-supported invariant",
        "rerun the targeted P3 gate before raising formal state",
        "use full-targeted evidence and closure refresh before closing P3 blockers",
    ]


def _semantic_invariant_repair_packets(
    semantic_invariant_review: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(semantic_invariant_review, dict):
        return []

    source = _semantic_review_source(semantic_invariant_review)
    packets: list[dict[str, Any]] = []
    for index, drift in enumerate(_as_list(semantic_invariant_review.get("drifts")), start=1):
        if not isinstance(drift, dict):
            continue
        drift_id = _string(drift.get("drift_id")) or f"SI-{index:03d}"
        status = _semantic_drift_status(drift)
        owner_phase = _semantic_drift_owner_phase(status)
        packet = {
            "packet_id": f"P3-semantic-invariant-{drift_id}",
            "packet_type": "semantic-invariant-repair",
            "source": f"{source}.drifts.{drift_id}",
            "defect_key": f"semantic_invariant_drift_{drift_id}",
            "human_label": "语义不变量修复",
            "status": status,
            "why": _string(drift.get("finding")),
            "owner_phase": owner_phase,
            "repair_route": _repair_route(owner_phase),
            "source_operation_id": _string(drift.get("source_operation_id")),
            "invariant_type": _string(drift.get("invariant_type")),
            "expected_owner_service": _string(drift.get("expected_owner_service")),
            "expected_aggregate": _string(drift.get("expected_aggregate")),
            "expected_mutation_scope": _string(drift.get("expected_mutation_scope")),
            "expected_lifecycle_event": _string(drift.get("expected_lifecycle_event")),
            "source_ids": _string_list(drift.get("source_ids")),
            "affected_files": _string_list(drift.get("affected_files")),
            "target_generated_units": _string_list(drift.get("affected_files")),
            "red_test_targets": _string_list(drift.get("red_test_targets")),
            "review_bound_reasons": _string_list(drift.get("review_bound_reasons")),
            "change_unit_types": _change_unit_types("semantic_invariant_repair", owner_phase),
            "required_agentic_actions": _semantic_invariant_required_actions(status),
            "minimum_rerun_boundary": _minimum_rerun_boundary(owner_phase),
            "claim_ceiling": "implementation-in-progress" if status == "BLOCKED" else "review-bound",
        }
        packets.append(packet)
    return packets


def _repair_packets(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for row in _as_list(assessment.get("acceptance_rows")):
        if not isinstance(row, dict):
            continue
        status = _string(row.get("status")).upper()
        if status not in {"BLOCKED", "REVIEW-BOUND"}:
            continue
        defect_key = _string(row.get("key")) or "unnamed_defect"
        owner_phase = _owner_phase(defect_key)
        packets.append(
            {
                "packet_id": f"P3-repair-{defect_key}",
                "source": f"phase-mainline-scorecard.acceptance_rows.{defect_key}",
                "defect_key": defect_key,
                "human_label": _string(row.get("label")),
                "status": status,
                "why": _string(row.get("why")),
                "owner_phase": owner_phase,
                "repair_route": _repair_route(owner_phase),
                "change_unit_types": _change_unit_types(defect_key, owner_phase),
                "required_agentic_actions": _required_agentic_actions(defect_key, owner_phase),
                "minimum_rerun_boundary": _minimum_rerun_boundary(owner_phase),
                "claim_ceiling": "implementation-in-progress",
            }
        )
    return packets


def build_agentic_repair_interrupt(
    *,
    case_name: str,
    version: str,
    assessment: dict[str, Any],
    human_review: dict[str, Any] | None = None,
    semantic_invariant_review: dict[str, Any] | None = None,
    max_rounds: int = 2,
) -> dict[str, Any]:
    scorecard_packets = _repair_packets(assessment)
    human_review_packets = _human_review_repair_packets(human_review)
    semantic_invariant_packets = _semantic_invariant_repair_packets(semantic_invariant_review)
    packets = scorecard_packets + human_review_packets + semantic_invariant_packets
    verdict = _string(assessment.get("verdict"))
    human_action = _material_human_review_action(human_review)
    interrupt_required = bool(verdict in INTERRUPT_VERDICTS or human_action or semantic_invariant_packets)
    trigger_sources = ["phase-verdict", "phase-mainline-scorecard"]
    if human_action:
        trigger_sources.append("human-rough-review")
    if semantic_invariant_packets:
        trigger_sources.append(_semantic_review_source(semantic_invariant_review))
    blocking_packet_count = sum(1 for packet in packets if packet.get("status") == "BLOCKED")
    return {
        "artifact_kind": "phase3-agentic-repair-interrupt",
        "case_name": _string(case_name),
        "version": _string(version),
        "interrupt_required": interrupt_required,
        "trigger_sources": trigger_sources,
        "source_verdict": verdict,
        "source_total_score": assessment.get("total_score"),
        "claim_ceiling": _string(assessment.get("recommended_formal_state")) or "review-bound",
        "repair_loop": {
            "owner": "agentic",
            "workflow_role": "preserve checkpoint order, packet contract, rerun boundary, and evidence capture",
            "agentic_role": "localize whether to repair code, tests, runtime evidence, handoff, or return upstream",
            "evidence_role": "cap claims until targeted rerun evidence supports a stronger state",
            "max_rounds": max(1, int(max_rounds)),
            "stop_conditions": [
                "targeted rerun proves the blocking defect is closed",
                "the defect is routed to P1/P2/P4 with evidence and minimum rerun boundary",
                "max rounds are exhausted and the claim remains capped",
            ],
        },
        "repair_packets": packets,
        "human_rough_review_breakpoint": {
            "enabled": True,
            "actions": ["批准", "带保留项批准", "要求修改", "要求返回", "提供干预输入", "明确跳过审核"],
            "material_defect_actions": sorted(MATERIAL_HUMAN_REVIEW_ACTIONS),
            "rule": "material human-review defects must enter repair packets or upstream return, not final-report-only failure",
        },
        "summary": {
            "repair_packet_count": len(packets),
            "blocking_packet_count": blocking_packet_count,
            "review_bound_packet_count": len(packets) - blocking_packet_count,
            "human_review_interrupt": bool(human_action),
            "human_review_packet_count": len(human_review_packets),
            "semantic_invariant_packet_count": len(semantic_invariant_packets),
        },
    }


def render_agentic_repair_interrupt_markdown(
    interrupt: dict[str, Any],
    *,
    output_locale: str = "zh-CN",
) -> str:
    zh = _string(output_locale).lower() in {"zh-cn", "zh", "cn"}
    title = "# P3 Agentic 返工中断包" if zh else "# P3 Agentic Repair Interrupt"
    packets_title = "## 返工包" if zh else "## Repair Packets"
    boundary_title = "## 退出边界" if zh else "## Exit Boundary"
    lines = [
        title,
        "",
        f"- interrupt_required: `{str(bool(interrupt.get('interrupt_required'))).lower()}`",
        f"- source_verdict: `{interrupt.get('source_verdict', '')}`",
        f"- source_total_score: `{interrupt.get('source_total_score', '')}`",
        f"- claim_ceiling: `{interrupt.get('claim_ceiling', '')}`",
        f"- max_rounds: `{interrupt.get('repair_loop', {}).get('max_rounds', 0)}`",
        "",
        packets_title,
    ]
    for packet in _as_list(interrupt.get("repair_packets")):
        if not isinstance(packet, dict):
            continue
        lines.extend(
            [
                f"- `{packet.get('defect_key', '')}` {packet.get('human_label', '')}",
                f"  - status: `{packet.get('status', '')}`",
                f"  - owner_phase: `{packet.get('owner_phase', '')}`",
                f"  - repair_route: `{packet.get('repair_route', '')}`",
                f"  - minimum_rerun_boundary: `{packet.get('minimum_rerun_boundary', '')}`",
                f"  - change_unit_types: `{', '.join(str(item) for item in _as_list(packet.get('change_unit_types')))}`",
            ]
        )
        if packet.get("packet_type"):
            lines.append(f"  - packet_type: `{packet.get('packet_type', '')}`")
        if packet.get("module_key"):
            lines.append(f"  - module_key: `{packet.get('module_key', '')}`")
        if packet.get("rewrite_objective"):
            lines.append(f"  - rewrite_objective: `{packet.get('rewrite_objective', '')}`")
        affected_files = _string_list(packet.get("affected_files"))
        if affected_files:
            lines.append(f"  - affected_files: `{', '.join(affected_files)}`")
    lines.extend(
        [
            "",
            boundary_title,
            "- Scorecard and human-review blockers are repair interrupts, not final-report-only findings.",
            "- Workflow controls order; Agentic controls repair judgment; evidence caps claims.",
            "- Do not raise P3 formal state until targeted rerun evidence supports it.",
            "",
        ]
    )
    return "\n".join(lines)


def render_agentic_repair_interrupt_json(interrupt: dict[str, Any]) -> str:
    return json.dumps(interrupt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
