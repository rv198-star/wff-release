from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping


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
    try:
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
    except subprocess.TimeoutExpired as exc:
        stderr_text = str(exc.stderr or "")
        timeout_message = f"Command timed out after {timeout_seconds} seconds"
        payload = {
            "command": command,
            "exit_code": 124,
            "stdout": str(exc.output or ""),
            "stderr": f"{stderr_text}\n{timeout_message}".strip(),
            "passed": False,
            "timed_out": True,
            "error": str(exc),
        }
    except OSError as exc:
        payload = {
            "command": command,
            "exit_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "passed": False,
            "timed_out": False,
            "error": str(exc),
        }
    payload.update(
        {
            "started_at_epoch_s": round(started_at_epoch_s, 3),
            "finished_at_epoch_s": round(time.time(), 3),
            "duration_ms": int(round((time.monotonic() - started_monotonic) * 1000)),
        }
    )
    return payload


def compose_output_is_v2_or_newer(value: str) -> bool:
    match = re.search(r"(?:version\s+)?v?(\d+)(?:\.\d+)", value, re.IGNORECASE)
    return bool(match and int(match.group(1)) >= 2)


def safe_compose_version_probe(command: list[str], timeout_seconds: int = 5) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def detect_compose_command() -> list[str]:
    docker = shutil.which("docker")
    if docker:
        completed = safe_compose_version_probe([docker, "compose", "version"])
        compose_output = (completed.stdout.strip() or completed.stderr.strip()) if completed is not None else ""
        if completed is not None and completed.returncode == 0 and compose_output_is_v2_or_newer(compose_output):
            return [docker, "compose"]
    docker_compose = shutil.which("docker-compose")
    if docker_compose:
        completed = safe_compose_version_probe([docker_compose, "--version"])
        compose_output = (completed.stdout.strip() or completed.stderr.strip()) if completed is not None else ""
        if completed is not None and completed.returncode == 0 and compose_output_is_v2_or_newer(compose_output):
            return [docker_compose]
    return []


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


def command_has_host_port_bind_conflict(report: Mapping[str, Any] | None) -> bool:
    if not isinstance(report, Mapping):
        return False
    text = " ".join(str(report.get(key, "")) for key in ("stdout", "stderr")).lower()
    docker_bind_for = bool(re.search(r"\bbind for \S+:\d+", text))
    docker_listen_bind = bool(re.search(r"\blisten tcp(?:4|6)?\s+\S+:\d+: bind: address already in use", text))
    if "port is already allocated" in text and docker_bind_for:
        return True
    if "ports are not available" in text and docker_listen_bind:
        return True
    if "driver failed programming external connectivity" in text and (docker_bind_for or docker_listen_bind):
        return True
    return False
