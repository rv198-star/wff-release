#!/usr/bin/env python3
"""
Phase-3 delivery-gate mode authority metadata.
"""

from __future__ import annotations

from typing import Any


CLI_MODES = (
    "delivery-gate",
    "delivery-handoff",
    "productness-gate",
    "api-docs",
    "code-review",
    "security-audit",
    "coverage-collection",
)


PHASE3_MODE_AUTHORITY: dict[str, dict[str, Any]] = {
    "delivery-gate": {
        "mode": "delivery-gate",
        "validation_profile": "phase",
        "blocking_scope": "formal P3 delivery-gate closure for the supplied implementation package",
        "formal_p3_closure_authority": True,
        "claim_ceiling": "P3 delivery evidence for the supplied package under selected runtime/strictness settings",
    },
    "delivery-handoff": {
        "mode": "delivery-handoff",
        "validation_profile": "focused",
        "blocking_scope": "handoff artifact generation/support when selected",
        "formal_p3_closure_authority": False,
        "claim_ceiling": "handoff artifact support only; not full P3 closure",
    },
    "productness-gate": {
        "mode": "productness-gate",
        "validation_profile": "phase",
        "blocking_scope": "frontend/productness contract evidence when selected or required",
        "formal_p3_closure_authority": False,
        "claim_ceiling": "frontend/productness contract evidence only; not full P3 closure",
    },
    "api-docs": {
        "mode": "api-docs",
        "validation_profile": "focused",
        "blocking_scope": "API documentation generation/support when selected",
        "formal_p3_closure_authority": False,
        "claim_ceiling": "API documentation support only; not full P3 closure",
    },
    "code-review": {
        "mode": "code-review",
        "validation_profile": "focused",
        "blocking_scope": "selected code-review evidence; blocks selected mode on severe findings",
        "formal_p3_closure_authority": False,
        "claim_ceiling": "code-review evidence only; not full P3 closure",
    },
    "security-audit": {
        "mode": "security-audit",
        "validation_profile": "focused",
        "blocking_scope": "selected security-audit evidence; blocks selected mode on critical/high findings",
        "formal_p3_closure_authority": False,
        "claim_ceiling": "security-audit evidence only; not full P3 closure or production risk acceptance",
    },
    "coverage-collection": {
        "mode": "coverage-collection",
        "validation_profile": "focused",
        "blocking_scope": "coverage evidence collection when selected",
        "formal_p3_closure_authority": False,
        "claim_ceiling": "coverage evidence support only; not full P3 closure",
    },
}


def phase3_mode_authority_map() -> dict[str, dict[str, Any]]:
    return {mode: dict(authority) for mode, authority in PHASE3_MODE_AUTHORITY.items()}


def phase3_mode_authority(mode: str) -> dict[str, Any]:
    normalized = str(mode or "").strip() or "delivery-gate"
    try:
        return dict(PHASE3_MODE_AUTHORITY[normalized])
    except KeyError as exc:
        known = ", ".join(CLI_MODES)
        raise SystemExit(f"Unknown Phase-3 delivery gate mode '{normalized}'. Known modes: {known}") from exc


def decorate_phase3_mode_payload(payload: dict[str, Any], mode: str) -> dict[str, Any]:
    decorated = dict(payload)
    decorated.setdefault("mode_authority", phase3_mode_authority(mode))
    return decorated
