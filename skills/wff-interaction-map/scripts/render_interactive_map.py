#!/usr/bin/env python3
"""Render a validated WFF interaction-map packet as bounded standalone HTML."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Sequence

from check_interaction_map_layout import (
    CANVAS_BOTTOM_RESERVED,
    CANVAS_WIDTH,
    COMPONENT_GAP,
    COMPONENT_HEIGHT,
    COMPONENT_TOP,
    adaptive_canvas_height,
    presentation_layer as _presentation_layer,
)
from validate_interaction_map import load_packet, validate_packet


LANE_TOP = 174.0
VIEW_KIND_BY_MAP_TYPE = {
    "p1_business": "business_interaction",
    "p2_architecture_data": "system_interaction",
    "px_current_state_impact": "current_state_impact",
}
FLOW_COLORS = {
    "control": "#2563eb",
    "handoff": "#7c3aed",
    "data_write": "#b45309",
    "event": "#c2410c",
    "exception": "#be123c",
    "impact": "#9333ea",
    "safety": "#dc2626",
}
STATE_COLORS = {
    "confirmed": "#047857",
    "inferred": "#1d4ed8",
    "review-bound": "#b45309",
    "conflict": "#be123c",
    "unknown": "#64748b",
}
TEXT = {
    "en": {
        "document_suffix": "WFF interaction-map companion",
        "interaction_map": "Interaction map",
        "view_titles": {
            "business_interaction": "Business interaction",
            "system_interaction": "System interaction",
            "current_state_impact": "Current-state impact",
        },
        "source_evidence": "Source evidence",
        "open_evidence": "Open source evidence",
        "close_evidence": "Close source evidence",
        "scenario_paths": "Scenario paths",
        "relation_sequence": "Relation sequence",
        "evidence_state": "Evidence state",
        "source_refs": "Source refs",
        "item": "Item",
        "summary": "Summary",
        "graph_structure": "Graph structure",
        "kind": "Kind",
        "lane": "Lane",
        "node_role": "Node role",
        "behavior_node": "Behavior node",
        "from_node": "From",
        "to_node": "To",
        "flow_type": "Flow type",
        "source_path": "Source path",
        "source_kind": "Evidence kind",
        "anchor": "Anchor",
        "legend": "Legend",
        "component": "Component",
        "relation": "Relation",
        "claim_note": (
            "Human-review companion only. It does not accept evidence, change gates, "
            "or raise claim ceilings."
        ),
        "static_evidence": "Static evidence table (available without JavaScript)",
    },
    "zh-CN": {
        "document_suffix": "WFF 交互图附属视图",
        "interaction_map": "交互图",
        "view_titles": {
            "business_interaction": "业务交互",
            "system_interaction": "系统交互",
            "current_state_impact": "现状影响",
        },
        "source_evidence": "证据来源",
        "open_evidence": "打开证据来源",
        "close_evidence": "关闭证据来源",
        "scenario_paths": "场景路径",
        "relation_sequence": "关系序列",
        "evidence_state": "证据状态",
        "source_refs": "来源引用",
        "item": "条目",
        "summary": "摘要",
        "graph_structure": "图结构",
        "kind": "类型",
        "lane": "泳道",
        "node_role": "节点角色",
        "behavior_node": "行为节点",
        "from_node": "起点",
        "to_node": "终点",
        "flow_type": "流类型",
        "source_path": "来源路径",
        "source_kind": "证据类型",
        "anchor": "锚点",
        "legend": "图例",
        "component": "组件",
        "relation": "关系",
        "claim_note": "仅供人工审阅；不接受证据、不改变门禁，也不提高声明上限。",
        "static_evidence": "静态证据表（无 JavaScript 时仍可查阅）",
    },
}
LANE_LABELS = {
    "en": {
        "business_interaction": {
            "entry": "Business entry",
            "decision": "Decision",
            "exception": "Exception",
        },
        "system_interaction": {
            "entry": "Entry",
            "boundary": "Boundary",
            "application": "Application",
            "persistence": "Persistence",
        },
        "current_state_impact": {
            "current_state": "Current state",
            "change_surface": "Change surface",
            "compatibility": "Compatibility",
            "review": "Review",
        },
    },
    "zh-CN": {
        "business_interaction": {
            "entry": "业务入口",
            "decision": "业务判断",
            "exception": "异常路径",
        },
        "system_interaction": {
            "entry": "系统入口",
            "boundary": "交互边界",
            "application": "应用处理",
            "persistence": "持久化",
        },
        "current_state_impact": {
            "current_state": "现状",
            "change_surface": "变更面",
            "compatibility": "兼容影响",
            "review": "审阅",
        },
    },
}


def _render_locale(explicit: str | None) -> str:
    candidate = explicit.strip() if isinstance(explicit, str) else ""
    if not candidate:
        candidate = os.environ.get("WFF_OUTPUT_LOCALE", "").strip()
    if not candidate:
        candidate = "zh-CN"
    return "en" if candidate.lower().startswith("en") else "zh-CN"


def _esc(value: Any) -> str:
    return (
        html.escape(str(value), quote=True)
        .replace("\u2028", "&#8232;")
        .replace("\u2029", "&#8233;")
    )


def _script_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _lane_label(layer: str, locale: str, view_kind: str) -> str:
    configured = LANE_LABELS[locale][view_kind].get(layer)
    if configured is not None:
        return configured
    return layer.replace("_", " ")


def _build_components(
    nodes: list[dict[str, Any]],
    locale: str,
    view_kind: str,
) -> list[dict[str, Any]]:
    lane_order: list[str] = []
    lane_counts: dict[str, int] = {}
    for node in nodes:
        layer = _presentation_layer(node)
        if layer not in lane_counts:
            lane_order.append(layer)
            lane_counts[layer] = 0
        lane_counts[layer] += 1

    lane_total = max(1, len(lane_order))
    lane_slot_width = 1440.0 / lane_total
    lane_width = max(12.0, lane_slot_width - 20.0)
    row_offsets: dict[str, int] = {layer: 0 for layer in lane_order}
    components: list[dict[str, Any]] = []

    for index, node in enumerate(nodes):
        layer = _presentation_layer(node)
        lane_index = lane_order.index(layer)
        row_index = row_offsets[layer]
        row_offsets[layer] += 1
        x = 80.0 + lane_index * lane_slot_width + 10.0
        y = COMPONENT_TOP + row_index * (COMPONENT_HEIGHT + COMPONENT_GAP)
        components.append(
            {
                "id": f"component-{index}",
                "index": index,
                "node_id": node["id"],
                "label": node["label"],
                "kind": node["kind"],
                "layer": layer,
                "lane_semantic": f"{view_kind}.{layer}",
                "lane_label": _lane_label(layer, locale, view_kind),
                "lane_index": lane_index,
                "x": round(x, 2),
                "y": round(y, 2),
                "width": round(lane_width, 2),
                "height": COMPONENT_HEIGHT,
                "state": node["evidence_state"],
                "source_refs": list(node["source_refs"]),
            }
        )
    return components


def _anchor(component: dict[str, Any], side: str) -> tuple[float, float]:
    x = float(component["x"])
    y = float(component["y"])
    width = float(component["width"])
    height = float(component["height"])
    if side == "left":
        return x, y + height / 2.0
    if side == "right":
        return x + width, y + height / 2.0
    if side == "top":
        return x + width / 2.0, y
    return x + width / 2.0, y + height


def _build_paths(
    relations: list[dict[str, Any]],
    components: list[dict[str, Any]],
    node_layers: dict[str, str],
) -> list[dict[str, Any]]:
    component_by_node = {str(item["node_id"]): item for item in components}
    paths: list[dict[str, Any]] = []

    for index, relation in enumerate(relations):
        source_id = str(relation["from"])
        target_id = str(relation["to"])
        missing = [
            endpoint
            for endpoint in (source_id, target_id)
            if endpoint not in component_by_node
        ]
        if missing:
            raise ValueError(
                f"missing component endpoint for relation {relation.get('id', index)}: "
                + ", ".join(missing)
            )

        source = component_by_node[source_id]
        target = component_by_node[target_id]
        same_layer = node_layers.get(source_id) == node_layers.get(target_id)
        if source is target:
            sx, sy = _anchor(source, "right")
            tx, ty = _anchor(target, "top")
            curve = (
                f"M {sx:.1f} {sy:.1f} C {sx + 90:.1f} {sy - 90:.1f}, "
                f"{tx + 90:.1f} {ty - 90:.1f}, {tx:.1f} {ty:.1f}"
            )
            label_x, label_y = sx + 72.0, sy - 74.0
        elif same_layer:
            upper, lower = (source, target) if source["y"] <= target["y"] else (target, source)
            bend_x = max(float(upper["x"] + upper["width"]), float(lower["x"] + lower["width"])) + 52.0
            sx, sy = _anchor(source, "right")
            tx, ty = _anchor(target, "right")
            curve = (
                f"M {sx:.1f} {sy:.1f} C {bend_x:.1f} {sy:.1f}, "
                f"{bend_x:.1f} {ty:.1f}, {tx:.1f} {ty:.1f}"
            )
            label_x, label_y = bend_x, (sy + ty) / 2.0 - 10.0
        else:
            forwards = float(source["x"]) <= float(target["x"])
            sx, sy = _anchor(source, "right" if forwards else "left")
            tx, ty = _anchor(target, "left" if forwards else "right")
            offset = max(44.0, abs(tx - sx) * 0.38)
            first_control = sx + offset if forwards else sx - offset
            second_control = tx - offset if forwards else tx + offset
            curve = (
                f"M {sx:.1f} {sy:.1f} C {first_control:.1f} {sy:.1f}, "
                f"{second_control:.1f} {ty:.1f}, {tx:.1f} {ty:.1f}"
            )
            label_x, label_y = (sx + tx) / 2.0, (sy + ty) / 2.0 - 12.0

        flow_type = str(relation["flow_type"])
        paths.append(
            {
                "id": f"path-{index}",
                "index": index,
                "relation_id": relation["id"],
                "source_id": source_id,
                "target_id": target_id,
                "source_index": source["index"],
                "target_index": target["index"],
                "curve": curve,
                "label_x": round(label_x, 2),
                "label_y": round(label_y, 2),
                "label": relation["label"],
                "flow_type": flow_type,
                "color": FLOW_COLORS.get(flow_type, "#475569"),
                "state": relation["evidence_state"],
                "source_refs": list(relation["source_refs"]),
            }
        )
    return paths


def _joined(values: Sequence[Any]) -> str:
    return ", ".join(str(value) for value in values)


def _render_scenario_rows(scenarios: list[dict[str, Any]], locale: str) -> str:
    text = TEXT[locale]
    rows: list[str] = []
    for index, scenario in enumerate(scenarios):
        sequence = " → ".join(_esc(item) for item in scenario["relation_sequence"])
        refs = _esc(_joined(scenario["source_refs"])) or "—"
        rows.append(
            f'''<li class="scenario-row" data-scenario-index="{index}" data-evidence-state="{_esc(scenario["evidence_state"])}">
  <strong>{_esc(scenario["label"])}</strong>
  <span><b>{_esc(text["relation_sequence"])}:</b> {sequence}</span>
  <span><b>{_esc(text["evidence_state"])}:</b> {_esc(scenario["evidence_state"])}</span>
  <span><b>{_esc(text["source_refs"])}:</b> {refs}</span>
</li>'''
        )
    return "\n".join(rows)


def _evidence_tables(packet: dict[str, Any], locale: str) -> str:
    text = TEXT[locale]
    rows: list[str] = []
    description_key = {
        "nodes": "label",
        "behaviors": "summary",
        "relations": "label",
        "scenarios": "label",
    }
    for collection_name in ("nodes", "behaviors", "relations", "scenarios"):
        item_kind = collection_name[:-1]
        for item in packet[collection_name]:
            refs = _joined(item["source_refs"]) or "—"
            if collection_name == "nodes":
                graph_structure = (
                    f'{text["node_role"]}: {item["phase_role"]}; '
                    f'{text["kind"]}: {item["kind"]}'
                )
            elif collection_name == "behaviors":
                graph_structure = f'{text["behavior_node"]}: {item["node_id"]}'
            elif collection_name == "relations":
                graph_structure = (
                    f'{text["from_node"]}: {item["from"]}; '
                    f'{text["to_node"]}: {item["to"]}; '
                    f'{text["flow_type"]}: {item["flow_type"]}'
                )
            else:
                sequence = " → ".join(str(value) for value in item["relation_sequence"])
                graph_structure = f'{text["relation_sequence"]}: {sequence}'
            rows.append(
                f'''<tr data-evidence-state="{_esc(item["evidence_state"])}">
  <th scope="row">{_esc(item_kind)}:{_esc(item["id"])}</th>
  <td>{_esc(item[description_key[collection_name]])}</td>
  <td>{_esc(graph_structure)}</td>
  <td>{_esc(item["evidence_state"])}</td>
  <td>{_esc(refs)}</td>
</tr>'''
            )
    source_rows = []
    for source in packet["source_refs"]:
        source_rows.append(
            f'''<tr>
  <th scope="row">{_esc(source["id"])}</th>
  <td>{_esc(source["path"])}</td>
  <td>{_esc(source.get("anchor", ""))}</td>
  <td>{_esc(source["evidence_kind"])}</td>
</tr>'''
        )
    return f'''<div class="table-scroll">
<table>
  <thead><tr><th>{_esc(text["item"])}</th><th>{_esc(text["summary"])}</th><th>{_esc(text["graph_structure"])}</th><th>{_esc(text["evidence_state"])}</th><th>{_esc(text["source_refs"])}</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
</div>
<div class="table-scroll">
<table>
  <thead><tr><th>{_esc(text["source_refs"])}</th><th>{_esc(text["source_path"])}</th><th>{_esc(text["anchor"])}</th><th>{_esc(text["source_kind"])}</th></tr></thead>
  <tbody>{''.join(source_rows)}</tbody>
</table>
</div>'''


def _render_evidence_drawer(packet: dict[str, Any], locale: str) -> str:
    text = TEXT[locale]
    tables = _evidence_tables(packet, locale)
    return f'''<aside id="evidence-drawer" class="evidence-drawer" role="dialog" aria-modal="true" aria-labelledby="evidence-title" hidden>
  <header>
    <h2 id="evidence-title">{_esc(text["source_evidence"])}</h2>
    <button id="evidence-close" type="button">{_esc(text["close_evidence"])}</button>
  </header>
  {tables}
</aside>'''


def _render_static_evidence(packet: dict[str, Any], locale: str) -> str:
    text = TEXT[locale]
    tables = _evidence_tables(packet, locale)
    return f'''<details class="static-evidence" data-role="static-evidence-table" open>
  <summary>{_esc(text["static_evidence"])}</summary>
  {tables}
</details>'''


def _render_lane_headers(
    components: list[dict[str, Any]],
    canvas_height: int,
) -> str:
    lane_bounds: dict[str, tuple[float, float, str]] = {}
    for component in components:
        layer = str(component["layer"])
        if layer not in lane_bounds:
            lane_bounds[layer] = (
                float(component["x"]),
                float(component["width"]),
                str(component["lane_label"]),
            )
    lane_height = canvas_height - LANE_TOP - CANVAS_BOTTOM_RESERVED
    return "\n".join(
        f'''<g class="lane">
  <rect x="{x:.1f}" y="174" width="{width:.1f}" height="{lane_height:.1f}" rx="12" />
  <text x="{x + width / 2.0:.1f}" y="204" text-anchor="middle">{_esc(label)}</text>
</g>'''
        for _, (x, width, label) in lane_bounds.items()
    )


def _svg_identifier(identifier: str, namespace: str) -> str:
    if not namespace:
        return identifier
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", namespace):
        raise ValueError(
            "SVG id namespace must start with a letter and use only letters, digits, '_' or '-'"
        )
    return f"{namespace}-{identifier}"


def _render_components(
    components: list[dict[str, Any]],
    locale: str,
    *,
    id_namespace: str = "",
) -> str:
    text = TEXT[locale]
    chunks: list[str] = []
    for component in components:
        state = str(component["state"])
        color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
        accessible_name = (
            f'{component["label"]}; {text["kind"]}: {component["kind"]}; '
            f'{text["lane"]}: {component["lane_label"]}; '
            f'{text["evidence_state"]}: {state}'
        )
        chunks.append(
            f'''<g id="{_svg_identifier(str(component["id"]), id_namespace)}" class="component" data-component-index="{component["index"]}" data-evidence-state="{_esc(state)}" tabindex="0" role="listitem" aria-label="{_esc(accessible_name)}">
  <rect x="{component["x"]}" y="{component["y"]}" width="{component["width"]}" height="{component["height"]}" rx="14" style="--state-color:{color}" />
  <text x="{float(component["x"]) + 14.0:.1f}" y="{float(component["y"]) + 31.0:.1f}">{_esc(component["label"])}</text>
  <text class="component-meta" x="{float(component["x"]) + 14.0:.1f}" y="{float(component["y"]) + 55.0:.1f}">{_esc(component["kind"])} · {_esc(state)}</text>
</g>'''
        )
    return "\n".join(chunks)


def _render_paths(
    paths: list[dict[str, Any]],
    locale: str,
    *,
    id_namespace: str = "",
    marker_id: str = "arrow",
) -> str:
    text = TEXT[locale]
    chunks: list[str] = []
    for path in paths:
        accessible_name = (
            f'{path["label"]}; {text["from_node"]}: {path["source_id"]}; '
            f'{text["to_node"]}: {path["target_id"]}; '
            f'{text["flow_type"]}: {path["flow_type"]}; '
            f'{text["evidence_state"]}: {path["state"]}'
        )
        chunks.append(
            f'''<g id="{_svg_identifier(str(path["id"]), id_namespace)}" class="relation-path" data-path-index="{path["index"]}" data-source-index="{path["source_index"]}" data-target-index="{path["target_index"]}" data-evidence-state="{_esc(path["state"])}" tabindex="0" role="listitem" aria-label="{_esc(accessible_name)}">
  <path d="{_esc(path["curve"])}" style="--path-color:{path["color"]}" marker-end="url(#{marker_id})" />
  <text x="{path["label_x"]}" y="{path["label_y"]}" text-anchor="middle">{_esc(path["label"])}</text>
</g>'''
        )
    return "\n".join(chunks)


def _embedded_svg_styles() -> str:
    return """<style>
.wff-interaction-map-svg .lane rect { fill: #f8fafc; stroke: #dbe4ee; }
.wff-interaction-map-svg .lane text { fill: #334155; font-size: 16px; font-weight: 700; }
.wff-interaction-map-svg .component rect { fill: #fff; stroke: var(--state-color); stroke-width: 3; }
.wff-interaction-map-svg .component text { fill: #172033; font-size: 18px; font-weight: 750; pointer-events: none; }
.wff-interaction-map-svg .component .component-meta { fill: #475569; font-size: 13px; font-weight: 600; }
.wff-interaction-map-svg .relation-path path { fill: none; stroke: var(--path-color); stroke-width: 4; }
.wff-interaction-map-svg .relation-path text { fill: #172033; font-size: 14px; font-weight: 700; paint-order: stroke; stroke: #fff; stroke-width: 6px; }
.wff-interaction-map-svg .legend { fill: #334155; font-size: 15px; }
</style>"""


def render_embedded_svg(
    packet: dict[str, Any],
    locale: str | None = None,
    *,
    id_namespace: str = "",
    include_styles: bool = False,
) -> str:
    """Render a source-labeled static SVG inside a dossier document."""
    validation = validate_packet(packet)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    resolved_locale = _render_locale(locale)
    text = TEXT[resolved_locale]
    view_kind = VIEW_KIND_BY_MAP_TYPE[packet["map_type"]]
    components = _build_components(packet["nodes"], resolved_locale, view_kind)
    canvas_height = adaptive_canvas_height(packet["nodes"])
    node_layers = {
        str(node["id"]): _presentation_layer(node) for node in packet["nodes"]
    }
    paths = _build_paths(packet["relations"], components, node_layers)
    title = _esc(packet["title"])
    view_title = _esc(text["view_titles"][view_kind])
    marker_id = _svg_identifier("arrow", id_namespace)
    title_id = _svg_identifier("interaction-map-svg-title", id_namespace)
    class_attribute = ' class="wff-interaction-map-svg"' if include_styles else ""
    styles = _embedded_svg_styles() if include_styles else ""
    return f'''<svg{class_attribute} viewBox="0 0 {CANVAS_WIDTH} {canvas_height}" role="group" aria-labelledby="{title_id}">
      {styles}
      <title id="{title_id}">{title}</title>
      <defs><marker id="{marker_id}" markerWidth="12" markerHeight="8" refX="11" refY="4" orient="auto"><path d="M 0 0 L 12 4 L 0 8 z" fill="context-stroke" /></marker></defs>
      <rect width="1600" height="{canvas_height}" fill="#ffffff" />
      <text x="80" y="82" font-size="38" font-weight="800">{title}</text>
      <text x="80" y="124" font-size="20" fill="#475569">{view_title}</text>
      {_render_lane_headers(components, canvas_height)}
      <g role="list" aria-label="{_esc(text["relation"])}">{_render_paths(paths, resolved_locale, id_namespace=id_namespace, marker_id=marker_id)}</g>
      <g role="list" aria-label="{_esc(text["component"])}">{_render_components(components, resolved_locale, id_namespace=id_namespace)}</g>
      <g class="legend" transform="translate(80 {canvas_height - 100})"><text>{_esc(text["legend"])} · {_esc(text["component"])} = □ · {_esc(text["relation"])} = →</text></g>
      <text x="80" y="{canvas_height - 46}" class="legend">{_esc(text["claim_note"])}</text>
    </svg>'''


def render_html(packet: dict[str, Any], locale: str | None = None) -> str:
    validation = validate_packet(packet)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))

    resolved_locale = _render_locale(locale)
    text = TEXT[resolved_locale]
    view_kind = VIEW_KIND_BY_MAP_TYPE[packet["map_type"]]
    components = _build_components(packet["nodes"], resolved_locale, view_kind)
    canvas_height = adaptive_canvas_height(packet["nodes"])
    node_layers = {
        str(node["id"]): _presentation_layer(node) for node in packet["nodes"]
    }
    paths = _build_paths(packet["relations"], components, node_layers)
    scenario_rows = _render_scenario_rows(packet["scenarios"], resolved_locale)
    evidence_drawer = _render_evidence_drawer(packet, resolved_locale)
    static_evidence = _render_static_evidence(packet, resolved_locale)
    packet_json = _script_json(packet)
    title = _esc(packet["title"])
    view_title = _esc(text["view_titles"][view_kind])

    return f'''<!doctype html>
<html lang="{resolved_locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {_esc(text["document_suffix"])}</title>
<style>
:root {{ color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; color: #172033; background: #eef3f8; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
button, summary, [tabindex] {{ outline-offset: 4px; }}
button:focus-visible, summary:focus-visible, [tabindex]:focus-visible {{ outline: 4px solid #1d4ed8; }}
.page {{ max-width: 1680px; margin: auto; padding: 24px; }}
.page-head {{ display: flex; align-items: end; justify-content: space-between; gap: 24px; margin-bottom: 16px; }}
.eyebrow {{ margin: 0; color: #475569; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }}
h1 {{ margin: 6px 0 0; font-size: clamp(1.7rem, 4vw, 3.2rem); }}
.stage-scroll, .table-scroll {{ overflow: auto; max-width: 100%; }}
.stage-scroll {{ border: 1px solid #cbd5e1; border-radius: 18px; background: white; }}
svg {{ display: block; width: 1600px; height: {canvas_height}px; min-width: 900px; }}
.lane rect {{ fill: #f8fafc; stroke: #dbe4ee; }}
.lane text {{ fill: #334155; font-size: 16px; font-weight: 700; }}
.component rect {{ fill: #fff; stroke: var(--state-color); stroke-width: 3; }}
.component text {{ fill: #172033; font-size: 18px; font-weight: 750; pointer-events: none; }}
.component .component-meta {{ fill: #475569; font-size: 13px; font-weight: 600; }}
.relation-path path {{ fill: none; stroke: var(--path-color); stroke-width: 4; }}
.relation-path text {{ fill: #172033; font-size: 14px; font-weight: 700; paint-order: stroke; stroke: #fff; stroke-width: 6px; }}
.component[data-muted="true"], .relation-path[data-muted="true"] {{ opacity: .22; }}
.component[data-active="true"] rect, .relation-path[data-active="true"] path {{ stroke-width: 7; }}
.legend {{ fill: #334155; font-size: 15px; }}
.scenario-section, .static-evidence {{ margin-top: 20px; border: 1px solid #cbd5e1; border-radius: 16px; background: white; padding: 18px; }}
.scenario-list {{ display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; max-height: 28rem; overflow: auto; }}
.scenario-row {{ display: grid; gap: 5px; border-inline-start: 5px solid #64748b; padding: 10px 14px; background: #f8fafc; }}
.scenario-row span {{ overflow-wrap: anywhere; }}
.evidence-drawer {{ position: fixed; z-index: 5; inset: 0 0 0 auto; width: min(720px, 94vw); overflow: auto; overscroll-behavior: contain; padding: 22px; background: white; border-inline-start: 1px solid #94a3b8; box-shadow: -16px 0 40px rgb(15 23 42 / .22); }}
.evidence-drawer[hidden] {{ display: none; }}
.evidence-drawer header {{ position: sticky; top: 0; display: flex; justify-content: space-between; align-items: center; gap: 16px; background: white; padding-bottom: 12px; }}
button {{ border: 0; border-radius: 10px; background: #173d75; color: white; padding: 11px 16px; font: inherit; font-weight: 700; cursor: pointer; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
th, td {{ padding: 9px; border: 1px solid #dbe4ee; text-align: start; vertical-align: top; overflow-wrap: anywhere; }}
th {{ background: #f1f5f9; }}
.claim-note {{ max-width: 72ch; color: #475569; }}
@media (prefers-reduced-motion: no-preference) {{
  .component, .relation-path {{ transition: opacity 150ms ease, stroke-width 150ms ease; }}
}}
@media (max-width: 760px) {{ .page {{ padding: 12px; }} .page-head {{ align-items: start; flex-direction: column; }} }}
</style>
</head>
<body data-wff-interaction-map data-view-kind="{view_kind}" data-role="human-review-only">
<main id="main-content" class="page">
  <header class="page-head">
    <div><p class="eyebrow">{_esc(text["interaction_map"])} · {view_title}</p><h1>{title}</h1></div>
    <button id="evidence-open" type="button" aria-controls="evidence-drawer" aria-expanded="false">{_esc(text["open_evidence"])}</button>
  </header>
  <p class="claim-note">{_esc(text["claim_note"])}</p>
  <section class="stage-scroll" aria-label="{title}">
    <svg viewBox="0 0 {CANVAS_WIDTH} {canvas_height}" role="group" aria-labelledby="interaction-map-svg-title">
      <title id="interaction-map-svg-title">{title}</title>
      <defs>
        <marker id="arrow" markerWidth="12" markerHeight="8" refX="11" refY="4" orient="auto"><path d="M 0 0 L 12 4 L 0 8 z" fill="context-stroke" /></marker>
      </defs>
      <rect width="1600" height="{canvas_height}" fill="#ffffff" />
      <text x="80" y="82" font-size="38" font-weight="800">{title}</text>
      <text x="80" y="124" font-size="20" fill="#475569">{view_title}</text>
      {_render_lane_headers(components, canvas_height)}
      <g role="list" aria-label="{_esc(text["relation"])}">{_render_paths(paths, resolved_locale)}</g>
      <g role="list" aria-label="{_esc(text["component"])}">{_render_components(components, resolved_locale)}</g>
      <g class="legend" transform="translate(80 {canvas_height - 100})"><text>{_esc(text["legend"])} · {_esc(text["component"])} = □ · {_esc(text["relation"])} = →</text></g>
      <text x="80" y="{canvas_height - 46}" class="legend">{_esc(text["claim_note"])}</text>
    </svg>
  </section>
  <section class="scenario-section" data-role="scenario-list">
    <h2>{_esc(text["scenario_paths"])}</h2>
    <ol class="scenario-list">{scenario_rows}</ol>
  </section>
  {static_evidence}
</main>
{evidence_drawer}
<script id="interaction-map-packet" type="application/json">{packet_json}</script>
<script>
"use strict";
const allPaths = () => Array.from(document.querySelectorAll(".relation-path"));
const allComponents = () => Array.from(document.querySelectorAll(".component"));
const indexesForPath = (path) => [path.dataset.sourceIndex, path.dataset.targetIndex];
let evidenceReturnFocus = null;

function setFocus(pathIndexes, componentIndexes) {{
  const pathSet = new Set(pathIndexes.map(String));
  const componentSet = new Set(componentIndexes.map(String));
  allPaths().forEach((path) => {{
    const active = pathSet.has(path.dataset.pathIndex || "");
    path.dataset.active = String(active);
    path.dataset.muted = String(!active);
  }});
  allComponents().forEach((component) => {{
    const active = componentSet.has(component.dataset.componentIndex || "");
    component.dataset.active = String(active);
    component.dataset.muted = String(!active);
  }});
}}

function focusPath(path) {{
  setFocus([path.dataset.pathIndex || ""], indexesForPath(path));
}}

function focusComponent(component) {{
  const index = component.dataset.componentIndex || "";
  const paths = allPaths().filter((path) => indexesForPath(path).includes(index));
  const componentIndexes = new Set([index]);
  paths.forEach((path) => indexesForPath(path).forEach((item) => componentIndexes.add(item)));
  setFocus(paths.map((path) => path.dataset.pathIndex || ""), Array.from(componentIndexes));
}}

function clearFocus() {{
  allPaths().forEach((path) => {{ path.dataset.active = "false"; path.dataset.muted = "false"; }});
  allComponents().forEach((component) => {{ component.dataset.active = "false"; component.dataset.muted = "false"; }});
}}

function toggleEvidence(force) {{
  const drawer = document.getElementById("evidence-drawer");
  const main = document.getElementById("main-content");
  const open = document.getElementById("evidence-open");
  const close = document.getElementById("evidence-close");
  const shouldOpen = typeof force === "boolean" ? force : drawer.hidden;
  if (shouldOpen) evidenceReturnFocus = document.activeElement;
  drawer.hidden = !shouldOpen;
  main.inert = shouldOpen;
  open.setAttribute("aria-expanded", String(shouldOpen));
  if (shouldOpen) {{
    close.focus();
  }} else {{
    const returnTarget = evidenceReturnFocus;
    evidenceReturnFocus = null;
    const canRestore = returnTarget instanceof HTMLElement
      && returnTarget.isConnected
      && returnTarget !== document.body
      && !returnTarget.hidden
      && !returnTarget.matches("[disabled], [inert]")
      && returnTarget.tabIndex >= 0;
    if (canRestore) returnTarget.focus();
    if (!canRestore || document.activeElement !== returnTarget) open.focus();
  }}
}}

allPaths().forEach((path) => {{
  path.addEventListener("mouseenter", () => focusPath(path));
  path.addEventListener("mouseleave", clearFocus);
  path.addEventListener("focus", () => focusPath(path));
  path.addEventListener("blur", clearFocus);
}});
allComponents().forEach((component) => {{
  component.addEventListener("mouseenter", () => focusComponent(component));
  component.addEventListener("mouseleave", clearFocus);
  component.addEventListener("focus", () => focusComponent(component));
  component.addEventListener("blur", clearFocus);
}});
document.getElementById("evidence-open").addEventListener("click", () => toggleEvidence(true));
document.getElementById("evidence-close").addEventListener("click", () => toggleEvidence(false));
document.addEventListener("keydown", (event) => {{
  const drawer = document.getElementById("evidence-drawer");
  if (drawer.hidden) return;
  if (event.key === "Escape") {{
    event.preventDefault();
    toggleEvidence(false);
    return;
  }}
  if (event.key === "Tab") {{
    const focusableElements = Array.from(drawer.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter((element) => element instanceof HTMLElement && !element.hidden);
    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];
    if (!first || !last) {{
      event.preventDefault();
      return;
    }}
    const active = document.activeElement;
    const leavesBackward = event.shiftKey && (active === first || !drawer.contains(active));
    const leavesForward = !event.shiftKey && (active === last || !drawer.contains(active));
    if (leavesBackward || leavesForward) {{
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }}
  }}
}});
</script>
</body>
</html>
'''


def _write_atomic(path: Path, text: str) -> None:
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
        os.replace(temporary_path, path)
    except BaseException:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
        raise


def _error_report(error_kind: str, message: str) -> str:
    return json.dumps(
        {"valid": False, "error_kind": error_kind, "error": message},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path, help="JSON packet to render")
    parser.add_argument("--output", required=True, type=Path, help="HTML output path")
    parser.add_argument("--locale", help="Output locale (en prefix or zh-CN fallback)")
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

    try:
        rendered = render_html(packet, locale=args.locale)
    except ValueError as exc:
        print(_error_report("packet_invalid", str(exc)), file=sys.stderr)
        return 1

    try:
        _write_atomic(args.output, rendered)
    except (OSError, UnicodeError) as exc:
        print(_error_report("output_io", str(exc)), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
