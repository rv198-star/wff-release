#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


import argparse
import json
from pathlib import Path

from common.human_review_surface import emit_human_review_surface
from common.script_data_assets import load_script_text_asset
from common.claim_control_runtime import ClaimRecord, emit_path_b_claim_control_sidecar
from phasex.phasex_claim_routing import audit_phasex_artifact_claim_refs, phasex_claim_control_route_decision

REPO_ROOT = Path(__file__).resolve().parents[2]

WFF_SCRIPT_DATA_ASSETS = ("scripts/phasex/data/target-driver-packet.md.template",)
TARGET_DRIVER_PACKET_TEMPLATE = load_script_text_asset(__file__, "target-driver-packet.md.template")


PROFILE_OUTPUTS = {
    "assessment-only": [
        (
            "wff-x-scan-code-baseline",
            "wff-x-scan-code-baseline.md",
            "wff-x-scan-code-baseline: scan-code-baseline",
            "reference-packages/phasex-brownfield-refactoring/wff-x-scan-code-baseline/output-template.md",
        ),
        (
            "wff-x-scan-tech-health",
            "wff-x-scan-tech-health.md",
            "wff-x-scan-tech-health: scan-tech-health",
            "reference-packages/phasex-brownfield-refactoring/wff-x-scan-tech-health/output-template.md",
        ),
    ],
    "technical-refactor": [
        (
            "wff-x-scan-code-baseline",
            "wff-x-scan-code-baseline.md",
            "wff-x-scan-code-baseline: scan-code-baseline",
            "reference-packages/phasex-brownfield-refactoring/wff-x-scan-code-baseline/output-template.md",
        ),
        (
            "wff-x-scan-tech-health",
            "wff-x-scan-tech-health.md",
            "wff-x-scan-tech-health: scan-tech-health",
            "reference-packages/phasex-brownfield-refactoring/wff-x-scan-tech-health/output-template.md",
        ),
        (
            "wff-x-plan-test-protection",
            "wff-x-plan-test-protection.md",
            "wff-x-plan-test-protection: plan-test-protection",
            "reference-packages/phasex-brownfield-refactoring/wff-x-plan-test-protection/output-template.md",
        ),
    ],
    "target-driver": [
        (
            "wff-x-scan-code-baseline",
            "wff-x-scan-code-baseline.md",
            "wff-x-scan-code-baseline: scan-code-baseline",
            "reference-packages/phasex-brownfield-refactoring/wff-x-scan-code-baseline/output-template.md",
        ),
        (
            "wff-x-intake-target-driver",
            "wff-x-intake-target-driver.md",
            "wff-x-intake-target-driver: target-driver-intake",
            "reference-packages/phasex-brownfield-refactoring/wff-x-intake-target-driver/output-template.md",
        ),
    ],
}

PROFILE_RULES = {
    "assessment-only": {
        "path": "`wff-x-scan-code-baseline -> wff-x-scan-tech-health`",
        "typical_exit": "explicit decision point / continue later",
    },
    "technical-refactor": {
        "path": "`wff-x-scan-code-baseline -> wff-x-scan-tech-health -> wff-x-plan-test-protection`",
        "typical_exit": "Phase-3 brownfield implementation",
    },
    "target-driver": {
        "path": "`wff-x-scan-code-baseline -> wff-x-intake-target-driver`",
        "typical_exit": "Phase-1 constrained re-entry or direct Phase-3",
    },
}

PROFILE_METHOD_BACKBONES = {
    "assessment-only": [
        "`docs/source-registers/phaseX-source-library-seed-v0.1.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/index-map.md`",
    ],
    "technical-refactor": [
        "`docs/source-registers/phaseX-source-library-seed-v0.1.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/refactor-requires-self-testing-tests-and-fast-feedback-loop.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/branch-by-abstraction-for-long-running-refactors.md`",
        "`sources/books/extracted/the-art-of-unit-testing/stage-guidance-draft.md`",
    ],
    "target-driver": [
        "`docs/source-registers/phaseX-source-library-seed-v0.1.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`",
        "`sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a PhaseX Wave-1 brownfield case root."
    )
    parser.add_argument(
        "--system-root",
        required=True,
        help="Path to the existing system or brownfield repository root.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Target PhaseX case directory, for example tmp/local-artifacts/<case>/phase-x.",
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(PROFILE_OUTPUTS.keys()),
        help="PhaseX Wave-1 profile to scaffold.",
    )
    parser.add_argument("--case-name", help="Optional case name override.")
    parser.add_argument("--version", default="v-next", help="Case version label.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty output directory.",
    )
    return parser.parse_args()


def ensure_output_dir(path: Path, force: bool) -> None:
    if path.exists() and any(path.iterdir()) and not force:
        raise SystemExit(
            f"Refusing to scaffold into non-empty directory: {path}\n"
            "Use --force only when you explicitly want to refresh PhaseX target files."
        )
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def infer_case_name(output_dir: Path) -> str:
    if output_dir.name.startswith("phase-x") and output_dir.parent.name:
        return output_dir.parent.name
    return output_dir.name


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def build_manifest(
    *,
    case_name: str,
    version: str,
    system_root: Path,
    output_dir: Path,
    profile: str,
) -> str:
    lines = [
        "# PhaseX Wave-1 Manifest",
        "",
        "## Identity",
        "",
        f"- case_name: `{case_name}`",
        f"- version: `{version}`",
        f"- system_root: `{display_path(system_root)}`",
        f"- output_dir: `{display_path(output_dir)}`",
        f"- selected_profile: `{profile}`",
        "",
        "## Official Entry",
        "",
        "- skill: `skills/wff-x/`",
        "- bootstrap: `docs/phases/phase-x/phaseX-session-bootstrap.md`",
        "- decision_tree: `docs/phases/phase-x/phaseX-wave1-profile-decision-tree-v0.1.md`",
        "- stage_family: `reference-packages/phasex-brownfield-refactoring/`",
        "",
        "## Profile Rule",
        "",
        f"- execution_path: {PROFILE_RULES[profile]['path']}",
        f"- typical_exit: {PROFILE_RULES[profile]['typical_exit']}",
        "",
        "## Brownfield Boundary",
        "",
        "- Keep current-state truth separate from target-state recommendation.",
        "- Do not silently widen a bounded slice into a full-system redesign.",
        "- Record uncertainty explicitly when the repository does not expose enough evidence.",
        "- If the case no longer fits a Wave-1 profile honestly, stop and re-plan instead of fake-fitting it.",
        "",
        "## Method Backbone",
        "",
    ]

    for item in PROFILE_METHOD_BACKBONES[profile]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
        "## Required Outputs",
        "",
        ]
    )

    for _, filename, title, _ in PROFILE_OUTPUTS[profile]:
        lines.append(f"- `{filename}`: authored target for {title}")

    lines.extend(
        [
            "- `phasex-wave1-manifest.md`: profile and boundary record for this case root",
            "",
            "## Authoring Order",
            "",
        ]
    )
    for index, (_, _, title, _) in enumerate(PROFILE_OUTPUTS[profile], start=1):
        lines.append(f"{index}. {title}")
    lines.extend(
        [
            "",
            "## Downstream Intent",
            "",
            "- `assessment-only`: decide whether more work is justified",
            "- `technical-refactor`: protect brownfield change before implementation",
            "- `target-driver`: package the bounded change for Phase-1 or Phase-3 consumption",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_skill_stub(
    *,
    skill_id: str,
    skill_title: str,
    template_path: str,
    system_root: Path,
    output_dir: Path,
    filename: str,
    profile: str,
) -> str:
    return "\n".join(
        [
            f"# {skill_title}",
            "",
            "## Status",
            "",
            "- state: `fresh-target`",
            "- authoring_mode: `derive-from-brownfield-system-and-official-wave-1-pack`",
            f"- selected_profile: `{profile}`",
            "",
            "## Inputs",
            "",
            f"- system_root: `{display_path(system_root)}`",
            f"- official_template: `{template_path}`",
            f"- case_root: `{display_path(output_dir)}`",
            "",
            "## Rules",
            "",
            "- Treat the existing system as the source of current-state truth.",
            "- Do not copy earlier PhaseX case prose as if it were current evidence.",
            "- Keep observed facts, inferences, and recommendations clearly separated.",
            "- If evidence is too thin, record uncertainty instead of broadening scope to fake completeness.",
            "",
            "## Next Step",
            "",
            "- Replace this stub with a complete Wave-1 output for the selected profile.",
            "",
            f"<!-- scaffolded_target: {filename} -->",
            "",
        ]
    )


def _prefix_packet_field(field_name: str, lines: list[str]) -> list[str]:
    prefixed = [f"- {field_name}:"]
    for line in lines:
        prefixed.append(f"  {line}" if line else "")
    return prefixed


def build_target_driver_p1_packet_lines(system_label: str) -> list[str]:
    return _prefix_packet_field(
        "px_to_p1_change_source_packet",
        [
            "- packet_type: `P1 Source Input Packet`",
            "- packet_subtype: `existing-system-change`",
            f"- current_state_summary: `{system_label}` is treated as an existing system with partial scaffold evidence and review-bound current-state facts.",
            "- target_change_summary: Build a bounded target-driver intake that can become PRD scope without hiding compatibility risk.",
            "- observed_business_facts:",
            "  - The selected profile is `target-driver`.",
            "  - The case needs current-state evidence, target semantics, protected behavior, and route decision recorded together.",
            "  - The initial scaffold does not prove owner sign-off or production readiness.",
            "- inferred_business_semantics:",
            "  - The target change should prioritize source-truth preservation over broad redesign.",
            "  - P1 should expand only accepted packet facts and should keep unknowns review-bound.",
            "- legacy_behaviors_to_preserve:",
            "  - Existing public behavior remains protected until a compatibility strategy says otherwise.",
            "  - Existing data and runtime assumptions remain protected until P2 documents migration and rollback.",
            "- source_conflicts: none confirmed at scaffold time; conflicts remain review-bound.",
            "- explicit_unknowns:",
            "  - exact affected modules",
            "  - exact owner availability",
            "  - exact migration complexity",
            "  - exact test-protection coverage",
            "- non_goals: full-system redesign, production migration, UAT sign-off, hidden owner approval.",
            "- acceptance_pressure: Downstream PRD and ESP must not invent unregistered target scope or compatibility facts.",
            "- demand_change_evaluation:",
            "  - change_intent: create a constrained brownfield re-entry surface",
            "  - business_impact: reduces downstream fact drift and protects legacy behavior before implementation",
            "  - affected_users_workflows: product owner intake, architecture review, implementation action-card planning, review decision",
            "  - non_goals_scope_boundaries: no production readiness claim and no unbounded refactor",
            "  - proceed_decision: `proceed-to-P1`",
            "- demand_clarification_addendum:",
            "  - clarification_status: `not-answered`",
            "  - response_source: `scaffolded target-driver packet`",
            "  - target_success_boundary: downstream artifacts preserve packet facts, constraints, and unknowns",
            "  - acceptance_boundary: generated PRD, ESP, and action cards keep claim ceiling visible",
            "  - priority_users_workflows: product owner intake, architecture owner compatibility review, implementation owner action-card planning",
            "  - scope_confirmation: `review-bound`",
            "  - compatibility_confirmation: `protect-first until deeper evidence exists`",
            "  - conservative_default_if_unanswered: return to P1 or P2 instead of direct implementation",
            "  - remaining_review_bound_items: exact affected modules, owner availability, migration complexity, test-protection coverage",
            "- claim_ceiling: `review-bound brownfield source packet`",
        ],
    )


def build_target_driver_p2_packet_lines() -> list[str]:
    return _prefix_packet_field(
        "px_to_p2_architecture_change_intake_packet",
        [
            "- packet_type: `P2 Existing-System Architecture Change Intake Packet`",
            "- packet_subtype: `existing-system-architecture-change`",
            "- as_is_boundary_map: current repository, public surfaces, data stores, runtime assumptions, and tests require deeper scan before architecture change.",
            "- module_service_inventory: Change Intake, Current-State Evidence, Compatibility Boundary, Target Scope Definition, Downstream Handoff, Review Decision Loop.",
            "- data_storage_constraints: preserve existing data shape until P2 documents migration, backfill, rollback, and audit behavior.",
            "- interface_external_surface_constraints: preserve public interfaces unless compatibility strategy, versioning, and consumer impact are documented.",
            "- runtime_deployment_constraints: deployment posture remains review-bound until environment and operational dependencies are scanned.",
            "- compatibility_constraints: protected legacy behaviors and brownfield invariants are mandatory architecture inputs.",
            "- technical_health_pressure: target-driver slice needs evidence-led protection before code changes begin.",
            "- target_architecture_pressure: architecture must support source-bound handoff without turning Markdown views into truth.",
            "- unresolved_architecture_questions: affected modules, interface consumers, data migration needs, rollback path, test-protection coverage.",
            "- architecture_change_impact_triage:",
            "  - change_impact_level: `AC-2`",
            "  - compatibility_strategy: `preserve-interface-first`",
            "  - migration_strategy: `review-bound until P2 scan`",
            "  - rollback_strategy: `protect legacy behavior and require explicit rollback notes`",
            "  - decision_gate_status: `review-bound-provisional`",
            "- evidence_state_ledger: scaffold-level evidence only; deeper PX scan or P2 analysis required for stronger claims.",
            "- recommended_P2_entry_points:",
            "  - `Stage-01 architecture boundary`",
            "  - `Stage-02 module/domain decomposition`",
            "  - `Stage-03 data/interface design`",
        ],
    )


def build_target_driver_packet(
    *,
    skill_title: str,
    template_path: str,
    system_root: Path,
    output_dir: Path,
    filename: str,
    profile: str,
) -> str:
    system_label = system_root.name or "existing-system"
    return TARGET_DRIVER_PACKET_TEMPLATE.format(
        skill_title=skill_title,
        profile=profile,
        system_root_display=display_path(system_root),
        template_path=template_path,
        output_dir_display=display_path(output_dir),
        filename=filename,
        system_label=system_label,
        target_driver_p1_packet="\n".join(build_target_driver_p1_packet_lines(system_label)),
        target_driver_p2_packet="\n".join(build_target_driver_p2_packet_lines()),
    )


def emit_phasex_claim_control_sidecars(
    *,
    output_dir: Path,
    case_name: str,
    profile: str,
    generated_files: list[Path],
) -> dict[str, object]:
    claim_id = f"PX-{profile.upper()}-001"
    claims = [
        ClaimRecord(
            id=claim_id,
            kind="phasex_profile_boundary",
            text=f"PhaseX case {case_name} uses the {profile} profile boundary.",
            source_refs=["phasex-wave1-manifest.md#selected_profile"],
        )
    ]
    accepted_claim_ids = {claim.id for claim in claims}
    artifacts = []
    for artifact_path in generated_files:
        artifact_id = f"px:{artifact_path.stem}"
        route_decision = phasex_claim_control_route_decision(
            artifact_path=artifact_path,
            artifact_id=artifact_id,
        )
        result = emit_path_b_claim_control_sidecar(
            artifact_path=artifact_path,
            artifact_id=artifact_id,
            claims=claims,
            view_id=artifact_id,
            source_count=2,
            upstream_surface_paths=[],
        )
        px_audit = audit_phasex_artifact_claim_refs(
            artifact_path=artifact_path,
            accepted_claim_ids=accepted_claim_ids,
        )
        classifications = sorted(
            set(result["acceptance"].get("classifications", []))
            | set(px_audit.get("classifications", []))
        )
        overall_status = "pass" if result["acceptance"]["overall_status"] == "pass" and not classifications else "blocked"
        artifacts.append(
            {
                "artifact_path": str(artifact_path),
                "sidecar_path": result["sidecar_path"],
                "overall_status": overall_status,
                "claim_ceiling": "claim-controlled"
                if overall_status == "pass"
                else "blocked:phasex-claim-control-invalid",
                "route_decision": route_decision,
                "classifications": classifications,
                "unknown_claim_refs": px_audit["unknown_claim_refs"],
                "proposed_claim_refs": px_audit["proposed_claim_refs"],
                "conflicting_claim_refs": px_audit["conflicting_claim_refs"],
                "explicit_claim_refs": px_audit["explicit_claim_refs"],
            }
        )
    all_pass = artifacts and all(row["overall_status"] == "pass" for row in artifacts)
    report = {
        "artifact_kind": "phasex-claim-control-sidecar-report",
        "overall_status": "pass" if all_pass else "blocked" if artifacts else "review_bound",
        "claim_ceiling": "claim-controlled"
        if all_pass
        else "blocked:phasex-claim-control-invalid"
        if artifacts
        else "review-bound:missing-phasex-artifacts",
        "routing_policy": "default Path B for PX generated docs because they are multi-source downstream handoff artifacts",
        "creates_claims": False,
        "uses_rendered_views_as_truth": False,
        "artifacts": artifacts,
    }
    report_path = output_dir / "phasex-claim-control-report.json"
    write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {"report_path": str(report_path), "report": report}


def main() -> None:
    args = parse_args()
    system_root = Path(args.system_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    case_name = args.case_name or infer_case_name(output_dir)

    ensure_output_dir(output_dir, args.force)

    generated_files = [output_dir / "phasex-wave1-manifest.md"]
    write_text(
        generated_files[0],
        build_manifest(
            case_name=case_name,
            version=args.version,
            system_root=system_root,
            output_dir=output_dir,
            profile=args.profile,
        ),
    )

    for skill_id, filename, skill_title, template_path in PROFILE_OUTPUTS[args.profile]:
        content = (
            build_target_driver_packet(
                skill_title=skill_title,
                template_path=template_path,
                system_root=system_root,
                output_dir=output_dir,
                filename=filename,
                profile=args.profile,
            )
            if args.profile == "target-driver" and filename == "wff-x-intake-target-driver.md"
            else build_skill_stub(
                skill_id=skill_id,
                skill_title=skill_title,
                template_path=template_path,
                system_root=system_root,
                output_dir=output_dir,
                filename=filename,
                profile=args.profile,
            )
        )
        write_text(
            output_dir / filename,
            content,
        )
        generated_files.append(output_dir / filename)
    emit_phasex_claim_control_sidecars(
        output_dir=output_dir,
        case_name=case_name,
        profile=args.profile,
        generated_files=generated_files,
    )
    emit_human_review_surface(output_dir, "phasex")


if __name__ == "__main__":
    main()
