#!/usr/bin/env python3
"""Export WFF role-agent configuration for supported agent platforms."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from release.role_agent_manifest import (  # noqa: E402
    RoleAgentManifestError,
    load_role_agent_manifest,
    role_by_id,
)


SUPPORTED_PLATFORMS = ("opencode", "claude-code", "codex")
CODEX_BLOCK_BEGIN = "<!-- WFF-ROLE-AGENTS:BEGIN -->"
CODEX_BLOCK_END = "<!-- WFF-ROLE-AGENTS:END -->"


class WffAgentError(RuntimeError):
    """Raised when WFF role-agent export cannot proceed."""


def yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def bullet_lines(items: list[str]) -> list[str]:
    return [f"- `{item}`" for item in items]


def role_instruction_body(role: dict[str, Any], *, platform_note: str) -> str:
    lines = [
        f"# {role['display_name']}",
        "",
        platform_note,
        "",
        "## WFF Boundary",
        "",
        "This role is an optional entry surface over WFF skills and profiles. It does not replace WFF workflow, source truth, architecture truth, implementation truth, evidence gates, or claim ceilings.",
        "",
        "## Role Identity",
        "",
        f"- Role id: `{role['id']}`",
        f"- Short name: `{role['short_name']}`",
        f"- Primary profile: `{role['primary_profile']}`",
        f"- Allowed profiles: {', '.join(f'`{item}`' for item in role['allowed_profiles'])}",
        f"- Professional stance: {role['professional_stance']}",
        f"- Voice: {role['voice']}",
        "",
        "## Mounted WFF Skills",
        "",
        *bullet_lines(role["mounted_skills"]),
        "",
        "Use only the abilities implied by these mounted skills. If the user asks for work outside this role, route to the correct WFF role instead of pretending to own it.",
        "",
        "## Communication Contract",
        "",
        *bullet_lines(role["communication_contract"]),
        "",
        "Explain hard ideas in plain language first. Use a short story, example, or close analogy before WFF terms when the user may not understand the term.",
        "",
        "## Local Judgment",
        "",
        *bullet_lines(role["local_judgment"]),
        "",
        "## Challenge Behavior",
        "",
        *bullet_lines(role["challenge_behavior"]),
        "",
        "## Forbidden Overreach",
        "",
        *bullet_lines(role["forbidden_overreach"]),
        "",
        "## Return Routes",
        "",
    ]
    for reason, target in sorted(role["return_routes"].items()):
        lines.append(f"- `{reason}` -> `{target}`")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            role["evidence_boundary"],
            "",
            "Do not upgrade unverified facts into confirmed truth. Do not claim validation, production readiness, approval, or acceptance without evidence.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_opencode_agent(role: dict[str, Any]) -> str:
    frontmatter = [
        "---",
        f"description: {yaml_scalar(role['professional_stance'])}",
        "mode: all",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + role_instruction_body(
        role,
        platform_note=(
            "OpenCode can load this as a project agent from `.opencode/agents/`. "
            "`mode: all` lets the role work both as a direct primary agent and as an @-mentioned subagent."
        ),
    )


def render_claude_agent(role: dict[str, Any]) -> str:
    frontmatter = [
        "---",
        f"name: {role['id']}",
        f"description: {yaml_scalar(role['professional_stance'])}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + role_instruction_body(
        role,
        platform_note="Claude Code can load this as a project subagent from `.claude/agents/`.",
    )


def render_codex_role_doc(role: dict[str, Any]) -> str:
    return role_instruction_body(
        role,
        platform_note=(
            "Codex does not provide the same native role switching surface as OpenCode or Claude Code in this adapter. "
            "Use this document as a project-local WFF role instruction and reference it from `AGENTS.md` or the current conversation."
        ),
    )


def role_sort_key(role: dict[str, Any]) -> str:
    return str(role["id"])


def select_roles(manifest: dict[str, Any], role_args: list[str]) -> list[dict[str, Any]]:
    if not role_args:
        raise WffAgentError("at least one role id or `all` is required")
    if "all" in role_args:
        if len(role_args) != 1:
            raise WffAgentError("use either `all` or explicit role ids, not both")
        return sorted(manifest["roles"], key=role_sort_key)
    selected: list[dict[str, Any]] = []
    try:
        for role_id in role_args:
            selected.append(role_by_id(manifest, role_id))
    except RoleAgentManifestError as exc:
        raise WffAgentError(str(exc)) from exc
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for role in selected:
        role_id = str(role["id"])
        if role_id in seen:
            continue
        seen.add(role_id)
        deduped.append(role)
    return deduped


def write_role_files(output_dir: Path, roles: list[dict[str, Any]], renderer) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for role in roles:
        path = output_dir / f"{role['id']}.md"
        path.write_text(renderer(role), encoding="utf-8")
        written.append(path)
    return written


def render_codex_agents_block(roles: list[dict[str, Any]]) -> str:
    lines = [
        CODEX_BLOCK_BEGIN,
        "## WFF Role Agents",
        "",
        "Codex does not provide the same native role switching surface as OpenCode or Claude Code in this adapter.",
        "Use these project-local role files as explicit instructions when you want a WFF professional role to guide the work:",
        "",
    ]
    for role in roles:
        lines.append(f"- `{role['display_name']}`: `.codex/wff-agents/{role['id']}.md`")
    lines.extend(
        [
            "",
            "These roles are optional entry surfaces over WFF skills and profiles. They do not replace WFF workflow, evidence gates, or claim ceilings.",
            CODEX_BLOCK_END,
        ]
    )
    return "\n".join(lines)


def update_codex_agents_md(project_root: Path, roles: list[dict[str, Any]]) -> Path:
    agents_path = project_root / "AGENTS.md"
    existing = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    block = render_codex_agents_block(roles)
    pattern = re.compile(
        rf"{re.escape(CODEX_BLOCK_BEGIN)}.*?{re.escape(CODEX_BLOCK_END)}",
        flags=re.DOTALL,
    )
    if pattern.search(existing):
        updated = pattern.sub(block, existing)
    else:
        separator = "\n\n" if existing.strip() else ""
        updated = existing.rstrip() + separator + block + "\n"
    agents_path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return agents_path


def setup_platform(platform: str, project_root: Path, roles: list[dict[str, Any]]) -> list[Path]:
    if platform == "opencode":
        return write_role_files(project_root / ".opencode" / "agents", roles, render_opencode_agent)
    if platform == "claude-code":
        return write_role_files(project_root / ".claude" / "agents", roles, render_claude_agent)
    if platform == "codex":
        written = write_role_files(project_root / ".codex" / "wff-agents", roles, render_codex_role_doc)
        written.append(update_codex_agents_md(project_root, roles))
        return written
    raise WffAgentError(
        "unsupported WFF agent platform: "
        f"{platform}; supported platforms: {', '.join(SUPPORTED_PLATFORMS)}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export WFF role-agent configuration for agent platforms")
    parser.add_argument("--repo-root", default=".", help="WFF repository or install-pack root")

    subparsers = parser.add_subparsers(dest="command", required=True)
    setup = subparsers.add_parser("setup", help="write project-local platform role configuration")
    setup.add_argument("platform", help="target platform: opencode, claude-code, or codex")
    setup.add_argument("roles", nargs="+", help="role ids to export, or `all`")
    setup.add_argument("--project-root", default=".", help="business project root to update")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "setup":
        raise WffAgentError(f"unsupported command: {args.command}")

    repo_root = Path(args.repo_root).resolve()
    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        raise WffAgentError(f"project root does not exist: {project_root}")
    if not project_root.is_dir():
        raise WffAgentError(f"project root is not a directory: {project_root}")
    try:
        manifest = load_role_agent_manifest(repo_root, validate_references=False)
    except RoleAgentManifestError as exc:
        raise WffAgentError(str(exc)) from exc
    roles = select_roles(manifest, list(args.roles))
    written = setup_platform(str(args.platform), project_root, roles)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WffAgentError as exc:
        print(f"[wff-agent] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
