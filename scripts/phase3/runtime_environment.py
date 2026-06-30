from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from common.output_language import localize_phase3_runtime_environment_ledger
from phase3.phase3_toolchain_bootstrap import command_version, compose_version


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def normalize_environment_tokens(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for token in str(value).split(","):
            cleaned = token.strip().lower()
            if cleaned:
                normalized.add(cleaned)
    return normalized


def detect_current_available_runtime_environments(
    *,
    explicit_available_runtime_environments: list[str] | None = None,
    bootstrap_report: dict[str, Any] | None = None,
    command_version_fn: Callable[[str, list[str]], str] | None = None,
    compose_version_fn: Callable[[], str] | None = None,
) -> list[str]:
    resolved_command_version = command_version_fn or command_version
    resolved_compose_version = compose_version_fn or compose_version
    available = normalize_environment_tokens(explicit_available_runtime_environments)
    checks = bootstrap_report.get("checks", {}) if isinstance(bootstrap_report, dict) else {}
    if not isinstance(checks, dict):
        checks = {}

    docker_version = str(checks.get("docker_version", "")).strip() or resolved_command_version("docker", ["--version"])
    docker_server_version = str(checks.get("docker_server_version", "")).strip() or resolved_command_version(
        "docker",
        ["version", "--format", "{{.Server.Version}}"],
    )
    docker_compose_version = str(checks.get("compose_version", "")).strip() or resolved_compose_version()
    if docker_version and docker_server_version and docker_compose_version:
        available.add("docker-server")

    node_version = str(checks.get("node_version", "")).strip() or resolved_command_version("node", ["--version"])
    pnpm_version = str(checks.get("pnpm_version", "")).strip() or resolved_command_version("pnpm", ["--version"])
    if node_version and pnpm_version:
        available.add("web-harness")

    return sorted(available)


def infer_required_runtime_environment(packet_document: dict[str, Any]) -> str:
    explicit = str(packet_document.get("required_runtime_environment", "")).strip().lower()
    if explicit:
        return explicit

    targets = [str(item).strip().lower() for item in packet_document.get("implementation_targets", []) if str(item).strip()]
    hint = str(packet_document.get("skill_entrypoint_hint", "")).strip().lower()
    lane = str(packet_document.get("lane", "")).strip().lower()

    joined = " ".join([hint, lane, *targets])
    if any(token in joined for token in ("ios", "swift", "xcode", "uikit", "swiftui")):
        return "ios-simulator-or-macos-build-host"
    if any(token in joined for token in ("android", "kotlin", "gradle", "jetpack")):
        return "android-emulator-or-android-build-host"
    if "flutter" in joined:
        return "flutter-device-or-emulator"
    if "react-native" in joined:
        return "mobile-simulator-or-device-harness"
    if any(token in joined for token in ("electron", "tauri", "desktop")):
        return "desktop-runtime-harness"
    if "/apps/web/" in joined or "frontend-web" in joined or lane == "frontend":
        return "browser-runtime-or-web-harness"
    if "/apps/api/" in joined or "backend-api" in joined or lane == "backend":
        return "docker-server"
    return "target-runtime-environment"


def blocked_capabilities(environment: str) -> list[str]:
    mapping = {
        "docker-server": ["container-build", "compose-startup", "migration-smoke", "health-readiness-smoke"],
        "browser-runtime-or-web-harness": ["ui-runtime", "browser-integration", "frontend-scenario-replay"],
        "ios-simulator-or-macos-build-host": ["ios-build", "ios-simulator-runtime", "ios-ui-integration"],
        "android-emulator-or-android-build-host": ["android-build", "android-emulator-runtime", "android-ui-integration"],
        "flutter-device-or-emulator": ["flutter-build", "flutter-runtime", "flutter-ui-integration"],
        "mobile-simulator-or-device-harness": ["mobile-build", "mobile-runtime", "mobile-ui-integration"],
        "desktop-runtime-harness": ["desktop-build", "desktop-runtime", "desktop-ui-integration"],
    }
    return mapping.get(environment, ["target-runtime-validation"])


def handoff_requirement(environment: str) -> str:
    return f"Provide {environment} and rerun packet verification before claiming verified / implementation-ready."


def available_for_environment(required: str, available: set[str]) -> bool:
    if required in available:
        return True
    aliases = {
        "browser-runtime-or-web-harness": {"browser-runtime", "web-harness"},
        "ios-simulator-or-macos-build-host": {"ios-simulator", "macos-build-host"},
        "android-emulator-or-android-build-host": {"android-emulator", "android-build-host"},
        "flutter-device-or-emulator": {"flutter-device", "flutter-emulator"},
        "mobile-simulator-or-device-harness": {"mobile-simulator", "device-harness"},
    }
    return bool(aliases.get(required, set()) & available)


def build_runtime_environment_ledger_markdown(report: dict[str, Any], output_locale: str | None = None) -> str:
    lines = [
        "# Phase-3 Runtime Environment Ledger",
        "",
        "## Summary",
        f"- packet_count: {report.get('summary', {}).get('packet_count', 0)}",
        f"- packets_with_available_runtime: {report.get('summary', {}).get('packets_with_available_runtime', 0)}",
        f"- packets_missing_runtime: {report.get('summary', {}).get('packets_missing_runtime', 0)}",
        f"- available_runtime_environments: {', '.join(report.get('available_runtime_environments', [])) or 'none'}",
        "",
        "## Packet Ledger",
    ]
    rows = report.get("rows", [])
    if not isinstance(rows, list) or not rows:
        lines.append("- none")
    else:
        for row in rows:
            if not isinstance(row, dict):
                continue
            lines.extend(
                [
                    f"- packet_id: {row.get('packet_id', '')}",
                    f"  lane: {row.get('lane', '')}",
                    f"  required_runtime_environment: {row.get('required_runtime_environment', '')}",
                    f"  current_availability: {row.get('current_availability', '')}",
                    f"  allowed_progress_ceiling: {row.get('allowed_progress_ceiling', '')}",
                    f"  blocked_capabilities: {', '.join(row.get('blocked_capabilities', [])) or 'none'}",
                ]
            )
    lines.append("")
    return localize_phase3_runtime_environment_ledger("\n".join(lines), output_locale)


def generate_runtime_environment_ledger(
    *,
    execution_loop_plan: dict[str, Any],
    output_dir: Path,
    available_runtime_environments: list[str] | None = None,
) -> dict[str, Any]:
    available = normalize_environment_tokens(available_runtime_environments)
    rows: list[dict[str, Any]] = []

    for wave in execution_loop_plan.get("waves", []):
        if not isinstance(wave, dict):
            continue
        wave_number = int(wave.get("wave", 0) or 0)
        for packet in wave.get("worker_packets", []):
            if not isinstance(packet, dict):
                continue
            packet_id_value = f"wave-{wave_number:02d}:{str(packet.get('lane', '')).strip()}"
            packet_path = output_dir / str(packet.get("packet_json", "")).strip()
            packet_document = load_json(packet_path) if packet_path.exists() else {"packet_id": packet_id_value, **packet}
            required_environment = infer_required_runtime_environment(packet_document)
            is_available = available_for_environment(required_environment, available)
            rows.append(
                {
                    "packet_id": packet_id_value,
                    "wave": wave_number,
                    "lane": str(packet_document.get("lane", packet.get("lane", ""))).strip(),
                    "work_package_ids": list(packet_document.get("work_package_ids", [])),
                    "required_runtime_environment": required_environment,
                    "current_availability": "available" if is_available else "missing",
                    "blocked_capabilities": [] if is_available else blocked_capabilities(required_environment),
                    "allowed_progress_ceiling": "runtime-verified-eligible" if is_available else "static-implementation-only",
                    "handoff_requirement": "" if is_available else handoff_requirement(required_environment),
                }
            )

    summary = {
        "packet_count": len(rows),
        "packets_with_available_runtime": sum(1 for row in rows if row["current_availability"] == "available"),
        "packets_missing_runtime": sum(1 for row in rows if row["current_availability"] != "available"),
    }
    return {
        "available_runtime_environments": sorted(available),
        "summary": summary,
        "rows": rows,
    }


def refresh_runtime_environment_ledger(
    *,
    execution_loop_plan_path: Path,
    output_dir: Path,
    output_path: Path | None = None,
    explicit_available_runtime_environments: list[str] | None = None,
    bootstrap_report: dict[str, Any] | None = None,
    command_version_fn: Callable[[str, list[str]], str] | None = None,
    compose_version_fn: Callable[[], str] | None = None,
) -> dict[str, Any]:
    resolved_output_dir = output_dir.resolve()
    resolved_output_path = (output_path or (resolved_output_dir / "runtime-environment-ledger.json")).resolve()
    report = generate_runtime_environment_ledger(
        execution_loop_plan=load_json(execution_loop_plan_path.resolve()),
        output_dir=resolved_output_dir,
        available_runtime_environments=detect_current_available_runtime_environments(
            explicit_available_runtime_environments=explicit_available_runtime_environments,
            bootstrap_report=bootstrap_report,
            command_version_fn=command_version_fn,
            compose_version_fn=compose_version_fn,
        ),
    )
    write_text(resolved_output_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_text(resolved_output_path.with_suffix(".md"), build_runtime_environment_ledger_markdown(report))
    return report
