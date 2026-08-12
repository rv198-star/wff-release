"""Small explicit trigger/exclusion policy for bounded Agentic challenge.

The policy accepts only phase-owned identifiers. It does not infer risk from
keywords, artifact size, confidence, model output, or finding volume.
"""

from __future__ import annotations


PHASE_TRIGGER_MATRIX: dict[str, frozenset[str]] = {
    "P1": frozenset({
        "product-world-sufficiency",
        "cross-phase-commitment",
        "candidate-world-semantics",
    }),
    "P2": frozenset({
        "architecture-ownership",
        "contract-operation-identity",
        "dependency-compatibility",
        "cross-phase-disposition",
    }),
    "P3": frozenset({
        "implementation-invariant",
        "irreversible-migration",
        "exact-realization",
    }),
    "P4": frozenset({
        "agentic-claim-ceiling",
        "unresolved-risk-closure",
    }),
    "PX": frozenset({
        "brownfield-authority-boundary",
        "cross-phase-return",
    }),
    "PRE-P1": frozenset({"source-admission"}),
}

DEFAULT_EXCLUSIONS = frozenset({
    "evidence-read-or-summary",
    "formatting-or-rename",
    "deterministic-identity-schema-package-check",
    "unambiguous-user-instruction",
    "low-risk-directly-tested-change",
    "tool-or-test-rerun-without-new-decision",
})


class BoundedChallengePolicyError(ValueError):
    """Raised when Workflow supplies an unknown trigger or exclusion ID."""


def challenge_required(*, phase_id: str, trigger_id: str, exclusion_id: str = "") -> bool:
    phase = str(phase_id or "").strip().upper()
    trigger = str(trigger_id or "").strip()
    exclusion = str(exclusion_id or "").strip()
    if exclusion:
        if exclusion not in DEFAULT_EXCLUSIONS:
            raise BoundedChallengePolicyError(
                f"unknown bounded-challenge exclusion: {exclusion}"
            )
        return False
    if trigger not in PHASE_TRIGGER_MATRIX.get(phase, frozenset()):
        raise BoundedChallengePolicyError(
            f"unknown bounded-challenge trigger for {phase}: {trigger}"
        )
    return True
