"""Compatibility classification for pre/post bounded-challenge v1 authority."""

from __future__ import annotations

from typing import Any, Mapping


CURRENT_DECISION_INTEGRITY_CONTRACT = "bounded-challenge-integrity-v1"
LEGACY_DECISION_INTEGRITY_CONTRACT = "legacy-pre-bounded-challenge-v1"


class DecisionIntegrityCompatibilityError(ValueError):
    """Raised when historical proof is used to publish new authority."""


def classify_decision_integrity(decision: Mapping[str, Any]) -> str:
    marker = str(
        decision.get("decision_integrity_contract")
        or LEGACY_DECISION_INTEGRITY_CONTRACT
    )
    challenge = decision.get("bounded_challenge")
    binding = decision.get("challenge_binding")
    if marker == CURRENT_DECISION_INTEGRITY_CONTRACT:
        if isinstance(challenge, Mapping) and isinstance(binding, Mapping):
            return "current-bound-authority"
        return "invalid-integrity-contract"
    if marker == LEGACY_DECISION_INTEGRITY_CONTRACT:
        if challenge is None and binding is None:
            return "legacy-historical-readable"
        return "invalid-integrity-contract"
    return "invalid-integrity-contract"


def classify_authority_integrity(authority: Mapping[str, Any]) -> str:
    marker = str(
        authority.get("decision_integrity_contract")
        or LEGACY_DECISION_INTEGRITY_CONTRACT
    )
    binding_digest = str(authority.get("challenge_binding_digest") or "")
    if marker == CURRENT_DECISION_INTEGRITY_CONTRACT:
        if binding_digest.startswith("sha256:") and len(binding_digest) == 71:
            return "current-bound-authority"
        return "invalid-integrity-contract"
    if marker == LEGACY_DECISION_INTEGRITY_CONTRACT and not binding_digest:
        return "legacy-historical-readable"
    return "invalid-integrity-contract"


def require_current_integrity_pair(
    *,
    decision: Mapping[str, Any],
    authority: Mapping[str, Any],
    label: str,
) -> None:
    if decision.get('decision_integrity_contract') == 'p2-omr-sqr-integrity-v1':
        from common.agentic_decision_authority import canonical_digest
        try:
            if (decision.get('phase_id') != 'P2' or authority.get('phase_id') != 'P2'
                    or authority.get('decision_integrity_contract') != 'p2-omr-sqr-integrity-v1'
                    or authority.get('final_review_digest') != decision['final_review']['content_digest']
                    or authority.get('decision_digest') != decision['content_digest']
                    or decision.get('bounded_challenge') is not None or decision.get('challenge_binding') is not None
                    or authority.get('bounded_challenge') is not None or authority.get('challenge_binding_digest')
                    or authority.get('content_digest') != canonical_digest({k:v for k,v in authority.items() if k!='content_digest'})
                    or decision['content_digest'] != canonical_digest({k:v for k,v in decision.items() if k!='content_digest'})):
                raise ValueError('Final P2 review identity differs')
            from phase2.p2_final_review import validate_acceptance_record
            validate_acceptance_record(decision['final_review'],payload=decision['semantic_payload'])
        except (ValueError, KeyError, TypeError) as exc:
            raise DecisionIntegrityCompatibilityError(str(exc)) from exc
        return
    decision_class = classify_decision_integrity(decision)
    authority_class = classify_authority_integrity(authority)
    if (
        decision_class != "current-bound-authority"
        or authority_class != "current-bound-authority"
    ):
        raise DecisionIntegrityCompatibilityError(
            f"{label} is {decision_class}/{authority_class}; historical legacy proof is readable but cannot publish new current-generation authority"
        )
    binding = decision.get("challenge_binding")
    binding_digest = (
        str(binding.get("content_digest") or "")
        if isinstance(binding, Mapping)
        else ""
    )
    if authority.get("challenge_binding_digest") != binding_digest:
        raise DecisionIntegrityCompatibilityError(
            f"{label} authority does not retain the accepted decision challenge binding"
        )
