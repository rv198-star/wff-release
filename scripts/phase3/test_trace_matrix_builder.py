#!/usr/bin/env python3
"""
Build the Phase-3 test trace matrix from Stage-03/04 structured sources.
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

from phase3.contract_tools import (
    build_contract_trace_matches,
    camel_and_word_tokens,
    endpoint_rows_from_openapi_spec,
    parse_reference_cell,
    parse_api_endpoint_rows,
    parse_contract_trace_rows,
    parse_replay_rows,
    parse_scenario_rows,
    replay_test_filename,
    scenario_identifier,
    scenario_test_filename,
)
from phase3.contract_test_scaffolder import build_contract_test_target_lookup


def referenced_ids(text: str, prefix: str) -> list[str]:
    pattern = re.compile(rf"\b{prefix}-\d+\b", flags=re.IGNORECASE)
    return sorted({match.group(0).upper() for match in pattern.finditer(text)})


def resolve_replay_ref(replay_ref: str, replay_by_id: dict[str, str]) -> str | None:
    upper = replay_ref.upper()
    if upper in replay_by_id:
        return upper
    prefixed = f"P2-{upper}"
    if prefixed in replay_by_id:
        return prefixed
    return None


def endpoint_source_id(endpoint_name: str) -> str:
    return f"P3-EF-{re.sub(r'[^A-Z0-9]+', '', endpoint_name.upper())}"


def _extract_security_field(text: str, field_name: str) -> str:
    match = re.search(
        rf"{re.escape(field_name)}\s*:\s*(?:`([^`]+)`|([^\n]+))",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return (match.group(1) or match.group(2) or "").strip(" -`")


def build_security_decision_rows(esp_text: str) -> list[dict[str, object]]:
    lowered = esp_text.lower()
    has_token_lifecycle = "token" in lowered and any(token in lowered for token in ("refresh", "rotation", "lifetime"))
    has_session_boundary = "session" in lowered or "revocation" in lowered
    if not has_token_lifecycle:
        return []

    details = " ".join(
        part
        for part in [
            _extract_security_field(esp_text, "token_strategy"),
            _extract_security_field(esp_text, "token_lifetime"),
            _extract_security_field(esp_text, "refresh_mechanism"),
            _extract_security_field(esp_text, "revocation_approach"),
        ]
        if part
    )
    if not details and has_session_boundary:
        details = "token lifecycle, refresh token rotation, and session revocation posture"

    return [
        {
            "source_type": "security-decision",
            "source_id": "P2-SEC-AUTH-LIFECYCLE",
            "source_subject": "Token lifecycle and rotation posture",
            "test_type": "unit",
            "test_targets": ["tests/unit/api/foundation/runtime-foundation.unit.test.ts"],
            "upstream_trace_ids": [],
            "verification_hook": details or "token lifecycle and refresh token rotation remain explicit",
        }
    ]


def scenario_endpoint_refs(row: dict[str, object]) -> set[str]:
    raw = ""
    for key in ("contracts / endpoints", "contracts/endpoints", "contracts_or_endpoints"):
        if key in row:
            raw = str(row.get(key, ""))
            break
    return {item for item in parse_reference_cell(raw) if item}


def replay_mentions_endpoint(endpoint_name: str, replay_row: dict[str, object]) -> bool:
    operation_tokens = camel_and_word_tokens(endpoint_name)
    haystack = " ".join(
        [
            str(replay_row.get("scenario_or_contract", "")),
            str(replay_row.get("expected_outcome", "")),
            str(replay_row.get("observed_outcome", "")),
        ]
    )
    return bool(operation_tokens & camel_and_word_tokens(haystack))


def align_runtime_endpoint_rows(
    runtime_endpoint_rows: list[dict[str, object]],
    source_endpoint_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    source_by_method_path = {
        (str(row.get("method", "")).strip().upper(), str(row.get("path", "")).strip()): row
        for row in source_endpoint_rows
        if str(row.get("method", "")).strip() and str(row.get("path", "")).strip()
    }
    aligned_rows: list[dict[str, object]] = []
    for row in runtime_endpoint_rows:
        method = str(row.get("method", "")).strip().upper()
        path = str(row.get("path", "")).strip()
        source_row = source_by_method_path.get((method, path), {})
        source_endpoint_name = str(source_row.get("endpoint_name", "")).strip()
        aliases = []
        if source_endpoint_name and source_endpoint_name != str(row.get("endpoint_name", "")).strip():
            aliases.append(source_endpoint_name)
        aligned_rows.append({**row, "aliases": aliases})
    return aligned_rows


def endpoint_matches_scenario_refs(endpoint_row: dict[str, object], scenario_row: dict[str, object]) -> bool:
    refs = scenario_endpoint_refs(scenario_row)
    if not refs:
        return False
    endpoint_names = {
        str(endpoint_row.get("endpoint_name", "")).strip(),
        *[str(item).strip() for item in endpoint_row.get("aliases", []) if str(item).strip()],
    }
    return bool(endpoint_names & refs)


def replay_mentions_endpoint_row(endpoint_row: dict[str, object], replay_row: dict[str, object]) -> bool:
    names = [
        str(endpoint_row.get("endpoint_name", "")).strip(),
        *[str(item).strip() for item in endpoint_row.get("aliases", []) if str(item).strip()],
    ]
    return any(name and replay_mentions_endpoint(name, replay_row) for name in names)


def build_test_trace_matrix(
    *,
    esp_text: str,
    stage_03_text: str,
    stage_04_text: str,
    openapi_spec: dict[str, object] | None = None,
) -> dict[str, object]:
    source_endpoint_rows = parse_api_endpoint_rows(esp_text)
    runtime_endpoint_rows = endpoint_rows_from_openapi_spec(openapi_spec or {}) if openapi_spec else []
    endpoint_rows = (
        align_runtime_endpoint_rows(runtime_endpoint_rows, source_endpoint_rows)
        if runtime_endpoint_rows
        else source_endpoint_rows
    )
    contract_target_lookup = build_contract_test_target_lookup(
        [
            {
                "operation_id": str(row["endpoint_name"]),
                "method": str(row["method"]),
                "path": str(row["path"]),
            }
            for row in endpoint_rows
        ]
    )
    contract_rows = build_contract_trace_matches(parse_contract_trace_rows(stage_03_text), endpoint_rows)
    scenario_rows = parse_scenario_rows(stage_03_text)
    replay_rows = parse_replay_rows(stage_04_text)
    scenario_by_id = {
        scenario_identifier(str(row["scenario"]))[0]: str(row["scenario"]) for row in scenario_rows
    }
    replay_by_id = {str(row["replay_id"]).upper(): str(row["scenario_or_contract"]) for row in replay_rows}

    rows: list[dict[str, object]] = []
    unmatched_contract_trace_ids: list[str] = []

    for row in contract_rows:
        matched = list(row.get("matched_endpoints", []))
        scenario_refs = referenced_ids(str(row.get("verification_hook", "")), "SCN")
        replay_refs = referenced_ids(str(row.get("verification_hook", "")), "RP")
        test_targets = [
            f"tests/contracts/{contract_target_lookup[(endpoint_name, str(next(ep['method'] for ep in endpoint_rows if ep['endpoint_name'] == endpoint_name)).upper(), str(next(ep['path'] for ep in endpoint_rows if ep['endpoint_name'] == endpoint_name)))]}"
            for endpoint_name in matched
        ]
        for scenario_id in scenario_refs:
            if scenario_id in scenario_by_id:
                test_targets.append(f"tests/scenarios/{scenario_test_filename(scenario_by_id[scenario_id])}")
        for replay_id in replay_refs:
            resolved = resolve_replay_ref(replay_id, replay_by_id)
            if resolved:
                test_targets.append(f"tests/replays/{replay_test_filename(resolved, replay_by_id[resolved])}")
        test_targets = sorted(set(test_targets))

        if not test_targets:
            unmatched_contract_trace_ids.append(str(row["trace_id"]))
        rows.append(
            {
                "source_type": "contract-trace",
                "source_id": str(row["trace_id"]),
                "source_subject": str(row["trace_subject"]),
                "test_type": "contract",
                "test_targets": test_targets,
                "upstream_trace_ids": row.get("upstream_trace_ids", []),
                "verification_hook": str(row.get("verification_hook", "")),
            }
        )

    for row in scenario_rows:
        scenario_id, _ = scenario_identifier(str(row["scenario"]))
        rows.append(
            {
                "source_type": "scenario",
                "source_id": scenario_id,
                "source_subject": str(row["scenario"]),
                "test_type": "scenario",
                "test_targets": [f"tests/scenarios/{scenario_test_filename(str(row['scenario']))}"],
                "upstream_trace_ids": row.get("upstream_trace_ids", []),
                "verification_hook": str(row.get("measurement_hook", "")),
            }
        )

    for row in replay_rows:
        rows.append(
            {
                "source_type": "replay",
                "source_id": str(row["replay_id"]),
                "source_subject": str(row["scenario_or_contract"]),
                "test_type": "replay",
                "test_targets": [
                    f"tests/replays/{replay_test_filename(str(row['replay_id']), str(row['scenario_or_contract']))}"
                ],
                "upstream_trace_ids": row.get("upstream_trace_ids", []),
                "verification_hook": str(row.get("expected_outcome", "")),
                "linked_rbi_or_wp": row.get("linked_rbi_or_wp", []),
            }
        )

    matched_endpoint_names = {
        endpoint_name
        for row in contract_rows
        for endpoint_name in row.get("matched_endpoints", [])
    }
    endpoint_fallback_rows: list[dict[str, object]] = []
    for endpoint in endpoint_rows:
        endpoint_name = str(endpoint["endpoint_name"])
        if endpoint_name in matched_endpoint_names:
            continue
        scenario_matches = [row for row in scenario_rows if endpoint_matches_scenario_refs(endpoint, row)]
        replay_matches = [row for row in replay_rows if replay_mentions_endpoint_row(endpoint, row)]
        test_targets = [
            f"tests/contracts/{contract_target_lookup[(endpoint_name, str(endpoint['method']).upper(), str(endpoint['path']))]}"
        ]
        upstream_trace_ids: set[str] = set()
        verification_refs: list[str] = []
        for scenario_row in scenario_matches:
            scenario_name = str(scenario_row["scenario"])
            scenario_id, _ = scenario_identifier(scenario_name)
            test_targets.append(f"tests/scenarios/{scenario_test_filename(scenario_name)}")
            upstream_trace_ids.update(str(item).strip() for item in scenario_row.get("upstream_trace_ids", []) if str(item).strip())
            verification_refs.append(scenario_id)
        for replay_row in replay_matches:
            replay_id = str(replay_row["replay_id"]).upper()
            test_targets.append(
                f"tests/replays/{replay_test_filename(replay_id, str(replay_row['scenario_or_contract']))}"
            )
            upstream_trace_ids.update(str(item).strip() for item in replay_row.get("upstream_trace_ids", []) if str(item).strip())
            verification_refs.append(replay_id)
        endpoint_fallback_rows.append(
            {
                "source_type": "endpoint-contract-fallback",
                "source_id": endpoint_source_id(endpoint_name),
                "source_subject": f"{endpoint_name} endpoint fallback contract ({endpoint['method']} {endpoint['path']})",
                "test_type": "contract",
                "test_targets": sorted(set(test_targets)),
                "upstream_trace_ids": sorted(upstream_trace_ids),
                "verification_hook": ", ".join(sorted(set(verification_refs))) or "endpoint fallback closure",
            }
        )

    rows.extend(endpoint_fallback_rows)
    security_decision_rows = build_security_decision_rows(esp_text)
    rows.extend(security_decision_rows)

    return {
        "rows": rows,
        "summary": {
            "contract_trace_count": len(contract_rows),
            "scenario_count": len(scenario_rows),
            "replay_count": len(replay_rows),
            "unmatched_contract_trace_ids": unmatched_contract_trace_ids,
            "matched_endpoint_count": len(matched_endpoint_names),
            "endpoint_fallback_count": len(endpoint_fallback_rows),
            "security_decision_count": len(security_decision_rows),
            "matrix_row_count": len(rows),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Phase-3 test trace matrix")
    parser.add_argument("--esp", required=True, help="Path to engineering-spec-pack.md")
    parser.add_argument("--stage-03", required=True, help="Path to Stage-03 markdown")
    parser.add_argument("--stage-04", required=True, help="Path to Stage-04 markdown")
    parser.add_argument("--openapi", help="Optional final OpenAPI document path")
    parser.add_argument("--output", required=True, help="Output path for test-trace-matrix.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    matrix = build_test_trace_matrix(
        esp_text=Path(args.esp).resolve().read_text(encoding="utf-8"),
        stage_03_text=Path(args.stage_03).resolve().read_text(encoding="utf-8"),
        stage_04_text=Path(args.stage_04).resolve().read_text(encoding="utf-8"),
        openapi_spec=json.loads(Path(args.openapi).resolve().read_text(encoding="utf-8")) if args.openapi else None,
    )
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), **matrix["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
