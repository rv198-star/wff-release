#!/usr/bin/env python3
"""
Check structural drift between the frozen Phase-3 OpenAPI contract and a later implementation-facing spec.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path

from phase3.contract_tools import load_openapi_document


def compare_openapi_docs(baseline: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
    baseline_paths = baseline.get("paths", {})
    candidate_paths = candidate.get("paths", {})
    if not isinstance(baseline_paths, dict) or not isinstance(candidate_paths, dict):
        raise ValueError("both OpenAPI documents must contain a paths object")

    removed_operations: list[str] = []
    added_operations: list[str] = []
    changed_status_codes: list[dict[str, object]] = []

    def iter_operations(paths: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
        operations: dict[tuple[str, str], dict[str, object]] = {}
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                operations[(str(path), str(method).lower())] = operation
        return operations

    baseline_ops = iter_operations(baseline_paths)
    candidate_ops = iter_operations(candidate_paths)

    for key, baseline_operation in baseline_ops.items():
        path, method = key
        if key not in candidate_ops:
            removed_operations.append(f"{method.upper()} {path}")
            continue
        candidate_operation = candidate_ops[key]
        baseline_responses = baseline_operation.get("responses", {})
        candidate_responses = candidate_operation.get("responses", {})
        if not isinstance(baseline_responses, dict) or not isinstance(candidate_responses, dict):
            continue
        baseline_codes = sorted(str(code) for code in baseline_responses.keys())
        candidate_codes = sorted(str(code) for code in candidate_responses.keys())
        missing = [code for code in baseline_codes if code not in candidate_codes]
        added = [code for code in candidate_codes if code not in baseline_codes]
        if missing or added:
            changed_status_codes.append(
                {
                    "operation": f"{method.upper()} {path}",
                    "missing_status_codes": missing,
                    "added_status_codes": added,
                }
            )

    for key in candidate_ops:
        if key not in baseline_ops:
            path, method = key
            added_operations.append(f"{method.upper()} {path}")

    incompatible = bool(removed_operations or any(row["missing_status_codes"] for row in changed_status_codes))
    return {
        "verdict": "fail" if incompatible else "pass",
        "removed_operations": removed_operations,
        "added_operations": added_operations,
        "changed_status_codes": changed_status_codes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare a frozen OpenAPI document with a later candidate")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", help="Optional output path for the diff report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    baseline = load_openapi_document(Path(args.baseline).resolve())
    candidate = load_openapi_document(Path(args.candidate).resolve())
    report = compare_openapi_docs(baseline, candidate)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
