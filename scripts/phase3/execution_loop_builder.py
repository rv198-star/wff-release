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
import re
from pathlib import Path
from typing import Any

from phase3.action_card_slice_packets import build_backend_subagent_slice_packets, mark_slice_file_conflicts
from phase3.collection_tools import dedupe_dict_rows, dedupe_strings_in_order
from phase3.contract_test_scaffolder import build_contract_test_target_lookup
from phase3.review_support import write_json_and_markdown_report, write_json_report
from phase3.worker_packet_artifacts import worker_input_packet_markdown
import phase3.verification_plan as verification_plan
import phase3.worker_playbook as worker_playbook
import phase3.execution_loop_artifacts as execution_loop_artifacts
import phase3.work_package_planning as work_package_planning


BACKEND_TARGETED_VITEST_BATCH_SIZE = verification_plan.BACKEND_TARGETED_VITEST_BATCH_SIZE
TARGETED_TEST_CATEGORIES_BY_LANE = verification_plan.TARGETED_TEST_CATEGORIES_BY_LANE
MUTATING_CONTRACT_TOKENS = verification_plan.MUTATING_CONTRACT_TOKENS


def backend_targeted_vitest_batch_size() -> int:
    return verification_plan.backend_targeted_vitest_batch_size()


READ_CONTRACT_TOKENS = verification_plan.READ_CONTRACT_TOKENS


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def materialize_worker_packet(
    *,
    json_path: Path,
    worker_packet: dict[str, Any],
) -> dict[str, str]:
    return write_json_and_markdown_report(
        json_path=json_path,
        report=worker_packet,
        markdown=worker_input_packet_markdown(worker_packet),
    )


def build_wave_plan_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    return work_package_planning.build_wave_plan_markdown(report, output_locale)


def build_work_package_wave_plan(
    *,
    esp_text: str,
    packet_index: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    return work_package_planning.build_work_package_wave_plan(
        esp_text=esp_text,
        packet_index=packet_index,
        output_dir=output_dir,
    )


def collect_trace_refs(text: str) -> set[str]:
    return work_package_planning.collect_trace_refs(text)


def classify_lane(implementation_targets: list[str]) -> str:
    return work_package_planning.classify_lane(implementation_targets)


def build_contract_test_lookup(openapi_spec: dict[str, object]) -> dict[str, dict[str, str]]:
    return work_package_planning.build_contract_test_lookup(openapi_spec)


def build_surface_lookup(esp_text: str, *, output_dir: Path | None = None) -> dict[str, str]:
    return work_package_planning.build_surface_lookup(esp_text, output_dir=output_dir)


def infer_targets_from_scope(
    *,
    scope: str,
    acceptance_criteria: str,
    openapi_spec: dict[str, object],
    surface_lookup: dict[str, str],
) -> list[str]:
    return work_package_planning.infer_targets_from_scope(
        scope=scope,
        acceptance_criteria=acceptance_criteria,
        openapi_spec=openapi_spec,
        surface_lookup=surface_lookup,
    )


def build_scenario_lookup(stage_03_text: str) -> dict[str, dict[str, object]]:
    return work_package_planning.build_scenario_lookup(stage_03_text)


def build_replay_lookup(stage_04_text: str) -> dict[str, dict[str, object]]:
    return work_package_planning.build_replay_lookup(stage_04_text)


def categorize_tests(test_targets: list[str]) -> dict[str, list[str]]:
    return work_package_planning.categorize_tests(test_targets)


def execution_packet_markdown(packet: dict[str, Any], output_locale: str | None = None) -> str:
    return work_package_planning.execution_packet_markdown(packet, output_locale)


def build_work_package_packets(
    *,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    openapi_spec: dict[str, object],
    implementation_bindings: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    return work_package_planning.build_work_package_packets(
        esp_text=esp_text,
        stage_03_text=stage_03_text,
        stage_04_text=stage_04_text,
        openapi_spec=openapi_spec,
        implementation_bindings=implementation_bindings,
        output_dir=output_dir,
    )


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
    return worker_playbook.lane_skill_hint(lane)


def primary_test_categories(lane: str) -> list[str]:
    return verification_plan.primary_test_categories(lane)


def workspace_scope(lane: str) -> str:
    return verification_plan.workspace_scope(lane)


def slugify(value: str) -> str:
    return worker_playbook.slugify(value)


def quoted_targets(targets: list[str]) -> str:
    return verification_plan.quoted_targets(targets)


def build_backend_playbook(
    *,
    contract_operations: list[dict[str, Any]],
    implementation_targets: list[str],
    test_targets: dict[str, list[str]],
) -> dict[str, Any]:
    return worker_playbook.build_backend_playbook(
        contract_operations=contract_operations,
        implementation_targets=implementation_targets,
        test_targets=test_targets,
    )


def build_frontend_playbook(
    *,
    frontend_surfaces: list[str],
    frontend_surface_designs: list[dict[str, Any]],
    prototype_constraints: dict[str, str],
    external_executor_brief: list[str],
    semantic_disqualifiers: list[str],
    test_targets: dict[str, list[str]],
) -> dict[str, Any]:
    return worker_playbook.build_frontend_playbook(
        frontend_surfaces=frontend_surfaces,
        frontend_surface_designs=frontend_surface_designs,
        prototype_constraints=prototype_constraints,
        external_executor_brief=external_executor_brief,
        semantic_disqualifiers=semantic_disqualifiers,
        test_targets=test_targets,
    )


def build_platform_playbook(test_targets: dict[str, list[str]]) -> dict[str, Any]:
    return worker_playbook.build_platform_playbook(test_targets)


def environment_bootstrap(workspace_root_hint: str = ".") -> dict[str, str]:
    return verification_plan.environment_bootstrap(workspace_root_hint)


def targeted_test_categories(lane: str) -> tuple[str, ...]:
    return verification_plan.targeted_test_categories(lane)


def unique_test_targets(targets: list[str]) -> list[str]:
    return verification_plan.unique_test_targets(targets)


def flatten_targeted_tests(lane: str, test_targets: dict[str, list[str]]) -> list[str]:
    return verification_plan.flatten_targeted_tests(lane, test_targets)


def target_matches_any_token(target: str, tokens: tuple[str, ...]) -> bool:
    return verification_plan.target_matches_any_token(target, tokens)


def first_matching_target(targets: list[str], tokens: tuple[str, ...], *, exclude: set[str] | None = None) -> str:
    return verification_plan.first_matching_target(targets, tokens, exclude=exclude)


def select_representative_contract_tests(targets: list[str]) -> list[str]:
    return verification_plan.select_representative_contract_tests(targets)


def select_critical_targeted_tests(*, lane: str, test_targets: dict[str, list[str]]) -> list[str]:
    return verification_plan.select_critical_targeted_tests(lane=lane, test_targets=test_targets)


def build_verification_commands(
    lane: str,
    test_targets: dict[str, list[str]],
    *,
    validation_level: str = "",
    full_targeted_evidence: bool = True,
) -> dict[str, object]:
    return verification_plan.build_verification_commands(
        lane,
        test_targets,
        validation_level=validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )


def ensure_loop_plan_metadata(output_dir: Path) -> None:
    metadata_path = output_dir / "phase3-run-metadata.json"
    metadata = load_json_if_exists(metadata_path) or {}
    metadata.setdefault("artifact_kind", "execution-loop-plan-only")
    metadata.setdefault("generation_entrypoint", "scripts/phase3/execution_loop_builder.py")
    metadata["has_execution_loop_plan"] = True
    write_json_report(metadata_path, metadata)


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
    return worker_input_packet_markdown(packet, output_locale)


def loop_plan_markdown(plan: dict[str, Any], output_locale: str | None = None) -> str:
    return execution_loop_artifacts.execution_loop_plan_markdown(plan, output_locale)


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
                worker_packet["subagent_slice_packets"] = build_backend_subagent_slice_packets(worker_packet)
                worker_packet["subagent_slice_conflict_summary"] = mark_slice_file_conflicts(
                    worker_packet["subagent_slice_packets"]
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
                worker_packet["subagent_slice_packets"] = []
                worker_packet["subagent_slice_conflict_summary"] = {
                    "conflict_count": 0,
                    "conflicting_files": [],
                    "file_owners": {},
                }
            else:
                worker_packet["implementation_playbook"] = build_platform_playbook(
                    test_targets=worker_packet["test_targets"],
                )
                worker_packet["subagent_slice_packets"] = []
                worker_packet["subagent_slice_conflict_summary"] = {
                    "conflict_count": 0,
                    "conflicting_files": [],
                    "file_owners": {},
                }
            wave_dir = packets_root / f"wave-{wave_number:02d}"
            json_path = wave_dir / f"{lane}-worker-input-packet.json"
            markdown_path = wave_dir / f"{lane}-worker-input-packet.md"
            materialize_worker_packet(json_path=json_path, worker_packet=worker_packet)

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
        worker_packet["subagent_slice_packets"] = build_backend_subagent_slice_packets(worker_packet)
        worker_packet["subagent_slice_conflict_summary"] = mark_slice_file_conflicts(worker_packet["subagent_slice_packets"])
        wave_dir = packets_root / f"wave-{wave_number:02d}"
        json_path = wave_dir / "backend-worker-input-packet.json"
        markdown_path = wave_dir / "backend-worker-input-packet.md"
        materialize_worker_packet(json_path=json_path, worker_packet=worker_packet)

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
    write_json_and_markdown_report(
        json_path=json_path,
        report=plan,
        markdown=loop_plan_markdown(plan),
        markdown_path=markdown_path,
    )
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
