# Stage-02 Rule Cards — domain-module-service-decomposition

## RC-01
- statement: Stage-02 must decompose Stage-01 capability structure into explicit domain/module/service candidates.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-02

## RC-02
- statement: Stage-02 must preserve Stage-01 boundary constraints and must not re-open scope silently.
- type: requirement
- source: `reference-packages/phase2-design-architecture/stage-01-architecture-definition-and-boundary-setting/skill-contract.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-02

## RC-03
- statement: If Stage-01 handoff is missing or unusable, Stage-02 must refuse or remain blocked.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-04
- statement: Domain boundaries must have explicit responsibility statements and ownership notes.
- type: requirement
- source: `ddd-reference`
- source_tier: Tier 3
- confidence: high
- applies_to_stage: Stage-02

## RC-05
- statement: Module boundaries must not duplicate core responsibilities across modules without explicit rationale.
- type: prohibition
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-02

## RC-06
- statement: Service candidates must include dependency-facing role and collaboration direction.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-02

## RC-06A
- statement: Stage-02 service candidates must expose canonical `home_module` and `service_type` fields so Stage-03 and validation tooling do not need to infer service ownership from prose alone.
- type: requirement
- source: `docs/phases/phase-2/phase-2-stage-module-scorecard-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-07
- statement: Dependency/collaboration map must be explicit and decomposition-ready for Stage-03.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-02

## RC-07A
- statement: Stage-02 dependency/collaboration map must include anti-cycle rules and an explicit violation consequence; a one-way diagram alone is not sufficient for D2.6.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-08
- statement: Mermaid diagram evidence is required for structure and dependency views.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-09
- statement: Declaration-state and NFR truth-boundary semantics from Stage-01 must remain explicit.
- type: requirement
- source: `templates/handoff-contract.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-10
- statement: TOGAF domains can be used only as completeness checks and must not replace Stage-2 skeleton.
- type: boundary
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-11
- statement: SOA-lite/SOMA/BPMN may be sidecar references only and must not become default decomposition format.
- type: boundary
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-02

## RC-12
- statement: Provisional decomposition content must preserve status/source/confidence/verification and unresolved assumptions.
- type: requirement
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-13
- statement: Aggregate lifecycle states must be closed by declared owning writers and must not require downstream read-only consumers to mutate upstream truth.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-02

## RC-13A
- statement: Stage-02 lifecycle ownership closure must include a conflict detection rule that explains how hidden owner overlap or write-ownership contradictions are surfaced before Stage-03 handoff.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-13B
- statement: Stage-02 must provide a machine-readable aggregate catalog that binds each authoritative object to owning domain, owning module, authoritative service, lifecycle coverage, and public-boundary posture.
- type: requirement
- source: `docs/phases/phase-2/phase-2-stage-module-scorecard-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-13C
- statement: Every aggregate listed in Stage-02 `aggregate_catalog` must appear once in an explicit lifecycle-coverage table, including owner writer, trigger events, terminal/failure exit, and Mermaid binding or justified non-Mermaid lifecycle expression.
- type: requirement
- source: `docs/phases/phase-2/phase-2-stage-module-scorecard-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02
