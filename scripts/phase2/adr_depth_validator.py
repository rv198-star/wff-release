#!/usr/bin/env python3
"""
Warning-level ADR depth validation for Phase-2 Stage-01 outputs.
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


COMPARATIVE_SIGNAL_RE = re.compile(
    r"\b(?:vs\.?|versus|compared to|faster|slower|higher|lower|more|less|simpler|heavier|lighter|stronger|weaker|better|worse|because|trade[- ]?off|latency|throughput|capacity|cost|risk|complexity|fit)\b",
    re.IGNORECASE,
)
SCOPE_SIGNAL_RE = re.compile(
    r"(?:\bfirst[- ]wave\b|\bfirst[- ]pass\b|\bphase[- ]\d+\b|\btenant\b|\boperator\b|\bpublic[- ]boundary\b|\bp95\b|\bp99\b|\bms\b|\bsec(?:ond)?s?\b|\bday?s?\b|\bweek?s?\b|\bmonth?s?\b|\bquarter\b|\b[0-9]+(?:\.[0-9]+)?\b|%)",
    re.IGNORECASE,
)
CONSTRAINT_SIGNAL_RE = re.compile(
    r"\b(?:trust|replay|review|latency|throughput|capacity|cost|security|compliance|rollback|operability|migration|integration|vendor|reliability)\b",
    re.IGNORECASE,
)


def validate_adr_block(block: str) -> dict[str, Any]:
    from phase2.phase2_quality_check import (
        extract_structured_block,
        extract_structured_field,
        is_placeholder_like,
        word_count,
    )

    items: list[dict[str, Any]] = []
    for match in re.finditer(r"^\s*- (adr_[^:\n]+):\n((?:^\s{2,}.*\n?)*)", block, flags=re.MULTILINE):
        entry_key = match.group(1).strip().strip("`")
        entry = match.group(2)
        ad_id = extract_structured_field(entry, "ad_id")
        title = extract_structured_field(entry, "title")
        decision = extract_structured_field(entry, "decision")
        evidence = extract_structured_field(entry, "evidence")
        consequences = extract_structured_field(entry, "consequences")
        alternatives_block = extract_structured_block(entry, "alternatives_considered")
        alternative_count = alternatives_block.count("alternative_name:")
        rejected_count = alternatives_block.count("rejected_because:")
        comparative_signal_count = len(COMPARATIVE_SIGNAL_RE.findall(alternatives_block))
        constraint_signal_count = len(CONSTRAINT_SIGNAL_RE.findall(f"{decision} {alternatives_block}"))
        consequence_scope_signal_count = len(SCOPE_SIGNAL_RE.findall(consequences))

        checks = [
            {
                "name": "real_alternatives",
                "current": alternative_count,
                "minimum": 2,
                "passed": alternative_count >= 2 and rejected_count >= 2,
                "reason": "alternatives_considered should contain at least two named alternatives with explicit rejection reasons",
            },
            {
                "name": "comparative_reasoning_signal",
                "current": comparative_signal_count,
                "minimum": 2,
                "passed": comparative_signal_count >= 2,
                "reason": "alternatives should show actual comparison language rather than rubber-stamp naming only",
            },
            {
                "name": "decision_and_evidence_specificity",
                "current": min(word_count(decision), word_count(evidence)),
                "minimum": 6,
                "passed": word_count(decision) >= 8
                and word_count(evidence) >= 6
                and not is_placeholder_like(decision)
                and not is_placeholder_like(evidence),
                "reason": "decision and evidence should be specific enough to explain why the ADR exists",
            },
            {
                "name": "consequences_scoped",
                "current": consequence_scope_signal_count,
                "minimum": 1,
                "passed": word_count(consequences) >= 14
                and consequence_scope_signal_count >= 1
                and not is_placeholder_like(consequences),
                "reason": "consequences should include scope, time, capacity, or rollout qualifiers instead of generic pros/cons",
            },
            {
                "name": "constraint_closure_signal",
                "current": constraint_signal_count,
                "minimum": 1,
                "passed": constraint_signal_count >= 1,
                "reason": "decision and alternatives should expose the dominant constraint that closed the choice",
            },
        ]
        items.append(
            {
                "entry_key": entry_key,
                "ad_id": ad_id or entry_key,
                "title": title,
                "checks": checks,
                "passed": all(check["passed"] for check in checks),
            }
        )

    return {
        "applied": True,
        "severity": "warning",
        "items": items,
        "passed": bool(items) and all(item["passed"] for item in items),
        "missing": not bool(items),
    }


def validate_file(path: Path) -> dict[str, Any]:
    from phase2.phase2_quality_check import block_text

    text = path.read_text(encoding="utf-8")
    block = block_text(text, "key_architecture_decisions")
    result = validate_adr_block(block)
    result["path"] = str(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ADR depth signals in a Stage-01 output")
    parser.add_argument("stage_01")
    args = parser.parse_args()

    result = validate_file(Path(args.stage_01).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
