# Phase-4 Skill Architecture Design v0.1

## 1. Goal

Phase-4 is the official thin `testing-validation` gate for the development / pre-production lifecycle.
When a case needs handoff-readiness packaging, Phase-4 may extend into an optional `Stage-04 release-readiness-and-final-handoff`.

Its job is not to implement software.
Its mainline job is to read Phase-3 delivery evidence and convert it into a closure-grade validation judgment with explicit traceability, claim ceilings, and residual reliance boundaries.
If the judgment cannot close, Phase-4 must route remediation to the owning upstream phase instead of fixing the upstream artifact itself.

## 2. Boundary

### Phase-4 is responsible for

- functional acceptance mapped from `TEST-* -> API-* -> REQ-*`
- Phase-2 decision alignment so validation does not drift away from the design intent inherited from architecture planning
- UI state review at the surface / page level
- visual acceptance evidence such as screenshot, video, or manual walkthrough record
- defect visibility, blocked-path visibility, and review-bound carryover
- critical-path human sign-off visibility when automation alone is insufficient for a trustworthy closure
- validation closure judgment
- structured remediation routing when validation cannot close
- optional development / pre-production release-readiness posture, sign-off status visibility, residual-risk visibility, and final handoff packaging when `Stage-04` is explicitly enabled

### Phase-4 is not responsible for

- new backend/frontend feature implementation
- rerunning or replacing Phase-3 integration suites by default
- patching Phase-3 code, tests, runtime assets, or delivery gates
- rewriting Phase-2 contracts or architecture decisions
- inventing missing Phase-1 product truth
- replacing missing Phase-3 contract/runtime evidence with guesses
- production release approval, online UAT ownership, real owner sign-off, or production risk acceptance
- deployment cutover orchestration

## 3. Mainline

Phase-4 uses a thin 3-stage main chain by default:

1. `Stage-01 acceptance-coverage-planning`
2. `Stage-02 evidence-execution-and-defect-identification`
3. `Stage-03 validation-closure-and-delivery-readiness-judgment`

Optional extension:

4. `Stage-04 release-readiness-and-final-handoff`

The Stage-03 directory name is retained for compatibility, but its responsibility is testing-validation closure and downstream reliance boundaries, not ownership of delivery readiness.

The intent is to stay lighter than Phase-3 while keeping handoff readiness optional:

- reuse inherited Phase-3 evidence
- avoid creating a second implementation runtime
- spend effort on evidence quality, coverage logic, and closure honesty
- route concrete remediation to P1/P2/P3 instead of performing it inside P4
- only activate `Stage-04` when a case truly needs development / pre-production release-readiness posture, sign-off status visibility, residual-risk visibility, or handoff packaging

## 4. Acceptance Model

Phase-4 explicitly separates three acceptance item types.

### 4.1 `functional`

This is the mandatory acceptance layer.

- source: Phase-3 trace registry + worker-run evidence
- evidence shape: executable test evidence
- closure rule: every `functional` item must pass

### 4.2 `ui-review`

This is the interface-state review layer.

- source: frontend worker packets + implemented routes + linked automated evidence
- evidence shape: route files, packet verification, optional manual review note
- closure rule: may remain `review-bound`, but must stay explicit

### 4.3 `visual-evidence`

This is the screenshot/video/manual visual capture layer.

- source: real screenshot/video/manual review artifacts only
- evidence shape: PNG/JPG/WebP/GIF/MP4/WebM/manual record
- closure rule: may remain `review-bound` when the environment cannot capture visuals; must never be fabricated

## 5. Stage Responsibilities

### Stage-01

Freeze:

- acceptance catalog
- contract registry
- decision coverage alignment against Phase-2
- coverage rationale
- entry/exit gate posture
- execution-control artifact

Key rule:

- if screenshot/manual visual evidence is not currently available, mark that posture as `review-bound` up front
- if a UI/visual item sits on the critical path, declare whether human sign-off is required instead of waiting until closure time

### Stage-02

Execute against the Stage-01 model:

- consume real Phase-3 test reports
- mark `functional` items pass/fail/blocked from actual evidence
- accept external screenshot/video/manual review manifests when they are explicitly supplied
- mark `ui-review` / `visual-evidence` pass only when real review artifacts exist
- otherwise keep them `review-bound` or `blocked`

Key rule:

- missing screenshots in a non-capture environment are not a reason to lie; they are a reason to record explicit review-bound carryover
- critical-path sign-off is a first-class evidence channel, not an implicit side note

### Stage-03

Close with explicit decision logic:

- `return` if any `functional` item is not `pass`
- `return` if a non-functional acceptance item explicitly fails
- `pass-with-review-bound-items` if all functional items pass but some UI/visual items remain review-bound
- `pass-with-review-bound-items` if critical-path human sign-off is still pending
- `pass` only if all item types pass with real evidence and any required critical-path sign-off is explicit

When returning, emit a remediation packet with:

- `return_target`
- `reason_class`
- `evidence_refs`
- `required_action`
- `minimum_rerun_from`
- `downstream_validation_required`
- `suggested_commands`

Routing rules:

- Phase-4 failed because it did not consume available Phase-3 evidence -> `return_target = P4`
- Phase-3 mainline evidence exists but lacks full targeted SQL / contract / scenario / replay evidence -> `return_target = P3`, `reason_class = missing-phase3-full-targeted-evidence`
- Phase-3 evidence is missing or too weak for a claim Phase-3 already makes -> `return_target = P3`
- implementation violates accepted Phase-2 contracts -> `return_target = P3`
- Phase-2 contract/design is invalid or not validation-ready -> `return_target = P2`
- Phase-1 or Phase-2 truth gap would force validation to invent truth -> `return_target = P1/P2`
- non-blocking UI / visual / manual evidence is absent -> keep `review-bound` instead of returning

## 6. Downstream Contract

Stage-03 hands off to optional `Stage-04` or equivalent downstream governance with:

- a closure decision
- residual review-bound items
- a list of what downstream may rely on
- a list of what downstream must not assume
- a passing S1-S3 output-contract report

Mandatory downstream rule:

- `pass-with-review-bound-items` is not equivalent to `Stage-04` release-readiness approval
- Phase-4 S1-S3 output-contract validation proves testing-validation closure integrity; it does not approve release or create final handoff packaging
- Stage-04 may package handoff readiness, but production go-live, rollback, monitoring, real owner sign-off, and production risk acceptance remain external authorities unless supplied as external evidence

## 7. Current Environment Policy

The current local environment may lack:

- browser-driven screenshot capture
- visual diff infrastructure
- video recording harness

Therefore the official policy is:

- include UI/visual acceptance in Phase-4 anyway
- do not silently drop it
- do not fabricate assets
- keep it as `review-bound` when the environment cannot actually produce the evidence

## 8. Official Scripts

- `scripts/phase4/phase4_stage1_planning.py`
- `scripts/phase4/phase4_stage2_execution.py`
- `scripts/phase4/phase4_stage3_closure.py`
- `scripts/phase4/run_phase4_first_version.py`

Current note:

- `Stage-04` is merged into Phase-4 conceptually and is available only through an explicit opt-in runner flag.
- The Stage-04 output contract is defined in `docs/phases/phase-4/phase-4-stage-04-release-readiness-contract-v0.1.md`.
- The default runner path must remain read-only over the supplied Phase-3 root and write only under the requested Phase-4 output directory.

## 9. Output Expectation

A complete fresh Phase-4 run should produce:

- Stage-01 planning artifacts
- Stage-02 execution / defect / review-bound artifacts
- Stage-03 closure judgment and downstream boundary note
- S1-S3 output-contract report
- remediation packet when closure returns
- optional Stage-04 release-readiness and final handoff artifacts when `--enable-stage4` is explicitly enabled
- root metadata, quality check, and delivery gate

## 10. One-Sentence Summary

Phase-4 is the thin read-only evidence and judgment layer that turns Phase-3 delivery outputs into honest validation closure, and when needed, extends into an optional Stage-04 for development / pre-production handoff readiness without splitting into a separate lifecycle phase.
