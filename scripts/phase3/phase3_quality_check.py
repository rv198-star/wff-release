#!/usr/bin/env python3
"""
Foundation structural quality gate for Phase-3 S01/S02 outputs.
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

from phase3.phase3_artifact_quality import analyze_openapi_contract_quality, analyze_test_assertion_quality
from phase3.contract_tools import (
    parse_api_endpoint_rows,
    parse_implementation_start_order_rows,
    parse_replay_rows,
    parse_schema_tables,
    parse_scenario_rows,
    parse_work_package_rows,
)


def count_contract_tests(root: Path) -> int:
    return len(list(root.glob("*.contract.test.ts")))


def count_scenario_tests(root: Path) -> int:
    return len(list(root.glob("*.scenario.test.ts")))


def count_replay_tests(root: Path) -> int:
    return len(list(root.glob("*.replay.test.ts")))


def count_schema_tests(root: Path) -> int:
    return len(list(root.glob("*.schema.test.ts")))


def count_execution_packets(root: Path) -> int:
    return len(list(root.glob("*/execution-packet.json")))


def count_worker_input_packets(root: Path) -> int:
    return len(list(root.glob("wave-*/**/*-worker-input-packet.json")))


def count_generated_type_inputs(path: Path) -> int:
    document = path.read_text(encoding="utf-8")
    return len(re.findall(r"export interface [A-Za-z0-9_]+Input\b", document))


def count_api_client_methods(path: Path) -> int:
    document = path.read_text(encoding="utf-8")
    return len(re.findall(r"async [a-z][A-Za-z0-9_]*\(", document))


def count_migration_tables(path: Path) -> int:
    sql = path.read_text(encoding="utf-8")
    return len(re.findall(r"CREATE TABLE IF NOT EXISTS", sql))


def count_openapi_operations(path: Path | None) -> int:
    spec = load_json_if_exists(path)
    if not spec:
        return 0
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return 0
    operations = 0
    for methods in paths.values():
        if not isinstance(methods, dict):
            continue
        for method in methods.keys():
            if str(method).lower() in {"get", "post", "put", "patch", "delete"}:
                operations += 1
    return operations


def load_json_if_exists(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def package_has_scripts(path: Path | None, required_scripts: set[str]) -> bool:
    if path is None or not path.exists():
        return False
    payload = load_json_if_exists(path)
    if not payload:
        return False
    scripts = payload.get("scripts", {})
    if not isinstance(scripts, dict):
        return False
    return all(str(scripts.get(script, "")).strip() for script in required_scripts)


def file_contains_all(path: Path | None, required_tokens: tuple[str, ...]) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return all(token in document for token in required_tokens)



def dockerfile_has_runtime_start_semantics(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return "EXPOSE 3000" in document and ("CMD [" in document or "ENTRYPOINT [" in document)


def compose_has_runtime_service(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return all(token in document for token in ("healthcheck:", "postgres:", "redis:")) and any(
        token in document for token in ("command:", "entrypoint:")
    )

def compiled_binding_operation_count(implementation_bindings_path: Path | None) -> int:
    payload = load_json_if_exists(implementation_bindings_path)
    if not payload:
        return 0
    raw_rows = payload.get("compiled_bindings", [])
    if not isinstance(raw_rows, list):
        return 0
    valid_http_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
    operations = {
        (str(row.get("http_method") or "").strip().upper(), str(row.get("api_endpoint") or "").strip())
        for row in raw_rows
        if isinstance(row, dict)
        and str(row.get("http_method") or "").strip().upper() in valid_http_methods
        and str(row.get("api_endpoint") or "").strip().startswith("/")
    }
    return len(operations)


def payload_typing_summary(implementation_bindings_path: Path | None) -> tuple[bool, int]:
    if implementation_bindings_path is None or not implementation_bindings_path.exists():
        return True, 0
    bindings = load_json_if_exists(implementation_bindings_path) or {}
    workspace_root = implementation_bindings_path.parent
    unknown_targets: set[str] = set()
    for row in bindings.get("rows", []):
        if not isinstance(row, dict):
            continue
        for target in row.get("implementation_targets", []):
            normalized = str(target).strip()
            if not normalized:
                continue
            if not normalized.startswith("apps/api/src/"):
                continue
            path = workspace_root / normalized
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if re.search(r"\bpayload\s*:\s*unknown\b", text):
                unknown_targets.add(normalized)
    return len(unknown_targets) == 0, len(unknown_targets)


def analyze_phase3_bootstrap(
    *,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    openapi_path: Path,
    migration_path: Path,
    shared_types_path: Path,
    api_client_path: Path,
    stack_decision_path: Path | None = None,
    schema_tests_dir: Path | None = None,
    trace_registry_path: Path | None = None,
    implementation_bindings_path: Path | None = None,
    work_package_packets_dir: Path | None = None,
    work_package_wave_plan_path: Path | None = None,
    execution_loop_plan_path: Path | None = None,
    worker_input_packets_dir: Path | None = None,
    execution_runtime_state_path: Path | None = None,
    dispatch_manifest_path: Path | None = None,
    worker_run_report_path: Path | None = None,
    runtime_cycle_summary_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
    coverage_plan_path: Path | None = None,
    ci_workflow_path: Path | None = None,
    docker_compose_dev_path: Path | None = None,
    docker_compose_prod_path: Path | None = None,
    dockerfile_path: Path | None = None,
    env_example_path: Path | None = None,
    runtime_entrypoint_path: Path | None = None,
    root_package_json_path: Path | None = None,
    api_package_json_path: Path | None = None,
    toolchain_bootstrap_report_path: Path | None = None,
    require_frontend_contract: bool = False,
    contracts_dir: Path,
    scenarios_dir: Path,
    replays_dir: Path,
    test_trace_matrix_path: Path,
    test_obligation_audit_path: Path | None = None,
    test_richness_review_path: Path | None = None,
) -> dict[str, object]:
    endpoint_count = count_openapi_operations(openapi_path) or len(parse_api_endpoint_rows(esp_text))
    table_count = len(parse_schema_tables(esp_text))
    scenario_count = len(parse_scenario_rows(stage_03_text))
    replay_count = len(parse_replay_rows(stage_04_text))

    failures: list[str] = []
    warnings: list[str] = []

    if not openapi_path.exists():
        failures.append("openapi_missing")
    if not migration_path.exists():
        failures.append("migration_missing")
    if not shared_types_path.exists():
        failures.append("shared_types_missing")
    if not api_client_path.exists():
        failures.append("api_client_missing")
    if stack_decision_path is not None and not stack_decision_path.exists():
        failures.append("stack_decision_missing")
    if trace_registry_path is not None and not trace_registry_path.exists():
        failures.append("trace_registry_missing")
    if implementation_bindings_path is not None and not implementation_bindings_path.exists():
        failures.append("implementation_bindings_missing")
    if work_package_packets_dir is not None:
        if not work_package_packets_dir.exists():
            failures.append("work_package_packets_missing")
            execution_packet_count = 0
        else:
            execution_packet_count = count_execution_packets(work_package_packets_dir)
            try:
                expected_work_package_count = len(parse_work_package_rows(esp_text))
            except ValueError:
                try:
                    expected_work_package_count = len(parse_implementation_start_order_rows(esp_text))
                except ValueError:
                    expected_work_package_count = 0
            if expected_work_package_count and execution_packet_count < expected_work_package_count:
                failures.append("work_package_packet_count_below_expected_count")
    else:
        execution_packet_count = 0
    if work_package_wave_plan_path is not None:
        if not work_package_wave_plan_path.exists():
            failures.append("work_package_wave_plan_missing")
            wave_plan_status = "missing"
            wave_count = 0
        else:
            wave_plan = json.loads(work_package_wave_plan_path.read_text(encoding="utf-8"))
            wave_plan_status = str(wave_plan.get("overall_status", "")).strip() or "unknown"
            wave_count = int(wave_plan.get("summary", {}).get("wave_count", 0) or 0)
            if wave_plan_status != "valid":
                failures.append("work_package_wave_plan_invalid")
    else:
        wave_plan_status = "not-requested"
        wave_count = 0
    if execution_loop_plan_path is not None:
        if not execution_loop_plan_path.exists():
            failures.append("execution_loop_plan_missing")
            execution_loop_status = "missing"
        else:
            execution_loop = json.loads(execution_loop_plan_path.read_text(encoding="utf-8"))
            execution_loop_status = str(execution_loop.get("overall_status", "")).strip() or "unknown"
            if execution_loop_status != "valid":
                failures.append("execution_loop_plan_invalid")
    else:
        execution_loop_status = "not-requested"
    if worker_input_packets_dir is not None:
        if not worker_input_packets_dir.exists():
            failures.append("worker_input_packets_missing")
            worker_input_packet_count = 0
        else:
            worker_input_packet_count = count_worker_input_packets(worker_input_packets_dir)
            if worker_input_packet_count == 0:
                failures.append("worker_input_packet_count_zero")
    else:
        worker_input_packet_count = 0
    if execution_runtime_state_path is not None and not execution_runtime_state_path.exists():
        failures.append("execution_runtime_state_missing")
    if dispatch_manifest_path is not None and not dispatch_manifest_path.exists():
        failures.append("dispatch_manifest_missing")
    if worker_run_report_path is not None and not worker_run_report_path.exists():
        failures.append("worker_run_report_missing")
    if runtime_cycle_summary_path is not None and not runtime_cycle_summary_path.exists():
        failures.append("runtime_cycle_summary_missing")
    if runtime_environment_ledger_path is not None and not runtime_environment_ledger_path.exists():
        failures.append("runtime_environment_ledger_missing")
    if coverage_plan_path is not None and not coverage_plan_path.exists():
        failures.append("coverage_plan_missing")
    if ci_workflow_path is not None and not ci_workflow_path.exists():
        failures.append("ci_workflow_missing")
    if docker_compose_dev_path is not None and not docker_compose_dev_path.exists():
        failures.append("docker_compose_dev_missing")
    if docker_compose_prod_path is not None and not docker_compose_prod_path.exists():
        failures.append("docker_compose_prod_missing")
    if dockerfile_path is not None and not dockerfile_path.exists():
        failures.append("dockerfile_missing")
    if env_example_path is not None and not env_example_path.exists():
        failures.append("env_example_missing")
    if runtime_entrypoint_path is not None and not runtime_entrypoint_path.exists():
        failures.append("runtime_entrypoint_missing")
    if root_package_json_path is not None and not root_package_json_path.exists():
        failures.append("root_package_json_missing")
    if api_package_json_path is not None and not api_package_json_path.exists():
        failures.append("api_package_json_missing")

    runtime_baseline_scripts_present = package_has_scripts(root_package_json_path, {"start", "migrate", "build"})
    api_runtime_scripts_present = package_has_scripts(api_package_json_path, {"start", "migrate", "build"})
    env_contract_present = file_contains_all(
        env_example_path,
        ("DATABASE_URL=", "REDIS_URL=", "OIDC_CLIENT_SECRET=", "PORT=", "HOST="),
    )
    runtime_entrypoint_present = file_contains_all(
        runtime_entrypoint_path,
        ("/healthz", "/readyz", "createServer", "checkDatabaseReadiness"),
    )
    dockerfile_runtime_present = dockerfile_has_runtime_start_semantics(dockerfile_path)
    compose_prod_runtime_present = compose_has_runtime_service(docker_compose_prod_path)
    if root_package_json_path is not None and not runtime_baseline_scripts_present:
        failures.append("root_runtime_scripts_missing")
    if api_package_json_path is not None and not api_runtime_scripts_present:
        failures.append("api_runtime_scripts_missing")
    if env_example_path is not None and not env_contract_present:
        failures.append("env_contract_missing_runtime_fields")
    if runtime_entrypoint_path is not None and not runtime_entrypoint_present:
        failures.append("runtime_entrypoint_missing_health_or_db_probe")
    if dockerfile_path is not None and not dockerfile_runtime_present:
        failures.append("dockerfile_missing_runtime_start_semantics")
    if docker_compose_prod_path is not None and not compose_prod_runtime_present:
        failures.append("docker_compose_prod_missing_runtime_service")
    if toolchain_bootstrap_report_path is not None and not toolchain_bootstrap_report_path.exists():
        warnings.append("toolchain_bootstrap_report_missing")
        toolchain_bootstrap_status = "missing"
        toolchain_bootstrap_status_basis = "missing-report"
        toolchain_bootstrap_raw_status = "missing"
    elif toolchain_bootstrap_report_path is not None:
        toolchain_bootstrap_report = load_json_if_exists(toolchain_bootstrap_report_path) or {}
        toolchain_bootstrap_status = str(toolchain_bootstrap_report.get("overall_status", "unknown")).strip() or "unknown"
        toolchain_bootstrap_raw_status = toolchain_bootstrap_status
        toolchain_bootstrap_status_basis = (
            str(toolchain_bootstrap_report.get("status_semantics", "")).strip()
            or "initial-bootstrap-snapshot-before-runtime-validation"
        )
        if toolchain_bootstrap_status == "pending-install":
            warnings.append("toolchain_bootstrap_pending_install")
        elif toolchain_bootstrap_status != "ready":
            warnings.append("toolchain_bootstrap_not_ready")
    else:
        toolchain_bootstrap_status = "not-requested"
        toolchain_bootstrap_status_basis = "not-requested"
        toolchain_bootstrap_raw_status = "not-requested"
    if count_contract_tests(contracts_dir) < endpoint_count:
        failures.append("contract_test_count_below_endpoint_count")
    if count_scenario_tests(scenarios_dir) < scenario_count:
        failures.append("scenario_test_count_below_scenario_count")
    if count_replay_tests(replays_dir) < replay_count:
        failures.append("replay_test_count_below_replay_count")
    openapi_contract_report = analyze_openapi_contract_quality(load_json_if_exists(openapi_path) or {})
    openapi_contract_summary = dict(openapi_contract_report.get("summary", {}))
    if openapi_contract_report.get("overall_quality_gate") != "pass":
        failures.append("openapi_contract_quality_failed")
    tests_root = scenarios_dir.parent.parent if scenarios_dir.name == "scenarios" and scenarios_dir.parent.name == "tests" else scenarios_dir.parent
    artifact_assertion_report = analyze_test_assertion_quality(tests_root)
    artifact_assertion_summary = dict(artifact_assertion_report.get("summary", {}))
    if artifact_assertion_summary.get("blocker_count", 0) > 0:
        warnings.append("artifact_assertion_quality_review_bound")
    if migration_path.exists() and count_migration_tables(migration_path) < table_count:
        failures.append("migration_table_count_below_schema_count")
    if schema_tests_dir is not None:
        if not schema_tests_dir.exists():
            failures.append("schema_tests_missing")
            schema_test_count = 0
        else:
            schema_test_count = count_schema_tests(schema_tests_dir)
            if schema_test_count < table_count:
                failures.append("schema_test_count_below_schema_count")
    else:
        schema_test_count = 0
    if shared_types_path.exists():
        type_inputs = count_generated_type_inputs(shared_types_path)
        if type_inputs < endpoint_count:
            failures.append("shared_types_input_count_below_endpoint_count")
        if "ApiErrorEnvelope" not in shared_types_path.read_text(encoding="utf-8"):
            failures.append("shared_types_error_envelope_missing")
    else:
        type_inputs = 0
    if api_client_path.exists():
        client_methods = count_api_client_methods(api_client_path)
        if client_methods < endpoint_count:
            failures.append("api_client_method_count_below_endpoint_count")
        if "createApiClient" not in api_client_path.read_text(encoding="utf-8"):
            failures.append("api_client_factory_missing")
    else:
        client_methods = 0
    compiled_binding_count = compiled_binding_operation_count(implementation_bindings_path)
    compiled_binding_authority_enforced = require_frontend_contract
    openapi_has_derived_authority = file_contains_all(openapi_path, ('"x-derived-artifact-kind"', '"x-derived-authority"'))
    shared_types_has_derived_authority = file_contains_all(shared_types_path, ("Derived artifact authority:",))
    api_client_has_derived_authority = file_contains_all(api_client_path, ("Derived artifact authority:",))
    if implementation_bindings_path is not None and implementation_bindings_path.exists():
        if compiled_binding_count <= 0 and require_frontend_contract:
            failures.append("compiled_bindings_missing")
        elif not require_frontend_contract:
            warnings.append("compiled_bindings_not_required_for_backend_first_mainline")
        if compiled_binding_authority_enforced and not openapi_has_derived_authority:
            failures.append("openapi_derived_authority_missing")
        if compiled_binding_authority_enforced and not shared_types_has_derived_authority:
            failures.append("shared_types_derived_authority_missing")
        if compiled_binding_authority_enforced and not api_client_has_derived_authority:
            failures.append("api_client_derived_authority_missing")
        if compiled_binding_authority_enforced and compiled_binding_count > 0 and endpoint_count != compiled_binding_count:
            failures.append("openapi_operation_count_mismatches_compiled_bindings")
        if compiled_binding_authority_enforced and openapi_has_derived_authority and openapi_path.exists():
            openapi_payload = load_json_if_exists(openapi_path) or {}
            if str(openapi_payload.get("x-derived-authority", "")).strip() != "compiled-bindings":
                failures.append("openapi_derived_authority_not_compiled_bindings")
        if compiled_binding_authority_enforced and shared_types_has_derived_authority and shared_types_path.exists():
            if "Derived artifact authority: compiled-bindings" not in shared_types_path.read_text(encoding="utf-8"):
                failures.append("shared_types_derived_authority_not_compiled_bindings")
        if compiled_binding_authority_enforced and api_client_has_derived_authority and api_client_path.exists():
            if "Derived artifact authority: compiled-bindings" not in api_client_path.read_text(encoding="utf-8"):
                failures.append("api_client_derived_authority_not_compiled_bindings")
    all_payload_typed, unknown_payload_target_count = payload_typing_summary(implementation_bindings_path)
    if not all_payload_typed:
        warnings.append("implementation_payloads_still_generic")
    if not test_trace_matrix_path.exists():
        failures.append("test_trace_matrix_missing")
        matrix_summary = {"unmatched_contract_trace_ids": ["missing-matrix"]}
    else:
        matrix = json.loads(test_trace_matrix_path.read_text(encoding="utf-8"))
        matrix_summary = matrix.get("summary", {})
        unmatched = list(matrix_summary.get("unmatched_contract_trace_ids", []))
        if unmatched:
            warnings.append("unmatched_contract_trace_ids_present")
    test_obligation_quality: dict[str, object] = {
        "overall_quality_gate": "not-provided",
        "missing_count": 0,
        "weak_count": 0,
        "failure_count": 0,
        "warning_count": 0,
    }
    if test_obligation_audit_path is not None:
        if not test_obligation_audit_path.exists():
            failures.append("test_obligation_audit_missing")
            test_obligation_quality["overall_quality_gate"] = "missing"
        else:
            obligation_audit = load_json_if_exists(test_obligation_audit_path) or {}
            obligation_summary = obligation_audit.get("summary", {})
            obligation_summary = obligation_summary if isinstance(obligation_summary, dict) else {}
            test_obligation_quality = {
                "overall_quality_gate": str(obligation_audit.get("overall_quality_gate", "unknown")),
                "missing_count": int(obligation_summary.get("missing_count", 0) or 0),
                "weak_count": int(obligation_summary.get("weak_count", 0) or 0),
                "failure_count": int(obligation_summary.get("failure_count", 0) or 0),
                "warning_count": int(obligation_summary.get("warning_count", 0) or 0),
            }
            if str(obligation_audit.get("overall_quality_gate", "")).strip() != "pass":
                failures.append("test_obligation_quality_failed")

    test_richness_review: dict[str, object] = {
        "status": "not-provided",
        "agentic_review_status": "not-provided",
        "evidence_claim_ceiling": "not-provided",
        "risk_signal_count": 0,
    }
    richness_review_bound = False
    if test_richness_review_path is not None:
        if not test_richness_review_path.exists():
            failures.append("test_richness_review_missing")
            test_richness_review["status"] = "missing"
        else:
            richness_payload = load_json_if_exists(test_richness_review_path) or {}
            agentic = richness_payload.get("agentic_review", {})
            agentic = agentic if isinstance(agentic, dict) else {}
            evidence = richness_payload.get("evidence_bridge", {})
            evidence = evidence if isinstance(evidence, dict) else {}
            workflow = richness_payload.get("workflow_preflight", {})
            workflow = workflow if isinstance(workflow, dict) else {}
            risk_signals = workflow.get("risk_signals", [])
            risk_signal_count = len(risk_signals) if isinstance(risk_signals, list) else 0
            agentic_status = str(agentic.get("status", "required")).strip() or "required"
            claim_ceiling = str(evidence.get("claim_ceiling", "review-bound")).strip() or "review-bound"
            test_richness_review = {
                "status": "present",
                "agentic_review_status": agentic_status,
                "evidence_claim_ceiling": claim_ceiling,
                "risk_signal_count": risk_signal_count,
            }
            if agentic_status != "pass" or claim_ceiling == "review-bound":
                richness_review_bound = True
                warnings.append("test_richness_agentic_review_required")

    gate = "pass" if not failures else "fail"
    state = "review-bound" if gate == "pass" and richness_review_bound else ("foundation-ready" if gate == "pass" else "blocked")
    return {
        "overall_quality_gate": gate,
        "recommended_formal_state": state,
        "checks": {
            "endpoint_count": endpoint_count,
            "schema_table_count": table_count,
            "scenario_count": scenario_count,
            "replay_count": replay_count,
            "contract_test_count": count_contract_tests(contracts_dir),
            "scenario_test_count": count_scenario_tests(scenarios_dir),
            "replay_test_count": count_replay_tests(replays_dir),
            "artifact_assertion_quality": artifact_assertion_summary,
            "openapi_contract_quality": openapi_contract_summary,
            "schema_test_count": schema_test_count,
            "migration_table_count": count_migration_tables(migration_path) if migration_path.exists() else 0,
            "shared_types_input_count": type_inputs,
            "api_client_method_count": client_methods,
            "compiled_binding_operation_count": compiled_binding_count,
            "frontend_contract_required": require_frontend_contract,
            "compiled_binding_authority_enforced": compiled_binding_authority_enforced,
            "openapi_has_derived_authority": openapi_has_derived_authority,
            "shared_types_has_derived_authority": shared_types_has_derived_authority,
            "api_client_has_derived_authority": api_client_has_derived_authority,
            "stack_decision_present": bool(stack_decision_path and stack_decision_path.exists()),
            "trace_registry_present": bool(trace_registry_path and trace_registry_path.exists()),
            "implementation_bindings_present": bool(implementation_bindings_path and implementation_bindings_path.exists()),
            "work_package_packet_count": execution_packet_count,
            "work_package_packets_present": bool(work_package_packets_dir and work_package_packets_dir.exists()),
            "work_package_wave_plan_present": bool(work_package_wave_plan_path and work_package_wave_plan_path.exists()),
            "work_package_wave_plan_status": wave_plan_status,
            "work_package_wave_count": wave_count,
            "execution_loop_plan_present": bool(execution_loop_plan_path and execution_loop_plan_path.exists()),
            "execution_loop_plan_status": execution_loop_status,
            "worker_input_packets_present": bool(worker_input_packets_dir and worker_input_packets_dir.exists()),
            "worker_input_packet_count": worker_input_packet_count,
            "execution_runtime_state_present": bool(execution_runtime_state_path and execution_runtime_state_path.exists()),
            "dispatch_manifest_present": bool(dispatch_manifest_path and dispatch_manifest_path.exists()),
            "worker_run_report_present": bool(worker_run_report_path and worker_run_report_path.exists()),
            "runtime_cycle_summary_present": bool(runtime_cycle_summary_path and runtime_cycle_summary_path.exists()),
            "runtime_environment_ledger_present": bool(
                runtime_environment_ledger_path and runtime_environment_ledger_path.exists()
            ),
            "coverage_plan_present": bool(coverage_plan_path and coverage_plan_path.exists()),
            "ci_workflow_present": bool(ci_workflow_path and ci_workflow_path.exists()),
            "docker_compose_dev_present": bool(docker_compose_dev_path and docker_compose_dev_path.exists()),
            "docker_compose_prod_present": bool(docker_compose_prod_path and docker_compose_prod_path.exists()),
            "dockerfile_present": bool(dockerfile_path and dockerfile_path.exists()),
            "env_example_present": bool(env_example_path and env_example_path.exists()),
            "runtime_entrypoint_present": bool(runtime_entrypoint_path and runtime_entrypoint_path.exists()),
            "root_runtime_scripts_present": runtime_baseline_scripts_present,
            "api_runtime_scripts_present": api_runtime_scripts_present,
            "env_contract_present": env_contract_present,
            "runtime_entrypoint_health_ready_present": runtime_entrypoint_present,
            "dockerfile_runtime_present": dockerfile_runtime_present,
            "compose_prod_runtime_present": compose_prod_runtime_present,
            "toolchain_bootstrap_report_present": bool(
                toolchain_bootstrap_report_path and toolchain_bootstrap_report_path.exists()
            ),
            "toolchain_bootstrap_status": toolchain_bootstrap_status,
            "toolchain_bootstrap_raw_status": toolchain_bootstrap_raw_status,
            "toolchain_bootstrap_status_basis": toolchain_bootstrap_status_basis,
            "all_payload_typed": all_payload_typed,
            "unknown_payload_target_count": unknown_payload_target_count,
            "trace_matrix_summary": matrix_summary,
            "test_obligation_quality": test_obligation_quality,
            "test_richness_review": test_richness_review,
        },
        "failures": failures,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase-3 foundation quality gate")
    parser.add_argument("--esp", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--openapi", required=True)
    parser.add_argument("--migration", required=True)
    parser.add_argument("--shared-types", required=True)
    parser.add_argument("--api-client", required=True)
    parser.add_argument("--stack-decision")
    parser.add_argument("--schema-tests-dir")
    parser.add_argument("--trace-registry")
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--work-package-packets-dir")
    parser.add_argument("--work-package-wave-plan")
    parser.add_argument("--execution-loop-plan")
    parser.add_argument("--worker-input-packets-dir")
    parser.add_argument("--execution-runtime-state")
    parser.add_argument("--dispatch-manifest")
    parser.add_argument("--worker-run-report")
    parser.add_argument("--runtime-cycle-summary")
    parser.add_argument("--runtime-environment-ledger")
    parser.add_argument("--coverage-plan")
    parser.add_argument("--ci-workflow")
    parser.add_argument("--docker-compose-dev")
    parser.add_argument("--docker-compose-prod")
    parser.add_argument("--dockerfile")
    parser.add_argument("--env-example")
    parser.add_argument("--runtime-entrypoint")
    parser.add_argument("--root-package-json")
    parser.add_argument("--api-package-json")
    parser.add_argument("--toolchain-bootstrap-report")
    parser.add_argument("--test-obligation-audit")
    parser.add_argument("--test-richness-review")
    parser.add_argument(
        "--require-frontend-contract",
        action="store_true",
        help="treat compiled frontend contract authority as a mainline hard requirement instead of optional lane evidence",
    )
    parser.add_argument("--contracts-dir", required=True)
    parser.add_argument("--scenarios-dir", required=True)
    parser.add_argument("--replays-dir", required=True)
    parser.add_argument("--test-trace-matrix", required=True)
    parser.add_argument("--output", help="Optional output path for the JSON report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = analyze_phase3_bootstrap(
        esp_text=Path(args.esp).resolve().read_text(encoding="utf-8"),
        stage_03_text=Path(args.stage_03).resolve().read_text(encoding="utf-8"),
        stage_04_text=Path(args.stage_04).resolve().read_text(encoding="utf-8"),
        openapi_path=Path(args.openapi).resolve(),
        migration_path=Path(args.migration).resolve(),
        shared_types_path=Path(args.shared_types).resolve(),
        api_client_path=Path(args.api_client).resolve(),
        stack_decision_path=Path(args.stack_decision).resolve() if args.stack_decision else None,
        schema_tests_dir=Path(args.schema_tests_dir).resolve() if args.schema_tests_dir else None,
        trace_registry_path=Path(args.trace_registry).resolve() if args.trace_registry else None,
        implementation_bindings_path=Path(args.implementation_bindings).resolve() if args.implementation_bindings else None,
        work_package_packets_dir=Path(args.work_package_packets_dir).resolve() if args.work_package_packets_dir else None,
        work_package_wave_plan_path=Path(args.work_package_wave_plan).resolve() if args.work_package_wave_plan else None,
        execution_loop_plan_path=Path(args.execution_loop_plan).resolve() if args.execution_loop_plan else None,
        worker_input_packets_dir=Path(args.worker_input_packets_dir).resolve() if args.worker_input_packets_dir else None,
        execution_runtime_state_path=Path(args.execution_runtime_state).resolve() if args.execution_runtime_state else None,
        dispatch_manifest_path=Path(args.dispatch_manifest).resolve() if args.dispatch_manifest else None,
        worker_run_report_path=Path(args.worker_run_report).resolve() if args.worker_run_report else None,
        runtime_cycle_summary_path=Path(args.runtime_cycle_summary).resolve() if args.runtime_cycle_summary else None,
        runtime_environment_ledger_path=Path(args.runtime_environment_ledger).resolve()
        if args.runtime_environment_ledger
        else None,
        coverage_plan_path=Path(args.coverage_plan).resolve() if args.coverage_plan else None,
        ci_workflow_path=Path(args.ci_workflow).resolve() if args.ci_workflow else None,
        docker_compose_dev_path=Path(args.docker_compose_dev).resolve() if args.docker_compose_dev else None,
        docker_compose_prod_path=Path(args.docker_compose_prod).resolve() if args.docker_compose_prod else None,
        dockerfile_path=Path(args.dockerfile).resolve() if args.dockerfile else None,
        env_example_path=Path(args.env_example).resolve() if args.env_example else None,
        runtime_entrypoint_path=Path(args.runtime_entrypoint).resolve() if args.runtime_entrypoint else None,
        root_package_json_path=Path(args.root_package_json).resolve() if args.root_package_json else None,
        api_package_json_path=Path(args.api_package_json).resolve() if args.api_package_json else None,
        toolchain_bootstrap_report_path=Path(args.toolchain_bootstrap_report).resolve()
        if args.toolchain_bootstrap_report
        else None,
        require_frontend_contract=args.require_frontend_contract,
        contracts_dir=Path(args.contracts_dir).resolve(),
        scenarios_dir=Path(args.scenarios_dir).resolve(),
        replays_dir=Path(args.replays_dir).resolve(),
        test_trace_matrix_path=Path(args.test_trace_matrix).resolve(),
        test_obligation_audit_path=Path(args.test_obligation_audit).resolve() if args.test_obligation_audit else None,
        test_richness_review_path=Path(args.test_richness_review).resolve() if args.test_richness_review else None,
    )
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["overall_quality_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
