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
4. UI, visual, screenshot, video, and manual-review evidence stay explicit; missing evidence becomes `review-bound`, not fake green.
5. Consume required current-generation evidence even when an acceptance catalog omitted a corresponding item. A failed runtime, targeted-test, exact-realization binding, Trace, semantic-realization, or P3 overall-claim report cannot coexist with zero defects and a passing closure. Phase-2 decision coverage must preserve the same truth boundary: a review-bound, deferred, provider-neutral, unknown, or explicitly unaccepted identity/provider/token/key posture is not an accepted decision and must not be promoted into a synthetic high-priority P4 coverage obligation; explicit accepted structured identity/token/key choices remain mandatory coverage inputs.
6. Preserve the P3 result layers exactly: backend/runtime diagnostic, semantic realization, Human/AI review, and overall claim. P4 consumes the overall weakest-evidence state and item-level owners/routes; it must not upgrade `implementation-in-progress` because a technical score or scaffold report is green. For current modular P3 evidence, `runtime_test_refs` identify the concrete passed tests, while `runtime_evidence_refs` must resolve to retained parseable JSON verification reports; missing, malformed, or non-JSON evidence refs remain fail-closed and must not be reinterpreted as proof.
7. An environment/transient-only disposition may keep a failure review-bound only when it is caller-accepted, bound to the exact evidence digest, and names an accepted decision reference, owner, reason, retry route, and claim ceiling; P4 records that the classification was not independently verified.
8. Production approval, owner sign-off, online UAT, go-live, rollback readiness, monitoring handover, and production risk acceptance are outside default WFF authority unless supplied as external evidence.
9. Every return must name the owning phase, evidence reference, minimum rerun boundary, and claim ceiling.

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
3. Execute evidence consumption against real inherited reports and runtime artifacts.
4. Classify missing or weak evidence as review-bound, blocked, or return-worthy.
5. Emit closure judgment and routed findings.
6. Validate the Phase-4 output contract.
7. Stop at validation closure unless an explicit release-readiness extension is requested.

## Remediation Routing

Route by cause:
- P4 evidence-consumption defect -> rerun Phase-4
- a consumed semantic-realization or exact-binding ledger keeps each existing commitment's contract/operation/decision identity, owner, disposition, reason, evidence boundary, claim ceiling, and minimum rerun route; an upstream `local-return-required` item returns to Phase-2, while a Phase-3 `realization-incomplete`, missing decision binding, or unconfirmed Trace item returns to Phase-3
- missing Phase-3 runtime/test evidence -> return to Phase-3
- implementation violates accepted contracts -> return to Phase-3
- architecture/design truth is invalid or insufficient -> return to Phase-2
- product/source truth is missing -> return to Phase-1 or intake
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
- `return-to-phase2`
- `return-to-phase1`
- `blocked`

Do not present Phase-4 as production approval unless explicit external production evidence is supplied and named.
