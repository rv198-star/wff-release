#!/usr/bin/env python3
"""Human-readable project knowledge projection for P3 Authority Delta.

The canonical semantic source remains the machine Authority Delta ledger. This
module renders and validates the fixed project-level Markdown view
`p3-realization-decisions.md` without mutating frozen P1/P2 authority.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
from typing import Any, Mapping

from common.agentic_decision_authority import canonical_digest, write_json_atomic
from phase3.agentic_implementation_authority import (
    build_authority_delta_ledger,
    validate_authority_delta_ledger,
    validate_authority_delta_records,
)


REALIZATION_DECISIONS_FILENAME = "p3-realization-decisions.md"
REALIZATION_DECISIONS_KIND = "p3-realization-decisions.v1"
REALIZATION_DECISIONS_BINDING_SCHEMA = "wff.p3-realization-decisions-binding.v1"
REALIZATION_DECISIONS_BINDING_RELATIVE_PATH = ".phase3-evidence/p3-realization-decisions-binding.json"
EKRI_INGESTION_ELIGIBILITY = "eligible-p3-realization-project-knowledge"
NO_MATERIAL_DECISIONS_TEXT = (
    "No material realization decisions beyond frozen P1/P2 authority were recorded for this P3 decision."
)
PROJECT_KNOWLEDGE_VISIBILITY = "project-knowledge"
IMPLEMENTATION_ONLY_VISIBILITY = "implementation-only"
KNOWLEDGE_SCOPES = ("product", "architecture", "ux", "implementation")


class P3RealizationDecisionsError(ValueError):
    pass


def resolve_project_artifact_root(
    *,
    phase2_root: Path,
    output_dir: Path,
    explicit_root: Path | None = None,
) -> Path:
    """Resolve the root that owns human lifecycle artifacts.

    Full-lifecycle orchestration uses sibling `phase-2` / `phase-3` directories,
    so their parent is the project artifact root. Direct P3 callers may provide
    `--project-artifact-root`; otherwise the P3 output root is the safe fallback.
    """
    phase2_root = phase2_root.resolve()
    output_dir = output_dir.resolve()
    if explicit_root is not None:
        return explicit_root.resolve()
    phase2_name = phase2_root.name.lower().replace("_", "-")
    phase3_name = output_dir.name.lower().replace("_", "-")
    if (
        phase2_root.parent == output_dir.parent
        and phase2_name in {"phase-2", "phase2"}
        and phase3_name in {"phase-3", "phase3"}
    ):
        return output_dir.parent.resolve()
    return output_dir


def prepare_authority_delta_ledger(
    *,
    authority: Mapping[str, Any],
    supplied_ledger: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if supplied_ledger is not None:
        ledger = dict(supplied_ledger)
        records = validate_authority_delta_ledger(ledger, authority=authority)
        _validate_human_projection_records(records)
        return ledger, records
    records = validate_authority_delta_records(
        authority.get("authority_delta_records", []),
        known_slice_ids=set((authority.get("slice_decisions") or {}).keys()),
    )
    _validate_human_projection_records(records)
    ledger = build_authority_delta_ledger(
        decision_id=str(authority.get("decision_id") or ""),
        decision_digest=str(authority.get("decision_digest") or ""),
        records=records,
    )
    return ledger, records


def persist_p3_realization_knowledge(
    *,
    phase2_root: Path,
    output_dir: Path,
    project_artifact_root: Path,
    authority: Mapping[str, Any],
    supplied_ledger: Mapping[str, Any] | None,
) -> dict[str, Any]:
    ledger, records = prepare_authority_delta_ledger(
        authority=authority,
        supplied_ledger=supplied_ledger,
    )
    ledger_path = output_dir.resolve() / ".phase3-evidence" / "p3-authority-delta-ledger.json"
    write_json_atomic(ledger_path, ledger)
    return write_p3_realization_decisions(
        phase2_root=phase2_root,
        phase3_root=output_dir,
        project_artifact_root=project_artifact_root,
        authority=authority,
        ledger=ledger,
        ledger_path=ledger_path,
        records=records,
    )


def write_p3_realization_decisions(
    *,
    phase2_root: Path,
    phase3_root: Path,
    project_artifact_root: Path,
    authority: Mapping[str, Any],
    ledger: Mapping[str, Any],
    ledger_path: Path,
    records: list[dict[str, Any]] | None = None,
    frozen_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    phase2_root = phase2_root.resolve()
    phase3_root = phase3_root.resolve()
    project_artifact_root = project_artifact_root.resolve()
    project_artifact_root.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_path.resolve()
    rows = records if records is not None else validate_authority_delta_ledger(ledger, authority=authority)
    _validate_human_projection_records(rows)
    output_path = project_artifact_root / REALIZATION_DECISIONS_FILENAME
    text = render_p3_realization_decisions(
        phase2_root=phase2_root,
        phase3_root=phase3_root,
        project_artifact_root=project_artifact_root,
        authority=authority,
        ledger=ledger,
        ledger_path=ledger_path,
        records=rows,
        frozen_facts=frozen_facts,
    )
    output_path.write_text(text, encoding="utf-8")
    validation = validate_p3_realization_decisions(
        path=output_path,
        authority=authority,
        ledger=ledger,
        records=rows,
    )
    if not validation["valid"]:
        raise P3RealizationDecisionsError(
            "P3 realization decisions projection is invalid: " + ", ".join(validation["errors"])
        )
    content_sha256 = _sha256_file(output_path)
    binding_path = phase3_root / REALIZATION_DECISIONS_BINDING_RELATIVE_PATH
    binding = {
        "schema_version": REALIZATION_DECISIONS_BINDING_SCHEMA,
        "status": "bound",
        "path": REALIZATION_DECISIONS_FILENAME,
        "project_artifact_root_relative": os.path.relpath(project_artifact_root, phase3_root),
        "content_sha256": content_sha256,
        "p3_decision_id": str(authority.get("decision_id") or ""),
        "p3_decision_digest": str(authority.get("decision_digest") or ""),
        "authority_delta_ledger_path": os.path.relpath(ledger_path, phase3_root),
        "authority_delta_content_digest": str(ledger.get("content_digest") or ""),
        "upstream_reconciled": False,
        "ekri_ingestion_eligibility": EKRI_INGESTION_ELIGIBILITY,
    }
    binding["content_digest"] = canonical_digest(binding)
    write_json_atomic(binding_path, binding)
    return {
        "status": "project-realization-knowledge-recorded",
        "path": str(output_path),
        "content_sha256": content_sha256,
        "binding_path": str(binding_path),
        "binding_content_digest": str(binding.get("content_digest") or ""),
        "project_artifact_root": str(project_artifact_root),
        "authority_delta_ledger_path": str(ledger_path),
        "authority_delta_content_digest": str(ledger.get("content_digest") or ""),
        "record_count": len(rows),
        "project_knowledge_count": sum(_human_visibility(row) == PROJECT_KNOWLEDGE_VISIBILITY for row in rows),
        "implementation_only_count": sum(_human_visibility(row) == IMPLEMENTATION_ONLY_VISIBILITY for row in rows),
        "upstream_reconciled": False,
        "ekri_ingestion_eligibility": EKRI_INGESTION_ELIGIBILITY,
        "claim_ceiling": (
            "Human-readable P3 realization knowledge only; frozen P1/P2 authority remains unchanged and no PRD/ESP backfill is performed."
        ),
    }


def render_p3_realization_decisions(
    *,
    phase2_root: Path,
    phase3_root: Path,
    project_artifact_root: Path,
    authority: Mapping[str, Any],
    ledger: Mapping[str, Any],
    ledger_path: Path,
    records: list[dict[str, Any]],
    frozen_facts: Mapping[str, Any] | None = None,
) -> str:
    esp_path = phase2_root / "engineering-spec-pack.md"
    prd_path = _discover_phase1_prd(phase2_root)
    projected = [row for row in records if _human_visibility(row) == PROJECT_KNOWLEDGE_VISIBILITY]
    implementation_only = [row for row in records if _human_visibility(row) == IMPLEMENTATION_ONLY_VISIBILITY]
    grouped: dict[str, list[dict[str, Any]]] = {scope: [] for scope in KNOWLEDGE_SCOPES}
    unresolved: list[dict[str, Any]] = []
    for row in projected:
        if str(row.get("local_application") or "") == "record-only" or (str(row.get("classification") or "") == "product-ambiguity" and row.get("gap_decision_contract") != "p3-gap-decisions-v1"):
            unresolved.append(row)
            continue
        grouped[_knowledge_scope(row)].append(row)

    lines = [
        "<!-- wff:p3-realization-decisions:v1 -->",
        "# P3 Realization Decisions",
        "",
        "This project-level document records material product, architecture, UX, and implementation decisions learned during P3 realization. It supplements the frozen PRD/ESP for human lookup but does not revise, replace, or silently backfill either upstream artifact.",
        "",
        "## Authority Baseline",
        "",
        f"- artifact_kind: `{REALIZATION_DECISIONS_KIND}`",
        f"- project_artifact_path: `{REALIZATION_DECISIONS_FILENAME}`",
        f"- PRD reference: `{_portable_ref(prd_path, project_artifact_root) if prd_path else 'carried-via-p2-handoff'}`",
        f"- ESP reference: `{_portable_ref(esp_path, project_artifact_root)}`",
        f"- P3 implementation decision id: `{str(authority.get('decision_id') or '')}`",
        f"- P3 implementation decision digest: `{str(authority.get('decision_digest') or '')}`",
        f"- Authority Delta ledger: `{_portable_ref(ledger_path, project_artifact_root)}`",
        f"- Authority Delta content digest: `{str(ledger.get('content_digest') or '')}`",
        "- upstream_reconciled: `false`",
        "- PRD backfill: `not-performed`",
        "- ESP backfill: `not-performed`",
        f"- EKRI ingestion eligibility: `{EKRI_INGESTION_ELIGIBILITY}`",
        "",
        "The machine Authority Delta ledger remains canonical for identity, exact binding, reconciliation status, and evidence references. This Markdown is its bounded human/project-knowledge projection.",
        "",
    ]

    if not records:
        lines.extend(["## Material Realization Decisions", "", NO_MATERIAL_DECISIONS_TEXT, ""])
    else:
        section_titles = {
            "product": "Product Decisions",
            "architecture": "Architecture Realization Decisions",
            "ux": "UX / User-visible State Decisions",
            "implementation": "Implementation Realization Decisions",
        }
        for scope in KNOWLEDGE_SCOPES:
            rows = grouped[scope]
            if not rows:
                continue
            lines.extend([f"## {section_titles[scope]}", ""])
            for row in rows:
                lines.extend(_render_delta_row(row, scope=scope))
        if unresolved:
            lines.extend(["## Unresolved Gaps / Next-Version Backport", ""])
            for row in unresolved:
                lines.extend(_render_delta_row(row, scope=_knowledge_scope(row)))
        if implementation_only:
            lines.extend(
                [
                    "## Implementation-only Authority Delta",
                    "",
                    "The following canonical delta records are intentionally not expanded into project knowledge because their `human_projection.visibility` is `implementation-only`:",
                    "",
                ]
            )
            for row in implementation_only:
                lines.append(f"- `{str(row.get('delta_id') or '')}` — {str(row.get('decision_statement') or '').strip()}")
            lines.append("")

    gap_rows = [row for row in records if row.get("gap_decision_contract") == "p3-gap-decisions-v1"]
    if gap_rows:
        lines.extend(["## Effective Truth / Next-Version Backport", "",
                      "Derived read view over the unchanged frozen sources and canonical P3 deltas; not a second authority.", ""])
        if frozen_facts is not None:
            from common.p3_gap_records import effective_truth
            view = effective_truth(frozen_facts, records)
            for identity, fact in sorted(view["facts"].items()):
                lines.append("- " + json.dumps({"id": identity, **fact}, ensure_ascii=False, sort_keys=True))
            for identity, review in sorted(view["decision_reviews"].items()):
                lines.append("- decision-review: " + json.dumps({"id": identity, **review}, ensure_ascii=False, sort_keys=True))
            for row in view["already_applied_rejected_decisions"]:
                lines.append("- already-applied-rejected: " + json.dumps(row, ensure_ascii=False, sort_keys=True))
        else:
            lines.append("- Full frozen fact values were not supplied to this projection; source references and explicit delta additions below are the available read view.")
            from common.p3_gap_records import decision_review
            for row in gap_rows:
                review = decision_review(row)
                rejected = review["status"] == "rejected"
                lines.append("- " + json.dumps({"delta_id": row["id"], "frozen_basis": row["basis"],
                    "review_status": review["status"], "already_applied_surfaces": review["already_applied_surfaces"],
                    "effective_confirmation_required": review["confirmation_required"],
                    "supersedes": [] if rejected else row.get("supersedes", []),
                    "facts": [] if rejected else row.get("new_facts", []) + row.get("inferred_facts", [])}, ensure_ascii=False))
        from common.p3_gap_records import decision_review
        for row in gap_rows:
            review = decision_review(row)
            lines.append("- backport: " + json.dumps({"delta_id":row["id"], "target":row["backport_target"],
                "basis":row["basis"], "upstream_reconciled":False, "review_status":review["status"],
                "already_applied_surfaces":review["already_applied_surfaces"],
                "confirmation_required":review["confirmation_required"]}, ensure_ascii=False))
        lines.append("")

    lines.extend(
        [
            "## Reconciliation Status",
            "",
            "- Frozen P1/P2 authority mutation performed: `false`",
            "- Upstream reconciliation status: `deferred-post-p3`",
            "- This document may be consumed by P4, later P3/change flows, maintainers, and EKRI as P3-realization project knowledge.",
            "- EKRI consumption must retain `upstream_reconciled=false` and must not promote this document to P1/P2 authority.",
            "",
            "## Claim Ceiling",
            "",
            "This document proves only that P3 realization decisions were retained in a stable human-readable project artifact. It does not prove PRD/ESP revision, UAT, owner sign-off, production readiness, or release authorization.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_p3_realization_decisions(
    *,
    path: Path,
    authority: Mapping[str, Any],
    ledger: Mapping[str, Any],
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not path.is_file() or path.is_symlink():
        return {"valid": False, "errors": ["p3-realization-decisions-missing"], "path": str(path)}
    text = path.read_text(encoding="utf-8")
    if "<!-- wff:p3-realization-decisions:v1 -->" not in text:
        errors.append("schema-marker-missing")
    expected_pairs = {
        "artifact_kind": REALIZATION_DECISIONS_KIND,
        "P3 implementation decision id": str(authority.get("decision_id") or ""),
        "P3 implementation decision digest": str(authority.get("decision_digest") or ""),
        "Authority Delta content digest": str(ledger.get("content_digest") or ""),
        "EKRI ingestion eligibility": EKRI_INGESTION_ELIGIBILITY,
    }
    for label, expected in expected_pairs.items():
        if not expected or not re.search(rf"^- {re.escape(label)}: `{re.escape(expected)}`$", text, flags=re.MULTILINE):
            errors.append(f"metadata-mismatch:{label}")
    for exact in (
        "- upstream_reconciled: `false`",
        "- PRD backfill: `not-performed`",
        "- ESP backfill: `not-performed`",
    ):
        if exact not in text:
            errors.append(f"boundary-missing:{exact.split(':', 1)[0].lstrip('- ')}")

    rows = records if records is not None else [dict(row) for row in ledger.get("records", []) if isinstance(row, Mapping)]
    if not rows:
        if NO_MATERIAL_DECISIONS_TEXT not in text:
            errors.append("no-material-decisions-declaration-missing")
    else:
        for row in rows:
            delta_id = str(row.get("delta_id") or "").strip()
            if not delta_id:
                errors.append("delta-id-missing")
                continue
            if _human_visibility(row) == PROJECT_KNOWLEDGE_VISIBILITY:
                if not re.search(rf"^### `{re.escape(delta_id)}`", text, flags=re.MULTILINE):
                    errors.append(f"project-knowledge-delta-missing:{delta_id}")
            elif f"- `{delta_id}` —" not in text:
                errors.append(f"implementation-only-delta-index-missing:{delta_id}")
    return {
        "valid": not errors,
        "errors": errors,
        "path": str(path),
        "content_sha256": _sha256_file(path),
        "record_count": len(rows),
    }


def _render_delta_row(row: Mapping[str, Any], *, scope: str) -> list[str]:
    delta_id = str(row.get("delta_id") or "").strip()
    projection = row.get("human_projection") if isinstance(row.get("human_projection"), Mapping) else {}
    title = str(projection.get("title") or "").strip() or _default_title(row)
    evidence = [str(value).strip() for value in row.get("evidence_refs", []) if str(value).strip()]
    gap_lines = []
    if row.get("gap_decision_contract") == "p3-gap-decisions-v1":
        from common.p3_gap_records import validate_gap_record
        validate_gap_record(row)
        fields = ("level", "trigger", "question", "basis", "rule", "alternatives", "reasoning", "rationale",
                  "reversible", "affected_surfaces", "new_facts", "inferred_facts", "sensitivity",
                  "confirmation_required", "backport_target", "supersedes")
        gap_lines = ["- " + key + ": " + json.dumps(row[key], ensure_ascii=False) for key in fields if key in row]
        gap_lines += ["- effective truth: frozen source IDs/digests above + this delta; only explicit T2 supersedes applies",
                      "- next-version backport: " + str(row["backport_target"]), "- upstream_reconciled: `false`"]
    return [
        f"### `{delta_id}` — {title}",
        "",
        f"- knowledge_scope: `{scope}`",
        f"- classification: `{str(row.get('classification') or '')}`",
        f"- source_slice_id: `{str(row.get('source_slice_id') or '')}`",
        f"- affected_upstream_authority: `{str(row.get('affected_authority') or '')}`",
        f"- local_application: `{str(row.get('local_application') or '')}`",
        f"- reconciliation_status: `{str(row.get('reconciliation_status') or '')}`",
        "- applied_upstream: `false`",
        f"- finding: {str(row.get('finding') or '').strip()}",
        f"- decision: {str(row.get('decision_statement') or '').strip()}",
        *gap_lines,
        f"- evidence: {', '.join(f'`{item}`' for item in evidence)}",
        f"- claim_ceiling: {str(row.get('claim_ceiling') or '').strip()}",
        "",
    ]


def _default_title(row: Mapping[str, Any]) -> str:
    statement = str(row.get("decision_statement") or "").strip()
    if not statement:
        return str(row.get("delta_id") or "P3 realization decision")
    first = statement.split(".", 1)[0].strip()
    return first[:160]


def _validate_human_projection_records(records: list[dict[str, Any]]) -> None:
    for row in records:
        delta_id = str(row.get("delta_id") or "").strip() or "<unknown>"
        projection = row.get("human_projection")
        if projection is None:
            continue
        if not isinstance(projection, Mapping):
            raise P3RealizationDecisionsError(f"P3 Authority Delta human_projection must be an object: {delta_id}")
        visibility = str(projection.get("visibility") or "").strip()
        scope = str(projection.get("knowledge_scope") or "").strip()
        title = str(projection.get("title") or "").strip()
        if visibility not in {PROJECT_KNOWLEDGE_VISIBILITY, IMPLEMENTATION_ONLY_VISIBILITY}:
            raise P3RealizationDecisionsError(f"P3 Authority Delta has invalid human projection visibility: {delta_id}")
        if scope not in KNOWLEDGE_SCOPES:
            raise P3RealizationDecisionsError(f"P3 Authority Delta has invalid human projection knowledge scope: {delta_id}")
        if title and len(title) > 200:
            raise P3RealizationDecisionsError(f"P3 Authority Delta human projection title is too long: {delta_id}")


def _human_visibility(row: Mapping[str, Any]) -> str:
    projection = row.get("human_projection") if isinstance(row.get("human_projection"), Mapping) else {}
    visibility = str(projection.get("visibility") or PROJECT_KNOWLEDGE_VISIBILITY).strip()
    return visibility if visibility in {PROJECT_KNOWLEDGE_VISIBILITY, IMPLEMENTATION_ONLY_VISIBILITY} else PROJECT_KNOWLEDGE_VISIBILITY


def _knowledge_scope(row: Mapping[str, Any]) -> str:
    projection = row.get("human_projection") if isinstance(row.get("human_projection"), Mapping) else {}
    explicit = str(projection.get("knowledge_scope") or "").strip()
    if explicit in KNOWLEDGE_SCOPES:
        return explicit
    classification = str(row.get("classification") or "").strip()
    affected = str(row.get("affected_authority") or "").strip()
    text = " ".join(
        str(row.get(key) or "").lower()
        for key in ("finding", "decision_statement", "claim_ceiling")
    )
    if classification == "product-ambiguity" or affected == "P1":
        return "product"
    if any(token in text for token in ("consumer-facing", "product surface", "workspace", "navigation", "user-visible", "frontend page", "parent insights", "child companion")):
        return "product"
    resolution = row.get("resolution_payload") if isinstance(row.get("resolution_payload"), Mapping) else {}
    if resolution.get("schema_type_overrides") or resolution.get("schema_field_additions"):
        return "architecture"
    if any(token in text for token in ("persistence", "schema", "session", "adapter", "boundary", "runtime topology", "contract binding")):
        return "architecture"
    return "implementation"


def _discover_phase1_prd(phase2_root: Path) -> Path | None:
    stage4 = phase2_root / "stage-04-design-convergence-and-delivery-prototype.md"
    if stage4.is_file() and not stage4.is_symlink():
        text = stage4.read_text(encoding="utf-8")
        for pattern in (
            r"phase1_prd\s*:\s*`([^`]+\.md)`",
            r"phase1[-_ ]prd\s*:\s*`([^`]+\.md)`",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                candidate = Path(match.group(1)).expanduser()
                if not candidate.is_absolute():
                    candidate = (phase2_root / candidate).resolve()
                else:
                    candidate = candidate.resolve()
                if candidate.is_file() and not candidate.is_symlink():
                    return candidate
    candidates = sorted(
        path
        for path in phase2_root.glob("*prd*.md")
        if path.is_file() and not path.is_symlink()
    )
    return candidates[0].resolve() if candidates else None


def _portable_ref(path: Path, project_artifact_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_artifact_root.resolve()).as_posix()
    except ValueError:
        return resolved.name


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
