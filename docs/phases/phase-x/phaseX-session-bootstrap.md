# PhaseX Session Bootstrap

## Purpose

Use this document when a case does **not** start from greenfield product intent.

PhaseX is the sidecar family for:
- brownfield entry
- legacy modernization
- technical refactoring
- local change-on-existing-codebase
- migration-oriented preparation

It is **not** the default Phase-5 after Phase-4.
It is the bridge used when an existing system must be understood, constrained, protected, and then handed into P1 or P3.

## Current Scope

Current runnable implementation scope is **Wave-1**.

Wave-1 supports:
- `wff-x-scan-code-baseline scan-code-baseline`
- `wff-x-scan-tech-health scan-tech-health`
- `wff-x-plan-test-protection plan-test-protection`
- `wff-x-intake-target-driver target-driver-intake` as the `target-driver` profile

Wave-2 is now open as a v1.4 staged package-expansion line. The first tranche is baseline completion:

- `wff-x-scan-db-baseline scan-db-baseline`
- `wff-x-scan-biz-arch scan-biz-arch`

Wave-2 tranche order:

1. `wff-x-scan-db-baseline / wff-x-scan-biz-arch` baseline completion
2. `wff-x-design-target-arch / wff-x-intake-target-driver` target architecture and GAP / change decomposition
3. `wff-x-plan-refactor / wff-x-plan-migration` refactor and migration strategy

`outer-boundary concern` is not a standalone v1.4 target. Its useful outer-boundary / validation concerns are folded into `wff-x-design-target-arch` unless later case pressure proves a narrower separate slice.

Output-contract alignment:

- `wff-x-scan-code-baseline / wff-x-scan-db-baseline` primarily align to P2 and may provide only limited P3 seed material.
- `wff-x-scan-biz-arch` primarily aligns to P1 and provides secondary P2 consumption material.

## When to Enter PhaseX

Enter PhaseX when:
- there is already a live or legacy codebase
- the user wants refactoring, modernization, migration, or takeover work
- the next action depends on understanding current structure first
- a local change request must preserve compatibility with existing modules or APIs

Do **not** enter PhaseX when:
- the case is genuinely greenfield and should start from Phase-1
- the user already has a converged P1/P2 package and is simply asking for fresh implementation
- the task is a narrow bugfix that does not require brownfield baseline discovery

## Repo-Level First Read

Read in this order:

1. `docs/current-project-consensus.md`
2. `docs/current-canonical-reference-map-v0.1.md`
3. `docs/phases/phase-x/phaseX-brownfield-and-refactoring-stage-package-v0.md`
4. `docs/phases/phase-x/phaseX-wave1-implementation-plan-v0.1.md`
5. `docs/source-registers/phaseX-source-library-seed-v0.1.md`
6. `docs/phases/phase-x/phaseX-wave1-profile-decision-tree-v0.1.md`
7. `docs/phases/phase-x/phaseX-wave1-self-audit-guide-v0.1.md`
8. `reference-packages/phasex-brownfield-refactoring/README.md`

## Official Entry

Current official repo entry for runnable Wave-1:

- `skills/wff-x/`
- `scripts/phasex/scaffold_phasex_case.py`
- `scripts/phasex/validate_phasex_case.py`

## Official Working Root

Use the case-first local artifact layout:

- `tmp/local-artifacts/<case-name>/phase-x/`

Keep generated brownfield outputs there rather than mixing them into `reference-packages/` or repository validation fixtures.

## Refactoring Method Backbone

When the profile is `technical-refactor`, do not treat PhaseX as repository summarization only.

Use the extracted refactoring bundle as the active method backbone:

- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/index-map.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/stage-guidance-draft.md`

Minimum active cards:

- behavior-preservation boundary
- two hats
- self-testing tests and fast feedback
- small steps that keep the system working
- Branch by Abstraction for long-running replacements

## Wave-1 Profiles

### `assessment-only`

Use when the immediate goal is:
- understand the codebase
- score current health
- decide whether further work is justified

Expected skill path:
- `wff-x-scan-code-baseline -> wff-x-scan-tech-health`

Typical exit:
- human decision
- or continue to `technical-refactor`

### `technical-refactor`

Use when:
- business behavior is intended to remain broadly stable
- refactoring / tech debt / testability / operability are the main drivers

Expected skill path:
- `wff-x-scan-code-baseline -> wff-x-scan-tech-health -> wff-x-plan-test-protection`

Typical exit:
- direct handoff to Phase-3 as brownfield implementation work

### `target-driver`

Use when:
- an existing system needs a bounded change
- the change should preserve brownfield compatibility constraints
- the change may need to re-enter Phase-1 in constrained mode

Expected skill path:
- `wff-x-scan-code-baseline (local scope) -> wff-x-intake-target-driver`

Typical exit:
- re-enter Phase-1 with brownfield constraints
- or direct handoff to Phase-3 if it is clearly technical-only

## Core Boundary Rules

- PhaseX is **artifact-first**, not freeform analysis.
- PhaseX must preserve current-state truth and compatibility constraints explicitly.
- PhaseX must not silently upgrade “partial understanding” into full architecture certainty.
- Wave-1 should stay narrow; do not reopen the full 10-skill design unless a real blocker forces it.

## v1.3.10 Control Boundary

Use PhaseX Wave-1 as:

> Workflow shell + Agentic brownfield core + Evidence bridge.

- Workflow controls profile selection, stage order, required outputs, and scaffold / validation mechanics.
- Agentic controls codebase understanding, risk interpretation, safety-net strategy, and downstream route judgment.
- Evidence caps claims through code references, commands, tests, unknowns, confidence, and review-bound items.

The validator may require reviewable surfaces such as `codebase_truth_packet`, `risk_to_action_map`, `safety_net_strategy`, and `brownfield_handoff_packet`. It must not decide whether those judgments are correct.

## Output Expectations

Wave-1 outputs should answer:
- what exists now
- where the technical risk is
- what must be protected before change
- whether the next move is `back to P1` or `forward to P3`
- what is observed code truth, what is Agentic inference, and what remains unknown
- which evidence ceiling limits any readiness or compatibility claim

Wave-2 first-tranche outputs should answer:
- what data architecture exists now
- what business semantics exist now
- which baseline facts are P2 constraints
- which business facts should re-enter P1
- which P3 hints are seed material only

## Downstream Interface

### Toward Phase-1

PhaseX should pass:
- change-point statement
- affected modules
- impacted surfaces
- acceptance criteria anchors
- recommended route
- brownfield non-goals
- compatibility constraints
- brownfield invariants
- `third-party-dependency-manifest` when the change touches external APIs / SaaS / IdP / data providers

### Toward Phase-3

PhaseX should pass:
- current module boundaries
- health hotspots
- safety-net priorities
- brownfield guardrails that implementation must preserve

### Toward P2 Stage-02.5

If `wff-x-scan-code-baseline` or `wff-x-intake-target-driver` identifies third-party dependency change, preserve:

- `third_party_dependency_scan` from `wff-x-scan-code-baseline`
- `third-party-dependency-manifest` from `wff-x-intake-target-driver`
- any `compatibility_requirement` tied to brownfield external integrations

## One-Line Summary

PhaseX Wave-1 is the minimum bridge that lets an existing system enter the P1-P4 world without pretending it started from a blank page.
