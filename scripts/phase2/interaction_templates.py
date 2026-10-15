"""Neutral D templates, original-ID input selection and bounded local decoding."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import html
import re
import json
from pathlib import Path
from typing import Any, Mapping

from common.agentic_decision_authority import canonical_digest
from common.semantic_materialization import get_pointer, load_json_strict, validate_schema, MaterializationError
from common.semantic_generation_wire import parse_raw_object, object_depth, WireError
from phase2.p1_input_projection import select_items, validate_projection

LIBRARY_PATH = Path(__file__).with_name("data") / "interaction-design-v1.json"
MAX_REQUEST_TOKENS = 60_000
MAX_OUTPUT_TOKENS = 8_000
MAX_SLOT_CHARS = 3_200
ID_FIELDS = {"commitment_id": "commitment", "context_id": "context", "object_id": "object",
             "feature_id": "feature", "decision_id": "decision", "role_id": "role",
             "actor_id": "role", "operation_id": "operation", "action_id": "action",
             "state_id": "state", "transition_id": "transition", "attribute_id": "attribute",
             "field_id": "field", "service_id": "service", "contract_id": "contract"}


class InteractionError(ValueError):
    pass


def bound(body: Mapping[str, Any]) -> dict:
    result = deepcopy(dict(body))
    result.pop("content_digest", None)
    return {**result, "content_digest": canonical_digest(result)}


def check_bound(value: Mapping[str, Any], label: str) -> None:
    if not isinstance(value, dict) or value.get("content_digest") != canonical_digest(
            {k: v for k, v in value.items() if k != "content_digest"}):
        raise InteractionError(label + " digest differs")


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_library(path: Path = LIBRARY_PATH) -> dict:
    data = load_json_strict(path)
    if data.get("version") != "interaction-design@1":
        raise InteractionError("Unsupported template version")
    for name in ("sections", "patterns"):
        ids = [row["id"] for row in data[name]]
        if len(ids) != len(set(ids)):
            raise InteractionError("Duplicate template identity")
    library = bound(data)
    if object_depth(response_schema(library)) > 3:
        raise InteractionError("Local response schema exceeds three object layers")
    return library


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def _array(items: dict, maximum: int = 24) -> dict:
    return {"type": "array", "items": items, "maxItems": maximum}


def response_schema(library: dict) -> dict:
    text = {"type": "string"}
    params, slots = {}, {"reason": text}
    for card in library["patterns"]:
        for key, spec in card["params"].items():
            schema = _array(text) if spec["many"] else text
            if key in params and params[key] != schema:
                raise InteractionError("Parameter cardinality differs between cards")
            params[key] = schema
        slots.update({key: text for key in card["slots"]})
    use = _object({"pattern": text, "params": _object(params, []), "trim": _array(text),
                   "slots": _object(slots, [])}, ["pattern", "params", "trim", "slots"])
    custom = _object({"title": text, "text": text, "refs": _array(text), "reason": text},
                     ["title", "text", "refs", "reason"])
    gap = _object({"kind": {"type": "string", "enum": ["T1", "T2"]},
                   "question": text, "refs": _array(text)}, ["kind", "question"])
    return _object({"section": text, "uses": _array(use, 16), "custom": _array(custom, 12),
                    "gaps": _array(gap, 24)}, ["section", "uses", "custom", "gaps"])


def architecture_references(raw: bytes, *, expected_sha256: str, logical_id: str,
                            selectors: list[dict]) -> list[dict]:
    """Read actual field identities from a separately frozen architecture input.

    Selectors name original JSON pointers, never replacement values or labels.
    This reader establishes provenance, not an architecture acceptance verdict.
    """
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256.removeprefix("sha256:") or not logical_id:
        raise InteractionError("Architecture frozen source SHA or identity differs")
    def pairs(rows):
        value = {}
        for key, child in rows:
            if key in value:
                raise InteractionError("Duplicate architecture source key")
            value[key] = child
        return value
    source = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(InteractionError("Non-JSON source number")))
    result = []
    for selector in selectors:
        if set(selector) != {"id_pointer", "value_pointer"}:
            raise InteractionError("Architecture selection only names original ID/value pointers")
        id_pointer, value_pointer = selector["id_pointer"], selector["value_pointer"]
        if id_pointer.rsplit("/", 1)[0] != value_pointer:
            raise InteractionError("Architecture ID must belong to the selected original row")
        field = id_pointer.rsplit("/", 1)[-1]
        if field not in ID_FIELDS:
            raise InteractionError("Original architecture ID family is unknown")
        row = get_pointer(source, value_pointer); identity = get_pointer(source, id_pointer)
        if not isinstance(row, dict) or not isinstance(identity, str) or not identity:
            raise InteractionError("Architecture row or original identity is invalid")
        result.append(bound({"id": identity, "family": ID_FIELDS[field], "value": row,
            "id_pointer": id_pointer, "source": {"logical_id": logical_id,
                "sha256": "sha256:" + actual, "path": value_pointer, "value_digest": canonical_digest(row)}}))
    return result


def prepare_section(*, projection: dict, p1_raw: bytes, expected_p1_sha256: str,
                    logical_id: str, section: str, selection: Mapping[str, list[str]],
                    architecture: list[dict] | None = None, library: dict | None = None) -> dict:
    library = load_library() if library is None else library
    check_bound(library, "Template library")
    validate_projection(projection, p1_raw, expected_sha256=expected_p1_sha256, logical_id=logical_id)
    skeleton = next((s for s in library["sections"] if s["id"] == section), None)
    if skeleton is None:
        raise InteractionError("Unknown section identity")
    references = {}
    for category, identities in selection.items():
        for row in select_items(projection, category=category, p1_ids=identities):
            key = (row["p1_id_kind"], row["p1_id"], row["source"]["path"])
            if key not in references:
                references[key] = {"id": row["p1_id"], "family": row["p1_id_kind"],
                    "id_pointer": row["id_pointer"], "source": deepcopy(row["source"]), "value": {}}
            for field, value in row["value"].items():
                existing = references[key]["value"]
                if field in existing and existing[field] != value:
                    raise InteractionError("Original field differs between projections")
                existing[field] = deepcopy(value)
    rows = [bound(row) for row in references.values()]
    for document in architecture or []:
        # Re-read exact frozen bytes here; a caller-supplied rehashed reference is not source proof.
        if set(document) != {"raw", "expected_sha256", "logical_id", "selectors"}:
            raise InteractionError("Architecture inputs require raw frozen bytes and original selectors")
        rows.extend(architecture_references(**document))
    cards = [card for card in library["patterns"] if card["id"] in skeleton["patterns"]]
    paths = [row["source"]["path"] for row in rows]
    global_gap_paths = ("/unresolved_items/", "/context_sufficiency/missing_facts/",
                        "/interaction_relevant_product_context/unresolved_items/")
    upstream_gaps = [deepcopy(gap) for gap in projection["backport_queue"]
        if gap["source"]["path"].startswith(global_gap_paths) or any(
            gap["source"]["path"] == path or gap["source"]["path"].startswith(path + "/")
            for path in paths if path)]
    return bound({"schema_version": "wff.interaction-section-input.v1", "section": deepcopy(skeleton),
        "projection_digest": projection["content_digest"], "references": rows, "upstream_gaps": upstream_gaps,
        "template_digest": library["content_digest"], "template_version": library["version"],
        "cards": cards, "phrasing": deepcopy(library["phrasing"])})


def share_author_references(packets, *, reference_key="references", include_all=True):
    """Give D authors the same ID-selected records that can coexist in a review.

    Only union the caller's already selected original records, never the full
    projection. Conflict checks and original source bindings stay intact.
    """
    refs = {}
    for packet in packets:
        check_bound(packet, "Author input")
        for row in packet[reference_key]:
            key = source_anchor(row)
            if key not in refs:
                refs[key] = deepcopy(row)
            else:
                for name, value in row["value"].items():
                    if name in refs[key]["value"] and refs[key]["value"][name] != value:
                        raise InteractionError("Selected original author fact conflicts")
                    refs[key]["value"][name] = deepcopy(value)
    rows = [bound(row) for row in refs.values()]
    return [bound({**packet, reference_key: [row for row in rows
        if include_all or source_anchor(row) in {source_anchor(r) for r in packet[reference_key]}]}) for packet in packets]


def resolve_reference(packet: dict, identity: str, families: list[str] | None = None) -> dict:
    rows = [row for row in packet["references"] if row["id"] == identity and
            (not families or "*" in families or row["family"] in families)]
    # A parent ID never selects a child identity; ambiguous original rows need a narrower input selection.
    if len(rows) != 1:
        raise InteractionError("Reference is absent, ambiguous or from another identity family: " + identity)
    return rows[0]


def decode_response(raw: str, library: dict) -> tuple[dict, list[str]]:
    notes = []
    stripped = raw.strip()
    if stripped.startswith("```json\n") and stripped.endswith("\n```"):
        stripped = stripped[len("```json\n"):-len("\n```")]
        notes.append("single-json-fence")
    value, rule = parse_raw_object(stripped)
    if rule != "none":
        notes.append(rule)
    schema = response_schema(library)
    def normalize(item, shape, path):
        if shape.get("type") == "array" and not isinstance(item, list):
            notes.append(path + ":singleton-to-array"); item = [item]
        elif shape.get("type") in {"string", "object"} and isinstance(item, list) and len(item) == 1:
            notes.append(path + ":single-array-to-value"); item = item[0]
        if shape.get("type") == "object" and isinstance(item, dict):
            return {key: normalize(child, shape["properties"][key], path + "/" + key)
                    if key in shape["properties"] else child for key, child in item.items()}
        if shape.get("type") == "array" and isinstance(item, list):
            return [normalize(child, shape["items"], path + "/" + str(i)) for i, child in enumerate(item)]
        return item
    return normalize(value, schema, ""), notes


def validate_response(value: dict, packet: dict, library: dict) -> list[str]:
    diagnostics = []
    try:
        check_bound(packet, "Section input")
        check_bound(library, "Template library")
        if packet["template_digest"] != library["content_digest"]:
            raise InteractionError("Template changed after input selection")
        validate_schema(value, response_schema(library))
        if value["section"] != packet["section"]["id"]:
            raise InteractionError("Response section differs")
        cards = {card["id"]: card for card in packet["cards"]}
        for i, use in enumerate(value["uses"]):
            if use["pattern"] not in cards:
                raise InteractionError(f"uses/{i}: pattern is not a supplied candidate")
            card = cards[use["pattern"]]
            if set(use["params"]) - set(card["params"]):
                raise InteractionError(f"uses/{i}: unknown pattern parameter")
            for key in card["required_params"]:
                if not use["params"].get(key):
                    raise InteractionError(f"uses/{i}/params/{key}: required reference is missing")
            for key, identifiers in use["params"].items():
                for identity in identifiers if card["params"][key]["many"] else [identifiers]:
                    resolve_reference(packet, identity, card["params"][key]["families"])
            if len(use["trim"]) != len(set(use["trim"])) or set(use["trim"]) - set(card["optional_parts"]):
                raise InteractionError(f"uses/{i}/trim: only distinct optional part names may be removed")
            if set(use["slots"]) - (set(card["slots"]) | {"reason"}):
                raise InteractionError(f"uses/{i}/slots: unknown slot")
            for key in card["required_slots"] + (["reason"] if use["trim"] else []):
                if not use["slots"].get(key, "").strip():
                    raise InteractionError(f"uses/{i}/slots/{key}: required text is missing")
            for key, text in use["slots"].items():
                limit = card["slots"].get(key, {}).get("max_chars", MAX_SLOT_CHARS)
                if len(text) > limit:
                    raise InteractionError(f"uses/{i}/slots/{key}: exceeds {limit} characters")
        for kind in ("custom", "gaps"):
            for i, row in enumerate(value[kind]):
                for field, child in row.items():
                    if isinstance(child, str) and len(child) > MAX_SLOT_CHARS:
                        raise InteractionError(f"{kind}/{i}/{field}: exceeds {MAX_SLOT_CHARS} characters")
                for identity in row.get("refs", []):
                    resolve_reference(packet, identity)
                required_text = ("title", "text", "reason") if kind == "custom" else ("question",)
                if any(not row[key].strip() for key in required_text):
                    raise InteractionError(f"{kind}/{i}: named text is empty")
                if kind == "custom" and not row["reason"].strip():
                    raise InteractionError(f"custom/{i}: deviation reason is missing")
    except MaterializationError as exc:
        diagnostics.append(f"{exc} [{exc.code} at {exc.path or '/'}]")
    except InteractionError as exc:
        diagnostics.append(str(exc))
    return diagnostics



def _escape(text: Any) -> str:
    value = text if isinstance(text, str) else compact(text)
    return re.sub(r"([\\`*_{}\[\]()#+!|])", r"\\\1", html.escape(value))


def source_anchor(row: dict) -> str:
    return "source-" + canonical_digest({"id": row["id"], "family": row["family"],
        "source": row["source"]}).split(":")[-1][:20]


def reference_label(row: dict, parameter: str = "") -> str:
    keys = ("user_role_or_actor", "role", "name", "label") if parameter in {"actor", "actors"} else (
        "name", "label", "task", "statement")
    for key in keys:
        if isinstance(row["value"].get(key), str) and row["value"][key]:
            return row["value"][key]
    return row["id"]


def _link(row: dict, parameter: str = "") -> str:
    return f"[{_escape(reference_label(row, parameter))}](#{source_anchor(row)}) (`{_escape(row['id'])}`)"


def render_section(value: dict, packet: dict, library: dict) -> dict:
    """Execute the selected structure without supplying absent business values."""
    diagnostics = validate_response(value, packet, library)
    if diagnostics:
        raise InteractionError("; ".join(diagnostics))
    section = packet["section"]; cards = {row["id"]: row for row in packet["cards"]}
    lines = []; sources = {}; delegated = []
    for number, use in enumerate(value["uses"], 1):
        card = cards[use["pattern"]]; block_id = f"{section['id']}-pattern-{number}"
        lines += [f'<a id="{block_id}"></a>', f"### {number}. {_escape(card['title'])}", ""]
        by_param = {}
        for key, identifiers in use["params"].items():
            ids = identifiers if card["params"][key]["many"] else [identifiers]
            rows = [resolve_reference(packet, identity, card["params"][key]["families"]) for identity in ids]
            by_param[key] = rows
            lines += [f"- {_escape(key)}: " + "; ".join(_link(row, key) for row in rows)]
            for row in rows:
                sources[source_anchor(row)] = row
        lines.append("")
        if use["pattern"] == "pat.role-permission@1":
            lines += ["| Actor | Operation | Original authority |", "|---|---|---|"]
            for actor in by_param.get("actors", []):
                for operation in by_param.get("actions", []):
                    facts = operation["value"]
                    access = facts.get("terminal_access", {})
                    allowed = facts.get("allowed_roles", access.get("allowed_roles", []) if isinstance(access, dict) else [])
                    known = isinstance(allowed, list) and any(x in allowed for x in
                        (actor["id"], reference_label(actor, "actors")))
                    posture = "Explicit in the referenced operation" if known else packet["phrasing"]["undecided"]
                    lines.append(f"| {_link(actor, 'actors')} | {_link(operation)} | {_escape(posture)} |")
            lines.append("")
        elif use["pattern"] == "pat.state-machine@1":
            lines += ["| Transition reference | Original from | Original to |", "|---|---|---|"]
            for transition in by_param.get("transitions", []):
                facts = transition["value"]
                # Only explicit original fields; do not infer an edge from names or order.
                start = facts.get("from_state", facts.get("from", packet["phrasing"]["undecided"]))
                end = facts.get("to_state", facts.get("to", packet["phrasing"]["undecided"]))
                lines.append(f"| {_link(transition)} | {_escape(start)} | {_escape(end)} |")
            lines.append("")
        elif use["pattern"] == "pat.wizard@1":
            for i, row in enumerate(by_param.get("tasks", []), 1):
                lines.append(f"{i}. {_link(row)}")
            lines.append("")
        for part in card["parts"]:
            if part["id"] in use["trim"]:
                continue
            lines += [f"#### {_escape(part['title'])}", ""]
            for key in part.get("params", []):
                for source in by_param.get(key, []):
                    lines.append("- " + _link(source, key))
            supplied = [key for key in part.get("slots", []) if key in use["slots"]]
            for key in supplied:
                lines += [f"**{_escape(key.replace('_', ' '))}**", "", _escape(use["slots"][key]), ""]
            if not supplied:
                lines += [_escape(part.get("text", packet["phrasing"]["undecided"])), ""]
        if "reason" in use["slots"]:
            lines += ["Reason: " + _escape(use["slots"]["reason"]), ""]
        if use["pattern"] == "pat.delegation@1":
            delegated.append(bound({"id": "D-DEL-" + block_id, "scope": deepcopy(use["params"]["scope"]),
                **{key: use["slots"][key] for key in card["required_slots"]},
                "source_section": section["id"], "confirmation_posture": "Not human approval"}))
    for number, row in enumerate(value["custom"], 1):
        block = len(value["uses"]) + number
        lines += [f'<a id="{section["id"]}-custom-{number}"></a>',
                  f"### {block}. {_escape(row['title'])}", "", _escape(row["text"]), "",
                  "Reason: " + _escape(row["reason"]), "",
                  _escape(packet["phrasing"]["custom_ceiling"]), ""]
        for identity in row["refs"]:
            source = resolve_reference(packet, identity); sources[source_anchor(source)] = source
            lines.append("- " + _link(source))
    gaps = deepcopy(value["gaps"])
    if not value["uses"] and not value["custom"] and not gaps:
        gaps.append({"kind": "T1", "question": "No section content was supplied; downstream design inference remains open.", "refs": []})
    for gap in gaps:
        lines += [f"- {_escape(gap['kind'])} gap: {_escape(gap['question'])}"]
        for identity in gap.get("refs", []):
            row = resolve_reference(packet, identity); sources[source_anchor(row)] = row
            lines.append("  - " + _link(row))
    return bound({"schema_version": "wff.interaction-section.v1", "section": section["id"],
        "title": section["title"], "input_digest": packet["content_digest"],
        "template_version": packet["template_version"], "template_digest": packet["template_digest"],
        "payload": deepcopy(value), "markdown": "\n".join(lines).strip() + "\n",
        "provenance": list(sources.values()), "claim_ceiling": packet["phrasing"]["source_ceiling"],
        "claim_ceilings": {"source": packet["phrasing"]["source_ceiling"],
                           **({"custom": packet["phrasing"]["custom_ceiling"]} if value["custom"] else {}),
                           **({"gap": packet["phrasing"]["gap_ceiling"]} if gaps else {})},
        "gaps": gaps, "delegation_rules": delegated, "custom_blocks": len(value["custom"]),
        "pattern_blocks": len(value["uses"]), "status": "accepted"})


def reference_catalog(references, *, allow_architecture_records=False):
    """Validate selected identities locally and expose their exact family/labels."""
    families = {}; values = {}; labels = set(); identity_families = {}
    for row in references:
        identity, family, value = row.get("id"), row.get("family"), row.get("value")
        if not isinstance(identity, str) or not identity or family not in {*ID_FIELDS.values(), "architecture-author-record"} or not isinstance(value, dict):
            raise InteractionError("Invalid selected reference identity/family/value")
        existing = identity_families.setdefault(identity, set())
        combined = existing | {family}
        if len(combined) > 1 and not (allow_architecture_records and "architecture-author-record" in combined and len(combined)==2):
            raise InteractionError("Ambiguous selected reference identity: " + identity)
        existing.add(family)
        key = (family, identity)
        visible = model_fact_value(value)
        if key in values and values[key] != visible:
            raise InteractionError("Conflicting selected reference values: " + identity)
        values[key] = visible
        families.setdefault(family, set()).add(identity)
        label = value.get("user_role_or_actor")
        if label is not None:
            if not isinstance(label, str) or not label.strip():
                raise InteractionError("Invalid original role label")
            labels.add(label)
    return {"ids_by_family": {key: sorted(ids) for key, ids in sorted(families.items())},
            "role_labels": sorted(labels)}


def model_fact_value(value):
    """Original business fields only; citation metadata stays in retained inputs."""
    metadata = {"backfill_refs", "context_refs", "source_answer_digest", "source_pointer", "source_refs", "source_section"}
    if value.get("status") == "degraded-T2" and value.get("source_section"):
        return {"status":"degraded-T2", "question":value["source_section"]+" unavailable (T2)"}
    return {key: deepcopy(item) for key,item in value.items() if key not in metadata}


def assemble_sections(sections: list[dict], *, library: dict, requested: list[str] | None = None) -> dict:
    check_bound(library, "Template library")
    ordered = [row for row in library["sections"] if requested is None or row["id"] in requested]
    if requested is not None and (len(set(requested)) != len(requested) or {r["id"] for r in ordered} != set(requested)):
        raise InteractionError("Unknown or duplicate requested section")
    by_id = {}
    for section in sections:
        check_bound(section, "Accepted/degraded section")
        if section["section"] in by_id or section["template_digest"] != library["content_digest"]:
            raise InteractionError("Duplicate section or changed template")
        by_id[section["section"]] = section
    if set(by_id) - {r["id"] for r in ordered}:
        raise InteractionError("Section outside this assembly")
    lines = ["# Product frontend interaction design", ""]; sources = {}; gaps = []; rendered = []
    for number, skeleton in enumerate(ordered, 1):
        section = by_id.get(skeleton["id"])
        lines += [f'<a id="section-{skeleton["id"]}"></a>', f"## {number}. {_escape(skeleton['title'])}", ""]
        if section is None:
            gap = {"section": skeleton["id"], "kind": "T1", "question": "Section not generated in this bounded run."}
            gaps.append(gap); lines += ["T1 gap: " + gap["question"], ""]
            continue
        rendered.append(section); lines += [section["markdown"], ""]
        gaps.extend({**row, "section": section["section"]} for row in section["gaps"])
        for row in section["provenance"]:
            anchor = source_anchor(row)
            if anchor not in sources:
                sources[anchor] = deepcopy(row)
            else:
                merged = deepcopy(sources[anchor])
                for key, value in row["value"].items():
                    if key in merged["value"] and merged["value"][key] != value:
                        raise InteractionError("Original source field differs across sections")
                    merged["value"][key] = deepcopy(value)
                sources[anchor] = bound(merged)
    lines += ["## Referenced input", ""]
    for anchor, row in sources.items():
        lines += [f'<a id="{anchor}"></a>', f"- `{_escape(row['id'])}` ({_escape(row['family'])}): {_escape(reference_label(row))}",
                  f"  - Frozen source: `{_escape(row['source']['sha256'])}`; pointer: `{_escape(row['source']['path'])}`; value digest: `{_escape(row['source']['value_digest'])}`."]
        for key in ("attributes", "key_attributes", "states", "state", "claim_ceiling"):
            if key in row["value"]:
                lines.append(f"  - {_escape(key)}: {_escape(row['value'][key])}")
    patterns = sum(s["pattern_blocks"] for s in rendered); custom = sum(s["custom_blocks"] for s in rendered)
    return bound({"schema_version": "wff.interaction-design.v1", "review_contract": "p2-omr-sqr.v1",
        "template_digest": library["content_digest"], "template_version": library["version"],
        "requested_sections": [row["id"] for row in ordered], "sections": rendered, "gaps": gaps,
        "markdown": "\n".join(lines).strip() + "\n", "claim_ceiling": library["phrasing"]["source_ceiling"],
        "metrics": {"delivered_sections": sum(s["status"] == "accepted" for s in rendered),
                    "total_sections": len(ordered), "pattern_blocks": patterns, "custom_blocks": custom,
                    "custom_segment_ratio": custom / (patterns + custom) if patterns + custom else 0},
        "delegation_rules": [row for s in rendered for row in s["delegation_rules"]],
        "provenance": list(sources.values())})
