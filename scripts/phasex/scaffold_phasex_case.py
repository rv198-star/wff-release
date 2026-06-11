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
from common.claim_control_runtime import ClaimRecord, emit_path_b_claim_control_sidecar
from phasex.phasex_claim_routing import audit_phasex_artifact_claim_refs, phasex_claim_control_route_decision

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    return "\n".join(
        [
            f"# {skill_title}",
            "",
            "## Status",
            "",
            "- state: `fresh-target`",
            "- authoring_mode: `derive-from-brownfield-system-and-official-wave-1-pack`",
            f"- selected_profile: `{profile}`",
            "- claim_ceiling: `review-bound brownfield source packet; not owner sign-off, UAT, production readiness, or risk acceptance`",
            "",
            "## Inputs",
            "",
            f"- system_root: `{display_path(system_root)}`",
            f"- official_template: `{template_path}`",
            f"- case_root: `{display_path(output_dir)}`",
            "",
            "## 1. Document Metadata",
            "",
            f"- document_name: `{filename}`",
            "- skill_id: `wff-x-intake-target-driver`",
            "- skill_name: `target-driver-intake`",
            "- mode: `target-driver`",
            "- status: `draft`",
            "",
            "## 2. Change Context",
            "",
            f"- change_point_statement: Package a bounded target change for `{system_label}` so downstream P1, P2, or P3 work starts from explicit brownfield facts instead of an empty prompt.",
            "- why_now: The existing system needs a controlled re-entry surface before long-form PRD, architecture, or action-card generation consumes it.",
            "- bounded_scope_definition: Preserve current behavior while introducing a traceable target-driver intake, compatibility boundary, and downstream handoff packet.",
            "- excluded_scope: Full-system redesign, production migration, UAT sign-off, hidden owner approval, and automatic acceptance of inferred business truth.",
            "- brownfield_non_goals: Do not treat scaffolded observations as complete repository analysis, and do not widen the slice beyond the selected target-driver profile.",
            "- brownfield_handoff_packet:",
            "  - phase1_consumption_notes: Use this packet as source context for a constrained PRD re-entry, keeping unknowns explicit.",
            "  - phase3_consumption_notes: Implementation action cards must preserve compatibility constraints and protected legacy behavior.",
            "  - compatibility_claim_ceiling: Evidence is scaffold-level and review-bound until a deeper PX scan or owner confirmation adds stronger proof.",
            "  - route_decision_rationale: `return-to-P1` is preferred when target semantics are not yet specified enough for direct implementation.",
            "",
            "## 2.3 Target Users",
            "",
            "| Role | Description | Need |",
            "| --- | --- | --- |",
            "| Product owner | Owns the target change and accepts the business boundary | Needs a concise source packet that separates observed facts, inferred semantics, and unknowns |",
            "| Architecture owner | Protects module, data, interface, and runtime compatibility | Needs a current-state boundary and architecture intake before design changes |",
            "| Implementation owner | Turns the accepted slice into action cards and code changes | Needs protected behavior, required prework, and explicit source refs |",
            "| Review stakeholder | Decides whether the brownfield slice should proceed, narrow, or return for clarification | Needs traceable decision evidence and unresolved questions |",
            "",
            "## 3. Core Business Objectives",
            "",
            "- Convert a brownfield target request into a constrained source packet that P1 can expand without inventing business truth.",
            "- Preserve current-state behavior and compatibility constraints while still allowing a target-state change to be planned.",
            "- Give P2 enough architecture intake to reason about modules, data, interfaces, runtime posture, migration, and rollback.",
            "- Give P3 enough implementation context to produce action cards with source-bound acceptance criteria and protected behavior.",
            "- Keep every unresolved fact review-bound instead of promoting scaffold output to confirmed system truth.",
            "",
            "## 3.2 Structured Problem List",
            "",
            "- Brownfield target requests often mix current facts, desired behavior, guessed semantics, and implementation preference in one narrative.",
            "- Downstream long documents can overfit the target request and silently lose compatibility constraints.",
            "- Architecture work can start without knowing which legacy behaviors, interfaces, data stores, or runtime assumptions are protected.",
            "- Implementation action cards can become generic tasks when source refs, acceptance pressure, and risk notes are missing.",
            "- Reviewers need a stop path when evidence is thin, not a polished document that hides uncertainty.",
            "",
            "## 3.3 Structured Opportunity List",
            "",
            "- Use a target-driver packet to turn brownfield uncertainty into explicit source facts, inferred semantics, and unresolved questions.",
            "- Use compatibility constraints and invariants as first-class inputs before PRD or architecture expansion.",
            "- Route simple protected changes directly toward implementation while sending semantic changes back through P1 or P2.",
            "- Keep proposed changes small enough that P3 action cards can preserve behavior, tests, and rollback evidence.",
            "- Register the PX packet as a visible source artifact so later phases consume the packet rather than guessing from Markdown stubs.",
            "",
            "## 3.4 User Narratives",
            "",
            "- As a product owner, I want the target-driver packet to explain the target change, affected workflows, and open questions so I can decide whether P1 re-entry is justified.",
            "- As an architecture owner, I want the packet to identify module, data, interface, and runtime pressures so I can protect compatibility before design synthesis.",
            "- As an implementation owner, I want protected behaviors and acceptance boundaries so action cards do not mutate legacy contracts accidentally.",
            "- As a reviewer, I want unresolved facts and claim ceilings to remain visible so I can block, narrow, or approve the route with evidence.",
            "",
            "## 4. Module Responsibility Matrix",
            "",
            "| module | primary_actor | core_objects | responsibility | input | output | exit_action | architectural note |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| Change Intake | Product owner | ChangeRequest, TargetDriver, ClaimCeiling | Capture the target change and separate desired outcome from current-state proof | target request, business reason, affected workflow | bounded target-driver statement and route candidate | approve source packet for P1 or return for clarification | preserve claim ceiling and do not treat inferred semantics as confirmed truth |",
            "| Current-State Evidence | Architecture owner | EvidenceRef, ObservedFact, SourceScope | Record current-state facts and evidence refs available from the existing system | repository path, observed files, available docs | observed fact ledger and evidence state | hand off evidence constraints to architecture intake | keep observed facts separate from target recommendation |",
            "| Compatibility Boundary | Architecture owner | CompatibilityConstraint, ProtectedBehavior, BrownfieldInvariant | Identify behavior that must not break while the target change is planned | legacy behavior, interface constraints, data constraints | compatibility matrix and invariant register | route design around protected surfaces | protect interfaces, persistence assumptions, and runtime behavior |",
            "| Target Scope Definition | Product owner | TargetScope, NonGoal, AcceptancePressure | Define the smallest change scope and explicit non-goals | target driver, excluded scope, priority users | scoped target packet and acceptance pressure | decide P1, P2, P3, or protect-first route | keep bounded scope ahead of implementation preference |",
            "| Downstream Handoff | Implementation owner | HandoffRequirement, RequiredPrework, ActionCardSeed | Convert the packet into phase-specific handoff obligations | P1 source packet, P2 architecture packet, constraints | downstream handoff requirements and prework list | open PRD, ESP, or action-card generation | downstream must consume registered packet facts, not freeform guesses |",
            "| Review Decision Loop | Review stakeholder | DecisionRecord, UnresolvedQuestion, RouteDecision | Decide whether the target change proceeds, narrows, or returns | evidence ledger, unknowns, risk notes | route decision and remaining review-bound items | register decision and next phase entry | review output is evidence, not new business truth |",
            "",
            "## 5. Core Business Objects",
            "",
            "| Object | Owner Module | Description |",
            "| --- | --- | --- |",
            "| ChangeRequest | Change Intake | The bounded target change, business reason, affected workflow, and claim ceiling. |",
            "| TargetDriver | Change Intake | The specific driver that explains why the brownfield change should exist now. |",
            "| ObservedFact | Current-State Evidence | A current-state fact tied to source scope and evidence refs. |",
            "| CompatibilityConstraint | Compatibility Boundary | A protected behavior, interface, data, or runtime rule that downstream work must preserve. |",
            "| BrownfieldInvariant | Compatibility Boundary | A legacy property that cannot be silently broken by target-state generation. |",
            "| TargetScope | Target Scope Definition | The minimal in-scope change and explicit out-of-scope boundary. |",
            "| HandoffRequirement | Downstream Handoff | A requirement that P1, P2, or P3 must carry forward with source refs. |",
            "| DecisionRecord | Review Decision Loop | The evidence-backed route decision and remaining review-bound items. |",
            "",
            "## 6. Key Business Flows",
            "",
            "### Brownfield target-driver re-entry flow",
            "",
            "1. Capture the target request and write the claim ceiling before interpreting implementation work.",
            "2. Scan the existing system for observed current-state facts, affected surfaces, and evidence refs.",
            "3. Separate observed facts, inferred business semantics, target recommendations, and explicit unknowns.",
            "4. Register compatibility constraints, protected legacy behavior, and brownfield invariants.",
            "5. Decide whether the change should return to P1, enter P2, go protect-first, direct to P3, or stop for review.",
            "6. Emit P1 source packet, P2 architecture intake packet, and P3 action-card seeds with the same source refs.",
            "7. Audit downstream generated artifacts against the packet and keep unresolved claims review-bound.",
            "",
            "## 7. Non-functional Requirements",
            "",
            "- Traceability: every downstream assertion must reference the PX packet, an accepted claim, or an explicit proposed claim.",
            "- Compatibility: protected behavior, public interfaces, data migration assumptions, and rollback posture must remain visible.",
            "- Evidence honesty: scaffolded facts are review-bound unless supported by deeper scan evidence or owner confirmation.",
            "- Operability: runtime and deployment assumptions must be captured before implementation work starts.",
            "- Auditability: unresolved questions, source refs, and route decisions must be machine-readable enough for gates and human review.",
            "",
            "## 8. Architectural Constraints",
            "",
            "- Do not infer a target architecture from the current repository name alone.",
            "- Do not break existing public interfaces without a compatibility strategy and rollback path.",
            "- Do not treat a target-driver packet as production readiness evidence.",
            "- Do not let implementation action cards introduce new product scope outside the registered target scope.",
            "- If module, data, or runtime evidence is thin, preserve a conservative default and route the question to review.",
            "",
            "## 9. Out of Scope (MVP)",
            "",
            "- Full repository audit beyond the selected target-driver profile.",
            "- Automatic migration planning without P2 architecture analysis.",
            "- Owner sign-off, UAT, production readiness, budget approval, or production risk acceptance.",
            "- Broad platform redesign or unbounded cleanup work.",
            "- Silent promotion of inferred semantics into accepted product truth.",
            "",
            "## P0",
            "",
            "- Target change statement with claim ceiling and route candidate.",
            "- Current-state observed fact ledger with evidence refs and explicit unknowns.",
            "- Compatibility constraints, protected legacy behaviors, and brownfield invariants.",
            "- P1 source packet and P2 architecture intake packet.",
            "- Downstream handoff requirements for implementation action cards.",
            "",
            "## P1",
            "",
            "- Deeper repository scan that strengthens evidence confidence for affected modules.",
            "- Owner or maintainer confirmation when available, recorded as optional evidence.",
            "- More precise migration, rollback, and test-protection plan.",
            "",
            "## P2",
            "",
            "- Wider brownfield refactoring roadmap across multiple target-driver slices.",
            "- Automated evidence extraction from repository structure and historical proof snapshots.",
            "- Portfolio-level compatibility governance for repeated PX re-entry cases.",
            "",
            *build_target_driver_p1_packet_lines(system_label),
            "",
            *build_target_driver_p2_packet_lines(),
            "",
            "## phase1_constrained_reentry_summary",
            "",
            "- affected_modules: Change Intake, Current-State Evidence, Compatibility Boundary, Target Scope Definition, Downstream Handoff, Review Decision Loop",
            "- impacted_surfaces: source packet, architecture intake, action-card handoff, review decision record",
            "- acceptance_criteria:",
            "  - PRD keeps observed facts, inferred semantics, and unknowns separate.",
            "  - ESP preserves compatibility constraints and architecture questions.",
            "  - Action cards reference accepted upstream claims and do not add target scope silently.",
            "- recommended_route: `return-to-P1`",
            "- third-party-dependency-manifest:",
            "  - dependency_id: `none-confirmed-at-scaffold-time`",
            "  - integration_change_type: `none`",
            "  - compatibility_requirement: `review-bound`",
            "",
            "## unresolved_questions",
            "",
            "| question_id | question | blocking_level | owner_hint | owner_availability | fallback_handling |",
            "| --- | --- | --- | --- | --- | --- |",
            "| PX-Q-001 | Which modules and interfaces are truly affected? | high | architecture owner | unknown owner | protect-first |",
            "| PX-Q-002 | Which legacy behaviors must be regression protected? | high | implementation owner | unknown owner | conservative default |",
            "| PX-Q-003 | Does the target change need P1 semantics or only P3 implementation? | medium | product owner | optional owner | enter-P1/P2 |",
            "| PX-Q-004 | What migration and rollback evidence is required? | medium | architecture owner | optional owner | review-bound |",
            "",
            "## downstream_route_recommendation",
            "",
            "- recommended_route: `return-to-P1`",
            "- route_rationale: The packet contains enough structured source truth to start P1, while architecture and implementation claims remain review-bound.",
            "- handoff_requirements: downstream phases must consume this packet and its sidecar, preserve claim ceilings, and emit proposed claims for new facts.",
            "",
            f"<!-- scaffolded_target: {filename} -->",
            "",
        ]
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
