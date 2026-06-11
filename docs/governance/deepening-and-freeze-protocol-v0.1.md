# Deepening and Freeze Protocol（v0.1）

## 1. Purpose

This protocol defines when a runtime may deepen an artifact further and when it must freeze.

It is the state-resolution companion to:

- `runtime-deps/mindthus/source/skills/3l5s/resources/three-layer-recursive-loop.md`

It exists to avoid both:

- premature freezing
- endless refinement

The default principle is:

> deepen only when the next round will materially improve a specific artifact unit

---

## 2. Valid Reasons to Deepen

A new round is justified only when at least one of these is true:

- the current artifact unit is still generic
- a meaningful alternative was not actually compared
- the `why-this-not-that` rationale is weak
- uncertainty is still hidden or weakly classified
- the downstream handoff would force the next phase to reinvent the logic
- the prior round exposed a high-value contradiction or tension worth resolving

If none of these are true, freeze.

---

## 3. Round Types

The common round types are:

- `clarification round`
  - narrow missing context
- `comparison round`
  - compare alternatives and trade-offs
- `stress-test round`
  - pressure-test the current conclusion
- `integration round`
  - integrate prior reasoning gains into a stable artifact

Later rounds should become more integrative, not more exploratory.

---

## 4. Freeze States

An artifact may end in:

- `freeze`
  - good enough to hand off
- `freeze-with-review-bound-warning`
  - usable, but only with explicit uncertainty carryover
- `return-remediate`
  - must go back for targeted strengthening
- `blocked`
  - cannot proceed honestly

These states should be explicit in runtime traces and handoff notes.

---

## 5. Minimum Per-Round Trace

Each material round should record:

- target artifact unit
- trigger for the round
- what was refined
- what alternatives or tensions were considered
- what improved downstream usability
- why another round is or is not justified

If a round leaves no material trace, it should be treated as style-polish, not deepening.

---

## 6. Anti-Patterns

Do not:

- loop because the artifact feels vaguely weak
- use round 3 to reopen the whole problem space
- treat longer text as proof of deeper reasoning
- freeze without explaining why the remaining weakness is acceptable
