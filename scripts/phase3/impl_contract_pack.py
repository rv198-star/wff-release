from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from phase3.api_client_scaffolder import build_api_client_document
from phase3.contract_tools import (
    build_openapi_spec,
    derived_openapi_from_compiled_bindings,
    enrich_openapi_spec_with_behavior_evidence,
    load_compiled_bindings_document,
    parse_api_endpoint_rows,
)
from phase3.impl_context import write_json
from phase3.openapi_to_types import build_types_document
from phase3.phase3_behavior_card_consumption import extract_behavior_card_model
from phase3.phase3_behavior_card_scaffolder import write_behavior_card
from phase3.phase3_behavior_risk import classify_operation_risk
from phase3.phase3_behavior_source_resolver import load_operation_source_obligation_matrix, resolve_behavior_sources
from phase3.ui_prototype_fallback import generate_ui_prototype_fallback
from phase3.contract_tools import parse_schema_tables


def _snake_case(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized)
    return normalized.strip("_").lower()


def _module_slug_from_path(path: str) -> str:
    parts = [part for part in str(path).strip("/").split("/") if part and not part.startswith("{")]
    if parts and parts[0] == "api":
        parts = parts[1:]
    if parts and parts[0].startswith("v") and len(parts) > 1:
        parts = parts[1:]
    return (parts[0] if parts else "default").replace("_", "-")


def _operation_entries_from_openapi(spec: dict[str, object]) -> dict[str, dict[str, str]]:
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


def build_behavior_card_models(*, phase2_root: Path, output_dir: Path, spec: dict[str, object]) -> dict[str, dict[str, object]]:
    models: dict[str, dict[str, object]] = {}
    esp_text = (phase2_root / "engineering-spec-pack.md").read_text(encoding="utf-8")
    table_names = [str(table.get("table_name", "")).strip() for table in parse_schema_tables(esp_text)]
    openapi_entries = _operation_entries_from_openapi(spec)
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
        module_slug = _module_slug_from_path(path)
        operation_snake = _snake_case(operation_id)
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
        card_path = write_behavior_card(output_dir, source_bundle, risk)
        models[operation_id] = extract_behavior_card_model(card_path.read_text(encoding="utf-8"))
    return models


def materialize_contract_pack(
    *,
    phase2_root: Path | None = None,
    output_dir: Path,
    title: str,
    version: str,
    esp_text: str,
    stage_03_text: str = "",
    stage_04_text: str = "",
    ui_locale: str = "en",
    enable_ui_fallback: bool = False,
    enforce_compiled_authority: bool = False,
) -> dict[str, Any]:
    openapi_path = output_dir / "contracts" / "openapi.yaml"
    shared_types_path = output_dir / "packages" / "shared-types" / "index.ts"
    api_client_path = output_dir / "packages" / "api-client" / "index.ts"
    implementation_bindings_path = output_dir / "implementation-bindings.json"
    ui_fallback_report_path = output_dir / "prototype-fallback" / "ui-prototype-fallback-report.json"
    ui_ia_contract_path = output_dir / "prototype-fallback" / "ui-ia-contract.json"

    base_spec = build_openapi_spec(parse_api_endpoint_rows(esp_text), title=title, version=version)
    write_json(openapi_path, base_spec)

    if enable_ui_fallback and phase2_root is not None:
        ui_fallback_summary = generate_ui_prototype_fallback(
            phase2_root=phase2_root,
            output_dir=output_dir,
            stage_04_text=stage_04_text,
            esp_text=esp_text,
            stage_03_text=stage_03_text,
            openapi_path=openapi_path,
            ui_locale=ui_locale,
        )
        compiled_bindings = load_compiled_bindings_document(ui_ia_contract_path) if ui_ia_contract_path.exists() else []
    else:
        ui_fallback_summary = {
            "mode": "not-requested",
            "reason": "backend-first-mainline-default",
        }
        compiled_bindings = []

    spec = (
        derived_openapi_from_compiled_bindings(base_spec, compiled_bindings)
        if enforce_compiled_authority
        else base_spec
    )
    write_json(
        implementation_bindings_path,
        {
            "artifact_kind": "compiled-binding-artifact",
            "compiled_bindings": compiled_bindings,
            "rows": [],
        },
    )
    behavior_card_models = (
        build_behavior_card_models(phase2_root=phase2_root, output_dir=output_dir, spec=spec)
        if phase2_root is not None
        else {}
    )
    spec = enrich_openapi_spec_with_behavior_evidence(spec, behavior_card_models)
    write_json(openapi_path, spec)
    shared_types_path.parent.mkdir(parents=True, exist_ok=True)
    shared_types_path.write_text(build_types_document(spec), encoding="utf-8")
    api_client_path.parent.mkdir(parents=True, exist_ok=True)
    api_client_path.write_text(build_api_client_document(spec), encoding="utf-8")
    return {
        "ui_fallback_report_path": ui_fallback_report_path,
        "ui_ia_contract_path": ui_ia_contract_path,
        "openapi_path": openapi_path,
        "shared_types_path": shared_types_path,
        "api_client_path": api_client_path,
        "implementation_bindings_path": implementation_bindings_path,
        "ui_fallback_summary": ui_fallback_summary,
        "behavior_card_models": behavior_card_models,
        "spec": spec,
    }
