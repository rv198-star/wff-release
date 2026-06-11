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


class WffInitError(RuntimeError):
    """Raised when project initialization cannot proceed safely."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def valid_skills_root(candidate: Path) -> bool:
    return (candidate / BASE_SKILL_PROBE).is_file()


def normalize_skills_root(candidate: Path) -> Path:
    resolved = candidate.expanduser().resolve()
    if resolved.name == BASE_SKILL_NAME and (resolved / "scripts" / "init_registry.py").is_file():
        return resolved.parent
    return resolved


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
    roots.extend(
        [
            project_root / ".wff" / "skills",
            project_root / ".codex" / "skills",
            project_root / ".claude" / "skills",
        ]
    )
    user_home = Path.home() if home is None else home
    roots.extend(
        [
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
    base_skill_link: Path,
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
            "required_base_skill": BASE_SKILL_NAME,
            "base_skill_path": str((skills_root / BASE_SKILL_NAME).resolve()),
            "runtime_skill_link": str(base_skill_link.relative_to(project_root)),
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
                "",
                "Do not place business implementation code in this directory.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return readme_path


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
    base_skill_link, link_status = ensure_base_skill_link(resolved_project_root, resolved_skills_root)
    manifest_path = write_project_manifest(
        project_root=resolved_project_root,
        skills_root=resolved_skills_root,
        base_skill_link=base_skill_link,
    )
    readme_path = write_runtime_readme(resolved_project_root)
    return {
        "status": "ready" if link_status == "existing" else "initialized",
        "project_root": str(resolved_project_root),
        "skills_root": str(resolved_skills_root),
        "base_skill_link": str(base_skill_link),
        "manifest": str(manifest_path),
        "readme": str(readme_path),
        "tried_skills_roots": [str(path) for path in tried_roots],
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
