#!/usr/bin/env python3
"""
Render deterministic Phase-3 delivery acceptance and execution reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_acceptance_report, localize_phase3_execution_report


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def metric(report: dict[str, Any] | None, *path: str) -> str:
    current: Any = report
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return "n/a"
        current = current[key]
    return str(current)


def first_metric(report: dict[str, Any] | None, *paths: tuple[str, ...]) -> str:
    for path in paths:
        value = metric(report, *path)
        if value != "n/a":
            return value
    return "n/a"


def bullet_lines(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def path_name(path: Path | None) -> str:
    return path.name if path else "not-provided"


def render_list(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def build_acceptance_report(
    *,
    case_name: str,
    version: str,
    delivery_gate_report: dict[str, Any],
    bootstrap_report: dict[str, Any] | None = None,
    unit_test_report: dict[str, Any] | None = None,
    coverage_gate_report: dict[str, Any] | None = None,
    openapi_diff_report: dict[str, Any] | None = None,
    code_review_metrics: dict[str, Any] | None = None,
    security_audit_report: dict[str, Any] | None = None,
    trace_registry_final: dict[str, Any] | None = None,
    output_locale: str | None = None,
) -> str:
    warnings = [str(item) for item in delivery_gate_report.get("warnings", [])]
    failures = [str(item) for item in delivery_gate_report.get("failures", [])]
    unresolved_trace_ids = []
    if trace_registry_final is not None:
        unresolved_trace_ids = [str(item) for item in trace_registry_final.get("summary", {}).get("unresolved_trace_ids", [])]

    report = f"""# Phase-3 Acceptance Report

## 1. Run Metadata
- case_name:
  - `{case_name}`
- report_version:
  - `{version}`
- mainline_profile:
  - `backend-first`
- delivery_mode:
  - `{delivery_gate_report.get('checks', {}).get('delivery_mode', 'runtime-closure')}`
- recommended_formal_state:
  - `{delivery_gate_report.get('recommended_formal_state', 'unknown')}`
- phase_complete:
  - `{yes_no(bool(delivery_gate_report.get('phase_complete', False)))}`
- phase_completion_gate:
  - `{delivery_gate_report.get('phase_completion_gate', 'unknown')}`
- frontend_contract_required:
  - `{yes_no(bool(delivery_gate_report.get('checks', {}).get('frontend_contract_required', False)))}`
- frontend_contract_deferred:
  - `{yes_no(bool(delivery_gate_report.get('checks', {}).get('frontend_contract_deferred', False)))}`
- runtime_delivery_artifacts_required:
  - `{yes_no(bool(delivery_gate_report.get('checks', {}).get('runtime_delivery_artifacts_required', True)))}`

## 2. Acceptance Summary

| Acceptance Axis | Result | Evidence |
|---|---|---|
| Bootstrap integrity | `{metric(bootstrap_report, 'overall_quality_gate')}` | endpoints=`{metric(bootstrap_report, 'checks', 'endpoint_count')}`, contract tests=`{metric(bootstrap_report, 'checks', 'contract_test_count')}` |
| Implementation gate | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('implementation_gate', False)))}` | build/lint/typecheck plus backend truth aggregated by delivery gate |
| Unit tests | `{metric(unit_test_report, 'verdict')}` | gate=`{yes_no(bool(delivery_gate_report.get('checks', {}).get('unit_test_gate', False)))}` |
| Real backend boundary | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('backend_interface_gate', False)))}` | persistence_required=`{yes_no(bool(delivery_gate_report.get('checks', {}).get('backend_persistence_truth_required', False)))}`, sql=`{yes_no(bool(delivery_gate_report.get('checks', {}).get('backend_persistence_gate', False)))}`, migration=`{yes_no(bool(delivery_gate_report.get('checks', {}).get('backend_migration_gate', False)))}` |
| Backend layered API gate (L1→L4) | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('backend_layered_api_gate', False)))}` | present=`{yes_no(bool(delivery_gate_report.get('checks', {}).get('backend_layered_api_gate_present', False)))}`, blocked_wp=`{metric(delivery_gate_report, 'checks', 'backend_layer_blocked_work_packages')}` |
| Coverage + replay | `{metric(coverage_gate_report, 'overall_quality_gate')}` | lines=`{metric(coverage_gate_report, 'checks', 'lines_pct')}`, functions=`{metric(coverage_gate_report, 'checks', 'functions_pct')}`, branches=`{metric(coverage_gate_report, 'checks', 'branches_pct')}` |
| OpenAPI consistency | `{metric(openapi_diff_report, 'verdict')}` | removed_ops=`{len((openapi_diff_report or {}).get('removed_operations', [])) if openapi_diff_report else 'n/a'}` |
| Code review | `critical={first_metric(code_review_metrics, ('summary', 'critical_findings'), ('summary', 'critical'))}` | high=`{first_metric(code_review_metrics, ('summary', 'high_findings'), ('summary', 'high'))}` |
| Security audit | `critical={first_metric(security_audit_report, ('summary', 'critical_findings'), ('summary', 'critical'))}` | report source preserved |
| Trace closure | `unresolved={len(unresolved_trace_ids)}` | source_count=`{metric(trace_registry_final, 'summary', 'source_count')}` |

## 3. Delivery Artifact Checklist

| Artifact | Present |
|---|---|
| final OpenAPI | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('openapi_final_present', False)))}` |
| API doc assets | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('api_doc_assets_present', False)))}` |
| deploy runbook | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('deploy_runbook_present', False)))}` |
| Dockerfile | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('dockerfile_present', False)))}` |
| production compose | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('compose_prod_present', False)))}` |
| runtime smoke report | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('runtime_smoke_present', False)))}` |
| performance baseline | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('performance_baseline_present', False)))}` |
| acceptance report | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('acceptance_report_present', False)))}` |
| execution report | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('execution_report_present', False)))}` |
| final trace registry | `{yes_no(bool(delivery_gate_report.get('checks', {}).get('trace_registry_final_present', False)))}` |

## 4. Remaining Gaps
{bullet_lines(failures, "no blocking gaps recorded")}

## 4.1 Backend Layer Blocking Detail
{bullet_lines([f"{layer}: {wps}" for layer, wps in (delivery_gate_report.get('checks', {}).get('backend_layer_blocking_layers', {}) or {}).items()], "no backend layered blocking recorded")}

## 5. Residual Warnings
{bullet_lines(warnings, "no residual warnings")}

## 6. Traceability Notes
{bullet_lines([f"unresolved trace: {trace_id}" for trace_id in unresolved_trace_ids], "all final trace ids are resolved")}

## 7. Completion Semantics
- `foundation-ready`: scaffold exists; no completed implementation claim.
- `implementation-ready` / `delivery-ready`: require runnable code plus executed unit, contract, scenario, and replay evidence.
- Docker-backed delivery needs green runtime smoke or an explicit equivalent validation contract.
- Bootstrap adapters and `generated-runtime.ts` are not completion proof.
- `backend-first`: deferred frontend contract evidence is optional-lane unless explicitly required.
- `retained-proof`: curated proof sets may omit deploy/runtime byproducts when omissions stay explicit.
"""
    return localize_phase3_acceptance_report(report, output_locale)


def build_execution_report(
    *,
    case_name: str,
    version: str,
    bootstrap_report_path: Path,
    delivery_gate_report_path: Path,
    bootstrap_report: dict[str, Any],
    delivery_gate_report: dict[str, Any],
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
    acceptance_report_path: Path | None = None,
    output_locale: str | None = None,
) -> str:
    failures = [str(item) for item in delivery_gate_report.get("failures", [])]
    warnings = [str(item) for item in delivery_gate_report.get("warnings", [])]
    unresolved_trace_ids = []
    if trace_registry_final is not None:
        unresolved_trace_ids = [str(item) for item in trace_registry_final.get("summary", {}).get("unresolved_trace_ids", [])]

    report = f"""# Phase-3 Execution Report

## 1. Run Metadata
- case_name:
  - `{case_name}`
- report_version:
  - `{version}`
- mainline_profile:
  - `backend-first`
- delivery_mode:
  - `{delivery_gate_report.get('checks', {}).get('delivery_mode', 'runtime-closure')}`
- current_overall_status:
  - `{delivery_gate_report.get('recommended_formal_state', 'unknown')}`
- phase_complete:
  - `{"true" if delivery_gate_report.get('phase_complete', False) else "false"}`
- phase_completion_gate:
  - `{delivery_gate_report.get('phase_completion_gate', 'unknown')}`
- frontend_contract_required:
  - `{delivery_gate_report.get('checks', {}).get('frontend_contract_required', False)}`
- frontend_contract_deferred:
  - `{delivery_gate_report.get('checks', {}).get('frontend_contract_deferred', False)}`
- runtime_delivery_artifacts_required:
  - `{delivery_gate_report.get('checks', {}).get('runtime_delivery_artifacts_required', True)}`

## 2. Evidence Inventory
- bootstrap_report:
  - `{path_name(bootstrap_report_path)}`
- delivery_gate_report:
  - `{path_name(delivery_gate_report_path)}`
- unit_test_report:
  - `{path_name(unit_test_report_path)}`
- coverage_gate_report:
  - `{path_name(coverage_gate_report_path)}`
- openapi_diff_report:
  - `{path_name(openapi_diff_report_path)}`
- code_review_metrics:
  - `{path_name(code_review_metrics_path)}`
- security_audit_report:
  - `{path_name(security_audit_report_path)}`
- trace_registry_final:
  - `{path_name(trace_registry_final_path)}`
- acceptance_report:
  - `{path_name(acceptance_report_path)}`

## 3. Gate Summary

| Gate | Result | Evidence |
|---|---|---|
| bootstrap | `{bootstrap_report.get('overall_quality_gate', 'unknown')}` | recommended_state=`{bootstrap_report.get('recommended_formal_state', 'unknown')}` |
| build/lint/typecheck + backend truth aggregate | `{"pass" if delivery_gate_report.get('checks', {}).get('implementation_gate') else "fail"}` | implementation_complete=`{delivery_gate_report.get('implementation_complete', False)}` |
| unit tests (backend hard gate) | `{metric(unit_test_report, 'verdict')}` | backend_gate=`{delivery_gate_report.get('checks', {}).get('backend_unit_test_gate', False)}` |
| real backend service boundary | `{delivery_gate_report.get('checks', {}).get('backend_interface_gate', False)}` | persistence_required=`{delivery_gate_report.get('checks', {}).get('backend_persistence_truth_required', False)}` / sql=`{delivery_gate_report.get('checks', {}).get('backend_persistence_gate', False)}` / migration=`{delivery_gate_report.get('checks', {}).get('backend_migration_gate', False)}` |
| coverage + replay | `{metric(coverage_gate_report, 'overall_quality_gate')}` | lines=`{metric(coverage_gate_report, 'checks', 'lines_pct')}` / functions=`{metric(coverage_gate_report, 'checks', 'functions_pct')}` / branches=`{metric(coverage_gate_report, 'checks', 'branches_pct')}` |
| openapi diff | `{metric(openapi_diff_report, 'verdict')}` | removed_ops=`{len((openapi_diff_report or {}).get('removed_operations', [])) if openapi_diff_report else 'n/a'}` |
| code review | `critical={first_metric(code_review_metrics, ('summary', 'critical_findings'), ('summary', 'critical'))}` | high=`{first_metric(code_review_metrics, ('summary', 'high_findings'), ('summary', 'high'))}` / metadata_only=`{first_metric(code_review_metrics, ('summary', 'metadata_only_target_count'))}` |
| security audit | `critical={first_metric(security_audit_report, ('summary', 'critical_findings'), ('summary', 'critical'))}` | source preserved |
| final delivery | `{delivery_gate_report.get('phase_completion_gate', 'unknown')}` | delivery_ready=`{delivery_gate_report.get('phase_complete', False)}` |

## 4. Traceability Closure
- source_count:
  - `{metric(trace_registry_final, 'summary', 'source_count')}`
- resolved_source_count:
  - `{metric(trace_registry_final, 'summary', 'resolved_source_count')}`
- unresolved_source_count:
  - `{metric(trace_registry_final, 'summary', 'unresolved_source_count')}`

### 4.1 Unresolved Trace IDs
{render_list([f"`{trace_id}`" for trace_id in unresolved_trace_ids], "none")}

## 5. Delivery Artifact Presence
- openapi_final_present:
  - `{delivery_gate_report.get('checks', {}).get('openapi_final_present', False)}`
- api_doc_assets_present:
  - `{delivery_gate_report.get('checks', {}).get('api_doc_assets_present', False)}`
- deploy_runbook_present:
  - `{delivery_gate_report.get('checks', {}).get('deploy_runbook_present', False)}`
- dockerfile_present:
  - `{delivery_gate_report.get('checks', {}).get('dockerfile_present', False)}`
- compose_prod_present:
  - `{delivery_gate_report.get('checks', {}).get('compose_prod_present', False)}`
- runtime_smoke_present:
  - `{delivery_gate_report.get('checks', {}).get('runtime_smoke_present', False)}`
- runtime_smoke_green:
  - `{delivery_gate_report.get('checks', {}).get('runtime_smoke_green', False)}`
- performance_baseline_present:
  - `{delivery_gate_report.get('checks', {}).get('performance_baseline_present', False)}`
- acceptance_report_present:
  - `{delivery_gate_report.get('checks', {}).get('acceptance_report_present', False)}`
- execution_report_present:
  - `{delivery_gate_report.get('checks', {}).get('execution_report_present', False)}`

## 6. Blocking Findings
{render_list(failures, "none")}

## 7. Residual Warnings
{render_list(warnings, "none")}

## 8. Completion Semantics
- `foundation-ready`: scaffold exists; no completed implementation claim.
- `implementation-ready` / `delivery-ready`: require runnable code, backend boundary evidence, backend tests, and structured verification.
- Docker-backed delivery needs runtime smoke, not build-only proof.
- Frontend gaps remain explicit warnings unless `frontend_contract_required=true`.
- Passthrough-heavy `generated-runtime.ts` layers keep the run below `delivery-ready`.
- `retained-proof`: curated proof sets may omit deploy/runtime byproducts when omissions stay explicit.
"""
    return localize_phase3_execution_report(report, output_locale)
