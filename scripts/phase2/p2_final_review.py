"""Read-only P2 final-review identity compatibility from B 6da99f015.

No rubric generation, score gate, reviewer dispatch, or publication lifecycle.
OMR/SQR content is retained evidence; these checks establish exact provenance.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
import json
from common.agentic_decision_authority import canonical_digest
from common.semantic_materialization import load_json_strict

INTEGRITY_CONTRACT = "p2-omr-sqr-integrity-v1"


def _bound(value, label):
    if not isinstance(value, dict) or value.get("content_digest") != canonical_digest({k: v for k, v in value.items() if k != "content_digest"}):
        raise ValueError(label + " digest differs")
    return value


def validate_contract(contract):
    _bound(contract, "Review contract")
    if (contract.get("schema_version") != "wff.p2-final-review-contract.v1"
            or not isinstance(contract.get("claim_ceiling"), str) or not contract["claim_ceiling"].strip()):
        raise ValueError("Explicit review contract and claim ceiling required")
    if "review_packets" in contract:
        plan = contract["review_packets"]
        if (not isinstance(plan, list) or not plan or any(not isinstance(p, dict)
                or set(p) != {"packet_id", "sections", "input_digest", "prompt_sha256"}
                or not isinstance(p["packet_id"], str) or not p["packet_id"]
                or not isinstance(p["sections"], list) or not p["sections"]
                or any(not isinstance(s, str) or not s for s in p["sections"])
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(p["input_digest"]))
                or not isinstance(p["prompt_sha256"], dict) or set(p["prompt_sha256"]) != {"omr", "sqr"}
                or any(not re.fullmatch(r"[0-9a-f]{64}", str(d)) for d in p["prompt_sha256"].values()) for p in plan)):
            raise ValueError("Review packet plan is invalid")
    return deepcopy(contract)


def review_task_id(contract, kind, packet_id):
    namespace = contract.get("task_namespace", "p2-final")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", namespace):
        raise ValueError("Invalid review task namespace")
    return namespace + "-" + kind + ("." + packet_id if "review_packets" in contract else "")


def aggregate_review_parts(parts):
    """Project original packet findings without another semantic judgment."""
    findings = {}; notes = []
    for number, part in enumerate(parts, 1):
        result = part["result"]
        findings.update({f"P{number:03d}-{key}": deepcopy(value)
                         for key, value in result["findings"].items()})
        notes.extend(result["notes"])
    review_bound = any(p["result"]["verdict"] == "REVIEW_BOUND" for p in parts) or any(
        finding["severity"] == "review-bound" for finding in findings.values())
    return {"verdict": "REVIEW_BOUND" if review_bound else "PASS",
            "findings": findings, "notes": notes}


def _validate_review_parts(review, *, contract, subject_digest):
    plan = contract.get("review_packets")
    parts = review.get("parts")
    if (not isinstance(plan, list) or not plan or not isinstance(parts, list)
            or len(parts) != len(plan)):
        raise ValueError("Every declared review packet needs its original response")
    call_ids = set()
    for expected, part in zip(plan, parts):
        receipt = _bound(part["receipt"], "Review packet receipt")
        if (part.get("packet_id") != expected["packet_id"]
                or receipt.get("packet_id") != expected["packet_id"]
                or receipt.get("input_digest") != expected["input_digest"]
                or receipt.get("kind") != review["kind"]
                or receipt.get("prompt_sha256") != expected["prompt_sha256"][review["kind"]]
                or receipt.get("subject_digest") != subject_digest
                or receipt.get("contract_digest") != contract["content_digest"]
                or receipt.get("result_digest") != canonical_digest(part["result"])
                or not receipt.get("call_id") or receipt["call_id"] in call_ids):
            raise ValueError("Review packet binding or call identity differs")
        result = part["result"]
        if (not isinstance(result, dict) or result.get("verdict") not in {"PASS", "REVIEW_BOUND"}
                or not isinstance(result.get("findings"), dict)
                or any(not isinstance(f, dict) or f.get("severity") not in {"none", "non-material", "review-bound"}
                       for f in result["findings"].values())
                or not isinstance(result.get("notes"), list)
                or any(not isinstance(note, str) for note in result["notes"])):
            raise ValueError("Review packet result is invalid")
        call_ids.add(receipt["call_id"])
    if review["result"] != aggregate_review_parts(parts):
        raise ValueError("Review aggregate must preserve its packet results")
    if review["receipt"].get("packet_receipts") != [p["receipt"]["content_digest"] for p in parts]:
        raise ValueError("Review aggregate receipt differs from packet receipts")
    return parts


def validate_acceptance_record(record, *, payload):
    _bound(record, "Final review acceptance")
    if (not isinstance(record.get("bindings"), dict)
            or record["bindings"].get("semantic_payload_digest") != canonical_digest(payload)
            or record.get("sqr_isolation") != "no-omr-results-in-packet"
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(record.get("subject_digest", "")))
            or not record.get("journal_run_id")):
        raise ValueError("Final review acceptance binding is invalid")
    contract = validate_contract(record["contract"])
    if record.get("claim_ceiling") != contract["claim_ceiling"]:
        raise ValueError("Acceptance claim ceiling differs from reviewed contract")
    rows = record.get("reviews")
    if (not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows)
            or [r.get("kind") for r in rows] != ["omr", "sqr"]):
        raise ValueError("Require OMR then isolated SQR")
    for row in rows:
        receipt = _bound(row["receipt"], "Review receipt")
        result = row["result"]
        if (receipt.get("kind") != row["kind"] or receipt.get("subject_digest") != record["subject_digest"]
                or receipt.get("contract_digest") != contract["content_digest"]
                or receipt.get("result_digest") != canonical_digest(result)):
            raise ValueError("Final review receipt differs")
        if (not isinstance(result, dict) or result.get("verdict") not in {"PASS", "REVIEW_BOUND"}
                or not isinstance(result.get("findings"), dict)
                or any(not isinstance(f, dict) or f.get("severity") not in {"none", "non-material", "review-bound"}
                       for f in result["findings"].values())):
            raise ValueError("Unresolved material review prevents acceptance")
    if "review_packets" in contract:
        plan = contract["review_packets"]
        ids = [p.get("packet_id") for p in plan] if isinstance(plan, list) else []
        covered = [sid for p in plan for sid in p.get("sections", [])] if isinstance(plan, list) else []
        if (not ids or len(ids) != len(set(ids)) or len(covered) != len(set(covered))
                or set(covered) != set(payload.get("requested_sections", []))):
            raise ValueError("Review packets must bind the candidate section identities once")
        parts = [_validate_review_parts(row, contract=contract, subject_digest=record["subject_digest"]) for row in rows]
        call_ids = [p["receipt"]["call_id"] for group in parts for p in group]
        if len(call_ids) != len(set(call_ids)):
            raise ValueError("OMR and isolated SQR require distinct actual calls")
    if payload.get("review_contract") != "p2-omr-sqr.v1":
        raise ValueError("Final review requires its explicit P2 payload contract")


def acceptance_record(*, subject, contract, reviews, journal, run_id):
    """Bind the existing OMR/SQR rounds to every actual settled packet call."""
    validate_contract(contract)
    state = journal.status(run_id)
    if [r['kind'] for r in reviews] != ['omr', 'sqr']:
        raise ValueError('Require OMR then isolated SQR')
    positions = []
    for review in reviews:
        parts = (_validate_review_parts(review, contract=contract, subject_digest=subject['content_digest'])
                 if 'review_packets' in contract else [review])
        group_positions = []
        for part in parts:
            result, receipt = part['result'], part['receipt']
            task_id = review_task_id(contract, review['kind'], part.get('packet_id', 'packet-001'))
            matching = [(i, c) for i, c in enumerate(state['calls'])
                        if c['task_id'] == task_id and c['state'] == 'SETTLED'
                        and ('review_packets' not in contract or c['call_id'] == receipt.get('call_id'))
                        and c['payload_digest'] == canonical_digest(result)]
            if len(matching) != 1:
                raise ValueError('Review must have its actual settled Journal response')
            if 'review_packets' in contract:
                task = journal.db.execute('SELECT role,config FROM tasks WHERE run_id=? AND task_id=?',
                                          (run_id, task_id)).fetchone()
                if (task is None or task['role'] != review['kind']
                        or json.loads(task['config'])['prompt_digest'] != 'sha256:' + receipt['prompt_sha256']):
                    raise ValueError('Review packet differs from its issued Journal prompt')
            group_positions.append(matching[0][0])
            if (receipt['subject_digest'] != subject['content_digest']
                    or receipt['contract_digest'] != contract['content_digest']):
                raise ValueError('Review subject/contract differs')
        positions.append(group_positions)
    if max(positions[0]) >= min(positions[1]):
        raise ValueError('Require ordered OMR then SQR')
    body = {'contract': deepcopy(contract), 'subject_digest': subject['content_digest'],
            'bindings': deepcopy(subject['bindings']), 'reviews': deepcopy(reviews),
            'journal_run_id': run_id, 'sqr_isolation': 'no-omr-results-in-packet',
            'claim_ceiling': contract['claim_ceiling']}
    record = {**body, 'content_digest': canonical_digest(body)}
    validate_acceptance_record(record, payload=subject['semantic_projection']['p2_authority'])
    return record


def validate_candidate_delivery(root, subject, *, candidate, payload):
    if (subject.get('content_digest') != canonical_digest({k:v for k,v in subject.items() if k!='content_digest'})
            or subject['bindings'].get('candidate_digest') != candidate['content_digest']
            or subject['bindings'].get('semantic_payload_digest') != canonical_digest(payload)
            or subject['semantic_projection']['p2_authority'] != payload):
        raise ValueError('Candidate delivery subject is stale or changed')
    for name,digest in subject['bindings']['output_bytes'].items():
        path = root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('Missing/unsafe candidate delivery surface')
        if 'sha256:'+sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Candidate delivery bytes changed after review binding')


def load_subject(root: Path):
    """Load the recorded subject; never reconstruct one from unreviewed delivery."""
    subject = load_json_strict(root / "p2-final-review-subject.json")
    candidate = load_json_strict(root / ".phase2-evidence/p2-agentic-architecture-candidate.json")
    # The existing native candidate identity predicate, without importing its
    # generation adapter into every phase that reads decision envelopes.
    _bound(candidate, "Delivery candidate")
    if candidate.get("schema_version") != "wff.p2-agentic-architecture-candidate.v1" or not isinstance(candidate.get("input_snapshot"), dict):
        raise ValueError("Invalid delivery candidate")
    if subject.get("schema_version") != "wff.p2-final-review-subject.v1":
        raise ValueError("Invalid delivery subject contract")
    validate_candidate_delivery(root, subject, candidate=candidate,
                                payload=subject["semantic_projection"]["p2_authority"])
    return subject
