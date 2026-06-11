---
name: wff-x
description: Use when the case starts from an existing codebase or legacy system and you need the official PhaseX Wave-1 brownfield entry path for baseline extraction, health assessment, safety-net planning, PX Handoff Cards, or target-driver intake packaging before re-entering Phase-1, Phase-2, or Phase-3.
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

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.

## When to Use

Use when:
- the case starts from an existing codebase
- the user wants refactoring, legacy takeover, modernization, or bounded change on a live system
- you need baseline extraction, health scoring, safety-net planning, or a target-driver intake package

Do not use when:
- the case is genuinely greenfield
- the user already has a converged P1/P2 package and simply wants implementation
- the task is a tiny local fix with no brownfield discovery need

## Current Scope

Current runnable PhaseX implementation is **Wave-1**, not the full historical 10-skill blueprint.
Wave-1 `v0` remains the current default entry path.
Wave-2 is now open as a staged package-expansion line for v1.4 planning and implementation, but it does not replace Wave-1 scaffolding or validation.

Wave-1 supports:
- `wff-x-scan-code-baseline scan-code-baseline`
- `wff-x-scan-tech-health scan-tech-health`
- `wff-x-plan-test-protection plan-test-protection`
- `wff-x-intake-target-driver target-driver-intake` as the `target-driver` profile

Wave-2 first tranche adds authored package surfaces for:
- `wff-x-scan-db-baseline scan-db-baseline`
- `wff-x-scan-biz-arch scan-biz-arch`

Output-contract alignment:
- `wff-x-scan-code-baseline / wff-x-scan-db-baseline` primarily align to P2 and may provide only limited P3 seed material.
- `wff-x-scan-biz-arch` primarily aligns to P1 and provides secondary P2 consumption material.
- `wff-x-intake-target-driver` is the first-version aggregation point for PX Handoff Cards and mainline re-entry packets.

Later Wave-2 tranches are expected to cover `wff-x-design-target-arch / wff-x-plan-refactor / wff-x-plan-migration`.
`outer-boundary concern` is not a standalone v1.4 target; its useful outer-boundary / validation concerns are folded into `wff-x-design-target-arch`.

## Mainline Re-entry Surface

PhaseX does not replace P1-P4. PhaseX prepares existing-system truth so the mainline can continue without pretending the case is greenfield.

For `target-driver`, `wff-x-intake-target-driver` must produce:

- `PX Handoff Cards`
- `PX-to-P1 existing-system-change packet`
- `PX-to-P2 existing-system-architecture-change packet`

`PX Handoff Cards` are not P3 implementation ActionCards. They are takeover cards for existing-system work. Each card names the current-state facts, target driver, gap, evidence, inferred semantics, unknowns, compatibility constraints, protected legacy behaviors, risk notes, recommended route, required prework, and claim ceiling.

Recommended routes:

- `return-to-P1`: product demand, business target, user workflow, acceptance pressure, or requirement truth needs P1 convergence.
- `enter-P2`: architecture, data, interface, integration, deployment, performance, or compatibility pressure needs P2 architecture judgment.
- `protect-first`: safety-net evidence is too thin for honest brownfield change.
- `direct-to-P3`: narrow technical work only, with clear behavior-preservation boundary and protection evidence.
- `decision-required`: source conflict, missing owner, compliance, cost, or destructive replacement risk needs an explicit recorded decision. Owner confirmation is optional evidence, not a lifecycle prerequisite; when no owner is available, keep the fact review-bound and choose the conservative compatibility-preserving path.

The `PX-to-P1 existing-system-change packet` must use the P1 `packet_subtype: existing-system-change` contract. It is the demand-change input for P1 and must not ask P1 to judge architecture, database, code, or implementation plan.

The `PX-to-P2 existing-system-architecture-change packet` must use the P2 `packet_subtype: existing-system-architecture-change` contract. It is a P2 sidecar and must not replace the P1 PRD or `Phase-2 Design Input Contract`.

## v1.3.10 Control Boundary

PhaseX Wave-1 follows the same top project boundary:

- Workflow controls profile selection, stage order, required outputs, scaffold shape, and minimum validation.
- Agentic controls brownfield understanding and judgment: codebase truth interpretation, risk meaning, safety-net strategy, and downstream route rationale.
- Evidence caps claims through code references, commands, tests, unknowns, confidence, and review-bound items.

Validation confirms reviewable surfaces exist. It must not decide whether the brownfield interpretation, refactor judgment, or route decision is true.

## Read First

- `docs/phases/phase-x/phaseX-session-bootstrap.md`
- `docs/phases/phase-x/phaseX-wave1-implementation-plan-v0.1.md`
- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `docs/phases/phase-x/phaseX-wave1-profile-decision-tree-v0.1.md`
- `reference-packages/phasex-brownfield-refactoring/README.md`

## Official Entrypoint

Start by scaffolding a fresh PhaseX case root:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir <case-phasex-root> \
  --profile <assessment-only|technical-refactor|target-driver> \
  --version <vN>
```

Then validate the case root state:

```bash
python3 scripts/phasex/validate_phasex_case.py \
  --output-dir <case-phasex-root>
```

When `target-driver` is authored and the downstream mainline needs separate intake files, extract the P1/P2 re-entry packets:

```bash
python3 scripts/phasex/extract_mainline_reentry_packets.py \
  --target-driver <case-phasex-root>/wff-x-intake-target-driver.md \
  --output-dir <handoff-packet-output-dir>
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
- the real need is already beyond Wave-1 and requires broader PhaseX skills such as `wff-x-scan-db-baseline / wff-x-scan-biz-arch / wff-x-design-target-arch / wff-x-plan-refactor / wff-x-plan-migration`

### 2. Select exactly one Wave-1 profile

Pick the narrowest honest profile and keep it stable for the case root.

- `assessment-only`: understand the system, score technical health, then exit to an explicit decision point; human confirmation may strengthen evidence but is not required when no owner is available
- `technical-refactor`: preserve broad behavior, identify hotspots, then build the minimum safety net before implementation
- `target-driver`: package a bounded change as PX Handoff Cards plus constrained P1/P2/P3 re-entry material

If the repository evidence shows the selected profile is no longer honest, stop and re-plan instead of force-fitting the current lane.

### 3. Scaffold before authoring

Always scaffold the case root first, then author inside the generated files:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir <case-phasex-root> \
  --profile <assessment-only|technical-refactor|target-driver> \
  --version <vN>
```

Use the manifest as the execution contract for:

- selected profile
- authoring order
- boundary rules
- required output set

### 4. Author in profile order, not in freeform order

Profile order is fixed for Wave-1:

- `assessment-only`: author `wff-x-scan-code-baseline`, then `wff-x-scan-tech-health`
- `technical-refactor`: author `wff-x-scan-code-baseline`, then `wff-x-scan-tech-health`, then `wff-x-plan-test-protection`
- `target-driver`: author `wff-x-scan-code-baseline`, then `wff-x-intake-target-driver`

Per-output intent:

- `wff-x-scan-code-baseline`: establish AS-IS structure, codebase truth packet, uncertainty, runnability posture, and `third_party_dependency_scan` when outbound vendor/API/IdP signals exist
- `wff-x-scan-tech-health`: quantify health as supporting evidence, then make evidence-backed brownfield risk / readiness judgment
- `wff-x-plan-test-protection`: define the minimum safety-net strategy and go / no-go protection decision that makes behavior-preserving change honest
- `wff-x-intake-target-driver`: produce PX Handoff Cards, the PX-to-P1 existing-system-change packet, the PX-to-P2 architecture-change sidecar packet, and constrained Phase-3 notes when direct technical work is honest

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

- `assessment-only` exits to an explicit decision point, not directly to broad implementation. If no human owner is available, record `owner_unavailable`, preserve the claim ceiling, and continue only through a conservative route such as `protect-first`, `return-to-P1`, or `enter-P2`.
- `technical-refactor` may hand off to brownfield Phase-3 only after `wff-x-plan-test-protection` makes behavior-preservation guardrails explicit
- `target-driver` may return to Phase-1, enter Phase-2 through a sidecar, go direct to brownfield Phase-3, or protect first only when the PX Handoff Cards and re-entry packets make that route explicit

## Profile Rule

- `assessment-only`: `wff-x-scan-code-baseline -> wff-x-scan-tech-health`
- `technical-refactor`: `wff-x-scan-code-baseline -> wff-x-scan-tech-health -> wff-x-plan-test-protection`
- `target-driver`: `wff-x-scan-code-baseline -> wff-x-intake-target-driver`

If the case does not fit any of these honestly, do not fake a Wave-1 fit.
Record that a broader PhaseX lane is required.

## Required Output Set

A valid Wave-1 case should preserve:
- `phasex-wave1-manifest.md`
- `wff-x-scan-code-baseline.md` when selected
- `wff-x-scan-tech-health.md` when selected
- `wff-x-plan-test-protection.md` when selected
- `wff-x-intake-target-driver.md` when selected

When `target-driver` is selected, the authored package must keep the constrained re-entry spine explicit:
- `px_handoff_cards`
- `px_to_p1_change_source_packet`
- `px_to_p2_architecture_change_intake_packet`
- `affected_modules`
- `impacted_surfaces`
- `acceptance_criteria`
- `recommended_route`
- `brownfield_non_goals`
- `third-party-dependency-manifest` when external dependencies are touched

When `wff-x-scan-code-baseline` sees outbound vendor/API/IdP signals, keep a structured `third_party_dependency_scan` instead of burying it in prose.

## Stop Conditions

Stop Wave-1 and re-plan if any of these become true:

- the case now requires database-first truth, business-process reconstruction, target architecture design, migration planning, or multi-system entity mapping
- `technical-refactor` cannot define a credible behavior-preservation boundary or minimum safety net
- `target-driver` cannot name affected modules, impacted surfaces, acceptance anchors, PX Handoff Cards, mainline re-entry packets, or the honest downstream route
- the evidence is too thin and uncertainty would dominate the output

## Core Boundary

- PhaseX does not replace P1-P4.
- PhaseX should preserve brownfield truth and constraints explicitly.
- Wave-1 should remain minimal and useful; do not inflate it into the whole PhaseX blueprint without case pressure.
- Wave-2 package surfaces do not make PhaseX a default Phase-5 or a production-modernization claim.
- Do not turn Wave-1 into a table-completion exercise. If the output has surfaces but no code evidence, Agentic judgment, route rationale, or claim ceiling, treat it as thin.
