#!/usr/bin/env python3
"""
Generate the initial implementation bindings and executable source scaffolds for Phase-3.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
from pathlib import Path
from typing import Any

from phase3.contract_test_scaffolder import build_contract_test_target_lookup, contract_test_filename
from phase3.phase3_behavior_card_consumption import (
    render_behavior_step_test_mapping,
    render_repository_invariant_plan,
    render_service_implementation_plan,
)
try:
    from phase3.behavior_contract import (
        behavior_evidence_keys,
        typescript_array_literal,
        typescript_behavior_card_payload_helper_lines,
    )
except ModuleNotFoundError:
    from phase3.behavior_contract import (
        behavior_evidence_keys,
        typescript_array_literal,
        typescript_behavior_card_payload_helper_lines,
    )
from phase3.contract_tools import (
    extract_nested_bullet_items,
    load_openapi_document,
    slugify,
)
from phase3.implementation_binding_tools import (
    append_generated_sql_test_bindings,
    append_generated_unit_test_bindings,
    backend_foundation_unit_test_paths,
    backend_module_unit_test_path,
    build_wp_lookup,
    expand_scope_term_equivalents,
    foundation_implementation_targets_for_test_targets,
    frontend_surface_unit_test_path,
    infer_work_packages_from_replay_overlap,
    infer_work_packages_from_targets,
    parse_openapi_operations,
    propagate_shared_test_bindings,
    rebind_cross_operation_test_rows,
    scope_tokens,
    suggest_work_packages,
    trace_ids_in_text,
    unit_test_targets_for_implementation_targets,
)
from phase3.module_synthesis import (
    build_module_authoring_context,
    build_module_candidate_ledger,
    load_module_synthesis_bundle,
    write_module_synthesis_evidence,
    write_module_synthesis_quality_evidence,
)
from phase3.surface_policy import write_phase3_diagnostic_surface
from phase3.ui_locale import (
    infer_ui_locale,
    is_zh_locale,
    localize_information_object,
    localize_surface_title,
    normalize_role_display_name,
    page_role_eyebrow,
    page_role_label,
    surface_shell_copy,
    surface_success_copy,
    ui_field_label,
    ui_text,
    view_label,
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


UUID_LIKE_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
OPERATION_IDS_RE = re.compile(r"const operationIds = (\[[^;]*\]);", re.DOTALL)


def stable_uuid_seed(seed: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", str(seed).lower())
    alphabet = "abcdef0123456789"
    mapped = "".join(alphabet[ord(char) % len(alphabet)] for char in normalized)
    padded = (mapped + ("0" * 32))[:32]
    return f"{padded[:8]}-{padded[8:12]}-{padded[12:16]}-{padded[16:20]}-{padded[20:32]}"


def normalize_default_tenant_id(value: str) -> str:
    tenant = str(value).strip()
    if not tenant:
        return ""
    if UUID_LIKE_RE.fullmatch(tenant):
        return tenant.lower()
    return stable_uuid_seed(f"tenant_id:{tenant}")


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


def render_frontend_page_unit_test(route: str) -> str:
    component_name = f"{camel_case(route)}Page"
    surface_marker = f"/{route}".replace("//", "/")
    return "\n".join(
        [
            'import { createElement } from "react";',
            'import { renderToString } from "react-dom/server";',
            'import { describe, expect, it } from "vitest";',
            f'import {component_name} from "../../../apps/web/app/{route}/page";',
            "",
            f'describe("{route} page unit", () => {{',
            '  it("renders the generated execution surface", () => {',
            f"    const html = renderToString(createElement({component_name}));",
            f'    expect(html).toContain(\'data-phase3-surface="{surface_marker}"\');',
            "  });",
            "});",
            "",
        ]
    )


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


def render_runtime_adapter_module() -> str:
    return "\n".join(
        [
            "export interface GeneratedRuntimePayload {",
            "  path_params?: Record<string, unknown>;",
            "  pathParams?: Record<string, unknown>;",
            "  auth_context?: Record<string, unknown>;",
            "  authContext?: Record<string, unknown>;",
            "  body?: Record<string, unknown>;",
            "  query?: Record<string, unknown>;",
            "  force_error_code?: string;",
            "  invalid_query?: boolean;",
            "  [key: string]: unknown;",
            "}",
            "",
            "export type GeneratedRuntimeResult = Record<string, unknown>;",
            "",
            "function isRecord(value: unknown): value is Record<string, unknown> {",
            "  return typeof value === 'object' && value !== null && !Array.isArray(value);",
            "}",
            "",
            "function clonePayload<T>(value: T): T {",
            "  return JSON.parse(JSON.stringify(value)) as T;",
            "}",
            "",
            "function flattenNestedInputFields(target: Record<string, unknown>, value: unknown): void {",
            "  if (!isRecord(value)) {",
            "    return;",
            "  }",
            "  for (const [key, entry] of Object.entries(value)) {",
            "    if (target[key] === undefined) {",
            "      target[key] = clonePayload(entry);",
            "    }",
            "    if (isRecord(entry)) {",
            "      flattenNestedInputFields(target, entry);",
            "    }",
            "  }",
            "}",
            "",
            "export function normalizeGeneratedPayload(payload: GeneratedRuntimePayload): GeneratedRuntimePayload {",
            "  const next = isRecord(payload) ? clonePayload(payload) : {};",
            "  if (isRecord(next.body)) {",
            "    Object.assign(next, next.body);",
            "    delete next.body;",
            "  }",
            "  if (isRecord(next.input)) {",
            "    flattenNestedInputFields(next, next.input);",
            "  }",
            "  if (isRecord(next.query)) {",
            "    Object.assign(next, next.query);",
            "    delete next.query;",
            "  }",
            "  if (isRecord(next.pathParams) && !isRecord(next.path_params)) {",
            "    next.path_params = clonePayload(next.pathParams);",
            "  }",
            "  if (isRecord(next.authContext) && !isRecord(next.auth_context)) {",
            "    next.auth_context = clonePayload(next.authContext);",
            "  }",
            "  delete next.pathParams;",
            "  delete next.authContext;",
            "  return next as GeneratedRuntimePayload;",
            "}",
            "",
            "export function annotateRuntimePayload(",
            "  payload: GeneratedRuntimePayload,",
            "  additions: Record<string, unknown>,",
            "): GeneratedRuntimePayload {",
            "  const next = normalizeGeneratedPayload(payload);",
            "  for (const [key, value] of Object.entries(additions)) {",
            "    if (next[key] === undefined) {",
            "      next[key] = value;",
            "    }",
            "  }",
            "  return next;",
            "}",
            "",
            "export function appendEnvelopeMeta(",
            "  result: GeneratedRuntimeResult,",
            "  additions: Record<string, unknown>,",
            "): GeneratedRuntimeResult {",
            "  const next = isRecord(result) ? clonePayload(result) as GeneratedRuntimeResult : { data: result };",
            "  const meta = isRecord(next.meta) ? clonePayload(next.meta) : {};",
            "  for (const [key, value] of Object.entries(additions)) {",
            "    if (meta[key] === undefined) {",
            "      meta[key] = value;",
            "    }",
            "  }",
            "  next.meta = meta;",
            "  return next;",
            "}",
            "",
        ]
    )


def render_envelope_module() -> str:
    return "\n".join(
        [
            "export interface ApiEnvelope<TData> {",
            "  trace_id: string;",
            "  request_id?: string;",
            "  data: TData;",
            "  meta?: Record<string, unknown>;",
            "}",
            "",
            "export function buildEnvelope<TData>(",
            "  data: TData,",
            "  ids: { traceId: string; requestId: string },",
            "  meta?: Record<string, unknown>,",
            "): ApiEnvelope<TData> {",
            "  return {",
            "    trace_id: ids.traceId,",
            "    request_id: ids.requestId,",
            "    data,",
            "    meta,",
            "  };",
            "}",
            "",
        ]
    )


def render_errors_module() -> str:
    return "\n".join(
        [
            "export interface ApiErrorEnvelope {",
            "  error_kind: string;",
            "  error_code: string;",
            "  retryability?: string;",
            "  message?: string;",
            "  meta?: Record<string, unknown>;",
            "}",
            "",
            "export class ApiError extends Error {",
            "  readonly status: number;",
            "  readonly envelope: ApiErrorEnvelope;",
            "",
            "  constructor(status: number, envelope: ApiErrorEnvelope) {",
            "    super(`${status} ${envelope.error_code}`);",
            "    this.name = 'ApiError';",
            "    this.status = status;",
            "    this.envelope = envelope;",
            "  }",
            "}",
            "",
            "export function createApiError(",
            "  status: number,",
            "  errorKind: string,",
            "  errorCode: string,",
            "  retryability = 'never',",
            "  message = '',",
            "  meta?: Record<string, unknown>,",
            "): ApiError {",
            "  return new ApiError(status, {",
            "    error_kind: errorKind,",
            "    error_code: errorCode,",
            "    retryability,",
            "    message: message || undefined,",
            "    meta,",
            "  });",
            "}",
            "",
        ]
    )


def render_pagination_module() -> str:
    return "\n".join(
        [
            "export interface CursorPageRequest {",
            "  cursor?: string;",
            "  limit?: number;",
            "}",
            "",
            "export function buildCursorMeta(",
            "  items: unknown[],",
            "  exampleMeta?: Record<string, unknown>,",
            "  nextCursor?: string,",
            "): Record<string, unknown> {",
            "  const meta: Record<string, unknown> = { ...(exampleMeta ?? {}) };",
            "  const resolvedCursor = nextCursor ?? null;",
            "  if (meta.nextCursor === undefined && meta.next_cursor === undefined) {",
            "    meta.nextCursor = resolvedCursor;",
            "    meta.next_cursor = resolvedCursor;",
            "  } else {",
            "    if (meta.nextCursor === undefined) {",
            "      meta.nextCursor = meta.next_cursor ?? resolvedCursor;",
            "    }",
            "    if (meta.next_cursor === undefined) {",
            "      meta.next_cursor = meta.nextCursor ?? resolvedCursor;",
            "    }",
            "  }",
            "  if (meta.returnedCount === undefined && meta.returned_count === undefined) {",
            "    meta.returnedCount = items.length;",
            "    meta.returned_count = items.length;",
            "  } else {",
            "    if (meta.returnedCount === undefined) {",
            "      meta.returnedCount = meta.returned_count ?? items.length;",
            "    }",
            "    if (meta.returned_count === undefined) {",
            "      meta.returned_count = meta.returnedCount ?? items.length;",
            "    }",
            "  }",
            "  return meta;",
            "}",
            "",
        ]
    )


def render_auth_session_module() -> str:
    return "\n".join(
        [
            'import jwt from "jsonwebtoken";',
            'import { createApiError } from "./errors.js";',
            "",
            "export interface AuthSessionContext {",
            "  subject_id: string;",
            "  tenant_id: string;",
            "  roles: string[];",
            "  session_id: string;",
            "  oidc_claims: Record<string, unknown>;",
            "}",
            "",
            "export const ACCESS_TOKEN_TTL_SECONDS = 15 * 60;",
            "export const REFRESH_TOKEN_TTL_SECONDS = 8 * 60 * 60;",
            "",
            "function isRecord(value: unknown): value is Record<string, unknown> {",
            "  return typeof value === 'object' && value !== null && !Array.isArray(value);",
            "}",
            "",
            "function authTokenSecret(): string {",
            '  return process.env.AUTH_TOKEN_SECRET || "phase3-local-dev-secret";',
            "}",
            "",
            "function roleList(value: unknown): string[] {",
            "  if (Array.isArray(value)) {",
            "    return value.filter((item): item is string => typeof item === 'string' && item.length > 0);",
            "  }",
            "  if (typeof value === 'string' && value.trim()) {",
            "    return [value.trim()];",
            "  }",
            "  return [];",
            "}",
            "",
            "function refreshTokenFamilyId(raw: Record<string, unknown>): string {",
            "  const existing = raw.refresh_token_family_id ?? raw.refreshTokenFamilyId;",
            "  if (typeof existing === 'string' && existing.trim()) {",
            "    return existing.trim();",
            "  }",
            "  const sessionId = raw.session_id ?? raw.sid;",
            "  if (typeof sessionId === 'string' && sessionId.trim()) {",
            "    return `refresh-family-${sessionId.trim()}`;",
            "  }",
            "  return 'refresh-family-local';",
            "}",
            "",
            "function rotationCounter(raw: Record<string, unknown>): number {",
            "  const value = raw.rotation_counter ?? raw.rotationCounter;",
            "  return typeof value === 'number' && Number.isFinite(value) ? value : 0;",
            "}",
            "",
            "function signableClaims(raw: Record<string, unknown>): Record<string, unknown> {",
            "  const claims = { ...raw };",
            "  delete claims.exp;",
            "  delete claims.iat;",
            "  delete claims.nbf;",
            "  return claims;",
            "}",
            "",
            "export function issueAuthToken(raw: Record<string, unknown>): string {",
            "  return jwt.sign({ ...signableClaims(raw), token_use: 'access' }, authTokenSecret(), { algorithm: 'HS256', expiresIn: ACCESS_TOKEN_TTL_SECONDS });",
            "}",
            "",
            "export function issueRefreshToken(raw: Record<string, unknown>): string {",
            "  return jwt.sign(",
            "    {",
            "      ...signableClaims(raw),",
            "      token_use: 'refresh',",
            "      refresh_token_family_id: refreshTokenFamilyId(raw),",
            "      rotation_counter: rotationCounter(raw),",
            "    },",
            "    authTokenSecret(),",
            "    { algorithm: 'HS256', expiresIn: REFRESH_TOKEN_TTL_SECONDS },",
            "  );",
            "}",
            "",
            "export function rotateRefreshToken(raw: Record<string, unknown>): string {",
            "  return issueRefreshToken({",
            "    ...raw,",
            "    refresh_token_family_id: refreshTokenFamilyId(raw),",
            "    rotation_counter: rotationCounter(raw) + 1,",
            "  });",
            "}",
            "",
            "export function parseAuthorizationHeader(headerValue: string | undefined): Record<string, unknown> {",
            "  if (!headerValue || !headerValue.trim()) {",
            "    throw createApiError(401, 'auth_error', 'missing_bearer_token', 'caller_after_fix', 'Authorization header must use Bearer token');",
            "  }",
            "  const bearerPrefix = 'Bearer ';",
            "  const token = headerValue.startsWith(bearerPrefix) ? headerValue.slice(bearerPrefix.length).trim() : '';",
            "  if (!token) {",
            "    throw createApiError(401, 'auth_error', 'missing_bearer_token', 'caller_after_fix', 'Authorization header must use Bearer token');",
            "  }",
            "  try {",
            "    const verified = jwt.verify(token, authTokenSecret()) as unknown;",
            "    return isRecord(verified) ? verified : {};",
            "  } catch (error) {",
            "    throw createApiError(",
            "      401,",
            "      'auth_error',",
            "      'invalid_auth_token',",
            "      'caller_after_fix',",
            "      error instanceof Error ? error.message : 'token verification failed',",
            "    );",
            "  }",
            "}",
            "",
            "export function normalizeAuthSession(raw: unknown, fallbackTenantId: string): AuthSessionContext {",
            "  const source = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {};",
            "  const tenantId = typeof source.tenant_id === 'string' && source.tenant_id",
            "    ? source.tenant_id",
            "    : (typeof source.tenantId === 'string' && source.tenantId ? source.tenantId : fallbackTenantId);",
            "  const subjectId = typeof source.subject_id === 'string' && source.subject_id",
            "    ? source.subject_id",
            "    : (typeof source.sub === 'string' && source.sub ? source.sub : '');",
            "  const sessionId = typeof source.session_id === 'string' && source.session_id",
            "    ? source.session_id",
            "    : (typeof source.sid === 'string' && source.sid ? source.sid : '');",
            "  const roles = roleList(source.roles).length > 0 ? roleList(source.roles) : roleList(source.role);",
            "  const oidcClaims = isRecord(source.oidc_claims)",
            "    ? (source.oidc_claims as Record<string, unknown>)",
            "    : source;",
            "  if (!tenantId || !subjectId || !sessionId || roles.length === 0) {",
            "    throw createApiError(401, 'auth_error', 'invalid_auth_context', 'caller_after_fix', 'tenant/session claims are missing');",
            "  }",
            "  return {",
            "    subject_id: subjectId,",
            "    tenant_id: tenantId,",
            "    roles,",
            "    session_id: sessionId,",
            "    oidc_claims: oidcClaims,",
            "  };",
            "}",
            "",
            "export function requireRbacRole(session: AuthSessionContext, role: string): void {",
            "  if (!session.roles.includes(role)) {",
            "    throw createApiError(403, 'business_error', 'rbac_forbidden', 'never', `Missing role: ${role}`);",
            "  }",
            "}",
            "",
        ]
    )


def index_compiled_bindings_by_endpoint(
    compiled_bindings: list[dict[str, Any]] | None,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    binding_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in compiled_bindings or []:
        method = str(row.get("http_method") or "").strip().upper()
        path = str(row.get("api_endpoint") or "").strip()
        if not method or not path:
            continue
        binding_index.setdefault((method, path), []).append(row)
    return binding_index

def binding_rbac_policies(rows: list[dict[str, Any]], *, locale: str | None = None) -> list[str]:
    return ordered_ui_roles(
        *[
            extract_ui_policy_roles(
                row.get("rbac_policy") or row.get("visibility_rule") or "",
                locale=locale,
            )
            for row in rows
            if isinstance(row, dict)
        ],
        locale=locale,
    )


def json_clone(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))


def build_runtime_operation_specs(
    openapi_spec: dict[str, object],
    compiled_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    spec_index: dict[str, dict[str, Any]] = {}
    paths = openapi_spec.get("paths", {})
    if not isinstance(paths, dict):
        return spec_index
    binding_index = index_compiled_bindings_by_endpoint(compiled_bindings)
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId", "")).strip()
            if not operation_id:
                continue
            responses = operation.get("responses", {})
            if not isinstance(responses, dict):
                responses = {}
            success_status = next((code for code in sorted(responses) if str(code).startswith("2")), "200")
            success_content = responses.get(success_status, {})
            success_example: object = {}
            if isinstance(success_content, dict):
                content = success_content.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        success_example = json_clone(app_json.get("example", {}))
            request_example: object = {}
            request_required_fields: list[str] = []
            request_schema_source = ""
            request_body = operation.get("requestBody", {})
            if isinstance(request_body, dict):
                content = request_body.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        request_example = json_clone(app_json.get("example", {}))
                        request_schema = app_json.get("schema", {})
                        if isinstance(request_schema, dict):
                            request_schema_source = str(request_schema.get("x-schema-source", "")).strip()
                            if request_schema_source != "inferred-from-example":
                                raw_required = request_schema.get("required", [])
                                if isinstance(raw_required, list):
                                    request_required_fields = [
                                        str(item).strip()
                                        for item in raw_required
                                        if str(item).strip()
                                    ]
            failure_cases: list[dict[str, str]] = []
            for status, response in responses.items():
                if not str(status).startswith(("4", "5")):
                    continue
                if not isinstance(response, dict):
                    continue
                example = {}
                content = response.get("content", {})
                if isinstance(content, dict):
                    app_json = content.get("application/json", {})
                    if isinstance(app_json, dict):
                        example = app_json.get("example", {})
                failure_cases.append(
                    {
                        "status": str(status),
                        "error_kind": str(example.get("error_kind", "")).strip(),
                        "error_code": str(example.get("error_code", "")).strip(),
                        "retryability": str(example.get("retryability", "")).strip(),
                    }
                )
            parameters = operation.get("parameters", [])
            path_params = []
            required_path_params = []
            if isinstance(parameters, list):
                for parameter in parameters:
                    if not isinstance(parameter, dict):
                        continue
                    if str(parameter.get("in", "")).strip() == "path":
                        parameter_name = str(parameter.get("name", "")).strip()
                        if parameter_name:
                            path_params.append(parameter_name)
                            if bool(parameter.get("required")):
                                required_path_params.append(parameter_name)
            tags = operation.get("tags", [])
            tag = str(tags[0]).strip() if isinstance(tags, list) and tags else "default"
            matching_bindings = binding_index.get((str(method).upper(), str(path).strip()), [])
            spec_index[operation_id] = {
                "operationId": operation_id,
                "method": str(method).upper(),
                "path": str(path),
                "tag": tag,
                "purpose": str(operation.get("summary", "")).strip(),
                "requestExample": request_example,
                "requestRequiredFields": request_required_fields,
                "requestSchemaSource": request_schema_source,
                "responseExample": success_example,
                "failureCases": failure_cases,
                "successStatus": success_status,
                "pathParams": path_params,
                "requiredPathParams": required_path_params,
                "rbacPolicies": binding_rbac_policies(matching_bindings),
                "paginationRule": str(operation.get("x-pagination-rule", "")).strip(),
                "retryabilityPolicy": str(operation.get("x-retryability-policy", "")).strip(),
                "idempotencyRule": str(operation.get("x-idempotency-rule", "")).strip(),
            }
    return spec_index


def infer_default_tenant(operation_specs: dict[str, dict[str, Any]]) -> str:
    for spec in operation_specs.values():
        request_example = spec.get("requestExample", {})
        if isinstance(request_example, dict):
            tenant_id = str(request_example.get("tenant_id") or request_example.get("tenantId") or "").strip()
            if tenant_id:
                return normalize_default_tenant_id(tenant_id)
        response_example = spec.get("responseExample", {})
        if isinstance(response_example, dict):
            data = response_example.get("data", {})
            if isinstance(data, dict):
                tenant_id = str(data.get("tenant_id") or data.get("tenantId") or "").strip()
                if tenant_id:
                    return normalize_default_tenant_id(tenant_id)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        tenant_id = str(item.get("tenant_id") or item.get("tenantId") or "").strip()
                        if tenant_id:
                            return normalize_default_tenant_id(tenant_id)
    return "11111111-1111-1111-1111-111111111111"


def render_generated_runtime(operation_specs: dict[str, dict[str, Any]], default_tenant_id: str) -> str:
    template = """import { buildEnvelope } from "./envelope.js";
import { createApiError } from "./errors.js";
import { normalizeAuthSession } from "./auth-session.js";
import { buildCursorMeta } from "./pagination.js";

/**
 * Phase-3 shared execution support kernel.
 *
 * This file provides reusable stateful execution helpers for early Phase-3
 * verification and for repository-level operation planning. It is not, by
 * itself, evidence that the case has reached runnable implementation completion.
 *
 * Replacement rule:
 * 1. Replace repository delegates with real DAL/domain handlers during Phase-3 implementation.
 * 2. Keep frozen OpenAPI, unit tests, contract tests, scenario tests, and replay tests green during replacement.
 * 3. Keep generated-runtime.ts only as a compatibility facade once repository-level execution plans exist.
 */

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
type JsonRecord = Record<string, JsonValue | unknown>;

type FailureSpec = {
  status: string;
  error_kind: string;
  error_code: string;
  retryability: string;
};

type OperationSpec = {
  operationId: string;
  method: string;
  path: string;
  tag: string;
  purpose: string;
  requestExample: unknown;
  requestRequiredFields: string[];
  requestSchemaSource?: string;
  responseExample: unknown;
  failureCases: FailureSpec[];
  successStatus: string;
  pathParams: string[];
  requiredPathParams: string[];
  rbacPolicies: string[];
  paginationRule: string;
  retryabilityPolicy: string;
  idempotencyRule: string;
};

type OperationExecutionPlan = {
  operation_id: string;
  execution_mode: string;
  module_slug?: string;
  uniqueness_hint_fields?: string[];
  primary_record_key_hint?: string;
};

type AuditRecord = {
  audit_record_id: string;
  operation_id?: string;
  request_id: string;
  tenant_id: string;
  action_type: string;
  outcome: string;
  reason?: string;
  subject_id?: string;
  observed_at: string;
};

type RuntimeState = {
  entityRecords: Record<string, Record<string, JsonRecord>>;
  auditRecords: AuditRecord[];
  counters: Record<string, number>;
  createdKeys: Set<string>;
};

const OPERATION_SPECS: Record<string, OperationSpec> = __OPERATION_SPECS__;
const DEFAULT_TENANT_ID = "__DEFAULT_TENANT_ID__";
const DENY_TENANT_ID = "22222222-2222-2222-2222-222222222222";
const DEFAULT_AUTHENTICATED_ROLE = "authenticated";

let runtimeState = createInitialState();

function clone<T>(value: T): T {
  if (value === undefined) {
    return value;
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

function asRecord(value: unknown): JsonRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value as JsonRecord;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function snakeCase(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}

function looksLikeIsoTimestamp(value: string): boolean {
  return /^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?Z$/.test(value);
}

function alignTimestampPrecision(value: string, template: string): string {
  if (!looksLikeIsoTimestamp(value) || !looksLikeIsoTimestamp(template)) {
    return value;
  }
  if (!template.includes(".")) {
    return value.replace(".000Z", "Z");
  }
  return value;
}

function normalizeTemporalLikeValue(exampleValue: unknown, actualValue: unknown): unknown {
  if (actualValue instanceof Date) {
    return alignTimestampPrecision(actualValue.toISOString(), stringValue(exampleValue));
  }
  if (typeof actualValue === "string" && typeof exampleValue === "string") {
    return alignTimestampPrecision(actualValue, exampleValue);
  }
  return actualValue;
}

function normalizeScalarLikeValue(exampleValue: unknown, actualValue: unknown): unknown {
  const normalizedTemporal = normalizeTemporalLikeValue(exampleValue, actualValue);
  if (typeof exampleValue === "number") {
    const normalizedNumber = numberValue(normalizedTemporal);
    if (normalizedNumber !== undefined) {
      return normalizedNumber;
    }
  }
  return normalizedTemporal;
}

function isIdField(value: string): boolean {
  if (
    value === "operation_id"
    || value === "dispatch_operation_id"
    || value === "operationId"
    || value === "dispatchOperationId"
    || value === "trace_id"
    || value === "traceId"
    || value === "request_id"
    || value === "requestId"
  ) {
    return false;
  }
  return value.endsWith("_id") || value.endsWith("Id");
}

function stripIdSuffix(value: string): string {
  if (value.endsWith("_id")) {
    return value.slice(0, -3);
  }
  if (value.endsWith("Id")) {
    return value.slice(0, -2);
  }
  return value;
}

function snakeIdField(value: string): string {
  return snakeCase(value);
}

function camelIdField(value: string): string {
  const normalized = snakeIdField(value);
  if (!normalized.endsWith("_id")) {
    return value;
  }
  const base = normalized.slice(0, -3);
  return `${base.replace(/_([a-z0-9])/g, (_, token: string) => token.toUpperCase())}Id`;
}

function camelField(value: string): string {
  return snakeCase(value).replace(/_([a-z0-9])/g, (_, token: string) => token.toUpperCase());
}

function idFieldAliases(value: string): string[] {
  const normalized = snakeIdField(value);
  if (!normalized.endsWith("_id")) {
    return [normalized];
  }
  const aliases = new Set<string>([normalized]);
  const parts = normalized.split("_").filter(Boolean);
  if (parts.length > 2) {
    aliases.add(`${parts[parts.length - 2]}_id`);
  }
  return Array.from(aliases);
}

function primaryKeyAliasCandidates(value: string): string[] {
  const normalized = snakeIdField(value);
  if (!normalized.endsWith("_id")) {
    return [normalized].filter(Boolean);
  }
  const aliases = new Set<string>([normalized, ...idFieldAliases(normalized)]);
  const stripped = stripIdSuffix(normalized);
  const parts = stripped.split("_").filter(Boolean);
  if (parts.length > 1) {
    aliases.add(`${parts.at(-1)}_id`);
  }
  return Array.from(aliases).filter(Boolean);
}

function executionPlan(payload: JsonRecord): JsonRecord {
  return asRecord(payload.execution_plan);
}

function planPrimaryRecordKeyHint(payload: JsonRecord): string {
  const plan = executionPlan(payload);
  const hint = stringValue(plan.primary_record_key_hint) || stringValue(plan.primaryRecordKeyHint);
  return hint ? snakeCase(hint) : "";
}

function planUniquenessHintFields(payload: JsonRecord): string[] {
  const plan = executionPlan(payload);
  const raw = plan.uniqueness_hint_fields ?? plan.uniquenessHintFields;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function isCreateLikeOperation(spec: OperationSpec): boolean {
  return (
    spec.operationId.startsWith("Create")
    || spec.operationId.startsWith("Launch")
    || spec.operationId.startsWith("Export")
  );
}

function plannedFieldValue(payload: JsonRecord, pathParams: JsonRecord, field: string): string {
  const snakeField = snakeCase(field);
  const camelizedField = camelField(field);
  return (
    stringValue(payload[field])
    || stringValue(payload[snakeField])
    || stringValue(payload[camelizedField])
    || stringValue(pathParams[field])
    || stringValue(pathParams[snakeField])
    || stringValue(pathParams[camelizedField])
  );
}

function tokenParts(value: string): string[] {
  return value.split("_").filter(Boolean);
}

function scoreIdFieldCandidate(paramKey: string, field: string): number {
  const normalizedField = snakeIdField(field);
  if (!isIdField(field) || !normalizedField.endsWith("_id")) {
    return -1;
  }
  if (normalizedField === paramKey) {
    return 100;
  }
  const paramCore = stripIdSuffix(paramKey);
  const fieldCore = stripIdSuffix(normalizedField);
  if (fieldCore === paramCore) {
    return 90;
  }
  if (fieldCore.endsWith(paramCore) || paramCore.endsWith(fieldCore)) {
    return 80;
  }
  const paramTokens = tokenParts(paramCore);
  const fieldTokens = tokenParts(fieldCore);
  const overlap = paramTokens.filter((token) => fieldTokens.includes(token)).length;
  return overlap > 0 ? overlap * 10 : -1;
}

function resolvePathParamRecordId(spec: OperationSpec, param: string, data: JsonRecord): string {
  const paramKey = snakeCase(param);
  const direct = stringValue(data[paramKey]);
  if (direct) {
    return direct;
  }
  let bestField = "";
  let bestScore = -1;
  for (const [field, rawValue] of Object.entries(data)) {
    const id = stringValue(rawValue);
    if (!id) {
      continue;
    }
    const score = scoreIdFieldCandidate(paramKey, field);
    if (score > bestScore) {
      bestField = field;
      bestScore = score;
    }
  }
  return bestField ? stringValue(data[bestField]) : "";
}

function mergeRecords(base: JsonRecord, overrides: JsonRecord): JsonRecord {
  return {
    ...clone(base),
    ...clone(overrides),
  };
}

function nextCounter(key: string): number {
  runtimeState.counters[key] = (runtimeState.counters[key] ?? 0) + 1;
  return runtimeState.counters[key];
}

function nextId(prefix: string): string {
  return `${prefix}_${nextCounter(prefix)}`;
}

function isUuidLike(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

function stableUuidSeed(seed: string): string {
  const normalized = seed.toLowerCase().replace(/[^a-z0-9]+/g, "");
  const alphabet = "abcdef0123456789";
  let mapped = "";
  for (let index = 0; index < normalized.length; index += 1) {
    const code = normalized.charCodeAt(index);
    mapped += alphabet[code % alphabet.length];
  }
  const padded = (mapped + "0".repeat(32)).slice(0, 32);
  return `${padded.slice(0, 8)}-${padded.slice(8, 12)}-${padded.slice(12, 16)}-${padded.slice(16, 20)}-${padded.slice(20, 32)}`;
}

export function normalizeIdValue(field: string, raw: string): string {
  const normalizedField = snakeIdField(field);
  if (!normalizedField.endsWith("_id")) {
    return raw;
  }
  if (isUuidLike(raw)) {
    return raw.toLowerCase();
  }
  return stableUuidSeed(`${normalizedField}:${raw}`);
}

function normalizePayloadIdentifiers(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => normalizePayloadIdentifiers(item));
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  const record = value as Record<string, unknown>;
  const normalized: JsonRecord = {};
  for (const [key, entry] of Object.entries(record)) {
    if (typeof entry === "string" && (isIdField(key) || key === "tenant_id" || key === "tenantId")) {
      normalized[key] = normalizeIdValue(key, entry);
      continue;
    }
    normalized[key] = normalizePayloadIdentifiers(entry);
  }
  return normalized;
}

function nowIso(): string {
  return "2026-04-01T00:00:00.000Z";
}

function shouldExposePagination(spec: OperationSpec, meta: Record<string, unknown>): boolean {
  const rule = String(spec.paginationRule || "").trim().toLowerCase();
  if (rule && !["none", "not_applicable", "n/a"].includes(rule)) {
    return true;
  }
  return meta.nextCursor !== undefined || meta.next_cursor !== undefined || meta.returnedCount !== undefined || meta.returned_count !== undefined;
}

function paginationEnvelope(meta: Record<string, unknown>): Record<string, unknown> {
  return {
    hasMore: Boolean(meta.nextCursor ?? meta.next_cursor),
    nextCursor: meta.nextCursor ?? meta.next_cursor ?? null,
    pageSize: Number(meta.returnedCount ?? meta.returned_count ?? 0),
  };
}

function successEnvelope(spec: OperationSpec, data: unknown, meta?: Record<string, unknown>): Record<string, unknown> {
  const example = asRecord(spec.responseExample);
  const exampleMeta = asRecord(example.meta) as Record<string, unknown>;
  const resolvedMeta = meta ?? exampleMeta;
  const envelope = buildEnvelope(
    data,
    {
      traceId: stringValue(example.trace_id) || stringValue(exampleMeta.traceId) || stringValue(exampleMeta.trace_id) || `tr_${nextCounter("trace")}`,
      requestId: stringValue(example.request_id) || stringValue(exampleMeta.requestId) || stringValue(exampleMeta.request_id) || `req_${nextCounter("request")}`,
    },
    resolvedMeta,
  ) as unknown as Record<string, unknown>;
  const orderedEnvelope: Record<string, unknown> = {
    data: envelope.data,
    meta: envelope.meta,
  };
  if (shouldExposePagination(spec, resolvedMeta)) {
    orderedEnvelope.pagination = paginationEnvelope(resolvedMeta);
  }
  orderedEnvelope.request_id = envelope.request_id;
  orderedEnvelope.trace_id = envelope.trace_id;
  return orderedEnvelope;
}

function fieldLookupCandidates(field: string, options: { includeWorkflowInputVariants?: boolean } = {}): string[] {
  const normalized = snakeCase(field);
  const candidates = new Set<string>([field, normalized, camelField(field)]);
  const workflowInputPrefix = "workflow_input_";
  if (isIdField(field)) {
    for (const alias of idFieldAliases(field)) {
      candidates.add(alias);
      candidates.add(camelIdField(alias));
    }
  }
  if (options.includeWorkflowInputVariants && normalized && !normalized.startsWith(workflowInputPrefix)) {
    const workflowInputField = `${workflowInputPrefix}${normalized}`;
    candidates.add(workflowInputField);
    candidates.add(camelField(workflowInputField));
  }
  if (normalized.startsWith(workflowInputPrefix)) {
    const suffix = normalized.slice(workflowInputPrefix.length);
    if (suffix) {
      candidates.add(suffix);
      candidates.add(camelField(suffix));
    }
  }
  return Array.from(candidates);
}

function lookupFieldValue(record: JsonRecord, candidates: string[]): unknown {
  for (const candidate of candidates) {
    if (Object.prototype.hasOwnProperty.call(record, candidate)) {
      return record[candidate];
    }
  }
  return undefined;
}

function projectedRecordValue(record: JsonRecord, key: string): unknown {
  return lookupFieldValue(record, fieldLookupCandidates(key, { includeWorkflowInputVariants: true }));
}

function projectToExampleShape(exampleValue: unknown, actualValue: unknown): unknown {
  if (Array.isArray(exampleValue)) {
    if (!Array.isArray(actualValue)) {
      return clone(exampleValue);
    }
    if (exampleValue.length === 0) {
      return clone(actualValue);
    }
    return actualValue.map((item) => projectToExampleShape(exampleValue[0], item));
  }
  if (exampleValue && typeof exampleValue === "object") {
    const exampleRecord = asRecord(exampleValue);
    const actualRecord = asRecord(actualValue);
    if (Object.keys(exampleRecord).length === 0) {
      return clone(actualRecord);
    }
    const projected: JsonRecord = {};
    for (const [key, exampleEntry] of Object.entries(exampleRecord)) {
      projected[key] = projectToExampleShape(exampleEntry, projectedRecordValue(actualRecord, key));
    }
    return projected;
  }
  const normalizedActual = normalizeScalarLikeValue(exampleValue, actualValue);
  return normalizedActual === undefined ? clone(exampleValue) : clone(normalizedActual);
}

function projectResponseData(spec: OperationSpec, actualValue: unknown): unknown {
  return projectToExampleShape(asRecord(spec.responseExample).data, actualValue);
}

function projectListResponseData(spec: OperationSpec, actualRows: unknown[]): unknown {
  const exampleData = asRecord(spec.responseExample).data;
  if (Array.isArray(exampleData)) {
    return projectToExampleShape(exampleData, actualRows);
  }
  if (exampleData && typeof exampleData === "object") {
    const exampleRecord = asRecord(exampleData);
    const wrappedCollectionEntry = Object.entries(exampleRecord).find(([, entry]) => (
      Array.isArray(entry)
      && (entry.length === 0 || entry.some((item) => item && typeof item === "object" && !Array.isArray(item)))
    ));
    if (wrappedCollectionEntry) {
      const [collectionKey, exampleCollection] = wrappedCollectionEntry;
      const projected: JsonRecord = {};
      for (const [key, exampleEntry] of Object.entries(exampleRecord)) {
        projected[key] = key === collectionKey
          ? projectToExampleShape(exampleCollection, actualRows)
          : clone(exampleEntry);
      }
      return projected;
    }
    return projectToExampleShape(exampleRecord, actualRows[0]);
  }
  return projectToExampleShape(exampleData, actualRows);
}

function projectResponseMeta(spec: OperationSpec, actualMeta?: Record<string, unknown>): Record<string, unknown> {
  const exampleMeta = asRecord(asRecord(spec.responseExample).meta) as Record<string, unknown>;
  return projectToExampleShape(exampleMeta, actualMeta ?? exampleMeta) as Record<string, unknown>;
}

function findFailure(spec: OperationSpec, code: string): FailureSpec | undefined {
  return spec.failureCases.find((failure) => failure.error_code === code);
}

function findFailureByStatusPrefix(spec: OperationSpec, prefix: string): FailureSpec | undefined {
  return spec.failureCases.find((failure) => failure.status.startsWith(prefix));
}

function failureFor(spec: OperationSpec, code: string, fallbackStatus = "400"): never {
  const failure = findFailure(spec, code) ?? findFailureByStatusPrefix(spec, fallbackStatus);
  const status = Number(failure?.status ?? fallbackStatus);
  throw createApiError(
    status,
    failure?.error_kind || "business_error",
    failure?.error_code || code,
    failure?.retryability || "never",
    `${spec.operationId} rejected with ${failure?.error_code || code}`,
  );
}

function appendAuditRecord(details: {
  tenantId: string;
  actionType: string;
  outcome: string;
  reason?: string;
  subjectId?: string;
  operationId?: string;
  requestId?: string;
}): void {
  runtimeState.auditRecords.push({
    audit_record_id: nextId("aud"),
    operation_id: details.operationId,
    request_id: details.requestId || `req_audit_${nextCounter("audit_request")}`,
    tenant_id: details.tenantId,
    action_type: details.actionType,
    outcome: details.outcome,
    reason: details.reason,
    subject_id: details.subjectId,
    observed_at: nowIso(),
  });
}

function createInitialState(): RuntimeState {
  const state: RuntimeState = {
    entityRecords: {},
    auditRecords: [],
    counters: {},
    createdKeys: new Set<string>(),
  };
  for (const spec of Object.values(OPERATION_SPECS)) {
    seedStateFromSpec(state, spec);
  }
  return state;
}

function seedStateFromSpec(state: RuntimeState, spec: OperationSpec): void {
  const response = asRecord(spec.responseExample);
  const request = asRecord(spec.requestExample);
  const responseMeta = asRecord(response.meta);
  const tenantId = normalizeIdValue(
    "tenant_id",
    stringValue(request.tenant_id) || stringValue(request.tenantId) || DEFAULT_TENANT_ID,
  );
  const responseData = response.data;
  if (Array.isArray(responseData) && spec.operationId === "ListAuditLogs") {
    state.auditRecords = responseData
      .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
      .map((item) => ({
        audit_record_id: stringValue(item.audit_record_id) || nextId("aud"),
        request_id: stringValue(item.request_id)
          || stringValue(item.requestId)
          || stringValue(response.request_id)
          || stringValue(responseMeta.request_id)
          || stringValue(responseMeta.requestId)
          || `req_audit_seed_${nextCounter("audit_seed_request")}`,
        tenant_id: stringValue(item.tenant_id) || tenantId,
        action_type: stringValue(item.action_type) || "task_export",
        outcome: stringValue(item.outcome) || "allowed",
        observed_at: nowIso(),
      }));
    return;
  }
  if (isCreateLikeOperation(spec)) {
    return;
  }
  const responseRecords = responseExampleRecords(spec);
  if (responseRecords.length === 0) {
    return;
  }
  for (const responseRecord of responseRecords) {
    const data = normalizePayloadIdentifiers({
      ...clone(responseRecord),
      tenant_id: stringValue(responseRecord.tenant_id) || stringValue(responseRecord.tenantId) || tenantId,
    }) as JsonRecord;
    for (const [field, rawValue] of Object.entries(data)) {
      if (!isIdField(field)) {
        continue;
      }
      const id = stringValue(rawValue);
      if (!id) {
        continue;
      }
      for (const recordKey of idFieldAliases(field)) {
        state.entityRecords[recordKey] ??= {};
        state.entityRecords[recordKey][id] = {
          ...clone(data),
          ...clone(state.entityRecords[recordKey][id] ?? {}),
        };
      }
    }
    for (const param of spec.pathParams) {
      const key = snakeCase(param);
      const id = resolvePathParamRecordId(spec, param, data);
      if (!id) {
        continue;
      }
      state.entityRecords[key] ??= {};
      state.entityRecords[key][id] = {
        ...clone(data),
        ...clone(state.entityRecords[key][id] ?? {}),
      };
    }
  }
}

function recordKeyAliases(recordKey: string): string[] {
  const normalized = snakeCase(recordKey);
  return Array.from(new Set([recordKey, normalized, camelIdField(normalized), ...idFieldAliases(normalized)]));
}

function lookupRecord(recordKey: string, id: string): JsonRecord | undefined {
  for (const alias of recordKeyAliases(recordKey)) {
    const normalizedId = normalizeIdValue(alias, id);
    const record = runtimeState.entityRecords[alias]?.[id] ?? runtimeState.entityRecords[alias]?.[normalizedId];
    if (record) {
      return record;
    }
  }
  return undefined;
}

function primaryPathParam(spec: OperationSpec): string {
  return spec.pathParams[0] || "";
}

function pathParamRecordKey(spec: OperationSpec, param: string): string {
  const normalized = snakeCase(param);
  if (normalized && normalized !== "id") {
    return normalized;
  }
  const responsePrimary = responsePrimaryIdField(spec);
  if (responsePrimary) {
    return responsePrimary;
  }
  const operationEntity = operationEntityBase(spec);
  if (operationEntity) {
    return `${operationEntity}_id`;
  }
  return normalized;
}

function primaryRecordKey(spec: OperationSpec): string {
  const param = primaryPathParam(spec);
  return param ? pathParamRecordKey(spec, param) : "";
}

function defaultPathParams(spec: OperationSpec): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const param of spec.pathParams) {
    const key = snakeCase(param);
    const recordKey = pathParamRecordKey(spec, param) || key;
    const known = runtimeState.entityRecords[recordKey] ?? runtimeState.entityRecords[key];
    const first = known ? Object.keys(known)[0] : "";
    const fallbackBase = recordKey || key || "id";
    const fallback = first || `${fallbackBase}_1`;
    params[param] = (isIdField(param) || recordKey.endsWith("_id"))
      ? normalizeIdValue(recordKey || param, fallback)
      : fallback;
  }
  return params;
}

function resolveRecordKeyCandidates(spec: OperationSpec, payload: JsonRecord): string[] {
  const candidates = [planPrimaryRecordKeyHint(payload), primaryRecordKey(spec)].filter(Boolean);
  return Array.from(new Set(candidates));
}

function resolvePrimaryRecordContext(spec: OperationSpec, payload: JsonRecord): {
  pathParams: JsonRecord;
  recordKey: string;
  id: string;
  record: JsonRecord | undefined;
} {
  const pathParams = mergeRecords(defaultPathParams(spec), asRecord(payload.path_params));
  const pathParam = primaryPathParam(spec);
  const recordKeys = resolveRecordKeyCandidates(spec, payload);
  const id = pathParam
    ? stringValue(pathParams[pathParam]) || stringValue(pathParams[snakeCase(pathParam)])
    : "";
  let recordKey = recordKeys[0] || "";
  let record: JsonRecord | undefined;
  if (id) {
    for (const candidate of recordKeys) {
      const resolved = lookupRecord(candidate, id);
      if (resolved) {
        recordKey = candidate;
        record = resolved;
        break;
      }
    }
  }
  return {
    pathParams,
    recordKey,
    id,
    record,
  };
}

function deriveTargetTenantId(spec: OperationSpec, payload: JsonRecord): string {
  const pathParams = asRecord(payload.path_params);
  const authContext = asRecord(payload.auth_context);
  const tenantIdFromPayload =
    stringValue(payload.tenant_id)
    || stringValue(payload.tenantId)
    || stringValue(pathParams.tenant_id)
    || stringValue(pathParams.tenantId)
    || stringValue(authContext.tenant_id)
    || stringValue(authContext.tenantId);
  if (tenantIdFromPayload) {
    return normalizeIdValue("tenant_id", tenantIdFromPayload);
  }
  for (const param of spec.pathParams) {
    const record = lookupRecord(
      pathParamRecordKey(spec, param),
      stringValue(pathParams[param]) || stringValue(pathParams[snakeCase(param)]),
    );
    if (record) {
      return normalizeIdValue("tenant_id", stringValue(record.tenant_id) || DEFAULT_TENANT_ID);
    }
  }
  return DEFAULT_TENANT_ID;
}

function hasTenantAccessControl(spec: OperationSpec): boolean {
  return spec.failureCases.some((failure) => failure.error_code === "tenant_forbidden");
}

function resolveExecutionAccess(spec: OperationSpec, payload: JsonRecord): { tenantId: string; subjectId: string } {
  const tenantId = deriveTargetTenantId(spec, payload);
  const policies = effectiveRbacPolicies(spec);
  const requiresTenantCheck = hasTenantAccessControl(spec);
  if (policies.length === 0 && !requiresTenantCheck) {
    return { tenantId, subjectId: "user_1" };
  }
  const session = normalizeAuthSession(payload.auth_context, tenantId);
  requireAnyRbacRole(session, policies);
  const sessionTenantId = normalizeIdValue("tenant_id", stringValue(session.tenant_id) || tenantId);
  if (requiresTenantCheck && sessionTenantId !== tenantId) {
    appendAuditRecord({
      tenantId,
      actionType: `${spec.tag}_access`,
      outcome: "denied",
      reason: "tenant_forbidden",
      subjectId: session.subject_id,
    });
    failureFor(spec, "tenant_forbidden", "403");
  }
  return { tenantId: sessionTenantId, subjectId: session.subject_id };
}

function uniqueNonEmpty(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => String(value).trim()).filter(Boolean)));
}

function effectiveRbacPolicies(spec: OperationSpec): string[] {
  const policies = uniqueNonEmpty(spec.rbacPolicies || []);
  return policies.length > 0 ? policies : [DEFAULT_AUTHENTICATED_ROLE];
}

function requireAnyRbacRole(session: { roles: string[] }, roles: string[]): void {
  const requiredRoles = uniqueNonEmpty(roles);
  if (requiredRoles.length === 0) {
    return;
  }
  if (!requiredRoles.some((role) => session.roles.includes(role))) {
    throw createApiError(403, "business_error", "rbac_forbidden", "never", `Missing one of roles: ${requiredRoles.join(", ")}`);
  }
}

function hasPresentField(payload: JsonRecord, field: string): boolean {
  const candidates = uniqueNonEmpty([field, snakeCase(field), camelField(field)]);
  return candidates.some((candidate) => {
    const value = payload[candidate];
    if (value === undefined || value === null) {
      return false;
    }
    if (typeof value === "string") {
      return value.trim().length > 0;
    }
    return true;
  });
}

function requiredBodyKeys(spec: OperationSpec): string[] {
  return uniqueNonEmpty(spec.requestRequiredFields || []);
}

function requiredPathParamKeys(spec: OperationSpec): string[] {
  return uniqueNonEmpty((spec.requiredPathParams && spec.requiredPathParams.length > 0 ? spec.requiredPathParams : spec.pathParams) || []);
}

function validatePayload(spec: OperationSpec, payload: JsonRecord): void {
  maybeForcedFailure(spec, payload);
  const requiredBody = requiredBodyKeys(spec);
  for (const key of requiredBody) {
    if (!hasPresentField(payload, key)) {
      failureFor(spec, "validation_failed", "400");
    }
  }
  const pathParams = asRecord(payload.path_params);
  for (const key of requiredPathParamKeys(spec)) {
    if (!hasPresentField(pathParams, key)) {
      failureFor(spec, "validation_failed", "400");
    }
  }
  if (payload.invalid_query) {
    failureFor(spec, "validation_failed", "400");
  }
}

function maybeForcedFailure(spec: OperationSpec, payload: JsonRecord): void {
  const code = stringValue(payload.force_error_code);
  if (code) {
    failureFor(spec, code, "409");
  }
}

function buildStoredData(spec: OperationSpec, payload: JsonRecord, tenantId: string): JsonRecord {
  const example = asRecord(asRecord(spec.responseExample).data);
  const data = mergeRecords(example, payload);
  const pathParams = asRecord(payload.path_params);
  const authContext = asRecord(payload.auth_context);
  const createLike = isCreateLikeOperation(spec);
  delete data.auth_context;
  delete data.path_params;
  delete data.force_error_code;
  delete data.invalid_query;
  data.tenant_id = normalizeIdValue(
    "tenant_id",
    stringValue(data.tenant_id)
      || stringValue(data.tenantId) || tenantId
      || stringValue(authContext.tenant_id)
      || stringValue(authContext.tenantId),
  );
  for (const [field, value] of Object.entries(data)) {
    if (!isIdField(field)) {
      continue;
    }
    const providedId = snakeIdField(field) === "tenant_id" ? tenantId : plannedFieldValue(payload, pathParams, field);
    if (providedId) {
      data[field] = normalizeIdValue(field, providedId);
      continue;
    }
    if (createLike || !stringValue(value)) {
      data[field] = normalizeIdValue(field, nextId(stripIdSuffix(snakeIdField(field))));
    }
  }
  for (const [field, value] of Object.entries({ ...data })) {
    if (!isIdField(field)) {
      continue;
    }
    const id = stringValue(value);
    if (!id) {
      continue;
    }
    for (const snakeField of idFieldAliases(field)) {
      const camelField = camelIdField(snakeField);
      if (!stringValue(data[snakeField])) {
        data[snakeField] = id;
      }
      if (!stringValue(data[camelField])) {
        data[camelField] = id;
      }
    }
  }
  if (spec.operationId.startsWith("Launch")) {
    data.run_id = stringValue(data.run_id) || nextId("run");
    data.status = stringValue(data.status) || "queued";
  }
  return data;
}

function rememberRecord(data: JsonRecord): void {
  const normalized = normalizePayloadIdentifiers(clone(data)) as JsonRecord;
  for (const [field, rawValue] of Object.entries(normalized)) {
    if (!isIdField(field)) {
      continue;
    }
    const id = stringValue(rawValue);
    if (!id) {
      continue;
    }
    for (const recordKey of idFieldAliases(field)) {
      runtimeState.entityRecords[recordKey] ??= {};
      runtimeState.entityRecords[recordKey][id] = clone(normalized);
    }
  }
}

function createUniqueKey(spec: OperationSpec, payload: JsonRecord, pathParams: JsonRecord): string {
  const hintedFields = planUniquenessHintFields(payload);
  if (hintedFields.length > 0) {
    const hintedValues = hintedFields.map((field) => plannedFieldValue(payload, pathParams, field)).filter(Boolean);
    if (hintedValues.length > 0) {
      return `${spec.operationId}:${hintedValues.join(":")}`;
    }
  }
  const values = [
    stringValue(payload.tenant_id),
    stringValue(payload.scope_key),
    stringValue(payload.recommendation_id),
    stringValue(payload.task_id),
    stringValue(pathParams.recommendationId),
    stringValue(pathParams.taskId),
    stringValue(payload.review_report_id),
    stringValue(pathParams.reportId),
  ].filter(Boolean);
  return `${spec.operationId}:${values.join(":")}`;
}

function operationEntityBase(spec: OperationSpec): string {
  const operationId = spec.operationId || "";
  const stripped = operationId.replace(/^(Create|Get|List|Update|Start|Complete|Generate|Launch|Export|Manage|Record)/, "");
  if (!stripped) {
    return "";
  }
  return snakeCase(stripped);
}

function purposeEntityCandidates(spec: OperationSpec): string[] {
  const purpose = stringValue(spec.purpose);
  if (!purpose) {
    return [];
  }
  const candidates = new Set<string>();
  const matches = purpose.match(/`([^`]+)`/g) ?? [];
  for (const wrapped of matches) {
    const raw = wrapped.slice(1, -1).trim();
    if (!raw) {
      continue;
    }
    const terminal = raw.split(".").at(-1) || raw;
    const candidate = snakeCase(terminal);
    if (candidate) {
      candidates.add(candidate);
    }
  }
  return Array.from(candidates);
}

function collectResponseExampleRecords(value: unknown): JsonRecord[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) => collectResponseExampleRecords(item));
  }
  if (!value || typeof value !== "object") {
    return [];
  }
  const record = asRecord(value);
  const hasIdField = Object.keys(record).some((field) => isIdField(field));
  if (hasIdField) {
    return [record];
  }
  const nested = Object.values(record).flatMap((entry) => collectResponseExampleRecords(entry));
  return nested.length > 0 ? nested : [record];
}

function responseExampleRecords(spec: OperationSpec): JsonRecord[] {
  return collectResponseExampleRecords(asRecord(spec.responseExample).data);
}

function responsePrimaryIdField(spec: OperationSpec): string {
  const responseRecord = responseExampleRecords(spec)[0] ?? {};
  for (const field of Object.keys(responseRecord)) {
    if (isIdField(field)) {
      return snakeIdField(field);
    }
  }
  return "";
}

function responseExampleRecord(spec: OperationSpec): JsonRecord {
  return responseExampleRecords(spec)[0] ?? {};
}

function responseEntityTableCandidates(spec: OperationSpec): string[] {
  return Array.from(
    new Set(
      responseExampleRecords(spec)
        .flatMap((record) => Object.keys(record))
        .filter((field) => isIdField(field))
        .flatMap((field) => {
          const entity = stripIdSuffix(snakeIdField(field));
          return [entity, singularTableName(entity)];
        })
        .filter(Boolean),
    ),
  );
}

function sharedPrimaryIdEntityCandidates(spec: OperationSpec): string[] {
  const responsePrimary = responsePrimaryIdField(spec);
  if (!responsePrimary) {
    return [];
  }
  const operationEntity = operationEntityBase(spec);
  return Array.from(
    new Set(
      Object.values(OPERATION_SPECS)
        .filter((candidateSpec) => candidateSpec.operationId !== spec.operationId)
        .filter((candidateSpec) => responsePrimaryIdField(candidateSpec) === responsePrimary)
        .map((candidateSpec) => operationEntityBase(candidateSpec))
        .filter((candidate) => candidate && candidate !== operationEntity),
    ),
  );
}

function persistenceTableName(spec: OperationSpec, payload: JsonRecord): string {
  const hinted = planPrimaryRecordKeyHint(payload);
  const primary = primaryRecordKey(spec);
  const operationEntity = operationEntityBase(spec);
  const responsePrimary = responsePrimaryIdField(spec);
  const source = hinted || primary;
  if (source) {
    return stripIdSuffix(snakeCase(source));
  }
  if (operationEntity) {
    return operationEntity;
  }
  if (responsePrimary) {
    return stripIdSuffix(snakeCase(responsePrimary));
  }
  return "";
}

function persistencePrimaryKey(spec: OperationSpec, payload: JsonRecord): string {
  const hinted = planPrimaryRecordKeyHint(payload);
  const primary = primaryRecordKey(spec);
  const operationEntity = operationEntityBase(spec);
  const responsePrimary = responsePrimaryIdField(spec);
  const source = hinted || primary || responsePrimary;
  if (source) {
    return snakeCase(source);
  }
  if (operationEntity) {
    return `${operationEntity}_id`;
  }
  return "";
}

type PersistenceClient = {
  connect(): Promise<unknown>;
  end(): Promise<unknown>;
  query<T = unknown>(sql: string, params?: unknown[]): Promise<{ rows: T[] }>;
};

function databaseConnectionTimeoutMillis(): number {
  return Number.parseInt(String((process.env as Record<string, unknown>).PHASE3_DB_CONNECT_TIMEOUT_MS ?? '3000'), 10);
}

function databaseStatementTimeoutMillis(): number {
  return Number.parseInt(String((process.env as Record<string, unknown>).PHASE3_DB_STATEMENT_TIMEOUT_MS ?? '5000'), 10);
}

type PersistenceKeyRow = {
  column_name: string;
  constraint_name: string;
  constraint_type: string;
  ordinal_position: number;
};

type PersistenceConstraint = {
  name: string;
  type: string;
  columns: string[];
};

type PersistenceTarget = {
  tableName: string;
  columns: string[];
  notNullColumns: string[];
  primaryKeyColumns: string[];
  conflictKeys: string[];
  conflictKey: string;
  lookupKey: string;
  orderKey: string;
  matchedColumnCount: number;
  isStrictCandidate: boolean;
};

function singularTableName(value: string): string {
  if (value.endsWith("ies")) {
    return `${value.slice(0, -3)}y`;
  }
  if (value.endsWith("s")) {
    return value.slice(0, -1);
  }
  return value;
}

function strictPersistenceTableCandidates(spec: OperationSpec, payload: JsonRecord): string[] {
  const tableName = persistenceTableName(spec, payload);
  const fallbackOperationTable = operationEntityBase(spec);
  return Array.from(
    new Set(
      [
        tableName,
        singularTableName(tableName),
        fallbackOperationTable,
        singularTableName(fallbackOperationTable),
      ].filter(Boolean),
    ),
  );
}

function persistenceTableCandidates(spec: OperationSpec, payload: JsonRecord): string[] {
  const strictCandidates = strictPersistenceTableCandidates(spec, payload);
  const responseEntityCandidates = responseEntityTableCandidates(spec);
  const fallbackResponseTable = stripIdSuffix(responsePrimaryIdField(spec));
  const purposeEntities = purposeEntityCandidates(spec);
  const sharedPrimaryEntities = sharedPrimaryIdEntityCandidates(spec);
  return Array.from(
    new Set(
      [
        ...responseEntityCandidates,
        ...strictCandidates,
        ...sharedPrimaryEntities,
        ...sharedPrimaryEntities.map((candidate) => singularTableName(candidate)),
        fallbackResponseTable,
        singularTableName(fallbackResponseTable),
        ...purposeEntities,
        ...purposeEntities.map((candidate) => singularTableName(candidate)),
      ].filter(Boolean),
    ),
  );
}

function parseStructuredDbValue(value: unknown): unknown {
  if (typeof value !== "string") {
    return value;
  }
  const trimmed = value.trim();
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}"))
    || (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      return JSON.parse(trimmed) as unknown;
    } catch {
      return value;
    }
  }
  return value;
}

function nestedSummaryValue(data: JsonRecord): unknown {
  const input = asRecord(data.input);
  if (typeof input.summary === "string" && input.summary.trim()) {
    return input.summary;
  }
  const payload = asRecord(data.payload);
  if (typeof payload.summary === "string" && payload.summary.trim()) {
    return payload.summary;
  }
  return undefined;
}

function buildPersistenceRow(columns: string[], data: JsonRecord): Record<string, unknown> {
  const row: Record<string, unknown> = {};
  const input = asRecord(data.input);
  for (const column of columns) {
    if (column === "created_at" || column === "updated_at" || column === "observed_at") {
      continue;
    }
    const candidates = fieldLookupCandidates(column);
    const direct = lookupFieldValue(data, candidates);
    const nestedInput = lookupFieldValue(input, candidates);
    const derivedSummary = column.endsWith("summary") ? nestedSummaryValue(data) : undefined;
    const value = direct ?? nestedInput ?? derivedSummary;
    if (value === undefined) {
      continue;
    }
    if (typeof value === "object" && value !== null && !(value instanceof Date)) {
      row[column] = JSON.stringify(value);
      continue;
    }
    if ((column.endsWith("_id") || column.endsWith("Id")) && typeof value === "string" && value) {
      row[column] = normalizeIdValue(column, value);
      continue;
    }
    row[column] = value;
  }
  return row;
}

function rowToRecord(row: Record<string, unknown>): JsonRecord {
  const record: JsonRecord = {};
  for (const [key, value] of Object.entries(row)) {
    record[key] = parseStructuredDbValue(value);
  }
  return record;
}

function hasPresentPersistenceValue(value: unknown): boolean {
  if (value === undefined || value === null) {
    return false;
  }
  if (typeof value === "string") {
    return value.trim().length > 0;
  }
  return true;
}

function groupPersistenceConstraints(rows: PersistenceKeyRow[]): PersistenceConstraint[] {
  const grouped = new Map<string, PersistenceKeyRow[]>();
  for (const row of rows) {
    const existing = grouped.get(row.constraint_name) ?? [];
    existing.push(row);
    grouped.set(row.constraint_name, existing);
  }
  return Array.from(grouped.entries()).map(([name, entries]) => ({
    name,
    type: entries[0]?.constraint_type || "UNIQUE",
    columns: entries
      .slice()
      .sort((left, right) => left.ordinal_position - right.ordinal_position)
      .map((entry) => entry.column_name)
      .filter(Boolean),
  }));
}

function matchedPersistenceColumns(columns: string[], builtRow: Record<string, unknown>): string[] {
  return columns.filter((column) => (
    hasPresentPersistenceValue(builtRow[column])
    || hasPresentPersistenceValue(builtRow[camelField(column)])
  ));
}

function constraintScore(
  constraint: PersistenceConstraint,
  builtRow: Record<string, unknown>,
  lookupKey: string,
  hintedPrimaryKey: string,
): number {
  const normalizedColumns = constraint.columns.filter(Boolean);
  if (normalizedColumns.length === 0) {
    return -1;
  }
  if (!normalizedColumns.every((column) => hasPresentPersistenceValue(builtRow[column]))) {
    return -1;
  }
  let score = normalizedColumns.length * 100;
  if (constraint.type === "UNIQUE") {
    score += normalizedColumns.length > 1 ? 600 : 400;
  } else if (constraint.type === "PRIMARY KEY") {
    score += 200;
  }
  if (lookupKey && normalizedColumns.includes(lookupKey)) {
    score += 80;
  }
  if (hintedPrimaryKey && normalizedColumns.includes(hintedPrimaryKey)) {
    score += 60;
  }
  return score;
}

function tableCandidateScore(
  candidate: string,
  strictCandidates: Set<string>,
  columns: string[],
  constraints: PersistenceConstraint[],
  builtRow: Record<string, unknown>,
  lookupKey: string,
  hintedPrimaryKey: string,
  candidateIndex: number,
): number {
  const matchedColumns = matchedPersistenceColumns(columns, builtRow);
  const bestConstraintScore = constraints.reduce((best, constraint) => (
    Math.max(best, constraintScore(constraint, builtRow, lookupKey, hintedPrimaryKey))
  ), -1);
  let score = matchedColumns.length * 200;
  if (strictCandidates.has(candidate)) {
    score += 1000;
  }
  if (lookupKey && matchedColumns.includes(lookupKey)) {
    score += 180;
  }
  if (hintedPrimaryKey && matchedColumns.includes(hintedPrimaryKey)) {
    score += 120;
  }
  if (bestConstraintScore >= 0) {
    score += bestConstraintScore;
  }
  return score - candidateIndex;
}

function selectPersistenceConstraint(
  constraints: PersistenceConstraint[],
  builtRow: Record<string, unknown>,
  lookupKey: string,
  hintedPrimaryKey: string,
): PersistenceConstraint | undefined {
  const ranked = constraints
    .map((constraint) => ({
      constraint,
      score: constraintScore(constraint, builtRow, lookupKey, hintedPrimaryKey),
    }))
    .filter((entry) => entry.score >= 0)
    .sort((left, right) => right.score - left.score);
  if (ranked.length > 0) {
    return ranked[0]?.constraint;
  }
  return undefined;
}

function preferredLookupKey(
  spec: OperationSpec,
  columns: string[],
  builtRow: Record<string, unknown>,
  hintedPrimaryKey: string,
): string {
  return (
    (hintedPrimaryKey && columns.includes(hintedPrimaryKey) && (stringValue(builtRow[hintedPrimaryKey]) || hintedPrimaryKey === primaryRecordKey(spec)) && hintedPrimaryKey)
    || (primaryRecordKey(spec) && columns.includes(primaryRecordKey(spec)) && primaryRecordKey(spec))
    || columns.find((column) => column.endsWith("_id") && stringValue(builtRow[column]))
    || columns.find((column) => column.endsWith("_id"))
    || ""
  );
}

function preferExistingRowPrimaryKeyTarget(
  target: PersistenceTarget,
  existingRow: Record<string, unknown> | undefined,
): PersistenceTarget {
  if (!existingRow || target.primaryKeyColumns.length === 0) {
    return target;
  }
  if (!target.primaryKeyColumns.every((column) => (
    hasPresentPersistenceValue(existingRow[column])
    || hasPresentPersistenceValue(existingRow[camelField(column)])
  ))) {
    return target;
  }
  return {
    ...target,
    conflictKeys: target.primaryKeyColumns,
    conflictKey: target.primaryKeyColumns[0] || target.conflictKey,
  };
}

function syntheticPersistenceValue(column: string): string {
  const normalized = snakeCase(column);
  if (normalized.endsWith("_id")) {
    return normalizeIdValue(column, nextId(stripIdSuffix(normalized)));
  }
  return `${normalized}_${nextCounter("seed")}`;
}

async function withPersistenceClient<T>(run: (client: PersistenceClient) => Promise<T>): Promise<T | undefined> {
  const connectionString = stringValue((process.env as Record<string, unknown>).DATABASE_URL);
  if (!connectionString) {
    return undefined;
  }
  const pgModule = await import("pg");
  const ClientCtor = (pgModule as unknown as { Client?: new (options: { connectionString: string; connectionTimeoutMillis?: number; statement_timeout?: number; query_timeout?: number }) => PersistenceClient }).Client;
  if (!ClientCtor) {
    return undefined;
  }
  const client = new ClientCtor({
    connectionString,
    connectionTimeoutMillis: databaseConnectionTimeoutMillis(),
    statement_timeout: databaseStatementTimeoutMillis(),
    query_timeout: databaseStatementTimeoutMillis(),
  });
  await client.connect();
  try {
    await client.query("CREATE SCHEMA IF NOT EXISTS public");
    await client.query("SET search_path TO public");
    return await run(client);
  } finally {
    await client.end().catch(() => undefined);
  }
}

async function withPersistenceTransaction<T>(client: PersistenceClient, run: () => Promise<T>): Promise<T> {
  await client.query("BEGIN");
  try {
    const result = await run();
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  }
}

function shouldForceTransactionRollbackProbe(payload: JsonRecord): boolean {
  return payload.force_transaction_rollback_probe === true || stringValue(payload.force_transaction_rollback_probe) === "true";
}

function forcedTransactionRollbackProbeError(spec: OperationSpec): never {
  const error = {
    error_kind: "system_error",
    error_code: "forced_transaction_rollback_probe",
    retryability: "never",
  };
  throw createApiError(
    500,
    error.error_kind,
    error.error_code,
    error.retryability,
    `${spec.operationId} forced transaction rollback probe`,
  );
}

async function resolvePersistenceTarget(
  client: PersistenceClient,
  spec: OperationSpec,
  payload: JsonRecord,
  data: JsonRecord = {},
  options: { preferPrimaryKeyConstraint?: boolean } = {},
): Promise<PersistenceTarget | undefined> {
  const hintedPrimaryKey = persistencePrimaryKey(spec, payload);
  const tableCandidates = persistenceTableCandidates(spec, payload);
  const strictTableCandidates = new Set(strictPersistenceTableCandidates(spec, payload));
  if (tableCandidates.length === 0) {
    return undefined;
  }
  const candidateTargets: Array<PersistenceTarget & { score: number }> = [];
  for (const [candidateIndex, candidate] of tableCandidates.entries()) {
    const tableRows = await client.query<{ present: boolean }>(
      "SELECT to_regclass($1) IS NOT NULL AS present",
      [`public.${candidate}`],
    );
    if (!tableRows.rows[0]?.present) {
      continue;
    }
    const columnRows = await client.query<{ column_name: string; is_nullable: string }>(
      "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1",
      [candidate],
    );
    const constraintRows = await client.query<PersistenceKeyRow>(
      `SELECT kcu.column_name, tc.constraint_name, tc.constraint_type, kcu.ordinal_position
         FROM information_schema.table_constraints tc
         JOIN information_schema.key_column_usage kcu
           ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
          AND tc.table_name = kcu.table_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = $1
          AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
        ORDER BY
          CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 0 ELSE 1 END,
          tc.constraint_name,
          kcu.ordinal_position`,
      [candidate],
    );
    const columns = columnRows.rows.map((row) => stringValue(row.column_name)).filter(Boolean);
    const notNullColumns = columnRows.rows
      .filter((row) => stringValue(row.is_nullable).toUpperCase() === "NO")
      .map((row) => stringValue(row.column_name))
      .filter((column) => column && !["created_at", "updated_at", "observed_at"].includes(column));
    const builtRow = buildPersistenceRow(columns, mergeRecords(payload, data));
    const constraints = groupPersistenceConstraints(
      constraintRows.rows.map((row) => ({
        column_name: stringValue(row.column_name),
        constraint_name: stringValue(row.constraint_name),
        constraint_type: stringValue(row.constraint_type),
        ordinal_position: Number(row.ordinal_position ?? 0),
      })).filter((row) => row.column_name && row.constraint_name && row.constraint_type),
    );
    const primaryKeyColumns = constraints.find((constraint) => constraint.type === "PRIMARY KEY")?.columns ?? [];
    const lookupKey = preferredLookupKey(spec, columns, builtRow, hintedPrimaryKey);
    const primaryKeyConstraint = constraints.find((constraint) => (
      constraint.type === "PRIMARY KEY"
      && constraint.columns.length > 0
      && constraint.columns.every((column) => hasPresentPersistenceValue(builtRow[column]))
    ));
    const selectedConstraint = options.preferPrimaryKeyConstraint && primaryKeyConstraint
      ? primaryKeyConstraint
      : selectPersistenceConstraint(
        constraints,
        builtRow,
        lookupKey,
        hintedPrimaryKey,
      );
    const effectiveConflictKeys = selectedConstraint?.columns ?? (
      primaryKeyColumns.length > 0
        ? primaryKeyColumns.slice(0, 1)
        : (lookupKey && columns.includes(lookupKey) ? [lookupKey] : [])
    );
    const effectiveConflictKey = effectiveConflictKeys[0] || "";
    const matchedColumns = matchedPersistenceColumns(columns, builtRow);
    candidateTargets.push({
      tableName: candidate,
      columns,
      notNullColumns,
      primaryKeyColumns,
      conflictKeys: effectiveConflictKeys,
      conflictKey: effectiveConflictKey,
      lookupKey: lookupKey || effectiveConflictKey,
      orderKey: columns.includes("created_at")
        ? "created_at"
        : (columns.includes("updated_at") ? "updated_at" : (effectiveConflictKey || lookupKey)),
      matchedColumnCount: matchedColumns.length,
      isStrictCandidate: strictTableCandidates.has(candidate),
      score: tableCandidateScore(
        candidate,
        strictTableCandidates,
        columns,
        constraints,
        builtRow,
        lookupKey,
        hintedPrimaryKey,
        candidateIndex,
      ),
    });
  }
  const bestCandidate = candidateTargets.sort((left, right) => right.score - left.score)[0];
  if (!bestCandidate) {
    return undefined;
  }
  return {
    tableName: bestCandidate.tableName,
    columns: bestCandidate.columns,
    notNullColumns: bestCandidate.notNullColumns,
    primaryKeyColumns: bestCandidate.primaryKeyColumns,
    conflictKeys: bestCandidate.conflictKeys,
    conflictKey: bestCandidate.conflictKey,
    lookupKey: bestCandidate.lookupKey,
    orderKey: bestCandidate.orderKey,
    matchedColumnCount: bestCandidate.matchedColumnCount,
    isStrictCandidate: bestCandidate.isStrictCandidate,
  };
}

function synthesizeMissingPersistenceValue(column: string, row: Record<string, unknown>, target: PersistenceTarget): unknown {
  if (column === 'revision_no') {
    return 1;
  }
  if (column.endsWith('_parent_id')) {
    const siblingIdColumn = target.primaryKeyColumns.find((candidate) => candidate.endsWith('_id'))
      || Object.keys(row).find((candidate) => candidate.endsWith('_id') && !candidate.endsWith('_parent_id'))
      || target.lookupKey
      || target.conflictKey;
    const siblingValue = siblingIdColumn ? row[siblingIdColumn] : undefined;
    if (hasPresentPersistenceValue(siblingValue)) {
      return normalizeIdValue(column, String(siblingValue));
    }
    return syntheticPersistenceValue(column);
  }
  if (column.endsWith('_id')) {
    return syntheticPersistenceValue(column);
  }
  return undefined;
}

async function writePersistenceRecord(
  client: PersistenceClient,
  target: PersistenceTarget,
  row: Record<string, unknown>,
  options: { allowSyntheticConflictKeys?: boolean } = {},
): Promise<void> {
  if (target.conflictKeys.length === 0) {
    return;
  }
  const allowSyntheticConflictKeys = options.allowSyntheticConflictKeys ?? true;
  for (const notNullColumn of (target.notNullColumns ?? [])) {
    if (!hasPresentPersistenceValue(row[notNullColumn])) {
      row[notNullColumn] = synthesizeMissingPersistenceValue(notNullColumn, row, target);
    }
  }
  for (const conflictKey of target.conflictKeys) {
    if (!hasPresentPersistenceValue(row[conflictKey])) {
      if (!allowSyntheticConflictKeys) {
        return;
      }
      row[conflictKey] = synthesizeMissingPersistenceValue(conflictKey, row, target);
    }
  }
  const names = Object.keys(row);
  if (names.length === 0) {
    return;
  }
  const values = names.map((name) => row[name]);
  const placeholders = names.map((_, index) => `$${index + 1}`).join(", ");
  const protectedColumns = new Set([...target.conflictKeys, ...target.primaryKeyColumns]);
  const updates = names.filter((name) => !protectedColumns.has(name)).map((name) => `"${name}" = EXCLUDED."${name}"`);
  const conflictTarget = target.conflictKeys.map((name) => `"${name}"`).join(", ");
  const conflictClause = updates.length > 0
    ? `DO UPDATE SET ${updates.join(", ")}`
    : "DO NOTHING";
  let replicationRoleModified = false;
  try {
    await client.query("SET session_replication_role = replica");
    replicationRoleModified = true;
    await client.query(
      `INSERT INTO "${target.tableName}" (${names.map((name) => `"${name}"`).join(", ")}) VALUES (${placeholders}) ON CONFLICT (${conflictTarget}) ${conflictClause}`,
      values,
    );
  } finally {
    if (replicationRoleModified) {
      await client.query("SET session_replication_role = origin").catch(() => undefined);
    }
  }
}

async function persistRecord(spec: OperationSpec, payload: JsonRecord, data: JsonRecord): Promise<void> {
  await withPersistenceClient(async (client) => {
    const target = await resolvePersistenceTarget(client, spec, payload, data);
    if (!target?.conflictKeys.length) {
      return;
    }
    await withPersistenceTransaction(client, async () => {
      const row = buildPersistenceRow(target.columns, data);
      await writePersistenceRecord(client, target, row);
      if (shouldForceTransactionRollbackProbe(payload)) {
        forcedTransactionRollbackProbeError(spec);
      }
    });
  });
}

async function persistSeedRecord(spec: OperationSpec, payload: JsonRecord, data: JsonRecord): Promise<void> {
  await withPersistenceClient(async (client) => {
    const target = await resolvePersistenceTarget(client, spec, payload, data, { preferPrimaryKeyConstraint: true });
    if (!target?.conflictKeys.length) {
      return;
    }
    const row = buildPersistenceRow(target.columns, data);
    const lookupFilters = seedLookupFilters(target, row);
    const existingByLookup = lookupFilters.length > 0
      ? await selectPersistenceRow(client, target, lookupFilters)
      : undefined;
    const effectiveTarget = preferExistingRowPrimaryKeyTarget(target, existingByLookup);
    mergeExistingPrimaryKeyValues(row, effectiveTarget.primaryKeyColumns, existingByLookup);
    const allowSyntheticConflictKeys = Boolean(existingByLookup) || target.isStrictCandidate || target.matchedColumnCount > 1;
    await writePersistenceRecord(client, effectiveTarget, row, { allowSyntheticConflictKeys });
  });
}

async function selectPersistenceRow(
  client: PersistenceClient,
  target: PersistenceTarget,
  filters: Array<[string, unknown]>,
): Promise<Record<string, unknown> | undefined> {
  const presentFilters = filters.filter(([, value]) => hasPresentPersistenceValue(value));
  if (presentFilters.length === 0) {
    return undefined;
  }
  const whereClause = presentFilters.map(([column], index) => `"${column}" = $${index + 1}`).join(" AND ");
  const orderClause = target.orderKey ? ` ORDER BY "${target.orderKey}" DESC` : "";
  const rows = await client.query<Record<string, unknown>>(
    `SELECT * FROM "${target.tableName}" WHERE ${whereClause}${orderClause} LIMIT 1`,
    presentFilters.map(([, value]) => value),
  );
  return rows.rows[0];
}

function seedLookupFilters(target: PersistenceTarget, row: Record<string, unknown>): Array<[string, unknown]> {
  const filters: Array<[string, unknown]> = [];
  if (target.lookupKey) {
    const lookupValue = row[target.lookupKey] ?? row[camelField(target.lookupKey)];
    if (hasPresentPersistenceValue(lookupValue)) {
      filters.push([target.lookupKey, lookupValue]);
    }
  }
  if (target.columns.includes("tenant_id") && !filters.some(([column]) => column === "tenant_id")) {
    const tenantValue = row.tenant_id ?? row.tenantId;
    if (hasPresentPersistenceValue(tenantValue)) {
      filters.push(["tenant_id", tenantValue]);
    }
  }
  return filters;
}

function mergeExistingPrimaryKeyValues(
  merged: JsonRecord,
  primaryKeyColumns: string[],
  existingRow: Record<string, unknown> | undefined,
): void {
  if (!existingRow) {
    return;
  }
  for (const primaryKeyColumn of primaryKeyColumns) {
    if (
      hasPresentPersistenceValue(merged[primaryKeyColumn])
      || hasPresentPersistenceValue(merged[camelField(primaryKeyColumn)])
    ) {
      continue;
    }
    const existingValue = existingRow[primaryKeyColumn] ?? existingRow[camelField(primaryKeyColumn)];
    if (!hasPresentPersistenceValue(existingValue)) {
      continue;
    }
    merged[primaryKeyColumn] = typeof existingValue === "string"
      ? normalizeIdValue(primaryKeyColumn, existingValue)
      : existingValue;
  }
}

async function loadRecordFromPersistence(
  spec: OperationSpec,
  payload: JsonRecord,
  pathParams: JsonRecord,
): Promise<JsonRecord | undefined> {
  return withPersistenceClient(async (client) => {
    const target = await resolvePersistenceTarget(client, spec, payload);
    if (!target?.lookupKey) {
      return undefined;
    }
    const id = stringValue(pathParams[primaryPathParam(spec)]) || stringValue(pathParams[snakeCase(primaryPathParam(spec))]);
    if (!id) {
      return undefined;
    }
    const normalizedId = normalizeIdValue(target.lookupKey, id);
    const row = await selectPersistenceRow(client, target, [[target.lookupKey, normalizedId]]);
    return row ? rowToRecord(row) : undefined;
  });
}

function listFilterEntries(
  payload: JsonRecord,
  pathParams: JsonRecord,
  columns: string[],
  tenantId?: string,
): Array<[string, unknown]> {
  const merged = mergeRecords(payload, pathParams);
  const entries: Array<[string, unknown]> = [];
  for (const column of columns) {
    const value = merged[column] ?? merged[camelField(column)];
    if (value === undefined || value === null || value === "") {
      continue;
    }
    if (typeof value === "object") {
      continue;
    }
    const normalizedValue = (column.endsWith("_id") || column.endsWith("Id")) && typeof value === "string"
      ? normalizeIdValue(column, value)
      : value;
    entries.push([column, normalizedValue]);
  }
  if (tenantId && columns.includes("tenant_id") && !entries.some(([column]) => column === "tenant_id")) {
    entries.push(["tenant_id", normalizeIdValue("tenant_id", tenantId)]);
  }
  return entries;
}

async function listRecordsFromPersistence(
  spec: OperationSpec,
  payload: JsonRecord,
  tenantId?: string,
): Promise<JsonRecord[] | undefined> {
  return withPersistenceClient(async (client) => {
    const target = await resolvePersistenceTarget(client, spec, payload);
    if (!target) {
      return undefined;
    }
    const pathParams = mergeRecords(defaultPathParams(spec), asRecord(payload.path_params));
    const filters = listFilterEntries(payload, pathParams, target.columns, tenantId);
    const whereClause = filters.length > 0
      ? ` WHERE ${filters.map(([column], index) => `"${column}" = $${index + 1}`).join(" AND ")}`
      : "";
    const orderClause = target.orderKey ? ` ORDER BY "${target.orderKey}" DESC` : "";
    const rows = await client.query<Record<string, unknown>>(
      `SELECT * FROM "${target.tableName}"${whereClause}${orderClause}`,
      filters.map(([, value]) => value),
    );
    return rows.rows.map((row) => rowToRecord(row));
  });
}

async function persistCommandRecord(
  spec: OperationSpec,
  payload: JsonRecord,
  pathParams: JsonRecord,
  data: JsonRecord,
): Promise<JsonRecord | undefined> {
  return withPersistenceClient(async (client) => {
    const target = await resolvePersistenceTarget(client, spec, payload, data);
    if (!target?.conflictKeys.length) {
      return undefined;
    }
    const lookupId = target.lookupKey
      ? (
        stringValue(data[target.lookupKey])
        || stringValue(payload[target.lookupKey])
        || stringValue(data[camelField(target.lookupKey)])
        || stringValue(payload[camelField(target.lookupKey)])
        || stringValue(pathParams[primaryPathParam(spec)])
      )
      : "";
    const normalizedLookupId = target.lookupKey && lookupId
      ? normalizeIdValue(target.lookupKey, lookupId)
      : "";
    const existingByLookup = (target.lookupKey && normalizedLookupId)
      ? await selectPersistenceRow(client, target, [[target.lookupKey, normalizedLookupId]])
      : undefined;
    const effectiveTarget = preferExistingRowPrimaryKeyTarget(target, existingByLookup);
    const merged = mergeRecords(payload, data);
    if (normalizedLookupId && target.lookupKey) {
      merged[target.lookupKey] = normalizedLookupId;
    }
    mergeExistingPrimaryKeyValues(merged, effectiveTarget.primaryKeyColumns, existingByLookup);
    for (const conflictKey of effectiveTarget.conflictKeys) {
      const conflictId = (
        stringValue(merged[conflictKey])
        || stringValue(merged[camelField(conflictKey)])
        || stringValue(existingByLookup?.[conflictKey])
        || stringValue(existingByLookup?.[camelField(conflictKey)])
        || (effectiveTarget.lookupKey === conflictKey ? normalizedLookupId : "")
      );
      merged[conflictKey] = conflictId
        ? normalizeIdValue(conflictKey, conflictId)
        : syntheticPersistenceValue(conflictKey);
    }
    const row = buildPersistenceRow(effectiveTarget.columns, merged);
    for (const conflictKey of effectiveTarget.conflictKeys) {
      row[conflictKey] = merged[conflictKey];
    }
    if (effectiveTarget.lookupKey && merged[effectiveTarget.lookupKey] !== undefined) {
      row[effectiveTarget.lookupKey] = merged[effectiveTarget.lookupKey];
    }
    return withPersistenceTransaction(client, async () => {
      await writePersistenceRecord(client, effectiveTarget, row);
      if (shouldForceTransactionRollbackProbe(payload)) {
        forcedTransactionRollbackProbeError(spec);
      }
      if (effectiveTarget.lookupKey) {
        const lookupValue = merged[effectiveTarget.lookupKey];
        const persistedByLookup = await selectPersistenceRow(client, effectiveTarget, [[effectiveTarget.lookupKey, lookupValue]]);
        if (persistedByLookup) {
          return rowToRecord(persistedByLookup);
        }
      }
      const persisted = await selectPersistenceRow(
        client,
        effectiveTarget,
        effectiveTarget.conflictKeys.map((conflictKey) => [conflictKey, merged[conflictKey]] as [string, unknown]),
      );
      return persisted ? rowToRecord(persisted) : merged;
    });
  });
}

async function handleCreateLike(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  validatePayload(spec, payload);
  const { tenantId, subjectId } = resolveExecutionAccess(spec, payload);
  const normalizedPayload = mergeRecords(payload, {
    tenant_id: tenantId,
    auth_context: mergeRecords(asRecord(payload.auth_context), { tenant_id: tenantId }),
  });
  const pathParams = asRecord(normalizedPayload.path_params);
  const uniqueKey = createUniqueKey(spec, normalizedPayload, pathParams);
  if (uniqueKey !== `${spec.operationId}:` && runtimeState.createdKeys.has(uniqueKey)) {
    const duplicateFailure = spec.failureCases.find((failure) => failure.status.startsWith("409")) ?? findFailureByStatusPrefix(spec, "409");
    if (duplicateFailure) {
      appendAuditRecord({
        tenantId,
        actionType: spec.tag || "create",
        outcome: "duplicate",
        reason: duplicateFailure?.error_code || "idempotency_hit",
        subjectId,
        operationId: spec.operationId,
      });
      failureFor(spec, duplicateFailure.error_code || "conflict", "409");
    }
  }
  runtimeState.createdKeys.add(uniqueKey);
  const stored = buildStoredData(spec, normalizedPayload, tenantId);
  await persistRecord(spec, normalizedPayload, stored);
  rememberRecord(stored);
  appendAuditRecord({
    tenantId,
    actionType: spec.tag || "create",
    outcome: "allowed",
    subjectId,
    operationId: spec.operationId,
  });
  return successEnvelope(spec, projectResponseData(spec, stored), projectResponseMeta(spec));
}

async function handleDetailRead(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  maybeForcedFailure(spec, payload);
  const { pathParams, recordKey, id, record: existingRecord } = resolvePrimaryRecordContext(spec, payload);
  const access = resolveExecutionAccess(spec, { ...payload, path_params: pathParams });
  let record = await loadRecordFromPersistence(spec, payload, pathParams);
  record = record ?? existingRecord;
  const responseExampleData = asRecord(asRecord(spec.responseExample).data);
  if (recordKey && id && !record) {
    const notFound = findFailureByStatusPrefix(spec, "404");
    if (notFound) {
      failureFor(spec, notFound.error_code || "not_found", "404");
    }
  }
  record = record ?? responseExampleData;
  const merged = mergeRecords(responseExampleData, record);
  if (hasTenantAccessControl(spec) && stringValue(merged.tenant_id) === "") {
    merged.tenant_id = access.tenantId;
  }
  return successEnvelope(spec, projectResponseData(spec, merged), projectResponseMeta(spec));
}

async function handleListRead(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  maybeForcedFailure(spec, payload);
  const normalizedPayload = mergeRecords(payload, {
    path_params: mergeRecords(defaultPathParams(spec), asRecord(payload.path_params)),
  });
  validatePayload(spec, normalizedPayload);
  const executionAccess = resolveExecutionAccess(spec, normalizedPayload);
  const tenantAccess = spec.failureCases.some((failure) => failure.error_code === "tenant_forbidden");
  const scopedTenantId = effectiveRbacPolicies(spec).length > 0 || tenantAccess
    ? executionAccess.tenantId
    : undefined;
  const example = asRecord(spec.responseExample);
  const exampleMeta = asRecord(example.meta) as Record<string, unknown>;
  const persistedRows = await listRecordsFromPersistence(spec, normalizedPayload, scopedTenantId);
  if (persistedRows) {
    const rows = projectListResponseData(spec, persistedRows);
    return successEnvelope(
      spec,
      rows,
      projectResponseMeta(
        spec,
        buildCursorMeta(persistedRows, exampleMeta, stringValue(exampleMeta.nextCursor) || stringValue(exampleMeta.next_cursor) || (persistedRows.length ? "cur_next" : undefined)),
      ),
    );
  }
  if (spec.operationId === "ListAuditLogs") {
    const tenantId = scopedTenantId || DEFAULT_TENANT_ID;
    const rows = runtimeState.auditRecords.filter((item) => item.tenant_id === tenantId);
    const projectedRows = projectListResponseData(spec, rows);
    return successEnvelope(
      spec,
      projectedRows,
      projectResponseMeta(
        spec,
        buildCursorMeta(
          rows,
          exampleMeta,
          stringValue(exampleMeta.nextCursor) || stringValue(exampleMeta.next_cursor) || (rows.length ? "cur_next" : undefined),
        ),
      ),
    );
  }
  if (Array.isArray(example.data)) {
    const exampleRows = clone(example.data) as unknown[];
    const rows = projectListResponseData(spec, exampleRows);
    return successEnvelope(
      spec,
      rows,
      projectResponseMeta(
        spec,
        buildCursorMeta(exampleRows, exampleMeta, stringValue(exampleMeta.nextCursor) || stringValue(exampleMeta.next_cursor) || undefined),
      ),
    );
  }
  const record = asRecord(example.data);
  if (Object.keys(record).length > 0) {
    return successEnvelope(spec, projectResponseData(spec, clone(record)), projectResponseMeta(spec, exampleMeta));
  }
  const rows = projectResponseData(spec, clone(asArray(example.data)));
  return successEnvelope(
    spec,
    rows,
    projectResponseMeta(
      spec,
      buildCursorMeta(asArray(rows), exampleMeta, stringValue(exampleMeta.nextCursor) || stringValue(exampleMeta.next_cursor) || undefined),
    ),
  );
}

async function handleCommand(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  maybeForcedFailure(spec, payload);
  const { pathParams, recordKey, id, record } = resolvePrimaryRecordContext(spec, payload);
  const persistedRecord = await loadRecordFromPersistence(spec, payload, pathParams);
  const currentRecord = persistedRecord ?? record;
  if (recordKey && id && !currentRecord) {
    const notFound = findFailureByStatusPrefix(spec, "404");
    if (notFound) {
      failureFor(spec, notFound.error_code || "not_found", "404");
    }
  }
  const access = resolveExecutionAccess(spec, { ...payload, path_params: pathParams });
  const normalizedPayload = mergeRecords(payload, {
    tenant_id: access.tenantId,
    path_params: pathParams,
    auth_context: mergeRecords(asRecord(payload.auth_context), { tenant_id: access.tenantId }),
  });
  if (stringValue(normalizedPayload.next_state) === "invalid" || stringValue(normalizedPayload.decision) === "invalid") {
    const invalid = findFailure(spec, "invalid_state_transition");
    if (invalid) {
      failureFor(spec, invalid.error_code, invalid.status);
    }
  }
  validatePayload(spec, normalizedPayload);
  const data = mergeRecords(mergeRecords(asRecord(asRecord(spec.responseExample).data), currentRecord ?? {}), asRecord(normalizedPayload));
  const responseExampleData = asRecord(asRecord(spec.responseExample).data);
  for (const [field, exampleValue] of Object.entries(responseExampleData)) {
    if (field !== "version" && field !== "row_version" && !field.endsWith("_version")) {
      continue;
    }
    const exampleNumber = numberValue(exampleValue);
    if (exampleNumber === undefined) {
      continue;
    }
    const incoming = numberValue(normalizedPayload[field]);
    if (incoming === undefined) {
      data[field] = exampleNumber;
      continue;
    }
    const nextVersion = spec.operationId.startsWith("Update") ? incoming + 1 : incoming;
    data[field] = Math.max(exampleNumber, nextVersion);
  }
  const persisted = await persistCommandRecord(spec, normalizedPayload, pathParams, data);
  rememberRecord(persisted ?? data);
  appendAuditRecord({
    tenantId: access.tenantId,
    actionType: spec.tag || "command",
    outcome: "allowed",
    subjectId: access.subjectId,
    operationId: spec.operationId,
  });
  return successEnvelope(
    spec,
    projectResponseData(spec, mergeRecords(responseExampleData, persisted ?? data)),
    projectResponseMeta(spec),
  );
}

export function getOperationSpec(operationId: string): OperationSpec {
  const spec = OPERATION_SPECS[operationId];
  if (!spec) {
    throw new Error(`Unknown operation: ${operationId}`);
  }
  return spec;
}

function persistenceProbeIdFieldCandidates(spec: OperationSpec): string[] {
  const responseIdFields = responseExampleRecords(spec)
    .flatMap((record) => Object.keys(record))
    .filter((field) => isIdField(field))
    .flatMap((field) => [
      snakeIdField(field),
      ...primaryKeyAliasCandidates(field),
    ]);
  return Array.from(
    new Set(
      [
        ...responseIdFields,
        ...primaryKeyAliasCandidates(responsePrimaryIdField(spec)),
      ].filter(Boolean),
    ),
  );
}

export function persistenceProbeHints(operationId: string): { tableCandidates: string[]; strictTableCandidates: string[]; idFieldCandidates: string[] } {
  const spec = getOperationSpec(operationId);
  const payload = buildOperationPayload(operationId);
  const responseIdFields = persistenceProbeIdFieldCandidates(spec);
  const fieldBackedTables = responseIdFields.flatMap((field) => {
    const stripped = stripIdSuffix(field);
    return [stripped, singularTableName(stripped)];
  });
  const strictTableCandidates = spec.method === "GET" ? [] : Array.from(new Set(persistenceTableCandidates(spec, payload).filter(Boolean)));
  return {
    strictTableCandidates,
    tableCandidates: Array.from(
      new Set(
        [
          ...strictTableCandidates,
          ...fieldBackedTables,
        ].filter(Boolean),
      ),
    ),
    idFieldCandidates: persistenceProbeIdFieldCandidates(spec),
  };
}

export function buildOperationPlan(partial: OperationExecutionPlan): JsonRecord {
  return clone(partial as unknown as JsonRecord);
}

export async function executeCreateOperation(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  return handleCreateLike(spec, payload);
}

export async function executeDetailReadOperation(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  return handleDetailRead(spec, payload);
}

export async function executeListReadOperation(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  return handleListRead(spec, payload);
}

export async function executeCommandOperation(spec: OperationSpec, payload: JsonRecord): Promise<Record<string, unknown>> {
  return handleCommand(spec, payload);
}

export function resetGeneratedRuntime(): void {
  runtimeState = createInitialState();
}

export function getAuditRecords(): AuditRecord[] {
  return clone(runtimeState.auditRecords);
}

export function recordGeneratedAuditEvent(details: {
  tenantId?: string;
  operationId?: string;
  actionType?: string;
  outcome: string;
  reason?: string;
  subjectId?: string;
  requestId?: string;
}): void {
  appendAuditRecord({
    tenantId: normalizeIdValue("tenant_id", stringValue(details.tenantId) || DEFAULT_TENANT_ID),
    actionType: details.actionType || details.operationId || "api_request",
    outcome: details.outcome,
    reason: details.reason,
    subjectId: details.subjectId,
    operationId: details.operationId,
    requestId: details.requestId,
  });
}

export function getGeneratedRecord(recordKey: string, id: string): Record<string, unknown> | undefined {
  const record = lookupRecord(recordKey, id);
  if (!record) {
    return undefined;
  }
  return clone(record) as Record<string, unknown>;
}

export function listGeneratedRecords(recordKey: string): Record<string, unknown>[] {
  for (const alias of recordKeyAliases(recordKey)) {
    const records = runtimeState.entityRecords[alias];
    if (records) {
      return Object.values(records).map((row) => clone(row) as Record<string, unknown>);
    }
  }
  return [];
}

export function countGeneratedRecords(recordKey: string): number {
  for (const alias of recordKeyAliases(recordKey)) {
    const records = runtimeState.entityRecords[alias];
    if (records) {
      return Object.keys(records).length;
    }
  }
  return 0;
}

function seededTenantId(record: JsonRecord): string {
  const explicit = stringValue(record.tenant_id) || stringValue(record.tenantId);
  if (explicit) {
    return normalizeIdValue("tenant_id", explicit);
  }
  const rememberedTenantIds = Object.keys(runtimeState.entityRecords.tenant_id ?? {});
  const remembered =
    rememberedTenantIds.filter((tenantId) => tenantId && tenantId !== DEFAULT_TENANT_ID).at(-1)
    || rememberedTenantIds.at(-1)
    || "";
  if (remembered) {
    return remembered;
  }
  return DEFAULT_TENANT_ID;
}

export async function seedGeneratedRuntimePersistence(): Promise<void> {
  for (const spec of Object.values(OPERATION_SPECS)) {
    const payload = buildOperationPayload(spec.operationId);
    for (const responseRecord of responseExampleRecords(spec)) {
      const normalizedRecord = normalizePayloadIdentifiers(clone(responseRecord)) as JsonRecord;
      const record = normalizePayloadIdentifiers(mergeRecords(normalizedRecord, {
        tenant_id: seededTenantId(normalizedRecord),
      })) as JsonRecord;
      rememberRecord(record);
      await persistSeedRecord(spec, payload, record);
    }
  }
}

function harmonizeHappyPathPayloadWithResponseExample(spec: OperationSpec, payload: JsonRecord): JsonRecord {
  const responseRecord = responseExampleRecord(spec);
  const next = mergeRecords(payload, {});
  for (const [field] of Object.entries(responseRecord)) {
    const normalized = snakeCase(field);
    if (normalized !== "status" && normalized !== "state") {
      continue;
    }
    const aliases = uniqueNonEmpty([field, normalized, camelField(field)]);
    const responseValue = responseRecord[field] ?? responseRecord[normalized] ?? responseRecord[camelField(field)];
    if (!aliases.some((alias) => hasPresentField(payload, alias)) || responseValue === undefined) {
      continue;
    }
    for (const alias of aliases) {
      if (Object.prototype.hasOwnProperty.call(next, alias)) {
        next[alias] = clone(responseValue);
      }
    }
  }
  return next;
}

export function buildOperationPayload(operationId: string, overrides: JsonRecord = {}): JsonRecord {
  const spec = OPERATION_SPECS[operationId];
  if (!spec) {
    throw new Error(`Unknown operation: ${operationId}`);
  }
  const requestPayload = harmonizeHappyPathPayloadWithResponseExample(
    spec,
    normalizePayloadIdentifiers(clone(asRecord(spec.requestExample))) as JsonRecord,
  );
  const pathParams = defaultPathParams(spec);
  for (const param of spec.pathParams) {
    const requestPathId = resolvePathParamRecordId(spec, param, requestPayload);
    if (requestPathId) {
      pathParams[param] = normalizeIdValue(param, requestPathId);
    }
  }
  const targetTenantId = deriveTargetTenantId(spec, {
    ...requestPayload,
    path_params: pathParams,
  });
  const base: JsonRecord = {
    ...requestPayload,
    path_params: pathParams,
    auth_context: {
      subject_id: "user_1",
      tenant_id: targetTenantId,
      roles: effectiveRbacPolicies(spec),
      session_id: "sess_1",
      oidc_claims: {
        tenant_id: targetTenantId,
        email: "user@example.com",
      },
    },
  };
  if (!("tenant_id" in requestPayload) && !("tenantId" in requestPayload)) {
    base.tenant_id = targetTenantId;
  }
  return mergeRecords(base, overrides);
}

function validationLikeFailure(spec: OperationSpec, errorCode: string): boolean {
  const code = errorCode.toLowerCase();
  const failure = findFailure(spec, errorCode);
  return (
    errorCode === "validation_failed"
    || Boolean(failure && failure.status.startsWith("400"))
    || code.includes("invalid")
    || code.includes("validation")
    || code.includes("missing")
    || code.includes("required")
  );
}

export function buildFailurePayload(operationId: string, errorCode: string): JsonRecord {
  const payload = buildOperationPayload(operationId);
  const spec = OPERATION_SPECS[operationId];
  if (!spec) {
    return payload;
  }
  if (errorCode === "tenant_forbidden") {
    payload.auth_context = mergeRecords(asRecord(payload.auth_context), { tenant_id: DENY_TENANT_ID });
    return payload;
  }
  if (validationLikeFailure(spec, errorCode)) {
    const requiredBody = requiredBodyKeys(spec);
    if (requiredBody.length > 0) {
      delete payload[requiredBody[0]];
    }
    payload.invalid_query = true;
    return payload;
  }
  const notFound = findFailureByStatusPrefix(spec, "404");
  if (notFound && errorCode === notFound.error_code) {
    const pathParams = asRecord(payload.path_params);
    const key = primaryPathParam(spec);
    if (key) {
      pathParams[key] = `missing_${snakeCase(key)}`;
      payload.path_params = pathParams;
    } else {
      payload.force_error_code = errorCode;
    }
    return payload;
  }
  if (errorCode === "invalid_state_transition") {
    payload.next_state = "invalid";
    return payload;
  }
  payload.force_error_code = errorCode;
  return payload;
}

export async function invokeGeneratedOperation(operationId: string, payload: unknown): Promise<unknown> {
  const spec = OPERATION_SPECS[operationId];
  if (!spec) {
    throw new Error(`Unknown operation: ${operationId}`);
  }
  const normalized = asRecord(payload);
  const responseData = asRecord(spec.responseExample).data;
  if (operationId.startsWith("Create") || operationId.startsWith("Launch") || operationId.startsWith("Export")) {
    return handleCreateLike(spec, normalized);
  }
  if (operationId.startsWith("Get") && spec.pathParams.length > 0) {
    return handleDetailRead(spec, normalized);
  }
  if ((spec.method === "GET" && Array.isArray(responseData)) || operationId.startsWith("List")) {
    return handleListRead(spec, normalized);
  }
  return handleCommand(spec, normalized);
}
"""
    return (
        template.replace(
            "__OPERATION_SPECS__",
            json.dumps(operation_specs, ensure_ascii=False, indent=2, sort_keys=True),
        )
        .replace("__DEFAULT_TENANT_ID__", default_tenant_id)
    )


def render_generated_runtime_facade() -> str:
    return "\n".join(
        [
            'import {',
            "  buildFailurePayload,",
            "  buildOperationPayload,",
            "  countGeneratedRecords,",
            "  getAuditRecords,",
            "  getGeneratedRecord,",
            "  invokeGeneratedOperation as invokeOperationSupport,",
            "  listGeneratedRecords,",
            "  normalizeIdValue,",
            "  persistenceProbeHints,",
            "  recordGeneratedAuditEvent,",
            "  resetGeneratedRuntime as resetSupportRuntime,",
            "  seedGeneratedRuntimePersistence as seedSupportPersistence,",
            '} from "./operation-support.js";',
            "",
            "/**",
            " * Compatibility facade kept for existing tests and bootstrap tooling.",
            " *",
            " * Real repository execution should import explicit helpers from",
            " * `operation-support.ts` instead of routing every call through this facade.",
            " */",
            "",
            "export {",
            "  buildFailurePayload,",
            "  buildOperationPayload,",
            "  countGeneratedRecords,",
            "  getAuditRecords,",
            "  getGeneratedRecord,",
            "  listGeneratedRecords,",
            "  normalizeIdValue,",
            "  persistenceProbeHints,",
            "  recordGeneratedAuditEvent,",
            "  seedSupportPersistence as seedGeneratedRuntimePersistence,",
            "};",
            "",
            "export function resetGeneratedRuntime(): void {",
            "  resetSupportRuntime();",
            "}",
            "",
            "export async function invokeGeneratedOperation(operationId: string, payload: unknown): Promise<unknown> {",
            "  return invokeOperationSupport(operationId, payload);",
            "}",
            "",
        ]
    )


def render_runtime_test_kit(
    *,
    operations_by_tag: dict[str, list[dict[str, str]]],
) -> str:
    import_lines = [
        'import { ApiError } from "../../apps/api/src/common/errors";',
        'import {',
        "  buildFailurePayload,",
        "  buildOperationPayload,",
        "  countGeneratedRecords,",
        "  getGeneratedRecord,",
        "  getAuditRecords,",
        "  invokeGeneratedOperation,",
        "  listGeneratedRecords,",
        "  resetGeneratedRuntime as resetGeneratedRuntimeSupport,",
        '} from "../../apps/api/src/common/generated-runtime";',
    ]
    handler_lines = [
        "const operationHandlers: Record<string, (payload: unknown) => Promise<unknown>> = {",
    ]
    for module_slug, grouped_operations in operations_by_tag.items():
        controller_class = f"{camel_case(module_slug)}Controller"
        import_lines.append(
            f'import {{ {controller_class} }} from "../../apps/api/src/modules/{module_slug}/{module_slug}.controller";'
        )
        for operation in grouped_operations:
            operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
            method_name = lower_camel(operation_id)
            handler_lines.append(
                f'  "{operation_id}": (payload) => new {controller_class}().{method_name}(payload),'
            )
    handler_lines.extend(["};", ""])
    body = [
        "",
        *handler_lines,
        "type RuntimeContext = Record<string, unknown>;",
        "",
        "function deepClone<T>(value: T): T {",
        "  if (value === undefined) {",
        "    return value;",
        "  }",
        "  return JSON.parse(JSON.stringify(value)) as T;",
        "}",
        "",
        "function isRecord(value: unknown): value is Record<string, unknown> {",
        "  return typeof value === \"object\" && value !== null && !Array.isArray(value);",
        "}",
        "",
        "function snakeCase(value: string): string {",
        "  return value.replace(/([a-z0-9])([A-Z])/g, \"$1_$2\").toLowerCase();",
        "}",
        "",
        "function isTrackedContextField(key: string): boolean {",
        "  return key.endsWith(\"_id\") || key.endsWith(\"Id\") || key === \"state\" || key === \"status\" || key === \"row_version\" || key === \"version\" || key.endsWith(\"_version\") || key.endsWith(\"Version\") || key === \"uncertainty_level\" || key === \"uncertaintyLevel\";",
        "}",
        "",
        "function stripIdSuffix(value: string): string {",
        "  if (value.endsWith(\"_id\")) {",
        "    return value.slice(0, -3);",
        "  }",
        "  if (value.endsWith(\"Id\")) {",
        "    return value.slice(0, -2);",
        "  }",
        "  return value;",
        "}",
        "",
        "function tokenParts(value: string): string[] {",
        "  return value.split(\"_\").filter(Boolean);",
        "}",
        "",
        "function scoreContextKey(requestedKey: string, candidateKey: string): number {",
        "  if (candidateKey === requestedKey) {",
        "    return 100;",
        "  }",
        "  const requestedCore = stripIdSuffix(requestedKey);",
        "  const candidateCore = stripIdSuffix(candidateKey);",
        "  if (candidateCore === requestedCore) {",
        "    return 90;",
        "  }",
        "  if (candidateCore.endsWith(requestedCore) || requestedCore.endsWith(candidateCore)) {",
        "    return 80;",
        "  }",
        "  const requestedTokens = tokenParts(requestedCore);",
        "  const candidateTokens = tokenParts(candidateCore);",
        "  const overlap = requestedTokens.filter((token) => candidateTokens.includes(token)).length;",
        "  return overlap > 0 ? overlap * 10 : -1;",
        "}",
        "",
        "function resolveContextKey(key: string, context: RuntimeContext): string {",
        "  const requested = snakeCase(key);",
        "  let bestKey = \"\";",
        "  let bestScore = -1;",
        "  for (const candidate of Object.keys(context)) {",
        "    const score = scoreContextKey(requested, snakeCase(candidate));",
        "    if (score > bestScore) {",
        "      bestKey = candidate;",
        "      bestScore = score;",
        "    }",
        "  }",
        "  return bestKey;",
        "}",
        "",
        "function hasMeaningfulValue(value: unknown): boolean {",
        "  if (value === undefined || value === null) {",
        "    return false;",
        "  }",
        "  if (typeof value === \"string\") {",
        "    return value.trim().length > 0;",
        "  }",
        "  return true;",
        "}",
        "",
        "function shouldPreserveExplicitField(key: string, value: unknown): boolean {",
        "  const normalized = snakeCase(key);",
        "  return hasMeaningfulValue(value) && (normalized === \"status\" || normalized === \"state\" || normalized.endsWith(\"_id\") || normalized === \"version\" || normalized === \"expected_version\");",
        "}",
        "",
        "function withPersistenceDisabled<T>(run: () => T): T {",
        "  const databaseUrl = process.env.DATABASE_URL;",
        "  const postgresHostPort = process.env.POSTGRES_HOST_PORT;",
        "  delete process.env.DATABASE_URL;",
        "  delete process.env.POSTGRES_HOST_PORT;",
        "  try {",
        "    return run();",
        "  } finally {",
        "    if (databaseUrl === undefined) {",
        "      delete process.env.DATABASE_URL;",
        "    } else {",
        "      process.env.DATABASE_URL = databaseUrl;",
        "    }",
        "    if (postgresHostPort === undefined) {",
        "      delete process.env.POSTGRES_HOST_PORT;",
        "    } else {",
        "      process.env.POSTGRES_HOST_PORT = postgresHostPort;",
        "    }",
        "  }",
        "}",
        "",
        "async function withPersistenceDisabledAsync<T>(run: () => Promise<T>): Promise<T> {",
        "  const databaseUrl = process.env.DATABASE_URL;",
        "  const postgresHostPort = process.env.POSTGRES_HOST_PORT;",
        "  delete process.env.DATABASE_URL;",
        "  delete process.env.POSTGRES_HOST_PORT;",
        "  try {",
        "    return await run();",
        "  } finally {",
        "    if (databaseUrl === undefined) {",
        "      delete process.env.DATABASE_URL;",
        "    } else {",
        "      process.env.DATABASE_URL = databaseUrl;",
        "    }",
        "    if (postgresHostPort === undefined) {",
        "      delete process.env.POSTGRES_HOST_PORT;",
        "    } else {",
        "      process.env.POSTGRES_HOST_PORT = postgresHostPort;",
        "    }",
        "  }",
        "}",
        "",
        "export {",
        "  buildFailurePayload,",
        "  buildOperationPayload,",
        "  countGeneratedRecords,",
        "  getAuditRecords,",
        "};",
        "",
        "export function resetGeneratedRuntime(): void {",
        "  withPersistenceDisabled(() => {",
        "    resetGeneratedRuntimeSupport();",
        "  });",
        "}",
        "",
        "",
        "export async function invokeOperation(operationId: string, payload: unknown): Promise<unknown> {",
        "  return withPersistenceDisabledAsync(async () => {",
        "    const handler = operationHandlers[operationId];",
        "    if (handler) {",
        "      return handler(payload);",
        "    }",
        "    return invokeGeneratedOperation(operationId, payload);",
        "  });",
        "}",
        "",
        "export function extractEnvelopeData<T = unknown>(result: unknown): T {",
        "  if (!isRecord(result) || !(\"data\" in result)) {",
        '    throw new Error("Expected envelope with data");',
        "  }",
        "  return result.data as T;",
        "}",
        "",
        "export function applyRuntimeContext(payload: unknown, context: RuntimeContext): Record<string, unknown> {",
        "  const next = isRecord(payload) ? deepClone(payload) : {};",
        "  for (const key of Object.keys(next)) {",
        "    if (key === \"path_params\" || key === \"auth_context\") {",
        "      continue;",
        "    }",
        "    if (!isTrackedContextField(key)) {",
        "      continue;",
        "    }",
        "    if (shouldPreserveExplicitField(key, next[key])) {",
        "      continue;",
        "    }",
        "    const match = resolveContextKey(key, context);",
        "    if (match) {",
        "      next[key] = context[match];",
        "    }",
        "  }",
        "  if (isRecord(next.path_params)) {",
        "    const pathParams = next.path_params;",
        "    for (const key of Object.keys(pathParams)) {",
        "      if (!isTrackedContextField(key)) {",
        "        continue;",
        "      }",
        "      const match = resolveContextKey(key, context);",
        "      if (match) {",
        "        pathParams[key] = context[match];",
        "      }",
        "    }",
        "    next.path_params = pathParams;",
        "  }",
        "  if (isRecord(next.auth_context)) {",
        "    const authContext = next.auth_context;",
        "    const tenantMatch = resolveContextKey(\"tenant_id\", context);",
        "    if (tenantMatch) {",
        "      authContext.tenant_id = context[tenantMatch];",
        "    }",
        "    next.auth_context = authContext;",
        "  }",
        "  return next;",
        "}",
        "",
        "export function absorbEnvelopeContext(result: unknown, context: RuntimeContext): RuntimeContext {",
        "  const data = extractEnvelopeData<unknown>(result);",
        "  const source = Array.isArray(data) ? data.find((item) => isRecord(item)) : data;",
        "  if (!isRecord(source)) {",
        "    return context;",
        "  }",
        "  for (const [key, value] of Object.entries(source)) {",
        "    if (isTrackedContextField(key)) {",
        "      context[key] = value;",
        "    }",
        "  }",
        "  return context;",
        "}",
        "",
        "export function getRecord(recordKey: string, id: string): Record<string, unknown> | undefined {",
        "  return getGeneratedRecord(recordKey, id);",
        "}",
        "",
        "export function listRecords(recordKey: string): Record<string, unknown>[] {",
        "  return listGeneratedRecords(recordKey);",
        "}",
        "",
        "export function latestAuditRecord(): Record<string, unknown> | undefined {",
        "  const records = getAuditRecords();",
        "  return records.length > 0 ? (records.at(-1) as Record<string, unknown>) : undefined;",
        "}",
        "",
        "export async function captureApiError(action: Promise<unknown>): Promise<ApiError> {",
        "  try {",
        "    await action;",
        "  } catch (error) {",
        "    if (error instanceof ApiError) {",
        "      return error;",
        "    }",
        "    throw error;",
        "  }",
        '  throw new Error("Expected ApiError");',
        "}",
        "",
    ]
    return "\n".join(import_lines + body)


def render_generated_api_router(
    *,
    operations_by_tag: dict[str, list[dict[str, str]]],
    operation_specs: dict[str, dict[str, Any]],
    compiled_bindings: list[dict[str, Any]] | None = None,
) -> str:
    import_lines = [
        'import type { IncomingMessage, ServerResponse } from "node:http";',
        'import { URL } from "node:url";',
        'import { normalizeAuthSession, parseAuthorizationHeader } from "./common/auth-session.js";',
        'import { ApiError, createApiError } from "./common/errors.js";',
        'import { recordGeneratedAuditEvent } from "./common/operation-support.js";',
    ]
    binding_index = index_compiled_bindings_by_endpoint(compiled_bindings)
    route_rows: list[str] = []
    for module_slug, grouped_operations in operations_by_tag.items():
        controller_class = f"{camel_case(module_slug)}Controller"
        import_lines.append(f'import {{ {controller_class} }} from "./modules/{module_slug}/{module_slug}.controller.js";')
        for operation in grouped_operations:
            operation_id = operation["operation_id"] or f"{operation['method']}-{operation['path']}"
            spec = runtime_spec_for_operation(operation, operation_specs)
            success_status = int(str(spec.get("successStatus", "200")).strip() or "200")
            matching_bindings = binding_index.get((str(operation["method"]).upper(), str(operation["path"]).strip()), [])
            binding_sources = [
                str(row.get("service_binding_id") or "").strip()
                for row in matching_bindings
                if str(row.get("service_binding_id") or "").strip()
            ]
            binding_modes = sorted(
                {
                    str(row.get("binding_mode") or "").strip()
                    for row in matching_bindings
                    if str(row.get("binding_mode") or "").strip()
                }
            )
            rbac_policies = binding_rbac_policies(matching_bindings)
            failure_semantics = sorted(
                {
                    str(row.get("failure_codes") or "").strip()
                    for row in matching_bindings
                    if str(row.get("failure_codes") or "").strip()
                }
            )
            route_rows.extend(
                [
                    "  {",
                    f'    operationId: "{operation_id}",',
                    f'    method: "{str(operation["method"]).upper()}",',
                    f'    pathTemplate: "{operation["path"]}",',
                    f"    successStatus: {success_status},",
                    f"    bindingSources: {json.dumps(binding_sources, ensure_ascii=False)},",
                    f"    bindingModes: {json.dumps(binding_modes, ensure_ascii=False)},",
                    f"    rbacPolicies: {json.dumps(rbac_policies, ensure_ascii=False)},",
                    f"    failureSemantics: {json.dumps(failure_semantics, ensure_ascii=False)},",
                    f"    handler: (payload) => new {controller_class}().{lower_camel(operation_id)}(payload),",
                    "  },",
                ]
            )
    return "\n".join(
        import_lines
        + [
            "",
            f'// Derived artifact authority: {"compiled-bindings" if binding_index else "missing-compiled-bindings"}',
            "type RouteDef = {",
            "  operationId: string;",
            "  method: string;",
            "  pathTemplate: string;",
            "  successStatus: number;",
            "  bindingSources: string[];",
            "  bindingModes: string[];",
            "  rbacPolicies: string[];",
            "  failureSemantics: string[];",
            "  handler: (payload: Record<string, unknown>) => Promise<unknown>;",
            "};",
            "",
            "const routeTable: RouteDef[] = [",
            *route_rows,
            "];",
            "",
            "function isRecord(value: unknown): value is Record<string, unknown> {",
            "  return typeof value === \"object\" && value !== null && !Array.isArray(value);",
            "}",
            "",
            "async function readJsonBody(request: IncomingMessage): Promise<Record<string, unknown>> {",
            "  const chunks: Buffer[] = [];",
            "  for await (const chunk of request) {",
            "    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));",
            "  }",
            "  if (chunks.length === 0) {",
            "    return {};",
            "  }",
            "  const raw = Buffer.concat(chunks).toString(\"utf-8\").trim();",
            "  if (!raw) {",
            "    return {};",
            "  }",
            "  const parsed = JSON.parse(raw) as unknown;",
            "  return isRecord(parsed) ? parsed : {};",
            "}",
            "",
            "function buildQuery(url: URL): Record<string, unknown> {",
            "  const entries = Array.from(url.searchParams.entries());",
            "  return Object.fromEntries(entries);",
            "}",
            "",
            "function matchPath(pathTemplate: string, actualPath: string): Record<string, string> | null {",
            "  const templateParts = pathTemplate.split(\"/\").filter(Boolean);",
            "  const actualParts = actualPath.split(\"/\").filter(Boolean);",
            "  if (templateParts.length !== actualParts.length) {",
            "    return null;",
            "  }",
            "  const params: Record<string, string> = {};",
            "  for (let index = 0; index < templateParts.length; index += 1) {",
            "    const templatePart = templateParts[index];",
            "    const actualPart = decodeURIComponent(actualParts[index] ?? \"\");",
            "    if (templatePart.startsWith(\"{\") && templatePart.endsWith(\"}\")) {",
            "      params[templatePart.slice(1, -1)] = actualPart;",
            "      continue;",
            "    }",
            "    if (templatePart !== actualPart) {",
            "      return null;",
            "    }",
            "  }",
            "  return params;",
            "}",
            "",
            "function allowPhase3AuthContextHeader(): boolean {",
            "  return process.env.PHASE3_ALLOW_AUTH_CONTEXT_HEADER === \"true\";",
            "}",
            "",
            "function parsePhase3AuthContextHeader(request: IncomingMessage): Record<string, unknown> {",
            "  if (!allowPhase3AuthContextHeader()) {",
            "    return {};",
            "  }",
            "  const raw = request.headers[\"x-phase3-auth-context\"];",
            "  const value = Array.isArray(raw) ? raw[0] : raw;",
            "  if (typeof value !== \"string\" || !value.trim()) {",
            "    return {};",
            "  }",
            "  try {",
            "    const parsed = JSON.parse(decodeURIComponent(value)) as unknown;",
            "    return isRecord(parsed) ? parsed : {};",
            "  } catch {",
            "    return {};",
            "  }",
            "}",
            "",
            "function parseAuthContext(request: IncomingMessage): Record<string, unknown> {",
            "  const raw = request.headers.authorization;",
            "  const authorization = Array.isArray(raw) ? raw[0] : raw;",
            "  if (typeof authorization === \"string\" && authorization.trim()) {",
            "    return parseAuthorizationHeader(authorization);",
            "  }",
            "  const fallbackContext = parsePhase3AuthContextHeader(request);",
            "  if (Object.keys(fallbackContext).length > 0) {",
            "    return fallbackContext;",
            "  }",
            "  return parseAuthorizationHeader(undefined);",
            "}",
            "",
            "function stringValue(value: unknown): string {",
            "  return typeof value === \"string\" ? value.trim() : \"\";",
            "}",
            "",
            "function uniqueNonEmpty(values: string[]): string[] {",
            "  return Array.from(new Set(values.map((value) => String(value).trim()).filter(Boolean)));",
            "}",
            "",
            "function deriveRouteTenantId(",
            "  authContext: Record<string, unknown>,",
            "  payload: Record<string, unknown>,",
            "  pathParams: Record<string, string>,",
            "): string {",
            "  const body = isRecord(payload.body) ? payload.body : {};",
            "  return stringValue(payload.tenant_id)",
            "    || stringValue(payload.tenantId)",
            "    || stringValue(body.tenant_id)",
            "    || stringValue(body.tenantId)",
            "    || stringValue(pathParams.tenant_id)",
            "    || stringValue(pathParams.tenantId)",
            "    || stringValue(authContext.tenant_id)",
            "    || stringValue(authContext.tenantId);",
            "}",
            "",
            "function applyRouteTenantContext(",
            "  payload: Record<string, unknown>,",
            "  pathParams: Record<string, string>,",
            "  authContext: Record<string, unknown>,",
            "  tenantId: string,",
            "): void {",
            "  if (!tenantId) {",
            "    return;",
            "  }",
            "  if (payload.tenant_id === undefined && payload.tenantId === undefined) {",
            "    payload.tenant_id = tenantId;",
            "  }",
            "  const body = isRecord(payload.body) ? payload.body : undefined;",
            "  if (body && body.tenant_id === undefined && body.tenantId === undefined) {",
            "    body.tenant_id = tenantId;",
            "  }",
            "  if (",
            "    (Object.prototype.hasOwnProperty.call(pathParams, \"tenant_id\") || Object.prototype.hasOwnProperty.call(pathParams, \"tenantId\"))",
            "    && pathParams.tenant_id === undefined",
            "    && pathParams.tenantId === undefined",
            "  ) {",
            "    pathParams.tenant_id = tenantId;",
            "  }",
            "  if (authContext.tenant_id === undefined && authContext.tenantId === undefined) {",
            "    authContext.tenant_id = tenantId;",
            "  }",
            "}",
            "",
            "function enforceRouteRbacPolicies(",
            "  route: RouteDef,",
            "  authContext: Record<string, unknown>,",
            "  payload: Record<string, unknown>,",
            "  pathParams: Record<string, string>,",
            "): string {",
            "  const tenantId = deriveRouteTenantId(authContext, payload, pathParams);",
            "  const requiredRoles = uniqueNonEmpty(route.rbacPolicies || []);",
            "  const effectiveRoles = requiredRoles.length > 0 ? requiredRoles : [\"authenticated\"];",
            "  const session = normalizeAuthSession(authContext, tenantId || \"11111111-1111-1111-1111-111111111111\");",
            "  if (!effectiveRoles.some((role) => session.roles.includes(role))) {",
            "    throw createApiError(403, \"business_error\", \"rbac_forbidden\", \"never\", `Missing one of roles: ${effectiveRoles.join(\", \")}`);",
            "  }",
            "  return stringValue(session.tenant_id) || tenantId;",
            "}",
            "",
            "function auditRouteDenial(",
            "  route: RouteDef,",
            "  error: ApiError,",
            "  authContext: Record<string, unknown>,",
            "  payload: Record<string, unknown>,",
            "  pathParams: Record<string, string>,",
            "): void {",
            "  recordGeneratedAuditEvent({",
            "    tenantId: deriveRouteTenantId(authContext, payload, pathParams) || stringValue(authContext.tenant_id) || stringValue(authContext.tenantId),",
            "    operationId: route.operationId,",
            "    actionType: route.operationId,",
            "    outcome: \"denied\",",
            "    reason: error.envelope.error_code,",
            "    subjectId: stringValue(authContext.subject_id) || stringValue(authContext.sub),",
            "    requestId: stringValue(payload.request_id) || stringValue(payload.requestId),",
            "  });",
            "}",
            "",
            "function failureCodeFromHeader(request: IncomingMessage): string {",
            "  const raw = request.headers[\"x-phase3-force-error-code\"];",
            "  const value = Array.isArray(raw) ? raw[0] : raw;",
            "  return typeof value === \"string\" ? value : \"\";",
            "}",
            "",
            "export async function handleGeneratedApiRequest(",
            "  request: IncomingMessage,",
            "  response: ServerResponse,",
            "  helpers: { sendJson: (response: ServerResponse, statusCode: number, payload: Record<string, unknown>) => void },",
            "): Promise<boolean> {",
            "  const method = request.method || \"GET\";",
            "  const url = new URL(request.url || \"/\", `http://${request.headers.host || \"localhost\"}`);",
            "  for (const route of routeTable) {",
            "    if (route.method !== method) {",
            "      continue;",
            "    }",
            "    const pathParams = matchPath(route.pathTemplate, url.pathname);",
            "    if (!pathParams) {",
            "      continue;",
            "    }",
            "    let authContext: Record<string, unknown> = {};",
            "    let payload: Record<string, unknown> = {};",
            "    try {",
            "      const body = await readJsonBody(request);",
            "      const query = buildQuery(url);",
            "      authContext = parseAuthContext(request);",
            "      const forceErrorCode = failureCodeFromHeader(request);",
            "      payload = {",
            "        ...query,",
            "        ...body,",
            "        body,",
            "        query,",
            "        path_params: pathParams,",
            "        pathParams: pathParams,",
            "        auth_context: authContext,",
            "        authContext: authContext,",
            "      };",
            "      const tenantId = enforceRouteRbacPolicies(route, authContext, payload, pathParams);",
            "      applyRouteTenantContext(payload, pathParams, authContext, tenantId);",
            "      if (forceErrorCode) {",
            "        payload.force_error_code = forceErrorCode;",
            "      }",
            "      const result = await route.handler(payload);",
            "      helpers.sendJson(response, route.successStatus, isRecord(result) ? result : { data: result });",
            "    } catch (error) {",
            "      if (error instanceof ApiError) {",
            "        auditRouteDenial(route, error, authContext, payload, pathParams);",
            "        helpers.sendJson(response, error.status, error.envelope as unknown as Record<string, unknown>);",
            "      } else {",
            "        helpers.sendJson(response, 500, {",
            '          error_kind: "system_error",',
            '          error_code: "generated_route_handler_failed",',
            "          message: error instanceof Error ? error.message : String(error),",
            "        });",
            "      }",
            "    }",
            "    return true;",
            "  }",
            "  return false;",
            "}",
            "",
        ]
    )


def render_backend_runtime_harness() -> str:
    return "\n".join(
        [
            'import { readdir, readFile } from "node:fs/promises";',
            'import type { Server } from "node:http";',
            'import type { AddressInfo } from "node:net";',
            'import { join } from "node:path";',
            'import { fileURLToPath } from "node:url";',
            'import { Client } from "pg";',
            'import { issueAuthToken } from "../../apps/api/src/common/auth-session";',
            'import { createApiServer } from "../../apps/api/src/main";',
            'import { runMigrations } from "../../apps/api/src/runtime/database";',
            'import { getOperationSpec } from "../../apps/api/src/common/operation-support";',
            'import {',
            '  buildFailurePayload as buildFailurePayloadSupport,',
            '  buildOperationPayload as buildOperationPayloadSupport,',
            '  getAuditRecords as getAuditRecordsSupport,',
            '  normalizeIdValue as normalizeRuntimeIdentifierValue,',
            '  persistenceProbeHints as persistenceProbeHintsSupport,',
            '  resetGeneratedRuntime,',
            '  seedGeneratedRuntimePersistence,',
            '} from "../../apps/api/src/common/generated-runtime";',
            "",
            "export { normalizeRuntimeIdentifierValue };",
            "",
            "type TransactionQuery = <T extends Record<string, unknown> = Record<string, unknown>>(sql: string, params?: unknown[]) => Promise<T[]>;",
            "",
            "export interface BackendRuntime {",
            "  baseUrl: string;",
            "  close(): Promise<void>;",
            "  initializeDatabase(): Promise<void>;",
            "  restoreScenario(): Promise<void>;",
            "  resetDatabase(): Promise<void>;",
            "  getResetEvents(): RuntimeHarnessResetEvent[];",
            "  getAuditRecords(): Record<string, unknown>[];",
            "  query<T extends Record<string, unknown> = Record<string, unknown>>(sql: string, params?: unknown[]): Promise<T[]>;",
            "  withTransaction<T>(run: (query: TransactionQuery) => Promise<T>): Promise<T>;",
            "}",
            "",
            "interface RuntimeHarnessResetEvent {",
            "  stage: string;",
            "  status: 'started' | 'passed' | 'failed';",
            "  at: string;",
            "  message?: string;",
            "}",
            "",
            "export interface PersistenceRoundTripEvidence {",
            "  tableName: string;",
            "  idField: string;",
            "  idValue: string;",
            "  matchedRows: number;",
            "  checkedFieldNames: string[];",
            "  checkedValueFieldNames: string[];",
            "  mismatchedFieldNames: string[];",
            "  persistedRow: Record<string, unknown>;",
            "}",
            "",
            "export class HttpApiError extends Error {",
            "  readonly status: number;",
            "  readonly envelope: Record<string, unknown>;",
            "",
            "  constructor(status: number, envelope: Record<string, unknown>) {",
            "    super(`${status} ${String(envelope.error_code ?? \"http_error\")}`);",
            "    this.name = \"HttpApiError\";",
            "    this.status = status;",
            "    this.envelope = envelope;",
            "  }",
            "}",
            "",
            "function isRecord(value: unknown): value is Record<string, unknown> {",
            "  return typeof value === \"object\" && value !== null && !Array.isArray(value);",
            "}",
            "",
            "function deepClone<T>(value: T): T {",
            "  if (value === undefined) {",
            "    return value;",
            "  }",
            "  return JSON.parse(JSON.stringify(value)) as T;",
            "}",
            "",
            "function baseDatabaseUrl(): string {",
            "  const hostPort = process.env.POSTGRES_HOST_PORT || '55432';",
            "  const connectionString = process.env.PHASE3_BASE_DATABASE_URL || process.env.DATABASE_URL || `postgresql://postgres:postgres@127.0.0.1:${hostPort}/app`;",
            "  process.env.PHASE3_BASE_DATABASE_URL = connectionString;",
            "  return connectionString;",
            "}",
            "",
            "function sanitizeDatabaseName(value: string): string {",
            "  return value.replace(/[^a-zA-Z0-9_]+/g, '_').replace(/^_+|_+$/g, '') || 'app';",
            "}",
            "",
            "function quoteIdentifier(value: string): string {",
            "  return `\"${value.replace(/\"/g, '\"\"')}\"`;",
            "}",
            "",
            "function resolveWorkerDatabaseUrl(baseConnectionString: string): string {",
            "  if (process.env.PHASE3_DISABLE_WORKER_DATABASE_ISOLATION === '1') {",
            "    return baseConnectionString;",
            "  }",
            "  const url = new URL(baseConnectionString);",
            "  const baseName = sanitizeDatabaseName(decodeURIComponent(url.pathname.replace(/^\\//, '')) || 'app');",
            "  const workerId = sanitizeDatabaseName(process.env.VITEST_WORKER_ID || process.env.VITEST_POOL_ID || String(process.pid));",
            "  url.pathname = `/${baseName}_w${workerId}`;",
            "  return url.toString();",
            "}",
            "",
            "function ensureDatabaseUrl(): string {",
            "  const connectionString = resolveWorkerDatabaseUrl(baseDatabaseUrl());",
            "  process.env.DATABASE_URL = connectionString;",
            "  return connectionString;",
            "}",
            "",
            "function ensureAuthTokenSecret(): string {",
            "  const secret = process.env.AUTH_TOKEN_SECRET || 'phase3-local-dev-secret';",
            "  process.env.AUTH_TOKEN_SECRET = secret;",
            "  return secret;",
            "}",
            "",
            "function databaseConnectionTimeoutMillis(): number {",
            "  return Number.parseInt(process.env.PHASE3_DB_CONNECT_TIMEOUT_MS || '3000', 10);",
            "}",
            "",
            "function databaseStatementTimeoutMillis(): number {",
            "  return Number.parseInt(process.env.PHASE3_DB_STATEMENT_TIMEOUT_MS || '5000', 10);",
            "}",
            "",
            "let databaseResetQueue: Promise<void> = Promise.resolve();",
            "let migrationDocumentCache: Promise<string[]> | null = null;",
            "let workerDatabaseReady: Promise<void> | null = null;",
            "let sharedBackendRuntime: BackendRuntime | null = null;",
            "let databaseRebuilt = false;",
            "const runtimeHarnessResetEvents: RuntimeHarnessResetEvent[] = [];",
            "",
            "function recordRuntimeHarnessResetEvent(stage: string, status: RuntimeHarnessResetEvent['status'], message?: string): void {",
            "  runtimeHarnessResetEvents.push({ stage, status, at: new Date().toISOString(), message });",
            "}",
            "",
            "async function loadMigrationDocuments(): Promise<string[]> {",
            "  if (!migrationDocumentCache) {",
            "    const supportDir = fileURLToPath(new URL('.', import.meta.url));",
            "    const migrationsDir = join(supportDir, '../../db/migrations');",
            "    migrationDocumentCache = (async () => {",
            "      const entries = (await readdir(migrationsDir)).filter((entry) => entry.endsWith('.sql')).sort();",
            "      return Promise.all(entries.map((entry) => readFile(join(migrationsDir, entry), 'utf-8')));",
            "    })();",
            "  }",
            "  return migrationDocumentCache;",
            "}",
            "",
            "async function prepareClientSchema(client: Client): Promise<void> {",
            "  await client.query('CREATE SCHEMA IF NOT EXISTS public');",
            "  await client.query('SET search_path TO public');",
            "}",
            "",
            "async function withClient<T>(run: (client: Client) => Promise<T>): Promise<T> {",
            "  const client = new Client({",
            "    connectionString: ensureDatabaseUrl(),",
            "    connectionTimeoutMillis: databaseConnectionTimeoutMillis(),",
            "    statement_timeout: databaseStatementTimeoutMillis(),",
            "    query_timeout: databaseStatementTimeoutMillis(),",
            "  });",
            "  await client.connect();",
            "  try {",
            "    await prepareClientSchema(client);",
            "    return await run(client);",
            "  } finally {",
            "    await client.end();",
            "  }",
            "}",
            "",
            "async function ensureWorkerDatabaseExists(connectionString: string): Promise<void> {",
            "  if (process.env.PHASE3_DISABLE_WORKER_DATABASE_ISOLATION === '1') {",
            "    return;",
            "  }",
            "  const targetUrl = new URL(connectionString);",
            "  const targetDatabaseName = sanitizeDatabaseName(decodeURIComponent(targetUrl.pathname.replace(/^\\//, '')) || 'app');",
            "  const maintenanceUrl = new URL(baseDatabaseUrl());",
            "  maintenanceUrl.pathname = '/postgres';",
            "  const client = new Client({",
            "    connectionString: maintenanceUrl.toString(),",
            "    connectionTimeoutMillis: databaseConnectionTimeoutMillis(),",
            "    statement_timeout: databaseStatementTimeoutMillis(),",
            "    query_timeout: databaseStatementTimeoutMillis(),",
            "  });",
            "  await client.connect();",
            "  try {",
            "    const existing = await client.query<{ exists: boolean }>('SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = $1) AS exists', [targetDatabaseName]);",
            "    if (!existing.rows[0]?.exists) {",
            "      await client.query(`CREATE DATABASE ${quoteIdentifier(targetDatabaseName)}`);",
            "    }",
            "  } finally {",
            "    await client.end();",
            "  }",
            "}",
            "",
            "async function ensureWorkerDatabaseReady(): Promise<void> {",
            "  const connectionString = ensureDatabaseUrl();",
            "  if (!workerDatabaseReady) {",
            "    workerDatabaseReady = ensureWorkerDatabaseExists(connectionString);",
            "  }",
            "  await workerDatabaseReady;",
            "}",
            "",
            "async function terminateOtherDatabaseConnections(client: Client): Promise<void> {",
            "  await client.query(",
            "    `SELECT pg_terminate_backend(pid)",
            "       FROM pg_stat_activity",
            "      WHERE datname = current_database()",
            "        AND pid <> pg_backend_pid()`,",
            "  );",
            "}",
            "",
            "async function resetPublicSchema(): Promise<void> {",
            "  await withClient(async (client) => {",
            "    await terminateOtherDatabaseConnections(client);",
            "    await client.query('DROP SCHEMA IF EXISTS public CASCADE');",
            "    await client.query('CREATE SCHEMA public');",
            "    await client.query('GRANT ALL ON SCHEMA public TO postgres');",
            "    await client.query('GRANT ALL ON SCHEMA public TO public');",
            "    await client.query('SET search_path TO public');",
            "  });",
            "}",
            "",
            "async function runSerializedDatabaseReset(task: () => Promise<void>): Promise<void> {",
            "  const pending = databaseResetQueue.then(task);",
            "  databaseResetQueue = pending.catch(() => undefined);",
            "  return pending;",
            "}",
            "",
            "async function truncatePublicTables(): Promise<void> {",
            "  await withClient(async (client) => {",
            "    const result = await client.query<{ tablename: string }>(`SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename`);",
            "    const tableNames = result.rows.map((row) => row.tablename).filter(Boolean);",
            "    if (tableNames.length === 0) {",
            "      return;",
            "    }",
            "    const quoted = tableNames.map((name) => `public.${JSON.stringify(name)}`).join(', ');",
            "    await client.query(`TRUNCATE ${quoted} RESTART IDENTITY CASCADE`);",
            "  });",
            "}",
            "",
            "async function rebuildDatabaseState(): Promise<void> {",
            "  recordRuntimeHarnessResetEvent('rebuild:reset-runtime', 'started');",
            "  resetGeneratedRuntime();",
            "  recordRuntimeHarnessResetEvent('rebuild:reset-runtime', 'passed');",
            "  recordRuntimeHarnessResetEvent('rebuild:schema', 'started');",
            "  await resetPublicSchema();",
            "  recordRuntimeHarnessResetEvent('rebuild:schema', 'passed');",
            "  recordRuntimeHarnessResetEvent('rebuild:migrate', 'started');",
            "  await runMigrations(await loadMigrationDocuments());",
            "  recordRuntimeHarnessResetEvent('rebuild:migrate', 'passed');",
            "  recordRuntimeHarnessResetEvent('rebuild:seed', 'started');",
            "  await seedGeneratedRuntimePersistence();",
            "  recordRuntimeHarnessResetEvent('rebuild:seed', 'passed');",
            "}",
            "",
            "async function restoreDatabaseState(): Promise<void> {",
            "  recordRuntimeHarnessResetEvent('restore:reset-runtime', 'started');",
            "  resetGeneratedRuntime();",
            "  recordRuntimeHarnessResetEvent('restore:reset-runtime', 'passed');",
            "  recordRuntimeHarnessResetEvent('restore:truncate', 'started');",
            "  await truncatePublicTables();",
            "  recordRuntimeHarnessResetEvent('restore:truncate', 'passed');",
            "  recordRuntimeHarnessResetEvent('restore:seed', 'started');",
            "  await seedGeneratedRuntimePersistence();",
            "  recordRuntimeHarnessResetEvent('restore:seed', 'passed');",
            "}",
            "",
            "function snakeCase(value: string): string {",
            "  return value.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase();",
            "}",
            "",
            "function camelCase(value: string): string {",
            "  return snakeCase(value).replace(/_([a-z0-9])/g, (_, token: string) => token.toUpperCase());",
            "}",
            "",
            "function stringValue(value: unknown): string {",
            "  if (typeof value === 'string') {",
            "    return value;",
            "  }",
            "  if (typeof value === 'number' || typeof value === 'boolean') {",
            "    return String(value);",
            "  }",
            "  return '';",
            "}",
            "",
            "function uniqueStrings(values: string[]): string[] {",
            "  return Array.from(new Set(values.filter((value) => value.trim().length > 0)));",
            "}",
            "",
            "function stripIdSuffix(value: string): string {",
            "  if (value.endsWith('_id')) {",
            "    return value.slice(0, -3);",
            "  }",
            "  if (value.endsWith('Id')) {",
            "    return value.slice(0, -2);",
            "  }",
            "  return value;",
            "}",
            "",
            "function tokenParts(value: string): string[] {",
            "  return value.split('_').filter(Boolean);",
            "}",
            "",
            "function scoreContextKey(requestedKey: string, candidateKey: string): number {",
            "  if (candidateKey === requestedKey) {",
            "    return 100;",
            "  }",
            "  const requestedCore = stripIdSuffix(requestedKey);",
            "  const candidateCore = stripIdSuffix(candidateKey);",
            "  if (candidateCore === requestedCore) {",
            "    return 90;",
            "  }",
            "  if (candidateCore.endsWith(requestedCore) || requestedCore.endsWith(candidateCore)) {",
            "    return 80;",
            "  }",
            "  const requestedTokens = tokenParts(requestedCore);",
            "  const candidateTokens = tokenParts(candidateCore);",
            "  const overlap = requestedTokens.filter((token) => candidateTokens.includes(token)).length;",
            "  return overlap > 0 ? overlap * 10 : -1;",
            "}",
            "",
            "function resolveContextKey(key: string, context: Record<string, unknown>): string {",
            "  const requested = snakeCase(key);",
            "  let bestKey = '';",
            "  let bestScore = -1;",
            "  for (const candidate of Object.keys(context)) {",
            "    const score = scoreContextKey(requested, snakeCase(candidate));",
            "    if (score > bestScore) {",
            "      bestKey = candidate;",
            "      bestScore = score;",
            "    }",
            "  }",
            "  return bestKey;",
            "}",
            "",
            "function trackedContextField(key: string): boolean {",
            "  return key.endsWith('_id') || key.endsWith('Id') || key === 'status' || key === 'state' || key.includes('version') || key.toLowerCase().includes('uncertainty');",
            "}",
            "",
            "function hasMeaningfulValue(value: unknown): boolean {",
            "  if (value === undefined || value === null) {",
            "    return false;",
            "  }",
            "  if (typeof value === 'string') {",
            "    return value.trim().length > 0;",
            "  }",
            "  return true;",
            "}",
            "",
            "function shouldPreserveExplicitField(key: string, value: unknown): boolean {",
            "  const normalized = snakeCase(key);",
            "  return hasMeaningfulValue(value) && (normalized === 'status' || normalized === 'state' || normalized.endsWith('_id') || normalized === 'version' || normalized === 'expected_version');",
            "}",
            "",
            "function applyPayloadToHttpRequest(spec: Record<string, unknown>, payload: Record<string, unknown>, runtime: BackendRuntime): { url: string; init: globalThis.RequestInit } {",
            "  const pathTemplate = String(spec.path ?? '/');",
            "  const method = String(spec.method ?? 'GET').toUpperCase();",
            "  const pathParams = isRecord(payload.path_params) ? payload.path_params : {};",
            "  let resolvedPath = pathTemplate;",
            "  for (const [key, value] of Object.entries(pathParams)) {",
            "    resolvedPath = resolvedPath.replace(`{${key}}`, encodeURIComponent(String(value)));",
            "  }",
            "  const url = new URL(resolvedPath, runtime.baseUrl);",
            "  const requestBody = isRecord(payload.body) ? deepClone(payload.body) : {};",
            "  for (const [key, value] of Object.entries(payload)) {",
            "    if ([\"body\", \"query\", \"path_params\", \"pathParams\", \"auth_context\", \"authContext\"].includes(key)) {",
            "      continue;",
            "    }",
            "    requestBody[key] = value;",
            "  }",
            "  const headers: Record<string, string> = {};",
            "  const authContext = isRecord(payload.auth_context) ? payload.auth_context : {};",
            "  if (Object.keys(authContext).length > 0) {",
            "    headers.authorization = `Bearer ${issueAuthToken(authContext)}`;",
            "  }",
            "  if (typeof payload.force_error_code === 'string' && payload.force_error_code) {",
            "    headers['x-phase3-force-error-code'] = String(payload.force_error_code);",
            "  }",
            "  if (method === 'GET' || method === 'HEAD') {",
            "    for (const [key, value] of Object.entries(requestBody)) {",
            "      if (value !== undefined && value !== null && value !== '') {",
            "        url.searchParams.set(key, String(value));",
            "      }",
            "    }",
            "    return { url: url.toString(), init: { method, headers } };",
            "  }",
            "  headers['content-type'] = 'application/json';",
            "  return {",
            "    url: url.toString(),",
            "    init: { method, headers, body: JSON.stringify(requestBody) },",
            "  };",
            "}",
            "",
            "function withAuthorizationHeader(request: { url: string; init: globalThis.RequestInit }, authorization: string): { url: string; init: globalThis.RequestInit } {",
            "  return {",
            "    url: request.url,",
            "    init: {",
            "      ...request.init,",
            "      headers: {",
            "        ...((request.init.headers ?? {}) as Record<string, string>),",
            "        authorization,",
            "      },",
            "    },",
            "  };",
            "}",
            "",
            "export async function startBackendRuntime(): Promise<BackendRuntime> {",
            "  if (sharedBackendRuntime) {",
            "    return sharedBackendRuntime;",
            "  }",
            "  ensureDatabaseUrl();",
            "  await ensureWorkerDatabaseReady();",
            "  ensureAuthTokenSecret();",
            "  const host = '127.0.0.1';",
            "  const server = await createApiServer();",
            "  await new Promise<void>((resolve) => {",
            "    server.listen(0, host, () => resolve());",
            "  });",
            "  (server as Server).unref();",
            "  const address = server.address() as AddressInfo;",
            "  const runtime: BackendRuntime = {",
            "    baseUrl: `http://${host}:${address.port}`,",
            "    async close(): Promise<void> {",
            "      return;",
            "    },",
            "    async initializeDatabase(): Promise<void> {",
            "      await runSerializedDatabaseReset(async () => {",
            "        if (!databaseRebuilt) {",
            "          await rebuildDatabaseState();",
            "          databaseRebuilt = true;",
            "          return;",
            "        }",
            "        await restoreDatabaseState();",
            "      });",
            "    },",
            "    async restoreScenario(): Promise<void> {",
            "      await runSerializedDatabaseReset(async () => {",
            "        await restoreDatabaseState();",
            "      });",
            "    },",
            "    async resetDatabase(): Promise<void> {",
            "      await runSerializedDatabaseReset(async () => {",
            "        await rebuildDatabaseState();",
            "        databaseRebuilt = true;",
            "      });",
            "    },",
            "    getResetEvents(): RuntimeHarnessResetEvent[] {",
            "      return runtimeHarnessResetEvents.map((event) => ({ ...event }));",
            "    },",
            "    getAuditRecords(): Record<string, unknown>[] {",
            "      return getAuditRecordsSupport();",
            "    },",
            "    async query<T extends Record<string, unknown> = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {",
            "      return withClient(async (client) => {",
            "        const result = await client.query(sql, params);",
            "        return result.rows as T[];",
            "      });",
            "    },",
            "    async withTransaction<T>(run: (query: TransactionQuery) => Promise<T>): Promise<T> {",
            "      return withClient(async (client) => {",
            "        await client.query('BEGIN');",
            "        const query: TransactionQuery = async <R extends Record<string, unknown> = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<R[]> => {",
            "          const result = await client.query(sql, params);",
            "          return result.rows as R[];",
            "        };",
            "        try {",
            "          const result = await run(query);",
            "          await client.query('COMMIT');",
            "          return result;",
            "        } catch (error) {",
            "          await client.query('ROLLBACK');",
            "          throw error;",
            "        }",
            "      });",
            "    },",
            "  };",
            "  sharedBackendRuntime = runtime;",
            "  return runtime;",
            "}",
            "",
            "export function buildOperationPayload(operationId: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {",
            "  return buildOperationPayloadSupport(operationId, overrides);",
            "}",
            "",
            "export function buildFailurePayload(operationId: string, errorCode: string): Record<string, unknown> {",
            "  return buildFailurePayloadSupport(operationId, errorCode);",
            "}",
            "",
            "export async function invokeHttpOperation(runtime: BackendRuntime, operationId: string, payload: Record<string, unknown>): Promise<unknown> {",
            "  const spec = getOperationSpec(operationId) as unknown as Record<string, unknown>;",
            "  const request = applyPayloadToHttpRequest(spec, payload, runtime);",
            "  const response = await fetch(request.url, request.init);",
            "  const text = await response.text();",
            "  const parsed = text ? (JSON.parse(text) as unknown) : {};",
            "  if (!response.ok) {",
            "    throw new HttpApiError(response.status, isRecord(parsed) ? parsed : { error_code: 'http_error' });",
            "  }",
            "  return parsed;",
            "}",
            "",
            "export async function invokeHttpOperationWithAuthHeader(",
            "  runtime: BackendRuntime,",
            "  operationId: string,",
            "  payload: Record<string, unknown>,",
            "  authorization: string,",
            "): Promise<unknown> {",
            "  const spec = getOperationSpec(operationId) as unknown as Record<string, unknown>;",
            "  const request = withAuthorizationHeader(applyPayloadToHttpRequest(spec, payload, runtime), authorization);",
            "  const response = await fetch(request.url, request.init);",
            "  const text = await response.text();",
            "  const parsed = text ? (JSON.parse(text) as unknown) : {};",
            "  if (!response.ok) {",
            "    throw new HttpApiError(response.status, isRecord(parsed) ? parsed : { error_code: 'http_error' });",
            "  }",
            "  return parsed;",
            "}",
            "",
            "export async function captureApiError(action: Promise<unknown>): Promise<HttpApiError> {",
            "  try {",
            "    await action;",
            "  } catch (error) {",
            "    if (error instanceof HttpApiError) {",
            "      return error;",
            "    }",
            "    throw error;",
            "  }",
            "  throw new Error('Expected HttpApiError');",
            "}",
            "",
            "export function extractEnvelopeData<T = unknown>(result: unknown): T {",
            "  if (!isRecord(result) || !('data' in result)) {",
            "    throw new Error('Expected envelope with data');",
            "  }",
            "  return result.data as T;",
            "}",
            "",
            "export function applyRuntimeContext(payload: unknown, context: Record<string, unknown>): Record<string, unknown> {",
            "  const next = isRecord(payload) ? deepClone(payload) : {};",
            "  for (const key of Object.keys(next)) {",
            "    if (key === 'path_params' || key === 'auth_context' || key === 'pathParams' || key === 'authContext') {",
            "      continue;",
            "    }",
            "    if (!trackedContextField(key)) {",
            "      continue;",
            "    }",
            "    if (shouldPreserveExplicitField(key, next[key])) {",
            "      continue;",
            "    }",
            "    const match = resolveContextKey(key, context);",
            "    if (match) {",
            "      next[key] = context[match];",
            "    }",
            "  }",
            "  const pathParams = isRecord(next.path_params) ? next.path_params : {};",
            "  for (const key of Object.keys(pathParams)) {",
            "    if (!trackedContextField(key)) {",
            "      continue;",
            "    }",
            "    const match = resolveContextKey(key, context);",
            "    if (match) {",
            "      pathParams[key] = context[match];",
            "    }",
            "  }",
            "  next.path_params = pathParams;",
            "  next.pathParams = pathParams;",
            "  const authContext = isRecord(next.auth_context) ? next.auth_context : {};",
            "  const tenantMatch = resolveContextKey('tenant_id', context);",
            "  if (tenantMatch) {",
            "    authContext.tenant_id = context[tenantMatch];",
            "  }",
            "  next.auth_context = authContext;",
            "  next.authContext = authContext;",
            "  return next;",
            "}",
            "",
            "export function absorbEnvelopeContext(result: unknown, context: Record<string, unknown>): Record<string, unknown> {",
            "  const source = envelopeRecords(result)[0];",
            "  if (!isRecord(source)) {",
            "    return context;",
            "  }",
            "  for (const [key, value] of Object.entries(source)) {",
            "    if (trackedContextField(key)) {",
            "      context[key] = value;",
            "    }",
            "  }",
            "  return context;",
            "}",
            "",
            "function collectEnvelopeRecords(value: unknown): Record<string, unknown>[] {",
            "  if (Array.isArray(value)) {",
            "    return value.flatMap((item) => collectEnvelopeRecords(item));",
            "  }",
            "  if (!isRecord(value)) {",
            "    return [];",
            "  }",
            "  if (recordIdFieldCandidates(value).length > 0) {",
            "    return [value];",
            "  }",
            "  const nested = Object.values(value).flatMap((entry) => collectEnvelopeRecords(entry));",
            "  return nested.length > 0 ? nested : [value];",
            "}",
            "",
            "function envelopeRecords(result: unknown): Record<string, unknown>[] {",
            "  return collectEnvelopeRecords(extractEnvelopeData<unknown>(result));",
            "}",
            "",
            "function recordIdFieldCandidates(record: Record<string, unknown>): string[] {",
            "  return uniqueStrings(",
            "    Object.keys(record)",
            "      .map((key) => snakeCase(key))",
            "      .filter((key) => key.endsWith('_id')),",
            "  );",
            "}",
            "",
            "function recordFieldValue(record: Record<string, unknown>, field: string): unknown {",
            "  const normalized = snakeCase(field);",
            "  const camel = camelCase(normalized);",
            "  return record[field] ?? record[normalized] ?? record[camel];",
            "}",
            "",
            "function resolveProbeColumn(candidateField: string, columns: string[]): string {",
            "  const requested = snakeCase(candidateField);",
            "  let bestColumn = '';",
            "  let bestScore = -1;",
            "  for (const column of columns) {",
            "    const score = scoreContextKey(requested, snakeCase(column));",
            "    if (score > bestScore) {",
            "      bestColumn = column;",
            "      bestScore = score;",
            "    }",
            "  }",
            "  return bestScore >= 0 ? bestColumn : '';",
            "}",
            "",
            "function resolveComparableColumn(candidateField: string, columns: string[]): string {",
            "  const requested = snakeCase(candidateField);",
            "  let bestColumn = '';",
            "  let bestScore = -1;",
            "  for (const column of columns) {",
            "    const score = scoreContextKey(requested, snakeCase(column));",
            "    if (score > bestScore) {",
            "      bestColumn = column;",
            "      bestScore = score;",
            "    }",
            "  }",
            "  const identifierLike = isIdentifierLikeField(requested);",
            "  if (bestScore >= (identifierLike ? 80 : 90)) {",
            "    return bestColumn;",
            "  }",
            "  if ((requested === 'id' || requested.endsWith('_id')) && columns.includes('id')) {",
            "    return 'id';",
            "  }",
            "  return '';",
            "}",
            "",
            "function isIdentifierLikeField(field: string): boolean {",
            "  const normalized = snakeCase(field);",
            "  return normalized === 'id' || normalized.endsWith('_id');",
            "}",
            "",
            "function looksLikeIsoTimestamp(value: string): boolean {",
            "  return /^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?Z$/.test(value.trim());",
            "}",
            "",
            "function normalizeIsoTimestamp(value: string): string {",
            "  return value.trim().replace('.000Z', 'Z');",
            "}",
            "",
            "function tryParseStructuredValue(value: string): unknown {",
            "  const trimmed = value.trim();",
            "  if (!(trimmed.startsWith('{') || trimmed.startsWith('['))) {",
            "    return value;",
            "  }",
            "  try {",
            "    return JSON.parse(trimmed) as unknown;",
            "  } catch {",
            "    return value;",
            "  }",
            "}",
            "",
            "function canonicalizePersistenceValue(value: unknown): unknown {",
            "  if (value instanceof Date) {",
            "    return normalizeIsoTimestamp(value.toISOString());",
            "  }",
            "  if (Array.isArray(value)) {",
            "    return value.map((item) => canonicalizePersistenceValue(item));",
            "  }",
            "  if (isRecord(value)) {",
            "    return Object.keys(value)",
            "      .sort()",
            "      .reduce<Record<string, unknown>>((accumulator, key) => {",
            "        accumulator[key] = canonicalizePersistenceValue(value[key]);",
            "        return accumulator;",
            "      }, {});",
            "  }",
            "  if (typeof value === 'string' && looksLikeIsoTimestamp(value)) {",
            "    return normalizeIsoTimestamp(value);",
            "  }",
            "  return value;",
            "}",
            "",
            "function normalizePersistenceComparableValue(expected: unknown, actual: unknown): unknown {",
            "  let normalizedActual = actual;",
            "  if (typeof normalizedActual === 'string') {",
            "    const trimmed = normalizedActual.trim();",
            "    if (typeof expected === 'number' && trimmed.length > 0 && !Number.isNaN(Number(trimmed))) {",
            "      normalizedActual = Number(trimmed);",
            "    } else if (typeof expected === 'boolean' && ['true', 'false'].includes(trimmed.toLowerCase())) {",
            "      normalizedActual = trimmed.toLowerCase() === 'true';",
            "    } else if (isRecord(expected) || Array.isArray(expected)) {",
            "      normalizedActual = tryParseStructuredValue(trimmed);",
            "    } else {",
            "      normalizedActual = trimmed;",
            "    }",
            "  } else if (typeof normalizedActual === 'number' && typeof expected === 'string') {",
            "    normalizedActual = String(normalizedActual);",
            "  } else if (typeof normalizedActual === 'boolean' && typeof expected === 'string') {",
            "    normalizedActual = normalizedActual ? 'true' : 'false';",
            "  }",
            "  return canonicalizePersistenceValue(normalizedActual);",
            "}",
            "",
            "function stableJson(value: unknown): string {",
            "  return JSON.stringify(canonicalizePersistenceValue(value));",
            "}",
            "",
            "function normalizeIdentifierComparableValue(field: string, value: unknown): unknown {",
            "  if (value === undefined || value === null) {",
            "    return value;",
            "  }",
            "  const text = stringValue(value);",
            "  if (!text) {",
            "    return canonicalizePersistenceValue(value);",
            "  }",
            "  return normalizeRuntimeIdentifierValue(field, text);",
            "}",
            "",
            "function persistenceValuesMatch(field: string, expected: unknown, actual: unknown): boolean {",
            "  if (isIdentifierLikeField(field)) {",
            "    return stableJson(normalizeIdentifierComparableValue(field, expected)) === stableJson(normalizeIdentifierComparableValue(field, actual));",
            "  }",
            "  return stableJson(expected) === stableJson(normalizePersistenceComparableValue(expected, actual));",
            "}",
            "",
            "export async function queryTableColumns(runtime: BackendRuntime, tableName: string): Promise<string[]> {",
            "  const rows = await runtime.query<{ column_name: string }>(",
            '    "SELECT column_name FROM information_schema.columns WHERE table_schema = \'public\' AND table_name = $1 ORDER BY ordinal_position",',
            "    [tableName],",
            "  );",
            "  return rows.map((row) => String(row.column_name));",
            "}",
            "",
            "export async function requiresPersistenceRoundTripEvidence(runtime: BackendRuntime, operationId: string): Promise<boolean> {",
            "  const hints = persistenceProbeHintsSupport(operationId);",
            "  const strictTableCandidates = uniqueStrings(",
            "    Array.isArray(hints.strictTableCandidates)",
            "      ? hints.strictTableCandidates",
            "      : (Array.isArray(hints.tableCandidates) ? hints.tableCandidates : []),",
            "  );",
            "  for (const tableName of strictTableCandidates) {",
            "    const columns = await queryTableColumns(runtime, tableName);",
            "    if (columns.length > 0) {",
            "      return true;",
            "    }",
            "  }",
            "  return false;",
            "}",
            "",
            "export async function collectPersistenceTargetRowCounts(runtime: BackendRuntime, operationId: string): Promise<Record<string, number>> {",
            "  const hints = persistenceProbeHintsSupport(operationId);",
            "  const strictTableCandidates = uniqueStrings(",
            "    Array.isArray(hints.strictTableCandidates)",
            "      ? hints.strictTableCandidates",
            "      : (Array.isArray(hints.tableCandidates) ? hints.tableCandidates : []),",
            "  );",
            "  const counts: Record<string, number> = {};",
            "  for (const tableName of strictTableCandidates) {",
            "    const columns = await queryTableColumns(runtime, tableName);",
            "    if (columns.length === 0) {",
            "      continue;",
            "    }",
            "    const rows = await runtime.query<{ count: number }>(`SELECT COUNT(*)::int AS count FROM \"${tableName}\"`);",
            "    counts[tableName] = Number(rows[0]?.count ?? 0);",
            "  }",
            "  return counts;",
            "}",
            "",
            "export async function collectPersistenceRoundTripEvidence(runtime: BackendRuntime, operationId: string, result: unknown): Promise<PersistenceRoundTripEvidence[]> {",
            "  const records = envelopeRecords(result);",
            "  if (records.length === 0) {",
            "    return [];",
            "  }",
            "  const hints = persistenceProbeHintsSupport(operationId);",
            "  const tableCandidates = uniqueStrings(Array.isArray(hints.tableCandidates) ? hints.tableCandidates : []);",
            "  const idFieldCandidates = uniqueStrings(",
            "    (Array.isArray(hints.idFieldCandidates) ? hints.idFieldCandidates : []).map((field) => snakeCase(field)),",
            "  );",
            "  const evidence: PersistenceRoundTripEvidence[] = [];",
            "  const seenEvidence = new Set<string>();",
            "  for (const tableName of tableCandidates) {",
            "    const columns = await queryTableColumns(runtime, tableName);",
            "    if (columns.length === 0) {",
            "      continue;",
            "    }",
            "    for (const record of records) {",
            "      const candidateFields = uniqueStrings([...idFieldCandidates, ...recordIdFieldCandidates(record)]);",
            "      for (const idField of candidateFields) {",
            "        const probeColumn = resolveProbeColumn(idField, columns);",
            "        if (!probeColumn) {",
            "          continue;",
            "        }",
            "        const idValue = stringValue(recordFieldValue(record, idField)) || stringValue(recordFieldValue(record, probeColumn));",
            "        if (!idValue) {",
            "          continue;",
            "        }",
            "        const normalizedIdValue = normalizeRuntimeIdentifierValue(probeColumn, idValue);",
            "        const countRows = await runtime.query<{ count: number }>(",
            "          `SELECT COUNT(*)::int AS count FROM \"${tableName}\" WHERE \"${probeColumn}\" = $1`,",
            "          [normalizedIdValue],",
            "        );",
            "        const matchedRows = Number(countRows[0]?.count ?? 0);",
            "        if (matchedRows <= 0) {",
            "          continue;",
            "        }",
            "        const selectedRows = await runtime.query<Record<string, unknown>>(",
            "          `SELECT * FROM \"${tableName}\" WHERE \"${probeColumn}\" = $1 LIMIT 1`,",
            "          [normalizedIdValue],",
            "        );",
            "        const persistedRow = selectedRows[0] ?? {};",
            "        const checkedFieldNames: string[] = [];",
            "        const checkedValueFieldNames: string[] = [];",
            "        const mismatchedFieldNames: string[] = [];",
            "        for (const fieldName of Object.keys(record)) {",
            "          const comparableColumn = resolveComparableColumn(fieldName, columns);",
            "          if (!comparableColumn) {",
            "            continue;",
            "          }",
            "          const expectedValue = recordFieldValue(record, fieldName);",
            "          if (expectedValue === undefined) {",
            "            continue;",
            "          }",
            "          checkedFieldNames.push(fieldName);",
            "          if (!isIdentifierLikeField(fieldName)) {",
            "            checkedValueFieldNames.push(fieldName);",
            "          }",
            "          if (!persistenceValuesMatch(comparableColumn, expectedValue, persistedRow[comparableColumn])) {",
            "            mismatchedFieldNames.push(fieldName);",
            "          }",
            "        }",
            "        const evidenceKey = `${tableName}:${probeColumn}:${normalizedIdValue}`;",
            "        if (seenEvidence.has(evidenceKey)) {",
            "          continue;",
            "        }",
            "        seenEvidence.add(evidenceKey);",
            "        evidence.push({",
            "          tableName,",
            "          idField: probeColumn,",
            "          idValue: normalizedIdValue,",
            "          matchedRows,",
            "          checkedFieldNames,",
            "          checkedValueFieldNames,",
            "          mismatchedFieldNames,",
            "          persistedRow,",
            "        });",
            "      }",
            "    }",
            "  }",
            "  return evidence;",
            "}",
            "",
            "export async function queryTableIndexes(runtime: BackendRuntime, tableName: string): Promise<string[]> {",
            "  const rows = await runtime.query<{ indexname: string }>(",
            '    "SELECT indexname FROM pg_indexes WHERE schemaname = \'public\' AND tablename = $1 ORDER BY indexname",',
            "    [tableName],",
            "  );",
            "  return rows.map((row) => String(row.indexname));",
            "}",
            "",
        ]
    )


def render_generated_runtime_positioning() -> str:
    return "\n".join(
        [
            "# Generated Runtime Positioning",
            "",
            "## Scope",
            "- The foundation package may include a generated runtime to bootstrap early verification, but Phase-3 is not complete while business behavior still depends primarily on it.",
            "- `generated-runtime.ts` now exists as a compatibility facade; shared execution semantics live in `operation-support.ts`, and repository modules should bind through explicit operation plans rather than treating the facade as the default backend.",
            "- Generated controller/service/repository adapters preserve the frozen Phase-2 contract surface, but they must be replaced with real implementation code before `delivery-ready`.",
            "",
            "## Why This Exists In Phase-3",
            "- It makes contract, scenario, replay, lint, typecheck, and build lanes executable early in the implementation cycle.",
            "- It exposes semantic gaps early without claiming that the underlying business/domain stack is complete.",
            "",
            "## Concurrency Validation Boundary",
            "- Phase-3 conflict scenarios normally validate deterministic conflict-path semantics against the generated runtime.",
            "- They prove idempotency, version-conflict handling, retry guidance, and authoritative final state preservation.",
            "- They do not, by themselves, prove production-grade parallel race safety, database lock behavior, or multi-node contention correctness.",
            "",
            "## Replacement Rule",
            "1. Replace repository delegates with real DAL/domain implementations during Phase-3 implementation, not as a default deferred step.",
            "2. Keep the frozen OpenAPI plus unit/contract/scenario/replay tests green during each replacement.",
            "3. Do not treat `generated-runtime.ts` as delivery evidence once real implementation work is underway.",
            "",
            "## Completion Interpretation",
            "- `foundation-ready` means the scaffold and failing-test package are frozen and implementation may start.",
            "- `delivery-ready` requires runnable implementation code plus executed unit/contract/scenario/replay evidence; scaffold-only runtime behavior is insufficient.",
            "",
        ]
    )


def sanitize_route_segment(route_value: str, fallback_surface: str) -> str:
    candidates = [part for part in str(route_value).split("/") if part.strip()]
    normalized = [stable_slug(part, fallback="surface") for part in candidates]
    if normalized:
        return "/".join(normalized)
    return stable_slug(fallback_surface, fallback="surface")


def humanize_ui_label(value: str) -> str:
    candidate = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value)).replace("_", " ").replace("-", " ")
    tokens = [token for token in candidate.split() if token]
    words: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in {"id", "api", "cta", "roi"}:
            words.append(lowered.upper())
        else:
            words.append(lowered.capitalize())
    return " ".join(words) or "Field"


UI_MUTATING_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def ui_page_http_methods(page_contract: dict[str, Any] | None = None) -> set[str]:
    methods: set[str] = set()
    for item in (page_contract or {}).get("data_required", []):
        if not isinstance(item, dict):
            continue
        method = str(item.get("method") or item.get("http_method") or "").strip().upper()
        if method:
            methods.add(method)
    for item in (page_contract or {}).get("actions_and_transitions", []):
        if not isinstance(item, dict):
            continue
        binding = item.get("api_binding")
        if isinstance(binding, dict):
            method = str(binding.get("method") or "").strip().upper()
            if method:
                methods.add(method)
    return methods


def ui_page_section_views(page_contract: dict[str, Any] | None = None) -> set[str]:
    views: set[str] = set()
    for section in (page_contract or {}).get("sections", []):
        if not isinstance(section, dict):
            continue
        view = str(section.get("view") or "").strip().lower()
        if view:
            views.add(view)
    return views


def ui_page_semantics(surface: str, page_contract: dict[str, Any] | None = None) -> dict[str, Any]:
    lowered = surface.lower()
    route_lower = str((page_contract or {}).get("route") or "").strip().lower()
    haystack = " ".join(part for part in (lowered, route_lower) if part)
    tokens = ui_page_interest_tokens(surface, page_contract)
    methods = ui_page_http_methods(page_contract)
    section_views = ui_page_section_views(page_contract)
    data_presentation = {
        str(item).strip().lower()
        for item in (page_contract or {}).get("data_presentation", [])
        if str(item).strip()
    }
    user_inputs = [
        item
        for item in (page_contract or {}).get("user_inputs", [])
        if isinstance(item, dict) and str(item.get("field") or "").strip()
    ]
    summary_cards = [
        str(item).strip()
        for item in (page_contract or {}).get("summary_cards", [])
        if str(item).strip()
    ]
    detail_fields = [
        str(item).strip()
        for item in (page_contract or {}).get("detail_fields_in_order", [])
        if str(item).strip()
    ]
    return {
        "methods": methods,
        "section_views": section_views,
        "tokens": tokens,
        "has_mutation": bool(methods & UI_MUTATING_HTTP_METHODS),
        "has_form_inputs": bool(user_inputs),
        "has_form_section": bool(section_views & {"form", "filter-bar"}),
        "has_table": bool(section_views & {"table", "list"}) or any(
            token in item
            for item in data_presentation
            for token in ("table", "list", "grid", "board")
        ),
        "has_detail": bool(section_views & {"detail", "detail-list"}) or bool(detail_fields),
        "has_summary": bool(section_views & {"summary-cards"}) or bool(summary_cards),
        "is_review": any(
            token in haystack for token in ("review", "report", "revise", "audit")
        ),
        "is_creation": bool({"create", "new", "onboarding", "setup", "registration", "register"} & tokens) or any(
            token in haystack for token in ("create", "new", "onboarding", "setup", "registration", "register")
        ),
    }


def infer_ui_page_role(surface: str, page_contract: dict[str, Any] | None = None) -> str:
    semantics = ui_page_semantics(surface, page_contract)
    methods = semantics["methods"]
    explicit_role = str((page_contract or {}).get("page_role") or "").strip()
    if explicit_role:
        normalized_explicit = explicit_role.lower()
        if normalized_explicit == "detail":
            if semantics["is_review"]:
                return "review"
            if semantics["has_mutation"] and semantics["has_form_inputs"]:
                return "form-flow" if semantics["is_creation"] else "workflow"
            if semantics["has_table"]:
                return "workspace" if semantics["has_summary"] else "list"
        return explicit_role
    lowered = surface.lower()
    if "review" in lowered:
        return "review"
    if "task" in lowered and any(token in lowered for token in ("update", "state", "workflow")):
        return "workflow"
    if any(token in lowered for token in ("recommendation", "detail", "export")):
        return "detail"
    if any(token in lowered for token in ("overview", "dashboard", "findings", "home")):
        return "workspace"
    if any(token in lowered for token in ("list", "queue", "catalog", "search")):
        return "list"
    if any(token in lowered for token in ("onboarding", "setup", "create", "new", "edit", "form")):
        return "form-flow"
    if methods & {"POST", "PUT", "PATCH", "DELETE"}:
        return "form-flow"
    return "detail"


UI_BLUEPRINT_TYPE_ALIASES = {
    "setup-flow": "setup-flow",
    "configuration": "setup-flow",
    "analysis-board": "analysis-board",
    "dashboard": "analysis-board",
    "dashboard-workbench": "analysis-board",
    "record-list": "analysis-board",
    "comparison": "analysis-board",
    "record-workbench": "record-workbench",
    "decision-workbench": "record-workbench",
    "record-editor": "record-workbench",
    "billing-settlement": "record-workbench",
    "workflow-step": "record-workbench",
    "execution-workbench": "execution-workbench",
    "queue-board": "execution-workbench",
    "review-decision": "review-decision",
    "detail-view": "detail-view",
    "entity-detail": "detail-view",
    "record-detail": "detail-view",
}


def normalize_ui_blueprint_type(page_blueprint_type: Any, *, preserve_unknown: bool = False) -> str:
    raw = str(page_blueprint_type or "").strip()
    if not raw:
        return ""
    normalized = re.sub(r"[\s_]+", "-", raw.lower())
    resolved = UI_BLUEPRINT_TYPE_ALIASES.get(normalized)
    if resolved:
        return resolved
    return raw if preserve_unknown else ""


def infer_ui_page_blueprint_type(surface: str, page_contract: dict[str, Any] | None = None) -> str:
    semantics = ui_page_semantics(surface, page_contract)
    explicit_blueprint = normalize_ui_blueprint_type(
        (page_contract or {}).get("page_blueprint_type"),
        preserve_unknown=True,
    )
    if explicit_blueprint:
        if explicit_blueprint == "detail-view":
            if semantics["is_review"]:
                return "review-decision"
            if semantics["has_mutation"] and semantics["has_form_inputs"]:
                return "setup-flow" if semantics["is_creation"] else "record-workbench"
        if explicit_blueprint == "analysis-board" and semantics["has_mutation"] and semantics["has_form_inputs"] and not semantics["has_table"]:
            return "record-workbench"
        return explicit_blueprint
    page_role = infer_ui_page_role(surface, page_contract)
    lowered = surface.lower()
    route_lower = str(page_contract.get("route") or "").strip().lower() if page_contract else ""
    blueprint_haystack = " ".join(part for part in (lowered, route_lower) if part)
    tokens = semantics["tokens"]
    if page_role == "review" or any(token in blueprint_haystack for token in ("review", "report", "revise")) or {"review", "report", "revise"} & tokens:
        return "review-decision"
    if page_role == "form-flow" or any(token in blueprint_haystack for token in ("onboarding", "setup", "create", "new", "edit", "form")):
        return "setup-flow"
    if page_role == "workflow" and semantics["has_form_inputs"] and not semantics["has_table"]:
        return "record-workbench"
    if page_role in {"workspace", "list"} or any(token in blueprint_haystack for token in ("overview", "findings", "dashboard", "home")):
        return "analysis-board"
    if page_role == "detail" or any(token in blueprint_haystack for token in ("detail", "profile", "view")):
        return "detail-view"
    if (
        page_role == "workflow"
        or any(token in blueprint_haystack for token in ("task-state", "task_state", "task update", "task-update", "execution"))
        or ("task" in blueprint_haystack and "update" in blueprint_haystack)
    ):
        return "execution-workbench"
    if {"onboarding", "setup"} & tokens:
        return "setup-flow"
    if {"overview", "findings", "dashboard"} & tokens:
        return "analysis-board"
    if {"recommendation", "export"} & tokens:
        return "record-workbench"
    if {"detail", "profile", "view"} & tokens:
        return "detail-view"
    if {"task", "execution"} & tokens:
        return "execution-workbench"
    return "detail-view"


def _normalize_ui_input_options(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            value = str(item.get("value") or "").strip()
            label = str(item.get("label") or value).strip()
        else:
            value = str(item).strip()
            label = humanize_ui_label(value)
        if not value:
            continue
        normalized.append({"value": value, "label": label or humanize_ui_label(value)})
    return normalized


def _infer_ui_input_datatype(field: str, validation: str) -> str:
    normalized = str(field).strip()
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized).replace("-", "_").lower()
    lowered_validation = str(validation or "").strip().lower()
    if "boolean" in lowered_validation:
        return "boolean"
    if "json" in lowered_validation:
        return "json"
    if "list" in lowered_validation:
        return "list"
    if "enum" in lowered_validation:
        return "enum"
    if lowered_validation in {"identifier", "integer", "number", "date", "datetime"}:
        return lowered_validation
    if normalized.endswith("Id") or snake.endswith("_id"):
        return "identifier"
    if any(token in snake for token in ("datetime", "timestamp")) or snake.endswith("_at") or (("date" in snake or "time" in snake) and "update" not in snake):
        return "datetime" if "time" in snake or "datetime" in snake or snake.endswith("_at") else "date"
    if any(token in snake for token in ("age", "count", "total", "quantity", "size", "index", "page_size", "version")):
        return "integer"
    if any(token in snake for token in ("amount", "price", "fee", "cost", "rate", "score", "percent")):
        return "number"
    return "text"


def _default_ui_input_control(*, field: str, datatype: str, value_source: str, editability: str, options: list[dict[str, str]]) -> str:
    normalized = str(field).strip()
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized).replace("-", "_").lower()
    if editability == "hidden" or value_source == "auth-session":
        return "hidden"
    if editability == "readonly":
        return "readonly"
    if datatype == "boolean":
        return "checkbox"
    if datatype in {"json", "list"}:
        return "textarea"
    if datatype == "enum" or options:
        return "select"
    if datatype in {"integer", "number"}:
        return "number"
    if datatype == "date":
        return "date"
    if datatype == "datetime":
        return "datetime"
    if datatype == "identifier" and not (normalized in {"tenantId", "tenant_id"} or snake == "tenant_id"):
        return "lookup"
    return "text"


def _default_ui_input_display_format(*, datatype: str, control: str, value_source: str) -> str:
    if control == "hidden":
        return "hidden"
    if control == "lookup":
        return "lookup"
    if value_source in {"workflow-context", "response-binding"}:
        return "reference"
    if datatype == "enum":
        return "badge"
    if datatype in {"integer", "number"}:
        return "numeric"
    if datatype in {"date", "datetime"}:
        return datatype
    if datatype in {"json", "list"}:
        return "multiline"
    if datatype == "boolean":
        return "boolean"
    if datatype == "identifier":
        return "identifier"
    return "text"


def normalize_ui_input_spec(item: dict[str, Any], *, locale: str = "en") -> dict[str, Any]:
    field = str(item.get("field") or "").strip()
    validation = str(item.get("validation") or "text").strip() or "text"
    datatype = str(item.get("datatype") or "").strip() or _infer_ui_input_datatype(field, validation)
    options = _normalize_ui_input_options(item.get("options"))
    value_source = str(item.get("value_source") or "user-input").strip() or "user-input"
    editability = str(item.get("editability") or "").strip() or (
        "hidden" if value_source in {"auth-session", "system-generated", "server-default"}
        else ("readonly" if value_source == "response-binding" else "editable")
    )
    control = str(item.get("control") or "").strip() or _default_ui_input_control(
        field=field,
        datatype=datatype,
        value_source=value_source,
        editability=editability,
        options=options,
    )
    label = str(item.get("label") or humanize_ui_label(field)).strip() or humanize_ui_label(field)
    if is_zh_locale(locale):
        default_placeholder = f"请输入{label}"
        default_helper = ""
        default_group = "主要输入" if bool(item.get("required")) else "可选输入"
        if control in {"select", "lookup"}:
            default_placeholder = f"请选择{label}"
        elif control == "hidden":
            default_placeholder = "由系统生成并自动携带"
            default_helper = "这个值由系统生成或从当前会话继承，不需要人工填写。"
        elif editability == "readonly":
            default_helper = "这个值来自当前流程上下文，会在本步骤中继续沿用。"
    else:
        default_placeholder = f"Enter {label.lower()}"
        default_helper = ""
        default_group = "Primary input" if bool(item.get("required")) else "Optional input"
        if control in {"select", "lookup"}:
            default_placeholder = f"Select {label.lower()}"
        elif control == "hidden":
            default_placeholder = "Generated by the system"
            default_helper = "This value is generated by the system or carried from the current session."
        elif editability == "readonly":
            default_helper = "This value is carried from the current record context."
    return {
        "field": field,
        "label": label,
        "required": bool(item.get("required")),
        "validation": validation,
        "value_source": value_source,
        "editability": editability,
        "datatype": datatype,
        "control": control,
        "options": options,
        "options_source": str(item.get("options_source") or "").strip(),
        "system_generated": bool(item.get("system_generated")),
        "server_assigned": bool(item.get("server_assigned")),
        "lookup_entity": str(item.get("lookup_entity") or "").strip(),
        "display_format": str(item.get("display_format") or _default_ui_input_display_format(datatype=datatype, control=control, value_source=value_source)).strip(),
        "placeholder": str(item.get("placeholder") or default_placeholder).strip(),
        "helper": str(item.get("helper") or default_helper).strip(),
        "group": str(item.get("group") or default_group).strip(),
    }


def _surface_business_label(surface: str, locale: str) -> str:
    label = localize_surface_title(surface, locale).strip()
    return label or humanize_ui_label(surface)



def _surface_section_title(surface: str, *, kind: str, locale: str) -> str:
    label = _surface_business_label(surface, locale)
    if is_zh_locale(locale):
        mapping = {
            "summary": f"{label}概览",
            "context": f"当前{label}",
            "selector": "查找当前记录",
            "form": f"{label}信息",
            "result": f"已保存的{label}",
            "status": "操作状态",
            "selection": "当前选中记录",
            "workload": "当前待办",
            "next": "下一步",
            "detail": f"{label}详情",
            "list": f"{label}列表",
        }
    else:
        mapping = {
            "summary": f"{label} overview",
            "context": f"Current {label}",
            "selector": "Find current record",
            "form": f"{label} details",
            "result": f"Saved {label}",
            "status": "Action status",
            "selection": "Current selection",
            "workload": "Active workload",
            "next": "Next step",
            "detail": f"{label} details",
            "list": f"{label} list",
        }
    return mapping.get(kind, label)



def default_ui_page_sections(
    surface: str,
    *,
    page_role: str,
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    locale: str = "en",
) -> list[dict[str, Any]]:
    summary_fields = display_fields[:4]
    input_fields = [str(item.get("field") or "").strip() for item in user_inputs if str(item.get("field") or "").strip()]
    if page_role == "workspace":
        return [
            {
                "section_id": "summary",
                "title": _surface_section_title(surface, kind="summary", locale=locale),
                "purpose": "Show the live operating state and the most important context for this workspace.",
                "view": "summary-cards",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "priorities",
                "title": _surface_section_title(surface, kind="workload", locale=locale),
                "purpose": "Keep the current work queue visible so the operator can choose the next record quickly.",
                "view": "list",
                "bind_fields": display_fields[:6],
            },
            {
                "section_id": "next-action",
                "title": _surface_section_title(surface, kind="next", locale=locale),
                "purpose": "Make the immediate next step visible without exposing reviewer-only guidance.",
                "view": "cta-panel",
                "bind_fields": [],
            },
        ]
    if page_role == "list":
        return [
            {
                "section_id": "filters",
                "title": _surface_section_title(surface, kind="selector", locale=locale),
                "purpose": "Narrow the working set before opening a record.",
                "view": "filter-bar",
                "bind_fields": input_fields,
            },
            {
                "section_id": "results",
                "title": _surface_section_title(surface, kind="list", locale=locale),
                "purpose": "Keep the current list view readable and scannable.",
                "view": "table",
                "bind_fields": display_fields[:6],
            },
            {
                "section_id": "selection",
                "title": _surface_section_title(surface, kind="selection", locale=locale),
                "purpose": "Keep the selected record visible while the operator decides what to do next.",
                "view": "detail",
                "bind_fields": summary_fields,
            },
        ]
    if page_role == "detail":
        return [
            {
                "section_id": "summary",
                "title": _surface_section_title(surface, kind="context", locale=locale),
                "purpose": "Surface the primary record details before the next handoff decision.",
                "view": "detail",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "supporting-detail",
                "title": _surface_section_title(surface, kind="detail", locale=locale),
                "purpose": "Keep supporting evidence and related records visible together.",
                "view": "detail-list",
                "bind_fields": display_fields[:8],
            },
            {
                "section_id": "handoff-readiness",
                "title": _surface_section_title(surface, kind="status", locale=locale),
                "purpose": "Show what is ready for the next action or handoff.",
                "view": "status-banner",
                "bind_fields": [],
            },
        ]
    if page_role == "workflow":
        return [
            {
                "section_id": "current-progress",
                "title": _surface_section_title(surface, kind="status", locale=locale),
                "purpose": "Show the latest workflow state for the current record.",
                "view": "status-banner",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "update-form",
                "title": _surface_section_title(surface, kind="form", locale=locale),
                "purpose": "Capture the inputs required to complete this business step.",
                "view": "form",
                "bind_fields": input_fields,
            },
            {
                "section_id": "confirmation",
                "title": _surface_section_title(surface, kind="result", locale=locale),
                "purpose": "Show the saved result once the update is accepted.",
                "view": "result",
                "bind_fields": display_fields[:6],
            },
        ]
    if page_role == "review":
        return [
            {
                "section_id": "report-summary",
                "title": _surface_section_title(surface, kind="summary", locale=locale),
                "purpose": "Summarize the current review posture and supporting evidence.",
                "view": "summary-cards",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "decision",
                "title": _surface_section_title(surface, kind="form", locale=locale),
                "purpose": "Capture the decision with enough context for the next cycle.",
                "view": "form",
                "bind_fields": input_fields,
            },
            {
                "section_id": "follow-up",
                "title": _surface_section_title(surface, kind="next", locale=locale),
                "purpose": "Keep the immediate follow-up visible after submission.",
                "view": "next-steps",
                "bind_fields": [],
            },
        ]
    return [
        {
            "section_id": "context",
            "title": _surface_section_title(surface, kind="context", locale=locale),
            "purpose": "Give the operator the essential context before they change anything on this page.",
            "view": "detail",
            "bind_fields": summary_fields,
        },
        {
            "section_id": "work-area",
            "title": _surface_section_title(surface, kind="form", locale=locale),
            "purpose": "Capture the inputs required to complete this step.",
            "view": "form",
            "bind_fields": input_fields,
        },
        {
            "section_id": "result",
            "title": _surface_section_title(surface, kind="result", locale=locale),
            "purpose": "Show the saved state after the action completes.",
            "view": "result",
            "bind_fields": display_fields[:6],
        },
    ]


def merge_preferred_ui_sections(
    *,
    preferred_sections: list[dict[str, Any]],
    synthesized_sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_preferred = [
        section
        for section in preferred_sections
        if isinstance(section, dict) and str(section.get("section_id") or "").strip()
    ]
    if not normalized_preferred:
        return [
            section
            for section in synthesized_sections
            if isinstance(section, dict) and str(section.get("section_id") or "").strip()
        ]
    merged = [dict(section) for section in normalized_preferred]
    synthesized_by_id: dict[str, dict[str, Any]] = {}
    synthesized_by_view: dict[str, dict[str, Any]] = {}
    for section in synthesized_sections:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id") or "").strip()
        view = str(section.get("view") or "").strip().lower()
        if section_id and section_id not in synthesized_by_id:
            synthesized_by_id[section_id] = section
        if view and view not in synthesized_by_view:
            synthesized_by_view[view] = section
    for section in merged:
        section_id = str(section.get("section_id") or "").strip()
        view = str(section.get("view") or "").strip().lower()
        synthesized = synthesized_by_id.get(section_id) or synthesized_by_view.get(view)
        if view == "filter-bar" and synthesized:
            section["bind_fields"] = _merge_bind_fields(
                [str(item).strip() for item in synthesized.get("bind_fields", []) if str(item).strip()],
                [str(item).strip() for item in section.get("bind_fields", []) if str(item).strip()],
            )
    present_ids = {str(section.get("section_id") or "").strip() for section in merged}
    present_views = {str(section.get("view") or "").strip().lower() for section in merged}
    augmentable_ids = {"filters", "latest-result", "state-honesty"}
    # Preserve runtime scaffolding plus the synthesized primary work area when
    # the upstream contract omitted an explicit form section.
    augmentable_views = {"filter-bar", "result", "status-banner", "form"}
    for section in synthesized_sections:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id") or "").strip()
        view = str(section.get("view") or "").strip().lower()
        if not section_id or section_id in present_ids:
            continue
        if section_id not in augmentable_ids and view not in augmentable_views:
            continue
        if view and view in present_views:
            continue
        merged.append(dict(section))
        present_ids.add(section_id)
        if view:
            present_views.add(view)
    return merged




def _merge_bind_fields(prioritized_fields: list[str], existing_fields: list[str]) -> list[str]:
    merged: list[str] = []
    for field in [*prioritized_fields, *existing_fields]:
        normalized = str(field).strip()
        if not normalized or normalized in {"tenantId", "tenant_id"} or normalized in merged:
            continue
        merged.append(normalized)
    return merged


def _selector_bind_fields(
    *,
    user_inputs: list[dict[str, Any]],
    selector_fields: list[str],
    filters_and_selectors: list[str],
) -> list[str]:
    input_fields = [str(item.get("field") or "").strip() for item in user_inputs if str(item.get("field") or "").strip()]
    candidates = _merge_bind_fields(selector_fields, input_fields)
    if not candidates:
        return []
    if not filters_and_selectors:
        return candidates[:1]
    return candidates[: max(1, min(len(filters_and_selectors), len(candidates)))]



def _selector_input_validation(field: str) -> str:
    normalized = str(field).strip()
    lowered = normalized.lower()
    if lowered.endswith("id") or lowered.endswith("_id"):
        return "identifier"
    if lowered in {"status", "state"} or lowered.endswith("status") or lowered.endswith("state"):
        return "enum"
    if "version" in lowered:
        return "integer"
    return "text"


def augment_user_inputs_with_selector_fields(
    *,
    user_inputs: list[dict[str, Any]],
    selector_fields: list[str],
    actions: list[dict[str, Any]],
    locale: str,
) -> list[dict[str, Any]]:
    if not selector_fields:
        return user_inputs
    existing_fields = {
        str(item.get("field") or "").strip()
        for item in user_inputs
        if isinstance(item, dict) and str(item.get("field") or "").strip()
    }
    required_fields = {
        str(field).strip()
        for action in actions
        if isinstance(action, dict)
        for field in action.get("required_fields", [])
        if str(field).strip()
    }
    selector_group = "记录查找" if is_zh_locale(locale) else "Record lookup"
    augmented = list(user_inputs)
    for field in selector_fields:
        normalized = str(field).strip()
        if not normalized or normalized in {"tenantId", "tenant_id"} or normalized in existing_fields:
            continue
        validation = _selector_input_validation(normalized)
        datatype = _infer_ui_input_datatype(normalized, validation)
        lookup_entity = ""
        if datatype == "identifier":
            stem = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized).replace("-", "_").lower()
            lookup_entity = stem[:-3] if stem.endswith("_id") else (stem[:-2] if stem.endswith("id") else stem)
        control = "lookup" if datatype == "identifier" else ("select" if datatype == "enum" else "text")
        augmented.append(
            normalize_ui_input_spec(
                {
                    "field": normalized,
                    "required": normalized in required_fields,
                    "validation": validation,
                    "group": selector_group,
                    "value_source": "workflow-context",
                    "editability": "editable",
                    "datatype": datatype,
                    "control": control,
                    "lookup_entity": lookup_entity,
                    "options_source": f"entity:{lookup_entity}" if control == "lookup" and lookup_entity else "",
                    "display_format": "lookup" if control == "lookup" else "selector",
                },
                locale=locale,
            )
        )
        existing_fields.add(normalized)
    return augmented

def contract_driven_ui_sections(
    *,
    surface: str,
    page_role: str,
    locale: str,
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    selector_fields: list[str],
    summary_cards: list[str],
    detail_fields_in_order: list[str],
    table_columns: list[str],
    filters_and_selectors: list[str],
    submission_feedback: list[str],
    required_status_messages: list[str],
) -> list[dict[str, Any]]:
    if not any([summary_cards, detail_fields_in_order, table_columns, filters_and_selectors, submission_feedback, required_status_messages]):
        return []
    sections = default_ui_page_sections(
        surface,
        page_role=page_role,
        display_fields=display_fields,
        user_inputs=user_inputs,
        locale=locale,
    )
    input_fields = [str(item.get("field") or "").strip() for item in user_inputs if str(item.get("field") or "").strip()]
    selector_bind_fields = _selector_bind_fields(
        user_inputs=user_inputs,
        selector_fields=selector_fields,
        filters_and_selectors=filters_and_selectors,
    )
    has_view = {str(item.get("view") or "").strip().lower() for item in sections if isinstance(item, dict)}
    if filters_and_selectors and selector_bind_fields:
        for section in sections:
            if not isinstance(section, dict):
                continue
            if str(section.get("view") or "").strip().lower() == "filter-bar":
                section["bind_fields"] = _merge_bind_fields(
                    selector_bind_fields,
                    [str(item).strip() for item in section.get("bind_fields", []) if str(item).strip()],
                )
                break
        else:
            sections.insert(
                1 if sections else 0,
                {
                    "section_id": "filters",
                    "title": _surface_section_title(surface, kind="selector", locale=locale),
                    "purpose": "Choose the current record before acting in the main workspace.",
                    "view": "filter-bar",
                    "bind_fields": selector_bind_fields,
                },
            )
            has_view.add("filter-bar")
    remaining_form_fields = [field for field in input_fields if field not in set(selector_bind_fields)]
    should_add_form = "form" not in has_view and bool(
        remaining_form_fields if filters_and_selectors else len(input_fields) > 1
    )
    if should_add_form:
        sections.insert(
            2 if filters_and_selectors and len(sections) >= 2 else 1 if sections else 0,
            {
                "section_id": "work-form",
                "title": _surface_section_title(surface, kind="form", locale=locale),
                "purpose": "Keep the business inputs required for this step in the primary workspace.",
                "view": "form",
                "bind_fields": remaining_form_fields or input_fields,
            },
        )
        has_view.add("form")
    if submission_feedback and "result" not in has_view:
        sections.append(
            {
                "section_id": "latest-result",
                "title": _surface_section_title(surface, kind="result", locale=locale),
                "purpose": "Keep the latest outcome visible after the action succeeds.",
                "view": "result",
                "bind_fields": display_fields[:6],
            }
        )
    if required_status_messages and "status-banner" not in has_view:
        sections.append(
            {
                "section_id": "state-honesty",
                "title": _surface_section_title(surface, kind="status", locale=locale),
                "purpose": "Keep loading, empty, error, and blocked states explicit.",
                "view": "status-banner",
                "bind_fields": display_fields[:4],
            }
        )
    return sections


def default_ui_page_copy(
    surface: str,
    *,
    page_role: str,
    actions: list[dict[str, Any]],
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    locale: str = "en",
) -> dict[str, Any]:
    lowered = surface.lower()
    localized_surface = localize_surface_title(surface, locale)
    success_copy = surface_success_copy(surface, page_role, locale)
    if is_zh_locale(locale):
        if "onboarding" in lowered or "setup" in lowered:
            subtitle = "在执行开始前确认范围详情和基线上下文。"
            goal = "采集激活后续观察与审核工作所需的范围信息。"
            primary_label = "加载范围配置"
        elif "overview" in lowered or "findings" in lowered:
            subtitle = "查看当前信号图景、待处理发现以及需要关注的区域。"
            goal = "理解哪些内容发生了变化、哪些被阻塞，以及应优先处理哪些发现。"
            primary_label = "刷新总览与发现"
        elif "recommendation" in lowered:
            subtitle = "查看建议详情、支撑信息以及下游执行所需的交接上下文。"
            goal = "查看建议详情，并在不丢失上下文的前提下准备任务交接。"
            primary_label = "加载建议详情"
        elif "task" in lowered:
            subtitle = "保持执行轨迹最新，并让状态变化对后续流程清晰可见。"
            goal = "记录最新任务结果，并让工作流状态对下一位操作者保持同步。"
            primary_label = "提交任务更新"
        elif "review" in lowered:
            subtitle = "汇总当前结果、记录操作人决策，并显式保留不确定性。"
            goal = "记录继续或修订决策，并为下一轮审核保留足够上下文。"
            primary_label = "提交审核决策"
        elif page_role == "workspace":
            subtitle = "查看当前角色工作区的实时状态，并处理当前待办。"
            goal = "确认当前需要处理的事项，并进入正确的业务页面。"
            primary_label = f"打开{localized_surface}"
        elif page_role == "list":
            subtitle = "定位当前需要处理的记录，并直接进入处理。"
            goal = "快速找到目标记录，并带着必要上下文继续操作。"
            primary_label = f"打开{localized_surface}"
        elif page_role == "workflow":
            subtitle = "完成当前业务动作，并让结果继续停留在本页可见。"
            goal = "用必需输入完成当前业务步骤，并保留清晰反馈。"
            primary_label = f"保存{localized_surface}"
        else:
            subtitle = "查看当前记录，并完成分配到本页的业务任务。"
            goal = "在本页完成当前业务任务，并保持结果可见。"
            primary_label = f"打开{localized_surface}"
        primary_hint = "使用这个操作完成当前业务任务，并保留记录上下文。"
        secondary_label = "刷新当前数据" if page_role in {"workspace", "list", "detail"} else "继续编辑"
        empty_headline = f"暂无{localized_surface}数据" if page_role in {"workspace", "list"} else "当前还没有可展示的数据"
        empty_body = "完成必需输入或加载当前记录后，这个页面才会被填充。"
        success_headline = success_copy["headline"]
        success_body = success_copy["body"]
        error_headline = "无法保存当前变更" if page_role in {"form-flow", "workflow", "review"} else "无法加载当前视图"
        error_body = "保留页面结构，清楚说明差距，并展示安全重试方式。"
    else:
        if "onboarding" in lowered or "setup" in lowered:
            subtitle = "Confirm the scope details and baseline context before execution begins."
            goal = "Capture the scope information required to activate downstream observation and review work."
            primary_label = "Load scope setup"
        elif "overview" in lowered or "findings" in lowered:
            subtitle = "Review the current signal picture, outstanding findings, and the areas that need attention."
            goal = "Understand what changed, what is blocked, and which findings should be handled first."
            primary_label = "Refresh findings overview"
        elif "recommendation" in lowered:
            subtitle = "Inspect the recommendation, supporting detail, and the handoff context for downstream execution."
            goal = "Review the recommendation details and prepare a clean task handoff without losing context."
            primary_label = "Load recommendation detail"
        elif "task" in lowered:
            subtitle = "Keep the execution trail current and make state changes visible to the rest of the workflow."
            goal = "Record the latest task outcome and keep the workflow state synchronized for the next operator."
            primary_label = "Submit task update"
        elif "review" in lowered:
            subtitle = "Summarize the outcome, record the operator decision, and keep uncertainty explicit."
            goal = "Record a continue-or-revise decision with enough context for the next review cycle."
            primary_label = "Submit review decision"
        elif page_role == "workspace":
            subtitle = "Review the live operating state for this role and act on the current workload."
            goal = "See what needs action now and open the correct business page."
            primary_label = f"Open {surface}"
        elif page_role == "list":
            subtitle = "Find the record that needs action and open it directly."
            goal = "Locate the target record quickly and continue with the context you need."
            primary_label = f"Open {surface}"
        elif page_role == "workflow":
            subtitle = "Complete the current business action and keep the outcome visible on this page."
            goal = "Finish this business step with the required inputs and visible feedback."
            primary_label = f"Save {surface}"
        else:
            subtitle = "Review the current record and finish the task assigned to this page."
            goal = "Finish the current business task on this page and keep the result visible."
            primary_label = f"Open {surface}"
        primary_hint = "Use this action to complete the current business task without dropping record context."
        secondary_label = "Refresh current data" if page_role in {"workspace", "list", "detail"} else "Keep editing"
        empty_headline = f"No {surface.lower()} data yet" if page_role in {"workspace", "list"} else "Nothing is ready to show yet"
        empty_body = "Complete the required inputs or load the current record to populate this page."
        success_headline = success_copy["headline"]
        success_body = success_copy["body"]
        error_headline = "We could not save your change" if page_role in {"form-flow", "workflow", "review"} else "We could not load the current view"
        error_body = "Keep the page structure visible, explain the gap clearly, and show how to retry safely."
    first_action = next((str(item.get("action") or "").strip() for item in actions if str(item.get("action") or "").strip()), "")
    return {
        "eyebrow": page_role_eyebrow(page_role, locale),
        "subtitle": subtitle,
        "user_goal": goal,
        "primary_cta": {
            "label": first_action or primary_label,
            "hint": primary_hint,
        },
        "secondary_cta": {
            "label": secondary_label,
            "kind": "refresh" if page_role in {"workspace", "list", "detail"} else "secondary",
        },
        "sections": default_ui_page_sections(surface, page_role=page_role, display_fields=display_fields, user_inputs=user_inputs, locale=locale),
        "empty_state": {
            "headline": empty_headline,
            "body": empty_body,
        },
        "success_state": {
            "headline": success_headline,
            "body": success_body,
        },
        "error_state": {
            "headline": error_headline,
            "body": error_body,
        },
    }


def contract_driven_data_presentation(
    *,
    summary_cards: list[str],
    detail_fields_in_order: list[str],
    table_columns: list[str],
    filters_and_selectors: list[str],
    required_status_messages: list[str],
    submission_feedback: list[str],
) -> list[str]:
    items: list[str] = []
    if summary_cards:
        items.append("summary-cards")
    if filters_and_selectors:
        items.append("filter-bar")
    if table_columns:
        items.append("table-or-list")
    if detail_fields_in_order:
        items.append("detail-panel")
    if submission_feedback:
        items.append("submission-result")
    if required_status_messages:
        items.append("status-banner")
    return list(dict.fromkeys(items))


def localize_rendered_ui_code(rendered: str, *, locale: str) -> str:
    if locale != "zh-CN":
        return rendered
    replacements = {
        "Delivery workspace": ui_text(locale, "delivery_workspace"),
        "Runnable MVP": ui_text(locale, "runnable_mvp"),
        "Operate the runnable workflow": ui_text(locale, "operate_runnable_workflow"),
        "Open the page you need, keep the latest record state visible, and submit the next workflow action against the running service.": ui_text(locale, "workspace_intro"),
        "Open business pages that keep inputs, current data, and next actions connected to the running backend.": ui_text(locale, "workspace_intro_compact"),
        "Open primary workspace": ui_text(locale, "open_primary_workspace"),
        "Primary work area": ui_text(locale, "primary_work_area"),
        "No pages generated yet": ui_text(locale, "no_pages_generated_yet"),
        "Generate at least one IA-backed page to continue.": ui_text(locale, "generate_ia_backed_page_to_continue"),
        "Live work areas": ui_text(locale, "live_work_areas"),
        "Each page should keep the goal, work area, current data, and next steps visible together.": ui_text(locale, "live_work_areas_hint"),
        "Connected runtime coverage": ui_text(locale, "connected_runtime_coverage"),
        "The MVP keeps business pages tied to runnable backend operations instead of a detached mock console.": ui_text(locale, "connected_runtime_hint"),
        "Available work areas": ui_text(locale, "available_work_areas"),
        "Choose the page that matches the job to be done. Each work area should expose the data the user must see and the input they must submit.": ui_text(locale, "available_work_areas_hint"),
        "Open page": ui_text(locale, "open_page"),
        "Primary action": ui_text(locale, "primary_action"),
        "Linked service actions": ui_text(locale, "linked_service_actions"),
        "Delivery slices": ui_text(locale, "delivery_slices"),
        "Workspace</Link>": ui_text(locale, "workspace_menu") + "</Link>",
        "Back to workspace": ui_text(locale, "back_to_workspace"),
        "Previous page": ui_text(locale, "previous_page"),
        "Next page": ui_text(locale, "next_page"),
        "Business role": "适用角色",
        "Information objects": "信息对象",
        "Current stage": "当前阶段",
        "Current status": "当前状态",
        "What this page unlocks": "本页完成后解锁",
        "Saved context": "已保存的上下文",
        "Auto carry-forward": "自动延续",
        "Non-empty identifiers and business inputs will be carried into the next page automatically.": "非空的标识符和业务输入会自动带入下一页。",
        "Must stay visible together": "必须一起可见",
        "Required inputs or confirmations": "必须输入或确认",
        "Context continuity": "上下文延续",
        "Execution brief": "执行约束",
        "Summary cards": "摘要卡片",
        "Detail fields in order": "详情字段顺序",
        "Table columns": "列表列",
        "Filters and selectors": "筛选与选择器",
        "Submission feedback": "提交反馈",
        "Required status messages": "必须状态提示",
        "Goal for this page": ui_text(locale, "goal_for_this_page"),
        "Main action": ui_text(locale, "main_action"),
        "Use this action to move the workflow forward.": ui_text(locale, "main_action_hint"),
        "Ready when": ui_text(locale, "ready_when"),
        "Work area": ui_text(locale, "work_area"),
        "Fill in the required details, keep the current context visible, and submit when this step is ready.": ui_text(locale, "work_area_hint"),
        "Complete the current business action with the fields below. Values captured earlier in the workflow remain available here.": "用下方字段完成当前业务动作，前面步骤里已经填写过的上下文会继续保留在这里。",
        "(required)": ui_text(locale, "required_suffix"),
        "(optional)": ui_text(locale, "optional_suffix"),
        "Enter value": ui_text(locale, "enter_value"),
        "Choose an option": ui_text(locale, "choose_option"),
        ">Yes<": ">" + ui_text(locale, "yes") + "<",
        ">No<": ">" + ui_text(locale, "no") + "<",
        "Refresh current data": ui_text(locale, "refresh_current_data"),
        "Working selectors": "当前筛选与选择",
        "Pending live data": "等待实时数据",
        "Page structure": ui_text(locale, "page_structure"),
        "Bound fields:": ui_text(locale, "bound_fields") + ":",
        "Workflow steps": ui_text(locale, "workflow_steps"),
        "Business steps on this page": "本页业务步骤",
        "Choose the step that matches what you need to do on this page.": ui_text(locale, "workflow_steps_hint"),
        "Choose the business step that matches what you need to complete on this page.": "选择本页当前需要完成的业务步骤。",
        "Current step": ui_text(locale, "current_step"),
        "This action needs": ui_text(locale, "this_action_needs"),
        "This action needs:": ui_text(locale, "this_action_needs") + ":",
        "It updates": ui_text(locale, "it_updates"),
        "It updates:": ui_text(locale, "it_updates") + ":",
        "Select step": ui_text(locale, "select_step"),
        "After each action": ui_text(locale, "after_each_action"),
        "Success:": ui_text(locale, "success_prefix") + ":",
        "Retry path:": ui_text(locale, "retry_path") + ":",
        "Current snapshot": ui_text(locale, "current_snapshot"),
        "Current results": ui_text(locale, "current_results"),
        "Current detail": ui_text(locale, "current_detail"),
        "Current context": ui_text(locale, "current_context"),
        "Complete this step": "完成本步",
        "Visible context": "可见上下文",
        "Save action": "保存动作",
        "Record overview": "记录概览",
        "Related context": "相关上下文",
        "Visible state changes": "可见状态变化",
        "State changes operators must see": "操作方必须看到的状态变化",
        "Decision state changes": "决策状态变化",
        "Execution state changes": "执行状态变化",
        "Review state changes": "审核状态变化",
        "Current task": "当前任务",
        "Current action": "当前动作",
        "Scope readiness": "范围就绪情况",
        "Prepare next action": "准备下一步操作",
        "Created scope and launch result": "已创建范围与启动结果",
        "Current results": "当前结果",
        "Action status": "操作状态",
        "Submission status": "提交状态",
        "Saved scope and launch result": "已保存范围与启动结果",
        "Scope context": "范围上下文",
        "Next action": "下一步动作",
        "Next step": "下一步",
        "Continue workflow": "继续工作流",
        "Findings board": "发现看板",
        "Board status": "看板状态",
        "Next workflow actions": "后续工作流动作",
        "Decision summary": "决策摘要",
        "Evidence reading chain": "证据阅读链路",
        "Freeze recommendation": "冻结建议",
        "Decision output": "决策输出",
        "Export to execution": "导出到执行",
        "Execution summary": "执行摘要",
        "Task board": "任务看板",
        "Update task state": "更新任务状态",
        "Execution evidence": "执行证据",
        "Task status": "任务状态",
        "Downstream review": "下游审核",
        "Review outcome summary": "审核结果摘要",
        "Review evidence": "审核证据",
        "Decision and follow-up": "决策与后续动作",
        "Published review": "已发布审核",
        "Review status": "审核状态",
        "Continue or revise": "继续或修订",
        "Context snapshot": "上下文快照",
        "Current record": "当前记录",
        "Update record": "更新记录",
        "Action: ": "动作：",
        "Business role": "业务角色",
        "Primary work region": "主工作区",
        "Information objects": "信息对象",
        "Current status": "当前状态",
        "Support regions": "支持区域",
        "Latest workflow state": ui_text(locale, "latest_workflow_state"),
        "Review context": ui_text(locale, "review_context"),
        "Active role": ui_text(locale, "active_role"),
        "This role can review current data but cannot submit changes on this page.": ui_text(locale, "role_access_limited"),
        "Current data": ui_text(locale, "current_data"),
        "Updating this page": ui_text(locale, "updating_this_page"),
        "Ready to work": ui_text(locale, "ready_to_work"),
        "Loading the latest workflow data for this page.": ui_text(locale, "loading_latest_workflow_data"),
        "Loading...": ui_text(locale, "loading"),
        "Saving...": ui_text(locale, "saving"),
        "This page is waiting for its primary data binding.": ui_text(locale, "page_waiting_binding"),
        "Required path parameters are still missing.": ui_text(locale, "required_path_parameters_missing"),
        "What happens next": ui_text(locale, "what_happens_next"),
        "Step ${index + 1}": "步骤 ${index + 1}",
        " Success: ": f" {ui_text(locale, 'success_prefix')}: ",
        " Error: ": f" {ui_text(locale, 'error_prefix')}: ",
        '"Continue"': json.dumps("继续", ensure_ascii=False),
        "Primary input": "主要输入",
        "Optional input": "可选输入",
        "Keep editing": "继续编辑",
    }
    for source, target in replacements.items():
        rendered = rendered.replace(source, target)
    return rendered


def build_generic_ui_page(surface: str) -> dict[str, Any]:
    route = sanitize_route_segment("", surface)
    locale = infer_ui_locale(surface)
    page_role = infer_ui_page_role(surface)
    user_inputs = [normalize_ui_input_spec({"field": "query", "required": False, "validation": "text"}, locale=locale)]
    copy = default_ui_page_copy(
        surface,
        page_role=page_role,
        actions=[{"action": f"Open {surface}", "on_success": "Show the current page data.", "on_error": "Keep the page open with recovery guidance."}],
        display_fields=[],
        user_inputs=user_inputs,
        locale=locale,
    )
    return {
        "page_id": route.replace("/", "-"),
        "page_title": surface,
        "route": f"/{route}",
        "page_role": page_role,
        "eyebrow": copy["eyebrow"],
        "subtitle": copy["subtitle"],
        "user_goal": copy["user_goal"],
        "primary_cta": copy["primary_cta"],
        "secondary_cta": copy["secondary_cta"],
        "sections": copy["sections"],
        "data_required": [],
        "data_presentation": ["table-or-list", "detail-panel", "status-banner"],
        "display_fields": [],
        "user_inputs": user_inputs,
        "field_source_mapping": [{"field": "query", "source": "user-input", "bind_to": "api-contract-to-be-finalized"}],
        "state_conditions": {
            "loading": "page data query in progress",
            "success": "primary data loaded and rendered",
            "empty": "query returned no records",
            "error": "request failed and retry is available",
        },
        "empty_state": copy["empty_state"],
        "success_state": copy["success_state"],
        "error_state": copy["error_state"],
        "actions_and_transitions": [
            {
                "action": copy["primary_cta"]["label"],
                "on_success": "Show the current page data and keep the next action visible.",
                "on_error": "Keep the page open with validation and recovery guidance.",
            }
        ],
    }


def load_ui_pages(*, output_dir: Path, primary_surfaces: list[str], ui_ia_contract_path: Path | None = None) -> list[dict[str, Any]]:
    contract_candidates = (
        [ui_ia_contract_path]
        if ui_ia_contract_path is not None
        else [
            output_dir / "prototype-fallback" / "ui-delivery-contract.json",
            output_dir / "prototype-fallback" / "ui-ia-contract.json",
        ]
    )
    for contract_path in contract_candidates:
        if contract_path is None or not contract_path.exists():
            continue
        try:
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        payload_locale = str(payload.get("locale") or "").strip() if isinstance(payload, dict) else ""
        payload_app_context = payload.get("app_context", {}) if isinstance(payload, dict) and isinstance(payload.get("app_context", {}), dict) else {}
        raw_pages = payload.get("pages", []) if isinstance(payload, dict) else []
        if isinstance(raw_pages, list):
            pages: list[dict[str, Any]] = []
            for raw_page in raw_pages:
                if not isinstance(raw_page, dict):
                    continue
                title = str(raw_page.get("page_title") or raw_page.get("title") or "").strip()
                if not title:
                    continue
                page_locale = infer_ui_locale(str(raw_page.get("locale") or payload_locale or "").strip(), title, str(raw_page.get("subtitle") or ""), str(raw_page.get("user_goal") or ""))
                route_segment = sanitize_route_segment(str(raw_page.get("route") or ""), title)
                user_inputs = [
                    normalize_ui_input_spec(item, locale=page_locale)
                    for item in raw_page.get("user_inputs", [])
                    if isinstance(item, dict) and str(item.get("field", "")).strip()
                ] or [normalize_ui_input_spec({"field": "query", "required": False, "validation": "text"}, locale=page_locale)]
                page_role = infer_ui_page_role(title, raw_page)
                display_fields = [
                    str(item).strip()
                    for item in raw_page.get("display_fields", [])
                    if str(item).strip()
                ]
                actions = [
                    {
                        **item,
                        "action": str(item.get("action") or "").strip(),
                        "on_success": str(item.get("on_success") or "").strip(),
                        "on_error": str(item.get("on_error") or "").strip(),
                    }
                    for item in raw_page.get("actions_and_transitions", [])
                    if isinstance(item, dict) and str(item.get("action", "")).strip()
                ]
                copy = default_ui_page_copy(
                    title,
                    page_role=page_role,
                    actions=actions,
                    display_fields=display_fields,
                    user_inputs=user_inputs,
                    locale=page_locale,
                )
                summary_cards = [
                    str(item).strip()
                    for item in raw_page.get("summary_cards", [])
                    if str(item).strip()
                ]
                detail_fields_in_order = [
                    str(item).strip()
                    for item in raw_page.get("detail_fields_in_order", [])
                    if str(item).strip()
                ]
                table_columns = [
                    str(item).strip()
                    for item in raw_page.get("table_columns", [])
                    if str(item).strip()
                ]
                filters_and_selectors = [
                    str(item).strip()
                    for item in raw_page.get("filters_and_selectors", [])
                    if str(item).strip()
                ]
                selector_fields = [
                    str(item.get("field") or "").strip()
                    for item in raw_page.get("field_source_mapping", [])
                    if isinstance(item, dict)
                    and str(item.get("source") or "").strip() == "workflow-context"
                    and str(item.get("field") or "").strip()
                ]
                user_inputs = augment_user_inputs_with_selector_fields(
                    user_inputs=user_inputs,
                    selector_fields=selector_fields,
                    actions=actions,
                    locale=page_locale,
                )
                copy = default_ui_page_copy(
                    title,
                    page_role=page_role,
                    actions=actions,
                    display_fields=display_fields,
                    user_inputs=user_inputs,
                    locale=page_locale,
                )
                required_status_messages = contract_list_value(raw_page.get("required_status_messages", []))
                submission_feedback = [
                    str(item).strip()
                    for item in raw_page.get("submission_feedback", [])
                    if str(item).strip()
                ]
                contract_sections = contract_driven_ui_sections(
                    surface=title,
                    page_role=page_role,
                    locale=page_locale,
                    display_fields=display_fields,
                    user_inputs=user_inputs,
                    summary_cards=summary_cards,
                    detail_fields_in_order=detail_fields_in_order,
                    table_columns=table_columns,
                    selector_fields=selector_fields,
                    filters_and_selectors=filters_and_selectors,
                    submission_feedback=submission_feedback,
                    required_status_messages=required_status_messages,
                )
                contract_presentation = contract_driven_data_presentation(
                    summary_cards=summary_cards,
                    detail_fields_in_order=detail_fields_in_order,
                    table_columns=table_columns,
                    filters_and_selectors=filters_and_selectors,
                    required_status_messages=required_status_messages,
                    submission_feedback=submission_feedback,
                )
                explicit_sections = [
                    section
                    for section in raw_page.get("sections", [])
                    if isinstance(section, dict) and str(section.get("section_id", "")).strip()
                ]
                resolved_sections = merge_preferred_ui_sections(
                    preferred_sections=explicit_sections,
                    synthesized_sections=contract_sections,
                ) or copy["sections"]
                raw_data_presentation = [
                    str(item).strip()
                    for item in raw_page.get("data_presentation", [])
                    if str(item).strip()
                ]
                resolved_data_presentation = list(dict.fromkeys(raw_data_presentation + contract_presentation)) or [
                    "table-or-list",
                    "detail-panel",
                    "status-banner",
                ]
                resolved_page_blueprint_type = infer_ui_page_blueprint_type(
                    title,
                    {
                        **raw_page,
                        "page_role": page_role,
                        "sections": resolved_sections,
                        "data_presentation": resolved_data_presentation,
                        "user_inputs": user_inputs,
                        "summary_cards": summary_cards,
                        "detail_fields_in_order": detail_fields_in_order,
                        "table_columns": table_columns,
                        "filters_and_selectors": filters_and_selectors,
                    },
                )
                audience_mode = str(raw_page.get("audience_mode") or "app").strip() or "app"
                page_contract_id = str(raw_page.get("page_id") or route_segment.replace("/", "-")).strip()
                canonical_page_id = str(raw_page.get("canonical_page_id") or page_contract_id).strip()
                surface_variant = str(raw_page.get("surface_variant") or page_contract_id).strip()
                session_role_source = str(raw_page.get("session_role_source") or ("login_session" if audience_mode == "app" else "")).strip()
                auth_entry_route = normalize_ui_route(raw_page.get("auth_entry_route") or "")
                auth_entry_label = str(raw_page.get("auth_entry_label") or "").strip()
                workspace_entry_roles = [
                    str(item).strip()
                    for item in raw_page.get("workspace_entry_roles", [])
                    if str(item).strip()
                ]
                navigation_scope = str(raw_page.get("navigation_scope") or ("workspace" if audience_mode == "app" else "hidden")).strip()
                default_reachability_mode = "hidden"
                if audience_mode == "app":
                    default_reachability_mode = "direct" if workspace_entry_roles or navigation_scope != "flow" else "flow"
                route_reachability_mode = str(raw_page.get("route_reachability_mode") or default_reachability_mode).strip()
                handoff_visibility = str(raw_page.get("handoff_visibility") or ("implicit_context" if raw_page.get("next_route_candidates") else "")).strip()
                forbidden_exposure = [
                    str(item).strip()
                    for item in raw_page.get("forbidden_exposure", [])
                    if str(item).strip()
                ]
                surface_contract_alerts = [
                    str(item).strip()
                    for item in raw_page.get("surface_contract_alerts", [])
                    if str(item).strip()
                ]
                pages.append(
                    {
                        "contract_source": str(raw_page.get("contract_source") or "").strip(),
                        "locale": page_locale,
                        "page_id": page_contract_id,
                        "page_title": title,
                        "route": f"/{route_segment}",
                        "page_blueprint_type": resolved_page_blueprint_type,
                        "canonical_page_id": canonical_page_id,
                        "surface_variant": surface_variant,
                        "audience_mode": audience_mode,
                        "session_role_source": session_role_source,
                        "auth_entry_route": auth_entry_route,
                        "auth_entry_label": auth_entry_label,
                        "workspace_entry_roles": workspace_entry_roles,
                        "route_reachability_mode": route_reachability_mode,
                        "navigation_scope": navigation_scope,
                        "handoff_visibility": handoff_visibility,
                        "forbidden_exposure": forbidden_exposure,
                        "surface_contract_alerts": surface_contract_alerts,
                        "page_role": page_role,
                        "allowed_roles": [
                            str(item).strip()
                            for item in raw_page.get("allowed_roles", [])
                            if str(item).strip()
                        ],
                        "read_only_vs_editable_by_role": raw_page.get("read_only_vs_editable_by_role", {})
                        if isinstance(raw_page.get("read_only_vs_editable_by_role", {}), dict)
                        else {},
                        "business_objects": [
                            str(item).strip()
                            for item in raw_page.get("business_objects", [])
                            if str(item).strip()
                        ],
                        "required_regions": [
                            str(item).strip()
                            for item in raw_page.get("required_regions", [])
                            if str(item).strip()
                        ],
                        "next_route_candidates": [
                            str(item).strip()
                            for item in raw_page.get("next_route_candidates", [])
                            if str(item).strip()
                        ],
                        "compiled_interactions": [
                            item for item in raw_page.get("compiled_interactions", []) if isinstance(item, dict)
                        ],
                        "app_context": payload_app_context,
                        "workflow_step": raw_page.get("workflow_step", {}) if isinstance(raw_page.get("workflow_step", {}), dict) else {},
                        "page_actor": [
                            str(item).strip()
                            for item in raw_page.get("page_actor", [])
                            if str(item).strip()
                        ],
                        "information_objects": [
                            str(item).strip()
                            for item in raw_page.get("information_objects", [])
                            if str(item).strip()
                        ],
                        "must_show_together": [
                            str(item).strip()
                            for item in raw_page.get("must_show_together", [])
                            if str(item).strip()
                        ],
                        "required_user_inputs_or_confirmations": [
                            str(item).strip()
                            for item in raw_page.get("required_user_inputs_or_confirmations", [])
                            if str(item).strip()
                        ],
                        "render_blocks_in_order": [
                            str(item).strip()
                            for item in raw_page.get("render_blocks_in_order", [])
                            if str(item).strip()
                        ],
                        "field_groups": [
                            str(item).strip()
                            for item in raw_page.get("field_groups", [])
                            if str(item).strip()
                        ],
                        "input_controls": [
                            str(item).strip()
                            for item in raw_page.get("input_controls", [])
                            if str(item).strip()
                        ],
                        "summary_cards": summary_cards,
                        "detail_fields_in_order": detail_fields_in_order,
                        "table_columns": table_columns,
                        "filters_and_selectors": filters_and_selectors,
                        "required_status_messages": required_status_messages,
                        "submission_feedback": submission_feedback,
                        "context_arrives_from": str(raw_page.get("context_arrives_from") or "").strip(),
                        "context_must_continue_to": str(raw_page.get("context_must_continue_to") or "").strip(),
                        "executor_brief": [
                            str(item).strip()
                            for item in raw_page.get("executor_brief", [])
                            if str(item).strip()
                        ],
                        "eyebrow": str(raw_page.get("eyebrow") or copy["eyebrow"]).strip(),
                        "subtitle": str(raw_page.get("subtitle") or copy["subtitle"]).strip(),
                        "user_goal": str(raw_page.get("user_goal") or copy["user_goal"]).strip(),
                        "primary_cta": (
                            raw_page.get("primary_cta", {})
                            if isinstance(raw_page.get("primary_cta", {}), dict) and raw_page.get("primary_cta")
                            else {
                                **copy["primary_cta"],
                                "label": str(raw_page.get("primary_cta_label") or copy["primary_cta"]["label"]).strip(),
                            }
                        ),
                        "secondary_cta": raw_page.get("secondary_cta", {}) if isinstance(raw_page.get("secondary_cta", {}), dict) else copy["secondary_cta"],
                        "sections": resolved_sections,
                        "data_required": raw_page.get("data_required", []) if isinstance(raw_page.get("data_required", []), list) else [],
                        "data_presentation": resolved_data_presentation,
                        "display_fields": display_fields,
                        "user_inputs": user_inputs,
                        "field_source_mapping": [
                            item
                            for item in raw_page.get("field_source_mapping", [])
                            if isinstance(item, dict) and str(item.get("field", "")).strip()
                        ],
                        "state_conditions": raw_page.get("state_conditions", {})
                        if isinstance(raw_page.get("state_conditions", {}), dict)
                        else {},
                        "actions_and_transitions": actions or [
                            {
                                "action": copy["primary_cta"]["label"],
                                "on_success": "让最新状态继续显示在当前页面上。" if is_zh_locale(page_locale) else "Show the latest state on the current page.",
                                "on_error": "保留当前页面并展示恢复指引。" if is_zh_locale(page_locale) else "Keep the page open with recovery guidance.",
                            }
                        ],
                        "empty_state": raw_page.get("empty_state", {}) if isinstance(raw_page.get("empty_state", {}), dict) else copy["empty_state"],
                        "success_state": raw_page.get("success_state", {}) if isinstance(raw_page.get("success_state", {}), dict) else copy["success_state"],
                        "error_state": raw_page.get("error_state", {}) if isinstance(raw_page.get("error_state", {}), dict) else copy["error_state"],
                    }
                )
            if pages:
                return pages
    surfaces = primary_surfaces or [
        "Overview dashboard",
        "Primary record list",
        "Record detail view",
        "Action workspace",
    ]
    return [build_generic_ui_page(surface) for surface in surfaces]


def ui_page_route_segment(page_contract: dict[str, Any], fallback_surface: str) -> str:
    return sanitize_route_segment(str(page_contract.get("route") or ""), fallback_surface)


def load_compiled_bindings(*, output_dir: Path, ui_ia_contract_path: Path | None = None) -> list[dict[str, Any]]:
    contract_candidates = (
        [ui_ia_contract_path]
        if ui_ia_contract_path is not None
        else [
            output_dir / "prototype-fallback" / "ui-ia-contract.json",
            output_dir / "prototype-fallback" / "ui-delivery-contract.json",
        ]
    )
    for contract_path in contract_candidates:
        if contract_path is None or not contract_path.exists():
            continue
        try:
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        raw_rows = payload.get("compiled_bindings", []) if isinstance(payload, dict) else []
        if isinstance(raw_rows, list) and raw_rows:
            return [row for row in raw_rows if isinstance(row, dict)]
    return []


def ui_page_interest_tokens(surface: str, page_contract: dict[str, Any] | None = None) -> set[str]:
    haystacks = [surface]
    if page_contract:
        haystacks.append(str(page_contract.get("route") or ""))
        haystacks.extend(str(item) for item in page_contract.get("data_presentation", []) if str(item).strip())
        for item in page_contract.get("data_required", []):
            if isinstance(item, dict):
                haystacks.append(
                    " ".join(
                        [
                            str(item.get("method", "")).strip(),
                            str(item.get("path", "")).strip(),
                            str(item.get("purpose", "")).strip(),
                        ]
                    )
                )
        for item in page_contract.get("user_inputs", []):
            if isinstance(item, dict):
                haystacks.append(
                    " ".join(
                        [
                            str(item.get("field", "")).strip(),
                            str(item.get("validation", "")).strip(),
                        ]
                    )
                )
        for item in page_contract.get("actions_and_transitions", []):
            if isinstance(item, dict):
                haystacks.append(
                    " ".join(
                        [
                            str(item.get("action", "")).strip(),
                            str(item.get("on_success", "")).strip(),
                            str(item.get("on_error", "")).strip(),
                        ]
                    )
                )
    return expand_scope_term_equivalents(scope_tokens(" ".join(haystacks)))


def relative_api_import(route_segment: str) -> str:
    depth = max(1, len([part for part in route_segment.split("/") if part.strip()]))
    return "../" * depth + "api"


def ui_page_data_focus(page_contract: dict[str, Any]) -> str:
    user_goal = str(page_contract.get("user_goal") or "").strip()
    if user_goal:
        return user_goal
    data_required = page_contract.get("data_required", [])
    if isinstance(data_required, list):
        for item in data_required:
            if not isinstance(item, dict):
                continue
            purpose = str(item.get("purpose", "")).strip()
            if purpose:
                return purpose
            path = str(item.get("path", "")).strip()
            if path:
                return path
    presentation = [str(item).strip() for item in page_contract.get("data_presentation", []) if str(item).strip()]
    if presentation:
        return presentation[0]
    return "frozen IA data requirements"


def ui_page_action_focus(page_contract: dict[str, Any]) -> str:
    primary_cta = page_contract.get("primary_cta", {})
    if isinstance(primary_cta, dict) and str(primary_cta.get("label") or "").strip():
        return str(primary_cta.get("label") or "").strip()
    actions = page_contract.get("actions_and_transitions", [])
    if isinstance(actions, list):
        for item in actions:
            if isinstance(item, dict) and str(item.get("action", "")).strip():
                return str(item.get("action", "")).strip()
    return "review linked transitions"


def contract_text_value(raw: Any) -> str:
    if isinstance(raw, dict):
        text = str(raw.get("text") or "").strip()
        if text:
            return text
    return str(raw or "").strip()


def contract_list_value(raw: Any) -> list[str]:
    if isinstance(raw, dict):
        items = raw.get("items", [])
        if isinstance(items, list):
            return [str(item).strip() for item in items if str(item).strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def normalize_ui_role_name(value: Any, locale: str | None = None) -> str:
    candidate = re.sub(r"\s+", " ", str(value or "").strip().strip("`")).strip()
    if not candidate or locale is None:
        return candidate
    return normalize_role_display_name(candidate, locale) or candidate


def ordered_ui_roles(*groups: Any, locale: str | None = None) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        items = group if isinstance(group, list) else [group]
        for item in items:
            role = normalize_ui_role_name(item, locale=locale)
            if not role:
                continue
            key = role.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(role)
    return ordered


def split_ui_role_candidates(raw: Any, locale: str | None = None) -> list[str]:
    text = normalize_ui_role_name(raw, locale=locale).strip("[]")
    if not text or text.lower() in {"—", "-", "none", "n/a", "not_applicable"}:
        return []
    parts = [
        part.strip()
        for part in re.split(r"\s*(?:,|/|;|\||、|，|\band\b|\bor\b)\s*", text, flags=re.IGNORECASE)
        if part.strip()
    ]
    return ordered_ui_roles(parts or [text], locale=locale)


def extract_ui_policy_roles(raw: Any, locale: str | None = None) -> list[str]:
    text = normalize_ui_role_name(raw, locale=locale)
    if not text or text.lower() in {"—", "-", "none", "n/a", "not_applicable"}:
        return []
    bracketed: list[str] = []
    for match in re.findall(r"\[([^\]]+)\]", text):
        bracketed.extend(split_ui_role_candidates(match, locale=locale))
    if bracketed:
        return ordered_ui_roles(bracketed, locale=locale)
    simplified = re.sub(r"\b(?:role|roles|allow|allows|allowed|require|requires|required|policy|visible|visibility)\b", " ", text, flags=re.IGNORECASE)
    simplified = re.sub(r"\b(?:in|is|are|only|any|of|with|for|current|user|actor)\b", " ", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\s+", " ", simplified).strip(" -:")
    return split_ui_role_candidates(simplified, locale=locale)


def ui_page_allowed_roles(page_contract: dict[str, Any], fallback_roles: list[str], *, locale: str | None = None) -> list[str]:
    page_locale = str(page_contract.get("locale") or "").strip() or locale
    explicit = [
        normalize_ui_role_name(item, locale=page_locale)
        for item in page_contract.get("allowed_roles", [])
        if normalize_ui_role_name(item, locale=page_locale)
    ]
    policy_roles: list[str] = []
    for interaction in page_contract.get("compiled_interactions", []):
        if not isinstance(interaction, dict):
            continue
        policy_roles.extend(
            extract_ui_policy_roles(interaction.get("rbac_policy") or interaction.get("visibility_rule") or "", locale=page_locale)
        )
    page_actor_roles = [
        normalize_ui_role_name(item, locale=page_locale)
        for item in page_contract.get("page_actor", [])
        if normalize_ui_role_name(item, locale=page_locale)
    ]
    inferred_roles = ordered_ui_roles(explicit, policy_roles, page_actor_roles, locale=page_locale)
    if inferred_roles:
        return inferred_roles
    return ordered_ui_roles(fallback_roles[:1], locale=page_locale)


def ui_page_has_mutating_action(page_contract: dict[str, Any]) -> bool:
    for action in page_contract.get("actions_and_transitions", []):
        if not isinstance(action, dict):
            continue
        method = str((action.get("api_binding") or {}).get("method") or "").strip().upper()
        if method and method != "GET":
            return True
    for interaction in page_contract.get("compiled_interactions", []):
        if not isinstance(interaction, dict):
            continue
        trigger_kind = str(interaction.get("trigger_kind") or "").strip()
        method = str(interaction.get("http_method") or "").strip().upper()
        if trigger_kind and trigger_kind != "page_load" and method != "GET":
            return True
    return False


def ui_page_role_access_policy(page_contract: dict[str, Any], allowed_roles: list[str], *, locale: str | None = None) -> dict[str, Any]:
    page_locale = str(page_contract.get("locale") or "").strip() or locale
    editable_roles: list[str] = []
    for interaction in page_contract.get("compiled_interactions", []):
        if not isinstance(interaction, dict):
            continue
        trigger_kind = str(interaction.get("trigger_kind") or "").strip()
        method = str(interaction.get("http_method") or "").strip().upper()
        if trigger_kind == "page_load" or method == "GET":
            continue
        editable_roles = ordered_ui_roles(
            editable_roles,
            extract_ui_policy_roles(interaction.get("rbac_policy") or interaction.get("visibility_rule") or "", locale=page_locale),
            locale=page_locale,
        )
    has_mutating_action = ui_page_has_mutating_action(page_contract)
    if has_mutating_action and not editable_roles:
        editable_roles = allowed_roles[:]
    read_only_roles = [role for role in allowed_roles if role not in editable_roles]
    if not has_mutating_action and allowed_roles:
        read_only_roles = allowed_roles[:]
    return {
        "allowed_roles": allowed_roles,
        "editable_roles": editable_roles,
        "read_only_roles": read_only_roles,
        "default_access": "editable" if editable_roles else "read-only",
    }


def derive_ui_role_session_contract(ui_pages: list[dict[str, Any]], raw_context: dict[str, Any]) -> dict[str, Any]:
    role_locale = str(raw_context.get("locale") or "").strip() or next(
        (str(page.get("locale") or "").strip() for page in ui_pages if str(page.get("locale") or "").strip()),
        "en",
    )
    fallback_roles = ordered_ui_roles(
        [str(item).strip() for item in raw_context.get("supporting_roles", []) if str(item).strip()],
        [str(raw_context.get("current_session_role") or "").strip()],
        locale=role_locale,
    )
    route_policies: dict[str, dict[str, Any]] = {}
    role_routes: dict[str, list[str]] = {}
    role_page_ids: dict[str, list[str]] = {}
    role_page_titles: dict[str, list[str]] = {}
    role_editable_routes: dict[str, list[str]] = {}
    explicit_entry_routes: dict[str, str] = {}
    session_role_candidates: list[str] = []
    derived_auth_entry_route = ""
    derived_auth_entry_label = ""
    default_route = str(ui_pages[0].get("route") or "").strip() if ui_pages else "/"

    for page in ui_pages:
        route = str(page.get("route") or "").strip() or "/"
        allowed_roles = ui_page_allowed_roles(page, fallback_roles=fallback_roles, locale=role_locale)
        page["allowed_roles"] = allowed_roles
        page_access = ui_page_role_access_policy(page, allowed_roles, locale=role_locale)
        if isinstance(page.get("read_only_vs_editable_by_role"), dict):
            explicit_policy = page.get("read_only_vs_editable_by_role", {})
            page_access["editable_roles"] = ordered_ui_roles(explicit_policy.get("editable_roles", []), page_access["editable_roles"], locale=role_locale)
            page_access["read_only_roles"] = ordered_ui_roles(explicit_policy.get("read_only_roles", []), page_access["read_only_roles"], locale=role_locale)
            page_access["default_access"] = str(explicit_policy.get("default_access") or page_access["default_access"]).strip() or page_access["default_access"]
        page["read_only_vs_editable_by_role"] = {
            "editable_roles": page_access["editable_roles"],
            "read_only_roles": page_access["read_only_roles"],
            "default_access": page_access["default_access"],
        }
        audience_mode = str(page.get("audience_mode") or "app").strip().lower()
        session_role_source = str(page.get("session_role_source") or "").strip().lower()
        workspace_entry_roles = ui_page_workspace_entry_roles(page, locale=role_locale)
        page["workspace_entry_roles"] = workspace_entry_roles
        navigation_scope = ui_page_navigation_scope(page)
        page["navigation_scope"] = navigation_scope
        route_reachability_mode = ui_page_route_reachability_mode(page, locale=role_locale)
        page["route_reachability_mode"] = route_reachability_mode
        if audience_mode in {"", "app"} and session_role_source == "login_session":
            session_role_candidates = ordered_ui_roles(
                session_role_candidates,
                page_access["editable_roles"],
                allowed_roles[:1],
                locale=role_locale,
            )
            page_auth_entry_route = normalize_ui_route(page.get("auth_entry_route") or "")
            page_auth_entry_label = str(page.get("auth_entry_label") or "").strip()
            if page_auth_entry_route and not derived_auth_entry_route:
                derived_auth_entry_route = page_auth_entry_route
            if page_auth_entry_label and not derived_auth_entry_label:
                derived_auth_entry_label = page_auth_entry_label
        route_policies[route] = {
            "allowed_roles": allowed_roles,
            "editable_roles": page_access["editable_roles"],
            "read_only_roles": page_access["read_only_roles"],
            "workspace_entry_roles": workspace_entry_roles,
            "route_reachability_mode": route_reachability_mode,
            "navigation_scope": navigation_scope,
            "denied_behavior": "redirect-to-role-entry",
        }
        for role in workspace_entry_roles:
            if role in allowed_roles and role not in explicit_entry_routes:
                explicit_entry_routes[role] = route
        for role in allowed_roles:
            role_routes.setdefault(role, [])
            if route not in role_routes[role]:
                role_routes[role].append(route)
            page_id = str(page.get("page_id") or "").strip()
            page_title = str(page.get("page_title") or "").strip()
            if page_id:
                role_page_ids.setdefault(role, [])
                if page_id not in role_page_ids[role]:
                    role_page_ids[role].append(page_id)
            if page_title:
                role_page_titles.setdefault(role, [])
                if page_title not in role_page_titles[role]:
                    role_page_titles[role].append(page_title)
        for role in page_access["editable_roles"]:
            role_editable_routes.setdefault(role, [])
            if route not in role_editable_routes[role]:
                role_editable_routes[role].append(route)

    ordered_roles = ordered_ui_roles(list(role_routes.keys()), locale=role_locale) if role_routes else ordered_ui_roles(fallback_roles, locale=role_locale)
    derived_entry_routes: dict[str, str] = {}
    derived_workspaces: list[dict[str, Any]] = []
    for role in ordered_roles:
        accessible_routes = role_routes.get(role, [])
        editable_routes = role_editable_routes.get(role, [])
        explicit_entry_route = explicit_entry_routes.get(role, "")
        entry_route = explicit_entry_route or (editable_routes[0] if editable_routes else (accessible_routes[0] if accessible_routes else default_route))
        ordered_accessible_routes = accessible_routes[:]
        if entry_route and entry_route in ordered_accessible_routes:
            ordered_accessible_routes = [entry_route, *[route for route in ordered_accessible_routes if route != entry_route]]
        derived_entry_routes[role] = entry_route
        derived_workspaces.append(
            {
                "role": role,
                "entry_route": entry_route,
                "page_routes": ordered_accessible_routes,
                "page_ids": role_page_ids.get(role, []),
                "page_titles": role_page_titles.get(role, []),
                "default_access": "editable" if editable_routes else "read-only",
            }
        )

    raw_entry_routes = raw_context.get("role_scoped_entry_routes", {}) if isinstance(raw_context.get("role_scoped_entry_routes", {}), dict) else {}
    role_scoped_entry_routes = {
        role: str(raw_entry_routes.get(role) or derived_entry_routes.get(role) or default_route).strip() or default_route
        for role in ordered_roles
    }
    raw_current_role = normalize_ui_role_name(raw_context.get("current_session_role") or "", locale=role_locale)
    login_session_roles = [role for role in session_role_candidates if role in ordered_roles]
    login_session_required = bool(login_session_roles)
    derived_session_role = next(iter(login_session_roles), "")
    explicit_session_bootstrap_required = len(login_session_roles) > 1 and not raw_current_role
    current_session_role = (
        raw_current_role
        if raw_current_role in ordered_roles
        else ("" if login_session_required else (derived_session_role or (ordered_roles[0] if ordered_roles else "")))
    )
    multi_role_bootstrap_route = role_scoped_entry_routes.get(current_session_role) or default_route
    raw_route_guard = raw_context.get("route_guard_policy", {}) if isinstance(raw_context.get("route_guard_policy", {}), dict) else {}
    auth_entry_route = normalize_ui_route(raw_route_guard.get("auth_entry_route") or derived_auth_entry_route)
    if login_session_required and not auth_entry_route:
        auth_entry_route = "/auth/login"
    default_auth_entry_label = "登录" if is_zh_locale(role_locale) else "Sign in"
    auth_entry_label = str(raw_route_guard.get("auth_entry_label") or derived_auth_entry_label or (default_auth_entry_label if auth_entry_route else "")).strip()
    default_route_guard_denied_behavior = "redirect-to-login" if auth_entry_route else "redirect-to-role-entry"
    effective_route_guard_denied_behavior = str(raw_route_guard.get("denied_behavior") or default_route_guard_denied_behavior).strip() or default_route_guard_denied_behavior
    raw_route_map = raw_route_guard.get("routes", {}) if isinstance(raw_route_guard.get("routes", {}), dict) else {}
    merged_route_policies: dict[str, dict[str, Any]] = {}
    for route, policy in route_policies.items():
        raw_policy = raw_route_map.get(route) if isinstance(raw_route_map.get(route), dict) else {}
        if isinstance(raw_policy, dict):
            merged_policy = {**policy, **raw_policy}
            for list_field in ("allowed_roles", "editable_roles", "read_only_roles", "workspace_entry_roles"):
                if isinstance(raw_policy.get(list_field), list):
                    merged_policy[list_field] = ordered_ui_roles(raw_policy.get(list_field, []), locale=role_locale)
            merged_policy["navigation_scope"] = ui_page_navigation_scope(merged_policy)
            merged_policy["route_reachability_mode"] = ui_page_route_reachability_mode(merged_policy, locale=role_locale)
            merged_policy["denied_behavior"] = str(raw_policy.get("denied_behavior") or effective_route_guard_denied_behavior).strip() or effective_route_guard_denied_behavior
            merged_route_policies[route] = merged_policy
        else:
            merged_route_policies[route] = {**policy, "denied_behavior": effective_route_guard_denied_behavior}
    raw_workspace_rows = raw_context.get("available_workspaces", []) if isinstance(raw_context.get("available_workspaces", []), list) else []
    workspace_by_role = {
        normalize_ui_role_name(item.get("role") or "", locale=role_locale): item
        for item in raw_workspace_rows
        if isinstance(item, dict) and normalize_ui_role_name(item.get("role") or "", locale=role_locale)
    }
    available_workspaces: list[dict[str, Any]] = []
    for workspace in derived_workspaces:
        role = workspace["role"]
        raw_workspace = workspace_by_role.get(role, {})
        available_workspaces.append(
            {
                "role": role,
                "entry_route": str(raw_workspace.get("entry_route") or role_scoped_entry_routes.get(role) or workspace["entry_route"]).strip() or workspace["entry_route"],
                "page_routes": [str(item).strip() for item in raw_workspace.get("page_routes", workspace["page_routes"]) if str(item).strip()],
                "page_ids": [str(item).strip() for item in raw_workspace.get("page_ids", workspace["page_ids"]) if str(item).strip()],
                "page_titles": [str(item).strip() for item in raw_workspace.get("page_titles", workspace["page_titles"]) if str(item).strip()],
                "default_access": str(raw_workspace.get("default_access") or workspace["default_access"]).strip() or workspace["default_access"],
            }
        )
    auth_test_accounts: list[dict[str, str]] = []
    if auth_entry_route:
        seen_email_locals: set[str] = set()
        for index, workspace in enumerate(available_workspaces, start=1):
            role = str(workspace.get("role") or "").strip()
            fallback_seed = role or f"workspace-{index}"
            route_seed = sanitize_route_segment(str(workspace.get("entry_route") or ""), fallback_seed).replace("/", "-").strip("-")
            email_local = route_seed or f"workspace-{index}"
            base_email_local = email_local
            dedupe_index = 2
            while email_local in seen_email_locals:
                email_local = f"{base_email_local}-{dedupe_index}"
                dedupe_index += 1
            seen_email_locals.add(email_local)
            auth_test_accounts.append(
                {
                    "role": role,
                    "email": f"{email_local}@example.test",
                    "password": "Phase3Pass!",
                }
            )

    raw_read_only_map = raw_context.get("read_only_vs_editable_by_role", {}) if isinstance(raw_context.get("read_only_vs_editable_by_role", {}), dict) else {}
    read_only_vs_editable_by_role = {
        route: (raw_read_only_map.get(route) if isinstance(raw_read_only_map.get(route), dict) else {
            "editable_roles": policy.get("editable_roles", []),
            "read_only_roles": policy.get("read_only_roles", []),
        })
        for route, policy in merged_route_policies.items()
    }
    return {
        "current_session_role": current_session_role,
        "available_workspaces": available_workspaces,
        "auth_test_accounts": auth_test_accounts,
        "role_scoped_entry_routes": role_scoped_entry_routes,
        "route_guard_policy": {
            "mode": str(raw_route_guard.get("mode") or ("role-scoped-workspaces" if len(ordered_roles) > 1 else "single-role-workspace")).strip(),
            "workspace_switch_required": bool(raw_route_guard.get("workspace_switch_required")) if "workspace_switch_required" in raw_route_guard else explicit_session_bootstrap_required,
            "default_route": str(raw_route_guard.get("default_route") or role_scoped_entry_routes.get(current_session_role) or multi_role_bootstrap_route).strip() or multi_role_bootstrap_route,
            "denied_behavior": effective_route_guard_denied_behavior,
            "auth_entry_route": auth_entry_route,
            "auth_entry_label": auth_entry_label,
            "routes": merged_route_policies,
        },
        "read_only_vs_editable_by_role": read_only_vs_editable_by_role,
    }


def normalize_ui_route(value: Any) -> str:
    candidate = str(value or "").replace("`", "").strip()
    if not candidate or candidate.lower() in {"—", "-", "none", "n/a"}:
        return ""
    return candidate if candidate.startswith("/") else f"/{route_slug(candidate)}"


def ordered_ui_route_values(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        route = normalize_ui_route(value)
        if not route:
            continue
        key = route.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(route)
    return ordered


def ui_page_navigation_routes(page_contract: dict[str, Any]) -> list[str]:
    routes: list[Any] = []
    navigation = page_contract.get("navigation") if isinstance(page_contract.get("navigation"), dict) else {}
    next_route = normalize_ui_route(navigation.get("next_route") or "")
    if next_route:
        routes.append(next_route)
    routes.extend(page_contract.get("next_route_candidates", []))
    return ordered_ui_route_values(routes)


def ui_page_workspace_entry_roles(page_contract: dict[str, Any], *, locale: str) -> list[str]:
    return ordered_ui_roles(
        [str(item).strip() for item in page_contract.get("workspace_entry_roles", []) if str(item).strip()],
        locale=locale,
    )


def ui_page_navigation_scope(page_contract: dict[str, Any]) -> str:
    explicit_scope = str(page_contract.get("navigation_scope") or "").strip().lower()
    if explicit_scope in {"workspace", "flow", "hidden"}:
        return explicit_scope
    audience_mode = str(page_contract.get("audience_mode") or "app").strip().lower()
    if audience_mode != "app":
        return "hidden"
    return "flow" if ui_page_navigation_routes(page_contract) else "workspace"


def ui_page_route_reachability_mode(page_contract: dict[str, Any], *, locale: str) -> str:
    explicit_mode = str(page_contract.get("route_reachability_mode") or "").strip().lower()
    if explicit_mode in {"direct", "flow", "hidden"}:
        return explicit_mode
    audience_mode = str(page_contract.get("audience_mode") or "app").strip().lower()
    navigation_scope = ui_page_navigation_scope(page_contract)
    workspace_entry_roles = ui_page_workspace_entry_roles(page_contract, locale=locale)
    if audience_mode != "app":
        return "hidden"
    if workspace_entry_roles:
        return "direct"
    return "flow" if navigation_scope == "flow" else "direct"


def derive_ui_workflow_navigation_contract(
    ui_pages: list[dict[str, Any]],
    role_shell: dict[str, Any],
    *,
    locale: str,
) -> dict[str, Any]:
    zh = is_zh_locale(locale)
    route_guard_policy = role_shell.get("route_guard_policy", {}) if isinstance(role_shell.get("route_guard_policy", {}), dict) else {}
    route_guard_routes = route_guard_policy.get("routes", {}) if isinstance(route_guard_policy.get("routes", {}), dict) else {}
    default_denied_behavior = str(route_guard_policy.get("denied_behavior") or "redirect-to-role-entry").strip() or "redirect-to-role-entry"
    page_by_route: dict[str, dict[str, Any]] = {}
    title_by_route: dict[str, str] = {}
    allowed_roles_by_route: dict[str, list[str]] = {}
    route_modes_by_route: dict[str, str] = {}
    ordered_routes: list[str] = []
    for index, page in enumerate(ui_pages, start=1):
        title = str(page.get("page_title") or f"Surface {index}").strip()
        route = normalize_ui_route(page.get("route") or f"/{ui_page_route_segment(page, title)}")
        if not route:
            continue
        page_by_route[route] = page
        title_by_route[route] = title or route
        ordered_routes.append(route)
        allowed_roles_by_route[route] = [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()]
        route_modes_by_route[route] = ui_page_route_reachability_mode(page, locale=locale)
    global_previous: dict[str, str] = {}
    global_next: dict[str, str] = {}
    for index, route in enumerate(ordered_routes):
        global_previous[route] = ordered_routes[index - 1] if index > 0 else ""
        global_next[route] = ordered_routes[index + 1] if index + 1 < len(ordered_routes) else ""

    global_nav_items = [{
        "route": "/",
        "label": ui_text(locale, "workspace_menu"),
        "kind": "workspace-home",
    }]
    local_nav_items: dict[str, list[dict[str, Any]]] = {}
    contextual_nav_items: dict[str, dict[str, Any]] = {}
    next_step_cta: dict[str, dict[str, Any]] = {}
    placemaking_markers: dict[str, dict[str, Any]] = {}
    reachability_roles: dict[str, dict[str, Any]] = {}
    reachability_routes: dict[str, dict[str, Any]] = {}
    has_progression = False

    role_entry_routes = role_shell.get("role_scoped_entry_routes", {}) if isinstance(role_shell.get("role_scoped_entry_routes", {}), dict) else {}
    for workspace in role_shell.get("available_workspaces", []):
        if not isinstance(workspace, dict):
            continue
        role = normalize_ui_role_name(workspace.get("role") or "", locale=locale)
        workspace_routes = [
            route
            for route in ordered_ui_route_values(workspace.get("page_routes", []))
            if route in page_by_route
        ]
        if not role or not workspace_routes:
            continue
        entry_route = normalize_ui_route(
            role_entry_routes.get(role)
            or workspace.get("entry_route")
            or workspace_routes[0]
        )
        if entry_route not in workspace_routes:
            entry_route = workspace_routes[0]
        direct_routes = ordered_ui_route_values(
            [entry_route, *[route for route in workspace_routes if route_modes_by_route.get(route, "direct") == "direct"]]
        )
        flow_routes = [
            route
            for route in workspace_routes
            if route_modes_by_route.get(route, "direct") == "flow" and route != entry_route
        ]
        hidden_routes = [
            route
            for route in workspace_routes
            if route_modes_by_route.get(route, "direct") == "hidden" and route != entry_route
        ]
        ordered_role_routes = ordered_ui_route_values(
            [
                entry_route,
                *[route for route in direct_routes if route != entry_route],
                *flow_routes,
                *hidden_routes,
            ]
        )
        progression_routes = ordered_ui_route_values([entry_route, *flow_routes])
        default_reachable_routes = direct_routes
        reachability_roles[role] = {
            "entry_route": entry_route,
            "ordered_routes": ordered_role_routes,
            "direct_routes": direct_routes,
            "flow_routes": flow_routes,
            "default_reachable_routes": default_reachable_routes,
            "unlock_rule": "flow-routes-require-unlock",
        }
        if flow_routes:
            has_progression = True
        local_nav_items[role] = []
        total_steps = len(progression_routes)
        for route in ordered_role_routes:
            page = page_by_route[route]
            title = title_by_route.get(route, route)
            reachability_mode = route_modes_by_route.get(route, "direct")
            progression_index = progression_routes.index(route) if route in progression_routes else -1
            local_previous_route = progression_routes[progression_index - 1] if progression_index > 0 else ""
            local_next_route = progression_routes[progression_index + 1] if progression_index >= 0 and progression_index + 1 < total_steps else ""
            explicit_previous_candidate = normalize_ui_route((page.get("navigation") or {}).get("previous_route") if isinstance(page.get("navigation"), dict) else "")
            explicit_next_candidates = ui_page_navigation_routes(page)
            explicit_previous = ""
            if explicit_previous_candidate and explicit_previous_candidate in ordered_role_routes:
                explicit_previous = explicit_previous_candidate
            elif progression_index >= 0 and local_previous_route:
                explicit_previous = local_previous_route
            elif explicit_previous_candidate and (
                not allowed_roles_by_route.get(explicit_previous_candidate)
                or role in allowed_roles_by_route.get(explicit_previous_candidate, [])
            ):
                explicit_previous = explicit_previous_candidate

            next_route = ""
            for candidate in explicit_next_candidates:
                if candidate and candidate in ordered_role_routes and candidate != route:
                    next_route = candidate
                    break
            if not next_route and progression_index >= 0 and local_next_route:
                next_route = local_next_route
            if not next_route:
                for candidate in explicit_next_candidates:
                    if candidate and (
                        not allowed_roles_by_route.get(candidate)
                        or role in allowed_roles_by_route.get(candidate, [])
                    ):
                        next_route = candidate
                        break

            handoff_route = ""
            if not next_route:
                for candidate in explicit_next_candidates:
                    if candidate and candidate != route:
                        handoff_route = candidate
                        break
            fallback_cross_role_next = global_next.get(route, "")
            if not handoff_route and fallback_cross_role_next and fallback_cross_role_next != route:
                handoff_route = fallback_cross_role_next
            step_text = ""
            step_index = None
            if progression_index >= 0 and total_steps > 1:
                step_text = str((page.get("workflow_step", {}) or {}).get("step") or "").strip() or (
                    f"第 {progression_index + 1}/{total_steps} 步" if zh else f"Step {progression_index + 1} of {total_steps}"
                )
                step_index = progression_index + 1
            locked_reason = ""
            if reachability_mode == "flow" and local_previous_route:
                locked_reason = (
                    "请先完成上一步，当前步骤才会解锁。" if zh else "Complete the previous step before this step unlocks."
                )
            if reachability_mode != "hidden":
                nav_item = {
                    "route": route,
                    "label": title,
                    "step_label": step_text,
                    "unlocked_by_default": route in default_reachable_routes,
                    "locked_reason": locked_reason,
                }
                if step_index:
                    nav_item["step_index"] = step_index
                    nav_item["total_steps"] = total_steps
                local_nav_items[role].append(nav_item)
            contextual_nav_items.setdefault(route, {"by_role": {}})
            contextual_nav_items[route]["by_role"][role] = {
                "previous_route": explicit_previous,
                "next_route": next_route,
                "previous_label": title_by_route.get(explicit_previous, ""),
                "next_label": title_by_route.get(next_route, ""),
                "current_label": title,
            }
            next_kind = "terminal"
            target_route = next_route
            target_label = title_by_route.get(next_route, "")
            target_role = role
            if next_route:
                next_kind = "same-role"
                label = (
                    f"继续到 {title_by_route.get(next_route, next_route)}"
                    if zh
                    else f"Continue to {title_by_route.get(next_route, next_route)}"
                )
            elif handoff_route:
                handoff_roles = allowed_roles_by_route.get(handoff_route, [])
                handoff_visibility = str(page.get("handoff_visibility") or "").strip().lower()
                target_role = role if not handoff_roles or role in handoff_roles else handoff_roles[0]
                next_kind = "handoff-summary"
                target_route = ""
                target_label = ""
                label = ""
                if handoff_visibility != "implicit_context":
                    label = (
                        "提交后会交接到下一个工作区。"
                        if zh
                        else "Submission hands off to the next workspace."
                    )
            else:
                label = ""
            next_step_cta.setdefault(route, {"by_role": {}})
            next_step_cta[route]["by_role"][role] = {
                "kind": next_kind,
                "target_route": target_route,
                "target_role": target_role,
                "target_label": target_label,
                "label": label,
            }
            placemaking_markers.setdefault(route, {"by_role": {}})
            placemaking_marker = {
                "step_label": step_text,
                "current_label": title,
                "previous_label": title_by_route.get(explicit_previous, ""),
                "next_label": title_by_route.get(next_route, ""),
            }
            if step_index:
                placemaking_marker["step_index"] = step_index
                placemaking_marker["total_steps"] = total_steps
            placemaking_markers[route]["by_role"][role] = placemaking_marker
            reachability_routes.setdefault(
                route,
                {
                    "allowed_roles": allowed_roles_by_route.get(route, []),
                    "by_role": {},
                    "denied_behavior": str(
                        ((route_guard_routes.get(route) if isinstance(route_guard_routes.get(route), dict) else {}) or {}).get("denied_behavior")
                        or default_denied_behavior
                    ).strip() or default_denied_behavior,
                },
            )
            role_reachability = {
                "entry_route": entry_route,
                "reachability_mode": reachability_mode,
                "reachable_by_default": route in default_reachable_routes,
                "reachable_after_route": local_previous_route if reachability_mode == "flow" else "",
                "next_route": next_route,
                "locked_reason": locked_reason,
            }
            if step_index:
                role_reachability["step_index"] = step_index
                role_reachability["total_steps"] = total_steps
            reachability_routes[route]["by_role"][role] = role_reachability

    return {
        "primary_navigation_mode": "workflow-progression" if has_progression else "workspace-entry-only",
        "global_nav_items": global_nav_items,
        "local_nav_items": local_nav_items,
        "contextual_nav_items": contextual_nav_items,
        "next_step_cta": next_step_cta,
        "route_reachability_policy": {
            "mode": "entry-direct-flow",
            "denied_behavior": default_denied_behavior,
            "roles": reachability_roles,
            "routes": reachability_routes,
        },
        "placemaking_markers": placemaking_markers,
    }


def ui_app_context(ui_pages: list[dict[str, Any]]) -> dict[str, Any]:
    raw = {}
    if ui_pages:
        candidate = ui_pages[0].get("app_context", {})
        if isinstance(candidate, dict):
            raw = candidate
    locale = infer_ui_locale(
        *[
            " ".join(
                [
                    str(page.get("locale") or ""),
                    str(page.get("page_title") or ""),
                    str(page.get("subtitle") or ""),
                    str(page.get("user_goal") or ""),
                ]
            )
            for page in ui_pages
        ]
    )
    product_name = str(raw.get("product_name") or "").strip() or (
        "Runnable business application" if not is_zh_locale(locale) else "可操作业务应用"
    )
    product_heading = str(raw.get("product_heading") or "").strip() or (
        f"{product_name} workbench" if not is_zh_locale(locale) else f"{product_name} 业务工作台"
    )
    supporting_roles = [
        str(item).strip()
        for item in raw.get("supporting_roles", [])
        if str(item).strip()
    ]
    workflow_backbone = [
        item
        for item in raw.get("workflow_backbone", [])
        if isinstance(item, dict) and (str(item.get("step") or "").strip() or str(item.get("label") or "").strip())
    ]
    key_entities = [
        str(item).strip()
        for item in raw.get("key_entities", [])
        if str(item).strip()
    ]
    role_shell = derive_ui_role_session_contract(
        ui_pages,
        {
            "locale": locale,
            "supporting_roles": supporting_roles,
            "current_session_role": raw.get("current_session_role", ""),
            "available_workspaces": raw.get("available_workspaces", []),
            "role_scoped_entry_routes": raw.get("role_scoped_entry_routes", {}),
            "route_guard_policy": raw.get("route_guard_policy", {}),
            "read_only_vs_editable_by_role": raw.get("read_only_vs_editable_by_role", {}),
        },
    )
    workflow_navigation = derive_ui_workflow_navigation_contract(ui_pages, role_shell, locale=locale)
    supporting_roles = ordered_ui_roles(supporting_roles, [workspace.get("role", "") for workspace in role_shell["available_workspaces"]], locale=locale)
    return {
        "product_name": product_name,
        "product_heading": product_heading,
        "supporting_roles": supporting_roles,
        "workflow_backbone": workflow_backbone,
        "key_entities": key_entities,
        "locale": locale,
        "current_session_role": role_shell["current_session_role"],
        "available_workspaces": role_shell["available_workspaces"],
        "role_scoped_entry_routes": role_shell["role_scoped_entry_routes"],
        "route_guard_policy": role_shell["route_guard_policy"],
        "read_only_vs_editable_by_role": role_shell["read_only_vs_editable_by_role"],
        "primary_navigation_mode": workflow_navigation["primary_navigation_mode"],
        "global_nav_items": workflow_navigation["global_nav_items"],
        "local_nav_items": workflow_navigation["local_nav_items"],
        "contextual_nav_items": workflow_navigation["contextual_nav_items"],
        "next_step_cta": workflow_navigation["next_step_cta"],
        "route_reachability_policy": workflow_navigation["route_reachability_policy"],
        "placemaking_markers": workflow_navigation["placemaking_markers"],
    }


def ui_page_actor_label(page_contract: dict[str, Any], app_context: dict[str, Any], *, locale: str) -> str:
    actors = [
        str(item).strip()
        for item in page_contract.get("page_actor", [])
        if str(item).strip()
    ]
    if actors:
        return " / ".join(actors)
    return "workflow owner" if not is_zh_locale(locale) else "业务负责人"


def ui_page_information_objects(page_contract: dict[str, Any]) -> list[str]:
    business_objects = [
        localize_information_object(str(item).strip(), page_contract.get("locale"))
        for item in page_contract.get("business_objects", [])
        if str(item).strip()
    ]
    if business_objects:
        return business_objects[:6]
    objects = [
        localize_information_object(str(item).strip(), page_contract.get("locale"))
        for item in page_contract.get("information_objects", [])
        if str(item).strip()
    ]
    if objects:
        return objects[:6]
    return [
        fieldLabel
        for fieldLabel in [
            str(item).strip()
            for item in page_contract.get("display_fields", [])
            if str(item).strip()
        ][:6]
    ]


def relative_workflow_storage_import(route_segment: str) -> str:
    depth = max(1, len([part for part in route_segment.split("/") if part.strip()]))
    return "../" * depth + "workflow-storage"


def relative_role_session_import(route_segment: str) -> str:
    depth = max(1, len([part for part in route_segment.split("/") if part.strip()]))
    return "../" * depth + "role-session-storage"


def relative_workflow_progress_import(route_segment: str) -> str:
    depth = max(1, len([part for part in route_segment.split("/") if part.strip()]))
    return "../" * depth + "workflow-progress-storage"


def render_workflow_storage_module() -> str:
    return "\n".join(
        [
            'const STORAGE_KEY = "phase3-workflow-context";',
            "",
            "export type WorkflowContext = Record<string, string>;",
            "",
            "function isBrowser(): boolean {",
            '  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";',
            "}",
            "",
            "export function readWorkflowContext(): WorkflowContext {",
            "  if (!isBrowser()) {",
            "    return {};",
            "  }",
            "  try {",
            "    const raw = window.localStorage.getItem(STORAGE_KEY);",
            "    if (!raw) {",
            "      return {};",
            "    }",
            "    const parsed = JSON.parse(raw) as unknown;",
            "    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {",
            "      return {};",
            "    }",
            "    return Object.fromEntries(",
            "      Object.entries(parsed as Record<string, unknown>)",
            "        .map(([key, value]) => [key, typeof value === 'string' ? value : String(value ?? '')])",
            "        .filter(([key, value]) => key.trim().length > 0 && value.trim().length > 0),",
            "    );",
            "  } catch {",
            "    return {};",
            "  }",
            "}",
            "",
            "export function persistWorkflowContext(partial: Record<string, unknown>): WorkflowContext {",
            "  const current = readWorkflowContext();",
            "  const next: WorkflowContext = { ...current };",
            "  for (const [key, value] of Object.entries(partial)) {",
            "    if (!key.trim()) {",
            "      continue;",
            "    }",
            "    const normalized = typeof value === 'string' ? value.trim() : String(value ?? '').trim();",
            "    if (!normalized) {",
            "      continue;",
            "    }",
            "    next[key] = normalized;",
            "  }",
            "  if (isBrowser()) {",
            "    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));",
            "  }",
            "  return next;",
            "}",
            "",
            "export function clearWorkflowContext(): void {",
            "  if (isBrowser()) {",
            "    window.localStorage.removeItem(STORAGE_KEY);",
            "  }",
            "}",
            "",
        ]
    )


def render_role_session_storage_module() -> str:
    return "\n".join(
        [
            'const STORAGE_KEY = "phase3-role-session";',
            "",
            "export type RoleSession = {",
            "  currentRole?: string;",
            "  entryRoute?: string;",
            "};",
            "",
            "function isBrowser(): boolean {",
            '  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";',
            "}",
            "",
            "export function readRoleSession(): RoleSession {",
            "  if (!isBrowser()) {",
            "    return {};",
            "  }",
            "  try {",
            "    const raw = window.localStorage.getItem(STORAGE_KEY);",
            "    if (!raw) {",
            "      return {};",
            "    }",
            "    const parsed = JSON.parse(raw) as unknown;",
            "    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {",
            "      return {};",
            "    }",
            "    const source = parsed as Record<string, unknown>;",
            "    const currentRole = typeof source.currentRole === 'string' ? source.currentRole.trim() : '';",
            "    const entryRoute = typeof source.entryRoute === 'string' ? source.entryRoute.trim() : '';",
            "    return {",
            "      ...(currentRole ? { currentRole } : {}),",
            "      ...(entryRoute ? { entryRoute } : {}),",
            "    };",
            "  } catch {",
            "    return {};",
            "  }",
            "}",
            "",
            "export function persistRoleSession(partial: RoleSession): RoleSession {",
            "  const current = readRoleSession();",
            "  const next: RoleSession = { ...current, ...partial };",
            "  if (isBrowser()) {",
            "    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));",
            "  }",
            "  return next;",
            "}",
            "",
            "export function clearRoleSession(): void {",
            "  if (isBrowser()) {",
            "    window.localStorage.removeItem(STORAGE_KEY);",
            "  }",
            "}",
            "",
        ]
    )


def render_workflow_progress_storage_module() -> str:
    return "\n".join(
        [
            'const STORAGE_KEY = "phase3-workflow-progress";',
            'export const WORKFLOW_PROGRESS_EVENT = "phase3-workflow-progress-change";',
            "",
            "export type WorkflowProgressState = {",
            "  unlockedRoutes: string[];",
            "  lastRoute?: string;",
            "};",
            "",
            "export type WorkflowProgress = Record<string, WorkflowProgressState>;",
            "",
            "function isBrowser(): boolean {",
            '  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";',
            "}",
            "",
            "function normalizeRoutes(value: unknown): string[] {",
            "  if (!Array.isArray(value)) {",
            "    return [];",
            "  }",
            "  const ordered: string[] = [];",
            "  const seen = new Set<string>();",
            "  for (const item of value) {",
            "    const route = typeof item === 'string' ? item.trim() : String(item ?? '').trim();",
            "    if (!route) {",
            "      continue;",
            "    }",
            "    const key = route.toLowerCase();",
            "    if (seen.has(key)) {",
            "      continue;",
            "    }",
            "    seen.add(key);",
            "    ordered.push(route);",
            "  }",
            "  return ordered;",
            "}",
            "",
            "function emitChange(next: WorkflowProgress): void {",
            "  if (!isBrowser() || typeof window.dispatchEvent !== 'function') {",
            "    return;",
            "  }",
            "  window.dispatchEvent(new CustomEvent(WORKFLOW_PROGRESS_EVENT, { detail: next }));",
            "}",
            "",
            "export function readWorkflowProgress(): WorkflowProgress {",
            "  if (!isBrowser()) {",
            "    return {};",
            "  }",
            "  try {",
            "    const raw = window.localStorage.getItem(STORAGE_KEY);",
            "    if (!raw) {",
            "      return {};",
            "    }",
            "    const parsed = JSON.parse(raw) as unknown;",
            "    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {",
            "      return {};",
            "    }",
            "    const source = parsed as Record<string, unknown>;",
            "    const next: WorkflowProgress = {};",
            "    for (const [role, value] of Object.entries(source)) {",
            "      if (!role.trim() || !value || typeof value !== 'object' || Array.isArray(value)) {",
            "        continue;",
            "      }",
            "      const row = value as Record<string, unknown>;",
            "      const unlockedRoutes = normalizeRoutes(row.unlockedRoutes);",
            "      const lastRoute = typeof row.lastRoute === 'string' ? row.lastRoute.trim() : '';",
            "      next[role] = {",
            "        unlockedRoutes,",
            "        ...(lastRoute ? { lastRoute } : {}),",
            "      };",
            "    }",
            "    return next;",
            "  } catch {",
            "    return {};",
            "  }",
            "}",
            "",
            "function persist(next: WorkflowProgress): WorkflowProgress {",
            "  if (isBrowser()) {",
            "    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));",
            "    emitChange(next);",
            "  }",
            "  return next;",
            "}",
            "",
            "export function initializeWorkflowProgress(role: string, entryRoute: string): WorkflowProgress {",
            "  const normalizedRole = role.trim();",
            "  const normalizedEntryRoute = entryRoute.trim();",
            "  const current = readWorkflowProgress();",
            "  if (!normalizedRole || !normalizedEntryRoute) {",
            "    return current;",
            "  }",
            "  const existing = current[normalizedRole] ?? { unlockedRoutes: [] };",
            "  const unlockedRoutes = normalizeRoutes([normalizedEntryRoute, ...existing.unlockedRoutes]);",
            "  return persist({",
            "    ...current,",
            "    [normalizedRole]: {",
            "      unlockedRoutes,",
            "      lastRoute: existing.lastRoute || normalizedEntryRoute,",
            "    },",
            "  });",
            "}",
            "",
            "export function markWorkflowRouteVisited(role: string, route: string): WorkflowProgress {",
            "  const normalizedRole = role.trim();",
            "  const normalizedRoute = route.trim();",
            "  const current = readWorkflowProgress();",
            "  if (!normalizedRole || !normalizedRoute) {",
            "    return current;",
            "  }",
            "  const existing = current[normalizedRole] ?? { unlockedRoutes: [] };",
            "  return persist({",
            "    ...current,",
            "    [normalizedRole]: {",
            "      unlockedRoutes: normalizeRoutes([...existing.unlockedRoutes, normalizedRoute]),",
            "      lastRoute: normalizedRoute,",
            "    },",
            "  });",
            "}",
            "",
            "export function unlockWorkflowRoute(role: string, route: string): WorkflowProgress {",
            "  const normalizedRole = role.trim();",
            "  const normalizedRoute = route.trim();",
            "  const current = readWorkflowProgress();",
            "  if (!normalizedRole || !normalizedRoute) {",
            "    return current;",
            "  }",
            "  const existing = current[normalizedRole] ?? { unlockedRoutes: [] };",
            "  return persist({",
            "    ...current,",
            "    [normalizedRole]: {",
            "      unlockedRoutes: normalizeRoutes([...existing.unlockedRoutes, normalizedRoute]),",
            "      ...(existing.lastRoute ? { lastRoute: existing.lastRoute } : {}),",
            "    },",
            "  });",
            "}",
            "",
            "export function clearWorkflowProgress(role?: string): WorkflowProgress {",
            "  const current = readWorkflowProgress();",
            "  const normalizedRole = typeof role === 'string' ? role.trim() : '';",
            "  if (!normalizedRole) {",
            "    if (isBrowser()) {",
            "      window.localStorage.removeItem(STORAGE_KEY);",
            "      emitChange({});",
            "    }",
            "    return {};",
            "  }",
            "  const next = { ...current };",
            "  delete next[normalizedRole];",
            "  return persist(next);",
            "}",
            "",
        ]
    )

def render_blueprint_layout_markup(page_blueprint_type: str) -> str:
    normalized = normalize_ui_blueprint_type(page_blueprint_type, preserve_unknown=True)
    if normalized == "setup-flow":
        surface = """
      <section data-phase3-region="setup-flow" style={{ display: "grid", gap: 16 }}>
        {renderSetupFlowWorkspace()}
      </section>
"""
    elif normalized == "analysis-board":
        surface = """
      <section data-phase3-region="analysis-board" style={{ display: "grid", gap: 16 }}>
        {renderAnalysisBoardWorkspace()}
      </section>
"""
    elif normalized == "record-workbench":
        surface = """
      <section data-phase3-region="record-workbench" style={{ display: "grid", gap: 16 }}>
        {renderWorkbenchWorkspace()}
      </section>
"""
    elif normalized == "execution-workbench":
        surface = """
      <section data-phase3-region="execution-workbench" style={{ display: "grid", gap: 16 }}>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 1.9fr) minmax(320px, 1fr)" }}>
          <div>{renderExecutionBoard()}</div>
          <aside>{renderExecutionRail()}</aside>
        </div>
      </section>
"""
    elif normalized == "review-decision":
        surface = """
      <section data-phase3-region="review-decision" style={{ display: "grid", gap: 16 }}>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 1.6fr) minmax(360px, 1fr)" }}>
          <div>{renderReviewEvidenceLedger()}</div>
          <aside>{renderReviewDecisionRail()}</aside>
        </div>
      </section>
"""
    elif normalized == "detail-view":
        surface = """
      <section data-phase3-region="detail-view" style={{ display: "grid", gap: 16 }}>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 1.8fr) minmax(320px, 1fr)" }}>
          <div>{renderDetailReadingPane()}</div>
          <aside>{renderDetailActionSidebar()}</aside>
        </div>
      </section>
"""
    else:
        surface = """
      <section data-phase3-region="unsupported-blueprint" style={{ display: "grid", gap: 16 }}>
        {sectionShell("Blueprint support gap", (
          <div style={{ display: "grid", gap: 12 }}>
            <p style={{ margin: 0, color: "#b42318" }}>
              {`This page contract declares blueprint '${pageBlueprintType}', but the fallback renderer does not support it yet.`}
            </p>
            <p style={{ margin: 0, color: "#475569" }}>
              {supportCopy(primaryWorkRegion, subtitle, userGoal, actionModel)}
            </p>
          </div>
        ))}
        {renderStatusCard("Renderer readiness")}
      </section>
"""
    return surface.strip("\n")


def render_workflow_intent_markup(page_blueprint_type: str) -> str:
    _ = page_blueprint_type
    return ""


def render_page_component(
    surface: str,
    *,
    page_contract: dict[str, Any] | None = None,
    related_operations: list[dict[str, str]],
    related_work_packages: list[dict[str, str]],
    navigation: dict[str, str] | None = None,
    app_context: dict[str, Any] | None = None,
) -> str:
    page = page_contract or build_generic_ui_page(surface)
    locale = infer_ui_locale(
        str(page.get("locale") or ""),
        surface,
        str(page.get("page_title") or ""),
        str(page.get("subtitle") or ""),
        str(page.get("user_goal") or ""),
        str(page.get("eyebrow") or ""),
    )
    route = ui_page_route_segment(page, surface)
    page_route = str(page.get("route") or f"/{route}").strip() or f"/{route}"
    if not page_route.startswith("/"):
        page_route = f"/{page_route}"
    component_name = f"{camel_case(route)}Page"
    title = str(page.get("page_title") or surface).replace("/", " / ")
    page_role = infer_ui_page_role(title, page)
    page_blueprint_type = infer_ui_page_blueprint_type(title, page)
    normalized_inputs = [
        normalize_ui_input_spec(item, locale=locale)
        for item in page.get("user_inputs", [])
        if isinstance(item, dict) and str(item.get("field", "")).strip()
    ] or [normalize_ui_input_spec({"field": "query", "required": False, "validation": "text"}, locale=locale)]
    display_fields = [str(item).strip() for item in page.get("display_fields", []) if str(item).strip()]
    normalized_actions = [
        item
        for item in page.get("actions_and_transitions", [])
        if isinstance(item, dict) and str(item.get("action", "")).strip()
    ]
    contract_summary_cards = [str(item).strip() for item in page.get("summary_cards", []) if str(item).strip()]
    contract_detail_fields = [str(item).strip() for item in page.get("detail_fields_in_order", []) if str(item).strip()]
    contract_table_columns = [str(item).strip() for item in page.get("table_columns", []) if str(item).strip()]
    contract_filters = [str(item).strip() for item in page.get("filters_and_selectors", []) if str(item).strip()]
    selector_fields = [
        str(item.get("field") or "").strip()
        for item in page.get("field_source_mapping", [])
        if isinstance(item, dict)
        and str(item.get("source") or "").strip() == "workflow-context"
        and str(item.get("field") or "").strip()
    ]
    normalized_inputs = augment_user_inputs_with_selector_fields(
        user_inputs=normalized_inputs,
        selector_fields=selector_fields,
        actions=normalized_actions,
        locale=locale,
    )
    contract_status_messages = contract_list_value(page.get("required_status_messages", []))
    contract_submission_feedback = [str(item).strip() for item in page.get("submission_feedback", []) if str(item).strip()]
    copy = default_ui_page_copy(
        title,
        page_role=page_role,
        actions=normalized_actions,
        display_fields=display_fields,
        user_inputs=normalized_inputs,
        locale=locale,
    )
    shell_copy = surface_shell_copy(title, page_role, locale)
    synthesized_contract_sections = contract_driven_ui_sections(
        surface=title,
        page_role=page_role,
        locale=locale,
        display_fields=display_fields,
        user_inputs=normalized_inputs,
        summary_cards=contract_summary_cards,
        detail_fields_in_order=contract_detail_fields,
        table_columns=contract_table_columns,
        selector_fields=selector_fields,
        filters_and_selectors=contract_filters,
        submission_feedback=contract_submission_feedback,
        required_status_messages=contract_status_messages,
    )
    synthesized_contract_presentation = contract_driven_data_presentation(
        summary_cards=contract_summary_cards,
        detail_fields_in_order=contract_detail_fields,
        table_columns=contract_table_columns,
        filters_and_selectors=contract_filters,
        required_status_messages=contract_status_messages,
        submission_feedback=contract_submission_feedback,
    )
    operations_blob = json.dumps(related_operations, ensure_ascii=False, indent=2)
    work_packages_blob = json.dumps(related_work_packages, ensure_ascii=False, indent=2)
    data_required_blob = json.dumps(page.get("data_required", []), ensure_ascii=False, indent=2)
    presentation_blob = json.dumps(
        synthesized_contract_presentation or page.get("data_presentation", []),
        ensure_ascii=False,
        indent=2,
    )
    user_inputs_blob = json.dumps(normalized_inputs, ensure_ascii=False, indent=2)
    field_mappings_blob = json.dumps(page.get("field_source_mapping", []), ensure_ascii=False, indent=2)
    state_conditions_blob = json.dumps(page.get("state_conditions", {}), ensure_ascii=False, indent=2)
    actions_blob = json.dumps(normalized_actions or [
        {
            "action": copy["primary_cta"]["label"],
            "on_success": "让最新状态继续显示在当前页面上。" if is_zh_locale(locale) else "Show the latest state on the current page.",
            "on_error": "保留当前页面并展示恢复指引。" if is_zh_locale(locale) else "Keep the page open with recovery guidance.",
        }
    ], ensure_ascii=False, indent=2)
    display_fields_blob = json.dumps(display_fields, ensure_ascii=False, indent=2)
    page_navigation: dict[str, str] = {}
    if isinstance(page.get("navigation"), dict):
        page_navigation.update(
            {
                key: str(value).strip()
                for key, value in page.get("navigation", {}).items()
                if key in {"previous_route", "next_route"} and str(value).strip()
            }
        )
    if not page_navigation.get("next_route"):
        next_route_candidates = [
            str(item).strip()
            for item in page.get("next_route_candidates", [])
            if str(item).strip()
        ]
        if next_route_candidates:
            page_navigation["next_route"] = next_route_candidates[0]
    if navigation:
        page_navigation.update({key: str(value).strip() for key, value in navigation.items() if str(value).strip()})
    navigation_blob = json.dumps(page_navigation, ensure_ascii=False, indent=2)
    primary_api_binding = page.get("primary_api_binding")
    if not isinstance(primary_api_binding, dict) or not str(primary_api_binding.get("path") or "").strip():
        data_required = page.get("data_required", [])
        primary_api_binding = data_required[0] if isinstance(data_required, list) and data_required else None
    primary_api_binding_blob = json.dumps(primary_api_binding, ensure_ascii=False, indent=2)
    eyebrow_blob = json.dumps(str(page.get("eyebrow") or copy["eyebrow"]).strip(), ensure_ascii=False)
    subtitle_blob = json.dumps(str(page.get("subtitle") or copy["subtitle"]).strip(), ensure_ascii=False)
    user_goal_blob = json.dumps(str(page.get("user_goal") or copy["user_goal"]).strip(), ensure_ascii=False)
    primary_cta_blob = json.dumps(page.get("primary_cta", {}) if isinstance(page.get("primary_cta", {}), dict) else copy["primary_cta"], ensure_ascii=False, indent=2)
    secondary_cta_blob = json.dumps(page.get("secondary_cta", {}) if isinstance(page.get("secondary_cta", {}), dict) else copy["secondary_cta"], ensure_ascii=False, indent=2)
    section_source = (
        (page.get("sections", []) if isinstance(page.get("sections", []), list) and page.get("sections") else [])
        or synthesized_contract_sections
        or copy["sections"]
    )
    localized_sections = []
    for item in section_source:
        if not isinstance(item, dict):
            continue
        localized_item = dict(item)
        localized_item["view"] = view_label(str(item.get("view") or ""), locale)
        localized_sections.append(localized_item)
    field_labels = {
        field: ui_field_label(field, locale)
        for field in {
            *display_fields,
            *[str(item.get("field") or "").strip() for item in normalized_inputs if str(item.get("field") or "").strip()],
            *[
                str(field).strip()
                for action in normalized_actions
                if isinstance(action, dict)
                for field in [
                    *action.get("required_fields", []),
                    *action.get("optional_fields", []),
                    *action.get("result_fields", []),
                ]
                if str(field).strip()
            ],
            *[
                str(field).strip()
                for section in localized_sections
                if isinstance(section, dict)
                for field in section.get("bind_fields", [])
                if str(field).strip()
            ],
        }
    }
    field_labels_blob = json.dumps(field_labels, ensure_ascii=False, indent=2)
    sections_blob = json.dumps(localized_sections, ensure_ascii=False, indent=2)
    empty_state_blob = json.dumps(page.get("empty_state", {}) if isinstance(page.get("empty_state", {}), dict) and page.get("empty_state") else copy["empty_state"], ensure_ascii=False, indent=2)
    success_state_blob = json.dumps(page.get("success_state", {}) if isinstance(page.get("success_state", {}), dict) and page.get("success_state") else copy["success_state"], ensure_ascii=False, indent=2)
    error_state_blob = json.dumps(page.get("error_state", {}) if isinstance(page.get("error_state", {}), dict) and page.get("error_state") else copy["error_state"], ensure_ascii=False, indent=2)
    page_app_context_source = app_context if isinstance(app_context, dict) and app_context else (
        page.get("app_context", {})
        if isinstance(page.get("app_context", {}), dict) and page.get("app_context")
        else {}
    )
    page_app_context = dict(page_app_context_source) if page_app_context_source else ui_app_context([page])
    app_context_blob = json.dumps(page_app_context, ensure_ascii=False, indent=2)
    shell_copy_blob = json.dumps(shell_copy, ensure_ascii=False, indent=2)
    workflow_step_blob = json.dumps(page.get("workflow_step", {}) if isinstance(page.get("workflow_step", {}), dict) else {}, ensure_ascii=False, indent=2)
    information_objects_blob = json.dumps(ui_page_information_objects(page), ensure_ascii=False, indent=2)
    allowed_roles_blob = json.dumps(
        [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    read_only_by_role_blob = json.dumps(
        page.get("read_only_vs_editable_by_role", {})
        if isinstance(page.get("read_only_vs_editable_by_role", {}), dict)
        else {},
        ensure_ascii=False,
        indent=2,
    )
    required_regions_blob = json.dumps(
        [str(item).strip() for item in page.get("required_regions", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    next_route_candidates_blob = json.dumps(
        [str(item).strip() for item in page.get("next_route_candidates", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    compiled_interactions_blob = json.dumps(
        [item for item in page.get("compiled_interactions", []) if isinstance(item, dict)],
        ensure_ascii=False,
        indent=2,
    )
    must_show_together_blob = json.dumps(
        [str(item).strip() for item in page.get("must_show_together", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    required_inputs_contract_blob = json.dumps(
        [str(item).strip() for item in page.get("required_user_inputs_or_confirmations", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    render_blocks_blob = json.dumps(
        [str(item).strip() for item in page.get("render_blocks_in_order", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    page_blueprint_type_blob = json.dumps(page_blueprint_type, ensure_ascii=False)
    primary_work_region_blob = json.dumps(str(page.get("primary_work_region") or "").strip(), ensure_ascii=False)
    secondary_support_regions_blob = json.dumps(
        [str(item).strip() for item in page.get("secondary_support_regions", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    dominant_component_pattern_blob = json.dumps(str(page.get("dominant_component_pattern") or "").strip(), ensure_ascii=False)
    action_model_blob = json.dumps(str(page.get("action_model") or "").strip(), ensure_ascii=False)
    page_locale_blob = json.dumps(locale, ensure_ascii=False)
    business_state_transitions_blob = json.dumps(
        [item for item in page.get("business_state_transitions", []) if isinstance(item, dict)],
        ensure_ascii=False,
        indent=2,
    )
    forbidden_layout_patterns_blob = json.dumps(
        [str(item).strip() for item in page.get("forbidden_layout_patterns", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    field_groups_blob = json.dumps(
        [str(item).strip() for item in page.get("field_groups", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    input_controls_blob = json.dumps(
        [str(item).strip() for item in page.get("input_controls", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    summary_cards_blob = json.dumps(
        [str(item).strip() for item in page.get("summary_cards", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    detail_fields_blob = json.dumps(
        [str(item).strip() for item in page.get("detail_fields_in_order", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    table_columns_blob = json.dumps(
        [str(item).strip() for item in page.get("table_columns", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    filters_selectors_blob = json.dumps(
        [str(item).strip() for item in page.get("filters_and_selectors", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    required_status_messages_blob = json.dumps(contract_list_value(page.get("required_status_messages", [])), ensure_ascii=False, indent=2)
    submission_feedback_blob = json.dumps(
        [str(item).strip() for item in page.get("submission_feedback", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    context_arrives_from_blob = json.dumps(str(page.get("context_arrives_from") or "").strip(), ensure_ascii=False)
    context_must_continue_to_blob = json.dumps(str(page.get("context_must_continue_to") or "").strip(), ensure_ascii=False)
    executor_brief_blob = json.dumps(
        [str(item).strip() for item in page.get("executor_brief", []) if str(item).strip()],
        ensure_ascii=False,
        indent=2,
    )
    setup_route_hints_block = ""
    api_import = relative_api_import(route)
    workflow_storage_import = relative_workflow_storage_import(route)
    role_session_import = relative_role_session_import(route)
    workflow_progress_import = relative_workflow_progress_import(route)
    template = r"""
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { callApi } from "__API_IMPORT__";
import { persistWorkflowContext, readWorkflowContext } from "__WORKFLOW_STORAGE_IMPORT__";
import { readRoleSession } from "__ROLE_SESSION_IMPORT__";
import { WORKFLOW_PROGRESS_EVENT, initializeWorkflowProgress, markWorkflowRouteVisited, readWorkflowProgress, unlockWorkflowRoute } from "__WORKFLOW_PROGRESS_IMPORT__";

type DataRequired = {
  source: string;
  method: string;
  path: string;
  purpose: string;
  interaction_id?: string;
  service_binding_id?: string;
  domain_service?: string;
  binding_mode?: string;
  trigger_kind?: string;
};

type InputOption = {
  value: string;
  label: string;
};

type UserInput = {
  field: string;
  label?: string;
  required: boolean;
  validation: string;
  value_source?: string;
  internal_exposure?: string;
  editability?: string;
  datatype?: string;
  control?: string;
  options?: InputOption[];
  options_source?: string;
  system_generated?: boolean;
  server_assigned?: boolean;
  lookup_entity?: string;
  display_format?: string;
  placeholder?: string;
  helper?: string;
  group?: string;
};

type ActionInputSource = {
  field: string;
  source: string;
  bind_to?: string;
  value_source?: string;
  internal_exposure?: string;
  editability?: string;
  datatype?: string;
  control?: string;
  options?: InputOption[];
  options_source?: string;
  system_generated?: boolean;
  server_assigned?: boolean;
  lookup_entity?: string;
  display_format?: string;
};

type SurfaceAction = {
  interaction_id?: string;
  service_binding_id?: string;
  flow_id?: string;
  trigger_kind?: string;
  action_type?: string;
  binding_mode?: string;
  readiness_status?: string;
  blocked_reason?: string;
  action: string;
  on_success: string;
  on_error: string;
  next_route?: string;
  summary?: string;
  required_fields?: string[];
  optional_fields?: string[];
  required_input_sources?: ActionInputSource[];
  optional_input_sources?: ActionInputSource[];
  result_fields?: string[];
  response_bindings?: Array<{
    from: string;
    to: string;
  }>;
  server_generated_fields?: string[];
  ui_refresh_targets?: string[];
  handoff_materialization?: string;
  internal_exposure?: string;
  actor_role?: string;
  consumer_role?: string;
  visible_next_page_id?: string;
  completion_signal?: string;
  handoff_surface_type?: string;
  next_role_entry_mode?: string;
  api_binding?: {
    method?: string;
    path?: string;
  };
};

type CompiledInteraction = {
  interaction_id?: string;
  region?: string;
  element_type?: string;
  interaction_pattern?: string;
  trigger_kind?: string;
  action_type?: string;
  input_schema_ref?: string;
  display_field_set?: string[];
  validation_rules?: string;
  visibility_rule?: string;
  enabled_rule?: string;
  success_state?: string;
  error_state?: string;
  blocked_rule?: string;
  next_route?: string;
  flow_id?: string;
  step_id?: string;
  transition_condition?: string;
  next_page_id?: string;
  visible_next_page_id?: string;
  completion_signal?: string;
  actor_role?: string;
  consumer_role?: string;
  handoff_surface_type?: string;
  next_role_entry_mode?: string;
  handoff_context_fields?: string[];
  handoff_materialization?: string;
  failure_route?: string;
  termination_condition?: string;
  service_binding_id?: string;
  binding_mode?: string;
  domain_service?: string;
  api_endpoint?: string;
  http_method?: string;
  request_field_mapping?: string;
  response_field_mapping?: string;
  value_source_map?: Record<string, string>;
  server_generated_fields?: string[];
  ui_refresh_targets?: string[];
  rbac_policy?: string;
  audit_event?: string;
  failure_codes?: string;
  internal_exposure?: string;
  readiness_status?: string;
  blocked_reason?: string;
};

type SurfaceNavigation = {
  previous_route?: string;
  next_route?: string;
};

type PageSection = {
  section_id: string;
  title: string;
  purpose: string;
  view: string;
  bind_fields?: string[];
};

type CtaConfig = {
  label: string;
  hint?: string;
  kind?: string;
};

type StateCopy = {
  headline: string;
  body: string;
};

type BusinessStateTransition = {
  domain_object?: string;
  from_state?: string;
  to_state?: string;
  trigger_action?: string;
  ui_state_change?: string;
  evidence_fields?: string[];
};

type WorkflowStep = {
  step?: string;
  label?: string;
  surface?: string;
};

type ShellCopy = {
  selectors_panel_title: string;
  work_area_title: string;
  work_area_hint: string;
  current_step_label: string;
  workflow_steps_title: string;
  workflow_steps_hint: string;
  current_data_title: string;
  next_steps_title: string;
  pending_live_data: string;
};

type WorkflowNavItem = {
  route: string;
  label: string;
  step_label?: string;
  step_index?: number;
  total_steps?: number;
  unlocked_by_default?: boolean;
  locked_reason?: string;
};

type ContextualNav = {
  previous_route?: string;
  next_route?: string;
  previous_label?: string;
  next_label?: string;
  current_label?: string;
};

type NextStepCta = {
  kind?: string;
  target_route?: string;
  target_role?: string;
  target_label?: string;
  label?: string;
};

type PlacemakingMarker = {
  step_label?: string;
  current_label?: string;
  previous_label?: string;
  next_label?: string;
  step_index?: number;
  total_steps?: number;
};

type RoleReachability = {
  entry_route?: string;
  ordered_routes?: string[];
  direct_routes?: string[];
  flow_routes?: string[];
  default_reachable_routes?: string[];
  unlock_rule?: string;
};

type RouteReachability = {
  entry_route?: string;
  reachability_mode?: string;
  reachable_by_default?: boolean;
  reachable_after_route?: string;
  next_route?: string;
  step_index?: number;
  total_steps?: number;
  locked_reason?: string;
};

type WorkflowProgressState = {
  unlockedRoutes: string[];
  lastRoute?: string;
};

type WorkflowProgress = Record<string, WorkflowProgressState>;

type PageRoleAccess = {
  editable_roles?: string[];
  read_only_roles?: string[];
  default_access?: string;
};

type AppContext = {
  product_name: string;
  product_heading: string;
  supporting_roles?: string[];
  workflow_backbone?: WorkflowStep[];
  key_entities?: string[];
  current_session_role?: string;
  role_scoped_entry_routes?: Record<string, string>;
  route_guard_policy?: {
    workspace_switch_required?: boolean;
    default_route?: string;
    denied_behavior?: string;
    auth_entry_route?: string;
    auth_entry_label?: string;
    routes?: Record<string, { allowed_roles?: string[]; editable_roles?: string[]; read_only_roles?: string[] }>;
  };
  read_only_vs_editable_by_role?: Record<string, PageRoleAccess>;
  primary_navigation_mode?: string;
  global_nav_items?: Array<{ route: string; label: string; kind?: string }>;
  local_nav_items?: Record<string, WorkflowNavItem[]>;
  contextual_nav_items?: Record<string, { by_role?: Record<string, ContextualNav> }>;
  next_step_cta?: Record<string, { by_role?: Record<string, NextStepCta> }>;
  route_reachability_policy?: {
    mode?: string;
    denied_behavior?: string;
    roles?: Record<string, RoleReachability>;
    routes?: Record<string, { allowed_roles?: string[]; by_role?: Record<string, RouteReachability>; denied_behavior?: string }>;
  };
  placemaking_markers?: Record<string, { by_role?: Record<string, PlacemakingMarker> }>;
};

const pageRole = __PAGE_ROLE__;
const pageLocale = __PAGE_LOCALE__;
const zhLocale = pageLocale.toLowerCase().startsWith("zh");
const eyebrow = __EYEBROW__;
const subtitle = __SUBTITLE__;
const userGoal = __USER_GOAL__;
const primaryCta = __PRIMARY_CTA__ as CtaConfig;
const secondaryCta = __SECONDARY_CTA__ as CtaConfig;
const sections = __SECTIONS__ as PageSection[];
const emptyState = __EMPTY_STATE__ as StateCopy;
const successState = __SUCCESS_STATE__ as StateCopy;
const errorState = __ERROR_STATE__ as StateCopy;

const dataRequired: DataRequired[] = __DATA_REQUIRED__;
const primaryApiBinding = __PRIMARY_API_BINDING__ as DataRequired | null;
const displayFields = __DISPLAY_FIELDS__ as readonly string[];
const fieldLabels = __FIELD_LABELS__ as Record<string, string>;
const userInputs: UserInput[] = __USER_INPUTS__;
const stateConditions = __STATE_CONDITIONS__ as Record<string, string>;
const actionsAndTransitions: SurfaceAction[] = __ACTIONS__;
const navigation: SurfaceNavigation = __NAVIGATION__;
const appContext = __APP_CONTEXT__ as AppContext;
const shellCopy = __SHELL_COPY__ as ShellCopy;
const workflowStep = __WORKFLOW_STEP__ as WorkflowStep;
const informationObjects = __INFORMATION_OBJECTS__ as readonly string[];
const allowedRoles = __ALLOWED_ROLES__ as readonly string[];
const readOnlyByRole = __READ_ONLY_BY_ROLE__ as PageRoleAccess;
const requiredRegions = __REQUIRED_REGIONS__ as readonly string[];
const nextRouteCandidates = __NEXT_ROUTE_CANDIDATES__ as readonly string[];
const compiledInteractions = __COMPILED_INTERACTIONS__ as CompiledInteraction[];
const pageBlueprintType = __PAGE_BLUEPRINT_TYPE__;
const blueprintKind = String(pageBlueprintType).trim().toLowerCase();
const primaryWorkRegion = __PRIMARY_WORK_REGION__;
const secondarySupportRegions = __SECONDARY_SUPPORT_REGIONS__ as readonly string[];
const dominantComponentPattern = __DOMINANT_COMPONENT_PATTERN__;
const actionModel = __ACTION_MODEL__;
const businessStateTransitions = __BUSINESS_STATE_TRANSITIONS__ as BusinessStateTransition[];
const summaryCardsContract = __SUMMARY_CARDS__ as readonly string[];
const tableColumnsContract = __TABLE_COLUMNS__ as readonly string[];
const requiredStatusMessages = __REQUIRED_STATUS_MESSAGES__ as readonly string[];
const contextArrivesFrom = __CONTEXT_ARRIVES_FROM__;
const contextMustContinueTo = __CONTEXT_MUST_CONTINUE_TO__;
const pageRoute = "__ROUTE__";
void [workflowStep, requiredRegions, nextRouteCandidates, secondarySupportRegions, dominantComponentPattern, contextArrivesFrom, contextMustContinueTo];

function contextualNavForRole(route: string, role: string): ContextualNav | null {
  return appContext.contextual_nav_items?.[route]?.by_role?.[role] ?? null;
}

function nextStepCtaForRole(route: string, role: string): NextStepCta | null {
  return appContext.next_step_cta?.[route]?.by_role?.[role] ?? null;
}

function placemakingForRole(route: string, role: string): PlacemakingMarker | null {
  return appContext.placemaking_markers?.[route]?.by_role?.[role] ?? null;
}

function reachabilityForRole(route: string, role: string): RouteReachability | null {
  return appContext.route_reachability_policy?.routes?.[route]?.by_role?.[role] ?? null;
}

function workflowProgressForRole(progress: WorkflowProgress, role: string): WorkflowProgressState {
  return progress[role] ?? { unlockedRoutes: [] };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function friendlyLabel(value: string): string {
  const candidate = value.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").trim();
  if (!candidate) {
    return "Field";
  }
  return candidate
    .split(/\s+/)
    .map((token) => {
      const lowered = token.toLowerCase();
      if (["id", "api", "cta", "roi"].includes(lowered)) {
        return lowered.toUpperCase();
      }
      return lowered.charAt(0).toUpperCase() + lowered.slice(1);
    })
    .join(" ");
}

function fieldLabel(value: string): string {
  return fieldLabels[value] || friendlyLabel(value);
}

function textValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function cleanContractText(value: unknown, fallback = ""): string {
  const candidate = textValue(value).trim();
  if (!candidate) {
    return fallback;
  }
  if (["—", "-", "none", "n/a"].includes(candidate.toLowerCase())) {
    return fallback;
  }
  return candidate;
}

const internalUiMetaMarkers = [
  "advance-workflow-or-refresh-page-state",
  "carry the active selection",
  "last completed decision",
  "derive visible context",
  "block-if-",
  "enabled_when",
  "render-page-data-view",
  "render-context-summary",
  "show-inline-action-error",
  "show-data-view-load-error",
  "show-context-load-error",
  "not_applicable",
  "request.",
  "response.",
  "query.",
  "ui.",
  "service_binding",
  "failure_codes",
  "audit_event",
  "rbac",
  "agent-internal",
];

function normalizeCopyHaystack(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function looksLikeInternalMetaText(value: unknown): boolean {
  const candidate = cleanContractText(value);
  if (!candidate) {
    return false;
  }
  const haystack = normalizeCopyHaystack(candidate);
  if (internalUiMetaMarkers.some((marker) => haystack.includes(marker))) {
    return true;
  }
  if (/^[a-z0-9]+(?:[-_][a-z0-9]+){2,}$/.test(candidate)) {
    return true;
  }
  if (/(^|[^a-z])http\s+\d{3}\b/i.test(candidate)) {
    return true;
  }
  if (candidate.includes("->") && /(request\.|response\.|query\.|ui\.)/i.test(candidate)) {
    return true;
  }
  return false;
}

function firstBusinessCopy(...values: unknown[]): string {
  for (const value of values) {
    const candidate = cleanContractText(value);
    if (!candidate || looksLikeInternalMetaText(candidate)) {
      continue;
    }
    return candidate;
  }
  return "";
}

function friendlyRouteLabel(value: unknown): string {
  const candidate = cleanContractText(value);
  if (!candidate) {
    return "";
  }
  if (candidate.startsWith("/")) {
    const slug = candidate.split("/").filter(Boolean).at(-1) || "";
    return slug ? friendlyLabel(slug) : candidate;
  }
  return candidate;
}

function arrivalContextCopy(value: unknown): string {
  const explicit = firstBusinessCopy(value);
  if (explicit) {
    return explicit;
  }
  return zhLocale
    ? "本页延续上一步选中的记录与上下文。"
    : "This page continues with the record selected in the previous step.";
}

function carryForwardCopy(fields: readonly string[], fallback: unknown): string {
  const visibleFields = fields
    .map((field) => cleanContractText(field))
    .filter(Boolean)
    .filter((field) => !looksLikeInternalMetaText(field));
  const fieldText = compactList(visibleFields, fieldLabel);
  if (fieldText) {
    return fieldText;
  }
  const explicit = firstBusinessCopy(fallback);
  if (explicit) {
    return explicit;
  }
  return zhLocale
    ? "当前记录与本次更新会继续带到下一步。"
    : "The current record and this update stay available in the next step.";
}

function stepOutcomeCopy(...values: unknown[]): string {
  return firstBusinessCopy(...values)
    || (zhLocale
      ? "在当前记录上应用当前更新，并保持结果可见。"
      : "Apply the current update on the active record and keep the result visible.");
}

function supportCopy(...values: unknown[]): string {
  return firstBusinessCopy(...values)
    || (zhLocale
      ? "处理当前记录并保存本次更新。"
      : "Review the current record and save the current update.");
}
void [arrivalContextCopy, carryForwardCopy, supportCopy];

function normalizeReadiness(value: unknown): string {
  return cleanContractText(value, "ready").toLowerCase();
}

function compactList(values: readonly string[], formatter?: (value: string) => string): string {
  const items = values
    .map((value) => String(value).trim())
    .filter(Boolean)
    .map((value) => formatter ? formatter(value) : value)
    .filter(Boolean);
  return items.join(zhLocale ? "、" : ", ");
}

function isLifecycleTrigger(value: unknown): boolean {
  const normalized = cleanContractText(value).toLowerCase();
  return normalized === "page_load" || normalized === "route_enter" || normalized === "handoff_resume";
}

function requestFromCompiledInteraction(interaction: CompiledInteraction | null | undefined): DataRequired | null {
  const path = cleanContractText(interaction?.api_endpoint || "");
  if (!path) {
    return null;
  }
  return {
    source: "api",
    method: cleanContractText(interaction?.http_method || "", "GET"),
    path,
    purpose: cleanContractText(interaction?.action_type || interaction?.interaction_id || "", "Load page data"),
    interaction_id: cleanContractText(interaction?.interaction_id || ""),
    service_binding_id: cleanContractText(interaction?.service_binding_id || ""),
    domain_service: cleanContractText(interaction?.domain_service || ""),
    binding_mode: cleanContractText(interaction?.binding_mode || ""),
    trigger_kind: cleanContractText(interaction?.trigger_kind || ""),
  };
}

type ParsedPayload = Record<string, unknown> | unknown[] | string | number | boolean | null;

function parseBody(body: string): { raw: string; payload: ParsedPayload; envelopeData: ParsedPayload } {
  const raw = body.trim();
  if (!raw) {
    return { raw: "", payload: null, envelopeData: null };
  }
  try {
    const payload = JSON.parse(raw) as ParsedPayload;
    const envelopeData: ParsedPayload = isRecord(payload) && "data" in payload ? (payload.data as ParsedPayload) : payload;
    return { raw, payload, envelopeData };
  } catch {
    return { raw, payload: raw, envelopeData: raw };
  }
}

function hasRenderableData(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (isRecord(value)) {
    return Object.keys(value).length > 0;
  }
  return typeof value === "string" ? value.trim().length > 0 : value !== null && value !== undefined;
}

function flattenRows(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) {
    return value.filter(isRecord);
  }
  if (isRecord(value)) {
    return [value];
  }
  return [];
}

function readBindingValue(payload: unknown, from: string): unknown {
  if (!from.trim()) {
    return undefined;
  }
  const segments = from.split(".").map((segment) => segment.trim()).filter(Boolean);
  let current: unknown = payload;
  for (const segment of segments) {
    if (Array.isArray(current)) {
      current = current[0];
    }
    if (!isRecord(current) || !(segment in current)) {
      return undefined;
    }
    current = current[segment];
  }
  return current;
}

function contractValue(field: string, primary: unknown, fallbackRecord: Record<string, unknown> | null, formValues: Record<string, string>): string {
  const normalized = field.trim();
  if (!normalized) {
    return "";
  }
  const directPrimary = readBindingValue(primary, normalized);
  if (directPrimary !== undefined) {
    return textValue(directPrimary);
  }
  if (fallbackRecord && normalized in fallbackRecord) {
    return textValue(fallbackRecord[normalized]);
  }
  if (normalized in formValues) {
    return textValue(formValues[normalized]);
  }
  return "";
}

function interpolatePath(pathTemplate: string, values: Record<string, string>): { path: string; remaining: Record<string, string> } {
  let path = pathTemplate || "/";
  const remaining: Record<string, string> = {};
  for (const [key, value] of Object.entries(values)) {
    const token = `{${key}}`;
    if (path.includes(token) && value.trim()) {
      path = path.replaceAll(token, encodeURIComponent(value.trim()));
      continue;
    }
    remaining[key] = value;
  }
  return { path, remaining };
}

type RequestFieldBinding = {
  from: string;
  to: string;
};

function parseRequestFieldMapping(mappingText: string): RequestFieldBinding[] {
  return mappingText
    .split(";")
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const [left = "", right = ""] = chunk.split("->", 2);
      const from = left.trim().split(".").filter(Boolean).at(-1)?.replaceAll("[]", "").trim() || "";
      const to = right.trim();
      return { from, to };
    })
    .filter((binding) => Boolean(binding.from && binding.to));
}

function hasMappedRequestContext(interaction: CompiledInteraction | null | undefined, values: Record<string, string>): boolean {
  const bindings = parseRequestFieldMapping(cleanContractText(interaction?.request_field_mapping || ""));
  if (bindings.length === 0) {
    return true;
  }
  return bindings.some((binding) => Boolean(values[binding.from]?.trim()));
}

function setNestedRequestValue(target: Record<string, unknown>, path: string, value: string): void {
  const segments = path
    .split(".")
    .map((segment) => segment.replaceAll("[]", "").trim())
    .filter(Boolean);
  if (segments.length === 0) {
    return;
  }
  let current: Record<string, unknown> = target;
  for (const segment of segments.slice(0, -1)) {
    const existing = current[segment];
    if (!isRecord(existing)) {
      current[segment] = {};
    }
    current = current[segment] as Record<string, unknown>;
  }
  current[segments[segments.length - 1]] = value;
}

function buildMappedRequest(interaction: CompiledInteraction | null | undefined, values: Record<string, string>): {
  query: Record<string, string>;
  body: Record<string, unknown>;
} {
  const mappingText = cleanContractText(interaction?.request_field_mapping || "");
  const bindings = parseRequestFieldMapping(mappingText);
  const query: Record<string, string> = {};
  const body: Record<string, unknown> = {};
  for (const binding of bindings) {
    const value = values[binding.from];
    if (!value?.trim()) {
      continue;
    }
    if (binding.to.startsWith("query.")) {
      query[binding.to.slice("query.".length)] = value.trim();
      continue;
    }
    if (binding.to.startsWith("request.")) {
      setNestedRequestValue(body, binding.to.slice("request.".length), value.trim());
    }
  }
  return { query, body };
}

function stateMessage(stateKey: string): string {
  return stateConditions[stateKey] || "";
}

function stateHeadline(stateKey: "idle" | "loading" | "success" | "empty" | "error"): string {
  if (stateKey === "success") return successState.headline;
  if (stateKey === "empty") return emptyState.headline;
  if (stateKey === "error") return errorState.headline;
  if (stateKey === "loading") return "Updating this page";
  return "Ready to work";
}

function stateBody(stateKey: "idle" | "loading" | "success" | "empty" | "error"): string {
  if (stateKey === "success") return successState.body;
  if (stateKey === "empty") return emptyState.body;
  if (stateKey === "error") return errorState.body;
  if (stateKey === "loading") return stateMessage("loading") || "Loading the latest workflow data for this page.";
  return userGoal;
}

function recoveryGuidance(status: number | null): string {
  if (status === 401) {
    return zhLocale
      ? "当前会话缺少这次提交需要的访问上下文。请返回工作区重新进入后再试。"
      : "Your session is missing the access context required for this action. Return to the workspace and try again.";
  }
  if (status === 403) {
    return zhLocale
      ? "你当前没有执行这项操作的权限。"
      : "You do not have permission to complete this action.";
  }
  if (status === 404) {
    return zhLocale
      ? "当前请求的记录还不可用。请先刷新页面上下文或确认关键标识，再安全重试。"
      : "The requested record is not available right now. Refresh the page context or confirm the identifiers before trying again.";
  }
  if (status !== null && status >= 500) {
    return zhLocale
      ? "服务暂时还无法完成这一步。请保留当前输入，稍后再安全重试。"
      : "The service could not complete this step right now. Keep your current inputs and retry in a moment.";
  }
  return stateMessage("error") || errorState.body || "We could not complete this step. Review the current inputs and try again.";
}

function actionInputMeta(entry: ActionInputSource, userInputByField?: Map<string, UserInput>): {
  source: string;
  valueSource: string;
  editability: string;
  systemGenerated: boolean;
  serverAssigned: boolean;
} {
  const field = String(entry.field || "").trim();
  const fallback = field ? userInputByField?.get(field) : undefined;
  return {
    source: String(entry.source || "").trim(),
    valueSource: String(entry.value_source || fallback?.value_source || entry.source || "").trim(),
    editability: String(entry.editability || fallback?.editability || "").trim(),
    systemGenerated: Boolean(entry.system_generated ?? fallback?.system_generated),
    serverAssigned: Boolean(entry.server_assigned ?? fallback?.server_assigned),
  };
}

function hasVisibleActionInputField(entry: ActionInputSource, userInputByField?: Map<string, UserInput>): boolean {
  const field = String(entry.field || "").trim();
  if (!field) {
    return false;
  }
  const fallback = userInputByField?.get(field);
  if (!fallback) {
    return false;
  }
  const editability = String(fallback.editability || entry.editability || "").trim();
  return editability !== "hidden" && editability !== "readonly" && editability !== "derived";
}

function actionInputNeedsWorkflowContext(entry: ActionInputSource, userInputByField?: Map<string, UserInput>): boolean {
  const meta = actionInputMeta(entry, userInputByField);
  if (meta.source === "auth-session") {
    return false;
  }
  if (hasVisibleActionInputField(entry, userInputByField)) {
    return false;
  }
  if (meta.systemGenerated || meta.serverAssigned || meta.valueSource === "system-generated" || meta.valueSource === "server-default") {
    return false;
  }
  return meta.source === "workflow-context" || meta.source === "response-binding" || meta.valueSource === "workflow-context" || meta.valueSource === "response-binding";
}

function actionInputNeedsUserEntry(entry: ActionInputSource, userInputByField?: Map<string, UserInput>): boolean {
  const meta = actionInputMeta(entry, userInputByField);
  if (meta.source === "auth-session") {
    return false;
  }
  if (hasVisibleActionInputField(entry, userInputByField)) {
    return true;
  }
  if (meta.systemGenerated || meta.serverAssigned || meta.valueSource === "system-generated" || meta.valueSource === "server-default") {
    return false;
  }
  if (actionInputNeedsWorkflowContext(entry, userInputByField)) {
    return false;
  }
  return meta.source === "user-input" && meta.editability !== "hidden" && meta.editability !== "readonly" && meta.editability !== "derived";
}

function missingActionInputGuidance(missing: ActionInputSource[], userInputByField?: Map<string, UserInput>): string {
  const visibleInputs = missing
    .filter((item) => actionInputNeedsUserEntry(item, userInputByField))
    .map((item) => fieldLabel(item.field));
  const carriedContext = missing
    .filter((item) => actionInputNeedsWorkflowContext(item, userInputByField))
    .map((item) => fieldLabel(item.field));
  if (carriedContext.length > 0) {
    return zhLocale
      ? `这次提交仍缺少上一步生成的数据：${carriedContext.join("、")}。请先完成前一步，或重新加载当前记录后再安全重试。`
      : `This action still needs saved context: ${carriedContext.join(", ")}. Finish the earlier page or reload the current record, then retry safely.`;
  }
  if (visibleInputs.length > 0) {
    return zhLocale
      ? `这次提交还缺少以下输入：${visibleInputs.join("、")}。请补全后再安全重试。`
      : `This action still needs: ${visibleInputs.join(", ")}. Fill in the missing fields and retry safely.`;
  }
  return zhLocale
    ? "这次提交缺少必需输入来源。请先核对当前工作流上下文，再安全重试。"
    : "This action is missing required context. Review the current record and retry safely.";
}

function readinessGuidance(status: string, blockedReason: string, label: string): string {
  const reasonSuffix = blockedReason
    ? (zhLocale ? `原因：${blockedReason}` : `Reason: ${blockedReason}`)
    : "";
  if (status === "review-bound") {
    return zhLocale
      ? ["这一步当前仍在复核中，暂时还不能直接执行。", reasonSuffix].filter(Boolean).join(" ")
      : ["This action is not available yet.", reasonSuffix].filter(Boolean).join(" ");
  }
  if (status === "stale") {
    return zhLocale
      ? ["这一步正在等待最新校验后的实现绑定，当前还不能继续。", reasonSuffix].filter(Boolean).join(" ")
      : ["This action is refreshing to the latest available state before it can continue.", reasonSuffix].filter(Boolean).join(" ");
  }
  if (status === "blocked") {
    return zhLocale
      ? [`${label || "当前动作"}暂时被阻断，完成前置条件后才能继续。`, reasonSuffix].filter(Boolean).join(" ")
      : [`${label || "This action"} is blocked until the required prerequisites are available.`, reasonSuffix].filter(Boolean).join(" ");
  }
  return zhLocale
    ? ["这一步当前不可执行。", reasonSuffix].filter(Boolean).join(" ")
    : ["This step is not executable yet.", reasonSuffix].filter(Boolean).join(" ");
}

export default function __COMPONENT_NAME__() {
  const [formState, setFormState] = useState<Record<string, string>>(() =>
    ({
      ...Object.fromEntries(userInputs.map((item) => [item.field, ""])),
      ...readWorkflowContext(),
    }),
  );
  const [uiState, setUiState] = useState<"idle" | "loading" | "success" | "empty" | "error">("idle");
  const [httpStatus, setHttpStatus] = useState<number | null>(null);
  const [responseBody, setResponseBody] = useState("");
  const [errorText, setErrorText] = useState("");
  const actionableActions = actionsAndTransitions.filter((action) => Boolean(action.api_binding?.path));
  const [activeActionIndex, setActiveActionIndex] = useState(0);
  const activeAction = actionableActions[activeActionIndex] ?? null;
  const userInputByField = useMemo(
    () => new Map(userInputs.map((item) => [item.field, item])),
    [],
  );
  const primaryRequest = activeAction?.api_binding?.path
    ? {
        source: "api",
        method: activeAction.api_binding.method || primaryApiBinding?.method || "GET",
        path: activeAction.api_binding.path,
        purpose: activeAction.action,
        interaction_id: activeAction.interaction_id,
        service_binding_id: activeAction.service_binding_id,
        domain_service: "",
        binding_mode: activeAction.binding_mode,
        trigger_kind: activeAction.trigger_kind,
      }
    : (primaryApiBinding ?? dataRequired[0] ?? null);
  const primaryActionLabel = primaryCta.label || activeAction?.action || actionsAndTransitions[0]?.action || "Continue";
  const [currentRole, setCurrentRole] = useState<string>(String(appContext.current_session_role || allowedRoles[0] || ""));
  useEffect(() => {
    const stored = readRoleSession();
    if (stored.currentRole) {
      setCurrentRole(stored.currentRole);
    }
  }, []);
  const effectiveRole = currentRole || String(appContext.current_session_role || allowedRoles[0] || "");
  const pageRoleAccess = appContext.read_only_vs_editable_by_role?.[pageRoute] ?? readOnlyByRole;
  const pageEditableRoles = pageRoleAccess?.editable_roles ?? [];
  const pageReadOnlyRoles = pageRoleAccess?.read_only_roles ?? [];
  const pageReadOnly = Boolean(effectiveRole && pageReadOnlyRoles.includes(effectiveRole) && !pageEditableRoles.includes(effectiveRole));
  const [workflowProgress, setWorkflowProgress] = useState<WorkflowProgress>(() => readWorkflowProgress());
  useEffect(() => {
    setWorkflowProgress(readWorkflowProgress());
    if (typeof window === "undefined") {
      return;
    }
    const syncProgress = () => {
      setWorkflowProgress(readWorkflowProgress());
    };
    window.addEventListener(WORKFLOW_PROGRESS_EVENT, syncProgress);
    return () => window.removeEventListener(WORKFLOW_PROGRESS_EVENT, syncProgress);
  }, []);
  const contextualNav = contextualNavForRole(pageRoute, effectiveRole) ?? {};
  const nextStepCta = nextStepCtaForRole(pageRoute, effectiveRole) ?? {};
  const placemaking = placemakingForRole(pageRoute, effectiveRole) ?? {};
  const routeReachability = reachabilityForRole(pageRoute, effectiveRole) ?? {};
  void placemaking;
  const roleEntryRoute = cleanContractText(routeReachability.entry_route || appContext.role_scoped_entry_routes?.[effectiveRole] || "");
  useEffect(() => {
    if (!effectiveRole) {
      return;
    }
    initializeWorkflowProgress(effectiveRole, roleEntryRoute || pageRoute);
    setWorkflowProgress(markWorkflowRouteVisited(effectiveRole, pageRoute));
  }, [effectiveRole, roleEntryRoute]);
  const resolvedNextRole = cleanContractText(nextStepCta.target_role || effectiveRole || "");
  const suppressCrossRoleNextRoute = nextStepCta.kind === "handoff-summary";
  const resolvedNextRoute = cleanContractText(suppressCrossRoleNextRoute ? "" : (nextStepCta.target_route || contextualNav.next_route || navigation.next_route || ""));
  const resolvedNextLabel = cleanContractText(suppressCrossRoleNextRoute ? "" : (nextStepCta.target_label || contextualNav.next_label || friendlyRouteLabel(resolvedNextRoute)));

  function isRouteUnlockedForRole(route: string, role: string): boolean {
    const normalizedRoute = String(route || "").trim();
    const normalizedRole = String(role || "").trim();
    if (!normalizedRoute) {
      return false;
    }
    const routePolicy = reachabilityForRole(normalizedRoute, normalizedRole) ?? {};
    const entryRoute = cleanContractText(
      routePolicy.entry_route
      || appContext.role_scoped_entry_routes?.[normalizedRole]
      || "",
    );
    const reachabilityMode = cleanContractText(routePolicy.reachability_mode || "");
    if (reachabilityMode === "hidden") {
      return false;
    }
    if (normalizedRoute === pageRoute || normalizedRoute === entryRoute || Boolean(routePolicy.reachable_by_default)) {
      return true;
    }
    if (reachabilityMode && reachabilityMode !== "flow") {
      return true;
    }
    return workflowProgressForRole(workflowProgress, normalizedRole).unlockedRoutes.includes(normalizedRoute);
  }

  const nextRouteUnlocked = !resolvedNextRoute || isRouteUnlockedForRole(resolvedNextRoute, resolvedNextRole || effectiveRole) || uiState === "success";

  function actionLabel(action: SurfaceAction | null | undefined, fallback = "Continue") {
    const primary = cleanContractText(primaryCta.label || "");
    const raw = cleanContractText(action?.action || "");
    if (primary && (!raw || raw === primary || raw.length > 40 || raw.includes("->"))) {
      return primary;
    }
    if (raw.includes("->")) {
      return raw.split("->")[0].trim();
    }
    return raw || primary || fallback;
  }

  function renderNextStepAction(): ReactNode {
    if (!resolvedNextRoute) {
      return null;
    }
    const defaultLabel = cleanContractText(
      resolvedNextLabel || friendlyRouteLabel(resolvedNextRoute),
      zhLocale ? "继续处理" : "Open next task",
    );
    if (!nextRouteUnlocked) {
      return (
        <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 10, padding: "10px 14px", border: "1px solid #d5d9e2", background: "#f8fafc", color: "#475569" }}>
          {routeReachability.locked_reason || (zhLocale ? "完成当前步骤后，下一步才会解锁。" : "Complete the current step to unlock the next page.")}
        </span>
      );
    }
    return (
      <a href={resolvedNextRoute} style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 10, padding: "10px 14px", border: "1px solid #0f766e", background: "#0f766e", textDecoration: "none", color: "#fff" }}>
        {nextStepCta.label || defaultLabel}
      </a>
    );
  }

  const currentInteraction = useMemo(() => {
    const interactionId = cleanContractText(activeAction?.interaction_id || primaryRequest?.interaction_id || "");
    if (interactionId) {
      const exact = compiledInteractions.find((item) => cleanContractText(item.interaction_id) === interactionId);
      if (exact) {
        return exact;
      }
    }
    const serviceBindingId = cleanContractText(activeAction?.service_binding_id || primaryRequest?.service_binding_id || "");
    if (serviceBindingId) {
      const exact = compiledInteractions.find((item) => cleanContractText(item.service_binding_id) === serviceBindingId);
      if (exact) {
        return exact;
      }
    }
    const requestPath = cleanContractText(activeAction?.api_binding?.path || primaryRequest?.path || "");
    const requestMethod = cleanContractText(activeAction?.api_binding?.method || primaryRequest?.method || "").toUpperCase();
    if (requestPath) {
      const exact = compiledInteractions.find((item) => {
        const candidatePath = cleanContractText(item.api_endpoint || "");
        const candidateMethod = cleanContractText(item.http_method || "").toUpperCase();
        return candidatePath === requestPath && (!requestMethod || !candidateMethod || candidateMethod === requestMethod);
      });
      if (exact) {
        return exact;
      }
    }
    if (activeAction) {
      return compiledInteractions.find((item) => cleanContractText(item.trigger_kind || "") !== "page_load") || compiledInteractions[0] || null;
    }
    return compiledInteractions.find((item) => cleanContractText(item.trigger_kind || "") === "page_load") || compiledInteractions[0] || null;
  }, [activeAction, primaryRequest, compiledInteractions]);
  const currentInteractionReadiness = normalizeReadiness(currentInteraction?.readiness_status || activeAction?.readiness_status);
  const currentInteractionBlockedReason = cleanContractText(currentInteraction?.blocked_reason || activeAction?.blocked_reason || "");
  const currentInteractionUnavailable = Boolean((currentInteraction || activeAction) && currentInteractionReadiness !== "ready");
  const lifecycleInteraction = useMemo(
    () => compiledInteractions.find((item) => isLifecycleTrigger(item.trigger_kind)) || null,
    [compiledInteractions],
  );
  const lifecycleRequest = useMemo(() => {
    const compiledRequest = requestFromCompiledInteraction(lifecycleInteraction);
    if (compiledRequest) {
      return compiledRequest;
    }
    return dataRequired.find((item) => isLifecycleTrigger(item.trigger_kind)) ?? null;
  }, [lifecycleInteraction, dataRequired]);
  const trimmedValues = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(formState).map(([key, value]) => [key, value.trim()]),
      ),
    [formState],
  );
  const parsedResponse = useMemo(() => parseBody(responseBody), [responseBody]);
  const responseRows = useMemo(() => flattenRows(parsedResponse.envelopeData), [parsedResponse]);
  const responseRecord = useMemo(
    () => (isRecord(parsedResponse.envelopeData) ? parsedResponse.envelopeData : null),
    [parsedResponse],
  );
  const activeFieldNames = useMemo(() => {
    const ordered = [
      ...(activeAction?.required_fields ?? []),
      ...(activeAction?.optional_fields ?? []),
    ]
      .map((field) => String(field).trim())
      .filter(Boolean);
    return Array.from(new Set(ordered));
  }, [activeAction]);
  const activeInputs = useMemo(() => {
    if (activeFieldNames.length === 0) {
      return userInputs;
    }
    return activeFieldNames
      .map((field) => userInputByField.get(field))
      .filter((item): item is UserInput => Boolean(item));
  }, [activeFieldNames, userInputByField]);
  const activeResultFields = useMemo(
    () =>
      activeAction?.result_fields && activeAction.result_fields.length > 0
        ? activeAction.result_fields.map((field) => String(field).trim()).filter(Boolean)
        : [...displayFields],
    [activeAction, displayFields],
  );
  const responseColumns = useMemo(
    () =>
      activeResultFields.length > 0
        ? [...activeResultFields]
        : Array.from(
            new Set(
              responseRows.flatMap((row) => Object.keys(row)),
            ),
          ),
    [activeResultFields, responseRows],
  );
  const detailFieldOrder = useMemo(
    () =>
      activeResultFields.length > 0
        ? activeResultFields
        : responseRecord
          ? Object.keys(responseRecord)
          : [],
    [activeResultFields, responseRecord],
  );
  const autoLoadRequest = lifecycleRequest ?? (!activeAction ? primaryRequest : null);
  const autoLoadInteraction = lifecycleInteraction ?? (!activeAction && isLifecycleTrigger(primaryRequest?.trigger_kind || "") ? currentInteraction : null);
  const autoLoadInterpolated = useMemo(
    () => autoLoadRequest ? interpolatePath(autoLoadRequest.path || "/", trimmedValues) : { path: "", remaining: {} },
    [autoLoadRequest, trimmedValues],
  );
  const autoLoadHasMappedContext = useMemo(
    () => hasMappedRequestContext(autoLoadInteraction, trimmedValues),
    [autoLoadInteraction, trimmedValues],
  );
  const autoLoadAllowed = Boolean(
    autoLoadRequest
    && isLifecycleTrigger(autoLoadRequest.trigger_kind || autoLoadInteraction?.trigger_kind || "")
    && autoLoadHasMappedContext
    && (autoLoadRequest.method || "GET").toUpperCase() === "GET"
    && !autoLoadInterpolated.path.includes("{")
    && normalizeReadiness(autoLoadInteraction?.readiness_status) === "ready",
  );
  const refreshRequest = (
    lifecycleRequest && (lifecycleRequest.method || "GET").toUpperCase() === "GET"
      ? lifecycleRequest
      : (primaryRequest && (primaryRequest.method || "GET").toUpperCase() === "GET" ? primaryRequest : null)
  );
  const refreshInteraction = refreshRequest === lifecycleRequest ? lifecycleInteraction : currentInteraction;
  const refreshUnavailable = Boolean(
    (refreshInteraction || (refreshRequest !== lifecycleRequest ? activeAction : null))
    && normalizeReadiness(refreshInteraction?.readiness_status || (refreshRequest !== lifecycleRequest ? activeAction?.readiness_status : "")) !== "ready",
  );
  const summaryCardBindings = useMemo(() => {
    const labels = summaryCardsContract.length > 0 ? summaryCardsContract : displayFields.slice(0, 4);
    const candidateFields = displayFields.length > 0 ? displayFields : detailFieldOrder;
    return labels
      .map((label, index) => ({
        label,
        field: candidateFields[index] || candidateFields[0] || "",
        }))
      .filter((item) => item.label);
  }, [summaryCardsContract, displayFields, detailFieldOrder]);
  const tableBindings = useMemo(() => {
    const availableFields = responseColumns.length > 0 ? responseColumns : displayFields;
    if (tableColumnsContract.length > 0) {
      return tableColumnsContract
        .map((label, index) => ({
          label,
          field: availableFields[index] || availableFields[0] || "",
        }))
        .filter((item) => item.field);
    }
    return availableFields.map((field) => ({
      label: fieldLabel(field),
      field,
    }));
  }, [tableColumnsContract, responseColumns, displayFields]);
  const loadingLabel = primaryRequest && (primaryRequest.method || "GET").toUpperCase() === "GET" ? "Loading..." : "Saving...";
  const setupFlowSteps = useMemo(
    () =>
      actionableActions.map((action, index) => {
        const requiredSources = (action.required_input_sources ?? []).filter(
          (entry): entry is ActionInputSource => Boolean(entry?.field && entry?.source),
        );
        const missingVisible: string[] = [];
        const missingContext: string[] = [];
        for (const entry of requiredSources) {
          const field = String(entry.field || "").trim();
          if (!field) {
            continue;
          }
          const currentValue = contractValue(field, parsedResponse.envelopeData, responseRecord, trimmedValues).trim();
          if (currentValue) {
            continue;
          }
          if (actionInputNeedsUserEntry(entry, userInputByField)) {
            missingVisible.push(fieldLabel(field));
          } else if (actionInputNeedsWorkflowContext(entry, userInputByField)) {
            missingContext.push(fieldLabel(field));
          }
        }
        return {
          index,
          action,
          missingVisible,
          missingContext,
        };
      }),
    [actionableActions, parsedResponse.envelopeData, responseRecord, trimmedValues, userInputByField],
  );
  const activeSetupStep = setupFlowSteps[activeActionIndex] ?? null;
  const sectionsByView = useMemo(() => {
    const grouped: Record<string, PageSection[]> = {};
    for (const section of sections) {
      const view = String(section.view || "").trim().toLowerCase() || "detail";
      grouped[view] = grouped[view] ?? [];
      grouped[view].push(section);
    }
    return grouped;
  }, [sections]);

  useEffect(() => {
    persistWorkflowContext(
      Object.fromEntries(
        Object.entries(formState).filter(([, value]) => value.trim().length > 0),
      ),
    );
  }, [formState]);

  function applyResponseBindings(action: SurfaceAction | null | undefined, envelopeData: unknown): void {
    const bindings = action?.response_bindings ?? [];
    if (bindings.length === 0) {
      return;
    }
    setFormState((current) => {
      const next = { ...current };
      let changed = false;
      for (const binding of bindings) {
        const from = String(binding.from || "").trim();
        const to = String(binding.to || "").trim();
        if (!from || !to) {
          continue;
        }
        const rawValue = readBindingValue(envelopeData, from);
        const value = textValue(rawValue);
        if (!value) {
          continue;
        }
        if (next[to] === value) {
          continue;
        }
        next[to] = value;
        changed = true;
      }
      return changed ? next : current;
    });
  }

  async function runBoundAction(
    action?: SurfaceAction | null,
    overrides?: { request?: DataRequired | null; interaction?: CompiledInteraction | null },
  ): Promise<void> {
    const boundRequest = overrides?.request ?? (
      action?.api_binding?.path
      ? {
          source: "api",
          method: action.api_binding.method || primaryApiBinding?.method || "GET",
          path: action.api_binding.path,
          purpose: action.action,
          interaction_id: action.interaction_id,
          service_binding_id: action.service_binding_id,
          domain_service: "",
          binding_mode: action.binding_mode,
          trigger_kind: action.trigger_kind,
        }
      : primaryRequest
    );
    const interactionMeta = overrides?.interaction ?? (() => {
      const interactionId = cleanContractText(action?.interaction_id || boundRequest?.interaction_id || "");
      if (interactionId) {
        const exact = compiledInteractions.find((item) => cleanContractText(item.interaction_id) === interactionId);
        if (exact) {
          return exact;
        }
      }
      const serviceBindingId = cleanContractText(action?.service_binding_id || boundRequest?.service_binding_id || "");
      if (serviceBindingId) {
        const exact = compiledInteractions.find((item) => cleanContractText(item.service_binding_id) === serviceBindingId);
        if (exact) {
          return exact;
        }
      }
      const requestPath = cleanContractText(action?.api_binding?.path || boundRequest?.path || "");
      const requestMethod = cleanContractText(action?.api_binding?.method || boundRequest?.method || "").toUpperCase();
      if (requestPath) {
        return compiledInteractions.find((item) => {
          const candidatePath = cleanContractText(item.api_endpoint || "");
          const candidateMethod = cleanContractText(item.http_method || "").toUpperCase();
          return candidatePath === requestPath && (!requestMethod || !candidateMethod || candidateMethod === requestMethod);
        }) ?? null;
      }
      return null;
    })();
    const interactionReadiness = normalizeReadiness(interactionMeta?.readiness_status || action?.readiness_status);
    const interactionBlockedReason = cleanContractText(interactionMeta?.blocked_reason || action?.blocked_reason || "");
    if (!boundRequest) {
      setUiState("error");
      setErrorText("This page is waiting for its primary data binding.");
      setResponseBody("");
      setHttpStatus(null);
      return;
    }
    if ((interactionMeta || action) && interactionReadiness !== "ready") {
      setUiState("error");
      setErrorText(readinessGuidance(interactionReadiness, interactionBlockedReason, action?.action || primaryActionLabel));
      setResponseBody("");
      setHttpStatus(null);
      return;
    }
    const method = (boundRequest.method || "GET").toUpperCase();
    if (pageReadOnly && method !== "GET") {
      setUiState("error");
      setErrorText("This role can review current data but cannot submit changes on this page.");
      setResponseBody("");
      setHttpStatus(null);
      return;
    }
    const requiredInputSources = (action?.required_input_sources ?? []).filter(
      (entry): entry is ActionInputSource => Boolean(entry?.field && entry?.source),
    );
    const missingInputs = requiredInputSources.filter((entry) => {
      const field = String(entry.field || "").trim();
      if (!field) {
        return false;
      }
      if (!actionInputNeedsUserEntry(entry, userInputByField) && !actionInputNeedsWorkflowContext(entry, userInputByField)) {
        return false;
      }
      return !contractValue(field, parsedResponse.envelopeData, responseRecord, trimmedValues).trim();
    });
    if (missingInputs.length > 0) {
      setUiState("error");
      setErrorText(missingActionInputGuidance(missingInputs, userInputByField));
      setResponseBody("");
      setHttpStatus(null);
      return;
    }
    const activeValues = Object.fromEntries(
      Object.entries(trimmedValues).filter(([, value]) => value.length > 0),
    );
    const interpolated = interpolatePath(boundRequest.path || "/", activeValues);
    if (interpolated.path.includes("{")) {
      setUiState("error");
      setErrorText("Required path parameters are still missing.");
      return;
    }
    const url = new URL(interpolated.path, "http://phase3.local");
    const mappedRequest = buildMappedRequest(interactionMeta, activeValues);
    let init: globalThis.RequestInit = { method };
    if (method === "GET" || method === "DELETE") {
      const queryPayload = Object.keys(mappedRequest.query).length > 0 ? mappedRequest.query : interpolated.remaining;
      for (const [key, value] of Object.entries(queryPayload)) {
        if (value) {
          url.searchParams.set(key, value);
        }
      }
    } else {
      const bodyPayload = Object.keys(mappedRequest.body).length > 0 ? mappedRequest.body : interpolated.remaining;
      init = {
        method,
        headers: { "content-type": "application/json" },
        body: JSON.stringify(bodyPayload),
      };
    }
    setUiState("loading");
    setErrorText("");
    try {
      const response = await callApi(url.pathname + url.search, init);
      setHttpStatus(response.status);
      setResponseBody(response.body);
      const parsed = parseBody(response.body);
      if (response.status >= 400) {
        setUiState("error");
        setErrorText(recoveryGuidance(response.status));
        return;
      }
      applyResponseBindings(action, parsed.envelopeData);
      if (effectiveRole) {
        setWorkflowProgress(markWorkflowRouteVisited(effectiveRole, pageRoute));
      }
      const continuationRoute = cleanContractText(
        nextStepCta.target_route
        || contextualNav.next_route
        || action?.next_route
        || interactionMeta?.next_route
        || navigation.next_route
        || "",
      );
      const continuationRole = cleanContractText(nextStepCta.target_role || effectiveRole || "");
      if (continuationRoute && continuationRole) {
        setWorkflowProgress(unlockWorkflowRoute(continuationRole, continuationRoute));
      }
      if (hasRenderableData(parsed.envelopeData)) {
        setUiState("success");
        return;
      }
      setUiState("empty");
    } catch (error) {
      setUiState("error");
      setErrorText(String(error));
      setHttpStatus(null);
      setResponseBody("");
    }
  }

  useEffect(() => {
    if (autoLoadAllowed && uiState === "idle") {
      void runBoundAction(null, { request: autoLoadRequest, interaction: autoLoadInteraction });
    }
  }, [autoLoadAllowed, autoLoadInteraction, autoLoadRequest, uiState]);

  function renderActionButtons() {
    if (String(pageBlueprintType) === "setup-flow" && activeAction) {
      const currentStepLabel = primaryActionLabel;
      const disabled = Boolean(
        uiState === "loading"
        || !activeAction.api_binding?.path
        || currentInteractionUnavailable
        || (pageReadOnly && (activeAction.api_binding?.method || "GET").toUpperCase() !== "GET")
        || (activeSetupStep && (activeSetupStep.missingVisible.length > 0 || activeSetupStep.missingContext.length > 0)),
      );
      return (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            key={activeAction.action + String(activeAction.api_binding?.path || activeActionIndex)}
            type="button"
            disabled={disabled}
            onClick={() => {
              void runBoundAction(activeAction);
            }}
            style={{
              fontWeight: 700,
              borderRadius: 10,
              border: "1px solid #0f766e",
              background: "#0f766e",
              color: "#fff",
              padding: "10px 16px",
            }}
          >
            {uiState === "loading" ? loadingLabel : currentStepLabel}
          </button>
          {refreshRequest ? (
            <button
              type="button"
              disabled={uiState === "loading" || refreshUnavailable}
              onClick={() => {
                void runBoundAction(
                  refreshRequest === lifecycleRequest ? null : activeAction,
                  { request: refreshRequest, interaction: refreshInteraction },
                );
              }}
              style={{ borderRadius: 10, border: "1px solid #d5d9e2", background: "#fff", padding: "10px 14px" }}
            >
              {secondaryCta.label || "Refresh current data"}
            </button>
          ) : null}
        </div>
      );
    }
    return (
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {actionableActions.length > 0 ? (
          actionableActions.map((action, index) => {
            const actionRequestMethod = (action.api_binding?.method || "GET").toUpperCase();
            const isActive = index === activeActionIndex;
            const actionLoadingLabel = actionRequestMethod === "GET" ? "Loading..." : "Saving...";
            const actionUnavailable = Boolean(normalizeReadiness(action.readiness_status) !== "ready");
            return (
              <button
                key={action.action + String(action.api_binding?.path || index)}
                type="button"
                disabled={uiState === "loading" || !action.api_binding?.path || actionUnavailable || (pageReadOnly && actionRequestMethod !== "GET")}
                onClick={() => {
                  setActiveActionIndex(index);
                  void runBoundAction(action);
                }}
                style={{
                  fontWeight: isActive ? 700 : 500,
                  borderRadius: 10,
                  border: isActive ? "1px solid #0f766e" : "1px solid #d5d9e2",
                  background: isActive ? "#ecfeff" : "#fff",
                  padding: "10px 14px",
                }}
              >
                {uiState === "loading" && isActive ? actionLoadingLabel : actionLabel(action, primaryActionLabel)}
              </button>
            );
          })
        ) : (
          <button
            type="submit"
            disabled={uiState === "loading" || !primaryRequest || currentInteractionUnavailable || (pageReadOnly && (primaryRequest?.method || "GET").toUpperCase() !== "GET")}
            style={{
              fontWeight: 700,
              borderRadius: 12,
              border: "1px solid #0f766e",
              background: "#0f766e",
              color: "#fff",
              padding: "12px 18px",
            }}
          >
            {uiState === "loading" ? loadingLabel : primaryActionLabel}
          </button>
        )}
        {refreshRequest ? (
          <button
            type="button"
            disabled={uiState === "loading" || refreshUnavailable}
            onClick={() => {
              void runBoundAction(
                refreshRequest === lifecycleRequest ? null : activeAction,
                { request: refreshRequest, interaction: refreshInteraction },
              );
            }}
            style={{ borderRadius: 10, border: "1px solid #d5d9e2", background: "#fff", padding: "10px 14px" }}
          >
            {secondaryCta.label || "Refresh current data"}
          </button>
        ) : null}
      </div>
    );
  }

  function inputValue(item: UserInput): string {
    return formState[item.field] ?? "";
  }

  function setInputValue(field: string, value: string): void {
    setFormState((current) => ({ ...current, [field]: value }));
  }

  function shouldHideInput(item: UserInput): boolean {
    return item.editability === "hidden" || item.control === "hidden";
  }

  function shouldRenderReadOnlyInput(item: UserInput): boolean {
    return !shouldHideInput(item) && (
      item.editability === "readonly"
      || item.value_source === "workflow-context"
      || item.value_source === "response-binding"
      || item.value_source === "system-generated"
      || Boolean(item.system_generated)
      || Boolean(item.server_assigned)
    );
  }

  function controlPlaceholder(item: UserInput): string {
    if (item.placeholder) {
      return item.placeholder;
    }
    if (item.control === "lookup" && item.lookup_entity) {
      return zhLocale ? `搜索${friendlyLabel(item.lookup_entity)}` : `Search ${friendlyLabel(item.lookup_entity)}`;
    }
    return item.validation || (zhLocale ? "请输入值" : "Enter value");
  }

  function renderEditableControl(item: UserInput, compact = false): ReactNode {
    const value = inputValue(item);
    const options = item.options ?? [];
    const baseStyle = {
      padding: compact ? "10px 12px" : "12px 14px",
      borderRadius: 10,
      border: "1px solid #cbd5e1",
      background: "#fff",
    };
    if (item.control === "textarea") {
      return (
        <textarea
          value={value}
          disabled={pageReadOnly}
          onChange={(event) => setInputValue(item.field, event.target.value)}
          placeholder={controlPlaceholder(item)}
          rows={compact ? 3 : 5}
          style={{ ...baseStyle, resize: "vertical" }}
        />
      );
    }
    if (item.control === "checkbox") {
      return (
        <label style={{ display: "flex", gap: 10, alignItems: "center", minHeight: compact ? 42 : 48 }}>
          <input
            type="checkbox"
            checked={value === "true"}
            disabled={pageReadOnly}
            onChange={(event) => setInputValue(item.field, event.target.checked ? "true" : "false")}
          />
          <span>{item.helper || item.validation || (zhLocale ? "切换此项" : "Toggle this field")}</span>
        </label>
      );
    }
    if (item.control === "select" || (item.control === "lookup" && options.length > 0)) {
      return (
        <select
          value={value}
          disabled={pageReadOnly}
          onChange={(event) => setInputValue(item.field, event.target.value)}
          style={baseStyle}
        >
          <option value="">{zhLocale ? "请选择" : "Choose an option"}</option>
          {options.map((option) => (
            <option key={`${item.field}-${option.value}`} value={option.value}>{option.label || option.value}</option>
          ))}
        </select>
      );
    }
    if (item.control === "number") {
      return (
        <input
          type="number"
          inputMode="decimal"
          step={item.datatype === "integer" ? "1" : "any"}
          value={value}
          disabled={pageReadOnly}
          onChange={(event) => setInputValue(item.field, event.target.value)}
          placeholder={controlPlaceholder(item)}
          style={baseStyle}
        />
      );
    }
    if (item.control === "date") {
      return (
        <input
          type="date"
          value={value}
          disabled={pageReadOnly}
          onChange={(event) => setInputValue(item.field, event.target.value)}
          style={baseStyle}
        />
      );
    }
    if (item.control === "datetime") {
      return (
        <input
          type="datetime-local"
          value={value}
          disabled={pageReadOnly}
          onChange={(event) => setInputValue(item.field, event.target.value)}
          style={baseStyle}
        />
      );
    }
    if (item.control === "lookup") {
      return (
        <input
          type="search"
          value={value}
          disabled={pageReadOnly}
          onChange={(event) => setInputValue(item.field, event.target.value)}
          placeholder={controlPlaceholder(item)}
          style={baseStyle}
        />
      );
    }
    return (
      <input
        type="text"
        value={value}
        disabled={pageReadOnly}
        onChange={(event) => setInputValue(item.field, event.target.value)}
        placeholder={controlPlaceholder(item)}
        style={baseStyle}
      />
    );
  }

  function renderInputField(item: UserInput, variant: "form" | "filter"): ReactNode | null {
    if (shouldHideInput(item)) {
      return null;
    }
    const compact = variant === "filter";
    const labelText = item.label || fieldLabel(item.field);
    const helperText = item.helper || item.validation || (item.lookup_entity ? (zhLocale ? `关联 ${friendlyLabel(item.lookup_entity)}` : `Reference ${friendlyLabel(item.lookup_entity)}`) : "");
    const currentValue = contractValue(item.field, parsedResponse.envelopeData, responseRecord, trimmedValues) || inputValue(item) || shellCopy.pending_live_data;
    const containerStyle = compact
      ? { display: "grid", gap: 6 }
      : { display: "grid", gap: 8, padding: 14, border: "1px solid #e2e8f0", borderRadius: 14, background: "#fff", ...(item.control === "textarea" ? { gridColumn: "1 / -1" } : {}) };
    if (shouldRenderReadOnlyInput(item)) {
      return (
        <div key={item.field} style={containerStyle}>
          <span style={{ fontWeight: 600 }}>{labelText}</span>
          <div style={{ padding: compact ? "10px 12px" : "12px 14px", borderRadius: 10, border: "1px solid #dbe4f0", background: "#f8fafc", color: "#0f172a", fontWeight: 600 }}>
            {currentValue}
          </div>
          <small style={{ color: "#64748b" }}>
            {helperText || (item.value_source === "workflow-context" ? (zhLocale ? "该值会沿用当前记录上下文。" : "This value is carried from the current record context.") : "")}
          </small>
        </div>
      );
    }
    return (
      <label key={item.field} style={containerStyle}>
        <span>
          <strong>{labelText}</strong> {variant === "form" ? (item.required ? "(required)" : "(optional)") : null}
        </span>
        {renderEditableControl(item, compact)}
        {helperText ? <small style={{ color: "#64748b" }}>{helperText}</small> : null}
      </label>
    );
  }

  function renderScopedInputs(section: PageSection) {
    const sectionFieldSet = new Set((section.bind_fields ?? []).map((field) => String(field).trim()).filter(Boolean));
    const scopedInputs = sectionFieldSet.size > 0
      ? activeInputs.filter((item) => sectionFieldSet.has(item.field))
      : activeInputs;
    const effectiveInputs = scopedInputs.length > 0 ? scopedInputs : activeInputs;
    const grouped = new Map<string, UserInput[]>();
    for (const item of effectiveInputs) {
      const group = item.group || (item.required ? "Primary input" : "Optional input");
      const current = grouped.get(group) ?? [];
      current.push(item);
      grouped.set(group, current);
    }
    const groupedEntries = Array.from(grouped.entries());
    const genericGroupNames = new Set(["Primary input", "Optional input", "主要输入", "可选输入", "Record lookup", "记录查找"]);
    return (
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void runBoundAction(activeAction);
        }}
        style={{ display: "grid", gap: 20 }}
      >
        {groupedEntries.map(([groupName, items], index) => {
          const renderedItems = items
            .map((item) => renderInputField(item, "form"))
            .filter((node): node is ReactNode => node !== null);
          if (renderedItems.length === 0) {
            return null;
          }
          const shouldCollapseGroupShell = groupedEntries.length === 1 && genericGroupNames.has(groupName);
          if (shouldCollapseGroupShell) {
            return (
              <div key={`${groupName}-${index}`} style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", alignItems: "start" }}>
                {renderedItems}
              </div>
            );
          }
          return (
            <fieldset key={groupName} style={{ border: "1px solid #dbe4f0", borderRadius: 18, padding: 20, display: "grid", gap: 16, background: "#f8fafc" }}>
              <legend style={{ padding: "0 10px", fontWeight: 700 }}>{groupName}</legend>
              <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", alignItems: "start" }}>
                {renderedItems}
              </div>
            </fieldset>
          );
        })}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, flexWrap: "wrap" }}>
          {renderActionButtons()}
        </div>
      </form>
    );
  }

  function renderFilterControls(fields: readonly string[]) {
    const fieldSet = new Set(fields.map((field) => String(field).trim()).filter(Boolean));
    const scopedInputs = fieldSet.size > 0
      ? activeInputs.filter((item) => fieldSet.has(item.field))
      : activeInputs;
    const effectiveInputs = scopedInputs.length > 0 ? scopedInputs : activeInputs;
    const renderedInputs = effectiveInputs
      .slice(0, 6)
      .map((item) => renderInputField(item, "filter"))
      .filter((node): node is ReactNode => node !== null);
    if (renderedInputs.length === 0) {
      return renderActionButtons();
    }
    return (
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void runBoundAction(activeAction);
        }}
        style={{ display: "grid", gap: 12 }}
      >
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
          {renderedInputs}
        </div>
        {renderActionButtons()}
      </form>
    );
  }

  function renderSetupFlowToolbar() {
    if (blueprintKind !== "setup-flow" || !activeAction) {
      return null;
    }
    const hasSetupSignals = setupFlowSteps.length > 1 || currentInteractionUnavailable;
    if (!hasSetupSignals) {
      return null;
    }
    return sectionShell(
      "Current action",
      <div style={{ display: "grid", gap: 14 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {setupFlowSteps.map((step) => {
            const selected = step.index === activeActionIndex;
            return (
              <button
                key={step.action.action + String(step.index)}
                type="button"
                onClick={() => {
                  setActiveActionIndex(step.index);
                }}
                style={{
                  borderRadius: 999,
                  border: selected ? "1px solid #0f766e" : "1px solid #d5d9e2",
                  background: selected ? "#ecfeff" : "#fff",
                  padding: "8px 12px",
                  fontWeight: selected ? 700 : 500,
                }}
              >
                {actionLabel(step.action, primaryActionLabel)}
              </button>
            );
          })}
        </div>
        <div style={{ display: "grid", gap: 8 }}>
          <strong>{primaryActionLabel}</strong>
          {currentInteractionUnavailable ? (
            <p style={{ margin: 0, color: "#b42318" }}>
              {readinessGuidance(currentInteractionReadiness, currentInteractionBlockedReason, activeAction.action)}
            </p>
          ) : null}
          {activeSetupStep?.missingVisible.length ? (
            <p style={{ margin: 0, color: "#b45309" }}>
              {zhLocale
                ? `提交前还需要填写：${activeSetupStep.missingVisible.join("、")}`
                : `Fill in these inputs before submitting: ${activeSetupStep.missingVisible.join(", ")}`}
            </p>
          ) : null}
          {activeSetupStep?.missingContext.length ? (
            <p style={{ margin: 0, color: "#1d4ed8" }}>
              {zhLocale
                ? `这一步还在等待上一步生成：${activeSetupStep.missingContext.join("、")}`
                : `This step is still waiting for the previous step to produce: ${activeSetupStep.missingContext.join(", ")}`}
            </p>
          ) : null}
__SETUP_ROUTE_HINTS__
        </div>
      </div>,
    );
  }

  function renderFieldList(fields: readonly string[]) {
    const items = fields
      .map((field) => {
        const normalized = String(field).trim();
        return {
          field: normalized,
          label: fieldLabel(normalized),
          value: contractValue(normalized, parsedResponse.envelopeData, responseRecord, trimmedValues),
        };
      })
      .filter((item) => item.field);
    if (items.length === 0) {
      return (
        <div style={{ border: "1px dashed #d1d5db", borderRadius: 12, padding: 16, background: "#fafafa" }}>
          <strong>{emptyState.headline}</strong>
          <p style={{ marginBottom: 0 }}>{emptyState.body}</p>
        </div>
      );
    }
    return (
      <dl style={{ display: "grid", gridTemplateColumns: "minmax(140px, 220px) 1fr", gap: 10 }}>
        {items.map((item) => (
          <div key={item.field} style={{ display: "contents" }}>
            <dt style={{ fontWeight: 600 }}>{item.label}</dt>
            <dd style={{ margin: 0 }}>{item.value || "—"}</dd>
          </div>
        ))}
      </dl>
    );
  }

  function pickSections(...views: string[]): PageSection[] {
    const ordered: PageSection[] = [];
    for (const view of views) {
      ordered.push(...(sectionsByView[String(view).trim().toLowerCase()] ?? []));
    }
    return ordered;
  }

  function firstSection(...views: string[]): PageSection | null {
    return pickSections(...views)[0] ?? null;
  }

  function fieldsForSection(section: PageSection | null | undefined, fallback: readonly string[] = []): string[] {
    const scoped = (section?.bind_fields ?? []).map((field) => String(field).trim()).filter(Boolean);
    return scoped.length > 0 ? scoped : [...fallback];
  }

  const setupSection = firstSection("form", "filter-bar");
  const summarySection = firstSection("summary-cards");
  const detailSection = firstSection("detail", "detail-list");
  const tableSection = firstSection("table", "list");
  const resultSection = firstSection("result");
  const nextStepSection = firstSection("next-steps");
  const summaryFields = fieldsForSection(summarySection, summaryCardBindings.map((item) => item.field));
  const detailFields = fieldsForSection(detailSection, detailFieldOrder);
  const resultFields = fieldsForSection(resultSection, detailFieldOrder);

  function hasResolvedFieldValue(field: string) {
    const value = contractValue(field, parsedResponse.envelopeData, responseRecord, trimmedValues);
    return Boolean(value && value !== shellCopy.pending_live_data && value !== "—");
  }

  function hasResolvedValues(fields: readonly string[]) {
    return fields.some((field) => hasResolvedFieldValue(field));
  }

  function sectionShell(title: string, body: ReactNode, aside?: ReactNode) {
    return (
      <section style={{ border: "1px solid #d9d9d9", borderRadius: 16, padding: 20, background: "#fff", display: "grid", gap: 16 }}>
        <div style={{ display: "grid", gap: 6 }}>
          <h2 style={{ margin: 0 }}>{title}</h2>
        </div>
        {body}
        {aside ?? null}
      </section>
    );
  }

  function presentPanels(panels: Array<ReactNode | null | undefined>) {
    return panels.filter((panel): panel is ReactNode => panel !== null && panel !== undefined);
  }

  function renderMetricStrip(title: string, fields: readonly string[]) {
    const effectiveFields = fields.length > 0 ? fields : summaryCardBindings.map((item) => item.field).filter(Boolean);
    if (effectiveFields.length === 0 || (!responseRecord && responseRows.length === 0 && !hasResolvedValues(effectiveFields))) {
      return null;
    }
    return sectionShell(
      title,
      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
        {effectiveFields.slice(0, 6).map((field) => (
          <article key={field} style={{ border: "1px solid #e2e8f0", borderRadius: 14, padding: 16, background: "#f8fafc" }}>
            <p style={{ margin: 0, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 12 }}>{fieldLabel(field)}</p>
            <h3 style={{ marginTop: 10, marginBottom: 0, fontSize: 18 }}>{contractValue(field, parsedResponse.envelopeData, responseRecord, trimmedValues) || shellCopy.pending_live_data}</h3>
          </article>
        ))}
      </div>,
    );
  }

  function renderDataTable(title: string, fields: readonly string[]) {
    const effectiveFields = fields.length > 0 ? fields : tableBindings.map((item) => item.field).filter(Boolean);
    if (responseRows.length === 0) {
      return sectionShell(
        title,
        responseRecord ? renderFieldList(effectiveFields) : (
          <div style={{ border: "1px dashed #d1d5db", borderRadius: 12, padding: 16, background: "#fafafa" }}>
            <strong>{emptyState.headline}</strong>
            <p style={{ marginBottom: 0 }}>{emptyState.body}</p>
          </div>
        ),
      );
    }
    return sectionShell(
      title,
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {effectiveFields.slice(0, 8).map((field) => (
                <th key={field} style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "8px 6px" }}>{fieldLabel(field)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {responseRows.map((row, index) => (
              <tr key={index}>
                {effectiveFields.slice(0, 8).map((field) => (
                  <td key={field} style={{ borderBottom: "1px solid #f0f0f0", padding: "8px 6px" }}>{textValue(row[field]) || "—"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>,
    );
  }

  function renderEvidenceDetails(title: string, fields: readonly string[]) {
    const effectiveFields = fields.length > 0 ? fields : detailFieldOrder;
    if (effectiveFields.length === 0 || (!responseRecord && responseRows.length === 0 && !hasResolvedValues(effectiveFields))) {
      return null;
    }
    return sectionShell(title, renderFieldList(effectiveFields));
  }

  function renderActionForm(title: string, section: PageSection | null) {
    if (section && String(section.view || "").toLowerCase() === "filter-bar") {
      return sectionShell(title, renderFilterControls(fieldsForSection(section, activeInputs.map((item) => item.field))));
    }
    return sectionShell(title, renderScopedInputs(section ?? { section_id: "generated-form", title, purpose: title, view: "form" }));
  }

  function renderStatusCard(title: string) {
    const showStatusDetails = currentInteractionUnavailable || uiState === "error";
    const shouldRenderCard = currentInteractionUnavailable || uiState === "loading" || uiState === "success" || uiState === "error" || uiState === "empty";
    if (!shouldRenderCard) {
      return null;
    }
    return sectionShell(
      title,
      <div style={{ display: "grid", gap: 12 }}>
        {currentInteractionUnavailable ? (
        <article style={{ border: "1px solid #fecaca", borderRadius: 12, padding: 14, background: "#fff1f2" }}>
            <strong>{zhLocale ? "动作状态" : "Action status"}</strong>
            <p style={{ marginBottom: 0 }}>
              {readinessGuidance(currentInteractionReadiness, currentInteractionBlockedReason, primaryActionLabel)}
            </p>
          </article>
        ) : null}
        <article style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, background: "#f8fafc" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <strong>{stateHeadline(uiState)}</strong>
            {showStatusDetails && httpStatus !== null ? <span>{"HTTP " + String(httpStatus)}</span> : null}
          </div>
          <p style={{ marginBottom: 0 }}>{errorText || stateBody(uiState)}</p>
          {showStatusDetails && requiredStatusMessages.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, color: "#475569" }}>
              {requiredStatusMessages.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          ) : null}
        </article>
      </div>,
    );
  }

  function renderOutcomeCard(title: string, fields: readonly string[]) {
    const effectiveFields = fields.length > 0 ? fields : detailFieldOrder.slice(0, 6);
    if (uiState !== "success" && !responseRecord && !hasResolvedValues(effectiveFields)) {
      return null;
    }
    return sectionShell(
      title,
      <div style={{ display: "grid", gap: 12 }}>
        <article style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, background: "#f8fafc" }}>
          <strong>{successState.headline}</strong>
          <p style={{ marginBottom: 0 }}>{successState.body}</p>
        </article>
        {responseRecord ? renderFieldList(effectiveFields) : null}
      </div>,
    );
  }

  function renderTransitionTimeline(title: string) {
    if (uiState !== "success" && !responseRecord && responseRows.length === 0) {
      return null;
    }
    return sectionShell(
      title,
      businessStateTransitions.length > 0 ? (
        <ol style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 12 }}>
          {businessStateTransitions.map((transition, index) => (
            <li key={`${transition.domain_object || "transition"}-${index}`} style={{ display: "grid", gap: 6 }}>
              <strong>{transition.domain_object || `Transition ${index + 1}`}</strong>
              <span>{[transition.from_state, transition.to_state].filter(Boolean).join(" -> ")}</span>
              {transition.trigger_action ? <span>{`Action: ${transition.trigger_action}`}</span> : null}
              {transition.ui_state_change ? <span>{transition.ui_state_change}</span> : null}
            </li>
          ))}
        </ol>
      ) : (
        <p style={{ margin: 0, color: "#475569" }}>{stepOutcomeCopy(subtitle, userGoal, actionModel)}</p>
      ),
    );
  }

  function renderContinuationPanel(title: string) {
    if (uiState !== "success" || !resolvedNextRoute) {
      return null;
    }
    return sectionShell(
      title,
      <div style={{ display: "grid", gap: 12 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {renderNextStepAction()}
        </div>
      </div>,
    );
  }

  function renderSetupFlowWorkspace() {
    const leadPanels = [
      renderActionForm(setupSection?.title || primaryWorkRegion || "Prepare next action", setupSection),
      renderMetricStrip(summarySection?.title || "Record overview", fieldsForSection(summarySection, summaryCardBindings.map((item) => item.field))),
    ];
    const asidePanels = presentPanels([
      renderStatusCard("Action status"),
      renderOutcomeCard(resultSection?.title || "Saved scope and launch result", fieldsForSection(resultSection, detailFieldOrder)),
      detailSection ? renderEvidenceDetails(detailSection.title, fieldsForSection(detailSection, detailFieldOrder)) : null,
      renderContinuationPanel(nextStepSection?.title || "Next step"),
    ]);
    if (asidePanels.length === 0) {
      return <div style={{ display: "grid", gap: 16 }}>{leadPanels}</div>;
    }
    return (
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 1.75fr) minmax(320px, 1fr)" }}>
        <div style={{ display: "grid", gap: 16 }}>{leadPanels}</div>
        <aside style={{ display: "grid", gap: 16, alignContent: "start" }}>
          {asidePanels.map((panel, index) => (
            <div key={index}>{panel}</div>
          ))}
        </aside>
      </div>
    );
  }

  function renderAnalysisBoardWorkspace() {
    return (
      <>
        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          {renderMetricStrip(summarySection?.title || "Priority signals", fieldsForSection(summarySection, summaryCardBindings.map((item) => item.field)))}
          {renderTransitionTimeline("State changes operators must see")}
        </div>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 1.9fr) minmax(320px, 1fr)" }}>
          <div style={{ display: "grid", gap: 16 }}>
            {setupSection ? renderActionForm(setupSection.title, setupSection) : null}
            {renderDataTable(tableSection?.title || primaryWorkRegion || "Findings board", fieldsForSection(tableSection, tableBindings.map((item) => item.field)))}
          </div>
          <aside style={{ display: "grid", gap: 16, alignContent: "start" }}>
            {renderEvidenceDetails(detailSection?.title || "Selected finding context", fieldsForSection(detailSection, detailFieldOrder))}
            {resultSection ? renderOutcomeCard(resultSection.title, fieldsForSection(resultSection, detailFieldOrder)) : null}
            {renderStatusCard("Board status")}
            {renderContinuationPanel(nextStepSection?.title || "Next step")}
          </aside>
        </div>
      </>
    );
  }

  function renderWorkbenchSnapshot() {
    return (
      <div style={{ display: "grid", gap: 16 }}>
        {renderMetricStrip(summarySection?.title || "Record status", summaryFields)}
        {renderActionForm(setupSection?.title || primaryWorkRegion || "Update record decision", setupSection)}
        {renderEvidenceDetails(detailSection?.title || primaryWorkRegion || "Current record", detailFields)}
      </div>
    );
  }

  function renderWorkbenchActionRail() {
    const hasPrimaryWorkbenchForm = Boolean(setupSection || activeInputs.length > 0);
    const panels = presentPanels([
      !hasPrimaryWorkbenchForm ? sectionShell(primaryCta.label || "Save action", (
        <div style={{ display: "grid", gap: 12 }}>
          {currentInteractionUnavailable ? (
            <p style={{ margin: 0, color: "#b42318" }}>
              {readinessGuidance(currentInteractionReadiness, currentInteractionBlockedReason, primaryActionLabel)}
            </p>
          ) : null}
          {renderActionButtons()}
        </div>
      )) : null,
      renderStatusCard("Commit status"),
      renderTransitionTimeline("Record state changes"),
      renderOutcomeCard(resultSection?.title || "Committed record result", resultFields),
      renderContinuationPanel(nextStepSection?.title || "Next step"),
    ]);
    if (panels.length === 0) {
      return null;
    }
    return (
      <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
        {panels.map((panel, index) => (
          <div key={index}>{panel}</div>
        ))}
      </div>
    );
  }

  function renderWorkbenchWorkspace() {
    const actionRail = renderWorkbenchActionRail();
    if (!actionRail) {
      return renderWorkbenchSnapshot();
    }
    return (
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(0, 1.6fr) minmax(360px, 1fr)" }}>
        <div>{renderWorkbenchSnapshot()}</div>
        <aside>{actionRail}</aside>
      </div>
    );
  }

  function renderExecutionBoard() {
    return (
      <div style={{ display: "grid", gap: 16 }}>
        {renderMetricStrip(summarySection?.title || "Execution summary", fieldsForSection(summarySection, summaryCardBindings.map((item) => item.field)))}
        {renderDataTable(tableSection?.title || primaryWorkRegion || "Task board", fieldsForSection(tableSection, tableBindings.map((item) => item.field)))}
        {renderEvidenceDetails(detailSection?.title || "Execution evidence", fieldsForSection(detailSection, detailFieldOrder))}
      </div>
    );
  }

  function renderExecutionRail() {
    return (
      <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
        {renderStatusCard("Task status")}
        {setupSection ? renderActionForm(setupSection.title, setupSection) : null}
        {renderTransitionTimeline("Execution state changes")}
        {renderContinuationPanel(nextStepSection?.title || "Next step")}
      </div>
    );
  }

  function renderReviewEvidenceLedger() {
    return (
      <div style={{ display: "grid", gap: 16 }}>
        {setupSection ? renderActionForm(setupSection?.title || "Decision input", setupSection) : null}
        {renderMetricStrip(summarySection?.title || "Review outcome summary", summaryFields)}
        {renderEvidenceDetails(detailSection?.title || primaryWorkRegion || "Review evidence", detailFields)}
        {renderOutcomeCard(resultSection?.title || "Published review", resultFields)}
        {renderTransitionTimeline("Review state changes")}
      </div>
    );
  }

  function renderReviewDecisionRail() {
    return (
      <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
        {!setupSection ? sectionShell("Follow-up", (
          <div style={{ display: "grid", gap: 12 }}>
            {renderActionButtons()}
          </div>
        )) : null}
        {renderStatusCard("Review status")}
        {renderContinuationPanel(nextStepSection?.title || "Continue or revise")}
      </div>
    );
  }

  function renderDetailReadingPane() {
    return (
      <div style={{ display: "grid", gap: 16 }}>
        {(setupSection || activeInputs.length > 0) ? renderActionForm(setupSection?.title || primaryWorkRegion || "Update record decision", setupSection) : null}
        {renderMetricStrip(summarySection?.title || "Record overview", summaryFields)}
        {renderEvidenceDetails(detailSection?.title || primaryWorkRegion || "Detail reading chain", detailFields)}
        {resultSection ? renderOutcomeCard(resultSection.title, resultFields) : null}
      </div>
    );
  }

  function renderDetailActionSidebar() {
    return (
      <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
        {renderStatusCard("Current detail state")}
        {renderTransitionTimeline("Record state changes")}
        {renderContinuationPanel(nextStepSection?.title || "Related actions")}
      </div>
    );
  }
  void [renderSetupFlowWorkspace, renderAnalysisBoardWorkspace, renderWorkbenchWorkspace, renderExecutionBoard, renderExecutionRail, renderReviewEvidenceLedger, renderReviewDecisionRail, renderDetailReadingPane, renderDetailActionSidebar];

  function renderBlueprintAppendix() {
    const layoutUsesTable = blueprintKind === "analysis-board" || blueprintKind === "execution-workbench";
    const layoutUsesOutcome = blueprintKind !== "analysis-board" && blueprintKind !== "execution-workbench" && blueprintKind !== "unsupported-blueprint";
    const layoutUsesTransitions = blueprintKind !== "setup-flow" && blueprintKind !== "detail-view" && blueprintKind !== "unsupported-blueprint";
    const panels: Array<{ key: string; node: ReactNode }> = [];
    if (tableSection && !layoutUsesTable) {
      panels.push({
        key: "table",
        node: renderDataTable(
          tableSection.title || primaryWorkRegion || shellCopy.current_data_title,
          fieldsForSection(tableSection, tableBindings.map((item) => item.field)),
        ),
      });
    }
    if (resultSection && !layoutUsesOutcome) {
      panels.push({
        key: "result",
        node: renderOutcomeCard(
          resultSection.title || successState.headline,
          fieldsForSection(resultSection, detailFieldOrder),
        ),
      });
    }
    if (businessStateTransitions.length > 0 && !layoutUsesTransitions) {
      panels.push({
        key: "transitions",
        node: renderTransitionTimeline(zhLocale ? "状态变化" : "State changes"),
      });
    }
    if (panels.length === 0) {
      return null;
    }
    return (
      <section data-phase3-region="contract-appendix" style={{ display: "grid", gap: 16 }}>
        {panels.map((panel) => (
          <div key={panel.key}>{panel.node}</div>
        ))}
      </section>
    );
  }

  return (
    <main data-phase3-surface="__ROUTE__" data-phase3-role={pageRole} style={{ display: "grid", gap: 20 }}>
      <header style={{ display: "grid", gap: 16, border: "1px solid #dbe4f0", borderRadius: 24, padding: 24, background: "linear-gradient(135deg, #ffffff 0%, #f6f9ff 58%, #eff8f6 100%)", boxShadow: "0 20px 44px rgba(15, 23, 42, 0.08)" }}>
        <div style={{ display: "grid", gap: 8, maxWidth: 760 }}>
          <p style={{ margin: 0, color: "#4b5563", textTransform: "uppercase", letterSpacing: "0.12em", fontSize: 12, fontWeight: 700 }}>
            {appContext.product_name || eyebrow}
          </p>
          <h1 style={{ margin: 0 }}>__TITLE__</h1>
          <p style={{ margin: 0, color: "#475569", maxWidth: 760 }}>{firstBusinessCopy(subtitle) || firstBusinessCopy(userGoal) || subtitle}</p>
        </div>
        {informationObjects.length > 0 ? (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {informationObjects.slice(0, 6).map((objectLabel) => (
              <span key={objectLabel} style={{ borderRadius: 999, padding: "6px 12px", background: "#fff", border: "1px solid #dbe4f0", color: "#334155" }}>
                {objectLabel}
              </span>
            ))}
          </div>
        ) : null}
        {pageReadOnly ? (
          <div style={{ border: "1px solid #fcd34d", borderRadius: 14, padding: 14, background: "#fffbeb", color: "#92400e" }}>
            {"This role can review current data but cannot submit changes on this page."}
          </div>
        ) : null}
      </header>

      {renderSetupFlowToolbar()}

__WORKFLOW_INTENT_LAYOUT__

__BLUEPRINT_LAYOUT__

      {renderBlueprintAppendix()}
    </main>
  );
}
"""
    rendered = (
        template.replace("__API_IMPORT__", api_import)
        .replace("__WORKFLOW_STORAGE_IMPORT__", workflow_storage_import)
        .replace("__ROLE_SESSION_IMPORT__", role_session_import)
        .replace("__WORKFLOW_PROGRESS_IMPORT__", workflow_progress_import)
        .replace("__PAGE_ROLE__", json.dumps(page_role, ensure_ascii=False))
        .replace("__PAGE_LOCALE__", page_locale_blob)
        .replace("__EYEBROW__", eyebrow_blob)
        .replace("__SUBTITLE__", subtitle_blob)
        .replace("__USER_GOAL__", user_goal_blob)
        .replace("__PRIMARY_CTA__", primary_cta_blob)
        .replace("__SECONDARY_CTA__", secondary_cta_blob)
        .replace("__SECTIONS__", sections_blob)
        .replace("__EMPTY_STATE__", empty_state_blob)
        .replace("__SUCCESS_STATE__", success_state_blob)
        .replace("__ERROR_STATE__", error_state_blob)
        .replace("__DATA_REQUIRED__", data_required_blob)
        .replace("__PRIMARY_API_BINDING__", primary_api_binding_blob)
        .replace("__PRESENTATION__", presentation_blob)
        .replace("__DISPLAY_FIELDS__", display_fields_blob)
        .replace("__FIELD_LABELS__", field_labels_blob)
        .replace("__USER_INPUTS__", user_inputs_blob)
        .replace("__FIELD_MAPPINGS__", field_mappings_blob)
        .replace("__STATE_CONDITIONS__", state_conditions_blob)
        .replace("__ACTIONS__", actions_blob)
        .replace("__OPERATIONS__", operations_blob)
        .replace("__WORK_PACKAGES__", work_packages_blob)
        .replace("__NAVIGATION__", navigation_blob)
        .replace("__APP_CONTEXT__", app_context_blob)
        .replace("__SHELL_COPY__", shell_copy_blob)
        .replace("__WORKFLOW_STEP__", workflow_step_blob)
        .replace("__INFORMATION_OBJECTS__", information_objects_blob)
        .replace("__ALLOWED_ROLES__", allowed_roles_blob)
        .replace("__READ_ONLY_BY_ROLE__", read_only_by_role_blob)
        .replace("__REQUIRED_REGIONS__", required_regions_blob)
        .replace("__NEXT_ROUTE_CANDIDATES__", next_route_candidates_blob)
        .replace("__COMPILED_INTERACTIONS__", compiled_interactions_blob)
        .replace("__MUST_SHOW_TOGETHER__", must_show_together_blob)
        .replace("__REQUIRED_INPUTS_CONTRACT__", required_inputs_contract_blob)
        .replace("__RENDER_BLOCKS_IN_ORDER__", render_blocks_blob)
        .replace("__PAGE_BLUEPRINT_TYPE__", page_blueprint_type_blob)
        .replace("__PRIMARY_WORK_REGION__", primary_work_region_blob)
        .replace("__SECONDARY_SUPPORT_REGIONS__", secondary_support_regions_blob)
        .replace("__DOMINANT_COMPONENT_PATTERN__", dominant_component_pattern_blob)
        .replace("__ACTION_MODEL__", action_model_blob)
        .replace("__BUSINESS_STATE_TRANSITIONS__", business_state_transitions_blob)
        .replace("__FORBIDDEN_LAYOUT_PATTERNS__", forbidden_layout_patterns_blob)
        .replace("__FIELD_GROUPS__", field_groups_blob)
        .replace("__INPUT_CONTROLS__", input_controls_blob)
        .replace("__SUMMARY_CARDS__", summary_cards_blob)
        .replace("__DETAIL_FIELDS_IN_ORDER__", detail_fields_blob)
        .replace("__SETUP_ROUTE_HINTS__", setup_route_hints_block)
        .replace("__TABLE_COLUMNS__", table_columns_blob)
        .replace("__FILTERS_AND_SELECTORS__", filters_selectors_blob)
        .replace("__REQUIRED_STATUS_MESSAGES__", required_status_messages_blob)
        .replace("__SUBMISSION_FEEDBACK__", submission_feedback_blob)
        .replace("__CONTEXT_ARRIVES_FROM__", context_arrives_from_blob)
        .replace("__CONTEXT_MUST_CONTINUE_TO__", context_must_continue_to_blob)
        .replace("__EXECUTOR_BRIEF__", executor_brief_blob)
        .replace("__WORKFLOW_INTENT_LAYOUT__", render_workflow_intent_markup(page_blueprint_type))
        .replace("__BLUEPRINT_LAYOUT__", render_blueprint_layout_markup(page_blueprint_type))
        .replace("__COMPONENT_NAME__", component_name)
        .replace("__ROUTE__", page_route)
        .replace("__TITLE__", title)
    )
    return localize_rendered_ui_code(rendered, locale=locale)


def render_home_page(ui_pages: list[dict[str, Any]], operations: list[dict[str, str]], wp_rows: list[dict[str, object]]) -> str:
    del operations, wp_rows
    app_context = ui_app_context(ui_pages)
    locale = str(app_context.get("locale") or "en")
    zh = is_zh_locale(locale)
    session_required_label = "Sign in required" if not zh else "需要登录"
    session_required_hint = (
        "This app opens role workspaces only after a valid session is established."
        if not zh
        else "建立有效会话后，应用才会打开角色工作区。"
    )
    session_required_body = (
        "Use the deployment's authentication entry to sign in as an assigned role before opening business pages."
        if not zh
        else "请先通过部署提供的认证入口，以已分配角色登录后再进入业务页面。"
    )
    no_accessible_pages_label = ui_text(locale, "no_accessible_pages")
    read_only_mode_label = ui_text(locale, "read_only_mode")
    editable_mode_label = ui_text(locale, "editable_mode")
    active_workspace_hint = (
        "Continue the active business task from the current workspace."
        if not zh
        else "从当前工作区继续处理业务。"
    )
    current_context_label = "Current context" if not zh else "当前上下文"
    current_context_hint = (
        "Saved record context stays available while you move between pages."
        if not zh
        else "已保存的记录上下文会在页面之间延续。"
    )
    empty_context_label = (
        "Saved context appears here after you complete a page action."
        if not zh
        else "完成页面操作后，这里会显示已保存的上下文。"
    )
    surface_section_label = "Available pages" if not zh else "可用页面"
    surface_section_hint = (
        "Only pages available to the current workspace are shown here."
        if not zh
        else "这里仅显示当前工作区可进入的页面。"
    )
    open_workspace_label = "Open workspace" if not zh else "进入工作区"
    end_session_label = "Sign out" if not zh else "退出登录"
    open_page_label = "Open page" if not zh else "进入页面"
    main_action_label = "Main action" if not zh else "主要操作"
    ordered_pages = [page for page in ui_pages if str(page.get("page_title") or "").strip()]
    surfaces: list[dict[str, Any]] = []
    for page in ordered_pages:
        surfaces.append(
            {
                "href": str(page.get("route") or f"/{route_slug(str(page.get('page_title') or 'surface'))}"),
                "title": str(page.get("page_title") or ""),
                "subtitle": str(page.get("subtitle") or ""),
                "summary": ui_page_data_focus(page),
                "actionFocus": ui_page_action_focus(page),
                "allowedRoles": [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()],
                "defaultAccess": str((page.get("read_only_vs_editable_by_role", {}) or {}).get("default_access") or "").strip(),
            }
        )
    surfaces_blob = json.dumps(surfaces, ensure_ascii=False, indent=2)
    app_context_blob = json.dumps(app_context, ensure_ascii=False, indent=2)
    template = r'''import { useEffect, useState } from "react";
import { clearWorkflowContext, readWorkflowContext } from "./workflow-storage";
import { clearRoleSession, readRoleSession } from "./role-session-storage";
import { clearWorkflowProgress } from "./workflow-progress-storage";

type SurfaceLink = {
  href: string;
  title: string;
  subtitle: string;
  summary: string;
  actionFocus: string;
  allowedRoles: string[];
  defaultAccess?: string;
};

type WorkspaceLink = {
  role: string;
  entry_route: string;
  page_routes?: string[];
  page_ids?: string[];
  page_titles?: string[];
  default_access?: string;
};

type AppContext = {
  product_name: string;
  product_heading: string;
  key_entities?: string[];
  current_session_role?: string;
  available_workspaces?: WorkspaceLink[];
  role_scoped_entry_routes?: Record<string, string>;
  route_guard_policy?: {
    workspace_switch_required?: boolean;
    denied_behavior?: string;
    auth_entry_route?: string;
    auth_entry_label?: string;
  };
};

type WorkflowContext = Record<string, string>;

const surfaces: SurfaceLink[] = __SURFACES__;
const appContext = __APP_CONTEXT__ as AppContext;

export default function HomePage() {
  const [workflowContext, setWorkflowContext] = useState<WorkflowContext>({});
  const [currentRole, setCurrentRole] = useState<string>(String(appContext.current_session_role || ''));
  const workspaces = appContext.available_workspaces ?? [];
  const workspaceRoles = workspaces.map((workspace) => String(workspace.role || '')).filter((role) => role.length > 0);
  useEffect(() => {
    setWorkflowContext(readWorkflowContext());
    const stored = readRoleSession();
    const storedRole = String(stored.currentRole || '').trim();
    const bootstrapRole = String(appContext.current_session_role || '').trim();
    if (storedRole && (workspaceRoles.length === 0 || workspaceRoles.includes(storedRole))) {
      setCurrentRole(storedRole);
      return;
    }
    if (bootstrapRole && (workspaceRoles.length === 0 || workspaceRoles.includes(bootstrapRole))) {
      setCurrentRole(bootstrapRole);
      return;
    }
    setCurrentRole('');
  }, []);
  const effectiveRole = currentRole || String(appContext.current_session_role || '');
  const hasRoleSession = Boolean(effectiveRole);
  const usesDirectWorkspace = workspaces.length === 0;
  const requiresWorkspaceBootstrap = !hasRoleSession && !usesDirectWorkspace && workspaces.length > 0;
  const roleEntryRoutes = appContext.role_scoped_entry_routes ?? {};
  const authEntryRoute = String(appContext.route_guard_policy?.auth_entry_route || '').trim();
  const authEntryLabel = String(appContext.route_guard_policy?.auth_entry_label || 'Sign in').trim() || 'Sign in';
  const visibleSurfaces = !requiresWorkspaceBootstrap
    ? surfaces.filter((surface) => !hasRoleSession || surface.allowedRoles.length === 0 || surface.allowedRoles.includes(effectiveRole))
    : [];
  const currentWorkspace = hasRoleSession ? workspaces.find((workspace) => String(workspace.role || '') === effectiveRole) ?? null : null;
  const primarySurface = currentWorkspace
    ? (visibleSurfaces.find((surface) => surface.href === String(roleEntryRoutes[effectiveRole] || currentWorkspace.entry_route || '')) ?? visibleSurfaces[0] ?? null)
    : (usesDirectWorkspace ? (visibleSurfaces[0] ?? null) : null);
  const contextEntries = Object.entries(workflowContext).filter(([key, value]) => key.trim().length > 0 && value.trim().length > 0);

  function endCurrentSession() {
    clearRoleSession();
    if (effectiveRole) {
      clearWorkflowProgress(effectiveRole);
    } else {
      clearWorkflowProgress();
    }
    clearWorkflowContext();
    setCurrentRole('');
    setWorkflowContext({});
    if (typeof window !== 'undefined') {
      window.location.assign('/');
    }
  }

  return (
    <main data-phase3-surface="home" data-phase3-role="workspace" style={{ display: "grid", gap: 20 }}>
      <header style={{ display: 'grid', gap: 10, border: '1px solid #d9d9d9', borderRadius: 20, padding: 24, background: 'linear-gradient(135deg, #fff 0%, #f4f8ff 100%)' }}>
        <p style={{ margin: 0, color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{appContext.product_name}</p>
        <h1 style={{ margin: 0 }}>{requiresWorkspaceBootstrap ? __SESSION_REQUIRED_LABEL__ : appContext.product_heading}</h1>
        <p style={{ margin: 0, color: '#444' }}>{requiresWorkspaceBootstrap ? __SESSION_REQUIRED_HINT__ : __ACTIVE_WORKSPACE_HINT__}</p>
        {!requiresWorkspaceBootstrap ? (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            {(appContext.key_entities ?? []).length > 0 ? <span style={{ color: '#64748b' }}>{(appContext.key_entities ?? []).slice(0, 3).join(' / ')}</span> : null}
            {effectiveRole ? <span style={{ borderRadius: 999, padding: '8px 12px', background: '#ecfeff', border: '1px solid #a5f3fc', color: '#0f766e', fontWeight: 700 }}>{effectiveRole}</span> : null}
          </div>
        ) : null}
        {!requiresWorkspaceBootstrap ? (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            {primarySurface ? <a href={primarySurface.href} style={{ display: 'inline-flex', width: 'fit-content', alignItems: 'center', justifyContent: 'center', borderRadius: 10, padding: '10px 14px', border: '1px solid #0f766e', background: '#0f766e', color: '#fff', textDecoration: 'none' }}>{__OPEN_WORKSPACE_LABEL__}</a> : null}
            {hasRoleSession ? <button type="button" onClick={() => endCurrentSession()} style={{ borderRadius: 10, padding: '10px 14px', border: '1px solid #d5d9e2', background: '#fff' }}>{__END_SESSION_LABEL__}</button> : null}
          </div>
        ) : null}
      </header>
      {requiresWorkspaceBootstrap ? (
        <section data-phase3-region="session-required" style={{ display: 'grid', gap: 16 }}>
          <article style={{ border: '1px solid #d9d9d9', borderRadius: 16, padding: 20, background: '#fff', display: 'grid', gap: 12 }}>
            <h2 style={{ margin: 0 }}>{__SESSION_REQUIRED_LABEL__}</h2>
            <p style={{ margin: 0, color: '#444' }}>{__SESSION_REQUIRED_HINT__}</p>
            <p style={{ margin: 0, color: '#475569' }}>{__SESSION_REQUIRED_BODY__}</p>
            {authEntryRoute ? <a href={authEntryRoute} style={{ display: 'inline-flex', width: 'fit-content', alignItems: 'center', justifyContent: 'center', borderRadius: 10, padding: '10px 14px', border: '1px solid #0f766e', background: '#0f766e', color: '#fff', textDecoration: 'none' }}>{authEntryLabel}</a> : null}
          </article>
        </section>
      ) : null}
      {!requiresWorkspaceBootstrap && (hasRoleSession || usesDirectWorkspace) ? (
        <section data-phase3-region="workflow-context" style={{ border: '1px solid #d9d9d9', borderRadius: 16, padding: 20, background: '#fff', display: 'grid', gap: 16 }}>
          <div style={{ display: 'grid', gap: 6 }}><h2 style={{ margin: 0 }}>__CURRENT_CONTEXT_LABEL__</h2><p style={{ margin: 0, color: '#444' }}>__CURRENT_CONTEXT_HINT__</p></div>
          {contextEntries.length > 0 ? (
            <dl style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 220px) 1fr', gap: 10 }}>
              {contextEntries.map(([key, value]) => (
                <div key={key} style={{ display: 'contents' }}>
                  <dt style={{ fontWeight: 600 }}>{key}</dt>
                  <dd style={{ margin: 0 }}>{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p style={{ margin: 0, color: '#444' }}>__EMPTY_CONTEXT_LABEL__</p>
          )}
        </section>
      ) : null}
      {!requiresWorkspaceBootstrap && (hasRoleSession || usesDirectWorkspace) ? (
        <section data-phase3-region="surface-list" style={{ display: 'grid', gap: 16 }}>
          <div style={{ display: 'grid', gap: 6 }}>
            <h2 style={{ margin: 0 }}>__SURFACE_SECTION_LABEL__</h2>
            <p style={{ margin: 0, color: '#444' }}>__SURFACE_SECTION_HINT__</p>
          </div>
          {visibleSurfaces.length === 0 ? <p style={{ margin: 0, color: '#475569' }}>{__NO_ACCESSIBLE_PAGES_LABEL__}</p> : null}
          {visibleSurfaces.map((surface) => (
            <article key={surface.href} style={{ border: '1px solid #d9d9d9', borderRadius: 16, padding: 18, background: '#fff', display: 'grid', gap: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <div style={{ display: 'grid', gap: 6 }}>
                  <h3 style={{ margin: 0 }}><a href={surface.href}>{surface.title}</a></h3>
                  {surface.subtitle ? <p style={{ margin: 0, color: '#444' }}>{surface.subtitle}</p> : null}
                </div>
                <div style={{ display: 'grid', gap: 8, justifyItems: 'end' }}><span style={{ borderRadius: 999, padding: '6px 10px', background: '#f8fafc', border: '1px solid #d9e2ec', color: '#334155', fontSize: 12 }}>{surface.defaultAccess === 'read-only' ? __READ_ONLY_MODE_LABEL__ : __EDITABLE_MODE_LABEL__}</span><a href={surface.href}>{__OPEN_PAGE_LABEL__}</a></div>
              </div>
              {surface.summary ? <p style={{ margin: 0 }}>{surface.summary}</p> : null}
              <p style={{ margin: 0, color: '#334155' }}><strong>__MAIN_ACTION_LABEL__:</strong> {surface.actionFocus}</p>
            </article>
          ))}
        </section>
      ) : null}
    </main>
  );
}
'''
    rendered = template.replace('__SURFACES__', surfaces_blob).replace('__APP_CONTEXT__', app_context_blob)
    replacements = {
        '__SESSION_REQUIRED_LABEL__': json.dumps(session_required_label, ensure_ascii=False),
        '__SESSION_REQUIRED_HINT__': json.dumps(session_required_hint, ensure_ascii=False),
        '__SESSION_REQUIRED_BODY__': json.dumps(session_required_body, ensure_ascii=False),
        '__ACTIVE_WORKSPACE_HINT__': json.dumps(active_workspace_hint, ensure_ascii=False),
        '__OPEN_WORKSPACE_LABEL__': json.dumps(open_workspace_label, ensure_ascii=False),
        '__END_SESSION_LABEL__': json.dumps(end_session_label, ensure_ascii=False),
        '__READ_ONLY_MODE_LABEL__': json.dumps(read_only_mode_label, ensure_ascii=False),
        '__EDITABLE_MODE_LABEL__': json.dumps(editable_mode_label, ensure_ascii=False),
        '__CURRENT_CONTEXT_LABEL__': current_context_label,
        '__CURRENT_CONTEXT_HINT__': current_context_hint,
        '__EMPTY_CONTEXT_LABEL__': empty_context_label,
        '__SURFACE_SECTION_LABEL__': surface_section_label,
        '__SURFACE_SECTION_HINT__': surface_section_hint,
        '__NO_ACCESSIBLE_PAGES_LABEL__': json.dumps(no_accessible_pages_label, ensure_ascii=False),
        '__OPEN_PAGE_LABEL__': json.dumps(open_page_label, ensure_ascii=False),
        '__MAIN_ACTION_LABEL__': main_action_label,
    }
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered



def render_auth_entry_page(ui_pages: list[dict[str, Any]]) -> str:
    app_context = ui_app_context(ui_pages)
    locale = str(app_context.get("locale") or "en")
    zh = is_zh_locale(locale)
    route_guard_policy = app_context.get("route_guard_policy") if isinstance(app_context.get("route_guard_policy"), dict) else {}
    auth_entry_route = normalize_ui_route(route_guard_policy.get("auth_entry_route") or "")
    route_segments = [segment for segment in auth_entry_route.strip("/").split("/") if segment]
    import_prefix = "/".join([".."] * len(route_segments) + ["role-session-storage"]) if route_segments else "./role-session-storage"
    heading = str(route_guard_policy.get("auth_entry_label") or ("登录" if zh else "Sign in")).strip() or ("登录" if zh else "Sign in")
    hint = (
        "使用已分配的工作区身份登录后继续业务处理。"
        if zh
        else "Sign in with your assigned workspace before continuing the business flow."
    )
    identity_label = "邮箱" if zh else "Work email"
    password_label = "密码" if zh else "Password"
    workspace_label = "工作区" if zh else "Workspace"
    submit_label = "登录" if zh else "Sign in"
    missing_role_text = "请选择要进入的工作区。" if zh else "Choose the workspace you need to enter."
    missing_credentials_text = "请输入可识别的账号与密码。" if zh else "Enter a recognizable account and password."
    invalid_credentials_text = "账号或密码不正确。" if zh else "The account or password is incorrect."
    no_workspace_text = "当前账号还没有可用工作区。" if zh else "No workspace is currently available for this account."
    identity_placeholder = "name@company.com"
    password_placeholder = "输入密码" if zh else "Enter password"
    app_context_blob = json.dumps(app_context, ensure_ascii=False, indent=2)
    template = r'''import { FormEvent, useEffect, useState } from "react";
import { persistRoleSession, readRoleSession } from "__ROLE_SESSION_IMPORT__";

type WorkspaceLink = {
  role: string;
  entry_route: string;
  page_routes?: string[];
  page_ids?: string[];
  page_titles?: string[];
  default_access?: string;
};

type AuthTestAccount = {
  role: string;
  email: string;
  password: string;
};

type AppContext = {
  product_name: string;
  role_scoped_entry_routes?: Record<string, string>;
  available_workspaces?: WorkspaceLink[];
  auth_test_accounts?: AuthTestAccount[];
};

const appContext = __APP_CONTEXT__ as AppContext;

export default function AuthEntryPage() {
  const workspaces = appContext.available_workspaces ?? [];
  const roleEntryRoutes = appContext.role_scoped_entry_routes ?? {};
  const authTestAccounts = appContext.auth_test_accounts ?? [];
  const availableRoles = workspaces.map((workspace) => String(workspace.role || '').trim()).filter((role) => role.length > 0);
  const [selectedRole, setSelectedRole] = useState<string>(availableRoles[0] || '');
  const [identity, setIdentity] = useState('');
  const [password, setPassword] = useState('');
  const [errorText, setErrorText] = useState('');

  useEffect(() => {
    const stored = readRoleSession();
    const storedRole = String(stored.currentRole || '').trim();
    const storedRoute = String(stored.entryRoute || '').trim();
    if (storedRole && storedRoute && typeof window !== 'undefined') {
      window.location.assign(storedRoute);
    }
  }, []);

  function entryRouteForRole(role: string): string {
    const explicitRoute = String(roleEntryRoutes[role] || '').trim();
    if (explicitRoute) {
      return explicitRoute;
    }
    const workspace = workspaces.find((item) => String(item.role || '').trim() === role);
    const workspaceRoute = String(workspace?.entry_route || '').trim();
    return workspaceRoute || '/';
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorText('');
    if (!selectedRole) {
      setErrorText(__MISSING_ROLE_TEXT__);
      return;
    }
    if (!identity.trim() || !password.trim()) {
      setErrorText(__MISSING_CREDENTIALS_TEXT__);
      return;
    }
    const normalizedIdentity = identity.trim().toLowerCase();
    const matchedAccount = authTestAccounts.find((account) => (
      String(account.role || '').trim() === selectedRole
      && String(account.email || '').trim().toLowerCase() === normalizedIdentity
      && String(account.password || '') === password
    ));
    if (authTestAccounts.length > 0 && !matchedAccount) {
      setErrorText(__INVALID_CREDENTIALS_TEXT__);
      return;
    }
    const entryRoute = entryRouteForRole(selectedRole);
    persistRoleSession({ currentRole: selectedRole, entryRoute });
    if (typeof window !== 'undefined') {
      window.location.assign(entryRoute);
    }
  }

  return (
    <main data-phase3-surface="auth-entry" data-phase3-role="session-entry" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
      <section style={{ width: '100%', maxWidth: 440, borderRadius: 20, border: '1px solid #d9d9d9', background: '#fff', padding: 24, display: 'grid', gap: 18, boxShadow: '0 18px 48px rgba(15, 23, 42, 0.08)' }}>
        <div style={{ display: 'grid', gap: 6 }}>
          <p style={{ margin: 0, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{appContext.product_name}</p>
          <h1 style={{ margin: 0 }}>{__HEADING__}</h1>
          <p style={{ margin: 0, color: '#475569' }}>{__HINT__}</p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 14 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontWeight: 600 }}>{__IDENTITY_LABEL__}</span>
            <input value={identity} onChange={(event) => setIdentity(event.target.value)} placeholder={__IDENTITY_PLACEHOLDER__} autoComplete="username" style={{ borderRadius: 12, border: '1px solid #cbd5e1', padding: '10px 12px' }} />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontWeight: 600 }}>{__PASSWORD_LABEL__}</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={__PASSWORD_PLACEHOLDER__} autoComplete="current-password" style={{ borderRadius: 12, border: '1px solid #cbd5e1', padding: '10px 12px' }} />
          </label>
          {availableRoles.length > 1 ? (
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontWeight: 600 }}>{__WORKSPACE_LABEL__}</span>
              <select value={selectedRole} onChange={(event) => setSelectedRole(event.target.value)} style={{ borderRadius: 12, border: '1px solid #cbd5e1', padding: '10px 12px' }}>
                {availableRoles.map((role) => <option key={role} value={role}>{role}</option>)}
              </select>
            </label>
          ) : selectedRole ? (
            <div style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontWeight: 600 }}>{__WORKSPACE_LABEL__}</span>
              <div style={{ borderRadius: 12, border: '1px solid #cbd5e1', padding: '10px 12px', background: '#f8fafc' }}>{selectedRole}</div>
            </div>
          ) : null}
          {availableRoles.length === 0 ? <p style={{ margin: 0, color: '#b91c1c' }}>{__NO_WORKSPACE_TEXT__}</p> : null}
          {errorText ? <p style={{ margin: 0, color: '#b91c1c' }}>{errorText}</p> : null}
          <button type="submit" disabled={availableRoles.length === 0} style={{ borderRadius: 12, border: '1px solid #0f766e', background: '#0f766e', color: '#fff', padding: '10px 14px', fontWeight: 700, cursor: availableRoles.length === 0 ? 'not-allowed' : 'pointer', opacity: availableRoles.length === 0 ? 0.6 : 1 }}>
            {__SUBMIT_LABEL__}
          </button>
        </form>
      </section>
    </main>
  );
}
'''
    rendered = template.replace('__ROLE_SESSION_IMPORT__', import_prefix).replace('__APP_CONTEXT__', app_context_blob)
    replacements = {
        '__HEADING__': json.dumps(heading, ensure_ascii=False),
        '__HINT__': json.dumps(hint, ensure_ascii=False),
        '__IDENTITY_LABEL__': json.dumps(identity_label, ensure_ascii=False),
        '__PASSWORD_LABEL__': json.dumps(password_label, ensure_ascii=False),
        '__WORKSPACE_LABEL__': json.dumps(workspace_label, ensure_ascii=False),
        '__SUBMIT_LABEL__': json.dumps(submit_label, ensure_ascii=False),
        '__MISSING_ROLE_TEXT__': json.dumps(missing_role_text, ensure_ascii=False),
        '__MISSING_CREDENTIALS_TEXT__': json.dumps(missing_credentials_text, ensure_ascii=False),
        '__INVALID_CREDENTIALS_TEXT__': json.dumps(invalid_credentials_text, ensure_ascii=False),
        '__NO_WORKSPACE_TEXT__': json.dumps(no_workspace_text, ensure_ascii=False),
        '__IDENTITY_PLACEHOLDER__': json.dumps(identity_placeholder, ensure_ascii=False),
        '__PASSWORD_PLACEHOLDER__': json.dumps(password_placeholder, ensure_ascii=False),
    }
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered


def render_ui_app(ui_pages: list[dict[str, Any]]) -> str:
    app_context = ui_app_context(ui_pages)
    locale = str(app_context.get("locale") or "en")
    zh = is_zh_locale(locale)
    import_lines = [
        'import { useEffect, useState } from "react";',
        'import { Layout, Menu, Typography } from "antd";',
        'import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";',
        'import { clearWorkflowContext } from "./workflow-storage";',
        'import { clearRoleSession, persistRoleSession, readRoleSession } from "./role-session-storage";',
        'import { WORKFLOW_PROGRESS_EVENT, clearWorkflowProgress, initializeWorkflowProgress, readWorkflowProgress } from "./workflow-progress-storage";',
        'import HomePage from "./page";',
    ]
    route_defs: list[str] = ['      <Route path="/" element={effectiveRole ? <Navigate to={redirectTarget} replace /> : <HomePage />} />']
    route_guard_policy = app_context.get("route_guard_policy") if isinstance(app_context.get("route_guard_policy"), dict) else {}
    auth_entry_route = normalize_ui_route(route_guard_policy.get("auth_entry_route") or "")
    auth_entry_route_segment = auth_entry_route.strip("/")
    if auth_entry_route_segment:
        import_lines.append(f'import AuthEntryPage from "./{auth_entry_route_segment}/page";')
        route_defs.append(f'      <Route path="{auth_entry_route}" element={{<AuthEntryPage />}} />'.replace("{{<", "{<").replace(">}}", ">}"))
    surface_routes: list[dict[str, Any]] = []
    for index, page in enumerate(ui_pages, start=1):
        title = str(page.get("page_title") or f"Surface {index}").strip()
        route_segment = ui_page_route_segment(page, title)
        import_name = f"Surface{index}Page"
        import_lines.append(f'import {import_name} from "./{route_segment}/page";')
        route_defs.append(f'      <Route path="/{route_segment}" element={{<{import_name} />}} />'.replace("{{<", "{<").replace(">}}", ">}"))
        surface_routes.append(
            {
                "route": f"/{route_segment}",
                "title": title,
                "allowedRoles": [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()],
                "defaultAccess": str((page.get("read_only_vs_editable_by_role", {}) or {}).get("default_access") or "").strip(),
            }
        )
    sign_out_label = ui_text(locale, "sign_out")
    workflow_locked_label = "完成前一步后解锁" if zh else "Unlocks after the previous step"
    app_context_blob = json.dumps(app_context, ensure_ascii=False, indent=2)
    surface_routes_blob = json.dumps(surface_routes, ensure_ascii=False, indent=2)
    route_defs_blob = "\n".join(route_defs + ['      <Route path="*" element={<Navigate to="/" replace />} />'])
    template = r'''import { useEffect, useState } from "react";
import { Layout, Menu, Typography } from "antd";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { clearWorkflowContext } from "./workflow-storage";
import { clearRoleSession, persistRoleSession, readRoleSession } from "./role-session-storage";
import { WORKFLOW_PROGRESS_EVENT, clearWorkflowProgress, initializeWorkflowProgress, readWorkflowProgress } from "./workflow-progress-storage";
import HomePage from "./page";
__IMPORT_LINES__

type WorkspaceLink = {
  role: string;
  entry_route: string;
  page_routes?: string[];
  page_ids?: string[];
  page_titles?: string[];
  default_access?: string;
};

type WorkflowNavItem = {
  route: string;
  label: string;
  step_label?: string;
  step_index?: number;
  total_steps?: number;
  unlocked_by_default?: boolean;
  locked_reason?: string;
};

type ContextualNav = {
  previous_route?: string;
  next_route?: string;
  previous_label?: string;
  next_label?: string;
  current_label?: string;
};

type NextStepCta = {
  kind?: string;
  target_route?: string;
  target_role?: string;
  target_label?: string;
  label?: string;
};

type PlacemakingMarker = {
  step_label?: string;
  current_label?: string;
  previous_label?: string;
  next_label?: string;
  step_index?: number;
  total_steps?: number;
};

type RoleReachability = {
  entry_route?: string;
  ordered_routes?: string[];
  direct_routes?: string[];
  flow_routes?: string[];
  default_reachable_routes?: string[];
  unlock_rule?: string;
};

type RouteReachability = {
  entry_route?: string;
  reachability_mode?: string;
  reachable_by_default?: boolean;
  reachable_after_route?: string;
  next_route?: string;
  step_index?: number;
  total_steps?: number;
  locked_reason?: string;
};

type WorkflowProgressState = {
  unlockedRoutes: string[];
  lastRoute?: string;
};

type WorkflowProgress = Record<string, WorkflowProgressState>;

type AppContext = {
  product_name: string;
  product_heading: string;
  supporting_roles?: string[];
  key_entities?: string[];
  current_session_role?: string;
  available_workspaces?: WorkspaceLink[];
  role_scoped_entry_routes?: Record<string, string>;
  route_guard_policy?: {
    workspace_switch_required?: boolean;
    default_route?: string;
    denied_behavior?: string;
    auth_entry_route?: string;
    auth_entry_label?: string;
    routes?: Record<string, { allowed_roles?: string[]; editable_roles?: string[]; read_only_roles?: string[] }>;
  };
  global_nav_items?: Array<{ route: string; label: string; kind?: string }>;
  local_nav_items?: Record<string, WorkflowNavItem[]>;
  contextual_nav_items?: Record<string, { by_role?: Record<string, ContextualNav> }>;
  next_step_cta?: Record<string, { by_role?: Record<string, NextStepCta> }>;
  route_reachability_policy?: {
    mode?: string;
    denied_behavior?: string;
    workspace_switch_required?: boolean;
    roles?: Record<string, RoleReachability>;
    routes?: Record<string, { allowed_roles?: string[]; by_role?: Record<string, RouteReachability>; denied_behavior?: string }>;
  };
  placemaking_markers?: Record<string, { by_role?: Record<string, PlacemakingMarker> }>;
};

const appContext = __APP_CONTEXT__ as AppContext;
const surfaceRoutes = __SURFACE_ROUTES__ as Array<{ route: string; title: string; allowedRoles: string[]; defaultAccess?: string }>;
const workspaces = appContext.available_workspaces ?? [];

function allowedRolesForRoute(route: string): string[] {
  return surfaceRoutes.find((surface) => surface.route === route)?.allowedRoles ?? [];
}

function entryRouteForRole(role: string): string {
  return String(appContext.role_scoped_entry_routes?.[role] || workspaces.find((workspace) => String(workspace.role || '') === role)?.entry_route || '/');
}

function routePolicyForRole(route: string, role: string): RouteReachability | null {
  return appContext.route_reachability_policy?.routes?.[route]?.by_role?.[role] ?? null;
}
void routePolicyForRole;

function workflowProgressForRole(progress: WorkflowProgress, role: string): WorkflowProgressState {
  return progress[role] ?? { unlockedRoutes: [] };
}

function isRouteAccessible(route: string, role: string): boolean {
  if (route === '/') {
    return true;
  }
  if (!role) {
    return false;
  }
  const allowedRoles = allowedRolesForRoute(route);
  return allowedRoles.length === 0 || allowedRoles.includes(role);
}

function isRouteReachable(route: string, role: string, progress: WorkflowProgress): boolean {
  if (route === '/') {
    return true;
  }
  if (!isRouteAccessible(route, role) || !role) {
    return false;
  }
  const entryRoute = entryRouteForRole(role);
  const routePolicy = routePolicyForRole(route, role);
  const reachabilityMode = String(routePolicy?.reachability_mode || '').trim();
  if (reachabilityMode === 'hidden') {
    return false;
  }
  const defaultReachableRoutes = appContext.route_reachability_policy?.roles?.[role]?.default_reachable_routes ?? [entryRoute];
  if (route === entryRoute || defaultReachableRoutes.includes(route) || Boolean(routePolicy?.reachable_by_default)) {
    return true;
  }
  if (reachabilityMode && reachabilityMode !== 'flow') {
    return true;
  }
  const unlockedRoutes = workflowProgressForRole(progress, role).unlockedRoutes;
  return unlockedRoutes.includes(route);
}

function fallbackRoute(role: string, progress: WorkflowProgress): string {
  if (!role) {
    return '/';
  }
  const roleProgress = workflowProgressForRole(progress, role);
  if (roleProgress.lastRoute && isRouteReachable(roleProgress.lastRoute, role, progress)) {
    return roleProgress.lastRoute;
  }
  const orderedRoutes = appContext.route_reachability_policy?.roles?.[role]?.ordered_routes ?? [];
  for (const route of orderedRoutes) {
    if (isRouteReachable(route, role, progress)) {
      return route;
    }
  }
  return entryRouteForRole(role);
}

function workflowNavLabel(item: WorkflowNavItem): string {
  return String(item.label || item.step_label || '').trim();
}

function resolveCurrentRole(workspaceRoles: string[]): string {
  const stored = readRoleSession();
  const storedRole = String(stored.currentRole || '').trim();
  const bootstrapRole = String(appContext.current_session_role || '').trim();
  if (storedRole && (workspaceRoles.length === 0 || workspaceRoles.includes(storedRole))) {
    return storedRole;
  }
  if (bootstrapRole && (workspaceRoles.length === 0 || workspaceRoles.includes(bootstrapRole))) {
    return bootstrapRole;
  }
  return '';
}

export function App() {
  const location = useLocation();
  const workspaceRoles = workspaces.map((workspace) => String(workspace.role || '')).filter((role) => role.length > 0);
  const [currentRole, setCurrentRole] = useState<string>(() => resolveCurrentRole(workspaceRoles));
  const [workflowProgress, setWorkflowProgress] = useState<WorkflowProgress>(() => readWorkflowProgress());
  const [sessionBootstrapResolved, setSessionBootstrapResolved] = useState<boolean>(false);
  useEffect(() => {
    setCurrentRole(resolveCurrentRole(workspaceRoles));
    setWorkflowProgress(readWorkflowProgress());
    setSessionBootstrapResolved(true);
    if (typeof window === 'undefined') {
      return;
    }
    const syncProgress = () => {
      setWorkflowProgress(readWorkflowProgress());
    };
    window.addEventListener(WORKFLOW_PROGRESS_EVENT, syncProgress);
    return () => window.removeEventListener(WORKFLOW_PROGRESS_EVENT, syncProgress);
  }, []);
  const effectiveRole = currentRole || String(appContext.current_session_role || '');
  const authEntryRoute = String(appContext.route_guard_policy?.auth_entry_route || '').trim();
  const isAuthEntryRoute = Boolean(authEntryRoute && location.pathname === authEntryRoute);
  const authRedirectEnabled = Boolean(
    sessionBootstrapResolved
    && location.pathname !== '/'
    && !effectiveRole
    && appContext.route_guard_policy?.denied_behavior === 'redirect-to-login'
    && authEntryRoute
    && !isAuthEntryRoute
  );
  useEffect(() => {
    if (authRedirectEnabled && typeof window !== 'undefined') {
      window.location.assign(authEntryRoute);
    }
  }, [authRedirectEnabled, authEntryRoute]);
  useEffect(() => {
    const entryRoute = entryRouteForRole(effectiveRole);
    if (effectiveRole && entryRoute) {
      persistRoleSession({ currentRole: effectiveRole, entryRoute });
      setWorkflowProgress(initializeWorkflowProgress(effectiveRole, entryRoute));
    }
  }, [effectiveRole]);
  function signOut() {
    clearRoleSession();
    clearWorkflowContext();
    clearWorkflowProgress();
    setCurrentRole('');
    setWorkflowProgress({});
    if (typeof window !== 'undefined') {
      window.location.assign('/');
    }
  }
  const globalMenuItems = (appContext.global_nav_items ?? []).map((item) => ({
    key: item.route,
    label: <Link to={item.route}>{item.label}</Link>,
  }));
  const roleMenuItems = (appContext.local_nav_items?.[effectiveRole] ?? []).map((item) => {
    const reachable = isRouteReachable(item.route, effectiveRole, workflowProgress);
    const label = workflowNavLabel(item);
    return {
      key: item.route,
      label: reachable ? <Link to={item.route}>{label}</Link> : <span>{label}</span>,
      disabled: !reachable,
      title: reachable ? undefined : (item.locked_reason || __WORKFLOW_LOCKED_LABEL__),
    };
  });
  const fallbackMenuItems = effectiveRole ? surfaceRoutes.filter((surface) => isRouteAccessible(surface.route, effectiveRole)).map((surface) => ({
    key: surface.route,
    label: <Link to={surface.route}>{surface.title}</Link>,
  })) : [];
  const menuItems = effectiveRole ? (roleMenuItems.length > 0 ? roleMenuItems : fallbackMenuItems) : globalMenuItems;
  const selectedKey = menuItems.some((item) => item.key === location.pathname) ? location.pathname : '/';
  const redirectTarget = effectiveRole ? fallbackRoute(effectiveRole, workflowProgress) : '/';
  const requiresWorkspaceBootstrap = Boolean(!effectiveRole && workspaces.length > 0 && appContext.route_guard_policy?.workspace_switch_required);
  const routeOutlet = (
    <Routes>
__ROUTE_DEFS__
    </Routes>
  );
  if (!sessionBootstrapResolved && location.pathname !== '/' && !isAuthEntryRoute) {
    return null;
  }
  if (location.pathname !== '/' && !effectiveRole && !isAuthEntryRoute) {
    if (authRedirectEnabled) {
      return null;
    }
    return <Navigate to="/" replace />;
  }
  if (location.pathname !== '/' && !isAuthEntryRoute && !isRouteAccessible(location.pathname, effectiveRole)) {
    return <Navigate to={entryRouteForRole(effectiveRole)} replace />;
  }
  if (location.pathname !== '/' && !isAuthEntryRoute && !isRouteReachable(location.pathname, effectiveRole, workflowProgress)) {
    return <Navigate to={redirectTarget} replace />;
  }
  if (requiresWorkspaceBootstrap) {
    return (
      <Layout className="phase3-app-shell" style={{ minHeight: "100vh", background: "transparent" }}>
        <Layout.Content className="phase3-app-shell__content" style={{ padding: 32, display: "grid", placeItems: "start center" }}>
          <div className="phase3-app-shell__canvas" style={{ display: "grid", gap: 20, width: "100%", maxWidth: 1120 }}>
            {routeOutlet}
          </div>
        </Layout.Content>
      </Layout>
    );
  }
  return (
    <Layout className="phase3-app-shell" style={{ minHeight: "100vh", background: "transparent" }}>
      <Layout.Sider width={288} breakpoint="lg" collapsedWidth={0} className="phase3-app-shell__sider">
        <div className="phase3-app-shell__brand" style={{ padding: 24, display: "grid", gap: 10 }}>
          <Typography.Text style={{ color: "rgba(255,255,255,0.72)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700 }}>{appContext.product_name}</Typography.Text>
          <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>{appContext.product_heading}</Typography.Title>
        </div>
        <Menu className="phase3-app-menu" theme="dark" mode="inline" selectedKeys={[selectedKey]} items={menuItems} />
        {effectiveRole ? (
          <div style={{ padding: 16, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <button type="button" onClick={() => signOut()} style={{ width: "100%", borderRadius: 10, border: "1px solid rgba(255,255,255,0.16)", background: "rgba(255,255,255,0.08)", color: "#fff", padding: "10px 14px" }}>{__SIGN_OUT_LABEL__}</button>
          </div>
        ) : null}
      </Layout.Sider>
      <Layout.Content className="phase3-app-shell__content" style={{ padding: 28 }}>
        <div className="phase3-app-shell__canvas" style={{ display: "grid", gap: 20 }}>
          {routeOutlet}
        </div>
      </Layout.Content>
    </Layout>
  );
}
'''
    extra_import_lines = "\n".join(import_lines[7:])
    rendered = template.replace('__IMPORT_LINES__', extra_import_lines)
    rendered = rendered.replace('__APP_CONTEXT__', app_context_blob)
    rendered = rendered.replace('__SURFACE_ROUTES__', surface_routes_blob)
    rendered = rendered.replace('__ROUTE_DEFS__', route_defs_blob)
    replacements = {
        '__WORKFLOW_LOCKED_LABEL__': json.dumps(workflow_locked_label, ensure_ascii=False),
        '__SIGN_OUT_LABEL__': json.dumps(sign_out_label, ensure_ascii=False),
    }
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return localize_rendered_ui_code(rendered, locale=locale)

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


def route_slug(surface: str) -> str:
    return stable_slug(surface, fallback="surface")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def related_operations_for_surface(
    surface: str,
    operations: list[dict[str, str]],
    *,
    page_contract: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    interest_tokens = ui_page_interest_tokens(surface, page_contract)
    related: list[dict[str, str]] = []
    for operation in operations:
        haystack = " ".join(
            [
                str(operation.get("operation_id", "")),
                str(operation.get("tag", "")),
                str(operation.get("path", "")),
            ]
        )
        if interest_tokens & scope_tokens(haystack):
            related.append(
                {
                    "operationId": str(operation.get("operation_id", "")).strip(),
                    "method": str(operation.get("method", "")).upper(),
                    "path": str(operation.get("path", "")).strip(),
                }
            )
    return related[:5]


def related_work_packages_for_surface(
    surface: str,
    wp_rows: list[dict[str, object]],
    *,
    page_contract: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    interest_tokens = ui_page_interest_tokens(surface, page_contract)
    related: list[dict[str, str]] = []
    for row in wp_rows:
        wp_id = str(row.get("wp_id", "")).strip()
        scope = str(row.get("scope", row.get("implementation_scope", ""))).strip()
        acceptance_criteria = str(row.get("acceptance_criteria", "")).strip()
        haystack = f"{scope} {acceptance_criteria}"
        if interest_tokens & scope_tokens(haystack):
            related.append(
                {
                    "wpId": wp_id,
                    "scope": scope,
                    "acceptance": acceptance_criteria,
                }
            )
    return related[:4]


def operation_by_contract_test_target(operations: list[dict[str, str]]) -> dict[str, str]:
    target_lookup = build_contract_test_target_lookup(list(operations))
    mapping: dict[str, str] = {}
    for operation in operations:
        operation_id = str(operation.get("operation_id", "")).strip() or f"{operation['method']}-{operation['path']}"
        method = str(operation.get("method", "")).upper()
        path = str(operation.get("path", "")).strip()
        target = target_lookup.get((operation_id, method, path))
        if target:
            mapping[f"tests/contracts/{target}"] = operation_id
    return mapping


def infer_binding_operation_id(
    *,
    source_subject: str,
    test_targets: list[str],
    operations: list[dict[str, str]],
    contract_operation_by_test: dict[str, str],
) -> str:
    direct_matches = [
        contract_operation_by_test[target]
        for target in test_targets
        if target in contract_operation_by_test and contract_operation_by_test[target]
    ]
    if len(set(direct_matches)) == 1:
        return direct_matches[0]

    normalized_subject = source_subject.lower()
    subject_matches = [
        str(operation.get("operation_id", "")).strip()
        for operation in operations
        if str(operation.get("operation_id", "")).strip()
        and str(operation.get("operation_id", "")).strip().lower() in normalized_subject
    ]
    if len(set(subject_matches)) == 1:
        return subject_matches[0]
    return ""


def infer_targets_from_scope(
    *,
    scope: str,
    acceptance_criteria: str,
    operations_by_tag: dict[str, list[dict[str, str]]],
    ui_pages: list[dict[str, Any]],
    output_dir: Path,
) -> list[str]:
    targets: set[str] = set()
    scope_terms = expand_scope_term_equivalents(scope_tokens(scope) | scope_tokens(acceptance_criteria))
    if not scope_terms:
        return []

    for module_slug, grouped_operations in operations_by_tag.items():
        haystack = " ".join(
            " ".join([operation["operation_id"], operation["tag"], operation["path"]])
            for operation in grouped_operations
        )
        if len(scope_terms & scope_tokens(haystack)) >= 1:
            controller_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.controller.ts"
            service_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.service.ts"
            repository_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.repository.ts"
            targets.add(str(controller_path.relative_to(output_dir)))
            targets.add(str(service_path.relative_to(output_dir)))
            targets.add(str(repository_path.relative_to(output_dir)))

    for page in ui_pages:
        surface = str(page.get("page_title") or "").strip()
        if surface and len(scope_terms & ui_page_interest_tokens(surface, page)) >= 1:
            page_path = output_dir / "apps" / "web" / "app" / ui_page_route_segment(page, surface) / "page.tsx"
            targets.add(str(page_path.relative_to(output_dir)))

    return sorted(targets)


def scaffold_phase3_implementation(
    *,
    esp_text: str,
    openapi_spec: dict[str, object],
    phase3_trace_registry: dict[str, Any],
    output_dir: Path,
    ui_ia_contract_path: Path | None = None,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
    synthesis_brief: dict[str, Any] | None = None,
    service_authoring_packet: dict[str, Any] | None = None,
    module_synthesis_bundle_path: Path | None = None,
    action_card_execution_map: dict[str, Any] | None = None,
    action_card_execution_map_path: Path | None = None,
    business_behavior_authoring_plan: dict[str, Any] | None = None,
    business_behavior_authoring_plan_path: Path | None = None,
    agentic_semantic_decisions: dict[str, Any] | None = None,
    project_implementation_conventions: dict[str, Any] | None = None,
    module_implementation_briefs: dict[str, Any] | None = None,
    action_card_direct_implementation_driver: dict[str, Any] | None = None,
) -> dict[str, object]:
    operations = parse_openapi_operations(openapi_spec)
    wp_rows = build_wp_lookup(esp_text)
    primary_surfaces = extract_nested_bullet_items(esp_text, "primary_surfaces")
    ui_pages = load_ui_pages(output_dir=output_dir, primary_surfaces=primary_surfaces, ui_ia_contract_path=ui_ia_contract_path)
    app_context = ui_app_context(ui_pages)
    compiled_bindings = load_compiled_bindings(output_dir=output_dir, ui_ia_contract_path=ui_ia_contract_path)
    runtime_specs = build_runtime_operation_specs(openapi_spec, compiled_bindings=compiled_bindings)
    module_synthesis_candidate_ledger: dict[str, Any] | None = None
    module_synthesis_bundle: dict[str, Any] | None = None
    module_synthesis_authoring_context: dict[str, Any] | None = None
    module_synthesis_summary: dict[str, Any] = {
        "mode": "disabled",
        "selected_module": "",
        "authoring_context_path": "",
        "authoring_context_sha256": "",
        "candidate_ledger_path": "",
        "selected_manifest_path": "",
        "module_behavior_plan_path": "",
        "renderer_bypass_evidence_path": "",
        "human_review_packet_path": "",
        "tvg_quality_audit_path": "",
        "obligation_consumption_audit_path": "",
        "module_rewrite_packet_path": "",
        "bypassed_renderers": [],
    }
    if module_synthesis_bundle_path is not None:
        module_synthesis_candidate_ledger = build_module_candidate_ledger(
            openapi_spec=openapi_spec,
            phase3_trace_registry=phase3_trace_registry,
            operation_specs=runtime_specs,
        )
        manifest_path = module_synthesis_bundle_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("module synthesis bundle manifest must be a JSON object")
        selected_module = str(manifest.get("selected_module", "")).strip()
        module_synthesis_authoring_context = build_module_authoring_context(
            openapi_spec=openapi_spec,
            candidate_ledger=module_synthesis_candidate_ledger,
            selected_module=selected_module,
            phase3_trace_registry=phase3_trace_registry,
            operation_specs=runtime_specs,
            behavior_card_models=behavior_card_models,
        )
        module_synthesis_bundle = load_module_synthesis_bundle(
            bundle_root=module_synthesis_bundle_path,
            candidate_ledger=module_synthesis_candidate_ledger,
            authoring_context=module_synthesis_authoring_context,
        )
        quality_paths = write_module_synthesis_quality_evidence(
            output_dir=output_dir,
            bundle=module_synthesis_bundle,
        )
        module_synthesis_summary["module_behavior_plan_path"] = quality_paths["module_behavior_plan_path"]
        module_synthesis_summary["tvg_quality_audit_path"] = quality_paths["tvg_quality_audit_path"]
        module_synthesis_summary["obligation_consumption_audit_path"] = quality_paths["obligation_consumption_audit_path"]
        module_synthesis_summary["module_rewrite_packet_path"] = quality_paths["module_rewrite_packet_path"]
        quality_audit = module_synthesis_bundle.get("quality_audit", {})
        if not isinstance(quality_audit, dict) or quality_audit.get("overall_quality_gate") != "pass":
            failures = "; ".join(str(item) for item in quality_audit.get("failures", []) if str(item).strip()) if isinstance(quality_audit, dict) else ""
            raise ValueError(f"module synthesis quality gate failed: {failures}")

    module_targets_by_contract: dict[str, list[str]] = {}
    operations_by_tag: dict[str, list[dict[str, str]]] = {}
    for operation in operations:
        operations_by_tag.setdefault(
            stable_slug(
                operation["tag"],
                fallback=str(operation.get("operation_id") or "default"),
            ),
            [],
        ).append(operation)

    default_tenant_id = infer_default_tenant(runtime_specs)
    write_text(output_dir / "apps" / "api" / "src" / "common" / "envelope.ts", render_envelope_module())
    write_text(output_dir / "apps" / "api" / "src" / "common" / "errors.ts", render_errors_module())
    write_text(output_dir / "apps" / "api" / "src" / "common" / "pagination.ts", render_pagination_module())
    write_text(output_dir / "apps" / "api" / "src" / "common" / "auth-session.ts", render_auth_session_module())
    write_text(output_dir / "apps" / "api" / "src" / "common" / "runtime-adapter.ts", render_runtime_adapter_module())
    write_text(
        output_dir / "apps" / "api" / "src" / "common" / "operation-support.ts",
        render_generated_runtime(runtime_specs, default_tenant_id),
    )
    write_text(
        output_dir / "apps" / "api" / "src" / "common" / "generated-runtime.ts",
        render_generated_runtime_facade(),
    )
    write_text(
        output_dir / "apps" / "api" / "src" / "generated-api-router.ts",
        render_generated_api_router(
            operations_by_tag=operations_by_tag,
            operation_specs=runtime_specs,
            compiled_bindings=compiled_bindings,
        ),
    )
    write_text(
        output_dir / "tests" / "support" / "runtime-test-kit.ts",
        render_runtime_test_kit(operations_by_tag=operations_by_tag),
    )
    write_text(
        output_dir / "tests" / "support" / "backend-runtime-harness.ts",
        render_backend_runtime_harness(),
    )
    foundation_unit_test_paths = backend_foundation_unit_test_paths()
    for relative_path in foundation_unit_test_paths:
        write_text(output_dir / Path(relative_path), render_backend_foundation_unit_test(runtime_specs))
    write_phase3_diagnostic_surface(
        output_dir,
        "generated-runtime-positioning.md",
        render_generated_runtime_positioning(),
    )
    write_text(output_dir / "apps" / "web" / "app" / "page.tsx", render_home_page(ui_pages, operations, wp_rows))
    write_text(output_dir / "apps" / "web" / "app" / "ui-app.tsx", render_ui_app(ui_pages))
    auth_entry_route = normalize_ui_route(((app_context.get("route_guard_policy") if isinstance(app_context.get("route_guard_policy"), dict) else {}) or {}).get("auth_entry_route") or "")
    if auth_entry_route and auth_entry_route != "/":
        write_text(output_dir / "apps" / "web" / "app" / auth_entry_route.strip("/") / "page.tsx", render_auth_entry_page(ui_pages))
    write_text(output_dir / "apps" / "web" / "app" / "workflow-storage.ts", render_workflow_storage_module())
    write_text(output_dir / "apps" / "web" / "app" / "role-session-storage.ts", render_role_session_storage_module())
    write_text(output_dir / "apps" / "web" / "app" / "workflow-progress-storage.ts", render_workflow_progress_storage_module())

    written_modules: list[str] = []
    written_repositories: list[str] = []
    written_unit_tests: list[str] = [str(output_dir / Path(relative_path)) for relative_path in foundation_unit_test_paths]
    contract_target_lookup = build_contract_test_target_lookup(list(operations))
    for module_slug, grouped_operations in operations_by_tag.items():
        module_class = camel_case(module_slug)
        controller_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.controller.ts"
        service_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.service.ts"
        repository_path = output_dir / "apps" / "api" / "src" / "modules" / module_slug / f"{module_slug}.repository.ts"
        unit_test_path = output_dir / backend_module_unit_test_path(module_slug)
        module_synthesis_units = synthesis_units_for_module(
            synthesis_brief,
            module_slug=module_slug,
            operations=grouped_operations,
        )
        write_text(
            controller_path,
            render_controller_module(module_class, grouped_operations, module_slug),
        )
        if module_synthesis_bundle is not None and str(module_synthesis_bundle.get("selected_module", "")) == module_slug:
            files_by_role = module_synthesis_bundle["files_by_role"]
            write_text(service_path, str(files_by_role["service"]["content"]))
            write_text(repository_path, str(files_by_role["repository"]["content"]))
            write_text(unit_test_path, str(files_by_role["unit-test"]["content"]))
        else:
            write_text(
                service_path,
                render_service_module(
                    module_class,
                    grouped_operations,
                    module_slug,
                    behavior_card_models=behavior_card_models,
                    operation_specs=runtime_specs,
                    synthesis_units=module_synthesis_units,
                    authoring_packet=service_authoring_packet,
                    business_behavior_authoring_plan=business_behavior_authoring_plan,
                    action_card_execution_map=action_card_execution_map,
                    action_card_direct_implementation_driver=action_card_direct_implementation_driver,
                    agentic_semantic_decisions=agentic_semantic_decisions,
                    module_implementation_briefs=module_implementation_briefs,
                ),
            )
            write_text(
                repository_path,
                render_repository_module(
                    module_class,
                    grouped_operations,
                    module_slug,
                    runtime_specs,
                    behavior_card_models=behavior_card_models,
                    business_behavior_authoring_plan=business_behavior_authoring_plan,
                    action_card_execution_map=action_card_execution_map,
                    action_card_direct_implementation_driver=action_card_direct_implementation_driver,
                    agentic_semantic_decisions=agentic_semantic_decisions,
                    module_implementation_briefs=module_implementation_briefs,
                ),
            )
            write_text(
                unit_test_path,
                render_backend_module_unit_test(
                    module_slug,
                    grouped_operations,
                    runtime_specs,
                    behavior_card_models=behavior_card_models,
                    synthesis_units=module_synthesis_units,
                    business_behavior_authoring_plan=business_behavior_authoring_plan,
                    action_card_execution_map=action_card_execution_map,
                    action_card_direct_implementation_driver=action_card_direct_implementation_driver,
                    agentic_semantic_decisions=agentic_semantic_decisions,
                    module_implementation_briefs=module_implementation_briefs,
                ),
            )
        written_modules.extend([str(controller_path), str(service_path)])
        written_repositories.append(str(repository_path))
        written_unit_tests.append(str(unit_test_path))
        for operation in grouped_operations:
            contract_path = (
                f"tests/contracts/{contract_target_lookup[(operation['operation_id'], str(operation['method']).upper(), str(operation['path']))]}"
            )
            module_targets_by_contract.setdefault(contract_path, [])
            module_targets_by_contract[contract_path].extend(
                [
                    str(controller_path.relative_to(output_dir)),
                    str(service_path.relative_to(output_dir)),
                    str(repository_path.relative_to(output_dir)),
                ]
            )

    if module_synthesis_candidate_ledger is not None and module_synthesis_bundle is not None:
        module_synthesis_summary = write_module_synthesis_evidence(
            output_dir=output_dir,
            candidate_ledger=module_synthesis_candidate_ledger,
            bundle=module_synthesis_bundle,
            authoring_context=module_synthesis_authoring_context,
        )

    written_pages: list[str] = []
    for index, page in enumerate(ui_pages):
        surface = str(page.get("page_title") or "").strip()
        if not surface:
            continue
        route = ui_page_route_segment(page, surface)
        page_path = output_dir / "apps" / "web" / "app" / route / "page.tsx"
        unit_test_path = output_dir / frontend_surface_unit_test_path(route)
        write_text(
            page_path,
            render_page_component(
                surface,
                page_contract=page,
                related_operations=related_operations_for_surface(surface, operations, page_contract=page),
                related_work_packages=related_work_packages_for_surface(surface, wp_rows, page_contract=page),
                navigation={
                    "previous_route": str(ui_pages[index - 1].get("route", "")).strip() if index > 0 else "",
                    "next_route": str(ui_pages[index + 1].get("route", "")).strip() if index + 1 < len(ui_pages) else "",
                },
                app_context=app_context,
            ),
        )
        write_text(unit_test_path, render_frontend_page_unit_test(route))
        written_pages.append(str(page_path))
        written_unit_tests.append(str(unit_test_path))

    work_package_plans: list[str] = []
    inferred_targets_by_wp: dict[str, list[str]] = {}
    for row in wp_rows:
        wp_id = str(row.get("wp_id", "")).strip()
        scope = str(row.get("scope", row.get("implementation_scope", ""))).strip()
        acceptance_criteria = str(row.get("acceptance_criteria", "")).strip()
        target = output_dir / "work-packages" / wp_id.lower() / "implementation-plan.md"
        write_text(
            target,
            "\n".join(
                [
                    f"# {wp_id} Implementation Plan",
                    "",
                    f"- scope: {scope}",
                    f"- acceptance_criteria: {acceptance_criteria}",
                    f"- estimated_effort: {str(row.get('estimated_effort', 'n/a')).strip()}",
                    f"- depends_on: {', '.join(row.get('depends_on', [])) or 'none'}",
                    f"- linked_rbi_or_slice: {', '.join(row.get('linked_rbi_or_slice', [])) or 'none'}",
                    "",
                ]
            ),
        )
        work_package_plans.append(str(target))
        inferred_targets_by_wp[wp_id] = infer_targets_from_scope(
            scope=scope,
            acceptance_criteria=acceptance_criteria,
            operations_by_tag=operations_by_tag,
            ui_pages=ui_pages,
            output_dir=output_dir,
        )

    trace_rows = phase3_trace_registry.get("rows", [])
    if not isinstance(trace_rows, list):
        raise ValueError("phase-3 trace registry must contain rows")

    direct_work_package_map: dict[str, list[str]] = {}
    test_target_to_source_ids: dict[str, set[str]] = {}
    for row in trace_rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_subject = str(row.get("source_subject", "")).strip()
        direct_work_package_map[source_id] = suggest_work_packages(
            source_id,
            source_subject,
            wp_rows,
            source_type=str(row.get("source_type", "")).strip(),
            verification_hook=str(row.get("verification_hook", "")).strip(),
        )
        for test_target in [str(item) for item in row.get("test_targets", []) if str(item).strip()]:
            test_target_to_source_ids.setdefault(test_target, set()).add(source_id)

    binding_rows: list[dict[str, Any]] = []
    contract_operation_by_test = operation_by_contract_test_target(operations)
    for row in trace_rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_subject = str(row.get("source_subject", "")).strip()
        test_targets = [str(item) for item in row.get("test_targets", []) if str(item).strip()]
        implementation_targets: list[str] = []
        for test_target in test_targets:
            implementation_targets.extend(module_targets_by_contract.get(test_target, []))
        implementation_targets.extend(foundation_implementation_targets_for_test_targets(test_targets))
        implementation_targets = sorted(set(implementation_targets))
        work_packages = list(direct_work_package_map.get(source_id, []))
        if not work_packages:
            for test_target in test_targets:
                for related_source_id in sorted(test_target_to_source_ids.get(test_target, set())):
                    if related_source_id == source_id:
                        continue
                    work_packages.extend(direct_work_package_map.get(related_source_id, []))
        work_packages = sorted(set(work_packages))
        if not work_packages and implementation_targets:
            work_packages = infer_work_packages_from_targets(
                implementation_targets=implementation_targets,
                inferred_targets_by_wp=inferred_targets_by_wp,
            )
        if not work_packages:
            work_packages = infer_work_packages_from_replay_overlap(
                source_row=row,
                trace_rows=trace_rows,
            )
        if not implementation_targets and work_packages:
            for wp_id in work_packages:
                implementation_targets.extend(inferred_targets_by_wp.get(wp_id, []))
            if not implementation_targets:
                implementation_targets.extend(
                    [str((Path("work-packages") / wp_id.lower() / "implementation-plan.md")) for wp_id in work_packages]
                )
        binding_row = {
            "source_id": source_id,
            "source_type": str(row.get("source_type", "")).strip(),
            "source_subject": source_subject,
            "test_targets": sorted(set(test_targets)),
            "implementation_targets": sorted(set(implementation_targets)),
            "work_packages": work_packages,
            "runtime_evidence_refs": sorted(set(test_targets)),
            "binding_status": "suggested",
        }
        operation_id = infer_binding_operation_id(
            source_subject=source_subject,
            test_targets=sorted(set(test_targets)),
            operations=operations,
            contract_operation_by_test=contract_operation_by_test,
        )
        if operation_id:
            binding_row["operation_id"] = operation_id
            behavior_model = (behavior_card_models or {}).get(operation_id)
            operation_semantics = (
                behavior_model.get("operation_semantics", {})
                if isinstance(behavior_model, dict) and isinstance(behavior_model.get("operation_semantics"), dict)
                else {}
            )
            if operation_semantics:
                binding_row["operation_semantics"] = dict(operation_semantics)
        binding_rows.append(binding_row)

    propagate_shared_test_bindings(
        binding_rows=binding_rows,
        inferred_targets_by_wp=inferred_targets_by_wp,
    )
    rebind_cross_operation_test_rows(
        binding_rows=binding_rows,
        operations=operations,
        output_dir=output_dir,
        inferred_targets_by_wp=inferred_targets_by_wp,
        wp_rows=wp_rows,
    )
    propagate_shared_test_bindings(
        binding_rows=binding_rows,
        inferred_targets_by_wp=inferred_targets_by_wp,
    )
    append_generated_unit_test_bindings(binding_rows)
    append_generated_sql_test_bindings(binding_rows, output_dir=output_dir)

    action_card_projection_default = action_card_execution_map is not None and business_behavior_authoring_plan is not None
    business_behavior_plan_default = business_behavior_authoring_plan is not None and not action_card_projection_default
    semantic_decision_summary = (
        agentic_semantic_decisions.get("summary", {})
        if isinstance(agentic_semantic_decisions, dict) and isinstance(agentic_semantic_decisions.get("summary"), dict)
        else {}
    )
    project_convention_summary = (
        project_implementation_conventions.get("summary", {})
        if isinstance(project_implementation_conventions, dict)
        and isinstance(project_implementation_conventions.get("summary"), dict)
        else {}
    )
    module_implementation_summary = (
        module_implementation_briefs.get("summary", {})
        if isinstance(module_implementation_briefs, dict)
        and isinstance(module_implementation_briefs.get("summary"), dict)
        else {}
    )
    action_card_direct_driver_summary = (
        action_card_direct_implementation_driver.get("summary", {})
        if isinstance(action_card_direct_implementation_driver, dict)
        and isinstance(action_card_direct_implementation_driver.get("summary"), dict)
        else {}
    )
    report = {
        "artifact_kind": "compiled-binding-artifact",
        "compiled_bindings": compiled_bindings,
        "rows": binding_rows,
        "metadata": {
            "agentic_body_authoring_default": True,
            "agentic_body_authoring_mode": "default-p3-mainline",
            "agentic_body_authoring_control_boundary": "workflow supplies OpenAPI/runtime/trace context; Agentic body authoring kernel shapes default service/repository/unit bodies; evidence verifies runtime and caps claims",
            "agentic_body_authoring_gate_policy": "no new F5/F6-style gate controls default content truth",
            "business_behavior_authoring_plan_default": business_behavior_plan_default,
            "business_behavior_authoring_plan_kind": str((business_behavior_authoring_plan or {}).get("artifact_kind", ""))
            if business_behavior_plan_default
            else "",
            "business_behavior_authoring_plan_path": str(business_behavior_authoring_plan_path or "")
            if business_behavior_plan_default
            else "",
            "action_card_execution_map_default": action_card_execution_map is not None,
            "action_card_authoring_projection_default": action_card_projection_default,
            "action_card_authoring_projection_persisted": False,
            "action_card_rich_context_persisted": False,
            "agentic_semantic_authoring_default": agentic_semantic_decisions is not None,
            "agentic_semantic_authoring_mode": str((agentic_semantic_decisions or {}).get("mode", "")),
            "agentic_semantic_decision_count": int(semantic_decision_summary.get("agentic_semantic_decision_count", 0) or 0),
            "script_semantic_default_count": int(semantic_decision_summary.get("script_semantic_default_count", 0) or 0),
            "owner_not_declared_count": int(semantic_decision_summary.get("owner_not_declared_count", 0) or 0),
            "aggregate_review_bound_count": int(semantic_decision_summary.get("aggregate_review_bound_count", 0) or 0),
            "default_heavy_artifact_count": int(semantic_decision_summary.get("default_heavy_artifact_count", 0) or 0),
            "project_convention_synthesis_default": project_implementation_conventions is not None,
            "project_convention_default_heavy_artifact_count": int(
                project_convention_summary.get("default_heavy_artifact_count", 0) or 0
            ),
            "agentic_module_implementation_brief_default": module_implementation_briefs is not None,
            "agentic_module_implementation_brief_mode": str((module_implementation_briefs or {}).get("mode", "")),
            "agentic_module_implementation_brief_module_count": int(
                module_implementation_summary.get("module_count", 0) or 0
            ),
            "agentic_module_implementation_brief_persisted": False,
            "agentic_module_implementation_default_heavy_artifact_count": int(
                module_implementation_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "action_card_direct_implementation_driver_default": action_card_direct_implementation_driver is not None,
            "action_card_direct_implementation_driver_kind": str(
                (action_card_direct_implementation_driver or {}).get("artifact_kind", "")
            ),
            "action_card_direct_implementation_driver_persisted": False,
            "action_card_direct_implementation_driver_operation_count": int(
                action_card_direct_driver_summary.get("operation_count", 0) or 0
            ),
            "action_card_direct_implementation_default_heavy_artifact_count": int(
                action_card_direct_driver_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "module_synthesis_mode": module_synthesis_summary["mode"],
        },
        "summary": {
            "binding_count": len(binding_rows),
            "compiled_binding_count": len(compiled_bindings),
            "work_package_count": len(wp_rows),
            "module_stub_count": len(written_modules),
            "repository_stub_count": len(written_repositories),
            "frontend_page_count": len(written_pages),
            "unit_test_count": len(written_unit_tests),
            "work_package_plan_count": len(work_package_plans),
            "runtime_positioning_present": True,
            "synthesis_selected_unit_count": len(synthesis_brief.get("selected_semantic_units", []))
            if isinstance(synthesis_brief, dict) and isinstance(synthesis_brief.get("selected_semantic_units"), list)
            else 0,
            "agentic_body_authoring_default": True,
            "agentic_body_authoring_mode": "default-p3-mainline",
            "business_behavior_authoring_plan_default": business_behavior_plan_default,
            "business_behavior_authoring_plan_path": str(business_behavior_authoring_plan_path or "")
            if business_behavior_plan_default
            else "",
            "action_card_authoring_projection_default": action_card_projection_default,
            "action_card_authoring_projection_persisted": False,
            "action_card_rich_context_persisted": False,
            "agentic_semantic_authoring_default": agentic_semantic_decisions is not None,
            "agentic_semantic_decision_count": int(semantic_decision_summary.get("agentic_semantic_decision_count", 0) or 0),
            "script_semantic_default_count": int(semantic_decision_summary.get("script_semantic_default_count", 0) or 0),
            "owner_not_declared_count": int(semantic_decision_summary.get("owner_not_declared_count", 0) or 0),
            "aggregate_review_bound_count": int(semantic_decision_summary.get("aggregate_review_bound_count", 0) or 0),
            "default_heavy_artifact_count": int(semantic_decision_summary.get("default_heavy_artifact_count", 0) or 0),
            "project_convention_synthesis_default": project_implementation_conventions is not None,
            "project_convention_default_heavy_artifact_count": int(
                project_convention_summary.get("default_heavy_artifact_count", 0) or 0
            ),
            "agentic_module_implementation_brief_default": module_implementation_briefs is not None,
            "agentic_module_implementation_brief_module_count": int(
                module_implementation_summary.get("module_count", 0) or 0
            ),
            "agentic_module_implementation_brief_persisted": False,
            "agentic_module_implementation_default_heavy_artifact_count": int(
                module_implementation_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "action_card_direct_implementation_driver_default": action_card_direct_implementation_driver is not None,
            "action_card_direct_implementation_driver_persisted": False,
            "action_card_direct_implementation_driver_operation_count": int(
                action_card_direct_driver_summary.get("operation_count", 0) or 0
            ),
            "action_card_direct_implementation_default_heavy_artifact_count": int(
                action_card_direct_driver_summary.get("persisted_default_heavy_artifact_count", 0) or 0
            ),
            "business_behavior_authoring_plan_operation_count": (business_behavior_authoring_plan or {})
            .get("summary", {})
            .get("operation_count", 0)
            if isinstance((business_behavior_authoring_plan or {}).get("summary", {}), dict)
            else 0,
            "module_synthesis_mode": module_synthesis_summary["mode"],
            "module_synthesis_selected_module": module_synthesis_summary["selected_module"],
            "module_synthesis_authoring_context_path": module_synthesis_summary["authoring_context_path"],
            "module_synthesis_authoring_context_sha256": module_synthesis_summary["authoring_context_sha256"],
            "module_synthesis_behavior_plan_path": module_synthesis_summary["module_behavior_plan_path"],
            "module_synthesis_renderer_bypass_evidence_path": module_synthesis_summary["renderer_bypass_evidence_path"],
            "module_synthesis_human_review_packet_path": module_synthesis_summary["human_review_packet_path"],
            "module_synthesis_tvg_quality_audit_path": module_synthesis_summary["tvg_quality_audit_path"],
            "module_synthesis_obligation_consumption_audit_path": module_synthesis_summary["obligation_consumption_audit_path"],
            "module_synthesis_rewrite_packet_path": module_synthesis_summary["module_rewrite_packet_path"],
        },
    }
    output_path = output_dir / "implementation-bindings.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output_path": str(output_path), **report["summary"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase-3 implementation bindings and source scaffolds")
    parser.add_argument("--esp", required=True)
    parser.add_argument("--openapi", required=True)
    parser.add_argument("--trace-registry", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ui-ia-contract")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir).resolve()
    summary = scaffold_phase3_implementation(
        esp_text=Path(args.esp).resolve().read_text(encoding="utf-8"),
        openapi_spec=load_openapi_document(Path(args.openapi).resolve()),
        phase3_trace_registry=json.loads(Path(args.trace_registry).resolve().read_text(encoding="utf-8")),
        output_dir=output_dir,
        ui_ia_contract_path=Path(args.ui_ia_contract).resolve() if args.ui_ia_contract else None,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
