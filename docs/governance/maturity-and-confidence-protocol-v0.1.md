# Maturity and Confidence Protocol（v0.1）

## 1. Purpose

This protocol defines how runtimes should express readiness honestly without collapsing delivery maturity and evidence confidence into one vague label.

It exists to prevent two opposite failures:

- false readiness:
  - a document sounds decisive, but downstream still does not know what is safe to start
- false immaturity:
  - a document honestly lacks market proof, but the runtime therefore fails to express that some downstream work can still begin safely

The correct behavior is to score and hand off both axes explicitly.

---

## 2. Two Independent Axes

### Delivery Readiness

This axis asks:

- how mature is the document as a downstream handoff artifact?
- what work can safely start now?

Default states:

- `artifact-draft`
- `review-ready`
- `downstream-start-safe`
- `implementation-commit-ready`
- `blocked`

### Evidence Confidence

This axis asks:

- how strong is the truth basis behind the current conclusion?
- what kind of confidence has actually been earned?

Default states:

- `design-time-inference-heavy`
- `source-grounded-but-unvalidated`
- `partially-signal-backed`
- `externally-validated`
- `contradicted`

These axes are related but not interchangeable.

---

## 3. Core Semantics

- A document may be `downstream-start-safe` while still only `source-grounded-but-unvalidated`.
- Low evidence confidence does not automatically forbid design or architecture start.
- High delivery readiness does not imply market truth has been validated.
- `review-bound` is primarily an evidence / downstream-constraint signal, not a delivery-readiness state by itself.

If a runtime outputs only one maturity label, it is flattening meaning it still needs.

---

## 4. Required Questions

For each high-impact subject, ask:

- what is the current delivery-readiness state?
- what is the current evidence-confidence state?
- what specific basis supports each state?
- what blocks the next delivery-readiness state?
- what blocks the next evidence-confidence state?
- what downstream action is safe now?
- what downstream assumptions are forbidden?

If these questions are not answered, maturity language is decorative rather than operational.

---

## 5. Minimum Ledger

At minimum, the runtime should preserve a maturity / confidence ledger with:

- `subject`
- `delivery_readiness_state`
- `evidence_confidence_state`
- `current_basis`
- `blocker_to_next_delivery_state`
- `blocker_to_next_evidence_state`
- `safe_downstream_action`
- `forbidden_assumptions`

This ledger may appear as a table or structured bullets, but it must be downstream-consumable.

---

## 6. Final PRD / Handoff Rule

Stage-04 and the final converged PRD should explicitly declare:

- `document_delivery_state`
- `evidence_confidence_state`
- `safe_start_scope`
- `blocked_commitments`
- `warning / pending external confirmation` summary and ledger

The final PRD must not force downstream consumers to infer these from scattered prose.

---

## 6.5 Warning Ledger Rule

When a PRD is mature enough to pass under current inputs but still lacks external proof, the runtime should not hide that gap inside generic risk prose.

It should emit a dedicated warning/pending-confirmation ledger that makes explicit:

- what subject is still warning-bearing
- why it is still warning-bearing
- what external confirmation is still missing
- what current document use is safe
- what stronger commitment is still blocked

This is how the runtime keeps two truths visible at once:

- the document itself may already be mature
- the business/evidence completeness may still be partial

---

## 7. Decision Rule

When making a final admission judgment:

- use delivery readiness to decide what downstream work may start
- use evidence confidence to decide what claims, promises, or commitments remain unsafe

This means:

- design / architecture may start under constrained conditions
- implementation commitments, pricing commitments, or rollout claims may still be blocked

Both truths must be stated together.

---

## 8. Anti-Patterns

Do not:

- use weak evidence as an excuse to avoid defining safe downstream start scope
- use `ready-to-converge` or `can start design` as proof that the market truth is validated
- hide blocked commitments inside generic risk prose
- treat `AI-INFERRED` as the only maturity signal the document needs
- collapse delivery readiness and evidence confidence into a single overall adjective
