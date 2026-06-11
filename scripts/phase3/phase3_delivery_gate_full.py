#!/usr/bin/env python3
"""
Resolve the formal completion state of a Phase-3 implementation run.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from phase3.delivery_asset_checks import (
    compose_has_startable_runtime,
    delivery_asset_has_hardcoded_secrets,
    dir_has_entries,
    dockerfile_has_healthcheck,
    dockerfile_has_multistage_build,
    dockerfile_has_non_root_user,
    dockerfile_has_runtime_entrypoint,
    path_exists,
)
from phase3.delivery_gate_cli import (
    build_acceptance_report,
    build_execution_report,
    build_parser,
    build_phase3_delivery_gate_context,
    build_phase3_mode_handlers as build_phase3_mode_handlers_with_delivery,
    emit_phase3_delivery_gate_summary,
    emit_phase3_mode_result,
    load_text,
    parse_phase3_delivery_gate_args,
    resolve_optional_path,
    run_api_docs_mode,
    run_code_review_mode,
    run_coverage_collection_mode,
    run_delivery_gate_mode as run_delivery_gate_cli_mode,
    run_delivery_handoff_mode,
    run_phase3_delivery_gate_cli,
    run_productness_gate_mode,
    run_security_audit_mode,
    validate_phase3_delivery_gate_args,
    write_phase3_cli_output,
)
from phase3.delivery_gate_context import Phase3DeliveryGateContext
from phase3.delivery_mode_authority import (
    CLI_MODES,
    decorate_phase3_mode_payload,
    phase3_mode_authority,
    phase3_mode_authority_map,
)
from phase3.claim_ceiling_resolver import (
    apply_phase3_claim_ceiling,
    build_phase3_claim_ceiling_report,
)
from phase3.trace_gap_checks import (
    first_int,
    trace_registry_blocking_gap_count,
    trace_registry_quality_report,
)


def optional_phase3_gate_sidecar(module_name: str):
    try:
        return importlib.import_module(f"phase3.{module_name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"phase3.{module_name}":
            return None
        raise


def _report_status_green(report: dict[str, Any] | None) -> bool:
    if not isinstance(report, dict) or not report:
        return False
    for key in ("overall_quality_gate", "quality_gate", "overall_verdict", "verdict", "status", "overall_status"):
        value = str(report.get(key, "")).strip().lower()
        if value in {"pass", "passed", "ok", "ready", "valid", "success"}:
            return True
        if value in {"fail", "failed", "blocked", "return-remediate", "return_remediate"}:
            return False
    return False


def report_is_pass(report: dict[str, Any] | None) -> bool:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.report_is_pass(report)
    return _report_status_green(report)


def bootstrap_report_is_green(report: dict[str, Any] | None) -> bool:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.bootstrap_report_is_green(report)
    checks = report.get("checks", {}) if isinstance(report, dict) else {}
    if isinstance(checks, dict):
        toolchain_status = str(
            checks.get("toolchain_bootstrap_status") or checks.get("toolchain_bootstrap_raw_status") or ""
        ).strip().lower()
        if toolchain_status in {"ready", "toolchain-ready", "pass"}:
            return True
        if toolchain_status in {"fail", "failed", "blocked", "not-ready", "error"}:
            return False
    return _report_status_green(report)


def bootstrap_toolchain_status_fields(report: dict[str, Any] | None) -> tuple[str, str]:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.bootstrap_toolchain_status_fields(report)
    checks = report.get("checks", {}) if isinstance(report, dict) else {}
    if isinstance(checks, dict):
        status = str(checks.get("toolchain_bootstrap_status") or checks.get("toolchain_bootstrap_raw_status") or "unknown")
        basis = str(checks.get("toolchain_bootstrap_status_basis") or "backend_truth_sidecar_unavailable")
        return status, basis
    return "unknown", "backend_truth_sidecar_unavailable"


def ledger_step_is_pass(report: dict[str, Any] | None, step_name: str) -> bool:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.ledger_step_is_pass(report, step_name)
    return False


def ledger_step_present(report: dict[str, Any] | None, step_name: str) -> bool:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.ledger_step_present(report, step_name)
    return False


def latest_packet_rows(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.latest_packet_rows(report)
    return []


def lane_packet_rows(report: dict[str, Any] | None, lane: str) -> list[dict[str, Any]]:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.lane_packet_rows(report, lane)
    return []


def lane_step_is_pass(report: dict[str, Any] | None, lane: str, step_name: str) -> bool:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.lane_step_is_pass(report, lane, step_name)
    return False


def lane_step_present(report: dict[str, Any] | None, lane: str, step_name: str) -> bool:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.lane_step_present(report, lane, step_name)
    return False


def backend_layer_gate_rollup(report: dict[str, Any] | None) -> dict[str, Any]:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.backend_layer_gate_rollup(report)
    return {
        "present": False,
        "all_green": False,
        "rows": [],
        "blocking_layers": [],
        "blocked_work_packages": [],
        "reason": "backend_truth_sidecar_not_packaged",
    }


def backend_truth_rollup(report: dict[str, Any] | None) -> dict[str, Any]:
    module = optional_phase3_gate_sidecar("backend_truth_checks")
    if module is not None:
        return module.backend_truth_rollup(report)
    return {
        "sidecar_unavailable": True,
        "reason": "backend_truth_sidecar_not_packaged",
        "service_boundary_signal_present": False,
        "service_boundary_truth": False,
        "requires_persistence_truth": False,
        "sql_persistence_truth": False,
        "service_persistence_roundtrip_truth": False,
        "migration_execution": False,
        "public_contract_skeleton_required": False,
        "public_contract_skeleton_truth": True,
        "persistence_reentry_truth": True,
        "api_evidence_linkage_truth": True,
        "public_contract_risk_tiers": [],
        "state_isolation_values": [],
        "reentry_policy_values": [],
        "rerun_proof_values": [],
        "persistence_reentry_evidence_present": False,
    }


def ui_ia_contract_valid(path: Path | None) -> tuple[bool, dict[str, Any]]:
    module = optional_phase3_gate_sidecar("frontend_contract_checks")
    if module is not None:
        return module.ui_ia_contract_valid(path)
    return False, {"reason": "frontend_contract_checks_sidecar_not_packaged"}


def surface_contract_taxonomy_report(
    ui_ia_contract_path: Path | None,
    productness_gate_report: dict[str, Any] | None,
) -> dict[str, Any]:
    module = optional_phase3_gate_sidecar("frontend_contract_checks")
    if module is not None:
        return module.surface_contract_taxonomy_report(ui_ia_contract_path, productness_gate_report)
    return {
        "present": False,
        "source": "sidecar-unavailable",
        "gate_pass": False,
        "report_reused": False,
        "report_validation_reason": "frontend_contract_checks_sidecar_not_packaged",
        "checks": {},
        "metrics": {},
    }


def build_phase3_mainline_assessment(delivery_gate_report: dict[str, Any]) -> dict[str, Any]:
    module = optional_phase3_gate_sidecar("mainline_assessment")
    if module is not None:
        return module.build_phase3_mainline_assessment(delivery_gate_report=delivery_gate_report)
    phase_gate = str(delivery_gate_report.get("phase_completion_gate", "")).strip().lower()
    implementation_ready = bool(delivery_gate_report.get("implementation_ready"))
    failures = list(delivery_gate_report.get("failures", []) or [])
    warnings = list(delivery_gate_report.get("warnings", []) or [])
    verdict = "PASS" if phase_gate == "pass" else "RETURN-REMEDIATE"
    total_score = 80.0 if verdict == "PASS" else 50.0
    return {
        "phase": "P3",
        "verdict": verdict,
        "phase_verdict": verdict,
        "delivery_mode": delivery_gate_report.get("delivery_mode", "runtime-closure"),
        "recommended_formal_state": delivery_gate_report.get("recommended_formal_state", "implementation-in-progress"),
        "runtime_closure_state": "unknown",
        "artifact_quality_state": "unknown",
        "implementation_depth_state": "unknown",
        "frontend_scope_state": "unknown",
        "total_score": total_score,
        "phase_total_score": total_score,
        "blockers_count": len(failures),
        "warning_count": len(warnings),
        "failure_count": len(failures),
        "review_bound_items_count": 0,
        "phase_complete": verdict == "PASS",
        "implementation_complete": implementation_ready,
        "acceptance_rows": [],
        "blockers": failures,
        "warnings": warnings,
        "sidecar_unavailable": True,
        "reason": "mainline_assessment_sidecar_not_packaged",
    }


def write_phase3_mainline_assessment_artifacts(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
    case_name: str = "",
    version: str = "",
    output_locale: str = "zh-CN",
    human_review: dict[str, Any] | None = None,
) -> dict[str, str]:
    module = optional_phase3_gate_sidecar("mainline_assessment")
    if module is not None:
        return module.write_phase3_mainline_assessment_artifacts(
            output_dir=output_dir,
            assessment=assessment,
            case_name=case_name,
            version=version,
            output_locale=output_locale,
            human_review=human_review,
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = output_dir / "phase-mainline-scorecard.md"
    acceptance_matrix_path = output_dir / "phase-acceptance-matrix.md"
    verdict_path = output_dir / "phase-verdict.json"
    verdict = assessment.get("verdict", assessment.get("phase_verdict", "RETURN-REMEDIATE"))
    scorecard_path.write_text(
        "# Phase-3 Mainline Assessment\n\n"
        "- mode: `sidecar-unavailable`\n"
        f"- verdict: `{verdict}`\n",
        encoding="utf-8",
    )
    acceptance_matrix_path.write_text(
        "# Phase-3 Acceptance Matrix\n\n"
        "- assessment sidecar not packaged in this install profile\n",
        encoding="utf-8",
    )
    verdict_path.write_text(json.dumps(assessment, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "scorecard_path": str(scorecard_path),
        "acceptance_matrix_path": str(acceptance_matrix_path),
        "verdict_path": str(verdict_path),
        "agentic_repair_interrupt_path": "",
        "agentic_repair_interrupt_markdown_path": "",
        "agentic_repair_interrupt_required": "false",
        "agentic_repair_interrupt_packet_count": "0",
    }

def build_phase3_mainline_assessment_summary(
    *,
    assessment: dict[str, Any],
    artifact_paths: dict[str, str],
) -> dict[str, Any]:
    module = optional_phase3_gate_sidecar("mainline_assessment")
    if module is not None:
        return module.build_phase3_mainline_assessment_summary(assessment=assessment, artifact_paths=artifact_paths)
    return {
        "phase": "P3",
        "phase_verdict": assessment.get("phase_verdict", assessment.get("verdict", "RETURN-REMEDIATE")),
        "phase_total_score": assessment.get("phase_total_score", assessment.get("total_score", 0.0)),
        "blockers_count": assessment.get("blockers_count", 0),
        "warning_count": assessment.get("warning_count", 0),
        "failure_count": assessment.get("failure_count", 0),
        "review_bound_items_count": assessment.get("review_bound_items_count", 0),
        "phase_complete": assessment.get("phase_complete", False),
        "implementation_complete": assessment.get("implementation_complete", False),
        "phase_scorecard_path": artifact_paths.get("scorecard_path", ""),
        "phase_acceptance_matrix_path": artifact_paths.get("acceptance_matrix_path", ""),
        "phase_verdict_path": artifact_paths.get("verdict_path", ""),
        "agentic_repair_interrupt_path": "",
        "agentic_repair_interrupt_markdown_path": "",
        "agentic_repair_interrupt_required": False,
        "agentic_repair_interrupt_packet_count": 0,
        "sidecar_unavailable": True,
        "reason": "mainline_assessment_sidecar_not_packaged",
    }


def generate_phase3_api_docs(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return importlib.import_module("phase3.api_doc_generation").generate_phase3_api_docs(*args, **kwargs)


def analyze_phase3_coverage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return importlib.import_module("phase3.coverage_collection").analyze_phase3_coverage(*args, **kwargs)


def generate_phase3_delivery_handoff(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return importlib.import_module("phase3.delivery_handoff").generate_phase3_delivery_handoff(*args, **kwargs)


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def run_productness_gate(frontend_dir: Path | None, ui_ia_contract_path: Path | None) -> dict[str, Any]:
    return importlib.import_module("phase3.productness_gate").run_gate(frontend_dir, ui_ia_contract_path)


def classify_behavior_card_consistency(
    *,
    behavior_card_report: dict[str, Any] | None,
    test_mapping_report: dict[str, Any] | None,
    implementation_mapping_report: dict[str, Any] | None,
    high_risk: bool = True,
) -> dict[str, Any]:
    if not high_risk:
        return {"classification": "consistent", "missing_test_steps": [], "missing_implementation_steps": []}
    if not isinstance(behavior_card_report, dict) or not behavior_card_report:
        return {"classification": "p2_handoff_gap", "missing_test_steps": [], "missing_implementation_steps": []}
    if str(behavior_card_report.get("overall_quality_gate", "")).lower() not in {"pass", ""}:
        return {"classification": "p2_handoff_gap", "missing_test_steps": [], "missing_implementation_steps": []}
    card_steps = [str(item) for item in behavior_card_report.get("steps", []) if str(item).strip()]
    covered_steps = [str(item) for item in (test_mapping_report or {}).get("covered_steps", []) if str(item).strip()]
    implemented_steps = [str(item) for item in (implementation_mapping_report or {}).get("implemented_steps", []) if str(item).strip()]
    missing_test_steps = [step for step in card_steps if step not in covered_steps]
    missing_implementation_steps = [step for step in card_steps if step not in implemented_steps]
    if missing_test_steps:
        classification = "action_card_test_gap"
    elif missing_implementation_steps:
        classification = "action_card_implementation_gap"
    else:
        classification = "consistent"
    if set(covered_steps) - set(card_steps) or set(implemented_steps) - set(card_steps):
        classification = "trace_drift"
    return {
        "classification": classification,
        "missing_test_steps": missing_test_steps,
        "missing_implementation_steps": missing_implementation_steps,
    }


def analyze_phase3_delivery(
    *,
    bootstrap_report: dict[str, Any],
    build_report: dict[str, Any] | None = None,
    lint_report: dict[str, Any] | None = None,
    typecheck_report: dict[str, Any] | None = None,
    unit_test_report: dict[str, Any] | None = None,
    coverage_gate_report: dict[str, Any] | None = None,
    wp_gate_report: dict[str, Any] | None = None,
    verification_ledger_report: dict[str, Any] | None = None,
    openapi_diff_report: dict[str, Any] | None = None,
    code_review_metrics: dict[str, Any] | None = None,
    behavior_static_preflight_report: dict[str, Any] | None = None,
    security_audit_report: dict[str, Any] | None = None,
    openapi_final_path: Path | None = None,
    api_doc_dir: Path | None = None,
    deploy_runbook_path: Path | None = None,
    dockerfile_path: Path | None = None,
    compose_prod_path: Path | None = None,
    runtime_smoke_report: dict[str, Any] | None = None,
    runtime_smoke_report_path: Path | None = None,
    started_service_smoke_report: dict[str, Any] | None = None,
    started_service_smoke_report_path: Path | None = None,
    performance_baseline_path: Path | None = None,
    acceptance_report_path: Path | None = None,
    execution_report_path: Path | None = None,
    trace_registry_final_path: Path | None = None,
    ui_prototype_fallback_report_path: Path | None = None,
    ui_ia_contract_path: Path | None = None,
    productness_gate_report: dict[str, Any] | None = None,
    require_frontend_contract: bool = False,
    retained_proof_mode: bool = False,
    strict_runtime_closure: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    delivery_mode = "retained-proof" if retained_proof_mode else "runtime-closure"
    runtime_delivery_assets_required = not retained_proof_mode

    bootstrap_green = bootstrap_report_is_green(bootstrap_report)
    if not bootstrap_green:
        failures.append("bootstrap_gate_failed")
    bootstrap_checks = bootstrap_report.get("checks", {}) if isinstance(bootstrap_report, dict) else {}
    bootstrap_toolchain_status, bootstrap_toolchain_status_basis = bootstrap_toolchain_status_fields(bootstrap_report)
    if strict_runtime_closure and bootstrap_toolchain_status != "ready":
        bootstrap_green = False
        failures.append("strict_runtime_toolchain_not_ready")
    bootstrap_all_payload_typed = bool(bootstrap_checks.get("all_payload_typed", True))
    bootstrap_all_payload_typed_basis = str(bootstrap_checks.get("all_payload_typed_basis", "")).strip() or "bootstrap-report"

    runtime_smoke_present = path_exists(runtime_smoke_report_path) or runtime_smoke_report is not None
    runtime_smoke_green = report_is_pass(runtime_smoke_report) if runtime_smoke_report is not None else False
    started_service_smoke_present = path_exists(started_service_smoke_report_path) or started_service_smoke_report is not None
    started_service_smoke_green = report_is_pass(started_service_smoke_report) if started_service_smoke_report is not None else False

    runtime_wp_green = report_is_pass(wp_gate_report) if wp_gate_report is not None else False
    runtime_build_green = ledger_step_is_pass(verification_ledger_report, "build")
    runtime_lint_green = ledger_step_is_pass(verification_ledger_report, "lint")
    runtime_typecheck_green = ledger_step_is_pass(verification_ledger_report, "typecheck")
    runtime_unit_tests_green = ledger_step_is_pass(verification_ledger_report, "unit-tests")
    runtime_targeted_tests_green = ledger_step_is_pass(verification_ledger_report, "targeted-tests")
    implementation_signal_present = any(
        report is not None
        for report in (
            build_report,
            lint_report,
            typecheck_report,
            unit_test_report,
            coverage_gate_report,
            wp_gate_report,
            verification_ledger_report,
        )
    )
    has_packet_level_verification = bool(latest_packet_rows(verification_ledger_report))
    backend_packet_present = bool(lane_packet_rows(verification_ledger_report, "backend"))
    frontend_packet_present = bool(lane_packet_rows(verification_ledger_report, "frontend"))
    backend_layer_rollup = backend_layer_gate_rollup(wp_gate_report)
    backend_truth = backend_truth_rollup(verification_ledger_report)
    ui_fallback_report = load_json(ui_prototype_fallback_report_path)
    ui_fallback_mode = (
        str(ui_fallback_report.get("mode", "")).strip().lower()
        if isinstance(ui_fallback_report, dict)
        else ""
    )
    ui_fallback_generated = ui_fallback_mode == "fallback-generated"
    ui_ia_valid, ui_ia_detail = ui_ia_contract_valid(ui_ia_contract_path)
    surface_contract_taxonomy = surface_contract_taxonomy_report(ui_ia_contract_path, productness_gate_report)
    surface_contract_present = bool(surface_contract_taxonomy.get("present"))
    surface_contract_checks = (
        surface_contract_taxonomy.get("checks", {}) if isinstance(surface_contract_taxonomy.get("checks", {}), dict) else {}
    )
    surface_contract_metrics = (
        surface_contract_taxonomy.get("metrics", {}) if isinstance(surface_contract_taxonomy.get("metrics", {}), dict) else {}
    )
    surface_contract_gate_green = bool(surface_contract_taxonomy.get("gate_pass")) if surface_contract_present else False
    surface_contract_report_reused = bool(surface_contract_taxonomy.get("report_reused"))
    surface_contract_report_validation_reason = str(surface_contract_taxonomy.get("report_validation_reason") or "").strip()
    frontend_contract_blocking = require_frontend_contract

    if backend_packet_present:
        backend_unit_test_signal_present = lane_step_present(verification_ledger_report, "backend", "unit-tests")
        backend_unit_tests_green = lane_step_is_pass(verification_ledger_report, "backend", "unit-tests")
        backend_targeted_signal_present = backend_truth["service_boundary_signal_present"] or lane_step_present(
            verification_ledger_report, "backend", "targeted-tests"
        )
        backend_targeted_tests_green = bool(backend_truth["service_boundary_truth"])
        backend_persistence_truth_required = bool(backend_truth["requires_persistence_truth"])
        backend_persistence_green = (
            True
            if not backend_persistence_truth_required
            else bool(backend_truth["sql_persistence_truth"]) and bool(backend_truth["service_persistence_roundtrip_truth"])
        )
        backend_migration_green = (
            True if not backend_persistence_truth_required else bool(backend_truth["migration_execution"])
        )
        public_contract_skeleton_gate_green = (
            True
            if not bool(backend_truth["public_contract_skeleton_required"])
            else bool(backend_truth["public_contract_skeleton_truth"])
        )
        persistence_reentry_gate_green = (
            True if not backend_persistence_truth_required else bool(backend_truth["persistence_reentry_truth"])
        )
        api_evidence_linkage_gate_green = bool(backend_truth["api_evidence_linkage_truth"])
    elif has_packet_level_verification:
        backend_unit_test_signal_present = False
        backend_unit_tests_green = False
        backend_targeted_signal_present = False
        backend_targeted_tests_green = False
        backend_persistence_truth_required = False
        backend_persistence_green = False
        backend_migration_green = False
        public_contract_skeleton_gate_green = False
        persistence_reentry_gate_green = False
        api_evidence_linkage_gate_green = False
    else:
        backend_unit_test_signal_present = ledger_step_present(verification_ledger_report, "unit-tests")
        backend_unit_tests_green = runtime_unit_tests_green
        backend_targeted_signal_present = ledger_step_present(verification_ledger_report, "targeted-tests")
        backend_targeted_tests_green = runtime_targeted_tests_green
        backend_persistence_truth_required = False
        backend_persistence_green = True
        backend_migration_green = True
        public_contract_skeleton_gate_green = True
        persistence_reentry_gate_green = True
        api_evidence_linkage_gate_green = True
    backend_packet_truth_required = implementation_signal_present
    backend_packet_truth_present = backend_packet_present
    strict_runtime_backend_gate_green = (
        strict_runtime_closure
        and backend_packet_present
        and backend_unit_tests_green
        and backend_targeted_tests_green
        and backend_persistence_green
        and backend_migration_green
        and public_contract_skeleton_gate_green
        and persistence_reentry_gate_green
        and api_evidence_linkage_gate_green
    )
    backend_layer_full_evidence_gate_green = backend_layer_rollup["all_green"]
    backend_layer_effective_gate_green = backend_layer_full_evidence_gate_green or strict_runtime_backend_gate_green
    runtime_wp_effective_green = runtime_wp_green or strict_runtime_backend_gate_green
    backend_core_gate_green = (
        (backend_packet_truth_present if backend_packet_truth_required else True)
        and (backend_targeted_tests_green if backend_packet_present else True)
        and (backend_persistence_green if backend_packet_present else True)
        and (backend_migration_green if backend_packet_present else True)
        and (public_contract_skeleton_gate_green if backend_packet_present else True)
        and (persistence_reentry_gate_green if backend_packet_present else True)
        and (backend_layer_effective_gate_green if backend_layer_rollup["present"] else True)
    )

    if frontend_packet_present:
        frontend_targeted_signal_present = lane_step_present(verification_ledger_report, "frontend", "targeted-tests")
        frontend_targeted_tests_green = lane_step_is_pass(verification_ledger_report, "frontend", "targeted-tests")
    elif has_packet_level_verification:
        frontend_targeted_signal_present = False
        frontend_targeted_tests_green = False
    else:
        frontend_targeted_signal_present = ledger_step_present(verification_ledger_report, "targeted-tests")
        frontend_targeted_tests_green = runtime_targeted_tests_green

    build_green = report_is_pass(build_report) if build_report is not None else runtime_build_green
    lint_green = report_is_pass(lint_report) if lint_report is not None else runtime_lint_green
    typecheck_green = report_is_pass(typecheck_report) if typecheck_report is not None else runtime_typecheck_green
    unit_tests_green = report_is_pass(unit_test_report) if unit_test_report is not None else backend_unit_tests_green
    coverage_green = report_is_pass(coverage_gate_report) if coverage_gate_report is not None else True
    openapi_diff_pass = report_is_pass(openapi_diff_report) if openapi_diff_report is not None else False
    code_review_critical = first_int(
        code_review_metrics,
        ("critical_findings",),
        ("summary", "critical_findings"),
        ("summary", "critical"),
        ("metrics", "critical_findings"),
        ("metrics", "critical"),
    )
    code_review_high = first_int(
        code_review_metrics,
        ("high_findings",),
        ("summary", "high_findings"),
        ("summary", "high"),
        ("metrics", "high_findings"),
        ("metrics", "high"),
    )
    code_review_mock_runtime_dependencies = first_int(
        code_review_metrics,
        ("mock_runtime_dependency_count",),
        ("summary", "mock_runtime_dependency_count"),
    )
    code_review_frontend_surface_gaps = first_int(
        code_review_metrics,
        ("frontend_core_surface_gap_count",),
        ("summary", "frontend_core_surface_gap_count"),
    )
    code_review_frontend_contract_meta_surfaces = first_int(
        code_review_metrics,
        ("frontend_contract_meta_surface_count",),
        ("summary", "frontend_contract_meta_surface_count"),
    )
    code_review_frontend_operability_gaps = first_int(
        code_review_metrics,
        ("frontend_operability_gap_count",),
        ("summary", "frontend_operability_gap_count"),
    )
    code_review_frontend_contract_alignment_gaps = first_int(
        code_review_metrics,
        ("frontend_contract_alignment_gap_count",),
        ("summary", "frontend_contract_alignment_gap_count"),
    )
    code_review_empty_or_audit_shaped_services = first_int(
        code_review_metrics,
        ("empty_or_audit_shaped_service_count",),
        ("summary", "empty_or_audit_shaped_service_count"),
    )
    code_review_same_source_test_risks = first_int(
        code_review_metrics,
        ("same_source_test_risk_count",),
        ("summary", "same_source_test_risk_count"),
    )
    code_review_anti_cheat_negative_tests = first_int(
        code_review_metrics,
        ("anti_cheat_negative_test_count",),
        ("summary", "anti_cheat_negative_test_count"),
    )
    code_review_all_payload_typed = None
    if isinstance(code_review_metrics, dict):
        code_review_summary = code_review_metrics.get("summary", {})
        if isinstance(code_review_summary, dict):
            if "all_payload_typed" in code_review_summary:
                code_review_all_payload_typed = bool(code_review_summary.get("all_payload_typed"))
            elif isinstance(code_review_summary.get("unknown_payload_target_count"), (int, float)):
                code_review_all_payload_typed = int(code_review_summary.get("unknown_payload_target_count", 0) or 0) == 0
    if code_review_all_payload_typed is not None:
        bootstrap_all_payload_typed = code_review_all_payload_typed
        bootstrap_all_payload_typed_basis = "code-review-metrics.summary"
    behavior_card_consistency = {}
    if isinstance(code_review_metrics, dict):
        candidate = code_review_metrics.get("behavior_card_consistency")
        if not isinstance(candidate, dict):
            summary = code_review_metrics.get("summary", {})
            candidate = summary.get("behavior_card_consistency") if isinstance(summary, dict) else None
        if isinstance(candidate, dict):
            behavior_card_consistency = candidate
    behavior_card_consistency_classification = str(behavior_card_consistency.get("classification", "consistent")).strip()
    behavior_static_preflight_gate_green = True
    behavior_static_preflight_blockers: list[str] = []
    if isinstance(behavior_static_preflight_report, dict) and behavior_static_preflight_report:
        behavior_static_preflight_gate_green = str(
            behavior_static_preflight_report.get("overall_quality_gate", "")
        ).strip().lower() in {"pass", ""}
        blockers = behavior_static_preflight_report.get("blockers", [])
        if isinstance(blockers, list):
            behavior_static_preflight_blockers = [str(item) for item in blockers if str(item).strip()]
    behavior_card_missing_implementation_steps = [
        str(item).strip()
        for item in behavior_card_consistency.get("missing_implementation_steps", [])
        if str(item).strip()
    ]
    strict_runtime_behavior_test_gap_resolved = (
        strict_runtime_closure
        and behavior_card_consistency_classification in {"action_card_test_gap", "p3_test_gap"}
        and not behavior_card_missing_implementation_steps
        and backend_packet_present
        and runtime_targeted_tests_green
        and runtime_unit_tests_green
        and runtime_build_green
        and runtime_lint_green
        and runtime_typecheck_green
        and runtime_smoke_green
        and started_service_smoke_green
    )
    implementation_depth_gate_green = (
        (
            behavior_card_consistency_classification in {"", "consistent"}
            or strict_runtime_behavior_test_gap_resolved
        )
        and behavior_static_preflight_gate_green
    )
    security_critical = first_int(
        security_audit_report,
        ("critical_findings",),
        ("summary", "critical_findings"),
        ("summary", "critical"),
        ("metrics", "critical_findings"),
        ("metrics", "critical"),
    )
    security_high = first_int(
        security_audit_report,
        ("high_findings",),
        ("summary", "high_findings"),
        ("summary", "high"),
        ("metrics", "high_findings"),
        ("metrics", "high"),
    )
    auth_downgrade_findings = first_int(
        security_audit_report,
        ("auth_downgrade_findings",),
        ("summary", "auth_downgrade_findings"),
    )

    if build_report is not None and not build_green:
        failures.append("build_gate_failed")
    if lint_report is not None and not lint_green:
        failures.append("lint_gate_failed")
    if typecheck_report is not None and not typecheck_green:
        failures.append("typecheck_gate_failed")
    if unit_test_report is not None and not unit_tests_green:
        failures.append("unit_test_gate_failed")
    if coverage_gate_report is not None and not coverage_green:
        failures.append("coverage_gate_failed")
    if backend_packet_truth_required and not backend_packet_truth_present:
        failures.append("backend_packet_truth_missing")
    if backend_packet_present and not backend_targeted_tests_green:
        failures.append("backend_interface_gate_failed")
    if backend_packet_present and backend_persistence_truth_required and not backend_persistence_green:
        failures.append("backend_persistence_gate_failed")
    if backend_packet_present and backend_persistence_truth_required and not backend_migration_green:
        failures.append("backend_migration_gate_failed")
    if backend_layer_rollup["present"] and not backend_layer_effective_gate_green:
        failures.append("backend_layered_api_gate_failed")
    if backend_packet_present and not public_contract_skeleton_gate_green:
        failures.append("public_contract_skeleton_gate_failed")
    if not implementation_depth_gate_green:
        if not behavior_static_preflight_gate_green:
            failures.append("behavior_static_preflight_failed")
        elif behavior_card_consistency_classification in {"action_card_implementation_gap", "p3_implementation_gap"}:
            failures.append("action_card_implementation_gap")
        elif behavior_card_consistency_classification in {"action_card_test_gap", "p3_test_gap"}:
            if not strict_runtime_behavior_test_gap_resolved:
                failures.append("action_card_test_gap")
        elif behavior_card_consistency_classification == "trace_drift":
            failures.append("behavior_card_trace_drift")
        elif behavior_card_consistency_classification == "trace_authority_gap":
            failures.append("behavior_card_trace_authority_gap")
        elif behavior_card_consistency_classification == "p2_operation_source_obligation_gap":
            failures.append("p2_operation_source_obligation_gap")
        elif behavior_card_consistency_classification == "risk_tier_mismatch":
            failures.append("risk_tier_mismatch")
        elif behavior_card_consistency_classification in {
            "p1_value_to_p2_operation_resolution_matrix_missing",
            "implementation_component_catalog_missing",
            "component_action_card_obligation_missing",
            "component_action_card_obligation_matrix_missing",
            "action_card_depth_mismatch",
            "action_card_source_material_missing",
            "required_action_card_missing",
            "acd_required_deep_but_card_slim",
            "split_required_card_implemented_directly",
        }:
            failures.append(behavior_card_consistency_classification)
        else:
            failures.append("behavior_card_handoff_gap")
    if backend_packet_present and not persistence_reentry_gate_green:
        failures.append("persistence_reentry_gate_failed")
    if code_review_mock_runtime_dependencies > 0:
        failures.append("mock_runtime_dependency_detected")
    if frontend_contract_blocking and code_review_frontend_surface_gaps > 0:
        failures.append("frontend_core_surface_gap_detected")
    if frontend_contract_blocking and code_review_frontend_contract_meta_surfaces > 0:
        failures.append("frontend_contract_meta_surface_detected")
    if frontend_contract_blocking and code_review_frontend_operability_gaps > 0:
        failures.append("frontend_operability_gap_detected")
    if frontend_contract_blocking and code_review_frontend_contract_alignment_gaps > 0:
        failures.append("frontend_contract_alignment_gap_detected")
    if frontend_contract_blocking and frontend_packet_present and not frontend_targeted_tests_green:
        failures.append("frontend_interface_gate_failed")
    if frontend_contract_blocking and not ui_ia_valid:
        failures.append("ui_ia_contract_gate_failed")
    if frontend_contract_blocking and not surface_contract_present:
        failures.append("surface_contract_evidence_missing")
    if frontend_contract_blocking and productness_gate_report is not None and not surface_contract_report_reused:
        failures.append("surface_contract_productness_report_invalid")
    if frontend_contract_blocking and surface_contract_present and not surface_contract_checks.get("core_interaction_guess_gate", True):
        failures.append("surface_contract_guess_gate_failed")
    if frontend_contract_blocking and surface_contract_present and not surface_contract_checks.get("operable_cross_page_flow_gate", True):
        failures.append("surface_contract_flow_gate_failed")
    if frontend_contract_blocking and surface_contract_present and not surface_contract_checks.get("core_surface_pass_gate", True):
        failures.append("surface_contract_core_surface_gate_failed")
    if frontend_contract_blocking and surface_contract_present and not surface_contract_checks.get("role_surface_alignment_gate", True):
        failures.append("surface_contract_role_alignment_gate_failed")
    if frontend_contract_blocking and surface_contract_present and not surface_contract_checks.get("authority_status_gate", True):
        failures.append("surface_contract_authority_status_gate_failed")
    implementation_ready = (
        bootstrap_green
        and build_green
        and lint_green
        and typecheck_green
        and unit_tests_green
        and coverage_green
        and backend_core_gate_green
        and code_review_mock_runtime_dependencies == 0
        and (code_review_frontend_surface_gaps == 0 if frontend_contract_blocking else True)
        and (code_review_frontend_contract_meta_surfaces == 0 if frontend_contract_blocking else True)
        and (code_review_frontend_operability_gaps == 0 if frontend_contract_blocking else True)
        and (code_review_frontend_contract_alignment_gaps == 0 if frontend_contract_blocking else True)
        and ((frontend_targeted_tests_green if frontend_packet_present else True) if frontend_contract_blocking else True)
        and (ui_ia_valid if frontend_contract_blocking else True)
        and (surface_contract_present if frontend_contract_blocking else True)
        and (surface_contract_gate_green if frontend_contract_blocking else True)
        and ((surface_contract_report_reused if productness_gate_report is not None else True) if frontend_contract_blocking else True)
        and (runtime_wp_effective_green if wp_gate_report is not None else True)
        and implementation_depth_gate_green
    )
    unit_test_signal_present = bool(unit_test_report is not None or backend_unit_test_signal_present)
    if openapi_diff_report is not None and not openapi_diff_pass:
        failures.append("openapi_diff_failed")
    if code_review_metrics is not None and (code_review_critical > 0 or code_review_high > 0):
        failures.append("code_review_has_high_or_critical_findings")
    if security_audit_report is not None and security_critical > 0:
        failures.append("security_audit_has_critical_findings")
    if security_audit_report is not None and security_high > 0:
        failures.append("security_audit_has_high_findings")

    trace_registry_final_present = path_exists(trace_registry_final_path)
    trace_registry_payload = (
        load_json(trace_registry_final_path)
        if trace_registry_final_present and trace_registry_final_path and trace_registry_final_path.suffix == ".json"
        else None
    )
    if isinstance(trace_registry_payload, dict) and trace_registry_final_path is not None:
        trace_registry_payload = dict(trace_registry_payload)
        trace_registry_payload["trace_db_present"] = bool(trace_registry_payload.get("trace_db_present")) or (
            trace_registry_final_path.parent / ".trace" / "trace.db"
        ).exists()
    trace_quality = trace_registry_quality_report(trace_registry_payload)
    trace_registry_gap_count = trace_registry_blocking_gap_count(trace_registry_payload)
    trace_registry_unresolved_count = int(trace_quality.get("unresolved_count", 0) or 0)
    trace_registry_review_count = int(trace_quality.get("review_count", 0) or 0)
    trace_registry_suggested_count = int(trace_quality.get("suggested_count", 0) or 0)
    trace_registry_abuse_count = int(trace_quality.get("abuse_count", 0) or 0)
    if trace_registry_final_present and (
        trace_registry_gap_count > 0 or trace_registry_unresolved_count > 0 or trace_registry_abuse_count > 0
    ):
        failures.append("trace_registry_final_has_unresolved_ids")
    if trace_registry_final_present and bool(trace_quality.get("trace_db_projection_blocking")):
        failures.append("trace_db_not_indexed_for_phase3_evidence")

    openapi_final_present = path_exists(openapi_final_path)
    api_doc_assets_present = dir_has_entries(api_doc_dir)
    deploy_runbook_present = path_exists(deploy_runbook_path)
    dockerfile_present = path_exists(dockerfile_path)
    compose_prod_present = path_exists(compose_prod_path)
    dockerfile_runtime_present = dockerfile_has_runtime_entrypoint(dockerfile_path)
    dockerfile_multistage_present = dockerfile_has_multistage_build(dockerfile_path)
    dockerfile_non_root_present = dockerfile_has_non_root_user(dockerfile_path)
    dockerfile_healthcheck_present = dockerfile_has_healthcheck(dockerfile_path)
    dockerfile_secret_safe = dockerfile_present and not delivery_asset_has_hardcoded_secrets(dockerfile_path)
    compose_prod_runtime_present = compose_has_startable_runtime(compose_prod_path)
    compose_prod_secret_safe = compose_prod_present and not delivery_asset_has_hardcoded_secrets(compose_prod_path)
    performance_baseline_present = path_exists(performance_baseline_path)
    acceptance_report_present = path_exists(acceptance_report_path)
    execution_report_present = path_exists(execution_report_path)
    delivery_docker_production_minimum = all(
        [
            dockerfile_multistage_present,
            dockerfile_non_root_present,
            dockerfile_healthcheck_present,
            dockerfile_secret_safe,
            compose_prod_secret_safe,
        ]
    )

    if runtime_delivery_assets_required:
        delivery_artifacts_complete = all(
            [
                openapi_final_present,
                api_doc_assets_present,
                deploy_runbook_present,
                dockerfile_present,
                compose_prod_present,
                performance_baseline_present,
                acceptance_report_present,
                execution_report_present,
                trace_registry_final_present,
            ]
        )
    else:
        delivery_artifacts_complete = all(
            [
                openapi_final_present,
                acceptance_report_present,
                execution_report_present,
                trace_registry_final_present,
            ]
        )

    delivery_report_inputs_complete = all(
        report is not None for report in (openapi_diff_report, code_review_metrics, security_audit_report)
    )

    delivery_ready = (
        implementation_ready
        and ((not ui_fallback_generated) if frontend_contract_blocking else True)
        and delivery_report_inputs_complete
        and openapi_diff_pass
        and code_review_critical == 0
        and code_review_high == 0
        and security_critical == 0
        and security_high == 0
        and auth_downgrade_findings == 0
        and trace_registry_gap_count == 0
        and (api_evidence_linkage_gate_green if api_doc_assets_present else True)
        and delivery_artifacts_complete
        and (
            (
                dockerfile_runtime_present
                and compose_prod_runtime_present
                and delivery_docker_production_minimum
                and runtime_smoke_green
                and started_service_smoke_green
            )
            if runtime_delivery_assets_required
            else True
        )
    )

    if not build_green:
        warnings.append("build_gate_not_green_yet")
    if not lint_green:
        warnings.append("lint_gate_not_green_yet")
    if not typecheck_green:
        warnings.append("typecheck_gate_not_green_yet")
    if not unit_test_signal_present:
        warnings.append("unit_test_evidence_missing")
    elif not unit_tests_green:
        warnings.append("unit_test_gate_not_green_yet")
    if implementation_signal_present and coverage_gate_report is None:
        warnings.append("coverage_gate_report_missing")
    if not backend_targeted_signal_present and coverage_gate_report is None:
        warnings.append("backend_interface_evidence_missing")
    if backend_packet_truth_required and not backend_packet_truth_present:
        warnings.append("backend_packet_level_truth_missing")
    elif backend_packet_present and not backend_targeted_tests_green:
        warnings.append("backend_service_boundary_truth_missing")
    elif coverage_gate_report is not None and not coverage_green:
        warnings.append("coverage_gate_not_green_yet")
    if backend_packet_present and backend_persistence_truth_required and not backend_persistence_green:
        warnings.append("backend_sql_persistence_truth_missing")
    if backend_packet_present and backend_persistence_truth_required and not bool(backend_truth["service_persistence_roundtrip_truth"]):
        warnings.append("backend_service_persistence_roundtrip_truth_missing")
    if backend_packet_present and backend_persistence_truth_required and not backend_migration_green:
        warnings.append("backend_migration_execution_missing")
    if backend_layer_rollup["present"] and not backend_layer_effective_gate_green:
        warnings.append("backend_layered_api_validation_not_green")
    elif backend_layer_rollup["present"] and not backend_layer_full_evidence_gate_green and strict_runtime_backend_gate_green:
        warnings.append("backend_full_evidence_deferred_by_strict_runtime")
    if backend_packet_present and not public_contract_skeleton_gate_green:
        warnings.append("public_contract_skeleton_truth_missing")
    if backend_packet_present and not persistence_reentry_gate_green:
        warnings.append("persistence_reentry_truth_missing")
    if api_doc_assets_present and not api_evidence_linkage_gate_green:
        warnings.append("api_evidence_linkage_missing")
    if code_review_mock_runtime_dependencies > 0:
        warnings.append("mock_runtime_dependency_still_present")
    if code_review_frontend_surface_gaps > 0:
        warnings.append("frontend_core_surface_coverage_incomplete")
    if code_review_frontend_contract_meta_surfaces > 0:
        warnings.append("frontend_contract_meta_scaffold_still_present")
    if code_review_frontend_operability_gaps > 0:
        warnings.append("frontend_operability_not_proven")
    if code_review_frontend_contract_alignment_gaps > 0:
        warnings.append("frontend_contract_alignment_incomplete")
    if frontend_packet_present and not frontend_targeted_signal_present:
        warnings.append("frontend_interface_evidence_missing")
    elif frontend_packet_present and not frontend_targeted_tests_green:
        warnings.append("frontend_interface_gate_not_green_yet")
    if frontend_packet_present and not backend_core_gate_green:
        warnings.append("frontend_capped_by_backend_runtime_reachability")
    if not frontend_contract_blocking and not surface_contract_present:
        warnings.append("frontend_contract_optional_lane_not_requested")
    if wp_gate_report is not None and not runtime_wp_effective_green:
        warnings.append("wp_gate_not_green_yet")
    elif wp_gate_report is not None and not runtime_wp_green and strict_runtime_backend_gate_green:
        warnings.append("wp_full_evidence_deferred_by_strict_runtime")
    if frontend_packet_present and not lane_step_is_pass(verification_ledger_report, "frontend", "unit-tests"):
        warnings.append("frontend_unit_test_relaxed_in_p3")
    if ui_fallback_generated and ui_prototype_fallback_report_path is None:
        warnings.append("ui_fallback_report_missing")
    if ui_fallback_generated and not ui_ia_valid:
        warnings.append("ui_ia_contract_not_ready")
    if frontend_contract_blocking and not surface_contract_present:
        warnings.append("surface_contract_evidence_missing")
    elif (path_exists(ui_ia_contract_path) or productness_gate_report is not None) and not surface_contract_present:
        warnings.append("surface_contract_evidence_missing")
    if surface_contract_report_validation_reason == "fingerprint-missing":
        warnings.append("surface_contract_productness_report_fingerprint_missing")
    elif surface_contract_report_validation_reason == "path-mismatch":
        warnings.append("surface_contract_productness_report_path_mismatch")
    elif surface_contract_report_validation_reason == "hash-mismatch":
        warnings.append("surface_contract_productness_report_hash_mismatch")
    elif surface_contract_report_validation_reason == "current-contract-missing" and productness_gate_report is not None:
        warnings.append("surface_contract_productness_report_missing_current_contract")
    elif surface_contract_report_validation_reason == "path-invalid":
        warnings.append("surface_contract_productness_report_path_invalid")
    if surface_contract_present and not surface_contract_checks.get("core_interaction_guess_gate", True):
        warnings.append("surface_contract_still_requires_p3_guessing")
    if surface_contract_present and not surface_contract_checks.get("operable_cross_page_flow_gate", True):
        warnings.append("surface_contract_operable_flow_missing")
    if surface_contract_present and not surface_contract_checks.get("core_surface_pass_gate", True):
        warnings.append("surface_contract_core_surface_incomplete")
    if surface_contract_present and not surface_contract_checks.get("role_surface_alignment_gate", True):
        warnings.append("surface_contract_role_alignment_not_green")
    if surface_contract_present and not surface_contract_checks.get("authority_status_gate", True):
        warnings.append("surface_contract_authority_status_not_green")
    if strict_runtime_behavior_test_gap_resolved:
        warnings.append("behavior_card_test_gap_resolved_by_strict_runtime")
    if implementation_ready and ui_fallback_generated:
        warnings.append("ui_still_fallback_generated")
    if implementation_ready and not openapi_diff_pass:
        warnings.append("openapi_diff_not_green_yet")
    if implementation_ready and code_review_metrics is None:
        warnings.append("code_review_metrics_missing")
    if implementation_ready and security_audit_report is None:
        warnings.append("security_audit_report_missing")
    if implementation_ready and not openapi_final_present:
        warnings.append("openapi_final_missing")
    if runtime_delivery_assets_required and implementation_ready and not api_doc_assets_present:
        warnings.append("api_doc_assets_missing")
    if runtime_delivery_assets_required and implementation_ready and not deploy_runbook_present:
        warnings.append("deploy_runbook_missing")
    if runtime_delivery_assets_required and implementation_ready and not dockerfile_present:
        warnings.append("dockerfile_missing")
    if runtime_delivery_assets_required and implementation_ready and dockerfile_present and not dockerfile_runtime_present:
        warnings.append("dockerfile_not_startable_yet")
    if runtime_delivery_assets_required and implementation_ready and not compose_prod_present:
        warnings.append("compose_prod_missing")
    if runtime_delivery_assets_required and implementation_ready and compose_prod_present and not compose_prod_runtime_present:
        warnings.append("compose_prod_not_startable_yet")
    if runtime_delivery_assets_required and implementation_ready and dockerfile_present and not dockerfile_multistage_present:
        warnings.append("dockerfile_not_multistage_yet")
    if runtime_delivery_assets_required and implementation_ready and dockerfile_present and not dockerfile_non_root_present:
        warnings.append("dockerfile_non_root_user_missing")
    if runtime_delivery_assets_required and implementation_ready and dockerfile_present and not dockerfile_healthcheck_present:
        warnings.append("dockerfile_healthcheck_missing")
    if runtime_delivery_assets_required and implementation_ready and dockerfile_present and not dockerfile_secret_safe:
        warnings.append("dockerfile_contains_inline_secret_or_credentials")
    if runtime_delivery_assets_required and implementation_ready and compose_prod_present and not compose_prod_secret_safe:
        warnings.append("compose_prod_contains_inline_secret_or_credentials")
    if runtime_delivery_assets_required and implementation_ready and not runtime_smoke_present:
        warnings.append("runtime_smoke_report_missing")
    elif runtime_delivery_assets_required and implementation_ready and not runtime_smoke_green:
        warnings.append("runtime_smoke_not_green_yet")
    if runtime_delivery_assets_required and implementation_ready and runtime_smoke_green and not started_service_smoke_present:
        warnings.append("started_service_smoke_report_missing")
    elif runtime_delivery_assets_required and implementation_ready and started_service_smoke_present and not started_service_smoke_green:
        warnings.append("started_service_smoke_not_green_yet")
    if security_audit_report is not None and auth_downgrade_findings > 0:
        warnings.append("auth_implementation_downgrade_detected")
    if runtime_delivery_assets_required and implementation_ready and not performance_baseline_present:
        warnings.append("performance_baseline_missing")
    if implementation_ready and not acceptance_report_present:
        warnings.append("acceptance_report_missing")
    if implementation_ready and not execution_report_present:
        warnings.append("execution_report_missing")
    if implementation_ready and not trace_registry_final_present:
        warnings.append("trace_registry_final_missing")
    if bootstrap_toolchain_status == "pending-install" and not implementation_ready:
        warnings.append("bootstrap_toolchain_install_not_attempted_yet")
    elif bootstrap_toolchain_status not in ("ready", "pending-install", "unknown", "not-requested") and not implementation_ready:
        warnings.append("bootstrap_toolchain_not_ready_yet")
    if not bootstrap_all_payload_typed:
        warnings.append("implementation_payloads_still_generic")

    if not bootstrap_green:
        state = "blocked"
    elif delivery_ready:
        state = "delivery-ready"
    elif implementation_ready:
        state = "implementation-ready"
    elif implementation_signal_present:
        state = "implementation-in-progress"
    else:
        state = "foundation-ready"

    report = {
        "overall_quality_gate": "pass" if not failures else "fail",
        "phase_completion_gate": "pass" if delivery_ready else "fail",
        "implementation_complete": implementation_ready,
        "phase_complete": delivery_ready,
        "recommended_formal_state": state,
        "checks": {
            "delivery_mode": delivery_mode,
            "retained_proof_mode": retained_proof_mode,
            "strict_runtime_closure": strict_runtime_closure,
            "runtime_delivery_artifacts_required": runtime_delivery_assets_required,
            "bootstrap_gate": bootstrap_green,
            "implementation_signal_present": implementation_signal_present,
            "has_packet_level_verification": has_packet_level_verification,
            "backend_packet_present": backend_packet_present,
            "frontend_packet_present": frontend_packet_present,
            "bootstrap_toolchain_status": bootstrap_toolchain_status,
            "bootstrap_toolchain_status_basis": bootstrap_toolchain_status_basis,
            "bootstrap_all_payload_typed": bootstrap_all_payload_typed,
            "bootstrap_all_payload_typed_basis": bootstrap_all_payload_typed_basis,
            "build_gate": build_green,
            "lint_gate": lint_green,
            "typecheck_gate": typecheck_green,
            "unit_test_gate": unit_tests_green,
            "coverage_report_present": coverage_gate_report is not None,
            "coverage_gate": coverage_green,
            "wp_gate_pass": runtime_wp_effective_green,
            "wp_gate_report_pass": runtime_wp_green,
            "backend_unit_test_gate": unit_tests_green,
            "backend_packet_truth_required": backend_packet_truth_required,
            "backend_packet_truth_present": backend_packet_truth_present,
            "backend_interface_gate": backend_targeted_tests_green,
            "backend_persistence_gate": backend_persistence_green,
            "backend_service_persistence_roundtrip_gate": True
            if not backend_persistence_truth_required
            else bool(backend_truth["service_persistence_roundtrip_truth"]),
            "backend_migration_gate": backend_migration_green,
            "public_contract_skeleton_gate": public_contract_skeleton_gate_green,
            "public_contract_skeleton_required": bool(backend_truth["public_contract_skeleton_required"]),
            "public_contract_risk_tiers": backend_truth["public_contract_risk_tiers"],
            "persistence_reentry_gate": persistence_reentry_gate_green,
            "persistence_state_isolation_values": backend_truth["state_isolation_values"],
            "persistence_reentry_policy_values": backend_truth["reentry_policy_values"],
            "persistence_rerun_proof_values": backend_truth["rerun_proof_values"],
            "persistence_reentry_evidence_present": bool(backend_truth["persistence_reentry_evidence_present"]),
            "api_evidence_linkage_gate": api_evidence_linkage_gate_green,
            "backend_layered_api_gate": backend_layer_effective_gate_green,
            "backend_layered_api_full_evidence_gate": backend_layer_full_evidence_gate_green,
            "strict_runtime_backend_gate": strict_runtime_backend_gate_green,
            "backend_layered_api_gate_present": backend_layer_rollup["present"],
            "backend_layer_blocking_layers": backend_layer_rollup["blocking_layers"],
            "backend_layer_blocked_work_packages": backend_layer_rollup["blocked_work_packages"],
            "frontend_interface_gate": frontend_targeted_tests_green,
            "frontend_interface_signal_present": frontend_targeted_signal_present,
            "frontend_ceiling_state": "runtime-reachable"
            if frontend_packet_present and not backend_core_gate_green
            else ("implementation-eligible" if frontend_packet_present else "not-applicable"),
            "backend_persistence_truth_required": backend_persistence_truth_required,
            "backend_unit_test_signal_present": unit_test_signal_present,
            "backend_interface_signal_present": backend_targeted_signal_present,
            "frontend_unit_tests_relaxed": frontend_packet_present,
            "frontend_contract_required": frontend_contract_blocking,
            "frontend_contract_deferred": (not frontend_contract_blocking) and not surface_contract_present,
            "ui_fallback_generated": ui_fallback_generated,
            "delivery_ui_source_ready": (not ui_fallback_generated) if frontend_contract_blocking else True,
            "ui_ia_contract_present": path_exists(ui_ia_contract_path),
            "ui_ia_contract_valid": ui_ia_valid,
            "ui_ia_contract_detail": ui_ia_detail,
            "surface_contract_gate_present": surface_contract_present,
            "surface_contract_gate_source": surface_contract_taxonomy.get("source", "missing"),
            "surface_contract_gate": surface_contract_gate_green if surface_contract_present else False,
            "surface_contract_report_reused": surface_contract_report_reused,
            "surface_contract_report_validation_reason": surface_contract_report_validation_reason,
            "surface_contract_checks": surface_contract_checks,
            "surface_contract_metrics": surface_contract_metrics,
            "core_interaction_guess_count": int(surface_contract_metrics.get("core_interaction_guess_count", 0) or 0),
            "operable_cross_page_flow_count": int(surface_contract_metrics.get("operable_cross_page_flow_count", 0) or 0),
            "core_surface_pass_count": int(surface_contract_metrics.get("core_surface_pass_count", 0) or 0),
            "core_surface_count": int(surface_contract_metrics.get("core_surface_count", 0) or 0),
            "role_surface_alignment": surface_contract_metrics.get("role_surface_alignment", {}),
            "verification_lint_gate": runtime_lint_green,
            "verification_typecheck_gate": runtime_typecheck_green,
            "verification_unit_tests_gate": runtime_unit_tests_green,
            "verification_build_gate": runtime_build_green,
            "verification_targeted_tests_gate": runtime_targeted_tests_green,
            "implementation_gate": implementation_ready,
            "implementation_depth_gate": implementation_depth_gate_green,
            "behavior_static_preflight_gate": behavior_static_preflight_gate_green,
            "behavior_static_preflight_blockers": behavior_static_preflight_blockers,
            "behavior_card_consistency_classification": behavior_card_consistency_classification,
            "behavior_card_test_gap_resolved_by_strict_runtime": strict_runtime_behavior_test_gap_resolved,
            "behavior_card_missing_implementation_steps": behavior_card_missing_implementation_steps,
            "behavior_card_missing_test_steps": behavior_card_consistency.get("missing_test_steps", []),
            "openapi_diff_report_present": openapi_diff_report is not None,
            "openapi_diff_pass": openapi_diff_pass,
            "code_review_report_present": code_review_metrics is not None,
            "code_review_critical_findings": code_review_critical,
            "code_review_high_findings": code_review_high,
            "code_review_mock_runtime_dependency_count": code_review_mock_runtime_dependencies,
            "code_review_frontend_core_surface_gap_count": code_review_frontend_surface_gaps,
            "code_review_frontend_contract_meta_surface_count": code_review_frontend_contract_meta_surfaces,
            "code_review_frontend_operability_gap_count": code_review_frontend_operability_gaps,
            "code_review_frontend_contract_alignment_gap_count": code_review_frontend_contract_alignment_gaps,
            "empty_or_audit_shaped_service_count": code_review_empty_or_audit_shaped_services,
            "same_source_test_risk_count": code_review_same_source_test_risks,
            "anti_cheat_negative_test_count": code_review_anti_cheat_negative_tests,
            "security_audit_report_present": security_audit_report is not None,
            "security_critical_findings": security_critical,
            "security_high_findings": security_high,
            "auth_downgrade_findings": auth_downgrade_findings,
            "openapi_final_present": openapi_final_present,
            "api_doc_assets_present": api_doc_assets_present,
            "deploy_runbook_present": deploy_runbook_present,
            "dockerfile_present": dockerfile_present,
            "compose_prod_present": compose_prod_present,
            "dockerfile_runtime_present": dockerfile_runtime_present,
            "dockerfile_multistage_present": dockerfile_multistage_present,
            "dockerfile_non_root_present": dockerfile_non_root_present,
            "dockerfile_healthcheck_present": dockerfile_healthcheck_present,
            "dockerfile_secret_safe": dockerfile_secret_safe,
            "compose_prod_runtime_present": compose_prod_runtime_present,
            "compose_prod_secret_safe": compose_prod_secret_safe,
            "delivery_docker_production_minimum": delivery_docker_production_minimum,
            "runtime_smoke_present": runtime_smoke_present,
            "runtime_smoke_green": runtime_smoke_green,
            "started_service_smoke_present": started_service_smoke_present,
            "started_service_smoke_green": started_service_smoke_green,
            "performance_baseline_present": performance_baseline_present,
            "acceptance_report_present": acceptance_report_present,
            "execution_report_present": execution_report_present,
            "trace_registry_final_present": trace_registry_final_present,
            "trace_registry_gap_count": trace_registry_gap_count,
            "trace_registry_confirmed_count": int(trace_quality.get("confirmed_count", 0) or 0),
            "trace_registry_suggested_count": trace_registry_suggested_count,
            "trace_registry_review_count": trace_registry_review_count,
            "trace_registry_unresolved_count": trace_registry_unresolved_count,
            "trace_registry_unknown_count": int(trace_quality.get("unknown_count", 0) or 0),
            "trace_registry_abuse_count": trace_registry_abuse_count,
            "trace_registry_chain_coverage_state": str(trace_quality.get("chain_coverage_state", "unknown")),
            "trace_registry_quality": trace_quality,
            "trace_db_present": bool(trace_quality.get("trace_db_present")),
            "trace_db_indexed": bool(trace_quality.get("trace_db_indexed")),
            "trace_db_projection_status": str(trace_quality.get("trace_db_projection_status") or ""),
            "trace_db_projection_blocking": bool(trace_quality.get("trace_db_projection_blocking")),
            "delivery_artifacts_complete": delivery_artifacts_complete,
            "delivery_gate": delivery_ready,
        },
        "failures": failures,
        "warnings": warnings,
    }
    report["mainline_assessment"] = build_phase3_mainline_assessment(delivery_gate_report=report)
    report = apply_phase3_claim_ceiling(
        report,
        build_phase3_claim_ceiling_report(
            requested_formal_state=str(report.get("recommended_formal_state") or ""),
            checks=report.get("checks", {}),
            failures=failures,
            warnings=warnings,
            scope_states=report["mainline_assessment"],
        ),
    )
    report["mainline_assessment"] = build_phase3_mainline_assessment(delivery_gate_report=report)
    return report


def run_delivery_gate_mode(context: Phase3DeliveryGateContext) -> int:
    return run_delivery_gate_cli_mode(context, analyze_delivery=analyze_phase3_delivery)


def build_phase3_mode_handlers():
    handlers = build_phase3_mode_handlers_with_delivery(analyze_delivery=analyze_phase3_delivery)
    handlers["delivery-gate"] = run_delivery_gate_mode
    return handlers


def run_phase3_delivery_gate_mode(context: Phase3DeliveryGateContext) -> int:
    return build_phase3_mode_handlers()[context.mode](context)


def main(argv: list[str] | None = None) -> int:
    return run_phase3_delivery_gate_cli(argv=argv, analyze_delivery=analyze_phase3_delivery)


if __name__ == "__main__":
    raise SystemExit(main())
