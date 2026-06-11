#!/usr/bin/env python3
"""
Build deterministic Phase-3 verification command plans.
"""

from __future__ import annotations

import os
import re
import shlex
from typing import Any

from phase3.validation_levels import build_validation_profile, normalize_validation_level


BACKEND_TARGETED_VITEST_BATCH_SIZE = 16
TARGETED_TEST_CATEGORIES_BY_LANE = {
    "backend": ("sql", "contract", "scenario", "replay"),
    "frontend": ("contract", "scenario", "replay"),
}
MUTATING_CONTRACT_TOKENS = (
    "create",
    "post",
    "submit",
    "update",
    "put",
    "patch",
    "delete",
    "remove",
    "approve",
    "reject",
    "transition",
)
READ_CONTRACT_TOKENS = (
    "list",
    "get",
    "read",
    "find",
    "search",
    "query",
    "retrieve",
    "fetch",
    "overview",
)


def backend_targeted_vitest_batch_size() -> int:
    raw_value = str(os.environ.get("PHASE3_TARGETED_VITEST_BATCH_SIZE", "")).strip()
    if not raw_value:
        return BACKEND_TARGETED_VITEST_BATCH_SIZE
    try:
        parsed = int(raw_value)
    except ValueError:
        return BACKEND_TARGETED_VITEST_BATCH_SIZE
    return parsed if parsed > 0 else BACKEND_TARGETED_VITEST_BATCH_SIZE


def primary_test_categories(lane: str) -> list[str]:
    if lane == "backend":
        return ["sql", "contract", "scenario", "replay", "unit"]
    if lane == "frontend":
        return ["scenario", "replay", "unit"]
    return ["contract", "scenario", "replay", "unit"]


def workspace_scope(lane: str) -> str:
    if lane == "backend":
        return "@app/api"
    if lane == "frontend":
        return "@app/web"
    return "workspace-root"


def quoted_targets(targets: list[str]) -> str:
    return " ".join(shlex.quote(str(target)) for target in targets if str(target).strip())


def environment_bootstrap(workspace_root_hint: str = ".") -> dict[str, str]:
    return {
        "package_manager": "pnpm",
        "bootstrap_command": f"pnpm install --dir {workspace_root_hint} --frozen-lockfile=false",
        "readiness_rule": "Run this before packet verification when node_modules is missing.",
    }


def targeted_test_categories(lane: str) -> tuple[str, ...]:
    return TARGETED_TEST_CATEGORIES_BY_LANE.get(str(lane).strip().lower(), ("contract", "scenario", "replay"))


def unique_test_targets(targets: list[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for raw_target in targets:
        target = str(raw_target).strip()
        if not target or target in seen:
            continue
        selected.append(target)
        seen.add(target)
    return selected


def flatten_targeted_tests(lane: str, test_targets: dict[str, list[str]]) -> list[str]:
    return unique_test_targets(
        [
            target
            for key in targeted_test_categories(lane)
            for target in test_targets.get(key, [])
        ]
    )


def target_matches_any_token(target: str, tokens: tuple[str, ...]) -> bool:
    lowered = str(target).strip().lower()
    return any(re.search(rf"(?:^|[^a-z0-9]){re.escape(token)}(?:[^a-z0-9]|$)", lowered) for token in tokens)


def first_matching_target(targets: list[str], tokens: tuple[str, ...], *, exclude: set[str] | None = None) -> str:
    excluded = exclude or set()
    for target in targets:
        if target in excluded:
            continue
        if target_matches_any_token(target, tokens):
            return target
    return ""


def select_representative_contract_tests(targets: list[str]) -> list[str]:
    normalized = unique_test_targets(targets)
    if len(normalized) <= 1:
        return normalized
    selected: list[str] = []
    mutating = first_matching_target(normalized, MUTATING_CONTRACT_TOKENS)
    if mutating:
        selected.append(mutating)
    read = first_matching_target(normalized, READ_CONTRACT_TOKENS, exclude=set(selected))
    if read:
        selected.append(read)
    if not selected:
        selected.append(normalized[0])
    return unique_test_targets(selected)


def select_critical_targeted_tests(*, lane: str, test_targets: dict[str, list[str]]) -> list[str]:
    selected: list[str] = []
    for key in targeted_test_categories(lane):
        category_targets = unique_test_targets(test_targets.get(key, []))
        if key == "contract":
            selected.extend(select_representative_contract_tests(category_targets))
        elif category_targets:
            selected.append(category_targets[0])
    return unique_test_targets(selected)


def build_verification_commands(
    lane: str,
    test_targets: dict[str, list[str]],
    *,
    validation_level: str = "",
    full_targeted_evidence: bool = True,
) -> dict[str, object]:
    lane_key = str(lane).strip().lower()
    resolved_validation_level = normalize_validation_level(
        validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    validation_profile = build_validation_profile(
        resolved_validation_level,
        full_targeted_evidence=full_targeted_evidence,
    )
    targeted_tests = flatten_targeted_tests(lane_key, test_targets)
    critical_targeted_tests = select_critical_targeted_tests(lane=lane_key, test_targets=test_targets)
    unit_tests = [target for target in test_targets.get("unit", []) if str(target).strip()]
    if lane_key == "backend":
        lint = "pnpm --filter @app/api lint"
        typecheck = "pnpm --filter @app/api typecheck"
        build = "pnpm --filter @app/api build"
    elif lane_key == "frontend":
        lint = "pnpm --filter @app/web lint"
        typecheck = "pnpm --filter @app/web typecheck"
        build = "pnpm --filter @app/web build"
    else:
        lint = "pnpm lint"
        typecheck = "pnpm typecheck"
        build = "pnpm build"

    def vitest_command(report_filename: str, targets: list[str]) -> str:
        command = (
            f'pnpm exec vitest run --config vitest.config.ts --reporter=json --outputFile "$PHASE3_RUN_DIR/{report_filename}"'
        )
        if targets:
            command = f"{command} {quoted_targets(targets)}"
        return command

    def sequential_vitest_command(report_filename: str, targets: list[str], *, batch_size: int = 1) -> str:
        command = (
            "python3 scripts/run_vitest_targets_sequentially.py "
            '--workspace-root . --config vitest.config.ts '
            f'--report-path "$PHASE3_RUN_DIR/{report_filename}"'
        )
        if batch_size > 1:
            command = f"{command} --batch-size {int(batch_size)}"
        for target in targets:
            normalized = str(target).strip()
            if normalized:
                command = f"{command} --target {shlex.quote(normalized)}"
        return command

    sequence = ["lint", "typecheck"]
    commands: dict[str, str] = {
        "lint": lint,
        "typecheck": typecheck,
        "build": build,
    }
    reporting: dict[str, dict[str, str]] = {}

    if targeted_tests:
        if lane_key == "backend":
            backend_batch_size = backend_targeted_vitest_batch_size()
            commands["critical-targeted-tests"] = sequential_vitest_command(
                "critical-targeted-tests.vitest.json",
                critical_targeted_tests,
                batch_size=backend_batch_size,
            )
            commands["full-targeted-tests"] = sequential_vitest_command(
                "full-targeted-tests.vitest.json",
                targeted_tests,
                batch_size=backend_batch_size,
            )
            reporting["critical-targeted-tests"] = {
                "parser": "vitest-json",
                "report_path": "$PHASE3_RUN_DIR/critical-targeted-tests.vitest.json",
                "test_targets": critical_targeted_tests,
            }
            reporting["full-targeted-tests"] = {
                "parser": "vitest-json",
                "report_path": "$PHASE3_RUN_DIR/full-targeted-tests.vitest.json",
                "test_targets": targeted_tests,
            }
            if full_targeted_evidence:
                sequence.append("full-targeted-tests")
            else:
                sequence.append("critical-targeted-tests")
        else:
            sequence.append("targeted-tests")
            commands["targeted-tests"] = vitest_command("targeted-tests.vitest.json", targeted_tests)
            reporting["targeted-tests"] = {
                "parser": "vitest-json",
                "report_path": "$PHASE3_RUN_DIR/targeted-tests.vitest.json",
            }
    if unit_tests:
        sequence.append("unit-tests")
        commands["unit-tests"] = vitest_command("unit-tests.vitest.json", unit_tests)
        reporting["unit-tests"] = {
            "parser": "vitest-json",
            "report_path": "$PHASE3_RUN_DIR/unit-tests.vitest.json",
        }
    sequence.append("build")

    return {
        "workspace_scope": workspace_scope(lane),
        "validation_level": resolved_validation_level,
        "validation_profile": validation_profile,
        "sequence": sequence,
        "commands": commands,
        "reporting": reporting,
        "verification_layers": {
            "build_smoke": {
                "sequence": ["lint", "typecheck", "build"],
                "claim": "toolchain, static analysis, and package build are runnable",
            },
            "critical_runtime": {
                "sequence": ["critical-targeted-tests" if lane_key == "backend" else "targeted-tests"]
                if targeted_tests and not (lane_key == "backend" and full_targeted_evidence)
                else [],
                "test_targets": critical_targeted_tests if lane_key == "backend" else targeted_tests,
                "execution": (
                    "fast-mode-only"
                    if lane_key == "backend" and targeted_tests and full_targeted_evidence
                    else "in-default-sequence"
                ),
                "claim": "bounded runtime proof for service boundary, persistence, and representative business flow",
            },
            "full_evidence": {
                "sequence": ["full-targeted-tests"] if lane_key == "backend" and targeted_tests else (["targeted-tests"] if targeted_tests else []),
                "test_targets": targeted_tests,
                "execution": (
                    "in-default-sequence"
                    if full_targeted_evidence or not (lane_key == "backend" and targeted_tests)
                    else "deferred-by-fast-mode"
                ),
                "claim": "complete generated SQL, contract, scenario, and replay evidence",
            },
        },
        "note": "Frozen interface tests remain primary. Backend strict-runtime runs full-targeted-tests by default; fast/focused validation levels use critical-targeted-tests and require explicit strict full validation before delivery-ready or release-proof claims. All Vitest steps must emit real JSON reports.",
    }
