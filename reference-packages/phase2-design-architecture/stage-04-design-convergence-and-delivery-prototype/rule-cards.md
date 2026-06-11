# Stage-04 Rule Cards — design-convergence-and-delivery-prototype

## RC-01
- statement: Stage-04 must converge Stage-01~03 outputs into one coherent delivery-oriented design package.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-04

## RC-02
- statement: Stage-04 must preserve upstream decision rationale and unresolved review-bound items.
- type: requirement
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-03
- statement: If Stage-03 handoff is missing or unusable, Stage-04 must refuse or remain blocked.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-04
- statement: Stage-04 must output design verification notes that explain readiness and known limits.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-04

## RC-04A
- statement: Stage-04 design verification notes must record verification method, acceptance rule, residual gap, and linked RBI/WP where applicable; result-plus-evidence only is not sufficient for implementation-facing convergence.
- type: requirement
- source: `docs/phases/phase-2/phase-2-stage-module-scorecard-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-04B
- statement: Stage-04 must maintain replay-backed verification evidence for at least the happy path, a failure/clarification path, and an implementation-handoff consumption path; design verification rows alone are not sufficient once the Phase-2 package claims implementation-facing maturity.
- type: requirement
- source: `docs/phases/phase-2/stage-2-traceability-fine-grained-lane-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-05
- statement: Stage-04 must provide a delivery-prototype-oriented representation or equivalent structured expression.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-04

## RC-06
- statement: Handoff package must be implementation-consumable and include explicit unresolved items.
- type: requirement
- source: `templates/handoff-checklist.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-07
- statement: Stage-04 must not mask unresolved risks as completed design certainty.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-08
- statement: Mermaid convergence evidence is required.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-09
- statement: Declaration-state and NFR handling semantics must remain explicit in final handoff package.
- type: requirement
- source: `templates/handoff-contract.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-10
- statement: TOGAF/SOA-lite lens usage must remain optional and must not redefine Stage-04 output structure.
- type: boundary
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-11
- statement: Provisional and review-bound items in final package must preserve provenance/confidence/verification fields.
- type: requirement
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-12
- statement: Stage-04 must explicitly state downstream consumption rule for review-bound content.
- type: requirement
- source: `templates/handoff-contract.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-13
- statement: Stage-04 must preserve the dominant bottleneck hypothesis and alternative-analysis evidence from Stage-03 rather than collapsing it into a recommendation-only summary.
- type: requirement
- source: `reference-packages/phase2-design-architecture/stage-03-data-storage-and-interface-design/skill-contract.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-04

## RC-14
- statement: Stage-04 must explicitly distinguish acceptable mainstream baseline from constraint-dominant optimum candidate when that distinction matters.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-04

## RC-15
- statement: Stage-04 must not regress a stronger candidate into an unexplained mainstream default just because the default is easier to narrate or implement.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-16
- statement: Stage-04 must output a coarse-grained implementation task sketch so downstream implementation planning can start without reverse-engineering the design package.
- type: requirement
- source: `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-17
- statement: Stage-04 implementation task sketch must stay at slice/module/work-package level and must not freeze class, method, file, or ticket-level design.
- type: boundary
- source: `docs/phases/phase-2/phase-2-completion-and-phase-3-guidance-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-18
- statement: Stage-04 must surface unresolved lifecycle ownership, command-boundary, and public-name closure contradictions instead of hiding them inside a convergence summary.
- type: requirement
- source: `docs/phases/phase-2/stage-2-retrospective-and-optimization-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-19
- statement: Stage-04 readiness wording must not exceed the package's verification, confidence, and realizability evidence.
- type: prohibition
- source: `templates/handoff-checklist.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-19A
- statement: The final execution-report formal state must not silently exceed Stage-04 `strongest_supported_readiness_label` unless an explicit override rationale is recorded and auditable.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-20
- statement: Each implementation slice/work-package in Stage-04 must record completion signal and acceptance criteria; workflow anchors alone are not sufficient for D4.2.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-21
- statement: Every RBI must bind to a spike/work-package or be explicitly tagged out-of-current-phase-scope with responsible party; floating RBI rows do not satisfy D4.6 / D4.10.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-21A
- statement: Stage-04 must maintain a machine-readable RBI trace registry that covers every RBI and states its downstream implementation-facing handoff rule.
- type: requirement
- source: `docs/phases/phase-2/stage-2-traceability-fine-grained-lane-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-22
- statement: Optimality review must explicitly distinguish acceptable baseline from optimal candidate using structured fields, including why the chosen path is better than merely acceptable and how reversible the choice is.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04
