---
name: wff-impl
description: Use when running or rerunning the official Phase-3 implementation flow from a completed Phase-2 handoff.
---

# Phase-3 Implementation Orchestrator

## Overview

This is the official Phase-3 entry skill. It turns the accepted Phase-2 handoff into runnable implementation, tests, runtime evidence, and delivery handoff.

Phase-3 is not ad hoc coding. It freezes contracts, generates failing tests, implements bounded work packages, verifies runtime behavior, and records claim ceilings.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-3 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, env vars, and protocol keywords in their canonical form.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- a completed Phase-2 handoff exists
- the case has an Engineering Spec Pack and implementation entry artifact
- the goal is runnable delivery with tests and evidence

Do not use when:
- Phase-1 or Phase-2 truth is still unresolved
- the task is a tiny isolated code edit
- the user only wants post-implementation review or validation

## Core Rules

1. Treat Phase-2 contracts, topology, data model, API contracts, and work packages as frozen input.
2. Return upstream instead of inventing missing product or architecture truth.
3. Generate or preserve failing tests before implementation.
4. Implement by bounded work package or packet, not by broad opportunistic coding.
5. Keep backend-first as the default mainline. Frontend, dispatch, hardening, and support lanes are optional unless explicitly activated.
6. Consume trace authority from `wff-base-traceability-management` and P2 bridge artifacts before claiming behavior/action-card source closure.
7. Separate script pass, test-obligation pass, runtime pass, test-quality pass, and delivery-ready claims.
8. Cap formal state by the weakest missing runtime, infrastructure, UI, manual, or external evidence.

## Primary Entrypoints

Aggregate implementation flow:

```bash
python3 scripts/phase3/run_impl.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output>
```

Focused capability runners:
- `scripts/phase3/run_impl_action_cards.py`
- `scripts/phase3/run_impl_db_schema.py`
- `scripts/phase3/run_impl_api_docs.py`
- `scripts/phase3/run_impl_backend.py`
- `scripts/phase3/run_impl_frontend.py`
- `scripts/phase3/run_impl_verification.py`

Runtime support:
- `scripts/phase3/phase3_toolchain_bootstrap.py`
- `scripts/phase3/run_vitest_targets_sequentially.py`
- `scripts/phase3/phase3_delivery_gate.py`

Read `reference-packages/phase3-implementation-delivery/README.md` before running or rerunning Phase-3.

TVG flags, when supported by a runner, are `--thinking-value-gain-mode` and
`--thinking-value-gain-output-profile`; use `coverage_rich` only to preserve
reviewable implementation reasoning. TVG is not the decision owner.

## Phase Review And Runnable Closure

Expose a Phase Review Breakpoint before delivery handoff. Reviewers may approve (`批准`), require modification (`要求修改`), require return (`要求返回`), or provide intervention input (`提供干预输入`); the decision must preserve runnable value and evidence-backed behavior, not final-report shape.

P3 closure is value-bearing only when core paths are runnable, accepted P2 contracts are implemented or review-bound, tests prove behavior beyond status/schema shape, runtime and persistence evidence are meaningful, and claim ceilings are explicit.

## Required Inputs

Read or verify:
- Phase-2 root
- `engineering-spec-pack.md`
- `phase-3-implementation-entry.md`
- Phase-2 trace registry or explicit review-bound reason
- implementation component catalog and action-card obligation matrix
- accepted API contracts and data model
- work-package ordering and risk posture

## Execution Sequence

1. Confirm Phase-2 handoff completeness and claim ceiling.
2. Freeze stack, contracts, topology, and runtime assumptions.
3. Generate implementation action cards and failing test obligations.
4. Generate or refresh DB schema, API docs, backend, optional frontend, and verification packs.
5. Bootstrap the runtime toolchain.
6. Run targeted tests by evidence family: SQL, contracts, scenarios, replays, and relevant units.
7. Run runtime smoke and started-service smoke when the chosen stack supports them.
8. Run delivery gate and record formal state.
9. Route failures to P1, P2, P3, or environment according to their real cause.

## Evidence Standards

Delivery claims require meaningful evidence:
- high-risk public operations require behavior cards before service/repository implementation.
- service code must implement behavior-card pseudocode steps; otherwise classify the gap as a `P3 implementation gap`.
- P3 must consume `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json` as canonical JSON bridge artifacts.
- Discovery policy is `canonical-json-first-markdown-diagnostic-only`; classify missing or malformed bridge material as `matrix_missing_from_p2`, `matrix_present_loader_missed`, or an equivalent review-bound source state using fields such as `source_requirement_status`.
- optional UI compiled bindings are not global OpenAPI authority. Use `require_frontend_contract` before letting compiled frontend bindings constrain backend OpenAPI/types/client operation authority.
- payload typing review is scoped to backend implementation targets; frontend page helper `payload: unknown` is not backend implementation genericity.
- API/contract tests must use documented request paths, not only helper-enriched payloads.
- SQL/persistence claims require real migration and write/read or state-transition proof.
- Scenario and replay tests must prove business outcomes, failure semantics, idempotency, or state invariance where relevant.
- Backend unit tests should verify non-trivial service/domain/repository behavior.
- Generated runtime or passthrough helpers may bootstrap work, but cannot be the final proof of implementation quality.
- UI/frontend claims need real routes and basic operable behavior, not a placeholder surface.

## P3 Agentic Repair Interrupts

Scorecard, delivery-gate, and human rough-review defects are repair triggers. When the reviewer says `要求修改`, `要求返回`, or `提供干预输入`, produce `agentic-repair-interrupt.json` and `agentic-repair-interrupt.md` with an Agentic repair packet, owning phase, minimum rerun boundary, and claim ceiling; do not treat final reports as the only output.

## P3 Agentic Quality Repair

Agentic generation-quality repair must be test-first and evidence-capped. When claiming quality gain, at least one generated code, test, or evidence unit must change; script pass alone does not prove quality gain. TVG is a generation value-gain tool, not a decision owner. WAE / EDSP / SELA own decision placement when workflow/agentic/evidence boundaries, fuzzy structure, or system-level trade-off must be judged.

Semantic invariant repair must use source-supported semantic invariant evidence. Review-bound source truth remains review-bound; do not turn it into confident implementation truth. No generated `/tmp` output edits, GEO-only hidden branches, PetClinic-only hidden branches, or error-type patches may be used to create a fake quality gain.

## P3 Authoring And Direct Driver Boundary

Default backend generation follows the action-card spine: `P2 component-action-card-obligation-matrix -> P3 implementation action cards -> action-card execution map -> service/repository/unit code`. `business-behavior-authoring-plan` may exist only as subordinate in-memory compatibility context; do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json` into a rich context artifact, or add a replacement persisted truth surface.

Before default service/repository/unit generation, synthesize in-memory project implementation conventions and an in-memory `phase3-agentic-module-implementation-brief.v1`. Agentic owns owner / aggregate / invariant / value-rule / service-flow strategy / repository-effect strategy / unit-test intent; Workflow supplies order/context/evidence; renderer helpers stay mechanical; Evidence / Gates may report mechanical owner/aggregate residue and cap claims.

`phase3-action-card-direct-implementation-driver.v1` is the default pre-file-write driver. Action Card obligations directly drive service/repository/unit generation; supporting semantic inputs may enrich naming, grouping, conventions, and implementation posture, but they must not bypass Action Card obligations.

Repository/audit/event generation must synthesize repository domain effects, state transition effects, audit/event effects, failure effect boundaries, and existing `domain_event_models` or `domain_event_catalog` before file write. Generated comments may expose producer / consumer / trigger / payload / timing / idempotency as `action-card-domain-event-modeling-effect`. This is not a performance optimization and not a P1/P2/P4 expansion.

## Selected-Module And Diagnostic Boundaries

Default Phase-3 mainline execution must not prepare `.phase3-review/phase3-synthesis-brief.json` or inject `Synthesis intent` comments. If a synthesis-only path is explicitly used, keep it as experimental evidence behind a non-default opt-in.

`--module-synthesis-bundle` is an explicit Phase-3 opt-in. Selected-module synthesis remains residue-governed, internal/experimental, and non-default; it is not a GEO/PetClinic branch and not an error-type patch. Thin or missing-TVG bundles must fail before selected service/repository/unit-test file bodies are written. `phase3-module-authoring-context.v1`, `authoring_context_sha256`, `phase3-module-tvg-quality-audit.v1`, `phase3-module-rewrite-packet.v1`, `phase3-module-behavior-plan.v1`, `module_behavior_plan`, and `phase3-module-obligation-consumption-audit.v1` are bounded evidence bridges, not business-truth generators.

Diagnostic-only material such as `generated-runtime-positioning.md` may move under `.phase3-diagnostics/` and review-only material may move under `.phase3-review/`, but protected quality-floor surfaces, P4-consumed evidence, and canonical proof must stay discoverable. Keep P4-consumed and canonical evidence root-level unless a resolver-backed profile proves the consumer path. Hard removal requires a separate classification record. Prefer profile directories over deletion, add resolver coverage before moving paths, do not chase root file count alone, and do not promote P3 slimming patterns to P1/P2/P4 without explicit work control.

Strict-runtime cost expectation: P3 accounted for about `96%` of recorded phase-step time in the retained proof. The main cost comes from full-targeted SQL / contract / scenario / replay evidence and work that must repeatedly restore runtime state; runtime smoke itself is not the main P3 wall-clock driver. RestoreV2 may optimize the generated backend test harness but must fall back to legacy truncate+seed restore. RestoreV3 may optimize first-clean-baseline cost.
`PHASE3_TEMPLATE_DATABASE_RESTORE=0` disables template restore. RestoreV4 may cache baseline-fixture restore plans, but do not treat plan caching as compensating-operation restore. Generated compensating-operation restore（反操作恢复）belongs to a later high-confidence optimization lane. Do not lower strict-runtime evidence. A fast-path pass must not be treated as `delivery-ready` / release-proof closure. `--validation-level fast` and focused validation do not auto-run runtime
smoke; 快速验证、聚焦验证、严格全量验证 carry different claim ceilings. 默认迭代可以先做快速验证或聚焦验证, but 声明上限必须明确低于交付就绪 / 发布证明.

## Optional Lanes

Use only when activated by scope or evidence need:
- frontend implementation
- API documentation hardening
- security review
- code review
- coverage collection
- dispatch / packet execution
- reader translation or delivery packaging support

Optional lanes must not weaken backend/runtime evidence or hide review-bound items.

## Completion Standard

Stop with one of these states:
- `delivery-ready`: runnable implementation and required evidence are green under the declared environment boundary
- `implementation-ready-with-claim-ceiling`: useful implementation exists but named evidence is missing
- `return-to-phase2`: accepted architecture/contract truth is insufficient or contradictory
- `return-to-phase1`: product truth is missing
- `blocked`: required runtime, toolchain, dependency, or source evidence is unavailable

Do not call Phase-3 complete when the repository only contains scaffolds, generated-runtime passthroughs, exit-code-only green reports, or unreviewed fake-green tests.
