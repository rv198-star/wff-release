#!/usr/bin/env python3
"""
Generate a fallback UI prototype input pack for Phase-3 when human-authored prototype assets are missing.
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

from common.gwt_format_checker import first_table_with_headers
from phase3.ui_locale import (
    infer_ui_locale,
    is_zh_locale,
    localize_information_object,
    localize_surface_title,
    normalize_inline_locale_variants,
    normalize_role_display_name,
    normalize_surface_display_title,
    page_role_eyebrow,
    surface_shell_copy,
    surface_success_copy,
    ui_field_label,
    ui_text,
)


MANUAL_PROTOTYPE_CANDIDATES = (
    "ui-prototype-spec.md",
    "ui-prototype-spec.html",
    "ui-wireframes.html",
    "prototype-wireframe.md",
    "prototype-wireframe.html",
    "prototype.html",
)

IGNORED_BASELINE_PROTOTYPE_FILES = {
    "stage-04-design-convergence-and-delivery-prototype.md",
}


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _endpoint_rows(esp_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, Any]] = []
    for line in esp_text.splitlines():
        if "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if len(parts) < 3:
            continue
        method = parts[0].upper()
        path = parts[1]
        if method in {"GET", "POST", "PUT", "PATCH", "DELETE"} and path.startswith("/"):
            rows.append(
                {
                    "method": method,
                    "path": path,
                    "purpose": parts[2],
                    "request_example": _parse_json_example(parts[3]) if len(parts) > 3 else {},
                    "response_example": _parse_json_example(parts[4]) if len(parts) > 4 else {},
                }
            )
    return rows


def _parse_json_example(raw: str) -> Any:
    candidate = str(raw).strip()
    if not candidate:
        return {}
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def _extract_openapi_content_example(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return {}
    content = payload.get("content", {})
    if not isinstance(content, dict):
        return {}
    app_json = content.get("application/json", {})
    if not isinstance(app_json, dict):
        return {}
    return app_json.get("example", {})


def _endpoint_rows_from_openapi(openapi_path: Path) -> list[dict[str, Any]]:
    if not openapi_path.exists():
        return []
    payload = json.loads(openapi_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    paths = payload.get("paths", {})
    if not isinstance(paths, dict):
        return []
    rows: list[dict[str, Any]] = []
    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            method_upper = str(method).upper()
            if method_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            purpose = ""
            request_example: Any = {}
            response_example: Any = {}
            operation_id = ""
            if isinstance(operation, dict):
                operation_id = str(operation.get("operationId", "")).strip()
                purpose = str(operation.get("summary", "")).strip() or operation_id
                request_example = _extract_openapi_content_example(operation.get("requestBody", {}))
                if not isinstance(request_example, dict):
                    request_example = {}
                parameters = operation.get("parameters", [])
                if isinstance(parameters, list):
                    for parameter in parameters:
                        if not isinstance(parameter, dict):
                            continue
                        name = str(parameter.get("name", "")).strip()
                        if not name:
                            continue
                        example = parameter.get("example")
                        if example is None and isinstance(parameter.get("schema"), dict) and "example" in parameter.get("schema", {}):
                            example = parameter["schema"]["example"]
                        if example is None and name in request_example:
                            continue
                        request_example[name] = example
                responses = operation.get("responses", {})
                if isinstance(responses, dict):
                    success_statuses = sorted(
                        [key for key in responses if str(key).startswith("2")],
                        key=str,
                    )
                    if success_statuses:
                        response_example = _extract_openapi_content_example(responses.get(success_statuses[0], {}))
            rows.append(
                {
                    "operation_id": operation_id,
                    "method": method_upper,
                    "path": path,
                    "purpose": purpose,
                    "request_example": request_example,
                    "response_example": response_example,
                }
            )
    return rows


def _discover_manual_prototype_assets(phase2_root: Path) -> list[str]:
    assets: list[str] = []
    for candidate in MANUAL_PROTOTYPE_CANDIDATES:
        path = phase2_root / candidate
        if path.exists():
            assets.append(str(path))
    for path in phase2_root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name in IGNORED_BASELINE_PROTOTYPE_FILES:
            continue
        if "prototype" in name and path.suffix.lower() in {".html", ".md"}:
            assets.append(str(path))
    return sorted(set(assets))


def _extract_workflow_hints(stage04_text: str) -> list[str]:
    hints: list[str] = []
    for line in stage04_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[-*]\s+", stripped) and any(token in stripped.lower() for token in ("user", "flow", "page", "state", "error", "empty")):
            hints.append(re.sub(r"^[-*]\s+", "", stripped))
    return hints[:12]


def _extract_page_map_entries_from_prototype_spec(prototype_spec_text: str) -> list[dict[str, str]]:
    section = "\n".join(_extract_markdown_section_lines(prototype_spec_text, r"surface matrix|page map"))
    if not section.strip():
        return []

    def _clean_scalar(value: object) -> str:
        return str(value or "").strip().strip("`")

    def _clean_list(value: object) -> str:
        return ", ".join(_split_compiled_values(value))

    def _build_entry(raw_row: dict[str, object]) -> dict[str, str]:
        return {
            "page_name": _clean_scalar(raw_row.get("page_name")),
            "page_role": _clean_scalar(raw_row.get("page_role") or raw_row.get("parent_page")),
            "page_blueprint_type": _clean_scalar(raw_row.get("page_blueprint_type")),
            "primary_actor": _clean_scalar(raw_row.get("primary_actor")),
            "why_it_exists": _clean_scalar(raw_row.get("why_it_exists") or raw_row.get("primary_action")),
            "dominant_interaction_pattern": _clean_scalar(raw_row.get("dominant_interaction_pattern")),
            "route": _clean_scalar(raw_row.get("route") or raw_row.get("route_pattern")),
            "canonical_page_id": _clean_scalar(raw_row.get("canonical_page_id")),
            "surface_variant": _clean_scalar(raw_row.get("surface_variant")),
            "audience_mode": _clean_scalar(raw_row.get("audience_mode")),
            "session_role_source": _clean_scalar(raw_row.get("session_role_source")),
            "workspace_entry_roles": _clean_list(raw_row.get("workspace_entry_roles")),
            "route_reachability_mode": _clean_scalar(raw_row.get("route_reachability_mode")),
            "navigation_scope": _clean_scalar(raw_row.get("navigation_scope")),
            "handoff_visibility": _clean_scalar(raw_row.get("handoff_visibility")),
            "forbidden_exposure": _clean_list(raw_row.get("forbidden_exposure")),
        }

    table_lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    if len(table_lines) >= 3:
        headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
        required_headers = {
            "page_id",
            "page_name",
            "page_blueprint_type",
            "primary_actor",
            "primary_action",
            "route_pattern",
            "parent_page",
        }
        if required_headers.issubset(set(headers)):
            entries: list[dict[str, str]] = []
            for line in table_lines[2:]:
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if len(cells) < len(headers):
                    cells.extend([""] * (len(headers) - len(cells)))
                row = dict(zip(headers, cells))
                entry = _build_entry(row)
                if entry["page_name"]:
                    entries.append(entry)
            if entries:
                return entries

    parts = re.split(r"(?m)^\s{2}-\s+page_\d+:\s*$", section)
    entries: list[dict[str, str]] = []
    for block in parts[1:]:
        entry = _build_entry(
            {
                "page_name": _extract_single_nested_value(block, "page_name"),
                "page_role": _extract_single_nested_value(block, "page_role"),
                "page_blueprint_type": _extract_single_nested_value(block, "page_blueprint_type"),
                "primary_actor": _extract_single_nested_value(block, "primary_actor"),
                "why_it_exists": _extract_single_nested_value(block, "why_it_exists"),
                "dominant_interaction_pattern": _extract_single_nested_value(block, "dominant_interaction_pattern"),
                "route": _extract_single_nested_value(block, "route"),
                "route_pattern": _extract_single_nested_value(block, "route_pattern"),
                "canonical_page_id": _extract_single_nested_value(block, "canonical_page_id"),
                "surface_variant": _extract_single_nested_value(block, "surface_variant"),
                "audience_mode": _extract_single_nested_value(block, "audience_mode"),
                "session_role_source": _extract_single_nested_value(block, "session_role_source"),
                "workspace_entry_roles": _extract_single_nested_value(block, "workspace_entry_roles") or ", ".join(_extract_nested_bullets(block, "workspace_entry_roles")),
                "route_reachability_mode": _extract_single_nested_value(block, "route_reachability_mode"),
                "navigation_scope": _extract_single_nested_value(block, "navigation_scope"),
                "handoff_visibility": _extract_single_nested_value(block, "handoff_visibility"),
                "forbidden_exposure": ", ".join(_extract_nested_bullets(block, "forbidden_exposure")),
            }
        )
        if entry["page_name"]:
            entries.append(entry)
    return entries



def _extract_page_names_from_prototype_spec(prototype_spec_text: str) -> list[str]:
    return [
        str(entry.get("page_name") or "").strip()
        for entry in _extract_page_map_entries_from_prototype_spec(prototype_spec_text)
        if str(entry.get("page_name") or "").strip()
    ]


def _is_placeholder_surface(value: str) -> bool:
    normalized = str(value).strip()
    if not normalized:
        return False
    lowered = normalized.casefold()
    return bool(
        re.fullmatch(r"module[-\s]*\d+", lowered)
        or re.fullmatch(r"模块\s*\(module\)\s*\d+", lowered)
        or re.fullmatch(r"模块\s*\d+", lowered)
    )


def _extract_main_flow_goals_from_prototype_spec(prototype_spec_text: str) -> dict[str, list[str]]:
    section = "\n".join(_extract_markdown_section_lines(prototype_spec_text, r"main flow|主流程"))
    if not section.strip():
        return {}
    goals_by_page: dict[str, list[str]] = {}
    current_page = ""
    for raw in section.splitlines():
        line = raw.strip()
        from_match = re.search(r"-\s*from_page:\s*`?([^`\n]+)`?", line)
        if from_match:
            current_page = from_match.group(1).strip()
            goals_by_page.setdefault(current_page, [])
            continue
        goal_match = re.search(r"-\s*user_goal:\s*(.+)", line)
        if goal_match and current_page:
            goal = goal_match.group(1).strip()
            if goal:
                goals_by_page.setdefault(current_page, []).append(goal)
    return goals_by_page


def _looks_like_dependency_copy(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    lowered = normalized.casefold()
    return (
        lowered.startswith("depends on ")
        or lowered.startswith("dependent on ")
        or " depends on " in lowered
        or "依赖" in normalized
    )


def _semantic_page_role(page_role: str, page_blueprint_type: str) -> str:
    normalized_role = str(page_role or "").strip().lower()
    if normalized_role in {"workspace", "list", "detail", "workflow", "review", "form-flow"}:
        return normalized_role
    blueprint = _normalize_blueprint_type(page_blueprint_type, preserve_unknown=True)
    if blueprint in {"dashboard", "analysis-board", "execution-workbench"}:
        return "workspace"
    if blueprint == "setup-flow":
        return "form-flow"
    if blueprint == "record-workbench":
        return "workflow"
    if blueprint == "detail-view":
        return "detail"
    if blueprint == "review-decision":
        return "review"
    return normalized_role or "workflow"


def _surface_goal_candidate(value: Any) -> str:
    return str(value or "").strip().strip("`")


def _surface_goal_score(candidate: str, *, page_name: str, localized_title: str) -> int:
    cleaned = _surface_goal_candidate(candidate)
    if not cleaned or _looks_like_dependency_copy(cleaned) or _looks_like_meta_surface_copy(cleaned):
        return -10_000
    lowered = cleaned.casefold()
    score = 0
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    score += min(len(words), 10)
    action_signals = (
        "create",
        "update",
        "record",
        "review",
        "accept",
        "complete",
        "capture",
        "confirm",
        "schedule",
        "register",
        "collect",
        "pay",
        "submit",
        "close",
        "advance",
        "inspect",
        "登记",
        "创建",
        "更新",
        "记录",
        "审核",
        "评审",
        "接受",
        "提交",
        "确认",
        "排班",
        "支付",
        "关闭",
        "推进",
    )
    if any(signal in lowered for signal in action_signals):
        score += 8
    if "->" in cleaned or "→" in cleaned:
        score += 3
    if len(words) <= 2 and not any(signal in lowered for signal in action_signals):
        score -= 5
    normalized_page_name = str(page_name or "").strip().casefold()
    normalized_title = str(localized_title or "").strip().casefold()
    if normalized_page_name and lowered == normalized_page_name:
        score -= 4
    if normalized_title and lowered == normalized_title:
        score -= 4
    return score


def _best_surface_goal(
    *,
    surface: dict[str, Any],
    prototype_page_contract: dict[str, Any],
    page_name: str,
    main_flow_goals: dict[str, list[str]],
    localized_title: str,
) -> str:
    candidates = [
        _surface_goal_candidate(surface.get("primary_user_goal")),
        *[_surface_goal_candidate(goal) for goal in main_flow_goals.get(page_name, [])],
        _surface_goal_candidate(prototype_page_contract.get("action_model")),
        _surface_goal_candidate(surface.get("primary_action")),
    ]
    best_value = ""
    best_score = -10_000
    for candidate in candidates:
        score = _surface_goal_score(candidate, page_name=page_name, localized_title=localized_title)
        if score > best_score:
            best_value = candidate
            best_score = score
    if best_value:
        return best_value
    return localized_title


_META_SURFACE_COPY_PATTERNS = (
    "selected object",
    "context preserved",
    "return with context",
    "necessary update",
    "downstream actor",
    "queryable together",
    "decision-support",
    "role/status summary",
    "without hiding uncertainty",
)
_ACTION_PRIORITY = {
    "submit": 10,
    "record": 9,
    "start": 9,
    "create": 8,
    "save": 8,
    "update": 7,
    "confirm": 7,
    "review": 6,
    "approve": 6,
    "accept": 6,
    "schedule": 6,
    "register": 6,
    "open": 5,
    "load": 4,
    "select": 4,
}


def _looks_like_meta_surface_copy(value: str) -> bool:
    cleaned = normalize_inline_locale_variants(_surface_goal_candidate(value), "en")
    if not cleaned or _looks_like_dependency_copy(cleaned):
        return True
    lowered = cleaned.casefold()
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    action_signals = tuple(_ACTION_PRIORITY.keys()) + (
        "inspect",
        "close",
        "pay",
        "登记",
        "创建",
        "更新",
        "记录",
        "审核",
        "评审",
        "接受",
        "提交",
        "确认",
        "排班",
        "支付",
        "关闭",
        "推进",
        "打开",
        "开始",
        "保存",
    )
    if any(pattern in lowered for pattern in _META_SURFACE_COPY_PATTERNS):
        return True
    if re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+){2,}", cleaned):
        return True
    english_action_signals = [signal for signal in action_signals if re.fullmatch(r"[A-Za-z ]+", signal)]
    non_latin_action_signals = [signal for signal in action_signals if not re.fullmatch(r"[A-Za-z ]+", signal)]
    starts_with_action = any(lowered.startswith(f"{signal} ") or lowered == signal for signal in english_action_signals)
    if not starts_with_action:
        starts_with_action = any(cleaned.startswith(signal) for signal in non_latin_action_signals)
    generic_goal_nouns = ("record", "records", "detail", "details", "summary", "queue", "workspace", "report")
    if len(words) <= 3 and any(lowered.endswith(f" {noun}") or lowered == noun for noun in generic_goal_nouns) and not starts_with_action:
        return True
    return len(words) <= 3 and not starts_with_action


def _normalized_object_phrase(business_objects: list[str], page_title: str, *, locale: str) -> str:
    object_labels = [
        normalize_inline_locale_variants(localize_information_object(str(item), locale), locale).strip()
        for item in business_objects
        if str(item).strip()
    ]
    object_labels = [item for item in object_labels if item]
    if object_labels:
        if is_zh_locale(locale):
            return "、".join(object_labels[:2])
        return " and ".join(object_labels[:2])
    return page_title or ("当前记录" if is_zh_locale(locale) else "current record")


def _strip_role_prefix(candidate: str, allowed_roles: list[str], *, locale: str) -> str:
    text = normalize_inline_locale_variants(candidate, locale).strip()
    for role in allowed_roles:
        normalized_role = normalize_role_display_name(role, locale)
        if not normalized_role:
            continue
        text = re.sub(rf"^\s*{re.escape(normalized_role)}\s+", "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalize_goal_clause(clause: str, *, locale: str) -> str:
    candidate = normalize_inline_locale_variants(clause, locale)
    candidate = re.sub(r"\b(?:system|service) validates\b", "review" if not is_zh_locale(locale) else "查看", candidate, flags=re.IGNORECASE)
    candidate = candidate.strip(" ,;:.。；，")
    replacements = (
        (r"^opens\b", "open"),
        (r"^creates\b", "create"),
        (r"^starts\b", "start"),
        (r"^registers\b", "register"),
        (r"^reviews\b", "review"),
        (r"^records\b", "record"),
        (r"^selects\b", "select"),
        (r"^updates\b", "update"),
        (r"^confirms\b", "confirm"),
        (r"^accepts\b", "accept"),
        (r"^loads\b", "load"),
        (r"^saves\b", "save"),
        (r"^checks in\b", "check in"),
        (r"^pays\b", "record payment"),
    )
    for pattern, replacement in replacements:
        candidate = re.sub(pattern, replacement, candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if not candidate:
        return ""
    if not is_zh_locale(locale):
        candidate = candidate[:1].upper() + candidate[1:]
    return candidate


def _fallback_action_label(
    *,
    action_type: str,
    page_title: str,
    page_role: str,
    business_objects: list[str],
    locale: str,
) -> str:
    target = _normalized_object_phrase(business_objects, page_title, locale=locale)
    normalized_action_type = str(action_type or "").strip().lower()
    if is_zh_locale(locale):
        verb_map = {
            "create": "创建",
            "update": "更新",
            "review": "审核",
            "accept": "接收",
            "confirm": "确认",
            "load_context": "打开",
            "load": "加载",
            "list": "查看",
            "read": "查看",
            "save": "保存",
            "submit": "提交",
            "start": "开始",
        }
        verb = verb_map.get(normalized_action_type)
        if verb:
            return f"{verb}{target}"
        if page_role == "review":
            return "记录决策"
        return f"处理{target}"
    verb_map = {
        "create": "Create",
        "update": "Update",
        "review": "Review",
        "accept": "Accept",
        "confirm": "Confirm",
        "load_context": "Open",
        "load": "Load",
        "list": "Review",
        "read": "Review",
        "save": "Save",
        "submit": "Submit",
        "start": "Start",
    }
    verb = verb_map.get(normalized_action_type)
    if verb:
        return f"{verb} {target}"
    if page_role == "review":
        return "Record decision"
    return f"Work on {target}"


def _compact_action_label(
    value: str,
    *,
    locale: str,
    action_type: str,
    page_title: str,
    page_role: str,
    business_objects: list[str],
    allowed_roles: list[str],
) -> str:
    candidate = _strip_role_prefix(value, allowed_roles, locale=locale)
    if not candidate or _looks_like_meta_surface_copy(candidate):
        return _fallback_action_label(
            action_type=action_type,
            page_title=page_title,
            page_role=page_role,
            business_objects=business_objects,
            locale=locale,
        )
    parts = [
        _normalize_goal_clause(part, locale=locale)
        for part in re.split(r"\s*(?:->|→|\band\b|\bthen\b|;)\s*", candidate, flags=re.IGNORECASE)
        if part.strip()
    ]
    parts = [part for part in parts if part]
    if not parts:
        return _fallback_action_label(
            action_type=action_type,
            page_title=page_title,
            page_role=page_role,
            business_objects=business_objects,
            locale=locale,
        )
    def score(part: str) -> tuple[int, int]:
        lowered = part.casefold()
        priority = next((value for verb, value in _ACTION_PRIORITY.items() if lowered.startswith(f"{verb} ")), 0)
        return priority, -len(part)
    return sorted(parts, key=score, reverse=True)[0]


def _fallback_page_facing_goal(
    *,
    page_role: str,
    page_title: str,
    business_objects: list[str],
    locale: str,
) -> str:
    target = _normalized_object_phrase(business_objects, page_title, locale=locale)
    if is_zh_locale(locale):
        if page_role == "form-flow":
            return f"录入{target}并继续下一步。"
        if page_role == "workflow":
            return f"更新当前{target}并保留结果可见。"
        if page_role == "review":
            return f"审核当前{target}并记录决策。"
        if page_role in {"workspace", "list"}:
            return f"定位需要处理的{target}并继续办理。"
        return f"查看当前{target}并完成本页任务。"
    if page_role == "form-flow":
        return f"Enter the required {target.lower()} details and continue."
    if page_role == "workflow":
        return f"Update the current {target.lower()} and keep the result visible."
    if page_role == "review":
        return f"Review the current {target.lower()} and record the decision."
    if page_role in {"workspace", "list"}:
        return f"Find the {target.lower()} that needs action and continue."
    return f"Review the current {target.lower()} and complete the task on this page."


def _normalize_page_facing_goal(
    value: str,
    *,
    locale: str,
    page_role: str,
    page_title: str,
    business_objects: list[str],
    allowed_roles: list[str],
) -> str:
    candidate = _strip_role_prefix(value, allowed_roles, locale=locale)
    candidate = re.sub(r"\bwithout hiding uncertainty\b", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\bbefore proceeding\b", "", candidate, flags=re.IGNORECASE)
    if not candidate or _looks_like_meta_surface_copy(candidate):
        return _fallback_page_facing_goal(
            page_role=page_role,
            page_title=page_title,
            business_objects=business_objects,
            locale=locale,
        )
    parts = [
        _normalize_goal_clause(part, locale=locale)
        for part in re.split(r"\s*(?:->|→|\bthen\b|;)\s*", candidate, flags=re.IGNORECASE)
        if part.strip()
    ]
    parts = [part for part in parts if part and not _looks_like_meta_surface_copy(part)]
    if not parts:
        return _fallback_page_facing_goal(
            page_role=page_role,
            page_title=page_title,
            business_objects=business_objects,
            locale=locale,
        )
    if is_zh_locale(locale):
        sentence = "，并".join(parts[:2]).strip("，")
        return sentence if sentence.endswith("。") else f"{sentence}。"
    sentence = " and ".join(parts[:2]).strip()
    return sentence if sentence.endswith(".") else f"{sentence}."


def _surface_name_from_goals(goals: list[str], *, locale: str) -> str:
    haystack = " ".join(str(goal).strip() for goal in goals if str(goal).strip())
    lowered = haystack.casefold()
    if not lowered:
        return ""
    if any(token in lowered for token in ("pet", "register", "first visit", "invoice review")) or any(
        token in haystack for token in ("宠物", "建档", "登记", "账单复核")
    ):
        return "前台登记与账单复核 / front-desk-intake-billing" if is_zh_locale(locale) else "Front desk intake and billing / front-desk-intake-billing"
    if "payment" in lowered or "支付" in haystack or "paid" in lowered:
        return "收费结算 / payments" if is_zh_locale(locale) else "Payment settlement / payments"
    if any(token in lowered for token in ("checked-in", "check in", "visit completed", "auto-generates invoice", "opens checked-in")) or any(
        token in haystack for token in ("接诊", "已到诊", "就诊完成")
    ):
        return "接诊队列与就诊流转 / visit-flow" if is_zh_locale(locale) else "Visit flow / visit-flow"
    if any(token in lowered for token in ("prescription", "diagnosis", "symptoms", "examination", "drug stock")) or any(
        token in haystack for token in ("处方", "诊断", "症状")
    ):
        return "就诊记录与处方 / visit-records-prescriptions" if is_zh_locale(locale) else "Visit records and prescriptions / visit-records-prescriptions"
    if "appointment" in lowered or "预约" in haystack:
        return "预约管理 / appointments" if is_zh_locale(locale) else "Appointment scheduling / appointments"
    return ""


def _resolve_business_surfaces_from_prototype_spec(prototype_spec_text: str, *, locale: str) -> list[str]:
    page_names = _extract_page_names_from_prototype_spec(prototype_spec_text)
    if not page_names or not any(_is_placeholder_surface(name) for name in page_names):
        return page_names
    goals_by_page = _extract_main_flow_goals_from_prototype_spec(prototype_spec_text)
    resolved: list[str] = []
    for page_name in page_names:
        inferred = _surface_name_from_goals(goals_by_page.get(page_name, []), locale=locale) if _is_placeholder_surface(page_name) else ""
        resolved.append(inferred or page_name)
    return resolved


def _extract_primary_surfaces(stage04_text: str, prototype_spec_text: str = "") -> list[str]:
    if prototype_spec_text:
        prototype_pages = _resolve_business_surfaces_from_prototype_spec(
            prototype_spec_text,
            locale=infer_ui_locale(prototype_spec_text),
        )
        if prototype_pages:
            return prototype_pages[:8]
    surfaces: list[str] = []
    lines = stage04_text.splitlines()
    in_section = False
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("- primary_surfaces:"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("- ") and (
                stripped.endswith(":") or re.match(r"^- [a-z0-9_]+:", stripped)
            ):
                break
            tick_match = re.match(r"^- `([^`]+)`(?:\s+\(.+\))?$", stripped)
            if tick_match:
                surfaces.append(tick_match.group(1).strip())
            elif stripped.startswith("- "):
                surfaces.append(stripped[2:].strip("` ").strip())
    return [surface for surface in surfaces if surface][:8]


def _dedupe_surfaces(surfaces: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for surface in surfaces:
        normalized = str(surface).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _surface_list_has_onboarding(surfaces: list[str]) -> bool:
    for surface in surfaces:
        lowered = str(surface).strip().lower()
        if not lowered:
            continue
        if "onboarding" in lowered or "setup" in lowered:
            return True
        if any(token in str(surface) for token in ("接入", "范围", "配置")):
            return True
    return False


def _ensure_required_primary_surfaces(
    primary_surfaces: list[str],
    endpoints: list[dict[str, str]],
) -> list[str]:
    surfaces = _dedupe_surfaces(primary_surfaces)
    if not surfaces:
        return surfaces
    operation_ids = {
        str(endpoint.get("operation_id") or "").strip()
        for endpoint in endpoints
        if str(endpoint.get("operation_id") or "").strip()
    }
    requires_onboarding = bool(
        operation_ids & {"GetTenantAccessPolicy", "CreateTrackedScope", "StartObservationRun"}
    )
    if requires_onboarding and not _surface_list_has_onboarding(surfaces):
        surfaces = ["Onboarding / scope setup", *surfaces]
    return surfaces[:8]


def _extract_phase1_prd_path(stage04_text: str, phase2_root: Path) -> Path | None:
    match = re.search(r"- phase1_prd:\s*`?([^`\n]+)`?", stage04_text)
    if not match:
        return None
    return _resolve_phase_artifact_path(match.group(1), phase2_root)


def _candidate_relocated_artifact_paths(raw: str, phase2_root: Path) -> list[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    normalized = str(raw or "").strip().replace("\\", "/")
    if not normalized:
        return []

    suffix_candidates: list[Path] = []
    anchor = "tmp/local-artifacts/"
    if anchor in normalized:
        anchor_suffix = normalized.split(anchor, 1)[1].strip("/")
        if anchor_suffix:
            suffix_candidates.append(Path("tmp") / "local-artifacts" / anchor_suffix)
            suffix_candidates.append(Path(anchor_suffix))

    raw_path = Path(normalized)
    for tail_size in (4, 3, 2):
        if len(raw_path.parts) >= tail_size:
            suffix_candidates.append(Path(*raw_path.parts[-tail_size:]))

    search_roots: list[Path] = []
    for candidate in (
        phase2_root.resolve(),
        phase2_root.resolve().parent if phase2_root.resolve().parent.name == "local-artifacts" else None,
        repo_root / "tmp" / "local-artifacts",
        repo_root,
    ):
        if candidate is None or not candidate.exists() or candidate in search_roots:
            continue
        search_roots.append(candidate)

    direct_candidates: list[Path] = []
    for root in search_roots:
        for suffix in suffix_candidates:
            candidate = (root / suffix).resolve()
            if candidate.exists() and candidate not in direct_candidates:
                direct_candidates.append(candidate)
    if direct_candidates:
        return direct_candidates

    filename = raw_path.name
    if not filename:
        return []

    matches: list[Path] = []
    for root in search_roots:
        for candidate in root.rglob(filename):
            if candidate.is_file() and candidate not in matches:
                matches.append(candidate)

    if not matches:
        return []

    ordered_suffixes = sorted(
        [suffix.as_posix() for suffix in suffix_candidates if str(suffix)],
        key=lambda value: value.count("/"),
        reverse=True,
    )

    def sort_key(path: Path) -> tuple[int, int, str]:
        rendered = path.as_posix()
        best_suffix_depth = 0
        for suffix in ordered_suffixes:
            if rendered.endswith(suffix):
                best_suffix_depth = max(best_suffix_depth, suffix.count("/") + 1)
        return (-best_suffix_depth, len(path.parts), rendered)

    return sorted(matches, key=sort_key)


def _resolve_phase_artifact_path(raw: str, phase2_root: Path) -> Path | None:
    cleaned = str(raw or "").strip().strip("`")
    if not cleaned:
        return None
    candidate = Path(cleaned)
    if not candidate.is_absolute():
        candidate = (phase2_root / candidate).resolve()
    if candidate.exists():
        return candidate
    relocated_candidates = _candidate_relocated_artifact_paths(cleaned, phase2_root)
    return relocated_candidates[0] if relocated_candidates else None


def _extract_phase1_prototype_spec_path(stage04_text: str, phase2_root: Path) -> Path | None:
    explicit_match = re.search(r"- phase1_prototype_spec:\s*`?([^`\n]+)`?", stage04_text)
    if explicit_match:
        candidate = _resolve_phase_artifact_path(explicit_match.group(1), phase2_root)
        if candidate is not None:
            return candidate
    prd_path = _extract_phase1_prd_path(stage04_text, phase2_root)
    if not prd_path:
        return None
    candidate = prd_path.parent / "prototype-spec.md"
    return candidate if candidate.exists() else None


def _extract_phase1_prototype_prompt_pack_path(stage04_text: str, phase2_root: Path) -> Path | None:
    explicit_match = re.search(r"- phase1_prototype_prompt_pack:\s*`?([^`\n]+)`?", stage04_text)
    if explicit_match:
        candidate = _resolve_phase_artifact_path(explicit_match.group(1), phase2_root)
        if candidate is not None:
            return candidate
    prd_path = _extract_phase1_prd_path(stage04_text, phase2_root)
    if not prd_path:
        return None
    candidate = prd_path.parent / "prototype-prompt-pack.md"
    return candidate if candidate.exists() else None


def _extract_phase1_interaction_flow_contract_path(stage04_text: str, phase2_root: Path) -> Path | None:
    explicit_match = re.search(r"- phase1_interaction_flow_contract:\s*`?([^`\n]+)`?", stage04_text)
    if explicit_match:
        candidate = _resolve_phase_artifact_path(explicit_match.group(1), phase2_root)
        if candidate is not None:
            return candidate
    prd_path = _extract_phase1_prd_path(stage04_text, phase2_root)
    if not prd_path:
        return None
    candidate = prd_path.parent / "prototype-interaction-flow-contract.md"
    return candidate if candidate.exists() else None


def _extract_document_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    match = re.search(r"^- document_name:\s*`?([^`\n]+)`?", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _normalize_product_name(document_heading: str) -> str:
    candidate = str(document_heading).strip()
    if not candidate:
        return ""
    for suffix in (
        " Product Requirements Document",
        " PRD",
        " 产品需求文档",
    ):
        if candidate.endswith(suffix):
            candidate = candidate[: -len(suffix)].strip()
            break
    return candidate or document_heading.strip()


def _extract_markdown_section_lines(text: str, heading_pattern: str) -> list[str]:
    lines = text.splitlines()
    start: int | None = None
    heading_level = 0
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if not heading_match:
            continue
        level = len(heading_match.group(1))
        title = heading_match.group(2).strip()
        if start is None and re.search(heading_pattern, title, re.IGNORECASE):
            start = index + 1
            heading_level = level
            continue
        if start is not None and level <= heading_level:
            return lines[start:index]
    return lines[start:] if start is not None else []


def _extract_bullet_items_from_section(text: str, heading_pattern: str) -> list[str]:
    items: list[str] = []
    for raw in _extract_markdown_section_lines(text, heading_pattern):
        stripped = raw.strip()
        if not re.match(r"^[-*]\s+", stripped):
            continue
        item = re.sub(r"^[-*]\s+", "", stripped).strip()
        if item:
            items.append(item)
    return items


def _normalized_field_variants(value: str) -> set[str]:
    candidate = re.sub(r"\s+", " ", str(value or "").strip().strip("`")).lower().replace("_", " ")
    if not candidate:
        return set()
    variants = {candidate.strip(" :-")}
    without_parens = re.sub(r"\([^)]*\)", " ", candidate)
    variants.add(re.sub(r"\s+", " ", without_parens).strip(" :-"))
    for match in re.findall(r"\(([^)]*)\)", candidate):
        inner = re.sub(r"\s+", " ", match.replace("_", " ")).strip(" :-")
        if inner:
            variants.add(inner)
    expanded = set(variants)
    for item in list(variants):
        for part in re.split(r"[／/|]", item):
            cleaned = re.sub(r"\s+", " ", part).strip(" :-")
            if cleaned:
                expanded.add(cleaned)
    return {item for item in expanded if item}


def _field_key_matches(raw_key: str, expected_field: str) -> bool:
    expected_variants = _normalized_field_variants(expected_field)
    if not expected_variants:
        return False
    return bool(_normalized_field_variants(raw_key) & expected_variants)


def _extract_nested_bullets(block: str, field: str, *, field_indent: int = 4, item_indent: int = 6) -> list[str]:
    lines = block.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        match = re.match(r"^-\s+(.+?):\s*$", stripped)
        if indent == field_indent and match and _field_key_matches(match.group(1), field):
            start_index = index + 1
            break
    if start_index is None:
        return []
    items: list[str] = []
    for line in lines[start_index:]:
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == field_indent and re.match(r"^-\s+.+?:\s*$", stripped):
            break
        nested = re.match(rf"^\s{{{item_indent}}}-\s+(.+?)\s*$", line)
        if nested:
            items.append(nested.group(1).strip().strip("`"))
            continue
        if line.strip() and (len(line) - len(line.lstrip())) < item_indent:
            break
    return items


def _extract_single_nested_value(block: str, field: str, *, field_indent: int = 4) -> str:
    for line in block.splitlines():
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        match = re.match(r"^-\s+(.+?):\s*(.+?)\s*$", stripped)
        if indent != field_indent or not match or not _field_key_matches(match.group(1), field):
            continue
        value = match.group(2).strip()
        if value.startswith("`") and value.endswith("`") and len(value) >= 2:
            value = value[1:-1].strip()
        return value
    return ""


def _split_compiled_values(raw: Any) -> list[str]:
    cleaned = str(raw or "").replace("`", "").strip()
    if not cleaned or cleaned in {"—", "-"}:
        return []
    return [
        value.strip()
        for value in re.split(r"\s*(?:,|;|(?<=\s)and(?=\s))\s*", cleaned, flags=re.IGNORECASE)
        if value.strip() and value.strip() not in {"—", "-"}
    ]


def _compiled_scalar(raw: Any) -> str:
    cleaned = str(raw or "").replace("`", "").strip()
    return "" if not cleaned or cleaned.lower() in {"—", "-", "none", "n/a"} else cleaned


_BLUEPRINT_TYPE_ALIASES = {
    "setup-flow": "setup-flow",
    "configuration": "setup-flow",
    "analysis-board": "analysis-board",
    "dashboard": "analysis-board",
    "dashboard-workbench": "analysis-board",
    "record-list": "analysis-board",
    "comparison": "analysis-board",
    "record-workbench": "record-workbench",
    "decision-workbench": "record-workbench",
    "record-editor": "record-workbench",
    "billing-settlement": "record-workbench",
    "workflow-step": "record-workbench",
    "execution-workbench": "execution-workbench",
    "queue-board": "execution-workbench",
    "review-decision": "review-decision",
    "detail-view": "detail-view",
    "entity-detail": "detail-view",
    "record-detail": "detail-view",
}


def _normalize_blueprint_type(page_blueprint_type: Any, *, preserve_unknown: bool = False) -> str:
    raw = str(page_blueprint_type or "").strip()
    if not raw:
        return ""
    normalized = re.sub(r"[\s_]+", "-", raw.lower())
    resolved = _BLUEPRINT_TYPE_ALIASES.get(normalized)
    if resolved:
        return resolved
    return raw if preserve_unknown else ""


_APP_SURFACE_DEFAULT_FORBIDDEN_EXPOSURE = [
    "role_switcher",
    "review_copy",
    "contract_metadata",
    "cross_role_cta",
]


def _default_navigation_scope(page_blueprint_type: str) -> str:
    normalized = _normalize_blueprint_type(page_blueprint_type, preserve_unknown=True)
    if normalized in {"setup-flow", "review-decision"}:
        return "flow"
    if normalized in {"analysis-board", "record-workbench", "execution-workbench", "detail-view"}:
        return "workspace"
    return "workspace"


def _default_route_reachability_mode(*, audience_mode: str, navigation_scope: str, workspace_entry_roles: list[str]) -> str:
    if audience_mode != "app":
        return "hidden"
    if workspace_entry_roles:
        return "direct"
    return "flow" if navigation_scope == "flow" else "direct"


def _surface_matrix_row_from_mapping(raw_row: dict[str, object], *, fallback_page_id: str) -> dict[str, Any]:
    page_name = str(raw_row.get("page_name") or "").strip().strip("`")
    route = str(raw_row.get("route") or raw_row.get("route_pattern") or "").strip().strip("`")
    if not route and page_name:
        route = f"/{_business_slug(page_name)}"
    return {
        "page_id": str(raw_row.get("page_id") or "").strip().strip("`") or fallback_page_id,
        "page_name": page_name,
        "route": route,
        "page_blueprint_type": str(raw_row.get("page_blueprint_type") or "").strip().strip("`"),
        "page_role": str(raw_row.get("page_role") or raw_row.get("parent_page") or "").strip().strip("`"),
        "primary_actor": str(raw_row.get("primary_actor") or "").strip().strip("`"),
        "allowed_roles": _split_compiled_values(raw_row.get("allowed_roles", "")),
        "primary_user_goal": str(raw_row.get("primary_user_goal") or raw_row.get("why_it_exists") or raw_row.get("primary_action") or "").strip().strip("`"),
        "primary_action": str(raw_row.get("primary_action") or "").strip().strip("`"),
        "business_objects": _split_compiled_values(raw_row.get("business_objects", "")),
        "must_show_together": _split_compiled_values(raw_row.get("must_show_together", "")),
        "required_regions": _split_compiled_values(raw_row.get("required_regions", "")),
        "entry_conditions": _compiled_scalar(raw_row.get("entry_conditions", "")),
        "exit_conditions": _compiled_scalar(raw_row.get("exit_conditions", "")),
        "next_route_candidates": _split_compiled_values(raw_row.get("next_route_candidates", "")),
        "denied_behavior": _compiled_scalar(raw_row.get("denied_behavior", "")),
        "readiness_status": str(raw_row.get("readiness_status") or "").strip().strip("`"),
        "blocked_reason": str(raw_row.get("blocked_reason") or "").strip().strip("`"),
        "canonical_page_id": _compiled_scalar(raw_row.get("canonical_page_id", "")),
        "surface_variant": _compiled_scalar(raw_row.get("surface_variant", "")),
        "audience_mode": _compiled_scalar(raw_row.get("audience_mode", "")),
        "session_role_source": _compiled_scalar(raw_row.get("session_role_source", "")),
        "auth_entry_route": _normalize_route_path(raw_row.get("auth_entry_route", "")),
        "auth_entry_label": _compiled_scalar(raw_row.get("auth_entry_label", "")),
        "workspace_entry_roles": _split_compiled_values(raw_row.get("workspace_entry_roles", "")),
        "route_reachability_mode": _compiled_scalar(raw_row.get("route_reachability_mode", "")),
        "navigation_scope": _compiled_scalar(raw_row.get("navigation_scope", "")),
        "handoff_visibility": _compiled_scalar(raw_row.get("handoff_visibility", "")),
        "forbidden_exposure": _split_compiled_values(raw_row.get("forbidden_exposure", "")),
    }


def _merge_blocked_reasons(existing: str, *additional: str) -> str:
    seen: list[str] = []
    for raw in (existing, *additional):
        value = str(raw or "").strip()
        if not value:
            continue
        if value not in seen:
            seen.append(value)
    return "; ".join(seen)


def _resolve_surface_contract_v2(
    *,
    surface: dict[str, Any],
    page_name: str,
    page_id: str,
    page_blueprint_type: str,
    allowed_roles: list[str],
    locale: str,
) -> tuple[dict[str, Any], list[str]]:
    explicit_canonical_page_id = _compiled_scalar(surface.get("canonical_page_id"))
    explicit_surface_variant = _compiled_scalar(surface.get("surface_variant"))
    explicit_audience_mode = _compiled_scalar(surface.get("audience_mode")).lower()
    explicit_session_role_source = _compiled_scalar(surface.get("session_role_source")).lower()
    explicit_auth_entry_route = _normalize_route_path(surface.get("auth_entry_route", ""))
    explicit_auth_entry_label = _compiled_scalar(surface.get("auth_entry_label"))
    explicit_workspace_entry_roles = [str(item).strip() for item in surface.get("workspace_entry_roles", []) if str(item).strip()]
    explicit_route_reachability_mode = _compiled_scalar(surface.get("route_reachability_mode")).lower()
    explicit_navigation_scope = _compiled_scalar(surface.get("navigation_scope")).lower()
    explicit_handoff_visibility = _compiled_scalar(surface.get("handoff_visibility")).lower()
    explicit_forbidden_exposure = [str(item).strip() for item in surface.get("forbidden_exposure", []) if str(item).strip()]
    has_explicit_v2 = any(
        [
            explicit_canonical_page_id,
            explicit_surface_variant,
            explicit_audience_mode,
            explicit_session_role_source,
            bool(explicit_workspace_entry_roles),
            explicit_route_reachability_mode,
            explicit_navigation_scope,
            explicit_handoff_visibility,
            bool(explicit_forbidden_exposure),
        ]
    )
    v2_required = has_explicit_v2 or len(allowed_roles) > 1
    audience_mode = explicit_audience_mode or "app"
    navigation_scope = explicit_navigation_scope or (_default_navigation_scope(page_blueprint_type) if audience_mode == "app" else "hidden")
    workspace_entry_roles = explicit_workspace_entry_roles if audience_mode == "app" else []
    default_auth_entry_route = (
        "/auth/login"
        if audience_mode == "app" and (explicit_session_role_source or "login_session") == "login_session"
        else ""
    )
    default_auth_entry_label = "登录" if is_zh_locale(locale) else "Sign in"
    contract = {
        "canonical_page_id": explicit_canonical_page_id or _business_slug(page_name or page_id),
        "surface_variant": explicit_surface_variant or _business_slug(page_name or page_id),
        "audience_mode": audience_mode,
        "session_role_source": explicit_session_role_source or ("login_session" if audience_mode == "app" else ""),
        "auth_entry_route": explicit_auth_entry_route or default_auth_entry_route,
        "auth_entry_label": explicit_auth_entry_label or (default_auth_entry_label if (explicit_auth_entry_route or default_auth_entry_route) else ""),
        "workspace_entry_roles": workspace_entry_roles,
        "route_reachability_mode": explicit_route_reachability_mode or _default_route_reachability_mode(
            audience_mode=audience_mode,
            navigation_scope=navigation_scope,
            workspace_entry_roles=workspace_entry_roles,
        ),
        "navigation_scope": navigation_scope,
        "handoff_visibility": explicit_handoff_visibility,
        "forbidden_exposure": explicit_forbidden_exposure or (list(_APP_SURFACE_DEFAULT_FORBIDDEN_EXPOSURE) if audience_mode == "app" else []),
        "v2_required": v2_required,
    }
    alerts: list[str] = []
    if v2_required and not explicit_canonical_page_id:
        alerts.append("surface v2 contract missing canonical_page_id")
    if v2_required and not explicit_surface_variant:
        alerts.append("surface v2 contract missing surface_variant")
    if v2_required and not explicit_audience_mode:
        alerts.append("surface v2 contract missing audience_mode")
    if audience_mode == "app" and v2_required and not explicit_session_role_source:
        alerts.append("surface v2 contract missing session_role_source")
    if audience_mode == "app" and contract["session_role_source"] == "login_session" and v2_required and not explicit_auth_entry_route:
        alerts.append("surface v2 contract missing auth_entry_route")
    if audience_mode == "app" and contract["session_role_source"] == "login_session" and v2_required and not explicit_auth_entry_label:
        alerts.append("surface v2 contract missing auth_entry_label")
    if audience_mode == "app" and v2_required and not explicit_navigation_scope:
        alerts.append("surface v2 contract missing navigation_scope")
    if audience_mode == "app" and v2_required and not explicit_forbidden_exposure:
        alerts.append("surface v2 contract missing forbidden_exposure")
    return contract, alerts



def _extract_surface_matrix_rows_from_prototype_spec(prototype_spec_text: str) -> list[dict[str, Any]]:
    section = "\n".join(_extract_markdown_section_lines(prototype_spec_text, r"surface matrix|page map|页面地图"))
    if not section.strip():
        return []
    table = first_table_with_headers(
        section,
        {"page_id", "page_name", "page_blueprint_type"},
        id_headers=("page_id",),
    )
    rows: list[dict[str, Any]] = []
    if table is not None:
        for row in table["rows"]:
            compiled_row = _surface_matrix_row_from_mapping(row, fallback_page_id=f"P{len(rows) + 1:02d}")
            if compiled_row["page_name"]:
                rows.append(compiled_row)
        if rows:
            return rows

    fields = {
        "page_id",
        "page_name",
        "route",
        "route_pattern",
        "page_role",
        "page_blueprint_type",
        "primary_actor",
        "allowed_roles",
        "primary_user_goal",
        "why_it_exists",
        "primary_action",
        "business_objects",
        "must_show_together",
        "required_regions",
        "entry_conditions",
        "exit_conditions",
        "next_route_candidates",
        "denied_behavior",
        "readiness_status",
        "blocked_reason",
        "canonical_page_id",
        "surface_variant",
        "audience_mode",
        "session_role_source",
        "auth_entry_route",
        "auth_entry_label",
        "workspace_entry_roles",
        "route_reachability_mode",
        "navigation_scope",
        "handoff_visibility",
        "forbidden_exposure",
    }
    current: dict[str, str] = {}
    page_index = 0
    for raw in section.splitlines():
        if re.match(r"^\s*-\s+page_\d+:\s*$", raw):
            if current.get("page_name"):
                page_index += 1
                rows.append(_surface_matrix_row_from_mapping(current, fallback_page_id=f"P{page_index:02d}"))
            current = {}
            continue
        field_match = re.match(r"^\s*-\s+([A-Za-z0-9_]+):\s*(.+?)?\s*$", raw)
        if not field_match:
            continue
        field = field_match.group(1).strip()
        if field not in fields:
            continue
        current[field] = (field_match.group(2) or "").strip().strip("`")
    if current.get("page_name"):
        page_index += 1
        rows.append(_surface_matrix_row_from_mapping(current, fallback_page_id=f"P{page_index:02d}"))
    return rows



def _extract_table_rows_from_heading(text: str, heading_pattern: str, required_headers: set[str], id_headers: tuple[str, ...]) -> list[dict[str, str]]:
    section = "\n".join(_extract_markdown_section_lines(text, heading_pattern))
    if not section.strip():
        return []
    table = first_table_with_headers(section, required_headers, id_headers=id_headers)
    if table is None:
        return []
    return [{key: str(value).strip().strip("`") for key, value in row.items()} for row in table["rows"]]


def _extract_interaction_matrix_rows(contract_text: str) -> list[dict[str, str]]:
    return _extract_table_rows_from_heading(
        contract_text,
        r"interaction matrix",
        {"interaction_id", "page_id", "region", "element_type", "interaction_pattern", "trigger_kind", "action_type", "user_intent"},
        ("interaction_id",),
    )


def _extract_flow_contract_rows(contract_text: str) -> list[dict[str, str]]:
    return _extract_table_rows_from_heading(
        contract_text,
        r"flow contract",
        {"flow_id", "use_case_id", "step_id", "from_page_id", "from_interaction_id", "next_page_id"},
        ("flow_id",),
    )


def _extract_interaction_enrichment_rows(text: str) -> list[dict[str, str]]:
    table = first_table_with_headers(
        text,
        {"interaction_id", "page_id", "input_schema_ref", "display_field_set", "validation_rules", "enabled_rule", "error_state", "readiness_status", "blocked_reason"},
        id_headers=("interaction_id",),
    )
    if table is None:
        return []
    return [{key: str(value).strip().strip("`") for key, value in row.items()} for row in table["rows"]]


def _extract_binding_matrix_rows(text: str) -> list[dict[str, str]]:
    table = first_table_with_headers(
        text,
        {"service_binding_id", "interaction_id", "use_case_id", "binding_mode", "domain_service", "api_endpoint", "http_method", "request_field_mapping", "response_field_mapping", "rbac_policy", "audit_event", "failure_codes", "readiness_status", "blocked_reason"},
        id_headers=("service_binding_id",),
    )
    if table is None:
        return []
    return [{key: str(value).strip().strip("`") for key, value in row.items()} for row in table["rows"]]


_VALUE_SOURCE_ALIASES = {
    "user_input": "user-input",
    "workflow_context": "workflow-context",
    "response_binding": "response-binding",
    "system_generated": "system-generated",
    "server_default": "server-default",
    "derived": "derived",
    "auth_session": "auth-session",
}

_INTERNAL_EXPOSURE_ALIASES = {
    "user_visible": "user_visible",
    "review_only": "review_only",
    "system_hidden": "system_hidden",
}

_HANDOFF_MATERIALIZATION_ALIASES = {
    "implicit_context": "implicit_context",
    "user_visible_summary": "user_visible_summary",
    "review_only": "review_only",
}


def _normalize_compiled_enum(raw: Any, *, aliases: dict[str, str]) -> str:
    cleaned = _compiled_scalar(raw).lower()
    if not cleaned:
        return ""
    normalized = re.sub(r"[\s-]+", "_", cleaned)
    return aliases.get(normalized, normalized)


def _normalize_value_source(raw: Any) -> str:
    return _normalize_compiled_enum(raw, aliases=_VALUE_SOURCE_ALIASES)


def _normalize_internal_exposure(raw: Any) -> str:
    return _normalize_compiled_enum(raw, aliases=_INTERNAL_EXPOSURE_ALIASES)


def _normalize_handoff_materialization(raw: Any) -> str:
    return _normalize_compiled_enum(raw, aliases=_HANDOFF_MATERIALIZATION_ALIASES)


def _parse_field_enum_map(raw: Any, *, normalizer: Callable[[Any], str]) -> dict[str, str]:
    cleaned = _compiled_scalar(raw)
    if not cleaned:
        return {}
    entries: dict[str, str] = {}
    for chunk in re.split(r"\s*[;,]\s*", cleaned):
        piece = str(chunk).strip().strip("`")
        if not piece:
            continue
        match = re.match(r"^(?P<field>[A-Za-z0-9_\.\[\]-]+)\s*(?:=|:)\s*(?P<value>[A-Za-z0-9_\-]+)$", piece)
        if not match:
            continue
        field = match.group("field").split(".")[-1].replace("[]", "").strip()
        value = normalizer(match.group("value"))
        if field and value:
            entries[field] = value
    return entries


def _input_source_from_value_source(value_source: str) -> str:
    if value_source == "workflow-context":
        return "workflow-context"
    if value_source == "response-binding":
        return "response-binding"
    return "user-input"


def _mapping_field_names(mapping_text: str, *, right_hand: bool = False) -> list[str]:
    names: list[str] = []
    for chunk in _split_compiled_values(mapping_text):
        left, _, right = chunk.partition("->")
        candidate = right if right_hand else left
        normalized = str(candidate).strip()
        if not normalized:
            continue
        field = normalized.split(".")[-1].replace("[]", "").strip()
        if field and field not in names and field not in {"request", "response", "query", "ui"}:
            names.append(field)
    return names

def _extract_prototype_page_contracts(prototype_spec_text: str) -> list[dict[str, Any]]:
    section = "\n".join(_extract_markdown_section_lines(prototype_spec_text, r"page briefs"))
    if not section.strip():
        return []
    parts = re.split(r"(?m)^\s{2}-\s+page_\d+:\s*$", section)
    page_contracts: list[dict[str, Any]] = []
    for block in parts[1:]:
        page_name = _extract_single_nested_value(block, "page_name")
        if not page_name:
            continue
        page_contracts.append(
            {
                "page_name": page_name,
                "page_role": _extract_single_nested_value(block, "page_role"),
                "page_blueprint_type": _extract_single_nested_value(block, "page_blueprint_type"),
                "primary_work_region": _extract_single_nested_value(block, "primary_work_region"),
                "secondary_support_regions": _extract_nested_bullets(block, "secondary_support_regions"),
                "dominant_component_pattern": _extract_single_nested_value(block, "dominant_component_pattern"),
                "action_model": _extract_single_nested_value(block, "action_model"),
                "forbidden_layout_patterns": _extract_nested_bullets(block, "forbidden_layout_patterns"),
                "must_show_together": _extract_nested_bullets(block, "must_show_together"),
                "required_user_inputs_or_confirmations": _extract_nested_bullets(block, "required_user_inputs_or_confirmations"),
                "render_blocks_in_order": _extract_nested_bullets(block, "render_blocks_in_order"),
                "field_groups": _extract_nested_bullets(block, "field_groups"),
                "input_controls": _extract_nested_bullets(block, "input_controls"),
                "summary_cards": _extract_nested_bullets(block, "summary_cards"),
                "detail_fields_in_order": _extract_nested_bullets(block, "detail_fields_in_order"),
                "table_columns": _extract_nested_bullets(block, "table_columns"),
                "filters_and_selectors": _extract_nested_bullets(block, "filters_and_selectors"),
                "required_status_messages": _extract_nested_bullets(block, "required_status_messages"),
                "primary_cta_label": _extract_single_nested_value(block, "primary_cta_label"),
                "secondary_ctas": _extract_nested_bullets(block, "secondary_ctas"),
                "submission_feedback": _extract_nested_bullets(block, "submission_feedback"),
                "context_arrives_from": _extract_single_nested_value(block, "context_arrives_from"),
                "context_must_continue_to": _extract_single_nested_value(block, "context_must_continue_to"),
                "executor_brief": _extract_nested_bullets(block, "executor_brief"),
            }
        )
    return page_contracts


def _extract_external_executor_brief(prototype_spec_text: str) -> list[str]:
    lines = prototype_spec_text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"^-\s+(.+?):\s*$", stripped)
        if match and _field_key_matches(match.group(1), "external_executor_brief"):
            start_index = index + 1
            break
    if start_index is None:
        return []
    items: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if re.match(r"^-\s+.+?:\s*$", stripped):
            break
        nested = re.match(r"^\s{2}-\s+(.+?)\s*$", line)
        if nested:
            items.append(nested.group(1).strip().strip("`"))
            continue
        if line.strip() and not line.startswith(" "):
            break
    return items


def _extract_prototype_generation_constraints(prototype_spec_text: str) -> dict[str, str]:
    section = "\n".join(_extract_markdown_section_lines(prototype_spec_text, r"prototype generation constraints"))
    if not section.strip():
        return {}
    match = re.search(
        r"^\s*-\s+prototype_generation_constraints:\s*$",
        section,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return {}
    constraints: dict[str, str] = {}
    for line in section[match.end() :].splitlines():
        if re.match(r"^\s*-\s+[A-Za-z0-9_]+:\s*$", line):
            break
        nested = re.match(r"^\s{2}-\s+([A-Za-z0-9_]+):\s*(.+?)\s*$", line)
        if nested:
            key = nested.group(1).strip()
            value = nested.group(2).strip()
            if not key or not value:
                continue
            if value.startswith("`") and value.endswith("`") and len(value) >= 2:
                value = value[1:-1].strip()
            if value:
                constraints[key] = value
            continue
        if line.strip() and not line.startswith(" "):
            break
    return constraints


def _extract_nested_items_after_key(document_text: str, key_pattern: str) -> list[str]:
    lines = document_text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"^-\s+(.+?):\s*$", stripped)
        if not match:
            continue
        if any(_field_key_matches(match.group(1), candidate.strip()) for candidate in key_pattern.split("|")):
            start_index = index + 1
            break
    if start_index is None:
        return []
    items: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if re.match(r"^-\s+.+?:\s*$", stripped):
            break
        nested = re.match(r"^\s{2}-\s+(.+?)\s*$", line)
        if nested:
            items.append(nested.group(1).strip().strip("`"))
            continue
        if line.strip() and not line.startswith(" "):
            break
    return items


def _is_meta_positioning_candidate(candidate: str) -> bool:
    lowered = str(candidate).strip().lower()
    if not lowered:
        return True
    blocked_tokens = (
        "该 prd 不是",
        "重编译",
        "recompile",
        "source summary",
        "main document",
        "完整主文档",
        "executive summary",
        "stage-01",
        "stage-02",
        "stage-03",
        "stage-04",
        "stage 1",
        "stage 2",
        "stage 3",
        "stage 4",
    )
    return any(token in lowered for token in blocked_tokens)


def _choose_positioning_candidate(candidates: list[str]) -> str:
    ranked: list[tuple[int, str]] = []
    for raw in candidates:
        candidate = str(raw).strip()
        if not candidate or _is_meta_positioning_candidate(candidate):
            continue
        lowered = candidate.lower()
        score = 0
        if any(token in lowered for token in ("promise", "value", "helps", "enable", "supports", "承诺", "闭环", "可观测", "可解释", "可执行", "可复盘")):
            score += 2
        if any(token in lowered for token in ("workflow-first", "step 1", "step 2", "step 3", "step 4", "step 5")):
            score -= 1
        ranked.append((score, candidate))
    if not ranked:
        return ""
    ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    candidate = ranked[0][1].strip()
    for separator in ("；", ";"):
        if separator not in candidate:
            continue
        head, tail = candidate.split(separator, 1)
        lowered_tail = tail.lower()
        if any(token in lowered_tail for token in ("不承诺", "未验证", "review-bound", "not promise", "unverified")):
            trimmed = head.strip().rstrip("，,")
            if trimmed and trimmed[-1] not in "。.!?":
                trimmed += "。" if re.search(r"[\u4e00-\u9fff]", trimmed) else "."
            return trimmed
    return candidate


def _extract_positioning_statement_from_prototype_spec(prototype_spec_text: str) -> str:
    candidates: list[str] = []
    value_promise_match = re.search(r"- first_wave_value_promise:\s*(.+)", prototype_spec_text)
    if value_promise_match:
        candidates.append(value_promise_match.group(1).strip())
    candidates.extend(_extract_nested_items_after_key(prototype_spec_text, r"current_product_context"))
    return _choose_positioning_candidate(candidates)


def _match_prototype_page_contract(
    surface_title: str,
    page_role: str,
    surface_source: str,
    prototype_page_contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    def bucket(value: str) -> str:
        lowered = value.strip().lower()
        if any(token in lowered for token in ("onboarding", "setup", "settings", "scope", "tenant", "permission", "接入", "配置", "设置", "范围")):
            return "settings"
        if any(token in lowered for token in ("overview", "dashboard", "baseline", "总览", "仪表板")):
            return "overview"
        if any(token in lowered for token in ("finding", "findings", "recommendation", "内容优化", "发现", "建议")):
            return "findings"
        if any(token in lowered for token in ("task", "任务")):
            return "tasks"
        if any(token in lowered for token in ("competitor", "竞品")):
            return "competitors"
        if any(token in lowered for token in ("review", "report", "复盘", "审核", "报告", "continue", "revise")):
            return "reports"
        if any(token in lowered for token in ("asset", "资产")):
            return "asset-detail"
        return lowered

    normalized_title = surface_title.strip().lower()
    for contract in prototype_page_contracts:
        page_name = str(contract.get("page_name") or "").strip()
        if not page_name:
            continue
        lowered_name = page_name.lower()
        if normalized_title == lowered_name or normalized_title in lowered_name or lowered_name in normalized_title:
            return contract
    for contract in prototype_page_contracts:
        if str(contract.get("page_role") or "").strip().lower() == page_role.strip().lower():
            return contract
    surface_bucket = bucket(surface_source or surface_title or page_role)
    for contract in prototype_page_contracts:
        contract_bucket = bucket(str(contract.get("page_role") or "")) or bucket(str(contract.get("page_name") or ""))
        if surface_bucket and surface_bucket == contract_bucket:
            return contract
    return {}


def _extract_primary_actor_from_prd(prd_text: str) -> str:
    patterns = (
        r"- chosen segment:\s*`?([^`\n]+)`?",
        r"- primary_boundary:\s*`?([^`\n]+)`?",
        r"- direct user:\s*([^`\n]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, prd_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_supporting_roles_from_prd(prd_text: str) -> list[str]:
    roles: list[str] = []
    for item in _extract_bullet_items_from_section(prd_text, r"secondary\s*/\s*supporting roles"):
        role = item.split(":", 1)[0].strip("` ").strip()
        if role:
            roles.append(role)
    return roles


def _extract_workflow_backbone_from_prd(
    prd_text: str,
    *,
    locale: str,
    primary_surfaces: list[str],
) -> list[dict[str, str]]:
    workflow_line = ""
    for line in prd_text.splitlines():
        if "Step 1" in line and "Step 2" in line and "Step 3" in line:
            workflow_line = line.strip()
            break
    matches = re.findall(r"(Step\s*\d+)\s*([^->。\n]+)", workflow_line)
    if matches:
        backbone: list[dict[str, str]] = []
        for index, (step, label) in enumerate(matches):
            backbone.append(
                {
                    "step": step.strip(),
                    "label": label.strip(" ：:"),
                    "surface": localize_surface_title(primary_surfaces[index], locale)
                    if index < len(primary_surfaces)
                    else label.strip(" ：:"),
                }
            )
        return backbone
    if primary_surfaces:
        return [
            {
                "step": f"Step {index + 1}",
                "label": localize_surface_title(surface, locale),
                "surface": localize_surface_title(surface, locale),
            }
            for index, surface in enumerate(primary_surfaces)
        ]
    return []


def _extract_design_guardrails_from_prd(prd_text: str) -> list[str]:
    items = _extract_bullet_items_from_section(prd_text, r"design can start")
    normalized: list[str] = []
    for item in items:
        candidate = str(item).strip()
        if not candidate:
            continue
        candidate = candidate.replace(
            "每个关键页面都要能映射回 模块 (module) responsibility、core objects 和状态推进。",
            "每个关键页面都要能映射回业务责任边界、核心对象和状态推进。",
        )
        candidate = candidate.replace(
            "Each critical page must map back to module responsibility, core objects, and state progression.",
            "Each critical page must map back to business responsibility, core objects, and state progression.",
        )
        normalized.append(candidate)
    return normalized[:8]


def _extract_positioning_statement_from_prd(prd_text: str) -> str:
    candidates: list[str] = []
    for raw in _extract_markdown_section_lines(prd_text, r"1\.\s*executive summary"):
        stripped = raw.strip()
        if stripped and not stripped.startswith("##") and not stripped.startswith("###"):
            candidates.append(stripped)
    for pattern in (
        r"- final_problem_statement:\s*(.+)",
        r"- product_scope:\s*(.+)",
    ):
        match = re.search(pattern, prd_text)
        if match:
            candidates.append(match.group(1).strip())
    return _choose_positioning_candidate(candidates)


def _extract_problem_statement_from_prd(prd_text: str) -> str:
    match = re.search(r"- final_problem_statement:\s*(.+)", prd_text)
    if match:
        return match.group(1).strip()
    for raw in _extract_markdown_section_lines(prd_text, r"synthesized problem narrative"):
        stripped = raw.strip()
        if stripped and not stripped.startswith("###"):
            return stripped
    return ""


def _extract_key_entities_from_stage03(stage03_text: str) -> list[str]:
    entities: list[str] = []
    in_table = False
    for raw in stage03_text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("| object |"):
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                break
            if stripped.startswith("| ---"):
                continue
            parts = [part.strip() for part in stripped.split("|")[1:-1]]
            if not parts:
                continue
            entity = parts[0]
            if entity and entity not in entities:
                entities.append(entity)
    return entities[:8]


def _purpose_information_object(purpose: str) -> str:
    for candidate in reversed(re.findall(r"`([^`]+)`", purpose)):
        if "." not in candidate and candidate.strip():
            return candidate.strip()
    for candidate in reversed(re.findall(r"`([^`]+)`", purpose)):
        normalized = candidate.split(".")[-1].strip()
        if normalized:
            return _humanize_identifier(normalized)
    return ""


def _information_objects_from_data_required(data_required: list[dict[str, Any]]) -> list[str]:
    objects: list[str] = []
    for item in data_required:
        if not isinstance(item, dict):
            continue
        purpose = str(item.get("purpose") or "").strip()
        object_name = _purpose_information_object(purpose)
        if object_name and object_name not in objects:
            objects.append(object_name)
    return objects[:6]


def _match_supporting_role(supporting_roles: list[str], keywords: tuple[str, ...]) -> str:
    for role in supporting_roles:
        lowered = role.lower()
        if any(keyword in lowered for keyword in keywords):
            return role
    return ""


def _default_page_actor(surface: str, *, primary_actor: str, supporting_roles: list[str]) -> list[str]:
    lowered = surface.lower()
    roles: list[str] = []
    content_role = _match_supporting_role(supporting_roles, ("content", "operator"))
    business_role = _match_supporting_role(supporting_roles, ("business", "owner"))
    compliance_role = _match_supporting_role(supporting_roles, ("legal", "it", "reviewer", "security", "compliance"))
    if any(token in lowered for token in ("onboarding", "setup")) or any(token in surface for token in ("接入", "配置")):
        roles.extend([primary_actor, compliance_role])
    elif any(token in lowered for token in ("overview", "findings")) or any(token in surface for token in ("总览", "发现")):
        roles.extend([primary_actor])
    elif any(token in lowered for token in ("recommendation", "detail", "export")) or any(token in surface for token in ("建议", "详情", "导出")):
        roles.extend([primary_actor, content_role])
    elif "task" in lowered or "任务" in surface:
        roles.extend([content_role, primary_actor])
    elif "review" in lowered or any(token in surface for token in ("审核", "复盘", "修订")):
        roles.extend([primary_actor, business_role])
    else:
        roles.extend([primary_actor])
    return [role for role in dict.fromkeys(role for role in roles if role)]


def _build_app_context(
    *,
    stage_04_text: str,
    phase2_root: Path,
    locale: str,
    primary_surfaces: list[str],
) -> dict[str, Any]:
    prd_path = _extract_phase1_prd_path(stage_04_text, phase2_root)
    prototype_spec_path = _extract_phase1_prototype_spec_path(stage_04_text, phase2_root)
    prototype_prompt_pack_path = _extract_phase1_prototype_prompt_pack_path(stage_04_text, phase2_root)
    prd_text = _read(prd_path) if prd_path else ""
    prototype_spec_text = _read(prototype_spec_path) if prototype_spec_path else ""
    stage03_text = _read(phase2_root / "stage-03-data-storage-and-interface-design.md")
    document_heading = _extract_document_heading(prd_text)
    product_name = _normalize_product_name(document_heading) or (
        "Runnable business application" if not is_zh_locale(locale) else "可操作业务应用"
    )
    product_heading = (
        f"{product_name} workbench" if not is_zh_locale(locale) else f"{product_name} 业务工作台"
    )
    positioning = _extract_positioning_statement_from_prototype_spec(prototype_spec_text) or _extract_positioning_statement_from_prd(prd_text) or (
        "Operate the core workflow with visible context, actionable inputs, and runnable backend bindings."
        if not is_zh_locale(locale)
        else "围绕主业务闭环执行范围配置、发现诊断、建议转任务和周期复盘，并保持页面与真实后端运行时联通。"
    )
    raw_primary_actor = _extract_primary_actor_from_prd(prd_text)
    primary_actor = normalize_role_display_name(raw_primary_actor, locale) or raw_primary_actor or (
        "workflow owner" if not is_zh_locale(locale) else "业务负责人"
    )
    supporting_roles = _dedupe_strings(
        [
            normalize_role_display_name(str(item).strip(), locale) or str(item).strip()
            for item in _extract_supporting_roles_from_prd(prd_text)
            if str(item).strip()
        ]
    )
    workflow_backbone = _extract_workflow_backbone_from_prd(
        prd_text,
        locale=locale,
        primary_surfaces=primary_surfaces,
    )
    key_entities = _extract_key_entities_from_stage03(stage03_text)
    design_guardrails = _extract_design_guardrails_from_prd(prd_text)
    external_executor_brief = _extract_external_executor_brief(prototype_spec_text)
    return {
        "product_name": product_name,
        "product_heading": product_heading,
        "locale": locale,
        "positioning": _text_with_visibility(
            positioning,
            "agent-internal",
            "shapes page design intent and product framing; do not render as user-visible UI copy",
        ),
        "problem_statement": _text_with_visibility(
            _extract_problem_statement_from_prd(prd_text),
            "agent-internal",
            "captures product/problem framing for implementation planning only",
        ),
        "primary_actor": _text_with_visibility(
            primary_actor,
            "agent-internal",
            "defines the target persona for design decisions; do not render as a visible persona badge",
        ),
        "supporting_roles": supporting_roles,
        "workflow_backbone": workflow_backbone,
        "key_entities": key_entities,
        "design_guardrails": design_guardrails,
        "external_executor_brief": external_executor_brief,
        "prototype_spec_path": str(prototype_spec_path) if prototype_spec_path else "",
        "prototype_prompt_pack_path": str(prototype_prompt_pack_path) if prototype_prompt_pack_path else "",
    }


ROLE_POLICY_SPLIT_RE = re.compile(r"\s*(?:,|/|;|\||、|，|\band\b|\bor\b)\s*", flags=re.IGNORECASE)
ROLE_POLICY_SKIP_TOKENS = {
    "role",
    "roles",
    "in",
    "is",
    "are",
    "allow",
    "allows",
    "allowed",
    "require",
    "requires",
    "required",
    "policy",
    "only",
    "any",
    "of",
    "with",
    "current",
    "user",
    "actor",
    "visible",
    "visibility",
}


def _normalize_role_label(value: Any, *, locale: str | None = None) -> str:
    text = str(value or "").strip().strip("`")
    text = re.sub(r"\s+", " ", text)
    if locale is None:
        return text
    return normalize_role_display_name(text, locale) or text


def _ordered_role_union(*groups: Any) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in groups:
        items = group if isinstance(group, list) else [group]
        for item in items:
            role = _normalize_role_label(item)
            if not role:
                continue
            key = role.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(role)
    return ordered


def _split_role_candidates(raw: str, *, locale: str | None = None) -> list[str]:
    text = _normalize_role_label(raw, locale=locale).strip("[]")
    if not text or text.lower() in {"—", "-", "none", "n/a", "not_applicable"}:
        return []
    candidates = [part.strip() for part in ROLE_POLICY_SPLIT_RE.split(text) if part.strip()]
    roles: list[str] = []
    for candidate in candidates or [text]:
        normalized = _normalize_role_label(candidate, locale=locale).strip("[]")
        if not normalized:
            continue
        lowered = normalized.casefold()
        if lowered in ROLE_POLICY_SKIP_TOKENS:
            continue
        roles.append(normalized)
    return _ordered_role_union(roles)


def _extract_roles_from_policy_text(raw: Any, *, locale: str | None = None) -> list[str]:
    text = _normalize_role_label(raw, locale=locale)
    if not text or text.lower() in {"—", "-", "none", "n/a", "not_applicable"}:
        return []
    roles: list[str] = []
    for match in re.findall(r"\[([^\]]+)\]", text):
        roles.extend(_split_role_candidates(match, locale=locale))
    if roles:
        return _ordered_role_union(roles)
    simplified = re.sub(r"\b(?:role|roles|allow|allows|allowed|require|requires|required|policy|visible|visibility)\b", " ", text, flags=re.IGNORECASE)
    simplified = re.sub(r"\b(?:in|is|are|only|any|of|with|for|current|user|actor)\b", " ", simplified, flags=re.IGNORECASE)
    simplified = re.sub(r"\s+", " ", simplified).strip(" -:")
    return _split_role_candidates(simplified, locale=locale)


def _page_allowed_roles(page: dict[str, Any], *, fallback_roles: list[str]) -> list[str]:
    page_locale = str(page.get("locale") or "").strip() or None
    explicit_roles = [
        _normalize_role_label(item, locale=page_locale)
        for item in page.get("allowed_roles", [])
        if _normalize_role_label(item, locale=page_locale)
    ]
    policy_roles: list[str] = []
    for interaction in page.get("compiled_interactions", []):
        if not isinstance(interaction, dict):
            continue
        policy_roles.extend(
            _extract_roles_from_policy_text(
                interaction.get("rbac_policy") or interaction.get("visibility_rule") or "",
                locale=page_locale,
            )
        )
    page_actor_roles = [
        _normalize_role_label(item, locale=page_locale)
        for item in page.get("page_actor", [])
        if _normalize_role_label(item, locale=page_locale)
    ]
    inferred_roles = _ordered_role_union(explicit_roles, policy_roles, page_actor_roles)
    if inferred_roles:
        return inferred_roles
    return _ordered_role_union(fallback_roles[:1])


def _page_has_mutating_action(page: dict[str, Any]) -> bool:
    for action in page.get("actions_and_transitions", []):
        if not isinstance(action, dict):
            continue
        method = str((action.get("api_binding") or {}).get("method") or "").strip().upper()
        if method and method != "GET":
            return True
    for interaction in page.get("compiled_interactions", []):
        if not isinstance(interaction, dict):
            continue
        trigger_kind = str(interaction.get("trigger_kind") or "").strip()
        method = str(interaction.get("http_method") or "").strip().upper()
        if trigger_kind and trigger_kind != "page_load" and method != "GET":
            return True
    return False


def _page_role_access_policy(page: dict[str, Any], *, allowed_roles: list[str]) -> dict[str, Any]:
    page_locale = str(page.get("locale") or "").strip() or None
    editable_roles: list[str] = []
    for interaction in page.get("compiled_interactions", []):
        if not isinstance(interaction, dict):
            continue
        trigger_kind = str(interaction.get("trigger_kind") or "").strip()
        method = str(interaction.get("http_method") or "").strip().upper()
        if trigger_kind == "page_load" or method == "GET":
            continue
        editable_roles = _ordered_role_union(
            editable_roles,
            _extract_roles_from_policy_text(
                interaction.get("rbac_policy") or interaction.get("visibility_rule") or "",
                locale=page_locale,
            ),
        )
    has_mutating_action = _page_has_mutating_action(page)
    if has_mutating_action and not editable_roles:
        editable_roles = allowed_roles[:]
    read_only_roles = [role for role in allowed_roles if role not in editable_roles]
    if not has_mutating_action and allowed_roles:
        read_only_roles = allowed_roles[:]
    default_access = "editable" if editable_roles else "read-only"
    return {
        "allowed_roles": allowed_roles,
        "editable_roles": editable_roles,
        "read_only_roles": read_only_roles,
        "default_access": default_access,
    }


def _derive_role_workspace_contract(*, pages: list[dict[str, Any]], app_context: dict[str, Any]) -> dict[str, Any]:
    role_locale = str(app_context.get("locale") or "").strip() or next(
        (str(page.get("locale") or "").strip() for page in pages if str(page.get("locale") or "").strip()),
        "en",
    )
    fallback_roles = _ordered_role_union(
        [
            _normalize_role_label(item, locale=role_locale)
            for item in app_context.get("supporting_roles", [])
            if _normalize_role_label(item, locale=role_locale)
        ],
        [_normalize_role_label(_visibility_text(app_context.get("primary_actor", "")), locale=role_locale)],
    )
    route_policies: dict[str, dict[str, Any]] = {}
    role_routes: dict[str, list[str]] = {}
    role_page_ids: dict[str, list[str]] = {}
    role_page_titles: dict[str, list[str]] = {}
    role_editable_routes: dict[str, list[str]] = {}
    explicit_entry_routes: dict[str, str] = {}
    session_role_candidates: list[str] = []
    derived_auth_entry_route = ""
    derived_auth_entry_label = ""
    default_route = str(pages[0].get("route") or "").strip() if pages else "/"

    for page in pages:
        route = str(page.get("route") or "").strip() or "/"
        allowed_roles = _page_allowed_roles(page, fallback_roles=fallback_roles)
        page_access = _page_role_access_policy(page, allowed_roles=allowed_roles)
        if isinstance(page.get("read_only_vs_editable_by_role"), dict):
            explicit_policy = page.get("read_only_vs_editable_by_role", {})
            page_access["editable_roles"] = _ordered_role_union(
                [
                    _normalize_role_label(item, locale=role_locale)
                    for item in explicit_policy.get("editable_roles", [])
                    if _normalize_role_label(item, locale=role_locale)
                ],
                page_access["editable_roles"],
            )
            page_access["read_only_roles"] = _ordered_role_union(
                [
                    _normalize_role_label(item, locale=role_locale)
                    for item in explicit_policy.get("read_only_roles", [])
                    if _normalize_role_label(item, locale=role_locale)
                ],
                page_access["read_only_roles"],
            )
            page_access["default_access"] = str(explicit_policy.get("default_access") or page_access["default_access"]).strip() or page_access["default_access"]
        page["allowed_roles"] = allowed_roles
        page["read_only_vs_editable_by_role"] = {
            "editable_roles": page_access["editable_roles"],
            "read_only_roles": page_access["read_only_roles"],
            "default_access": page_access["default_access"],
        }
        audience_mode = str(page.get("audience_mode") or "app").strip().lower()
        session_role_source = str(page.get("session_role_source") or "").strip().lower()
        workspace_entry_roles = _page_workspace_entry_roles(page, locale=role_locale)
        page["workspace_entry_roles"] = workspace_entry_roles
        navigation_scope = _page_navigation_scope(page)
        page["navigation_scope"] = navigation_scope
        route_reachability_mode = _page_route_reachability_mode(page, locale=role_locale)
        page["route_reachability_mode"] = route_reachability_mode
        if audience_mode in {"", "app"} and session_role_source == "login_session":
            session_role_candidates = _ordered_role_union(
                session_role_candidates,
                page_access["editable_roles"],
                allowed_roles[:1],
            )
            page_auth_entry_route = _normalize_route_path(page.get("auth_entry_route") or "")
            page_auth_entry_label = str(page.get("auth_entry_label") or "").strip()
            if page_auth_entry_route and not derived_auth_entry_route:
                derived_auth_entry_route = page_auth_entry_route
            if page_auth_entry_label and not derived_auth_entry_label:
                derived_auth_entry_label = page_auth_entry_label
        route_policies[route] = {
            "allowed_roles": allowed_roles,
            "editable_roles": page_access["editable_roles"],
            "read_only_roles": page_access["read_only_roles"],
            "workspace_entry_roles": workspace_entry_roles,
            "route_reachability_mode": route_reachability_mode,
            "navigation_scope": navigation_scope,
            "denied_behavior": "redirect-to-role-entry",
        }
        for role in workspace_entry_roles:
            if role in allowed_roles and role not in explicit_entry_routes:
                explicit_entry_routes[role] = route
        for role in allowed_roles:
            role_routes.setdefault(role, [])
            if route not in role_routes[role]:
                role_routes[role].append(route)
            role_page_ids.setdefault(role, [])
            page_id = str(page.get("page_id") or "").strip()
            if page_id and page_id not in role_page_ids[role]:
                role_page_ids[role].append(page_id)
            role_page_titles.setdefault(role, [])
            page_title = str(page.get("page_title") or "").strip()
            if page_title and page_title not in role_page_titles[role]:
                role_page_titles[role].append(page_title)
        for role in page_access["editable_roles"]:
            role_editable_routes.setdefault(role, [])
            if route not in role_editable_routes[role]:
                role_editable_routes[role].append(route)

    ordered_roles = _ordered_role_union(list(role_routes.keys())) if role_routes else _ordered_role_union(fallback_roles)
    derived_entry_routes: dict[str, str] = {}
    derived_workspaces: list[dict[str, Any]] = []
    for role in ordered_roles:
        accessible_routes = role_routes.get(role, [])
        editable_routes = role_editable_routes.get(role, [])
        explicit_entry_route = explicit_entry_routes.get(role, "")
        entry_route = explicit_entry_route or (editable_routes[0] if editable_routes else (accessible_routes[0] if accessible_routes else default_route))
        ordered_accessible_routes = accessible_routes[:]
        if entry_route and entry_route in ordered_accessible_routes:
            ordered_accessible_routes = [entry_route, *[route for route in ordered_accessible_routes if route != entry_route]]
        derived_entry_routes[role] = entry_route
        derived_workspaces.append(
            {
                "role": role,
                "entry_route": entry_route,
                "page_routes": ordered_accessible_routes,
                "page_ids": role_page_ids.get(role, []),
                "page_titles": role_page_titles.get(role, []),
                "default_access": "editable" if editable_routes else "read-only",
            }
        )

    raw_entry_routes = app_context.get("role_scoped_entry_routes", {}) if isinstance(app_context.get("role_scoped_entry_routes", {}), dict) else {}
    role_scoped_entry_routes = {
        role: str(raw_entry_routes.get(role) or derived_entry_routes.get(role) or default_route).strip() or default_route
        for role in ordered_roles
    }
    raw_current_role = _normalize_role_label(app_context.get("current_session_role") or "", locale=role_locale)
    login_session_roles = [role for role in session_role_candidates if role in ordered_roles]
    login_session_required = bool(login_session_roles)
    derived_session_role = login_session_roles[0] if login_session_roles else ""
    explicit_session_bootstrap_required = len(login_session_roles) > 1 and not raw_current_role
    current_session_role = (
        raw_current_role
        if raw_current_role in ordered_roles
        else ("" if login_session_required else (derived_session_role or (ordered_roles[0] if ordered_roles else "")))
    )
    raw_route_guard = app_context.get("route_guard_policy", {}) if isinstance(app_context.get("route_guard_policy", {}), dict) else {}
    auth_entry_route = _normalize_route_path(raw_route_guard.get("auth_entry_route") or derived_auth_entry_route)
    if login_session_required and not auth_entry_route:
        auth_entry_route = "/auth/login"
    default_auth_entry_label = "登录" if is_zh_locale(role_locale) else "Sign in"
    auth_entry_label = str(raw_route_guard.get("auth_entry_label") or derived_auth_entry_label or (default_auth_entry_label if auth_entry_route else "")).strip()
    default_route_guard_denied_behavior = "redirect-to-login" if auth_entry_route else "redirect-to-role-entry"
    effective_route_guard_denied_behavior = str(raw_route_guard.get("denied_behavior") or default_route_guard_denied_behavior).strip() or default_route_guard_denied_behavior
    raw_route_map = raw_route_guard.get("routes", {}) if isinstance(raw_route_guard.get("routes", {}), dict) else {}
    merged_route_policies: dict[str, dict[str, Any]] = {}
    for route, policy in route_policies.items():
        raw_policy = raw_route_map.get(route) if isinstance(raw_route_map.get(route), dict) else {}
        if isinstance(raw_policy, dict):
            merged_policy = {**policy, **raw_policy}
            for list_field in ("allowed_roles", "editable_roles", "read_only_roles", "workspace_entry_roles"):
                if isinstance(raw_policy.get(list_field), list):
                    merged_policy[list_field] = _ordered_role_union(raw_policy.get(list_field, []))
            merged_policy["navigation_scope"] = _page_navigation_scope(merged_policy)
            merged_policy["route_reachability_mode"] = _page_route_reachability_mode(merged_policy, locale=role_locale)
            merged_policy["denied_behavior"] = str(raw_policy.get("denied_behavior") or effective_route_guard_denied_behavior).strip() or effective_route_guard_denied_behavior
            merged_route_policies[route] = merged_policy
        else:
            merged_route_policies[route] = {**policy, "denied_behavior": effective_route_guard_denied_behavior}

    raw_workspaces = app_context.get("available_workspaces", []) if isinstance(app_context.get("available_workspaces", []), list) else []
    workspace_by_role = {
        _normalize_role_label(item.get("role") or "", locale=role_locale): item
        for item in raw_workspaces
        if isinstance(item, dict) and _normalize_role_label(item.get("role") or "", locale=role_locale)
    }
    available_workspaces: list[dict[str, Any]] = []
    for workspace in derived_workspaces:
        role = workspace["role"]
        raw_workspace = workspace_by_role.get(role, {})
        available_workspaces.append(
            {
                "role": role,
                "entry_route": str(raw_workspace.get("entry_route") or role_scoped_entry_routes.get(role) or workspace["entry_route"]).strip() or workspace["entry_route"],
                "page_routes": [str(item).strip() for item in raw_workspace.get("page_routes", workspace["page_routes"]) if str(item).strip()],
                "page_ids": [str(item).strip() for item in raw_workspace.get("page_ids", workspace["page_ids"]) if str(item).strip()],
                "page_titles": [str(item).strip() for item in raw_workspace.get("page_titles", workspace["page_titles"]) if str(item).strip()],
                "default_access": str(raw_workspace.get("default_access") or workspace["default_access"]).strip() or workspace["default_access"],
            }
        )

    return {
        "current_session_role": current_session_role,
        "available_workspaces": available_workspaces,
        "role_scoped_entry_routes": role_scoped_entry_routes,
        "route_guard_policy": {
            "mode": str(raw_route_guard.get("mode") or ("role-scoped-workspaces" if len(ordered_roles) > 1 else "single-role-workspace")).strip(),
            "workspace_switch_required": bool(raw_route_guard.get("workspace_switch_required")) if "workspace_switch_required" in raw_route_guard else explicit_session_bootstrap_required,
            "default_route": str(raw_route_guard.get("default_route") or role_scoped_entry_routes.get(current_session_role) or default_route).strip() or default_route,
            "denied_behavior": effective_route_guard_denied_behavior,
            "auth_entry_route": auth_entry_route,
            "auth_entry_label": auth_entry_label,
            "routes": merged_route_policies,
        },
        "read_only_vs_editable_by_role": {
            route: {
                "editable_roles": policy.get("editable_roles", []),
                "read_only_roles": policy.get("read_only_roles", []),
            }
            for route, policy in merged_route_policies.items()
        },
    }


def _normalize_route_path(value: Any) -> str:
    candidate = str(value or "").replace("`", "").strip()
    if not candidate or candidate.lower() in {"—", "-", "none", "n/a"}:
        return ""
    return candidate if candidate.startswith("/") else f"/{_business_slug(candidate)}"


def _ordered_route_values(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        route = _normalize_route_path(value)
        if not route:
            continue
        key = route.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(route)
    return ordered


def _page_navigation_routes(page: dict[str, Any]) -> list[str]:
    routes: list[Any] = []
    navigation = page.get("navigation") if isinstance(page.get("navigation"), dict) else {}
    next_route = _normalize_route_path(navigation.get("next_route") or "")
    if next_route:
        routes.append(next_route)
    routes.extend(page.get("next_route_candidates", []))
    return _ordered_route_values(routes)


def _page_workspace_entry_roles(page: dict[str, Any], *, locale: str) -> list[str]:
    return _ordered_role_union(
        [
            _normalize_role_label(item, locale=locale)
            for item in page.get("workspace_entry_roles", [])
            if _normalize_role_label(item, locale=locale)
        ]
    )


def _page_navigation_scope(page: dict[str, Any]) -> str:
    explicit_scope = str(page.get("navigation_scope") or "").strip().lower()
    if explicit_scope in {"workspace", "flow", "hidden"}:
        return explicit_scope
    audience_mode = str(page.get("audience_mode") or "app").strip().lower()
    page_blueprint_type = str(page.get("page_blueprint_type") or "").strip()
    if audience_mode != "app":
        return "hidden"
    if page.get("next_route_candidates") or _page_navigation_routes(page):
        return "flow"
    return _default_navigation_scope(page_blueprint_type)


def _page_route_reachability_mode(page: dict[str, Any], *, locale: str) -> str:
    explicit_mode = str(page.get("route_reachability_mode") or "").strip().lower()
    if explicit_mode in {"direct", "flow", "hidden"}:
        return explicit_mode
    audience_mode = str(page.get("audience_mode") or "app").strip().lower()
    navigation_scope = _page_navigation_scope(page)
    workspace_entry_roles = _page_workspace_entry_roles(page, locale=locale)
    return _default_route_reachability_mode(
        audience_mode=audience_mode,
        navigation_scope=navigation_scope,
        workspace_entry_roles=workspace_entry_roles,
    )


def _derive_workflow_navigation_contract(*, pages: list[dict[str, Any]], app_context: dict[str, Any]) -> dict[str, Any]:
    locale = str(app_context.get("locale") or "en")
    zh = is_zh_locale(locale)
    route_guard_policy = app_context.get("route_guard_policy", {}) if isinstance(app_context.get("route_guard_policy", {}), dict) else {}
    route_guard_routes = route_guard_policy.get("routes", {}) if isinstance(route_guard_policy.get("routes", {}), dict) else {}
    default_denied_behavior = str(route_guard_policy.get("denied_behavior") or "redirect-to-role-entry").strip() or "redirect-to-role-entry"
    page_by_route: dict[str, dict[str, Any]] = {}
    title_by_route: dict[str, str] = {}
    allowed_roles_by_route: dict[str, list[str]] = {}
    route_modes_by_route: dict[str, str] = {}
    ordered_routes: list[str] = []
    for page in pages:
        route = _normalize_route_path(page.get("route") or "")
        if not route:
            continue
        page_by_route[route] = page
        title_by_route[route] = str(page.get("page_title") or route).strip() or route
        ordered_routes.append(route)
        allowed_roles_by_route[route] = [str(item).strip() for item in page.get("allowed_roles", []) if str(item).strip()]
        route_modes_by_route[route] = _page_route_reachability_mode(page, locale=locale)
    global_previous: dict[str, str] = {}
    global_next: dict[str, str] = {}
    for index, route in enumerate(ordered_routes):
        global_previous[route] = ordered_routes[index - 1] if index > 0 else ""
        global_next[route] = ordered_routes[index + 1] if index + 1 < len(ordered_routes) else ""

    local_nav_items: dict[str, list[dict[str, Any]]] = {}
    contextual_nav_items: dict[str, dict[str, Any]] = {}
    next_step_cta: dict[str, dict[str, Any]] = {}
    placemaking_markers: dict[str, dict[str, Any]] = {}
    reachability_roles: dict[str, dict[str, Any]] = {}
    reachability_routes: dict[str, dict[str, Any]] = {}
    has_progression = False
    role_entry_routes = app_context.get("role_scoped_entry_routes", {}) if isinstance(app_context.get("role_scoped_entry_routes", {}), dict) else {}

    for workspace in app_context.get("available_workspaces", []):
        if not isinstance(workspace, dict):
            continue
        role = _normalize_role_label(workspace.get("role") or "", locale=locale)
        workspace_routes = [route for route in _ordered_route_values(workspace.get("page_routes", [])) if route in page_by_route]
        if not role or not workspace_routes:
            continue
        entry_route = _normalize_route_path(
            role_entry_routes.get(role)
            or workspace.get("entry_route")
            or workspace_routes[0]
        )
        if entry_route not in workspace_routes:
            entry_route = workspace_routes[0]
        direct_routes = _ordered_route_values(
            [entry_route, *[route for route in workspace_routes if route_modes_by_route.get(route, "direct") == "direct"]]
        )
        flow_routes = [route for route in workspace_routes if route_modes_by_route.get(route, "direct") == "flow" and route != entry_route]
        hidden_routes = [route for route in workspace_routes if route_modes_by_route.get(route, "direct") == "hidden" and route != entry_route]
        ordered_role_routes = _ordered_route_values([entry_route, *[route for route in direct_routes if route != entry_route], *flow_routes, *hidden_routes])
        progression_routes = _ordered_route_values([entry_route, *flow_routes])
        default_reachable_routes = direct_routes
        reachability_roles[role] = {
            "entry_route": entry_route,
            "ordered_routes": ordered_role_routes,
            "direct_routes": direct_routes,
            "flow_routes": flow_routes,
            "default_reachable_routes": default_reachable_routes,
            "unlock_rule": "flow-routes-require-unlock",
        }
        if flow_routes:
            has_progression = True
        local_nav_items[role] = []
        total_steps = len(progression_routes)
        for route in ordered_role_routes:
            page = page_by_route[route]
            title = title_by_route.get(route, route)
            reachability_mode = route_modes_by_route.get(route, "direct")
            progression_index = progression_routes.index(route) if route in progression_routes else -1
            local_previous_route = progression_routes[progression_index - 1] if progression_index > 0 else ""
            local_next_route = progression_routes[progression_index + 1] if progression_index >= 0 and progression_index + 1 < total_steps else ""
            explicit_previous_candidate = _normalize_route_path((page.get("navigation") or {}).get("previous_route") if isinstance(page.get("navigation"), dict) else "")
            next_candidates = _page_navigation_routes(page)
            explicit_previous = ""
            if explicit_previous_candidate and explicit_previous_candidate in ordered_role_routes:
                explicit_previous = explicit_previous_candidate
            elif progression_index >= 0 and local_previous_route:
                explicit_previous = local_previous_route
            elif explicit_previous_candidate and (
                not allowed_roles_by_route.get(explicit_previous_candidate)
                or role in allowed_roles_by_route.get(explicit_previous_candidate, [])
            ):
                explicit_previous = explicit_previous_candidate

            next_route = ""
            for candidate in next_candidates:
                if candidate and candidate in ordered_role_routes and candidate != route:
                    next_route = candidate
                    break
            if not next_route and progression_index >= 0 and local_next_route:
                next_route = local_next_route
            if not next_route:
                for candidate in next_candidates:
                    if candidate and (
                        not allowed_roles_by_route.get(candidate)
                        or role in allowed_roles_by_route.get(candidate, [])
                    ):
                        next_route = candidate
                        break

            handoff_route = ""
            if not next_route:
                for candidate in next_candidates:
                    if candidate and candidate != route:
                        handoff_route = candidate
                        break
            fallback_cross_role_next = global_next.get(route, "")
            if not handoff_route and fallback_cross_role_next and fallback_cross_role_next != route:
                handoff_route = fallback_cross_role_next
            step_text = ""
            step_index = None
            if progression_index >= 0 and total_steps > 1:
                step_text = str((page.get("workflow_step", {}) or {}).get("step") or "").strip() or (
                    f"第 {progression_index + 1}/{total_steps} 步" if zh else f"Step {progression_index + 1} of {total_steps}"
                )
                step_index = progression_index + 1
            locked_reason = ""
            if reachability_mode == "flow" and local_previous_route:
                locked_reason = (
                    "请先完成上一步，当前步骤才会解锁。" if zh else "Complete the previous step before this step unlocks."
                )
            if reachability_mode != "hidden":
                nav_item = {
                    "route": route,
                    "label": title,
                    "step_label": step_text,
                    "unlocked_by_default": route in default_reachable_routes,
                    "locked_reason": locked_reason,
                }
                if step_index:
                    nav_item["step_index"] = step_index
                    nav_item["total_steps"] = total_steps
                local_nav_items[role].append(nav_item)
            contextual_nav_items.setdefault(route, {"by_role": {}})
            contextual_nav_items[route]["by_role"][role] = {
                "previous_route": explicit_previous,
                "next_route": next_route,
                "previous_label": title_by_route.get(explicit_previous, ""),
                "next_label": title_by_route.get(next_route, ""),
                "current_label": title,
            }
            next_roles = allowed_roles_by_route.get(next_route, [])
            target_role = role if not next_roles or role in next_roles else next_roles[0]
            next_kind = "terminal"
            if next_route:
                next_kind = "same-role" if not next_roles or role in next_roles else "handoff"
            if next_kind == "handoff":
                label = f"切换到 {target_role} 继续" if zh else f"Continue in {target_role}"
            elif next_route:
                label = f"继续到 {title_by_route.get(next_route, next_route)}" if zh else f"Continue to {title_by_route.get(next_route, next_route)}"
            elif handoff_route:
                handoff_roles = allowed_roles_by_route.get(handoff_route, [])
                target_role = role if not handoff_roles or role in handoff_roles else handoff_roles[0]
                next_kind = "handoff"
                label = f"切换到 {target_role} 继续" if zh else f"Continue in {target_role}"
            else:
                label = ""
            next_step_cta.setdefault(route, {"by_role": {}})
            next_step_cta[route]["by_role"][role] = {
                "kind": next_kind,
                "target_route": next_route,
                "target_role": target_role,
                "target_label": title_by_route.get(next_route, ""),
                "label": label,
            }
            placemaking_markers.setdefault(route, {"by_role": {}})
            placemaking_marker = {
                "step_label": step_text,
                "current_label": title,
                "previous_label": title_by_route.get(explicit_previous, ""),
                "next_label": title_by_route.get(next_route, ""),
            }
            if step_index:
                placemaking_marker["step_index"] = step_index
                placemaking_marker["total_steps"] = total_steps
            placemaking_markers[route]["by_role"][role] = placemaking_marker
            reachability_routes.setdefault(
                route,
                {
                    "allowed_roles": allowed_roles_by_route.get(route, []),
                    "by_role": {},
                    "denied_behavior": str(
                        ((route_guard_routes.get(route) if isinstance(route_guard_routes.get(route), dict) else {}) or {}).get("denied_behavior")
                        or default_denied_behavior
                    ).strip() or default_denied_behavior,
                },
            )
            role_reachability = {
                "entry_route": entry_route,
                "reachability_mode": reachability_mode,
                "reachable_by_default": route in default_reachable_routes,
                "reachable_after_route": local_previous_route if reachability_mode == "flow" else "",
                "next_route": next_route,
                "locked_reason": locked_reason,
            }
            if step_index:
                role_reachability["step_index"] = step_index
                role_reachability["total_steps"] = total_steps
            reachability_routes[route]["by_role"][role] = role_reachability

    return {
        "primary_navigation_mode": "workflow-progression" if has_progression else "workspace-entry-only",
        "global_nav_items": [{"route": "/", "label": ui_text(locale, "dashboard"), "kind": "workspace-home"}],
        "local_nav_items": local_nav_items,
        "contextual_nav_items": contextual_nav_items,
        "next_step_cta": next_step_cta,
        "route_reachability_policy": {
            "mode": "entry-direct-flow",
            "denied_behavior": default_denied_behavior,
            "roles": reachability_roles,
            "routes": reachability_routes,
        },
        "placemaking_markers": placemaking_markers,
    }


FRONTEND_EXPERIENCE_SOURCE_CARDS = {
    "app-posture-follows-usage-context": "sources/books/extracted/about-face-4/cards-draft/platform-and-posture-should-follow-usage-context.md",
    "reduce-navigation-burden": "sources/books/extracted/about-face-4/cards-draft/interaction-burden-is-tax-on-users-reduce-navigation.md",
    "offer-choices-not-questions": "sources/books/extracted/about-face-4/cards-draft/controls-should-offer-choices-not-questions.md",
    "navigation-taxonomy": "sources/books/extracted/information-architecture-for-the-web/cards-draft/navigation-global-local-contextual-and-supplemental.md",
    "placemaking": "sources/books/extracted/information-architecture-for-the-web/cards-draft/placemaking-users-need-you-are-here.md",
    "metadata-controlled-vocabulary": "sources/books/extracted/information-architecture-for-the-web/cards-draft/metadata-and-controlled-vocab-are-system-glue.md",
}


def _dedupe_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def _derive_frontend_experience_contract(*, pages: list[dict[str, Any]], app_context: dict[str, Any], locale: str) -> dict[str, Any]:
    zh = is_zh_locale(locale)
    workspace_roles = [
        str(workspace.get("role") or "").strip()
        for workspace in app_context.get("available_workspaces", [])
        if isinstance(workspace, dict) and str(workspace.get("role") or "").strip()
    ]
    navigation_mode = str(app_context.get("primary_navigation_mode") or "").strip() or "workspace-entry-only"
    workflow_roles = (app_context.get("route_reachability_policy") or {}).get("roles", {}) if isinstance(app_context.get("route_reachability_policy"), dict) else {}
    has_workflow_progression = navigation_mode == "workflow-progression" or any(
        len([str(route).strip() for route in (row.get("ordered_routes") or []) if str(route).strip()]) > 1
        for row in workflow_roles.values()
        if isinstance(row, dict)
    )
    if len(pages) > 1 or len(workspace_roles) > 1 or has_workflow_progression:
        posture_id = "sovereign-workflow-application"
        posture_label = "独占式工作流应用" if zh else "Sovereign workflow application"
        posture_reason = (
            "该案例由多页面工作流与角色工作区组成，壳层必须以工作台和流程推进为主，而不是平铺成工具目录。"
            if zh
            else "This case behaves like a multi-step workbench, so the shell should privilege workspace and workflow progression instead of a flat utility menu."
        )
    else:
        posture_id = "transient-task-surface"
        posture_label = "暂时性任务界面" if zh else "Transient task surface"
        posture_reason = (
            "该案例主要承载单步任务，壳层应保持轻量，不必伪装成大型工作台。"
            if zh
            else "This case is closer to a single-step task surface, so the shell should stay lightweight rather than pretending to be a large workbench."
        )

    typed_control_fields: list[str] = []
    controlled_vocabulary_fields: list[str] = []
    generated_or_context_fields: list[str] = []
    for page in pages:
        for item in page.get("user_inputs", []):
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            control = str(item.get("control") or "").strip()
            value_source = str(item.get("value_source") or "").strip()
            if control and control != "text":
                typed_control_fields.append(field)
            if item.get("options") or str(item.get("options_source") or "").strip() or str(item.get("lookup_entity") or "").strip():
                controlled_vocabulary_fields.append(field)
            if value_source in {"workflow-context", "response-binding", "system-generated"} or item.get("system_generated") or item.get("server_assigned"):
                generated_or_context_fields.append(field)

    typed_control_fields = _dedupe_strings(typed_control_fields)
    controlled_vocabulary_fields = _dedupe_strings(controlled_vocabulary_fields)
    generated_or_context_fields = _dedupe_strings(generated_or_context_fields)

    rule_coverage = [
        {
            "rule_id": "app-posture-follows-usage-context",
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["app-posture-follows-usage-context"],
            "status": "active",
            "contract_hooks": ["app_context.available_workspaces", "app_context.primary_navigation_mode", "app_context.route_guard_policy"],
            "gate_hooks": ["experience-rule-contract", "audience-boundary", "nav-posture"],
            "web_app_dimensions": ["audience-boundary", "nav-posture"],
            "browser_audit_focus": ["session bootstrap", "role workspace shell", "flat menu avoidance"],
        },
        {
            "rule_id": "reduce-navigation-burden",
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["reduce-navigation-burden"],
            "status": "active",
            "contract_hooks": ["app_context.local_nav_items", "app_context.route_reachability_policy", "app_context.next_step_cta"],
            "gate_hooks": ["experience-rule-contract", "handoff-exposure", "nav-posture"],
            "web_app_dimensions": ["handoff-exposure", "nav-posture"],
            "browser_audit_focus": ["reachable next step", "no unnecessary page-hopping"],
        },
        {
            "rule_id": "offer-choices-not-questions",
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["offer-choices-not-questions"],
            "status": "active",
            "contract_hooks": ["pages[].user_inputs[].control", "pages[].user_inputs[].options", "pages[].user_inputs[].value_source"],
            "gate_hooks": ["experience-rule-contract", "field-semantics"],
            "web_app_dimensions": ["field-semantics"],
            "browser_audit_focus": ["typed controls", "readonly generated ids", "visible choices"],
            "evidence_fields": typed_control_fields[:12],
        },
        {
            "rule_id": "navigation-taxonomy",
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["navigation-taxonomy"],
            "status": "active",
            "contract_hooks": ["app_context.global_nav_items", "app_context.local_nav_items", "app_context.contextual_nav_items", "app_context.next_step_cta"],
            "gate_hooks": ["experience-rule-contract", "nav-posture"],
            "web_app_dimensions": ["nav-posture"],
            "browser_audit_focus": ["global/local/contextual nav", "supplemental next-step guidance"],
        },
        {
            "rule_id": "placemaking",
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["placemaking"],
            "status": "active",
            "contract_hooks": ["app_context.placemaking_markers", "app_context.current_session_role"],
            "gate_hooks": ["experience-rule-contract", "nav-posture"],
            "web_app_dimensions": ["nav-posture"],
            "browser_audit_focus": ["you are here", "previous/current/next markers"],
        },
        {
            "rule_id": "metadata-controlled-vocabulary",
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["metadata-controlled-vocabulary"],
            "status": "active",
            "contract_hooks": ["pages[].field_labels", "pages[].user_inputs[].options_source", "pages[].user_inputs[].lookup_entity", "pages[].user_inputs[].display_format"],
            "gate_hooks": ["experience-rule-contract", "audience-boundary", "field-semantics"],
            "web_app_dimensions": ["audience-boundary", "field-semantics"],
            "browser_audit_focus": ["consistent labels", "consistent status vocabulary", "controlled selection vocabulary"],
            "evidence_fields": controlled_vocabulary_fields[:12],
        },
    ]

    browser_audit_checklist = [
        {
            "check_id": "FE-WEBAPP-01",
            "dimension": "audience-boundary",
            "rule_ids": ["app-posture-follows-usage-context", "metadata-controlled-vocabulary"],
            "prompt": (
                "确认当前页面服务于当前角色工作；若会话缺失则进入真实登录入口，而不是 chooser/demo fallback；同时不出现 role switcher、评审/教程文案或合同元信息泄漏。"
                if zh
                else "Confirm the current surface serves the active role; missing-session access must go to the real auth entry instead of a chooser/demo fallback; and the page must not expose a role switcher, review/tutorial copy, or contract metadata."
            ),
            "evidence_fields": ["pages[].audience_mode", "pages[].forbidden_exposure", "app_context.available_workspaces", "app_context.route_guard_policy", "app_context.route_guard_policy.auth_entry_route"],
            "bad_patterns": ["role switcher", "review/tutorial copy", "contract metadata leak", "chooser/demo fallback for missing session"],
        },
        {
            "check_id": "FE-WEBAPP-02",
            "dimension": "handoff-exposure",
            "rule_ids": ["reduce-navigation-burden"],
            "prompt": (
                "确认跨角色交接保持隐式上下文或受控摘要，不出现 switch-role-to-continue 之类的显式 CTA。"
                if zh
                else "Confirm cross-role handoff stays implicit or audience-safe and does not show switch-role-to-continue style CTA copy."
            ),
            "evidence_fields": ["pages[].handoff_visibility", "pages[].forbidden_exposure", "pages[].compiled_interactions[].next_page_id", "app_context.next_step_cta"],
            "bad_patterns": ["cross-role CTA", "switch-role-to-continue", "explicit handoff tutorial copy"],
        },
        {
            "check_id": "FE-WEBAPP-03",
            "dimension": "field-semantics",
            "rule_ids": ["offer-choices-not-questions", "metadata-controlled-vocabulary"],
            "prompt": (
                "确认选择类字段使用 typed controls，且 system-generated ID 不要求人工文本输入。"
                if zh
                else "Confirm choice-like fields use typed controls and system-generated identifiers are not manual text inputs."
            ),
            "evidence_fields": ["pages[].user_inputs[].control", "pages[].user_inputs[].options", "pages[].user_inputs[].value_source"],
            "focused_fields": _dedupe_strings([*typed_control_fields[:12], *generated_or_context_fields[:12], *controlled_vocabulary_fields[:12]]),
            "bad_patterns": ["system-generated id as text input", "choice field collapsed to text input", "missing options semantics"],
        },
        {
            "check_id": "FE-WEBAPP-04",
            "dimension": "nav-posture",
            "rule_ids": ["app-posture-follows-usage-context", "reduce-navigation-burden", "navigation-taxonomy", "placemaking"],
            "prompt": (
                "确认导航表现为当前角色工作区：只暴露可达路径，请求进入声明可达的 route 时要么停留在目标 route、要么按 contract 重定向到 auth 入口，并且能看出当前位置/下一步，而不是站点总览。"
                if zh
                else "Confirm navigation behaves like the current role workspace: only reachable routes are exposed, declared direct routes either land on the target route or redirect to the contract-declared auth entry, and current/next markers remain visible instead of a flat site map shell."
            ),
            "evidence_fields": ["pages[].route", "pages[].route_reachability_mode", "app_context.primary_navigation_mode", "app_context.local_nav_items", "app_context.contextual_nav_items", "app_context.route_reachability_policy", "app_context.route_guard_policy.auth_entry_route", "app_context.next_step_cta", "app_context.placemaking_markers"],
            "bad_patterns": ["flat site menu", "unreachable route exposed", "requested route lands elsewhere", "missing-session route falls back to chooser/demo", "missing current-next placemaking"],
        },
    ]

    return {
        "rule_bundle_id": "wo15-frontend-webapp-rules-v1",
        "source_cards": [FRONTEND_EXPERIENCE_SOURCE_CARDS[key] for key in FRONTEND_EXPERIENCE_SOURCE_CARDS],
        "app_posture": {
            "posture_id": posture_id,
            "label": posture_label,
            "reason": posture_reason,
            "derived_from": {
                "workspace_count": len(workspace_roles),
                "page_count": len(pages),
                "primary_navigation_mode": navigation_mode,
            },
            "source_card": FRONTEND_EXPERIENCE_SOURCE_CARDS["app-posture-follows-usage-context"],
        },
        "navigation_profile": {
            "model": "global-local-contextual-next-step",
            "global_nav_present": bool(app_context.get("global_nav_items")),
            "local_nav_present": any(bool(items) for items in (app_context.get("local_nav_items") or {}).values()) if isinstance(app_context.get("local_nav_items"), dict) else False,
            "contextual_nav_present": bool(app_context.get("contextual_nav_items")),
            "next_step_present": bool(app_context.get("next_step_cta")),
            "placemaking_present": bool(app_context.get("placemaking_markers")),
        },
        "control_semantics_summary": {
            "typed_control_fields": typed_control_fields[:20],
            "controlled_vocabulary_fields": controlled_vocabulary_fields[:20],
            "generated_or_context_fields": generated_or_context_fields[:20],
        },
        "rule_coverage": rule_coverage,
        "browser_audit_dimensions": [row["dimension"] for row in browser_audit_checklist],
        "prototype_review_checklist": browser_audit_checklist,
        "prototype_review_dimensions": [row["dimension"] for row in browser_audit_checklist],
        "browser_audit_checklist": browser_audit_checklist,
    }


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "surface"


def _business_slug(page_name: str) -> str:
    candidate = str(page_name).strip()
    if "/" in candidate:
        english_part = candidate.split("/")[-1].strip()
        if english_part and english_part.isascii() and " " not in english_part:
            return _slugify(english_part)
    return _slugify(candidate)


def _display_surface_title(surface: str, locale: str) -> str:
    candidate = str(surface).strip()
    mapped = localize_surface_title(candidate, locale)
    if mapped != candidate:
        return mapped
    if "/" in candidate:
        business_name, route_slug = [part.strip() for part in candidate.split("/", 1)]
        if business_name:
            return business_name
        if route_slug and route_slug.isascii() and " " not in route_slug:
            return _humanize_identifier(route_slug)
    return candidate


def _text_with_visibility(text: str, visibility: str, usage: str) -> dict[str, str]:
    return {
        "text": str(text).strip(),
        "visibility": visibility,
        "usage": usage,
    }


def _items_with_visibility(items: list[str], visibility: str, usage: str) -> dict[str, Any]:
    return {
        "items": [str(item).strip() for item in items if str(item).strip()],
        "visibility": visibility,
        "usage": usage,
    }


def _visibility_text(value: Any) -> str:
    if isinstance(value, dict):
        text = str(value.get("text") or "").strip()
        if text:
            return text
    return str(value or "").strip()


def _humanize_identifier(value: str) -> str:
    candidate = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value)).replace("_", " ").replace("-", " ")
    tokens = [token for token in candidate.split() if token]
    normalized: list[str] = []
    for token in tokens:
        lowered = token.lower()
        if lowered in {"id", "api", "cta", "roi"}:
            normalized.append(lowered.upper())
        else:
            normalized.append(lowered.capitalize())
    return " ".join(normalized) or "Field"


FIELD_SPEC_DEFAULTS: dict[str, dict[str, str]] = {
    "tenantId": {"validation": "identifier"},
    "scopeId": {"validation": "identifier"},
    "scopeKey": {"validation": "text"},
    "scopeVersion": {"validation": "integer"},
    "brandName": {"validation": "text"},
    "competitors": {"validation": "list"},
    "questions": {"validation": "list"},
    "pages": {"validation": "list"},
    "idempotencyKey": {"validation": "text"},
    "observationRunId": {"validation": "identifier"},
    "priorityBands": {"validation": "list"},
    "includeCompetitorWindow": {"validation": "boolean"},
    "cursor": {"validation": "text"},
    "pageSize": {"validation": "integer"},
    "statuses": {"validation": "list"},
    "ownerSubjectId": {"validation": "identifier"},
    "includeRecommendationSummary": {"validation": "boolean"},
    "includeBlockedOnly": {"validation": "boolean"},
    "sortBy": {"validation": "text"},
    "findingId": {"validation": "identifier"},
    "expectedFindingVersion": {"validation": "integer"},
    "includeCompetitorContext": {"validation": "boolean"},
    "includeRecommendationContext": {"validation": "boolean"},
    "includeAttributionSeam": {"validation": "boolean"},
    "assetId": {"validation": "identifier"},
    "decision": {"validation": "enum"},
    "decisionRationale": {"validation": "text"},
    "priorityOverride": {"validation": "enum"},
    "attributionContextRef": {"validation": "text"},
    "recommendationId": {"validation": "identifier"},
    "taskId": {"validation": "identifier"},
    "status": {"validation": "enum"},
    "expectedVersion": {"validation": "integer"},
    "executionEvidenceRef": {"validation": "text"},
    "blockedReason": {"validation": "text"},
    "cycleKey": {"validation": "text"},
    "freezeTaskStatusesBefore": {"validation": "text"},
    "includeUncertaintyBreakdown": {"validation": "boolean"},
}


def _field_default_validation(field: str) -> str:
    return FIELD_SPEC_DEFAULTS.get(field, {}).get("validation", "text")


FIELD_ENUM_OPTIONS: dict[str, list[str]] = {
    "status": ["draft", "scheduled", "active", "in_progress", "blocked", "completed", "cancelled"],
    "state": ["draft", "active", "blocked", "completed", "cancelled"],
    "decision": ["accept", "defer", "reject"],
    "priority_override": ["low", "medium", "high", "critical"],
    "priority_band": ["low", "medium", "high", "critical"],
    "priority": ["low", "medium", "high", "critical"],
}


def _humanize_option_label(value: str) -> str:
    normalized = str(value).strip().replace("_", " ").replace("-", " ")
    if not normalized:
        return ""
    return normalized[:1].upper() + normalized[1:]


def _localized_option_label(value: str, *, locale: str) -> str:
    normalized = str(value).strip().lower()
    if not is_zh_locale(locale):
        return _humanize_option_label(normalized)
    translations = {
        "draft": "草稿",
        "scheduled": "已安排",
        "active": "进行中",
        "in_progress": "处理中",
        "blocked": "已阻塞",
        "completed": "已完成",
        "cancelled": "已取消",
        "accept": "接受",
        "defer": "暂缓",
        "reject": "驳回",
        "low": "低",
        "medium": "中",
        "high": "高",
        "critical": "关键",
    }
    return translations.get(normalized, _humanize_option_label(normalized))


def _singularize_token(token: str) -> str:
    normalized = str(token).strip().lower()
    if normalized.endswith("ies") and len(normalized) > 4:
        return normalized[:-3] + "y"
    if normalized.endswith("ses") and len(normalized) > 4:
        return normalized[:-2]
    if normalized.endswith("s") and len(normalized) > 3 and not normalized.endswith(("ss", "us", "is")):
        return normalized[:-1]
    return normalized


def _camel_case_token(token: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", str(token).strip()) if part]
    if not parts:
        return ""
    head = parts[0].lower()
    tail = "".join(part[:1].upper() + part[1:] for part in parts[1:])
    return head + tail


def _identifier_stem(field: str) -> str:
    normalized = str(field).strip()
    snake = _snake_case_field(normalized)
    if snake.endswith("_id"):
        return snake[:-3]
    if normalized.endswith("Id") and len(normalized) > 2:
        return _snake_case_field(normalized[:-2])
    return snake


def _lookup_entity_for_field(field: str) -> str:
    stem = _identifier_stem(field)
    if not stem or stem in {"tenant", "user", "account"}:
        return ""
    return stem


def _resource_id_candidates(api_path: str) -> set[str]:
    segments = [
        segment
        for segment in str(api_path).split("/")
        if segment
        and segment not in {"api"}
        and not re.fullmatch(r"v\d+", segment)
        and not segment.startswith("{")
    ]
    if not segments:
        return set()
    resource_token = _singularize_token(segments[-1])
    camel = _camel_case_token(resource_token)
    candidates = {
        f"{camel}Id" if camel else "",
        f"{resource_token}_id" if resource_token else "",
    }
    return {candidate for candidate in candidates if candidate}


def _infer_field_datatype(field: str, validation: str | None = None) -> str:
    normalized = str(field).strip()
    snake = _snake_case_field(normalized)
    lowered_validation = str(validation or "").strip().lower()
    if "boolean" in lowered_validation:
        return "boolean"
    if "json" in lowered_validation:
        return "json"
    if "list" in lowered_validation:
        return "list"
    if "enum" in lowered_validation:
        return "enum"
    if "date" in lowered_validation and "time" in lowered_validation:
        return "datetime"
    if lowered_validation in {"date", "datetime", "integer", "number", "identifier"}:
        return lowered_validation
    if normalized.endswith("Id") or snake.endswith("_id"):
        return "identifier"
    if any(token in snake for token in ("datetime", "timestamp")) or snake.endswith("_at") or (("date" in snake or "time" in snake) and "update" not in snake):
        return "datetime" if "time" in snake or "datetime" in snake or snake.endswith("_at") else "date"
    if any(token in snake for token in ("age", "count", "total", "quantity", "size", "index", "page_size", "version")):
        return "integer"
    if any(token in snake for token in ("amount", "price", "fee", "cost", "rate", "score", "percent")):
        return "number"
    return "text"


def _field_options(field: str, *, datatype: str, locale: str) -> tuple[list[dict[str, str]], str]:
    if datatype != "enum":
        return [], ""
    snake = _snake_case_field(field)
    values = FIELD_ENUM_OPTIONS.get(snake, FIELD_ENUM_OPTIONS.get(_identifier_stem(field), []))
    options = [
        {"value": value, "label": _localized_option_label(value, locale=locale)}
        for value in values
        if str(value).strip()
    ]
    return options, f"field-vocabulary:{snake}"


def _field_display_format(*, datatype: str, control: str, value_source: str) -> str:
    if control == "hidden":
        return "hidden"
    if control == "lookup":
        return "lookup"
    if value_source in {"workflow-context", "response-binding"}:
        return "reference"
    if datatype == "enum":
        return "badge"
    if datatype in {"integer", "number"}:
        return "numeric"
    if datatype in {"date", "datetime"}:
        return datatype
    if datatype in {"json", "list"}:
        return "multiline"
    if datatype == "boolean":
        return "boolean"
    if datatype == "identifier":
        return "identifier"
    return "text"


def _field_control(
    field: str,
    *,
    datatype: str,
    value_source: str,
    editability: str,
    options: list[dict[str, str]],
    selector: bool = False,
) -> str:
    if editability == "hidden" or value_source == "auth-session":
        return "hidden"
    if editability == "readonly":
        return "readonly"
    if selector and datatype == "identifier":
        return "lookup"
    if datatype == "boolean":
        return "checkbox"
    if datatype in {"json", "list"}:
        return "textarea"
    if datatype == "enum" or options:
        return "select"
    if datatype in {"integer", "number"}:
        return "number"
    if datatype == "date":
        return "date"
    if datatype == "datetime":
        return "datetime"
    if datatype == "identifier" and _lookup_entity_for_field(field):
        return "lookup"
    return "text"


def _field_semantics(
    field: str,
    *,
    locale: str,
    validation: str | None,
    source: str = "user-input",
    bind_to: str = "",
    selector: bool = False,
) -> dict[str, Any]:
    datatype = _infer_field_datatype(field, validation)
    system_generated = False
    server_assigned = False
    value_source = source or "user-input"
    if value_source == "user-input":
        bind_method, _, bind_path = bind_to.partition(" ")
        if bind_method.upper() == "POST" and field in _resource_id_candidates(bind_path):
            value_source = "system-generated"
            system_generated = True
            server_assigned = True
    editability = "editable"
    if value_source in {"auth-session", "system-generated", "server-default"}:
        editability = "hidden"
    elif value_source == "response-binding":
        editability = "readonly"
    elif value_source == "workflow-context" and not selector:
        editability = "readonly"
    options, options_source = _field_options(field, datatype=datatype, locale=locale)
    lookup_entity = _lookup_entity_for_field(field)
    control = _field_control(
        field,
        datatype=datatype,
        value_source=value_source,
        editability=editability,
        options=options,
        selector=selector,
    )
    if control != "lookup":
        lookup_entity = ""
    return {
        "value_source": value_source,
        "editability": editability,
        "datatype": datatype,
        "control": control,
        "options": options,
        "options_source": options_source or (f"entity:{lookup_entity}" if lookup_entity else ""),
        "system_generated": system_generated,
        "server_assigned": server_assigned,
        "lookup_entity": lookup_entity,
        "display_format": _field_display_format(
            datatype=datatype,
            control=control,
            value_source=value_source,
        ),
    }


def _make_input_spec(
    field: str,
    *,
    locale: str,
    required: bool,
    validation: str | None = None,
    group: str | None = None,
    surface: str = "",
    value_source: str = "user-input",
    editability: str | None = None,
    datatype: str | None = None,
    control: str | None = None,
    options: list[dict[str, str]] | None = None,
    options_source: str | None = None,
    system_generated: bool | None = None,
    server_assigned: bool | None = None,
    lookup_entity: str | None = None,
    display_format: str | None = None,
) -> dict[str, Any]:
    label = ui_field_label(field, locale)
    effective_validation = validation or _field_default_validation(field)
    semantics = _field_semantics(field, locale=locale, validation=effective_validation, source=value_source)
    effective_datatype = datatype or str(semantics.get("datatype") or "").strip() or "text"
    effective_options = options if isinstance(options, list) else list(semantics.get("options") or [])
    effective_value_source = str(value_source or semantics.get("value_source") or "user-input").strip() or "user-input"
    effective_editability = str(editability or semantics.get("editability") or "editable").strip() or "editable"
    effective_lookup_entity = str(lookup_entity or semantics.get("lookup_entity") or "").strip()
    effective_options_source = str(options_source or semantics.get("options_source") or "").strip()
    effective_system_generated = bool(system_generated if system_generated is not None else semantics.get("system_generated"))
    effective_server_assigned = bool(server_assigned if server_assigned is not None else semantics.get("server_assigned"))
    effective_control = str(
        control
        or _field_control(
            field,
            datatype=effective_datatype,
            value_source=effective_value_source,
            editability=effective_editability,
            options=effective_options,
        )
    ).strip() or "text"
    default_group = group or _surface_input_group(surface, field, required=required, locale=locale)
    placeholder = _surface_input_placeholder(field, label, locale=locale)
    if effective_control in {"select", "lookup"}:
        placeholder = f"请选择{label}" if is_zh_locale(locale) else f"Select {label.lower()}"
    elif effective_control == "hidden":
        placeholder = "由系统生成并自动携带" if is_zh_locale(locale) else "Generated by the system"
    helper = _surface_input_helper(field, label, validation=effective_validation, locale=locale)
    if effective_control == "hidden":
        helper = "这个值由系统自动生成或从当前会话继承，不需要人工填写。" if is_zh_locale(locale) else "This value is generated by the system or carried from the current session."
    elif effective_editability == "readonly":
        helper = "这个值来自当前流程上下文，会在本步骤中继续沿用。" if is_zh_locale(locale) else "This value comes from the current workflow context and is carried into this step."
    elif effective_control == "lookup" and effective_lookup_entity:
        helper = f"请选择当前步骤要关联的{ui_field_label(effective_lookup_entity, locale)}。" if is_zh_locale(locale) else f"Choose the {effective_lookup_entity.replace('_', ' ')} record to link in this step."
    if not helper:
        helper = ""
    return {
        "field": field,
        "label": label,
        "required": required,
        "validation": effective_validation,
        "value_source": effective_value_source,
        "editability": effective_editability,
        "datatype": effective_datatype,
        "control": effective_control,
        "options": effective_options,
        "options_source": effective_options_source,
        "system_generated": effective_system_generated,
        "server_assigned": effective_server_assigned,
        "lookup_entity": effective_lookup_entity,
        "display_format": str(
            display_format
            or semantics.get("display_format")
            or _field_display_format(
                datatype=effective_datatype,
                control=effective_control,
                value_source=effective_value_source,
            )
        ).strip(),
        "placeholder": placeholder,
        "helper": helper,
        "group": default_group,
    }


def _build_action_spec(
    endpoint: dict[str, Any] | None,
    *,
    locale: str,
    summary_en: str,
    summary_zh: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
    result_fields: list[str] | None = None,
    response_bindings: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    if not endpoint:
        return None
    return {
        "action": _action_label_for_endpoint(endpoint, locale=locale),
        "summary": summary_zh if is_zh_locale(locale) else summary_en,
        "required_fields": required_fields,
        "optional_fields": optional_fields or [],
        "result_fields": result_fields or [],
        "response_bindings": response_bindings or [],
        "api_binding": {
            "method": endpoint["method"],
            "path": endpoint["path"],
        },
    }


def _surface_input_group(surface: str, field: str, *, required: bool, locale: str) -> str:
    lowered_surface = str(surface).lower()
    if is_zh_locale(locale):
        if any(token in lowered_surface for token in ("onboarding", "setup")) or any(token in surface for token in ("接入", "配置", "范围")):
            if field in {"tenantId"}:
                return "租户与权限"
            if field in {"scopeKey", "brandName", "competitors", "questions", "pages"}:
                return "范围定义"
            if field in {"scopeId", "scopeVersion", "idempotencyKey"}:
                return "观测启动"
        if any(token in lowered_surface for token in ("overview", "findings")) or any(token in surface for token in ("总览", "发现")):
            if field in {"tenantId", "scopeId", "observationRunId"}:
                return "工作上下文"
            return "筛选条件"
        if "recommendation" in lowered_surface or any(token in surface for token in ("建议", "导出")):
            if field in {"tenantId", "findingId", "expectedFindingVersion", "includeCompetitorContext", "includeRecommendationContext", "includeAttributionSeam"}:
                return "发现上下文"
            if field in {"assetId", "decision", "decisionRationale", "priorityOverride", "attributionContextRef"}:
                return "建议决策"
            return "任务导出"
        if "task" in lowered_surface or "任务" in surface:
            if field in {"tenantId", "scopeId", "statuses", "ownerSubjectId", "includeRecommendationSummary", "includeBlockedOnly", "sortBy", "cursor", "pageSize"}:
                return "任务筛选"
            return "状态更新"
        if "review" in lowered_surface or any(token in surface for token in ("审核", "复盘", "修订")):
            if field in {"tenantId", "scopeId", "cycleKey", "freezeTaskStatusesBefore", "includeUncertaintyBreakdown"}:
                return "周期上下文"
            return "审核决策"
        return "主要输入" if required else "可选输入"
    return "Primary input" if required else "Optional input"


def _surface_input_placeholder(field: str, label: str, *, locale: str) -> str:
    if not is_zh_locale(locale):
        return f"Enter {label.lower()}"
    examples = {
        "tenantId": "例如：tenant-001",
        "scopeKey": "例如：brand-core",
        "brandName": "例如：Acme Cloud",
        "competitors": "每行一个竞品名称或域名",
        "questions": "每行一个需要持续跟踪的问题",
        "pages": "每行一个需要跟踪的页面 URL",
        "idempotencyKey": "例如：launch-20260408-01",
        "scopeId": "例如：scp_001",
        "observationRunId": "例如：run_20260407_01",
        "findingId": "例如：finding_001",
        "assetId": "例如：asset_pricing_page",
        "recommendationId": "例如：rec_001",
        "taskId": "例如：task_001",
        "decisionRationale": "说明为什么接受、推迟或驳回该建议",
        "executionEvidenceRef": "填写执行记录、提交链接或工单引用",
        "blockedReason": "说明当前任务为什么被阻塞",
        "cycleKey": "例如：2026-W14",
    }
    return examples.get(field, f"请输入{label}")


def _surface_input_helper(field: str, label: str, *, validation: str, locale: str) -> str:
    if not is_zh_locale(locale):
        return ""
    help_map = {
        "tenantId": "选择或输入当前工作的租户边界，后续所有动作都会在这个边界内执行。",
        "scopeKey": "这是范围草稿的稳定标识，后续观测与复盘都会沿用它。",
        "brandName": "填写本轮 GEO 关注的品牌或产品名称。",
        "competitors": "录入当前最需要对比的竞品，系统会据此组织对比视角。",
        "questions": "填写本轮想回答的核心问题，例如品牌提及、对比缺口或内容盲区。",
        "pages": "填写需要纳入首轮观测的页面、资产或 URL 列表。",
        "scopeId": "用于绑定已创建的跟踪范围，并把上下文带入后续步骤。",
        "observationRunId": "用于定位当前观测周期，确保看到的是同一轮结果。",
        "findingId": "选择要进入详情诊断的具体发现。",
        "decision": "填写当前建议的处理结论，例如接受、暂缓或驳回。",
        "decisionRationale": "说明为什么做出这个建议决策，供后续任务与复盘追溯。",
        "assetId": "选择要落地建议的具体内容资产或页面。",
        "recommendationId": "使用已经冻结的建议 ID，把它导出到任务链路。",
        "taskId": "指定要更新状态的任务。",
        "status": "填写任务或审核的最新业务状态。",
        "expectedVersion": "用于并发保护，避免覆盖掉别人刚提交的变更。",
        "executionEvidenceRef": "填写执行证据，便于后续审核和复盘查证。",
        "blockedReason": "如果任务受阻，请明确记录阻塞原因。",
        "cycleKey": "用于标识当前复盘周期，例如周、月或运营批次。",
    }
    if field in help_map:
        return help_map[field]
    return ""


def _surface_contract_overrides(surface: str, *, locale: str) -> dict[str, list[str]]:
    lowered = surface.lower()
    zh = is_zh_locale(locale)
    if any(token in lowered for token in ("onboarding", "setup")) or any(token in surface for token in ("接入", "配置", "范围")):
        return {
            "summary_cards": ["租户权限状态", "范围草稿状态", "观测启动准备度"] if zh else ["Tenant policy status", "Scope draft status", "Observation start readiness"],
            "detail_fields_in_order": ["租户边界", "范围标识", "品牌名称", "竞品列表", "关注问题", "关键页面", "范围版本"] if zh else ["Tenant boundary", "Scope key", "Brand name", "Competitors", "Tracked questions", "Tracked pages", "Scope version"],
            "table_columns": ["对象", "当前值", "状态", "更新时间"] if zh else ["Object", "Current value", "Status", "Updated at"],
            "filters_and_selectors": ["租户边界", "范围标识"] if zh else ["Tenant boundary", "Scope key"],
        }
    if any(token in lowered for token in ("overview", "findings")) or any(token in surface for token in ("总览", "发现")):
        return {
            "summary_cards": ["高优先级发现", "平均评分", "待处理任务", "阻塞任务"] if zh else ["Priority findings", "Average score", "Open tasks", "Blocked tasks"],
            "detail_fields_in_order": ["发现 ID", "严重程度", "评分", "优先级", "建议状态", "任务 ID", "负责人"] if zh else ["Finding ID", "Severity", "Score", "Priority band", "Recommendation status", "Task ID", "Owner"],
            "table_columns": ["发现 ID", "严重程度", "评分", "优先级", "建议状态", "关联任务"] if zh else ["Finding ID", "Severity", "Score", "Priority", "Recommendation status", "Linked task"],
            "filters_and_selectors": ["租户", "观测运行", "优先级", "状态筛选"] if zh else ["Tenant", "Observation run", "Priority band", "Status filter"],
        }
    if "recommendation" in lowered or any(token in surface for token in ("建议", "导出")):
        return {
            "summary_cards": ["当前发现", "严重程度", "建议状态", "任务导出状态"] if zh else ["Current finding", "Severity", "Recommendation status", "Task export status"],
            "detail_fields_in_order": ["发现 ID", "差距说明", "竞品上下文", "归因边界", "建议 ID", "任务 ID"] if zh else ["Finding ID", "Gap explanation", "Competitor context", "Attribution seam", "Recommendation ID", "Task ID"],
            "table_columns": ["资产 ID", "资产类型", "建议状态", "任务状态"] if zh else ["Asset ID", "Asset type", "Recommendation status", "Task status"],
            "filters_and_selectors": ["发现 ID", "目标资产", "决策状态"] if zh else ["Finding ID", "Target asset", "Decision status"],
        }
    if "task" in lowered or "任务" in surface:
        return {
            "summary_cards": ["待处理任务", "进行中任务", "阻塞任务", "最新审计回执"] if zh else ["Open tasks", "In-progress tasks", "Blocked tasks", "Latest audit receipt"],
            "detail_fields_in_order": ["任务 ID", "任务状态", "负责人", "阻塞原因", "执行证据", "审计追踪"] if zh else ["Task ID", "Task status", "Owner", "Blocked reason", "Execution evidence", "Audit trace"],
            "table_columns": ["任务 ID", "当前状态", "负责人", "阻塞原因", "到期时间"] if zh else ["Task ID", "Current status", "Owner", "Blocked reason", "Due at"],
            "filters_and_selectors": ["范围", "状态", "负责人", "仅看阻塞项"] if zh else ["Scope", "Status", "Owner", "Blocked only"],
        }
    if "review" in lowered or any(token in surface for token in ("审核", "复盘", "修订")):
        return {
            "summary_cards": ["当前周期结论", "不确定性等级", "继续/修订建议", "审计记录"] if zh else ["Current cycle conclusion", "Uncertainty level", "Continue or revise", "Audit record"],
            "detail_fields_in_order": ["审核报告 ID", "审核摘要", "决策姿态", "阈值依据", "不确定性说明"] if zh else ["Review report ID", "Review summary", "Decision posture", "Threshold rationale", "Uncertainty note"],
            "table_columns": ["审计记录 ID", "动作类型", "追踪 ID"] if zh else ["Audit record ID", "Action type", "Trace ID"],
            "filters_and_selectors": ["复盘周期", "范围", "是否包含不确定性拆解"] if zh else ["Review cycle", "Scope", "Include uncertainty breakdown"],
        }
    return {}


def _merge_user_inputs_from_actions(actions: list[dict[str, Any]], *, locale: str, surface: str = "") -> list[dict[str, Any]]:
    def _source_entries(action: dict[str, Any], key: str) -> list[dict[str, Any]]:
        entries = action.get(key, [])
        if isinstance(entries, list):
            return [entry for entry in entries if isinstance(entry, dict)]
        return []

    ordered_fields: list[str] = []
    required_by_field: dict[str, bool] = {}
    preferred_entry_by_field: dict[str, dict[str, Any]] = {}
    for action in actions:
        required_fields = {
            str(field).strip()
            for field in action.get("required_fields", [])
            if str(field).strip()
        }
        for entry in [*_source_entries(action, "required_input_sources"), *_source_entries(action, "optional_input_sources")]:
            source = str(entry.get("source") or "").strip() or "user-input"
            value_source = str(entry.get("value_source") or source).strip() or source
            if source != "user-input" and value_source not in {"system-generated", "server-default"}:
                continue
            normalized = str(entry.get("field") or "").strip()
            if not normalized:
                continue
            if normalized not in ordered_fields:
                ordered_fields.append(normalized)
            if normalized in required_fields:
                required_by_field[normalized] = True
            else:
                required_by_field.setdefault(normalized, False)
            current = preferred_entry_by_field.get(normalized)
            candidate = dict(entry)
            if current is None:
                preferred_entry_by_field[normalized] = candidate
                continue
            current_editability = str(current.get("editability") or "").strip()
            candidate_editability = str(candidate.get("editability") or "").strip()
            if current_editability != "editable" and candidate_editability == "editable":
                preferred_entry_by_field[normalized] = candidate
                continue
            current_value_source = str(current.get("value_source") or current.get("source") or "").strip()
            if current_value_source != "user-input" and value_source == "user-input":
                preferred_entry_by_field[normalized] = candidate
    return [
        _make_input_spec(
            field,
            locale=locale,
            required=required_by_field.get(field, False),
            validation=str(preferred_entry_by_field.get(field, {}).get("validation") or "").strip() or None,
            surface=surface,
            value_source=str(preferred_entry_by_field.get(field, {}).get("value_source") or preferred_entry_by_field.get(field, {}).get("source") or "user-input").strip() or "user-input",
            editability=str(preferred_entry_by_field.get(field, {}).get("editability") or "").strip() or None,
            datatype=str(preferred_entry_by_field.get(field, {}).get("datatype") or "").strip() or None,
            control=str(preferred_entry_by_field.get(field, {}).get("control") or "").strip() or None,
            options=preferred_entry_by_field.get(field, {}).get("options") if isinstance(preferred_entry_by_field.get(field, {}).get("options"), list) else None,
            options_source=str(preferred_entry_by_field.get(field, {}).get("options_source") or "").strip() or None,
            system_generated=preferred_entry_by_field.get(field, {}).get("system_generated") if "system_generated" in preferred_entry_by_field.get(field, {}) else None,
            server_assigned=preferred_entry_by_field.get(field, {}).get("server_assigned") if "server_assigned" in preferred_entry_by_field.get(field, {}) else None,
            lookup_entity=str(preferred_entry_by_field.get(field, {}).get("lookup_entity") or "").strip() or None,
            display_format=str(preferred_entry_by_field.get(field, {}).get("display_format") or "").strip() or None,
        )
        for field in ordered_fields
    ]


def _field_source_mapping_from_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    semantic_keys = (
        "value_source",
        "editability",
        "datatype",
        "control",
        "options",
        "options_source",
        "system_generated",
        "server_assigned",
        "lookup_entity",
        "display_format",
        "internal_exposure",
    )
    for action in actions:
        api_binding = action.get("api_binding", {})
        bind_to = ""
        if isinstance(api_binding, dict):
            bind_to = f"{api_binding.get('method', '')} {api_binding.get('path', '')}".strip()
        entries = [
            *(
                entry
                for entry in action.get("required_input_sources", [])
                if isinstance(entry, dict)
            ),
            *(
                entry
                for entry in action.get("optional_input_sources", [])
                if isinstance(entry, dict)
            ),
        ]
        for entry in entries:
            normalized = str(entry.get("field") or "").strip()
            if not normalized:
                continue
            source = str(entry.get("source") or "").strip() or "user-input"
            key = (normalized, source)
            if key in seen:
                continue
            seen.add(key)
            mapping: dict[str, Any] = {
                "field": normalized,
                "source": source,
                "bind_to": str(entry.get("bind_to") or bind_to or "api-contract-to-be-finalized").strip(),
            }
            for semantic_key in semantic_keys:
                if semantic_key in entry:
                    mapping[semantic_key] = entry.get(semantic_key)
            mappings.append(mapping)
    return mappings


def _snake_case_field(value: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value).strip()).lower()


def _action_field_source(field: str) -> str:
    normalized = str(field).strip()
    snake = _snake_case_field(normalized)
    if normalized in {"tenantId", "tenant_id"} or snake == "tenant_id":
        return "user-input"
    if normalized in {
        "scopeKey",
        "brandName",
        "competitors",
        "questions",
        "pages",
        "priorityBands",
        "includeCompetitorWindow",
        "cursor",
        "pageSize",
        "statuses",
        "ownerSubjectId",
        "includeRecommendationSummary",
        "includeBlockedOnly",
        "sortBy",
        "includeCompetitorContext",
        "includeRecommendationContext",
        "includeAttributionSeam",
        "assetId",
        "decision",
        "decisionRationale",
        "priorityOverride",
        "attributionContextRef",
        "idempotencyKey",
        "status",
        "executionEvidenceRef",
        "blockedReason",
        "cycleKey",
        "freezeTaskStatusesBefore",
        "includeUncertaintyBreakdown",
        "query",
    }:
        return "user-input"
    if snake.endswith("_id") or normalized.endswith("Id") or "version" in snake or snake in {"status", "state"}:
        return "workflow-context"
    return "user-input"


def _annotate_action_input_sources(actions: list[dict[str, Any]], *, locale: str = "en") -> list[dict[str, Any]]:
    carried_context_fields: set[str] = set()
    carried_field_producers: dict[str, int] = {}
    annotated_actions: list[dict[str, Any]] = []
    for action in actions:
        annotated = dict(action)
        annotated["response_bindings"] = [
            dict(binding)
            for binding in action.get("response_bindings", [])
            if isinstance(binding, dict)
        ]
        api_binding = action.get("api_binding", {})
        bind_to = ""
        if isinstance(api_binding, dict):
            bind_to = f"{api_binding.get('method', '')} {api_binding.get('path', '')}".strip()

        def build_entries(fields: list[Any]) -> list[dict[str, Any]]:
            entries: list[dict[str, Any]] = []
            for field in fields:
                normalized = str(field).strip()
                if not normalized:
                    continue
                source = _action_field_source(normalized)
                bind_method, _, bind_path = bind_to.partition(" ")
                if (
                    source == "workflow-context"
                    and bind_method.upper() == "POST"
                    and normalized in _resource_id_candidates(bind_path)
                    and normalized not in carried_context_fields
                ):
                    source = "user-input"
                if source == "workflow-context" and normalized in carried_context_fields:
                    source = "response-binding"
                    producer_index = carried_field_producers.get(normalized)
                    if producer_index is not None:
                        producer_action = annotated_actions[producer_index]
                        producer_bindings = producer_action.setdefault("response_bindings", [])
                        if not any(
                            isinstance(binding, dict) and str(binding.get("to") or "").strip() == normalized
                            for binding in producer_bindings
                        ):
                            producer_bindings.append({"from": normalized, "to": normalized})
                entry: dict[str, Any] = {
                    "field": normalized,
                    "source": source,
                    "bind_to": bind_to or "api-contract-to-be-finalized",
                }
                entry.update(
                    _field_semantics(
                        normalized,
                        locale=locale,
                        validation=_field_default_validation(normalized),
                        source=source,
                        bind_to=bind_to,
                    )
                )
                entries.append(entry)
            return entries

        required_fields = [
            field
            for field in action.get("required_fields", [])
            if str(field).strip()
        ]
        optional_fields = [
            field
            for field in action.get("optional_fields", [])
            if str(field).strip()
        ]
        annotated["required_input_sources"] = build_entries(required_fields)
        annotated["optional_input_sources"] = build_entries(optional_fields)
        annotated_actions.append(annotated)
        action_index = len(annotated_actions) - 1

        for field in action.get("result_fields", []):
            normalized = str(field).strip()
            if normalized:
                carried_context_fields.add(normalized)
                carried_field_producers[normalized] = action_index
        for binding in action.get("response_bindings", []):
            if not isinstance(binding, dict):
                continue
            target = str(binding.get("to") or "").strip()
            if target:
                carried_context_fields.add(target)
                carried_field_producers[target] = action_index

    return annotated_actions


def _surface_business_blueprint(
    surface: str,
    page_endpoints: list[dict[str, Any]],
    *,
    locale: str,
) -> dict[str, Any] | None:
    endpoints_by_operation = {
        str(endpoint.get("operation_id") or "").strip(): endpoint
        for endpoint in page_endpoints
        if str(endpoint.get("operation_id") or "").strip()
    }
    lowered = surface.lower()
    if "onboarding" in lowered or "setup" in lowered or any(token in surface for token in ("接入", "范围", "配置")):
        actions = [
            _build_action_spec(
                endpoints_by_operation.get("GetTenantAccessPolicy"),
                locale=locale,
                summary_en="Confirm the working tenant before the scope setup starts.",
                summary_zh="先确认当前使用的是哪个工作租户，再开始填写范围信息。",
                required_fields=["tenantId"],
                result_fields=["tenantId", "role", "policyDecision"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("CreateTrackedScope"),
                locale=locale,
                summary_en="Create the tracked scope draft with brand, competitors, key questions, and target pages.",
                summary_zh="录入品牌、竞品、关注问题与关键页面，创建可观测的跟踪范围草稿。",
                required_fields=["tenantId", "scopeKey", "brandName", "competitors", "questions", "pages"],
                result_fields=["trackedScopeId", "status", "scopeVersion"],
                response_bindings=[{"from": "trackedScopeId", "to": "scopeId"}],
            ),
            _build_action_spec(
                endpoints_by_operation.get("GetAttributionSeamReference"),
                locale=locale,
                summary_en="Review attribution seam limits so downstream operators do not overstate ROI certainty.",
                summary_zh="查看当前范围的归因边界和口径限制，避免后续误读结果。",
                required_fields=["tenantId", "scopeId"],
                optional_fields=["scopeVersion"],
                result_fields=["scopeId", "scopeVersion", "sourceTag", "funnelStage", "conversionEvent", "authoritative", "reactivationTrigger"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("StartObservationRun"),
                locale=locale,
                summary_en="Start the first observation run for the current scope so the findings workspace can be populated.",
                summary_zh="基于当前范围启动第一轮观测，为后续发现列表和任务流转准备真实数据。",
                required_fields=["tenantId", "scopeId", "idempotencyKey"],
                result_fields=["observationRunId", "status", "scopeId"],
                response_bindings=[{"from": "observationRunId", "to": "observationRunId"}],
            ),
        ]
        resolved_actions = _annotate_action_input_sources([action for action in actions if action], locale=locale)
        if not resolved_actions:
            return None
        return {
            "page_role": "form-flow",
            "page_blueprint_type": "setup-flow",
            "subtitle": "先确认工作租户，再填写范围并启动首轮观测。",
            "user_goal": "完成跟踪范围接入，让系统具备后续发现、建议和审核所需的基线数据。",
            "primary_cta": {
                "label": "创建跟踪范围" if is_zh_locale(locale) else "Create tracked scope",
                "hint": "先确认工作租户，再创建范围草稿，并为后续观测保留 scopeId。"
                if is_zh_locale(locale)
                else "Validate the tenant first, then create the scope draft and carry the scopeId into observation.",
            },
            "secondary_cta": {
                "label": "刷新当前状态" if is_zh_locale(locale) else "Refresh current state",
                "kind": "refresh",
            },
            "sections": [
                {
                    "section_id": "tenant-policy",
                    "title": "工作租户确认" if is_zh_locale(locale) else "Working tenant",
                    "purpose": "先确认当前填写和提交会落在哪个工作租户下。"
                    if is_zh_locale(locale)
                    else "Make the current working tenant explicit before setup starts.",
                    "view": "summary-cards",
                    "bind_fields": ["tenantId", "role", "policyDecision"],
                },
                {
                    "section_id": "scope-draft",
                    "title": "范围草稿" if is_zh_locale(locale) else "Scope draft",
                    "purpose": "录入品牌、竞品、问题与关键页面，形成后续观测基线。"
                    if is_zh_locale(locale)
                    else "Capture the brand, competitors, questions, and target pages that define the scope baseline.",
                    "view": "form",
                    "bind_fields": ["scopeKey", "brandName", "competitors", "questions", "pages"],
                },
                {
                    "section_id": "run-readiness",
                    "title": "归因边界与观测启动" if is_zh_locale(locale) else "Attribution seam and run start",
                    "purpose": "在启动观测前查看归因限制，并确认 scopeId 已可用于下一步。"
                    if is_zh_locale(locale)
                    else "Review attribution seam limits and confirm the scope is ready before observation starts.",
                    "view": "next-steps",
                    "bind_fields": ["scopeId", "scopeVersion", "sourceTag", "funnelStage", "conversionEvent", "observationRunId"],
                },
            ],
            "data_presentation": ["summary-cards", "form-layout", "status-banner"],
            "display_fields": ["tenantId", "role", "policyDecision", "trackedScopeId", "status", "scopeVersion", "scopeId", "observationRunId"],
            "summary_cards": _surface_contract_overrides(surface, locale=locale).get("summary_cards", []),
            "detail_fields_in_order": _surface_contract_overrides(surface, locale=locale).get("detail_fields_in_order", []),
            "table_columns": _surface_contract_overrides(surface, locale=locale).get("table_columns", []),
            "filters_and_selectors": _surface_contract_overrides(surface, locale=locale).get("filters_and_selectors", []),
            "user_inputs": _merge_user_inputs_from_actions(resolved_actions, locale=locale, surface=surface),
            "field_source_mapping": _field_source_mapping_from_actions(resolved_actions),
            "actions_and_transitions": resolved_actions,
        }
    if "overview" in lowered or "findings" in lowered or any(token in surface for token in ("总览", "发现")):
        actions = [
            _build_action_spec(
                endpoints_by_operation.get("ListVisibilityFindings"),
                locale=locale,
                summary_en="Load the current findings list with priority filters and observation context.",
                summary_zh="加载当前观测周期的发现列表，并按优先级筛选需要优先处理的问题。",
                required_fields=["tenantId", "observationRunId"],
                optional_fields=["priorityBands", "includeCompetitorWindow", "cursor", "pageSize"],
                result_fields=["findingId", "severity", "score", "priorityBand", "measurementWindow", "recommendationStatus", "traceAnchor"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("ListOptimizationTasks"),
                locale=locale,
                summary_en="Refresh the task board so findings and execution work stay visible together.",
                summary_zh="刷新任务看板，让发现优先级与执行状态保持在同一工作面里可见。",
                required_fields=["tenantId", "scopeId"],
                optional_fields=["statuses", "ownerSubjectId", "includeRecommendationSummary", "includeBlockedOnly", "sortBy", "cursor", "pageSize"],
                result_fields=["taskId", "status", "ownerSubjectId", "blockedReason", "recommendationId", "queuePosition", "dueAt"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("GetCompetitorSnapshot"),
                locale=locale,
                summary_en="Inspect the latest competitor comparison snapshot for the active scope.",
                summary_zh="查看当前范围的最新竞品快照，确认发现所依赖的比较窗口与分值背景。",
                required_fields=["tenantId", "scopeId"],
                result_fields=["scopeId", "comparativeScore", "snapshotRef"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("ListAuditTrail"),
                locale=locale,
                summary_en="Open the audit trail when a finding or task state needs trace evidence.",
                summary_zh="在需要追溯发现或任务变化时，打开审计轨迹查看关键证据。",
                required_fields=["tenantId"],
                optional_fields=["cursor", "pageSize"],
                result_fields=["auditRecordId", "actionType", "traceId"],
            ),
        ]
        resolved_actions = _annotate_action_input_sources([action for action in actions if action], locale=locale)
        if not resolved_actions:
            return None
        return {
            "page_role": "workspace",
            "page_blueprint_type": "analysis-board",
            "subtitle": "把发现列表、任务看板和竞品背景放在同一工作面里联动查看。",
            "user_goal": "快速判断当前观测周期里哪些问题最值得优先处理，以及哪些任务正在推进或受阻。",
            "primary_cta": {
                "label": "加载发现列表" if is_zh_locale(locale) else "Load findings",
                "hint": "先看当前发现，再按需切到任务看板、竞品快照或审计轨迹。"
                if is_zh_locale(locale)
                else "Start with findings, then pivot into the task board, competitor snapshot, or audit trail as needed.",
            },
            "secondary_cta": {
                "label": "刷新当前状态" if is_zh_locale(locale) else "Refresh current state",
                "kind": "refresh",
            },
            "sections": [
                {
                    "section_id": "cycle-summary",
                    "title": "当前周期概览" if is_zh_locale(locale) else "Current cycle summary",
                    "purpose": "把当前观测周期内最重要的发现、分值与状态聚合在一起。"
                    if is_zh_locale(locale)
                    else "Summarize the most important findings, scores, and statuses in the current observation cycle.",
                    "view": "summary-cards",
                    "bind_fields": ["findingId", "severity", "score", "priorityBand", "recommendationStatus"],
                },
                {
                    "section_id": "findings-board",
                    "title": "优先发现" if is_zh_locale(locale) else "Priority findings",
                    "purpose": "集中查看需要进入建议与任务流转的高优先级发现。"
                    if is_zh_locale(locale)
                    else "Keep the findings that should move into recommendation and task handoff visible together.",
                    "view": "list",
                    "bind_fields": ["findingId", "severity", "score", "priorityBand", "measurementWindow"],
                },
                {
                    "section_id": "task-board",
                    "title": "执行任务看板" if is_zh_locale(locale) else "Execution task board",
                    "purpose": "并排查看任务状态、负责人和阻塞原因，避免只看到发现不看到执行。"
                    if is_zh_locale(locale)
                    else "Keep task status, owner, and blocked reason visible so execution does not drift away from findings.",
                    "view": "table",
                    "bind_fields": ["taskId", "status", "ownerSubjectId", "blockedReason", "dueAt"],
                },
            ],
            "data_presentation": ["summary-cards", "table-or-list", "status-banner"],
            "display_fields": ["findingId", "severity", "score", "priorityBand", "recommendationStatus", "taskId", "status", "ownerSubjectId"],
            "summary_cards": _surface_contract_overrides(surface, locale=locale).get("summary_cards", []),
            "detail_fields_in_order": _surface_contract_overrides(surface, locale=locale).get("detail_fields_in_order", []),
            "table_columns": _surface_contract_overrides(surface, locale=locale).get("table_columns", []),
            "filters_and_selectors": _surface_contract_overrides(surface, locale=locale).get("filters_and_selectors", []),
            "user_inputs": _merge_user_inputs_from_actions(resolved_actions, locale=locale, surface=surface),
            "field_source_mapping": _field_source_mapping_from_actions(resolved_actions),
            "actions_and_transitions": resolved_actions,
        }
    if "recommendation" in lowered or any(token in surface for token in ("建议", "导出")):
        actions = [
            _build_action_spec(
                endpoints_by_operation.get("GetFindingDetail"),
                locale=locale,
                summary_en="Open the full finding detail with competitor context, recommendation options, and attribution seam.",
                summary_zh="打开完整发现详情，把竞品背景、建议选项与归因边界放在同一个决策面里查看。",
                required_fields=["tenantId", "findingId"],
                optional_fields=["expectedFindingVersion", "includeCompetitorContext", "includeRecommendationContext", "includeAttributionSeam"],
                result_fields=["findingId", "severity", "priorityBand", "gapExplanation", "measurementWindow", "competitorContext", "recommendationOptions", "attributionSeam"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("GetContentAssetCatalog"),
                locale=locale,
                summary_en="Load the current content assets so the recommendation can target a concrete editable asset.",
                summary_zh="加载当前内容资产目录，为建议决策选择明确可编辑的目标资产。",
                required_fields=["tenantId", "scopeId"],
                optional_fields=["cursor"],
                result_fields=["contentAssetId", "path", "assetType"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("CreateRecommendationDecision"),
                locale=locale,
                summary_en="Freeze the recommendation decision with rationale, target asset, and priority override.",
                summary_zh="记录建议决策，冻结目标资产、决策理由和优先级覆盖，形成可导出的 payload。",
                required_fields=["tenantId", "findingId", "assetId", "decision", "decisionRationale", "priorityOverride", "attributionContextRef"],
                result_fields=["recommendationId", "status", "payloadVersion"],
                response_bindings=[{"from": "recommendationId", "to": "recommendationId"}],
            ),
            _build_action_spec(
                endpoints_by_operation.get("CreateOptimizationTask"),
                locale=locale,
                summary_en="Export the approved recommendation into an optimization task with an explicit owner.",
                summary_zh="把已确认的建议导出成优化任务，并明确负责人和幂等键。",
                required_fields=["tenantId", "recommendationId", "ownerSubjectId", "idempotencyKey"],
                result_fields=["taskId", "status", "queuePosition", "expectedVersion"],
                response_bindings=[{"from": "taskId", "to": "taskId"}, {"from": "expectedVersion", "to": "expectedVersion"}],
            ),
        ]
        resolved_actions = _annotate_action_input_sources([action for action in actions if action], locale=locale)
        if not resolved_actions:
            return None
        return {
            "page_role": "detail",
            "page_blueprint_type": "record-workbench",
            "subtitle": "围绕单个发现完成诊断、建议决策和任务导出，而不是把这些动作拆散在不同调试页里。",
            "user_goal": "针对一个具体发现完成诊断与建议冻结，并把确定的建议导出到任务执行链路。",
            "primary_cta": {
                "label": "加载发现详情" if is_zh_locale(locale) else "Load finding detail",
                "hint": "先确认发现诊断，再冻结建议决策，最后导出任务。"
                if is_zh_locale(locale)
                else "Inspect the finding first, then freeze the recommendation decision and export the task.",
            },
            "secondary_cta": {
                "label": "刷新当前状态" if is_zh_locale(locale) else "Refresh current state",
                "kind": "refresh",
            },
            "sections": [
                {
                    "section_id": "finding-diagnosis",
                    "title": "发现诊断" if is_zh_locale(locale) else "Finding diagnosis",
                    "purpose": "集中查看差距说明、竞品上下文和归因边界，避免脱离上下文做建议。"
                    if is_zh_locale(locale)
                    else "Keep the gap explanation, competitor context, and attribution seam visible before a recommendation is frozen.",
                    "view": "detail",
                    "bind_fields": ["findingId", "severity", "gapExplanation", "measurementWindow", "competitorContext", "attributionSeam"],
                },
                {
                    "section_id": "decision-freeze",
                    "title": "建议决策" if is_zh_locale(locale) else "Recommendation decision",
                    "purpose": "填写目标资产、决策理由和优先级，形成可追溯的建议 payload。"
                    if is_zh_locale(locale)
                    else "Capture the target asset, rationale, and priority to freeze a traceable recommendation payload.",
                    "view": "form",
                    "bind_fields": ["assetId", "decision", "decisionRationale", "priorityOverride", "attributionContextRef"],
                },
                {
                    "section_id": "task-export",
                    "title": "任务导出" if is_zh_locale(locale) else "Task export",
                    "purpose": "确认 recommendationId 与负责人后，把建议明确地导出为任务。"
                    if is_zh_locale(locale)
                    else "Carry the recommendationId and owner assignment forward into task export.",
                    "view": "status-banner",
                    "bind_fields": ["recommendationId", "ownerSubjectId", "taskId", "queuePosition", "expectedVersion"],
                },
            ],
            "data_presentation": ["entity-summary", "timeline", "state-badges"],
            "display_fields": ["findingId", "severity", "gapExplanation", "measurementWindow", "competitorContext", "recommendationId", "taskId", "status"],
            "summary_cards": _surface_contract_overrides(surface, locale=locale).get("summary_cards", []),
            "detail_fields_in_order": _surface_contract_overrides(surface, locale=locale).get("detail_fields_in_order", []),
            "table_columns": _surface_contract_overrides(surface, locale=locale).get("table_columns", []),
            "filters_and_selectors": _surface_contract_overrides(surface, locale=locale).get("filters_and_selectors", []),
            "user_inputs": _merge_user_inputs_from_actions(resolved_actions, locale=locale, surface=surface),
            "field_source_mapping": _field_source_mapping_from_actions(resolved_actions),
            "actions_and_transitions": resolved_actions,
        }
    if ("task" in lowered and any(token in lowered for token in ("update", "state"))) or "任务" in surface:
        actions = [
            _build_action_spec(
                endpoints_by_operation.get("ListOptimizationTasks"),
                locale=locale,
                summary_en="Open the task board with owner, recommendation link, and blocked reason visible together.",
                summary_zh="打开任务看板，同时查看负责人、上游建议关联和阻塞原因。",
                required_fields=["tenantId", "scopeId"],
                optional_fields=["statuses", "ownerSubjectId", "includeRecommendationSummary", "includeBlockedOnly", "sortBy", "cursor", "pageSize"],
                result_fields=["taskId", "status", "ownerSubjectId", "blockedReason", "recommendationId", "dueAt", "expectedVersion"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("UpdateOptimizationTaskStatus"),
                locale=locale,
                summary_en="Update one task with the next status, expected version, and execution evidence.",
                summary_zh="针对单个任务提交新的状态、版本号和执行证据，保证状态变更可追溯。",
                required_fields=["tenantId", "taskId", "status", "expectedVersion", "executionEvidenceRef"],
                optional_fields=["blockedReason"],
                result_fields=["taskId", "status", "version", "blockedReason", "executionEvidenceRef", "auditTraceRef"],
                response_bindings=[{"from": "version", "to": "expectedVersion"}],
            ),
            _build_action_spec(
                endpoints_by_operation.get("ListAuditTrail"),
                locale=locale,
                summary_en="Inspect the audit evidence that confirms the latest task mutation.",
                summary_zh="查看审计轨迹，确认任务状态变化已经留下可追溯证据。",
                required_fields=["tenantId"],
                optional_fields=["cursor", "pageSize"],
                result_fields=["auditRecordId", "actionType", "traceId"],
            ),
        ]
        resolved_actions = _annotate_action_input_sources([action for action in actions if action], locale=locale)
        if not resolved_actions:
            return None
        return {
            "page_role": "workflow",
            "page_blueprint_type": "execution-workbench",
            "subtitle": "把任务看板、状态更新和审计回执放到同一工作面里，避免任务状态变更脱离上下文。",
            "user_goal": "保持优化任务的执行状态、版本和证据链最新，并让后续审核始终看到真实任务面貌。",
            "primary_cta": {
                "label": "加载任务列表" if is_zh_locale(locale) else "Load task board",
                "hint": "先打开任务看板，再提交单个任务状态更新，并用审计轨迹确认回执。"
                if is_zh_locale(locale)
                else "Open the task board first, then submit one task update and confirm it in the audit trail.",
            },
            "secondary_cta": {
                "label": "刷新当前状态" if is_zh_locale(locale) else "Refresh current state",
                "kind": "refresh",
            },
            "sections": [
                {
                    "section_id": "task-board",
                    "title": "任务看板" if is_zh_locale(locale) else "Task board",
                    "purpose": "集中查看任务状态、负责人、阻塞原因和上游建议关联。"
                    if is_zh_locale(locale)
                    else "Keep task status, owner, blocked reason, and recommendation linkage visible together.",
                    "view": "table",
                    "bind_fields": ["taskId", "status", "ownerSubjectId", "blockedReason", "recommendationId", "dueAt"],
                },
                {
                    "section_id": "status-update",
                    "title": "状态更新" if is_zh_locale(locale) else "Status update",
                    "purpose": "填写版本号和执行证据，避免任务状态被无痕覆盖。"
                    if is_zh_locale(locale)
                    else "Capture the expected version and execution evidence so task state never changes silently.",
                    "view": "form",
                    "bind_fields": ["taskId", "status", "expectedVersion", "executionEvidenceRef", "blockedReason"],
                },
                {
                    "section_id": "audit-receipt",
                    "title": "审计回执" if is_zh_locale(locale) else "Audit receipt",
                    "purpose": "在状态提交后确认审计记录和追踪引用已经生成。"
                    if is_zh_locale(locale)
                    else "Confirm that an audit record and trace reference were generated after the update.",
                    "view": "detail-list",
                    "bind_fields": ["auditTraceRef", "auditRecordId", "traceId"],
                },
            ],
            "data_presentation": ["status-banner", "table-or-list", "submission-result"],
            "display_fields": ["taskId", "status", "ownerSubjectId", "blockedReason", "recommendationId", "expectedVersion", "auditTraceRef"],
            "summary_cards": _surface_contract_overrides(surface, locale=locale).get("summary_cards", []),
            "detail_fields_in_order": _surface_contract_overrides(surface, locale=locale).get("detail_fields_in_order", []),
            "table_columns": _surface_contract_overrides(surface, locale=locale).get("table_columns", []),
            "filters_and_selectors": _surface_contract_overrides(surface, locale=locale).get("filters_and_selectors", []),
            "user_inputs": _merge_user_inputs_from_actions(resolved_actions, locale=locale, surface=surface),
            "field_source_mapping": _field_source_mapping_from_actions(resolved_actions),
            "actions_and_transitions": resolved_actions,
        }
    if "review" in lowered or any(token in surface for token in ("审核", "继续", "修订")):
        actions = [
            _build_action_spec(
                endpoints_by_operation.get("GenerateReviewReport"),
                locale=locale,
                summary_en="Generate the review report for the current cycle and keep uncertainty explicit in the result.",
                summary_zh="为当前周期生成审核报告，并让不确定性、阈值依据和 posture 一并返回。",
                required_fields=["tenantId", "scopeId", "cycleKey", "freezeTaskStatusesBefore"],
                optional_fields=["includeUncertaintyBreakdown"],
                result_fields=["reviewReportId", "status", "decisionPosture", "uncertaintyLevel", "uncertaintyNote", "thresholdRationale", "reviewSummary"],
            ),
            _build_action_spec(
                endpoints_by_operation.get("ListAuditTrail"),
                locale=locale,
                summary_en="Inspect the audit trail for review-sensitive events and carry the evidence into the next cycle.",
                summary_zh="查看审核相关的审计轨迹，把回执和敏感边界证据带入下一周期。",
                required_fields=["tenantId"],
                optional_fields=["cursor", "pageSize"],
                result_fields=["auditRecordId", "actionType", "traceId"],
            ),
        ]
        resolved_actions = _annotate_action_input_sources([action for action in actions if action], locale=locale)
        if not resolved_actions:
            return None
        return {
            "page_role": "review",
            "page_blueprint_type": "review-decision",
            "subtitle": "先冻结当前周期审核结果，再查看审计证据；当前后端返回 decision posture，但未提供独立的 continue/revise 写入接口。",
            "user_goal": "完成当前周期审核总结，保留不确定性和阈值依据，并把结论与审计证据一起带入下一步。",
            "primary_cta": {
                "label": "生成审核报告" if is_zh_locale(locale) else "Generate review report",
                "hint": "当前可生成报告并查看系统返回的 decision posture；显式写入 continue/revise 决策仍需要后端补充接口。"
                if is_zh_locale(locale)
                else "This page can generate the report and show the returned decision posture; an explicit continue/revise write endpoint is still missing.",
            },
            "secondary_cta": {
                "label": "刷新当前状态" if is_zh_locale(locale) else "Refresh current state",
                "kind": "refresh",
            },
            "sections": [
                {
                    "section_id": "cycle-input",
                    "title": "周期输入" if is_zh_locale(locale) else "Cycle input",
                    "purpose": "填写范围、周期和冻结时间，确保审核报告基于固定任务快照生成。"
                    if is_zh_locale(locale)
                    else "Capture the scope, cycle, and freeze timestamp so the review is generated from a pinned task snapshot.",
                    "view": "form",
                    "bind_fields": ["scopeId", "cycleKey", "freezeTaskStatusesBefore", "includeUncertaintyBreakdown"],
                },
                {
                    "section_id": "review-outcome",
                    "title": "审核结论" if is_zh_locale(locale) else "Review outcome",
                    "purpose": "展示系统返回的 posture、不确定性和阈值依据，明确这是一份冻结结果。"
                    if is_zh_locale(locale)
                    else "Surface the returned posture, uncertainty, and threshold rationale as a frozen review outcome.",
                    "view": "summary-cards",
                    "bind_fields": ["reviewReportId", "decisionPosture", "uncertaintyLevel", "uncertaintyNote", "thresholdRationale"],
                },
                {
                    "section_id": "review-audit",
                    "title": "审计与后续" if is_zh_locale(locale) else "Audit and follow-up",
                    "purpose": "补充审核敏感边界的审计证据，并明确下一轮应继续还是补充更多证据。"
                    if is_zh_locale(locale)
                    else "Add audit evidence for review-sensitive edges and make the next cycle's follow-up explicit.",
                    "view": "detail-list",
                    "bind_fields": ["reviewSummary", "auditRecordId", "actionType", "traceId"],
                },
            ],
            "data_presentation": ["summary-cards", "detail-panel", "status-banner"],
            "display_fields": ["reviewReportId", "status", "decisionPosture", "uncertaintyLevel", "uncertaintyNote", "thresholdRationale", "reviewSummary"],
            "summary_cards": _surface_contract_overrides(surface, locale=locale).get("summary_cards", []),
            "detail_fields_in_order": _surface_contract_overrides(surface, locale=locale).get("detail_fields_in_order", []),
            "table_columns": _surface_contract_overrides(surface, locale=locale).get("table_columns", []),
            "filters_and_selectors": _surface_contract_overrides(surface, locale=locale).get("filters_and_selectors", []),
            "user_inputs": _merge_user_inputs_from_actions(resolved_actions, locale=locale, surface=surface),
            "field_source_mapping": _field_source_mapping_from_actions(resolved_actions),
            "actions_and_transitions": resolved_actions,
        }
    return None


def _infer_page_role(surface: str, page_endpoints: list[dict[str, Any]], *, page_index: int) -> str:
    lowered = surface.lower()
    methods = {str(endpoint.get("method", "")).upper() for endpoint in page_endpoints}
    if "review" in lowered or "审核" in surface:
        return "review"
    if ("task" in lowered and any(token in lowered for token in ("update", "state", "workflow"))) or "任务" in surface:
        return "workflow"
    if any(token in lowered for token in ("recommendation", "detail", "export")) or any(token in surface for token in ("建议", "详情", "导出")):
        return "detail"
    if any(token in lowered for token in ("overview", "dashboard", "findings", "home")) or any(token in surface for token in ("总览", "发现", "首页")):
        return "workspace"
    if any(token in lowered for token in ("list", "queue", "catalog", "search")) or any(token in surface for token in ("列表", "清单", "搜索")):
        return "list"
    if any(token in lowered for token in ("onboarding", "setup", "create", "new", "edit", "form")) or any(token in surface for token in ("接入", "配置", "创建", "编辑", "表单")):
        return "form-flow"
    if methods & {"POST", "PUT", "PATCH", "DELETE"}:
        return "form-flow"
    if page_index == 0:
        return "workspace"
    return "detail"


def _infer_page_blueprint_type(surface: str, page_role: str, prototype_page_contract: dict[str, Any] | None = None) -> str:
    if prototype_page_contract and str(prototype_page_contract.get("page_blueprint_type") or "").strip():
        return _normalize_blueprint_type(
            prototype_page_contract.get("page_blueprint_type"),
            preserve_unknown=True,
        )
    lowered = surface.lower()
    if page_role == "review" or "review" in lowered or "审核" in surface:
        return "review-decision"
    if page_role == "workflow" or "task" in lowered or "任务" in surface:
        return "execution-workbench"
    if page_role == "detail" or any(token in lowered for token in ("detail", "profile", "view")) or any(token in surface for token in ("详情", "资料")):
        return "detail-view"
    if page_role == "workspace" or "overview" in lowered or any(token in surface for token in ("总览", "发现")):
        return "analysis-board"
    if page_role == "form-flow" or any(token in lowered for token in ("onboarding", "setup", "create")) or any(token in surface for token in ("接入", "配置", "创建")):
        return "setup-flow"
    if page_role == "list":
        return "analysis-board"
    return "detail-view"


def _canonical_page_role_from_blueprint(page_blueprint_type: str, *, fallback: str = "") -> str:
    blueprint = _normalize_blueprint_type(page_blueprint_type, preserve_unknown=True)
    if blueprint == "setup-flow":
        return "form-flow"
    if blueprint in {"record-workbench", "execution-workbench"}:
        return "workflow"
    if blueprint in {"analysis-board", "dashboard"}:
        return "workspace"
    if blueprint == "detail-view":
        return "detail"
    if blueprint == "review-decision":
        return "review"
    return str(fallback or "").strip() or "workflow"


def _refine_page_blueprint_type_from_runtime_semantics(
    surface: str,
    page_blueprint_type: str,
    *,
    page_role: str,
    user_inputs: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    methods: set[str] | None = None,
) -> str:
    normalized = _normalize_blueprint_type(page_blueprint_type, preserve_unknown=True)
    lowered = str(surface or "").strip().lower()
    normalized_role = str(page_role or "").strip().lower()
    input_rows = [item for item in (user_inputs or []) if isinstance(item, dict) and str(item.get("field") or "").strip()]
    has_form_inputs = bool(input_rows)
    method_set = {str(item).strip().upper() for item in (methods or set()) if str(item).strip()}
    action_rows = [item for item in (actions or []) if isinstance(item, dict)]
    for action in action_rows:
        api_binding = action.get("api_binding") if isinstance(action.get("api_binding"), dict) else {}
        method = str(api_binding.get("method") or action.get("http_method") or "").strip().upper()
        if method:
            method_set.add(method)
    has_mutation = bool(method_set & {"POST", "PUT", "PATCH", "DELETE"})
    if not has_mutation:
        mutation_verbs = (
            "save",
            "create",
            "update",
            "record",
            "register",
            "schedule",
            "submit",
            "confirm",
            "pay",
            "close",
            "publish",
            "approve",
            "accept",
            "登记",
            "创建",
            "更新",
            "提交",
            "确认",
            "预约",
            "支付",
            "关闭",
            "审核",
        )
        for action in action_rows:
            action_text = str(action.get("action") or "").strip().lower()
            if action_text and any(verb in action_text for verb in mutation_verbs):
                has_mutation = True
                break
    is_review = normalized_role == "review" or "review" in lowered or "审核" in str(surface or "")
    is_creation = (
        normalized_role == "form-flow"
        or any(token in lowered for token in ("onboarding", "setup", "create", "new", "registration", "register", "intake"))
        or any(token in str(surface or "") for token in ("创建", "登记", "接入", "配置"))
    )
    if normalized == "detail-view":
        if is_review:
            return "review-decision"
        if has_mutation and has_form_inputs:
            return "setup-flow" if is_creation else "record-workbench"
    if not normalized and has_mutation and has_form_inputs:
        return "setup-flow" if is_creation else "record-workbench"
    return normalized or page_blueprint_type


def _default_blueprint_semantics(page_blueprint_type: str, *, locale: str = "en") -> dict[str, Any]:
    zh = is_zh_locale(locale)
    normalized = _normalize_blueprint_type(page_blueprint_type, preserve_unknown=True)
    defaults = {
        "setup-flow": {
            "primary_work_region": "以范围配置表单为主工作区，旁边保留权限与就绪度说明",
            "secondary_support_regions": [
                "治理/权限摘要区",
                "激活结果与下一步去向区",
            ],
            "dominant_component_pattern": "表单主工作区 + 就绪度侧栏",
            "action_model": "先确认约束，再提交配置并把成功结果带入下一步",
        },
        "analysis-board": {
            "primary_work_region": "以发现/对象列表为主工作区，并保持当前优先级上下文可见",
            "secondary_support_regions": [
                "周期摘要与状态指示区",
                "关联任务/竞品/审计支持区",
            ],
            "dominant_component_pattern": "摘要条 + 主列表/看板 + 支持侧栏",
            "action_model": "先浏览优先对象，再进入详情或下游动作",
        },
        "record-workbench": {
            "primary_work_region": "以单条业务记录详情和可提交的决策/状态表单并排构成主工作区",
            "secondary_support_regions": [
                "相关记录/历史支撑区",
                "交接结果与下游影响区",
            ],
            "dominant_component_pattern": "记录详情面板 + 决策/状态表单 + 交接结果区",
            "action_model": "先检查当前记录，再提交决策或状态更新，并保留可继续流转的结果",
        },
        "execution-workbench": {
            "primary_work_region": "以任务列表和状态更新面板组合成主工作区",
            "secondary_support_regions": [
                "审计回执区",
                "阻塞与版本确认区",
            ],
            "dominant_component_pattern": "任务表格 + 更新表单 + 审计侧栏",
            "action_model": "选中任务，提交状态变更，并确认回执与版本",
        },
        "review-decision": {
            "primary_work_region": "以审核结论和决策输入构成主工作区",
            "secondary_support_regions": [
                "不确定性/阈值依据区",
                "审计与后续动作区",
            ],
            "dominant_component_pattern": "审核摘要 + 决策区 + 后续说明区",
            "action_model": "生成审核结果，判断 posture，并明确下一周期动作",
        },
        "detail-view": {
            "primary_work_region": "以单个业务对象的重点详情和当前状态为主工作区",
            "secondary_support_regions": ["关联上下文区", "后续动作区"],
            "dominant_component_pattern": "详情阅读面 + 支撑上下文 + 有边界的后续动作区",
            "action_model": "先理解当前对象与状态，再执行边界清晰的后续动作",
        },
    }
    if normalized in defaults:
        resolved = defaults[normalized]
    elif str(page_blueprint_type or "").strip():
        resolved = {
            "primary_work_region": (
                f"当前合同声明了未支持的页面蓝图 `{page_blueprint_type}`，必须先补齐对应渲染器。"
                if zh
                else f"The contract declares unsupported blueprint '{page_blueprint_type}'. Add a dedicated renderer before implementation continues."
            ),
            "secondary_support_regions": [
                "合同与渲染器差异说明区" if zh else "contract and renderer mismatch note",
                "后续修复与交接区" if zh else "follow-up remediation area",
            ],
            "dominant_component_pattern": "unsupported-blueprint-contract",
            "action_model": "禁止静默回退为通用详情页。" if zh else "Do not silently fall back to a generic detail shell.",
        }
    else:
        resolved = defaults["detail-view"]
    if zh:
        return resolved
    english_defaults = {
        "setup-flow": {
            "primary_work_region": "a setup form as the main work area with governance and readiness kept alongside it",
            "secondary_support_regions": ["governance and permission summary", "activation outcome and next route"],
            "dominant_component_pattern": "form-led setup surface with a readiness side rail",
            "action_model": "confirm constraints, submit the setup data, and carry the successful result into the next step",
        },
        "analysis-board": {
            "primary_work_region": "a list or board of the active findings/records as the main work area",
            "secondary_support_regions": ["cycle summary and state indicators", "task/competitor/audit support context"],
            "dominant_component_pattern": "summary strip plus main board/list with a support rail",
            "action_model": "review priorities first, then drill into the next downstream action",
        },
        "record-workbench": {
            "primary_work_region": "a single-record workbench that keeps the live record context beside the commit action",
            "secondary_support_regions": ["related history or support context", "handoff outcome and downstream consequence area"],
            "dominant_component_pattern": "record detail panel plus a decision or state-update form with visible handoff results",
            "action_model": "inspect the current record, commit the next decision or state change, and keep the downstream result visible",
        },
        "execution-workbench": {
            "primary_work_region": "a task list paired with a status update panel",
            "secondary_support_regions": ["audit receipt", "blocked reason and version confirmation"],
            "dominant_component_pattern": "task table with update form and audit rail",
            "action_model": "select a task, submit the next mutation, and confirm the receipt and version",
        },
        "review-decision": {
            "primary_work_region": "a review summary and decision area kept together",
            "secondary_support_regions": ["uncertainty and threshold support", "audit and follow-up area"],
            "dominant_component_pattern": "review summary with decision panel and follow-up support",
            "action_model": "generate the review result, inspect posture, and make the next-cycle move explicit",
        },
        "detail-view": {
            "primary_work_region": "a focused detail surface for one business object and its current state",
            "secondary_support_regions": ["related context", "bounded follow-up actions"],
            "dominant_component_pattern": "detail reading surface with supporting context and clearly bounded next actions",
            "action_model": "understand the current object and state first, then take the bounded next action",
        },
    }
    if normalized in english_defaults:
        return english_defaults[normalized]
    return resolved


def _layout_for_blueprint(page_blueprint_type: str) -> dict[str, Any]:
    normalized = _normalize_blueprint_type(page_blueprint_type, preserve_unknown=True)
    layouts = {
        "analysis-board": {
            "pattern": "dashboard",
            "regions": ["summary-kpi-strip", "primary-chart-area", "detail-table"],
            "sidebar": "filter-panel",
            "prohibited": ["generic-card-stack", "api-explorer"],
        },
        "record-workbench": {
            "pattern": "master-detail-workbench",
            "regions": ["record-summary", "decision-panel", "handoff-panel"],
            "sidebar": "support-context",
            "prohibited": ["single-form", "raw-json-display"],
        },
        "execution-workbench": {
            "pattern": "kanban-or-list",
            "regions": ["status-filter-bar", "task-list", "inline-action-area"],
            "sidebar": "none",
            "prohibited": ["static-text-dump", "api-call-buttons"],
        },
        "setup-flow": {
            "pattern": "wizard",
            "regions": ["step-indicator", "form-area", "validation-feedback"],
            "sidebar": "help-panel",
            "prohibited": ["single-page-dump", "debug-console"],
        },
        "review-decision": {
            "pattern": "report-with-action",
            "regions": ["evidence-summary", "metric-highlights", "decision-action-area"],
            "sidebar": "none",
            "prohibited": ["raw-data-table", "api-response-panel"],
        },
        "detail-view": {
            "pattern": "focused-detail",
            "regions": ["record-header", "detail-reading", "related-actions"],
            "sidebar": "support-context",
            "prohibited": ["generic-json-viewer"],
        },
    }
    if normalized in layouts:
        return layouts[normalized]
    return {
        "pattern": "unsupported-blueprint",
        "regions": ["contract-mismatch"],
        "sidebar": "none",
        "prohibited": ["generic-card-stack", "api-explorer", "generic-json-viewer"],
    }


def _transition_spec(
    *,
    domain_object: str,
    from_state: str,
    to_state: str,
    trigger_action: str,
    ui_state_change: str,
    evidence_fields: list[str],
) -> dict[str, Any]:
    return {
        "domain_object": domain_object,
        "from_state": from_state,
        "to_state": to_state,
        "trigger_action": trigger_action,
        "ui_state_change": ui_state_change,
        "evidence_fields": [field for field in evidence_fields if str(field).strip()],
    }


def _action_label_at(actions: list[dict[str, Any]], index: int, fallback: str) -> str:
    if 0 <= index < len(actions):
        label = str(actions[index].get("action") or "").strip()
        if label:
            return label
    return fallback


_TRANSITION_PATH_SKIP_TOKENS = {
    "api",
    "detail",
    "details",
    "flow",
    "history",
    "list",
    "queue",
    "search",
    "status",
    "summary",
    "summaries",
}
_TRANSITION_ACTION_PREFIXES = (
    "accept",
    "approve",
    "book",
    "confirm",
    "continue",
    "create",
    "delete",
    "export",
    "generate",
    "inspect",
    "issue",
    "launch",
    "load",
    "manage",
    "open",
    "record",
    "refresh",
    "register",
    "resume",
    "review",
    "run",
    "save",
    "schedule",
    "select",
    "start",
    "submit",
    "update",
    "validate",
    "view",
)


def _transition_resource_from_path(api_path: str) -> str:
    segments = [
        _singularize_token(segment)
        for segment in str(api_path).split("/")
        if segment
        and segment not in {"api"}
        and not re.fullmatch(r"v\d+", segment)
        and not segment.startswith("{")
    ]
    for token in reversed(segments):
        if token and token not in _TRANSITION_PATH_SKIP_TOKENS:
            return token
    return ""


def _transition_domain_object_from_action(action: dict[str, Any], *, locale: str) -> str:
    zh = is_zh_locale(locale)
    response_bindings = [
        dict(binding)
        for binding in action.get("response_bindings", [])
        if isinstance(binding, dict)
    ]
    candidate_fields = [
        str(binding.get("to") or "").strip()
        for binding in response_bindings
        if str(binding.get("to") or "").strip()
    ]
    candidate_fields.extend(
        str(field).strip()
        for field in action.get("result_fields", [])
        if str(field).strip()
    )
    candidate_fields.extend(
        str(field).strip()
        for field in action.get("required_fields", [])
        if str(field).strip()
    )
    for field in candidate_fields:
        entity = _lookup_entity_for_field(field)
        if entity:
            humanized = _humanize_identifier(entity)
            return humanized if zh else humanized.lower()
    api_binding = action.get("api_binding", {})
    if isinstance(api_binding, dict):
        resource = _transition_resource_from_path(str(api_binding.get("path") or "").strip())
        if resource:
            humanized = _humanize_identifier(resource)
            return humanized if zh else humanized.lower()
    action_label = str(action.get("action") or "").strip()
    if action_label:
        lowered = action_label.lower()
        trimmed = action_label
        for prefix in _TRANSITION_ACTION_PREFIXES:
            if lowered.startswith(f"{prefix} "):
                trimmed = action_label[len(prefix) + 1 :].strip()
                break
        trimmed = trimmed.strip(" -:")
        if trimmed:
            if zh:
                return trimmed
            return trimmed[:1].lower() + trimmed[1:]
    return "当前对象" if zh else "record"


def _transition_kind_from_action(action: dict[str, Any], *, next_route: str) -> str:
    api_binding = action.get("api_binding", {})
    method = str(api_binding.get("method") or "").strip().upper() if isinstance(api_binding, dict) else ""
    label = str(action.get("action") or "").strip().lower()
    if not method and label.startswith("continue"):
        return "workflow"
    if method == "GET":
        return "load"
    if method == "DELETE":
        return "delete"
    if any(token in label for token in ("start", "launch", "resume", "run")):
        return "start"
    if any(token in label for token in ("create", "register", "book", "schedule", "issue", "generate")):
        return "create"
    if any(token in label for token in ("update", "save", "submit", "manage", "record", "confirm", "accept", "approve", "export")):
        return "update"
    if next_route and label.startswith("continue"):
        return "workflow"
    if method in {"POST", "PUT", "PATCH"}:
        return "update"
    return "load" if method else "workflow"


def _transition_states(kind: str, *, locale: str) -> tuple[str, str]:
    zh = is_zh_locale(locale)
    if zh:
        labels = {
            "load": ("未加载", "已可见"),
            "create": ("草稿", "已创建"),
            "update": ("当前状态", "已更新"),
            "start": ("待启动", "运行中"),
            "delete": ("已存在", "已移除"),
            "workflow": ("当前步骤", "下一步骤"),
        }
        return labels.get(kind, ("待处理", "已应用"))
    labels = {
        "load": ("not-loaded", "visible"),
        "create": ("draft", "created"),
        "update": ("current-state", "updated"),
        "start": ("ready", "running"),
        "delete": ("present", "removed"),
        "workflow": ("current-step", "next-step"),
    }
    return labels.get(kind, ("pending-action", "applied"))


def _transition_evidence_fields(action: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for binding in action.get("response_bindings", []):
        if not isinstance(binding, dict):
            continue
        source = str(binding.get("from") or "").strip()
        target = str(binding.get("to") or "").strip()
        if target:
            fields.append(target)
        elif source:
            fields.append(source)
    fields.extend(str(field).strip() for field in action.get("result_fields", []) if str(field).strip())
    if not fields:
        fields.extend(
            str(field).strip()
            for field in action.get("required_fields", [])
            if str(field).strip() and (str(field).strip().endswith("Id") or str(field).strip().lower() in {"status", "state"})
        )
    ordered: list[str] = []
    seen: set[str] = set()
    for field in fields:
        if field in seen:
            continue
        seen.add(field)
        ordered.append(field)
    return ordered[:5]


def _transition_ui_state_change(
    kind: str,
    *,
    domain_object: str,
    next_route: str,
    locale: str,
) -> str:
    route_hint = f" {next_route}" if next_route else ""
    if is_zh_locale(locale):
        if kind == "load":
            return f"把{domain_object}的当前数据、状态和下一步动作一起展示出来，而不是停留在空壳页面。"
        if kind == "create":
            return f"保留新建后的{domain_object}上下文，并让下一步工作流可以直接继续。"
        if kind == "start":
            return f"显示{domain_object}已启动后的运行状态，并把上下文继续带入后续步骤。"
        if kind == "update":
            return f"在当前页面直接反映{domain_object}更新后的业务状态，而不是只回显 transport 成功。"
        if kind == "delete":
            return f"让{domain_object}从当前工作面移除，并明确告知后续可执行动作。"
        if kind == "workflow":
            return f"把当前上下文继续带入下一步{route_hint or '工作流'}，不要退化成评审导览页。"
        return f"让{domain_object}在动作完成后体现为明确的业务状态变化。"
    if kind == "load":
        return f"Materialize the {domain_object} context with current data and next-step cues instead of an empty shell."
    if kind == "create":
        return f"Keep the created {domain_object} visible and let the next workflow step start from the saved context."
    if kind == "start":
        return f"Show the running {domain_object} state and carry the current context into the next workflow step."
    if kind == "update":
        return f"Reflect the updated {domain_object} state in place instead of only echoing transport-level success."
    if kind == "delete":
        return f"Remove the {domain_object} from the active workspace and make the follow-up action explicit."
    if kind == "workflow":
        return f"Carry the current workflow context into{route_hint or ' the next step'} without exposing reviewer-only navigation scaffolding."
    return f"Show a concrete business-state change for the {domain_object} after the action completes."


def _generic_transition_from_action(
    action: dict[str, Any],
    *,
    next_route: str,
    locale: str,
) -> dict[str, Any] | None:
    trigger_action = str(action.get("action") or "").strip()
    if not trigger_action:
        return None
    kind = _transition_kind_from_action(action, next_route=next_route)
    from_state, to_state = _transition_states(kind, locale=locale)
    domain_object = _transition_domain_object_from_action(action, locale=locale)
    return _transition_spec(
        domain_object=domain_object,
        from_state=from_state,
        to_state=to_state,
        trigger_action=trigger_action,
        ui_state_change=_transition_ui_state_change(
            kind,
            domain_object=domain_object,
            next_route=next_route,
            locale=locale,
        ),
        evidence_fields=_transition_evidence_fields(action),
    )


def _business_state_transitions(
    *,
    page_blueprint_type: str,
    actions: list[dict[str, Any]],
    next_route: str,
    locale: str,
) -> list[dict[str, Any]]:
    transitions = [
        transition
        for transition in (
            _generic_transition_from_action(action, next_route=next_route, locale=locale)
            for action in actions
            if isinstance(action, dict)
        )
        if transition
    ]
    if transitions:
        return transitions[:4]
    zh = is_zh_locale(locale)
    return [
        _transition_spec(
            domain_object="页面工作流" if zh else "page workflow",
            from_state="空闲" if zh else "idle",
            to_state="已推进" if zh else "advanced",
            trigger_action=_action_label_at(actions, 0, "推进工作流" if zh else "Advance workflow"),
            ui_state_change=(
                "显示有意义的业务状态变化，而不是只显示传输层响应。"
                if zh
                else "Show a meaningful business state change rather than only the transport response."
            ),
            evidence_fields=[],
        )
    ]


def _page_semantic_guardrails(
    *,
    page_blueprint_type: str,
    dominant_component_pattern: str,
    forbidden_layout_patterns: list[str],
    prototype_constraints: dict[str, str],
    locale: str,
) -> list[str]:
    zh = is_zh_locale(locale)
    base = [
        (
            "Do not render prototype metadata such as goals, purposes, or design notes as dominant on-screen copy."
            if not zh
            else "不要把目标、purpose、design notes 等原型元数据作为主屏文案直接渲染。"
        ),
        (
            f"Keep the page as a purpose-built {page_blueprint_type} surface with the component pattern '{dominant_component_pattern}'."
            if not zh
            else f"页面必须保持为面向业务的 {page_blueprint_type} 形态，并落实“{dominant_component_pattern}”这一组件模式。"
        ),
        (
            "Do not reduce the page to a generic API call form, raw JSON result panel, or contract viewer."
            if not zh
            else "不要把页面退化成通用 API 调用表单、原始 JSON 结果面板或合同查看器。"
        ),
        (
            "Reflect business-state transitions in the page structure after actions complete; HTTP loading/success alone is not enough."
            if not zh
            else "动作完成后必须在页面结构上体现业务状态流转；只有 HTTP loading/success 还不够。"
        ),
    ]
    if prototype_constraints.get("must_not_render_demo_console_or_api_explorer") == "yes":
        base.append(
            "API Explorer / demo-console framing is explicitly disallowed by the prototype contract."
            if not zh
            else "原型契约明确禁止 API Explorer / demo console 式主框架。"
        )
    if prototype_constraints.get("must_not_replace_page_intent_with_generic_workspace_labels") == "yes":
        base.append(
            "Do not replace the page intent with generic labels such as workspace, console, runtime, or acceptance dashboard."
            if not zh
            else "不要用 workspace、console、runtime、acceptance dashboard 之类的泛化标签替换页面意图。"
        )
    for item in forbidden_layout_patterns:
        normalized = str(item).strip()
        if normalized:
            base.append(normalized)
    return list(dict.fromkeys(base))


def _global_semantic_disqualifiers(
    *,
    prototype_constraints: dict[str, str],
    external_executor_brief: list[str],
    locale: str,
) -> list[str]:
    zh = is_zh_locale(locale)
    items = [
        (
            "Pages must not behave like configuration-driven API explorers or requirement-document viewers."
            if not zh
            else "页面不得表现为配置驱动的 API Explorer 或需求文档查看器。"
        ),
        (
            "Distinct business pages must not collapse into one shared generic renderer."
            if not zh
            else "不同业务页面不得塌缩为同一个共享通用渲染器。"
        ),
        (
            "Actions must cause meaningful UI state changes beyond transport-level success/error banners."
            if not zh
            else "用户动作必须触发有意义的 UI 业务状态变化，而不是停留在传输层 success/error 提示。"
        ),
    ]
    if prototype_constraints.get("must_present_as_business_product_not_demo_shell") == "yes":
        items.append(
            "The site must present as a business product, not a demo shell."
            if not zh
            else "站点必须呈现为业务产品，而不是 demo shell。"
        )
    if prototype_constraints.get("must_not_center_home_on_stepper_or_debug_cards") == "yes":
        items.append(
            "Home or landing routes must not be centered on stepper/debug-card framing."
            if not zh
            else "首页/首屏不能以 stepper 或 debug cards 作为主框架。"
        )
    items.extend(str(item).strip() for item in external_executor_brief if str(item).strip())
    return list(dict.fromkeys(items))


def _default_page_subtitle(surface: str, page_role: str, *, locale: str = "en") -> str:
    lowered = surface.lower()
    if "onboarding" in lowered or "setup" in lowered or "接入" in surface or "配置" in surface:
        if is_zh_locale(locale):
            return "在执行开始前确认范围详情和基线上下文。"
        return "Confirm the scope details and baseline context before execution begins."
    if "overview" in lowered or "findings" in lowered or "总览" in surface or "发现" in surface:
        if is_zh_locale(locale):
            return "查看当前信号图景、待处理发现以及需要关注的区域。"
        return "Review the current signal picture, outstanding findings, and the areas that need attention."
    if "recommendation" in lowered or "建议" in surface:
        if is_zh_locale(locale):
            return "查看建议详情、支撑信息以及下游执行所需的交接上下文。"
        return "Inspect the recommendation, supporting detail, and the handoff context for downstream execution."
    if "task" in lowered or "任务" in surface:
        if is_zh_locale(locale):
            return "保持执行轨迹最新，并让状态变化对后续流程清晰可见。"
        return "Keep the execution trail current and make state changes visible to the rest of the workflow."
    if "review" in lowered or "审核" in surface:
        if is_zh_locale(locale):
            return "汇总当前结果、记录操作人决策，并显式保留不确定性。"
        return "Summarize the outcome, record the operator decision, and keep uncertainty explicit."
    if page_role == "workspace":
        if is_zh_locale(locale):
            return "在一个页面中查看当前状态、关键信号和下一步操作。"
        return "See the current state, key signals, and the next action from one place."
    if page_role == "list":
        if is_zh_locale(locale):
            return "筛选当前工作集，并打开需要处理的条目。"
        return "Filter the current workload and open the item that needs action."
    if page_role == "detail":
        if is_zh_locale(locale):
            return "在继续之前查看当前记录、支撑证据以及相关上下文。"
        return "Inspect the current record, supporting evidence, and related context before moving on."
    if page_role == "workflow":
        if is_zh_locale(locale):
            return "在保留最新状态和操作意图的前提下推进工作流。"
        return "Move the workflow forward while preserving the latest state and operator intent."
    if is_zh_locale(locale):
        return "使用清晰的输入、反馈和下一步操作完成当前步骤。"
    return "Complete the current step with clear inputs, feedback, and a visible next action."


def _default_user_goal(surface: str, page_role: str, *, locale: str = "en") -> str:
    lowered = surface.lower()
    if "onboarding" in lowered or "setup" in lowered or "接入" in surface or "配置" in surface:
        if is_zh_locale(locale):
            return "采集激活后续观察与审核工作所需的范围信息。"
        return "Capture the scope information required to activate downstream observation and review work."
    if "overview" in lowered or "findings" in lowered or "总览" in surface or "发现" in surface:
        if is_zh_locale(locale):
            return "理解哪些内容发生了变化、哪些被阻塞，以及应优先处理哪些发现。"
        return "Understand what changed, what is blocked, and which findings should be handled first."
    if "recommendation" in lowered or "建议" in surface:
        if is_zh_locale(locale):
            return "查看建议详情，并在不丢失上下文的前提下准备任务交接。"
        return "Review the recommendation details and prepare a clean task handoff without losing context."
    if "task" in lowered or "任务" in surface:
        if is_zh_locale(locale):
            return "记录最新任务结果，并让工作流状态对下一位操作者保持同步。"
        return "Record the latest task outcome and keep the workflow state synchronized for the next operator."
    if "review" in lowered or "审核" in surface:
        if is_zh_locale(locale):
            return "记录继续或修订决策，并为下一轮审核保留足够上下文。"
        return "Record a continue-or-revise decision with enough context for the next review cycle."
    if page_role == "workspace":
        if is_zh_locale(locale):
            return "查看当前运行图景并选择下一步操作。"
        return "Review the current operating picture and choose the next action."
    if page_role == "list":
        if is_zh_locale(locale):
            return "快速找到正确条目，并带着足够上下文打开处理。"
        return "Find the right item quickly and open it with enough context to act."
    if page_role == "detail":
        if is_zh_locale(locale):
            return "查看当前记录并确认支撑细节后再变更状态。"
        return "Inspect the current record and confirm the supporting detail before changing status."
    if page_role == "workflow":
        if is_zh_locale(locale):
            return "以明确状态、操作意图和可见反馈推进工作流。"
        return "Move the workflow forward with explicit state, operator intent, and visible feedback."
    if is_zh_locale(locale):
        return "用必需的业务输入和清晰状态反馈完成当前工作流步骤。"
    return "Complete this workflow step with the required business inputs and visible status feedback."


def _default_primary_cta(surface: str, page_role: str, page_endpoints: list[dict[str, Any]], *, locale: str = "en") -> dict[str, str]:
    lowered = surface.lower()
    methods = {str(endpoint.get("method", "")).upper() for endpoint in page_endpoints}
    localized_surface = localize_surface_title(surface, locale)
    if "onboarding" in lowered or "setup" in lowered or "接入" in surface or "配置" in surface:
        if is_zh_locale(locale):
            return {
                "label": "加载范围配置",
                "hint": "拉取当前范围详情，让接入流程可以基于正确基线继续。",
            }
        return {
            "label": "Load scope setup",
            "hint": "Bring in the current scope details so onboarding can continue with the right baseline.",
        }
    if "overview" in lowered or "findings" in lowered or "总览" in surface or "发现" in surface:
        if is_zh_locale(locale):
            return {
                "label": "刷新总览与发现",
                "hint": "在选择下一步操作前更新当前发现视图。",
            }
        return {
            "label": "Refresh findings overview",
            "hint": "Update the current findings picture before choosing the next action.",
        }
    if "recommendation" in lowered or "建议" in surface:
        if is_zh_locale(locale):
            return {
                "label": "加载建议详情",
                "hint": "在导出或交接之前先打开当前建议上下文。",
            }
        return {
            "label": "Load recommendation detail",
            "hint": "Open the current recommendation context before exporting or handing off work.",
        }
    if "task" in lowered or "任务" in surface:
        if is_zh_locale(locale):
            return {
                "label": "提交任务更新",
                "hint": "保存最新执行状态，并确认下游工作流反馈。",
            }
        return {
            "label": "Submit task update",
            "hint": "Save the latest execution state and confirm the downstream workflow response.",
        }
    if "review" in lowered or "审核" in surface:
        if is_zh_locale(locale):
            return {
                "label": "提交审核决策",
                "hint": "记录操作人决策，并显式说明下一步审核动作。",
            }
        return {
            "label": "Submit review decision",
            "hint": "Record the operator decision and make the next review step explicit.",
        }
    if methods & {"POST", "PUT", "PATCH", "DELETE"} or page_role in {"form-flow", "workflow"}:
        if is_zh_locale(locale):
            return {
                "label": f"保存{localized_surface}",
                "hint": "提交当前业务输入，并让结果状态继续停留在本页可见。",
            }
        return {
            "label": f"Save {surface}",
            "hint": "Submit the current business inputs and keep the resulting state visible on this page.",
        }
    if is_zh_locale(locale):
        return {
            "label": f"打开{localized_surface}",
            "hint": "加载本页当前数据，并显式呈现下一步业务操作。",
        }
    return {
        "label": f"Open {surface}",
        "hint": "Load the current page data and make the next business action visible.",
    }


def _default_secondary_cta(surface: str, page_role: str, *, locale: str = "en") -> dict[str, str]:
    lowered = surface.lower()
    if "review" in lowered or "审核" in surface:
        if is_zh_locale(locale):
            return {"label": "返回发现列表", "kind": "navigation"}
        return {"label": "Return to findings", "kind": "navigation"}
    if "task" in lowered or "任务" in surface:
        if is_zh_locale(locale):
            return {"label": "刷新当前状态", "kind": "refresh"}
        return {"label": "Refresh current status", "kind": "refresh"}
    if page_role in {"workspace", "list", "detail"}:
        if is_zh_locale(locale):
            return {"label": "刷新当前数据", "kind": "refresh"}
        return {"label": "Refresh current data", "kind": "refresh"}
    if is_zh_locale(locale):
        return {"label": "继续编辑", "kind": "secondary"}
    return {"label": "Keep editing", "kind": "secondary"}


def _business_surface_label(surface: str, locale: str) -> str:
    label = localize_surface_title(surface, locale).strip()
    return label or _humanize_identifier(surface)



def _surface_section_title(surface: str, *, kind: str, locale: str) -> str:
    label = _business_surface_label(surface, locale)
    if is_zh_locale(locale):
        mapping = {
            "summary": f"{label}概览",
            "context": f"当前{label}",
            "selector": "查找当前记录",
            "form": f"{label}信息",
            "result": f"已保存的{label}",
            "status": "操作状态",
            "selection": "当前选中记录",
            "workload": "当前待办",
            "next": "下一步",
            "detail": f"{label}详情",
            "list": f"{label}列表",
        }
    else:
        mapping = {
            "summary": f"{label} overview",
            "context": f"Current {label}",
            "selector": "Find current record",
            "form": f"{label} details",
            "result": f"Saved {label}",
            "status": "Action status",
            "selection": "Current selection",
            "workload": "Active workload",
            "next": "Next step",
            "detail": f"{label} details",
            "list": f"{label} list",
        }
    return mapping.get(kind, label)



def _default_sections(
    surface: str,
    page_role: str,
    *,
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    locale: str = "en",
) -> list[dict[str, Any]]:
    summary_fields = display_fields[:4]
    decision_fields = [str(item.get("field") or "").strip() for item in user_inputs if str(item.get("field") or "").strip()]
    if page_role == "workspace":
        return [
            {
                "section_id": "summary",
                "title": _surface_section_title(surface, kind="summary", locale=locale),
                "purpose": "Show the live operating state and the most important context for this workspace.",
                "view": "summary-cards",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "highlights",
                "title": _surface_section_title(surface, kind="workload", locale=locale),
                "purpose": "Keep the current work queue visible so the operator can choose the next record quickly.",
                "view": "list",
                "bind_fields": display_fields[:6],
            },
            {
                "section_id": "next-step",
                "title": _surface_section_title(surface, kind="next", locale=locale),
                "purpose": "Make the immediate next step visible without reviewer-only guidance.",
                "view": "cta-panel",
                "bind_fields": [],
            },
        ]
    if page_role == "list":
        return [
            {
                "section_id": "filters",
                "title": _surface_section_title(surface, kind="selector", locale=locale),
                "purpose": "Narrow the current working set before opening a record.",
                "view": "filter-bar",
                "bind_fields": decision_fields,
            },
            {
                "section_id": "results",
                "title": _surface_section_title(surface, kind="list", locale=locale),
                "purpose": "Keep the current list view readable and scannable.",
                "view": "table",
                "bind_fields": display_fields[:6],
            },
            {
                "section_id": "selection",
                "title": _surface_section_title(surface, kind="selection", locale=locale),
                "purpose": "Keep the selected record visible while the operator decides what to do next.",
                "view": "detail",
                "bind_fields": summary_fields,
            },
        ]
    if page_role == "detail":
        return [
            {
                "section_id": "summary",
                "title": _surface_section_title(surface, kind="context", locale=locale),
                "purpose": "Surface the primary record details before the next handoff decision.",
                "view": "detail",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "supporting-detail",
                "title": _surface_section_title(surface, kind="detail", locale=locale),
                "purpose": "Keep supporting evidence and related records visible together.",
                "view": "detail-list",
                "bind_fields": display_fields[:8],
            },
            {
                "section_id": "handoff",
                "title": _surface_section_title(surface, kind="status", locale=locale),
                "purpose": "Show what is ready for the next action or handoff.",
                "view": "status-banner",
                "bind_fields": [],
            },
        ]
    if page_role == "workflow":
        return [
            {
                "section_id": "current-progress",
                "title": _surface_section_title(surface, kind="status", locale=locale),
                "purpose": "Show the latest workflow state for the current record.",
                "view": "status-banner",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "update-form",
                "title": _surface_section_title(surface, kind="form", locale=locale),
                "purpose": "Capture the inputs required to complete this business step.",
                "view": "form",
                "bind_fields": decision_fields,
            },
            {
                "section_id": "confirmation",
                "title": _surface_section_title(surface, kind="result", locale=locale),
                "purpose": "Show the saved result once the update is accepted.",
                "view": "result",
                "bind_fields": display_fields[:6],
            },
        ]
    if page_role == "review":
        return [
            {
                "section_id": "report-summary",
                "title": _surface_section_title(surface, kind="summary", locale=locale),
                "purpose": "Summarize the current review posture and supporting evidence.",
                "view": "summary-cards",
                "bind_fields": summary_fields,
            },
            {
                "section_id": "decision",
                "title": _surface_section_title(surface, kind="form", locale=locale),
                "purpose": "Capture the decision with enough context for the next cycle.",
                "view": "form",
                "bind_fields": decision_fields,
            },
            {
                "section_id": "follow-up",
                "title": _surface_section_title(surface, kind="next", locale=locale),
                "purpose": "Keep the immediate follow-up visible after submission.",
                "view": "next-steps",
                "bind_fields": [],
            },
        ]
    return [
        {
            "section_id": "context",
            "title": _surface_section_title(surface, kind="context", locale=locale),
            "purpose": "Give the operator the essential context before they change anything on this page.",
            "view": "detail",
            "bind_fields": summary_fields,
        },
        {
            "section_id": "work-area",
            "title": _surface_section_title(surface, kind="form", locale=locale),
            "purpose": "Capture the inputs required to complete this step.",
            "view": "form",
            "bind_fields": decision_fields,
        },
        {
            "section_id": "result",
            "title": _surface_section_title(surface, kind="result", locale=locale),
            "purpose": "Show the saved state after the action completes.",
            "view": "result",
            "bind_fields": display_fields[:6],
        },
    ]



def _merge_bind_fields(prioritized_fields: list[str], existing_fields: list[str]) -> list[str]:
    merged: list[str] = []
    for field in [*prioritized_fields, *existing_fields]:
        normalized = str(field).strip()
        if not normalized or normalized in {"tenantId", "tenant_id"} or normalized in merged:
            continue
        merged.append(normalized)
    return merged


def _selector_bind_fields(
    *,
    user_inputs: list[dict[str, Any]],
    selector_fields: list[str],
    filters_and_selectors: list[str],
) -> list[str]:
    input_fields = [str(item.get("field") or "").strip() for item in user_inputs if str(item.get("field") or "").strip()]
    candidates = _merge_bind_fields(selector_fields, input_fields)
    if not candidates:
        return []
    if not filters_and_selectors:
        return candidates[:1]
    return candidates[: max(1, min(len(filters_and_selectors), len(candidates)))]



def _augment_user_inputs_with_selector_fields(
    *,
    user_inputs: list[dict[str, Any]],
    selector_fields: list[str],
    actions: list[dict[str, Any]],
    locale: str,
    surface: str,
) -> list[dict[str, Any]]:
    if not selector_fields:
        return user_inputs
    existing_fields = {
        str(item.get("field") or "").strip()
        for item in user_inputs
        if isinstance(item, dict) and str(item.get("field") or "").strip()
    }
    required_fields = {
        str(field).strip()
        for action in actions
        if isinstance(action, dict)
        for field in action.get("required_fields", [])
        if str(field).strip()
    }
    selector_group = "记录查找" if is_zh_locale(locale) else "Record lookup"
    augmented = list(user_inputs)
    for field in selector_fields:
        normalized = str(field).strip()
        if not normalized or normalized in {"tenantId", "tenant_id"} or normalized in existing_fields:
            continue
        selector_datatype = _infer_field_datatype(normalized, _field_default_validation(normalized))
        selector_control = "lookup" if selector_datatype == "identifier" else ("select" if selector_datatype == "enum" else "text")
        augmented.append(
            _make_input_spec(
                normalized,
                locale=locale,
                required=normalized in required_fields,
                group=selector_group,
                surface=surface,
                value_source="workflow-context",
                editability="editable",
                datatype=selector_datatype,
                control=selector_control,
                lookup_entity=_lookup_entity_for_field(normalized) or None,
                options_source=(f"entity:{_lookup_entity_for_field(normalized)}" if selector_control == "lookup" and _lookup_entity_for_field(normalized) else None),
                display_format="lookup" if selector_control == "lookup" else "selector",
            )
        )
        existing_fields.add(normalized)
    return augmented

def _contract_driven_sections(
    *,
    surface: str,
    page_role: str,
    locale: str,
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    selector_fields: list[str],
    summary_cards: list[str],
    detail_fields_in_order: list[str],
    table_columns: list[str],
    filters_and_selectors: list[str],
    submission_feedback: list[str],
    required_status_messages: list[str],
) -> list[dict[str, Any]]:
    if not any([summary_cards, detail_fields_in_order, table_columns, filters_and_selectors, submission_feedback, required_status_messages]):
        return []
    sections = _default_sections(surface, page_role, display_fields=display_fields, user_inputs=user_inputs, locale=locale)
    selector_bind_fields = _selector_bind_fields(
        user_inputs=user_inputs,
        selector_fields=selector_fields,
        filters_and_selectors=filters_and_selectors,
    )
    has_view = {str(item.get("view") or "").strip().lower() for item in sections if isinstance(item, dict)}
    if filters_and_selectors and selector_bind_fields:
        for section in sections:
            if not isinstance(section, dict):
                continue
            if str(section.get("view") or "").strip().lower() == "filter-bar":
                section["bind_fields"] = _merge_bind_fields(
                    selector_bind_fields,
                    [str(item).strip() for item in section.get("bind_fields", []) if str(item).strip()],
                )
                break
        else:
            sections.insert(
                1 if sections else 0,
                {
                    "section_id": "filters",
                    "title": _surface_section_title(surface, kind="selector", locale=locale),
                    "purpose": "Choose the current record before acting in the main workspace.",
                    "view": "filter-bar",
                    "bind_fields": selector_bind_fields,
                },
            )
            has_view.add("filter-bar")
    if submission_feedback and "result" not in has_view:
        sections.append(
            {
                "section_id": "latest-result",
                "title": _surface_section_title(surface, kind="result", locale=locale),
                "purpose": "Keep the latest outcome visible after the action succeeds.",
                "view": "result",
                "bind_fields": display_fields[:6],
            }
        )
    if required_status_messages and "status-banner" not in has_view:
        sections.append(
            {
                "section_id": "state-honesty",
                "title": _surface_section_title(surface, kind="status", locale=locale),
                "purpose": "Keep loading, empty, error, and blocked states explicit.",
                "view": "status-banner",
                "bind_fields": display_fields[:4],
            }
        )
    return sections



def _contract_driven_presentation(
    *,
    summary_cards: list[str],
    detail_fields_in_order: list[str],
    table_columns: list[str],
    filters_and_selectors: list[str],
    required_status_messages: list[str],
    submission_feedback: list[str],
) -> list[str]:
    items: list[str] = []
    if summary_cards:
        items.append("summary-cards")
    if filters_and_selectors:
        items.append("filter-bar")
    if table_columns:
        items.append("table-or-list")
    if detail_fields_in_order:
        items.append("detail-panel")
    if submission_feedback:
        items.append("submission-result")
    if required_status_messages:
        items.append("status-banner")
    return list(dict.fromkeys(items))


def _default_empty_state(surface: str, page_role: str, *, locale: str = "en") -> dict[str, str]:
    localized_surface = localize_surface_title(surface, locale)
    if page_role in {"workspace", "list"}:
        if is_zh_locale(locale):
            return {
                "headline": f"暂无{localized_surface}数据",
                "body": "完成第一次成功执行后，这个页面应显示当前工作集以及下一条待查看项。",
            }
        return {
            "headline": f"No {surface.lower()} data yet",
            "body": "Once the first successful run completes, this page should show the working set and the next item to inspect.",
        }
    if is_zh_locale(locale):
        return {
            "headline": "当前还没有可展示的数据",
            "body": "完成必需输入或加载当前记录后，这个页面才会被填充。",
        }
    return {
        "headline": "Nothing is ready to show yet",
        "body": "Complete the required inputs or load the current record to populate this page.",
    }


def _default_success_state(surface: str, page_role: str, *, locale: str = "en") -> dict[str, str]:
    return surface_success_copy(surface, page_role, locale)


def _default_error_state(page_role: str, *, locale: str = "en") -> dict[str, str]:
    if page_role in {"form-flow", "workflow", "review"}:
        if is_zh_locale(locale):
            return {
                "headline": "无法保存当前变更",
                "body": "保留当前输入，清楚说明失败原因，并展示安全重试方式。",
            }
        return {
            "headline": "We could not save your change",
            "body": "Keep the current inputs visible, explain the failure clearly, and show how to retry safely.",
        }
    if is_zh_locale(locale):
        return {
            "headline": "无法加载当前视图",
            "body": "保持页面结构可见，明确说明缺口原因，并允许操作者无损重试。",
        }
    return {
        "headline": "We could not load the current view",
        "body": "Keep the page structure visible, explain the gap clearly, and let the operator retry without losing context.",
    }


def _default_acceptance_checks(
    surface: str,
    *,
    page_role: str,
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    next_route: str | None,
    locale: str = "en",
) -> list[str]:
    localized_surface = localize_surface_title(surface, locale)
    if is_zh_locale(locale):
        checks = [
            f"页面需要渲染 `{localized_surface}` 的标题、副标题和用户目标。",
            f"页面需要为 `{page_role}` 交互模式保留清晰可见的工作区。",
        ]
        if display_fields:
            checks.append("页面需要展示这些关键数据字段：" + "、".join(display_fields[:6]) + "。")
        if user_inputs:
            checks.append(
                "页面需要允许用户输入：" + "、".join(str(item.get("field") or "").strip() for item in user_inputs[:6] if str(item.get("field") or "").strip()) + "。"
            )
        if next_route:
            checks.append(f"成功后需要显式给出下一步导航，并指向 `{next_route}`。")
        return checks
    checks = [
        f"Render a page-level title, subtitle, and goal for `{surface}`.",
        f"Keep a visible work area for the `{page_role}` interaction pattern.",
    ]
    if display_fields:
        checks.append(f"Render the required data fields: {', '.join(display_fields[:6])}.")
    if user_inputs:
        checks.append(
            "Allow the operator to enter: " + ", ".join(str(item.get("field") or "").strip() for item in user_inputs[:6] if str(item.get("field") or "").strip()) + "."
        )
    if next_route:
        checks.append(f"Keep the next navigation step explicit by linking to `{next_route}` after success.")
    return checks


def _surface_title_tokens(surface: str) -> list[str]:
    raw_tokens = [token.lower() for token in re.split(r"[^a-zA-Z0-9]+", surface) if token.strip()]
    tokens: list[str] = []
    for token in raw_tokens:
        if len(token) < 3:
            continue
        tokens.append(token)
        if token.endswith("ies") and len(token) > 4:
            tokens.append(token[:-3] + "y")
        elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
            tokens.append(token[:-1])
    return list(dict.fromkeys(tokens))


def _default_presentation(surface: str, page_endpoints: list[dict[str, Any]]) -> list[str]:
    lowered = surface.lower()
    if "overview" in lowered or "dashboard" in lowered:
        return ["summary-cards", "trend-list", "alert-panel"]
    if "list" in lowered or "catalog" in lowered or "queue" in lowered:
        return ["search-filter-bar", "table-or-list", "pagination-controls"]
    if "detail" in lowered:
        return ["entity-summary", "timeline", "state-badges"]
    methods = {str(endpoint.get("method", "")).upper() for endpoint in page_endpoints}
    if methods & {"POST", "PUT", "PATCH", "DELETE"}:
        return ["form-layout", "validation-inline", "submission-result"]
    if methods == {"GET"} or "view" in lowered:
        return ["table-or-list", "detail-panel", "status-banner"]
    return ["table-or-list", "detail-panel", "status-banner"]


def _validation_hint(example_value: Any, field_name: str) -> str:
    if isinstance(example_value, bool):
        return "boolean"
    if isinstance(example_value, int) and not isinstance(example_value, bool):
        return "integer"
    if isinstance(example_value, float):
        return "number"
    if isinstance(example_value, list):
        return "list"
    if isinstance(example_value, dict):
        return "json object"
    inferred = _infer_field_datatype(field_name)
    if inferred == "identifier":
        return "identifier"
    if inferred == "integer":
        return "integer"
    if inferred == "number":
        return "number"
    if inferred in {"date", "datetime"}:
        return inferred
    return "text"


def _request_example_fields(page_endpoints: list[dict[str, Any]], *, method_filter: set[str]) -> list[tuple[str, Any]]:
    fields: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for endpoint in page_endpoints:
        if str(endpoint.get("method", "")).upper() not in method_filter:
            continue
        request_example = endpoint.get("request_example", {})
        if not isinstance(request_example, dict):
            continue
        for key, value in request_example.items():
            if not str(key).strip() or str(key).strip() in seen:
                continue
            seen.add(str(key).strip())
            fields.append((str(key).strip(), value))
    return fields


def _surface_operation_sequence(surface: str) -> list[str]:
    lowered = surface.lower()
    if "onboarding" in lowered or "setup" in lowered or "接入" in surface or "范围" in surface or "配置" in surface:
        return [
            "GetTenantAccessPolicy",
            "CreateTrackedScope",
            "GetAttributionSeamReference",
            "StartObservationRun",
        ]
    if "overview" in lowered or "findings" in lowered or "总览" in surface or "发现" in surface:
        return [
            "ListVisibilityFindings",
            "ListOptimizationTasks",
            "GetCompetitorSnapshot",
            "ListAuditTrail",
        ]
    if "recommendation" in lowered or "导出" in surface or "建议" in surface:
        return [
            "GetFindingDetail",
            "GetContentAssetCatalog",
            "CreateRecommendationDecision",
            "CreateOptimizationTask",
        ]
    if "task" in lowered or "任务" in surface:
        return [
            "ListOptimizationTasks",
            "UpdateOptimizationTaskStatus",
            "ListAuditTrail",
        ]
    if "review" in lowered or "审核" in surface or "continue" in lowered or "revise" in lowered:
        return [
            "GenerateReviewReport",
            "ListAuditTrail",
        ]
    return []


def _action_label_for_endpoint(endpoint: dict[str, Any], *, locale: str = "en") -> str:
    operation_id = str(endpoint.get("operation_id") or "").strip()
    labels = {
        "CreateTrackedScope": ("Create tracked scope", "创建跟踪范围"),
        "GetTenantAccessPolicy": ("Confirm working tenant", "确认工作租户"),
        "StartObservationRun": ("Start observation run", "启动观测运行"),
        "CompleteObservationRun": ("Complete observation run", "完成观测运行"),
        "GetCompetitorSnapshot": ("Load competitor snapshot", "加载竞品快照"),
        "CreateRecommendationDecision": ("Create recommendation decision", "生成建议决策"),
        "CreateOptimizationTask": ("Create optimization task", "导出优化任务"),
        "GetContentAssetCatalog": ("Load content asset catalog", "加载内容资产目录"),
        "GenerateReviewReport": ("Generate review report", "生成审核报告"),
        "ListAuditTrail": ("Load audit trail", "加载审计轨迹"),
        "ListVisibilityFindings": ("Load visibility findings", "加载发现列表"),
        "GetFindingDetail": ("Load finding detail", "加载发现详情"),
        "UpdateOptimizationTaskStatus": ("Update task status", "更新任务状态"),
        "ListOptimizationTasks": ("Load optimization tasks", "加载任务列表"),
        "GetAttributionSeamReference": ("Review scope boundary", "查看范围边界"),
    }
    if operation_id in labels:
        return labels[operation_id][1 if is_zh_locale(locale) else 0]
    method = str(endpoint.get("method", "")).upper()
    purpose = str(endpoint.get("purpose", "")).strip() or str(endpoint.get("path", "")).strip() or operation_id
    if is_zh_locale(locale):
        prefix = {
            "GET": "加载",
            "POST": "提交",
            "PATCH": "更新",
            "PUT": "保存",
            "DELETE": "删除",
        }.get(method, "执行")
        return f"{prefix}{purpose}"
    prefix = {
        "GET": "Load",
        "POST": "Submit",
        "PATCH": "Update",
        "PUT": "Save",
        "DELETE": "Delete",
    }.get(method, "Run")
    return f"{prefix} {purpose}"


def _default_user_inputs(surface: str, page_endpoints: list[dict[str, Any]], *, locale: str = "en") -> list[dict[str, Any]]:
    def make_input(field: str, *, required: bool, validation: str) -> dict[str, Any]:
        helper = {
            "path parameter": "Needed to load the exact record or workflow step for this page.",
            "identifier": "Use the stable business identifier expected by this workflow step.",
            "boolean": "Choose whether this condition should be enabled for the current action.",
            "json object": "Paste structured values only when the upstream contract requires them.",
            "list": "Provide a comma-separated or structured list when multiple values are expected.",
        }.get(validation, "")
        if is_zh_locale(locale):
            helper = {
                "path parameter": "用于加载当前页面所需的准确记录或流程步骤。",
                "identifier": "请使用该步骤要求的稳定业务标识符。",
                "boolean": "请选择该条件在当前操作中是否开启。",
                "json object": "仅在上游契约明确要求时粘贴结构化值。",
                "list": "当需要多个值时，请提供逗号分隔列表或结构化列表。",
            }.get(validation, "")
        return {
            **_make_input_spec(field, locale=locale, required=required, validation=validation, surface=surface),
            **({"helper": helper} if helper else {}),
        }

    path_params: list[str] = []
    for endpoint in page_endpoints:
        for match in re.findall(r"\{([^}]+)\}", str(endpoint.get("path", ""))):
            normalized = re.sub(r"[^A-Za-z0-9_]+", "_", str(match)).strip("_")
            if normalized and normalized not in path_params:
                path_params.append(normalized)

    methods = {str(endpoint.get("method", "")).upper() for endpoint in page_endpoints}
    inputs: list[dict[str, Any]] = [
        make_input(field, required=True, validation="path parameter") for field in path_params
    ]
    request_fields = _request_example_fields(page_endpoints, method_filter={"POST", "PUT", "PATCH", "DELETE"})
    if methods & {"POST", "PUT", "PATCH", "DELETE"} and request_fields:
        for field_name, example_value in request_fields:
            if field_name in path_params:
                continue
            inputs.append(make_input(
                field_name,
                required=example_value not in (None, "", [], {}),
                validation=_validation_hint(example_value, field_name),
            ))
        return inputs
    if methods & {"POST", "PUT", "PATCH", "DELETE"}:
        inputs.extend(
            [
                make_input("primary_input", required=True, validation="non-empty text or identifier"),
                make_input("secondary_input", required=False, validation="optional free text"),
            ]
        )
        return inputs
    query_fields = _request_example_fields(page_endpoints, method_filter={"GET", "DELETE"})
    if query_fields:
        for field_name, example_value in query_fields:
            if field_name in path_params:
                continue
            inputs.append(make_input(
                field_name,
                required=False,
                validation=_validation_hint(example_value, field_name),
            ))
        return inputs
    title_tokens = _surface_title_tokens(surface)
    if "search" in title_tokens or "list" in title_tokens or "catalog" in title_tokens:
        inputs.extend(
            [
                make_input("query", required=False, validation="text"),
                make_input("filter", required=False, validation="enum/text"),
            ]
        )
        return inputs
    inputs.extend(
        [
            make_input("query", required=False, validation="text"),
            make_input("context_id", required=False, validation="identifier"),
        ]
    )
    return inputs


def _unwrap_response_data(response_example: Any) -> Any:
    if isinstance(response_example, dict) and "data" in response_example:
        return response_example.get("data")
    return response_example


def _display_fields_from_response(response_example: Any) -> list[str]:
    data = _unwrap_response_data(response_example)
    if isinstance(data, list):
        if not data or not isinstance(data[0], dict):
            return []
        keys = [str(key).strip() for key in data[0].keys() if str(key).strip()]
    elif isinstance(data, dict):
        keys = [str(key).strip() for key in data.keys() if str(key).strip()]
    else:
        return []
    preferred_prefixes = ("id", "name", "title", "status", "type", "score", "version", "updated", "created")
    preferred: list[str] = []
    remaining: list[str] = []
    for key in keys:
        lowered = key.lower()
        if lowered.endswith("_id") or lowered.endswith("id") or any(lowered.startswith(prefix) for prefix in preferred_prefixes):
            preferred.append(key)
        else:
            remaining.append(key)
    ordered = preferred + remaining
    deduped: list[str] = []
    seen: set[str] = set()
    for key in ordered:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped[:8]


def _default_display_fields(page_endpoints: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()
    for endpoint in page_endpoints:
        for key in _display_fields_from_response(endpoint.get("response_example", {})):
            if key in seen:
                continue
            seen.add(key)
            fields.append(key)
    return fields[:8]


def _default_state_conditions(surface: str, page_endpoints: list[dict[str, Any]], *, locale: str = "en") -> dict[str, str]:
    methods = {str(endpoint.get("method", "")).upper() for endpoint in page_endpoints}
    if methods & {"POST", "PUT", "PATCH", "DELETE"}:
        if is_zh_locale(locale):
            return {
                "loading": "正在加载前置上下文和待提交状态",
                "success": "操作已被接受，刷新后的状态已在页面可见",
                "empty": "该页面尚不存在历史上下文或记录",
                "error": "校验、策略或上游错误已以内联方式展示，并提供重试指引",
            }
        return {
            "loading": "load prerequisite context and pending submission state",
            "success": "operation accepted and refreshed state visible on the page",
            "empty": "no prior context or records exist yet for this surface",
            "error": "validation, policy, or upstream errors are shown inline with retry guidance",
        }
    lowered = surface.lower()
    if "detail" in lowered or "view" in lowered or "详情" in surface:
        if is_zh_locale(locale):
            return {
                "loading": "详情数据查询进行中",
                "success": "所选记录及其相关状态已可见",
                "empty": "请求的记录或支撑上下文不存在",
                "error": "详情加载失败，但重试路径仍保持可见",
            }
        return {
            "loading": "detail data query in progress",
            "success": "selected record and related state are visible",
            "empty": "requested record or supporting context is absent",
            "error": "detail load failed and the retry path stays visible",
        }
    if is_zh_locale(locale):
        return {
            "loading": "页面数据查询进行中",
            "success": "主要数据已加载并渲染",
            "empty": "查询未返回任何记录",
            "error": "请求失败，可重新尝试",
        }
    return {
        "loading": "page data query in progress",
        "success": "primary data loaded and rendered",
        "empty": "query returned no records",
        "error": "request failed and retry is available",
    }


def _field_source_mapping(
    *,
    data_required: list[dict[str, Any]],
    user_inputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    semantic_keys = (
        "value_source",
        "editability",
        "datatype",
        "control",
        "options",
        "options_source",
        "system_generated",
        "server_assigned",
        "lookup_entity",
        "display_format",
        "internal_exposure",
    )
    for item in user_inputs:
        field = str(item.get("field", "")).strip()
        if not field:
            continue
        source_ref = ""
        if data_required:
            first = data_required[0]
            source_ref = f"{first.get('method', '')} {first.get('path', '')}".strip()
        mapping: dict[str, Any] = {
            "field": field,
            "source": str(item.get("source") or "user-input").strip() or "user-input",
            "bind_to": source_ref or "api-contract-to-be-finalized",
        }
        for semantic_key in semantic_keys:
            if semantic_key in item:
                mapping[semantic_key] = item.get(semantic_key)
        mappings.append(mapping)
    return mappings


def _interaction_action_label(interaction: dict[str, str], *, locale: str) -> str:
    intent = str(interaction.get("user_intent") or "").strip()
    if intent:
        return intent
    action_type = str(interaction.get("action_type") or "").strip().replace("_", " ")
    if action_type:
        return action_type
    return "执行交互" if is_zh_locale(locale) else "Run interaction"


def _compiled_sections_from_regions(
    *,
    required_regions: list[str],
    display_fields: list[str],
    user_inputs: list[dict[str, Any]],
    locale: str,
) -> list[dict[str, Any]]:
    view_map = {
        "context_header": ("summary-cards", "Current context", "当前上下文"),
        "data_view": ("table-or-list", "Primary data view", "主数据视图"),
        "work_area": ("form", "Work area", "工作区"),
        "status_feedback": ("status-banner", "State and guidance", "状态与提示"),
        "next_steps": ("next-steps", "Next steps", "下一步"),
        "audit_strip": ("audit-strip", "Audit evidence", "审计证据"),
    }
    input_fields = [str(item.get("field") or "").strip() for item in user_inputs if str(item.get("field") or "").strip()]
    sections: list[dict[str, Any]] = []
    for region in required_regions:
        normalized = str(region).strip()
        if not normalized:
            continue
        view, en_title, zh_title = view_map.get(normalized, ("detail", normalized.replace("_", " ").title(), normalized))
        bind_fields = input_fields if normalized == "work_area" and input_fields else display_fields[:6]
        sections.append(
            {
                "section_id": normalized,
                "title": zh_title if is_zh_locale(locale) else en_title,
                "purpose": (
                    f"Compiled from required region `{normalized}` so this workflow area stays explicit."
                    if not is_zh_locale(locale)
                    else f"根据必需区域 `{normalized}` 编译，确保该工作区域保持显式。"
                ),
                "view": view,
                "bind_fields": bind_fields,
            }
        )
    return sections


def _compile_surface_contract_artifacts(
    *,
    prototype_spec_text: str,
    interaction_flow_contract_text: str,
    stage_03_text: str,
    esp_text: str,
    locale: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    surface_rows = _extract_surface_matrix_rows_from_prototype_spec(prototype_spec_text)
    prototype_page_contracts = _extract_prototype_page_contracts(prototype_spec_text)
    main_flow_goals = _extract_main_flow_goals_from_prototype_spec(prototype_spec_text)
    prototype_contract_by_name = {
        str(contract.get("page_name") or "").strip(): contract
        for contract in prototype_page_contracts
        if str(contract.get("page_name") or "").strip()
    }
    prototype_constraints = _extract_prototype_generation_constraints(prototype_spec_text)
    interaction_rows = _extract_interaction_matrix_rows(interaction_flow_contract_text)
    flow_rows = _extract_flow_contract_rows(interaction_flow_contract_text)
    source_text = stage_03_text or esp_text
    enrichment_rows = _extract_interaction_enrichment_rows(source_text)
    binding_rows = _extract_binding_matrix_rows(source_text)
    if not surface_rows or not interaction_rows or not enrichment_rows or not binding_rows:
        return [], []

    enrichment_by_interaction = {
        str(row.get("interaction_id") or "").strip(): row
        for row in enrichment_rows
        if str(row.get("interaction_id") or "").strip()
    }
    binding_by_interaction = {
        str(row.get("interaction_id") or "").strip(): row
        for row in binding_rows
        if str(row.get("interaction_id") or "").strip()
    }
    flows_by_interaction: dict[str, list[dict[str, str]]] = {}
    for row in flow_rows:
        interaction_id = str(row.get("from_interaction_id") or "").strip()
        if interaction_id:
            flows_by_interaction.setdefault(interaction_id, []).append(row)
    route_to_page_id = {
        _compiled_scalar(row.get("route")): str(row.get("page_id") or "").strip()
        for row in surface_rows
        if _compiled_scalar(row.get("route")) and str(row.get("page_id") or "").strip()
    }

    compiled_pages: list[dict[str, Any]] = []
    compiled_bindings: list[dict[str, Any]] = []
    for index, surface in enumerate(surface_rows):
        page_id = str(surface.get("page_id") or "").strip() or f"P{index + 1:02d}"
        page_name = str(surface.get("page_name") or "").strip()
        page_route = str(surface.get("route") or f"/{_business_slug(page_name)}").strip()
        prototype_page_contract = prototype_contract_by_name.get(page_name, {})
        surface_page_role = (
            str(prototype_page_contract.get("page_role") or "").strip()
            or str(surface.get("page_role") or "").strip()
            or _infer_page_role(page_name, [], page_index=index)
        )
        page_blueprint_type = (
            _normalize_blueprint_type(surface.get("page_blueprint_type"), preserve_unknown=True)
            or _normalize_blueprint_type(prototype_page_contract.get("page_blueprint_type"), preserve_unknown=True)
            or _infer_page_blueprint_type(page_name, surface_page_role, prototype_page_contract)
        )
        page_role = _semantic_page_role(surface_page_role, page_blueprint_type)
        allowed_roles = [
            normalize_role_display_name(str(item).strip(), locale)
            for item in surface.get("allowed_roles", [])
            if normalize_role_display_name(str(item).strip(), locale)
        ]
        surface_contract_v2, surface_contract_alerts = _resolve_surface_contract_v2(
            surface=surface,
            page_name=page_name,
            page_id=page_id,
            page_blueprint_type=page_blueprint_type,
            allowed_roles=allowed_roles,
            locale=locale,
        )
        business_objects = [str(item).strip() for item in surface.get("business_objects", []) if str(item).strip()]
        display_title = normalize_surface_display_title(page_name, locale, page_role=page_role, business_objects=business_objects)
        required_regions = [str(item).strip() for item in surface.get("required_regions", []) if str(item).strip()]
        next_route_candidates = [str(item).strip() for item in surface.get("next_route_candidates", []) if str(item).strip()]
        page_readiness_status = str(surface.get("readiness_status") or "").strip() or "ready"
        page_blocked_reason = str(surface.get("blocked_reason") or "").strip()
        page_interactions = [row for row in interaction_rows if str(row.get("page_id") or "").strip() == page_id]
        compiled_interactions: list[dict[str, Any]] = []
        page_actions: list[dict[str, Any]] = []
        page_data_required: list[dict[str, Any]] = []
        page_display_fields: list[str] = []
        page_submission_feedback: list[str] = []
        page_status_messages: list[str] = []
        page_context_fields: set[str] = set()

        for interaction in page_interactions:
            interaction_id = str(interaction.get("interaction_id") or "").strip()
            enrichment = enrichment_by_interaction.get(interaction_id, {})
            binding = binding_by_interaction.get(interaction_id, {})
            flow = (flows_by_interaction.get(interaction_id) or [{}])[0]
            trigger_kind = str(interaction.get("trigger_kind") or "").strip()
            display_field_set = _split_compiled_values(enrichment.get("display_field_set", ""))
            for field in display_field_set:
                if field not in page_display_fields:
                    page_display_fields.append(field)

            value_source_by_field = _parse_field_enum_map(
                enrichment.get("value_source", ""),
                normalizer=_normalize_value_source,
            )
            internal_exposure_by_field = _parse_field_enum_map(
                enrichment.get("internal_exposure", ""),
                normalizer=_normalize_internal_exposure,
            )
            interaction_internal_exposure = _normalize_internal_exposure(enrichment.get("internal_exposure"))
            if not interaction_internal_exposure:
                interaction_internal_exposure = "review_only" if surface_contract_v2["audience_mode"] != "app" else "user_visible"
            server_generated_fields = _split_compiled_values(binding.get("server_generated_fields", ""))
            server_generated_field_set = {str(item).strip() for item in server_generated_fields if str(item).strip()}
            ui_refresh_targets = _split_compiled_values(binding.get("ui_refresh_targets", ""))
            handoff_materialization = _normalize_handoff_materialization(binding.get("handoff_materialization"))
            if not handoff_materialization:
                handoff_materialization = _normalize_handoff_materialization(surface_contract_v2.get("handoff_visibility"))
            if not handoff_materialization and any(
                str(item.get("next_page_id") or item.get("visible_next_page_id") or "").strip()
                for item in (flow,)
            ):
                handoff_materialization = "implicit_context" if surface_contract_v2["audience_mode"] == "app" else "review_only"
            input_fields = _mapping_field_names(str(binding.get("request_field_mapping", "")))
            response_fields = _mapping_field_names(str(binding.get("response_field_mapping", "")), right_hand=True) or display_field_set
            if trigger_kind == "page_load":
                page_context_fields.update(input_fields)
            bind_to = f"{binding.get('http_method', '')} {binding.get('api_endpoint', '')}".strip()
            required_input_sources: list[dict[str, Any]] = []
            for field in input_fields:
                normalized_field = str(field).strip()
                explicit_value_source = value_source_by_field.get(normalized_field, "")
                source = _input_source_from_value_source(explicit_value_source) if explicit_value_source else "user-input"
                if not explicit_value_source:
                    if trigger_kind == "page_load" or normalized_field in page_context_fields:
                        source = "workflow-context"
                    elif normalized_field in {"tenantId", "tenant_id"}:
                        source = "auth-session"
                effective_value_source = explicit_value_source
                if not effective_value_source and normalized_field in server_generated_field_set:
                    effective_value_source = "system-generated"
                if not effective_value_source:
                    effective_value_source = source
                source_entry: dict[str, Any] = {
                    "field": normalized_field,
                    "source": source,
                    "bind_to": bind_to or "api-contract-to-be-finalized",
                }
                source_entry.update(
                    _field_semantics(
                        normalized_field,
                        locale=locale,
                        validation=_field_default_validation(normalized_field),
                        source=effective_value_source,
                        bind_to=bind_to,
                    )
                )
                field_internal_exposure = internal_exposure_by_field.get(normalized_field, interaction_internal_exposure)
                if field_internal_exposure:
                    source_entry["internal_exposure"] = field_internal_exposure
                required_input_sources.append(source_entry)
            response_bindings = [{"from": field, "to": field} for field in response_fields]
            if bind_to:
                data_required_entry = {
                    "source": "api",
                    "method": str(binding.get("http_method") or "").strip(),
                    "path": str(binding.get("api_endpoint") or "").strip(),
                    "purpose": str(interaction.get("user_intent") or interaction.get("action_type") or "").strip(),
                    "interaction_id": interaction_id,
                    "service_binding_id": str(binding.get("service_binding_id") or "").strip(),
                    "domain_service": str(binding.get("domain_service") or "").strip(),
                    "binding_mode": str(binding.get("binding_mode") or "").strip(),
                    "trigger_kind": trigger_kind,
                }
                if data_required_entry not in page_data_required:
                    page_data_required.append(data_required_entry)
            next_route = _compiled_scalar(interaction.get("next_route"))
            flow_next_page_id = _compiled_scalar(flow.get("next_page_id"))
            resolved_next_page_id = flow_next_page_id
            route_target_page_id = route_to_page_id.get(next_route, "")
            if route_target_page_id:
                resolved_next_page_id = route_target_page_id
            failure_route = _compiled_scalar(flow.get("failure_route"))
            blocked_reason = str(binding.get("blocked_reason") or enrichment.get("blocked_reason") or interaction.get("blocked_reason") or "").strip()
            if blocked_reason and blocked_reason not in {"—", "-", "none", "n/a"}:
                page_status_messages.append(f"blocked: {blocked_reason}")
            action_entry = {
                "interaction_id": interaction_id,
                "service_binding_id": str(binding.get("service_binding_id") or "").strip(),
                "flow_id": str(flow.get("flow_id") or "").strip(),
                "trigger_kind": trigger_kind,
                "binding_mode": str(binding.get("binding_mode") or "").strip(),
                "readiness_status": str(binding.get("readiness_status") or enrichment.get("readiness_status") or interaction.get("readiness_status") or "").strip(),
                "blocked_reason": blocked_reason,
                "action": _compact_action_label(
                    _interaction_action_label(interaction, locale=locale),
                    locale=locale,
                    action_type=str(interaction.get("action_type") or "").strip(),
                    page_title=display_title,
                    page_role=page_role,
                    business_objects=business_objects,
                    allowed_roles=allowed_roles,
                ),
                "action_type": str(interaction.get("action_type") or "").strip(),
                "required_fields": input_fields,
                "required_input_sources": required_input_sources,
                "response_bindings": response_bindings,
                "server_generated_fields": server_generated_fields,
                "ui_refresh_targets": ui_refresh_targets,
                "handoff_materialization": handoff_materialization,
                "internal_exposure": interaction_internal_exposure,
                "actor_role": normalize_role_display_name(str(flow.get("actor_role") or "").strip(), locale),
                "consumer_role": normalize_role_display_name(str(flow.get("consumer_role") or "").strip(), locale),
                "visible_next_page_id": str(flow.get("visible_next_page_id") or "").strip(),
                "completion_signal": str(flow.get("completion_signal") or "").strip(),
                "handoff_surface_type": str(flow.get("handoff_surface_type") or "").strip(),
                "next_role_entry_mode": str(flow.get("next_role_entry_mode") or "").strip(),
                "on_success": normalize_inline_locale_variants(str(interaction.get("success_state") or "").strip(), locale),
                "on_error": normalize_inline_locale_variants(str(interaction.get("error_state") or "").strip(), locale),
                "next_route": next_route,
                "api_binding": {
                    "method": str(binding.get("http_method") or "").strip(),
                    "path": str(binding.get("api_endpoint") or "").strip(),
                },
            }
            if trigger_kind != "page_load":
                page_actions.append(action_entry)
                if action_entry["on_success"]:
                    page_submission_feedback.append(action_entry["on_success"])

            compiled_interactions.append(
                {
                    "interaction_id": interaction_id,
                    "region": str(interaction.get("region") or "").strip(),
                    "element_type": str(interaction.get("element_type") or "").strip(),
                    "interaction_pattern": str(interaction.get("interaction_pattern") or "").strip(),
                    "trigger_kind": trigger_kind,
                    "action_type": str(interaction.get("action_type") or "").strip(),
                    "input_schema_ref": str(enrichment.get("input_schema_ref") or "").strip(),
                    "display_field_set": display_field_set,
                    "validation_rules": str(enrichment.get("validation_rules") or "").strip(),
                    "value_source_map": value_source_by_field,
                    "internal_exposure": interaction_internal_exposure,
                    "visibility_rule": str(interaction.get("visibility_rule") or "").strip(),
                    "enabled_rule": str(enrichment.get("enabled_rule") or "").strip(),
                    "success_state": normalize_inline_locale_variants(str(interaction.get("success_state") or "").strip(), locale),
                    "error_state": normalize_inline_locale_variants(str(interaction.get("error_state") or "").strip(), locale),
                    "blocked_rule": str(interaction.get("blocked_rule") or "").strip(),
                    "next_route": next_route,
                    "flow_id": str(flow.get("flow_id") or "").strip(),
                    "step_id": str(flow.get("step_id") or "").strip(),
                    "transition_condition": str(flow.get("transition_condition") or "").strip(),
                    "next_page_id": resolved_next_page_id,
                    "visible_next_page_id": str(flow.get("visible_next_page_id") or "").strip(),
                    "handoff_context_fields": _split_compiled_values(flow.get("handoff_context_fields", "")),
                    "completion_signal": str(flow.get("completion_signal") or "").strip(),
                    "actor_role": normalize_role_display_name(str(flow.get("actor_role") or "").strip(), locale),
                    "consumer_role": normalize_role_display_name(str(flow.get("consumer_role") or "").strip(), locale),
                    "handoff_surface_type": str(flow.get("handoff_surface_type") or "").strip(),
                    "next_role_entry_mode": str(flow.get("next_role_entry_mode") or "").strip(),
                    "handoff_materialization": handoff_materialization,
                    "failure_route": failure_route,
                    "termination_condition": str(flow.get("termination_condition") or "").strip(),
                    "service_binding_id": str(binding.get("service_binding_id") or "").strip(),
                    "binding_mode": str(binding.get("binding_mode") or "").strip(),
                    "domain_service": str(binding.get("domain_service") or "").strip(),
                    "api_endpoint": str(binding.get("api_endpoint") or "").strip(),
                    "http_method": str(binding.get("http_method") or "").strip(),
                    "request_field_mapping": str(binding.get("request_field_mapping") or "").strip(),
                    "response_field_mapping": str(binding.get("response_field_mapping") or "").strip(),
                    "server_generated_fields": server_generated_fields,
                    "ui_refresh_targets": ui_refresh_targets,
                    "rbac_policy": str(binding.get("rbac_policy") or "").strip(),
                    "audit_event": str(binding.get("audit_event") or "").strip(),
                    "failure_codes": str(binding.get("failure_codes") or "").strip(),
                    "readiness_status": str(binding.get("readiness_status") or enrichment.get("readiness_status") or interaction.get("readiness_status") or "").strip(),
                    "blocked_reason": blocked_reason,
                }
            )
            if binding:
                compiled_bindings.append(
                    {
                        "page_id": page_id,
                        "canonical_page_id": surface_contract_v2["canonical_page_id"],
                        "audience_mode": surface_contract_v2["audience_mode"],
                        "exposure_scope": interaction_internal_exposure,
                        "interaction_id": interaction_id,
                        "service_binding_id": str(binding.get("service_binding_id") or "").strip(),
                        "flow_id": str(flow.get("flow_id") or "").strip(),
                        "use_case_id": str(binding.get("use_case_id") or interaction.get("use_case_id") or flow.get("use_case_id") or "").strip(),
                        "binding_mode": str(binding.get("binding_mode") or "").strip(),
                        "domain_service": str(binding.get("domain_service") or "").strip(),
                        "api_endpoint": str(binding.get("api_endpoint") or "").strip(),
                        "http_method": str(binding.get("http_method") or "").strip(),
                        "request_field_mapping": str(binding.get("request_field_mapping") or "").strip(),
                        "response_field_mapping": str(binding.get("response_field_mapping") or "").strip(),
                        "server_generated_fields": server_generated_fields,
                        "ui_refresh_targets": ui_refresh_targets,
                        "handoff_materialization": handoff_materialization,
                        "rbac_policy": str(binding.get("rbac_policy") or "").strip(),
                        "audit_event": str(binding.get("audit_event") or "").strip(),
                        "failure_codes": str(binding.get("failure_codes") or "").strip(),
                    }
                )

        user_inputs = _merge_user_inputs_from_actions(page_actions, locale=locale, surface=page_name)
        field_source_mapping = _field_source_mapping_from_actions(page_actions)
        selector_fields = [
            str(item.get("field") or "").strip()
            for item in field_source_mapping
            if isinstance(item, dict)
            and str(item.get("source") or "").strip() == "workflow-context"
            and str(item.get("field") or "").strip()
        ]
        user_inputs = _augment_user_inputs_with_selector_fields(
            user_inputs=user_inputs,
            selector_fields=selector_fields,
            actions=page_actions,
            locale=locale,
            surface=page_name,
        )
        page_blueprint_type = _refine_page_blueprint_type_from_runtime_semantics(
            page_name,
            page_blueprint_type,
            page_role=page_role,
            user_inputs=user_inputs,
            actions=page_actions,
        )
        page_role = _canonical_page_role_from_blueprint(page_blueprint_type, fallback=page_role)
        blueprint_semantics = _default_blueprint_semantics(page_blueprint_type, locale=locale)
        primary_work_region = str(
            prototype_page_contract.get("primary_work_region")
            or blueprint_semantics.get("primary_work_region")
            or ""
        ).strip()
        secondary_support_regions = [
            str(item).strip()
            for item in (
                prototype_page_contract.get("secondary_support_regions")
                or blueprint_semantics.get("secondary_support_regions", [])
            )
            if str(item).strip()
        ]
        dominant_component_pattern = str(
            prototype_page_contract.get("dominant_component_pattern")
            or blueprint_semantics.get("dominant_component_pattern")
            or ""
        ).strip()
        action_model = str(
            prototype_page_contract.get("action_model")
            or blueprint_semantics.get("action_model")
            or ""
        ).strip()
        summary_cards = [
            str(item).strip()
            for item in prototype_page_contract.get("summary_cards", [])
            if str(item).strip()
        ]
        detail_fields_in_order = [
            str(item).strip()
            for item in prototype_page_contract.get("detail_fields_in_order", [])
            if str(item).strip()
        ]
        table_columns = [
            str(item).strip()
            for item in prototype_page_contract.get("table_columns", [])
            if str(item).strip()
        ]
        filters_and_selectors = [
            str(item).strip()
            for item in prototype_page_contract.get("filters_and_selectors", [])
            if str(item).strip()
        ]
        required_status_messages = [
            str(item).strip()
            for item in prototype_page_contract.get("required_status_messages", [])
            if str(item).strip()
        ]
        submission_feedback = [
            str(item).strip()
            for item in prototype_page_contract.get("submission_feedback", [])
            if str(item).strip()
        ]
        contract_sections = _contract_driven_sections(
            surface=page_name,
            page_role=page_role,
            locale=locale,
            display_fields=page_display_fields,
            user_inputs=user_inputs,
            summary_cards=summary_cards,
            detail_fields_in_order=detail_fields_in_order,
            table_columns=table_columns,
            selector_fields=selector_fields,
            filters_and_selectors=filters_and_selectors,
            submission_feedback=submission_feedback,
            required_status_messages=required_status_messages,
        )
        sections = contract_sections or _default_sections(
            page_name,
            page_role,
            display_fields=page_display_fields,
            user_inputs=user_inputs,
            locale=locale,
        ) or _compiled_sections_from_regions(
            required_regions=required_regions,
            display_fields=page_display_fields,
            user_inputs=user_inputs,
            locale=locale,
        )
        contract_presentation = _contract_driven_presentation(
            summary_cards=summary_cards,
            detail_fields_in_order=detail_fields_in_order,
            table_columns=table_columns,
            filters_and_selectors=filters_and_selectors,
            required_status_messages=required_status_messages,
            submission_feedback=submission_feedback,
        )
        data_presentation = list(
            dict.fromkeys(
                [
                    *contract_presentation,
                    *[
                        str(section.get("view") or "").strip()
                        for section in sections
                        if isinstance(section, dict) and str(section.get("view") or "").strip()
                    ],
                ]
            )
        ) or _default_presentation(page_name, page_data_required)
        forbidden_layout_patterns = [
            str(item).strip()
            for item in prototype_page_contract.get("forbidden_layout_patterns", [])
            if str(item).strip()
        ]
        business_state_transitions = _business_state_transitions(
            page_blueprint_type=page_blueprint_type,
            actions=page_actions,
            next_route=next_route_candidates[0] if next_route_candidates else "",
            locale=locale,
        )
        semantic_guardrails = _page_semantic_guardrails(
            page_blueprint_type=page_blueprint_type,
            dominant_component_pattern=dominant_component_pattern,
            forbidden_layout_patterns=forbidden_layout_patterns,
            prototype_constraints=prototype_constraints,
            locale=locale,
        )
        has_surface_handoff = bool(
            next_route_candidates
            or any(str(item.get("next_page_id") or item.get("next_route") or "").strip() for item in compiled_interactions)
        )
        compiled_handoff_visibility = next(
            (
                _normalize_handoff_materialization(item.get("handoff_materialization"))
                for item in compiled_interactions
                if _normalize_handoff_materialization(item.get("handoff_materialization"))
            ),
            "",
        )
        if not surface_contract_v2["handoff_visibility"] and compiled_handoff_visibility:
            surface_contract_v2["handoff_visibility"] = compiled_handoff_visibility
        elif not surface_contract_v2["handoff_visibility"] and has_surface_handoff:
            surface_contract_v2["handoff_visibility"] = "implicit_context" if surface_contract_v2["audience_mode"] == "app" else "review_only"
        if surface_contract_alerts:
            if page_readiness_status == "ready":
                page_readiness_status = "blocked"
            page_blocked_reason = _merge_blocked_reasons(page_blocked_reason, *surface_contract_alerts)
            page_status_messages.extend(f"blocked: {item}" for item in surface_contract_alerts)
        merged_status_messages = list(dict.fromkeys(required_status_messages + page_status_messages))
        merged_submission_feedback = list(dict.fromkeys(submission_feedback + page_submission_feedback))
        localized_title = display_title
        resolved_page_goal = _normalize_page_facing_goal(
            _best_surface_goal(
                surface=surface,
                prototype_page_contract=prototype_page_contract,
                page_name=page_name,
                main_flow_goals=main_flow_goals,
                localized_title=localized_title,
            ),
            locale=locale,
            page_role=page_role,
            page_title=localized_title,
            business_objects=business_objects,
            allowed_roles=allowed_roles,
        )
        compiled_pages.append(
            {
                "contract_source": "compiled-surface-contract",
                "page_id": page_id,
                "source_page_name": page_name,
                "page_title": localized_title,
                "locale": locale,
                "route": page_route,
                "page_role": page_role,
                "page_blueprint_type": page_blueprint_type,
                "canonical_page_id": surface_contract_v2["canonical_page_id"],
                "surface_variant": surface_contract_v2["surface_variant"],
                "audience_mode": surface_contract_v2["audience_mode"],
                "session_role_source": surface_contract_v2["session_role_source"],
                "auth_entry_route": surface_contract_v2["auth_entry_route"],
                "auth_entry_label": surface_contract_v2["auth_entry_label"],
                "workspace_entry_roles": surface_contract_v2["workspace_entry_roles"],
                "route_reachability_mode": surface_contract_v2["route_reachability_mode"],
                "navigation_scope": surface_contract_v2["navigation_scope"],
                "handoff_visibility": surface_contract_v2["handoff_visibility"],
                "forbidden_exposure": surface_contract_v2["forbidden_exposure"],
                "surface_contract_alerts": surface_contract_alerts,
                "primary_actor": normalize_role_display_name(str(surface.get("primary_actor") or "").strip(), locale),
                "allowed_roles": allowed_roles,
                "primary_user_goal": resolved_page_goal,
                "business_objects": business_objects,
                "required_regions": required_regions,
                "next_route_candidates": next_route_candidates,
                "denied_behavior": str(surface.get("denied_behavior") or "").strip(),
                "readiness_status": page_readiness_status,
                "blocked_reason": page_blocked_reason,
                "compiled_interactions": compiled_interactions,
                "data_required": page_data_required,
                "data_presentation": data_presentation,
                "display_fields": page_display_fields,
                "user_inputs": user_inputs,
                "field_source_mapping": field_source_mapping,
                "state_conditions": _default_state_conditions(page_name, page_data_required, locale=locale),
                "actions_and_transitions": page_actions,
                "primary_work_region": primary_work_region,
                "secondary_support_regions": secondary_support_regions,
                "dominant_component_pattern": dominant_component_pattern,
                "action_model": action_model,
                "sections": sections,
                "must_show_together": [
                    str(item).strip()
                    for item in (
                        prototype_page_contract.get("must_show_together")
                        or surface.get("must_show_together", [])
                    )
                    if str(item).strip()
                ],
                "required_user_inputs_or_confirmations": [
                    str(item).strip()
                    for item in prototype_page_contract.get("required_user_inputs_or_confirmations", [])
                    if str(item).strip()
                ],
                "render_blocks_in_order": [
                    str(item).strip()
                    for item in prototype_page_contract.get("render_blocks_in_order", [])
                    if str(item).strip()
                ],
                "field_groups": [
                    str(item).strip()
                    for item in prototype_page_contract.get("field_groups", [])
                    if str(item).strip()
                ],
                "input_controls": [
                    str(item).strip()
                    for item in prototype_page_contract.get("input_controls", [])
                    if str(item).strip()
                ],
                "summary_cards": summary_cards,
                "detail_fields_in_order": detail_fields_in_order,
                "table_columns": table_columns,
                "filters_and_selectors": filters_and_selectors,
                "required_status_messages": _items_with_visibility(
                    merged_status_messages,
                    "implementation-guide",
                    "each status must become a user-facing state; do not render the raw contract list verbatim",
                ),
                "submission_feedback": merged_submission_feedback,
                "context_arrives_from": str(
                    prototype_page_contract.get("context_arrives_from")
                    or surface.get("entry_conditions")
                    or ""
                ).strip(),
                "context_must_continue_to": str(
                    prototype_page_contract.get("context_must_continue_to")
                    or surface.get("exit_conditions")
                    or ""
                ).strip(),
                "eyebrow": page_role_eyebrow(page_role, locale),
                "subtitle": resolved_page_goal or localized_title,
                "user_goal": resolved_page_goal or localized_title,
                "primary_cta": (
                    {
                        "label": _compact_action_label(
                            str(prototype_page_contract.get("primary_cta_label") or page_actions[0].get("action") or "").strip(),
                            locale=locale,
                            action_type=str((page_actions[0] if page_actions else {}).get("action_type") or "").strip().lower(),
                            page_title=localized_title,
                            page_role=page_role,
                            business_objects=business_objects,
                            allowed_roles=allowed_roles,
                        ),
                        "hint": normalize_inline_locale_variants(str(page_actions[0].get("on_success") or "").strip(), locale),
                        "kind": "primary-action",
                    }
                    if page_actions
                    else _default_primary_cta(page_name, page_role, page_data_required, locale=locale)
                ),
                "secondary_cta": (
                    {
                        "label": normalize_inline_locale_variants(str(prototype_page_contract.get("secondary_ctas", [""])[0] or "").strip(), locale),
                        "kind": "secondary-action",
                    }
                    if prototype_page_contract.get("secondary_ctas")
                    else _default_secondary_cta(page_name, page_role, locale=locale)
                ),
                "empty_state": _default_empty_state(page_name, page_role, locale=locale),
                "success_state": _default_success_state(page_name, page_role, locale=locale),
                "error_state": _default_error_state(page_role, locale=locale),
                "business_state_transitions": business_state_transitions,
                "semantic_guardrails": semantic_guardrails,
                "implementation_design": {
                    "interaction_pattern": page_blueprint_type,
                    "primary_work_region": primary_work_region,
                    "dominant_component_pattern": dominant_component_pattern,
                    "business_state_transitions": business_state_transitions,
                    "semantic_guardrails": semantic_guardrails,
                },
                "navigation": {
                    "previous_route": str(surface_rows[index - 1].get("route") or "").strip() if index > 0 else "",
                    "next_route": next_route_candidates[0] if next_route_candidates else "",
                },
            }
        )
    return compiled_pages, compiled_bindings


def _surface_keyword_groups(surface: str) -> list[str]:
    tokens = _surface_title_tokens(surface)
    lowered = surface.lower()
    expanded = list(tokens)
    if any(token in lowered for token in ("create", "new", "submit", "update", "edit")):
        expanded.extend(["create", "update", "submit"])
    if any(token in lowered for token in ("overview", "dashboard", "home")):
        expanded.extend(["summary", "status", "list"])
    if any(token in lowered for token in ("detail", "profile", "view")):
        expanded.extend(["detail", "id"])
    if any(token in lowered for token in ("list", "catalog", "queue", "search")):
        expanded.extend(["list", "search", "query"])
    if not expanded:
        expanded.extend(["list", "detail", "status"])
    return list(dict.fromkeys(expanded))


def _pick_endpoints_for_surface(
    surface: str,
    endpoints: list[dict[str, str]],
    *,
    desired_count: int = 2,
) -> list[dict[str, str]]:
    keywords = _surface_keyword_groups(surface)
    scored: list[tuple[int, dict[str, str]]] = []
    for endpoint in endpoints:
        haystack = " ".join(
            [
                str(endpoint.get("method", "")),
                str(endpoint.get("path", "")),
                str(endpoint.get("purpose", "")),
            ]
        ).lower()
        score = 0
        for keyword in keywords:
            if keyword in haystack:
                score += 2
        if str(endpoint.get("method", "")).upper() == "GET":
            score += 1
        scored.append((score, endpoint))
    scored.sort(key=lambda item: item[0], reverse=True)
    picked = [row for score, row in scored if score > 0][:desired_count]
    if picked:
        return picked
    return endpoints[:desired_count]


def _pick_endpoints_with_hard_rules(
    surface: str,
    endpoints: list[dict[str, str]],
    *,
    desired_count: int = 2,
) -> list[dict[str, str]]:
    operation_sequence = _surface_operation_sequence(surface)
    if operation_sequence:
        ordered: list[dict[str, str]] = []
        for operation_id in operation_sequence:
            for endpoint in endpoints:
                if str(endpoint.get("operation_id") or "").strip() == operation_id:
                    ordered.append(endpoint)
                    break
        if ordered:
            return ordered
    lowered = surface.lower()
    if any(token in lowered for token in ("create", "new", "submit", "update", "edit", "action", "operation")):
        preferred = [
            endpoint
            for endpoint in endpoints
            if str(endpoint.get("method", "")).upper() in {"POST", "PUT", "PATCH", "DELETE"}
        ]
        if preferred:
            return preferred[:desired_count]
    if any(token in lowered for token in ("overview", "dashboard", "list", "catalog", "detail", "view", "search")):
        preferred = [
            endpoint
            for endpoint in endpoints
            if str(endpoint.get("method", "")).upper() == "GET"
        ]
        if preferred:
            return preferred[:desired_count]
    return _pick_endpoints_for_surface(surface, endpoints, desired_count=desired_count)


def generate_ui_prototype_fallback(
    *,
    phase2_root: Path,
    output_dir: Path,
    stage_04_text: str,
    esp_text: str,
    stage_03_text: str = "",
    openapi_path: Path | None = None,
    ui_locale: str | None = None,
) -> dict[str, Any]:
    fallback_dir = output_dir / "prototype-fallback"
    fallback_dir.mkdir(parents=True, exist_ok=True)

    manual_assets = _discover_manual_prototype_assets(phase2_root)
    triggered = len(manual_assets) == 0
    endpoints = _endpoint_rows_from_openapi(openapi_path) if openapi_path is not None else []
    endpoint_source = "openapi" if endpoints else "esp"
    if not endpoints:
        endpoints = _endpoint_rows(esp_text)
    locale = infer_ui_locale(stage_04_text, esp_text, preferred=ui_locale)
    workflow_hints = _extract_workflow_hints(stage_04_text)
    prototype_spec_path = _extract_phase1_prototype_spec_path(stage_04_text, phase2_root)
    prototype_prompt_pack_path = _extract_phase1_prototype_prompt_pack_path(stage_04_text, phase2_root)
    interaction_flow_contract_path = _extract_phase1_interaction_flow_contract_path(stage_04_text, phase2_root)
    prototype_spec_text = _read(prototype_spec_path) if prototype_spec_path else ""
    interaction_flow_contract_text = _read(interaction_flow_contract_path) if interaction_flow_contract_path else ""
    resolved_stage_03_text = stage_03_text or _read(phase2_root / "stage-03-data-storage-and-interface-design.md")
    prototype_page_map = _extract_page_map_entries_from_prototype_spec(prototype_spec_text)
    prototype_page_map_by_name = {
        str(entry.get("page_name") or "").strip(): entry
        for entry in prototype_page_map
        if str(entry.get("page_name") or "").strip()
    }
    compiled_pages, compiled_bindings = _compile_surface_contract_artifacts(
        prototype_spec_text=prototype_spec_text,
        interaction_flow_contract_text=interaction_flow_contract_text,
        stage_03_text=resolved_stage_03_text,
        esp_text=esp_text,
        locale=locale,
    )
    authoritative_compiled_contract = bool(compiled_pages) and all(
        not page.get("surface_contract_alerts")
        for page in compiled_pages
        if isinstance(page, dict)
    )
    mode = (
        "manual-prototype-detected"
        if not triggered
        else ("compiled-contract-generated" if authoritative_compiled_contract else "fallback-generated")
    )
    primary_surfaces = _ensure_required_primary_surfaces(
        [str(page.get("source_page_name") or page.get("page_title") or "").strip() for page in compiled_pages if str(page.get("source_page_name") or page.get("page_title") or "").strip()]
        or _extract_primary_surfaces(stage_04_text, prototype_spec_text),
        endpoints,
    )
    prototype_page_contracts = _extract_prototype_page_contracts(prototype_spec_text)
    prototype_constraints = _extract_prototype_generation_constraints(prototype_spec_text)
    external_executor_brief = _extract_external_executor_brief(prototype_spec_text)
    app_context = _build_app_context(
        stage_04_text=stage_04_text,
        phase2_root=phase2_root,
        locale=locale,
        primary_surfaces=primary_surfaces,
    )
    top_endpoints = endpoints[:8]

    fallback_md_path = fallback_dir / "ui-prototype-fallback.md"
    wireframes_path = fallback_dir / "ui-wireframes.html"
    api_mapping_path = fallback_dir / "ui-api-mapping.json"
    ia_contract_path = fallback_dir / "ui-ia-contract.json"
    delivery_contract_path = fallback_dir / "ui-delivery-contract.json"
    frontend_stack_path = fallback_dir / "frontend-default-stack.json"
    site_dir = fallback_dir / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    site_index_path = site_dir / "index.html"
    site_css_path = site_dir / "style.css"
    report_path = fallback_dir / "ui-prototype-fallback-report.json"

    fallback_md_path.write_text(
        "\n".join(
            [
                f"# {ui_text(locale, 'fallback_ui_title')}",
                "",
                f"- mode: mode",
                f"- purpose: {ui_text(locale, 'fallback_purpose')}",
                "",
                f"## {ui_text(locale, 'required_mvp_pages')}",
                "1. Workspace page: current status, recent signals, and the next recommended action"
                if not is_zh_locale(locale)
                else "1. 工作台页面：展示当前状态、最近信号和推荐的下一步操作",
                "2. List/detail page: browse the current working set and inspect a selected item"
                if not is_zh_locale(locale)
                else "2. 列表/详情页面：浏览当前工作集并查看选中项详情",
                "3. Form/workflow page: capture business inputs, validate them, and submit safely"
                if not is_zh_locale(locale)
                else "3. 表单/工作流页面：采集业务输入、执行校验并安全提交",
                "4. Review page: summarize evidence, record the operator decision, and keep the next step explicit"
                if not is_zh_locale(locale)
                else "4. 审核页面：汇总证据、记录操作人决策并明确下一步",
                "",
                f"## {ui_text(locale, 'workflow_hints')}",
                *([f"- {hint}" for hint in workflow_hints] or ["- (no explicit hints extracted)"]),
                "",
                f"## {ui_text(locale, 'backend_api_anchors')}",
                *(
                    [f"- `{row['method']} {row['path']}` -> {row['purpose']}" for row in top_endpoints]
                    or ["- (no API rows discovered in ESP markdown table format)"]
                ),
                "",
                f"## {ui_text(locale, 'evidence_rule')}",
                "- This fallback is a default input, not a final UX sign-off."
                if not is_zh_locale(locale)
                else "- 该 fallback 只是默认输入，不代表最终 UX 签收。",
                "- P3 implementation must still deliver materially operable IA pages rather than explanatory placeholders or debug consoles."
                if not is_zh_locale(locale)
                else "- P3 实现仍必须交付可实际操作的 IA 页面，而不是说明性占位页或调试控制台。",
                "- Page contracts must describe user goal, primary CTA, sections, states, and data/input bindings before code generation begins."
                if not is_zh_locale(locale)
                else "- 在代码生成前，页面契约必须明确用户目标、主要 CTA、页面分区、状态以及数据/输入绑定。",
                "- At least one cross-page user flow must execute end-to-end, and every core IA route must expose its page-level action and data state."
                if not is_zh_locale(locale)
                else "- 至少有一个跨页面用户流需要端到端可执行，并且每个核心 IA 路由都必须暴露页面级操作与数据状态。",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    wireframes_path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                f"<html lang=\"{locale}\">",
                f"<head><meta charset=\"utf-8\" /><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" /><title>{ui_text(locale, 'wireframes_title')}</title></head>",
                "<body>",
                f"<h1>{ui_text(locale, 'wireframes_title')}</h1>",
                "<p>Mode: " + (mode) + "</p>",
                "<section><h2>Workspace</h2><p>" + ui_text(locale, "site_workspace_desc") + "</p></section>"
                if not is_zh_locale(locale)
                else "<section><h2>工作台</h2><p>" + ui_text(locale, "site_workspace_desc") + "</p></section>",
                "<section><h2>List / Detail</h2><p>" + ui_text(locale, "site_list_detail_desc") + "</p></section>"
                if not is_zh_locale(locale)
                else "<section><h2>列表 / 详情</h2><p>" + ui_text(locale, "site_list_detail_desc") + "</p></section>",
                "<section><h2>Workflow Form</h2><p>" + ui_text(locale, "site_workflow_form_desc") + "</p></section>"
                if not is_zh_locale(locale)
                else "<section><h2>工作流表单</h2><p>" + ui_text(locale, "site_workflow_form_desc") + "</p></section>",
                "<section><h2>Review</h2><p>" + ui_text(locale, "site_review_desc") + "</p></section>"
                if not is_zh_locale(locale)
                else "<section><h2>审核</h2><p>" + ui_text(locale, "site_review_desc") + "</p></section>",
                "</body>",
                "</html>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    site_css_path.write_text(
        "\n".join(
            [
                "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; line-height: 1.5; }",
                "nav a { margin-right: 12px; }",
                ".card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 12px 0; }",
                ".muted { color: #666; }",
                ".pill { display: inline-block; border-radius: 999px; padding: 4px 10px; background: #eef2ff; color: #1e3a8a; margin-right: 8px; font-size: 12px; }",
                "table { border-collapse: collapse; width: 100%; }",
                "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    surface_pages = (
        [str(page.get("source_page_name") or page.get("page_title") or "").strip() for page in compiled_pages if str(page.get("source_page_name") or page.get("page_title") or "").strip()]
        or primary_surfaces
        or [
            "Overview dashboard",
            "Primary record list",
            "Record detail view",
            "Action workspace",
        ]
    )
    surface_titles = [_display_surface_title(surface, locale) for surface in surface_pages]
    delivery_pages: list[dict[str, Any]] = list(compiled_pages)
    mapping = {
        "mode": mode,
        "locale": locale,
        "app_context": app_context,
        "surface_provenance": "compiled-surface-contract" if compiled_pages else ("phase1-prototype-spec" if prototype_page_map else "stage04-primary-surfaces"),
        "pages": [],
    }
    if compiled_pages:
        for page in delivery_pages:
            mapping["pages"].append(
                {
                    "page": _business_slug(str(page.get("source_page_name") or page.get("page_title") or "").strip()),
                    "title": str(page.get("page_title") or "").strip(),
                    "page_role": str(page.get("page_role") or "").strip(),
                    "page_blueprint_type": str(page.get("page_blueprint_type") or "").strip(),
                    "canonical_page_id": str(page.get("canonical_page_id") or "").strip(),
                    "surface_variant": str(page.get("surface_variant") or "").strip(),
                    "audience_mode": str(page.get("audience_mode") or "").strip(),
                    "workspace_entry_roles": page.get("workspace_entry_roles", []),
                    "route_reachability_mode": str(page.get("route_reachability_mode") or "").strip(),
                    "navigation_scope": str(page.get("navigation_scope") or "").strip(),
                    "forbidden_exposure": page.get("forbidden_exposure", []),
                    "surface_contract_alerts": page.get("surface_contract_alerts", []),
                    "dominant_layout": _layout_for_blueprint(str(page.get("page_blueprint_type") or "").strip()),
                    "business_state_transitions": page.get("business_state_transitions", []),
                    "semantic_guardrails": page.get("semantic_guardrails", []),
                    "page_actor": page.get("page_actor", []),
                    "workflow_step": page.get("workflow_step", {}),
                    "information_objects": page.get("information_objects", []),
                    "primary_cta": page.get("primary_cta", {}),
                    "api_candidates": page.get("data_required", []),
                    "prototype_page_contract": page.get("prototype_page_contract", {}),
                }
            )
    loop_surfaces = [] if compiled_pages else surface_pages
    for idx, surface in enumerate(loop_surfaces, start=1):
        page_map_entry = prototype_page_map_by_name.get(str(surface).strip(), {})
        surface_slug = _business_slug(surface)
        surface_title = surface_titles[idx - 1]
        page_endpoints = _pick_endpoints_with_hard_rules(surface, endpoints)
        blueprint = _surface_business_blueprint(surface, page_endpoints, locale=locale)
        display_fields = (
            [str(item).strip() for item in blueprint.get("display_fields", []) if str(item).strip()]
            if blueprint
            else _default_display_fields(page_endpoints)
        )
        user_inputs = (
            [item for item in blueprint.get("user_inputs", []) if isinstance(item, dict)]
            if blueprint
            else _default_user_inputs(surface, page_endpoints, locale=locale)
        )
        data_required = [
            {
                "source": "api",
                "method": endpoint["method"],
                "path": endpoint["path"],
                "purpose": endpoint["purpose"],
            }
            for endpoint in page_endpoints
        ]
        page_role = (
            str(page_map_entry.get("page_role") or "").strip()
            or (str(blueprint.get("page_role") or "").strip() if blueprint else "")
            or _infer_page_role(surface, page_endpoints, page_index=idx - 1)
        )
        primary_cta = (
            blueprint.get("primary_cta")
            if blueprint and isinstance(blueprint.get("primary_cta"), dict)
            else _default_primary_cta(surface, page_role, page_endpoints, locale=locale)
        )
        secondary_cta = (
            blueprint.get("secondary_cta")
            if blueprint and isinstance(blueprint.get("secondary_cta"), dict)
            else _default_secondary_cta(surface, page_role, locale=locale)
        )
        workflow_step = (
            app_context.get("workflow_backbone", [])[idx - 1]
            if idx - 1 < len(app_context.get("workflow_backbone", []))
            else {}
        )
        next_route = f"/{_business_slug(surface_pages[idx])}" if idx < len(surface_pages) else ""
        prototype_page_contract = _match_prototype_page_contract(surface_title, page_role, surface, prototype_page_contracts)
        page_blueprint_type = (
            str(page_map_entry.get("page_blueprint_type") or "").strip()
            or (str(blueprint.get("page_blueprint_type") or "").strip() if blueprint else "")
            or _infer_page_blueprint_type(surface, page_role, prototype_page_contract)
        )
        page_blueprint_type = _refine_page_blueprint_type_from_runtime_semantics(
            surface,
            page_blueprint_type,
            page_role=page_role,
            user_inputs=user_inputs,
            methods={str(item.get("method") or "").strip().upper() for item in page_endpoints if str(item.get("method") or "").strip()},
        )
        page_role = _canonical_page_role_from_blueprint(page_blueprint_type, fallback=page_role)
        blueprint_semantics = _default_blueprint_semantics(page_blueprint_type, locale=locale)
        fallback_surface_contract_v2, fallback_surface_contract_alerts = _resolve_surface_contract_v2(
            surface=page_map_entry,
            page_name=surface,
            page_id=surface_slug,
            page_blueprint_type=page_blueprint_type,
            allowed_roles=[],
            locale=locale,
        )
        if not fallback_surface_contract_v2["handoff_visibility"] and next_route:
            fallback_surface_contract_v2["handoff_visibility"] = "implicit_context"
        summary_cards = [
            str(item).strip()
            for item in (
                blueprint.get("summary_cards", [])
                if blueprint and isinstance(blueprint.get("summary_cards", []), list) and blueprint.get("summary_cards")
                else prototype_page_contract.get("summary_cards", [])
            )
            if str(item).strip()
        ]
        detail_fields_in_order = [
            str(item).strip()
            for item in (
                blueprint.get("detail_fields_in_order", [])
                if blueprint and isinstance(blueprint.get("detail_fields_in_order", []), list) and blueprint.get("detail_fields_in_order")
                else prototype_page_contract.get("detail_fields_in_order", [])
            )
            if str(item).strip()
        ]
        table_columns = [
            str(item).strip()
            for item in (
                blueprint.get("table_columns", [])
                if blueprint and isinstance(blueprint.get("table_columns", []), list) and blueprint.get("table_columns")
                else prototype_page_contract.get("table_columns", [])
            )
            if str(item).strip()
        ]
        filters_and_selectors = [
            str(item).strip()
            for item in (
                blueprint.get("filters_and_selectors", [])
                if blueprint and isinstance(blueprint.get("filters_and_selectors", []), list) and blueprint.get("filters_and_selectors")
                else prototype_page_contract.get("filters_and_selectors", [])
            )
            if str(item).strip()
        ]
        selector_fields = [
            str(item.get("field") or "").strip()
            for item in (
                blueprint.get("field_source_mapping", [])
                if blueprint and isinstance(blueprint.get("field_source_mapping"), list)
                else prototype_page_contract.get("field_source_mapping", [])
            )
            if isinstance(item, dict)
            and str(item.get("source") or "").strip() == "workflow-context"
            and str(item.get("field") or "").strip()
        ]
        user_inputs = _augment_user_inputs_with_selector_fields(
            user_inputs=user_inputs,
            selector_fields=selector_fields,
            actions=[
                item
                for item in (
                    blueprint.get("actions_and_transitions", [])
                    if blueprint and isinstance(blueprint.get("actions_and_transitions"), list)
                    else prototype_page_contract.get("actions_and_transitions", [])
                )
                if isinstance(item, dict)
            ],
            locale=locale,
            surface=surface,
        )
        required_status_messages = [
            str(item).strip()
            for item in prototype_page_contract.get("required_status_messages", [])
            if str(item).strip()
        ]
        submission_feedback = [
            str(item).strip()
            for item in prototype_page_contract.get("submission_feedback", [])
            if str(item).strip()
        ]
        contract_sections = _contract_driven_sections(
            surface=surface,
            page_role=page_role,
            locale=locale,
            display_fields=display_fields,
            user_inputs=user_inputs,
            summary_cards=summary_cards,
            detail_fields_in_order=detail_fields_in_order,
            table_columns=table_columns,
            selector_fields=selector_fields,
            filters_and_selectors=filters_and_selectors,
            submission_feedback=submission_feedback,
            required_status_messages=required_status_messages,
        )
        contract_presentation = _contract_driven_presentation(
            summary_cards=summary_cards,
            detail_fields_in_order=detail_fields_in_order,
            table_columns=table_columns,
            filters_and_selectors=filters_and_selectors,
            required_status_messages=required_status_messages,
            submission_feedback=submission_feedback,
        )
        resolved_sections: list[dict[str, Any]]
        if blueprint and isinstance(blueprint.get("sections"), list) and blueprint.get("sections"):
            resolved_sections = [item for item in blueprint.get("sections", []) if isinstance(item, dict)]
        elif contract_sections:
            resolved_sections = contract_sections
        else:
            resolved_sections = _default_sections(surface, page_role, display_fields=display_fields, user_inputs=user_inputs, locale=locale)
        resolved_presentation = list(
            dict.fromkeys(
                [
                    *(
                        [str(item).strip() for item in blueprint.get("data_presentation", []) if str(item).strip()]
                        if blueprint and isinstance(blueprint.get("data_presentation"), list)
                        else []
                    ),
                    *contract_presentation,
                ]
            )
        )
        if not resolved_presentation:
            resolved_presentation = _default_presentation(surface, page_endpoints)
        transitions: list[dict[str, Any]] = []
        if blueprint and isinstance(blueprint.get("actions_and_transitions"), list):
            for action in blueprint.get("actions_and_transitions", []):
                if not isinstance(action, dict) or not str(action.get("action") or "").strip():
                    continue
                hydrated_action = dict(action)
                hydrated_action.setdefault("on_success", _default_success_state(surface, page_role, locale=locale)["body"])
                hydrated_action.setdefault("on_error", _default_error_state(page_role, locale=locale)["body"])
                transitions.append(hydrated_action)
        else:
            for endpoint in page_endpoints:
                transitions.append(
                    {
                        "action": _action_label_for_endpoint(endpoint, locale=locale),
                        "on_success": _default_success_state(surface, page_role, locale=locale)["body"],
                        "on_error": _default_error_state(page_role, locale=locale)["body"],
                        "api_binding": {
                            "method": endpoint["method"],
                            "path": endpoint["path"],
                        },
                    }
                )
        if next_route:
            transitions.append(
                {
                    "action": (f"Continue to {surface_titles[idx]}" if not is_zh_locale(locale) else f"继续到{surface_titles[idx]}"),
                    "on_success": "Carry the current context into the next workflow step."
                    if not is_zh_locale(locale)
                    else "将当前上下文带入下一步工作流。",
                    "on_error": "Keep the current page open with the guidance still visible."
                    if not is_zh_locale(locale)
                    else "保持当前页面打开，并继续显示操作指引。",
                }
            )
        business_state_transitions = _business_state_transitions(
            page_blueprint_type=page_blueprint_type,
            actions=transitions,
            next_route=next_route,
            locale=locale,
        )
        page_actor = _default_page_actor(
            surface,
            primary_actor=_visibility_text(app_context.get("primary_actor", "")),
            supporting_roles=[
                str(item).strip()
                for item in app_context.get("supporting_roles", [])
                if str(item).strip()
            ],
        )
        information_objects = [
            localize_information_object(item, locale)
            for item in _information_objects_from_data_required(data_required)
        ]
        dominant_component_pattern = str(
            prototype_page_contract.get("dominant_component_pattern")
            or blueprint.get("dominant_component_pattern")
            or blueprint_semantics.get("dominant_component_pattern")
            or ""
        ).strip() if blueprint else str(
            prototype_page_contract.get("dominant_component_pattern")
            or blueprint_semantics.get("dominant_component_pattern")
            or ""
        ).strip()
        forbidden_layout_patterns = [
            str(item).strip()
            for item in (
                blueprint.get("forbidden_layout_patterns", [])
                if blueprint and isinstance(blueprint.get("forbidden_layout_patterns"), list) and blueprint.get("forbidden_layout_patterns")
                else prototype_page_contract.get("forbidden_layout_patterns", [])
            )
            if str(item).strip()
        ]
        semantic_guardrails = _page_semantic_guardrails(
            page_blueprint_type=page_blueprint_type,
            dominant_component_pattern=dominant_component_pattern,
            forbidden_layout_patterns=forbidden_layout_patterns,
            prototype_constraints=prototype_constraints,
            locale=locale,
        )
        mapping["pages"].append(
            {
                "page": surface_slug,
                "title": surface_title,
                "page_role": page_role,
                "page_blueprint_type": page_blueprint_type,
                "canonical_page_id": fallback_surface_contract_v2["canonical_page_id"],
                "surface_variant": fallback_surface_contract_v2["surface_variant"],
                "audience_mode": fallback_surface_contract_v2["audience_mode"],
                "workspace_entry_roles": fallback_surface_contract_v2["workspace_entry_roles"],
                "route_reachability_mode": fallback_surface_contract_v2["route_reachability_mode"],
                "navigation_scope": fallback_surface_contract_v2["navigation_scope"],
                "forbidden_exposure": fallback_surface_contract_v2["forbidden_exposure"],
                "surface_contract_alerts": fallback_surface_contract_alerts,
                "dominant_layout": _layout_for_blueprint(page_blueprint_type),
                "business_state_transitions": business_state_transitions,
                "semantic_guardrails": semantic_guardrails,
                "page_actor": page_actor,
                "workflow_step": workflow_step,
                "information_objects": information_objects,
                "primary_cta": primary_cta,
                "api_candidates": page_endpoints,
                "prototype_page_contract": prototype_page_contract,
            }
        )
        delivery_pages.append(
            {
                "page_id": surface_slug,
                "locale": locale,
                "page_title": surface_title,
                "route": f"/{surface_slug}",
                "page_role": page_role,
                "page_blueprint_type": page_blueprint_type,
                "canonical_page_id": fallback_surface_contract_v2["canonical_page_id"],
                "surface_variant": fallback_surface_contract_v2["surface_variant"],
                "audience_mode": fallback_surface_contract_v2["audience_mode"],
                "session_role_source": fallback_surface_contract_v2["session_role_source"],
                "auth_entry_route": fallback_surface_contract_v2["auth_entry_route"],
                "auth_entry_label": fallback_surface_contract_v2["auth_entry_label"],
                "workspace_entry_roles": fallback_surface_contract_v2["workspace_entry_roles"],
                "route_reachability_mode": fallback_surface_contract_v2["route_reachability_mode"],
                "navigation_scope": fallback_surface_contract_v2["navigation_scope"],
                "handoff_visibility": fallback_surface_contract_v2["handoff_visibility"],
                "forbidden_exposure": fallback_surface_contract_v2["forbidden_exposure"],
                "surface_contract_alerts": fallback_surface_contract_alerts,
                "dominant_layout": _layout_for_blueprint(page_blueprint_type),
                "primary_work_region": str(
                    prototype_page_contract.get("primary_work_region")
                    or blueprint.get("primary_work_region")
                    or blueprint_semantics.get("primary_work_region")
                    or ""
                ).strip()
                if blueprint
                else str(
                    prototype_page_contract.get("primary_work_region")
                    or blueprint_semantics.get("primary_work_region")
                    or ""
                ).strip(),
                "secondary_support_regions": [
                    str(item).strip()
                    for item in (
                        (
                            prototype_page_contract.get("secondary_support_regions")
                            or blueprint.get("secondary_support_regions")
                            or blueprint_semantics.get("secondary_support_regions", [])
                        )
                        if blueprint
                        else (
                            prototype_page_contract.get("secondary_support_regions")
                            or blueprint_semantics.get("secondary_support_regions", [])
                        )
                    )
                    if str(item).strip()
                ],
                "dominant_component_pattern": dominant_component_pattern,
                "action_model": str(
                    prototype_page_contract.get("action_model")
                    or blueprint.get("action_model")
                    or blueprint_semantics.get("action_model")
                    or ""
                ).strip()
                if blueprint
                else str(
                    prototype_page_contract.get("action_model")
                    or blueprint_semantics.get("action_model")
                    or ""
                ).strip(),
                "forbidden_layout_patterns": forbidden_layout_patterns,
                "app_context": app_context,
                "workflow_step": workflow_step,
                "page_actor": page_actor,
                "information_objects": information_objects,
                "prototype_page_contract": prototype_page_contract,
                "eyebrow": str(blueprint.get("eyebrow") or page_role_eyebrow(page_role, locale)).strip() if blueprint else page_role_eyebrow(page_role, locale),
                "subtitle": str(blueprint.get("subtitle") or _default_page_subtitle(surface, page_role, locale=locale)).strip() if blueprint else _default_page_subtitle(surface, page_role, locale=locale),
                "user_goal": str(blueprint.get("user_goal") or _default_user_goal(surface, page_role, locale=locale)).strip() if blueprint else _default_user_goal(surface, page_role, locale=locale),
                "primary_cta": primary_cta,
                "secondary_cta": secondary_cta,
                "sections": resolved_sections,
                "data_required": data_required,
                "primary_api_binding": data_required[0] if data_required else {},
                "data_presentation": resolved_presentation,
                "display_fields": display_fields,
                "user_inputs": user_inputs,
                "field_source_mapping": (
                    [item for item in blueprint.get("field_source_mapping", []) if isinstance(item, dict)]
                    if blueprint and isinstance(blueprint.get("field_source_mapping"), list)
                    else _field_source_mapping(data_required=data_required, user_inputs=user_inputs)
                ),
                "state_conditions": _default_state_conditions(surface, page_endpoints, locale=locale),
                "business_state_transitions": business_state_transitions,
                "actions_and_transitions": transitions or [
                    {
                        "action": primary_cta["label"],
                        "on_success": _default_success_state(surface, page_role, locale=locale)["body"],
                        "on_error": _default_error_state(page_role, locale=locale)["body"],
                    }
                ],
                "semantic_guardrails": semantic_guardrails,
                "implementation_design": {
                    "interaction_pattern": page_blueprint_type,
                    "primary_work_region": str(
                        prototype_page_contract.get("primary_work_region")
                        or blueprint.get("primary_work_region")
                        or blueprint_semantics.get("primary_work_region")
                        or ""
                    ).strip()
                    if blueprint
                    else str(
                        prototype_page_contract.get("primary_work_region")
                        or blueprint_semantics.get("primary_work_region")
                        or ""
                    ).strip(),
                    "dominant_component_pattern": dominant_component_pattern,
                    "business_state_transitions": business_state_transitions,
                    "semantic_guardrails": semantic_guardrails,
                },
                "navigation": {
                    "previous_route": f"/{_business_slug(surface_pages[idx - 2])}" if idx > 1 else "",
                    "next_route": next_route,
                },
                "empty_state": _default_empty_state(surface, page_role, locale=locale),
                "success_state": _default_success_state(surface, page_role, locale=locale),
                "error_state": _default_error_state(page_role, locale=locale),
                "must_show_together": [
                    str(item).strip()
                    for item in prototype_page_contract.get("must_show_together", [])
                    if str(item).strip()
                ],
                "required_user_inputs_or_confirmations": [
                    str(item).strip()
                    for item in prototype_page_contract.get("required_user_inputs_or_confirmations", [])
                    if str(item).strip()
                ],
                "render_blocks_in_order": [
                    str(item).strip()
                    for item in prototype_page_contract.get("render_blocks_in_order", [])
                    if str(item).strip()
                ],
                "field_groups": [
                    str(item).strip()
                    for item in (
                        blueprint.get("field_groups", [])
                        if blueprint and isinstance(blueprint.get("field_groups", []), list) and blueprint.get("field_groups")
                        else prototype_page_contract.get("field_groups", [])
                    )
                    if str(item).strip()
                ],
                "input_controls": [
                    str(item).strip()
                    for item in prototype_page_contract.get("input_controls", [])
                    if str(item).strip()
                ],
                "summary_cards": summary_cards,
                "detail_fields_in_order": detail_fields_in_order,
                "table_columns": table_columns,
                "filters_and_selectors": filters_and_selectors,
                "required_status_messages": _items_with_visibility(
                    required_status_messages,
                    "implementation-guide",
                    "each status must become a user-friendly UI state; do not render the raw status list verbatim",
                ),
                "primary_cta_label": str(prototype_page_contract.get("primary_cta_label") or "").strip(),
                "secondary_ctas": [
                    str(item).strip()
                    for item in prototype_page_contract.get("secondary_ctas", [])
                    if str(item).strip()
                ],
                "submission_feedback": submission_feedback,
                "context_arrives_from": str(prototype_page_contract.get("context_arrives_from") or "").strip(),
                "context_must_continue_to": str(prototype_page_contract.get("context_must_continue_to") or "").strip(),
                "executor_brief": [
                    str(item).strip()
                    for item in prototype_page_contract.get("executor_brief", [])
                    if str(item).strip()
                ],
                "acceptance_checks": _default_acceptance_checks(
                    surface,
                    page_role=page_role,
                    display_fields=display_fields,
                    user_inputs=user_inputs,
                    next_route=next_route or None,
                    locale=locale,
                ),
            }
        )
    app_context.update(_derive_role_workspace_contract(pages=delivery_pages, app_context=app_context))
    app_context.update(_derive_workflow_navigation_contract(pages=delivery_pages, app_context=app_context))
    app_context["frontend_experience_contract"] = _derive_frontend_experience_contract(
        pages=delivery_pages,
        app_context=app_context,
        locale=locale,
    )
    api_mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nav_links = [f'<a href="./index.html">{ui_text(locale, "dashboard")}</a>']
    for page in delivery_pages:
        nav_links.append(f'<a href="./{page["page_id"]}.html">{page["page_title"]}</a>')
    nav = "<nav>" + "".join(nav_links) + "</nav>"
    site_index_path.write_text(
        "\n".join(
            [
                f"<!doctype html><html lang=\"{locale}\"><head><meta charset=\"utf-8\" /><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" /><title>{ui_text(locale, 'site_dashboard_title')}</title><link rel=\"stylesheet\" href=\"./style.css\" /></head><body>",
                nav,
                f"<h1>{app_context['product_heading']}</h1>",
                f"<p class=\"muted\">{ui_text(locale, 'site_dashboard_note')}</p>",
                f"<div class=\"card\"><h2>{ui_text(locale, 'site_workflow_areas')}</h2><p>{ui_text(locale, 'site_workflow_areas_hint')}</p></div>",
                (
                    "<div class=\"card\"><h2>"
                    + ("Workflow backbone" if not is_zh_locale(locale) else "主业务流程")
                    + "</h2><ul>"
                    + "".join(
                        f"<li><strong>{step['step']}</strong> {step['label']}</li>"
                        for step in app_context.get("workflow_backbone", [])
                        if isinstance(step, dict)
                    )
                    + "</ul></div>"
                ),
                "<div class=\"card\"><h2>"
                + ui_text(locale, "site_expected_behavior")
                + "</h2><ol><li>"
                + ("Show the right business data" if not is_zh_locale(locale) else "展示正确的业务数据")
                + "</li><li>"
                + ("Capture the required inputs" if not is_zh_locale(locale) else "采集必须输入")
                + "</li><li>"
                + ("Keep the next action explicit" if not is_zh_locale(locale) else "明确下一步操作")
                + "</li></ol></div>",
                "</body></html>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for page in delivery_pages:
        surface_path = site_dir / f"{page['page_id']}.html"
        section_markup = "".join(
            f"<div class=\"card\"><span class=\"pill\">{section['view']}</span><h2>{section['title']}</h2><p>{section['purpose']}</p></div>"
            for section in page["sections"]
        )
        surface_path.write_text(
            "\n".join(
                [
                    f"<!doctype html><html lang=\"{locale}\"><head><meta charset=\"utf-8\" /><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" /><title>{page['page_title']}</title><link rel=\"stylesheet\" href=\"./style.css\" /></head><body>",
                    nav,
                    f"<h1>{page['page_title']}</h1>",
                    f"<p class=\"muted\">{page['subtitle']}</p>",
                    f"<div class=\"card\"><h2>{ui_text(locale, 'site_user_goal')}</h2><p>{page['user_goal']}</p></div>",
                    f"<div class=\"card\"><h2>{ui_text(locale, 'site_primary_cta')}</h2><p>{page['primary_cta']['label']}</p><p class=\"muted\">{page['primary_cta']['hint']}</p></div>",
                    (
                        "<div class=\"card\"><h2>"
                        + ("Information objects" if not is_zh_locale(locale) else "信息对象")
                        + "</h2><p>"
                        + " / ".join(page.get("information_objects", []))
                        + "</p></div>"
                        if page.get("information_objects")
                        else ""
                    ),
                    section_markup,
                    f"<div class=\"card\"><h2>{ui_text(locale, 'site_states')}</h2><ul><li>{page['state_conditions']['loading']}</li><li>{page['state_conditions']['success']}</li><li>{page['state_conditions']['empty']}</li><li>{page['state_conditions']['error']}</li></ul></div>",
                    "</body></html>",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    ia_contract = {
        "mode": mode,
        "locale": locale,
        "surface_provenance": "compiled-surface-contract" if compiled_pages else ("phase1-prototype-spec" if prototype_page_map else "stage04-primary-surfaces"),
        "contract_source": "compiled-surface-contract" if compiled_pages else "fallback-derived",
        "app_context": app_context,
        "prototype_generation_constraints": prototype_constraints,
        "external_executor_brief": external_executor_brief,
        "semantic_disqualifiers": _global_semantic_disqualifiers(
            prototype_constraints=prototype_constraints,
            external_executor_brief=external_executor_brief,
            locale=locale,
        ),
        "contract_rule": "Freeze page-level IA fields before P3 implementation: role, goal, sections, data_required, data_presentation, display_fields, user_inputs, actions_and_transitions, business_state_transitions, and semantic_guardrails.",
        "frontend_experience_contract": app_context.get("frontend_experience_contract", {}),
        "compiled_bindings": compiled_bindings,
        "pages": delivery_pages,
    }
    ia_contract_path.write_text(json.dumps(ia_contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    delivery_contract = {
        "mode": ia_contract["mode"],
        "locale": locale,
        "surface_provenance": ia_contract["surface_provenance"],
        "contract_source": ia_contract["contract_source"],
        "app_context": app_context,
        "prototype_generation_constraints": prototype_constraints,
        "external_executor_brief": external_executor_brief,
        "semantic_disqualifiers": ia_contract["semantic_disqualifiers"],
        "contract_rule": "Use this delivery contract to generate human-usable MVP pages that hide implementation detail while preserving API/data bindings.",
        "frontend_experience_contract": app_context.get("frontend_experience_contract", {}),
        "compiled_bindings": compiled_bindings,
        "pages": delivery_pages,
    }
    delivery_contract_path.write_text(json.dumps(delivery_contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frontend_default_stack = {
        "activated_when": [
            "phase2_ui_prototype_missing",
            "phase2_frontend_stack_not_explicit",
        ],
        "stack": {
            "framework": "react",
            "build_tool": "vite",
            "ui_library": "ant-design",
            "router": "react-router",
            "data_fetching": "tanstack-query",
            "form": "react-hook-form",
            "validation": "zod",
        },
        "delivery_rule": {
            "visual_fidelity": "fallback-low-fidelity-allowed",
            "usability_floor": "must-be-operable",
            "minimum_operable_flow": "at-least-one-cross-page-end-to-end-user-flow",
            "core_route_floor": "every-core-ia-route-must-be-materially-operable",
            "forbidden": [
                "reachability-only-placeholder-page",
                "build-green-without-operable-ui-flow",
                "contract-dump-instead-of-operable-page",
            ],
        },
    }
    frontend_stack_path.write_text(json.dumps(frontend_default_stack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "triggered": triggered,
        "mode": mode,
        "manual_prototype_assets": manual_assets,
        "fallback_artifacts": {
            "ui_prototype_fallback": str(fallback_md_path),
            "ui_wireframes": str(wireframes_path),
            "ui_api_mapping": str(api_mapping_path),
            "ui_ia_contract": str(ia_contract_path),
            "ui_delivery_contract": str(delivery_contract_path),
            "frontend_default_stack": str(frontend_stack_path),
            "ui_site_root": str(site_dir),
            "ui_site_entry": str(site_index_path),
        },
        "alignment": {
            "locale": locale,
            "surface_provenance": ia_contract["surface_provenance"],
            "contract_source": ia_contract["contract_source"],
            "primary_surfaces": primary_surfaces,
            "product_name": app_context.get("product_name", ""),
            "primary_actor": _visibility_text(app_context.get("primary_actor", "")),
            "critical_flow_hints_from_p2": workflow_hints,
            "api_endpoint_count": len(endpoints),
            "api_endpoint_source": endpoint_source,
            "phase1_prototype_spec_path": str(prototype_spec_path) if prototype_spec_path else "",
            "phase1_prototype_spec_present": bool(prototype_spec_path and prototype_spec_path.exists()),
            "phase1_prototype_prompt_pack_path": str(prototype_prompt_pack_path) if prototype_prompt_pack_path else "",
            "phase1_prototype_prompt_pack_present": bool(prototype_prompt_pack_path and prototype_prompt_pack_path.exists()),
            "phase1_interaction_flow_contract_path": str(interaction_flow_contract_path) if interaction_flow_contract_path else "",
            "phase1_interaction_flow_contract_present": bool(interaction_flow_contract_path and interaction_flow_contract_path.exists()),
            "phase1_prototype_page_contract_count": len(prototype_page_contracts),
            "phase1_external_executor_brief_count": len(external_executor_brief),
            "compiled_binding_count": len(compiled_bindings),
        },
        "rule": "When manual prototype is missing, fallback prototype inputs are generated before P3 implementation.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase-3 fallback prototype inputs")
    parser.add_argument("--phase2-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ui-locale", default="zh-CN")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    phase2_root = Path(args.phase2_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    report = generate_ui_prototype_fallback(
        phase2_root=phase2_root,
        output_dir=output_dir,
        stage_04_text=_read(phase2_root / "stage-04-design-convergence-and-delivery-prototype.md"),
        esp_text=_read(phase2_root / "engineering-spec-pack.md"),
        openapi_path=output_dir / "contracts" / "openapi.yaml",
        ui_locale=args.ui_locale,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
