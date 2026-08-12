#!/usr/bin/env python3
"""Aggregate Human Review decision-quality evidence for one lifecycle case."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.human_review_terminology import (  # noqa: E402
    localize_review_terms,
    review_status_label,
)
from common.human_review_decision_quality import (  # noqa: E402
    audit_projection,
    audit_summary,
    source_anchor_terms,
)
from common.human_semantic_projection import (  # noqa: E402
    PROJECTION_KINDS,
    projection_source_refs,
)


REPORT_SCHEMA = "wff.human-review-decision-quality-case-audit.v1"
DEFAULT_JSON = Path("human-review") / "decision-quality-audit.json"
DEFAULT_MARKDOWN = Path("human-review") / "decision-quality-audit.md"


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _projection_path(case_root: Path, kind: str) -> Path:
    return case_root / "human-review" / "projections" / f"{kind}.json"


def _load_projection(path: Path, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{kind} projection is unreadable: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("projection_kind") != kind:
        raise ValueError(f"{kind} projection identity is invalid")
    return payload


def _entry(case_root: Path, kind: str) -> dict[str, Any]:
    path = _projection_path(case_root, kind)
    if not path.is_file() or path.is_symlink():
        return {
            "kind": kind,
            "status": "missing",
            "verdict": "fail",
            "score": 0.0,
            "detail": "projection file is missing",
        }
    payload = _load_projection(path, kind)
    refs = projection_source_refs(case_root, kind)
    report = audit_projection(
        kind=kind,
        payload=payload,
        source_anchors=source_anchor_terms(case_root, refs),
    )
    shallow = [
        {
            "title": section["title"],
            "verdict": section["verdict"],
            "score": section["score"],
            "finding_codes": [item["code"] for item in section["findings"]],
        }
        for section in report["sections"]
        if section["verdict"] != "pass"
    ]
    return {
        "kind": kind,
        "status": "audited",
        "path": path.relative_to(case_root).as_posix(),
        "verdict": report["verdict"],
        "score": report["score"],
        "summary": audit_summary(report),
        "shallow_sections": shallow,
        "report_path": str(
            payload.get("decision_quality", {}).get("path") or ""
        ),
    }


def _overall(entries: list[dict[str, Any]]) -> str:
    verdicts = [str(item.get("verdict") or "fail") for item in entries]
    if not verdicts or "fail" in verdicts:
        return "fail"
    if "review-bound" in verdicts:
        return "review-bound"
    return "pass"


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Human Review Decision Quality Audit",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- case_root: `{report['case_root']}`",
        f"- verdict: `{review_status_label(report['verdict'])}`",
        "",
        "## Projection Summary",
        "",
        "| Projection | Verdict | Score | Shallow sections |",
        "|---|---:|---:|---:|",
    ]
    for entry in report["entries"]:
        lines.append(
            f"| `{entry['kind']}` | `{review_status_label(entry['verdict'])}` | "
            f"{float(entry.get('score') or 0.0):.2f} | "
            f"{len(entry.get('shallow_sections', []))} |"
        )
    for entry in report["entries"]:
        shallow = entry.get("shallow_sections", [])
        if not shallow:
            continue
        lines.extend(["", f"## {entry['kind']} Review Gaps", ""])
        for section in shallow:
            codes = ", ".join(section.get("finding_codes", [])) or "none"
            lines.append(
                f"- **{localize_review_terms(section['title'])}** — "
                f"`{review_status_label(section['verdict'])}` / "
                f"{section['score']}: {codes}"
            )
    lines.append("")
    return "\n".join(lines)


def audit_case(
    case_root: Path,
    *,
    kinds: list[str] | tuple[str, ...] | None = None,
    json_path: Path | None = None,
    markdown_path: Path | None = None,
) -> dict[str, Any]:
    root = case_root.resolve()
    selected = list(kinds or PROJECTION_KINDS)
    unknown = sorted(set(selected) - set(PROJECTION_KINDS))
    if unknown:
        raise ValueError("unsupported decision-quality projection kinds: " + ", ".join(unknown))
    entries = [_entry(root, kind) for kind in selected]
    report = {
        "schema_version": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "case_root": str(root),
        "verdict": _overall(entries),
        "entries": entries,
    }
    target_json = (json_path or root / DEFAULT_JSON).resolve()
    target_markdown = (markdown_path or root / DEFAULT_MARKDOWN).resolve()
    for target in (target_json, target_markdown):
        if not target.is_relative_to(root):
            raise ValueError("decision-quality audit outputs must remain inside the case root")
    _atomic_text(
        target_json,
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _atomic_text(target_markdown, _markdown(report))
    return {
        **report,
        "json_path": str(target_json),
        "markdown_path": str(target_markdown),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--kind", action="append", choices=PROJECTION_KINDS)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = audit_case(args.case_root, kinds=args.kind)
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "detail": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "audited", **report}, ensure_ascii=False))
    if args.strict and report["verdict"] != "pass":
        return 1
    return 1 if report["verdict"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
