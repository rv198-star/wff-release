from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase3.surface_policy import write_phase3_profiled_surface


PHASE3_TIMING_SEGMENT_NAMES = (
    "generation",
    "toolchain_install",
    "mainline_backend_verification",
    "coverage_collection",
    "runtime_smoke",
    "delivery_gate",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def start_timer() -> float:
    return time.monotonic()


def set_timing_segment(
    segments: dict[str, dict[str, Any]],
    name: str,
    *,
    duration_seconds: float | str,
    status: str = "recorded",
    **extra: Any,
) -> None:
    payload: dict[str, Any] = {
        "duration_seconds": duration_seconds,
        "status": status,
    }
    payload.update(extra)
    segments[name] = payload


def record_timing_segment(
    segments: dict[str, dict[str, Any]],
    name: str,
    started_monotonic: float,
    *,
    status: str = "recorded",
    **extra: Any,
) -> None:
    set_timing_segment(
        segments,
        name,
        duration_seconds=round(max(0.0, time.monotonic() - started_monotonic), 3),
        status=status,
        **extra,
    )


def normalized_phase3_timing_segments(segments: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for name in PHASE3_TIMING_SEGMENT_NAMES:
        raw = segments.get(name)
        if isinstance(raw, dict) and "duration_seconds" in raw:
            normalized[name] = dict(raw)
        else:
            normalized[name] = {
                "duration_seconds": "not-recorded",
                "status": "not-recorded",
            }
    return normalized


def write_phase3_timing_report(
    *,
    output_dir: Path,
    segments: dict[str, Any],
) -> Path:
    report = {
        "generated_at": utc_now_iso(),
        "segments": normalized_phase3_timing_segments(segments),
    }
    return write_phase3_profiled_surface(
        output_dir.resolve(),
        "phase3-timing-report.json",
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
