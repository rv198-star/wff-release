#!/usr/bin/env python3
"""Build the default Phase-3 business behavior authoring plan."""

from __future__ import annotations

import re
from typing import Any


PLAN_KIND = "phase3-business-behavior-authoring-plan.v1"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value))
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def _slug(value: str, *, fallback: str = "default") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return normalized or fallback


def _camel_case(value: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", str(value)) if part]
    if not parts:
        return "Operation"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _operation_id(operation: dict[str, Any]) -> str:
    return str(
        operation.get("operation_id")
        or operation.get("operationId")
        or f"{operation.get('method', '')}-{operation.get('path', '')}"
    ).strip()


def _response_data(spec: dict[str, Any]) -> Any:
    response = spec.get("responseExample", {})
    return response.get("data", {}) if isinstance(response, dict) else {}


def _execution_mode(operation: dict[str, Any], spec: dict[str, Any], behavior_model: dict[str, Any]) -> str:
    explicit = str(
        behavior_model.get("execution_mode")
        or behavior_model.get("executionMode")
        or spec.get("executionMode")
        or spec.get("execution_mode")
        or ""
    ).strip()
    if explicit:
        return explicit
    operation_id = _operation_id(operation) or str(spec.get("operationId") or "").strip()
    method = str(operation.get("method") or spec.get("method") or "").upper()
    response_data = _response_data(spec)
    if operation_id.startswith(("Create", "Launch", "Export")):
        return "create"
    if operation_id.startswith("List") or (method == "GET" and isinstance(response_data, list)):
        return "list-read"
    if operation_id.startswith("Get") or method == "GET":
        return "detail-read"
    return "command"


def _failure_codes(spec: dict[str, Any], behavior_model: dict[str, Any]) -> list[str]:
    codes: list[Any] = []
    codes.extend(_as_list(behavior_model.get("error_codes")))
    for failure in _as_list(spec.get("failureCases")):
        if isinstance(failure, dict):
            codes.append(failure.get("error_code"))
    if "invalid_request" not in [str(code).strip() for code in codes]:
        codes.append("invalid_request")
    return _unique_strings(codes)


def _required_context(spec: dict[str, Any], behavior_model: dict[str, Any]) -> list[str]:
    fields = _as_list(spec.get("requestRequiredFields"))
    if not fields:
        fields = _as_list(behavior_model.get("required_context"))
    return _unique_strings(fields)


def _module_slug(operation: dict[str, Any], spec: dict[str, Any]) -> str:
    tag = str(operation.get("tag") or spec.get("tag") or "").strip()
    if tag:
        return _slug(tag)
    operation_id = _operation_id(operation)
    return _slug(operation_id, fallback="operation")


def _source_refs(operation_id: str, implementation_bindings: dict[str, Any]) -> list[str]:
    refs: list[Any] = []
    for row in _as_list(implementation_bindings.get("rows")):
        if not isinstance(row, dict):
            continue
        row_operation_id = str(row.get("operation_id") or row.get("operationId") or "").strip()
        haystack = " ".join(
            [
                row_operation_id,
                str(row.get("source_subject") or ""),
                " ".join(str(target) for target in _as_list(row.get("implementation_targets"))),
                " ".join(str(target) for target in _as_list(row.get("test_targets"))),
            ]
        ).lower()
        if row_operation_id != operation_id and operation_id.lower() not in haystack:
            continue
        refs.extend(
            [
                row.get("source_id"),
                *_as_list(row.get("source_ids")),
                *_as_list(row.get("upstream_trace_ids")),
                *_as_list(row.get("work_packages")),
            ]
        )
    return _unique_strings(refs)


def _response_fields(spec: dict[str, Any]) -> list[str]:
    data = _response_data(spec)
    if isinstance(data, list):
        first = data[0] if data and isinstance(data[0], dict) else {}
        return list(first.keys())
    if isinstance(data, dict):
        return list(data.keys())
    return []


def _behavior_intent(operation_id: str, spec: dict[str, Any], behavior_model: dict[str, Any]) -> str:
    return str(behavior_model.get("business_intent") or spec.get("purpose") or f"Execute {operation_id}").strip()


def _semantic_defaults(
    operation_id: str,
    module_slug: str,
    execution_mode: str,
    behavior_model: dict[str, Any],
) -> dict[str, Any]:
    semantics = behavior_model.get("operation_semantics") if isinstance(behavior_model.get("operation_semantics"), dict) else {}
    aggregate = str(semantics.get("aggregate") or _camel_case(module_slug)).strip()
    owner_service = str(semantics.get("owner_service") or f"{aggregate}Service").strip()
    event = _as_list(semantics.get("trigger_events"))
    if not event and execution_mode not in {"detail-read", "list-read"}:
        event = [f"{operation_id}Completed"]
    return {
        "owner_service": owner_service,
        "aggregate": aggregate,
        "state_set": _unique_strings(_as_list(semantics.get("state_set"))),
        "trigger_events": _unique_strings(event),
        "mutation_guard": str(semantics.get("mutation_guard") or behavior_model.get("invariants") or "").strip(),
        "readonly_dependencies": _unique_strings(_as_list(semantics.get("readonly_dependencies"))),
        "evidence_keys": _unique_strings(_as_list(semantics.get("evidence_keys"))),
    }


def _operation_plan(
    operation: dict[str, Any],
    *,
    operation_specs: dict[str, dict[str, Any]],
    behavior_card_models: dict[str, dict[str, Any]],
    implementation_bindings: dict[str, Any],
) -> dict[str, Any]:
    operation_id = _operation_id(operation)
    spec = operation_specs.get(operation_id, {})
    behavior_model = behavior_card_models.get(operation_id, {})
    execution_mode = _execution_mode(operation, spec, behavior_model)
    module_slug = _module_slug(operation, spec)
    is_read = execution_mode in {"detail-read", "list-read"}
    failure_codes = _failure_codes(spec, behavior_model)
    source_refs = _source_refs(operation_id, implementation_bindings)
    semantics = _semantic_defaults(operation_id, module_slug, execution_mode, behavior_model)
    response_fields = _response_fields(spec)
    required_context = _required_context(spec, behavior_model)
    invariant_text = str(behavior_model.get("invariants") or semantics.get("mutation_guard") or "").strip()

    fallback_reason = "" if source_refs or behavior_model else "source-backed-behavior-plan-incomplete"
    return {
        "operation_id": operation_id,
        "module_slug": module_slug,
        "execution_mode": execution_mode,
        "source_refs": source_refs,
        "behavior_intent": _behavior_intent(operation_id, spec, behavior_model),
        "required_context": required_context,
        "read_write_semantics": {
            "mode": execution_mode,
            "mutation": "no-mutation" if is_read else "durable-write",
            "read_only": is_read,
            "business_path": "read-projection" if is_read else "state-changing-flow",
        },
        "state_conflict_policy": {
            "state_transition": str(behavior_model.get("state_transition") or "").strip(),
            "error_codes": failure_codes,
            "requires_expected_version": "version_conflict" in failure_codes
            or any("version" in field.lower() for field in required_context + response_fields),
        },
        "repository_effect": {
            "decision_load": True,
            "invariant_persistence": not is_read,
            "read_back": True,
            "runtime_bridge": True,
            "durable_mutation": not is_read,
        },
        "audit_or_event_effect": {
            "required": not is_read,
            "effect": str(behavior_model.get("audit_effect") or ("no mutation audit event" if is_read else f"append {_snake_case(operation_id)} audit event")).strip(),
            "trigger_events": semantics["trigger_events"],
        },
        "semantic_owner": {
            "owner_service": semantics["owner_service"],
            "aggregate": semantics["aggregate"],
            "state_set": semantics["state_set"],
            "mutation_guard": semantics["mutation_guard"],
            "readonly_dependencies": semantics["readonly_dependencies"],
            "evidence_keys": _unique_strings([*semantics["evidence_keys"], *response_fields, "trace_id"]),
        },
        "response_mapping": {
            "fields": response_fields,
            "source": "responseExample.data" if response_fields else "runtime-result",
        },
        "unit_test_obligations": {
            "required_context": required_context,
            "failure_codes": failure_codes,
            "assert_repository_order": not is_read,
            "assert_no_mutation": is_read,
            "assert_business_fields": response_fields,
        },
        "fallback_reason": fallback_reason,
        "claim_ceiling": "source-backed default-mainline authoring plan; generated quality still requires runtime evidence and human Review",
        "invariants": invariant_text,
    }


def _action_card_projection_entry(
    operation: dict[str, Any],
    *,
    operation_specs: dict[str, dict[str, Any]],
    action_card_entry: dict[str, Any],
) -> dict[str, Any]:
    operation_id = _operation_id(operation)
    spec = operation_specs.get(operation_id, {})
    components = [item for item in _as_list(action_card_entry.get("components")) if isinstance(item, dict)]
    action_card_refs = _unique_strings([component.get("action_card_id") for component in components])
    acd_levels = _unique_strings([component.get("acd_level") for component in components])
    required_tests = _unique_strings(_as_list(action_card_entry.get("required_tests")))
    source_refs = _unique_strings(_as_list(action_card_entry.get("source_refs")))
    review_bound_items = _unique_strings(_as_list(action_card_entry.get("review_bound_items")))
    execution_mode = str(action_card_entry.get("execution_mode") or spec.get("executionMode") or spec.get("execution_mode") or "").strip()
    if not execution_mode:
        execution_mode = _execution_mode(operation, spec, {})
    response_fields = _response_fields(spec)
    required_context = _required_context(spec, {})
    failure_codes = _failure_codes(spec, {})
    is_read = execution_mode in {"detail-read", "list-read"}
    return {
        "operation_id": operation_id,
        "module_slug": _module_slug(operation, spec),
        "execution_mode": execution_mode,
        "source_refs": source_refs,
        "action_card_refs": action_card_refs,
        "acd_levels": acd_levels,
        "source_sufficiency_status": str(action_card_entry.get("source_sufficiency_status") or "review-bound"),
        "review_bound_items": review_bound_items,
        "required_context": required_context,
        "read_write_semantics": {
            "mode": execution_mode,
            "mutation": "no-mutation" if is_read else "durable-write",
            "read_only": is_read,
        },
        "response_mapping": {
            "fields": response_fields,
            "source": "responseExample.data" if response_fields else "runtime-result",
        },
        "unit_test_obligations": {
            "required_context": required_context,
            "required_tests": required_tests,
            "failure_codes": failure_codes,
            "assert_repository_order": not is_read,
            "assert_no_mutation": is_read,
            "assert_business_fields": response_fields,
        },
        "fallback_reason": "" if not review_bound_items else "action-card-execution-map-review-bound",
        "claim_ceiling": "action-card projection only; generated quality still requires runtime evidence and human Review",
    }


def build_business_behavior_authoring_plan(
    *,
    operations: list[dict[str, Any]],
    operation_specs: dict[str, dict[str, Any]],
    behavior_card_models: dict[str, dict[str, Any]],
    implementation_bindings: dict[str, Any],
    action_card_execution_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    map_operations = action_card_execution_map.get("operations") if isinstance(action_card_execution_map, dict) else None
    if isinstance(map_operations, dict):
        operation_plans = {
            _operation_id(operation): _action_card_projection_entry(
                operation,
                operation_specs=operation_specs,
                action_card_entry=map_operations.get(_operation_id(operation), {}),
            )
            for operation in operations
            if _operation_id(operation) and isinstance(map_operations.get(_operation_id(operation)), dict)
        }
        mode = "action-card-projection"
        agentic_boundary = "action-card authoring and execution mapping before service/repository/unit file write"
    else:
        operation_plans = {
            _operation_id(operation): _operation_plan(
                operation,
                operation_specs=operation_specs,
                behavior_card_models=behavior_card_models,
                implementation_bindings=implementation_bindings,
            )
            for operation in operations
            if _operation_id(operation)
        }
        mode = "default-p3-mainline"
        agentic_boundary = "business behavior authoring plan before service/repository/unit file write"
    return {
        "artifact_kind": PLAN_KIND,
        "mode": mode,
        "control_boundary": {
            "workflow": "phase order, context assembly, file placement, runtime evidence, claim ceiling",
            "agentic": agentic_boundary,
            "evidence": "focused tests, strict-runtime, human Review",
        },
        "operations": operation_plans,
        "summary": {
            "operation_count": len(operation_plans),
            "fallback_operation_count": sum(1 for item in operation_plans.values() if item.get("fallback_reason")),
        },
        "claim_ceiling": "authoring input only; not generated quality proof without strict-runtime and human Review",
    }
