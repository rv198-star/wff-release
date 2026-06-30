#!/usr/bin/env python3
"""
Build deterministic work-package execution packets and wave plans for Phase-3.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_execution_packet, localize_phase3_wave_plan
from phase3.collection_tools import dedupe_strings_in_order
from phase3.contract_test_scaffolder import build_contract_test_target_lookup
from phase3.contract_tools import (
    extract_nested_bullet_items,
    parse_replay_rows,
    parse_scenario_rows,
    replay_test_filename,
    scenario_identifier,
    scenario_test_filename,
    slugify,
)
from phase3.implementation_binding_tools import (
    build_wp_lookup,
    expand_scope_term_equivalents,
    parse_openapi_operations,
    scope_tokens,
    trace_ids_in_text,
)
from phase3.frontend_route_segments import frontend_route_file_segment, route_slug, sanitize_route_segment
from phase3.review_support import write_json_and_markdown_report, write_json_report
from phase3.worker_playbook import lane_skill_hint


def build_wave_plan_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Work Package Execution Wave Plan",
        "",
        "## Summary",
        f"- overall_status: {report.get('overall_status', 'unknown')}",
        f"- wave_count: {summary.get('wave_count', 0)}",
        f"- ready_work_package_count: {summary.get('ready_work_package_count', 0)}",
        f"- blocked_work_package_count: {summary.get('blocked_work_package_count', 0)}",
        f"- unscheduled_work_package_count: {summary.get('unscheduled_work_package_count', 0)}",
        "",
        "## Waves",
    ]

    for wave in report.get("waves", []):
        lines.extend(
            [
                f"### Wave {wave['wave']}",
                f"- status: {wave['wave_status']}",
                f"- ready_rows: {wave['ready_row_count']}/{wave['row_count']}",
            ]
        )
        for row in wave.get("rows", []):
            reasons = ", ".join(row.get("blocking_reasons", [])) or "none"
            lines.append(
                f"- {row['wp_id']} [{row['execution_readiness']}] lane={row['suggested_owner_lane']} depends_on={', '.join(row['depends_on']) or 'none'} blocking={reasons}"
            )
        lines.append("")

    unscheduled = report.get("unscheduled_rows", [])
    if unscheduled:
        lines.extend(["## Unscheduled"])
        for row in unscheduled:
            reasons = ", ".join(row.get("blocking_reasons", [])) or "none"
            lines.append(f"- {row['wp_id']}: {reasons}")
        lines.append("")

    return localize_phase3_wave_plan("\n".join(lines) + "\n", output_locale)


def build_work_package_wave_plan(
    *,
    esp_text: str,
    packet_index: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    wp_rows = build_wp_lookup(esp_text)
    wp_order = [str(row.get("wp_id", "")).strip() for row in wp_rows if str(row.get("wp_id", "")).strip()]
    wp_row_lookup = {str(row.get("wp_id", "")).strip(): row for row in wp_rows if str(row.get("wp_id", "")).strip()}
    known_wp_ids = set(wp_order)

    packet_lookup: dict[str, dict[str, Any]] = {}
    for row in packet_index.get("rows", []):
        if not isinstance(row, dict):
            continue
        wp_id = str(row.get("wp_id", "")).strip()
        if wp_id:
            packet_lookup[wp_id] = row

    declared_deps: dict[str, list[str]] = {}
    unknown_deps: dict[str, list[str]] = {}
    for wp_id in wp_order:
        row = wp_row_lookup[wp_id]
        deps = [str(item).strip() for item in row.get("depends_on", []) if str(item).strip()]
        declared_deps[wp_id] = [dep for dep in deps if dep in known_wp_ids]
        unknown_deps[wp_id] = [dep for dep in deps if dep not in known_wp_ids]

    remaining = set(wp_order)
    placed: set[str] = set()
    waves: list[list[str]] = []
    while remaining:
        ready = [
            wp_id
            for wp_id in wp_order
            if wp_id in remaining and not unknown_deps[wp_id] and all(dep in placed for dep in declared_deps[wp_id])
        ]
        if not ready:
            break
        waves.append(ready)
        for wp_id in ready:
            placed.add(wp_id)
            remaining.remove(wp_id)

    scheduled_rows: list[dict[str, Any]] = []
    wave_rows: list[dict[str, Any]] = []
    for wave_index, wave_wp_ids in enumerate(waves, start=1):
        rows: list[dict[str, Any]] = []
        for wp_id in wave_wp_ids:
            packet = packet_lookup.get(wp_id, {})
            packet_status = str(packet.get("packet_status", "")).strip() or "missing"
            blocking_reasons: list[str] = []
            if not packet:
                blocking_reasons.append("missing_execution_packet")
            elif packet_status != "ready":
                blocking_reasons.append(f"packet_{packet_status.replace('-', '_')}")
            row = {
                "wp_id": wp_id,
                "wave": wave_index,
                "depends_on": declared_deps[wp_id],
                "suggested_owner_lane": str(packet.get("suggested_owner_lane", "unknown")).strip() or "unknown",
                "packet_status": packet_status,
                "skill_hint": str(packet.get("skill_hint", packet.get("skill_entrypoint_hint", ""))).strip()
                or str(packet.get("skill_entrypoint_hint", "wff-impl")).strip(),
                "packet_json": str(packet.get("packet_json", "")).strip(),
                "packet_markdown": str(packet.get("packet_markdown", "")).strip(),
                "source_count": int(packet.get("source_count", 0) or 0),
                "test_count": int(packet.get("test_count", 0) or 0),
                "implementation_target_count": int(packet.get("implementation_target_count", 0) or 0),
                "execution_readiness": "ready" if not blocking_reasons else "blocked",
                "blocking_reasons": blocking_reasons,
            }
            rows.append(row)
            scheduled_rows.append(row)
        ready_row_count = sum(1 for row in rows if row["execution_readiness"] == "ready")
        wave_rows.append(
            {
                "wave": wave_index,
                "row_count": len(rows),
                "ready_row_count": ready_row_count,
                "wave_status": "ready" if ready_row_count == len(rows) else "partially-blocked",
                "rows": rows,
            }
        )

    unscheduled_rows: list[dict[str, Any]] = []
    for wp_id in wp_order:
        if wp_id not in remaining:
            continue
        blocking_reasons = []
        if unknown_deps[wp_id]:
            blocking_reasons.extend(f"unknown_dependency:{dep}" for dep in unknown_deps[wp_id])
        unresolved = [dep for dep in declared_deps[wp_id] if dep in remaining]
        if unresolved:
            blocking_reasons.extend(f"dependency_cycle_or_unresolved:{dep}" for dep in unresolved)
        if not blocking_reasons:
            blocking_reasons.append("unschedulable")
        packet = packet_lookup.get(wp_id, {})
        unscheduled_rows.append(
            {
                "wp_id": wp_id,
                "depends_on": declared_deps[wp_id] + unknown_deps[wp_id],
                "suggested_owner_lane": str(packet.get("suggested_owner_lane", "unknown")).strip() or "unknown",
                "packet_status": str(packet.get("packet_status", "missing")).strip() or "missing",
                "blocking_reasons": blocking_reasons,
            }
        )

    report = {
        "overall_status": "valid" if not unscheduled_rows else "invalid",
        "summary": {
            "work_package_count": len(wp_order),
            "scheduled_work_package_count": len(scheduled_rows),
            "unscheduled_work_package_count": len(unscheduled_rows),
            "wave_count": len(wave_rows),
            "ready_work_package_count": sum(
                1 for row in scheduled_rows if row["execution_readiness"] == "ready"
            ),
            "blocked_work_package_count": sum(
                1 for row in scheduled_rows if row["execution_readiness"] != "ready"
            )
            + len(unscheduled_rows),
        },
        "waves": wave_rows,
        "unscheduled_rows": unscheduled_rows,
    }

    json_path = output_dir / "work-package-wave-plan.json"
    markdown_path = output_dir / "work-package-wave-plan.md"
    write_json_and_markdown_report(
        json_path=json_path,
        report=report,
        markdown=build_wave_plan_markdown(report),
        markdown_path=markdown_path,
    )
    return {
        "output_path": str(json_path),
        "markdown_path": str(markdown_path),
        **report["summary"],
        "overall_status": report["overall_status"],
    }


def collect_trace_refs(text: str) -> set[str]:
    return trace_ids_in_text(text)


def classify_lane(implementation_targets: list[str]) -> str:
    has_api = any(target.startswith("apps/api/") for target in implementation_targets)
    has_web = any(target.startswith("apps/web/") for target in implementation_targets)
    if has_api and has_web:
        return "fullstack"
    if has_api:
        return "backend"
    if has_web:
        return "frontend"
    if implementation_targets:
        return "platform"
    return "coordination"


def build_contract_test_lookup(openapi_spec: dict[str, object]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    operations = parse_openapi_operations(openapi_spec)
    target_lookup = build_contract_test_target_lookup(list(operations))
    for operation in operations:
        key = f"tests/contracts/{target_lookup[(operation['operation_id'], str(operation['method']).upper(), str(operation['path']))]}"
        lookup[key] = operation
    return lookup


def build_surface_lookup(esp_text: str, *, output_dir: Path | None = None) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if output_dir is not None:
        contract_path = output_dir / "prototype-fallback" / "ui-ia-contract.json"
        if contract_path.exists():
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"expected JSON object at {contract_path}")
            for raw_page in payload.get("pages", []):
                if not isinstance(raw_page, dict):
                    continue
                title = str(raw_page.get("page_title") or raw_page.get("title") or "").strip()
                if not title:
                    continue
                route_segment = sanitize_route_segment(str(raw_page.get("route") or ""), title)
                lookup[f"apps/web/app/{frontend_route_file_segment(route_segment)}/page.tsx"] = title
            if lookup:
                return lookup
    for surface in extract_nested_bullet_items(esp_text, "primary_surfaces"):
        lookup[f"apps/web/app/{frontend_route_file_segment(route_slug(surface))}/page.tsx"] = surface
    return lookup


def infer_targets_from_scope(
    *,
    scope: str,
    acceptance_criteria: str,
    openapi_spec: dict[str, object],
    surface_lookup: dict[str, str],
) -> list[str]:
    inferred: set[str] = set()
    tokens = expand_scope_term_equivalents(scope_tokens(scope) | scope_tokens(acceptance_criteria))

    for target, surface in surface_lookup.items():
        if tokens and len(tokens & scope_tokens(surface)) >= 1:
            inferred.add(target)

    for operation in parse_openapi_operations(openapi_spec):
        haystack = " ".join(
            [
                operation.get("operation_id", ""),
                operation.get("tag", ""),
                operation.get("path", ""),
            ]
        )
        if tokens and len(tokens & scope_tokens(haystack)) >= 1:
            module_slug = slugify(operation["tag"])
            inferred.add(f"apps/api/src/modules/{module_slug}/{module_slug}.controller.ts")
            inferred.add(f"apps/api/src/modules/{module_slug}/{module_slug}.service.ts")
    return sorted(inferred)


def build_scenario_lookup(stage_03_text: str) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for row in parse_scenario_rows(stage_03_text):
        scenario_name = str(row.get("scenario", "")).strip()
        scenario_id, _ = scenario_identifier(scenario_name)
        lookup[scenario_id] = {
            **row,
            "scenario_id": scenario_id,
            "test_target": f"tests/scenarios/{scenario_test_filename(scenario_name)}",
        }
    return lookup


def build_replay_lookup(stage_04_text: str) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for row in parse_replay_rows(stage_04_text):
        replay_id = str(row.get("replay_id", "")).strip().upper()
        lookup[replay_id] = {
            **row,
            "replay_id": replay_id,
            "test_target": f"tests/replays/{replay_test_filename(replay_id, str(row.get('scenario_or_contract', '')))}",
        }
    return lookup


def categorize_tests(test_targets: list[str]) -> dict[str, list[str]]:
    categories = {"sql": [], "contract": [], "scenario": [], "replay": [], "unit": []}
    for target in sorted(set(test_targets)):
        if target.endswith(".sql.test.ts"):
            categories["sql"].append(target)
        elif target.endswith(".contract.test.ts"):
            categories["contract"].append(target)
        elif target.endswith(".scenario.test.ts"):
            categories["scenario"].append(target)
        elif target.endswith(".replay.test.ts"):
            categories["replay"].append(target)
        elif target.endswith(".unit.test.ts"):
            categories["unit"].append(target)
    return categories


def execution_packet_markdown(packet: dict[str, Any], output_locale: str | None = None) -> str:
    source_rows = packet.get("source_rows", [])
    contract_operations = packet.get("contract_operations", [])
    frontend_surfaces = packet.get("frontend_surfaces", [])
    categorized_tests = packet.get("test_targets", {})
    lines = [
        f"# {packet['wp_id']} Execution Packet",
        "",
        "## Core",
        f"- scope: {packet['scope'] or 'n/a'}",
        f"- acceptance_criteria: {packet['acceptance_criteria'] or 'n/a'}",
        f"- estimated_effort: {packet['estimated_effort'] or 'n/a'}",
        f"- owner_lane: {packet['suggested_owner_lane']}",
        f"- skill_hint: {packet['skill_entrypoint_hint']}",
        f"- status: {packet['packet_status']}",
        f"- depends_on: {', '.join(packet['depends_on']) or 'none'}",
        f"- linked_rbi_or_slice: {', '.join(packet['linked_rbi_or_slice']) or 'none'}",
        "",
        "## Trace Inputs",
    ]
    if source_rows:
        for row in source_rows:
            lines.append(
                f"- {row['source_id']} [{row['source_type']}]: {row['source_subject']}"
            )
    else:
        lines.append("- No bound source rows yet. Review WP trace linkage before implementation.")
    lines.extend(["", "## Test Targets"])
    for key in ("sql", "contract", "scenario", "replay", "unit"):
        values = categorized_tests.get(key, [])
        lines.append(f"- {key}: {', '.join(values) or 'none'}")
    lines.extend(["", "## Contract Surface"])
    if contract_operations:
        for operation in contract_operations:
            lines.append(
                f"- {operation['operation_id']}: {operation['method'].upper()} {operation['path']} [{operation['tag']}]"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Implementation Targets"])
    for target in packet["implementation_targets"] or ["none"]:
        lines.append(f"- {target}")
    lines.extend(["", "## Frontend Surfaces"])
    for surface in frontend_surfaces or ["none"]:
        lines.append(f"- {surface}")
    lines.extend(
        [
            "",
            "## Execution Rules",
            "- Keep OpenAPI, migration, and trace IDs frozen unless a contract change is explicitly approved.",
            "- Make the listed tests green before expanding scope.",
            "- Preserve evidence linkage from source trace -> test -> implementation target.",
        ]
    )
    return localize_phase3_execution_packet("\n".join(lines) + "\n", output_locale)


def build_work_package_packets(
    *,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    openapi_spec: dict[str, object],
    implementation_bindings: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    wp_rows = build_wp_lookup(esp_text)
    binding_rows = implementation_bindings.get("rows", [])
    if not isinstance(binding_rows, list):
        raise ValueError("implementation_bindings must contain rows")

    contract_lookup = build_contract_test_lookup(openapi_spec)
    surface_lookup = build_surface_lookup(esp_text, output_dir=output_dir)
    scenario_lookup = build_scenario_lookup(stage_03_text)
    replay_lookup = build_replay_lookup(stage_04_text)

    bindings_by_wp: dict[str, list[dict[str, Any]]] = {}
    for row in binding_rows:
        if not isinstance(row, dict):
            continue
        for wp_id in [str(item).strip() for item in row.get("work_packages", []) if str(item).strip()]:
            bindings_by_wp.setdefault(wp_id, []).append(row)

    packets_root = output_dir / "work-package-packets"
    packet_index_rows: list[dict[str, Any]] = []
    underlinked: list[str] = []
    lane_counter: Counter[str] = Counter()

    for wp_row in wp_rows:
        wp_id = str(wp_row.get("wp_id", "")).strip()
        scope = str(wp_row.get("scope", wp_row.get("implementation_scope", ""))).strip()
        acceptance_criteria = str(wp_row.get("acceptance_criteria", "")).strip()
        wp_bindings = bindings_by_wp.get(wp_id, [])

        source_rows = [
            {
                "source_id": str(row.get("source_id", "")).strip(),
                "source_type": str(row.get("source_type", "")).strip(),
                "source_subject": str(row.get("source_subject", "")).strip(),
            }
            for row in wp_bindings
        ]

        implementation_targets = sorted(
            {
                str(target).strip()
                for row in wp_bindings
                for target in row.get("implementation_targets", [])
                if str(target).strip()
            }
        )
        test_targets = sorted(
            {
                str(target).strip()
                for row in wp_bindings
                for target in row.get("test_targets", [])
                if str(target).strip()
            }
        )

        for ref in collect_trace_refs(acceptance_criteria):
            if ref.startswith("SCN-") and ref in scenario_lookup:
                test_targets.append(str(scenario_lookup[ref]["test_target"]))
            if ref.startswith("RP-") and ref in replay_lookup:
                test_targets.append(str(replay_lookup[ref]["test_target"]))
        test_targets = sorted(set(test_targets))

        if not implementation_targets:
            implementation_targets = infer_targets_from_scope(
                scope=scope,
                acceptance_criteria=acceptance_criteria,
                openapi_spec=openapi_spec,
                surface_lookup=surface_lookup,
            )

        contract_operations = [
            contract_lookup[target]
            for target in test_targets
            if target in contract_lookup
        ]
        frontend_surfaces = dedupe_strings_in_order(
            [
                surface_lookup[target]
                for target in implementation_targets
                if target in surface_lookup
            ]
        )

        lane = classify_lane(implementation_targets)
        lane_counter.update([lane])
        packet_status = "ready" if source_rows and test_targets else "under-linked"
        if packet_status != "ready":
            underlinked.append(wp_id)

        packet = {
            "wp_id": wp_id,
            "scope": scope,
            "acceptance_criteria": acceptance_criteria,
            "estimated_effort": str(wp_row.get("estimated_effort", "")).strip(),
            "effort_basis": str(wp_row.get("effort_basis", "")).strip(),
            "fte_breakdown": str(wp_row.get("fte_breakdown", "")).strip(),
            "team_assumption": str(wp_row.get("team_assumption", "")).strip(),
            "rollback_or_fallback": str(wp_row.get("rollback_or_fallback", "")).strip(),
            "depends_on": [str(item).strip() for item in wp_row.get("depends_on", []) if str(item).strip()],
            "linked_rbi_or_slice": [str(item).strip() for item in wp_row.get("linked_rbi_or_slice", []) if str(item).strip()],
            "suggested_owner_lane": lane,
            "skill_entrypoint_hint": lane_skill_hint(lane),
            "packet_status": packet_status,
            "source_rows": source_rows,
            "test_targets": categorize_tests(test_targets),
            "contract_operations": contract_operations,
            "implementation_targets": implementation_targets,
            "frontend_surfaces": frontend_surfaces,
        }

        packet_dir = packets_root / wp_id.lower()
        json_path = packet_dir / "execution-packet.json"
        markdown_path = packet_dir / "execution-packet.md"
        write_json_and_markdown_report(
            json_path=json_path,
            report=packet,
            markdown=execution_packet_markdown(packet),
            markdown_path=markdown_path,
        )

        packet_index_rows.append(
            {
                "wp_id": wp_id,
                "packet_status": packet_status,
                "suggested_owner_lane": lane,
                "packet_json": str(json_path.relative_to(output_dir)),
                "packet_markdown": str(markdown_path.relative_to(output_dir)),
                "source_count": len(source_rows),
                "test_count": sum(len(values) for values in packet["test_targets"].values()),
                "implementation_target_count": len(implementation_targets),
            }
        )

    index = {
        "summary": {
            "work_package_count": len(wp_rows),
            "packet_count": len(packet_index_rows),
            "underlinked_work_packages": underlinked,
            "lane_counts": dict(sorted(lane_counter.items())),
        },
        "rows": packet_index_rows,
    }
    write_json_report(packets_root / "index.json", index)
    return index
