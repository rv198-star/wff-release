# PhaseX Source Library Seed (v0.1)

## Purpose

This document defines the minimum method backbone for **PhaseX Wave-1**.

PhaseX should not stop at repository summarization. Its `technical-refactor` lane must absorb explicit refactoring discipline from the repository's existing extracted-source library.

## Primary Backbone

### Refactoring (2nd Edition)

Primary entry files:

- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/index-map.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/stage-guidance-draft.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/alignment-review.md`

Current Wave-1 cards to absorb:

- `cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`
- `cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`
- `cards-draft/refactor-requires-self-testing-tests-and-fast-feedback-loop.md`
- `cards-draft/keep-system-working-via-small-steps-avoid-debugging-by-design.md`
- `cards-draft/make-change-easy-then-make-easy-change-preparatory-refactoring.md`
- `cards-draft/branch-by-abstraction-for-long-running-refactors.md`
- `cards-draft/smell-to-action-trigger-sheet-for-refactoring-preparation.md`

## Secondary Support

### Refactoring Databases: Evolutionary Database Design

Use as the database-evolution support for brownfield schema change, data migration, and shared-database refactor:

- `sources/books/extracted/refactoring-databases-evolutionary-database-design/index-map.md`
- `sources/books/extracted/refactoring-databases-evolutionary-database-design/stage-guidance-draft.md`
- `sources/books/extracted/refactoring-databases-evolutionary-database-design/alignment-review.md`

Use it mainly for:

- schema evolution with behavior/information preservation
- transition period and scaffolding for multi-application schema change
- database regression tests before and during refactor
- schema version tracking and refactoring bundle discipline
- deployment / retest / backup / backout discipline

Boundary:

- do not upgrade this source into a general PhaseX backbone for every case
- activate it when the case includes database-first truth, schema migration, shared-database coupling, or rollback-sensitive data change

### The Art of Unit Testing

Use as the safety-net supplement for brownfield change:

- `sources/books/extracted/the-art-of-unit-testing/index-map.md`
- `sources/books/extracted/the-art-of-unit-testing/stage-guidance-draft.md`

Use it mainly for:

- legacy-code pre-refactor safety net
- testability seams
- trustworthy / maintainable / readable tests
- fast, self-checking feedback

## Wave-1 Mapping

### PX-SK-01 codebase-baseline-extraction

Absorb lightly:

- smell hints only as observation aids
- do not jump from smell to redesign claim without evidence

### PX-SK-02 database-baseline-extraction

Must absorb when database scope is in play:

- schema as an evolvable asset, not a frozen snapshot
- indexes / constraints / sensitive fields as first-class baseline facts
- transition-period risk when multiple applications share the same schema
- schema-version and rollout-readiness evidence

### PX-SK-04 technical-health-assessment

Must absorb:

- behavior-preservation boundary
- two-hats risk
- smell-to-action trigger thinking
- whether the change is true refactor, feature change, or mixed change

### PX-SK-07 safety-net-test-construction

Must absorb:

- self-testing tests before refactor
- fast feedback loop
- small steps while keeping the system working
- Branch by Abstraction when the replacement cannot be completed safely in one bounded pass

### PX-SK-06 partial gap-analysis-and-change-decomposition

Must absorb:

- clear excluded-scope line
- behavior-preservation boundary for unchanged surfaces
- separation between product change and structural change

### PX-SK-08 refactoring-strategy-definition

Must absorb when refactor touches persistence:

- database refactoring must preserve both behavioral and informational semantics
- prepare deprecate migrate test version announce as the minimum DB refactor lifecycle
- avoid big-bang schema replacement when scaffolding or transition period is required

### PX-SK-09 migration-strategy-and-cutover-plan

Must absorb when the change includes data migration or schema cutover:

- database regression tests as rollout gate input
- backup / retest / backout discipline before production cutover
- schema version tracking and explicit rollback trigger conditions
- multi-application compatibility window during migration

## Anti-Patterns To Prevent

- calling any cleanup “refactoring” without stating the behavior-preservation boundary
- mixing feature work and refactor work into one un-auditable blob
- planning structural change before a safety net exists
- turning large replacement into big-bang rewrite when bounded abstraction is needed
- treating a generic debt list as a usable refactor plan

## One-Line Summary

PhaseX Wave-1 should use the repository's refactoring extraction as a real method backbone, and activate the evolutionary-database-design bundle whenever the brownfield case includes database refactor or migration risk.
