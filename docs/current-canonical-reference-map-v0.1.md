# Current Canonical Reference Map（v0.1）

## Purpose

This file is a maintenance-oriented navigation map for a large repository.

Its job is to reduce forgetting and re-orientation cost by answering:

1. which documents define the current repo-level truth
2. which documents are the current best entry points for each phase
3. where historical planning material should be read only as context, not as the active rule

## Core Rule

When a dated file under `docs/plans/` conflicts with a stable document outside `docs/plans/`, prefer the stable document outside `docs/plans/`.

Use `docs/plans/` for:

- design evolution
- checkpoint history
- implementation archaeology

Use the documents below for current repo behavior.

## Repo-Level First Read

Read these first when re-entering the project:

1. `docs/v1.2-design-principles-v0.1.md` when the work belongs to the `v1.2` redesign / simplification / scoring track
2. `docs/v1.2-phase-thinking-mode-split-v0.1.md` when the work concerns `P1/P2` reasoning posture, loop intensity, or checklist-vs-deep-loop boundary
3. `runtime-deps/mindthus/source/skills/wae/SKILL.md` when the work concerns Workflow / Agentic / Evidence control boundaries, mainline vs optional lane placement, script-vs-judgment boundary, or output-value quality risk
4. `runtime-deps/mindthus/source/skills/edsp/SKILL.md` when BTGSB exposes ambiguous structural diagnosis, proposition testing, trend reading, or concrete scenario selection
5. `docs/v1.2-mainline-scoring-and-acceptance-matrix-v0.1.md` when the work concerns phase scoring, acceptance verdicts, or stable review criteria
6. `docs/v1.2-script-surface-classification-v0.1.md` when the work concerns actual script reduction, especially the `Phase-3` control surface
7. `docs/current-project-consensus.md`
8. `docs/current-canonical-reference-map-v0.1.md`
9. `docs/governance/document-lifecycle-policy-v0.1.md`
10. `docs/phase-retrospective-and-next-step.md`

## Cross-Phase Canonical Docs

### Method stack

- `runtime-deps/mindthus/README.md` is the entrypoint for reusable methodology source.
- `runtime-deps/mindthus/source/skills/3l5s/` contains the primary 3L5S / BTGSB problem-processing kernel and recursive loop.
- `runtime-deps/mindthus/source/skills/edsp/` contains qualitative structural judgment and scenario projection.
- `runtime-deps/mindthus/source/skills/wae/` contains the Workflow / Agentic / Evidence control-boundary method.
- `runtime-deps/mindthus/source/skills/tvg/` contains Thinking Value-Gain method and trace discipline.
- `runtime-deps/mindthus/source/skills/sela/` contains the system-efficiency-over-local-advantage strategic lens.
- Archived local method copies live under `archive/docs/methods/` for historical comparison only.

### Project-wide governance

- `docs/v1.2-design-principles-v0.1.md` when reviewing or implementing `v1.2` design changes
- `docs/v1.2-phase-thinking-mode-split-v0.1.md` when deciding how `P1` and `P2` should differ in reasoning mode and review posture
- `runtime-deps/mindthus/source/skills/wae/SKILL.md` when deciding which logic stays workflow-controlled, which returns to agentic judgment, which requires evidence capping, and which remains optional
- `runtime-deps/mindthus/source/skills/edsp/SKILL.md` inside BTGSB when deciding whether a fuzzy issue is a structure problem or a configuration problem, and whether to stop at L1 or run L1 → L2
- `docs/v1.2-mainline-scoring-and-acceptance-matrix-v0.1.md` when deciding how a phase should be scored and how `PASS / RETURN / BLOCKED` should be assigned
- `docs/v1.2-script-surface-classification-v0.1.md` when deciding which scripts must stay, which should become optional, and which should be merged or retired
- `docs/current-project-consensus.md`
- `docs/governance/document-lifecycle-policy-v0.1.md`
- `docs/governance/phase-admission-matrix-v0.1.md`
- `docs/governance/artifact-traceability-layer-v0.md`
- `docs/governance/artifact-traceability-minimum-rules-v0.1.md`
- `docs/phases/phase-2/engineering-spec-pack-v0.1.md`

### Historical planning boundary

- `docs/plans/README.md`

Interpretation:

- `docs/plans/` is retained project memory
- it is not the primary source of current boundaries, gates, or runtime expectations

## Phase-1 Current Canonical Docs

Use these as the active Phase-1 reference set:

- `docs/phases/phase-1/phase-1-session-bootstrap.md`
- `docs/phases/phase-1/phase-1-skills-structure-v0.1.md`
- `docs/phases/phase-1/product-requirements-stage-package-v0.md`
- `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- `docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- `docs/phases/phase-1/phase-1-prd-to-phase-2-readiness-assessment-v0.1.md`
- `docs/phases/phase-1/phase-1-execution-report-template-v0.1.md`

Use these when Phase-1 thinking depth or quality calibration is under discussion:

- `docs/phases/phase-1/phase-1-thinking-loop-v0.1.md`
- `docs/phases/phase-1/phase-1-thinking-runtime-layer-v0.1.md`
- `docs/phases/phase-1/phase-1-depth-mode-runtime-protocol-v0.1.md`
- `docs/phases/phase-1/phase-1-thinking-runtime-synthesis-v0.1.md`
- `docs/phases/phase-1/phase-1-prd-excellence-scoring-rubric-v0.1.md`

## Phase-2 Current Canonical Docs

Use these as the active Phase-2 reference set:

- `docs/phases/phase-2/phase-2-session-bootstrap.md`
- `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- `docs/source-registers/design-architecture-source-library-seed-v0.1.md`
- `docs/source-registers/design-architecture-stage-source-register-v0.1.md`
- `docs/source-registers/design-architecture-stage-source-unit-coverage-ledger-v0.1.md`
- `docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md`
- `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- `docs/phases/phase-2/phase-2-execution-report-template.md`
- `docs/phases/phase-2/phase-2-completion-and-phase-3-guidance-v0.1.md`

Use these when Phase-2 quality/risk rules are under discussion:

- `docs/phases/phase-2/phase-2-realizability-architecture-review-rule-v0.1.md`
- `docs/phases/phase-2/phase-2-external-dependency-feasibility-rule-v0.1.md`
- `docs/phases/phase-2/phase-2-case-backed-validation-matrix-v0.1.md`

## Phase-3 Current Canonical Docs

Use these as the active Phase-3 reference set:

- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- `docs/phases/phase-3/development-stage-package-v0.md`
- `docs/source-registers/development-implementation-source-library-seed-v0.1.md`
- `docs/source-registers/development-stage-source-register-v0.2.md`
- `docs/source-registers/development-stage-source-unit-coverage-ledger-v0.1.md`

## Phase-4 Current Canonical Docs

Use these as the active Phase-4 reference set:

- `docs/phases/phase-4/phase-4-skill-architecture-design-v0.1.md`
- `docs/phases/phase-4/testing-validation-stage-package-v0.md`
- `docs/source-registers/testing-validation-source-index-v0.1.md`
- `docs/source-registers/testing-validation-source-library-seed-v0.1.md`
- `docs/source-registers/testing-validation-source-register-v0.1.md`
- `docs/source-registers/testing-validation-source-unit-coverage-ledger-v0.1.md`
- `docs/release-readiness-stage-package-v0.md`

Important boundary:

- Phase-4 now contains the 3-stage validation mainline
- release-readiness is treated as an optional `Phase-4 Stage-04` extension, not as a separate default lifecycle phase

## Incubating Extension Track

These documents are intentionally tracked so the project does not forget them, but they do not yet change the default P1-P4 lifecycle.

- `docs/phases/phase-x/phaseX-brownfield-and-refactoring-stage-package-v0.md`

Interpretation:

- `PhaseX` is an incubation track for brownfield entry, legacy modernization, refactoring, migration, and multi-system integration
- it is not the default mainline after Phase-4
- it should currently be read as a design-and-planning draft for a special sidecar family
- first implementation wave should stay narrow and prioritize the minimum viable set rather than all 10 proposed skills

## Operational Reading Order by Task

### If you are resuming implementation work

Read:

1. `docs/current-project-consensus.md`
2. `docs/current-canonical-reference-map-v0.1.md`
3. the current phase architecture doc
4. the current phase stage-package doc
5. the current phase session bootstrap doc if it exists

### If you are reviewing an old design choice

Read:

1. the current canonical doc first
2. `docs/plans/README.md`
3. the dated plan/checkpoint file only as historical context

### If you are repairing drift or confusion

Check:

1. whether the statement comes from `docs/plans/`
2. whether a newer stable doc outside `docs/plans/` already supersedes it
3. whether the current skill/script behavior matches the stable doc rather than the old plan

## One-Line Summary

This map exists to keep a large repo re-enterable: current truth first, historical plans second.
