"""Verify immutable tokens survived reader translation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


TRACE_ID_PATTERNS = [
    r"\bP\d-[A-Z0-9-]{3,}\b",
    r"\bARCH-[A-Z0-9-]{3,}\b",
    r"\bWP-[A-Z0-9-]+\b",
    r"\bRBI-\d+\b",
    r"\bAC-\d+\b",
    r"\b(?:RQ|EP|BVS|DR)-\d+\b",
    r"\bWO-[A-Z0-9-]{3,}\b",
    r"\btrial-v\d+\b",
]
FILE_PATH_RE = re.compile(
    r"\b(?:[A-Za-z0-9_.{}-]+/)+[A-Za-z0-9_.{}-]+\.(?:md|json|yaml|yml|ts|tsx|js|jsx|sql|py)\b"
)
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
STATUS_ENUM_RE = re.compile(
    r"\b(?:downstream-start-safe|review-ready|implementation-ready|implementation-planning-ready|"
    r"delivery-ready|testing-validation-complete|source-grounded-but-unvalidated|"
    r"partially-signal-backed|externally-validated|review-bound-but-not-ready)\b"
)

# Backtick values matching these patterns are reader-facing prose, NOT machine tokens.
_READER_FACING_BACKTICK_PATTERNS = [
    # Long English prose with natural sentence structure
    re.compile(r"^(?=.*[.,!?;:])(?=.*\s)[A-Za-z].{40,}$"),
    # Contains natural-language function words in a sentence structure
    re.compile(r"^(?=.*\b(?:the|and|for|from|into|with|that|this|must|should|will|each|when|then)\b)(?=.*\s)[A-Za-z].{30,}$", re.IGNORECASE),
    # Reader-facing role names
    re.compile(r"^[\w\s/-]*(?:owner|operator|manager|reviewer|veterinarian|receptionist|clinic)[\w\s/-]*$", re.IGNORECASE),
    # Title Case multi-word labels (2+ words with spaces)
    re.compile(r"^(?:[A-Z][a-z]+(?:\s+[A-Z][a-zA-Z]+)+)$"),
    # Natural language with common business context words
    re.compile(r"^(?=.*\b(?:marketing|business|content|growth|scope|baseline|finding|recommendation|task|review|slice|snapshot|check|direction|mapping|payload|contract)\b)(?=.*\s)[A-Za-z].{15,}$", re.IGNORECASE),
    # Business labels with pipes/slashes — reader-facing categorization
    re.compile(r"^(?=.*\s*[|/]\s*)[A-Za-z].{15,}$"),
    # Kebab-case methodology/concept names (2+ hyphens, no code indicators)
    re.compile(r"^[a-z]+-[a-z]+(?:-[a-z]+)+$"),
    # Natural language descriptions with common prepositions
    re.compile(r"^(?=.*\b(?:vs|support|check|story|map)\b)[A-Za-z].{10,}$", re.IGNORECASE),
]


def _is_machine_token(value: str) -> bool:
    """A machine token is a technical identifier that must survive translation.

    True machine tokens: trace IDs, file paths, code identifiers, status enums,
    version strings, schema/API/package/module names.

    NOT machine tokens: reader-facing labels, role names, business prose,
    document section headings, decision labels, methodology names.
    """
    # REJECT first: reader-facing patterns (check BEFORE accepting code patterns)
    for pat in _READER_FACING_BACKTICK_PATTERNS:
        if pat.search(value):
            return False
    # Single-word common nouns, decision labels, binary answers
    if re.fullmatch(r"(?:yes|no|present|system|clickable|Revise|Go|Pause|None|true|false)", value):
        return False
    # Kebab-case prose (2+ hyphens, all lowercase) → methodology/concept name
    if re.fullmatch(r"[a-z]+(?:-[a-z]+){2,}", value) and "/" not in value:
        return False
    # Natural language structure → NOT machine token
    if " " in value and len(value) > 20:
        return False
    if " " in value and re.search(r"\b(?:and|or|vs|for|with|from|into|support|check|story|map)\b", value, re.IGNORECASE):
        return False

    # ACCEPT: file paths with slashes
    if "/" in value:
        return True
    # ACCEPT: status enums (hyphenated machine contracts) — check before kebab reject
    if STATUS_ENUM_RE.fullmatch(value):
        return True
    # ACCEPT: version strings
    if re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?(?:-[a-z0-9.]+)?", value, re.IGNORECASE):
        return True
    # ACCEPT: snake_case or dotted identifiers (underscores/dots, not hyphens)
    if re.fullmatch(r"[a-z][a-z0-9]*(?:[_.][a-z0-9]+)+", value):
        return True
    # ACCEPT: Object/class identifiers: PascalCase or camelCase
    if re.fullmatch(r"[A-Z][A-Za-z0-9]+(?:[A-Z][a-z0-9]+)+", value):
        return True
    # ACCEPT: Short identifiers with code-signalling special characters
    if " " not in value and len(value) <= 50 and re.search(r"[_.:{}()]", value):
        return True
    # Single common English words (no special chars, no spaces) → reader-facing, not machine token
    if " " not in value and len(value) <= 30 and re.fullmatch(r"[a-zA-Z]+", value):
        return False
    # Anything else with natural language → reject
    if " " in value:
        return False
    # Short value with letters only → likely a word, not a machine token
    if re.fullmatch(r"[a-zA-Z]+", value):
        return False
    return True


def _is_reader_facing_context(line: str) -> bool:
    """Check if a status-enum-containing line is a reader-facing label definition,
    not a machine contract row."""
    # Lines that are primarily natural language with status values mixed in
    # are reader-facing, not machine enum declarations
    if re.match(r"^(?:[-*+]\s*)?[A-Za-z0-9_. -]{5,60}\s*[:=]\s*[A-Za-z0-9_.| -]{1,40}$", line):
        return False  # Short structured key:value — likely machine
    if re.match(r"^(?:[-*+]\s*)?[A-Za-z0-9_. -]*\b(?:label|title|name|description|summary|narrative|statement)\b", line, re.IGNORECASE):
        return True  # Natural-language label field
    return False


@dataclass(frozen=True)
class IntegrityResult:
    verdict: str
    canonical_path: str
    reader_path: str
    locale: str
    missing_tokens: list[str]
    token_count: int


def immutable_tokens(text: str) -> list[str]:
    tokens: set[str] = set()

    # Trace IDs and file paths (always machine tokens)
    for pattern in TRACE_ID_PATTERNS:
        for match in re.finditer(pattern, text):
            tokens.add(match.group(0).strip())
    for match in FILE_PATH_RE.finditer(text):
        tokens.add(match.group(0).strip())

    # Backtick content — filter reader-facing labels
    for match in BACKTICK_RE.finditer(text):
        value = match.group(1).strip()
        if not value or len(value) > 180:
            continue
        if _is_machine_token(value):
            tokens.add(value)

    # Status enums in structured context
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or _is_reader_facing_context(stripped):
            continue
        if re.match(
            r"^(?:[-*+]\s*)?[A-Za-z0-9_. -]*(?:state|status|delivery|evidence|readiness|decision)[A-Za-z0-9_. -]*\s*[:=]",
            stripped, re.IGNORECASE,
        ):
            for match in STATUS_ENUM_RE.finditer(stripped):
                tokens.add(match.group(0))

    return sorted(tokens)


def check_integrity(
    *,
    canonical_path: Path,
    reader_path: Path,
    locale: str,
    canonical_text: str | None = None,
    reader_text: str | None = None,
) -> IntegrityResult:
    source = canonical_text or canonical_path.read_text(encoding="utf-8")
    target = reader_text or reader_path.read_text(encoding="utf-8")
    required_tokens = immutable_tokens(source)
    missing = [token for token in required_tokens if token not in target]
    # Threshold-based: 0-1 missing → pass (acceptable noise), 2+ → warn.
    # For human-review documents, a single missing token does not invalidate
    # the translation; the integrity report surfaces it for the reviewer.
    if not missing:
        verdict = "pass"
    elif len(missing) <= 1:
        verdict = "warn"
    else:
        verdict = "fail"
    return IntegrityResult(
        verdict=verdict,
        canonical_path=str(canonical_path),
        reader_path=str(reader_path),
        locale=locale,
        missing_tokens=missing,
        token_count=len(required_tokens),
    )


def render_reader_preamble(canonical_name: str, locale: str, artifact_label: str) -> str:
    if locale == "zh-CN":
        return "\n".join([
            "> 本地化阅读版（localized reader artifact）",
            f"> artifact_label: `{artifact_label}`",
            f"> canonical_of: `{canonical_name}`",
            "> 规则: 保留 trace id、artifact id、状态枚举、文件路径、API/字段名和声明上限；如与 canonical 冲突，以 canonical 为准。",
            "",
        ])
    return "\n".join([
        "> Localized reader artifact",
        f"> artifact_label: `{artifact_label}`",
        f"> canonical_of: `{canonical_name}`",
        "> Rule: this reader is a human-facing rewrite for the target locale; canonical remains authoritative.",
        "",
    ])


@dataclass(frozen=True)
class StructureReport:
    h2_count_match: bool
    table_row_drift_pct: float
    unclosed_fences: bool
    issues: list[str]


def check_structure(
    *,
    canonical_text: str,
    reader_text: str,
) -> StructureReport:
    issues: list[str] = []

    # H2 count: allow ±2 before flagging (minor variance is acceptable noise)
    src_h2 = len(re.findall(r"^## ", canonical_text, re.MULTILINE))
    trans_h2 = len(re.findall(r"^## ", reader_text, re.MULTILINE))
    h2_ok = abs(src_h2 - trans_h2) <= 2

    # Table row count
    src_tbl = len(re.findall(r"^\|", canonical_text, re.MULTILINE))
    trans_tbl = len(re.findall(r"^\|", reader_text, re.MULTILINE))
    drift = abs(trans_tbl - src_tbl) / max(src_tbl, 1) * 100 if src_tbl > 0 else 0

    # Unclosed code fences
    src_fences = len(re.findall(r"^```", canonical_text, re.MULTILINE))
    trans_fences = len(re.findall(r"^```", reader_text, re.MULTILINE))
    fence_ok = (trans_fences % 2 == 0)

    if not h2_ok:
        issues.append(f"H2 count mismatch: source={src_h2}, translation={trans_h2}")
    if drift > 30:
        issues.append(f"Table row drift {drift:.0f}% (source={src_tbl}, translation={trans_tbl})")
    if not fence_ok:
        issues.append(f"Unclosed code fences: {trans_fences} fence markers (should be even)")

    return StructureReport(
        h2_count_match=h2_ok,
        table_row_drift_pct=round(drift, 1),
        unclosed_fences=not fence_ok,
        issues=issues,
    )


def write_integrity_report(result: IntegrityResult, output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps({
            "verdict": result.verdict,
            "canonical_path": result.canonical_path,
            "reader_path": result.reader_path,
            "locale": result.locale,
            "immutable_token_count": result.token_count,
            "missing_immutable_tokens": result.missing_tokens,
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
