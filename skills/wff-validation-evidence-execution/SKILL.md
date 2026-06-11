---
name: wff-validation-evidence-execution
description: Use when running Phase-4 Stage-02 from Stage-01 outputs and inherited Phase-3 evidence to produce explicit execution results, defect records, and review-bound visual/UI notes.
---

# Phase-4 Stage-02 Evidence Execution Defect Triage

## Scope

This skill owns Phase-4 Stage-02.

Its job is to execute the frozen acceptance model against real evidence and convert outcomes into reviewable records.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write execution notes, per-item outcome explanations, review-bound statements, and evidence summaries in Chinese
- preserve code, file paths, commands, test ids, API/schema field names, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only execution artifacts or result commentary unless the user explicitly requests English

## Required Inputs

Read:

- `docs/phases/phase-4/phase-4-skill-architecture-design-v0.1.md`
- the case Stage-01 acceptance catalog
- the case Stage-01 execution-control artifact
- the case Phase-3 worker-run evidence
- the case frontend worker packets and route files

## Stage-02 Rules

1. Functional items must be resolved from actual validation evidence.
2. Functional and `data-fidelity` items must read inherited Phase-3 runtime-truth artifacts before calling the result green.
3. If Phase-3 still reports mock dependency in core paths, mark the affected runtime-truth result `conditional-pass`, not `pass`.
4. Do not infer green from build success alone when functional targets are missing.
5. UI review may use route files plus linked packet evidence, and may also consume external/manual review evidence when it is explicitly supplied.
6. Screenshot/video/manual evidence may pass only when a real artifact exists.
7. Missing visual artifacts in a non-capture environment are not defects by themselves, but they must stay explicit.
8. Missing mandatory functional or data-fidelity evidence is blocking.
9. Critical-path sign-off is tracked separately from automated pass/fail so closure can stay honest without overloading execution status.

## Official Script

- `scripts/phase4/phase4_stage2_execution.py`

## Done Standard

Stage-02 is done only when every acceptance item has:

- a status
- an actual_result
- evidence paths or an explicit review-bound note
- defect / unresolved visibility where applicable
