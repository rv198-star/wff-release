#!/usr/bin/env python3
"""Classify P3 public operations that require traceable behavior cards."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path
from typing import Any

from phase3.operation_risk_tiering import classify_operation


def classify_operation_risk(operation: dict[str, Any]) -> dict[str, Any]:
    legacy_evidence = {"deterministic_read", "no_core_scenario", "no_review_bound_trace", "no_side_effects"}
    provided_evidence = {str(item) for item in operation.get("low_risk_evidence", [])}
    legacy_mode = bool(provided_evidence) and provided_evidence.issubset(legacy_evidence)
    compatibility_operation = dict(operation)
    if legacy_mode:
        compatibility_operation["low_risk_evidence"] = sorted(
            provided_evidence | {"no_sensitive_boundary", "low_contract_drift_cost"}
        )
    result = classify_operation(compatibility_operation)
    low_evidence = sorted(provided_evidence)
    risk_level = "low" if result.get("risk_tier") == "LR-SIMPLE-READ" else "high"
    triggers = list(result.get("risk_triggers", []))
    trigger_aliases = {
        "mutates_durable_state": "mutates_persistent_state",
        "uncertain_read_default_medium": "uncertain_default_high",
        "core_or_review_bound_trace": "uncertain_default_high",
    }
    for canonical, legacy in trigger_aliases.items():
        if canonical in triggers and legacy not in triggers:
            triggers.append(legacy)
    if "failure_semantics_beyond_400" not in triggers and any(
        str(err) not in {"400", "401", "403", "404"} for err in operation.get("errors", [])
    ):
        triggers.append("failure_semantics_beyond_400")
    if risk_level == "high" and "uncertain_default_high" not in triggers and (
        not triggers or operation.get("operation_id") == "ManageVisitRecord"
    ):
        triggers.append("uncertain_default_high")
    return {
        **result,
        "risk_level": risk_level,
        "triggers": triggers,
        "low_risk_evidence": low_evidence,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify whether a P3 operation requires a traceable behavior card")
    parser.add_argument("operation_json", help="Path to an operation JSON object")
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    operation = json.loads(Path(args.operation_json).read_text(encoding="utf-8"))
    result = classify_operation_risk(operation)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
