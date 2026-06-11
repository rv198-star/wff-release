from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.phase3_delivery_gate import analyze_phase3_delivery, build_acceptance_report, build_execution_report
from phase3.mainline_assessment import (
    emit_phase3_mainline_assessment,
    update_phase3_run_metadata_with_assessment,
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_phase3_case_reports(
    *,
    case_name: str,
    version: str,
    bootstrap_report_path: Path,
    delivery_gate_path: Path,
    acceptance_report_path: Path,
    execution_report_path: Path,
    bootstrap_report: dict[str, Any],
    delivery: dict[str, Any],
    unit_test_report_path: Path | None = None,
    unit_test_report: dict[str, Any] | None = None,
    coverage_gate_report_path: Path | None = None,
    coverage_gate_report: dict[str, Any] | None = None,
    openapi_diff_report_path: Path | None = None,
    openapi_diff_report: dict[str, Any] | None = None,
    code_review_metrics_path: Path | None = None,
    code_review_metrics: dict[str, Any] | None = None,
    security_audit_report_path: Path | None = None,
    security_audit_report: dict[str, Any] | None = None,
    trace_registry_final_path: Path | None = None,
    trace_registry_final: dict[str, Any] | None = None,
    output_locale: str | None = None,
) -> None:
    write_text(
        acceptance_report_path,
        build_acceptance_report(
            case_name=case_name,
            version=version,
            delivery_gate_report=delivery,
            bootstrap_report=bootstrap_report,
            unit_test_report=unit_test_report,
            coverage_gate_report=coverage_gate_report,
            openapi_diff_report=openapi_diff_report,
            code_review_metrics=code_review_metrics,
            security_audit_report=security_audit_report,
            trace_registry_final=trace_registry_final,
            output_locale=output_locale,
        ),
    )
    write_text(
        execution_report_path,
        build_execution_report(
            case_name=case_name,
            version=version,
            bootstrap_report_path=bootstrap_report_path,
            delivery_gate_report_path=delivery_gate_path,
            bootstrap_report=bootstrap_report,
            delivery_gate_report=delivery,
            unit_test_report_path=unit_test_report_path,
            unit_test_report=unit_test_report,
            coverage_gate_report_path=coverage_gate_report_path,
            coverage_gate_report=coverage_gate_report,
            openapi_diff_report_path=openapi_diff_report_path,
            openapi_diff_report=openapi_diff_report,
            code_review_metrics_path=code_review_metrics_path,
            code_review_metrics=code_review_metrics,
            security_audit_report_path=security_audit_report_path,
            security_audit_report=security_audit_report,
            trace_registry_final_path=trace_registry_final_path,
            trace_registry_final=trace_registry_final,
            acceptance_report_path=acceptance_report_path,
            output_locale=output_locale,
        ),
    )


def finalize_phase3_delivery_closure(
    *,
    case_name: str,
    version: str,
    output_dir: Path,
    bootstrap_report_path: Path,
    bootstrap_report: dict[str, Any],
    delivery_gate_path: Path,
    acceptance_report_path: Path,
    execution_report_path: Path,
    analyze_kwargs: dict[str, Any],
    unit_test_report_path: Path | None = None,
    unit_test_report: dict[str, Any] | None = None,
    coverage_gate_report_path: Path | None = None,
    coverage_gate_report: dict[str, Any] | None = None,
    openapi_diff_report_path: Path | None = None,
    openapi_diff_report: dict[str, Any] | None = None,
    code_review_metrics_path: Path | None = None,
    code_review_metrics: dict[str, Any] | None = None,
    security_audit_report_path: Path | None = None,
    security_audit_report: dict[str, Any] | None = None,
    trace_registry_final_path: Path | None = None,
    trace_registry_final: dict[str, Any] | None = None,
    metadata_path: Path | None = None,
    output_locale: str | None = None,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    initial_analyze_kwargs = dict(analyze_kwargs)
    delivery = analyze_phase3_delivery(**initial_analyze_kwargs)

    if case_name:
        write_phase3_case_reports(
            case_name=case_name,
            version=version,
            bootstrap_report_path=bootstrap_report_path,
            delivery_gate_path=delivery_gate_path,
            acceptance_report_path=acceptance_report_path,
            execution_report_path=execution_report_path,
            bootstrap_report=bootstrap_report,
            delivery=delivery,
            unit_test_report_path=unit_test_report_path,
            unit_test_report=unit_test_report,
            coverage_gate_report_path=coverage_gate_report_path,
            coverage_gate_report=coverage_gate_report,
            openapi_diff_report_path=openapi_diff_report_path,
            openapi_diff_report=openapi_diff_report,
            code_review_metrics_path=code_review_metrics_path,
            code_review_metrics=code_review_metrics,
            security_audit_report_path=security_audit_report_path,
            security_audit_report=security_audit_report,
            trace_registry_final_path=trace_registry_final_path,
            trace_registry_final=trace_registry_final,
            output_locale=output_locale,
        )
        delivery = analyze_phase3_delivery(
            **{
                **initial_analyze_kwargs,
                "acceptance_report_path": acceptance_report_path,
                "execution_report_path": execution_report_path if execution_report_path.exists() else None,
            }
        )
        write_phase3_case_reports(
            case_name=case_name,
            version=version,
            bootstrap_report_path=bootstrap_report_path,
            delivery_gate_path=delivery_gate_path,
            acceptance_report_path=acceptance_report_path,
            execution_report_path=execution_report_path,
            bootstrap_report=bootstrap_report,
            delivery=delivery,
            unit_test_report_path=unit_test_report_path,
            unit_test_report=unit_test_report,
            coverage_gate_report_path=coverage_gate_report_path,
            coverage_gate_report=coverage_gate_report,
            openapi_diff_report_path=openapi_diff_report_path,
            openapi_diff_report=openapi_diff_report,
            code_review_metrics_path=code_review_metrics_path,
            code_review_metrics=code_review_metrics,
            security_audit_report_path=security_audit_report_path,
            security_audit_report=security_audit_report,
            trace_registry_final_path=trace_registry_final_path,
            trace_registry_final=trace_registry_final,
            output_locale=output_locale,
        )
        delivery = analyze_phase3_delivery(
            **{
                **initial_analyze_kwargs,
                "acceptance_report_path": acceptance_report_path,
                "execution_report_path": execution_report_path,
            }
        )

    write_json(delivery_gate_path, delivery)
    assessment_artifacts, assessment_summary = emit_phase3_mainline_assessment(
        output_dir=output_dir,
        assessment=delivery["mainline_assessment"],
        case_name=case_name,
        version=version,
        output_locale=output_locale or "zh-CN",
    )

    if case_name:
        write_phase3_case_reports(
            case_name=case_name,
            version=version,
            bootstrap_report_path=bootstrap_report_path,
            delivery_gate_path=delivery_gate_path,
            acceptance_report_path=acceptance_report_path,
            execution_report_path=execution_report_path,
            bootstrap_report=bootstrap_report,
            delivery=delivery,
            unit_test_report_path=unit_test_report_path,
            unit_test_report=unit_test_report,
            coverage_gate_report_path=coverage_gate_report_path,
            coverage_gate_report=coverage_gate_report,
            openapi_diff_report_path=openapi_diff_report_path,
            openapi_diff_report=openapi_diff_report,
            code_review_metrics_path=code_review_metrics_path,
            code_review_metrics=code_review_metrics,
            security_audit_report_path=security_audit_report_path,
            security_audit_report=security_audit_report,
            trace_registry_final_path=trace_registry_final_path,
            trace_registry_final=trace_registry_final,
            output_locale=output_locale,
        )

    if metadata_path is not None and metadata_path.exists():
        update_phase3_run_metadata_with_assessment(
            metadata_path=metadata_path,
            assessment_artifacts=assessment_artifacts,
            assessment_summary=assessment_summary,
        )

    return delivery, assessment_artifacts, assessment_summary
