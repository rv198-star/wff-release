#!/usr/bin/env python3
"""Source-admission checks for cross-phase handoff inputs.

The check is intentionally mechanical and conservative. It catches empty or
placeholder-only handoff inputs before a downstream phase treats clean shape as
source truth. It does not decide whether a substantive source is semantically
correct.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERN = re.compile(
    r"(?i)(?:\bTBD\b|\bTODO\b|\bplaceholder\b|\bscaffold\b|\bfixture\b|\bexample-only\b|"
    r"\bsource-defined workflow\b|\bauthored stage output\b|source[_ -]?signals\s*:\s*`?\(?none\)?`?|"
    r"^\s*(?:\{\}|\[\])\s*$|^\s*[-*]?\s*`?\(?none\)?`?\s*$)"
)


def _is_markdown_structure_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if re.fullmatch(r"[:|\-\s]+", stripped):
        return True
    return False


def _substantive_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if not _is_markdown_structure_line(line)]


def _placeholder_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if PLACEHOLDER_PATTERN.search(line)]


def _status_and_findings(text: str) -> tuple[str, list[dict[str, Any]], list[str]]:
    lines = _substantive_lines(text)
    if not str(text or "").strip():
        return (
            "blocked",
            [
                {
                    "classification": "empty_source_input",
                    "severity": "blocking",
                    "reason": "handoff source input is empty or whitespace-only",
                }
            ],
            lines,
        )
    if not lines:
        return (
            "blocked",
            [
                {
                    "classification": "thin_source_input",
                    "severity": "blocking",
                    "reason": "handoff source input contains no substantive non-heading lines",
                }
            ],
            lines,
        )
    placeholders = _placeholder_lines(lines)
    if placeholders and len(placeholders) == len(lines):
        return (
            "blocked",
            [
                {
                    "classification": "thin_source_input",
                    "severity": "blocking",
                    "reason": "handoff source input is placeholder-only",
                    "placeholder_line_count": len(placeholders),
                }
            ],
            lines,
        )
    return "pass", [], lines


def _claim_ceiling(status: str) -> str:
    if status == "blocked":
        return "blocked:source-admission"
    if status == "review_bound":
        return "review-bound:source-admission"
    return "claim-clean:source-admission"


def build_source_admission_report(
    text: str,
    *,
    source_label: str,
    boundary: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    status, findings, lines = _status_and_findings(text)
    classifications = sorted(
        {str(finding.get("classification")) for finding in findings if finding.get("classification")}
    )
    report = {
        "artifact_kind": "cross-phase-source-admission-report.v1",
        "boundary": boundary,
        "source_label": source_label,
        "overall_status": status,
        "claim_ceiling": _claim_ceiling(status),
        "classifications": classifications,
        "findings": findings,
        "substantive_line_count": len(lines),
        "policy": (
            "This report blocks empty or placeholder-only handoff input before downstream phase work. "
            "It does not prove full semantic correctness."
        ),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _source_path_report(path: Path) -> dict[str, Any]:
    resolved = str(path.resolve())
    if not path.exists() or not path.is_file():
        return {
            "path": resolved,
            "exists": False,
            "overall_status": "blocked",
            "substantive_line_count": 0,
            "text": "",
            "findings": [
                {
                    "classification": "missing_source_input",
                    "severity": "blocking",
                    "path": resolved,
                    "reason": "required handoff source file is missing or not a file",
                }
            ],
        }
    text = path.read_text(encoding="utf-8")
    status, findings, lines = _status_and_findings(text)
    path_findings = []
    for finding in findings:
        enriched = dict(finding)
        enriched["path"] = resolved
        path_findings.append(enriched)
    return {
        "path": resolved,
        "exists": True,
        "overall_status": status,
        "substantive_line_count": len(lines),
        "text": text,
        "findings": path_findings,
    }


def build_source_admission_report_for_paths(
    required_paths: list[Path],
    *,
    boundary: str,
    source_label: str,
    output_path: Path | None = None,
    alternative_path_groups: list[list[Path]] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    path_reports: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    missing_paths: list[str] = []
    substantive_line_count = 0

    def record_required(report: dict[str, Any]) -> None:
        nonlocal substantive_line_count
        public_report = {key: value for key, value in report.items() if key != "text"}
        path_reports.append(public_report)
        if report["exists"]:
            scanned_paths.append(str(report["path"]))
            substantive_line_count += int(report["substantive_line_count"])
        if not report["exists"]:
            missing_paths.append(str(report["path"]))
        findings.extend(report["findings"])

    for path in required_paths:
        record_required(_source_path_report(path))

    alternative_reports: list[dict[str, Any]] = []
    for group_index, group in enumerate(alternative_path_groups or [], start=1):
        candidate_reports = [_source_path_report(path) for path in group]
        passing = [report for report in candidate_reports if report["overall_status"] == "pass"]
        for report in candidate_reports:
            if report["exists"]:
                scanned_paths.append(str(report["path"]))
                substantive_line_count += int(report["substantive_line_count"])
        if not passing:
            for report in candidate_reports:
                if not report["exists"]:
                    missing_paths.append(str(report["path"]))
                findings.extend(report["findings"])
        alternative_reports.append(
            {
                "group_index": group_index,
                "overall_status": "pass" if passing else "blocked",
                "candidate_paths": [
                    {key: value for key, value in report.items() if key != "text"} for report in candidate_reports
                ],
            }
        )

    classifications = sorted(
        {str(finding.get("classification")) for finding in findings if finding.get("classification")}
    )
    status = "blocked" if any(str(finding.get("severity")) == "blocking" for finding in findings) else "pass"
    report = {
        "artifact_kind": "cross-phase-source-admission-report.v1",
        "boundary": boundary,
        "source_label": source_label,
        "overall_status": status,
        "claim_ceiling": _claim_ceiling(status),
        "classifications": classifications,
        "findings": findings,
        "substantive_line_count": substantive_line_count,
        "scanned_paths": scanned_paths,
        "missing_paths": missing_paths,
        "path_reports": path_reports,
        "alternative_path_groups": alternative_reports,
        "policy": (
            "This report blocks missing, empty, or placeholder-only required handoff source files before "
            "downstream phase work. It does not prove full semantic correctness."
        ),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_source_admission_report_for_path(
    path: Path,
    *,
    boundary: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return build_source_admission_report(
        text,
        source_label=str(path),
        boundary=boundary,
        output_path=output_path,
    )
