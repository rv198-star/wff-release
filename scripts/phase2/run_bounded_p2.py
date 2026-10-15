#!/usr/bin/env python3
"""One repository entry for bounded P2, including its offline prompt dry run.

Wires the existing M1 author, review, freeze, transport and Journal functions.
External directories contain configuration, declarations and outputs only.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from functools import partial
from contextlib import ExitStack
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path: sys.path.insert(0, str(SCRIPTS_ROOT))
from common.agentic_decision_authority import canonical_digest
from common.bounded_model_call import estimate_request_tokens, CallBoundary
from common.bounded_response_stream import ResponsesTransport
from common.semantic_generation_journal import GenerationJournal
from common.semantic_generation_wire import object_depth
from common.semantic_materialization import write_json_exclusive
from phase2.architecture_templates import prepare_architecture_section, prompt_for, schema, author_view
from phase2 import architecture_generation as architecture
from phase2.interaction_templates import prepare_section, load_library, bound, compact, check_bound, response_schema, assemble_sections, share_author_references, model_fact_value
from phase2.interaction_generation import (section_prompt, generate_sections, prepare_review_packets, review_prompt,
    review_and_freeze, freeze_bounded_interaction, load_frozen_interaction, call_metrics)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment_credential():
    return os.environ["OPENAI_API_KEY"]


def read_source(spec):
    path = Path(spec["path"])
    if path.is_symlink() or sha(path) != spec["sha256"]: raise ValueError("Source digest differs: " + str(path))
    return json.loads(path.read_bytes())


def scenario_token_limit(config):
    """One configured phase/scenario ceiling across both declared runs."""
    value = config["token_limit"]
    if type(value) is not int or value <= 0:
        raise ValueError("Scenario token_limit must be a positive integer")
    return value


def planned_review_reservations(config):
    """One protected 60K request + 8K output for every already planned review."""
    if not config.get("protect_reviews", False):
        return {}
    return {"p2-"+label+"."+kind+f".packet-{index:03d}": 68000
            for label, groups in config["reviews"].items()
            for kind in ("omr", "sqr") for index, _ in enumerate(groups, 1)}


def validate_previous_budget(config, previous):
    if (previous["token_limit"] != scenario_token_limit(config)
            or previous["scenario"] != config["logical_id"]):
        raise ValueError("Second run cannot change the scenario or its cumulative limit")


def inputs(config):
    p1 = Path(config["p1"]["path"]).read_bytes(); read_source(config["p1"])
    projection = read_source(config["projection"])
    packets = [prepare_architecture_section(projection=projection, p1_raw=p1,
        expected_p1_sha256=config["p1"]["sha256"], logical_id=config["logical_id"],
        section=row["section"], purpose=row["purpose"], selection=row["selection"],
        source_fields=row.get("source_fields"), prior_sections=row.get("prior_sections"),
        prior_collections=row.get("prior_collections")) for row in config["architecture"]]
    # Shared original IDs must expose the same selected fields to every author
    # that cites them, even when a later review combines those fields.
    packets = share_author_references(packets, reference_key="sources", include_all=False)
    selected_sources = share_author_references(packets, reference_key="sources")[0]["sources"]
    packets = [bound({**packet,"reference_sources":selected_sources}) for packet in packets]
    if len({p["section"] for p in packets}) != len(packets): raise ValueError("Duplicate architecture section")
    if {p["section"].split(".")[0] for p in packets} != {"stage01","stage02","stage03","stage04","engineering"}:
        raise ValueError("Full P2 configuration needs Stage01–04 and engineering-spec scope")
    if set(config["interaction"]) != {s["id"] for s in load_library()["sections"]}:
        raise ValueError("Full P2 configuration needs every D section")
    return p1, projection, packets


def select_architecture(selected, flat, selectors, selection):
    """M1 select_architecture with case-specific display names moved to configuration."""
    selected_ids = {item for items in selected.values() for item in items}
    related_ids = set(selection.get("related_ids", selected_ids))
    operations = {x["operation_id"] for x in flat["operations"] if set(x["p1_refs"]) & related_ids}
    if selection["operations"] == "all": operations = {x["operation_id"] for x in flat["operations"]}
    elif selection["operations"] == "none": operations = set()
    elif selection["operations"] != "related": raise ValueError("Unknown operation selection")
    allowed = set(operations)
    allowed.update(x["field_id"] for x in flat["fields"]
        if x["operation_id"] in operations and x["name"] in selection["field_names"])
    allowed.update(x["state_id"] for x in flat["states"] if x["object_id"] in selected_ids)
    if selection["services"]: allowed.update(x["service_id"] for x in flat["services"])
    if selection["policies"]: allowed.update(x["decision_id"] for x in flat["policies"] if set(x["p1_refs"]) & selected_ids)
    gap_scope = set(selection.get("gap_reference_ids", selected_ids - set(selected.get("objects_attributes", []))))
    allowed.update(x["decision_id"] for x in flat["gap_inputs"]
        if x["status"] == "degraded-T2" or set(x["p1_refs"]) & gap_scope)
    return [{key:row[key] for key in ("id_pointer","value_pointer")} for row in selectors if row["id"] in allowed]


def interaction_inputs(config, p1, projection, flat, selectors):
    raw = compact(flat).encode(); digest = hashlib.sha256(raw).hexdigest()
    return share_author_references([prepare_section(projection=projection, p1_raw=p1, expected_p1_sha256=config["p1"]["sha256"],
        logical_id=config["logical_id"], section=sid, selection=row["selection"],
        architecture=[{"raw":raw, "expected_sha256":digest, "logical_id":"bounded-p2-architecture",
            "selectors":select_architecture(row["selection"], flat, selectors, row["architecture_selection"])}])
        for sid,row in config["interaction"].items()], include_all=False)



def fact_symmetry(author_views, review_inputs):
    """Offline comparison of exact model-visible fields, including prior decisions.

    Each section declares applicable original fact IDs; other sections' original answers remain
    available for consistency review, not new input truth.
    """
    violations = []; comparisons = 0
    versions = [(label, variant) for label, inputs in review_inputs.items()
                for variant in [inputs, *([inputs["actual_reused_authors"]] if "actual_reused_authors" in inputs else [])]]
    for label, inputs in versions:
        for packet in inputs["packets"]:
            for section in packet["view"]["sections"]:
                sid = section["section"]; view = author_views[sid]
                known = {(r["family"], r["id"]): model_fact_value(r["value"]) for r in view["facts"]}
                prior = [r for rows in view.get("earlier_explicit_decisions", {}).values() for r in rows]
                for fact in packet["view"]["facts"]:
                    if {"id":fact["id"],"family":fact["family"]} not in section.get("fact_refs", []): continue
                    comparisons += 1
                    value = model_fact_value(fact["value"])
                    available = (value in prior if fact["family"] == "architecture-author-record" else
                        all(key in known.get((fact["family"],fact["id"]), {})
                            and known[(fact["family"],fact["id"])][key] == expected
                            for key, expected in value.items()) and (fact["family"],fact["id"]) in known)
                    if not available:
                        violations.append({"scope":label, "packet":packet["packet_id"], "section":sid,
                            "fact_id":fact["id"], "family":fact["family"]})
    return {"comparisons":comparisons, "violation_count":len(violations), "violations":violations}


def sizing_view(target, original):
    """Offline union: unchanged prior-record sizes plus target-case input sizes.

    This view is never dispatched. IDs and raw answers are not translated between
    projects, and the source project's decisions are not target-project truth.
    """
    view = deepcopy(target)
    facts = {(row["family"], row["id"]): deepcopy(row) for row in original["facts"]}
    for row in target["facts"]:
        key = (row["family"], row["id"])
        if key in facts and facts[key] != row:
            raise ValueError("Sizing source and target fact identity conflict")
        facts[key] = deepcopy(row)
    view["facts"] = list(facts.values())
    if "earlier_explicit_decisions" in original:
        view["earlier_explicit_decisions"] = deepcopy(original["earlier_explicit_decisions"])
    return view


def sizing_payload(payload, target_references, original_non_p1):
    """Size unchanged answers with target facts and source-case prior-record sizes.

    Original provenance remains in the immutable source artifact. This wrapper
    explicitly makes no claim that source-case answers cite target-case facts.
    """
    value = deepcopy(payload)
    for row in value["sections"]:
        row["status"] = "cross-scenario-sizing-only"
        row["provenance"] = deepcopy(target_references[row["section"]])
        row["provenance"].extend(deepcopy(original_non_p1[row["section"]]))
    value["claim_ceiling"] = ("Offline size proxy only: original source-case answers are unchanged; "
        "target facts replace source-case P1 inputs for size only, not semantic validity or acceptance.")
    return bound(value)


def measured_comparison(specs, section, role, estimate):
    samples = []
    for spec in specs:
        path = Path(spec["path"])
        if sha(path) != spec["sha256"]: raise ValueError("Measured call evidence digest differs")
        for line in path.read_text().splitlines():
            row = json.loads(line)
            wanted = section if role == "author" else ("review."+role+"."+section.split(".",1)[1]
                if section.startswith("review.") else "review.p2-"+section.split(".")[0]+"."+role+"."+section.split(".",1)[1])
            if row["section"] != wanted or row.get("provider_request_tokens") is None: continue
            samples.append({"source":str(path), "milestone":spec["milestone"],
                "call_id":row["call_id"], "request_tokens":row["provider_request_tokens"],
                "difference":estimate-row["provider_request_tokens"]})
    return {"samples":samples, "m3_measured":any(row["milestone"]=="M3" for row in samples),
            "missing_reason":None if samples else "No completed measured call for this section; no substitute measurement"}


def frozen_dry_run(config, output_dir):
    """Same-case M2/M3 raw proposals only; missing answers remain missing."""
    if not config.get("protect_reviews"):
        raise ValueError("Real frozen preflight requires protected planned reviews")
    output_dir.mkdir(parents=True, exist_ok=False)
    p1, projection, packets = inputs(config)
    source = config["frozen_upstream"]
    old_config = read_source(source["config"])
    if old_config["p1"] != config["p1"]:
        raise ValueError("Frozen preflight must use the same original P1; cross-case substitutes forbidden")
    records = [read_source(spec) for spec in source["architecture_records"]]
    for record in records: check_bound(record, "Frozen original architecture answer")
    by_id = {row["answer"]["section"]:row for row in records}
    if len(by_id) != len(records): raise ValueError("Duplicate original section")
    flat = read_source(source["architecture_input"])
    if flat["p1_authority_sha256"] != config["p1"]["sha256"]:
        raise ValueError("Frozen architecture belongs to another P1")
    selectors = read_source(source["architecture_index"])["selectors"]
    original_d = read_source(source["interaction"]); check_bound(original_d, "Frozen raw D")
    d_packets = interaction_inputs(config,p1,projection,flat,selectors)
    profile = read_source(config["calibration"])
    if (profile["endpoint"],profile["model"]) != (config["endpoint"],config["model"]):
        raise ValueError("Calibration identity differs")
    request_profile=profile.get("request_calibration",{})
    if request_profile and not all(re.fullmatch(r"[0-9a-f]{64}",str(item.get("evidence_sha256",""))) for item in (profile,request_profile)):
        raise ValueError("Request calibration needs bound measured evidence")
    estimate = partial(estimate_request_tokens, request_divisor=request_profile.get("divisor",1))
    rows=[]; author_views={}; prior=[]; selected_records=[]
    def retain(section, role, prompt):
        path=output_dir/(section+"."+role+".txt"); path.write_text(prompt)
        tokens=estimate(prompt)
        rows.append({"section":section,"role":role,"prompt_path":str(path),"prompt_sha256":sha(path),
            "request_estimate":tokens,"output_reservation":8000,"reservation":tokens+8000,
            "comparison":measured_comparison(source["measurements"],section,role,tokens)})
    for packet in packets:
        sid=packet["section"];view=author_view(packet,prior);author_views[sid]=view
        retain(sid,"author",prompt_for(packet,prior))
        if sid in by_id:
            # Only attach this new prompt's source selection; the old answer is unchanged.
            record=bound({**by_id[sid],"author_context":view})
            selected_records.append(record);prior.append(by_id[sid]["answer"])
    a_payload=architecture.review_payload(selected_records,packets,[])
    d_by_id={row["section"]:row for row in original_d["sections"]}
    d_sections=[]
    for packet in d_packets:
        sid=packet["section"]["id"];author_views[sid]={"facts":packet["references"]}
        retain(sid,"author",section_prompt(packet))
        original=deepcopy(d_by_id[sid])
        d_sections.append(bound(original))
    d_payload=bound({**original_d,"sections":d_sections})
    reviews={}
    for label,payload in (("architecture",a_payload),("interaction",d_payload)):
        contract,subject,groups=prepare_review_packets(payload,groups=config["reviews"][label],
            request_estimator=estimate,namespace="p2-"+label,scope=label,
            recompute_groups=config.get("recompute_review_groups",False))
        reviews[label]={"contract":contract,"subject_digest":subject["content_digest"],"packets":groups}
        for kind in ("omr","sqr"):
            for packet in groups: retain(label+"."+packet["packet_id"],kind,review_prompt(packet,kind))
    symmetry=fact_symmetry(author_views,reviews)
    reserves=planned_review_reservations(config)
    author_sum=sum(row["reservation"] for row in rows if row["role"]=="author")
    repair=config["contingency_reservation"]
    maximum=max(row["request_estimate"] for row in rows)
    gaps=read_source(config["gap_scope"])
    report={"mode":"offline-dry-run","round":1,"model_calls":0,
        "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=SCRIPTS_ROOT.parent,text=True).strip(),
        "repository_dirty":bool(subprocess.check_output(["git","status","--porcelain"],cwd=SCRIPTS_ROOT.parent,text=True).strip()),
        "runtime_sha256":sha(__file__),"config_digest":canonical_digest(config),"rows":rows,
        "request_divisor":profile.get("request_calibration",{}).get("divisor",1),
        "maximum_request_estimate":maximum,"fact_symmetry":symmetry,
        "schema_object_depth":max(object_depth(schema()),object_depth(response_schema(load_library()))),
        "frozen_upstream":source,"same_case_real_outputs":True,"substitute_contents":False,
        "missing_original_answers":{"architecture":[p["section"] for p in packets if p["section"] not in by_id],
            "interaction":[s["section"] for s in original_d["sections"] if s.get("payload") is None]},
        "claim_ceiling":"Actual frozen proposals size future prompts only; missing answers stay missing, never accepted or reused by generation.",
        "initial_author_reservation":author_sum,"review_reservations":reserves,
        "protected_review_tokens":sum(reserves.values()),"contingency_reservation":repair,
        "planned_reservation_sum":author_sum+sum(reserves.values())+repair,
        "review_calls":sum(row["role"] in {"omr","sqr"} for row in rows),
        "max_interaction_review_calls":config.get("max_interaction_review_calls",4),
        "interaction_review_calls":sum(row["role"] in {"omr","sqr"} and row["section"].startswith("interaction.") for row in rows),
        "gap_scope":gaps,"gap_decision_calls":0,"token_limit":scenario_token_limit(config),
        "scenario_token_limit":scenario_token_limit(config)}
    report["ready"]=(maximum<=60000 and report["planned_reservation_sum"]<=scenario_token_limit(config)
        and report["interaction_review_calls"]<=config.get("max_interaction_review_calls",4) and symmetry["violation_count"]==0
        and report["schema_object_depth"]<=3 and len(gaps["gaps"])==config["expected_architecture_gap_count"])
    for name,value in (("report.json",report),("architecture-packets.json",packets),("interaction-packets.json",d_packets),
                       ("review-inputs.json",reviews),("fact-symmetry.json",symmetry)):
        write_json_exclusive(output_dir/name,value)
    (output_dir/"calls.jsonl").touch()
    print(compact({key:value for key,value in report.items() if key not in {"rows","frozen_upstream","gap_scope"}}),flush=True)
    return report


def dry_run(config, output_dir, selection=None):
    """Offline C5: all author prompts and original review packages, zero transport."""
    if "frozen_upstream" in config:
        if selection: raise ValueError("This Owner-authorized extra run has no retry run")
        return frozen_dry_run(config, output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    p1, projection, packets = inputs(config)
    surrogate = read_source(config["surrogates"]["architecture"])
    d_payload = read_source(config["surrogates"]["interaction"])
    check_bound(d_payload, "Frozen D author output")
    records = surrogate["sections"]; by_id = {r["answer"]["section"]:r for r in records}
    flat = read_source(config["surrogates"]["architecture_input"])
    selectors = read_source(config["surrogates"]["architecture_index"])["selectors"]
    d_packets = interaction_inputs(config, p1, projection, flat, selectors)
    profile = read_source(config["calibration"])
    request_profile = profile.get("request_calibration", {})
    divisor = request_profile.get("divisor", 1.0)
    if request_profile and not all(re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("evidence_sha256", "")))
                                   for evidence in (profile,request_profile)):
        raise ValueError("Request calibration needs bound measured evidence")
    estimate = partial(estimate_request_tokens, request_divisor=divisor)
    token_limit = scenario_token_limit(config)
    chosen = None; reuse_ids = set(); original_authored = None
    if selection:
        old_root,old,_,old_d = previous_run(selection["previous_run"])
        if selection["round"] != 2: raise ValueError("Subset dry run is for round two only")
        validate_previous_budget(config, old)
        token_limit -= old["accounting"]["charged_tokens"]
        chosen = selection["retry_sections"]
        reuse_ids = set(selection.get("reuse_authored", []))
        if not reuse_ids <= set(chosen["interaction"]): raise ValueError("Reused authors must belong to the selected unmet D scope")
        if reuse_ids:
            if old_d["review"]["parts"]: raise ValueError("Do not reuse a previously reviewed/rejected author through the never-reviewed path")
            original_authored = json.loads((old_root/"interaction/interaction-authored.json").read_bytes())
            check_bound(original_authored, "Original accepted authors")
            if not reuse_ids <= {row["section"] for row in original_authored["sections"] if row["status"] == "accepted"}:
                raise ValueError("Only structure-accepted original authors can be reused")
        if not set(chosen["architecture"])<=set(old["unmet_architecture"]) or not set(chosen["interaction"])<=set(old["unmet_interaction"]):
            raise ValueError("Subset dry run may only retry unmet units")
    sizing_config = config["surrogates"].get("sizing_source_config")
    source_packets = {}; source_d_packets = {}
    if sizing_config:
        if reuse_ids: raise ValueError("Cross-scenario sizing cannot rebind reused authors")
        source_config = read_source(sizing_config)
        source_p1, source_projection, source_arch = inputs(source_config)
        if source_config["p1"]["sha256"] == config["p1"]["sha256"]:
            raise ValueError("Cross-scenario sizing requires a distinct frozen source")
        source_packets = {p["section"]:p for p in source_arch}
        source_d_packets = {p["section"]["id"]:p for p in
            interaction_inputs(source_config, source_p1, source_projection, flat, selectors)}
    rows = []; prior = []; author_views = {}; target_references = {}; sizing_references = {}
    def retain(section, role, prompt, surrogate_prompt=None):
        path = output_dir / (section + "." + role + ".txt"); path.write_text(prompt)
        rows.append({"section":section, "role":role, "prompt_path":str(path), "prompt_sha256":sha(path),
            "request_estimate":estimate(prompt), "output_reservation":8000,
            "reservation":estimate(prompt)+8000})
        if surrogate_prompt is not None:
            surrogate_path = output_dir/(section+"."+role+".M1-surrogate.txt")
            surrogate_path.write_text(surrogate_prompt)
            row = rows[-1]
            row.update(actual_request_estimate=row["request_estimate"],
                surrogate_request_estimate=estimate(surrogate_prompt),
                surrogate_prompt_path=str(surrogate_path), surrogate_prompt_sha256=sha(surrogate_path))
            row["request_estimate"] = max(row["actual_request_estimate"], row["surrogate_request_estimate"])
            row["reservation"] = row["request_estimate"]+8000
    for packet in packets:
        sid = packet["section"]
        view = author_view(packet, prior)
        author_views[sid] = view
        target_references[sid] = packet["sources"]
        size_prompt = None
        if sizing_config:
            original_view = author_view(source_packets[sid], prior)
            original_view["facts"] = []
            author_views[sid] = sizing_view(view, original_view)
            size_prompt = prompt_for(packet, prior).rsplit("\n", 1)[0] + "\n" + compact(author_views[sid])
        if not chosen or sid in chosen["architecture"]:
            retain(sid, "author", prompt_for(packet, prior), surrogate_prompt=size_prompt)
        if packet["section"] in by_id: prior.append(by_id[packet["section"]]["answer"])
    for packet in d_packets:
        sid = packet["section"]["id"]
        author_views[sid] = {"facts":packet["references"]}
        target_references[sid] = packet["references"]
        size_prompt = None
        if sizing_config:
            sizing_references[sid] = [r for r in source_d_packets[sid]["references"]
                if r.get("source", {}).get("logical_id") == "bounded-p2-architecture"
                and (r["family"],r["id"]) not in {(f["family"],f["id"]) for f in packet["references"]}]
            original = {"facts":sizing_references[sid]}
            target = json.loads(section_prompt(packet).rsplit("\n", 1)[1])
            author_views[sid] = sizing_view(target, original)
            size_prompt = section_prompt(packet).rsplit("\n", 1)[0] + "\n" + compact(author_views[sid])
        if (not chosen or sid in chosen["interaction"]) and sid not in reuse_ids:
            retain(sid, "author", section_prompt(packet), surrogate_prompt=size_prompt)
    # ESP had no M1 output. Use the declared A3 answer unchanged as an explicit
    # sizing surrogate, never an accepted engineering artifact or generation reuse.
    original_packets = {p["content_digest"]:p for spec in config["surrogates"]["architecture_packets"] for p in read_source(spec)}
    review_surrogates = []
    for packet in packets:
        sid = packet["section"]
        record = by_id.get(sid)
        if record:
            original = original_packets[record["input_digest"]]
            review_surrogates.append(bound({**original, "patterns":packet["patterns"]}))
        else: review_surrogates.append(packet)
    a_payload = architecture.review_payload(records, review_surrogates, [])
    for row in a_payload["sections"]:
        if row["payload"] is None and "architecture_authored" not in config["surrogates"]:
            source = config["surrogates"]["architecture_section_aliases"][row["section"]]
            original = next(s for s in a_payload["sections"] if s["section"] == source)
            row.update(payload=deepcopy(original["payload"]), provenance=deepcopy(original["provenance"]),
                       gaps=deepcopy(original["gaps"]), status="sizing-surrogate-only")
    a_payload = bound(a_payload)
    if "architecture_authored" in config["surrogates"]:
        # M3 uses retained M2 author answers (including reviewed T2 proposals),
        # never their rendered documents or M1's smaller proxy. Sections without
        # an admitted answer remain T2; the report does not invent a successful one.
        a_payload = read_source(config["surrogates"]["architecture_authored"])
        check_bound(a_payload, "M2 actual architecture author outputs")
    if sizing_config:
        for row in a_payload["sections"]:
            sizing_references[row["section"]] = [r for r in row["provenance"]
                if r["family"] == "architecture-author-record"]
        a_payload = sizing_payload(a_payload, target_references, sizing_references)
        d_payload = sizing_payload(d_payload, target_references, sizing_references)
    review_inputs = {}
    for label, payload in (("architecture",a_payload),("interaction",d_payload)):
        declared_groups = config["reviews"][label]
        if chosen:
            selected = chosen[label]
            if not selected: continue
            declared_groups = [[sid for sid in group if sid in selected] for group in declared_groups]
            declared_groups = [group for group in declared_groups if group]
            payload = bound({**payload, "requested_sections":selected,
                "sections":[row for row in payload["sections"] if row["section"] in selected]})
        contract, subject, groups = prepare_review_packets(payload, groups=declared_groups, request_estimator=estimate, recompute_groups=config.get("recompute_review_groups", False),
            namespace="p2-"+label, scope=label)
        review_inputs[label] = {"contract":contract,"subject_digest":subject["content_digest"],"packets":groups}
        actual_groups = None
        if label == "interaction" and reuse_ids:
            by_section = {row["section"]:row for row in original_authored["sections"]}
            actual_payload = bound({**payload, "sections":[deepcopy(by_section[row["section"]])
                if row["section"] in reuse_ids else row for row in payload["sections"]]})
            actual_contract, actual_subject, actual_groups = prepare_review_packets(actual_payload,
                groups=[packet["sections"] for packet in groups], request_estimator=estimate, namespace="p2-"+label, scope=label)
            review_inputs[label]["actual_reused_authors"] = {"contract":actual_contract,
                "subject_digest":actual_subject["content_digest"],"packets":actual_groups}
        for kind in ("omr","sqr"):
            for index, packet in enumerate(groups):
                retain(label+"."+packet["packet_id"], kind,
                    review_prompt(actual_groups[index],kind) if actual_groups else review_prompt(packet,kind),
                    surrogate_prompt=review_prompt(packet,kind) if actual_groups else None)
    write_json_exclusive(output_dir/"architecture-packets.json", packets)
    write_json_exclusive(output_dir/"interaction-packets.json", d_packets)
    write_json_exclusive(output_dir/"review-inputs.json", review_inputs)
    gap_scope = read_source(config["gap_scope"])
    if (profile["endpoint"],profile["model"]) != (config["endpoint"],config["model"]):
        raise ValueError("Channel/model requires its matching calibration")
    reserves = planned_review_reservations(config)
    author_sum = sum(row["reservation"] for row in rows if row["role"] == "author")
    planned = author_sum + sum(reserves.values()) if reserves else sum(row["reservation"] for row in rows)
    contingency = config["contingency_reservation"]
    source_commit = subprocess.check_output(["git","rev-parse","HEAD"],cwd=SCRIPTS_ROOT.parent,text=True).strip()
    repository_dirty = bool(subprocess.check_output(["git","status","--porcelain"],cwd=SCRIPTS_ROOT.parent,text=True).strip())
    symmetry = fact_symmetry(author_views, review_inputs)
    write_json_exclusive(output_dir/"fact-symmetry.json", symmetry)
    report = {"source_commit":source_commit, "runtime_sha256":sha(Path(__file__)), "repository_dirty":repository_dirty,
        "mode":"offline-dry-run", "round":2 if selection else 1, "model_calls":0, "rows":rows,
        "fact_symmetry":symmetry, "scenario_token_limit":scenario_token_limit(config),
        "recompute_review_groups":config.get("recompute_review_groups", False),
        "require_fact_symmetry":config.get("require_fact_symmetry", False), "request_divisor":divisor, "calibration":config["calibration"],
        "maximum_request_estimate":max(row["request_estimate"] for row in rows),
        "initial_author_reservation":author_sum, "review_reservations":reserves,
        "protected_review_tokens":sum(reserves.values()),
        "initial_reservation_sum":planned, "contingency_reservation":contingency,
        "planned_reservation_sum":planned+contingency, "token_limit":token_limit,
        "review_calls":sum(row["role"] in {"omr","sqr"} for row in rows),
        "max_interaction_review_calls":config.get("max_interaction_review_calls",4),
        "interaction_review_calls":sum(row["role"] in {"omr","sqr"} and row["section"].startswith("interaction.") for row in rows),
        "gap_decision_calls":0, "gap_scope":gap_scope, "schema_object_depth":max(object_depth(schema()), object_depth(response_schema(load_library()))),
        "surrogates":config["surrogates"],
        "cross_scenario_sizing_only":bool(sizing_config),
        "surrogate_claim_ceiling":"Unchanged source-case answers measure size only; no target-case semantic acceptance or generation reuse.",
        "surrogate_missing_answers":{label:[row["section"] for row in payload["sections"] if row.get("payload") is None]
            for label,payload in (("architecture",a_payload),("interaction",d_payload))},
        "config_digest":canonical_digest(config)}
    report["ready"] = (report["maximum_request_estimate"]<=60000 and report["planned_reservation_sum"]<=token_limit
        and report["interaction_review_calls"]<=config.get("max_interaction_review_calls",4) and report["schema_object_depth"]<=3
        and len(gap_scope["gaps"])==config["expected_architecture_gap_count"]
        and (not config.get("require_fact_symmetry", False) or symmetry["violation_count"] == 0))
    write_json_exclusive(output_dir/"report.json",report)
    print(compact(report),flush=True)
    return report


def run(config, declaration, output_dir):
    """M1 A3/D wiring under one declared Journal and one original OMR/SQR per group."""
    dry = read_source(declaration["dry_run"])
    if not dry["ready"] or dry["round"] != declaration["round"] or dry["config_digest"] != canonical_digest(config): raise ValueError("Exact C5 dry run required")
    if (dry["source_commit"] != declaration["source_commit"] or dry["runtime_sha256"] != sha(Path(__file__))
            or dry["repository_dirty"]): raise ValueError("Formal dry run must bind the exact clean entry commit")
    if declaration["round"] not in (1,2): raise ValueError("At most two declared runs")
    if declaration["round"] == 2:
        return run_unmet(config, declaration, output_dir)
    if not 0 < declaration["max_tokens"] <= scenario_token_limit(config) or not 0<=declaration["max_repairs"]<=2:
        raise ValueError("Declared token/repair limit differs")
    head = subprocess.check_output(["git","rev-parse","HEAD"],cwd=SCRIPTS_ROOT.parent,text=True).strip()
    if head != declaration["source_commit"] or subprocess.check_output(["git","status","--porcelain"],cwd=SCRIPTS_ROOT.parent,text=True).strip():
        raise ValueError("Run must use the declared clean repository commit")
    if output_dir.exists(): raise ValueError("Declared run output cannot be reset")
    output_dir.mkdir(parents=True)
    p1, projection, packets = inputs(config); profile = read_source(config["calibration"])
    if (profile["endpoint"],profile["model"]) != (config["endpoint"],config["model"]): raise ValueError("Calibration identity differs")
    context = {"run_id":declaration["run_id"],"wp":config.get("wp", "WP2.3"),"scenario":config["logical_id"],
        "model":config["model"],"measurement_kind":"model"}
    started = time.time(); deadline = started + declaration["wall_seconds"]
    transport = ResponsesTransport(endpoint=config["endpoint"],api_key=environment_credential,
        model=config["model"],output_dir=output_dir,deadline=deadline,reasoning_effort="medium",calibration=profile)
    def send(prompt, *, max_output_tokens):
        reply = transport(prompt,max_output_tokens=max_output_tokens)
        print(compact({"call":transport.count,"finish_reason":reply.get("finish_reason"),
            "request_tokens":reply.get("request_tokens"),"output_tokens":reply.get("output_tokens"),
            "caller_cutoff":reply.get("caller_cutoff"),"calibration_check":reply.get("calibration_check")}),flush=True)
        return reply
    send.estimate_request_tokens = transport.estimate_request_tokens
    if hasattr(transport, "request_estimate_metadata"):
        send.request_estimate_metadata = transport.request_estimate_metadata
    write_json_exclusive(output_dir/"config.json",config); write_json_exclusive(output_dir/"declaration.json",declaration)
    write_json_exclusive(output_dir/"architecture-packets.json",packets)
    errors = []
    with GenerationJournal(output_dir/"journal") as journal:
        journal.create_run(run_id=context["run_id"],phase="P2",snapshot_digest=canonical_digest(config),
            contract_digest=canonical_digest(declaration),max_calls=declaration["max_calls"],
            max_tokens=declaration["max_tokens"],wall_seconds=declaration["wall_seconds"],budget_policy="charged-pending",
            review_reservations=planned_review_reservations(config))
        a_dir = output_dir/"architecture"; d_dir = output_dir/"interaction"
        result = architecture.generate_sections(packets=packets,journal=journal,context=context,send=send,
            output_dir=a_dir,max_repairs=declaration["max_repairs"])
        a_payload = architecture.review_payload(result["records"],packets,result["degraded"])
        try:
            review_and_freeze(payload=a_payload,journal=journal,context=context,send=send,output_dir=a_dir,
                collect_only=True,recompute_groups=config.get("recompute_review_groups", False),groups=config["reviews"]["architecture"],namespace="p2-architecture",scope="architecture")
        except (ValueError,TimeoutError) as exc: errors.append("architecture reviews: "+str(exc))
        a_frozen = architecture.freeze(records=result["records"],packets=packets,degraded=result["degraded"],
            journal=journal,context=context,output_dir=a_dir,p1_sha256=config["p1"]["sha256"],
            projection_sha256=config["projection"]["sha256"],stop_reason=result["stopped"] or compact(errors))
        d_packets = interaction_inputs(config,p1,projection,a_frozen["input"],a_frozen["selectors"])
        write_json_exclusive(output_dir/"interaction-packets.json",d_packets)
        library = load_library()
        d_result = generate_sections(packets=d_packets,library=library,journal=journal,context=context,send=send,
            output_dir=d_dir,max_repairs=declaration["max_repairs"],failure_level="T2")
        try:
            review_and_freeze(payload=d_result["payload"],journal=journal,context=context,send=send,output_dir=d_dir,
                collect_only=True,recompute_groups=config.get("recompute_review_groups", False),groups=config["reviews"]["interaction"],namespace="p2-interaction",scope="interaction-design",
                max_review_calls=config.get("max_interaction_review_calls",4),max_transport_attempts=1)
        except (ValueError,TimeoutError) as exc: errors.append("D reviews: "+str(exc))
        freeze_bounded_interaction(payload=d_result["payload"],library=library,journal=journal,context=context,
            output_dir=d_dir,stop_reason=d_result["stopped"] or compact(errors))
        d_frozen = load_frozen_interaction(d_dir/"interaction-freeze.json",expected_sha256=sha(d_dir/"interaction-freeze.json"))
        accounting = journal.accounting(context["run_id"])
        rows = [json.loads(line) for directory in (a_dir,d_dir) if (directory/"calls.jsonl").exists()
            for line in (directory/"calls.jsonl").read_text().splitlines()]
        with (output_dir/"calls.jsonl").open("x") as stream:
            for row in rows: stream.write(compact(row)+"\n")
        report = {"run_id":context["run_id"],"round":declaration["round"],"source_commit":head,
            "token_limit":scenario_token_limit(config),"scenario":config["logical_id"],
            "duration_seconds":time.time()-started,"accounting":accounting,"errors":errors,
            "architecture":a_frozen["manifest"],"architecture_review":a_frozen["review"],
            "interaction":d_frozen["payload"]["metrics"],"interaction_review":d_frozen["review"],
            "review_complete":a_frozen["review"]["review_complete"] and d_frozen["review"]["review_complete"],
            "metrics":call_metrics(rows),"calls":len(rows),"review_calls":sum(row["section"].startswith("review.") for row in rows),
            "max_interaction_review_calls":config.get("max_interaction_review_calls",4),
            "interaction_review_calls":sum(row["section"].startswith("review.") for row in rows if row["prompt_path"].startswith(str(d_dir))),
            "gap_decision_calls":0,"calibrated_at_end":transport.calibrated,
            "unmet_architecture":[g["section"] for g in a_frozen["input"]["degraded_sections"]],
            "unmet_interaction":[s["section"] for s in d_frozen["payload"]["sections"] if s["status"]!="accepted"],
            "freeze_sha256":{"architecture":sha(a_dir/"freeze-manifest.json"),"interaction":sha(d_dir/"interaction-freeze.json")},
            "calls_sha256":sha(output_dir/"calls.jsonl"),"config_digest":canonical_digest(config)}
        write_json_exclusive(output_dir/"run-result.json",report); print(compact(report),flush=True)
    return report


def previous_run(spec):
    """Read frozen first-run evidence; do not reopen it for writes or reset budget."""
    result = read_source(spec); root = Path(spec["path"]).parent
    if result["round"] != 1 or sha(root/"calls.jsonl") != result["calls_sha256"]:
        raise ValueError("Second run needs unchanged first-run evidence")
    with sqlite3.connect("file:"+str(root/"journal/generation.sqlite3")+"?mode=ro&immutable=1",uri=True) as db:
        db.row_factory = sqlite3.Row
        calls = db.execute("SELECT * FROM calls WHERE run_id=?",(result["run_id"],)).fetchall()
        if any(c["state"] in {"RESERVED","DISPATCHED","RESPONSE_RECORDED"} for c in calls):
            raise ValueError("First run has unresolved pending execution")
        charged = sum(c["usage_tokens"] if c["usage_tokens"] is not None else
                      0 if c["state"]=="FAILED_CONFIRMED" else c["reservation"] for c in calls)
        if charged != result["accounting"]["charged_tokens"] or len(calls)!=result["calls"]:
            raise ValueError("First-run cost differs from durable Journal")
    apath = root/"architecture/freeze-manifest.json"
    if sha(apath) != result["freeze_sha256"]["architecture"]: raise ValueError("Prior architecture manifest differs")
    manifest = json.loads(apath.read_bytes()); check_bound(manifest,"Prior architecture freeze")
    for name,digest in manifest["files"].items():
        if sha(apath.parent/name)!=digest: raise ValueError("Prior architecture artifact differs")
    d = load_frozen_interaction(root/"interaction/interaction-freeze.json",expected_sha256=result["freeze_sha256"]["interaction"])
    return root,result,json.loads((apath.parent/"section-decisions.json").read_bytes()),d


def run_unmet(config, declaration, output_dir):
    """Second declared run: only selected unmet units, existing functions, remaining cost."""
    old_root,old,old_a,old_d = previous_run(declaration["previous_run"])
    a_ids = declaration["retry_sections"]["architecture"]; d_ids = declaration["retry_sections"]["interaction"]
    reuse_ids = set(declaration.get("reuse_authored", []))
    if not reuse_ids <= set(d_ids): raise ValueError("Reused authors must belong to the selected unmet D scope")
    if reuse_ids and old_d["review"]["parts"]:
        raise ValueError("Do not reuse a previously reviewed/rejected author through the never-reviewed path")
    if (len(a_ids)!=len(set(a_ids)) or len(d_ids)!=len(set(d_ids))
            or not set(a_ids)<=set(old["unmet_architecture"]) or not set(d_ids)<=set(old["unmet_interaction"])):
        raise ValueError("Second run may select only prior unmet sections")
    validate_previous_budget(config, old)
    remaining = scenario_token_limit(config)-old["accounting"]["charged_tokens"]
    if not 0<declaration["max_tokens"]<=remaining or not 0<=declaration["max_repairs"]<=2:
        raise ValueError("Second run exceeds cumulative token/repair limit")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=SCRIPTS_ROOT.parent,text=True).strip()
    if head!=declaration["source_commit"] or subprocess.check_output(["git","status","--porcelain"],cwd=SCRIPTS_ROOT.parent,text=True).strip():
        raise ValueError("Second run requires its declared clean repository commit")
    groups = {label:[[sid for sid in group if sid in chosen] for group in config["reviews"][label]]
              for label,chosen in (("architecture",a_ids),("interaction",d_ids))}
    groups = {label:[g for g in value if g] for label,value in groups.items()}
    d_remaining = config.get("max_interaction_review_calls",4)-old["interaction_review_calls"]
    if 2*len(groups["interaction"])>d_remaining:
        raise ValueError("Selected D retry cannot fit the remaining configured review allowance; retain its gaps")
    if not a_ids and not d_ids: raise ValueError("No new run when no unmet unit can be attempted")
    p1,projection,all_packets=inputs(config);packets=[p for p in all_packets if p["section"] in a_ids]
    profile=read_source(config["calibration"])
    if (profile["endpoint"],profile["model"])!=(config["endpoint"],config["model"]): raise ValueError("Calibration identity differs")
    output_dir.mkdir(parents=True,exist_ok=False)
    for name,value in (("config.json",config),("declaration.json",declaration),("architecture-packets.json",packets)):
        write_json_exclusive(output_dir/name,value)
    context={"run_id":declaration["run_id"],"wp":config.get("wp", "WP2.3"),"scenario":config["logical_id"],"model":config["model"],"measurement_kind":"model"}
    started=time.time(); transport=ResponsesTransport(endpoint=config["endpoint"],api_key=environment_credential,
        model=config["model"],output_dir=output_dir,deadline=started+declaration["wall_seconds"],reasoning_effort="medium",calibration=profile)
    errors=[];directories=[];lineage={"previous_run":declaration["previous_run"],"unchanged_D_due_to_review_cap":bool(old["unmet_interaction"] and not d_ids)}
    with GenerationJournal(output_dir/"journal") as journal:
        journal.create_run(run_id=context["run_id"],phase="P2",snapshot_digest=canonical_digest(config),contract_digest=canonical_digest(declaration),
            max_calls=declaration["max_calls"],max_tokens=declaration["max_tokens"],wall_seconds=declaration["wall_seconds"],budget_policy="charged-pending")
        # Combine original receipts only for unchanged units. Replaced units need
        # both new receipts; a missing first-round receipt is never invented.
        def retained_review_complete(label, selected, requested, review):
            saved=json.loads((old_root/label/(label+"-review-inputs.json")).read_bytes())
            present={(part["kind"],part["packet_id"]) for part in review["parts"]}
            covered={sid for packet in saved["packets"]
                if all((kind,packet["packet_id"]) in present for kind in ("omr","sqr"))
                for sid in packet["sections"]}
            return set(requested)-set(selected)<=covered
        accepted=old_a["sections"];degraded=[g for g in old_a["degraded"] if g["section"] not in a_ids]
        a_complete=retained_review_complete("architecture",a_ids,
            [p["section"] for p in all_packets],old["architecture_review"])
        if packets:
            a_dir=output_dir/"architecture";directories.append(a_dir)
            generated=architecture.generate_sections(packets=packets,journal=journal,context=context,send=transport,output_dir=a_dir,
                max_repairs=declaration["max_repairs"],prior_records=accepted)
            payload=architecture.review_payload(generated["records"],packets,generated["degraded"],
                reference_records=accepted, reference_packets=all_packets)
            try:review_and_freeze(payload=payload,journal=journal,context=context,send=transport,output_dir=a_dir,collect_only=True,
                groups=groups["architecture"],recompute_groups=config.get("recompute_review_groups", False),namespace="p2-architecture",scope="architecture")
            except (ValueError,TimeoutError) as exc:errors.append(str(exc))
            frozen=architecture.freeze(records=generated["records"],packets=packets,degraded=generated["degraded"],journal=journal,context=context,
                output_dir=a_dir,p1_sha256=config["p1"]["sha256"],projection_sha256=config["projection"]["sha256"],stop_reason=compact(errors),
                reference_records=accepted, reference_packets=all_packets)
            accepted=accepted+frozen["records"];degraded+=frozen["input"]["degraded_sections"]
            a_complete=a_complete and frozen["review"]["review_complete"]
            lineage["new_architecture"]={"path":str(a_dir/"freeze-manifest.json"),"sha256":sha(a_dir/"freeze-manifest.json")}
        flat,selectors=architecture.architecture_input(accepted,degraded,p1_sha256=config["p1"]["sha256"],projection_sha256=config["projection"]["sha256"])
        write_json_exclusive(output_dir/"architecture-combined-input.json",flat)
        d_payload=old_d["payload"]
        d_complete=retained_review_complete("interaction",d_ids,
            d_payload["requested_sections"],old_d["review"])
        if d_ids:
            d_dir=output_dir/"interaction";directories.append(d_dir)
            d_packets=[p for p in interaction_inputs(config,p1,projection,flat,selectors) if p["section"]["id"] in d_ids]
            write_json_exclusive(output_dir/"interaction-packets.json",d_packets)
            with ExitStack() as stack:
                original_sections = {}
                if reuse_ids:
                    authored = json.loads((old_root/"interaction/interaction-authored.json").read_bytes())
                    original_journal = stack.enter_context(GenerationJournal(old_root/"journal", replay_settled_only=True))
                    original_sections = {row["section"]:(row,original_journal) for row in authored["sections"] if row["section"] in reuse_ids}
                    if set(original_sections) != reuse_ids: raise ValueError("Missing original author for declared reuse")
                generated=generate_sections(packets=d_packets,library=load_library(),journal=journal,context=context,send=transport,
                    output_dir=d_dir,max_repairs=declaration["max_repairs"],failure_level="T2",accepted=original_sections)
            try:review_and_freeze(payload=generated["payload"],journal=journal,context=context,send=transport,output_dir=d_dir,collect_only=True,
                groups=groups["interaction"],recompute_groups=config.get("recompute_review_groups", False),namespace="p2-interaction",scope="interaction-design",max_review_calls=config.get("max_interaction_review_calls",4),
                previous_review_calls=old["interaction_review_calls"],max_transport_attempts=1)
            except (ValueError,TimeoutError) as exc:errors.append(str(exc))
            freeze_bounded_interaction(payload=generated["payload"],library=load_library(),journal=journal,context=context,
                output_dir=d_dir,stop_reason=compact(errors))
            new=load_frozen_interaction(d_dir/"interaction-freeze.json",expected_sha256=sha(d_dir/"interaction-freeze.json"))
            d_payload=assemble_sections([s for s in old_d["payload"]["sections"] if s["section"] not in d_ids]+new["payload"]["sections"],
                library=load_library(),requested=old_d["payload"]["requested_sections"])
            d_complete=d_complete and new["review"]["review_complete"]
            lineage["new_interaction"]={"path":str(d_dir/"interaction-freeze.json"),"sha256":sha(d_dir/"interaction-freeze.json")}
        write_json_exclusive(output_dir/"interaction-combined.json",d_payload);write_json_exclusive(output_dir/"freeze-lineage.json",lineage)
        rows=[json.loads(line) for folder in directories if (folder/"calls.jsonl").exists() for line in (folder/"calls.jsonl").read_text().splitlines()]
        with (output_dir/"calls.jsonl").open("x") as stream:
            for row in rows:stream.write(compact(row)+"\n")
        accounting=journal.accounting(context["run_id"])
        report={"run_id":context["run_id"],"round":2,"source_commit":head,"token_limit":scenario_token_limit(config),"scenario":config["logical_id"],"previous_run":declaration["previous_run"],
            "duration_seconds":time.time()-started,"accounting":accounting,
            "cumulative_charged_tokens":old["accounting"]["charged_tokens"]+accounting["charged_tokens"],
            "metrics":call_metrics(rows),"calls":len(rows),"calls_sha256":sha(output_dir/"calls.jsonl"),"errors":errors,"interaction":d_payload["metrics"],
            "architecture_accepted_sections":len(accepted),"review_complete":a_complete and d_complete,
            "unmet_architecture":[g["section"] for g in degraded],"unmet_interaction":[s["section"] for s in d_payload["sections"] if s["status"]!="accepted"],
            "max_interaction_review_calls":config.get("max_interaction_review_calls",4),
            "interaction_review_calls":sum(row["section"].startswith("review.p2-interaction.") for row in rows),
            "review_calls":sum(row["section"].startswith("review.") for row in rows),"gap_decision_calls":0,
            "lineage_sha256":sha(output_dir/"freeze-lineage.json"),"config_digest":canonical_digest(config),"frozen_after_second_run":True,
            "reused_structure_accepted_authors":sorted(reuse_ids)}
        write_json_exclusive(output_dir/"run-result.json",report);print(compact(report),flush=True)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("mode",choices=["dry-run","run"])
    parser.add_argument("--config",type=Path,required=True);parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--declaration",type=Path)
    args=parser.parse_args(argv);config=json.loads(args.config.read_bytes())
    if args.mode=="dry-run": return 0 if dry_run(config,args.out,
        json.loads(args.declaration.read_bytes()) if args.declaration else None)["ready"] else 2
    if args.declaration is None: parser.error("run requires --declaration")
    run(config,json.loads(args.declaration.read_bytes()),args.out);return 0

if __name__=="__main__":raise SystemExit(main())
