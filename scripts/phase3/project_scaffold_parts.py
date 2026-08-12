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
    write_text(package_path, json.dumps(package, ensure_ascii=False, indent=2) + "\n")
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
    return {"files_created": files, "count": len(files)}


def scaffold_web_app(*, output_dir: Path) -> dict[str, object]:
    package_path = output_dir / "apps/web/package.json"
    page_path = output_dir / "apps/web/app/page.tsx"
    write_text(package_path, json.dumps({"name": "@app/web", "private": True}, indent=2) + "\n")
    write_text(page_path, "export function Page() { return <main data-phase3-surface=\"/\">Phase-3 Web</main>; }\n")
    return {"files_created": [str(package_path), str(page_path)], "count": 2}
