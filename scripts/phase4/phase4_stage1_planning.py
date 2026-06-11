#!/usr/bin/env python3
"""
Build the Phase-4 Stage-01 planning package from a completed Phase-3 root.
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

from common.output_language import localize_phase4_stage1_markdown
from common.markdown_table_tools import markdown_tables
from phase4.phase4_common import (
    api_id_for_operation,
    block_text,
    collect_visual_evidence_paths,
    compact_token,
    dedupe_preserve_order,
    discover_openapi_path,
    ensure_list,
    extract_phase3_surface_markers_from_file,
    extract_operation_ids_from_file,
    extract_structured_field,
    load_frontend_packets,
    load_worker_packets,
    load_json,
    markdown_heading_section,
    load_json_if_exists,
    load_phase3_mainline_summary,
    load_openapi_spec,
    load_phase3_runtime_environment_summary,
    prefixed_id,
    relative_to_root,
    render_markdown_table,
    stable_suffix,
    utc_now_iso,
    write_json,
    write_text,
)


STAGE_DIRNAME = "stage-01-acceptance-coverage-planning"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CORE_FLOW_TOKENS = {
    "activate",
    "auth",
    "decision",
    "export",
    "launch",
    "policy",
    "recommendation",
    "report",
    "review",
    "scope",
    "task",
    "tenant",
}
SECURITY_NEGATIVE_TOKENS = {
    "access",
    "audit",
    "auth",
    "claims",
    "credential",
    "cross",
    "deny",
    "denied",
    "expired",
    "forbidden",
    "isolation",
    "key",
    "kms",
    "oidc",
    "policy",
    "refresh",
    "reuse",
    "role",
    "rotation",
    "secret",
    "session",
    "tenant",
    "token",
    "unauthorized",
}
IDENTITY_DECISION_HINTS: dict[str, tuple[str, ...]] = {
    "ID-01": ("oidc", "tenant", "role", "claims", "deny", "audit", "policy", "forbidden"),
    "ID-02": ("token", "refresh", "rotation", "session", "auth", "deny", "forbidden", "credential"),
    "ID-03": ("key", "secret", "kms", "tenant", "isolation", "audit", "rotation"),
}
SIGNAL_STOPWORDS = {
    "about",
    "after",
    "against",
    "aligned",
    "allow",
    "always",
    "because",
    "before",
    "between",
    "build",
    "capture",
    "driven",
    "evidence",
    "expected",
    "explicit",
    "flow",
    "frozen",
    "linked",
    "must",
    "notes",
    "pass",
    "phase",
    "prompt",
    "related",
    "reviewable",
    "stage",
    "still",
    "subject",
    "summary",
    "surface",
    "system",
    "target",
    "test",
    "this",
    "type",
    "validation",
    "when",
    "with",
}


def flatten_test_targets(packet: dict[str, Any]) -> list[str]:
    targets = packet.get("test_targets")
    if isinstance(targets, dict):
        collected: list[str] = []
        for value in targets.values():
            collected.extend(str(item) for item in ensure_list(value))
        return dedupe_preserve_order(collected)
    return dedupe_preserve_order(str(item) for item in ensure_list(targets))


def is_unexecutable_contract_trace_gap(row: dict[str, Any]) -> bool:
    source_type = str(row.get("source_type") or "").strip().lower()
    if source_type != "contract-trace":
        return False
    if any(str(item).strip() for item in ensure_list(row.get("test_targets"))):
        return False
    final_resolution = str(row.get("final_resolution") or "").strip().lower()
    binding_status = str(row.get("binding_status") or "").strip().lower()
    return final_resolution in {"review", "unresolved"} or binding_status in {"suggested", "review", "unresolved"}


def functional_item_has_requirement_anchor(item: dict[str, Any]) -> bool:
    if item.get("related_req_ids"):
        return True
    source_type = str(item.get("source_type") or "").strip().lower()
    if not source_type:
        return False
    if source_type in {"contract-trace", "scenario", "replay"}:
        return False
    return bool(item.get("source_id")) and bool(item.get("test_targets") or item.get("implementation_targets"))


def build_operation_rows(openapi_spec: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, methods in (openapi_spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            operation_id = str(operation.get("operationId") or f"{method}_{path}")
            tags = [str(item) for item in ensure_list(operation.get("tags")) if item]
            rows.append(
                {
                    "api_id": api_id_for_operation(operation_id),
                    "operation_id": operation_id,
                    "operation_token": compact_token(operation_id),
                    "method": str(method).upper(),
                    "path": str(path),
                    "summary": str(operation.get("summary") or ""),
                    "owner": tags[0] if tags else "",
                    "related_requirements": [],
                    "related_tests": [],
                }
            )
    return sorted(rows, key=lambda row: (row["api_id"], row["path"], row["method"]))


def split_signal_words(raw: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    return re.sub(r"[^A-Za-z0-9]+", " ", spaced)


def signal_tokens(*parts: str) -> list[str]:
    tokens: list[str] = []
    for part in parts:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", split_signal_words(part).lower()):
            if token in SIGNAL_STOPWORDS:
                continue
            tokens.append(token)
    return dedupe_preserve_order(tokens)


def build_item_signal_text(item: dict[str, Any], api_lookup: dict[str, dict[str, Any]]) -> str:
    parts = [
        str(item.get("source_id") or ""),
        str(item.get("source_type") or ""),
        str(item.get("acceptance_item") or ""),
        str(item.get("scenario_prompt") or ""),
        str(item.get("expected_result") or ""),
        str(item.get("surface_name") or ""),
        str(item.get("notes") or ""),
        " ".join(str(value) for value in ensure_list(item.get("related_surface_refs"))),
        " ".join(str(value) for value in ensure_list(item.get("test_targets"))),
        " ".join(str(value) for value in ensure_list(item.get("expected_evidence"))),
    ]
    for api_id in ensure_list(item.get("related_api_ids")):
        row = api_lookup.get(str(api_id)) or {}
        parts.extend(
            [
                str(api_id),
                str(row.get("operation_id") or ""),
                str(row.get("summary") or ""),
                str(row.get("path") or ""),
                str(row.get("method") or ""),
            ]
        )
    return " ".join(part for part in parts if part)


def risk_profile_for_item(item: dict[str, Any], api_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    related_rows = [api_lookup[str(api_id)] for api_id in ensure_list(item.get("related_api_ids")) if str(api_id) in api_lookup]
    methods = {str(row.get("method") or "").upper() for row in related_rows if row.get("method")}
    item_tokens = set(signal_tokens(build_item_signal_text(item, api_lookup)))
    matched_core_tokens = sorted(item_tokens & CORE_FLOW_TOKENS)
    critical_reasons: list[str] = []
    supporting_reasons: list[str] = []
    if methods & WRITE_METHODS:
        critical_reasons.append("write-api")
    if matched_core_tokens:
        supporting_reasons.append("core-workflow:" + ",".join(matched_core_tokens[:4]))
    critical_path = bool(methods & WRITE_METHODS)
    human_signoff_required = critical_path and item.get("acceptance_type") in {"ui-review", "visual-evidence"}
    if item.get("acceptance_type") == "functional":
        risk_weight = "critical" if critical_path else ("high" if supporting_reasons else "medium")
    else:
        risk_weight = "high" if critical_path else "medium"
    return {
        "risk_weight": risk_weight,
        "critical_path": critical_path,
        "human_signoff_required": human_signoff_required,
        "risk_basis": critical_reasons or supporting_reasons or ["secondary-acceptance-layer"],
        "match_tokens": list(item_tokens),
    }


def load_phase2_root(phase3_root: Path) -> Path | None:
    metadata = load_json_if_exists(phase3_root / "phase3-run-metadata.json") or {}
    raw_phase2_root = str(metadata.get("phase2_root") or "").strip()
    if not raw_phase2_root:
        return None
    phase2_root = Path(raw_phase2_root).resolve()
    return phase2_root if phase2_root.exists() else None


def extract_first_backticked_value(block: str, field_name: str) -> str:
    pattern = re.compile(rf"{re.escape(field_name)}:\s*\n\s+(?:-\s+)?`([^`]+)`", re.IGNORECASE)
    match = pattern.search(block)
    return match.group(1).strip() if match else ""


def build_phase2_decision_records(phase2_root: Path | None) -> dict[str, Any]:
    if phase2_root is None:
        return {
            "phase2_root": "",
            "esp_path": "",
            "records": [],
            "summary": {
                "decision_count": 0,
                "architecture_decision_count": 0,
                "tradeoff_decision_count": 0,
                "observability_decision_count": 0,
                "identity_decision_count": 0,
            },
        }

    esp_path = phase2_root / "engineering-spec-pack.md"
    if not esp_path.exists():
        return {
            "phase2_root": str(phase2_root),
            "esp_path": str(esp_path),
            "records": [],
            "summary": {
                "decision_count": 0,
                "architecture_decision_count": 0,
                "tradeoff_decision_count": 0,
                "observability_decision_count": 0,
                "identity_decision_count": 0,
            },
        }

    text = esp_path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []

    adr_block = block_text(text, "key_architecture_decisions")
    for match in re.finditer(r"^\s{2}- (adr_[^:\n]+):\n((?:^\s{4,}.*\n?)*)", adr_block, flags=re.MULTILINE):
        entry = match.group(2)
        decision_id = extract_structured_field(entry, "ad_id") or match.group(1).strip().upper()
        title = extract_structured_field(entry, "title")
        decision = extract_structured_field(entry, "decision")
        evidence = extract_structured_field(entry, "evidence")
        context = extract_structured_field(entry, "context")
        records.append(
            {
                "decision_id": decision_id,
                "category": "architecture",
                "priority": "critical",
                "title": title,
                "summary": " ".join(part for part in [title, decision, evidence, context] if part),
                "source_section": "3.6 Key Architecture Decisions",
                "match_tokens": signal_tokens(title, decision, evidence, context),
            }
        )

    tradeoff_section = markdown_heading_section(text, "6.10 Key Tradeoff Decisions")
    for table in markdown_tables(tradeoff_section):
        if "decision_id" not in table["headers"]:
            continue
        for row in table["rows"]:
            decision_id = str(row.get("decision_id") or "").strip()
            tradeoff_axis = str(row.get("tradeoff_axis") or "")
            chosen_posture = str(row.get("chosen_posture") or "")
            benefit = str(row.get("benefit") or "")
            accepted_because = str(row.get("accepted_because") or "")
            cost_or_risk = str(row.get("cost_or_risk") or "")
            priority = "high" if set(signal_tokens(tradeoff_axis, chosen_posture, benefit)) & {"queue", "tenant", "review", "report"} else "medium"
            records.append(
                {
                    "decision_id": decision_id or f"TD-{len(records) + 1:02d}",
                    "category": "tradeoff",
                    "priority": priority,
                    "title": tradeoff_axis or decision_id,
                    "summary": " ".join(part for part in [tradeoff_axis, chosen_posture, benefit, cost_or_risk, accepted_because] if part),
                    "source_section": "6.10 Key Tradeoff Decisions",
                    "match_tokens": signal_tokens(tradeoff_axis, chosen_posture, benefit, cost_or_risk, accepted_because),
                }
            )
        break

    observability_section = markdown_heading_section(text, "10.8 Observability and Operational Readiness")
    for table in markdown_tables(observability_section):
        if "surface" not in table["headers"]:
            continue
        for index, row in enumerate(table["rows"], start=1):
            surface = str(row.get("surface") or "")
            service_or_flow = str(row.get("service_or_flow") or "")
            key_metrics = str(row.get("key_metrics") or "")
            slo_or_threshold = str(row.get("slo_or_threshold") or "")
            rollout_guardrail = str(row.get("rollout_guardrail") or "")
            records.append(
                {
                    "decision_id": f"OBS-{index:02d}",
                    "category": "observability",
                    "priority": "high",
                    "title": surface,
                    "summary": " ".join(part for part in [surface, service_or_flow, key_metrics, slo_or_threshold, rollout_guardrail] if part),
                    "source_section": "10.8 Observability and Operational Readiness",
                    "match_tokens": signal_tokens(surface, service_or_flow, key_metrics, slo_or_threshold, rollout_guardrail),
                }
            )
        break

    identity_block = block_text(text, "identity_and_key_management_choice_posture")
    recommended_approach = extract_first_backticked_value(identity_block, "recommended_approach")
    access_token_lifetime = extract_first_backticked_value(identity_block, "access_token_lifetime")
    refresh_strategy = extract_first_backticked_value(identity_block, "refresh_strategy")
    rotation_policy = extract_first_backticked_value(identity_block, "rotation_policy")
    secret_storage = extract_first_backticked_value(identity_block, "secret_storage")
    tenant_isolation_note = extract_first_backticked_value(identity_block, "tenant_isolation_note")
    if identity_block:
        records.extend(
            [
                {
                    "decision_id": "ID-01",
                    "category": "identity",
                    "priority": "critical",
                    "title": "Managed OIDC + tenant-scoped BFF posture",
                    "summary": recommended_approach,
                    "source_section": "10.9 Identity, Auth Vendor, and Key Lifecycle",
                    "match_tokens": signal_tokens(
                        "Managed OIDC + tenant-scoped BFF posture",
                        recommended_approach,
                        "cross-tenant deny audit protected endpoint role claims policy check",
                    ),
                },
                {
                    "decision_id": "ID-02",
                    "category": "identity",
                    "priority": "high",
                    "title": "Token lifecycle and rotation posture",
                    "summary": " ".join(part for part in [access_token_lifetime, refresh_strategy, rotation_policy] if part),
                    "source_section": "10.9 Identity, Auth Vendor, and Key Lifecycle",
                    "match_tokens": signal_tokens(
                        "Token lifecycle and rotation posture",
                        access_token_lifetime,
                        refresh_strategy,
                        rotation_policy,
                        "auth context deny forbidden expired credential protected endpoint session reuse",
                    ),
                },
                {
                    "decision_id": "ID-03",
                    "category": "identity",
                    "priority": "high",
                    "title": "Key management and tenant isolation posture",
                    "summary": " ".join(part for part in [secret_storage, tenant_isolation_note] if part),
                    "source_section": "10.9 Identity, Auth Vendor, and Key Lifecycle",
                    "match_tokens": signal_tokens(
                        "Key management and tenant isolation posture",
                        secret_storage,
                        tenant_isolation_note,
                        "secret rotation kms tenant isolation audit log deny path",
                    ),
                },
            ]
        )

    return {
        "phase2_root": str(phase2_root),
        "esp_path": str(esp_path),
        "records": records,
        "summary": {
            "decision_count": len(records),
            "architecture_decision_count": len([record for record in records if record["category"] == "architecture"]),
            "tradeoff_decision_count": len([record for record in records if record["category"] == "tradeoff"]),
            "observability_decision_count": len([record for record in records if record["category"] == "observability"]),
            "identity_decision_count": len([record for record in records if record["category"] == "identity"]),
        },
    }


def apply_risk_metadata(
    acceptance_items: list[dict[str, Any]],
    operation_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    api_lookup = {row["api_id"]: row for row in operation_rows}
    enriched_items: list[dict[str, Any]] = []
    for item in acceptance_items:
        risk = risk_profile_for_item(item, api_lookup)
        enriched_items.append({**item, **risk, "phase2_decision_ids": []})
    return enriched_items, api_lookup


def build_phase2_decision_alignment(
    decision_records: list[dict[str, Any]],
    acceptance_items: list[dict[str, Any]],
    api_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    item_tokens_by_id = {
        item["test_id"]: set(signal_tokens(build_item_signal_text(item, api_lookup)))
        for item in acceptance_items
    }
    item_links: dict[str, list[str]] = {item["test_id"]: [] for item in acceptance_items}
    rows: list[dict[str, Any]] = []

    for record in decision_records:
        record_tokens = set(record.get("match_tokens") or [])
        ranked_matches: list[tuple[int, dict[str, Any], list[str], str]] = []
        identity_hints = set(IDENTITY_DECISION_HINTS.get(str(record.get("decision_id") or ""), ()))
        for item in acceptance_items:
            item_tokens = item_tokens_by_id[item["test_id"]]
            overlap = sorted(record_tokens & item_tokens)
            score = len(overlap)
            coverage_mode = "token-overlap"
            if record.get("category") == "identity":
                hint_overlap = sorted(identity_hints & item_tokens)
                security_overlap = sorted(SECURITY_NEGATIVE_TOKENS & item_tokens)
                if not overlap and not hint_overlap and len(security_overlap) < 2:
                    continue
                if len(overlap) < 2 and not hint_overlap and len(security_overlap) < 3:
                    continue
                score += len(hint_overlap) + min(2, len(security_overlap))
                overlap = dedupe_preserve_order([*overlap, *hint_overlap, *security_overlap[:4]])
                coverage_mode = "identity-negative-path" if hint_overlap and security_overlap else "identity-proxy"
            elif len(overlap) < 2:
                continue
            if item.get("critical_path"):
                score += 1
            ranked_matches.append((score, item, overlap, coverage_mode))
        ranked_matches.sort(key=lambda row: (-row[0], row[1]["test_id"]))
        matched = ranked_matches[:5]
        for _, item, _, _ in matched:
            item_links[item["test_id"]] = dedupe_preserve_order([*item_links[item["test_id"]], record["decision_id"]])
        coverage_strength = "none"
        match_mode = "none"
        if matched:
            coverage_strength = "direct" if matched[0][0] >= 4 else "thematic"
            match_mode = matched[0][3]
        rows.append(
            {
                "decision_id": record["decision_id"],
                "category": record["category"],
                "priority": record["priority"],
                "title": record["title"],
                "source_section": record["source_section"],
                "coverage_status": "mapped" if matched else "unmapped",
                "coverage_strength": coverage_strength,
                "match_mode": match_mode,
                "matched_test_ids": [item["test_id"] for _, item, _, _ in matched],
                "matched_acceptance_types": dedupe_preserve_order(
                    item["acceptance_type"] for _, item, _, _ in matched
                ),
                "match_signals": matched[0][2][:6] if matched else [],
                "summary": record["summary"],
            }
        )

    mapped_decision_count = len([row for row in rows if row["coverage_status"] == "mapped"])
    high_priority_unmapped_count = len(
        [row for row in rows if row["priority"] in {"critical", "high"} and row["coverage_status"] != "mapped"]
    )
    decision_alignment_complete = bool(rows) and high_priority_unmapped_count == 0
    return {
        "rows": rows,
        "item_links": item_links,
        "summary": {
            "decision_count": len(rows),
            "mapped_decision_count": mapped_decision_count,
            "unmapped_decision_count": len(rows) - mapped_decision_count,
            "high_priority_unmapped_count": high_priority_unmapped_count,
            "decision_alignment_complete": decision_alignment_complete,
        },
    }


def infer_related_api_ids(
    row: dict[str, Any],
    operation_rows: list[dict[str, Any]],
    contract_filename_lookup: dict[str, str],
    source_to_api_ids: dict[str, list[str]],
) -> list[str]:
    matches: list[str] = []
    for target in ensure_list(row.get("test_targets")):
        target_name = Path(str(target)).name.lower()
        if target_name.endswith(".contract.test.ts"):
            token = compact_token(target_name.removesuffix(".contract.test.ts"))
            api_id = contract_filename_lookup.get(token)
            if api_id:
                matches.append(api_id)
    if matches:
        return dedupe_preserve_order(matches)

    source_id = str(row.get("source_id") or "")
    packet_matches = source_to_api_ids.get(source_id, [])
    if packet_matches:
        return dedupe_preserve_order(packet_matches)

    row_haystack = compact_token(
        " ".join(
            [
                str(row.get("source_id") or ""),
                str(row.get("source_subject") or ""),
                str(row.get("verification_hook") or ""),
            ]
        )
    )
    for operation in operation_rows:
        token = operation["operation_token"]
        if token and len(token) >= 6 and token in row_haystack:
            matches.append(operation["api_id"])
    return dedupe_preserve_order(matches)


def build_source_to_api_ids(worker_packets: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for packet in worker_packets:
        packet_api_ids = [
            api_id_for_operation(str(item.get("operation_id") or ""))
            for item in ensure_list(packet.get("contract_operations"))
            if item.get("operation_id")
        ]
        packet_api_ids = [api_id for api_id in packet_api_ids if api_id != "API-UNKNOWN"]
        for source_row in ensure_list(packet.get("source_rows")):
            source_id = str(source_row.get("source_id") or "")
            if not source_id:
                continue
            mapping[source_id] = dedupe_preserve_order([*mapping.get(source_id, []), *packet_api_ids])
    return mapping


def select_surface_targets(surface_name: str, packet_targets: list[str], *, phase3_root: Path | None = None) -> list[str]:
    if len(packet_targets) <= 1:
        return packet_targets
    expected_route = f"/{str(surface_name).strip()}".replace("//", "/")
    if phase3_root is not None and surface_name.strip():
        marker_matches: list[str] = []
        for target in packet_targets:
            markers = extract_phase3_surface_markers_from_file(phase3_root / target)
            if expected_route in markers:
                marker_matches.append(target)
        if marker_matches:
            return dedupe_preserve_order(marker_matches)
    surface_token = compact_token(surface_name)
    ordered_matches: list[str] = []
    for target in packet_targets:
        target_path = Path(target)
        target_tokens = [
            compact_token(target_path.stem),
            compact_token(target_path.parent.name),
            compact_token(str(target_path)),
        ]
        if any(token and token in surface_token for token in target_tokens):
            ordered_matches.append(target)
    return dedupe_preserve_order(ordered_matches or packet_targets)


def build_surface_records(
    frontend_packets: list[dict[str, Any]],
    trace_lookup: dict[str, dict[str, Any]],
    phase3_root: Path,
) -> list[dict[str, Any]]:
    surfaces: dict[str, dict[str, Any]] = {}
    for packet in frontend_packets:
        packet_test_targets = flatten_test_targets(packet)
        packet_api_ids = [api_id_for_operation(str(item.get("operation_id") or "")) for item in ensure_list(packet.get("contract_operations"))]
        packet_api_ids = [api_id for api_id in packet_api_ids if api_id != "API-UNKNOWN"]
        packet_source_ids = [str(item.get("source_id")) for item in ensure_list(packet.get("source_rows")) if item.get("source_id")]
        packet_req_ids: list[str] = []
        for source_id in packet_source_ids:
            packet_req_ids.extend(str(item) for item in ensure_list(trace_lookup.get(source_id, {}).get("upstream_trace_ids")))
        packet_targets = [str(item) for item in ensure_list(packet.get("implementation_targets"))]

        surface_names = [str(item) for item in ensure_list(packet.get("frontend_surfaces")) if item]
        for surface_index, surface_name in enumerate(surface_names):
            if len(surface_names) == len(packet_targets) and packet_targets:
                selected_targets = [packet_targets[surface_index]]
            else:
                selected_targets = select_surface_targets(surface_name, packet_targets, phase3_root=phase3_root)
            file_api_ids: list[str] = []
            for target in selected_targets:
                for operation_id in extract_operation_ids_from_file(phase3_root / target):
                    file_api_ids.append(api_id_for_operation(operation_id))
            surface_api_ids = dedupe_preserve_order(file_api_ids or packet_api_ids)
            record = surfaces.setdefault(
                surface_name,
                {
                    "surface_name": surface_name,
                    "surface_id": prefixed_id("SURFACE", surface_name),
                    "surface_slug": stable_suffix(surface_name),
                    "packet_ids": [],
                    "packet_refs": [],
                    "implementation_targets": [],
                    "related_api_ids": [],
                    "related_req_ids": [],
                    "source_ids": [],
                    "test_targets": [],
                },
            )
            record["packet_ids"] = dedupe_preserve_order([*record["packet_ids"], str(packet.get("packet_id") or "")])
            record["packet_refs"] = dedupe_preserve_order([*record["packet_refs"], str(packet.get("packet_path") or "")])
            record["implementation_targets"] = dedupe_preserve_order([*record["implementation_targets"], *selected_targets])
            record["related_api_ids"] = dedupe_preserve_order([*record["related_api_ids"], *surface_api_ids])
            record["related_req_ids"] = dedupe_preserve_order([*record["related_req_ids"], *packet_req_ids])
            record["source_ids"] = dedupe_preserve_order([*record["source_ids"], *packet_source_ids])
            record["test_targets"] = dedupe_preserve_order([*record["test_targets"], *packet_test_targets])
    return sorted(surfaces.values(), key=lambda row: row["surface_name"])


def load_phase3_full_targeted_passed_tests(phase3_root: Path) -> list[str]:
    passed: list[str] = []
    for report_path in sorted((phase3_root / ".phase3-mainline-execution" / "backend-runs").glob("run-*/full-test-report.json")):
        report = load_json_if_exists(report_path) or {}
        failed = [str(item) for item in ensure_list(report.get("failed_tests")) if str(item).strip()]
        if failed:
            continue
        passed.extend(str(item) for item in ensure_list(report.get("passed_tests")) if str(item).strip())
    return dedupe_preserve_order(passed)


def build_phase2_decision_runtime_acceptance_items(
    *,
    decision_records: list[dict[str, Any]],
    operation_rows: list[dict[str, Any]],
    phase3_root: Path,
) -> list[dict[str, Any]]:
    passed_tests = load_phase3_full_targeted_passed_tests(phase3_root)
    if not passed_tests:
        return []

    operation_tokens_by_api_id = {
        row["api_id"]: set(signal_tokens(row.get("operation_id", ""), row.get("summary", ""), row.get("path", ""), row.get("owner", "")))
        for row in operation_rows
    }
    test_tokens_by_target = {target: set(signal_tokens(Path(target).stem, target)) for target in passed_tests}
    items: list[dict[str, Any]] = []
    for record in decision_records:
        if str(record.get("priority") or "").strip().lower() not in {"critical", "high"}:
            continue
        record_tokens = set(str(item) for item in ensure_list(record.get("match_tokens")) if str(item).strip())
        if str(record.get("category") or "") == "identity":
            record_tokens |= set(IDENTITY_DECISION_HINTS.get(str(record.get("decision_id") or ""), ()))
            record_tokens |= SECURITY_NEGATIVE_TOKENS
        related_api_ids = [
            api_id
            for api_id, tokens in operation_tokens_by_api_id.items()
            if record_tokens & tokens
        ]
        if not related_api_ids and operation_rows:
            related_api_ids = [row["api_id"] for row in operation_rows if str(row.get("method") or "").upper() in WRITE_METHODS][:5]
        selected_tests = [
            target
            for target, tokens in test_tokens_by_target.items()
            if record_tokens & tokens
        ]
        if not selected_tests:
            related_operation_tokens = set()
            for row in operation_rows:
                if row["api_id"] in related_api_ids:
                    related_operation_tokens.add(compact_token(str(row.get("operation_id") or "")))
            selected_tests = [
                target
                for target in passed_tests
                if any(token and token in compact_token(target) for token in related_operation_tokens)
            ]
        if not selected_tests:
            selected_tests = passed_tests

        decision_id = str(record.get("decision_id") or "phase2-decision").strip()
        title = str(record.get("title") or decision_id).strip()
        items.append(
            {
                "test_id": f"TEST-P2-DECISION-{stable_suffix(decision_id)}",
                "acceptance_type": "functional",
                "source_id": decision_id,
                "source_type": "phase2-decision",
                "acceptance_item": f"{title} remains covered by Phase-3 full-targeted runtime evidence",
                "related_api_ids": dedupe_preserve_order(related_api_ids),
                "api_linkage_status": "mapped" if related_api_ids else "explicit-mainline-runtime-evidence",
                "related_req_ids": [],
                "related_surface_refs": [],
                "scenario_prompt": "Consume Phase-3 mainline full-targeted evidence before accepting this Phase-2 decision as closed.",
                "expected_result": "Relevant contract, SQL, replay, or service-boundary evidence is green in the Phase-3 full-targeted report.",
                "actual_result": "",
                "expected_evidence": ["full-test-report.json", "phase3-verification-ledger.json"],
                "status": "not-run",
                "evidence_path": [],
                "owner_or_executor": "phase4-stage02",
                "notes": str(record.get("summary") or title),
                "test_targets": dedupe_preserve_order(selected_tests),
                "implementation_targets": [],
            }
        )
    return sorted(items, key=lambda item: item["test_id"])


def build_acceptance_items(
    *,
    trace_rows: list[dict[str, Any]],
    trace_lookup: dict[str, dict[str, Any]],
    frontend_packets: list[dict[str, Any]],
    worker_packets: list[dict[str, Any]],
    operation_rows: list[dict[str, Any]],
    phase3_root: Path,
) -> list[dict[str, Any]]:
    contract_filename_lookup = {
        compact_token(row["operation_id"]): row["api_id"] for row in operation_rows if row.get("operation_id")
    }
    source_to_api_ids = build_source_to_api_ids(worker_packets)
    source_to_surfaces: dict[str, list[str]] = {}
    for packet in frontend_packets:
        packet_surfaces = [str(item) for item in ensure_list(packet.get("frontend_surfaces")) if item]
        for source_row in ensure_list(packet.get("source_rows")):
            source_id = str(source_row.get("source_id") or "")
            if not source_id:
                continue
            source_to_surfaces[source_id] = dedupe_preserve_order([*source_to_surfaces.get(source_id, []), *packet_surfaces])

    items: list[dict[str, Any]] = []
    backend_trace_items: list[dict[str, Any]] = []
    for row in trace_rows:
        source_id = str(row.get("source_id") or "")
        related_api_ids = infer_related_api_ids(row, operation_rows, contract_filename_lookup, source_to_api_ids)
        api_linkage_status = "mapped" if related_api_ids else "explicit-no-api-boundary"
        trace_item = {
            "test_id": prefixed_id("TEST", source_id),
            "acceptance_type": "functional",
            "source_id": source_id,
            "source_type": str(row.get("source_type") or ""),
            "acceptance_item": str(row.get("source_subject") or source_id),
            "related_api_ids": related_api_ids,
            "api_linkage_status": api_linkage_status,
            "related_req_ids": [str(item) for item in ensure_list(row.get("upstream_trace_ids"))],
            "related_surface_refs": source_to_surfaces.get(source_id, []),
            "scenario_prompt": str(row.get("verification_hook") or "Execute linked tests against the frozen Phase-3 contract/runtime evidence."),
            "expected_result": "All linked contract/scenario/replay evidence remains green and preserves the stated acceptance subject.",
            "actual_result": "",
            "expected_evidence": ["vitest-json", "verification-report.json"],
            "status": "not-run",
            "evidence_path": [],
            "owner_or_executor": "phase4-stage02",
            "notes": str(row.get("source_type") or ""),
            "test_targets": [str(item) for item in ensure_list(row.get("test_targets"))],
            "implementation_targets": [],
        }
        backend_trace_items.append(trace_item)
        # Unresolved contract-trace gaps without executable targets stay visible via data-fidelity/code-review,
        # but they should not be promoted into mandatory runnable functional acceptance items.
        if is_unexecutable_contract_trace_gap(row):
            continue
        items.append(trace_item)

    for surface in build_surface_records(frontend_packets, trace_lookup, phase3_root):
        items.append(
            {
                "test_id": f"TEST-UI-{surface['surface_slug']}",
                "acceptance_type": "ui-review",
                "source_id": surface["surface_id"],
                "source_type": "frontend-surface",
                "acceptance_item": f"{surface['surface_name']} respects contract-driven loading, success, empty, denied, and error states",
                "related_api_ids": surface["related_api_ids"],
                "related_req_ids": surface["related_req_ids"],
                "related_surface_refs": [surface["surface_name"]],
                "scenario_prompt": "Review the implemented surface against the linked packet scope and state model.",
                "expected_result": "The surface behavior remains aligned to the frozen API contract and packet-level scenario coverage.",
                "actual_result": "",
                "expected_evidence": ["frontend route file", "packet verification", "manual walkthrough note"],
                "status": "not-run",
                "evidence_path": [],
                "owner_or_executor": "phase4-stage02",
                "notes": ", ".join(surface["packet_ids"]),
                "test_targets": surface["test_targets"],
                "implementation_targets": surface["implementation_targets"],
                "surface_name": surface["surface_name"],
                "surface_slug": surface["surface_slug"],
            }
        )
        items.append(
            {
                "test_id": f"TEST-VISUAL-{surface['surface_slug']}",
                "acceptance_type": "visual-evidence",
                "source_id": surface["surface_id"],
                "source_type": "frontend-surface",
                "acceptance_item": f"{surface['surface_name']} has reviewable screenshot/video/manual visual evidence",
                "related_api_ids": surface["related_api_ids"],
                "related_req_ids": surface["related_req_ids"],
                "related_surface_refs": [surface["surface_name"]],
                "scenario_prompt": "Capture screenshot, short video, or equivalent manual review artifact for the surface.",
                "expected_result": "At least one reviewable visual artifact exists, or the gap remains explicit and review-bound.",
                "actual_result": "",
                "expected_evidence": ["screenshot", "video", "manual walkthrough record"],
                "status": "not-run",
                "evidence_path": [],
                "owner_or_executor": "phase4-stage02",
                "notes": "Visual evidence is required for design-facing acceptance; do not fake it when the environment cannot capture it.",
                "test_targets": surface["test_targets"],
                "implementation_targets": surface["implementation_targets"],
                "surface_name": surface["surface_name"],
                "surface_slug": surface["surface_slug"],
            }
        )

    for item in backend_trace_items:
        if not item.get("related_api_ids") and not item.get("test_targets"):
            continue
        items.append(
            {
                "test_id": f"TEST-DF-{str(item['source_id']).replace('TEST-', '')}",
                "acceptance_type": "data-fidelity",
                "source_id": item["source_id"],
                "source_type": item["source_type"],
                "acceptance_item": f"{item['acceptance_item']} is backed by real persistence/runtime truth instead of mock or simulation",
                "related_api_ids": item["related_api_ids"],
                "related_req_ids": item["related_req_ids"],
                "related_surface_refs": item["related_surface_refs"],
                "scenario_prompt": "Resolve runtime truth from Phase-3 verification and review artifacts before accepting backend green as real.",
                "expected_result": "Phase-3 evidence proves real service-boundary execution and real persistence truth for this slice, or the result stays explicitly conditional.",
                "actual_result": "",
                "expected_evidence": [
                    "phase3-delivery-gate.json",
                    "phase3-verification-ledger.json",
                    "code-review-metrics.json",
                    "mock-dependency-manifest.json",
                ],
                "status": "not-run",
                "evidence_path": [],
                "owner_or_executor": "phase4-stage02",
                "notes": "Do not collapse pass-on-mock into pass.",
                "test_targets": item["test_targets"],
                "implementation_targets": item["implementation_targets"],
            }
        )

    return sorted(items, key=lambda item: item["test_id"])


def attach_registry_links(
    api_registry_rows: list[dict[str, Any]],
    acceptance_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_api_id = {row["api_id"]: {**row} for row in api_registry_rows}
    for item in acceptance_items:
        for api_id in item.get("related_api_ids", []):
            row = by_api_id.get(api_id)
            if row is None:
                continue
            row["related_tests"] = dedupe_preserve_order([*row["related_tests"], item["test_id"]])
            row["related_requirements"] = dedupe_preserve_order([*row["related_requirements"], *item.get("related_req_ids", [])])
    return list(sorted(by_api_id.values(), key=lambda row: row["api_id"]))


def build_acceptance_checklist_markdown(items: list[dict[str, Any]]) -> str:
    rows = [
        [
            item["test_id"],
            item["acceptance_type"],
            item["acceptance_item"],
            item.get("risk_weight", ""),
            str(bool(item.get("critical_path"))).lower(),
            str(bool(item.get("human_signoff_required"))).lower(),
            item.get("related_api_ids", []),
            item.get("related_req_ids", []),
            item.get("related_surface_refs", []),
            item.get("phase2_decision_ids", []),
            item["scenario_prompt"],
            item["expected_result"],
            item["actual_result"],
            item.get("expected_evidence", []),
            item["status"],
            item.get("evidence_path", []),
            item["owner_or_executor"],
            item["notes"],
        ]
        for item in items
    ]
    table = render_markdown_table(
        [
            "test_id",
            "acceptance_type",
            "acceptance_item",
            "risk_weight",
            "critical_path",
            "human_signoff_required",
            "related_api_ids",
            "related_req_ids",
            "related_surface_refs",
            "phase2_decision_ids",
            "scenario_prompt",
            "expected_result",
            "actual_result",
            "expected_evidence",
            "status",
            "evidence_path",
            "owner / executor",
            "notes",
        ],
        rows,
    )
    return "\n".join(
        [
            "# Acceptance Checklist",
            "",
            "## Scope Summary",
            "- acceptance_scope_summary: Functional acceptance is mandatory; UI review and visual evidence are explicit secondary acceptance types.",
            "- target_environment_summary: Consume inherited Phase-3 executable evidence before any new manual review work.",
            "- out_of_scope_items: release approval, production go-live decision, long-run exploratory UX research.",
            "- review_bound_items: screenshot/video/manual visual evidence may remain review-bound when the capture environment is unavailable.",
            "",
            "## Acceptance Item Table",
            table,
            "",
            "## Gate Linkage",
            "- entry_gate_reference: `test-entry-exit-gate-checklist.md`",
            "- exit_gate_reference: `test-entry-exit-gate-checklist.md`",
            "- pass_fail_rule_summary: all `functional` items must pass; unresolved `ui-review` / `visual-evidence` items must stay explicit.",
            "- blocked_state_rule: if a mandatory functional or data-fidelity item lacks evidence, Stage-03 must return.",
            "",
            "## Execution Notes",
            "- evidence_capture_expectations: functional items use inherited worker-run evidence; UI/visual items may use screenshot, video, or manual walkthrough record.",
            "- defect_capture_linkage: `../stage-02-evidence-execution-and-defect-identification/defect-record.json`",
            "- retest_or_follow_up_rule: review-bound visual items carry forward to optional Phase-4 Stage-04 release-readiness handling, or equivalent downstream governance, if no capture environment exists in Stage-01..03.",
        ]
    ) + "\n"


def build_decision_alignment_markdown(alignment_rows: list[dict[str, Any]]) -> str:
    mapped_rows = [
        [
            row["decision_id"],
            row["category"],
            row["priority"],
            row["title"],
            row["coverage_strength"],
            row.get("match_mode", "token-overlap"),
            row["matched_test_ids"],
            row["matched_acceptance_types"],
            row["match_signals"],
        ]
        for row in alignment_rows
        if row["coverage_status"] == "mapped"
    ]
    uncovered_rows = [
        [
            row["decision_id"],
            row["category"],
            row["priority"],
            row["title"],
            row["source_section"],
            row["summary"],
        ]
        for row in alignment_rows
        if row["coverage_status"] != "mapped"
    ]
    return "\n".join(
        [
            "# Decision Coverage Alignment",
            "",
            "## Why This Exists",
            "- Phase-4 should not validate runtime outputs in isolation from the Phase-2 design decisions that shaped the architecture, auth posture, and operational guardrails.",
            "- Unmapped decisions are warnings about design intent that may have escaped explicit acceptance coverage.",
            "- Identity decisions should map to negative-path acceptance such as deny, cross-tenant, audit, secret, or token-lifecycle surfaces rather than only generic happy-path coverage.",
            "",
            "## Covered Decisions",
            render_markdown_table(
                [
                    "decision_id",
                    "category",
                    "priority",
                    "title",
                    "coverage_strength",
                    "match_mode",
                    "matched_test_ids",
                    "matched_acceptance_types",
                    "match_signals",
                ],
                mapped_rows,
            ),
            "",
            "## Uncovered / Weakly-Covered Decisions",
            render_markdown_table(
                ["decision_id", "category", "priority", "title", "source_section", "summary"],
                uncovered_rows,
            ),
        ]
    ) + "\n"


def build_contract_registry_markdown(registry_rows: list[dict[str, Any]], openapi_ref: str, approved: bool) -> str:
    table_rows = [
        [
            row["api_id"],
            "sync-api",
            row["operation_id"],
            row["owner"] or "unassigned-tag",
            "approved" if approved else "review",
            openapi_ref,
            "follow frozen Phase-3 OpenAPI until next contract revision",
            "business/system error envelope from OpenAPI response set",
            "",
            row["related_requirements"],
            row["related_tests"],
            row["summary"],
            "",
        ]
        for row in registry_rows
    ]
    table = render_markdown_table(
        [
            "api_id",
            "type",
            "name",
            "owner",
            "status",
            "spec_path",
            "versioning_policy",
            "error_model",
            "related_module (MOD-*)",
            "related_requirements (REQ-*)",
            "related_tests (TEST-*)",
            "compatibility_notes",
            "last_reviewed",
        ],
        table_rows,
    )
    return "\n".join(
        [
            "# Contract Registry",
            "",
            "## Registry Rules",
            "- Every contract keeps a stable `API-*` id derived from Phase-3 `operationId`.",
            "- The registry is regenerated from the frozen Phase-3 OpenAPI contract, not from narrative-only interpretation.",
            "- `functional`, `ui-review`, and `visual-evidence` acceptance items may all reference the same `API-*` ids.",
            "",
            "## Contract Registry Table",
            table,
            "",
            "## Review-Bound Notes",
            "- Open questions / review_bound_inputs: none added at Stage-01; contract truth is inherited from Phase-3.",
        ]
    ) + "\n"


def build_coverage_markdown(items: list[dict[str, Any]]) -> str:
    functional_ids = [item["test_id"] for item in items if item["acceptance_type"] == "functional"]
    ui_ids = [item["test_id"] for item in items if item["acceptance_type"] == "ui-review"]
    visual_ids = [item["test_id"] for item in items if item["acceptance_type"] == "visual-evidence"]
    scope_rows = [
        [
            "Functional contract/scenario/replay acceptance",
            "This is the mandatory business-truth layer inherited from Phase-3 execution evidence.",
            dedupe_preserve_order(req for item in items if item["acceptance_type"] == "functional" for req in item.get("related_req_ids", [])),
            dedupe_preserve_order(api for item in items if item["acceptance_type"] == "functional" for api in item.get("related_api_ids", [])),
            functional_ids,
            "high",
            "deep",
            "All linked tests must pass before closure.",
        ],
        [
            "UI state review",
            "Surface-level validation confirms that frontend routes reflect the frozen contract states instead of only compiling.",
            dedupe_preserve_order(req for item in items if item["acceptance_type"] == "ui-review" for req in item.get("related_req_ids", [])),
            dedupe_preserve_order(api for item in items if item["acceptance_type"] == "ui-review" for api in item.get("related_api_ids", [])),
            ui_ids,
            "medium",
            "focused",
            "Manual/UI review may remain review-bound if only code/test evidence exists.",
        ],
        [
            "Visual evidence capture",
            "Screenshot/video/manual evidence makes design acceptance auditable rather than implied.",
            dedupe_preserve_order(req for item in items if item["acceptance_type"] == "visual-evidence" for req in item.get("related_req_ids", [])),
            dedupe_preserve_order(api for item in items if item["acceptance_type"] == "visual-evidence" for api in item.get("related_api_ids", [])),
            visual_ids,
            "medium",
            "focused",
            "If capture tooling is absent, keep the gap explicit as review-bound.",
        ],
    ]
    table = render_markdown_table(
        ["scope_area", "why_in_scope", "related_req_ids", "related_api_ids", "planned_test_ids", "priority", "coverage_depth", "notes"],
        scope_rows,
    )
    return "\n".join(
        [
            "# Test Coverage Explanation",
            "",
            "## Coverage Objective",
            "- coverage_objective_summary: Convert inherited Phase-3 delivery evidence into a closure-reviewable acceptance model without losing traceability or visual-review honesty.",
            "- decision_basis: `mixed`",
            "- primary_business_or_delivery_risks: hidden functional regression, UI state drift, fake visual sign-off.",
            "- validation_focus_areas: functional acceptance first, then UI state review, then screenshot/manual visual evidence.",
            "",
            "## Scope Coverage Table",
            table,
            "",
            "## Explicit Exclusions and Trade-offs",
            "- excluded_scope_areas: release cutover rehearsal, production smoke after deployment, long-form usability research.",
            "- why_excluded: those belong to later operational/release phases rather than Phase-4 testing-validation.",
            "- deferred_follow_up_areas: screenshot/video capture automation if a browser-capable environment becomes available.",
            "- trade_off_notes: when no visual harness exists, preserve review-bound closure instead of fabricating screenshots.",
        ]
    ) + "\n"


def build_gate_markdown(
    trace_mapping_complete: bool,
    visual_assets_present: bool,
    decision_alignment_complete: bool,
    high_priority_unmapped_count: int,
    runtime_environment_summary: dict[str, Any],
) -> str:
    missing_runtime_lanes = [str(value) for value in ensure_list(runtime_environment_summary.get("missing_runtime_lanes"))]
    runtime_ledger_present = bool(runtime_environment_summary.get("present"))
    runtime_gate_status = (
        "review-bound" if (not runtime_ledger_present or missing_runtime_lanes or not visual_assets_present) else "pass"
    )
    table = render_markdown_table(
        ["gate_item", "rationale", "evidence_required", "current_status", "owner", "notes"],
        [
            [
                "acceptance scope is explicit",
                "Stage-02 must not execute against implicit scope",
                "acceptance checklist reference",
                "pass",
                "phase4-stage01",
                "functional, data-fidelity, ui-review, and visual-evidence items are all enumerated",
            ],
            [
                "requirement / contract traceability exists",
                "Acceptance claims must remain reviewable",
                "`TEST-* -> API-* -> REQ-*` mapping evidence",
                "pass" if trace_mapping_complete else "fail",
                "phase4-stage01",
                "driven from Phase-3 trace registry and OpenAPI contract",
            ],
            [
                "phase-2 decision coverage posture is explicit",
                "Closure quality should reveal whether critical design decisions received any acceptance coverage",
                "decision coverage alignment artifact",
                "pass" if decision_alignment_complete else "review-bound",
                "phase4-stage01",
                f"high_priority_unmapped_count={high_priority_unmapped_count}",
            ],
            [
                "execution environment is available or explicitly review-bound",
                "Stage-02 must not start on hidden environment assumptions",
                "environment readiness note",
                runtime_gate_status,
                "phase4-stage01",
                (
                    f"runtime_ledger_present={str(runtime_ledger_present).lower()}; "
                    f"missing_runtime_lanes={','.join(missing_runtime_lanes) or 'none'}; "
                    f"visual_assets_present={str(visual_assets_present).lower()}"
                ),
            ],
            [
                "execution-control artifact exists",
                "Stage-02 needs an explicit execution frame",
                "execution-control reference",
                "pass",
                "phase4-stage01",
                "functional, data-fidelity, and visual evidence paths are split by acceptance type",
            ],
        ],
    )
    exit_table = render_markdown_table(
        ["gate_item", "rationale", "evidence_required", "current_status", "owner", "notes"],
        [
            [
                "planned execution results are recorded",
                "Closure must be based on explicit execution evidence",
                "execution result reference",
                "pass",
                "phase4-stage03",
                "Stage-02 emits a per-item results ledger",
            ],
            [
                "defects / unresolved issues are explicit",
                "Closure must not hide unresolved failures or review-bound items",
                "defect record / review-bound record",
                "pass",
                "phase4-stage03",
                "visual evidence gaps remain explicit instead of being greenwashed",
            ],
            [
                "evidence paths exist for meaningful outcomes",
                "Narrative-only closure is not enough",
                "evidence pointer list",
                "pass",
                "phase4-stage03",
                "functional items bind to worker-run evidence; data-fidelity items bind to Phase-3 runtime truth artifacts; visual items bind to assets or review-bound notes",
            ],
            [
                "residual risk / sign-off logic is explicit",
                "Stage-03 must record judgment cleanly",
                "closure summary / downstream boundary note",
                "pass",
                "phase4-stage03",
                "Phase-4 stops before release approval",
            ],
        ],
    )
    return "\n".join(
        [
            "# Test Entry / Exit Gate Checklist",
            "",
            "## Gate Scope Summary",
            "- stage01_scope_summary: Freeze an acceptance model that can be executed from inherited Phase-3 evidence without inventing missing visual proof.",
            "- gate_owner_or_review_role: phase4-stage01 / phase4-stage03",
            "- target_environment_summary: Phase-3 executable artifact root plus any optional manual review environment.",
            "- review_bound_items: screenshot/video/manual capture may remain review-bound if no capture harness exists.",
            "",
            "## Entry Gate Checklist",
            table,
            "",
            "## Exit Gate Checklist",
            exit_table,
            "",
            "## Gate Decision Rules",
            "- stage02_may_start_when: functional and data-fidelity scope, trace mapping, and execution-control artifacts are explicit.",
            "- stage02_must_not_start_when: mandatory functional or data-fidelity acceptance items have no upstream evidence basis.",
            "- stage03_may_close_when: all functional items pass and any remaining UI/visual/signoff gaps stay explicit as review-bound.",
            "- stage03_must_return_when: any functional item fails, blocks, or remains not-run.",
            "- re_test_condition_rule: any failed item or changed acceptance scope requires a Stage-02 rerun.",
            "- waiver_or_review_bound_rule: review-bound is allowed for non-functional visual/manual evidence gaps and for critical-path signoff that is still pending.",
        ]
    ) + "\n"


def build_execution_control_markdown(
    items: list[dict[str, Any]],
    visual_assets_present: bool,
    runtime_environment_summary: dict[str, Any],
) -> str:
    missing_runtime_lanes = [str(value) for value in ensure_list(runtime_environment_summary.get("missing_runtime_lanes"))]
    missing_runtime_detail = []
    for lane in missing_runtime_lanes:
        lane_row = runtime_environment_summary.get("lanes", {}).get(lane, {})
        required = ", ".join(str(value) for value in ensure_list(lane_row.get("required_runtime_environments")))
        missing_runtime_detail.append(f"{lane}:{required or 'target-runtime-environment'}")
    groups = [
        [
            "functional-regression",
            [item["test_id"] for item in items if item["acceptance_type"] == "functional"],
            "Confirm every Phase-3 trace subject still has passing automated evidence.",
            "Inherited worker-run evidence exists for every linked test target.",
            "test-report.json + verification-report.json",
            "Fail or missing evidence goes to defect-record.json",
            "Mandatory gate",
        ],
        [
            "ui-review",
            [item["test_id"] for item in items if item["acceptance_type"] == "ui-review"],
            "Confirm the rendered surface still reflects the contract-driven state model.",
            "Frontend route files and packet verification are present.",
            "route file path + packet verification or manual note",
            "Missing manual review or required critical-path signoff is explicit, not hidden",
            "Non-blocking if only manual review/signoff is pending",
        ],
        [
            "visual-evidence",
            [item["test_id"] for item in items if item["acceptance_type"] == "visual-evidence"],
            "Collect screenshot/video/manual walkthrough evidence when possible.",
            "Capture environment available or explicitly absent.",
            "screenshot / video / manual walkthrough",
            "No visual asset -> review-bound record",
            "Current Stage-01 posture: " + ("capture-ready" if visual_assets_present else "capture-review-bound"),
        ],
    ]
    table = render_markdown_table(
        ["execution_group", "linked_test_ids", "objective", "prerequisite", "evidence_expected", "defect_capture_rule", "notes"],
        groups,
    )
    return "\n".join(
        [
            "# Test Execution Control",
            "",
            "## Execution Objective and Scope",
            "- execution_objective_summary: Execute acceptance against inherited Phase-3 evidence first, then layer manual/UI/visual evidence where available.",
            "- in_scope_validation_areas: functional evidence replay, frontend state review, screenshot/manual evidence capture.",
            "- out_of_scope_validation_areas: deployment rehearsal, production go-live, business sign-off ceremony.",
            "- priority_scenarios: functional acceptance items first.",
            "- assumptions_or_review_bound_conditions: no screenshot automation is assumed unless real assets exist.",
            "",
            "## Environment and Prerequisites",
            "- target_environment: completed Phase-3 artifact root",
            "- environment_requirements: OpenAPI, trace registry, worker-run test reports, frontend route files",
            "- required_access_or_credentials: none beyond filesystem access for the artifact root",
            "- test_data_or_fixture_requirements: inherit from Phase-3 worker-run evidence",
            "- install_run_guide_reference: inherited Phase-3 deploy/runbook when manual replay is needed",
            f"- env_missing_blockers: {', '.join(missing_runtime_detail) if missing_runtime_detail else 'none'}; "
            f"visual_capture={'available' if visual_assets_present else 'review-bound'}",
            "",
            "## Roles and Execution Ownership",
            "- execution_owner: phase4-stage02",
            "- participating_roles: implementation reviewer, QA/reviewer, optional designer or product owner for visual sign-off",
            "- sign_off_or_review_roles: phase4-stage03 plus human reviewer for critical-path UI/visual acceptance items",
            "- escalation_contacts_or_next_actor: optional Phase-4 Stage-04 owner or equivalent downstream release-readiness owner if visual sign-off remains review-bound",
            "",
            "## Execution Control Table",
            table,
            "",
            "## Evidence and Defect Discipline",
            "- execution_log_reference: `../stage-02-evidence-execution-and-defect-identification/test-execution-evidence.md`",
            "- defect_record_reference: `../stage-02-evidence-execution-and-defect-identification/defect-record.json`",
            "- evidence_path_rule: every acceptance item must point to evidence or an explicit review-bound note",
            "- screenshot_log_recording_expectations: use screenshot/video/manual note when real capture is possible; otherwise keep the gap explicit",
            "- critical_path_signoff_rule: critical UI/visual acceptance items may need human signoff even when automated evidence is green",
            "- blocked_state_recording_rule: mandatory functional and data-fidelity evidence gaps are blocking",
        ]
    ) + "\n"


def build_planning_package_markdown(
    *,
    phase3_root: Path,
    stage01_dir: Path,
    acceptance_items: list[dict[str, Any]],
    trace_mapping_complete: bool,
    functional_api_mapping_complete: bool,
    functional_req_mapping_complete: bool,
    decision_alignment_complete: bool,
    high_priority_unmapped_count: int,
    review_bound_visual_posture: bool,
    visual_assets_present: bool,
    delivery_state: str,
    phase3_mainline_summary: dict[str, Any],
    runtime_environment_summary: dict[str, Any],
) -> str:
    functional_count = len([item for item in acceptance_items if item["acceptance_type"] == "functional"])
    data_fidelity_count = len([item for item in acceptance_items if item["acceptance_type"] == "data-fidelity"])
    ui_count = len([item for item in acceptance_items if item["acceptance_type"] == "ui-review"])
    visual_count = len([item for item in acceptance_items if item["acceptance_type"] == "visual-evidence"])
    missing_runtime_lanes = [str(value) for value in ensure_list(runtime_environment_summary.get("missing_runtime_lanes"))]
    return "\n".join(
        [
            "# Testing-Validation Planning Package",
            "",
            "## Document Metadata",
            "- document_name: Phase-4 Stage-01 planning package",
            "- stage: `acceptance-coverage-planning`",
            "- version: 0.1.0",
            "- status: `approved`",
            "",
            "## Intake Summary",
            f"- upstream_phase3_handoff_reference: `{relative_to_root(phase3_root, phase3_root) or '.'}`",
            f"- implementation_scope_summary: Phase-3 delivery state = `{delivery_state}`",
            f"- phase3_mainline_verdict: `{str(phase3_mainline_summary.get('phase_verdict') or 'unknown')}`",
            f"- phase3_mainline_total_score: `{phase3_mainline_summary.get('phase_total_score', 'unknown')}`",
            f"- requirement_and_contract_scope_summary: {functional_count} mandatory functional items, {data_fidelity_count} data-fidelity items, {ui_count} UI review items, {visual_count} visual evidence items",
            "- review_bound_or_unresolved_inputs: visual capture stays review-bound when no capture environment exists",
            "- acceptance_priority_summary: functional/data-fidelity first; UI/visual explicit, not faked",
            "",
            "## Stage-01 Posture",
            "- decision_mode: `auto-proposed`",
            "- stage01_status: `ready`",
            "- why_this_status: inherited Phase-3 evidence is sufficient to freeze acceptance scope and Stage-02 controls",
            "- validation_posture_summary: functional/data-fidelity mandatory; UI/visual secondary evidence",
            "- coverage_priority_basis: `mixed`",
            "- execution_control_posture: `lightweight-equivalent`",
            "",
            "## Acceptance and Coverage Linkage",
            "- acceptance_checklist_reference: `acceptance-checklist.md`",
            "- coverage_explanation_reference: `test-coverage-explanation.md`",
            "- contract_registry_reference: `contract-registry.md`",
            "- decision_coverage_alignment_reference: `decision-coverage-alignment.md`",
            f"- traceability_mapping_summary: `TEST-* -> API-* -> REQ-*` mapping {'complete' if trace_mapping_complete else 'incomplete'}; functional_api_mapping_complete=`{str(functional_api_mapping_complete).lower()}`; functional_req_mapping_complete=`{str(functional_req_mapping_complete).lower()}`",
            f"- phase2_decision_alignment_summary: decision_alignment_complete=`{str(decision_alignment_complete).lower()}`; high_priority_unmapped_count=`{high_priority_unmapped_count}`",
            "- ui_and_visual_acceptance_summary: data-fidelity, UI review, and screenshot/manual capture are modeled as separate acceptance item types",
            "- stage02_entry_gate_summary: Stage-02 may start from inherited mandatory evidence; visual gaps stay explicit",
            "",
            "## Gate and Execution-Control Linkage",
            "- test_entry_exit_gate_checklist_reference: `test-entry-exit-gate-checklist.md`",
            "- test_execution_control_template_reference: `test-execution-control.md`",
            f"- environment_readiness_summary: runtime_ledger_present=`{str(bool(runtime_environment_summary.get('present'))).lower()}`; "
            f"missing_runtime_lanes=`{','.join(missing_runtime_lanes) or 'none'}`; visual_assets_present=`{str(visual_assets_present).lower()}`",
            f"- env_missing_blockers: {', '.join(missing_runtime_lanes) if missing_runtime_lanes else 'none'}",
            f"- blocked_or_review_bound_conditions: {', '.join(filter(None, [','.join(missing_runtime_lanes), 'visual capture remains review-bound' if review_bound_visual_posture else ''])) or 'none'}",
            "",
            "## Scope and Exclusion Capture",
            "- in_scope_features_or_claims: all linked Phase-3 trace subjects plus frontend UI/visual acceptance surfaces",
            "- out_of_scope_features_or_claims: production cutover and final release approval",
            "- priority_scenarios: mandatory functional and data-fidelity acceptance first",
            "- deferred_or_follow_up_validation_items: screenshot/video capture automation when a browser-capable environment exists",
            "",
            "## Traceability Hooks",
            "- upstream_req_links: inherited from `phase-3-trace-registry-final.json`",
            "- upstream_api_links: inherited from `openapi-final.yaml`",
            "- planned_test_ids: see `acceptance-catalog.json`",
            "- traceability_notes_for_stage02: do not widen scope beyond the frozen acceptance catalog",
            "",
            "## Stage-02 Start Declaration",
            "- stage02_may_start: `yes`",
            "- required_conditions_already_satisfied: acceptance scope, trace mapping, execution-control artifact, inherited functional evidence",
            "- required_conditions_still_open: screenshot/video/manual visual capture may remain review-bound",
            "- explicit_refusal_conditions_if_no: any missing mandatory functional or data-fidelity evidence would block Stage-02",
            "",
            "## Attached Artifacts",
            "- attached_artifacts:",
            "  - `acceptance-checklist.md`",
            "  - `acceptance-catalog.json`",
            "  - `contract-registry.md`",
            "  - `contract-registry.json`",
            "  - `decision-coverage-alignment.md`",
            "  - `decision-coverage-alignment.json`",
            "  - `test-coverage-explanation.md`",
            "  - `test-entry-exit-gate-checklist.md`",
            "  - `test-execution-control.md`",
            "",
            "## Evidence / Review Notes",
            "- review_notes: Phase-4 explicitly carries UI and visual acceptance without pretending automation exists where it does not.",
            "- waiver_or_provisional_notes: only non-functional visual items may remain review-bound.",
            "- downstream_must_not_assume: screenshot-backed visual sign-off exists unless Stage-02 records real assets.",
        ]
    ) + "\n"


def build_phase4_stage1_planning(
    *,
    phase3_root: Path,
    output_dir: Path,
    title: str,
    version: str,
    output_locale: str | None = None,
) -> dict[str, Any]:
    stage01_dir = output_dir / STAGE_DIRNAME
    stage01_dir.mkdir(parents=True, exist_ok=True)

    openapi_path = discover_openapi_path(phase3_root)
    openapi_spec = load_openapi_spec(openapi_path)
    trace_registry = load_json(phase3_root / "phase-3-trace-registry-final.json")
    delivery_gate = load_json_if_exists(phase3_root / "phase3-delivery-gate.json") or {}
    phase3_mainline_summary = load_phase3_mainline_summary(phase3_root)
    frontend_packets = load_frontend_packets(phase3_root)
    worker_packets = load_worker_packets(phase3_root)
    visual_assets = collect_visual_evidence_paths(phase3_root)
    runtime_environment_summary = load_phase3_runtime_environment_summary(phase3_root)
    phase2_root = load_phase2_root(phase3_root)
    phase2_decisions = build_phase2_decision_records(phase2_root)

    trace_rows = [dict(row) for row in ensure_list(trace_registry.get("rows"))]
    trace_lookup = {str(row.get("source_id")): row for row in trace_rows if row.get("source_id")}
    operation_rows = build_operation_rows(openapi_spec)
    acceptance_items = build_acceptance_items(
        trace_rows=trace_rows,
        trace_lookup=trace_lookup,
        frontend_packets=frontend_packets,
        worker_packets=worker_packets,
        operation_rows=operation_rows,
        phase3_root=phase3_root,
    )
    if not [item for item in acceptance_items if item.get("acceptance_type") == "functional"]:
        acceptance_items.extend(
            build_phase2_decision_runtime_acceptance_items(
                decision_records=phase2_decisions["records"],
                operation_rows=operation_rows,
                phase3_root=phase3_root,
            )
        )
    acceptance_items, api_lookup = apply_risk_metadata(acceptance_items, operation_rows)
    decision_alignment = build_phase2_decision_alignment(phase2_decisions["records"], acceptance_items, api_lookup)
    acceptance_items = [
        {
            **item,
            "phase2_decision_ids": decision_alignment["item_links"].get(item["test_id"], []),
        }
        for item in acceptance_items
    ]
    registry_rows = attach_registry_links(operation_rows, acceptance_items)

    functional_items = [item for item in acceptance_items if item["acceptance_type"] == "functional"]
    functional_req_mapping_complete = all(functional_item_has_requirement_anchor(item) for item in functional_items)
    functional_api_mapping_complete = all(
        item.get("related_api_ids") or item.get("api_linkage_status") == "explicit-no-api-boundary"
        for item in functional_items
    )
    trace_mapping_complete = functional_req_mapping_complete and functional_api_mapping_complete
    review_bound_visual_posture = not bool(visual_assets)
    decision_alignment_complete = bool(decision_alignment["summary"]["decision_alignment_complete"])
    high_priority_unmapped_count = int(decision_alignment["summary"]["high_priority_unmapped_count"])
    delivery_state = str(
        phase3_mainline_summary.get("recommended_formal_state")
        or delivery_gate.get("recommended_formal_state")
        or "unknown"
    )
    phase3_claim_ceiling_report = (
        phase3_mainline_summary.get("claim_ceiling_report")
        if isinstance(phase3_mainline_summary.get("claim_ceiling_report"), dict)
        else {}
    )
    contract_registry_approved = delivery_state == "delivery-ready" and str(
        phase3_mainline_summary.get("phase_verdict") or ""
    ).strip() not in {"BLOCKED", "RETURN-REMEDIATE"}

    acceptance_json_path = stage01_dir / "acceptance-catalog.json"
    acceptance_md_path = stage01_dir / "acceptance-checklist.md"
    contract_json_path = stage01_dir / "contract-registry.json"
    contract_md_path = stage01_dir / "contract-registry.md"
    decision_alignment_json_path = stage01_dir / "decision-coverage-alignment.json"
    decision_alignment_md_path = stage01_dir / "decision-coverage-alignment.md"
    runtime_environment_path = stage01_dir / "runtime-environment-readiness.json"
    coverage_md_path = stage01_dir / "test-coverage-explanation.md"
    gate_md_path = stage01_dir / "test-entry-exit-gate-checklist.md"
    exec_md_path = stage01_dir / "test-execution-control.md"
    planning_md_path = stage01_dir / "testing-validation-planning-package.md"
    summary_path = stage01_dir / "stage-01-summary.json"

    write_json(
        acceptance_json_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_root": str(phase3_root),
            "summary": {
                "acceptance_item_count": len(acceptance_items),
                "functional_count": len([item for item in acceptance_items if item["acceptance_type"] == "functional"]),
                "data_fidelity_count": len([item for item in acceptance_items if item["acceptance_type"] == "data-fidelity"]),
                "ui_review_count": len([item for item in acceptance_items if item["acceptance_type"] == "ui-review"]),
                "visual_evidence_count": len([item for item in acceptance_items if item["acceptance_type"] == "visual-evidence"]),
                "functional_api_mapped_count": len(
                    [item for item in acceptance_items if item["acceptance_type"] == "functional" and item.get("related_api_ids")]
                ),
                "functional_api_optional_count": len(
                    [item for item in acceptance_items if item["acceptance_type"] == "functional" and not item.get("related_api_ids")]
                ),
                "critical_path_count": len([item for item in acceptance_items if item.get("critical_path")]),
                "human_signoff_required_count": len(
                    [item for item in acceptance_items if item.get("human_signoff_required")]
                ),
            },
            "items": acceptance_items,
        },
    )
    write_text(
        acceptance_md_path,
        localize_phase4_stage1_markdown(build_acceptance_checklist_markdown(acceptance_items), output_locale),
    )
    write_json(
        decision_alignment_json_path,
        {
            "generated_at": utc_now_iso(),
            "phase2_root": phase2_decisions["phase2_root"],
            "esp_path": phase2_decisions["esp_path"],
            "summary": {
                **phase2_decisions["summary"],
                **decision_alignment["summary"],
            },
            "rows": decision_alignment["rows"],
        },
    )
    write_text(
        decision_alignment_md_path,
        localize_phase4_stage1_markdown(build_decision_alignment_markdown(decision_alignment["rows"]), output_locale),
    )
    write_json(
        runtime_environment_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_root": str(phase3_root),
            "source_ledger_path": runtime_environment_summary.get("path", ""),
            "summary": {
                "ledger_present": bool(runtime_environment_summary.get("present")),
                "packet_count": int(runtime_environment_summary.get("packet_count") or 0),
                "packets_with_available_runtime": int(runtime_environment_summary.get("packets_with_available_runtime") or 0),
                "packets_missing_runtime": int(runtime_environment_summary.get("packets_missing_runtime") or 0),
                "missing_runtime_lanes": [
                    str(value) for value in ensure_list(runtime_environment_summary.get("missing_runtime_lanes"))
                ],
                "available_runtime_environments": [
                    str(value)
                    for value in ensure_list(runtime_environment_summary.get("available_runtime_environments"))
                ],
            },
            "lanes": runtime_environment_summary.get("lanes", {}),
        },
    )
    write_json(
        contract_json_path,
        {
            "generated_at": utc_now_iso(),
            "phase3_openapi_path": str(openapi_path),
            "summary": {
                "api_count": len(registry_rows),
                "approved_contract_count": len(registry_rows) if contract_registry_approved else 0,
            },
            "rows": registry_rows,
        },
    )
    write_text(
        contract_md_path,
        localize_phase4_stage1_markdown(
            build_contract_registry_markdown(
                registry_rows,
                openapi_ref=relative_to_root(openapi_path, phase3_root),
                approved=contract_registry_approved,
            ),
            output_locale,
        ),
    )
    write_text(
        coverage_md_path,
        localize_phase4_stage1_markdown(build_coverage_markdown(acceptance_items), output_locale),
    )
    write_text(
        gate_md_path,
        localize_phase4_stage1_markdown(
            build_gate_markdown(
                trace_mapping_complete,
                bool(visual_assets),
                decision_alignment_complete,
                high_priority_unmapped_count,
                runtime_environment_summary,
            ),
            output_locale,
        ),
    )
    write_text(
        exec_md_path,
        localize_phase4_stage1_markdown(
            build_execution_control_markdown(
                acceptance_items,
                bool(visual_assets),
                runtime_environment_summary,
            ),
            output_locale,
        ),
    )
    write_text(
        planning_md_path,
        localize_phase4_stage1_markdown(
            build_planning_package_markdown(
                phase3_root=phase3_root,
                stage01_dir=stage01_dir,
                acceptance_items=acceptance_items,
                trace_mapping_complete=trace_mapping_complete,
                functional_api_mapping_complete=functional_api_mapping_complete,
                functional_req_mapping_complete=functional_req_mapping_complete,
                decision_alignment_complete=decision_alignment_complete,
                high_priority_unmapped_count=high_priority_unmapped_count,
                review_bound_visual_posture=review_bound_visual_posture,
                visual_assets_present=bool(visual_assets),
                delivery_state=delivery_state,
                phase3_mainline_summary=phase3_mainline_summary,
                runtime_environment_summary=runtime_environment_summary,
            ),
            output_locale,
        ),
    )

    summary = {
        "stage": "acceptance-coverage-planning",
        "title": title,
        "version": version,
        "generated_at": utc_now_iso(),
        "phase3_root": str(phase3_root),
        "output_dir": str(stage01_dir),
        "stage02_may_start": True,
        "phase3_mainline_summary_present": bool(phase3_mainline_summary.get("present")),
        "phase3_mainline_verdict": str(phase3_mainline_summary.get("phase_verdict") or ""),
        "phase3_mainline_total_score": phase3_mainline_summary.get("phase_total_score"),
        "phase3_delivery_state": delivery_state,
        "phase3_claim_ceiling_report": phase3_claim_ceiling_report,
        "phase3_claim_ceiling_resolved_formal_state": str(
            phase3_mainline_summary.get("claim_ceiling_resolved_formal_state") or "unknown"
        ),
        "phase3_claim_ceiling_blocks_ready": bool(phase3_mainline_summary.get("claim_ceiling_blocks_ready")),
        "trace_mapping_complete": trace_mapping_complete,
        "functional_api_mapping_complete": functional_api_mapping_complete,
        "functional_req_mapping_complete": functional_req_mapping_complete,
        "decision_alignment_complete": decision_alignment_complete,
        "phase2_root": phase2_decisions["phase2_root"],
        "visual_capture_review_bound": review_bound_visual_posture,
        "visual_assets_present": bool(visual_assets),
        "runtime_environment_ledger_present": bool(runtime_environment_summary.get("present")),
        "runtime_environment_missing_packet_count": int(runtime_environment_summary.get("packets_missing_runtime") or 0),
        "runtime_environment_missing_lanes": [
            str(value) for value in ensure_list(runtime_environment_summary.get("missing_runtime_lanes"))
        ],
        "acceptance_item_count": len(acceptance_items),
        "functional_count": len([item for item in acceptance_items if item["acceptance_type"] == "functional"]),
        "data_fidelity_count": len([item for item in acceptance_items if item["acceptance_type"] == "data-fidelity"]),
        "functional_api_mapped_count": len(
            [item for item in acceptance_items if item["acceptance_type"] == "functional" and item.get("related_api_ids")]
        ),
        "functional_api_optional_count": len(
            [item for item in acceptance_items if item["acceptance_type"] == "functional" and not item.get("related_api_ids")]
        ),
        "critical_path_count": len([item for item in acceptance_items if item.get("critical_path")]),
        "human_signoff_required_count": len([item for item in acceptance_items if item.get("human_signoff_required")]),
        "decision_count": int(decision_alignment["summary"]["decision_count"]),
        "mapped_decision_count": int(decision_alignment["summary"]["mapped_decision_count"]),
        "high_priority_unmapped_count": high_priority_unmapped_count,
        "ui_review_count": len([item for item in acceptance_items if item["acceptance_type"] == "ui-review"]),
        "visual_evidence_count": len([item for item in acceptance_items if item["acceptance_type"] == "visual-evidence"]),
        "artifacts": {
            "planning_package": relative_to_root(planning_md_path, output_dir),
            "acceptance_catalog_json": relative_to_root(acceptance_json_path, output_dir),
            "acceptance_checklist_md": relative_to_root(acceptance_md_path, output_dir),
            "contract_registry_json": relative_to_root(contract_json_path, output_dir),
            "contract_registry_md": relative_to_root(contract_md_path, output_dir),
            "decision_alignment_json": relative_to_root(decision_alignment_json_path, output_dir),
            "decision_alignment_md": relative_to_root(decision_alignment_md_path, output_dir),
            "runtime_environment_readiness_json": relative_to_root(runtime_environment_path, output_dir),
            "coverage_md": relative_to_root(coverage_md_path, output_dir),
            "gate_md": relative_to_root(gate_md_path, output_dir),
            "execution_control_md": relative_to_root(exec_md_path, output_dir),
        },
    }
    write_json(summary_path, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the Phase-4 Stage-01 planning package")
    parser.add_argument("--phase3-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--title", default="Phase-4 Testing Validation")
    parser.add_argument("--version", default="0.1.0")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_phase4_stage1_planning(
        phase3_root=Path(args.phase3_root).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        title=args.title,
        version=args.version,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["stage02_may_start"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
