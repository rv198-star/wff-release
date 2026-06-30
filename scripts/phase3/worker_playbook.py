#!/usr/bin/env python3
"""
Build deterministic Phase-3 worker implementation playbooks.
"""

from __future__ import annotations

from typing import Any

from phase3.contract_tools import slugify as contract_slugify


def lane_skill_hint(lane: str) -> str:
    if lane == "backend":
        return "wff-impl-backend"
    if lane == "frontend":
        return "wff-impl-frontend"
    return "wff-impl"


def slugify(value: str) -> str:
    return contract_slugify(value) or "module"


def build_backend_playbook(
    *,
    contract_operations: list[dict[str, Any]],
    implementation_targets: list[str],
    test_targets: dict[str, list[str]],
) -> dict[str, Any]:
    controller_targets = [target for target in implementation_targets if target.endswith(".controller.ts")]
    service_targets = [target for target in implementation_targets if target.endswith(".service.ts")]
    mappings: list[dict[str, str]] = []
    for operation in contract_operations:
        operation_id = str(operation.get("operation_id", "")).strip()
        method = str(operation.get("method", "")).strip().upper()
        path = str(operation.get("path", "")).strip()
        module_slug = slugify(str(operation.get("tag", "")).strip() or operation_id or path)
        controller_target = next(
            (
                target
                for target in controller_targets
                if f"/{module_slug}/" in target or target.endswith(f"/{module_slug}.controller.ts")
            ),
            controller_targets[0] if len(controller_targets) == 1 else "",
        )
        service_target = next(
            (
                target
                for target in service_targets
                if f"/{module_slug}/" in target or target.endswith(f"/{module_slug}.service.ts")
            ),
            service_targets[0] if len(service_targets) == 1 else "",
        )
        repository_target = f"apps/api/src/modules/{module_slug}/{module_slug}.repository.ts"
        mappings.append(
            {
                "operation_id": operation_id,
                "http_surface": f"{method} {path}".strip(),
                "controller_target": controller_target,
                "service_target": service_target,
                "repository_target": repository_target,
            }
        )

    return {
        "contract_to_code_map": mappings,
        "implementation_steps": [
            "Freeze the contract first: do not edit OpenAPI, shared types, or migrations from inside the worker packet.",
            "For each assigned operation, implement controller input/output mapping first, then the service method, then any repository or adapter boundary the service needs.",
            "After each operation or thin vertical slice, run the targeted contract tests before broadening into scenario or replay coverage.",
            "Only move to scenario/replay fixes after the relevant contract tests for the slice are green.",
        ],
        "test_sequence": [
            *([f"sql: {item}" for item in test_targets.get("sql", [])]),
            *([f"contract: {item}" for item in test_targets.get("contract", [])]),
            *([f"scenario: {item}" for item in test_targets.get("scenario", [])]),
            *([f"replay: {item}" for item in test_targets.get("replay", [])]),
            *([f"unit: {item}" for item in test_targets.get("unit", [])]),
        ],
    }


def build_frontend_playbook(
    *,
    frontend_surfaces: list[str],
    frontend_surface_designs: list[dict[str, Any]],
    prototype_constraints: dict[str, str],
    external_executor_brief: list[str],
    semantic_disqualifiers: list[str],
    test_targets: dict[str, list[str]],
) -> dict[str, Any]:
    return {
        "surface_sequence": frontend_surfaces,
        "surface_implementation_designs": frontend_surface_designs,
        "prototype_constraints": prototype_constraints,
        "external_executor_brief": external_executor_brief,
        "semantic_disqualifiers": semantic_disqualifiers,
        "implementation_steps": [
            "Translate each assigned prototype surface into a page-specific implementation design before coding.",
            "Choose the interaction pattern, visible business-state transitions, validation rules, and information hierarchy that match the page's business function.",
            "Do not build or reuse a generic renderer that maps JSON section metadata into UI templates across distinct page types.",
            "Start from the frozen API client and shared types only after the page-specific implementation design is clear; do not hand-roll public HTTP calls.",
            "Implement loading, success, empty, denied, and error states explicitly before visual polish.",
            "Reflect business-state transitions as UI changes after actions complete; do not stop at transport-level success or raw response rendering.",
            "Keep each scenario surface aligned to the assigned replay/scenario tests and only widen scope after the targeted scenario tests are green.",
        ],
        "test_sequence": [
            *([f"scenario: {item}" for item in test_targets.get("scenario", [])]),
            *([f"replay: {item}" for item in test_targets.get("replay", [])]),
            *([f"unit: {item}" for item in test_targets.get("unit", [])]),
        ],
    }


def build_platform_playbook(test_targets: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "implementation_steps": [
            "Use the platform lane for cross-cutting concerns only: CI, shared infra, or shared tooling.",
            "Do not absorb backend/frontend business logic into platform targets.",
        ],
        "test_sequence": [
            *([f"contract: {item}" for item in test_targets.get("contract", [])]),
            *([f"scenario: {item}" for item in test_targets.get("scenario", [])]),
            *([f"replay: {item}" for item in test_targets.get("replay", [])]),
            *([f"unit: {item}" for item in test_targets.get("unit", [])]),
        ],
    }
