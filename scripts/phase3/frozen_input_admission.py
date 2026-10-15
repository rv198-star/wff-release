"""Read frozen partial inputs into the existing P3 implementation authority.

This is input compatibility, not a second authority or a substitute P2 receipt.
Host-Agent decisions still own scope and semantics; original gaps remain visible.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath

from common.agentic_decision_authority import build_input_snapshot, canonical_digest
from common.action_card_authority_projection import build_s2_authority_extensions
from common.p3_gap_records import effective_truth
from phase3.p3_fact_registration import load_frozen_fact_index

ADMISSION = "wff.p3-frozen-input-admission.v1"
CEILING = ("P3 execution over the explicitly selected frozen-input scope only; upstream gaps and "
           "review limitations remain. No complete P2, S1B, delivery, UAT or production claim.")


def _read_bound(path, digest):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Frozen input must be an existing regular file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != str(digest).removeprefix("sha256:"):
        raise ValueError("Frozen input SHA256 differs")
    return raw


def admit_frozen_inputs(sources, fact_sources):
    """Bind original bytes and selected original IDs; never manufacture upstream files."""
    if {s.get("kind") for s in sources} != {"P1", "architecture", "interaction"} or len(sources) != 3:
        raise ValueError("Exactly P1, architecture and interaction frozen inputs required")
    bound = {}; ceilings = []; gaps = []
    for source in sources:
        path = Path(source["path"]).resolve()
        raw = _read_bound(source["path"], source["sha256"])
        document = json.loads(raw)
        if not isinstance(document, dict):
            raise ValueError("Frozen input document must be an object")
        members = [(path, raw)]
        for relative, digest in document.get("files", {}).items():
            rel = PurePosixPath(relative)
            member = path.parent / relative
            if rel.is_absolute() or ".." in rel.parts or not member.resolve().is_relative_to(path.parent):
                raise ValueError("Frozen manifest member escapes its root")
            members.append((member.resolve(), _read_bound(member, digest)))
        for member, data in members:
            key = str(member)
            actual = hashlib.sha256(data).hexdigest()
            if key in bound and bound[key] != actual:
                raise ValueError("Conflicting frozen source identities")
            bound[key] = actual
            if member.suffix != ".json":
                continue
            payload = json.loads(data)
            if not isinstance(payload, dict):
                continue
            if payload.get("claim_ceiling"):
                ceilings.append({"path": key, "sha256": actual, "claim_ceiling": payload["claim_ceiling"]})
            if isinstance(payload.get("gaps"), list):
                gaps.append({"path": key, "sha256": actual, "gaps": deepcopy(payload["gaps"])})
    if not fact_sources:
        raise ValueError("Original fact selectors required")
    for source in fact_sources:
        if bound.get(str(Path(source["path"]).resolve())) != source["sha256"].removeprefix("sha256:"):
            raise ValueError("Fact selectors must address admitted original frozen files")
    facts = load_frozen_fact_index(fact_sources)
    snapshot = build_input_snapshot(phase_id="P3", inputs=tuple((str(i), Path(p)) for i, p in enumerate(sorted(bound))))
    result = {"schema_version": ADMISSION, "sources": deepcopy(sources), "fact_sources": deepcopy(fact_sources),
              "input_snapshot": snapshot, "frozen_facts_digest": canonical_digest(facts),
              "source_claim_ceilings": ceilings, "inherited_gaps": gaps,
              "upstream_complete": False, "upstream_regeneration_allowed": False,
              "claim_ceiling": CEILING}
    result["content_digest"] = canonical_digest(result)
    return result, facts


def _target(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Implementation/test target must be a relative workspace path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError("Implementation/test target escapes its workspace")
    return value


def build_frozen_input_authority(*, sources, fact_sources, decision):
    """Project a host decision into the one canonical P3 authority, with a bounded ceiling."""
    from phase3.agentic_implementation_authority import AUTHORITY_SCHEMA, validate_authority_delta_records
    admission, facts = admit_frozen_inputs(sources, fact_sources)
    if decision.get("source_admission_digest") != admission["content_digest"]:
        raise ValueError("P3 decision is bound to different frozen inputs")
    for field in ("decision_id", "owner_id", "claim_ceiling"):
        if not isinstance(decision.get(field), str) or not decision[field].strip():
            raise ValueError("Host decision identity, owner and ceiling required")
    rows = deepcopy(decision.get("implementation_slices"))
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Explicit selected implementation slices required")
    ids = [row.get("slice_id") for row in rows]
    if any(not isinstance(key, str) or not key for key in ids) or len(set(ids)) != len(ids):
        raise ValueError("Selected slice identity missing or duplicated")
    records = validate_authority_delta_records(decision.get("authority_delta_records", []), known_slice_ids=set(ids))
    view = effective_truth(facts, records)["facts"]
    operations = set()
    for row in rows:
        op = row.get("operation_id"); registered = view.get("api:" + str(op))
        if (not isinstance(op, str) or not op or op in operations or not registered or not registered["active"]
                or registered["kind"] != "api_fields" or not isinstance(registered["value"], list)
                or len(registered["value"]) != 2):
            raise ValueError("Every selected operation needs unique frozen or registered API identity")
        operations.add(op)
        if row.get("disposition") != "implement":
            raise ValueError("Only explicitly selected execution slices belong in this bounded projection")
        basis = row.get("basis", [])
        if not basis or any(not isinstance(b, dict) or set(b) != {"id", "digest"}
                            or b["id"] not in facts or b["digest"] != facts[b["id"]]["digest"] for b in basis):
            raise ValueError("Each selected slice needs original source IDs and digests")
        for field in ("reason", "semantic_owner", "authorization", "state_mutation", "failure_behavior",
                      "persistence_effects", "integration_behavior", "claim_ceiling"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError("Host implementation judgment missing: " + field)
        for field in ("implementation_targets", "test_targets", "runtime_evidence_intents", "component_ids"):
            if not isinstance(row.get(field), list) or not row[field] or any(not isinstance(v, str) or not v.strip() for v in row[field]):
                raise ValueError("Selected scope binding missing: " + field)
        for target in row["implementation_targets"] + row["test_targets"]:
            _target(target)
        if set(row.get("authority_delta_refs", [])) - {r["delta_id"] for r in records}:
            raise ValueError("Selected slice cites an unregistered delta")
    digest = canonical_digest(decision)
    extensions = build_s2_authority_extensions(implementation_rows=rows, decision_id=decision["decision_id"], decision_digest=digest)
    authority = {"schema_version": AUTHORITY_SCHEMA, "status": "accepted-p3-agentic-implementation-authority",
        "phase_id": "P3", "decision_id": decision["decision_id"], "decision_digest": digest,
        "input_snapshot_digest": admission["input_snapshot"]["snapshot_digest"],
        "frozen_input_admission": admission, "bounded_host_decision": deepcopy(decision),
        "bounded_execution_only": True, "upstream_review_complete": False,
        "component_coverage": {"status": "complete", "scope": "explicitly-selected-P3-slices-only", "slice_ids": ids},
        **extensions, "decisions": {row["operation_id"]: deepcopy(extensions["slice_decisions"][row["slice_id"]]) for row in rows},
        "exact_realization_plan": [{**row, "declared_implementation_targets": row["implementation_targets"],
                                    "declared_test_targets": row["test_targets"]} for row in rows],
        "authority_delta_records": records,
        "overall_handoff": {"status": "review-bound", "minimum_rerun": "P3", "claim_ceiling": CEILING},
        "claim_ceiling": CEILING}
    authority["content_digest"] = canonical_digest(authority)
    return authority


def frozen_input_authority_is_valid(authority):
    """Rebuild from retained source bytes; a rehashed status label cannot promote a claim."""
    try:
        admission = authority["frozen_input_admission"]
        if admission.get("schema_version") != ADMISSION:
            return False
        rebuilt = build_frozen_input_authority(sources=admission["sources"], fact_sources=admission["fact_sources"],
                                                decision=authority["bounded_host_decision"])
        return rebuilt == authority
    except (KeyError, TypeError, ValueError, OSError):
        return False
