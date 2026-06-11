# Stage-2 Runtime Hardening Targets (v0.1)

## 1. Purpose

This document distinguishes the current authored-package verification coverage of Phase-2 from the minimum runtime-hardening surface that should exist for a docs-first design / architecture phase.

Related Phase-2 support docs:

- `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- `docs/phases/phase-2/stage-2-traceability-baseline-v0.1.md`
- `docs/internal/improvement-reports/stage-2-retrospective-and-optimization-v0.1.md`

It does **not** attempt to build a full orchestrator.

Current aligned state:

- Stage-01~04 now all have the minimum pilot runtime-hardening artifacts described in this document
- the current boundary is no longer "Stage-01 only", but "all four authored substages at first-pass evidence depth"

It defines the smallest extra layer needed so Phase-2 is not limited to:

- runtime contracts
- dry-run examples
- rule-conformance robustness notes

without any state-transition or failure-path execution evidence.

---

## 2. What Phase-2 already has

Phase-2 already has:

- runtime contracts (`skill-contract.md`)
- execution SOPs (`stage-sop.md`)
- output templates (`output-template.md`)
- source cards (`source-cards.md`)
- self-test cases and dry-run outputs
- verification reports
- robustness test cases and reports
- coarse-grained traceability baseline with IDs / links / source binding

This means Stage-2 is already strong at:

- package shape
- gate / refusal / handoff logic
- review-bound truth-boundary discipline

But it is still weak at:

- runtime-visible state transitions
- failure-path output examples that feel like real execution traces
- explicit decision logs for stage-entry / stage-block / handoff states

---

## 3. What runtime hardening means for Stage-2

For Phase-2, runtime hardening means adding lightweight artifacts that record:

- what state the stage entered
- why a refusal / blocked / provisional state occurred
- what inputs were missing or insufficient
- what transition became possible next
- what downstream handoff was or was not allowed

This is especially important in Phase-2 because:

- boundary mistakes poison downstream decomposition
- hidden NFR uncertainty becomes design debt
- false convergence in Stage-04 can look “complete” too early

---

## 4. Minimum runtime-hardening artifacts

The minimum target artifact set is:

- `runtime-decision-log.md`
- `state-transition-record.md`
- `failure-path-output.md`

### 4.1 `runtime-decision-log.md`
Should record:

- intake summary
- state transitions taken
- decision reason
- gate-pass / blocked / refusal / provisional outcomes

### 4.2 `state-transition-record.md`
Should record:

- initial state
- next state
- trigger
- missing fields / decision conditions
- allowed next transitions

### 4.3 `failure-path-output.md`
Should record:

- an invalid or incomplete input case
- the exact blocked / refusal shape
- why the output is blocked and what must happen next

---

## 5. Current first-pass coverage

The first pilot started at:

- Stage-01 `architecture-definition-and-boundary-setting`

It has now been expanded to:

- Stage-02 `domain-module-service-decomposition`
- Stage-03 `data-storage-and-interface-design`
- Stage-04 `design-convergence-and-delivery-prototype`

Current coverage intent by stage:

- Stage-01: architecture-entry blockage, partial-NFR review-bound pass, dependency realizability surfacing
- Stage-02: brownfield conflict, hidden ownership overlap, review re-entry before decomposition handoff
- Stage-03: external dependency realizability, substitute-boundary retry path, stale-fact / duplicate-command rejection
- Stage-04: readiness downgrade, contradiction-triggered review re-entry, convergence-time evidence preservation

---

## 6. Relationship with wff-base-traceability-management

Runtime hardening and traceability are related but different:

- `wff-base-traceability-management` governs identity, binding, and links
- runtime hardening governs execution-state evidence

The minimum integration point is:

- runtime-hardening pilot artifacts should also carry or reference the same coarse trace anchors / output artifact IDs when they explain a blocked or handoff decision

---

## 7. Current target truth level

After this v0.1 step, Phase-2 should be described as:

- structurally complete authored package family
- verification-complete at package shape level
- coarse-grained traceability-baselined and registry-pilot-exercisable
- pilot runtime-hardened across Stage-01~04 at first-pass evidence depth

Not yet:

- live orchestrator-backed
- fully fine-grained registry-enforced end to end
- replay-proven against a broad adversarial case set in multiple equally deep local real cases

---

## 8. Immediate rule

From this point onward, Phase-2 should not claim full runtime hardening unless:

- runtime-decision logs exist
- failure-path artifacts exist
- state transitions are explicitly recorded

At minimum, every authored Phase-2 Stage should now demonstrate this pilot surface.
