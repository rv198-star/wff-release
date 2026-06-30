#!/usr/bin/env python3
"""
Load and validate the WFF skill catalog registry.

The catalog owns skill classification and release posture. Install profiles own
pack composition. Validation keeps those surfaces from drifting apart.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CATALOG_PATH = Path("config/wff-skill-catalog.json")
SCHEMA_VERSION = "v1.0-wff-skill-catalog"
PUBLISHABLE_POSTURES = {
    "published-runtime-facing",
    "published-support",
    "published-preview",
    "published-optional",
    "published-compatibility",
}


class SkillCatalogError(ValueError):
    """Raised when the WFF skill catalog is invalid."""


def repo_skill_names(repo_root: Path) -> set[str]:
    skills_root = repo_root / "skills"
    return {
        path.parent.name
        for path in skills_root.glob("*/SKILL.md")
        if path.parent.is_dir()
    }


def load_skill_catalog(repo_root: Path) -> dict[str, Any]:
    catalog_path = repo_root / CATALOG_PATH
    if not catalog_path.exists():
        raise SkillCatalogError(f"skill catalog not found: {catalog_path}")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    errors = skill_catalog_errors(repo_root, catalog)
    if errors:
        raise SkillCatalogError("; ".join(errors))
    return catalog


def catalog_by_name(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(skill.get("name", "")): skill for skill in catalog.get("skills", [])}


def skill_catalog_errors(repo_root: Path, catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if catalog.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    declared_categories = _declared_values(catalog, "categories", errors)
    declared_release_postures = _declared_values(catalog, "release_postures", errors)
    declared_install_values = _declared_values(catalog, "install_profile_reference_values", errors)

    repo_names = repo_skill_names(repo_root)
    seen: set[str] = set()
    catalog_names: set[str] = set()

    skills = catalog.get("skills", [])
    if not isinstance(skills, list) or not skills:
        errors.append("skills must be a non-empty list")
        return errors

    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            errors.append(f"skill entry {index} must be an object")
            continue

        name = str(skill.get("name", "")).strip()
        if not name:
            errors.append(f"skill entry {index} missing name")
            continue
        if name in seen:
            errors.append(f"duplicate skill catalog entry: {name}")
        seen.add(name)
        catalog_names.add(name)

        if name not in repo_names:
            errors.append(f"catalog references missing repo skill: {name}")

        category = str(skill.get("category", "")).strip()
        if category not in declared_categories:
            errors.append(f"{name} has unknown category: {category}")

        release_posture = str(skill.get("release_posture", "")).strip()
        if release_posture not in declared_release_postures:
            errors.append(f"{name} has unknown release_posture: {release_posture}")

        install_profile_reference = str(skill.get("install_profile_reference", "")).strip()
        if install_profile_reference not in declared_install_values:
            errors.append(f"{name} has unknown install_profile_reference: {install_profile_reference}")

        if install_profile_reference == "allowed" and release_posture not in PUBLISHABLE_POSTURES:
            errors.append(f"{name} allows install-profile references but is not publishable: {release_posture}")
        if install_profile_reference == "forbidden" and release_posture in PUBLISHABLE_POSTURES:
            errors.append(f"{name} forbids install-profile references but is publishable: {release_posture}")

    missing = sorted(repo_names - catalog_names)
    if missing:
        errors.append("catalog does not include repo skills: " + ", ".join(missing))

    extra = sorted(catalog_names - repo_names)
    if extra:
        errors.append("catalog includes non-repo skills: " + ", ".join(extra))

    return errors


def _declared_values(catalog: dict[str, Any], key: str, errors: list[str]) -> set[str]:
    values = catalog.get(key, [])
    if not isinstance(values, list) or not values:
        errors.append(f"{key} must be a non-empty list")
        return set()
    normalized = {str(value).strip() for value in values if str(value).strip()}
    if len(normalized) != len(values):
        errors.append(f"{key} contains blank values")
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the WFF skill catalog registry")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()

    catalog_path = args.repo_root / CATALOG_PATH
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"skill catalog not found: {catalog_path}")
        return 1

    errors = skill_catalog_errors(args.repo_root, catalog)
    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"skill catalog ok: {len(catalog.get('skills', []))} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
