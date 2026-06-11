from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Callable

from phase3.api_client_scaffolder import build_api_client_document
from phase3.behavior_card_models import build_behavior_card_models
from phase3.contract_test_scaffolder import scaffold_contract_tests
from phase3.esp_to_migration import generate_migration_sql, parse_schema_tables
from phase3.esp_to_openapi import build_openapi_spec, parse_api_endpoint_rows
from phase3.impl_action_cards import run_impl_action_cards
from phase3.impl_contract_pack import materialize_contract_pack
from phase3.impl_db_schema import run_impl_db_schema
from phase3.openapi_to_types import build_types_document
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
from phase3.sql_test_scaffolder import scaffold_sql_tests


def build_implementation_action_cards(*, phase2_root: Path, output_dir: Path) -> dict[str, object]:
    summary = run_impl_action_cards(phase2_root=phase2_root, output_dir=output_dir)
    validation_payload = summary.get("validation_payload", {})
    return validation_payload if isinstance(validation_payload, dict) else {}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def optional_phase3_diagnostic_module(module_name: str):
    try:
        module = __import__(f"phase3.{module_name}", fromlist=["*"])
    except ModuleNotFoundError as exc:
        if exc.name == f"phase3.{module_name}":
            return None
        raise
    return module


def diagnostic_sidecar_unavailable_summary(sidecar_id: str) -> dict[str, object]:
    return {
        "mode": "unavailable",
        "sidecar_id": sidecar_id,
        "reason": f"{sidecar_id}_sidecar_not_packaged",
    }


def write_test_obligation_artifacts(*args: object, **kwargs: object) -> dict[str, object]:
    module = optional_phase3_diagnostic_module("test_obligation_matrix")
    if module is None:
        return diagnostic_sidecar_unavailable_summary("test_obligation_matrix")
    return module.write_test_obligation_artifacts(*args, **kwargs)


def write_test_richness_review_artifacts(*args: object, **kwargs: object) -> dict[str, object]:
    module = optional_phase3_diagnostic_module("test_richness_review")
    if module is None:
        return diagnostic_sidecar_unavailable_summary("test_richness_review")
    return module.write_test_richness_review_artifacts(*args, **kwargs)


def _optional_test_scaffolder_module(module_name: str):
    try:
        return importlib.import_module(f"phase3.{module_name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"phase3.{module_name}":
            return None
        raise


def _test_scaffolder_output_dir(args: tuple[object, ...], kwargs: dict[str, object]) -> Path:
    raw = kwargs.get("output_dir") if "output_dir" in kwargs else (args[1] if len(args) > 1 else ".")
    return Path(raw)


def _test_scaffolder_unavailable_summary(output_dir: Path, sidecar_id: str) -> dict[str, object]:
    return {
        "output_dir": str(output_dir),
        "files_created": [],
        "count": 0,
        "mode": "unavailable",
        "sidecar_id": sidecar_id,
        "reason": f"{sidecar_id}_sidecar_not_packaged",
    }


def scaffold_scenario_tests(*args: object, **kwargs: object) -> dict[str, object]:
    module = _optional_test_scaffolder_module("scenario_test_scaffolder")
    if module is None:
        return _test_scaffolder_unavailable_summary(
            _test_scaffolder_output_dir(args, kwargs),
            "scenario_test_scaffolder",
        )
    return module.scaffold_scenario_tests(*args, **kwargs)


def scaffold_replay_tests(*args: object, **kwargs: object) -> dict[str, object]:
    module = _optional_test_scaffolder_module("replay_test_scaffolder")
    if module is None:
        return _test_scaffolder_unavailable_summary(
            _test_scaffolder_output_dir(args, kwargs),
            "replay_test_scaffolder",
        )
    return module.scaffold_replay_tests(*args, **kwargs)


def build_test_trace_matrix(*args: object, **kwargs: object) -> dict[str, object]:
    module = _optional_test_scaffolder_module("test_trace_matrix_builder")
    if module is None:
        return {
            "rows": [],
            "summary": {
                "contract_trace_count": 0,
                "scenario_count": 0,
                "replay_count": 0,
                "unmatched_contract_trace_ids": [],
                "matched_endpoint_count": 0,
                "endpoint_fallback_count": 0,
                "security_decision_count": 0,
                "matrix_row_count": 0,
            },
            "mode": "unavailable",
            "sidecar_id": "test_trace_matrix_builder",
            "sidecar_unavailable": True,
            "reason": "test_trace_matrix_builder_sidecar_not_packaged",
        }
    return module.build_test_trace_matrix(*args, **kwargs)


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
