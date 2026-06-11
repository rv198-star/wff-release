# Stage-01 Rule Cards — architecture-definition-and-boundary-setting

## Usage

This file records atomic Stage-01 rules before runtime prose drafting. Each rule should remain individually auditable.

---

## RC-01
- statement: Stage-01 must freeze system boundary, constraints, capability map, and architecture direction before Stage-02 decomposition begins.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-02
- statement: Stage-01 must consume upstream handoff declaration states explicitly, including `present | absent | unknown | deferred`, rather than guessing missing inputs.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-03
- statement: If no Phase-1 handoff package or equivalent architecture-entry input exists, Stage-01 must refuse or remain blocked.
- type: prohibition
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-04
- statement: Stage-01 must output a system boundary statement that distinguishes in-scope, adjacent, and explicitly out-of-scope concerns.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-01

## RC-05
- statement: Stage-01 must output constraints separated into inherited constraints versus inferred or still-review-bound constraints.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-06
- statement: Stage-01 must not silently treat Phase-1 `key constraints` as a complete NFR baseline.
- type: prohibition
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-07
- statement: When NFR input is partial, absent, unknown, or deferred, Stage-01 must expand it into architecture-facing quality-attribute structure or preserve the gap explicitly.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-08
- statement: Stage-01 must output a capability map or equivalent capability-centered structural view that can guide Stage-02 decomposition.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-01

## RC-08A
- statement: Each Stage-01 capability group must declare at least `priority`, `maturity`, and `rationale`; a plain name-only capability list is not sufficient for D1.8 / D6.2.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-08B
- statement: If Stage-02 is expected to expose a support or shared-platform domain, Stage-01 must either align it explicitly in `capability_map` or reserve a named support/platform capability lane with a concrete justification.
- type: requirement
- source: `docs/phases/phase-2/phase-2-round1-validation-hardening-plan-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-09
- statement: Stage-01 must output key architecture decisions together with rationale and downstream impact.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-09A
- statement: Stage-01 architecture decisions must use a structured ADR shape with at least `Status`, `Context`, `Decision`, `Alternatives Considered`, `Consequences`, and `Evidence`; counting bare `AD-XX` bullets is not sufficient.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-09B
- statement: Stage-01 must maintain a machine-readable decision trace registry that covers every ADR and states the downstream artifact handoff target plus verification hook.
- type: requirement
- source: `docs/phases/phase-2/stage-2-traceability-fine-grained-lane-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-10
- statement: Mermaid diagram evidence is required in Stage-01, including a system-boundary/context view and a capability-map or equivalent structural view.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-11
- statement: Every Stage-01 output section that may contain uncertainty must preserve `status`, `source`, `confidence`, `verification`, `assumptions`, and `open_questions` semantics.
- type: requirement
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-12
- statement: TOGAF four domains may be used only as completeness/review lens and must not replace the Stage-2 four-substage execution backbone.
- type: boundary
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-13
- statement: SOA-lite, SOMA, and BPMN may appear only as sidecar or review lens and must not enter Stage-01 as default runtime method backbone.
- type: boundary
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-14
- statement: `ddd-reference` is the primary source for boundary language and capability/bounded-context framing in Stage-01.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-01

## RC-15
- statement: `software-architecture-in-practice` is the primary source for architecture direction, quality-attribute framing, and review logic in Stage-01.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-01

## RC-16
- statement: `diagram-expression` is the primary source for Stage-01 diagram expression discipline and evidence-vs-handoff diagram quality.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-01

## RC-17
- statement: `iso-25010-quality-model` may be used as a supporting taxonomy only when it directly helps expand partial NFR input into architecture-facing quality attributes.
- type: exception
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 2
- confidence: medium-high
- applies_to_stage: Stage-01

## RC-18
- statement: `eventstorming-glossary-cheat-sheet` may be used only as discovery vocabulary support when upstream scenario language is too weak to support boundary/capability discussion.
- type: exception
- source: `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- source_tier: Tier 2
- confidence: medium-high
- applies_to_stage: Stage-01

## RC-19
- statement: Stage-01 must hand off to Stage-02 with enough structure that decomposition can start without re-deriving boundary, constraint posture, or architecture direction from scratch.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-20
- statement: Stage-01 must not collapse review-bound assumptions or placeholder diagrams into approved architecture truth.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-21
- statement: Stage-01 must output a boundary-level security architecture sketch that identifies trust boundaries, identity/access posture, and audit-sensitive edges even when detailed security design is deferred.
- type: requirement
- source: `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-21A
- statement: Stage-01 security architecture sketch must explicitly record auth-sequence direction, a dedicated authentication sequence diagram, and key-management posture; a generic RBAC-only note is not sufficient for D1.4.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-22
- statement: Stage-01 must output an order-of-magnitude capacity estimation so downstream stages do not inherit a scale vacuum just because exact numbers are not yet known.
- type: requirement
- source: `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01

## RC-22A
- statement: Each forbidden assumption carried into Stage-01 must cite verification evidence or explicit evidence strength; source-plus-status alone is not sufficient for D1.7.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-01
