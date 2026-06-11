# Refactoring (2nd Edition) — Index Map

## Scope

- Source file:
  - `sources/books/original/phase-others/refactoring-improving-the-design-of-existing-code.md`
- Extraction depth:
  - `index-map -> knowledge-card-draft -> stage-guidance-draft`
- Book type judgment:
  - `method-heavy`
  - `system / engineering-governance support`
- Primary Stage focus:
  - `development`
  - `testing`
  - `maintenance / refactoring`
- Current downstream target:
  - Future standalone stage: `refactoring-preparation` (bounded, test-backed change)
  - Legacy-change workstream support (Branch by Abstraction, preparatory refactoring)

## Extraction boundary (pass-1)

This is a bounded first pass.

- Extracted in pass-1:
  - Chapter 1 (refactoring workflow via worked example): focus on **tests-first safety net**, **split phases**, **small steps**, **keep system working**
  - Chapter 2 (principles): focus on **definitions**, **two hats**, **when/why refactor**, **refactor vs performance**, **large refactor strategies (Branch by Abstraction)**
- Deferred (index-only in pass-1):
  - Chapter 3 smells (catalog exists; deeper per-smell cards can be added later)
  - Chapter 4 testing chapter (can be extracted later as a deeper safety-net/testing bundle)
  - Refactoring catalog chapters (useful, but too large for first pass)

## Extraction boundary (pass-2)

With full source available, pass-2 adds two preparation-level layers:

- Chapter 4 (testing) — add the minimum reusable safety-net spine (not framework-specific)
- Chapter 3 (smells) — add a smell-to-action trigger sheet for selecting bounded entry points

## Section map (organized by use)

| Section (by use) | Core problem solved | Stage | Type | Priority |
|---|---|---|---|---:|
| What refactoring is (and isn’t) | Defines refactoring as behavior-preserving structural change; distinguishes from restructuring & performance work | development | concept / boundary | very high |
| Two hats (change vs refactor) | Prevents mixing feature work and refactoring work; clarifies how to measure progress | development | method / boundary | very high |
| Tests-first safety net | Makes refactoring safe; enforces self-testing tests and fast feedback | testing | checklist / method | very high |
| Small steps, always working | “Keep the system working” and reduce debugging via micro-steps | development | method / discipline | very high |
| Make change easy, then make the easy change | Preparatory refactoring as navigation, not detour | development | method / heuristic | very high |
| Opportunistic cleanup (camping rule) | Prevents “perfect cleanup” scope creep; encourages incremental hygiene | development | method / boundary | high |
| Long refactoring strategies | Provides patterns like Branch by Abstraction for multi-week refactors | development | method / risk | high |
| Smell-driven targeting (catalog) | Provides a refactoring target selection heuristic (smells) without prescribing automatic rules | maintenance | concept / warning | medium |

## Coverage ledger

- `source-unit-coverage-ledger-v0.1.md`

## Planned card clusters (pass-1)

- define-refactoring-by-behavior-preservation-and-change-cost
- two-hats-separate-feature-work-from-refactoring-work
- refactor-requires-self-testing-tests-and-fast-feedback-loop
- keep-system-working-via-small-steps-avoid-debugging-by-design
- make-change-easy-then-make-easy-change-preparatory-refactoring
- opportunistic-cleanup-camping-rule-leave-code-better-than-found
- three-strikes-rule-refactor-on-third-duplication
- branch-by-abstraction-for-long-running-refactors
- refactor-vs-performance-optimization-different-goals-and-tradeoffs

## Planned card clusters (pass-2)

- self-testing-tests-are-a-refactoring-safety-net-not-ceremony
- test-first-helps-define-done-and-focus-on-interfaces
- smell-to-action-trigger-sheet-for-refactoring-preparation

## Planned card clusters (pass-3)

Add the most common refactoring building blocks (Chapter 6) as reusable method cards:

- extract-function-separates-intent-from-implementation
- inline-function-removes-accidental-indirection
- extract-variable-makes_intermediate_intent_visible
- inline-variable-removes_noise_when_name_adds_no_information

## Skip / low-value (for this repo)

- Publishing metadata, translator/editor bios, marketing/praise pages
- Tool-specific IDE/automation details that do not generalize across stacks
- Exhaustive refactoring catalog extraction in pass-1 (too large; extract on demand)
