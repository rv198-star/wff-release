---
name: wff-arch
description: Use when running or rerunning a real case through the official Phase-2 design and architecture flow from an accepted Phase-1 handoff.
---

# Phase-2 Design / Architecture Orchestrator

## Overview

This is the official Phase-2 entry skill. It turns a Phase-1 handoff into a bounded architecture package, not freewritten design prose.

Phase-2 owns architecture translation, source absorption, risk posture, data/API contracts, and the implementation-facing handoff. It must not rediscover product truth or make Phase-3 invent missing architecture.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-2 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, table names, env vars, and protocol keywords in their canonical form.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- the user wants to start Phase-2 from an accepted Phase-1 PRD or handoff
- the output must feed implementation planning or an Engineering Spec Pack
- an existing Phase-2 case needs rerun, hardening, or closure
- an existing-system architecture-change intake packet must be consumed alongside the Phase-1 authority input

Do not use when:
- Phase-1 product truth is still unresolved
- the task is only a small edit to one design document
- the task is code implementation, validation, or deployment execution

## Core Rules

1. Consume Phase-1 truth as upstream authority. Do not invent business/product direction inside Phase-2.
2. Design for first delivery and downstream implementation leverage. Avoid both minimal notes and speculative enterprise architecture.
3. Keep trace absorption explicit from Phase-1 trace units into Stage outputs, ESP sections, contracts, risks, and handoff surfaces.
4. Use bounded agentic design judgment for boundary choices, module decomposition, data ownership, contracts, dependencies, rollout posture, and trade-offs.
5. Record unresolved architecture truth as `review-bound` with owner, validation path, and downstream impact.
6. Treat machine-pass as structural evidence only. Architecture value, handoff usefulness, and claim ceiling still require judgment.
7. Preserve the development / pre-production boundary. Do not imply production approval, owner sign-off, or UAT without supplied external evidence.

## Required Inputs

Read first:
- `docs/phases/phase-2/phase-2-session-bootstrap.md`
- `docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md`
- `reference-packages/phase2-design-architecture/README.md`
- the Phase-1 PRD sections `Phase-2 Design Input Contract` and `Fine-Grained Trace Registry`

For existing-system architecture changes, also consume the optional `P2 Existing-System Architecture Change Intake Packet`. It supplies current-system architecture facts and constraints; it does not replace Phase-1 demand truth.

P1 PRD and `Phase-2 Design Input Contract` remain the authority input. The
`existing-system-architecture-change` side branch is not a new Phase-2 flow; it
adds bounded `Architecture Change Impact Triage` and `Architecture Change Design`
before normal Stage expression. Agentic owns the architecture judgment.
Workflow only controls side-branch order and claim guards.

Existing-system acceptance markers:
- `AC-1`: additive or compatible change with bounded evidence can continue.
- `AC-2`: migration, rollback, or compatibility pressure must be explicit.
- `AC-3`: destructive or contract-breaking risk routes to `architecture-decision-required`.
- `AC-4`: missing critical evidence routes to `blocked`.

AC-3 / AC-4 must not be promoted as ready-for-P3. Owner confirmation is optional evidence. additive compatibility is the default safety posture for this side branch, not a global Phase-2 principle; destructive replacement requires an explicit architecture decision.

## Phase Review And Value-Bearing Closure

Expose a Phase Review Breakpoint before promoting to Phase-3. Reviewers may approve (`批准`), require modification (`要求修改`), require return (`要求返回`), or provide intervention input (`提供干预输入`); the decision must preserve architecture and delivery judgment, not only Stage shape or wrapper pass.

P2 closure is value-bearing only when architecture value, delivery value, implementation-facing handoff value, protected surfaces, and downstream consumer paths remain explicit. P2 must preserve project language for P3; P3 synthesizes project implementation conventions from source-backed P2 outputs and `tech-stack-decision.yaml`, not from case-name heuristics.

## P2 Event Model Direct Driver

When the source and P1/P2 contracts imply events, P2 owns the event model before
P3 implementation. Use `p2-architecture-event-model-driver.v1` to preserve
`domain_event_vocabulary`, `domain_event_model_catalog`, producer / consumer /
trigger / payload / timing / idempotency, event_versioning_and_schema_posture,
`p3_event_handoff`, and `review_bound_event_gaps`. Workflow keeps order and
handoff placement; Agentic owns architecture/event-model judgment; Templates /
TVG shape depth only; Evidence / Gates prove traceability and cap claims. Schema
checks must not generate architecture judgment. Do not create a default heavy
event artifact. P3 consumes event models; P3 does not invent complete event
architecture when P2 is silent.

## Thinking Value-Gain Generation Strategy

Use TVG after the Phase-1 full-use result proves useful enough to consume, not to make architecture more elaborate by default. Default `--thinking-value-gain-mode`
may stay off unless depth is needed; when enabled, expose
`--thinking-value-gain-output-profile` as `insight_dense | balanced | coverage_rich`.
Preserve Thinking Thickness and Value Density around operation flow / sequence / state / replay source material. If P1 full-use produces inflated or lower-signal truth, return or cap the claim instead of deepening architecture around it.

## Entrypoints

Fresh Phase-2 generation:

```bash
python3 scripts/phase2/run_phase2_fresh_generation.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <version-label> \
  --run-wrapper
```

Existing-system architecture-change intake:

```bash
python3 scripts/phase2/run_phase2_existing_system_intake.py \
  --phase1-prd <phase1-prd.md> \
  --existing-system-architecture-change-intake <intake.md> \
  --output-dir <case-phase2-root> \
  --version <version-label> \
  --run-wrapper
```

Manual or remediation-first scaffold:

```bash
python3 scripts/phase2/scaffold_phase2_case.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <version-label>
```

Use `scripts/phase2/phase2_quality_check.py` only for focused quality checks over supplied Stage artifacts.

## Execution Sequence

1. Confirm the Phase-1 handoff and choose a fresh Phase-2 case root.
2. Read the Phase-2 input contract and build a top-down absorption plan.
3. Run the fresh generation entrypoint, or scaffold only when manual remediation is intentional.
4. If an existing-system architecture-change packet exists, classify impact, compatibility posture, migration pressure, rollback needs, and decision gates.
5. Generate or refresh Stage-01 through Stage-04 using the official stage packs.
6. Run wrapper closure so the trace registry, execution report, Engineering Spec Pack, and Phase-3 implementation entry are emitted together.
7. Review architecture value and downstream handoff readiness before promoting to Phase-3.

## Required Output Set

A valid Phase-2 package preserves:
- Stage-01 architecture definition
- Stage-02 domain/module decomposition
- Stage-02.5 third-party integration design when triggered
- Stage-03 data/interface design
- Stage-04 convergence and delivery plan
- Phase-2 execution report
- Engineering Spec Pack
- Phase-3 implementation entry
- traceability registry evidence
- quality check report
- explicit review-bound and claim-ceiling statements

## Quality Floor

Phase-2 is complete only when:
- every material Phase-1 trace unit is absorbed or explicitly review-bound
- architecture decisions explain why the chosen boundary is useful for delivery
- API, data, interaction, risk, and rollout surfaces are implementation-facing
- ESP is self-contained enough for Phase-3 to start without guessing
- high-risk operations carry source obligations and implementation-depth obligations
- unresolved items have owners, validation paths, and downstream impact

## Completion Standard

Stop with one of these states:
- `ready-for-phase3`: architecture and handoff are sufficient for implementation
- `ready-with-review-bound-items`: implementation may proceed only with named ceilings
- `return-to-phase1`: missing product truth blocks honest architecture
- `blocked`: required source, dependency, or decision evidence is absent

Do not call Phase-2 complete when the package only has template shape, pointer-only handoff, or generic architecture language.
