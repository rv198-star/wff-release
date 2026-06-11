#!/usr/bin/env python3
"""
Shared Phase-3 delivery gate CLI context.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Phase3DeliveryGateContext:
    mode: str
    output_dir: Path | None
    output_path: Path | None
    workspace_root: Path | None
    frontend_dir: Path | None
    bootstrap_report_path: Path | None
    build_report_path: Path | None
    lint_report_path: Path | None
    typecheck_report_path: Path | None
    unit_test_report_path: Path | None
    coverage_gate_report_path: Path | None
    wp_gate_report_path: Path | None
    verification_ledger_report_path: Path | None
    openapi_diff_report_path: Path | None
    code_review_metrics_path: Path | None
    behavior_static_preflight_report_path: Path | None
    security_audit_report_path: Path | None
    openapi_final_path: Path | None
    api_doc_dir: Path | None
    deploy_runbook_path: Path | None
    dockerfile_path: Path | None
    compose_prod_path: Path | None
    runtime_smoke_report_path: Path | None
    started_service_smoke_report_path: Path | None
    performance_baseline_path: Path | None
    acceptance_report_path: Path | None
    execution_report_path: Path | None
    trace_registry_final_path: Path | None
    ui_prototype_fallback_report_path: Path | None
    ui_ia_contract_path: Path | None
    productness_gate_report_path: Path | None
    baseline_openapi_path: Path | None
    candidate_openapi_path: Path | None
    implementation_bindings_path: Path | None
    coverage_json_path: Path | None
    replay_json_path: Path | None
    tech_stack_decision_path: Path | None
    title: str
    version: str
    case_name: str
    output_locale: str | None
    require_frontend_contract: bool
    retained_proof_mode: bool
    strict_runtime_closure: bool
    min_lines_pct: float
    min_functions_pct: float
    min_branches_pct: float
