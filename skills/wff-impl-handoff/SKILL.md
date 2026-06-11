---
name: wff-impl-handoff
description: Use when finalizing Phase-3 into a deployable handoff package after implementation and audits are green, including deploy runbook, acceptance summary, execution report, final trace registry, and delivery-ready verification.
---

# Phase-3 Delivery Handoff

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns the non-code finalization work at S04 after implementation is stable.

It is responsible for turning a green implementation into a reviewable, deployable, trace-complete delivery package.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-handoff/` for the capability contract, SOP, output template, and source cards.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write handoff summaries, deployment guidance, acceptance notes, rollback cautions, and operator instructions in Chinese
- preserve code, file paths, commands, API/schema field names, trace ids, artifact ids, env vars, image/tag names, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only delivery notes or handoff conclusions unless the user explicitly requests English

## Rules

- Do not claim Phase-3 complete before the delivery gate returns `delivery-ready`.
- Do not hide unresolved review/security findings inside prose summaries.
- The handoff package must preserve the frozen contract baseline and the final implementation evidence together.
- Deployment readiness must include rollback and observability posture, not only a build artifact.
- Do not overwrite existing real deployment assets with generic fallback scaffolds; generate baseline Docker/compose assets only when the case does not already provide them.
- Generated or preserved Docker delivery assets should satisfy a production minimum: startable runtime entrypoint, healthcheck, non-root runtime when feasible, and no hard-coded secrets.

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `phase3-quality-check.json`
- the case implementation gate outputs (build / lint / typecheck / coverage / replay)
- the case `code-review-metrics.json`
- the case `security-audit-checklist.json`
- the case OpenAPI diff report

## Required Outputs

- `deploy-runbook.md`
- `phase-3-acceptance-report.md`
- `phase-3-execution-report.md`
- `phase-3-trace-registry-final.json`
- final delivery gate report

## Primary Tool

- `scripts/phase3/phase3_delivery_gate.py`
- provide runtime smoke / started-service evidence to the delivery gate when slim profiles do not ship smoke helper scripts
- full-pack/source-tree support mode: delivery-handoff report generation is optional support tooling, not shipped in slim implementation profiles

## Completion Standard

This skill is done only when:
- deployment artifacts are present
- runtime smoke and started-service API smoke evidence are present for Docker-based delivery paths, or an explicit equivalent runtime-validation contract is preserved
- acceptance and execution reports are generated from current evidence
- acceptance and execution reports are written
- final trace registry is preserved
- the delivery gate returns `delivery-ready`
