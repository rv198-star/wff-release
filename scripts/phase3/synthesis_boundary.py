from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase3.surface_policy import write_phase3_profiled_surface


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item).strip()]


def _source_priority(source_type: str) -> int:
    normalized = source_type.strip().lower()
    if normalized in {"contract", "api", "endpoint"}:
        return 45
    if normalized in {"scenario", "flow"}:
        return 35
    if normalized in {"replay", "idempotency"}:
        return 30
    if normalized in {"sql", "persistence", "data"}:
        return 25
    return 10


def _work_packages(row: dict[str, Any]) -> list[str]:
    packages = _string_list(row.get("work_packages"))
    package_id = str(row.get("work_package_id", "")).strip()
    if package_id:
        packages.append(package_id)
    return sorted(set(packages))


def _rank_binding_row(row: dict[str, Any]) -> int:
    implementation_targets = _string_list(row.get("implementation_targets"))
    test_targets = _string_list(row.get("test_targets"))
    runtime_evidence_refs = _string_list(row.get("runtime_evidence_refs"))
    source_subject = str(row.get("source_subject", "")).strip()
    operation_id = str(row.get("operation_id", "")).strip()
    return (
        _source_priority(str(row.get("source_type", "")))
        + len(implementation_targets) * 5
        + len(test_targets) * 4
        + len(runtime_evidence_refs) * 3
        + len(_work_packages(row)) * 2
        + (3 if operation_id else 0)
        + (2 if source_subject else 0)
    )


def _semantic_intent(row: dict[str, Any]) -> str:
    subject = str(row.get("source_subject", "")).strip()
    operation_id = str(row.get("operation_id", "")).strip()
    source_id = str(row.get("source_id", "")).strip()
    if subject and operation_id:
        return f"Preserve {subject} while implementing {operation_id}."
    if subject:
        return f"Preserve {subject} in generated implementation and tests."
    if operation_id:
        return f"Preserve source-bound behavior while implementing {operation_id}."
    return f"Preserve source-bound behavior for {source_id or 'this semantic unit'}."


def _selected_semantic_units(implementation_bindings: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    rows = [row for row in _as_list(implementation_bindings.get("rows")) if isinstance(row, dict)]
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        implementation_targets = _string_list(row.get("implementation_targets"))
        test_targets = _string_list(row.get("test_targets"))
        runtime_evidence_refs = _string_list(row.get("runtime_evidence_refs"))
        if not implementation_targets and not test_targets and not runtime_evidence_refs:
            continue
        candidate = {
            "source_id": str(row.get("source_id", "")).strip(),
            "source_type": str(row.get("source_type", "")).strip(),
            "source_subject": str(row.get("source_subject", "")).strip(),
            "operation_id": str(row.get("operation_id", "")).strip(),
            "work_package_id": str(row.get("work_package_id", "")).strip(),
            "work_packages": _work_packages(row),
            "implementation_targets": implementation_targets,
            "test_targets": test_targets,
            "runtime_evidence_refs": runtime_evidence_refs,
            "implementation_semantic_intent": _semantic_intent(row),
            "agentic_decision": "synthesize implementation meaning before generated code/test bodies are scaffolded",
            "selection_reason": "concrete implementation/test/evidence target with source-bound semantic value",
            "_rank": _rank_binding_row(row),
            "_source_order": index,
        }
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-int(item["_rank"]), int(item["_source_order"])))
    selected = candidates[: max(0, limit)]
    for item in selected:
        item.pop("_rank", None)
        item.pop("_source_order", None)
    return selected


def build_phase3_synthesis_brief(
    *,
    case_name: str,
    version: str,
    phase2_root: Path,
    implementation_bindings: dict[str, Any],
    mainline_verification_mode: str,
    output_locale: str = "zh-CN",
) -> dict[str, Any]:
    selected_units = _selected_semantic_units(implementation_bindings)
    rows = [row for row in _as_list(implementation_bindings.get("rows")) if isinstance(row, dict)]
    return {
        "artifact_kind": "phase3-pre-generation-synthesis-brief",
        "schema_version": "phase3-synthesis-brief.v1",
        "phase": "phase3",
        "case_name": str(case_name).strip(),
        "version": str(version).strip(),
        "output_locale": str(output_locale).strip() or "zh-CN",
        "phase2_root": str(Path(phase2_root)),
        "handoff_point": "before-implementation-scaffolding",
        "mainline_verification_mode": str(mainline_verification_mode).strip() or "strict-runtime",
        "control_boundary": {
            "workflow_controls_order": "build source-bound brief after P3 trace/source bindings exist and before implementation scaffolding starts",
            "agentic_owns_module_synthesis": "resolve semantic intent, module emphasis, and test meaning for selected units before generated bodies are created",
            "evidence_caps_claims": "selected units carry source, target, and runtime-evidence references; generated claims remain capped by later gates",
        },
        "agentic_owned_modules": [
            "implementation_semantic_intent",
            "module_synthesis_emphasis",
            "source_bound_test_obligation",
            "bounded_rewrite_seed",
        ],
        "workflow_owned_modules": [
            "phase_order",
            "artifact_paths",
            "schema_version",
            "review_profile_location",
        ],
        "selected_semantic_units": selected_units,
        "summary": {
            "binding_row_count": len(rows),
            "selected_semantic_unit_count": len(selected_units),
            "review_surface_profile": ".phase3-review",
            "post_generation_compiler": False,
        },
    }


def _render_unit(unit: dict[str, Any], index: int) -> list[str]:
    targets = _string_list(unit.get("implementation_targets"))
    tests = _string_list(unit.get("test_targets"))
    evidence = _string_list(unit.get("runtime_evidence_refs"))
    lines = [
        f"### {index}. {unit.get('source_id', '') or 'unidentified-source'}",
        "",
        f"- source_subject: {unit.get('source_subject', '') or 'unknown'}",
        f"- implementation_semantic_intent: {unit.get('implementation_semantic_intent', '')}",
        f"- implementation_targets: {', '.join(targets) if targets else 'none'}",
        f"- test_targets: {', '.join(tests) if tests else 'none'}",
        f"- runtime_evidence_refs: {', '.join(evidence) if evidence else 'none'}",
        "",
    ]
    return lines


def render_phase3_synthesis_brief_markdown(brief: dict[str, Any], *, output_locale: str = "zh-CN") -> str:
    if str(output_locale).strip() == "zh-CN":
        lines = [
            "# Phase 3 生成前综合简报",
            "",
            f"- artifact_kind: {brief.get('artifact_kind', '')}",
            f"- handoff_point: {brief.get('handoff_point', '')}",
            f"- case_name: {brief.get('case_name', '')}",
            f"- version: {brief.get('version', '')}",
            f"- mainline_verification_mode: {brief.get('mainline_verification_mode', '')}",
            "- boundary: Workflow 控制顺序，Agentic 在 implementation scaffolding 之前负责模块语义综合，Evidence 限制后续声明。",
            "- guardrail: not an after-the-fact compiler; 不复活 R1 stage packets 或 R2 artifact compiler。",
            "",
            "## Selected Semantic Units",
            "",
        ]
    else:
        lines = [
            "# Phase 3 Pre-Generation Synthesis Brief",
            "",
            f"- artifact_kind: {brief.get('artifact_kind', '')}",
            f"- handoff_point: {brief.get('handoff_point', '')}",
            f"- case_name: {brief.get('case_name', '')}",
            f"- version: {brief.get('version', '')}",
            f"- mainline_verification_mode: {brief.get('mainline_verification_mode', '')}",
            "- boundary: Workflow controls order, Agentic owns module synthesis before implementation scaffolding, Evidence caps claims.",
            "- guardrail: not an after-the-fact compiler; do not revive R1 stage packets or R2 artifact compiler.",
            "",
            "## Selected Semantic Units",
            "",
        ]
    for index, unit in enumerate(_as_list(brief.get("selected_semantic_units")), start=1):
        if isinstance(unit, dict):
            lines.extend(_render_unit(unit, index))
    return "\n".join(lines).rstrip() + "\n"


def write_phase3_synthesis_brief_artifacts(
    *,
    output_dir: Path,
    case_name: str,
    version: str,
    phase2_root: Path,
    implementation_bindings: dict[str, Any],
    mainline_verification_mode: str,
    output_locale: str = "zh-CN",
) -> dict[str, Any]:
    brief = build_phase3_synthesis_brief(
        case_name=case_name,
        version=version,
        phase2_root=phase2_root,
        implementation_bindings=implementation_bindings,
        mainline_verification_mode=mainline_verification_mode,
        output_locale=output_locale,
    )
    json_path = write_phase3_profiled_surface(
        output_dir,
        "phase3-synthesis-brief.json",
        json.dumps(brief, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    markdown_path = write_phase3_profiled_surface(
        output_dir,
        "phase3-synthesis-brief.md",
        render_phase3_synthesis_brief_markdown(brief, output_locale=output_locale),
    )
    return {
        "brief": brief,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
