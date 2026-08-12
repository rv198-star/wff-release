#!/usr/bin/env python3
"""Check deterministic interaction-map presentation constraints and warnings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from validate_interaction_map import load_packet, validate_packet


CANVAS_WIDTH = 1600
BASE_CANVAS_HEIGHT = 900
COMPONENT_TOP = 224.0
COMPONENT_HEIGHT = 72.0
COMPONENT_GAP = 16.0
CANVAS_BOTTOM_RESERVED = 156.0
COMPONENT_BOTTOM_PADDING = 24.0
LONG_LABEL_LIMIT = 34
SEMANTIC_INTENT_NOTE = (
    "layout guard is presentation-only and does not decide semantic truth"
)
ALLOWED_LAYOUTS = {"layered", "staged", "matrix", "centered", "comparison"}
LANE_NAMESPACES = {
    "p1_business": "business_interaction.",
    "p2_architecture_data": "system_interaction.",
    "px_current_state_impact": "current_state_impact.",
}


def presentation_layer(node: dict[str, Any]) -> str:
    """Return the presentation-only lane key used by layout consumers."""
    for key in ("phase_role", "kind"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "review"


def adaptive_canvas_height(nodes: Sequence[dict[str, Any]]) -> int:
    """Calculate the deterministic height from the busiest presentation lane."""
    lane_counts: dict[str, int] = {}
    for node in nodes:
        layer = presentation_layer(node)
        lane_counts[layer] = lane_counts.get(layer, 0) + 1
    busiest_lane = max(lane_counts.values(), default=0)
    if busiest_lane == 0:
        return BASE_CANVAS_HEIGHT
    component_bottom = (
        COMPONENT_TOP
        + (busiest_lane - 1) * (COMPONENT_HEIGHT + COMPONENT_GAP)
        + COMPONENT_HEIGHT
    )
    required_height = int(
        component_bottom + COMPONENT_BOTTOM_PADDING + CANVAS_BOTTOM_RESERVED
    )
    return max(BASE_CANVAS_HEIGHT, required_height)


def check_layout(packet: dict[str, Any]) -> dict[str, Any]:
    semantic = validate_packet(packet)
    errors = list(semantic["errors"])
    warnings = [*semantic["warnings"], SEMANTIC_INTENT_NOTE]

    raw_hints = packet.get("presentation_hints")
    hints = raw_hints if isinstance(raw_hints, dict) else {}
    if "canvas" in hints and hints["canvas"] != {
        "width": CANVAS_WIDTH,
        "height": BASE_CANVAS_HEIGHT,
    }:
        errors.append("presentation_hints.canvas must remain 1600x900")

    if "preferred_layout" in hints:
        preferred = hints["preferred_layout"]
        if not isinstance(preferred, str) or preferred not in ALLOWED_LAYOUTS:
            warnings.append(
                f"presentation_hints.preferred_layout is unsupported: {preferred}"
            )

    raw_nodes = packet.get("nodes")
    nodes = raw_nodes if isinstance(raw_nodes, list) else []
    layout_nodes = [node for node in nodes if isinstance(node, dict)]
    raw_relations = packet.get("relations")
    relations = raw_relations if isinstance(raw_relations, list) else []
    node_ids = {
        str(node.get("id", "")) for node in nodes if isinstance(node, dict)
    }
    connected = {
        str(endpoint)
        for relation in relations
        if isinstance(relation, dict)
        for endpoint in (relation.get("from"), relation.get("to"))
        if endpoint is not None
    }
    isolated = node_ids - connected
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", ""))
        label = str(node.get("label", ""))
        if len(label) > LONG_LABEL_LIMIT:
            warnings.append(
                f"node {node_id} label is long for first-screen presentation"
            )
        if node_id in isolated:
            warnings.append(f"node {node_id} is intentionally isolated in presentation")

    lane_hint = hints.get("lane_hint") or {}
    expected_namespace = LANE_NAMESPACES.get(str(packet.get("map_type")), "")
    if isinstance(lane_hint, dict):
        for node_id, lane in sorted(lane_hint.items(), key=lambda item: str(item[0])):
            if expected_namespace and not str(lane).startswith(expected_namespace):
                warnings.append(
                    f"presentation_hints.lane_hint for {node_id} "
                    "crosses map-mode namespace"
                )

    metrics = {
        "canvas_width": CANVAS_WIDTH,
        "canvas_height": adaptive_canvas_height(layout_nodes),
        "base_canvas_height": BASE_CANVAS_HEIGHT,
        "node_count": semantic["metrics"]["node_count"],
        "warning_count": len(warnings),
    }
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def _error_report(error_kind: str, message: str) -> str:
    return json.dumps(
        {"valid": False, "error_kind": error_kind, "error": message},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        required=True,
        type=Path,
        help="JSON packet to check",
    )
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

    result = check_layout(packet)
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
