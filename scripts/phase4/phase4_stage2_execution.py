#!/usr/bin/env python3
"""
Execute the Phase-4 Stage-02 evidence pass from Stage-01 outputs and inherited Phase-3 evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from pathlib import Path
from typing import Any

from common.output_language import localize_phase4_stage2_execution_markdown
from phase4.phase4_common import (
    api_id_for_operation,
    collect_test_evidence,
    collect_visual_evidence_paths,
    compact_token,
    dedupe_preserve_order,
    ensure_list,
    extract_operation_ids_from_file,
    extract_operation_ids_from_text,
    load_json,
    load_phase3_mainline_summary,
    load_phase3_runtime_environment_summary,
    load_worker_packets,
    relative_to_root,
    render_markdown_table,
    utc_now_iso,
    write_json,
    write_text,
)
from phase4.phase4_stage1_planning import STAGE_DIRNAME as STAGE01_DIRNAME


STAGE_DIRNAME = "stage-02-evidence-execution-and-defect-identification"


def resolve_external_path(raw_path: str, manifest_path: Path, external_evidence_dir: Path | None) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    if external_evidence_dir is not None:
        evidence_candidate = (external_evidence_dir / candidate).resolve()
        if evidence_candidate.exists():
            return evidence_candidate
    manifest_candidate = (manifest_path.parent / candidate).resolve()
    if manifest_candidate.exists():
        return manifest_candidate
    return manifest_candidate


def load_external_evidence_manifest(
    manifest_path: Path | None,
    *,
    phase3_root: Path,
    external_evidence_dir: Path | None,
) -> dict[str, Any]:
    if manifest_path is None:
        return {
            "manifest_path": "",
            "items": [],
            "summary": {"item_count": 0, "valid_item_count": 0, "missing_path_count": 0},
        }

    payload = load_json(manifest_path)
    normalized_items: list[dict[str, Any]] = []
    missing_paths: list[str] = []
    for raw_item in ensure_list(payload.get("items")):
        evidence_paths: list[str] = []
        for raw_path in ensure_list(raw_item.get("evidence_paths") or raw_item.get("paths") or raw_item.get("files")):
            resolved = resolve_external_path(str(raw_path), manifest_path, external_evidence_dir)
            if resolved.exists():
                evidence_paths.append(relative_to_root(resolved, phase3_root))
            else:
                missing_paths.append(str(resolved))
        reviewer = str(raw_item.get("reviewer") or raw_item.get("reviewer_role") or "").strip()
        note = str(raw_item.get("note") or raw_item.get("manual_review_note") or "").strip()
        evidence_type = str(raw_item.get("evidence_type") or "manual-review-note").strip()
        if evidence_type == "manual-review-note" and note and reviewer and not evidence_paths:
            evidence_paths = [relative_to_root(manifest_path, phase3_root)]
        route_observation = _route_observation_from_note(note, raw_item if isinstance(raw_item, dict) else {})
        normalized_items.append(
            {
                "test_id": str(raw_item.get("test_id") or "").strip(),
                "surface_name": str(raw_item.get("surface_name") or "").strip(),
                "surface_slug": str(raw_item.get("surface_slug") or "").strip(),
                "acceptance_types": [
                    str(value)
                    for value in ensure_list(
                        raw_item.get("for_acceptance_types")
                        or raw_item.get("acceptance_types")
                        or raw_item.get("acceptance_type")
                    )
                    if str(value).strip()
                ],
                "evidence_type": evidence_type,
                "status": str(raw_item.get("status") or "pass").strip().lower(),
                "signoff": bool(raw_item.get("signoff")),
                "reviewer": reviewer,
                "note": note,
                "evidence_paths": evidence_paths,
                "requested_route": route_observation["requested_route"],
                "final_route": route_observation["final_route"],
                "route_landing_status": route_observation["route_landing_status"],
                "auth_entry_route": route_observation["auth_entry_route"],
            }
        )
    valid_item_count = len(
        [
            item
            for item in normalized_items
            if item["evidence_paths"] or (item["evidence_type"] == "manual-review-note" and item["reviewer"] and item["note"])
        ]
    )
    return {
        "manifest_path": str(manifest_path),
        "items": normalized_items,
        "summary": {
            "item_count": len(normalized_items),
            "valid_item_count": valid_item_count,
            "missing_path_count": len(missing_paths),
        },
        "missing_paths": missing_paths,
    }


def external_entries_for_item(item: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    test_id = str(item.get("test_id") or "")
    surface_name = str(item.get("surface_name") or "")
    surface_slug = str(item.get("surface_slug") or "")
    acceptance_type = str(item.get("acceptance_type") or "")
    for entry in ensure_list(manifest.get("items")):
        acceptance_types = [str(value) for value in ensure_list(entry.get("acceptance_types"))]
        if acceptance_types and acceptance_type not in acceptance_types:
            continue
        if entry.get("test_id") and str(entry.get("test_id")) == test_id:
            matched.append(entry)
            continue
        if surface_name and str(entry.get("surface_name") or "") == surface_name:
            matched.append(entry)
            continue
        if surface_slug and str(entry.get("surface_slug") or "") == surface_slug:
            matched.append(entry)
    return matched


def evaluate_external_review(item: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    entries = external_entries_for_item(item, manifest)
    evidence_paths = dedupe_preserve_order(
        path for entry in entries for path in ensure_list(entry.get("evidence_paths"))
    )
    reviewers = dedupe_preserve_order(
        str(entry.get("reviewer")) for entry in entries if str(entry.get("reviewer") or "").strip()
    )
    notes = [str(entry.get("note") or "").strip() for entry in entries if str(entry.get("note") or "").strip()]
    explicit_fail = any(str(entry.get("status") or "") == "fail" for entry in entries)
    explicit_pass = any(str(entry.get("status") or "") == "pass" for entry in entries)
    manual_record_present = any(
        str(entry.get("evidence_type") or "") == "manual-review-note"
        and str(entry.get("reviewer") or "").strip()
        and str(entry.get("note") or "").strip()
        for entry in entries
    )
    signed_off = any(
        str(entry.get("status") or "") == "pass" and bool(entry.get("signoff")) and str(entry.get("reviewer") or "").strip()
        for entry in entries
    )
    route_observations = [
        {
            "requested_route": str(entry.get("requested_route") or "").strip(),
            "final_route": str(entry.get("final_route") or "").strip(),
            "route_landing_status": str(entry.get("route_landing_status") or "").strip().lower(),
            "auth_entry_route": str(entry.get("auth_entry_route") or "").strip(),
            "note": str(entry.get("note") or "").strip(),
            "reviewer": str(entry.get("reviewer") or "").strip(),
        }
        for entry in entries
        if any(
            str(entry.get(key) or "").strip()
            for key in ("requested_route", "final_route", "route_landing_status", "auth_entry_route")
        )
    ]
    route_mismatch_observations = [
        observation
        for observation in route_observations
        if observation["route_landing_status"] == "route-mismatch"
        or (
            observation["requested_route"]
            and observation["final_route"]
            and observation["requested_route"] != observation["final_route"]
            and observation["route_landing_status"] != "auth-redirect"
        )
    ]
    auth_redirect_observations = [
        observation for observation in route_observations if observation["route_landing_status"] == "auth-redirect"
    ]
    return {
        "entries": entries,
        "evidence_paths": evidence_paths,
        "reviewers": reviewers,
        "notes": notes,
        "explicit_fail": explicit_fail,
        "explicit_pass": explicit_pass,
        "manual_record_present": manual_record_present,
        "signed_off": signed_off,
        "manifest_path": str(manifest.get("manifest_path") or ""),
        "route_observations": route_observations,
        "route_mismatch_observations": route_mismatch_observations,
        "auth_redirect_observations": auth_redirect_observations,
    }


def load_json_if_exists(path: Path) -> dict[str, Any]:
    return load_json(path) if path.exists() else {}


def load_retained_stage2_test_evidence(stage02_dir: Path) -> dict[str, dict[str, Any]]:
    evidence_index = load_json_if_exists(stage02_dir / "test-evidence-index.json")
    retained_test_evidence = evidence_index.get("test_evidence", {}) if isinstance(evidence_index, dict) else {}
    if not isinstance(retained_test_evidence, dict):
        return {}
    return {
        str(test_id): dict(bucket)
        for test_id, bucket in retained_test_evidence.items()
        if isinstance(bucket, dict) and str(test_id).strip()
    }


def route_from_implementation_target(target: str) -> str:
    path = Path(str(target))
    parts = list(path.parts)
    if "app" not in parts:
        return ""
    app_index = parts.index("app")
    route_parts = parts[app_index + 1 : -1]
    if not route_parts:
        return "/"
    return "/" + "/".join(route_parts)


def executable_source_text(text: str) -> str:
    without_block_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    without_line_comments = re.sub(r"(^|[^:])//.*$", r"\1", without_block_comments, flags=re.MULTILINE)
    return without_line_comments


def _clean_route_token(value: Any) -> str:
    route = str(value or "").strip().strip("`'\"")
    route = route.rstrip(".,);]")
    return route if route.startswith("/") else ""


def _route_observation_from_note(note: str, raw_item: dict[str, Any]) -> dict[str, str]:
    requested_route = _clean_route_token(
        raw_item.get("requested_route") or raw_item.get("target_route") or raw_item.get("expected_route")
    )
    final_route = _clean_route_token(
        raw_item.get("final_route") or raw_item.get("observed_route") or raw_item.get("landed_route")
    )
    auth_entry_route = _clean_route_token(raw_item.get("auth_entry_route") or raw_item.get("auth_redirect_route"))
    route_landing_status = str(raw_item.get("route_landing_status") or raw_item.get("navigation_status") or "").strip().lower()
    note_text = str(note or "").strip()
    if note_text:
        stayed_match = re.search(
            r"Navigating to\s+(?P<requested>/\S+)\s+stayed on\s+(?P<final>/\S+)",
            note_text,
            re.IGNORECASE,
        )
        redirected_match = re.search(
            r"Navigating to\s+(?P<requested>/\S+)\s+(?:redirected|landed)\s+(?:to\s+)?(?P<final>/\S+)",
            note_text,
            re.IGNORECASE,
        )
        reached_match = re.search(r"(?:reached|landed on)\s+(?P<route>/\S+)", note_text, re.IGNORECASE)
        if stayed_match:
            requested_route = requested_route or _clean_route_token(stayed_match.group("requested"))
            final_route = final_route or _clean_route_token(stayed_match.group("final"))
            route_landing_status = route_landing_status or "route-mismatch"
        elif redirected_match:
            requested_route = requested_route or _clean_route_token(redirected_match.group("requested"))
            final_route = final_route or _clean_route_token(redirected_match.group("final"))
            if not auth_entry_route and (
                "/auth/" in final_route or final_route.endswith("/login") or "login" in note_text.lower()
            ):
                auth_entry_route = final_route
            if not route_landing_status:
                route_landing_status = "auth-redirect" if auth_entry_route and final_route == auth_entry_route else "redirected"
        elif reached_match:
            final_route = final_route or _clean_route_token(reached_match.group("route"))
            requested_route = requested_route or final_route
            route_landing_status = route_landing_status or "matched"

    if not route_landing_status:
        if requested_route and final_route:
            if requested_route == final_route:
                route_landing_status = "matched"
            elif auth_entry_route and final_route == auth_entry_route:
                route_landing_status = "auth-redirect"
            else:
                route_landing_status = "route-mismatch"
        elif final_route:
            route_landing_status = "matched"

    if route_landing_status == "auth-redirect" and not auth_entry_route:
        auth_entry_route = final_route

    return {
        "requested_route": requested_route,
        "final_route": final_route,
        "route_landing_status": route_landing_status,
        "auth_entry_route": auth_entry_route,
    }


def _format_route_observation_message(observation: dict[str, str]) -> str:
    requested_route = str(observation.get("requested_route") or "").strip()
    final_route = str(observation.get("final_route") or observation.get("auth_entry_route") or "").strip()
    route_landing_status = str(observation.get("route_landing_status") or "").strip().lower()
    if route_landing_status == "auth-redirect" and requested_route and final_route:
        return f"Browser evidence confirmed missing-session auth redirect from `{requested_route}` to `{final_route}`."
    if requested_route and final_route and requested_route != final_route:
        return f"Browser evidence showed route landing mismatch: requested `{requested_route}` but landed on `{final_route}`."
    if final_route:
        return f"Browser evidence confirmed the surface landed on `{final_route}`."
    return "Browser evidence reported a navigation outcome for this surface."


def _pascal_case(value: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", value) if part]
    if not parts:
        return ""
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _camel_case(value: str) -> str:
    pascal = _pascal_case(value)
    return pascal[:1].lower() + pascal[1:] if pascal else ""


def binding_method_candidates(compiled_interactions: list[dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for interaction in compiled_interactions:
        binding_id = str(interaction.get("service_binding_id") or "").strip()
        suffix = binding_id.rsplit(".", 1)[-1].strip() if binding_id else ""
        for candidate in (
            suffix,
            _camel_case(suffix),
            _pascal_case(suffix),
        ):
            normalized = str(candidate).strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)
    return candidates


def api_binding_usage_present(
    *,
    executable_text: str,
    expected_api_ids: list[str],
    expected_api_paths: list[str],
    compiled_interactions: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    discovered_api_ids = [
        api_id_for_operation(operation_id)
        for operation_id in extract_operation_ids_from_text(executable_text)
    ]
    if expected_api_ids and all(api_id in discovered_api_ids for api_id in expected_api_ids):
        evidence.append("operation-id-reference")

    call_like_pattern = re.compile(r"\b(?:callApi|fetch)\s*\(|\.\s*request\s*\(", re.MULTILINE)
    if call_like_pattern.search(executable_text):
        evidence.append("request-call")

    method_candidates = binding_method_candidates(compiled_interactions)
    if any(
        re.search(rf"(?:\bawait\s+)?(?:[A-Za-z_][A-Za-z0-9_]*\.)?{re.escape(candidate)}\s*\(", executable_text)
        for candidate in method_candidates
    ):
        evidence.append("generated-client-call")

    if expected_api_paths and any(path in executable_text for path in expected_api_paths):
        evidence.append("api-path-reference")

    return bool(evidence), evidence


def navigation_targets_from_text(executable_text: str) -> list[str]:
    patterns = (
        r'href\s*=\s*["\']([^"\']+)["\']',
        r'to\s*=\s*["\']([^"\']+)["\']',
        r'router\.(?:push|replace)\(\s*["\']([^"\']+)["\']',
        r'navigate\(\s*["\']([^"\']+)["\']',
        r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
        r'next_route\s*:\s*["\']([^"\']+)["\']',
        r'failure_route\s*:\s*["\']([^"\']+)["\']',
    )
    targets: list[str] = []
    for pattern in patterns:
        targets.extend(
            route.strip()
            for route in re.findall(pattern, executable_text)
            if str(route).strip().startswith("/")
        )
    return dedupe_preserve_order(targets)


def load_phase3_runtime_truth_summary(phase3_root: Path) -> dict[str, Any]:
    delivery_gate = load_json_if_exists(phase3_root / "phase3-delivery-gate.json")
    mainline_summary = load_phase3_mainline_summary(phase3_root)
    code_review = load_json_if_exists(phase3_root / "code-review-metrics.json")
    mock_manifest = load_json_if_exists(phase3_root / "mock-dependency-manifest.json")
    verification_ledger = load_json_if_exists(phase3_root / "phase3-verification-ledger.json")
    runtime_smoke = load_json_if_exists(phase3_root / "runtime-smoke-report.json")
    started_service_smoke = load_json_if_exists(phase3_root / "started-service-smoke-report.json")
    checks = delivery_gate.get("checks", {}) if isinstance(delivery_gate, dict) else {}
    ledger_backend_truth = (
        verification_ledger.get("aggregated", {}).get("backend_truth", {})
        if isinstance(verification_ledger.get("aggregated"), dict)
        else {}
    )
    full_targeted_report_paths = sorted(
        phase3_root.glob(".phase3-mainline-execution/backend-runs/**/full-test-report.json")
    )
    mainline_backend_report_paths = sorted(
        [
            *phase3_root.glob(".phase3-mainline-execution/backend-runs/**/verification-report.json"),
            *phase3_root.glob(".phase3-mainline-execution/backend-runs/**/test-report.json"),
        ]
    )
    full_targeted_failed_tests: list[str] = []
    full_targeted_passed_tests: list[str] = []
    full_targeted_verdicts: list[str] = []
    for report_path in full_targeted_report_paths:
        report = load_json_if_exists(report_path)
        if not isinstance(report, dict):
            continue
        full_targeted_verdicts.append(str(report.get("verdict") or "").strip().lower())
        full_targeted_passed_tests.extend(
            str(item).strip()
            for item in ensure_list(report.get("passed_tests") or report.get("observed_passed_tests"))
            if str(item).strip()
        )
        full_targeted_failed_tests.extend(
            str(item).strip()
            for item in ensure_list(
                report.get("failed_tests") or report.get("observed_failed_tests") or report.get("missing_expected_tests")
            )
            if str(item).strip()
        )
    full_targeted_evidence_present = bool(full_targeted_report_paths)
    if not full_targeted_evidence_present:
        full_targeted_evidence_status = "missing"
    elif full_targeted_failed_tests or any(verdict == "fail" for verdict in full_targeted_verdicts):
        full_targeted_evidence_status = "fail"
    elif full_targeted_passed_tests or any(verdict == "pass" for verdict in full_targeted_verdicts):
        full_targeted_evidence_status = "pass"
    else:
        full_targeted_evidence_status = "unknown"
    delivery_state = str(
        mainline_summary.get("recommended_formal_state") or delivery_gate.get("recommended_formal_state") or ""
    ).strip().lower()
    delivery_green_default = delivery_state == "delivery-ready"
    full_targeted_report_refs = [relative_to_root(path, phase3_root) for path in full_targeted_report_paths]
    mock_dependency_count = int(
        (code_review.get("summary", {}) if isinstance(code_review, dict) else {}).get("mock_runtime_dependency_count", 0)
        or len(ensure_list(mock_manifest.get("items")))
    )
    return {
        "delivery_gate_present": bool(delivery_gate),
        "delivery_gate_path": relative_to_root(phase3_root / "phase3-delivery-gate.json", phase3_root),
        "code_review_path": relative_to_root(phase3_root / "code-review-metrics.json", phase3_root),
        "mock_manifest_path": relative_to_root(phase3_root / "mock-dependency-manifest.json", phase3_root),
        "mainline_summary_present": bool(mainline_summary.get("present")),
        "mainline_summary_source": str(mainline_summary.get("source") or ""),
        "phase_verdict": str(mainline_summary.get("phase_verdict") or ""),
        "phase_total_score": mainline_summary.get("phase_total_score"),
        "phase_verdict_path": str(mainline_summary.get("phase_verdict_path") or ""),
        "phase_scorecard_path": str(mainline_summary.get("phase_scorecard_path") or ""),
        "phase_acceptance_matrix_path": str(mainline_summary.get("phase_acceptance_matrix_path") or ""),
        "mainline_backend_verification_present": bool(mainline_backend_report_paths),
        "mainline_backend_verification_report_paths": [
            relative_to_root(path, phase3_root) for path in mainline_backend_report_paths
        ],
        "full_targeted_evidence_present": full_targeted_evidence_present,
        "full_targeted_evidence_status": full_targeted_evidence_status,
        "full_targeted_report_paths": full_targeted_report_refs,
        "full_targeted_failed_tests": dedupe_preserve_order(full_targeted_failed_tests),
        "full_targeted_passed_test_count": len(dedupe_preserve_order(full_targeted_passed_tests)),
        "verification_ledger_path": relative_to_root(phase3_root / "phase3-verification-ledger.json", phase3_root),
        "runtime_smoke_path": relative_to_root(phase3_root / "runtime-smoke-report.json", phase3_root),
        "started_service_smoke_path": relative_to_root(phase3_root / "started-service-smoke-report.json", phase3_root),
        "evidence_paths": [
            path
            for path, exists in [
                *[(path, True) for path in full_targeted_report_refs],
                (relative_to_root(phase3_root / "phase3-delivery-gate.json", phase3_root), bool(delivery_gate)),
                (relative_to_root(phase3_root / "phase3-verification-ledger.json", phase3_root), bool(verification_ledger)),
                (relative_to_root(phase3_root / "runtime-smoke-report.json", phase3_root), bool(runtime_smoke)),
                (relative_to_root(phase3_root / "started-service-smoke-report.json", phase3_root), bool(started_service_smoke)),
                (relative_to_root(phase3_root / "code-review-metrics.json", phase3_root), bool(code_review)),
                (relative_to_root(phase3_root / "mock-dependency-manifest.json", phase3_root), bool(mock_manifest)),
            ]
            if exists
        ],
        "mock_dependency_count": mock_dependency_count,
        "mock_dependency_present": mock_dependency_count > 0,
        "backend_interface_gate": bool(checks.get("backend_interface_gate", delivery_green_default)),
        "backend_persistence_truth_required": bool(checks.get("backend_persistence_truth_required")),
        "backend_persistence_gate": bool(
            checks.get(
                "backend_persistence_gate",
                ledger_backend_truth.get("sql_persistence_truth_packet_count", 0) > 0 or delivery_green_default,
            )
        ),
        "backend_migration_gate": bool(
            checks.get(
                "backend_migration_gate",
                ledger_backend_truth.get("migration_execution_packet_count", 0) > 0 or delivery_green_default,
            )
        ),
        "runtime_smoke_green": bool(
            checks.get("runtime_smoke_green")
            or str(runtime_smoke.get("overall_quality_gate") or runtime_smoke.get("verdict") or "").lower() == "pass"
        ),
        "started_service_smoke_green": bool(
            checks.get("started_service_smoke_green")
            or str(started_service_smoke.get("overall_quality_gate") or started_service_smoke.get("verdict") or "").lower()
            == "pass"
        ),
    }


def flatten_packet_test_targets(packet: dict[str, Any]) -> list[str]:
    targets = packet.get("test_targets")
    if isinstance(targets, dict):
        flattened: list[str] = []
        for value in targets.values():
            flattened.extend(str(item) for item in ensure_list(value) if str(item).strip())
        return dedupe_preserve_order(flattened)
    return dedupe_preserve_order(str(item) for item in ensure_list(targets) if str(item).strip())


def build_worker_packet_context(worker_packets: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, list[str]]]]:
    context: dict[str, dict[str, dict[str, list[str]]]] = {
        "backend": {
            "source_to_packets": {},
            "api_to_packets": {},
            "test_target_to_packets": {},
        },
        "frontend": {
            "surface_to_packets": {},
            "implementation_target_to_packets": {},
            "test_target_to_packets": {},
        },
    }
    for packet in worker_packets:
        lane = str(packet.get("lane") or "").strip().lower()
        packet_id = str(packet.get("packet_id") or "").strip()
        if lane not in context or not packet_id:
            continue
        if lane == "backend":
            for source_row in ensure_list(packet.get("source_rows")):
                source_id = str((source_row or {}).get("source_id") or "").strip()
                if source_id:
                    current = context["backend"]["source_to_packets"].setdefault(source_id, [])
                    context["backend"]["source_to_packets"][source_id] = dedupe_preserve_order([*current, packet_id])
            for operation in ensure_list(packet.get("contract_operations")):
                operation_id = str((operation or {}).get("operation_id") or "").strip()
                if operation_id:
                    api_id = api_id_for_operation(operation_id)
                    current = context["backend"]["api_to_packets"].setdefault(api_id, [])
                    context["backend"]["api_to_packets"][api_id] = dedupe_preserve_order([*current, packet_id])
        if lane == "frontend":
            for surface_name in ensure_list(packet.get("frontend_surfaces")):
                normalized = str(surface_name).strip()
                if normalized:
                    current = context["frontend"]["surface_to_packets"].setdefault(normalized, [])
                    context["frontend"]["surface_to_packets"][normalized] = dedupe_preserve_order([*current, packet_id])
            for target in ensure_list(packet.get("implementation_targets")):
                normalized = str(target).strip()
                if normalized:
                    current = context["frontend"]["implementation_target_to_packets"].setdefault(normalized, [])
                    context["frontend"]["implementation_target_to_packets"][normalized] = dedupe_preserve_order(
                        [*current, packet_id]
                    )
        for target in flatten_packet_test_targets(packet):
            current = context[lane]["test_target_to_packets"].setdefault(target, [])
            context[lane]["test_target_to_packets"][target] = dedupe_preserve_order([*current, packet_id])
    return context


def runtime_environment_context_for_item(
    item: dict[str, Any],
    packet_context: dict[str, dict[str, dict[str, list[str]]]],
    runtime_environment: dict[str, Any],
) -> dict[str, Any]:
    acceptance_type = str(item.get("acceptance_type") or "")
    target_lane = "frontend" if acceptance_type in {"ui-review", "visual-evidence"} else "backend"
    lane_context = packet_context.get(target_lane, {})
    candidate_packet_ids: list[str] = []

    if target_lane == "backend":
        source_id = str(item.get("source_id") or "").strip()
        if source_id:
            candidate_packet_ids.extend(lane_context.get("source_to_packets", {}).get(source_id, []))
        for api_id in ensure_list(item.get("related_api_ids")):
            candidate_packet_ids.extend(lane_context.get("api_to_packets", {}).get(str(api_id), []))
        for test_target in ensure_list(item.get("test_targets")):
            candidate_packet_ids.extend(lane_context.get("test_target_to_packets", {}).get(str(test_target), []))
    else:
        surface_name = str(item.get("surface_name") or "").strip()
        if surface_name:
            candidate_packet_ids.extend(lane_context.get("surface_to_packets", {}).get(surface_name, []))
        for target in ensure_list(item.get("implementation_targets")):
            candidate_packet_ids.extend(
                lane_context.get("implementation_target_to_packets", {}).get(str(target), [])
            )
        for test_target in ensure_list(item.get("test_targets")):
            candidate_packet_ids.extend(lane_context.get("test_target_to_packets", {}).get(str(test_target), []))

    candidate_packet_ids = dedupe_preserve_order(packet_id for packet_id in candidate_packet_ids if packet_id)
    rows_by_packet = runtime_environment.get("rows_by_packet", {})
    matched_rows = [rows_by_packet[packet_id] for packet_id in candidate_packet_ids if packet_id in rows_by_packet]
    lane_summary = runtime_environment.get("lanes", {}).get(target_lane, {})
    if not runtime_environment.get("present"):
        status = "unknown"
    elif matched_rows:
        status = (
            "available"
            if all(str(row.get("current_availability") or "").strip().lower() == "available" for row in matched_rows)
            else "missing"
        )
    elif lane_summary:
        status = "available" if lane_summary.get("all_runtime_available") else "missing"
    else:
        status = "unknown"

    required_runtime_environments = dedupe_preserve_order(
        [
            *[
                str(row.get("required_runtime_environment") or "").strip()
                for row in matched_rows
                if str(row.get("required_runtime_environment") or "").strip()
            ],
            *[str(value) for value in ensure_list(lane_summary.get("required_runtime_environments")) if str(value).strip()],
        ]
    )
    blocked_capabilities = dedupe_preserve_order(
        [
            *[
                str(value)
                for row in matched_rows
                if str(row.get("current_availability") or "").strip().lower() != "available"
                for value in ensure_list(row.get("blocked_capabilities"))
                if str(value).strip()
            ],
            *[str(value) for value in ensure_list(lane_summary.get("blocked_capabilities")) if str(value).strip()],
        ]
    )
    return {
        "status": status,
        "target_lane": target_lane,
        "matched_packet_ids": candidate_packet_ids,
        "required_runtime_environments": required_runtime_environments,
        "blocked_capabilities": blocked_capabilities,
        "evidence_paths": [runtime_environment.get("path", "")] if runtime_environment.get("path") else [],
    }


def match_visual_assets(item: dict[str, Any], visual_assets: list[str]) -> list[str]:
    tokens = [compact_token(str(item.get("surface_name") or "")), compact_token(str(item.get("test_id") or ""))]
    for target in ensure_list(item.get("implementation_targets")):
        target_path = Path(str(target))
        tokens.append(compact_token(target_path.stem))
        tokens.append(compact_token(target_path.parent.name))
    tokens = [token for token in dedupe_preserve_order(tokens) if token]
    matches = [asset for asset in visual_assets if any(token and token in compact_token(asset) for token in tokens)]
    return dedupe_preserve_order(matches)


def functional_status(
    item: dict[str, Any],
    test_evidence: dict[str, dict[str, Any]],
    runtime_truth: dict[str, Any],
    runtime_environment: dict[str, Any],
) -> dict[str, Any]:
    targets = [str(target) for target in ensure_list(item.get("test_targets"))]
    if not targets:
        return {
            "status": "blocked",
            "actual_result": "No linked automated test targets were available for this mandatory functional item.",
            "evidence_paths": [],
            "human_signoff_status": "not-required",
            "signoff_evidence_paths": [],
            "reviewers": [],
            "external_evidence_refs": [],
        }
    target_rows = [test_evidence.get(target, {"verdict": "not-run", "report_paths": []}) for target in targets]
    verdicts = [str(row.get("verdict") or "not-run") for row in target_rows]
    evidence_paths = dedupe_preserve_order(
        report_path for row in target_rows for report_path in ensure_list(row.get("report_paths"))
    )
    pass_count = verdicts.count("pass")
    fail_count = verdicts.count("fail")
    if fail_count > 0:
        status = "fail"
        actual_result = f"{pass_count}/{len(targets)} linked tests passed; {fail_count} failed."
    elif pass_count == len(targets):
        evidence_paths = dedupe_preserve_order(
            [
                *evidence_paths,
                *runtime_truth.get("evidence_paths", []),
                runtime_truth.get("delivery_gate_path", ""),
                runtime_truth.get("code_review_path", ""),
                runtime_truth.get("mock_manifest_path", ""),
                *runtime_environment.get("evidence_paths", []),
            ]
        )
        if item.get("related_api_ids") and not runtime_truth.get("backend_interface_gate", True):
            status = "blocked"
            actual_result = "Linked tests passed, but Phase-3 backend service-boundary truth is not green."
        elif (
            item.get("related_api_ids")
            and runtime_truth.get("backend_persistence_truth_required")
            and (
                not runtime_truth.get("backend_persistence_gate", False)
                or not runtime_truth.get("backend_migration_gate", False)
            )
        ):
            status = "blocked"
            actual_result = "Linked tests passed, but Phase-3 persistence or migration truth is still incomplete."
        else:
            conditional_reasons: list[str] = []
            if runtime_environment.get("status") == "missing":
                required_runtime = ", ".join(
                    str(value) for value in ensure_list(runtime_environment.get("required_runtime_environments"))
                )
                conditional_reasons.append(
                    f"the runtime-environment ledger still marks `{required_runtime or 'target-runtime-environment'}` as missing for this lane"
                )
            if item.get("related_api_ids") and runtime_truth.get("mock_dependency_present"):
                conditional_reasons.append("Phase-3 runtime truth still reports mock dependency in core paths")
            if conditional_reasons:
                status = "conditional-pass"
                actual_result = f"All {len(targets)} linked tests passed, but " + " and ".join(conditional_reasons) + "."
            else:
                status = "pass"
                actual_result = f"All {len(targets)} linked tests passed."
    else:
        status = "blocked"
        actual_result = f"{pass_count}/{len(targets)} linked tests passed; at least one linked target has no recorded evidence."
    return {
        "status": status,
        "actual_result": actual_result,
        "evidence_paths": evidence_paths,
        "human_signoff_status": "not-required",
        "signoff_evidence_paths": [],
        "reviewers": [],
        "external_evidence_refs": [],
    }


def data_fidelity_status(
    item: dict[str, Any],
    runtime_truth: dict[str, Any],
    runtime_environment: dict[str, Any],
) -> dict[str, Any]:
    evidence_paths = [
        path
        for path in (
            *runtime_truth.get("evidence_paths", []),
            runtime_truth.get("delivery_gate_path", ""),
            runtime_truth.get("code_review_path", ""),
            runtime_truth.get("mock_manifest_path", ""),
            *runtime_environment.get("evidence_paths", []),
        )
        if path
    ]
    if not runtime_truth.get("backend_interface_gate", False):
        return {
            "status": "blocked",
            "actual_result": "Phase-3 backend service-boundary truth is not green.",
            "evidence_paths": evidence_paths,
            "human_signoff_status": "not-required",
            "signoff_evidence_paths": [],
            "reviewers": [],
            "external_evidence_refs": [],
        }
    if runtime_truth.get("backend_persistence_truth_required") and not runtime_truth.get("backend_persistence_gate", False):
        return {
            "status": "blocked",
            "actual_result": "Phase-3 persistence truth is not green for a database-backed slice.",
            "evidence_paths": evidence_paths,
            "human_signoff_status": "not-required",
            "signoff_evidence_paths": [],
            "reviewers": [],
            "external_evidence_refs": [],
        }
    if runtime_truth.get("backend_persistence_truth_required") and not runtime_truth.get("backend_migration_gate", False):
        return {
            "status": "blocked",
            "actual_result": "Phase-3 migration execution truth is not green for a database-backed slice.",
            "evidence_paths": evidence_paths,
            "human_signoff_status": "not-required",
            "signoff_evidence_paths": [],
            "reviewers": [],
            "external_evidence_refs": [],
        }
    conditional_reasons: list[str] = []
    if runtime_environment.get("status") == "missing":
        required_runtime = ", ".join(
            str(value) for value in ensure_list(runtime_environment.get("required_runtime_environments"))
        )
        conditional_reasons.append(
            f"the runtime-environment ledger still marks `{required_runtime or 'target-runtime-environment'}` as missing for this lane"
        )
    if runtime_truth.get("mock_dependency_present"):
        conditional_reasons.append("Phase-3 runtime truth still reports mock dependency in core execution paths")
    if conditional_reasons:
        return {
            "status": "conditional-pass",
            "actual_result": "Phase-3 runtime truth is only conditionally acceptable because " + " and ".join(conditional_reasons) + ".",
            "evidence_paths": evidence_paths,
            "human_signoff_status": "not-required",
            "signoff_evidence_paths": [],
            "reviewers": [],
            "external_evidence_refs": [],
        }
    return {
        "status": "pass",
        "actual_result": "Phase-3 runtime truth proves real service-boundary and persistence behavior for this slice.",
        "evidence_paths": evidence_paths,
        "human_signoff_status": "not-required",
        "signoff_evidence_paths": [],
        "reviewers": [],
        "external_evidence_refs": [],
    }


def audit_frontend_surface(item: dict[str, Any], phase3_root: Path, ui_ia_contract: dict[str, Any]) -> dict[str, Any]:
    page_paths = [str(path) for path in ensure_list(item.get("implementation_targets"))]
    expected_api_ids = [str(api_id) for api_id in ensure_list(item.get("related_api_ids"))]
    contract_pages_by_route = {
        str(page.get("route") or "").strip(): page
        for page in ensure_list(ui_ia_contract.get("pages"))
        if isinstance(page, dict) and str(page.get("route") or "").strip()
    }
    frontend_experience_contract = ui_ia_contract.get("frontend_experience_contract")
    if not isinstance(frontend_experience_contract, dict):
        app_context = ui_ia_contract.get("app_context")
        if isinstance(app_context, dict) and isinstance(app_context.get("frontend_experience_contract"), dict):
            frontend_experience_contract = app_context.get("frontend_experience_contract")
        else:
            frontend_experience_contract = {}
    browser_review_checklist = [
        row for row in ensure_list(frontend_experience_contract.get("browser_audit_checklist"))
        if isinstance(row, dict)
    ]
    browser_review_dimensions = dedupe_preserve_order(
        [
            str(row.get("dimension") or "").strip()
            for row in browser_review_checklist
            if str(row.get("dimension") or "").strip()
        ]
    )
    browser_review_bad_patterns = dedupe_preserve_order(
        [
            str(pattern).strip()
            for row in browser_review_checklist
            for pattern in ensure_list(row.get("bad_patterns"))
            if str(pattern).strip()
        ]
    )
    expected_browser_dimensions = ["audience-boundary", "handoff-exposure", "field-semantics", "nav-posture"]
    contract_pages_by_id = {
        str(page.get("page_id") or "").strip(): page
        for page in ensure_list(ui_ia_contract.get("pages"))
        if isinstance(page, dict) and str(page.get("page_id") or "").strip()
    }
    legacy_demo_tokens = (
        "What This Screen Does",
        "Action Panel",
        "Runtime Result",
        "Flow Guidance",
        "Operational entrypoint",
        "Frozen IA routes",
        "Primary action:",
    )
    page_rows: list[dict[str, Any]] = []
    for page_path in page_paths:
        absolute_path = phase3_root / page_path
        exists = absolute_path.exists()
        text = absolute_path.read_text(encoding="utf-8") if exists else ""
        executable_text = executable_source_text(text)
        route = route_from_implementation_target(page_path)
        contract_page = contract_pages_by_route.get(route, {})
        compiled_interactions = [
            row for row in ensure_list(contract_page.get("compiled_interactions")) if isinstance(row, dict)
        ]
        expected_route = str(contract_page.get("route") or route).strip()
        expected_blueprint = str(contract_page.get("page_blueprint_type") or "").strip()
        expected_roles = [str(role).strip() for role in ensure_list(contract_page.get("allowed_roles")) if str(role).strip()]
        expected_regions = [
            str(region).strip() for region in ensure_list(contract_page.get("required_regions")) if str(region).strip()
        ]
        expected_interaction_ids = [
            str(row.get("interaction_id") or "").strip() for row in compiled_interactions if str(row.get("interaction_id") or "").strip()
        ]
        expected_service_binding_ids = [
            str(row.get("service_binding_id") or "").strip()
            for row in compiled_interactions
            if str(row.get("service_binding_id") or "").strip()
        ]
        expected_api_paths = [
            str(row.get("api_endpoint") or "").strip()
            for row in compiled_interactions
            if str(row.get("api_endpoint") or "").strip()
        ]
        expected_navigation_targets = dedupe_preserve_order(
            [
                *[
                    str(row.get("next_route") or "").strip()
                    for row in compiled_interactions
                    if str(row.get("next_route") or "").strip().startswith("/")
                ],
                *[
                    str((contract_pages_by_id.get(str(row.get("next_page_id") or "").strip(), {}) or {}).get("route") or "").strip()
                    for row in compiled_interactions
                    if str((contract_pages_by_id.get(str(row.get("next_page_id") or "").strip(), {}) or {}).get("route") or "").strip().startswith("/")
                ],
                *[
                    str(row.get("failure_route") or "").strip()
                    for row in compiled_interactions
                    if str(row.get("failure_route") or "").strip().startswith("/")
                ],
            ]
        )
        discovered_api_ids = [api_id_for_operation(operation_id) for operation_id in extract_operation_ids_from_file(absolute_path)]
        api_binding_present, api_binding_evidence = api_binding_usage_present(
            executable_text=executable_text,
            expected_api_ids=expected_api_ids,
            expected_api_paths=expected_api_paths,
            compiled_interactions=compiled_interactions,
        )
        discovered_navigation_targets = navigation_targets_from_text(executable_text)
        flow_binding_present = (
            not expected_navigation_targets
            or bool(set(expected_navigation_targets) & set(discovered_navigation_targets))
            or all(target in executable_text for target in expected_navigation_targets)
        )
        checks = {
            "file_exists": exists,
            "contract_page_present": bool(contract_page),
            "main_shell_present": "<main" in executable_text,
            "surface_marker_present": (
                f'data-phase3-surface="{expected_route}"' in executable_text
                if expected_route
                else "data-phase3-surface=" in executable_text
            ),
            "surface_role_present": "data-phase3-role=" in executable_text,
            "blueprint_present": (not expected_blueprint) or expected_blueprint in executable_text,
            "allowed_roles_present": all(role in executable_text for role in expected_roles),
            "required_regions_present": all(region in executable_text for region in expected_regions),
            "compiled_interactions_present": bool(compiled_interactions) and api_binding_present,
            "service_bindings_present": bool(expected_service_binding_ids) and api_binding_present,
            "flow_markers_present": flow_binding_present,
            "api_binding_usage_present": api_binding_present,
            "legacy_demo_shell_absent": not any(token in executable_text for token in legacy_demo_tokens),
            "api_mentions_present": (not expected_api_ids) or all(api_id in discovered_api_ids for api_id in expected_api_ids) or api_binding_present,
        }
        gating_keys = (
            "file_exists",
            "contract_page_present",
            "main_shell_present",
            "surface_marker_present",
            "surface_role_present",
            "blueprint_present",
            "allowed_roles_present",
            "required_regions_present",
            "compiled_interactions_present",
            "service_bindings_present",
            "flow_markers_present",
            "api_mentions_present",
            "legacy_demo_shell_absent",
        )
        page_rows.append(
            {
                "page_path": page_path,
                "route": expected_route or route,
                "contract_page_id": str(contract_page.get("page_id") or "").strip(),
                "discovered_api_ids": discovered_api_ids,
                "api_binding_evidence": api_binding_evidence,
                "discovered_navigation_targets": discovered_navigation_targets,
                "expected_navigation_targets": expected_navigation_targets,
                "checks": checks,
                "all_checks_pass": all(checks[key] for key in gating_keys),
            }
        )

    return {
        "surface_name": item.get("surface_name"),
        "ui_review_test_id": f"TEST-UI-{item.get('surface_slug')}",
        "visual_evidence_test_id": f"TEST-VISUAL-{item.get('surface_slug')}",
        "browser_review_checklist": browser_review_checklist,
        "browser_review_dimensions": browser_review_dimensions,
        "browser_review_bad_patterns": browser_review_bad_patterns,
        "browser_review_dimension_coverage": {
            "covered": browser_review_dimensions,
            "missing": [dimension for dimension in expected_browser_dimensions if dimension not in browser_review_dimensions],
        },
        "page_rows": page_rows,
        "all_checks_pass": bool(page_rows) and all(row["all_checks_pass"] for row in page_rows),
    }


def review_status(
    item: dict[str, Any],
    phase3_root: Path,
    test_evidence: dict[str, dict[str, Any]],
    visual_assets: list[str],
    surface_audits: dict[str, dict[str, Any]],
    external_manifest: dict[str, Any],
    runtime_environment: dict[str, Any],
) -> dict[str, Any]:
    page_paths = [str(path) for path in ensure_list(item.get("implementation_targets"))]
    existing_pages = [path for path in page_paths if (phase3_root / path).exists()]
    linked_test_targets = [str(target) for target in ensure_list(item.get("test_targets"))]
    linked_verdicts = [str((test_evidence.get(target) or {}).get("verdict") or "not-run") for target in linked_test_targets]
    linked_tests_green = bool(linked_verdicts) and all(verdict == "pass" for verdict in linked_verdicts)
    visual_matches = match_visual_assets(item, visual_assets)
    surface_audit = surface_audits.get(str(item.get("surface_name") or ""))
    surface_audit_path = "frontend-surface-audit.json" if surface_audit else ""
    external_review = evaluate_external_review(item, external_manifest)
    human_signoff_required = bool(item.get("human_signoff_required"))
    external_evidence_refs = dedupe_preserve_order(
        [*external_review["evidence_paths"], *( [external_review["manifest_path"]] if external_review["manifest_path"] else [] )]
    )

    def signoff_payload(*, evidence_ready: bool) -> tuple[str, list[str]]:
        if external_review["signed_off"]:
            return "signed-off", external_review["evidence_paths"]
        if not human_signoff_required:
            return "not-required", []
        if not evidence_ready:
            return "not-ready", []
        return "review-bound", []

    if item["acceptance_type"] == "visual-evidence":
        if external_review["route_mismatch_observations"]:
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
            return {
                "status": "fail",
                "actual_result": _format_route_observation_message(external_review["route_mismatch_observations"][0]),
                "evidence_paths": external_review["evidence_paths"] or external_evidence_refs,
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        if external_review["explicit_fail"]:
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
            return {
                "status": "fail",
                "actual_result": "External visual/manual review reported a failure for this surface.",
                "evidence_paths": external_review["evidence_paths"] or external_evidence_refs,
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        if external_review["explicit_pass"] and (external_review["evidence_paths"] or external_review["manual_record_present"]):
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=True)
            note_suffix = f" Reviewed by {', '.join(external_review['reviewers'])}." if external_review["reviewers"] else ""
            actual_result = "External visual/manual evidence was supplied for the target surface."
            if external_review["auth_redirect_observations"]:
                actual_result = _format_route_observation_message(external_review["auth_redirect_observations"][0])
            return {
                "status": "pass",
                "actual_result": actual_result + note_suffix,
                "evidence_paths": external_review["evidence_paths"],
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        if visual_matches:
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=True)
            return {
                "status": "pass",
                "actual_result": "Visual evidence assets were found for the target surface.",
                "evidence_paths": visual_matches,
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        if existing_pages and (linked_tests_green or (surface_audit and surface_audit.get("all_checks_pass"))):
            evidence_paths = dedupe_preserve_order([surface_audit_path, *existing_pages, *runtime_environment.get("evidence_paths", [])])
            if runtime_environment.get("status") == "missing":
                required_runtime = ", ".join(
                    str(value) for value in ensure_list(runtime_environment.get("required_runtime_environments"))
                )
                actual_result = (
                    "No screenshot/video/manual artifact was found and "
                    f"`{required_runtime or 'target-runtime-environment'}` is missing; the gap remains explicit and review-bound."
                )
            elif linked_tests_green:
                actual_result = "No screenshot/video/manual artifact was found; the gap remains explicit and review-bound."
            else:
                actual_result = "Surface structure audit passed, but screenshot/video/manual evidence is still missing; the gap remains explicit and review-bound."
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
            return {
                "status": "review-bound",
                "actual_result": actual_result,
                "evidence_paths": evidence_paths,
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
        return {
            "status": "blocked",
            "actual_result": "The surface has no usable implementation/test basis for visual acceptance.",
            "evidence_paths": dedupe_preserve_order([*existing_pages, *runtime_environment.get("evidence_paths", [])]),
            "human_signoff_status": human_signoff_status,
            "signoff_evidence_paths": signoff_evidence_paths,
            "reviewers": external_review["reviewers"],
            "external_evidence_refs": external_evidence_refs,
        }

    if external_review["route_mismatch_observations"]:
        human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
        return {
            "status": "fail",
            "actual_result": _format_route_observation_message(external_review["route_mismatch_observations"][0]),
            "evidence_paths": external_review["evidence_paths"] or external_evidence_refs,
            "human_signoff_status": human_signoff_status,
            "signoff_evidence_paths": signoff_evidence_paths,
            "reviewers": external_review["reviewers"],
            "external_evidence_refs": external_evidence_refs,
        }
    if external_review["explicit_fail"]:
        human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
        return {
            "status": "fail",
            "actual_result": "External UI/manual review reported a failure for this surface.",
            "evidence_paths": external_review["evidence_paths"] or external_evidence_refs,
            "human_signoff_status": human_signoff_status,
            "signoff_evidence_paths": signoff_evidence_paths,
            "reviewers": external_review["reviewers"],
            "external_evidence_refs": external_evidence_refs,
        }
    if external_review["explicit_pass"] and (external_review["evidence_paths"] or external_review["manual_record_present"]):
        evidence_paths = dedupe_preserve_order([*external_review["evidence_paths"], *existing_pages])
        note_suffix = f" Reviewed by {', '.join(external_review['reviewers'])}." if external_review["reviewers"] else ""
        actual_result = "External UI/manual review passed for the target surface."
        if external_review["auth_redirect_observations"]:
            actual_result = _format_route_observation_message(external_review["auth_redirect_observations"][0])
        human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=True)
        return {
            "status": "pass",
            "actual_result": actual_result + note_suffix,
            "evidence_paths": evidence_paths,
            "human_signoff_status": human_signoff_status,
            "signoff_evidence_paths": signoff_evidence_paths,
            "reviewers": external_review["reviewers"],
            "external_evidence_refs": external_evidence_refs,
        }
    if surface_audit and surface_audit.get("all_checks_pass"):
        evidence_paths = dedupe_preserve_order([surface_audit_path, *existing_pages, *runtime_environment.get("evidence_paths", [])])
        if runtime_environment.get("status") == "missing":
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
            required_runtime = ", ".join(
                str(value) for value in ensure_list(runtime_environment.get("required_runtime_environments"))
            )
            return {
                "status": "review-bound",
                "actual_result": (
                    "Surface structure audit passed, but "
                    f"`{required_runtime or 'target-runtime-environment'}` is missing; runtime UI acceptance stays review-bound."
                ),
                "evidence_paths": evidence_paths,
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        if linked_tests_green:
            human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=True)
            return {
                "status": "pass",
                "actual_result": "Surface structure audit and linked packet verification both passed.",
                "evidence_paths": evidence_paths,
                "human_signoff_status": human_signoff_status,
                "signoff_evidence_paths": signoff_evidence_paths,
                "reviewers": external_review["reviewers"],
                "external_evidence_refs": external_evidence_refs,
            }
        human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
        return {
            "status": "review-bound",
            "actual_result": "Surface structure audit passed, but linked runtime/browser evidence is still incomplete; acceptance remains explicitly review-bound.",
            "evidence_paths": evidence_paths,
            "human_signoff_status": human_signoff_status,
            "signoff_evidence_paths": signoff_evidence_paths,
            "reviewers": external_review["reviewers"],
            "external_evidence_refs": external_evidence_refs,
        }
    if surface_audit and existing_pages and not surface_audit.get("all_checks_pass"):
        evidence_paths = dedupe_preserve_order([surface_audit_path, *existing_pages, *runtime_environment.get("evidence_paths", [])])
        human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
        return {
            "status": "fail",
            "actual_result": "Surface audit found missing required structural markers or contract linkage.",
            "evidence_paths": evidence_paths,
            "human_signoff_status": human_signoff_status,
            "signoff_evidence_paths": signoff_evidence_paths,
            "reviewers": external_review["reviewers"],
            "external_evidence_refs": external_evidence_refs,
        }
    human_signoff_status, signoff_evidence_paths = signoff_payload(evidence_ready=False)
    return {
        "status": "blocked",
        "actual_result": "The surface lacks either a route file, a passing linked evidence set, or a usable surface audit.",
        "evidence_paths": dedupe_preserve_order([*existing_pages, *runtime_environment.get("evidence_paths", [])]),
        "human_signoff_status": human_signoff_status,
        "signoff_evidence_paths": signoff_evidence_paths,
        "reviewers": external_review["reviewers"],
        "external_evidence_refs": external_evidence_refs,
    }


def item_has_residual_review(item: dict[str, Any]) -> bool:
    return item["status"] == "review-bound" or item.get("human_signoff_status") == "review-bound"


def summarize_status_counts(items: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for item in items:
        bucket = summary.setdefault(item["acceptance_type"], {})
        status = str(item.get("status") or "unknown")
        bucket[status] = bucket.get(status, 0) + 1
    overall = summary.setdefault("overall", {})
    for item in items:
        status = str(item.get("status") or "unknown")
        overall[status] = overall.get(status, 0) + 1
    return summary


def build_execution_markdown(
    items: list[dict[str, Any]],
    summary_counts: dict[str, dict[str, int]],
    surface_audits: dict[str, dict[str, Any]],
) -> str:
    status_rows = [
        [acceptance_type, ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))]
        for acceptance_type, counts in summary_counts.items()
    ]
    unresolved = [item for item in items if item["status"] in {"fail", "blocked", "review-bound"} or item_has_residual_review(item)]
    unresolved_rows = [
        [
            item["test_id"],
            item["acceptance_type"],
            item["status"],
            item.get("human_signoff_status", "not-required"),
            item["acceptance_item"],
            item["actual_result"],
            item.get("evidence_path", []),
        ]
        for item in unresolved
    ]
    surface_rows = []
    for audit in surface_audits.values():
        checked_pages = len(audit.get("page_rows", []))
        passed_pages = len([row for row in audit.get("page_rows", []) if row.get("all_checks_pass")])
        surface_rows.append([audit.get("surface_name"), "pass" if audit.get("all_checks_pass") else "fail", f"{passed_pages}/{checked_pages} pages"])
    return "\n".join(
        [
            "# Test Execution Evidence",
            "",
            "## Execution Summary",
            render_markdown_table(["acceptance_type", "status_breakdown"], status_rows),
            "",
            "## Frontend Surface Audit Summary",
            render_markdown_table(["surface_name", "audit_verdict", "page_checks"], surface_rows),
            "",
            "## Unresolved / Review-Bound Items",
            render_markdown_table(
                ["test_id", "acceptance_type", "status", "human_signoff_status", "acceptance_item", "actual_result", "evidence_path"],
                unresolved_rows,
            ),
            "",
            "## Execution Notes",
            "- Functional items consume inherited Phase-3 automated evidence and must not be downgraded to narrative-only claims.",
            "- Data-fidelity items consume inherited Phase-3 runtime truth artifacts and must keep mock dependency explicit.",
            "- UI review and visual evidence items may remain `review-bound` when no screenshot/manual capture artifact exists.",
            "- `human_signoff_status = review-bound` means the item is otherwise evidentially ready and only manual critical-path signoff remains.",
            "- `human_signoff_status = not-ready` means the item has not yet reached the manual-signoff boundary because review evidence is still incomplete or already failed.",
            "- Missing mandatory functional or data-fidelity evidence is blocking and must force Stage-03 to return.",
        ]
    ) + "\n"


def build_phase4_stage2_execution(
    *,
    phase3_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    retained_proof_mode: bool = False,
    external_evidence_manifest: Path | None = None,
    external_evidence_dir: Path | None = None,
    output_locale: str | None = None,
) -> dict[str, Any]:
    stage01_dir = output_dir / STAGE01_DIRNAME
    stage02_dir = output_dir / STAGE_DIRNAME
    stage02_dir.mkdir(parents=True, exist_ok=True)

    acceptance_catalog = load_json(stage01_dir / "acceptance-catalog.json")
    acceptance_items = [dict(item) for item in ensure_list(acceptance_catalog.get("items"))]
    test_evidence = collect_test_evidence(phase3_root)
    if retained_proof_mode:
        retained_test_evidence = load_retained_stage2_test_evidence(stage02_dir)
        for test_id, bucket in retained_test_evidence.items():
            test_evidence.setdefault(test_id, bucket)
    visual_assets = collect_visual_evidence_paths(phase3_root)
    runtime_truth = load_phase3_runtime_truth_summary(phase3_root)
    runtime_environment = load_phase3_runtime_environment_summary(phase3_root)
    ui_ia_contract = load_json_if_exists(phase3_root / "prototype-fallback" / "ui-ia-contract.json")
    packet_context = build_worker_packet_context(load_worker_packets(phase3_root))
    external_manifest = load_external_evidence_manifest(
        external_evidence_manifest,
        phase3_root=phase3_root,
        external_evidence_dir=external_evidence_dir,
    )
    surface_seed_items: dict[str, dict[str, Any]] = {}
    for item in acceptance_items:
        surface_name = str(item.get("surface_name") or "")
        if item.get("acceptance_type") not in {"ui-review", "visual-evidence"} or not surface_name:
            continue
        surface_seed_items.setdefault(surface_name, item)
    surface_audits = {
        surface_name: audit_frontend_surface(item, phase3_root, ui_ia_contract)
        for surface_name, item in surface_seed_items.items()
    }

    resolved_items: list[dict[str, Any]] = []
    defect_items: list[dict[str, Any]] = []
    review_bound_items: list[dict[str, Any]] = []
    signoff_pending_items: list[dict[str, Any]] = []
    signoff_not_ready_items: list[dict[str, Any]] = []

    for item in acceptance_items:
        runtime_environment_context = runtime_environment_context_for_item(item, packet_context, runtime_environment)
        if item["acceptance_type"] == "functional":
            resolved_status = functional_status(item, test_evidence, runtime_truth, runtime_environment_context)
        elif item["acceptance_type"] == "data-fidelity":
            resolved_status = data_fidelity_status(item, runtime_truth, runtime_environment_context)
        else:
            resolved_status = review_status(
                item,
                phase3_root,
                test_evidence,
                visual_assets,
                surface_audits,
                external_manifest,
                runtime_environment_context,
            )
        resolved = {
            **item,
            "status": resolved_status["status"],
            "actual_result": resolved_status["actual_result"],
            "evidence_path": resolved_status["evidence_paths"],
            "human_signoff_status": resolved_status["human_signoff_status"],
            "signoff_evidence_path": resolved_status["signoff_evidence_paths"],
            "reviewers": resolved_status["reviewers"],
            "external_evidence_refs": resolved_status["external_evidence_refs"],
            "runtime_environment_status": runtime_environment_context["status"],
            "runtime_environment_lane": runtime_environment_context["target_lane"],
            "runtime_environment_requirements": runtime_environment_context["required_runtime_environments"],
            "runtime_environment_packets": runtime_environment_context["matched_packet_ids"],
        }
        resolved_items.append(resolved)
        if resolved["status"] in {"fail", "blocked"}:
            defect_items.append(resolved)
        if item_has_residual_review(resolved):
            review_bound_items.append(resolved)
        if resolved.get("human_signoff_status") == "review-bound":
            signoff_pending_items.append(resolved)
        if resolved.get("human_signoff_status") == "not-ready":
            signoff_not_ready_items.append(resolved)

    summary_counts = summarize_status_counts(resolved_items)

    results_path = stage02_dir / "test-execution-results.json"
    evidence_index_path = stage02_dir / "test-evidence-index.json"
    surface_audit_path = stage02_dir / "frontend-surface-audit.json"
    external_evidence_path = stage02_dir / "external-evidence-consumption.json"
    defect_path = stage02_dir / "defect-record.json"
    review_bound_path = stage02_dir / "review-bound-record.json"
    signoff_path = stage02_dir / "critical-path-signoff-record.json"
    execution_md_path = stage02_dir / "test-execution-evidence.md"
    summary_path = stage02_dir / "stage-02-summary.json"

    write_json(
        results_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_root": str(phase3_root),
            "phase3_runtime_truth": runtime_truth,
            "summary": summary_counts,
            "items": resolved_items,
        },
    )
    write_json(
        evidence_index_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_root": str(phase3_root),
            "summary": {
                "automated_test_target_count": len(test_evidence),
                "visual_asset_count": len(visual_assets),
                "external_evidence_item_count": int(external_manifest["summary"]["item_count"]),
            },
            "test_evidence": test_evidence,
            "visual_assets": visual_assets,
        },
    )
    write_json(
        external_evidence_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_root": str(phase3_root),
            "summary": external_manifest["summary"],
            "manifest_path": external_manifest["manifest_path"],
            "missing_paths": external_manifest.get("missing_paths", []),
            "items": external_manifest["items"],
        },
    )
    write_json(
        surface_audit_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_root": str(phase3_root),
            "summary": {
                "surface_count": len(surface_audits),
                "passing_surface_count": len([audit for audit in surface_audits.values() if audit.get("all_checks_pass")]),
            },
            "surfaces": list(surface_audits.values()),
        },
    )
    write_json(
        defect_path,
        {
            "generated_at": utc_now_iso(),
            "summary": {
                "defect_count": len(defect_items),
                "blocking_functional_count": len(
                    [item for item in defect_items if item["acceptance_type"] == "functional"]
                ),
            },
            "items": defect_items,
        },
    )
    write_json(
        review_bound_path,
        {
            "generated_at": utc_now_iso(),
            "summary": {"review_bound_count": len(review_bound_items)},
            "items": review_bound_items,
        },
    )
    write_json(
        signoff_path,
        {
            "generated_at": utc_now_iso(),
            "summary": {
                "signoff_pending_count": len(signoff_pending_items),
                "signoff_not_ready_count": len(signoff_not_ready_items),
            },
            "items": signoff_pending_items,
        },
    )
    write_text(
        execution_md_path,
        localize_phase4_stage2_execution_markdown(
            build_execution_markdown(resolved_items, summary_counts, surface_audits),
            output_locale,
        ),
    )

    summary = {
        "stage": "evidence-execution-and-defect-identification",
        "title": title,
        "version": version,
        "generated_at": utc_now_iso(),
        "phase3_root": str(phase3_root),
        "output_dir": str(stage02_dir),
        "phase3_mainline_summary_present": bool(runtime_truth.get("mainline_summary_present")),
        "phase3_mainline_verdict": str(runtime_truth.get("phase_verdict") or ""),
        "phase3_mainline_total_score": runtime_truth.get("phase_total_score"),
        "phase3_mainline_backend_verification_present": bool(runtime_truth.get("mainline_backend_verification_present")),
        "phase3_full_targeted_evidence_present": bool(runtime_truth.get("full_targeted_evidence_present")),
        "phase3_full_targeted_evidence_status": str(runtime_truth.get("full_targeted_evidence_status") or "unknown"),
        "phase3_full_targeted_failed_tests": runtime_truth.get("full_targeted_failed_tests", []),
        "functional_pass_count": len(
            [item for item in resolved_items if item["acceptance_type"] == "functional" and item["status"] == "pass"]
        ),
        "functional_non_pass_count": len(
            [
                item
                for item in resolved_items
                if item["acceptance_type"] == "functional" and item["status"] not in {"pass", "conditional-pass"}
            ]
        ),
        "functional_conditional_pass_count": len(
            [item for item in resolved_items if item["acceptance_type"] == "functional" and item["status"] == "conditional-pass"]
        ),
        "data_fidelity_non_pass_count": len(
            [
                item
                for item in resolved_items
                if item["acceptance_type"] == "data-fidelity" and item["status"] not in {"pass", "conditional-pass"}
            ]
        ),
        "data_fidelity_conditional_pass_count": len(
            [item for item in resolved_items if item["acceptance_type"] == "data-fidelity" and item["status"] == "conditional-pass"]
        ),
        "review_bound_count": len(review_bound_items),
        "signoff_pending_count": len(signoff_pending_items),
        "signoff_not_ready_count": len(signoff_not_ready_items),
        "runtime_environment_ledger_present": bool(runtime_environment.get("present")),
        "runtime_environment_missing_lane_count": len(
            [lane for lane in ensure_list(runtime_environment.get("missing_runtime_lanes")) if str(lane).strip()]
        ),
        "runtime_environment_missing_lanes": [
            str(lane) for lane in ensure_list(runtime_environment.get("missing_runtime_lanes")) if str(lane).strip()
        ],
        "ui_review_non_pass_count": len(
            [item for item in resolved_items if item["acceptance_type"] == "ui-review" and item["status"] != "pass"]
        ),
        "visual_review_bound_count": len(
            [item for item in resolved_items if item["acceptance_type"] == "visual-evidence" and item["status"] == "review-bound"]
        ),
        "defect_count": len(defect_items),
        "status_counts": summary_counts,
        "artifacts": {
            "results_json": relative_to_root(results_path, output_dir),
            "evidence_index_json": relative_to_root(evidence_index_path, output_dir),
            "surface_audit_json": relative_to_root(surface_audit_path, output_dir),
            "external_evidence_json": relative_to_root(external_evidence_path, output_dir),
            "defect_record_json": relative_to_root(defect_path, output_dir),
            "review_bound_record_json": relative_to_root(review_bound_path, output_dir),
            "critical_path_signoff_json": relative_to_root(signoff_path, output_dir),
            "execution_md": relative_to_root(execution_md_path, output_dir),
        },
    }
    write_json(summary_path, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute the Phase-4 Stage-02 evidence pass")
    parser.add_argument("--phase3-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-4 Testing Validation")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--external-evidence-manifest")
    parser.add_argument("--external-evidence-dir")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_phase4_stage2_execution(
        phase3_root=Path(args.phase3_root).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        title=args.title,
        version=args.version,
        external_evidence_manifest=Path(args.external_evidence_manifest).resolve() if args.external_evidence_manifest else None,
        external_evidence_dir=Path(args.external_evidence_dir).resolve() if args.external_evidence_dir else None,
    )
    print(summary["artifacts"]["results_json"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
