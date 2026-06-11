from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase3.phase3_delivery_gate import (
    collect_phase3_coverage,
    generate_phase3_api_docs,
    generate_phase3_delivery_handoff,
    run_phase3_code_review,
    run_phase3_security_audit,
)
from phase3.phase3_runtime_smoke import run_phase3_runtime_smoke
from phase3.delivery_closure import finalize_phase3_delivery_closure
from phase3.timing_report import record_timing_segment, set_timing_segment, start_timer
from phase3.trace_registry import finalize_trace_registry
from phase3.worker_packet_runner import load_json, load_json_if_exists


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def first_existing_path(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def sync_json_report_if_provided(source_path: Path | None, destination_path: Path) -> Path | None:
    if source_path is None:
        return destination_path if destination_path.exists() else None
    if not source_path.exists():
        return destination_path if destination_path.exists() else None
    payload = load_json(source_path.resolve())
    write_text(destination_path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return destination_path


def resolve_runtime_smoke_service_url(explicit_service_url: str | None = None) -> str:
    explicit = (explicit_service_url or "").strip()
    if explicit:
        return explicit

    env_url = os.environ.get("PHASE3_RUNTIME_SMOKE_SERVICE_URL", "").strip()
    if env_url:
        return env_url

    for key in ("PHASE3_RUNTIME_SMOKE_API_HOST_PORT", "API_HOST_PORT"):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        try:
            port = int(raw)
        except ValueError:
            continue
        if 1 <= port <= 65535:
            return f"http://127.0.0.1:{port}"

    return "http://127.0.0.1:3000"


def resolve_delivery_bootstrap_report(output_dir: Path) -> tuple[dict[str, Any] | None, Path]:
    quality_report_path = output_dir / "phase3-quality-check.json"
    quality_report = load_json_if_exists(quality_report_path)
    if quality_report is None:
        return None, quality_report_path

    bootstrap_report = dict(quality_report)
    checks = quality_report.get("checks", {})
    bootstrap_checks = dict(checks) if isinstance(checks, dict) else {}
    toolchain_bootstrap_report = load_json_if_exists(output_dir / "phase3-toolchain-bootstrap.json") or {}
    if isinstance(toolchain_bootstrap_report, dict) and toolchain_bootstrap_report:
        toolchain_status = str(toolchain_bootstrap_report.get("overall_status", "unknown")).strip() or "unknown"
        bootstrap_checks["toolchain_bootstrap_status"] = toolchain_status
        bootstrap_checks["toolchain_bootstrap_raw_status"] = toolchain_status
        bootstrap_checks["toolchain_bootstrap_status_basis"] = (
            str(toolchain_bootstrap_report.get("status_semantics", "")).strip()
            or "initial-bootstrap-snapshot-before-runtime-validation"
        )
    code_review_metrics = load_json_if_exists(output_dir / "code-review-metrics.json") or {}
    code_review_summary = code_review_metrics.get("summary", {}) if isinstance(code_review_metrics, dict) else {}
    if isinstance(code_review_summary, dict):
        if "all_payload_typed" in code_review_summary:
            bootstrap_checks["all_payload_typed"] = bool(code_review_summary.get("all_payload_typed"))
            bootstrap_checks["all_payload_typed_basis"] = "code-review-metrics.summary"
        unknown_payload_target_count = code_review_summary.get("unknown_payload_target_count")
        if isinstance(unknown_payload_target_count, (int, float)):
            bootstrap_checks["unknown_payload_target_count"] = int(unknown_payload_target_count)
    bootstrap_report["checks"] = bootstrap_checks
    return bootstrap_report, quality_report_path


def refresh_phase3_post_execution(
    output_dir: Path,
    *,
    retained_proof_mode: bool = False,
    strict_runtime_closure: bool = False,
    run_runtime_smoke: bool = False,
    runtime_smoke_service_url: str | None = None,
    runtime_smoke_fn=run_phase3_runtime_smoke,
    skip_coverage_collection: bool = False,
    coverage_collection_skip_reason: str = "",
    toolchain_bootstrap_report_path: Path | None = None,
    unit_test_report_path: Path | None = None,
    coverage_gate_report_path: Path | None = None,
    wp_gate_report_path: Path | None = None,
    verification_ledger_report_path: Path | None = None,
    runtime_smoke_report_path: Path | None = None,
    started_service_smoke_report_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    timing_segments: dict[str, dict[str, Any]] = {}
    sync_json_report_if_provided(toolchain_bootstrap_report_path, output_dir / "phase3-toolchain-bootstrap.json")
    bootstrap_report, bootstrap_report_path = resolve_delivery_bootstrap_report(output_dir)
    if bootstrap_report is None:
        return {}

    trace_matrix = load_json_if_exists(output_dir / "test-trace-matrix.json")
    implementation_bindings = load_json_if_exists(output_dir / "implementation-bindings.json")
    trace_registry_final_path = output_dir / "phase-3-trace-registry-final.json"
    trace_registry_final = load_json_if_exists(trace_registry_final_path)
    tech_stack_decision_path = output_dir / "tech-stack-decision.yaml"
    baseline_openapi_path = output_dir / "contracts" / "openapi.yaml"
    if trace_matrix is not None and implementation_bindings is not None:
        trace_registry_final = finalize_trace_registry(
            test_trace_matrix=trace_matrix,
            implementation_bindings=implementation_bindings,
        )
        write_text(
            trace_registry_final_path,
            json.dumps(trace_registry_final, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )

    delivery_gate_path = output_dir / "phase3-delivery-gate.json"
    acceptance_report_path = output_dir / "phase-3-acceptance-report.md"
    execution_report_path = output_dir / "phase-3-execution-report.md"
    metadata = load_json_if_exists(output_dir / "phase3-run-metadata.json") or {}
    case_name = str(metadata.get("case_name", "")).strip()
    version = str(metadata.get("version", "")).strip() or "0.1.0"
    tech_stack_text = tech_stack_decision_path.read_text(encoding="utf-8") if tech_stack_decision_path.exists() else ""

    canonical_coverage_gate_report_path = output_dir / "phase3-coverage-gate.json"
    coverage_started = start_timer()
    if skip_coverage_collection:
        write_text(
            canonical_coverage_gate_report_path,
            json.dumps(
                {
                    "collected": False,
                    "collection_status": coverage_collection_skip_reason or "skipped",
                    "collection_command": "",
                    "command_exit_code": 0,
                    "coverage_summary_path": "",
                    "stdout_log_path": "",
                    "stderr_log_path": "",
                    "overall_quality_gate": "fail",
                    "checks": {},
                    "failures": ["coverage_collection_skipped"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        record_timing_segment(timing_segments, "coverage_collection", coverage_started, status="skipped")
    else:
        collect_phase3_coverage(
            workspace_root=output_dir,
            output_path=canonical_coverage_gate_report_path,
        )
        record_timing_segment(timing_segments, "coverage_collection", coverage_started)
    resolved_coverage_gate_report_path = sync_json_report_if_provided(
        coverage_gate_report_path,
        canonical_coverage_gate_report_path,
    )
    if resolved_coverage_gate_report_path is None:
        resolved_coverage_gate_report_path = first_existing_path(
            canonical_coverage_gate_report_path,
            output_dir / "coverage-gate.json",
        )
    coverage_gate_report = load_json_if_exists(resolved_coverage_gate_report_path)
    resolved_wp_gate_report_path = sync_json_report_if_provided(
        wp_gate_report_path,
        output_dir / "phase3-wp-gate.json",
    )
    resolved_verification_ledger_report_path = sync_json_report_if_provided(
        verification_ledger_report_path,
        output_dir / "phase3-verification-ledger.json",
    )
    wp_gate_report = load_json_if_exists(resolved_wp_gate_report_path)
    verification_ledger_report = load_json_if_exists(resolved_verification_ledger_report_path)

    if baseline_openapi_path.exists() and not retained_proof_mode:
        generate_phase3_api_docs(
            baseline_openapi=load_json(baseline_openapi_path),
            output_dir=output_dir,
            title=f"{case_name or 'Phase-3'} API Documentation",
        )

    if case_name and not retained_proof_mode:
        generate_phase3_delivery_handoff(
            output_dir=output_dir,
            case_name=case_name,
            version=version,
            tech_stack_text=tech_stack_text,
            wp_gate_report=wp_gate_report,
            verification_ledger_report=verification_ledger_report,
            coverage_gate_report=coverage_gate_report,
        )

    openapi_diff_report_path = first_existing_path(output_dir / "openapi-diff.json", output_dir / "openapi-diff-report.json")
    code_review_summary = run_phase3_code_review(
        output_dir=output_dir,
        implementation_bindings=implementation_bindings,
        trace_registry_final=trace_registry_final,
        openapi_diff_report=load_json_if_exists(openapi_diff_report_path),
    )
    security_audit_summary = run_phase3_security_audit(
        output_dir=output_dir,
        tech_stack_text=tech_stack_text,
    )
    code_review_metrics_path = output_dir / "code-review-metrics.json"
    security_audit_report_path = output_dir / "security-audit-checklist.json"
    mock_dependency_manifest_path = output_dir / "mock-dependency-manifest.json"
    code_review_metrics = load_json_if_exists(code_review_metrics_path) or {}
    write_text(
        mock_dependency_manifest_path,
        json.dumps(
            {
                "generated_at": utc_now_iso(),
                "summary": {
                    "mock_runtime_dependency_count": int(
                        (code_review_metrics.get("summary", {}) if isinstance(code_review_metrics, dict) else {}).get(
                            "mock_runtime_dependency_count",
                            0,
                        )
                    ),
                },
                "items": list(code_review_metrics.get("mock_runtime_dependencies", []))
                if isinstance(code_review_metrics, dict)
                else [],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    resolved_unit_test_report_path = sync_json_report_if_provided(
        unit_test_report_path,
        output_dir / "unit-test-report.json",
    )
    if resolved_unit_test_report_path is None:
        resolved_unit_test_report_path = first_existing_path(
            output_dir / "unit-test-report.json",
            output_dir / "unit-tests-report.json",
        )
    resolved_runtime_smoke_report_path = sync_json_report_if_provided(
        runtime_smoke_report_path,
        output_dir / "runtime-smoke-report.json",
    )
    if resolved_runtime_smoke_report_path is None:
        resolved_runtime_smoke_report_path = output_dir / "runtime-smoke-report.json"
    resolved_started_service_smoke_report_path = sync_json_report_if_provided(
        started_service_smoke_report_path,
        output_dir / "started-service-smoke-report.json",
    )
    if resolved_started_service_smoke_report_path is None:
        resolved_started_service_smoke_report_path = output_dir / "started-service-smoke-report.json"
    ui_prototype_fallback_report_path = first_existing_path(
        output_dir / "prototype-fallback" / "ui-prototype-fallback-report.json",
    )
    ui_ia_contract_path = first_existing_path(
        output_dir / "prototype-fallback" / "ui-ia-contract.json",
    )

    resolved_runtime_smoke_service_url = resolve_runtime_smoke_service_url(runtime_smoke_service_url)
    runtime_smoke_summary = {}
    if run_runtime_smoke and first_existing_path(output_dir / "Dockerfile") and first_existing_path(output_dir / "docker-compose.prod.yml"):
        runtime_smoke_started = start_timer()
        runtime_smoke_summary = runtime_smoke_fn(
            workspace_root=output_dir,
            output_path=resolved_runtime_smoke_report_path,
            service_url=resolved_runtime_smoke_service_url,
        )
        record_timing_segment(timing_segments, "runtime_smoke", runtime_smoke_started)
    else:
        set_timing_segment(
            timing_segments,
            "runtime_smoke",
            duration_seconds=0.0,
            status="skipped",
            run_runtime_smoke=run_runtime_smoke,
        )

    delivery_kwargs = {
        "bootstrap_report": bootstrap_report,
        "unit_test_report": load_json_if_exists(resolved_unit_test_report_path),
        "coverage_gate_report": coverage_gate_report,
        "wp_gate_report": wp_gate_report,
        "verification_ledger_report": verification_ledger_report,
        "openapi_diff_report": load_json_if_exists(openapi_diff_report_path),
        "code_review_metrics": code_review_metrics,
        "security_audit_report": load_json_if_exists(security_audit_report_path),
        "openapi_final_path": first_existing_path(output_dir / "openapi-final.yaml"),
        "api_doc_dir": first_existing_path(output_dir / "docs" / "api") or (output_dir / "docs" / "api"),
        "deploy_runbook_path": first_existing_path(output_dir / "deploy-runbook.md"),
        "dockerfile_path": first_existing_path(output_dir / "Dockerfile"),
        "compose_prod_path": first_existing_path(output_dir / "docker-compose.prod.yml"),
        "runtime_smoke_report": load_json_if_exists(resolved_runtime_smoke_report_path),
        "runtime_smoke_report_path": (
            resolved_runtime_smoke_report_path if resolved_runtime_smoke_report_path.exists() else None
        ),
        "started_service_smoke_report": load_json_if_exists(resolved_started_service_smoke_report_path),
        "started_service_smoke_report_path": (
            resolved_started_service_smoke_report_path if resolved_started_service_smoke_report_path.exists() else None
        ),
        "performance_baseline_path": first_existing_path(output_dir / "performance-baseline.json"),
        "acceptance_report_path": acceptance_report_path if acceptance_report_path.exists() else None,
        "execution_report_path": execution_report_path if execution_report_path.exists() else None,
        "trace_registry_final_path": trace_registry_final_path if trace_registry_final_path.exists() else None,
        "ui_prototype_fallback_report_path": ui_prototype_fallback_report_path,
        "ui_ia_contract_path": ui_ia_contract_path,
        "retained_proof_mode": retained_proof_mode,
        "strict_runtime_closure": strict_runtime_closure,
    }
    metadata_path = output_dir / "phase3-run-metadata.json"
    delivery_gate_started = start_timer()
    delivery, assessment_artifacts, assessment_summary = finalize_phase3_delivery_closure(
        case_name=case_name,
        version=version,
        output_dir=output_dir,
        bootstrap_report_path=bootstrap_report_path,
        bootstrap_report=bootstrap_report,
        delivery_gate_path=delivery_gate_path,
        acceptance_report_path=acceptance_report_path,
        execution_report_path=execution_report_path,
        analyze_kwargs=delivery_kwargs,
        unit_test_report_path=resolved_unit_test_report_path,
        unit_test_report=delivery_kwargs["unit_test_report"],
        coverage_gate_report_path=resolved_coverage_gate_report_path,
        coverage_gate_report=coverage_gate_report,
        openapi_diff_report_path=openapi_diff_report_path,
        openapi_diff_report=delivery_kwargs["openapi_diff_report"],
        code_review_metrics_path=code_review_metrics_path,
        code_review_metrics=delivery_kwargs["code_review_metrics"],
        security_audit_report_path=security_audit_report_path,
        security_audit_report=delivery_kwargs["security_audit_report"],
        trace_registry_final_path=trace_registry_final_path if trace_registry_final_path.exists() else None,
        trace_registry_final=trace_registry_final,
        metadata_path=metadata_path,
    )
    record_timing_segment(timing_segments, "delivery_gate", delivery_gate_started)

    return {
        "trace_registry_final_path": str(trace_registry_final_path) if trace_registry_final_path.exists() else "",
        "delivery_gate_path": str(delivery_gate_path),
        "retained_proof_mode": retained_proof_mode,
        "strict_runtime_closure": strict_runtime_closure,
        "recommended_formal_state": delivery.get("recommended_formal_state", ""),
        "mainline_assessment_paths": assessment_artifacts,
        "mainline_assessment_summary": assessment_summary,
        "phase_verdict_path": assessment_summary["phase_verdict_path"],
        "phase_verdict": assessment_summary["phase_verdict"],
        "phase_total_score": assessment_summary["phase_total_score"],
        "code_review_summary": code_review_summary,
        "security_audit_summary": security_audit_summary,
        "runtime_smoke_summary": runtime_smoke_summary,
        "runtime_smoke_service_url": resolved_runtime_smoke_service_url,
        "timing_segments": timing_segments,
    }
