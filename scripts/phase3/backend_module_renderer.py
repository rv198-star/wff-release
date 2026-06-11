#!/usr/bin/env python3
"""Render generated Phase-3 backend module artifacts."""

from __future__ import annotations

import json
import re
from typing import Any

from phase3.behavior_contract import (
    behavior_evidence_keys,
    typescript_array_literal,
    typescript_behavior_card_payload_helper_lines,
)
from phase3.contract_tools import slugify
from phase3.phase3_behavior_card_consumption import (
    render_behavior_step_test_mapping,
    render_repository_invariant_plan,
    render_service_implementation_plan,
)


def camel_case(value: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    if not words:
        return "Generated"
    return "".join(word[:1].upper() + word[1:] for word in words)


def lower_camel(value: str) -> str:
    class_name = camel_case(value)
    if not class_name:
        return "handle"
    return class_name[:1].lower() + class_name[1:]


def snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized.lower()


def runtime_spec_for_operation(
    operation: dict[str, str],
    operation_specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
    return operation_specs.get(operation_id, {})


def business_behavior_authoring_plan_for_operation(
    business_behavior_authoring_plan: dict[str, Any] | None,
    operation_id: str,
) -> dict[str, Any]:
    if not isinstance(business_behavior_authoring_plan, dict):
        return {}
    operations = business_behavior_authoring_plan.get("operations")
    if not isinstance(operations, dict):
        return {}
    entry = operations.get(operation_id)
    return entry if isinstance(entry, dict) else {}


def action_card_execution_map_for_operation(
    action_card_execution_map: dict[str, Any] | None,
    operation_id: str,
) -> dict[str, Any]:
    if not isinstance(action_card_execution_map, dict):
        return {}
    operations = action_card_execution_map.get("operations")
    if not isinstance(operations, dict):
        return {}
    entry = operations.get(operation_id)
    return entry if isinstance(entry, dict) else {}


def agentic_semantic_decision_for_operation(
    agentic_semantic_decisions: dict[str, Any] | None,
    operation_id: str,
) -> dict[str, Any]:
    if not isinstance(agentic_semantic_decisions, dict):
        return {}
    decisions = agentic_semantic_decisions.get("decisions")
    if not isinstance(decisions, dict):
        return {}
    entry = decisions.get(operation_id)
    return entry if isinstance(entry, dict) else {}


def module_implementation_brief_for_module(
    module_implementation_briefs: dict[str, Any] | None,
    module_slug: str,
) -> dict[str, Any]:
    if not isinstance(module_implementation_briefs, dict):
        return {}
    modules = module_implementation_briefs.get("modules")
    if not isinstance(modules, dict):
        return {}
    entry = modules.get(module_slug)
    return entry if isinstance(entry, dict) else {}


def action_card_direct_driver_for_operation(
    action_card_direct_implementation_driver: dict[str, Any] | None,
    operation_id: str,
) -> dict[str, Any]:
    if not isinstance(action_card_direct_implementation_driver, dict):
        return {}
    operations = action_card_direct_implementation_driver.get("operations")
    if not isinstance(operations, dict):
        return {}
    entry = operations.get(operation_id)
    return entry if isinstance(entry, dict) else {}


def render_action_card_direct_service_comment_lines(driver_operation: dict[str, Any] | None) -> list[str]:
    if not isinstance(driver_operation, dict) or not driver_operation:
        return []
    lines = ["  // action-card-direct-driver: service-execution"]
    for step in _unique_nonempty_strings(_listish(driver_operation.get("service_execution_steps"))):
        lines.append(f"  // action-card-service-step: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("audit_event_steps"))):
        lines.append(f"  // action-card-audit-event: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("audit_event_effects"))):
        lines.append(f"  // action-card-audit-event-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("domain_event_modeling_effects"))):
        lines.append(f"  // action-card-domain-event-modeling-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("failure_effect_boundaries"))):
        lines.append(f"  // action-card-failure-effect-boundary: {step}")
    return lines


def render_action_card_direct_repository_comment_lines(driver_operation: dict[str, Any] | None) -> list[str]:
    if not isinstance(driver_operation, dict) or not driver_operation:
        return []
    lines = ["  // action-card-direct-driver: repository-effect"]
    for step in _unique_nonempty_strings(_listish(driver_operation.get("repository_effect_steps"))):
        lines.append(f"  // action-card-repository-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("repository_domain_effects"))):
        lines.append(f"  // action-card-repository-domain-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("state_transition_effects"))):
        lines.append(f"  // action-card-state-transition-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("audit_event_effects"))):
        lines.append(f"  // action-card-audit-event-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("domain_event_modeling_effects"))):
        lines.append(f"  // action-card-domain-event-modeling-effect: {step}")
    for step in _unique_nonempty_strings(_listish(driver_operation.get("failure_effect_boundaries"))):
        lines.append(f"  // action-card-failure-effect-boundary: {step}")
    return lines


def render_action_card_direct_unit_comment_lines(driver_operation: dict[str, Any] | None) -> list[str]:
    if not isinstance(driver_operation, dict) or not driver_operation:
        return []
    lines = ["  // action-card-direct-driver: unit-obligation"]
    for obligation in _unique_nonempty_strings(_listish(driver_operation.get("unit_assertion_obligations"))):
        lines.append(f"  // action-card-unit-obligation: {obligation}")
    return lines


def apply_action_card_driver_to_model(
    model: dict[str, Any],
    driver_operation: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(driver_operation, dict) or not driver_operation:
        return model
    next_model = dict(model)
    operation_semantics = (
        dict(next_model.get("operation_semantics", {}))
        if isinstance(next_model.get("operation_semantics"), dict)
        else {}
    )
    owner_service = str(driver_operation.get("owner_service") or "").strip()
    aggregate = str(driver_operation.get("aggregate") or "").strip()
    evidence_links = _unique_nonempty_strings(_listish(driver_operation.get("evidence_links")))
    if owner_service:
        operation_semantics["owner_service"] = owner_service
    if aggregate:
        operation_semantics["aggregate"] = aggregate
    if evidence_links:
        operation_semantics["evidence_keys"] = evidence_links
    next_model["operation_semantics"] = operation_semantics

    service_steps = _unique_nonempty_strings(_listish(driver_operation.get("service_execution_steps")))
    if service_steps:
        next_model["steps"] = [
            {"id": f"step-{index}", "title": step}
            for index, step in enumerate(service_steps, start=1)
        ]
    repository_effects = _unique_nonempty_strings(
        _listish(driver_operation.get("repository_domain_effects"))
        + _listish(driver_operation.get("repository_effect_steps"))
    )
    if repository_effects:
        next_model["persistence_effects"] = "; ".join(repository_effects)
    audit_steps = _unique_nonempty_strings(
        _listish(driver_operation.get("audit_event_effects"))
        + _listish(driver_operation.get("audit_event_steps"))
    )
    if audit_steps:
        next_model["audit_effect"] = "; ".join(audit_steps)
    failure_steps = _unique_nonempty_strings(_listish(driver_operation.get("failure_mapping_steps")))
    if failure_steps:
        next_model["error_codes"] = failure_steps
    unit_obligations = _unique_nonempty_strings(_listish(driver_operation.get("unit_assertion_obligations")))
    if unit_obligations:
        next_model["agentic_module_test_intent"] = "Action Card unit obligations: " + ", ".join(unit_obligations)
    next_model["action_card_direct_implementation_driver"] = driver_operation
    next_model["agentic_body_authoring_mode"] = "action-card-direct-implementation-driver"
    return next_model


def apply_module_implementation_brief_to_model(
    model: dict[str, Any],
    brief: dict[str, Any] | None,
    operation_id: str,
) -> dict[str, Any]:
    if not isinstance(brief, dict) or not brief:
        return model
    next_model = dict(model)
    aggregate_model = brief.get("aggregate_invariant_model") if isinstance(brief.get("aggregate_invariant_model"), dict) else {}
    service_strategy = brief.get("service_flow_strategy") if isinstance(brief.get("service_flow_strategy"), dict) else {}
    repository_strategy = (
        brief.get("repository_effect_strategy") if isinstance(brief.get("repository_effect_strategy"), dict) else {}
    )
    posture = (
        brief.get("transaction_audit_auth_error_posture")
        if isinstance(brief.get("transaction_audit_auth_error_posture"), dict)
        else {}
    )
    unit_strategy = brief.get("unit_test_strategy") if isinstance(brief.get("unit_test_strategy"), dict) else {}
    operation_test_intents = (
        unit_strategy.get("operation_test_intents") if isinstance(unit_strategy.get("operation_test_intents"), dict) else {}
    )
    operation_semantics = (
        dict(next_model.get("operation_semantics", {}))
        if isinstance(next_model.get("operation_semantics"), dict)
        else {}
    )
    owner_service = str(service_strategy.get("owner_service") or "").strip()
    aggregate = str(aggregate_model.get("aggregate") or "").strip()
    if owner_service:
        operation_semantics["owner_service"] = owner_service
    if aggregate:
        operation_semantics["aggregate"] = aggregate
    context_sufficiency = brief.get("context_sufficiency") if isinstance(brief.get("context_sufficiency"), dict) else {}
    evidence_keys = _unique_nonempty_strings(
        _listish(operation_semantics.get("evidence_keys")) + _listish(context_sufficiency.get("source_refs"))
    )
    if evidence_keys:
        operation_semantics["evidence_keys"] = evidence_keys
    next_model["operation_semantics"] = operation_semantics
    invariants = _unique_nonempty_strings(_listish(aggregate_model.get("invariants")))
    if invariants:
        next_model["invariants"] = "; ".join(invariants)
    if repository_strategy.get("strategy"):
        next_model["persistence_effects"] = str(repository_strategy.get("strategy")).strip()
    if posture.get("transaction"):
        next_model["transaction_rule"] = str(posture.get("transaction")).strip()
    if posture.get("audit"):
        next_model["audit_effect"] = str(posture.get("audit")).strip()
    if operation_test_intents.get(operation_id):
        next_model["agentic_module_test_intent"] = str(operation_test_intents.get(operation_id)).strip()
    next_model["agentic_module_implementation_brief"] = brief
    next_model["agentic_body_authoring_mode"] = "agentic-module-implementation-brief"
    return next_model


def apply_agentic_semantic_decision_to_model(
    model: dict[str, Any],
    decision: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(decision, dict) or not decision:
        return model
    next_model = dict(model)
    operation_semantics = dict(next_model.get("operation_semantics", {})) if isinstance(next_model.get("operation_semantics"), dict) else {}
    decision_semantics = decision.get("operation_semantics") if isinstance(decision.get("operation_semantics"), dict) else {}
    operation_semantics.update({key: value for key, value in decision_semantics.items() if value not in ("", [], None)})
    next_model["operation_semantics"] = operation_semantics
    invariants = decision.get("domain_invariants") if isinstance(decision.get("domain_invariants"), list) else []
    invariant_texts = [str(item.get("invariant") or "").strip() for item in invariants if isinstance(item, dict) and str(item.get("invariant") or "").strip()]
    if invariant_texts:
        next_model["invariants"] = "; ".join(invariant_texts)
    value_rule = decision.get("value_rule") if isinstance(decision.get("value_rule"), dict) else {}
    if value_rule.get("rule"):
        next_model["state_transition"] = str(value_rule.get("rule")).strip()
    next_model["agentic_semantic_decision"] = decision
    next_model["agentic_body_authoring_mode"] = "agentic-semantic-authoring"
    return next_model


def render_action_card_trace_comment_lines(action_card_entry: dict[str, Any] | None) -> list[str]:
    if not isinstance(action_card_entry, dict) or not action_card_entry:
        return []
    components = [item for item in _listish(action_card_entry.get("components")) if isinstance(item, dict)]
    if not components:
        return []
    lines: list[str] = []
    operation_id = str(action_card_entry.get("operation_id") or "").strip()
    for component in components:
        action_card_id = str(component.get("action_card_id") or component.get("component_id") or "").strip()
        acd_level = str(component.get("acd_level") or "").strip()
        if action_card_id:
            lines.append(f"  // action-card-id: {action_card_id}")
        if operation_id:
            lines.append(f"  // action-card-step: {operation_id}")
        if acd_level:
            lines.append(f"  // acd-level: {acd_level}")
    return lines


def collapse_service_mechanical_helpers(source: str) -> str:
    source = re.sub(r"this\.resolve[A-Za-z0-9]+ContextValue\(", "this.resolveContextValue(", source)
    source = re.sub(r"this\.merge[A-Za-z0-9]+RepositoryResult\(", "this.mergeRepositoryResult(", source)
    source = re.sub(
        r"\n  private resolve[A-Za-z0-9]+ContextValue\(context: Record<string, unknown>, key: string\): unknown \{\n"
        r"    const requestedSnake = key\.replace\(/\(\[a-z0-9\]\)\(\[A-Z\]\)/g, \"\$1_\$2\"\)\.toLowerCase\(\);\n"
        r"    for \(const source of \[context, context\.path_params, context\.auth_context, context\.body, context\.input, context\.query\]\) \{\n"
        r"      if \(!source \|\| typeof source !== \"object\" \|\| Array\.isArray\(source\)\) \{\n"
        r"        continue;\n"
        r"      \}\n"
        r"      const record = source as Record<string, unknown>;\n"
        r"      for \(const candidate of Object\.keys\(record\)\) \{\n"
        r"        const candidateSnake = candidate\.replace\(/\(\[a-z0-9\]\)\(\[A-Z\]\)/g, \"\$1_\$2\"\)\.toLowerCase\(\);\n"
        r"        if \(candidate === key \|\| candidateSnake === requestedSnake\) \{\n"
        r"          return record\[candidate\];\n"
        r"        \}\n"
        r"      \}\n"
        r"    \}\n"
        r"    return undefined;\n"
        r"  \n?\}\n?",
        "",
        source,
    )
    source = re.sub(
        r"\n  private merge[A-Za-z0-9]+RepositoryResult\(nextState: Record<string, unknown>, repositoryResult: unknown\): Record<string, unknown> \{\n"
        r"    if \(!repositoryResult \|\| typeof repositoryResult !== \"object\" \|\| Array\.isArray\(repositoryResult\)\) \{\n"
        r"      return \{ \.\.\.nextState \};\n"
        r"    \}\n"
        r"    const resultRecord = repositoryResult as Record<string, unknown>;\n"
        r"    const data = resultRecord\.data;\n"
        r"    if \(data && typeof data === \"object\" && !Array\.isArray\(data\)\) \{\n"
        r"      return \{ \.\.\.nextState, \.\.\.\(data as Record<string, unknown>\) \};\n"
        r"    \}\n"
        r"    return \{ \.\.\.nextState, \.\.\.resultRecord \};\n"
        r"  \n?\}\n?",
        "",
        source,
    )
    helper_block = """
  private resolveContextValue(context: Record<string, unknown>, key: string): unknown {
    const requestedSnake = key.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
    for (const source of [context, context.path_params, context.auth_context, context.body, context.input, context.query]) {
      if (!source || typeof source !== "object" || Array.isArray(source)) {
        continue;
      }
      const record = source as Record<string, unknown>;
      for (const candidate of Object.keys(record)) {
        const candidateSnake = candidate.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
        if (candidate === key || candidateSnake === requestedSnake) {
          return record[candidate];
        }
      }
    }
    return undefined;
  }

  private mergeRepositoryResult(nextState: Record<string, unknown>, repositoryResult: unknown): Record<string, unknown> {
    if (!repositoryResult || typeof repositoryResult !== "object" || Array.isArray(repositoryResult)) {
      return { ...nextState };
    }
    const resultRecord = repositoryResult as Record<string, unknown>;
    const data = resultRecord.data;
    if (data && typeof data === "object" && !Array.isArray(data)) {
      return { ...nextState, ...(data as Record<string, unknown>) };
    }
    return { ...nextState, ...resultRecord };
  }
"""
    if "this.resolveContextValue(" in source or "this.mergeRepositoryResult(" in source:
        source = source.rstrip()
        if source.endswith("\n}"):
            source = source[:-2].rstrip() + "\n" + helper_block + "\n}\n"
    return source


def _unique_nonempty_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def _listish(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _default_failure_case_for_error_code(error_code: str) -> dict[str, str]:
    defaults = {
        "invalid_request": ("400", "business_error", "never"),
        "forbidden": ("403", "business_error", "never"),
        "tenant_forbidden": ("403", "business_error", "never"),
        "not_found": ("404", "business_error", "never"),
        "version_conflict": ("409", "business_error", "never"),
        "dependency_unavailable": ("503", "system_error", "safe"),
    }
    status, kind, retryability = defaults.get(error_code, ("400", "business_error", "never"))
    return {
        "status": status,
        "error_kind": kind,
        "error_code": error_code,
        "retryability": retryability,
    }


def operation_spec_with_business_behavior_plan(
    spec: dict[str, Any],
    plan_entry: dict[str, Any],
) -> dict[str, Any]:
    if not plan_entry:
        return spec
    merged = dict(spec)
    required_context = _unique_nonempty_strings(_listish(merged.get("requestRequiredFields")) + _listish(plan_entry.get("required_context")))
    if required_context:
        merged["requestRequiredFields"] = required_context
    execution_mode = str(plan_entry.get("execution_mode") or "").strip()
    if execution_mode:
        merged["executionMode"] = execution_mode
    state_policy = plan_entry.get("state_conflict_policy") if isinstance(plan_entry.get("state_conflict_policy"), dict) else {}
    unit_obligations = plan_entry.get("unit_test_obligations") if isinstance(plan_entry.get("unit_test_obligations"), dict) else {}
    planned_error_codes = _unique_nonempty_strings(
        _listish(state_policy.get("error_codes"))
        + _listish(unit_obligations.get("failure_codes"))
    )
    failure_cases = [dict(item) for item in merged.get("failureCases", []) if isinstance(item, dict)]
    existing_codes = {
        str(item.get("error_code", "")).strip()
        for item in failure_cases
        if str(item.get("error_code", "")).strip()
    }
    for error_code in planned_error_codes:
        if error_code not in existing_codes:
            failure_cases.append(_default_failure_case_for_error_code(error_code))
            existing_codes.add(error_code)
    if failure_cases:
        merged["failureCases"] = failure_cases
    return merged


def response_example_data(spec: dict[str, Any]) -> Any:
    response_example = spec.get("responseExample", {})
    if not isinstance(response_example, dict):
        return {}
    return response_example.get("data", {})


def response_data_is_array(spec: dict[str, Any]) -> bool:
    return isinstance(response_example_data(spec), list)


def response_id_fields(spec: dict[str, Any]) -> list[str]:
    data = response_example_data(spec)
    if isinstance(data, dict):
        return [key for key in data if key.endswith("_id") or key.endswith("Id")]
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [key for key in data[0] if key.endswith("_id") or key.endswith("Id")]
    return []


def primary_response_id_field(spec: dict[str, Any]) -> str:
    fields = response_id_fields(spec)
    return fields[0] if fields else ""


def strip_id_suffix(value: str) -> str:
    if value.endswith("_id"):
        return value[:-3]
    if value.endswith("Id"):
        return value[:-2]
    return value


def singularize_token(value: str) -> str:
    normalized = snake_case(value)
    if normalized.endswith("ies"):
        return f"{normalized[:-3]}y"
    if normalized.endswith("ses"):
        return normalized[:-2]
    if normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def operation_entity_candidates(spec: dict[str, Any]) -> list[str]:
    candidates: set[str] = set()
    operation_id = str(spec.get("operationId", "")).strip()
    stripped = re.sub(r"^(Create|Get|List|Update|Start|Complete|Generate|Launch|Export|Record|Refresh)", "", operation_id)
    if stripped:
        candidates.add(snake_case(stripped))
    tag = str(spec.get("tag", "")).strip()
    if tag:
        candidates.add(snake_case(tag))
    path = str(spec.get("path", "")).strip()
    if path:
        segments = [
            snake_case(segment)
            for segment in path.split("/")
            if segment and not segment.startswith("{") and segment not in {"api", "v1", "v2", "internal"}
        ]
        if segments:
            candidates.add(segments[-1])
            if len(segments) >= 2:
                candidates.add(segments[-2])
    expanded: set[str] = set()
    for candidate in candidates:
        normalized = snake_case(candidate)
        if not normalized:
            continue
        singular = singularize_token(normalized)
        expanded.add(normalized)
        expanded.add(singular)
        parts = [part for part in singular.split("_") if part]
        if parts:
            expanded.add(parts[-1])
        if len(parts) >= 2:
            expanded.add("_".join(parts[-2:]))
    return [candidate for candidate in expanded if candidate]


def collect_response_id_field_candidates(value: Any, depth: int = 0) -> list[tuple[str, int]]:
    candidates: list[tuple[str, int]] = []
    if isinstance(value, list):
        for item in value:
            candidates.extend(collect_response_id_field_candidates(item, depth + 1))
        return candidates
    if not isinstance(value, dict):
        return candidates
    for key, entry in value.items():
        if isinstance(key, str) and (key.endswith("_id") or key.endswith("Id")):
            candidates.append((key, depth))
        if isinstance(entry, (dict, list)):
            candidates.extend(collect_response_id_field_candidates(entry, depth + 1))
    return candidates


def score_primary_record_hint(field: str, depth: int, entity_candidates: list[str]) -> int:
    normalized = snake_case(field)
    core = singularize_token(strip_id_suffix(normalized))
    score = max(0, 60 - (depth * 10))
    for candidate in entity_candidates:
        singular = singularize_token(candidate)
        if not singular:
            continue
        if normalized == f"{singular}_id":
            score = max(score, 400 - (depth * 10))
            continue
        if core == singular:
            score = max(score, 360 - (depth * 10))
            continue
        if core.endswith(singular) or singular.endswith(core):
            score = max(score, 320 - (depth * 10))
            continue
        overlap = len(set(core.split("_")) & set(singular.split("_")))
        if overlap > 0:
            score = max(score, 220 + (overlap * 20) - (depth * 10))
    return score


def operation_primary_record_hint(spec: dict[str, Any]) -> str:
    path_params = spec.get("pathParams", [])
    if isinstance(path_params, list):
        for param in path_params:
            normalized = snake_case(str(param).strip())
            if normalized:
                return normalized
    response_data = response_example_data(spec)
    scored_candidates: list[tuple[int, int, str]] = []
    for order, (field, depth) in enumerate(collect_response_id_field_candidates(response_data)):
        normalized = snake_case(field)
        if not normalized:
            continue
        score = score_primary_record_hint(normalized, depth, operation_entity_candidates(spec))
        scored_candidates.append((score, depth, f"{order:04d}:{normalized}"))
    if scored_candidates:
        scored_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        return scored_candidates[0][2].split(":", 1)[1]
    return snake_case(primary_response_id_field(spec))


def operation_execution_mode(spec: dict[str, Any]) -> str:
    operation_id = str(spec.get("operationId", "")).strip()
    method = str(spec.get("method", "")).upper()
    if operation_id.startswith(("Create", "Launch", "Export")):
        return "create"
    if operation_id.startswith("Get") and spec.get("pathParams"):
        return "detail-read"
    if (method == "GET" and response_data_is_array(spec)) or operation_id.startswith("List"):
        return "list-read"
    return "command"


def ts_property_access(field_name: str) -> str:
    return f".{field_name}" if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", field_name) else f"[{json.dumps(field_name, ensure_ascii=False)}]"


def unit_business_literal_fields(spec: dict[str, Any]) -> dict[str, Any]:
    data = response_example_data(spec)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        data = data[0]
    if not isinstance(data, dict):
        return {}
    fields: dict[str, Any] = {}
    for field_name, value in data.items():
        normalized = snake_case(str(field_name)).replace("_", "")
        if normalized.endswith("id") or normalized in {"traceid", "createdat", "updatedat"}:
            continue
        if isinstance(value, (str, int, float, bool)) and value is not None:
            fields[str(field_name)] = value
    return fields


def unit_business_assertion_lines(data_expr: str, spec: dict[str, Any]) -> list[str]:
    return [
        f"    expect({data_expr}{ts_property_access(field_name)}).toBe({json.dumps(value, ensure_ascii=False)});"
        for field_name, value in unit_business_literal_fields(spec).items()
    ]


def first_failure_case(spec: dict[str, Any]) -> dict[str, Any]:
    failure_cases = spec.get("failureCases", [])
    if isinstance(failure_cases, list):
        for failure in failure_cases:
            if isinstance(failure, dict) and str(failure.get("error_code", "")).strip():
                return failure
    return {}


def matching_failure_case(
    spec: dict[str, Any],
    *,
    status_prefixes: tuple[str, ...] = (),
    code_tokens: tuple[str, ...] = (),
) -> dict[str, Any]:
    failure_cases = spec.get("failureCases", [])
    if not isinstance(failure_cases, list):
        return {}
    lowered_tokens = tuple(token.lower() for token in code_tokens)
    for failure in failure_cases:
        if not isinstance(failure, dict):
            continue
        status = str(failure.get("status", "")).strip()
        code = str(failure.get("error_code", "")).strip().lower()
        if status_prefixes and any(status.startswith(prefix) for prefix in status_prefixes):
            return failure
        if lowered_tokens and any(token in code for token in lowered_tokens):
            return failure
    return {}


def operation_uniqueness_hint_fields(spec: dict[str, Any]) -> list[str]:
    request_example = spec.get("requestExample", {})
    if not isinstance(request_example, dict):
        return []
    ordered: list[str] = []
    for preferred in (
        "tenant_id",
        "tenantId",
        "scope_key",
        "scopeKey",
        "run_id",
        "runId",
        "finding_id",
        "findingId",
        "recommendation_id",
        "recommendationId",
        "task_id",
        "taskId",
        "review_report_id",
        "reviewReportId",
        "payload_version",
        "payloadVersion",
        "expected_version",
        "expectedVersion",
        "decision",
        "status",
    ):
        if preferred in request_example:
            ordered.append(preferred)
    for key, value in request_example.items():
        normalized = str(key).strip()
        if not normalized or normalized.startswith("_") or value is None:
            continue
        lowered = normalized.lower()
        if normalized in ordered:
            continue
        if (
            normalized.endswith("_id")
            or normalized.endswith("Id")
            or normalized.endswith("_key")
            or normalized.endswith("Key")
            or "version" in lowered
            or "decision" in lowered
            or "status" in lowered
        ):
            ordered.append(normalized)
    if ordered:
        return ordered[:4]
    fallback = [
        str(key).strip()
        for key, value in request_example.items()
        if str(key).strip() and not str(key).strip().startswith("_") and value is not None
    ]
    return fallback[:3]




def render_backend_module_unit_test(
    module_slug: str,
    operations: list[dict[str, str]],
    operation_specs: dict[str, dict[str, Any]],
    *,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
    synthesis_units: list[dict[str, Any]] | None = None,
    business_behavior_authoring_plan: dict[str, Any] | None = None,
    action_card_execution_map: dict[str, Any] | None = None,
    action_card_direct_implementation_driver: dict[str, Any] | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    module_implementation_briefs: dict[str, Any] | None = None,
) -> str:
    module_class = camel_case(module_slug)
    controller_class = f"{module_class}Controller"
    service_class = f"{module_class}Service"
    repository_class = f"{module_class}Repository"
    module_implementation_brief = module_implementation_brief_for_module(module_implementation_briefs, module_slug)
    runtime_test_kit_imports = [
        "buildFailurePayload",
        "buildOperationPayload",
        "captureApiError",
        "extractEnvelopeData",
        "resetGeneratedRuntime",
    ]
    lines = [
        'import { beforeEach, describe, expect, it, vi } from "vitest";',
        'import {',
        *[f"  {entry}," for entry in runtime_test_kit_imports],
        '} from "../../../support/runtime-test-kit";',
        f'import {{ {controller_class} }} from "../../../../apps/api/src/modules/{module_slug}/{module_slug}.controller";',
        f'import {{ {service_class} }} from "../../../../apps/api/src/modules/{module_slug}/{module_slug}.service";',
        f'import {{ {repository_class} }} from "../../../../apps/api/src/modules/{module_slug}/{module_slug}.repository";',
        "",
        "// @phase3-test-family isolated-unit",
        "// @phase3-collaborator-proof repository-double",
        "// @phase3-generated-runtime-module false",
        *([f"// agentic-module-implementation-brief: {module_slug}"] if module_implementation_brief else []),
        *render_synthesis_intent_comment_lines(synthesis_units),
        "",
        f'describe("{module_slug} module unit", () => {{',
*[f"  {line}" if line else "" for line in typescript_behavior_card_payload_helper_lines(map_name=None)],
        "  beforeEach(() => {",
        "    resetGeneratedRuntime();",
        "  });",
        "",
    ]
    for operation in operations:
        operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
        method_name = lower_camel(operation_id)
        action_card_entry = action_card_execution_map_for_operation(action_card_execution_map, operation_id)
        action_card_driver_operation = action_card_direct_driver_for_operation(
            action_card_direct_implementation_driver,
            operation_id,
        )
        plan_entry = business_behavior_authoring_plan_for_operation(business_behavior_authoring_plan, operation_id)
        spec = operation_spec_with_business_behavior_plan(runtime_spec_for_operation(operation, operation_specs), plan_entry)
        execution_mode = operation_execution_mode(spec)
        is_read_operation = execution_mode in {"detail-read", "list-read"}
        record_key = primary_response_id_field(spec)
        behavior_model = (
            business_behavior_plan_entry_to_authoring_model(plan_entry, operation=operation, spec=spec)
            if plan_entry
            else (behavior_card_models or {}).get(operation_id)
        )
        behavior_model = apply_agentic_semantic_decision_to_model(
            behavior_model or {},
            agentic_semantic_decision_for_operation(agentic_semantic_decisions, operation_id),
        )
        behavior_model = apply_module_implementation_brief_to_model(
            behavior_model,
            module_implementation_brief,
            operation_id,
        )
        behavior_model = apply_action_card_driver_to_model(behavior_model, action_card_driver_operation)
        behavior_unit_lines = render_behavior_step_test_mapping(behavior_model)["unit"].splitlines() if behavior_model else []
        agentic_module_test_intent = str(behavior_model.get("agentic_module_test_intent") or "").strip()
        data_type = "unknown[]" if response_data_is_array(spec) else "Record<string, unknown>"
        evidence_keys = behavior_evidence_keys(behavior_model)
        payload_expr = f'buildBehaviorCardPayload("{operation_id}", buildOperationPayload("{operation_id}"), {typescript_array_literal(evidence_keys)})'
        plan_source_refs = _unique_nonempty_strings(_listish(plan_entry.get("source_refs"))) if plan_entry else []
        plan_required_context = _unique_nonempty_strings(_listish(plan_entry.get("required_context"))) if plan_entry else []
        if plan_source_refs or plan_required_context:
            for source_ref in plan_source_refs:
                lines.append(f"  // behavior-plan-source-ref: {source_ref}")
            if plan_required_context:
                lines.append(f"  // behavior-plan-required-context: {', '.join(plan_required_context)}")
            lines.append("")
        action_card_trace_lines = render_action_card_trace_comment_lines(action_card_entry)
        if action_card_trace_lines:
            lines.extend(action_card_trace_lines)
            lines.append("")
        action_card_direct_lines = render_action_card_direct_unit_comment_lines(action_card_driver_operation)
        if action_card_direct_lines:
            lines.extend(action_card_direct_lines)
            lines.append("")
        if agentic_module_test_intent:
            lines.append(f"  // agentic-module-test-intent: {agentic_module_test_intent}")
            lines.append("")
        validation_case = matching_failure_case(
            spec,
            status_prefixes=("400",),
            code_tokens=("invalid", "validation", "missing", "required"),
        )
        required_fields = [
            str(field).strip()
            for field in spec.get("requestRequiredFields", [])
            if str(field).strip()
        ] if isinstance(spec.get("requestRequiredFields", []), list) else []
        missing_required_field = required_fields[0] if required_fields else ""
        permission_case = matching_failure_case(
            spec,
            status_prefixes=("403",),
            code_tokens=("forbidden", "permission", "tenant"),
        )
        not_found_case = matching_failure_case(spec, status_prefixes=("404",), code_tokens=("not_found", "not-found"))
        conflict_case = matching_failure_case(spec, status_prefixes=("409",), code_tokens=("conflict", "duplicate", "version"))
        db_error_case = matching_failure_case(
            spec,
            status_prefixes=("5",),
            code_tokens=("db", "database", "dependency", "unavailable", "timeout"),
        )
        lines.extend(
            [
                f'  it("{operation_id} controller preserves the contract envelope", async () => {{',
                f"    const controller = new {controller_class}();",
                f'    const result = await controller.{method_name}({payload_expr}) as Record<string, unknown>;',
                '    expect(result).toHaveProperty("trace_id");',
                '    expect(result).toHaveProperty("data");',
                '    expect(result).toHaveProperty("meta");',
                '    expect(result.meta).not.toHaveProperty("controller_module");',
                '    expect(result.meta).not.toHaveProperty("service_module");',
                "  });",
                "",
                f'  it("{operation_id} service executes typed backend flow", async () => {{',
                "    const repository = {",
                f"      load{camel_case(operation_id)}ForDecision: vi.fn(async (context: Record<string, unknown>) => ({{ ...context, expectedVersion: context.expectedVersion ?? context.expected_version }})),",
                *([] if is_read_operation else [
                    f"      persist{camel_case(operation_id)}WithInvariants: vi.fn(async () => undefined),",
                    f"      append{camel_case(operation_id)}AuditEffect: vi.fn(async () => undefined),",
                ]),
                f"    }} as unknown as {repository_class};",
                f"    const service = new {service_class}(repository);",
                *behavior_unit_lines,
            ]
        )
        lines.extend(
            [
                f'    const result = await service.{method_name}({payload_expr}) as Record<string, unknown>;',
                f"    const data = extractEnvelopeData<{data_type}>(result);",
                '    expect(result).toHaveProperty("data");',
                '    expect(result.meta).not.toHaveProperty("service_module");',
                '    expect(result.meta).not.toHaveProperty("service_method");',
            ]
        )
        if execution_mode == "create" and record_key:
            excluded_id_keys = {"trace_id", "traceId", "request_id", "requestId", "operation_id", "operationId"}
            evidence_id_keys = [key for key in evidence_keys if (key.endswith("_id") or key.endswith("Id")) and key not in excluded_id_keys]
            id_candidates = [record_key, *evidence_id_keys]
            id_candidates_literal = typescript_array_literal(id_candidates)
            lines.extend(
                [
                    f'    const recordIdCandidates = {id_candidates_literal};',
                    "    const createdRecordId = recordIdCandidates.map((key) => (data as Record<string, unknown>)[key] ?? (data as Record<string, unknown>)[key.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase())]).find((value) => value !== undefined && value !== null && String(value).length > 0);",
                    f'    expect(createdRecordId).toBeTruthy();',
                ]
            )
        elif execution_mode == "detail-read" and record_key:
            lines.append(f'    expect(data).toHaveProperty("{record_key}");')
        elif execution_mode == "list-read" and response_data_is_array(spec):
            lines.append("    expect(Array.isArray(data)).toBe(true);")
        else:
            lines.append("    expect(data).toBeTruthy();")
        if not response_data_is_array(spec):
            lines.extend(unit_business_assertion_lines("data", spec))
        lines.extend(
            [
                f"    expect(repository.load{camel_case(operation_id)}ForDecision).toHaveBeenCalled();",
                *([] if is_read_operation else [
                    f"    expect(repository.persist{camel_case(operation_id)}WithInvariants).toHaveBeenCalled();",
                    f"    expect(repository.append{camel_case(operation_id)}AuditEffect).toHaveBeenCalled();",
                ]),
                "  });",
                "",
                f'  it("{operation_id} repository exposes behavior-card step methods", async () => {{',
                f"    const repository = new {repository_class}();",
                f"    const context = {payload_expr};",
                f"    const current = await repository.load{camel_case(operation_id)}ForDecision(context);",
                "    expect(current).toBeTruthy();",
                *(
                    [f"    await repository.readBack{camel_case(operation_id)}(context);"]
                    if is_read_operation
                    else [
                        f"    await repository.persist{camel_case(operation_id)}WithInvariants(context, current);",
                        f"    await repository.append{camel_case(operation_id)}AuditEffect(context, current);",
                    ]
                ),
                "  });",
                "",
            ]
        )
        if validation_case:
            validation_code = str(validation_case.get("error_code", "")).strip()
            validation_status = str(validation_case.get("status", "")).strip() or "400"
            lines.extend(
                [
                    f'  it("{operation_id} service validates required context", async () => {{',
                    f"    const service = new {service_class}();",
                    f'    const error = await captureApiError(service.{method_name}(buildFailurePayload("{operation_id}", "{validation_code}")));',
                    f"    expect(error.status).toBe({validation_status});",
                    f'    expect(error.envelope.error_code).toBe("{validation_code}");',
                    "  });",
                    "",
                    f'  it("{operation_id} service rejects invalid query before repository access", async () => {{',
                    "    const repository = {",
                    f"      load{camel_case(operation_id)}ForDecision: vi.fn(async (context: Record<string, unknown>) => context),",
                    *([] if is_read_operation else [
                        f"      persist{camel_case(operation_id)}WithInvariants: vi.fn(async () => undefined),",
                        f"      append{camel_case(operation_id)}AuditEffect: vi.fn(async () => undefined),",
                    ]),
                    f"    }} as unknown as {repository_class};",
                    f"    const service = new {service_class}(repository);",
                    f'    const error = await captureApiError(service.{method_name}({{ ...{payload_expr}, invalid_query: true }}));',
                    f"    expect(error.status).toBe({validation_status});",
                    f'    expect(error.envelope.error_code).toBe("{validation_code}");',
                    f'    const stringError = await captureApiError(service.{method_name}({{ ...{payload_expr}, invalid_query: "true" }}));',
                    f"    expect(stringError.status).toBe({validation_status});",
                    f'    expect(stringError.envelope.error_code).toBe("{validation_code}");',
                    f"    expect(repository.load{camel_case(operation_id)}ForDecision).not.toHaveBeenCalled();",
                    "  });",
                    "",
                ]
            )
            if missing_required_field:
                missing_required_field_camel = re.sub(
                    r"_([a-zA-Z0-9])",
                    lambda match: match.group(1).upper(),
                    missing_required_field,
                )
                delete_alias_line = (
                    f'    delete invalidPayload["{missing_required_field_camel}"];'
                    if missing_required_field_camel != missing_required_field
                    else ""
                )
                lines.extend(
                    [
                        f'  it("{operation_id} service rejects missing required contract fields before repository access", async () => {{',
                        "    const repository = {",
                        f"      load{camel_case(operation_id)}ForDecision: vi.fn(async (context: Record<string, unknown>) => context),",
                        *([] if is_read_operation else [
                            f"      persist{camel_case(operation_id)}WithInvariants: vi.fn(async () => undefined),",
                            f"      append{camel_case(operation_id)}AuditEffect: vi.fn(async () => undefined),",
                        ]),
                        f"    }} as unknown as {repository_class};",
                        f"    const service = new {service_class}(repository);",
                        f"    const invalidPayload = {{ ...{payload_expr} }};",
                        f'    delete invalidPayload["{missing_required_field}"];',
                        *([delete_alias_line] if delete_alias_line else []),
                        f"    const error = await captureApiError(service.{method_name}(invalidPayload));",
                        f"    expect(error.status).toBe({validation_status});",
                        f'    expect(error.envelope.error_code).toBe("{validation_code}");',
                        f"    expect(repository.load{camel_case(operation_id)}ForDecision).not.toHaveBeenCalled();",
                        "  });",
                        "",
                    ]
                )
        if permission_case:
            permission_code = str(permission_case.get("error_code", "")).strip()
            permission_status = str(permission_case.get("status", "")).strip() or "403"
            lines.extend(
                [
                    f'  it("{operation_id} service enforces permission and tenant boundary", async () => {{',
                    f"    const service = new {service_class}();",
                    f'    const error = await captureApiError(service.{method_name}(buildFailurePayload("{operation_id}", "{permission_code}")));',
                    f"    expect(error.status).toBe({permission_status});",
                    f'    expect(error.envelope.error_code).toBe("{permission_code}");',
                    "  });",
                    "",
                ]
            )
            operation_semantics = (
                behavior_model.get("operation_semantics", {})
                if isinstance(behavior_model, dict) and isinstance(behavior_model.get("operation_semantics"), dict)
                else {}
            )
            owner_service = str(operation_semantics.get("owner_service") or "").strip()
            semantic_status = str(operation_semantics.get("status") or "").strip()
            if owner_service and semantic_status in {"resolved", ""}:
                lines.extend(
                    [
                        f'  it("{operation_id} service rejects wrong semantic owner before repository access", async () => {{',
                        "    const repository = {",
                        f"      load{camel_case(operation_id)}ForDecision: vi.fn(async (context: Record<string, unknown>) => context),",
                        f"      persist{camel_case(operation_id)}WithInvariants: vi.fn(async () => undefined),",
                        f"      append{camel_case(operation_id)}AuditEffect: vi.fn(async () => undefined),",
                        f"    }} as unknown as {repository_class};",
                        f"    const service = new {service_class}(repository);",
                        f'    const error = await captureApiError(service.{method_name}({{ ...{payload_expr}, expectedOwnerService: "OtherService" }}));',
                        f"    expect(error.status).toBe({permission_status});",
                        f'    expect(error.envelope.error_code).toBe("{permission_code}");',
                        f"    expect(repository.load{camel_case(operation_id)}ForDecision).not.toHaveBeenCalled();",
                        *([] if is_read_operation else [
                            f"    expect(repository.persist{camel_case(operation_id)}WithInvariants).not.toHaveBeenCalled();",
                            f"    expect(repository.append{camel_case(operation_id)}AuditEffect).not.toHaveBeenCalled();",
                        ]),
                        "  });",
                        "",
                    ]
                )
        if conflict_case and str(conflict_case.get("error_code", "")).strip() == "version_conflict":
            conflict_status = str(conflict_case.get("status", "")).strip() or "409"
            if not is_read_operation:
                lines.extend(
                    [
                        f'  it("{operation_id} service rejects stale repository versions before persistence", async () => {{',
                        "    const repository = {",
                        f"      load{camel_case(operation_id)}ForDecision: vi.fn(async (context: Record<string, unknown>) => ({{ ...context, expectedVersion: 2 }})),",
                        f"      persist{camel_case(operation_id)}WithInvariants: vi.fn(async () => undefined),",
                        f"      append{camel_case(operation_id)}AuditEffect: vi.fn(async () => undefined),",
                        f"    }} as unknown as {repository_class};",
                        f"    const service = new {service_class}(repository);",
                        f"    const stalePayload = {{ ...{payload_expr}, expectedVersion: 1, expected_version: 1 }};",
                        f"    const error = await captureApiError(service.{method_name}(stalePayload));",
                        f"    expect(error.status).toBe({conflict_status});",
                        '    expect(error.envelope.error_code).toBe("version_conflict");',
                        f"    expect(repository.persist{camel_case(operation_id)}WithInvariants).not.toHaveBeenCalled();",
                        f"    expect(repository.append{camel_case(operation_id)}AuditEffect).not.toHaveBeenCalled();",
                        "  });",
                        "",
                    ]
                )
        state_data_expr = "(data[0] as Record<string, unknown>)" if response_data_is_array(spec) else "data"
        state_assertions = unit_business_assertion_lines(state_data_expr, spec)
        if state_assertions:
            lines.extend(
                [
                    f'  it("{operation_id} service preserves state transition", async () => {{',
                    "    const repository = {",
                    f"      load{camel_case(operation_id)}ForDecision: vi.fn(async (context: Record<string, unknown>) => ({{ ...context, expectedVersion: context.expectedVersion ?? context.expected_version }})),",
                    *([] if is_read_operation else [
                        f"      persist{camel_case(operation_id)}WithInvariants: vi.fn(async () => undefined),",
                        f"      append{camel_case(operation_id)}AuditEffect: vi.fn(async () => undefined),",
                    ]),
                    f"    }} as unknown as {repository_class};",
                    f"    const service = new {service_class}(repository);",
                    f'    const result = await service.{method_name}({payload_expr}) as Record<string, unknown>;',
                    f"    const data = extractEnvelopeData<{data_type}>(result);",
                    *state_assertions,
                    *(
                        [f"    expect(repository.load{camel_case(operation_id)}ForDecision).toHaveBeenCalled();"]
                        if is_read_operation
                        else [f"    expect(repository.persist{camel_case(operation_id)}WithInvariants).toHaveBeenCalled();"]
                    ),
                    "  });",
                    "",
                ]
            )
        error_mapping_case = conflict_case or first_failure_case(spec)
        if error_mapping_case:
            error_code = str(error_mapping_case.get("error_code", "")).strip()
            error_status = str(error_mapping_case.get("status", "")).strip() or "400"
            lines.extend(
                [
                    f'  it("{operation_id} service maps errors to envelope semantics", async () => {{',
                    f"    const service = new {service_class}();",
                    f'    const error = await captureApiError(service.{method_name}(buildFailurePayload("{operation_id}", "{error_code}")));',
                    f"    expect(error.status).toBe({error_status});",
                    f'    expect(error.envelope.error_code).toBe("{error_code}");',
                    "  });",
                    "",
                ]
            )
        failure_case = first_failure_case(spec)
        if failure_case:
            failure_code = str(failure_case.get("error_code", "")).strip()
            failure_status = str(failure_case.get("status", "")).strip()
            lines.extend(
                [
                    f'  it("{operation_id} service surfaces business error semantics", async () => {{',
                    f"    const service = new {service_class}();",
                    f'    const error = await captureApiError(service.{method_name}(buildFailurePayload("{operation_id}", "{failure_code}")));',
                    f"    expect(error.status).toBe({failure_status or '400'});",
                    f'    expect(error.envelope.error_code).toBe("{failure_code}");',
                    "  });",
                    "",
                ]
            )
        repository_error_cases = [
            failure
            for failure in (not_found_case, conflict_case, db_error_case)
            if failure and str(failure.get("error_code", "")).strip()
        ]
        if repository_error_cases:
            lines.extend(
                [
                    f'  it("{operation_id} repository covers not-found, duplicate, and db error translation", async () => {{',
                    f"    const repository = new {repository_class}();",
                ]
            )
            for failure in repository_error_cases:
                failure_code = str(failure.get("error_code", "")).strip()
                failure_status = str(failure.get("status", "")).strip() or "400"
                lines.extend(
                    [
                        f'    const {lower_camel(failure_code)} = await captureApiError(repository.{method_name}(buildFailurePayload("{operation_id}", "{failure_code}")));',
                        f"    expect({lower_camel(failure_code)}.status).toBe({failure_status});",
                        f'    expect({lower_camel(failure_code)}.envelope.error_code).toBe("{failure_code}");',
                    ]
                )
            lines.extend(
                [
                    "  });",
                    "",
                ]
            )
    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def render_backend_foundation_unit_test(operation_specs: dict[str, dict[str, Any]]) -> str:
    operation_ids = sorted(str(operation_id).strip() for operation_id in operation_specs if str(operation_id).strip())
    sample_operation_id = operation_ids[0] if operation_ids else ""
    create_like_operation_id = next(
        (
            operation_id
            for operation_id in operation_ids
            if operation_execution_mode(operation_specs.get(operation_id, {})) == "create"
        ),
        sample_operation_id,
    )
    failure_code = "validation_failed"
    if create_like_operation_id:
        failure_cases = operation_specs.get(create_like_operation_id, {}).get("failureCases", [])
        if isinstance(failure_cases, list):
            for entry in failure_cases:
                if not isinstance(entry, dict):
                    continue
                candidate = str(entry.get("error_code", "")).strip()
                if candidate:
                    failure_code = candidate
                    break

    lines = [
        'import { beforeEach, describe, expect, it } from "vitest";',
        'import { issueAuthToken, issueRefreshToken, normalizeAuthSession, parseAuthorizationHeader, requireRbacRole, rotateRefreshToken } from "../../../../apps/api/src/common/auth-session";',
        'import { buildCursorMeta } from "../../../../apps/api/src/common/pagination";',
        'import { appendEnvelopeMeta, annotateRuntimePayload, normalizeGeneratedPayload } from "../../../../apps/api/src/common/runtime-adapter";',
        'import { buildOperationPlan, getOperationSpec } from "../../../../apps/api/src/common/operation-support";',
        'import { buildFailurePayload, buildOperationPayload, normalizeIdValue, resetGeneratedRuntime } from "../../../../apps/api/src/common/generated-runtime";',
        'import { checkDatabaseReadiness, runMigrations } from "../../../../apps/api/src/runtime/database";',
        "",
        'describe("phase3 api foundation unit", () => {',
        "  beforeEach(() => {",
        "    resetGeneratedRuntime();",
        "    delete process.env.DATABASE_URL;",
        '    process.env.AUTH_TOKEN_SECRET = "phase3-foundation-secret";',
        "  });",
        "",
        '  it("auth session helpers issue bearer tokens and normalize fallback claims", () => {',
        "    const token = issueAuthToken({",
        '      tenant_id: "tenant-001",',
        '      sub: "user-001",',
        '      sid: "sess-001",',
        '      role: "tenant_admin",',
        "    });",
        "    const parsed = parseAuthorizationHeader(`Bearer ${token}`);",
        '    const session = normalizeAuthSession(parsed, "tenant-fallback");',
        '    expect(session.tenant_id).toBe("tenant-001");',
        '    expect(session.subject_id).toBe("user-001");',
        '    expect(session.session_id).toBe("sess-001");',
        '    expect(session.roles).toEqual(["tenant_admin"]);',
        '    requireRbacRole(session, "tenant_admin");',
        "  });",
        "",
        '  it("auth session helpers enforce token lifecycle and refresh rotation", () => {',
        "    const accessToken = issueAuthToken({",
        '      tenant_id: "tenant-001",',
        '      sub: "user-001",',
        '      sid: "sess-001",',
        '      role: "tenant_admin",',
        "    });",
        "    const accessClaims = parseAuthorizationHeader(`Bearer ${accessToken}`);",
        "    expect(accessClaims.token_use).toBe('access');",
        "    expect(Number(accessClaims.exp) - Number(accessClaims.iat)).toBe(15 * 60);",
        "    const refreshToken = issueRefreshToken({",
        '      tenant_id: "tenant-001",',
        '      sub: "user-001",',
        '      sid: "sess-001",',
        '      role: "tenant_admin",',
        "    });",
        "    const refreshClaims = parseAuthorizationHeader(`Bearer ${refreshToken}`);",
        "    expect(refreshClaims.token_use).toBe('refresh');",
        "    expect(Number(refreshClaims.exp) - Number(refreshClaims.iat)).toBe(8 * 60 * 60);",
        "    expect(refreshClaims.refresh_token_family_id).toBe('refresh-family-sess-001');",
        "    expect(refreshClaims.rotation_counter).toBe(0);",
        "    const rotatedToken = rotateRefreshToken(refreshClaims);",
        "    const rotatedClaims = parseAuthorizationHeader(`Bearer ${rotatedToken}`);",
        "    expect(rotatedClaims.refresh_token_family_id).toBe(refreshClaims.refresh_token_family_id);",
        "    expect(rotatedClaims.rotation_counter).toBe(1);",
        "  });",
        "",
        '  it("auth session helpers reject invalid bearer inputs and missing roles", () => {',
        '    expect(() => parseAuthorizationHeader("Basic token")).toThrow(/bearer token|missing_bearer_token/i);',
        '    expect(() => normalizeAuthSession({ sub: "user-001" }, "tenant-fallback")).toThrow(/tenant\\/session claims are missing|invalid_auth_context/i);',
        '    const session = normalizeAuthSession({ tenantId: "tenant-fallback", sub: "user-001", sid: "sess-001", role: "tenant_admin" }, "tenant-fallback");',
        '    expect(() => requireRbacRole(session, "vet_staff")).toThrow(/Missing role|rbac_forbidden/i);',
        "  });",
        "",
        '  it("runtime payload helpers normalize aliases without clobbering explicit values", () => {',
        "    const normalized = normalizeGeneratedPayload({",
        '      body: { appointmentId: "appointment-001" },',
        '      query: { cursor: "cursor-001" },',
        '      input: { nested: { paymentId: "payment-001" } },',
        '      pathParams: { appointmentId: "appointment-001" },',
        '      authContext: { tenant_id: "tenant-001" },',
        "    });",
        '    expect(normalized.appointmentId).toBe("appointment-001");',
        '    expect(normalized.cursor).toBe("cursor-001");',
        '    expect(normalized.paymentId).toBe("payment-001");',
        '    expect(normalized.path_params).toEqual({ appointmentId: "appointment-001" });',
        '    expect(normalized.auth_context).toEqual({ tenant_id: "tenant-001" });',
        "    const annotated = annotateRuntimePayload(",
        '      { body: { appointmentId: "appointment-001" } },',
        '      { appointmentId: "keep-explicit", force_error_code: "validation_failed" },',
        "    );",
        '    expect(annotated.appointmentId).toBe("appointment-001");',
        '    expect(annotated.force_error_code).toBe("validation_failed");',
        '    const envelope = appendEnvelopeMeta({ data: { ok: true }, meta: { traceId: "trace-001" } }, { traceId: "trace-override", requestId: "req-001" });',
        '    expect(envelope.meta).toEqual({ traceId: "trace-001", requestId: "req-001" });',
        "  });",
        "",
        '  it("pagination helper mirrors camel and snake cursor metadata", () => {',
        '    const meta = buildCursorMeta([1, 2], { next_cursor: "cursor-002" });',
        '    expect(meta.nextCursor).toBe("cursor-002");',
        '    expect(meta.next_cursor).toBe("cursor-002");',
        '    expect(meta.returnedCount).toBe(2);',
        '    expect(meta.returned_count).toBe(2);',
        '    const emptyMeta = buildCursorMeta([], {}, "cursor-005");',
        '    expect(emptyMeta.nextCursor).toBe("cursor-005");',
        '    expect(emptyMeta.next_cursor).toBe("cursor-005");',
        '    expect(emptyMeta.returnedCount).toBe(0);',
        '    expect(emptyMeta.returned_count).toBe(0);',
        '    const camelOnlyMeta = buildCursorMeta([], { nextCursor: "cursor-003", returnedCount: 0 });',
        '    expect(camelOnlyMeta.next_cursor).toBe("cursor-003");',
        '    expect(camelOnlyMeta.returned_count).toBe(0);',
        '    const snakeOnlyMeta = buildCursorMeta([], { next_cursor: "cursor-004", returned_count: 0 });',
        '    expect(snakeOnlyMeta.nextCursor).toBe("cursor-004");',
        '    expect(snakeOnlyMeta.returnedCount).toBe(0);',
        "  });",
        "",
        '  it("database helpers fail fast when runtime configuration is missing", async () => {',
        '    await expect(checkDatabaseReadiness()).resolves.toEqual({ ready: false, reason: "database_url_missing" });',
        '    await expect(runMigrations(["select 1"])).rejects.toThrow(/DATABASE_URL is required/);',
        "  });",
        "",
    ]
    if sample_operation_id:
        lines.extend(
            [
                '  it("operation support helpers expose stable specs and deterministic payload seeds", () => {',
                f'    const spec = getOperationSpec("{sample_operation_id}");',
                f'    const payload = buildOperationPayload("{sample_operation_id}");',
                f'    const failurePayload = buildFailurePayload("{create_like_operation_id}", "{failure_code}");',
                '    const plan = buildOperationPlan({ operation_id: spec.operationId, execution_mode: "create", module_slug: spec.tag });',
                f'    expect(spec.operationId).toBe("{sample_operation_id}");',
                '    expect(payload).toHaveProperty("auth_context");',
                '    expect(payload).toHaveProperty("path_params");',
                '    expect(failurePayload).toHaveProperty("auth_context");',
                '    expect(plan).toEqual({ operation_id: spec.operationId, execution_mode: "create", module_slug: spec.tag });',
                '    expect(normalizeIdValue("tenant_id", "tenant-demo")).not.toBe("tenant-demo");',
                '    expect(normalizeIdValue("display_name", "front desk")).toBe("front desk");',
                "  });",
                "",
            ]
        )
    lines.extend(["});", ""])
    return "\n".join(lines)

def _comment_fragment(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().replace("*/", "")


def _match_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def synthesis_units_for_module(
    synthesis_brief: dict[str, Any] | None,
    *,
    module_slug: str,
    operations: list[dict[str, str]],
) -> list[dict[str, Any]]:
    if not isinstance(synthesis_brief, dict):
        return []
    operation_ids = {
        _match_key(operation.get("operation_id") or f"{operation.get('method', '')}-{operation.get('path', '')}")
        for operation in operations
    }
    module_marker = f"/modules/{module_slug}/"
    selected: list[dict[str, Any]] = []
    units = synthesis_brief.get("selected_semantic_units", [])
    if not isinstance(units, list):
        return []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        operation_id = _match_key(unit.get("operation_id", ""))
        subject_key = _match_key(unit.get("source_subject", ""))
        intent_key = _match_key(unit.get("implementation_semantic_intent", ""))
        implementation_targets = [str(target).strip().lower() for target in unit.get("implementation_targets", []) if str(target).strip()]
        test_targets = [str(target).strip().lower() for target in unit.get("test_targets", []) if str(target).strip()]
        target_matches = any(module_marker in f"/{target}" for target in [*implementation_targets, *test_targets])
        operation_matches = bool(operation_id and operation_id in operation_ids)
        subject_matches = any(operation_id and (operation_id in subject_key or operation_id in intent_key) for operation_id in operation_ids)
        if target_matches or operation_matches or subject_matches:
            selected.append(unit)
    return selected[:3]


def render_synthesis_intent_comment_lines(synthesis_units: list[dict[str, Any]] | None) -> list[str]:
    if not synthesis_units:
        return []
    lines = ["// Phase3 pre-generation synthesis boundary"]
    for unit in synthesis_units:
        source_id = _comment_fragment(unit.get("source_id", "unidentified-source")) or "unidentified-source"
        subject = _comment_fragment(unit.get("source_subject", "unknown subject")) or "unknown subject"
        intent = _comment_fragment(unit.get("implementation_semantic_intent", "preserve source-bound intent"))
        lines.append(f"// Synthesis intent [{source_id}]: {subject} | {intent}")
    return lines


def service_body_authoring_replacement(
    authoring_packet: dict[str, Any] | None,
    operation_id: str,
) -> str:
    if not isinstance(authoring_packet, dict):
        return ""
    if str(authoring_packet.get("mode") or "").strip() != "bounded-agentic-service-body":
        return ""
    operations = authoring_packet.get("operations")
    if not isinstance(operations, dict):
        return ""
    entry = operations.get(operation_id)
    if not isinstance(entry, dict):
        return ""
    replacement = str(entry.get("replacement_body") or "").strip("\n")
    if not replacement.strip():
        return ""
    non_comment_lines = [
        line
        for line in replacement.splitlines()
        if line.strip() and not line.strip().startswith("//")
    ]
    if not non_comment_lines:
        return ""
    return replacement


def agentic_body_authoring_model_for_operation(operation: dict[str, str], spec: dict[str, Any]) -> dict[str, Any]:
    operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
    execution_mode = operation_execution_mode(spec)
    request_fields = [
        str(field).strip()
        for field in spec.get("requestRequiredFields", [])
        if str(field).strip()
    ] if isinstance(spec.get("requestRequiredFields", []), list) else []
    response_fields = list(response_example_data(spec)[0].keys()) if response_data_is_array(spec) and response_example_data(spec) else (
        list(response_example_data(spec).keys()) if isinstance(response_example_data(spec), dict) else []
    )
    failure_cases = spec.get("failureCases", []) if isinstance(spec.get("failureCases", []), list) else []
    failure_codes = [
        str(item.get("error_code", "")).strip()
        for item in failure_cases
        if isinstance(item, dict) and str(item.get("error_code", "")).strip()
    ]
    for required_code in ("invalid_request", "version_conflict"):
        if required_code not in failure_codes:
            failure_codes.append(required_code)
    entity = singularize_token(stable_slug(str(spec.get("tag") or operation.get("tag") or "operation"), fallback="operation"))
    aggregate = camel_case(entity)
    owner_service = f"{aggregate}Service"
    persistence_surface = entity or snake_case(operation_id) or "operation_record"
    idempotency_rule = str(spec.get("idempotencyRule") or "").strip()
    retryability_policy = str(spec.get("retryabilityPolicy") or "").strip()
    state_transition = (
        "read-only projection preserves durable state"
        if execution_mode in {"detail-read", "list-read"}
        else f"{aggregate} draft -> active when {operation_id} succeeds"
    )
    persistence_effects = (
        "read-only runtime bridge, no durable mutation"
        if execution_mode in {"detail-read", "list-read"}
        else f"{persistence_surface}, audit_events"
    )
    invariants = ", ".join(
        item
        for item in [
            "preserve tenant boundary" if any("tenant" in field.lower() for field in request_fields + response_fields) else "",
            "required contract fields before repository access" if request_fields else "",
            "expected_version conflict guard" if any("version" in field.lower() for field in request_fields + response_fields) else "",
            idempotency_rule,
        ]
        if item
    ) or "preserve operation contract and source-backed runtime evidence"
    evidence_keys = [
        field
        for field in [operation_primary_record_hint(spec), *response_fields, *request_fields, "trace_id"]
        if field
    ][:6]
    return {
        "operation_id": operation_id,
        "upstream_trace_ids": [],
        "steps": [
            {"id": "step-1", "title": f"Receive {operation_id} and preserve caller trace context."},
            {"id": "step-2", "title": "Validate contract fields and business context before repository access."},
            {"id": "step-3", "title": "Load current runtime evidence needed for an honest decision."},
            {"id": "step-4", "title": "Apply operation-specific state, read-only, or conflict policy."},
            {"id": "step-5", "title": "Persist or read back through the runtime bridge with evidence."},
            {"id": "step-6", "title": "Return the frozen response envelope and declared failure semantics."},
        ],
        "error_codes": failure_codes,
        "business_intent": str(spec.get("purpose") or f"Execute {operation_id}").strip(),
        "execution_mode": execution_mode,
        "operation_semantics": {
            "status": "resolved",
            "owner_service": owner_service,
            "aggregate": aggregate,
            "state_set": ["active"] if execution_mode not in {"detail-read", "list-read"} else [],
            "trigger_events": [f"{operation_id}Completed"] if execution_mode not in {"detail-read", "list-read"} else [],
            "mutation_guard": invariants,
            "terminal_or_failure_exit": retryability_policy or "declared failure mapping",
            "readonly_dependencies": evidence_keys if execution_mode in {"detail-read", "list-read"} else [],
            "evidence_keys": evidence_keys,
        },
        "persistence_effects": persistence_effects,
        "invariants": invariants,
        "state_transition": state_transition,
        "transaction_rule": idempotency_rule or "runtime bridge with independent read-back evidence",
        "audit_effect": f"append {snake_case(operation_id)} audit event" if execution_mode not in {"detail-read", "list-read"} else "no mutation audit event",
        "agentic_body_authoring_mode": "default-p3-mainline",
    }


def business_behavior_plan_entry_to_authoring_model(plan_entry: dict[str, Any], *, operation: dict[str, str], spec: dict[str, Any]) -> dict[str, Any]:
    operation_id = str(
        plan_entry.get("operation_id")
        or operation.get("operation_id")
        or spec.get("operationId")
        or f"{operation.get('method', '')}-{operation.get('path', '')}"
    ).strip()
    state_policy = plan_entry.get("state_conflict_policy") if isinstance(plan_entry.get("state_conflict_policy"), dict) else {}
    repository_effect = plan_entry.get("repository_effect") if isinstance(plan_entry.get("repository_effect"), dict) else {}
    audit_effect = plan_entry.get("audit_or_event_effect") if isinstance(plan_entry.get("audit_or_event_effect"), dict) else {}
    semantic_owner = plan_entry.get("semantic_owner") if isinstance(plan_entry.get("semantic_owner"), dict) else {}
    read_write = plan_entry.get("read_write_semantics") if isinstance(plan_entry.get("read_write_semantics"), dict) else {}
    unit_obligations = plan_entry.get("unit_test_obligations") if isinstance(plan_entry.get("unit_test_obligations"), dict) else {}
    response_mapping = plan_entry.get("response_mapping") if isinstance(plan_entry.get("response_mapping"), dict) else {}
    execution_mode = str(plan_entry.get("execution_mode") or spec.get("executionMode") or "").strip() or operation_execution_mode(spec)
    source_refs = _unique_nonempty_strings(_listish(plan_entry.get("source_refs")))
    error_codes = _unique_nonempty_strings(
        _listish(state_policy.get("error_codes"))
        + _listish(unit_obligations.get("failure_codes"))
        + [
            item.get("error_code")
            for item in spec.get("failureCases", [])
            if isinstance(item, dict)
        ]
    )
    if "invalid_request" not in error_codes:
        error_codes.append("invalid_request")
    evidence_keys = _unique_nonempty_strings(
        _listish(semantic_owner.get("evidence_keys"))
        + _listish(response_mapping.get("fields"))
        + _listish(unit_obligations.get("assert_business_fields"))
        + ["trace_id"]
    )
    persistence_terms = []
    if repository_effect.get("decision_load"):
        persistence_terms.append("decision load")
    if repository_effect.get("invariant_persistence"):
        persistence_terms.append("invariant persistence")
    if repository_effect.get("read_back"):
        persistence_terms.append("independent read-back")
    if repository_effect.get("runtime_bridge"):
        persistence_terms.append("runtime bridge")
    if repository_effect.get("durable_mutation") is False or read_write.get("read_only") is True:
        persistence_terms.append("no durable mutation")
    persistence_effects = ", ".join(persistence_terms) or str(read_write.get("mutation") or "runtime bridge")
    return {
        "operation_id": operation_id,
        "upstream_trace_ids": source_refs,
        "steps": [
            {"id": "step-1", "title": f"Receive {operation_id} and preserve caller trace context."},
            {"id": "step-2", "title": "Validate required business context from the source-backed authoring plan before repository access."},
            {"id": "step-3", "title": "Load current aggregate or projection evidence needed for the planned decision."},
            {"id": "step-4", "title": str(state_policy.get("state_transition") or "Apply source-backed state, read-only, or conflict policy.").strip()},
            {"id": "step-5", "title": str(audit_effect.get("effect") or "Persist/read back through the runtime bridge with evidence.").strip()},
            {"id": "step-6", "title": "Return the frozen response envelope and declared failure semantics."},
        ],
        "error_codes": error_codes,
        "business_intent": str(plan_entry.get("behavior_intent") or spec.get("purpose") or f"Execute {operation_id}").strip(),
        "execution_mode": execution_mode,
        "operation_semantics": {
            "status": "resolved",
            "owner_service": str(semantic_owner.get("owner_service") or "").strip(),
            "aggregate": str(semantic_owner.get("aggregate") or "").strip(),
            "state_set": _unique_nonempty_strings(_listish(semantic_owner.get("state_set"))),
            "trigger_events": _unique_nonempty_strings(_listish(audit_effect.get("trigger_events"))),
            "mutation_guard": str(semantic_owner.get("mutation_guard") or plan_entry.get("invariants") or "").strip(),
            "terminal_or_failure_exit": "declared failure mapping",
            "readonly_dependencies": _unique_nonempty_strings(_listish(semantic_owner.get("readonly_dependencies"))),
            "evidence_keys": evidence_keys,
        },
        "persistence_effects": persistence_effects,
        "invariants": str(plan_entry.get("invariants") or semantic_owner.get("mutation_guard") or "business invariants").strip(),
        "state_transition": str(state_policy.get("state_transition") or "").strip(),
        "transaction_rule": "source-backed runtime bridge with independent read-back evidence",
        "audit_effect": str(audit_effect.get("effect") or ("no mutation audit event" if execution_mode in {"detail-read", "list-read"} else f"append {snake_case(operation_id)} audit event")).strip(),
        "agentic_body_authoring_mode": "default-p3-mainline",
        "business_behavior_authoring_plan_kind": "phase3-business-behavior-authoring-plan.v1",
    }


def agentic_body_authoring_model(
    operation: dict[str, str],
    *,
    operation_specs: dict[str, dict[str, Any]] | None,
    behavior_card_models: dict[str, dict[str, Any]] | None,
    business_behavior_authoring_plan: dict[str, Any] | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    module_implementation_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
    spec = runtime_spec_for_operation(operation, operation_specs or {})
    decision = agentic_semantic_decision_for_operation(agentic_semantic_decisions, operation_id)
    plan_entry = business_behavior_authoring_plan_for_operation(business_behavior_authoring_plan, operation_id)
    if plan_entry:
        return apply_module_implementation_brief_to_model(
            apply_agentic_semantic_decision_to_model(
                business_behavior_plan_entry_to_authoring_model(plan_entry, operation=operation, spec=spec),
                decision,
            ),
            module_implementation_brief,
            operation_id,
        )
    behavior_model = (behavior_card_models or {}).get(operation_id)
    if behavior_model:
        return apply_module_implementation_brief_to_model(
            apply_agentic_semantic_decision_to_model(behavior_model, decision),
            module_implementation_brief,
            operation_id,
        )
    return apply_module_implementation_brief_to_model(
        apply_agentic_semantic_decision_to_model(
            agentic_body_authoring_model_for_operation(
                operation,
                spec,
            ),
            decision,
        ),
        module_implementation_brief,
        operation_id,
    )


def render_controller_module(module_class: str, operations: list[dict[str, str]], module_slug: str) -> str:
    lines = [
        'import { annotateRuntimePayload, normalizeGeneratedPayload, type GeneratedRuntimePayload, type GeneratedRuntimeResult } from "../../common/runtime-adapter.js";',
        f'import {{ {module_class}Service }} from "./{module_slug}.service.js";',
        "",
        f"export class {module_class}Controller {{",
        f"  constructor(private readonly service = new {module_class}Service()) {{}}",
        "",
    ]
    for operation in operations:
        operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
        method_name = lower_camel(operation_id)
        lines.extend(
            [
                f"  async {method_name}(payload: GeneratedRuntimePayload): Promise<GeneratedRuntimeResult> {{",
                f'    const request = annotateRuntimePayload(payload, {{ controller_module: "{module_slug}", operation_id: "{operation_id}" }});',
                "    const normalized = normalizeGeneratedPayload(request);",
                '    normalized.request_origin = normalized.request_origin ?? "controller";',
                f"    const result = await this.service.{method_name}(normalized);",
                "    return result;",
                "  }",
                "",
            ]
        )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def render_service_module(
    module_class: str,
    operations: list[dict[str, str]],
    module_slug: str,
    *,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
    operation_specs: dict[str, dict[str, Any]] | None = None,
    synthesis_units: list[dict[str, Any]] | None = None,
    authoring_packet: dict[str, Any] | None = None,
    business_behavior_authoring_plan: dict[str, Any] | None = None,
    action_card_execution_map: dict[str, Any] | None = None,
    action_card_direct_implementation_driver: dict[str, Any] | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    module_implementation_briefs: dict[str, Any] | None = None,
) -> str:
    fallback_operations = [
        operation
        for operation in operations
        if not (behavior_card_models or {}).get(operation["operation_id"] or f"{operation['method']}-{operation['path']}")
    ]
    _ = fallback_operations
    lines = ['import { type GeneratedRuntimePayload, type GeneratedRuntimeResult } from "../../common/runtime-adapter.js";']
    packet_requires_api_error = any(
        "createApiError" in service_body_authoring_replacement(
            authoring_packet,
            operation["operation_id"] or f"{operation['method']}-{operation['path']}",
        )
        for operation in operations
    )
    if operations or packet_requires_api_error:
        lines.append('import { createApiError } from "../../common/errors.js";')
    lines.append(f'import {{ {module_class}Repository }} from "./{module_slug}.repository.js";')
    lines.append("")
    lines.append("// agentic-body-authoring-kernel: default-p3-mainline")
    module_implementation_brief = module_implementation_brief_for_module(module_implementation_briefs, module_slug)
    if module_implementation_brief:
        lines.append(f"// agentic-module-implementation-brief: {module_slug}")
        renderer_notes = (
            module_implementation_brief.get("renderer_notes")
            if isinstance(module_implementation_brief.get("renderer_notes"), dict)
            else {}
        )
        renderer_role = str(renderer_notes.get("renderer_role") or "").strip()
        if renderer_role:
            lines.append(f"// renderer-role: {renderer_role}")
    synthesis_comment_lines = render_synthesis_intent_comment_lines(synthesis_units)
    if synthesis_comment_lines:
        lines.extend(synthesis_comment_lines)
        lines.append("")
    lines.extend(
        [
            f"export class {module_class}Service {{",
            f"  constructor(private readonly repository = new {module_class}Repository()) {{}}",
            "",
        ]
    )
    for operation in operations:
        operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
        method_name = lower_camel(operation_id)
        action_card_entry = action_card_execution_map_for_operation(action_card_execution_map, operation_id)
        action_card_driver_operation = action_card_direct_driver_for_operation(
            action_card_direct_implementation_driver,
            operation_id,
        )
        behavior_model = (behavior_card_models or {}).get(operation_id)
        authored_body = service_body_authoring_replacement(authoring_packet, operation_id)
        if authored_body:
            action_card_trace_lines = render_action_card_trace_comment_lines(action_card_entry)
            if action_card_trace_lines:
                lines.extend(action_card_trace_lines)
            lines.extend(
                [
                    f"  async {method_name}(payload: GeneratedRuntimePayload): Promise<GeneratedRuntimeResult> {{",
                    authored_body,
                    "  }",
                    "",
                ]
            )
            continue
        plan_entry = business_behavior_authoring_plan_for_operation(business_behavior_authoring_plan, operation_id)
        operation_spec = operation_spec_with_business_behavior_plan((operation_specs or {}).get(operation_id, {}), plan_entry)
        body_model = agentic_body_authoring_model(
            operation,
            operation_specs={**(operation_specs or {}), operation_id: operation_spec},
            behavior_card_models=behavior_card_models,
            business_behavior_authoring_plan=business_behavior_authoring_plan,
            agentic_semantic_decisions=agentic_semantic_decisions,
            module_implementation_brief=module_implementation_brief,
        )
        body_model = apply_action_card_driver_to_model(body_model, action_card_driver_operation)
        plan = render_service_implementation_plan(body_model, module_class=module_class, operation_spec=operation_spec)
        body = plan[plan.find("{") + 1 : plan.rfind("}")].strip("\n")
        action_card_trace_lines = render_action_card_trace_comment_lines(action_card_entry)
        if action_card_trace_lines:
            lines.extend(action_card_trace_lines)
        action_card_direct_lines = render_action_card_direct_service_comment_lines(action_card_driver_operation)
        if action_card_direct_lines:
            lines.extend(action_card_direct_lines)
        lines.extend([body, ""])
    lines.append("}")
    lines.append("")
    return collapse_service_mechanical_helpers("\n".join(lines))


def render_repository_module(
    module_class: str,
    operations: list[dict[str, str]],
    module_slug: str,
    operation_specs: dict[str, dict[str, Any]],
    *,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
    business_behavior_authoring_plan: dict[str, Any] | None = None,
    action_card_execution_map: dict[str, Any] | None = None,
    action_card_direct_implementation_driver: dict[str, Any] | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    module_implementation_briefs: dict[str, Any] | None = None,
) -> str:
    execution_handler_by_mode = {
        "create": "executeCreateOperation",
        "detail-read": "executeDetailReadOperation",
        "list-read": "executeListReadOperation",
        "command": "executeCommandOperation",
    }
    planned_operation_specs = {
        (operation["operation_id"] or f"{operation['method']}-{operation['path']}"): operation_spec_with_business_behavior_plan(
            runtime_spec_for_operation(operation, operation_specs),
            business_behavior_authoring_plan_for_operation(
                business_behavior_authoring_plan,
                operation["operation_id"] or f"{operation['method']}-{operation['path']}",
            ),
        )
        for operation in operations
    }
    behavior_operations = list(operations)
    fallback_operations: list[dict[str, str]] = []
    runtime_bound_operations = behavior_operations
    used_handlers = [
        execution_handler_by_mode[mode]
        for mode in ("create", "detail-read", "list-read", "command")
        if any(
            operation_execution_mode(planned_operation_specs.get(operation["operation_id"] or f"{operation['method']}-{operation['path']}", runtime_spec_for_operation(operation, operation_specs))) == mode
            for operation in runtime_bound_operations
        )
    ]
    operation_support_imports = ", ".join(["buildOperationPlan", *used_handlers, "getOperationSpec"]) if runtime_bound_operations else ""
    module_implementation_brief = module_implementation_brief_for_module(module_implementation_briefs, module_slug)
    lines = []
    if fallback_operations:
        lines.append(
            'import { annotateRuntimePayload, normalizeGeneratedPayload, type GeneratedRuntimePayload, type GeneratedRuntimeResult } from "../../common/runtime-adapter.js";'
        )
    if operation_support_imports:
        lines.append(f'import {{ {operation_support_imports} }} from "../../common/operation-support.js";')
    lines.extend([
        "",
        "// agentic-body-authoring-kernel: default-p3-mainline",
        *([f"// agentic-module-implementation-brief: {module_slug}"] if module_implementation_brief else []),
        f"export class {module_class}Repository {{",
    ])
    for operation in operations:
        operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
        method_name = lower_camel(operation_id)
        action_card_entry = action_card_execution_map_for_operation(action_card_execution_map, operation_id)
        action_card_driver_operation = action_card_direct_driver_for_operation(
            action_card_direct_implementation_driver,
            operation_id,
        )
        behavior_model = agentic_body_authoring_model(
            operation,
            operation_specs={**operation_specs, operation_id: planned_operation_specs.get(operation_id, runtime_spec_for_operation(operation, operation_specs))},
            behavior_card_models=behavior_card_models,
            business_behavior_authoring_plan=business_behavior_authoring_plan,
            agentic_semantic_decisions=agentic_semantic_decisions,
            module_implementation_brief=module_implementation_brief,
        )
        behavior_model = apply_action_card_driver_to_model(behavior_model, action_card_driver_operation)
        spec = planned_operation_specs.get(operation_id, runtime_spec_for_operation(operation, operation_specs))
        execution_mode = operation_execution_mode(spec)
        plan = render_repository_invariant_plan(behavior_model, module_class=module_class)
        body = plan[plan.find("{") + 1 : plan.rfind("}")].strip("\n")
        helper_start = body.find("\n\n  private async transaction(")
        write_start = body.find("\n\n  private async write", helper_start + 1) if helper_start >= 0 else -1
        action_card_trace_lines = render_action_card_trace_comment_lines(action_card_entry)
        action_card_direct_lines = render_action_card_direct_repository_comment_lines(action_card_driver_operation)
        if helper_start >= 0 and write_start > helper_start:
            operation_body = body[:helper_start].rstrip()
            transaction_body = body[helper_start:write_start].strip("\n")
            write_body = body[write_start:].strip("\n")
            handler_name = execution_handler_by_mode[execution_mode]
            record_hint = operation_primary_record_hint(spec)
            uniqueness_blob = json.dumps(operation_uniqueness_hint_fields(spec), ensure_ascii=False)
            runtime_bridge = "\n".join([
                f'  private async execute{camel_case(operation_id)}RuntimeBridge(context: Record<string, unknown>, nextState: Record<string, unknown> = {{}}): Promise<Record<string, unknown>> {{',
                f'    const spec = getOperationSpec("{operation_id}");',
                '    const normalized: Record<string, unknown> = { ...context, ...nextState };',
                f'    const primaryRecordKey = "{record_hint}";',
                '    if (primaryRecordKey && normalized[primaryRecordKey] === undefined) {',
                '      for (const [candidate, value] of Object.entries(normalized)) {',
                '        const candidateSnake = candidate.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();',
                '        if (candidateSnake.endsWith(`_${primaryRecordKey}`) && value !== undefined) {',
                '          normalized[primaryRecordKey] = value;',
                '          break;',
                '        }',
                '      }',
                '    }',
                f'    normalized.execution_plan = buildOperationPlan({{ execution_mode: "{execution_mode}", module_slug: "{module_slug}", operation_id: "{operation_id}", uniqueness_hint_fields: {uniqueness_blob}, primary_record_key_hint: "{record_hint}" }});',
                f'    const result = await Promise.resolve({handler_name}(spec, normalized));',
                '    return result as Record<string, unknown>;',
                '  }',
            ])
            operation_facade = "\n".join([
                f"  async {method_name}(payload: Record<string, unknown>): Promise<Record<string, unknown>> {{",
                f"    return this.execute{camel_case(operation_id)}RuntimeBridge(payload);",
                "  }",
            ])
            write_body = write_body.replace(
                "void context;\n    void nextState;\n    return { ...context, ...nextState };",
                f"return this.execute{camel_case(operation_id)}RuntimeBridge(context, nextState);",
            )
            write_body = write_body.replace(
                "void context;\n    void nextState;",
                f"return this.execute{camel_case(operation_id)}RuntimeBridge(context, nextState);",
            )
            if action_card_trace_lines:
                lines.extend(action_card_trace_lines)
            if action_card_direct_lines:
                lines.extend(action_card_direct_lines)
            lines.extend([operation_body, ""])
            lines.extend([operation_facade, ""])
            lines.extend([runtime_bridge, ""])
            if "private async transaction(" not in "\n".join(lines):
                lines.extend([transaction_body, ""])
            lines.extend([write_body, ""])
        else:
            if execution_mode in {"detail-read", "list-read"}:
                handler_name = execution_handler_by_mode[execution_mode]
                record_hint = operation_primary_record_hint(spec)
                uniqueness_blob = json.dumps(operation_uniqueness_hint_fields(spec), ensure_ascii=False)
                runtime_bridge = "\n".join([
                    f'  private async execute{camel_case(operation_id)}RuntimeBridge(context: Record<string, unknown>, nextState: Record<string, unknown> = {{}}): Promise<Record<string, unknown>> {{',
                    f'    const spec = getOperationSpec("{operation_id}");',
                    '    const normalized: Record<string, unknown> = { ...context, ...nextState };',
                    f'    const primaryRecordKey = "{record_hint}";',
                    '    if (primaryRecordKey && normalized[primaryRecordKey] === undefined) {',
                    '      for (const [candidate, value] of Object.entries(normalized)) {',
                    '        const candidateSnake = candidate.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();',
                    '        if (candidateSnake.endsWith(`_${primaryRecordKey}`) && value !== undefined) {',
                    '          normalized[primaryRecordKey] = value;',
                    '          break;',
                    '        }',
                    '      }',
                    '    }',
                    f'    normalized.execution_plan = buildOperationPlan({{ execution_mode: "{execution_mode}", module_slug: "{module_slug}", operation_id: "{operation_id}", uniqueness_hint_fields: {uniqueness_blob}, primary_record_key_hint: "{record_hint}" }});',
                    f'    const result = await Promise.resolve({handler_name}(spec, normalized));',
                    '    return result as Record<string, unknown>;',
                    '  }',
                ])
                operation_facade = "\n".join([
                    f"  async {method_name}(payload: Record<string, unknown>): Promise<Record<string, unknown>> {{",
                    f"    return this.execute{camel_case(operation_id)}RuntimeBridge(payload);",
                    "  }",
                ])
                body = body.replace(
                    "return { ...context };",
                    f"return this.execute{camel_case(operation_id)}RuntimeBridge(context);",
                )
                if action_card_trace_lines:
                    lines.extend(action_card_trace_lines)
                if action_card_direct_lines:
                    lines.extend(action_card_direct_lines)
                lines.extend([body, ""])
                lines.extend([operation_facade, ""])
                lines.extend([runtime_bridge, ""])
                continue
            if action_card_trace_lines:
                lines.extend(action_card_trace_lines)
            if action_card_direct_lines:
                lines.extend(action_card_direct_lines)
            lines.extend([body, ""])
        continue
        spec = runtime_spec_for_operation(operation, operation_specs)
        execution_mode = operation_execution_mode(spec)
        handler_name = execution_handler_by_mode[execution_mode]
        record_hint = operation_primary_record_hint(spec)
        uniqueness_blob = json.dumps(operation_uniqueness_hint_fields(spec), ensure_ascii=False)
        lines.extend(
            [
                f"  async {method_name}(payload: GeneratedRuntimePayload): Promise<GeneratedRuntimeResult> {{",
                f'    const spec = getOperationSpec("{operation_id}");',
                f'    const request = annotateRuntimePayload(payload, {{ repository_module: "{module_slug}", repository_method: "{method_name}", operation_id: "{operation_id}" }});',
                "    const normalized = normalizeGeneratedPayload(request);",
                f'    normalized.execution_plan = buildOperationPlan({{ execution_mode: "{execution_mode}", module_slug: "{module_slug}", operation_id: "{operation_id}", uniqueness_hint_fields: {uniqueness_blob}, primary_record_key_hint: "{record_hint}" }});',
                f"    const result = await Promise.resolve({handler_name}(spec, normalized));",
                "    return result as GeneratedRuntimeResult;",
                "  }",
                "",
            ]
        )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)

def stable_slug(value: str, *, fallback: str = "default") -> str:
    primary = slugify(value)
    if primary:
        return primary

    ascii_fallback = slugify(fallback)
    tokens: list[str] = []
    buffer = ""
    for char in str(value):
        if char.isascii() and char.isalnum():
            buffer += char.lower()
            continue
        if buffer:
            tokens.append(buffer)
            buffer = ""
        if char.isspace() or char in {"-", "_", "/", "."}:
            continue
        tokens.append(f"u{ord(char):04x}")
    if buffer:
        tokens.append(buffer)

    normalized = slugify("-".join(tokens))
    if normalized:
        return normalized
    return ascii_fallback or "default"
