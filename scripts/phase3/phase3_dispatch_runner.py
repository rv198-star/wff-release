#!/usr/bin/env python3
"""
Execute the current dispatchable packet queue for Phase-3.
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
from typing import Any

from phase3.phase3_runtime_smoke import run_phase3_runtime_smoke
from phase3.dispatch_execution import (
    build_dispatch_cycle_markdown,
    build_dispatch_loop_markdown,
    persist_dispatch_report,
    run_dispatch_cycle_impl,
    run_dispatch_loop_impl,
)
from phase3.dispatch_runtime import (
    cap_frontend_packet_unlocked_by_runtime_ceiling,
    evaluate_dispatch_preflight,
    refresh_execution_dispatch_state,
)
from phase3.post_execution_refresh import (
    refresh_phase3_post_execution as refresh_phase3_post_execution_support,
    resolve_delivery_bootstrap_report,
    resolve_runtime_smoke_service_url,
)
from phase3.runtime_environment import generate_runtime_environment_ledger as generate_runtime_environment_ledger_support
from phase3.runtime_environment import detect_current_available_runtime_environments as detect_current_available_runtime_environments_support
from phase3.runtime_environment import refresh_runtime_environment_ledger as refresh_runtime_environment_ledger_support
from phase3.worker_packet_runner import RUN_MODES, current_runtime_row, load_json, run_worker_packet, sorted_dispatchable_packets
from phase3.wp_gate_cycle import run_wp_gate_cycle
from phase3.phase3_toolchain_bootstrap import bootstrap_phase3_toolchain
from phase3.phase3_toolchain_bootstrap import command_version, compose_version

CLI_MODES = tuple(sorted({*RUN_MODES, "wp-gate-cycle"}))


@dataclass(frozen=True)
class Phase3DispatchRunnerContext:
    output_dir: Path
    wp_gate_report_path: Path | None
    test_report_path: Path | None
    implementation_bindings_path: Path | None
    typecheck_report_path: Path | None
    lint_report_path: Path | None
    build_report_path: Path | None
    verification_ledger_path: Path | None
    runtime_environment_ledger_path: Path | None
    runtime_smoke_service_url: str | None


def detect_current_available_runtime_environments(
    *,
    explicit_available_runtime_environments: list[str] | None = None,
    bootstrap_report: dict[str, Any] | None = None,
) -> list[str]:
    return detect_current_available_runtime_environments_support(
        explicit_available_runtime_environments=explicit_available_runtime_environments,
        bootstrap_report=bootstrap_report,
        command_version_fn=command_version,
        compose_version_fn=compose_version,
    )


def generate_runtime_environment_ledger(
    *,
    execution_loop_plan: dict[str, Any],
    output_dir: Path,
    available_runtime_environments: list[str] | None = None,
) -> dict[str, Any]:
    return generate_runtime_environment_ledger_support(
        execution_loop_plan=execution_loop_plan,
        output_dir=output_dir,
        available_runtime_environments=available_runtime_environments,
    )


def refresh_runtime_environment_ledger(
    *,
    execution_loop_plan_path: Path,
    output_dir: Path,
    output_path: Path | None = None,
    explicit_available_runtime_environments: list[str] | None = None,
    bootstrap_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return refresh_runtime_environment_ledger_support(
        execution_loop_plan_path=execution_loop_plan_path,
        output_dir=output_dir,
        output_path=output_path,
        explicit_available_runtime_environments=explicit_available_runtime_environments,
        bootstrap_report=bootstrap_report,
        command_version_fn=command_version,
        compose_version_fn=compose_version,
    )


def refresh_phase3_post_execution(
    output_dir: Path,
    *,
    retained_proof_mode: bool = False,
    run_runtime_smoke: bool = False,
    runtime_smoke_service_url: str | None = None,
    skip_coverage_collection: bool = False,
    coverage_collection_skip_reason: str = "",
    toolchain_bootstrap_report_path: Path | None = None,
    unit_test_report_path: Path | None = None,
    coverage_gate_report_path: Path | None = None,
    wp_gate_report_path: Path | None = None,
    verification_ledger_report_path: Path | None = None,
    runtime_smoke_report_path: Path | None = None,
) -> dict[str, Any]:
    return refresh_phase3_post_execution_support(
        output_dir,
        retained_proof_mode=retained_proof_mode,
        run_runtime_smoke=run_runtime_smoke,
        runtime_smoke_service_url=runtime_smoke_service_url,
        runtime_smoke_fn=run_phase3_runtime_smoke,
        skip_coverage_collection=skip_coverage_collection,
        coverage_collection_skip_reason=coverage_collection_skip_reason,
        toolchain_bootstrap_report_path=toolchain_bootstrap_report_path,
        unit_test_report_path=unit_test_report_path,
        coverage_gate_report_path=coverage_gate_report_path,
        wp_gate_report_path=wp_gate_report_path,
        verification_ledger_report_path=verification_ledger_report_path,
        runtime_smoke_report_path=runtime_smoke_report_path,
    )


def run_dispatch_cycle(
    *,
    output_dir: Path,
    mode: str = "plan-only",
    max_packets: int = 1,
    actor: str = "",
    note: str = "",
    wp_gate_report_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
    run_runtime_smoke: bool = False,
    runtime_smoke_service_url: str | None = None,
    refresh_post_execution: bool = True,
) -> dict[str, Any]:
    return run_dispatch_cycle_impl(
        output_dir=output_dir,
        mode=mode,
        max_packets=max_packets,
        actor=actor,
        note=note,
        wp_gate_report_path=wp_gate_report_path.resolve() if wp_gate_report_path is not None else None,
        runtime_environment_ledger_path=(
            runtime_environment_ledger_path.resolve() if runtime_environment_ledger_path is not None else None
        ),
        run_runtime_smoke=run_runtime_smoke,
        runtime_smoke_service_url=runtime_smoke_service_url,
        refresh_post_execution=refresh_post_execution,
        refresh_execution_dispatch_state_fn=lambda **kwargs: refresh_execution_dispatch_state(
            **kwargs,
            refresh_runtime_environment_ledger_fn=refresh_runtime_environment_ledger,
        ),
        evaluate_dispatch_preflight_fn=lambda **kwargs: evaluate_dispatch_preflight(
            **kwargs,
            bootstrap_phase3_toolchain_fn=bootstrap_phase3_toolchain,
        ),
        load_json_fn=load_json,
        sorted_dispatchable_packets_fn=sorted_dispatchable_packets,
        current_runtime_row_fn=current_runtime_row,
        cap_frontend_packet_unlocked_by_runtime_ceiling_fn=cap_frontend_packet_unlocked_by_runtime_ceiling,
        run_worker_packet_fn=run_worker_packet,
        refresh_phase3_post_execution_fn=refresh_phase3_post_execution,
        resolve_runtime_smoke_service_url_fn=resolve_runtime_smoke_service_url,
        persist_dispatch_report_fn=persist_dispatch_report,
        build_markdown_fn=build_dispatch_cycle_markdown,
    )


def run_dispatch_loop(
    *,
    output_dir: Path,
    mode: str = "plan-only",
    max_cycles: int = 10,
    max_packets_per_cycle: int = 0,
    actor: str = "",
    note: str = "",
    wp_gate_report_path: Path | None = None,
    runtime_environment_ledger_path: Path | None = None,
    run_runtime_smoke: bool = False,
    runtime_smoke_service_url: str | None = None,
) -> dict[str, Any]:
    return run_dispatch_loop_impl(
        output_dir=output_dir,
        mode=mode,
        max_cycles=max_cycles,
        max_packets_per_cycle=max_packets_per_cycle,
        actor=actor,
        note=note,
        wp_gate_report_path=wp_gate_report_path.resolve() if wp_gate_report_path is not None else None,
        runtime_environment_ledger_path=(
            runtime_environment_ledger_path.resolve() if runtime_environment_ledger_path is not None else None
        ),
        run_runtime_smoke=run_runtime_smoke,
        runtime_smoke_service_url=runtime_smoke_service_url,
        refresh_execution_dispatch_state_fn=lambda **kwargs: refresh_execution_dispatch_state(
            **kwargs,
            refresh_runtime_environment_ledger_fn=refresh_runtime_environment_ledger,
        ),
        sorted_dispatchable_packets_fn=sorted_dispatchable_packets,
        load_json_fn=load_json,
        run_dispatch_cycle_fn=run_dispatch_cycle,
        refresh_phase3_post_execution_fn=refresh_phase3_post_execution,
        resolve_runtime_smoke_service_url_fn=resolve_runtime_smoke_service_url,
        persist_dispatch_report_fn=persist_dispatch_report,
        build_loop_markdown_fn=build_dispatch_loop_markdown,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the current Phase-3 dispatch cycle")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=CLI_MODES, default="plan-only")
    parser.add_argument("--packet")
    parser.add_argument("--wave", type=int)
    parser.add_argument("--lane")
    parser.add_argument("--max-packets", type=int, default=1)
    parser.add_argument("--repeat-until-stalled", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=10)
    parser.add_argument("--max-packets-per-cycle", type=int, default=0)
    parser.add_argument("--actor", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--wp-gate-report")
    parser.add_argument("--test-report")
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--typecheck-report")
    parser.add_argument("--lint-report")
    parser.add_argument("--build-report")
    parser.add_argument("--verification-ledger")
    parser.add_argument("--runtime-environment-ledger")
    parser.add_argument("--run-runtime-smoke", action="store_true")
    parser.add_argument("--runtime-smoke-service-url", default="")
    parser.add_argument("--allow-non-dispatchable", action="store_true")
    return parser


def parse_phase3_dispatch_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def validate_phase3_dispatch_args(args: argparse.Namespace) -> None:
    if args.mode == "wp-gate-cycle":
        if args.repeat_until_stalled:
            raise ValueError("--repeat-until-stalled is not supported for --mode wp-gate-cycle")
        if not args.test_report:
            raise ValueError("--test-report is required for --mode wp-gate-cycle")
        return

    if args.packet or args.wave is not None or args.lane:
        if args.repeat_until_stalled:
            raise ValueError("--repeat-until-stalled is not supported for packet-targeted execution")


def build_phase3_dispatch_runner_context(args: argparse.Namespace) -> Phase3DispatchRunnerContext:
    return Phase3DispatchRunnerContext(
        output_dir=Path(args.output_dir).resolve(),
        wp_gate_report_path=Path(args.wp_gate_report).resolve() if args.wp_gate_report else None,
        test_report_path=Path(args.test_report).resolve() if args.test_report else None,
        implementation_bindings_path=Path(args.implementation_bindings).resolve()
        if args.implementation_bindings
        else None,
        typecheck_report_path=Path(args.typecheck_report).resolve() if args.typecheck_report else None,
        lint_report_path=Path(args.lint_report).resolve() if args.lint_report else None,
        build_report_path=Path(args.build_report).resolve() if args.build_report else None,
        verification_ledger_path=Path(args.verification_ledger).resolve() if args.verification_ledger else None,
        runtime_environment_ledger_path=Path(args.runtime_environment_ledger).resolve()
        if args.runtime_environment_ledger
        else None,
        runtime_smoke_service_url=str(args.runtime_smoke_service_url).strip() or None,
    )


def emit_phase3_dispatch_summary(summary: dict[str, Any], *, success: bool = True) -> int:
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if success else 1


def run_wp_gate_cycle_mode(args: argparse.Namespace, context: Phase3DispatchRunnerContext) -> int:
    summary = run_wp_gate_cycle(
        output_dir=context.output_dir,
        test_report_path=context.test_report_path,
        implementation_bindings_path=context.implementation_bindings_path,
        typecheck_report_path=context.typecheck_report_path,
        lint_report_path=context.lint_report_path,
        build_report_path=context.build_report_path,
        verification_ledger_path=context.verification_ledger_path,
        runtime_environment_ledger_path=context.runtime_environment_ledger_path,
    )
    return emit_phase3_dispatch_summary(
        summary,
        success=summary["wp_gate_report"]["overall_quality_gate"] == "pass",
    )


def run_packet_targeted_dispatch(args: argparse.Namespace, context: Phase3DispatchRunnerContext) -> int:
    summary = run_worker_packet(
        output_dir=context.output_dir,
        packet=args.packet,
        wave=args.wave,
        lane=args.lane,
        mode=args.mode,
        actor=args.actor,
        note=args.note,
        wp_gate_report_path=context.wp_gate_report_path,
        runtime_environment_ledger_path=context.runtime_environment_ledger_path,
        allow_non_dispatchable=args.allow_non_dispatchable,
    )
    return emit_phase3_dispatch_summary(summary)


def run_dispatch_mainline(args: argparse.Namespace, context: Phase3DispatchRunnerContext) -> int:
    if args.repeat_until_stalled:
        summary = run_dispatch_loop(
            output_dir=context.output_dir,
            mode=args.mode,
            max_cycles=args.max_cycles,
            max_packets_per_cycle=args.max_packets_per_cycle,
            actor=args.actor,
            note=args.note,
            wp_gate_report_path=context.wp_gate_report_path,
            runtime_environment_ledger_path=context.runtime_environment_ledger_path,
            run_runtime_smoke=bool(args.run_runtime_smoke),
            runtime_smoke_service_url=context.runtime_smoke_service_url,
        )
    else:
        summary = run_dispatch_cycle(
            output_dir=context.output_dir,
            mode=args.mode,
            max_packets=args.max_packets,
            actor=args.actor,
            note=args.note,
            wp_gate_report_path=context.wp_gate_report_path,
            runtime_environment_ledger_path=context.runtime_environment_ledger_path,
            run_runtime_smoke=bool(args.run_runtime_smoke),
            runtime_smoke_service_url=context.runtime_smoke_service_url,
        )
    return emit_phase3_dispatch_summary(summary)


def main() -> int:
    args = parse_phase3_dispatch_args()
    try:
        validate_phase3_dispatch_args(args)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}")
        return 2

    context = build_phase3_dispatch_runner_context(args)
    if args.mode == "wp-gate-cycle":
        return run_wp_gate_cycle_mode(args, context)
    if args.packet or args.wave is not None or args.lane:
        return run_packet_targeted_dispatch(args, context)
    return run_dispatch_mainline(args, context)


if __name__ == "__main__":
    raise SystemExit(main())
