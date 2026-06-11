from __future__ import annotations

import re


TRIAL_TOKEN_PATTERN = re.compile(r"\btrial-v[0-9][a-z0-9._-]*\b", flags=re.IGNORECASE)
SIMPLE_VERSION_PATTERN = re.compile(r"\bv(\d+(?:\.\d+)*(?:-[a-z0-9._-]+)?)\b", flags=re.IGNORECASE)
R_STYLE_VERSION_PATTERN = re.compile(r"\br(\d+)\b", flags=re.IGNORECASE)
VERSION_FIELD_PATTERN = re.compile(
    r"^[ \t]*-[ \t]+(?:report_version|current_version|run_version|version|报告版本|当前版本|运行版本|版本(?:\s*\(version\))?):[ \t]*`?([^`\n]+)`?[ \t]*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def choose_best_identifiers(tokens: set[str]) -> set[str]:
    if not tokens:
        return set()
    filtered = {token for token in tokens if token != "trial-v0.1"} or set(tokens)
    if len(filtered) <= 1:
        return filtered
    best = max(filtered, key=lambda token: (".0-verified" in token, "verified" in token, len(token), token))
    return {best}


def normalize_version_identifier(raw: str) -> str:
    value = raw.strip().lower()
    if not value:
        return ""
    if value.startswith("trial-v"):
        return value
    match = re.fullmatch(r"v(\d+(?:\.\d+)*(?:-[a-z0-9._-]+)?)", value) or re.fullmatch(r"r(\d+)", value)
    if match:
        return f"trial-v{match.group(1)}"
    if value.isdigit():
        return f"trial-v{value}"
    return value


def extract_version_field_values(text: str) -> list[str]:
    return [match.group(1).strip() for match in VERSION_FIELD_PATTERN.finditer(text) if match.group(1).strip()]


def extract_version_identifiers(text: str) -> set[str]:
    version_values = extract_version_field_values(text)
    canonical_from_fields = set()
    for value in version_values:
        lowered = value.strip().lower()
        if lowered.startswith("trial-v"):
            canonical_from_fields.add(lowered)
        canonical_from_fields.update(
            f"trial-v{match.group(1).lower()}"
            for match in SIMPLE_VERSION_PATTERN.finditer(value)
        )
        canonical_from_fields.update(
            f"trial-v{match.group(1)}"
            for match in R_STYLE_VERSION_PATTERN.finditer(value)
        )
        if lowered.isdigit():
            canonical_from_fields.add(f"trial-v{lowered}")
    if canonical_from_fields:
        return choose_best_identifiers(canonical_from_fields)

    normalized_fields = {normalize_version_identifier(value) for value in version_values}
    normalized_fields.discard("")
    if normalized_fields:
        return choose_best_identifiers(normalized_fields)

    tokens = {token.lower() for token in TRIAL_TOKEN_PATTERN.findall(text)}
    if tokens:
        return choose_best_identifiers(tokens)

    fallback_trialized = {
        f"trial-v{match.group(1).lower()}"
        for match in SIMPLE_VERSION_PATTERN.finditer(text)
    }
    return choose_best_identifiers(fallback_trialized)
