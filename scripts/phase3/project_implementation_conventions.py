#!/usr/bin/env python3
"""Synthesize in-memory Phase-3 project implementation conventions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


CONVENTION_KIND = "phase3-project-implementation-conventions.v1"


def _listish(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [part for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def _upper_camel(value: str) -> str:
    return "".join(word[:1].upper() + word[1:].lower() for word in _words(value))


def _aggregate_from_domain_name(value: str) -> str:
    name = _upper_camel(value)
    for suffix in ("Review", "Workflow", "Service", "Manager"):
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _source_status(value: Any) -> str:
    return "present" if value else "missing"


def _stack_summary(tech_stack_decision: dict[str, Any]) -> dict[str, str]:
    return {
        "backend_framework": _text(tech_stack_decision.get("backend_framework") or tech_stack_decision.get("backendFramework")),
        "language": _text(tech_stack_decision.get("language")),
        "orm": _text(tech_stack_decision.get("orm")),
        "test_runner": _text(tech_stack_decision.get("test_runner") or tech_stack_decision.get("testRunner")),
        "frontend_framework": _text(tech_stack_decision.get("frontend_framework") or tech_stack_decision.get("frontendFramework")),
    }


def parse_stack_decision_text(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    section = ""
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            section = line[:-1].strip()
            continue
        match = re.match(r"\s+([A-Za-z0-9_]+):\s*(.+?)\s*$", line)
        if not match:
            continue
        key = match.group(1)
        value = match.group(2).strip().strip('"')
        if section == "runtime":
            if key == "backend_language":
                result["language"] = value
            elif key in {"backend_framework", "frontend_framework"}:
                result[key] = value
        elif section == "storage" and key == "primary_database":
            result["orm"] = value
    return result


def _component_naming(component_responsibilities: list[Any]) -> tuple[dict[str, str], dict[str, str], list[str]]:
    domain_services: dict[str, str] = {}
    aggregates: dict[str, str] = {}
    forbidden: list[str] = []
    for item in component_responsibilities:
        if not isinstance(item, dict):
            continue
        component_id = _text(item.get("component_id"))
        preferred = _text(item.get("preferred_domain_name"))
        if component_id and preferred:
            domain_name = _upper_camel(preferred)
            domain_services[component_id] = f"{domain_name}Service"
            aggregates[component_id] = _aggregate_from_domain_name(domain_name)
        for name in _listish(item.get("forbidden_names")):
            text = _text(name)
            if text and text not in forbidden:
                forbidden.append(text)
    return domain_services, aggregates, forbidden


def _ui_conventions(
    *,
    handoff_ui: dict[str, Any],
    frontend_surface_context: dict[str, Any] | None,
    stack: dict[str, str],
) -> dict[str, Any]:
    surface_declared = bool(handoff_ui.get("applicable")) or bool(frontend_surface_context)
    if not surface_declared:
        return {
            "applicable": False,
            "reason": "no frontend/UI surface declared",
        }
    return {
        "applicable": True,
        "surface_posture": _text(handoff_ui.get("surface_posture")) or "operator workflow",
        "component_naming": "Use domain task names, not endpoint or component ids.",
        "states": ["loading", "empty", "validation-error", "permission-denied", "audit-visible-success"],
        "frontend_code_style": (
            f"Use {stack['frontend_framework']} conventions with source-backed domain component names."
            if stack.get("frontend_framework")
            else "Use selected frontend stack conventions with source-backed domain component names."
        ),
    }


def mechanical_residue_metrics(text: str) -> dict[str, int]:
    owner_matches = re.findall(r"P2CMP[0-9]+Service", text)
    aggregate_matches = re.findall(r"\bP2CMP[0-9]+\b", text)
    return {
        "mechanical_owner_name_count": len(owner_matches),
        "mechanical_aggregate_name_count": len(aggregate_matches),
        "forbidden_name_residue_count": len(owner_matches) + len(aggregate_matches),
    }


def synthesize_project_implementation_conventions(
    *,
    p2_language_handoff: dict[str, Any] | None,
    tech_stack_decision: dict[str, Any] | None,
    action_card_context: dict[str, Any] | None,
    frontend_surface_context: dict[str, Any] | None = None,
    output_root: Path | None = None,
    persist_default: bool = False,
) -> dict[str, Any]:
    del output_root, persist_default
    handoff = p2_language_handoff if isinstance(p2_language_handoff, dict) else {}
    stack = _stack_summary(tech_stack_decision or {})
    domain_services, aggregates, forbidden_names = _component_naming(_listish(handoff.get("component_responsibilities")))
    forbidden_patterns = ["P2CMP*Service", "P2CMP*"]
    handoff_ui = handoff.get("ui_ux_intent") if isinstance(handoff.get("ui_ux_intent"), dict) else {}
    residue_metrics = mechanical_residue_metrics(str(action_card_context or ""))
    drift_count = residue_metrics["forbidden_name_residue_count"]

    return {
        "artifact_kind": CONVENTION_KIND,
        "mode": "in-memory-before-semantic-decisions",
        "source_inputs": {
            "p2_language_handoff": _source_status(p2_language_handoff),
            "tech_stack_decision": _source_status(tech_stack_decision),
            "action_cards": _source_status(action_card_context),
        },
        "naming_conventions": {
            "domain_service": "Use source-backed P2 domain responsibility names; never use P2CMP ids as final owner names.",
            "aggregate": "Prefer P2 aggregate candidates or domain object names; keep gaps review-bound instead of inventing unsupported terms.",
            "repository": "Name repositories after persisted aggregate boundaries.",
            "tests": "Name test units after behavior intent, not component id.",
            "domain_services": domain_services,
            "aggregates": aggregates,
            "forbidden_names": sorted(set(forbidden_names)),
            "forbidden_final_owner_patterns": forbidden_patterns,
        },
        "code_conventions": {
            "service_boundary": "Service owns orchestration, invariant checks, failure mapping, and selected stack transaction posture.",
            "repository_boundary": "Repository owns persistence effects and read/write separation.",
            "selected_stack": {key: value for key, value in stack.items() if value},
        },
        "design_conventions": {
            "read_path": "Read/list/detail operations must preserve no-mutation posture.",
            "write_path": "Command operations must make invariant and value-rule checks explicit before persistence.",
            "failure_path": "Failure paths must be named and testable.",
        },
        "ui_ux_conventions": _ui_conventions(
            handoff_ui=handoff_ui,
            frontend_surface_context=frontend_surface_context,
            stack=stack,
        ),
        "summary": {
            "component_convention_count": len(domain_services),
            "missing_language_gap_count": len(_listish(handoff.get("missing_language_gaps"))),
            **residue_metrics,
            "naming_convention_drift_count": drift_count,
            "code_convention_drift_count": 0,
            "design_convention_drift_count": 0,
            "ui_ux_convention_applicability": "applicable"
            if _ui_conventions(
                handoff_ui=handoff_ui,
                frontend_surface_context=frontend_surface_context,
                stack=stack,
            ).get("applicable")
            else "not-applicable",
            "default_heavy_artifact_count": 0,
        },
        "claim_ceiling": "conventions guide generation; strict-runtime and human Review decide quality claims",
    }
