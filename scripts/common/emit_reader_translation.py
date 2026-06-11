#!/usr/bin/env python3
"""Thin-script LLM reader translation for localized lifecycle documents.

LLM-controlled segmentation: the LLM proposes natural segment boundaries, then
the Python script validates those boundaries so unusually dense sections are not
sent as oversized translation chunks.

Examples:
  python3 emit_reader_translation.py --canonical prd.md --artifact-label "P1 PRD"
  python3 emit_reader_translation.py --canonical prd.md --model deepseek-chat \\
      --api-base https://api.deepseek.com/v1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.reader_artifact_integrity import (
    IntegrityResult,
    StructureReport,
    check_integrity,
    check_structure,
    render_reader_preamble,
    write_integrity_report,
)
from common.output_language import resolve_output_locale


@dataclass(frozen=True)
class TranslationResult:
    verdict: str
    canonical_path: Path
    reader_path: Path
    translated_path: Path | None
    locale: str
    artifact_label: str
    detail: str
    integrity: IntegrityResult | None


@dataclass
class _LLMResponse:
    content: str
    finish_reason: str
    usage: dict[str, int]


def build_translated_reader_path(canonical_path: Path, locale: str) -> Path:
    base = canonical_path.with_suffix("")
    return base.with_name(f"{base.name}.reader.{locale}.md")


_SYSTEM_PROMPT = """You are a senior technical translator producing reader-facing target-locale editions of lifecycle documents.

## Immutable Tokens (preserve exactly)
These MUST remain unchanged in the output:
- Trace IDs: P1-..., ARCH-..., WP-..., RBI-..., AC-..., WO-..., RQ-..., EP-..., BVS-..., DR-...
- File names and paths (scripts/phase1/run_phase1_full_trial.py, engineering-spec-pack.md)
- Code, API endpoints, schema field names, database column names
- Object/class identifiers (TenantWorkspace, ActorRole, AuditRecord, TrackedScope)
- Status enum values (pass, fail, warn, review-ready, downstream-start-safe, review-bound)
- Dot-separated package identifiers (geo.baseline.generation.and.query)
- Version strings and date stamps in technical contexts

## Translation Rules

### Prose
- Translate ALL headings, paragraphs, bullet values, table headers, table cells into natural target-locale language
- For zh-CN: natural Simplified Chinese with local professional expression; avoid stiff literal translation
- Split long English sentences into shorter Chinese ones when facts remain intact
- Business roles, workflow descriptions, judgment labels, rationale prose — all translate
- Snake_case labels used as document labels (not schema fields) must be translated

### Headings
- EVERY markdown heading (H1, H2, H3, H4, H5, H6) in the source MUST appear in the translation
- Translate heading text into target locale; keep `#`/`##`/`###` markers and heading level unchanged
- The number of H2 (`## `) headings in your output must EXACTLY match the source -- count them in source and verify in output
- If a heading seems redundant: translate it anyway. It is better to keep a heading than to drop it

### Tables
- Preserve markdown table structure: pipes, alignment rows, column count, row count
- EVERY table row in the source MUST produce exactly ONE table row in the output
- Translate cell content but never skip, merge, or summarize rows
- Translate reader-facing table headers
- Field-identifier headers (requirement_id, trace_id, target_asset_id) may stay unchanged
- Acceptance criteria Given/When/Then: translate the prose, preserve technical object names

### Terminology (zh-CN)
- workflow-first → 工作流优先
- review-bound → 受评审约束
- downstream-start-safe → 可安全启动下游
- tracked scope → 跟踪范围
- finding(s) → 发现项
- recommendation → 建议
- task → 任务
- baseline generation → 基线生成
- claim ceiling → 声明上限
- B2B marketing owner → B2B 营销负责人
- business owner / growth owner → 业务负责人 / 增长负责人
- content operator → 内容运营人员

### Chinese-First Rule (zh-CN)
- Every business term, role name, workflow label, concept name, AND snake_case/kebab-case section label MUST appear Chinese-first with English in parentheses on first mention in each major section
- This applies even when listing multiple terms in one sentence:
  BAD:  "从 tracked scope 到 observation baseline，再到 finding/recommendation/task/review"
  GOOD: "从跟踪范围（tracked scope）到观测基线（observation baseline），再到发现项/建议/任务/评审（finding/recommendation/task/review）"
- Snake_case/kebab-case field labels used as section markers are READER-FACING, not machine anchors:
  BAD:  "- domain_map:" / "- service_candidates:" / "- data_sensitivity:"
  GOOD: "- 领域映射（domain_map）：" / "- 候选服务（service_candidates）：" / "- 数据敏感性（data_sensitivity）："
- Common ESP section labels that MUST be Chinese-first: data_sensitivity→数据敏感性, schema_draft→Schema草案, api_endpoint→API端点, handoff_package→交接包, dependency_graph→依赖图, risk_summary→风险摘要, feasibility_judgment→可实现性判断, implementation_entry→实现入口, contract_registry→契约注册表
- Dot-separated package/module identifiers (geo.audit.AuditRecord) are machine anchors (keep exact), but surrounding descriptions must be Chinese:
  BAD:  "geo.audit.AuditRecord — contract surface for audit trail"
  GOOD: "geo.audit.AuditRecord — 审计追踪的契约面"
- After first introduction in a section, use Chinese-only (no repeated English parentheticals):
  BAD:  "跟踪范围（tracked scope）…配置跟踪范围（tracked scope）…" (repeated)
  GOOD: "跟踪范围（tracked scope）…配置跟踪范围…" (Chinese-only after first use)
- This applies section-wide: each H2 section resets first-mention, but WITHIN a section, do NOT repeat the English paren

### Acceptance Criteria (Given/When/Then)
- Translate Given/When/Then prose into natural Chinese:
  BAD:  "Given tenant identity, member roles, and audit policy are available"
  GOOD: "给定租户身份、成员角色和审计策略已可用"
- Preserve technical object names inside GWT cells (TenantWorkspace, ActorRole, etc.)
- Field keys (given/when/then column headers) may stay or be translated — consistency matters more

### What NOT to do
- Do NOT output the English source heading as a standalone line before the Chinese translation
- Do NOT invent, create, or add any heading (H1-H6) that does not exist in the source. Every heading in your output MUST be a direct translation of a heading from the source segment — do not add headings for "better organization"
    - Do NOT output the EXACT same heading TWICE in the same segment — but distinct headings that are merely similar must each appear (e.g. "## 数据模型" and "## API 设计" are different and both must stay)
- Do NOT delete rows, renumber IDs, or change facts
- Do NOT add external validation, sign-off, budget approval, UAT, production readiness claims
- Do NOT leave bare English business terms OR snake_case labels in Chinese prose — always Chinese-first
- Do NOT leave entire English sentences (especially GWT cells or action descriptions) untranslated
- Do NOT add commentary, explanations, or meta-notes
- Do NOT wrap output in markdown code fences"""


_PLAN_PROMPT = """Below is a heading outline of the source document. Create a segmentation plan.

Split at natural H2 boundaries, targeting ~{target_lines} lines per segment.

Return JSON with this exact schema:
{{"total_segments": <N>, "segments": [{{"index":<int>,"heading":"<EXACT source heading>","start_line":<int>,"end_line":<int>}}], "terminology_notes":"<key terms>"}}

Rules:
- Copy headings EXACTLY from source. Do NOT translate or modify.
- start_line/end_line are 0-based line numbers. First segment starts at 0. Last ends at EOF.
- Cover ALL content — no gaps. Return ONLY JSON, no fences."""


_SEGMENT_PROMPT = """You are translating segment {index}/{total} of a document.

Document: {artifact_label}
Target locale: {target_locale}
Canonical: {canonical_name}

Segment heading: {heading}

{context_block}

{structure_notes}
Translate this segment into reader-facing {target_locale}. Preserve all immutable tokens (trace IDs, file paths, code identifiers, status enums). Return ONLY the translated markdown — no code fences, no commentary.

## Source Segment

{segment_text}"""


def _read_translation_config() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "generated-output-policy.json"
    try:
        policy = json.loads(config_path.read_text(encoding="utf-8"))
        return policy.get("reader_translation", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _get_client(api_base: str | None = None, api_key: str | None = None):
    import openai
    cfg = _read_translation_config()
    kwargs: dict = {}
    key = api_key or os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"), "") or cfg.get("api_key", "")
    if key and key != "__NOT_SET__":
        kwargs["api_key"] = key
    base = api_base or cfg.get("api_base_url") or os.environ.get("OPENAI_BASE_URL", "")
    if base:
        kwargs["base_url"] = base
    return openai.OpenAI(**kwargs)


def _call_llm(
    *,
    client,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 32768,
    timeout: int = 1800,
) -> _LLMResponse:
    cfg = _read_translation_config()
    max_retries = cfg.get("max_retries", 3)
    backoff = cfg.get("retry_backoff_seconds", [1, 2, 4])

    reasoning_effort = cfg.get("reasoning_effort", "")

    last_error = None
    for attempt in range(max_retries):
        try:
            extra_kwargs: dict = {}
            if reasoning_effort:
                extra_kwargs["reasoning_effort"] = reasoning_effort
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=timeout,
                max_tokens=max_tokens,
                **extra_kwargs,
            )
            content = response.choices[0].message.content
            if content is None or not content.strip():
                raise RuntimeError(f"LLM returned empty response (finish_reason={response.choices[0].finish_reason})")
            return _LLMResponse(
                content=content,
                finish_reason=response.choices[0].finish_reason or "unknown",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            )
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                import time
                delay = backoff[min(attempt, len(backoff) - 1)]
                time.sleep(delay)
                continue
    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_error}")


def _parse_segment_plan(raw_json: str) -> dict:
    """Parse the LLM's segmentation plan from JSON response."""
    text = raw_json.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    # Extract JSON object if wrapped in other text
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        text = m.group(0)
    # Common LLM JSON fixes
    text = re.sub(r',\s*}', '}', text)  # trailing comma before }
    text = re.sub(r',\s*]', ']', text)  # trailing comma before ]
    return json.loads(text)


def _is_esp_document(source_text: str) -> bool:
    """Detect engineering spec pack documents by scanning for ESP-specific patterns."""
    indicators = [
        r'\bengineering.spec.pack\b', r'\bESP\b',
        r'architecture.definition', r'domain.module.service.decomposition',
        r'\bcontract_registry\b', r'\binterface_contracts\b',
        r'\.aggregate\.', r'\.audit\.', r'\.identity\.',
    ]
    score = sum(1 for pat in indicators if re.search(pat, source_text, re.IGNORECASE))
    return score >= 3


def _build_context_block(translated_segments: list[dict], terminology_notes: str) -> str:
    if not translated_segments:
        return ""
    lines = [
        "## Context from Previous Segments",
        "",
        f"Terminology decisions: {terminology_notes}",
        "",
        "Already translated sections (use same terminology):",
    ]
    for seg in translated_segments:
        term_map = seg.get("term_map", "")
        term_str = f" — terms: {term_map}" if term_map else ""
        lines.append(f"- {seg['heading']}{term_str}")
    return "\n".join(lines)


def _build_heading_summary(source_text: str) -> str:
    """Build a compact heading outline for the segmentation planner."""
    lines = source_text.splitlines()
    headings = [(i + 1, l.strip()) for i, l in enumerate(lines) if l.strip().startswith("## ")]
    if not headings:
        return f"Document: {len(lines)} lines, no H2 headings found"
    parts = [f"Total: {len(lines)} lines, {len(headings)} H2 sections"]
    for ln, h in headings:
        parts.append(f"  L{ln}: {h}")
    return "\n".join(parts)


def _deterministic_segments(source_text: str, target_lines: int = 500) -> list[dict]:
    """Fallback: deterministic H2 segmentation when LLM plan fails."""
    lines = source_text.splitlines(keepends=True)
    total = len(lines)
    h2_positions = [(i, l.strip()) for i, l in enumerate(lines) if l.strip().startswith("## ")]
    if not h2_positions:
        return [{"index": 1, "heading": "(document)", "start_line": 0, "end_line": total}]
    segments: list[dict] = []
    current_start = 0
    current_size = 0
    for idx, (pos, _) in enumerate(h2_positions):
        next_pos = h2_positions[idx + 1][0] if idx + 1 < len(h2_positions) else total
        section_size = next_pos - pos
        if current_size > 0 and current_size + section_size > target_lines * 1.3:
            heading = next((h for p, h in h2_positions if p == current_start), "(preamble)")
            if heading == "(preamble)" and current_start > 0:
                heading = next((h for p, h in h2_positions if p >= current_start), "(document)")
            segments.append({"index": len(segments) + 1, "heading": heading,
                             "start_line": current_start, "end_line": pos})
            current_start = pos
            current_size = 0
        current_size += section_size
    if current_start < total:
        heading = next((h for p, h in h2_positions if p == current_start), None)
        if heading is None:
            heading = "(preamble)" if current_start == 0 else next((h for p, h in h2_positions if p >= current_start), "(document)")
        segments.append({"index": len(segments) + 1, "heading": heading, "start_line": current_start, "end_line": total})
    return segments


def _refine_segments(source_text: str, segments: list[dict], target_lines: int = 500) -> list[dict]:
    """Fill gaps, merge heading-only stubs, and split oversized segments.

    LLM plans can skip lines, duplicate heading boundaries, or produce overly
    large segments for dense sections.  Gap/tail filling ensures complete coverage;
    stub merging prevents duplicate H2s from segment-boundary overlap; sub-heading
    splitting keeps per-segment size under the translation budget.
    """
    lines = source_text.splitlines(keepends=True)
    total = len(lines)

    # Step 1: fill gaps and tail
    filled: list[dict] = []
    cursor = 0
    for raw in sorted(segments, key=lambda s: int(s.get("start_line", 0))):
        start_line = max(0, min(total, int(raw.get("start_line", cursor))))
        end_line = max(start_line, min(total, int(raw.get("end_line", total))))
        if start_line > cursor:
            heading = ""
            for idx in range(cursor, start_line):
                if lines[idx].strip().startswith("#"):
                    heading = lines[idx].strip()
                    break
            filled.append({"heading": heading or "(gap)", "start_line": cursor, "end_line": start_line})
        if end_line > cursor:
            heading = str(raw.get("heading") or "")
            if not heading:
                for idx in range(max(start_line, cursor), end_line):
                    if lines[idx].strip().startswith("#"):
                        heading = lines[idx].strip()
                        break
            filled.append({"heading": heading or "(document)", "start_line": max(start_line, cursor), "end_line": end_line})
            cursor = end_line
    if cursor < total:
        filled.append({"heading": "(tail)", "start_line": cursor, "end_line": total})

    # Step 2: merge heading-only stubs into the next segment when both share a heading.
    # The LLM planner sometimes emits a tiny segment (just the H2 + blank line) followed
    # by a full-content segment with the same heading.  Without merging, the heading
    # gets translated twice and the final document has duplicate H2s.
    deduped: list[dict] = []
    for i, seg in enumerate(filled):
        if not deduped:
            deduped.append(dict(seg))
            continue
        prev = deduped[-1]
        prev_size = prev["end_line"] - prev["start_line"]
        if prev_size <= 15 and prev.get("heading") == seg.get("heading"):
            prev["end_line"] = seg["end_line"]
        else:
            deduped.append(dict(seg))
    filled = deduped

    # Step 3: split oversized segments at the first available sub-heading level
    refined: list[dict] = []
    budget = max(80, int(target_lines * 1.3))
    for seg in filled:
        start = int(seg["start_line"])
        end = int(seg["end_line"])
        heading = str(seg.get("heading") or "")
        if end - start <= budget:
            refined.append({"heading": heading, "start_line": start, "end_line": end})
            continue
        split = False
        for level in range(3, 7):
            marker = "#" * level + " "
            positions = [i for i in range(start, end) if lines[i].startswith(marker)]
            if len(positions) >= 2 or (positions and positions[0] > start):
                prev = start
                for pos in positions:
                    if prev < pos:
                        refined.append({"heading": heading, "start_line": prev, "end_line": pos})
                    prev = pos
                if prev < end:
                    refined.append({"heading": heading, "start_line": prev, "end_line": end})
                split = True
                break
        if not split:
            # Last resort: fixed window
            window = max(40, target_lines)
            pos = start
            while pos < end:
                nxt = min(pos + window, end)
                refined.append({"heading": heading, "start_line": pos, "end_line": nxt})
                pos = nxt

    for index, seg in enumerate(refined, 1):
        seg["index"] = index
    return refined


def _extract_term_map(translated_text: str) -> str:
    pairs = re.findall(r'([一-鿿]{2,20})（([A-Za-z][A-Za-z\s_/-]{3,40})）', translated_text)
    if not pairs:
        return ""
    seen = set()
    items = []
    for zh, en in pairs:
        key = en.strip().lower()
        if key not in seen and len(key) > 3:
            seen.add(key)
            items.append(f"{zh}={en.strip()}")
            if len(items) >= 12:
                break
    return ", ".join(items)


def run_llm_translation(
    *,
    source_text: str,
    target_locale: str,
    artifact_label: str,
    canonical_name: str,
    model: str,
    api_base: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
    progress_file: Path | None = None,
) -> _LLMResponse:
    """LLM-controlled segmentation with deterministic fallback.

    1. Try LLM plan from heading summary (primary path)
    2. Fall back to deterministic H2 segmentation if LLM plan fails
    3. Translate each segment with context from prior segments
    """
    client = _get_client(api_base=api_base, api_key=api_key)
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    cfg = _read_translation_config()
    resolved_timeout = timeout or cfg.get("timeout_seconds", 1800)
    target_lines = cfg.get("segment_target_lines", 500)
    seg_max_tokens = cfg.get("max_tokens_per_segment", 32768)
    is_esp = _is_esp_document(source_text)

    # Phase 1: Segmentation plan — LLM primary, deterministic fallback
    plan_text = _PLAN_PROMPT.format(target_lines=target_lines)
    heading_summary = _build_heading_summary(source_text)
    plan_prompt = f"{plan_text}\n\n## Document Heading Summary\n\n{heading_summary}"

    terminology_notes = ""
    try:
        plan_response = _call_llm(
            client=client, system_prompt="You are a document structure analyst. Return only valid JSON.",
            user_prompt=plan_prompt, model=model, max_tokens=16384, timeout=resolved_timeout,
        )
        for k in total_usage:
            total_usage[k] += plan_response.usage.get(k, 0)
        plan = _parse_segment_plan(plan_response.content)
        segments = plan["segments"]
        terminology_notes = plan.get("terminology_notes", "")
        # Normalize: fix 0-based index, ensure coverage
        for i, seg in enumerate(segments):
            if seg.get("index", 1) < 1:
                seg["index"] = i + 1
        if segments and segments[0]["start_line"] != 0:
            segments[0]["start_line"] = 0
    except Exception:
        segments = _deterministic_segments(source_text, target_lines=target_lines)
    segments = _refine_segments(source_text, segments, target_lines=target_lines)

    # Phase 2: Translate each segment
    translated_segments: list[dict] = []
    all_translations: list[str] = []
    last_finish_reason = "stop"
    seg_started_at = __import__("time").time()

    if progress_file:
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress_file.write_text("", encoding="utf-8")  # truncate / create

    source_lines = source_text.splitlines(keepends=True)
    for seg in segments:
        seg_text = "".join(source_lines[seg["start_line"]:seg["end_line"]])
        context_block = _build_context_block(translated_segments, terminology_notes)

        seg_h2 = len([l for l in seg_text.splitlines() if l.strip().startswith("## ")])
        seg_h3 = len([l for l in seg_text.splitlines() if l.strip().startswith("### ")])
        seg_rows = len([l for l in seg_text.splitlines() if l.strip().startswith("|")])
        structure_notes_parts = ["## Structural Requirements (MUST follow)"]
        if seg_h2:
            structure_notes_parts.append(
                f"- This segment contains exactly {seg_h2} H2 (`## `) headings in the source. "
                f"Your output MUST contain exactly {seg_h2} H2 headings — no more, no fewer."
            )
        if seg_h3:
            structure_notes_parts.append(
                f"- This segment contains exactly {seg_h3} H3 (`### `) headings. "
                f"Preserve all {seg_h3}."
            )
        if seg_rows:
            structure_notes_parts.append(
                f"- This segment contains exactly {seg_rows} table rows (`|`). "
                f"Your output MUST contain exactly {seg_rows} table rows."
            )
        structure_notes_parts.append(
            "- IMPORTANT: Only translate headings that exist in the source segment. "
            "Do NOT invent, create, or add any new heading. "
            "Every heading in your output must be a translation of a heading from the source."
        )
        structure_notes_parts.append(
            "- After translating, mentally count: did you produce exactly the required number "
            "of H2 headings, H3 headings, and table rows? If not, fix before returning."
        )
        structure_notes = "\n".join(structure_notes_parts) + "\n\n"

        seg_prompt = _SEGMENT_PROMPT.format(
            index=seg["index"], total=len(segments),
            artifact_label=artifact_label, target_locale=target_locale,
            canonical_name=canonical_name, heading=seg["heading"],
            context_block=context_block, structure_notes=structure_notes,
            segment_text=seg_text,
        )

        system_prompt = _SYSTEM_PROMPT
        if is_esp:
            system_prompt += "\n\nThis is an Engineering Spec Pack. ALL snake_case/kebab-case field labels MUST be Chinese-first — no exceptions."

        seg_response = _call_llm(
            client=client, system_prompt=system_prompt, user_prompt=seg_prompt,
            model=model, max_tokens=seg_max_tokens, timeout=resolved_timeout,
        )
        for k in total_usage:
            total_usage[k] += seg_response.usage.get(k, 0)
        last_finish_reason = seg_response.finish_reason

        term_map = _extract_term_map(seg_response.content)
        all_translations.append(seg_response.content)
        translated_segments.append({"heading": seg["heading"], "index": seg["index"], "term_map": term_map})

        if progress_file:
            elapsed = int(__import__("time").time() - seg_started_at)
            with open(progress_file, "a", encoding="utf-8") as pf:
                pf.write(json.dumps({
                    "segment": seg["index"],
                    "total_segments": len(segments),
                    "heading": seg.get("heading", ""),
                    "tokens": seg_response.usage,
                    "elapsed_s": elapsed,
                    "status": "segment-done",
                }, ensure_ascii=False) + "\n")

    if progress_file:
        elapsed = int(__import__("time").time() - seg_started_at)
        with open(progress_file, "a", encoding="utf-8") as pf:
            pf.write(json.dumps({
                "status": "all-segments-done",
                "total_tokens": total_usage,
                "total_elapsed_s": elapsed,
            }, ensure_ascii=False) + "\n")

    return _LLMResponse(
        content="\n\n".join(all_translations),
        finish_reason=last_finish_reason,
        usage=total_usage,
    )


def strip_code_fences(text: str) -> str:
    text = text.strip()
    fence = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip() + "\n"
    return text + "\n"


def translate_reader_artifact(
    *,
    canonical_path: Path,
    target_locale: str,
    artifact_label: str,
    output_path: Path | None = None,
    model: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    progress_file: Path | None = None,
) -> TranslationResult:
    cfg = _read_translation_config()
    resolved_model = model or cfg.get("model", "deepseek-v4-flash")
    locale = resolve_output_locale(target_locale)
    if locale == "en":
        return TranslationResult(
            verdict="pass",
            canonical_path=canonical_path.resolve(),
            reader_path=canonical_path.resolve(),
            translated_path=None,
            locale=locale,
            artifact_label=artifact_label,
            detail="target-locale is en; reader artifact is canonical",
            integrity=None,
        )

    resolved_output = output_path or build_translated_reader_path(canonical_path, locale)
    source_text = canonical_path.read_text(encoding="utf-8")

    try:
        response = run_llm_translation(
            source_text=source_text,
            target_locale=locale,
            artifact_label=artifact_label,
            canonical_name=canonical_path.name,
            model=resolved_model,
            api_base=api_base,
            api_key=api_key,
            progress_file=progress_file,
        )
    except Exception as exc:
        return TranslationResult(
            verdict="translation-failed",
            canonical_path=canonical_path.resolve(),
            reader_path=resolved_output,
            translated_path=None,
            locale=locale,
            artifact_label=artifact_label,
            detail=f"LLM call failed: {exc}",
            integrity=None,
        )

    cleaned = strip_code_fences(response.content)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    package_reader_artifact(
        canonical_path=canonical_path,
        translated_text=cleaned,
        output_path=resolved_output,
        locale=locale,
        artifact_label=artifact_label,
    )

    # Verify integrity against the packaged output (includes preamble)
    packaged_text = resolved_output.read_text(encoding="utf-8")
    integrity = check_integrity(
        canonical_path=canonical_path,
        reader_path=resolved_output,
        locale=locale,
        reader_text=packaged_text,
    )
    structure = check_structure(canonical_text=source_text, reader_text=packaged_text)

    detail_parts = [f"translated via {resolved_model}"]
    detail_parts.append(f"tokens: in={response.usage['prompt_tokens']} out={response.usage['completion_tokens']}")
    if response.finish_reason == "length":
        detail_parts.append("WARNING: some segments truncated")
    detail_parts.append(f"integrity={integrity.verdict}")
    if structure.issues:
        detail_parts.append(f"structure: {'; '.join(structure.issues)}")
    else:
        detail_parts.append("structure: ok")

    # Verdict: only fail on truly broken output.
    # Minor structural drift (H2 ±2, table drift <30%) and 1 missing token
    # are informational for the human reviewer, not blockers.
    if integrity.verdict == "fail":
        verdict = "degrade"  # 2+ missing tokens — usable but needs attention
    elif structure.issues or integrity.verdict == "warn":
        verdict = "degrade"  # minor issues surfaced for reviewer
    else:
        verdict = "pass"

    return TranslationResult(
        verdict=verdict,
        canonical_path=canonical_path.resolve(),
        reader_path=resolved_output,
        translated_path=resolved_output,
        locale=locale,
        artifact_label=artifact_label,
        detail="; ".join(detail_parts),
        integrity=integrity,
    )


def package_reader_artifact(
    *,
    canonical_path: Path,
    translated_text: str,
    output_path: Path,
    locale: str,
    artifact_label: str,
) -> Path:
    preamble = render_reader_preamble(canonical_path.name, locale, artifact_label)
    lines = translated_text.splitlines()
    packaged: list[str] = []
    inserted = False
    for index, line in enumerate(lines):
        packaged.append(line)
        if index == 0 and line.startswith("#"):
            packaged.append("")
            packaged.append(preamble.rstrip())
            inserted = True
    if not inserted:
        packaged = [preamble.rstrip(), *packaged]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(packaged).rstrip() + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Produce a localized reader artifact via LLM-controlled translation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  emit_reader_translation.py --canonical prd.md --artifact-label "P1 PRD"
  emit_reader_translation.py --canonical prd.md --model deepseek-chat --api-base https://api.deepseek.com/v1""",
    )
    parser.add_argument("--canonical", required=True, type=Path, help="Canonical English source document")
    parser.add_argument("--target-locale", default="zh-CN", help="Target reader locale")
    parser.add_argument("--artifact-label", required=True, help="Human-readable artifact label")
    parser.add_argument("--output", type=Path, help="Output reader path (auto-generated if omitted)")
    cfg = _read_translation_config()
    parser.add_argument("--model", default=cfg.get("model") or os.environ.get("WFF_TRANSLATION_MODEL", "deepseek-chat"),
                        help="LLM model name (config: reader_translation.model, env: WFF_TRANSLATION_MODEL)")
    parser.add_argument("--api-base", default=cfg.get("api_base_url") or os.environ.get("OPENAI_BASE_URL"),
                        help="OpenAI-compatible API base URL (config: reader_translation.api_base_url, env: OPENAI_BASE_URL)")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"),
                        help="API key (env: OPENAI_API_KEY)")
    parser.add_argument("--integrity-json", type=Path, help="Write integrity report to JSON path")
    parser.add_argument("--progress-file", type=Path, help="Write segment-level progress as JSONL")
    parser.add_argument("--mock", action="store_true", help="Use mock translation for pipeline testing only")
    args = parser.parse_args(argv)

    if args.mock:
        locale = resolve_output_locale(args.target_locale)
        resolved_output = args.output or build_translated_reader_path(args.canonical.resolve(), locale)
        source = args.canonical.read_text(encoding="utf-8")
        mock_text = f"""# [MOCK] 本地化阅读版

> mock 翻译 — 移除 --mock 运行真实 LLM 翻译
> 源文件: {len(source.splitlines())} 行, {len(source)} 字符

设置环境变量后运行:
  export OPENAI_API_KEY=sk-...
  export OPENAI_BASE_URL=https://api.deepseek.com/v1
  python3 {Path(__file__).name} --canonical {args.canonical} --artifact-label "{args.artifact_label}"
"""
        package_reader_artifact(
            canonical_path=args.canonical.resolve(),
            translated_text=mock_text,
            output_path=resolved_output,
            locale=locale,
            artifact_label=args.artifact_label,
        )
        integrity = check_integrity(
            canonical_path=args.canonical.resolve(),
            reader_path=resolved_output,
            locale=locale,
        )
        print(json.dumps({
            "verdict": "mock",
            "canonical": str(args.canonical.resolve()),
            "reader": str(resolved_output),
            "locale": locale,
            "detail": "mock — set env vars and remove --mock for real LLM translation",
            "integrity_verdict": integrity.verdict,
            "missing_token_count": len(integrity.missing_tokens),
            "token_count": integrity.token_count,
            "source_lines": len(source.splitlines()),
        }, ensure_ascii=False, indent=2))
        if args.integrity_json:
            write_integrity_report(integrity, args.integrity_json)
        return 0 if integrity.verdict == "pass" else 1

    result = translate_reader_artifact(
        canonical_path=args.canonical.resolve(),
        target_locale=args.target_locale,
        artifact_label=args.artifact_label,
        output_path=args.output,
        model=args.model,
        api_base=args.api_base or None,
        api_key=args.api_key or None,
        progress_file=args.progress_file,
    )

    print(json.dumps({
        "verdict": result.verdict,
        "canonical": str(result.canonical_path),
        "reader": str(result.reader_path),
        "locale": result.locale,
        "detail": result.detail,
        "integrity_verdict": result.integrity.verdict if result.integrity else None,
        "missing_token_count": len(result.integrity.missing_tokens) if result.integrity else None,
    }, ensure_ascii=False, indent=2))

    if result.integrity and args.integrity_json:
        write_integrity_report(result.integrity, args.integrity_json)

    if result.verdict == "translation-failed":
        return 2
    if result.verdict == "degrade":
        return 1
    return 0 if result.verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
