#!/usr/bin/env python3
"""Validate traceable behavior cards before tests and implementation consume them."""

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


REQUIRED_SECTIONS = [
    "Traceability Binding",
    "Business Intent",
    "Public Contract",
    "Human-Readable Pseudocode",
    "Error Trigger Table",
    "State And Persistence Effects",
    "Test Mapping",
    "Implementation Mapping",
    "Review-Bound Items",
]
TRACE_ID_RE = re.compile(r"\bP[12]-(?:US|UC|REQ|AC|DTR|CTR|RP|RT)-\d+\b")


def _section(text: str, title: str) -> str:
    pattern = re.compile(rf"^##\s+\d+\.\s+{re.escape(title)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^##\s+\d+\.\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end]


def _metadata_value(markdown: str, key: str) -> str:
    match = re.search(rf"^[-*]\s*{re.escape(key)}:\s*([^\n]+)$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _metadata_list(markdown: str, key: str) -> list[str]:
    value = _metadata_value(markdown, key)
    if not value or value == "none":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _source_requirement_statuses(markdown: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    in_block = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped == "- source_requirement_statuses:":
            in_block = True
            continue
        if in_block and stripped.startswith("- ") and ":" in stripped:
            key, value = stripped[2:].split(":", 1)
            statuses[key.strip()] = value.strip()
            continue
        if in_block and stripped.startswith("- "):
            break
    return statuses


def _pseudocode_is_weak(pseudocode: str) -> bool:
    steps = re.findall(r"^\s*\d+\.\s+(.+)$", pseudocode, re.MULTILINE)
    if len(steps) < 4:
        return True
    weak_words = {"call service", "save", "return", "todo"}
    joined = " ".join(step.lower().strip(". ") for step in steps)
    if all(word in joined for word in ("call service", "save", "return")) and len(joined) < 120:
        return True
    return any(step.lower().strip(". ") in weak_words for step in steps)


def validate_behavior_card(
    markdown: str,
    *,
    high_risk: bool = True,
    resolvable_ids: set[str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    missing_sections = [section for section in REQUIRED_SECTIONS if not _section(markdown, section)]
    if missing_sections:
        blockers.append("missing_required_sections")

    trace_ids = sorted(set(TRACE_ID_RE.findall(markdown)))
    if high_risk and not any(item.startswith("P1-") for item in trace_ids):
        blockers.append("missing_p1_trace_ids")
    if high_risk and not any(item.startswith("P2-") for item in trace_ids):
        blockers.append("missing_p2_trace_ids")

    if resolvable_ids is not None:
        unresolved = [item for item in trace_ids if item not in resolvable_ids]
        if unresolved:
            blockers.append("unresolvable_upstream_ids")

    pseudocode = _section(markdown, "Human-Readable Pseudocode")
    if _pseudocode_is_weak(pseudocode):
        blockers.append("weak_pseudocode")

    normalized = markdown.lower()
    required_content = ["todo", "pending", "call service", "save", "return"]
    if normalized.count("todo") >= 2 or all(token in normalized for token in required_content[:1]):
        blockers.append("field_filled_only")

    if "source missing" in normalized or "exact operation-to-state binding missing" in normalized or "source precision" in normalized:
        warnings.append("anchor_precision_gap")

    operation_risk_row_status = _metadata_value(markdown, "operation_risk_row_status")
    if operation_risk_row_status == "p2_operation_risk_row_missing":
        blockers.append("p2_operation_risk_row_missing")
    if operation_risk_row_status == "risk_tier_mismatch":
        blockers.append("risk_tier_mismatch")
    required_source_types = _metadata_list(markdown, "required_source_types")
    source_requirement_statuses = _source_requirement_statuses(markdown)
    for source_type in required_source_types:
        if source_requirement_statuses.get(source_type) == "not_required":
            blockers.append("required_source_marked_not_required")

    trace_authority_match = re.search(r"^[-*]\s*trace_authority_status:\s*([^\n]+)$", markdown, re.MULTILINE)
    trace_authority_status = trace_authority_match.group(1).strip() if trace_authority_match else "unknown"
    if high_risk and trace_authority_status not in {"registry-bound", "unknown"}:
        warnings.append("trace_authority_not_registry_bound")

    return {
        "status": "fail" if blockers else "pass",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "trace_ids": trace_ids,
        "missing_sections": missing_sections,
        "trace_authority_status": trace_authority_status,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a P3 traceable behavior card")
    parser.add_argument("card_path")
    parser.add_argument("--high-risk", action="store_true", default=False)
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate_behavior_card(Path(args.card_path).read_text(encoding="utf-8"), high_risk=args.high_risk)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
