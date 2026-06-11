# Validation / Closure Stage Skill Package (Phase-4)

## 1. What this is

This directory is the retained **Phase-4 (validation / closure) Stage Skill set** for this repository.

After the development / pre-production scope boundary was clarified, this package should be read as a thin read-only validation gate package, not as a production release or second implementation package. It contains:

- a frozen 3-stage main chain
- an optional Stage-04 development / pre-production release-readiness extension that is explicitly opt-in at runtime
- runtime core files for each stage
- Stage-01 control-layer templates
- happy-path self-test / dry-run / verification artifacts
- rule-level robustness coverage artifacts
- bilingual audit mirrors for runtime / verification / robustness assets
- source/control/runtime layering that stays within the Phase-4 boundary

In other words, this directory is currently:

> **the retained package set for the Phase-4 thin validation / closure gate, with source, control, runtime, verification, robustness, and bilingual audit assets aligned**

---

## 2. The 3 main substages in Phase-4

### Stage-01: acceptance-coverage-planning
Answers:
- what acceptance claims must be validated
- how `TEST-* -> API-* -> REQ-*` mapping is preserved
- what coverage posture and gate posture should govern Stage-02

### Stage-02: evidence-execution-and-defect-identification
Answers:
- how bounded validation work is executed under Stage-01 controls
- how execution evidence, defect visibility, and blocked-path visibility are recorded

### Stage-03: validation-closure-and-delivery-readiness-judgment
Answers:
- how Stage-02 evidence becomes a validation closure judgment
- what downstream consumers may and must not assume
- which unresolved defects / risks remain explicit after Phase-4 closes

The directory name is retained for compatibility. Stage-03 closes testing-validation and downstream reliance boundaries; it does not own P3 delivery readiness or production authorization.

### Optional Stage-04: release-readiness-and-final-handoff
Answers:
- whether a development / pre-production release-readiness posture, sign-off status record, residual-risk visibility record, or handoff pack is needed after Stage-03
- how release-readiness posture is packaged without turning Stage-03 itself into release approval
- what final handoff package downstream operators or owners should receive

---

## 3. What assets each stage currently contains

Each stage currently contains three layers of assets:

### A. Runtime Assets
- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

### B. Verification Assets
- `verification.md`
- `self-test-case.md`
- `self-test-dry-run-output.md`
- `self-test-verification-report.md`

### C. Chinese Audit Mirrors
- runtime mirrors: `skill-contract.zh-CN.md`, `stage-sop.zh-CN.md`, `output-template.zh-CN.md`, `source-cards.zh-CN.md`
- verification mirrors: `verification.zh-CN.md`, `self-test-*.zh-CN.md`
- robustness mirrors: `robustness-test-case.zh-CN.md`, `robustness-test-report.zh-CN.md`

### D. Robustness Assets
- `robustness-test-case.md`
- `robustness-test-report.md`

Phase-4 also depends on shared Stage-01 control artifacts under `templates/`.

---

## 4. What Phase-4 now adds beyond Phase-3

Phase-4 is not “more P3 testing.” Its special burden is:

- reading P3 implementation and runtime evidence into acceptance-facing validation structure
- preserving `TEST-* -> API-* -> REQ-*` traceability instead of narrative-only checklists
- enforcing evidence discipline before closure claims
- routing failed closure back to the owning upstream phase
- separating Stage-03 closure judgment from optional Stage-04 release-readiness confirmation

So the core discipline of this Phase-4 package is:

> **preserve testing truth boundaries while still producing a usable downstream closure judgment**

Phase-4 must not patch implementation, architecture, or requirement truth. When closure cannot be granted, it should identify the owning phase:

- P4 when the validation layer failed to consume available evidence
- P3 when implementation or runtime evidence is missing/incorrect
- P2 when the accepted design/contract is not validation-ready
- P1/P2 when validation would otherwise have to invent upstream product/design truth
- review-bound carryover when the gap is UI/visual/manual evidence that does not block mandatory functional validation

---

## 5. Current verification status

### Completed in this first pass
- Stage-01 self-test / dry-run / verification: present
- Stage-02 self-test / dry-run / verification: present
- Stage-03 self-test / dry-run / verification: present

### Completed bilingual audit coverage
- runtime mirrors: present
- verification mirrors: present
- robustness mirrors: present

### Completed robustness coverage
- refusal path coverage
- blocked path coverage
- fake-readiness / fake-completion prevention coverage
- Stage-03 / optional Stage-04 boundary leakage prevention coverage

### Current boundary
Phase-4 mainline is now structurally complete as a first-pass authored package set and has passed a first explicit audit/self-test checkpoint at the current target depth.

It is **not**:
- a P3 integration-test replacement
- a production deployment, rollback, cutover, monitoring, or online UAT automation package
- a real owner sign-off or production risk-acceptance authority
- a place to repair generated P3/P4 proof outputs by hand

The optional Stage-04 runtime surface now exists as an opt-in repository runner extension, but it remains a release-readiness packaging layer rather than release execution or production authorization.

---

## 6. How to use this package right now

The recommended current use is:

> **treat each stage as a manual runtime pack**

That means:
- `skill-contract.md` defines the stage boundary
- `stage-sop.md` defines the execution order
- `output-template.md` defines the required artifact shape
- `source-cards.md` defines the preferred method/material inputs

Verification artifacts should be used as:
- examples of good-path dry-run structure
- checks for whether a real run is shape-correct
- reminders of refusal / blocked / fake-certainty boundaries

---

## 7. One-sentence summary

This directory is now:

> **the retained formal Stage Skill set for the Phase-4 thin validation / closure gate, with source, control, runtime, verification, rule-level robustness, and bilingual audit assets present.**
