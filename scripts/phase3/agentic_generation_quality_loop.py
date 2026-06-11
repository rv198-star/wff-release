from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MINIMUM_DEPTH = "L3: generation/change-loop intervention"
TVG_ROLE = "generation-value-gain-tool"
DECISION_METHODS = ["WAE", "EDSP", "SELA"]
OBLIGATION_CATEGORIES = [
    "business-state",
    "permission",
    "error",
    "persistence",
    "idempotency",
    "replay",
    "scenario-meaning",
]
SEMANTIC_OBLIGATION_CATEGORIES = [
    "semantic-owner",
    "semantic-aggregate",
    "semantic-lifecycle-event",
    "semantic-mutation-scope",
]
DEFAULT_SCORECARD_DIMENSIONS = [
    "Semantic implementation maturity",
    "Behavioral completeness",
    "Test assertion depth",
    "Runtime evidence usefulness",
    "Handoff and maintainability leverage",
]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item).strip()]


def _source_priority(source_type: str) -> int:
    normalized = source_type.strip().lower()
    if normalized in {"contract", "contract-trace", "interface", "api"}:
        return 40
    if normalized in {"scenario", "flow"}:
        return 35
    if normalized in {"replay", "idempotency"}:
        return 30
    if normalized in {"sql", "persistence", "data"}:
        return 25
    return 10


def _rank_binding_row(row: dict[str, Any]) -> int:
    semantic_invariants = _semantic_invariants(row)
    semantic_bonus = 0
    if any(str(item.get("source_status") or "").strip() == "source-supported" for item in semantic_invariants):
        semantic_bonus = 80
    elif semantic_invariants:
        semantic_bonus = 20
    return (
        _source_priority(str(row.get("source_type", "")))
        + (len(_string_list(row.get("implementation_targets"))) * 4)
        + (len(_string_list(row.get("test_targets"))) * 3)
        + (len(_string_list(row.get("runtime_evidence_refs"))) * 2)
        + (len(_string_list(row.get("work_packages"))) * 2)
        + semantic_bonus
    )


def _planned_change_units(
    *,
    implementation_targets: list[str],
    test_targets: list[str],
    runtime_evidence_refs: list[str],
) -> list[dict[str, str]]:
    units: list[dict[str, str]] = []
    for target in implementation_targets:
        units.append({"change_unit_type": "code", "target": target})
    for target in test_targets:
        units.append({"change_unit_type": "test", "target": target})
    for target in runtime_evidence_refs:
        units.append({"change_unit_type": "evidence", "target": target})
    return units


def _target_generated_units(
    *,
    implementation_targets: list[str],
    test_targets: list[str],
    runtime_evidence_refs: list[str],
) -> list[str]:
    seen: dict[str, None] = {}
    for target in [*implementation_targets, *test_targets, *runtime_evidence_refs]:
        seen.setdefault(target, None)
    return list(seen)


def _obligation_signals(row_or_unit: dict[str, Any]) -> set[str]:
    signals = {item.lower() for item in _string_list(row_or_unit.get("obligation_signals"))}
    signals.update(item.lower() for item in _string_list(row_or_unit.get("quality_signals")))
    signals.update(item.lower() for item in _string_list(row_or_unit.get("risk_signals")))

    haystack = " ".join(
        [
            str(row_or_unit.get("source_type", "")),
            str(row_or_unit.get("source_subject", "")),
            " ".join(_string_list(row_or_unit.get("implementation_targets"))),
            " ".join(_string_list(row_or_unit.get("test_targets"))),
            " ".join(_string_list(row_or_unit.get("runtime_evidence_refs"))),
        ]
    ).lower()
    if any(token in haystack for token in ("state", "lifecycle", "transition")):
        signals.add("business-state")
    if any(token in haystack for token in ("permission", "auth", "owner", "role")):
        signals.add("permission")
    if any(token in haystack for token in ("error", "failure", "invalid", "exception")):
        signals.add("error")
    if any(token in haystack for token in ("persist", "repository", "sql", "data")):
        signals.add("persistence")
    if any(token in haystack for token in ("idempot", "duplicate")):
        signals.add("idempotency")
    if "replay" in haystack:
        signals.add("replay")
    if any(token in haystack for token in ("scenario", "meaning", "flow")):
        signals.add("scenario-meaning")
    return signals


def _semantic_source_status(raw_status: Any) -> str:
    normalized = str(raw_status or "").strip().lower().replace("_", "-")
    if normalized in {"resolved", "source-supported", "supported"}:
        return "source-supported"
    return "review-bound"


def _semantic_lifecycle_events(semantics: dict[str, Any]) -> list[str]:
    events = _string_list(semantics.get("trigger_events"))
    if events:
        return events
    event = str(semantics.get("lifecycle_event") or "").strip()
    return [event] if event else []


def _semantic_mutation_scope(semantics: dict[str, Any], *, source_status: str) -> str:
    explicit = str(semantics.get("mutation_scope") or "").strip()
    if explicit:
        return explicit
    if source_status != "source-supported":
        return "review-bound"
    owner = str(semantics.get("owner_service") or "").strip().lower()
    guard = str(semantics.get("mutation_guard") or "").strip().lower()
    events = _semantic_lifecycle_events(semantics)
    if "orchestrator" in owner or "orchestrator" in guard:
        return "review-orchestrated-mutation"
    if not events and _string_list(semantics.get("readonly_dependencies")):
        return "read-only"
    return "mutation"


def _semantic_invariants(row: dict[str, Any]) -> list[dict[str, Any]]:
    semantics = row.get("operation_semantics")
    if not isinstance(semantics, dict):
        return []

    operation_id = str(row.get("operation_id") or semantics.get("operation_id") or "").strip()
    if not operation_id:
        return []

    source_id = str(row.get("source_id") or "").strip()
    source_status = _semantic_source_status(semantics.get("status") or semantics.get("semantic_status"))
    return [
        {
            "source_operation_id": operation_id,
            "source_status": source_status,
            "owner_service": str(semantics.get("owner_service") or "").strip()
            if source_status == "source-supported"
            else "",
            "aggregate": str(semantics.get("aggregate") or "").strip()
            if source_status == "source-supported"
            else "",
            "lifecycle_events": _semantic_lifecycle_events(semantics)
            if source_status == "source-supported"
            else [],
            "mutation_scope": _semantic_mutation_scope(semantics, source_status=source_status),
            "state_set": _string_list(semantics.get("state_set"))
            if source_status == "source-supported"
            else [],
            "evidence_keys": _string_list(semantics.get("evidence_keys"))
            if source_status == "source-supported"
            else [],
            "source_ids": [source_id] if source_id else [],
            "review_bound_reasons": _string_list(semantics.get("review_bound_reasons"))
            if source_status != "source-supported"
            else [],
        }
    ]


def _semantic_test_obligations(unit: dict[str, Any]) -> list[dict[str, Any]]:
    invariants = [item for item in _as_list(unit.get("semantic_invariants")) if isinstance(item, dict)]
    if not invariants:
        return []

    obligations: list[dict[str, Any]] = []
    source_id = str(unit.get("source_id", "")).strip()
    for category in SEMANTIC_OBLIGATION_CATEGORIES:
        supported_invariants = [
            invariant
            for invariant in invariants
            if str(invariant.get("source_status") or "").strip() == "source-supported"
        ]
        if supported_invariants:
            support_status = "source-supported"
            source_operation_ids = [
                str(invariant.get("source_operation_id") or "").strip()
                for invariant in supported_invariants
                if str(invariant.get("source_operation_id") or "").strip()
            ]
        else:
            support_status = "review-bound"
            source_operation_ids = [
                str(invariant.get("source_operation_id") or "").strip()
                for invariant in invariants
                if str(invariant.get("source_operation_id") or "").strip()
            ]
        obligations.append(
            {
                "obligation_id": f"{source_id}:{category}" if source_id else category,
                "category": category,
                "support_status": support_status,
                "source_ids": [source_id] if source_id else [],
                "source_operation_ids": source_operation_ids,
                "source_subject": str(unit.get("source_subject", "")).strip(),
                "target_generated_units": _string_list(unit.get("target_generated_units")),
                "assertion_goal": _assertion_goal(category),
                "claim_ceiling": "review-bound-until-runtime-evidence",
            }
        )
    return obligations


def build_test_obligations(unit: dict[str, Any]) -> list[dict[str, Any]]:
    signals = _obligation_signals(unit)
    source_id = str(unit.get("source_id", "")).strip()
    source_subject = str(unit.get("source_subject", "")).strip()
    obligations: list[dict[str, Any]] = []
    for category in OBLIGATION_CATEGORIES:
        supported = category in signals
        obligations.append(
            {
                "obligation_id": f"{source_id}:{category}" if source_id else category,
                "category": category,
                "support_status": "source-supported" if supported else "review-bound",
                "source_ids": [source_id] if source_id else [],
                "source_subject": source_subject,
                "target_generated_units": _string_list(unit.get("target_generated_units")),
                "assertion_goal": _assertion_goal(category),
                "claim_ceiling": "review-bound-until-runtime-evidence",
            }
        )
    obligations.extend(_semantic_test_obligations(unit))
    return obligations


def _assertion_goal(category: str) -> str:
    goals = {
        "business-state": "prove intended state transition and rejected invalid state movement",
        "permission": "prove allowed and denied actor paths at the service boundary",
        "error": "prove domain error behavior rather than generic exception shape",
        "persistence": "prove durable write/read effect through repository or data boundary",
        "idempotency": "prove duplicate request handling is stable and intentional",
        "replay": "prove replay evidence exercises the same business behavior",
        "scenario-meaning": "prove the test scenario carries product meaning, not only transport shape",
        "semantic-owner": "prove source-supported owner service semantics before mutation",
        "semantic-aggregate": "prove aggregate identity semantics are preserved in code and tests",
        "semantic-lifecycle-event": "prove lifecycle event semantics match source-supported operation truth",
        "semantic-mutation-scope": "prove mutation/read-only scope matches source-supported operation truth",
    }
    return goals.get(category, "keep review-bound until source truth supports a concrete assertion")


def _primary_change_type(planned_change_units: list[dict[str, str]]) -> str:
    priority = {"code": 0, "test": 1, "evidence": 2}
    if not planned_change_units:
        return "review"
    ordered = sorted(
        planned_change_units,
        key=lambda item: priority.get(str(item.get("change_unit_type", "")).strip(), 99),
    )
    return str(ordered[0].get("change_unit_type", "")).strip() or "review"


def _change_packet(*, unit: dict[str, Any], version: str) -> dict[str, Any]:
    planned_change_units = [
        item for item in _as_list(unit.get("planned_change_units")) if isinstance(item, dict)
    ]
    obligations = build_test_obligations(unit)
    return {
        "packet_id": f"{str(version).strip() or 'candidate'}:{unit.get('source_id', '')}",
        "change_unit_type": _primary_change_type(planned_change_units),
        "before_ref": dict(unit.get("baseline_refs", {})) if isinstance(unit.get("baseline_refs"), dict) else {},
        "after_ref": f"{str(version).strip() or 'candidate'}-candidate:{unit.get('source_id', '')}",
        "test_obligation_ids": [str(item.get("obligation_id", "")).strip() for item in obligations],
        "runtime_evidence_refs": _string_list(unit.get("runtime_evidence_refs")),
        "claim_ceiling": "review-bound-until-runtime-evidence",
        "scorecard_dimension_targets": _string_list(unit.get("scorecard_dimensions")),
        "change_units": planned_change_units,
    }


def _select_behavior_units(
    *,
    implementation_bindings: dict[str, Any],
    baseline_refs: dict[str, Any],
    scorecard_dimensions: list[str],
    limit: int,
    version: str,
) -> list[dict[str, Any]]:
    rows = [row for row in _as_list(implementation_bindings.get("rows")) if isinstance(row, dict)]
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        implementation_targets = _string_list(row.get("implementation_targets"))
        test_targets = _string_list(row.get("test_targets"))
        runtime_evidence_refs = _string_list(row.get("runtime_evidence_refs"))
        target_generated_units = _target_generated_units(
            implementation_targets=implementation_targets,
            test_targets=test_targets,
            runtime_evidence_refs=runtime_evidence_refs,
        )
        if not target_generated_units:
            continue

        candidate = {
            "source_id": str(row.get("source_id", "")).strip(),
            "source_type": str(row.get("source_type", "")).strip(),
            "source_subject": str(row.get("source_subject", "")).strip(),
            "operation_id": str(row.get("operation_id", "")).strip(),
            "decision_owner": "agentic",
            "decision_methods": list(DECISION_METHODS),
            "tvg_role": TVG_ROLE,
            "minimum_depth": MINIMUM_DEPTH,
            "baseline_refs": dict(baseline_refs),
            "scorecard_dimensions": list(scorecard_dimensions),
            "obligation_signals": _string_list(row.get("obligation_signals")),
            "quality_signals": _string_list(row.get("quality_signals")),
            "risk_signals": _string_list(row.get("risk_signals")),
            "implementation_targets": implementation_targets,
            "test_targets": test_targets,
            "runtime_evidence_refs": runtime_evidence_refs,
            "target_generated_units": target_generated_units,
            "semantic_invariants": _semantic_invariants(row),
            "planned_change_units": _planned_change_units(
                implementation_targets=implementation_targets,
                test_targets=test_targets,
                runtime_evidence_refs=runtime_evidence_refs,
            ),
            "selection_reason": "highest value/risk generated-unit candidate with concrete code, test, or evidence targets",
            "_rank": _rank_binding_row(row),
            "_source_order": index,
        }
        candidate["test_obligations"] = build_test_obligations(candidate)
        candidate["change_packet"] = _change_packet(unit=candidate, version=version)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-int(item["_rank"]), int(item["_source_order"])))
    selected = candidates[: max(0, limit)]
    for item in selected:
        item.pop("_rank", None)
        item.pop("_source_order", None)
    return selected


def build_generation_quality_loop(
    *,
    case_name: str,
    version: str,
    implementation_bindings: dict[str, object],
    baseline_refs: dict[str, object],
    scorecard_dimensions: list[str],
    limit: int = 3,
) -> dict[str, object]:
    selected_units = _select_behavior_units(
        implementation_bindings=implementation_bindings,
        baseline_refs=baseline_refs,
        scorecard_dimensions=scorecard_dimensions,
        limit=limit,
        version=version,
    )
    change_types = {
        str(change.get("change_unit_type", "")).strip()
        for unit in selected_units
        for change in _as_list(unit.get("planned_change_units"))
        if isinstance(change, dict)
    }
    obligation_count = sum(
        len(_as_list(unit.get("test_obligations"))) for unit in selected_units
    )
    return {
        "artifact_kind": "phase3-agentic-generation-quality-loop",
        "case_name": str(case_name).strip(),
        "version": str(version).strip(),
        "decision_methods": list(DECISION_METHODS),
        "tvg_role": TVG_ROLE,
        "minimum_depth": MINIMUM_DEPTH,
        "baseline_refs": dict(baseline_refs),
        "scorecard_dimensions": list(scorecard_dimensions),
        "selected_behavior_units": selected_units,
        "summary": {
            "selected_behavior_unit_count": len(selected_units),
            "test_obligation_count": obligation_count,
            "planned_change_unit_types": sorted(change_types),
            "has_code_test_or_evidence_change_unit": bool(change_types & {"code", "test", "evidence"}),
            "decision_owner": "agentic",
            "tvg_decision_owner": False,
        },
    }


def render_generation_quality_loop_markdown(loop: dict[str, Any], *, output_locale: str = "zh-CN") -> str:
    zh = str(output_locale).strip().lower() in {"zh-cn", "zh", "cn"}
    title = "# P3 Agentic 生成质量循环" if zh else "# P3 Agentic Generation Quality Loop"
    summary_title = "## 摘要" if zh else "## Summary"
    units_title = "## 行为单元" if zh else "## Behavior Units"
    obligations_title = "## 测试义务" if zh else "## Test Obligations"
    evidence_title = "## 证据边界" if zh else "## Evidence Boundary"
    no_units = "未选择可变更行为单元；保持 review-bound。" if zh else "No changeable behavior unit selected; keep review-bound."
    lines = [
        title,
        "",
        summary_title,
        f"- minimum_depth: `{loop.get('minimum_depth', '')}`",
        f"- tvg_role: `{loop.get('tvg_role', '')}`",
        f"- selected_behavior_unit_count: `{loop.get('summary', {}).get('selected_behavior_unit_count', 0)}`",
        f"- test_obligation_count: `{loop.get('summary', {}).get('test_obligation_count', 0)}`",
        "",
        units_title,
    ]
    units = _as_list(loop.get("selected_behavior_units"))
    if not units:
        lines.append(f"- {no_units}")
    for unit in units:
        if not isinstance(unit, dict):
            continue
        packet = unit.get("change_packet", {}) if isinstance(unit.get("change_packet"), dict) else {}
        lines.extend(
            [
                f"- `{unit.get('source_id', '')}` {unit.get('source_subject', '')}",
                f"  - decision_owner: `{unit.get('decision_owner', '')}`",
                f"  - target_generated_units: `{', '.join(_string_list(unit.get('target_generated_units')))}`",
                f"  - change_unit_type: `{packet.get('change_unit_type', '')}`",
                f"  - claim_ceiling: `{packet.get('claim_ceiling', 'review-bound-until-runtime-evidence')}`",
            ]
        )
    lines.extend(["", obligations_title])
    for unit in units:
        if not isinstance(unit, dict):
            continue
        obligations = _as_list(unit.get("test_obligations"))
        if not obligations:
            continue
        supported = [
            str(item.get("category", ""))
            for item in obligations
            if isinstance(item, dict) and item.get("support_status") == "source-supported"
        ]
        review_bound = [
            str(item.get("category", ""))
            for item in obligations
            if isinstance(item, dict) and item.get("support_status") == "review-bound"
        ]
        lines.append(f"- `{unit.get('source_id', '')}` source-supported: `{', '.join(supported)}`")
        lines.append(f"- `{unit.get('source_id', '')}` review-bound: `{', '.join(review_bound)}`")
    lines.extend(
        [
            "",
            evidence_title,
            "- Evidence caps claims; script pass alone does not prove quality gain.",
            "- Human quality audit must compare against v1.2.4 and v1.3.1 before closeout.",
            "",
        ]
    )
    return "\n".join(lines)


def _loop_summary(selected_units: list[dict[str, Any]]) -> dict[str, Any]:
    change_types = {
        str(change.get("change_unit_type", "")).strip()
        for unit in selected_units
        for change in _as_list(unit.get("planned_change_units"))
        if isinstance(change, dict)
    }
    obligation_count = sum(
        len(_as_list(unit.get("test_obligations"))) for unit in selected_units
    )
    return {
        "selected_behavior_unit_count": len(selected_units),
        "test_obligation_count": obligation_count,
        "planned_change_unit_types": sorted(change_types),
        "has_code_test_or_evidence_change_unit": bool(change_types & {"code", "test", "evidence"}),
        "decision_owner": "agentic",
        "tvg_decision_owner": False,
    }


def _append_generated_quality_test_unit(loop: dict[str, Any], *, relative_test_path: str) -> None:
    selected_units = [
        unit for unit in _as_list(loop.get("selected_behavior_units")) if isinstance(unit, dict)
    ]
    version = str(loop.get("version", "")).strip()
    for unit in selected_units:
        targets = _string_list(unit.get("target_generated_units"))
        if relative_test_path not in targets:
            targets.append(relative_test_path)
        unit["target_generated_units"] = targets

        test_targets = _string_list(unit.get("test_targets"))
        if relative_test_path not in test_targets:
            test_targets.append(relative_test_path)
        unit["test_targets"] = test_targets

        planned_change_units = [
            item for item in _as_list(unit.get("planned_change_units")) if isinstance(item, dict)
        ]
        if relative_test_path not in [str(item.get("target", "")).strip() for item in planned_change_units]:
            planned_change_units.append({"change_unit_type": "test", "target": relative_test_path})
        unit["planned_change_units"] = planned_change_units
        unit["test_obligations"] = build_test_obligations(unit)
        unit["change_packet"] = _change_packet(unit=unit, version=version)
    loop["summary"] = _loop_summary(selected_units)


def render_generation_quality_obligation_test(loop: dict[str, Any]) -> str:
    records: list[dict[str, Any]] = []
    for unit in _as_list(loop.get("selected_behavior_units")):
        if not isinstance(unit, dict):
            continue
        obligations = [item for item in _as_list(unit.get("test_obligations")) if isinstance(item, dict)]
        records.append(
            {
                "sourceId": str(unit.get("source_id", "")).strip(),
                "sourceSubject": str(unit.get("source_subject", "")).strip(),
                "changeUnitTypes": sorted(
                    {
                        str(item.get("change_unit_type", "")).strip()
                        for item in _as_list(unit.get("planned_change_units"))
                        if isinstance(item, dict) and str(item.get("change_unit_type", "")).strip()
                    }
                ),
                "supportedCategories": [
                    str(item.get("category", "")).strip()
                    for item in obligations
                    if item.get("support_status") == "source-supported"
                ],
                "reviewBoundCategories": [
                    str(item.get("category", "")).strip()
                    for item in obligations
                    if item.get("support_status") == "review-bound"
                ],
            }
        )
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    return "\n".join(
        [
            'import { describe, expect, it } from "vitest";',
            "",
            "// Generated by the v1.3.2 Agentic Test-First Generation Repair Loop.",
            "// This proves obligation/change-packet structure only; runtime claims remain evidence-capped.",
            f"const obligations = {records_json} as const;",
            "",
            'describe("agentic generation quality obligations", () => {',
            '  it("keeps every selected behavior unit tied to a generated test obligation and change packet", () => {',
            "    expect(obligations.length).toBeGreaterThan(0);",
            "    for (const item of obligations) {",
            "      expect(item.sourceId.length).toBeGreaterThan(0);",
            "      expect(item.changeUnitTypes.some((type) => [\"code\", \"test\", \"evidence\"].includes(type))).toBe(true);",
            "      expect([...item.supportedCategories, ...item.reviewBoundCategories]).toContain(\"scenario-meaning\");",
            "      expect(item.reviewBoundCategories).toBeDefined();",
            "    }",
            "  });",
            "});",
            "",
        ]
    )


def write_agentic_generation_quality_loop_artifacts(
    *,
    output_dir: Path,
    case_name: str,
    version: str,
    implementation_bindings: dict[str, object],
    baseline_refs: dict[str, object] | None = None,
    scorecard_dimensions: list[str] | None = None,
    output_locale: str = "zh-CN",
    limit: int = 3,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    loop = build_generation_quality_loop(
        case_name=case_name,
        version=version,
        implementation_bindings=implementation_bindings,
        baseline_refs=baseline_refs
        or {
            "v1.2.4": "retained v1.2.4 P3/P4 proof output for this case",
            "v1.3.1": "current v1.3.1 limited-gain output for this case",
        },
        scorecard_dimensions=scorecard_dimensions or list(DEFAULT_SCORECARD_DIMENSIONS),
        limit=limit,
    )
    generated_test_relative_path = "tests/unit/api/agentic-generation-quality-obligations.unit.test.ts"
    _append_generated_quality_test_unit(loop, relative_test_path=generated_test_relative_path)
    generated_test_path = output_dir / generated_test_relative_path
    generated_test_path.parent.mkdir(parents=True, exist_ok=True)
    generated_test_path.write_text(render_generation_quality_obligation_test(loop), encoding="utf-8")
    json_path = output_dir / "agentic-generation-quality-loop.json"
    markdown_path = output_dir / "agentic-generation-quality-loop.md"
    json_path.write_text(
        json.dumps(loop, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_generation_quality_loop_markdown(loop, output_locale=output_locale),
        encoding="utf-8",
    )
    summary = dict(loop["summary"]) if isinstance(loop.get("summary"), dict) else {}
    summary.update(
        {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "generated_quality_obligation_test_path": str(generated_test_path),
        }
    )
    return summary
