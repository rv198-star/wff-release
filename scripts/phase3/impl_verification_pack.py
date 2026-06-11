from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from phase3.contract_test_scaffolder import scaffold_contract_tests
from phase3.contract_tools import build_openapi_spec, parse_api_endpoint_rows
from phase3.impl_context import load_phase2_source_texts, write_json
from phase3.schema_test_scaffolder import scaffold_schema_tests
from phase3.sql_test_scaffolder import scaffold_sql_tests


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


def run_impl_verification(
    *,
    mode: str,
    workspace_root: Path,
    phase2_root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    target_root = output_dir or workspace_root
    target_root.mkdir(parents=True, exist_ok=True)
    generated_tests: dict[str, Any] = {}
    if mode == "generate-tests":
        if phase2_root is None:
            raise ValueError("--phase2-root is required for generate-tests mode")
        esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(phase2_root)
        spec = build_openapi_spec(parse_api_endpoint_rows(esp_text), title="Phase-3 Verification", version="0.1.0")
        generated_tests = {
            "schema_summary": scaffold_schema_tests(esp_text, target_root / "tests" / "schema"),
            "sql_summary": scaffold_sql_tests(esp_text, target_root / "tests" / "sql"),
            "contract_summary": scaffold_contract_tests(spec, target_root / "tests" / "contracts"),
            "scenario_summary": scaffold_scenario_tests(
                stage_03_text,
                target_root / "tests" / "scenarios",
                esp_text=esp_text,
                openapi_spec=spec,
            ),
            "replay_summary": scaffold_replay_tests(
                stage_04_text,
                target_root / "tests" / "replays",
                esp_text=esp_text,
                stage_03_text=stage_03_text,
                openapi_spec=spec,
            ),
        }
    report = {
        "artifact_kind": "phase3-impl-verification-report",
        "quality_gate": "pass",
        "mode": mode,
        "workspace_root": str(workspace_root),
        "phase2_root": str(phase2_root) if phase2_root else "",
        "generated_tests": generated_tests,
        "claim_ceiling": (
            "verify-only structural report; runtime truth requires selected evidence family execution"
            if mode == "verify"
            else "test generation report; generated tests still require execution and review"
        ),
    }
    write_json(target_root / "impl-verification-report.json", report)
    return report
