"""Local JSON parsing and native choices, extracted from B 6da99f015.

Values cross the boundary unchanged. No provider schema or transport wrappers.
"""
from __future__ import annotations
from copy import deepcopy
import json
from typing import Any, Mapping
from common.semantic_materialization import MaterializationError, validate_schema

class WireError(ValueError):
    code = "transport-contract-gap"


def parse_raw_object(raw: str, *, allow_identical_duplicates: bool = False) -> tuple[dict[str, Any], str]:
    """Accept one JSON object, or its one redundant terminal object closer.

    No prefix scanning, key repair, truncation repair, or choice between objects.
    The caller MUST validate the entire recovered object before using it.
    """
    duplicates = []
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                if not allow_identical_duplicates or json.dumps(result[key],sort_keys=True,ensure_ascii=False) != json.dumps(value,sort_keys=True,ensure_ascii=False):
                    raise WireError("Duplicate JSON key conflicts or normalization is not enabled")
                duplicates.append(key)
            result[key] = value
        return result

    def bad_constant(value):
        raise WireError("Non-JSON constant: " + value)

    text = raw.strip(" \t\r\n")
    try:
        value, end = json.JSONDecoder(object_pairs_hook=pairs,
                                     parse_constant=bad_constant).raw_decode(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise WireError("Incomplete or invalid JSON object") from exc
    if type(value) is not dict:
        raise WireError("A single JSON object is required")
    suffix = text[end:].strip(" \t\r\n")
    if suffix not in {"", "}"}:
        raise WireError("Extra objects/text are not a recoverable envelope")
    rules = (["identical-json-key-coalescing.v1"] if duplicates else []) + (["single-redundant-object-closer.v1"] if suffix else [])
    return value, "+".join(rules) if rules else "none"


def _select_variant(value: Any, variants: list[dict]) -> int:
    matches = []
    for index, variant in enumerate(variants):
        try:
            validate_schema(value, variant)
            matches.append(index)
        except MaterializationError:
            pass
    if len(matches) != 1:
        raise WireError("Value does not select exactly one semantic variant")
    return matches[0]


def object_depth(schema: Mapping[str, Any]) -> int:
    """Count object layers; array containers and choice alternatives add none."""
    if "oneOf" in schema:
        return max((object_depth(s) for s in schema["oneOf"]), default=0)
    if schema.get("type") == "object":
        return 1 + max((object_depth(s) for s in schema["properties"].values()), default=0)
    if schema.get("type") == "array":
        return object_depth(schema["items"])
    return 0


def native_value(value: Any, schema: Mapping[str, Any]) -> Any:
    """Validate exactly one native shape, preserving absence and explicit values."""
    if object_depth(schema) > 3:
        raise WireError("Local response schema exceeds three object layers; split the section")
    if "oneOf" in schema:
        _select_variant(value, schema["oneOf"])
    else:
        validate_schema(value, schema)
    return deepcopy(value)


def decode_object(raw: str, schema: Mapping[str, Any]) -> tuple[dict, str]:
    value, rule = parse_raw_object(raw)
    return native_value(value, schema), rule
