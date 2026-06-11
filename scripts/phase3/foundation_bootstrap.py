from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from phase3.api_client_scaffolder import build_api_client_document
from phase3.contract_test_scaffolder import scaffold_contract_tests
from phase3.esp_to_migration import generate_migration_sql, parse_schema_tables
from phase3.esp_to_openapi import build_openapi_spec, parse_api_endpoint_rows
from phase3.impl_action_cards import run_impl_action_cards
from phase3.impl_contract_pack import materialize_contract_pack
from phase3.impl_db_schema import run_impl_db_schema
from phase3.openapi_to_types import build_types_document
from phase3.phase3_behavior_card_consumption import extract_behavior_card_model
from phase3.phase3_behavior_card_scaffolder import write_behavior_card
from phase3.phase3_behavior_risk import classify_operation_risk
from phase3.phase3_behavior_source_resolver import load_operation_source_obligation_matrix, resolve_behavior_sources
from phase3.phase3_implementation_action_card_scaffolder import (
    load_action_card_obligations,
    render_implementation_action_card,
    validate_action_card_obligations,
)
from phase3.contract_tools import (
    derived_openapi_from_compiled_bindings,
    enrich_openapi_spec_with_behavior_evidence,
    load_compiled_bindings_document,
)
from phase3.test_obligation_matrix import write_test_obligation_artifacts
from phase3.test_richness_review import write_test_richness_review_artifacts
from phase3.ui_prototype_fallback import generate_ui_prototype_fallback
from phase3.replay_test_scaffolder import scaffold_replay_tests
from phase3.scenario_test_scaffolder import scaffold_scenario_tests
from phase3.sql_test_scaffolder import scaffold_sql_tests
from phase3.test_trace_matrix_builder import build_test_trace_matrix


def _snake_case(value: str) -> str:
    import re

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


def build_implementation_action_cards(*, phase2_root: Path, output_dir: Path) -> dict[str, object]:
    summary = run_impl_action_cards(phase2_root=phase2_root, output_dir=output_dir)
    validation_payload = summary.get("validation_payload", {})
    return validation_payload if isinstance(validation_payload, dict) else {}


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


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_phase2_source_texts(phase2_root: Path) -> tuple[str, str, str]:
    esp_text = (phase2_root / "engineering-spec-pack.md").read_text(encoding="utf-8")
    stage_03_text = (phase2_root / "stage-03-data-storage-and-interface-design.md").read_text(encoding="utf-8")
    stage_04_text = (phase2_root / "stage-04-design-convergence-and-delivery-prototype.md").read_text(encoding="utf-8")
    return esp_text, stage_03_text, stage_04_text


def emit_phase3_bootstrap_artifacts(
    *,
    phase2_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    ui_locale: str,
    enable_ui_fallback: bool,
    enforce_compiled_authority: bool,
) -> dict[str, object]:
    ui_fallback_report_path = output_dir / "prototype-fallback" / "ui-prototype-fallback-report.json"
    ui_ia_contract_path = output_dir / "prototype-fallback" / "ui-ia-contract.json"
    openapi_path = output_dir / "contracts" / "openapi.yaml"
    migration_path = output_dir / "db" / "migrations" / "001_initial_schema.sql"
    shared_types_path = output_dir / "packages" / "shared-types" / "index.ts"
    api_client_path = output_dir / "packages" / "api-client" / "index.ts"
    sql_tests_dir = output_dir / "tests" / "sql"
    contracts_dir = output_dir / "tests" / "contracts"
    scenarios_dir = output_dir / "tests" / "scenarios"
    replays_dir = output_dir / "tests" / "replays"
    trace_matrix_path = output_dir / "test-trace-matrix.json"
    implementation_bindings_path = output_dir / "implementation-bindings.json"

    contract_pack = materialize_contract_pack(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=title,
        version=version,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        ui_locale=ui_locale,
        enable_ui_fallback=enable_ui_fallback,
        enforce_compiled_authority=enforce_compiled_authority,
    )
    spec = contract_pack["spec"]
    ui_fallback_summary = contract_pack["ui_fallback_summary"]
    behavior_card_models = contract_pack["behavior_card_models"]
    db_schema_summary = run_impl_db_schema(
        phase2_root=phase2_root,
        output_dir=output_dir,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        behavior_card_models=behavior_card_models,
    )
    action_card_summary = build_implementation_action_cards(phase2_root=phase2_root, output_dir=output_dir)
    contract_summary = scaffold_contract_tests(spec, contracts_dir, behavior_card_models=behavior_card_models)
    sql_summary = db_schema_summary["sql_summary"]
    scenario_summary = scaffold_scenario_tests(
        stage_03_text,
        scenarios_dir,
        esp_text=esp_text,
        openapi_spec=spec,
        behavior_card_models=behavior_card_models,
    )
    replay_summary = scaffold_replay_tests(
        stage_04_text,
        replays_dir,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        openapi_spec=spec,
        behavior_card_models=behavior_card_models,
    )
    test_obligation_summary = write_test_obligation_artifacts(
        output_dir=output_dir,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_spec=spec,
        behavior_card_models=behavior_card_models,
    )
    test_richness_review_summary = write_test_richness_review_artifacts(
        output_dir=output_dir,
        test_obligation_audit_path=output_dir / "test-obligation-audit.json",
    )

    matrix = build_test_trace_matrix(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_spec=spec,
    )
    trace_matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "ui_fallback_report_path": ui_fallback_report_path,
        "ui_ia_contract_path": ui_ia_contract_path,
        "openapi_path": openapi_path,
        "migration_path": migration_path,
        "shared_types_path": shared_types_path,
        "api_client_path": api_client_path,
        "contracts_dir": contracts_dir,
        "sql_tests_dir": sql_tests_dir,
        "scenarios_dir": scenarios_dir,
        "replays_dir": replays_dir,
        "trace_matrix_path": trace_matrix_path,
        "implementation_bindings_path": implementation_bindings_path,
        "ui_fallback_summary": ui_fallback_summary,
        "contract_summary": contract_summary,
        "sql_summary": sql_summary,
        "scenario_summary": scenario_summary,
        "replay_summary": replay_summary,
        "behavior_card_models": behavior_card_models,
        "behavior_card_summary": {
            "output_dir": str(output_dir / "behavior-cards"),
            "count": len(behavior_card_models),
            "operation_ids": sorted(behavior_card_models),
        },
        "test_obligation_summary": test_obligation_summary,
        "test_richness_review_summary": test_richness_review_summary,
        "action_card_summary": action_card_summary,
        "spec": spec,
        "matrix": matrix,
    }


def run_phase3_bootstrap_stage_impl(
    *,
    args: Any,
    phase2_root: Path,
    output_dir: Path,
    ui_locale: str,
    analyze_phase3_bootstrap_fn: Callable[..., dict[str, Any]],
) -> dict[str, object]:
    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
    bootstrap = emit_phase3_bootstrap_artifacts(
        phase2_root=phase2_root,
        output_dir=output_dir,
        title=args.title,
        version=args.version,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        ui_locale=ui_locale,
        enable_ui_fallback=True,
        enforce_compiled_authority=True,
    )

    quality_report_path = output_dir / "phase3-quality-check.json"
    quality = analyze_phase3_bootstrap_fn(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_path=bootstrap["openapi_path"],
        migration_path=bootstrap["migration_path"],
        shared_types_path=bootstrap["shared_types_path"],
        api_client_path=bootstrap["api_client_path"],
        contracts_dir=bootstrap["contracts_dir"],
        scenarios_dir=bootstrap["scenarios_dir"],
        replays_dir=bootstrap["replays_dir"],
        test_trace_matrix_path=bootstrap["trace_matrix_path"],
        implementation_bindings_path=bootstrap["implementation_bindings_path"],
        require_frontend_contract=True,
    )
    write_json(quality_report_path, quality)

    return {
        "output_dir": str(output_dir),
        "openapi": str(bootstrap["openapi_path"]),
        "migration": str(bootstrap["migration_path"]),
        "shared_types": str(bootstrap["shared_types_path"]),
        "api_client": str(bootstrap["api_client_path"]),
        "contract_summary": bootstrap["contract_summary"],
        "sql_summary": bootstrap["sql_summary"],
        "scenario_summary": bootstrap["scenario_summary"],
        "replay_summary": bootstrap["replay_summary"],
        "ui_prototype_fallback_summary": bootstrap["ui_fallback_summary"],
        "quality_report": str(quality_report_path),
        "quality_gate": quality["overall_quality_gate"],
        "recommended_formal_state": quality["recommended_formal_state"],
        "test_richness_review_summary": bootstrap["test_richness_review_summary"],
    }
