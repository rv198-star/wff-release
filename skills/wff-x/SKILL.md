---
name: wff-x
description: Use when the case starts from an existing codebase or legacy system and you need the official PhaseX Wave-1 brownfield entry path for baseline extraction, health assessment, safety-net planning, or partial gap packaging before re-entering Phase-1 or Phase-3.
---

# PhaseX Brownfield Orchestrator

## Overview

This is the official Wave-1 entry skill for the PhaseX brownfield / legacy / refactoring track.

PhaseX is **not** a default linear phase after Phase-4.
It is the sidecar phase flow used when an existing system must be understood and constrained before the main lifecycle can continue honestly.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write brownfield baseline notes, health assessments, safety-net plans, gap analyses, and downstream handoff text in Chinese
- preserve code, file paths, commands, API/schema field names, trace ids, artifact ids, env vars, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only PhaseX artifacts or assessment conclusions unless the user explicitly requests English

## When to Use

Use when:
- the case starts from an existing codebase
- the user wants refactoring, legacy takeover, modernization, or bounded change on a live system
- you need baseline extraction, health scoring, safety-net planning, or a partial gap package

Do not use when:
- the case is genuinely greenfield
- the user already has a converged P1/P2 package and simply wants implementation
- the task is a tiny local fix with no brownfield discovery need

## Current Scope

Current PhaseX implementation is **Wave-1**, not the full 10-skill blueprint.
Wave-1 `v0` is the current frozen baseline.
Do not widen scope, rename bridge fields, or invent a Wave-2 lane unless a real case proves Wave-1 is insufficient.

Wave-1 supports:
- `PX-SK-01 codebase-baseline-extraction`
- `PX-SK-04 technical-health-assessment`
- `PX-SK-07 safety-net-test-construction`
- `PX-SK-06 gap-analysis-and-change-decomposition` in `partial` mode

## v1.3.10 Control Boundary

PhaseX Wave-1 follows the same top project boundary:

- Workflow controls profile selection, stage order, required outputs, scaffold shape, and minimum validation.
- Agentic controls brownfield understanding and judgment: codebase truth interpretation, risk meaning, safety-net strategy, and downstream route rationale.
- Evidence caps claims through code references, commands, tests, unknowns, confidence, and review-bound items.

Validation confirms reviewable surfaces exist. It must not decide whether the brownfield interpretation, refactor judgment, or route decision is true.

## Read First

- `docs/phases/phase-x/phaseX-session-bootstrap.md`
- `docs/phases/phase-x/phaseX-wave1-implementation-plan-v0.1.md`
- `docs/internal/source-registers/phaseX-source-library-seed-v0.1.md`
- `docs/phases/phase-x/phaseX-wave1-profile-decision-tree-v0.1.md`
- `reference-packages/phasex-brownfield-refactoring/README.md`

## Official Entrypoint

Start by scaffolding a fresh PhaseX case root:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir <case-phasex-root> \
  --profile <assessment-only|technical-refactor|partial-change> \
  --version <vN>
```

Then validate the case root state:

```bash
python3 scripts/phasex/validate_phasex_case.py \
  --output-dir <case-phasex-root>
```

## Working Root

Use:

- `tmp/local-artifacts/<case-name>/phase-x/`

## Orchestration SOP

### 1. Confirm honest PhaseX fit

Enter PhaseX only if the next move depends on brownfield truth.

- existing codebase, legacy repo, live system, or constrained change on top of one
- refactor / modernization / takeover / bounded brownfield change
- current structure and compatibility constraints must be made explicit before P1 or P3

Reject Wave-1 fit if:

- the task is actually greenfield and should start in Phase-1
- the task is a tiny local fix with no discovery need
- the real need is already beyond Wave-1 and requires broader PhaseX skills such as `PX-SK-02 / 03 / 05 / 08 / 09 / 10`

### 2. Select exactly one Wave-1 profile

Pick the narrowest honest profile and keep it stable for the case root.

- `assessment-only`: understand the system, score technical health, then stop for a human decision
- `technical-refactor`: preserve broad behavior, identify hotspots, then build the minimum safety net before implementation
- `partial-change`: package a bounded change for constrained re-entry into P1 or direct brownfield P3

If the repository evidence shows the selected profile is no longer honest, stop and re-plan instead of force-fitting the current lane.

### 3. Scaffold before authoring

Always scaffold the case root first, then author inside the generated files:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir <case-phasex-root> \
  --profile <assessment-only|technical-refactor|partial-change> \
  --version <vN>
```

Use the manifest as the execution contract for:

- selected profile
- authoring order
- boundary rules
- required output set

### 4. Author in profile order, not in freeform order

Profile order is fixed for Wave-1:

- `assessment-only`: author `PX-SK-01`, then `PX-SK-04`
- `technical-refactor`: author `PX-SK-01`, then `PX-SK-04`, then `PX-SK-07`
- `partial-change`: author `PX-SK-01`, then `PX-SK-06 partial`

Per-output intent:

- `PX-SK-01`: establish AS-IS structure, codebase truth packet, uncertainty, runnability posture, and `third_party_dependency_scan` when outbound vendor/API/IdP signals exist
- `PX-SK-04`: quantify health as supporting evidence, then make evidence-backed brownfield risk / readiness judgment
- `PX-SK-07`: define the minimum safety-net strategy and go / no-go protection decision that makes behavior-preserving change honest
- `PX-SK-06 partial`: produce the constrained re-entry bridge and brownfield handoff package that P1 or P3 can consume

### 5. Validate after scaffold replacement and before exit

Run validation whenever authored stubs are replaced and once again before handing off downstream:

```bash
python3 scripts/phasex/validate_phasex_case.py \
  --output-dir <case-phasex-root>
```

Interpret results strictly:

- `scaffold-only`: authoring has not started or is incomplete
- `authored-invalid`: fields or bridge structure are still missing; do not hand off
- `authored-valid`: Wave-1 minimum is satisfied for the selected profile

Warnings are not a pass excuse. Read them and decide whether the case is drifting wider than the chosen profile.

### 6. Exit only through the declared downstream route

- `assessment-only` exits to a human decision, not directly to broad implementation
- `technical-refactor` may hand off to brownfield Phase-3 only after `PX-SK-07` makes behavior-preservation guardrails explicit
- `partial-change` may return to Phase-1 or go direct to brownfield Phase-3 only when the constrained re-entry spine is complete

## Profile Rule

- `assessment-only`: `PX-SK-01 -> PX-SK-04`
- `technical-refactor`: `PX-SK-01 -> PX-SK-04 -> PX-SK-07`
- `partial-change`: `PX-SK-01 -> PX-SK-06 partial`

If the case does not fit any of these honestly, do not fake a Wave-1 fit.
Record that a broader PhaseX lane is required.

## Required Output Set

A valid Wave-1 case should preserve:
- `phasex-wave1-manifest.md`
- `px-sk-01-codebase-baseline-extraction.md` when selected
- `px-sk-04-technical-health-assessment.md` when selected
- `px-sk-07-safety-net-test-construction.md` when selected
- `px-sk-06-gap-analysis-and-change-decomposition-partial.md` when selected

When `partial-change` is selected, the authored package must keep the constrained re-entry spine explicit:
- `affected_modules`
- `impacted_surfaces`
- `acceptance_criteria`
- `recommended_route`
- `brownfield_non_goals`
- `third-party-dependency-manifest` when external dependencies are touched

When `PX-SK-01` sees outbound vendor/API/IdP signals, keep a structured `third_party_dependency_scan` instead of burying it in prose.

## Stop Conditions

Stop Wave-1 and re-plan if any of these become true:

- the case now requires database-first truth, business-process reconstruction, target architecture design, migration planning, or multi-system entity mapping
- `technical-refactor` cannot define a credible behavior-preservation boundary or minimum safety net
- `partial-change` cannot name affected modules, impacted surfaces, acceptance anchors, or the honest downstream route
- the evidence is too thin and uncertainty would dominate the output

## Core Boundary

- PhaseX does not replace P1-P4.
- PhaseX should preserve brownfield truth and constraints explicitly.
- Wave-1 should remain minimal and useful; do not inflate it into the whole PhaseX blueprint without case pressure.
- Do not turn Wave-1 into a table-completion exercise. If the output has surfaces but no code evidence, Agentic judgment, route rationale, or claim ceiling, treat it as thin.
