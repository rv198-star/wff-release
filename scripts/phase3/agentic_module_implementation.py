#!/usr/bin/env python3
"""Build in-memory Phase-3 Agentic module implementation briefs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


BRIEF_SET_KIND = "phase3-agentic-module-implementation-brief-set.v1"
BRIEF_KIND = "phase3-agentic-module-implementation-brief.v1"


def _listish(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _text(value)
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _slug(value: str, *, fallback: str = "default") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return normalized or fallback


def _words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [part for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def _upper_camel(value: str) -> str:
    words = _words(value)
    if not words:
        return "Module"
    return "".join(word[:1].upper() + word[1:].lower() for word in words)


def _operation_id(operation: dict[str, Any]) -> str:
    return _text(
        operation.get("operation_id")
        or operation.get("operationId")
        or f"{operation.get('method', '')}-{operation.get('path', '')}"
    )


def _module_slug(operation: dict[str, Any], action_card_entry: dict[str, Any], operation_id: str) -> str:
    tag = _text(operation.get("tag"))
    if tag:
        return _slug(tag)
    for component in _listish(action_card_entry.get("components")):
        if not isinstance(component, dict):
            continue
        hint = _text(component.get("target_path_hint"))
        match = re.search(r"modules/([^/]+)/", hint)
        if match:
            return _slug(match.group(1))
    return _slug(operation_id)


def _execution_mode(operation: dict[str, Any], spec: dict[str, Any]) -> str:
    explicit = _text(spec.get("executionMode") or spec.get("execution_mode") or operation.get("executionMode"))
    if explicit:
        return explicit
    operation_id = _operation_id(operation)
    method = _text(operation.get("method") or spec.get("method")).upper()
    response = spec.get("responseExample")
    data = response.get("data") if isinstance(response, dict) else None
    if operation_id.startswith("List") or (method == "GET" and isinstance(data, list)):
        return "list-read"
    if operation_id.startswith("Get") or method == "GET":
        return "detail-read"
    if operation_id.startswith("Create"):
        return "create"
    return "command"


def _response_fields(spec: dict[str, Any]) -> list[str]:
    response = spec.get("responseExample")
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}
    if not isinstance(data, dict):
        return []
    return [str(key) for key in data.keys()]


def _decision_for_operation(agentic_semantic_decisions: dict[str, Any] | None, operation_id: str) -> dict[str, Any]:
    if not isinstance(agentic_semantic_decisions, dict):
        return {}
    decisions = agentic_semantic_decisions.get("decisions")
    if not isinstance(decisions, dict):
        return {}
    decision = decisions.get(operation_id)
    return decision if isinstance(decision, dict) else {}


def _component_ids(action_card_entry: dict[str, Any]) -> list[str]:
    ids: list[Any] = []
    ids.extend(_listish(action_card_entry.get("action_card_refs")))
    ids.extend(_listish(action_card_entry.get("component_refs")))
    for component in _listish(action_card_entry.get("components")):
        if isinstance(component, dict):
            ids.append(component.get("component_id"))
            ids.append(component.get("action_card_id"))
    return _unique_strings(ids)


def _convention_lookup(
    project_implementation_conventions: dict[str, Any] | None,
    component_ids: list[str],
) -> dict[str, str]:
    if not isinstance(project_implementation_conventions, dict):
        return {}
    naming = project_implementation_conventions.get("naming_conventions")
    if not isinstance(naming, dict):
        return {}
    services = naming.get("domain_services") if isinstance(naming.get("domain_services"), dict) else {}
    aggregates = naming.get("aggregates") if isinstance(naming.get("aggregates"), dict) else {}
    result: dict[str, str] = {}
    for component_id in component_ids:
        owner = _text(services.get(component_id))
        aggregate = _text(aggregates.get(component_id))
        if owner and "owner_service" not in result:
            result["owner_service"] = owner
        if aggregate and "aggregate" not in result:
            result["aggregate"] = aggregate
    return result


def _decision_owner(decision: dict[str, Any]) -> str:
    semantic_owner = decision.get("semantic_owner") if isinstance(decision.get("semantic_owner"), dict) else {}
    return _text(semantic_owner.get("owner_service"))


def _decision_aggregate(decision: dict[str, Any]) -> str:
    aggregate = decision.get("aggregate_boundary") if isinstance(decision.get("aggregate_boundary"), dict) else {}
    return _text(aggregate.get("aggregate"))


def _decision_invariants(decision: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    for item in _listish(decision.get("domain_invariants")):
        if isinstance(item, dict):
            values.append(item.get("invariant"))
        else:
            values.append(item)
    return _unique_strings(values)


def _source_status(action_card_entry: dict[str, Any], decision: dict[str, Any]) -> str:
    missing = _listish(action_card_entry.get("review_bound_items"))
    sufficiency = _text(action_card_entry.get("source_sufficiency_status"))
    decision_context = decision.get("context_sufficiency") if isinstance(decision.get("context_sufficiency"), dict) else {}
    decision_status = _text(decision_context.get("status"))
    if missing or decision_status == "review-bound" or sufficiency in {"review-bound", "insufficient", "missing"}:
        return "review-bound"
    return "sufficient"


def _build_module_brief(
    module_slug: str,
    entries: list[dict[str, Any]],
    *,
    project_implementation_conventions: dict[str, Any] | None,
) -> dict[str, Any]:
    owner_candidates: list[Any] = []
    aggregate_candidates: list[Any] = []
    invariant_candidates: list[Any] = []
    review_bound_gaps: list[Any] = []
    write_operations: list[str] = []
    read_operations: list[str] = []
    operation_test_intents: dict[str, str] = {}
    source_refs: list[Any] = []
    required_tests: list[Any] = []
    component_ids: list[Any] = []
    operation_group_rows: list[dict[str, Any]] = []

    for entry in entries:
        operation = entry["operation"]
        operation_id = entry["operation_id"]
        spec = entry["spec"]
        decision = entry["decision"]
        action_card_entry = entry["action_card_entry"]
        execution_mode = entry["execution_mode"]
        if execution_mode in {"detail-read", "list-read"}:
            read_operations.append(operation_id)
        else:
            write_operations.append(operation_id)
        component_ids.extend(entry["component_ids"])
        convention = _convention_lookup(project_implementation_conventions, entry["component_ids"])
        owner_candidates.extend([convention.get("owner_service"), _decision_owner(decision)])
        aggregate_candidates.extend([convention.get("aggregate"), _decision_aggregate(decision)])
        invariant_candidates.extend(_decision_invariants(decision))
        review_bound_gaps.extend(_listish(action_card_entry.get("review_bound_items")))
        decision_context = decision.get("context_sufficiency") if isinstance(decision.get("context_sufficiency"), dict) else {}
        review_bound_gaps.extend(_listish(decision_context.get("missing_truth")))
        source_refs.extend(_listish(action_card_entry.get("source_refs")))
        required_tests.extend(_listish(action_card_entry.get("required_tests")))
        response_fields = _response_fields(spec)
        if execution_mode in {"detail-read", "list-read"}:
            operation_test_intents[operation_id] = (
                f"prove {operation_id} uses read projection without durable mutation"
            )
        else:
            fields = _unique_strings(_listish(spec.get("requestRequiredFields")))
            field_note = f" after validating {fields[0]}" if fields else ""
            operation_test_intents[operation_id] = f"prove {operation_id} persists invariant-backed state{field_note}"
        operation_group_rows.append(
            {
                "operation_id": operation_id,
                "method": _text(operation.get("method")),
                "path": _text(operation.get("path")),
                "execution_mode": execution_mode,
                "response_fields": response_fields,
                "source_refs": _unique_strings(_listish(action_card_entry.get("source_refs"))),
            }
        )

    owner_service = _unique_strings(owner_candidates)[0] if _unique_strings(owner_candidates) else f"{_upper_camel(module_slug)}Service"
    aggregate = _unique_strings(aggregate_candidates)[0] if _unique_strings(aggregate_candidates) else _upper_camel(module_slug)
    invariants = _unique_strings(invariant_candidates) or [
        f"{aggregate} implementation must preserve source-backed behavior and keep missing truth review-bound."
    ]
    status = "review-bound" if _unique_strings(review_bound_gaps) else "sufficient"
    code_conventions = (
        project_implementation_conventions.get("code_conventions")
        if isinstance(project_implementation_conventions, dict)
        and isinstance(project_implementation_conventions.get("code_conventions"), dict)
        else {}
    )
    design_conventions = (
        project_implementation_conventions.get("design_conventions")
        if isinstance(project_implementation_conventions, dict)
        and isinstance(project_implementation_conventions.get("design_conventions"), dict)
        else {}
    )
    return {
        "artifact_kind": BRIEF_KIND,
        "module_slug": module_slug,
        "module_purpose": f"Implement {aggregate} behaviors through source-backed service, repository, and unit-test strategy.",
        "context_sufficiency": {
            "status": status,
            "source_refs": _unique_strings(source_refs),
            "required_tests": _unique_strings(required_tests),
            "component_refs": _unique_strings(component_ids),
        },
        "operation_groups": {
            "operations": operation_group_rows,
            "read_operations": read_operations,
            "write_operations": write_operations,
        },
        "aggregate_invariant_model": {
            "aggregate": aggregate,
            "invariants": invariants,
        },
        "service_flow_strategy": {
            "owner_service": owner_service,
            "strategy": _text(code_conventions.get("service_boundary"))
            or "Service owns orchestration, invariant checks, failure mapping, and transaction posture.",
            "write_flow": _text(design_conventions.get("write_path"))
            or "Command operations make invariant and value-rule checks explicit before persistence.",
            "read_flow": _text(design_conventions.get("read_path"))
            or "Read/list/detail operations preserve no-mutation posture.",
        },
        "repository_effect_strategy": {
            "aggregate": aggregate,
            "strategy": _text(code_conventions.get("repository_boundary"))
            or "Repository owns persistence effects, read/write separation, and runtime bridge mapping.",
            "write_operations": write_operations,
            "read_operations": read_operations,
            "durable_mutation_required": bool(write_operations),
        },
        "transaction_audit_auth_error_posture": {
            "transaction": "write operations require bounded transaction/read-back posture; read operations must not mutate",
            "audit": "write operations append source-backed audit/event effect; read operations keep no-mutation audit posture",
            "auth": "preserve auth/tenant context from runtime payload before repository effect",
            "error": "map validation, authorization, not-found, conflict, and dependency failures to explicit business errors",
        },
        "unit_test_strategy": {
            "module_test_intent": f"Prove {module_slug} service/repository behavior follows action-card and semantic decisions.",
            "operation_test_intents": operation_test_intents,
        },
        "renderer_notes": {
            "renderer_role": "mechanical-mapping-only",
            "allowed_script_work": ["syntax", "imports", "path placement", "trace comments", "runtime harness wiring"],
            "forbidden_script_work": ["business truth generation", "module strategy decision", "quality gate as content author"],
        },
        "review_bound_gaps": _unique_strings(review_bound_gaps),
        "claim_ceiling": "module implementation brief requires generated code/test/runtime evidence",
    }


def build_module_implementation_briefs(
    *,
    operations: list[dict[str, Any]],
    rich_context: dict[str, Any] | None,
    operation_specs: dict[str, dict[str, Any]] | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    project_implementation_conventions: dict[str, Any] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    del output_root
    rich_operations = rich_context.get("operations") if isinstance(rich_context, dict) and isinstance(rich_context.get("operations"), dict) else {}
    specs = operation_specs or {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    review_bound_operation_count = 0
    for operation in operations:
        operation_id = _operation_id(operation)
        if not operation_id:
            continue
        spec = specs.get(operation_id, {})
        action_card_entry = rich_operations.get(operation_id, {}) if isinstance(rich_operations.get(operation_id, {}), dict) else {}
        module_slug = _module_slug(operation, action_card_entry, operation_id)
        decision = _decision_for_operation(agentic_semantic_decisions, operation_id)
        execution_mode = _execution_mode(operation, spec)
        if _source_status(action_card_entry, decision) == "review-bound":
            review_bound_operation_count += 1
        grouped.setdefault(module_slug, []).append(
            {
                "operation": operation,
                "operation_id": operation_id,
                "spec": spec,
                "action_card_entry": action_card_entry,
                "decision": decision,
                "execution_mode": execution_mode,
                "component_ids": _component_ids(action_card_entry),
            }
        )

    modules = {
        module_slug: _build_module_brief(
            module_slug,
            entries,
            project_implementation_conventions=project_implementation_conventions,
        )
        for module_slug, entries in grouped.items()
    }
    return {
        "artifact_kind": BRIEF_SET_KIND,
        "mode": "in-memory-before-service-repository-unit-file-write",
        "modules": modules,
        "summary": {
            "module_count": len(modules),
            "operation_count": sum(len(entries) for entries in grouped.values()),
            "review_bound_operation_count": review_bound_operation_count,
            "persisted_default_heavy_artifact_count": 0,
        },
        "claim_ceiling": "module implementation briefs guide rendering; strict-runtime and human Review decide quality claims",
    }
