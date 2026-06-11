#!/usr/bin/env python3
"""
Install profile manifest loader and validator.
"""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any


MANIFEST_PATH = Path("config/wff-install-profiles.json")
BUILDABLE_PROFILE_STATUSES = {"default", "supported", "preview"}


class InstallProfileError(ValueError):
    """Raised when an install profile manifest or profile id is invalid."""


def load_install_profile_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / MANIFEST_PATH
    if not manifest_path.exists():
        raise InstallProfileError(f"install profile manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_install_profile_manifest(repo_root, manifest)
    if errors:
        raise InstallProfileError("; ".join(errors))
    return manifest


def profile_by_id(manifest: dict[str, Any], profile_id: str) -> dict[str, Any]:
    for profile in manifest.get("profiles", []):
        if profile.get("id") == profile_id:
            return profile
    raise InstallProfileError(f"unknown install profile: {profile_id}")


def supported_build_profile_ids(manifest: dict[str, Any]) -> list[str]:
    return [
        str(profile["id"])
        for profile in manifest.get("profiles", [])
        if profile.get("status") in BUILDABLE_PROFILE_STATUSES
    ]


def validate_install_profile_manifest(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if manifest.get("schema_version") != "v1.4-install-profiles":
        errors.append("schema_version must be v1.4-install-profiles")

    profiles = manifest.get("profiles", [])
    if not isinstance(profiles, list) or not profiles:
        errors.append("profiles must be a non-empty list")
        return errors

    seen: set[str] = set()
    profile_ids: set[str] = set()
    for profile in profiles:
        profile_id = str(profile.get("id", "")).strip()
        if not profile_id:
            errors.append("profile missing id")
            continue
        if profile_id in seen:
            errors.append(f"duplicate profile id: {profile_id}")
        seen.add(profile_id)
        profile_ids.add(profile_id)

    default_profile = str(manifest.get("default_profile", "")).strip()
    if default_profile not in profile_ids:
        errors.append(f"default_profile does not exist: {default_profile}")

    target_package_ids = _collect_id_set(manifest, "target_packages", errors)
    capability_ids = _collect_id_set(manifest, "capability_packages", errors)
    resource_module_ids = _collect_id_set(manifest, "resource_modules", errors)

    _validate_target_packages(manifest, capability_ids, resource_module_ids, errors)
    _validate_capability_packages(repo_root, manifest, resource_module_ids, errors)
    _validate_resource_modules(repo_root, manifest, errors)

    for profile in profiles:
        profile_id = str(profile.get("id", "")).strip() or "<missing>"
        _validate_profile(repo_root, profile_id, profile, target_package_ids, capability_ids, resource_module_ids, errors)

    return errors


def _collect_id_set(manifest: dict[str, Any], collection_key: str, errors: list[str]) -> set[str]:
    collection = manifest.get(collection_key, [])
    if not isinstance(collection, list) or not collection:
        errors.append(f"{collection_key} must be a non-empty list")
        return set()

    seen: set[str] = set()
    for index, item in enumerate(collection):
        if not isinstance(item, dict):
            errors.append(f"{collection_key} item {index} must be an object")
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            errors.append(f"{collection_key} item {index} missing id")
            continue
        if item_id in seen:
            errors.append(f"duplicate {collection_key} id: {item_id}")
        seen.add(item_id)
    return seen


def _validate_id_refs(
    owner: str,
    field: str,
    values: Any,
    known_ids: set[str],
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(values, list):
        errors.append(f"{owner} {field} must be a list")
        return
    for value in values:
        ref = str(value)
        if ref not in known_ids:
            errors.append(f"{owner} references unknown {label}: {ref}")


def _validate_target_packages(
    manifest: dict[str, Any],
    capability_ids: set[str],
    resource_module_ids: set[str],
    errors: list[str],
) -> None:
    for package in manifest.get("target_packages", []):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id", "")).strip() or "<missing-target-package>"
        for required_key in ("audience", "layer", "capabilities", "resource_modules"):
            if required_key not in package:
                errors.append(f"target_package {package_id} missing required field: {required_key}")
        _validate_id_refs(package_id, "capabilities", package.get("capabilities", []), capability_ids, "capability", errors)
        _validate_id_refs(
            package_id,
            "resource_modules",
            package.get("resource_modules", []),
            resource_module_ids,
            "resource_module",
            errors,
        )


def _validate_capability_packages(
    repo_root: Path,
    manifest: dict[str, Any],
    resource_module_ids: set[str],
    errors: list[str],
) -> None:
    for capability in manifest.get("capability_packages", []):
        if not isinstance(capability, dict):
            continue
        capability_id = str(capability.get("id", "")).strip() or "<missing-capability>"
        for required_key in ("skills", "resource_modules"):
            if required_key not in capability:
                errors.append(f"capability_package {capability_id} missing required field: {required_key}")
        for skill_name in capability.get("skills", []):
            if not (repo_root / "skills" / str(skill_name) / "SKILL.md").exists():
                errors.append(f"capability_package {capability_id} references missing skill: {skill_name}")
        _validate_id_refs(
            capability_id,
            "resource_modules",
            capability.get("resource_modules", []),
            resource_module_ids,
            "resource_module",
            errors,
        )


def _validate_resource_modules(repo_root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    for module in manifest.get("resource_modules", []):
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("id", "")).strip() or "<missing-resource-module>"
        for required_key in ("type", "paths"):
            if required_key not in module:
                errors.append(f"resource_module {module_id} missing required field: {required_key}")
        paths = module.get("paths", [])
        if not isinstance(paths, list):
            errors.append(f"resource_module {module_id} paths must be a list")
            continue
        for relative_path in paths:
            if not (repo_root / str(relative_path)).exists():
                errors.append(f"resource_module {module_id} references missing path: {relative_path}")


def _validate_profile(
    repo_root: Path,
    profile_id: str,
    profile: dict[str, Any],
    target_package_ids: set[str],
    capability_ids: set[str],
    resource_module_ids: set[str],
    errors: list[str],
) -> None:
    for required_key in (
        "status",
        "pack_type",
        "skills",
        "standalone_claim",
        "package_kind",
        "audience",
        "layer",
        "target_package",
        "capabilities",
        "resource_modules",
    ):
        if required_key not in profile:
            errors.append(f"{profile_id} missing required field: {required_key}")

    target_package = str(profile.get("target_package", "")).strip()
    if target_package and target_package not in target_package_ids:
        errors.append(f"{profile_id} references unknown target_package: {target_package}")
    _validate_id_refs(profile_id, "capabilities", profile.get("capabilities", []), capability_ids, "capability", errors)
    _validate_id_refs(
        profile_id,
        "resource_modules",
        profile.get("resource_modules", []),
        resource_module_ids,
        "resource_module",
        errors,
    )

    for skill_name in profile.get("skills", []):
        if not (repo_root / "skills" / str(skill_name) / "SKILL.md").exists():
            errors.append(f"{profile_id} references missing skill: {skill_name}")

    for key in (
        "explicit_scripts",
        "explicit_docs",
        "explicit_templates",
        "explicit_root_files",
        "excluded_scripts",
        "excluded_docs",
        "excluded_templates",
        "excluded_root_files",
    ):
        for relative_path in profile.get(key, []):
            if not (repo_root / str(relative_path)).exists():
                errors.append(f"{profile_id} {key} references missing path: {relative_path}")

    for key in ("explicit_reference_package_dirs", "explicit_release_case_dirs", "explicit_runtime_dep_dirs"):
        for relative_path in profile.get(key, []):
            if not (repo_root / str(relative_path)).is_dir():
                errors.append(f"{profile_id} {key} references missing directory: {relative_path}")

    targets = profile.get("root_entrypoint_targets", {})
    for entrypoint in profile.get("root_entrypoints", []):
        if entrypoint not in targets:
            errors.append(f"{profile_id} root entrypoint has no target script: {entrypoint}")
            continue
        target = str(targets[entrypoint])
        if not (repo_root / target).exists():
            errors.append(f"{profile_id} root entrypoint target missing: {entrypoint} -> {target}")

    for blocker_index, blocker in enumerate(profile.get("blockers", [])):
        for key in ("type", "reason", "evidence", "future_action"):
            if not blocker.get(key):
                errors.append(f"{profile_id} blocker {blocker_index} missing {key}")
