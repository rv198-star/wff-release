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
import concurrent.futures
import hashlib
import json
import os
import re
import signal
import sys
import threading
import time
from contextlib import contextmanager
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
- File names and repository paths shown in the source material (for example, engineering-spec-pack.md)
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
- review-bound → 待审阅确认（机器状态枚举仍保留 review-bound）
- human reviewer → 审阅人（仅在明确区分人工与 AI/自动化时使用“人工审阅者”）
- downstream-start-safe → 可安全启动下游
- tracked scope → 跟踪范围
- finding(s) → 发现项
- recommendation → 建议
- task → 任务
- baseline generation → 基线生成
- claim ceiling → 声明上限
- primary decision owner → 核心决策负责人
- decision owner / commitment owner → 决策负责人 / 投入负责人
- supporting operator → 协作执行人员

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


_PLAN_PROMPT = """Below is a structural map of the source document. Create a semantic segmentation plan.

Use the listed semantic anchors to keep related tables, contracts, objects, and list groups together.
Target no more than {target_chars} source characters per segment. Prefer smaller coherent
segments over one oversized segment. Boundaries MUST use 0-based line positions shown in
the map and MUST NOT split a markdown table or fenced block.

Return JSON with this exact schema:
{{"total_segments": <N>, "segments": [{{"index":<int>,"heading":"<EXACT source heading>","start_line":<int>,"end_line":<int>}}], "terminology_notes":"<key terms>"}}

Rules:
- Copy headings EXACTLY from source. Do NOT translate or modify.
- start_line/end_line are 0-based line numbers. First segment starts at 0. Last ends at EOF.
- Cover ALL content in order — no gaps or overlaps. Return ONLY JSON, no fences."""


_REPLAN_PROMPT = """The segment from line {start_line} through {end_line} is too large.
Split only that range into smaller semantically coherent segments using the structural map.
Each segment must contain no more than {target_chars} source characters. Preserve related
tables, contracts, objects, and list groups. Boundaries MUST use 0-based line positions
shown in the map and MUST NOT split a markdown table or fenced block.

Return JSON with this exact schema:
{{"total_segments": <N>, "segments": [{{"index":<int>,"heading":"<EXACT source heading or semantic anchor>","start_line":<int>,"end_line":<int>}}], "terminology_notes":"<key terms>"}}

Do not use aliases such as start/end/label. The first segment starts at {start_line} and
the last ends at {end_line}. Cover the range exactly with no gaps or overlaps."""


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
    # Retry ownership stays in _call_llm so one configured deadline cannot be
    # multiplied by hidden SDK retries.
    kwargs["max_retries"] = 0
    return openai.OpenAI(**kwargs)


class _LLMDeadlineExceeded(TimeoutError):
    pass


@contextmanager
def _hard_deadline(seconds: float):
    """Bound a synchronous provider call in the translation subprocess."""
    if (
        seconds <= 0
        or not hasattr(signal, "setitimer")
        or threading.current_thread() is not threading.main_thread()
    ):
        yield
        return

    def _raise_timeout(_signum, _frame):
        raise _LLMDeadlineExceeded(f"LLM call exceeded {seconds:.1f}s deadline")

    previous = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _call_llm(
    *,
    client,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 32768,
    timeout: float = 1800,
) -> _LLMResponse:
    cfg = _read_translation_config()
    max_retries = cfg.get("max_retries", 3)
    backoff = cfg.get("retry_backoff_seconds", [1, 2, 4])

    reasoning_effort = cfg.get("reasoning_effort", "")

    last_error = None
    deadline = time.monotonic() + timeout
    for attempt in range(max_retries):
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _LLMDeadlineExceeded(
                    f"LLM call exceeded {timeout:.1f}s total deadline"
                )
            extra_kwargs: dict = {}
            if reasoning_effort:
                extra_kwargs["reasoning_effort"] = reasoning_effort
            with _hard_deadline(remaining):
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=remaining,
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
                delay = backoff[min(attempt, len(backoff) - 1)]
                if time.monotonic() + delay >= deadline:
                    break
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


def _build_shared_context_block(terminology_notes: str) -> str:
    """Build immutable document-level context shared by parallel workers."""
    notes = terminology_notes.strip() or "Use the terminology rules in the system prompt."
    return "\n".join(
        [
            "## Document Translation Context",
            "",
            f"Terminology decisions: {notes}",
            "",
            "Translate this segment independently while following the same document-level terminology.",
        ]
    )


def _build_segment_structure_notes(segment_text: str) -> str:
    h2_count = sum(1 for line in segment_text.splitlines() if line.strip().startswith("## "))
    h3_count = sum(1 for line in segment_text.splitlines() if line.strip().startswith("### "))
    table_rows = sum(1 for line in segment_text.splitlines() if line.strip().startswith("|"))
    parts = ["## Structural Requirements (MUST follow)"]
    if h2_count:
        parts.append(
            f"- This segment contains exactly {h2_count} H2 (`## `) headings in the source. "
            f"Your output MUST contain exactly {h2_count} H2 headings — no more, no fewer."
        )
    if h3_count:
        parts.append(
            f"- This segment contains exactly {h3_count} H3 (`### `) headings. "
            f"Preserve all {h3_count}."
        )
    if table_rows:
        parts.append(
            f"- This segment contains exactly {table_rows} table rows (`|`). "
            f"Your output MUST contain exactly {table_rows} table rows."
        )
    parts.extend(
        [
            "- IMPORTANT: Only translate headings that exist in the source segment. "
            "Do NOT invent, create, or add any new heading. Every heading in your output "
            "must be a translation of a heading from the source.",
            "- After translating, mentally count the required H2 headings, H3 headings, "
            "and table rows. Fix any mismatch before returning.",
        ]
    )
    return "\n".join(parts) + "\n\n"


def _translate_segment(
    *,
    client,
    segment: dict,
    segment_text: str,
    segment_hash: str,
    total_segments: int,
    context_block: str,
    artifact_label: str,
    target_locale: str,
    canonical_name: str,
    model: str,
    max_tokens: int,
    timeout: float,
    is_esp: bool,
) -> dict:
    prompt = _SEGMENT_PROMPT.format(
        index=segment["index"],
        total=total_segments,
        artifact_label=artifact_label,
        target_locale=target_locale,
        canonical_name=canonical_name,
        heading=segment["heading"],
        context_block=context_block,
        structure_notes=_build_segment_structure_notes(segment_text),
        segment_text=segment_text,
    )
    system_prompt = _SYSTEM_PROMPT
    if is_esp:
        system_prompt += (
            "\n\nThis is an Engineering Spec Pack. ALL snake_case/kebab-case field "
            "labels MUST be Chinese-first — no exceptions."
        )
    response = _call_llm(
        client=client,
        system_prompt=system_prompt,
        user_prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    term_map = _extract_term_map(response.content)
    return {
        "source_sha256": segment_hash,
        "content": response.content,
        "term_map": term_map,
        "usage": response.usage,
        "finish_reason": response.finish_reason,
        "mode": "translated",
    }


def _build_structural_summary(
    source_text: str, *, start_line: int = 0, end_line: int | None = None
) -> str:
    """Expose bounded semantic anchors without asking Workflow to choose boundaries."""
    lines = source_text.splitlines(keepends=True)
    end = len(lines) if end_line is None else min(len(lines), end_line)
    start = max(0, min(start_line, end))
    parts = [
        f"Range: [{start}, {end}) of {len(lines)} lines",
        f"Range characters: {sum(len(line) for line in lines[start:end])}",
        "Candidate semantic anchors (0-based line positions):",
    ]
    in_fence: str | None = _fence_state_before_line(lines, start)
    table_start: int | None = None
    for index in range(start, end):
        raw = lines[index]
        stripped = raw.strip()
        lstripped = raw.lstrip()
        if in_fence is not None:
            if lstripped.startswith(in_fence):
                parts.append(f"  L{index + 1}: fence_end {in_fence}")
                in_fence = None
            continue
        if lstripped.startswith("```") or lstripped.startswith("~~~"):
            in_fence = lstripped[:3]
            parts.append(f"  L{index}: fence_start {stripped[:100]}")
            continue

        is_table_row = lstripped.startswith("|")
        if is_table_row and table_start is None:
            table_start = index
        elif not is_table_row and table_start is not None:
            preview = lines[table_start].strip()[:140]
            parts.append(f"  L{table_start}: table [{table_start}, {index}) {preview}")
            table_start = None

        if re.match(r"^#{1,6}\s+\S", lstripped):
            parts.append(f"  L{index}: heading {stripped[:180]}")
            continue
        indent = len(raw) - len(lstripped)
        if indent <= 2 and re.match(
            r"^-\s+(?:`?[A-Za-z0-9_.-]+`?|contract_\d+|[\u4e00-\u9fff][^:：]{0,60})\s*[:：]",
            lstripped,
        ):
            parts.append(f"  L{index}: list_group {stripped[:180]}")
    if table_start is not None:
        preview = lines[table_start].strip()[:140]
        parts.append(f"  L{table_start}: table [{table_start}, {end}) {preview}")
    parts.append(f"  L{end}: range_end")
    return "\n".join(parts)


def _build_heading_summary(source_text: str) -> str:
    """Compatibility alias for callers that need the planner's structural map."""
    return _build_structural_summary(source_text)


def _refine_segments(source_text: str, segments: list[dict], target_lines: int = 500) -> list[dict]:
    """Normalize only explicit H2 boundaries; never invent fixed line windows."""
    lines = source_text.splitlines(keepends=True)
    filled = [dict(segment) for segment in sorted(
        segments, key=lambda item: int(item.get("start_line", 0))
    )]

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
        if (
            prev_size <= 15
            and prev.get("heading") == seg.get("heading")
            and int(prev["end_line"]) == int(seg["start_line"])
        ):
            prev["end_line"] = seg["end_line"]
        else:
            deduped.append(dict(seg))
    filled = deduped

    # H2 headings are explicit document-semantic boundaries. Smaller semantic
    # boundaries remain Agentic-owned and are handled by focused replanning.
    refined: list[dict] = []
    for seg in filled:
        start = int(seg["start_line"])
        end = int(seg["end_line"])
        heading = str(seg.get("heading") or "")
        h2_positions = [i for i in range(start, end) if lines[i].startswith("## ")]
        if len(h2_positions) >= 2 or (h2_positions and h2_positions[0] > start):
            previous = start
            for position in h2_positions:
                if previous < position:
                    refined.append(
                        {"heading": heading, "start_line": previous, "end_line": position}
                    )
                previous = position
            if previous < end:
                refined.append(
                    {"heading": lines[previous].strip(), "start_line": previous, "end_line": end}
                )
            continue
        refined.append({"heading": heading, "start_line": start, "end_line": end})

    for index, seg in enumerate(refined, 1):
        seg["index"] = index
    return refined


def _segment_source(source_lines: list[str], segment: dict) -> str:
    return "".join(source_lines[int(segment["start_line"]):int(segment["end_line"])])


def _boundary_is_safe(source_lines: list[str], boundary: int) -> bool:
    if boundary <= 0 or boundary >= len(source_lines):
        return True
    if _fence_state_before_line(source_lines, boundary) is not None:
        return False
    previous = source_lines[boundary - 1].lstrip().startswith("|")
    following = source_lines[boundary].lstrip().startswith("|")
    return not (previous and following)


def _semantic_boundary_lines(source_text: str) -> set[int]:
    lines = source_text.splitlines(keepends=True)
    boundaries = {0, len(lines)}
    in_fence: str | None = None
    table_start: int | None = None
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        lstripped = raw.lstrip()
        if in_fence is not None:
            if lstripped.startswith(in_fence):
                in_fence = None
                boundaries.add(index + 1)
            continue
        if lstripped.startswith("```") or lstripped.startswith("~~~"):
            in_fence = lstripped[:3]
            boundaries.add(index)
            continue
        is_table_row = lstripped.startswith("|")
        if is_table_row and table_start is None:
            table_start = index
            boundaries.add(index)
        elif not is_table_row and table_start is not None:
            boundaries.add(index)
            table_start = None
        if re.match(r"^#{1,6}\s+\S", lstripped):
            boundaries.add(index)
        indent = len(raw) - len(lstripped)
        if indent <= 2 and re.match(
            r"^-\s+(?:`?[A-Za-z0-9_.-]+`?|contract_\d+|[\u4e00-\u9fff][^:：]{0,60})\s*[:：]",
            lstripped,
        ):
            boundaries.add(index)
    return boundaries


def _validate_segment_plan(
    source_text: str,
    segments: list[dict],
    *,
    expected_start: int = 0,
    expected_end: int | None = None,
) -> list[dict]:
    source_lines = source_text.splitlines(keepends=True)
    semantic_boundaries = _semantic_boundary_lines(source_text)
    end = len(source_lines) if expected_end is None else expected_end
    normalized: list[dict] = []
    cursor = expected_start
    for index, raw in enumerate(segments, 1):
        start = int(raw.get("start_line", -1))
        stop = int(raw.get("end_line", -1))
        if start != cursor or stop <= start or stop > end:
            raise ValueError(
                f"invalid Agentic segment coverage at {index}: expected start {cursor}, "
                f"received [{start}, {stop})"
            )
        if not _boundary_is_safe(source_lines, start) or not _boundary_is_safe(source_lines, stop):
            raise ValueError(f"Agentic segment {index} splits a table or fenced block")
        if start not in semantic_boundaries or stop not in semantic_boundaries:
            raise ValueError(
                f"Agentic segment {index} uses a boundary absent from the structural map"
            )
        normalized.append(
            {
                "index": index,
                "heading": str(raw.get("heading") or "(document)"),
                "start_line": start,
                "end_line": stop,
            }
        )
        cursor = stop
    if cursor != end:
        raise ValueError(f"Agentic segment plan ends at {cursor}; expected {end}")
    return normalized


def _plan_hash(segments: list[dict], terminology_notes: str) -> str:
    payload = json.dumps(
        {"segments": segments, "terminology_notes": terminology_notes},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


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


def _fence_state_before_line(source_lines: list[str], start_line: int) -> str | None:
    """Return the open Markdown fence, if any, at a source line boundary."""
    active_fence: str | None = None
    for line in source_lines[:start_line]:
        stripped = line.lstrip()
        if active_fence is not None:
            if stripped.startswith(active_fence):
                active_fence = None
        elif stripped.startswith("```"):
            active_fence = "```"
        elif stripped.startswith("~~~"):
            active_fence = "~~~"
    return active_fence


def _has_translatable_content(
    segment_text: str, *, active_fence: str | None = None
) -> bool:
    """Return whether a segment has non-empty content outside fenced code blocks."""
    for line in segment_text.splitlines():
        stripped = line.lstrip()
        if active_fence is not None:
            if stripped.startswith(active_fence):
                active_fence = None
            continue
        if stripped.startswith("```"):
            active_fence = "```"
            continue
        if stripped.startswith("~~~"):
            active_fence = "~~~"
            continue
        if stripped.strip():
            if re.match(r"^#{1,6}\s+\S", stripped):
                continue
            return True
    return False


def _request_segment_plan(
    *,
    client,
    source_text: str,
    model: str,
    timeout: float,
    target_chars: int,
    start_line: int = 0,
    end_line: int | None = None,
) -> tuple[list[dict], str, dict[str, int]]:
    source_lines = source_text.splitlines(keepends=True)
    end = len(source_lines) if end_line is None else end_line
    if start_line == 0 and end == len(source_lines):
        instruction = _PLAN_PROMPT.format(target_chars=target_chars)
    else:
        instruction = _REPLAN_PROMPT.format(
            start_line=start_line,
            end_line=end,
            target_chars=target_chars,
        )
    structural_map = _build_structural_summary(
        source_text, start_line=start_line, end_line=end
    )
    base_prompt = f"{instruction}\n\n## Source Structural Map\n\n{structural_map}"
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    validation_error = ""
    for attempt in range(3):
        correction = ""
        if validation_error:
            correction = (
                "\n\n## Previous Plan Rejected\n\n"
                f"Validation error: {validation_error}\n"
                "Return a corrected full plan. Do not ask Workflow to fill, drop, or "
                "move any source line."
            )
        response = _call_llm(
            client=client,
            system_prompt="You are a document structure analyst. Return only valid JSON.",
            user_prompt=base_prompt + correction,
            model=model,
            max_tokens=16384,
            timeout=timeout,
        )
        for key in usage:
            usage[key] += response.usage.get(key, 0)
        try:
            plan = _parse_segment_plan(response.content)
            raw_segments = plan.get("segments")
            if not isinstance(raw_segments, list) or not raw_segments:
                raise ValueError("Agentic segmentation plan contains no segments")
            if start_line == 0 and end == len(source_lines):
                raw_segments = _refine_segments(source_text, raw_segments)
            segments = _validate_segment_plan(
                source_text,
                raw_segments,
                expected_start=start_line,
                expected_end=end,
            )
            return segments, str(plan.get("terminology_notes") or ""), usage
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            validation_error = str(exc)
            if attempt == 2:
                raise RuntimeError(
                    f"Agentic segmentation plan remained invalid: {validation_error}"
                ) from exc
    raise AssertionError("unreachable")


def _agentic_segments(
    *,
    client,
    source_text: str,
    model: str,
    timeout: float,
    target_chars: int,
) -> tuple[list[dict], str, dict[str, int]]:
    segments, terminology_notes, usage = _request_segment_plan(
        client=client,
        source_text=source_text,
        model=model,
        timeout=timeout,
        target_chars=target_chars,
    )
    source_lines = source_text.splitlines(keepends=True)
    for round_index in range(4):
        oversized = [
            segment
            for segment in segments
            if len(_segment_source(source_lines, segment)) > target_chars
        ]
        if not oversized:
            for index, segment in enumerate(segments, 1):
                segment["index"] = index
            return segments, terminology_notes, usage
        if round_index == 3:
            break
        replacements: dict[int, list[dict]] = {}
        for segment in oversized:
            replanned, focused_notes, focused_usage = _request_segment_plan(
                client=client,
                source_text=source_text,
                model=model,
                timeout=timeout,
                target_chars=target_chars,
                start_line=int(segment["start_line"]),
                end_line=int(segment["end_line"]),
            )
            if len(replanned) < 2:
                raise RuntimeError(
                    "Agentic replanning did not split an oversized semantic segment"
                )
            replacements[id(segment)] = replanned
            if focused_notes:
                terminology_notes = "; ".join(
                    part for part in (terminology_notes, focused_notes) if part
                )
            for key in usage:
                usage[key] += focused_usage.get(key, 0)
        segments = [
            child
            for segment in segments
            for child in replacements.get(id(segment), [segment])
        ]
        segments = _validate_segment_plan(source_text, segments)
    raise RuntimeError("Agentic segmentation remained oversized after three replans")


def _checkpoint_path(progress_file: Path | None) -> Path | None:
    if progress_file is None:
        return None
    return progress_file.with_name(f"{progress_file.name}.checkpoint.json")


def _load_translation_checkpoint(
    checkpoint_path: Path | None,
    *,
    source_hash: str,
    target_locale: str,
    model: str,
    target_chars: int,
) -> dict | None:
    if checkpoint_path is None or not checkpoint_path.is_file():
        return None
    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        payload.get("schema_version") != "wff.reader-segment-checkpoint.v1"
        or payload.get("source_sha256") != source_hash
        or payload.get("target_locale") != target_locale
        or payload.get("model") != model
        or payload.get("target_chars") != target_chars
        or not isinstance(payload.get("segments"), list)
        or not isinstance(payload.get("completed"), dict)
    ):
        return None
    expected_plan_hash = _plan_hash(
        payload["segments"], str(payload.get("terminology_notes") or "")
    )
    if payload.get("plan_sha256") != expected_plan_hash:
        return None
    return payload


def _new_translation_checkpoint(
    *,
    source_hash: str,
    target_locale: str,
    model: str,
    target_chars: int,
    segments: list[dict],
    terminology_notes: str,
    plan_usage: dict[str, int],
) -> dict:
    return {
        "schema_version": "wff.reader-segment-checkpoint.v1",
        "source_sha256": source_hash,
        "target_locale": target_locale,
        "model": model,
        "target_chars": target_chars,
        "plan_sha256": _plan_hash(segments, terminology_notes),
        "segments": segments,
        "terminology_notes": terminology_notes,
        "plan_usage": plan_usage,
        "completed": {},
    }


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
    """Translate an Agentic semantic plan with exact segment-level recovery."""
    client = _get_client(api_base=api_base, api_key=api_key)
    cfg = _read_translation_config()
    resolved_timeout = timeout or cfg.get("timeout_seconds", 1800)
    target_chars = int(cfg.get("segment_target_chars", 40000))
    seg_max_tokens = cfg.get("max_tokens_per_segment", 32768)
    is_esp = _is_esp_document(source_text)
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    checkpoint_path = _checkpoint_path(progress_file)
    checkpoint = _load_translation_checkpoint(
        checkpoint_path,
        source_hash=source_hash,
        target_locale=target_locale,
        model=model,
        target_chars=target_chars,
    )
    resumed = checkpoint is not None
    if checkpoint is None:
        segments, terminology_notes, plan_usage = _agentic_segments(
            client=client,
            source_text=source_text,
            model=model,
            timeout=resolved_timeout,
            target_chars=target_chars,
        )
        checkpoint = _new_translation_checkpoint(
            source_hash=source_hash,
            target_locale=target_locale,
            model=model,
            target_chars=target_chars,
            segments=segments,
            terminology_notes=terminology_notes,
            plan_usage=plan_usage,
        )
        if checkpoint_path is not None:
            _atomic_write_json(checkpoint_path, checkpoint)
    else:
        segments = _validate_segment_plan(source_text, checkpoint["segments"])
        terminology_notes = str(checkpoint.get("terminology_notes") or "")

    total_usage = {
        key: int(checkpoint.get("plan_usage", {}).get(key, 0))
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }

    # Phase 2: Translate incomplete segments with bounded concurrency. Translation
    # remains inside the detached reader lane; P1-P4 never waits for this work.
    seg_started_at = time.time()
    source_lines = source_text.splitlines(keepends=True)
    max_parallel_segments = max(1, int(cfg.get("max_parallel_segments", 4)))

    # Concurrent workers may finish out of order. Retain every independently
    # valid checkpoint entry rather than truncating recovery to a prefix.
    valid_completed: dict[str, dict] = {}
    for seg in segments:
        seg_text = _segment_source(source_lines, seg)
        segment_hash = hashlib.sha256(seg_text.encode("utf-8")).hexdigest()
        completed = checkpoint["completed"].get(str(seg["index"]))
        if (
            isinstance(completed, dict)
            and completed.get("source_sha256") == segment_hash
            and str(completed.get("content") or "")
        ):
            valid_completed[str(seg["index"])] = completed
    if valid_completed != checkpoint["completed"]:
        checkpoint["completed"] = valid_completed
        if checkpoint_path is not None:
            _atomic_write_json(checkpoint_path, checkpoint)

    if progress_file and not resumed:
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress_file.write_text("", encoding="utf-8")
    elif progress_file:
        with open(progress_file, "a", encoding="utf-8") as pf:
            pf.write(
                json.dumps(
                    {
                        "status": "resume",
                        "completed_segments": len(checkpoint["completed"]),
                        "plan_sha256": checkpoint["plan_sha256"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    records: dict[str, dict] = dict(checkpoint["completed"])
    pending: list[tuple[dict, str, str]] = []

    def record_completion(segment: dict, record: dict) -> None:
        key = str(segment["index"])
        records[key] = record
        checkpoint["completed"][key] = record
        if checkpoint_path is not None:
            _atomic_write_json(checkpoint_path, checkpoint)
        if progress_file:
            elapsed = int(time.time() - seg_started_at)
            with open(progress_file, "a", encoding="utf-8") as pf:
                pf.write(
                    json.dumps(
                        {
                            "segment": segment["index"],
                            "total_segments": len(segments),
                            "heading": segment.get("heading", ""),
                            "tokens": record.get("usage") or {},
                            "elapsed_s": elapsed,
                            "status": "segment-done",
                            "mode": record.get("mode", "translated"),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    for seg in segments:
        key = str(seg["index"])
        if key in records:
            continue
        seg_text = _segment_source(source_lines, seg)
        segment_hash = hashlib.sha256(seg_text.encode("utf-8")).hexdigest()
        if not _has_translatable_content(
            seg_text,
            active_fence=_fence_state_before_line(source_lines, seg["start_line"]),
        ):
            record_completion(
                seg,
                {
                    "source_sha256": segment_hash,
                    "content": seg_text,
                    "term_map": "",
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    "finish_reason": "stop",
                    "mode": "verbatim-protected-content",
                },
            )
            continue
        pending.append((seg, seg_text, segment_hash))

    shared_context = _build_shared_context_block(terminology_notes)
    worker_count = min(max_parallel_segments, len(pending)) if pending else 0
    first_error: Exception | None = None

    if worker_count <= 1:
        for seg, seg_text, segment_hash in pending:
            previous_segments = [
                {
                    "heading": previous["heading"],
                    "index": previous["index"],
                    "term_map": str(records[str(previous["index"])].get("term_map") or ""),
                }
                for previous in segments
                if previous["index"] < seg["index"] and str(previous["index"]) in records
            ]
            context_block = (
                _build_context_block(previous_segments, terminology_notes)
                or shared_context
            )
            record = _translate_segment(
                client=client,
                segment=seg,
                segment_text=seg_text,
                segment_hash=segment_hash,
                total_segments=len(segments),
                context_block=context_block,
                artifact_label=artifact_label,
                target_locale=target_locale,
                canonical_name=canonical_name,
                model=model,
                max_tokens=seg_max_tokens,
                timeout=resolved_timeout,
                is_esp=is_esp,
            )
            record_completion(seg, record)
    elif pending:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="wff-reader-translation",
        ) as executor:
            future_segments = {
                executor.submit(
                    _translate_segment,
                    client=client,
                    segment=seg,
                    segment_text=seg_text,
                    segment_hash=segment_hash,
                    total_segments=len(segments),
                    context_block=shared_context,
                    artifact_label=artifact_label,
                    target_locale=target_locale,
                    canonical_name=canonical_name,
                    model=model,
                    max_tokens=seg_max_tokens,
                    timeout=resolved_timeout,
                    is_esp=is_esp,
                ): seg
                for seg, seg_text, segment_hash in pending
            }
            for future in concurrent.futures.as_completed(future_segments):
                seg = future_segments[future]
                try:
                    record = future.result()
                except Exception as exc:  # retain successful peer checkpoints first
                    if first_error is None:
                        first_error = exc
                    continue
                record_completion(seg, record)

    if first_error is not None:
        raise first_error

    all_translations: list[str] = []
    last_finish_reason = "stop"
    for seg in segments:
        record = records.get(str(seg["index"]))
        if not isinstance(record, dict) or not str(record.get("content") or ""):
            raise RuntimeError(f"segment {seg['index']} completed without durable content")
        all_translations.append(str(record["content"]))
        usage = record.get("usage") or {}
        for key in total_usage:
            total_usage[key] += int(usage.get(key, 0))
        last_finish_reason = str(record.get("finish_reason") or "stop")

    if progress_file:
        elapsed = int(time.time() - seg_started_at)
        with open(progress_file, "a", encoding="utf-8") as pf:
            pf.write(
                json.dumps(
                    {
                        "status": "all-segments-done",
                        "parallel_workers": worker_count,
                        "total_tokens": total_usage,
                        "total_elapsed_s": elapsed,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

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
  export OPENAI_API_KEY=<your-api-key>
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
