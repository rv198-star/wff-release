"""Derived P1/P2 -> P3 semantic-consistency evidence.

This module does not create product, architecture, or implementation truth.
It binds already accepted P1 claims, explicit P2 contracts/semantics, and P3
implementation/evidence surfaces so Workflow can preserve the handoff and
Evidence can expose silent loss, misbinding, or missing realization.
"""

from __future__ import annotations

from hashlib import sha256
import importlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from common.bounded_agentic_challenge import challenge_summary
from common.claim_control_acceptance import evaluate_claim_control_acceptance
from common.claim_control_contract import validate_claim_control_surface


COMMITMENT_UNION_SCHEMA = "wff.semantic-commitment-union.v1"
REALIZATION_LEDGER_SCHEMA = "wff.semantic-realization-ledger.v1"
EVIDENCE_DISPOSITION_SCHEMA = "wff.evidence-disposition.v1"
COMMITMENT_UNION_VERIFICATION_SCHEMA = "wff.semantic-commitment-union-verification.v1"
P1_COMMITMENT_AUTHORITY_SCHEMA = "wff.p1-commitment-authority-snapshot.v1"
P1_AGENTIC_PRODUCT_AUTHORITY_SCHEMA = "wff.p1-agentic-product-authority.v1"
P2_COMMITMENT_DISPOSITION_SCHEMA = "wff.p2-commitment-disposition-ledger.v1"
PHASE2_CLAIM_CONTROL_VERIFICATION_SCHEMA = "wff.phase2-claim-control-verification.v1"

P1_COMMITMENT_KINDS = {
    "workflow_step",
    "acceptance_criterion",
    "epic",
    "requirement",
    "use_case",
    "user_story",
    "policy",
    "constraint",
}
P1_ACCEPTED_STATUSES = {"accepted", "approved", "active"}
EXACT_P1_P2_RESOLUTION_STATUS = "mapped"
ENVIRONMENT_DISPOSITION_CLASSES = {"environment-only", "transient-only"}


def canonical_digest(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def content_digest_is_valid(payload: dict[str, Any], *, schema_version: str | None = None) -> bool:
    if not isinstance(payload, dict):
        return False
    if schema_version is not None and payload.get("schema_version") != schema_version:
        return False
    expected = str(payload.get("content_digest") or "").strip()
    if not expected:
        return False
    body = {key: value for key, value in payload.items() if key != "content_digest"}
    return expected == canonical_digest(body)


def load_json_object(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists() or path.is_symlink():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_regular_file(path: Path) -> bool:
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        return False
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            return False
    return True


def build_p1_commitment_authority_snapshot(
    *,
    artifact_path: Path,
    sidecar_path: Path,
) -> dict[str, Any]:
    artifact = artifact_path.resolve()
    sidecar = sidecar_path.resolve()
    if not _safe_regular_file(artifact) or not _safe_regular_file(sidecar):
        raise ValueError("P1 commitment authority requires safe regular artifact and sidecar files")
    acceptance = evaluate_claim_control_acceptance(
        artifact,
        surface_path=sidecar,
    )
    surface = load_json_object(sidecar)
    contract = validate_claim_control_surface(surface) if surface else {"overall_status": "blocked"}
    agentic_authority_path = artifact.parent / "p1-agentic-product-authority.json"
    agentic_authority = load_json_object(agentic_authority_path)
    agentic_authority_valid = p1_agentic_product_authority_is_valid(agentic_authority)
    accepted = bool(
        acceptance.get("overall_status") == "pass"
        and contract.get("overall_status") == "pass"
    )
    payload = {
        "schema_version": P1_COMMITMENT_AUTHORITY_SCHEMA,
        "status": "accepted-p1-commitment-authority" if accepted else "blocked-p1-commitment-authority",
        "source_artifact": {
            "name": artifact.name,
            "sha256": file_digest(artifact),
        },
        "source_sidecar": {
            "name": sidecar.name,
            "sha256": file_digest(sidecar),
        },
        "acceptance": {
            "overall_status": str(acceptance.get("overall_status") or "blocked"),
            "classifications": string_list(acceptance.get("classifications")),
            "required_mechanism": str(
                (acceptance.get("route_decision") or {}).get("required_mechanism") or ""
            ),
        },
        "claim_control_surface_digest": canonical_digest(surface),
        "claim_control_surface": surface,
        "agentic_product_authority": agentic_authority if agentic_authority_valid else {},
        "agentic_product_authority_digest": (
            str(agentic_authority.get("content_digest") or "") if agentic_authority_valid else ""
        ),
        "authority_mode": (
            "snapshot-bound-agentic-product-authority"
            if agentic_authority_valid
            else "legacy-compiled-claim-authority"
        ),
        "claim_ceiling": (
            "This P2 handoff snapshot preserves accepted P1 claim authority for deterministic downstream identity checks. "
            "It does not create product truth, alter P1, or establish L2/L2+."
        ),
    }
    payload["content_digest"] = canonical_digest(
        {key: payload[key] for key in payload if key != "content_digest"}
    )
    return payload


def p1_agentic_product_authority_is_valid(authority: dict[str, Any]) -> bool:
    if not isinstance(authority, dict) or authority.get("schema_version") != P1_AGENTIC_PRODUCT_AUTHORITY_SCHEMA:
        return False
    if authority.get("status") != "accepted-p1-agentic-product-authority":
        return False
    expected = str(authority.get("content_digest") or "")
    body = {key: value for key, value in authority.items() if key != "content_digest"}
    if not expected or expected != canonical_digest(body):
        return False
    commitments = authority.get("commitments")
    return bool(
        authority.get("decision_digest")
        and isinstance(commitments, list)
        and commitments
        and all(isinstance(row, dict) and str(row.get("commitment_id") or "") for row in commitments)
    )


def p1_commitment_authority_is_valid(snapshot: dict[str, Any]) -> bool:
    if not content_digest_is_valid(snapshot, schema_version=P1_COMMITMENT_AUTHORITY_SCHEMA):
        return False
    if snapshot.get("status") != "accepted-p1-commitment-authority":
        return False
    acceptance = snapshot.get("acceptance") if isinstance(snapshot.get("acceptance"), dict) else {}
    if acceptance.get("overall_status") != "pass":
        return False
    surface = snapshot.get("claim_control_surface")
    if not isinstance(surface, dict) or not surface:
        return False
    if snapshot.get("claim_control_surface_digest") != canonical_digest(surface):
        return False
    if validate_claim_control_surface(surface).get("overall_status") != "pass":
        return False
    agentic_authority = snapshot.get("agentic_product_authority")
    if agentic_authority:
        if not isinstance(agentic_authority, dict) or not p1_agentic_product_authority_is_valid(agentic_authority):
            return False
        if snapshot.get("agentic_product_authority_digest") != agentic_authority.get("content_digest"):
            return False
        if snapshot.get("authority_mode") != "snapshot-bound-agentic-product-authority":
            return False
    for key in ("source_artifact", "source_sidecar"):
        row = snapshot.get(key) if isinstance(snapshot.get(key), dict) else {}
        name = str(row.get("name") or "")
        digest = str(row.get("sha256") or "")
        if not name or Path(name).name != name or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            return False
    return True


def p1_claim_control_from_authority(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not p1_commitment_authority_is_valid(snapshot):
        return {}
    surface = snapshot.get("claim_control_surface")
    return dict(surface) if isinstance(surface, dict) else {}


P1_UPSTREAM_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:P1-(?:AC|EP|REQ|UC|US)-\d{3}|FLOW-\d{1,4}|STATE-[A-Za-z0-9_:-]+)(?![A-Za-z0-9_-])"
)


def _resolve_safe_file_within(root: Path, raw_path: object) -> Path | None:
    base = root.resolve()
    raw = str(raw_path or "").strip()
    if not raw:
        return None
    original = Path(raw)
    candidates = [original] if original.is_absolute() else [base / original]
    candidates.append(base / original.name)
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(base)
        except (OSError, ValueError):
            continue
        if _safe_regular_file(resolved):
            return resolved
    return None


def verify_phase2_claim_control_report(
    *,
    phase2_root: Path,
    report: dict[str, Any],
    p1_commitment_authority: dict[str, Any],
) -> dict[str, Any]:
    root = phase2_root.resolve()
    failures: list[str] = []
    p1_surface = p1_claim_control_from_authority(p1_commitment_authority)
    if not p1_surface:
        failures.append("p1_commitment_authority_invalid")
    if str(report.get("overall_status") or "") != "pass":
        failures.append("phase2_claim_control_report_not_pass")
    if str(report.get("phase1_claim_source_mode") or "") != "upstream-claim-control":
        failures.append("phase2_claim_source_not_upstream_control")
    if str(report.get("p1_commitment_authority_digest") or "") != str(
        p1_commitment_authority.get("content_digest") or ""
    ):
        failures.append("phase2_p1_authority_digest_mismatch")

    accepted_ids: set[str] = set()
    claim_rows = (p1_surface.get("claim_index") or {}).get("claims", [])
    if isinstance(claim_rows, list):
        for row in claim_rows:
            if not isinstance(row, dict):
                continue
            claim_id = str(row.get("id") or "").strip()
            status = str(row.get("status") or "").strip().lower()
            if claim_id and status in P1_ACCEPTED_STATUSES:
                accepted_ids.add(claim_id)

    normalized_artifacts: list[dict[str, Any]] = []
    artifacts = report.get("artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        failures.append("phase2_claim_control_artifacts_missing")
        artifacts = []
    for index, raw_row in enumerate(artifacts):
        if not isinstance(raw_row, dict):
            failures.append(f"phase2_claim_control_artifact_invalid:{index}")
            continue
        artifact = _resolve_safe_file_within(root, raw_row.get("artifact_path"))
        sidecar = _resolve_safe_file_within(root, raw_row.get("sidecar_path"))
        if artifact is None or sidecar is None:
            failures.append(f"phase2_claim_control_artifact_path_invalid:{index}")
            continue
        acceptance = evaluate_claim_control_acceptance(artifact, surface_path=sidecar)
        refs = sorted(set(P1_UPSTREAM_REF_RE.findall(artifact.read_text(encoding="utf-8"))))
        unknown_refs = sorted(ref for ref in refs if ref not in accepted_ids)
        declared_refs = sorted(string_list(raw_row.get("declared_upstream_p1_claim_refs")))
        if acceptance.get("overall_status") != "pass":
            failures.append(f"phase2_claim_control_acceptance_failed:{artifact.name}")
        if unknown_refs:
            failures.append(f"phase2_unknown_upstream_p1_claim_ref:{artifact.name}")
        if declared_refs != refs:
            failures.append(f"phase2_declared_upstream_refs_mismatch:{artifact.name}")
        normalized_artifacts.append(
            {
                "artifact_path": artifact.name,
                "sidecar_path": sidecar.name,
                "artifact_sha256": file_digest(artifact),
                "sidecar_sha256": file_digest(sidecar),
                "claim_control_acceptance_status": str(acceptance.get("overall_status") or "blocked"),
                "declared_upstream_p1_claim_refs": refs,
                "unknown_upstream_p1_claim_refs": unknown_refs,
            }
        )

    normalized_report = {
        "artifact_kind": "phase2-verified-claim-control-report",
        "overall_status": "pass" if not failures else "blocked",
        "phase1_claim_source_mode": "upstream-claim-control",
        "p1_commitment_authority_digest": str(
            p1_commitment_authority.get("content_digest") or ""
        ),
        "artifacts": normalized_artifacts,
    }
    verification = {
        "schema_version": PHASE2_CLAIM_CONTROL_VERIFICATION_SCHEMA,
        "status": "verified" if not failures else "blocked",
        "verified": not failures,
        "failures": sorted(set(failures)),
        "normalized_report_digest": canonical_digest(normalized_report),
        "claim_ceiling": (
            "This receipt verifies P2 claim-control artifact identity and upstream P1 reference consistency. "
            "It does not judge architecture quality or establish L2/L2+."
        ),
    }
    verification["content_digest"] = canonical_digest(
        {key: verification[key] for key in verification if key != "content_digest"}
    )
    return {
        "report": normalized_report,
        "verification": verification,
    }


def phase2_claim_control_verification_is_valid(receipt: dict[str, Any]) -> bool:
    return bool(
        content_digest_is_valid(
            receipt,
            schema_version=PHASE2_CLAIM_CONTROL_VERIFICATION_SCHEMA,
        )
        and receipt.get("verified") is True
        and receipt.get("status") == "verified"
        and not receipt.get("failures")
    )


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        values = value
    elif value is None:
        values = []
    else:
        values = [value]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _successful_rendered_claim_ids(claim_control: dict[str, Any]) -> set[str]:
    rendered: set[str] = set()
    refs = claim_control.get("render_refs", {}).get("refs", [])
    if not isinstance(refs, list):
        return rendered
    for row in refs:
        if not isinstance(row, dict) or str(row.get("audit_status") or "").strip().lower() != "pass":
            continue
        rendered.update(string_list(row.get("rendered_claim_refs")))
    return rendered


def _declared_realization_claim_ids(claim_control: dict[str, Any]) -> set[str]:
    declared: set[str] = set()
    items = claim_control.get("claim_realizations", {}).get("items", [])
    if not isinstance(items, list):
        return declared
    for row in items:
        if not isinstance(row, dict):
            continue
        status = str(row.get("realization_status") or "").strip().lower()
        claim_id = str(row.get("claim_id") or "").strip()
        if claim_id and status in {"declared", "accepted", "review-bound"}:
            declared.add(claim_id)
    return declared


def explicit_p1_claims_from_agentic_authority(
    authority: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not p1_agentic_product_authority_is_valid(authority):
        return [], ["p1_agentic_product_authority_invalid"]
    commitments: list[dict[str, Any]] = []
    failures: list[str] = []
    for row in authority.get("commitments", []):
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("commitment_id") or "").strip()
        kind = str(row.get("kind") or "").strip()
        status = str(row.get("status") or "").strip().lower()
        if not claim_id or kind not in P1_COMMITMENT_KINDS or status not in P1_ACCEPTED_STATUSES:
            continue
        source_refs = string_list(row.get("source_refs"))
        feature_ids = string_list(row.get("feature_ids"))
        if not source_refs or not feature_ids:
            failures.append(f"p1_agentic_commitment_missing_binding:{claim_id}")
            continue
        commitments.append(
            {
                "claim_id": claim_id,
                "kind": kind,
                "status": status,
                "text": str(row.get("statement") or "").strip(),
                "source_refs": source_refs,
                "feature_ids": feature_ids,
                "truth_state": str(row.get("truth_state") or ""),
                "owner": str(row.get("owner") or ""),
                "claim_ceiling": str(row.get("claim_ceiling") or ""),
            }
        )
    if not commitments:
        failures.append("no_explicit_p1_agentic_commitments")
    return commitments, sorted(set(failures))


def explicit_p1_claims(claim_control: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Return accepted P1 commitments that are bound to compiled authority.

    Projection prose cannot create a commitment: a claim must be present in the
    compiled claim index, have an accepted status, have a declared structured
    realization, and be rendered by a passing render-ref block.
    """

    failures: list[str] = []
    metadata = claim_control.get("artifact_metadata", {})
    authority = claim_control.get("claim_authority", {})
    if str(metadata.get("claim_authority_mode") or "") not in {
        "phase1-compiled-claim-surface",
        "snapshot-bound-agentic-product-authority",
    }:
        failures.append("p1_compiled_claim_authority_missing")
    if str(authority.get("compilation_status") or metadata.get("claim_compilation_status") or "") != "compiled":
        failures.append("p1_claim_compilation_not_complete")
    if str(metadata.get("inference_policy") or "") not in {"", "routing-hints-only-not-claim-truth"}:
        failures.append("p1_inference_policy_can_create_claim_truth")

    declared = _declared_realization_claim_ids(claim_control)
    rendered = _successful_rendered_claim_ids(claim_control)
    rows = claim_control.get("claim_index", {}).get("claims", [])
    if not isinstance(rows, list):
        failures.append("p1_claim_index_missing")
        return [], failures

    commitments: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        claim_id = str(row.get("id") or "").strip()
        kind = str(row.get("kind") or "").strip()
        status = str(row.get("status") or "").strip().lower()
        if not claim_id or kind not in P1_COMMITMENT_KINDS or status not in P1_ACCEPTED_STATUSES:
            continue
        if claim_id not in declared or claim_id not in rendered:
            failures.append(f"p1_claim_not_bound_to_realization_and_render:{claim_id}")
            continue
        commitments.append(
            {
                "claim_id": claim_id,
                "kind": kind,
                "status": status,
                "text": str(row.get("text") or "").strip(),
                "source_refs": string_list(row.get("source_refs")),
            }
        )
    return commitments, sorted(set(failures))


def _operation_rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def p2_commitment_disposition_ledger_is_valid(ledger: dict[str, Any]) -> bool:
    if not content_digest_is_valid(ledger, schema_version=P2_COMMITMENT_DISPOSITION_SCHEMA):
        return False
    if ledger.get("status") != "p1-commitment-dispositions-complete":
        return False
    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        return False
    commitment_ids = [
        str(row.get("commitment_id") or "").strip()
        for row in rows
        if isinstance(row, dict)
    ]
    if not all(commitment_ids) or len(commitment_ids) != len(set(commitment_ids)):
        return False
    if not str(ledger.get("decision_digest") or "").strip():
        return False
    if not str(ledger.get("p1_authority_digest") or "").strip():
        return False
    return True


def _authored_p2_disposition(
    *,
    claim: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any] | None:
    if not p2_commitment_disposition_ledger_is_valid(ledger):
        return None
    claim_id = str(claim.get("claim_id") or "").strip()
    row = next(
        (
            dict(item)
            for item in ledger.get("rows", [])
            if isinstance(item, dict) and str(item.get("commitment_id") or "").strip() == claim_id
        ),
        None,
    )
    if row is None:
        return None
    operation_index = {
        str(item.get("operation_id") or "").strip(): dict(item)
        for item in ledger.get("operation_portfolio", [])
        if isinstance(item, dict) and str(item.get("operation_id") or "").strip()
    }
    non_operation_index = {
        str(item.get("realization_id") or "").strip(): dict(item)
        for item in ledger.get("non_operation_realizations", [])
        if isinstance(item, dict) and str(item.get("realization_id") or "").strip()
    }
    authored = str(row.get("disposition") or "").strip()
    realization_ids = string_list(row.get("realization_ids"))
    operation_ids = [item for item in realization_ids if item in operation_index]
    non_operation_ids = [item for item in realization_ids if item in non_operation_index]
    contract_ids = sorted(
        {
            str(operation_index[item].get("contract_id") or "").strip()
            for item in operation_ids
            if str(operation_index[item].get("contract_id") or "").strip()
        }
    )
    if authored in {"exact-operation", "exact-operation-set"}:
        disposition = "accepted-p2-contract"
        owner = "P3"
        requirement = "exact-realization-required"
    elif authored == "non-operation-realization":
        disposition = "accepted-p2-non-operation"
        owner = "P3"
        requirement = "exact-realization-required"
    elif authored == "return-p1":
        disposition = "return-p1"
        owner = "P1"
        requirement = "upstream-return-required"
    elif authored == "p2-local-repair":
        disposition = "local-return-required"
        owner = "P2"
        requirement = "upstream-return-required"
    elif authored in {"deferred", "review-bound"}:
        disposition = "explicit-unresolved"
        owner = str(row.get("owner") or "P2")
        requirement = "preserve-review-bound"
    elif authored == "excluded":
        disposition = "explicit-excluded"
        owner = str(row.get("owner") or "P2")
        requirement = "no-realization-required"
    else:
        return None
    return {
        "authored_p2_disposition": authored,
        "p2_operation_ids": operation_ids,
        "p2_contract_ids": contract_ids,
        "p2_operation_contracts": {
            operation_id: str(operation_index[operation_id].get("contract_id") or "").strip()
            for operation_id in operation_ids
            if str(operation_index[operation_id].get("contract_id") or "").strip()
        },
        "p2_non_operation_ids": non_operation_ids,
        "p2_non_operation_realizations": {
            realization_id: non_operation_index[realization_id]
            for realization_id in non_operation_ids
        },
        "p2_disposition": disposition,
        "disposition_owner": owner,
        "disposition_reason": str(row.get("reason") or "").strip(),
        "disposition_evidence_refs": string_list(row.get("evidence_refs")),
        "minimum_rerun": str(row.get("minimum_rerun") or "").strip(),
        "claim_ceiling": str(row.get("claim_ceiling") or "").strip(),
        "p3_realization_requirement": requirement,
        "semantic_statuses": {
            operation_id: "resolved-by-agentic-architecture-decision"
            for operation_id in operation_ids
        },
    }


def build_semantic_commitment_union(
    *,
    p1_claim_control: dict[str, Any],
    operation_source_obligations: dict[str, Any],
    p1_operation_resolutions: dict[str, Any],
    operation_semantics: dict[str, Any],
    p2_claim_control_report: dict[str, Any] | None = None,
    p1_commitment_authority: dict[str, Any] | None = None,
    p2_claim_control_verification: dict[str, Any] | None = None,
    p2_commitment_disposition_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the L2 denominator view without inventing semantic truth."""

    agentic_authority = (
        p1_commitment_authority.get("agentic_product_authority", {})
        if isinstance(p1_commitment_authority, dict)
        and isinstance(p1_commitment_authority.get("agentic_product_authority"), dict)
        else {}
    )
    if agentic_authority:
        p1_claims, authority_failures = explicit_p1_claims_from_agentic_authority(agentic_authority)
    else:
        p1_claims, authority_failures = explicit_p1_claims(p1_claim_control)
    if p1_commitment_authority is not None and not p1_commitment_authority_is_valid(
        p1_commitment_authority
    ):
        authority_failures.append("p1_commitment_authority_snapshot_invalid")
    if p2_claim_control_verification is not None and not phase2_claim_control_verification_is_valid(
        p2_claim_control_verification
    ):
        authority_failures.append("phase2_claim_control_verification_invalid")
    operation_rows = _operation_rows(operation_source_obligations, "operations")
    resolution_rows = _operation_rows(p1_operation_resolutions, "resolutions")
    semantic_rows = _operation_rows(operation_semantics, "operations")

    operation_by_id = {
        str(row.get("operation_id") or "").strip(): row
        for row in operation_rows
        if str(row.get("operation_id") or "").strip()
    }
    semantics_by_operation = {
        str(row.get("operation_id") or "").strip(): row
        for row in semantic_rows
        if str(row.get("operation_id") or "").strip()
    }
    p2_absorbed_p1_claim_ids: set[str] = set()
    report = p2_claim_control_report if isinstance(p2_claim_control_report, dict) else {}
    artifacts = report.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if str(artifact.get("claim_control_acceptance_status") or artifact.get("overall_status") or "").strip().lower() != "pass":
                continue
            p2_absorbed_p1_claim_ids.update(string_list(artifact.get("declared_upstream_p1_claim_refs")))

    exact_operations_by_p1: dict[str, set[str]] = {}
    for operation_id, row in operation_by_id.items():
        for claim_id in string_list(row.get("upstream_p1_trace_ids")):
            exact_operations_by_p1.setdefault(claim_id, set()).add(operation_id)
    for row in resolution_rows:
        if str(row.get("resolution_status") or "").strip() != EXACT_P1_P2_RESOLUTION_STATUS:
            continue
        operation_id = str(row.get("operation_id") or "").strip()
        if not operation_id:
            continue
        for claim_id in string_list(row.get("p1_trace_ids")):
            exact_operations_by_p1.setdefault(claim_id, set()).add(operation_id)

    authored_ledger = (
        p2_commitment_disposition_ledger
        if isinstance(p2_commitment_disposition_ledger, dict)
        else {}
    )
    if authored_ledger and not p2_commitment_disposition_ledger_is_valid(authored_ledger):
        authority_failures.append("p2_commitment_disposition_ledger_invalid")

    commitments: list[dict[str, Any]] = []
    p1_mapped_operations: set[str] = set()
    for claim in p1_claims:
        claim_id = claim["claim_id"]
        authored_disposition = _authored_p2_disposition(claim=claim, ledger=authored_ledger)
        if authored_ledger and authored_disposition is None:
            authority_failures.append(f"p2_commitment_disposition_missing:{claim_id}")
        operation_ids = sorted(exact_operations_by_p1.get(claim_id, set()))
        contract_ids = sorted(
            {
                str(operation_by_id[operation_id].get("contract_trace_id") or "").strip()
                for operation_id in operation_ids
                if operation_id in operation_by_id
                and str(operation_by_id[operation_id].get("contract_trace_id") or "").strip()
            }
        )
        missing_contract_operations = [
            operation_id
            for operation_id in operation_ids
            if not str(operation_by_id.get(operation_id, {}).get("contract_trace_id") or "").strip()
        ]
        if authored_disposition is not None:
            operation_ids = list(authored_disposition["p2_operation_ids"])
            contract_ids = list(authored_disposition["p2_contract_ids"])
            p1_mapped_operations.update(operation_ids)
            commitments.append(
                {
                    "commitment_id": f"p1:{claim_id}",
                    "origin_phase": "P1",
                    "authority_ids": [claim_id],
                    "commitment_kind": claim["kind"],
                    "commitment_text": claim["text"],
                    "source_refs": claim["source_refs"],
                    **authored_disposition,
                }
            )
            continue
        if not operation_ids and claim_id in p2_absorbed_p1_claim_ids:
            disposition = "explicit-unresolved"
            owner = "P2"
            realization_requirement = "preserve-review-bound"
            reason = (
                "P2 claim-control proves explicit absorption, but no exact operation or non-operation realization identity is available"
            )
        elif not operation_ids or missing_contract_operations:
            disposition = "local-return-required"
            owner = "P2"
            realization_requirement = "upstream-return-required"
            reason = (
                "P1 commitment has no exact P2 disposition"
                if not operation_ids
                else "P1 commitment maps to a P2 operation without an explicit contract trace"
            )
        else:
            p1_mapped_operations.update(operation_ids)
            review_bound_operations = [
                operation_id
                for operation_id in operation_ids
                if str(semantics_by_operation.get(operation_id, {}).get("semantic_status") or "") != "resolved"
            ]
            if review_bound_operations:
                disposition = "explicit-unresolved"
                owner = "P2"
                realization_requirement = "preserve-review-bound"
                reason = "P2 contract is explicit, but one or more semantic decisions remain review-bound"
            else:
                disposition = "accepted-p2-contract"
                owner = "P3"
                realization_requirement = "exact-realization-required"
                reason = "P1 commitment has exact P2 contract and resolved P2 semantic authority"
        commitments.append(
            {
                "commitment_id": f"p1:{claim_id}",
                "origin_phase": "P1",
                "authority_ids": [claim_id],
                "commitment_kind": claim["kind"],
                "commitment_text": claim["text"],
                "source_refs": claim["source_refs"],
                "p2_operation_ids": operation_ids,
                "p2_contract_ids": contract_ids,
                "p2_operation_contracts": {
                    operation_id: str(operation_by_id.get(operation_id, {}).get("contract_trace_id") or "").strip()
                    for operation_id in operation_ids
                    if str(operation_by_id.get(operation_id, {}).get("contract_trace_id") or "").strip()
                },
                "p2_disposition": disposition,
                "disposition_owner": owner,
                "disposition_reason": reason,
                "p3_realization_requirement": realization_requirement,
                "semantic_statuses": {
                    operation_id: str(semantics_by_operation.get(operation_id, {}).get("semantic_status") or "missing")
                    for operation_id in operation_ids
                },
            }
        )

    for operation_id, row in sorted(operation_by_id.items()):
        contract_id = str(row.get("contract_trace_id") or "").strip()
        if not contract_id or operation_id in p1_mapped_operations:
            continue
        semantic_status = str(semantics_by_operation.get(operation_id, {}).get("semantic_status") or "missing")
        commitments.append(
            {
                "commitment_id": f"p2:{contract_id}",
                "origin_phase": "P2",
                "authority_ids": [contract_id],
                "commitment_kind": "p2-operation-contract",
                "commitment_text": str(row.get("classification_rationale") or operation_id).strip(),
                "source_refs": string_list(row.get("source_files")),
                "p2_operation_ids": [operation_id],
                "p2_contract_ids": [contract_id],
                "p2_operation_contracts": {operation_id: contract_id},
                "p2_disposition": "accepted-p2-contract" if semantic_status == "resolved" else "explicit-unresolved",
                "disposition_owner": "P3" if semantic_status == "resolved" else "P2",
                "disposition_reason": (
                    "Explicit valid P2-only contract requires exact P3 realization"
                    if semantic_status == "resolved"
                    else "Explicit P2-only contract is retained with unresolved semantic authority"
                ),
                "p3_realization_requirement": (
                    "exact-realization-required" if semantic_status == "resolved" else "preserve-review-bound"
                ),
                "semantic_statuses": {operation_id: semantic_status},
            }
        )

    counts = {
        "p1_explicit_commitments": len(p1_claims),
        "p2_only_commitments": len([row for row in commitments if row["origin_phase"] == "P2"]),
        "commitment_union": len(commitments),
        "local_return_required": len(
            [row for row in commitments if row["p2_disposition"] == "local-return-required"]
        ),
        "explicit_unresolved": len([row for row in commitments if row["p2_disposition"] == "explicit-unresolved"]),
        "exact_realization_required": len(
            [row for row in commitments if row["p3_realization_requirement"] == "exact-realization-required"]
        ),
    }
    status = "commitment-union-built"
    if not p1_claims:
        authority_failures.append("no_explicit_p1_commitments")
    if authority_failures:
        status = "not-evaluable"
        authority_failures = sorted(set(authority_failures))
    payload = {
        "schema_version": COMMITMENT_UNION_SCHEMA,
        "status": status,
        "denominator_rule": "ExplicitValid(P1) union ExplicitValid(P2)",
        "authority_failures": authority_failures,
        "source_receipts": {
            "p1_commitment_authority": str(
                (p1_commitment_authority or {}).get("content_digest") or ""
            ),
            "p1_claim_control": canonical_digest(p1_claim_control),
            "p1_agentic_product_authority": str(agentic_authority.get("content_digest") or ""),
            "phase2_claim_control_verification": str(
                (p2_claim_control_verification or {}).get("content_digest") or ""
            ),
            "operation_source_obligations": canonical_digest(operation_source_obligations),
            "p1_operation_resolutions": canonical_digest(p1_operation_resolutions),
            "operation_semantics": canonical_digest(operation_semantics),
            "p2_claim_control_report": canonical_digest(
                p2_claim_control_report if isinstance(p2_claim_control_report, dict) else {}
            ),
            "p2_commitment_disposition_ledger": str(authored_ledger.get("content_digest") or ""),
            "p2_agentic_architecture_decision": str(authored_ledger.get("decision_digest") or ""),
        },
        "counts": counts,
        "commitments": commitments,
        "claim_ceiling": (
            "This derived union binds accepted P1 claim authority and explicit P2 contracts. "
            "It does not create semantic truth, score L2/L2+, or authorize P3 to guess unresolved decisions."
        ),
    }
    payload["content_digest"] = canonical_digest({key: payload[key] for key in payload if key != "content_digest"})
    return payload


def verify_semantic_commitment_union(
    *,
    persisted_union: dict[str, Any],
    p1_claim_control: dict[str, Any],
    operation_source_obligations: dict[str, Any],
    p1_operation_resolutions: dict[str, Any],
    operation_semantics: dict[str, Any],
    p2_claim_control_report: dict[str, Any] | None = None,
    p1_commitment_authority: dict[str, Any] | None = None,
    p2_claim_control_verification: dict[str, Any] | None = None,
    p2_commitment_disposition_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rebuilt_union = build_semantic_commitment_union(
        p1_claim_control=p1_claim_control,
        operation_source_obligations=operation_source_obligations,
        p1_operation_resolutions=p1_operation_resolutions,
        operation_semantics=operation_semantics,
        p2_claim_control_report=p2_claim_control_report,
        p1_commitment_authority=p1_commitment_authority,
        p2_claim_control_verification=p2_claim_control_verification,
        p2_commitment_disposition_ledger=p2_commitment_disposition_ledger,
    )
    persisted_digest = str(persisted_union.get("content_digest") or "")
    rebuilt_digest = str(rebuilt_union.get("content_digest") or "")
    persisted_self_valid = content_digest_is_valid(
        persisted_union,
        schema_version=COMMITMENT_UNION_SCHEMA,
    )
    source_receipts_match = persisted_union.get("source_receipts") == rebuilt_union.get("source_receipts")
    verified = bool(
        persisted_self_valid
        and str(persisted_union.get("status") or "") == "commitment-union-built"
        and str(rebuilt_union.get("status") or "") == "commitment-union-built"
        and persisted_digest == rebuilt_digest
        and source_receipts_match
    )
    if not persisted_union:
        status = "not-evaluable"
        reason = "persisted semantic commitment union is missing"
    elif not persisted_self_valid:
        status = "invalid"
        reason = "persisted semantic commitment union schema or content digest is invalid"
    elif str(rebuilt_union.get("status") or "") != "commitment-union-built":
        status = "not-evaluable"
        reason = "source authority cannot produce an evaluable commitment union"
    elif persisted_digest != rebuilt_digest or not source_receipts_match:
        status = "mismatch"
        reason = "persisted semantic commitment union does not match source-rebuilt authority"
    else:
        status = "verified"
        reason = "persisted union matches source-rebuilt P1/P2 authority"
    receipt = {
        "schema_version": COMMITMENT_UNION_VERIFICATION_SCHEMA,
        "status": status,
        "verified": verified,
        "reason": reason,
        "persisted_digest": persisted_digest,
        "rebuilt_digest": rebuilt_digest,
        "source_receipts": rebuilt_union.get("source_receipts", {}),
        "claim_ceiling": (
            "This receipt verifies that the persisted commitment union matches current P1/P2 authority surfaces. "
            "It does not judge semantic quality or establish L2/L2+."
        ),
    }
    receipt["content_digest"] = canonical_digest(
        {key: receipt[key] for key in receipt if key != "content_digest"}
    )
    return {
        "verification": receipt,
        "rebuilt_union": rebuilt_union,
    }


def commitment_union_verification_is_valid(receipt: dict[str, Any]) -> bool:
    return bool(
        content_digest_is_valid(receipt, schema_version=COMMITMENT_UNION_VERIFICATION_SCHEMA)
        and receipt.get("verified") is True
        and receipt.get("status") == "verified"
        and str(receipt.get("persisted_digest") or "")
        and receipt.get("persisted_digest") == receipt.get("rebuilt_digest")
    )


def _binding_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows", [])
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def build_semantic_realization_ledger(
    *,
    commitment_union: dict[str, Any],
    implementation_bindings: dict[str, Any],
    trace_registry_final: dict[str, Any],
    commitment_union_verification: dict[str, Any] | None = None,
    authority_source_paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind the denominator to exact P3 implementation and evidence."""

    verification = (
        commitment_union_verification
        if isinstance(commitment_union_verification, dict)
        else {}
    )
    source_paths = dict(authority_source_paths) if isinstance(authority_source_paths, dict) else {}
    verification_valid = commitment_union_verification_is_valid(verification)
    if (
        not verification_valid
        or not content_digest_is_valid(commitment_union, schema_version=COMMITMENT_UNION_SCHEMA)
        or str(commitment_union.get("status") or "") != "commitment-union-built"
    ):
        payload = {
            "schema_version": REALIZATION_LEDGER_SCHEMA,
            "status": "invalid-commitment-union",
            "denominator_rule": "ExplicitValid(P1) union ExplicitValid(P2)",
            "source_commitment_union_digest": str(commitment_union.get("content_digest") or ""),
            "counts": {"commitments": 1, "realized": 0, "review_bound": 0, "blocking": 1},
            "results": [
                {
                    "commitment_id": "authority:semantic-commitment-union",
                    "origin_phase": "P2",
                    "authority_ids": [],
                    "p2_operation_ids": [],
                    "p2_contract_ids": [],
                    "p2_disposition": "invalid-authority",
                    "status": "invalid-authority",
                    "blocking": True,
                    "reason": (
                        str(verification.get("reason") or "semantic commitment union source verification is missing or invalid")
                        if not verification_valid
                        else (
                            "semantic commitment union is not evaluable"
                            if str(commitment_union.get("status") or "") == "not-evaluable"
                            else "semantic commitment union schema or content digest is invalid"
                        )
                    ),
                    "operation_results": [],
                }
            ],
            "blocking_commitment_ids": ["authority:semantic-commitment-union"],
            "review_bound_commitment_ids": [],
            "commitment_union_verification": verification,
            "authority_source_paths": source_paths,
            "commitment_union_verification_digest": str(verification.get("content_digest") or ""),
            "claim_ceiling": "Invalid or unverified P2 commitment authority blocks P3 realization claims.",
        }
        payload["content_digest"] = canonical_digest({key: payload[key] for key in payload if key != "content_digest"})
        return payload

    bindings_by_operation: dict[str, list[dict[str, Any]]] = {}
    for row in _binding_rows(implementation_bindings):
        operation_id = str(row.get("operation_id") or "").strip()
        if operation_id:
            bindings_by_operation.setdefault(operation_id, []).append(row)

    non_operation_bindings_by_id: dict[str, list[dict[str, Any]]] = {}
    raw_non_operation_rows = implementation_bindings.get("non_operation_rows", [])
    if isinstance(raw_non_operation_rows, list):
        for raw_row in raw_non_operation_rows:
            if not isinstance(raw_row, dict):
                continue
            realization_id = str(raw_row.get("non_operation_realization_id") or "").strip()
            if realization_id:
                non_operation_bindings_by_id.setdefault(realization_id, []).append(dict(raw_row))

    confirmed_trace_by_operation: dict[str, list[dict[str, Any]]] = {}
    for row in _binding_rows(trace_registry_final):
        evidence = row.get("trace_link_evidence", {}) if isinstance(row.get("trace_link_evidence"), dict) else {}
        operation_id = str(evidence.get("operation_id") or row.get("operation_id") or "").strip()
        if operation_id and str(row.get("final_resolution") or "").strip() == "confirmed":
            confirmed_trace_by_operation.setdefault(operation_id, []).append(row)

    results: list[dict[str, Any]] = []
    for commitment in commitment_union.get("commitments", []):
        if not isinstance(commitment, dict):
            continue
        commitment_id = str(commitment.get("commitment_id") or "").strip()
        requirement = str(commitment.get("p3_realization_requirement") or "").strip()
        operation_ids = string_list(commitment.get("p2_operation_ids"))
        operation_contracts = (
            dict(commitment.get("p2_operation_contracts", {}))
            if isinstance(commitment.get("p2_operation_contracts"), dict)
            else {}
        )
        fallback_contract_ids = set(string_list(commitment.get("p2_contract_ids")))
        non_operation_ids = string_list(commitment.get("p2_non_operation_ids"))
        if not non_operation_ids and isinstance(commitment.get("p2_non_operation_realizations"), dict):
            non_operation_ids = [str(key).strip() for key in commitment["p2_non_operation_realizations"] if str(key).strip()]
        operation_results: list[dict[str, Any]] = []
        non_operation_results: list[dict[str, Any]] = []
        if requirement == "upstream-return-required":
            status = "upstream-return-required"
            blocking = True
            reason = "P1 commitment has no accepted exact P2 disposition"
        elif requirement == "preserve-review-bound":
            status = "review-bound"
            blocking = False
            reason = "P2 explicitly retained unresolved semantic authority; P3 must not fake realization"
        else:
            for operation_id in operation_ids:
                expected_contract_ids = {
                    str(operation_contracts.get(operation_id) or "").strip()
                } - {""}
                if not expected_contract_ids:
                    expected_contract_ids = set(fallback_contract_ids)
                operation_bindings = bindings_by_operation.get(operation_id, [])
                operation_traces = confirmed_trace_by_operation.get(operation_id, [])
                bindings = [
                    row
                    for row in operation_bindings
                    if str(row.get("source_id") or "").strip() in expected_contract_ids
                ]
                traces = [
                    row
                    for row in operation_traces
                    if str(row.get("source_id") or "").strip() in expected_contract_ids
                ]
                exact_targets = sorted(
                    {
                        target
                        for binding in bindings
                        for target in string_list(binding.get("implementation_targets"))
                    }
                )
                evidence_refs = sorted(
                    {
                        target
                        for binding in bindings
                        for target in string_list(binding.get("runtime_evidence_refs"))
                    }
                )
                if not expected_contract_ids:
                    operation_status = "missing-contract-authority"
                elif (operation_bindings or operation_traces) and not bindings and not traces:
                    operation_status = "contract-misbound-realization"
                elif not bindings:
                    operation_status = "missing-realization"
                elif not exact_targets:
                    operation_status = "missing-implementation-target"
                elif not traces or not evidence_refs:
                    operation_status = "evidence-incomplete"
                else:
                    operation_status = "realized"
                operation_results.append(
                    {
                        "operation_id": operation_id,
                        "status": operation_status,
                        "expected_contract_ids": sorted(expected_contract_ids),
                        "observed_binding_source_ids": sorted(
                            {
                                str(row.get("source_id") or "").strip()
                                for row in operation_bindings
                                if str(row.get("source_id") or "").strip()
                            }
                        ),
                        "observed_trace_source_ids": sorted(
                            {
                                str(row.get("source_id") or "").strip()
                                for row in operation_traces
                                if str(row.get("source_id") or "").strip()
                            }
                        ),
                        "implementation_targets": exact_targets,
                        "runtime_evidence_refs": evidence_refs,
                        "confirmed_trace_ids": sorted(
                            str(row.get("source_id") or "").strip() for row in traces if str(row.get("source_id") or "").strip()
                        ),
                    }
                )
            for realization_id in non_operation_ids:
                candidate_bindings = non_operation_bindings_by_id.get(realization_id, [])
                exact_targets = sorted(
                    {
                        target
                        for binding in candidate_bindings
                        for target in string_list(binding.get("implementation_targets"))
                    }
                )
                declared_tests = {
                    target
                    for binding in candidate_bindings
                    for target in string_list(binding.get("test_targets"))
                }
                runtime_tests = {
                    target
                    for binding in candidate_bindings
                    for target in string_list(binding.get("runtime_test_refs"))
                }
                behavior_test_refs = sorted(
                    target
                    for target in declared_tests.intersection(runtime_tests)
                    if target.startswith("tests/unit/api/")
                )
                evidence_refs = sorted(
                    {
                        target
                        for binding in candidate_bindings
                        for target in string_list(binding.get("runtime_evidence_refs"))
                        if str(target).lower().endswith(".json")
                    }
                )
                decision_identities = {
                    (
                        str(binding.get("implementation_decision_id") or "").strip(),
                        str(binding.get("implementation_decision_digest") or "").strip(),
                    )
                    for binding in candidate_bindings
                }
                exact_decision_identity = bool(
                    len(candidate_bindings) == 1
                    and len(decision_identities) == 1
                    and all(next(iter(decision_identities), ("", "")))
                )
                if not candidate_bindings:
                    non_operation_status = "missing-realization"
                elif not exact_decision_identity:
                    non_operation_status = "identity-ambiguous"
                elif not exact_targets:
                    non_operation_status = "missing-implementation-target"
                elif not behavior_test_refs:
                    non_operation_status = "behavior-evidence-missing"
                elif not evidence_refs:
                    non_operation_status = "evidence-incomplete"
                else:
                    non_operation_status = "realized"
                non_operation_results.append(
                    {
                        "non_operation_realization_id": realization_id,
                        "status": non_operation_status,
                        "implementation_targets": exact_targets,
                        "runtime_test_refs": behavior_test_refs,
                        "runtime_evidence_refs": evidence_refs,
                    }
                )

            failed = [
                row
                for row in [*operation_results, *non_operation_results]
                if row["status"] != "realized"
            ]
            if not operation_ids and not non_operation_ids:
                status = "missing-realization"
                blocking = True
                reason = "Realization-required commitment has no exact P2 operation or non-operation identity"
            elif failed:
                status = "realization-incomplete"
                blocking = True
                reason = "One or more exact P2 operations/non-operations lack implementation or behavioral evidence linkage"
            else:
                status = "realized"
                blocking = False
                reason = "All exact P2 operations/non-operations have implementation targets and retained behavioral evidence"
        results.append(
            {
                "commitment_id": commitment_id,
                "origin_phase": commitment.get("origin_phase", ""),
                "authority_ids": string_list(commitment.get("authority_ids")),
                "p2_operation_ids": operation_ids,
                "p2_contract_ids": string_list(commitment.get("p2_contract_ids")),
                "p2_non_operation_ids": non_operation_ids,
                "p2_disposition": commitment.get("p2_disposition", ""),
                "status": status,
                "blocking": blocking,
                "reason": reason,
                "operation_results": operation_results,
                "non_operation_results": non_operation_results,
            }
        )

    blocking_rows = [row for row in results if row["blocking"]]
    review_bound_rows = [row for row in results if row["status"] == "review-bound"]
    realized_rows = [row for row in results if row["status"] == "realized"]
    payload = {
        "schema_version": REALIZATION_LEDGER_SCHEMA,
        "status": "semantic-realization-ledger-built",
        "denominator_rule": commitment_union.get("denominator_rule", "ExplicitValid(P1) union ExplicitValid(P2)"),
        "source_commitment_union_digest": commitment_union.get("content_digest", ""),
        "commitment_union_verification": verification,
        "authority_source_paths": source_paths,
        "commitment_union_verification_digest": str(verification.get("content_digest") or ""),
        "source_receipts": {
            "commitment_union": str(commitment_union.get("content_digest") or ""),
            "implementation_bindings": canonical_digest(implementation_bindings),
            "trace_registry_final": canonical_digest(trace_registry_final),
        },
        "counts": {
            "commitments": len(results),
            "realized": len(realized_rows),
            "review_bound": len(review_bound_rows),
            "blocking": len(blocking_rows),
        },
        "results": results,
        "blocking_commitment_ids": [row["commitment_id"] for row in blocking_rows],
        "review_bound_commitment_ids": [row["commitment_id"] for row in review_bound_rows],
        "claim_ceiling": (
            "This ledger proves exact identity linkage across existing P1/P2/P3 surfaces. "
            "It does not judge semantic quality, create implementation truth, or establish meets-L2/L2+."
        ),
    }
    payload["content_digest"] = canonical_digest({key: payload[key] for key in payload if key != "content_digest"})
    return payload


def load_evidence_dispositions(path: Path | None) -> list[dict[str, Any]]:
    payload = load_json_object(path)
    if payload.get("schema_version") != EVIDENCE_DISPOSITION_SCHEMA:
        return []
    items = payload.get("items", [])
    return [dict(row) for row in items if isinstance(row, dict)] if isinstance(items, list) else []


def accepted_environment_disposition(
    *,
    evidence_path: Path,
    relative_path: str,
    dispositions: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    if not evidence_path.exists() or evidence_path.is_symlink():
        return None
    digest = file_digest(evidence_path)
    for row in dispositions:
        if str(row.get("evidence_path") or "").strip() != relative_path:
            continue
        if str(row.get("evidence_digest") or "").strip() != digest:
            continue
        if str(row.get("status") or "").strip() != "accepted":
            continue
        if str(row.get("classification") or "").strip() not in ENVIRONMENT_DISPOSITION_CLASSES:
            continue
        if not all(
            str(row.get(key) or "").strip()
            for key in ("decision_reference", "owner", "reason", "retry_route", "claim_ceiling")
        ):
            continue
        challenge = row.get("bounded_challenge")
        try:
            p4_binding = importlib.import_module("phase4.bounded_challenge_binding")
            p4_binding.validate_p4_evidence_challenge_binding(row=row)
        except (ImportError, AttributeError, TypeError, ValueError):
            continue
        accepted = dict(row)
        accepted["bounded_challenge"] = challenge_summary(
            challenge if isinstance(challenge, dict) else {}
        )
        accepted["evidence_challenge_binding_digest"] = str(
            (row.get("evidence_challenge_binding") or {}).get("content_digest") or ""
        )
        accepted["verification"] = "caller-asserted-accepted-exact-evidence-bound-not-independently-verified"
        return accepted
    return None
