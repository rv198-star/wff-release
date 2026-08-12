from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from phase3.contract_tools import parse_schema_tables
from phase3.phase3_behavior_card_consumption import extract_behavior_card_model
from phase3.phase3_behavior_card_scaffolder import write_behavior_card
from phase3.phase3_behavior_risk import classify_operation_risk
from phase3.phase3_behavior_source_resolver import load_operation_source_obligation_matrix, resolve_behavior_sources


def snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def module_slug_from_path(path: str) -> str:
    parts = [part for part in str(path).strip("/").split("/") if part and not part.startswith("{")]
    if parts and parts[0] == "api":
        parts = parts[1:]
    if parts and parts[0].startswith("v") and len(parts) > 1:
        parts = parts[1:]
    return (parts[0] if parts else "default").replace("_", "-")


def operation_entries_from_openapi(spec: dict[str, object]) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return entries
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if str(method).lower() not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId") or f"{method}-{path}").strip()
            if not operation_id:
                continue
            responses = operation.get("responses", {})
            errors = [str(status) for status in responses if str(status).startswith(("4", "5"))] if isinstance(responses, dict) else []
            entries.setdefault(
                operation_id,
                {
                    "operation_id": operation_id,
                    "method": str(method).upper(),
                    "path": str(path),
                    "errors": ",".join(errors),
                },
            )
    return entries


def _accepted_p3_target_projection(
    implementation_authority: Mapping[str, Any] | None,
    operation_id: str,
) -> dict[str, Any]:
    if not isinstance(implementation_authority, Mapping):
        return {}
    decisions = implementation_authority.get("decisions", {})
    if not isinstance(decisions, Mapping):
        return {}
    decision = decisions.get(operation_id)
    if not isinstance(decision, Mapping):
        return {
            "controller_target": "not separately declared by accepted P3 authority",
            "service_target": "not separately declared by accepted P3 authority",
            "repository_target": "not separately declared by accepted P3 authority",
            "unit_test": "not separately declared by accepted P3 authority",
            "p3_declared_tests": "none declared by accepted P3 authority",
        }
    implementation_targets = [str(item).strip() for item in decision.get("implementation_targets", []) if str(item).strip()]
    test_targets = [str(item).strip() for item in decision.get("test_targets", []) if str(item).strip()]
    service_targets = [target for target in implementation_targets if target.endswith(".service.ts")]
    repository_targets = [target for target in implementation_targets if target.endswith(".repository.ts")]
    unit_targets = [target for target in test_targets if target.startswith("tests/unit/")]
    persistence_rows: list[Mapping[str, Any]] = []
    slice_decisions = implementation_authority.get("slice_decisions", {})
    if isinstance(slice_decisions, Mapping):
        for raw in slice_decisions.values():
            if not isinstance(raw, Mapping) or str(raw.get("operation_id") or "").strip() != operation_id:
                continue
            rows = raw.get("durable_persistence_decisions", [])
            if isinstance(rows, list):
                persistence_rows.extend(item for item in rows if isinstance(item, Mapping))
    persistence_modes = sorted({str(row.get("persistence_mode") or "").strip() for row in persistence_rows if str(row.get("persistence_mode") or "").strip()})
    command_kinds = sorted({str(row.get("command_kind") or "").strip() for row in persistence_rows if str(row.get("command_kind") or "").strip()})
    return {
        "controller_target": "not separately declared by accepted P3 authority",
        "service_target": ", ".join(service_targets) or "not separately declared by accepted P3 authority",
        "repository_target": ", ".join(repository_targets) or "not separately declared by accepted P3 authority",
        "unit_test": ", ".join(unit_targets) or "not separately declared by accepted P3 authority",
        "p3_declared_tests": ", ".join(test_targets) or "none declared by accepted P3 authority",
        "persistence_mode": persistence_modes[0] if len(persistence_modes) == 1 else "",
        "persistence_command_kind": command_kinds[0] if len(command_kinds) == 1 else "",
    }


def build_behavior_card_models(
    *,
    phase2_root: Path,
    output_dir: Path,
    spec: dict[str, object],
    implementation_authority: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, object]]:
    models: dict[str, dict[str, object]] = {}
    esp_text = (phase2_root / "engineering-spec-pack.md").read_text(encoding="utf-8")
    table_names = [str(table.get("table_name", "")).strip() for table in parse_schema_tables(esp_text)]
    openapi_entries = operation_entries_from_openapi(spec)
    p2_operation_rows = load_operation_source_obligation_matrix(phase2_root)
    operation_ids = list(dict.fromkeys([*p2_operation_rows.keys(), *openapi_entries.keys()]))
    for operation_id in operation_ids:
        if not operation_id:
            continue
        p2_row = p2_operation_rows.get(operation_id, {})
        openapi_entry = openapi_entries.get(operation_id, {})
        method = str(openapi_entry.get("method") or p2_row.get("http_method") or "").upper()
        path = str(openapi_entry.get("path") or p2_row.get("api_endpoint") or f"/{operation_id}")
        errors = [item for item in str(openapi_entry.get("errors", "")).split(",") if item]
        source_bundle = resolve_behavior_sources(phase2_root, operation_id)
        risk = classify_operation_risk(
            {
                "operation_id": operation_id,
                "method": method,
                "errors": errors,
                "upstream_trace_ids": source_bundle.get("upstream_trace_ids", []),
            }
        )
        if not risk.get("requires_behavior_card"):
            continue
        module_slug = module_slug_from_path(path)
        operation_snake = snake_case(operation_id)
        matched_tables = [table for table in table_names if table and any(token in table for token in operation_snake.split("_") if token)]
        persistence_surfaces = ", ".join(matched_tables or table_names[:1])
        source_bundle.update(
            {
                "persistence_surfaces": persistence_surfaces,
                "contract_test": f"tests/contracts/{operation_id.lower()}.contract.test.ts",
                "scenario_test": "tests/scenarios/* linked by P2 scenario coverage",
                "replay_test": "tests/replays/* linked by P2 replay evidence",
                "sql_test": f"tests/sql/{(matched_tables or table_names or ['operation'])[0]}.sql.test.ts",
                "unit_test": f"tests/unit/api/modules/{module_slug}.unit.test.ts",
                "controller_target": f"apps/api/src/modules/{module_slug}/{module_slug}.controller.ts",
                "service_target": f"apps/api/src/modules/{module_slug}/{module_slug}.service.ts",
                "repository_target": f"apps/api/src/modules/{module_slug}/{module_slug}.repository.ts",
                "db_target": persistence_surfaces,
            }
        )
        authority_projection = _accepted_p3_target_projection(implementation_authority, operation_id)
        if authority_projection:
            source_bundle.update(authority_projection)
        card_path = write_behavior_card(output_dir, source_bundle, risk)
        models[operation_id] = extract_behavior_card_model(card_path.read_text(encoding="utf-8"))
    return models
