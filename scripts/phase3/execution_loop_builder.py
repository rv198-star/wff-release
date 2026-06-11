#!/usr/bin/env python3
"""
Build wave-based worker input packets and an execution loop plan for Phase-3.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import os
import re
import shlex
from collections import Counter
from pathlib import Path
from typing import Any

from phase3.contract_test_scaffolder import build_contract_test_target_lookup, contract_test_filename
from common.output_language import localize_phase3_execution_loop_plan, localize_phase3_execution_packet, localize_phase3_wave_plan, localize_phase3_worker_input_packet
from phase3.contract_tools import extract_nested_bullet_items, parse_replay_rows, parse_scenario_rows, replay_test_filename, scenario_identifier, scenario_test_filename, slugify
from phase3.phase3_implementation_scaffolder import route_slug, sanitize_route_segment
from phase3.implementation_binding_tools import (
    build_wp_lookup,
    expand_scope_term_equivalents,
    parse_openapi_operations,
    scope_tokens,
    trace_ids_in_text,
)


BACKEND_TARGETED_VITEST_BATCH_SIZE = 16
TARGETED_TEST_CATEGORIES_BY_LANE = {
    "backend": ("sql", "contract", "scenario", "replay"),
    "frontend": ("contract", "scenario", "replay"),
}
MUTATING_CONTRACT_TOKENS = (
    "create",
    "post",
    "submit",
    "update",
    "put",
    "patch",
    "delete",
    "remove",
    "approve",
    "reject",
    "transition",
)


def backend_targeted_vitest_batch_size() -> int:
    raw_value = str(os.environ.get("PHASE3_TARGETED_VITEST_BATCH_SIZE", "")).strip()
    if not raw_value:
        return BACKEND_TARGETED_VITEST_BATCH_SIZE
    try:
        parsed = int(raw_value)
    except ValueError:
        return BACKEND_TARGETED_VITEST_BATCH_SIZE
    return parsed if parsed > 0 else BACKEND_TARGETED_VITEST_BATCH_SIZE
READ_CONTRACT_TOKENS = (
    "list",
    "get",
    "read",
    "find",
    "search",
    "query",
    "retrieve",
    "fetch",
    "overview",
)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
    write_text(json_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(markdown_path, build_wave_plan_markdown(report))
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
            payload = load_json(contract_path)
            for raw_page in payload.get("pages", []):
                if not isinstance(raw_page, dict):
                    continue
                title = str(raw_page.get("page_title") or raw_page.get("title") or "").strip()
                if not title:
                    continue
                route_segment = sanitize_route_segment(str(raw_page.get("route") or ""), title)
                lookup[f"apps/web/app/{route_segment}/page.tsx"] = title
            if lookup:
                return lookup
    for surface in extract_nested_bullet_items(esp_text, "primary_surfaces"):
        lookup[f"apps/web/app/{route_slug(surface)}/page.tsx"] = surface
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
        write_text(json_path, json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        write_text(markdown_path, execution_packet_markdown(packet))

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
    write_text(packets_root / "index.json", json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return index


def normalize_surface_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value).strip().casefold(), flags=re.UNICODE)


def route_from_target(target: str) -> str:
    match = re.match(r"^apps/web/app/(.+)/page\.tsx$", str(target).strip())
    if not match:
        return ""
    return "/" + match.group(1).strip("/")


def load_frontend_contract(output_dir: Path) -> dict[str, Any] | None:
    return load_json_if_exists(output_dir / "prototype-fallback" / "ui-ia-contract.json")


def select_frontend_surface_designs(
    *,
    output_dir: Path,
    frontend_surfaces: list[str],
    implementation_targets: list[str],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str], list[str]]:
    contract = load_frontend_contract(output_dir)
    if not contract:
        return [], {}, [], []
    pages = contract.get("pages", [])
    if not isinstance(pages, list):
        pages = []
    by_title: dict[str, dict[str, Any]] = {}
    by_route: dict[str, dict[str, Any]] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        title = str(page.get("page_title") or page.get("title") or "").strip()
        route = str(page.get("route") or "").strip()
        if title:
            by_title[normalize_surface_key(title)] = page
        if route:
            by_route[normalize_surface_key(route)] = page

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for surface in frontend_surfaces:
        page = by_title.get(normalize_surface_key(surface))
        if not page:
            continue
        key = str(page.get("page_id") or page.get("route") or page.get("page_title") or "").strip()
        if key and key not in seen:
            seen.add(key)
            selected.append(page)
    for target in implementation_targets:
        route = route_from_target(target)
        if not route:
            continue
        page = by_route.get(normalize_surface_key(route))
        if not page:
            continue
        key = str(page.get("page_id") or page.get("route") or page.get("page_title") or "").strip()
        if key and key not in seen:
            seen.add(key)
            selected.append(page)

    constraints = contract.get("prototype_generation_constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    external_brief = contract.get("external_executor_brief", [])
    if not isinstance(external_brief, list):
        external_brief = []
    semantic_disqualifiers = contract.get("semantic_disqualifiers", [])
    if not isinstance(semantic_disqualifiers, list):
        semantic_disqualifiers = []
    normalized_constraints = {
        str(key).strip(): str(value).strip()
        for key, value in constraints.items()
        if str(key).strip() and str(value).strip()
    }
    return (
        selected,
        normalized_constraints,
        [str(item).strip() for item in external_brief if str(item).strip()],
        [str(item).strip() for item in semantic_disqualifiers if str(item).strip()],
    )


def lane_skill_hint(lane: str) -> str:
    if lane == "backend":
        return "wff-impl-implement-backend-api"
    if lane == "frontend":
        return "wff-impl-implement-frontend-web"
    return "wff-impl"


def primary_test_categories(lane: str) -> list[str]:
    if lane == "backend":
        return ["sql", "contract", "scenario", "replay", "unit"]
    if lane == "frontend":
        return ["scenario", "replay", "unit"]
    return ["contract", "scenario", "replay", "unit"]


def workspace_scope(lane: str) -> str:
    if lane == "backend":
        return "@app/api"
    if lane == "frontend":
        return "@app/web"
    return "workspace-root"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "module"


def quoted_targets(targets: list[str]) -> str:
    return " ".join(shlex.quote(str(target)) for target in targets if str(target).strip())


def build_backend_playbook(
    *,
    contract_operations: list[dict[str, Any]],
    implementation_targets: list[str],
    test_targets: dict[str, list[str]],
) -> dict[str, Any]:
    controller_targets = [target for target in implementation_targets if target.endswith(".controller.ts")]
    service_targets = [target for target in implementation_targets if target.endswith(".service.ts")]
    mappings: list[dict[str, str]] = []
    for operation in contract_operations:
        operation_id = str(operation.get("operation_id", "")).strip()
        method = str(operation.get("method", "")).strip().upper()
        path = str(operation.get("path", "")).strip()
        module_slug = slugify(str(operation.get("tag", "")).strip() or operation_id or path)
        controller_target = next(
            (target for target in controller_targets if f"/{module_slug}/" in target or target.endswith(f"/{module_slug}.controller.ts")),
            controller_targets[0] if len(controller_targets) == 1 else "",
        )
        service_target = next(
            (target for target in service_targets if f"/{module_slug}/" in target or target.endswith(f"/{module_slug}.service.ts")),
            service_targets[0] if len(service_targets) == 1 else "",
        )
        repository_target = f"apps/api/src/modules/{module_slug}/{module_slug}.repository.ts"
        mappings.append(
            {
                "operation_id": operation_id,
                "http_surface": f"{method} {path}".strip(),
                "controller_target": controller_target,
                "service_target": service_target,
                "repository_target": repository_target,
            }
        )

    return {
        "contract_to_code_map": mappings,
        "implementation_steps": [
            "Freeze the contract first: do not edit OpenAPI, shared types, or migrations from inside the worker packet.",
            "For each assigned operation, implement controller input/output mapping first, then the service method, then any repository or adapter boundary the service needs.",
            "After each operation or thin vertical slice, run the targeted contract tests before broadening into scenario or replay coverage.",
            "Only move to scenario/replay fixes after the relevant contract tests for the slice are green.",
        ],
        "test_sequence": [
            *([f"sql: {item}" for item in test_targets.get("sql", [])]),
            *([f"contract: {item}" for item in test_targets.get("contract", [])]),
            *([f"scenario: {item}" for item in test_targets.get("scenario", [])]),
            *([f"replay: {item}" for item in test_targets.get("replay", [])]),
            *([f"unit: {item}" for item in test_targets.get("unit", [])]),
        ],
    }


def build_frontend_playbook(
    *,
    frontend_surfaces: list[str],
    frontend_surface_designs: list[dict[str, Any]],
    prototype_constraints: dict[str, str],
    external_executor_brief: list[str],
    semantic_disqualifiers: list[str],
    test_targets: dict[str, list[str]],
) -> dict[str, Any]:
    return {
        "surface_sequence": frontend_surfaces,
        "surface_implementation_designs": frontend_surface_designs,
        "prototype_constraints": prototype_constraints,
        "external_executor_brief": external_executor_brief,
        "semantic_disqualifiers": semantic_disqualifiers,
        "implementation_steps": [
            "Translate each assigned prototype surface into a page-specific implementation design before coding.",
            "Choose the interaction pattern, visible business-state transitions, validation rules, and information hierarchy that match the page's business function.",
            "Do not build or reuse a generic renderer that maps JSON section metadata into UI templates across distinct page types.",
            "Start from the frozen API client and shared types only after the page-specific implementation design is clear; do not hand-roll public HTTP calls.",
            "Implement loading, success, empty, denied, and error states explicitly before visual polish.",
            "Reflect business-state transitions as UI changes after actions complete; do not stop at transport-level success or raw response rendering.",
            "Keep each scenario surface aligned to the assigned replay/scenario tests and only widen scope after the targeted scenario tests are green.",
        ],
        "test_sequence": [
            *([f"scenario: {item}" for item in test_targets.get("scenario", [])]),
            *([f"replay: {item}" for item in test_targets.get("replay", [])]),
            *([f"unit: {item}" for item in test_targets.get("unit", [])]),
        ],
    }


def build_platform_playbook(test_targets: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "implementation_steps": [
            "Use the platform lane for cross-cutting concerns only: CI, shared infra, or shared tooling.",
            "Do not absorb backend/frontend business logic into platform targets.",
        ],
        "test_sequence": [
            *([f"contract: {item}" for item in test_targets.get("contract", [])]),
            *([f"scenario: {item}" for item in test_targets.get("scenario", [])]),
            *([f"replay: {item}" for item in test_targets.get("replay", [])]),
            *([f"unit: {item}" for item in test_targets.get("unit", [])]),
        ],
    }


def environment_bootstrap(workspace_root_hint: str = ".") -> dict[str, str]:
    return {
        "package_manager": "pnpm",
        "bootstrap_command": f"pnpm install --dir {workspace_root_hint} --frozen-lockfile=false",
        "readiness_rule": "Run this before packet verification when node_modules is missing.",
    }


def targeted_test_categories(lane: str) -> tuple[str, ...]:
    return TARGETED_TEST_CATEGORIES_BY_LANE.get(str(lane).strip().lower(), ("contract", "scenario", "replay"))


def unique_test_targets(targets: list[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for raw_target in targets:
        target = str(raw_target).strip()
        if not target or target in seen:
            continue
        selected.append(target)
        seen.add(target)
    return selected


def flatten_targeted_tests(lane: str, test_targets: dict[str, list[str]]) -> list[str]:
    return unique_test_targets(
        [
            target
            for key in targeted_test_categories(lane)
            for target in test_targets.get(key, [])
        ]
    )


def target_matches_any_token(target: str, tokens: tuple[str, ...]) -> bool:
    lowered = str(target).strip().lower()
    return any(re.search(rf"(?:^|[^a-z0-9]){re.escape(token)}(?:[^a-z0-9]|$)", lowered) for token in tokens)


def first_matching_target(targets: list[str], tokens: tuple[str, ...], *, exclude: set[str] | None = None) -> str:
    excluded = exclude or set()
    for target in targets:
        if target in excluded:
            continue
        if target_matches_any_token(target, tokens):
            return target
    return ""


def select_representative_contract_tests(targets: list[str]) -> list[str]:
    normalized = unique_test_targets(targets)
    if len(normalized) <= 1:
        return normalized
    selected: list[str] = []
    mutating = first_matching_target(normalized, MUTATING_CONTRACT_TOKENS)
    if mutating:
        selected.append(mutating)
    read = first_matching_target(normalized, READ_CONTRACT_TOKENS, exclude=set(selected))
    if read:
        selected.append(read)
    if not selected:
        selected.append(normalized[0])
    return unique_test_targets(selected)


def select_critical_targeted_tests(*, lane: str, test_targets: dict[str, list[str]]) -> list[str]:
    selected: list[str] = []
    for key in targeted_test_categories(lane):
        category_targets = unique_test_targets(test_targets.get(key, []))
        if key == "contract":
            selected.extend(select_representative_contract_tests(category_targets))
        elif category_targets:
            selected.append(category_targets[0])
    return unique_test_targets(selected)


def build_verification_commands(
    lane: str,
    test_targets: dict[str, list[str]],
    *,
    full_targeted_evidence: bool = True,
) -> dict[str, object]:
    lane_key = str(lane).strip().lower()
    targeted_tests = flatten_targeted_tests(lane_key, test_targets)
    critical_targeted_tests = select_critical_targeted_tests(lane=lane_key, test_targets=test_targets)
    unit_tests = [target for target in test_targets.get("unit", []) if str(target).strip()]
    if lane_key == "backend":
        lint = "pnpm --filter @app/api lint"
        typecheck = "pnpm --filter @app/api typecheck"
        build = "pnpm --filter @app/api build"
    elif lane_key == "frontend":
        lint = "pnpm --filter @app/web lint"
        typecheck = "pnpm --filter @app/web typecheck"
        build = "pnpm --filter @app/web build"
    else:
        lint = "pnpm lint"
        typecheck = "pnpm typecheck"
        build = "pnpm build"

    def vitest_command(report_filename: str, targets: list[str]) -> str:
        command = (
            f'pnpm exec vitest run --config vitest.config.ts --reporter=json --outputFile "$PHASE3_RUN_DIR/{report_filename}"'
        )
        if targets:
            command = f"{command} {quoted_targets(targets)}"
        return command

    def sequential_vitest_command(report_filename: str, targets: list[str], *, batch_size: int = 1) -> str:
        command = (
            "python3 scripts/run_vitest_targets_sequentially.py "
            '--workspace-root . --config vitest.config.ts '
            f'--report-path "$PHASE3_RUN_DIR/{report_filename}"'
        )
        if batch_size > 1:
            command = f"{command} --batch-size {int(batch_size)}"
        for target in targets:
            normalized = str(target).strip()
            if normalized:
                command = f"{command} --target {shlex.quote(normalized)}"
        return command

    sequence = ["lint", "typecheck"]
    commands: dict[str, str] = {
        "lint": lint,
        "typecheck": typecheck,
        "build": build,
    }
    reporting: dict[str, dict[str, str]] = {}

    if targeted_tests:
        if lane_key == "backend":
            backend_batch_size = backend_targeted_vitest_batch_size()
            commands["critical-targeted-tests"] = sequential_vitest_command(
                "critical-targeted-tests.vitest.json",
                critical_targeted_tests,
                batch_size=backend_batch_size,
            )
            commands["full-targeted-tests"] = sequential_vitest_command(
                "full-targeted-tests.vitest.json",
                targeted_tests,
                batch_size=backend_batch_size,
            )
            reporting["critical-targeted-tests"] = {
                "parser": "vitest-json",
                "report_path": "$PHASE3_RUN_DIR/critical-targeted-tests.vitest.json",
                "test_targets": critical_targeted_tests,
            }
            reporting["full-targeted-tests"] = {
                "parser": "vitest-json",
                "report_path": "$PHASE3_RUN_DIR/full-targeted-tests.vitest.json",
                "test_targets": targeted_tests,
            }
            if full_targeted_evidence:
                sequence.append("full-targeted-tests")
            else:
                sequence.append("critical-targeted-tests")
        else:
            sequence.append("targeted-tests")
            commands["targeted-tests"] = vitest_command("targeted-tests.vitest.json", targeted_tests)
            reporting["targeted-tests"] = {
                "parser": "vitest-json",
                "report_path": "$PHASE3_RUN_DIR/targeted-tests.vitest.json",
            }
    if unit_tests:
        sequence.append("unit-tests")
        commands["unit-tests"] = vitest_command("unit-tests.vitest.json", unit_tests)
        reporting["unit-tests"] = {
            "parser": "vitest-json",
            "report_path": "$PHASE3_RUN_DIR/unit-tests.vitest.json",
        }
    sequence.append("build")

    return {
        "workspace_scope": workspace_scope(lane),
        "sequence": sequence,
        "commands": commands,
        "reporting": reporting,
        "verification_layers": {
            "build_smoke": {
                "sequence": ["lint", "typecheck", "build"],
                "claim": "toolchain, static analysis, and package build are runnable",
            },
            "critical_runtime": {
                "sequence": ["critical-targeted-tests" if lane_key == "backend" else "targeted-tests"]
                if targeted_tests and not (lane_key == "backend" and full_targeted_evidence)
                else [],
                "test_targets": critical_targeted_tests if lane_key == "backend" else targeted_tests,
                "execution": (
                    "fast-mode-only"
                    if lane_key == "backend" and targeted_tests and full_targeted_evidence
                    else "in-default-sequence"
                ),
                "claim": "bounded runtime proof for service boundary, persistence, and representative business flow",
            },
            "full_evidence": {
                "sequence": ["full-targeted-tests"] if lane_key == "backend" and targeted_tests else (["targeted-tests"] if targeted_tests else []),
                "test_targets": targeted_tests,
                "execution": (
                    "in-default-sequence"
                    if full_targeted_evidence or not (lane_key == "backend" and targeted_tests)
                    else "deferred-by-fast-mode"
                ),
                "claim": "complete generated SQL, contract, scenario, and replay evidence",
            },
        },
        "note": "Frozen interface tests remain primary. Backend strict-runtime runs full-targeted-tests by default; critical-targeted-tests is reserved for explicit fast sampling. All Vitest steps must emit real JSON reports.",
    }


def ensure_loop_plan_metadata(output_dir: Path) -> None:
    metadata_path = output_dir / "phase3-run-metadata.json"
    metadata = load_json_if_exists(metadata_path) or {}
    metadata.setdefault("artifact_kind", "execution-loop-plan-only")
    metadata.setdefault("generation_entrypoint", "scripts/phase3/execution_loop_builder.py")
    metadata["has_execution_loop_plan"] = True
    write_text(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def iter_openapi_operations(document: dict[str, Any]) -> list[dict[str, str]]:
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        return []
    operations: list[dict[str, str]] = []
    for raw_path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method, operation in sorted(path_item.items()):
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])
            first_tag = str(tags[0]).strip() if isinstance(tags, list) and tags else ""
            raw_segments = [segment for segment in str(raw_path).strip("/").split("/") if segment]
            inferred_tag = raw_segments[1] if len(raw_segments) >= 2 else (raw_segments[0] if raw_segments else "api")
            operations.append(
                {
                    "operation_id": str(operation.get("operationId", "")).strip(),
                    "method": str(method).upper(),
                    "path": str(raw_path).strip(),
                    "tag": first_tag or inferred_tag,
                }
            )
    return operations


def build_contract_operation_lookup(output_dir: Path) -> dict[str, dict[str, str]]:
    openapi_path = output_dir / "contracts" / "openapi.yaml"
    document = load_json_if_exists(openapi_path)
    if document is None:
        return {}
    lookup: dict[str, dict[str, str]] = {}
    operations = iter_openapi_operations(document)
    target_lookup = build_contract_test_target_lookup(list(operations))
    for operation in operations:
        contract_target = (
            f"tests/contracts/{target_lookup[(operation['operation_id'], str(operation['method']).upper(), str(operation['path']))]}"
        )
        lookup[contract_target] = operation
    return lookup


def supplemental_contract_sources(
    output_dir: Path,
    *,
    assigned_contract_targets: set[str],
) -> tuple[list[str], list[dict[str, str]]]:
    contracts_dir = output_dir / "tests" / "contracts"
    if not contracts_dir.exists():
        return [], []
    existing_contract_targets = sorted(
        f"tests/contracts/{path.name}"
        for path in contracts_dir.glob("*.contract.test.ts")
        if path.is_file()
    )
    unassigned_targets = sorted(target for target in existing_contract_targets if target not in assigned_contract_targets)
    operation_lookup = build_contract_operation_lookup(output_dir)
    source_rows: list[dict[str, str]] = []
    for index, target in enumerate(unassigned_targets, start=1):
        operation = operation_lookup.get(target, {})
        operation_id = str(operation.get("operation_id", "")).strip() or Path(target).stem
        source_rows.append(
            {
                "source_id": f"P3-OCT-{index:02d}",
                "source_type": "endpoint-contract-fallback",
                "source_subject": (
                    f"{operation_id} supplemental contract closure"
                    if operation
                    else f"Supplemental contract closure for {Path(target).name}"
                ),
            }
        )
    return unassigned_targets, source_rows


def split_targets_by_lane(targets: list[str]) -> dict[str, list[str]]:
    split = {"backend": [], "frontend": [], "platform": []}
    for target in targets:
        normalized = str(target).strip()
        if not normalized:
            continue
        if normalized.startswith("apps/api/"):
            split["backend"].append(normalized)
        elif normalized.startswith("apps/web/"):
            split["frontend"].append(normalized)
        else:
            split["platform"].append(normalized)
    return {lane: sorted(set(values)) for lane, values in split.items()}


def test_targets_for_lane(lane: str, categorized_tests: dict[str, Any]) -> dict[str, list[str]]:
    backend_categories = ("sql", "contract", "scenario", "replay")
    frontend_categories = ("scenario", "replay")
    platform_categories = ("contract", "scenario", "replay")
    if lane == "backend":
        allowed_categories = backend_categories
        unit_prefix = "tests/unit/api/"
    elif lane == "frontend":
        allowed_categories = frontend_categories
        unit_prefix = "tests/unit/web/"
    else:
        allowed_categories = platform_categories
        unit_prefix = "tests/unit/platform/"

    selected = {key: [] for key in ("sql", "contract", "scenario", "replay", "unit")}
    for key in allowed_categories:
        selected[key] = [
            str(item).strip()
            for item in categorized_tests.get(key, [])
            if str(item).strip()
        ]
    selected["unit"] = [
        str(item).strip()
        for item in categorized_tests.get("unit", [])
        if str(item).strip() and str(item).strip().startswith(unit_prefix)
    ]
    return selected


def dedupe_dict_rows(rows: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    kept: list[dict[str, Any]] = []
    for row in rows:
        key = tuple(str(row.get(field, "")).strip() for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def dedupe_strings_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        kept.append(normalized)
    return kept


def partition_existing_test_targets(
    *,
    output_dir: Path,
    categorized_tests: dict[str, Any],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    runnable = {key: [] for key in ("sql", "contract", "scenario", "replay", "unit")}
    missing = {key: [] for key in ("sql", "contract", "scenario", "replay", "unit")}
    for key in runnable:
        values = categorized_tests.get(key, [])
        if not isinstance(values, list):
            continue
        for item in values:
            target = str(item).strip()
            if not target:
                continue
            target_path = Path(target)
            candidate_path = target_path if target_path.is_absolute() else output_dir / target_path
            bucket = runnable if candidate_path.exists() else missing
            bucket[key].append(target)
    return (
        {key: sorted(set(values)) for key, values in runnable.items()},
        {key: sorted(set(values)) for key, values in missing.items()},
    )


def packet_markdown(packet: dict[str, Any], output_locale: str | None = None) -> str:
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
                    f"- {title}: pattern={design.get('page_blueprint_type', 'unknown')} work_region={design.get('primary_work_region', 'n/a')}"
                )
                for transition in design.get("business_state_transitions", [])[:3]:
                    if not isinstance(transition, dict):
                        continue
                    lines.append(
                        f"- transition: {transition.get('domain_object', 'object')} {transition.get('from_state', 'unknown')} -> {transition.get('to_state', 'unknown')} via {transition.get('trigger_action', 'action')}"
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
                    f"- {row.get('operation_id', 'unknown')} -> controller={row.get('controller_target', 'n/a')} service={row.get('service_target', 'n/a')} repository={row.get('repository_target', 'n/a')}"
                )
    return localize_phase3_worker_input_packet("\n".join(lines) + "\n", output_locale)


def loop_plan_markdown(plan: dict[str, Any], output_locale: str | None = None) -> str:
    summary = plan.get("summary", {})
    lines = [
        "# Phase-3 Execution Loop Plan",
        "",
        "## Summary",
        f"- overall_status: {plan.get('overall_status', 'unknown')}",
        f"- wave_count: {summary.get('wave_count', 0)}",
        f"- worker_packet_count: {summary.get('worker_packet_count', 0)}",
        f"- ready_now_wave_count: {summary.get('ready_now_wave_count', 0)}",
        f"- queued_wave_count: {summary.get('queued_wave_count', 0)}",
        f"- blocked_wave_count: {summary.get('blocked_wave_count', 0)}",
        f"- unassigned_contract_test_count: {summary.get('unassigned_contract_test_count', 0)}",
        "",
        "## Waves",
    ]
    for wave in plan.get("waves", []):
        lines.extend(
            [
                f"### Wave {wave['wave']}",
                f"- structural_status: {wave['structural_status']}",
                f"- dispatch_state: {wave['dispatch_state']}",
                f"- worker_packet_count: {wave['worker_packet_count']}",
            ]
        )
        for packet in wave.get("worker_packets", []):
            lines.append(
                f"- {packet['lane']} [{packet['worker_packet_status']}] dispatch={packet['dispatch_state']} wps={', '.join(packet['work_package_ids'])}"
            )
        lines.append("")
    if plan.get("unscheduled_rows"):
        lines.extend(["## Unscheduled"])
        for row in plan["unscheduled_rows"]:
            lines.append(f"- {row['wp_id']}: {', '.join(row.get('blocking_reasons', [])) or 'none'}")
        lines.append("")
    return localize_phase3_execution_loop_plan("\n".join(lines) + "\n", output_locale)


def build_execution_loop(
    *,
    wave_plan: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    packets_root = output_dir / "worker-input-packets"
    ensure_loop_plan_metadata(output_dir)
    wave_rows = wave_plan.get("waves", [])
    if not isinstance(wave_rows, list):
        raise ValueError("wave_plan must contain waves")

    loop_waves: list[dict[str, Any]] = []
    all_worker_packets: list[dict[str, Any]] = []
    lane_counter: dict[str, int] = {"backend": 0, "frontend": 0, "platform": 0}
    assigned_contract_targets: set[str] = set()

    prior_waves_structurally_ready = True
    for wave_row in wave_rows:
        wave_number = int(wave_row.get("wave", 0) or 0)
        wp_rows = wave_row.get("rows", [])
        lane_groups: dict[str, list[dict[str, Any]]] = {"backend": [], "frontend": [], "platform": []}

        for wp_row in wp_rows:
            packet_ref = str(wp_row.get("packet_json", "")).strip()
            if not packet_ref:
                continue
            wp_packet = load_json(output_dir / packet_ref)
            lane_targets = split_targets_by_lane([str(item) for item in wp_packet.get("implementation_targets", [])])

            for lane, targets in lane_targets.items():
                if not targets:
                    continue
                lane_groups[lane].append(
                    {
                        "wave_row": wp_row,
                        "wp_packet": wp_packet,
                        "assigned_targets": targets,
                    }
                )

        worker_packets: list[dict[str, Any]] = []
        for lane in ("backend", "frontend", "platform"):
            assignments = lane_groups[lane]
            if not assignments:
                continue

            work_packages: list[dict[str, Any]] = []
            source_rows: list[dict[str, Any]] = []
            contract_operations: list[dict[str, Any]] = []
            frontend_surfaces: list[str] = []
            implementation_targets: list[str] = []
            test_targets = {"sql": [], "contract": [], "scenario": [], "replay": [], "unit": []}
            missing_test_targets = {"sql": [], "contract": [], "scenario": [], "replay": [], "unit": []}
            blocking_reasons: list[str] = []
            upstream_wp_dependencies: set[str] = set()
            upstream_wave_ids: set[int] = set()
            packet_refs: list[str] = []

            for assignment in assignments:
                wp_row = assignment["wave_row"]
                wp_packet = assignment["wp_packet"]
                assigned_targets = assignment["assigned_targets"]
                wp_id = str(wp_row.get("wp_id", "")).strip()
                packet_refs.append(str(wp_row.get("packet_json", "")).strip())
                work_packages.append(
                    {
                        "wp_id": wp_id,
                        "scope": str(wp_packet.get("scope", "")).strip(),
                        "acceptance_criteria": str(wp_packet.get("acceptance_criteria", "")).strip(),
                        "wp_execution_readiness": str(wp_row.get("execution_readiness", "")).strip() or "unknown",
                        "wp_packet_status": str(wp_packet.get("packet_status", "")).strip() or "unknown",
                        "assigned_target_count": len(assigned_targets),
                        "assigned_targets": assigned_targets,
                        "wp_packet_json": str(wp_row.get("packet_json", "")).strip(),
                        "wp_packet_markdown": str(wp_row.get("packet_markdown", "")).strip(),
                        "blocking_reasons": [str(item).strip() for item in wp_row.get("blocking_reasons", []) if str(item).strip()],
                    }
                )
                implementation_targets.extend(assigned_targets)
                source_rows.extend([row for row in wp_packet.get("source_rows", []) if isinstance(row, dict)])
                contract_operations.extend([row for row in wp_packet.get("contract_operations", []) if isinstance(row, dict)])
                frontend_surfaces.extend(str(item).strip() for item in wp_packet.get("frontend_surfaces", []) if str(item).strip())
                categorized_tests = wp_packet.get("test_targets", {})
                if isinstance(categorized_tests, dict):
                    lane_tests = test_targets_for_lane(lane, categorized_tests)
                    runnable_lane_tests, missing_lane_tests = partition_existing_test_targets(
                        output_dir=output_dir,
                        categorized_tests=lane_tests,
                    )
                    for key in ("sql", "contract", "scenario", "replay", "unit"):
                        test_targets[key].extend(runnable_lane_tests[key])
                        missing_test_targets[key].extend(missing_lane_tests[key])
                    assigned_contract_targets.update(
                        str(item).strip()
                        for item in runnable_lane_tests.get("contract", [])
                        if str(item).strip()
                    )
                    blocking_reasons.extend(
                        f"missing_test_target:{target}"
                        for values in missing_lane_tests.values()
                        for target in values
                    )
                blocking_reasons.extend(str(item).strip() for item in wp_row.get("blocking_reasons", []) if str(item).strip())
                for dep in [str(item).strip() for item in wp_row.get("depends_on", []) if str(item).strip()]:
                    upstream_wp_dependencies.add(dep)
                for candidate_wave in wave_rows:
                    candidate_number = int(candidate_wave.get("wave", 0) or 0)
                    candidate_wp_ids = {
                        str(item.get("wp_id", "")).strip()
                        for item in candidate_wave.get("rows", [])
                        if isinstance(item, dict)
                    }
                    if candidate_number < wave_number and candidate_wp_ids & set(wp_row.get("depends_on", [])):
                        upstream_wave_ids.add(candidate_number)

            worker_packet_status = "ready" if not blocking_reasons else "blocked"
            if not prior_waves_structurally_ready:
                dispatch_state = "blocked-by-earlier-wave"
            elif worker_packet_status != "ready":
                dispatch_state = "blocked"
            elif wave_number == 1:
                dispatch_state = "ready-now"
            else:
                dispatch_state = "queued-on-prior-wave"

            frontend_surface_designs: list[dict[str, Any]] = []
            prototype_constraints: dict[str, str] = {}
            external_executor_brief: list[str] = []
            semantic_disqualifiers: list[str] = []
            if lane == "frontend":
                ordered_frontend_surfaces = dedupe_strings_in_order(frontend_surfaces)
                ordered_implementation_targets = dedupe_strings_in_order(implementation_targets)
                (
                    frontend_surface_designs,
                    prototype_constraints,
                    external_executor_brief,
                    semantic_disqualifiers,
                ) = select_frontend_surface_designs(
                    output_dir=output_dir,
                    frontend_surfaces=ordered_frontend_surfaces,
                    implementation_targets=ordered_implementation_targets,
                )
            else:
                ordered_frontend_surfaces = dedupe_strings_in_order(frontend_surfaces)
                ordered_implementation_targets = dedupe_strings_in_order(implementation_targets)

            worker_packet = {
                "packet_id": f"wave-{wave_number:02d}:{lane}",
                "wave": wave_number,
                "lane": lane,
                "skill_entrypoint_hint": lane_skill_hint(lane),
                "worker_packet_status": worker_packet_status,
                "dispatch_state": dispatch_state,
                "primary_test_categories": primary_test_categories(lane),
                "verification_commands": build_verification_commands(lane, {key: sorted(set(values)) for key, values in test_targets.items()}),
                "work_package_ids": [row["wp_id"] for row in work_packages],
                "upstream_wave_ids": sorted(upstream_wave_ids),
                "upstream_wp_dependencies": sorted(upstream_wp_dependencies),
                "packet_refs": sorted(set(packet_refs)),
                "work_packages": work_packages,
                "source_rows": dedupe_dict_rows(source_rows, ("source_id", "source_type", "source_subject")),
                "test_targets": {key: sorted(set(values)) for key, values in test_targets.items()},
                "missing_test_targets": {key: sorted(set(values)) for key, values in missing_test_targets.items()},
                "implementation_targets": ordered_implementation_targets,
                "contract_operations": dedupe_dict_rows(
                    contract_operations,
                    ("operation_id", "method", "path"),
                ),
                "frontend_surfaces": ordered_frontend_surfaces,
                "frontend_surface_designs": frontend_surface_designs,
                "prototype_constraints": prototype_constraints,
                "external_executor_brief": external_executor_brief,
                "semantic_disqualifiers": semantic_disqualifiers,
                "trace_subject_ids": sorted(
                    {
                        str(row.get("source_id", "")).strip()
                        for row in source_rows
                        if isinstance(row, dict) and str(row.get("source_id", "")).strip()
                    }
                ),
                "done_criteria": sorted(
                    set(
                        [
                            *[
                                f"{row['wp_id']}: {row['acceptance_criteria']}"
                                for row in work_packages
                                if row.get("acceptance_criteria")
                            ],
                            "Assigned contract/scenario/replay tests stay green for the packet scope before widening implementation.",
                            "Assigned unit tests are green for the packet-owned implementation targets.",
                            "Verification commands complete without breaking the frozen contract surface.",
                        ]
                    )
                ),
                "blocking_reasons": sorted(set(blocking_reasons)),
                "coordination_notes": [
                    "Keep OpenAPI, migrations, and trace IDs frozen while making assigned tests green.",
                    "Do not revert other worker changes; adjust to parallel edits on disjoint targets.",
                ],
                "environment_bootstrap": environment_bootstrap("."),
            }
            if lane == "backend":
                worker_packet["implementation_playbook"] = build_backend_playbook(
                    contract_operations=worker_packet["contract_operations"],
                    implementation_targets=worker_packet["implementation_targets"],
                    test_targets=worker_packet["test_targets"],
                )
            elif lane == "frontend":
                worker_packet["implementation_playbook"] = build_frontend_playbook(
                    frontend_surfaces=worker_packet["frontend_surfaces"],
                    frontend_surface_designs=worker_packet["frontend_surface_designs"],
                    prototype_constraints=worker_packet["prototype_constraints"],
                    external_executor_brief=worker_packet["external_executor_brief"],
                    semantic_disqualifiers=worker_packet["semantic_disqualifiers"],
                    test_targets=worker_packet["test_targets"],
                )
            else:
                worker_packet["implementation_playbook"] = build_platform_playbook(
                    test_targets=worker_packet["test_targets"],
                )
            wave_dir = packets_root / f"wave-{wave_number:02d}"
            json_path = wave_dir / f"{lane}-worker-input-packet.json"
            markdown_path = wave_dir / f"{lane}-worker-input-packet.md"
            write_text(json_path, json.dumps(worker_packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            write_text(markdown_path, packet_markdown(worker_packet))

            loop_worker_row = {
                "wave": wave_number,
                "lane": lane,
                "worker_packet_status": worker_packet_status,
                "dispatch_state": dispatch_state,
                "skill_entrypoint_hint": worker_packet["skill_entrypoint_hint"],
                "work_package_ids": worker_packet["work_package_ids"],
                "implementation_target_count": len(worker_packet["implementation_targets"]),
                "test_count": sum(len(values) for values in worker_packet["test_targets"].values()),
                "packet_json": str(json_path.relative_to(output_dir)),
                "packet_markdown": str(markdown_path.relative_to(output_dir)),
            }
            worker_packets.append(loop_worker_row)
            all_worker_packets.append(loop_worker_row)
            lane_counter[lane] += 1

        if not worker_packets:
            structural_status = "blocked"
        elif all(packet["worker_packet_status"] == "ready" for packet in worker_packets):
            structural_status = "ready"
        elif any(packet["worker_packet_status"] == "ready" for packet in worker_packets):
            structural_status = "partially-blocked"
        else:
            structural_status = "blocked"

        if not prior_waves_structurally_ready:
            dispatch_state = "blocked-by-earlier-wave"
        elif structural_status != "ready":
            dispatch_state = "blocked"
        elif wave_number == 1:
            dispatch_state = "ready-now"
        else:
            dispatch_state = "queued-on-prior-wave"

        for packet in worker_packets:
            if dispatch_state == "blocked-by-earlier-wave" and packet["worker_packet_status"] == "ready":
                packet["dispatch_state"] = "blocked-by-earlier-wave"

        loop_waves.append(
            {
                "wave": wave_number,
                "structural_status": structural_status,
                "dispatch_state": dispatch_state,
                "worker_packet_count": len(worker_packets),
                "worker_packets": worker_packets,
            }
        )
        prior_waves_structurally_ready = prior_waves_structurally_ready and structural_status == "ready"

    supplemental_contract_targets, supplemental_source_rows = supplemental_contract_sources(
        output_dir,
        assigned_contract_targets=assigned_contract_targets,
    )
    supplemental_contract_packet_count = 0
    if supplemental_contract_targets:
        operation_lookup = build_contract_operation_lookup(output_dir)
        contract_operations = [
            operation_lookup[target]
            for target in supplemental_contract_targets
            if target in operation_lookup
        ]
        implementation_targets = sorted(
            {
                target
                for operation in contract_operations
                for target in [
                    f"apps/api/src/modules/{slugify(operation.get('tag', '') or operation.get('operation_id', '') or operation.get('path', 'api'))}/{slugify(operation.get('tag', '') or operation.get('operation_id', '') or operation.get('path', 'api'))}.controller.ts",
                    f"apps/api/src/modules/{slugify(operation.get('tag', '') or operation.get('operation_id', '') or operation.get('path', 'api'))}/{slugify(operation.get('tag', '') or operation.get('operation_id', '') or operation.get('path', 'api'))}.service.ts",
                    f"apps/api/src/modules/{slugify(operation.get('tag', '') or operation.get('operation_id', '') or operation.get('path', 'api'))}/{slugify(operation.get('tag', '') or operation.get('operation_id', '') or operation.get('path', 'api'))}.repository.ts",
                ]
            }
        )
        wave_number = (max((wave.get("wave", 0) for wave in loop_waves), default=0)) + 1
        dispatch_state = "ready-now" if wave_number == 1 else "queued-on-prior-wave"
        if not prior_waves_structurally_ready:
            dispatch_state = "blocked-by-earlier-wave"
        test_targets = {"sql": [], "contract": supplemental_contract_targets, "scenario": [], "replay": [], "unit": []}
        worker_packet = {
            "packet_id": f"wave-{wave_number:02d}:backend",
            "wave": wave_number,
            "lane": "backend",
            "skill_entrypoint_hint": lane_skill_hint("backend"),
            "worker_packet_status": "ready",
            "dispatch_state": dispatch_state,
            "primary_test_categories": primary_test_categories("backend"),
            "verification_commands": build_verification_commands("backend", test_targets),
            "work_package_ids": [],
            "upstream_wave_ids": [wave_number - 1] if wave_number > 1 else [],
            "upstream_wp_dependencies": [],
            "packet_refs": [],
            "work_packages": [],
            "source_rows": supplemental_source_rows,
            "test_targets": test_targets,
            "missing_test_targets": {"sql": [], "contract": [], "scenario": [], "replay": [], "unit": []},
            "implementation_targets": implementation_targets,
            "contract_operations": contract_operations,
            "frontend_surfaces": [],
            "trace_subject_ids": [row["source_id"] for row in supplemental_source_rows],
            "done_criteria": [
                "All previously unassigned frozen contract tests are executed and green.",
                "Supplemental contract closure does not mutate the frozen contract surface.",
            ],
            "blocking_reasons": [],
            "coordination_notes": [
                "This packet closes contract tests that were generated from frozen endpoints but not assigned to any work-package packet.",
                "Treat it as endpoint coverage closure, not a substitute for normal WP ownership.",
            ],
            "environment_bootstrap": environment_bootstrap("."),
            "supplemental_contract_closure": True,
        }
        worker_packet["implementation_playbook"] = build_backend_playbook(
            contract_operations=contract_operations,
            implementation_targets=worker_packet["implementation_targets"],
            test_targets=worker_packet["test_targets"],
        )
        wave_dir = packets_root / f"wave-{wave_number:02d}"
        json_path = wave_dir / "backend-worker-input-packet.json"
        markdown_path = wave_dir / "backend-worker-input-packet.md"
        write_text(json_path, json.dumps(worker_packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        write_text(markdown_path, packet_markdown(worker_packet))

        loop_worker_row = {
            "wave": wave_number,
            "lane": "backend",
            "worker_packet_status": "ready",
            "dispatch_state": dispatch_state,
            "skill_entrypoint_hint": worker_packet["skill_entrypoint_hint"],
            "work_package_ids": [],
            "implementation_target_count": len(worker_packet["implementation_targets"]),
            "test_count": len(supplemental_contract_targets),
            "packet_json": str(json_path.relative_to(output_dir)),
            "packet_markdown": str(markdown_path.relative_to(output_dir)),
            "supplemental_contract_closure": True,
        }
        loop_waves.append(
            {
                "wave": wave_number,
                "structural_status": "ready" if prior_waves_structurally_ready else "blocked",
                "dispatch_state": dispatch_state,
                "worker_packet_count": 1,
                "worker_packets": [loop_worker_row],
                "supplemental_contract_closure": True,
            }
        )
        all_worker_packets.append(loop_worker_row)
        lane_counter["backend"] += 1
        supplemental_contract_packet_count = 1

    plan = {
        "overall_status": "valid" if str(wave_plan.get("overall_status", "")).strip() == "valid" else "invalid",
        "summary": {
            "wave_count": len(loop_waves),
            "worker_packet_count": len(all_worker_packets),
            "ready_now_wave_count": sum(1 for wave in loop_waves if wave["dispatch_state"] == "ready-now"),
            "queued_wave_count": sum(1 for wave in loop_waves if wave["dispatch_state"] == "queued-on-prior-wave"),
            "blocked_wave_count": sum(1 for wave in loop_waves if wave["dispatch_state"] in {"blocked", "blocked-by-earlier-wave"}),
            "ready_worker_packet_count": sum(1 for row in all_worker_packets if row["worker_packet_status"] == "ready"),
            "blocked_worker_packet_count": sum(1 for row in all_worker_packets if row["worker_packet_status"] != "ready"),
            "lane_counts": {lane: count for lane, count in lane_counter.items() if count > 0},
            "supplemental_contract_packet_count": supplemental_contract_packet_count,
            "unassigned_contract_test_count": len(supplemental_contract_targets),
        },
        "waves": loop_waves,
        "unscheduled_rows": wave_plan.get("unscheduled_rows", []),
    }

    json_path = output_dir / "execution-loop-plan.json"
    markdown_path = output_dir / "execution-loop-plan.md"
    write_text(json_path, json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(markdown_path, loop_plan_markdown(plan))
    return {
        "output_path": str(json_path),
        "markdown_path": str(markdown_path),
        **plan["summary"],
        "overall_status": plan["overall_status"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build worker input packets and execution loop plan")
    parser.add_argument("--wave-plan", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_execution_loop(
        wave_plan=load_json(Path(args.wave_plan).resolve()),
        output_dir=Path(args.output_dir).resolve(),
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["overall_status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
