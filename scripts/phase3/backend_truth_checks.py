#!/usr/bin/env python3
"""
Backend evidence rollups for Phase-3 delivery closure.
"""

from __future__ import annotations

from typing import Any


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


def bootstrap_report_is_green(report: dict[str, Any] | None) -> bool:
    if not isinstance(report, dict):
        return False
    checks = report.get("checks", {}) if isinstance(report.get("checks", {}), dict) else {}
    toolchain_status = str(
        checks.get("toolchain_bootstrap_status")
        or checks.get("toolchain_bootstrap_raw_status")
        or ""
    ).strip().lower()
    if toolchain_status in {"ready", "toolchain-ready", "pass"}:
        return True
    if toolchain_status in {"fail", "failed", "blocked", "not-ready", "error"}:
        return False
    if report_is_pass(report):
        return True
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


def latest_packet_rows(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    latest_by_packet = report.get("latest_by_packet", {})
    if not isinstance(latest_by_packet, dict):
        return []
    return [row for row in latest_by_packet.values() if isinstance(row, dict)]


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
