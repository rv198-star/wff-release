#!/usr/bin/env python3
"""
Generate a Stage-05b prototype-interaction-flow-contract artifact from a
page-level prototype-spec authority.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import re
from pathlib import Path

from common.output_language import resolve_output_locale
from phase1.phase1_generate_prototype_spec import (
    read_text,
    render_primary_locale_lines,
    required_value,
    slugify,
    split_roles,
)


def extract_markdown_section(text: str, keyword: str) -> str:
    match = re.search(
        rf"^(##+)\s+[^\n]*{re.escape(keyword)}[^\n]*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return ""
    start = match.start()
    heading_level = len(match.group(1))
    next_heading = re.search(
        rf"^#{{1,{heading_level}}}\s+",
        text[match.end() :],
        flags=re.MULTILINE,
    )
    if next_heading:
        end = match.end() + next_heading.start()
        return text[start:end].strip()
    return text[start:].strip()


def parse_table_rows(section_text: str) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in section_text.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 3:
        return []
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        row = dict(zip(headers, cells))
        if any(str(value).strip() for value in row.values()):
            rows.append(row)
    return rows


def normalize_text(value: str) -> str:
    return str(value or "").strip().strip("`")


def is_dependency_note(value: str) -> bool:
    normalized = normalize_text(value)
    if not normalized:
        return False
    lowered = normalized.casefold()
    return (
        lowered.startswith("depends on ")
        or lowered.startswith("dependent on ")
        or " depends on " in lowered
        or "依赖" in normalized
    )


def strip_support_prefix(value: str) -> str:
    cleaned = normalize_text(value)
    if not cleaned:
        return ""
    cleaned = re.sub(
        r"^(?:support the user in completing|support the action directly|支持用户完成|支持动作直接完成)[:：]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def looks_like_low_information_goal(value: str) -> bool:
    cleaned = strip_support_prefix(value)
    if not cleaned or is_dependency_note(cleaned):
        return True
    lowered = cleaned.casefold()
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
        return False
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    return len(words) <= 3


def intent_candidate_score(value: str, *, page_name: str = "") -> int:
    cleaned = strip_support_prefix(value)
    if not cleaned or is_dependency_note(cleaned):
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
    if looks_like_low_information_goal(cleaned):
        score -= 5
    if page_name and cleaned.casefold() == normalize_text(page_name).casefold():
        score -= 4
    return score


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def page_reference_aliases(value: str) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []

    aliases: list[str] = [normalized]
    stripped_parenthetical = re.sub(r"\s*\([^)]*\)", "", normalized).strip()
    if stripped_parenthetical and stripped_parenthetical != normalized:
        aliases.append(stripped_parenthetical)

    parenthetical_values = re.findall(r"\(([^)]*)\)", normalized)
    for parenthetical in parenthetical_values:
        cleaned = normalize_text(parenthetical)
        if cleaned:
            aliases.append(cleaned)

    if any(separator in normalized for separator in ("+", "/", "／", "→", "->", "|")):
        parts = [
            normalize_text(part)
            for part in re.split(r"\s*(?:\+|/|／|→|->|\|)\s*", normalized)
            if normalize_text(part)
        ]
        aliases.extend(parts)
        if parts:
            aliases.append(parts[0])

    return unique_preserve_order(aliases)


def parse_page_map_rows(prototype_spec_text: str) -> list[dict[str, str]]:
    section = extract_markdown_section(prototype_spec_text, "Page Map")
    rows = parse_table_rows(section)
    if rows:
        return rows

    lines = prototype_spec_text.splitlines()
    in_page_map = False
    current: dict[str, str] = {}
    rows = []
    fields = {
        "page_name",
        "page_role",
        "primary_actor",
        "why_it_exists",
        "page_blueprint_type",
        "route",
        "route_pattern",
    }
    for raw in lines:
        stripped = raw.strip()
        if stripped == "## 4. Page Map" or stripped.startswith("- page_map:"):
            in_page_map = True
            continue
        if in_page_map and stripped.startswith("## ") and "Page Map" not in stripped:
            if current.get("page_name"):
                rows.append(current)
            break
        if not in_page_map:
            continue
        if re.match(r"^\s*-\s+page_\d+:\s*$", raw):
            if current.get("page_name"):
                rows.append(current)
            current = {}
            continue
        field_match = re.match(r"^\s*-\s+([A-Za-z0-9_]+):\s*(.+?)?\s*$", raw.strip())
        if not field_match:
            continue
        field = field_match.group(1).strip()
        if field not in fields:
            continue
        value = (field_match.group(2) or "").strip().strip("`").strip()
        current[field] = value
    if current.get("page_name"):
        rows.append(current)
    return rows


def split_csv(value: str) -> list[str]:
    items: list[str] = []
    for item in str(value or "").split(","):
        cleaned = item.strip().strip("`")
        if cleaned and cleaned != "—":
            items.append(cleaned)
    return items


def parse_main_flow_steps(prototype_spec_text: str) -> list[dict[str, str]]:
    section = extract_markdown_section(prototype_spec_text, "Main Flow")
    if not section:
        return []
    steps: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in section.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if "alternate_paths" in stripped or "route_graph_note" in stripped:
            break
        if re.match(r"^\s*-\s+step_\d+:\s*$", stripped):
            if current:
                steps.append(current)
            current = {}
            continue
        field_match = re.match(r"^\s*-\s+([A-Za-z0-9_]+):\s*(.+?)?\s*$", stripped)
        if not field_match:
            continue
        field = field_match.group(1).strip()
        if field not in {
            "from_page",
            "to_page",
            "user_goal",
            "system_response",
            "context_that_must_survive_navigation",
        }:
            continue
        current[field] = normalize_text(field_match.group(2) or "")
    if current:
        steps.append(current)
    return [step for step in steps if step.get("from_page") and step.get("to_page")]


def parse_surface_pages(prototype_spec_text: str) -> list[dict[str, object]]:
    rows = parse_page_map_rows(prototype_spec_text)
    pages: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        page_id = normalize_text(row.get("page_id") or "")
        page_name = normalize_text(row.get("page_name") or "")
        route = normalize_text(row.get("route") or "")
        page_blueprint_type = normalize_text(row.get("page_blueprint_type") or "")
        primary_actor = normalize_text(row.get("primary_actor") or "")
        allowed_roles = split_roles(str(row.get("allowed_roles") or ""))
        primary_user_goal = normalize_text(row.get("primary_user_goal") or "")
        bound_use_case_ids = split_csv(str(row.get("bound_use_case_ids") or ""))
        business_objects = split_csv(str(row.get("business_objects") or ""))
        required_regions = split_csv(str(row.get("required_regions") or ""))
        entry_conditions = normalize_text(row.get("entry_conditions") or "")
        next_route_candidates = split_csv(str(row.get("next_route_candidates") or ""))
        denied_behavior = normalize_text(row.get("denied_behavior") or "")
        readiness_status = normalize_text(row.get("readiness_status") or "")
        blocked_reason = normalize_text(row.get("blocked_reason") or "")
        primary_action = normalize_text(row.get("primary_action") or "")
        pages.append(
            {
                "page_id": page_id,
                "page_name": page_name,
                "page_slug": slugify(page_name),
                "route": route,
                "page_blueprint_type": page_blueprint_type,
                "primary_actor": primary_actor,
                "allowed_roles": allowed_roles,
                "primary_user_goal": primary_user_goal,
                "bound_use_case_ids": bound_use_case_ids or ["TBD"],
                "business_objects": business_objects,
                "required_regions": required_regions,
                "entry_conditions": entry_conditions,
                "next_route_candidates": next_route_candidates or ["—"],
                "denied_behavior": denied_behavior,
                "readiness_status": readiness_status,
                "blocked_reason": blocked_reason,
                "primary_action": primary_action,
            }
        )
    return pages


def validate_surface_pages(pages: list[dict[str, object]]) -> None:
    if not pages:
        raise SystemExit("Interaction flow contract generation requires a prototype-spec page map")

    invalid_pages: list[str] = []
    for page in pages:
        missing: list[str] = []
        if not str(page.get("page_id") or "").strip():
            missing.append("page_id")
        if not str(page.get("page_name") or "").strip():
            missing.append("page_name")
        if not str(page.get("route") or "").strip():
            missing.append("route")
        if not str(page.get("page_blueprint_type") or "").strip():
            missing.append("page_blueprint_type")
        if not str(page.get("primary_actor") or "").strip():
            missing.append("primary_actor")
        if not page.get("allowed_roles"):
            missing.append("allowed_roles")
        if not str(page.get("primary_user_goal") or "").strip():
            missing.append("primary_user_goal")
        if not page.get("bound_use_case_ids"):
            missing.append("bound_use_case_ids")
        if not page.get("business_objects"):
            missing.append("business_objects")
        if not page.get("required_regions"):
            missing.append("required_regions")
        if not page.get("next_route_candidates"):
            missing.append("next_route_candidates")
        if not str(page.get("denied_behavior") or "").strip():
            missing.append("denied_behavior")
        if not str(page.get("readiness_status") or "").strip():
            missing.append("readiness_status")
        if not str(page.get("primary_action") or "").strip():
            missing.append("primary_action")
        if missing:
            invalid_pages.append(
                f"{page.get('page_name') or page.get('page_id') or 'unknown-page'}: missing {', '.join(missing)}"
            )
    if invalid_pages:
        raise SystemExit(
            "Interaction flow contract generation requires complete S5 surface authority; "
            + " ; ".join(invalid_pages)
        )


def visibility_rule(page: dict[str, object]) -> str:
    roles = [role for role in page["allowed_roles"] if role and role != "TBD"]
    if not roles:
        return "always_visible"
    return "role in [" + ",".join(roles) + "]"


def infer_action_type(primary_action: str, blueprint: str) -> str:
    blob = f"{primary_action} {blueprint}".lower()
    if any(token in blob for token in ("payment", "pay", "结算", "收款")):
        return "record_payment"
    if any(token in blob for token in ("approve", "continue", "decision", "review", "record decision", "review-decision")):
        return "submit"
    if any(token in blob for token in ("assign", "reserve", "schedule")):
        return "assign"
    if any(token in blob for token in ("check-in", "check in", "登记")):
        return "check_in"
    if any(token in blob for token in ("create", "register", "activate", "setup", "configure")):
        return "create"
    if any(token in blob for token in ("update", "edit", "save")):
        return "update"
    if "review-decision" in blob:
        return "submit"
    return "transition_status"


def work_area_element_type(page_blueprint_type: str) -> str:
    mapping = {
        "setup-flow": "form",
        "execution-workbench": "action-bar",
        "review-decision": "action-bar",
        "dashboard": "action-bar",
        "detail-view": "form",
        "record-workbench": "form",
        "analysis-board": "form",
        "decision-workbench": "action-bar",
    }
    return mapping.get(page_blueprint_type, "form")


def data_view_element_type(page_blueprint_type: str) -> str:
    mapping = {
        "dashboard": "table",
        "execution-workbench": "table",
        "review-decision": "detail-panel",
        "analysis-board": "detail-panel",
        "decision-workbench": "detail-panel",
        "setup-flow": "detail-panel",
        "record-workbench": "detail-panel",
        "detail-view": "detail-panel",
    }
    return mapping.get(page_blueprint_type, "detail-panel")


def interaction_pattern_for_action(action_type: str) -> str:
    mapping = {
        "load_context": "detail-inspect",
        "create": "create-record",
        "update": "edit-record",
        "assign": "handoff-and-continue",
        "submit": "handoff-and-continue",
        "record_payment": "settlement-entry",
        "check_in": "status-transition",
        "transition_status": "status-transition",
    }
    return mapping.get(action_type, "detail-inspect")


def next_route(page: dict[str, object]) -> str:
    routes = [route for route in page["next_route_candidates"] if route and route != "—"]
    return routes[0] if routes else ""


def lifecycle_blocked_rule(page: dict[str, object]) -> str:
    if page["readiness_status"] != "ready":
        return "block-if-page-contract-is-not-ready"
    return "block-if-required-page-context-is-missing"


def primary_blocked_rule(page: dict[str, object]) -> str:
    if page["readiness_status"] != "ready":
        return "block-if-page-contract-is-not-ready"
    return "block-if-entry-conditions-or-upstream-context-are-not-satisfied"


def interaction_readiness(page: dict[str, object]) -> tuple[str, str]:
    status = str(page["readiness_status"]).strip() or "review-bound"
    reason = str(page["blocked_reason"]).strip()
    if status == "ready":
        return "ready", ""
    return status, reason or "page-level surface contract is not fully ready"


def handoff_context_fields(source_page: dict[str, object], target_page: dict[str, object]) -> list[str]:
    shared = [
        item
        for item in source_page["business_objects"]
        if item in target_page["business_objects"]
    ]
    if shared:
        return [f"{slugify(item).replace('-', '_')}_context" for item in shared[:3]]
    return ["workflow_context"]


def page_lookup_by_name(pages: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    lookup: dict[str, list[dict[str, object]]] = {}
    for page in pages:
        raw_aliases = [
            *page_reference_aliases(str(page["page_name"])),
            normalize_text(str(page.get("route") or "")),
            normalize_text(str(page.get("page_slug") or "")),
        ]
        for alias in unique_preserve_order([item for item in raw_aliases if item]):
            key = alias.casefold()
            if not key:
                continue
            bucket = lookup.setdefault(key, [])
            if page not in bucket:
                bucket.append(page)
    return lookup


def flow_goal_hints_by_page(flow_steps: list[dict[str, str]]) -> dict[str, list[str]]:
    hints: dict[str, list[str]] = {}
    for step in flow_steps:
        source_page = normalize_text(step.get("from_page", ""))
        if not source_page:
            continue
        values = unique_preserve_order(
            [
                strip_support_prefix(step.get("user_goal", "")),
                strip_support_prefix(step.get("system_response", "")),
            ]
        )
        if not values:
            continue
        for alias in page_reference_aliases(source_page):
            key = alias.casefold()
            if not key:
                continue
            bucket = hints.setdefault(key, [])
            for value in values:
                if value and value not in bucket:
                    bucket.append(value)
    return hints


def page_goal_hints(page: dict[str, object], flow_goal_hints: dict[str, list[str]]) -> list[str]:
    collected: list[str] = []
    for alias in [
        *page_reference_aliases(str(page.get("page_name") or "")),
        normalize_text(str(page.get("route") or "")),
        normalize_text(str(page.get("page_slug") or "")),
    ]:
        collected.extend(flow_goal_hints.get(alias.casefold(), []))
    return unique_preserve_order(collected)


def intent_from_entry_conditions(page: dict[str, object]) -> str:
    entry_conditions = normalize_text(str(page.get("entry_conditions") or ""))
    if not entry_conditions or is_dependency_note(entry_conditions):
        return ""
    if re.search(r"(?:^|[^A-Za-z0-9])(?:[A-Za-z0-9_]*id)(?:[^A-Za-z0-9]|$)", entry_conditions, flags=re.IGNORECASE):
        return f"using {entry_conditions}"
    if any(separator in entry_conditions for separator in (",", "/", ";")):
        return f"using {entry_conditions}"
    if len(entry_conditions.split()) <= 8:
        return f"when {entry_conditions}"
    return ""


def synthesize_user_intent(page: dict[str, object], flow_goal_hints: dict[str, list[str]]) -> str:
    page_name = normalize_text(str(page.get("page_name") or ""))
    primary_action = strip_support_prefix(str(page.get("primary_action") or ""))
    primary_user_goal = strip_support_prefix(str(page.get("primary_user_goal") or ""))
    entry_hint = intent_from_entry_conditions(page)
    flow_candidates = page_goal_hints(page, flow_goal_hints)
    best_flow_value = ""
    best_flow_score = -10_000
    for candidate in flow_candidates:
        score = intent_candidate_score(candidate, page_name=page_name)
        if score > best_flow_score:
            best_flow_value = strip_support_prefix(candidate)
            best_flow_score = score
    if best_flow_value and best_flow_score >= 8:
        return best_flow_value

    candidates = [
        primary_action,
        primary_user_goal,
    ]
    if primary_action and entry_hint:
        candidates.append(f"{primary_action} {entry_hint}")
    if primary_user_goal and entry_hint:
        candidates.append(f"{primary_user_goal} {entry_hint}")
    if page_name and primary_action and not looks_like_low_information_goal(primary_action):
        candidates.append(f"advance {page_name} by completing {primary_action}")
    if page_name and entry_hint:
        candidates.append(f"advance {page_name} {entry_hint}")

    best_value = ""
    best_score = -10_000
    for candidate in unique_preserve_order(candidates):
        score = intent_candidate_score(candidate, page_name=page_name)
        if score > best_score:
            best_value = strip_support_prefix(candidate)
            best_score = score
    if best_value:
        return best_value
    return primary_action or primary_user_goal or page_name or "complete the current workflow step"


def resolve_page_reference(
    raw_reference: str,
    pages_by_name: dict[str, list[dict[str, object]]],
) -> dict[str, object] | None:
    for alias in page_reference_aliases(raw_reference):
        matches = pages_by_name.get(alias.casefold(), [])
        if len(matches) == 1:
            return matches[0]
    return None


def build_interaction_rows(
    pages: list[dict[str, object]],
    flow_goal_hints: dict[str, list[str]],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    rows: list[dict[str, str]] = []
    primary_action_interactions: dict[str, str] = {}
    for page in pages:
        status, blocked_reason = interaction_readiness(page)
        use_case_id = next((value for value in page["bound_use_case_ids"] if value and value != "TBD"), "TBD")
        page_slug = str(page["page_slug"])

        if "context_header" in page["required_regions"]:
            rows.append(
                {
                    "interaction_id": f"{page_slug}.load-context-header",
                    "page_id": str(page["page_id"]),
                    "region": "context_header",
                    "element_type": "summary-card",
                    "interaction_pattern": "detail-inspect",
                    "trigger_kind": "page_load",
                    "action_type": "load_context",
                    "user_intent": f"Review context and role/status summary for {page['page_name']}",
                    "visibility_rule": visibility_rule(page),
                    "blocked_rule": lifecycle_blocked_rule(page),
                    "success_state": "render-context-summary",
                    "error_state": "show-context-load-error",
                    "next_route": "",
                    "use_case_id": use_case_id,
                    "readiness_status": status,
                    "blocked_reason": blocked_reason,
                }
            )

        if "data_view" in page["required_regions"]:
            rows.append(
                {
                    "interaction_id": f"{page_slug}.load-data-view",
                    "page_id": str(page["page_id"]),
                    "region": "data_view",
                    "element_type": data_view_element_type(str(page["page_blueprint_type"])),
                    "interaction_pattern": "detail-inspect",
                    "trigger_kind": "page_load",
                    "action_type": "load_context",
                    "user_intent": f"Review decision-support data required on {page['page_name']}",
                    "visibility_rule": visibility_rule(page),
                    "blocked_rule": lifecycle_blocked_rule(page),
                    "success_state": "render-page-data-view",
                    "error_state": "show-data-view-load-error",
                    "next_route": "",
                    "use_case_id": use_case_id,
                    "readiness_status": status,
                    "blocked_reason": blocked_reason,
                }
            )

        action_type = infer_action_type(str(page["primary_action"]), str(page["page_blueprint_type"]))
        action_interaction_id = f"{page_slug}.{slugify(str(page['primary_action'])) or 'primary-action'}"
        primary_action_interactions[str(page["page_id"])] = action_interaction_id
        rows.append(
            {
                "interaction_id": action_interaction_id,
                "page_id": str(page["page_id"]),
                "region": "work_area",
                "element_type": work_area_element_type(str(page["page_blueprint_type"])),
                "interaction_pattern": interaction_pattern_for_action(action_type),
                "trigger_kind": "user_action",
                "action_type": action_type,
                "user_intent": synthesize_user_intent(page, flow_goal_hints),
                "visibility_rule": visibility_rule(page),
                "blocked_rule": primary_blocked_rule(page),
                "success_state": "advance-workflow-or-refresh-page-state",
                "error_state": "show-inline-action-error-and-preserve-context",
                "next_route": next_route(page),
                "use_case_id": use_case_id,
                "readiness_status": status,
                "blocked_reason": blocked_reason,
            }
        )
    return rows, primary_action_interactions


def flow_readiness(source_page: dict[str, object], target_page: dict[str, object]) -> tuple[str, str]:
    statuses = {str(source_page["readiness_status"]), str(target_page["readiness_status"])}
    reasons = [str(source_page["blocked_reason"]).strip(), str(target_page["blocked_reason"]).strip()]
    joined_reason = "; ".join(reason for reason in reasons if reason)
    if "blocked" in statuses:
        return "blocked", joined_reason or "source or target page is blocked"
    if "review-bound" in statuses or "TBD" in source_page["bound_use_case_ids"]:
        reason = joined_reason or "flow still depends on review-bound page-level authority"
        if "review-bound" not in reason:
            reason = f"review-bound: {reason}"
        return "review-bound", reason
    return "ready", ""


def transition_condition(source_page: dict[str, object], target_page: dict[str, object]) -> str:
    shared = handoff_context_fields(source_page, target_page)
    if shared and shared != ["workflow_context"]:
        return f"{source_page['primary_action']} completed and {', '.join(shared)} preserved"
    return f"{source_page['primary_action']} completed and required downstream context preserved"


def resolve_flow_pages(
    step: dict[str, str],
    pages_by_name: dict[str, list[dict[str, object]]],
) -> tuple[dict[str, object], dict[str, object]]:
    source_page = resolve_page_reference(step.get("from_page", ""), pages_by_name)
    target_page = resolve_page_reference(step.get("to_page", ""), pages_by_name)
    if source_page is None:
        raise SystemExit(f"Flow Contract generation could not resolve from_page: {step.get('from_page', '')}")
    if target_page is None:
        raise SystemExit(f"Flow Contract generation could not resolve to_page: {step.get('to_page', '')}")
    return source_page, target_page


def build_flow_rows(
    flow_steps: list[dict[str, str]],
    pages: list[dict[str, object]],
    primary_action_interactions: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not flow_steps:
        raise SystemExit("Interaction flow contract generation requires explicit main flow authority in prototype-spec")

    pages_by_name = page_lookup_by_name(pages)
    for index, step in enumerate(flow_steps, start=1):
        source_page, target_page = resolve_flow_pages(step, pages_by_name)
        use_case_id = next((value for value in source_page["bound_use_case_ids"] if value and value != "TBD"), "TBD")
        status, blocked_reason = flow_readiness(source_page, target_page)
        flow_id_suffix = slugify(use_case_id.replace("uc.", "") if use_case_id != "TBD" else "first-wave-mainline")
        handoff_fields = normalize_text(step.get("context_that_must_survive_navigation", "")) or ", ".join(
            handoff_context_fields(source_page, target_page)
        )
        transition = normalize_text(step.get("system_response", "")) or transition_condition(source_page, target_page)
        rows.append(
            {
                "flow_id": f"flow.{flow_id_suffix}",
                "use_case_id": use_case_id,
                "step_id": f"step.{slugify(str(source_page['page_name']))}-to-{slugify(str(target_page['page_name']))}",
                "step_order": str(index),
                "from_page_id": str(source_page["page_id"]),
                "from_interaction_id": primary_action_interactions.get(str(source_page["page_id"]), "TBD"),
                "transition_condition": transition,
                "next_page_id": str(target_page["page_id"]),
                "handoff_context_fields": handoff_fields,
                "failure_route": str(source_page["route"]),
                "termination_condition": (
                    f"workflow goal reached on {target_page['page_name']}"
                    if index == len(flow_steps)
                    else "—"
                ),
                "readiness_status": status,
                "blocked_reason": blocked_reason,
            }
        )
    route_lookup = {
        normalize_text(str(page.get("route") or "")): page
        for page in pages
        if normalize_text(str(page.get("route") or ""))
    }
    existing_pairs = {
        (str(row.get("from_page_id") or "").strip(), str(row.get("next_page_id") or "").strip())
        for row in rows
        if str(row.get("from_page_id") or "").strip() and str(row.get("next_page_id") or "").strip()
    }
    step_order = len(rows)
    for page in pages:
        source_page_id = str(page.get("page_id") or "").strip()
        next_routes = [
            normalize_text(str(route))
            for route in page.get("next_route_candidates", [])
            if normalize_text(str(route)) and normalize_text(str(route)) != "—"
        ]
        if not source_page_id or not next_routes:
            continue
        target_page = next((route_lookup.get(route) for route in next_routes if route_lookup.get(route) is not None), None)
        if target_page is None:
            continue
        target_page_id = str(target_page.get("page_id") or "").strip()
        if not target_page_id or (source_page_id, target_page_id) in existing_pairs:
            continue
        use_case_id = next((value for value in page["bound_use_case_ids"] if value and value != "TBD"), "TBD")
        status, blocked_reason = flow_readiness(page, target_page)
        flow_id_suffix = slugify(use_case_id.replace("uc.", "") if use_case_id != "TBD" else f"{page['page_slug']}-route")
        handoff_fields = ", ".join(handoff_context_fields(page, target_page))
        step_order += 1
        rows.append(
            {
                "flow_id": f"flow.{flow_id_suffix}",
                "use_case_id": use_case_id,
                "step_id": f"step.{slugify(str(page['page_name']))}-to-{slugify(str(target_page['page_name']))}",
                "step_order": str(step_order),
                "from_page_id": source_page_id,
                "from_interaction_id": primary_action_interactions.get(source_page_id, "TBD"),
                "transition_condition": transition_condition(page, target_page),
                "next_page_id": target_page_id,
                "handoff_context_fields": handoff_fields,
                "failure_route": str(page["route"]),
                "termination_condition": (
                    f"workflow goal reached on {target_page['page_name']}"
                    if not [route for route in target_page.get("next_route_candidates", []) if normalize_text(str(route)) and normalize_text(str(route)) != "—"]
                    else "—"
                ),
                "readiness_status": status,
                "blocked_reason": blocked_reason,
            }
        )
        existing_pairs.add((source_page_id, target_page_id))
    return rows


def render_lines(
    prototype_spec_path: Path,
    version: str,
    owner: str,
    pages: list[dict[str, object]],
    interaction_rows: list[dict[str, str]],
    flow_rows: list[dict[str, str]],
) -> list[str]:
    lines: list[str] = [
        "# Prototype Interaction Flow Contract",
        "",
        "## 1. Metadata",
        "- document_name: `prototype-interaction-flow-contract.md`",
        "- artifact_id: `P1-S05b-IFC-001`",
        f"- version: `{version}`",
        "- status:",
        "  - `review`",
        f"- owner: `{owner}`",
        "- derived_from:",
        f"  - `{prototype_spec_path.name}`",
        "  - `P1-S05-SPEC-001`",
        "",
        "## 2. Objective and Authority",
        "- authority_role:",
        "  - `P1 Interaction Matrix + Flow Contract authority`",
        "- upstream_dependency:",
        "  - `prototype-spec.md` remains the page-level Surface Matrix authority",
        "- downstream_usage_rule:",
        "  - P2 may enrich `input_schema_ref / display_field_set / validation_rules / enabled_rule`, but must not rewrite P1-owned interaction or flow semantics silently.",
        "- S5_to_S5b_boundary:",
        "  - `S5` owns page-level route, blueprint, role, region, object, and page readiness truth.",
        "  - `S5b` owns interaction-level product-side semantics and cross-page flow semantics.",
        "  - `prototype-prompt-pack.md` may supplement visual intent only; it must not replace S5 or S5b authority.",
        "",
        "## 3. Interaction Matrix",
        "| interaction_id | page_id | region | element_type | interaction_pattern | trigger_kind | action_type | user_intent | visibility_rule | blocked_rule | success_state | error_state | next_route | use_case_id | readiness_status | blocked_reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in interaction_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    required_value(str(row["interaction_id"])),
                    required_value(str(row["page_id"])),
                    required_value(str(row["region"])),
                    required_value(str(row["element_type"])),
                    required_value(str(row["interaction_pattern"])),
                    required_value(str(row["trigger_kind"])),
                    required_value(str(row["action_type"])),
                    required_value(str(row["user_intent"])),
                    required_value(str(row["visibility_rule"])),
                    required_value(str(row["blocked_rule"])),
                    required_value(str(row["success_state"])),
                    required_value(str(row["error_state"])),
                    required_value(str(row["next_route"]), "—"),
                    required_value(str(row["use_case_id"])),
                    required_value(str(row["readiness_status"])),
                    required_value(str(row["blocked_reason"]), "—"),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 4. Flow Contract",
            "| flow_id | use_case_id | step_id | step_order | from_page_id | from_interaction_id | transition_condition | next_page_id | handoff_context_fields | failure_route | termination_condition | readiness_status | blocked_reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in flow_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    required_value(str(row["flow_id"])),
                    required_value(str(row["use_case_id"])),
                    required_value(str(row["step_id"])),
                    required_value(str(row["step_order"])),
                    required_value(str(row["from_page_id"])),
                    required_value(str(row["from_interaction_id"])),
                    required_value(str(row["transition_condition"])),
                    required_value(str(row["next_page_id"])),
                    required_value(str(row["handoff_context_fields"])),
                    required_value(str(row["failure_route"])),
                    required_value(str(row["termination_condition"]), "—"),
                    required_value(str(row["readiness_status"])),
                    required_value(str(row["blocked_reason"]), "—"),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 5. Product-Side Boundary Notes",
            "- P1-owned interaction fields:",
            "  - `interaction_id / page_id / region / element_type / interaction_pattern / trigger_kind / action_type / user_intent / visibility_rule / blocked_rule / success_state / error_state / next_route / readiness_status / blocked_reason`",
            "- P1-owned flow fields:",
            "  - `use_case_id / flow_id / step_id / step_order / from_page_id / from_interaction_id / transition_condition / next_page_id / handoff_context_fields / failure_route / termination_condition / readiness_status / blocked_reason`",
            "- P2-owned later enrichment fields (not authored here):",
            "  - `input_schema_ref / display_field_set / validation_rules / enabled_rule`",
            "",
            "## 6. Readiness and Honesty",
            "- readiness_policy:",
            "  - lifecycle interactions for `context_header / data_view` must remain explicit when those regions are required by S5.",
            "  - any interaction or flow derived from a `review-bound` or `blocked` page must carry that readiness state forward instead of silently upgrading to `ready`.",
            "  - if a page cannot be explicitly bound to a usable `use_case_id`, the downstream interaction/flow rows must remain `review-bound` or `blocked` with a concrete reason.",
        ]
    )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Stage-05b interaction + flow contract artifact")
    parser.add_argument("--prototype-spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--owner", default="Codex Stage-05b interaction-flow-contract generator")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    args = parser.parse_args()

    prototype_spec_path = Path(args.prototype_spec).resolve()
    output_path = Path(args.output).resolve()
    locale = resolve_output_locale(args.output_locale)

    prototype_spec_text = read_text(prototype_spec_path)
    pages = parse_surface_pages(prototype_spec_text)
    validate_surface_pages(pages)
    flow_steps = parse_main_flow_steps(prototype_spec_text)
    flow_goal_hints = flow_goal_hints_by_page(flow_steps)

    interaction_rows, primary_action_interactions = build_interaction_rows(pages, flow_goal_hints)
    flow_rows = build_flow_rows(flow_steps, pages, primary_action_interactions)

    lines = render_lines(
        prototype_spec_path=prototype_spec_path,
        version=args.version,
        owner=args.owner,
        pages=pages,
        interaction_rows=interaction_rows,
        flow_rows=flow_rows,
    )
    rendered = render_primary_locale_lines(
        lines,
        output_path.name,
        locale,
        preserve_table_body_literals=True,
    )
    output_path.write_text("\n".join(rendered).rstrip() + "\n", encoding="utf-8")
    print(f"prototype_interaction_flow_contract: {output_path}")
    print(f"prototype_spec: {prototype_spec_path}")
    print("FINAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
