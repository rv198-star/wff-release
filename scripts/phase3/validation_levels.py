from __future__ import annotations

from typing import Any


VALIDATION_LEVEL_CHOICES = ("fast", "focused", "strict")


def normalize_validation_level(
    value: object = "",
    *,
    full_targeted_evidence: bool | None = None,
) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return "fast" if full_targeted_evidence is False else "strict"
    if normalized not in VALIDATION_LEVEL_CHOICES:
        raise ValueError(f"unknown validation level: {normalized}")
    return normalized


def full_targeted_evidence_for_validation_level(level: object) -> bool:
    return normalize_validation_level(level) == "strict"


def build_validation_profile(
    level: object = "",
    *,
    full_targeted_evidence: bool | None = None,
) -> dict[str, Any]:
    normalized = normalize_validation_level(level, full_targeted_evidence=full_targeted_evidence)
    full_evidence = full_targeted_evidence_for_validation_level(normalized) if full_targeted_evidence is None else bool(full_targeted_evidence)
    if normalized == "strict" and not full_evidence:
        raise ValueError("strict validation level requires full targeted evidence")
    if normalized in {"fast", "focused"} and full_evidence:
        raise ValueError(f"{normalized} validation level cannot run as full targeted evidence")

    if normalized == "strict":
        return {
            "level": "strict",
            "full_targeted_evidence": True,
            "runs_full_targeted_tests": True,
            "full_targeted_followup_required": False,
            "claim_ceiling": (
                "full-targeted backend evidence path; delivery-ready or release-proof claims still require "
                "runtime smoke, started-service smoke, and delivery gates"
            ),
            "next_step": "complete runtime smoke, started-service smoke, and delivery gates before delivery-ready or release-proof claims",
            "user_prompt_key": "strict_full_validation_completed",
        }

    if normalized == "focused":
        return {
            "level": "focused",
            "full_targeted_evidence": False,
            "runs_full_targeted_tests": False,
            "full_targeted_followup_required": True,
            "claim_ceiling": (
                "focused validation profile using bounded critical runtime sampling; "
                "cannot claim delivery-ready or release-proof closure"
            ),
            "next_step": "ask whether to continue with strict full validation before any delivery-ready or release-proof claim",
            "user_prompt_key": "focused_validation_full_followup_required",
        }

    return {
        "level": "fast",
        "full_targeted_evidence": False,
        "runs_full_targeted_tests": False,
        "full_targeted_followup_required": True,
        "claim_ceiling": "fast critical-path validation only; cannot claim delivery-ready or release-proof closure",
        "next_step": "ask whether to continue with strict full validation before any delivery-ready or release-proof claim",
        "user_prompt_key": "fast_validation_full_followup_required",
    }
