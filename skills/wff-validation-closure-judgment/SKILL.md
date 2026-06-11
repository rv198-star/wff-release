---
name: wff-validation-closure-judgment
description: Use when closing Phase-4 Stage-03 from Stage-02 evidence and you need an explicit validation verdict with downstream reliance boundaries.
---

# Phase-4 Stage-03 Closure Judgment

## Scope

This skill owns Phase-4 Stage-03.

Its job is to turn Stage-02 execution evidence into a clean closure decision without leaking into optional Stage-04 release-readiness approval.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write closure judgments, pass/return reasoning, residual-risk explanations, and acceptance conclusions in Chinese
- preserve code, file paths, commands, test ids, API/schema field names, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only closure artifacts or decision commentary unless the user explicitly requests English

## Required Inputs

Read:

- `docs/phases/phase-4/phase-4-skill-architecture-design-v0.1.md`
- the case Stage-01 gate posture
- the case Stage-02 execution results
- the case defect record
- the case review-bound record

## Decision Rules

1. If any `functional` item is not `pass`, return.
2. If any `data-fidelity` item is neither `pass` nor explicit `conditional-pass`, return.
3. If Phase-3 runtime truth keeps any mandatory item at `conditional-pass`, use `pass-with-mock-dependency`.
4. If a non-functional UI/visual item explicitly fails, return.
5. If all mandatory items pass but some UI/visual items remain unresolved, use `pass-with-review-bound-items`.
6. If unresolved UI review items reach half or more of the core UI surface count, return instead of soft-passing.
7. If critical-path human sign-off is still pending, do not emit plain `pass` even when automated evidence is green.
8. Use `pass` only when all item types pass with real evidence and no required sign-off is pending.
9. Never equate Stage-03 closure with optional Stage-04 release-readiness approval.

## Official Script

- `scripts/phase4/phase4_stage3_closure.py`

## Done Standard

Stage-03 is done only when it outputs:

- a closure decision
- a rationale
- explicit downstream may-assume / must-not-assume boundaries
- a root `phase4-delivery-gate.json`
- and, when a release profile exists, a clear handoff boundary into optional Stage-04
