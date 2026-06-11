#!/usr/bin/env python3
"""
Generate the first Phase-3 foundation package from a completed Phase-2 root.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from phase3.phase3_delivery_gate import generate_phase3_delivery_handoff
from phase3.delivery_closure import finalize_phase3_delivery_closure
from phase3.dispatch_lane_bootstrap import initialize_optional_dispatch_lane, select_bootstrap_worker_packet
from phase3.foundation_bootstrap import (
    emit_phase3_bootstrap_artifacts,
    load_phase2_source_texts,
    run_phase3_bootstrap_stage_impl,
)
from phase3.mainline_backend_execution import execute_phase3_mainline_backend_verification
from phase3.foundation_mainline import run_phase3_foundation_mainline_impl
from phase3.post_execution_refresh import refresh_phase3_post_execution
from phase3.phase3_implementation_scaffolder import scaffold_phase3_implementation
from phase3.phase3_project_scaffold import generate_project_scaffold
from phase3.phase3_quality_check import analyze_phase3_bootstrap
from phase3.phase3_stack_decision import build_stack_decision_document
from phase3.trace_registry import finalize_trace_registry, initialize_phase3_trace_registry
from phase3.phase3_toolchain_bootstrap import bootstrap_phase3_toolchain
from common.output_language import localize_phase3_coverage_plan, resolve_output_locale
from phase3.schema_test_scaffolder import scaffold_schema_tests


@dataclass(frozen=True)
class Phase3RunnerContext:
    phase2_root: Path
    output_dir: Path
    output_locale: str
    ui_locale: str


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
    return build_parser().parse_args(argv)


def validate_phase3_runner_args(args: argparse.Namespace) -> None:
    if args.mainline_stage == "bootstrap" and args.enable_dispatch_lane:
        raise ValueError("--enable-dispatch-lane is only available for --mainline-stage foundation")

    if args.require_frontend_contract and not args.enable_ui_fallback:
        raise ValueError("--require-frontend-contract currently requires --enable-ui-fallback")


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
    )


def run_phase3_bootstrap_stage(args: argparse.Namespace, context: Phase3RunnerContext) -> int:
    summary = run_phase3_bootstrap_stage_impl(
        args=args,
        phase2_root=context.phase2_root,
        output_dir=context.output_dir,
        ui_locale=context.ui_locale,
        analyze_phase3_bootstrap_fn=analyze_phase3_bootstrap,
    )
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
        "--module-synthesis-bundle",
        dest="module_synthesis_bundle_path",
        default="",
        help="explicit opt-in directory for phase3-module-synthesis-bundle.v1 selected-module authoring",
    )
    return parser

def run_phase3_foundation_mainline(args: argparse.Namespace, context: Phase3RunnerContext) -> int:
    esp_text, stage_03_text, stage_04_text = load_phase2_source_texts(context.phase2_root)
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
    return emit_phase3_runner_summary(summary)


def main() -> int:
    args = parse_phase3_first_version_args()
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
