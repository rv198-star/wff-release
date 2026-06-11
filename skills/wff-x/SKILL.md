---
name: wff-x
description: Use when the case starts from an existing codebase or legacy system and needs code-backed assessment before re-entering Phase-1, Phase-2, or Phase-3.
---

# PhaseX Brownfield Orchestrator

## Overview

This is the official existing-system entry skill. Use it when a live, legacy, or code-backed system must be understood before the main lifecycle can continue honestly.

PhaseX is not a default phase after Phase-4. It is a sidecar route for brownfield takeover, modernization, refactoring, migration, or bounded change.

## Product Boundary

PX is a code-backed existing-system assessment. Related documents are supporting evidence, but standalone documents are not enough; standalone PRDs, diagrams, test reports, API notes, DB notes, or incident records do not replace repository/runtime/system facts.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed PhaseX outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, env vars, and protocol keywords in their canonical form.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- the case starts from an existing codebase, live system, legacy system, or constrained change on top of one
- current structure, compatibility constraints, risks, and safety nets must be made explicit
- the next honest route may be P1, P2, P3, or protect-first

Do not use when:
- the case is genuinely greenfield
- the input is only a standalone document without code/system context
- the user already has an accepted P1/P2 package and simply wants implementation
- the task is a tiny local fix with no brownfield discovery need

## Core Rules

1. Separate observed facts, inferred semantics, unknowns, conflicts, and review-bound items.
2. Preserve legacy behavior and compatibility constraints unless the user supplies a clear replacement decision.
3. Build safety-net expectations before recommending risky change.
4. Do not turn PX handoff cards into P3 implementation action cards; PX handoff cards are not P3 implementation ActionCards.
5. Do not ask P1 to judge architecture, database, code, or implementation plan.
6. Do not ask P2 to replace P1 demand truth with technical findings.
7. Cap claims by code evidence, runnable checks, missing owner confirmation, and environment limits.

## Required Inputs

Read first:
- `docs/phases/phase-x/phaseX-session-bootstrap.md`
- `docs/phases/phase-x/phaseX-wave1-implementation-plan-v0.1.md`
- `docs/phases/phase-x/phaseX-wave1-profile-decision-tree-v0.1.md`
- `reference-packages/phasex-brownfield-refactoring/README.md`
- the existing system root

## Entrypoints

Scaffold a fresh PhaseX case:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir <case-phasex-root> \
  --profile <assessment-only|technical-refactor|target-driver> \
  --version <version-label>
```

Validate the case root:

```bash
python3 scripts/phasex/validate_phasex_case.py \
  --output-dir <case-phasex-root>
```

Extract mainline re-entry packets when target-driver output is ready:

```bash
python3 scripts/phasex/extract_mainline_reentry_packets.py \
  --target-driver <case-phasex-root>/wff-x-intake-target-driver.md \
  --output-dir <handoff-output-dir>
```

## Profiles

- `assessment-only`: understand the system, score health, and exit to a decision point.
- `technical-refactor`: preserve broad behavior, identify hotspots, and plan the minimum safety net.
- `target-driver`: package a bounded change as PX handoff cards plus constrained P1/P2/P3 re-entry material.

Wave-2 probes may use `wff-x-scan-code-baseline / wff-x-scan-db-baseline` and
`wff-x-scan-biz-arch` to separate code, data, and business architecture facts.
Keep outer-boundary concerns explicit and do not treat standalone documents as
system truth without code-backed assessment.

Choose exactly one profile for the case root. If evidence shows the chosen profile is no longer honest, stop and re-plan.

## Mainline Re-entry Surface

For `target-driver`, produce:
- PX Handoff Cards
- PX-to-P1 existing-system-change packet
- PX-to-P2 existing-system-architecture-change packet

`wff-x-intake-target-driver` is the first-version aggregation point for these
handoff cards and re-entry packets.

Recommended routes:
- `return-to-P1`: demand, business target, workflow, or acceptance truth needs P1 convergence
- `enter-P2`: architecture, data, interface, deployment, performance, or compatibility pressure needs P2 judgment
- `protect-first`: safety-net evidence is too thin for honest change
- `direct-to-P3`: narrow technical work with clear behavior-preservation boundary and protection evidence
- `decision-required`: source conflict, missing owner, compliance, cost, or destructive replacement risk needs a recorded decision

## Execution Sequence

1. Confirm the case genuinely needs brownfield truth.
2. Select the narrowest honest profile.
3. Scaffold a fresh PhaseX case root.
4. Author the generated files from code-backed evidence.
5. Preserve observed / inferred / unknown / conflict labels.
6. Validate the case root.
7. If target-driver is active, extract P1/P2 re-entry packets and state the recommended route.

## Completion Standard

Stop with one of these states:
- `assessment-complete`
- `protect-first`
- `return-to-P1`
- `enter-P2`
- `direct-to-P3`
- `decision-required`
- `blocked`

Do not let PhaseX pretend an existing system is greenfield, and do not route risky brownfield change forward without visible safety-net and compatibility boundaries.
