# Stage-03 Rule Cards — requirements-decomposition-and-mvp-slicing

## Usage

This file records atomic Stage-03 rules before prose drafting.

---

## RC-01
- statement: Stage-03 converts a structured requirements panorama into an explainable MVP boundary and delivery slices.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/skill-contract.md`
- source_tier: Tier 4
- confidence: medium-high
- applies_to_stage: Stage-03

## RC-02
- statement: Stage-03 requires a Stage-02 panorama / story-map / equivalent whole structure as input.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-03
- statement: If no whole-picture structure exists upstream, Stage-03 must refuse or return.
- type: prohibition
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-04
- statement: Stage-03 must output an MVP definition.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-05
- statement: Stage-03 must output a release slicing explanation covering first / later / deferred items.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-06
- statement: Stage-03 must form a minimum viable experience loop, not just a reduced scope list.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-07
- statement: Slice logic must be explainable in terms of value, risk, and dependency.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-08
- statement: Deferred items must be explicit; if there are none, the output must explain why.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-09
- statement: Stage-03 has a required `slice-map` structure evidence gate.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-10
- statement: A valid Stage-03 slice-map must have at least 2 slices, and each slice must include capability boundary, acceptance target, and key dependency.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-11
- statement: If the output is only “phase 1 do A/B/C” without slice boundaries and acceptance targets, Stage-03 fails.
- type: prohibition
- source: `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-12
- statement: Stage-03 may still carry provisional uncertainty, but unresolved assumptions must remain explicit and review-bound.
- type: requirement
- source: `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-13
- statement: `user-story-mapping` is the primary slicing and whole-experience-loop source for Stage-03.
- type: requirement
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-14
- statement: `effective-requirements-analysis` supports decomposition discipline and structured requirement breakup.
- type: heuristic
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-15
- statement: `lean-product-development` should constrain Stage-03 toward early value and anti-overbuild discipline, but not replace slicing logic itself.
- type: boundary
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-03

## RC-16
- statement: Stage-03 should preserve Stage-02’s high-risk validation point and carry it forward into the MVP slicing logic.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-02-requirements-analysis/self-test-dry-run-output.md`
- source_tier: Tier 4
- confidence: high
- applies_to_stage: Stage-03

## RC-17
- statement: Stage-03 should not pretend validation has already happened; it only prepares a testable slice and assumption set.
- type: boundary
- source: `reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/skill-contract.md`
- source_tier: Tier 4
- confidence: medium-high
- applies_to_stage: Stage-03
