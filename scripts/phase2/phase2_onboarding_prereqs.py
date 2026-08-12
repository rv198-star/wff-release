#!/usr/bin/env python3
"""
Helpers for deriving Phase-3 onboarding environment and dependency prerequisites.
"""

from __future__ import annotations

import re


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def block_text(text: str, block_name: str) -> str:
    lines = text.splitlines()
    marker = f"- {block_name}:"
    start = next((index for index, line in enumerate(lines) if line.startswith(marker)), None)
    if start is None:
        return ""
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("## ") or (line.startswith("- ") and not line.startswith("  - ")):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def extract_block_scalar(block: str, field_name: str) -> str:
    nested = re.search(
        rf"{re.escape(field_name)}:\s*\n\s+- `?([^`\n]+)`?",
        block,
        flags=re.IGNORECASE,
    )
    if nested:
        return nested.group(1).strip()
    inline = re.search(
        rf"^\s*- {re.escape(field_name)}:\s*`?([^`\n][^\n`]*)`?\s*$",
        block,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return inline.group(1).strip() if inline else ""


def extract_structured_block(entry: str, field_name: str, *, indent: int = 4) -> str:
    lines = entry.splitlines()
    marker_pattern = re.compile(rf"^(\s*)- {re.escape(field_name)}:\s*(.*)$", flags=re.IGNORECASE)
    start = None
    marker_indent = indent
    remainder = ""
    for index, line in enumerate(lines):
        match = marker_pattern.match(line)
        if match:
            start = index
            marker_indent = len(match.group(1))
            remainder = match.group(2).strip()
            break
    if start is None:
        return ""
    collected = [remainder] if remainder else []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        if current_indent <= marker_indent and stripped.startswith("- "):
            break
        collected.append(stripped.strip("`"))
    return "\n".join(collected)


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
