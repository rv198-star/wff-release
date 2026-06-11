# Phase Admission Matrix（v0.1）

## 1. Purpose

This document unifies the current admission logic for the main downstream transitions:

- Phase-1 → Phase-2
- Phase-2 → Phase-3
- Phase-3 → Phase-4

The goal is to stop future case testing from reopening the same baseline questions about whether a downstream phase may start.

---

## 2. Interpretation rule

This matrix does **not** replace the detailed templates/rules/checklists.

It is the current consolidated reading of them.

Use it as:

- the first lookup for gate decisions
- a cross-phase consistency aid
- a starting point for audits and case reviews

---

## 3. Admission states

### `PASS`
- downstream may start normally

### `PASS with constrained/review-bound conditions`
- downstream may start
- but must explicitly preserve the declared limits and unresolved items

### `BLOCKED`
- downstream must not start as if the handoff were sufficient
- missing or unresolved items must be treated as blockers/remediation items

---

## 4. Phase-1 → Phase-2

### Required downstream handoff type
- design/architecture-consumable handoff

### Required convergence condition
- Unified Product Pack convergence state must be explicit

### PASS when
- Phase-1 core business deliverables are covered enough for design/architecture to consume
- handoff exists
- decision state exists
- critical unresolved items are clearly classified
- Unified Product Pack state is at least explicit and the handoff is usable

### Stage-02b skip handling

When Stage-02b (requirements-specification-deepening) was NOT executed:

- the handoff must include an explicit `stage_02b_skip_declaration` stating:
  - NFR state: at minimum, the Stage-02a NFR initial identification scan must be present
  - domain model state: `not-produced | partial-from-02a | deferred-to-phase-2`
  - information architecture state: `not-produced | partial-from-02a | deferred-to-phase-2`
  - impact assessment: what Phase-2 architecture work is affected by the absence of 02b outputs
  - mitigation: whether the NFR initial identification scan from 02a is sufficient for Phase-2 safe start, or additional work is needed

- this is compatible with both `PASS` and `PASS with constrained/review-bound conditions`:
  - `PASS`: if 02a NFR scan is rated `minimum_viable_for_phase2: yes` and impact is bounded
  - `PASS with constrained conditions`: if 02a NFR scan is present but rated `minimum_viable_for_phase2: no`, Phase-2 must explicitly plan NFR discovery as part of its own Stage-01

- this triggers `BLOCKED` if:
  - no NFR information exists at all (neither 02a scan nor 02b output)
  - Phase-2 would be forced to invent NFR truth from scratch

### PASS with constrained/review-bound conditions when
- some non-critical items remain partial or review-bound
- handoff still exists and remains design/architecture-consumable
- provisional content is explicitly marked and does not force downstream to invent critical truth

### BLOCKED when
- no architecture-entry/design-consumable handoff exists
- critical unresolved truth would force Phase-2 to invent core user/scope/constraint truth
- Class C unresolved items remain unresolved

### Primary references
- `docs/phases/phase-1/unified-product-pack-v0.1.md`
- `docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`
- `reference-packages/phase1-product-requirements/stage-04-requirements-validation/output-template.md`
- `docs/governance/cross-phase-unresolved-truth-handling-v0.1.md`

---

## 5. Phase-2 → Phase-3

### Required downstream handoff type
- implementation-facing handoff package

### Required convergence condition
- Engineering Spec Pack and realizability review must be explicit enough that the design is honestly implementation-consumable

### PASS when
- implementation-facing handoff exists
- Engineering Spec Pack is explicit enough for implementation-entry use
- realizability review says effectively `realizable as designed`
- review-bound items do not replace core engineering decisions

### PASS with constrained/review-bound conditions when
- implementation-facing handoff exists
- realizability review explicitly says the design is only realizable with a constrained/simulated boundary or remains review-bound in bounded ways
- downstream assumptions and forbidden assumptions are explicit

### BLOCKED when
- no implementation-facing handoff exists
- realizability review concludes `blocked for implementation-facing handoff`
- the design only looks coherent but still lacks an honest realizable path

### Primary references
- `docs/phases/phase-2/engineering-spec-pack-v0.1.md`
- `docs/phases/phase-2/phase-2-realizability-architecture-review-rule-v0.1.md`
- `reference-packages/phase2-design-architecture/stage-04-design-convergence-and-delivery-prototype/output-template.md`
- `templates/implementation-readiness-package.md`

---

## 6. Phase-3 → Phase-4

### Required downstream handoff type
- testing-facing implementation handoff / implementation audit handoff

### Required convergence condition
- implementation scope, readiness, and test-relevant boundaries must be explicit enough for testing-validation planning to begin honestly

### PASS when
- implementation-audit/handoff package exists
- implementation scope and test-relevant boundaries are explicit
- no critical blocked item prevents testing-validation planning/execution on the declared target

### PASS with constrained/review-bound conditions when
- implementation is only ready for bounded testing-validation under declared limits
- deferred items remain explicit but do not invalidate first-pass testing work

### BLOCKED when
- there is no usable implementation-entry or implementation-handoff package
- Phase-3 cannot provide enough implementation truth for Phase-4 to plan and evaluate testing honestly
- Phase-4 would have to invent implementation facts rather than validate them

### Primary references
- `templates/implementation-readiness-package.md`
- `archive/examples/implementation-development-package/stage-01-implementation-readiness-and-task-alignment/skill-contract.md` (historical reference)
- `archive/examples/implementation-development-package/stage-03-implementation-audit-and-handoff-gate/output-template.md` (historical reference)
- `docs/governance/cross-phase-unresolved-truth-handling-v0.1.md`

---

## 7. Working rule

When uncertain, use this order:

1. check the phase-specific template and checklist
2. check the convergence pack definition (if applicable)
3. check unresolved-truth classification
4. map the case to this matrix

---

## 8. Current status

This is the first consolidated admission matrix.

It should be treated as:

- the current working reference
- a cross-phase review aid
- a candidate for later formal review/finalization
