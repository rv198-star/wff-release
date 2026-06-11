# Cross-Phase Unresolved Truth Handling（v0.1）

## 1. Why this document exists

The first Phase-1 → Phase-4 end-to-end trial did **not** reveal a broken package chain.

It revealed a more subtle and more important risk:

> unresolved upstream truth can be carried downstream cleanly in shape, but accumulate in weight until later phases are forced to absorb too much uncertainty.

This document defines the first project-level rule set for deciding:

- which unresolved truths may continue downstream
- which unresolved truths must become blocked / remediation items before the next phase
- how that distinction should be expressed

---

## 2. Core principle

Not all unresolved truth is equally dangerous.

The goal is **not** “resolve everything early.”
The goal is:

> **allow harmless uncertainty to flow, but stop uncertainty that amplifies downstream truth cost.**

In other words:

- acceptable ambiguity may continue as review-bound carryover
- amplifying ambiguity must be escalated into blocked/remediation or explicit non-pass state

---

## 3. Three classes of unresolved truth

### Class A — Acceptable Carryover

Definition:

- unresolved, but does not distort the next phase’s main job
- does not force downstream to invent critical structure
- can remain explicit as assumption / provisional / review-bound note

Examples:

- low-priority secondary user segmentation details
- later-slice prioritization nuances
- optional UX polish choices
- optional analytics/reporting details not in first slice

Default handling:

- may pass downstream as explicit review-bound truth

---

### Class B — Downstream-Risk-Amplifying Carryover

Definition:

- unresolved, but still allows the next phase to proceed in a bounded way
- however, if carried too long, it becomes a strong downstream burden
- should be allowed only with explicit visibility and caution

Examples:

- partial privacy / retention expectations
- partial external integration realism
- unresolved operator-control vs automation boundary
- partial NFR expectations that affect architecture or testing posture but do not fully block first-pass structuring

Default handling:

- may pass downstream only as **review-bound carryover**
- must be surfaced in output decision sections, not hidden in side notes
- later phases should not silently compress this class into confirmed truth

---

### Class C — Must-Resolve-Before-Next-Phase

Definition:

- unresolved, and its absence prevents the next phase from doing its main job honestly
- downstream would have to invent critical truth or fake gate completion

Examples:

- no defensible target-user boundary before structured requirement shaping
- no architecture-entry handoff before Phase-2 Stage-01
- no implementation-entry handoff before Phase-3 Stage-01
- no Stage-01 may-start basis before Phase-3 or Phase-4 execution stages
- no evidence basis for closure while trying to give a pass judgment

Default handling:

- do **not** pass as ordinary downstream input
- convert to blocked/remediation or explicit non-pass output

---

## 4. Decision rule

For any unresolved item, ask:

### Question 1
Can the next phase still do its real job without inventing critical truth?

- If **no** → Class C
- If **yes** → continue

### Question 2
Will this unresolved item materially increase downstream interpretation burden or distort test/architecture/implementation decisions if left unresolved too long?

- If **yes** → Class B
- If **no** → Class A

---

## 5. Expression rules by class

### Class A expression
- may appear in:
  - assumptions
  - open questions
  - review-bound notes

### Class B expression
- must appear in:
  - assumptions / unresolved items
  - decision summary
  - downstream usage rule or handoff boundary
  - stage status if material enough

### Class C expression
- must appear in:
  - blocked/remediation section
  - may-start / may-pass / closure decision section
  - explicit refusal or non-pass judgment when applicable

---

## 6. First project-level application from the restaurant-owner trial

### Example 1 — privacy / retention policy clarity
- classification:
  - Class B
- why:
  - early phases can still structure product and architecture work
  - but by Phase-4 it becomes a major testing-planning burden

### Example 2 — external integration realism
- classification:
  - Class B
- why:
  - architecture and implementation can proceed in bounded review-bound form
  - but execution/testing realism degrades if this stays weak too long

### Example 3 — assistive-only vs more autonomous behavior boundary
- classification:
  - Class B
- why:
  - product/architecture can still progress provisionally
  - but validation and closure judgment become much weaker if this is never clarified

### Example 4 — no real implementation handoff
- classification:
  - Class C
- why:
  - Phase-3 cannot honestly perform readiness work without a real implementation-entry basis

---

## 7. Immediate convergence implication

The next round of cross-phase convergence should not focus only on file symmetry.

It should focus on whether phase outputs clearly mark:

- acceptable carryover
- downstream-risk-amplifying carryover
- must-resolve-before-next-phase blockers

This is likely a higher-value patching direction than broader prose alignment.

---

## 8. Current status

This is a first project-level rule set.

It should be treated as:

- a convergence artifact
- a future checklist input
- a review lens for later selective patching

It is **not yet**:

- a fully integrated output-template rule across all phases
- a registry-enforced truth-state system
- a live orchestrator policy
