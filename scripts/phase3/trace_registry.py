#!/usr/bin/env python3
"""
Finalize the Phase-3 trace registry by binding Phase-2 trace surfaces to implementation artifacts.
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
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def initialize_phase3_trace_registry(test_trace_matrix: dict[str, Any]) -> dict[str, Any]:
    rows = test_trace_matrix.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("test trace matrix must contain rows")
    registry_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        registry_rows.append(
            {
                "source_id": str(row.get("source_id", "")).strip(),
                "source_type": str(row.get("source_type", "")).strip(),
                "source_subject": str(row.get("source_subject", "")).strip(),
                "upstream_trace_ids": list(row.get("upstream_trace_ids", [])),
                "linked_rbi_or_wp": list(row.get("linked_rbi_or_wp", [])),
                "test_targets": list(row.get("test_targets", [])),
                "implementation_targets": [],
                "work_packages": [],
                "binding_status": "pending-implementation",
                "verification_hook": str(row.get("verification_hook", "")).strip(),
            }
        )
    return {
        "rows": registry_rows,
        "summary": {
            "source_count": len(registry_rows),
            "pending_source_count": len(registry_rows),
            "resolved_source_count": 0,
        },
    }


def parse_bindings(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        return {}
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip()
        if not source_id:
            continue
        implementation_targets = sorted(
            {
                str(item).strip()
                for item in row.get("implementation_targets", [])
                if str(item).strip()
            }
        )
        work_packages = sorted({str(item).strip() for item in row.get("work_packages", []) if str(item).strip()})
        runtime_evidence_refs = sorted(
            {str(item).strip() for item in row.get("runtime_evidence_refs", []) if str(item).strip()}
        )
        mapping[source_id.upper()] = {
            "implementation_targets": implementation_targets,
            "work_packages": work_packages,
            "runtime_evidence_refs": runtime_evidence_refs,
            "binding_status": str(row.get("binding_status", "")).strip() or (
                "bound" if implementation_targets else "unbound"
            ),
        }
    return mapping


def finalize_trace_registry(
    *,
    test_trace_matrix: dict[str, Any],
    implementation_bindings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = test_trace_matrix.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("test trace matrix must contain rows")

    binding_by_source = parse_bindings(implementation_bindings)
    final_rows: list[dict[str, Any]] = []
    unresolved_trace_ids: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "")).strip().upper()
        source_type = str(row.get("source_type", "")).strip()
        test_targets = sorted({str(item).strip() for item in row.get("test_targets", []) if str(item).strip()})
        binding = binding_by_source.get(source_id, {})
        implementation_targets = list(binding.get("implementation_targets", []))
        work_packages = list(binding.get("work_packages", []))
        runtime_evidence_refs = list(binding.get("runtime_evidence_refs", []))
        resolved = bool(test_targets and implementation_targets)
        if not resolved:
            unresolved_trace_ids.append(source_id)
        final_rows.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "source_subject": str(row.get("source_subject", "")).strip(),
                "upstream_trace_ids": row.get("upstream_trace_ids", []),
                "verification_hook": str(row.get("verification_hook", "")).strip(),
                "test_targets": test_targets,
                "implementation_targets": implementation_targets,
                "work_packages": work_packages,
                "runtime_evidence_refs": runtime_evidence_refs,
                "binding_status": str(binding.get("binding_status", "bound" if resolved else "unbound")),
                "final_resolution": "resolved" if resolved else "unresolved",
            }
        )

    source_type_breakdown: dict[str, int] = {}
    for row in final_rows:
        source_type_breakdown[row["source_type"]] = source_type_breakdown.get(row["source_type"], 0) + 1

    return {
        "rows": final_rows,
        "summary": {
            "source_count": len(final_rows),
            "resolved_source_count": len(final_rows) - len(unresolved_trace_ids),
            "unresolved_source_count": len(unresolved_trace_ids),
            "unresolved_trace_ids": unresolved_trace_ids,
            "source_type_breakdown": source_type_breakdown,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finalize the Phase-3 trace registry")
    parser.add_argument("--test-trace-matrix", required=True)
    parser.add_argument("--implementation-bindings")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = finalize_trace_registry(
        test_trace_matrix=load_json(Path(args.test_trace_matrix).resolve()),
        implementation_bindings=load_json(Path(args.implementation_bindings).resolve()) if args.implementation_bindings else None,
    )
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), **report["summary"]}, ensure_ascii=False))
    return 0 if not report["summary"]["unresolved_trace_ids"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
