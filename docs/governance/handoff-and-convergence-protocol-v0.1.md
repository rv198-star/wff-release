# Handoff and Convergence Protocol（v0.1）

## 1. Purpose

This protocol defines the minimum reasoning standard for downstream handoff and final convergence.

Its purpose is to prevent a common failure:

- the analysis may be decent
- but the downstream consumer still does not know what is safe to start, what remains unresolved, or what must not be assumed

Status labels alone are not enough.

---

## 2. Required Handoff Packet

Any downstream-consumable handoff should make these items explicit:

- `consumer`
  - who the handoff is for
- `safe_start_scope`
  - what work may begin now
- `unresolved_truths`
  - what remains open
- `forbidden_assumptions`
  - what downstream must not silently promote
- `warning_or_pending_confirmation_ledger`
  - what may remain warning-bearing even though the document itself is mature enough to pass
- `next_validation_or_remediation`
  - what should happen before deeper commitment
- `artifact_references`
  - what source artifacts carry the supporting reasoning

If the downstream consumer still has to infer these, the handoff is incomplete.

---

## 3. Convergence Rule

When multiple artifacts converge into one final deliverable:

- preserve deep reasoning that downstream needs
- externalize runtime-only residue that is useful for audit but noisy for handoff
- do not compress away decision rationale, trade-offs, or uncertainty state

The converged artifact should be:

- easier to consume than the assembled draft
- not materially shallower in judgment

---

## 4. Safe-Start Rule

Every handoff should answer:

- what can design start without inventing product truth?
- what can architecture start without inventing business truth?
- what must wait for more validation?
- which parts are document-complete but still business-incomplete?

If this is missing, the handoff is not yet operational.

---

## 5. Anti-Patterns

Do not:

- hand off only a verdict label
- state that downstream can start without defining the safe scope
- hide uncertainty inside generic risk sections
- use convergence to compress away the reasoning that made the artifact trustworthy
