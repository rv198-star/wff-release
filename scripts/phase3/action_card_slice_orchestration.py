from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_subagent_slice_orchestration_report
from phase3.review_support import write_json_and_markdown_report


READY_ORCHESTRATION_CLAIM_CEILING = (
    "orchestration evidence only; ready-for-slice-execution means slice contracts are schedulable, "
    "not implemented or runtime-verified; TPlan scout SubAgents may audit or score, while code edits require "
    "an explicit write-capable runner"
)
BLOCKED_ORCHESTRATION_CLAIM_CEILING = (
    "blocked slice orchestration only; no slice execution readiness claim while blockers or conflicts exist"
)
NOT_APPLICABLE_CLAIM_CEILING = "not applicable; no backend SubAgent slice run manifests found"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def discover_slice_run_manifests(output_dir: Path) -> list[Path]:
    worker_runs = output_dir / "worker-runs"
    if not worker_runs.exists():
        return []
    selected: list[Path] = []
    for packet_dir in sorted(path for path in worker_runs.iterdir() if path.is_dir()):
        manifests = sorted(
            packet_dir.glob("run-*/subagent-slice-run-manifest.json"),
            key=lambda path: _run_manifest_sort_key(path),
        )
        if manifests:
            selected.append(manifests[-1])
    return selected


def _run_manifest_sort_key(path: Path) -> tuple[int, str]:
    match = re.fullmatch(r"run-(\d+)", path.parent.name)
    if match:
        return (int(match.group(1)), path.parent.name)
    return (-1, path.parent.name)


def _summary_int(summary: dict[str, Any], key: str) -> int:
    return int(summary.get(key, 0) or 0)


def build_slice_orchestration_report(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    manifest_paths = discover_slice_run_manifests(output_dir)
    packet_rows: list[dict[str, Any]] = []
    slice_rows: list[dict[str, Any]] = []
    blockers: set[str] = set()
    totals = {
        "packet_count": 0,
        "slice_count": 0,
        "ready_slice_count": 0,
        "blocked_slice_count": 0,
        "actual_subagent_execution_count": 0,
        "write_runner_execution_count": 0,
        "read_only_review_count": 0,
        "action_card_runner_supported_count": 0,
        "runner_protocol_versions": [],
        "runner_kinds": [],
        "configured_authoring_max_workers": 0,
        "active_authoring_max_workers": 0,
        "configured_verification_max_workers": 0,
        "conflict_count": 0,
        "missing_evidence_count": 0,
    }
    for manifest_path in manifest_paths:
        manifest = _load_json(manifest_path)
        summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
        packet_id = str(manifest.get("packet_id") or manifest_path.parent.parent.name).strip()
        manifest_slice_runs = [row for row in _as_list(manifest.get("slice_runs")) if isinstance(row, dict)]
        derived_slice_count = len(manifest_slice_runs)
        derived_ready_count = sum(1 for row in manifest_slice_runs if str(row.get("slice_status") or "").strip() == "ready")
        derived_blocked_count = sum(
            1 for row in manifest_slice_runs if str(row.get("slice_status") or "").strip() == "blocked"
        )
        if (
            derived_slice_count != _summary_int(summary, "slice_count")
            or derived_ready_count != _summary_int(summary, "ready_slice_count")
            or derived_blocked_count != _summary_int(summary, "blocked_slice_count")
        ):
            blockers.add("manifest_summary_mismatch")
        packet_rows.append(
            {
                "packet_id": packet_id,
                "manifest_path": str(manifest_path),
                "overall_slice_run_status": str(manifest.get("overall_slice_run_status") or "unknown").strip(),
                "slice_count": derived_slice_count,
                "blocked_slice_count": derived_blocked_count,
                "conflict_count": _summary_int(summary, "conflict_count"),
                "packet_claim_ceiling": str(manifest.get("packet_claim_ceiling") or "").strip(),
            }
        )
        totals["packet_count"] += 1
        totals["slice_count"] += derived_slice_count
        totals["ready_slice_count"] += derived_ready_count
        totals["blocked_slice_count"] += derived_blocked_count
        totals["actual_subagent_execution_count"] += _summary_int(summary, "actual_subagent_execution_count")
        totals["write_runner_execution_count"] += _summary_int(summary, "write_runner_execution_count")
        totals["read_only_review_count"] += _summary_int(summary, "read_only_review_count")
        if bool(summary.get("action_card_runner_supported", summary.get("slice_runner_supported", False))):
            totals["action_card_runner_supported_count"] += 1
        protocol_version = str(summary.get("runner_protocol_version") or "").strip()
        if protocol_version and protocol_version not in totals["runner_protocol_versions"]:
            totals["runner_protocol_versions"].append(protocol_version)
        runner_kind = str(summary.get("runner_kind") or "").strip()
        if runner_kind and runner_kind not in totals["runner_kinds"]:
            totals["runner_kinds"].append(runner_kind)
        totals["configured_authoring_max_workers"] = max(
            totals["configured_authoring_max_workers"],
            _summary_int(summary, "configured_authoring_max_workers"),
        )
        totals["active_authoring_max_workers"] += _summary_int(summary, "active_authoring_max_workers")
        totals["configured_verification_max_workers"] = max(
            totals["configured_verification_max_workers"],
            _summary_int(summary, "configured_verification_max_workers"),
        )
        totals["conflict_count"] += _summary_int(summary, "conflict_count")
        totals["missing_evidence_count"] += _summary_int(summary, "missing_evidence_count")
        if derived_blocked_count:
            blockers.add("blocked_slice")
        if _summary_int(summary, "conflict_count"):
            blockers.add("owned_file_conflict")
        for slice_run in manifest_slice_runs:
            row_blockers = [str(item).strip() for item in _as_list(slice_run.get("blocking_reasons")) if str(item).strip()]
            blockers.update(row_blockers)
            slice_rows.append(
                {
                    "packet_id": packet_id,
                    "slice_id": str(slice_run.get("slice_id") or "").strip(),
                    "slice_status": str(slice_run.get("slice_status") or "unknown").strip(),
                    "operation_id": str(slice_run.get("operation_id") or "").strip(),
                    "operation_ids": _as_list(slice_run.get("operation_ids")),
                    "current_subagent_permission": str(
                        slice_run.get("current_subagent_permission") or "read-only-audit"
                    ).strip(),
                    "write_execution_requirement": str(
                        slice_run.get("write_execution_requirement") or "requires-write-capable-runner"
                    ).strip(),
                    "blocking_reasons": row_blockers,
                    "execution_state": str(slice_run.get("execution_state") or "not-started").strip(),
                    "evidence_ref": str(slice_run.get("evidence_ref") or "").strip(),
                }
            )

    gate = "not-applicable"
    claim_ceiling = NOT_APPLICABLE_CLAIM_CEILING
    if totals["packet_count"]:
        gate = "blocked" if totals["blocked_slice_count"] or totals["conflict_count"] or blockers else "ready-for-slice-execution"
        claim_ceiling = BLOCKED_ORCHESTRATION_CLAIM_CEILING if gate == "blocked" else READY_ORCHESTRATION_CLAIM_CEILING
    summary = {
        **totals,
        "overall_orchestration_gate": gate,
    }
    return {
        "artifact_kind": "phase3-subagent-slice-orchestration-report",
        "output_dir": str(output_dir),
        "overall_orchestration_gate": gate,
        "claim_ceiling": claim_ceiling,
        "summary": summary,
        "blockers": sorted(blockers),
        "packet_rows": packet_rows,
        "slice_rows": slice_rows,
        "manifest_paths": [str(path) for path in manifest_paths],
    }


def build_slice_orchestration_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    lines = [
        "# SubAgent Slice Orchestration Report",
        "",
        "## Summary",
        f"- overall_orchestration_gate: {report.get('overall_orchestration_gate', 'unknown')}",
        f"- packet_count: {summary.get('packet_count', 0)}",
        f"- slice_count: {summary.get('slice_count', 0)}",
        f"- ready_slice_count: {summary.get('ready_slice_count', 0)}",
        f"- blocked_slice_count: {summary.get('blocked_slice_count', 0)}",
        f"- actual_subagent_execution_count: {summary.get('actual_subagent_execution_count', 0)}",
        f"- write_runner_execution_count: {summary.get('write_runner_execution_count', 0)}",
        f"- read_only_review_count: {summary.get('read_only_review_count', 0)}",
        f"- action_card_runner_supported_count: {summary.get('action_card_runner_supported_count', 0)}",
        f"- runner_protocol_versions: {', '.join(summary.get('runner_protocol_versions', []) or []) or 'none'}",
        f"- runner_kinds: {', '.join(summary.get('runner_kinds', []) or []) or 'none'}",
        f"- configured_authoring_max_workers: {summary.get('configured_authoring_max_workers', 0)}",
        f"- active_authoring_max_workers: {summary.get('active_authoring_max_workers', 0)}",
        f"- configured_verification_max_workers: {summary.get('configured_verification_max_workers', 0)}",
        f"- conflict_count: {summary.get('conflict_count', 0)}",
        f"- claim_ceiling: {report.get('claim_ceiling', '')}",
        "",
        "## Blockers",
    ]
    for blocker in report.get("blockers", []) or ["none"]:
        lines.append(f"- {blocker}")
    lines.extend(["", "## Packets"])
    for row in report.get("packet_rows", []) or [{"packet_id": "none"}]:
        if row.get("packet_id") == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row.get('packet_id', 'unknown')} [{row.get('overall_slice_run_status', 'unknown')}] "
                f"slices={row.get('slice_count', 0)} blocked={row.get('blocked_slice_count', 0)}"
            )
    return localize_phase3_subagent_slice_orchestration_report("\n".join(lines) + "\n", output_locale)


def write_slice_orchestration_report(output_dir: Path) -> dict[str, str]:
    report = build_slice_orchestration_report(output_dir)
    return write_json_and_markdown_report(
        json_path=output_dir / "subagent-slice-orchestration-report.json",
        report=report,
        markdown=build_slice_orchestration_markdown(report),
        markdown_path=output_dir / "subagent-slice-orchestration-report.md",
    )
