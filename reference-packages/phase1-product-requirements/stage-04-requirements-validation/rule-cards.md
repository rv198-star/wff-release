# Stage-04 Rule Cards — requirements-validation-and-concept-proof

## Usage

This file records atomic Stage-04 rules before prose drafting.

---

## RC-01
- statement: Stage-04 validates key assumptions, key decisions, and key requirement/MVP choices, then feeds the result back into earlier stages.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-04-requirements-validation/skill-contract.md`
- source_tier: Tier 4
- confidence: medium-high
- applies_to_stage: Stage-04

## RC-02
- statement: Stage-04 requires explicit validation targets (assumptions / risks / key decision points).
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-03
- statement: If there is no explicit validation target, Stage-04 must refuse or not start.
- type: prohibition
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-04
- statement: Stage-04 must output a validation conclusion that is explainable through evidence.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-05
- statement: Stage-04 must output a validation record describing method, sample/feedback, and key findings.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-06
- statement: Stage-04 must output revision recommendations that can feed back into Stage-02/03.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-07
- statement: Stage-04 conclusion must resolve into Go / No-Go / Revise (or equivalent explicit decision state).
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-08
- statement: If validation uses a prototype, it should stay as low-cost as possible.
- type: heuristic
- source: `reference-packages/phase1-product-requirements/stage-04-requirements-validation/stage-sop.md`
- source_tier: Tier 4
- confidence: medium-high
- applies_to_stage: Stage-04

## RC-09
- statement: A `validation-flow` is recommended and should represent hypothesis → method → threshold/signal → result → decision.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-10
- statement: Stage-04 must not pretend validation is complete if the output is still based on review-bound upstream assumptions.
- type: prohibition
- source: `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-11
- statement: `user-story-mapping` is the primary source for validation-learning loop logic in this phase.
- type: requirement
- source: `docs/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-12
- statement: `inspired` is the primary source for product validation / prototype-testing mindset in Stage-04.
- type: requirement
- source: `docs/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-13
- statement: `lean-product-development` should constrain Stage-04 toward learning and revision, not heavy upfront certainty.
- type: boundary
- source: `docs/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04

## RC-14
- statement: Stage-04 should validate the key assumptions carried from Stage-03 MVP slicing rather than inventing a new validation target disconnected from the slice logic.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-03-requirements-decomposition/self-test-dry-run-output.md`
- source_tier: Tier 4
- confidence: high
- applies_to_stage: Stage-04

## RC-15
- statement: Stage-04 should hand off to design/architecture with validation outcome, prototype/equivalent evidence, and revision recommendations.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-04
