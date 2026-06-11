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
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from common.host_port_allocator import allocate_host_ports, host_port_in_use
from common.output_language import localize_phase3_runtime_smoke_report, resolve_output_locale
from phase3.phase3_started_service_smoke import run_phase3_started_service_smoke


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "phase3-runtime-smoke"


def workspace_identity_slug(workspace_root: Path) -> str:
    resolved = str(workspace_root.resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:8]
    return f"{slugify(workspace_root.name)}-{digest}"


def completed_payload(command: list[str], completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": command,
        "exit_code": int(completed.returncode),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def run_command(command: list[str], cwd: Path, timeout_seconds: int, extra_env: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    started_at_epoch_s = time.time()
    started_monotonic = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
        env=env,
    )
    payload = completed_payload(command, completed)
    payload.update(
        {
            "started_at_epoch_s": round(started_at_epoch_s, 3),
            "finished_at_epoch_s": round(time.time(), 3),
            "duration_ms": int(round((time.monotonic() - started_monotonic) * 1000)),
        }
    )
    return payload


def command_has_transient_network_failure(payload: dict[str, Any]) -> bool:
    combined = f"{payload.get('stdout', '')}\n{payload.get('stderr', '')}".lower()
    return any(
        marker in combined
        for marker in (
            "eai_again",
            "etimedout",
            "econnreset",
            "temporary failure",
            "fetch failed",
            "network timeout",
        )
    )


def detect_compose_command() -> list[str]:
    docker = shutil.which("docker")
    if docker:
        completed = subprocess.run(
            [docker, "compose", "version"],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            return [docker, "compose"]
    docker_compose = shutil.which("docker-compose")
    if docker_compose:
        return [docker_compose]
    return []


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def probe_url(url: str, timeout_seconds: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            body = response.read(512).decode("utf-8", errors="replace")
            return {
                "url": url,
                "ok": 200 <= int(response.status) < 300,
                "status_code": int(response.status),
                "body_excerpt": body,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(512).decode("utf-8", errors="replace")
        return {
            "url": url,
            "ok": False,
            "status_code": int(exc.code),
            "body_excerpt": body,
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "url": url,
            "ok": False,
            "status_code": 0,
            "body_excerpt": "",
            "error": str(exc),
        }


def wait_for_probe(url: str, timeout_seconds: int, interval_seconds: float) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    latest = probe_url(url, timeout_seconds=max(1, int(interval_seconds) or 1))
    while time.time() < deadline:
        if latest.get("ok"):
            return latest
        time.sleep(interval_seconds)
        latest = probe_url(url, timeout_seconds=max(1, int(interval_seconds) or 1))
    latest["timed_out"] = True
    return latest


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


def runtime_smoke_port_defaults(workspace_root: Path) -> dict[str, int]:
    defaults = {
        **parse_env_file(workspace_root / ".env.example"),
        **parse_env_file(workspace_root / ".env"),
    }
    resolved: dict[str, int] = {
        "WEB_HOST_PORT": 53100,
        "POSTGRES_HOST_PORT": 55432,
        "REDIS_HOST_PORT": 56379,
    }
    for key in tuple(resolved.keys()):
        raw = (
            os.environ.get(f"PHASE3_RUNTIME_SMOKE_{key}", "").strip()
            or os.environ.get(key, "").strip()
            or str(defaults.get(key, "")).strip()
        )
        if not raw:
            continue
        try:
            resolved[key] = int(raw)
        except ValueError:
            continue
    return resolved


def resolve_runtime_smoke_host_ports(
    *,
    workspace_root: Path,
    service_url: str,
) -> dict[str, int]:
    parsed = urlparse(service_url)
    defaults = runtime_smoke_port_defaults(workspace_root)
    return allocate_host_ports(
        requested_ports={
            "API_HOST_PORT": int(parsed.port or 3000),
            "WEB_HOST_PORT": defaults["WEB_HOST_PORT"],
            "POSTGRES_HOST_PORT": defaults["POSTGRES_HOST_PORT"],
            "REDIS_HOST_PORT": defaults["REDIS_HOST_PORT"],
        },
        port_in_use=host_port_in_use,
    )


def normalize_runtime_smoke_service_url(service_url: str | None) -> str:
    value = str(service_url or "").strip()
    if not value or value.lower() in {"none", "null"}:
        return "http://127.0.0.1:3000"
    return value


def runtime_smoke_service_url(service_url: str, api_host_port: int) -> str:
    parsed = urlparse(normalize_runtime_smoke_service_url(service_url))
    scheme = parsed.scheme or "http"
    hostname = parsed.hostname or "127.0.0.1"
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname if api_host_port <= 0 else f"{hostname}:{api_host_port}"
    return urlunparse(parsed._replace(scheme=scheme, netloc=netloc))


def build_runtime_smoke_env(service_url: str, selected_host_ports: dict[str, int]) -> dict[str, str]:
    return {
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": "app",
        "DATABASE_URL": "postgresql://postgres:postgres@postgres:5432/app",
        "REDIS_URL": "redis://redis:6379",
        "OIDC_ISSUER_URL": "https://smoke.invalid/oidc",
        "OIDC_CLIENT_ID": "phase3-smoke-client",
        "OIDC_CLIENT_SECRET": "phase3-smoke-secret",
        "AUTH_TOKEN_SECRET": "phase3-runtime-smoke-secret",
        "PHASE3_ALLOW_AUTH_CONTEXT_HEADER": "false",
        "PORT": "3000",
        "HOST": "0.0.0.0",
        "WEB_PORT": "3100",
        "WEB_API_BASE_URL": "http://api:3000",
        "VITE_API_BASE_URL": "/api",
        "API_HOST_PORT": str(selected_host_ports["API_HOST_PORT"]),
        "WEB_HOST_PORT": str(selected_host_ports["WEB_HOST_PORT"]),
        "POSTGRES_HOST_PORT": str(selected_host_ports["POSTGRES_HOST_PORT"]),
        "REDIS_HOST_PORT": str(selected_host_ports["REDIS_HOST_PORT"]),
    }


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
    workspace_slug = workspace_identity_slug(workspace_root)
    normalized_image_tag = image_tag or f"{workspace_slug}:phase3-smoke"
    project_name = f"phase3-smoke-{workspace_slug}"
    requested_service_url = service_url
    normalized_service_url = normalize_runtime_smoke_service_url(service_url)
    selected_host_ports = resolve_runtime_smoke_host_ports(
        workspace_root=workspace_root,
        service_url=normalized_service_url,
    )
    effective_service_url = runtime_smoke_service_url(
        normalized_service_url,
        selected_host_ports["API_HOST_PORT"],
    )
    runtime_smoke_env = build_runtime_smoke_env(effective_service_url, selected_host_ports)
    runtime_smoke_env["DOCKER_BUILDKIT"] = os.environ.get("DOCKER_BUILDKIT", "1") or "1"
    runtime_smoke_env["COMPOSE_DOCKER_CLI_BUILD"] = os.environ.get("COMPOSE_DOCKER_CLI_BUILD", "1") or "1"
    if effective_service_url != requested_service_url:
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
                commands["compose_up"] = run_command(
                    [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "up", "-d", "api"],
                    workspace_root,
                    command_timeout_seconds,
                    runtime_smoke_env,
                )
                compose_up_passed = bool(commands["compose_up"].get("passed"))
                compose_started = compose_up_passed
                if not compose_up_passed:
                    failures.append("docker_compose_up_failed")

            if compose_up_passed:
                commands["migration"] = run_command(
                    [*compose_command, "-p", project_name, "-f", str(compose_prod_path), "run", "--rm", "api", "pnpm", "migrate"],
                    workspace_root,
                    command_timeout_seconds,
                    runtime_smoke_env,
                )
                migration_passed = bool(commands["migration"].get("passed"))
                if not migration_passed:
                    failures.append("docker_migration_failed")

            if compose_up_passed:
                probes["healthz"] = wait_for_probe(
                    f"{effective_service_url.rstrip('/')}/healthz",
                    startup_timeout_seconds,
                    2.0,
                )
                health_probe_passed = bool(probes["healthz"].get("ok"))
                if not health_probe_passed:
                    failures.append("health_probe_failed")

                probes["readyz"] = wait_for_probe(
                    f"{effective_service_url.rstrip('/')}/readyz",
                    startup_timeout_seconds,
                    2.0,
                )
                readiness_probe_passed = bool(probes["readyz"].get("ok"))
                if not readiness_probe_passed:
                    failures.append("readiness_probe_failed")

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
                    runtime_smoke_env,
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
        write_text(output_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
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
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
