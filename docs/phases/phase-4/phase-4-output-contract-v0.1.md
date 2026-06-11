# Phase-4 Output Contract v0.1

## Goal

Define the stable Phase-4 S1-S3 testing-validation output package.

This contract describes the artifacts and closure semantics that downstream reviewers may rely on after Phase-4 Stage-03. It is a read-only validation and handoff-boundary contract over supplied Phase-3 evidence. It does not define Phase-4 Stage-04 release approval, production risk acceptance, owner sign-off, deployment, rollback, or final handoff packaging.

## Root Artifacts

Every complete Phase-4 S1-S3 output root must include:

- `phase-verdict.json`
- `phase4-delivery-gate.json`
- `phase4-quality-check.json`
- `phase4-run-metadata.json`
- `phase-acceptance-matrix.md`
- `phase-mainline-scorecard.md`

## Stage-01 Artifacts

Stage-01 freezes the acceptance model and execution posture.

Required artifacts:

- `stage-01-acceptance-coverage-planning/acceptance-catalog.json`
- `stage-01-acceptance-coverage-planning/contract-registry.json`
- `stage-01-acceptance-coverage-planning/decision-coverage-alignment.json`
- `stage-01-acceptance-coverage-planning/runtime-environment-readiness.json`
- `stage-01-acceptance-coverage-planning/stage-01-summary.json`
- `stage-01-acceptance-coverage-planning/testing-validation-planning-package.md`
- `stage-01-acceptance-coverage-planning/acceptance-checklist.md`
- `stage-01-acceptance-coverage-planning/test-coverage-explanation.md`
- `stage-01-acceptance-coverage-planning/test-entry-exit-gate-checklist.md`
- `stage-01-acceptance-coverage-planning/test-execution-control.md`

## Stage-02 Artifacts

Stage-02 executes the Stage-01 model against inherited evidence and records defects, blocked items, and review-bound items.

Required artifacts:

- `stage-02-evidence-execution-and-defect-identification/test-evidence-index.json`
- `stage-02-evidence-execution-and-defect-identification/test-execution-results.json`
- `stage-02-evidence-execution-and-defect-identification/test-execution-evidence.md`
- `stage-02-evidence-execution-and-defect-identification/defect-record.json`
- `stage-02-evidence-execution-and-defect-identification/review-bound-record.json`
- `stage-02-evidence-execution-and-defect-identification/external-evidence-consumption.json`
- `stage-02-evidence-execution-and-defect-identification/frontend-surface-audit.json`
- `stage-02-evidence-execution-and-defect-identification/critical-path-signoff-record.json`
- `stage-02-evidence-execution-and-defect-identification/stage-02-summary.json`

## Stage-03 Artifacts

Stage-03 converts Stage-02 evidence into a testing-validation closure judgment and downstream reliance boundary.

The retained directory name includes `delivery-readiness-judgment` for compatibility with existing scripts and proof snapshots. It does not mean Stage-03 owns delivery readiness or production authorization.

Required artifacts:

- `stage-03-validation-closure-and-delivery-readiness-judgment/test-closure-judgment.md`
- `stage-03-validation-closure-and-delivery-readiness-judgment/downstream-boundary-note.md`
- `stage-03-validation-closure-and-delivery-readiness-judgment/stage-03-summary.json`

## Closure Decisions

Phase-4 S1-S3 may close with these decisions:

- `pass`
- `pass-with-review-bound-items`
- `pass-with-mock-dependency`
- `return`

Closure rules:

- `pass` requires all mandatory functional and data-fidelity evidence to pass, no blocking defects, no review-bound items, and no pending critical sign-off.
- `pass-with-review-bound-items` requires all mandatory functional and data-fidelity evidence to pass while non-blocking UI, visual, or manual-review evidence remains explicit.
- `pass-with-mock-dependency` is allowed only when runtime truth is explicitly conditional and downstream reliance is capped.
- `return` requires remediation routing evidence.
- Stage-03 may recommend `testing-validation-complete`; it must not declare `release-approved`, production go-live approval, real owner sign-off, or production risk acceptance.

## Required Root Semantics

`phase-verdict.json` must expose:

- `verdict`
- `total_score` or `phase_total_score`
- `review_bound_items_count`
- `blockers_count`

`phase4-delivery-gate.json` must expose:

- `closure_decision`
- `recommended_formal_state`
- `checks`

For a plain `pass`, `phase4-delivery-gate.json` must show:

- `recommended_formal_state: testing-validation-complete`
- `checks.blocking_count: 0`
- `checks.review_bound_count: 0`
- `checks.signoff_pending_count: 0`

## Remediation Semantics

When closure returns, the output should include remediation references in the delivery gate or run metadata. The remediation packet must identify:

- `return_target`
- `reason_class`
- `evidence_refs`
- `required_action`
- `minimum_rerun_from`
- `downstream_validation_required`

If a generated return lacks a remediation packet, downstream must treat the output as contract-incomplete rather than inventing the route from memory.

## Stage-04 Boundary

This contract ends at Stage-03 testing-validation closure.

It does not authorize:

- release approval
- final go / no-go decision
- owner sign-off
- risk acceptance
- deployment cutover
- rollback approval
- operations handoff packaging
- production monitoring handover

Those belong to optional Phase-4 Stage-04 or downstream release governance.

When Stage-04 is explicitly enabled, use the separate contract:

- `docs/phases/phase-4/phase-4-stage-04-release-readiness-contract-v0.1.md`
