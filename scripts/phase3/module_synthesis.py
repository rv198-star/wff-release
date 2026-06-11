from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from phase3.contract_test_scaffolder import build_contract_test_target_lookup
from phase3.contract_tools import slugify
from phase3.implementation_binding_tools import backend_module_unit_test_path, parse_openapi_operations


REQUIRED_ROLES = ("service", "repository", "unit-test")
BUNDLE_KIND = "phase3-module-synthesis-bundle.v1"
LEDGER_KIND = "phase3-module-synthesis-candidate-ledger.v1"
AUTHORING_CONTEXT_KIND = "phase3-module-authoring-context.v1"
QUALITY_AUDIT_KIND = "phase3-module-tvg-quality-audit.v1"
REWRITE_PACKET_KIND = "phase3-module-rewrite-packet.v1"
BEHAVIOR_PLAN_KIND = "phase3-module-behavior-plan.v1"
OBLIGATION_CONSUMPTION_AUDIT_KIND = "phase3-module-obligation-consumption-audit.v1"
REQUIRED_TVG_AXES = ("behavior-depth", "evidence-depth", "failure-depth")


def module_file_paths(module_slug: str) -> dict[str, str]:
    return {
        "service": f"apps/api/src/modules/{module_slug}/{module_slug}.service.ts",
        "repository": f"apps/api/src/modules/{module_slug}/{module_slug}.repository.ts",
        "unit-test": backend_module_unit_test_path(module_slug),
    }


def _json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def candidate_ledger_sha256(ledger: dict[str, Any]) -> str:
    return _json_hash(ledger)


def module_authoring_context_sha256(context: dict[str, Any]) -> str:
    return _json_hash(context)


def _operation_id(operation: dict[str, str]) -> str:
    return str(operation.get("operation_id") or f"{operation.get('method', '')}-{operation.get('path', '')}").strip()


def _module_slug(operation: dict[str, str]) -> str:
    return slugify(str(operation.get("tag", "")).strip()) or slugify(_operation_id(operation)) or "default"


def _is_disqualified_module(module_slug: str) -> bool:
    normalized = module_slug.lower()
    tokens = set(normalized.replace("-", "_").split("_")) | set(normalized.split("-"))
    disqualified = {
        "auth",
        "authentication",
        "authorization",
        "health",
        "healthcheck",
        "metrics",
        "runtime",
        "generated",
        "utility",
        "utilities",
        "shared",
        "infra",
        "infrastructure",
    }
    return bool(tokens & disqualified)


def _trace_rows_for_module(
    *,
    module_slug: str,
    operation_ids: list[str],
    phase3_trace_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = phase3_trace_registry.get("rows", [])
    if not isinstance(rows, list):
        return []
    selected: list[dict[str, Any]] = []
    operation_tokens = {operation_id.lower() for operation_id in operation_ids if operation_id}
    module_marker = f"/{module_slug}/"
    unit_marker = f"/{module_slug}.unit.test.ts"
    for row in rows:
        if not isinstance(row, dict):
            continue
        haystack = " ".join(
            [
                str(row.get("trace_id", "")),
                str(row.get("source_ref", "")),
                str(row.get("operation_id", "")),
                " ".join(str(item) for item in row.get("implementation_targets", []) if str(item).strip())
                if isinstance(row.get("implementation_targets"), list)
                else "",
                " ".join(str(item) for item in row.get("test_targets", []) if str(item).strip())
                if isinstance(row.get("test_targets"), list)
                else "",
            ]
        ).lower()
        if any(token and token.lower() in haystack for token in operation_tokens) or module_marker in haystack or unit_marker in haystack:
            selected.append(row)
    return selected


def _invariant_signal_count(operation_ids: list[str], operation_specs: dict[str, dict[str, Any]]) -> int:
    signal_count = 0
    tokens = ("status", "state", "lifecycle", "version", "tenant", "owner", "permission", "capacity")
    for operation_id in operation_ids:
        spec = operation_specs.get(operation_id, {})
        text = json.dumps(spec, ensure_ascii=False).lower() if isinstance(spec, dict) else ""
        if any(token in text for token in tokens):
            signal_count += 1
    return signal_count


def build_module_candidate_ledger(
    *,
    openapi_spec: dict[str, object],
    phase3_trace_registry: dict[str, Any],
    operation_specs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    operation_specs = operation_specs or {}
    operations_by_module: dict[str, list[dict[str, str]]] = {}
    for operation in parse_openapi_operations(openapi_spec):
        operations_by_module.setdefault(_module_slug(operation), []).append(operation)

    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for module_slug, operations in sorted(operations_by_module.items()):
        operations = sorted(operations, key=lambda operation: _operation_id(operation))
        operation_ids = [_operation_id(operation) for operation in operations]
        expected_paths = module_file_paths(module_slug)
        if _is_disqualified_module(module_slug):
            rejected.append({"module_slug": module_slug, "reason": "infrastructure-or-non-business-module"})
            continue
        trace_rows = _trace_rows_for_module(
            module_slug=module_slug,
            operation_ids=operation_ids,
            phase3_trace_registry=phase3_trace_registry,
        )
        if not trace_rows:
            rejected.append({"module_slug": module_slug, "reason": "missing-source-or-phase2-trace-reference"})
            continue
        invariant_count = _invariant_signal_count(operation_ids, operation_specs)
        score = 0
        score += len(operation_ids) * 2
        score += 2
        score += invariant_count * 3
        if len(operation_ids) > 1:
            score += 2
        score += len(trace_rows)
        eligible.append(
            {
                "module_slug": module_slug,
                "score": score,
                "operation_ids": operation_ids,
                "operation_count": len(operation_ids),
                "ownership_scope": [expected_paths[role] for role in REQUIRED_ROLES],
                "service_path": expected_paths["service"],
                "repository_path": expected_paths["repository"],
                "unit_test_path": expected_paths["unit-test"],
                "source_references": sorted(
                    {
                        str(row.get("trace_id") or row.get("source_ref") or row.get("operation_id") or "").strip()
                        for row in trace_rows
                        if str(row.get("trace_id") or row.get("source_ref") or row.get("operation_id") or "").strip()
                    }
                ),
                "score_reasons": {
                    "operation_count": len(operation_ids),
                    "repository_backed": True,
                    "source_supported_invariant_count": invariant_count,
                    "trace_row_count": len(trace_rows),
                },
            }
        )
    eligible.sort(key=lambda item: (-int(item["score"]), str(item["module_slug"])))
    return {
        "artifact_kind": LEDGER_KIND,
        "eligible_candidates": eligible,
        "rejected_candidates": rejected,
        "selection_rule": "agentic-select-one-eligible-module",
    }


def _selected_candidate(candidate_ledger: dict[str, Any], selected_module: str) -> dict[str, Any]:
    for candidate in candidate_ledger.get("eligible_candidates", []):
        if isinstance(candidate, dict) and str(candidate.get("module_slug", "")).strip() == selected_module:
            return candidate
    raise ValueError(f"selected module is not eligible for authoring context: {selected_module}")


def _source_references_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    refs: set[str] = set()
    for row in rows:
        for key in ("trace_id", "source_id", "source_ref", "operation_id"):
            value = str(row.get(key, "")).strip()
            if value:
                refs.add(value)
    return sorted(refs)


def _behavior_obligations(model: dict[str, Any]) -> dict[str, Any]:
    obligation_keys = (
        "steps",
        "operation_semantics",
        "error_codes",
        "persistence_effects",
        "invariants",
        "state_transition",
        "transaction_rule",
        "audit_effect",
        "authorization",
        "rbac",
        "risk_controls",
        "evidence_keys",
    )
    obligations: dict[str, Any] = {}
    for key in obligation_keys:
        if key in model and model[key] not in (None, "", [], {}):
            obligations[key] = model[key]
    return obligations


def _runtime_obligation_fields(spec: dict[str, Any]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    field_map = {
        "requestExample": "request_example",
        "requestRequiredFields": "request_required_fields",
        "responseExample": "response_example",
        "failureCases": "failure_cases",
        "successStatus": "success_status",
        "pathParams": "path_params",
        "queryParams": "query_params",
        "pagination": "pagination",
        "idempotency": "idempotency",
        "retryability": "retryability",
    }
    for source_key, target_key in field_map.items():
        value = spec.get(source_key)
        if value not in (None, "", [], {}):
            selected[target_key] = value
    return selected


def build_module_authoring_context(
    *,
    openapi_spec: dict[str, object],
    candidate_ledger: dict[str, Any],
    selected_module: str,
    phase3_trace_registry: dict[str, Any],
    operation_specs: dict[str, dict[str, Any]] | None = None,
    behavior_card_models: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    operation_specs = operation_specs or {}
    behavior_card_models = behavior_card_models or {}
    selected_module = slugify(selected_module)
    candidate = _selected_candidate(candidate_ledger, selected_module)
    selected_operation_ids = [str(item).strip() for item in candidate.get("operation_ids", []) if str(item).strip()]
    selected_operations = [
        operation
        for operation in parse_openapi_operations(openapi_spec)
        if _module_slug(operation) == selected_module and _operation_id(operation) in selected_operation_ids
    ]
    selected_operations.sort(key=lambda operation: (_operation_id(operation), str(operation.get("method", "")), str(operation.get("path", ""))))
    trace_rows = _trace_rows_for_module(
        module_slug=selected_module,
        operation_ids=selected_operation_ids,
        phase3_trace_registry=phase3_trace_registry,
    )
    contract_targets = build_contract_test_target_lookup(list(selected_operations))
    operation_contexts: list[dict[str, Any]] = []
    for operation in selected_operations:
        operation_id = _operation_id(operation)
        method = str(operation.get("method", "")).upper()
        path = str(operation.get("path", "")).strip()
        runtime_spec = operation_specs.get(operation_id, {})
        behavior_model = behavior_card_models.get(operation_id, {})
        operation_contexts.append(
            {
                "operation_id": operation_id,
                "method": method,
                "path": path,
                "tag": str(operation.get("tag", "")).strip(),
                "contract_test_target": f"tests/contracts/{contract_targets[(operation_id, method, path)]}",
                **_runtime_obligation_fields(runtime_spec if isinstance(runtime_spec, dict) else {}),
                "behavior_obligations": _behavior_obligations(behavior_model if isinstance(behavior_model, dict) else {}),
            }
        )
    public_surface_obligations = {
        "preserve_frozen_response_shape": True,
        "forbid_extra_public_meta_fields": True,
        "map_failures_to_declared_error_envelope": True,
        "do_not_raise_formal_claims_without_evidence_bridge": True,
    }
    auth_session_obligations = {
        "required_claims": ["tenant_id", "subject_id", "session_id", "roles"],
        "accepted_claim_aliases": {
            "tenant_id": ["tenantId"],
            "subject_id": ["sub"],
            "session_id": ["sid"],
            "roles": ["role"],
        },
        "default_required_role": ["authenticated"],
        "rule": "When selected-module code or tests invoke runtime helpers directly, provide complete auth_context claims instead of relying on HTTP harness token injection.",
    }
    persistence_audit_obligations = {
        "preserve_declared_persistence_effects": True,
        "preserve_declared_transaction_or_rollback_rules": True,
        "preserve_declared_audit_effects": True,
        "derive_from_behavior_card_or_runtime_spec": True,
    }
    method_guidance = {
        "wae": "Workflow keeps outer order and evidence boundaries; Agentic owns selected-module semantics and implementation judgment.",
        "tvg": "Use bounded value-gain rounds only when the module is structurally complete but weak in practical decision, evidence, review, reuse, or handoff value.",
        "btgsb": "If generated behavior surprises runtime evidence, return from action to reproducible signal and falsifiable problem before rewriting.",
    }
    source_references = _source_references_from_rows(trace_rows)
    contract_test_targets = sorted(
        {
            str(operation_context.get("contract_test_target", "")).strip()
            for operation_context in operation_contexts
            if str(operation_context.get("contract_test_target", "")).strip()
        }
    )
    behavior_obligations_by_operation = {
        str(operation_context.get("operation_id", "")).strip(): operation_context.get("behavior_obligations", {})
        for operation_context in operation_contexts
        if str(operation_context.get("operation_id", "")).strip()
    }
    return {
        "artifact_kind": AUTHORING_CONTEXT_KIND,
        "selected_module": selected_module,
        "ownership_scope": [module_file_paths(selected_module)[role] for role in REQUIRED_ROLES],
        "candidate_ledger_sha256": candidate_ledger_sha256(candidate_ledger),
        "source_references": source_references,
        "operations": operation_contexts,
        "public_surface_obligations": public_surface_obligations,
        "auth_session_obligations": auth_session_obligations,
        "persistence_audit_obligations": persistence_audit_obligations,
        "method_guidance": method_guidance,
        "public_surface": public_surface_obligations,
        "behavior_obligations": behavior_obligations_by_operation,
        "evidence_obligations": {
            "source_references": source_references,
            "contract_test_targets": contract_test_targets,
            "unit_test_targets": [module_file_paths(selected_module)["unit-test"]],
            "ownership_scope": [module_file_paths(selected_module)[role] for role in REQUIRED_ROLES],
            "local_evidence_gate_required": True,
        },
        "method_obligations": method_guidance,
        "claim_ceiling": "authoring context sufficiency packet only; generated files still require local evidence gate and human quality review",
    }


def _string_list(value: object) -> list[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = str(item.get("title") or item.get("name") or item.get("id") or "").strip()
            else:
                text = str(item).strip()
            if text:
                items.append(text)
        return items
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False, sort_keys=True)]
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def _operation_semantics_dict(behavior_obligations: dict[str, Any]) -> dict[str, Any]:
    semantics = behavior_obligations.get("operation_semantics")
    return semantics if isinstance(semantics, dict) else {}


def build_module_behavior_plan(*, authoring_context: dict[str, Any]) -> dict[str, Any]:
    operations: dict[str, Any] = {}
    for operation_context in authoring_context.get("operations", []):
        if not isinstance(operation_context, dict):
            continue
        operation_id = str(operation_context.get("operation_id", "")).strip()
        if not operation_id:
            continue
        behavior_obligations = (
            operation_context.get("behavior_obligations", {})
            if isinstance(operation_context.get("behavior_obligations"), dict)
            else {}
        )
        semantics = _operation_semantics_dict(behavior_obligations)
        request_required_fields = _string_list(operation_context.get("request_required_fields"))
        failure_codes = {
            str(case.get("error_code", "")).strip()
            for case in operation_context.get("failure_cases", [])
            if isinstance(case, dict) and str(case.get("error_code", "")).strip()
        }
        failure_codes.update(_string_list(behavior_obligations.get("error_codes")))
        service_flow_obligations = _string_list(behavior_obligations.get("steps"))
        state_transition_obligations = _string_list(behavior_obligations.get("state_transition"))
        state_transition_obligations.extend(_string_list(semantics.get("state_set")))
        invariant_obligations = _string_list(behavior_obligations.get("invariants"))
        invariant_obligations.extend(_string_list(semantics.get("mutation_guard")))
        owner_service = str(semantics.get("owner_service", "")).strip()
        if owner_service:
            invariant_obligations.append(owner_service)
        persistence_obligations = _string_list(behavior_obligations.get("persistence_effects"))
        transaction_obligations = _string_list(behavior_obligations.get("transaction_rule"))
        audit_event_obligations = _string_list(behavior_obligations.get("audit_effect"))
        audit_event_obligations.extend(_string_list(semantics.get("trigger_events")))
        evidence_keys = _string_list(semantics.get("evidence_keys"))
        operations[operation_id] = {
            "operation_id": operation_id,
            "service_flow_obligations": service_flow_obligations,
            "contract_validation_obligations": request_required_fields,
            "failure_mapping_obligations": sorted(failure_codes),
            "state_transition_obligations": state_transition_obligations,
            "invariant_obligations": invariant_obligations,
            "persistence_obligations": persistence_obligations,
            "transaction_obligations": transaction_obligations,
            "audit_event_obligations": audit_event_obligations,
            "evidence_obligations": evidence_keys,
            "repository_obligations": {
                "decision_load": bool(service_flow_obligations or evidence_keys or persistence_obligations),
                "invariant_persist": bool(persistence_obligations or invariant_obligations or transaction_obligations),
                "audit_effect": bool(audit_event_obligations),
                "read_back_or_runtime_bridge": bool(evidence_keys or persistence_obligations),
            },
        }
    return {
        "artifact_kind": BEHAVIOR_PLAN_KIND,
        "selected_module": str(authoring_context.get("selected_module", "")).strip(),
        "operations": operations,
        "claim_ceiling": "behavior plan for selected-module synthesis audit; not generated quality proof",
    }


def _safe_relative_path(value: object) -> str:
    rel = str(value or "").strip().replace("\\", "/")
    if not rel:
        raise ValueError("bundle file path is required")
    parsed = PurePosixPath(rel)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError(f"bundle file path escapes expected root: {rel}")
    return rel


def _non_comment_lines(content: str) -> list[str]:
    lines: list[str] = []
    in_block = False
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if in_block:
            if "*/" in line:
                in_block = False
            continue
        if line.startswith("/*"):
            if "*/" not in line:
                in_block = True
            continue
        if line.startswith("//") or line.startswith("*") or line == "*/":
            continue
        lines.append(line)
    return lines


def _reject_thin_content(content: str, *, role: str, path: str) -> None:
    non_comment = _non_comment_lines(content)
    if not non_comment:
        raise ValueError(f"{role} file is comment-only: {path}")
    lowered = "\n".join(non_comment).lower()
    placeholder_tokens = ("todo", "placeholder", "lorem ipsum", "not implemented", "stub only")
    if any(token in lowered for token in placeholder_tokens):
        raise ValueError(f"{role} file contains placeholder content: {path}")


def _signal_present(content: str, tokens: tuple[str, ...]) -> bool:
    lowered = content.lower()
    return any(token.lower() in lowered for token in tokens)


def _behavior_signal_present(content: str, tokens: tuple[str, ...]) -> bool:
    lowered = content.lower()
    for token in tokens:
        normalized = token.lower()
        if not normalized:
            continue
        if re.fullmatch(r"[a-z0-9_]+", normalized):
            if re.search(rf"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])", lowered):
                return True
            continue
        if normalized in lowered:
            return True
    return False


def _behavior_plan_has_obligations(module_behavior_plan: dict[str, Any]) -> bool:
    operations = module_behavior_plan.get("operations", {})
    if not isinstance(operations, dict):
        return False
    obligation_keys = (
        "service_flow_obligations",
        "contract_validation_obligations",
        "failure_mapping_obligations",
        "state_transition_obligations",
        "invariant_obligations",
        "persistence_obligations",
        "transaction_obligations",
        "audit_event_obligations",
        "evidence_obligations",
    )
    for operation in operations.values():
        if not isinstance(operation, dict):
            continue
        if any(operation.get(key) not in (None, "", [], {}) for key in obligation_keys):
            return True
        repository = operation.get("repository_obligations", {})
        if isinstance(repository, dict) and any(bool(value) for value in repository.values()):
            return True
    return False


def _behavior_depth_signals(
    *,
    service_content: str,
    repository_content: str,
    module_behavior_plan: dict[str, Any],
) -> dict[str, bool]:
    if not _behavior_plan_has_obligations(module_behavior_plan):
        return {}
    service_tokens = service_content.lower()
    repository_tokens = repository_content.lower()
    signals = {
        "service_behavior_flow": _behavior_signal_present(
            service_tokens,
            ("behavior-card-step", "operation-semantic", "load", "persist", "map", "validate"),
        ),
        "service_contract_validation": _behavior_signal_present(
            service_tokens,
            ("invalid_request", "missing_", "required", "tenant", "validate"),
        ),
        "service_state_conflict_policy": _behavior_signal_present(
            service_tokens,
            ("version_conflict", "expectedversion", "state", "transition", "status"),
        ),
        "service_invariant_guard": _behavior_signal_present(
            service_tokens,
            ("operation-semantic-guard", "mutation_guard", "owner", "invariant", "guard"),
        ),
        "service_audit_event": _behavior_signal_present(
            service_tokens,
            ("audit", "event", "append", "trigger"),
        ),
        "repository_decision_load": _behavior_signal_present(
            repository_tokens,
            ("fordecision", "load", "decision"),
        ),
        "repository_invariant_persistence": _behavior_signal_present(
            repository_tokens,
            ("withinvariants", "transaction", "persistence", "persist", "write"),
        ),
        "repository_audit_effect": _behavior_signal_present(
            repository_tokens,
            ("audit", "event", "append"),
        ),
        "repository_readback_or_runtime_bridge": _behavior_signal_present(
            repository_tokens,
            ("readback", "read-back", "execution_plan", "runtime bridge", "operationplan"),
        ),
    }
    return signals


def _method_name_for_operation(operation_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", operation_id).strip()
    if not normalized:
        return ""
    words = normalized.split()
    first = words[0][:1].lower() + words[0][1:]
    return "".join([first, *words[1:]])


def _operation_method_coverage_signals(
    *,
    service_content: str,
    repository_content: str,
    module_behavior_plan: dict[str, Any],
) -> dict[str, bool]:
    operations = module_behavior_plan.get("operations", {})
    if not isinstance(operations, dict):
        return {}
    signals: dict[str, bool] = {}
    for operation_id in sorted(str(item).strip() for item in operations if str(item).strip()):
        method_name = _method_name_for_operation(operation_id)
        if not method_name:
            continue
        service_pattern = re.compile(rf"\b(?:async\s+)?{re.escape(method_name)}\s*\(", flags=re.IGNORECASE)
        repository_pattern = re.compile(
            rf"\b(?:async\s+)?(?:{re.escape(method_name)}|load{re.escape(operation_id)}ForDecision|persist{re.escape(operation_id)}WithInvariants|readBack{re.escape(operation_id)})\s*\(",
            flags=re.IGNORECASE,
        )
        signals[f"service_method_{operation_id}"] = bool(service_pattern.search(service_content))
        signals[f"repository_method_{operation_id}"] = bool(repository_pattern.search(repository_content))
    return signals


def _expected_runtime_bridge_helper(operation_id: str) -> str:
    if operation_id.startswith(("Create", "Launch", "Export")):
        return "executeCreateOperation"
    if operation_id.startswith("Get"):
        return "executeDetailReadOperation"
    if operation_id.startswith(("List", "Search")):
        return "executeListReadOperation"
    if operation_id.startswith(
        (
            "Update",
            "Patch",
            "Delete",
            "Remove",
            "Archive",
            "Restore",
            "Approve",
            "Reject",
            "Submit",
            "Start",
            "Stop",
            "Cancel",
            "Close",
            "Reopen",
            "Manage",
            "Record",
        )
    ):
        return "executeCommandOperation"
    return ""


def _repository_runtime_bridge_kind_signals(
    *,
    repository_content: str,
    module_behavior_plan: dict[str, Any],
) -> dict[str, bool]:
    operations = module_behavior_plan.get("operations", {})
    if not isinstance(operations, dict):
        return {}
    signals: dict[str, bool] = {}
    for operation_id in sorted(str(item).strip() for item in operations if str(item).strip()):
        expected_helper = _expected_runtime_bridge_helper(operation_id)
        if not expected_helper:
            continue
        spec_pattern = re.compile(
            rf"getOperationSpec\s*\(\s*['\"]{re.escape(operation_id)}['\"]\s*\)",
            flags=re.IGNORECASE,
        )
        if not spec_pattern.search(repository_content):
            continue
        signal_name = f"repository_runtime_bridge_{operation_id}"
        signals[signal_name] = False
        for match in spec_pattern.finditer(repository_content):
            window = repository_content[max(0, match.start() - 500) : match.end() + 1200]
            if re.search(rf"\b{re.escape(expected_helper)}\s*\(", window):
                signals[signal_name] = True
                break
    return signals


def _compact_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _snake_to_camel(value: str) -> str:
    parts = [part for part in re.split(r"[_\-\s]+", value.strip()) if part]
    if not parts:
        return ""
    return parts[0][:1].lower() + parts[0][1:] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _value_aliases(value: str) -> set[str]:
    raw = str(value or "").strip()
    if not raw:
        return set()
    aliases = {raw, raw.lower(), raw.replace("-", "_"), raw.replace("_", "-"), raw.replace("_", " ")}
    camel = _snake_to_camel(raw)
    if camel:
        aliases.add(camel)
    compact = _compact_token(raw)
    if compact:
        aliases.add(compact)
    return {alias for alias in aliases if alias}


def _content_has_exactish_value(content: str, value: str) -> bool:
    value = str(value or "").strip()
    if not value or value.lower() in {"none", "n/a", "na", "null"}:
        return False
    lowered = content.lower()
    compact_content = _compact_token(content)
    for alias in _value_aliases(value):
        alias_lower = alias.lower()
        if re.fullmatch(r"[a-z0-9_]+", alias_lower):
            if re.search(rf"(?<![a-z0-9_]){re.escape(alias_lower)}(?![a-z0-9_])", lowered):
                return True
        elif alias_lower in lowered:
            return True
        compact_alias = _compact_token(alias)
        if compact_alias and compact_alias in compact_content:
            return True
    return False


def _operation_windows(content: str, operation_id: str) -> list[str]:
    operation_id = str(operation_id or "").strip()
    method_name = _method_name_for_operation(operation_id)
    markers = [marker for marker in (operation_id, method_name) if marker]
    windows: list[str] = []
    for marker in markers:
        for match in re.finditer(re.escape(marker), content, flags=re.IGNORECASE):
            windows.append(content[max(0, match.start() - 600) : min(len(content), match.end() + 1800)])
    return windows or [content]


def _operation_content_has_value(content: str, operation_id: str, value: str) -> bool:
    return any(_content_has_exactish_value(window, value) for window in _operation_windows(content, operation_id))


def _field_access_patterns(field: str) -> list[str]:
    aliases = sorted(_value_aliases(field), key=len, reverse=True)
    patterns: list[str] = []
    for alias in aliases:
        if not alias:
            continue
        escaped = re.escape(alias)
        patterns.extend(
            [
                rf"\b(?:payload|context|record|body|input|params|path_params|query)\s*\.\s*{escaped}\b",
                rf"\b(?:payload|context|record|body|input|params|path_params|query)\s*\[\s*['\"]{escaped}['\"]\s*\]",
            ]
        )
    return patterns


def _service_operation_has_executable_required_context_guard(service_content: str, operation_id: str, field: str) -> bool:
    for window in _operation_windows(service_content, operation_id):
        if not _content_has_exactish_value(window, field):
            continue
        for pattern in _field_access_patterns(field):
            guard_patterns = [
                rf"\bif\s*\([^;\n]{{0,240}}!\s*{pattern}",
                rf"\bif\s*\([^;\n]{{0,240}}{pattern}\s*(?:===|==)\s*(?:undefined|null|\"\"|'')",
                rf"\bif\s*\([^;\n]{{0,240}}(?:typeof\s+)?{pattern}[^;\n]{{0,160}}\)",
                rf"{pattern}\s*!==\s*decision\.expectedVersion",
                rf"{pattern}\s*!==\s*current\.expectedVersion",
                rf"{pattern}\s*!==\s*decision\.expected_version",
                rf"{pattern}\s*!==\s*current\.expected_version",
            ]
            if any(re.search(guard_pattern, window, flags=re.IGNORECASE) for guard_pattern in guard_patterns):
                return True
        if "review-bound" in window.lower() and _content_has_exactish_value(window, field):
            return True
    return False


def _signal_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_")
    return token or "value"


def _finding(
    *,
    operation_id: str,
    obligation_class: str,
    source_obligation: str,
    expected_surface: str,
    observed: object,
    message: str,
    severity: str = "blocking",
) -> dict[str, Any]:
    return {
        "operation_id": operation_id,
        "obligation_class": obligation_class,
        "source_obligation": source_obligation,
        "expected_surface": expected_surface,
        "observed": observed,
        "severity": severity,
        "message": message,
    }


def _owner_service_obligations(operation: dict[str, Any]) -> list[str]:
    owners: set[str] = set()
    values: list[str] = []
    for key in ("invariant_obligations", "service_flow_obligations", "state_transition_obligations"):
        values.extend(_string_list(operation.get(key)))
    for value in values:
        owners.update(re.findall(r"\b[A-Z][A-Za-z0-9]*Service\b", value))
    return sorted(owners)


def _observed_service_tokens(content: str) -> list[str]:
    return sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9]*Service\b", content)))


def _audit_event_obligations(operation: dict[str, Any]) -> list[str]:
    events: set[str] = set()
    for value in _string_list(operation.get("audit_event_obligations")):
        for token in re.findall(
            r"\b[A-Z][A-Za-z0-9]*(?:Activated|Created|Updated|Deleted|Archived|Submitted|Approved|Rejected|Completed|Failed|Event)\b",
            value,
        ):
            if token.lower() not in {"event", "auditevent"}:
                events.add(token)
        stripped = value.strip()
        if re.fullmatch(r"[A-Z][A-Za-z0-9]*(?:Activated|Created|Updated|Deleted|Archived|Submitted|Approved|Rejected|Completed|Failed|Event)", stripped):
            events.add(stripped)
    return sorted(events)


def _operation_declares_read_only(operation_id: str, operation: dict[str, Any]) -> bool:
    values: list[str] = []
    for key in (
        "service_flow_obligations",
        "state_transition_obligations",
        "invariant_obligations",
        "persistence_obligations",
        "audit_event_obligations",
    ):
        values.extend(_string_list(operation.get(key)))
    text = " ".join(values).lower()
    read_only_tokens = (
        "read-only",
        "read only",
        "do not mutate",
        "no mutation",
        "no-mutation",
        "without durable mutation",
        "without durable write",
        "states none",
        "none via none",
    )
    if any(token in text for token in read_only_tokens):
        return True
    return operation_id.startswith(("List", "Get", "Search")) and not _string_list(operation.get("persistence_obligations"))


def _repository_has_mutating_method_for_operation(repository_content: str, operation_id: str) -> bool:
    mutation_method_names = [
        f"persist{operation_id}WithInvariants",
        f"write{operation_id}",
        f"insert{operation_id}",
        f"update{operation_id}",
        f"delete{operation_id}",
        f"upsert{operation_id}",
    ]
    for method_name in mutation_method_names:
        if re.search(rf"\b(?:async\s+)?{re.escape(method_name)}\s*\(", repository_content, flags=re.IGNORECASE):
            return True
    return False


def _repository_has_no_mutation_reason(repository_content: str, operation_id: str) -> bool:
    for window in _operation_windows(repository_content, operation_id):
        lowered = window.lower()
        if any(
            token in lowered
            for token in (
                "read-only",
                "read only",
                "no mutation",
                "no-mutation",
                "does not mutate",
                "do not mutate",
                "without durable mutation",
                "without durable write",
                "no durable write",
            )
        ):
            return True
    return False


def _repository_has_read_only_write_path(repository_content: str, operation_id: str) -> bool:
    mutating_method_names = [
        f"persist{operation_id}WithInvariants",
        f"write{operation_id}",
        f"insert{operation_id}",
        f"update{operation_id}",
        f"delete{operation_id}",
        f"upsert{operation_id}",
    ]
    for method_name in mutating_method_names:
        match = re.search(rf"\b(?:async\s+)?{re.escape(method_name)}\s*\(", repository_content, flags=re.IGNORECASE)
        if not match:
            continue
        window = repository_content[match.start() : min(len(repository_content), match.start() + 1200)].lower()
        if method_name.lower().startswith("persist"):
            return True
        if any(token in window for token in ("transaction(", "write", "insert", "update", "delete", "upsert", "persisted", "invariant_persistence")):
            return True
    return False


def audit_module_obligation_consumption(
    *,
    service_content: str,
    repository_content: str,
    unit_content: str,
    module_behavior_plan: dict[str, Any],
) -> dict[str, Any]:
    operations = module_behavior_plan.get("operations", {})
    if not isinstance(operations, dict):
        operations = {}
    signals: dict[str, bool] = {}
    findings: list[dict[str, Any]] = []

    def record(
        signal_name: str,
        *,
        present: bool,
        operation_id: str,
        obligation_class: str,
        source_obligation: str,
        expected_surface: str,
        observed: object,
        message: str,
    ) -> None:
        signals[signal_name] = present
        if not present:
            findings.append(
                _finding(
                    operation_id=operation_id,
                    obligation_class=obligation_class,
                    source_obligation=source_obligation,
                    expected_surface=expected_surface,
                    observed=observed,
                    message=message,
                )
            )

    for operation_id, raw_operation in sorted(operations.items()):
        operation_id = str(operation_id).strip()
        if not operation_id or not isinstance(raw_operation, dict):
            continue
        operation = raw_operation

        for owner in _owner_service_obligations(operation):
            signal_name = f"service_obligation_{_signal_token(operation_id)}_semantic_owner"
            record(
                signal_name,
                present=_operation_content_has_value(service_content, operation_id, owner),
                operation_id=operation_id,
                obligation_class="semantic_owner",
                source_obligation=owner,
                expected_surface="service",
                observed=_observed_service_tokens(service_content),
                message="Generated service must consume the exact source-backed semantic owner instead of substituting a generic profile owner.",
            )

        for field in _string_list(operation.get("contract_validation_obligations")):
            signal_name = f"service_obligation_{_signal_token(operation_id)}_required_context_{_signal_token(field)}"
            has_executable_guard = _service_operation_has_executable_required_context_guard(service_content, operation_id, field)
            record(
                signal_name,
                present=has_executable_guard,
                operation_id=operation_id,
                obligation_class="required_context",
                source_obligation=field,
                expected_surface="service",
                observed="executable guard present"
                if has_executable_guard
                else (
                    "non-executable field-name marker only"
                    if _operation_content_has_value(service_content, operation_id, field)
                    else "missing from selected service operation body"
                ),
                message="Generated service must consume each source-backed required context field through executable validation, propagation, or explicit review-bound handling; a field-name list is not enough.",
            )

        for event in _audit_event_obligations(operation):
            service_signal = f"service_obligation_{_signal_token(operation_id)}_audit_event_{_signal_token(event)}"
            record(
                service_signal,
                present=_operation_content_has_value(service_content, operation_id, event),
                operation_id=operation_id,
                obligation_class="audit_event",
                source_obligation=event,
                expected_surface="service",
                observed="present" if _operation_content_has_value(service_content, operation_id, event) else "missing exact declared event from selected service operation body",
                message="Generated service must consume the exact declared audit event; generic audit/event wording is not sufficient.",
            )
            repository_signal = f"repository_obligation_{_signal_token(operation_id)}_audit_event_{_signal_token(event)}"
            record(
                repository_signal,
                present=_operation_content_has_value(repository_content, operation_id, event),
                operation_id=operation_id,
                obligation_class="audit_event",
                source_obligation=event,
                expected_surface="repository",
                observed="present" if _operation_content_has_value(repository_content, operation_id, event) else "missing exact declared event from selected repository operation body",
                message="Generated repository must persist or expose the exact declared audit event when the behavior plan names one.",
            )

        repository_obligations = operation.get("repository_obligations", {})
        repository_obligations = repository_obligations if isinstance(repository_obligations, dict) else {}
        read_only = _operation_declares_read_only(operation_id, operation)
        if read_only:
            mutates = _repository_has_mutating_method_for_operation(repository_content, operation_id)
            has_reason = _repository_has_no_mutation_reason(repository_content, operation_id)
            has_write_path = _repository_has_read_only_write_path(repository_content, operation_id)
            signal_name = f"repository_obligation_{_signal_token(operation_id)}_read_only_no_mutation"
            record(
                signal_name,
                present=(not mutates) and not has_write_path,
                operation_id=operation_id,
                obligation_class="read_only_no_mutation",
                source_obligation="; ".join(
                    _string_list(operation.get("invariant_obligations"))
                    or _string_list(operation.get("state_transition_obligations"))
                    or ["read-only/no-mutation operation"]
                ),
                expected_surface="repository",
                observed="read-only method still exposes a write/persist path"
                if has_write_path
                else "mutating repository path with only a no-mutation explanation"
                if mutates and has_reason
                else "mutating repository path without no-mutation explanation"
                if mutates
                else "read-only honored",
                message="Read-only operations must not be turned into invariant persistence or write paths; a no-mutation comment cannot override executable mutation behavior.",
            )
        else:
            if repository_obligations.get("decision_load"):
                signal_name = f"repository_obligation_{_signal_token(operation_id)}_decision_load"
                record(
                    signal_name,
                    present=bool(
                        re.search(
                            rf"\b(?:async\s+)?load{re.escape(operation_id)}ForDecision\s*\(",
                            repository_content,
                            flags=re.IGNORECASE,
                        )
                    ),
                    operation_id=operation_id,
                    obligation_class="decision_load",
                    source_obligation="repository decision-load obligation",
                    expected_surface="repository",
                    observed="repository decision-load method present"
                    if re.search(
                        rf"\b(?:async\s+)?load{re.escape(operation_id)}ForDecision\s*\(",
                        repository_content,
                        flags=re.IGNORECASE,
                    )
                    else "missing load{operation}ForDecision",
                    message="Repository must expose operation-specific decision-load evidence when the behavior plan requires it.",
                )
            if repository_obligations.get("invariant_persist"):
                signal_name = f"repository_obligation_{_signal_token(operation_id)}_invariant_persist"
                record(
                    signal_name,
                    present=bool(
                        re.search(
                            rf"\b(?:async\s+)?persist{re.escape(operation_id)}WithInvariants\s*\(",
                            repository_content,
                            flags=re.IGNORECASE,
                        )
                    ),
                    operation_id=operation_id,
                    obligation_class="invariant_persist",
                    source_obligation="; ".join(
                        _string_list(operation.get("persistence_obligations"))
                        + _string_list(operation.get("transaction_obligations"))
                        + _string_list(operation.get("invariant_obligations"))
                    ),
                    expected_surface="repository",
                    observed="repository invariant-persist method present"
                    if re.search(
                        rf"\b(?:async\s+)?persist{re.escape(operation_id)}WithInvariants\s*\(",
                        repository_content,
                        flags=re.IGNORECASE,
                    )
                    else "missing persist{operation}WithInvariants",
                    message="Repository must consume persistence, transaction, or invariant obligations through an operation-specific invariant persistence surface.",
                )
            if repository_obligations.get("audit_effect") and not _audit_event_obligations(operation):
                signal_name = f"repository_obligation_{_signal_token(operation_id)}_audit_effect"
                record(
                    signal_name,
                    present=bool(
                        re.search(
                            rf"\b(?:async\s+)?append{re.escape(operation_id)}AuditEffect\s*\(",
                            repository_content,
                            flags=re.IGNORECASE,
                        )
                    ),
                    operation_id=operation_id,
                    obligation_class="audit_effect",
                    source_obligation="repository audit-effect obligation",
                    expected_surface="repository",
                    observed="repository audit-effect method present"
                    if re.search(
                        rf"\b(?:async\s+)?append{re.escape(operation_id)}AuditEffect\s*\(",
                        repository_content,
                        flags=re.IGNORECASE,
                    )
                    else "missing append{operation}AuditEffect",
                    message="Repository must expose operation-specific audit-effect handling when the behavior plan requires it.",
                )
            if repository_obligations.get("read_back_or_runtime_bridge"):
                signal_name = f"repository_obligation_{_signal_token(operation_id)}_read_back_or_runtime_bridge"
                expected_helper = _expected_runtime_bridge_helper(operation_id)
                present = bool(
                    re.search(
                        rf"\b(?:async\s+)?readBack{re.escape(operation_id)}\s*\(",
                        repository_content,
                        flags=re.IGNORECASE,
                    )
                ) or bool(expected_helper and re.search(rf"\b{re.escape(expected_helper)}\s*\(", repository_content))
                record(
                    signal_name,
                    present=present,
                    operation_id=operation_id,
                    obligation_class="read_back_or_runtime_bridge",
                    source_obligation="repository read-back/runtime-bridge obligation",
                    expected_surface="repository",
                    observed="repository read-back/runtime bridge present" if present else "missing readBack{operation} or expected runtime bridge",
                    message="Repository must consume runtime evidence obligations through read-back or the expected operation runtime bridge.",
                )

    missing_signals = [signal for signal, present in signals.items() if not present]
    return {
        "artifact_kind": OBLIGATION_CONSUMPTION_AUDIT_KIND,
        "overall_consumption_gate": "pass" if not missing_signals else "fail",
        "signals": signals,
        "missing_signals": missing_signals,
        "findings": findings,
        "claim_ceiling": "exact obligation-consumption audit only; it does not prove business correctness without local evidence gate and human Review",
    }


def _tvg_loop_failures(loop: object) -> list[str]:
    if not isinstance(loop, dict):
        return ["tvg_quality_loop is required"]
    failures: list[str] = []
    axes = loop.get("value_gain_axes")
    axis_values = {str(axis).strip() for axis in axes} if isinstance(axes, list) else set()
    missing_axes = [axis for axis in REQUIRED_TVG_AXES if axis not in axis_values]
    if missing_axes:
        failures.append(f"tvg_quality_loop missing value_gain_axes: {', '.join(missing_axes)}")
    rounds = loop.get("rounds")
    if not isinstance(rounds, list) or not any(isinstance(item, dict) and str(item.get("value_gain", "")).strip() for item in rounds):
        failures.append("tvg_quality_loop must include at least one value-gain round")
    if not str(loop.get("exit_gate", "")).strip():
        failures.append("tvg_quality_loop exit_gate is required")
    if not str(loop.get("agentic_exit_audit", "")).strip():
        failures.append("tvg_quality_loop agentic_exit_audit is required")
    if str(loop.get("exit_state", "")).strip() != "agentic-exit-ready":
        failures.append("tvg_quality_loop exit_state must be agentic-exit-ready")
    return failures


def audit_module_synthesis_quality(*, bundle: dict[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest", {}) if isinstance(bundle.get("manifest"), dict) else {}
    files_by_role = bundle.get("files_by_role", {}) if isinstance(bundle.get("files_by_role"), dict) else {}
    unit_file = files_by_role.get("unit-test", {}) if isinstance(files_by_role.get("unit-test"), dict) else {}
    service_file = files_by_role.get("service", {}) if isinstance(files_by_role.get("service"), dict) else {}
    repository_file = files_by_role.get("repository", {}) if isinstance(files_by_role.get("repository"), dict) else {}
    unit_content = str(unit_file.get("content", ""))
    service_content = str(service_file.get("content", ""))
    repository_content = str(repository_file.get("content", ""))
    module_behavior_plan = (
        bundle.get("module_behavior_plan", {})
        if isinstance(bundle.get("module_behavior_plan"), dict)
        else {}
    )
    signals = {
        "tvg_exit_audit": not _tvg_loop_failures(manifest.get("tvg_quality_loop")),
        "isolated_unit_marker": _signal_present(unit_content, ("@phase3-test-family isolated-unit", "isolated-unit")),
        "repository_double": _signal_present(
            unit_content,
            ("@phase3-collaborator-proof repository-double", "repository-double", "vi.fn(", "spyon("),
        ),
        "repository_call_assertion": _signal_present(
            unit_content,
            ("tohavebeencalled", "tohavebeencalledwith", ".mock.calls", "expect(repository"),
        ),
        "negative_branch": _signal_present(
            unit_content,
            ("invalid_query", "missing_", "forbidden", "version_conflict", "not_found", "rejects"),
        ),
        "repository_not_called_assertion": _signal_present(
            unit_content,
            ("not.tohavebeencalled", "tohavenotbeencalled", "tohavebeencalledtimes(0"),
        ),
        "repository_error_translation": _signal_present(
            unit_content,
            ("dependency_unavailable", "not_found", "version_conflict", "captureapierror", "error_code", "status"),
        ),
    }
    signals.update(
        _behavior_depth_signals(
            service_content=service_content,
            repository_content=repository_content,
            module_behavior_plan=module_behavior_plan,
        )
    )
    signals.update(
        _operation_method_coverage_signals(
            service_content=service_content,
            repository_content=repository_content,
            module_behavior_plan=module_behavior_plan,
        )
    )
    signals.update(
        _repository_runtime_bridge_kind_signals(
            repository_content=repository_content,
            module_behavior_plan=module_behavior_plan,
        )
    )
    obligation_consumption_audit = audit_module_obligation_consumption(
        service_content=service_content,
        repository_content=repository_content,
        unit_content=unit_content,
        module_behavior_plan=module_behavior_plan,
    )
    consumption_signals = obligation_consumption_audit.get("signals", {})
    if isinstance(consumption_signals, dict):
        signals.update({str(signal): bool(present) for signal, present in consumption_signals.items()})
    missing_signals = [signal for signal, present in signals.items() if not present]
    failures = _tvg_loop_failures(manifest.get("tvg_quality_loop"))
    unit_signal_names = [
        "isolated_unit_marker",
        "repository_double",
        "repository_call_assertion",
        "negative_branch",
        "repository_not_called_assertion",
        "repository_error_translation",
    ]
    missing_unit_signals = [signal for signal in unit_signal_names if signal in missing_signals]
    if missing_unit_signals:
        failures.append(f"unit-test richness missing signals: {', '.join(missing_unit_signals)}")
    behavior_signal_names = [
        "service_behavior_flow",
        "service_contract_validation",
        "service_state_conflict_policy",
        "service_invariant_guard",
        "service_audit_event",
        "repository_decision_load",
        "repository_invariant_persistence",
        "repository_audit_effect",
        "repository_readback_or_runtime_bridge",
    ]
    missing_behavior_signals = [signal for signal in behavior_signal_names if signal in missing_signals]
    if missing_behavior_signals:
        failures.append(f"service/repository behavior-depth missing signals: {', '.join(missing_behavior_signals)}")
    missing_operation_method_signals = [
        signal
        for signal in missing_signals
        if signal.startswith("service_method_") or signal.startswith("repository_method_")
    ]
    if missing_operation_method_signals:
        failures.append(
            f"selected-module operation-method coverage missing signals: {', '.join(missing_operation_method_signals)}"
        )
    missing_runtime_bridge_signals = [
        signal
        for signal in missing_signals
        if signal.startswith("repository_runtime_bridge_")
    ]
    if missing_runtime_bridge_signals:
        failures.append(
            f"selected-module runtime bridge kind missing signals: {', '.join(missing_runtime_bridge_signals)}"
        )
    missing_consumption_signals = [
        signal
        for signal in missing_signals
        if signal.startswith("service_obligation_") or signal.startswith("repository_obligation_")
    ]
    if missing_consumption_signals:
        failures.append(
            f"selected-module obligation-consumption missing signals: {', '.join(missing_consumption_signals)}"
        )
    return {
        "artifact_kind": QUALITY_AUDIT_KIND,
        "selected_module": str(bundle.get("selected_module", "")).strip(),
        "overall_quality_gate": "pass" if not failures else "fail",
        "required_tvg_axes": list(REQUIRED_TVG_AXES),
        "signals": signals,
        "missing_signals": missing_signals,
        "failures": failures,
        "warnings": [],
        "obligation_consumption_audit": obligation_consumption_audit,
        "module_behavior_plan_artifact_kind": str(module_behavior_plan.get("artifact_kind", "")).strip(),
        "claim_ceiling": "TVG audit shape, unit-test richness, and selected service/repository behavior-depth signals only; human Review still decides generated artifact quality",
    }


def build_module_rewrite_packet(*, bundle: dict[str, Any], quality_audit: dict[str, Any]) -> dict[str, Any]:
    selected_module = str(bundle.get("selected_module", "")).strip()
    missing_signals = [str(item) for item in quality_audit.get("missing_signals", []) if str(item).strip()]
    failures = [str(item) for item in quality_audit.get("failures", []) if str(item).strip()]
    instructions = [
        "Regenerate the selected service/repository/unit-test bundle through a bounded Agentic rewrite; do not hand-edit generated output roots.",
        "Preserve the same selected module ownership scope and authoring_context_sha256 unless source or contract inputs changed.",
    ]
    if "tvg_exit_audit" in missing_signals or any("tvg_quality_loop" in failure for failure in failures):
        instructions.append("Add a complete tvg_quality_loop with behavior-depth, evidence-depth, failure-depth, value-gain rounds, exit gate, and agentic exit audit.")
    if any(signal in missing_signals for signal in ("repository_double", "repository_call_assertion")):
        instructions.append("Strengthen unit-test richness with a repository double and explicit repository call assertions.")
    if any(signal in missing_signals for signal in ("negative_branch", "repository_not_called_assertion")):
        instructions.append("Strengthen unit-test richness with at least one negative branch that proves invalid input does not call the repository.")
    if "repository_error_translation" in missing_signals:
        instructions.append("Strengthen unit-test richness with repository failure mapping or declared error-envelope translation evidence.")
    behavior_signals = {
        "service_behavior_flow",
        "service_contract_validation",
        "service_state_conflict_policy",
        "service_invariant_guard",
        "service_audit_event",
        "repository_decision_load",
        "repository_invariant_persistence",
        "repository_audit_effect",
        "repository_readback_or_runtime_bridge",
    }
    if behavior_signals & set(missing_signals):
        instructions.append(
            "Regenerate service/repository behavior depth from module_behavior_plan: include operation flow, validation, state/conflict policy, invariant guard, audit/event hook, repository decision load, invariant persistence, and read-back/runtime bridge where required."
        )
    if any(signal.startswith("service_method_") or signal.startswith("repository_method_") for signal in missing_signals):
        instructions.append(
            "Regenerate selected service/repository operation-method coverage from module_behavior_plan so every selected operation has the controller-callable service method and matching repository/runtime bridge method."
        )
    if any(signal.startswith("repository_runtime_bridge_") for signal in missing_signals):
        instructions.append(
            "Regenerate selected repository runtime bridges from operation semantics: create-like operations must use create bridges, detail reads must use detail-read bridges, list/search reads must use list-read bridges, and state-changing commands must use command bridges."
        )
    if any(signal.startswith("service_obligation_") or signal.startswith("repository_obligation_") for signal in missing_signals):
        consumption_audit = quality_audit.get("obligation_consumption_audit", {})
        findings = consumption_audit.get("findings", []) if isinstance(consumption_audit, dict) else []
        obligation_items: list[str] = []
        if isinstance(findings, list):
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                operation_id = str(finding.get("operation_id", "")).strip()
                source_obligation = str(finding.get("source_obligation", "")).strip()
                expected_surface = str(finding.get("expected_surface", "")).strip()
                obligation_class = str(finding.get("obligation_class", "")).strip()
                if operation_id and source_obligation and expected_surface and obligation_class:
                    obligation_items.append(
                        f"{operation_id} {expected_surface} {obligation_class} exact source obligation `{source_obligation}`"
                    )
                if len(obligation_items) >= 8:
                    break
        if obligation_items:
            instructions.append(
                "Regenerate selected-module exact obligation consumption from module_behavior_plan: "
                + "; ".join(obligation_items)
                + ". Do not substitute generic OperationProfile values, invented owners, invented audit events, or read/write behavior that the source plan did not authorize."
            )
        else:
            instructions.append(
                "Regenerate selected-module exact obligation consumption from module_behavior_plan; operation-specific source obligations must be consumed in service/repository/unit surfaces before file write."
            )
    return {
        "artifact_kind": REWRITE_PACKET_KIND,
        "selected_module": selected_module,
        "missing_signals": missing_signals,
        "quality_failures": failures,
        "rewrite_instructions": instructions,
        "rewrite_boundary": "bounded Agentic bundle rerun before selected-module file write",
        "forbidden_actions": [
            "do not patch generated proof outputs by hand",
            "do not add GEO/PetClinic-specific branches",
            "do not weaken test-obligation gates",
        ],
        "claim_ceiling": "rewrite packet only; not evidence of generated quality improvement",
    }


def _expected_role_for_path(path: str, selected_module: str) -> str:
    expected = module_file_paths(selected_module)
    for role, expected_path in expected.items():
        if path == expected_path:
            return role
    raise ValueError(f"file path does not match selected module ownership scope: {path}")


def load_module_synthesis_bundle(
    *,
    bundle_root: Path,
    candidate_ledger: dict[str, Any],
    authoring_context: dict[str, Any] | None = None,
    require_quality_gate: bool = False,
) -> dict[str, Any]:
    bundle_root = bundle_root.resolve()
    manifest_path = bundle_root / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"module synthesis bundle manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("module synthesis bundle manifest must be a JSON object")
    if str(manifest.get("artifact_kind", "")).strip() != BUNDLE_KIND:
        raise ValueError("module synthesis bundle has wrong artifact_kind")
    if str(manifest.get("phase", "")).strip() != "phase-3":
        raise ValueError("module synthesis bundle phase must be phase-3")

    selected_module = slugify(str(manifest.get("selected_module", "")).strip())
    eligible_modules = {
        str(candidate.get("module_slug", "")).strip()
        for candidate in candidate_ledger.get("eligible_candidates", [])
        if isinstance(candidate, dict)
    }
    if not selected_module or selected_module not in eligible_modules:
        raise ValueError(f"selected module is not eligible: {selected_module}")

    expected_hash = candidate_ledger_sha256(candidate_ledger)
    manifest_hash = str(manifest.get("candidate_ledger_sha256", "")).strip()
    if manifest_hash and manifest_hash != expected_hash:
        raise ValueError("module synthesis bundle candidate_ledger_sha256 does not match candidate ledger")

    expected_context_hash = ""
    if authoring_context is not None:
        expected_context_hash = module_authoring_context_sha256(authoring_context)
        manifest_context_hash = str(manifest.get("authoring_context_sha256", "")).strip()
        if not manifest_context_hash:
            raise ValueError("module synthesis bundle authoring_context_sha256 is required")
        if manifest_context_hash != expected_context_hash:
            raise ValueError("module synthesis bundle authoring_context_sha256 does not match authoring context")

    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("module synthesis bundle files must be a list")
    files_by_role: dict[str, dict[str, Any]] = {}
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("module synthesis file entry must be an object")
        rel_path = _safe_relative_path(entry.get("path"))
        role = str(entry.get("role", "")).strip()
        expected_role = _expected_role_for_path(rel_path, selected_module)
        if role != expected_role:
            raise ValueError(f"file role does not match path: {rel_path}")
        file_rel = _safe_relative_path(entry.get("file") or str(Path("files") / rel_path))
        source_path = bundle_root / file_rel
        if not source_path.exists():
            raise ValueError(f"module synthesis file is missing: {source_path}")
        content = source_path.read_text(encoding="utf-8")
        _reject_thin_content(content, role=role, path=rel_path)
        declared_sha = str(entry.get("sha256", "")).strip()
        actual_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if declared_sha and declared_sha != actual_sha:
            raise ValueError(f"module synthesis file sha256 mismatch: {rel_path}")
        files_by_role[role] = {
            "path": rel_path,
            "role": role,
            "content": content,
            "sha256": actual_sha,
        }

    missing_roles = [role for role in REQUIRED_ROLES if role not in files_by_role]
    if missing_roles:
        raise ValueError(f"module synthesis bundle missing required file roles: {', '.join(missing_roles)}")

    ownership_scope = [str(item).strip().replace("\\", "/") for item in manifest.get("ownership_scope", [])]
    expected_scope = [module_file_paths(selected_module)[role] for role in REQUIRED_ROLES]
    if sorted(ownership_scope) != sorted(expected_scope):
        raise ValueError("module synthesis ownership_scope does not match selected module file paths")

    bundle = {
        "artifact_kind": BUNDLE_KIND,
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "bundle_root": str(bundle_root),
        "selected_module": selected_module,
        "files_by_role": files_by_role,
        "candidate_ledger_sha256": expected_hash,
        "authoring_context_sha256": expected_context_hash,
    }
    if authoring_context is not None:
        bundle["module_behavior_plan"] = build_module_behavior_plan(authoring_context=authoring_context)
    quality_audit = audit_module_synthesis_quality(bundle=bundle)
    rewrite_packet = (
        build_module_rewrite_packet(bundle=bundle, quality_audit=quality_audit)
        if quality_audit["overall_quality_gate"] != "pass"
        else {}
    )
    bundle["quality_audit"] = quality_audit
    bundle["rewrite_packet"] = rewrite_packet
    if require_quality_gate and quality_audit["overall_quality_gate"] != "pass":
        failures = "; ".join(str(item) for item in quality_audit.get("failures", []) if str(item).strip())
        raise ValueError(f"module synthesis quality gate failed: {failures}")
    return bundle


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_module_synthesis_quality_evidence(
    *,
    output_dir: Path,
    bundle: dict[str, Any],
    quality_audit: dict[str, Any] | None = None,
    rewrite_packet: dict[str, Any] | None = None,
) -> dict[str, str]:
    evidence_root = output_dir / ".phase3-review" / "module-synthesis"
    behavior_plan_path = evidence_root / "module-behavior-plan.json"
    quality_audit_path = evidence_root / "tvg-quality-audit.json"
    obligation_consumption_audit_path = evidence_root / "obligation-consumption-audit.json"
    rewrite_packet_path = evidence_root / "module-rewrite-packet.json"
    behavior_plan = bundle.get("module_behavior_plan", {})
    audit = quality_audit if isinstance(quality_audit, dict) else bundle.get("quality_audit", {})
    if not isinstance(audit, dict) or not audit:
        audit = audit_module_synthesis_quality(bundle=bundle)
    consumption_audit = audit.get("obligation_consumption_audit", {}) if isinstance(audit, dict) else {}
    if not isinstance(consumption_audit, dict) or not consumption_audit:
        consumption_audit = audit_module_obligation_consumption(
            service_content=str(
                (
                    bundle.get("files_by_role", {})
                    if isinstance(bundle.get("files_by_role"), dict)
                    else {}
                )
                .get("service", {})
                .get("content", "")
            ),
            repository_content=str(
                (
                    bundle.get("files_by_role", {})
                    if isinstance(bundle.get("files_by_role"), dict)
                    else {}
                )
                .get("repository", {})
                .get("content", "")
            ),
            unit_content=str(
                (
                    bundle.get("files_by_role", {})
                    if isinstance(bundle.get("files_by_role"), dict)
                    else {}
                )
                .get("unit-test", {})
                .get("content", "")
            ),
            module_behavior_plan=behavior_plan if isinstance(behavior_plan, dict) else {},
        )
    packet = rewrite_packet if isinstance(rewrite_packet, dict) else bundle.get("rewrite_packet", {})
    if not isinstance(packet, dict):
        packet = {}
    if not packet and audit.get("overall_quality_gate") != "pass":
        packet = build_module_rewrite_packet(bundle=bundle, quality_audit=audit)
    behavior_plan_path_value = ""
    if isinstance(behavior_plan, dict) and behavior_plan:
        _write_json(behavior_plan_path, behavior_plan)
        behavior_plan_path_value = str(behavior_plan_path)
    _write_json(quality_audit_path, audit)
    _write_json(obligation_consumption_audit_path, consumption_audit)
    packet_path_value = ""
    if packet:
        _write_json(rewrite_packet_path, packet)
        packet_path_value = str(rewrite_packet_path)
    return {
        "module_behavior_plan_path": behavior_plan_path_value,
        "tvg_quality_audit_path": str(quality_audit_path),
        "obligation_consumption_audit_path": str(obligation_consumption_audit_path),
        "module_rewrite_packet_path": packet_path_value,
    }


def render_human_review_packet_zh(
    *,
    selected_module: str,
    ownership_scope: list[str],
    bundle: dict[str, Any],
    bypass_evidence: dict[str, Any],
    authoring_context_path: str = "",
    authoring_context_sha256: str = "",
) -> str:
    manifest = bundle.get("manifest", {}) if isinstance(bundle.get("manifest"), dict) else {}
    return "\n".join(
        [
            "# P3 Module Synthesis 人工 Review Packet",
            "",
            f"- selected_module: `{selected_module}`",
            f"- selection_rationale: {str(manifest.get('selection_rationale', '')).strip()}",
            f"- claim_ceiling: {str(manifest.get('claim_ceiling', '')).strip()}",
            "",
            "## Agentic-owned files",
            *[f"- `{path}`" for path in ownership_scope],
            "",
            "## Renderer bypass evidence",
            f"- bypassed_renderers: `{', '.join(bypass_evidence.get('bypassed_renderers', []))}`",
            f"- old_control_surface: `{bypass_evidence.get('old_control_surface', '')}`",
            "",
            "## Authoring context",
            f"- authoring_context_path: `{authoring_context_path}`",
            f"- authoring_context_sha256: `{authoring_context_sha256}`",
            "",
            "## 人工 Review 问题",
            "- 上下文是否覆盖 source / contract / behavior / evidence / method obligations，而不是只围绕本次错误补丁？",
            "- 这三个文件是否体现了真实 module-level Agentic 生成，而不是注释、sidecar 或旧 renderer 包装？",
            "- service/repository/test 是否比旧生成物更有业务语义，或至少没有明显变弱？",
            "- unit test 是否验证了行为含义，而不是只验证存在性或响应形状？",
            "- 是否存在 P1/P2 未支持的产品真相发明？",
            "- 是否需要 bounded rewrite，还是应关闭为 direction-only / route-failed？",
            "",
        ]
    )


def write_module_synthesis_evidence(
    *,
    output_dir: Path,
    candidate_ledger: dict[str, Any],
    bundle: dict[str, Any],
    authoring_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_module = str(bundle.get("selected_module", "")).strip()
    ownership_scope = [module_file_paths(selected_module)[role] for role in REQUIRED_ROLES]
    evidence_root = output_dir / ".phase3-review" / "module-synthesis"
    authoring_context_path = evidence_root / "authoring-context.json"
    candidate_ledger_path = evidence_root / "candidate-ledger.json"
    selected_manifest_path = evidence_root / "selected-module-manifest.json"
    bypass_evidence_path = evidence_root / "renderer-bypass-evidence.json"
    human_review_packet_path = evidence_root / "human-review-packet.zh-CN.md"
    quality_paths = write_module_synthesis_quality_evidence(output_dir=output_dir, bundle=bundle)
    bypass_evidence = {
        "artifact_kind": "phase3-module-synthesis-renderer-bypass-evidence.v1",
        "selected_module": selected_module,
        "ownership_scope": ownership_scope,
        "bypassed_renderers": [
            "render_service_module",
            "render_repository_module",
            "render_backend_module_unit_test",
        ],
        "old_control_surface": "selected module service/repository/unit-test body renderers",
        "claim_ceiling": "renderer bypass evidence only; runtime and human review still required",
    }
    authoring_context_hash = module_authoring_context_sha256(authoring_context) if authoring_context is not None else ""
    if authoring_context is not None:
        _write_json(authoring_context_path, authoring_context)
    _write_json(candidate_ledger_path, candidate_ledger)
    _write_json(selected_manifest_path, bundle.get("manifest", {}))
    _write_json(bypass_evidence_path, bypass_evidence)
    human_review_packet_path.write_text(
        render_human_review_packet_zh(
            selected_module=selected_module,
            ownership_scope=ownership_scope,
            bundle=bundle,
            bypass_evidence=bypass_evidence,
            authoring_context_path=str(authoring_context_path) if authoring_context is not None else "",
            authoring_context_sha256=authoring_context_hash,
        ),
        encoding="utf-8",
    )
    return {
        "mode": "enabled",
        "selected_module": selected_module,
        "authoring_context_path": str(authoring_context_path) if authoring_context is not None else "",
        "authoring_context_sha256": authoring_context_hash,
        "candidate_ledger_path": str(candidate_ledger_path),
        "selected_manifest_path": str(selected_manifest_path),
        "module_behavior_plan_path": quality_paths["module_behavior_plan_path"],
        "obligation_consumption_audit_path": quality_paths["obligation_consumption_audit_path"],
        "renderer_bypass_evidence_path": str(bypass_evidence_path),
        "human_review_packet_path": str(human_review_packet_path),
        "tvg_quality_audit_path": quality_paths["tvg_quality_audit_path"],
        "module_rewrite_packet_path": quality_paths["module_rewrite_packet_path"],
        "bypassed_renderers": list(bypass_evidence["bypassed_renderers"]),
    }
