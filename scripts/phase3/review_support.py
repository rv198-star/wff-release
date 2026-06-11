from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.surface_policy import write_phase3_profiled_surface


FINDING_SEVERITIES = ("critical", "high", "medium", "low")


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def load_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def write_text_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_json_report(path: Path, payload: dict[str, Any]) -> Path:
    return write_text_file(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_profiled_markdown_report(output_dir: Path, surface_name: str, content: str) -> Path:
    return write_phase3_profiled_surface(output_dir, surface_name, content)


def write_json_and_markdown_report(
    *,
    json_path: Path,
    report: dict[str, Any],
    markdown: str,
    markdown_path: Path | None = None,
) -> dict[str, str]:
    resolved_markdown_path = markdown_path or json_path.with_suffix(".md")
    written_json_path = write_json_report(json_path, report)
    written_markdown_path = write_text_file(resolved_markdown_path, markdown)
    return {
        "json_path": str(written_json_path),
        "markdown_path": str(written_markdown_path),
    }


def emit_review_artifacts(
    *,
    output_dir: Path,
    json_name: str,
    markdown_surface_name: str,
    report: dict[str, Any],
    markdown: str,
) -> dict[str, Any]:
    json_path = write_json_report(output_dir / json_name, report)
    markdown_path = write_profiled_markdown_report(output_dir, markdown_surface_name, markdown)
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        **summary,
    }


def emit_evidence_artifacts(
    *,
    output_dir: Path,
    json_name: str,
    markdown_name: str,
    report: dict[str, Any],
    markdown: str,
    profiled_markdown: bool = False,
    summary_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    json_path = write_json_report(output_dir / json_name, report)
    if profiled_markdown:
        markdown_path = write_profiled_markdown_report(output_dir, markdown_name, markdown)
    else:
        markdown_path = write_text_file(output_dir / markdown_name, markdown)
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        **(summary_fields or {}),
    }


def finding_severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        f"{severity}_findings": sum(1 for row in findings if str(row.get("severity") or "") == severity)
        for severity in FINDING_SEVERITIES
    }


def render_findings_markdown(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "- none"
    lines: list[str] = []
    for finding in findings:
        severity = str(finding.get("severity") or "unknown")
        title = str(finding.get("title") or "untitled finding")
        evidence = str(finding.get("evidence") or "no evidence")
        lines.append(f"- [{severity}] {title} ({evidence})")
    return "\n".join(lines)


def render_review_report_markdown(
    *,
    title: str,
    summary_lines: list[str],
    check_lines: list[str] | None = None,
    findings: list[dict[str, Any]] | None = None,
) -> str:
    lines = [
        f"# {title}",
        "",
        "## Summary",
        *summary_lines,
    ]
    if check_lines:
        lines.extend(["", "## Checks", *check_lines])
    lines.extend(["", "## Findings", render_findings_markdown(findings or []), ""])
    return "\n".join(lines)


def review_summary_has_no_high_severity_findings(summary: dict[str, Any]) -> bool:
    return int(summary.get("critical_findings", 0) or 0) == 0 and int(summary.get("high_findings", 0) or 0) == 0


def support_gate_passed(mode: str, payload: dict[str, Any]) -> bool:
    if mode in {"code-review", "security-audit"}:
        return review_summary_has_no_high_severity_findings(payload)
    if mode == "coverage-collection":
        return payload.get("overall_quality_gate") == "pass" or bool(payload.get("collected"))
    if mode == "verdict":
        return payload.get("verdict") == "pass"
    return True


def support_gate_exit_code(mode: str, payload: dict[str, Any]) -> int:
    return 0 if support_gate_passed(mode, payload) else 1


def emit_gate_cli_result(
    payload: dict[str, Any],
    *,
    output_path: Path | None = None,
    success_key: str = "overall_quality_gate",
) -> int:
    if output_path is not None:
        write_json_report(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get(success_key) == "pass" else 1
