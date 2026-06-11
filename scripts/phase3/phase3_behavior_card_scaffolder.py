#!/usr/bin/env python3
"""Scaffold traceable Phase-3 behavior cards from resolved P1/P2 source bundles."""

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


TRACE_ID_RE = re.compile(r"\bP[12]-(?:EP|US|UC|REQ|AC|DTR|CTR|RP|RT)-\d+\b")


def _slug_operation(operation_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "", operation_id.strip())
    return cleaned or "operation"


def _source_ref(source: dict[str, Any]) -> str:
    if source.get("status") != "resolved":
        return str(source.get("reason") or "source missing")
    file = str(source.get("file") or "unknown-source")
    line = source.get("line")
    trace_id = str(source.get("trace_id") or source.get("marker") or "source")
    return f"{trace_id} @ {file}:{line}" if line else f"{trace_id} @ {file}"




def _source_ref_for_step(source: dict[str, Any], source_type: str, source_bundle: dict[str, Any]) -> str:
    statuses = source_bundle.get("source_requirement_statuses", {})
    if isinstance(statuses, dict) and str(statuses.get(source_type, "")).replace("_", "-") == "not-required":
        return "not required for low-risk read operation"
    return _source_ref(source)


def _source_authority(source: dict[str, Any]) -> str:
    if source.get("status") == "review_bound":
        return "review-bound"
    return str(source.get("authority") or "markdown-fallback")


def _trace_authority_status(sources: list[dict[str, Any]]) -> str:
    authorities = [_source_authority(source) for source in sources]
    if authorities and all(authority == "registry-bound" for authority in authorities):
        return "registry-bound"
    if any(authority == "registry-bound" for authority in authorities):
        return "partial"
    return "fallback_or_review_bound"


def _format_list(items: list[str]) -> str:
    if not items:
        return "  - none"
    return "\n".join(f"  - {item}" for item in items)


def _format_mapping(value: str, fallback: str) -> str:
    cleaned = str(value).strip()
    return cleaned if cleaned else fallback


def _format_inline_list(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    return ", ".join(str(item) for item in items if str(item).strip())


def _format_source_requirement_statuses(statuses: Any) -> str:
    if not isinstance(statuses, dict) or not statuses:
        return "  - none"
    return "\n".join(f"  - {key}: {value}" for key, value in statuses.items())


def _semantic_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip()) or "none"
    cleaned = str(value or "").strip()
    return cleaned or "none"


def _semantic_payload_section(semantics: Any) -> tuple[str, str, str, str, str]:
    generic_transition = "derived from P2 flow/state source and enforced by the service transition policy"
    generic_invariants = "preserve trace id, tenant boundary, version/conflict semantics, and public error envelope"
    generic_transaction = "required for high-risk writes; use caller token, aggregate id, or version guard where applicable"
    generic_audit = "record business-visible evidence when the operation mutates state or crosses a boundary"
    if not isinstance(semantics, dict) or semantics.get("status") != "resolved":
        return "", generic_transition, generic_invariants, generic_transaction, generic_audit
    owner = str(semantics.get("owner_service") or "").strip()
    aggregate = str(semantics.get("aggregate") or "").strip()
    state_set = _semantic_list(semantics.get("state_set"))
    trigger_events = _semantic_list(semantics.get("trigger_events"))
    mutation_guard = str(semantics.get("mutation_guard") or "").strip()
    terminal_exit = str(semantics.get("terminal_or_failure_exit") or "").strip()
    readonly_dependencies = _semantic_list(semantics.get("readonly_dependencies"))
    evidence_keys = _semantic_list(semantics.get("evidence_keys"))
    transition = f"{aggregate} states {state_set} via {trigger_events}" if aggregate else f"states {state_set} via {trigger_events}"
    invariants = mutation_guard or f"{owner} owns {aggregate} writes"
    transaction_rule = f"preserve evidence keys {evidence_keys}"
    audit_effect = f"emit or preserve {trigger_events} after authoritative write"
    section = f"""## 2A. Operation Semantic Payload

- semantic_status: resolved
- owner_service: {owner or 'unknown'}
- aggregate: {aggregate or 'unknown'}
- state_set: {state_set}
- trigger_events: {trigger_events}
- mutation_guard: {mutation_guard or 'none'}
- terminal_or_failure_exit: {terminal_exit or 'none'}
- readonly_dependencies: {readonly_dependencies}
- evidence_keys: {evidence_keys}

"""
    return section, transition, invariants, transaction_rule, audit_effect


def generate_behavior_card(source_bundle: dict[str, Any], risk_result: dict[str, Any] | None = None) -> str:
    operation_id = str(source_bundle.get("operation_id") or "UnknownOperation")
    upstream_ids = [
        str(item).strip()
        for item in source_bundle.get("upstream_trace_ids", [])
        if TRACE_ID_RE.fullmatch(str(item).strip())
    ]
    risk_result = risk_result or {}
    review_bound = [str(item) for item in source_bundle.get("review_bound", []) if str(item).strip()]
    contract = source_bundle.get("contract_source", {}) if isinstance(source_bundle.get("contract_source"), dict) else {}
    flow = source_bundle.get("flow_source", {}) if isinstance(source_bundle.get("flow_source"), dict) else {}
    sequence = source_bundle.get("sequence_source", {}) if isinstance(source_bundle.get("sequence_source"), dict) else {}
    state = source_bundle.get("state_source", {}) if isinstance(source_bundle.get("state_source"), dict) else {}
    contract_subject = str(contract.get("subject") or operation_id)
    source_by_type = {"P2-CTR": contract, "P2-FLOW": flow, "P2-SEQ": sequence, "P2-STATE": state}
    required_source_type_values = [str(item) for item in source_bundle.get("required_source_types", []) if str(item).strip()]
    required_sources = [source_by_type[source_type] for source_type in required_source_type_values if source_type in source_by_type]
    sources = required_sources or [contract, flow, sequence, state]
    source_refs = [_source_ref(contract), _source_ref(flow), _source_ref(sequence), _source_ref(state)]
    trace_authority_status = _trace_authority_status(sources)
    operation_risk_row_status = str(source_bundle.get("operation_risk_row_status", "unknown"))
    risk_tier = str(source_bundle.get("risk_tier") or risk_result.get("risk_tier") or risk_result.get("risk_level", "unknown"))
    required_source_types = _format_inline_list(source_bundle.get("required_source_types", [])) or "none"
    not_required_source_types = _format_inline_list(source_bundle.get("not_required_source_types", [])) or "none"
    source_requirement_statuses = _format_source_requirement_statuses(source_bundle.get("source_requirement_statuses", {}))
    triggers = [str(item) for item in risk_result.get("triggers", []) if str(item).strip()]
    persistence_surfaces = _format_mapping(str(source_bundle.get("persistence_surfaces", "")), "operation-specific durable surface to be bound by P2/P3 schema evidence")
    contract_test = _format_mapping(str(source_bundle.get("contract_test", "")), f"tests/contracts/{operation_id}.contract.test.ts")
    scenario_test = _format_mapping(str(source_bundle.get("scenario_test", "")), "tests/scenarios/* scenario linked by operation trace")
    replay_test = _format_mapping(str(source_bundle.get("replay_test", "")), "tests/replays/* replay linked by operation trace")
    sql_test = _format_mapping(str(source_bundle.get("sql_test", "")), f"tests/sql/{persistence_surfaces.split(',')[0].strip()}.sql.test.ts")
    unit_test = _format_mapping(str(source_bundle.get("unit_test", "")), f"tests/unit/api/modules/{operation_id}.unit.test.ts")
    controller_target = _format_mapping(str(source_bundle.get("controller_target", "")), "generated controller method")
    service_target = _format_mapping(str(source_bundle.get("service_target", "")), "behavior-card service method")
    repository_target = _format_mapping(str(source_bundle.get("repository_target", "")), "behavior-card repository/adapter method")
    db_target = _format_mapping(str(source_bundle.get("db_target", "")), persistence_surfaces)
    semantic_section, state_transition, invariants, transaction_rule, audit_effect = _semantic_payload_section(source_bundle.get("operation_semantics"))

    return f"""# 可溯源业务行为卡：{operation_id}

## 0. Traceability Binding

- registry_artifact_id: P3-BC-{_slug_operation(operation_id)}
- artifact_type: INTERFACE
- operation_id: {operation_id}
- upstream_trace_ids:
{_format_list(upstream_ids)}
- trace_authority_status: {trace_authority_status}
- contract_source_authority: {_source_authority(contract)}
- flow_source_authority: {_source_authority(flow)}
- sequence_source_authority: {_source_authority(sequence)}
- state_source_authority: {_source_authority(state)}
- trace_authority_rule: P3-only trace registry is not upstream authority; resolve from wff-base-traceability-management first.
- operation_risk_row_status: {operation_risk_row_status}
- risk_tier: {risk_tier}
- required_source_types: {required_source_types}
- not_required_source_types: {not_required_source_types}
- source_requirement_statuses:
{source_requirement_statuses}
- source_bindings:
{_format_list(source_refs)}
- downstream_bindings:
  - contract test: {contract_test}
  - scenario test: {scenario_test}
  - replay test: {replay_test}
  - service implementation: {service_target}
  - repository / adapter implementation: {repository_target}

## 1. Business Intent

`{operation_id}` protects the public behavior of `{contract_subject}` before private implementation starts. The operation must keep the P1/P2 trace chain visible so reviewers can see why the behavior exists, which contract defines it, and which downstream code/test surfaces prove it. For high-risk operations, this card prevents generated code from satisfying response shape while leaving the real service/repository behavior thin or implicit.

## 2. Public Contract

- request contract: derived from `{operation_id}` / `{contract_subject}` P2 source.
- response contract: derived from `{operation_id}` / `{contract_subject}` P2 source.
- data contract: `{contract_subject}`.
- public errors: `invalid_request`, `forbidden`, `not_found`, `version_conflict`, `dependency_unavailable`.
- public stability rule: additive-only public contract change; do not silently rewrite P2 contract during P3.

{semantic_section}
## 3. Human-Readable Pseudocode

1. Receive `{operation_id}` and preserve caller trace context.
   - source: {_source_ref(contract)}
   - implementation owner: controller
2. Validate required business context, tenant/permission posture, and contract fields before any state change.
   - source: {_source_ref(contract)}
   - implementation owner: service validation
3. Load the current aggregate, version, and persistence evidence needed to decide the operation honestly.
   - source: {_source_ref_for_step(flow, "P2-FLOW", source_bundle)}
   - implementation owner: repository
4. Apply the P2 behavior/state rule and reject stale, forbidden, or invalid transitions with explicit business errors.
   - source: {_source_ref_for_step(state, "P2-STATE", source_bundle)}
   - implementation owner: service policy
5. Persist the state change and audit/event evidence atomically when the operation mutates durable state.
   - source: {_source_ref_for_step(sequence, "P2-SEQ", source_bundle)}
   - implementation owner: repository / adapter
6. Return the frozen response envelope with trace metadata and stable machine-readable error semantics.
   - source: {_source_ref(contract)}
   - implementation owner: controller response mapper

## 4. Error Trigger Table

| error_code | trigger condition | implementation owner | test owner |
|---|---|---|---|
| invalid_request | required contract field or business context is missing or invalid | service validation | contract/unit |
| forbidden | caller violates tenant, permission, or ownership boundary | service policy | contract/scenario |
| not_found | required aggregate, dependency, or source record does not exist | repository + service | contract/scenario |
| version_conflict | stale version, replay conflict, or concurrency guard rejects the write | service + repository | contract/scenario/unit |
| dependency_unavailable | DB, queue, cache, or external adapter cannot provide required evidence | adapter/error mapping | contract |

## 5. State And Persistence Effects

- state transition: {state_transition}.
- tables / collections / queues affected: {persistence_surfaces}.
- invariants: {invariants}.
- transaction / idempotency / replay rule: {transaction_rule}.
- audit / event / side effect: {audit_effect}.

## 6. Test Mapping

| behavior step | contract test | scenario test | replay test | SQL test | unit test |
|---|---|---|---|---|---|
| step-1 receive and trace | {contract_test} | {scenario_test} | {replay_test} | n/a | {unit_test} |
| step-2 validate context | {contract_test} | {scenario_test} | {replay_test} | n/a | {unit_test} |
| step-3 load aggregate | {contract_test} | {scenario_test} | {replay_test} | {sql_test} | {unit_test} |
| step-4 apply rule | {contract_test} | {scenario_test} | {replay_test} | {sql_test} | {unit_test} |
| step-5 persist effects | {contract_test} | {scenario_test} | {replay_test} | {sql_test} | {unit_test} |
| step-6 return envelope | {contract_test} | {scenario_test} | {replay_test} | n/a | {unit_test} |

## 7. Implementation Mapping

| behavior step | controller | service | repository/adapter | DB/schema |
|---|---|---|---|---|
| step-1 receive and trace | {controller_target} | n/a | n/a | n/a |
| step-2 validate context | {controller_target} | {service_target} | n/a | n/a |
| step-3 load aggregate | n/a | {service_target} | {repository_target} | {db_target} |
| step-4 apply rule | n/a | {service_target} | {repository_target} | {db_target} |
| step-5 persist effects | n/a | {service_target} | {repository_target} | {db_target} |
| step-6 return envelope | {controller_target} | {service_target} | n/a | n/a |

## 8. Review-Bound Items

- risk_level: {risk_result.get("risk_level", "unknown")}
- risk_triggers:
{_format_list(triggers)}
- unresolved_source_precision:
{_format_list(review_bound)}
"""


def write_behavior_card(output_root: str | Path, source_bundle: dict[str, Any], risk_result: dict[str, Any] | None = None) -> Path:
    root = Path(output_root)
    operation_id = str(source_bundle.get("operation_id") or "UnknownOperation")
    card_path = root / "behavior-cards" / f"{_slug_operation(operation_id)}.behavior-card.md"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(generate_behavior_card(source_bundle, risk_result), encoding="utf-8")
    return card_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a P3 traceable behavior card from a source bundle")
    parser.add_argument("source_bundle_json")
    parser.add_argument("--risk-json")
    parser.add_argument("--output-root", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_bundle = json.loads(Path(args.source_bundle_json).read_text(encoding="utf-8"))
    risk_result = json.loads(Path(args.risk_json).read_text(encoding="utf-8")) if args.risk_json else None
    path = write_behavior_card(args.output_root, source_bundle, risk_result)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
