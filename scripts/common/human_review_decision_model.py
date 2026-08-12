#!/usr/bin/env python3
"""Validate and render structured Human Review decision models.

Agentic generation owns every decision, rationale, constraint, risk, question,
and evidence selection. This module only validates source binding and stable
shape, then renders Markdown without inventing semantic content.
"""

from __future__ import annotations

import re
from typing import Any

from common.human_review_terminology import (
    REVIEW_BOUND_DISPLAY,
    localize_review_terms,
    review_status_label,
    reviewer_label,
)


MODEL_SCHEMA = "wff.human-review-decision-model.v1"
ACTION_MODEL_SCHEMA = "wff.human-review-action-card-model.v1"
ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._-]*\Z")
MACHINE_ID_PATTERN = re.compile(r"\b(?:P[1-4]|ARCH|AC|WP|RQ)-[A-Z0-9][A-Z0-9._:-]*\b", re.IGNORECASE)


class HumanReviewDecisionModelError(ValueError):
    """The Agentic Human Review decision model is structurally invalid."""


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HumanReviewDecisionModelError(f"{field} must be an object")
    return value


def _text(value: object, field: str, *, minimum: int = 1, maximum: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) < minimum:
        raise HumanReviewDecisionModelError(f"{field} is missing or too short")
    if len(text) > maximum:
        raise HumanReviewDecisionModelError(f"{field} exceeds the bounded text limit")
    return text


def _strings(
    value: object,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = 12,
    item_minimum: int = 2,
) -> list[str]:
    if not isinstance(value, list):
        raise HumanReviewDecisionModelError(f"{field} must be a list")
    result: list[str] = []
    for index, item in enumerate(value, start=1):
        text = _text(item, f"{field}[{index}]", minimum=item_minimum, maximum=600)
        if text not in result:
            result.append(text)
    if len(result) < minimum or len(result) > maximum:
        raise HumanReviewDecisionModelError(
            f"{field} must contain between {minimum} and {maximum} unique items"
        )
    return result


def _identifier(value: object, field: str) -> str:
    identifier = _text(value, field, minimum=2, maximum=80)
    if not ID_PATTERN.fullmatch(identifier):
        raise HumanReviewDecisionModelError(
            f"{field} must start with a letter and use only letters, digits, '.', '_', or '-'"
        )
    return identifier


def _evidence_anchors(
    value: object,
    field: str,
    *,
    allowed_source_refs: set[str] | None,
    minimum: int = 1,
    maximum: int = 10,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise HumanReviewDecisionModelError(f"{field} must be a list")
    anchors: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(value, start=1):
        item = _object(raw, f"{field}[{index}]")
        label = _text(item.get("label"), f"{field}[{index}].label", minimum=3, maximum=160)
        source_ref = _text(
            item.get("source_ref"),
            f"{field}[{index}].source_ref",
            minimum=3,
            maximum=300,
        )
        if allowed_source_refs is not None and source_ref not in allowed_source_refs:
            raise HumanReviewDecisionModelError(
                f"{field}[{index}].source_ref is outside the accepted source packet"
            )
        identity = str(item.get("identity") or "").strip()
        if identity and len(identity) > 160:
            raise HumanReviewDecisionModelError(f"{field}[{index}].identity is too long")
        key = (label, source_ref, identity)
        if key in seen:
            continue
        seen.add(key)
        anchors.append(
            {"label": label, "source_ref": source_ref, "identity": identity}
        )
    if len(anchors) < minimum or len(anchors) > maximum:
        raise HumanReviewDecisionModelError(
            f"{field} must contain between {minimum} and {maximum} unique anchors"
        )
    return anchors


def _risks(value: object, field: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise HumanReviewDecisionModelError(f"{field} must be a list")
    risks: list[dict[str, str]] = []
    for index, raw in enumerate(value, start=1):
        item = _object(raw, f"{field}[{index}]")
        status = _text(item.get("status"), f"{field}[{index}].status")
        if status not in {"accepted", "review-bound"}:
            raise HumanReviewDecisionModelError(
                f"{field}[{index}].status must be accepted or review-bound"
            )
        risks.append(
            {
                "statement": _text(
                    item.get("statement"),
                    f"{field}[{index}].statement",
                    minimum=12,
                    maximum=700,
                ),
                "impact": _text(
                    item.get("impact"),
                    f"{field}[{index}].impact",
                    minimum=8,
                    maximum=700,
                ),
                "status": status,
            }
        )
    if not risks or len(risks) > 8:
        raise HumanReviewDecisionModelError(f"{field} must contain between 1 and 8 risks")
    return risks


def _review_questions(value: object, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HumanReviewDecisionModelError(f"{field} must be a list")
    questions: list[dict[str, Any]] = []
    for index, raw in enumerate(value, start=1):
        item = _object(raw, f"{field}[{index}]")
        question = _text(
            item.get("question"),
            f"{field}[{index}].question",
            minimum=10,
            maximum=500,
        )
        if "?" not in question and "？" not in question and "是否" not in question:
            raise HumanReviewDecisionModelError(
                f"{field}[{index}].question must be an explicit review question"
            )
        questions.append(
            {
                "question": question,
                "owner": _text(
                    item.get("owner"),
                    f"{field}[{index}].owner",
                    minimum=2,
                    maximum=120,
                ),
                "blocking": bool(item.get("blocking", False)),
            }
        )
    if not questions or len(questions) > 6:
        raise HumanReviewDecisionModelError(
            f"{field} must contain between 1 and 6 review questions"
        )
    return questions


def _section(
    raw: object,
    *,
    field: str,
    allowed_source_refs: set[str] | None,
) -> dict[str, Any]:
    item = _object(raw, field)
    return {
        "id": _identifier(item.get("id"), f"{field}.id"),
        "title": _text(item.get("title"), f"{field}.title", minimum=3, maximum=160),
        "decision": _text(
            item.get("decision"), f"{field}.decision", minimum=40, maximum=1800
        ),
        "affected_subjects": _strings(
            item.get("affected_subjects"),
            f"{field}.affected_subjects",
            minimum=1,
            maximum=12,
        ),
        "rationale": _strings(
            item.get("rationale"), f"{field}.rationale", minimum=1, maximum=6, item_minimum=12
        ),
        "constraints": _strings(
            item.get("constraints"),
            f"{field}.constraints",
            minimum=1,
            maximum=8,
            item_minimum=8,
        ),
        "risks": _risks(item.get("risks"), f"{field}.risks"),
        "review_questions": _review_questions(
            item.get("review_questions"), f"{field}.review_questions"
        ),
        "evidence_anchors": _evidence_anchors(
            item.get("evidence_anchors"),
            f"{field}.evidence_anchors",
            allowed_source_refs=allowed_source_refs,
        ),
    }


def _relationship(
    raw: object,
    *,
    field: str,
    allowed_source_refs: set[str] | None,
) -> dict[str, Any]:
    item = _object(raw, field)
    return {
        "id": _identifier(item.get("id"), f"{field}.id"),
        "title": _text(item.get("title"), f"{field}.title", minimum=3, maximum=160),
        "relationship": _text(
            item.get("relationship"),
            f"{field}.relationship",
            minimum=40,
            maximum=1800,
        ),
        "affected_subjects": _strings(
            item.get("affected_subjects"),
            f"{field}.affected_subjects",
            minimum=1,
            maximum=16,
        ),
        "evidence_anchors": _evidence_anchors(
            item.get("evidence_anchors"),
            f"{field}.evidence_anchors",
            allowed_source_refs=allowed_source_refs,
        ),
        "review_bound_impact": _text(
            item.get("review_bound_impact"),
            f"{field}.review_bound_impact",
            minimum=12,
            maximum=1000,
        ),
    }


def normalize_document_model(
    *,
    kind: str,
    value: object,
    allowed_source_refs: list[str] | None,
) -> dict[str, Any]:
    payload = _object(value, "review_model")
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise HumanReviewDecisionModelError("review_model.sections must be a list")
    minimum = 6 if kind == "prd-core" else 7
    if len(raw_sections) < minimum or len(raw_sections) > 16:
        raise HumanReviewDecisionModelError(
            f"review_model.sections must contain between {minimum} and 16 sections"
        )
    allowed = set(allowed_source_refs) if allowed_source_refs is not None else None
    sections = [
        _section(raw, field=f"review_model.sections[{index}]", allowed_source_refs=allowed)
        for index, raw in enumerate(raw_sections, start=1)
    ]
    ids = [section["id"] for section in sections]
    if len(ids) != len(set(ids)):
        raise HumanReviewDecisionModelError("review_model.sections ids must be unique")

    raw_relationships = payload.get("appendix_relationships")
    if not isinstance(raw_relationships, list) or not (2 <= len(raw_relationships) <= 8):
        raise HumanReviewDecisionModelError(
            "review_model.appendix_relationships must contain between 2 and 8 items"
        )
    relationships = [
        _relationship(
            raw,
            field=f"review_model.appendix_relationships[{index}]",
            allowed_source_refs=allowed,
        )
        for index, raw in enumerate(raw_relationships, start=1)
    ]
    relationship_ids = [item["id"] for item in relationships]
    if len(relationship_ids) != len(set(relationship_ids)):
        raise HumanReviewDecisionModelError(
            "review_model.appendix_relationships ids must be unique"
        )
    return {
        "schema_version": MODEL_SCHEMA,
        "projection_kind": kind,
        "sections": sections,
        "appendix_relationships": relationships,
    }


def _anchor_text(anchor: dict[str, str]) -> str:
    identity = f" / `{anchor['identity']}`" if anchor["identity"] else ""
    return (
        f"{localize_review_terms(anchor['label'])}"
        f"（`{anchor['source_ref']}`{identity}）"
    )


def render_document_model(model: dict[str, Any]) -> tuple[str, str]:
    main_sections: list[str] = []
    for section in model["sections"]:
        rationale = "；".join(
            localize_review_terms(item) for item in section["rationale"]
        )
        constraints = "；".join(
            localize_review_terms(item) for item in section["constraints"]
        )
        risks = "；".join(
            f"{localize_review_terms(item['statement'])}"
            f"（影响：{localize_review_terms(item['impact'])}；"
            f"状态：{review_status_label(item['status'])}）"
            for item in section["risks"]
        )
        questions = "\n".join(
            f"- {localize_review_terms(item['question'])}"
            f"（责任人：{reviewer_label(item['owner'])}；"
            f"{'阻断' if item['blocking'] else '非阻断'}）"
            for item in section["review_questions"]
        )
        subjects = "、".join(
            f"`{localize_review_terms(item)}`"
            for item in section["affected_subjects"]
        )
        main_sections.append(
            "\n\n".join(
                [
                    f"## {localize_review_terms(section['title'])}",
                    localize_review_terms(section["decision"]),
                    f"**影响对象。** {subjects}",
                    f"**为什么这样选择。** {rationale}",
                    f"**约束。** {constraints}",
                    f"**风险与例外。** {risks}",
                    f"**请审阅。**\n{questions}",
                ]
            )
        )

    appendix_sections: list[str] = []
    for relationship in model["appendix_relationships"]:
        subjects = "、".join(
            f"`{localize_review_terms(item)}`"
            for item in relationship["affected_subjects"]
        )
        anchors = "\n".join(
            f"- {_anchor_text(anchor)}" for anchor in relationship["evidence_anchors"]
        )
        appendix_sections.append(
            "\n\n".join(
                [
                    f"### {localize_review_terms(relationship['title'])}",
                    localize_review_terms(relationship["relationship"]),
                    f"**影响对象。** {subjects}",
                    f"**证据锚点。**\n{anchors}",
                    f"**{REVIEW_BOUND_DISPLAY}的影响。** "
                    f"{localize_review_terms(relationship['review_bound_impact'])}",
                ]
            )
        )
    return "\n\n".join(main_sections), "\n\n".join(appendix_sections)


def _card(
    raw: object,
    *,
    field: str,
    allowed_source_refs: set[str] | None,
) -> dict[str, Any]:
    item = _object(raw, field)
    components = _strings(
        item.get("component_ids"),
        f"{field}.component_ids",
        minimum=1,
        maximum=80,
    )
    operations = _strings(
        item.get("operation_ids"),
        f"{field}.operation_ids",
        minimum=1,
        maximum=30,
    )
    return {
        "id": _identifier(item.get("id"), f"{field}.id"),
        "title": _text(item.get("title"), f"{field}.title", minimum=3, maximum=160),
        "summary": _text(item.get("summary"), f"{field}.summary", minimum=12, maximum=500),
        "component_ids": components,
        "operation_ids": operations,
        "goal": _text(item.get("goal"), f"{field}.goal", minimum=30, maximum=1200),
        "implementation_decisions": _strings(
            item.get("implementation_decisions"),
            f"{field}.implementation_decisions",
            minimum=1,
            maximum=8,
            item_minimum=15,
        ),
        "constraints": _strings(
            item.get("constraints"),
            f"{field}.constraints",
            minimum=1,
            maximum=8,
            item_minimum=8,
        ),
        "failure_conditions": _strings(
            item.get("failure_conditions"),
            f"{field}.failure_conditions",
            minimum=1,
            maximum=10,
            item_minimum=8,
        ),
        "proof_obligations": _strings(
            item.get("proof_obligations"),
            f"{field}.proof_obligations",
            minimum=1,
            maximum=10,
            item_minimum=10,
        ),
        "review_questions": _review_questions(
            item.get("review_questions"), f"{field}.review_questions"
        ),
        "risks": _risks(item.get("risks"), f"{field}.risks"),
        "evidence_anchors": _evidence_anchors(
            item.get("evidence_anchors"),
            f"{field}.evidence_anchors",
            allowed_source_refs=allowed_source_refs,
        ),
    }


def normalize_action_card_model(
    *,
    value: object,
    required_component_ids: list[str],
    allowed_source_refs: list[str] | None,
) -> dict[str, Any]:
    payload = _object(value, "review_model")
    raw_cards = payload.get("cards")
    if not isinstance(raw_cards, list) or not raw_cards:
        raise HumanReviewDecisionModelError("review_model.cards must be a non-empty list")
    if len(raw_cards) > min(12, len(required_component_ids)):
        raise HumanReviewDecisionModelError("review_model.cards is not sufficiently grouped")
    allowed = set(allowed_source_refs) if allowed_source_refs is not None else None
    cards = [
        _card(raw, field=f"review_model.cards[{index}]", allowed_source_refs=allowed)
        for index, raw in enumerate(raw_cards, start=1)
    ]
    ids = [card["id"] for card in cards]
    if len(ids) != len(set(ids)):
        raise HumanReviewDecisionModelError("review_model.cards ids must be unique")
    observed = [component for card in cards for component in card["component_ids"]]
    expected = sorted(required_component_ids)
    if sorted(observed) != expected:
        missing = sorted(set(expected) - set(observed))
        duplicate = sorted({item for item in observed if observed.count(item) > 1})
        unknown = sorted(set(observed) - set(expected))
        raise HumanReviewDecisionModelError(
            "review_model.cards component coverage mismatch: "
            f"missing={missing[:12]} duplicate={duplicate[:12]} unknown={unknown[:12]}"
        )
    return {
        "schema_version": ACTION_MODEL_SCHEMA,
        "projection_kind": "action-card-set",
        "cards": cards,
    }


def render_action_card_model(model: dict[str, Any]) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for card in model["cards"]:
        decisions = "；".join(
            localize_review_terms(item) for item in card["implementation_decisions"]
        )
        constraints = "；".join(
            localize_review_terms(item) for item in card["constraints"]
        )
        failures = "；".join(
            localize_review_terms(item) for item in card["failure_conditions"]
        )
        proofs = "；".join(
            localize_review_terms(item) for item in card["proof_obligations"]
        )
        questions = "；".join(
            f"{localize_review_terms(item['question'])}"
            f"（责任人：{reviewer_label(item['owner'])}；"
            f"{'阻断' if item['blocking'] else '非阻断'}）"
            for item in card["review_questions"]
        )
        risks = "；".join(
            f"{localize_review_terms(item['statement'])}"
            f"（影响：{localize_review_terms(item['impact'])}；"
            f"状态：{review_status_label(item['status'])}）"
            for item in card["risks"]
        )
        operations = "、".join(
            f"`{localize_review_terms(item)}`" for item in card["operation_ids"]
        )
        anchors = "\n".join(
            f"- {_anchor_text(anchor)}" for anchor in card["evidence_anchors"]
        )
        main = "\n\n".join(
            [
                f"**目标。** {localize_review_terms(card['goal'])}",
                f"**实施判断。** {decisions}。约束：{constraints}",
                f"**失败条件。** {failures}",
                f"**审阅与证明。** {proofs}。请确认：{questions}",
            ]
        )
        appendix = "\n\n".join(
            [
                "### 工程责任与操作关系",
                f"本卡围绕 {operations} 组织实施责任；组件身份保留在结构化模型中，不作为人类正文清单。",
                f"**证据锚点。**\n{anchors}",
                "### 风险、证明与待决问题",
                f"{risks}。证明义务：{proofs}。待确认问题：{questions}",
            ]
        )
        rendered.append(
            {
                "id": card["id"],
                "title": localize_review_terms(card["title"]),
                "summary": localize_review_terms(card["summary"]),
                "component_ids": card["component_ids"],
                "operation_ids": card["operation_ids"],
                "main_markdown": main,
                "appendix_markdown": appendix,
                "decision_model": card,
            }
        )
    return rendered
