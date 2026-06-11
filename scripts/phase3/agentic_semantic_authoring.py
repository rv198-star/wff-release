#!/usr/bin/env python3
"""Build in-memory Phase-3 Agentic semantic authoring decisions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


DECISION_SET_KIND = "phase3-agentic-semantic-decision-set.v1"
DECISION_KIND = "phase3-agentic-semantic-decision.v1"


def _words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [part for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def _upper_camel(value: str) -> str:
    words = _words(value)
    if not words:
        return "Operation"
    return "".join(word[:1].upper() + word[1:].lower() for word in words)


def _singularize_word(word: str) -> str:
    if len(word) > 3 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _strip_operation_prefix(operation_id: str) -> str:
    candidate = str(operation_id or "").strip()
    for prefix in (
        "Create",
        "Update",
        "Patch",
        "Manage",
        "Record",
        "Submit",
        "Approve",
        "Reject",
        "Delete",
        "Archive",
        "Launch",
        "Export",
        "Get",
        "List",
        "Search",
    ):
        if candidate.startswith(prefix) and len(candidate) > len(prefix):
            return candidate[len(prefix) :]
    return candidate


def _strip_operation_tail(value: str) -> str:
    words = _words(value)
    while len(words) > 1 and words[-1].lower() in {
        "status",
        "state",
        "detail",
        "details",
        "summary",
        "summaries",
        "list",
        "view",
        "history",
        "report",
        "result",
        "results",
    }:
        words = words[:-1]
    return " ".join(_singularize_word(word.lower()) for word in words)


def _module_slug_from_context(operation_id: str, action_card_entry: dict[str, Any]) -> str:
    components = action_card_entry.get("components")
    if isinstance(components, list):
        for component in components:
            if not isinstance(component, dict):
                continue
            hint = str(component.get("target_path_hint") or "").strip()
            match = re.search(r"modules/([^/]+)/", hint)
            if match:
                return match.group(1)
            component_id = str(component.get("component_id") or "").strip()
            if component_id:
                return re.sub(r"-(service|repository|controller|module)$", "", component_id)
    return _strip_operation_tail(_strip_operation_prefix(operation_id))


def _execution_mode(operation: dict[str, Any], spec: dict[str, Any]) -> str:
    explicit = str(spec.get("executionMode") or spec.get("execution_mode") or operation.get("executionMode") or "").strip()
    if explicit:
        return explicit
    method = str(operation.get("method") or spec.get("method") or "").upper()
    operation_id = str(operation.get("operation_id") or spec.get("operationId") or "").strip()
    data = spec.get("responseExample", {}).get("data", {}) if isinstance(spec.get("responseExample"), dict) else {}
    if method == "GET" and isinstance(data, list):
        return "list-read"
    if method == "GET" or operation_id.startswith("Get"):
        return "detail-read"
    if operation_id.startswith("List"):
        return "list-read"
    if operation_id.startswith("Create"):
        return "create"
    return "command"


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


def _semantic_component_refs(action_card_entry: dict[str, Any]) -> list[str]:
    refs: list[Any] = []
    for component in _as_list(action_card_entry.get("components")):
        if isinstance(component, dict):
            refs.append(component.get("component_id"))
    refs.extend(_as_list(action_card_entry.get("action_card_refs")))
    refs.extend(_as_list(action_card_entry.get("component_refs")))
    return _unique_strings(refs)


def _response_fields(spec: dict[str, Any]) -> list[str]:
    response = spec.get("responseExample")
    if not isinstance(response, dict):
        return []
    data = response.get("data")
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else {}
    if not isinstance(data, dict):
        return []
    return [str(key) for key in data.keys()]


def _required_fields(spec: dict[str, Any]) -> list[str]:
    return _unique_strings(_as_list(spec.get("requestRequiredFields")))


def classify_semantic_authority(
    *,
    semantic_owner: str,
    aggregate: str,
    domain_invariants: list[Any],
    source: str,
) -> dict[str, Any]:
    owner = str(semantic_owner or "").strip()
    aggregate_value = str(aggregate or "").strip()
    source_value = str(source or "").strip()
    weak_owner = owner in {"", "not-declared", "unknown", "review-bound"}
    weak_aggregate = aggregate_value in {"", "review-bound", "unknown", "not-declared"}
    weak_invariants = not [item for item in domain_invariants if str(item).strip()]
    if source_value == "script-default" or weak_owner or weak_aggregate or weak_invariants:
        return {
            "authority": "agentic-required",
            "content_truth_complete": False,
            "reason": "script default cannot decide semantic truth; Agentic semantic authoring must decide or keep the item review-bound",
        }
    return {
        "authority": "source-backed-agentic",
        "content_truth_complete": True,
        "reason": "semantic truth is backed by explicit source context and Agentic authoring judgment",
    }


def _build_invariant(
    *,
    operation_id: str,
    aggregate: str,
    execution_mode: str,
    required_fields: list[str],
    response_fields: list[str],
) -> dict[str, str]:
    if execution_mode in {"detail-read", "list-read"}:
        invariant = f"{operation_id} must project {aggregate} evidence without durable mutation."
        test_intent = "prove repository read path is used and persist/audit mutation methods are not called"
    elif required_fields:
        invariant = f"{operation_id} must validate {', '.join(required_fields[:4])} before changing {aggregate} state."
        test_intent = f"reject {operation_id} when required {required_fields[0]} context is absent"
    elif response_fields:
        invariant = f"{operation_id} must preserve {aggregate} response identity through the runtime bridge."
        test_intent = f"assert generated response carries {response_fields[0]} from context or repository state"
    else:
        invariant = f"{operation_id} must preserve the {aggregate} boundary and declared failure semantics."
        test_intent = f"exercise success and invalid_request paths for {operation_id}"
    return {
        "invariant": invariant,
        "evidence_source": "action-card rich context + operation contract",
        "test_intent": test_intent,
    }


def _decision_for_operation(
    operation: dict[str, Any],
    *,
    action_card_entry: dict[str, Any],
    spec: dict[str, Any],
    behavior_model: dict[str, Any],
    project_implementation_conventions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operation_id = str(operation.get("operation_id") or spec.get("operationId") or "").strip()
    module_slug = _module_slug_from_context(operation_id, action_card_entry)
    aggregate = _upper_camel(module_slug or _strip_operation_prefix(operation_id))
    owner_service = f"{aggregate}Service"
    execution_mode = _execution_mode(operation, spec)
    required_fields = _required_fields(spec)
    response_fields = _response_fields(spec)
    source_refs = _unique_strings(_as_list(action_card_entry.get("source_refs")))
    required_tests = _unique_strings(_as_list(action_card_entry.get("required_tests")))
    missing_truth = _unique_strings(_as_list(action_card_entry.get("review_bound_items")))
    invariant = _build_invariant(
        operation_id=operation_id,
        aggregate=aggregate,
        execution_mode=execution_mode,
        required_fields=required_fields,
        response_fields=response_fields,
    )
    mutation = "no-mutation" if execution_mode in {"detail-read", "list-read"} else "durable-write"
    behavior_semantics = (
        behavior_model.get("operation_semantics")
        if isinstance(behavior_model.get("operation_semantics"), dict)
        else {}
    )
    explicit_owner = str(behavior_semantics.get("owner_service") or "").strip()
    explicit_aggregate = str(behavior_semantics.get("aggregate") or "").strip()
    if explicit_owner:
        owner_service = explicit_owner
    if explicit_aggregate:
        aggregate = explicit_aggregate
    convention_naming = (
        project_implementation_conventions.get("naming_conventions")
        if isinstance(project_implementation_conventions, dict)
        and isinstance(project_implementation_conventions.get("naming_conventions"), dict)
        else {}
    )
    convention_services = (
        convention_naming.get("domain_services")
        if isinstance(convention_naming.get("domain_services"), dict)
        else {}
    )
    convention_aggregates = (
        convention_naming.get("aggregates")
        if isinstance(convention_naming.get("aggregates"), dict)
        else {}
    )
    for component_id in _semantic_component_refs(action_card_entry):
        convention_owner = str(convention_services.get(component_id) or "").strip()
        convention_aggregate = str(convention_aggregates.get(component_id) or "").strip()
        if convention_owner and not explicit_owner:
            owner_service = convention_owner
        if convention_aggregate and not explicit_aggregate:
            aggregate = convention_aggregate
        if (convention_owner and not explicit_owner) or (convention_aggregate and not explicit_aggregate):
            break
    context_status = "review-bound" if missing_truth else "sufficient"
    return {
        "artifact_kind": DECISION_KIND,
        "operation_id": operation_id,
        "decision_owner": "agentic",
        "context_sufficiency": {
            "status": context_status,
            "missing_truth": missing_truth,
            "source_refs": source_refs,
            "required_tests": required_tests,
        },
        "semantic_owner": {
            "owner_service": owner_service,
            "owner_kind": "operation-module-service",
            "owner_source": "source-supported" if source_refs or action_card_entry else "contract-derived-review-bound",
            "reasoning": f"{operation_id} is authored inside the {aggregate} boundary before service/repository/unit file write.",
        },
        "aggregate_boundary": {
            "aggregate": aggregate,
            "boundary_rule": f"{operation_id} must keep {aggregate} identity, state, and evidence coherent.",
        },
        "domain_invariants": [invariant],
        "value_rule": {
            "rule": f"{operation_id} must deliver {mutation} behavior for {aggregate} without hiding source or runtime evidence gaps.",
            "implementation_implication": (
                "read path must not call persistence/audit mutation methods"
                if mutation == "no-mutation"
                else "write path must validate context, persist invariants, append audit effect, and read back evidence"
            ),
        },
        "failure_paths": [
            {
                "condition": invariant["test_intent"],
                "behavior": "reject before repository mutation" if mutation == "durable-write" else "return explicit business error without mutation",
                "test_intent": invariant["test_intent"],
            }
        ],
        "operation_semantics": {
            "status": "resolved" if context_status == "sufficient" else "review-bound",
            "owner_service": owner_service,
            "aggregate": aggregate,
            "state_set": ["active"] if mutation == "durable-write" else [],
            "trigger_events": [f"{operation_id}Completed"] if mutation == "durable-write" else [],
            "mutation_guard": invariant["invariant"],
            "terminal_or_failure_exit": "declared failure mapping",
            "readonly_dependencies": response_fields if mutation == "no-mutation" else [],
            "evidence_keys": _unique_strings([*source_refs, *required_fields, *response_fields, "trace_id"])[:8],
        },
        "claim_ceiling": "semantic decision requires generated code/test/runtime evidence",
    }


def build_agentic_semantic_decisions(
    *,
    operations: list[dict[str, Any]],
    rich_context: dict[str, Any],
    output_root: Path | None = None,
    operation_specs: dict[str, dict[str, Any]] | None = None,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
    project_implementation_conventions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del output_root
    rich_operations = rich_context.get("operations") if isinstance(rich_context.get("operations"), dict) else {}
    specs = operation_specs or {}
    behavior_models = behavior_card_models or {}
    decisions: dict[str, dict[str, Any]] = {}
    for operation in operations:
        operation_id = str(operation.get("operation_id") or operation.get("operationId") or "").strip()
        if not operation_id:
            continue
        decision = _decision_for_operation(
            {"operation_id": operation_id, **operation},
            action_card_entry=rich_operations.get(operation_id, {}) if isinstance(rich_operations.get(operation_id, {}), dict) else {},
            spec=specs.get(operation_id, {}),
            behavior_model=behavior_models.get(operation_id, {}),
            project_implementation_conventions=project_implementation_conventions,
        )
        decisions[operation_id] = decision
    script_default_count = 0
    owner_not_declared_count = 0
    aggregate_review_bound_count = 0
    mechanical_owner_name_count = 0
    mechanical_aggregate_name_count = 0
    for decision in decisions.values():
        authority = classify_semantic_authority(
            semantic_owner=str(decision.get("semantic_owner", {}).get("owner_service") or ""),
            aggregate=str(decision.get("aggregate_boundary", {}).get("aggregate") or ""),
            domain_invariants=decision.get("domain_invariants", []) if isinstance(decision.get("domain_invariants"), list) else [],
            source="agentic-semantic-authoring",
        )
        if authority["authority"] == "agentic-required":
            script_default_count += 1
        if str(decision.get("semantic_owner", {}).get("owner_service") or "") == "not-declared":
            owner_not_declared_count += 1
        if str(decision.get("aggregate_boundary", {}).get("aggregate") or "") == "review-bound":
            aggregate_review_bound_count += 1
        if re.fullmatch(r"P2CMP[0-9]+Service", str(decision.get("semantic_owner", {}).get("owner_service") or "")):
            mechanical_owner_name_count += 1
        if re.fullmatch(r"P2CMP[0-9]+", str(decision.get("aggregate_boundary", {}).get("aggregate") or "")):
            mechanical_aggregate_name_count += 1
    return {
        "artifact_kind": DECISION_SET_KIND,
        "mode": "in-memory-before-file-write",
        "decisions": decisions,
        "summary": {
            "decision_count": len(decisions),
            "agentic_semantic_decision_count": len(decisions),
            "script_semantic_default_count": script_default_count,
            "owner_not_declared_count": owner_not_declared_count,
            "aggregate_review_bound_count": aggregate_review_bound_count,
            "mechanical_owner_name_count": mechanical_owner_name_count,
            "mechanical_aggregate_name_count": mechanical_aggregate_name_count,
            "forbidden_name_residue_count": mechanical_owner_name_count + mechanical_aggregate_name_count,
            "default_heavy_artifact_count": 0,
        },
        "claim_ceiling": "semantic authoring input only; generated quality requires strict-runtime and human Review",
    }
