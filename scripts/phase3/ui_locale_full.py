#!/usr/bin/env python3
"""
Full locale helpers for Phase-3 fallback/UI generation support.
"""

from __future__ import annotations

import re
from typing import Any

from common.script_data_assets import load_script_json_asset


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


WFF_SCRIPT_DATA_ASSETS = ("scripts/phase3/data/ui-locale-copy.json",)


def _load_ui_locale_copy() -> dict[str, Any]:
    loaded = load_script_json_asset(__file__, "ui-locale-copy.json")
    return loaded if isinstance(loaded, dict) else {}


_UI_LOCALE_COPY = _load_ui_locale_copy()

UI_TEXT: dict[str, dict[str, str]] = {
    str(locale): {str(key): str(value) for key, value in entries.items()}
    for locale, entries in dict(_UI_LOCALE_COPY.get("ui_text", {})).items()
    if isinstance(entries, dict)
}
SURFACE_TITLE_MAP: dict[str, str] = {
    str(key): str(value)
    for key, value in dict(_UI_LOCALE_COPY.get("surface_title_map", {})).items()
}
INFORMATION_OBJECT_MAP: dict[str, str] = {
    str(key): str(value)
    for key, value in dict(_UI_LOCALE_COPY.get("information_object_map", {})).items()
}
PAGE_ROLE_EYEBROW: dict[str, dict[str, str]] = {
    str(locale): {str(key): str(value) for key, value in entries.items()}
    for locale, entries in dict(_UI_LOCALE_COPY.get("page_role_eyebrow", {})).items()
    if isinstance(entries, dict)
}
PAGE_ROLE_LABEL: dict[str, dict[str, str]] = {
    str(locale): {str(key): str(value) for key, value in entries.items()}
    for locale, entries in dict(_UI_LOCALE_COPY.get("page_role_label", {})).items()
    if isinstance(entries, dict)
}
VIEW_LABEL: dict[str, dict[str, str]] = {
    str(locale): {str(key): str(value) for key, value in entries.items()}
    for locale, entries in dict(_UI_LOCALE_COPY.get("view_label", {})).items()
    if isinstance(entries, dict)
}
FIELD_LABEL_MAP: dict[str, dict[str, str]] = {
    str(locale): {str(key): str(value) for key, value in entries.items()}
    for locale, entries in dict(_UI_LOCALE_COPY.get("field_label_map", {})).items()
    if isinstance(entries, dict)
}
SURFACE_COPY_DEFAULTS: dict[str, dict[str, dict[str, str]]] = {
    str(locale): {
        str(role): {str(key): str(value) for key, value in copy.items()}
        for role, copy in entries.items()
        if isinstance(copy, dict)
    }
    for locale, entries in dict(_UI_LOCALE_COPY.get("surface_copy_defaults", {})).items()
    if isinstance(entries, dict)
}

def normalize_ui_locale(locale: str | None) -> str:
    candidate = str(locale or "").strip().lower()
    if candidate.startswith("zh"):
        return "zh-CN"
    return "en"


def is_zh_locale(locale: str | None) -> bool:
    return normalize_ui_locale(locale) == "zh-CN"


def infer_ui_locale(*values: object, preferred: str | None = None) -> str:
    if preferred and str(preferred).strip().lower() not in {"", "auto"}:
        return normalize_ui_locale(preferred)
    cjk_count = 0
    for value in values:
        cjk_count += len(_CJK_RE.findall(str(value or "")))
    return "zh-CN" if cjk_count >= 6 else "en"


def ui_text(locale: str | None, key: str, **kwargs: object) -> str:
    normalized = normalize_ui_locale(locale)
    template = UI_TEXT.get(normalized, UI_TEXT["en"]).get(key) or UI_TEXT["en"][key]
    return template.format(**kwargs)


def _fallback_humanize_identifier(value: str) -> str:
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


def normalize_inline_locale_variants(text: str, locale: str | None) -> str:
    candidate = str(text or "").strip()
    if not candidate:
        return ""

    def choose_side(match: re.Match[str]) -> str:
        left = match.group(1).strip()
        right = match.group(2).strip()
        left_has_cjk = bool(_CJK_RE.search(left))
        right_has_cjk = bool(_CJK_RE.search(right))
        if left_has_cjk == right_has_cjk:
            return match.group(0)
        if is_zh_locale(locale):
            return left if left_has_cjk else right
        return right if left_has_cjk else left

    normalized = re.sub(r"([^()]{1,48})\s*\(([^()]{1,48})\)", choose_side, candidate)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_role_display_name(value: str, locale: str | None) -> str:
    candidate = normalize_inline_locale_variants(value, locale).strip().strip("`")
    if not candidate:
        return ""
    if re.fullmatch(r"[a-z0-9 _/\-]+", candidate):
        candidate = candidate.replace("_", " ").replace("/", " ").replace("-", " ")
        return re.sub(r"\s+", " ", candidate).strip()
    if re.fullmatch(r"[A-Za-z0-9 _/\-]+", candidate) and ("_" in candidate or "-" in candidate):
        candidate = _fallback_humanize_identifier(candidate.replace("/", " "))
    return re.sub(r"\s+", " ", candidate).strip()


def normalize_surface_display_title(
    surface: str,
    locale: str | None,
    *,
    page_role: str = "",
    business_objects: list[str] | None = None,
) -> str:
    candidate = normalize_inline_locale_variants(localize_surface_title(surface, locale), locale).strip().strip("`")
    if not candidate:
        candidate = str(surface or "").strip()
    candidate = re.sub(r"\bworkspace\b\s*$", "", candidate, flags=re.IGNORECASE).strip(" -/")
    lowered = candidate.casefold()
    if any(token in lowered for token in ("cross-module", "handoff")) and business_objects:
        object_label = next(
            (
                normalize_inline_locale_variants(localize_information_object(item, locale), locale).strip()
                for item in business_objects
                if str(item).strip()
            ),
            "",
        )
        if object_label:
            if is_zh_locale(locale):
                suffix = "队列" if page_role in {"workspace", "list", "workflow"} else "详情"
                candidate = f"{object_label}{suffix}"
            else:
                suffix = "Queue" if page_role in {"workspace", "list", "workflow"} else "Detail"
                candidate = f"{object_label} {suffix}"
    if re.fullmatch(r"[A-Za-z0-9 &/_\-]+", candidate) and (
        candidate.lower() == candidate or "_" in candidate or "-" in candidate
    ):
        candidate = _fallback_humanize_identifier(candidate.replace("&", " ").replace("/", " "))
    return re.sub(r"\s+", " ", candidate).strip() or str(surface or "").strip()


def localize_surface_title(surface: str, locale: str | None) -> str:
    if not is_zh_locale(locale):
        return surface
    return SURFACE_TITLE_MAP.get(str(surface).strip(), str(surface).strip())


def localize_information_object(value: str, locale: str | None) -> str:
    candidate = str(value).strip()
    if not candidate or not is_zh_locale(locale):
        return candidate
    return INFORMATION_OBJECT_MAP.get(candidate, candidate)


def ui_field_label(field: str, locale: str | None) -> str:
    normalized = normalize_ui_locale(locale)
    candidate = str(field or "").strip()
    if not candidate:
        return "Field" if normalized == "en" else "字段"
    mapped = FIELD_LABEL_MAP.get(normalized, FIELD_LABEL_MAP["en"]).get(candidate)
    if mapped:
        return mapped
    return _fallback_humanize_identifier(candidate)


def page_role_eyebrow(page_role: str, locale: str | None) -> str:
    normalized = normalize_ui_locale(locale)
    return PAGE_ROLE_EYEBROW.get(normalized, PAGE_ROLE_EYEBROW["en"]).get(page_role, "Workflow step" if normalized == "en" else "流程步骤")


def page_role_label(page_role: str, locale: str | None) -> str:
    normalized = normalize_ui_locale(locale)
    return PAGE_ROLE_LABEL.get(normalized, PAGE_ROLE_LABEL["en"]).get(page_role, page_role)


def view_label(view: str, locale: str | None) -> str:
    normalized = normalize_ui_locale(locale)
    return VIEW_LABEL.get(normalized, VIEW_LABEL["en"]).get(view, view)


def _surface_copy_defaults(page_role: str, locale: str | None) -> dict[str, str]:
    normalized = normalize_ui_locale(locale)
    role_defaults = SURFACE_COPY_DEFAULTS.get(normalized, SURFACE_COPY_DEFAULTS.get("en", {}))
    fallback = role_defaults.get("detail", {})
    return dict(role_defaults.get(page_role, fallback))

def surface_shell_copy(surface: str, page_role: str, locale: str | None) -> dict[str, str]:
    lowered = str(surface or "").lower()
    copy = _surface_copy_defaults(page_role, locale)
    zh = is_zh_locale(locale)
    if "onboarding" in lowered or "setup" in lowered or any(token in surface for token in ("接入", "范围", "配置")):
        copy.update(
            {
                "selectors_panel_title": "当前接入范围" if zh else "Current setup scope",
                "work_area_title": "范围配置" if zh else "Scope configuration",
                "work_area_hint": "先完成租户校验，再录入范围信息并启动观测。"
                if zh
                else "Validate the tenant first, then capture the scope inputs and start observation.",
                "current_step_label": "配置步骤" if zh else "Setup step",
                "workflow_steps_title": "范围接入流程" if zh else "Scope setup flow",
                "workflow_steps_hint": "按顺序完成租户校验、范围创建、边界确认和观测启动。"
                if zh
                else "Complete tenant validation, scope creation, boundary review, and observation start in order.",
                "current_data_title": "当前配置结果" if zh else "Current setup state",
                "next_steps_title": "配置完成后" if zh else "After setup",
                "pending_live_data": "等待配置结果" if zh else "Pending setup data",
            }
        )
        return copy
    if "overview" in lowered or "findings" in lowered or any(token in surface for token in ("总览", "发现")):
        copy.update(
            {
                "selectors_panel_title": "当前查看范围" if zh else "Current findings scope",
                "work_area_title": "发现检视与筛选" if zh else "Findings review and filtering",
                "work_area_hint": "先定位当前范围与观测周期，再切换发现、任务和竞品背景。"
                if zh
                else "Set the active scope and observation run first, then pivot across findings, tasks, and competitor context.",
                "current_step_label": "查看步骤" if zh else "Review step",
                "workflow_steps_title": "发现处理步骤" if zh else "Findings handling steps",
                "workflow_steps_hint": "先加载发现，再按需查看任务、竞品快照和审计轨迹。"
                if zh
                else "Load findings first, then inspect tasks, competitor snapshots, and audit evidence as needed.",
                "current_data_title": "当前发现与任务" if zh else "Current findings and tasks",
                "next_steps_title": "查看或刷新后" if zh else "After review or refresh",
                "pending_live_data": "等待发现数据" if zh else "Pending findings data",
            }
        )
        return copy
    if "recommendation" in lowered or any(token in surface for token in ("建议", "导出")):
        copy.update(
            {
                "selectors_panel_title": "当前建议范围" if zh else "Current recommendation scope",
                "work_area_title": "建议处理与任务导出" if zh else "Recommendation handling and task export",
                "work_area_hint": "围绕单个发现完成诊断、建议冻结和任务导出。"
                if zh
                else "Handle one finding from diagnosis through recommendation freeze and task export.",
                "current_step_label": "处理步骤" if zh else "Handling step",
                "workflow_steps_title": "建议处置步骤" if zh else "Recommendation handling steps",
                "workflow_steps_hint": "先查看发现详情，再冻结建议并导出任务。"
                if zh
                else "Inspect the finding first, then freeze the recommendation and export the task.",
                "current_data_title": "当前建议详情" if zh else "Current recommendation detail",
                "next_steps_title": "每次处理后" if zh else "After each decision",
                "pending_live_data": "等待建议数据" if zh else "Pending recommendation data",
            }
        )
        return copy
    if "task" in lowered or "任务" in surface:
        copy.update(
            {
                "selectors_panel_title": "当前任务范围" if zh else "Current task scope",
                "work_area_title": "任务执行更新" if zh else "Task execution update",
                "work_area_hint": "保持任务状态、执行证据和阻塞原因在同一工作面里更新。"
                if zh
                else "Update task state, execution evidence, and blocked reasons in one working surface.",
                "current_step_label": "执行步骤" if zh else "Execution step",
                "workflow_steps_title": "任务推进步骤" if zh else "Task progression steps",
                "workflow_steps_hint": "先加载任务，再提交状态更新并确认审计回执。"
                if zh
                else "Load the task board first, then submit the update and confirm the audit receipt.",
                "current_data_title": "当前任务状态" if zh else "Current task state",
                "next_steps_title": "每次更新后" if zh else "After each update",
                "pending_live_data": "等待任务数据" if zh else "Pending task data",
            }
        )
        return copy
    if "review" in lowered or any(token in surface for token in ("审核", "继续", "修订")):
        copy.update(
            {
                "selectors_panel_title": "当前审核范围" if zh else "Current review scope",
                "work_area_title": "审核决策" if zh else "Review decision",
                "work_area_hint": "先冻结当前周期输入，再查看审核结论与审计证据。"
                if zh
                else "Freeze the cycle inputs first, then inspect the review outcome and audit evidence.",
                "current_step_label": "审核步骤" if zh else "Review step",
                "workflow_steps_title": "审核闭环步骤" if zh else "Review closure steps",
                "workflow_steps_hint": "先生成审核报告，再查看审计证据并决定后续处理。"
                if zh
                else "Generate the review report first, then inspect the audit evidence and decide the follow-up.",
                "current_data_title": "当前审核结果" if zh else "Current review outcome",
                "next_steps_title": "提交后" if zh else "After submission",
                "pending_live_data": "等待审核结果" if zh else "Pending review data",
            }
        )
        return copy
    return copy


def surface_success_copy(surface: str, page_role: str, locale: str | None) -> dict[str, str]:
    localized_surface = localize_surface_title(surface, locale)
    zh = is_zh_locale(locale)
    lowered = str(surface or "").lower()
    if "onboarding" in lowered or "setup" in lowered or any(token in surface for token in ("接入", "范围", "配置")):
        return {
            "headline": f"{localized_surface}已更新" if zh else f"{surface} updated",
            "body": "最新范围配置已显示在本页，可继续启动观测或进入总览。"
            if zh
            else "The latest scope setup is visible on this page and ready for observation start or overview follow-up.",
        }
    if "overview" in lowered or "findings" in lowered or any(token in surface for token in ("总览", "发现")):
        return {
            "headline": f"{localized_surface}已加载" if zh else f"{surface} loaded",
            "body": "最新发现与任务状态已显示，可继续查看建议详情或处理任务。"
            if zh
            else "The latest findings and task states are visible, so the next recommendation or task action is clear.",
        }
    if "recommendation" in lowered or any(token in surface for token in ("建议", "导出")):
        return {
            "headline": f"{localized_surface}已更新" if zh else f"{surface} updated",
            "body": "建议详情和任务导出结果已刷新，可继续交接下游执行。"
            if zh
            else "The recommendation detail and task export outcome are visible, ready for downstream handoff.",
        }
    if "task" in lowered or "任务" in surface:
        return {
            "headline": f"{localized_surface}已更新" if zh else f"{surface} updated",
            "body": "最新任务状态与执行证据已显示，可继续处理下一项任务或进入审核。"
            if zh
            else "The latest task state and execution evidence are visible, ready for the next task or review step.",
        }
    if "review" in lowered or any(token in surface for token in ("审核", "继续", "修订")):
        return {
            "headline": f"{localized_surface}已更新" if zh else f"{surface} updated",
            "body": "审核结论与关键证据已显示，可继续进入下一轮或回到修订流程。"
            if zh
            else "The review outcome and supporting evidence are visible, ready for the next cycle or a revise path.",
        }
    if page_role in {"form-flow", "workflow", "review"}:
        return {
            "headline": f"{localized_surface}已更新" if zh else f"{surface} updated",
            "body": "最新状态应继续停留在本页可见，便于操作者确认结果并继续推进。"
            if zh
            else "The latest state should stay visible on this page so the operator can confirm the result and continue.",
        }
    return {
        "headline": f"{localized_surface}已加载" if zh else f"{surface} loaded",
        "body": "当前业务结果已显示，可继续下一步操作。"
        if zh
        else "The current business result is visible and ready for the next action.",
    }
