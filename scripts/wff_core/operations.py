"""The nine public structural operations of WFF Core contract 1.0.0."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .errors import ContractValidationError, ExtensionRegistrationError
from .models import (
    AdmissionDisposition,
    ArtifactBinding,
    ArtifactRef,
    ClaimState,
    ControlOwnership,
    EntryKind,
    EvidenceRef,
    HandoffDecision,
    HandoffPacket,
    KnowledgeState,
    PhaseAdmission,
    PhaseDescriptor,
    ReturnReentryMode,
    ReturnReentryPacket,
    RouteDisposition,
    RouteRequest,
    RouteResolution,
    UnresolvedStatus,
    ExtensionDescriptor,
)
from .registry import ExtensionRegistry


def resolve_route(
    request: RouteRequest,
    descriptors: Iterable[ExtensionDescriptor],
) -> RouteResolution:
    """Resolve one route request against declarative descriptors.

    Registry storage and indexes remain internal. The public operation consumes
    the P1-declared RouteRequest and ExtensionDescriptor types only.
    """
    if not isinstance(request, RouteRequest):
        raise ContractValidationError("resolve_route requires a RouteRequest")
    registry = ExtensionRegistry()
    try:
        registry.register_many(tuple(descriptors))
    except TypeError as exc:
        raise ContractValidationError(
            "resolve_route descriptors must be an iterable of ExtensionDescriptor values"
        ) from exc
    except ExtensionRegistrationError as exc:
        return RouteResolution(
            request_id=request.request_id,
            disposition=RouteDisposition.BLOCKED,
            reason=f"Declarative extension registry is invalid: {exc}",
        )
    descriptor = registry.descriptor_for_route(request.intent_key)
    if descriptor is None:
        return RouteResolution(
            request_id=request.request_id,
            disposition=RouteDisposition.UNREGISTERED,
            reason=(
                f"No declarative extension route is registered for {request.intent_key!r}; "
                "Core does not guess a capability."
            ),
        )
    return RouteResolution(
        request_id=request.request_id,
        disposition=RouteDisposition.RESOLVED,
        extension_id=descriptor.extension_id,
        reason="Resolved from the validated declarative extension registry snapshot.",
    )


def _handoff_disposition(packet: HandoffPacket) -> tuple[AdmissionDisposition, str]:
    statuses = {item.status for item in packet.unresolved_items}
    if packet.decision is HandoffDecision.BLOCKED or UnresolvedStatus.BLOCKED in statuses:
        return AdmissionDisposition.BLOCKED, "The handoff is explicitly blocked."
    if packet.decision is HandoffDecision.RETURN or UnresolvedStatus.CONFLICT in statuses:
        return AdmissionDisposition.RETURN, "The handoff requires bounded upstream return."
    if (
        packet.decision is HandoffDecision.CONTINUE_REVIEW_BOUND
        or statuses
        & {
            UnresolvedStatus.PROVISIONAL,
            UnresolvedStatus.REVIEW_BOUND,
            UnresolvedStatus.UNKNOWN,
        }
    ):
        return (
            AdmissionDisposition.ADMIT_REVIEW_BOUND,
            "The handoff may continue only while unresolved items remain explicit.",
        )
    return AdmissionDisposition.ADMIT, "The handoff envelope permits normal continuation."


def validate_handoff_envelope(packet: HandoffPacket) -> PhaseAdmission:
    """Validate structural handoff state without judging artifact semantics."""
    if not isinstance(packet, HandoffPacket):
        raise ContractValidationError(
            "validate_handoff_envelope requires a HandoffPacket"
        )
    disposition, reason = _handoff_disposition(packet)
    return PhaseAdmission(
        phase_id=packet.to_phase_id,
        disposition=disposition,
        input_refs=packet.artifact_refs,
        semantic_judgment_owner=f"{packet.to_phase_id} capability owner",
        reason=reason,
    )


def evaluate_phase_admission(
    descriptor: PhaseDescriptor,
    packet: HandoffPacket,
) -> PhaseAdmission:
    """Apply structural phase requirements, preserving extension-owned judgment."""
    if not isinstance(descriptor, PhaseDescriptor):
        raise ContractValidationError(
            "evaluate_phase_admission requires a PhaseDescriptor"
        )
    if not isinstance(packet, HandoffPacket):
        raise ContractValidationError(
            "evaluate_phase_admission requires a HandoffPacket"
        )
    if packet.to_phase_id != descriptor.phase_id:
        return PhaseAdmission(
            phase_id=descriptor.phase_id,
            disposition=AdmissionDisposition.BLOCKED,
            input_refs=packet.artifact_refs,
            semantic_judgment_owner=descriptor.truth_owner,
            reason=(
                f"Handoff target {packet.to_phase_id!r} does not match phase "
                f"{descriptor.phase_id!r}."
            ),
        )
    available_contracts = {artifact.artifact_type for artifact in packet.artifact_refs}
    missing = sorted(set(descriptor.required_input_contracts) - available_contracts)
    if missing:
        return PhaseAdmission(
            phase_id=descriptor.phase_id,
            disposition=AdmissionDisposition.BLOCKED,
            input_refs=packet.artifact_refs,
            semantic_judgment_owner=descriptor.truth_owner,
            reason=(
                "Required structural input contracts are missing: "
                + ", ".join(missing)
                + ". Core does not infer the missing truth."
            ),
        )
    envelope = validate_handoff_envelope(packet)
    return PhaseAdmission(
        phase_id=descriptor.phase_id,
        disposition=envelope.disposition,
        input_refs=packet.artifact_refs,
        semantic_judgment_owner=descriptor.truth_owner,
        reason=(
            envelope.reason
            + " Semantic sufficiency remains the responsibility of the declared truth owner."
        ),
    )


def bind_artifact(
    artifact: ArtifactRef,
    binding: ArtifactBinding,
) -> ArtifactBinding:
    """Accept a storage-neutral binding when subject identity is consistent."""
    if not isinstance(artifact, ArtifactRef) or not isinstance(
        binding, ArtifactBinding
    ):
        raise ContractValidationError(
            "bind_artifact requires ArtifactRef and ArtifactBinding values"
        )
    if binding.subject_artifact_id != artifact.artifact_id:
        raise ContractValidationError(
            "artifact binding subject does not match the supplied artifact identity"
        )
    return binding


def record_evidence(evidence: EvidenceRef) -> EvidenceRef:
    """Return a validated evidence record without upgrading its knowledge state."""
    if not isinstance(evidence, EvidenceRef):
        raise ContractValidationError("record_evidence requires an EvidenceRef")
    return evidence


def cap_claim(
    claim: ClaimState,
    evidence: Iterable[EvidenceRef],
) -> ClaimState:
    """Apply a generic weakest-evidence ceiling without owning phase state truth.

    Core verifies evidence-reference closure. Unknown or review-bound mandatory
    evidence cannot support an unchanged requested state, so the generic
    envelope is capped to ``review-bound``. Phase-specific state ordering remains
    extension-owned.
    """
    if not isinstance(claim, ClaimState):
        raise ContractValidationError("cap_claim requires a ClaimState")
    indexed: dict[str, EvidenceRef] = {}
    for item in evidence:
        if not isinstance(item, EvidenceRef):
            raise ContractValidationError("cap_claim evidence must be EvidenceRef values")
        if item.evidence_id in indexed:
            raise ContractValidationError(
                f"duplicate evidence_id supplied to cap_claim: {item.evidence_id}"
            )
        indexed[item.evidence_id] = item
    missing = sorted(set(claim.evidence_refs) - set(indexed))
    if missing:
        raise ContractValidationError(
            "claim references missing mandatory evidence: " + ", ".join(missing)
        )
    weak = sorted(
        identifier
        for identifier in claim.evidence_refs
        if indexed[identifier].knowledge_state
        in {KnowledgeState.UNKNOWN, KnowledgeState.REVIEW_BOUND}
    )
    if not weak:
        return claim
    supported_state = claim.supported_state
    if supported_state == claim.requested_state:
        supported_state = "review-bound"
    ceiling_marker = (
        "Mandatory evidence remains unknown or review-bound; "
        "no stronger claim is supported."
    )
    weak_marker = "Weak evidence refs: " + ", ".join(weak) + "."
    claim_ceiling = claim.claim_ceiling
    if ceiling_marker not in claim_ceiling:
        claim_ceiling = claim_ceiling.rstrip() + " " + ceiling_marker
    ceiling_reason = claim.ceiling_reason
    if weak_marker not in ceiling_reason:
        ceiling_reason = ceiling_reason.rstrip() + " " + weak_marker
    return replace(
        claim,
        supported_state=supported_state,
        claim_ceiling=claim_ceiling,
        ceiling_reason=ceiling_reason,
    )


def classify_control_owner(ownership: ControlOwnership) -> ControlOwnership:
    """Preserve a declared ownership split without transferring truth control."""
    if not isinstance(ownership, ControlOwnership):
        raise ContractValidationError(
            "classify_control_owner requires a ControlOwnership value"
        )
    return ownership


def register_extension(descriptor: ExtensionDescriptor) -> ExtensionDescriptor:
    """Validate and return declarative metadata; never load an implementation.

    Persistence, indexing, and snapshot assembly are internal Core concerns.
    """
    if not isinstance(descriptor, ExtensionDescriptor):
        raise ContractValidationError(
            "register_extension requires an ExtensionDescriptor"
        )
    return descriptor


def route_return_or_reentry(packet: ReturnReentryPacket) -> RouteRequest:
    """Convert a bounded return/re-entry packet into a route request."""
    if not isinstance(packet, ReturnReentryPacket):
        raise ContractValidationError(
            "route_return_or_reentry requires a ReturnReentryPacket"
        )
    entry_kind = (
        EntryKind.RETURN
        if packet.mode is ReturnReentryMode.REMEDIATION_RETURN
        else EntryKind.REENTRY
    )
    return RouteRequest(
        request_id=packet.packet_id,
        entry_kind=entry_kind,
        intent_key=packet.target_phase_id,
        source_refs=(),
    )
