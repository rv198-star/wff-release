from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from phase3.api_client_scaffolder import build_api_client_document
from phase3.behavior_card_models import build_behavior_card_models
from phase3.contract_tools import (
    build_openapi_spec,
    derived_openapi_from_compiled_bindings,
    enrich_openapi_spec_with_behavior_evidence,
    load_compiled_bindings_document,
    parse_api_endpoint_rows,
)
from phase3.impl_context import write_json
from phase3.openapi_to_types import build_types_document


def _generate_ui_prototype_fallback(**kwargs: Any) -> dict[str, Any]:
    module = importlib.import_module("phase3.ui_prototype_fallback")
    return module.generate_ui_prototype_fallback(**kwargs)


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
        ui_fallback_summary = _generate_ui_prototype_fallback(
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
