#!/usr/bin/env python3
"""
Shared WO-15 surface-contract taxonomy metrics for Phase-3/4 gates and closure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from phase3.ui_locale import normalize_role_display_name


LIFECYCLE_TRIGGERS = {"page_load", "route_enter", "handoff_resume"}
NON_READY_STATUSES = {"blocked", "review-bound", "stale"}
VALID_READINESS_STATUSES = {"ready", *NON_READY_STATUSES}


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _clean_text(value: Any) -> str:
    candidate = str(value or "").strip()
    return "" if candidate.lower() in {"", "-", "—", "none", "n/a"} else candidate


def _clean_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _page_rows(ui_ia_contract: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ui_ia_contract.get("pages", [])
    return [row for row in rows if isinstance(row, dict)]


def _interaction_rows(page: dict[str, Any]) -> list[dict[str, Any]]:
    rows = page.get("compiled_interactions", [])
    if isinstance(rows, list) and rows:
        return [row for row in rows if isinstance(row, dict)]
    return []


def _interaction_status(row: dict[str, Any]) -> str:
    return _clean_text(row.get("readiness_status")).lower() or "ready"


def _raw_readiness_status(row: dict[str, Any]) -> str:
    return _clean_text(row.get("readiness_status")).lower()


def _blocked_reason(row: dict[str, Any]) -> str:
    return _clean_text(row.get("blocked_reason"))


def _is_core_surface(page: dict[str, Any]) -> bool:
    page_role = _clean_text(page.get("page_role")).lower()
    if not page_role:
        return True
    return page_role not in {"support", "secondary", "supplementary", "auxiliary"}


def _core_scope_source(pages: list[dict[str, Any]]) -> str:
    explicit_roles = [
        _clean_text(page.get("page_role")).lower()
        for page in pages
        if _clean_text(page.get("page_role"))
    ]
    if explicit_roles:
        return "page_role_excludes_support_surfaces"
    return "contract_slice_defaults_to_core_scope"


def _canonical_role_variants(value: str) -> set[str]:
    candidate = _clean_text(value)
    if not candidate:
        return set()
    variants = {
        re.sub(r"\s+", " ", candidate).strip().lower(),
        re.sub(r"\s+", " ", normalize_role_display_name(candidate, None)).strip().lower(),
        re.sub(r"\s*\([^()]*\)\s*", " ", candidate).strip().lower(),
    }
    parenthetical_tokens = re.findall(r"\(([^()]+)\)", candidate)
    for token in parenthetical_tokens:
        cleaned = _clean_text(token)
        if not cleaned:
            continue
        variants.add(re.sub(r"\s+", " ", cleaned).strip().lower())
        variants.add(re.sub(r"\s+", " ", normalize_role_display_name(cleaned, None)).strip().lower())
    return {item for item in variants if item}


def _role_tokens(value: str) -> set[str]:
    text = _clean_text(value)
    if not text:
        return set()
    bracket_matches = re.findall(r"\[([^\]]+)\]", text)
    candidates = bracket_matches if bracket_matches else [text]
    tokens: set[str] = set()
    for candidate in candidates:
        cleaned = re.sub(r"\b(role|roles|in|allow|allowed|policy)\b", " ", candidate, flags=re.IGNORECASE)
        for part in re.split(r"[,;/|]+", cleaned):
            tokens.update(_canonical_role_variants(part))
    return tokens


def metric_definitions() -> dict[str, dict[str, Any]]:
    return {
        "core_interaction_guess_count": {
            "count_object": "当前案例中被标记为核心交互的 interaction rows",
            "count_rule": "凡任一核心交互仍需要 P3 自行补页面职责、元素、字段、服务、next-step、failure-route，计 1",
        },
        "operable_cross_page_flow_count": {
            "count_object": "当前案例中满足可从起点页面执行到下一页面且 handoff context 完整的跨页 flow",
            "minimum_conditions": [
                "存在 flow_id",
                "至少跨 2 个 page_id",
                "存在 next_page_id",
                "存在可满足的 transition_condition",
                "handoff context 不缺关键字段",
            ],
        },
        "core_surface_pass_count": {
            "count_object": "当前案例中被声明为核心页面的页面",
            "pass_conditions": [
                "blueprint 明确",
                "required regions 渲染语义明确",
                "至少 1 个核心 interaction 已绑定",
                "关键展示数据具备 read-side binding",
                "role / denied behavior 可判定",
            ],
        },
        "role_surface_alignment": {
            "count_object": "当前案例全部核心页面",
            "pass_conditions": [
                "allowed_roles",
                "visibility_rule",
                "rbac_policy",
                "denied_behavior / error_state",
                "四者不冲突",
            ],
        },
    }


def compute_surface_contract_metrics(ui_ia_contract: dict[str, Any]) -> dict[str, Any]:
    pages = _page_rows(ui_ia_contract)
    core_pages = [page for page in pages if _is_core_surface(page)] or pages
    page_ids = [_clean_text(page.get("page_id")) or _clean_text(page.get("route")) for page in core_pages]
    page_id_set = {page_id for page_id in page_ids if page_id}
    core_interaction_ids = [
        _clean_text(interaction.get("interaction_id"))
        for page in core_pages
        for interaction in _interaction_rows(page)
        if _clean_text(interaction.get("interaction_id"))
    ]

    guess_rows: list[dict[str, Any]] = []
    pass_page_ids: list[str] = []
    fail_rows: list[dict[str, Any]] = []
    aligned_surface_ids: list[str] = []
    misalignments: list[dict[str, Any]] = []
    status_summary = {"ready": 0, "blocked": 0, "review-bound": 0, "stale": 0}
    page_status_summary = {"ready": 0, "blocked": 0, "review-bound": 0, "stale": 0}
    cross_page_flows: list[dict[str, Any]] = []
    seen_flow_ids: set[str] = set()
    non_ready_contract_rows: list[dict[str, Any]] = []
    core_non_ready_contract_rows: list[dict[str, Any]] = []
    readiness_consistency_issues: list[dict[str, Any]] = []

    for page in pages:
        page_id = _clean_text(page.get("page_id")) or _clean_text(page.get("route"))
        is_core_surface = _is_core_surface(page)
        page_status_raw = _raw_readiness_status(page)
        page_status = page_status_raw or "ready"
        page_blocked_reason = _blocked_reason(page)
        page_status_summary[page_status] = page_status_summary.get(page_status, 0) + 1
        if page_status_raw and page_status not in VALID_READINESS_STATUSES:
            readiness_consistency_issues.append(
                {
                    "row_kind": "page",
                    "page_id": page_id,
                    "issue": "invalid_readiness_status",
                    "status": page_status,
                }
            )
        elif page_status in NON_READY_STATUSES:
            non_ready_contract_rows.append(
                {
                    "row_kind": "page",
                    "page_id": page_id,
                    "status": page_status,
                    "blocked_reason": page_blocked_reason,
                }
            )
            if is_core_surface:
                core_non_ready_contract_rows.append(
                    {
                        "row_kind": "page",
                        "page_id": page_id,
                        "status": page_status,
                        "blocked_reason": page_blocked_reason,
                    }
                )
            if not page_blocked_reason:
                readiness_consistency_issues.append(
                    {
                        "row_kind": "page",
                        "page_id": page_id,
                        "issue": "non_ready_without_blocked_reason",
                        "status": page_status,
                    }
                )
        elif page_blocked_reason:
            readiness_consistency_issues.append(
                {
                    "row_kind": "page",
                    "page_id": page_id,
                    "issue": "ready_with_blocked_reason",
                    "status": page_status,
                }
            )
        allowed_roles = {_clean_text(role).lower() for role in _clean_list(page.get("allowed_roles")) if _clean_text(role)}
        required_regions = _clean_list(page.get("required_regions"))
        interactions = _interaction_rows(page)
        page_denied_behavior = _clean_text(page.get("denied_behavior"))

        for interaction in interactions:
            interaction_status_raw = _raw_readiness_status(interaction)
            status = _interaction_status(interaction)
            interaction_id = _clean_text(interaction.get("interaction_id"))
            interaction_blocked_reason = _blocked_reason(interaction)
            status_summary[status] = status_summary.get(status, 0) + 1
            if interaction_status_raw and status not in VALID_READINESS_STATUSES:
                readiness_consistency_issues.append(
                    {
                        "row_kind": "interaction",
                        "page_id": page_id,
                        "interaction_id": interaction_id,
                        "issue": "invalid_readiness_status",
                        "status": status,
                    }
                )
            elif status in NON_READY_STATUSES:
                non_ready_contract_rows.append(
                    {
                        "row_kind": "interaction",
                        "page_id": page_id,
                        "interaction_id": interaction_id,
                        "status": status,
                        "blocked_reason": interaction_blocked_reason,
                    }
                )
                if is_core_surface:
                    core_non_ready_contract_rows.append(
                        {
                            "row_kind": "interaction",
                            "page_id": page_id,
                            "interaction_id": interaction_id,
                            "status": status,
                            "blocked_reason": interaction_blocked_reason,
                        }
                    )
                if not interaction_blocked_reason:
                    readiness_consistency_issues.append(
                        {
                            "row_kind": "interaction",
                            "page_id": page_id,
                            "interaction_id": interaction_id,
                            "issue": "non_ready_without_blocked_reason",
                            "status": status,
                        }
                    )
            elif interaction_blocked_reason:
                readiness_consistency_issues.append(
                    {
                        "row_kind": "interaction",
                        "page_id": page_id,
                        "interaction_id": interaction_id,
                        "issue": "ready_with_blocked_reason",
                        "status": status,
                    }
                )
            if not is_core_surface:
                continue
            missing_dimensions: list[str] = []
            for key in ("interaction_id", "region", "element_type", "interaction_pattern", "trigger_kind", "action_type"):
                if not _clean_text(interaction.get(key)):
                    missing_dimensions.append(key)
            for key in ("service_binding_id", "domain_service", "api_endpoint"):
                if not _clean_text(interaction.get(key)):
                    missing_dimensions.append(key)
            trigger_kind = _clean_text(interaction.get("trigger_kind")).lower()
            if trigger_kind in LIFECYCLE_TRIGGERS:
                if not _clean_text(interaction.get("display_field_set")) and not _clean_list(interaction.get("display_field_set")):
                    missing_dimensions.append("display_field_set")
                if not _clean_text(interaction.get("response_field_mapping")):
                    missing_dimensions.append("response_field_mapping")
            else:
                if not _clean_text(interaction.get("input_schema_ref")):
                    missing_dimensions.append("input_schema_ref")
                if not _clean_text(interaction.get("request_field_mapping")):
                    missing_dimensions.append("request_field_mapping")
                if not _clean_text(interaction.get("response_field_mapping")):
                    missing_dimensions.append("response_field_mapping")
            if _clean_text(interaction.get("next_page_id")) or _clean_text(interaction.get("next_route")):
                for key in ("flow_id", "step_id", "transition_condition", "failure_route"):
                    if not _clean_text(interaction.get(key)):
                        missing_dimensions.append(key)
                if not _clean_list(interaction.get("handoff_context_fields")):
                    missing_dimensions.append("handoff_context_fields")
            if missing_dimensions:
                guess_rows.append(
                    {
                        "page_id": page_id,
                        "interaction_id": interaction_id,
                        "missing_dimensions": sorted(set(missing_dimensions)),
                    }
                )

            flow_id = _clean_text(interaction.get("flow_id"))
            next_page_id = _clean_text(interaction.get("next_page_id"))
            transition_condition = _clean_text(interaction.get("transition_condition"))
            handoff_context_fields = _clean_list(interaction.get("handoff_context_fields"))
            if (
                flow_id
                and flow_id not in seen_flow_ids
                and next_page_id
                and next_page_id != page_id
                and next_page_id in page_id_set
                and transition_condition
                and handoff_context_fields
                and status == "ready"
            ):
                seen_flow_ids.add(flow_id)
                cross_page_flows.append(
                    {
                        "flow_id": flow_id,
                        "from_page_id": page_id,
                        "interaction_id": interaction_id,
                        "next_page_id": next_page_id,
                        "handoff_context_fields": handoff_context_fields,
                    }
                )

        has_bound_interaction = any(
            _clean_text(interaction.get("service_binding_id"))
            and _clean_text(interaction.get("domain_service"))
            and _clean_text(interaction.get("api_endpoint"))
            for interaction in interactions
        )
        has_read_side_binding = any(
            _clean_text(interaction.get("api_endpoint"))
            and (
                _clean_text(interaction.get("binding_mode")).lower() in {"read", "read_write"}
                or _clean_text(interaction.get("trigger_kind")).lower() in LIFECYCLE_TRIGGERS
            )
            for interaction in interactions
        )
        role_evidence = any(
            _clean_text(interaction.get("visibility_rule"))
            and _clean_text(interaction.get("rbac_policy"))
            and (_clean_text(interaction.get("error_state")) or _clean_text(interaction.get("failure_codes")))
            for interaction in interactions
        ) or bool(page_denied_behavior)
        if not is_core_surface:
            continue
        pass_reasons: list[str] = []
        if not _clean_text(page.get("page_blueprint_type")):
            pass_reasons.append("page_blueprint_type")
        if not required_regions:
            pass_reasons.append("required_regions")
        if not interactions:
            pass_reasons.append("compiled_interactions")
        if not has_bound_interaction:
            pass_reasons.append("bound_interaction")
        if not has_read_side_binding:
            pass_reasons.append("read_side_binding")
        if not allowed_roles or not role_evidence:
            pass_reasons.append("role_or_denied_evidence")
        if pass_reasons:
            fail_rows.append({"page_id": page_id, "missing_dimensions": pass_reasons})
        else:
            pass_page_ids.append(page_id)

        page_alignment_issues: list[str] = []
        if not allowed_roles:
            page_alignment_issues.append("allowed_roles_missing")
        page_has_role_alignment_signal = False
        for interaction in interactions:
            visibility_rule = _clean_text(interaction.get("visibility_rule"))
            rbac_policy = _clean_text(interaction.get("rbac_policy"))
            error_state = _clean_text(interaction.get("error_state"))
            failure_codes = _clean_text(interaction.get("failure_codes"))
            if not visibility_rule:
                page_alignment_issues.append(f"{_clean_text(interaction.get('interaction_id')) or 'interaction'}:visibility_rule_missing")
                continue
            if not rbac_policy:
                page_alignment_issues.append(f"{_clean_text(interaction.get('interaction_id')) or 'interaction'}:rbac_policy_missing")
                continue
            if not error_state and not failure_codes:
                page_alignment_issues.append(f"{_clean_text(interaction.get('interaction_id')) or 'interaction'}:denied_state_missing")
            visibility_roles = _role_tokens(visibility_rule)
            policy_roles = _role_tokens(rbac_policy)
            comparable_roles = visibility_roles or policy_roles
            if comparable_roles and allowed_roles and not (comparable_roles & allowed_roles):
                page_alignment_issues.append(
                    f"{_clean_text(interaction.get('interaction_id')) or 'interaction'}:role_mismatch"
                )
            else:
                page_has_role_alignment_signal = True
        if page_alignment_issues or not page_has_role_alignment_signal:
            misalignments.append(
                {
                    "page_id": page_id,
                    "issues": sorted(set(page_alignment_issues or ["role_alignment_signal_missing"])),
                }
            )
        else:
            aligned_surface_ids.append(page_id)

    role_surface_alignment = {
        "all_core_surfaces_aligned": len(aligned_surface_ids) == len(core_pages),
        "aligned_surface_count": len(aligned_surface_ids),
        "core_surface_count": len(core_pages),
        "aligned_surface_ids": aligned_surface_ids,
        "misaligned_surface_ids": [row["page_id"] for row in misalignments],
        "misalignments": misalignments,
    }

    return {
        "definitions": metric_definitions(),
        "core_scope_source": _core_scope_source(pages),
        "core_surface_count": len(core_pages),
        "core_page_ids": page_ids,
        "core_interaction_ids": core_interaction_ids,
        "core_interaction_count": sum(len(_interaction_rows(page)) for page in core_pages),
        "core_interaction_guess_count": len(guess_rows),
        "core_interaction_guess_rows": guess_rows,
        "operable_cross_page_flow_count": len(cross_page_flows),
        "operable_cross_page_flows": cross_page_flows,
        "core_surface_pass_count": len(pass_page_ids),
        "core_surface_pass_page_ids": pass_page_ids,
        "core_surface_failures": fail_rows,
        "role_surface_alignment": role_surface_alignment,
        "readiness_status_summary": status_summary,
        "page_readiness_status_summary": page_status_summary,
        "non_ready_contract_rows": non_ready_contract_rows,
        "core_non_ready_contract_rows": core_non_ready_contract_rows,
        "readiness_consistency_issues": readiness_consistency_issues,
    }


def evaluate_surface_contract_taxonomy(ui_ia_contract: dict[str, Any]) -> dict[str, Any]:
    metrics = compute_surface_contract_metrics(ui_ia_contract)
    core_surface_count = int(metrics.get("core_surface_count", 0) or 0)
    core_surface_pass_count = int(metrics.get("core_surface_pass_count", 0) or 0)
    core_interaction_guess_count = int(metrics.get("core_interaction_guess_count", 0) or 0)
    operable_cross_page_flow_count = int(metrics.get("operable_cross_page_flow_count", 0) or 0)
    role_surface_alignment = metrics.get("role_surface_alignment", {})
    non_ready_contract_rows = [
        row for row in metrics.get("non_ready_contract_rows", []) if isinstance(row, dict)
    ]
    core_non_ready_contract_rows = [
        row for row in metrics.get("core_non_ready_contract_rows", []) if isinstance(row, dict)
    ]
    readiness_consistency_issues = [
        row for row in metrics.get("readiness_consistency_issues", []) if isinstance(row, dict)
    ]
    flow_required = core_surface_count > 1
    checks = {
        "core_surface_present": core_surface_count > 0,
        "core_interaction_guess_gate": core_interaction_guess_count == 0,
        "operable_cross_page_flow_required": flow_required,
        "operable_cross_page_flow_gate": (not flow_required) or operable_cross_page_flow_count > 0,
        "core_surface_pass_gate": core_surface_count > 0 and core_surface_pass_count == core_surface_count,
        "role_surface_alignment_gate": bool(role_surface_alignment.get("all_core_surfaces_aligned")),
        "authority_status_gate": not core_non_ready_contract_rows and not readiness_consistency_issues,
    }
    failures: list[str] = []
    warnings: list[str] = []
    if not checks["core_surface_present"]:
        failures.append("core_surface_missing")
    if not checks["core_interaction_guess_gate"]:
        failures.append("core_interactions_require_guessing")
    if not checks["operable_cross_page_flow_gate"]:
        failures.append("operable_cross_page_flow_missing")
    if not checks["core_surface_pass_gate"]:
        failures.append("core_surface_contract_incomplete")
    if not checks["role_surface_alignment_gate"]:
        failures.append("role_surface_alignment_failed")
    if core_non_ready_contract_rows:
        failures.append("authority_status_not_ready")
    if readiness_consistency_issues:
        failures.append("authority_status_inconsistent")
    if non_ready_contract_rows and not core_non_ready_contract_rows:
        warnings.append("support_surface_non_ready_rows_explicit")
    if checks["core_surface_present"] and not flow_required:
        warnings.append("single_surface_case_cross_page_flow_not_required")
    return {
        "metrics": metrics,
        "checks": checks,
        "gate_pass": not failures,
        "failures": failures,
        "warnings": warnings,
    }
