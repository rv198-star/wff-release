# Stage-02 Rule Cards — requirements-analysis

## Usage

This file records atomic Stage-02 rules before prose drafting.

---

## RC-01
- statement: Stage-02 converts research conclusions into a structured requirements view rather than directly slicing implementation.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-02-requirements-analysis/skill-contract.md`
- source_tier: Tier 4
- confidence: medium-high
- applies_to_stage: Stage-02

## RC-02
- statement: Stage-02 requires Stage-01 structured conclusions, including user groups and key problems.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-03
- statement: If basic research conclusions are missing, Stage-02 must refuse or return to Stage-01.
- type: prohibition
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-04
- statement: Stage-02 must produce a requirements panorama / story map or an equivalent structured view.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-05
- statement: Stage-02 must produce a key constraints list.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-06
- statement: Stage-02 must produce an initial priority split including at least high-value first, high-risk-to-validate, and deferrable items.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-07
- statement: Stage-02 exit requires a whole structure that can walk from goal to activity to task to constraint.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-08
- statement: Having only story items without a whole-picture structure is a direct fail signal.
- type: prohibition
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-09
- statement: Stage-02 has a required diagram evidence gate.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-10
- statement: Stage-02 must contain either a `story-map` or a `requirements-structure` artifact.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-11
- statement: A valid Stage-02 `story-map` must have at least 3 backbone activities, at least 2 tasks under each activity, one marked main flow, one boundary/exclusion, and one high-risk validation point.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-12
- statement: If no Stage-02 structure evidence exists, return to Stage-02 step-1 or even Stage-01 if user/problem structure is still weak.
- type: refusal
- source: `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-13
- statement: Stage-02 must preserve Stage-01 provisional uncertainty instead of silently upgrading it to confirmed fact.
- type: requirement
- source: `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-14
- statement: Stage-02 may consume provisional Stage-01 input only as review-bound input, not as confirmed fact.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-01-user-research/self-test-verification-report.md`
- source_tier: Tier 4
- confidence: high
- applies_to_stage: Stage-02

## RC-15
- statement: `effective-requirements-analysis` is the primary template/analysis source for Stage-02.
- type: requirement
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-16
- statement: `user-story-mapping` is the primary panorama/story-structure source for Stage-02.
- type: requirement
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-17
- statement: `product-demand-fit` protects upstream problem/evidence quality and should prevent shallow structural analysis disconnected from evidence.
- type: heuristic
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-18
- statement: `lean-product-development` should constrain Stage-02 with value/adaptation principles, but should not become the detailed structural template itself.
- type: boundary
- source: `docs/internal/source-registers/product-requirements-source-index.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02

## RC-19
- statement: Stage-02 should distinguish goals, activities, tasks, and constraints rather than mixing them into one flat list.
- type: requirement
- source: `reference-packages/phase1-product-requirements/stage-02-requirements-analysis/skill-contract.md`
- source_tier: Tier 4
- confidence: medium-high
- applies_to_stage: Stage-02

## RC-20
- statement: Stage-02 should identify at least one high-risk point that later validation work must examine.
- type: requirement
- source: `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- source_tier: Tier 1
- confidence: high
- applies_to_stage: Stage-02
