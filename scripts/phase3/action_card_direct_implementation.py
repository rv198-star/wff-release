"""Build the in-memory Phase-3 Action Card direct implementation driver."""

from __future__ import annotations

import re
from typing import Any


DRIVER_KIND = "phase3-action-card-direct-implementation-driver.v1"
LEADING_OPERATION_VERBS = {
    "Create",
    "Update",
    "Manage",
    "Start",
    "Complete",
    "Record",
    "List",
    "Get",
    "Search",
    "Read",
    "Delete",
    "Approve",
    "Reject",
    "Submit",
}
TRAILING_OPERATION_DESCRIPTORS = {"Status", "State", "Detail", "Details"}
EVENT_VERB_SUFFIXES = {
    "Create": "Created",
    "Start": "Started",
    "Complete": "Completed",
    "Update": "Updated",
    "Approve": "Approved",
    "Reject": "Rejected",
    "Submit": "Submitted",
    "Delete": "Deleted",
    "Record": "Recorded",
}
POLICY_BOUNDARY_MARKERS = {
    "boundary",
    "permission",
    "policy",
    "constraint",
    "guardrail",
    "access",
    "权限",
    "边界",
    "策略",
    "约束",
}
PERSISTENT_SUBJECT_MARKERS = {
    "record",
    "task",
    "view",
    "run",
    "report",
    "decision",
    "asset",
    "finding",
    "recommendation",
    "order",
    "plan",
    "summary",
    "记录",
    "任务",
    "视图",
    "报告",
    "决策",
    "订单",
    "计划",
    "审计",
}


def _listish(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def _operation_id(operation: dict[str, object]) -> str:
    return str(
        operation.get("operation_id")
        or operation.get("operationId")
        or f"{operation.get('method', '')}-{operation.get('path', '')}"
    ).strip()


def _operation_entry(rich_context: dict[str, object] | None, operation_id: str) -> dict[str, Any]:
    if not isinstance(rich_context, dict):
        return {}
    operations = rich_context.get("operations")
    if not isinstance(operations, dict):
        return {}
    entry = operations.get(operation_id)
    return entry if isinstance(entry, dict) else {}


def _semantic_decision(agentic_semantic_decisions: dict[str, object] | None, operation_id: str) -> dict[str, Any]:
    if not isinstance(agentic_semantic_decisions, dict):
        return {}
    decisions = agentic_semantic_decisions.get("decisions")
    if not isinstance(decisions, dict):
        return {}
    entry = decisions.get(operation_id)
    return entry if isinstance(entry, dict) else {}


def _components(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in _listish(entry.get("components")) if isinstance(item, dict)]


def _action_card_refs(entry: dict[str, Any]) -> list[str]:
    refs = _listish(entry.get("action_card_refs"))
    if refs:
        return _unique_strings(
            [
                item.get("action_card_id") if isinstance(item, dict) else item
                for item in refs
            ]
        )
    return _unique_strings(
        [
            component.get("action_card_id") or component.get("component_id")
            for component in _components(entry)
        ]
    )


def _component_values(entry: dict[str, Any], key: str) -> list[Any]:
    return [component.get(key) for component in _components(entry)]


def _execution_steps(entry: dict[str, Any], operation_id: str) -> list[str]:
    direct = _unique_strings(_listish(entry.get("execution_steps")) + _listish(entry.get("service_execution_steps")))
    if direct:
        return direct
    component_types = _unique_strings(_component_values(entry, "component_type"))
    if _components(entry):
        return [
            f"load {operation_id} source-backed context from Action Card obligations",
            f"apply {operation_id} business decision using {', '.join(component_types) or 'component'} obligations",
            f"persist or return {operation_id} according to Action Card read/write intent",
        ]
    return []


def _repository_effect_steps(entry: dict[str, Any], service_steps: list[str], operation_id: str) -> list[str]:
    direct = _unique_strings(_listish(entry.get("repository_effect_steps")))
    if direct:
        return direct
    write_keywords = ("persist", "save", "insert", "update")
    selected = [
        step
        for step in service_steps
        if any(keyword in step.lower() for keyword in write_keywords)
    ]
    if not selected:
        read_keywords = ("load", "read", "repository")
        selected = [
            step
            for step in service_steps
            if any(keyword in step.lower() for keyword in read_keywords)
        ]
    if selected:
        return _unique_strings(selected)
    if _components(entry):
        return [f"apply {operation_id} repository effect from Action Card obligations"]
    return []


def _audit_event_steps(entry: dict[str, Any], service_steps: list[str]) -> list[str]:
    direct = _unique_strings(_listish(entry.get("audit_event_steps")))
    if direct:
        return direct
    keywords = ("audit", "event", "recorded", "changed")
    return _unique_strings(
        [step for step in service_steps if any(keyword in step.lower() for keyword in keywords)]
    )


def _failure_mapping_steps(entry: dict[str, Any], runtime_spec: dict[str, object] | None) -> list[str]:
    runtime_failures = []
    if isinstance(runtime_spec, dict):
        runtime_failures = [
            item.get("error_code")
            for item in _listish(runtime_spec.get("failureCases"))
            if isinstance(item, dict)
        ]
    return _unique_strings(
        _listish(entry.get("failure_modes"))
        + _listish(entry.get("failure_mapping_steps"))
        + runtime_failures
    )


def _is_read_operation(operation: dict[str, object], runtime_spec: dict[str, object] | None) -> bool:
    mode = str((runtime_spec or {}).get("executionMode") or (runtime_spec or {}).get("execution_mode") or "").strip().lower()
    if mode in {"detail-read", "list-read", "read", "query"}:
        return True
    method = str(operation.get("method") or "").strip().upper()
    operation_id = _operation_id(operation).lower()
    return method == "GET" or operation_id.startswith(("list", "get", "search", "read"))


def _split_operation_words(operation_id: str) -> list[str]:
    return re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", operation_id)


def _singularize(word: str) -> str:
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 1:
        return word[:-1]
    return word


def _subject_from_operation_id(operation_id: str) -> str:
    words = _split_operation_words(operation_id)
    if not words:
        return operation_id
    if words and words[0] in LEADING_OPERATION_VERBS:
        words = words[1:]
    while words and words[-1] in TRAILING_OPERATION_DESCRIPTORS:
        words = words[:-1]
    if words:
        words[-1] = _singularize(words[-1])
    return "".join(words) or operation_id


def _normalise_owner_subject(owner: str) -> str:
    subject = owner
    for suffix in ("WorkflowService", "Service", "Workflow"):
        if subject.endswith(suffix):
            subject = subject[: -len(suffix)]
    return subject


def _is_weak_domain_subject(candidate: str, inferred: str) -> bool:
    if not candidate:
        return True
    raw_lower = candidate.lower()
    snake = "_".join(_split_operation_words(candidate)).lower() or raw_lower
    if any(marker in raw_lower or marker in snake for marker in POLICY_BOUNDARY_MARKERS) and not any(
        marker in raw_lower or marker in snake for marker in PERSISTENT_SUBJECT_MARKERS
    ):
        return True
    if len(candidate) <= 1:
        return True
    candidate_words = _split_operation_words(candidate)
    if candidate in LEADING_OPERATION_VERBS or candidate in TRAILING_OPERATION_DESCRIPTORS:
        return True
    if candidate_words and all(word in LEADING_OPERATION_VERBS or word in TRAILING_OPERATION_DESCRIPTORS for word in candidate_words):
        return True
    return bool(inferred and candidate != inferred and inferred.startswith(candidate))


def _domain_subject(operation_id: str, aggregate: str, owner: str) -> str:
    inferred = _subject_from_operation_id(operation_id)
    candidates = [aggregate, _normalise_owner_subject(owner)]
    for candidate in candidates:
        text = str(candidate or "").strip()
        if not _is_weak_domain_subject(text, inferred):
            return text
    return inferred


def _domain_subject_from_steps(service_steps: list[str]) -> str:
    for step in service_steps:
        words = [word.strip(".,:;()[]{}") for word in step.split()]
        for index, word in enumerate(words):
            lower = word.lower()
            if lower in {"load", "read", "return", "persist", "append", "validate", "apply"}:
                continue
            if word[:1].isupper():
                return word
            if index + 1 < len(words) and words[index + 1].lower() in {"aggregate", "projection", "record", "list"}:
                return word
    return ""


def _looks_like_domain_event_name(word: str) -> bool:
    suffixes = tuple(set(EVENT_VERB_SUFFIXES.values()) | {"Changed", "Recorded", "Prepared", "Evaluated"})
    return word.endswith(suffixes) or "Event" in word


def _event_name_from_steps(audit_steps: list[str], operation_id: str, subject: str) -> str:
    for step in audit_steps:
        words = [
            token.strip(".,:;()[]{}")
            for token in step.replace("/", " ").split()
            if token.strip(".,:;()[]{}")
        ]
        for word in words:
            lower = word.lower()
            if lower in {"append", "record", "emit", "audit", "event", "events"}:
                continue
            if "event" in lower or _looks_like_domain_event_name(word):
                return word
    operation_words = _split_operation_words(operation_id)
    if not operation_words:
        return f"{subject}Changed" if subject else f"{operation_id}Changed"
    suffix = EVENT_VERB_SUFFIXES.get(operation_words[0], "Changed")
    subject_words = _split_operation_words(subject)
    remainder = operation_words[1:] if operation_words[0] in LEADING_OPERATION_VERBS else operation_words
    if subject_words and remainder[: len(subject_words)] == subject_words:
        remainder = remainder[len(subject_words) :]
    event_root = subject + "".join(remainder)
    return f"{event_root or subject or operation_id}{suffix}"


def _trigger_event_names(entry: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    semantics = decision.get("operation_semantics") if isinstance(decision.get("operation_semantics"), dict) else {}
    return _unique_strings(
        _listish(entry.get("trigger_events"))
        + _listish(entry.get("domain_events"))
        + _listish(semantics.get("trigger_events"))
    )


def _domain_event_models(entry: dict[str, Any], decision: dict[str, Any]) -> list[dict[str, str]]:
    semantics = decision.get("operation_semantics") if isinstance(decision.get("operation_semantics"), dict) else {}
    raw_models = (
        _listish(entry.get("domain_event_models"))
        + _listish(entry.get("domain_event_catalog"))
        + _listish(semantics.get("domain_event_models"))
        + _listish(semantics.get("domain_event_catalog"))
    )
    models: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        model = {
            "event_name": str(item.get("event_name") or item.get("name") or "").strip(),
            "producer": str(item.get("producer") or "").strip(),
            "consumer": str(item.get("consumer") or "").strip(),
            "trigger": str(item.get("trigger") or item.get("trigger_condition") or "").strip(),
            "payload": str(item.get("payload") or item.get("payload_shape") or "").strip(),
            "timing": str(item.get("timing") or item.get("ordering_semantics") or "").strip(),
            "idempotency": str(item.get("idempotency") or item.get("idempotency_rule") or "").strip(),
        }
        if not model["event_name"]:
            continue
        key = (model["event_name"], model["producer"], model["consumer"])
        if key in seen:
            continue
        seen.add(key)
        models.append(model)
    return models


def _domain_event_modeling_effects(event_models: list[dict[str, str]], event_names: list[str]) -> list[str]:
    selected_names = set(event_names)
    effects: list[str] = []
    for model in event_models:
        event_name = model["event_name"]
        if selected_names and event_name not in selected_names:
            continue
        details = [
            f"producer {model['producer']}" if model["producer"] else "",
            f"consumer {model['consumer']}" if model["consumer"] else "",
            f"trigger {model['trigger']}" if model["trigger"] else "",
            f"payload {model['payload']}" if model["payload"] else "",
            f"timing {model['timing']}" if model["timing"] else "",
            f"idempotency {model['idempotency']}" if model["idempotency"] else "",
        ]
        effect = f"model {event_name}"
        populated = [detail for detail in details if detail]
        if populated:
            effect += " with " + "; ".join(populated)
        effects.append(effect)
    return _unique_strings(effects)


def _transition_name(service_steps: list[str], operation_id: str) -> str:
    for step in service_steps:
        lower = step.lower()
        if "transition" in lower:
            before = lower.split("transition", 1)[0].strip()
            words = [word for word in before.split() if word not in {"validate", "apply", "the", "a", "an"}]
            if words:
                return " ".join(words[-2:] if len(words) > 1 else words) + " transition"
            return "state transition"
    if any(token in operation_id.lower() for token in ("status", "state", "start", "complete", "approve", "reject")):
        return "state transition"
    return "business transition"


def _repository_domain_effects(
    *,
    operation: dict[str, object],
    operation_id: str,
    aggregate: str,
    owner: str,
    service_steps: list[str],
    runtime_spec: dict[str, object] | None,
) -> list[str]:
    subject = _domain_subject(operation_id, aggregate, owner)
    if subject == operation_id or not subject:
        subject = _domain_subject_from_steps(service_steps) or subject
    if _is_read_operation(operation, runtime_spec):
        read_surface = "projection"
        if any("aggregate" in step.lower() for step in service_steps):
            read_surface = "aggregate"
        return [f"read {subject} {read_surface} for {operation_id} without durable mutation"]
    return [f"persist {subject} lifecycle change for {operation_id}"]


def _state_transition_effects(
    *,
    operation: dict[str, object],
    operation_id: str,
    aggregate: str,
    owner: str,
    service_steps: list[str],
    runtime_spec: dict[str, object] | None,
) -> list[str]:
    if _is_read_operation(operation, runtime_spec):
        return []
    subject = _domain_subject(operation_id, aggregate, owner)
    transition = _transition_name(service_steps, operation_id)
    return [f"apply {subject} {transition} before durable write"]


def _audit_event_effects(
    *,
    operation: dict[str, object],
    operation_id: str,
    aggregate: str,
    owner: str,
    audit_steps: list[str],
    trigger_events: list[str],
    runtime_spec: dict[str, object] | None,
) -> list[str]:
    subject = _domain_subject(operation_id, aggregate, owner)
    if _is_read_operation(operation, runtime_spec):
        return [f"do not emit mutation audit/event for {operation_id} read-only path"]
    event_name = (trigger_events or [_event_name_from_steps(audit_steps, operation_id, subject)])[0]
    return [f"record {event_name} after {subject} write commits"]


def _failure_effect_boundaries(
    *,
    operation: dict[str, object],
    operation_id: str,
    aggregate: str,
    owner: str,
    failure_steps: list[str],
    runtime_spec: dict[str, object] | None,
) -> list[str]:
    if _is_read_operation(operation, runtime_spec):
        return []
    subject = _domain_subject(operation_id, aggregate, owner)
    priority_tokens = ("version", "conflict", "duplicate", "forbidden", "permission")
    selected = ""
    for token in priority_tokens:
        selected = next((failure for failure in failure_steps if token in failure.lower()), "")
        if selected:
            break
    selected = selected or (failure_steps[0] if failure_steps else "")
    if not selected:
        return [
            f"map request/authorization/conflict/dependency failures before {subject} write or event emission"
        ]
    return [f"map {selected} before {subject} write or event emission"]


def _unit_assertion_obligations(entry: dict[str, Any], runtime_spec: dict[str, object] | None) -> list[str]:
    request_fields = []
    if isinstance(runtime_spec, dict):
        request_fields = _listish(runtime_spec.get("requestRequiredFields"))
    return _unique_strings(
        _listish(entry.get("required_tests"))
        + _listish(entry.get("unit_assertion_obligations"))
        + request_fields
    )


def _owner_and_aggregate(
    *,
    entry: dict[str, Any],
    decision: dict[str, Any],
    module_implementation_briefs: dict[str, object] | None,
    module_slug: str,
) -> tuple[str, str]:
    semantics = decision.get("operation_semantics") if isinstance(decision.get("operation_semantics"), dict) else {}
    owner = str(semantics.get("owner_service") or entry.get("owner_service") or "").strip()
    aggregate = str(semantics.get("aggregate") or entry.get("aggregate") or "").strip()
    if (owner and aggregate) or not isinstance(module_implementation_briefs, dict):
        return owner, aggregate
    modules = module_implementation_briefs.get("modules")
    module = modules.get(module_slug) if isinstance(modules, dict) else None
    if isinstance(module, dict):
        service_strategy = module.get("service_flow_strategy") if isinstance(module.get("service_flow_strategy"), dict) else {}
        aggregate_model = module.get("aggregate_invariant_model") if isinstance(module.get("aggregate_invariant_model"), dict) else {}
        owner = owner or str(service_strategy.get("owner_service") or "").strip()
        aggregate = aggregate or str(aggregate_model.get("aggregate") or "").strip()
    return owner, aggregate


def build_action_card_direct_implementation_driver(
    *,
    operations: list[dict[str, object]],
    rich_context: dict[str, object] | None,
    runtime_operation_specs: dict[str, dict[str, object]] | None = None,
    agentic_semantic_decisions: dict[str, object] | None = None,
    project_implementation_conventions: dict[str, object] | None = None,
    module_implementation_briefs: dict[str, object] | None = None,
) -> dict[str, object]:
    driver_operations: dict[str, dict[str, object]] = {}
    runtime_specs = runtime_operation_specs or {}
    _ = project_implementation_conventions

    for operation in operations:
        operation_id = _operation_id(operation)
        if not operation_id:
            continue
        module_slug = str(operation.get("tag") or "").strip()
        entry = _operation_entry(rich_context, operation_id)
        decision = _semantic_decision(agentic_semantic_decisions, operation_id)
        runtime_spec = runtime_specs.get(operation_id, {})
        service_steps = _execution_steps(entry, operation_id)
        repository_steps = _repository_effect_steps(entry, service_steps, operation_id)
        audit_steps = _audit_event_steps(entry, service_steps)
        trigger_events = _trigger_event_names(entry, decision)
        domain_event_models = _domain_event_models(entry, decision)
        failure_steps = _failure_mapping_steps(entry, runtime_spec)
        unit_obligations = _unit_assertion_obligations(entry, runtime_spec)
        owner, aggregate = _owner_and_aggregate(
            entry=entry,
            decision=decision,
            module_implementation_briefs=module_implementation_briefs,
            module_slug=module_slug,
        )
        repository_domain_effects = _repository_domain_effects(
            operation=operation,
            operation_id=operation_id,
            aggregate=aggregate,
            owner=owner,
            service_steps=service_steps,
            runtime_spec=runtime_spec,
        )
        state_transition_effects = _state_transition_effects(
            operation=operation,
            operation_id=operation_id,
            aggregate=aggregate,
            owner=owner,
            service_steps=service_steps,
            runtime_spec=runtime_spec,
        )
        audit_event_effects = _audit_event_effects(
            operation=operation,
            operation_id=operation_id,
            aggregate=aggregate,
            owner=owner,
            audit_steps=audit_steps,
            trigger_events=trigger_events,
            runtime_spec=runtime_spec,
        )
        domain_event_modeling_effects = _domain_event_modeling_effects(domain_event_models, trigger_events)
        failure_effect_boundaries = _failure_effect_boundaries(
            operation=operation,
            operation_id=operation_id,
            aggregate=aggregate,
            owner=owner,
            failure_steps=failure_steps,
            runtime_spec=runtime_spec,
        )
        review_bound_gaps = []
        if not service_steps:
            review_bound_gaps.append("service_execution_steps_missing")
        if not unit_obligations:
            review_bound_gaps.append("unit_assertion_obligations_missing")

        driver_operations[operation_id] = {
            "operation_id": operation_id,
            "module_slug": module_slug,
            "action_card_refs": _action_card_refs(entry),
            "behavior_card_refs": _unique_strings(_listish(entry.get("behavior_card_refs"))),
            "aggregate": aggregate,
            "owner_service": owner,
            "service_execution_steps": service_steps,
            "repository_effect_steps": repository_steps,
            "repository_domain_effects": repository_domain_effects,
            "state_transition_effects": state_transition_effects,
            "failure_mapping_steps": failure_steps,
            "failure_effect_boundaries": failure_effect_boundaries,
            "audit_event_steps": audit_steps,
            "trigger_events": trigger_events,
            "audit_event_effects": audit_event_effects,
            "domain_event_modeling_effects": domain_event_modeling_effects,
            "unit_assertion_obligations": unit_obligations,
            "evidence_links": _unique_strings(
                _listish(entry.get("source_refs"))
                + _listish(entry.get("evidence_links"))
            ),
            "review_bound_gaps": review_bound_gaps,
            "control_precedence": (
                "Action Card direct driver > F.13 semantic decision > "
                "F.14 convention > F.15 module brief > renderer fallback"
            ),
        }

    return {
        "artifact_kind": DRIVER_KIND,
        "mode": "default-p3-mainline-in-memory",
        "operations": driver_operations,
        "summary": {
            "operation_count": len(driver_operations),
            "operation_with_service_steps_count": sum(
                1 for entry in driver_operations.values() if entry["service_execution_steps"]
            ),
            "operation_with_repository_effect_count": sum(
                1 for entry in driver_operations.values() if entry["repository_effect_steps"]
            ),
            "operation_with_repository_domain_effect_count": sum(
                1 for entry in driver_operations.values() if entry["repository_domain_effects"]
            ),
            "operation_with_audit_event_effect_count": sum(
                1 for entry in driver_operations.values() if entry["audit_event_effects"]
            ),
            "operation_with_domain_event_modeling_effect_count": sum(
                1 for entry in driver_operations.values() if entry["domain_event_modeling_effects"]
            ),
            "operation_with_unit_obligation_count": sum(
                1 for entry in driver_operations.values() if entry["unit_assertion_obligations"]
            ),
            "review_bound_operation_count": sum(
                1 for entry in driver_operations.values() if entry["review_bound_gaps"]
            ),
            "persisted": False,
            "persisted_default_heavy_artifact_count": 0,
        },
        "claim_ceiling": (
            "in-memory Action Card direct implementation input only; generated quality "
            "requires strict-runtime and human Review"
        ),
    }
