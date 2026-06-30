#!/usr/bin/env python3
"""
Render deterministic Phase-3 worker packet artifacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.output_language import (
    localize_phase3_packet_run_report,
    localize_phase3_worker_input_packet,
    localize_phase3_worker_packet_runbook,
)


def packet_slug(packet_id: str) -> str:
    return packet_id.replace(":", "-")


def next_run_directory(output_dir: Path, packet: str) -> Path:
    packet_root = output_dir / "worker-runs" / packet_slug(packet)
    existing = [
        path
        for path in packet_root.iterdir()
        if path.is_dir() and path.name.startswith("run-")
    ] if packet_root.exists() else []
    next_index = len(existing) + 1
    return packet_root / f"run-{next_index:03d}"


def operation_count(row: dict[str, Any]) -> int:
    operation_ids = row.get("operation_ids", [])
    if isinstance(operation_ids, list) and operation_ids:
        return len(operation_ids)
    return 1 if str(row.get("operation_id") or "").strip() else 0


def build_done_criteria(packet_document: dict[str, Any]) -> list[str]:
    criteria: list[str] = []
    for row in packet_document.get("work_packages", []):
        if not isinstance(row, dict):
            continue
        acceptance = str(row.get("acceptance_criteria", "")).strip()
        wp_id = str(row.get("wp_id", "")).strip()
        if acceptance:
            prefix = f"{wp_id}: " if wp_id else ""
            criteria.append(f"{prefix}{acceptance}")
    verification = packet_document.get("verification_commands", {})
    if isinstance(verification, dict):
        sequence = verification.get("sequence", [])
        if isinstance(sequence, list) and sequence:
            criteria.append(
                f"Verification sequence completes: {', '.join(str(item) for item in sequence if str(item).strip())}"
            )
    if packet_document.get("test_targets"):
        criteria.append("Assigned contract/scenario/replay tests remain green for this packet scope.")
        criteria.append("Assigned unit tests are green for the packet-owned implementation targets.")
    criteria.append("Frozen contracts, migrations, and trace IDs remain compatible with Phase-2 truth.")
    return criteria


def build_verification_script(packet_document: dict[str, Any]) -> str:
    verification = packet_document.get("verification_commands", {})
    if not isinstance(verification, dict):
        return "#!/usr/bin/env bash\nset -euo pipefail\n# verification commands unavailable\n"
    commands = verification.get("commands", {})
    sequence = verification.get("sequence", [])
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"# packet_id: {packet_document.get('packet_id', 'unknown')}",
        f"# workspace_scope: {verification.get('workspace_scope', 'workspace-root')}",
        "",
    ]
    if isinstance(sequence, list):
        for step in sequence:
            normalized_step = str(step).strip()
            if not normalized_step:
                continue
            command = ""
            if isinstance(commands, dict):
                command = str(commands.get(normalized_step, "")).strip()
            if command:
                lines.append(command)
    return "\n".join(lines) + "\n"


def worker_input_packet_markdown(packet: dict[str, Any], output_locale: str | None = None) -> str:
    verification_commands = packet["verification_commands"]
    commands = verification_commands["commands"]
    reporting = verification_commands.get("reporting", {})
    lines = [
        f"# Wave {packet['wave']:02d} {packet['lane'].title()} Worker Input Packet",
        "",
        "## Summary",
        f"- packet_id: {packet['packet_id']}",
        f"- worker_packet_status: {packet['worker_packet_status']}",
        f"- dispatch_state: {packet['dispatch_state']}",
        f"- skill_entrypoint_hint: {packet['skill_entrypoint_hint']}",
        f"- work_packages: {', '.join(packet['work_package_ids']) or 'none'}",
        f"- upstream_wave_ids: {', '.join(str(item) for item in packet['upstream_wave_ids']) or 'none'}",
        f"- upstream_wp_dependencies: {', '.join(packet['upstream_wp_dependencies']) or 'none'}",
        "",
        "## Tests",
        f"- primary_categories: {', '.join(packet['primary_test_categories']) or 'none'}",
        f"- sql: {', '.join(packet['test_targets'].get('sql', [])) or 'none'}",
        f"- contract: {', '.join(packet['test_targets'].get('contract', [])) or 'none'}",
        f"- scenario: {', '.join(packet['test_targets'].get('scenario', [])) or 'none'}",
        f"- replay: {', '.join(packet['test_targets'].get('replay', [])) or 'none'}",
        f"- unit: {', '.join(packet['test_targets'].get('unit', [])) or 'none'}",
        f"- missing sql: {', '.join(packet.get('missing_test_targets', {}).get('sql', [])) or 'none'}",
        f"- missing contract: {', '.join(packet.get('missing_test_targets', {}).get('contract', [])) or 'none'}",
        f"- missing scenario: {', '.join(packet.get('missing_test_targets', {}).get('scenario', [])) or 'none'}",
        f"- missing replay: {', '.join(packet.get('missing_test_targets', {}).get('replay', [])) or 'none'}",
        f"- missing unit: {', '.join(packet.get('missing_test_targets', {}).get('unit', [])) or 'none'}",
        "",
        "## Verification Commands",
        f"- workspace_scope: {verification_commands['workspace_scope']}",
        f"- lint: {commands['lint']}",
        f"- typecheck: {commands['typecheck']}",
        f"- critical-targeted-tests: {commands.get('critical-targeted-tests', 'n/a')}",
        f"- targeted-tests: {commands.get('targeted-tests', 'n/a')}",
        f"- full-targeted-tests: {commands.get('full-targeted-tests', 'n/a')}",
        f"- unit-tests: {commands.get('unit-tests', 'n/a')}",
        f"- build: {commands['build']}",
        f"- critical-targeted-tests-report: {reporting.get('critical-targeted-tests', {}).get('report_path', 'n/a')}",
        f"- targeted-tests-report: {reporting.get('targeted-tests', {}).get('report_path', 'n/a')}",
        f"- full-targeted-tests-report: {reporting.get('full-targeted-tests', {}).get('report_path', 'n/a')}",
        f"- unit-tests-report: {reporting.get('unit-tests', {}).get('report_path', 'n/a')}",
        "",
        "## Environment Bootstrap",
        f"- package_manager: {packet.get('environment_bootstrap', {}).get('package_manager', 'pnpm')}",
        f"- bootstrap_command: {packet.get('environment_bootstrap', {}).get('bootstrap_command', 'pnpm install --frozen-lockfile=false')}",
        f"- readiness_rule: {packet.get('environment_bootstrap', {}).get('readiness_rule', 'Bootstrap workspace dependencies before verification.')}",
        "",
        "## Targets",
    ]
    for target in packet.get("implementation_targets", []) or ["none"]:
        lines.append(f"- {target}")
    lines.extend(["", "## Source Rows"])
    for row in packet.get("source_rows", []) or [{"source_id": "none", "source_type": "", "source_subject": ""}]:
        if row["source_id"] == "none":
            lines.append("- none")
        else:
            lines.append(f"- {row['source_id']} [{row['source_type']}]: {row['source_subject']}")
    lines.extend(["", "## Work Package Assignments"])
    for row in packet.get("work_packages", []):
        blocking = ", ".join(row.get("blocking_reasons", [])) or "none"
        lines.append(
            f"- {row['wp_id']} [{row['wp_execution_readiness']}] targets={row['assigned_target_count']} blocking={blocking}"
        )
    lines.extend(["", "## Done Criteria"])
    for criterion in packet.get("done_criteria", []) or ["Keep frozen contracts stable while making packet tests green."]:
        lines.append(f"- {criterion}")
    slice_packets = packet.get("subagent_slice_packets", [])
    if isinstance(slice_packets, list) and slice_packets:
        lines.extend(["", "## SubAgent Slice Packets"])
        for slice_packet in slice_packets:
            if not isinstance(slice_packet, dict):
                continue
            lines.append(
                f"- {slice_packet.get('slice_id', 'unknown')} [{slice_packet.get('slice_status', 'unknown')}] "
                f"operation={slice_packet.get('operation_id', 'n/a')} "
                f"operations={operation_count(slice_packet)} "
                f"files={len(slice_packet.get('owned_files', []))}"
            )
            blocking = ", ".join(str(item) for item in slice_packet.get("blocking_reasons", []) if str(item).strip())
            if blocking:
                lines.append(f"  - blocking: {blocking}")
        conflict_summary = packet.get("subagent_slice_conflict_summary", {})
        if isinstance(conflict_summary, dict) and conflict_summary.get("conflict_count"):
            lines.append(f"- file_conflicts: {', '.join(conflict_summary.get('conflicting_files', []))}")
    lines.extend(["", "## Coordination"])
    for note in packet.get("coordination_notes", []) or ["Coordinate shared traces and do not rewrite frozen contracts."]:
        lines.append(f"- {note}")
    playbook = packet.get("implementation_playbook", {})
    if isinstance(playbook, dict) and playbook:
        lines.extend(["", "## Implementation Playbook"])
        for step in playbook.get("implementation_steps", []) or ["Follow packet-local implementation sequence."]:
            lines.append(f"- {step}")
        if packet.get("prototype_constraints"):
            lines.extend(["", "## Prototype Constraints"])
            for key, value in packet.get("prototype_constraints", {}).items():
                lines.append(f"- {key}: {value}")
        if packet.get("external_executor_brief"):
            lines.extend(["", "## External Executor Brief"])
            for item in packet.get("external_executor_brief", []):
                lines.append(f"- {item}")
        if packet.get("frontend_surface_designs"):
            lines.extend(["", "## Frontend Surface Designs"])
            for design in packet.get("frontend_surface_designs", []):
                if not isinstance(design, dict):
                    continue
                title = str(design.get("page_title") or design.get("title") or design.get("route") or "surface").strip()
                lines.append(
                    f"- {title}: pattern={design.get('page_blueprint_type', 'unknown')} "
                    f"work_region={design.get('primary_work_region', 'n/a')}"
                )
                for transition in design.get("business_state_transitions", [])[:3]:
                    if not isinstance(transition, dict):
                        continue
                    lines.append(
                        f"- transition: {transition.get('domain_object', 'object')} "
                        f"{transition.get('from_state', 'unknown')} -> {transition.get('to_state', 'unknown')} "
                        f"via {transition.get('trigger_action', 'action')}"
                    )
        if packet.get("semantic_disqualifiers"):
            lines.extend(["", "## Semantic Disqualifiers"])
            for item in packet.get("semantic_disqualifiers", []):
                lines.append(f"- {item}")
        contract_map = playbook.get("contract_to_code_map", [])
        if isinstance(contract_map, list) and contract_map:
            lines.extend(["", "## Contract To Code Map"])
            for row in contract_map:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('operation_id', 'unknown')} -> controller={row.get('controller_target', 'n/a')} "
                    f"service={row.get('service_target', 'n/a')} repository={row.get('repository_target', 'n/a')}"
                )
    return localize_phase3_worker_input_packet("\n".join(lines) + "\n", output_locale)


def build_runbook(
    packet_document: dict[str, Any],
    runtime_row: dict[str, Any] | None,
    mode: str,
    output_locale: str | None = None,
) -> str:
    runtime_row = runtime_row or {}
    test_targets = packet_document.get("test_targets", {})
    lines = [
        f"# Worker Packet Runbook: {packet_document.get('packet_id', 'unknown')}",
        "",
        "## Runtime Selection",
        f"- mode: {mode}",
        f"- lane: {packet_document.get('lane', 'unknown')}",
        f"- selected_state: {runtime_row.get('current_state', 'unknown')}",
        f"- dispatch_decision: {runtime_row.get('dispatch_decision', 'unknown')}",
        "",
        "## Owned Targets",
    ]
    for target in packet_document.get("implementation_targets", []) or ["none"]:
        lines.append(f"- {target}")
    lines.extend(["", "## Trace Subjects"])
    for row in packet_document.get("source_rows", []) or [{"source_id": "none", "source_type": "", "source_subject": ""}]:
        if row.get("source_id") == "none":
            lines.append("- none")
        else:
            lines.append(
                f"- {row.get('source_id', '')} [{row.get('source_type', '')}]: {row.get('source_subject', '')}"
            )
    lines.extend(
        [
            "",
            "## Tests",
            f"- contract: {', '.join(test_targets.get('contract', [])) or 'none'}",
            f"- scenario: {', '.join(test_targets.get('scenario', [])) or 'none'}",
            f"- replay: {', '.join(test_targets.get('replay', [])) or 'none'}",
            f"- unit: {', '.join(test_targets.get('unit', [])) or 'none'}",
            "",
            "## Done Criteria",
        ]
    )
    for item in build_done_criteria(packet_document):
        lines.append(f"- {item}")
    verification = packet_document.get("verification_commands", {})
    commands = verification.get("commands", {}) if isinstance(verification, dict) else {}
    lines.extend(
        [
            "",
            "## Environment Bootstrap",
            f"- package_manager: {packet_document.get('environment_bootstrap', {}).get('package_manager', 'pnpm')}",
            f"- bootstrap_command: {packet_document.get('environment_bootstrap', {}).get('bootstrap_command', 'pnpm install --frozen-lockfile=false')}",
            f"- readiness_rule: {packet_document.get('environment_bootstrap', {}).get('readiness_rule', 'Bootstrap workspace dependencies before verification.')}",
            "",
            "## Verification Commands",
            f"- lint: {commands.get('lint', 'n/a')}",
            f"- typecheck: {commands.get('typecheck', 'n/a')}",
            f"- targeted-tests: {commands.get('targeted-tests', 'n/a')}",
            f"- unit-tests: {commands.get('unit-tests', 'n/a')}",
            f"- build: {commands.get('build', 'n/a')}",
            "",
            "## Coordination",
        ]
    )
    for note in packet_document.get("coordination_notes", []) or ["Coordinate on frozen contracts before changing shared files."]:
        lines.append(f"- {note}")
    playbook = packet_document.get("implementation_playbook", {})
    if isinstance(playbook, dict) and playbook:
        lines.extend(["", "## Implementation Playbook"])
        for step in playbook.get("implementation_steps", []) or ["Follow the packet-local implementation sequence."]:
            lines.append(f"- {step}")
        contract_map = playbook.get("contract_to_code_map", [])
        if isinstance(contract_map, list) and contract_map:
            lines.extend(["", "## Contract To Code Map"])
            for row in contract_map:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('operation_id', 'unknown')} -> controller={row.get('controller_target', 'n/a')} "
                    f"service={row.get('service_target', 'n/a')} repository={row.get('repository_target', 'n/a')}"
                )
    return localize_phase3_worker_packet_runbook("\n".join(lines) + "\n", output_locale)


def build_packet_summary_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        f"# Packet Run Report: {report['packet_id']}",
        "",
        "## Summary",
        f"- mode: {report['mode']}",
        f"- actor: {report['actor'] or 'n/a'}",
        f"- dispatchable_when_selected: {'yes' if report['dispatchable_when_selected'] else 'no'}",
        f"- selected_pre_state: {report['pre_runtime_row'].get('current_state', 'unknown')}",
        f"- selected_post_state: {report['post_runtime_row'].get('current_state', 'unknown')}",
        f"- statuses_recorded: {', '.join(report['event_statuses_recorded']) or 'none'}",
        "",
        "## Outputs",
        f"- run_dir: {report['run_dir']}",
        f"- runbook: {report['runbook_path']}",
        f"- verification_script: {report['verification_script_path']}",
    ]
    if report.get("subagent_slice_run_manifest_path"):
        lines.append(f"- subagent_slice_manifest: {report['subagent_slice_run_manifest_path']}")
        lines.append(
            f"- subagent_slice_manifest_markdown: {report.get('subagent_slice_run_manifest_markdown_path', 'n/a')}"
        )
        lines.append(
            "- subagent_permission: TPlan scout SubAgents may audit/score only; "
            "code edits require an explicit write-capable runner"
        )
        if report.get("action_card_runner_bootstrap_path"):
            lines.append(f"- action_card_runner_bootstrap: {report['action_card_runner_bootstrap_path']}")
            bootstrap = report.get("action_card_runner_bootstrap", {})
            if isinstance(bootstrap, dict):
                lines.append(
                    "- action_card_runner_bootstrap_claim_ceiling: "
                    f"{bootstrap.get('claim_ceiling', 'bootstrap guidance only; not execution evidence')}"
                )
        slice_summary = report.get("subagent_slice_run_summary", {})
        if isinstance(slice_summary, dict):
            lines.append(f"- subagent_slice_status: {slice_summary.get('overall_slice_run_status', 'unknown')}")
            lines.append(f"- subagent_slice_count: {slice_summary.get('slice_count', 0)}")
            lines.append(
                "- actual_subagent_execution_count: "
                f"{slice_summary.get('actual_subagent_execution_count', 0)}"
            )
            lines.append(
                "- write_runner_execution_count: "
                f"{slice_summary.get('write_runner_execution_count', 0)}"
            )
            lines.append(
                "- read_only_review_count: "
                f"{slice_summary.get('read_only_review_count', 0)}"
            )
            lines.append(
                "- slice_runner_supported: "
                f"{slice_summary.get('slice_runner_supported', False)}"
            )
            lines.append(
                "- action_card_runner_supported: "
                f"{slice_summary.get('action_card_runner_supported', False)}"
            )
            lines.append(
                "- runner_protocol_version: "
                f"{slice_summary.get('runner_protocol_version', 'action-card-runner/v1')}"
            )
            lines.append(
                "- runner_kind: "
                f"{slice_summary.get('runner_kind', 'generic')}"
            )
            lines.append(
                "- configured_authoring_max_workers: "
                f"{slice_summary.get('configured_authoring_max_workers', 0)}"
            )
            lines.append(
                "- active_authoring_max_workers: "
                f"{slice_summary.get('active_authoring_max_workers', 0)}"
            )
            lines.append(
                "- configured_verification_max_workers: "
                f"{slice_summary.get('configured_verification_max_workers', 0)}"
            )
    if report.get("subagent_slice_orchestration_report_path"):
        lines.append(f"- subagent_slice_orchestration_report: {report['subagent_slice_orchestration_report_path']}")
        lines.append(
            "- subagent_slice_orchestration_report_markdown: "
            f"{report.get('subagent_slice_orchestration_report_markdown_path', 'n/a')}"
        )
        orchestration_summary = report.get("subagent_slice_orchestration_summary", {})
        if isinstance(orchestration_summary, dict):
            lines.append(
                "- subagent_slice_orchestration_gate: "
                f"{orchestration_summary.get('overall_orchestration_gate', 'unknown')}"
            )
    verification_execution = report.get("verification_execution")
    if isinstance(verification_execution, dict):
        lines.extend(
            [
                "",
                "## Verification Execution",
                f"- overall_verdict: {verification_execution.get('overall_verdict', 'unknown')}",
                f"- report_path: {verification_execution.get('report_path', 'n/a')}",
            ]
        )
    gate_cycle_report = report.get("wp_gate_cycle_report")
    if isinstance(gate_cycle_report, dict):
        lines.extend(
            [
                "",
                "## WP Gate Cycle",
                f"- wp_gate_path: {gate_cycle_report.get('wp_gate_path', 'n/a')}",
                f"- dispatchable_packet_count: {gate_cycle_report.get('runtime_summary', {}).get('dispatchable_packet_count', 0)}",
            ]
        )
    if report.get("note"):
        lines.extend(["", "## Note", f"- {report['note']}"])
    return localize_phase3_packet_run_report("\n".join(lines) + "\n", output_locale)
