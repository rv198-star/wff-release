"""Versioned public semantic types for the WFF Core contract 1.0.0.

The types preserve identity, evidence, ownership, and control boundaries. They
validate structure only and intentionally do not decide product, architecture,
implementation, validation-content, or brownfield truth.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
import re
from typing import Any, Iterable, Mapping

from .errors import ContractValidationError


_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]*$")
_SEMVER_RANGE = re.compile(
    r"^>=\d+\.\d+\.\d+(?:,<\d+\.\d+\.\d+)?$"
)


def _text(value: object, label: str, *, minimum: int = 1, maximum: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) < minimum or len(text) > maximum:
        raise ContractValidationError(
            f"{label} must contain between {minimum} and {maximum} characters"
        )
    return text


def _optional_text(value: object, label: str, *, maximum: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ContractValidationError(f"{label} exceeds {maximum} characters")
    return text


def _identifier(value: object, label: str) -> str:
    identifier = _text(value, label, maximum=240)
    if _IDENTIFIER.fullmatch(identifier) is None:
        raise ContractValidationError(
            f"{label} must start with a letter and use letters, digits, '.', '_', ':', or '-'"
        )
    return identifier


def _unique_texts(
    values: Iterable[object],
    label: str,
    *,
    identifiers: bool = False,
) -> tuple[str, ...]:
    result: list[str] = []
    for index, raw in enumerate(values, start=1):
        value = (
            _identifier(raw, f"{label}[{index}]")
            if identifiers
            else _text(raw, f"{label}[{index}]", maximum=1000)
        )
        if value not in result:
            result.append(value)
    return tuple(result)


def _serialize(value: object) -> object:
    if isinstance(value, StrEnum):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _serialize(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _serialize(item) for key, item in value.items()}
    return value


class ContractValue:
    """Mixin for deterministic JSON-compatible public contract projections."""

    def to_dict(self) -> dict[str, Any]:
        serialized = _serialize(self)
        if not isinstance(serialized, dict):
            raise ContractValidationError("contract value did not serialize to an object")
        return serialized


class EntryKind(StrEnum):
    EXTERNAL = "external"
    CONTINUATION = "continuation"
    RETURN = "return"
    REENTRY = "reentry"


class RouteDisposition(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNREGISTERED = "unregistered"
    BLOCKED = "blocked"


class PhaseKind(StrEnum):
    MAINLINE = "mainline"
    SIDECAR = "sidecar"


class AdmissionDisposition(StrEnum):
    ADMIT = "admit"
    ADMIT_REVIEW_BOUND = "admit-review-bound"
    RETURN = "return"
    BLOCKED = "blocked"


class HandoffDecision(StrEnum):
    CONTINUE = "continue"
    CONTINUE_REVIEW_BOUND = "continue-review-bound"
    RETURN = "return"
    BLOCKED = "blocked"


class UnresolvedStatus(StrEnum):
    PROVISIONAL = "provisional"
    REVIEW_BOUND = "review-bound"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class EvidenceKind(StrEnum):
    SOURCE = "source"
    TEST = "test"
    RUNTIME = "runtime"
    TRACE = "trace"
    REVIEW = "review"
    DECISION = "decision"
    EXTERNAL_AUTHORITY = "external-authority"


class KnowledgeState(StrEnum):
    OBSERVED_FACT = "observed-fact"
    INFERRED_KNOWLEDGE = "inferred-knowledge"
    UNKNOWN = "unknown"
    REVIEW_BOUND = "review-bound"


class ExtensionKind(StrEnum):
    PHASE = "phase"
    ROUTE_ADAPTER = "route-adapter"
    SUPPORT = "support"
    ASSURANCE = "assurance"
    ADAPTATION = "adaptation"


class FailurePolicy(StrEnum):
    FAIL_CLOSED = "fail-closed"
    RETURN_UPSTREAM = "return-upstream"
    REVIEW_BOUND = "review-bound"


class ReturnReentryMode(StrEnum):
    REMEDIATION_RETURN = "remediation-return"
    PHASEX_REENTRY = "phasex-reentry"


@dataclass(frozen=True)
class ArtifactRef(ContractValue):
    artifact_id: str
    artifact_type: str
    artifact_version: str
    source_authority: str
    location: str = ""
    content_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _identifier(self.artifact_id, "artifact_id"))
        object.__setattr__(self, "artifact_type", _identifier(self.artifact_type, "artifact_type"))
        object.__setattr__(self, "artifact_version", _text(self.artifact_version, "artifact_version", maximum=120))
        object.__setattr__(self, "source_authority", _text(self.source_authority, "source_authority", maximum=500))
        object.__setattr__(self, "location", _optional_text(self.location, "location", maximum=2000))
        digest = _optional_text(self.content_digest, "content_digest", maximum=200)
        if digest and not digest.startswith("sha256:"):
            raise ContractValidationError("content_digest must use the sha256:<hex> form")
        object.__setattr__(self, "content_digest", digest)


@dataclass(frozen=True)
class RouteRequest(ContractValue):
    request_id: str
    entry_kind: EntryKind
    intent_key: str
    source_refs: tuple[ArtifactRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _identifier(self.request_id, "request_id"))
        object.__setattr__(self, "entry_kind", EntryKind(self.entry_kind))
        object.__setattr__(self, "intent_key", _text(self.intent_key, "intent_key", maximum=240))
        refs = tuple(self.source_refs)
        if any(not isinstance(item, ArtifactRef) for item in refs):
            raise ContractValidationError("source_refs must contain ArtifactRef values")
        object.__setattr__(self, "source_refs", refs)


@dataclass(frozen=True)
class RouteResolution(ContractValue):
    request_id: str
    disposition: RouteDisposition
    extension_id: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _identifier(self.request_id, "request_id"))
        disposition = RouteDisposition(self.disposition)
        object.__setattr__(self, "disposition", disposition)
        extension = _optional_text(self.extension_id, "extension_id", maximum=240)
        if extension:
            extension = _identifier(extension, "extension_id")
        if disposition is RouteDisposition.RESOLVED and not extension:
            raise ContractValidationError("resolved routes require extension_id")
        if disposition is not RouteDisposition.RESOLVED and extension:
            raise ContractValidationError("non-resolved routes must not name an extension_id")
        object.__setattr__(self, "extension_id", extension)
        object.__setattr__(self, "reason", _text(self.reason, "reason", minimum=4, maximum=2000))


@dataclass(frozen=True)
class PhaseDescriptor(ContractValue):
    phase_id: str
    phase_kind: PhaseKind
    truth_owner: str
    required_input_contracts: tuple[str, ...]
    allowed_next_phase_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase_id", _identifier(self.phase_id, "phase_id"))
        object.__setattr__(self, "phase_kind", PhaseKind(self.phase_kind))
        object.__setattr__(self, "truth_owner", _text(self.truth_owner, "truth_owner", maximum=500))
        required = _unique_texts(self.required_input_contracts, "required_input_contracts", identifiers=True)
        if not required:
            raise ContractValidationError("required_input_contracts must not be empty")
        object.__setattr__(self, "required_input_contracts", required)
        object.__setattr__(
            self,
            "allowed_next_phase_ids",
            _unique_texts(self.allowed_next_phase_ids, "allowed_next_phase_ids", identifiers=True),
        )


@dataclass(frozen=True)
class PhaseAdmission(ContractValue):
    phase_id: str
    disposition: AdmissionDisposition
    input_refs: tuple[ArtifactRef, ...]
    semantic_judgment_owner: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase_id", _identifier(self.phase_id, "phase_id"))
        object.__setattr__(self, "disposition", AdmissionDisposition(self.disposition))
        refs = tuple(self.input_refs)
        if any(not isinstance(item, ArtifactRef) for item in refs):
            raise ContractValidationError("input_refs must contain ArtifactRef values")
        object.__setattr__(self, "input_refs", refs)
        object.__setattr__(
            self,
            "semantic_judgment_owner",
            _text(self.semantic_judgment_owner, "semantic_judgment_owner", maximum=500),
        )
        object.__setattr__(self, "reason", _text(self.reason, "reason", minimum=4, maximum=2000))


@dataclass(frozen=True)
class ArtifactBinding(ContractValue):
    binding_id: str
    subject_artifact_id: str
    relation: str
    object_ref: str
    authority_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "binding_id", _identifier(self.binding_id, "binding_id"))
        object.__setattr__(self, "subject_artifact_id", _identifier(self.subject_artifact_id, "subject_artifact_id"))
        object.__setattr__(self, "relation", _identifier(self.relation, "relation"))
        object.__setattr__(self, "object_ref", _text(self.object_ref, "object_ref", maximum=1000))
        object.__setattr__(self, "authority_ref", _text(self.authority_ref, "authority_ref", maximum=1000))


@dataclass(frozen=True)
class EvidenceRef(ContractValue):
    evidence_id: str
    evidence_kind: EvidenceKind
    knowledge_state: KnowledgeState
    subject_refs: tuple[str, ...]
    provenance: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _identifier(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "evidence_kind", EvidenceKind(self.evidence_kind))
        object.__setattr__(self, "knowledge_state", KnowledgeState(self.knowledge_state))
        refs = _unique_texts(self.subject_refs, "subject_refs")
        if not refs:
            raise ContractValidationError("subject_refs must not be empty")
        object.__setattr__(self, "subject_refs", refs)
        object.__setattr__(self, "provenance", _text(self.provenance, "provenance", minimum=8, maximum=2000))


@dataclass(frozen=True)
class ClaimState(ContractValue):
    claim_id: str
    scope: str
    requested_state: str
    supported_state: str
    evidence_refs: tuple[str, ...]
    claim_ceiling: str
    ceiling_reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _identifier(self.claim_id, "claim_id"))
        object.__setattr__(self, "scope", _text(self.scope, "scope", maximum=1000))
        object.__setattr__(self, "requested_state", _identifier(self.requested_state, "requested_state"))
        object.__setattr__(self, "supported_state", _identifier(self.supported_state, "supported_state"))
        refs = _unique_texts(self.evidence_refs, "evidence_refs", identifiers=True)
        if not refs:
            raise ContractValidationError("evidence_refs must not be empty")
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "claim_ceiling", _text(self.claim_ceiling, "claim_ceiling", minimum=8, maximum=2000))
        object.__setattr__(self, "ceiling_reason", _text(self.ceiling_reason, "ceiling_reason", minimum=8, maximum=2000))


@dataclass(frozen=True)
class UnresolvedItem(ContractValue):
    item_id: str
    status: UnresolvedStatus
    owner: str
    verification_needed: str
    downstream_must_not_assume: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _identifier(self.item_id, "item_id"))
        object.__setattr__(self, "status", UnresolvedStatus(self.status))
        object.__setattr__(self, "owner", _text(self.owner, "owner", maximum=500))
        object.__setattr__(
            self,
            "verification_needed",
            _text(self.verification_needed, "verification_needed", minimum=4, maximum=2000),
        )
        object.__setattr__(
            self,
            "downstream_must_not_assume",
            _text(self.downstream_must_not_assume, "downstream_must_not_assume", minimum=4, maximum=2000),
        )


@dataclass(frozen=True)
class HandoffPacket(ContractValue):
    handoff_id: str
    from_phase_id: str
    to_phase_id: str
    artifact_refs: tuple[ArtifactRef, ...]
    evidence_refs: tuple[str, ...]
    unresolved_items: tuple[UnresolvedItem, ...] = ()
    decision: HandoffDecision = HandoffDecision.CONTINUE

    def __post_init__(self) -> None:
        object.__setattr__(self, "handoff_id", _identifier(self.handoff_id, "handoff_id"))
        object.__setattr__(self, "from_phase_id", _identifier(self.from_phase_id, "from_phase_id"))
        object.__setattr__(self, "to_phase_id", _identifier(self.to_phase_id, "to_phase_id"))
        artifacts = tuple(self.artifact_refs)
        if not artifacts or any(not isinstance(item, ArtifactRef) for item in artifacts):
            raise ContractValidationError("artifact_refs must contain at least one ArtifactRef")
        object.__setattr__(self, "artifact_refs", artifacts)
        evidence = _unique_texts(self.evidence_refs, "evidence_refs", identifiers=True)
        if not evidence:
            raise ContractValidationError("evidence_refs must not be empty")
        object.__setattr__(self, "evidence_refs", evidence)
        unresolved = tuple(self.unresolved_items)
        if any(not isinstance(item, UnresolvedItem) for item in unresolved):
            raise ContractValidationError("unresolved_items must contain UnresolvedItem values")
        object.__setattr__(self, "unresolved_items", unresolved)
        object.__setattr__(self, "decision", HandoffDecision(self.decision))


@dataclass(frozen=True)
class ControlOwnership(ContractValue):
    concern_id: str
    workflow_role: str
    agentic_role: str
    template_role: str
    evidence_role: str
    forbidden_owner_transfer: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "concern_id", _identifier(self.concern_id, "concern_id"))
        object.__setattr__(self, "workflow_role", _text(self.workflow_role, "workflow_role", maximum=1000))
        object.__setattr__(self, "agentic_role", _text(self.agentic_role, "agentic_role", maximum=1000))
        object.__setattr__(self, "template_role", _text(self.template_role, "template_role", maximum=1000))
        object.__setattr__(self, "evidence_role", _text(self.evidence_role, "evidence_role", maximum=1000))
        transfers = _unique_texts(self.forbidden_owner_transfer, "forbidden_owner_transfer")
        if not transfers:
            raise ContractValidationError("forbidden_owner_transfer must not be empty")
        object.__setattr__(self, "forbidden_owner_transfer", transfers)


@dataclass(frozen=True)
class ExtensionDescriptor(ContractValue):
    extension_id: str
    extension_kind: ExtensionKind
    core_contract_range: str
    route_keys: tuple[str, ...]
    phase_ids: tuple[str, ...]
    consumes_contracts: tuple[str, ...]
    produces_contracts: tuple[str, ...]
    compatibility_aliases: tuple[str, ...]
    truth_owner: str
    failure_policy: FailurePolicy

    def __post_init__(self) -> None:
        object.__setattr__(self, "extension_id", _identifier(self.extension_id, "extension_id"))
        object.__setattr__(self, "extension_kind", ExtensionKind(self.extension_kind))
        version_range = _text(self.core_contract_range, "core_contract_range", maximum=80)
        if _SEMVER_RANGE.fullmatch(version_range) is None:
            raise ContractValidationError(
                "core_contract_range must use >=MAJOR.MINOR.PATCH[,<MAJOR.MINOR.PATCH]"
            )
        object.__setattr__(self, "core_contract_range", version_range)
        object.__setattr__(self, "route_keys", _unique_texts(self.route_keys, "route_keys"))
        object.__setattr__(self, "phase_ids", _unique_texts(self.phase_ids, "phase_ids", identifiers=True))
        consumes = _unique_texts(self.consumes_contracts, "consumes_contracts", identifiers=True)
        if not consumes:
            raise ContractValidationError("consumes_contracts must not be empty")
        object.__setattr__(self, "consumes_contracts", consumes)
        object.__setattr__(
            self,
            "produces_contracts",
            _unique_texts(self.produces_contracts, "produces_contracts", identifiers=True),
        )
        object.__setattr__(
            self,
            "compatibility_aliases",
            _unique_texts(self.compatibility_aliases, "compatibility_aliases"),
        )
        object.__setattr__(self, "truth_owner", _text(self.truth_owner, "truth_owner", maximum=1000))
        failure_policy = FailurePolicy(self.failure_policy)
        object.__setattr__(self, "failure_policy", failure_policy)
        if self.extension_kind is ExtensionKind.PHASE:
            if not self.phase_ids:
                raise ContractValidationError("phase extensions must declare phase_ids")
            if not self.produces_contracts:
                raise ContractValidationError(
                    "phase extensions must declare produced public contracts"
                )
        if self.extension_kind is ExtensionKind.ROUTE_ADAPTER and not self.route_keys:
            raise ContractValidationError(
                "route-adapter extensions must declare route_keys"
            )


@dataclass(frozen=True)
class ReturnReentryPacket(ContractValue):
    packet_id: str
    mode: ReturnReentryMode
    source_phase_id: str
    target_phase_id: str
    evidence_refs: tuple[str, ...]
    required_action: str
    minimum_rerun_boundary: str
    claim_ceiling: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", _identifier(self.packet_id, "packet_id"))
        object.__setattr__(self, "mode", ReturnReentryMode(self.mode))
        object.__setattr__(self, "source_phase_id", _identifier(self.source_phase_id, "source_phase_id"))
        object.__setattr__(self, "target_phase_id", _identifier(self.target_phase_id, "target_phase_id"))
        evidence = _unique_texts(self.evidence_refs, "evidence_refs", identifiers=True)
        if not evidence:
            raise ContractValidationError("evidence_refs must not be empty")
        object.__setattr__(self, "evidence_refs", evidence)
        object.__setattr__(self, "required_action", _text(self.required_action, "required_action", minimum=4, maximum=2000))
        object.__setattr__(
            self,
            "minimum_rerun_boundary",
            _identifier(self.minimum_rerun_boundary, "minimum_rerun_boundary"),
        )
        object.__setattr__(self, "claim_ceiling", _text(self.claim_ceiling, "claim_ceiling", minimum=8, maximum=2000))
