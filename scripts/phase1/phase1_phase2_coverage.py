#!/usr/bin/env python3
"""
Shared helpers for Phase-1 -> Phase-2 coverage contract analysis.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from phase1.phase1_trace_units import extract_phase1_trace_units, phase1_phase2_design_contract_rows
from phase2.phase2_trace_alignment import build_phase2_phase1_resolution_report, split_trace_ids


def normalize_table_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("`").lower())


def markdown_tables(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = text.splitlines()
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
        headers = [normalize_table_header(part) for part in group[0].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for row_line in group[2:]:
            parts = [part.strip().strip("`") for part in row_line.strip("|").split("|")]
            if len(parts) < len(headers):
                parts.extend([""] * (len(headers) - len(parts)))
            rows.append(dict(zip(headers, parts)))
        tables.append({"headers": headers, "rows": rows})
    return tables


def block_text(text: str, block_name: str) -> str:
    lines = text.splitlines()
    start = None
    marker = f"- {block_name}:"
    for idx, line in enumerate(lines):
        if line.startswith(marker):
            start = idx
            break
    if start is None:
        return ""
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("- ") and not line.startswith("  - "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def table_rows_from_block(block: str, required_headers: set[str]) -> list[dict[str, str]]:
    for table in markdown_tables(block):
        headers = set(table["headers"])
        if not required_headers.issubset(headers):
            continue
        return [row for row in table["rows"] if all(row.get(header, "").strip() for header in required_headers)]
    return []


def extract_fine_grained_trace_units(stage_paths: dict[str, Path]) -> dict[str, list[dict[str, str]]]:
    stage_01_text = stage_paths["stage_01"].read_text(encoding="utf-8")
    stage_03_text = stage_paths["stage_03"].read_text(encoding="utf-8")
    stage_04_text = stage_paths["stage_04"].read_text(encoding="utf-8")
    return {
        "decision_trace_units": table_rows_from_block(
            block_text(stage_01_text, "decision_trace_registry"),
            {"trace_id", "adr_id", "decision_title", "upstream_reference", "downstream_artifact_id", "verification_hook"},
        ),
        "contract_trace_units": table_rows_from_block(
            block_text(stage_03_text, "contract_trace_registry"),
            {"trace_id", "trace_subject", "subject_type", "owning_module", "downstream_artifact_id", "verification_hook"},
        ),
        "rbi_trace_units": table_rows_from_block(
            block_text(stage_04_text, "rbi_trace_registry"),
            {"trace_id", "rbi_id", "bound_wp", "downstream_artifact_id", "verification_hook", "handoff_rule"},
        ),
        "replay_trace_units": table_rows_from_block(
            block_text(stage_04_text, "verification_replay_evidence"),
            {
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
            },
        ),
    }


def scenario_trace_rows(stage_03_text: str) -> list[dict[str, str]]:
    return table_rows_from_block(
        block_text(stage_03_text, "scenario_coverage_matrix"),
        {
            "scenario",
            "actors",
            "entities",
            "modules",
            "contracts / endpoints",
            "failure_note",
            "acceptance_criteria",
            "measurement_hook",
        },
    )


def append_unique_coverage_item(bucket: list[dict[str, str]], *, artifact_id: str, mode: str) -> None:
    cleaned_id = artifact_id.strip()
    cleaned_mode = mode.strip() or "explicit"
    if not cleaned_id:
        return
    if any(item["artifact_id"] == cleaned_id and item["mode"] == cleaned_mode for item in bucket):
        return
    bucket.append({"artifact_id": cleaned_id, "mode": cleaned_mode})


def phase1_unit_is_covered(unit_type: str, coverage: dict[str, list[dict[str, str]]]) -> bool:
    if unit_type == "epic":
        return bool(coverage["decision_trace_units"] or coverage["scenario_rows"] or coverage["replay_trace_units"])
    if unit_type in {"primary-user-story", "use-case"}:
        return bool(coverage["scenario_rows"] or coverage["replay_trace_units"])
    if unit_type == "requirement":
        return bool(
            coverage["decision_trace_units"]
            or coverage["contract_trace_units"]
            or coverage["rbi_trace_units"]
            or coverage["replay_trace_units"]
            or coverage["scenario_rows"]
        )
    if unit_type == "acceptance-criteria":
        return bool(coverage["scenario_rows"] or coverage["contract_trace_units"] or coverage["replay_trace_units"])
    return any(coverage.values())


def phase1_unit_has_explicit_binding(unit_type: str, coverage: dict[str, list[dict[str, str]]]) -> bool:
    relevant: list[dict[str, str]] = []
    if unit_type == "epic":
        relevant.extend(coverage["decision_trace_units"])
        relevant.extend(coverage["scenario_rows"])
        relevant.extend(coverage["replay_trace_units"])
    elif unit_type in {"primary-user-story", "use-case"}:
        relevant.extend(coverage["scenario_rows"])
        relevant.extend(coverage["replay_trace_units"])
    elif unit_type == "requirement":
        relevant.extend(coverage["decision_trace_units"])
        relevant.extend(coverage["contract_trace_units"])
        relevant.extend(coverage["rbi_trace_units"])
        relevant.extend(coverage["replay_trace_units"])
        relevant.extend(coverage["scenario_rows"])
    elif unit_type == "acceptance-criteria":
        relevant.extend(coverage["scenario_rows"])
        relevant.extend(coverage["contract_trace_units"])
        relevant.extend(coverage["replay_trace_units"])
    else:
        for values in coverage.values():
            relevant.extend(values)
    return any(item["mode"] == "explicit" for item in relevant)


def build_phase1_phase2_coverage_report(
    *,
    phase1_prd: Path,
    stage_03: Path,
    resolution_report: dict[str, Any],
) -> dict[str, Any]:
    phase1_units = extract_phase1_trace_units(phase1_prd.read_text(encoding="utf-8"))
    contract_rows = phase1_phase2_design_contract_rows(phase1_units)
    coverage_rows_by_id: dict[str, dict[str, Any]] = {}

    for contract_row in contract_rows:
        coverage_rows_by_id[contract_row["phase1_trace_id"]] = {
            **contract_row,
            "decision_trace_units": [],
            "contract_trace_units": [],
            "rbi_trace_units": [],
            "replay_trace_units": [],
            "scenario_rows": [],
        }

    row_group_to_bucket = {
        "decision_trace_units": "decision_trace_units",
        "contract_trace_units": "contract_trace_units",
        "rbi_trace_units": "rbi_trace_units",
        "replay_trace_units": "replay_trace_units",
    }

    for row in resolution_report.get("rows", []):
        bucket_name = row_group_to_bucket.get(str(row.get("row_group", "")).strip())
        artifact_id = str(row.get("artifact_id", "")).strip()
        mode = str(row.get("mode", "")).strip() or "missing"
        if not bucket_name or not artifact_id:
            continue
        for phase1_id in row.get("phase1_upstream_trace_ids", []):
            key = str(phase1_id).strip()
            if key not in coverage_rows_by_id:
                continue
            append_unique_coverage_item(coverage_rows_by_id[key][bucket_name], artifact_id=artifact_id, mode=mode)

    for scenario_row in scenario_trace_rows(stage_03.read_text(encoding="utf-8")):
        explicit_upstream_ids = [
            trace_id for trace_id in split_trace_ids(str(scenario_row.get("upstream_trace_ids", ""))) if trace_id.startswith("P1-")
        ]
        if not explicit_upstream_ids:
            continue
        scenario_name = str(scenario_row.get("scenario", "")).strip()
        for phase1_id in explicit_upstream_ids:
            if phase1_id not in coverage_rows_by_id:
                continue
            append_unique_coverage_item(
                coverage_rows_by_id[phase1_id]["scenario_rows"],
                artifact_id=scenario_name or "unnamed-scenario",
                mode="explicit",
            )

    rows: list[dict[str, Any]] = []
    type_summary: dict[str, dict[str, int]] = {}
    for phase1_id in [row["phase1_trace_id"] for row in contract_rows]:
        entry = coverage_rows_by_id[phase1_id]
        coverage = {
            "decision_trace_units": entry["decision_trace_units"],
            "contract_trace_units": entry["contract_trace_units"],
            "rbi_trace_units": entry["rbi_trace_units"],
            "replay_trace_units": entry["replay_trace_units"],
            "scenario_rows": entry["scenario_rows"],
        }
        covered = phase1_unit_is_covered(str(entry.get("unit_type", "")), coverage)
        explicit_bound = phase1_unit_has_explicit_binding(str(entry.get("unit_type", "")), coverage)
        coverage_status = "pass" if covered and explicit_bound else "inferred-only" if covered else "missing"
        gap_note = (
            "none"
            if coverage_status == "pass"
            else "coverage exists only by inference; add explicit `upstream_trace_ids` to Stage-01/03/04 rows"
            if coverage_status == "inferred-only"
            else "no qualifying Phase-2 design surface is explicitly bound to this Phase-1 trace unit"
        )
        row = {
            "phase1_trace_id": phase1_id,
            "source_id": entry["source_id"],
            "unit_type": entry["unit_type"],
            "summary": entry["summary"],
            "expected_phase2_surfaces": entry["expected_phase2_surfaces"],
            "coverage_expectation": entry["coverage_expectation"],
            "decision_trace_units": ", ".join(item["artifact_id"] for item in entry["decision_trace_units"]) or "",
            "contract_trace_units": ", ".join(item["artifact_id"] for item in entry["contract_trace_units"]) or "",
            "scenario_rows": ", ".join(item["artifact_id"] for item in entry["scenario_rows"]) or "",
            "replay_trace_units": ", ".join(item["artifact_id"] for item in entry["replay_trace_units"]) or "",
            "rbi_trace_units": ", ".join(item["artifact_id"] for item in entry["rbi_trace_units"]) or "",
            "coverage_status": coverage_status,
            "gap_note": gap_note,
        }
        rows.append(row)

        unit_type = str(entry.get("unit_type", "unknown"))
        bucket = type_summary.setdefault(unit_type, {"total": 0, "pass": 0, "inferred_only": 0, "missing": 0})
        bucket["total"] += 1
        bucket[coverage_status.replace("-", "_")] += 1

    pass_rows = sum(1 for row in rows if row["coverage_status"] == "pass")
    inferred_only_rows = sum(1 for row in rows if row["coverage_status"] == "inferred-only")
    missing_rows = sum(1 for row in rows if row["coverage_status"] == "missing")
    overall_verdict = "pass" if missing_rows == 0 and inferred_only_rows == 0 else "fail"
    return {
        "summary": {
            "total_phase1_trace_units": len(rows),
            "pass_rows": pass_rows,
            "inferred_only_rows": inferred_only_rows,
            "missing_rows": missing_rows,
            "overall_verdict": overall_verdict,
            "type_breakdown": type_summary,
        },
        "rows": rows,
    }


def analyze_phase1_phase2_coverage_contract(
    *,
    phase1_prd: Path,
    stage_paths: dict[str, Path],
) -> dict[str, Any]:
    fine_grained_trace_units = extract_fine_grained_trace_units(stage_paths)
    resolution_report = build_phase2_phase1_resolution_report(
        phase1_prd=phase1_prd,
        fine_grained_trace_units=fine_grained_trace_units,
    )
    coverage_report = build_phase1_phase2_coverage_report(
        phase1_prd=phase1_prd,
        stage_03=stage_paths["stage_03"],
        resolution_report=resolution_report,
    )
    return {
        "phase1_prd": str(phase1_prd),
        "resolution_report": resolution_report,
        "coverage_report": coverage_report,
        "verdict": coverage_report["summary"]["overall_verdict"],
    }
