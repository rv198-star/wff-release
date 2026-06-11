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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def infer_source_fingerprint(text: str, *, source_label: str = "") -> dict[str, Any]:
    haystack = _normalize(f"{source_label}\n{text}")
    domain_scores: dict[str, int] = {}
    for domain, hints in DOMAIN_HINTS.items():
        score = sum(1 for hint in hints if _normalize(hint) in haystack)
        if score:
            domain_scores[domain] = score
    domain = "unknown"
    if domain_scores:
        domain = sorted(domain_scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "domain": domain,
        "domain_scores": domain_scores,
        "source_label": source_label,
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
