from __future__ import annotations

import json
from pathlib import Path

from common.script_data_assets import load_script_text_asset
from phase3.renderer_common import ascii_slug

ROOT_ASSETS = (
    ("pnpm-workspace.yaml", "project-scaffold/pnpm-workspace.yaml"), (".npmrc", "project-scaffold/.npmrc"),
    ("tsconfig.base.json", "project-scaffold/tsconfig.base.json"), ("tsconfig.json", "project-scaffold/tsconfig.backend.json"),
    ("eslint.config.mjs", "project-scaffold/eslint.config.mjs"), ("vitest.config.ts", "project-scaffold/vitest.config.ts"),
    (".env.example", "project-scaffold/.env.example"), ("docker-compose.dev.yml", "project-scaffold/docker-compose.dev.yml"),
    ("docker-compose.prod.yml", "project-scaffold/docker-compose.prod.yml"), (".dockerignore", "project-scaffold/.dockerignore"),
    ("Dockerfile", "project-scaffold/Dockerfile"), (".github/workflows/ci.yml", "project-scaffold/.github/workflows/ci.yml"),
)
API_ASSETS = (
    "apps/api/package.json", "apps/api/tsconfig.json", "apps/api/tsconfig.build.json", "apps/api/src/main.ts",
    "apps/api/src/generated-api-router.ts", "apps/api/src/runtime/database.ts", "apps/api/src/runtime/migrate.ts", "apps/api/src/runtime/operation-runtime.ts", "apps/api/src/runtime/postgres-storage.ts",
    "apps/api/src/common/envelope.ts", "apps/api/src/common/errors.ts", "apps/api/src/common/pagination.ts",
    "tests/unit/api/auth-session.test.ts",
)
WEB_ASSETS = (
    "apps/web/package.json",
    "apps/web/tsconfig.json",
    "apps/web/tsconfig.build.json",
    "apps/web/vite.config.ts",
    "apps/web/app/theme.css",
    "apps/web/app/main.tsx",
    "apps/web/app/api.ts",
    "apps/web/app/vite-env.d.ts",
    "apps/web/app/server.ts",
)

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def _asset_text(asset_name: str) -> str:
    return load_script_text_asset(__file__, asset_name)


def _emit_asset(output_dir: Path, relative_path: str, asset_name: str) -> str:
    path = output_dir / relative_path
    write_text(path, _asset_text(asset_name))
    return str(path)


def _emit_assets(output_dir: Path, assets: tuple[tuple[str, str], ...]) -> list[str]:
    return [_emit_asset(output_dir, relative, asset) for relative, asset in assets]


def scaffold_root_workspace(*, output_dir: Path, project_name: str) -> dict[str, object]:
    package = json.loads(_asset_text("project-scaffold/package.backend.json"))
    package["name"] = ascii_slug(project_name, fallback="phase3-app")
    package_path = output_dir / "package.json"
    web_materialized = (output_dir / "apps" / "web" / "package.json").is_file()
    write_text(package_path, json.dumps(package, ensure_ascii=False, indent=2) + "\n")
    if web_materialized:
        _merge_web_overlay_into_root_package(output_dir)
    files = [str(package_path), *_emit_assets(output_dir, ROOT_ASSETS)]
    vitest_runner_source = Path(__file__).resolve().parent / "run_vitest_targets_sequentially.py"
    vitest_runner_target = output_dir / "scripts" / "run_vitest_targets_sequentially.py"
    if not vitest_runner_source.is_file():
        raise FileNotFoundError(f"Phase-3 runtime verification helper is missing: {vitest_runner_source}")
    write_text(vitest_runner_target, vitest_runner_source.read_text(encoding="utf-8"))
    files.append(str(vitest_runner_target))
    return {"files_created": files, "count": len(files)}


def scaffold_shared_packages(*, output_dir: Path) -> dict[str, object]:
    files: list[str] = []
    for name in ("shared-types", "api-client"):
        files.append(_emit_asset(output_dir, f"packages/{name}/package.json", f"project-scaffold/packages/{name}/package.json"))
        index_path = output_dir / "packages" / name / "index.ts"
        if not index_path.exists():
            write_text(index_path, "export {};\n")
            files.append(str(index_path))
    return {"files_created": files, "count": len(files)}


def scaffold_api_app(*, output_dir: Path) -> dict[str, object]:
    files = _emit_assets(output_dir, tuple((path, f"project-scaffold/{path}") for path in API_ASSETS))
    from phase3.api_support_renderer import render_auth_session_module, render_errors_module

    errors_path = output_dir / "apps/api/src/common/errors.ts"
    write_text(errors_path, render_errors_module())
    files.append(str(errors_path))
    auth_session_path = output_dir / "apps/api/src/common/auth-session.ts"
    write_text(auth_session_path, render_auth_session_module())
    files.append(str(auth_session_path))
    return {"files_created": files, "count": len(files)}


def _merge_web_overlay_into_root_package(output_dir: Path) -> str:
    package_path = output_dir / "package.json"
    if not package_path.is_file():
        return "root-package-absent"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    overlay = json.loads(_asset_text("project-scaffold/package.web-overlay.json"))
    for section, values in overlay.items():
        if not isinstance(values, dict):
            continue
        current = package.get(section)
        if not isinstance(current, dict):
            current = {}
            package[section] = current
        current.update(values)
    write_text(package_path, json.dumps(package, ensure_ascii=False, indent=2) + "\n")
    return "merged"


def _frontend_index_html(ui_locale: str = "en") -> str:
    locale = str(ui_locale or "en").strip() or "en"
    title = "Phase-3 工作台" if locale.lower().startswith("zh") else "Phase-3 Web"
    return "\n".join([
        "<!doctype html>",
        f'<html lang="{locale}">',
        "  <head>",
        '    <meta charset="UTF-8" />',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
        f"    <title>{title}</title>",
        "  </head>",
        "  <body>",
        '    <div id="root"></div>',
        '    <script type="module" src="/app/main.tsx"></script>',
        "  </body>",
        "</html>",
        "",
    ])


def _default_frontend_app() -> str:
    return '\n'.join([
        'import HomePage from "./page";',
        '',
        'export function App() {',
        '  return <HomePage />;',
        '}',
        '',
    ])


def scaffold_frozen_backend_frontend_runtime_overlay(*, output_dir: Path) -> dict[str, object]:
    """Add only the root runtime assets required by a new Web surface.

    Existing WFF-P3 backend/root files are preserved byte-for-byte except package.json,
    where the Web dependency/script overlay is merged additively.
    """
    runtime_assets = (
        ".env.example",
        "docker-compose.dev.yml",
        "docker-compose.prod.yml",
        ".dockerignore",
        "Dockerfile",
    )
    created: list[str] = []
    preserved: list[str] = []
    for relative in runtime_assets:
        path = output_dir / relative
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"unsafe frozen-backend runtime overlay target: {relative}")
            preserved.append(relative)
            continue
        write_text(path, _asset_text(f"project-scaffold/{relative}"))
        created.append(str(path))
    package_mode = _merge_web_overlay_into_root_package(output_dir)
    return {
        "mode": "frozen-backend-frontend-runtime-overlay",
        "files_created": created,
        "preserved_existing": preserved,
        "count": len(created),
        "root_package_web_overlay": package_mode,
    }


def scaffold_web_app(
    *,
    output_dir: Path,
    preserve_existing: tuple[str, ...] = (),
    ui_locale: str = "en",
) -> dict[str, object]:
    preserve = {str(value).strip().replace("\\", "/") for value in preserve_existing if str(value).strip()}
    files: list[str] = []
    preserved: list[str] = []
    for relative in WEB_ASSETS:
        normalized = str(relative).replace("\\", "/")
        path = output_dir / relative
        if normalized in preserve and path.exists():
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"unsafe preserved Web asset: {relative}")
            preserved.append(relative)
            continue
        files.append(_emit_asset(output_dir, relative, f"project-scaffold/{relative}"))
    index_path = output_dir / "apps/web/index.html"
    write_text(index_path, _frontend_index_html(ui_locale))
    files.append(str(index_path))
    package_mode = _merge_web_overlay_into_root_package(output_dir)
    return {
        "files_created": files,
        "preserved_existing": preserved,
        "count": len(files),
        "root_package_web_overlay": package_mode,
    }
