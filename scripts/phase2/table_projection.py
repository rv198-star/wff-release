#!/usr/bin/env python3
"""Deterministic Phase-2 table and schema storage projection helpers."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from common.script_data_assets import load_script_json_asset
from phase2.projection_utils import to_snake, unique_preserve


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


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase2/data/table-design-templates.json",)


def _load_semantic_table_design_templates() -> dict[str, dict[str, object]]:
    loaded = load_script_json_asset(__file__, "table-design-templates.json")
    return {str(key): dict(value) for key, value in loaded.items() if isinstance(value, dict)}


SEMANTIC_TABLE_DESIGN_TEMPLATES = _load_semantic_table_design_templates()


def semantic_table_design_template(table_name: str) -> dict[str, object] | None:
    template = SEMANTIC_TABLE_DESIGN_TEMPLATES.get(table_name)
    return copy.deepcopy(template) if template is not None else None


def table_design_template(table_name: str) -> dict[str, object]:
    semantic_template = semantic_table_design_template(table_name)
    if semantic_template is not None:
        return semantic_template
    default_pk = "tenant_id" if table_name == "tenant" else f"{table_name}_id"
    default: dict[str, object] = {
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
