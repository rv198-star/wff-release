"""Mechanical helpers for public semantic proposals, never semantic acceptance.

The schema used to validate an Author response is also the exported public
interface. Native phase validators still own cross-field product/architecture
rules. No allocation maps, workflow scheduling, or business defaults belong here.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from common.agentic_decision_authority import canonical_digest


class MaterializationError(ValueError):
    """A public contract gap with a stable code and JSON-pointer path."""

    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": str(self)}


def load_json_strict(path: Path) -> Any:
    """Reject duplicate keys and non-JSON constants before contract validation."""
    def pairs(rows: list[tuple[str, Any]]) -> dict:
        result: dict[str, Any] = {}
        for key, value in rows:
            if key in result:
                raise MaterializationError("duplicate-json-key", "", "JSON object keys must be unique")
            result[key] = value
        return result

    def invalid_constant(_: str) -> None:
        raise MaterializationError("invalid-json-number", "", "NaN and Infinity are not JSON values")

    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MaterializationError("invalid-json", "", "Input must be a UTF-8 JSON document") from exc


def write_json_exclusive(path: Path, value: Any) -> None:
    """Atomically install one NEW JSON output without replacing prior evidence.

    A same-directory temporary file is fully flushed before an atomic hard-link
    publication. A crash before publication cannot expose partial target bytes.
    The Workflow owns the directory; this is not a claim of adversarial OS isolation.
    """
    target = Path(path).absolute()
    current = Path(target.anchor)
    for part in target.parts[1:-1]:
        current /= part
        if current.is_symlink():
            raise MaterializationError("unsafe-output-path", "", "Output parents cannot be symbolic links")
    if not target.parent.is_dir():
        raise MaterializationError("missing-output-parent", "", "Create a Workflow-owned output directory first")
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, name = tempfile.mkstemp(prefix=".wff-draft-", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError as exc:
            raise MaterializationError("output-exists", "", "Existing outputs must not be overwritten") from exc
        except OSError as exc:
            raise MaterializationError("atomic-output-unavailable", "", "This directory does not support no-replace atomic publication") from exc
        directory_fd = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def obj(properties: Mapping[str, dict], *, optional: tuple[str, ...] = ()) -> dict:
    """Closed object contract: unsupported choices are never silently dropped."""
    if not set(optional).issubset(properties):
        raise ValueError("Optional keys must be declared properties")
    return {"type": "object", "properties": deepcopy(dict(properties)),
            "required": [key for key in properties if key not in optional],
            "additionalProperties": False}


def arr(items: dict, *, minimum: int = 0) -> dict:
    return {"type": "array", "items": deepcopy(items), "minItems": minimum}


def text(*, empty: bool = False) -> dict:
    return {"type": "string", "minLength": 0 if empty else 1}


def choice(values: Any) -> dict:
    return {"type": "string", "enum": sorted(set(values))}


def pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def validate_schema(value: Any, schema: Mapping[str, Any], path: str = "") -> None:
    """Validate the deliberately small exported schema dialect without deps.

    No coercions: a boolean is not an integer, NaN/Infinity are not JSON values,
    a tuple is not a JSON array, and unknown keys fail even inside nested rows.
    """
    if "oneOf" in schema:
        matches = 0
        for variant in schema["oneOf"]:
            try:
                validate_schema(value, variant, path)
                matches += 1
            except MaterializationError:
                pass
        if matches != 1:
            raise MaterializationError("contract-shape", path, "Value must match exactly one declared shape")
        return
    kind = schema.get("type")
    valid_type = {
        "object": type(value) is dict, "array": type(value) is list,
        "string": type(value) is str, "boolean": type(value) is bool,
        "integer": type(value) is int,
        "number": type(value) in (int, float) and (type(value) is int or math.isfinite(value)),
        "null": value is None,
    }
    if kind not in valid_type:
        raise ValueError(f"Unsupported schema type: {kind}")
    if not valid_type[kind]:
        raise MaterializationError("contract-type", path, f"Expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise MaterializationError("contract-enum", path, "Value is outside the public enum")
    if kind == "object":
        props = schema["properties"]
        extra = set(value) - set(props)
        if extra and schema.get("additionalProperties") is False:
            key = sorted(extra)[0]
            raise MaterializationError("unsupported-choice", path + "/" + pointer_token(key), "Choice is not supported by this interface version")
        for key in schema.get("required", []):
            if key not in value:
                raise MaterializationError("missing-choice", path + "/" + pointer_token(key), "Explicit choice is required")
        for key, item in value.items():
            if key in props:
                validate_schema(item, props[key], path + "/" + pointer_token(key))
    elif kind == "array":
        if len(value) < schema.get("minItems", 0):
            raise MaterializationError("missing-choice", path, "Array has too few choices")
        for index, item in enumerate(value):
            validate_schema(item, schema["items"], f"{path}/{index}")
        if schema.get("uniqueItems") and len({canonical_digest(item) for item in value}) != len(value):
            raise MaterializationError("duplicate-choice", path, "Choices must be unique")
    elif kind == "string":
        if len(value) < schema.get("minLength", 0) or (schema.get("minLength", 0) > 0 and not value.strip()):
            raise MaterializationError("missing-choice", path, "Text must be nonempty")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise MaterializationError("contract-pattern", path, "Text does not match the public pattern")
    elif kind in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            raise MaterializationError("contract-range", path, "Number is below the declared minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise MaterializationError("contract-range", path, "Number exceeds the declared maximum")


def leaf_paths(value: Any, path: str = "") -> set[str]:
    if type(value) is dict and value:
        return set().union(*(leaf_paths(v, path + "/" + pointer_token(k)) for k, v in value.items()))
    if type(value) is list and value:
        return set().union(*(leaf_paths(v, f"{path}/{i}") for i, v in enumerate(value)))
    return {path}


def get_pointer(value: Any, path: str) -> Any:
    if not path:
        return value
    if type(path) is not str or not path.startswith("/"):
        raise MaterializationError("invalid-pointer", str(path), "Expected an absolute JSON pointer")
    try:
        for token in path[1:].split("/"):
            if re.search(r"~(?![01])", token):
                raise ValueError("Invalid JSON pointer escape")
            key = token.replace("~1", "/").replace("~0", "~")
            if type(value) is list:
                if re.fullmatch(r"0|[1-9][0-9]*", key) is None:
                    raise ValueError("Noncanonical array index")
                value = value[int(key)]
            elif type(value) is dict:
                value = value[key]
            else:
                raise TypeError("Cannot traverse a scalar")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MaterializationError("unknown-reference", path, "Reference does not resolve canonically") from exc
    return value
