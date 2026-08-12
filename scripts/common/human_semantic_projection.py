#!/usr/bin/env python3
"""Generate source-bound, human-first PRD/ESP/Action Card projections for v1.6.

This is a read-only companion lane. It reorganizes existing phase truth for
human review, keeps complete engineering identity coverage in a machine-only
sidecar, and never changes P1-P4 canonical state or claim ceilings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common.human_review_architecture_reconstruction import (
    ArchitectureReconstructionInputError,
    discover_reconstruction_input,
    reconstruction_receipt,
    validate_reconstruction_conflict_coverage,
)
from common.human_review_decision_model import (
    HumanReviewDecisionModelError,
    normalize_action_card_model,
    normalize_document_model,
    render_action_card_model,
    render_document_model,
)
from common.human_review_decision_quality import (
    audit_projection,
    audit_summary,
    decision_quality_report_path,
    repair_feedback,
    source_anchor_terms,
    validate_decision_quality_report,
    write_decision_quality_report,
)


SCHEMA_VERSION = "wff.human-semantic-projection.v5"
IDENTITY_INDEX_SCHEMA = "wff.human-semantic-identity-index.v1"
PROJECTION_KINDS = ("prd-core", "esp-core", "action-card-set")
ID_PATTERN = re.compile(r"\b(?:P[1-4]|ARCH|AC|WP|RQ)-[A-Z0-9][A-Z0-9._:-]*\b")
ACTION_COMPONENT_PATTERN = re.compile(r"\bP2-CMP-[A-Z0-9._:-]+\b")
MARKDOWN_HEADING_PATTERN = re.compile(r"^#{2,5}\s+(.+?)\s*$", re.MULTILINE)
CODE_ONLY_LINE_PATTERN = re.compile(
    r"^(?:[-*+]\s+|\d+[.)]\s+)?(?:`[^`]+`(?:\s*[,，、;；|/]\s*)?)+[。.]?$"
)
FORBIDDEN_MAIN_MARKERS = (
    "文档元数据",
    "可追溯性命名",
    "Trace Registry",
    "Source Artifacts",
    "上游绑定",
    "必需来源",
    "required_source_ids",
    "source_sufficiency_status",
    "component_id：",
    "component_id:",
)
SEMANTIC_COVERAGE = {
    "prd-core": {
        "business-problem-and-value": ("业务", "问题", "价值", "经营压力"),
        "roles-and-responsibility": ("角色", "责任", "接待", "兽医", "经理"),
        "workflow-and-scenarios": ("场景", "流程", "交接", "动作", "状态"),
        "scope-and-exclusions": ("范围", "首版", "排除", "边界"),
        "success-and-continuation": ("验收", "指标", "持续使用", "继续", "调整", "暂停"),
        "review-and-claim-boundary": ("评审", "主张", "证据", "review-bound"),
    },
    "esp-core": {
        "architecture-and-boundaries": ("架构", "分层", "边界"),
        "modules-and-ownership": ("模块", "服务", "责任", "归属", "写入", "读取"),
        "state-invariants-and-failure": ("状态", "不变量", "失败", "阻塞", "迁移"),
        "flow-and-handoffs": ("流程", "序列", "交接", "调用"),
        "data-interfaces-and-contracts": ("数据", "接口", "契约", "持久化", "schema"),
        "security-and-audit": ("权限", "审计", "租户", "安全"),
        "implementation-proof-and-risk": ("实施", "测试", "风险", "review-bound", "证据"),
    },
}
FORBIDDEN_APPENDIX_LABELS = (
    "完整 ID 索引",
    "必需 ID 原样清单",
    "required_ids 原样索引",
    "权威与身份清单",
)
APPENDIX_SEMANTIC_TERMS = {
    "prd-core": ("需求", "验收", "场景", "来源", "证据", "关系", "影响", "review-bound"),
    "esp-core": ("组件", "操作", "契约", "责任", "风险", "测试", "关系", "影响", "review-bound"),
    "action-card-set": ("组件", "操作", "责任", "测试", "风险", "证明", "待决", "review-bound"),
}


class HumanSemanticProjectionError(ValueError):
    """The candidate is not a valid human semantic projection."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_case_file(case_root: Path, ref: str) -> Path:
    root = case_root.resolve()
    path = (root / ref).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise HumanSemanticProjectionError(f"projection source is missing or unsafe: {ref}")
    return path


def _validation_card_refs(case_root: Path) -> list[str]:
    validation_path = _safe_case_file(case_root, "phase-3/action-cards/validation.json")
    try:
        payload = json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HumanSemanticProjectionError(f"Action Card validation is unreadable: {exc}") from exc
    if payload.get("passed") is not True or not isinstance(payload.get("cards"), list):
        raise HumanSemanticProjectionError("Action Card validation must report passed=true with cards")
    root = case_root.resolve()
    refs: list[str] = []
    for index, raw in enumerate(payload["cards"], start=1):
        candidate = Path(str(raw))
        path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
            raise HumanSemanticProjectionError(f"Action Card validation path {index} is unsafe")
        refs.append(path.relative_to(root).as_posix())
    if not refs:
        raise HumanSemanticProjectionError("Action Card validation contains no cards")
    return refs


def projection_source_refs(case_root: Path, kind: str) -> list[str]:
    if kind == "prd-core":
        refs = [
            "phase-1/phase-1-product-requirements-document-main-document.md",
            "phase-1/phase1-business-release-truth-pack.json",
            "phase-1/.phase1-evidence/p1-semantic-authoring-spine.json",
            "phase-1/phase1-operating-baseline-model.json",
        ]
    elif kind == "esp-core":
        refs = [
            "phase-2/engineering-spec-pack.md",
            "phase-2/.phase2-evidence/implementation-component-catalog.json",
            "phase-2/.phase2-evidence/operation-behavior-semantics.json",
            "phase-2/.phase2-evidence/p1-value-to-p2-operation-resolution-matrix.json",
            "phase-2/stage-01-architecture-definition-and-boundary-setting.claim-control.json",
        ]
        try:
            reconstruction = discover_reconstruction_input(case_root)
        except ArchitectureReconstructionInputError as exc:
            raise HumanSemanticProjectionError(
                f"optional architecture reconstruction input is invalid: {exc}"
            ) from exc
        if reconstruction is not None:
            refs.append(str(reconstruction["ref"]))
    elif kind == "action-card-set":
        refs = ["phase-3/action-cards/validation.json", *_validation_card_refs(case_root)]
        for optional in (
            "phase-3/action-card-report.json",
            "phase-3/.phase3-review/action-card-readiness-summary.json",
            "phase-3/.phase3-review/action-card-execution-map.json",
        ):
            path = (case_root.resolve() / optional).resolve()
            if path.is_file() and not path.is_symlink() and path.is_relative_to(case_root.resolve()):
                refs.append(optional)
    else:
        raise HumanSemanticProjectionError(f"unsupported semantic projection kind: {kind}")
    for ref in refs:
        _safe_case_file(case_root, ref)
    return list(dict.fromkeys(refs))


def source_receipt(case_root: Path, refs: list[str]) -> dict[str, str]:
    return {ref: sha256_file(_safe_case_file(case_root, ref)) for ref in refs}


def _required_ids(case_root: Path, kind: str, refs: list[str]) -> list[str]:
    values: set[str] = set()
    for ref in refs:
        text = _safe_case_file(case_root, ref).read_text(encoding="utf-8")
        if kind == "action-card-set":
            values.update(ACTION_COMPONENT_PATTERN.findall(text))
            match = re.search(r"(P2-CMP-[A-Z0-9._:-]+)-action-card\.md$", ref, re.IGNORECASE)
            if match:
                values.add(match.group(1).upper())
        else:
            values.update(ID_PATTERN.findall(text))
    if kind == "prd-core":
        values = {item for item in values if item.startswith("P1-")}
    elif kind == "esp-core":
        values = {item for item in values if item.startswith(("P1-", "P2-", "ARCH-"))}
    if not values:
        raise HumanSemanticProjectionError(f"{kind} source packet exposes no required identities")
    return sorted(values)


def _source_blocks(case_root: Path, refs: list[str], *, max_chars: int) -> list[str]:
    blocks: list[str] = []
    total = 0
    for ref in refs:
        text = _safe_case_file(case_root, ref).read_text(encoding="utf-8")
        total += len(text)
        if total > max_chars:
            raise HumanSemanticProjectionError(
                f"projection source packet exceeds configured character ceiling ({max_chars})"
            )
        blocks.append(f"\n## SOURCE: {ref}\n{text}")
    return blocks


def _base_prompt(kind: str, required_ids: list[str], refs: list[str]) -> list[str]:
    common = [
        "直接使用简体中文生成面向产品、架构和交付审阅者的结构化决策模型。",
        "不要生成 Markdown。Workflow 会从已验收的 review_model 确定性渲染 Markdown 和 HTML。",
        "不要翻译或复制 canonical 文档结构；请按读者需要重新组织决策、理由、约束、风险、审阅问题和证据锚点。",
        "不得发明输入材料没有支持的业务、架构或实现事实。机器状态继续使用 review-bound；面向审阅人的中文正文统一写‘待审阅确认’，不要显示 raw review-bound、受评审约束或人类审阅者。",
        "每个 evidence_anchor.source_ref 必须严格复制允许来源列表中的一个路径；不得引用 packet、queue、lease、评分或模型内部信息。",
        "每个核心决策必须点名来源支撑的对象/角色/操作/状态，给出当前选择、理由、约束、风险/例外、可检查证据，以及至少一个明确可回答的审阅问题。",
        "完整 machine identity coverage 由 Workflow 单独保存，不要为覆盖而把编号写入自然语言字段。",
        "允许的来源路径：",
        json.dumps(refs, ensure_ascii=False),
    ]
    if kind == "prd-core":
        return [
            *common,
            "review_model.sections 使用 6 到 14 项，覆盖业务问题与价值、角色责任、场景/交接、首版范围、验收/持续使用以及评审主张边界。",
            "每个 section 决定一件审阅者可以同意、反对或修改的产品事项；不要重复‘核心判断’或只写抽象闭环。",
            "review_model.appendix_relationships 使用 2 到 6 项，解释需求、场景、验收、证据和待审阅确认事项之间的关系。",
        ]
    if kind == "esp-core":
        return [
            *common,
            "review_model.sections 使用 7 到 16 项，覆盖架构边界、模块责任、状态/不变量/失败、关键交接、数据接口、权限审计及实施证明风险。",
            "ESP 决策必须点名模块、聚合、服务、操作、状态或接口，并说明为什么采用当前方案、失败或权衡是什么、架构师需要回答什么。",
            "若允许来源中包含 `.wff/architecture-reconstruction/review-input.json`，必须使用其中的架构树、责任、实现意图、变更影响和保证机制归属来丰富决策；每个 open_conflicts.id 必须作为 evidence_anchor.identity 出现在至少一个明确审阅问题所在 section 中。不得自动解决冲突。",
            "review_model.appendix_relationships 使用 2 到 8 项，解释组件到操作、契约、状态、测试和风险的关系。",
        ]
    return [
        *common,
        "review_model.cards 按业务/实施责任把底层组件组织为通常 4 到 8 张、最多 12 张人类行动卡，不得一组件一张主读卡。",
        "每张卡必须包含 goal、implementation_decisions、constraints、failure_conditions、proof_obligations、risks、review_questions 和 evidence_anchors。",
        "卡片标题必须是人类可理解的实施责任，例如‘管理复诊任务’，不能是组件 ID。",
        "以下 required component identities 必须且只能出现在一张卡的 component_ids 中：",
        json.dumps(required_ids, ensure_ascii=False),
    ]


def _document_model_shape() -> dict[str, Any]:
    evidence = {"label": "source-grounded evidence", "source_ref": "allowed/path.json", "identity": "optional exact identity"}
    risk = {"statement": "concrete risk or exception", "impact": "decision impact", "status": "accepted|review-bound"}
    question = {"question": "explicit review question?", "owner": "review owner", "blocking": True}
    return {
        "sections": [
            {
                "id": "anchor-safe-id",
                "title": "human-readable section title",
                "decision": "current concrete decision",
                "affected_subjects": ["named subject"],
                "rationale": ["why this decision exists"],
                "constraints": ["constraint or invariant"],
                "risks": [risk],
                "review_questions": [question],
                "evidence_anchors": [evidence],
            }
        ],
        "appendix_relationships": [
            {
                "id": "relationship-id",
                "title": "relationship title",
                "relationship": "how responsibilities, evidence, or contracts relate",
                "affected_subjects": ["named subject"],
                "evidence_anchors": [evidence],
                "review_bound_impact": "what remains unresolved and why it matters",
            }
        ],
    }


def _action_model_shape() -> dict[str, Any]:
    evidence = {"label": "source-grounded evidence", "source_ref": "allowed/action-card.md", "identity": "optional exact identity"}
    return {
        "cards": [
            {
                "id": "human-card-id",
                "title": "human-readable responsibility",
                "summary": "one-sentence implementation responsibility",
                "component_ids": ["P2-CMP-..."],
                "operation_ids": ["operation name"],
                "goal": "concrete implementation goal",
                "implementation_decisions": ["current implementation decision"],
                "constraints": ["invariant or boundary"],
                "failure_conditions": ["specific failure condition"],
                "proof_obligations": ["specific test or runtime proof"],
                "risks": [{"statement": "risk", "impact": "impact", "status": "accepted|review-bound"}],
                "review_questions": [{"question": "explicit implementation review question?", "owner": "review owner", "blocking": True}],
                "evidence_anchors": [evidence],
            }
        ]
    }


def _prompt(case_root: Path, kind: str, refs: list[str], required_ids: list[str], *, max_chars: int) -> str:
    schema = {
        "document_title": "string",
        "reader_summary": "string",
        "review_model": _action_model_shape() if kind == "action-card-set" else _document_model_shape(),
        "fidelity_review": {"status": "accepted|review-bound", "rationale": "string"},
    }
    return "\n".join(
        [
            *_base_prompt(kind, required_ids, refs),
            "只返回一个 JSON 对象，不要代码围栏、Markdown 正文或额外解释。输出结构：",
            json.dumps(schema, ensure_ascii=False),
            *_source_blocks(case_root, refs, max_chars=max_chars),
        ]
    )


def _parse_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    candidate = re.sub(r"^```(?:json)?\s*\n", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\n```\s*$", "", candidate)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise HumanSemanticProjectionError(f"projection response is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise HumanSemanticProjectionError("projection response must be a JSON object")
    return payload


def _text(payload: dict[str, Any], key: str, *, minimum: int = 1) -> str:
    value = str(payload.get(key) or "").strip()
    if len(value) < minimum:
        raise HumanSemanticProjectionError(f"projection {key} is missing or too short")
    return value


def _fidelity(payload: dict[str, Any]) -> dict[str, str]:
    review = payload.get("fidelity_review")
    if not isinstance(review, dict):
        raise HumanSemanticProjectionError("projection fidelity_review is missing")
    status = str(review.get("status") or "")
    rationale = str(review.get("rationale") or "").strip()
    if status not in {"accepted", "review-bound"} or not rationale:
        raise HumanSemanticProjectionError("projection fidelity_review is invalid")
    return {"status": status, "rationale": rationale}


def _markdown_headings(markdown: str) -> list[str]:
    return [match.group(1).strip() for match in MARKDOWN_HEADING_PATTERN.finditer(markdown)]


def _semantic_coverage(kind: str, markdown: str) -> list[str]:
    lowered = markdown.lower()
    return [
        topic
        for topic, terms in SEMANTIC_COVERAGE[kind].items()
        if not any(term.lower() in lowered for term in terms)
    ]


def _bare_identity_lines(markdown: str) -> list[str]:
    bare: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if CODE_ONLY_LINE_PATTERN.fullmatch(line):
            bare.append(line)
            continue
        content = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", line)
        identities = ID_PATTERN.findall(content)
        if not identities:
            continue
        remainder = ID_PATTERN.sub("", content)
        remainder = re.sub(r"[`*_.,;:：、，；/|()\[\]\s-]+", "", remainder)
        if len(remainder) <= 4:
            bare.append(line)
    return bare


def _prose_lines(markdown: str) -> list[str]:
    prose: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "|", "```")):
            continue
        if _bare_identity_lines(line):
            continue
        plain = re.sub(r"[`*_>\[\]()#-]", "", line).strip()
        if len(plain) >= 20 and re.search(r"[\u4e00-\u9fff]", plain):
            prose.append(plain)
    return prose


def _validate_appendix_quality(kind: str, appendix: str, *, card_index: int | None = None) -> None:
    label = f"human Action Card {card_index} appendix" if card_index is not None else f"{kind} appendix"
    forbidden = [item for item in FORBIDDEN_APPENDIX_LABELS if item in appendix]
    if forbidden:
        raise HumanSemanticProjectionError(
            f"{label} exposes a machine identity index as human content: {', '.join(forbidden)}"
        )
    headings = _markdown_headings(appendix)
    minimum_headings = 1 if card_index is not None else 2
    if len(headings) < minimum_headings:
        raise HumanSemanticProjectionError(f"{label} lacks semantic sections")
    bare_lines = _bare_identity_lines(appendix)
    nonempty = [line for line in appendix.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if len(bare_lines) >= 4 or (nonempty and len(bare_lines) / len(nonempty) > 0.2):
        raise HumanSemanticProjectionError(
            f"{label} is dominated by naked machine identities ({len(bare_lines)} lines)"
        )
    required_prose = 1 if card_index is not None else 2
    if len(_prose_lines(appendix)) < required_prose:
        raise HumanSemanticProjectionError(f"{label} lacks explanatory prose")
    semantic_terms = APPENDIX_SEMANTIC_TERMS["action-card-set" if card_index is not None else kind]
    matched = {term for term in semantic_terms if term.lower() in appendix.lower()}
    minimum_terms = 2 if card_index is not None else 3
    if len(matched) < minimum_terms:
        raise HumanSemanticProjectionError(
            f"{label} does not explain enough relationships, evidence, or review impact"
        )


def _machine_identity_index(required_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": IDENTITY_INDEX_SCHEMA,
        "visibility": "machine-only",
        "count": len(required_ids),
        "identities": list(required_ids),
    }


def _validate_rendered_document(
    kind: str,
    *,
    title: str,
    summary: str,
    main: str,
    appendix: str,
    required_ids: list[str],
    review_model: dict[str, Any],
    fidelity_review: dict[str, str],
) -> dict[str, Any]:
    if len(main) < 300 or len(appendix) < 100:
        raise HumanSemanticProjectionError("rendered Human Review document is too thin")
    headings = _markdown_headings(main)
    minimum_headings = 6 if kind == "prd-core" else 7
    if len(headings) < minimum_headings:
        raise HumanSemanticProjectionError(
            f"human main document is over-compressed: {len(headings)} headings, expected at least {minimum_headings}"
        )
    normalized_headings = [
        re.sub(r"^\d+(?:\.\d+)*[.、:：]?\s*", "", item).strip()
        for item in headings
    ]
    repeated = sorted(
        {item for item in normalized_headings if normalized_headings.count(item) > 2}
    )
    if repeated:
        raise HumanSemanticProjectionError(
            "human main document repeats generic headings instead of adding meaning: "
            + ", ".join(repeated)
        )
    missing_topics = _semantic_coverage(kind, main)
    if missing_topics:
        raise HumanSemanticProjectionError(
            "human main document misses semantic review coverage: "
            + ", ".join(missing_topics)
        )
    leaked = [marker for marker in FORBIDDEN_MAIN_MARKERS if marker in main]
    if leaked:
        raise HumanSemanticProjectionError(
            "human main document still exposes machine/control sections: "
            + ", ".join(leaked)
        )
    main_ids = sum(1 for identity in required_ids if identity in main)
    if main_ids > max(10, len(required_ids) // 3):
        raise HumanSemanticProjectionError(
            "too many engineering identities remain in the human main document"
        )
    appendix_ids = sum(1 for identity in required_ids if identity in appendix)
    if appendix_ids > max(12, len(required_ids) // 8):
        raise HumanSemanticProjectionError(
            "human appendix reproduces too much of the machine identity index"
        )
    _validate_appendix_quality(kind, appendix)
    return {
        "document_title": title,
        "reader_summary": summary,
        "review_model": review_model,
        "main_markdown": main,
        "appendix_markdown": appendix,
        "fidelity_review": fidelity_review,
    }


def _validate_document(
    kind: str,
    payload: dict[str, Any],
    required_ids: list[str],
    allowed_source_refs: list[str] | None,
) -> dict[str, Any]:
    title = _text(payload, "document_title", minimum=3)
    summary = _text(payload, "reader_summary", minimum=20)
    try:
        review_model = normalize_document_model(
            kind=kind,
            value=payload.get("review_model"),
            allowed_source_refs=allowed_source_refs,
        )
        main, appendix = render_document_model(review_model)
    except HumanReviewDecisionModelError as exc:
        raise HumanSemanticProjectionError(f"structured review model is invalid: {exc}") from exc
    return _validate_rendered_document(
        kind,
        title=title,
        summary=summary,
        main=main,
        appendix=appendix,
        required_ids=required_ids,
        review_model=review_model,
        fidelity_review=_fidelity(payload),
    )


def _validate_action_cards(
    payload: dict[str, Any],
    required_ids: list[str],
    allowed_source_refs: list[str] | None,
) -> dict[str, Any]:
    title = _text(payload, "document_title", minimum=3)
    summary = _text(payload, "reader_summary", minimum=20)
    try:
        review_model = normalize_action_card_model(
            value=payload.get("review_model"),
            required_component_ids=required_ids,
            allowed_source_refs=allowed_source_refs,
        )
        cards = render_action_card_model(review_model)
    except HumanReviewDecisionModelError as exc:
        raise HumanSemanticProjectionError(f"structured Action Card model is invalid: {exc}") from exc

    for index, card in enumerate(cards, start=1):
        main = str(card["main_markdown"])
        appendix = str(card["appendix_markdown"])
        if len(card["summary"]) < 10 or len(main) < 120 or len(appendix) < 80:
            raise HumanSemanticProjectionError(
                f"rendered human Action Card {index} content is too thin"
            )
        for marker in ("目标。", "实施判断。", "失败条件。", "审阅与证明。"):
            if marker not in main:
                raise HumanSemanticProjectionError(
                    f"human Action Card {index} misses reader marker: {marker}"
                )
        leaked = [marker for marker in FORBIDDEN_MAIN_MARKERS if marker in main]
        if leaked:
            raise HumanSemanticProjectionError(
                f"human Action Card {index} exposes machine/control sections: "
                + ", ".join(leaked)
            )
        if len(set(ACTION_COMPONENT_PATTERN.findall(appendix))) > 3:
            raise HumanSemanticProjectionError(
                f"human Action Card {index} appendix reproduces the component identity index"
            )
        _validate_appendix_quality("action-card-set", appendix, card_index=index)
    return {
        "document_title": title,
        "reader_summary": summary,
        "review_model": review_model,
        "cards": cards,
        "fidelity_review": _fidelity(payload),
    }


def validate_projection_payload(
    *,
    kind: str,
    payload: dict[str, Any],
    required_ids: list[str],
    allowed_source_refs: list[str] | None = None,
    reconstruction_conflict_ids: list[str] | None = None,
) -> dict[str, Any]:
    if kind not in PROJECTION_KINDS:
        raise HumanSemanticProjectionError(f"unsupported projection kind: {kind}")
    normalized = (
        _validate_action_cards(payload, required_ids, allowed_source_refs)
        if kind == "action-card-set"
        else _validate_document(kind, payload, required_ids, allowed_source_refs)
    )
    if kind == "esp-core" and reconstruction_conflict_ids:
        try:
            validate_reconstruction_conflict_coverage(
                normalized["review_model"], reconstruction_conflict_ids
            )
        except ArchitectureReconstructionInputError as exc:
            raise HumanSemanticProjectionError(str(exc)) from exc
    return {"schema_version": SCHEMA_VERSION, "projection_kind": kind, **normalized}


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
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def refresh_projection_rendering(
    *,
    case_root: Path,
    kind: str,
    output_path: Path,
    locale: str | None = None,
) -> dict[str, Any]:
    """Deterministically refresh rendered fields from an accepted review model.

    This compatibility path never invokes a model and never changes semantic
    decisions. It is used when a reader-only renderer or terminology update
    makes cached Markdown stale while source truth and the structured model are
    still current.
    """

    root = case_root.resolve()
    output = output_path.resolve()
    if not output.is_relative_to(root) or not output.is_file() or output.is_symlink():
        raise HumanSemanticProjectionError(
            "existing semantic projection must be a regular file inside the case root"
        )
    try:
        payload = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HumanSemanticProjectionError(
            f"existing semantic projection is unreadable: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise HumanSemanticProjectionError("existing semantic projection must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("projection_kind") != kind:
        raise HumanSemanticProjectionError(
            "existing semantic projection schema or kind is incompatible with deterministic refresh"
        )

    refs = projection_source_refs(root, kind)
    receipt = source_receipt(root, refs)
    if payload.get("source_hashes") != receipt:
        raise HumanSemanticProjectionError(
            "existing semantic projection source hashes are stale"
        )
    reconstruction = (
        discover_reconstruction_input(root) if kind == "esp-core" else None
    )
    reconstruction_metadata = reconstruction_receipt(reconstruction)
    if payload.get("architecture_reconstruction_input") != reconstruction_metadata:
        raise HumanSemanticProjectionError(
            "existing semantic projection architecture reconstruction input is stale"
        )
    reconstruction_conflict_ids = (
        list(reconstruction["conflict_ids"]) if reconstruction is not None else []
    )
    required_ids = _required_ids(root, kind, refs)
    if payload.get("machine_identity_index") != _machine_identity_index(required_ids):
        raise HumanSemanticProjectionError(
            "existing semantic projection machine identity index is stale"
        )

    normalized = validate_projection_payload(
        kind=kind,
        payload=payload,
        required_ids=required_ids,
        allowed_source_refs=refs,
        reconstruction_conflict_ids=reconstruction_conflict_ids,
    )
    quality_report = audit_projection(
        kind=kind,
        payload=normalized,
        source_anchors=source_anchor_terms(root, refs),
    )
    if quality_report.get("verdict") == "fail":
        raise HumanSemanticProjectionError(repair_feedback(quality_report))

    quality_path = decision_quality_report_path(output)
    write_decision_quality_report(quality_path, quality_report)
    quality_pointer = {
        "path": quality_path.resolve().relative_to(root).as_posix(),
        "sha256": sha256_file(quality_path),
        "summary": audit_summary(quality_report),
    }
    final = {
        **normalized,
        "target_locale": str(locale or payload.get("target_locale") or "zh-CN"),
        "source_hashes": receipt,
        "machine_identity_index": _machine_identity_index(required_ids),
        "decision_quality": quality_pointer,
        "architecture_reconstruction_input": reconstruction_metadata,
    }
    _atomic_json(output, final)
    return {
        "path": str(output),
        "sha256": sha256_file(output),
        "source_hashes": receipt,
        "required_id_count": len(required_ids),
        "fidelity_status": final["fidelity_review"]["status"],
        "decision_quality_verdict": quality_report["verdict"],
        "decision_quality_score": quality_report["score"],
        "decision_quality_path": str(quality_path.resolve()),
        "decision_quality_sha256": quality_pointer["sha256"],
        "architecture_reconstruction_input": reconstruction_metadata,
        "refresh_mode": "deterministic-render",
    }


def generate_projection(
    *,
    case_root: Path,
    kind: str,
    locale: str,
    output_path: Path,
    invoke: Callable[[str, str], str],
    max_source_chars: int = 900_000,
) -> dict[str, Any]:
    root = case_root.resolve()
    refs = projection_source_refs(root, kind)
    receipt = source_receipt(root, refs)
    reconstruction = (
        discover_reconstruction_input(root) if kind == "esp-core" else None
    )
    reconstruction_metadata = reconstruction_receipt(reconstruction)
    reconstruction_conflict_ids = (
        list(reconstruction["conflict_ids"]) if reconstruction is not None else []
    )
    required_ids = _required_ids(root, kind, refs)
    source_anchors = source_anchor_terms(root, refs)
    base_prompt = _prompt(root, kind, refs, required_ids, max_chars=max_source_chars)
    system = (
        "You are a senior product, architecture, and implementation editor. "
        "Your job is to produce source-grounded structured review decisions, not Markdown or machine data chains. "
        "Remain faithful to the supplied phase truth; deterministic rendering will create the human document."
    )
    previous = ""
    error = ""
    for attempt in range(2):
        prompt = base_prompt
        if error:
            prompt += (
                "\n\nThe previous candidate failed deterministic human-projection validation. "
                f"Repair it and return a complete JSON object. Validation error: {error}"
                f"\n\n## PREVIOUS CANDIDATE\n{previous}"
            )
        previous = invoke(system, prompt)
        try:
            candidate = _parse_object(previous)
            normalized = validate_projection_payload(
                kind=kind,
                payload=candidate,
                required_ids=required_ids,
                allowed_source_refs=refs,
                reconstruction_conflict_ids=reconstruction_conflict_ids,
            )
        except HumanSemanticProjectionError as exc:
            error = str(exc)
            if attempt == 0:
                continue
            raise
        quality_report = audit_projection(
            kind=kind,
            payload=normalized,
            source_anchors=source_anchors,
        )
        if quality_report["verdict"] != "pass" and attempt == 0:
            error = repair_feedback(quality_report)
            continue
        if quality_report["verdict"] == "fail":
            raise HumanSemanticProjectionError(repair_feedback(quality_report))

        quality_path = decision_quality_report_path(output_path)
        write_decision_quality_report(quality_path, quality_report)
        quality_pointer = {
            "path": quality_path.resolve().relative_to(root).as_posix(),
            "sha256": sha256_file(quality_path),
            "summary": audit_summary(quality_report),
        }
        final = {
            **normalized,
            "target_locale": locale,
            "source_hashes": receipt,
            "machine_identity_index": _machine_identity_index(required_ids),
            "decision_quality": quality_pointer,
            "architecture_reconstruction_input": reconstruction_metadata,
        }
        _atomic_json(output_path, final)
        return {
            "path": str(output_path.resolve()),
            "sha256": sha256_file(output_path),
            "source_hashes": receipt,
            "required_id_count": len(required_ids),
            "fidelity_status": final["fidelity_review"]["status"],
            "decision_quality_verdict": quality_report["verdict"],
            "decision_quality_score": quality_report["score"],
            "decision_quality_path": str(quality_path.resolve()),
            "decision_quality_sha256": quality_pointer["sha256"],
            "architecture_reconstruction_input": reconstruction_metadata,
        }
    raise HumanSemanticProjectionError(error or "human semantic projection failed")


def validate_projection_artifact(
    *,
    case_root: Path,
    kind: str,
    output_path: Path,
    expected_source_hashes: object,
    expected_sha256: object | None = None,
) -> bool:
    if not output_path.is_file() or output_path.is_symlink() or not isinstance(expected_source_hashes, dict):
        return False
    try:
        if expected_sha256 is not None and sha256_file(output_path) != expected_sha256:
            return False
        refs = projection_source_refs(case_root.resolve(), kind)
        receipt = source_receipt(case_root.resolve(), refs)
        if receipt != expected_source_hashes:
            return False
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return False
        if payload.get("schema_version") != SCHEMA_VERSION or payload.get("projection_kind") != kind:
            return False
        reconstruction = (
            discover_reconstruction_input(case_root.resolve())
            if kind == "esp-core"
            else None
        )
        reconstruction_metadata = reconstruction_receipt(reconstruction)
        reconstruction_conflict_ids = (
            list(reconstruction["conflict_ids"])
            if reconstruction is not None
            else []
        )
        required_ids = _required_ids(case_root.resolve(), kind, refs)
        normalized = validate_projection_payload(
            kind=kind,
            payload=payload,
            required_ids=required_ids,
            allowed_source_refs=refs,
            reconstruction_conflict_ids=reconstruction_conflict_ids,
        )
        for field in ("review_model", "main_markdown", "appendix_markdown", "cards"):
            if field in normalized and payload.get(field) != normalized.get(field):
                return False
        if payload.get("source_hashes") != receipt:
            return False
        if payload.get("architecture_reconstruction_input") != reconstruction_metadata:
            return False
        if payload.get("machine_identity_index") != _machine_identity_index(required_ids):
            return False
        quality_report = audit_projection(
            kind=kind,
            payload=normalized,
            source_anchors=source_anchor_terms(case_root.resolve(), refs),
        )
        if quality_report.get("verdict") == "fail":
            return False
        quality_pointer = payload.get("decision_quality")
        if not isinstance(quality_pointer, dict):
            return False
        if quality_pointer.get("summary") != audit_summary(quality_report):
            return False
        quality_ref = Path(str(quality_pointer.get("path") or ""))
        quality_path = (case_root.resolve() / quality_ref).resolve()
        if (
            quality_ref.is_absolute()
            or not quality_path.is_relative_to(case_root.resolve())
            or sha256_file(quality_path) != str(quality_pointer.get("sha256") or "")
            or not validate_decision_quality_report(quality_path, expected=quality_report)
        ):
            return False
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        HumanSemanticProjectionError,
        ArchitectureReconstructionInputError,
    ):
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-root", required=True, type=Path)
    parser.add_argument("--kind", required=True, choices=PROJECTION_KINDS)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-locale", default="zh-CN")
    parser.add_argument("--model")
    parser.add_argument("--api-base")
    parser.add_argument("--api-key")
    args = parser.parse_args(argv)

    from common.emit_reader_translation import _call_llm, _get_client, _read_translation_config

    config = _read_translation_config()
    projection_config = config.get("human_semantic_projection", {})
    if not isinstance(projection_config, dict):
        projection_config = {}
    model = args.model or projection_config.get("model") or config.get("model", "gpt-5.4")
    api_base = args.api_base or config.get("api_base_url") or os.environ.get("OPENAI_BASE_URL")
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    client = _get_client(api_base=api_base, api_key=api_key)

    def invoke(system_prompt: str, user_prompt: str) -> str:
        return _call_llm(
            client=client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=int(projection_config.get("max_tokens", config.get("max_tokens_per_segment", 32768))),
            timeout=float(projection_config.get("timeout_seconds", config.get("timeout_seconds", 1800))),
        ).content

    try:
        report = generate_projection(
            case_root=args.case_root.resolve(),
            kind=args.kind,
            locale=args.target_locale,
            output_path=args.output.resolve(),
            invoke=invoke,
            max_source_chars=int(projection_config.get("max_source_chars", 900_000)),
        )
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        HumanSemanticProjectionError,
        ArchitectureReconstructionInputError,
    ) as exc:
        print(json.dumps({"status": "failed", "kind": args.kind, "detail": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "generated", "kind": args.kind, **report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
