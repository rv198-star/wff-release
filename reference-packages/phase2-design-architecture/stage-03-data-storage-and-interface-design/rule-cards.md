# Stage-03 Rule Cards — data-storage-and-interface-design

## RC-01
- statement: Stage-03 must convert Stage-02 decomposition into explicit data/storage/interface design artifacts.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-03

## RC-02
- statement: Stage-03 must preserve Stage-02 boundary and dependency assumptions rather than re-splitting module/service responsibilities.
- type: requirement
- source: `reference-packages/phase2-design-architecture/stage-02-domain-module-service-decomposition/skill-contract.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-03

## RC-03
- statement: If Stage-02 handoff is missing or unusable, Stage-03 must refuse or remain blocked.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-04
- statement: Data model must align with decomposition boundaries and identify ownership.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-03

## RC-05
- statement: Storage strategy must include constraint rationale and explicit tradeoff notes.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-03

## RC-05A
- statement: Stage-03 storage design must connect hot access paths to explicit index posture; schema-level `index_hint` strings alone do not satisfy implementation-facing index reasoning.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-06
- statement: Interface contracts must define input/output boundaries, error behavior, and compatibility notes.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-03

## RC-06C
- statement: Stage-03 must define a canonical response/error contract that distinguishes `business_error` from `system_error`, plus retryability and caller-action posture; endpoint-local status codes alone are not sufficient.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-06A
- statement: Stage-03 API endpoint drafts must provide real JSON-shaped request and response examples for the core public endpoints; field-summary prose alone does not satisfy the contract-example requirement.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-06B
- statement: Core Stage-03 interface contracts must include structured schema representation using JSON Schema or TypeScript interface shape; prose-only content shape is not sufficient for D3.4.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-07
- statement: Interaction flow must map cross-boundary dependencies and highlight critical failure paths.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-03

## RC-08
- statement: Mermaid diagram evidence is required for data structure and interaction flow views.
- type: requirement
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-08A
- statement: Stage-03 security architecture outline must explicitly record auth-sequence direction, token posture, and key-management posture; generic trust-boundary prose alone is not sufficient for D3.7.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-09
- statement: NFR declaration semantics and review-bound markers must remain explicit.
- type: requirement
- source: `templates/handoff-contract.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-10
- statement: Stage-03 must not present tentative contract assumptions as approved implementation constraints.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-11
- statement: TOGAF/SOA-lite lens usage is optional and must not replace Stage-03 output structure.
- type: boundary
- source: `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-12
- statement: Provisional data/interface content must preserve provenance/confidence/verification fields.
- type: requirement
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-13
- statement: Stage-03 must identify the dominant bottleneck or constraint that governs architecture choice when major tradeoffs exist.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-03

## RC-14
- statement: When dominant constraints are strong, Stage-03 must compare materially different architecture candidates rather than only refining a mainstream baseline.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-03

## RC-15
- statement: Stage-03 must explain why the default or mainstream solution is insufficient when a stronger constraint-dominant candidate is selected.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-03

## RC-16
- statement: Stage-03 must not stop at the first acceptable solution if dominant constraints suggest a stronger but less mainstream pattern should be evaluated.
- type: prohibition
- source: `docs/stage-skill-construction-lifecycle-reference-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-17
- statement: Aggregate lifecycle states and authoritative write paths must align with declared owning modules; downstream read-only consumers must not be required to mutate upstream truth.
- type: requirement
- source: `software-architecture-in-practice`
- source_tier: Tier 3
- confidence: medium-high
- applies_to_stage: Stage-03

## RC-18
- statement: Each authoritative business mutation must have one primary command boundary unless a non-overlapping multi-step split is explicitly documented.
- type: requirement
- source: `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- source_tier: Tier 2
- confidence: high
- applies_to_stage: Stage-03

## RC-19
- statement: Public-boundary objects, contracts, snapshots, and endpoint-visible names must be registry-closed across schema, contracts, and API drafts, or explicitly marked derived/deferred.
- type: requirement
- source: `templates/handoff-contract.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-20
- statement: Stage-03 technology selection evidence marked as externally verified must include both source URL and verification date; URL-only evidence is not sufficient for D3.8.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-20A
- statement: Stage-03 technology selection evaluation must compare candidates across multiple engineering dimensions such as reliability, performance/capacity, scalability, maintainability, cost, security/compliance, and deployment complexity; short summary-only matrices do not satisfy D3.8.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-21
- statement: Key list/read endpoints in Stage-03 must record explicit pagination and rate-limit posture; hiding them in generic prose is not sufficient for D3.5.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-21A
- statement: Implementation-facing Stage-03 endpoints must record response profile, retryability posture, and idempotency rule; otherwise downstream services are forced to invent incompatible caller behavior.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-22
- statement: Stage-03 dominant bottleneck hypothesis must include a measurement plan, threshold, and spike scope; naming the bottleneck alone is not sufficient for D3.9.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-23
- statement: Architecture alternative candidates must state pros, cons, cost burden, fit scenario, and reversibility posture in a structured form; label-only alternatives are not sufficient for D3.10 / D3.13.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-24
- statement: Public boundary registry closure must include a namespace rule and apply namespace values to boundary-visible names; origin/status/closure alone is not sufficient for D3.12.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-24A
- statement: Stage-03 must preserve canonical Stage-02 domain-event names in a dedicated carry-forward mapping or in explicit scenario/flow touchpoints; implicit paraphrase without mapping is not sufficient for cross-stage closure.
- type: requirement
- source: `docs/phases/phase-2/phase-2-round1-validation-hardening-plan-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-24B
- statement: Stage-03 must maintain a machine-readable contract trace registry for core contracts, endpoints, event mappings, or public-boundary items so fine-grained handoff trace units can be bound without prose-only inference.
- type: requirement
- source: `docs/phases/phase-2/stage-2-traceability-fine-grained-lane-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03
- type: requirement
- source: `docs/phases/phase-2/phase-2-round1-validation-hardening-plan-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-25
- statement: Stage-03 schema draft must include per-table field registries with `field_name / data_type / nullable / constraints / index_hint`; one-line `fields` strings alone are not sufficient for implementation-facing schema depth.
- type: requirement
- source: `docs/phases/phase-2/phase-2-v7-fresh-proof-r3-comprehensive-review-v2.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-25A
- statement: Stage-03 schema field registries must use implementation-facing, storage-aware data types; placeholder types such as `string`, `number`, or `object` are not sufficient once the package claims implementation-planning depth.
- type: requirement
- source: `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-26
- statement: Every Stage-03 scenario row must carry quantified acceptance criteria and an explicit measurement hook; failure-note-only scenarios are not sufficient for implementation planning.
- type: requirement
- source: `docs/phases/phase-2/phase-2-v7-fresh-proof-r3-comprehensive-review-v2.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-26A
- statement: Stage-03 scenario coverage must include at least two explicitly labeled concurrent-conflict scenarios with visible coordination strategy; generic happy-path/failure-path matrices are not sufficient once authoritative writes can race.
- type: requirement
- source: `docs/phases/phase-2/phase-2-skill-optimization-plan-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-27
- statement: Stage-03 technology selection evaluation matrices must compare each candidate across at least 10 explicit dimensions with non-placeholder values; summary-plus-decision tables are not sufficient for D3.8 depth.
- type: requirement
- source: `docs/phases/phase-2/phase-2-skill-optimization-plan-v1.0.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03
