"""Resolve WFF runtime support paths across project and user install layouts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


BASE_SKILL_NAME = "wff-base-traceability-management"
BASE_TRACE_SCRIPT = Path(BASE_SKILL_NAME, "scripts", "init_registry.py")


def valid_skills_root(candidate: Path) -> bool:
    return (candidate / BASE_TRACE_SCRIPT).is_file()


def normalize_skills_root(candidate: Path) -> Path:
    resolved = candidate.expanduser().resolve()
    if resolved.name == BASE_SKILL_NAME and (resolved / "scripts" / "init_registry.py").is_file():
        return resolved.parent
    return resolved


def candidate_wff_skills_roots(
    *,
    project_root: Path,
    fallback_roots: Iterable[Path],
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> list[Path]:
    environment = os.environ if env is None else env
    roots: list[Path] = []
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
    roots.extend(root / "skills" for root in fallback_roots)

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


def resolve_wff_base_trace_scripts(
    *,
    project_root: Path,
    fallback_roots: Iterable[Path],
    env: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    candidates = candidate_wff_skills_roots(
        project_root=project_root.resolve(),
        fallback_roots=fallback_roots,
        env=env,
        home=home,
    )
    for candidate in candidates:
        if valid_skills_root(candidate):
            return (candidate / BASE_SKILL_NAME / "scripts").resolve()
    tried = "\n".join(f"- {path}" for path in candidates)
    raise FileNotFoundError(f"could not resolve WFF base traceability scripts. Tried:\n{tried}")
