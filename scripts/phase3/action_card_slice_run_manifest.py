from __future__ import annotations

from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_subagent_slice_run_manifest
from phase3.review_support import write_json_and_markdown_report


READY_PACKET_CLAIM_CEILING = (
    "slice run manifest is protocol-ready evidence only; implementation completion still requires actual execution by "
    "a write-capable runner or human/main-thread actor, changed-file evidence, targeted tests, runtime evidence, and "
    "review; TPlan scout SubAgents may audit or score, while code edits require an explicit write-capable runner"
)
RUNNER_EXECUTED_PACKET_CLAIM_CEILING = (
    "Action Card slice runner execution evidence is recorded; claim remains bounded to slice-level implementation "
    "artifacts and does not replace full P3 runtime verification, review, and global claim-ceiling acceptance"
)
BLOCKED_PACKET_CLAIM_CEILING = (
    "blocked slice manifest only; no implementation completion claim while blocked slices exist"
)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _operation_count(row: dict[str, Any]) -> int:
    operation_ids = _as_list(row.get("operation_ids"))
    if operation_ids:
        return len(operation_ids)
    return 1 if str(row.get("operation_id") or "").strip() else 0


def _count_missing_evidence(slice_runs: list[dict[str, Any]]) -> int:
    count = 0
    for row in slice_runs:
        reasons = [str(item) for item in _as_list(row.get("blocking_reasons"))]
        if any(reason.startswith("missing_") or reason.startswith("missing_test_target:") for reason in reasons):
            count += 1
    return count


def _slice_return_contract(slice_packet: dict[str, Any]) -> dict[str, Any]:
    existing = (
        slice_packet.get("subagent_return_contract", {})
        if isinstance(slice_packet.get("subagent_return_contract"), dict)
        else {}
    )
    return {
        **existing,
        "required_fields": [
            "slice_id",
            "mode",
            "commands_run",
            "evidence_summary",
            "blockers",
            "claim_ceiling",
        ],
        "read_only_review_fields": [
            "slice_id",
            "review_score",
            "findings",
            "evidence_checked",
            "blockers",
            "claim_ceiling",
        ],
        "write_runner_return_fields": [
            "slice_id",
            "changed_files",
            "commands_run",
            "evidence_summary",
            "blockers",
            "claim_ceiling",
        ],
    }


def _slice_claim_ceiling(slice_packet: dict[str, Any]) -> str:
    value = str(slice_packet.get("claim_ceiling") or "").strip()
    if "write-capable runner" in value and ("TPlan scout SubAgents" in value or "read-only SubAgents" in value):
        return value
    return (
        "slice packet protocol only; implementation quality still requires a write-capable runner or "
        "human/main-thread execution, changed-file evidence, targeted tests, runtime evidence, and review; "
        "TPlan scout SubAgents may audit or score the packet, while code edits require an explicit write-capable runner"
    )


def empty_slice_run_summary() -> dict[str, Any]:
    return {
        "slice_count": 0,
        "ready_slice_count": 0,
        "blocked_slice_count": 0,
        "actual_subagent_execution_count": 0,
        "write_runner_execution_count": 0,
        "read_only_review_count": 0,
        "slice_execution_mode": "not-applicable",
        "slice_runner_supported": False,
        "action_card_runner_supported": False,
        "batch_runner_supported": False,
        "batch_runner_execution_count": 0,
        "runner_protocol_version": "action-card-runner/v1",
        "runner_kind": "generic",
        "configured_authoring_max_workers": 0,
        "active_authoring_max_workers": 0,
        "configured_verification_max_workers": 0,
        "conflict_count": 0,
        "missing_evidence_count": 0,
        "overall_slice_run_status": "not-applicable",
        "packet_claim_ceiling": "not applicable; no backend SubAgent slice run manifest for this packet",
    }


def build_slice_run_manifest(
    *,
    packet_document: dict[str, Any],
    packet_id: str,
    run_dir: Path,
    mode: str,
) -> dict[str, Any]:
    slice_packets = [
        row for row in _as_list(packet_document.get("subagent_slice_packets")) if isinstance(row, dict)
    ]
    conflict_summary = (
        packet_document.get("subagent_slice_conflict_summary", {})
        if isinstance(packet_document.get("subagent_slice_conflict_summary"), dict)
        else {}
    )
    slice_runs: list[dict[str, Any]] = []
    for slice_packet in slice_packets:
        slice_runs.append(
            {
                "slice_id": str(slice_packet.get("slice_id") or "").strip(),
                "slice_kind": str(slice_packet.get("slice_kind") or "").strip(),
                "slice_status": str(slice_packet.get("slice_status") or "blocked").strip() or "blocked",
                "operation_id": str(slice_packet.get("operation_id") or "").strip(),
                "operation_ids": _as_list(slice_packet.get("operation_ids")),
                "http_surface": str(slice_packet.get("http_surface") or "").strip(),
                "http_surfaces": _as_list(slice_packet.get("http_surfaces")),
                "action_card_refs": _as_list(slice_packet.get("action_card_refs")),
                "source_refs": _as_list(slice_packet.get("source_refs")),
                "current_subagent_permission": str(
                    slice_packet.get("current_subagent_permission") or "read-only-audit"
                ).strip(),
                "write_execution_requirement": str(
                    slice_packet.get("write_execution_requirement") or "requires-write-capable-runner"
                ).strip(),
                "allowed_edit_files": _as_list(slice_packet.get("allowed_edit_files")),
                "owned_files": _as_list(slice_packet.get("owned_files")),
                "forbidden_edit_patterns": _as_list(slice_packet.get("forbidden_edit_patterns")),
                "green_commands": slice_packet.get("green_commands", {})
                if isinstance(slice_packet.get("green_commands"), dict)
                else {},
                "red_signal_rule": str(slice_packet.get("red_signal_rule") or "").strip(),
                "done_criteria": _as_list(slice_packet.get("done_criteria")),
                "subagent_return_contract": _slice_return_contract(slice_packet),
                "claim_ceiling": _slice_claim_ceiling(slice_packet),
                "blocking_reasons": _as_list(slice_packet.get("blocking_reasons")),
                "execution_state": "not-started",
                "evidence_ref": "",
            }
        )
    ready_count = sum(1 for row in slice_runs if row.get("slice_status") == "ready")
    blocked_count = sum(1 for row in slice_runs if row.get("slice_status") == "blocked")
    actual_execution_count = sum(
        1
        for row in slice_runs
        if str(row.get("execution_state") or "not-started").strip() not in {"", "not-started"}
    )
    write_runner_execution_count = sum(
        1 for row in slice_runs if str(row.get("execution_state") or "").strip() == "write-runner-executed"
    )
    read_only_review_count = sum(
        1 for row in slice_runs if str(row.get("execution_state") or "").strip() == "read-only-reviewed"
    )
    overall_status = "not-applicable"
    packet_claim_ceiling = empty_slice_run_summary()["packet_claim_ceiling"]
    if slice_runs:
        overall_status = "blocked" if blocked_count else "ready"
        packet_claim_ceiling = BLOCKED_PACKET_CLAIM_CEILING if blocked_count else READY_PACKET_CLAIM_CEILING
    summary = {
        "slice_count": len(slice_runs),
        "ready_slice_count": ready_count,
        "blocked_slice_count": blocked_count,
        "actual_subagent_execution_count": actual_execution_count,
        "write_runner_execution_count": write_runner_execution_count,
        "read_only_review_count": read_only_review_count,
        "slice_execution_mode": mode,
        "slice_runner_supported": False,
        "action_card_runner_supported": False,
        "runner_protocol_version": "action-card-runner/v1",
        "runner_kind": "generic",
        "configured_authoring_max_workers": 0,
        "active_authoring_max_workers": 0,
        "configured_verification_max_workers": 0,
        "conflict_count": int(conflict_summary.get("conflict_count", 0) or 0),
        "missing_evidence_count": _count_missing_evidence(slice_runs),
        "overall_slice_run_status": overall_status,
        "packet_claim_ceiling": packet_claim_ceiling,
    }
    return {
        "packet_id": packet_id,
        "mode": mode,
        "run_dir": str(run_dir),
        "overall_slice_run_status": overall_status,
        "packet_claim_ceiling": packet_claim_ceiling,
        "summary": summary,
        "slice_conflict_summary": conflict_summary,
        "slice_runs": slice_runs,
    }


def build_slice_run_manifest_markdown(manifest: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        f"# SubAgent Slice Run Manifest: {manifest.get('packet_id', 'unknown')}",
        "",
        "## Summary",
        f"- overall_slice_run_status: {manifest.get('overall_slice_run_status', 'unknown')}",
        f"- slice_count: {manifest.get('summary', {}).get('slice_count', 0)}",
        f"- ready_slice_count: {manifest.get('summary', {}).get('ready_slice_count', 0)}",
        f"- blocked_slice_count: {manifest.get('summary', {}).get('blocked_slice_count', 0)}",
        f"- actual_subagent_execution_count: {manifest.get('summary', {}).get('actual_subagent_execution_count', 0)}",
        f"- write_runner_execution_count: {manifest.get('summary', {}).get('write_runner_execution_count', 0)}",
        f"- read_only_review_count: {manifest.get('summary', {}).get('read_only_review_count', 0)}",
        f"- slice_execution_mode: {manifest.get('summary', {}).get('slice_execution_mode', manifest.get('mode', 'unknown'))}",
        f"- slice_runner_supported: {manifest.get('summary', {}).get('slice_runner_supported', False)}",
        f"- action_card_runner_supported: {manifest.get('summary', {}).get('action_card_runner_supported', False)}",
        f"- runner_protocol_version: {manifest.get('summary', {}).get('runner_protocol_version', 'action-card-runner/v1')}",
        f"- runner_kind: {manifest.get('summary', {}).get('runner_kind', 'generic')}",
        f"- configured_authoring_max_workers: {manifest.get('summary', {}).get('configured_authoring_max_workers', 0)}",
        f"- active_authoring_max_workers: {manifest.get('summary', {}).get('active_authoring_max_workers', 0)}",
        f"- configured_verification_max_workers: {manifest.get('summary', {}).get('configured_verification_max_workers', 0)}",
        f"- packet_claim_ceiling: {manifest.get('packet_claim_ceiling', '')}",
        "- current_subagent_permission: read-only-audit",
        "- write_execution_requirement: requires-write-capable-runner",
    ]
    bootstrap = manifest.get("action_card_runner_bootstrap", {})
    if isinstance(bootstrap, dict) and bootstrap.get("path"):
        lines.extend(
            [
                f"- action_card_runner_bootstrap: {bootstrap.get('path')}",
                f"- action_card_runner_bootstrap_claim_ceiling: {bootstrap.get('claim_ceiling', '')}",
            ]
        )
    lines.extend(["", "## Slice Runs"])
    for row in manifest.get("slice_runs", []) or [{"slice_id": "none", "slice_status": ""}]:
        if row.get("slice_id") == "none":
            lines.append("- none")
            continue
        lines.append(
            f"- {row.get('slice_id', 'unknown')} [{row.get('slice_status', 'unknown')}] "
            f"operation={row.get('operation_id', 'n/a')} "
            f"operations={_operation_count(row)} evidence={row.get('evidence_ref', '') or 'none'}"
        )
        blocking = ", ".join(str(item) for item in _as_list(row.get("blocking_reasons")) if str(item).strip())
        if blocking:
            lines.append(f"  - blocking: {blocking}")
    return localize_phase3_subagent_slice_run_manifest("\n".join(lines) + "\n", output_locale)


def write_slice_run_manifest(*, json_path: Path, manifest: dict[str, Any]) -> dict[str, str]:
    return write_json_and_markdown_report(
        json_path=json_path,
        report=manifest,
        markdown=build_slice_run_manifest_markdown(manifest),
    )
