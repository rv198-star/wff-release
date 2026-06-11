#!/usr/bin/env python3
"""Initialize a project-local WFF runtime attachment under .wff/."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_SKILL_NAME = "wff-base-traceability-management"
BASE_SKILL_PROBE = Path(BASE_SKILL_NAME, "scripts", "init_registry.py")
RESOURCE_ROOT_ENV_VARS = ("WFF_RESOURCE_ROOT", "WFF_INSTALL_ROOT")
WFF_PACK_DISCOVERY_IGNORED_CHILDREN = {"skills"}
PROJECT_CONTEXT_RELATIVE_PATH = Path(".wff", "PROJECT_CONTEXT.md")
PROJECT_CONTEXT_IMPORT_CANDIDATE_NAMES = ("CONTEXT.md", "project-context.md")
PROJECT_CONTEXT_TEMPLATE = """# WFF Project Context

## Context Authority

This file is project-level Agent context. It helps WFF agents make better default judgments, but it does not replace P1/P2/P3/PX/P4 lifecycle truth.

## Human Maintained Context

## Demand / Business Context

## Architecture / Design Context

## Code / Implementation Context

## Brownfield Context
<!-- only for brownfield / migration / refactor / change projects -->

## Key References

## Conflict / Review Notes
"""


class WffInitError(RuntimeError):
    """Raised when project initialization cannot proceed safely."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def valid_skills_root(candidate: Path) -> bool:
    return (candidate / BASE_SKILL_PROBE).is_file()


def valid_resource_root(candidate: Path) -> bool:
    return (candidate / "skills" / BASE_SKILL_PROBE).is_file() and (candidate / "scripts").is_dir()


def normalize_skills_root(candidate: Path) -> Path:
    resolved = candidate.expanduser().resolve()
    if resolved.name == BASE_SKILL_NAME and (resolved / "scripts" / "init_registry.py").is_file():
        return resolved.parent
    return resolved


def normalize_resource_root(candidate: Path) -> Path:
    resolved = candidate.expanduser().resolve()
    if resolved.name == "skills" and valid_skills_root(resolved):
        return resolved.parent
    if resolved.name == BASE_SKILL_NAME and (resolved / "scripts" / "init_registry.py").is_file():
        return resolved.parent.parent
    return resolved


def wff_pack_roots(root: Path) -> list[Path]:
    roots = [root]
    try:
        roots.extend(
            sorted(
                path
                for path in root.expanduser().iterdir()
                if path.is_dir() and path.name not in WFF_PACK_DISCOVERY_IGNORED_CHILDREN
            )
        )
    except FileNotFoundError:
        pass
    return roots


def candidate_skills_roots(
    *,
    project_root: Path,
    explicit_skills_root: Path | None = None,
    install_root: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> list[Path]:
    environment = os.environ if env is None else env
    roots: list[Path] = []
    if explicit_skills_root is not None:
        roots.append(explicit_skills_root)
    env_root = environment.get("WFF_SKILLS_ROOT", "").strip()
    if env_root:
        roots.append(Path(env_root))
    project_wff_roots = wff_pack_roots(project_root / ".wff")
    roots.extend(
        [
            project_root / ".wff" / "skills",
            *(root / "skills" for root in project_wff_roots),
            project_root / ".agents" / "skills",
            project_root / ".opencode" / "skills",
            project_root / ".codex" / "skills",
            project_root / ".claude" / "skills",
        ]
    )
    user_home = Path.home() if home is None else home
    user_wff_roots = wff_pack_roots(user_home / ".wff")
    roots.extend(
        [
            user_home / ".wff" / "skills",
            *(root / "skills" for root in user_wff_roots),
            user_home / ".agents" / "skills",
            user_home / ".config" / "opencode" / "skills",
            user_home / ".codex" / "skills",
            user_home / ".claude" / "skills",
        ]
    )
    if install_root is None:
        install_root = Path(__file__).resolve().parents[2]
    roots.append(install_root / "skills")

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        normalized = normalize_skills_root(root)
        key = str(normalized)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def candidate_resource_roots(
    *,
    project_root: Path,
    skills_root: Path | None = None,
    install_root: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> list[Path]:
    environment = os.environ if env is None else env
    roots: list[Path] = []
    for env_var in RESOURCE_ROOT_ENV_VARS:
        env_root = environment.get(env_var, "").strip()
        if env_root:
            roots.append(Path(env_root))

    if skills_root is not None:
        roots.append(skills_root)

    roots.extend(wff_pack_roots(project_root / ".wff"))

    user_home = Path.home() if home is None else home
    roots.extend(wff_pack_roots(user_home / ".wff"))

    if install_root is None:
        install_root = Path(__file__).resolve().parents[2]
    roots.append(install_root)

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        normalized = normalize_resource_root(root)
        key = str(normalized)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def resolve_skills_root(
    *,
    project_root: Path,
    explicit_skills_root: Path | None = None,
    install_root: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[Path, list[Path]]:
    candidates = candidate_skills_roots(
        project_root=project_root,
        explicit_skills_root=explicit_skills_root,
        install_root=install_root,
        home=home,
        env=env,
    )
    for candidate in candidates:
        if valid_skills_root(candidate):
            return candidate, candidates
    tried = "\n".join(f"- {path}" for path in candidates)
    raise WffInitError(
        "could not find WFF base skill. Provide --skills-root pointing to a skills directory.\n"
        f"Tried:\n{tried}"
    )


def resolve_resource_root(
    *,
    project_root: Path,
    skills_root: Path | None = None,
    install_root: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[Path | None, list[Path]]:
    candidates = candidate_resource_roots(
        project_root=project_root,
        skills_root=skills_root,
        install_root=install_root,
        home=home,
        env=env,
    )
    for candidate in candidates:
        if valid_resource_root(candidate):
            return candidate, candidates
    return None, candidates


def relative_link_target(source: Path, link_parent: Path) -> str:
    return os.path.relpath(source, start=link_parent)


def ensure_base_skill_link(project_root: Path, skills_root: Path) -> tuple[Path, str]:
    wff_skills_root = project_root / ".wff" / "skills"
    wff_skills_root.mkdir(parents=True, exist_ok=True)
    link_path = wff_skills_root / BASE_SKILL_NAME
    source_skill = skills_root / BASE_SKILL_NAME
    if not (source_skill / "scripts" / "init_registry.py").is_file():
        raise WffInitError(f"required base skill is incomplete: {source_skill}")

    if link_path.is_symlink():
        if link_path.exists() and link_path.resolve() == source_skill.resolve():
            return link_path, "existing"
        link_path.unlink()
    elif link_path.exists():
        raise WffInitError(f"refusing to overwrite existing non-symlink path: {link_path}")

    link_path.symlink_to(relative_link_target(source_skill.resolve(), wff_skills_root), target_is_directory=True)
    return link_path, "created"


def write_project_manifest(
    *,
    project_root: Path,
    skills_root: Path,
    resource_root: Path | None,
    base_skill_link: Path,
    project_context_path: Path,
    project_context_status: str,
    project_context_import_candidates: list[str],
) -> Path:
    manifest_path = project_root / ".wff" / "wff-project.json"
    existing: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except json.JSONDecodeError as exc:
            raise WffInitError(f"invalid existing WFF project manifest: {manifest_path}") from exc

    now = utc_now_iso()
    existing.setdefault("initialized_at", now)
    existing.update(
        {
            "schema_version": "wff-project-init/v1",
            "updated_at": now,
            "project_root": str(project_root.resolve()),
            "skills_root": str(skills_root.resolve()),
            "resource_root": str(resource_root.resolve()) if resource_root is not None else "",
            "resource_root_status": "resolved" if resource_root is not None else "unresolved",
            "required_base_skill": BASE_SKILL_NAME,
            "base_skill_path": str((skills_root / BASE_SKILL_NAME).resolve()),
            "runtime_skill_link": str(base_skill_link.relative_to(project_root)),
            "project_context_path": project_context_path.relative_to(project_root).as_posix(),
            "project_context_status": project_context_status,
            "project_context_import_candidates": project_context_import_candidates,
        }
    )
    manifest_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def write_runtime_readme(project_root: Path) -> Path:
    readme_path = project_root / ".wff" / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                "# WFF Runtime Attachment",
                "",
                "This directory is maintained by `wff-init`.",
                "",
                "It lets WFF runtime scripts find required local support skills without modifying business source code.",
                "",
                "Managed surfaces:",
                "",
                f"- `skills/{BASE_SKILL_NAME}`",
                "- `wff-project.json`",
                "- `PROJECT_CONTEXT.md`",
                "",
                "If `wff-project.json` records `resource_root`, WFF agents and wrappers should use it as the install-pack root for bundled support resources.",
                "",
                "Do not place business implementation code in this directory.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return readme_path


def discover_project_context_import_candidates(project_root: Path) -> list[str]:
    return [
        candidate_name
        for candidate_name in PROJECT_CONTEXT_IMPORT_CANDIDATE_NAMES
        if (project_root / candidate_name).is_file()
    ]


def ensure_project_context(project_root: Path) -> tuple[Path, str, list[str]]:
    context_path = project_root / PROJECT_CONTEXT_RELATIVE_PATH
    context_path.parent.mkdir(parents=True, exist_ok=True)
    import_candidates = discover_project_context_import_candidates(project_root)
    if context_path.exists():
        if not context_path.is_file():
            raise WffInitError(f"refusing to overwrite existing non-file project context path: {context_path}")
        return context_path, "existing", import_candidates
    context_path.write_text(PROJECT_CONTEXT_TEMPLATE, encoding="utf-8")
    return context_path, "created", import_candidates


def initialize_wff_project(
    *,
    project_root: Path | str,
    skills_root: Path | str | None = None,
    install_root: Path | None = None,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    resolved_project_root = Path(project_root).expanduser().resolve()
    resolved_project_root.mkdir(parents=True, exist_ok=True)
    explicit_skills_root = Path(skills_root).expanduser() if skills_root is not None else None
    resolved_skills_root, tried_roots = resolve_skills_root(
        project_root=resolved_project_root,
        explicit_skills_root=explicit_skills_root,
        install_root=install_root,
        home=home,
        env=env,
    )
    resolved_resource_root, tried_resource_roots = resolve_resource_root(
        project_root=resolved_project_root,
        skills_root=resolved_skills_root,
        install_root=install_root,
        home=home,
        env=env,
    )
    base_skill_link, link_status = ensure_base_skill_link(resolved_project_root, resolved_skills_root)
    project_context_path, project_context_status, project_context_import_candidates = ensure_project_context(
        resolved_project_root
    )
    manifest_path = write_project_manifest(
        project_root=resolved_project_root,
        skills_root=resolved_skills_root,
        resource_root=resolved_resource_root,
        base_skill_link=base_skill_link,
        project_context_path=project_context_path,
        project_context_status=project_context_status,
        project_context_import_candidates=project_context_import_candidates,
    )
    readme_path = write_runtime_readme(resolved_project_root)
    return {
        "status": "ready" if link_status == "existing" else "initialized",
        "project_root": str(resolved_project_root),
        "skills_root": str(resolved_skills_root),
        "resource_root": str(resolved_resource_root) if resolved_resource_root is not None else "",
        "resource_root_status": "resolved" if resolved_resource_root is not None else "unresolved",
        "base_skill_link": str(base_skill_link),
        "project_context": str(project_context_path),
        "project_context_status": project_context_status,
        "project_context_import_candidates": project_context_import_candidates,
        "manifest": str(manifest_path),
        "readme": str(readme_path),
        "tried_skills_roots": [str(path) for path in tried_roots],
        "tried_resource_roots": [str(path) for path in tried_resource_roots],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize .wff runtime attachment for the current project.")
    parser.add_argument("--project-root", default=".", help="target business project directory; defaults to cwd")
    parser.add_argument("--skills-root", help="installed WFF skills root; defaults to automatic discovery")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = initialize_wff_project(project_root=args.project_root, skills_root=args.skills_root)
    except WffInitError as exc:
        print(f"[wff-init] ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
