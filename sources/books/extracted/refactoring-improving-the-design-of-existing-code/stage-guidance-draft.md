# Refactoring (2nd Edition) — Stage Guidance Draft

## Goal

Turn *Refactoring (2nd Edition)* into a reusable **change-safety and design-improvement discipline pack** for this repository.

This bundle is not trying to teach every catalog refactoring. It is primarily used to:

- keep change safe via tests-first and small steps
- prevent “feature + refactor” mixing
- guide when to refactor (and when not to)
- support longer refactors with bounded strategies

## Boundary

- This bundle does **not** replace language/framework-specific refactoring tooling.
- This bundle does **not** aim to cover every smell or refactoring catalog entry in pass-1.
- This bundle **does** provide reusable decision rules and checklists that can be absorbed into the future `refactoring-preparation` stage contracts and gates.

## Best-fit mapping in this repository

This bundle is primarily intended for a future standalone stage:

- `refactoring-preparation`

It provides reusable decision rules and safety disciplines for bounded, test-backed structural change.

### Refactoring Preparation — Stage outcomes to support

Treat these as the core outcomes this bundle should enable:

1. **Refactoring intent is explicit and bounded**
   - behavior-preservation boundary is stated
   - what is *not* being changed is stated

2. **Safety net exists before structural change**
   - self-testing tests or equivalent fast feedback loop is available

3. **Execution discipline prevents drift**
   - two-hats separation is practiced
   - small steps keep the system working

4. **Large refactors have a migration strategy**
   - Branch by Abstraction (or equivalent) is used instead of big-bang rewrite

### Recommended card set (first absorption)

- `define-refactoring-by-behavior-preservation-and-change-cost.md`
- `two-hats-separate-feature-work-from-refactoring-work.md`
- `refactor-requires-self-testing-tests-and-fast-feedback-loop.md`
- `keep-system-working-via-small-steps-avoid-debugging-by-design.md`
- `make-change-easy-then-make-easy-change-preparatory-refactoring.md`
- `opportunistic-cleanup-camping-rule-leave-code-better-than-found.md`
- `three-strikes-rule-refactor-on-third-duplication.md`
- `branch-by-abstraction-for-long-running-refactors.md`
- `refactor-vs-performance-optimization-different-goals-and-tradeoffs.md`

### Pass-2 extension (now that full source exists)

Add a preparation-level layer that improves the practicality of the stage:

- Testing safety-net spine (Chapter 4)
  - `self-testing-tests-are-a-refactoring-safety-net-not-ceremony.md`
  - `test-first-helps-define-done-and-focus-on-interfaces.md`
- Smell-to-action trigger sheet (Chapter 3 + 5.2)
  - `smell-to-action-trigger-sheet-for-refactoring-preparation.md`

### Pass-3 extension (high-frequency refactor primitives)

Add a small set of high-frequency refactor primitives (Chapter 6) as method cards:

- `extract-function-separates-intent-from-implementation.md`
- `inline-function-removes-accidental-indirection.md`
- `extract-variable-makes_intermediate_intent_visible.md`
- `inline-variable-removes_noise_when_name_adds_no_information.md`

## Future expansion (pass-2 candidates)

- A smell-to-action index that maps smells to minimal refactoring candidates
- A separate safety-net/testing bundle extracted from Chapter 4
- On-demand extraction of catalog entries used most frequently by refactoring-preparation work
