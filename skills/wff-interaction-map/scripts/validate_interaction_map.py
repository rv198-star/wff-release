#!/usr/bin/env python3
"""Validate a WFF interaction-map packet without deciding its content truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = "wff.interaction_map.v1"
ALLOWED_MAP_TYPES = {"p1_business", "p2_architecture_data", "px_current_state_impact"}
ALLOWED_EVIDENCE_STATES = {"confirmed", "inferred", "review-bound", "conflict", "unknown"}
PX_CONFIRMED_SOURCE_KINDS = {"code", "runtime", "database", "api", "test"}
ALLOWED_EVIDENCE_KINDS = {
    "phase_artifact",
    "trace_registry",
    "claim_surface",
    "contract_table",
    "mermaid",
    "code",
    "runtime",
    "database",
    "api",
    "test",
    "external_document",
    "human_review",
}
ALLOWED_PRESENTATION_HINTS = {
    "preferred_layout",
    "canvas",
    "lane_hint",
    "primary_path_hint",
    "label_compact_hint",
}
MODE_AUTHORITY = {
    "p1_business": ("p1", "wff-req"),
    "p2_architecture_data": ("p2", "wff-arch"),
    "px_current_state_impact": ("px", "wff-x"),
}


def _require_nonblank_string(
    obj: dict[str, Any],
    key: str,
    label: str,
    errors: list[str],
) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return ""
    return value


def _require_object_list(
    packet: dict[str, Any],
    key: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    value = packet.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be an array")
        return []

    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{key} entry {index} must be an object")
            continue
        objects.append(item)
    return objects


def _index_unique(
    items: list[dict[str, Any]],
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            errors.append(f"{label} missing id")
            continue
        if item_id in indexed:
            errors.append(f"duplicate {label} id: {item_id}")
            continue
        indexed[item_id] = item
    return indexed


def _item_label(kind: str, item: dict[str, Any], index: int) -> str:
    item_id = item.get("id")
    if isinstance(item_id, str) and item_id.strip():
        return f"{kind} {item_id}"
    return f"{kind} entry {index}"


def _source_ref_ids(
    item: dict[str, Any],
    label: str,
    source_index: dict[str, dict[str, Any]],
    errors: list[str],
) -> list[str]:
    raw_refs = item.get("source_refs")
    if not isinstance(raw_refs, list):
        errors.append(f"{label} source_refs must be an array")
        return []

    refs: list[str] = []
    for index, source_ref in enumerate(raw_refs):
        if not isinstance(source_ref, str) or not source_ref.strip():
            errors.append(f"{label} source_refs entry {index} must be a nonblank string")
            continue
        refs.append(source_ref)
        if source_ref not in source_index:
            errors.append(f"{label} references unknown source {source_ref}")
    return refs


def _validate_evidence(
    item: dict[str, Any],
    label: str,
    map_type: str,
    source_index: dict[str, dict[str, Any]],
    evidence_states: set[str],
    errors: list[str],
) -> str:
    evidence_state = _require_nonblank_string(
        item,
        "evidence_state",
        f"{label} evidence_state",
        errors,
    )
    if evidence_state:
        evidence_states.add(evidence_state)
        if evidence_state not in ALLOWED_EVIDENCE_STATES:
            errors.append(f"{label} has invalid evidence state: {evidence_state}")

    refs = _source_ref_ids(item, label, source_index, errors)
    if evidence_state == "confirmed" and not refs:
        errors.append(f"{label}: confirmed items require at least one source ref")

    if evidence_state == "confirmed" and map_type == "px_current_state_impact":
        source_kinds = [
            source_index[source_ref].get("evidence_kind")
            for source_ref in refs
            if source_ref in source_index
        ]
        if not any(
            isinstance(source_kind, str) and source_kind in PX_CONFIRMED_SOURCE_KINDS
            for source_kind in source_kinds
        ):
            errors.append(
                f"{label}: PX confirmed items require at least one "
                "code/runtime/database/api/test source ref"
            )
    return evidence_state


def _empty_metrics() -> dict[str, Any]:
    return {
        "node_count": 0,
        "behavior_count": 0,
        "relation_count": 0,
        "scenario_count": 0,
        "evidence_states": [],
    }


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    evidence_states: set[str] = set()

    if not isinstance(packet, dict):
        return {
            "valid": False,
            "errors": ["packet must be an object"],
            "warnings": warnings,
            "metrics": _empty_metrics(),
        }

    if packet.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be '{SCHEMA_VERSION}'")
    _require_nonblank_string(packet, "map_id", "map_id", errors)
    map_type = _require_nonblank_string(packet, "map_type", "map_type", errors)
    _require_nonblank_string(packet, "title", "title", errors)
    if map_type and map_type not in ALLOWED_MAP_TYPES:
        errors.append(f"unsupported map_type: {map_type}")

    raw_authority = packet.get("authority_boundary")
    if not isinstance(raw_authority, dict):
        errors.append("authority_boundary must be an object")
        authority: dict[str, Any] = {}
    else:
        authority = raw_authority
    source_phase = _require_nonblank_string(
        authority,
        "source_phase",
        "authority_boundary.source_phase",
        errors,
    )
    truth_owner = _require_nonblank_string(
        authority,
        "truth_owner",
        "authority_boundary.truth_owner",
        errors,
    )
    if authority.get("claim_authority") != "none":
        errors.append("authority_boundary.claim_authority must be 'none'")
    if authority.get("rendering_role") != "human_review_companion":
        errors.append(
            "authority_boundary.rendering_role must be 'human_review_companion'"
        )
    expected_authority = MODE_AUTHORITY.get(map_type)
    if expected_authority is not None:
        expected_phase, expected_owner = expected_authority
        if source_phase and source_phase != expected_phase:
            errors.append(
                f"authority_boundary.source_phase must be '{expected_phase}' "
                f"for map_type {map_type}"
            )
        if truth_owner and truth_owner != expected_owner:
            errors.append(
                f"authority_boundary.truth_owner must be '{expected_owner}' "
                f"for map_type {map_type}"
            )

    raw_hints = packet.get("presentation_hints")
    if "presentation_hints" in packet and not isinstance(raw_hints, dict):
        errors.append("presentation_hints must be an object")
    elif isinstance(raw_hints, dict):
        unknown_hints = [key for key in raw_hints if key not in ALLOWED_PRESENTATION_HINTS]
        for key in sorted(unknown_hints, key=str):
            warnings.append(f"unknown presentation hint: {key}")

    sources = _require_object_list(packet, "source_refs", errors)
    nodes = _require_object_list(packet, "nodes", errors)
    behaviors = _require_object_list(packet, "behaviors", errors)
    relations = _require_object_list(packet, "relations", errors)
    scenarios = _require_object_list(packet, "scenarios", errors)
    if isinstance(packet.get("nodes"), list) and not packet["nodes"]:
        errors.append("nodes must contain at least one node")

    source_index = _index_unique(sources, "source", errors)
    node_index = _index_unique(nodes, "node", errors)
    _index_unique(behaviors, "behavior", errors)
    relation_index = _index_unique(relations, "relation", errors)
    _index_unique(scenarios, "scenario", errors)

    for index, source in enumerate(sources):
        label = _item_label("source", source, index)
        _require_nonblank_string(source, "path", f"{label} path", errors)
        evidence_kind = _require_nonblank_string(
            source,
            "evidence_kind",
            f"{label} evidence_kind",
            errors,
        )
        if evidence_kind and evidence_kind not in ALLOWED_EVIDENCE_KINDS:
            errors.append(f"{label} has invalid evidence kind: {evidence_kind}")
        if "anchor" in source:
            _require_nonblank_string(source, "anchor", f"{label} anchor", errors)

    connected_node_ids = {
        endpoint
        for relation in relations
        for endpoint in (relation.get("from"), relation.get("to"))
        if isinstance(endpoint, str) and endpoint.strip()
    }

    node_states: list[tuple[str, str]] = []
    for index, node in enumerate(nodes):
        label = _item_label("node", node, index)
        node_id = node.get("id")
        _require_nonblank_string(node, "label", f"{label} label", errors)
        _require_nonblank_string(node, "kind", f"{label} kind", errors)
        _require_nonblank_string(node, "phase_role", f"{label} phase_role", errors)
        evidence_state = _validate_evidence(
            node,
            label,
            map_type,
            source_index,
            evidence_states,
            errors,
        )
        if isinstance(node_id, str) and node_id.strip():
            node_states.append((node_id, evidence_state))

    for index, behavior in enumerate(behaviors):
        label = _item_label("behavior", behavior, index)
        node_id = _require_nonblank_string(
            behavior,
            "node_id",
            f"{label} node_id",
            errors,
        )
        _require_nonblank_string(behavior, "summary", f"{label} summary", errors)
        if node_id and node_id not in node_index:
            errors.append(f"{label} references unknown node {node_id}")
        _validate_evidence(
            behavior,
            label,
            map_type,
            source_index,
            evidence_states,
            errors,
        )

    for index, relation in enumerate(relations):
        label = _item_label("relation", relation, index)
        source_node = _require_nonblank_string(
            relation,
            "from",
            f"{label} from",
            errors,
        )
        target_node = _require_nonblank_string(
            relation,
            "to",
            f"{label} to",
            errors,
        )
        _require_nonblank_string(relation, "label", f"{label} label", errors)
        _require_nonblank_string(relation, "flow_type", f"{label} flow_type", errors)
        if source_node and source_node not in node_index:
            errors.append(f"{label} references unknown source node {source_node}")
        if target_node and target_node not in node_index:
            errors.append(f"{label} references unknown target node {target_node}")
        if "sequence" in relation:
            sequence = relation.get("sequence")
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
                errors.append(f"relation sequence must be a non-negative integer: {label}")
        _validate_evidence(
            relation,
            label,
            map_type,
            source_index,
            evidence_states,
            errors,
        )

    for index, scenario in enumerate(scenarios):
        label = _item_label("scenario", scenario, index)
        _require_nonblank_string(scenario, "label", f"{label} label", errors)
        raw_sequence = scenario.get("relation_sequence")
        if not isinstance(raw_sequence, list) or not raw_sequence:
            errors.append(f"scenario relation_sequence must be a non-empty array: {label}")
        else:
            for sequence_index, relation_id in enumerate(raw_sequence):
                if not isinstance(relation_id, str) or not relation_id.strip():
                    errors.append(
                        f"{label} relation_sequence entry {sequence_index} "
                        "must be a nonblank string"
                    )
                elif relation_id not in relation_index:
                    errors.append(f"{label} references unknown relation {relation_id}")
        _validate_evidence(
            scenario,
            label,
            map_type,
            source_index,
            evidence_states,
            errors,
        )

    for node_id, evidence_state in node_states:
        if evidence_state in {"confirmed", "inferred"} and node_id not in connected_node_ids:
            errors.append(
                f"{evidence_state} node must participate in a relation: {node_id}"
            )

    metrics = {
        "node_count": len(nodes),
        "behavior_count": len(behaviors),
        "relation_count": len(relations),
        "scenario_count": len(scenarios),
        "evidence_states": sorted(evidence_states),
    }
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def load_packet(path: Path) -> dict[str, Any]:
    packet = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(packet, dict):
        raise ValueError("packet JSON root must be a top-level JSON object")
    return packet


def _error_report(error_kind: str, message: str) -> str:
    return json.dumps(
        {"valid": False, "error_kind": error_kind, "error": message},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path, help="JSON packet to validate")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        packet = load_packet(args.packet)
    except json.JSONDecodeError as exc:
        print(_error_report("json_parse", str(exc)), file=sys.stderr)
        return 2
    except OSError as exc:
        print(_error_report("input_io", str(exc)), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(_error_report("json_root", str(exc)), file=sys.stderr)
        return 2

    result = validate_packet(packet)
    report = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(report)
    else:
        try:
            args.output.write_text(report, encoding="utf-8")
        except OSError as exc:
            print(_error_report("output_io", str(exc)), file=sys.stderr)
            return 2
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
