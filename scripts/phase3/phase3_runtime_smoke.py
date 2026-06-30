#!/usr/bin/env python3
"""
Execute Docker-based runtime smoke validation for a Phase-3 workspace.
"""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from common.host_port_allocator import host_port_in_use
from common.output_language import localize_phase3_runtime_smoke_report, resolve_output_locale
from phase3.phase3_started_service_smoke import run_phase3_started_service_smoke
from phase3.review_support import support_gate_exit_code, write_json_report
from phase3.runtime_smoke_executor import (
    command_has_host_port_bind_conflict,
    command_has_transient_network_failure,
    detect_compose_command,
    run_command,
    wait_for_probe,
)
from phase3.runtime_smoke_plan import build_runtime_smoke_plan as canonical_build_runtime_smoke_plan


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    checks = report.get("checks", {})
    probes = report.get("probes", {})
    commands = report.get("commands", {})
    selected_host_ports = report.get("selected_host_ports", {})
    lines = [
        "# Phase-3 Runtime Smoke Report",
        "",
        "## Summary",
        f"- verdict: {report.get('verdict', 'unknown')}",
        f"- overall_quality_gate: {report.get('overall_quality_gate', 'unknown')}",
        f"- workspace_root: {report.get('workspace_root', '')}",
        f"- docker_available: {checks.get('docker_available', False)}",
        f"- compose_command_available: {checks.get('compose_command_available', False)}",
        f"- image_build_passed: {checks.get('image_build_passed', False)}",
        f"- compose_up_passed: {checks.get('compose_up_passed', False)}",
        f"- migration_passed: {checks.get('migration_passed', False)}",
        f"- health_probe_passed: {checks.get('health_probe_passed', False)}",
        f"- readiness_probe_passed: {checks.get('readiness_probe_passed', False)}",
        f"- started_service_smoke_green: {checks.get('started_service_smoke_green', False)}",
        "",
        "## Probes",
        f"- healthz_status: {probes.get('healthz', {}).get('status_code', 'n/a')}",
        f"- readyz_status: {probes.get('readyz', {}).get('status_code', 'n/a')}",
        "",
        "## Host Ports",
        f"- api_host_port: {selected_host_ports.get('API_HOST_PORT', 'n/a')}",
        f"- web_host_port: {selected_host_ports.get('WEB_HOST_PORT', 'n/a')}",
        f"- postgres_host_port: {selected_host_ports.get('POSTGRES_HOST_PORT', 'n/a')}",
        f"- redis_host_port: {selected_host_ports.get('REDIS_HOST_PORT', 'n/a')}",
        "",
        "## Commands",
    ]
    for key in ("image_build", "compose_up", "migration", "compose_down"):
        row = commands.get(key, {})
        lines.append(f"- {key}: exit_code={row.get('exit_code', 'n/a')} command={' '.join(row.get('command', []))}")
    lines.extend(
        [
            "",
            "## Failures",
            *([f"- {item}" for item in report.get("failures", [])] or ["- none"]),
            "",
            "## Warnings",
            *([f"- {item}" for item in report.get("warnings", [])] or ["- none"]),
            "",
        ]
    )
    return localize_phase3_runtime_smoke_report("\n".join(lines), output_locale)


def compact_terminal_summary(report: dict[str, Any], output_path: Path) -> dict[str, Any]:
    checks = report.get("checks", {})
    return {
        "verdict": report.get("verdict", "unknown"),
        "overall_quality_gate": report.get("overall_quality_gate", "unknown"),
        "output_path": str(output_path.resolve()),
        "markdown_output_path": str(output_path.resolve().with_suffix(".md")),
        "checks": {
            "runtime_smoke_green": bool(checks.get("runtime_smoke_green", False)),
            "image_build_passed": bool(checks.get("image_build_passed", False)),
            "compose_up_passed": bool(checks.get("compose_up_passed", False)),
            "migration_passed": bool(checks.get("migration_passed", False)),
            "health_probe_passed": bool(checks.get("health_probe_passed", False)),
            "readiness_probe_passed": bool(checks.get("readiness_probe_passed", False)),
            "started_service_smoke_green": bool(checks.get("started_service_smoke_green", False)),
        },
        "failures": report.get("failures", []),
        "warnings": report.get("warnings", []),
    }


def _build_runtime_smoke_plan(
    *,
    workspace_root: Path,
    service_url: str | None = None,
    exclude_ports: set[int] | None = None,
) -> dict[str, object]:
    return canonical_build_runtime_smoke_plan(
        workspace_root=workspace_root,
        service_url=service_url,
        exclude_ports=exclude_ports,
        port_in_use_fn=host_port_in_use,
    )


def redact_runtime_smoke_env(env: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        normalized = key.upper()
        if "SECRET" in normalized or "PASSWORD" in normalized or normalized.endswith("_KEY"):
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def run_phase3_runtime_smoke(
    *,
    workspace_root: Path,
    output_path: Path | None = None,
    image_tag: str = "",
    service_url: str = "http://127.0.0.1:3000",
    runtime_plan: dict[str, object] | None = None,
    startup_timeout_seconds: int = 45,
    command_timeout_seconds: int = 300,
    cleanup: bool = True,
    output_locale: str | None = None,
    run_started_service_smoke: bool = True,
    started_service_smoke_fn=run_phase3_started_service_smoke,
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    dockerfile_path = workspace_root / "Dockerfile"
    compose_prod_path = workspace_root / "docker-compose.prod.yml"
    failures: list[str] = []
    warnings: list[str] = []
    commands: dict[str, Any] = {}
    probes: dict[str, Any] = {}
    started_service_smoke_report: dict[str, Any] = {}

    docker_available = bool(shutil.which("docker"))
    compose_command = detect_compose_command()
    compose_available = bool(compose_command)
    if runtime_plan is None:
        runtime_plan = _build_runtime_smoke_plan(
            workspace_root=workspace_root,
            service_url=service_url,
        )
    workspace_slug = str(runtime_plan["workspace_slug"])
    normalized_image_tag = image_tag or f"{workspace_slug}:phase3-smoke"
    project_name = str(runtime_plan["compose_project_name"])
    requested_service_url_input = str(runtime_plan["requested_service_url_input"])
    requested_service_url = requested_service_url_input
    effective_service_url = str(runtime_plan["service_url"])
    selected_host_ports = dict(runtime_plan["selected_host_ports"])
    runtime_smoke_env = dict(runtime_plan["runtime_env"])
    if effective_service_url != requested_service_url_input:
        warnings.append("runtime_smoke_service_url_adjusted")

    if not dockerfile_path.exists():
        failures.append("dockerfile_missing")
    if not compose_prod_path.exists():
        failures.append("compose_prod_missing")
    if not docker_available:
        failures.append("docker_missing")
    if docker_available and not compose_available:
        failures.append("docker_compose_missing")

    image_build_passed = False
    compose_up_passed = False
    migration_passed = False
    health_probe_passed = False
    readiness_probe_passed = False
    started_service_smoke_green = False
    compose_down_passed = not cleanup
    compose_started = False
    active_runtime_smoke_env = runtime_smoke_env

    if not failures:
        try:
            commands["image_build"] = run_command(
                [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "build", "api"],
                workspace_root,
                command_timeout_seconds,
                runtime_smoke_env,
            )
            if not commands["image_build"].get("passed") and command_has_transient_network_failure(commands["image_build"]):
                image_build_attempts = [commands["image_build"]]
                warnings.append("docker_image_build_retried_after_transient_failure")
                commands["image_build"] = run_command(
                    [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "build", "api"],
                    workspace_root,
                    command_timeout_seconds,
                    runtime_smoke_env,
                )
                image_build_attempts.append(commands["image_build"])
                commands["image_build_attempts"] = image_build_attempts
            image_build_passed = bool(commands["image_build"].get("passed"))
            if not image_build_passed:
                failures.append("docker_image_build_failed")

            if image_build_passed:
                runtime_smoke_attempts: list[dict[str, Any]] = []
                excluded_ports: set[int] = set()

                def reallocate_ports_after_bind_conflict(attempt_record: dict[str, Any]) -> None:
                    nonlocal compose_down_passed
                    nonlocal effective_service_url
                    nonlocal runtime_smoke_env
                    nonlocal selected_host_ports
                    commands["compose_down"] = run_command(
                        [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "down", "--remove-orphans", "-v"],
                        workspace_root,
                        command_timeout_seconds,
                        active_runtime_smoke_env,
                    )
                    attempt_record["compose_down"] = commands["compose_down"]
                    compose_down_passed = bool(commands["compose_down"].get("passed"))
                    if not compose_down_passed:
                        warnings.append("docker_compose_down_failed")
                    excluded_ports.update(int(port) for port in selected_host_ports.values())
                    replanned_runtime_plan = _build_runtime_smoke_plan(
                        workspace_root=workspace_root,
                        service_url=requested_service_url_input,
                        exclude_ports=excluded_ports,
                    )
                    selected_host_ports = dict(replanned_runtime_plan["selected_host_ports"])
                    effective_service_url = str(replanned_runtime_plan["service_url"])
                    runtime_smoke_env = dict(replanned_runtime_plan["runtime_env"])
                    warnings.append("runtime_smoke_ports_reallocated_after_bind_conflict")
                    if "runtime_smoke_service_url_adjusted" not in warnings and effective_service_url != requested_service_url_input:
                        warnings.append("runtime_smoke_service_url_adjusted")

                for attempt_index in range(1, 4):
                    active_runtime_smoke_env = runtime_smoke_env
                    attempt_record: dict[str, Any] = {
                        "attempt": attempt_index,
                        "selected_host_ports": dict(selected_host_ports),
                        "service_url": effective_service_url,
                    }
                    commands["migration"] = run_command(
                        [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "run", "--rm", "api", "pnpm", "migrate"],
                        workspace_root,
                        command_timeout_seconds,
                        active_runtime_smoke_env,
                    )
                    attempt_record["migration"] = commands["migration"]
                    migration_passed = bool(commands["migration"].get("passed"))
                    compose_started = True
                    if not migration_passed and command_has_host_port_bind_conflict(commands["migration"]) and attempt_index < 3:
                        runtime_smoke_attempts.append(attempt_record)
                        reallocate_ports_after_bind_conflict(attempt_record)
                        migration_passed = False
                        continue
                    if not migration_passed:
                        runtime_smoke_attempts.append(attempt_record)
                        failures.append("docker_migration_failed")
                        break

                    commands["compose_up"] = run_command(
                        [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "up", "-d", "api"],
                        workspace_root,
                        command_timeout_seconds,
                        active_runtime_smoke_env,
                    )
                    attempt_record["compose_up"] = commands["compose_up"]
                    compose_up_passed = bool(commands["compose_up"].get("passed"))
                    if not compose_up_passed and command_has_host_port_bind_conflict(commands["compose_up"]) and attempt_index < 3:
                        runtime_smoke_attempts.append(attempt_record)
                        reallocate_ports_after_bind_conflict(attempt_record)
                        compose_up_passed = False
                        migration_passed = False
                        continue
                    runtime_smoke_attempts.append(attempt_record)
                    if not compose_up_passed:
                        failures.append("docker_compose_up_failed")
                        break

                    probes["healthz"] = wait_for_probe(
                        f"{effective_service_url.rstrip('/')}/healthz",
                        startup_timeout_seconds,
                        2.0,
                    )
                    health_probe_passed = bool(probes["healthz"].get("ok"))
                    if not health_probe_passed:
                        failures.append("health_probe_failed")
                        break

                    probes["readyz"] = wait_for_probe(
                        f"{effective_service_url.rstrip('/')}/readyz",
                        startup_timeout_seconds,
                        2.0,
                    )
                    readiness_probe_passed = bool(probes["readyz"].get("ok"))
                    if not readiness_probe_passed:
                        failures.append("readiness_probe_failed")
                    break
                if runtime_smoke_attempts:
                    commands["runtime_smoke_attempts"] = runtime_smoke_attempts

            if run_started_service_smoke and health_probe_passed and readiness_probe_passed:
                started_service_smoke_output_path = (
                    output_path.resolve().parent / "started-service-smoke-report.json"
                    if output_path is not None
                    else workspace_root / "started-service-smoke-report.json"
                )
                started_service_smoke_report = started_service_smoke_fn(
                    workspace_root=workspace_root,
                    service_url=effective_service_url,
                    auth_secret=runtime_smoke_env["AUTH_TOKEN_SECRET"],
                    output_path=started_service_smoke_output_path,
                )
                started_service_smoke_green = str(started_service_smoke_report.get("verdict", "")).strip().lower() == "pass"
                if not started_service_smoke_green:
                    failures.append("started_service_smoke_failed")
        finally:
            if cleanup and compose_available and (compose_started or commands.get("compose_up")):
                commands["compose_down"] = run_command(
                    [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "down", "--remove-orphans", "-v"],
                    workspace_root,
                    command_timeout_seconds,
                    active_runtime_smoke_env,
                )
                compose_down_passed = bool(commands["compose_down"].get("passed"))
                if not compose_down_passed:
                    warnings.append("docker_compose_down_failed")

    report = {
        "workspace_root": str(workspace_root),
        "compose_project_name": project_name,
        "dockerfile_path": str(dockerfile_path),
        "compose_prod_path": str(compose_prod_path),
        "image_tag": normalized_image_tag,
        "requested_service_url": requested_service_url,
        "service_url": effective_service_url,
        "selected_host_ports": selected_host_ports,
        "runtime_smoke_env": redact_runtime_smoke_env(runtime_smoke_env),
        "overall_quality_gate": "pass" if not failures else "fail",
        "verdict": "pass" if not failures else "fail",
        "checks": {
            "dockerfile_present": dockerfile_path.exists(),
            "compose_prod_present": compose_prod_path.exists(),
            "docker_available": docker_available,
            "compose_command_available": compose_available,
            "image_build_passed": image_build_passed,
            "compose_up_passed": compose_up_passed,
            "migration_passed": migration_passed,
            "health_probe_passed": health_probe_passed,
            "readiness_probe_passed": readiness_probe_passed,
            "started_service_smoke_requested": run_started_service_smoke,
            "started_service_smoke_present": bool(started_service_smoke_report),
            "started_service_smoke_green": started_service_smoke_green,
            "cleanup_requested": cleanup,
            "compose_down_passed": compose_down_passed,
            "runtime_smoke_green": not failures,
        },
        "commands": commands,
        "probes": probes,
        "started_service_smoke": {
            "verdict": started_service_smoke_report.get("verdict", "") if started_service_smoke_report else "",
            "output_path": (
                str((output_path.resolve().parent / "started-service-smoke-report.json"))
                if output_path is not None and started_service_smoke_report
                else ""
            ),
            "checks": started_service_smoke_report.get("checks", {}) if started_service_smoke_report else {},
            "failures": started_service_smoke_report.get("failures", []) if started_service_smoke_report else [],
        },
        "failures": failures,
        "warnings": warnings,
    }

    if output_path is not None:
        output_path = output_path.resolve()
        write_json_report(output_path, report)
        write_text(output_path.with_suffix(".md"), build_markdown(report, output_locale))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Docker-based runtime smoke validation for a Phase-3 workspace")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--image-tag", default="")
    parser.add_argument("--service-url", default="http://127.0.0.1:3000")
    parser.add_argument("--startup-timeout-seconds", type=int, default=45)
    parser.add_argument("--command-timeout-seconds", type=int, default=300)
    parser.add_argument("--skip-cleanup", action="store_true")
    parser.add_argument("--skip-started-service-smoke", action="store_true")
    parser.add_argument("--output-locale", default=resolve_output_locale())
    parser.add_argument(
        "--show-full-report",
        action="store_true",
        help="print the full runtime smoke JSON report to terminal; by default stdout is a compact summary",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run_phase3_runtime_smoke(
        workspace_root=Path(args.workspace_root),
        output_path=Path(args.output),
        image_tag=args.image_tag,
        service_url=args.service_url,
        startup_timeout_seconds=max(1, int(args.startup_timeout_seconds)),
        command_timeout_seconds=max(1, int(args.command_timeout_seconds)),
        cleanup=not args.skip_cleanup,
        output_locale=args.output_locale,
        run_started_service_smoke=not args.skip_started_service_smoke,
    )
    terminal_payload = report if args.show_full_report else compact_terminal_summary(report, Path(args.output))
    print(json.dumps(terminal_payload, ensure_ascii=False))
    return support_gate_exit_code("verdict", report)


if __name__ == "__main__":
    raise SystemExit(main())
