#!/usr/bin/env python3
"""
Resolve Phase-2 trace rows back to Phase-1 trace units.

This supports both explicit references via `upstream_trace_ids` and a conservative
fallback inference path for older Phase-2 artifacts that still use prose-only
upstream references.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from phase1.phase1_trace_units import extract_phase1_trace_units


PHASE1_TRACE_ID_PATTERN = re.compile(r"\bP1-(?:PRD-MAIN-[0-9]{4}|EP-[0-9]{3}|US-[0-9]{3}|UC-[0-9]{3}|REQ-[0-9]{3}|AC-[0-9]{3})\b")
PHASE2_FINE_GRAINED_TRACE_PATTERN = re.compile(
    r"^(?:P2-)?(?:DTR-[0-9]+|CTR-[0-9]+|RT-[0-9]+|RP-[0-9]+|DEC-[A-Z0-9]+(?:-[A-Z0-9]+)*|REPLAY-[A-Z0-9]+(?:-[A-Z0-9]+)*|RISK-[A-Z0-9]+(?:-[A-Z0-9]+)*)$"
)
GENERIC_TRACE_ID_PATTERN = re.compile(
    r"\b(?:P1-(?:PRD-MAIN-[0-9]{4}|EP-[0-9]{3}|US-[0-9]{3}|UC-[0-9]{3}|REQ-[0-9]{3}|AC-[0-9]{3})|P2-[A-Z0-9]+(?:-[A-Z0-9]+)+|[A-Z]{3,}(?:-[A-Z0-9]+)+|RBI-[0-9]+|WP-[A-Z0-9]+)\b"
)
TRACE_ROW_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "decision_trace_units": ("upstream_reference", "decision_title", "verification_hook"),
    "contract_trace_units": ("trace_subject", "verification_hook"),
    "rbi_trace_units": ("verification_hook", "handoff_rule", "rbi_id", "bound_wp"),
    "replay_trace_units": ("scenario_or_contract", "source_artifacts", "expected_outcome", "observed_outcome", "linked_rbi_or_wp"),
}

STOPWORDS = {
    "stage",
    "phase",
    "trace",
    "registry",
    "hook",
}


def clean_value(value: str) -> str:
    return value.strip().strip("`").strip()


def canonicalize_phase2_trace_artifact_id(value: str) -> str:
    raw = clean_value(value)
    if not raw:
        return ""
    if PHASE2_FINE_GRAINED_TRACE_PATTERN.fullmatch(raw):
        return raw if raw.startswith("P2-") else f"P2-{raw}"
    return raw


def phase2_trace_id_aliases(value: str) -> list[str]:
    canonical = canonicalize_phase2_trace_artifact_id(value)
    aliases = [canonical]
    if canonical.startswith("P2-"):
        aliases.append(canonical[3:])
    return list(dict.fromkeys(alias for alias in aliases if alias))


def split_trace_ids(value: str) -> list[str]:
    return list(
        dict.fromkeys(canonicalize_phase2_trace_artifact_id(match.group(0)) for match in GENERIC_TRACE_ID_PATTERN.finditer(value or ""))
    )


def normalize_text(value: str) -> str:
    raw = clean_value(value).lower()
    raw = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    raw = raw.replace("_", " ").replace("-", " ")
    return " ".join(re.findall(r"[a-z0-9]+", raw))


def normalized_tokens(value: str) -> set[str]:
    return {
        token
        for token in normalize_text(value).split()
        if len(token) > 2 and token not in STOPWORDS
    }


def phase1_catalog_from_prd(phase1_prd: Path) -> list[dict[str, str]]:
    text = phase1_prd.read_text(encoding="utf-8")
    units = extract_phase1_trace_units(text)
    catalog: list[dict[str, str]] = []
    for rows in units.values():
        for row in rows:
            catalog.append(
                {
                    "trace_id": row["trace_id"],
                    "source_id": row.get("source_id", ""),
                    "unit_type": row.get("unit_type", ""),
                    "summary": row.get("summary", ""),
                    "source_anchor": row.get("source_anchor", ""),
                }
            )
    return catalog


def explicit_upstream_trace_ids(row: dict[str, str]) -> list[str]:
    candidates = split_trace_ids(row.get("upstream_trace_ids", ""))
    if candidates:
        return candidates
    embedded = split_trace_ids(row.get("upstream_reference", ""))
    return embedded


def row_text_for_matching(row: dict[str, str], fields: Sequence[str]) -> str:
    return "\n".join(clean_value(row.get(field, "")) for field in fields if clean_value(row.get(field, "")))


def texts_overlap(left: str, right: str) -> bool:
    left_normalized = normalize_text(left)
    right_normalized = normalize_text(right)
    if not left_normalized or not right_normalized:
        return False
    if left_normalized in right_normalized or right_normalized in left_normalized:
        return True
    shared = normalized_tokens(left) & normalized_tokens(right)
    return len(shared) >= 2


def infer_phase1_trace_ids(row: dict[str, str], catalog: Sequence[dict[str, str]], fields: Sequence[str]) -> list[str]:
    reference_text = row_text_for_matching(row, fields)
    if not reference_text:
        return []
    explicit_phase1_ids = [trace_id for trace_id in split_trace_ids(reference_text) if trace_id.startswith("P1-")]
    if explicit_phase1_ids:
        return explicit_phase1_ids

    reference_tokens = normalized_tokens(reference_text)
    reference_normalized = normalize_text(reference_text)
    if not reference_tokens:
        return []

    scored: list[tuple[int, str]] = []
    for unit in catalog:
        unit_trace_id = unit["trace_id"]
        unit_text = " ".join(
            value for value in (unit.get("source_id", ""), unit.get("summary", ""), unit.get("unit_type", "")) if value
        )
        unit_tokens = normalized_tokens(unit_text)
        if not unit_tokens:
            continue
        score = len(reference_tokens & unit_tokens)
        if unit.get("summary") and normalize_text(unit["summary"]) and normalize_text(unit["summary"]) in reference_normalized:
            score += 3
        if unit.get("source_id") and unit["source_id"].lower() in reference_text.lower():
            score += 2
        if unit.get("unit_type") == "acceptance-criteria" and "must" in reference_normalized:
            score += 1
        if score <= 0:
            continue
        scored.append((score, unit_trace_id))

    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored:
        return []
    best_score = scored[0][0]
    threshold = max(2, best_score - 1)
    matches = [trace_id for score, trace_id in scored if score >= threshold][:4]
    return list(dict.fromkeys(matches))


def resolve_row_upstream_trace_ids(
    row: dict[str, str],
    *,
    row_group: str,
    phase1_catalog: Sequence[dict[str, str]],
) -> dict[str, object]:
    explicit_ids = explicit_upstream_trace_ids(row)
    explicit_phase1_ids = [trace_id for trace_id in explicit_ids if trace_id.startswith("P1-")]
    inferred_phase1_ids = (
        []
        if explicit_phase1_ids
        else infer_phase1_trace_ids(row, phase1_catalog, TRACE_ROW_TEXT_FIELDS.get(row_group, tuple(row.keys())))
    )
    resolved_phase1_ids = explicit_phase1_ids or inferred_phase1_ids
    if explicit_phase1_ids:
        mode = "explicit"
    elif inferred_phase1_ids:
        mode = "inferred"
    else:
        mode = "missing"
    return {
        "mode": mode,
        "explicit_upstream_trace_ids": explicit_ids,
        "phase1_upstream_trace_ids": resolved_phase1_ids,
    }


def build_phase2_phase1_resolution_report(
    *,
    phase1_prd: Path,
    fine_grained_trace_units: dict[str, list[dict[str, str]]],
) -> dict[str, object]:
    phase1_catalog = phase1_catalog_from_prd(phase1_prd)
    rows: list[dict[str, object]] = []
    rows_by_id: dict[str, dict[str, object]] = {}
    for row_group, units in fine_grained_trace_units.items():
        id_field = "replay_id" if row_group == "replay_trace_units" else "trace_id"
        for row in units:
            resolution = resolve_row_upstream_trace_ids(row, row_group=row_group, phase1_catalog=phase1_catalog)
            row_entry = {
                "row_group": row_group,
                "artifact_id": canonicalize_phase2_trace_artifact_id(row.get(id_field, "")),
                "mode": resolution["mode"],
                "explicit_upstream_trace_ids": resolution["explicit_upstream_trace_ids"],
                "phase1_upstream_trace_ids": resolution["phase1_upstream_trace_ids"],
                "row_payload": row,
            }
            rows.append(row_entry)
            rows_by_id[str(row_entry["artifact_id"])] = row_entry

    for row in rows:
        if row["row_group"] != "contract_trace_units" or row["phase1_upstream_trace_ids"]:
            continue
        contract_text = row_text_for_matching(row["row_payload"], TRACE_ROW_TEXT_FIELDS["contract_trace_units"])
        inherited_ids: list[str] = []
        for candidate in rows:
            if candidate["row_group"] != "decision_trace_units" or not candidate["phase1_upstream_trace_ids"]:
                continue
            decision_text = row_text_for_matching(candidate["row_payload"], TRACE_ROW_TEXT_FIELDS["decision_trace_units"])
            if texts_overlap(contract_text, decision_text):
                inherited_ids.extend(str(item) for item in candidate["phase1_upstream_trace_ids"])
        if inherited_ids:
            row["phase1_upstream_trace_ids"] = list(dict.fromkeys(inherited_ids))
            row["mode"] = "inherited"

    for row in rows:
        if row["row_group"] != "replay_trace_units" or row["phase1_upstream_trace_ids"]:
            continue
        replay_text = row_text_for_matching(row["row_payload"], TRACE_ROW_TEXT_FIELDS["replay_trace_units"])
        inherited_ids = []
        for candidate in rows:
            if candidate["row_group"] != "contract_trace_units" or not candidate["phase1_upstream_trace_ids"]:
                continue
            contract_text = row_text_for_matching(candidate["row_payload"], TRACE_ROW_TEXT_FIELDS["contract_trace_units"])
            if texts_overlap(replay_text, contract_text):
                inherited_ids.extend(str(item) for item in candidate["phase1_upstream_trace_ids"])
        if inherited_ids:
            row["phase1_upstream_trace_ids"] = list(dict.fromkeys(inherited_ids))
            row["mode"] = "inherited"

    for row in rows:
        if row["row_group"] != "rbi_trace_units" or row["phase1_upstream_trace_ids"]:
            continue
        replay_inherited_ids: list[str] = []
        rbi_id = clean_value(str(row["row_payload"].get("rbi_id", "")))
        bound_wp = clean_value(str(row["row_payload"].get("bound_wp", "")))
        for candidate in rows:
            if candidate["row_group"] != "replay_trace_units" or not candidate["phase1_upstream_trace_ids"]:
                continue
            linked_refs = split_trace_ids(str(candidate["row_payload"].get("linked_rbi_or_wp", "")))
            if rbi_id and rbi_id in linked_refs:
                replay_inherited_ids.extend(str(item) for item in candidate["phase1_upstream_trace_ids"])
            elif bound_wp and bound_wp in linked_refs:
                replay_inherited_ids.extend(str(item) for item in candidate["phase1_upstream_trace_ids"])
        if replay_inherited_ids:
            row["phase1_upstream_trace_ids"] = list(dict.fromkeys(replay_inherited_ids))
            row["mode"] = "inherited"
            continue
        rbi_text = row_text_for_matching(row["row_payload"], TRACE_ROW_TEXT_FIELDS["rbi_trace_units"])
        contract_inherited_ids: list[str] = []
        for candidate in rows:
            if candidate["row_group"] != "contract_trace_units" or not candidate["phase1_upstream_trace_ids"]:
                continue
            contract_text = row_text_for_matching(candidate["row_payload"], TRACE_ROW_TEXT_FIELDS["contract_trace_units"])
            if texts_overlap(rbi_text, contract_text):
                contract_inherited_ids.extend(str(item) for item in candidate["phase1_upstream_trace_ids"])
        if contract_inherited_ids:
            row["phase1_upstream_trace_ids"] = list(dict.fromkeys(contract_inherited_ids))
            row["mode"] = "inherited"

    explicit_count = sum(1 for row in rows if row["mode"] == "explicit")
    inferred_count = sum(1 for row in rows if row["mode"] == "inferred")
    inherited_count = sum(1 for row in rows if row["mode"] == "inherited")
    missing_count = sum(1 for row in rows if row["mode"] == "missing")
    return {
        "rows": [
            {
                "row_group": row["row_group"],
                "artifact_id": row["artifact_id"],
                "mode": row["mode"],
                "explicit_upstream_trace_ids": row["explicit_upstream_trace_ids"],
                "phase1_upstream_trace_ids": row["phase1_upstream_trace_ids"],
            }
            for row in rows
        ],
        "summary": {
            "total_rows": len(rows),
            "explicit_rows": explicit_count,
            "inferred_rows": inferred_count,
            "inherited_rows": inherited_count,
            "missing_rows": missing_count,
        },
    }
