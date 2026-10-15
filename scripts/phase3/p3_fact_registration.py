"""Compare actual realized schema/config artifacts with frozen facts and P3 deltas.

This checks registration and exact identity, not business reasonableness. The
caller supplies the real OpenAPI, database schema and consumed runtime config,
not a model's self-reported new_facts inventory; artifact hashes bind the proof.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import yaml

from common.agentic_decision_authority import canonical_digest
from common.p3_gap_records import FACT_KINDS, GapDecisionError, effective_truth


def load_frozen_fact_index(sources):
    """Read SHA-bound original IDs. ``basis`` admits source rules/context for reasoning
    without classifying them as a newly realized entity/role/permission/state/field.
    Generated new_facts still accept only the five realized fact categories.
    """
    from common.semantic_materialization import get_pointer
    result={}
    for source in sources:
        path=Path(source['path']);raw=path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest()!=source['sha256'].removeprefix('sha256:'):
            raise GapDecisionError("Frozen source bytes differ")
        document=json.loads(raw)
        for selector in source['selectors']:
            identity=get_pointer(document,selector['id_pointer'])
            original=get_pointer(document,selector['value_pointer'])
            if not isinstance(identity,str) or not identity or identity in result or selector['kind'] not in FACT_KINDS | {"basis"}:
                raise GapDecisionError("Selected original identity/category invalid or repeated")
            pointers=selector.get('comparison_pointers')
            value=[get_pointer(original,p) for p in pointers] if pointers is not None else deepcopy(original)
            result[identity]={'kind':selector['kind'],'value':value,'digest':canonical_digest(original),
                'original':deepcopy(original),'source_sha256':hashlib.sha256(raw).hexdigest(),
                'source_path':str(path),'id_pointer':selector['id_pointer'],'value_pointer':selector['value_pointer']}
    return result


def _row(identity, kind, value):
    return {"id":identity,"kind":kind,"value":value}


def _resolve_schema(schema, document, seen_refs=()):
    if not isinstance(schema, dict):
        raise GapDecisionError("OpenAPI schema must be an object")
    if "$ref" not in schema:
        return schema, seen_refs
    ref = schema["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen_refs:
        raise GapDecisionError("Unresolved/cyclic OpenAPI reference cannot prove no new facts")
    value = document
    try:
        for part in ref[2:].split('/'):
            value = value[part.replace('~1', '/').replace('~0', '~')]
    except (KeyError, TypeError) as exc:
        raise GapDecisionError("Unresolved OpenAPI fact reference") from exc
    resolved, refs = _resolve_schema(value, document, (*seen_refs, ref))
    siblings = {key: value for key, value in schema.items() if key != '$ref'}
    # Descriptions and explicit fact IDs may annotate a reference; structural
    # siblings need conjunction semantics rather than silently overwriting it.
    if {key for key in siblings if not key.startswith('x-')} - {'description', 'title', 'summary'}:
        raise GapDecisionError("Structural OpenAPI reference siblings require explicit parser coverage")
    return {**resolved, **siblings}, refs


def schema_type(schema, document, seen_refs=()):
    schema, refs = _resolve_schema(schema, document, seen_refs)
    value = schema.get("type", "unspecified")
    kinds = value if isinstance(value, list) else [value]
    if "type" in schema and (not kinds or any(not isinstance(k,str) or k not in
            {"null","boolean","object","array","number","integer","string"} for k in kinds)):
        raise GapDecisionError("Unsupported OpenAPI schema type")
    types = []
    for kind in kinds:
        if kind=="array" and "items" in schema:
            item=schema_type(schema["items"],document,refs)
            types.append(("("+item+")" if "|" in item else item)+"[]")
        else:types.append(kind)
    if schema.get("nullable") and "null" not in types: types.append("null")
    return "|".join(sorted(set(types)))


def comparison_value(fact, identity=None):
    """Project explicit representation, never infer business semantics from prose."""
    kind, value = fact["kind"], fact["value"]
    identity=fact.get("id", "") if identity is None else identity
    if not isinstance(identity, str):
        raise GapDecisionError("Fact ID must be a string; got " + type(identity).__name__
                               + ": " + json.dumps(identity, ensure_ascii=False))
    if kind == "basis" and isinstance(value, dict):
        if all(key in value for key in ("operation_id", "method", "path")):
            return "api_fields", [value["method"].lower(), value["path"]], "P2 operation method/path"
        if all(key in value for key in ("field_id", "name", "data_type")):
            return "api_fields", [value["name"], normalize_type(value["data_type"])], "P2 field name/data_type"
    if kind=="api_fields" and isinstance(value,str):
        # A leading explicit type/method is a projection, not proof of the prose
        # qualifications. Complete SQL definitions and semantic review still apply.
        operation=re.fullmatch(r"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE) (/[^ ;]+)(?:;.*)?",value,re.S)
        if identity.startswith("api:") and operation:
            return kind,[operation[1].lower(),operation[2]],"explicit method/path in registered description"
        field=re.fullmatch(r"(String|Integer|Number|Boolean|TEXT|INTEGER|REAL)(?: NOT NULL)?(?:;.*)?",value,re.S)
        if "." in identity and field:
            value=[identity.rsplit(".",1)[1],field[1].lower()]
    if kind == "api_fields" and isinstance(value, list) and len(value)==2 and all(isinstance(v,str) for v in value):
        if value[0].lower() in {"get","post","put","patch","delete","head","options","trace"} and value[1].startswith("/"):
            return kind, [value[0].lower(), value[1]], "HTTP method case"
        datatype=normalize_type(value[1])
        if identity.startswith("db:"):
            datatype={"text":"string","real":"number"}.get(datatype,datatype)
        return kind, [value[0], datatype], "explicit field type (shared DB identity maps TEXT/string and REAL/number)"
    return kind, value, "exact value"


def enum_members(value):
    if not isinstance(value,str):return None
    match=re.fullmatch(r"enum\(([A-Za-z_][A-Za-z_0-9-]*(?:,[A-Za-z_][A-Za-z_0-9-]*)*)\)",value)
    return match[1].split(",") if match else None


def normalize_type(value):
    # Preserve array element types and nullability; no TEXT/string or UUID/string
    # equivalence: those belong to different schema domains/constraints.
    return "|".join(sorted(set("string" if enum_members(part.strip()) is not None else part.strip().lower() for part in value.split("|"))))


def projected_known(fact, truth):
    known=truth.get(fact["id"])
    if known is not None: return known, fact["id"]
    # Parser namespace is derived only from an exact upstream operation ID.
    if fact["id"].startswith("api:"):
        identity=fact["id"][4:]; candidate=truth.get(identity)
        if candidate and isinstance(candidate["value"],dict) and candidate["value"].get("operation_id")==identity:
            return candidate, identity
    if fact["id"].endswith(".enum"):
        identity=fact["id"][:-5]; candidate=truth.get(identity)
        if candidate and isinstance(candidate["value"],dict):
            values=candidate["value"].get("enum",enum_members(candidate["value"].get("data_type")))
            if values is not None:return {**candidate,"kind":"states","value":values}, identity
    return None, None


def _schema_fields(schema, prefix, document, seen_refs=()):
    schema, refs = _resolve_schema(schema, document, seen_refs)
    if schema.get('enum') is not None:
        identity = schema.get('x-wff-fact-id', prefix)
        # Preserve malformed annotations for an explicit registration finding;
        # never coerce a list/dict to a plausible string identity.
        yield _row(identity + '.enum' if isinstance(identity, str) and identity else identity,
                   'states', schema['enum'])
    for name, prop in schema.get('properties', {}).items():
        resolved, _ = _resolve_schema(prop, document, refs)
        field = prefix + '.' + name
        yield _row(resolved.get('x-wff-fact-id', field), 'api_fields', [name, schema_type(resolved, document, refs)])
        yield from _schema_fields(prop, field, document, refs)
    if 'items' in schema:
        yield from _schema_fields(schema['items'], prefix + '[]', document, refs)
    if 'contentSchema' in schema:
        # A JSON-encoded string is still a declared business payload; inspecting
        # only its outer string type would hide its nested fields and states.
        yield from _schema_fields(schema['contentSchema'], prefix + '.content', document, refs)
    for key in ('allOf', 'oneOf', 'anyOf'):
        for index, child in enumerate(schema.get(key, [])):
            yield from _schema_fields(child, prefix + f'.{key}.{index}', document, refs)



def load_openapi_document(raw):
    """Read original JSON or YAML OpenAPI bytes without rewriting the artifact."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    class OriginalMappingLoader(yaml.SafeLoader):
        # OAS uses JSON-compatible value tags and failsafe scalar-string keys.
        # Keep the resolver local: never change PyYAML's process-wide loaders.
        yaml_implicit_resolvers = {}

        def construct_mapping(self, node, deep=False):
            result = {}
            for key_node, value_node in node.value:
                if not isinstance(key_node, yaml.ScalarNode) or key_node.tag not in {
                        "tag:yaml.org,2002:str", "tag:yaml.org,2002:int",
                        "tag:yaml.org,2002:float", "tag:yaml.org,2002:bool",
                        "tag:yaml.org,2002:null"}:
                    raise GapDecisionError("Ambiguous YAML OpenAPI mapping key")
                key = self.construct_scalar(key_node)
                if key in result:
                    raise GapDecisionError("Ambiguous YAML OpenAPI mapping key")
                result[key] = self.construct_object(value_node, deep=deep)
            return result

        def construct_object(self, node, deep=False):
            if node.tag not in {"tag:yaml.org,2002:" + kind for kind in
                               ("str", "int", "float", "bool", "null", "seq", "map")}:
                raise GapDecisionError("Unsupported YAML OpenAPI tag")
            return super().construct_object(node, deep=deep)

    def scalar(loader, node):
        value = loader.construct_scalar(node)
        if value == "" and node.tag == "tag:yaml.org,2002:null": return None
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise GapDecisionError("Non-JSON YAML OpenAPI scalar") from exc
        valid = {"int":type(parsed) is int, "float":type(parsed) in {int,float},
                 "bool":type(parsed) is bool, "null":parsed is None}
        if not valid[node.tag.rsplit(":",1)[-1]]:
            raise GapDecisionError("YAML OpenAPI scalar tag/value differs")
        return parsed

    patterns = {"null":r"^(?:null|)$", "bool":r"^(?:true|false)$",
        "int":r"^-?(?:0|[1-9][0-9]*)$",
        "float":r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?$"}
    for kind, pattern in patterns.items():
        tag = "tag:yaml.org,2002:" + kind
        OriginalMappingLoader.add_implicit_resolver(tag, re.compile(pattern), None)
        OriginalMappingLoader.add_constructor(tag, scalar)

    try:
        document = yaml.load(raw, Loader=OriginalMappingLoader)
        json.dumps(document, allow_nan=False)  # Require an acyclic JSON-compatible value.
        return document
    except (yaml.YAMLError, ValueError) as exc:
        raise GapDecisionError("Unreadable YAML OpenAPI artifact") from exc


def openapi_facts(document):
    if not isinstance(document,dict) or not isinstance(document.get('paths'),dict):
        raise GapDecisionError("Actual OpenAPI paths required")
    result=[]
    for path,item in document['paths'].items():
        if not isinstance(item,dict) or '$ref' in item: raise GapDecisionError('Unresolved OpenAPI path reference')
        for method,operation in item.items():
            if method.lower() not in {'get','put','post','delete','options','head','patch','trace'}:continue
            if not isinstance(operation,dict) or not operation.get('operationId'):
                raise GapDecisionError("Every realized operation needs its original/registered operation identity")
            op=operation['operationId']
            if not isinstance(op, str):
                raise GapDecisionError("OpenAPI operationId must be a nonempty string; got "
                                       + type(op).__name__ + ": " + json.dumps(op, ensure_ascii=False))
            result.append(_row('api:'+op,'api_fields',[method.lower(),path]))
            for parameter in item.get('parameters',[])+operation.get('parameters',[]):
                parameter, _ = _resolve_schema(parameter, document)
                value, _ = _resolve_schema(parameter.get('schema', {}), document)
                name = parameter['name']
                result.append(_row(parameter.get('x-wff-fact-id',f'api:{op}:{parameter["in"]}.{name}'),
                    'api_fields',[name,schema_type(value,document)]))
            if '$ref' in operation.get('requestBody',{}): raise GapDecisionError('Unresolved OpenAPI body reference')
            for media,value in operation.get('requestBody',{}).get('content',{}).items():
                result.extend(_schema_fields(value.get('schema',{}),f'api:{op}:request',document))
            for status,response in operation.get('responses',{}).items():
                if '$ref' in response: raise GapDecisionError('Unresolved OpenAPI response reference')
                for media,value in response.get('content',{}).items():
                    result.extend(_schema_fields(value.get('schema',{}),f'api:{op}:response:{status}',document))
    return result


def sql_facts(text):
    """Read realized CREATE TABLE declarations; ambiguous DDL is an evidence gap."""
    clean=re.sub(r'/\*.*?\*/|--[^\n]*','',text,flags=re.S)
    if re.search(r'\b(?:ALTER|DROP|TRIGGER|CREATE\s+(?:TYPE|DOMAIN|VIEW))\b', clean, re.I):
        raise GapDecisionError("Unparsed realized DDL cannot prove no new facts")
    if re.search(r'\b(?:CHECK|ENUM)\s*\(', clean, re.I):
        raise GapDecisionError("SQL state/constraint declarations require explicit parser coverage")
    result=[];matched=0
    pattern=r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["`]?([\w.]+)["`]?\s*\((.*?)\)\s*;'
    for match in re.finditer(pattern,clean,re.I|re.S):
        matched+=1;table,body=match.groups();result.append(_row('db:'+table,'entities',table))
        parts=re.split(r',\s*(?![^()]*\))',body)
        for part in parts:
            part=part.strip()
            if re.match(r'(?:CONSTRAINT|PRIMARY|FOREIGN|UNIQUE|CHECK)\b',part,re.I):continue
            field=re.match(r'["`]?([\w]+)["`]?\s+([A-Za-z]+(?:\s+PRECISION)?(?:\([^)]*\))?(?:\[\])?)',part,re.I)
            if not field:raise GapDecisionError("Unsupported realized SQL field; no zero-unregistered claim")
            name,kind=field.groups();result.append(_row('db:'+table+'.'+name,'api_fields',[name,kind.lower()]))
    if len(re.findall(r'CREATE\s+TABLE\b',clean,re.I))!=matched:
        raise GapDecisionError("Unsupported CREATE TABLE declaration")
    return result


def runtime_config_facts(document):
    """The role/permission/state arrays consumed by the application, not claimed changes."""
    required={'roles','permissions','states'}
    if not isinstance(document,dict) or not required<=set(document):
        raise GapDecisionError("Consumed runtime config must expose roles, permissions and states")
    result=[]
    for kind in sorted(required):
        if not isinstance(document[kind],list):raise GapDecisionError("Runtime fact arrays required")
        for row in document[kind]:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'] or 'value' not in row:
                raise GapDecisionError("Runtime fact identity/value required")
            identity = row.get('x-wff-fact-id', row['id'])
            if not isinstance(identity, str) or not identity:
                raise GapDecisionError('Runtime registration identity must be a nonempty string')
            result.append(_row(identity,kind,row['value']))
    return result


def check_realized_facts(*, root, artifacts, frozen_facts, records):
    """Bind findings to actual artifacts; missing parser coverage is not a zero result."""
    root=Path(root).resolve();view=effective_truth(frozen_facts,records)
    observed=[];sources=[];coverage=set();paths=set()
    for artifact in artifacts:
        relative=Path(artifact['path']);path=root/relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise GapDecisionError("Realized artifact must be an existing contained regular file")
        if path in paths:raise GapDecisionError("Duplicate realized artifact path")
        paths.add(path);raw=path.read_bytes();format=artifact['format']
        if format=='openapi':
            facts=openapi_facts(load_openapi_document(raw));coverage.update({'api_fields','states'})
        elif format=='sql':
            facts=sql_facts(raw.decode());coverage.update({'entities','api_fields'})
        elif format=='sqlite-ddl':
            from phase3.p3_sqlite_facts import sqlite_facts
            facts=sqlite_facts(raw.decode());coverage.update({'entities','api_fields'})
        elif format=='runtime-config':
            facts=runtime_config_facts(json.loads(raw));coverage.update({'roles','permissions','states'})
        else:raise GapDecisionError("Unknown realized artifact parser cannot prove absence")
        digest=hashlib.sha256(raw).hexdigest()
        sources.append({'path':str(relative),'sha256':digest,'format':format,'fact_count':len(facts)})
        observed.extend({**fact,'artifact':str(relative),'artifact_sha256':digest} for fact in facts)
    if coverage!=FACT_KINDS:raise GapDecisionError("Missing actual artifact coverage for fact categories")
    unregistered=[];registered=[];seen={};conflicts=set();valid=[]
    for fact in observed:
        if not isinstance(fact["id"], str) or not fact["id"]:
            unregistered.append({**fact,"reason":"invalid-fact-id","registered_identity":None,
                "diagnostic":"Fact ID must be a nonempty string; got " + type(fact["id"]).__name__})
        else:
            valid.append(fact)
    for fact in valid:
        key=(fact['kind'],fact['id']);signature=canonical_digest(comparison_value(fact)[:2])
        if key in seen and seen[key]!=signature:conflicts.add(key)
        seen[key]=signature
    for fact in valid:
        key=(fact['kind'],fact['id']);signature=canonical_digest(comparison_value(fact)[:2])
        if key in conflicts:
            unregistered.append({**fact,'reason':'conflicting-realized-identity','registered_identity':None})
            continue
        known,identity=projected_known(fact,view['facts'])
        actual=comparison_value(fact);expected=comparison_value(known,identity) if known else None
        if not known or not known['active'] or actual[:2]!=expected[:2]:
            reason=('missing-fact' if not known else 'inactive-fact' if not known['active'] else
                    'representation-unresolved' if isinstance(known['value'],str) and not isinstance(fact['value'],str) else 'different-fact')
            unregistered.append({**fact,'reason':reason,'registered_identity':identity})
        else:registered.append({**fact,'delta_id':known.get('delta_id'),'source_id':known.get('source_id'),
            'registered_identity':identity,'comparison_projection':expected[2]})
    report={'schema_version':'wff.p3-fact-registration-check.v1','artifacts':sources,
        'observed_fact_count':len(observed),'registered':registered,'unregistered':unregistered,
        'unregistered_count':len(unregistered),'new_identity_count':sum(r['reason']=='missing-fact' for r in unregistered),
        'unresolved_representation_count':sum(r['reason']=='representation-unresolved' for r in unregistered),
        'invalid_identity_count':sum(r['reason']=='invalid-fact-id' for r in unregistered),
        'conflicting_identity_count':len(conflicts),'checked_categories':sorted(coverage),
        'zero_unregistered':not unregistered,'upstream_reconciled':False,
        'claim_ceiling':'Registration of facts in these exact realized schema/config bytes; semantic reasonableness and actual runtime use require the existing implementation review and runtime evidence.'}
    report['content_digest']=canonical_digest(report)
    return report


def validate_read_model_bindings(*, root, bindings, resolution, ledger):
    """A registered decision alone does not create a realized read-model contract."""
    if not bindings or not isinstance(bindings,list): return False
    record=next((r for r in ledger.get('records',[]) if r.get('id')==resolution['id']),None)
    if record is None:return False
    registered=record.get('new_facts',[])+record.get('inferred_facts',[])
    root=Path(root).resolve()
    for binding in bindings:
        if not isinstance(binding,dict) or binding.get('decision_id')!=resolution['id'] or binding.get('decision_digest')!=resolution['digest']:
            return False
        relative=Path(binding.get('artifact',''));path=root/relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):return False
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=binding.get('artifact_sha256'):return False
        method=binding.get('method','').lower();route=binding.get('path');op=binding.get('operation_id')
        try:operation=json.loads(raw)['paths'][route][method]
        except (ValueError,KeyError,TypeError):return False
        expected=_row('api:'+str(op),'api_fields',[method,route])
        if operation.get('operationId')!=op or expected not in registered:return False
    return True


def realized_read_model_resolution(*, root, requirements):
    from common.p3_gap_records import registered_resolution
    root = Path(root)
    if root.name == ".phase3-evidence": root = root.parent
    ledger_path = root / ".phase3-evidence" / "p3-authority-delta-ledger.json"
    if not ledger_path.is_file() or ledger_path.is_symlink(): return None
    try:
        ledger = json.loads(ledger_path.read_text())
        resolution = registered_resolution(ledger, "business-read-model-authority-missing")
        if resolution and validate_read_model_bindings(root=root,
                bindings=requirements.get("p3_read_model_bindings"), resolution=resolution, ledger=ledger):
            return resolution
    except (ValueError, TypeError, KeyError, OSError):
        return None
    return None
