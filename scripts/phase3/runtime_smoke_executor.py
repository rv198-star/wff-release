from __future__ import annotations

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


def detect_pnpm_command() -> list[str]:
    pnpm = shutil.which("pnpm")
    if pnpm:
        return [pnpm]
    corepack = shutil.which("corepack")
    if corepack:
        return [corepack, "pnpm"]
    return []


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


FRONTEND_RUNTIME_EVIDENCE_MARKER_RE = re.compile(
    r"^\s*//\s*@wff:frontend-runtime-evidence\s+page_id=(?P<page>[A-Za-z0-9_.:-]+)\s+interaction_id=(?P<interaction>[A-Za-z0-9_.:-]+)(?:\s+operation_id=(?P<operation>[A-Za-z0-9_.:-]+))?\s*$",
    re.MULTILINE,
)
FRONTEND_CONSUMER_JOURNEY_MARKER_RE = re.compile(
    r"^\s*//\s*@wff:frontend-consumer-journey\s+journey_id=(?P<journey>[A-Za-z0-9_.:-]+)\s+entry_route=(?P<entry>\S+)\s+outcome=(?P<outcome>[A-Za-z0-9_.:-]+)(?:\s+persona_id=(?P<persona>[A-Za-z0-9_.:-]+))?\s*$",
    re.MULTILINE,
)
FRONTEND_CLEAN_FIRST_USE_MARKER_RE = re.compile(
    r"^\s*//\s*@wff:frontend-clean-first-use\s+journey_id=(?P<journey>[A-Za-z0-9_.:-]+)(?:\s+persona_id=(?P<persona>[A-Za-z0-9_.:-]+))?\s*$",
    re.MULTILINE,
)
FRONTEND_CONSUMER_PAGE_MARKER_RE = re.compile(
    r"^\s*//\s*@wff:frontend-consumer-page\s+page_id=(?P<page>[A-Za-z0-9_.:-]+)\s*$",
    re.MULTILINE,
)
FRONTEND_BROWSER_SUBSTITUTION_PATTERNS = (
    ("page.route", re.compile(r"\bpage\.route\s*\(")),
    ("context.route", re.compile(r"\bcontext\.route\s*\(")),
    ("route.fulfill", re.compile(r"\broute\.fulfill\s*\(")),
    ("route.abort", re.compile(r"\broute\.abort\s*\(")),
    ("page.setContent", re.compile(r"\bpage\.setContent\s*\(")),
    ("page.setExtraHTTPHeaders", re.compile(r"\bpage\.setExtraHTTPHeaders\s*\(")),
    ("context.setExtraHTTPHeaders", re.compile(r"\bcontext\.setExtraHTTPHeaders\s*\(")),
    ("extraHTTPHeaders", re.compile(r"\bextraHTTPHeaders\b")),
    ("phase3-role-session", re.compile(r"phase3-role-session")),
    ("x-phase3-auth-context", re.compile(r"x-phase3-auth-context", re.IGNORECASE)),
    ("VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER", re.compile(r"VITE_PHASE3_ALLOW_AUTH_CONTEXT_HEADER")),
    ("direct-auth-session-endpoint", re.compile(r"[\"']/auth/session[\"']")),
    ("document.cookie", re.compile(r"\bdocument\.cookie\b")),
)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def frontend_runtime_evidence_markers(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in FRONTEND_RUNTIME_EVIDENCE_MARKER_RE.finditer(text):
        row = {"page_id": match.group("page"), "interaction_id": match.group("interaction")}
        if match.group("operation"):
            row["operation_id"] = match.group("operation")
        rows.append(row)
    return rows


def frontend_consumer_journey_markers(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in FRONTEND_CONSUMER_JOURNEY_MARKER_RE.finditer(text):
        row = {
            "journey_id": match.group("journey"),
            "entry_route": match.group("entry"),
            "outcome": match.group("outcome"),
        }
        if match.group("persona"):
            row["persona_id"] = match.group("persona")
        rows.append(row)
    return rows


def frontend_clean_first_use_markers(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in FRONTEND_CLEAN_FIRST_USE_MARKER_RE.finditer(text):
        row = {"journey_id": match.group("journey")}
        if match.group("persona"):
            row["persona_id"] = match.group("persona")
        rows.append(row)
    return rows


def frontend_consumer_page_markers(text: str) -> list[dict[str, str]]:
    return [{"page_id": match.group("page")} for match in FRONTEND_CONSUMER_PAGE_MARKER_RE.finditer(text)]


def frontend_browser_substitution_findings(text: str) -> list[str]:
    return [label for label, pattern in FRONTEND_BROWSER_SUBSTITUTION_PATTERNS if pattern.search(text)]


def playwright_json_summary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"valid": False, "expected": 0, "unexpected": 0, "skipped": 0, "flaky": 0, "project_names": []}
    stats = payload.get("stats") if isinstance(payload.get("stats"), Mapping) else {}
    config = payload.get("config") if isinstance(payload.get("config"), Mapping) else {}
    projects = config.get("projects") if isinstance(config.get("projects"), list) else []
    expected = int(stats.get("expected", 0) or 0)
    unexpected = int(stats.get("unexpected", 0) or 0)
    skipped = int(stats.get("skipped", 0) or 0)
    flaky = int(stats.get("flaky", 0) or 0)
    names = [str(project.get("name") or "").strip() for project in projects if isinstance(project, Mapping) and str(project.get("name") or "").strip()]
    return {
        "valid": bool(expected > 0 and unexpected == 0),
        "expected": expected,
        "unexpected": unexpected,
        "skipped": skipped,
        "flaky": flaky,
        "project_names": names,
    }


def parse_playwright_json_output(stdout: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload = json.loads(str(stdout or ""))
    except json.JSONDecodeError:
        return {}, playwright_json_summary(None)
    if not isinstance(payload, dict):
        return {}, playwright_json_summary(None)
    return payload, playwright_json_summary(payload)


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
