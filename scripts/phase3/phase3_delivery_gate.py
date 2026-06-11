#!/usr/bin/env python3
"""Lightweight Phase-3 delivery gate entrypoint.

Full formal closure analysis and support modes live in
``phase3_delivery_gate_full.py`` plus the delivery-gate support CLI sidecars.
Slim implementation profiles keep this module as the stable delivery-gate
import/CLI surface and degrade to a review-bound report when the full sidecar
is not installed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import json
from pathlib import Path
import sys
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

_FULL_MODULE_NAMES = ("phase3.phase3_delivery_gate_full",)
CLI_MODES = (
    "delivery-gate",
    "delivery-handoff",
    "productness-gate",
    "api-docs",
    "code-review",
    "security-audit",
    "coverage-collection",
)


class Phase3SidecarUnavailable(RuntimeError):
    pass


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


def _full_module():
    for module_name in _FULL_MODULE_NAMES:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            expected_missing = {module_name, module_name.split(".", 1)[0]}
            if exc.name in expected_missing:
                continue
            raise
    return None


def resolve_optional_path(raw: str | None) -> Path | None:
    return Path(raw).resolve() if raw else None


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_phase3_cli_output(payload: dict[str, Any], output_path: Path | None) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def phase3_mode_authority_map() -> dict[str, dict[str, Any]]:
    module = _full_module()
    if module is not None:
        return module.phase3_mode_authority_map()
    return {"delivery-gate": phase3_mode_authority("delivery-gate")}


def phase3_mode_authority(mode: str) -> dict[str, Any]:
    module = _full_module()
    if module is not None:
        return module.phase3_mode_authority(mode)
    normalized = str(mode or "").strip() or "delivery-gate"
    if normalized != "delivery-gate":
        raise SystemExit(
            f"Phase-3 delivery gate mode '{normalized}' requires full-pack/source-tree support CLI sidecars"
        )
    return {
        "mode": "delivery-gate",
        "validation_profile": "phase",
        "blocking_scope": "formal P3 delivery-gate closure for the supplied implementation package",
        "formal_p3_closure_authority": True,
        "claim_ceiling": "P3 delivery evidence for the supplied package under selected runtime/strictness settings",
    }


def decorate_phase3_mode_payload(payload: dict[str, Any], mode: str) -> dict[str, Any]:
    module = _full_module()
    if module is not None:
        return module.decorate_phase3_mode_payload(payload, mode)
    decorated = dict(payload)
    decorated.setdefault("mode_authority", phase3_mode_authority(mode))
    return decorated


def _fallback_report(mode: str = "delivery-gate") -> dict[str, Any]:
    assessment = {
        "phase": "P3",
        "mainline_profile": "backend-first",
        "verdict": "RETURN-REMEDIATE",
        "phase_verdict": "RETURN-REMEDIATE",
        "total_score": None,
        "phase_total_score": None,
        "recommended_formal_state": "implementation-in-progress",
        "phase_complete": False,
        "implementation_complete": False,
        "review_bound_items": ["phase3_delivery_gate_full_sidecar_not_packaged"],
        "review_bound_items_count": 1,
        "blockers": [],
        "blockers_count": 0,
        "warnings": ["phase3_delivery_gate_full_sidecar_not_packaged"],
        "acceptance_rows": [
            {
                "key": "delivery_gate_full_sidecar_present",
                "label": "Full Phase-3 delivery gate analyzer present",
                "status": "REVIEW-BOUND",
                "why": "phase3_delivery_gate_full.py is full-pack-only and is not installed in this profile",
            }
        ],
        "dimension_scores": [],
    }
    return {
        "mode": mode,
        "artifact_kind": "phase3_delivery_gate_report",
        "sidecar_id": "phase3_delivery_gate_full",
        "sidecar_unavailable": True,
        "reason": "phase3_delivery_gate_full_sidecar_not_packaged",
        "phase_completion_gate": "review-bound",
        "recommended_formal_state": "implementation-in-progress",
        "phase_verdict": "RETURN-REMEDIATE",
        "phase_total_score": None,
        "phase_complete": False,
        "implementation_complete": False,
        "checks": {
            "delivery_gate_full_sidecar_present": False,
            "trace_registry_final_present": False,
            "trace_registry_gap_count": 0,
        },
        "failures": [],
        "warnings": ["phase3_delivery_gate_full_sidecar_not_packaged"],
        "mainline_assessment": assessment,
    }


def analyze_phase3_delivery(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        return _fallback_report()
    return module.analyze_phase3_delivery(*args, **kwargs)


def build_phase3_mainline_assessment(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        delivery_gate_report = kwargs.get("delivery_gate_report") if kwargs else None
        if not isinstance(delivery_gate_report, dict) and args:
            delivery_gate_report = args[0] if isinstance(args[0], dict) else None
        if isinstance(delivery_gate_report, dict) and isinstance(delivery_gate_report.get("mainline_assessment"), dict):
            return dict(delivery_gate_report["mainline_assessment"])
        return dict(_fallback_report().get("mainline_assessment", {}))
    return module.build_phase3_mainline_assessment(*args, **kwargs)


def build_phase3_mainline_assessment_summary(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        assessment = kwargs.get("assessment") if kwargs else None
        if not isinstance(assessment, dict) and args:
            assessment = args[0] if isinstance(args[0], dict) else {}
        assessment = assessment if isinstance(assessment, dict) else {}
        return {
            "phase": "P3",
            "mainline_profile": assessment.get("mainline_profile", "backend-first"),
            "recommended_formal_state": assessment.get("recommended_formal_state", "implementation-in-progress"),
            "phase_verdict": assessment.get("phase_verdict", assessment.get("verdict", "RETURN-REMEDIATE")),
            "phase_total_score": assessment.get("phase_total_score", assessment.get("total_score")),
            "review_bound_items_count": int(assessment.get("review_bound_items_count", 0) or 0),
            "blockers_count": int(assessment.get("blockers_count", 0) or 0),
        }
    return module.build_phase3_mainline_assessment_summary(*args, **kwargs)


def write_phase3_mainline_assessment_artifacts(*args: Any, **kwargs: Any) -> dict[str, str]:
    module = _full_module()
    if module is not None:
        return module.write_phase3_mainline_assessment_artifacts(*args, **kwargs)
    output_dir = Path(kwargs.get("output_dir") or (args[0] if args else ".")).resolve()
    assessment = kwargs.get("assessment") if isinstance(kwargs.get("assessment"), dict) else {}
    review_dir = output_dir / ".phase3-review"
    review_dir.mkdir(parents=True, exist_ok=True)
    assessment_path = review_dir / "phase3-mainline-assessment.json"
    summary_path = review_dir / "phase3-mainline-assessment-summary.json"
    write_phase3_cli_output(dict(assessment), assessment_path)
    write_phase3_cli_output(build_phase3_mainline_assessment_summary(assessment), summary_path)
    return {"assessment_path": str(assessment_path), "summary_path": str(summary_path)}


def ui_ia_contract_valid(*args: Any, **kwargs: Any) -> bool:
    module = _full_module()
    if module is None:
        return False
    return module.ui_ia_contract_valid(*args, **kwargs)


def classify_behavior_card_consistency(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        return {
            "classification": "review-bound",
            "missing_test_steps": [],
            "missing_implementation_steps": [],
            "reason": "phase3_delivery_gate_full_sidecar_not_packaged",
        }
    return module.classify_behavior_card_consistency(*args, **kwargs)


def build_acceptance_report(*args: Any, **kwargs: Any) -> str:
    module = _full_module()
    if module is None:
        payload = args[0] if args and isinstance(args[0], dict) else kwargs
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return module.build_acceptance_report(*args, **kwargs)


def build_execution_report(*args: Any, **kwargs: Any) -> str:
    module = _full_module()
    if module is None:
        payload = args[0] if args and isinstance(args[0], dict) else kwargs
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return module.build_execution_report(*args, **kwargs)


def _support_sidecar_unavailable(name: str) -> Phase3SidecarUnavailable:
    return Phase3SidecarUnavailable(f"{name} requires full-pack/source-tree support CLI sidecars")


def generate_phase3_api_docs(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("api-docs mode")
    return module.generate_phase3_api_docs(*args, **kwargs)


def analyze_phase3_coverage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("coverage analysis")
    return module.analyze_phase3_coverage(*args, **kwargs)


def collect_phase3_coverage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("coverage collection")
    return module.collect_phase3_coverage(*args, **kwargs)


def generate_phase3_delivery_handoff(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("delivery-handoff mode")
    return module.generate_phase3_delivery_handoff(*args, **kwargs)


def run_productness_gate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("productness-gate mode")
    return module.run_productness_gate(*args, **kwargs)


def run_phase3_code_review(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("code-review mode")
    return module.run_phase3_code_review(*args, **kwargs)


def run_phase3_security_audit(*args: Any, **kwargs: Any) -> dict[str, Any]:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("security-audit mode")
    return module.run_phase3_security_audit(*args, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    module = _full_module()
    if module is not None:
        return module.build_parser()
    parser = argparse.ArgumentParser(description="Run the slim Phase-3 delivery-gate entrypoint")
    parser.add_argument("--mode", choices=CLI_MODES, default="delivery-gate")
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
    parser.add_argument("--require-frontend-contract", action="store_true")
    parser.add_argument("--retained-proof-mode", action="store_true")
    parser.add_argument("--strict-runtime-closure", action="store_true")
    parser.add_argument("--output")
    return parser


def parse_phase3_delivery_gate_args(argv: list[str] | None = None):
    module = _full_module()
    if module is None:
        return build_parser().parse_args(argv)
    return module.parse_phase3_delivery_gate_args(argv)


def validate_phase3_delivery_gate_args(args: Any) -> None:
    module = _full_module()
    if module is not None:
        return module.validate_phase3_delivery_gate_args(args)
    if str(getattr(args, "mode", "delivery-gate") or "delivery-gate") != "delivery-gate":
        raise ValueError("support modes require full-pack/source-tree delivery gate CLI sidecars")
    if not getattr(args, "bootstrap_report", ""):
        raise ValueError("--bootstrap-report is required for --mode delivery-gate")


def build_phase3_delivery_gate_context(args: Any) -> Phase3DeliveryGateContext:
    module = _full_module()
    if module is not None:
        return module.build_phase3_delivery_gate_context(args)
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


def run_productness_gate_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("productness-gate mode")
    return module.run_productness_gate_mode(context)


def run_api_docs_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("api-docs mode")
    return module.run_api_docs_mode(context)


def run_delivery_handoff_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("delivery-handoff mode")
    return module.run_delivery_handoff_mode(context)


def run_code_review_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("code-review mode")
    return module.run_code_review_mode(context)


def run_security_audit_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("security-audit mode")
    return module.run_security_audit_mode(context)


def run_coverage_collection_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is None:
        raise _support_sidecar_unavailable("coverage-collection mode")
    return module.run_coverage_collection_mode(context)


def run_delivery_gate_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is not None:
        return module.run_delivery_gate_mode(context)
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
        mode=context.mode,
    )


def build_phase3_mode_handlers():
    module = _full_module()
    if module is not None:
        return module.build_phase3_mode_handlers()
    return {"delivery-gate": run_delivery_gate_mode}


def run_phase3_delivery_gate_mode(context: Phase3DeliveryGateContext) -> int:
    module = _full_module()
    if module is not None:
        return module.run_phase3_delivery_gate_mode(context)
    return build_phase3_mode_handlers()[context.mode](context)


def run_phase3_delivery_gate_cli(*, argv: list[str] | None, analyze_delivery: Any | None = None) -> int:
    module = _full_module()
    if module is not None:
        return module.run_phase3_delivery_gate_cli(argv=argv, analyze_delivery=analyze_delivery or module.analyze_phase3_delivery)
    args = parse_phase3_delivery_gate_args(argv)
    try:
        validate_phase3_delivery_gate_args(args)
        context = build_phase3_delivery_gate_context(args)
        return run_phase3_delivery_gate_mode(context)
    except (ValueError, Phase3SidecarUnavailable) as exc:
        print(f"[BLOCKED] {exc}")
        return 2


def main(argv: list[str] | None = None) -> int:
    module = _full_module()
    if module is None:
        return run_phase3_delivery_gate_cli(argv=argv)
    return module.main(argv)


def __getattr__(name: str) -> Any:
    module = _full_module()
    if module is not None and hasattr(module, name):
        return getattr(module, name)
    raise AttributeError(name)


__all__ = [
    "CLI_MODES",
    "Phase3DeliveryGateContext",
    "Phase3SidecarUnavailable",
    "analyze_phase3_coverage",
    "analyze_phase3_delivery",
    "build_acceptance_report",
    "build_execution_report",
    "build_parser",
    "build_phase3_delivery_gate_context",
    "build_phase3_mainline_assessment",
    "build_phase3_mainline_assessment_summary",
    "build_phase3_mode_handlers",
    "classify_behavior_card_consistency",
    "collect_phase3_coverage",
    "decorate_phase3_mode_payload",
    "emit_phase3_delivery_gate_summary",
    "emit_phase3_mode_result",
    "generate_phase3_api_docs",
    "generate_phase3_delivery_handoff",
    "load_json",
    "load_text",
    "main",
    "parse_phase3_delivery_gate_args",
    "phase3_mode_authority",
    "phase3_mode_authority_map",
    "resolve_optional_path",
    "run_api_docs_mode",
    "run_code_review_mode",
    "run_coverage_collection_mode",
    "run_delivery_gate_mode",
    "run_delivery_handoff_mode",
    "run_phase3_code_review",
    "run_phase3_delivery_gate_cli",
    "run_phase3_delivery_gate_mode",
    "run_phase3_security_audit",
    "run_productness_gate",
    "run_productness_gate_mode",
    "run_security_audit_mode",
    "ui_ia_contract_valid",
    "validate_phase3_delivery_gate_args",
    "write_phase3_cli_output",
    "write_phase3_mainline_assessment_artifacts",
]


if __name__ == "__main__":
    raise SystemExit(main())
