"""Portable, immutable raw input annex for P1/P2. No decisions or acceptance authority.

Index identity excludes execution roots, run IDs and timestamps. The existing
native snapshot/receipt binds this annex; it is not a second truth store.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from common.agentic_decision_authority import canonical_digest

INDEX_VERSION = "wff.portable-phase-inputs.v2"
SNAPSHOT_VERSION = "wff.agentic-decision-input-snapshot.v2"
ORIGIN_VERSION = "wff.input-origin-declaration.v1"
ORIGIN_STATES = {"user-stated", "agent-proposed", "unverified"}
LOGICAL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")


def raw_digest(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


def _regular(path: Path) -> bytes:
    # Check the unresolved path too: resolve() alone erases symlink evidence.
    if not path.is_absolute():
        path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError("Portable input may not traverse symlinks")
    if not path.is_file():
        raise ValueError("Portable input is missing or not a regular file")
    with path.open("rb") as stream:
        import os
        before = os.fstat(stream.fileno())
        data = stream.read()
        after = os.fstat(stream.fileno())
    live = path.stat()
    identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if identity(before) != identity(after) or identity(after) != identity(live) or len(data) != after.st_size:
        raise ValueError("Portable input changed during read")
    return data


def line_locators(data: bytes) -> list[dict[str, int]]:
    """UTF-8 physical lines, including CRLF and a trailing empty line."""
    data.decode("utf-8")
    result = []
    offset = 0
    for number, line in enumerate(data.split(b"\n"), 1):
        result.append({"line": number, "byte_start": offset, "byte_end": offset + len(line)})
        offset += len(line) + 1
    return result


def fact_locators(phase: str, role: str, data: bytes) -> list[dict[str, int]]:
    rows = line_locators(data)
    if phase == "P1" and role == "phase-input":
        text = data.decode("utf-8")
        begin, end = source_fact_span(text)
        begin, end = len(text[:begin].encode()), len(text[:end].encode())
        return [row for row in rows if row["byte_start"] < end and row["byte_end"] >= begin]
    return rows


def _origin(record: Mapping[str, Any] | None, *, logical_id: str, role: str, digest: str) -> tuple[str, str]:
    if record is None:
        return "unverified", ""
    required = {"schema_version", "logical_id", "role", "document_sha256", "origin_state", "evidence_ref", "content_digest"}
    if (set(record) != required or record.get("schema_version") != ORIGIN_VERSION
            or record.get("logical_id") != logical_id or record.get("role") != role
            or record.get("document_sha256") != digest or record.get("origin_state") not in ORIGIN_STATES
            or not isinstance(record.get("evidence_ref"), str) or not record["evidence_ref"].strip()
            or record.get("content_digest") != canonical_digest({k: v for k, v in record.items() if k != "content_digest"})):
        raise ValueError("Input origin declaration is invalid or refers to different bytes")
    # These are caller-admitted origin declarations, not external approval.
    return str(record["origin_state"]), str(record["content_digest"])


def _row(phase: str, logical_id: str, role: str, data: bytes, origin: Mapping[str, Any] | None) -> dict:
    if not LOGICAL_ID.fullmatch(logical_id) or not role or role.strip() != role:
        raise ValueError("Input logical identity/role is invalid")
    digest = raw_digest(data)
    state, receipt = _origin(origin, logical_id=logical_id, role=role, digest=digest)
    return {"logical_id": logical_id, "role": role, "sha256": digest,
            "fact_surface_locator_digest": canonical_digest(fact_locators(phase, role, data)),
            "origin_state": state, "origin_receipt_digest": receipt}


def index_name(phase: str) -> str:
    if phase not in {"P1", "P2"}:
        raise ValueError("Portable inputs support P1/P2 only")
    return phase.lower() + "-input-index.json"


def annex_path(root: Path, phase: str) -> Path:
    return root / "input-annex" / phase


def read_annex(root: Path, *, phase: str, expected_digest: str | None = None) -> dict:
    files = {p.relative_to(root).as_posix(): _regular(p)
             for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    result = read_annex_bytes(files, phase=phase, expected_digest=expected_digest)
    result["files"] = [root / rel for rel in sorted(files)]
    return result


def read_annex_bytes(files: Mapping[str, bytes], *, phase: str, expected_digest: str | None = None) -> dict:
    """Same validation for published files and a P1 annex retained inside P2 inputs."""
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate portable index key")
            result[key] = value
        return result
    if index_name(phase) not in files:
        raise ValueError("Portable input index is missing")
    value = json.loads(files[index_name(phase)], object_pairs_hook=unique_pairs)
    if (set(value) != {"schema_version", "phase_id", "inputs", "origin_declarations", "content_digest"}
            or value["schema_version"] != INDEX_VERSION or value["phase_id"] != phase
            or value["content_digest"] != canonical_digest({k: v for k, v in value.items() if k != "content_digest"})
            or (expected_digest is not None and value["content_digest"] != expected_digest)):
        raise ValueError("Portable input index is invalid or belongs to a different snapshot")
    rows, origins = value["inputs"], value["origin_declarations"]
    if not isinstance(rows, list) or not rows or not isinstance(origins, dict):
        raise ValueError("Portable input denominator is missing")
    ids = [row.get("logical_id") for row in rows]
    if any(not isinstance(i, str) for i in ids) or ids != sorted(set(ids)) or set(origins) - set(ids):
        raise ValueError("Portable input logical identities are incomplete/duplicated")
    documents = []
    required_files = {index_name(phase)}
    for row in rows:
        digest = row.get("sha256", "")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise ValueError("Invalid portable raw-byte digest")
        relative = "blobs/" + digest[7:] + ".raw"
        if relative not in files:
            raise ValueError("Portable original input is missing")
        data = files[relative]
        if _row(phase, row["logical_id"], row["role"], data, origins.get(row["logical_id"])) != row:
            raise ValueError("Portable input bytes, locator surface or origin differs from the index")
        required_files.add(relative)
        documents.append({**deepcopy(row), "data": data, "locators": fact_locators(phase, row["role"], data)})
    if sum(row["role"] == "phase-input" for row in rows) != 1:
        raise ValueError("Portable input must have one primary document")
    if set(files) != required_files:
        raise ValueError("Portable input file denominator differs from the exact index")
    return {"index": value, "documents": documents}


def input_snapshot(annex: Mapping[str, Any]) -> dict:
    index = annex["index"]
    body = {"schema_version": SNAPSHOT_VERSION, "phase_id": index["phase_id"],
            "inputs": deepcopy(index["inputs"]), "context": {"input_annex_digest": index["content_digest"]}}
    body["snapshot_digest"] = canonical_digest(body)
    return body

# Exact packet locator grammar extracted from the same B revision; no P1 runtime import.
P1_SOURCE_INPUT_PACKET_PATTERN = re.compile(r"^#\s+P1 Source Input Packet\b", flags=re.IGNORECASE | re.MULTILINE)

P1_SOURCE_BRIEF_HEADING_PATTERN = re.compile(
    r"^##\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*P1 Source Brief[^\n]*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

P1_PACKET_LEVEL_SECTION_TITLES = (
    "Intake Metadata",
    "Raw User Intent",
    "Source Materials",
    "Project Context Candidates",
    "Product Truth Challenge Notes",
    "Challenge Axis Coverage",
    "Truth-State Ledger",
    "Open Truth Gaps",
    "Reviewer Concerns",
    "Admission Decision",
    "Recommended P1 Profile / Depth Notes",
    "Handoff Note For wff-req",
)

def _normalized_heading_title(raw_heading: str) -> str:
    title = re.sub(r"^#+\s+", "", str(raw_heading or "")).strip()
    title = re.sub(r"^\d+(?:\.\d+)?\s+", "", title).strip()
    title = re.sub(r"\s+", " ", title).strip(" `")
    return title

def _is_packet_fact_surface_terminator(raw_heading: str) -> bool:
    title = _normalized_heading_title(raw_heading).casefold()
    return any(title == keyword.casefold() or title.startswith(f"{keyword.casefold()}:") for keyword in P1_PACKET_LEVEL_SECTION_TITLES)

def source_fact_span(source_text: str, *, packet_only: bool = False) -> tuple[int, int]:
    """Exact character interval, before display normalization; never locate by text search."""
    if not packet_only and not P1_SOURCE_INPUT_PACKET_PATTERN.search(source_text):
        return 0, len(source_text)
    match = P1_SOURCE_BRIEF_HEADING_PATTERN.search(source_text)
    if not match:
        return 0, 0
    start = match.start()
    end = len(source_text)
    tail = source_text[start:]
    for heading in re.finditer(r"^##\s+[^\n]+$", tail[match.end() - start :], flags=re.MULTILINE):
        raw_heading = heading.group(0)
        if _is_packet_fact_surface_terminator(raw_heading):
            end = match.end() + heading.start()
            break
    # Preserve legacy strip semantics while retaining the positions which caused it.
    while start < end and source_text[start].isspace():
        start += 1
    while end > start and source_text[end - 1].isspace():
        end -= 1
    return start, end
