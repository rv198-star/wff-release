---
name: wff-validation-acceptance-planning
description: Use when building Phase-4 Stage-01 planning outputs from a frozen Phase-3 root, including the acceptance catalog, coverage rationale, gate posture, and execution-control artifact.
---

# Phase-4 Stage-01 Acceptance Coverage Design

## Scope

This skill owns Phase-4 Stage-01.

Its job is to freeze a usable validation model before execution starts.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write acceptance planning text, coverage rationale, gate explanations, and execution-control guidance in Chinese
- preserve code, file paths, commands, test ids, API/schema field names, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only planning artifacts or acceptance rationale unless the user explicitly requests English

## Required Inputs

Read:

- `docs/phases/phase-4/phase-4-skill-architecture-design-v0.1.md`
- `templates/testing-validation-planning-package.md`
- `templates/acceptance-checklist.md`
- `templates/test-coverage-explanation.md`
- `templates/test-entry-exit-gate-checklist.md`
- `templates/test-execution-control-template.md`
- the case Phase-3 root

## Stage-01 Rules

1. Build the acceptance catalog from real Phase-3 trace and contract evidence.
2. Preserve `TEST-* -> API-* -> REQ-*` mapping.
3. Split acceptance into:
   - `functional`
   - `data-fidelity`
   - `ui-review`
   - `visual-evidence`
4. Functional and data-fidelity items are mandatory.
5. Data-fidelity items must consume Phase-3 runtime truth artifacts and distinguish `pass` from `conditional-pass`.
6. UI/visual items are explicit even when no capture harness exists.
7. If screenshot/manual evidence is unavailable, mark the posture `review-bound`.
8. Add risk metadata so critical-path UI/visual items can declare whether human sign-off is required.
9. When `phase2_root` is discoverable from Phase-3 metadata, emit a decision-coverage artifact that shows which Phase-2 design decisions are or are not covered by explicit acceptance items.

## Official Script

- `scripts/phase4/phase4_stage1_planning.py`

## Done Standard

Stage-01 is done only when Stage-02 can start without guessing:

- acceptance scope
- coverage logic
- gate rules
- execution-control posture
- visual-review honesty
