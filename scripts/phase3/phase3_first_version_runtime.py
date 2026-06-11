#!/usr/bin/env python3
"""Shared Phase-3 foundation / first-version runtime implementation.

This module owns the real first-version generation path used by both the
modular ``run_impl_foundation`` entrypoint and the legacy compatibility wrapper.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import importlib
import json
from dataclasses import dataclass
from pathlib import Path

from common.tvg_runtime_metadata import THINKING_VALUE_GAIN_OUTPUT_PROFILES
from common.contamination_boundary import build_contamination_report
from common.cross_phase_surface_policy import resolve_cross_phase_surface_path
from phase3.foundation_bootstrap import (
    emit_phase3_bootstrap_artifacts,
    load_phase2_source_texts,
    run_phase3_bootstrap_stage_impl,
)
from phase3.foundation_mainline import run_phase3_foundation_mainline_impl
from phase3.phase3_implementation_scaffolder import scaffold_phase3_implementation
from phase3.phase3_project_scaffold import generate_project_scaffold
from phase3.phase3_stack_decision import build_stack_decision_document
from phase3.phase3_toolchain_bootstrap import bootstrap_phase3_toolchain
from phase3.validation_levels import (
    VALIDATION_LEVEL_CHOICES,
    full_targeted_evidence_for_validation_level,
    normalize_validation_level,
)
from common.output_language import localize_phase3_coverage_plan, resolve_output_locale
from common.human_review_surface import emit_human_review_surface
from phase3.schema_test_scaffolder import scaffold_schema_tests


@dataclass(frozen=True)
class Phase3RunnerContext:
    phase2_root: Path
    output_dir: Path
    output_locale: str
    ui_locale: str
    thinking_value_gain_mode: str
    thinking_value_gain_output_profile: str


def _not_requested_summary() -> dict[str, object]:
    return {"mode": "not-requested"}


def _optional_phase3_runtime_sidecar(module_name: str):
    try:
        return importlib.import_module(f"phase3.{module_name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"phase3.{module_name}":
            return None
        raise


def initialize_phase3_trace_registry(test_trace_matrix: dict[str, object]) -> dict[str, object]:
    module = _optional_phase3_runtime_sidecar("trace_registry")
    if module is not None:
        return module.initialize_phase3_trace_registry(test_trace_matrix)
    rows = test_trace_matrix.get("rows", []) if isinstance(test_trace_matrix, dict) else []
    if not isinstance(rows, list):
        rows = []
    registry_rows = [
        {
            "source_id": str(row.get("source_id", "")).strip(),
            "source_type": str(row.get("source_type", "")).strip(),
            "source_subject": str(row.get("source_subject", "")).strip(),
            "upstream_trace_ids": list(row.get("upstream_trace_ids", [])),
            "linked_rbi_or_wp": list(row.get("linked_rbi_or_wp", [])),
            "test_targets": list(row.get("test_targets", [])),
            "implementation_targets": [],
            "work_packages": [],
            "binding_status": "trace-registry-sidecar-unavailable",
            "verification_hook": str(row.get("verification_hook", "")).strip(),
        }
        for row in rows
        if isinstance(row, dict)
    ]
    return {
        "rows": registry_rows,
        "summary": {
            "source_count": len(registry_rows),
            "pending_source_count": len(registry_rows),
            "resolved_source_count": 0,
        },
        "mode": "unavailable",
        "sidecar_id": "trace_registry",
        "sidecar_unavailable": True,
        "reason": "trace_registry_sidecar_not_packaged",
    }


def finalize_trace_registry(
    *,
    test_trace_matrix: dict[str, object],
    implementation_bindings: dict[str, object] | None = None,
) -> dict[str, object]:
    module = _optional_phase3_runtime_sidecar("trace_registry")
    if module is not None:
        return module.finalize_trace_registry(
            test_trace_matrix=test_trace_matrix,
            implementation_bindings=implementation_bindings,
        )
    rows = test_trace_matrix.get("rows", []) if isinstance(test_trace_matrix, dict) else []
    if not isinstance(rows, list):
        rows = []
    final_rows = []
    unresolved_trace_ids = []
    source_type_breakdown: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_type = str(row.get("source_type", "")).strip()
        if source_id:
            unresolved_trace_ids.append(source_id)
        source_type_breakdown[source_type] = source_type_breakdown.get(source_type, 0) + 1
        final_rows.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "source_subject": str(row.get("source_subject", "")).strip(),
                "upstream_trace_ids": row.get("upstream_trace_ids", []),
                "verification_hook": str(row.get("verification_hook", "")).strip(),
                "test_targets": row.get("test_targets", []),
                "implementation_targets": [],
                "work_packages": [],
                "runtime_evidence_refs": [],
                "binding_status": "trace-registry-sidecar-unavailable",
                "final_resolution": "unresolved",
            }
        )
    return {
        "rows": final_rows,
        "summary": {
            "source_count": len(final_rows),
            "resolved_source_count": 0,
            "unresolved_source_count": len(unresolved_trace_ids),
            "unresolved_trace_ids": unresolved_trace_ids,
            "source_type_breakdown": source_type_breakdown,
        },
        "mode": "unavailable",
        "sidecar_id": "trace_registry",
        "sidecar_unavailable": True,
        "reason": "trace_registry_sidecar_not_packaged",
    }


def refresh_phase3_post_execution(output_dir: Path, *args: object, **kwargs: object) -> dict[str, object]:
    module = _optional_phase3_runtime_sidecar("post_execution_refresh")
    if module is not None:
        return module.refresh_phase3_post_execution(output_dir, *args, **kwargs)
    return {
        "mode": "unavailable",
        "sidecar_id": "post_execution_refresh",
        "sidecar_unavailable": True,
        "reason": "post_execution_refresh_sidecar_not_packaged",
        "recommended_formal_state": "implementation-in-progress",
        "delivery_gate_path": str(output_dir / "phase3-delivery-gate.json"),
        "mainline_assessment_paths": {},
        "mainline_assessment_summary": {},
        "phase_verdict_path": "",
        "phase_verdict": "",
        "phase_total_score": None,
        "timing_segments": {},
    }


def finalize_phase3_delivery_closure(
    *args: object,
    **kwargs: object,
) -> tuple[dict[str, object], dict[str, str], dict[str, object]]:
    module = _optional_phase3_runtime_sidecar("delivery_closure")
    if module is not None:
        return module.finalize_phase3_delivery_closure(*args, **kwargs)
    return (
        {
            "mode": "unavailable",
            "sidecar_id": "delivery_closure",
            "sidecar_unavailable": True,
            "reason": "delivery_closure_sidecar_not_packaged",
            "phase_completion_gate": "review-bound",
            "recommended_formal_state": "implementation-in-progress",
            "mainline_assessment": {"phase_verdict": "RETURN-REMEDIATE"},
        },
        {},
        {
            "mode": "unavailable",
            "sidecar_id": "delivery_closure",
            "sidecar_unavailable": True,
            "reason": "delivery_closure_sidecar_not_packaged",
        },
    )


def generate_phase3_delivery_handoff(*args: object, **kwargs: object) -> dict[str, object]:
    try:
        module = importlib.import_module("phase3.delivery_handoff")
    except ModuleNotFoundError as exc:
        if exc.name == "phase3.delivery_handoff":
            return {
                "mode": "unavailable",
                "reason": "delivery_handoff_sidecar_not_packaged",
            }
        raise
    return module.generate_phase3_delivery_handoff(*args, **kwargs)


def execute_phase3_mainline_backend_verification(*args: object, **kwargs: object) -> dict[str, object]:
    try:
        module = importlib.import_module("phase3.mainline_backend_execution")
    except ModuleNotFoundError as exc:
        if exc.name == "phase3.mainline_backend_execution":
            return {
                "sidecar_unavailable": True,
                "attempted": False,
                "status": "skipped",
                "reason": "mainline_backend_verification_sidecar_not_packaged",
                "overall_verdict": "",
                "validation_level": str(kwargs.get("validation_level", "") or ""),
                "full_targeted_evidence": bool(kwargs.get("full_targeted_evidence", True)),
            }
        raise
    return module.execute_phase3_mainline_backend_verification(*args, **kwargs)


def analyze_phase3_bootstrap(*args: object, **kwargs: object) -> dict[str, object]:
    try:
        module = importlib.import_module("phase3.phase3_quality_check")
    except ModuleNotFoundError as exc:
        if exc.name == "phase3.phase3_quality_check":
            return {
                "overall_quality_gate": "pass",
                "recommended_formal_state": "implementation-in-progress",
                "sidecar_unavailable": True,
                "mode": "unavailable",
                "reason": "phase3_quality_check_sidecar_not_packaged",
                "metrics": {"quality_check_sidecar_present": False},
                "failures": [],
                "warnings": ["phase3_quality_check_sidecar_not_packaged"],
            }
        raise
    return module.analyze_phase3_bootstrap(*args, **kwargs)


def _dispatch_lane_bootstrap_module():
    return importlib.import_module("phase3.dispatch_lane_bootstrap")


def select_bootstrap_worker_packet(execution_loop_plan: dict[str, object]) -> tuple[int, str]:
    return _dispatch_lane_bootstrap_module().select_bootstrap_worker_packet(execution_loop_plan)


def initialize_optional_dispatch_lane(**kwargs: object) -> dict[str, object]:
    output_dir = kwargs["output_dir"]
    if not bool(kwargs.get("enabled")):
        return {
            "wp_packet_summary": _not_requested_summary(),
            "wp_wave_summary": _not_requested_summary(),
            "execution_loop_summary": _not_requested_summary(),
            "execution_dispatch_summary": _not_requested_summary(),
            "worker_run_report_summary": _not_requested_summary(),
            "bootstrap_worker_run_report_summary": _not_requested_summary(),
            "worker_packet_run_summary": _not_requested_summary(),
            "runtime_cycle_summary": _not_requested_summary(),
            "runtime_environment_ledger_summary": _not_requested_summary(),
            "worker_run_report_path": output_dir / "worker-run-report.json",
            "bootstrap_worker_run_report_path": output_dir / "bootstrap-worker-run-report.json",
            "runtime_environment_ledger_path": output_dir / "runtime-environment-ledger.json",
        }
    return _dispatch_lane_bootstrap_module().initialize_optional_dispatch_lane(**kwargs)


def build_test_coverage_plan(
    *,
    schema_count: int,
    sql_count: int,
    contract_count: int,
    scenario_count: int,
    replay_count: int,
    output_locale: str | None = None,
) -> str:
    text = "\n".join(
        [
            "# Phase-3 Test Coverage Plan",
            "",
            "## Coverage Targets",
            f"- schema_tests: {schema_count}",
            f"- sql_tests: {sql_count}",
            f"- contract_tests: {contract_count}",
            f"- scenario_tests: {scenario_count}",
            f"- replay_tests: {replay_count}",
            "",
            "## Rules",
            "- Tests are written before business implementation.",
            "- Contract tests remain the public-boundary source of truth.",
            "- Scenario and replay tests must stay bound to Phase-2 trace subjects.",
            "",
            "## Concurrency Interpretation",
            "- Concurrent/conflict scenarios in Phase-3 default to deterministic contract-level conflict-path validation.",
            "- They verify idempotency, version-conflict handling, retry guidance, and authoritative final state preservation.",
            "- They do not, by themselves, prove production-grade multi-node race safety or database lock correctness.",
            "- If true parallel contention validation is required, escalate that requirement into a Phase-4 hardening harness.",
            "",
        ]
    ) + "\n"
    return localize_phase3_coverage_plan(text, output_locale)


def emit_phase3_runner_summary(summary: dict[str, object]) -> int:
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["quality_gate"] == "pass" else 1


def parse_phase3_first_version_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    explicit_evidence_mode = any(
        item in {"--full-targeted-evidence", "--critical-targeted-evidence-only"} for item in raw_argv
    )
    args = build_parser().parse_args(argv)
    explicit_validation_level = bool(getattr(args, "validation_level", ""))
    if explicit_validation_level:
        args.validation_level = normalize_validation_level(args.validation_level)
        if not explicit_evidence_mode:
            args.full_targeted_evidence = full_targeted_evidence_for_validation_level(args.validation_level)
    else:
        args.validation_level = normalize_validation_level(
            "",
            full_targeted_evidence=bool(getattr(args, "full_targeted_evidence", True)),
        )
    return args


def validate_phase3_runner_args(args: argparse.Namespace) -> None:
    if args.mainline_stage == "bootstrap" and args.enable_dispatch_lane:
        raise ValueError("--enable-dispatch-lane is only available for --mainline-stage foundation")

    if args.require_frontend_contract and not args.enable_ui_fallback:
        raise ValueError("--require-frontend-contract currently requires --enable-ui-fallback")

    validation_level = normalize_validation_level(
        getattr(args, "validation_level", ""),
        full_targeted_evidence=bool(getattr(args, "full_targeted_evidence", True)),
    )
    full_targeted_evidence = bool(getattr(args, "full_targeted_evidence", True))
    if validation_level == "strict" and not full_targeted_evidence:
        raise ValueError("--validation-level strict requires --full-targeted-evidence")
    if validation_level in {"fast", "focused"} and full_targeted_evidence:
        raise ValueError(f"--validation-level {validation_level} requires --critical-targeted-evidence-only")


def build_phase3_runner_context(args: argparse.Namespace) -> Phase3RunnerContext:
    phase2_root = Path(args.phase2_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_locale = resolve_output_locale(args.output_locale)
    ui_locale = args.ui_locale or output_locale
    return Phase3RunnerContext(
        phase2_root=phase2_root,
        output_dir=output_dir,
        output_locale=output_locale,
        ui_locale=ui_locale,
        thinking_value_gain_mode=str(getattr(args, "thinking_value_gain_mode", "off") or "off"),
        thinking_value_gain_output_profile=str(
            getattr(args, "thinking_value_gain_output_profile", "coverage_rich") or "coverage_rich"
        ),
    )


def run_phase3_bootstrap_stage(args: argparse.Namespace, context: Phase3RunnerContext) -> int:
    summary = run_phase3_bootstrap_stage_impl(
        args=args,
        phase2_root=context.phase2_root,
        output_dir=context.output_dir,
        ui_locale=context.ui_locale,
        analyze_phase3_bootstrap_fn=analyze_phase3_bootstrap,
    )
    summary["thinking_value_gain_mode"] = context.thinking_value_gain_mode
    summary["thinking_value_gain_output_profile"] = context.thinking_value_gain_output_profile
    emit_human_review_surface(context.output_dir, "phase3")
    return emit_phase3_runner_summary(summary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the first Phase-3 foundation package")
    parser.add_argument(
        "--mainline-stage",
        choices=("foundation", "bootstrap"),
        default="foundation",
        help="foundation emits the backend-first Phase-3 mainline; bootstrap emits the S01/S02 contract/test pack only",
    )
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-3 First Version")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument("--ui-locale", default="")
    parser.add_argument(
        "--thinking-value-gain-mode",
        choices=("off", "full-use"),
        default="off",
        help="Mindthus TVG strategy marker for Phase-3 generation; defaults to off.",
    )
    parser.add_argument(
        "--thinking-value-gain-output-profile",
        choices=THINKING_VALUE_GAIN_OUTPUT_PROFILES,
        default="coverage_rich",
        help="Mindthus TVG output profile to record when TVG full-use is enabled.",
    )
    parser.add_argument(
        "--enable-ui-fallback",
        action="store_true",
        help="enable the optional frontend fallback lane and emit compiled UI contract artifacts",
    )
    parser.add_argument(
        "--enable-dispatch-lane",
        action="store_true",
        help="enable the optional dispatch / worker-packet / runtime-cycle lane",
    )
    parser.add_argument(
        "--require-frontend-contract",
        action="store_true",
        help="treat frontend contract evidence as a mainline hard requirement instead of optional lane evidence",
    )
    parser.add_argument(
        "--mainline-verification-mode",
        choices=("disabled", "if-ready", "strict-runtime"),
        default="if-ready",
        help="run the hidden backend verification hook for the default mainline when the toolchain is ready",
    )
    parser.add_argument(
        "--strict-runtime",
        dest="mainline_verification_mode",
        action="store_const",
        const="strict-runtime",
        help="alias for --mainline-verification-mode strict-runtime",
    )
    parser.add_argument(
        "--validation-level",
        choices=VALIDATION_LEVEL_CHOICES,
        default="",
        help=(
            "validation depth for backend mainline verification: fast/focused use critical targeted evidence and "
            "require later strict full validation before release claims; strict keeps full targeted evidence"
        ),
    )
    parser.add_argument(
        "--full-targeted-evidence",
        dest="full_targeted_evidence",
        action="store_true",
        help="run full-targeted-tests inside the backend mainline verification sequence; this is the default strict-runtime evidence mode",
    )
    parser.add_argument(
        "--critical-targeted-evidence-only",
        dest="full_targeted_evidence",
        action="store_false",
        help="use the faster critical-targeted-tests sampling path instead of full targeted integration evidence",
    )
    parser.set_defaults(full_targeted_evidence=True)
    parser.add_argument(
        "--install-toolchain",
        action="store_true",
        help="attempt pnpm install inside the generated Phase-3 workspace before evaluating mainline verification readiness",
    )
    parser.add_argument(
        "--run-runtime-smoke",
        action="store_true",
        help="run runtime smoke during post-execution refresh when docker assets and runtime prerequisites are available",
    )
    parser.add_argument(
        "--service-authoring-packet",
        dest="service_authoring_packet_path",
        default="",
        help="explicit opt-in JSON packet for bounded P3 service method body authoring",
    )
    parser.add_argument(
        "--enable-agentic-authoring-enrichment",
        action="store_true",
        help="enable optional in-memory agentic authoring enrichment for semantic decisions, module briefs, and direct implementation driver hints",
    )
    parser.add_argument(
        "--module-synthesis-bundle",
        dest="module_synthesis_bundle_path",
        default="",
        help="explicit opt-in directory for phase3-module-synthesis-bundle.v1 selected-module authoring",
    )
    return parser

def run_phase3_foundation_mainline(args: argparse.Namespace, context: Phase3RunnerContext) -> int:
    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(context.phase2_root)
    contamination_report = build_contamination_report(
        "\n\n".join([esp_text, stage_03_text, stage_04_text]),
        source_label=str(context.phase2_root),
        boundary="p2-to-p3",
        output_path=resolve_cross_phase_surface_path(
            context.output_dir,
            "phase3",
            "p2-to-p3-contamination-report.json",
        ),
    )
    if contamination_report["overall_status"] == "blocked":
        print(
            "[BLOCKED] p2-to-p3 contamination boundary failed: "
            f"{resolve_cross_phase_surface_path(context.output_dir, 'phase3', 'p2-to-p3-contamination-report.json')}"
        )
        print(f"classifications: {', '.join(contamination_report['classifications'])}")
        return 2
    bootstrap = emit_phase3_bootstrap_artifacts(
        phase2_root=context.phase2_root,
        output_dir=context.output_dir,
        title=args.title,
        version=args.version,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        ui_locale=context.ui_locale,
        enable_ui_fallback=args.enable_ui_fallback,
        enforce_compiled_authority=args.require_frontend_contract,
    )
    summary = run_phase3_foundation_mainline_impl(
        args=args,
        phase2_root=context.phase2_root,
        output_dir=context.output_dir,
        output_locale=context.output_locale,
        ui_locale=context.ui_locale,
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        bootstrap=bootstrap,
        build_test_coverage_plan_fn=build_test_coverage_plan,
        build_stack_decision_document_fn=build_stack_decision_document,
        generate_project_scaffold_fn=generate_project_scaffold,
        bootstrap_phase3_toolchain_fn=bootstrap_phase3_toolchain,
        scaffold_schema_tests_fn=scaffold_schema_tests,
        initialize_phase3_trace_registry_fn=initialize_phase3_trace_registry,
        scaffold_phase3_implementation_fn=scaffold_phase3_implementation,
        initialize_optional_dispatch_lane_fn=initialize_optional_dispatch_lane,
        analyze_phase3_bootstrap_fn=analyze_phase3_bootstrap,
        finalize_trace_registry_fn=finalize_trace_registry,
        generate_phase3_delivery_handoff_fn=generate_phase3_delivery_handoff,
        finalize_phase3_delivery_closure_fn=finalize_phase3_delivery_closure,
        refresh_phase3_post_execution_fn=refresh_phase3_post_execution,
        execute_phase3_mainline_backend_verification_fn=execute_phase3_mainline_backend_verification,
    )
    summary["thinking_value_gain_mode"] = context.thinking_value_gain_mode
    summary["thinking_value_gain_output_profile"] = context.thinking_value_gain_output_profile
    emit_human_review_surface(context.output_dir, "phase3")
    return emit_phase3_runner_summary(summary)


def main(
    argv: list[str] | None = None,
    *,
    runner_actor: str = "run_impl_foundation",
    generation_entrypoint: str = "scripts/phase3/run_impl_foundation.py",
) -> int:
    args = parse_phase3_first_version_args(argv)
    args.runner_actor = runner_actor
    args.generation_entrypoint = generation_entrypoint
    try:
        validate_phase3_runner_args(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    context = build_phase3_runner_context(args)
    if args.mainline_stage == "bootstrap":
        return run_phase3_bootstrap_stage(args, context)

    return run_phase3_foundation_mainline(args, context)


if __name__ == "__main__":
    raise SystemExit(main())
