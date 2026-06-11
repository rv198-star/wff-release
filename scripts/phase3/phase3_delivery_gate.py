#!/usr/bin/env python3
"""
Resolve the formal completion state of a Phase-3 implementation run.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from phase3.operable_surface_contract_metrics import evaluate_surface_contract_taxonomy
from common.output_language import localize_phase3_acceptance_report, localize_phase3_execution_report
from phase3.api_doc_generation import generate_phase3_api_docs
from phase3.agentic_repair_interrupt import (
    INTERRUPT_VERDICTS,
    build_agentic_repair_interrupt,
    render_agentic_repair_interrupt_json,
    render_agentic_repair_interrupt_markdown,
)
from phase3.code_review import run_phase3_code_review
from phase3.coverage_collection import analyze_phase3_coverage, collect_phase3_coverage
from phase3.delivery_handoff import generate_phase3_delivery_handoff
from phase3.productness_gate import run_gate as run_productness_gate
from phase3.security_audit import run_phase3_security_audit

CLI_MODES = (
    "delivery-gate",
    "delivery-handoff",
    "productness-gate",
    "api-docs",
    "code-review",
    "security-audit",
    "coverage-collection",
)


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


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def safe_load_json(path: Path | None) -> tuple[dict[str, Any] | None, str]:
    if path is None or not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None, "invalid-json"
    if not isinstance(payload, dict):
        return None, "invalid-json"
    return payload, "ok"


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


def clamp_dimension(score: int) -> int:
    return max(0, min(5, score))


def phase3_formal_state_consistent(report: dict[str, Any]) -> bool:
    checks = report.get("checks", {}) if isinstance(report, dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    state = str(report.get("recommended_formal_state", "")).strip()
    bootstrap_gate = bool(checks.get("bootstrap_gate"))
    implementation_complete = bool(report.get("implementation_complete", False))
    phase_complete = bool(report.get("phase_complete", False))
    implementation_signal_present = bool(checks.get("implementation_signal_present"))
    if not bootstrap_gate:
        return state == "blocked"
    if phase_complete:
        return state == "delivery-ready"
    if implementation_complete:
        return state == "implementation-ready"
    if implementation_signal_present:
        return state == "implementation-in-progress"
    return state == "foundation-ready"


def render_phase3_scorecard_markdown(assessment: dict[str, object]) -> str:
    lines = [
        "# Phase-3 Mainline Scorecard",
        "",
        f"- mainline_profile: `{assessment['mainline_profile']}`",
        f"- recommended_formal_state: `{assessment['recommended_formal_state']}`",
        f"- total_score: `{assessment['total_score']}` / 100",
        f"- verdict: `{assessment['verdict']}`",
        "",
        "| Dimension | Weight | Score | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in assessment["dimension_scores"]:
        notes = "; ".join(row["notes"]) if row["notes"] else "-"
        lines.append(f"| {row['label']} | {row['weight']} | {row['score']} / 5 | {notes} |")
    return "\n".join(lines).rstrip() + "\n"


def render_phase3_acceptance_matrix_markdown(assessment: dict[str, object]) -> str:
    lines = [
        "# Phase-3 Acceptance Matrix",
        "",
        f"- mainline_profile: `{assessment['mainline_profile']}`",
        f"- recommended_formal_state: `{assessment['recommended_formal_state']}`",
        f"- verdict: `{assessment['verdict']}`",
        "",
        "| Acceptance Item | Status | Why |",
        "|---|---|---|",
    ]
    for row in assessment["acceptance_rows"]:
        lines.append(f"| {row['label']} | `{row['status']}` | {row['why']} |")
    return "\n".join(lines).rstrip() + "\n"


def phase3_scope_states(delivery_gate_report: dict[str, Any], checks: dict[str, Any], failures: list[str]) -> dict[str, str]:
    runtime_closed = bool(delivery_gate_report.get("phase_complete")) and bool(delivery_gate_report.get("implementation_complete"))
    runtime_closure_state = "closed" if runtime_closed else "in-progress" if bool(checks.get("backend_packet_truth_present")) else "not-started"

    artifact_quality_gate = checks.get("artifact_assertion_quality_gate")
    if artifact_quality_gate is None:
        artifact_quality_gate = "artifact_assertion_quality_failed" not in failures
    artifact_quality_state = "pass" if bool(artifact_quality_gate) else "review-bound"

    domain_specific_count = int(checks.get("code_review_domain_specific_target_count", 0) or 0)
    runtime_kernel_count = int(checks.get("code_review_runtime_kernel_backed_target_count", 0) or 0)
    review_bound_depth_count = int(checks.get("code_review_review_bound_depth_target_count", 0) or 0)
    if domain_specific_count > 0:
        implementation_depth_state = "domain-specific"
    elif runtime_kernel_count > 0:
        implementation_depth_state = "runtime-kernel-backed"
    elif review_bound_depth_count > 0:
        implementation_depth_state = "review-bound"
    else:
        implementation_depth_state = "unknown"

    if bool(checks.get("frontend_contract_deferred")):
        frontend_scope_state = "deferred"
    elif bool(checks.get("frontend_contract_required")):
        frontend_scope_state = "required"
    elif bool(checks.get("surface_contract_gate_present")) or bool(checks.get("ui_ia_contract_present")):
        frontend_scope_state = "present"
    else:
        frontend_scope_state = "unknown"

    return {
        "runtime_closure_state": runtime_closure_state,
        "artifact_quality_state": artifact_quality_state,
        "implementation_depth_state": implementation_depth_state,
        "frontend_scope_state": frontend_scope_state,
    }


def build_phase3_mainline_assessment(*, delivery_gate_report: dict[str, Any]) -> dict[str, Any]:
    checks = delivery_gate_report.get("checks", {}) if isinstance(delivery_gate_report, dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    failures = [str(item) for item in delivery_gate_report.get("failures", [])]
    warnings = [str(item) for item in delivery_gate_report.get("warnings", [])]
    retained_proof_mode = bool(checks.get("retained_proof_mode"))
    runtime_delivery_assets_required = bool(checks.get("runtime_delivery_artifacts_required", not retained_proof_mode))

    persistence_required = bool(checks.get("backend_persistence_truth_required"))
    backend_truth_present = bool(checks.get("backend_packet_truth_present"))
    backend_interface_signal_present = bool(checks.get("backend_interface_signal_present"))
    backend_interface_gate = bool(checks.get("backend_interface_gate"))
    backend_persistence_gate = bool(checks.get("backend_persistence_gate"))
    backend_roundtrip_gate = bool(checks.get("backend_service_persistence_roundtrip_gate"))
    backend_migration_gate = bool(checks.get("backend_migration_gate"))
    frontend_contract_required = bool(checks.get("frontend_contract_required"))
    frontend_contract_deferred = bool(checks.get("frontend_contract_deferred"))
    frontend_truth_present = bool(checks.get("surface_contract_gate_present")) or bool(checks.get("ui_ia_contract_present"))
    frontend_honesty_explicit = frontend_contract_required or frontend_contract_deferred or frontend_truth_present
    formal_state_consistent = phase3_formal_state_consistent(delivery_gate_report)
    frontend_failure_present = any(item.startswith("frontend_") for item in failures)
    mainline_noise_warnings = [
        item for item in warnings if item not in {"frontend_contract_optional_lane_not_requested"}
    ]
    scope_states = phase3_scope_states(delivery_gate_report, checks, failures)
    effective_recommended_formal_state = str(delivery_gate_report.get("recommended_formal_state", ""))
    if scope_states["artifact_quality_state"] != "pass" and effective_recommended_formal_state == "delivery-ready":
        effective_recommended_formal_state = "artifact-quality-review-bound"

    verification_truth_green = (
        bool(checks.get("unit_test_gate"))
        and backend_interface_gate
        and (not persistence_required or backend_persistence_gate)
        and (not persistence_required or backend_roundtrip_gate)
        and (not persistence_required or backend_migration_gate)
    )
    startup_contract_explicit = (
        bool(checks.get("openapi_final_present"))
        and bool(checks.get("acceptance_report_present"))
        and bool(checks.get("execution_report_present"))
        and (
            not runtime_delivery_assets_required
            or (
                bool(checks.get("deploy_runbook_present"))
                and bool(checks.get("dockerfile_present"))
                and bool(checks.get("compose_prod_present"))
            )
        )
        and formal_state_consistent
    )
    verification_dimension_score = clamp_dimension(
        int(bool(checks.get("coverage_report_present")) and bool(checks.get("coverage_gate")))
        + int(backend_interface_signal_present and backend_interface_gate)
        + int(
            bool(checks.get("runtime_smoke_present")) and bool(checks.get("runtime_smoke_green"))
            if runtime_delivery_assets_required
            else bool(checks.get("acceptance_report_present"))
        )
        + int(
            bool(checks.get("dockerfile_runtime_present"))
            and bool(checks.get("compose_prod_runtime_present"))
            and bool(checks.get("delivery_docker_production_minimum"))
            if runtime_delivery_assets_required
            else bool(checks.get("execution_report_present"))
        )
        + int(
            bool(checks.get("deploy_runbook_present")) and bool(checks.get("performance_baseline_present"))
            if runtime_delivery_assets_required
            else (
                bool(checks.get("trace_registry_final_present"))
                and int(checks.get("trace_registry_gap_count", 0) or 0) == 0
            )
        )
    )
    verification_dimension_notes = [
        f"coverage_gate={'pass' if bool(checks.get('coverage_gate')) else 'not-green'}",
        f"backend_interface_gate={'pass' if backend_interface_gate else 'not-green'}",
    ]
    if runtime_delivery_assets_required:
        verification_dimension_notes.extend(
            [
                f"runtime_smoke={'green' if bool(checks.get('runtime_smoke_green')) else 'missing-or-not-green'}",
                (
                    "docker/compose runtime contract looks production-usable"
                    if bool(checks.get("dockerfile_runtime_present"))
                    and bool(checks.get("compose_prod_runtime_present"))
                    and bool(checks.get("delivery_docker_production_minimum"))
                    else "runtime delivery assets still thin"
                ),
                f"performance_baseline_present={'yes' if bool(checks.get('performance_baseline_present')) else 'no'}",
            ]
        )
    else:
        verification_dimension_notes.extend(
            [
                f"acceptance_report_present={'yes' if bool(checks.get('acceptance_report_present')) else 'no'}",
                f"execution_report_present={'yes' if bool(checks.get('execution_report_present')) else 'no'}",
                f"trace_registry_gap_count={int(checks.get('trace_registry_gap_count', 0) or 0)}",
            ]
        )
    startup_label = "startup / env / delivery gate 显式"
    if retained_proof_mode:
        startup_label = "retained proof closure semantics 显式"

    dimension_rows = [
        {
            "key": "business_correctness_and_structure_quality",
            "label": "业务正确性与结构质量",
            "weight": 25,
            "score": clamp_dimension(
                int(bool(checks.get("build_gate")) and bool(checks.get("lint_gate")) and bool(checks.get("typecheck_gate")))
                + int(bool(checks.get("unit_test_gate")))
                + int(backend_truth_present and backend_interface_gate)
                + int(bool(checks.get("backend_layered_api_gate")))
                + int(
                    bool(checks.get("code_review_report_present"))
                    and
                    int(checks.get("code_review_critical_findings", 0) or 0) == 0
                    and int(checks.get("code_review_high_findings", 0) or 0) == 0
                    and bool(checks.get("bootstrap_all_payload_typed"))
                )
            ),
            "notes": [
                f"build/lint/typecheck={'pass' if bool(checks.get('build_gate')) and bool(checks.get('lint_gate')) and bool(checks.get('typecheck_gate')) else 'not-green'}",
                f"backend_interface_gate={'pass' if backend_interface_gate else 'not-green'}",
                (
                    "backend layered API validation green"
                    if bool(checks.get("backend_layered_api_gate"))
                    else "backend layered API validation absent or not green"
                ),
                (
                    "code review high/critical findings cleared"
                    if int(checks.get("code_review_critical_findings", 0) or 0) == 0
                    and int(checks.get("code_review_high_findings", 0) or 0) == 0
                    else "code review still reports high/critical findings"
                ),
            ],
        },
        {
            "key": "data_contract_and_delivery_truth",
            "label": "数据/合同/交付真相",
            "weight": 25,
            "score": clamp_dimension(
                int(bool(checks.get("openapi_final_present")))
                + int(bool(checks.get("openapi_diff_report_present")) and bool(checks.get("openapi_diff_pass")))
                + int((not persistence_required) or backend_persistence_gate)
                + int((not persistence_required) or backend_migration_gate)
                + int(bool(checks.get("trace_registry_final_present")) and int(checks.get("trace_registry_gap_count", 0) or 0) == 0)
            ),
            "notes": [
                f"openapi_final_present={'yes' if bool(checks.get('openapi_final_present')) else 'no'}",
                f"openapi_diff_pass={'yes' if bool(checks.get('openapi_diff_pass')) else 'no'}",
                (
                    "persistence truth not required on current backend path"
                    if not persistence_required
                    else f"persistence/migration={'green' if backend_persistence_gate and backend_migration_gate else 'not-green'}"
                ),
                f"trace_registry_gap_count={int(checks.get('trace_registry_gap_count', 0) or 0)}",
            ],
        },
        {
            "key": "verification_operability_and_failure_handling",
            "label": "验证/可运维/失败处理",
            "weight": 25,
            "score": verification_dimension_score,
            "notes": verification_dimension_notes,
        },
        {
            "key": "phase4_consumability",
            "label": "P4 可消费性",
            "weight": 15,
            "score": clamp_dimension(
                int(bool(delivery_gate_report.get("implementation_complete", False)))
                + int(bool(delivery_gate_report.get("phase_complete", False)))
                + int(bool(checks.get("delivery_artifacts_complete")))
                + int(bool(checks.get("acceptance_report_present")) and bool(checks.get("execution_report_present")))
                + int(bool(checks.get("trace_registry_final_present")) and int(checks.get("trace_registry_gap_count", 0) or 0) == 0)
            ),
            "notes": [
                f"implementation_complete={'yes' if bool(delivery_gate_report.get('implementation_complete', False)) else 'no'}",
                f"phase_complete={'yes' if bool(delivery_gate_report.get('phase_complete', False)) else 'no'}",
                f"delivery_artifacts_complete={'yes' if bool(checks.get('delivery_artifacts_complete')) else 'no'}",
                (
                    "P4 can verify a real backend package"
                    if bool(checks.get("acceptance_report_present"))
                    and bool(checks.get("execution_report_present"))
                    and bool(checks.get("trace_registry_final_present"))
                    else "P4 inputs are still incomplete"
                ),
            ],
        },
        {
            "key": "evidence_honesty_and_mainline_discipline",
            "label": "证据诚实度与主线纪律",
            "weight": 10,
            "score": clamp_dimension(
                int(frontend_honesty_explicit)
                + int((not bool(checks.get("ui_fallback_generated"))) or (not frontend_contract_required))
                + int(bool(checks.get("bootstrap_all_payload_typed")))
                + int(int(checks.get("code_review_mock_runtime_dependency_count", 0) or 0) == 0)
                + int(formal_state_consistent and len(mainline_noise_warnings) <= 2)
            ),
            "notes": [
                (
                    "frontend optional lane is explicitly deferred"
                    if frontend_contract_deferred and not frontend_contract_required
                    else "frontend truth is explicitly present"
                    if frontend_truth_present
                    else "frontend contract is explicitly required"
                    if frontend_contract_required
                    else "frontend defer semantics are still implicit"
                ),
                f"ui_fallback_generated={'yes' if bool(checks.get('ui_fallback_generated')) else 'no'}",
                f"mock_runtime_dependency_count={int(checks.get('code_review_mock_runtime_dependency_count', 0) or 0)}",
                f"formal_state_consistent={'yes' if formal_state_consistent else 'no'}",
            ],
        },
    ]

    if persistence_required and backend_persistence_gate and backend_roundtrip_gate and backend_migration_gate:
        db_truth_status = "PASS"
        db_truth_why = "persistence behavior, roundtrip truth, and migration execution are all green"
    elif not persistence_required and backend_interface_gate:
        db_truth_status = "PASS"
        db_truth_why = "the current backend path is runtime-backed and does not require stronger persistence truth"
    elif not persistence_required and bool(checks.get("implementation_signal_present")):
        db_truth_status = "REVIEW-BOUND"
        db_truth_why = "current backend path does not demand stronger persistence truth yet, but runtime-backed proof is still limited"
    elif not persistence_required:
        db_truth_status = "REVIEW-BOUND"
        db_truth_why = "migration/schema assets exist, but executable persistence truth has not been proven yet"
    elif backend_truth_present or backend_interface_signal_present:
        db_truth_status = "REVIEW-BOUND"
        db_truth_why = "backend runtime truth exists, but persistence/migration proof is still incomplete"
    else:
        db_truth_status = "BLOCKED"
        db_truth_why = "migration/persistence truth is still too thin to trust database behavior"

    if backend_truth_present and backend_interface_gate:
        boundary_status = "PASS"
        boundary_why = "backend packet truth exists and the service boundary gate is green"
    elif backend_truth_present or backend_interface_signal_present:
        boundary_status = "REVIEW-BOUND"
        boundary_why = "a backend boundary signal exists, but the executed service boundary proof is still not fully green"
    else:
        boundary_status = "BLOCKED"
        boundary_why = "backend still looks too close to scaffold because no runnable service boundary truth is present"

    if bool(checks.get("openapi_final_present")) and bool(checks.get("openapi_diff_pass")):
        contract_status = "PASS"
        contract_why = "final OpenAPI exists and the implementation contract diff is green"
    elif bool(checks.get("openapi_final_present")) or bool(checks.get("openapi_diff_pass")):
        contract_status = "REVIEW-BOUND"
        contract_why = "contract truth is partially explicit, but freeze/implementation closure is still incomplete"
    else:
        contract_status = "BLOCKED"
        contract_why = "API contract is still too unstable for downstream verification"

    if verification_truth_green and bool(checks.get("coverage_gate")):
        verification_status = "PASS"
        verification_why = "service boundary, persistence truth, unit tests, and coverage evidence are all present"
    elif (
        bool(checks.get("backend_unit_test_signal_present"))
        or backend_interface_signal_present
        or bool(checks.get("coverage_gate"))
        or bool(checks.get("runtime_smoke_present"))
    ):
        verification_status = "REVIEW-BOUND"
        verification_why = "verification evidence exists, but it is still not strong enough to call the backend fully proven"
    else:
        verification_status = "BLOCKED"
        verification_why = "runtime-backed verification evidence is still missing"

    if (
        startup_contract_explicit
        and bool(checks.get("acceptance_report_present"))
        and bool(checks.get("execution_report_present"))
    ):
        startup_status = "PASS"
        startup_why = (
            "startup/env assets exist and the formal delivery state is explicit"
            if runtime_delivery_assets_required
            else "retained proof closure semantics are explicit without depending on runtime/deploy byproducts"
        )
    elif startup_contract_explicit:
        startup_status = "REVIEW-BOUND"
        startup_why = (
            "startup/env semantics are explicit, but delivery closure artifacts are not complete yet"
            if runtime_delivery_assets_required
            else "retained proof semantics are explicit, but closure artifacts are still incomplete"
        )
    else:
        startup_status = "BLOCKED"
        startup_why = (
            "startup/env/delivery gate semantics are still too implicit"
            if runtime_delivery_assets_required
            else "retained proof closure semantics are still too implicit"
        )

    if frontend_honesty_explicit and not frontend_failure_present:
        frontend_status = "PASS"
        frontend_why = (
            "frontend contract truth is explicit and does not silently pollute the backend mainline"
            if frontend_truth_present
            else "frontend defer/require semantics are explicit and do not silently pollute the backend mainline"
        )
    elif frontend_honesty_explicit:
        frontend_status = "REVIEW-BOUND"
        frontend_why = "frontend state is explicit, but frontend-side issues are still leaking into the current package"
    else:
        frontend_status = "BLOCKED"
        frontend_why = "frontend omission is not explicitly classified as required or deferred"

    acceptance_rows = [
        {
            "key": "migration_and_database_truth",
            "label": "可执行 migration 与数据库真相存在",
            "status": db_truth_status,
            "why": db_truth_why,
        },
        {
            "key": "backend_service_boundary",
            "label": "可运行 backend service boundary 存在",
            "status": boundary_status,
            "why": boundary_why,
        },
        {
            "key": "api_contract_frozen_and_implemented",
            "label": "API contract 已冻结并实现",
            "status": contract_status,
            "why": contract_why,
        },
        {
            "key": "service_and_persistence_verification",
            "label": "service + persistence verification evidence 存在",
            "status": verification_status,
            "why": verification_why,
        },
        {
            "key": "startup_env_and_delivery_gate_explicit",
            "label": startup_label,
            "status": startup_status,
            "why": startup_why,
        },
        {
            "key": "frontend_gap_honestly_marked",
            "label": "frontend 缺失被诚实标记",
            "status": frontend_status,
            "why": frontend_why,
        },
    ]

    total_score = round(sum((row["score"] / 5) * row["weight"] for row in dimension_rows), 1)
    blockers_count = sum(1 for row in acceptance_rows if row["status"] == "BLOCKED")
    review_bound_items_count = sum(1 for row in acceptance_rows if row["status"] == "REVIEW-BOUND")
    min_dimension_score = min((row["score"] for row in dimension_rows), default=0)

    if effective_recommended_formal_state.strip() == "blocked":
        verdict = "BLOCKED"
    elif blockers_count > 0 or total_score < 70:
        verdict = "RETURN-REMEDIATE"
    elif total_score >= 80 and min_dimension_score >= 3:
        verdict = "PASS with review-bound items" if review_bound_items_count > 0 else "PASS"
    else:
        verdict = "PASS with review-bound items"

    return {
        "phase": "P3",
        "mainline_profile": "backend-first",
        "delivery_mode": "retained-proof" if retained_proof_mode else "runtime-closure",
        "recommended_formal_state": effective_recommended_formal_state,
        **scope_states,
        "dimension_scores": dimension_rows,
        "acceptance_rows": acceptance_rows,
        "total_score": total_score,
        "verdict": verdict,
        "review_bound_items_count": review_bound_items_count,
        "blockers_count": blockers_count,
        "warning_count": len(warnings),
        "failure_count": len(failures),
        "phase_complete": bool(delivery_gate_report.get("phase_complete", False)),
        "implementation_complete": bool(delivery_gate_report.get("implementation_complete", False)),
        "formal_state_consistent": formal_state_consistent,
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
    output_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = output_dir / "phase-mainline-scorecard.md"
    acceptance_matrix_path = output_dir / "phase-acceptance-matrix.md"
    verdict_path = output_dir / "phase-verdict.json"
    repair_interrupt_path = output_dir / "agentic-repair-interrupt.json"
    repair_interrupt_markdown_path = output_dir / "agentic-repair-interrupt.md"
    repair_interrupt = build_agentic_repair_interrupt(
        case_name=case_name,
        version=version,
        assessment=assessment,
        human_review=human_review,
    )
    scorecard_path.write_text(render_phase3_scorecard_markdown(assessment), encoding="utf-8")
    acceptance_matrix_path.write_text(render_phase3_acceptance_matrix_markdown(assessment), encoding="utf-8")
    verdict_path.write_text(json.dumps(assessment, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    repair_interrupt_path.write_text(render_agentic_repair_interrupt_json(repair_interrupt), encoding="utf-8")
    repair_interrupt_markdown_path.write_text(
        render_agentic_repair_interrupt_markdown(repair_interrupt, output_locale=output_locale),
        encoding="utf-8",
    )
    return {
        "scorecard_path": str(scorecard_path),
        "acceptance_matrix_path": str(acceptance_matrix_path),
        "verdict_path": str(verdict_path),
        "agentic_repair_interrupt_path": str(repair_interrupt_path),
        "agentic_repair_interrupt_markdown_path": str(repair_interrupt_markdown_path),
        "agentic_repair_interrupt_required": str(bool(repair_interrupt.get("interrupt_required"))).lower(),
        "agentic_repair_interrupt_packet_count": str(
            int(repair_interrupt.get("summary", {}).get("repair_packet_count", 0) or 0)
        ),
    }


def build_phase3_mainline_assessment_summary(
    *,
    assessment: dict[str, Any],
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    artifact_paths = artifact_paths or {}
    return {
        "phase": str(assessment.get("phase", "P3")).strip() or "P3",
        "mainline_profile": str(assessment.get("mainline_profile", "backend-first")).strip() or "backend-first",
        "recommended_formal_state": str(assessment.get("recommended_formal_state", "")).strip(),
        "phase_verdict": str(assessment.get("verdict", "")).strip(),
        "runtime_closure_state": str(assessment.get("runtime_closure_state", "")).strip(),
        "artifact_quality_state": str(assessment.get("artifact_quality_state", "")).strip(),
        "implementation_depth_state": str(assessment.get("implementation_depth_state", "")).strip(),
        "frontend_scope_state": str(assessment.get("frontend_scope_state", "")).strip(),
        "phase_total_score": assessment.get("total_score"),
        "review_bound_items_count": int(assessment.get("review_bound_items_count", 0) or 0),
        "blockers_count": int(assessment.get("blockers_count", 0) or 0),
        "warning_count": int(assessment.get("warning_count", 0) or 0),
        "failure_count": int(assessment.get("failure_count", 0) or 0),
        "phase_complete": bool(assessment.get("phase_complete", False)),
        "implementation_complete": bool(assessment.get("implementation_complete", False)),
        "phase_scorecard_path": str(artifact_paths.get("scorecard_path", "")).strip(),
        "phase_acceptance_matrix_path": str(artifact_paths.get("acceptance_matrix_path", "")).strip(),
        "phase_verdict_path": str(artifact_paths.get("verdict_path", "")).strip(),
        "agentic_repair_interrupt_path": str(artifact_paths.get("agentic_repair_interrupt_path", "")).strip(),
        "agentic_repair_interrupt_markdown_path": str(
            artifact_paths.get("agentic_repair_interrupt_markdown_path", "")
        ).strip(),
        "agentic_repair_interrupt_required": (
            str(artifact_paths.get("agentic_repair_interrupt_required", "")).strip().lower() == "true"
            or str(assessment.get("verdict", "")).strip() in INTERRUPT_VERDICTS
            or int(assessment.get("blockers_count", 0) or 0) > 0
        ),
        "agentic_repair_interrupt_packet_count": int(
            str(artifact_paths.get("agentic_repair_interrupt_packet_count", "0")).strip() or 0
        ),
    }


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
- `foundation-ready` means the Phase-3 contract/test/scaffold package exists; it is not a completed implementation claim.
- `implementation-ready` and `delivery-ready` require runnable implementation code plus executed unit tests and executed contract/scenario/replay verification evidence.
- When Docker assets exist, `delivery-ready` should also include green runtime smoke evidence captured from that containerized environment or an explicit equivalent runtime-validation contract.
- Generated adapters, passthrough delegates, or `generated-runtime.ts` may exist as bootstrap assets, but they do not justify a completion claim on their own.
- In the `backend-first` mainline, frontend contract evidence may be explicitly deferred; when deferred, missing surface-contract evidence is an optional-lane condition rather than a mainline blocker.
- In `retained-proof` mode, intentionally curated code/method proof sets may omit deploy/runtime byproducts and should not be downgraded for that omission alone.
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
- `foundation-ready` means the foundation package is structurally complete enough to start implementation work; it is not a completion claim.
- `implementation-ready` / `delivery-ready` require runnable implementation code, backend interface evidence, backend unit tests, and structured verification results in addition to build/lint/typecheck green.
- When Docker assets exist, `delivery-ready` should be backed by containerized runtime smoke evidence rather than build-only proof.
- Frontend unit/component verification remains important evidence, but limited gaps may surface here as explicit warnings and Phase-4 follow-up rather than silently blocking backend completion.
- In the `backend-first` mainline, missing frontend contract evidence is only blocking when `frontend_contract_required=true`.
- If controller/service/repository layers still operate mainly as passthrough adapters into `generated-runtime.ts`, the run should remain below `delivery-ready`.
- In `retained-proof` mode, a curated proof set may intentionally omit deploy/runtime byproducts; those omissions should stay explicit but not be treated as runtime-closure blockers.
"""
    return localize_phase3_execution_report(report, output_locale)


def path_exists(path: Path | None) -> bool:
    return bool(path and path.exists())


def file_sha256(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dir_has_entries(path: Path | None) -> bool:
    return bool(path and path.exists() and path.is_dir() and any(path.iterdir()))


def file_contains_all(path: Path | None, required_tokens: tuple[str, ...]) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return all(token in document for token in required_tokens)


def dockerfile_has_runtime_entrypoint(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return "CMD [" in document or "ENTRYPOINT [" in document


def dockerfile_has_multistage_build(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    from_count = len([line for line in document.splitlines() if line.strip().lower().startswith("from ")])
    return from_count >= 2


def dockerfile_has_non_root_user(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    user_lines = [line.strip() for line in document.splitlines() if line.strip().lower().startswith("user ")]
    if not user_lines:
        return False
    effective_user = user_lines[-1].split(None, 1)[1].strip().strip("\"'")
    return effective_user.lower() not in {"root", "0"}


def dockerfile_has_healthcheck(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return "HEALTHCHECK" in document.upper()


def is_placeholder_value(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return normalized in {"", "replace-me", "changeme", "example", "placeholder"}


def contains_embedded_url_credentials(value: str) -> bool:
    return bool(re.search(r"[a-z][a-z0-9+.-]*://[^:\s\"'}]+:[^@\s\"'}]+@", value, re.IGNORECASE))


def extract_compose_default(value: str) -> str:
    match = re.search(r"\$\{[^}:]+:-([^}]*)\}", value)
    return match.group(1).strip() if match else ""


def delivery_asset_has_hardcoded_secrets(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    url_keys = {"DATABASE_URL", "REDIS_URL", "AMQP_URL", "BROKER_URL"}
    secret_suffixes = ("PASSWORD", "SECRET", "TOKEN", "KEY")
    for raw_line in document.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith(("ENV ", "ARG ")):
            _, _, remainder = line.partition(" ")
            key, sep, value = remainder.partition("=")
            if not sep:
                continue
            normalized_key = key.strip().upper()
            normalized_value = value.strip()
            if any(normalized_key.endswith(suffix) for suffix in secret_suffixes):
                if normalized_value.startswith("${"):
                    default_value = extract_compose_default(normalized_value)
                    if default_value and not is_placeholder_value(default_value):
                        return True
                    continue
                if not is_placeholder_value(normalized_value):
                    return True
            if normalized_key in url_keys:
                if normalized_value.startswith("${"):
                    default_value = extract_compose_default(normalized_value)
                    if default_value and contains_embedded_url_credentials(default_value):
                        return True
                    continue
                if contains_embedded_url_credentials(normalized_value):
                    return True
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        normalized_key = key.strip().strip("\"'").upper()
        normalized_value = value.strip()
        if any(normalized_key.endswith(suffix) for suffix in secret_suffixes):
            if normalized_value.startswith("${"):
                default_value = extract_compose_default(normalized_value)
                if default_value and not is_placeholder_value(default_value):
                    return True
                continue
            if not is_placeholder_value(normalized_value):
                return True
        if normalized_key in url_keys:
            if normalized_value.startswith("${"):
                default_value = extract_compose_default(normalized_value)
                if default_value and contains_embedded_url_credentials(default_value):
                    return True
                continue
            if contains_embedded_url_credentials(normalized_value):
                return True
    return False


def compose_has_startable_runtime(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    if "services:" not in document or "api:" not in document:
        return False
    if "healthcheck:" not in document:
        return False
    return any(token in document for token in ("command:", "entrypoint:", "image:", "build:"))


def report_is_pass(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    for key in ("overall_quality_gate", "phase_completion_gate", "verdict", "status", "gate"):
        value = report.get(key)
        if value is not None:
            return str(value).lower() == "pass"
    for key in ("success", "ok"):
        value = report.get(key)
        if value is not None:
            return bool(value)
    return False


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


def bootstrap_report_is_green(report: dict[str, Any] | None) -> bool:
    if report_is_pass(report):
        return True
    if not isinstance(report, dict):
        return False
    overall_status = str(report.get("overall_status") or "").strip().lower()
    if overall_status in {"ready", "pass"}:
        return True
    recommended_state = str(report.get("recommended_formal_state") or "").strip().lower()
    return recommended_state in {"toolchain-ready", "ready"}


def bootstrap_toolchain_status_fields(report: dict[str, Any] | None) -> tuple[str, str]:
    if not isinstance(report, dict):
        return "unknown", "initial-bootstrap-snapshot-before-runtime-validation"
    checks = report.get("checks", {}) if isinstance(report.get("checks", {}), dict) else {}
    status = str(checks.get("toolchain_bootstrap_status", "")).strip()
    if not status:
        status = str(report.get("overall_status") or report.get("status") or "unknown").strip() or "unknown"
    basis = str(checks.get("toolchain_bootstrap_status_basis", "")).strip()
    if not basis:
        basis = "initial-bootstrap-snapshot-before-runtime-validation"
    return status, basis


def ledger_step_is_pass(report: dict[str, Any] | None, step: str) -> bool:
    if not report:
        return False
    latest_verdicts = [
        str(row.get("step_verdicts", {}).get(step, "")).strip().lower()
        for row in latest_packet_rows(report)
        if isinstance(row.get("step_verdicts"), dict) and str(row.get("step_verdicts", {}).get(step, "")).strip()
    ]
    if latest_verdicts:
        return all(verdict == "pass" for verdict in latest_verdicts) and not any(
            verdict == "fail" for verdict in latest_verdicts
        )
    aggregated = report.get("aggregated", {})
    if not isinstance(aggregated, dict):
        return False
    step_status = aggregated.get("step_status", {})
    if not isinstance(step_status, dict):
        return False
    return str(step_status.get(step, "")).lower() == "pass"


def ledger_step_present(report: dict[str, Any] | None, step: str) -> bool:
    if not report:
        return False
    if any(
        isinstance(row.get("step_verdicts"), dict) and str(row.get("step_verdicts", {}).get(step, "")).strip()
        for row in latest_packet_rows(report)
    ):
        return True
    aggregated = report.get("aggregated", {})
    if not isinstance(aggregated, dict):
        return False
    step_status = aggregated.get("step_status", {})
    if not isinstance(step_status, dict):
        return False
    if str(step_status.get(step, "")).strip().lower() in {"pass", "fail"}:
        return True
    verification_timing = aggregated.get("verification_timing", {})
    if not isinstance(verification_timing, dict):
        return False
    step_duration_ms = verification_timing.get("step_duration_ms", {})
    if not isinstance(step_duration_ms, dict):
        return False
    step_row = step_duration_ms.get(step, {})
    if not isinstance(step_row, dict):
        return False
    sample_count = step_row.get("sample_count", 0)
    return isinstance(sample_count, (int, float)) and int(sample_count) > 0


def latest_packet_rows(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    latest_by_packet = report.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict):
        return []
    return [row for row in latest_by_packet.values() if isinstance(row, dict)]


def packet_lane(packet_id: str) -> str:
    normalized = str(packet_id).strip().lower()
    if ":" not in normalized:
        return ""
    return normalized.rsplit(":", 1)[-1]


def lane_packet_rows(report: dict[str, Any] | None, lane: str) -> list[dict[str, Any]]:
    normalized_lane = str(lane).strip().lower()
    return [
        row
        for row in latest_packet_rows(report)
        if packet_lane(str(row.get("packet_id", "")).strip()) == normalized_lane
    ]


def lane_step_present(report: dict[str, Any] | None, lane: str, step: str) -> bool:
    for row in lane_packet_rows(report, lane):
        step_verdicts = row.get("step_verdicts", {})
        if isinstance(step_verdicts, dict) and str(step_verdicts.get(step, "")).strip():
            return True
    return False


def lane_step_is_pass(report: dict[str, Any] | None, lane: str, step: str) -> bool:
    verdicts = []
    for row in lane_packet_rows(report, lane):
        step_verdicts = row.get("step_verdicts", {})
        if not isinstance(step_verdicts, dict):
            continue
        verdict = str(step_verdicts.get(step, "")).strip().lower()
        if verdict:
            verdicts.append(verdict)
    if not verdicts:
        return False
    return all(verdict == "pass" for verdict in verdicts) and not any(verdict == "fail" for verdict in verdicts)


def successful_backend_rows(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        row
        for row in lane_packet_rows(report, "backend")
        if str(row.get("overall_verdict", "")).strip().lower() == "pass"
    ]


def backend_truth_rollup(report: dict[str, Any] | None) -> dict[str, Any]:
    rows = successful_backend_rows(report)
    if not rows:
        return {
            "packet_count": 0,
            "service_boundary_signal_present": False,
            "service_boundary_truth": False,
            "requires_persistence_truth": False,
            "sql_persistence_truth": False,
            "service_persistence_roundtrip_truth": False,
            "migration_execution": False,
            "public_contract_skeleton_required": False,
            "public_contract_skeleton_truth": True,
            "public_contract_risk_tiers": [],
            "api_evidence_linkage_truth": True,
            "state_isolation_values": [],
            "reentry_policy_values": [],
            "rerun_proof_values": [],
            "persistence_reentry_evidence_present": False,
            "persistence_reentry_truth": True,
            "missing_truths": [],
        }

    service_boundary_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("service_boundary_truth"))
        for row in rows
    )
    requires_persistence_truth = any(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
        for row in rows
    )
    sql_persistence_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("sql_persistence_truth"))
        for row in rows
        if bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
    )
    service_persistence_roundtrip_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("service_persistence_roundtrip_truth"))
        for row in rows
        if bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
    )
    migration_execution = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("migration_execution"))
        for row in rows
        if bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
    )
    public_contract_skeleton_required = any(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("public_contract_skeleton_required"))
        for row in rows
    )
    public_contract_skeleton_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("public_contract_skeleton_truth"))
        for row in rows
        if bool(row.get("backend_evidence", {}).get("public_contract_skeleton_required"))
    )
    public_contract_risk_tiers = sorted(
        {
            str(row.get("backend_evidence", {}).get("public_contract_risk_tier", "")).strip()
            for row in rows
            if isinstance(row.get("backend_evidence"), dict)
            and str(row.get("backend_evidence", {}).get("public_contract_risk_tier", "")).strip()
        }
    )
    api_evidence_linkage_truth = all(
        isinstance(row.get("backend_evidence"), dict)
        and bool(row.get("backend_evidence", {}).get("api_evidence_linkage_truth", True))
        for row in rows
    )
    state_isolation_values = sorted(
        {
            str(row.get("backend_evidence", {}).get("state_isolation", "")).strip().lower()
            for row in rows
            if isinstance(row.get("backend_evidence"), dict)
            and str(row.get("backend_evidence", {}).get("state_isolation", "")).strip()
        }
    )
    reentry_policy_values = sorted(
        {
            str(row.get("backend_evidence", {}).get("reentry_policy", "")).strip().lower()
            for row in rows
            if isinstance(row.get("backend_evidence"), dict)
            and str(row.get("backend_evidence", {}).get("reentry_policy", "")).strip()
        }
    )
    rerun_proof_values = sorted(
        {
            str(row.get("backend_evidence", {}).get("rerun_proof", "")).strip().lower()
            for row in rows
            if isinstance(row.get("backend_evidence"), dict)
            and str(row.get("backend_evidence", {}).get("rerun_proof", "")).strip()
        }
    )
    persistence_reentry_evidence_present = any(
        isinstance(row.get("backend_evidence"), dict)
        and any(key in row.get("backend_evidence", {}) for key in ("state_isolation", "reentry_policy", "rerun_proof"))
        for row in rows
    )
    isolated_state_values = {"isolated", "ephemeral", "transactional", "per-test", "per-run"}
    restore_policy_values = {"init-restore", "restore", "reset", "rollback", "truncate-restore", "migration-reset"}
    repeatable_rerun_values = {"rerun-pass", "repeat-pass", "multi-run-pass", "idempotent-rerun", "reentrant"}
    persistence_reentry_truth = True
    if requires_persistence_truth and persistence_reentry_evidence_present:
        persistence_reentry_truth = (
            bool(set(state_isolation_values) & isolated_state_values)
            and bool(set(reentry_policy_values) & restore_policy_values)
            and bool(set(rerun_proof_values) & repeatable_rerun_values)
        )
    missing_truths: list[str] = []
    if not service_boundary_truth:
        missing_truths.append("service_boundary_truth")
    if requires_persistence_truth and not sql_persistence_truth:
        missing_truths.append("sql_persistence_truth")
    if requires_persistence_truth and not service_persistence_roundtrip_truth:
        missing_truths.append("service_persistence_roundtrip_truth")
    if requires_persistence_truth and not migration_execution:
        missing_truths.append("migration_execution")
    if public_contract_skeleton_required and not public_contract_skeleton_truth:
        missing_truths.append("public_contract_skeleton_truth")
    if requires_persistence_truth and not persistence_reentry_truth:
        missing_truths.append("persistence_reentry_truth")
    if not api_evidence_linkage_truth:
        missing_truths.append("api_evidence_linkage_truth")
    return {
        "packet_count": len(rows),
        "service_boundary_signal_present": True,
        "service_boundary_truth": service_boundary_truth,
        "requires_persistence_truth": requires_persistence_truth,
        "sql_persistence_truth": sql_persistence_truth,
        "service_persistence_roundtrip_truth": service_persistence_roundtrip_truth,
        "migration_execution": migration_execution,
        "public_contract_skeleton_required": public_contract_skeleton_required,
        "public_contract_skeleton_truth": public_contract_skeleton_truth,
        "public_contract_risk_tiers": public_contract_risk_tiers,
        "api_evidence_linkage_truth": api_evidence_linkage_truth,
        "state_isolation_values": state_isolation_values,
        "reentry_policy_values": reentry_policy_values,
        "rerun_proof_values": rerun_proof_values,
        "persistence_reentry_evidence_present": persistence_reentry_evidence_present,
        "persistence_reentry_truth": persistence_reentry_truth,
        "missing_truths": missing_truths,
    }


def first_int(report: dict[str, Any] | None, *paths: tuple[str, ...]) -> int:
    if not report:
        return 0
    for path in paths:
        current: Any = report
        matched = True
        for key in path:
            if not isinstance(current, dict) or key not in current:
                matched = False
                break
            current = current[key]
        if matched and isinstance(current, (int, float)):
            return int(current)
    return 0


def list_gap_count(report: dict[str, Any] | None, keys: set[str]) -> int:
    if not report:
        return 0
    pending: list[Any] = [report]
    count = 0
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in keys and isinstance(value, list):
                    count += len(value)
                else:
                    pending.append(value)
        elif isinstance(current, list):
            pending.extend(current)
    return count


def is_unexecutable_contract_trace_gap(row: dict[str, Any]) -> bool:
    source_type = str(row.get("source_type") or "").strip().lower()
    if source_type != "contract-trace":
        return False
    if any(str(item).strip() for item in row.get("test_targets", []) if item is not None):
        return False
    final_resolution = str(row.get("final_resolution") or "").strip().lower()
    binding_status = str(row.get("binding_status") or "").strip().lower()
    if final_resolution:
        return final_resolution == "unresolved"
    return binding_status in {"suggested", "unresolved"}


def trace_registry_blocking_gap_count(report: dict[str, Any] | None) -> int:
    if not report:
        return 0
    rows = report.get("rows", []) if isinstance(report, dict) else []
    if isinstance(rows, list):
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            final_resolution = str(row.get("final_resolution") or "").strip().lower()
            binding_status = str(row.get("binding_status") or "").strip().lower()
            if final_resolution:
                if final_resolution != "unresolved":
                    continue
            elif binding_status not in {"suggested", "unresolved"}:
                continue
            if is_unexecutable_contract_trace_gap(row):
                continue
            count += 1
        return count
    return list_gap_count(
        report,
        {
            "unbound_trace_ids",
            "unresolved_trace_ids",
            "missing_trace_ids",
            "unmatched_trace_ids",
            "remaining_trace_ids",
        },
    )


def ui_ia_contract_valid(path: Path | None) -> tuple[bool, dict[str, Any]]:
    if path is None or not path.exists():
        return False, {"reason": "missing"}
    payload, status = safe_load_json(path)
    if status != "ok" or not isinstance(payload, dict):
        return False, {"reason": "invalid-json"}
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return False, {"reason": "pages-missing"}
    required_page_keys = {
        "data_required",
        "data_presentation",
        "display_fields",
        "user_inputs",
        "actions_and_transitions",
        "state_conditions",
        "field_source_mapping",
        "page_blueprint_type",
        "primary_work_region",
        "secondary_support_regions",
        "dominant_component_pattern",
        "action_model",
    }
    has_operable_flow = False
    checked_pages = 0
    generic_shell_page_ids: list[str] = []
    generic_shell_section_ids = {
        "business-summary",
        "filters-selectors",
        "working-list",
        "detail-reading-chain",
        "action-feedback",
        "state-honesty",
    }
    allowed_action_input_sources = {"user-input", "workflow-context", "response-binding", "auth-session"}
    for page in pages:
        if not isinstance(page, dict):
            continue
        checked_pages += 1
        if not required_page_keys.issubset(page.keys()):
            return False, {"reason": "required-keys-missing", "page_id": page.get("page_id")}
        if not str(page.get("page_blueprint_type", "")).strip():
            return False, {"reason": "page-blueprint-missing", "page_id": page.get("page_id")}
        if not str(page.get("primary_work_region", "")).strip():
            return False, {"reason": "primary-work-region-missing", "page_id": page.get("page_id")}
        secondary_support_regions = page.get("secondary_support_regions")
        if not isinstance(secondary_support_regions, list) or not [item for item in secondary_support_regions if str(item).strip()]:
            return False, {"reason": "secondary-support-regions-missing", "page_id": page.get("page_id")}
        if not str(page.get("dominant_component_pattern", "")).strip():
            return False, {"reason": "dominant-component-pattern-missing", "page_id": page.get("page_id")}
        if not str(page.get("action_model", "")).strip():
            return False, {"reason": "action-model-missing", "page_id": page.get("page_id")}
        display_fields = page.get("display_fields")
        if not isinstance(display_fields, list):
            return False, {"reason": "display-fields-invalid", "page_id": page.get("page_id")}
        if page.get("data_required") and not display_fields:
            return False, {"reason": "display-fields-missing", "page_id": page.get("page_id")}
        sections = page.get("sections")
        if isinstance(sections, list):
            section_ids = {
                str(item.get("section_id", "")).strip()
                for item in sections
                if isinstance(item, dict) and str(item.get("section_id", "")).strip()
            }
            if section_ids and section_ids.issubset(generic_shell_section_ids):
                generic_shell_page_ids.append(str(page.get("page_id") or ""))
        transitions = page.get("actions_and_transitions")
        if not isinstance(transitions, list):
            return False, {"reason": "transitions-invalid", "page_id": page.get("page_id")}
        visible_user_inputs = {
            str(item.get("field", "")).strip()
            for item in page.get("user_inputs", [])
            if isinstance(item, dict) and str(item.get("field", "")).strip()
        }
        page_field_sources: dict[str, str] = {}
        for mapping in page.get("field_source_mapping", []):
            if not isinstance(mapping, dict):
                continue
            field = str(mapping.get("field", "")).strip()
            source = str(mapping.get("source", "")).strip()
            if field and source and field not in page_field_sources:
                page_field_sources[field] = source
        available_response_binding_targets: set[str] = set()
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            required_fields = [
                str(field).strip()
                for field in transition.get("required_fields", [])
                if str(field).strip()
            ]
            required_input_sources = transition.get("required_input_sources", [])
            source_by_field: dict[str, str] = {}
            if isinstance(required_input_sources, list):
                for entry in required_input_sources:
                    if not isinstance(entry, dict):
                        continue
                    field = str(entry.get("field", "")).strip()
                    source = str(entry.get("source", "")).strip()
                    if field and source and field not in source_by_field:
                        source_by_field[field] = source
            for field in required_fields:
                source = source_by_field.get(field) or page_field_sources.get(field, "")
                if source not in allowed_action_input_sources:
                    return False, {
                        "reason": "action-input-source-missing",
                        "page_id": page.get("page_id"),
                        "action": transition.get("action"),
                        "field": field,
                    }
                if source == "user-input" and field not in visible_user_inputs:
                    return False, {
                        "reason": "action-input-closure-missing",
                        "page_id": page.get("page_id"),
                        "action": transition.get("action"),
                        "field": field,
                        "source": source,
                    }
                if source == "response-binding" and field not in available_response_binding_targets:
                    return False, {
                        "reason": "action-input-closure-missing",
                        "page_id": page.get("page_id"),
                        "action": transition.get("action"),
                        "field": field,
                        "source": source,
                    }
            action = str(transition.get("action", "")).strip().lower()
            on_success = str(transition.get("on_success", "")).strip().lower()
            next_route = str(transition.get("next_route", "")).strip()
            has_structured_navigation = next_route.startswith("/")
            has_navigation_copy = bool(re.search(r"/[a-z0-9][a-z0-9/_-]*", on_success))
            has_progress_copy = (
                "navigate to" in on_success
                or "go to" in on_success
                or "refresh current page state" in on_success
                or "进入" in on_success
                or "跳转" in on_success
                or "下一步" in on_success
                or "带入下一步" in on_success
            )
            if action and (has_structured_navigation or has_navigation_copy or has_progress_copy):
                has_operable_flow = True
            for binding in transition.get("response_bindings", []):
                if not isinstance(binding, dict):
                    continue
                target = str(binding.get("to", "")).strip()
                if target:
                    available_response_binding_targets.add(target)
    if checked_pages == 0:
        return False, {"reason": "no-valid-pages"}
    if generic_shell_page_ids:
        return False, {
            "reason": "generic-shell-sections-detected",
            "page_count": checked_pages,
            "has_operable_flow": has_operable_flow,
            "generic_shell_page_ids": generic_shell_page_ids,
        }
    return has_operable_flow, {"reason": "ok", "page_count": checked_pages, "has_operable_flow": has_operable_flow}


def productness_report_contract_reference(productness_gate_report: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(productness_gate_report, dict):
        return {"ui_ia_contract_path": "", "ui_ia_contract_sha256": ""}
    nested = productness_gate_report.get("ui_ia_contract_reference")
    if not isinstance(nested, dict):
        nested = {}
    report_path = str(
        nested.get("ui_ia_contract_path")
        or productness_gate_report.get("ui_ia_contract_path")
        or ""
    ).strip()
    report_sha256 = str(
        nested.get("ui_ia_contract_sha256")
        or productness_gate_report.get("ui_ia_contract_sha256")
        or ""
    ).strip()
    return {
        "ui_ia_contract_path": report_path,
        "ui_ia_contract_sha256": report_sha256,
    }


def productness_report_matches_contract(
    ui_ia_contract_path: Path | None,
    productness_gate_report: dict[str, Any] | None,
) -> tuple[bool, str]:
    if not isinstance(productness_gate_report, dict):
        return False, "report-missing"
    checks = productness_gate_report.get("taxonomy_checks")
    metrics = productness_gate_report.get("contract_metrics")
    if not isinstance(checks, dict) or not isinstance(metrics, dict):
        return False, "report-payload-missing"
    reference = productness_report_contract_reference(productness_gate_report)
    report_path = reference["ui_ia_contract_path"]
    report_sha256 = reference["ui_ia_contract_sha256"]
    if not report_path or not report_sha256:
        return False, "fingerprint-missing"
    if ui_ia_contract_path is None or not ui_ia_contract_path.exists():
        return False, "current-contract-missing"
    try:
        current_path = str(ui_ia_contract_path.resolve())
        referenced_path = str(Path(report_path).resolve())
    except OSError:
        return False, "path-invalid"
    if referenced_path != current_path:
        return False, "path-mismatch"
    if report_sha256 != file_sha256(ui_ia_contract_path):
        return False, "hash-mismatch"
    return True, "matched"


def surface_contract_taxonomy_report(
    ui_ia_contract_path: Path | None,
    productness_gate_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_trusted, report_validation_reason = productness_report_matches_contract(
        ui_ia_contract_path,
        productness_gate_report,
    )
    if report_trusted and isinstance(productness_gate_report, dict):
        checks = productness_gate_report.get("taxonomy_checks")
        metrics = productness_gate_report.get("contract_metrics")
        if isinstance(checks, dict) and isinstance(metrics, dict):
            contract_failures = productness_gate_report.get("contract_failures", [])
            contract_warnings = productness_gate_report.get("contract_warnings", [])
            return {
                "present": True,
                "source": "phase3-productness-gate",
                "gate_pass": not contract_failures,
                "checks": checks,
                "metrics": metrics,
                "failures": [str(item) for item in contract_failures],
                "warnings": [str(item) for item in contract_warnings if str(item).strip()],
                "report_reused": True,
                "report_validation_reason": report_validation_reason,
            }
    if ui_ia_contract_path is None or not ui_ia_contract_path.exists():
        return {
            "present": False,
            "source": "missing",
            "gate_pass": False,
            "checks": {},
            "metrics": {},
            "failures": ["surface_contract_evidence_missing"],
            "warnings": [],
            "report_reused": False,
            "report_validation_reason": report_validation_reason,
        }
    payload, payload_status = safe_load_json(ui_ia_contract_path)
    if payload_status != "ok" or not isinstance(payload, dict) or not payload:
        return {
            "present": False,
            "source": "invalid-ui-ia-contract",
            "gate_pass": False,
            "checks": {},
            "metrics": {},
            "failures": ["surface_contract_invalid_json"],
            "warnings": [],
            "report_reused": False,
            "report_validation_reason": report_validation_reason,
        }
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return {
            "present": False,
            "source": "invalid-ui-ia-contract",
            "gate_pass": False,
            "checks": {},
            "metrics": {},
            "failures": ["surface_contract_pages_missing"],
            "warnings": [],
            "report_reused": False,
            "report_validation_reason": report_validation_reason,
        }
    assessment = evaluate_surface_contract_taxonomy(payload)
    return {
        "present": True,
        "source": "ui-ia-contract",
        **assessment,
        "report_reused": False,
        "report_validation_reason": (
            "recomputed-from-current-contract"
            if report_validation_reason in {"report-missing", "report-payload-missing"}
            else report_validation_reason
        ),
    }


def backend_layer_gate_rollup(wp_gate_report: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(wp_gate_report, dict):
        return {
            "present": False,
            "all_green": False,
            "blocking_layers": {},
            "blocked_work_packages": [],
        }
    rows = wp_gate_report.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    backend_rows = [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("lane", "")).strip().lower() == "backend"
    ]
    if not backend_rows:
        return {
            "present": False,
            "all_green": False,
            "blocking_layers": {},
            "blocked_work_packages": [],
        }
    blocking_layers: dict[str, list[str]] = {}
    blocked_work_packages: list[str] = []
    for row in backend_rows:
        wp_id = str(row.get("wp_id", "")).strip()
        layer = str(row.get("blocking_validation_layer", "")).strip()
        if layer:
            blocking_layers.setdefault(layer, []).append(wp_id)
            blocked_work_packages.append(wp_id)
    return {
        "present": True,
        "all_green": not blocked_work_packages,
        "blocking_layers": {
            key: sorted([wp for wp in values if wp])
            for key, values in sorted(blocking_layers.items())
        },
        "blocked_work_packages": sorted([wp for wp in blocked_work_packages if wp]),
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
    implementation_depth_gate_green = (
        behavior_card_consistency_classification in {"", "consistent"}
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
    trace_registry_gap_count = trace_registry_blocking_gap_count(
        load_json(trace_registry_final_path) if trace_registry_final_present and trace_registry_final_path and trace_registry_final_path.suffix == ".json" else None
    )
    if trace_registry_final_present and trace_registry_gap_count > 0:
        failures.append("trace_registry_final_has_unresolved_ids")

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
    runtime_smoke_present = path_exists(runtime_smoke_report_path) or runtime_smoke_report is not None
    runtime_smoke_green = report_is_pass(runtime_smoke_report) if runtime_smoke_report is not None else False
    started_service_smoke_present = path_exists(started_service_smoke_report_path) or started_service_smoke_report is not None
    started_service_smoke_green = report_is_pass(started_service_smoke_report) if started_service_smoke_report is not None else False
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
            "behavior_card_missing_implementation_steps": behavior_card_consistency.get("missing_implementation_steps", []),
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
            "delivery_artifacts_complete": delivery_artifacts_complete,
            "delivery_gate": delivery_ready,
        },
        "failures": failures,
        "warnings": warnings,
    }
    report["mainline_assessment"] = build_phase3_mainline_assessment(delivery_gate_report=report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve the formal completion state of a Phase-3 run")
    parser.add_argument(
        "--mode",
        choices=CLI_MODES,
        default="delivery-gate",
        help="delivery-gate resolves formal completion state; other modes run optional or specialized S04 sidecars",
    )
    parser.add_argument("--output-dir")
    parser.add_argument("--case-name")
    parser.add_argument("--workspace-root")
    parser.add_argument("--bootstrap-report")
    parser.add_argument("--build-report")
    parser.add_argument("--lint-report")
    parser.add_argument("--typecheck-report")
    parser.add_argument("--unit-test-report")
    parser.add_argument("--coverage-gate-report")
    parser.add_argument("--wp-gate-report")
    parser.add_argument("--verification-ledger-report")
    parser.add_argument("--openapi-diff-report")
    parser.add_argument("--code-review-metrics")
    parser.add_argument("--behavior-static-preflight-report")
    parser.add_argument("--security-audit-report")
    parser.add_argument("--openapi-final")
    parser.add_argument("--api-doc-dir")
    parser.add_argument("--deploy-runbook")
    parser.add_argument("--dockerfile")
    parser.add_argument("--compose-prod")
    parser.add_argument("--runtime-smoke-report")
    parser.add_argument("--started-service-smoke-report")
    parser.add_argument("--performance-baseline")
    parser.add_argument("--acceptance-report")
    parser.add_argument("--execution-report")
    parser.add_argument("--trace-registry-final")
    parser.add_argument("--ui-prototype-fallback-report")
    parser.add_argument("--ui-ia-contract")
    parser.add_argument("--productness-gate-report")
    parser.add_argument("--frontend-dir")
    parser.add_argument("--baseline-openapi")
    parser.add_argument("--candidate-openapi")
    parser.add_argument("--title", default="Phase-3 API Documentation")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--coverage-json")
    parser.add_argument("--replay-json")
    parser.add_argument("--min-lines-pct", type=float, default=80.0)
    parser.add_argument("--min-functions-pct", type=float, default=80.0)
    parser.add_argument("--min-branches-pct", type=float, default=70.0)
    parser.add_argument("--tech-stack-decision")
    parser.add_argument("--output-locale")
    parser.add_argument(
        "--require-frontend-contract",
        action="store_true",
        help="treat frontend contract / surface evidence as a mainline hard requirement instead of optional lane evidence",
    )
    parser.add_argument(
        "--retained-proof-mode",
        action="store_true",
        help="score a curated retained proof set instead of a runtime/deployment closure package",
    )
    parser.add_argument(
        "--strict-runtime-closure",
        action="store_true",
        help="treat missing install/build/runtime closure evidence as a hard blocker for delivery-gate state",
    )
    parser.add_argument("--output")
    return parser


def parse_phase3_delivery_gate_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def resolve_optional_path(raw: str | None) -> Path | None:
    return Path(raw).resolve() if raw else None


def load_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def validate_phase3_delivery_gate_args(args: argparse.Namespace) -> None:
    if args.mode == "productness-gate":
        if not args.frontend_dir:
            raise ValueError("--frontend-dir is required for --mode productness-gate")
        return
    if args.mode == "api-docs":
        if not args.baseline_openapi:
            raise ValueError("--baseline-openapi is required for --mode api-docs")
        if not args.output_dir:
            raise ValueError("--output-dir is required for --mode api-docs")
        return
    if args.mode == "delivery-handoff":
        if not args.output_dir:
            raise ValueError("--output-dir is required for --mode delivery-handoff")
        if not args.case_name:
            raise ValueError("--case-name is required for --mode delivery-handoff")
        return
    if args.mode == "code-review":
        if not args.output_dir:
            raise ValueError("--output-dir is required for --mode code-review")
        return
    if args.mode == "security-audit":
        if not args.output_dir:
            raise ValueError("--output-dir is required for --mode security-audit")
        return
    if args.mode == "coverage-collection":
        if not args.workspace_root and not args.coverage_json:
            raise ValueError("either --workspace-root or --coverage-json is required for --mode coverage-collection")
        return
    if not args.bootstrap_report:
        raise ValueError("--bootstrap-report is required for --mode delivery-gate")


def build_phase3_delivery_gate_context(args: argparse.Namespace) -> Phase3DeliveryGateContext:
    return Phase3DeliveryGateContext(
        mode=str(args.mode).strip() or "delivery-gate",
        output_dir=resolve_optional_path(args.output_dir),
        output_path=resolve_optional_path(args.output),
        workspace_root=resolve_optional_path(args.workspace_root),
        frontend_dir=resolve_optional_path(args.frontend_dir),
        bootstrap_report_path=resolve_optional_path(args.bootstrap_report),
        build_report_path=resolve_optional_path(args.build_report),
        lint_report_path=resolve_optional_path(args.lint_report),
        typecheck_report_path=resolve_optional_path(args.typecheck_report),
        unit_test_report_path=resolve_optional_path(args.unit_test_report),
        coverage_gate_report_path=resolve_optional_path(args.coverage_gate_report),
        wp_gate_report_path=resolve_optional_path(args.wp_gate_report),
        verification_ledger_report_path=resolve_optional_path(args.verification_ledger_report),
        openapi_diff_report_path=resolve_optional_path(args.openapi_diff_report),
        code_review_metrics_path=resolve_optional_path(args.code_review_metrics),
        behavior_static_preflight_report_path=resolve_optional_path(args.behavior_static_preflight_report),
        security_audit_report_path=resolve_optional_path(args.security_audit_report),
        openapi_final_path=resolve_optional_path(args.openapi_final),
        api_doc_dir=resolve_optional_path(args.api_doc_dir),
        deploy_runbook_path=resolve_optional_path(args.deploy_runbook),
        dockerfile_path=resolve_optional_path(args.dockerfile),
        compose_prod_path=resolve_optional_path(args.compose_prod),
        runtime_smoke_report_path=resolve_optional_path(args.runtime_smoke_report),
        started_service_smoke_report_path=resolve_optional_path(args.started_service_smoke_report),
        performance_baseline_path=resolve_optional_path(args.performance_baseline),
        acceptance_report_path=resolve_optional_path(args.acceptance_report),
        execution_report_path=resolve_optional_path(args.execution_report),
        trace_registry_final_path=resolve_optional_path(args.trace_registry_final),
        ui_prototype_fallback_report_path=resolve_optional_path(args.ui_prototype_fallback_report),
        ui_ia_contract_path=resolve_optional_path(args.ui_ia_contract),
        productness_gate_report_path=resolve_optional_path(args.productness_gate_report),
        baseline_openapi_path=resolve_optional_path(args.baseline_openapi),
        candidate_openapi_path=resolve_optional_path(args.candidate_openapi),
        implementation_bindings_path=resolve_optional_path(args.implementation_bindings),
        coverage_json_path=resolve_optional_path(args.coverage_json),
        replay_json_path=resolve_optional_path(args.replay_json),
        tech_stack_decision_path=resolve_optional_path(args.tech_stack_decision),
        title=str(args.title).strip() or "Phase-3 API Documentation",
        version=str(args.version).strip() or "0.1.0",
        case_name=str(args.case_name).strip(),
        output_locale=args.output_locale,
        require_frontend_contract=bool(args.require_frontend_contract),
        retained_proof_mode=bool(args.retained_proof_mode),
        strict_runtime_closure=bool(args.strict_runtime_closure),
        min_lines_pct=float(args.min_lines_pct),
        min_functions_pct=float(args.min_functions_pct),
        min_branches_pct=float(args.min_branches_pct),
    )


def write_phase3_cli_output(payload: dict[str, Any], output_path: Path | None) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def emit_phase3_delivery_gate_summary(payload: dict[str, Any], *, success: bool = True) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if success else 1


def emit_phase3_mode_result(
    payload: dict[str, Any],
    *,
    output_path: Path | None,
    success: bool = True,
) -> int:
    write_phase3_cli_output(payload, output_path)
    return emit_phase3_delivery_gate_summary(payload, success=success)


def run_productness_gate_mode(context: Phase3DeliveryGateContext) -> int:
    report = run_productness_gate(context.frontend_dir, context.ui_ia_contract_path)
    return emit_phase3_mode_result(report, output_path=context.output_path, success=report["verdict"] == "PASS")


def run_api_docs_mode(context: Phase3DeliveryGateContext) -> int:
    summary = generate_phase3_api_docs(
        baseline_openapi=load_json(context.baseline_openapi_path) or {},
        candidate_openapi=load_json(context.candidate_openapi_path),
        output_dir=context.output_dir,
        title=context.title,
        output_locale=context.output_locale,
    )
    return emit_phase3_mode_result(summary, output_path=context.output_path)


def run_delivery_handoff_mode(context: Phase3DeliveryGateContext) -> int:
    summary = generate_phase3_delivery_handoff(
        output_dir=context.output_dir,
        case_name=context.case_name,
        version=context.version,
        tech_stack_text=load_text(context.tech_stack_decision_path),
        wp_gate_report=load_json(context.wp_gate_report_path),
        verification_ledger_report=load_json(context.verification_ledger_report_path),
        coverage_gate_report=load_json(context.coverage_gate_report_path),
        output_locale=context.output_locale,
    )
    return emit_phase3_mode_result(summary, output_path=context.output_path)


def run_code_review_mode(context: Phase3DeliveryGateContext) -> int:
    summary = run_phase3_code_review(
        output_dir=context.output_dir,
        implementation_bindings=load_json(context.implementation_bindings_path),
        trace_registry_final=load_json(context.trace_registry_final_path),
        openapi_diff_report=load_json(context.openapi_diff_report_path),
        output_locale=context.output_locale,
    )
    return emit_phase3_mode_result(
        summary,
        output_path=context.output_path,
        success=summary["critical_findings"] == 0 and summary["high_findings"] == 0,
    )


def run_security_audit_mode(context: Phase3DeliveryGateContext) -> int:
    summary = run_phase3_security_audit(
        output_dir=context.output_dir,
        tech_stack_text=load_text(context.tech_stack_decision_path),
        output_locale=context.output_locale,
    )
    return emit_phase3_mode_result(
        summary,
        output_path=context.output_path,
        success=summary["critical_findings"] == 0 and summary["high_findings"] == 0,
    )


def run_coverage_collection_mode(context: Phase3DeliveryGateContext) -> int:
    replay_report = load_json(context.replay_json_path)
    if context.coverage_json_path is not None:
        report = analyze_phase3_coverage(
            coverage_report=load_json(context.coverage_json_path) or {},
            replay_report=replay_report,
            min_lines_pct=context.min_lines_pct,
            min_functions_pct=context.min_functions_pct,
            min_branches_pct=context.min_branches_pct,
        )
        return emit_phase3_mode_result(
            report,
            output_path=context.output_path,
            success=report.get("overall_quality_gate") == "pass",
        )
    report = collect_phase3_coverage(
        workspace_root=context.workspace_root,
        output_path=context.output_path,
        replay_report=replay_report,
    )
    return emit_phase3_mode_result(report, output_path=None, success=bool(report.get("collected")))


def run_delivery_gate_mode(context: Phase3DeliveryGateContext) -> int:
    report = analyze_phase3_delivery(
        bootstrap_report=load_json(context.bootstrap_report_path) or {},
        build_report=load_json(context.build_report_path),
        lint_report=load_json(context.lint_report_path),
        typecheck_report=load_json(context.typecheck_report_path),
        unit_test_report=load_json(context.unit_test_report_path),
        coverage_gate_report=load_json(context.coverage_gate_report_path),
        wp_gate_report=load_json(context.wp_gate_report_path),
        verification_ledger_report=load_json(context.verification_ledger_report_path),
        openapi_diff_report=load_json(context.openapi_diff_report_path),
        code_review_metrics=load_json(context.code_review_metrics_path),
        behavior_static_preflight_report=load_json(context.behavior_static_preflight_report_path),
        security_audit_report=load_json(context.security_audit_report_path),
        openapi_final_path=context.openapi_final_path,
        api_doc_dir=context.api_doc_dir,
        deploy_runbook_path=context.deploy_runbook_path,
        dockerfile_path=context.dockerfile_path,
        compose_prod_path=context.compose_prod_path,
        runtime_smoke_report=load_json(context.runtime_smoke_report_path),
        runtime_smoke_report_path=context.runtime_smoke_report_path,
        started_service_smoke_report=load_json(context.started_service_smoke_report_path),
        started_service_smoke_report_path=context.started_service_smoke_report_path,
        performance_baseline_path=context.performance_baseline_path,
        acceptance_report_path=context.acceptance_report_path,
        execution_report_path=context.execution_report_path,
        trace_registry_final_path=context.trace_registry_final_path,
        ui_prototype_fallback_report_path=context.ui_prototype_fallback_report_path,
        ui_ia_contract_path=context.ui_ia_contract_path,
        productness_gate_report=load_json(context.productness_gate_report_path),
        require_frontend_contract=context.require_frontend_contract,
        retained_proof_mode=context.retained_proof_mode,
        strict_runtime_closure=context.strict_runtime_closure,
    )
    if context.output_dir is not None:
        write_phase3_mainline_assessment_artifacts(
            output_dir=context.output_dir,
            assessment=report["mainline_assessment"],
        )
    return emit_phase3_mode_result(
        report,
        output_path=context.output_path,
        success=report["phase_completion_gate"] == "pass",
    )


def build_phase3_mode_handlers() -> dict[str, Callable[[Phase3DeliveryGateContext], int]]:
    return {
        "productness-gate": run_productness_gate_mode,
        "api-docs": run_api_docs_mode,
        "delivery-handoff": run_delivery_handoff_mode,
        "code-review": run_code_review_mode,
        "security-audit": run_security_audit_mode,
        "coverage-collection": run_coverage_collection_mode,
        "delivery-gate": run_delivery_gate_mode,
    }


def run_phase3_delivery_gate_mode(context: Phase3DeliveryGateContext) -> int:
    return build_phase3_mode_handlers()[context.mode](context)


def main(argv: list[str] | None = None) -> int:
    args = parse_phase3_delivery_gate_args(argv)
    try:
        validate_phase3_delivery_gate_args(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    context = build_phase3_delivery_gate_context(args)
    return run_phase3_delivery_gate_mode(context)


if __name__ == "__main__":
    raise SystemExit(main())
