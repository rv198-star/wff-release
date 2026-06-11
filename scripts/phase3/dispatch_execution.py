from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from common.output_language import localize_phase3_dispatch_cycle_report, localize_phase3_dispatch_loop_report


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_dispatch_cycle_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 Dispatch Cycle Report",
        "",
        "## Summary",
        f"- mode: {report['mode']}",
        f"- processed_packet_count: {report['processed_packet_count']}",
        f"- initial_dispatchable_packet_count: {report['initial_dispatchable_packet_count']}",
        f"- final_dispatchable_packet_count: {report['final_dispatchable_packet_count']}",
        "",
    ]
    preflight = report.get("preflight", {})
    if isinstance(preflight, dict) and preflight.get("status") == "blocked":
        lines.extend(
            [
                "## Preflight",
                f"- status: {preflight.get('status', 'unknown')}",
                f"- reason: {preflight.get('reason', 'unknown')}",
                f"- bootstrap_command: {preflight.get('bootstrap_command', 'n/a')}",
                "",
            ]
        )
    lines.append("## Processed Packets")
    for row in report.get("results", []) or [{"packet_id": "none", "post_state": "", "run_dir": ""}]:
        if row["packet_id"] == "none":
            lines.append("- none")
        else:
            lines.append(f"- {row['packet_id']} -> {row['post_state']} run_dir={row['run_dir']}")
    return localize_phase3_dispatch_cycle_report("\n".join(lines) + "\n", output_locale)


def build_dispatch_loop_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 Dispatch Loop Report",
        "",
        "## Summary",
        f"- mode: {report['mode']}",
        f"- cycle_count: {report['cycle_count']}",
        f"- processed_packet_count: {report['processed_packet_count']}",
        f"- final_dispatchable_packet_count: {report['final_dispatchable_packet_count']}",
        "",
    ]
    preflight = report.get("preflight", {})
    if isinstance(preflight, dict) and preflight.get("status") == "blocked":
        lines.extend(
            [
                "## Preflight",
                f"- status: {preflight.get('status', 'unknown')}",
                f"- reason: {preflight.get('reason', 'unknown')}",
                f"- bootstrap_command: {preflight.get('bootstrap_command', 'n/a')}",
                "",
            ]
        )
    lines.append("## Cycles")
    for row in report.get("cycles", []) or [{"cycle_index": 0, "processed_packet_count": 0, "final_dispatchable_packet_count": 0}]:
        if not row.get("cycle_index"):
            lines.append("- none")
        else:
            lines.append(
                f"- cycle={row['cycle_index']} processed={row['processed_packet_count']} remaining_ready={row['final_dispatchable_packet_count']}"
            )
    return localize_phase3_dispatch_loop_report("\n".join(lines) + "\n", output_locale)


def persist_dispatch_report(
    *,
    output_dir: Path,
    stem: str,
    report: dict[str, Any],
    markdown_builder: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    report_path = output_dir / f"{stem}.json"
    report_md_path = output_dir / f"{stem}.md"
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(report_md_path, markdown_builder(report))
    return {
        **report,
        "report_path": str(report_path),
        "report_markdown_path": str(report_md_path),
    }


def run_dispatch_cycle_impl(
    *,
    output_dir: Path,
    mode: str,
    max_packets: int,
    actor: str,
    note: str,
    wp_gate_report_path: Path | None,
    runtime_environment_ledger_path: Path | None,
    run_runtime_smoke: bool,
    runtime_smoke_service_url: str | None,
    refresh_post_execution: bool,
    refresh_execution_dispatch_state_fn: Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path | None]],
    evaluate_dispatch_preflight_fn: Callable[..., dict[str, Any]],
    load_json_fn: Callable[[Path], dict[str, Any]],
    sorted_dispatchable_packets_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    current_runtime_row_fn: Callable[[dict[str, Any], str], dict[str, Any] | None],
    cap_frontend_packet_unlocked_by_runtime_ceiling_fn: Callable[[Path, dict[str, Any], dict[str, Any]], bool],
    run_worker_packet_fn: Callable[..., dict[str, Any]],
    refresh_phase3_post_execution_fn: Callable[..., dict[str, Any]],
    resolve_runtime_smoke_service_url_fn: Callable[[str | None], str],
    persist_dispatch_report_fn: Callable[..., dict[str, Any]],
    build_markdown_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    execution_loop_plan, initial_dispatch, runtime_state, resolved_runtime_environment_ledger_path = (
        refresh_execution_dispatch_state_fn(
            output_dir=output_dir,
            wp_gate_report_path=wp_gate_report_path,
            runtime_environment_ledger_path=runtime_environment_ledger_path,
        )
    )
    dispatchable_rows = sorted_dispatchable_packets_fn(runtime_state)

    results: list[dict[str, Any]] = []
    processed_packet_count = 0
    skipped_packet_count = 0
    preflight: dict[str, Any] = {"status": "not-needed", "selected_packets": []}
    if mode in {"execute-verification", "execute-and-apply-gate"}:
        preflight = evaluate_dispatch_preflight_fn(
            output_dir=output_dir,
            execution_loop_plan=execution_loop_plan,
            dispatchable_rows=dispatchable_rows,
            max_packets=max_packets,
        )
        if preflight.get("status") == "blocked":
            report = {
                "mode": mode,
                "max_packets": max_packets,
                "actor": actor,
                "note": note,
                "initial_dispatchable_packet_count": int(initial_dispatch.get("dispatchable_packet_count", 0) or 0),
                "final_dispatchable_packet_count": len(dispatchable_rows),
                "processed_packet_count": 0,
                "skipped_packet_count": 0,
                "results": [],
                "runtime_state_path": str(output_dir / "execution-runtime-state.json"),
                "dispatch_manifest_path": str(output_dir / "dispatch-manifest.json"),
                "post_execution_refresh": {},
                "preflight": preflight,
                "run_runtime_smoke": run_runtime_smoke,
                "runtime_smoke_service_url": resolve_runtime_smoke_service_url_fn(runtime_smoke_service_url),
            }
            return persist_dispatch_report_fn(
                output_dir=output_dir,
                stem="dispatch-cycle-report",
                report=report,
                markdown_builder=build_markdown_fn,
            )
    for row in dispatchable_rows[: max(0, max_packets)]:
        packet_id = str(row.get("packet_id", "")).strip()
        if not packet_id:
            continue
        current_runtime_state = load_json_fn(output_dir / "execution-runtime-state.json")
        current_row = current_runtime_row_fn(current_runtime_state, packet_id)
        current_state = str(current_row.get("current_state", "")).strip() if current_row else "missing"
        if current_row and cap_frontend_packet_unlocked_by_runtime_ceiling_fn(output_dir, current_runtime_state, current_row):
            current_state = str(current_row.get("current_state", "")).strip() or "implemented"
        if current_state != "ready":
            results.append(
                {
                    "packet_id": packet_id,
                    "mode": mode,
                    "dispatchable_when_selected": False,
                    "event_statuses_recorded": [],
                    "verification_overall_verdict": "",
                    "run_dir": "",
                    "run_report_path": "",
                    "run_report_markdown_path": "",
                    "post_state": current_state or "unknown",
                    "skipped": True,
                    "skipped_reason": f"packet state changed before execution: {current_state or 'unknown'}",
                }
            )
            skipped_packet_count += 1
            continue
        results.append(
            run_worker_packet_fn(
                output_dir=output_dir,
                packet=packet_id,
                mode=mode,
                actor=actor or "phase3-dispatch-runner",
                note=note,
                wp_gate_report_path=wp_gate_report_path,
                runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
            )
        )
        processed_packet_count += 1

    final_runtime_state = load_json_fn(output_dir / "execution-runtime-state.json")
    final_dispatchable_rows = sorted_dispatchable_packets_fn(final_runtime_state)
    report = {
        "mode": mode,
        "max_packets": max_packets,
        "actor": actor,
        "note": note,
        "initial_dispatchable_packet_count": int(initial_dispatch.get("dispatchable_packet_count", 0) or 0),
        "final_dispatchable_packet_count": len(final_dispatchable_rows),
        "processed_packet_count": processed_packet_count,
        "skipped_packet_count": skipped_packet_count,
        "results": results,
        "runtime_state_path": str(output_dir / "execution-runtime-state.json"),
        "dispatch_manifest_path": str(output_dir / "dispatch-manifest.json"),
        "post_execution_refresh": (
            refresh_phase3_post_execution_fn(
                output_dir,
                run_runtime_smoke=run_runtime_smoke,
                runtime_smoke_service_url=runtime_smoke_service_url,
            )
            if refresh_post_execution
            else {}
        ),
        "preflight": preflight,
        "run_runtime_smoke": run_runtime_smoke,
        "runtime_smoke_service_url": resolve_runtime_smoke_service_url_fn(runtime_smoke_service_url),
    }
    return persist_dispatch_report_fn(
        output_dir=output_dir,
        stem="dispatch-cycle-report",
        report=report,
        markdown_builder=build_markdown_fn,
    )


def run_dispatch_loop_impl(
    *,
    output_dir: Path,
    mode: str,
    max_cycles: int,
    max_packets_per_cycle: int,
    actor: str,
    note: str,
    wp_gate_report_path: Path | None,
    runtime_environment_ledger_path: Path | None,
    run_runtime_smoke: bool,
    runtime_smoke_service_url: str | None,
    refresh_execution_dispatch_state_fn: Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path | None]],
    sorted_dispatchable_packets_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    load_json_fn: Callable[[Path], dict[str, Any]],
    run_dispatch_cycle_fn: Callable[..., dict[str, Any]],
    refresh_phase3_post_execution_fn: Callable[..., dict[str, Any]],
    resolve_runtime_smoke_service_url_fn: Callable[[str | None], str],
    persist_dispatch_report_fn: Callable[..., dict[str, Any]],
    build_loop_markdown_fn: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    cycles: list[dict[str, Any]] = []
    total_processed = 0
    preflight: dict[str, Any] = {"status": "not-needed", "selected_packets": []}

    for cycle_index in range(1, max(1, max_cycles) + 1):
        _, _, runtime_state, resolved_runtime_environment_ledger_path = refresh_execution_dispatch_state_fn(
            output_dir=output_dir,
            wp_gate_report_path=wp_gate_report_path,
            runtime_environment_ledger_path=runtime_environment_ledger_path,
        )
        dispatchable_rows = sorted_dispatchable_packets_fn(runtime_state)
        if not dispatchable_rows:
            break
        max_packets = (
            len(dispatchable_rows)
            if max_packets_per_cycle <= 0
            else min(len(dispatchable_rows), max_packets_per_cycle)
        )
        cycle_report = run_dispatch_cycle_fn(
            output_dir=output_dir,
            mode=mode,
            max_packets=max_packets,
            actor=actor,
            note=note,
            wp_gate_report_path=wp_gate_report_path,
            runtime_environment_ledger_path=resolved_runtime_environment_ledger_path,
            run_runtime_smoke=False,
            runtime_smoke_service_url=runtime_smoke_service_url,
            refresh_post_execution=False,
        )
        cycles.append(
            {
                "cycle_index": cycle_index,
                "processed_packet_count": cycle_report["processed_packet_count"],
                "initial_dispatchable_packet_count": cycle_report["initial_dispatchable_packet_count"],
                "final_dispatchable_packet_count": cycle_report["final_dispatchable_packet_count"],
                "results": cycle_report["results"],
                "preflight": cycle_report.get("preflight", {}),
            }
        )
        total_processed += cycle_report["processed_packet_count"]
        if isinstance(cycle_report.get("preflight"), dict):
            preflight = cycle_report["preflight"]
        if cycle_report["processed_packet_count"] == 0 or mode == "plan-only":
            break

    final_runtime_state = load_json_fn(output_dir / "execution-runtime-state.json")
    final_dispatchable_rows = sorted_dispatchable_packets_fn(final_runtime_state)
    report = {
        "mode": mode,
        "max_cycles": max_cycles,
        "max_packets_per_cycle": max_packets_per_cycle,
        "actor": actor,
        "note": note,
        "cycle_count": len(cycles),
        "processed_packet_count": total_processed,
        "final_dispatchable_packet_count": len(final_dispatchable_rows),
        "cycles": cycles,
        "runtime_state_path": str(output_dir / "execution-runtime-state.json"),
        "dispatch_manifest_path": str(output_dir / "dispatch-manifest.json"),
        "post_execution_refresh": refresh_phase3_post_execution_fn(
            output_dir,
            run_runtime_smoke=run_runtime_smoke,
            runtime_smoke_service_url=runtime_smoke_service_url,
        ),
        "preflight": preflight,
        "run_runtime_smoke": run_runtime_smoke,
        "runtime_smoke_service_url": resolve_runtime_smoke_service_url_fn(runtime_smoke_service_url),
    }
    return persist_dispatch_report_fn(
        output_dir=output_dir,
        stem="dispatch-loop-report",
        report=report,
        markdown_builder=build_loop_markdown_fn,
    )
