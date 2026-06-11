#!/usr/bin/env python3
"""
Cross-stage naming, terminology, and quantitative consistency checks for Phase-2.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from phase2.phase2_trace_alignment import (
    build_phase2_phase1_resolution_report,
    canonicalize_phase2_trace_artifact_id,
    phase2_trace_id_aliases,
)
from phase2.phase2_quality_check import analyze_stage


STOPWORDS = {
    "geo",
    "service",
    "domain",
    "module",
    "aggregate",
    "context",
    "note",
    "set",
    "lifecycle",
}


def camel_to_words(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = value.replace("_", " ").replace("-", " ")
    return value


def normalized_tokens(value: str) -> set[str]:
    parts = re.findall(r"[a-z0-9]+", camel_to_words(value).lower())
    return {part for part in parts if len(part) > 2 and part not in STOPWORDS}


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", camel_to_words(value).lower()))


def parse_backticked_items(block: str) -> list[str]:
    return re.findall(r"`([^`]+)`", block)


def clean_value(value: str) -> str:
    return value.strip().strip("`").strip()


def normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", clean_value(value).lower())


def parse_markdown_tables(block: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = block.splitlines()
    idx = 0
    while idx < len(lines):
        if not lines[idx].lstrip().startswith("|"):
            idx += 1
            continue
        group: list[str] = []
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            group.append(lines[idx].strip())
            idx += 1
        if len(group) < 2 or "---" not in group[1]:
            continue
        headers = [normalize_header(part) for part in group[0].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for row_line in group[2:]:
            parts = [clean_value(part) for part in row_line.strip("|").split("|")]
            if len(parts) < len(headers):
                parts.extend([""] * (len(headers) - len(parts)))
            rows.append(dict(zip(headers, parts)))
        tables.append({"headers": headers, "rows": rows})
    return tables


def table_column_values(block: str, header_names: tuple[str, ...]) -> list[str]:
    normalized_headers = {normalize_header(name) for name in header_names}
    values: list[str] = []
    for table in parse_markdown_tables(block):
        headers = set(table["headers"])
        column = next((name for name in normalized_headers if name in headers), "")
        if not column:
            continue
        for row in table["rows"]:
            value = clean_value(row.get(column, ""))
            if value:
                values.append(value)
    return list(dict.fromkeys(values))


def parse_domain_names(block: str) -> list[str]:
    names = [clean_value(match) for match in re.findall(r"domain_name:\s*([^\n]+)", block)]
    if names:
        return list(dict.fromkeys(names))
    return table_column_values(block, ("domain_name", "domain"))


def parse_service_names(block: str) -> list[str]:
    names = table_column_values(block, ("service_name",))
    if names:
        return names
    names = []
    for line in block.splitlines():
        if not line.startswith("  - "):
            continue
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`:"):
            names.append(clean_value(stripped.split("`", 2)[1]))
        elif stripped.startswith("- ") and stripped.endswith(":"):
            names.append(clean_value(stripped[2:-1]))
    return names


def parse_event_names(block: str) -> list[str]:
    names = table_column_values(block, ("event_name",))
    if names:
        return names
    return list(dict.fromkeys(clean_value(match) for match in re.findall(r"event_name:\s*`?([^\n`]+)`?", block)))


def parse_public_names(block: str) -> list[str]:
    return table_column_values(block, ("public_name",))


def parse_object_names(block: str) -> list[str]:
    return table_column_values(block, ("aggregate / object", "aggregate/object", "object"))


def parse_schema_table_names(block: str) -> list[str]:
    return table_column_values(block, ("table_name",))


def parse_lifecycle_targets(text: str) -> list[str]:
    lifecycle_rows = parse_required_table_rows(
        text,
        ("aggregate_name", "lifecycle_expression_type", "owner_writer", "trigger_events", "terminal_or_failure_exit", "mermaid_binding", "closure_note"),
    )
    table_names = [
        clean_value(row.get("aggregate_name", ""))
        for row in lifecycle_rows
        if "state diagram" in normalize_text(row.get("lifecycle_expression_type", ""))
        and clean_value(row.get("mermaid_binding", "")).lower() not in {"", "none", "no standalone mermaid", "not_applicable"}
    ]
    if table_names:
        return list(dict.fromkeys(name for name in table_names if name))
    names = [
        clean_value(match)
        for match in re.findall(r"^### .*?[—-]\s+(.+?) Lifecycle\s*$", text, flags=re.MULTILINE)
    ]
    return list(dict.fromkeys(names))


def parse_required_table_rows(block: str, required_headers: tuple[str, ...]) -> list[dict[str, str]]:
    normalized_required = tuple(normalize_header(name) for name in required_headers)
    required_set = set(normalized_required)
    for table in parse_markdown_tables(block):
        headers = set(table["headers"])
        if not required_set.issubset(headers):
            continue
        rows: list[dict[str, str]] = []
        for raw_row in table["rows"]:
            row = {normalize_header(key): clean_value(value) for key, value in raw_row.items()}
            if all(row.get(header, "") for header in normalized_required):
                rows.append(row)
        return rows
    return []


def extract_reference_ids(text: str) -> list[str]:
    matches = re.findall(r"\b(?:AD-[0-9]+|RBI-[0-9]+|WP-[A-Z0-9]+|P[0-9]-[A-Z0-9]+(?:-[A-Z0-9]+)+|[A-Z]{3,}(?:-[A-Z0-9]+)+)\b", text)
    return list(dict.fromkeys(canonicalize_phase2_trace_artifact_id(match.strip()) for match in matches if match.strip()))


def split_inline_items(value: str) -> list[str]:
    parts = re.split(r",|;|\band\b|\s/\s", clean_value(value), flags=re.IGNORECASE)
    return [item.strip().strip("`") for item in parts if item.strip().strip("`")]


def field_supported_by_corpus(row: dict[str, str], field_name: str, corpus: str, *, min_token_matches: int = 2) -> bool:
    value = clean_value(row.get(normalize_header(field_name), ""))
    if not value:
        return False
    return fuzzy_contains(corpus, value, min_token_matches=min_token_matches)


def fuzzy_contains(target_text: str, name: str, *, min_token_matches: int = 2) -> bool:
    target_raw = target_text.lower()
    name_raw = clean_value(name).lower()
    if name_raw and name_raw in target_raw:
        return True
    target_normalized = normalize_text(target_text)
    name_normalized = normalize_text(name)
    if name_normalized and name_normalized in target_normalized:
        return True
    tokens = normalized_tokens(name)
    if not tokens:
        return False
    matches = sum(1 for token in tokens if re.search(rf"\b{re.escape(token)}\b", target_normalized))
    if len(tokens) >= 5:
        threshold = max(min_token_matches, math.ceil(len(tokens) * 0.6))
    elif len(tokens) >= 3:
        threshold = max(min_token_matches, 3)
    else:
        threshold = max(min_token_matches, len(tokens))
    threshold = min(threshold, len(tokens))
    return matches >= max(threshold, 1)


def names_overlap(left: str, right: str) -> bool:
    left_clean = clean_value(left).lower()
    right_clean = clean_value(right).lower()
    if left_clean and right_clean and (
        left_clean == right_clean or left_clean in right_clean or right_clean in left_clean
    ):
        return True
    left_tokens = normalized_tokens(left)
    right_tokens = normalized_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shared = left_tokens & right_tokens
    threshold = min(2, len(left_tokens), len(right_tokens))
    return len(shared) >= max(threshold, 1)


def build_row(category: str, item: str, passed: bool, inconsistency: str = "", resolution: str = "") -> dict[str, str]:
    return {
        "check_category": category,
        "check_item": item,
        "result": "pass" if passed else "fail",
        "inconsistency_found": inconsistency,
        "resolution_or_justification": resolution,
    }


def analyze_consistency(stage_paths: dict[str, Path], phase1_prd: Path | None = None) -> dict[str, Any]:
    analyses = {key: analyze_stage(key, path) for key, path in stage_paths.items()}
    stage_01_text = analyses["stage_01"]["text"].lower()
    stage_01_capability_text = analyses["stage_01"]["blocks"]["capability_map"].lower()
    stage_02_text = analyses["stage_02"]["text"].lower()
    stage_03_text = analyses["stage_03"]["text"].lower()
    stage_04_text = analyses["stage_04"]["text"].lower()
    stage_03_event_alignment_text = "\n".join(
        (
            analyses["stage_03"]["blocks"].get("stage_02_event_name_carry_forward", ""),
            analyses["stage_03"]["blocks"]["interaction_flow"],
            analyses["stage_03"]["blocks"]["scenario_coverage_matrix"],
            analyses["stage_03"]["blocks"]["interface_contracts"],
            analyses["stage_03"]["blocks"]["api_endpoint_draft"],
        )
    ).lower()

    domain_names = parse_domain_names(analyses["stage_02"]["blocks"]["domain_map"])
    module_names = sorted(set(re.findall(r"`(geo\.[^`]+)`", analyses["stage_02"]["blocks"]["module_map"])))
    service_names = parse_service_names(analyses["stage_02"]["blocks"]["service_candidates"])
    event_names = parse_event_names(analyses["stage_02"]["blocks"]["domain_event_catalog"])
    public_names = parse_public_names(analyses["stage_03"]["blocks"]["public_boundary_registry_closure"])
    object_names = parse_object_names(analyses["stage_02"]["blocks"]["responsibility_matrix"])
    if not object_names:
        object_names = table_column_values(analyses["stage_02"]["blocks"]["canonical_object_structure"], ("object_name",))
    lifecycle_targets = parse_lifecycle_targets(analyses["stage_02"]["text"])
    schema_table_names = parse_schema_table_names(analyses["stage_03"]["blocks"]["schema_draft"])
    aggregate_count = len(object_names)
    canonical_object_rows = parse_required_table_rows(
        analyses["stage_02"]["blocks"]["canonical_object_structure"],
        (
            "object_name",
            "authoritative_aggregate",
            "authoritative_service",
            "primary_identifiers",
            "state_or_version_anchor",
            "backing_schema_or_projection",
            "stage_03_contract_or_endpoint",
            "closure_note",
        ),
    )
    service_endpoint_mapping_rows = parse_required_table_rows(
        analyses["stage_02"]["blocks"]["service_endpoint_mapping"],
        (
            "service_name",
            "home_module",
            "stage_03_endpoint_names",
            "public_contracts",
            "primary_owned_object",
            "mapping_note",
        ),
    )
    decision_trace_rows = parse_required_table_rows(
        analyses["stage_01"]["blocks"]["decision_trace_registry"],
        ("trace_id", "adr_id", "decision_title", "upstream_reference", "downstream_artifact_id", "verification_hook"),
    )
    contract_trace_rows = parse_required_table_rows(
        analyses["stage_03"]["blocks"]["contract_trace_registry"],
        ("trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook"),
    )
    rbi_rows = parse_required_table_rows(
        analyses["stage_04"]["blocks"]["unresolved_risks_and_review_bound_items"],
        ("rbi_id", "spike_wp", "blocks_which_wp"),
    )
    rbi_trace_rows = parse_required_table_rows(
        analyses["stage_04"]["blocks"]["rbi_trace_registry"],
        ("trace_id", "rbi_id", "bound_wp", "downstream_artifact_id", "verification_hook", "handoff_rule"),
    )
    replay_rows = parse_required_table_rows(
        analyses["stage_04"]["blocks"]["verification_replay_evidence"],
        (
            "replay_id",
            "scenario_or_contract",
            "replay_type",
            "source_artifacts",
            "expected_outcome",
            "observed_outcome",
            "verdict",
            "evidence_ref",
            "downstream_artifact_id",
            "linked_rbi_or_wp",
        ),
    )
    phase1_resolution_report = (
        build_phase2_phase1_resolution_report(
            phase1_prd=phase1_prd,
            fine_grained_trace_units={
                "decision_trace_units": decision_trace_rows,
                "contract_trace_units": contract_trace_rows,
                "rbi_trace_units": rbi_trace_rows,
                "replay_trace_units": replay_rows,
            },
        )
        if phase1_prd is not None
        else {"rows": [], "summary": {"total_rows": 0, "explicit_rows": 0, "inferred_rows": 0, "missing_rows": 0}}
    )
    phase1_resolution_rows: dict[str, dict[str, Any]] = {}
    for row in phase1_resolution_report.get("rows", []):
        for alias in phase2_trace_id_aliases(str(row.get("artifact_id", ""))):
            phase1_resolution_rows[alias] = row
    implementation_wp_ids = {
        ref for ref in extract_reference_ids(analyses["stage_04"]["blocks"]["implementation_task_sketch"]) if ref.startswith("WP-")
    }
    unresolved_rbi_ids = {row["rbi_id"] for row in rbi_rows}
    stage_02_er_entities = [
        value
        for value in re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", analyses["stage_02"]["text"])
        if value.endswith(("_ROOT", "_REPORT", "_TASK", "_EVENT", "_RUN", "_CAPTURE", "_REVISION", "_MEMBERSHIP"))
    ]
    replay_link_refs = set()
    for replay_row in replay_rows:
        replay_link_refs.update(
            ref
            for ref in extract_reference_ids(replay_row.get("linked_rbi_or_wp", ""))
            if ref.startswith(("RBI-", "WP-"))
        )

    rows: list[dict[str, str]] = []

    domain_parse_issue = bool(analyses["stage_02"]["blocks"]["domain_map"].strip()) and not domain_names
    missing_domains = [] if domain_parse_issue else [name for name in domain_names if not fuzzy_contains(stage_01_capability_text, name)]
    rows.append(
        build_row(
            "terminology",
            "Every Stage-02 domain appears in Stage-01 capability map",
            not domain_parse_issue and not missing_domains,
            "parse_failure: no-parseable-domain-names" if domain_parse_issue else ", ".join(missing_domains),
            "align Stage-01 capability map labels with Stage-02 domain names",
        )
    )

    missing_modules = [name for name in module_names if name.lower() not in analyses["stage_03"]["blocks"]["data_ownership_map"].lower()]
    rows.append(
        build_row(
            "terminology",
            "Every Stage-02 module referenced in Stage-03 data ownership",
            not missing_modules,
            ", ".join(missing_modules),
            "carry missing module names into Stage-03 ownership matrix",
        )
    )

    service_parse_issue = bool(analyses["stage_02"]["blocks"]["service_candidates"].strip()) and not service_names
    unmatched_services = [
        name
        for name in service_names
        if not fuzzy_contains(stage_03_text, name)
    ]
    rows.append(
        build_row(
            "terminology",
            "Every Stage-02 service has ≥1 API endpoint in Stage-03",
            not service_parse_issue and not unmatched_services,
            "parse_failure: no-parseable-service-names" if service_parse_issue else ", ".join(unmatched_services),
            "align service naming with API endpoint or contract names",
        )
    )

    service_endpoint_mapping_parse_issue = (
        bool(analyses["stage_02"]["blocks"]["service_endpoint_mapping"].strip()) and not service_endpoint_mapping_rows
    )
    unresolved_service_endpoint_mappings = []
    for row in service_endpoint_mapping_rows:
        issues: list[str] = []
        endpoints = split_inline_items(row.get("stage_03_endpoint_names", ""))
        contracts = split_inline_items(row.get("public_contracts", ""))
        internal_only = any("internal-only" in endpoint.lower() for endpoint in endpoints)
        if not internal_only and (
            not endpoints
            or any(
                not fuzzy_contains(analyses["stage_03"]["blocks"]["api_endpoint_draft"].lower(), endpoint, min_token_matches=1)
                for endpoint in endpoints
            )
        ):
            issues.append("endpoint-missing")
        contract_corpus = (
            analyses["stage_03"]["blocks"]["interface_contracts"]
            + "\n"
            + analyses["stage_03"]["blocks"]["public_boundary_registry_closure"]
            + "\n"
            + analyses["stage_03"]["blocks"]["api_endpoint_draft"]
            + "\n"
            + analyses["stage_03"]["text"]
        ).lower()
        contract_ok = bool(contracts) and all(
            fuzzy_contains(contract_corpus, contract, min_token_matches=1) for contract in contracts
        )
        if not contract_ok and row.get("primary_owned_object", ""):
            contract_ok = fuzzy_contains(contract_corpus, row.get("primary_owned_object", ""), min_token_matches=1)
        if not contract_ok:
            issues.append("contract-missing")
        module_ok = row.get("home_module", "").lower() in stage_03_text
        if not module_ok:
            module_ok = fuzzy_contains(stage_03_text, row.get("service_name", ""), min_token_matches=1) or fuzzy_contains(
                stage_03_text,
                row.get("primary_owned_object", ""),
                min_token_matches=1,
            )
        if not module_ok:
            issues.append("module-missing")
        if issues:
            unresolved_service_endpoint_mappings.append(f"{row['service_name']}[{','.join(issues)}]")
    rows.append(
        build_row(
            "traceability",
            "Service endpoint mapping rows resolve to Stage-03 endpoints and contracts",
            not service_endpoint_mapping_parse_issue and not unresolved_service_endpoint_mappings,
            (
                "parse_failure: no-parseable-service-endpoint-mapping-rows"
                if service_endpoint_mapping_parse_issue
                else ", ".join(unresolved_service_endpoint_mappings)
            ),
            "carry every Stage-02 service through an explicit endpoint/contract mapping rather than relying on loose naming similarity",
        )
    )

    state_diagram_count = analyses["stage_02"]["metrics"]["mermaid_stateDiagram_count"]
    object_parse_issue = bool(analyses["stage_02"]["blocks"]["responsibility_matrix"].strip()) and not object_names
    lifecycle_parse_issue = state_diagram_count > 0 and not lifecycle_targets
    unmatched_lifecycle_targets = [
        name for name in lifecycle_targets if not any(names_overlap(name, candidate) for candidate in object_names)
    ]
    lifecycle_ok = (
        not object_parse_issue
        and not lifecycle_parse_issue
        and bool(lifecycle_targets)
        and state_diagram_count >= len(lifecycle_targets)
        and not unmatched_lifecycle_targets
    )
    rows.append(
        build_row(
            "terminology",
            "Every aggregate with lifecycle in Stage-02 has stateDiagram",
            lifecycle_ok,
            (
                "parse_failure: no-parseable-object-names"
                if object_parse_issue
                else "parse_failure: no-parseable-lifecycle-targets"
                if lifecycle_parse_issue
                else f"lifecycle_targets={len(lifecycle_targets)}, state_diagrams={state_diagram_count}, unmatched={', '.join(unmatched_lifecycle_targets)}"
            ),
            "add `stateDiagram-v2` coverage for each key aggregate lifecycle",
        )
    )

    canonical_object_parse_issue = bool(analyses["stage_02"]["blocks"]["canonical_object_structure"].strip()) and not canonical_object_rows
    unresolved_canonical_objects = []
    canonical_schema_bindings = "\n".join(row.get("backing_schema_or_projection", "") for row in canonical_object_rows).lower()
    for row in canonical_object_rows:
        issues: list[str] = []
        schema_refs = split_inline_items(row.get("backing_schema_or_projection", ""))
        boundary_refs = split_inline_items(row.get("stage_03_contract_or_endpoint", ""))
        if not schema_refs or any(
            not fuzzy_contains(
                analyses["stage_03"]["blocks"]["schema_draft"] + "\n" + analyses["stage_03"]["blocks"]["data_ownership_map"],
                schema_ref,
                min_token_matches=1,
            )
            for schema_ref in schema_refs
        ):
            issues.append("schema-missing")
        if not boundary_refs or any(
            not fuzzy_contains(
                (
                    analyses["stage_03"]["blocks"]["interface_contracts"]
                    + "\n"
                    + analyses["stage_03"]["blocks"]["api_endpoint_draft"]
                    + "\n"
                    + analyses["stage_03"]["blocks"]["public_boundary_registry_closure"]
                ),
                boundary_ref,
                min_token_matches=1,
            )
            for boundary_ref in boundary_refs
        ):
            issues.append("boundary-surface-missing")
        if issues:
            unresolved_canonical_objects.append(f"{row['object_name']}[{','.join(issues)}]")
    rows.append(
        build_row(
            "traceability",
            "Canonical object structure rows bind to Stage-03 schema and boundary surfaces",
            not canonical_object_parse_issue and not unresolved_canonical_objects,
            (
                "parse_failure: no-parseable-canonical-object-rows"
                if canonical_object_parse_issue
                else ", ".join(unresolved_canonical_objects)
            ),
            "bind each Stage-02 canonical object to concrete Stage-03 schema tables plus contract or endpoint surfaces",
        )
    )

    schema_coverage_applicable = bool(canonical_object_rows)
    uncovered_schema_tables = (
        [
            name
            for name in schema_table_names
            if not (
                fuzzy_contains(canonical_schema_bindings, name, min_token_matches=1)
                or any(names_overlap(name, entity) for entity in stage_02_er_entities)
            )
        ]
        if schema_coverage_applicable
        else []
    )
    rows.append(
        build_row(
            "traceability",
            "Stage-02 canonical object structure or ER covers Stage-03 schema tables",
            not uncovered_schema_tables,
            ", ".join(uncovered_schema_tables),
            "carry every Stage-03 schema table back to a Stage-02 canonical object row or conceptual ER entity",
        )
    )

    contradiction_issues = []
    if "modular monolith" in stage_01_text and "modular monolith" not in (
        analyses["stage_04"]["blocks"]["architecture_convergence_summary"].lower()
        + analyses["stage_04"]["blocks"]["optimality_review"].lower()
    ):
        contradiction_issues.append("Stage-01 fixes modular-monolith direction but Stage-04 does not carry it forward")
    if "attribution" in stage_01_text and "deferred" in stage_01_text:
        later = (
            analyses["stage_04"]["blocks"]["architecture_convergence_summary"].lower()
            + analyses["stage_04"]["blocks"]["implementation_handoff_package"].lower()
        )
        if "attribution" in later and not any(token in later for token in ("deferred", "placeholder", "excluded")):
            contradiction_issues.append("Attribution seam no longer looks deferred in Stage-04")
    rows.append(
        build_row(
            "decision",
            "No contradictory decisions across Stages",
            not contradiction_issues,
            "; ".join(contradiction_issues),
            "preserve Stage-01 core decisions explicitly in later convergence artifacts",
        )
    )

    ad_ids = set(re.findall(r"AD-[0-9]+", analyses["stage_01"]["text"]))
    missing_ads = sorted(ad_id for ad_id in ad_ids if ad_id.lower() not in stage_04_text)
    rows.append(
        build_row(
            "decision",
            "Stage-04 convergence references all Stage-01 decisions",
            not missing_ads,
            ", ".join(missing_ads),
            "reference every Stage-01 AD-id in Stage-04 convergence or handoff sections",
        )
    )

    decision_trace_parse_issue = bool(analyses["stage_01"]["blocks"]["decision_trace_registry"].strip()) and not decision_trace_rows
    decision_chain_corpus = "\n".join((stage_03_text, stage_04_text))
    uncovered_decision_traces = [
        row["trace_id"]
        for row in decision_trace_rows
        if not (
            field_supported_by_corpus(row, "decision_title", decision_chain_corpus)
            or field_supported_by_corpus(row, "verification_hook", decision_chain_corpus)
        )
    ]
    rows.append(
        build_row(
            "traceability",
            "Decision trace rows carry forward into Stage-03/04 evidence",
            not decision_trace_parse_issue and not uncovered_decision_traces,
            (
                "parse_failure: no-parseable-decision-trace-rows"
                if decision_trace_parse_issue
                else ", ".join(uncovered_decision_traces)
            ),
            "carry each decision-trace hook into Stage-03 contracts, Stage-04 replay, or handoff evidence rather than only naming the AD-id",
        )
    )
    unresolved_phase1_decision_traces = [
        row["trace_id"]
        for row in decision_trace_rows
        if not phase1_resolution_rows.get(row["trace_id"], {}).get("phase1_upstream_trace_ids", [])
    ]
    rows.append(
        build_row(
            "traceability",
            "Decision trace rows resolve to Phase-1 trace ids",
            phase1_prd is None or not unresolved_phase1_decision_traces,
            "" if phase1_prd is None else ", ".join(unresolved_phase1_decision_traces),
            "bind each decision trace row to explicit Phase-1 requirement or acceptance ids, or keep enough semantic precision for deterministic inference",
        )
    )

    unmatched_public_names = [name for name in public_names if not fuzzy_contains(stage_02_text, name)]
    rows.append(
        build_row(
            "naming",
            "Stage-03 public boundary names match Stage-02 ER",
            not (bool(analyses["stage_03"]["blocks"]["public_boundary_registry_closure"].strip()) and not public_names)
            and not unmatched_public_names,
            (
                "parse_failure: no-parseable-public-names"
                if bool(analyses["stage_03"]["blocks"]["public_boundary_registry_closure"].strip()) and not public_names
                else ", ".join(unmatched_public_names)
            ),
            "align Stage-02 conceptual model and Stage-03 public-boundary registry vocabulary",
        )
    )

    api_service_ok = (not service_parse_issue) and len(unmatched_services) <= max(len(service_names) // 3, 1)
    rows.append(
        build_row(
            "naming",
            "API endpoint names consistent with service candidate names",
            api_service_ok,
            ", ".join(unmatched_services),
            "rename service candidates or endpoint groups so the mapping is obvious",
        )
    )

    unmatched_events = [name for name in event_names if not fuzzy_contains(stage_03_event_alignment_text, name)]
    rows.append(
        build_row(
            "naming",
            "Domain event names match Stage-02 event catalog",
            not (bool(analyses["stage_02"]["blocks"]["domain_event_catalog"].strip()) and not event_names) and not unmatched_events,
            (
                "parse_failure: no-parseable-event-names"
                if bool(analyses["stage_02"]["blocks"]["domain_event_catalog"].strip()) and not event_names
                else ", ".join(unmatched_events)
            ),
            "carry Stage-02 event names into Stage-03 contracts or scenario flows",
        )
    )

    contract_trace_parse_issue = bool(analyses["stage_03"]["blocks"]["contract_trace_registry"].strip()) and not contract_trace_rows
    contract_chain_corpus = "\n".join(
        (
            analyses["stage_04"]["blocks"]["design_verification_notes"],
            analyses["stage_04"]["blocks"]["verification_replay_evidence"],
            analyses["stage_04"]["blocks"]["implementation_handoff_package"],
            analyses["stage_04"]["blocks"]["implementation_task_sketch"],
            analyses["stage_04"]["text"],
        )
    ).lower()
    uncovered_contract_traces = []
    for row in contract_trace_rows:
        downstream_ok = row.get("downstream_artifact_id", "") == "HANDOFF-0001"
        coverage_ok = field_supported_by_corpus(row, "trace_subject", contract_chain_corpus) or field_supported_by_corpus(
            row, "verification_hook", contract_chain_corpus
        )
        if not (downstream_ok and coverage_ok):
            uncovered_contract_traces.append(row["trace_id"])
    rows.append(
        build_row(
            "traceability",
            "Contract trace rows are consumable by Stage-04 replay or handoff evidence",
            not contract_trace_parse_issue and not uncovered_contract_traces,
            (
                "parse_failure: no-parseable-contract-trace-rows"
                if contract_trace_parse_issue
                else ", ".join(uncovered_contract_traces)
            ),
            "bind every contract trace row to Stage-04 replay or handoff consumption rather than stopping at Stage-03 declaration",
        )
    )
    unresolved_phase1_contract_traces = [
        row["trace_id"]
        for row in contract_trace_rows
        if not phase1_resolution_rows.get(row["trace_id"], {}).get("phase1_upstream_trace_ids", [])
    ]
    rows.append(
        build_row(
            "traceability",
            "Contract trace rows resolve to Phase-1 trace ids",
            phase1_prd is None or not unresolved_phase1_contract_traces,
            "" if phase1_prd is None else ", ".join(unresolved_phase1_contract_traces),
            "carry Phase-1 upstream ids or enough semantic detail so every Stage-03 contract can be traced back to a Phase-1 requirement unit",
        )
    )

    rbi_trace_parse_issue = bool(analyses["stage_04"]["blocks"]["rbi_trace_registry"].strip()) and not rbi_trace_rows
    rbi_chain_corpus = "\n".join(
        (
            analyses["stage_04"]["blocks"]["design_verification_notes"],
            analyses["stage_04"]["blocks"]["verification_replay_evidence"],
            analyses["stage_04"]["blocks"]["implementation_handoff_package"],
            analyses["stage_04"]["blocks"]["implementation_task_sketch"],
        )
    ).lower()
    invalid_rbi_traces = []
    for row in rbi_trace_rows:
        issues: list[str] = []
        if row.get("rbi_id", "") not in unresolved_rbi_ids:
            issues.append("unknown-rbi")
        if row.get("bound_wp", "") not in implementation_wp_ids:
            issues.append("unknown-wp")
        if row.get("downstream_artifact_id", "") != "IMPL-STG00-INPUT-0001":
            issues.append("unexpected-downstream-id")
        if not (
            field_supported_by_corpus(row, "verification_hook", rbi_chain_corpus)
            or row.get("rbi_id", "") in replay_link_refs
            or row.get("bound_wp", "") in replay_link_refs
        ):
            issues.append("no-replay-or-handoff-coverage")
        if issues:
            invalid_rbi_traces.append(f"{row['trace_id']}[{','.join(issues)}]")
    rows.append(
        build_row(
            "traceability",
            "RBI trace rows bind declared RBI, work-package, and implementation intake chain",
            not rbi_trace_parse_issue and not invalid_rbi_traces,
            (
                "parse_failure: no-parseable-rbi-trace-rows"
                if rbi_trace_parse_issue
                else ", ".join(invalid_rbi_traces)
            ),
            "ensure every RBI trace row targets the implementation intake artifact, references a real WP, and has replay or handoff carry-forward evidence",
        )
    )
    unresolved_phase1_rbi_traces = [
        row["trace_id"]
        for row in rbi_trace_rows
        if not phase1_resolution_rows.get(row["trace_id"], {}).get("phase1_upstream_trace_ids", [])
    ]
    rows.append(
        build_row(
            "traceability",
            "RBI trace rows resolve to Phase-1 trace ids",
            phase1_prd is None or not unresolved_phase1_rbi_traces,
            "" if phase1_prd is None else ", ".join(unresolved_phase1_rbi_traces),
            "keep RBI handoff items tied to the originating Phase-1 requirement or acceptance units rather than only downstream implementation labels",
        )
    )

    replay_parse_issue = bool(analyses["stage_04"]["blocks"]["verification_replay_evidence"].strip()) and not replay_rows
    invalid_replay_rows = []
    for row in replay_rows:
        issues: list[str] = []
        if row.get("downstream_artifact_id", "") != "IMPL-STG00-INPUT-0001":
            issues.append("unexpected-downstream-id")
        linked_refs = [ref for ref in extract_reference_ids(row.get("linked_rbi_or_wp", "")) if ref.startswith(("RBI-", "WP-"))]
        if not linked_refs:
            issues.append("missing-rbi-wp-link")
        else:
            unknown_refs = [
                ref
                for ref in linked_refs
                if (ref.startswith("RBI-") and ref not in unresolved_rbi_ids)
                or (ref.startswith("WP-") and ref not in implementation_wp_ids)
            ]
            if unknown_refs:
                issues.append("unknown-link=" + "/".join(unknown_refs))
        if issues:
            invalid_replay_rows.append(f"{row['replay_id']}[{','.join(issues)}]")
    rows.append(
        build_row(
            "traceability",
            "Replay evidence rows reference declared RBI/WP and implementation intake target",
            not replay_parse_issue and not invalid_replay_rows,
            (
                "parse_failure: no-parseable-replay-rows"
                if replay_parse_issue
                else ", ".join(invalid_replay_rows)
            ),
            "keep replay evidence anchored to real RBI/WP ids and the implementation intake artifact",
        )
    )

    capacity_overlap = sum(
        1
        for token in ("throughput", "latency", "growth", "retention", "volume", "storage")
        if token in analyses["stage_01"]["blocks"]["capacity_estimation"].lower()
        and token in (
            analyses["stage_03"]["blocks"]["storage_strategy"].lower()
            + analyses["stage_03"]["blocks"]["capacity_and_performance_assumptions"].lower()
        )
    )
    rows.append(
        build_row(
            "quantitative",
            "Stage-01 capacity reflected in Stage-03 storage strategy",
            capacity_overlap >= 3,
            f"capacity keyword overlap={capacity_overlap}",
            "carry Stage-01 capacity numbers and growth assumptions into Stage-03 storage strategy explicitly",
        )
    )

    schema_table_count = analyses["stage_03"]["metrics"]["schema_table_count"]
    rows.append(
        build_row(
            "quantitative",
            "Schema table count ≥ Stage-02 aggregate count",
            schema_table_count >= aggregate_count,
            f"schema_table_count={schema_table_count}, aggregate_count={aggregate_count}",
            "expand Stage-03 schema coverage until every aggregate has explicit table-level realization",
        )
    )

    fail_count = sum(1 for row in rows if row["result"] == "fail")
    if fail_count == 0:
        verdict = "consistent"
    elif fail_count <= 3:
        verdict = "minor-inconsistencies"
    else:
        verdict = "major-inconsistencies"

    return {
        "rows": rows,
        "overall_consistency_verdict": verdict,
        "summary": {
            "domain_names": domain_names,
            "module_names": module_names,
            "service_names": service_names,
            "event_names": event_names,
            "public_names": public_names,
            "object_names": object_names,
            "lifecycle_targets": lifecycle_targets,
            "decision_trace_rows": len(decision_trace_rows),
            "contract_trace_rows": len(contract_trace_rows),
            "rbi_trace_rows": len(rbi_trace_rows),
            "replay_rows": len(replay_rows),
            "aggregate_count": aggregate_count,
            "schema_table_count": schema_table_count,
            "phase1_trace_resolution": phase1_resolution_report.get("summary", {}),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check cross-stage consistency for Phase-2 artifacts")
    parser.add_argument("--phase1-prd")
    parser.add_argument("--stage-01", required=True)
    parser.add_argument("--stage-02", required=True)
    parser.add_argument("--stage-03", required=True)
    parser.add_argument("--stage-04", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = analyze_consistency(
        {
            "stage_01": Path(args.stage_01),
            "stage_02": Path(args.stage_02),
            "stage_03": Path(args.stage_03),
            "stage_04": Path(args.stage_04),
        },
        phase1_prd=Path(args.phase1_prd) if args.phase1_prd else None,
    )
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "overall_consistency_verdict": result["overall_consistency_verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
