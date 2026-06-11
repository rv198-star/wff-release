#!/usr/bin/env python3
"""
Phase-3 delivery gate CLI parsing and mode dispatch.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Callable

from phase3.delivery_gate_context import Phase3DeliveryGateContext
from phase3.delivery_mode_authority import CLI_MODES, decorate_phase3_mode_payload
from phase3.review_support import support_gate_passed


class Phase3SidecarUnavailable(RuntimeError):
    """Raised when an optional Phase-3 support sidecar is not installed."""


def _delivery_report_rendering_module():
    try:
        return importlib.import_module("phase3.delivery_report_rendering")
    except ModuleNotFoundError as exc:
        if exc.name == "phase3.delivery_report_rendering":
            return None
        raise


def _fallback_report_line(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key, "") if isinstance(payload, dict) else ""
    return f"- {key}: `{value}`" if value not in ("", None) else f"- {key}: ``"


def build_acceptance_report(*args: object, **kwargs: object) -> str:
    module = _delivery_report_rendering_module()
    if module is not None:
        return module.build_acceptance_report(*args, **kwargs)
    delivery_gate_report = kwargs.get("delivery_gate_report", {})
    bootstrap_report = kwargs.get("bootstrap_report", {})
    return "\n".join(
        [
            "# Phase-3 Acceptance Report",
            "",
            "- mode: `delivery-report-rendering-sidecar-unavailable`",
            _fallback_report_line(
                delivery_gate_report if isinstance(delivery_gate_report, dict) else {},
                "phase_completion_gate",
            ),
            _fallback_report_line(
                delivery_gate_report if isinstance(delivery_gate_report, dict) else {},
                "recommended_formal_state",
            ),
            _fallback_report_line(
                bootstrap_report if isinstance(bootstrap_report, dict) else {},
                "quality_gate",
            ),
            "",
        ]
    )


def build_execution_report(*args: object, **kwargs: object) -> str:
    module = _delivery_report_rendering_module()
    if module is not None:
        return module.build_execution_report(*args, **kwargs)
    delivery_gate_report = kwargs.get("delivery_gate_report", {})
    return "\n".join(
        [
            "# Phase-3 Execution Report",
            "",
            "- mode: `delivery-report-rendering-sidecar-unavailable`",
            _fallback_report_line(
                delivery_gate_report if isinstance(delivery_gate_report, dict) else {},
                "phase_completion_gate",
            ),
            _fallback_report_line(
                delivery_gate_report if isinstance(delivery_gate_report, dict) else {},
                "phase_verdict",
            ),
            "",
        ]
    )


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve the formal completion state of a Phase-3 run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "mode authority: delivery-gate is the formal P3 closure mode; "
            "other modes emit support evidence with narrower claim ceilings."
        ),
    )
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


def _sidecar_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            raise Phase3SidecarUnavailable(
                f"optional Phase-3 support sidecar is not installed: {module_name}"
            ) from exc
        raise


def generate_phase3_api_docs(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _sidecar_module("phase3.api_doc_generation").generate_phase3_api_docs(*args, **kwargs)


def generate_phase3_delivery_handoff(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _sidecar_module("phase3.delivery_handoff").generate_phase3_delivery_handoff(*args, **kwargs)


def run_phase3_code_review(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _sidecar_module("phase3.code_review").run_phase3_code_review(*args, **kwargs)


def run_phase3_security_audit(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _sidecar_module("phase3.security_audit").run_phase3_security_audit(*args, **kwargs)


def analyze_phase3_coverage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _sidecar_module("phase3.coverage_collection").analyze_phase3_coverage(*args, **kwargs)


def collect_phase3_coverage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _sidecar_module("phase3.coverage_collection").collect_phase3_coverage(*args, **kwargs)


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


def write_phase3_mainline_assessment_artifacts(
    *,
    output_dir: Path,
    assessment: dict[str, Any],
    case_name: str = "",
    version: str = "",
    output_locale: str = "zh-CN",
    human_review: dict[str, Any] | None = None,
) -> dict[str, str]:
    try:
        module = importlib.import_module("phase3.mainline_assessment")
    except ModuleNotFoundError as exc:
        if exc.name != "phase3.mainline_assessment":
            raise
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
    return module.write_phase3_mainline_assessment_artifacts(
        output_dir=output_dir,
        assessment=assessment,
        case_name=case_name,
        version=version,
        output_locale=output_locale,
        human_review=human_review,
    )

def emit_phase3_delivery_gate_summary(payload: dict[str, Any], *, success: bool = True) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if success else 1


def emit_phase3_mode_result(
    payload: dict[str, Any],
    *,
    output_path: Path | None,
    success: bool = True,
    mode: str = "",
) -> int:
    if mode:
        payload = decorate_phase3_mode_payload(payload, mode)
    write_phase3_cli_output(payload, output_path)
    return emit_phase3_delivery_gate_summary(payload, success=success)


def run_productness_gate(frontend_dir: Path | None, ui_ia_contract_path: Path | None) -> dict[str, Any]:
    return importlib.import_module("phase3.productness_gate").run_gate(frontend_dir, ui_ia_contract_path)


def run_productness_gate_mode(context: Phase3DeliveryGateContext) -> int:
    report = run_productness_gate(context.frontend_dir, context.ui_ia_contract_path)
    return emit_phase3_mode_result(report, output_path=context.output_path, success=report["verdict"] == "PASS", mode=context.mode)


def run_api_docs_mode(context: Phase3DeliveryGateContext) -> int:
    summary = generate_phase3_api_docs(
        baseline_openapi=load_json(context.baseline_openapi_path) or {},
        candidate_openapi=load_json(context.candidate_openapi_path),
        output_dir=context.output_dir,
        title=context.title,
        output_locale=context.output_locale,
    )
    return emit_phase3_mode_result(summary, output_path=context.output_path, mode=context.mode)


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
    return emit_phase3_mode_result(summary, output_path=context.output_path, mode=context.mode)


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
        success=support_gate_passed(context.mode, summary),
        mode=context.mode,
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
        success=support_gate_passed(context.mode, summary),
        mode=context.mode,
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
            success=support_gate_passed(context.mode, report),
            mode=context.mode,
        )
    report = collect_phase3_coverage(
        workspace_root=context.workspace_root,
        output_path=context.output_path,
        replay_report=replay_report,
    )
    return emit_phase3_mode_result(report, output_path=None, success=support_gate_passed(context.mode, report), mode=context.mode)


def run_delivery_gate_mode(
    context: Phase3DeliveryGateContext,
    *,
    analyze_delivery: Callable[..., dict[str, Any]],
) -> int:
    report = analyze_delivery(
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
        mode=context.mode,
    )


def build_phase3_mode_handlers(
    *,
    analyze_delivery: Callable[..., dict[str, Any]],
) -> dict[str, Callable[[Phase3DeliveryGateContext], int]]:
    return {
        "productness-gate": run_productness_gate_mode,
        "api-docs": run_api_docs_mode,
        "delivery-handoff": run_delivery_handoff_mode,
        "code-review": run_code_review_mode,
        "security-audit": run_security_audit_mode,
        "coverage-collection": run_coverage_collection_mode,
        "delivery-gate": lambda context: run_delivery_gate_mode(context, analyze_delivery=analyze_delivery),
    }


def run_phase3_delivery_gate_mode(
    context: Phase3DeliveryGateContext,
    *,
    analyze_delivery: Callable[..., dict[str, Any]],
) -> int:
    return build_phase3_mode_handlers(analyze_delivery=analyze_delivery)[context.mode](context)


def run_phase3_delivery_gate_cli(
    *,
    argv: list[str] | None,
    analyze_delivery: Callable[..., dict[str, Any]],
) -> int:
    args = parse_phase3_delivery_gate_args(argv)
    try:
        validate_phase3_delivery_gate_args(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    context = build_phase3_delivery_gate_context(args)
    try:
        return run_phase3_delivery_gate_mode(context, analyze_delivery=analyze_delivery)
    except Phase3SidecarUnavailable as exc:
        print(f"[BLOCKED] {exc}")
        return 2


__all__ = [
    "Phase3DeliveryGateContext",
    "Phase3SidecarUnavailable",
    "analyze_phase3_coverage",
    "build_acceptance_report",
    "build_execution_report",
    "build_parser",
    "build_phase3_delivery_gate_context",
    "build_phase3_mode_handlers",
    "collect_phase3_coverage",
    "emit_phase3_delivery_gate_summary",
    "emit_phase3_mode_result",
    "generate_phase3_api_docs",
    "generate_phase3_delivery_handoff",
    "load_json",
    "load_text",
    "parse_phase3_delivery_gate_args",
    "resolve_optional_path",
    "run_api_docs_mode",
    "run_code_review_mode",
    "run_coverage_collection_mode",
    "run_delivery_gate_mode",
    "run_delivery_handoff_mode",
    "run_phase3_delivery_gate_cli",
    "run_phase3_delivery_gate_mode",
    "run_phase3_code_review",
    "run_phase3_security_audit",
    "run_productness_gate_mode",
    "run_security_audit_mode",
    "validate_phase3_delivery_gate_args",
    "write_phase3_cli_output",
    "write_phase3_mainline_assessment_artifacts",
]
