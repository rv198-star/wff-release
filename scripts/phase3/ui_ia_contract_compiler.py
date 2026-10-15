#!/usr/bin/env python3
"""Mechanical P1/P2 -> current UI IA projection for requested P3 frontend work.

The compiler joins already-accepted P1 page/flow truth with P2 interaction/API
bindings. It does not decide product composition. Missing realization-only
frontend detail remains open for P3 Agentic implementation judgment; missing or
review-bound business/API/security authority remains fail-closed downstream.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from common.markdown_table_tools import parse_markdown_table
from common.output_language import resolve_output_locale

_STATUS_RANK = {"ready": 0, "review-bound": 1, "blocked": 2, "stale": 3}


def _read(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required current authority file is missing or unreadable: {path}")
    return path.read_text(encoding="utf-8")


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    if text in {"—", "-", "none", "None", "null", "TBD"}:
        return ""
    if len(text) >= 2 and text[0] == "`" and text[-1] == "`":
        return text[1:-1].strip()
    return text


def _split_csv(value: Any) -> list[str]:
    text = _clean(value)
    return [item.strip().strip("`") for item in text.split(",") if item.strip().strip("`")] if text else []


def _table_after_marker(text: str, marker: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if marker in line), -1)
    if start < 0:
        return []
    table_start = next((index for index in range(start + 1, len(lines)) if lines[index].strip().startswith("|")), -1)
    if table_start < 0:
        return []
    table_lines: list[str] = []
    for line in lines[table_start:]:
        if not line.strip().startswith("|"):
            break
        table_lines.append(line)
    if len(table_lines) < 2:
        return []
    return parse_markdown_table("\n".join(table_lines), header_style="raw", strip_backticks=True)


def _path_from_stage04(stage04_text: str, field: str) -> Path | None:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*`([^`]+)`", stage04_text)
    return Path(match.group(1)).expanduser().resolve() if match else None


def _page_briefs(prototype_spec_text: str) -> dict[str, dict[str, Any]]:
    """Read optional realization hints without turning them into upstream gates."""
    lines = prototype_spec_text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "## 6. Page Briefs"), -1)
    if start < 0:
        return {}
    briefs: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    list_field = ""
    list_fields = {"secondary_support_regions", "render_blocks_in_order", "field_groups", "input_controls"}
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if re.match(r"^\s{2}- page_\d+:\s*$", line):
            current = {}
            list_field = ""
            continue
        if current is None:
            continue
        direct = re.match(r"^\s{4}- ([a-zA-Z0-9_]+):\s*(.*)$", line)
        if direct:
            key, raw = direct.groups()
            raw = _clean(raw)
            if key in list_fields and not raw:
                current[key] = []
                list_field = key
            else:
                current[key] = raw
                list_field = ""
            if key == "page_name" and raw:
                briefs[raw] = current
            continue
        child = re.match(r"^\s{6}-\s+(.*)$", line)
        if child and list_field:
            current.setdefault(list_field, []).append(_clean(child.group(1)))
    return briefs


def _combined_status(*statuses: Any) -> str:
    normalized = [str(value or "").strip().lower() for value in statuses if str(value or "").strip()]
    return max(normalized, key=lambda value: _STATUS_RANK.get(value, 1)) if normalized else "review-bound"


def _combined_reason(*reasons: Any) -> str:
    values: list[str] = []
    for reason in reasons:
        value = _clean(reason)
        if value and value not in values:
            values.append(value)
    return "; ".join(values)


def _machine_mapping_fields(value: Any, *, right_hand: bool = False) -> list[str]:
    fields: list[str] = []
    for raw in _clean(value).split(";"):
        if "->" not in raw:
            continue
        left, right = raw.split("->", 1)
        candidate = right if right_hand else left
        normalized = _clean(candidate).split(".")[-1].replace("[]", "").strip()
        if normalized and normalized not in fields:
            fields.append(normalized)
    return fields


def _explicit_value_sources(value: Any) -> dict[str, str]:
    sources: dict[str, str] = {}
    allowed = {
        "user_input": "user-input",
        "workflow_context": "workflow-context",
        "response_binding": "response-binding",
        "auth_session": "auth-session",
    }
    for raw in _clean(value).split(";"):
        if "=" not in raw:
            continue
        field, source = (_clean(part) for part in raw.split("=", 1))
        normalized = source.lower().replace("-", "_").replace(" ", "_")
        if field and normalized in allowed:
            sources[field] = allowed[normalized]
    return sources


def _input_controls_from_brief(brief: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in brief.get("input_controls", []):
        text = _clean(raw)
        if not text:
            continue
        parts = [_clean(part) for part in text.split("|")]
        field = parts[0].strip("`").strip() if parts else ""
        if not field:
            continue
        item: dict[str, Any] = {"field": field}
        for part in parts[1:]:
            key, sep, value = part.partition(":")
            if not sep:
                continue
            key = _clean(key).lower().replace(" ", "_")
            value = _clean(value).strip("`")
            if key == "control" and value:
                item["control"] = value
            elif key == "required" and value:
                item["required"] = value.lower() in {"yes", "true", "required"}
            elif key == "purpose" and value:
                item["purpose"] = value
        rows.append(item)
    return rows


def _looks_like_internal_identifier_reference(field: str) -> bool:
    raw = str(field or "").strip()
    tokenized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    normalized = re.sub(r"[^a-z0-9]+", "_", tokenized.casefold()).strip("_")
    return bool(normalized and (normalized == "id" or normalized.endswith("_id") or normalized.endswith("_ids")))


def _persona_id(role: str) -> str:
    raw = str(role or "").strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.casefold()).strip("-")
    if normalized:
        return normalized
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"role-{digest}"


def _accepted_terminal_roles(prototype_text: str) -> list[str]:
    match = re.search(r"accepted_terminal_roles\s*:\s*`([^`]+)`", prototype_text)
    if not match:
        return []
    roles = _split_csv(match.group(1))
    return [] if roles == ["review-bound"] else roles


def _load_p2_machine_authority(phase2_root: Path) -> dict[str, Any]:
    path = phase2_root / "p2-agentic-architecture-authority.json"
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if not str(payload.get("status") or "").strip().startswith("accepted-p2-agentic-architecture-authority"):
        return {}
    return payload


def _p2_operation_tables(authority: dict[str, Any]) -> dict[str, list[str]]:
    tables_by_operation: dict[str, list[str]] = {}
    for raw in authority.get("data_and_interaction_decisions", []):
        if not isinstance(raw, dict):
            continue
        operation_id = str(raw.get("operation_id") or "").strip()
        aggregate_id = str(raw.get("aggregate_id") or "").strip()
        table_name = str(raw.get("table_name") or "").strip()
        if not operation_id or not aggregate_id or not table_name:
            continue
        tables_by_operation.setdefault(operation_id, [])
        if table_name not in tables_by_operation[operation_id]:
            tables_by_operation[operation_id].append(table_name)
    return tables_by_operation


def _p2_context_reentry_requirements(authority: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw_disposition in authority.get("commitment_dispositions", []):
        if not isinstance(raw_disposition, dict):
            continue
        commitment_id = str(raw_disposition.get("commitment_id") or "").strip()
        coverage = raw_disposition.get("interaction_context_coverage", [])
        if not isinstance(coverage, list):
            continue
        for raw_context in coverage:
            if not isinstance(raw_context, dict) or raw_context.get("reentry_required") is not True:
                continue
            context_id = str(raw_context.get("context_id") or "").strip()
            role = str(raw_context.get("role") or "").strip()
            reentry_operation_ids = list(
                dict.fromkeys(
                    str(value).strip()
                    for value in raw_context.get("reentry_operation_ids", [])
                    if str(value).strip()
                )
            )
            if not context_id or not role or not reentry_operation_ids or (commitment_id, context_id) in seen:
                continue
            seen.add((commitment_id, context_id))
            rows.append(
                {
                    "commitment_id": commitment_id,
                    "context_id": context_id,
                    "role": role,
                    "reentry_operation_ids": reentry_operation_ids,
                    "reason": str(raw_context.get("reason") or "").strip(),
                }
            )
    return rows


def _p2_operation_catalog(authority: dict[str, Any]) -> list[dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    contract_rank: dict[str, tuple[int, int, int]] = {}
    for raw in authority.get("data_and_interaction_decisions", []):
        if not isinstance(raw, dict):
            continue
        operation_id = str(raw.get("operation_id") or "").strip()
        if not operation_id:
            continue
        row = dict(raw)
        rank = (
            1 if isinstance(row.get("result_fields"), list) and bool(row.get("result_fields")) else 0,
            1 if str(row.get("failure_codes") or "").strip() else 0,
            1 if not str(row.get("table_name") or "").strip() else 0,
        )
        if operation_id not in contracts or rank > contract_rank[operation_id]:
            contracts[operation_id] = row
            contract_rank[operation_id] = rank
    rows: list[dict[str, Any]] = []
    for raw in authority.get("operation_portfolio", []):
        if not isinstance(raw, dict):
            continue
        operation_id = str(raw.get("operation_id") or "").strip()
        method = str(raw.get("method") or "").strip().upper()
        path = str(raw.get("path") or "").strip()
        if not operation_id or not method or not path:
            continue
        terminal = raw.get("terminal_access") if isinstance(raw.get("terminal_access"), dict) else {}
        contract = contracts.get(operation_id, {})
        request_fields = [dict(item) for item in contract.get("request_fields", []) if isinstance(item, dict)]
        result_fields = [dict(item) for item in contract.get("result_fields", []) if isinstance(item, dict)]
        rows.append(
            {
                "operation_id": operation_id,
                "contract_id": str(raw.get("contract_id") or "").strip(),
                "service_id": str(raw.get("service_id") or raw.get("owner") or "").strip(),
                "aggregate_id": str(raw.get("aggregate_id") or "").strip(),
                "method": method,
                "path": path,
                "binding_mode": "read" if method in {"GET", "HEAD"} else "write",
                "statement": str(raw.get("statement") or "").strip(),
                "terminal_roles": [str(role).strip() for role in terminal.get("allowed_roles", []) if str(role).strip()],
                "visible_business_objects": [
                    str(item).strip() for item in terminal.get("visible_business_objects", []) if str(item).strip()
                ],
                "request_fields": request_fields,
                "result_fields": result_fields,
                "failure_codes": str(contract.get("failure_codes") or "").strip(),
                "idempotency_rule": str(contract.get("idempotency_rule") or "").strip(),
                "claim_ceiling": str(raw.get("claim_ceiling") or contract.get("claim_ceiling") or "").strip(),
            }
        )
    return rows


_TERMINAL_ROLE_DISPLAY_ALIASES: dict[str, set[str]] = {
    "child": {"child", "孩子", "儿童"},
    "parent": {"parent", "家长", "父母", "监护人"},
}


def _canonical_page_roles(raw_roles: list[str], terminal_roles: list[str]) -> list[str]:
    if not terminal_roles:
        return list(raw_roles)
    lowered = {str(role).strip().casefold() for role in raw_roles if str(role).strip()}
    result: list[str] = []
    for role in terminal_roles:
        canonical = role.casefold()
        aliases = {value.casefold() for value in _TERMINAL_ROLE_DISPLAY_ALIASES.get(canonical, {canonical})}
        if any(value == canonical or canonical in value or value in aliases for value in lowered):
            result.append(role)
    return result


def _operation_roles_for_page(
    operation_catalog: list[dict[str, Any]],
    operation_ids: list[str],
    accepted_terminal_roles: list[str],
) -> list[str]:
    selected = {str(value).strip() for value in operation_ids if str(value).strip()}
    roles = {
        str(role).strip()
        for row in operation_catalog
        if str(row.get("operation_id") or "").strip() in selected
        for role in row.get("terminal_roles", [])
        if str(role).strip()
    }
    if accepted_terminal_roles:
        return [role for role in accepted_terminal_roles if role in roles]
    return sorted(roles)


def _interaction_binding_mode(p1: dict[str, Any], binding: dict[str, Any]) -> str:
    explicit = _clean(binding.get("binding_mode")).casefold()
    if explicit in {"read", "write", "read_write"}:
        return explicit
    trigger = _clean(p1.get("trigger_kind")).casefold()
    action = _clean(p1.get("action_type")).casefold()
    if trigger == "page_load" or action in {"load", "load_context", "inspect", "read", "view"}:
        return "read"
    return "write"


def _operation_candidates(
    *, operation_catalog: list[dict[str, Any]], page_roles: list[str], binding_mode: str
) -> list[dict[str, Any]]:
    roles = {role.casefold() for role in page_roles}
    candidates: list[dict[str, Any]] = []
    for row in operation_catalog:
        operation_roles = {str(role).strip().casefold() for role in row.get("terminal_roles", []) if str(role).strip()}
        if roles and not roles.intersection(operation_roles):
            continue
        mode = str(row.get("binding_mode") or "").strip().casefold()
        if binding_mode == "read" and mode != "read":
            continue
        if binding_mode in {"write", "read_write"} and mode != "write":
            continue
        candidates.append(row)
    return candidates


def _exact_catalog_operation(
    *, binding: dict[str, Any], operation_catalog: list[dict[str, Any]]
) -> dict[str, Any] | None:
    domain_service = _clean(binding.get("domain_service"))
    operation_hint = domain_service.rsplit(".", 1)[-1] if "." in domain_service else ""
    endpoint = _clean(binding.get("api_endpoint"))
    method = _clean(binding.get("http_method")).upper()
    matches = [
        row
        for row in operation_catalog
        if (operation_hint and str(row.get("operation_id") or "") == operation_hint)
        or (
            endpoint
            and method
            and str(row.get("path") or "") == endpoint
            and str(row.get("method") or "").upper() == method
        )
    ]
    unique = {str(row.get("operation_id") or ""): row for row in matches}
    return next(iter(unique.values())) if len(unique) == 1 else None


def _merge_authority_user_inputs(
    brief_inputs: list[dict[str, Any]], field_source_mapping: list[dict[str, str]]
) -> list[dict[str, Any]]:
    brief_by_field = {
        str(item.get("field") or "").strip(): dict(item)
        for item in brief_inputs
        if str(item.get("field") or "").strip()
    }
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for mapping in field_source_mapping:
        field = str(mapping.get("field") or "").strip()
        source = str(mapping.get("source") or "").strip()
        if not field or source != "user-input" or field in seen:
            continue
        item = dict(brief_by_field.get(field, {}))
        item.update(
            {
                "field": field,
                "required": True,
                "source": "p2-explicit-interaction-binding",
                "purpose": str(item.get("purpose") or "Accepted P2 request field explicitly sourced from user input."),
                "internal_identifier_reference": _looks_like_internal_identifier_reference(field),
            }
        )
        rows.append(item)
        seen.add(field)
    return rows


def compile_ui_ia_contract_only(
    *, phase2_root: Path, output_path: Path, ui_locale: str | None = None,
    p3_read_model_bindings: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Compile current UI IA from explicit P1/P2 authority without product-design inference."""
    phase2_root = phase2_root.resolve()
    stage04_path = phase2_root / "stage-04-design-convergence-and-delivery-prototype.md"
    stage03_path = phase2_root / "stage-03-data-storage-and-interface-design.md"
    stage04_text = _read(stage04_path)
    stage03_text = _read(stage03_path)

    prototype_spec_path = _path_from_stage04(stage04_text, "phase1_prototype_spec")
    interaction_flow_path = _path_from_stage04(stage04_text, "phase1_interaction_flow_contract")
    if prototype_spec_path is None:
        prd_path = _path_from_stage04(stage04_text, "phase1_prd")
        if prd_path is not None:
            prototype_spec_path = prd_path.parent / "prototype-spec.md"
    if interaction_flow_path is None and prototype_spec_path is not None:
        interaction_flow_path = prototype_spec_path.parent / "prototype-interaction-flow-contract.md"
    if prototype_spec_path is None or interaction_flow_path is None:
        raise ValueError("current P2 Stage-04 does not reference current P1 prototype/page-flow authority")

    prototype_text = _read(prototype_spec_path)
    interaction_text = _read(interaction_flow_path)
    page_rows = _table_after_marker(prototype_text, "## 4. Page Map")
    interaction_rows = _table_after_marker(interaction_text, "## 3. Interaction Matrix")
    flow_rows = _table_after_marker(interaction_text, "## 4. Flow Contract")
    enrichment_rows = _table_after_marker(stage03_text, "interaction_matrix_p2_enrichment")
    binding_rows = _table_after_marker(stage03_text, "data_service_binding_matrix")
    if not page_rows:
        raise ValueError("current P1 prototype page map is missing")
    if not interaction_rows:
        raise ValueError("current P1 interaction matrix is missing")
    if not enrichment_rows or not binding_rows:
        raise ValueError("current P2 Stage-03 interaction/service-binding authority is missing")

    p2_machine_authority = _load_p2_machine_authority(phase2_root)
    operation_catalog = _p2_operation_catalog(p2_machine_authority)
    accepted_terminal_roles = _accepted_terminal_roles(prototype_text)
    if not accepted_terminal_roles and operation_catalog:
        accepted_terminal_roles = list(
            dict.fromkeys(
                str(role).strip()
                for row in operation_catalog
                for role in row.get("terminal_roles", [])
                if str(role).strip()
            )
        )
    page_roles_by_id = {
        _clean(row.get("page_id")): _canonical_page_roles(_split_csv(row.get("allowed_roles")), accepted_terminal_roles)
        for row in page_rows
        if _clean(row.get("page_id"))
    }

    briefs = _page_briefs(prototype_text)
    flows_by_interaction = {
        _clean(row.get("from_interaction_id")): row
        for row in flow_rows
        if _clean(row.get("from_interaction_id"))
    }
    enrichment_by_interaction = {
        _clean(row.get("interaction_id")): row
        for row in enrichment_rows
        if _clean(row.get("interaction_id"))
    }
    binding_by_interaction = {
        _clean(row.get("interaction_id")): row
        for row in binding_rows
        if _clean(row.get("interaction_id"))
    }

    interactions_by_page: dict[str, list[dict[str, Any]]] = {}
    compiled_bindings: list[dict[str, Any]] = []
    for p1 in interaction_rows:
        interaction_id = _clean(p1.get("interaction_id"))
        page_id = _clean(p1.get("page_id"))
        if not interaction_id or not page_id:
            continue
        enrich = enrichment_by_interaction.get(interaction_id, {})
        binding = binding_by_interaction.get(interaction_id, {})
        flow = flows_by_interaction.get(interaction_id, {})
        source_status = _combined_status(
            p1.get("readiness_status"),
            enrich.get("readiness_status"),
            binding.get("readiness_status"),
            flow.get("readiness_status"),
        )
        source_reason = _combined_reason(
            p1.get("blocked_reason"),
            enrich.get("blocked_reason"),
            binding.get("blocked_reason"),
            flow.get("blocked_reason"),
        )
        page_roles = page_roles_by_id.get(page_id, [])
        binding_mode = _interaction_binding_mode(p1, binding)
        compiled_binding_mode = _clean(binding.get("binding_mode")) or (binding_mode if operation_catalog else "")
        exact_operation = _exact_catalog_operation(binding=binding, operation_catalog=operation_catalog)
        candidates = _operation_candidates(
            operation_catalog=operation_catalog,
            page_roles=page_roles,
            binding_mode=binding_mode,
        )
        operation_candidates = [str(row.get("operation_id") or "").strip() for row in candidates if str(row.get("operation_id") or "").strip()]
        binding_authority_incomplete = any(
            not _clean(binding.get(field))
            for field in ("service_binding_id", "domain_service", "api_endpoint", "http_method", "response_field_mapping")
        )
        p3_realization_open = bool(
            operation_catalog
            and candidates
            and source_status not in {"blocked", "stale"}
            and (source_status == "review-bound" or binding_authority_incomplete)
        )
        effective_status = "p3-realization-open" if p3_realization_open else source_status
        effective_reason = (
            "Frozen P1/P2 business/API/role authority is sufficient; exact page composition or UI-field projection remains P3 Agentic realization."
            if p3_realization_open
            else source_reason
        )
        compiled = {
            "interaction_id": interaction_id,
            "page_id": page_id,
            "region": _clean(p1.get("region")),
            "element_type": _clean(p1.get("element_type")),
            "interaction_pattern": _clean(p1.get("interaction_pattern")),
            "trigger_kind": _clean(p1.get("trigger_kind")),
            "action_type": _clean(p1.get("action_type")),
            "user_intent": _clean(p1.get("user_intent")),
            "visibility_rule": _clean(p1.get("visibility_rule")),
            "blocked_rule": _clean(p1.get("blocked_rule")),
            "success_state": _clean(p1.get("success_state")),
            "error_state": _clean(enrich.get("error_state") or p1.get("error_state")),
            "next_route": _clean(p1.get("next_route")),
            "use_case_id": _clean(p1.get("use_case_id")),
            "input_schema_ref": _clean(enrich.get("input_schema_ref")),
            "display_field_set": _clean(enrich.get("display_field_set")),
            "validation_rules": _clean(enrich.get("validation_rules")),
            "enabled_rule": _clean(enrich.get("enabled_rule")),
            "value_source": _clean(enrich.get("value_source")),
            "internal_exposure": _clean(enrich.get("internal_exposure")),
            "service_binding_id": _clean(binding.get("service_binding_id")),
            "binding_mode": compiled_binding_mode,
            "domain_service": _clean(binding.get("domain_service")),
            "api_endpoint": _clean(binding.get("api_endpoint")),
            "http_method": _clean(binding.get("http_method")),
            "operation_id": str((exact_operation or {}).get("operation_id") or "").strip(),
            "contract_id": str((exact_operation or {}).get("contract_id") or "").strip(),
            "operation_candidates": operation_candidates,
            "authority_status": "sufficient" if (exact_operation or candidates) else source_status,
            "realization_status": "p3-open" if p3_realization_open else "frozen-binding",
            "source_readiness_status": source_status,
            "request_field_mapping": _clean(binding.get("request_field_mapping")),
            "response_field_mapping": _clean(binding.get("response_field_mapping")),
            "db_entities": _clean(binding.get("db_entities")),
            "rbac_policy": _clean(binding.get("rbac_policy")),
            "audit_event": _clean(binding.get("audit_event")),
            "failure_codes": _clean(binding.get("failure_codes")),
            "ui_refresh_targets": _clean(binding.get("ui_refresh_targets")),
            "handoff_materialization": _clean(binding.get("handoff_materialization")),
            "flow_id": _clean(flow.get("flow_id")),
            "next_page_id": _clean(flow.get("next_page_id")),
            "failure_route": _clean(flow.get("failure_route")),
            "termination_condition": _clean(flow.get("termination_condition")),
            "readiness_status": effective_status,
            "blocked_reason": effective_reason,
        }
        interactions_by_page.setdefault(page_id, []).append(compiled)
        compiled_bindings.append(compiled)

    pages: list[dict[str, Any]] = []
    for raw_page in page_rows:
        page_id = _clean(raw_page.get("page_id"))
        page_name = _clean(raw_page.get("page_name"))
        route = _clean(raw_page.get("route"))
        if not page_id or not page_name or not route:
            continue
        brief = briefs.get(page_name, {})
        page_interactions = interactions_by_page.get(page_id, [])
        raw_page_roles = _split_csv(raw_page.get("allowed_roles"))
        canonical_page_roles = page_roles_by_id.get(page_id, []) if accepted_terminal_roles else raw_page_roles
        page_operation_candidates = list(
            dict.fromkeys(
                operation_id
                for interaction in page_interactions
                for operation_id in [
                    _clean(interaction.get("operation_id")),
                    *[str(value).strip() for value in interaction.get("operation_candidates", []) if str(value).strip()],
                ]
                if operation_id
            )
        )
        role_projection_source = "p1-machine-terminal-role-contracts" if canonical_page_roles else ""
        if accepted_terminal_roles and not canonical_page_roles and page_operation_candidates:
            canonical_page_roles = _operation_roles_for_page(
                operation_catalog,
                page_operation_candidates,
                accepted_terminal_roles,
            )
            if canonical_page_roles:
                role_projection_source = "p2-operation-authority-recovery"
        if not page_operation_candidates:
            page_operation_candidates = list(
                dict.fromkeys(
                    str(row.get("operation_id") or "").strip()
                    for mode in ("read", "write")
                    for row in _operation_candidates(
                        operation_catalog=operation_catalog,
                        page_roles=canonical_page_roles,
                        binding_mode=mode,
                    )
                    if str(row.get("operation_id") or "").strip()
                )
            )
        display_fields: list[str] = []
        data_required: list[dict[str, str]] = []
        field_source_mapping: list[dict[str, str]] = []
        actions: list[dict[str, Any]] = []
        for interaction in page_interactions:
            for field in _split_csv(interaction.get("display_field_set")):
                if field not in display_fields:
                    display_fields.append(field)
            endpoint = _clean(interaction.get("api_endpoint"))
            method = _clean(interaction.get("http_method"))
            if endpoint and method:
                data_required.append(
                    {
                        "source": "api",
                        "method": method,
                        "path": endpoint,
                        "interaction_id": _clean(interaction.get("interaction_id")),
                        "service_binding_id": _clean(interaction.get("service_binding_id")),
                    }
                )
            explicit_sources = _explicit_value_sources(interaction.get("value_source"))
            for field, source in explicit_sources.items():
                source_row = {"field": field, "source": source}
                if source_row not in field_source_mapping:
                    field_source_mapping.append(source_row)
            if _clean(interaction.get("trigger_kind")) != "page_load":
                request_fields = _machine_mapping_fields(interaction.get("request_field_mapping"))
                required_sources = [
                    {"field": field, "source": explicit_sources[field]}
                    for field in request_fields
                    if field in explicit_sources
                ]
                response_fields = _machine_mapping_fields(interaction.get("response_field_mapping"), right_hand=True)
                actions.append(
                    {
                        "interaction_id": _clean(interaction.get("interaction_id")),
                        "action": _clean(interaction.get("user_intent") or interaction.get("action_type")),
                        "action_type": _clean(interaction.get("action_type")),
                        "required_fields": [row["field"] for row in required_sources],
                        "required_input_sources": required_sources,
                        "response_bindings": [{"from": field, "to": field} for field in response_fields],
                        "on_success": _clean(interaction.get("success_state")),
                        "on_error": _clean(interaction.get("error_state")),
                        "next_route": _clean(interaction.get("next_route")),
                        "readiness_status": _clean(interaction.get("readiness_status")),
                    }
                )

        user_inputs = _merge_authority_user_inputs(
            _input_controls_from_brief(brief), field_source_mapping
        )
        pages.append(
            {
                "page_id": page_id,
                "page_name": page_name,
                "page_title": page_name,
                "route": route,
                "page_blueprint_type": _clean(raw_page.get("page_blueprint_type")),
                "primary_actor": canonical_page_roles[0] if len(canonical_page_roles) == 1 else _clean(raw_page.get("primary_actor")),
                "allowed_roles": canonical_page_roles,
                "surface_role_projection_source": role_projection_source or "p1-surface-matrix",
                "canonical_operation_candidates": page_operation_candidates,
                "primary_user_goal": _clean(raw_page.get("primary_user_goal")),
                "bound_use_case_ids": _split_csv(raw_page.get("bound_use_case_ids")),
                "business_objects": _split_csv(raw_page.get("business_objects")),
                "must_show_together": _split_csv(raw_page.get("must_show_together")),
                "required_regions": _split_csv(raw_page.get("required_regions")),
                "entry_conditions": _clean(raw_page.get("entry_conditions")),
                "exit_conditions": _clean(raw_page.get("exit_conditions")),
                "next_route_candidates": _split_csv(raw_page.get("next_route_candidates")),
                "denied_behavior": _clean(raw_page.get("denied_behavior")),
                "readiness_status": _combined_status(raw_page.get("readiness_status")),
                "blocked_reason": _clean(raw_page.get("blocked_reason")),
                "canonical_page_id": _clean(raw_page.get("canonical_page_id")),
                "surface_variant": _clean(raw_page.get("surface_variant")),
                "audience_mode": _clean(raw_page.get("audience_mode")),
                "session_role_source": _clean(raw_page.get("session_role_source")),
                "auth_entry_route": _clean(raw_page.get("auth_entry_route")),
                "auth_entry_label": _clean(raw_page.get("auth_entry_label")),
                "workspace_entry_roles": _split_csv(raw_page.get("workspace_entry_roles")),
                "route_reachability_mode": _clean(raw_page.get("route_reachability_mode")),
                "navigation_scope": _clean(raw_page.get("navigation_scope")),
                "handoff_visibility": _clean(raw_page.get("handoff_visibility")),
                "forbidden_exposure": _split_csv(raw_page.get("forbidden_exposure")),
                "primary_work_region": _clean(brief.get("primary_work_region")),
                "secondary_support_regions": list(brief.get("secondary_support_regions", [])),
                "dominant_component_pattern": _clean(brief.get("dominant_component_pattern")),
                "action_model": _clean(brief.get("action_model")),
                "render_blocks_in_order": list(brief.get("render_blocks_in_order", [])),
                "field_groups": list(brief.get("field_groups", [])),
                "p1_blueprint_input_controls": list(brief.get("input_controls", [])),
                "input_controls": [dict(item) for item in user_inputs],
                "compiled_interactions": page_interactions,
                "data_required": data_required,
                "data_presentation": list(display_fields),
                "display_fields": display_fields,
                "user_inputs": user_inputs,
                "actions_and_transitions": actions,
                "state_conditions": [],
                "field_source_mapping": field_source_mapping,
                "p3_realization_open": {
                    "application_shell": True,
                    "navigation_presentation": True,
                    "component_composition": True,
                    "state_presentation": True,
                    "responsive_accessibility_realization": True,
                    "copy_and_visual_language": True,
                },
            }
        )
    if not pages:
        raise ValueError("current P1/P2 artifacts did not compile any UI IA pages")

    projected_page_roles = list(
        dict.fromkeys(
            role
            for page in pages
            for role in page.get("allowed_roles", [])
            if str(role).strip()
        )
    )
    required_roles = list(accepted_terminal_roles or projected_page_roles)
    auth_session_fields = list(
        dict.fromkeys(
            str(mapping.get("field") or "").strip()
            for page in pages
            for mapping in page.get("field_source_mapping", [])
            if isinstance(mapping, dict)
            and str(mapping.get("source") or "").strip() == "auth-session"
            and str(mapping.get("field") or "").strip()
        )
    )
    auth_entry_route_hints = list(
        dict.fromkeys(
            str(page.get("auth_entry_route") or "").strip()
            for page in pages
            if str(page.get("auth_entry_route") or "").strip()
        )
    )
    session_role_source_hints = list(
        dict.fromkeys(
            str(page.get("session_role_source") or "").strip()
            for page in pages
            if str(page.get("session_role_source") or "").strip()
        )
    )
    test_personas = [
        {
            "persona_id": _persona_id(role),
            "roles": [role],
            "qualification_mode": "independent-terminal-role",
        }
        for role in required_roles
    ]
    role_page_coverage = {
        role: sorted(
            str(page.get("page_id") or "").strip()
            for page in pages
            if role in page.get("allowed_roles", []) and str(page.get("page_id") or "").strip()
        )
        for role in required_roles
    }
    role_authority_missing_page_ids = sorted(
        str(page.get("page_id") or "").strip()
        for page in pages
        if str(page.get("primary_actor") or "").strip()
        and not page.get("allowed_roles")
        and str(page.get("page_id") or "").strip()
    )
    missing_terminal_role_pages = sorted(role for role, page_ids in role_page_coverage.items() if not page_ids)
    operation_roles = {
        str(role).strip()
        for row in operation_catalog
        for role in row.get("terminal_roles", [])
        if str(role).strip()
    }
    missing_operation_authority_roles = sorted(role for role in required_roles if operation_catalog and role not in operation_roles)
    role_authority_status = (
        "sufficient"
        if not role_authority_missing_page_ids and not missing_terminal_role_pages and not missing_operation_authority_roles
        else "review-bound"
    )
    product_access_requirements = {
        "requires_authenticated_session": bool(required_roles or auth_session_fields),
        "required_roles": required_roles,
        "test_personas": test_personas,
        "terminal_role_qualification": {
            "status": role_authority_status,
            "independent_persona_required": bool(required_roles),
            "super_role_qualifies_terminal_roles": False,
            "role_page_coverage": role_page_coverage,
            "missing_role_authority_page_ids": role_authority_missing_page_ids,
            "missing_terminal_role_pages": missing_terminal_role_pages,
            "missing_operation_authority_roles": missing_operation_authority_roles,
            "return_owner": (
                "P3 gap decision"
                if role_authority_missing_page_ids or missing_terminal_role_pages or missing_operation_authority_roles
                else ""
            ),
        },
        "auth_session_fields": auth_session_fields,
        "tenant_context_required": (
            any("tenant" in field.casefold() for field in auth_session_fields)
            or any(
                str(field.get("name") or "").strip().casefold() == "tenant_id"
                for row in operation_catalog
                for field in row.get("request_fields", [])
                if isinstance(field, dict)
            )
        ),
        "normal_api_auth_transport": "authorization-bearer",
        "forbidden_consumer_auth_shortcuts": [
            "x-phase3-auth-context",
            "phase3-role-session",
            "injected-browser-storage-identity",
        ],
        "upstream_realization_hints": {
            "session_role_sources": session_role_source_hints,
            "auth_entry_routes": auth_entry_route_hints,
        },
        "p3_realization_open": {
            "auth_entry_presentation": True,
            "session_storage_strategy": True,
            "provider_integration_when_not_frozen": True,
            "expired_or_denied_session_recovery": True,
        },
        "boundary": (
            "P3 must realize a product-facing authenticated session over the frozen security/RBAC/tenant boundary. "
            "Exact login/session UX remains P3 Agentic judgment unless explicitly frozen upstream; normal consumer API calls "
            "must use Authorization Bearer and must not depend on Phase-3 validation headers or injected browser identity."
        ),
    }

    effective_locale = resolve_output_locale(ui_locale)
    ready_bindings = [
        row for row in compiled_bindings
        if str(row.get("readiness_status") or "").strip().casefold() == "ready"
    ]
    read_bindings = [
        row for row in ready_bindings
        if str(row.get("http_method") or "").strip().upper() in {"GET", "HEAD"}
        or str(row.get("binding_mode") or "").strip().casefold() == "read"
    ]
    write_bindings = [
        row for row in ready_bindings
        if str(row.get("http_method") or "").strip().upper() not in {"", "GET", "HEAD"}
        or str(row.get("binding_mode") or "").strip().casefold() in {"write", "read_write"}
    ]
    durable_business_object_count = len(
        {
            str(value).strip()
            for page in pages
            for value in page.get("business_objects", [])
            if str(value).strip()
        }
    )
    machine_read_operations = [row for row in operation_catalog if str(row.get("binding_mode") or "") == "read"]
    machine_write_operations = [row for row in operation_catalog if str(row.get("binding_mode") or "") == "write"]
    effective_read_authority = machine_read_operations if operation_catalog else read_bindings
    effective_write_authority = machine_write_operations if operation_catalog else write_bindings
    requires_business_data_discovery = bool(
        effective_write_authority and (len(pages) > 1 or durable_business_object_count > 1)
    )
    manual_identifier_inputs = [
        {
            "page_id": str(page.get("page_id") or "").strip(),
            "route": str(page.get("route") or "").strip(),
            "field": str(item.get("field") or "").strip(),
        }
        for page in pages
        for item in page.get("user_inputs", [])
        if isinstance(item, dict) and bool(item.get("internal_identifier_reference"))
    ]
    internal_identifier_request_fields = list(
        dict.fromkeys(
            str(field.get("name") or "").strip()
            for row in operation_catalog
            for field in row.get("request_fields", [])
            if isinstance(field, dict)
            and _looks_like_internal_identifier_reference(str(field.get("name") or ""))
        )
    )
    operation_tables = _p2_operation_tables(p2_machine_authority)
    context_reentry_requirements = _p2_context_reentry_requirements(p2_machine_authority)
    context_reentry_operation_ids = list(
        dict.fromkeys(
            operation_id
            for row in context_reentry_requirements
            for operation_id in row.get("reentry_operation_ids", [])
            if operation_id
        )
    )
    clean_first_use_write_tables = sorted(
        {
            table_name
            for row in machine_write_operations
            for table_name in operation_tables.get(str(row.get("operation_id") or "").strip(), [])
            if table_name
        }
    )
    authority_tables = sorted({table_name for values in operation_tables.values() for table_name in values if table_name})
    clean_first_use_context_tables = sorted(set(authority_tables) - set(clean_first_use_write_tables))
    business_data_requirements = {
        "requires_business_data_discovery": requires_business_data_discovery,
        "read_model_status": (
            "sufficient" if (not requires_business_data_discovery or effective_read_authority) else "authority-gap"
        ),
        "read_interaction_ids": [str(row.get("interaction_id") or "").strip() for row in read_bindings],
        "write_interaction_ids": [str(row.get("interaction_id") or "").strip() for row in write_bindings],
        "read_operation_ids": [str(row.get("operation_id") or "").strip() for row in machine_read_operations],
        "write_operation_ids": [str(row.get("operation_id") or "").strip() for row in machine_write_operations],
        "internal_identifier_request_fields": internal_identifier_request_fields,
        "identifier_source_policy": "internal identifiers must come from authenticated/workflow context or accepted read/write responses, never manual consumer entry",
        "manual_identifier_inputs": manual_identifier_inputs,
        "consumer_manual_internal_ids_allowed": False,
        "clean_first_use_required": bool(effective_write_authority),
        "clean_first_use_write_tables": clean_first_use_write_tables,
        "clean_first_use_context_tables": clean_first_use_context_tables,
        "clean_first_use_table_classification_source": "p2-operation-table-authority" if operation_tables else "",
        "context_reentry_required": bool(context_reentry_requirements) or requires_business_data_discovery,
        "context_reentry_requirements": context_reentry_requirements,
        "context_reentry_operation_ids": context_reentry_operation_ids,
        "context_reentry_authority_source": (
            "p2-commitment-interaction-context-coverage" if context_reentry_requirements else ""
        ),
        "missing_authority": (
            ["business-read-model-authority-missing"]
            if requires_business_data_discovery and not effective_read_authority
            else []
        ),
        "return_owner": "P3 gap decision" if requires_business_data_discovery and not effective_read_authority else "",
        "gap_decision_route": "p3-gap-decision-required" if requires_business_data_discovery and not effective_read_authority else "",
        "claim_ceiling": "Business discovery/read-model sufficiency only; no seed data, fixture identity, or synthetic provider success may substitute for a consumer-visible read path.",
    }
    if p3_read_model_bindings is not None:
        from phase3.p3_fact_registration import realized_read_model_resolution
        business_data_requirements["p3_read_model_bindings"] = p3_read_model_bindings
        resolution = realized_read_model_resolution(root=output_path.parent, requirements=business_data_requirements)
        if resolution:
            business_data_requirements["p3_gap_resolution"] = resolution
            business_data_requirements["read_model_status"] = "registered-p3-read-model"
            # Keep the original missing-authority array visible as frozen-source provenance.
    project_language_requirements = {
        "consumer_locale": effective_locale,
        "consumer_copy_must_match_project_locale": True,
        "full_i18n_required": False,
        "technical_identifiers_may_remain_canonical": True,
    }

    payload = {
        "schema_version": "wff.ui-ia-contract.v1",
        "mode": "compiled-contract-generated",
        "contract_source": "p1-p2-current-authority-projection",
        "locale": effective_locale,
        "source_artifacts": {
            "prototype_spec": str(prototype_spec_path),
            "interaction_flow_contract": str(interaction_flow_path),
            "stage_03": str(stage03_path),
            "stage_04": str(stage04_path),
            "p2_machine_authority": (
                str(phase2_root / "p2-agentic-architecture-authority.json") if p2_machine_authority else ""
            ),
        },
        "contract_rule": (
            "Project explicit current P1/P2 machine business/API/security authority as canonical truth. Legacy surface interaction "
            "projection remains fail-closed only when the machine authority needed for that interaction class is absent; realization-only "
            "frontend detail remains P3 Agentic authority, including exact page composition and UI-field projection when frozen machine "
            "authority is sufficient."
        ),
        "canonical_operation_catalog": operation_catalog,
        "compiled_bindings": compiled_bindings,
        "product_access_requirements": product_access_requirements,
        "business_data_requirements": business_data_requirements,
        "project_language_requirements": project_language_requirements,
        "pages": pages,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
