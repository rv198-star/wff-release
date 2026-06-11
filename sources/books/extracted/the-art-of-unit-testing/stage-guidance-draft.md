# The Art of Unit Testing — Stage Guidance Draft

## Primary target stage

- `development`

## Best-fit use in this repository

This source is best treated as a **Phase-3 implementation support bundle** rather than a pure testing-stage source.

Its strongest reusable value is:

- defining minimum unit-test quality standards
- turning testability into design/coding constraints
- clarifying when mocks/stubs help vs hurt
- organizing test assets so they remain maintainable
- introducing legacy-code test strategies before heavy refactoring

## Recommended absorption directions

### 1. Phase-3 Stage-01 — Coding Baseline Contract

Absorb into rules such as:

- prefer interface/seam extraction for hard dependencies
- avoid logic-heavy constructors/static calls in core logic paths
- define minimum unit-test quality expectations beyond coverage percentage

#### First absorption shortlist (Stage-01)

Recommended cards to absorb first:

1. `ficc-fast-isolated-configuration-free-consistent-is-the-minimum-testability-bar`
2. `extract-interfaces-and-inject-dependencies-to-enable-unit-tests`
3. `design-for-testability-by-avoiding-hard-wired-dependencies`
4. `test-public-contracts-not-private-methods`

Why this set first:

- it defines the minimum meaning of testability
- it turns testability into coding-baseline rules rather than vague preference
- it avoids locking Phase-3 to a single language or framework

### 2. Phase-3 Stage-02 — Implementation / minimal automation

Absorb into expectations such as:

- unit tests are part of implementation evidence, not afterthoughts
- interaction testing should avoid overspecification
- test organization should map clearly to code under test

### 3. Phase-3 Stage-03 — Implementation Audit & Handoff Gate

Absorb into audit checks such as:

- tests are trustworthy / maintainable / readable
- more than one mock per test is treated as a warning sign
- testability waivers are explicit when hard-wired dependencies remain

#### First absorption shortlist (Stage-03)

Recommended cards to absorb first:

1. `good-unit-tests-have-trustworthy-maintainable-readable-pillars`
2. `no-logic-in-unit-tests-reduces-hidden-test-bugs`
3. `one-test-should-cover-one-concern`
4. `tests-must-be-isolated-from-order-and-shared-state`
5. `coverage-metrics-need-code-review-and-kill-checks-to-be-meaningful`
6. `setup-methods-should-not-hide-test-specific-context`
7. `test-names-should-encode-method-scenario-behavior`

Why this set first:

- it gives Stage-03 a real test-audit spine instead of generic "review the tests"
- it maps directly to trustworthy / maintainable / readable criteria
- it is audit-friendly and does not require locking into one framework's style

### 4. Future Refactoring / Reuse Convergence Phase

This source is also valuable for a future standalone refactoring phase because Chapter 10 and Chapter 11 give a practical path for:

- adding safety nets to legacy code
- refactoring toward testable seams
- avoiding uncontrolled big-bang rewrites

#### Keep as sidecar / later absorption

The following cards are valuable but should not be forced into the first-pass Phase-3 mainline:

- `legacy-code-needs-a-test-feasibility-table-before-test-introduction`
- `use-integration-tests-as-a-safety-net-before-refactoring-legacy-code`
- `map-tests-by-speed-type-and-code-under-test`

They are better treated as:

- legacy-workstream support
- future refactoring phase inputs
- or second-pass expansion after the mainline Phase-3 package stabilizes
