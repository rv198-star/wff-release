"""Structural snapshot/decision/application receipts for bounded Agentic authority.

This module owns identity, freshness, provenance, and application completeness.
It does not define product, architecture, or implementation semantics.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable, Mapping

from common.bounded_agentic_challenge import (
    BoundedAgenticChallengeError,
    validate_bounded_challenge,
)
from common.bounded_agentic_challenge_compat import (
    CURRENT_DECISION_INTEGRITY_CONTRACT,
    LEGACY_DECISION_INTEGRITY_CONTRACT,
)


DECISION_ENVELOPE_SCHEMA = "wff.agentic-decision-envelope.v1"
APPLICATION_RECEIPT_SCHEMA = "wff.agentic-decision-application-receipt.v1"
INPUT_SNAPSHOT_SCHEMA = "wff.agentic-decision-input-snapshot.v1"
ACCEPTED_DECISION_STATUSES = {"accepted", "review-bound", "agentic-decision-required", "rejected"}


class AgenticDecisionAuthorityError(ValueError):
    """Raised when an Agentic authority receipt is missing, stale, or malformed."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return "sha256:" + sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _content_digest(payload: Mapping[str, Any]) -> str:
    return canonical_digest({key: value for key, value in payload.items() if key != "content_digest"})


def content_digest_is_valid(payload: Mapping[str, Any], *, schema_version: str) -> bool:
    return bool(
        isinstance(payload, Mapping)
        and payload.get("schema_version") == schema_version
        and payload.get("content_digest") == _content_digest(payload)
    )


def safe_regular_file(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    if not resolved.is_file() or resolved.is_symlink():
        return False
    current = Path(resolved.anchor)
    for part in resolved.parts[1:]:
        current = current / part
        if current.is_symlink():
            return False
    return True


def build_input_snapshot(
    *,
    phase_id: str,
    inputs: Iterable[tuple[str, Path]],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for role, raw_path in inputs:
        path = raw_path.resolve()
        if not safe_regular_file(path):
            raise AgenticDecisionAuthorityError(f"unsafe Agentic decision input: {path}")
        rows.append(
            {
                "role": str(role).strip(),
                "name": path.name,
                "sha256": file_digest(path),
            }
        )
    rows.sort(key=lambda row: (row["role"], row["name"]))
    payload: dict[str, Any] = {
        "schema_version": INPUT_SNAPSHOT_SCHEMA,
        "phase_id": str(phase_id).strip(),
        "inputs": rows,
        "context": dict(context or {}),
    }
    payload["snapshot_digest"] = canonical_digest(payload)
    return payload


def validate_input_snapshot(snapshot: Mapping[str, Any], *, expected_phase_id: str) -> None:
    if snapshot.get("schema_version") != INPUT_SNAPSHOT_SCHEMA:
        raise AgenticDecisionAuthorityError("Agentic input snapshot schema is invalid")
    if str(snapshot.get("phase_id") or "") != expected_phase_id:
        raise AgenticDecisionAuthorityError("Agentic input snapshot phase is invalid")
    rows = snapshot.get("inputs")
    if not isinstance(rows, list) or not rows:
        raise AgenticDecisionAuthorityError("Agentic input snapshot has no inputs")
    for row in rows:
        if not isinstance(row, dict):
            raise AgenticDecisionAuthorityError("Agentic input snapshot row is invalid")
        if not str(row.get("role") or "") or Path(str(row.get("name") or "")).name != str(row.get("name") or ""):
            raise AgenticDecisionAuthorityError("Agentic input snapshot identity is invalid")
        digest = str(row.get("sha256") or "")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise AgenticDecisionAuthorityError("Agentic input snapshot digest is invalid")
    body = {key: value for key, value in snapshot.items() if key != "snapshot_digest"}
    if snapshot.get("snapshot_digest") != canonical_digest(body):
        raise AgenticDecisionAuthorityError("Agentic input snapshot is stale")


def build_decision_envelope(
    *,
    phase_id: str,
    decision_kind: str,
    decision_id: str,
    input_snapshot: Mapping[str, Any],
    owner_id: str,
    semantic_payload: Mapping[str, Any],
    decision_status: str = "accepted",
    unresolved_items: Iterable[Mapping[str, Any]] = (),
    claim_ceiling: str,
    bounded_challenge: Mapping[str, Any] | None = None,
    challenge_binding: Mapping[str, Any] | None = None,
    decision_integrity_contract: str | None = None,
) -> dict[str, Any]:
    validate_input_snapshot(input_snapshot, expected_phase_id=phase_id)
    status = str(decision_status).strip()
    if status not in ACCEPTED_DECISION_STATUSES:
        raise AgenticDecisionAuthorityError(f"unsupported Agentic decision status: {status}")
    payload: dict[str, Any] = {
        "schema_version": DECISION_ENVELOPE_SCHEMA,
        "decision_id": str(decision_id).strip(),
        "phase_id": str(phase_id).strip(),
        "decision_kind": str(decision_kind).strip(),
        "decision_status": status,
        "input_snapshot": dict(input_snapshot),
        "input_snapshot_digest": str(input_snapshot.get("snapshot_digest") or ""),
        "decision_owner": {"kind": "host-agent", "id": str(owner_id).strip()},
        "semantic_payload": dict(semantic_payload),
        "unresolved_items": [dict(item) for item in unresolved_items],
        "claim_ceiling": str(claim_ceiling).strip(),
    }
    integrity_contract = str(decision_integrity_contract or "").strip()
    if not integrity_contract:
        integrity_contract = (
            CURRENT_DECISION_INTEGRITY_CONTRACT
            if bounded_challenge is not None and challenge_binding is not None
            else LEGACY_DECISION_INTEGRITY_CONTRACT
        )
    if integrity_contract not in {
        CURRENT_DECISION_INTEGRITY_CONTRACT,
        LEGACY_DECISION_INTEGRITY_CONTRACT,
    }:
        raise AgenticDecisionAuthorityError(
            f"unsupported decision integrity contract: {integrity_contract}"
        )
    if status in {"accepted", "review-bound"} and (
        (bounded_challenge is None) != (challenge_binding is None)
    ):
        raise AgenticDecisionAuthorityError(
            "accepted/review-bound decisions require challenge evidence and exact binding together"
        )
    if integrity_contract == CURRENT_DECISION_INTEGRITY_CONTRACT and (
        bounded_challenge is None or challenge_binding is None
    ):
        raise AgenticDecisionAuthorityError(
            "bounded-challenge-integrity-v1 requires challenge evidence and exact binding"
        )
    payload["decision_integrity_contract"] = integrity_contract
    if bounded_challenge is not None:
        challenge = dict(bounded_challenge)
        if status in {"accepted", "review-bound"}:
            try:
                validate_bounded_challenge(
                    challenge,
                    expected_phase_id=str(phase_id).strip(),
                    expected_owner_id=str(owner_id).strip(),
                    accepted_decision=status == "accepted",
                )
            except BoundedAgenticChallengeError as exc:
                raise AgenticDecisionAuthorityError(
                    f"bounded Agentic challenge is invalid: {exc}"
                ) from exc
        payload["bounded_challenge"] = challenge
        if challenge_binding is not None:
            payload["challenge_binding"] = dict(challenge_binding)
    if not payload["decision_id"] or not payload["decision_kind"] or not payload["decision_owner"]["id"]:
        raise AgenticDecisionAuthorityError("Agentic decision identity is incomplete")
    if not payload["semantic_payload"]:
        raise AgenticDecisionAuthorityError("Agentic decision semantic payload is empty")
    payload["content_digest"] = _content_digest(payload)
    return payload


def validate_decision_envelope(
    decision: Mapping[str, Any],
    *,
    expected_phase_id: str,
    expected_decision_kind: str,
    expected_input_snapshot_digest: str,
    accepted_required: bool = True,
) -> None:
    if not content_digest_is_valid(decision, schema_version=DECISION_ENVELOPE_SCHEMA):
        raise AgenticDecisionAuthorityError("Agentic decision content digest is invalid")
    if str(decision.get("phase_id") or "") != expected_phase_id:
        raise AgenticDecisionAuthorityError("Agentic decision phase is invalid")
    if str(decision.get("decision_kind") or "") != expected_decision_kind:
        raise AgenticDecisionAuthorityError("Agentic decision kind is invalid")
    if str(decision.get("input_snapshot_digest") or "") != expected_input_snapshot_digest:
        raise AgenticDecisionAuthorityError("Agentic decision is stale for the current input snapshot")
    snapshot = decision.get("input_snapshot")
    if not isinstance(snapshot, dict):
        raise AgenticDecisionAuthorityError("Agentic decision input snapshot is missing")
    validate_input_snapshot(snapshot, expected_phase_id=expected_phase_id)
    if snapshot.get("snapshot_digest") != expected_input_snapshot_digest:
        raise AgenticDecisionAuthorityError("Agentic decision embeds a different input snapshot")
    owner = decision.get("decision_owner")
    if not isinstance(owner, dict) or owner.get("kind") != "host-agent" or not str(owner.get("id") or ""):
        raise AgenticDecisionAuthorityError("Agentic decision owner is invalid")
    status = str(decision.get("decision_status") or "")
    if status not in ACCEPTED_DECISION_STATUSES:
        raise AgenticDecisionAuthorityError("Agentic decision status is invalid")
    if accepted_required and status != "accepted":
        raise AgenticDecisionAuthorityError(f"Agentic decision is not accepted: {status}")
    if not isinstance(decision.get("semantic_payload"), dict) or not decision.get("semantic_payload"):
        raise AgenticDecisionAuthorityError("Agentic decision semantic payload is missing")
    integrity_contract = str(decision.get("decision_integrity_contract") or LEGACY_DECISION_INTEGRITY_CONTRACT)
    if integrity_contract not in {
        CURRENT_DECISION_INTEGRITY_CONTRACT,
        LEGACY_DECISION_INTEGRITY_CONTRACT,
    }:
        raise AgenticDecisionAuthorityError("Agentic decision integrity contract is invalid")
    challenge = decision.get("bounded_challenge")
    binding = decision.get("challenge_binding")
    if integrity_contract == CURRENT_DECISION_INTEGRITY_CONTRACT and (
        not isinstance(challenge, Mapping) or not isinstance(binding, Mapping)
    ):
        raise AgenticDecisionAuthorityError(
            "current Agentic decision integrity contract lacks challenge evidence or binding"
        )
    if status in {"accepted", "review-bound"} and (
        (challenge is None) != (binding is None)
    ):
        raise AgenticDecisionAuthorityError(
            "accepted/review-bound decision challenge evidence and binding are incomplete"
        )
    if challenge is not None:
        try:
            validate_bounded_challenge(
                challenge,
                expected_phase_id=expected_phase_id,
                expected_owner_id=str(owner.get("id") or ""),
                accepted_decision=status == "accepted",
            )
        except BoundedAgenticChallengeError as exc:
            raise AgenticDecisionAuthorityError(
                f"bounded Agentic challenge is invalid: {exc}"
            ) from exc


def build_application_receipt(
    *,
    decision: Mapping[str, Any],
    writer_id: str,
    output_paths: Iterable[Path],
    application_status: str,
    missing_applications: Iterable[str] = (),
    unused_decisions: Iterable[str] = (),
    claim_ceiling: str,
) -> dict[str, Any]:
    outputs: list[dict[str, str]] = []
    for raw_path in output_paths:
        path = raw_path.resolve()
        if not safe_regular_file(path):
            raise AgenticDecisionAuthorityError(f"unsafe Agentic application output: {path}")
        outputs.append({"name": path.name, "sha256": file_digest(path)})
    outputs.sort(key=lambda row: row["name"])
    payload: dict[str, Any] = {
        "schema_version": APPLICATION_RECEIPT_SCHEMA,
        "phase_id": str(decision.get("phase_id") or ""),
        "decision_id": str(decision.get("decision_id") or ""),
        "decision_digest": str(decision.get("content_digest") or ""),
        "canonical_writer_id": str(writer_id).strip(),
        "application_status": str(application_status).strip(),
        "outputs": outputs,
        "missing_applications": sorted({str(item).strip() for item in missing_applications if str(item).strip()}),
        "unused_decisions": sorted({str(item).strip() for item in unused_decisions if str(item).strip()}),
        "claim_ceiling": str(claim_ceiling).strip(),
    }
    if not payload["decision_id"] or not payload["decision_digest"] or not payload["canonical_writer_id"]:
        raise AgenticDecisionAuthorityError("Agentic application receipt identity is incomplete")
    payload["content_digest"] = _content_digest(payload)
    return payload


def validate_application_receipt(
    receipt: Mapping[str, Any],
    *,
    decision: Mapping[str, Any],
    required_output_names: Iterable[str] = (),
) -> None:
    if not content_digest_is_valid(receipt, schema_version=APPLICATION_RECEIPT_SCHEMA):
        raise AgenticDecisionAuthorityError("Agentic application receipt digest is invalid")
    if receipt.get("decision_id") != decision.get("decision_id") or receipt.get("decision_digest") != decision.get("content_digest"):
        raise AgenticDecisionAuthorityError("Agentic application receipt decision binding is invalid")
    if receipt.get("application_status") != "complete":
        raise AgenticDecisionAuthorityError("Agentic decision application is incomplete")
    if receipt.get("missing_applications") or receipt.get("unused_decisions"):
        raise AgenticDecisionAuthorityError("Agentic decision application has missing or unused items")
    outputs = receipt.get("outputs")
    if not isinstance(outputs, list):
        raise AgenticDecisionAuthorityError("Agentic application outputs are invalid")
    actual = {str(row.get("name") or "") for row in outputs if isinstance(row, dict)}
    missing = sorted(set(required_output_names) - actual)
    if missing:
        raise AgenticDecisionAuthorityError("Agentic application receipt misses outputs: " + ", ".join(missing))


def load_json_object(path: Path) -> dict[str, Any]:
    if not safe_regular_file(path):
        raise AgenticDecisionAuthorityError(f"unsafe JSON authority file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgenticDecisionAuthorityError(f"invalid JSON authority file: {path}") from exc
    if not isinstance(value, dict):
        raise AgenticDecisionAuthorityError(f"JSON authority must be an object: {path}")
    return value


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=path.parent) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
