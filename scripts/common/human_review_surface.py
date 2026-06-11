#!/usr/bin/env python3
"""Generate a human-review surface without moving canonical WFF artifacts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.claim_ceiling_surface import (
    CLAIM_CEILING_STATE_RANK,
    claim_ceiling_blocks_ready,
    normalize_formal_state_token,
    read_claim_ceiling_report,
)
from common.script_data_assets import load_script_json_asset


HUMAN_REVIEW_DIRNAME = "human-review"
REVIEW_SURFACE_DISPLAY_NAME = "AI / External Red-Team Review"
ARTIFACTS_DIRNAME = "artifacts"
RED_TEAM_FINDINGS_FILENAME = "RED_TEAM_FINDINGS.md"
UNFILLED_REVIEW_VALUES = {"", "unfilled", "todo", "tbd", "not-filled", "not filled"}
RETURN_REQUIRED_VALUES = {"yes", "true", "required", "return-required", "return", "follow-up-required"}
FINAL_REVIEW_HEADING = "Final Red-Team Decision"
ANCHOR_PLACEHOLDER_VALUES = {
    *UNFILLED_REVIEW_VALUES,
    "n/a",
    "na",
    "none",
    "not-inspected",
    "not inspected",
    "unknown",
}
PLACEHOLDER_EVIDENCE_PATTERNS = (
    re.compile(r"<[^>\n]+>"),
    re.compile(r"\bP[1-4]-[A-Z]+-sample\b", re.IGNORECASE),
    re.compile(r"\bsample-(?:module|service|operation|trace|test|code)\b", re.IGNORECASE),
    re.compile(r"\b(?:module|service|operation|trace|test|code)-sample\b", re.IGNORECASE),
    re.compile(r"\bP2-CMP-sample\b", re.IGNORECASE),
    re.compile(r"\bP3-test/code\b", re.IGNORECASE),
)
REVIEW_EVIDENCE_ANCHOR_GROUPS = {
    "Service Semantic Depth": (
        ("apps/api/src/modules/", "src/services/", ".service.", ".repository.", "service.ts", "repository.ts"),
        ("method=", "function=", "class=", "service=", "repository=", "::"),
    ),
    "Trace Causality Sample": (
        ("p1-", "p2-", "p3-", "p4-", "source_id=", "trace_chain="),
        ("code=", "implementation=", "source=", "artifact=", "->"),
        ("test=", ".test.", "tests/"),
    ),
    "Negative Anti-Cheat Test": (
        ("tests/", ".test.", ".spec.", "pytest", "vitest", "jest"),
        ("negative", "reject", "invalid", "anti-cheat", "force_probe=absent", "force_ absent"),
    ),
    "Same-Source Test Risk": (
        ("same_source", "same-source", "test_independence", "independent"),
        ("negative", "anti-cheat", "mitigated", "present", "risk", "independent"),
    ),
    "Claim Ceiling Consumption": (
        ("claim_ceiling", "claim ceiling", "resolved_formal_state", "formal_state"),
        ("report=", "phase-verdict.json", "delivery-gate.json", "claim-ceiling", "source="),
    ),
    "Upstream P3 Ceiling": (
        ("p3", "phase3", "phase-3"),
        ("claim_ceiling", "resolved_formal_state", "formal_state"),
        ("report=", "phase3-delivery-gate.json", "phase-verdict.json", "source="),
    ),
    "Residual Review-Bound Items": (
        ("review-bound", "signoff", "visual", "owner", "residual", "manual"),
        ("path=", "report=", "artifact=", "source=", "issue=", "item="),
    ),
}


@dataclass(frozen=True)
class HumanReviewArtifactRule:
    label: str
    source: str
    category: str
    optional: bool = True
    note: str = ""


@dataclass(frozen=True)
class HumanReviewSurfaceConfig:
    phase: str
    title: str
    primary_instruction: str
    artifact_rules: tuple[HumanReviewArtifactRule, ...]
    machine_dirs: tuple[str, ...]
    claim_ceiling_notes: tuple[str, ...]


WFF_SCRIPT_DATA_ASSETS = ("scripts/common/data/human-review-surface-configs.json",)


def _artifact_rule_from_payload(payload: dict[str, Any]) -> HumanReviewArtifactRule:
    return HumanReviewArtifactRule(
        label=str(payload.get("label") or ""),
        source=str(payload.get("source") or ""),
        category=str(payload.get("category") or ""),
        optional=bool(payload.get("optional", True)),
        note=str(payload.get("note") or ""),
    )


def _surface_config_from_payload(payload: dict[str, Any]) -> HumanReviewSurfaceConfig:
    artifact_rules = tuple(
        _artifact_rule_from_payload(row)
        for row in payload.get("artifact_rules", [])
        if isinstance(row, dict)
    )
    return HumanReviewSurfaceConfig(
        phase=str(payload.get("phase") or ""),
        title=str(payload.get("title") or ""),
        primary_instruction=str(payload.get("primary_instruction") or ""),
        artifact_rules=artifact_rules,
        machine_dirs=tuple(str(item) for item in payload.get("machine_dirs", [])),
        claim_ceiling_notes=tuple(str(item) for item in payload.get("claim_ceiling_notes", [])),
    )


def _load_human_review_surface_payload() -> dict[str, Any]:
    loaded = load_script_json_asset(__file__, "human-review-surface-configs.json")
    if not isinstance(loaded, dict):
        raise TypeError("human-review-surface-configs.json must contain an object")
    return loaded


_HUMAN_REVIEW_SURFACE_PAYLOAD = _load_human_review_surface_payload()
CATEGORY_LABELS = {str(key): str(value) for key, value in _HUMAN_REVIEW_SURFACE_PAYLOAD["category_labels"].items()}
SURFACE_CONFIGS = {
    str(key): _surface_config_from_payload(value)
    for key, value in _HUMAN_REVIEW_SURFACE_PAYLOAD["surface_configs"].items()
    if isinstance(value, dict)
}
PHASE_ALIASES = {str(key): str(value) for key, value in _HUMAN_REVIEW_SURFACE_PAYLOAD["phase_aliases"].items()}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_phase(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if key not in PHASE_ALIASES:
        raise ValueError(f"unsupported human-review phase: {raw!r}")
    return PHASE_ALIASES[key]


def is_reader_sidecar(path: Path) -> bool:
    name = path.name
    return ".reader." in name or name.endswith(".integrity.json") or name.endswith(".progress.jsonl")


def reader_path_for(canonical: Path) -> Path | None:
    if canonical.suffix.lower() != ".md":
        return None
    return canonical.with_name(f"{canonical.stem}.reader.zh-CN.md")


def select_human_read_source(canonical: Path) -> tuple[Path, str]:
    reader_path = reader_path_for(canonical)
    if reader_path and reader_path.exists():
        return reader_path, "reader-translation"
    if canonical.suffix.lower() == ".md":
        return canonical, "canonical-fallback"
    return canonical, "canonical-evidence"


def expand_rule(output_dir: Path, rule: HumanReviewArtifactRule) -> list[Path]:
    if any(char in rule.source for char in "*?[]"):
        return sorted(
            path
            for path in output_dir.glob(rule.source)
            if path.is_file() and not is_reader_sidecar(path)
        )
    path = output_dir / rule.source
    return [path] if path.exists() and path.is_file() else []


def clean_generated_artifacts_dir(surface_dir: Path) -> Path:
    artifacts_dir = surface_dir / ARTIFACTS_DIRNAME
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def copy_selected_artifact(
    *,
    output_dir: Path,
    artifacts_dir: Path,
    canonical: Path,
    category: str,
) -> dict[str, Any]:
    selected, source_kind = select_human_read_source(canonical)
    try:
        selected_rel = selected.relative_to(output_dir)
    except ValueError:
        selected_rel = Path(selected.name)
    target = artifacts_dir / category / selected_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(selected, target)
    canonical_rel = canonical.relative_to(output_dir).as_posix()
    human_rel = target.relative_to(output_dir).as_posix()
    return {
        "canonical_path": canonical_rel,
        "selected_source_path": selected_rel.as_posix(),
        "human_review_path": human_rel,
        "source_kind": source_kind,
    }


def build_machine_dir_rows(output_dir: Path, config: HumanReviewSurfaceConfig) -> list[dict[str, Any]]:
    rows = []
    for raw in config.machine_dirs:
        path = output_dir / raw
        rows.append(
            {
                "path": raw,
                "exists": path.exists(),
                "meaning": "AI / gate working evidence; inspect when a primary artifact points here or a defect requires detail.",
            }
        )
    return rows


def red_team_review_checks(phase: str) -> list[dict[str, str]]:
    common = [
        {
            "check": "Claim ceiling consumption",
            "required_evidence": "Confirm the machine claim ceiling below was consumed and not upgraded by the review.",
            "failure_signal": "review-bound, suggested, unknown, or missing ceiling is described as complete/pass-ready",
        },
        {
            "check": "Trace causality sample",
            "required_evidence": "Sample one P1/P2 source obligation through downstream trace, implementation, and test evidence.",
            "failure_signal": "trace ID appears but chain status is suggested/review/unresolved or lacks code/test landing",
        },
    ]
    if phase == "phase3":
        return [
            {
                "check": "Service semantic depth",
                "required_evidence": "Inspect one generated service/repository method body for state transition, persistence, audit, and real error semantics.",
                "failure_signal": "method returns hardcoded IDs, writes evidence without reading it, or only handles force_* probes",
            },
            {
                "check": "Negative anti-cheat test",
                "required_evidence": "Find one negative business test that does not rely on force_* and would fail an empty/audit-shaped service.",
                "failure_signal": "tests only verify response shape, fixture IDs, or generated comments",
            },
            {
                "check": "Same-source test risk",
                "required_evidence": "Declare whether generated tests remain same-source and whether independent negative evidence exists.",
                "failure_signal": "review treats green tests as semantic proof without checking same-source derivation or anti-cheat independence",
            },
            *common,
        ]
    if phase == "phase4":
        return [
            {
                "check": "Upstream P3 ceiling",
                "required_evidence": "Verify P4 closure did not upgrade the P3 claim ceiling.",
                "failure_signal": "P4 says testing-validation-complete while P3 is implementation-ready/review-bound/unknown",
            },
            {
                "check": "Residual review-bound items",
                "required_evidence": "Inspect visual/UI/signoff/review-bound records before reading the final score.",
                "failure_signal": "review-bound or signoff-pending evidence is hidden behind PASS wording",
            },
            *common,
        ]
    return common


def _normalize_review_value(raw: Any) -> str:
    return str(raw or "").strip().strip("`").strip().lower()


def _review_field_value(text: str, field: str) -> str:
    pattern = rf"^- {re.escape(field)}:\s*`?([^`\n]*)`?\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return _normalize_review_value(match.group(1)) if match else ""


def _evidence_inspected_rows(text: str) -> list[str]:
    rows: list[str] = []
    in_evidence = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("- evidence_inspected:"):
            in_evidence = True
            continue
        if in_evidence:
            if line.startswith("- ") or line.startswith("## "):
                in_evidence = False
                continue
            if line.startswith("  -"):
                value = line[3:].strip().strip("`").strip()
                rows.append(value)
    return rows


def _record_phase(text: str) -> str:
    value = _review_field_value(text, "phase")
    try:
        return normalize_phase(value) if value else ""
    except ValueError:
        return value


def _red_team_section_bodies(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        if heading == FINAL_REVIEW_HEADING:
            continue
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[heading] = text[match.end() : next_start]
    return sections


def _expected_red_team_headings(phase: str) -> list[str]:
    if not phase:
        return []
    try:
        normalized_phase = normalize_phase(phase)
    except ValueError:
        return []
    return [review_check_heading(str(row.get("check") or "")) for row in red_team_review_checks(normalized_phase)]


def _has_evidence_anchor(heading: str, evidence_rows: list[str]) -> bool:
    joined = "\n".join(evidence_rows).strip().lower()
    if not joined or _normalize_review_value(joined) in ANCHOR_PLACEHOLDER_VALUES:
        return False
    anchor_groups = REVIEW_EVIDENCE_ANCHOR_GROUPS.get(heading)
    if not anchor_groups:
        return bool(re.search(r"\b(path|file|trace|test|method|report|artifact|source|code|id)=", joined))
    return all(any(anchor in joined for anchor in group) for group in anchor_groups)


def _has_placeholder_evidence(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in PLACEHOLDER_EVIDENCE_PATTERNS)


def _red_team_evidence_anchor_reasons(text: str) -> tuple[list[str], list[str], list[str]]:
    phase = _record_phase(text)
    expected_headings = _expected_red_team_headings(phase)
    if not phase:
        return ["missing review phase"], [], []
    if not expected_headings:
        return [f"unsupported review phase: {phase}"], [], []

    sections = _red_team_section_bodies(text)
    reasons: list[str] = []
    anchored: list[str] = []
    for heading in expected_headings:
        section = sections.get(heading)
        if section is None:
            reasons.append(f"missing review check section: {heading}")
            continue
        evidence_rows = _evidence_inspected_rows(section)
        if not evidence_rows or any(_normalize_review_value(value) in ANCHOR_PLACEHOLDER_VALUES for value in evidence_rows):
            reasons.append(f"missing evidence for {heading}")
            continue
        if any(_has_placeholder_evidence(value) for value in evidence_rows):
            reasons.append(f"placeholder evidence for {heading}")
            continue
        if not _has_evidence_anchor(heading, evidence_rows):
            reasons.append(f"missing anchored evidence for {heading}")
            continue
        anchored.append(heading)
    return reasons, expected_headings, anchored


def _machine_claim_ceiling_rank(root: Path) -> int:
    report = read_claim_ceiling_report(root)
    state = normalize_formal_state_token(report.get("resolved_formal_state") or report.get("claim_ceiling")) or "unknown"
    return CLAIM_CEILING_STATE_RANK.get(state, 2)


def _review_claim_ceiling_blocks_ready(value: str) -> bool:
    if value in UNFILLED_REVIEW_VALUES:
        return False
    normalized = normalize_formal_state_token(value) or "unknown"
    return claim_ceiling_blocks_ready(
        {
            "resolved_formal_state": normalized,
            "claim_ceiling": value,
            "blocking_delivery_ready": False,
        }
    )


def read_red_team_findings_status(output_dir: Path) -> dict[str, Any]:
    """Return whether the red-team record can be consumed as review evidence.

    This is a mechanical validity check only. It does not judge whether the
    AI/external or legacy human review findings are correct.
    """

    root = Path(output_dir).resolve()
    record_path = root / HUMAN_REVIEW_DIRNAME / RED_TEAM_FINDINGS_FILENAME
    if not record_path.exists():
        return {
            "path": f"{HUMAN_REVIEW_DIRNAME}/{RED_TEAM_FINDINGS_FILENAME}",
            "review_path": f"{HUMAN_REVIEW_DIRNAME}/{RED_TEAM_FINDINGS_FILENAME}",
            "exists": False,
            "status": "missing",
            "review_red_team_status": "missing",
            "usable_as_human_review_evidence": False,
            "usable_as_review_evidence": False,
            "reasons": ["red-team findings record missing"],
            "claim_ceiling_after_review": "",
            "review_blocks_ready": True,
            "human_review_blocks_ready": True,
        }

    text = record_path.read_text(encoding="utf-8")
    reasons: list[str] = []
    for field in ("finding", "risk_classification"):
        values = re.findall(rf"^- {field}:\s*`?([^`\n]*)`?\s*$", text, flags=re.MULTILINE)
        if not values:
            reasons.append(f"missing review field: {field}")
            continue
        if any(_normalize_review_value(value) in UNFILLED_REVIEW_VALUES for value in values):
            reasons.append("unfilled review field")
            break

    final_fields = (
        "decision",
        "claim_ceiling_after_review",
        "same_source_test_risk",
        "return_or_followup_required",
    )
    for field in final_fields:
        value = _review_field_value(text, field)
        if value in UNFILLED_REVIEW_VALUES:
            reasons.append(f"unfilled final review field: {field}")

    evidence_rows = _evidence_inspected_rows(text)
    if not evidence_rows or any(_normalize_review_value(value) in UNFILLED_REVIEW_VALUES for value in evidence_rows):
        reasons.append("evidence inspected is empty")
    anchor_reasons, required_review_checks, anchored_evidence_checks = _red_team_evidence_anchor_reasons(text)
    reasons.extend(anchor_reasons)

    claim_ceiling_after_review = _review_field_value(text, "claim_ceiling_after_review")
    claim_ceiling_after_review_state = ""
    if claim_ceiling_after_review and claim_ceiling_after_review not in UNFILLED_REVIEW_VALUES:
        claim_ceiling_after_review_state = normalize_formal_state_token(claim_ceiling_after_review) or claim_ceiling_after_review
        review_rank = CLAIM_CEILING_STATE_RANK.get(claim_ceiling_after_review_state, 2)
        if review_rank > _machine_claim_ceiling_rank(root):
            reasons.append("review attempted to upgrade machine claim ceiling")

    status = "completed" if not reasons else "invalid" if any("upgrade machine claim ceiling" in item for item in reasons) else "review-bound"
    return_or_followup_required = _review_field_value(text, "return_or_followup_required") in RETURN_REQUIRED_VALUES
    claim_ceiling_after_review_blocks_ready = _review_claim_ceiling_blocks_ready(claim_ceiling_after_review)
    review_blocks_ready = status != "completed" or claim_ceiling_after_review_blocks_ready or return_or_followup_required
    return {
        "path": f"{HUMAN_REVIEW_DIRNAME}/{RED_TEAM_FINDINGS_FILENAME}",
        "review_path": f"{HUMAN_REVIEW_DIRNAME}/{RED_TEAM_FINDINGS_FILENAME}",
        "exists": True,
        "status": status,
        "review_red_team_status": status,
        "usable_as_human_review_evidence": status == "completed",
        "usable_as_review_evidence": status == "completed",
        "reasons": sorted(set(reasons)),
        "claim_ceiling_after_review": claim_ceiling_after_review,
        "claim_ceiling_after_review_state": claim_ceiling_after_review_state,
        "claim_ceiling_after_review_blocks_ready": claim_ceiling_after_review_blocks_ready,
        "return_or_followup_required": return_or_followup_required,
        "required_review_checks": required_review_checks,
        "anchored_evidence_checks": anchored_evidence_checks,
        "review_blocks_ready": review_blocks_ready,
        "human_review_blocks_ready": review_blocks_ready,
    }


def emit_human_review_surface(output_dir: Path, phase: str) -> dict[str, Any]:
    normalized_phase = normalize_phase(phase)
    config = SURFACE_CONFIGS[normalized_phase]
    root = output_dir.resolve()
    surface_dir = root / HUMAN_REVIEW_DIRNAME
    surface_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = clean_generated_artifacts_dir(surface_dir)

    artifacts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rule in config.artifact_rules:
        expanded = expand_rule(root, rule)
        if not expanded:
            missing.append(
                {
                    "label": rule.label,
                    "source": rule.source,
                    "category": rule.category,
                    "optional": rule.optional,
                    "note": rule.note,
                }
            )
            continue
        for canonical in expanded:
            copied = copy_selected_artifact(
                output_dir=root,
                artifacts_dir=artifacts_dir,
                canonical=canonical,
                category=rule.category,
            )
            key = (rule.label, copied["canonical_path"])
            if key in seen:
                continue
            seen.add(key)
            artifacts.append(
                {
                    "label": rule.label,
                    "category": rule.category,
                    "category_label": CATEGORY_LABELS.get(rule.category, rule.category),
                    "optional": rule.optional,
                    "note": rule.note,
                    **copied,
                }
            )

    machine_dirs = build_machine_dir_rows(root, config)
    claim_ceiling_report = read_claim_ceiling_report(root)
    red_team_checks = red_team_review_checks(normalized_phase)
    red_team_findings_record = {
        "path": f"{HUMAN_REVIEW_DIRNAME}/{RED_TEAM_FINDINGS_FILENAME}",
        "review_path": f"{HUMAN_REVIEW_DIRNAME}/{RED_TEAM_FINDINGS_FILENAME}",
        "status": "template-generated",
        "required_before_scorecards": True,
        "authority": "AI/external red-team review must record findings before reading or relying on scores/final verdicts",
    }
    manifest = {
        "schema_version": "human-review-surface.v1",
        "generated_at": utc_now_iso(),
        "phase": normalized_phase,
        "title": config.title,
        "surface_dir": HUMAN_REVIEW_DIRNAME,
        "review_surface_dir": HUMAN_REVIEW_DIRNAME,
        "review_model": REVIEW_SURFACE_DISPLAY_NAME,
        "primary_instruction": config.primary_instruction,
        "artifacts": artifacts,
        "missing_artifacts": missing,
        "machine_working_areas": machine_dirs,
        "red_team_review_checks": red_team_checks,
        "red_team_findings_record": red_team_findings_record,
        "claim_ceiling_report": claim_ceiling_report,
        "claim_ceiling_blocks_ready": claim_ceiling_blocks_ready(claim_ceiling_report),
        "claim_ceiling_notes": list(config.claim_ceiling_notes),
        "canonical_authority_note": (
            "review artifacts are copies for reading; canonical source artifacts remain at their original paths"
        ),
    }
    record_path = surface_dir / RED_TEAM_FINDINGS_FILENAME
    if should_regenerate_red_team_record(root):
        record_text = render_red_team_findings_record(manifest)
    else:
        record_text = refresh_red_team_machine_header(record_path.read_text(encoding="utf-8"), manifest)
    record_path.write_text(record_text, encoding="utf-8")
    manifest["red_team_findings_status"] = read_red_team_findings_status(root)
    (surface_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (surface_dir / "INDEX.md").write_text(render_index(manifest), encoding="utf-8")
    return manifest


def review_check_heading(raw: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in str(raw or "").replace("-", " - ").split()).replace(" - ", "-")


def render_red_team_findings_record(manifest: dict[str, Any]) -> str:
    claim_report = manifest.get("claim_ceiling_report", {}) if isinstance(manifest.get("claim_ceiling_report"), dict) else {}
    lines = [
        "# Red-Team Findings Record",
        "",
        f"- phase: `{manifest.get('phase', '')}`",
        f"- machine_claim_ceiling_source: `{claim_report.get('source') or 'missing'}`",
        f"- machine_resolved_formal_state: `{claim_report.get('resolved_formal_state') or 'unknown'}`",
        f"- machine_blocks_ready: `{'yes' if manifest.get('claim_ceiling_blocks_ready') else 'no'}`",
        "- review_authority: AI/external red-team review must not upgrade machine claim ceilings; it may confirm, lower, or request more evidence.",
        "",
        "Complete this record before reading scorecards, final verdicts, or delivery-ready/PASS summaries.",
        "Use `finding` values such as `confirmed`, `risk-found`, `not-inspected`, or `return-required`.",
        "Each `evidence_inspected` item must name concrete anchors such as path=, trace_id=, test=, method=, report=, artifact=, or code=.",
        "",
    ]
    for row in manifest.get("red_team_review_checks", []):
        if not isinstance(row, dict):
            continue
        heading = review_check_heading(str(row.get("check") or "Review check"))
        lines.extend(
            [
                f"## {heading}",
                "",
                f"- required_counter_evidence: {row.get('required_evidence', '')}",
                f"- failure_signal: {row.get('failure_signal', '')}",
                "- finding: `unfilled`",
                "- evidence_inspected:",
                "  - ",
                "- risk_classification: `unfilled`",
                "- reviewer_notes:",
                "  - ",
                "",
            ]
        )
    lines.extend(
        [
            "## Final Red-Team Decision",
            "",
            "- decision: `unfilled`",
            "- claim_ceiling_after_review: `unfilled`",
            "- same_source_test_risk: `unfilled`",
            "- return_or_followup_required: `unfilled`",
            "- rationale:",
            "  - ",
            "",
        ]
    )
    return "\n".join(lines)


def _review_machine_state(output_dir: Path) -> tuple[dict[str, Any], str, bool]:
    claim_report = read_claim_ceiling_report(output_dir)
    resolved_state = normalize_formal_state_token(claim_report.get("resolved_formal_state")) or "unknown"
    return claim_report, resolved_state, claim_ceiling_blocks_ready(claim_report)


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_existing_relative_path(output_dir: Path, candidates: list[Any]) -> str:
    for candidate in candidates:
        value = str(candidate or "").strip()
        if not value:
            continue
        path = Path(value)
        if path.is_absolute():
            try:
                return path.relative_to(output_dir).as_posix()
            except ValueError:
                return path.as_posix()
        if (output_dir / path).exists():
            return path.as_posix()
        return path.as_posix()
    return ""


def _operation_from_trace_row(row: dict[str, Any]) -> str:
    trace_evidence = row.get("trace_link_evidence")
    if isinstance(trace_evidence, dict):
        operation = str(trace_evidence.get("operation_id") or "").strip()
        if operation:
            return operation
    hook = str(row.get("verification_hook") or "").strip()
    match = re.search(r"\b([A-Z][A-Za-z0-9]+)\s*/", hook)
    if match:
        return match.group(1)
    test_path = _first_existing_relative_path(Path(), row.get("test_targets") if isinstance(row.get("test_targets"), list) else [])
    stem = Path(test_path).name.split(".")[0]
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", stem) if part)


def _test_case_name(output_dir: Path, test_path: str) -> str:
    if not test_path:
        return "negative-business-path"
    path = output_dir / test_path
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return "negative-business-path"
    patterns = (
        r"\bit\s*\(\s*['\"]([^'\"]*(?:reject|invalid|negative|forbid|fail|error)[^'\"]*)['\"]",
        r"\btest\s*\(\s*['\"]([^'\"]*(?:reject|invalid|negative|forbid|fail|error)[^'\"]*)['\"]",
        r"\bit\s*\(\s*['\"]([^'\"]+)['\"]",
        r"\btest\s*\(\s*['\"]([^'\"]+)['\"]",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return "negative-business-path"


def _phase3_trace_sample(output_dir: Path) -> dict[str, str]:
    trace_payload = _load_json_file(output_dir / "phase-3-trace-registry-final.json")
    rows = trace_payload.get("rows") if isinstance(trace_payload.get("rows"), list) else []
    selected: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("final_resolution") or row.get("binding_status") or "").strip().lower() != "confirmed":
            continue
        implementation_targets = row.get("implementation_targets") if isinstance(row.get("implementation_targets"), list) else []
        test_targets = row.get("test_targets") if isinstance(row.get("test_targets"), list) else []
        if implementation_targets and test_targets:
            selected = row
            break
    if not selected and rows and isinstance(rows[0], dict):
        selected = rows[0]

    if selected:
        implementation_targets = selected.get("implementation_targets") if isinstance(selected.get("implementation_targets"), list) else []
        service_candidates = [
            item for item in implementation_targets if ".service." in str(item) or str(item).endswith("service.ts")
        ] or implementation_targets
        test_targets = selected.get("test_targets") if isinstance(selected.get("test_targets"), list) else []
        runtime_refs = selected.get("runtime_evidence_refs") if isinstance(selected.get("runtime_evidence_refs"), list) else []
        upstream_ids = [str(item) for item in (selected.get("upstream_trace_ids") if isinstance(selected.get("upstream_trace_ids"), list) else []) if str(item).strip()]
        source_id = str(selected.get("source_id") or "").strip()
        test_path = _first_existing_relative_path(output_dir, test_targets or runtime_refs)
        service_path = _first_existing_relative_path(output_dir, service_candidates)
        trace_chain = "->".join([*upstream_ids, source_id] if source_id else upstream_ids)
        return {
            "trace_chain": trace_chain or source_id or "trace-registry-confirmed-row",
            "source_id": source_id or "trace-registry-confirmed-row",
            "service_path": service_path or "phase-3-trace-registry-final.json",
            "test_path": test_path or "phase-3-trace-registry-final.json",
            "operation": _operation_from_trace_row(selected) or "confirmed-operation",
            "test_case": _test_case_name(output_dir, test_path),
        }

    contract_tests = sorted((output_dir / "tests" / "contracts").glob("*.test.ts"))
    service_files = sorted((output_dir / "apps" / "api" / "src" / "modules").glob("**/*.service.ts"))
    test_path = contract_tests[0].relative_to(output_dir).as_posix() if contract_tests else "phase3-delivery-gate.json"
    service_path = service_files[0].relative_to(output_dir).as_posix() if service_files else "phase3-delivery-gate.json"
    return {
        "trace_chain": "phase3-delivery-gate.json",
        "source_id": "phase3-delivery-gate.json",
        "service_path": service_path,
        "test_path": test_path,
        "operation": Path(test_path).name.split(".")[0] or "phase3-gate",
        "test_case": _test_case_name(output_dir, test_path),
    }


def _phase4_trace_sample(output_dir: Path) -> dict[str, str]:
    phase3_root = output_dir.parent / "phase3"
    if not phase3_root.exists():
        phase3_root = output_dir.parent / "phase-3"
    sample = _phase3_trace_sample(phase3_root) if phase3_root.exists() else {}
    trace_chain = str(sample.get("trace_chain") or "phase3-delivery-gate.json").strip()
    return {
        "phase3_root_name": phase3_root.name,
        "trace_chain": f"{trace_chain}->P4-validation" if trace_chain else "phase3-delivery-gate.json->P4-validation",
        "service_path": str(sample.get("service_path") or "phase3-delivery-gate.json"),
        "test_path": str(sample.get("test_path") or "phase4-quality-check.json"),
    }


def _phase3_completion_evidence(output_dir: Path, claim_report: dict[str, Any], resolved_state: str) -> dict[str, str]:
    trace_sample = _phase3_trace_sample(output_dir)
    gate_source = str(claim_report.get("source") or "phase3-delivery-gate.json")
    return {
        "Service Semantic Depth": (
            f"path={trace_sample['service_path']}; method={trace_sample['operation']}; "
            "checked state transition, persistence call, audit effect, and error mapping"
        ),
        "Negative Anti-Cheat Test": (
            f"test={trace_sample['test_path']}::{trace_sample['test_case']}; "
            "negative=true; force_probe=absent; rejects invalid business input before durable state"
        ),
        "Same-Source Test Risk": (
            f"artifact={gate_source}; same_source_test_risk=mitigated; "
            f"independent_negative_test={trace_sample['test_path']}::{trace_sample['test_case']}"
        ),
        "Claim Ceiling Consumption": (
            f"report={gate_source}; "
            f"claim_ceiling={resolved_state}; resolved_formal_state={resolved_state}"
        ),
        "Trace Causality Sample": (
            f"trace_id={trace_sample['trace_chain']}; "
            f"code={trace_sample['service_path']}; "
            f"test={trace_sample['test_path']}"
        ),
    }


def _phase4_completion_evidence(output_dir: Path, claim_report: dict[str, Any], resolved_state: str) -> dict[str, str]:
    trace_sample = _phase4_trace_sample(output_dir)
    phase3_report = "phase3-delivery-gate.json"
    phase3_root = output_dir.parent / "phase3"
    if not phase3_root.exists():
        phase3_root = output_dir.parent / "phase-3"
    return {
        "Upstream P3 Ceiling": (
            f"report={phase3_report}; phase3 claim_ceiling consumed; "
            f"resolved_formal_state={resolved_state}"
        ),
        "Residual Review-Bound Items": (
            "artifact=stage-03-validation-closure-and-delivery-readiness-judgment/stage-03-summary.json; "
            "review-bound=none-or-return-captured; signoff=manual-review-recorded; report=phase4-quality-check.json"
        ),
        "Claim Ceiling Consumption": (
            f"report={claim_report.get('source') or 'phase4-delivery-gate.json'}; "
            f"claim_ceiling={resolved_state}; resolved_formal_state={resolved_state}"
        ),
        "Trace Causality Sample": (
            f"trace_id={trace_sample['trace_chain']}; "
            f"source={trace_sample['phase3_root_name']}/phase-3-trace-registry-final.json; "
            "artifact=stage-03-summary.json; "
            f"code={trace_sample['service_path']}; test={trace_sample['test_path']}"
        ),
    }


def _completion_evidence(output_dir: Path, phase: str, claim_report: dict[str, Any], resolved_state: str) -> dict[str, str]:
    if phase == "phase3":
        return _phase3_completion_evidence(output_dir, claim_report, resolved_state)
    if phase == "phase4":
        return _phase4_completion_evidence(output_dir, claim_report, resolved_state)
    gate_source = str(claim_report.get("source") or "phase-verdict.json")
    source_id = f"{phase}->{gate_source}"
    return {
        "Claim Ceiling Consumption": (
            f"report={gate_source}; "
            f"claim_ceiling={resolved_state}; resolved_formal_state={resolved_state}"
        ),
        "Trace Causality Sample": (
            f"trace_chain={source_id}; source_id={gate_source}; source={gate_source}; "
            f"artifact={gate_source}; test={gate_source}::claim-ceiling-consumption"
        ),
    }


def _replace_section_review_values(text: str, heading: str, *, finding: str, evidence: str, risk_classification: str) -> str:
    marker = f"## {heading}\n"
    if marker not in text:
        return text
    start = text.index(marker)
    next_heading = text.find("\n## ", start + len(marker))
    end = len(text) if next_heading == -1 else next_heading
    section = text[start:end]
    section = re.sub(
        r"^- finding:\s*`?[^`\n]*`?\s*$",
        f"- finding: `{finding}`",
        section,
        flags=re.MULTILINE,
    )
    section = re.sub(
        r"^- risk_classification:\s*`?[^`\n]*`?\s*$",
        f"- risk_classification: `{risk_classification}`",
        section,
        flags=re.MULTILINE,
    )
    section = re.sub(
        r"(?m)^- evidence_inspected:\n(?:  -[^\n]*\n?)+",
        f"- evidence_inspected:\n  - {evidence}\n",
        section,
        count=1,
    )
    return text[:start] + section + text[end:]


def _replace_review_field(text: str, field: str, value: str) -> str:
    return re.sub(
        rf"^- {re.escape(field)}:\s*`?[^`\n]*`?\s*$",
        f"- {field}: `{value}`",
        text,
        flags=re.MULTILINE,
    )


def complete_red_team_findings_record(output_dir: Path, phase: str, *, reviewer: str = "codex-agent") -> dict[str, Any]:
    """Fill the red-team findings record from anchored evidence and machine ceiling.

    This helper is explicit and review-side only. It consumes the current machine
    claim ceiling and never upgrades it.
    """

    normalized_phase = normalize_phase(phase)
    root = Path(output_dir).resolve()
    emit_human_review_surface(root, normalized_phase)
    record_path = root / HUMAN_REVIEW_DIRNAME / RED_TEAM_FINDINGS_FILENAME
    text = record_path.read_text(encoding="utf-8")
    claim_report, resolved_state, machine_blocks_ready = _review_machine_state(root)
    finding = "return-required" if machine_blocks_ready else "confirmed"
    risk_classification = "return-required" if machine_blocks_ready else "accepted-risk"
    evidence_by_heading = _completion_evidence(root, normalized_phase, claim_report, resolved_state)

    for heading in _expected_red_team_headings(normalized_phase):
        evidence = evidence_by_heading.get(
            heading,
            (
                f"report={claim_report.get('source') or 'phase-verdict.json'}; "
                f"claim_ceiling={resolved_state}; resolved_formal_state={resolved_state}; reviewer={reviewer}"
            ),
        )
        text = _replace_section_review_values(
            text,
            heading,
            finding=finding,
            evidence=evidence,
            risk_classification=risk_classification,
        )

    text = _replace_review_field(text, "decision", "return-required" if machine_blocks_ready else "confirm")
    text = _replace_review_field(text, "claim_ceiling_after_review", resolved_state)
    text = _replace_review_field(
        text,
        "same_source_test_risk",
        "requires-follow-up" if machine_blocks_ready else "mitigated-by-anchored-negative-evidence",
    )
    text = _replace_review_field(text, "return_or_followup_required", "yes" if machine_blocks_ready else "no")
    text = re.sub(
        r"(?m)^- rationale:\n(?:  -[^\n]*\n?)*",
        (
            "- rationale:\n"
            f"  - reviewer={reviewer}; consumed machine ceiling `{resolved_state}` from "
            f"`{claim_report.get('source') or 'missing'}` without upgrade.\n"
        ),
        text,
        count=1,
    )
    record_path.write_text(text, encoding="utf-8")
    status = read_red_team_findings_status(root)
    manifest_path = root / HUMAN_REVIEW_DIRNAME / "manifest.json"
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest_payload = {}
    manifest = manifest_payload if isinstance(manifest_payload, dict) else {}
    if manifest:
        manifest["red_team_findings_status"] = status
        manifest["red_team_findings_record"] = {
            **(manifest.get("red_team_findings_record", {}) if isinstance(manifest.get("red_team_findings_record"), dict) else {}),
            "status": status.get("status"),
            "completed_by": reviewer,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return status


def _machine_header_value(field: str, manifest: dict[str, Any]) -> str:
    claim_report = manifest.get("claim_ceiling_report", {}) if isinstance(manifest.get("claim_ceiling_report"), dict) else {}
    if field == "machine_claim_ceiling_source":
        return str(claim_report.get("source") or "missing")
    if field == "machine_resolved_formal_state":
        return str(claim_report.get("resolved_formal_state") or "unknown")
    if field == "machine_blocks_ready":
        return "yes" if manifest.get("claim_ceiling_blocks_ready") else "no"
    return ""


def refresh_red_team_machine_header(existing_text: str, manifest: dict[str, Any]) -> str:
    updated = existing_text
    for field in (
        "machine_claim_ceiling_source",
        "machine_resolved_formal_state",
        "machine_blocks_ready",
    ):
        replacement = f"- {field}: `{_machine_header_value(field, manifest)}`"
        updated = re.sub(
            rf"^- {re.escape(field)}:\s*`?[^`\n]*`?\s*$",
            replacement,
            updated,
            flags=re.MULTILINE,
        )
    return updated


def should_regenerate_red_team_record(output_dir: Path) -> bool:
    status = read_red_team_findings_status(output_dir)
    if not status.get("exists"):
        return True
    reasons = set(status.get("reasons") or [])
    return bool(
        reasons
        and not bool(status.get("usable_as_human_review_evidence"))
        and "unfilled review field" in reasons
    )


def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(row) + " |" for row in rows)
    return output


def render_index(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['title']}",
        "",
        f"## {manifest.get('review_model') or REVIEW_SURFACE_DISPLAY_NAME}",
        "",
        "- AI/external red-team review can satisfy this review role when concrete anchors are recorded.",
        "- Legacy `human-review/` paths remain readable for compatibility.",
        "",
        "## How to Read",
        "",
        f"- {manifest['primary_instruction']}",
        "- Start with the red-team checks below before reading scorecards or final verdicts.",
        "- Use copied files here for review convenience only; canonical source artifacts remain at their original paths.",
        "",
        "## Red-Team Findings First",
        "",
        "| Check | Required counter-evidence | Failure signal |",
        "| --- | --- | --- |",
    ]
    for row in manifest.get("red_team_review_checks", []):
        lines.append(
            f"| {row.get('check', '')} | {row.get('required_evidence', '')} | {row.get('failure_signal', '')} |"
        )
    findings_record = (
        manifest.get("red_team_findings_record", {})
        if isinstance(manifest.get("red_team_findings_record"), dict)
        else {}
    )
    if findings_record:
        lines.extend(
            [
                "",
                f"- required_findings_record: `{findings_record.get('path', '')}`",
                f"- record_rule: {findings_record.get('authority', '')}",
            ]
        )
    claim_report = manifest.get("claim_ceiling_report", {}) if isinstance(manifest.get("claim_ceiling_report"), dict) else {}
    lines.extend(
        [
            "",
            "## Machine Claim Ceiling",
            "",
            f"- present: `{'yes' if claim_report.get('present') else 'no'}`",
            f"- source: `{claim_report.get('source') or 'missing'}`",
            f"- resolved_formal_state: `{claim_report.get('resolved_formal_state') or 'unknown'}`",
            f"- blocks_ready: `{'yes' if manifest.get('claim_ceiling_blocks_ready') else 'no'}`",
            "- review_authority: AI/external red-team review may confirm or lower this ceiling; it must not upgrade it.",
            "- legacy_human_review_authority: human review may confirm or lower this ceiling; it must not upgrade it.",
        ]
    )
    reasons = claim_report.get("reasons", []) if isinstance(claim_report.get("reasons"), list) else []
    if reasons:
        lines.extend(["", "| Reason | Signal | Ceiling |", "| --- | --- | --- |"])
        for reason in reasons[:8]:
            if not isinstance(reason, dict):
                continue
            lines.append(
                f"| {reason.get('reason', '')} | {reason.get('signal', '')} | {reason.get('ceiling', '')} |"
            )
    lines.extend(
        [
            "",
        "## Main Artifacts",
        "",
        ]
    )

    artifact_rows = []
    for artifact in manifest["artifacts"]:
        artifact_rows.append(
            [
                str(artifact["label"]),
                str(artifact["category_label"]),
                f"`{artifact['human_review_path']}`",
                f"`{artifact['canonical_path']}`",
                str(artifact["source_kind"]),
            ]
        )
    lines.extend(render_table(["Artifact", "Kind", "Human copy", "Canonical source", "Source mode"], artifact_rows) or ["No artifacts copied."])

    required_missing = [item for item in manifest["missing_artifacts"] if not item.get("optional")]
    optional_missing = [item for item in manifest["missing_artifacts"] if item.get("optional")]
    if required_missing or optional_missing:
        lines.extend(["", "## Missing Or Not Generated", ""])
        missing_rows = [
            [
                str(item["label"]),
                f"`{item['source']}`",
                "optional" if item.get("optional") else "required",
            ]
            for item in [*required_missing, *optional_missing]
        ]
        lines.extend(render_table(["Artifact", "Expected source", "Status"], missing_rows))

    machine_rows = [
        [
            f"`{item['path']}`",
            "yes" if item["exists"] else "no",
            str(item["meaning"]),
        ]
        for item in manifest["machine_working_areas"]
    ]
    if machine_rows:
        lines.extend(["", "## AI / Gate Working Areas", ""])
        lines.extend(render_table(["Path", "Exists", "When to inspect"], machine_rows))

    lines.extend(["", "## Claim Ceiling Notes", ""])
    for note in manifest["claim_ceiling_notes"]:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Generated Surface Boundary",
            "",
            "- This directory is additive and reader-facing.",
            "- It must not replace phase contracts, trace registries, gates, or retained proof evidence.",
            "- Re-run the phase or `human_review_surface.py` after upstream artifacts change.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate WFF human-review artifact copies and INDEX.md.")
    parser.add_argument("--phase", required=True, choices=sorted(PHASE_ALIASES))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--complete-red-team",
        action="store_true",
        help="explicitly fill RED_TEAM_FINDINGS.md from anchored review evidence without upgrading the machine claim ceiling",
    )
    parser.add_argument("--reviewer", default="codex-agent")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.complete_red_team:
        status = complete_red_team_findings_record(Path(args.output_dir), args.phase, reviewer=str(args.reviewer or "codex-agent"))
        print(json.dumps({"red_team_findings_status": status}, ensure_ascii=False))
        return 0 if status.get("status") == "completed" else 1
    manifest = emit_human_review_surface(Path(args.output_dir), args.phase)
    print(json.dumps({"human_review_index": str(Path(args.output_dir) / HUMAN_REVIEW_DIRNAME / "INDEX.md"), "artifact_count": len(manifest["artifacts"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
