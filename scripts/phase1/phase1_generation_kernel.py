#!/usr/bin/env python3
"""
Shared Phase-1 source and domain extraction helpers.
"""

from __future__ import annotations

import re

from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases

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
            rf"^##+\s+(?:\d+(?:\.\d+)?\s+)?[^\n]*{re.escape(keyword)}[^\n]*$",
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
            rf"^#{{2,{heading_level}}}\s+",
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

def source_packet_evidence_block(source_text: str, heading_pattern: str) -> str:
    """Map legacy P1 source evidence headings to source-input-packet sections.

    Stage evidence packs cite raw source sections for review. A source input
    packet uses a different section contract, so missing legacy headings should
    resolve to the closest packet fact/review section instead of emitting
    `(source section not found)` noise.
    """

    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return ""
    for triggers, packet_headings in SOURCE_PACKET_EVIDENCE_ALIASES:
        if not any(re.search(trigger, heading_pattern, flags=re.IGNORECASE) for trigger in triggers):
            continue
        for heading in packet_headings:
            block = find_markdown_block(source_text, [heading])
            if block:
                return f"## P1 Source Brief Evidence: {heading}\n{normalize_source_handoff_phrases(demote_headings(block))}"
    block = source_fact_text(source_text)
    if block:
        lines = block.splitlines()
        excerpt = normalize_source_handoff_phrases("\n".join(lines[: min(len(lines), 20)]).strip())
        return f"## P1 Source Brief Evidence: excerpt\n{demote_headings(excerpt)}"
    return ""

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

    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return source_text
    block = find_markdown_block(source_text, ["P1 Source Brief"])
    if block:
        return normalize_source_handoff_phrases(block)
    return block or source_text

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

def detect_source_segments(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)

    def normalize_candidate(value: str) -> str:
        cleaned = str(value or "").strip().strip("`")
        cleaned = re.sub(r"^\s*(?:主要用户|次要用户|评审用户)\s*[：:]\s*", "", cleaned).strip()
        if not cleaned:
            return ""
        lowered = cleaned.casefold()
        excluded_prefixes = ("客群边界", "使用边界", "边界", "首发不做", "不做", "非目标")
        if any(lowered.startswith(prefix.casefold()) for prefix in excluded_prefixes):
            return ""
        if "不承诺" in cleaned or "不做" in cleaned:
            return ""
        return cleaned

    candidate_block = find_h2_block(fact_text, r"2\.3\s+研究对象/目标用户边界")
    candidates = [value for value in (normalize_candidate(item) for item in list_items_from_block(candidate_block)) if value]
    if not candidates:
        table_rows = parse_markdown_table(find_markdown_block(fact_text, ["User, Buyer, Operator", "2. Target Users", "Target Users", "目标用户"]))
        candidates = [
            normalize_candidate(str(row.get("Role", "") or row.get("role", "")).strip())
            for row in table_rows
            if normalize_candidate(str(row.get("Role", "") or row.get("role", "")).strip())
        ]
    if not candidates:
        target_users_block = find_markdown_block(fact_text, ["User, Buyer, Operator", "Target Users", "目标用户"])
        candidates = [value for value in (normalize_candidate(item) for item in list_items_from_block(target_users_block)) if value]
    if not candidates:
        for line in fact_text.splitlines():
            row = re.match(r"^\|\s*([^|]+?)\s*\|", line)
            if row:
                cell = normalize_candidate(row.group(1).strip())
                if cell and cell.lower() not in {"role", "---"} and "source section not found" not in cell.lower():
                    candidates.append(cell)
            if len(candidates) >= 5:
                break
    return unique_preserve_order(candidates) or ["primary operator", "secondary collaborator", "review stakeholder"]

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
        role_name = detect_source_segments(f"## 2.3 研究对象/目标用户边界\n- {item}")[0] if item else ""
        description = match.group(1) if match else ""
        if role_name and role_name not in seen:
            rows.append({"Role": role_name, "Description": description})
            seen.add(role_name)
    if rows:
        return rows
    rows = extract_table_rows(fact_text, ["User, Buyer, Operator", "2. Target Users", "Target Users", "目标用户"])
    if rows:
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            role = str(row.get("Role") or row.get("role") or "").strip().strip("`")
            if role:
                normalized = dict(row)
                normalized["Role"] = role
                normalized_rows.append(normalized)
        return normalized_rows or rows
    return [{"Role": value.strip("`"), "Description": ""} for value in detect_source_segments(fact_text)]

def detect_source_style(source_text: str) -> str:
    lowered = source_fact_text(source_text).casefold()
    if re.search(
        r"\bgeo\b|ai 搜索|生成式回答|ai 可见性|visibility|tracked scope|citation|competitor|竞争对手|归因|roi|conversion|b2b 市场|marketing owner|content operator|growth owner|baseline run",
        lowered,
    ):
        return "growth_observation"
    if re.search(r"pet|clinic|veterinar|宠物|诊所|就诊|治疗|复诊|随访|discharge|follow-up", lowered):
        return "pet_clinic"
    return "generic"

def _role_name_list(roles: list[dict[str, str]]) -> list[str]:
    return [role_label(row) for row in roles if role_label(row)]

def _find_role_by_hint(role_names: list[str], patterns: list[str], fallback_index: int) -> str:
    for role in role_names:
        lowered = role.casefold()
        if any(re.search(pattern, lowered) for pattern in patterns):
            return role
    return role_names[fallback_index] if role_names else "primary operator"

def infer_fallback_module_contract(
    source_text: str,
    business_name: str,
    roles: list[dict[str, str]],
) -> dict[str, str]:
    style = detect_source_style(source_text)
    role_names = _role_name_list(roles)
    lowered = business_name.casefold()

    if style == "growth_observation":
        primary_actor = _find_role_by_hint(role_names, [r"marketing", r"市场"], 0)
        execution_actor = _find_role_by_hint(role_names, [r"content", r"内容"], 1 if len(role_names) > 1 else 0)
        reviewer_actor = _find_role_by_hint(role_names, [r"business", r"增长", r"review"], 2 if len(role_names) > 2 else 0)
        if any(token in lowered for token in ["tenant", "audit", "actor"]):
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "TenantWorkspace, ActorRole, AuditRecord",
                "responsibility": "establish tenant, actor, and audit boundary for the GEO operating loop",
                "input": "tenant identity, member roles, and audit policy",
                "output": "active tenant workspace, role boundary, and audit-ready context",
                "exit_action": "save tenant/audit setup and enter tracked scope configuration",
                "architectural note": "preserve tenant-safe boundary and audit provenance before scope operations",
            }
        if "tracked scope" in lowered:
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "TrackedScope, ScopeTopicSet, CompetitorSet",
                "responsibility": "define monitored brand, competitor, topic, and prompt scope for one GEO cycle",
                "input": "brand targets, competitor set, topic boundaries, and prompt scope definition",
                "output": "versioned tracked scope, monitored topic set, and scope boundary",
                "exit_action": "freeze tracked scope and start baseline generation",
                "architectural note": "preserve scope provenance and downstream baseline comparability",
            }
        if "baseline" in lowered:
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "BaselineRun, EvidenceSnapshot, BaselineSummary",
                "responsibility": "run baseline collection and preserve explainable GEO evidence for the current cycle",
                "input": "tracked scope, prompt set, and collection window",
                "output": "baseline snapshot, evidence set, and freshness status",
                "exit_action": "review baseline freshness and open findings",
                "architectural note": "preserve evidence freshness, provenance, and cycle-level comparability",
            }
        if "finding" in lowered:
            return {
                "module": business_name,
                "primary_actor": primary_actor,
                "core_objects": "Finding, EvidenceLink, PriorityReason",
                "responsibility": "structure findings with evidence link, priority reason, and actionability signal",
                "input": "baseline snapshot, evidence set, and monitored scope context",
                "output": "prioritized findings, evidence links, and actionability rationale",
                "exit_action": "confirm finding priority and open recommendation/task handoff",
                "architectural note": "preserve finding readability and downstream recommendation continuity",
            }
        if "recommendation" in lowered or "task" in lowered:
            return {
                "module": business_name,
                "primary_actor": execution_actor,
                "core_objects": "Recommendation, ActionTask, ExecutionStatus",
                "responsibility": "turn recommendation-ready findings into assigned tasks with explicit evidence linkage",
                "input": "finding, evidence link, priority rationale, and owner hint",
                "output": "task-ready recommendation, assigned task, and execution status",
                "exit_action": "handoff execution and keep review linkage visible",
                "architectural note": "preserve finding-to-task bridge, ownership, and blocked-reason visibility",
            }
        if "review" in lowered:
            return {
                "module": business_name,
                "primary_actor": reviewer_actor,
                "core_objects": "ReviewCycle, DecisionRecord, ReviewSummary",
                "responsibility": "summarize one GEO cycle and record continue/revise/pause judgment with evidence",
                "input": "task outcomes, finding deltas, and cycle evidence",
                "output": "continue/revise/pause decision, review summary, and cycle conclusion",
                "exit_action": "record cycle decision and close the current review window",
                "architectural note": "preserve review judgment, evidence lineage, and audit trace",
            }

    if style == "pet_clinic":
        intake_actor = _find_role_by_hint(role_names, [r"reception", r"front desk", r"接待", r"前台"], 0)
        clinician_actor = _find_role_by_hint(role_names, [r"veter", r"vet", r"兽医"], 1 if len(role_names) > 1 else 0)
        manager_actor = _find_role_by_hint(role_names, [r"manager", r"admin", r"clinic", r"管理"], 2 if len(role_names) > 2 else 0)
        if any(token in lowered for token in ["接诊", "登记", "intake", "register", "预约", "arriv"]):
            return {
                "module": business_name,
                "primary_actor": intake_actor,
                "core_objects": "VisitRecord, PetProfile, IntakeSnapshot",
                "responsibility": "register the arriving pet and preserve clinician-ready intake context",
                "input": "arrival request, owner details, pet profile, and visit reason",
                "output": "checked-in visit, pet record, and intake handoff context",
                "exit_action": "complete intake and hand off to consultation or treatment",
                "architectural note": "preserve intake evidence, blocked reason, and clinician-ready handoff context",
            }
        if any(token in lowered for token in ["治疗", "检查", "consult", "care", "visit", "诊疗"]):
            return {
                "module": business_name,
                "primary_actor": clinician_actor,
                "core_objects": "TreatmentRecord, DiagnosticOrder, VisitPlan",
                "responsibility": "record diagnosis, treatment execution, and the next clinical action",
                "input": "checked-in visit, symptoms, prior record, and exam notes",
                "output": "treatment record, diagnostic result, and next action",
                "exit_action": "record treatment result and prepare discharge or follow-up",
                "architectural note": "preserve treatment evidence, blocked reason, and downstream discharge continuity",
            }
        if any(token in lowered for token in ["复诊", "随访", "review", "follow", "discharge", "离院"]):
            return {
                "module": business_name,
                "primary_actor": manager_actor,
                "core_objects": "FollowUpTask, DischargePacket, ReviewSummary",
                "responsibility": "arrange follow-up, discharge closure, and review-ready clinic summary",
                "input": "treatment result, discharge context, and follow-up need",
                "output": "follow-up plan, discharge confirmation, and review-ready summary",
                "exit_action": "close the visit and schedule follow-up or review",
                "architectural note": "preserve discharge closure, follow-up timing, and clinic review context",
            }

    return {
        "module": business_name,
        "primary_actor": _find_role_by_hint(role_names, [r".*"], 0),
        "core_objects": preserved_display_label(business_name, fallback="Business Object"),
        "responsibility": f"complete {business_name} with explicit input, output, and handoff",
        "input": f"{business_name} required input context",
        "output": f"{business_name} completion record",
        "exit_action": f"confirm {business_name} and hand off to the next step",
        "architectural note": "preserve explicit responsibility and downstream handoff",
    }

def extract_module_rows(source_text: str) -> list[dict[str, str]]:
    fact_text = source_fact_text(source_text)
    rows = extract_table_rows(
        fact_text,
        ["4. Module Responsibility Matrix", "Module Responsibility Matrix", "模块与实体清单"],
    )
    if rows:
        return rows
    fallbacks = flatten_bullets(find_markdown_block(fact_text, ["P0（MVP 必须有）"]), 6)
    if not fallbacks:
        fallbacks = label_block_items(fact_text, [r"P0"], limit=8)
    if not fallbacks:
        fallbacks = flatten_bullets(extract_main_flow_block(fact_text), 6)
    fallbacks = [item for item in fallbacks if not is_handoff_qualifier_label(item)]
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
        ["5. Core Business Objects", "Core Business Objects", "核心业务对象", "Core Objects"],
    )
    if rows:
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            object_name = (
                row.get("Object")
                or row.get("object")
                or row.get("Entity")
                or row.get("entity")
                or row.get("Name")
                or row.get("name")
                or row.get("core_object")
                or ""
            ).strip()
            if not object_name:
                continue
            normalized_rows.append(
                {
                    "Object": object_name,
                    "Owner Module": (
                        row.get("Owner Module")
                        or row.get("owner module")
                        or row.get("owner_module")
                        or row.get("owning_module")
                        or row.get("module")
                        or row.get("Module")
                        or ""
                    ).strip(),
                    "Description": (
                        row.get("Description")
                        or row.get("description")
                        or row.get("responsibility")
                        or row.get("purpose")
                        or ""
                    ).strip(),
                }
            )
        if normalized_rows:
            return normalized_rows
    modules = extract_module_rows(fact_text)

    def fallback_object_name(module_name: str) -> str:
        stripped = str(module_name or "").strip()
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
    return list_items_from_block(block)

def extract_architectural_constraints(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["8. Architectural Constraints", "Architectural Constraints", "Constraints", "关键约束"])
    return list_items_from_block(block)

def extract_out_of_scope_items(source_text: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    block = find_markdown_block(fact_text, ["9. Out of Scope (MVP)", "Out of Scope (MVP)", "Scope Boundary", "范围边界与非目标"])
    items = label_block_items(block, [r"Out of scope"], limit=8)
    if not items:
        items = list_items_from_block(block)
    return items

def extract_priority_bucket(source_text: str, heading: str) -> list[str]:
    fact_text = source_fact_text(source_text)
    values = flatten_bullets(find_markdown_block(fact_text, [heading]), 8)
    if not values and "P0" in heading:
        values = label_block_items(fact_text, [r"P0"], limit=8)
    if not values and "P1" in heading:
        values = label_block_items(fact_text, [r"P1"], limit=8)
    if not values and "P2" in heading:
        values = label_block_items(fact_text, [r"P2"], limit=8)
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
            if current_name:
                flows.append({"name": current_name, "steps": list(current_steps)})
            current_name = heading_title
            current_steps = []
            continue
        step = re.match(r"^\d+\.\s+(.+)$", line)
        if step:
            current_steps.append(step.group(1).strip())
    if current_name:
        flows.append({"name": current_name, "steps": list(current_steps)})
    if flows:
        return flows
    main_flow = flatten_bullets(extract_main_flow_block(fact_text), 8)
    if main_flow:
        return [{"name": "Primary Flow", "steps": main_flow}]
    return []

def derive_navigation_surfaces(module_rows: list[dict[str, str]], objectives: list[str]) -> list[str]:
    surfaces = [str(row.get("module", "")).strip() for row in module_rows if str(row.get("module", "")).strip()]
    objective_text = " ".join(objectives).lower()
    if "dashboard" in objective_text or "仪表盘" in objective_text:
        surfaces.append("dashboard")
    if "report" in objective_text or "运营数据" in objective_text:
        surfaces.append("reports")
    return unique_preserve_order(surfaces) or ["workflow-home", "operations", "reports"]

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
    r"manual|fragment|blocked|review|result|follow-?up|treatment|closure|continuity|"
    r"recommendation|finding|taskable|actionability|explainable|executable|"
    r"降低|减少|提升|改善|避免|防止|留存|增长|清晰|信任|质量|采纳|人工|碎片|阻塞|复盘|结果|复诊|治疗|闭环|连续|"
    r"建议|发现|可转任务|可执行|可解释"
)

COMMERCIAL_DECISION_PATTERNS = (
    r"budget|pricing|package|pilot|pay|willingness|roi|quote|commercial|invest|investment|"
    r"continue|revise|pause|business owner|decision owner|sponsor|"
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
