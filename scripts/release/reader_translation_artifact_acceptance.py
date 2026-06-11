#!/usr/bin/env python3
"""Validate generated reader translation artifacts without invoking an LLM."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.reader_artifact_integrity import check_integrity, check_structure


PHASE_DIR_ALIASES = {
    "phase-1": "phase1",
    "phase-2": "phase2",
    "phase-3": "phase3",
    "phase-4": "phase4",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_manifest_path(case_root: Path, manifest_path: str, *, kind: str = "") -> Path:
    path = Path(manifest_path)

    case_name = case_root.name
    parts = list(path.parts)
    if case_name in parts:
        case_index = len(parts) - 1 - list(reversed(parts)).index(case_name)
        tail = [PHASE_DIR_ALIASES.get(part, part) for part in parts[case_index + 1 :]]
        candidate = case_root.joinpath(*tail)
        if candidate.exists():
            return candidate

    if path.exists():
        return path

    basename = path.name
    search_roots = []
    if kind == "p1-prd":
        search_roots.append(case_root / "phase1")
    elif kind == "p2-esp":
        search_roots.append(case_root / "phase2")
    elif kind == "p3-action-card":
        search_roots.append(case_root / "phase3" / "action-cards")
    search_roots.append(case_root)

    for search_root in search_roots:
        if not search_root.exists():
            continue
        matches = sorted(candidate for candidate in search_root.rglob(basename) if candidate.is_file())
        if matches:
            return matches[0]
    return case_root / "__missing__" / basename


def _reader_has_preamble(reader_text: str, canonical_name: str, locale: str) -> bool:
    if locale == "zh-CN":
        marker_ok = "本地化阅读版" in reader_text and "localized reader artifact" in reader_text
    else:
        marker_ok = "Localized reader artifact" in reader_text
    return marker_ok and f"canonical_of: `{canonical_name}`" in reader_text


def _validate_target(case_root: Path, entry: dict[str, Any], locale: str) -> dict[str, Any]:
    kind = str(entry.get("kind", ""))
    canonical = _resolve_manifest_path(case_root, str(entry.get("canonical", "")), kind=kind)
    reader = _resolve_manifest_path(case_root, str(entry.get("reader", "")), kind=kind)
    integrity_json = _resolve_manifest_path(case_root, str(entry.get("integrity_json", "")), kind=kind)

    issues: list[str] = []
    if entry.get("status") != "generated":
        issues.append("manifest target status is not generated")
    if entry.get("verdict") != "pass":
        issues.append("manifest target verdict is not pass")
    if not canonical.exists():
        issues.append("canonical file missing")
    if not reader.exists():
        issues.append("reader file missing")
    if not integrity_json.exists():
        issues.append("integrity json missing")

    integrity_verdict = ""
    structure_issues: list[str] = []
    stored_integrity_verdict = ""
    preamble_ok = False
    if canonical.exists() and reader.exists():
        canonical_text = canonical.read_text(encoding="utf-8")
        reader_text = reader.read_text(encoding="utf-8")
        recomputed_integrity = check_integrity(
            canonical_path=canonical,
            reader_path=reader,
            locale=locale,
            canonical_text=canonical_text,
            reader_text=reader_text,
        )
        integrity_verdict = recomputed_integrity.verdict
        if recomputed_integrity.verdict != "pass":
            issues.append(f"recomputed integrity is {recomputed_integrity.verdict}")
        structure = check_structure(canonical_text=canonical_text, reader_text=reader_text)
        structure_issues = structure.issues
        if structure.issues:
            issues.extend(f"structure issue: {issue}" for issue in structure.issues)
        preamble_ok = _reader_has_preamble(reader_text, canonical.name, locale)
        if not preamble_ok:
            issues.append("reader preamble missing or canonical_of mismatch")

    if integrity_json.exists():
        try:
            stored_integrity = _load_json(integrity_json)
            stored_integrity_verdict = str(stored_integrity.get("verdict", ""))
            if stored_integrity_verdict != "pass":
                issues.append(f"stored integrity is {stored_integrity_verdict or 'missing'}")
        except json.JSONDecodeError:
            issues.append("integrity json is invalid")

    return {
        "kind": kind,
        "canonical": str(canonical),
        "reader": str(reader),
        "integrity_json": str(integrity_json),
        "manifest_status": str(entry.get("status", "")),
        "manifest_verdict": str(entry.get("verdict", "")),
        "stored_integrity_verdict": stored_integrity_verdict,
        "recomputed_integrity_verdict": integrity_verdict,
        "structure_issues": structure_issues,
        "preamble_ok": preamble_ok,
        "acceptance_verdict": "pass" if not issues else "fail",
        "issues": issues,
    }


def build_reader_translation_artifact_acceptance(case_root: Path) -> dict[str, Any]:
    case_root = case_root.resolve()
    manifest_path = case_root / "reader-translation-manifest.json"
    if not manifest_path.exists():
        return {
            "generated_at": utc_now_iso(),
            "case_root": str(case_root),
            "manifest_path": str(manifest_path),
            "target_locale": "",
            "verdict": "fail",
            "summary": {
                "total_targets": 0,
                "accepted_count": 0,
                "issue_count": 1,
                "generated_count": 0,
                "failed_count": 0,
            },
            "issues": ["reader-translation-manifest.json missing"],
            "targets": [],
        }

    manifest = _load_json(manifest_path)
    locale = str(manifest.get("target_locale", "zh-CN"))
    entries = list(manifest.get("targets", []))
    target_reports = [_validate_target(case_root, entry, locale) for entry in entries]
    summary = dict(manifest.get("summary", {}))
    total_targets = int(summary.get("total_targets", len(entries)))
    generated_count = int(summary.get("generated_count", 0))
    failed_count = int(summary.get("failed_count", 0))

    issues: list[str] = []
    if manifest.get("reader_evidence_state") != "generated":
        issues.append("reader_evidence_state is not generated")
    if total_targets != len(entries):
        issues.append("summary total_targets does not match targets length")
    if generated_count != total_targets:
        issues.append("summary generated_count does not match total_targets")
    if failed_count != 0:
        issues.append("summary failed_count is not zero")

    target_issue_count = sum(len(target["issues"]) for target in target_reports)
    accepted_count = sum(1 for target in target_reports if target["acceptance_verdict"] == "pass")
    issue_count = len(issues) + target_issue_count

    return {
        "generated_at": utc_now_iso(),
        "case_root": str(case_root),
        "manifest_path": str(manifest_path),
        "target_locale": locale,
        "verdict": "pass" if issue_count == 0 and accepted_count == total_targets else "fail",
        "summary": {
            "total_targets": total_targets,
            "accepted_count": accepted_count,
            "issue_count": issue_count,
            "generated_count": generated_count,
            "failed_count": failed_count,
        },
        "issues": issues,
        "targets": target_reports,
    }


def render_acceptance_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Reader Translation Artifact Acceptance",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- case_root: `{report['case_root']}`",
        f"- manifest_path: `{report['manifest_path']}`",
        f"- target_locale: `{report['target_locale']}`",
        f"- verdict: `{report['verdict']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    if report["issues"]:
        lines.extend(["", "## Manifest Issues", ""])
        for issue in report["issues"]:
            lines.append(f"- {issue}")
    lines.extend(
        [
            "",
            "## Targets",
            "",
            "| Kind | Acceptance | Manifest | Stored Integrity | Recomputed Integrity | Preamble | Issues | Reader |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for target in report["targets"]:
        issues = "<br>".join(target["issues"]) if target["issues"] else "-"
        manifest_state = f"{target['manifest_status']} / {target['manifest_verdict']}"
        lines.append(
            "| "
            f"`{target['kind']}` | `{target['acceptance_verdict']}` | `{manifest_state}` | "
            f"`{target['stored_integrity_verdict']}` | `{target['recomputed_integrity_verdict']}` | "
            f"`{target['preamble_ok']}` | {issues} | `{target['reader']}` |"
        )
    return "\n".join(lines).rstrip() + "\n"


def write_acceptance_outputs(
    report: dict[str, Any],
    *,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> None:
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_acceptance_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate generated reader translation artifacts.")
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_reader_translation_artifact_acceptance(args.case_root)
    write_acceptance_outputs(report, output_json=args.output_json, output_md=args.output_md)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_acceptance_markdown(report))
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
