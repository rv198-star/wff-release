---
name: wff-validation
description: Use when running or rerunning the official Phase-4 validation flow from a completed Phase-3 delivery root.
---

# Phase-4 Validation Orchestrator

## Overview

This is the official Phase-4 entry skill. It converts Phase-3 delivery evidence into validation closure, remediation routing, and claim-ceiling language.

Phase-4 is read-only over upstream artifacts. It validates and routes; it does not repair product truth, architecture truth, or implementation evidence by itself.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-4 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, test ids, API/schema fields, trace ids, artifact ids, env vars, and protocol keywords in their canonical form.

Generation governance: `docs/governance/bounded-generation-run-governance-v1.md` (中文：`docs/governance/bounded-generation-run-governance-v1.zh-CN.md`). It bounds section generation and review without weakening factual runtime evidence.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- a completed Phase-3 root exists
- the user needs official validation outputs rather than informal QA notes
- functional, data-fidelity, UI/manual/visual evidence, and closure boundaries must be tracked together

Do not use when:
- implementation is still changing materially
- contracts or runtime behavior are being redesigned
- the task is production cutover rather than validation closure

## Core Rules

1. Phase-4 must not mutate the supplied Phase-3 root.
2. Functional acceptance is mandatory.
3. Data-fidelity acceptance is mandatory when Phase-3 claims real runtime or persistence truth.
4. UI, visual, screenshot, video, and manual-review evidence stay explicit; missing evidence becomes `review-bound`, not fake green. For a requested frontend that already has current passing P3 browser evidence, screenshot/browser green proves observation only. Stage-02 uses a two-round AI Review plus synthesis gate: **Round 1 Open-ended Maturity Review (OMR)** is generated first in `open-ended-maturity-review-request.json`, contains no fixed review dimensions, receives no SQR score/findings, records concrete issues before one holistic maturity score, and passes only when the score is at least 80 with no `critical`/`high` finding. **Round 2 Structured Qualification Review (SQR)** then uses `ui-product-review-request.json` and its fixed dimensions; SQR must not receive OMR findings/results as review input. Current SQR dimensions include productness, first-entry/navigation/task continuity, **terminal-role fidelity and least privilege**, **business-data discovery/read-model sufficiency**, **Interaction Affordance & Task Efficiency**, **project-language alignment**, **clean first use plus reload/re-entry context recovery**, **trust/history/provenance**, Metadata Leakage, page composition/information hierarchy, business language, state/action clarity, desktop/mobile usability, and accessibility baseline. **Review Synthesis Gate (RSG)** does not average OMR and SQR scores: both independent reviews must pass; any valid OMR blocker or SQR failure blocks `ui-review`. Factual preconditions include one least-privilege persona journey per accepted terminal role when roles are required, no super-role substitution, no manual internal-ID consumer path, and clean-first-use evidence when the current contract requires it. Goals, constraints, blueprint/region names, operation/service-binding IDs, Agent instructions, architecture/authority rationale, and similar engineering metadata may shape the design but must not be treated as product copy by default. Validated OMR findings are retained in `open-ended-maturity-learning-candidates.json` as non-authoritative later-learning candidates. Workflow preserves the reviewer-provided finding facts but does not generalize them, affect the current review, or mutate SQR. Repeated cross-scenario/version OMR finding patterns may be generalized and promoted into later SQR dimensions/checks only when they form stable, business-independent PASS/FAIL knowledge and a later explicit Agentic/governance decision accepts the promotion; one-off findings do not automatically grow the checklist, and OMR is never retired merely because SQR matures.
5. Consume required current-generation evidence even when an acceptance catalog omitted a corresponding item. A failed runtime, targeted-test, exact-realization binding, Trace, semantic-realization, or P3 overall-claim report cannot coexist with zero defects and a passing closure. Phase-2 decision coverage must preserve the same truth boundary: a review-bound, deferred, provider-neutral, unknown, or explicitly unaccepted identity/provider/token/key posture is not an accepted decision and must not be promoted into a synthetic high-priority P4 coverage obligation; explicit accepted structured identity/token/key choices remain mandatory coverage inputs.
6. Preserve the P3 result layers exactly: backend/runtime diagnostic, semantic realization, Human/AI review, project realization knowledge, and overall claim. P4 consumes the overall weakest-evidence state and item-level owners/routes; it must not upgrade `implementation-in-progress` because a technical score or scaffold report is green. For current modular P3 evidence, `runtime_test_refs` identify the concrete passed tests, while `runtime_evidence_refs` must resolve to retained parseable JSON verification reports; missing, malformed, or non-JSON evidence refs remain fail-closed and must not be reinterpreted as proof.
7. An environment/transient-only disposition may keep a failure review-bound only when it is caller-accepted, bound to the exact evidence digest, and names an accepted decision reference, owner, reason, retry route, and claim ceiling; P4 records that the classification was not independently verified.
8. Production approval, owner sign-off, online UAT, go-live, rollback readiness, monitoring handover, and production risk acceptance are outside default WFF authority unless supplied as external evidence.
9. Every return must name the owning phase, evidence reference, minimum rerun boundary, and claim ceiling. Current UI/Product Review findings normally return to `p3-frontend-authoring`; missing product/API/state authority is routed to P3 for a gap decision and a next-version `backport_target`, never invented in P4. Any repaired frontend must rerun P3 browser/runtime evidence before the prior review can be reused; changed current identity creates a new review request.
10. P4 is read-only over the fixed project artifact `<project-artifact-root>/p3-realization-decisions.md`. For current P3 closure, require the `.phase3-evidence/p3-realization-decisions-binding.json` sidecar, exact Markdown SHA, P3 decision identity, canonical Authority Delta digest, complete delta projection/index coverage, and `upstream_reconciled=false`. A missing or drifted realization-decisions artifact blocks current P3 admission. P4 must not edit the Markdown, backfill PRD/ESP, or promote P3 realization knowledge into P1/P2 authority.

P4 consumes effective truth as frozen P1/P2 plus registered P3 decision deltas, using the merged realization-decisions view and exact `supersedes` bindings. Existing OMR → isolated SQR also reviews T2 decision records without extra rounds or role calls. P4 routes implementation defects and gap findings only to P3 within the cycle; it never regenerates P1/P2. If the upstream direction is fundamentally wrong, report it for a human cycle-termination decision.

## Phase Review And Strict-Proof Closure

P4 remains read-only validation and routing. Expose a Phase Review Breakpoint and Agent-led Review routing so evidence judgment and routing happen under a claim ceiling. Reviewers may approve (`批准`), require modification (`要求修改`), require return (`要求返回`), or provide intervention input (`提供干预输入`). P4 must not convert Review findings into upstream repair inside P4.

Strict-proof closure is valid only when validation honestly exposes risk, consumes available evidence, caps formal claims, and routes defects to the owning phase with a minimum rerun boundary. P4 protected surfaces must remain root-visible or resolver-backed for downstream consumers.

P4 does not challenge every evidence read. Use the bounded doubt-driven protocol only when an Agentic closure judgment would lower a real failure or raise the claim ceiling, including accepted environment/transient-only dispositions and unresolved-risk closure. The reviewer receives the exact evidence artifact/digest, closure contract, admitted environment/context identities and unknowns—not the preferred closure decision or P4 reasoning journey.

The P4 validation Agent reconciles every material finding. If the contract/context cannot support the disposition, keep the evidence failed and return to its owner. A valid unresolved classification remains explicitly review-bound with owner, retry route and claim ceiling. Default depth is one pass, maximum three; cross-model review is optional/per-invocation authorized. Mechanical evidence collection, digest verification, defect registration and ordinary reruns remain excluded.

Any environment/transient disposition that lowers a current failure requires `wff.evidence-challenge-binding.v1` over the exact evidence path/digest, P4 disposition contract and classification/owner/reason/retry/ceiling subject. Historical or unrelated challenge records cannot downgrade current evidence. Historical `legacy-pre-bounded-challenge-v1` decisions remain readable audit inputs only and never authorize a stronger current closure claim.

## Required Inputs

Read first:
- `docs/phases/phase-4/phase-4-skill-architecture-design-v0.1.md`
- `docs/phases/phase-4/phase-4-output-contract-v0.1.md`
- `reference-packages/phase4-validation-closure/README.md`
- `templates/testing-validation-planning-package.md`
- the case Phase-3 root
- `p3-agentic-implementation-authority.json` and its application receipt when implementation authority is claimed
- `p3-exact-realization-binding-ledger.json`
- `phase3-impl-aggregate-report.json` or the equivalent full-mainline overall result

## WFF Core Contract Binding

- Machine descriptor: `validation-closure`, phase `P4`, route `phase-4`, under `wff-core-contract` `1.0.0`.
- Consumes `phase-contract`, `handoff-contract`, `evidence-contract`, `claim-state-contract`, and `reentry-return-contract`.
- Core carries evidence identity, claim ceilings, and remediation routing envelopes; Phase-4 Agentic work owns validation judgment.
- Missing or incompatible Core metadata blocks validation entry and never authorizes a stronger claim.

## Entrypoint

Run:

```bash
python3 scripts/phase4/run_phase4_first_version.py \
  --phase3-root <phase3-root> \
  --output-dir <phase4-output> \
  --version <version-label>
```

Use `scripts/phase4/run_p1_p4_mainline_closure.py` only for mainline closure aggregation across supplied P1-P4 roots.

## Execution Sequence

1. Freeze the supplied Phase-3 evidence root.
2. Plan acceptance from inherited contracts, Phase-2 decisions, Phase-3 evidence, and declared validation boundary.
3. Execute evidence consumption against real inherited reports and runtime artifacts. If Stage-02 emits frontend AI Review requests, run them in order: first give `open-ended-maturity-review-request.json` plus current screenshots/traces to an independent open-ended reviewer without SQR dimensions/scores/findings; then give `ui-product-review-request.json` to an independent structured reviewer without OMR findings/results. Rerun Phase-4 with both evidence entries in the external manifest through `--external-evidence-manifest` / `--external-evidence-dir`. The rerun must retain validated OMR findings in `open-ended-maturity-learning-candidates.json`; this artifact is learning evidence only and must not be fed back into the current OMR or SQR reviewer.
4. Classify missing or weak evidence as review-bound, blocked, or return-worthy. RSG closes subjective `ui-review` only when both OMR and SQR pass independently; never average the two scores or let one compensate for the other. A valid OMR/SQR fail is a real defect/return signal; do not soften it because functional/browser evidence is green.
5. Emit closure judgment and routed findings.
6. Validate the Phase-4 output contract.
7. Stop at validation closure unless an explicit release-readiness extension is requested.

## Remediation Routing

Route by cause:
- P4 evidence-consumption defect -> rerun Phase-4
- a consumed semantic-realization or exact-binding ledger keeps each existing commitment's contract/operation/decision identity, owner, disposition, reason, evidence boundary, claim ceiling, and minimum rerun route; a legacy `local-return-required` item is compatibility-routed to Phase-3 for a gap decision and backport entry, while a Phase-3 `realization-incomplete`, missing decision binding, or unconfirmed Trace item returns to Phase-3
- missing Phase-3 runtime/test evidence -> return to Phase-3
- implementation violates accepted contracts -> return to Phase-3
- architecture/design truth is invalid or insufficient -> return to Phase-3 for a gap decision and next-version backport
- product/source truth is missing -> return to Phase-3 for a gap decision and next-version backport
- external production or owner evidence is absent -> keep review-bound outside default WFF authority

## Required Output Set

A valid Phase-4 package preserves:
- acceptance planning artifacts
- evidence execution results
- validation closure report
- routed remediation findings
- claim ceiling and delivery boundary
- output-contract validation report
- phase verdict, scorecard, and acceptance matrix

## Completion Standard

Stop with one of these states:
- `validation-closed`: supplied evidence supports the stated claim
- `closed-with-review-bound-items`: validation can close only with named ceilings
- `return-to-phase3`
- `blocked`

Do not present Phase-4 as production approval unless explicit external production evidence is supplied and named.


T2 review handling from M2: a new decision containing `new_facts` requires
`confirmation_required = true`. Bind the existing isolated SQR verdict to the original
record; mark rejected decisions in the effective view and next-version backport queue,
exclude their proposed facts from active truth, and never cite them as accepted resolutions.
List any code surfaces where a rejected decision was already applied; an annotation does
not undo code. Keep frozen historical records unchanged. See the existing
[p3-realization-decisions contract](../../reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md).
