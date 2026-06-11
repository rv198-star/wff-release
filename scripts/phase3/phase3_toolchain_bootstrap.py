#!/usr/bin/env python3
"""
Prepare or assess the Phase-3 workspace toolchain bootstrap state.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common.output_language import localize_phase3_toolchain_bootstrap_report


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def command_version(binary: str, args: list[str]) -> str:
    resolved = shutil.which(binary)
    if not resolved:
        return ""
    completed = subprocess.run(
        [resolved, *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip() or completed.stderr.strip()


def compose_output_is_v2_or_newer(value: str) -> bool:
    match = re.search(r"(?:version\s+)?v?(\d+)(?:\.\d+)", value, re.IGNORECASE)
    return bool(match and int(match.group(1)) >= 2)


def package_json_count(workspace_root: Path) -> int:
    return len(list(workspace_root.rglob("package.json")))


def required_pnpm_version(workspace_root: Path) -> str:
    package_path = workspace_root / "package.json"
    if not package_path.exists():
        return ""
    try:
        package_data = json.loads(package_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    package_manager = str(package_data.get("packageManager") or "").strip()
    if not package_manager.startswith("pnpm@"):
        return ""
    return package_manager.split("@", 1)[1].strip()


def pnpm_version_matches_required(current_version: str, required_version: str) -> bool:
    if not required_version:
        return True
    return current_version.strip().lstrip("v") == required_version.strip().lstrip("v")


def node_modules_present(workspace_root: Path) -> bool:
    return (workspace_root / "node_modules").exists()


def bootstrap_command(workspace_root: Path) -> str:
    return f"pnpm install --dir {workspace_root} --frozen-lockfile=false"


def normalize_process_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def compose_version() -> str:
    docker_compose = command_version("docker", ["compose", "version"])
    if docker_compose and compose_output_is_v2_or_newer(docker_compose):
        return docker_compose
    docker_compose_standalone = command_version("docker-compose", ["--version"])
    if docker_compose_standalone and compose_output_is_v2_or_newer(docker_compose_standalone):
        return docker_compose_standalone
    return ""


def build_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    checks = report.get("checks", {})
    install = report.get("install", {})
    lines = [
        "# Phase-3 Toolchain Bootstrap Report",
        "",
        "## Summary",
        f"- overall_status: {report.get('overall_status', 'unknown')}",
        f"- recommended_formal_state: {report.get('recommended_formal_state', 'unknown')}",
        f"- status_semantics: {report.get('status_semantics', 'unknown')}",
        f"- package_json_count: {checks.get('package_json_count', 0)}",
        f"- node_modules_present_before: {checks.get('node_modules_present_before', False)}",
        f"- node_modules_present_after: {checks.get('node_modules_present_after', False)}",
        f"- node_version: {checks.get('node_version', 'missing') or 'missing'}",
        f"- pnpm_version: {checks.get('pnpm_version', 'missing') or 'missing'}",
        f"- docker_version: {checks.get('docker_version', 'missing') or 'missing'}",
        f"- docker_server_version: {checks.get('docker_server_version', 'missing') or 'missing'}",
        f"- compose_version: {checks.get('compose_version', 'missing') or 'missing'}",
        f"- bootstrap_command: {report.get('bootstrap_command', '')}",
        "",
        "## Install",
        f"- install_attempted: {install.get('attempted', False)}",
        f"- install_succeeded: {install.get('succeeded', False)}",
        f"- install_exit_code: {install.get('exit_code', 'n/a')}",
        "",
        "## Findings",
    ]
    findings = report.get("findings", [])
    if not findings:
        lines.append("- none")
    else:
        for item in findings:
            lines.append(f"- {item}")
    lines.append("")
    return localize_phase3_toolchain_bootstrap_report("\n".join(lines), output_locale)


def bootstrap_phase3_toolchain(
    *,
    workspace_root: Path,
    install: bool = False,
    strict: bool = False,
    output_path: Path | None = None,
    install_timeout_seconds: int = 600,
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    node_version = command_version("node", ["--version"])
    pnpm_version = command_version("pnpm", ["--version"])
    docker_version = command_version("docker", ["--version"])
    docker_server_version = command_version("docker", ["version", "--format", "{{.Server.Version}}"])
    docker_compose_version = compose_version()
    required_pnpm = required_pnpm_version(workspace_root)
    pnpm_version_ok = pnpm_version_matches_required(pnpm_version, required_pnpm)
    before_node_modules = node_modules_present(workspace_root)
    package_count = package_json_count(workspace_root)
    install_payload: dict[str, Any] = {
        "attempted": False,
        "succeeded": False,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
    }

    install_requested = bool(install or strict)
    if install_requested and node_version and pnpm_version and pnpm_version_ok and not before_node_modules:
        try:
            completed = subprocess.run(
                [
                    "pnpm",
                    "install",
                    "--dir",
                    str(workspace_root),
                    "--frozen-lockfile=false",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=max(1, int(install_timeout_seconds)),
            )
            install_payload = {
                "attempted": True,
                "succeeded": completed.returncode == 0,
                "exit_code": int(completed.returncode),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired as exc:
            install_payload = {
                "attempted": True,
                "succeeded": False,
                "exit_code": "timeout",
                "stdout": normalize_process_output(exc.stdout),
                "stderr": normalize_process_output(exc.stderr)
                or f"pnpm install timed out after {max(1, int(install_timeout_seconds))} seconds",
            }

    after_node_modules = node_modules_present(workspace_root)
    findings: list[str] = []
    if not node_version:
        findings.append("node_missing")
    if not pnpm_version:
        findings.append("pnpm_missing")
    if pnpm_version and not pnpm_version_ok:
        findings.append("pnpm_version_mismatch")
    if not docker_version:
        findings.append("docker_missing")
    if docker_version and not docker_server_version:
        findings.append("docker_daemon_unavailable")
    if not docker_compose_version:
        findings.append("docker_compose_missing")
    if package_count == 0:
        findings.append("package_json_missing")
    if install_payload["attempted"] and not install_payload["succeeded"]:
        findings.append("pnpm_install_timeout" if install_payload["exit_code"] == "timeout" else "pnpm_install_failed")
    if not after_node_modules:
        findings.append("node_modules_missing_after_install" if install_payload["attempted"] else "node_modules_not_installed_yet")

    hard_blocked = any(
        marker in findings
        for marker in (
            "node_missing",
            "pnpm_missing",
            "pnpm_version_mismatch",
            "docker_missing",
            "docker_compose_missing",
            "package_json_missing",
            "pnpm_install_failed",
            "pnpm_install_timeout",
            "node_modules_missing_after_install",
        )
    )
    if after_node_modules and not hard_blocked:
        overall_status = "ready"
    elif (
        not install_payload["attempted"]
        and node_version
        and pnpm_version
        and pnpm_version_ok
        and docker_version
        and docker_compose_version
        and package_count > 0
        and not hard_blocked
    ):
        overall_status = "pending-install"
    else:
        overall_status = "blocked"
    recommended_formal_state = {
        "ready": "toolchain-ready",
        "pending-install": "toolchain-install-pending",
        "blocked": "toolchain-blocked",
    }.get(overall_status, "toolchain-unknown")
    report = {
        "workspace_root": str(workspace_root),
        "bootstrap_command": bootstrap_command(workspace_root),
        "overall_status": overall_status,
        "recommended_formal_state": recommended_formal_state,
        "status_semantics": "initial-bootstrap-snapshot-before-runtime-validation",
        "checks": {
            "package_json_count": package_count,
            "node_modules_present_before": before_node_modules,
            "node_modules_present_after": after_node_modules,
            "node_version": node_version,
            "pnpm_version": pnpm_version,
            "required_pnpm_version": required_pnpm,
            "pnpm_version_matches_required": pnpm_version_ok,
            "docker_version": docker_version,
            "docker_server_version": docker_server_version,
            "compose_version": docker_compose_version,
        },
        "install": {
            **install_payload,
            "requested": install_requested,
            "strict": bool(strict),
            "timeout_seconds": max(1, int(install_timeout_seconds)),
        },
        "findings": findings,
    }

    if output_path is not None:
        output_path = output_path.resolve()
        write_text(output_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        write_text(output_path.with_suffix(".md"), build_markdown(report))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess or bootstrap the Phase-3 toolchain workspace")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--install-timeout-seconds", type=int, default=600)
    parser.add_argument("--output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = bootstrap_phase3_toolchain(
        workspace_root=Path(args.workspace_root),
        install=bool(args.install),
        strict=bool(args.strict),
        output_path=Path(args.output).resolve() if args.output else None,
        install_timeout_seconds=args.install_timeout_seconds,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["overall_status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
