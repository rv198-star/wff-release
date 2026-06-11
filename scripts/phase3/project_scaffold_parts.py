from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.renderer_common import ascii_slug


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold_root_workspace(*, output_dir: Path, project_name: str) -> dict[str, Any]:
    files = []
    package = {
        "name": ascii_slug(project_name, fallback="phase3-app"),
        "private": True,
        "packageManager": "pnpm@9.0.0",
        "scripts": {"test": "vitest run --config vitest.config.ts"},
    }
    path = output_dir / "package.json"
    write_text(path, json.dumps(package, ensure_ascii=False, indent=2) + "\n")
    files.append(str(path))
    workspace_path = output_dir / "pnpm-workspace.yaml"
    write_text(workspace_path, "packages:\n  - apps/*\n  - packages/*\n")
    files.append(str(workspace_path))
    return {"files_created": files, "count": len(files)}


def scaffold_shared_packages(*, output_dir: Path) -> dict[str, Any]:
    files = []
    for package_name in ("shared-types", "api-client"):
        package_root = output_dir / "packages" / package_name
        package_json = package_root / "package.json"
        write_text(package_json, json.dumps({"name": f"@app/{package_name}", "private": True}, indent=2) + "\n")
        files.append(str(package_json))
        index_path = package_root / "index.ts"
        if not index_path.exists():
            write_text(index_path, "export {};\n")
            files.append(str(index_path))
    return {"files_created": files, "count": len(files)}


def scaffold_api_app(*, output_dir: Path) -> dict[str, Any]:
    files = []
    api_root = output_dir / "apps" / "api"
    package_json = api_root / "package.json"
    write_text(package_json, json.dumps({"name": "@app/api", "private": True}, indent=2) + "\n")
    files.append(str(package_json))
    main_path = api_root / "src" / "main.ts"
    write_text(main_path, "export function createApiServer() { return { started: true }; }\n")
    files.append(str(main_path))
    return {"files_created": files, "count": len(files)}


def scaffold_web_app(*, output_dir: Path) -> dict[str, Any]:
    files = []
    web_root = output_dir / "apps" / "web"
    package_json = web_root / "package.json"
    write_text(package_json, json.dumps({"name": "@app/web", "private": True}, indent=2) + "\n")
    files.append(str(package_json))
    page_path = web_root / "app" / "page.tsx"
    write_text(page_path, "export function Page() { return <main data-phase3-surface=\"/\">Phase-3 Web</main>; }\n")
    files.append(str(page_path))
    return {"files_created": files, "count": len(files)}


def scaffold_devops_assets(*, output_dir: Path) -> dict[str, Any]:
    files = []
    env_path = output_dir / ".env.example"
    write_text(env_path, "DATABASE_URL=postgres://postgres:postgres@localhost:5432/app\n")
    files.append(str(env_path))
    return {"files_created": files, "count": len(files)}
