"""M1 architecture author/freeze functions parameterized for the repository entry.

Source: WP1.4 prepare_architecture_a3.run and freeze_architecture_a3.freeze.
Dispatch, parsing, templates, Journal and OMR/SQR remain the existing functions.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from common.agentic_decision_authority import canonical_digest
from common.bounded_model_call import (dispatch, call_row, append_row, CallBoundary,
    SectionRejected, TransportSectionRejected)
from common.semantic_materialization import MaterializationError, write_json_exclusive
from common.semantic_generation_wire import parse_raw_object
from phase2.architecture_templates import (FIELDS, schema, prompt_for, validate,
    render_architecture_section, load_architecture_library, author_view)
from phase2.interaction_templates import bound, compact, check_bound, source_anchor
from phase2.interaction_generation import collect_bounded_reviews

COLLECTIONS = [*FIELDS]
CEILING = "P2 author proposals with explicit gaps; only original OMR/SQR receipts establish reviewed delivery. No UAT, human appointment, production proof or in-cycle upstream regeneration."


def generate_sections(*, packets, journal, context, send, output_dir, max_repairs=2, accepted=None, prior_records=None):
    """Port of the finite A3 author loop; every model call uses shared dispatch."""
    if type(max_repairs) is not int or not 0 <= max_repairs <= 2:
        raise ValueError("At most two same-section repairs")
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = [deepcopy(r["answer"]) for r in (prior_records or [])]; records = []; unresolved = []; stopped = None
    for packet in packets:
        sid = packet["section"]; answer = None; previous = None; diagnostics = []
        if accepted and sid in accepted:
            record = deepcopy(accepted[sid]); check_bound(record, "Reused reviewed architecture")
            if record["input_digest"] != packet["content_digest"]:
                raise ValueError("Reused architecture input differs")
            # Caller supplies only verified frozen delivery, never a rejected proposal.
            validate(compact(record["answer"]), packet, prior)
            records.append(record); prior.append(record["answer"])
            append_row(output_dir / "reuse.jsonl", {"section": sid, "original_call_id": record["call_id"],
                "input_digest": packet["content_digest"], "accepted_digest": record["content_digest"]})
            continue
        if stopped:
            diagnostics = ["Not dispatched after run boundary: " + stopped]
        else:
            for attempt in range(max_repairs + 1):
                prompt = prompt_for(packet, prior, previous=previous, diagnostics=diagnostics)
                if attempt and previous is None:
                    prompt += "\nSimplify this section after incomplete output: shorter bounded choices and named gaps. " + compact(diagnostics)
                row = call_row(context, section=sid, attempt=attempt, prompt=prompt,
                               template_version=packet["template_version"])
                row["repair_limit"] = max_repairs
                try:
                    call, reply, version = dispatch(journal=journal, context=context, task_id=sid + "." + str(attempt),
                        role="author", write_key=sid, prompt=prompt,
                        binding={"input_digest":packet["content_digest"], "template_digest":packet["template_digest"]},
                        send=send, output_dir=output_dir, row=row)
                except TransportSectionRejected as exc:
                    diagnostics = [str(exc)]; break
                except SectionRejected as exc:
                    previous = None; diagnostics = [str(exc)]; continue
                except (CallBoundary, MaterializationError, TimeoutError) as exc:
                    stopped = type(exc).__name__ + ": " + str(exc); diagnostics = [stopped]; break
                try:
                    text = reply["raw"].strip()
                    if text.startswith("```json\n") and text.endswith("\n```"): text = text[8:-4]
                    parse_raw_object(text); row["parse_ok"] = True
                    answer = validate(reply["raw"], packet, prior)
                    row.update(validate_ok=True, patterns=[kind for kind in packet["patterns"] if answer.get(kind)],
                        outcome="accepted" if attempt == 0 and row.get("transport_attempt",0) == 0 else "repaired")
                    journal.commit_draft(call_id=call["call_id"], expected_version=version)
                except ValueError as exc:
                    answer = None; diagnostics = [compact(exc.as_dict()) if isinstance(exc, MaterializationError) else str(exc)]; row["diagnostics"] = diagnostics
                    row["outcome"] = "degraded-T2" if attempt == max_repairs else "failed"
                journal.settle(call["call_id"]); append_row(output_dir / "calls.jsonl", row)
                print(compact({"section":sid, "attempt":attempt, "outcome":row["outcome"], "diagnostics":row["diagnostics"]}), flush=True)
                if answer is not None:
                    record = bound({"answer":answer, "call_id":call["call_id"], "journal_run_id":context["run_id"],
                        "input_digest":packet["content_digest"], "claim_ceiling":CEILING,
                        "author_context":author_view(packet, prior)})
                    write_json_exclusive(output_dir / (sid + ".json"), record)
                    records.append(record); prior.append(answer); break
                previous = reply["raw"]
        if answer is None:
            gap = {"section":sid, "kind":"T2", "accepted":False, "diagnostics":diagnostics,
                   "input_digest":packet["content_digest"]}
            unresolved.append(gap); write_json_exclusive(output_dir / (sid + ".gap.json"), gap)
    return {"records":records, "degraded":unresolved, "stopped":stopped}


def review_payload(records, packets, degraded, *, reference_records=None, reference_packets=None):
    """Wrap unchanged answers for existing OMR/SQR; selected facts keep provenance."""
    by_id = {r["answer"]["section"]:r for r in records}
    notices = [{"section":g["section"], "kind":"T2", "question":g["section"]+" unavailable (T2)", "refs":[]} for g in degraded]
    gaps = {g["section"]:g for g in notices}
    sections = []; facts = {}
    # Direct references to original author records must survive packet partitioning.
    # Keep their exact values and source binding; do not attach the entire draft.
    originals = {}
    source_packets = {p["section"]: p for p in (reference_packets or packets)}
    for record in [*(reference_records or []), *records]:
        for collection, fields in FIELDS.items():
            primary = next((key for key in fields if key.endswith("_id")), None)
            if primary is None: continue
            for index, row in enumerate(record["answer"][collection]):
                originals[row[primary]] = (record, collection, index, row)
    for packet in packets:
        sid = packet["section"]; record = by_id.get(sid); answer = record["answer"] if record else None
        refs = {ref for kind in FIELDS for row in answer[kind] for ref in row["p1_refs"]} if answer else set()
        selected = [deepcopy(row) for row in packet.get("reference_sources",packet["sources"]) if row["id"] in refs]
        identities = {item for kind in FIELDS for row in answer[kind] for value in row.values()
            for item in (value if isinstance(value, list) else [value]) if isinstance(item, str)} if answer else set()
        for identity in sorted(identities & originals.keys()):
            record, collection, index, original = originals[identity]
            origin = record["answer"]["section"]
            if origin == sid: continue
            context = by_id[sid].get("author_context") if by_id.get(sid) else None
            if context and original not in [item for rows in context["earlier_explicit_decisions"].values() for item in rows]:
                # A matching P1 object ID does not make a future technical record
                # available to an earlier author. Review original proposals as proposals.
                continue
            selected.append({"id": identity, "family": "architecture-author-record", "value": deepcopy(original),
                "source": {"section": origin, "path": f"/answer/{collection}/{index}",
                           "answer_digest": record["content_digest"]}})
            source = source_packets[origin]
            selected.extend(deepcopy(row) for row in source.get("reference_sources",source["sources"]) if row["id"] in original["p1_refs"])
        for row in selected:
            key = source_anchor(row)
            if key not in facts: facts[key] = deepcopy(row)
            else: facts[key]["value"].update(row["value"])
        sections.append({"section":sid, "status":"accepted" if answer else "degraded-T2",
            "payload":deepcopy(answer), "gaps":deepcopy(answer["gaps"]) if answer else [gaps.get(sid, {"kind":"T2", "question":"No author output", "refs":[]})],
            "provenance":selected, "patterns":packet["patterns"]})
    return bound({"schema_version":"wff.architecture-review-input.v1", "review_contract":"p2-omr-sqr.v1", "template_version":load_architecture_library()["version"],
        "requested_sections":[p["section"] for p in packets], "sections":sections,
        "provenance":list(facts.values()), "gaps":notices, "claim_ceiling":CEILING})


def architecture_input(records, degraded, *, p1_sha256, projection_sha256):
    """Port of M1's flattening/source-index, with explicit original source binding."""
    flat = {k:[deepcopy(row) for record in records for row in record["answer"][k]] for k in FIELDS}
    gap_inputs = []
    for record in records:
        for i, gap in enumerate(record["answer"]["gaps"]):
            identity = hashlib.sha256((record["content_digest"] + ":" + str(i)).encode()).hexdigest()[:24]
            gap_inputs.append({"decision_id":"ARCH-GAP-" + identity, "status":"unresolved-question",
                "question":gap["question"], "p1_refs":gap["p1_refs"], "source_section":record["answer"]["section"],
                "source_answer_digest":record["content_digest"], "source_pointer":"/answer/gaps/" + str(i),
                "claim_ceiling":"Unresolved question, not a grant or completed behavior."})
    for gap in degraded:
        gap_inputs.append({"decision_id":"ARCH-SECTION-GAP-" + hashlib.sha256(gap["section"].encode()).hexdigest()[:24],
            "status":"degraded-T2", "question":gap["section"] + " unavailable (T2)",
            "p1_refs":[], "source_section":gap["section"], "claim_ceiling":"T2 gap, not completed work."})
    flat = bound({"schema_version":"wff.bounded-architecture-input.v1", "claim_ceiling":CEILING,
        "p1_authority_sha256":p1_sha256, "p1_projection_sha256":projection_sha256,
        "accepted_section_inputs":[{"section":r["answer"]["section"], "call_id":r["call_id"],
            "input_digest":r["input_digest"], "answer_digest":r["content_digest"]} for r in records],
        **flat, "degraded_sections":[{"section":g["section"], "kind":"T2", "accepted":False,
            "question":g["section"] + " unavailable (T2)"} for g in degraded], "gap_inputs":gap_inputs})
    selectors = []
    for group, key in [("services","service_id"),("objects","object_id"),("operations","operation_id"),
            ("fields","field_id"),("states","state_id"),("policies","decision_id"),("gap_inputs","decision_id")]:
        selectors.extend({"id":row[key], "id_pointer":f"/{group}/{i}/{key}", "value_pointer":f"/{group}/{i}"}
                         for i,row in enumerate(flat[group]))
    return flat, selectors


def freeze(*, records, packets, degraded, journal, context, output_dir, p1_sha256, projection_sha256, stop_reason, reference_records=None, reference_packets=None):
    """Freeze every stage with the existing receipt dispositions; no new judgment."""
    authored = review_payload(records, packets, degraded, reference_records=reference_records, reference_packets=reference_packets)
    subject, inputs, parts, rejected, state, dispositions = collect_bounded_reviews(
        payload=authored, journal=journal, context=context, output_dir=output_dir)
    accepted = [r for r in records if not dispositions[r["answer"]["section"]]]
    unresolved = deepcopy(degraded) + [{"section":r["answer"]["section"], "kind":"T2", "accepted":False,
        "diagnostics":dispositions[r["answer"]["section"]]} for r in records if dispositions[r["answer"]["section"]]]
    flat, selectors = architecture_input(accepted, unresolved, p1_sha256=p1_sha256, projection_sha256=projection_sha256)
    review = bound({"parts":parts, "rejected_receipts":rejected, "dispositions":dispositions,
        "review_complete":bool(inputs["packets"]) and len(parts)==2*len(inputs["packets"]),
        "expected_review_calls":2*len(inputs["packets"]), "accepted_review_calls":len(parts),
        "subject_digest":subject["content_digest"], "review_inputs_digest":canonical_digest(inputs),
        "stop_reason":stop_reason, "accounting":journal.accounting(context["run_id"])})
    values = {"architecture-input.json":flat, "section-decisions.json":{"sections":accepted, "degraded":unresolved},
        "architecture-authored.json":authored, "architecture-review.json":review,
        "architecture-review-inputs.json":inputs, "architecture-subject.json":subject,
        "interface-source-index.json":{"selectors":selectors, "content_digest":flat["content_digest"]}}
    for name, value in values.items(): write_json_exclusive(output_dir / name, value)
    by_id = {p["section"]:p for p in packets}
    for stage in ("stage01","stage02","stage03","stage04","engineering"):
        text = "# " + stage + "\n\n" + CEILING + "\n"
        for record in accepted:
            if record["answer"]["section"].split(".")[0] == stage:
                text += "\n" + render_architecture_section(record["answer"], by_id[record["answer"]["section"]])["markdown"]
        for gap in unresolved:
            if gap["section"].split(".")[0] == stage: text += "\n" + gap["section"] + " unavailable (T2)\n"
        (output_dir / (stage + ".md")).write_text(text)
    files = {name:hashlib.sha256((output_dir/name).read_bytes()).hexdigest()
        for name in [*values, *[stage+".md" for stage in ("stage01","stage02","stage03","stage04","engineering")]]}
    manifest = bound({"schema_version":"wff.bounded-architecture-freeze.v1", "files":files,
        "review_complete":review["review_complete"], "accepted_sections":len(accepted), "degraded_sections":len(unresolved),
        "journal_run_id":context["run_id"], "claim_ceiling":CEILING})
    write_json_exclusive(output_dir / "freeze-manifest.json", manifest)
    return {"manifest":manifest, "input":flat, "selectors":selectors, "records":accepted, "review":review}
