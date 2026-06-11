#!/usr/bin/env python3
"""
Aggregate Phase-3 verification reports into an evidence ledger.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_verification_ledger
from phase3.execution_packet_access import load_json, load_json_if_exists
from phase3.review_support import write_json_and_markdown_report
import phase3.verification_execution as verification_execution


LEGACY_TARGETED_STEP = verification_execution.LEGACY_TARGETED_STEP
CRITICAL_TARGETED_STEP = verification_execution.CRITICAL_TARGETED_STEP
FULL_TARGETED_STEP = verification_execution.FULL_TARGETED_STEP
VERIFICATION_STEP_NAMES = verification_execution.VERIFICATION_STEP_NAMES


def summarize_int_values(values: list[int]) -> dict[str, int]:
    if not values:
        return {"sample_count": 0, "min": 0, "max": 0, "avg": 0, "total": 0}
    return {
        "sample_count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": round(sum(values) / len(values)),
        "total": sum(values),
    }


def empty_verification_ledger() -> dict[str, Any]:
    return {
        "summary": {
            "tracked_packet_count": 0,
            "successful_packet_count": 0,
            "failed_packet_count": 0,
            "aggregated_passed_test_count": 0,
            "aggregated_verification_duration_ms": 0,
        },
        "latest_by_packet": {},
        "aggregated": {
            "passed_tests": [],
            "packet_ids_with_green_verification": [],
            "step_status": {step: "unknown" for step in VERIFICATION_STEP_NAMES},
            "backend_truth": {
                "successful_backend_packet_count": 0,
                "packets_requiring_persistence_truth": 0,
                "service_boundary_truth_packet_count": 0,
                "sql_persistence_truth_packet_count": 0,
                "service_persistence_roundtrip_truth_packet_count": 0,
                "migration_execution_packet_count": 0,
                "missing_truths_by_packet": {},
            },
            "verification_timing": {
                "measurement_source": "verification-ledger",
                "packet_duration_ms": summarize_int_values([]),
                "step_duration_ms": {
                    step: summarize_int_values([])
                    for step in VERIFICATION_STEP_NAMES
                },
            },
        },
    }


def build_verification_ledger_markdown(ledger: dict[str, Any], output_locale: str | None = None) -> str:
    summary = ledger.get("summary", {})
    aggregated = ledger.get("aggregated", {})
    step_status = aggregated.get("step_status", {})
    lines = [
        "# Phase-3 Verification Ledger",
        "",
        "## Summary",
        f"- tracked_packet_count: {summary.get('tracked_packet_count', 0)}",
        f"- successful_packet_count: {summary.get('successful_packet_count', 0)}",
        f"- failed_packet_count: {summary.get('failed_packet_count', 0)}",
        f"- aggregated_passed_test_count: {summary.get('aggregated_passed_test_count', 0)}",
        f"- aggregated_verification_duration_ms: {summary.get('aggregated_verification_duration_ms', 0)}",
        "",
        "## Aggregated Step Status",
        f"- lint: {step_status.get('lint', 'unknown')}",
        f"- typecheck: {step_status.get('typecheck', 'unknown')}",
        f"- critical-targeted-tests: {step_status.get('critical-targeted-tests', 'unknown')}",
        f"- targeted-tests: {step_status.get('targeted-tests', 'unknown')}",
        f"- full-targeted-tests: {step_status.get('full-targeted-tests', 'unknown')}",
        f"- unit-tests: {step_status.get('unit-tests', 'unknown')}",
        f"- build: {step_status.get('build', 'unknown')}",
        "",
        "## Packet Entries",
    ]
    latest_by_packet = ledger.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict) or not latest_by_packet:
        lines.append("- none")
    else:
        for packet_id in sorted(latest_by_packet):
            row = latest_by_packet[packet_id]
            lines.append(
                f"- {packet_id} [{row.get('overall_verdict', 'unknown')}] "
                f"passed_tests={len(row.get('passed_tests', []))} run_dir={row.get('run_dir', 'n/a')}"
            )
    return localize_phase3_verification_ledger("\n".join(lines) + "\n", output_locale)


def extract_step_verdicts(verification_report: dict[str, Any]) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    for row in verification_report.get("steps", []):
        if not isinstance(row, dict):
            continue
        step = str(row.get("step", "")).strip()
        verdict = str(row.get("verdict", "")).strip()
        if step and verdict:
            verdicts[step] = verdict
    if CRITICAL_TARGETED_STEP in verdicts and LEGACY_TARGETED_STEP not in verdicts:
        verdicts[LEGACY_TARGETED_STEP] = verdicts[CRITICAL_TARGETED_STEP]
    if FULL_TARGETED_STEP in verdicts and LEGACY_TARGETED_STEP not in verdicts:
        verdicts[LEGACY_TARGETED_STEP] = verdicts[FULL_TARGETED_STEP]
    return verdicts


def extract_step_durations(verification_report: dict[str, Any]) -> dict[str, int]:
    durations: dict[str, int] = {}
    for row in verification_report.get("steps", []):
        if not isinstance(row, dict):
            continue
        step = str(row.get("step", "")).strip()
        value = row.get("duration_ms", 0)
        if step and isinstance(value, (int, float)):
            durations[step] = int(value)
    if CRITICAL_TARGETED_STEP in durations and LEGACY_TARGETED_STEP not in durations:
        durations[LEGACY_TARGETED_STEP] = durations[CRITICAL_TARGETED_STEP]
    if FULL_TARGETED_STEP in durations and LEGACY_TARGETED_STEP not in durations:
        durations[LEGACY_TARGETED_STEP] = durations[FULL_TARGETED_STEP]
    return durations


def verification_entry_from_report(
    *,
    verification_report: dict[str, Any],
    verification_report_path: Path | None = None,
) -> dict[str, Any]:
    packet = str(verification_report.get("packet_id", "")).strip()
    if not packet:
        raise ValueError("verification report missing packet_id")
    report_path_keys = ("test_report_path", "unit_test_report_path") + (
        ("full_test_report_path",)
        if str(verification_report.get("full_test_report_path", "")).strip()
        else ()
    )
    step_reports = [
        load_json_if_exists(
            Path(str(verification_report.get(path_key, "")).strip()).resolve()
            if str(verification_report.get(path_key, "")).strip()
            else None
        )
        or {}
        for path_key in report_path_keys
    ]
    passed_tests = sorted(
        {
            str(item).strip()
            for step_report in step_reports
            for item in step_report.get("passed_tests", [])
            if str(item).strip()
        }
    )
    failed_tests = sorted(
        {
            str(item).strip()
            for step_report in step_reports
            for item in step_report.get("failed_tests", [])
            if str(item).strip()
        }
    )
    step_duration_ms = extract_step_durations(verification_report)
    return {
        "packet_id": packet,
        "lane": str(verification_report.get("lane", "")).strip(),
        "work_package_ids": [
            str(item).strip()
            for item in verification_report.get("work_package_ids", [])
            if str(item).strip()
        ],
        "overall_verdict": str(verification_report.get("overall_verdict", "")).strip() or "unknown",
        "report_path": str(verification_report_path.resolve()) if verification_report_path else "",
        "workspace_root": str(verification_report.get("workspace_root", "")).strip(),
        "run_dir": str(verification_report.get("run_dir", "")).strip(),
        "test_report_path": str(verification_report.get("test_report_path", "")).strip(),
        "full_test_report_path": str(verification_report.get("full_test_report_path", "")).strip(),
        "unit_test_report_path": str(verification_report.get("unit_test_report_path", "")).strip(),
        "lint_report_path": str(verification_report.get("lint_report_path", "")).strip(),
        "typecheck_report_path": str(verification_report.get("typecheck_report_path", "")).strip(),
        "build_report_path": str(verification_report.get("build_report_path", "")).strip(),
        "step_verdicts": extract_step_verdicts(verification_report),
        "step_duration_ms": step_duration_ms,
        "packet_duration_ms": sum(step_duration_ms.values()),
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "backend_evidence": verification_report.get("backend_evidence")
        if isinstance(verification_report.get("backend_evidence"), dict)
        else None,
    }


def update_verification_ledger(
    *,
    ledger: dict[str, Any],
    verification_report: dict[str, Any],
    verification_report_path: Path | None = None,
) -> dict[str, Any]:
    latest_by_packet = ledger.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict):
        latest_by_packet = {}
    else:
        latest_by_packet = dict(latest_by_packet)

    entry = verification_entry_from_report(
        verification_report=verification_report,
        verification_report_path=verification_report_path,
    )
    latest_by_packet[entry["packet_id"]] = entry

    all_entries = [row for row in latest_by_packet.values() if isinstance(row, dict)]
    successful_entries = [
        row
        for row in all_entries
        if str(row.get("overall_verdict", "")).strip() == "pass"
    ]
    passed_tests = sorted(
        {
            str(test).strip()
            for row in all_entries
            for test in row.get("passed_tests", [])
            if str(test).strip()
        }
    )
    step_status = {}
    for step in VERIFICATION_STEP_NAMES:
        verdicts = [
            str(row.get("step_verdicts", {}).get(step, "")).strip()
            for row in all_entries
            if isinstance(row, dict)
            and str(row.get("step_verdicts", {}).get(step, "")).strip()
        ]
        if not verdicts:
            step_status[step] = "unknown"
        elif any(verdict == "fail" for verdict in verdicts):
            step_status[step] = "fail"
        elif all(verdict == "pass" for verdict in verdicts):
            step_status[step] = "pass"
        else:
            step_status[step] = "unknown"

    packet_durations = [
        int(row.get("packet_duration_ms", 0) or 0)
        for row in all_entries
        if isinstance(row, dict) and isinstance(row.get("packet_duration_ms", 0), (int, float))
    ]
    step_duration_ms = {}
    for step in VERIFICATION_STEP_NAMES:
        samples = [
            int(row.get("step_duration_ms", {}).get(step, 0) or 0)
            for row in all_entries
            if isinstance(row, dict)
            and isinstance(row.get("step_duration_ms", {}), dict)
            and step in row.get("step_duration_ms", {})
        ]
        step_duration_ms[step] = summarize_int_values(samples)

    failed_packet_count = sum(
        1
        for row in latest_by_packet.values()
        if isinstance(row, dict) and str(row.get("overall_verdict", "")).strip() == "fail"
    )
    successful_backend_entries = [
        row
        for row in successful_entries
        if isinstance(row, dict) and str(row.get("lane", "")).strip().lower() == "backend"
    ]
    backend_missing_truths = {
        str(row.get("packet_id", "")).strip(): list(row.get("backend_evidence", {}).get("missing_truths", []))
        for row in successful_backend_entries
        if isinstance(row.get("backend_evidence"), dict) and row.get("backend_evidence", {}).get("missing_truths")
    }
    return {
        "summary": {
            "tracked_packet_count": len(latest_by_packet),
            "successful_packet_count": len(successful_entries),
            "failed_packet_count": failed_packet_count,
            "aggregated_passed_test_count": len(passed_tests),
            "aggregated_verification_duration_ms": sum(packet_durations),
        },
        "latest_by_packet": {
            packet: latest_by_packet[packet]
            for packet in sorted(latest_by_packet)
        },
        "aggregated": {
            "passed_tests": passed_tests,
            "packet_ids_with_green_verification": sorted(
                str(row.get("packet_id", "")).strip()
                for row in successful_entries
                if str(row.get("packet_id", "")).strip()
            ),
            "step_status": step_status,
            "backend_truth": {
                "successful_backend_packet_count": len(successful_backend_entries),
                "packets_requiring_persistence_truth": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("requires_persistence_truth"))
                ),
                "service_boundary_truth_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("service_boundary_truth"))
                ),
                "sql_persistence_truth_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("sql_persistence_truth"))
                ),
                "service_persistence_roundtrip_truth_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("service_persistence_roundtrip_truth"))
                ),
                "migration_execution_packet_count": sum(
                    1
                    for row in successful_backend_entries
                    if isinstance(row.get("backend_evidence"), dict)
                    and bool(row.get("backend_evidence", {}).get("migration_execution"))
                ),
                "missing_truths_by_packet": backend_missing_truths,
            },
            "verification_timing": {
                "measurement_source": "verification-ledger",
                "packet_duration_ms": summarize_int_values(packet_durations),
                "step_duration_ms": step_duration_ms,
            },
        },
    }


def record_verification_report(
    *,
    ledger_path: Path,
    verification_report_path: Path,
) -> dict[str, Any]:
    ledger = load_json_if_exists(ledger_path.resolve()) or empty_verification_ledger()
    verification_report = load_json(verification_report_path.resolve())
    updated = update_verification_ledger(
        ledger=ledger,
        verification_report=verification_report,
        verification_report_path=verification_report_path,
    )
    markdown_path = ledger_path.with_suffix(".md")
    paths = write_json_and_markdown_report(
        json_path=ledger_path,
        report=updated,
        markdown=build_verification_ledger_markdown(updated),
        markdown_path=markdown_path,
    )
    return {
        "output_path": paths["json_path"],
        "markdown_path": paths["markdown_path"],
        **updated["summary"],
    }


def synthesize_gate_inputs_from_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    aggregated = ledger.get("aggregated", {})
    if not isinstance(aggregated, dict):
        aggregated = {}
    step_status = aggregated.get("step_status", {})
    if not isinstance(step_status, dict):
        step_status = {}
    return {
        "test_report": {
            "passed_tests": sorted(
                {
                    str(item).strip()
                    for item in aggregated.get("passed_tests", [])
                    if str(item).strip()
                }
            )
        },
        "lint_report": {"verdict": "pass"} if step_status.get("lint") == "pass" else None,
        "typecheck_report": {"verdict": "pass"} if step_status.get("typecheck") == "pass" else None,
        "build_report": {"verdict": "pass"} if step_status.get("build") == "pass" else None,
    }
