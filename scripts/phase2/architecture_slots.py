"""Neutral renderer slots: explicit author data or a visible undecided marker."""
from __future__ import annotations
from copy import deepcopy
from collections.abc import Mapping

UNDECIDED = "undecided: author decision required"

def author_slots(context, stage):
    value = context.get("architecture_slots", {}).get(stage, {})
    if not isinstance(value, Mapping):
        raise ValueError("architecture slots must be an object")
    return value

def author_value(context, stage, key):
    value = author_slots(context, stage).get(key)
    return str(value) if value is not None and str(value).strip() else UNDECIDED

def author_rows(context, stage, key):
    value = author_slots(context, stage).get(key, [])
    if not isinstance(value, list):
        raise ValueError("author row slot must be an array: " + key)
    return deepcopy(value)

def author_block(context, stage, key):
    return "  - " + author_value(context, stage, key)
