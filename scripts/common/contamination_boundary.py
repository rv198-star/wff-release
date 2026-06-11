#!/usr/bin/env python3
"""Lightweight cross-phase contamination boundary checks.

This module is intentionally narrow.  It detects known foreign/default-domain
residue at phase handoff boundaries and records evidence; it does not decide
general semantic correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResidueTerm:
    term: str
    classification: str
    source_domain: str
    severity: str


KNOWN_RESIDUE_TERMS: tuple[ResidueTerm, ...] = (
    ResidueTerm("AI visibility", "foreign_domain_residue", "geo", "blocking"),
    ResidueTerm("SEO manager", "foreign_domain_residue", "geo", "blocking"),
    ResidueTerm("action recommendation payload", "foreign_domain_residue", "geo", "blocking"),
    ResidueTerm("recommendation/action", "foreign_domain_residue", "geo", "blocking"),
    ResidueTerm("tracked scope", "foreign_domain_residue", "geo", "blocking"),
    ResidueTerm("CreateTrackedScope", "default_operation_residue", "geo", "blocking"),
)

DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "geo": ("geo", "generative engine optimization"),
    "invoice-adjustment": ("invoice adjustment", "billing", "invoice", "adjustment"),
    "order-query": ("order query", "order lookup", "order status", "buyer order"),
    "legacy-customer-id": ("legacy customer id", "customer identity", "partner callback"),
    "oracle-reporting": ("oracle reporting", "oracle database", "finance report", "reconciliation"),
    "petclinic": ("petclinic", "clinic", "veterinarian", "visit record"),
}

WEAK_DOMAIN_HINTS: dict[str, set[str]] = {
    "invoice-adjustment": {"adjustment"},
}

SOURCE_SPECIFIC_STOPWORDS = {
    "request_id",
    "trace_id",
    "error_code",
    "tenant_id",
    "phase_verdict",
    "review_bound",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").casefold()).strip("-")


def _is_negated_mention(haystack: str, start: int) -> bool:
    prefix = haystack[max(0, start - 24) : start]
    return bool(re.search(r"(?:\bnot\s+(?:an?\s+)?|不是|并非|非)\s*$", prefix))


def _hint_appears_positive(haystack: str, hint: str) -> bool:
    pattern = re.escape(_normalize(hint))
    for match in re.finditer(pattern, haystack):
        if not _is_negated_mention(haystack, match.start()):
            return True
    return False


def _source_specific_signals(text: str, *, source_label: str = "") -> list[str]:
    haystack = f"{source_label}\n{text}"
    signals: list[str] = []
    seen: set[str] = set()
    patterns = (
        r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b",
        r"\b[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*){2,}\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, haystack, flags=re.IGNORECASE):
            value = match.group(0).casefold()
            if value in SOURCE_SPECIFIC_STOPWORDS or value in seen:
                continue
            signals.append(value)
            seen.add(value)
    label_slug = re.sub(r"[^a-z0-9]+", "-", source_label.casefold()).strip("-")
    if label_slug and label_slug not in {"phase-1", "phase-2", "phase-3", "phase-4"}:
        for token in label_slug.split("-"):
            if len(token) >= 4 and token not in {"phase", "root", "tmp", "local", "artifacts"} and token not in seen:
                signals.append(token)
                seen.add(token)
    return signals[:20]


def _explicit_source_domains(text: str, *, source_label: str = "") -> set[str]:
    """Return source domains named by case/source metadata, not body prose.

    Source-specific identifiers are useful, but generated artifacts also carry
    generic metadata such as `case_name`, `stage_01`, and `updated_at`.  Those
    signals should not demote a retained case whose label explicitly names a
    configured domain.
    """

    label_slug = f"-{_slug(source_label)}-"
    explicit: set[str] = set()
    metadata_values: list[str] = []
    for match in re.finditer(
        r"^\s*[-*]?\s*(?:case[_ -]?name|source[_ -]?domain|canonical[_ -]?domain)\s*[:=]\s*`?([^`\n|]+?)`?\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        metadata_values.append(match.group(1))

    metadata_slugs = {f"-{_slug(value)}-" for value in metadata_values if _slug(value)}
    for domain, hints in DOMAIN_HINTS.items():
        domain_slug = _slug(domain)
        candidate_slugs = {domain_slug, *(_slug(hint) for hint in hints if _slug(hint))}
        if any(candidate and f"-{candidate}-" in label_slug for candidate in candidate_slugs):
            explicit.add(domain)
            continue
        if any(candidate and any(f"-{candidate}-" == metadata for metadata in metadata_slugs) for candidate in candidate_slugs):
            explicit.add(domain)
    return explicit


def infer_source_fingerprint(text: str, *, source_label: str = "") -> dict[str, Any]:
    haystack = _normalize(f"{source_label}\n{text}")
    domain_scores: dict[str, int] = {}
    for domain, hints in DOMAIN_HINTS.items():
        strong_score = 0
        weak_score = 0
        weak_hints = WEAK_DOMAIN_HINTS.get(domain, set())
        for hint in hints:
            if not _hint_appears_positive(haystack, hint):
                continue
            if hint in weak_hints:
                weak_score += 1
            else:
                strong_score += 1
        score = strong_score + (weak_score if strong_score > 0 else 0)
        if score:
            domain_scores[domain] = score
    domain = "unknown"
    if domain_scores:
        domain = sorted(domain_scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    signals = _source_specific_signals(text, source_label=source_label)
    explicit_domains = _explicit_source_domains(text, source_label=source_label)
    if signals and (not domain_scores or (max(domain_scores.values()) <= 1 and domain not in explicit_domains)):
        domain = "source-specific"
    return {
        "domain": domain,
        "domain_scores": domain_scores,
        "explicit_source_domains": sorted(explicit_domains),
        "source_label": source_label,
        "source_specific_signals": signals,
    }


def _line_number(text: str, term: str) -> int:
    pattern = _normalize(term)
    for index, line in enumerate(text.splitlines(), start=1):
        if pattern in _normalize(line):
            return index
    return 0


def _empty_source_signal_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for pattern in (r"source_signals:\s*`?\(none\)`?", r"-\s*`?\(none\)`?"):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            findings.append(
                {
                    "classification": "empty_source_signal",
                    "severity": "review_bound",
                    "term": "(none)",
                    "line": _line_number(text, "(none)"),
                    "reason": "source signal is empty or placeholder-like at a handoff boundary",
                }
            )
            break
    return findings


def scan_contamination(text: str, *, source_label: str = "") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fingerprint = infer_source_fingerprint(text, source_label=source_label)
    source_domain = str(fingerprint.get("domain") or "unknown")
    haystack = _normalize(text)
    findings: list[dict[str, Any]] = []
    for residue in KNOWN_RESIDUE_TERMS:
        if _normalize(residue.term) not in haystack:
            continue
        if source_domain == residue.source_domain:
            continue
        severity = residue.severity if source_domain != "unknown" else "review_bound"
        findings.append(
            {
                "classification": residue.classification,
                "severity": severity,
                "term": residue.term,
                "line": _line_number(text, residue.term),
                "source_domain": residue.source_domain,
                "detected_source_domain": source_domain,
                "reason": "known default-domain residue appears outside its matching source fingerprint",
            }
        )
    findings.extend(_empty_source_signal_findings(text))
    return fingerprint, findings


def _overall_status(findings: list[dict[str, Any]]) -> str:
    if any(str(finding.get("severity")) == "blocking" for finding in findings):
        return "blocked"
    if findings:
        return "review_bound"
    return "pass"


def _claim_ceiling(status: str) -> str:
    if status == "blocked":
        return "blocked:contamination-boundary"
    if status == "review_bound":
        return "review-bound:contamination-boundary"
    return "claim-clean:contamination-boundary"


def build_contamination_report(
    text: str,
    *,
    source_label: str,
    boundary: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    fingerprint, findings = scan_contamination(text, source_label=source_label)
    classifications = sorted({str(finding.get("classification")) for finding in findings if finding.get("classification")})
    status = _overall_status(findings)
    report = {
        "artifact_kind": "cross-phase-contamination-boundary-report.v1",
        "boundary": boundary,
        "source_label": source_label,
        "overall_status": status,
        "claim_ceiling": _claim_ceiling(status),
        "source_fingerprint": fingerprint,
        "classifications": classifications,
        "findings": findings,
        "policy": (
            "This report detects configured contamination residues at phase handoff boundaries. "
            "It does not prove full semantic correctness."
        ),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_contamination_report_for_path(
    path: Path,
    *,
    boundary: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return build_contamination_report(
        text,
        source_label=str(path),
        boundary=boundary,
        output_path=output_path,
    )
