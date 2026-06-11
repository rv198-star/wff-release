#!/usr/bin/env python3
"""
Deterministic Phase-3 delivery asset checks.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


def path_exists(path: Path | None) -> bool:
    return bool(path and path.exists())


def file_sha256(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dir_has_entries(path: Path | None) -> bool:
    return bool(path and path.exists() and path.is_dir() and any(path.iterdir()))


def file_contains_all(path: Path | None, required_tokens: tuple[str, ...]) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return all(token in document for token in required_tokens)


def dockerfile_has_runtime_entrypoint(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return "CMD [" in document or "ENTRYPOINT [" in document


def dockerfile_has_multistage_build(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    from_count = len([line for line in document.splitlines() if line.strip().lower().startswith("from ")])
    return from_count >= 2


def dockerfile_has_non_root_user(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    user_lines = [line.strip() for line in document.splitlines() if line.strip().lower().startswith("user ")]
    if not user_lines:
        return False
    effective_user = user_lines[-1].split(None, 1)[1].strip().strip("\"'")
    return effective_user.lower() not in {"root", "0"}


def dockerfile_has_healthcheck(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    return "HEALTHCHECK" in document.upper()


def is_placeholder_value(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    return normalized in {"", "replace-me", "changeme", "example", "placeholder"}


def contains_embedded_url_credentials(value: str) -> bool:
    return bool(re.search(r"[a-z][a-z0-9+.-]*://[^:\s\"'}]+:[^@\s\"'}]+@", value, re.IGNORECASE))


def extract_compose_default(value: str) -> str:
    match = re.search(r"\$\{[^}:]+:-([^}]*)\}", value)
    return match.group(1).strip() if match else ""


def _secret_line_has_inline_value(*, key: str, value: str) -> bool:
    normalized_key = key.strip().strip("\"'").upper()
    normalized_value = value.strip()
    url_keys = {"DATABASE_URL", "REDIS_URL", "AMQP_URL", "BROKER_URL"}
    secret_suffixes = ("PASSWORD", "SECRET", "TOKEN", "KEY")
    if any(normalized_key.endswith(suffix) for suffix in secret_suffixes):
        if normalized_value.startswith("${"):
            default_value = extract_compose_default(normalized_value)
            return bool(default_value and not is_placeholder_value(default_value))
        return not is_placeholder_value(normalized_value)
    if normalized_key in url_keys:
        if normalized_value.startswith("${"):
            default_value = extract_compose_default(normalized_value)
            return bool(default_value and contains_embedded_url_credentials(default_value))
        return contains_embedded_url_credentials(normalized_value)
    return False


def delivery_asset_has_hardcoded_secrets(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    for raw_line in document.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith(("ENV ", "ARG ")):
            _, _, remainder = line.partition(" ")
            key, sep, value = remainder.partition("=")
            if sep and _secret_line_has_inline_value(key=key, value=value):
                return True
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        if _secret_line_has_inline_value(key=key, value=value):
            return True
    return False


def compose_has_startable_runtime(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    document = path.read_text(encoding="utf-8")
    if "services:" not in document or "api:" not in document:
        return False
    if "healthcheck:" not in document:
        return False
    return any(token in document for token in ("command:", "entrypoint:", "image:", "build:"))
