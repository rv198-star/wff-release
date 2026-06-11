from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def resolve_wp_gate_report_path(output_dir: Path, wp_gate_report_path: Path | None) -> Path | None:
    if wp_gate_report_path is not None:
        return wp_gate_report_path.resolve()
    candidate = output_dir / "phase3-wp-gate.json"
    return candidate if candidate.exists() else None


def current_runtime_row(runtime_state: dict[str, Any], packet: str) -> dict[str, Any] | None:
    rows = runtime_state.get("rows", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("packet_id", "")).strip() == packet:
            return row
    return None


def execution_loop_row(execution_loop_plan: dict[str, Any], packet: str) -> dict[str, Any]:
    for wave in execution_loop_plan.get("waves", []):
        if not isinstance(wave, dict):
            continue
        wave_number = int(wave.get("wave", 0) or 0)
        for row in wave.get("worker_packets", []):
            if not isinstance(row, dict):
                continue
            candidate = f"wave-{wave_number:02d}:{str(row.get('lane', '')).strip()}"
            if candidate == packet:
                return {"packet_id": candidate, **row}
    raise ValueError(f"unknown packet_id: {packet}")


def load_worker_packet_document(output_dir: Path, loop_row: dict[str, Any]) -> dict[str, Any]:
    packet_ref = str(loop_row.get("packet_json", "")).strip()
    if not packet_ref:
        raise ValueError(f"packet_json missing for {loop_row.get('packet_id', 'unknown')}")
    packet_path = output_dir / packet_ref
    if not packet_path.exists():
        raise ValueError(f"worker packet missing: {packet_path}")
    packet_document = load_json(packet_path)
    packet_document.setdefault("packet_id", str(loop_row.get("packet_id", "")).strip())
    return packet_document


def requires_toolchain_bootstrap(command: str) -> bool:
    normalized = command.strip()
    return (
        "pnpm " in normalized
        or normalized.startswith("pnpm")
        or "run_vitest_targets_sequentially.py" in normalized
    )
