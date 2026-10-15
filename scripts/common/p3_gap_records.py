"""Pure P3 gap-record validation and derived views shared by phase consumers.

No model dispatch, phase runner, store or dependency on downstream runtime.
"""
from copy import deepcopy
import re
from common.agentic_decision_authority import canonical_digest

CONTRACT = "p3-gap-decisions-v1"
ROUTE = "p3-gap-decision-required"
DEFAULTS = {
    "permissions": ("DEF-PERM-01", "Least privilege; grant no operation not granted upstream; do not merge roles."),
    "security": ("DEF-SEC-01", "Deny by default; do not weaken authentication or introduce new credentials."),
    "tenant": ("DEF-TENANT-01", "Strict isolation; no cross-tenant reads or writes."),
    "legal": ("DEF-LEGAL-01", "Make no external compliance/legal claim; mark related text undecided."),
    "pricing": ("DEF-PRICE-01", "Set no price; show undecided/demo explicitly."),
    "external": ("DEF-EXT-01", "Disable or simulate with an explicit demo label."),
    "other": ("DEF-OTHER-01", "Choose the smallest reversible option; introduce no upstream-undefined state transition; mark undecided."),
}
T1_FIELDS = {"id", "level", "decision", "basis", "reasoning", "alternatives", "reversible", "backport_target"}
T2_FIELDS = {"id", "trigger", "question", "decision", "basis", "rule", "alternatives", "rationale", "reversible",
    "affected_surfaces", "new_facts", "sensitivity", "confirmation_required", "backport_target", "supersedes"}
FACT_KINDS = {"entities", "roles", "permissions", "states", "api_fields"}


class GapDecisionError(ValueError):
    pass


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _strings(value):
    return isinstance(value, list) and all(_text(x) for x in value)


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _facts(values):
    if not isinstance(values, list):
        raise GapDecisionError("Registered facts must be an explicit array")
    ids = set()
    for fact in values:
        if (not isinstance(fact, dict) or set(fact) != {"id", "kind", "value"}
                or not _text(fact["id"]) or fact["kind"] not in FACT_KINDS or fact["id"] in ids):
            raise GapDecisionError("Registered fact identity/kind is invalid or duplicated")
        canonical_digest(fact["value"])
        ids.add(fact["id"])
    return values


def validate_gap_record(row, *, frozen_facts=None):
    """Validate registration/identity only; existing Agentic reviews judge its reasoning."""
    if row.get("gap_decision_contract") != CONTRACT:
        raise GapDecisionError("Explicit P3 gap-decision contract required")
    level = row.get("level")
    required = T1_FIELDS if level == "T1" else T2_FIELDS if level == "T2" else set()
    if not required or not required <= set(row):
        raise GapDecisionError("T1 requires eight fields; T2 requires all fifteen decision fields")
    if (not _text(row.get("id")) or row.get("delta_id") != row["id"]
            or row.get("decision_statement") != row.get("decision")
            or row.get("upstream_reconciled") is not False or row.get("applied_upstream") is not False
            or row.get("detected_phase") != "P3" or not _text(row.get("source_slice_id"))
            or row.get("local_application") != "p3-local-resolution"
            or row.get("reconciliation_status") != "deferred-post-p3"):
        raise GapDecisionError("Decision must bind existing delta/slice identity and leave upstream frozen")
    if not _text(row["decision"]) or not _strings(row["alternatives"]) or not row["alternatives"]:
        raise GapDecisionError("Decision and considered alternatives are required")
    if type(row["reversible"]) is not bool or not _text(row["backport_target"]):
        raise GapDecisionError("Reversibility and next-version backport target required")
    basis = row["basis"]
    if not isinstance(basis, list) or not basis:
        raise GapDecisionError("Exact source IDs and digests are required")
    ids = set()
    for source in basis:
        if (not isinstance(source, dict) or set(source) != {"id", "digest"}
                or not _text(source["id"]) or not _digest(source["digest"]) or source["id"] in ids):
            raise GapDecisionError("Invalid or duplicate source basis")
        if frozen_facts is not None and (source["id"] not in frozen_facts
                or frozen_facts[source["id"]]["digest"] != source["digest"]):
            raise GapDecisionError("Decision basis differs from frozen source ID/digest")
        ids.add(source["id"])
    if level == "T1":
        if not _text(row["reasoning"]) or row.get("supersedes") or row.get("new_facts"):
            raise GapDecisionError("T1 needs reasoning and cannot supersede or add business facts")
        _facts(row.get("inferred_facts", []))
    else:
        if (row["trigger"] not in {"T2", "conflict", "infeasible"} or not _text(row["question"])
                or not _text(row["rationale"]) or not _text(row["rule"])
                or not _strings(row["affected_surfaces"]) or not row["affected_surfaces"]
                or not _strings(row["supersedes"]) or row["sensitivity"] not in DEFAULTS
                or type(row["confirmation_required"]) is not bool):
            raise GapDecisionError("Invalid T2 trigger, scope, rationale or confirmation posture")
        if set(row["supersedes"]) - ids:
            raise GapDecisionError("Supersedes must name exact entries in the source basis")
        _facts(row["new_facts"])
        if row["sensitivity"] != "other":
            rule, decision = DEFAULTS[row["sensitivity"]]
            if (row["rule"] != rule or row["decision"] != decision or row["confirmation_required"] is not True
                    or row["new_facts"] or row["supersedes"]):
                raise GapDecisionError("Sensitive gaps must use the mechanical conservative rule without new grants/facts")
        elif row.get("decision_origin") == "cap-default":
            rule, decision = DEFAULTS["other"]
            if row["rule"] != rule or row["decision"] != decision or row["confirmation_required"] is not True or row["new_facts"] or row["supersedes"]:
                raise GapDecisionError("At-cap default must remain conservative and confirmation-required")
    decision_review(row)
    return deepcopy(row)


def decision_review(row):
    """Read a host-bound SQR annotation without changing the original decision."""
    confirmation = bool(row.get("confirmation_required") or (row.get("level") == "T2" and row.get("new_facts")))
    review = row.get("sqr_review")
    if review is None:
        return {"status": "not-reviewed", "already_applied_surfaces": [], "confirmation_required": confirmation}
    required = {"status", "scope_digest", "record_digest", "call_ids", "findings", "already_applied_surfaces"}
    original = {key: value for key, value in row.items() if key != "sqr_review"}
    if (row.get("level") != "T2" or not isinstance(review, dict) or set(review) != required
            or review["status"] not in {"accepted", "rejected", "review-bound", "not-reviewed"}
            or not _digest(review["scope_digest"])
            or review["record_digest"] != canonical_digest(original)
            or not _strings(review["call_ids"])
            or (review["status"] != "not-reviewed" and not review["call_ids"])
            or not isinstance(review["findings"], list)
            or not _strings(review["already_applied_surfaces"])):
        raise GapDecisionError("SQR annotation must bind the unchanged original decision and actual review calls")
    return {**deepcopy(review), "confirmation_required": confirmation}


def effective_truth(frozen_facts, records):
    """Derived view only; exact explicit T2 supersedes, never a second store."""
    facts={key:{**deepcopy(value),"source_id":key,"delta_id":None,"active":True} for key,value in frozen_facts.items()}
    topics=set(); overridden=set(); backport=[]; reviews={}; applied_rejected=[]
    for row in records:
        if row.get("gap_decision_contract") != CONTRACT: continue
        validate_gap_record(row,frozen_facts=frozen_facts)
        if row["id"] in topics: raise GapDecisionError("Duplicate registered topic")
        topics.add(row["id"])
        review = decision_review(row); reviews[row["id"]] = review
        backport.append({"id":row["id"],"level":row["level"],"backport_target":row["backport_target"],
            "basis":deepcopy(row["basis"]),"upstream_reconciled":False,
            "review_status":review["status"],"already_applied_surfaces":review["already_applied_surfaces"],
            "confirmation_required":review["confirmation_required"]})
        if review["status"] == "rejected":
            if review["already_applied_surfaces"]:
                applied_rejected.append({"id":row["id"],"surfaces":review["already_applied_surfaces"]})
            continue
        supersedes=set(row.get("supersedes",[]))
        if overridden & supersedes:
            raise GapDecisionError("Multiple decisions cannot silently compete to supersede the same frozen fact")
        overridden.update(supersedes)
        for key in supersedes:
            facts[key]={**facts[key],"active":False,"superseded_by":row["id"]}
        for fact in row.get("new_facts",[])+row.get("inferred_facts",[]):
            key=fact["id"]
            if key in facts and (facts[key]["value"]!=fact["value"] or facts[key]["kind"]!=fact["kind"]):
                if row["level"]!="T2" or key not in supersedes:
                    raise GapDecisionError("Only explicit T2 supersedes may override a frozen/registered fact")
            if key in facts and key not in supersedes:
                continue
            facts[key]={"kind":fact["kind"],"value":deepcopy(fact["value"]),"digest":canonical_digest(fact["value"]),
                "source_id":key if key in frozen_facts else None,"delta_id":row["id"],"active":True}
    return {"facts":facts,"backport_queue":backport,"decision_reviews":reviews,
            "already_applied_rejected_decisions":applied_rejected,
            "derived_only":True,"upstream_reconciled":False}


def registered_resolution(ledger, topic):
    """Resolve a named runtime gap from the existing canonical ledger, not a status flag."""
    if not isinstance(ledger,dict) or ledger.get("schema_version")!="wff.p3-authority-delta-ledger.v1": return None
    body={k:v for k,v in ledger.items() if k!="content_digest"}
    if ledger.get("content_digest")!=canonical_digest(body) or ledger.get("upstream_mutation_performed") is not False: return None
    for row in ledger.get("records",[]):
        if row.get("gap_decision_contract")!=CONTRACT: continue
        validate_gap_record(row)
        review = decision_review(row)
        if review["status"] == "rejected": continue
        if topic==row["id"] or topic in row.get("affected_surfaces",[]):
            return {"id":row["id"],"digest":review.get("record_digest") or canonical_digest(row),"level":row["level"],
                "confirmation_required":review["confirmation_required"],"claim_ceiling":row["claim_ceiling"],
                "review_status":review["status"]}
    return None


