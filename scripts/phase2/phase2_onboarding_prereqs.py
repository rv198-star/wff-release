#!/usr/bin/env python3
"""
Helpers for deriving Phase-3 onboarding environment and dependency prerequisites.
"""

from __future__ import annotations

from phase2.phase2_quality_check import (
    block_text,
    extract_block_scalar,
    extract_structured_block,
    normalize_text,
)


def bullet_items_from_block(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        item = normalize_text(stripped[2:].strip("`"))
        if item and item not in items:
            items.append(item)
    return items


def format_nested_bullets(items: list[str], *, indent: int = 2, fallback: str = "missing") -> str:
    prefix = " " * indent + "- "
    if not items:
        return f"{prefix}{fallback}"
    return "\n".join(f"{prefix}{item}" for item in items)


def derive_environment_dependency_prerequisites(stage_03_text: str, stage_02_5_text: str = "") -> list[str]:
    tech_stack_block = block_text(stage_03_text, "technology_stack_and_deployment_assumptions")
    security_block = block_text(stage_03_text, "security_architecture_outline")
    activation_block = block_text(stage_02_5_text, "activation_decision") if stage_02_5_text else ""

    api_runtime = normalize_text(extract_block_scalar(tech_stack_block, "api_runtime"))
    primary_storage = normalize_text(extract_block_scalar(tech_stack_block, "primary_storage"))
    cache = normalize_text(extract_block_scalar(tech_stack_block, "cache"))
    queue_posture = normalize_text(extract_block_scalar(tech_stack_block, "queue_posture"))
    stage_02_5_status = normalize_text(extract_block_scalar(activation_block, "stage_status")).lower()
    key_management_items = bullet_items_from_block(
        extract_structured_block(security_block, "key_management_posture", indent=2)
    )

    items: list[str] = []
    if api_runtime:
        items.append(f"Keep the Stage-03 runtime baseline at `{api_runtime}` for backend and shared-contract slices.")
    if primary_storage:
        items.append(f"Provision `{primary_storage}` as the authoritative workflow store before implementing persistence-backed slices.")
    if cache:
        items.append(
            f"Treat the Stage-03 cache posture (`{cache}`) as bounded-read acceleration only; implementation must remain correct if the cache is bypassed or unavailable."
        )
    if queue_posture:
        items.append(
            f"Keep the Stage-03 queue posture (`{queue_posture}`) only on the slices it names; do not replace it with ad hoc in-process shortcuts."
        )
    if key_management_items:
        items.append(
            "Keep key and secret handling aligned with Stage-03 security posture: "
            + "; ".join(key_management_items)
            + "."
        )
    if stage_02_5_status == "skipped":
        items.append(
            "Do not bind a vendor-specific SDK, OAuth/OIDC mapping, callback contract, timeout budget, or mock/sandbox workflow until Stage-02.5 is re-entered with a named provider or external dependency contract."
        )

    return items
