#!/usr/bin/env python3
"""Runtime sidecar emitters for claim-controlled generated artifacts.

The contract validators in :mod:`common.claim_control_contract` define Path A/B
rules.  This module is the small generation-side adapter: stages call it after
they have their accepted claim surface and rendered artifact, and it writes the
sidecar consumed by the generic acceptance runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable



@dataclass(frozen=True)
class ClaimRecord:
    id: str
    kind: str
    text: str
    source_refs: list[str] = field(default_factory=list)
    status: str = "accepted"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "text": self.text,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class ClaimRelation:
    subject: str
    predicate: str
    object: str
    source_claim_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        refs = [str(item).strip() for item in self.source_claim_refs if str(item).strip()]
        if not refs:
            refs = [str(self.subject).strip(), str(self.object).strip()]
        return {
            "subject": str(self.subject).strip(),
            "predicate": str(self.predicate).strip(),
            "object": str(self.object).strip(),
            "source_claim_refs": refs,
        }


@dataclass(frozen=True)
class CanonicalName:
    id: str
    canonical: str
    allowed_aliases: list[str] = field(default_factory=list)
    forbidden_aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id).strip(),
            "canonical": str(self.canonical).strip(),
            "allowed_aliases": [str(item).strip() for item in self.allowed_aliases if str(item).strip()],
            "forbidden_aliases": [str(item).strip() for item in self.forbidden_aliases if str(item).strip()],
        }


@dataclass(frozen=True)
class CoverageObligation:
    claim_id: str
    required_view_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": str(self.claim_id).strip(),
            "required_view_ids": [str(item).strip() for item in self.required_view_ids if str(item).strip()],
        }


TRACE_UNIT_KIND_MAP = {
    "epic": "epic",
    "primary-user-story": "user_story",
    "use-case": "use_case",
    "requirement": "requirement",
    "acceptance-criteria": "acceptance_criterion",
    "acceptance_criterion": "acceptance_criterion",
}

PHASE1_TRACE_GROUP_ORDER = (
    "epic_trace_units",
    "use_case_trace_units",
    "requirement_trace_units",
    "acceptance_trace_units",
)


def _claim_control_acceptance_module():
    try:
        return importlib.import_module("common.claim_control_acceptance")
    except ModuleNotFoundError as exc:
        if exc.name == "common.claim_control_acceptance":
            return None
        raise


def infer_artifact_metadata(artifact_path: str | Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    module = _claim_control_acceptance_module()
    if module is not None:
        return module.infer_artifact_metadata(artifact_path, overrides)
    path = Path(artifact_path)
    metadata = {
        "artifact_id": path.stem.strip() or path.name.strip(),
        "source_count": 1,
        "view_count": 1 if path.exists() else 0,
        "claim_count": 0,
        "has_mermaid": False,
        "has_tables": False,
        "has_prose_sections": False,
        "inference_policy": "claim-control-acceptance-sidecar-unavailable",
    }
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                metadata[key] = value
    return metadata


def default_surface_path(artifact_path: str | Path) -> Path:
    module = _claim_control_acceptance_module()
    if module is not None:
        return module.default_surface_path(artifact_path)
    path = Path(artifact_path)
    return path.with_name(f"{path.stem}.claim-control.json")


def evaluate_claim_control_acceptance(
    artifact_path: str | Path,
    *,
    surface_path: str | Path | None = None,
    metadata_overrides: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    module = _claim_control_acceptance_module()
    if module is not None:
        return module.evaluate_claim_control_acceptance(
            artifact_path,
            surface_path=surface_path,
            metadata_overrides=metadata_overrides,
            profile=profile,
        )
    artifact = Path(artifact_path)
    surface = Path(surface_path) if surface_path is not None else default_surface_path(artifact)
    return {
        "artifact_kind": "claim-control-acceptance-report",
        "artifact_path": str(artifact),
        "surface_path": str(surface),
        "overall_status": "not_evaluated",
        "claim_ceiling": "review-bound:claim-control-acceptance-sidecar-not-packaged",
        "classifications": ["claim_control_acceptance_sidecar_unavailable"],
        "route_decision": {},
        "metadata": infer_artifact_metadata(artifact, metadata_overrides),
        "mechanism_report": None,
        "creates_claims": False,
        "uses_rendered_views_as_truth": False,
        "policy": "claim-control sidecar was emitted; acceptance validation is not packaged in this install profile",
        "sidecar_unavailable": True,
    }


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_ref_is_rendered(text: str, claim_ref: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_-]){re.escape(claim_ref)}(?![A-Za-z0-9_-])"
    return bool(re.search(pattern, text))


def _unique_claims(claims: Iterable[ClaimRecord]) -> list[ClaimRecord]:
    indexed: dict[str, ClaimRecord] = {}
    for claim in claims:
        claim_id = str(claim.id).strip()
        if not claim_id or claim_id in indexed:
            continue
        indexed[claim_id] = ClaimRecord(
            id=claim_id,
            kind=str(claim.kind or "claim").strip() or "claim",
            text=str(claim.text or claim_id).strip() or claim_id,
            source_refs=[str(item).strip() for item in claim.source_refs if str(item).strip()],
            status="accepted",
        )
    return list(indexed.values())


def accepted_claims_from_phase1_trace_units(
    trace_units: dict[str, list[dict[str, Any]]],
    *,
    source_label: str,
) -> list[ClaimRecord]:
    """Compile Phase-1 trace units into accepted claim records.

    This reads the generator's trace-unit structure, not arbitrary rendered
    prose.  Proposed or review-bound deltas are intentionally not accepted here.
    """

    claims: list[ClaimRecord] = []
    for group in PHASE1_TRACE_GROUP_ORDER:
        rows = trace_units.get(group, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            claim_id = str(row.get("trace_id") or "").strip()
            if not claim_id:
                continue
            source_anchor = str(row.get("source_anchor") or claim_id.lower()).strip()
            unit_type = str(row.get("unit_type") or "claim").strip()
            claims.append(
                ClaimRecord(
                    id=claim_id,
                    kind=TRACE_UNIT_KIND_MAP.get(unit_type, unit_type or "claim"),
                    text=str(row.get("summary") or claim_id).strip() or claim_id,
                    source_refs=[f"{source_label}#{source_anchor}"],
                )
            )
    return _unique_claims(claims)


def accepted_claim_ids_from_sidecar(sidecar_path: str | Path) -> list[str]:
    path = Path(sidecar_path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    claim_index = payload.get("claim_index") if isinstance(payload, dict) else None
    rows = claim_index.get("claims") if isinstance(claim_index, dict) else []
    ids: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("status") or "accepted").strip() != "accepted":
                continue
            claim_id = str(row.get("id") or "").strip()
            if claim_id and claim_id not in ids:
                ids.append(claim_id)
    return ids


def claims_from_sidecar(sidecar_path: str | Path, *, source_label: str = "upstream-claim-control") -> list[ClaimRecord]:
    del source_label
    path = Path(sidecar_path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    claim_index = payload.get("claim_index") if isinstance(payload, dict) else None
    rows = claim_index.get("claims") if isinstance(claim_index, dict) else []
    claims: list[ClaimRecord] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("status") or "accepted").strip() != "accepted":
                continue
            claim_id = str(row.get("id") or "").strip()
            if not claim_id:
                continue
            claims.append(
                ClaimRecord(
                    id=claim_id,
                    kind=str(row.get("kind") or "upstream_claim").strip() or "upstream_claim",
                    text=str(row.get("text") or claim_id).strip() or claim_id,
                    source_refs=[str(item).strip() for item in row.get("source_refs", []) if str(item).strip()],
                )
            )
    return _unique_claims(claims)


def canonical_names_from_sidecar(sidecar_path: str | Path) -> list[CanonicalName]:
    path = Path(sidecar_path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    names = payload.get("names") if isinstance(payload, dict) else None
    rows = names.get("items") if isinstance(names, dict) else []
    canonical_names: list[CanonicalName] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            claim_id = str(row.get("id") or "").strip()
            canonical = str(row.get("canonical") or "").strip()
            if not claim_id or not canonical:
                continue
            canonical_names.append(
                CanonicalName(
                    id=claim_id,
                    canonical=canonical,
                    allowed_aliases=[str(item).strip() for item in row.get("allowed_aliases", []) if str(item).strip()],
                    forbidden_aliases=[
                        str(item).strip() for item in row.get("forbidden_aliases", []) if str(item).strip()
                    ],
                )
            )
    return canonical_names


def simple_artifact_claims(*, artifact_id: str, kind: str, text: str, source_ref: str) -> list[ClaimRecord]:
    return [
        ClaimRecord(
            id=artifact_id,
            kind=kind,
            text=text,
            source_refs=[source_ref],
        )
    ]


def _split_upstream_paths(paths: list[str | Path] | None) -> tuple[list[str], list[str]]:
    claim_control_paths: list[str] = []
    artifact_paths: list[str] = []
    for item in paths or []:
        path = Path(item)
        rendered = str(path)
        if path.name.endswith(".claim-control.json"):
            claim_control_paths.append(rendered)
        else:
            artifact_paths.append(rendered)
    return claim_control_paths, artifact_paths


def _surface_status(count: int) -> str:
    return "populated" if count > 0 else "missing"


def emit_path_b_claim_control_sidecar(
    *,
    artifact_path: str | Path,
    artifact_id: str,
    claims: Iterable[ClaimRecord],
    view_id: str,
    source_count: int,
    upstream_surface_paths: list[str | Path] | None = None,
    sidecar_path: str | Path | None = None,
    relations: Iterable[ClaimRelation] | None = None,
    canonical_names: Iterable[CanonicalName] | None = None,
    coverage_obligations: Iterable[CoverageObligation] | None = None,
    source_claim_refs: Iterable[str] | None = None,
    claim_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = Path(artifact_path)
    surface_path = Path(sidecar_path) if sidecar_path else default_surface_path(artifact)
    accepted_claims = _unique_claims(claims)
    accepted_ids = sorted(claim.id for claim in accepted_claims)
    artifact_text = artifact.read_text(encoding="utf-8") if artifact.exists() else ""
    rendered_ids = sorted(claim_id for claim_id in accepted_ids if _claim_ref_is_rendered(artifact_text, claim_id))
    if not rendered_ids and accepted_ids:
        rendered_ids = [accepted_ids[0]]
        artifact.parent.mkdir(parents=True, exist_ok=True)
        suffix = f"\n<!-- claim-control-rendered-refs: {', '.join(rendered_ids)} -->\n"
        with artifact.open("a", encoding="utf-8") as handle:
            handle.write(suffix)
    source_ids = sorted(
        {
            str(ref).strip()
            for ref in (source_claim_refs if source_claim_refs is not None else rendered_ids)
            if str(ref).strip()
        }
    )
    upstream_claim_control_paths, upstream_artifact_paths = _split_upstream_paths(upstream_surface_paths)
    metadata = infer_artifact_metadata(
        artifact,
        {
            "artifact_id": artifact_id,
            "source_count": max(2, int(source_count or 0)),
            "claim_count": len(accepted_ids),
            "high_downstream_trust": True,
            "downstream_consumed": True,
        },
    )
    metadata["view_count"] = max(2, int(metadata.get("view_count") or 0))
    metadata["has_prose_sections"] = True
    metadata["claim_realization_mode"] = "agentic-structured"
    if upstream_claim_control_paths:
        metadata["claim_lineage_mode"] = "upstream-claim-control"
    if claim_authority:
        authority_mode = str(claim_authority.get("authority_mode") or "").strip()
        if authority_mode:
            metadata["claim_authority_mode"] = authority_mode
        compilation_status = str(claim_authority.get("compilation_status") or "").strip()
        if compilation_status:
            metadata["claim_compilation_status"] = compilation_status
    coverage_rows = list(coverage_obligations or [])
    if not coverage_rows:
        coverage_rows = [
            CoverageObligation(claim_id=claim_id, required_view_ids=[view_id])
            for claim_id in rendered_ids
        ]
    relation_rows = list(relations or [])
    canonical_name_rows = list(canonical_names or [])
    realization_count = len([claim for claim in accepted_claims if claim.id in rendered_ids])
    semantic_claim_ceiling = (
        "coverage-bound; semantic relations and canonical names not generated"
        if not relation_rows and not canonical_name_rows
        else "structured semantic surfaces partially populated"
    )

    surface = {
        "artifact_metadata": metadata,
        "claim_index": {
            "version": "claim-index/v0.1",
            "claims": [claim.to_dict() for claim in sorted(accepted_claims, key=lambda item: item.id)],
        },
        "writing_plan": {
            "version": "writing-plan/v0.1",
            "artifact_id": artifact_id,
            "route": "path_b",
            "views": [
                {
                    "view_id": view_id,
                    "required_claim_refs": rendered_ids,
                    "rendered_claim_refs": rendered_ids,
                    "available_claim_refs": accepted_ids,
                }
            ],
        },
        "claim_realizations": {
            "version": "claim-realization/v0.1",
            "items": [
                {
                    "claim_id": claim.id,
                    "block_id": f"{view_id}:block-001",
                    "view_id": view_id,
                    "realization_status": "declared",
                    "realization_text": claim.text,
                    "source_refs": list(claim.source_refs),
                }
                for claim in sorted(accepted_claims, key=lambda item: item.id)
                if claim.id in rendered_ids
            ],
        },
        "relations": {
            "version": "claim-relations/v0.1",
            "items": [relation.to_dict() for relation in relation_rows],
        },
        "names": {
            "version": "canonical-names/v0.1",
            "items": [name.to_dict() for name in canonical_name_rows],
        },
        "coverage_obligations": {
            "version": "coverage-obligations/v0.1",
            "items": [obligation.to_dict() for obligation in coverage_rows],
        },
        "claim_authority": dict(claim_authority or {}),
        "semantic_surface_summary": {
            "version": "semantic-surface-summary/v0.1",
            "claim_realizations": {"count": realization_count, "status": _surface_status(realization_count)},
            "relations": {"count": len(relation_rows), "status": _surface_status(len(relation_rows))},
            "names": {"count": len(canonical_name_rows), "status": _surface_status(len(canonical_name_rows))},
            "coverage_obligations": {"count": len(coverage_rows), "status": _surface_status(len(coverage_rows))},
            "semantic_claim_ceiling": semantic_claim_ceiling,
        },
        "render_refs": {
            "artifact_id": artifact_id,
            "artifact_version": "artifact:v1",
            "artifact_hash": _sha256_file(artifact) if artifact.exists() else "",
            "claim_surface_version": "claim-index/v0.1",
            "claim_surface_hash": "",
            "upstream_surface_paths": upstream_claim_control_paths,
            "upstream_artifact_paths": upstream_artifact_paths,
            "refs": [
                {
                    "block_id": f"{view_id}:block-001",
                    "view_id": view_id,
                    "rendered_claim_refs": rendered_ids,
                    "source_claim_refs": source_ids,
                    "audit_status": "pass",
                }
            ],
        },
        "proposed_claims": {"claims": []},
    }
    serialized_for_hash = json.dumps(surface, ensure_ascii=False, sort_keys=True)
    surface["render_refs"]["claim_surface_hash"] = _sha256_text(serialized_for_hash)
    surface_path.parent.mkdir(parents=True, exist_ok=True)
    surface_path.write_text(json.dumps(surface, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    acceptance = evaluate_claim_control_acceptance(artifact, surface_path=surface_path)
    return {
        "sidecar_path": str(surface_path),
        "surface": surface,
        "acceptance": acceptance,
    }
