#!/usr/bin/env python3
"""
Generate the Phase-3 project scaffold and CI/dev baseline.
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

from phase3.ui_locale import infer_ui_locale, page_role_label, ui_text


SCRIPT_DIR = Path(__file__).resolve().parent


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "phase3-app"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def bundled_script_content(filename: str) -> str:
    return (SCRIPT_DIR / filename).read_text(encoding="utf-8")


def _normalize_route_segment(route_value: str, fallback_title: str) -> str:
    candidates = [part for part in str(route_value).split("/") if part.strip()]
    normalized = [slugify(part) for part in candidates if slugify(part)]
    if normalized:
        return "/".join(normalized)
    return slugify(fallback_title)


def _scaffold_surface_pages(ui_ia_contract_path: Path | None) -> list[dict[str, Any]]:
    default_titles = [
        "Overview dashboard",
        "Primary record list",
        "Record detail view",
        "Action workspace",
    ]
    fallback_pages = [
        {
            "page_id": slugify(title),
            "title": title,
            "locale": "en",
            "route": _normalize_route_segment("", title),
            "subtitle": f"Use the {title.lower()} page to keep the workflow moving with the current context in view.",
            "goal": f"Review the current {title.lower()} context and complete the next action without leaving the page.",
            "page_role": "workspace" if "overview" in title.lower() else ("list" if "list" in title.lower() else ("detail" if "detail" in title.lower() else "workflow")),
            "allowed_roles": [],
            "business_objects": [],
            "required_regions": [],
            "next_route_candidates": [],
            "compiled_interactions": [],
            "presentation": ["table-or-list", "detail-panel", "status-banner"],
            "user_inputs": [{"field": "query", "required": False, "validation": "text"}],
            "actions": [{"action": "continue", "on_success": "navigate to next surface", "on_error": "stay on current surface"}],
            "states": {
                "loading": "page data query in progress",
                "success": "primary data loaded and rendered",
                "empty": "query returned no records",
                "error": "request failed and retry is available",
            },
        }
        for title in default_titles
    ]
    if ui_ia_contract_path is None or not ui_ia_contract_path.exists():
        return fallback_pages
    try:
        payload = json.loads(ui_ia_contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback_pages
    payload_locale = str(payload.get("locale") or "").strip() if isinstance(payload, dict) else ""
    raw_pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(raw_pages, list):
        return fallback_pages
    pages: list[dict[str, Any]] = []
    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            continue
        title = str(raw_page.get("page_title") or raw_page.get("title") or "").strip()
        if not title:
            continue
        route = _normalize_route_segment(str(raw_page.get("route") or ""), title)
        presentation = [
            str(item).strip()
            for item in raw_page.get("data_presentation", [])
            if str(item).strip()
        ] or ["table-or-list", "detail-panel", "status-banner"]
        user_inputs = [
            {
                "field": str(item.get("field") or "").strip(),
                "required": bool(item.get("required")),
                "validation": str(item.get("validation") or "").strip() or "text",
            }
            for item in raw_page.get("user_inputs", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        ]
        actions = [
            {
                "action": str(item.get("action") or "").strip(),
                "on_success": str(item.get("on_success") or "").strip(),
                "on_error": str(item.get("on_error") or "").strip(),
            }
            for item in raw_page.get("actions_and_transitions", [])
            if isinstance(item, dict) and str(item.get("action") or "").strip()
        ]
        states = raw_page.get("state_conditions", {}) if isinstance(raw_page.get("state_conditions", {}), dict) else {}
        pages.append(
            {
                "page_id": str(raw_page.get("page_id") or slugify(title)).strip(),
                "title": title,
                "locale": str(raw_page.get("locale") or payload_locale or "").strip(),
                "route": route,
                "subtitle": str(raw_page.get("subtitle") or f"Use the {title.lower()} page to complete the next job to be done.").strip(),
                "goal": str(raw_page.get("user_goal") or f"Keep the current {title.lower()} context visible while the next action is completed.").strip(),
                "page_role": str(raw_page.get("page_role") or ("workspace" if "overview" in title.lower() else "workflow")).strip(),
                "allowed_roles": [
                    str(item).strip()
                    for item in raw_page.get("allowed_roles", [])
                    if str(item).strip()
                ],
                "business_objects": [
                    str(item).strip()
                    for item in raw_page.get("business_objects", [])
                    if str(item).strip()
                ],
                "required_regions": [
                    str(item).strip()
                    for item in raw_page.get("required_regions", [])
                    if str(item).strip()
                ],
                "next_route_candidates": [
                    str(item).strip()
                    for item in raw_page.get("next_route_candidates", [])
                    if str(item).strip()
                ],
                "compiled_interactions": [
                    item
                    for item in raw_page.get("compiled_interactions", [])
                    if isinstance(item, dict)
                ],
                "presentation": presentation,
                "user_inputs": user_inputs or [{"field": "query", "required": False, "validation": "text"}],
                "actions": actions or [{"action": "continue", "on_success": "navigate to next surface", "on_error": "stay on current surface"}],
                "states": {
                    "loading": str(states.get("loading") or "page data query in progress"),
                    "success": str(states.get("success") or "primary data loaded and rendered"),
                    "empty": str(states.get("empty") or "query returned no records"),
                    "error": str(states.get("error") or "request failed and retry is available"),
                },
            }
        )
    return pages or fallback_pages


def _render_scaffold_ui_app(surface_pages: list[dict[str, Any]]) -> str:
    surfaces_blob = json.dumps(surface_pages, ensure_ascii=False, indent=2)
    locale = infer_ui_locale(
        *[
            " ".join(
                [
                    str(page.get("locale") or ""),
                    str(page.get("title") or ""),
                    str(page.get("subtitle") or ""),
                    str(page.get("goal") or ""),
                ]
            )
            for page in surface_pages
        ]
    )
    goal_title = "Goal for this page" if locale == "en" else "本页目标"
    work_area_title = "Work area" if locale == "en" else "工作区"
    work_area_hint = (
        "Enter the required information for this step and keep the latest draft state visible on the page."
        if locale == "en"
        else "填写本步骤所需信息，并让最新草稿状态继续停留在页面上。"
    )
    required_message_suffix = "is required" if locale == "en" else "为必填项"
    input_placeholder = "text" if locale == "en" else "请输入内容"
    save_draft_label = "Save current draft" if locale == "en" else "保存当前草稿"
    current_context_title = "Current context" if locale == "en" else "当前上下文"
    submitted_hint = (
        "The current working data will appear here after the user submits the form."
        if locale == "en"
        else "用户提交表单后，当前工作数据会显示在这里。"
    )
    data_signals_title = "Data and signals in view" if locale == "en" else "当前数据与信号"
    page_states_title = "Page states" if locale == "en" else "页面状态"
    loading_label = "loading" if locale == "en" else "加载中"
    success_label = "success" if locale == "en" else "成功"
    empty_label = "empty" if locale == "en" else "空态"
    error_label = "error" if locale == "en" else "失败"
    contract_anchor_title = "Contract anchors" if locale == "en" else "合同锚点"
    allowed_roles_title = "Allowed roles" if locale == "en" else "允许角色"
    business_objects_title = "Business objects" if locale == "en" else "业务对象"
    required_regions_title = "Required regions" if locale == "en" else "必需区域"
    interaction_binding_title = "Interaction and binding chain" if locale == "en" else "交互与绑定链"
    next_routes_title = "Next routes" if locale == "en" else "后续路由"
    no_contract_anchor_hint = (
        "This scaffold is still waiting for explicit compiled contract anchors."
        if locale == "en"
        else "这个 scaffold 还在等待显式的 compiled contract 锚点。"
    )
    next_steps_title = "What happens next" if locale == "en" else "下一步会发生什么"
    success_prefix = "Success" if locale == "en" else "成功"
    error_prefix = "Error" if locale == "en" else "失败"
    route_label = "Route" if locale == "en" else "路由"
    return "\n".join(
        [
            'import { useState } from "react";',
            'import { Button, Card, Form, Input, Layout, Menu, Space, Tag, Typography } from "antd";',
            'import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";',
            "",
            "type SurfaceInput = {",
            "  field: string;",
            "  required: boolean;",
            "  validation: string;",
            "};",
            "",
            "type SurfaceAction = {",
            "  action: string;",
            "  on_success: string;",
            "  on_error: string;",
            "  next_route?: string;",
            "};",
            "",
            "type SurfaceStates = {",
            "  loading: string;",
            "  success: string;",
            "  empty: string;",
            "  error: string;",
            "};",
            "",
            "type CompiledInteractionSpec = {",
            "  interaction_id?: string;",
            "  trigger_kind?: string;",
            "  binding_mode?: string;",
            "  domain_service?: string;",
            "  api_endpoint?: string;",
            "  next_page_id?: string;",
            "  failure_route?: string;",
            "  readiness_status?: string;",
            "  blocked_reason?: string;",
            "};",
            "",
            "type SurfaceSpec = {",
            "  title: string;",
            "  route: string;",
            "  subtitle: string;",
            "  goal: string;",
            "  page_role: string;",
            "  allowed_roles: string[];",
            "  business_objects: string[];",
            "  required_regions: string[];",
            "  next_route_candidates: string[];",
            "  compiled_interactions: CompiledInteractionSpec[];",
            "  presentation: string[];",
            "  user_inputs: SurfaceInput[];",
            "  actions: SurfaceAction[];",
            "  states: SurfaceStates;",
            "};",
            "",
            f"const surfaces: SurfaceSpec[] = {surfaces_blob};",
            "",
            "function SurfaceScaffoldPage({ surface }: { surface: SurfaceSpec }) {",
            "  const [submitted, setSubmitted] = useState<Record<string, string> | null>(null);",
            "  const hasContractAnchors = surface.allowed_roles.length > 0 || surface.business_objects.length > 0 || surface.required_regions.length > 0 || surface.compiled_interactions.length > 0 || surface.next_route_candidates.length > 0;",
            "  return (",
            "    <Space direction=\"vertical\" size={16} style={{ width: '100%' }}>",
            "      <Card>",
            "        <Space direction=\"vertical\" size={8} style={{ width: '100%' }}>",
            "          <Tag>{surface.page_role}</Tag>",
            "          <Typography.Title level={2} style={{ margin: 0 }}>{surface.title}</Typography.Title>",
            "          <Typography.Paragraph style={{ marginBottom: 0 }}>{surface.subtitle}</Typography.Paragraph>",
            f"          <Typography.Paragraph type=\"secondary\" style={{ marginBottom: 0 }}>{route_label}: /{{surface.route}}</Typography.Paragraph>",
            "        </Space>",
            "      </Card>",
            f"      <Card title={json.dumps(goal_title, ensure_ascii=False)}>",
            "        <Typography.Paragraph style={{ marginBottom: 0 }}>{surface.goal}</Typography.Paragraph>",
            "      </Card>",
            f"      <Card title={json.dumps(contract_anchor_title, ensure_ascii=False)}>",
            "        {hasContractAnchors ? (",
            "          <Space direction=\"vertical\" size={12} style={{ width: '100%' }}>",
            "            {surface.allowed_roles.length > 0 ? (",
            "              <div>",
            f"                <Typography.Text strong>{allowed_roles_title}</Typography.Text>",
            "                <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>",
            "                  {surface.allowed_roles.map((item) => <Tag key={item}>{item}</Tag>)}",
            "                </div>",
            "              </div>",
            "            ) : null}",
            "            {surface.business_objects.length > 0 ? (",
            "              <div>",
            f"                <Typography.Text strong>{business_objects_title}</Typography.Text>",
            "                <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>",
            "                  {surface.business_objects.map((item) => <Tag key={item} color=\"blue\">{item}</Tag>)}",
            "                </div>",
            "              </div>",
            "            ) : null}",
            "            {surface.required_regions.length > 0 ? (",
            "              <div>",
            f"                <Typography.Text strong>{required_regions_title}</Typography.Text>",
            "                <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>",
            "                  {surface.required_regions.map((item) => <Tag key={item} color=\"purple\">{item}</Tag>)}",
            "                </div>",
            "              </div>",
            "            ) : null}",
            "            {surface.compiled_interactions.length > 0 ? (",
            "              <div>",
            f"                <Typography.Text strong>{interaction_binding_title}</Typography.Text>",
            "                <div style={{ marginTop: 8, display: 'grid', gap: 8 }}>",
            "                  {surface.compiled_interactions.map((item, index) => (",
            "                    <Card key={item.interaction_id || String(index)} size=\"small\">",
            "                      <Space direction=\"vertical\" size={4} style={{ width: '100%' }}>",
            "                        <Typography.Text strong>{item.interaction_id || 'interaction'}</Typography.Text>",
            "                        <Typography.Paragraph style={{ marginBottom: 0 }}>",
            "                          {[item.trigger_kind, item.binding_mode, item.domain_service, item.api_endpoint].filter(Boolean).join(' · ') || '—'}",
            "                        </Typography.Paragraph>",
            "                        {(item.next_page_id || item.failure_route || item.readiness_status || item.blocked_reason) ? (",
            "                          <Typography.Paragraph type=\"secondary\" style={{ marginBottom: 0 }}>",
            "                            {[item.next_page_id ? `next: ${item.next_page_id}` : '', item.failure_route ? `failure: ${item.failure_route}` : '', item.readiness_status ? `status: ${item.readiness_status}` : '', item.blocked_reason ? `reason: ${item.blocked_reason}` : ''].filter(Boolean).join(' · ')}",
            "                          </Typography.Paragraph>",
            "                        ) : null}",
            "                      </Space>",
            "                    </Card>",
            "                  ))}",
            "                </div>",
            "              </div>",
            "            ) : null}",
            "            {surface.next_route_candidates.length > 0 ? (",
            "              <div>",
            f"                <Typography.Text strong>{next_routes_title}</Typography.Text>",
            "                <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>",
            "                  {surface.next_route_candidates.map((item) => <Tag key={item} color=\"green\">{item}</Tag>)}",
            "                </div>",
            "              </div>",
            "            ) : null}",
            "          </Space>",
            "        ) : (",
            f"          <Typography.Paragraph style={{ marginBottom: 0 }}>{no_contract_anchor_hint}</Typography.Paragraph>",
            "        )}",
            "      </Card>",
            f"      <Card title={json.dumps(work_area_title, ensure_ascii=False)}>",
            f"        <Typography.Paragraph>{work_area_hint}</Typography.Paragraph>",
            "        <Form",
            "          layout=\"vertical\"",
            "          onFinish={(values) => {",
            "            const normalized = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, String(value ?? '')]));",
            "            setSubmitted(normalized);",
            "          }}",
            "        >",
            "          {surface.user_inputs.map((item) => (",
            "            <Form.Item",
            "              key={item.field}",
            "              label={item.field}",
            "              name={item.field}",
            "              rules={[{ required: item.required, message: item.field + "
            + json.dumps(f" {required_message_suffix}", ensure_ascii=False)
            + " }]}",
            "              extra={item.validation}",
            "            >",
            f"              <Input placeholder={{item.validation || {json.dumps(input_placeholder, ensure_ascii=False)}}} />",
            "            </Form.Item>",
            "          ))}",
            f"          <Button htmlType=\"submit\" type=\"primary\">{save_draft_label}</Button>",
            "        </Form>",
            "      </Card>",
            f"      <Card title={json.dumps(current_context_title, ensure_ascii=False)}>",
            f"        {{submitted ? <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{{JSON.stringify(submitted, null, 2)}}</pre> : <Typography.Paragraph style={{ marginBottom: 0 }}>{submitted_hint}</Typography.Paragraph>}}",
            "      </Card>",
            f"      <Card title={json.dumps(data_signals_title, ensure_ascii=False)}>",
            "        <Space wrap>",
            "          {surface.presentation.map((item) => <Tag key={item}>{item}</Tag>)}",
            "        </Space>",
            "      </Card>",
            f"      <Card title={json.dumps(page_states_title, ensure_ascii=False)}>",
            "        <ul>",
            f"          <li><strong>{loading_label}</strong> {{surface.states.loading}}</li>",
            f"          <li><strong>{success_label}</strong> {{surface.states.success}}</li>",
            f"          <li><strong>{empty_label}</strong> {{surface.states.empty}}</li>",
            f"          <li><strong>{error_label}</strong> {{surface.states.error}}</li>",
            "        </ul>",
            "      </Card>",
            f"      <Card title={json.dumps(next_steps_title, ensure_ascii=False)}>",
            "        <ol>",
            "          {surface.actions.map((item) => (",
            "            <li key={item.action}>",
            f"              <strong>{{item.action}}</strong> {{` {success_prefix}: ${{item.on_success}}. {error_prefix}: ${{item.on_error}}.`}}",
            "            </li>",
            "          ))}",
            "        </ol>",
            "      </Card>",
            "    </Space>",
            "  );",
            "}",
            "",
            "function HomePage() {",
            "  const primarySurface = surfaces[0] ?? null;",
            "  return (",
            "    <Space direction=\"vertical\" size={16} style={{ width: '100%' }}>",
            "      <Card>",
            "        <Space direction=\"vertical\" size={8} style={{ width: '100%' }}>",
            f"          <Typography.Text type=\"secondary\">{ui_text(locale, 'delivery_workspace')}</Typography.Text>",
            f"          <Typography.Title level={{2}} style={{{{ margin: 0 }}}}>{ui_text(locale, 'operate_runnable_workflow')}</Typography.Title>",
            f"          <Typography.Paragraph style={{{{ marginBottom: 0 }}}}>{ui_text(locale, 'workspace_intro_scaffold')}</Typography.Paragraph>",
            f"          {{primarySurface ? <Link to={{`/${{primarySurface.route}}`}}>{ui_text(locale, 'open_primary_workspace')}</Link> : null}}",
            "        </Space>",
            "      </Card>",
            f"      <Card title={json.dumps(ui_text(locale, 'available_work_areas'), ensure_ascii=False)}>",
            "        <Space direction=\"vertical\" size={12} style={{ width: '100%' }}>",
            "          {surfaces.map((surface) => (",
            "            <Card key={surface.route} size=\"small\">",
            "              <Space direction=\"vertical\" size={6} style={{ width: '100%' }}>",
            f"                <Tag>{{{json.dumps({k: page_role_label(k, locale) for k in ['workspace','list','detail','form-flow','workflow','review']}, ensure_ascii=False)}[surface.page_role] ?? surface.page_role}}</Tag>",
            "                <Typography.Title level={4} style={{ margin: 0 }}><Link to={`/${surface.route}`}>{surface.title}</Link></Typography.Title>",
            "                <Typography.Paragraph style={{ marginBottom: 0 }}>{surface.goal}</Typography.Paragraph>",
            "                {surface.business_objects.length > 0 ? <Typography.Paragraph type=\"secondary\" style={{ marginBottom: 0 }}>{surface.business_objects.slice(0, 3).join(' / ')}</Typography.Paragraph> : null}",
            f"                <Typography.Paragraph type=\"secondary\" style={{{{ marginBottom: 0 }}}}>{{surface.actions[0]?.action ?? {json.dumps('Continue workflow' if locale == 'en' else '继续工作流', ensure_ascii=False)}}}</Typography.Paragraph>",
            "              </Space>",
            "            </Card>",
            "          ))}",
            "        </Space>",
            "      </Card>",
            "    </Space>",
            "  );",
            "}",
            "",
            "export function App() {",
            "  const location = useLocation();",
            "  const menuItems = [",
            f"    {{ key: '/', label: <Link to=\"/\">{ui_text(locale, 'workspace_menu')}</Link> }},",
            "    ...surfaces.map((surface) => ({ key: `/${surface.route}`, label: <Link to={`/${surface.route}`}>{surface.title}</Link> })),",
            "  ];",
            "  const selectedKey = menuItems.some((item) => item.key === location.pathname) ? location.pathname : '/';",
            "  return (",
            "    <Layout style={{ minHeight: '100vh', background: '#f5f7fb' }}>",
            "      <Layout.Sider width={280}>",
            "        <div style={{ padding: 20, display: 'grid', gap: 8 }}>",
            f"          <Typography.Text style={{ color: 'rgba(255,255,255,0.72)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{ui_text(locale, 'delivery_workspace')}</Typography.Text>",
            f"          <Typography.Title level={{4}} style={{{{ color: '#fff', margin: 0 }}}}>{ui_text(locale, 'runnable_mvp')}</Typography.Title>",
            "          <Typography.Paragraph style={{ color: 'rgba(255,255,255,0.78)', margin: 0 }}>",
            f"            {ui_text(locale, 'workspace_intro_generated')}",
            "          </Typography.Paragraph>",
            "        </div>",
            "        <Menu theme=\"dark\" mode=\"inline\" selectedKeys={[selectedKey]} items={menuItems} />",
            "      </Layout.Sider>",
            "      <Layout.Content style={{ padding: 24 }}>",
            "        <Routes>",
            "          <Route path=\"/\" element={<HomePage />} />",
            "          {surfaces.map((surface) => (",
            "            <Route key={surface.route} path={`/${surface.route}`} element={<SurfaceScaffoldPage surface={surface} />} />",
            "          ))}",
            "          <Route path=\"*\" element={<Navigate to=\"/\" replace />} />",
            "        </Routes>",
            "      </Layout.Content>",
            "    </Layout>",
            "  );",
            "}",
            "",
        ]
    )


def generate_project_scaffold(
    *,
    output_dir: Path,
    project_name: str,
    ui_ia_contract_path: Path | None = None,
    ui_locale: str | None = None,
) -> dict[str, object]:
    package_name = slugify(project_name)
    surface_pages = _scaffold_surface_pages(ui_ia_contract_path)
    web_locale = infer_ui_locale(
        *[
            " ".join(
                [
                    str(page.get("locale") or ""),
                    str(page.get("title") or ""),
                    str(page.get("subtitle") or ""),
                    str(page.get("goal") or ""),
                ]
            )
            for page in surface_pages
        ],
        preferred=ui_locale,
    )
    web_title = "Phase-3 Web" if web_locale == "en" else "Phase-3 工作台"
    created: list[str] = []

    def emit(path: Path, content: str, *, overwrite: bool = True) -> None:
        if overwrite or not path.exists():
            write_text(path, content)
            created.append(str(path))

    emit(
        output_dir / "package.json",
        json.dumps(
            {
                "name": package_name,
                "private": True,
                "packageManager": "pnpm@9.0.0",
                "scripts": {
                    "dev": "pnpm --filter @app/api dev",
                    "start": "pnpm --filter @app/api start",
                    "migrate": "pnpm --filter @app/api migrate",
                    "lint": "pnpm --filter @app/api lint && pnpm --filter @app/web lint && pnpm exec eslint --max-warnings=0 \"tests/**/*.ts\"",
                    "typecheck": "pnpm --filter @app/api typecheck && pnpm --filter @app/web typecheck",
                    "test": "pnpm exec vitest run --config vitest.config.ts",
                    "test:coverage": "pnpm exec vitest run --config vitest.config.ts --coverage.enabled --coverage.provider=v8 --coverage.reporter=json-summary --coverage.reporter=json --coverage.reporter=text-summary",
                    "test:coverage:unit": "pnpm exec vitest run --config vitest.config.ts tests/unit --coverage.enabled --coverage.provider=v8 --coverage.reporter=json-summary --coverage.reporter=json --coverage.reporter=text-summary --coverage.include='apps/api/src/modules/**/*.ts' --coverage.include='apps/api/src/common/**/*.ts'",
                    "build": "pnpm --filter @app/api build && pnpm --filter @app/web build",
                },
                "dependencies": {
                    "@hookform/resolvers": "^3.9.0",
                    "@tanstack/react-query": "^5.59.0",
                    "antd": "^5.21.7",
                    "jsonwebtoken": "^9.0.2",
                    "pg": "^8.13.1",
                    "react": "^19.0.0",
                    "react-dom": "^19.0.0",
                    "react-hook-form": "^7.53.0",
                    "react-router-dom": "^6.27.0",
                    "zod": "^3.23.8",
                },
                "devDependencies": {
                    "@eslint/js": "^9.20.0",
                    "@types/jsonwebtoken": "^9.0.9",
                    "@types/node": "^22.13.0",
                    "@types/pg": "^8.11.11",
                    "@types/react": "^19.0.10",
                    "@types/react-dom": "^19.0.4",
                    "@typescript-eslint/eslint-plugin": "^8.24.1",
                    "@typescript-eslint/parser": "^8.24.1",
                    "@vitest/coverage-v8": "^1.6.0",
                    "eslint": "^9.20.0",
                    "globals": "^15.14.0",
                    "typescript": "^5.7.3",
                    "vite": "^5.4.14",
                    "vitest": "^1.6.0",
                    "tsx": "^4.19.2",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "pnpm-workspace.yaml",
        "packages:\n  - apps/*\n  - packages/*\n",
    )
    emit(
        output_dir / ".npmrc",
        "manage-package-manager-versions=false\n",
    )
    emit(
        output_dir / "tsconfig.base.json",
        json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2022",
                    "module": "ESNext",
                    "moduleResolution": "Bundler",
                    "strict": True,
                    "esModuleInterop": True,
                    "allowSyntheticDefaultImports": True,
                    "forceConsistentCasingInFileNames": True,
                    "skipLibCheck": True,
                    "baseUrl": ".",
                    "jsx": "react-jsx",
                    "resolveJsonModule": True,
                    "paths": {
                        "@app/api-client": ["packages/api-client/index.ts"],
                        "@app/shared-types": ["packages/shared-types/index.ts"],
                    },
                }
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "eslint.config.mjs",
        "\n".join(
            [
                'import js from "@eslint/js";',
                'import globals from "globals";',
                'import tsParser from "@typescript-eslint/parser";',
                'import tsPlugin from "@typescript-eslint/eslint-plugin";',
                "",
                "export default [",
                '  { ignores: ["dist/**", "coverage/**", ".phase3-reports/**", "worker-runs/**"] },',
                "  js.configs.recommended,",
                "  {",
                '    files: ["**/*.ts", "**/*.tsx"],',
                "    languageOptions: {",
                "      parser: tsParser,",
                "      parserOptions: {",
                "        ecmaVersion: 2022,",
                '        sourceType: "module",',
                "        ecmaFeatures: { jsx: true },",
                "      },",
                "      globals: {",
                "        ...globals.node,",
                "        ...globals.browser,",
                "      },",
                "    },",
                '    plugins: { "@typescript-eslint": tsPlugin },',
                "    rules: {",
                "      ...tsPlugin.configs.recommended.rules,",
                '      "@typescript-eslint/no-explicit-any": "off",',
                "    },",
                "  },",
                "];",
                "",
            ]
        ),
    )
    emit(
        output_dir / "vitest.config.ts",
        "\n".join(
            [
                'import { defineConfig } from "vitest/config";',
                "",
                'const maxForks = Number(process.env.PHASE3_VITEST_MAX_FORKS ?? "2");',
                "const boundedMaxForks = Number.isFinite(maxForks) ? Math.max(1, Math.floor(maxForks)) : 2;",
                "const useSingleFork = boundedMaxForks === 1;",
                "",
                "export default defineConfig({",
                "  test: {",
                '    environment: "node",',
                '    include: ["tests/**/*.test.ts"],',
                "    fileParallelism: !useSingleFork,",
                '    pool: "forks",',
                "    poolOptions: {",
                "      forks: {",
                "        singleFork: useSingleFork,",
                "        isolate: !useSingleFork,",
                "        minForks: 1,",
                "        maxForks: boundedMaxForks,",
                "      },",
                "    },",
                "    hookTimeout: 120000,",
                "    testTimeout: 60000,",
                "    passWithNoTests: false,",
                "    reporters: [\"default\"],",
                "    coverage: {",
                '      provider: "v8",',
                '      reportsDirectory: "coverage",',
                '      reporter: ["text", "json-summary", "json"],',
                "    },",
                "  },",
                "});",
                "",
            ]
        ),
    )
    emit(
        output_dir / "scripts" / "run_vitest_targets_sequentially.py",
        bundled_script_content("run_vitest_targets_sequentially.py"),
    )
    emit(
        output_dir / ".env.example",
        "\n".join(
            [
                "POSTGRES_USER=postgres",
                "POSTGRES_PASSWORD=replace-with-a-long-random-password",
                "POSTGRES_DB=app",
                "DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:55432/${POSTGRES_DB}",
                "REDIS_URL=redis://localhost:56379",
                "OIDC_ISSUER_URL=https://example-issuer",
                "OIDC_CLIENT_ID=replace-me",
                "OIDC_CLIENT_SECRET=replace-me",
                "AUTH_TOKEN_SECRET=replace-me",
                "PHASE3_ALLOW_AUTH_CONTEXT_HEADER=false",
                "PORT=3000",
                "HOST=0.0.0.0",
                "WEB_PORT=3100",
                "API_BASE_URL=http://localhost:3000",
                "WEB_API_BASE_URL=http://api:3000",
                "VITE_API_BASE_URL=/api",
                "VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER=false",
                "API_HOST_PORT=53000",
                "WEB_HOST_PORT=53100",
                "POSTGRES_HOST_PORT=55432",
                "REDIS_HOST_PORT=56379",
                "",
            ]
        ),
    )
    emit(
        output_dir / "docker-compose.dev.yml",
        "\n".join(
            [
                "# Phase-3 runtime compose template",
                "# Runner owns COMPOSE_PROJECT_NAME and host port allocation.",
                "# Do not add container_name; run-scoped compose projects prevent cross-run teardown conflicts.",
                "services:",
                "  api:",
                "    build:",
                "      context: .",
                "      target: runtime",
                "    command: [\"pnpm\", \"--filter\", \"@app/api\", \"start:container\"]",
                "    depends_on:",
                "      - postgres",
                "      - redis",
                "    env_file:",
                "      - .env.example",
                "    environment:",
                "      DATABASE_URL: postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-app}",
                "      REDIS_URL: redis://redis:6379",
                "      PORT: 3000",
                "      HOST: 0.0.0.0",
                "      AUTH_TOKEN_SECRET: ${AUTH_TOKEN_SECRET:-replace-me}",
                "      CONTAINER_HEALTH_PORT: 3000",
                "      CONTAINER_HEALTH_PATH: /healthz",
                "    ports:",
                "      - \"${API_HOST_PORT:-53000}:3000\"",
                "    healthcheck:",
                "      test: [\"CMD-SHELL\", \"wget -q -O - http://127.0.0.1:3000/healthz >/dev/null 2>&1\"]",
                "      interval: 10s",
                "      timeout: 3s",
                "      retries: 5",
                "  web:",
                "    build:",
                "      context: .",
                "      target: web-runtime",
                "    command: [\"pnpm\", \"--filter\", \"@app/web\", \"start\"]",
                "    depends_on:",
                "      - api",
                "    env_file:",
                "      - .env.example",
                "    environment:",
                "      HOST: 0.0.0.0",
                "      WEB_PORT: 3100",
                "      WEB_API_BASE_URL: http://api:3000",
                "      VITE_API_BASE_URL: /api",
                "      CONTAINER_HEALTH_PORT: 3100",
                "      CONTAINER_HEALTH_PATH: /",
                "    ports:",
                "      - \"${WEB_HOST_PORT:-53100}:3100\"",
                "    healthcheck:",
                "      test: [\"CMD-SHELL\", \"wget -q -O - http://127.0.0.1:3100/ >/dev/null 2>&1\"]",
                "      interval: 10s",
                "      timeout: 3s",
                "      retries: 5",
                "  postgres:",
                "    image: postgres:16",
                "    environment:",
                "      POSTGRES_USER: ${POSTGRES_USER:-postgres}",
                "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}",
                "      POSTGRES_DB: ${POSTGRES_DB:-app}",
                "    ports:",
                "      - \"127.0.0.1:${POSTGRES_HOST_PORT:-55432}:5432\"",
                "  redis:",
                "    image: redis:7",
                "    ports:",
                "      - \"127.0.0.1:${REDIS_HOST_PORT:-56379}:6379\"",
                "",
            ]
        ),
    )
    emit(
        output_dir / "docker-compose.prod.yml",
        "\n".join(
            [
                "services:",
                "  api:",
                "    build:",
                "      context: .",
                "      target: runtime",
                "    command: [\"pnpm\", \"--filter\", \"@app/api\", \"start:container\"]",
                "    depends_on:",
                "      - postgres",
                "      - redis",
                "    environment:",
                "      DATABASE_URL: ${DATABASE_URL:?DATABASE_URL is required}",
                "      REDIS_URL: ${REDIS_URL:-redis://redis:6379}",
                "      OIDC_ISSUER_URL: ${OIDC_ISSUER_URL}",
                "      OIDC_CLIENT_ID: ${OIDC_CLIENT_ID}",
                "      OIDC_CLIENT_SECRET: ${OIDC_CLIENT_SECRET}",
                "      AUTH_TOKEN_SECRET: ${AUTH_TOKEN_SECRET:?AUTH_TOKEN_SECRET is required}",
                "      PHASE3_ALLOW_AUTH_CONTEXT_HEADER: ${PHASE3_ALLOW_AUTH_CONTEXT_HEADER:-false}",
                "      PORT: ${PORT:-3000}",
                "      HOST: ${HOST:-0.0.0.0}",
                "      CONTAINER_HEALTH_PORT: ${PORT:-3000}",
                "      CONTAINER_HEALTH_PATH: /healthz",
                "    ports:",
                "      - \"${API_HOST_PORT:-53000}:3000\"",
                "    healthcheck:",
                "      test: [\"CMD-SHELL\", \"wget -q -O - http://127.0.0.1:3000/healthz >/dev/null 2>&1\"]",
                "      interval: 10s",
                "      timeout: 3s",
                "      retries: 5",
                "  web:",
                "    build:",
                "      context: .",
                "      target: web-runtime",
                "    command: [\"pnpm\", \"--filter\", \"@app/web\", \"start\"]",
                "    depends_on:",
                "      - api",
                "    environment:",
                "      HOST: ${HOST:-0.0.0.0}",
                "      WEB_PORT: ${WEB_PORT:-3100}",
                "      WEB_API_BASE_URL: ${WEB_API_BASE_URL:-http://api:3000}",
                "      VITE_API_BASE_URL: ${VITE_API_BASE_URL:-/api}",
                "      CONTAINER_HEALTH_PORT: ${WEB_PORT:-3100}",
                "      CONTAINER_HEALTH_PATH: /",
                "    ports:",
                "      - \"${WEB_HOST_PORT:-53100}:3100\"",
                "    healthcheck:",
                "      test: [\"CMD-SHELL\", \"wget -q -O - http://127.0.0.1:3100/ >/dev/null 2>&1\"]",
                "      interval: 10s",
                "      timeout: 3s",
                "      retries: 5",
                "  postgres:",
                "    image: postgres:16",
                "    environment:",
                "      POSTGRES_USER: ${POSTGRES_USER:-postgres}",
                "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}",
                "      POSTGRES_DB: ${POSTGRES_DB:-app}",
                "    ports:",
                "      - \"127.0.0.1:${POSTGRES_HOST_PORT:-55432}:5432\"",
                "  redis:",
                "    image: redis:7",
                "    ports:",
                "      - \"127.0.0.1:${REDIS_HOST_PORT:-56379}:6379\"",
                "",
            ]
        ),
    )
    emit(
        output_dir / ".dockerignore",
        "\n".join(
            [
                "node_modules",
                ".pnpm-store",
                "coverage",
                ".phase3-reports",
                "worker-runs",
                "apps/api/dist",
                "apps/web/dist",
                "packages/*/dist",
                "*.log",
                ".git",
                "",
            ]
        ),
    )
    emit(
        output_dir / "Dockerfile",
        "\n".join(
            [
                "# syntax=docker/dockerfile:1.6",
                "FROM node:20-alpine AS deps",
                "WORKDIR /app",
                "RUN corepack enable",
                "ENV PNPM_HOME=/pnpm",
                "ENV PATH=$PNPM_HOME:$PATH",
                "",
                "COPY package.json pnpm-workspace.yaml .npmrc tsconfig.base.json eslint.config.mjs vitest.config.ts ./",
                "COPY apps/api/package.json apps/api/package.json",
                "COPY apps/web/package.json apps/web/package.json",
                "COPY packages/shared-types/package.json packages/shared-types/package.json",
                "COPY packages/api-client/package.json packages/api-client/package.json",
                "RUN --mount=type=cache,id=phase3-pnpm-store,target=/pnpm/store pnpm install --frozen-lockfile=false --store-dir /pnpm/store",
                "",
                "FROM deps AS api-builder",
                "COPY apps/api ./apps/api",
                "COPY packages ./packages",
                "COPY db ./db",
                "COPY tests ./tests",
                "RUN pnpm --filter @app/api build",
                "",
                "FROM deps AS web-builder",
                "COPY apps/web ./apps/web",
                "COPY packages ./packages",
                "RUN pnpm --filter @app/web build",
                "",
                "FROM node:20-alpine AS web-runtime",
                "WORKDIR /app",
                "RUN addgroup -S nodeapp && adduser -S nodeapp -G nodeapp",
                "RUN corepack enable",
                "COPY --from=web-builder --chown=nodeapp:nodeapp /app /app",
                "ENV CONTAINER_HEALTH_PORT=3100",
                "ENV CONTAINER_HEALTH_PATH=/",
                "USER nodeapp",
                "EXPOSE 3100",
                "HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 CMD wget -q -O - \"http://127.0.0.1:${CONTAINER_HEALTH_PORT}${CONTAINER_HEALTH_PATH}\" >/dev/null 2>&1 || exit 1",
                "CMD [\"pnpm\", \"--filter\", \"@app/web\", \"start\"]",
                "",
                "FROM node:20-alpine AS runtime",
                "WORKDIR /app",
                "RUN addgroup -S nodeapp && adduser -S nodeapp -G nodeapp",
                "RUN corepack enable",
                "COPY --from=api-builder --chown=nodeapp:nodeapp /app /app",
                "ENV CONTAINER_HEALTH_PORT=3000",
                "ENV CONTAINER_HEALTH_PATH=/healthz",
                "USER nodeapp",
                "EXPOSE 3000",
                "HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 CMD wget -q -O - \"http://127.0.0.1:${CONTAINER_HEALTH_PORT}${CONTAINER_HEALTH_PATH}\" >/dev/null 2>&1 || exit 1",
                "CMD [\"pnpm\", \"--filter\", \"@app/api\", \"start:container\"]",
                "",
            ]
        ),
    )
    emit(
        output_dir / ".github" / "workflows" / "ci.yml",
        "\n".join(
            [
                "name: ci",
                "on:",
                "  push:",
                "  pull_request:",
                "jobs:",
                "  verify:",
                "    runs-on: ubuntu-latest",
                "    steps:",
                "      - uses: actions/checkout@v4",
                "      - uses: pnpm/action-setup@v4",
                "        with:",
                "          version: 9",
                "      - uses: actions/setup-node@v4",
                "        with:",
                "          node-version: 20",
                "          cache: pnpm",
                "      - run: pnpm install --frozen-lockfile=false",
                "      - run: pnpm lint",
                "      - run: pnpm typecheck",
                "      - run: pnpm test",
                "      - run: pnpm test:coverage",
                "      - run: pnpm build",
                "",
            ]
        ),
    )

    emit(
        output_dir / "apps" / "api" / "package.json",
        json.dumps(
            {
                "name": "@app/api",
                "private": True,
                "type": "module",
                "scripts": {
                    "dev": "pnpm build && node dist/main.js",
                    "start": "node dist/main.js",
                    "start:container": "sh -lc 'until node dist/runtime/migrate.js; do sleep 1; done; node dist/main.js'",
                    "migrate": "node dist/runtime/migrate.js",
                    "lint": "eslint --max-warnings=0 \"src/**/*.ts\"",
                    "typecheck": "tsc --noEmit -p tsconfig.json",
                    "test": "vitest run --config ../../vitest.config.ts ../../tests/unit/api ../../tests/contracts ../../tests/scenarios ../../tests/replays",
                    "build": "tsc -p tsconfig.build.json",
                },
                "dependencies": {
                    "jsonwebtoken": "^9.0.2",
                    "pg": "^8.13.1",
                },
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "apps" / "api" / "tsconfig.json",
        json.dumps(
            {
                "extends": "../../tsconfig.base.json",
                "compilerOptions": {
                    "lib": ["ES2022"],
                    "outDir": "./dist",
                    "rootDir": "./src",
                    "types": ["node"],
                },
                "include": ["src/**/*.ts"],
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "apps" / "api" / "tsconfig.build.json",
        json.dumps(
            {
                "extends": "./tsconfig.json",
                "compilerOptions": {
                    "declaration": False,
                    "sourceMap": False,
                },
                "include": ["src/**/*.ts"],
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "apps" / "api" / "src" / "main.ts",
        "\n".join(
            [
                'import { createServer } from "node:http";',
                'import { URL, pathToFileURL } from "node:url";',
                'import { handleGeneratedApiRequest } from "./generated-api-router.js";',
                'import { checkDatabaseReadiness } from "./runtime/database.js";',
                "",
                "const host = process.env.HOST || \"0.0.0.0\";",
                "const port = Number.parseInt(process.env.PORT || \"3000\", 10);",
                "",
                "function sendJson(",
                "  response: import(\"node:http\").ServerResponse,",
                "  statusCode: number,",
                "  payload: Record<string, unknown>,",
                "): void {",
                "  response.statusCode = statusCode;",
                "  response.setHeader(\"content-type\", \"application/json; charset=utf-8\");",
                "  response.end(JSON.stringify(payload));",
                "}",
                "",
                "export async function createApiServer() {",
                "  return createServer(async (request, response) => {",
                "    const method = request.method || \"GET\";",
                "    const url = new URL(request.url || \"/\", `http://${request.headers.host || \"localhost\"}`);",
                "",
                "    if (method === \"GET\" && url.pathname === \"/healthz\") {",
                "      sendJson(response, 200, {",
                "        status: \"ok\",",
                "        service: \"phase3-api\",",
                "        startup_mode: \"runnable-runtime-baseline\",",
                "      });",
                "      return;",
                "    }",
                "",
                "    if (method === \"GET\" && url.pathname === \"/readyz\") {",
                "      const database = await checkDatabaseReadiness();",
                "      sendJson(response, database.ready ? 200 : 503, {",
                "        status: database.ready ? \"ready\" : \"not_ready\",",
                "        database,",
                "      });",
                "      return;",
                "    }",
                "",
                "    if (method === \"GET\" && url.pathname === \"/\") {",
                "      sendJson(response, 200, {",
                "        service: \"phase3-api\",",
                "        docs_hint: \"use /healthz or /readyz for runtime smoke checks\",",
                "      });",
                "      return;",
                "    }",
                "",
                "    const handled = await handleGeneratedApiRequest(request, response, { sendJson });",
                "    if (handled) {",
                "      return;",
                "    }",
                "",
                "    sendJson(response, 404, {",
                "      error_kind: \"system_error\",",
                "      error_code: \"route_not_found\",",
                "    });",
                "  });",
                "}",
                "",
                "export async function bootstrapApi(): Promise<import(\"node:http\").Server> {",
                "  const server = await createApiServer();",
                "  await new Promise<void>((resolve) => {",
                "    server.listen(port, host, () => resolve());",
                "  });",
                "  return server;",
                "}",
                "",
                "const directRun = (() => {",
                "  const entry = process.argv[1];",
                "  return Boolean(entry && import.meta.url === pathToFileURL(entry).href);",
                "})();",
                "",
                "if (directRun) {",
                "  bootstrapApi().then((server) => {",
                "    server.on(\"listening\", () => {",
                "      process.stdout.write(`phase3-api listening on http://${host}:${port}\\n`);",
                "    });",
                "  });",
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "api" / "src" / "generated-api-router.ts",
        "\n".join(
            [
                "// Derived artifact authority: pending-compiled-bindings",
                "// This placeholder router must be replaced by compiled-binding-derived routing during Phase-3 implementation.",
                'import type { IncomingMessage, ServerResponse } from "node:http";',
                "",
                "export async function handleGeneratedApiRequest(",
                "  _request: IncomingMessage,",
                "  _response: ServerResponse,",
                "  _helpers: { sendJson: (response: ServerResponse, statusCode: number, payload: Record<string, unknown>) => void },",
                "): Promise<boolean> {",
                "  return false;",
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "api" / "src" / "runtime" / "database.ts",
        "\n".join(
            [
                'import { Client } from "pg";',
                "",
                "export interface DatabaseReadiness {",
                "  ready: boolean;",
                "  reason?: string;",
                "  provider?: string;",
                "}",
                "",
                "function databaseConnectionTimeoutMillis(): number {",
                "  return Number.parseInt(process.env.PHASE3_DB_CONNECT_TIMEOUT_MS || '3000', 10);",
                "}",
                "",
                "function databaseStatementTimeoutMillis(): number {",
                "  return Number.parseInt(process.env.PHASE3_DB_STATEMENT_TIMEOUT_MS || '5000', 10);",
                "}",
                "",
                "function createDatabaseClient(connectionString: string): Client {",
                "  return new Client({",
                "    connectionString,",
                "    connectionTimeoutMillis: databaseConnectionTimeoutMillis(),",
                "    statement_timeout: databaseStatementTimeoutMillis(),",
                "    query_timeout: databaseStatementTimeoutMillis(),",
                "  });",
                "}",
                "",
                "export async function checkDatabaseReadiness(): Promise<DatabaseReadiness> {",
                "  const connectionString = process.env.DATABASE_URL || \"\";",
                "  if (!connectionString) {",
                "    return { ready: false, reason: \"database_url_missing\" };",
                "  }",
                "  const client = createDatabaseClient(connectionString);",
                "  try {",
                "    await client.connect();",
                "    await client.query(\"select 1 as ok\");",
                "    return { ready: true, provider: \"postgresql\" };",
                "  } catch (error) {",
                "    return { ready: false, reason: error instanceof Error ? error.message : \"db_probe_failed\" };",
                "  } finally {",
                "    await client.end().catch(() => undefined);",
                "  }",
                "}",
                "",
                "export async function runMigrations(sqlDocuments: string[]): Promise<{ applied: number }> {",
                "  const connectionString = process.env.DATABASE_URL || \"\";",
                "  if (!connectionString) {",
                "    throw new Error(\"DATABASE_URL is required for migrations\");",
                "  }",
                "  const client = createDatabaseClient(connectionString);",
                "  await client.connect();",
                "  try {",
                "    await client.query(\"CREATE SCHEMA IF NOT EXISTS public\");",
                "    await client.query(\"SET search_path TO public\");",
                "    for (const document of sqlDocuments) {",
                "      if (document.trim()) {",
                "        await client.query(document);",
                "      }",
                "    }",
                "    return { applied: sqlDocuments.length };",
                "  } finally {",
                "    await client.end();",
                "  }",
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "api" / "src" / "runtime" / "migrate.ts",
        "\n".join(
            [
                'import { readdir, readFile } from "node:fs/promises";',
                'import { join } from "node:path";',
                'import { fileURLToPath } from "node:url";',
                'import { runMigrations } from "./database.js";',
                "",
                "async function loadMigrations(): Promise<string[]> {",
                "  const runtimeDir = fileURLToPath(new URL('.', import.meta.url));",
                "  const migrationsDir = join(runtimeDir, '../../../../db/migrations');",
                "  const entries = (await readdir(migrationsDir)).filter((entry) => entry.endsWith('.sql')).sort();",
                "  const documents: string[] = [];",
                "  for (const entry of entries) {",
                "    documents.push(await readFile(join(migrationsDir, entry), 'utf-8'));",
                "  }",
                "  return documents;",
                "}",
                "",
                "async function main(): Promise<void> {",
                "  const documents = await loadMigrations();",
                "  const result = await runMigrations(documents);",
                "  process.stdout.write(`phase3 migrations applied: ${result.applied}\\n`);",
                "}",
                "",
                "main().catch((error) => {",
                "  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\\n`);",
                "  process.exitCode = 1;",
                "});",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "api" / "src" / "common" / "envelope.ts",
        "\n".join(
            [
                "export interface ApiEnvelope<TData> {",
                "  trace_id: string;",
                "  request_id?: string;",
                "  data: TData;",
                "  meta?: Record<string, unknown>;",
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "api" / "src" / "common" / "errors.ts",
        "\n".join(
            [
                "export interface ApiErrorEnvelope {",
                "  error_kind: string;",
                "  error_code: string;",
                "  retryability?: string;",
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "api" / "src" / "common" / "pagination.ts",
        "export interface CursorPageRequest { cursor?: string; limit?: number; }\n",
    )

    emit(
        output_dir / "apps" / "web" / "package.json",
        json.dumps(
            {
                "name": "@app/web",
                "private": True,
                "type": "module",
                "scripts": {
                    "dev": "vite --host 0.0.0.0 --port ${WEB_PORT:-3100}",
                    "lint": "eslint --max-warnings=0 \"app/**/*.{ts,tsx}\"",
                    "typecheck": "tsc --noEmit -p tsconfig.json",
                    "test": "vitest run --config ../../vitest.config.ts ../../tests/unit/web ../../tests/scenarios ../../tests/replays",
                    "build": "tsc -p tsconfig.build.json && vite build",
                    "start": "tsx app/server.ts",
                },
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "apps" / "web" / "tsconfig.json",
        json.dumps(
            {
                "extends": "../../tsconfig.base.json",
                "compilerOptions": {
                    "lib": ["DOM", "DOM.Iterable", "ES2022"],
                    "outDir": "./dist",
                    "rootDir": ".",
                    "types": ["node"],
                },
                "include": ["app/**/*.ts", "app/**/*.tsx", "vite.config.ts"],
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "apps" / "web" / "tsconfig.build.json",
        json.dumps(
            {
                "extends": "./tsconfig.json",
                "compilerOptions": {
                    "declaration": False,
                    "sourceMap": False,
                },
                "include": ["app/**/*.ts", "app/**/*.tsx", "vite.config.ts"],
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "apps" / "web" / "index.html",
        "\n".join(
            [
                "<!doctype html>",
                f'<html lang="{web_locale}">',
                "  <head>",
                '    <meta charset="UTF-8" />',
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
                f"    <title>{web_title}</title>",
                "  </head>",
                "  <body>",
                '    <div id="root"></div>',
                '    <script type="module" src="/app/main.tsx"></script>',
                "  </body>",
                "</html>",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "web" / "vite.config.ts",
        "\n".join(
            [
                'import { defineConfig } from "vite";',
                "",
                "export default defineConfig({",
                "  build: {",
                '    outDir: "dist",',
                "    emptyOutDir: true,",
                "  },",
                "});",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "web" / "app" / "page.tsx",
        "\n".join(
            [
                "export default function HomePage() {",
                '  return <main data-phase3-surface="home">Phase-3 scaffold home</main>;',
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "web" / "app" / "theme.css",
        "\n".join(
            [
                ':root {',
                '  color-scheme: light;',
                '  font-family: "IBM Plex Sans", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;',
                '}',
                '',
                'html, body, #root {',
                '  min-height: 100%;',
                '}',
                '',
                'body {',
                '  margin: 0;',
                '  background: radial-gradient(circle at top, rgba(190, 242, 233, 0.35), transparent 28%), linear-gradient(180deg, #edf3fb 0%, #f7f9fc 32%, #fbfcfe 100%);',
                '  color: #0f172a;',
                '  font-family: inherit;',
                '  line-height: 1.5;',
                '}',
                '',
                'a {',
                '  color: #0f766e;',
                '  text-decoration: none;',
                '}',
                '',
                'a:hover {',
                '  color: #0b5f5a;',
                '}',
                '',
                '.phase3-app-shell {',
                '  background: transparent !important;',
                '}',
                '',
                '.phase3-app-shell__sider,',
                '.phase3-app-shell__sider .ant-layout-sider-children {',
                '  background: linear-gradient(180deg, #0b1625 0%, #10263b 60%, #12354a 100%) !important;',
                '}',
                '',
                '.phase3-app-shell__sider {',
                '  box-shadow: 24px 0 60px rgba(2, 12, 27, 0.35);',
                '}',
                '',
                '.phase3-app-shell__brand {',
                '  border-bottom: 1px solid rgba(255, 255, 255, 0.08);',
                '}',
                '',
                '.phase3-app-shell__content {',
                '  background: transparent !important;',
                '}',
                '',
                '.phase3-app-shell__canvas {',
                '  width: min(1320px, 100%);',
                '  margin: 0 auto;',
                '}',
                '',
                '.phase3-chip-row {',
                '  display: flex;',
                '  gap: 8px;',
                '  flex-wrap: wrap;',
                '}',
                '',
                '.phase3-chip {',
                '  display: inline-flex;',
                '  align-items: center;',
                '  gap: 6px;',
                '  border-radius: 999px;',
                '  padding: 6px 12px;',
                '  border: 1px solid rgba(148, 163, 184, 0.24);',
                '  background: rgba(255, 255, 255, 0.9);',
                '  color: #334155;',
                '  font-size: 12px;',
                '  font-weight: 600;',
                '}',
                '',
                '.phase3-chip--sidebar {',
                '  border-color: rgba(148, 163, 184, 0.22);',
                '  background: rgba(255, 255, 255, 0.1);',
                '  color: #e2e8f0;',
                '}',
                '',
                '.phase3-app-menu.ant-menu {',
                '  background: transparent !important;',
                '  border-inline-end: none !important;',
                '  padding: 12px !important;',
                '}',
                '',
                '.phase3-app-menu .ant-menu-item {',
                '  height: auto !important;',
                '  line-height: 1.35 !important;',
                '  margin: 6px 0 !important;',
                '  border-radius: 14px !important;',
                '}',
                '',
                '.phase3-app-menu .ant-menu-item a {',
                '  display: block;',
                '  padding: 12px 8px;',
                '  white-space: normal;',
                '}',
                '',
                'main[data-phase3-surface] {',
                '  width: min(1180px, 100%);',
                '  margin: 0 auto;',
                '  padding-bottom: 24px;',
                '}',
                '',
                'main[data-phase3-surface] > header,',
                'main[data-phase3-surface] > section,',
                'main[data-phase3-surface] aside > section,',
                'main[data-phase3-surface] section article,',
                'main[data-phase3-surface] form fieldset {',
                '  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.07);',
                '}',
                '',
                'main[data-phase3-surface] > header,',
                'main[data-phase3-surface] > section,',
                'main[data-phase3-surface] aside > section {',
                '  border-color: #dbe4f0 !important;',
                '  background: rgba(255, 255, 255, 0.92) !important;',
                '  backdrop-filter: blur(14px);',
                '}',
                '',
                'main[data-phase3-surface] section article,',
                'main[data-phase3-surface] form fieldset {',
                '  border-color: rgba(148, 163, 184, 0.24) !important;',
                '  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 252, 0.98) 100%) !important;',
                '}',
                '',
                'main[data-phase3-surface] button,',
                'main[data-phase3-surface] input,',
                'main[data-phase3-surface] select,',
                'main[data-phase3-surface] textarea {',
                '  font: inherit;',
                '}',
                '',
                'main[data-phase3-surface] button {',
                '  min-height: 42px;',
                '  cursor: pointer;',
                '  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);',
                '}',
                '',
                'main[data-phase3-surface] button:disabled {',
                '  box-shadow: none;',
                '  cursor: not-allowed;',
                '  opacity: 0.6;',
                '}',
                '',
                'main[data-phase3-surface] input,',
                'main[data-phase3-surface] select,',
                'main[data-phase3-surface] textarea {',
                '  border-radius: 12px !important;',
                '  border: 1px solid #cbd5e1 !important;',
                '  background: #fff !important;',
                '  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.03);',
                '}',
                '',
                'main[data-phase3-surface] table {',
                '  font-size: 14px;',
                '  background: #fff;',
                '}',
                '',
                'main[data-phase3-surface] th {',
                '  background: #f8fafc;',
                '  color: #475569;',
                '  font-size: 12px;',
                '  font-weight: 700;',
                '  letter-spacing: 0.08em;',
                '  text-transform: uppercase;',
                '}',
                '',
                '@media (max-width: 1100px) {',
                '  .phase3-app-shell__content {',
                '    padding: 18px !important;',
                '  }',
                '',
                '  main[data-phase3-surface] {',
                '    width: 100%;',
                '  }',
                '}',
                '',
            ]
        ),
    )
    emit(
        output_dir / "apps" / "web" / "app" / "main.tsx",
        "\n".join(
            [
                'import "antd/dist/reset.css";',
                'import "./theme.css";',
                'import { StrictMode } from "react";',
                'import { createRoot } from "react-dom/client";',
                'import { BrowserRouter } from "react-router-dom";',
                'import { QueryClient, QueryClientProvider } from "@tanstack/react-query";',
                'import { App } from "./ui-app";',
                "",
                "const queryClient = new QueryClient();",
                "const root = document.getElementById(\"root\");",
                "if (!root) throw new Error(\"web root mount node not found\");",
                "",
                "createRoot(root).render(",
                "  <StrictMode>",
                "    <QueryClientProvider client={queryClient}>",
                "      <BrowserRouter>",
                "        <App />",
                "      </BrowserRouter>",
                "    </QueryClientProvider>",
                "  </StrictMode>,",
                ");",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "web" / "app" / "api.ts",
        "\n".join(
            [
                "const STORAGE_KEY = \"phase3-role-session\";",
                "",
                "type RoleSession = {",
                "  currentRole?: string;",
                "};",
                "",
                "function readRoleSession(): RoleSession {",
                "  if (typeof window === \"undefined\" || typeof window.localStorage === \"undefined\") {",
                "    return {};",
                "  }",
                "  try {",
                "    const raw = window.localStorage.getItem(STORAGE_KEY);",
                "    if (!raw) {",
                "      return {};",
                "    }",
                "    const parsed = JSON.parse(raw) as unknown;",
                "    if (!parsed || typeof parsed !== \"object\" || Array.isArray(parsed)) {",
                "      return {};",
                "    }",
                "    const source = parsed as Record<string, unknown>;",
                "    const currentRole = typeof source.currentRole === \"string\" ? source.currentRole.trim() : \"\";",
                "    return currentRole ? { currentRole } : {};",
                "  } catch {",
                "    return {};",
                "  }",
                "}",
                "",
                "function roleSessionAuthHeader(): string | undefined {",
                "  const currentRole = String(readRoleSession().currentRole || '').trim();",
                "  if (!currentRole) {",
                "    return undefined;",
                "  }",
                "  const slug = currentRole.toLowerCase().replace(/[^a-z0-9]+/g, \"-\").replace(/^-+|-+$/g, \"\") || \"workspace\";",
                "  return encodeURIComponent(JSON.stringify({",
                "    sub: `phase3-${slug}`,",
                "    subject_id: `phase3-${slug}`,",
                "    sid: `phase3-${slug}-session`,",
                "    session_id: `phase3-${slug}-session`,",
                "    role: currentRole,",
                "    roles: [currentRole],",
                "    oidc_claims: { role: currentRole },",
                "  }));",
                "}",
                "",
                "function withPhase3AuthHeaders(init?: globalThis.RequestInit): globalThis.RequestInit {",
                "  const headers = new Headers(init?.headers ?? {});",
                "  const allowAuthContextHeader = import.meta.env.VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER === \"true\";",
                "  if (allowAuthContextHeader && !headers.has(\"authorization\") && !headers.has(\"x-phase3-auth-context\")) {",
                "    const authContext = roleSessionAuthHeader();",
                "    if (authContext) {",
                "      headers.set(\"x-phase3-auth-context\", authContext);",
                "    }",
                "  }",
                "  return { ...init, headers };",
                "}",
                "",
                "export async function callApi(path: string, init?: globalThis.RequestInit): Promise<{ status: number; body: string }> {",
                "  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? \"/api\";",
                "  const normalizedBase = base.replace(/\\/$/, \"\");",
                "  const requestInit = withPhase3AuthHeaders(init);",
                "  if (path.startsWith(\"http://\") || path.startsWith(\"https://\")) {",
                "    const response = await fetch(path, requestInit);",
                "    const body = await response.text();",
                "    return { status: response.status, body };",
                "  }",
                "  const normalizedPath = path.startsWith(\"/\") ? path : `/${path}`;",
                "  const baseIsAbsolute = /^[a-z]+:\\/\\//i.test(normalizedBase);",
                "  const hasRelativeBasePrefix = !baseIsAbsolute && normalizedBase.length > 0 && (normalizedPath === normalizedBase || normalizedPath.startsWith(`${normalizedBase}/`));",
                "  const requestTarget = hasRelativeBasePrefix ? normalizedPath : `${normalizedBase}${normalizedPath}`;",
                "  const response = await fetch(baseIsAbsolute ? `${normalizedBase}${normalizedPath}` : requestTarget, requestInit);",
                "  const body = await response.text();",
                "  return { status: response.status, body };",
                "}",
                "",
            ]
        ),
    )
    emit(
        output_dir / "apps" / "web" / "app" / "vite-env.d.ts",
        "/// <reference types=\"vite/client\" />\n",
    )
    emit(
        output_dir / "apps" / "web" / "app" / "ui-app.tsx",
        _render_scaffold_ui_app(surface_pages),
    )
    emit(
        output_dir / "apps" / "web" / "app" / "server.ts",
        "\n".join(
            [
                "import { createServer } from \"node:http\";",
                "import { readFile } from \"node:fs/promises\";",
                "import { join } from \"node:path\";",
                "import { URL } from \"node:url\";",
                "",
                "const host = process.env.HOST ?? \"0.0.0.0\";",
                "const port = Number.parseInt(process.env.WEB_PORT ?? \"3100\", 10);",
                "const apiBaseUrl = process.env.WEB_API_BASE_URL ?? \"http://localhost:3000\";",
                "const normalizedApiBaseUrl = apiBaseUrl.replace(/\\/$/, \"\");",
                "",
                "const distDir = join(process.cwd(), \"dist\");",
                "",
                "async function buildRuntimeProof(): Promise<Record<string, unknown>> {",
                "  const checks = await Promise.allSettled([",
                "    fetch(`${normalizedApiBaseUrl}/healthz`),",
                "    fetch(`${normalizedApiBaseUrl}/readyz`),",
                "  ]);",
                "  const [healthz, readyz] = checks;",
                "  return {",
                "    ok: healthz.status === 'fulfilled' && readyz.status === 'fulfilled' && healthz.value.ok && readyz.value.ok,",
                "    api_base_url: normalizedApiBaseUrl,",
                "    healthz: healthz.status === 'fulfilled' ? { status: healthz.value.status, ok: healthz.value.ok } : { error: String(healthz.reason) },",
                "    readyz: readyz.status === 'fulfilled' ? { status: readyz.value.status, ok: readyz.value.ok } : { error: String(readyz.reason) },",
                "    checked_at: new Date().toISOString(),",
                "  };",
                "}",
                "",
                "function buildUpstreamHeaders(request: import(\"node:http\").IncomingMessage): Headers {",
                "  const headers = new Headers();",
                "  for (const [key, value] of Object.entries(request.headers)) {",
                "    if (value == null || key === 'host' || key === 'connection' || key === 'content-length') {",
                "      continue;",
                "    }",
                "    if (Array.isArray(value)) {",
                "      headers.set(key, value.join(', '));",
                "      continue;",
                "    }",
                "    headers.set(key, value);",
                "  }",
                "  return headers;",
                "}",
                "",
                "function copyUpstreamHeaders(upstreamResponse: Response, response: import(\"node:http\").ServerResponse): void {",
                "  for (const [key, value] of upstreamResponse.headers.entries()) {",
                "    if (key === 'content-length' || key === 'transfer-encoding' || key === 'connection') {",
                "      continue;",
                "    }",
                "    response.setHeader(key, value);",
                "  }",
                "}",
                "",
                "createServer(async (req, res) => {",
                "  const url = new URL(req.url ?? '/', `http://${host}:${port}`);",
                "  if (url.pathname === '/runtime-proof') {",
                "    const proof = await buildRuntimeProof();",
                "    res.statusCode = (proof.ok as boolean) ? 200 : 503;",
                "    res.setHeader('content-type', 'application/json; charset=utf-8');",
                "    res.end(JSON.stringify(proof));",
                "    return;",
                "  }",
                "",
                "  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {",
                "    const upstream = `${normalizedApiBaseUrl}${url.pathname}${url.search}`;",
                "    try {",
                "      const requestBody = await new Promise<string>((resolve, reject) => {",
                "        let data = '';",
                "        req.setEncoding('utf-8');",
                "        req.on('data', (chunk) => { data += chunk; });",
                "        req.on('end', () => resolve(data));",
                "        req.on('error', reject);",
                "      });",
                "      const headers = buildUpstreamHeaders(req);",
                "      const method = req.method ?? 'GET';",
                "      const upstreamResponse = await fetch(upstream, {",
                "        method,",
                "        headers,",
                "        body: requestBody.length > 0 && method !== 'GET' && method !== 'DELETE' ? requestBody : undefined,",
                "      });",
                "      const responseText = await upstreamResponse.text();",
                "      res.statusCode = upstreamResponse.status;",
                "      copyUpstreamHeaders(upstreamResponse, res);",
                "      res.setHeader('content-type', upstreamResponse.headers.get('content-type') ?? 'application/json; charset=utf-8');",
                "      res.end(responseText);",
                "    } catch (error) {",
                "      res.statusCode = 502;",
                "      res.setHeader('content-type', 'application/json; charset=utf-8');",
                "      res.end(JSON.stringify({ error: 'bad_gateway', detail: String(error) }));",
                "    }",
                "    return;",
                "  }",
                "",
                "  const assetPath = url.pathname === '/' ? '/index.html' : url.pathname;",
                "  try {",
                "    const file = await readFile(join(distDir, assetPath.replace(/^\\//, '')));",
                "    if (assetPath.endsWith('.js')) {",
                "      res.setHeader('content-type', 'application/javascript; charset=utf-8');",
                "    } else if (assetPath.endsWith('.css')) {",
                "      res.setHeader('content-type', 'text/css; charset=utf-8');",
                "    } else {",
                "      res.setHeader('content-type', 'text/html; charset=utf-8');",
                "    }",
                "    res.statusCode = 200;",
                "    res.end(file);",
                "    return;",
                "  } catch {",
                "    const indexHtml = await readFile(join(distDir, 'index.html'));",
                "    res.statusCode = 200;",
                "    res.setHeader('content-type', 'text/html; charset=utf-8');",
                "    res.end(indexHtml);",
                "    return;",
                "  }",
                "}).listen(port, host, () => {",
                "  process.stdout.write(`[web] listening on http://${host}:${port}\\n`);",
                "});",
                "",
            ]
        ),
    )

    emit(
        output_dir / "packages" / "shared-types" / "package.json",
        json.dumps(
            {
                "name": "@app/shared-types",
                "private": True,
                "type": "module",
                "main": "./index.ts",
            },
            indent=2,
        )
        + "\n",
    )
    emit(
        output_dir / "packages" / "api-client" / "package.json",
        json.dumps(
            {
                "name": "@app/api-client",
                "private": True,
                "type": "module",
                "main": "./index.ts",
            },
            indent=2,
        )
        + "\n",
    )
    ensure_file(
        output_dir / "packages" / "shared-types" / "index.ts",
        "// Derived artifact authority: pending-compiled-bindings\n// generated later by contract pack\n",
    )
    ensure_file(
        output_dir / "packages" / "api-client" / "index.ts",
        "// Derived artifact authority: pending-compiled-bindings\n// generated later by contract pack\n",
    )
    ensure_file(output_dir / "db" / "migrations" / ".gitkeep", "")
    ensure_file(output_dir / "tests" / "fixtures" / ".gitkeep", "")
    ensure_file(output_dir / "tests" / "helpers" / ".gitkeep", "")

    return {"output_dir": str(output_dir), "project_name": package_name, "files_written": created, "count": len(created)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the Phase-3 project scaffold")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-name", default="phase3-app")
    parser.add_argument("--ui-ia-contract-path")
    parser.add_argument("--ui-locale", default="zh-CN")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = generate_project_scaffold(
        output_dir=Path(args.output_dir).resolve(),
        project_name=args.project_name,
        ui_ia_contract_path=Path(args.ui_ia_contract_path).resolve() if args.ui_ia_contract_path else None,
        ui_locale=args.ui_locale,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
