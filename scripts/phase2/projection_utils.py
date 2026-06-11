from __future__ import annotations

import re

from phase2.technical_naming import choose_technical_snake


def to_snake(raw: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    value = value.replace("&", " and ")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if value:
        return value.lower()
    return choose_technical_snake(raw, prefix="entity")


def unique_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result
