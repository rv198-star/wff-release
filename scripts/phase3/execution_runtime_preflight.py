from __future__ import annotations

import json
import os
import re
import subprocess
import time
import zlib
from pathlib import Path
from typing import Any, Callable

from common.host_port_allocator import choose_available_host_port, host_port_in_use
from phase3.verification_backend_evidence import (
    analyze_backend_test_file,
    flatten_packet_tests,
    packet_lane,
)


RuntimeSubprocessRun = Callable[..., subprocess.CompletedProcess[str]]
PortInUseProbe = Callable[[str, int], bool]
ShellResolver = Callable[[], str]
SleepSeconds = Callable[[float], None]

RUNTIME_PREFLIGHT_PORT_RETRY_LIMIT = 5


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_execution_env(*, workspace_root: Path, run_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    home_dir = run_dir / "execution-home"
    corepack_home = run_dir / "corepack-home"
    pnpm_home = run_dir / "pnpm-home"
    xdg_cache_home = run_dir / "xdg-cache"
    npm_cache = run_dir / "npm-cache"
    for path in (home_dir, corepack_home, pnpm_home, xdg_cache_home, npm_cache):
        path.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home_dir)
    env["COREPACK_HOME"] = str(corepack_home)
    env["PNPM_HOME"] = str(pnpm_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    env["npm_config_cache"] = str(npm_cache)
    env["npm_config_userconfig"] = str(workspace_root / ".npmrc")
    env["PHASE3_RUN_DIR"] = str(run_dir)
    env["PHASE3_WORKSPACE_ROOT"] = str(workspace_root)
    env.setdefault("CI", "1")
    env.setdefault("FORCE_COLOR", "0")
    current_path = env.get("PATH", "")
    env["PATH"] = f"{pnpm_home}:{current_path}" if current_path else str(pnpm_home)
    return env


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


def parse_optional_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def choose_postgres_host_port(
    *,
    workspace_root: Path,
    packet_id_value: str,
    starting_port: int | None = None,
    exclude_ports: set[int] | None = None,
    port_in_use_probe: PortInUseProbe | None = None,
) -> int:
    defaults = {
        **parse_env_file(workspace_root / ".env.example"),
        **parse_env_file(workspace_root / ".env"),
    }
    seed = f"{workspace_root}:{packet_id_value}"
    base = 55000 + (zlib.adler32(seed.encode("utf-8")) % 3000)
    raw_requested = str(defaults.get("POSTGRES_HOST_PORT", str(base)) or str(base)).strip()
    try:
        requested = int(raw_requested)
    except (TypeError, ValueError):
        requested = base
    requested = starting_port or requested
    return choose_available_host_port(
        requested_port=requested,
        exclude_ports=exclude_ports,
        host="0.0.0.0",
        min_port=54000,
        max_port=62000,
        fallback_port=base,
        port_in_use=port_in_use_probe or host_port_in_use,
    )


def compose_project_name(*, workspace_root: Path, run_dir: Path | None = None) -> str:
    seed_value = str(workspace_root.resolve())
    if run_dir is not None:
        seed_value = f"{seed_value}:{run_dir.resolve()}"
    seed = seed_value.encode("utf-8", errors="ignore")
    suffix = zlib.adler32(seed) & 0xFFFFFFFF
    return f"phase3-{suffix:08x}"


def validate_runtime_compose_template(compose_path: Path) -> dict[str, Any]:
    findings: list[str] = []
    if not compose_path.exists() or not compose_path.is_file():
        return {
            "valid": False,
            "compose_path": str(compose_path),
            "findings": ["compose_file_missing"],
        }

    content = compose_path.read_text(encoding="utf-8", errors="ignore")
    if "container_name:" in content:
        findings.append("container_name_forbidden")
    if "  postgres:" not in content:
        findings.append("postgres_service_missing")
    if "image: postgres:16" not in content:
        findings.append("postgres_image_must_be_postgres_16")
    for env_key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        if env_key not in content:
            findings.append(f"{env_key.lower()}_missing")
    postgres_loopback_pattern = re.compile(
        r"127\.0\.0\.1:\$\{POSTGRES_HOST_PORT(?::-?[0-9]+)?\}:5432"
    )
    if not postgres_loopback_pattern.search(content):
        findings.append("postgres_port_must_bind_loopback_variable")
    if re.search(r'["\']?5432:5432["\']?', content):
        findings.append("postgres_fixed_host_port_forbidden")
    if "  redis:" in content and not re.search(
        r"127\.0\.0\.1:\$\{REDIS_HOST_PORT(?::-?[0-9]+)?\}:6379",
        content,
    ):
        findings.append("redis_port_must_bind_loopback_variable")
    if "  api:" in content:
        if "${API_HOST_PORT" not in content:
            findings.append("api_host_port_must_be_variable")
        if "/healthz" not in content:
            findings.append("api_healthcheck_missing")
    if "  web:" in content:
        if "${WEB_HOST_PORT" not in content:
            findings.append("web_host_port_must_be_variable")
        if "CONTAINER_HEALTH_PATH: /" not in content:
            findings.append("web_healthcheck_missing")
    return {
        "valid": not findings,
        "compose_path": str(compose_path),
        "findings": findings,
    }


def backend_runtime_preflight_required(*, packet_document: dict[str, Any], workspace_root: Path) -> bool:
    candidate_tests = flatten_packet_tests(packet_document, ("sql", "contract", "scenario", "replay"))
    if not candidate_tests:
        return False
    if packet_lane(packet_document) == "backend":
        return True
    analyzed_tests = [
        analyze_backend_test_file(test_path, workspace_root=workspace_root)
        for test_path in candidate_tests
    ]
    return any(
        bool(item.get("service_boundary_truth"))
        or bool(item.get("sql_persistence_truth"))
        or bool(item.get("service_persistence_roundtrip_truth"))
        or bool(item.get("migration_execution_truth"))
        for item in analyzed_tests
    )


def is_port_bind_conflict(stderr: str) -> bool:
    normalized = str(stderr).lower()
    return "port is already allocated" in normalized or "bind for 0.0.0.0:" in normalized


def ensure_backend_runtime_preflight(
    *,
    packet_document: dict[str, Any],
    workspace_root: Path,
    execution_env: dict[str, str],
    run_dir: Path,
    port_in_use_probe: PortInUseProbe | None = None,
    subprocess_run: RuntimeSubprocessRun | None = None,
    shell_resolver: ShellResolver | None = None,
    sleep_seconds: SleepSeconds | None = None,
) -> dict[str, Any]:
    result = {
        "required": False,
        "ready": True,
        "started": False,
        "command": "",
        "project_name": "",
        "failure_reason": "",
        "stdout_log_path": "",
        "stderr_log_path": "",
        "attempted_ports": [],
        "template_validation": {},
    }
    compose_path = workspace_root / "docker-compose.dev.yml"
    if not backend_runtime_preflight_required(packet_document=packet_document, workspace_root=workspace_root) or not compose_path.exists():
        return result

    run_command = subprocess_run or subprocess.run
    resolve_shell = shell_resolver or (lambda: "/bin/sh")
    sleep = sleep_seconds or time.sleep
    probe = port_in_use_probe or host_port_in_use

    result["required"] = True
    project_name = compose_project_name(workspace_root=workspace_root, run_dir=run_dir)
    execution_env["COMPOSE_PROJECT_NAME"] = project_name
    result["project_name"] = project_name
    stdout_path = run_dir / "verification-logs" / "runtime-preflight.stdout.log"
    stderr_path = run_dir / "verification-logs" / "runtime-preflight.stderr.log"
    result["stdout_log_path"] = str(stdout_path)
    result["stderr_log_path"] = str(stderr_path)
    template_validation = validate_runtime_compose_template(compose_path)
    result["template_validation"] = template_validation
    if not template_validation["valid"]:
        write_text(stdout_path, "")
        write_text(stderr_path, json.dumps(template_validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        result["ready"] = False
        result["failure_reason"] = "runtime_preflight_compose_template_invalid"
        return result
    packet_id_value = str(packet_document.get("packet_id", "")).strip()
    port_seed_value = f"{packet_id_value}:{run_dir.resolve()}"
    attempted_ports: set[int] = set()
    combined_stdout = ""
    combined_stderr = ""
    requested_preflight_port = parse_optional_int(
        execution_env.get("POSTGRES_HOST_PORT")
        or execution_env.get("PHASE3_RUNTIME_SMOKE_POSTGRES_HOST_PORT")
    )
    postgres_port = choose_postgres_host_port(
        workspace_root=workspace_root,
        packet_id_value=port_seed_value,
        starting_port=requested_preflight_port,
        port_in_use_probe=probe,
    )
    command = ""
    for attempt in range(1, RUNTIME_PREFLIGHT_PORT_RETRY_LIMIT + 1):
        attempted_ports.add(postgres_port)
        result["attempted_ports"] = sorted(attempted_ports)
        execution_env["POSTGRES_HOST_PORT"] = str(postgres_port)
        execution_env["DATABASE_URL"] = f"postgresql://postgres:postgres@127.0.0.1:{postgres_port}/app"
        command = f"docker compose -p {project_name} -f {compose_path} --project-directory {workspace_root} up -d postgres"
        result["command"] = command
        up_completed = run_command(
            command,
            cwd=workspace_root,
            shell=True,
            executable=resolve_shell(),
            text=True,
            capture_output=True,
            env=execution_env,
        )
        combined_stdout += f"[attempt {attempt} port {postgres_port}]\n{up_completed.stdout}"
        combined_stderr += f"[attempt {attempt} port {postgres_port}]\n{up_completed.stderr}"
        if up_completed.returncode == 0:
            break
        if attempt < RUNTIME_PREFLIGHT_PORT_RETRY_LIMIT and is_port_bind_conflict(up_completed.stderr):
            postgres_port = choose_postgres_host_port(
                workspace_root=workspace_root,
                packet_id_value=packet_id_value,
                starting_port=postgres_port + 1,
                exclude_ports=attempted_ports,
                port_in_use_probe=probe,
            )
            continue
        write_text(stdout_path, combined_stdout)
        write_text(stderr_path, combined_stderr)
        result["ready"] = False
        result["failure_reason"] = "runtime_preflight_compose_up_failed"
        return result

    write_text(stdout_path, combined_stdout)
    write_text(stderr_path, combined_stderr)

    result["started"] = True
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        ready_check = run_command(
            f"docker compose -p {project_name} -f {compose_path} --project-directory {workspace_root} exec -T postgres pg_isready -U postgres",
            cwd=workspace_root,
            shell=True,
            executable=resolve_shell(),
            text=True,
            capture_output=True,
            env=execution_env,
        )
        if ready_check.returncode == 0:
            return result
        sleep(1)
    result["ready"] = False
    result["failure_reason"] = "runtime_preflight_postgres_not_ready"
    return result


def teardown_backend_runtime_preflight(
    *,
    workspace_root: Path,
    execution_env: dict[str, str],
    subprocess_run: RuntimeSubprocessRun | None = None,
    shell_resolver: ShellResolver | None = None,
) -> None:
    compose_path = workspace_root / "docker-compose.dev.yml"
    if not compose_path.exists():
        return
    project_name = str(execution_env.get("COMPOSE_PROJECT_NAME", "")).strip()
    if not project_name:
        project_name = compose_project_name(workspace_root=workspace_root)
    run_command = subprocess_run or subprocess.run
    resolve_shell = shell_resolver or (lambda: "/bin/sh")
    run_command(
        f"docker compose -p {project_name} -f {compose_path} --project-directory {workspace_root} down --remove-orphans",
        cwd=workspace_root,
        shell=True,
        executable=resolve_shell(),
        text=True,
        capture_output=True,
        env=execution_env,
    )
