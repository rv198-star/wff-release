#!/usr/bin/env python3
"""Data-backed Phase-2 stage quality gate specifications."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Callable

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.script_data_assets import load_script_json_asset


WFF_SCRIPT_DATA_ASSETS = (
    "scripts/phase2/data/phase2-quality-gate-specs.json",
    "scripts/phase2/data/phase2-quality-check-rules.json",
)


_PHASE2_QUALITY_CHECK_RULES = load_script_json_asset(__file__, "phase2-quality-check-rules.json")

COMPLEXITY_PROFILES = tuple(str(profile) for profile in _PHASE2_QUALITY_CHECK_RULES.get("complexity_profiles", ()))
PROFILE_MINIMUMS = {
    str(profile): {str(key): int(value) for key, value in minimums.items()}
    for profile, minimums in _PHASE2_QUALITY_CHECK_RULES.get("profile_minimums", {}).items()
    if isinstance(minimums, dict)
}


def normalized_complexity_profile(value: str) -> str:
    return value if value in COMPLEXITY_PROFILES else "standard"


def profile_minimum(complexity_profile: str, key: str) -> int:
    profile = normalized_complexity_profile(complexity_profile)
    return int(PROFILE_MINIMUMS.get(profile, PROFILE_MINIMUMS["standard"]).get(key, PROFILE_MINIMUMS["standard"][key]))


def load_stage_gate_specs() -> dict[str, list[dict[str, Any]]]:
    loaded = load_script_json_asset(__file__, "phase2-quality-gate-specs.json")
    if not isinstance(loaded, dict):
        return {}
    specs: dict[str, list[dict[str, Any]]] = {}
    for stage_key, entries in loaded.items():
        if not isinstance(entries, list):
            continue
        specs[str(stage_key)] = [dict(entry) for entry in entries if isinstance(entry, dict)]
    return specs


def _metric_value(metrics: dict[str, Any], key: str) -> int:
    return int(metrics.get(key, 0) or 0)


def _resolve_number(
    expression: Any,
    metrics: dict[str, Any],
    *,
    complexity_profile: str,
    profile_minimum: Callable[[str, str], int],
) -> int:
    if isinstance(expression, bool):
        return int(expression)
    if isinstance(expression, int):
        return expression
    if isinstance(expression, str):
        return _metric_value(metrics, expression)
    if not isinstance(expression, dict):
        return 0
    if "metric" in expression:
        return _metric_value(metrics, str(expression["metric"]))
    if "profile" in expression:
        return int(profile_minimum(complexity_profile, str(expression["profile"])))
    if "max" in expression and isinstance(expression["max"], list):
        return max(
            (
                _resolve_number(
                    item,
                    metrics,
                    complexity_profile=complexity_profile,
                    profile_minimum=profile_minimum,
                )
                for item in expression["max"]
            ),
            default=0,
        )
    if "metric_gt" in expression:
        metric_key, floor = expression["metric_gt"]
        return int(_metric_value(metrics, str(metric_key)) > int(floor))
    if "metric_gte" in expression:
        metric_key, threshold = expression["metric_gte"]
        return int(
            _metric_value(metrics, str(metric_key))
            >= _resolve_number(
                threshold,
                metrics,
                complexity_profile=complexity_profile,
                profile_minimum=profile_minimum,
            )
        )
    if "metric_eq_metric" in expression:
        left, right = expression["metric_eq_metric"]
        return int(_metric_value(metrics, str(left)) == _metric_value(metrics, str(right)))
    if "all" in expression and isinstance(expression["all"], list):
        return int(
            all(
                _resolve_number(
                    item,
                    metrics,
                    complexity_profile=complexity_profile,
                    profile_minimum=profile_minimum,
                )
                for item in expression["all"]
            )
        )
    return 0


def evaluate_stage_gate_specs(
    specs: list[dict[str, Any]],
    metrics: dict[str, Any],
    *,
    complexity_profile: str,
    profile_minimum: Callable[[str, str], int],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for spec in specs:
        current = _resolve_number(
            spec.get("current"),
            metrics,
            complexity_profile=complexity_profile,
            profile_minimum=profile_minimum,
        )
        minimum = _resolve_number(
            spec.get("minimum", 1),
            metrics,
            complexity_profile=complexity_profile,
            profile_minimum=profile_minimum,
        )
        checks.append(
            {
                "name": str(spec.get("name", "")),
                "current": current,
                "minimum": minimum,
                "passed": current >= minimum,
                "evidence": str(spec.get("evidence", "")),
            }
        )
    return checks
