#!/usr/bin/env python3
"""
Generate a lightweight working glossary from Phase-2 outputs.
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


def _normalize_term(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("`"))


def _default_definition(category: str, source_surface: str) -> str:
    return f"{category} carried from {source_surface}."


def build_glossary_entries(
    *,
    stage_02_text: str = "",
    stage_03_text: str = "",
    stage_04_text: str = "",
) -> list[dict[str, str]]:
    from phase2.phase2_quality_check import (
        api_endpoint_entries,
        block_text,
        markdown_tables,
        matching_table_rows,
        tech_selection_candidate_entries,
    )

    entries: dict[str, dict[str, str]] = {}

    def add_entry(term: str, category: str, definition: str, source_surface: str) -> None:
        normalized_term = _normalize_term(term)
        normalized_definition = _normalize_term(definition)
        if not normalized_term:
            return
        current = entries.get(normalized_term.lower())
        candidate = {
            "term": normalized_term,
            "category": category,
            "working_definition": normalized_definition or _default_definition(category, source_surface),
            "source_surface": source_surface,
        }
        if current is None:
            entries[normalized_term.lower()] = candidate
            return
        if len(candidate["working_definition"]) > len(current["working_definition"]):
            entries[normalized_term.lower()] = candidate

    domain_block = block_text(stage_02_text, "domain_map")
    for match in re.finditer(r"^\s{4}- domain_name:\s*([^\n]+)$", domain_block, flags=re.MULTILINE):
        add_entry(match.group(1), "domain", "business domain carried into Stage-03/Stage-04 design.", "Stage-02 domain_map")

    module_block = block_text(stage_02_text, "module_map")
    for module_name in sorted(set(re.findall(r"`(geo\.[^`]+)`", module_block))):
        add_entry(module_name, "module", "implementation ownership boundary declared in Stage-02 module_map.", "Stage-02 module_map")

    service_block = block_text(stage_02_text, "service_candidates")
    for match in re.finditer(r"^\s{2}- `?([^`\n:]+)`?:\n((?:^\s{4,}.*\n?)*)", service_block, flags=re.MULTILINE):
        service_name = _normalize_term(match.group(1))
        entry = match.group(2)
        purpose_match = re.search(r"^\s{4}- purpose:\s*(.+)$", entry, flags=re.MULTILINE)
        purpose = purpose_match.group(1).strip() if purpose_match else "service candidate declared in Stage-02."
        add_entry(service_name, "service", purpose, "Stage-02 service_candidates")

    public_boundary_rows = matching_table_rows(
        block_text(stage_03_text, "public_boundary_registry_closure"),
        {"public_name", "namespace", "status", "origin", "closure_note"},
    )
    for row in public_boundary_rows:
        add_entry(
            row.get("public_name", ""),
            "public-boundary object",
            row.get("closure_note", "") or f"public-boundary surface in namespace {row.get('namespace', '')}",
            "Stage-03 public_boundary_registry_closure",
        )

    schema_rows = matching_table_rows(
        block_text(stage_03_text, "schema_draft"),
        {"table_name", "ownership", "pk", "fk", "unique_constraints", "composite_indexes"},
    )
    for row in schema_rows:
        ownership = row.get("ownership", "").strip() or "declared owner"
        add_entry(
            row.get("table_name", ""),
            "schema table",
            f"authoritative storage surface owned by {ownership}.",
            "Stage-03 schema_draft",
        )

    contract_block = block_text(stage_03_text, "interface_contracts")
    for match in re.finditer(r"contract_name:\s*`?([^\n`]+)`?", contract_block):
        contract_name = _normalize_term(match.group(1))
        nearby = contract_block[max(0, match.start() - 200) : match.start() + 400]
        purpose_match = re.search(r"purpose:\s*([^\n]+)", nearby)
        purpose = purpose_match.group(1).strip() if purpose_match else "interface contract carried into implementation handoff."
        add_entry(contract_name, "contract", purpose, "Stage-03 interface_contracts")

    for row in api_endpoint_entries(block_text(stage_03_text, "api_endpoint_draft")):
        add_entry(
            row.get("endpoint_name", ""),
            "endpoint",
            row.get("purpose", "") or "implementation-facing endpoint in Stage-03 API draft.",
            "Stage-03 api_endpoint_draft",
        )

    tech_rows = tech_selection_candidate_entries(block_text(stage_03_text, "technology_selection_evaluation_matrix"))
    for row in tech_rows[:3]:
        add_entry(
            row.get("candidate_name", ""),
            "technology candidate",
            row.get("rejection_reason", "") or row.get("final_decision", "") or "technology option evaluated in Stage-03.",
            "Stage-03 technology_selection_evaluation_matrix",
        )

    onboarding_block = block_text(stage_04_text, "glossary_or_onboarding_summary")
    for table in markdown_tables(onboarding_block):
        headers = set(table["headers"])
        if not {"term", "category", "working_definition", "source_surface"}.issubset(headers):
            continue
        for row in table["rows"]:
            add_entry(
                row.get("term", ""),
                row.get("category", "") or "implementation term",
                row.get("working_definition", ""),
                row.get("source_surface", "") or "Stage-04 glossary_or_onboarding_summary",
            )

    return sorted(entries.values(), key=lambda item: (item["category"], item["term"].lower()))


def glossary_markdown(entries: list[dict[str, str]]) -> str:
    if not entries:
        return "- glossary extraction yielded no structured terms"
    header = "| term | category | working_definition | source_surface |"
    separator = "|---|---|---|---|"
    rows = [
        f"| {entry['term']} | {entry['category']} | {entry['working_definition']} | {entry['source_surface']} |"
        for entry in entries
    ]
    return "\n".join([header, separator, *rows])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a working glossary from Phase-2 outputs")
    parser.add_argument("--stage-02", default="")
    parser.add_argument("--stage-03", default="")
    parser.add_argument("--stage-04", default="")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()

    def read_if_present(raw: str) -> str:
        return Path(raw).read_text(encoding="utf-8") if raw else ""

    entries = build_glossary_entries(
        stage_02_text=read_if_present(args.stage_02),
        stage_03_text=read_if_present(args.stage_03),
        stage_04_text=read_if_present(args.stage_04),
    )
    if args.format == "json":
        print(json.dumps(entries, ensure_ascii=False, indent=2))
    else:
        print(glossary_markdown(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
