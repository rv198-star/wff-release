# P1 Value-Bearing Artifact Closure (v0.1)

Status: `WO-119A.07` local verification record
Date: 2026-05-03
Owning work: `WO-119A.07`
Control boundary: `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
Stage Judgment Lens: `docs/governance/v1.3-stage-judgment-lens-v0.1.md`
Chinese mirror: `docs/phases/phase-1/p1-value-bearing-artifact-closure-v0.1.zh-CN.md`

## Purpose

This document defines the `v1.3.1` closure expectation for Phase-1 product requirements.

P1 closure must prove that the product requirement package carries enough product, business, user, acceptance, and source-truth value for P2 to design from it without inventing missing product truth.

## Closure Rule

P1 may close only when the output makes a substantive judgment on:

- product value;
- business value;
- user or stakeholder value;
- pain strength and status quo pressure;
- narrowest valuable wedge;
- acceptance meaning;
- source truth confidence;
- open truth gaps and review-bound carryover.

Format completeness, trace closure, PRD assembly, convergence score, or script pass are support signals. They are not sufficient value-bearing closure by themselves.

## Required Closure Statement

The P1 closeout surface should state:

- what product wedge is worth pursuing now;
- whose problem or decision it serves;
- why the status quo is insufficient;
- what smallest valuable slice should be protected;
- which source facts are strong enough to drive architecture;
- which facts remain review-bound;
- whether the package can continue to P2, needs bounded P1 remediation, or must return to pre-P1 source admission.

## Failure And Routing

Route findings as:

- `源头事实缺口` (`source-truth-gap`) -> pre-P1 admission or P1, depending on whether the source exists and was mishandled;
- `产品/规格缺口` (`product-spec-gap`) -> P1 remediation;
- architecture, implementation, or evidence issues -> downstream phase only when P1 truth is already sufficient.

If P2 would need to invent product goal, business value, user value, acceptance meaning, or status quo pressure, P1 is not value-bearing closed.

## No-Gain Disclosure Rule

High score is not the same as value gain.

If a P1 run has a high convergence score but selects no Agentic deepening target, the closeout must do one of three things:

- mark the result `stable-no-material-gain`;
- select a bounded high-value deepening target and rerun/remediate that target;
- explain why another deepening round is unlikely to create meaningful product or business value.

Do not present `target_count: 0` plus a high score as proof that `v1.3.1` improved P1 output quality.

## Local Verification Question

`WO-119A.07` is complete if this document and the P1 skill mirror make clear that P1 closure is a product-value and source-truth judgment, not PRD format completion.
