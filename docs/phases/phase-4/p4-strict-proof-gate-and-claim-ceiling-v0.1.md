# P4 Strict-Proof Gate And Claim Ceiling (v0.1)

Status: `WO-119A.10` local verification record
Date: 2026-05-03
Owning work: `WO-119A.10`
Control boundary: `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
Agent-led Review routing: `docs/governance/v1.3-agent-led-review-routing-v0.1.md`
Chinese mirror: `docs/phases/phase-4/p4-strict-proof-gate-and-claim-ceiling-v0.1.zh-CN.md`

## Purpose

This document defines the `v1.3.1` closure expectation for Phase-4 validation.

P4 closure must prove honest validation, risk exposure, routing, and claim ceiling. It must not become release approval or a repair phase.

## Closure Rule

P4 may close only when the output makes a substantive judgment on:

- evidence sufficiency;
- validation risk;
- formal claim ceiling;
- delivery boundary;
- review-bound carryover;
- return routing.

Acceptance catalog completion, output-contract pass, strict-proof report existence, or Stage-03 pass wording are support signals. They are not sufficient closure by themselves.

## Required Closure Statement

The P4 closeout surface should state:

- which claims are supported by supplied evidence;
- which claims are capped by missing evidence;
- which risks remain review-bound;
- which findings require return to P1/P2/P3/P4 or external authority;
- whether testing-validation may close under the development / pre-production lifecycle boundary;
- whether optional Stage-04 was explicitly requested.

## Strict-Proof Boundary

Strict-proof is a gate and claim-ceiling mechanism, not a peer mainline mode.

It may validate evidence and block or cap claims. It must not:

- invent source truth;
- redesign architecture;
- patch implementation;
- fabricate missing runtime or external evidence;
- turn production-shaped wording into production authority.

## Failure And Routing

Route findings through `v1.3 Agent-Led Review Routing`:

- source truth or product/spec gap -> pre-P1 admission or P1;
- architecture gap -> P2;
- implementation patch or implementation/runtime/test evidence gap -> P3;
- validation evidence-consumption or closure-judgment defect -> P4;
- missing production / owner-signoff / online UAT evidence -> outside default WFF authority unless supplied as external evidence.

If P4 returns, the output must include evidence references, required action, minimum rerun boundary, claim ceiling, and review-bound carryover.

## Local Verification Question

`WO-119A.10` is complete if this document and the P4 skill mirror make clear that P4 closure is evidence judgment and routing under a claim ceiling, not production approval or upstream repair.
