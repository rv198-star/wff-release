#!/usr/bin/env python3
"""Shared P2/P3 operation risk tiering and source obligations."""

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

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
LOW_RISK_EVIDENCE = {
    "deterministic_read",
    "no_core_scenario",
    "no_review_bound_trace",
    "no_side_effects",
    "no_sensitive_boundary",
    "low_contract_drift_cost",
}
ALL_SOURCE_TYPES = ["P2-CTR", "P2-FLOW", "P2-SEQ", "P2-STATE", "P2-RP"]
BUSINESS_VALUE_WEIGHTS = {"BV0", "BV1", "BV2", "BV3"}
IMPLEMENTATION_COMPLEXITIES = {"IC0", "IC1", "IC2", "IC3"}
ACD_LEVELS = {"ACD-0", "ACD-1", "ACD-2", "ACD-3"}


def normalize_business_value_weight(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in BUSINESS_VALUE_WEIGHTS else "review-bound"


def normalize_implementation_complexity(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in IMPLEMENTATION_COMPLEXITIES else "review-bound"


def normalize_acd_level(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in ACD_LEVELS else "review-bound"


def derive_acd_level(
    business_value_weight: Any,
    engineering_risk_tier: Any,
    implementation_complexity: Any,
    triggers: list[str] | None = None,
) -> dict[str, Any]:
    value = normalize_business_value_weight(business_value_weight)
    risk = str(engineering_risk_tier or "").strip().upper()
    complexity = normalize_implementation_complexity(implementation_complexity)
    trigger_set = {str(item).strip() for item in (triggers or []) if str(item).strip()}
    acd_triggers: list[str] = []

    high_risk = risk.startswith("HR-")
    medium_risk = risk.startswith("MR-")
    if value == "review-bound" or complexity == "review-bound" or not risk:
        acd_triggers.append("review_bound_depth_input")
        return {"acd_level": "review-bound", "acd_triggers": acd_triggers}
    if value == "BV3" and (high_risk or "over_broad_component" in trigger_set or "split_required" in trigger_set):
        acd_triggers.append("critical_value_with_high_risk")
        if "over_broad_component" in trigger_set or "split_required" in trigger_set:
            acd_triggers.append("over_broad_component")
        return {"acd_level": "ACD-3", "acd_triggers": acd_triggers}
    if value == "BV3" and complexity in {"IC2", "IC3"}:
        acd_triggers.append("critical_value_with_complexity")
        return {"acd_level": "ACD-3", "acd_triggers": acd_triggers}
    if high_risk or value in {"BV2", "BV3"} or complexity in {"IC2", "IC3"}:
        if high_risk:
            acd_triggers.append("high_engineering_risk")
        if value in {"BV2", "BV3"}:
            acd_triggers.append("high_business_value")
        if complexity in {"IC2", "IC3"}:
            acd_triggers.append("high_implementation_complexity")
        return {"acd_level": "ACD-2", "acd_triggers": acd_triggers}
    if medium_risk or value == "BV1" or complexity == "IC1":
        if medium_risk:
            acd_triggers.append("moderate_engineering_risk")
        if value == "BV1":
            acd_triggers.append("moderate_business_value")
        if complexity == "IC1":
            acd_triggers.append("moderate_implementation_complexity")
        return {"acd_level": "ACD-1", "acd_triggers": acd_triggers}
    acd_triggers.append("low_value_low_risk_low_complexity")
    return {"acd_level": "ACD-0", "acd_triggers": acd_triggers}


def compare_p2_p3_acd(p2_row: dict[str, Any] | None, recomputed: dict[str, Any]) -> dict[str, Any]:
    if not p2_row:
        return {
            "status": "p2_acd_row_missing",
            "effective_acd_level": "review-bound",
            "p3_recomputed_acd_level": normalize_acd_level(recomputed.get("acd_level")),
        }
    p2_level = normalize_acd_level(p2_row.get("acd_level"))
    recomputed_level = normalize_acd_level(recomputed.get("acd_level"))
    status = "aligned" if p2_level == recomputed_level else "acd_level_mismatch"
    return {
        "status": status,
        "effective_acd_level": p2_level,
        "p2_acd_level": p2_level,
        "p3_recomputed_acd_level": recomputed_level,
    }


def _tokens(operation: dict[str, Any]) -> str:
    fields = ["operation_id", "operationId", "summary", "description", "purpose", "notes", "path"]
    return " ".join(str(operation.get(field, "")) for field in fields).lower()


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def classify_operation(operation: dict[str, Any]) -> dict[str, Any]:
    method = str(operation.get("method", "")).upper()
    text = _tokens(operation)
    operation_id = str(operation.get("operation_id") or operation.get("operationId") or "").strip()
    persistence_effects = _list(operation.get("persistence_effects"))
    upstream_trace_ids = _list(operation.get("upstream_trace_ids"))
    low_risk_evidence = set(_list(operation.get("low_risk_evidence")))
    triggers: list[str] = []

    mutates = method in WRITE_METHODS or bool(persistence_effects) or any(
        token in text
        for token in (
            "create",
            "update",
            "delete",
            "archive",
            "submit",
            "confirm",
            "complete",
            "record",
            "export",
            "retry",
            "replay",
            "schedule",
            "manage",
        )
    )
    boundary = any(
        token in text
        for token in (
            "tenant",
            "permission",
            "identity",
            "role",
            "policy",
            "audit",
            "compliance",
            "billing",
            "approval",
            "evidence",
            "pii",
            "sensitive",
        )
    )
    orchestration = any(
        token in text
        for token in (
            "queue",
            "event",
            "async",
            "callback",
            "webhook",
            "scheduler",
            "batch",
            "external",
            "idempot",
            "replay",
            "retry",
            "concurr",
            "version",
            "cache",
        )
    )
    lifecycle = any(
        token in text
        for token in ("status", "state", "lifecycle", "version", "archive", "complete", "confirm", "submit")
    )
    core_or_review = any(
        trace.startswith("P1-UC-") or trace.startswith("P2-RT-") or trace.startswith("P2-RP-")
        for trace in upstream_trace_ids
    )

    if mutates:
        triggers.append("mutates_durable_state")
    if boundary:
        triggers.append("sensitive_boundary")
    if orchestration:
        triggers.append("orchestration_or_ordering")
    if lifecycle:
        triggers.append("lifecycle_or_state_transition")
    if core_or_review:
        triggers.append("core_or_review_bound_trace")

    required = ["P2-CTR"]
    tier = "MR-READ-SENSITIVE"
    requires_behavior_card = True

    if orchestration:
        tier = "HR-ORCHESTRATION"
        required.extend(["P2-FLOW", "P2-SEQ"])
        if lifecycle:
            required.append("P2-STATE")
        if any(token in text for token in ("replay", "retry", "handoff")):
            required.append("P2-RP")
    elif mutates:
        tier = "HR-MUTATION"
        required.append("P2-FLOW")
        if lifecycle or method == "PATCH":
            required.append("P2-STATE")
        if boundary or "audit" in text or "event" in text:
            required.append("P2-SEQ")
    elif boundary and method != "GET":
        tier = "HR-BOUNDARY"
        required.append("P2-FLOW")
        if orchestration:
            required.append("P2-SEQ")
        if lifecycle:
            required.append("P2-STATE")
    elif boundary:
        tier = "MR-READ-SENSITIVE"
        required.append("P2-FLOW")
    elif method == "GET" and LOW_RISK_EVIDENCE.issubset(low_risk_evidence):
        tier = "LR-SIMPLE-READ"
        requires_behavior_card = False
    else:
        if not triggers:
            triggers.append("uncertain_read_default_medium")
        if method == "GET":
            required.append("P2-FLOW")

    required = list(dict.fromkeys(required))
    not_required = [item for item in ALL_SOURCE_TYPES if item not in required]
    return {
        "operation_id": operation_id,
        "risk_tier": tier,
        "risk_triggers": triggers,
        "required_source_types": required,
        "not_required_source_types": not_required,
        "requires_behavior_card": requires_behavior_card,
        "classification_rationale": "; ".join(triggers) or "explicit low-risk evidence",
    }


def compare_p2_p3_risk(p2_row: dict[str, Any] | None, recomputed: dict[str, Any]) -> dict[str, Any]:
    if not p2_row:
        return {
            "status": "p2_operation_risk_row_missing",
            "effective_risk_tier": "review-bound",
            "effective_required_source_types": recomputed.get("required_source_types", []),
        }
    p2_tier = str(p2_row.get("risk_tier", "")).strip()
    recomputed_tier = str(recomputed.get("risk_tier", "")).strip()
    status = "aligned" if p2_tier == recomputed_tier else "risk_tier_mismatch"
    return {
        "status": status,
        "effective_risk_tier": p2_tier,
        "effective_required_source_types": list(p2_row.get("required_source_types", [])),
        "p2_risk_tier": p2_tier,
        "p3_recomputed_risk_tier": recomputed_tier,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify operation risk and source obligations")
    parser.add_argument("operation_json")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = classify_operation(json.loads(Path(args.operation_json).read_text(encoding="utf-8")))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
