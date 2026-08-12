#!/usr/bin/env python3
"""Audit whether Human Review projections support concrete expert decisions.

The audit is intentionally content-agnostic: it does not decide product or
architecture truth. It checks whether an Agentic projection exposes enough
source-grounded subjects, decisions, constraints, risks, evidence, and review
questions for a human to challenge the result.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable


AUDIT_SCHEMA = "wff.human-review-decision-quality-audit.v1"
SUMMARY_SCHEMA = "wff.human-review-decision-quality-summary.v1"

HEADING_PATTERN = re.compile(r"^(?P<marks>#{2,4})\s+(?P<title>.+?)\s*$", re.MULTILINE)
CODE_SPAN_PATTERN = re.compile(r"`([^`\n]{2,120})`")
API_PATH_PATTERN = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`]+)|(?<!\w)(/api/[^\s`]+)", re.IGNORECASE)
CAMEL_OR_SNAKE_PATTERN = re.compile(
    r"\b(?:[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]+)+|[a-z][a-z0-9]+(?:_[a-z0-9]+)+)\b"
)
IDENTITY_PATTERN = re.compile(r"\b(?:P[1-4]|ARCH|AC|WP|RQ)-[A-Z0-9][A-Z0-9._:-]*\b", re.IGNORECASE)
QUOTED_TERM_PATTERN = re.compile(r"[“\"]([^”\"\n]{2,60})[”\"]")

GENERIC_ANCHORS = {
    "系统",
    "模块",
    "对象",
    "主对象",
    "接口",
    "数据",
    "状态",
    "服务",
    "能力",
    "流程",
    "边界",
    "组件",
    "用户",
    "角色",
    "业务",
    "实现",
    "测试",
    "证据",
    "风险",
    "当前",
    "相关",
    "统一",
    "稳定身份",
}

DECISION_TERMS = (
    "选择",
    "采用",
    "决定",
    "必须",
    "只能",
    "允许",
    "禁止",
    "不得",
    "负责",
    "归属",
    "保留",
    "保持",
    "拆分",
    "合并",
    "写入",
    "读取",
    "返回",
)
RATIONALE_TERMS = (
    "因为",
    "因此",
    "为了",
    "原因",
    "基于",
    "前提",
    "约束",
    "只有",
    "否则",
    "以便",
    "避免",
    "防止",
)
RISK_TERMS = (
    "风险",
    "失败",
    "冲突",
    "阻塞",
    "异常",
    "例外",
    "非法",
    "缺失",
    "不足",
    "待确认",
    "待决",
    "review-bound",
    "回滚",
    "无权",
)
REVIEW_TERMS = (
    "请审阅",
    "请确认",
    "待确认",
    "需要确认",
    "需确认",
    "需要决定",
    "需决定",
    "需要评审",
    "审阅问题",
    "是否",
    "应由谁",
    "如何选择",
)
EVIDENCE_TERMS = (
    "证据",
    "测试",
    "验收",
    "证明",
    "来源",
    "指标",
    "审计",
    "trace",
    "回放",
    "运行时",
)

CRITICAL_HEADING_TERMS = {
    "prd-core": ("业务", "角色", "场景", "流程", "范围", "验收", "价值", "持续使用", "边界"),
    "esp-core": (
        "架构",
        "边界",
        "模块",
        "责任",
        "状态",
        "不变量",
        "流程",
        "交接",
        "数据",
        "接口",
        "契约",
        "权限",
        "审计",
        "实施",
        "风险",
    ),
    "action-card-set": ("行动卡",),
}

GENERIC_ONLY_PHRASES = (
    "支持扩展",
    "保持边界清晰",
    "提高可追踪性",
    "形成完整闭环",
    "统一处理",
    "按需处理",
    "每个主对象",
    "相关模块",
    "相关能力",
    "相关接口",
    "稳定身份、租户边界、版本和状态",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _walk_json_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_strings(item)


def _clean_anchor(value: str) -> str:
    anchor = re.sub(r"\s+", " ", value.strip().strip("`*_#-:：。.,，;；|/"))
    if not anchor or len(anchor) < 2 or len(anchor) > 80:
        return ""
    if anchor.lower() in {item.lower() for item in GENERIC_ANCHORS}:
        return ""
    if IDENTITY_PATTERN.fullmatch(anchor):
        return ""
    if anchor.isdigit():
        return ""
    return anchor


def source_anchor_terms(case_root: Path, refs: list[str], *, limit: int = 4000) -> list[str]:
    """Extract bounded, source-derived names without deciding their semantics."""

    root = case_root.resolve()
    anchors: set[str] = set()
    for ref in refs:
        path = (root / ref).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            continue
        text = path.read_text(encoding="utf-8")
        candidates: list[str] = []
        candidates.extend(CODE_SPAN_PATTERN.findall(text))
        candidates.extend(
            match.group("title") for match in HEADING_PATTERN.finditer(text)
        )
        candidates.extend(CAMEL_OR_SNAKE_PATTERN.findall(text))
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if payload is not None:
            candidates.extend(_walk_json_strings(payload))
        for candidate in candidates:
            anchor = _clean_anchor(candidate)
            if not anchor:
                continue
            # Long natural-language sentences are evidence, not stable anchors.
            if len(anchor) > 40 and not re.search(r"[_./]|[A-Z].*[A-Z]", anchor):
                continue
            anchors.add(anchor)
            if len(anchors) >= limit:
                return sorted(anchors, key=lambda item: (-len(item), item))
    return sorted(anchors, key=lambda item: (-len(item), item))


def split_markdown_sections(markdown: str) -> list[dict[str, Any]]:
    matches = list(HEADING_PATTERN.finditer(markdown))
    sections: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections.append(
            {
                "index": index + 1,
                "level": len(match.group("marks")),
                "title": match.group("title").strip(),
                "body": markdown[start:end].strip(),
            }
        )
    return sections


def _term_hits(text: str, terms: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return sorted({term for term in terms if term.lower() in lowered})


def _concrete_anchors(text: str, source_anchors: list[str]) -> list[str]:
    anchors: set[str] = set()
    for candidate in CODE_SPAN_PATTERN.findall(text):
        cleaned = _clean_anchor(candidate)
        if cleaned:
            anchors.add(cleaned)
    for match in API_PATH_PATTERN.finditer(text):
        candidate = match.group(1) or match.group(2) or ""
        cleaned = _clean_anchor(candidate)
        if cleaned:
            anchors.add(cleaned)
    for candidate in CAMEL_OR_SNAKE_PATTERN.findall(text):
        cleaned = _clean_anchor(candidate)
        if cleaned:
            anchors.add(cleaned)
    for candidate in QUOTED_TERM_PATTERN.findall(text):
        cleaned = _clean_anchor(candidate)
        if cleaned:
            anchors.add(cleaned)
    lowered = text.lower()
    for candidate in source_anchors:
        if candidate.lower() in lowered:
            anchors.add(candidate)
            if len(anchors) >= 24:
                break
    return sorted(anchors, key=lambda item: (-len(item), item))[:24]


def _is_critical(kind: str, title: str) -> bool:
    return any(term.lower() in title.lower() for term in CRITICAL_HEADING_TERMS[kind])


def _section_audit(
    *,
    kind: str,
    section: dict[str, Any],
    source_anchors: list[str],
    action_card: bool = False,
) -> dict[str, Any]:
    title = str(section["title"])
    body = str(section["body"])
    combined = f"{title}\n{body}"
    anchors = _concrete_anchors(combined, source_anchors)
    decisions = _term_hits(combined, DECISION_TERMS)
    rationales = _term_hits(combined, RATIONALE_TERMS)
    risks = _term_hits(combined, RISK_TERMS)
    reviews = _term_hits(combined, REVIEW_TERMS)
    evidence = _term_hits(combined, EVIDENCE_TERMS)
    findings: list[dict[str, str]] = []
    critical = action_card or _is_critical(kind, title)

    if len(re.sub(r"\s+", "", body)) < (100 if action_card else 80):
        findings.append(
            {
                "code": "section-too-thin",
                "severity": "error" if critical else "warning",
                "message": "The section is too short to support an expert review decision.",
            }
        )
    if not anchors:
        findings.append(
            {
                "code": "missing-concrete-subject",
                "severity": "error" if critical else "warning",
                "message": "No source-grounded object, role, operation, state, interface, or named subject is visible.",
            }
        )
    if not decisions:
        findings.append(
            {
                "code": "missing-current-decision",
                "severity": "error" if critical else "warning",
                "message": "The section describes principles without stating the current design or product decision.",
            }
        )
    if not rationales:
        findings.append(
            {
                "code": "missing-rationale-or-constraint",
                "severity": "warning",
                "message": "The section does not explain why the decision exists or what constrains it.",
            }
        )
    if critical and not risks:
        findings.append(
            {
                "code": "missing-risk-or-exception",
                "severity": "warning" if kind == "prd-core" else "error",
                "message": "The section does not expose a failure, exception, trade-off, or unresolved risk.",
            }
        )
    if critical and not reviews and "?" not in body and "？" not in body:
        findings.append(
            {
                "code": "missing-review-question",
                "severity": "warning" if kind == "prd-core" else "error",
                "message": "The reviewer is not told what decision, disagreement, or open question needs a response.",
            }
        )
    if action_card and not evidence:
        findings.append(
            {
                "code": "missing-proof-obligation",
                "severity": "error",
                "message": "The Action Card does not identify how the implementation decision will be proved.",
            }
        )
    if any(phrase in combined for phrase in GENERIC_ONLY_PHRASES) and not anchors:
        findings.append(
            {
                "code": "generic-principle-only",
                "severity": "error",
                "message": "Generic architecture/product principles are presented without concrete review subjects.",
            }
        )

    error_count = sum(1 for item in findings if item["severity"] == "error")
    warning_count = sum(1 for item in findings if item["severity"] == "warning")
    score = max(
        0,
        100
        - error_count * 22
        - warning_count * 8
        - (10 if critical and len(anchors) == 1 else 0),
    )
    verdict = "fail" if error_count else "review-bound" if warning_count >= 2 else "pass"
    return {
        "index": int(section["index"]),
        "level": int(section["level"]),
        "title": title,
        "critical": critical,
        "score": score,
        "verdict": verdict,
        "signals": {
            "concrete_anchors": anchors,
            "decision_terms": decisions,
            "rationale_terms": rationales,
            "risk_terms": risks,
            "review_terms": reviews,
            "evidence_terms": evidence,
        },
        "findings": findings,
    }


def _document_audit(
    *, kind: str, payload: dict[str, Any], source_anchors: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    sections = split_markdown_sections(str(payload.get("main_markdown") or ""))
    rows = [
        _section_audit(kind=kind, section=section, source_anchors=source_anchors)
        for section in sections
        if int(section["level"]) == 2
    ]
    findings: list[dict[str, str]] = []
    if not rows:
        findings.append(
            {
                "code": "no-review-sections",
                "severity": "error",
                "message": "The human projection has no H2 review sections.",
            }
        )
    if rows and sum(1 for row in rows if row["verdict"] == "pass") < max(2, len(rows) // 2):
        findings.append(
            {
                "code": "insufficient-decision-ready-sections",
                "severity": "error",
                "message": "Fewer than half of the primary sections are decision-ready.",
            }
        )
    return rows, findings


def _action_card_audit(
    *, payload: dict[str, Any], source_anchors: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    for index, card in enumerate(payload.get("cards", []), start=1):
        if not isinstance(card, dict):
            continue
        section = {
            "index": index,
            "level": 2,
            "title": str(card.get("title") or f"Action Card {index}"),
            "body": "\n\n".join(
                [
                    str(card.get("summary") or ""),
                    str(card.get("main_markdown") or ""),
                    str(card.get("appendix_markdown") or ""),
                    " ".join(str(item) for item in card.get("operation_ids", [])),
                ]
            ),
        }
        rows.append(
            _section_audit(
                kind="action-card-set",
                section=section,
                source_anchors=source_anchors,
                action_card=True,
            )
        )
    findings: list[dict[str, str]] = []
    if not rows:
        findings.append(
            {
                "code": "no-human-action-cards",
                "severity": "error",
                "message": "The projection contains no human Action Cards.",
            }
        )
    return rows, findings


def audit_projection(
    *,
    kind: str,
    payload: dict[str, Any],
    source_anchors: list[str] | None = None,
) -> dict[str, Any]:
    anchors = list(source_anchors or [])
    if kind == "action-card-set":
        sections, document_findings = _action_card_audit(payload=payload, source_anchors=anchors)
    else:
        sections, document_findings = _document_audit(
            kind=kind, payload=payload, source_anchors=anchors
        )

    error_count = sum(
        1
        for item in document_findings
        if item["severity"] == "error"
    ) + sum(
        1
        for section in sections
        for item in section["findings"]
        if item["severity"] == "error"
    )
    warning_count = sum(
        1
        for item in document_findings
        if item["severity"] == "warning"
    ) + sum(
        1
        for section in sections
        for item in section["findings"]
        if item["severity"] == "warning"
    )
    fail_sections = sum(1 for section in sections if section["verdict"] == "fail")
    review_bound_sections = sum(
        1 for section in sections if section["verdict"] == "review-bound"
    )
    score = (
        round(sum(int(section["score"]) for section in sections) / len(sections), 2)
        if sections
        else 0.0
    )
    if error_count:
        verdict = "fail"
    elif warning_count or review_bound_sections:
        verdict = "review-bound"
    else:
        verdict = "pass"
    return {
        "schema_version": AUDIT_SCHEMA,
        "projection_kind": kind,
        "verdict": verdict,
        "score": score,
        "summary": {
            "section_count": len(sections),
            "pass_count": sum(1 for section in sections if section["verdict"] == "pass"),
            "review_bound_count": review_bound_sections,
            "fail_count": fail_sections,
            "error_count": error_count,
            "warning_count": warning_count,
            "source_anchor_count": len(anchors),
        },
        "document_findings": document_findings,
        "sections": sections,
    }


def audit_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA,
        "verdict": str(report.get("verdict") or "fail"),
        "score": float(report.get("score") or 0.0),
        "section_count": int(report.get("summary", {}).get("section_count", 0)),
        "review_bound_count": int(
            report.get("summary", {}).get("review_bound_count", 0)
        ),
        "fail_count": int(report.get("summary", {}).get("fail_count", 0)),
        "error_count": int(report.get("summary", {}).get("error_count", 0)),
        "warning_count": int(report.get("summary", {}).get("warning_count", 0)),
    }


def repair_feedback(report: dict[str, Any], *, limit: int = 12) -> str:
    lines = [
        f"Decision-quality verdict: {report.get('verdict')}; score: {report.get('score')}."
    ]
    for section in report.get("sections", []):
        for finding in section.get("findings", []):
            lines.append(
                f"- [{finding.get('severity')}] {section.get('title')}: "
                f"{finding.get('code')} — {finding.get('message')}"
            )
            if len(lines) >= limit + 1:
                break
        if len(lines) >= limit + 1:
            break
    for finding in report.get("document_findings", []):
        if len(lines) >= limit + 1:
            break
        lines.append(
            f"- [{finding.get('severity')}] document: {finding.get('code')} — {finding.get('message')}"
        )
    lines.append(
        "Repair by naming concrete source-grounded subjects, the current decision, its reason or constraint, "
        "failure/trade-off conditions, evidence, and one explicit question the reviewer can answer."
    )
    return "\n".join(lines)


def decision_quality_report_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}.decision-quality.json")


def write_decision_quality_report(path: Path, report: dict[str, Any]) -> None:
    if report.get("schema_version") != AUDIT_SCHEMA:
        raise ValueError("invalid Human Review decision-quality report schema")
    _atomic_json(path, report)


def validate_decision_quality_report(
    path: Path, *, expected: dict[str, Any]
) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return _canonical_json(payload) == _canonical_json(expected)
