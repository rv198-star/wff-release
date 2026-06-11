"""Build Phase-2 structured operation behavior semantics.

This artifact makes operation-bound behavior semantics explicit for Phase-3.
It is authored at P2 from existing P2 design artifacts; P3 should consume it
before falling back to markdown/mermaid heuristics.
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

try:
    from phase3.phase3_operation_semantics import extract_operation_semantics
except ModuleNotFoundError:  # pragma: no cover - package import path for pytest
    from scripts.phase3_operation_semantics import extract_operation_semantics


def _read_phase2_markdown(phase2_root: Path) -> list[str]:
    return [path.read_text(encoding="utf-8", errors="ignore") for path in sorted(phase2_root.rglob("*.md")) if ".trace" not in path.parts]


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if cells and all(re.fullmatch(r"[-: ]+", cell) for cell in cells):
        return []
    return cells


def _snake_case(value: str) -> str:
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", value)
    return "_".join(word.lower() for word in words if word)


def _aggregate_from_operation(operation_id: str) -> str:
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", operation_id)
    if words and words[0].lower() in {"update", "get", "list", "manage", "create", "record", "start"}:
        words = words[1:]
    if words and words[-1].lower() == "status":
        words = words[:-1]
    return "".join(words) or operation_id


def _operation_contract_rows(source_texts: list[str]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    headers: list[str] = []
    for text in source_texts:
        for line in text.splitlines():
            cells = _split_table_row(line)
            if not cells:
                continue
            lowered = [cell.lower() for cell in cells]
            if (
                ("operation_id" in lowered or "endpoint_name" in lowered)
                and ("request_example" in lowered or "request_body_example" in lowered)
                and ("response_example" in lowered or "response_body_example" in lowered)
            ):
                headers = lowered
                continue
            if "aggregate_name" in lowered or "event_name" in lowered or "upstream_module" in lowered:
                headers = []
                continue
            if not headers or len(cells) < len(headers):
                continue
            row = dict(zip(headers, cells))
            operation_id = (row.get("operation_id", "") or row.get("endpoint_name", "")).strip()
            if operation_id:
                rows[operation_id] = row
    return rows


def _status_update_semantics(operation_id: str, row: dict[str, str] | None) -> dict[str, Any] | None:
    if not row or not operation_id.startswith("Update") or not operation_id.endswith("Status"):
        return None
    aggregate = _aggregate_from_operation(operation_id)
    request = row.get("request_example", "") or row.get("request_body_example", "")
    response = row.get("response_example", "") or row.get("response_body_example", "")
    combined = f"{request} {response}"
    evidence_keys = []
    aggregate_id = f"{_snake_case(aggregate)}_id"
    for key in (aggregate_id, "version", "trace_id", "tenant_id"):
        camel = "".join([part if index == 0 else part[:1].upper() + part[1:] for index, part in enumerate(key.split("_"))])
        if key in combined or camel in combined or key in {"version", "trace_id"}:
            evidence_keys.append(key)
    guard_conditions = []
    if "expectedVersion" in combined or "expected_version" in combined:
        guard_conditions.append("expectedVersion")
    status_values = re.findall(r'"status"\s*:\s*"([^"]+)"', combined)
    state_set = list(dict.fromkeys(status_values)) or ["updated"]
    return {
        "operation_id": operation_id,
        "status": "resolved",
        "operation_kind": "status-update",
        "owner_service": "",
        "aggregate": aggregate,
        "state_set": state_set,
        "trigger_events": [],
        "mutation_guard": f"apply bounded status update for {aggregate} with version guard",
        "terminal_or_failure_exit": f"reject missing {aggregate_id}, stale version, or invalid status update",
        "readonly_dependencies": [],
        "evidence_keys": evidence_keys,
        "guard_conditions": guard_conditions,
        "source_evidence": [" | ".join(row.values())],
    }



def _read_operation_semantics(operation_id: str, row: dict[str, str] | None) -> dict[str, Any] | None:
    if not row or not (operation_id.startswith("Get") or operation_id.startswith("List")):
        return None
    aggregate = _aggregate_from_operation(operation_id)
    if aggregate.endswith("Detail"):
        aggregate = aggregate[:-6]
    if aggregate.endswith("s") and operation_id.startswith("List"):
        aggregate = aggregate[:-1]
    request = row.get("request_example", "") or row.get("request_body_example", "")
    response = row.get("response_example", "") or row.get("response_body_example", "")
    combined = f"{request} {response}"
    evidence_keys = []
    aggregate_id = f"{_snake_case(aggregate)}_id"
    for key in (aggregate_id, "trace_id", "tenant_id"):
        camel = "".join([part if index == 0 else part[:1].upper() + part[1:] for index, part in enumerate(key.split("_"))])
        if key in combined or camel in combined or key == "trace_id":
            evidence_keys.append(key)
    operation_kind = "read-list" if operation_id.startswith("List") else "read-detail"
    return {
        "operation_id": operation_id,
        "status": "resolved",
        "operation_kind": operation_kind,
        "owner_service": "",
        "aggregate": aggregate,
        "state_set": [],
        "trigger_events": [],
        "mutation_guard": f"read-only projection for {aggregate}; do not mutate durable state",
        "terminal_or_failure_exit": f"reject missing {aggregate_id} or inaccessible read scope" if operation_kind == "read-detail" else f"return bounded {aggregate} list with stable trace evidence",
        "readonly_dependencies": [key for key in evidence_keys if key != aggregate_id],
        "evidence_keys": evidence_keys,
        "guard_conditions": [],
        "source_evidence": [" | ".join(row.values())],
    }

def _row_from_semantics(operation_id: str, semantics: dict[str, Any]) -> dict[str, Any]:
    if semantics.get("status") != "resolved":
        return {
            "operation_id": operation_id,
            "semantic_status": "review_bound",
            "source_authority": "p2-structured",
            "review_bound_reasons": list(semantics.get("review_bound_reasons", ["operation_semantics_not_found"])),
        }
    return {
        "operation_id": operation_id,
        "semantic_status": "resolved",
        "source_authority": "p2-structured",
        "owner_service": semantics.get("owner_service", ""),
        "aggregate": semantics.get("aggregate", ""),
        "state_set": semantics.get("state_set", []),
        "trigger_events": semantics.get("trigger_events", []),
        "mutation_guard": semantics.get("mutation_guard", ""),
        "terminal_or_failure_exit": semantics.get("terminal_or_failure_exit", ""),
        "readonly_dependencies": semantics.get("readonly_dependencies", []),
        "evidence_keys": semantics.get("evidence_keys", []),
        "guard_conditions": semantics.get("guard_conditions", []),
        "operation_kind": semantics.get("operation_kind", "lifecycle"),
        "source_evidence": semantics.get("source_evidence", []),
        "review_bound_reasons": [],
    }


def build_operation_semantic_payload(phase2_root: str | Path, operation_ids: list[str]) -> dict[str, Any]:
    root = Path(phase2_root)
    source_texts = _read_phase2_markdown(root)
    contract_rows = _operation_contract_rows(source_texts)
    rows = []
    for operation_id in operation_ids:
        semantics = extract_operation_semantics(operation_id, source_texts)
        if semantics.get("status") != "resolved":
            contract_row = contract_rows.get(operation_id)
            semantics = _status_update_semantics(operation_id, contract_row) or _read_operation_semantics(operation_id, contract_row) or semantics
        rows.append(_row_from_semantics(operation_id, semantics))
    return {
        "artifact": "operation-behavior-semantics",
        "schema_version": "v0.1",
        "source_authority": "p2-structured",
        "operations": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build P2 operation behavior semantics payload")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--operation-id", action="append", default=[])
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_operation_semantic_payload(args.phase2_root, args.operation_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
