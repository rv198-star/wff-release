#!/usr/bin/env python3
"""WFF role-agent mount manifest loader, validator, and renderer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from release.install_profile_manifest import load_install_profile_manifest  # noqa: E402


MANIFEST_PATH = Path("config/wff-role-mounts.json")
EXPECTED_ROLE_IDS = {
    "wff-product-manager",
    "wff-architect",
    "wff-programmer",
    "wff-qa-tester",
    "wff-refactor-architect",
    "wff-reviewer",
}
REQUIRED_ROLE_FIELDS = {
    "id",
    "display_name",
    "short_name",
    "primary_profile",
    "allowed_profiles",
    "mounted_skills",
    "professional_stance",
    "voice",
    "challenge_behavior",
    "local_judgment",
    "forbidden_overreach",
    "return_routes",
    "evidence_boundary",
    "communication_contract",
}


class RoleAgentManifestError(ValueError):
    """Raised when the role-agent manifest is invalid."""


def load_role_agent_manifest(repo_root: Path, *, validate_references: bool = True) -> dict[str, Any]:
    manifest_path = repo_root / MANIFEST_PATH
    if not manifest_path.exists():
        raise RoleAgentManifestError(f"role-agent manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_role_agent_manifest(repo_root, manifest, validate_references=validate_references)
    if errors:
        raise RoleAgentManifestError("; ".join(errors))
    return manifest


def role_by_id(manifest: dict[str, Any], role_id: str) -> dict[str, Any]:
    for role in manifest.get("roles", []):
        if role.get("id") == role_id:
            return role
    raise RoleAgentManifestError(f"unknown WFF role agent: {role_id}")


def validate_role_agent_manifest(
    repo_root: Path,
    manifest: dict[str, Any],
    *,
    validate_references: bool = True,
) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != "v1.4-role-agent-mounts":
        errors.append("schema_version must be v1.4-role-agent-mounts")
    if manifest.get("adapter_status") != "platform-adapter-supported":
        errors.append("adapter_status must be platform-adapter-supported")

    shared_contract = manifest.get("shared_communication_contract", [])
    if not isinstance(shared_contract, list) or not shared_contract:
        errors.append("shared_communication_contract must be a non-empty list")

    known_profiles: set[str] = set()
    known_skills: set[str] = set()
    if validate_references:
        install_manifest = load_install_profile_manifest(repo_root)
        known_profiles = {str(profile["id"]) for profile in install_manifest.get("profiles", [])}
        known_skills = {
            path.parent.name
            for path in (repo_root / "skills").glob("*/SKILL.md")
            if path.is_file()
        }

    roles = manifest.get("roles", [])
    if not isinstance(roles, list) or not roles:
        errors.append("roles must be a non-empty list")
        return errors

    role_ids: set[str] = set()
    for role in roles:
        if not isinstance(role, dict):
            errors.append("role entries must be objects")
            continue
        role_id = str(role.get("id", "")).strip()
        if not role_id:
            errors.append("role missing id")
            continue
        if role_id in role_ids:
            errors.append(f"duplicate role id: {role_id}")
        role_ids.add(role_id)
        if not role_id.startswith("wff-"):
            errors.append(f"role id must use wff- prefix: {role_id}")
        for field in sorted(REQUIRED_ROLE_FIELDS):
            if field not in role:
                errors.append(f"{role_id} missing required field: {field}")

        primary_profile = str(role.get("primary_profile", "")).strip()
        allowed_profiles = [str(value) for value in role.get("allowed_profiles", [])]
        if primary_profile not in allowed_profiles:
            errors.append(f"{role_id} primary_profile must be listed in allowed_profiles")
        if validate_references:
            for profile_id in allowed_profiles:
                if profile_id not in known_profiles:
                    errors.append(f"{role_id} references unknown profile: {profile_id}")

        mounted_skills = role.get("mounted_skills", [])
        if not isinstance(mounted_skills, list) or not mounted_skills:
            errors.append(f"{role_id} mounted_skills must be a non-empty list")
        elif validate_references:
            for skill_name in mounted_skills:
                if str(skill_name) not in known_skills:
                    errors.append(f"{role_id} references missing skill: {skill_name}")

        if role.get("communication_contract") != shared_contract:
            errors.append(f"{role_id} must inherit the shared communication contract exactly")
        for list_field in ("challenge_behavior", "local_judgment", "forbidden_overreach"):
            if not isinstance(role.get(list_field), list) or not role.get(list_field):
                errors.append(f"{role_id} {list_field} must be a non-empty list")
        if not isinstance(role.get("return_routes"), dict) or not role.get("return_routes"):
            errors.append(f"{role_id} return_routes must be a non-empty object")

    if role_ids != EXPECTED_ROLE_IDS:
        errors.append(f"role ids must equal {sorted(EXPECTED_ROLE_IDS)}")
    if "wff-guide" in role_ids:
        errors.append("wff-guide must not be defined; using-wff owns entry guidance")

    programmer = next((role for role in roles if role.get("id") == "wff-programmer"), {})
    forbidden = set(programmer.get("forbidden_overreach", []))
    for required in ("module-boundary-design", "api-contract-design", "data-ownership-design"):
        if required not in forbidden:
            errors.append(f"wff-programmer must forbid {required}")
    if programmer.get("return_routes", {}).get("architecture_conflict") != "wff-architect":
        errors.append("wff-programmer architecture_conflict must return to wff-architect")

    return errors


def render_role_agent_manifest_markdown(manifest: dict[str, Any]) -> str:
    lines: list[str] = [
        "# WFF Role-Agent Mounts",
        "",
        f"Schema version: `{manifest['schema_version']}`",
        f"Adapter status: `{manifest.get('adapter_status', '')}`",
        "",
        "These roles are optional entry surfaces over WFF skills and profiles. They do not replace the WFF mainline.",
        "",
        "## Shared Communication Contract",
        "",
    ]
    for item in manifest["shared_communication_contract"]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Roles")
    lines.append("")
    for role in manifest["roles"]:
        lines.extend(
            [
                f"### {role['display_name']}",
                "",
                f"- Role id: `{role['id']}`",
                f"- Primary profile: `{role['primary_profile']}`",
                f"- Allowed profiles: {', '.join(f'`{item}`' for item in role['allowed_profiles'])}",
                f"- Mounted skills: {', '.join(f'`{item}`' for item in role['mounted_skills'])}",
                f"- Professional stance: {role['professional_stance']}",
                f"- Voice: {role['voice']}",
                f"- Evidence boundary: {role['evidence_boundary']}",
                "",
                "Forbidden overreach:",
            ]
        )
        for item in role["forbidden_overreach"]:
            lines.append(f"- `{item}`")
        lines.append("")
        lines.append("Return routes:")
        for reason, target in sorted(role["return_routes"].items()):
            lines.append(f"- `{reason}` -> `{target}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_role_agent_outputs(
    *,
    manifest: dict[str, Any],
    output_json: Path | None,
    output_md: Path | None,
) -> None:
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_role_agent_manifest_markdown(manifest), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and render WFF role-agent mounts")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--output-json", help="Optional JSON output path")
    parser.add_argument("--output-md", help="Optional Markdown output path")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    manifest = load_role_agent_manifest(repo_root)
    write_role_agent_outputs(
        manifest=manifest,
        output_json=Path(args.output_json) if args.output_json else None,
        output_md=Path(args.output_md) if args.output_md else None,
    )
    if args.format == "markdown":
        print(render_role_agent_manifest_markdown(manifest), end="")
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
