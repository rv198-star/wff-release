#!/usr/bin/env python3
"""Build the Phase-1 semantic authoring spine before stage / PRD authoring."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from phase1.phase1_generation_kernel import (
    clean_source_text_value as _clean_text,
    find_markdown_block as _find_markdown_block,
)
from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases


ARTIFACT_ID = "p1-semantic-authoring-spine.v1"

SEMANTIC_TYPES = (
    "workflow_activity",
    "state_lifecycle",
    "object_data_record",
    "role_actor_decision_owner",
    "audit_compliance_constraint",
    "dashboard_review_decision_surface",
    "metric_success_signal",
    "open_truth_gap",
    "deferred_out_of_scope",
)

PROCESS_SURFACE_HEADINGS = (
    "Product Truth Challenge Notes",
    "Challenge Axis Coverage",
    "Truth-State Ledger",
    "Reviewer Concerns",
    "Admission Decision",
    "Handoff Note For wff-req",
)



def _is_packet(source_text: str) -> bool:
    return bool(re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE))



def _fact_surface(source_text: str) -> str:
    if not _is_packet(source_text):
        return source_text
    return normalize_source_handoff_phrases(_find_markdown_block(source_text, ("P1 Source Brief",)) or source_text)


def _section_title(line: str) -> str:
    return re.sub(r"^#+\s*", "", line).strip()


def _fact_candidates(block: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    section = "source"
    active_plain_label = ""
    table_headers: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            title = _section_title(line)
            if title in PROCESS_SURFACE_HEADINGS:
                section = "process-surface"
            else:
                section = title
            active_plain_label = ""
            table_headers = []
            continue
        if section == "process-surface":
            continue
        plain_label = re.match(r"^([A-Za-z0-9 /_-]{1,50}|P[0-9])\s*[:：]\s*$", line)
        if plain_label:
            active_plain_label = _clean_text(plain_label.group(1))
            table_headers = []
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [_clean_text(cell) for cell in line.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells):
                continue
            if not table_headers:
                table_headers = [cell.lower() for cell in cells]
                continue
            if len(cells) != len(table_headers):
                continue
            row_text = " / ".join(cell for cell in cells if cell)
            if row_text:
                candidates.append(
                    {
                        "source_excerpt": row_text,
                        "source_section": section,
                    }
                )
            continue
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if bullet:
            value = _clean_text(bullet.group(1))
            if value:
                source_section = f"{section} / {active_plain_label}" if active_plain_label else section
                candidates.append(
                    {
                        "source_excerpt": value,
                        "source_section": source_section,
                    }
                )
    return candidates


def _open_gap_candidates(source_text: str) -> list[dict[str, str]]:
    if not _is_packet(source_text):
        return []
    block = _find_markdown_block(source_text, ("Open Truth Gaps",))
    gaps: list[dict[str, str]] = []
    for raw in block.splitlines()[1:]:
        line = raw.strip()
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if not bullet:
            continue
        value = _clean_text(bullet.group(1))
        if value:
            gaps.append({"source_excerpt": value, "source_section": "Open Truth Gaps"})
    return gaps


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(token.casefold() in lowered for token in tokens)


def _semantic_matches(excerpt: str, section: str) -> list[tuple[str, str]]:
    text = f"{section} {excerpt}"
    matches: list[tuple[str, str]] = []
    if _has_any(
        text,
        (
            "state",
            "status",
            "lifecycle",
            "transition",
            "pending",
            "overdue",
            "completed",
            "blocked",
            "requested",
            "reviewed",
            "状态",
            "流转",
            "待处理",
            "逾期",
            "完成",
            "阻塞",
        ),
    ):
        matches.append(("state_lifecycle", "state_model_transition_guard"))
    if _has_any(
        text,
        (
            "audit",
            "compliance",
            "permission",
            "access",
            "retention",
            "sensitive",
            "role-based",
            "权限",
            "审计",
            "合规",
            "留痕",
            "留存",
            "敏感",
        ),
    ):
        matches.append(("audit_compliance_constraint", "nfr_audit_acceptance"))
    if _has_any(
        text,
        (
            "review",
            "dashboard",
            "visibility",
            "decision",
            "view",
            "pending",
            "overdue",
            "completed",
            "compare",
            "视图",
            "看板",
            "复盘",
            "决策",
            "可见",
        ),
    ):
        matches.append(("dashboard_review_decision_surface", "ia_review_decision_surface"))
    if _has_any(
        text,
        (
            "role",
            "actor",
            "owner",
            "buyer",
            "operator",
            "lead",
            "coordinator",
            "specialist",
            "责任",
            "角色",
            "负责人",
            "决策",
        ),
    ):
        matches.append(("role_actor_decision_owner", "role_boundary_decision_owner"))
    if _has_any(
        text,
        (
            "record",
            "data",
            "object",
            "request",
            "work item",
            "notes",
            "记录",
            "对象",
            "数据",
        ),
    ):
        matches.append(("object_data_record", "domain_object_data_record"))
    if _has_any(
        text,
        (
            "rate",
            "metric",
            "signal",
            "success",
            "threshold",
            "compare",
            "指标",
            "信号",
            "阈值",
            "成功",
        ),
    ):
        matches.append(("metric_success_signal", "validation_metric_success_signal"))
    if _has_any(text, ("out of scope", "non-goal", "deferred", "later", "future", "范围外", "非目标", "后续")):
        matches.append(("deferred_out_of_scope", "scope_boundary_deferred_item"))
    if _has_any(
        text,
        (
            "intake",
            "execution",
            "handoff",
            "closure",
            "complete",
            "open",
            "workflow",
            "service",
            "执行",
            "交接",
            "闭环",
            "流程",
        ),
    ):
        matches.append(("workflow_activity", "workflow_activity_user_journey"))
    return matches


def _instruction_for(semantic_type: str) -> str:
    instructions = {
        "workflow_activity": "Use as user journey or workflow activity only after separating embedded state, role, and audit semantics.",
        "state_lifecycle": "Use as lifecycle/state semantics, transition guard, or status model; do not render as a standalone module.",
        "object_data_record": "Use as domain object or information model material, not only as page copy.",
        "role_actor_decision_owner": "Use as role boundary, permission, handoff, or decision-owner material.",
        "audit_compliance_constraint": "Use as NFR, audit, compliance, risk, or acceptance material; do not turn into a workflow step.",
        "dashboard_review_decision_surface": "Use as IA, dashboard, review, or decision surface material; do not flatten into CRUD module names.",
        "metric_success_signal": "Use as validation signal or success metric under the current evidence ceiling.",
        "open_truth_gap": "Preserve as review-bound truth and claim ceiling; do not upgrade into confirmed requirements.",
        "deferred_out_of_scope": "Preserve as scope boundary, later slice, or future seam; do not promote into P0 promise.",
    }
    return instructions[semantic_type]


def _forbidden_for(semantic_type: str) -> str:
    forbidden = {
        "workflow_activity": "Do not let workflow labels swallow state, audit, role, or decision semantics.",
        "state_lifecycle": "Do not turn this into a main module name.",
        "object_data_record": "Do not reduce this to decorative UI field text.",
        "role_actor_decision_owner": "Do not replace source-native role language with generic primary operator placeholders.",
        "audit_compliance_constraint": "Do not make this a happy-path workflow step.",
        "dashboard_review_decision_surface": "Do not make this a generic CRUD module.",
        "metric_success_signal": "Do not present this as already externally validated.",
        "open_truth_gap": "Do not close this gap without source evidence.",
        "deferred_out_of_scope": "Do not include this in the first-wave P0 promise.",
    }
    return forbidden[semantic_type]


def _truth_state_for(semantic_type: str, source_section: str) -> str:
    if semantic_type == "open_truth_gap":
        return "review-bound"
    if "simulated" in source_section.casefold():
        return "simulated-source-backed"
    return "source-grounded"


def _downstream_consumers(semantic_type: str) -> list[str]:
    if semantic_type in {"state_lifecycle", "audit_compliance_constraint", "dashboard_review_decision_surface"}:
        return ["stage_02a", "stage_02b", "stage_03", "stage_04", "prd"]
    if semantic_type in {"open_truth_gap", "metric_success_signal"}:
        return ["stage_04", "prd"]
    return ["stage_02a", "stage_02b", "prd"]


def _summary(units: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {semantic_type: [] for semantic_type in SEMANTIC_TYPES}
    seen: dict[str, set[str]] = defaultdict(set)
    for unit in units:
        semantic_type = str(unit["semantic_type"])
        excerpt = str(unit["source_excerpt"])
        if excerpt in seen[semantic_type]:
            continue
        seen[semantic_type].add(excerpt)
        grouped[semantic_type].append(
            {
                "unit_id": str(unit["unit_id"]),
                "source_excerpt": excerpt,
                "placement_target": str(unit["placement_target"]),
            }
        )
    return grouped


def build_semantic_authoring_spine(source_text: str) -> dict[str, Any]:
    fact_surface = _fact_surface(source_text)
    candidates = _fact_candidates(fact_surface)
    units: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for candidate in candidates:
        excerpt = candidate["source_excerpt"]
        section = candidate["source_section"]
        for semantic_type, placement_target in _semantic_matches(excerpt, section):
            key = (excerpt, semantic_type)
            if key in seen:
                continue
            seen.add(key)
            units.append(
                {
                    "unit_id": f"SEM-{len(units) + 1:03d}",
                    "source_excerpt": excerpt,
                    "source_section": section,
                    "truth_state": _truth_state_for(semantic_type, section),
                    "semantic_type": semantic_type,
                    "placement_target": placement_target,
                    "authoring_instruction": _instruction_for(semantic_type),
                    "forbidden_flattening": _forbidden_for(semantic_type),
                    "downstream_consumers": _downstream_consumers(semantic_type),
                }
            )

    for gap in _open_gap_candidates(source_text):
        excerpt = gap["source_excerpt"]
        key = (excerpt, "open_truth_gap")
        if key in seen:
            continue
        seen.add(key)
        units.append(
            {
                "unit_id": f"SEM-{len(units) + 1:03d}",
                "source_excerpt": excerpt,
                "source_section": gap["source_section"],
                "truth_state": "review-bound",
                "semantic_type": "open_truth_gap",
                "placement_target": "claim_ceiling_review_bound_gap",
                "authoring_instruction": _instruction_for("open_truth_gap"),
                "forbidden_flattening": _forbidden_for("open_truth_gap"),
                "downstream_consumers": _downstream_consumers("open_truth_gap"),
            }
        )

    return {
        "artifact_id": ARTIFACT_ID,
        "source_kind": "p1-source-input-packet" if _is_packet(source_text) else "source-brief",
        "semantic_types": list(SEMANTIC_TYPES),
        "semantic_units": units,
        "placement_summary": _summary(units),
        "claim_ceiling": {
            "allowed": "P1 authoring may use source-grounded semantic placement under current evidence.",
            "forbidden": "external validation, owner sign-off, budget approval, production readiness",
        },
        "control_boundary": {
            "workflow": "preserve source order, contract shape, and evidence retention",
            "agentic": "interpret source facts into product semantic placement before authoring",
            "evidence": "retain source excerpt, truth state, placement target, and claim ceiling",
        },
    }
