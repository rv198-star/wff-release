from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.agentic_repair_interrupt import (
    INTERRUPT_VERDICTS,
    build_agentic_repair_interrupt,
    render_agentic_repair_interrupt_json,
    render_agentic_repair_interrupt_markdown,
)
from phase3.claim_ceiling_resolver import build_phase3_claim_ceiling_report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


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
    runtime_kernel_truth_present = (
        bool(checks.get("backend_interface_signal_present"))
        and bool(checks.get("backend_interface_gate"))
        and (
            bool(checks.get("backend_packet_truth_present"))
            or bool(checks.get("backend_layered_api_gate"))
            or bool(checks.get("strict_runtime_backend_gate"))
        )
    )
    if domain_specific_count > 0:
        implementation_depth_state = "domain-specific"
    elif runtime_kernel_count > 0 or runtime_kernel_truth_present:
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
    claim_ceiling_report = delivery_gate_report.get("claim_ceiling_report")
    if not isinstance(claim_ceiling_report, dict):
        claim_ceiling_report = build_phase3_claim_ceiling_report(
            requested_formal_state=effective_recommended_formal_state,
            checks=checks,
            failures=failures,
            warnings=warnings,
            scope_states=scope_states,
        )
    resolved_claim_state = str(claim_ceiling_report.get("resolved_formal_state") or "").strip()
    if resolved_claim_state and resolved_claim_state != effective_recommended_formal_state:
        effective_recommended_formal_state = resolved_claim_state

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
        {
            "key": "claim_ceiling_authoritative",
            "label": "统一 claim ceiling 已裁决 formal state",
            "status": "PASS" if not claim_ceiling_report.get("reasons") else "REVIEW-BOUND",
            "why": (
                "formal state is not capped by unresolved evidence"
                if not claim_ceiling_report.get("reasons")
                else "; ".join(str(row.get("reason")) for row in claim_ceiling_report.get("reasons", [])[:3])
            ),
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
        "claim_ceiling_report": claim_ceiling_report,
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
        "claim_ceiling_report": assessment.get("claim_ceiling_report", {}),
        "claim_ceiling": str(
            (assessment.get("claim_ceiling_report", {}) if isinstance(assessment.get("claim_ceiling_report"), dict) else {}).get(
                "claim_ceiling",
                assessment.get("recommended_formal_state", ""),
            )
        ).strip(),
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


def emit_phase3_mainline_assessment(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
    case_name: str = "",
    version: str = "",
    output_locale: str = "zh-CN",
    human_review: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    assessment_artifacts = write_phase3_mainline_assessment_artifacts(
        output_dir=output_dir,
        assessment=assessment,
        case_name=case_name,
        version=version,
        output_locale=output_locale,
        human_review=human_review,
    )
    assessment_summary = build_phase3_mainline_assessment_summary(
        assessment=assessment,
        artifact_paths=assessment_artifacts,
    )
    return assessment_artifacts, assessment_summary


def update_phase3_run_metadata_with_assessment(
    *,
    metadata_path: Path,
    assessment_artifacts: dict[str, str],
    assessment_summary: dict[str, Any],
) -> dict[str, Any]:
    metadata = load_json_if_exists(metadata_path) or {}
    metadata["mainline_assessment_artifacts"] = assessment_artifacts
    metadata["mainline_assessment_summary"] = assessment_summary
    metadata["phase_verdict_path"] = assessment_summary.get("phase_verdict_path", "")
    metadata["phase_verdict"] = assessment_summary.get("phase_verdict", "")
    metadata["phase_total_score"] = assessment_summary.get("phase_total_score")
    metadata["phase_review_bound_items_count"] = assessment_summary.get("review_bound_items_count", 0)
    metadata["phase_blockers_count"] = assessment_summary.get("blockers_count", 0)
    write_json(metadata_path, metadata)
    return metadata
