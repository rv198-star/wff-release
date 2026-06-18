#!/usr/bin/env python3
"""
Shared Phase-1 source and domain extraction helpers.
"""

from __future__ import annotations

import re

from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases


REVIEW_BOUND_MISSING_SOURCE_ROLE = "review-bound missing source role"
REVIEW_BOUND_MISSING_SOURCE_STATUS_QUO = "review-bound missing source status quo"
REVIEW_BOUND_MISSING_SOURCE_CONSTRAINT = "review-bound missing source constraint"
REVIEW_BOUND_MISSING_SOURCE_DEFERRED_SCOPE = "review-bound missing source deferred scope"
REVIEW_BOUND_MISSING_SOURCE_OUT_OF_SCOPE = "review-bound missing source out-of-scope item"
REVIEW_BOUND_MISSING_SOURCE_FLOW = "review-bound missing source flow"
REVIEW_BOUND_MISSING_SOURCE_MODULE_CHAIN = "review-bound missing source module chain"
REVIEW_BOUND_MISSING_SOURCE_MODULE_PAYLOAD = "review-bound missing source module payload"
REVIEW_BOUND_MISSING_SOURCE_DETAIL = "review-bound missing source detail"


def clean_source_text_value(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return normalize_source_handoff_phrases(text.strip(" `"))


def list_items_from_block(block: str) -> list[str]:
    if not block:
        return []
    items: list[str] = []
    for line in block.splitlines()[1:]:
        bullet = re.match(r"^\s*-\s+`?([^`]+?)`?\s*$", line)
        if bullet:
            items.append(bullet.group(1).strip())
            continue
        numbered = re.match(r"^\s*\d+\.\s+(.+?)\s*$", line)
        if numbered:
            items.append(numbered.group(1).strip())
    return [item for item in items if item and "source section not found" not in item.lower()]

def find_markdown_block(text: str, heading_keywords: list[str]) -> str:
    for keyword in heading_keywords:
        match = re.search(
            rf"^#+\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        heading_line = match.group(0)
        heading_level = len(re.match(r"^#+", heading_line).group(0))
        tail = text[start:]
        next_heading = re.search(
            rf"^#{{1,{heading_level}}}\s+",
            tail[match.end() - start :],
            flags=re.MULTILINE,
        )
        end = (match.end() - start) + next_heading.start() if next_heading else len(tail)
        return tail[:end].strip()
    return ""

def find_named_h2_block(text: str, heading_keywords: list[str]) -> str:
    for keyword in heading_keywords:
        match = re.search(
            rf"^##\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            continue
        start = match.start()
        tail = text[start:]
        next_h2 = re.search(r"^##\s+", tail[1:], flags=re.MULTILINE)
        end = next_h2.start() + 1 if next_h2 else len(tail)
        return tail[:end].strip()
    return ""

SOURCE_PACKET_EVIDENCE_ALIASES: list[tuple[tuple[str, ...], list[str]]] = [
    (("2\\.1", "项目/产品背景", "第一部分", "原版"), ["Project Context"]),
    (("2\\.2", "业务机会描述", "3\\.2", "结构化问题清单", "3\\.3", "结构化机会清单"), ["Project Context", "Desired Outcome"]),
    (("2\\.3", "研究对象", "目标用户"), ["User, Buyer, Operator"]),
    (("2\\.4", "证据线索", "6\\.1", "验证对象", "6\\.2", "判定信号"), ["Desired Outcome", "Success Signals"]),
    (("3\\.1", "产品/业务目标", "目标方向"), ["Desired Outcome"]),
    (("3\\.4", "用户叙事", "主流程"), ["Key Workflows", "Scenarios"]),
    (("4\\.1", "关键约束", "4\\.2", "指标口径"), ["Constraints"]),
    (("4\\.3", "范围边界", "非目标", "P0", "P1", "P2"), ["Scope Boundary"]),
    (("第九部分", "unknown", "provisional"), ["Open Truth Gaps"]),
    (("第十部分", "provenance", "标记"), ["Truth-State Ledger"]),
    (("第十二部分", "结论", "验收"), ["Admission Decision", "Handoff Note For wff-req"]),
]

P1_SOURCE_INPUT_PACKET_PATTERN = re.compile(r"^#\s+P1 Source Input Packet\b", flags=re.IGNORECASE | re.MULTILINE)
P1_SOURCE_BRIEF_HEADING_PATTERN = re.compile(
    r"^##\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*P1 Source Brief[^\n]*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
P1_PACKET_LEVEL_SECTION_TITLES = (
    "Intake Metadata",
    "Raw User Intent",
    "Source Materials",
    "Project Context Candidates",
    "Product Truth Challenge Notes",
    "Challenge Axis Coverage",
    "Truth-State Ledger",
    "Open Truth Gaps",
    "Reviewer Concerns",
    "Admission Decision",
    "Recommended P1 Profile / Depth Notes",
    "Handoff Note For wff-req",
)
P1_PACKET_ADMISSION_STATES = (
    "not-admission-ready",
    "provisional-ready-for-P1",
    "ready-for-P1",
)
P1_PACKET_ADMISSION_FIELD_PATTERN = re.compile(
    r"\badmission_(?:state|status)\b\s*[:：]\s*`?([^`\n]+)`?",
    flags=re.IGNORECASE,
)

def source_packet_evidence_block(source_text: str, heading_pattern: str) -> str:
    """Map legacy P1 source evidence headings to source-input-packet sections.

    Stage evidence packs cite raw source sections for review. A source input
    packet uses a different section contract, so missing legacy headings should
    resolve to the closest packet fact/review section instead of emitting
    `(source section not found)` noise.
    """

    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return ""
    fact_text = source_fact_text(source_text)
    if not fact_text:
        return ""
    for triggers, packet_headings in SOURCE_PACKET_EVIDENCE_ALIASES:
        if not any(re.search(trigger, heading_pattern, flags=re.IGNORECASE) for trigger in triggers):
            continue
        for heading in packet_headings:
            block = find_markdown_block(fact_text, [heading])
            if block:
                return f"## P1 Source Brief Evidence: {heading}\n{normalize_source_handoff_phrases(demote_headings(block))}"
    lines = fact_text.splitlines()
    excerpt = normalize_source_handoff_phrases("\n".join(lines[: min(len(lines), 20)]).strip())
    return f"## P1 Source Brief Evidence: excerpt\n{demote_headings(excerpt)}"


def _normalized_heading_title(raw_heading: str) -> str:
    title = re.sub(r"^#+\s+", "", str(raw_heading or "")).strip()
    title = re.sub(r"^\d+(?:\.\d+)?\s+", "", title).strip()
    title = re.sub(r"\s+", " ", title).strip(" `")
    return title


def _is_packet_fact_surface_terminator(raw_heading: str) -> bool:
    title = _normalized_heading_title(raw_heading).casefold()
    return any(title == keyword.casefold() or title.startswith(f"{keyword.casefold()}:") for keyword in P1_PACKET_LEVEL_SECTION_TITLES)


def find_p1_source_brief_packet_block(source_text: str) -> str:
    """Return the packet-embedded P1 Source Brief fact surface.

    Req-Chat may embed a standalone source brief whose internal sections are
    still H2 headings. Generic markdown block extraction would stop at the
    first such H2, so packet parsing must end on packet process/admission
    sections instead.
    """

    match = P1_SOURCE_BRIEF_HEADING_PATTERN.search(source_text)
    if not match:
        return ""
    start = match.start()
    tail = source_text[start:]
    for heading in re.finditer(r"^##\s+[^\n]+$", tail[match.end() - start :], flags=re.MULTILINE):
        raw_heading = heading.group(0)
        if _is_packet_fact_surface_terminator(raw_heading):
            return tail[: match.end() - start + heading.start()].strip()
    return tail.strip()

def flatten_bullets(block: str, limit: int) -> list[str]:
    if not block:
        return []
    items: list[str] = []
    for line in block.splitlines()[1:]:
        bullet = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if bullet:
            value = bullet.group(1).strip().strip("`")
            if value and "source section not found" not in value.casefold():
                items.append(value)
        if len(items) >= limit:
            break
    if items:
        return items
    fallbacks: list[str] = []
    for line in block.splitlines()[1:]:
        value = line.strip().strip("`")
        if not value or value.startswith("#"):
            continue
        if "source section not found" in value.casefold():
            continue
        fallbacks.append(value)
        if len(fallbacks) >= limit:
            break
    return fallbacks

def source_fact_text(source_text: str) -> str:
    """Return the authoritative fact-bearing body for a P1 source input packet.

    `wff-req-chat` packets contain both product facts and review/control
    metadata. Phase-1 extraction should use the `P1 Source Brief` as the
    business fact surface; challenge axes and ledgers are constraints, not
    product nouns.
    """

    if not P1_SOURCE_INPUT_PACKET_PATTERN.search(source_text):
        return source_text
    block = find_p1_source_brief_packet_block(source_text)
    if block:
        return normalize_source_handoff_phrases(block)
    return ""

def _normalize_packet_admission_state(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" `。.;；,，")
    folded = text.casefold()
    for state in P1_PACKET_ADMISSION_STATES:
        if folded == state.casefold():
            return state
    for state in P1_PACKET_ADMISSION_STATES:
        if re.search(rf"(?<![-\w]){re.escape(state)}(?![-\w])", text, flags=re.IGNORECASE):
            return state
    return ""

def source_packet_admission_state(source_text: str) -> str:
    """Return a source-input packet's explicit admission state when present."""

    if not P1_SOURCE_INPUT_PACKET_PATTERN.search(source_text):
        return ""
    blocks = [
        find_markdown_block(source_text, ["Admission Decision"]),
        find_markdown_block(source_text, ["Intake Metadata"]),
    ]
    for block in blocks:
        if not block:
            continue
        for match in P1_PACKET_ADMISSION_FIELD_PATTERN.finditer(block):
            state = _normalize_packet_admission_state(match.group(1))
            if state:
                return state
        for raw_line in block.splitlines():
            bullet = re.match(r"^\s*-\s+`?([^`\n]+)`?\s*$", raw_line)
            if not bullet:
                continue
            state = _normalize_packet_admission_state(bullet.group(1))
            if state:
                return state
    return ""

HANDOFF_QUALIFIER_PATTERN = re.compile(
    r"\b(?:role[- ]owned\s+|owner[- ]owned\s+|responsibility[- ]owned\s+)?next\s+(?:action|step)\b|"
    r"下一步.*(?:责任|动作)|(?:责任|角色).*下一步",
    flags=re.IGNORECASE,
)

def is_handoff_qualifier_label(value: str) -> bool:
    """Return true when a source label describes handoff ownership, not a module.

    Source packets often say a manager needs to see the "role-owned next
    action". That phrase should shape state/role semantics inside a workflow;
    treating it as a standalone module creates synthetic pages, inputs, outputs,
    and acceptance rows.
    """

    text = re.sub(r"\s+", " ", str(value or "")).strip(" `。.;；")
    if not text or len(text) > 80:
        return False
    if not HANDOFF_QUALIFIER_PATTERN.search(text):
        return False
    lowered = text.casefold()
    if any(token in lowered for token in ("view", "dashboard", "screen", "page", "report", "queue", "task list")):
        return False
    if any(token in text for token in ("视图", "看板", "页面", "报表", "队列", "任务列表")):
        return False
    return True

def label_block_items(source_text: str, label_patterns: list[str], *, limit: int = 12) -> list[str]:
    """Extract bullets under a plain label such as `P0:` inside a section."""

    lines = source_text.splitlines()
    items: list[str] = []
    active = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            active = False
            continue
        is_label = any(re.match(rf"^{pattern}\s*[:：]\s*$", line, flags=re.IGNORECASE) for pattern in label_patterns)
        if is_label:
            active = True
            continue
        if active and re.match(r"^[A-Za-z0-9 /_-]{1,40}\s*[:：]\s*$", line):
            break
        if active:
            bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+?)\s*$", line)
            if not bullet:
                continue
            value = bullet.group(1).strip().strip("`")
            if value and "source section not found" not in value.casefold():
                items.append(value)
            if len(items) >= limit:
                break
    return items

def find_h2_block(text: str, heading_pattern: str) -> str:
    match = re.search(
        rf"^##\s+{heading_pattern}.*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return source_packet_evidence_block(text, heading_pattern)
    start = match.start()
    tail = text[start:]
    next_h2 = re.search(r"^##\s+", tail[1:], flags=re.MULTILINE)
    end = next_h2.start() + 1 if next_h2 else len(tail)
    return tail[:end].strip()

def demote_headings(text: str, levels: int = 1) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            size = len(line) - len(line.lstrip("#"))
            out.append(f"{'#' * min(size + levels, 6)}{line[size:]}")
        else:
            out.append(line)
    return "\n".join(out).strip()

def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered

def role_label(row: dict[str, str]) -> str:
    return str(
        row.get('Role')
        or row.get('role')
        or row.get('persona')
        or row.get('user')
        or row.get('target_user')
        or ''
    ).strip()

def _normalized_label_key(label: str) -> str:
    return re.sub(r'\s+', ' ', str(label or '').strip().strip('`')).casefold()

def preserved_display_label(label: str, fallback: str = "Item") -> str:
    cleaned = str(label or "").strip().strip("`")
    if not cleaned:
        return fallback
    token = slug_token(cleaned)
    if re.search(r"[^\x00-\x7F]", cleaned) and token == "item":
        return cleaned
    return title_case_token(token)

def _normalize_source_segment_candidate(value: str) -> str:
    cleaned = str(value or "").strip().strip("`")
    cleaned = re.sub(r"^\s*(?:主要用户|次要用户|评审用户)\s*[：:]\s*", "", cleaned).strip()
    if not cleaned:
        return ""
    sentence_match = re.match(r"^(.{1,32}?)(?:负责(?!人)|需要|使用|创建|评审|审核|查看|操作|管理|完成|提交).*$", cleaned)
    if sentence_match:
        cleaned = sentence_match.group(1).strip(" ，,：:")
    lowered = cleaned.casefold()
    excluded_prefixes = ("客群边界", "使用边界", "边界", "首发不做", "不做", "非目标")
    if any(lowered.startswith(prefix.casefold()) for prefix in excluded_prefixes):
        return ""
    if "不承诺" in cleaned or "不做" in cleaned:
        return ""
    return cleaned

def detect_source_segments(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    candidate_block = find_h2_block(fact_text, r"2\.3\s+研究对象/目标用户边界")
    candidates = [
        value for value in (_normalize_source_segment_candidate(item) for item in list_items_from_block(candidate_block)) if value
    ]
    if not candidates:
        table_rows = parse_markdown_table(
            find_markdown_block(
                fact_text, ["User, Buyer, Operator", "2. Target Users", "Target Users", "Target Roles", "目标用户", "用户与角色"]
            )
        )
        candidates = [
            _normalize_source_segment_candidate(_row_value(row, "Role", "role", "角色", "persona", "user", "target_user"))
            for row in table_rows
            if _normalize_source_segment_candidate(_row_value(row, "Role", "role", "角色", "persona", "user", "target_user"))
        ]
    if not candidates:
        for headers, table_rows in iter_markdown_tables(fact_text):
            if not _table_has_header(headers, "Role", "role", "角色", "persona", "user", "target_user"):
                continue
            candidates = [
                _normalize_source_segment_candidate(_row_value(row, "Role", "role", "角色", "persona", "user", "target_user"))
                for row in table_rows
                if _normalize_source_segment_candidate(_row_value(row, "Role", "role", "角色", "persona", "user", "target_user"))
            ]
            if candidates:
                break
    if not candidates:
        candidates = [
            _normalize_source_segment_candidate(str(row.get("Role", "")))
            for row in _light_structured_role_rows(fact_text)
            if _normalize_source_segment_candidate(str(row.get("Role", "")))
        ]
    if not candidates:
        target_users_block = find_markdown_block(fact_text, ["User, Buyer, Operator", "Target Users", "Target Roles", "目标用户", "用户与角色"])
        candidates = [
            value
            for value in (_normalize_source_segment_candidate(item) for item in list_items_from_block(target_users_block))
            if value
        ]
    return unique_preserve_order(candidates)

def extract_product_label(source_text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", source_text, flags=re.MULTILINE)
    if not match:
        return "Source-Derived"
    title = match.group(1).strip()
    title = re.sub(r"\s*(Product Requirements Document|产品需求文档|PRD)\b.*$", "", title, flags=re.IGNORECASE).strip(" -—")
    return title or "Source-Derived"

def extract_main_flow_block(source_text: str) -> str:
    fact_text = source_fact_text(source_text)
    for pattern in (r"主流程[:：].+", r"Main Flow[:：].+", r"Core Flow[:：].+"):
        match = re.search(rf"^##\s+{pattern}\s*$", fact_text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return find_h2_block(fact_text, re.escape(match.group(0).split("##", 1)[1].strip()))
    return find_h2_block(fact_text, r"5\.2\s+最小可用体验闭环")

def parse_markdown_table(block: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append({headers[idx]: cells[idx] for idx in range(len(headers))})
    return rows


def iter_markdown_tables(block: str) -> list[tuple[list[str], list[dict[str, str]]]]:
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    lines = block.splitlines()
    index = 0
    while index < len(lines) - 1:
        if "|" not in lines[index] or "|" not in lines[index + 1]:
            index += 1
            continue
        if not re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", lines[index + 1]):
            index += 1
            continue
        headers = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        rows: list[dict[str, str]] = []
        index += 2
        while index < len(lines) and "|" in lines[index]:
            if re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", lines[index]):
                index += 1
                continue
            cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            if len(cells) == len(headers):
                rows.append({headers[pos]: cells[pos] for pos in range(len(headers))})
            index += 1
        if rows:
            tables.append((headers, rows))
    return tables


def _normalized_header_key(value: str) -> str:
    text = str(value or "").strip().strip("`").casefold()
    return re.sub(r"[\s_`：:/／|()（）-]+", "", text)


def _row_value(row: dict[str, str], *aliases: str) -> str:
    normalized_aliases = {_normalized_header_key(alias) for alias in aliases if alias}
    for key, value in row.items():
        if _normalized_header_key(key) in normalized_aliases:
            return str(value or "").strip().strip("`")
    return ""


def _table_has_header(headers: list[str], *aliases: str) -> bool:
    normalized = {_normalized_header_key(header) for header in headers}
    return any(_normalized_header_key(alias) in normalized for alias in aliases)


def _markdown_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in str(line or "").strip().strip("|").split("|")]


def _is_markdown_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", str(line or "")))


def _row_has_deferred_priority(row: dict[str, str]) -> bool:
    priority = _row_value(row, "优先级", "Priority", "priority", "Phase", "phase", "阶段")
    if not priority:
        return False
    normalized = _normalized_header_key(priority)
    return normalized in {"later", "deferred", "future", "后置", "以后"}


def _strip_deferred_priority_table_rows(markdown: str) -> str:
    lines = str(markdown or "").splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if index + 1 >= len(lines) or "|" not in line or not _is_markdown_table_separator(lines[index + 1]):
            kept.append(line)
            index += 1
            continue
        headers = _markdown_table_cells(line)
        kept.extend([line, lines[index + 1]])
        index += 2
        while index < len(lines) and "|" in lines[index]:
            row_line = lines[index]
            if _is_markdown_table_separator(row_line):
                kept.append(row_line)
                index += 1
                continue
            cells = _markdown_table_cells(row_line)
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            row = {headers[pos]: cells[pos] for pos in range(min(len(headers), len(cells)))}
            if not _row_has_deferred_priority(row):
                kept.append(row_line)
            index += 1
    return "\n".join(kept)


def parse_markdown_table_padded(block: str) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 3:
        return []
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        if re.match(r"^\|\s*[-: ]+\|\s*$", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append(dict(zip(headers, cells)))
    return rows


def parse_markdown_table_normalized(block: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in block.splitlines() if line.strip()]
    for idx in range(len(lines) - 1):
        if "|" not in lines[idx] or "|" not in lines[idx + 1]:
            continue
        if not re.match(r"^\s*\|?[\-:\s|]+\|?\s*$", lines[idx + 1]):
            continue
        headers = [
            re.sub(r"[^a-z0-9]+", "_", cell.strip().lower()).strip("_")
            for cell in lines[idx].strip().strip("|").split("|")
        ]
        rows: list[dict[str, str]] = []
        for line in lines[idx + 2 :]:
            if "|" not in line:
                break
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != len(headers):
                continue
            rows.append({header: cell for header, cell in zip(headers, cells)})
        if rows:
            return rows
    return []

def slug_token(text: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return token or "item"

def title_case_token(text: str) -> str:
    return re.sub(r"[_\-]+", " ", text).strip().title() or "Item"

def extract_table_rows(source_text: str, heading_keywords: list[str]) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    for keyword in heading_keywords:
        block = find_markdown_block(fact_text, [keyword])
        rows = parse_markdown_table(block)
        if rows:
            return rows
    return []

def extract_target_user_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    candidate_block = find_h2_block(fact_text, r"2\.3\s+研究对象/目标用户边界")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in list_items_from_block(candidate_block):
        match = re.match(r"^\s*(主要用户|次要用户|评审用户)\s*[：:]\s*(.+?)\s*$", item)
        role_name = _normalize_source_segment_candidate(match.group(2)) if match else ""
        description = match.group(1) if match else ""
        if role_name and role_name not in seen:
            rows.append({"Role": role_name, "Description": description})
            seen.add(role_name)
    if rows:
        return rows
    rows = extract_table_rows(fact_text, ["User, Buyer, Operator", "2. Target Users", "Target Users", "Target Roles", "目标用户", "用户与角色"])
    if rows:
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            role = _row_value(row, "Role", "role", "角色", "persona", "user", "target_user")
            if role:
                normalized = dict(row)
                normalized["Role"] = role
                description = _row_value(row, "Description", "description", "核心需求", "职责", "Source-backed responsibility")
                if description and "Description" not in normalized:
                    normalized["Description"] = description
                boundary = _row_value(row, "Boundary", "boundary", "关键边界", "Product implication")
                if boundary and "Boundary" not in normalized:
                    normalized["Boundary"] = boundary
                normalized_rows.append(normalized)
        return normalized_rows or rows
    for headers, table_rows in iter_markdown_tables(fact_text):
        if not _table_has_header(headers, "Role", "role", "角色", "persona", "user", "target_user"):
            continue
        normalized_rows = []
        for row in table_rows:
            role = _row_value(row, "Role", "role", "角色", "persona", "user", "target_user")
            if not role:
                continue
            normalized_rows.append(
                {
                    "Role": role,
                    "Description": _row_value(
                        row,
                        "Description",
                        "description",
                        "核心需求",
                        "职责",
                        "Source-backed responsibility",
                    ),
                    "Boundary": _row_value(row, "Boundary", "boundary", "关键边界", "Product implication"),
                }
            )
        if normalized_rows:
            return normalized_rows
    light_structured_roles = _light_structured_role_rows(fact_text)
    if light_structured_roles:
        return light_structured_roles
    return [{"Role": value.strip("`"), "Description": ""} for value in detect_source_segments(fact_text)]

def detect_source_style(source_text: str) -> str:
    return "source_semantic_profile"

def _role_name_list(roles: list[dict[str, str]]) -> list[str]:
    return [role_label(row) for row in roles if role_label(row)]

def _find_role_by_hint(role_names: list[str], patterns: list[str], fallback_index: int) -> str:
    for role in role_names:
        lowered = role.casefold()
        if any(re.search(pattern, lowered) for pattern in patterns):
            return role
    return role_names[fallback_index] if role_names else "primary operator"


def _choose_primary_actor_from_context(role_names: list[object], *context_values: str, fallback: str = "") -> str:
    role_names = [
        role_label(role) if isinstance(role, dict) else str(role or "").strip()
        for role in role_names
        if (role_label(role) if isinstance(role, dict) else str(role or "").strip())
    ]
    if not role_names:
        return fallback or "primary operator"
    weights = [10, 6, 4, 3, 2]
    scores: dict[str, int] = {role: 0 for role in role_names}
    for index, value in enumerate(context_values):
        text = clean_source_text_value(value).casefold()
        if not text:
            continue
        weight = weights[index] if index < len(weights) else 1
        for role in role_names:
            candidates = unique_preserve_order(
                [clean_source_text_value(role)] + _module_keyword_tokens(role)
            )
            for candidate in candidates:
                candidate_key = candidate.casefold()
                if candidate_key and candidate_key in text:
                    scores[role] += weight
    best_role = max(role_names, key=lambda role: scores.get(role, 0))
    return best_role if scores.get(best_role, 0) > 0 else fallback or role_names[0]


def _clean_sentence_fragment(value: object, *, fallback: str = "") -> str:
    text = clean_source_text_value(value)
    text = re.sub(r"^[A-Za-z0-9 _/-]{1,40}\s*[:：]\s*", "", text).strip()
    return text or fallback


def _source_steps_from_text(value: object, *, limit: int = 5) -> list[str]:
    text = _clean_sentence_fragment(value)
    if not text:
        return []
    parts = [
        _clean_sentence_fragment(part)
        for part in re.split(r"\s*(?:[；;]|->|→)\s*", text)
        if _clean_sentence_fragment(part)
    ]
    if len(parts) <= 1:
        parts = [
            _clean_sentence_fragment(part)
            for part in re.split(r"(?<=[。.!?！？])\s*", text)
            if _clean_sentence_fragment(part)
        ]
    return unique_preserve_order(parts)[:limit]


def _split_source_concepts(value: object, *, limit: int = 4) -> list[str]:
    text = _clean_sentence_fragment(value)
    if not text:
        return []
    parts = [
        _clean_sentence_fragment(part)
        for part in re.split(r"\s*(?:,|，|/|、|;|；|\+|->|→)\s*", text)
        if _clean_sentence_fragment(part)
    ]
    return unique_preserve_order(parts)[:limit]

LIGHT_STRUCTURED_FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "role": (
        "role",
        "roles",
        "target user",
        "target users",
        "user",
        "users",
        "persona",
        "personas",
        "operator",
        "operators",
        "buyer",
        "buyers",
        "review owner",
        "decision owner",
        "owner",
        "owner role",
        "角色",
        "用户",
        "目标用户",
        "使用者",
        "操作者",
        "负责人",
        "评审人",
        "决策人",
    ),
    "module": (
        "module",
        "modules",
        "capability",
        "capabilities",
        "feature",
        "features",
        "模块",
        "能力",
        "功能",
    ),
    "object": (
        "object",
        "objects",
        "business object",
        "business objects",
        "core object",
        "core objects",
        "data object",
        "data objects",
        "entity",
        "entities",
        "对象",
        "业务对象",
        "核心对象",
        "数据对象",
        "实体",
    ),
    "workflow": (
        "workflow",
        "workflows",
        "flow",
        "flows",
        "key workflow",
        "key workflows",
        "key workflows / scenarios",
        "scenario",
        "scenarios",
        "main flow",
        "工作流",
        "流程",
        "业务流程",
        "主流程",
        "场景",
    ),
    "constraint": (
        "constraint",
        "constraints",
        "boundary",
        "boundaries",
        "nfr",
        "nfrs",
        "non-functional requirement",
        "non-functional requirements",
        "约束",
        "边界",
        "非功能需求",
    ),
}


def _normalized_light_structured_label(value: object) -> str:
    text = clean_source_text_value(value).casefold()
    text = re.sub(r"[\*_`]+", "", text)
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text


def light_structured_fact_items(fact_text: str, group: str, *, limit: int = 12) -> list[str]:
    aliases = {
        _normalized_light_structured_label(alias)
        for alias in LIGHT_STRUCTURED_FACT_ALIASES.get(group, ())
    }
    items: list[str] = []
    for raw in fact_text.splitlines():
        match = re.match(r"^\s*[-*]\s+`?([^`：:]{1,64})`?\s*[:：]\s*(.+?)\s*$", raw)
        if not match:
            continue
        label = _normalized_light_structured_label(match.group(1))
        if label not in aliases:
            continue
        value = clean_source_text_value(match.group(2))
        if value and "source section not found" not in value.casefold():
            items.append(value)
        if len(items) >= limit:
            break
    return unique_preserve_order(items)


def _split_light_structured_name_description(value: object) -> tuple[str, str]:
    text = clean_source_text_value(value)
    if not text:
        return "", ""
    for pattern in (r"\s+[–—-]\s+", r"\s*[：:]\s+"):
        parts = re.split(pattern, text, maxsplit=1)
        if len(parts) != 2:
            continue
        name = _clean_sentence_fragment(parts[0])
        description = _clean_sentence_fragment(parts[1])
        if name and len(name) <= 80 and description:
            return name, description
    return text, ""


def _light_structured_role_rows(fact_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in light_structured_fact_items(fact_text, "role", limit=12):
        role, description = _split_light_structured_name_description(item)
        role = _clean_sentence_fragment(role).strip("`")
        description = _clean_sentence_fragment(description)
        if not role:
            continue
        key = _normalized_label_key(role)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"Role": role, "Description": description})
    return rows


def _light_structured_object_names(fact_text: str) -> list[str]:
    object_names: list[str] = []
    for item in light_structured_fact_items(fact_text, "object", limit=16):
        object_names.extend(_split_source_concepts(item, limit=16))
    return unique_preserve_order(object_names)


def _light_structured_flow_rows(fact_text: str) -> list[dict[str, object]]:
    flows: list[dict[str, object]] = []
    for item in light_structured_fact_items(fact_text, "workflow", limit=8):
        name, step_text = _split_light_structured_name_description(item)
        if step_text:
            steps = _source_steps_from_text(step_text, limit=8)
            flow_name = name or "Primary Flow"
        else:
            steps = _source_steps_from_text(item, limit=8)
            flow_name = "Primary Flow"
        if not steps:
            continue
        flows.append({"name": flow_name, "steps": steps})
    return flows


def _plain_workflow_bullet_flow_rows(fact_text: str) -> list[dict[str, object]]:
    flow_block = find_markdown_block(
        fact_text,
        ["6. Key Business Flows", "Key Business Flows", "Key Workflows", "Scenarios", "主流程"],
    )
    bullet_steps = flatten_bullets(flow_block, 8)
    if not bullet_steps:
        return []
    return [{"name": "Primary Flow", "steps": bullet_steps}]


SOURCE_OBJECT_TOKEN_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z0-9]*(?:Record|Plan|Feedback|Profile|Task|Case|State|Decision|Evidence|Result|Note|Item|Scope|Slot|Summary|Report)\b"
)


def _source_object_names_from_fact_text(fact_text: str) -> list[str]:
    first_wave_fact_text = _strip_deferred_priority_table_rows(fact_text)
    object_names = _light_structured_object_names(first_wave_fact_text)
    object_names.extend(SOURCE_OBJECT_TOKEN_PATTERN.findall(first_wave_fact_text))
    return unique_preserve_order(object_names)


def _light_structured_module_rows(
    fact_text: str,
    roles: list[dict[str, str]],
    *,
    include_plain_workflow_inference: bool = True,
) -> list[dict[str, str]]:
    module_items = light_structured_fact_items(fact_text, "module", limit=8)
    flow_rows = _light_structured_flow_rows(fact_text)
    if include_plain_workflow_inference and not flow_rows:
        flow_rows = _plain_workflow_bullet_flow_rows(fact_text)
    object_names = _source_object_names_from_fact_text(fact_text)
    if not module_items and flow_rows:
        if object_names:
            if len(object_names) >= 2:
                module_items = [f"{object_names[0]} / {object_names[1]} Review Loop"]
            else:
                module_items = [f"{object_names[0]} Workflow"]
        else:
            first_steps = [str(step).strip() for step in flow_rows[0].get("steps", []) if str(step).strip()]
            if first_steps:
                module_items = [f"{first_steps[0]} -> {first_steps[-1]}"]
    constraints = light_structured_fact_items(fact_text, "constraint", limit=8)
    rows: list[dict[str, str]] = []
    for item in module_items:
        module_name, description = _split_light_structured_name_description(item)
        if not module_name:
            continue
        contract = infer_fallback_module_contract(fact_text, module_name, roles)
        flow_steps = [
            str(step).strip()
            for flow in flow_rows
            for step in flow.get("steps", [])
            if str(step).strip()
        ]
        rows.append(
            contract
            | {
                "module": module_name,
                "primary_actor": _choose_primary_actor_from_context(
                    roles,
                    module_name,
                    description,
                    " ".join(flow_steps),
                    fallback=str(contract.get("primary_actor") or ""),
                ),
                "core_objects": ", ".join(object_names[:4]) or str(contract.get("core_objects") or ""),
                "responsibility": description or str(contract.get("responsibility") or module_name),
                "input": flow_steps[0] if flow_steps else str(contract.get("input") or ""),
                "output": flow_steps[-1] if flow_steps else str(contract.get("output") or ""),
                "architectural note": (
                    constraints[0]
                    if constraints
                    else "preserve source evidence from light-structured Req-Chat facts"
                ),
            }
        )
    return rows


def _module_keyword_tokens(module_name: str) -> list[str]:
    text = clean_source_text_value(module_name)
    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    tokens = ascii_tokens + cjk_chunks
    stopwords = {
        "and",
        "the",
        "with",
        "module",
        "workflow",
        "service",
        "business",
        "record",
        "source",
        "defined",
        "primary",
        "核心",
        "业务",
        "流程",
        "模块",
        "记录",
    }
    return [token for token in tokens if token.casefold() not in stopwords][:6]


def _looks_like_object_candidate(value: str) -> bool:
    text = clean_source_text_value(value)
    if not text or len(text) > 72:
        return False
    lowered = text.casefold()
    if any(
        token in lowered
        for token in (
            "目标",
            "goal",
            "product",
            "产品代号",
            "用户",
            "负责人",
            "operator",
            "manager",
            "场景",
            "建立",
            "帮助",
            "可观测",
            "可解释",
            "可执行",
            "可复盘",
        )
    ):
        return False
    if re.search(r"[。！？.!?]", text):
        return False
    return bool(re.search(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text))


def _object_candidates_from_source_lines(lines: list[str], *, limit: int = 4) -> list[str]:
    objectish_terms: list[str] = []
    for line in lines:
        objectish_terms.extend(
            item for item in _split_source_concepts(line, limit=4) if _looks_like_object_candidate(item)
        )
    return unique_preserve_order(objectish_terms)[:limit]


def _is_generic_projected_object(value: str) -> bool:
    return bool(
        re.search(
            r"primarybusinessflow|sourcedefinedworkflow|sourcedefinedcapability|businessflowrecord",
            re.sub(r"[^a-z0-9]+", "", str(value).casefold()),
        )
    )


def _object_name_from_capability(value: str) -> str:
    text = clean_source_text_value(value)
    text = re.sub(r"\b(?:管理|生成与查询|列表与详情|动作链|结论记录|基础模型)\b", "", text)
    text = re.sub(r"\b(?:create|update|list|detail|query|manage|record|review)\b", "", text, flags=re.IGNORECASE)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    if tokens:
        if len(tokens) == 1:
            base = title_case_token(tokens[0])
        else:
            base = "".join(title_case_token(token).replace(" ", "") for token in tokens[:3])
        if not re.search(r"(record|run|task|scope|slot|review|summary|profile|state)$", base, flags=re.IGNORECASE):
            if re.search(r"scope", base, flags=re.IGNORECASE):
                base += "Scope"
            elif re.search(r"baseline", base, flags=re.IGNORECASE):
                base += "Run"
            elif re.search(r"task|recommendation", base, flags=re.IGNORECASE):
                base += "Task"
            else:
                base += "Record"
        return base
    cjk = re.sub(r"[^\u4e00-\u9fff]+", "", text)
    if not cjk:
        return ""
    if not re.search(r"(记录|对象|任务|状态|档案|单|表|摘要)$", cjk):
        cjk = f"{cjk[:10]}记录"
    return cjk[:14]


def _fallback_object_names_from_source(source_text: str, *, limit: int = 6) -> list[str]:
    values: list[str] = []
    p0_items = (
        extract_priority_bucket(source_text, "P0（MVP 必须有）")
        or flatten_bullets(find_markdown_block(source_text, ["P0（MVP 必须有）", "P0", "MVP"]), 10)
        or label_block_items(source_text, [r"P0"], limit=10)
    )
    for item in p0_items:
        if re.search(r"tenant\s*/\s*actor\s*/\s*audit|基础模型|foundation|auth|权限|审计底座", item, flags=re.IGNORECASE):
            continue
        candidate = _object_name_from_capability(item)
        if candidate and _looks_like_object_candidate(candidate):
            values.append(candidate)
    if not values:
        for flow in extract_flow_rows(source_text):
            for step in flow.get("steps", []):
                candidate = _object_name_from_capability(str(step))
                if candidate and _looks_like_object_candidate(candidate):
                    values.append(candidate)
    return unique_preserve_order(values)[:limit]


def _best_matching_source_lines(source_text: str, module_name: str, *, limit: int = 4) -> list[str]:
    fact_text = source_fact_text(source_text)
    tokens = _module_keyword_tokens(module_name)
    lines: list[tuple[int, int, str]] = []
    for index, raw in enumerate(fact_text.splitlines()):
        line = raw.strip()
        if not line or line.startswith("#") or re.match(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$", line):
            continue
        cleaned = _clean_sentence_fragment(re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line).strip("| "))
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        score = sum(1 for token in tokens if token.casefold() in lowered)
        if score <= 0:
            continue
        lines.append((score, -index, cleaned))
    return [line for _, _, line in sorted(lines, reverse=True)[:limit]]


def _source_table_cells(source_text: str, headings: list[str], columns: list[str], *, limit: int = 6) -> list[str]:
    rows = extract_table_rows(source_text, headings)
    values: list[str] = []
    for row in rows:
        for column in columns:
            value = row.get(column) or row.get(column.lower()) or row.get(column.replace(" ", "_").lower())
            if value:
                values.extend(_split_source_concepts(value, limit=3) or [_clean_sentence_fragment(value)])
        if len(values) >= limit:
            break
    return unique_preserve_order([value for value in values if value])[:limit]


def _semantic_table_rows(source_text: str, required_headers: list[str]) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    matches: list[dict[str, str]] = []
    for headers, rows in iter_markdown_tables(fact_text):
        if all(_table_has_header(headers, header) for header in required_headers):
            matches.extend(rows)
    return matches


def _source_object_names(source_text: str, *, limit: int = 8) -> list[str]:
    rows = extract_table_rows(
        source_text,
        ["5. Core Business Objects", "Core Business Objects", "核心业务对象", "Core Objects", "数据对象", "Knowledge Base / Memory"],
    )
    if not rows:
        rows = _semantic_table_rows(source_text, ["数据对象"])
    values: list[str] = []
    for row in rows:
        object_name = (
            _row_value(row, "Object", "object", "Entity", "entity", "Name", "name", "core_object", "数据对象", "对象")
        )
        if object_name:
            values.extend(_split_source_concepts(object_name, limit=3) or [_clean_sentence_fragment(object_name)])
        if len(values) >= limit:
            break
    values.extend(_source_object_names_from_fact_text(source_text))
    return unique_preserve_order([value for value in values if value])[:limit]


def build_source_semantic_profile(
    source_text: str,
    *,
    module_name: str = "",
    roles: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Project concrete semantic hints from the source, without case branches."""

    fact_text = source_fact_text(source_text)
    role_names = _role_name_list(roles or extract_target_user_rows(fact_text))
    module_lines = _best_matching_source_lines(fact_text, module_name)
    source_flows = extract_flow_rows(fact_text)
    flow_steps = [
        str(step).strip()
        for flow in source_flows
        for step in flow.get("steps", [])
        if str(step).strip()
    ]
    module_tokens = _module_keyword_tokens(module_name)
    matching_flow_steps = [
        step
        for step in flow_steps
        if any(token.casefold() in step.casefold() for token in module_tokens)
    ][:4]
    generic_module_hint = bool(
        re.fullmatch(
            r"(?:primary business flow|source-defined workflow|source-defined capability|business flow)",
            clean_source_text_value(module_name),
            flags=re.IGNORECASE,
        )
        or is_generic_flow_container_title(module_name)
        or re.search(r"完成一次|闭环|complete.+loop", clean_source_text_value(module_name), flags=re.IGNORECASE)
    )
    module_object = "" if generic_module_hint else _object_name_from_capability(module_name)
    source_objects = _source_object_names(fact_text, limit=8)
    objects = [
        module_object
    ] if module_object and _looks_like_object_candidate(module_object) and not _is_generic_projected_object(module_object) else []
    objects = unique_preserve_order(objects + source_objects)
    module_object_rows = extract_table_rows(
        fact_text,
        ["4. Module Responsibility Matrix", "Module Responsibility Matrix", "模块与实体清单"],
    )
    for row in module_object_rows:
        module_value = str(row.get("module") or row.get("Module") or row.get("module_name") or "").strip()
        if module_name and module_value and _normalized_label_key(module_value) != _normalized_label_key(module_name):
            continue
        row_objects = row.get("core_objects") or row.get("Core Objects") or row.get("objects") or row.get("Objects") or ""
        if row_objects:
            objects = unique_preserve_order(_split_source_concepts(row_objects, limit=6) + objects + source_objects)[:8]
            break
    objects = [item for item in objects if not _is_generic_projected_object(item)]
    if not objects:
        objects = _fallback_object_names_from_source(fact_text, limit=6)
    else:
        objects = unique_preserve_order(
            objects + _object_candidates_from_source_lines(module_lines + matching_flow_steps, limit=3)
        )[:8]
    if not objects:
        objects = _object_candidates_from_source_lines(module_lines + matching_flow_steps, limit=4)
    constraints = extract_non_functional_requirements(fact_text) or extract_architectural_constraints(fact_text)
    outcomes = extract_business_objectives(fact_text)
    profile_name = _clean_sentence_fragment(module_name, fallback="source-defined capability")
    source_evidence = unique_preserve_order(module_lines + matching_flow_steps + outcomes[:2] + constraints[:2])
    primary_actor = _choose_primary_actor_from_context(
        role_names,
        module_name,
        " ".join(module_lines),
        " ".join(matching_flow_steps),
        fallback=role_names[0] if role_names else "primary operator",
    )
    for role in role_names:
        role_key = role.casefold()
        if primary_actor and primary_actor != (role_names[0] if role_names else ""):
            break
        if any(token.casefold() in " ".join(module_lines + matching_flow_steps).casefold() for token in _module_keyword_tokens(role)):
            primary_actor = role
            break
        if any(token in role_key for token in ("owner", "lead", "manager", "负责人", "主管", "经理", "owner")):
            primary_actor = role
            break
    return {
        "profile_id": "source-semantic-profile.v1",
        "domain_profile": "source-grounded-operating-loop",
        "module_name": profile_name,
        "primary_actor": primary_actor,
        "role_names": role_names,
        "core_objects": objects[:4] or [preserved_display_label(profile_name, fallback="Business Object")],
        "flow_steps": matching_flow_steps or flow_steps[:4],
        "source_evidence": source_evidence[:8],
        "constraints": constraints[:4],
        "outcomes": outcomes[:4],
        "claim_ceiling": "source-grounded semantic projection only; not external validation",
    }


def infer_agentic_module_contract(
    source_text: str,
    business_name: str,
    roles: list[dict[str, str]],
) -> dict[str, str]:
    profile = build_source_semantic_profile(source_text, module_name=business_name, roles=roles)
    module = str(profile.get("module_name") or business_name or "source-defined capability")
    primary_actor = str(profile.get("primary_actor") or "primary operator")
    core_objects = [str(item).strip() for item in profile.get("core_objects", []) if str(item).strip()]
    flow_steps = [str(item).strip() for item in profile.get("flow_steps", []) if str(item).strip()]
    source_evidence = [str(item).strip() for item in profile.get("source_evidence", []) if str(item).strip()]
    constraints = [str(item).strip() for item in profile.get("constraints", []) if str(item).strip()]
    first_step = flow_steps[0] if flow_steps else f"start {module}"
    last_step = flow_steps[-1] if flow_steps else f"complete {module}"
    evidence_phrase = source_evidence[0] if source_evidence else module
    object_phrase = ", ".join(core_objects[:3]) if core_objects else preserved_display_label(module, fallback="Business Object")
    constraint_phrase = constraints[0] if constraints else "source-defined boundary and audit context"
    responsibility = (
        f"turn source fact `{evidence_phrase}` into an executable `{module}` responsibility "
        "with explicit state, owner, blocked reason, and handoff"
    )
    input_value = f"{first_step} context, required {object_phrase} state, and source-grounded preconditions"
    output_value = f"{last_step} result, updated {object_phrase} state, and reviewable handoff context"
    return {
        "module": module,
        "primary_actor": primary_actor,
        "core_objects": object_phrase,
        "responsibility": responsibility,
        "input": input_value,
        "output": output_value,
        "exit_action": f"confirm {module} outcome and hand off the next source-defined action",
        "architectural note": f"preserve {constraint_phrase}; this contract is projected from source evidence rather than a named-case branch",
    }

def infer_fallback_module_contract(
    source_text: str,
    business_name: str,
    roles: list[dict[str, str]],
) -> dict[str, str]:
    return infer_agentic_module_contract(source_text, business_name, roles)

def extract_module_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    rows = extract_table_rows(
        fact_text,
        ["4. Module Responsibility Matrix", "Module Responsibility Matrix", "模块与实体清单"],
    )
    if rows:
        first_wave_rows = [row for row in rows if not _row_has_deferred_priority(row)]
        if first_wave_rows:
            return first_wave_rows
    priority_rows: list[dict[str, str]] = []
    capability_rows: list[dict[str, str]] = []
    engine_rows: list[dict[str, str]] = []
    roles = extract_target_user_rows(fact_text)
    for headers, table_rows in iter_markdown_tables(fact_text):
        if _table_has_header(headers, "闭环") and _table_has_header(headers, "内容"):
            for row in table_rows:
                if _row_has_deferred_priority(row):
                    continue
                module_name = _row_value(row, "闭环", "Module", "module", "能力", "Capability")
                if not module_name or module_name in {"闭环", "后置"}:
                    continue
                description = _row_value(row, "内容", "Description", "description", "职责") or module_name
                steps = _source_steps_from_text(description)
                contract = infer_fallback_module_contract(fact_text, module_name, roles)
                priority_rows.append(
                    contract
                    | {
                        "primary_actor": _choose_primary_actor_from_context(
                            roles,
                            module_name,
                            description,
                            fallback=str(contract.get("primary_actor") or ""),
                        ),
                        "responsibility": description,
                        "input": steps[0] if steps else (_row_value(row, "优先级", "Priority", "priority") or ""),
                        "output": steps[-1] if steps else str(contract.get("output") or ""),
                    }
                )
        elif _table_has_header(headers, "Agent 能力", "Capability") and _table_has_header(headers, "职责"):
            for row in table_rows:
                module_name = _row_value(row, "Agent 能力", "Capability", "能力", "module", "Module")
                if not module_name:
                    continue
                description = _row_value(row, "职责", "Responsibility", "Description") or module_name
                steps = _source_steps_from_text(description)
                contract = infer_fallback_module_contract(fact_text, module_name, roles)
                capability_rows.append(
                    contract
                    | {
                        "primary_actor": _choose_primary_actor_from_context(
                            roles,
                            module_name,
                            description,
                            fallback=str(contract.get("primary_actor") or ""),
                        ),
                        "responsibility": description,
                        "input": steps[0] if steps else str(contract.get("input") or ""),
                        "output": steps[-1] if steps else str(contract.get("output") or ""),
                        "architectural note": _row_value(row, "关键边界", "Boundary") or "preserve source-defined Agent boundary",
                    }
                )
        elif _table_has_header(headers, "引擎") and _table_has_header(headers, "首个闭环"):
            for row in table_rows:
                module_name = _row_value(row, "引擎", "Engine", "module", "Module")
                if not module_name:
                    continue
                description = _row_value(row, "定位", "Positioning", "Description") or module_name
                first_loop = _row_value(row, "首个闭环", "First Loop", "first_loop") or ""
                steps = _source_steps_from_text(first_loop)
                contract = infer_fallback_module_contract(fact_text, module_name, roles)
                engine_rows.append(
                    contract
                    | {
                        "primary_actor": _choose_primary_actor_from_context(
                            roles,
                            module_name,
                            description,
                            first_loop,
                            fallback=str(contract.get("primary_actor") or ""),
                        ),
                        "responsibility": description,
                        "input": steps[0] if steps else str(contract.get("input") or ""),
                        "output": steps[-1] if steps else first_loop,
                    }
                )
    semantic_rows = priority_rows + capability_rows + engine_rows
    if semantic_rows:
        primary: list[dict[str, str]] = []
        supporting: list[dict[str, str]] = []
        for row in semantic_rows:
            module_name = str(row.get("module", "")).strip()
            if module_name and module_name not in {item.get("module") for item in primary}:
                if re.search(r"后置|复杂防作弊|自定义人设", module_name):
                    continue
                if len(primary) < 6:
                    primary.append(row)
                else:
                    supporting.append(row)
        return primary or supporting[:6]
    light_structured_rows = _light_structured_module_rows(
        fact_text,
        roles,
        include_plain_workflow_inference=False,
    )
    if light_structured_rows:
        return light_structured_rows[:6]
    fallbacks = flatten_bullets(find_markdown_block(fact_text, ["P0（MVP 必须有）"]), 6)
    if not fallbacks:
        fallbacks = label_block_items(fact_text, [r"P0"], limit=8)
    if not fallbacks:
        fallbacks = flatten_bullets(extract_main_flow_block(fact_text), 6)
    fallbacks = [item for item in fallbacks if not is_handoff_qualifier_label(item)]
    if not fallbacks:
        inferred_light_rows = _light_structured_module_rows(
            fact_text,
            roles,
            include_plain_workflow_inference=True,
        )
        if inferred_light_rows:
            return inferred_light_rows[:6]
    roles = extract_target_user_rows(fact_text)
    modules: list[dict[str, str]] = []
    for item in fallbacks:
        business_name = item.strip() or "source-defined module"
        if "source section not found" in business_name.casefold():
            continue
        modules.append(infer_fallback_module_contract(fact_text, business_name, roles))
    return modules

def extract_object_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    rows = extract_table_rows(
        fact_text,
        ["5. Core Business Objects", "Core Business Objects", "核心业务对象", "Core Objects", "数据对象", "Knowledge Base / Memory"],
    )
    if not rows:
        rows = _semantic_table_rows(fact_text, ["数据对象"])
    if rows:
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            object_name = _row_value(
                row,
                "Object",
                "object",
                "Entity",
                "entity",
                "Name",
                "name",
                "core_object",
                "数据对象",
                "对象",
            )
            if not object_name:
                continue
            normalized_rows.append(
                {
                    "Object": object_name,
                    "Owner Module": (
                        _row_value(row, "Owner Module", "owner module", "owner_module", "owning_module", "module", "Module")
                    ),
                    "Description": (
                        _row_value(row, "Description", "description", "responsibility", "purpose", "主要字段", "字段")
                    ),
                }
            )
        if normalized_rows:
            return normalized_rows
    source_object_names = _source_object_names_from_fact_text(fact_text)
    if source_object_names:
        owner_module = ""
        source_modules = extract_module_rows(fact_text)
        if source_modules:
            owner_module = str(source_modules[0].get("module", "")).strip()
        return [
            {
                "Object": object_name,
                "Owner Module": owner_module,
                "Description": f"{object_name} from light-structured Req-Chat source facts",
            }
            for object_name in source_object_names[:8]
        ]
    modules = extract_module_rows(fact_text)

    def fallback_object_name(module_name: str) -> str:
        stripped = str(module_name or "").strip()
        capability_object = _object_name_from_capability(stripped)
        if capability_object and _looks_like_object_candidate(capability_object):
            return capability_object
        slug = slug_token(stripped)
        if stripped and (re.search(r"[^\x00-\x7F]", stripped) or slug == "item"):
            return stripped
        return title_case_token(slug)

    object_rows: list[dict[str, str]] = []
    for row in modules[:6]:
        core_objects = [item.strip() for item in str(row.get("core_objects", "")).split(",") if item.strip()]
        object_rows.append(
            {
                "Object": core_objects[0] if core_objects else fallback_object_name(str(row.get("module", "Business Object"))),
                "Owner Module": str(row.get("module", "workflow")),
                "Description": (
                    str(row.get("output", "")).strip()
                    or f"business record and state needed to keep {str(row.get('module', 'the business capability')).strip()} executable"
                ),
            }
        )
    return object_rows

def extract_business_objectives(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["3. Core Business Objectives", "Core Business Objectives", "Desired Outcome", "产品/业务目标方向"])
    items = list_items_from_block(block)
    if not items:
        items = label_block_items(block, [r"目标", r"success signals?", r"成功信号"], limit=8)
    return items

def extract_non_functional_requirements(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["7. Non-functional Requirements", "Non-functional Requirements", "Constraints", "关键约束"])
    return list_items_from_block(block) or light_structured_fact_items(fact_text, "constraint", limit=8)

def extract_architectural_constraints(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["8. Architectural Constraints", "Architectural Constraints", "Constraints", "关键约束"])
    return list_items_from_block(block) or light_structured_fact_items(fact_text, "constraint", limit=8)

def extract_out_of_scope_items(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["9. Out of Scope (MVP)", "Out of Scope (MVP)", "Scope Boundary", "范围边界与非目标"])
    items = label_block_items(block, [r"Out of scope"], limit=8)
    if not items:
        items = list_items_from_block(block)
    if not items:
        items = extract_negative_scope_items(fact_text)
    return items


def extract_negative_scope_items(text: str, *, limit: int = 8) -> list[str]:
    items: list[str] = []
    patterns = (
        r"\bmust\s+not\s+(?:invent|include|build|promise|claim|assume)\s+(.+?)(?:[.;\n]|$)",
        r"\bdo\s+not\s+(?:invent|include|build|promise|claim|assume)\s+(.+?)(?:[.;\n]|$)",
        r"不得(?:发明|纳入|包含|承诺|假设|建设|实现)\s*(.+?)(?:[。；;\n]|$)",
        r"不(?:要|应|会)?(?:发明|纳入|包含|承诺|假设|建设|实现|做)\s*(.+?)(?:[。；;\n]|$)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            value = clean_source_text_value(match.group(1))
            value = re.sub(r"^(?:P[0-9]\s+)?", "", value).strip()
            if not value:
                continue
            for item in re.split(r"\s*(?:,|、|/|\bor\b|\band\b|或|以及|和)\s*", value):
                item = clean_source_text_value(item)
                item = re.sub(r"\b(?:scope|capability|feature|module)s?\b$", "", item, flags=re.IGNORECASE).strip()
                if item:
                    items.append(item)
    return unique_preserve_order(items)[:limit]

def extract_priority_bucket(source_text: str, heading: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    values = flatten_bullets(find_markdown_block(fact_text, [heading]), 8)
    if not values and "P0" in heading:
        values = label_block_items(fact_text, [r"P0"], limit=8)
    if not values and "P1" in heading:
        values = label_block_items(fact_text, [r"P1"], limit=8)
    if not values and "P2" in heading:
        values = label_block_items(fact_text, [r"P2"], limit=8)
    if not values:
        desired_priority = ""
        if "P0" in heading:
            desired_priority = "P0"
        elif "P1" in heading:
            desired_priority = "P1"
        elif "P2" in heading:
            desired_priority = "P2"
        if desired_priority:
            for headers, rows in iter_markdown_tables(fact_text):
                if not (_table_has_header(headers, "优先级", "Priority") and _table_has_header(headers, "闭环")):
                    continue
                for row in rows:
                    priority = _row_value(row, "优先级", "Priority", "priority")
                    if desired_priority not in priority:
                        continue
                    module_name = _row_value(row, "闭环", "Module", "module")
                    description = _row_value(row, "内容", "Description", "description")
                    values.append(module_name if not description else f"{module_name}: {description}")
                if values:
                    break
    return values

def is_generic_flow_container_title(title: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(title or "")).strip().casefold()
    normalized = re.sub(r"^\d+(?:\.\d+)*\s+", "", normalized)
    normalized = re.sub(r"\s*/\s*", " / ", normalized)
    return normalized in {
        "key business flows",
        "key business flow",
        "key business flows / scenarios",
        "s / scenarios",
        "business flows",
        "business flow",
        "key workflows",
        "key workflows / scenarios",
        "key workflows, objects, and scope",
        "scenarios",
        "main flow",
        "主流程",
        "核心业务流程",
    }

def extract_flow_rows(source_text: str) -> list[dict[str, object]]:
    fact_text = source_fact_text(source_text)
    flow_block = find_markdown_block(fact_text, ["6. Key Business Flows", "Key Business Flows", "Key Workflows", "Scenarios", "主流程"])
    flows: list[dict[str, object]] = []
    current_name = ""
    current_steps: list[str] = []
    for raw in flow_block.splitlines():
        line = raw.strip()
        heading = re.match(r"^#{3,5}\s+(.+)$", line)
        if heading:
            heading_title = heading.group(1).strip()
            if is_generic_flow_container_title(heading_title):
                continue
            if current_name and current_steps:
                flows.append({"name": current_name, "steps": list(current_steps)})
            current_name = heading_title
            current_steps = []
            continue
        step = re.match(r"^\d+\.\s+(.+)$", line)
        if step:
            current_steps.append(step.group(1).strip())
    if current_name and current_steps:
        flows.append({"name": current_name, "steps": list(current_steps)})
    if flows:
        return flows
    light_structured_flows = _light_structured_flow_rows(fact_text)
    if light_structured_flows:
        return light_structured_flows
    bullet_flows = flatten_bullets(flow_block, 8)
    if bullet_flows:
        return [{"name": "Primary Flow", "steps": bullet_flows}]
    main_flow = flatten_bullets(extract_main_flow_block(fact_text), 8)
    if main_flow:
        return [{"name": "Primary Flow", "steps": main_flow}]
    table_flows: list[dict[str, object]] = []
    for headers, rows in iter_markdown_tables(fact_text):
        if _table_has_header(headers, "引擎") and _table_has_header(headers, "首个闭环"):
            for row in rows:
                name = _row_value(row, "引擎", "Engine", "module", "Module")
                first_loop = _row_value(row, "首个闭环", "First Loop", "first_loop")
                steps = [
                    _clean_sentence_fragment(part)
                    for part in re.split(r"\s*[；;]\s*", first_loop)
                    if _clean_sentence_fragment(part)
                ]
                if name and steps:
                    table_flows.append({"name": name, "steps": steps})
        elif _table_has_header(headers, "闭环") and _table_has_header(headers, "内容"):
            for row in rows:
                if _row_has_deferred_priority(row):
                    continue
                name = _row_value(row, "闭环", "Module", "module")
                content = _row_value(row, "内容", "Description", "description")
                steps = [
                    _clean_sentence_fragment(part)
                    for part in re.split(r"\s*[；;]\s*", content)
                    if _clean_sentence_fragment(part)
                ]
                if name and steps:
                    table_flows.append({"name": name, "steps": steps})
    if table_flows:
        return table_flows
    return []

def derive_navigation_surfaces(module_rows: list[dict[str, str]], objectives: list[str]) -> list[str]:
    surfaces = [str(row.get("module", "")).strip() for row in module_rows if str(row.get("module", "")).strip()]
    objective_text = " ".join(objectives).lower()
    if "dashboard" in objective_text or "仪表盘" in objective_text:
        surfaces.append("dashboard")
    if "report" in objective_text or "运营数据" in objective_text:
        surfaces.append("reports")
    return unique_preserve_order(surfaces) or ["review-bound source surface"]

def infer_first_slice_modules(module_rows: list[dict[str, str]], flow_rows: list[dict[str, object]]) -> list[str]:
    modules = [str(row.get("module", "")).strip() for row in module_rows if str(row.get("module", "")).strip()]
    if not modules:
        return ["source-defined first step", "source-defined completion step"]
    flow_text = " ".join(
        step.lower()
        for flow in flow_rows
        for step in [str(item).strip() for item in flow.get("steps", []) if str(item).strip()]
    )
    ordered = [module for module in modules if module.lower() in flow_text]
    if ordered:
        return unique_preserve_order(ordered)
    return modules

VALUE_SIGNAL_PATTERNS = (
    r"reduce|improve|increase|avoid|prevent|retain|grow|clarify|confidence|trust|quality|adoption|"
    r"manual|fragment|blocked|review|result|follow-?up|service execution|closure|continuity|"
    r"next-step guidance|source signal|taskable|actionability|explainable|executable|"
    r"降低|减少|提升|改善|避免|防止|留存|增长|清晰|信任|质量|采纳|人工|碎片|阻塞|复盘|结果|后续|执行|闭环|连续|"
    r"下一步|来源信号|可转任务|可执行|可解释"
)

COMMERCIAL_DECISION_PATTERNS = (
    r"budget|pricing|package|pilot|pay|willingness|roi|quote|commercial|invest|investment|"
    r"continue|revise|pause|decision owner|commitment owner|sponsor|"
    r"预算|定价|试点|付费|意愿|报价|投入|继续|调整|暂停|业务负责人|决策负责人"
)

USER_EXPERIENCE_SIGNAL_PATTERNS = (
    r"wait|waiting|handoff|confusion|manual|duplicate|reconstruct|friction|"
    r"blocked|delay|follow-?up|taskable|actionability|"
    r"等待|交接|混乱|人工|重复|补录|摩擦|阻塞|延迟|复诊|可转任务|可执行"
)

PRESSURE_SIGNAL_PATTERNS = (
    r"lack|missing|cannot|unable|fragment|manual|waste|friction|delay|blocked|drop|lag|invisible|"
    r"缺少|缺失|无法|不能|碎片|人工|浪费|摩擦|延迟|阻塞|遗漏|滞后|断层|不可见|失控"
)

SIGNAL_CONDITIONAL_PATTERN = re.compile(
    r"\bif\b|\bwhen\b|\bbecause\b|^\s*(?:如果|若|当(?!前))|以便|才能|否则|就更容易",
    flags=re.IGNORECASE,
)

SIGNAL_CONTRAST_PATTERN = re.compile(
    r"rather than|instead of|not just|not another|而不是|而非|不愿意|不是",
    flags=re.IGNORECASE,
)

SIGNAL_DECISION_PATTERN = re.compile(
    r"budget|pricing|pay|willingness|quote|pilot|invest|investment|judge|decision|continue|revise|pause|"
    r"预算|定价|付费|意愿|报价|试点|投入|判断|决策|继续|调整|暂停|买单",
    flags=re.IGNORECASE,
)

SIGNAL_PAIN_PATTERN = re.compile(
    r"lack|missing|cannot|unable|fragment|manual|waste|friction|delay|blocked|drop|lag|invisible|"
    r"缺少|缺失|无法|不能|碎片|人工|浪费|摩擦|延迟|阻塞|遗漏|滞后|断层|不可见|失控",
    flags=re.IGNORECASE,
)

SIGNAL_ACTIONABILITY_PATTERN = re.compile(
    r"action|task|execute|workflow|evidence|explain|actionability|review|follow-?up|"
    r"行动|任务|执行|工作流|证据|解释|可执行|可转任务|复盘|闭环|workflow-first",
    flags=re.IGNORECASE,
)

SIGNAL_NOUNISH_PATTERN = re.compile(r"^[A-Za-z0-9\u4e00-\u9fff /&()（）,，._+-]{1,32}$")

SIGNAL_LABEL_PREFIX_PATTERN = re.compile(
    r"^(?:line|signal|evidence|clue|observation|finding|线索|证据|信号)\s*\d*\s*[:：-]\s*",
    flags=re.IGNORECASE,
)

SIGNAL_SCAFFOLD_PREFIX_PATTERN = re.compile(
    r"^(?:adoption signal|review simulation|clickable(?:\s*/\s*structured prototype)? review|"
    r"structured prototype review|walkthrough|访谈/演练|点击原型 walkthrough \+ 访谈)\s*[:：-]\s*",
    flags=re.IGNORECASE,
)

SIGNAL_OPERATIONAL_FRAGMENT_PATTERN = re.compile(
    r"^(?:arrange|establish|register|execute|complete|create|build|trigger|configure|push|generate|"
    r"查看|建立|完成|推动|生成|触发|配置|登记|安排|执行)\b",
    flags=re.IGNORECASE,
)

SIGNAL_CONSEQUENCE_PATTERN = re.compile(
    r"lead to|results? in|causes?|keeps?|so that|worth continued investment|continued investment|"
    r"budget review|action loop|用户流失|运营判断滞后|持续投入|预算评审|动作闭环|"
    r"看到了问题但没有动作|经营动作|继续投入|失控",
    flags=re.IGNORECASE,
)

SIGNAL_OPPORTUNITY_PREFIX_PATTERN = re.compile(r"^(?:用|通过|借助|use|using)\b", flags=re.IGNORECASE)

SIGNAL_NEGATIVE_CONDITIONAL_PATTERN = re.compile(
    r"^\s*(?:if\b\s+(?:no|without)|when\b\s+(?:no|without)|如果没有|若没有|当没有)",
    flags=re.IGNORECASE,
)

def compact_signal_line(value: str) -> str:
    return normalize_source_handoff_phrases(re.sub(r"\s+", " ", str(value or "")).strip().strip("`"))

def normalize_signal_candidate(value: str) -> str:
    text = compact_signal_line(value)
    previous = None
    while text and text != previous:
        previous = text
        text = SIGNAL_LABEL_PREFIX_PATTERN.sub("", text).strip()
        text = SIGNAL_SCAFFOLD_PREFIX_PATTERN.sub("", text).strip()
    return text.strip(" -–—")

def collect_source_signal_pool(
    source_text: str,
    *,
    objectives: list[str],
    flows: list[dict[str, object]],
    modules: list[dict[str, str]],
    constraints: list[str],
) -> list[str]:
    fact_text = source_fact_text(source_text)
    pool: list[str] = []
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["2.2 业务机会描述", "业务机会描述", "Business Opportunity"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["2.4 至少 1 条可引用证据线索", "可引用证据线索", "Evidence"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["3.2 结构化问题清单", "结构化问题清单", "Structured Problem List"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["3.3 结构化机会清单", "结构化机会清单", "Structured Opportunity List"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["3.4 至少 1 条用户叙事", "用户叙事", "User Narrative"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["5.3 影响切片顺序的依赖假设", "依赖假设", "Dependency Assumption"]), 6))
    pool.extend(objectives)
    pool.extend(constraints[:6])
    pool.extend(extract_priority_bucket(fact_text, "P0（MVP 必须有）")[:6])
    pool.extend(
        extract_priority_bucket(fact_text, "P1（MVP 后尽快补）")[:4]
        + extract_priority_bucket(fact_text, "P2（后续阶段）")[:4]
    )
    pool.extend(str(flow.get("name", "")).strip() for flow in flows if str(flow.get("name", "")).strip())
    pool.extend(
        str(step).strip()
        for flow in flows
        for step in flow.get("steps", [])
        if str(step).strip()
    )
    pool.extend(
        str(row.get(key, "")).strip()
        for row in modules
        for key in ("module", "responsibility", "input", "output")
        if str(row.get(key, "")).strip()
    )
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["6.2 每条验证的最小方法与判定信号", "6.1 验证对象"]), 8))
    pool.extend(flatten_bullets(find_markdown_block(fact_text, ["第九部分：需要后续补实的 unknown / provisional 信息"]), 8))
    return [item for item in pool if compact_signal_line(item)]

def signal_intent_match(text: str, *, intent: str) -> bool:
    if intent == "pressure":
        if SIGNAL_CONDITIONAL_PATTERN.search(text) and not SIGNAL_NEGATIVE_CONDITIONAL_PATTERN.search(text):
            return False
        return bool(SIGNAL_PAIN_PATTERN.search(text))
    if intent == "commercial":
        return bool(SIGNAL_DECISION_PATTERN.search(text))
    if intent == "experience":
        return bool(
            SIGNAL_PAIN_PATTERN.search(text)
            or re.search(r"wait|waiting|handoff|manual reconstruction|人工遗漏|交接|补录|失控", text, flags=re.IGNORECASE)
        )
    return bool(
        SIGNAL_ACTIONABILITY_PATTERN.search(text)
        or SIGNAL_DECISION_PATTERN.search(text)
        or SIGNAL_CONTRAST_PATTERN.search(text)
    )

def signal_priority_score(candidate: str, *, intent: str = "generic") -> int:
    text = normalize_signal_candidate(candidate)
    score = 0
    if len(text) >= 18:
        score += 1
    if len(text) >= 36:
        score += 1
    if re.search(r"[，,；;：:!?？。]", text):
        score += 1
    if SIGNAL_CONDITIONAL_PATTERN.search(text):
        score += 3
    if SIGNAL_CONTRAST_PATTERN.search(text):
        score += 3
    if SIGNAL_DECISION_PATTERN.search(text):
        score += 3
    if SIGNAL_PAIN_PATTERN.search(text):
        score += 2
    if SIGNAL_ACTIONABILITY_PATTERN.search(text):
        score += 2
    if SIGNAL_NOUNISH_PATTERN.fullmatch(text):
        score -= 2
    if len(text) <= 12:
        score -= 2
    if intent == "pressure":
        if SIGNAL_PAIN_PATTERN.search(text):
            score += 4
        if SIGNAL_CONSEQUENCE_PATTERN.search(text):
            score += 3
        if SIGNAL_PAIN_PATTERN.search(text) and SIGNAL_DECISION_PATTERN.search(text):
            score += 3
        if SIGNAL_CONDITIONAL_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 4
        if SIGNAL_OPERATIONAL_FRAGMENT_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 4
        if SIGNAL_OPPORTUNITY_PREFIX_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 3
    elif intent == "commercial":
        if SIGNAL_DECISION_PATTERN.search(text):
            score += 5
        if SIGNAL_CONTRAST_PATTERN.search(text):
            score += 2
    elif intent == "experience":
        if SIGNAL_PAIN_PATTERN.search(text):
            score += 4
        if re.search(r"wait|waiting|handoff|manual reconstruction|人工遗漏|交接|补录|失控", text, flags=re.IGNORECASE):
            score += 3
        if SIGNAL_CONDITIONAL_PATTERN.search(text) and not SIGNAL_PAIN_PATTERN.search(text):
            score -= 2
    else:
        if SIGNAL_OPERATIONAL_FRAGMENT_PATTERN.search(text) and not (
            SIGNAL_DECISION_PATTERN.search(text) or SIGNAL_CONTRAST_PATTERN.search(text)
        ):
            score -= 4
        if SIGNAL_PAIN_PATTERN.search(text) and not SIGNAL_ACTIONABILITY_PATTERN.search(text):
            score -= 2
    return score

def select_source_grounded_signals(
    candidates: list[str],
    *,
    patterns: str,
    limit: int = 4,
    intent: str = "generic",
) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for idx, raw in enumerate(candidates):
        candidate = normalize_signal_candidate(raw)
        if not candidate or len(candidate) > 220:
            continue
        if not re.search(patterns, candidate, flags=re.IGNORECASE):
            continue
        if not signal_intent_match(candidate, intent=intent):
            continue
        key = _normalized_label_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        ranked.append((-signal_priority_score(candidate, intent=intent), idx, candidate))
    ranked.sort()
    return [candidate for _, _, candidate in ranked[:limit]]

def extract_domain_context(source_text: str) -> dict[str, object]:
    fact_text = source_fact_text(source_text)
    roles = extract_target_user_rows(source_text)
    objectives = extract_business_objectives(source_text)
    module_rows = extract_module_rows(source_text)
    object_rows = extract_object_rows(source_text)
    flow_rows = extract_flow_rows(source_text)
    nfrs = extract_non_functional_requirements(source_text)
    constraints = extract_architectural_constraints(source_text)
    out_of_scope = extract_out_of_scope_items(source_text)
    p0 = extract_priority_bucket(source_text, "P0（MVP 必须有）")
    p1 = extract_priority_bucket(source_text, "P1（MVP 后尽快补）")
    p2 = extract_priority_bucket(source_text, "P2（后续阶段）")
    navigation_surfaces = derive_navigation_surfaces(module_rows, objectives)
    first_slice_modules = infer_first_slice_modules(module_rows, flow_rows)
    validation_priority_signals = (
        flatten_bullets(find_markdown_block(fact_text, ["6.2 每条验证的最小方法与判定信号"]), 8)
        + flatten_bullets(find_markdown_block(fact_text, ["第九部分：需要后续补实的 unknown / provisional 信息"]), 8)
    )
    source_signal_pool = collect_source_signal_pool(
        source_text,
        objectives=objectives,
        flows=flow_rows,
        modules=module_rows,
        constraints=constraints,
    )
    return {
        "source_text": source_text,
        "product_label": extract_product_label(source_text),
        "roles": roles,
        "segments": detect_source_segments(source_text),
        "objectives": objectives,
        "modules": module_rows,
        "objects": object_rows,
        "flows": flow_rows,
        "nfrs": nfrs,
        "constraints": constraints,
        "out_of_scope": out_of_scope,
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "navigation_surfaces": navigation_surfaces,
        "first_slice_modules": first_slice_modules,
        "business_value_signals": select_source_grounded_signals(
            source_signal_pool,
            patterns=VALUE_SIGNAL_PATTERNS,
            limit=5,
            intent="value",
        ),
        "pressure_signals": select_source_grounded_signals(
            source_signal_pool,
            patterns=PRESSURE_SIGNAL_PATTERNS,
            limit=5,
            intent="pressure",
        ),
        "commercial_decision_signals": select_source_grounded_signals(
            validation_priority_signals + source_signal_pool,
            patterns=COMMERCIAL_DECISION_PATTERNS,
            limit=5,
            intent="commercial",
        ),
        "user_experience_signals": select_source_grounded_signals(
            source_signal_pool,
            patterns=USER_EXPERIENCE_SIGNAL_PATTERNS,
            limit=5,
            intent="experience",
        ),
    }
