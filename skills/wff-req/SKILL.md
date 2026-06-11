---
name: wff-req
description: Use when running a real product case through Phase-1 to produce an official PRD, evidence memo, gates, and handoff package.
---

# Phase-1 Product Requirements Orchestrator

## Overview

This is the official Phase-1 entry skill. It turns source material into a reviewed product requirements package, not a manually filled template.

Phase-1 owns product truth, business pressure, scope boundaries, acceptance intent, and the handoff contract for design.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-1 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, env vars, and protocol keywords in their canonical form.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- the user wants to turn source material into a PRD or requirements handoff
- downstream design, architecture, implementation, or validation will depend on the output
- the case enters through a `P1 source input packet` from `wff-req-chat`, PhaseX, or a human reviewer

Do not use when:
- the task is only editing one existing PRD section
- the user needs architecture, implementation, or validation instead
- the input is not ready and should return to intake

## Core Rules

1. Preserve source authority. Do not invent missing product truth to make the PRD look complete.
2. Keep business facts, inferences, unknowns, review-bound gaps, non-goals, and assumptions visibly separate.
3. Build top-down structure: epic, use case, requirement, acceptance criteria, and handoff trace.
4. Acceptance criteria must be actionable and should use Given / When / Then where it improves implementation clarity.
5. Existing-system change packets supply current-state context and demand pressure; they do not give P1 authority to decide architecture, database, code, or implementation plan.
6. Product outputs are evidence-capped. Missing owner sign-off, UAT, market validation, or production approval must remain explicit when absent.

## Required Inputs

Read first:
- `docs/phases/phase-1/phase-1-session-bootstrap.md`
- `reference-packages/phase1-product-requirements/README.md`
- `docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- source material or `P1 source input packet`

When the input packet has `packet_subtype: existing-system-change`, also read:
- target change
- affected users/workflows
- legacy behaviors to preserve
- unknowns and source conflicts
- demand clarification addendum when present

When the input is a `P1 source input packet`, consume its `Admission Decision`,
`Open Truth Gaps`, and `Reviewer Concerns` before generation. P1 must preserve review-bound gaps and must not invent missing product truth.

## Demand Change Evaluation

For `existing-system-change` packets, run a light Demand Change Evaluation
before normal PRD convergence:
- `Change Intent`: target change and non-goals.
- `Business Impact`: business pressure, value, risk, or urgency.
- `Affected Users / Workflows`: impacted user groups and workflow slices.
- `Proceed Decision`: `proceed-to-P1`, `return-to-intake`, or `review-bound-provisional`.

P1 evaluates demand clarity and business pressure only; it must not judge architecture, database, code, or implementation plan.

## P1 PRD Claim Authority Surface

The compiled claim authority surface is `.phase1-evidence/<prd-stem>.claim-surface.json`.
PRD Markdown is a rendered human-review view. Any claim-control sidecar must prefer the compiled claim surface; rendered PRD compatibility fallback may be
used for old artifacts but must not become source authority.

## Phase Review And Value-Bearing Closure

Expose a Phase Review Breakpoint before promoting to Phase-2. Reviewers may approve (`批准`), require modification (`要求修改`), require return (`要求返回`), or provide intervention input (`提供干预输入`); the decision must preserve product-value and source-truth judgment, not only template completeness.

P1 closure is value-bearing only when product value, business pressure, user value, pain strength, narrowest valuable wedge, and source truth confidence are visible. P1 protected surfaces must remain visible to downstream phases; moving diagnostics is allowed only when the consumer path and resolver coverage stay explicit.

## Thinking Value-Gain Full-Use Generation Strategy

Use TVG across all major P1 artifact units as a value-preservation strategy, not as a length-expansion rule. Default to `coverage_rich` when the source is broad,
but keep Thinking Thickness and Value Density explicit: deepen only when it
improves grounded product judgment, source truth, acceptance pressure, or
handoff usefulness. Preserve `business_value_signal_registry` evidence and treat
over-design regression as a real failure mode.

## Entrypoint

Run the official full-trial path:

```bash
python3 scripts/phase1/run_phase1_full_trial.py \
  --source <phase1-input.md> \
  --output-dir <phase1-output-dir> \
  --version <version-label> \
  --profile <review-bound-starter-pack|implementation-ready-prd> \
  --depth-mode <baseline|creative>
```

Use `baseline` by default. Use `creative` only when the user explicitly asks for broader product exploration.

Use `scripts/phase1/run_phase1_convergence.py` for convergence/remediation over generated Phase-1 outputs.

## Execution Sequence

1. Confirm source readiness and admission state.
2. Separate confirmed facts, inferred meaning, review-bound gaps, and non-goals.
3. Build the semantic authoring spine for product meaning before rendering PRD prose.
4. Generate deep Stage artifacts through the official runtime.
5. Assemble and converge the PRD.
6. Run gates and preserve execution evidence.
7. Emit the Phase-2 design input contract and fine-grained trace registry.
8. Present the review breakpoint and final claim ceiling.

## Required Output Set

A valid Phase-1 package preserves:
- stage outputs
- PRD
- evidence memo
- execution report
- gate JSON reports
- source/claim surface
- Phase-2 design input contract
- fine-grained trace registry
- explicit review-bound and claim-ceiling statements

## Quality Floor

Phase-1 is complete only when:
- the product problem, target users, workflows, and success pressure are understandable
- requirements and acceptance criteria are specific enough for design
- review-bound gaps are not hidden as confident requirements
- existing-system facts stay labeled as current-state context unless confirmed as target behavior
- downstream Phase-2 can consume traceable demand truth without inventing scope

## Completion Standard

Stop with one of these states:
- `ready-for-phase2`: product truth is sufficient for architecture
- `ready-with-review-bound-items`: Phase-2 may proceed only with named ceilings
- `return-to-intake`: demand is too unclear for honest PRD generation
- `blocked`: required source or decision evidence is absent

Do not call Phase-1 complete when the PRD is only polished prose without traceable source authority and acceptance pressure.
