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
    result = classify_operation(operation)
    low_evidence = sorted({str(item) for item in operation.get("low_risk_evidence", [])})
    risk_level = "low" if result.get("risk_tier") == "LR-SIMPLE-READ" else "high"
    return {
        **result,
        "risk_level": risk_level,
        "triggers": list(result.get("risk_triggers", [])),
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
        BROKEN
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
