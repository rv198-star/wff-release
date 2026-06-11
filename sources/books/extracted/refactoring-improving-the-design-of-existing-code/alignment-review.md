# Refactoring (2nd Edition) — Alignment Review

## Original-source alignment

This book’s core problem is not “code cleanup tips”, but a **disciplined approach to changing code safely**:

- refactoring is behavior-preserving structural change
- safety comes from **self-testing tests** and **small steps**
- development alternates between two distinct modes (feature vs refactor)
- large refactors require bounded strategies rather than big-bang rewrites

This extraction preserves that by focusing on decision rules, boundaries, and workflow discipline rather than mirroring the book chapter order or catalog completeness.

## Project alignment

In this repository, the source is useful as:

- a future standalone stage pack for `refactoring-preparation` (tests-first, small steps, always working)
- a contract/gate backbone for refactoring intent separation and change safety
- a refactoring/legacy-change workstream reference (Branch by Abstraction, preparatory refactoring)

## Judgment

Stage-complete judgment (pass-1): **partially yes (bounded discipline pack for refactoring-preparation)**.

- Index map exists with explicit pass boundary.
- Core card set exists for refactoring definitions, two-hats discipline, tests-first safety net, small steps, preparatory refactoring, and long-refactor strategy.
- Stage guidance exists and maps to `refactoring-preparation`.

Deferred:

- smell catalog deep extraction
- testing chapter deep extraction
- refactoring catalog deep extraction
