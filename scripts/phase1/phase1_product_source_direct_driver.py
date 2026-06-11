#!/usr/bin/env python3
"""Build the Phase-1 product/source direct driver before artifact authoring."""

from __future__ import annotations

import re
from typing import Any

from phase1.phase1_generation_kernel import (
    clean_source_text_value as _clean_text,
    find_markdown_block as _find_markdown_block,
)
from phase1.phase1_semantic_authoring_spine import build_semantic_authoring_spine
from phase1.phase1_source_text_normalization import normalize_source_handoff_phrases


DRIVER_ID = "p1-product-source-direct-driver.v1"
BUSINESS_COMPLETENESS_DRIVER_ID = "p1-business-completeness-direct-driver.v1"



def _source_fact_text(source_text: str) -> str:
    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return source_text
    return normalize_source_handoff_phrases(_find_markdown_block(source_text, ("P1 Source Brief",)) or source_text)


def _packet_open_truth_gap_items(source_text: str) -> list[str]:
    if not re.search(r"^#\s+P1 Source Input Packet\b", source_text, flags=re.IGNORECASE | re.MULTILINE):
        return []
    block = _find_markdown_block(source_text, ("Open Truth Gaps",))
    return _bullet_items(block, limit=12)


def _bullet_items(block: str, *, limit: int = 12) -> list[str]:
    items: list[str] = []
    for raw in block.splitlines()[1:]:
        line = raw.strip()
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if not bullet:
            continue
        value = _clean_text(bullet.group(1))
        if value and "source section not found" not in value.casefold() and value not in items:
            items.append(value)
        if len(items) >= limit:
            break
    return items


def _source_bullets(source_text: str) -> list[str]:
    bullets: list[str] = []
    for raw in source_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if bullet:
            line = bullet.group(1).strip()
        if line.startswith("#"):
            continue
        bullets.append(_clean_text(line))
    return [line for line in bullets if line]


def _parse_markdown_table(block: str) -> list[dict[str, str]]:
    rows: list[list[str]] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [_clean_text(cell) for cell in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells):
            continue
        rows.append(cells)
    if len(rows) < 2:
        return []
    headers = [cell.lower() for cell in rows[0]]
    parsed: list[dict[str, str]] = []
    for cells in rows[1:]:
        if len(cells) != len(headers):
            continue
        parsed.append(dict(zip(headers, cells)))
    return parsed


def _table_values(source_text: str, heading_patterns: tuple[str, ...], column_patterns: tuple[str, ...]) -> list[str]:
    block = _find_markdown_block(source_text, heading_patterns)
    values: list[str] = []
    for row in _parse_markdown_table(block):
        for header, value in row.items():
            if any(pattern in header for pattern in column_patterns):
                cleaned = _clean_text(value)
                if cleaned and cleaned not in values:
                    values.append(cleaned)
    return values


def _label_block_items(source_text: str, label_patterns: tuple[str, ...], *, limit: int = 12) -> list[str]:
    items: list[str] = []
    active = False
    for raw in source_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            active = False
            continue
        if any(re.match(rf"^{pattern}\s*[:：]\s*$", line, flags=re.IGNORECASE) for pattern in label_patterns):
            active = True
            continue
        if active and re.match(r"^[A-Za-z0-9 /_-]{1,40}\s*[:：]\s*$", line):
            break
        if not active:
            continue
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if not bullet:
            continue
        value = _clean_text(bullet.group(1))
        if value and "source section not found" not in value.casefold() and value not in items:
            items.append(value)
        if len(items) >= limit:
            break
    return items


def _section_items(
    source_text: str,
    heading_patterns: tuple[str, ...],
    *,
    exclude_heading_patterns: tuple[str, ...] = (),
) -> list[str]:
    items: list[str] = []
    active = False
    for raw in source_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            lowered = line.lower()
            active = any(pattern in lowered for pattern in heading_patterns) and not any(
                pattern in lowered for pattern in exclude_heading_patterns
            )
            continue
        if not active:
            continue
        bullet = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if bullet:
            line = bullet.group(1).strip()
        if line and not line.startswith("|"):
            items.append(_clean_text(line))
    return [item for item in items if item]


def _unique_preserve_order(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def _looks_like_operating_boundary_note(value: str) -> bool:
    lowered = value.casefold()
    boundary_patterns = (
        "mechanism testing only",
        "not real user research",
        "not external market validation",
        "not owner sign-off",
        "not budget approval",
        "not production readiness",
        "not real owner sign-off",
        "not real external validation",
        "these numbers are operating assumptions",
        "these numbers are synthetic operating assumptions",
        "these numbers and statements are synthetic operating assumptions",
        "these numbers and statements are operating assumptions",
        "these assumptions test",
        "这些数字只用于",
        "这些假设只用于",
        "不代表真实",
        "不是真实",
        "不是外部验证",
    )
    return any(pattern in lowered for pattern in boundary_patterns)


def _currency_values(text: str) -> list[str]:
    return re.findall(r"`?\$[\d,]+(?:-\$?[\d,]+)?(?:/[A-Za-z]+)?`?", text)


def _preferred_currency(text: str, *, monthly: bool = False) -> str:
    values = _currency_values(text)
    if not values:
        return ""
    if monthly:
        for value in reversed(values):
            if "/month" in value.lower():
                return value
    for value in reversed(values):
        if "-" in value or "/month" in value.lower():
            return value
    return values[-1]


def _first_percent(text: str) -> str:
    match = re.search(r"`?\d+\s*%`?", text)
    return match.group(0) if match else ""


def _first_hours(text: str) -> str:
    match = re.search(r"`?\d+\s*-\s*\d+\s*(?:hours?|小时)(?:/week|/周)?`?", text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _first_hour_rate(text: str) -> str:
    match = re.search(r"`?\$[\d,]+(?:\.\d+)?\s*/\s*(?:hour|hr|小时)`?", text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _normalize_operating_item(value: str, *, zh: bool) -> str:
    text = _strip_source_labels(value)
    lowered = text.casefold()
    if not text:
        return ""

    amount = _preferred_currency(text)
    monthly_amount = _preferred_currency(text, monthly=True)
    percent = _first_percent(text)
    hours = _first_hours(text)
    hour_rate = _first_hour_rate(text)
    weekly_reviews = re.search(r"\b\d+\s+weekly reviews\b|\b\d+\s*周\s*review\b", text, flags=re.IGNORECASE)
    weekly_review_text = weekly_reviews.group(0) if weekly_reviews else ""
    extra_fields = re.search(r"`?\d+`?\s*(?:extra\s+fields|个字段|字段)", text, flags=re.IGNORECASE)
    extra_fields_text = extra_fields.group(0) if extra_fields else ""

    has_pilot = re.search(r"pilot|试点", lowered)
    has_subscription = re.search(r"subscription range|pricing|discuss|订阅区间|付费|讨论", lowered)
    has_cost = re.search(r"cost|hour|chase|workload|人工|成本|工时|追问|追踪", lowered)
    has_threshold = re.search(r"threshold|review|missed|closed|drops?|increase|下降|阈值|复盘|解释|不升|不增加", lowered)
    has_friction = re.search(r"friction|field|administrative|entry|pause|阻力|字段|录入|暂停", lowered)
    no_subscription_commitment = re.search(r"not a subscription commitment|不承诺订阅|不等于订阅", lowered)

    if zh:
        if has_friction:
            fragments = []
            if extra_fields_text:
                fragments.append(f"额外字段不超过 {extra_fields_text}")
            if re.search(r"administrative|entry|录入", lowered):
                fragments.append("额外行政录入不可增加")
            if re.search(r"pause|暂停", lowered):
                fragments.append("摩擦上升则暂停试点")
            return "，".join(fragments) or text
        if has_subscription and amount:
            parts = []
            if weekly_review_text:
                parts.append(f"{weekly_review_text} 后")
            if percent:
                parts.append(f"overdue follow-up 下降 {percent}")
            if re.search(r"workload|工作量", lowered):
                parts.append("staff workload 不上升")
            condition = "且".join(parts)
            prefix = f"{condition}，" if condition else ""
            return f"{prefix}才讨论 {amount} 订阅区间"
        if has_cost and (hours or hour_rate or monthly_amount or amount):
            values = [value for value in (hours, hour_rate, monthly_amount or amount) if value]
            return f"当前人工追踪成本 {' / '.join(values)}"
        if has_threshold:
            parts = []
            if percent:
                parts.append(f"overdue follow-up 下降 {percent}")
            if re.search(r"missed|closed|解释|review|复盘", lowered):
                parts.append("weekly review 可解释 missed / closed follow-up")
            if re.search(r"workload|工作量", lowered):
                parts.append("staff workload 不上升")
            return "继续投入阈值：" + "，".join(parts) if parts else text
        if has_pilot and amount:
            suffix = "，但不等于订阅承诺" if no_subscription_commitment else ""
            return f"30 天试点预算 {amount}{suffix}"
        return text

    if has_friction:
        fragments = []
        if extra_fields_text:
            fragments.append(f"extra fields capped at {extra_fields_text}")
        if re.search(r"administrative|entry", lowered):
            fragments.append("no extra administrative entry")
        if re.search(r"pause", lowered):
            fragments.append("pause the pilot if friction rises")
        return ", ".join(fragments) or text
    if has_subscription and amount:
        parts = []
        if weekly_review_text:
            parts.append(f"after {weekly_review_text}")
        if percent:
            parts.append(f"overdue follow-up drops {percent}")
        if re.search(r"workload", lowered):
            parts.append("staff workload does not increase")
        condition = " and ".join(parts)
        prefix = f"{condition}, " if condition else ""
        return f"{prefix}discuss {amount} subscription range"
    if has_cost and (hours or hour_rate or monthly_amount or amount):
        values = [value for value in (hours, hour_rate, monthly_amount or amount) if value]
        return f"current tracking cost {' / '.join(values)}"
    if has_threshold:
        parts = []
        if percent:
            parts.append(f"overdue follow-up drops {percent}")
        if re.search(r"missed|closed|review", lowered):
            parts.append("weekly review explains missed / closed follow-up")
        if re.search(r"workload", lowered):
            parts.append("staff workload does not increase")
        return "continuation threshold: " + ", ".join(parts) if parts else text
    if has_pilot and amount:
        suffix = ", not a subscription commitment" if no_subscription_commitment else ""
        return f"30-day pilot budget {amount}{suffix}"
    return text


def _compact_operating_item(value: str, *, zh: bool = False) -> str:
    normalized = _normalize_operating_item(value, zh=zh)
    if normalized != _strip_source_labels(value):
        return normalized
    text = _strip_source_labels(value)
    text = re.sub(r"\s+", " ", text).strip("。；; ")
    if not text:
        return ""
    if len(text) <= 132:
        return text
    parts = [
        part.strip("。；; ")
        for part in re.split(r"[。；;]+", text)
        if part.strip("。；; ")
    ]
    priority = re.compile(
        r"\$|budget|cost|hour|pilot|subscription|threshold|review|workload|friction|pause|"
        r"预算|成本|工时|试点|订阅|付费|阈值|复盘|不升|不增加|阻力|暂停|30%",
        flags=re.IGNORECASE,
    )
    picked = [part for part in parts if priority.search(part)]
    if not picked:
        picked = parts[:1]
    compact = "; ".join(picked[:2]).strip("。；; ")
    if len(compact) > 150:
        words = re.split(r"\s+", compact)
        if len(words) > 1:
            compact = " ".join(words[:18]).strip()
        else:
            compact = compact[:150].rstrip("，,。；; ")
    return compact


def _operating_economics_items(fact_text: str) -> list[str]:
    section_items = _section_items(
        fact_text,
        (
            "budget",
            "cost",
            "continuation",
            "economics",
            "pricing",
            "commercial",
            "operating assumption",
            "adoption friction",
            "threshold",
            "pilot",
            "subscription",
            "workload",
            "预算",
            "成本",
            "继续",
            "投入",
            "经济",
            "商业",
            "采纳",
            "阻力",
            "阈值",
            "试点",
            "订阅",
            "付费",
            "工作量",
        ),
        exclude_heading_patterns=("open truth", "truth-state", "ledger", "gap", "缺口", "标记"),
    )
    labeled_loss_items = _label_block_items(
        fact_text,
        (
            "synthetic business loss",
            "simulated business loss",
            "real interview business loss",
            "real business loss",
            "business loss",
            "operating loss",
            "loss",
            "经营损失",
            "业务损失",
            "当前损失",
        ),
        limit=8,
    )
    items = _unique_preserve_order([*labeled_loss_items, *section_items])
    zh = _source_has_chinese(fact_text)
    return [
        compact
        for compact in (
            _compact_operating_item(item, zh=zh)
            for item in items
            if not _looks_like_operating_boundary_note(item)
        )
        if compact
    ]


def _first_operating_match(
    items: list[str],
    pattern: str,
    *,
    prefer_pattern: str = "",
    exclude_pattern: str = "",
) -> str:
    regex = re.compile(pattern, flags=re.IGNORECASE)
    prefer_regex = re.compile(prefer_pattern, flags=re.IGNORECASE) if prefer_pattern else None
    exclude_regex = re.compile(exclude_pattern, flags=re.IGNORECASE) if exclude_pattern else None
    if prefer_regex:
        for item in items:
            if regex.search(item) and prefer_regex.search(item) and not (exclude_regex and exclude_regex.search(item)):
                return item
    for item in items:
        if regex.search(item) and not (exclude_regex and exclude_regex.search(item)):
            return item
    for item in items:
        if regex.search(item):
            return item
    return ""


def _combined_cost_basis_item(items: list[str], *, zh: bool) -> str:
    hours_item = _first_operating_match(items, r"hours?|小时")
    money_item = _first_operating_match(
        items,
        r"cost|hour|hours|workload|成本|工时|工作量|\$",
        prefer_pattern=r"\$|/month",
    )
    combined = " ".join(_unique_preserve_order([hours_item, money_item]))
    if not combined:
        return ""
    hours = _first_hours(combined)
    hour_rate = _first_hour_rate(combined)
    monthly_amount = _preferred_currency(combined, monthly=True)
    amount = _preferred_currency(combined)
    values = [value for value in (hours, hour_rate, monthly_amount or amount) if value]
    if not values:
        return money_item or hours_item
    if zh:
        return f"当前人工追踪成本 {' / '.join(values)}"
    return f"current tracking cost {' / '.join(values)}"


def _operating_economics_proof_surface(fact_text: str) -> str:
    items = _operating_economics_items(fact_text)
    if not items:
        return ""
    zh = _source_has_chinese(fact_text)
    selected = _unique_preserve_order(
        [
            _combined_cost_basis_item(items, zh=zh),
            _first_operating_match(items, r"budget|pilot|预算|试点"),
            _first_operating_match(
                items,
                r"subscription|pricing|discuss|订阅|付费|讨论",
                prefer_pattern=r"/month|range|discuss|pricing|订阅区间|付费|讨论",
                exclude_pattern=r"not a subscription commitment|不承诺订阅|不等于订阅",
            ),
            _first_operating_match(items, r"threshold|30%|review|missed|closed|下降|阈值|复盘|解释|不升|不增加"),
            _first_operating_match(items, r"friction|field|administrative|entry|pause|阻力|字段|录入|暂停"),
        ]
    )
    if not selected:
        selected = items[:3]
    separator = "，" if zh else ", "
    return separator.join(selected[:5])


def _field_values(
    lines: list[str],
    patterns: tuple[str, ...],
    *,
    exclude_label_patterns: tuple[str, ...] = (),
) -> list[str]:
    values: list[str] = []
    for line in lines:
        if ":" in line:
            label, value = line.split(":", 1)
        elif "：" in line:
            label, value = line.split("：", 1)
        else:
            continue
        lowered_label = label.lower()
        if any(pattern in lowered_label for pattern in exclude_label_patterns):
            continue
        if not any(pattern in lowered_label for pattern in patterns):
            continue
        value = value.strip()
        value = _clean_text(value)
        if value and value not in values:
            values.append(value)
    return values


def _first(values: list[str], fallback: str) -> str:
    for value in values:
        if value:
            return value
    return fallback


def _last(values: list[str], fallback: str) -> str:
    for value in reversed(values):
        if value:
            return value
    return fallback


def _select_primary_user(users: list[str], buyers: list[str], fallback: str) -> str:
    for value in users + buyers:
        lowered = value.lower()
        if any(token in lowered for token in ("owner", "manager", "lead", "负责人", "经理", "管理", "决策")):
            return value
    return _first(users or buyers, fallback)


def _looks_like_role_owner(value: str) -> bool:
    text = _strip_source_labels(value)
    lowered = text.lower()
    if not text:
        return False
    if len(text) > 96:
        return False
    if any(token in text for token in ("哪些", "什么", "为什么", "如何", "是否", "：")):
        return False
    if any(token in lowered for token in ("what ", "which ", "why ", "how ", "whether ", "status", "signal", "metric")):
        return False
    return bool(
        re.search(
            r"\b(owner|manager|lead|buyer|sponsor|operator|coordinator|director|stakeholder)\b|负责人|经理|管理者|决策者|预算|采购",
            text,
            flags=re.IGNORECASE,
        )
    )


def _select_continuation_owner(users: list[str], buyers: list[str], fallback: str) -> str:
    high_intent = ("owner", "lead", "buyer", "sponsor", "budget", "director", "负责人", "决策", "预算", "采购")
    for value in buyers + users:
        lowered = _strip_source_labels(value).lower()
        if _looks_like_role_owner(value) and any(token in lowered for token in high_intent):
            return _strip_source_labels(value)
    for value in buyers + users:
        if _looks_like_role_owner(value):
            return _strip_source_labels(value)
    return fallback


def _join(values: list[str], fallback: str) -> str:
    compact = [value for value in values if value]
    return "; ".join(compact[:4]) if compact else fallback


def _strip_source_labels(value: str) -> str:
    text = _clean_text(value)
    text = re.sub(r"\b(?:目标|Goal|Objective|Desired Outcome)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:当前替代方案|现有方式|Current substitute|Status quo)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:核心问题|问题|Problem)\s*[:：]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"核心问题不是[“\"].*?[”\"]\s*[，,]\s*而是\s*", "", text)
    text = re.sub(r"核心问题不是.*?而是\s*", "", text)
    text = re.sub(r"核心问题是\s*", "", text)
    text = re.sub(r"(^|\s)[：:；;，,]+\s*", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip("。；;:： ")
    return text


def _split_source_parts(value: str) -> list[str]:
    text = _strip_source_labels(value)
    parts = [
        _strip_source_labels(part)
        for part in re.split(r"[。；;]+", text)
        if _strip_source_labels(part)
    ]
    return parts or ([text] if text else [])


def _short_phrase(value: str, fallback: str, *, max_chars: int = 64) -> str:
    for part in _split_source_parts(value):
        if len(part) <= max_chars:
            return part
    parts = _split_source_parts(value)
    if not parts:
        return fallback
    words = re.split(r"\s+", parts[0])
    if len(words) > 1:
        shortened = " ".join(words[:10]).strip()
        if shortened:
            return shortened
    return parts[0][:max_chars].rstrip("，,。；; ") or fallback


def _proof_label_from_values(proof_target: str, product_goal: str, pain: str) -> str:
    def trim_explanatory_slash_tail(part: str) -> str:
        source_note_tail_pattern = (
            r"\s+/\s+(?:(?:repeated sampling|procurement paperwork|production rollout evidence)"
            r"[^.;。；\n]*(?:[.;。；]\s*)?|"
            r"[^,/.;。；\n]*\b(?:stated that|remain outside|outside this fixture|"
            r"not only move|procurement paperwork|production rollout)\b[^,/.;。；\n]*(?:[.;。；]\s*)?)"
        )
        return re.sub(source_note_tail_pattern, " ", part, flags=re.IGNORECASE)

    def compact_long_proof_part(part: str, max_chars: int = 180) -> str:
        part = trim_explanatory_slash_tail(part)
        if len(part) <= max_chars:
            return part
        chunks = [chunk.strip("，,。；; ") for chunk in re.split(r"[，；;]+", part) if chunk.strip("，,。；; ")]
        selected: list[str] = []
        for chunk in chunks:
            candidate = "，".join([*selected, chunk]) if selected else chunk
            if len(candidate) > max_chars:
                break
            selected.append(chunk)
        if selected:
            return "，".join(selected)
        return part[:max_chars].rstrip("，,。；; ")

    def usable_proof_part(part: str) -> bool:
        lowered = part.casefold()
        if not part:
            return False
        if _looks_like_operating_boundary_note(part):
            return False
        if "not a subscription commitment" in lowered and not _currency_values(part):
            return False
        return bool(
            re.search(
                r"\$|budget|pilot|subscription|cost|hour|threshold|review|workload|proof|evidence|signal|"
                r"30%|状态线|复盘|证据|信号|阈值|试点|预算|订阅|付费|成本|工时|工作量",
                part,
                flags=re.IGNORECASE,
            )
        )

    for part in _split_source_parts(proof_target):
        if usable_proof_part(part):
            return compact_long_proof_part(part)
    goal = _short_phrase(product_goal, "", max_chars=56)
    if goal:
        return goal
    return _short_phrase(pain, "source-grounded review proof", max_chars=56)


def _evidence_surface_from_values(*values: str, fallback: str, max_parts: int = 2) -> str:
    parts: list[str] = []
    for value in values:
        for part in _split_source_parts(value):
            if part and part not in parts:
                parts.append(part)
    if not parts:
        return fallback
    priority_patterns = (
        re.compile(r"risk|follow[-\s]?up|overdue|风险|漏项", flags=re.IGNORECASE),
        re.compile(r"proof|evidence|signal|review|证据|验证|信号|复盘", flags=re.IGNORECASE),
        re.compile(r"closure|completion|闭环", flags=re.IGNORECASE),
    )

    def priority_score(part: str) -> int:
        return sum((len(priority_patterns) - index) for index, pattern in enumerate(priority_patterns) if pattern.search(part))

    selected: list[str] = [parts[0]]
    prioritized = sorted(
        [(priority_score(part), index, part) for index, part in enumerate(parts[1:], start=1) if priority_score(part) > 0],
        key=lambda row: (-row[0], row[1]),
    )
    for _, _, part in prioritized:
        if part not in selected:
            selected.append(part)
        if len(selected) >= max_parts:
            break
    if len(selected) < max_parts:
        for part in parts[1:]:
            if part not in selected:
                selected.append(part)
            if len(selected) >= max_parts:
                break
    return " / ".join(selected)


def _proof_surface_from_goal_or_pain(*, proof_target: str, product_goal: str, pain: str) -> str:
    proof_surface = _evidence_surface_from_values(
        proof_target,
        product_goal,
        fallback="",
    )
    if proof_surface:
        return proof_surface
    return _evidence_surface_from_values(
        pain,
        fallback=_proof_label_from_values(proof_target, product_goal, pain),
    )


def _evidence_bridge_reference(goal_surface: str, proof_surface: str, *, zh: bool) -> str:
    if goal_surface and proof_surface and goal_surface == proof_surface:
        return "这条可复核证据线" if zh else "that reviewable evidence line"
    return proof_surface or goal_surface


def _open_truth_surface(source_text: str, unknowns: list[str]) -> str:
    if unknowns:
        return _join(unknowns, "source open truth remains review-bound")
    return (
        "真实用户验证、预算 owner 权限、付费意愿或持续使用证据仍未闭合"
        if _source_has_chinese(source_text)
        else "real user validation, budget-owner authority, willingness-to-pay, or sustained-use evidence remains open"
    )


def _build_business_judgment_synthesis(
    *,
    source_text: str,
    primary_user: str,
    continuation_owner: str,
    status_quo: str,
    pain: str,
    product_goal: str,
    proof_target: str,
    decision_phrase: str,
    truth_state: str,
    unknowns: list[str],
) -> dict[str, object]:
    problem_label = _short_phrase(pain, "source-defined operating gap")
    substitute_label = _short_phrase(status_quo, "current substitute")
    proof_label = _proof_label_from_values(proof_target, product_goal, pain)
    goal_label = _short_phrase(product_goal, proof_label)
    if _source_has_chinese(source_text):
        product_decision = f"为 {primary_user} 收敛 {goal_label}，因为 {substitute_label} 仍会留下 {problem_label}。"
        commercial_decision = f"{continuation_owner} 应围绕 {proof_label} 判断是否 {decision_phrase}。"
        acceptance_decision = f"验收要证明 {problem_label} 已被 {proof_label} 关闭，且不抬高源真相。"
    else:
        product_decision = f"Focus on {goal_label} for {primary_user} because {substitute_label} still leaves {problem_label}."
        commercial_decision = f"{continuation_owner} should judge {decision_phrase} around {proof_label}."
        acceptance_decision = f"Acceptance must prove {problem_label} is closed by {proof_label} without upgrading source truth."
    return {
        "product_decision": product_decision,
        "commercial_decision": commercial_decision,
        "acceptance_decision": acceptance_decision,
        "problem_label": problem_label,
        "substitute_label": substitute_label,
        "proof_label": proof_label,
        "goal_label": goal_label,
        "claim_ceiling": truth_state,
        "review_bound_items": unknowns,
    }


def _build_business_judgment_transformation(
    *,
    source_text: str,
    primary_user: str,
    continuation_owner: str,
    status_quo: str,
    pain: str,
    product_goal: str,
    proof_target: str,
    decision_phrase: str,
    truth_state: str,
    unknowns: list[str],
) -> dict[str, object]:
    problem_label = _short_phrase(pain, "source-defined operating gap", max_chars=72)
    substitute_label = _short_phrase(status_quo, "current substitute", max_chars=72)
    goal_surface = _evidence_surface_from_values(product_goal, proof_target, fallback=_proof_label_from_values(proof_target, product_goal, pain))
    proof_surface = _proof_surface_from_goal_or_pain(
        proof_target=proof_target,
        product_goal=product_goal,
        pain=pain,
    )
    proof_bridge = _evidence_bridge_reference(
        goal_surface,
        proof_surface,
        zh=_source_has_chinese(source_text),
    )
    proof_matches_goal = bool(goal_surface and proof_surface and goal_surface == proof_surface)
    open_truth = _open_truth_surface(source_text, unknowns)
    if _source_has_chinese(source_text):
        product_bet = (
            f"让 {primary_user} 围绕 {goal_surface} 获得可复盘的业务闭环，"
            f"而不是把 {problem_label} 继续留给人工补位。"
        )
        why_now = (
            f"现在值得推进，是因为 {substitute_label} 已能维持日常运转，"
            f"但仍不能稳定暴露 {problem_label}；P1/P2 需要先验证这个断点是否足以支撑继续投入。"
        )
        why_this_wedge = (
            f"首版切片应聚焦 {goal_surface}，因为它把 {primary_user} 的日常动作、"
            f"{proof_bridge} 与 {continuation_owner} 的继续 / 调整 / 暂停判断接到同一条证据线上。"
        )
        why_not_status_quo = (
            f"{substitute_label} 的问题不是只慢一点，而是无法稳定产出 {proof_surface}，"
            f"因此不能单独支撑 {decision_phrase} 判断。"
        )
        why_not_single_tool_or_service_substitute = (
            f"单点工具或人工服务可以补某个步骤，但只要 {problem_label}、{proof_bridge}"
            f"与 {continuation_owner} 的判断仍分离，就不能替代这个产品押注。"
        )
        proof_needed_for_next_investment = (
            f"下一轮投入需要看到 {proof_surface} 足以让 {continuation_owner} 明确选择 {decision_phrase}；"
            f"否则只能保持 P1/P2 探索态。"
        )
        if proof_matches_goal:
            reader_facing_summary = (
                f"当前 source 支持把 {goal_surface} 同时作为产品主论点和继续投入证据；"
                f"但 {open_truth}，所以不能升级为真实市场验证。"
            )
        else:
            reader_facing_summary = (
                f"当前 source 支持把 {goal_surface} 作为产品主论点，并把 {proof_surface} "
                f"作为继续投入证据；但 {open_truth}，所以不能升级为真实市场验证。"
            )
    else:
        product_bet = (
            f"Let {primary_user} operate around {goal_surface} as a reviewable business loop, "
            f"instead of leaving {problem_label} to manual recovery."
        )
        why_now = (
            f"Now is worth P1/P2 exploration because {substitute_label} keeps work moving but still fails to expose "
            f"{problem_label} reliably enough for an investment decision."
        )
        why_this_wedge = (
            f"The first wedge should focus on {goal_surface} because it connects {primary_user} work, {proof_bridge}, "
            f"and {continuation_owner}'s continue / revise / pause decision in one evidence line."
        )
        why_not_status_quo = (
            f"{substitute_label} is not merely slower; it does not reliably produce {proof_surface}, "
            f"so it cannot carry the {decision_phrase} decision alone."
        )
        why_not_single_tool_or_service_substitute = (
            f"A single tool or service substitute may patch one step, but it does not replace the product bet while "
            f"{problem_label}, {proof_bridge}, and {continuation_owner} judgment remain separated."
        )
        proof_needed_for_next_investment = (
            f"The next investment step needs {proof_surface} strong enough for {continuation_owner} to choose "
            f"{decision_phrase}; otherwise the claim remains P1/P2 exploration only."
        )
        if proof_matches_goal:
            reader_facing_summary = (
                f"The current source supports {goal_surface} as both the product thesis and continuation proof, "
                f"but {open_truth}; it must not be upgraded into real market validation."
            )
        else:
            reader_facing_summary = (
                f"The current source supports {goal_surface} as the product thesis and {proof_surface} as continuation proof, "
                f"but {open_truth}; it must not be upgraded into real market validation."
            )
    return {
        "product_bet": product_bet,
        "why_now": why_now,
        "why_this_wedge": why_this_wedge,
        "why_not_status_quo": why_not_status_quo,
        "why_not_single_tool_or_service_substitute": why_not_single_tool_or_service_substitute,
        "proof_needed_for_next_investment": proof_needed_for_next_investment,
        "claim_blocking_open_truth": open_truth,
        "reader_facing_summary": reader_facing_summary,
        "claim_ceiling": truth_state,
        "review_bound_items": unknowns,
    }


def _semantic_authoring_summary(spine: dict[str, Any]) -> dict[str, Any]:
    placement_summary = spine.get("placement_summary", {}) if isinstance(spine, dict) else {}
    units = spine.get("semantic_units", []) if isinstance(spine, dict) else []
    type_counts: dict[str, int] = {}
    placement_targets: dict[str, list[str]] = {}
    if isinstance(placement_summary, dict):
        for semantic_type, rows in placement_summary.items():
            typed_rows = rows if isinstance(rows, list) else []
            type_counts[str(semantic_type)] = len(typed_rows)
            placement_targets[str(semantic_type)] = [
                str(row.get("placement_target", "")).strip()
                for row in typed_rows
                if isinstance(row, dict) and str(row.get("placement_target", "")).strip()
            ]
    return {
        "artifact_id": spine.get("artifact_id", "p1-semantic-authoring-spine.v1") if isinstance(spine, dict) else "",
        "semantic_unit_count": len(units) if isinstance(units, list) else 0,
        "type_counts": type_counts,
        "placement_targets": placement_targets,
    }


def _derive_truth_state(lines: list[str], unknowns: list[str]) -> str:
    if unknowns:
        return "source-grounded-but-review-bound" if lines else "review-bound"
    return "source-grounded" if lines else "review-bound"


def _decision_phrase(source_text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", source_text):
        return "继续 / 调整 / 暂停"
    return "continue / revise / pause"


def _source_has_chinese(source_text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", source_text))


def _has_proof_signal(source_text: str, proof_values: list[str]) -> bool:
    if proof_values:
        return True
    return bool(
        re.search(
            r"proof|evidence|validation|signal|threshold|decision|review|pilot|quote|证明|证据|验证|信号|阈值|决策|评审|复盘|试点|报价",
            source_text,
            flags=re.IGNORECASE,
        )
    )


def _business_loss_sentence(
    *,
    source_text: str,
    primary_user: str,
    status_quo: str,
    pain: str,
    product_goal: str,
) -> str:
    status_quo = _short_phrase(status_quo, "current substitute", max_chars=72)
    pain = _short_phrase(pain, "source-defined operating gap", max_chars=72)
    product_goal = _short_phrase(product_goal, "source-defined product goal", max_chars=72)
    if _source_has_chinese(source_text):
        return (
            f"当前替代方式是 {status_quo}，它让 {primary_user} 持续承受 {pain}，"
            f"从而拖慢或削弱 {product_goal}。"
        )
    return (
        f"The current substitute is {status_quo}; it leaves {primary_user} exposed to {pain}, "
        f"which weakens or delays {product_goal}."
    )


def _spend_at_risk_sentence(
    *,
    source_text: str,
    continuation_owner: str,
    product_goal: str,
    proof_target: str,
) -> str:
    product_goal = _short_phrase(product_goal, "source-defined product goal", max_chars=72)
    proof_target = _proof_label_from_values(proof_target, product_goal, product_goal)
    if _source_has_chinese(source_text):
        return (
            f"{continuation_owner} 的投入主要是围绕 {product_goal} 的时间、流程变更和继续评审成本；"
            f"继续判断看 {proof_target}。"
        )
    return (
        f"{continuation_owner} is not risking abstract budget only; the commitment is time, workflow-change effort, "
        f"and continuation review around {product_goal}, which should continue only when {proof_target} is clear enough."
    )


def _substitute_pressure_sentence(
    *,
    source_text: str,
    status_quo: str,
    proof_target: str,
) -> str:
    status_quo = _short_phrase(status_quo, "current substitute", max_chars=72)
    proof_target = _proof_label_from_values(proof_target, proof_target, proof_target)
    if _source_has_chinese(source_text):
        return f"{status_quo} 可以临时维持现状，但不足以稳定产生 {proof_target}，因此不能作为首版产品论证的终点。"
    return (
        f"{status_quo} may keep the current process moving, but it does not reliably produce {proof_target}; "
        "therefore it is not enough as the first-version product argument."
    )


def _proof_threshold_sentence(
    *,
    source_text: str,
    proof_target: str,
    decision_phrase: str,
) -> str:
    proof_target = _proof_label_from_values(proof_target, proof_target, proof_target)
    if _source_has_chinese(source_text):
        return f"最小通过阈值是：评审者能用 {proof_target} 明确影响 `{decision_phrase}` 判断。"
    return f"The minimum threshold is that reviewers can use {proof_target} to change a `{decision_phrase}` decision."


def _build_business_completeness_driver(
    *,
    source_text: str,
    primary_user: str,
    continuation_owner: str,
    status_quo: str,
    pain: str,
    product_goal: str,
    proof_target: str,
    decision_phrase: str,
    truth_state: str,
    proof: list[str],
    unknowns: list[str],
) -> dict[str, object]:
    has_proof_signal = _has_proof_signal(source_text, proof)
    evidence_state = "partially-signal-backed" if has_proof_signal else "source-grounded-but-unvalidated"
    missing_external_evidence = (
        "真实 buyer / budget owner 反馈、外部使用验证、报价或继续投入证据"
        if _source_has_chinese(source_text)
        else "real buyer or budget-owner feedback, external usage validation, quote evidence, or continuation commitment"
    )
    unresolved_truth = _join(unknowns, missing_external_evidence)
    status_quo_label = _short_phrase(status_quo, "current substitute", max_chars=72)
    pain_label = _short_phrase(pain, "source-defined operating gap", max_chars=72)
    product_goal_label = _short_phrase(product_goal, "source-defined product goal", max_chars=72)
    proof_label = _proof_label_from_values(proof_target, product_goal, pain)

    return {
        "driver_id": BUSINESS_COMPLETENESS_DRIVER_ID,
        "business_loss_chain": {
            "pain_holder": primary_user,
            "status_quo_to_beat": status_quo_label,
            "business_pressure": pain_label,
            "business_outcome_at_risk": product_goal_label,
            "loss_chain": _business_loss_sentence(
                source_text=source_text,
                primary_user=primary_user,
                status_quo=status_quo,
                pain=pain,
                product_goal=product_goal,
            ),
        },
        "continuation_economics": {
            "continuation_owner": continuation_owner,
            "spend_or_commitment_at_risk": _spend_at_risk_sentence(
                source_text=source_text,
                continuation_owner=continuation_owner,
                product_goal=product_goal,
                proof_target=proof_target,
            ),
            "continuation_decision": decision_phrase,
            "decision_trigger": _commercial_judgment_sentence(
                source_text=source_text,
                continuation_owner=continuation_owner,
                proof_target=proof_label,
                decision_phrase=decision_phrase,
            ),
        },
        "substitute_pressure_map": {
            "current_substitute": status_quo_label,
            "why_not_enough": _substitute_pressure_sentence(
                source_text=source_text,
                status_quo=status_quo,
                proof_target=proof_target,
            ),
            "minimum_proof_to_beat": proof_label,
        },
        "proof_for_continue": {
            "source_signal_state": "source proof signal present" if has_proof_signal else "source proof signal missing",
            "proof_artifact": proof_label,
            "directional_threshold": _proof_threshold_sentence(
                source_text=source_text,
                proof_target=proof_target,
                decision_phrase=decision_phrase,
            ),
            "missing_external_evidence": unresolved_truth,
        },
        "commercial_claim_ceiling": {
            "evidence_confidence_state": evidence_state,
            "allowed_claim": "P1 business completeness is review-ready under current source evidence",
            "forbidden_upgrade": "real external validation, willingness-to-pay, owner sign-off, budget approval, or production readiness",
            "truth_state": truth_state,
        },
        "downstream_business_contract": {
            "p2_must_preserve": [
                "business loss chain",
                "continuation owner",
                "proof artifact for continue / revise / pause",
                "commercial claim ceiling",
            ],
            "p2_must_not_invent": [
                "validated willingness-to-pay",
                "real budget approval",
                "external market validation",
                "new product goal outside source",
            ],
            "review_bound_gaps": unknowns or [missing_external_evidence],
        },
    }


def _product_judgment_sentence(
    *,
    source_text: str,
    primary_user: str,
    product_goal: str,
    status_quo: str,
    pain: str,
) -> str:
    if _source_has_chinese(source_text):
        return (
            f"产品应围绕 {product_goal} 服务 {primary_user}，因为现有方式 {status_quo} "
            f"仍无法稳定解决 {pain}。"
        )
    return (
        f"The product should focus on {product_goal} for {primary_user} because {status_quo} "
        f"still leaves {pain} unresolved."
    )


def _commercial_judgment_sentence(
    *,
    source_text: str,
    continuation_owner: str,
    proof_target: str,
    decision_phrase: str,
) -> str:
    if _source_has_chinese(source_text):
        return f"{continuation_owner} 应在看完 {proof_target} 后，再判断是否 {decision_phrase}。"
    return f"{continuation_owner} should decide whether to {decision_phrase} after reviewing {proof_target}."


def _acceptance_meaning_sentence(
    *,
    source_text: str,
    primary_user: str,
    pain: str,
    proof_target: str,
) -> str:
    if _source_has_chinese(source_text):
        return f"验收应证明 {primary_user} 能从 {pain} 进入 {proof_target}，且不牺牲源真相边界。"
    return (
        f"Acceptance should prove {primary_user} can move from {pain} to {proof_target} "
        "without losing source-truth honesty."
    )


def build_product_source_direct_driver(
    source_text: str,
    *,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Compile a compact P1 product/source judgment surface.

    The driver intentionally stays generic: it preserves source-native words and
    records judgment questions before P1 stage/PRD writers assemble artifacts.
    """

    semantic_authoring_spine = build_semantic_authoring_spine(source_text)
    semantic_authoring_summary = _semantic_authoring_summary(semantic_authoring_spine)
    fact_text = _source_fact_text(source_text)
    lines = _source_bullets(fact_text)
    context = dict(context or {})
    users = _field_values(lines, ("target user", "user", "用户", "研究对象", "角色"))
    buyers = _field_values(lines, ("buyer", "budget", "owner", "manager", "review", "approver", "决策", "预算", "负责人", "评审", "审批", "采购"))
    substitutes = _field_values(lines, ("substitute", "status quo", "current", "替代", "现状", "人工", "paper"))
    pains = _field_values(lines, ("pain", "pressure", "problem", "问题", "痛点", "失控", "遗漏"))
    goals = _field_values(
        lines,
        ("goal", "business goal", "objective", "目标", "机会"),
        exclude_label_patterns=("非目标", "non-goal", "out of scope", "范围边界"),
    )
    proof = _field_values(lines, ("proof", "evidence", "validation", "signal", "证明", "验证", "信号"))
    mvp = _field_values(lines, ("mvp", "p0", "first", "首版", "最小", "wedge"))
    unknowns = _field_values(lines, ("unknown", "review-bound", "provisional", "待验证", "未知", "假设"))
    table_roles = _table_values(
        fact_text,
        ("User, Buyer, Operator", "Target Users", "目标用户", "研究对象", "Roles"),
        ("role", "角色"),
    )
    table_owner_roles = [
        role
        for role in table_roles
        if _looks_like_role_owner(role)
        and re.search(r"owner|lead|buyer|budget|sponsor|director|负责人|决策|预算|采购", role, flags=re.IGNORECASE)
    ]
    section_users = _section_items(fact_text, ("目标用户", "研究对象", "target user", "users", "roles"))
    section_substitutes = _section_items(fact_text, ("现状", "背景", "证据线索", "substitute", "status quo", "evidence"))
    section_pains = _section_items(fact_text, ("业务机会", "结构化问题", "问题清单", "痛点", "problem", "pain"))
    section_goals = _section_items(fact_text, ("产品/业务目标", "目标方向", "机会清单", "business goal", "objective", "desired outcome"))
    section_proof = _section_items(fact_text, ("证据线索", "验证对象", "判定信号", "evidence", "validation", "signal", "success signals"))
    operating_economics_proof = _operating_economics_proof_surface(fact_text)
    section_mvp = _section_items(fact_text, ("p0", "mvp", "必须有"))
    label_mvp = _label_block_items(fact_text, ("P0",), limit=8)
    section_unknowns = _section_items(
        fact_text,
        ("unknown", "provisional", "待验证", "未知", "需要后续补实"),
        exclude_heading_patterns=("provenance", "标记表", "marker", "ledger", "truth-state"),
    )
    packet_unknowns = _packet_open_truth_gap_items(source_text)
    users = users or table_roles or section_users
    buyers = _unique_preserve_order(table_owner_roles + buyers)
    substitutes = substitutes or section_substitutes
    pains = pains or section_pains
    goals = goals or section_goals
    proof = proof or section_proof
    if operating_economics_proof:
        zh = _source_has_chinese(fact_text)
        proof = _unique_preserve_order(
            [operating_economics_proof]
            + [
                item
                for item in proof
                if not _looks_like_operating_boundary_note(item)
                and _normalize_operating_item(item, zh=zh) == _strip_source_labels(item)
            ]
        )
    if label_mvp or section_mvp:
        mvp = label_mvp or section_mvp
    if section_unknowns or packet_unknowns:
        unknowns = section_unknowns + [item for item in packet_unknowns if item not in section_unknowns]
    if unknowns:
        proof = [item for item in proof if item not in unknowns]

    primary_user = _select_primary_user(users, buyers, "source-defined primary user")
    continuation_owner = _select_continuation_owner(users, buyers, _last(users, primary_user))
    status_quo = _join(substitutes, "source-defined current workaround or substitute")
    pain = _join(pains or goals, "source-defined product/business pressure")
    product_goal = _join(section_goals or goals or pains, "resolve the source-defined product pressure")
    decision_phrase = _decision_phrase(source_text)
    proof_fallback = (
        f"能改变 `{decision_phrase}` 判断的评审证据"
        if _source_has_chinese(source_text)
        else f"review-bound proof that changes a {decision_phrase} decision"
    )
    proof_target = _join(proof, proof_fallback)
    mvp_wedge = _join(mvp, "smallest source-grounded valuable wedge remains review-bound")
    truth_state = _derive_truth_state(lines, unknowns)
    business_completeness_driver = _build_business_completeness_driver(
        source_text=source_text,
        primary_user=primary_user,
        continuation_owner=continuation_owner,
        status_quo=status_quo,
        pain=pain,
        product_goal=product_goal,
        proof_target=proof_target,
        decision_phrase=decision_phrase,
        truth_state=truth_state,
        proof=proof,
        unknowns=unknowns,
    )
    business_judgment_synthesis = _build_business_judgment_synthesis(
        source_text=source_text,
        primary_user=primary_user,
        continuation_owner=continuation_owner,
        status_quo=status_quo,
        pain=pain,
        product_goal=product_goal,
        proof_target=proof_target,
        decision_phrase=decision_phrase,
        truth_state=truth_state,
        unknowns=unknowns,
    )
    business_judgment_transformation = _build_business_judgment_transformation(
        source_text=source_text,
        primary_user=primary_user,
        continuation_owner=continuation_owner,
        status_quo=status_quo,
        pain=pain,
        product_goal=product_goal,
        proof_target=proof_target,
        decision_phrase=decision_phrase,
        truth_state=truth_state,
        unknowns=unknowns,
    )

    forbidden_assumptions = [
        "Do not upgrade review-bound source facts into confirmed market truth.",
        "Do not let P2 invent product goal, business value, MVP wedge, or acceptance meaning.",
        f"Do not replace source-native language such as `{primary_user}` and `{pain}` with generic product-world labels.",
    ]
    if unknowns:
        forbidden_assumptions.append(f"Do not treat unresolved truth as closed: {_join(unknowns, 'source unknowns')}.")

    value_targets = [
        {
            "target": "product_judgment",
            "focus": "sharpen why this product exists and what substitute it must beat",
            "value_exit": "stop when the product argument changes downstream P2 design pressure or exposes a real source gap",
        },
        {
            "target": "commercial_judgment",
            "focus": "make continuation owner, proof artifact, and decision leverage explicit",
            "value_exit": "stop when another round cannot change continue / revise / pause reasoning under current source evidence",
        },
        {
            "target": "mvp_wedge",
            "focus": "protect the narrowest valuable slice and defer non-essential scope honestly",
            "value_exit": "stop when the first slice is designable without hiding review-bound truth",
        },
    ]

    return {
        "driver_id": DRIVER_ID,
        "source_truth_admission": {
            "truth_state": truth_state,
            "source_native_terms": [primary_user, continuation_owner, status_quo, pain, product_goal],
            "review_bound_items": unknowns,
            "claim_ceiling": "development/pre-production P1 readiness only; no market validation or owner sign-off claim",
        },
        "product_judgment": {
            "primary_user_or_buyer": primary_user,
            "product_goal": product_goal,
            "status_quo_to_beat": status_quo,
            "why_this_not_that": _product_judgment_sentence(
                source_text=source_text,
                primary_user=primary_user,
                product_goal=product_goal,
                status_quo=status_quo,
                pain=pain,
            ),
        },
        "commercial_judgment": {
            "continuation_owner": continuation_owner,
            "proof_that_changes_decision": proof_target,
            "decision_leverage": _commercial_judgment_sentence(
                source_text=source_text,
                continuation_owner=continuation_owner,
                proof_target=proof_target,
                decision_phrase=decision_phrase,
            ),
            "commercial_truth_state": truth_state,
        },
        "business_feasibility": {
            "feasible_wedge": mvp_wedge,
            "business_reality": pain,
            "feasibility_claim": "feasible for P2 exploration only within the current source evidence ceiling",
        },
        "mvp_wedge": {
            "narrowest_valuable_wedge": mvp_wedge,
            "must_protect": [primary_user, product_goal, proof_target],
            "defer_or_review_bound": unknowns or ["external validation and exact commercial evidence"],
        },
        "acceptance_meaning": {
            "acceptance_should_prove": _acceptance_meaning_sentence(
                source_text=source_text,
                primary_user=primary_user,
                pain=pain,
                proof_target=proof_target,
            ),
            "not_just": "field presence, CRUD completion, or clean workflow labels",
        },
        "open_truth_gap_routing": {
            "pre_p1_or_p1": unknowns,
            "p2_must_not_invent": ["product goal", "business value", "MVP wedge", "acceptance meaning"],
            "downstream_route": "return to P1 or pre-P1 if a missing source fact changes product judgment",
        },
        "business_completeness_driver": business_completeness_driver,
        "business_judgment_synthesis": business_judgment_synthesis,
        "business_judgment_transformation": business_judgment_transformation,
        "semantic_authoring_spine": semantic_authoring_spine,
        "semantic_authoring_summary": semantic_authoring_summary,
        "forbidden_downstream_assumptions": forbidden_assumptions,
        "value_deepening_targets": value_targets,
        "claim_ceiling": {
            "state": truth_state,
            "allowed": "P1 package quality under current source evidence",
            "forbidden": "validated market truth, real business-owner approval, production go-live, or budget confirmation",
        },
    }
