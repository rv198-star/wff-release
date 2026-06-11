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
from pathlib import Path
from typing import Any

from common.script_data_assets import load_script_text_asset
from phase3.renderer_common import ascii_slug
from phase3.ui_locale import infer_ui_locale, page_role_label, ui_text


SCRIPT_DIR = Path(__file__).resolve().parent

WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase3/data/scaffold-ui-app.tsx.template",
    "scripts/phase3/data/project-scaffold/pnpm-workspace.yaml",
    "scripts/phase3/data/project-scaffold/.npmrc",
    "scripts/phase3/data/project-scaffold/tsconfig.base.json",
    "scripts/phase3/data/project-scaffold/eslint.config.mjs",
    "scripts/phase3/data/project-scaffold/vitest.config.ts",
    "scripts/phase3/data/project-scaffold/.env.example",
    "scripts/phase3/data/project-scaffold/docker-compose.dev.yml",
    "scripts/phase3/data/project-scaffold/docker-compose.prod.yml",
    "scripts/phase3/data/project-scaffold/.dockerignore",
    "scripts/phase3/data/project-scaffold/Dockerfile",
    "scripts/phase3/data/project-scaffold/.github/workflows/ci.yml",
    "scripts/phase3/data/project-scaffold/apps/api/package.json",
    "scripts/phase3/data/project-scaffold/apps/api/tsconfig.json",
    "scripts/phase3/data/project-scaffold/apps/api/tsconfig.build.json",
    "scripts/phase3/data/project-scaffold/apps/api/src/main.ts",
    "scripts/phase3/data/project-scaffold/apps/api/src/generated-api-router.ts",
    "scripts/phase3/data/project-scaffold/apps/api/src/runtime/database.ts",
    "scripts/phase3/data/project-scaffold/apps/api/src/runtime/migrate.ts",
    "scripts/phase3/data/project-scaffold/apps/api/src/common/envelope.ts",
    "scripts/phase3/data/project-scaffold/apps/api/src/common/errors.ts",
    "scripts/phase3/data/project-scaffold/apps/api/src/common/pagination.ts",
    "scripts/phase3/data/project-scaffold/apps/web/package.json",
    "scripts/phase3/data/project-scaffold/apps/web/tsconfig.json",
    "scripts/phase3/data/project-scaffold/apps/web/tsconfig.build.json",
    "scripts/phase3/data/project-scaffold/apps/web/vite.config.ts",
    "scripts/phase3/data/project-scaffold/apps/web/app/page.tsx",
    "scripts/phase3/data/project-scaffold/apps/web/app/theme.css",
    "scripts/phase3/data/project-scaffold/apps/web/app/main.tsx",
    "scripts/phase3/data/project-scaffold/apps/web/app/api.ts",
    "scripts/phase3/data/project-scaffold/apps/web/app/vite-env.d.ts",
    "scripts/phase3/data/project-scaffold/apps/web/app/server.ts",
    "scripts/phase3/data/project-scaffold/packages/shared-types/package.json",
    "scripts/phase3/data/project-scaffold/packages/api-client/package.json",
)

PROJECT_SCAFFOLD_TEXT_ASSETS = (
    ("pnpm-workspace.yaml", "project-scaffold/pnpm-workspace.yaml"),
    (".npmrc", "project-scaffold/.npmrc"),
    ("tsconfig.base.json", "project-scaffold/tsconfig.base.json"),
    ("eslint.config.mjs", "project-scaffold/eslint.config.mjs"),
    ("vitest.config.ts", "project-scaffold/vitest.config.ts"),
    (".env.example", "project-scaffold/.env.example"),
    ("docker-compose.dev.yml", "project-scaffold/docker-compose.dev.yml"),
    ("docker-compose.prod.yml", "project-scaffold/docker-compose.prod.yml"),
    (".dockerignore", "project-scaffold/.dockerignore"),
    ("Dockerfile", "project-scaffold/Dockerfile"),
    (".github/workflows/ci.yml", "project-scaffold/.github/workflows/ci.yml"),
    ("apps/api/package.json", "project-scaffold/apps/api/package.json"),
    ("apps/api/tsconfig.json", "project-scaffold/apps/api/tsconfig.json"),
    ("apps/api/tsconfig.build.json", "project-scaffold/apps/api/tsconfig.build.json"),
    ("apps/api/src/main.ts", "project-scaffold/apps/api/src/main.ts"),
    ("apps/api/src/generated-api-router.ts", "project-scaffold/apps/api/src/generated-api-router.ts"),
    ("apps/api/src/runtime/database.ts", "project-scaffold/apps/api/src/runtime/database.ts"),
    ("apps/api/src/runtime/migrate.ts", "project-scaffold/apps/api/src/runtime/migrate.ts"),
    ("apps/api/src/common/envelope.ts", "project-scaffold/apps/api/src/common/envelope.ts"),
    ("apps/api/src/common/errors.ts", "project-scaffold/apps/api/src/common/errors.ts"),
    ("apps/api/src/common/pagination.ts", "project-scaffold/apps/api/src/common/pagination.ts"),
    ("apps/web/package.json", "project-scaffold/apps/web/package.json"),
    ("apps/web/tsconfig.json", "project-scaffold/apps/web/tsconfig.json"),
    ("apps/web/tsconfig.build.json", "project-scaffold/apps/web/tsconfig.build.json"),
    ("apps/web/vite.config.ts", "project-scaffold/apps/web/vite.config.ts"),
    ("apps/web/app/page.tsx", "project-scaffold/apps/web/app/page.tsx"),
    ("apps/web/app/theme.css", "project-scaffold/apps/web/app/theme.css"),
    ("apps/web/app/main.tsx", "project-scaffold/apps/web/app/main.tsx"),
    ("apps/web/app/api.ts", "project-scaffold/apps/web/app/api.ts"),
    ("apps/web/app/vite-env.d.ts", "project-scaffold/apps/web/app/vite-env.d.ts"),
    ("apps/web/app/server.ts", "project-scaffold/apps/web/app/server.ts"),
    ("packages/shared-types/package.json", "project-scaffold/packages/shared-types/package.json"),
    ("packages/api-client/package.json", "project-scaffold/packages/api-client/package.json"),
)

def load_scaffold_ui_app_template() -> str:
    return load_script_text_asset(__file__, "scaffold-ui-app.tsx.template")


def load_project_scaffold_asset(asset_name: str) -> str:
    return load_script_text_asset(__file__, asset_name)


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
    normalized = [slug for part in candidates if (slug := ascii_slug(part, fallback=""))]
    if normalized:
        return "/".join(normalized)
    return ascii_slug(fallback_title, fallback="phase3-app")


def _scaffold_surface_pages(ui_ia_contract_path: Path | None) -> list[dict[str, Any]]:
    default_titles = [
        "Overview dashboard",
        "Primary record list",
        "Record detail view",
        "Action workspace",
    ]
    fallback_pages = [
        {
            "page_id": ascii_slug(title, fallback="phase3-app"),
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
                "page_id": str(raw_page.get("page_id") or ascii_slug(title, fallback="phase3-app")).strip(),
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
    labels = {
        "__SURFACES__": surfaces_blob,
        "__GOAL_TITLE__": json.dumps("Goal for this page" if locale == "en" else "本页目标", ensure_ascii=False),
        "__ROUTE_LABEL__": "Route" if locale == "en" else "路由",
        "__CONTRACT_ANCHOR_TITLE__": json.dumps("Contract anchors" if locale == "en" else "合同锚点", ensure_ascii=False),
        "__ALLOWED_ROLES_TITLE__": "Allowed roles" if locale == "en" else "允许角色",
        "__BUSINESS_OBJECTS_TITLE__": "Business objects" if locale == "en" else "业务对象",
        "__REQUIRED_REGIONS_TITLE__": "Required regions" if locale == "en" else "必需区域",
        "__INTERACTION_BINDING_TITLE__": "Interaction and binding chain" if locale == "en" else "交互与绑定链",
        "__NEXT_ROUTES_TITLE__": "Next routes" if locale == "en" else "后续路由",
        "__NO_CONTRACT_ANCHOR_HINT__": (
            "This scaffold is still waiting for explicit compiled contract anchors."
            if locale == "en"
            else "这个 scaffold 还在等待显式的 compiled contract 锚点。"
        ),
        "__WORK_AREA_TITLE__": json.dumps("Work area" if locale == "en" else "工作区", ensure_ascii=False),
        "__WORK_AREA_HINT__": (
            "Enter the required information for this step and keep the latest draft state visible on the page."
            if locale == "en"
            else "填写本步骤所需信息，并让最新草稿状态继续停留在页面上。"
        ),
        "__REQUIRED_MESSAGE_SUFFIX__": json.dumps(" is required" if locale == "en" else " 为必填项", ensure_ascii=False),
        "__INPUT_PLACEHOLDER__": json.dumps("text" if locale == "en" else "请输入内容", ensure_ascii=False),
        "__SAVE_DRAFT_LABEL__": "Save current draft" if locale == "en" else "保存当前草稿",
        "__CURRENT_CONTEXT_TITLE__": json.dumps("Current context" if locale == "en" else "当前上下文", ensure_ascii=False),
        "__SUBMITTED_HINT__": (
            "The current working data will appear here after the user submits the form."
            if locale == "en"
            else "用户提交表单后，当前工作数据会显示在这里。"
        ),
        "__DATA_SIGNALS_TITLE__": json.dumps("Data and signals in view" if locale == "en" else "当前数据与信号", ensure_ascii=False),
        "__PAGE_STATES_TITLE__": json.dumps("Page states" if locale == "en" else "页面状态", ensure_ascii=False),
        "__LOADING_LABEL__": "loading" if locale == "en" else "加载中",
        "__SUCCESS_LABEL__": "success" if locale == "en" else "成功",
        "__EMPTY_LABEL__": "empty" if locale == "en" else "空态",
        "__ERROR_LABEL__": "error" if locale == "en" else "失败",
        "__NEXT_STEPS_TITLE__": json.dumps("What happens next" if locale == "en" else "下一步会发生什么", ensure_ascii=False),
        "__SUCCESS_PREFIX__": "Success" if locale == "en" else "成功",
        "__ERROR_PREFIX__": "Error" if locale == "en" else "失败",
        "__DELIVERY_WORKSPACE__": ui_text(locale, "delivery_workspace"),
        "__OPERATE_RUNNABLE_WORKFLOW__": ui_text(locale, "operate_runnable_workflow"),
        "__WORKSPACE_INTRO_SCAFFOLD__": ui_text(locale, "workspace_intro_scaffold"),
        "__OPEN_PRIMARY_WORKSPACE__": ui_text(locale, "open_primary_workspace"),
        "__AVAILABLE_WORK_AREAS__": json.dumps(ui_text(locale, "available_work_areas"), ensure_ascii=False),
        "__PAGE_ROLE_LABELS__": "(" + json.dumps(
            {key: page_role_label(key, locale) for key in ["workspace", "list", "detail", "form-flow", "workflow", "review"]},
            ensure_ascii=False,
        ) + ")",
        "__CONTINUE_WORKFLOW__": json.dumps("Continue workflow" if locale == "en" else "继续工作流", ensure_ascii=False),
        "__WORKSPACE_MENU__": ui_text(locale, "workspace_menu"),
        "__RUNNABLE_MVP__": ui_text(locale, "runnable_mvp"),
        "__WORKSPACE_INTRO_GENERATED__": ui_text(locale, "workspace_intro_generated"),
    }
    rendered = load_scaffold_ui_app_template()
    for token, replacement in labels.items():
        rendered = rendered.replace(token, replacement)
    return rendered


def generate_project_scaffold(
    *,
    output_dir: Path,
    project_name: str,
    ui_ia_contract_path: Path | None = None,
    ui_locale: str | None = None,
) -> dict[str, object]:
    package_name = ascii_slug(project_name, fallback="phase3-app")
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
    for relative_path, asset_name in PROJECT_SCAFFOLD_TEXT_ASSETS:
        emit(output_dir / Path(relative_path), load_project_scaffold_asset(asset_name))

    emit(
        output_dir / "scripts" / "run_vitest_targets_sequentially.py",
        bundled_script_content("run_vitest_targets_sequentially.py"),
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
        output_dir / "apps" / "web" / "app" / "ui-app.tsx",
        _render_scaffold_ui_app(surface_pages),
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
