# Document Lifecycle Policy（v0.1）

## 1. Purpose

Not all documents in this repository should be treated with the same review burden.

This policy defines which documents require a visible:

> **draft → review → revise → finalized**

process, and which documents may remain lighter-weight working materials.

---

## 2. Core principle

The stricter the document’s downstream impact, the stricter its review lifecycle should be.

In practice:

- if a document changes gates, handoffs, implementation assumptions, or downstream trust
  - it should go through a visible review/revise/finalization process
- if a document is only a temporary working note or intermediate exploration artifact
  - it may remain draft-level or lightweight

---

## 3. Documents that should require full lifecycle

These should normally pass through:

- draft
- review
- revise
- finalized (or equivalent stable state)

### A. Gate / admission / refusal rules

Examples:

- phase admission rules
- realizability review rules
- blocked/review-bound handling rules
- boundary rules that affect repo behavior

Why:

- these documents change how the whole system decides whether downstream work may start

### B. Convergence packs and engineering-facing delivery objects

Examples:

- Unified Product Pack definitions
- Engineering Spec Pack definitions
- implementation-facing handoff specs
- project-grade pack definitions

Why:

- these documents shape what downstream teams or later phases rely on as “real package outputs”

### C. Official output templates and canonical pack templates

Examples:

- phase stage output templates
- canonical templates under `templates/`
- pack output templates that downstream execution depends on

Why:

- these define what “correct output” means for the system

### D. Family-level checkpoints and explicit system judgments

Examples:

- first-pass family checkpoints
- audit/self-test checkpoints
- real happy-path run checkpoints

Why:

- these documents carry repo-level truth claims and should not stay as casual drafts forever

### E. Process-policy / terminology / boundary docs

Examples:

- skills-vs-business-project boundary docs
- process-justice priority docs
- project vocabulary / concept model docs

Why:

- these documents affect how people interpret the entire repository

---

## 4. Documents that may remain lighter-weight

These do not necessarily require the full lifecycle unless they become canonical references later.

### A. Working notes / internal planning files

Examples:

- `task_plan.md`
- `findings.md`
- `progress.md`
- scratch planning notes
- dated documents under `docs/plans/` unless explicitly promoted into canonical docs

### B. Trial outputs / experiment artifacts

Examples:

- disposable test-package outputs
- temporary external-workspace manifests
- one-off run notes

### C. Intermediate bridge experiments

Examples:

- first exploration outputs used only to test a hypothesis
- temporary iteration artifacts before they are promoted into canonical packs/templates

---

## 5. Practical status model

### Recommended statuses for high-impact docs
- `draft`
- `review`
- `revision-n`
- `approved`
- `superseded` (when replaced by a stronger document)

### Minimal requirement

For high-impact docs, the repo should be able to answer:

1. is this still a draft?
2. has it been reviewed?
3. what changed in the latest revision?
4. is it currently the stable reference, or already superseded?

---

## 6. Immediate working rule

### Must go through full lifecycle
- rules
- gates
- official templates
- convergence packs
- checkpoints
- vocabulary/boundary docs

### May stay lightweight until promoted
- notes
- experiments
- temporary trial outputs
- local run records
- historical planning snapshots in `docs/plans/`

---

## 7. Final one-line rule

> **If a document can change downstream trust or behavior, it should not remain only a draft.**
