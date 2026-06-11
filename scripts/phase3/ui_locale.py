#!/usr/bin/env python3
"""
Shared locale helpers for Phase-3 fallback/UI generation support.
"""

from __future__ import annotations

import re


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


UI_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "delivery_workspace": "Business workspace",
        "runnable_mvp": "Operable business app",
        "workspace_menu": "Workspace",
        "operate_runnable_workflow": "Operate the current workflow",
        "workspace_intro": "Open the page that matches the business job to be done, keep the latest record state visible, and submit the next action against the running service.",
        "workspace_intro_compact": "Work from the current role workspace and keep live records connected to the running backend.",
        "workspace_intro_scaffold": "Use the available work areas to enter data, review current records, and move the workflow forward without dropping into a debug console.",
        "workspace_intro_generated": "Work from the current role workspace and keep live records connected to backend actions.",
        "open_primary_workspace": "Open primary workspace",
        "primary_work_area": "Primary work area",
        "no_pages_generated_yet": "No pages generated yet",
        "generate_ia_backed_page_to_continue": "Generate at least one IA-backed page to continue.",
        "live_work_areas": "Live work areas",
        "pages_label": "{count} pages",
        "live_work_areas_hint": "Each page should keep the goal, work area, current data, and next steps visible together.",
        "connected_runtime_coverage": "Connected runtime coverage",
        "connected_runtime_summary": "{operations} service actions / {slices} delivery slices",
        "connected_runtime_hint": "The MVP keeps business pages tied to runnable backend operations instead of a detached mock console.",
        "active_role": "Active role",
        "switch_role": "Switch role",
        "role_workspaces": "Select your workspace",
        "role_workspaces_hint": "Open the workspace that matches your current permissions.",
        "accessible_pages": "Accessible pages",
        "no_accessible_pages": "No pages are available for this role yet.",
        "enter_workspace": "Open workspace",
        "sign_out": "Sign out",
        "read_only_mode": "Read-only mode",
        "editable_mode": "Can edit",
        "role_access_limited": "This role can review current data but cannot submit changes on this page.",
        "available_work_areas": "Available work areas",
        "available_work_areas_hint": "Choose the page that matches the job to be done. Each work area should expose the data the user must see and the input they must submit.",
        "open_page": "Open page",
        "primary_action": "Primary action",
        "linked_service_actions": "Linked service actions",
        "delivery_slices": "Delivery slices",
        "back_to_workspace": "Back to workspace",
        "previous_page": "Previous page",
        "next_page": "Next page",
        "goal_for_this_page": "Goal for this page",
        "main_action": "Main action",
        "main_action_hint": "Use this action to move the workflow forward.",
        "ready_when": "Ready when",
        "work_area": "Work area",
        "work_area_hint": "Fill in the required details, keep the current context visible, and submit when this step is ready.",
        "required_suffix": "(required)",
        "optional_suffix": "(optional)",
        "enter_value": "Enter value",
        "choose_option": "Choose an option",
        "yes": "Yes",
        "no": "No",
        "refresh_current_data": "Refresh current data",
        "page_structure": "Page structure",
        "bound_fields": "Bound fields",
        "workflow_steps": "Workflow steps",
        "workflow_steps_hint": "Choose the step that matches what you need to do on this page.",
        "current_step": "Current step",
        "this_action_needs": "This action needs",
        "it_updates": "It updates",
        "select_step": "Select step",
        "after_each_action": "After each action",
        "retry_path": "Retry path",
        "current_snapshot": "Current snapshot",
        "current_results": "Current results",
        "current_detail": "Current detail",
        "current_context": "Current context",
        "latest_workflow_state": "Latest workflow state",
        "review_context": "Review context",
        "current_data": "Current data",
        "updating_this_page": "Updating this page",
        "ready_to_work": "Ready to work",
        "loading_latest_workflow_data": "Loading the latest page data.",
        "loading": "Loading...",
        "saving": "Saving...",
        "page_waiting_binding": "This page is waiting for its primary data binding.",
        "required_path_parameters_missing": "Required path parameters are still missing.",
        "what_happens_next": "What happens next",
        "success_prefix": "Success",
        "error_prefix": "Error",
        "dashboard": "Dashboard",
        "fallback_ui_title": "UI Prototype Fallback (Phase-3)",
        "fallback_purpose": "provide default UI input so Phase-3 can continue to a usable MVP when human prototype input is missing",
        "required_mvp_pages": "Required MVP Pages",
        "workflow_hints": "Workflow Hints From Phase-2",
        "backend_api_anchors": "Backend API Anchors",
        "evidence_rule": "Evidence Rule",
        "wireframes_title": "Phase-3 UI Fallback Wireframes",
        "site_dashboard_title": "Fallback UI - Dashboard",
        "site_dashboard_heading": "Fallback MVP Workspace",
        "site_dashboard_note": "Generated when no human prototype is provided. This is a business-facing default input, not a debug console.",
        "site_workflow_areas": "Workflow areas",
        "site_workflow_areas_hint": "Each linked page should become a usable surface with a clear goal, primary CTA, and visible result state.",
        "site_expected_behavior": "Expected MVP behavior",
        "site_user_goal": "User goal",
        "site_primary_cta": "Primary CTA",
        "site_states": "States",
        "site_workspace_desc": "Hero summary, current status, priority signals, and the next recommended action.",
        "site_list_detail_desc": "Filter bar, result list, selected-item summary, and visible empty/error states.",
        "site_workflow_form_desc": "Grouped business inputs, validation, save action, and confirmation feedback.",
        "site_review_desc": "Evidence summary, decision controls, and clear follow-up guidance.",
    },
    "zh-CN": {
        "delivery_workspace": "业务工作台",
        "runnable_mvp": "可操作业务应用",
        "workspace_menu": "工作台",
        "operate_runnable_workflow": "进入当前业务工作流",
        "workspace_intro": "打开与你当前业务任务匹配的页面，保持最新记录状态可见，并直接对运行中的服务提交下一步业务操作。",
        "workspace_intro_compact": "在当前角色工作区内完成业务，并让实时记录持续连接后端运行时。",
        "workspace_intro_scaffold": "使用这些工作区录入数据、查看当前记录，并在不落回调试控制台的前提下推进工作流。",
        "workspace_intro_generated": "在当前角色工作区内完成业务，并让实时记录持续连接后端动作。",
        "open_primary_workspace": "打开主工作区",
        "primary_work_area": "主要工作区",
        "no_pages_generated_yet": "尚未生成页面",
        "generate_ia_backed_page_to_continue": "至少生成一个与 IA 对齐的页面后才能继续。",
        "live_work_areas": "在线工作区",
        "pages_label": "{count} 个页面",
        "live_work_areas_hint": "每个页面都应同时展示目标、工作区、当前数据以及下一步操作。",
        "connected_runtime_coverage": "运行时联通覆盖",
        "connected_runtime_summary": "{operations} 个服务动作 / {slices} 个交付切片",
        "connected_runtime_hint": "这个 MVP 将业务页面绑定到真实可运行的后端操作，而不是脱离运行时的演示控制台。",
        "active_role": "当前角色",
        "switch_role": "切换角色",
        "role_workspaces": "选择登录工作区",
        "role_workspaces_hint": "请选择与你当前权限相符的工作区。",
        "accessible_pages": "可访问页面",
        "no_accessible_pages": "当前角色还没有可访问页面。",
        "enter_workspace": "进入工作区",
        "sign_out": "退出登录",
        "read_only_mode": "只读模式",
        "editable_mode": "可编辑",
        "role_access_limited": "当前角色可查看数据，但不能在本页提交变更。",
        "available_work_areas": "可用工作区",
        "available_work_areas_hint": "选择与你当前任务匹配的页面。每个工作区都应明确展示用户必须查看的数据和必须提交的输入。",
        "open_page": "打开页面",
        "primary_action": "主要操作",
        "linked_service_actions": "关联服务动作",
        "delivery_slices": "交付切片",
        "back_to_workspace": "返回工作台",
        "previous_page": "上一页",
        "next_page": "下一页",
        "goal_for_this_page": "本页目标",
        "main_action": "主要操作",
        "main_action_hint": "使用这个操作推进当前工作流。",
        "ready_when": "达成条件",
        "work_area": "工作区",
        "work_area_hint": "填写所需信息，保持当前上下文可见，并在准备完成后提交本步骤。",
        "required_suffix": "（必填）",
        "optional_suffix": "（可选）",
        "enter_value": "请输入内容",
        "choose_option": "请选择",
        "yes": "是",
        "no": "否",
        "refresh_current_data": "刷新当前数据",
        "page_structure": "页面结构",
        "bound_fields": "绑定字段",
        "workflow_steps": "业务步骤",
        "workflow_steps_hint": "选择当前页面需要执行的业务步骤。",
        "current_step": "当前步骤",
        "this_action_needs": "本步需要",
        "it_updates": "执行后关注",
        "select_step": "选择步骤",
        "after_each_action": "完成后会发生什么",
        "retry_path": "失败时如何处理",
        "current_snapshot": "当前快照",
        "current_results": "当前结果",
        "current_detail": "当前详情",
        "current_context": "当前上下文",
        "latest_workflow_state": "最新工作流状态",
        "review_context": "审核上下文",
        "current_data": "当前数据",
        "updating_this_page": "正在更新页面",
        "ready_to_work": "可开始操作",
        "loading_latest_workflow_data": "正在加载本页最新数据。",
        "loading": "加载中...",
        "saving": "保存中...",
        "page_waiting_binding": "当前页面尚未绑定主要数据接口。",
        "required_path_parameters_missing": "仍缺少必填路径参数。",
        "what_happens_next": "下一步会发生什么",
        "success_prefix": "成功",
        "error_prefix": "失败",
        "dashboard": "总览",
        "fallback_ui_title": "Phase-3 默认界面原型",
        "fallback_purpose": "在缺少人工界面原型输入时提供默认 UI 输入，使 Phase-3 仍能继续交付可用 MVP",
        "required_mvp_pages": "必须覆盖的 MVP 页面",
        "workflow_hints": "来自 Phase-2 的工作流提示",
        "backend_api_anchors": "后端 API 锚点",
        "evidence_rule": "证据规则",
        "wireframes_title": "Phase-3 默认界面线框",
        "site_dashboard_title": "默认界面 - 总览",
        "site_dashboard_heading": "默认 MVP 工作台",
        "site_dashboard_note": "当未提供人工界面原型时自动生成。这是面向业务的默认输入，不是调试控制台。",
        "site_workflow_areas": "工作流区域",
        "site_workflow_areas_hint": "每个链接页面最终都应成为具备明确目标、主要操作和可见结果状态的可用页面。",
        "site_expected_behavior": "预期 MVP 行为",
        "site_user_goal": "用户目标",
        "site_primary_cta": "主要操作",
        "site_states": "状态",
        "site_workspace_desc": "展示摘要、当前状态、优先信号和推荐的下一步操作。",
        "site_list_detail_desc": "展示筛选区、结果列表、选中项摘要以及明确的空态/错误态。",
        "site_workflow_form_desc": "展示分组业务输入、校验信息、保存操作和确认反馈。",
        "site_review_desc": "展示证据摘要、决策控件以及清晰的后续指引。",
    },
}


SURFACE_TITLE_MAP: dict[str, str] = {
    "Onboarding / scope setup": "接入与范围配置",
    "Overview + findings": "总览与发现",
    "Recommendation detail + task export": "建议详情与任务导出",
    "Task state update": "任务状态更新",
    "Review report + continue/revise decision": "审核报告与继续/修订决策",
    "Overview dashboard": "总览仪表板",
    "Primary record list": "主记录列表",
    "Record detail view": "记录详情页",
    "Action workspace": "操作工作区",
}


INFORMATION_OBJECT_MAP: dict[str, str] = {
    "Tenant": "租户",
    "Tracked Scope": "跟踪范围",
    "Attribution Seam": "归因边界",
    "Observation Run": "观测运行",
    "Visibility Finding": "可见性发现",
    "Competitor Snapshot": "竞品快照",
    "Optimization Recommendation": "优化建议",
    "Optimization Task": "优化任务",
    "Content Asset": "内容资产",
    "Review Report": "审核报告",
    "Audit Record": "审计记录",
}


PAGE_ROLE_EYEBROW: dict[str, dict[str, str]] = {
    "en": {
        "workspace": "Operations workspace",
        "list": "Working list",
        "detail": "Detail workspace",
        "form-flow": "Workflow setup",
        "workflow": "Workflow update",
        "review": "Review workspace",
    },
    "zh-CN": {
        "workspace": "运营工作区",
        "list": "工作列表",
        "detail": "详情工作区",
        "form-flow": "流程配置",
        "workflow": "流程更新",
        "review": "审核工作区",
    },
}


PAGE_ROLE_LABEL: dict[str, dict[str, str]] = {
    "en": {
        "workspace": "workspace",
        "list": "list",
        "detail": "detail",
        "form-flow": "form-flow",
        "workflow": "workflow",
        "review": "review",
    },
    "zh-CN": {
        "workspace": "工作台",
        "list": "列表",
        "detail": "详情",
        "form-flow": "表单流程",
        "workflow": "工作流",
        "review": "审核",
    },
}


VIEW_LABEL: dict[str, dict[str, str]] = {
    "en": {},
    "zh-CN": {
        "summary-cards": "摘要卡片",
        "list": "列表",
        "cta-panel": "操作面板",
        "filter-bar": "筛选栏",
        "table": "表格",
        "detail": "详情",
        "detail-list": "详情列表",
        "status-banner": "状态条",
        "form": "表单",
        "result": "结果",
        "next-steps": "后续步骤",
    },
}


FIELD_LABEL_MAP: dict[str, dict[str, str]] = {
    "en": {
        "tenantId": "Working Tenant",
        "scopeId": "Scope ID",
        "scopeKey": "Scope Key",
        "scopeVersion": "Scope Version",
        "brandName": "Brand Name",
        "competitors": "Competitors",
        "questions": "Questions",
        "pages": "Pages",
        "idempotencyKey": "Submission Batch Key",
        "observationRunId": "Observation Run ID",
        "priorityBands": "Priority Bands",
        "includeCompetitorWindow": "Include Competitor Window",
        "cursor": "Cursor",
        "pageSize": "Page Size",
        "statuses": "Statuses",
        "ownerSubjectId": "Owner",
        "includeRecommendationSummary": "Include Recommendation Summary",
        "includeBlockedOnly": "Blocked Only",
        "sortBy": "Sort By",
        "findingId": "Finding ID",
        "expectedFindingVersion": "Expected Finding Version",
        "includeCompetitorContext": "Include Competitor Context",
        "includeRecommendationContext": "Include Recommendation Context",
        "includeAttributionSeam": "Include Attribution Seam",
        "assetId": "Asset ID",
        "decision": "Decision",
        "decisionRationale": "Decision Rationale",
        "priorityOverride": "Priority Override",
        "attributionContextRef": "Attribution Context Ref",
        "recommendationId": "Recommendation ID",
        "payloadVersion": "Payload Version",
        "taskId": "Task ID",
        "status": "Status",
        "version": "Version",
        "expectedVersion": "Current Version",
        "executionEvidenceRef": "Execution Evidence Ref",
        "blockedReason": "Blocked Reason",
        "cycleKey": "Cycle Key",
        "freezeTaskStatusesBefore": "Freeze Tasks Before",
        "includeUncertaintyBreakdown": "Include Uncertainty Breakdown",
        "role": "Role",
        "policyDecision": "Policy Decision",
        "trackedScopeId": "Tracked Scope ID",
        "sourceTag": "Source Tag",
        "funnelStage": "Funnel Stage",
        "conversionEvent": "Conversion Event",
        "authoritative": "Authoritative",
        "reactivationTrigger": "Reactivation Trigger",
        "severity": "Severity",
        "score": "Score",
        "snapshotRef": "Snapshot Ref",
        "comparativeScore": "Comparative Score",
        "measurementWindow": "Measurement Window",
        "recommendationStatus": "Recommendation Status",
        "traceAnchor": "Trace Anchor",
        "competitorContext": "Competitor Context",
        "gapExplanation": "Gap Explanation",
        "recommendationOptions": "Recommendation Options",
        "attributionSeam": "Attribution Seam",
        "auditAnchors": "Audit Anchors",
        "contentAssetId": "Content Asset ID",
        "path": "Path",
        "assetType": "Asset Type",
        "queuePosition": "Queue Position",
        "dueAt": "Due At",
        "auditTraceRef": "Audit Trace Ref",
        "reviewReportId": "Review Report ID",
        "uncertaintyLevel": "Uncertainty Level",
        "uncertaintyNote": "Uncertainty Note",
        "decisionPosture": "Review Recommendation",
        "thresholdRationale": "Threshold Rationale",
        "reviewSummary": "Review Summary",
        "auditRecordId": "Audit Record ID",
        "actionType": "Action Type",
        "traceId": "Trace ID",
        "attributionWindow": "Attribution Window",
    },
    "zh-CN": {
        "tenantId": "工作租户",
        "scopeId": "范围 ID",
        "scopeKey": "范围标识",
        "scopeVersion": "范围版本",
        "brandName": "品牌名称",
        "competitors": "竞品列表",
        "questions": "关注问题",
        "pages": "关键页面",
        "idempotencyKey": "提交批次标识",
        "observationRunId": "观测运行 ID",
        "priorityBands": "优先级分层",
        "includeCompetitorWindow": "包含竞品窗口",
        "cursor": "游标",
        "pageSize": "每页数量",
        "statuses": "状态筛选",
        "ownerSubjectId": "负责人",
        "includeRecommendationSummary": "包含建议摘要",
        "includeBlockedOnly": "仅看阻塞项",
        "sortBy": "排序方式",
        "findingId": "发现 ID",
        "expectedFindingVersion": "期望发现版本",
        "includeCompetitorContext": "包含竞品上下文",
        "includeRecommendationContext": "包含建议上下文",
        "includeAttributionSeam": "包含归因边界",
        "assetId": "资产 ID",
        "decision": "决策状态",
        "decisionRationale": "决策理由",
        "priorityOverride": "优先级覆盖",
        "attributionContextRef": "归因上下文引用",
        "recommendationId": "建议 ID",
        "payloadVersion": "载荷版本",
        "taskId": "任务 ID",
        "status": "状态",
        "version": "版本号",
        "expectedVersion": "当前版本号",
        "executionEvidenceRef": "执行证据引用",
        "blockedReason": "阻塞原因",
        "cycleKey": "周期标识",
        "freezeTaskStatusesBefore": "冻结任务状态时间",
        "includeUncertaintyBreakdown": "包含不确定性拆解",
        "role": "角色",
        "policyDecision": "权限决策",
        "trackedScopeId": "跟踪范围 ID",
        "sourceTag": "来源标签",
        "funnelStage": "漏斗阶段",
        "conversionEvent": "转化事件",
        "authoritative": "是否权威",
        "reactivationTrigger": "重新激活条件",
        "severity": "严重程度",
        "score": "评分",
        "snapshotRef": "快照引用",
        "comparativeScore": "对比分值",
        "measurementWindow": "观测窗口",
        "recommendationStatus": "建议状态",
        "traceAnchor": "追踪锚点",
        "competitorContext": "竞品上下文",
        "gapExplanation": "差距说明",
        "recommendationOptions": "建议选项",
        "attributionSeam": "归因边界",
        "auditAnchors": "审计锚点",
        "contentAssetId": "内容资产 ID",
        "path": "路径",
        "assetType": "资产类型",
        "queuePosition": "队列位置",
        "dueAt": "到期时间",
        "auditTraceRef": "审计追踪引用",
        "reviewReportId": "审核报告 ID",
        "uncertaintyLevel": "不确定性等级",
        "uncertaintyNote": "不确定性说明",
        "decisionPosture": "审核建议",
        "thresholdRationale": "阈值依据",
        "reviewSummary": "审核摘要",
        "auditRecordId": "审计记录 ID",
        "actionType": "动作类型",
        "traceId": "追踪 ID",
        "attributionWindow": "归因窗口",
    },
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
    zh = is_zh_locale(locale)
    if zh:
        role_defaults = {
            "workspace": {
                "selectors_panel_title": "当前查看范围",
                "work_area_title": "工作区",
                "work_area_hint": "围绕当前业务目标切换视角、查看结果并继续下一步。",
                "current_step_label": "当前步骤",
                "workflow_steps_title": "本页业务步骤",
                "workflow_steps_hint": "选择当前页面需要执行的业务步骤。",
                "current_data_title": "当前结果",
                "next_steps_title": "完成本步后",
                "pending_live_data": "等待实时数据",
            },
            "list": {
                "selectors_panel_title": "当前筛选范围",
                "work_area_title": "筛选与处理",
                "work_area_hint": "先缩小工作集，再打开需要处理的记录。",
                "current_step_label": "当前步骤",
                "workflow_steps_title": "列表处理步骤",
                "workflow_steps_hint": "先筛选，再查看结果并进入下一步。",
                "current_data_title": "当前列表结果",
                "next_steps_title": "完成本步后",
                "pending_live_data": "等待列表数据",
            },
            "detail": {
                "selectors_panel_title": "当前处理范围",
                "work_area_title": "详情处理",
                "work_area_hint": "保持当前记录、支撑上下文和下一步动作同时可见。",
                "current_step_label": "当前步骤",
                "workflow_steps_title": "详情处理步骤",
                "workflow_steps_hint": "先查看详情，再执行冻结、导出或交接动作。",
                "current_data_title": "当前详情",
                "next_steps_title": "完成本步后",
                "pending_live_data": "等待详情数据",
            },
            "form-flow": {
                "selectors_panel_title": "当前配置范围",
                "work_area_title": "配置工作区",
                "work_area_hint": "先完成必填配置，再继续后续工作流动作。",
                "current_step_label": "配置步骤",
                "workflow_steps_title": "配置步骤",
                "workflow_steps_hint": "按顺序完成本页所需配置。",
                "current_data_title": "当前配置结果",
                "next_steps_title": "完成本步后",
                "pending_live_data": "等待配置结果",
            },
            "workflow": {
                "selectors_panel_title": "当前执行范围",
                "work_area_title": "执行更新",
                "work_area_hint": "保持状态、证据和阻塞原因在同一工作面里更新。",
                "current_step_label": "执行步骤",
                "workflow_steps_title": "执行步骤",
                "workflow_steps_hint": "依次完成查询、更新和确认动作。",
                "current_data_title": "当前执行结果",
                "next_steps_title": "每次更新后",
                "pending_live_data": "等待执行数据",
            },
            "review": {
                "selectors_panel_title": "当前审核范围",
                "work_area_title": "审核决策",
                "work_area_hint": "冻结当前周期输入，查看结论，再决定后续处理。",
                "current_step_label": "审核步骤",
                "workflow_steps_title": "审核闭环步骤",
                "workflow_steps_hint": "先生成审核结果，再查看证据并推进后续动作。",
                "current_data_title": "当前审核结果",
                "next_steps_title": "提交后",
                "pending_live_data": "等待审核结果",
            },
        }
    else:
        role_defaults = {
            "workspace": {
                "selectors_panel_title": "Current view scope",
                "work_area_title": "Work area",
                "work_area_hint": "Switch context, review the latest results, and move the business workflow forward.",
                "current_step_label": "Current step",
                "workflow_steps_title": "Business steps on this page",
                "workflow_steps_hint": "Choose the business step that matches what you need to complete on this page.",
                "current_data_title": "Current results",
                "next_steps_title": "After this step",
                "pending_live_data": "Pending live data",
            },
            "list": {
                "selectors_panel_title": "Current filter scope",
                "work_area_title": "Filter and act",
                "work_area_hint": "Narrow the working set first, then open the record that needs action.",
                "current_step_label": "Current step",
                "workflow_steps_title": "List handling steps",
                "workflow_steps_hint": "Filter first, then inspect the results and move forward.",
                "current_data_title": "Current list results",
                "next_steps_title": "After this step",
                "pending_live_data": "Pending list data",
            },
            "detail": {
                "selectors_panel_title": "Current decision scope",
                "work_area_title": "Detail handling",
                "work_area_hint": "Keep the current record, supporting context, and next action visible together.",
                "current_step_label": "Current step",
                "workflow_steps_title": "Detail handling steps",
                "workflow_steps_hint": "Inspect the detail first, then freeze, export, or hand off the next action.",
                "current_data_title": "Current detail",
                "next_steps_title": "After this step",
                "pending_live_data": "Pending detail data",
            },
            "form-flow": {
                "selectors_panel_title": "Current setup scope",
                "work_area_title": "Setup workspace",
                "work_area_hint": "Complete the required setup inputs before advancing the workflow.",
                "current_step_label": "Setup step",
                "workflow_steps_title": "Setup steps",
                "workflow_steps_hint": "Complete the setup steps on this page in sequence.",
                "current_data_title": "Current setup state",
                "next_steps_title": "After this step",
                "pending_live_data": "Pending setup data",
            },
            "workflow": {
                "selectors_panel_title": "Current execution scope",
                "work_area_title": "Execution update",
                "work_area_hint": "Keep the status, evidence, and blocked reason updated in one place.",
                "current_step_label": "Execution step",
                "workflow_steps_title": "Execution steps",
                "workflow_steps_hint": "Query, update, and confirm the workflow in order.",
                "current_data_title": "Current execution state",
                "next_steps_title": "After each update",
                "pending_live_data": "Pending execution data",
            },
            "review": {
                "selectors_panel_title": "Current review scope",
                "work_area_title": "Review decision",
                "work_area_hint": "Freeze the cycle inputs, inspect the outcome, and decide the follow-up.",
                "current_step_label": "Review step",
                "workflow_steps_title": "Review closure steps",
                "workflow_steps_hint": "Generate the review result first, then inspect evidence and move the follow-up forward.",
                "current_data_title": "Current review outcome",
                "next_steps_title": "After submission",
                "pending_live_data": "Pending review data",
            },
        }
    return role_defaults.get(page_role, role_defaults["detail"]).copy()


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
