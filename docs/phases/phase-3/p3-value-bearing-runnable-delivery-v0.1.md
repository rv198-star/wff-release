# P3 Value-Bearing Runnable Delivery (v0.1)

Status: `WO-119A.09` local verification record
Date: 2026-05-03
Owning work: `WO-119A.09`
Control boundary: `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
Stage Judgment Lens: `docs/governance/v1.3-stage-judgment-lens-v0.1.md`
Chinese mirror: `docs/phases/phase-3/p3-value-bearing-runnable-delivery-v0.1.zh-CN.md`

## Purpose

This document defines the `v1.3.1` closure expectation for Phase-3 implementation.

P3 closure must prove runnable delivery value, not merely code generation, endpoint existence, or script-green packaging.

## Closure Rule

P3 may close only when the output makes a substantive judgment on:

- runnable delivery value;
- core path usability;
- implementation completeness inside accepted P1/P2 truth;
- test meaning and assertion quality;
- runtime evidence strength;
- downstream continuation value.

Code volume, generated runtime green, unit-count pass, API shape existence, delivery-gate file presence, or script pass are support signals. They are not sufficient closure by themselves.

## Required Closure Statement

The P3 closeout surface should state:

- what core path is runnable and why it matters;
- which business behavior is actually implemented;
- which accepted P2 contracts are satisfied or review-bound;
- what tests prove beyond status codes or schema shape;
- which runtime, persistence, migration, API, UI, or infrastructure evidence supports the claim;
- what a downstream developer or Agent can safely continue from;
- what evidence is missing and how that caps the formal state.

## Failure And Routing

Route findings as:

- `源头事实缺口` (`source-truth-gap`) or `产品/规格缺口` (`product-spec-gap`) -> P1 / pre-P1 when implementation would otherwise invent business truth;
- `架构缺口` (`architecture-gap`) -> P2 when implementation requires design changes;
- `实现修补` (`implementation-patch`) -> P3 remediation;
- `证据缺口` (`evidence-gap`) -> P3 when runtime/test evidence is missing or weak.

If P4 would need to guess whether behavior is real, whether assertions are meaningful, or whether the runtime path actually works, P3 is not value-bearing closed.

## Agentic Implementation Loop Rule

P3 must emit a default Agentic implementation-loop surface even when optional dispatch is disabled:

- `agentic-implementation-loop.json`;
- `agentic-implementation-loop.md`.

The loop surface must select value/risk implementation slices, define bounded execution/remediation stop conditions, name TVG checkpoints for service-boundary/test-meaning/runtime-evidence value, and connect implementation bindings to runtime evidence expectations.

This artifact does not replace strict-runtime proof. Strict-runtime proof does not replace Agentic implementation-value judgment.

## Default Business Behavior Authoring Rule

For `v1.3.6.10`, `business-behavior-authoring-plan` is the default P3 mainline pre-file-write authoring context for service/repository/unit business bodies.

Workflow supplies order/context/evidence: phase order, OpenAPI/runtime spec assembly, P1/P2 source bridge loading, file placement, strict-runtime execution, and claim ceilings. Agentic/default authoring owns business behavior plan: operation intent, required context, read/write semantics, state/conflict policy, repository effects, audit/event effects, semantic owner, response mapping, and unit-test obligations before renderer file write.

Evidence caps claims through focused tests, GEO + PetClinic strict-runtime, and human Review. The plan existing, generated files existing, or script pass is not sufficient proof of generated-artifact quality.

Selected-module bundle remains non-default. Do not use `--module-synthesis-bundle`, selected-module synthesis, or F5/F6-style gate stacks as the default P3 business-depth mechanism.

## Action-Card-Centered Mainline Rule

For `v1.3.6.11`, default P3 code generation must use this spine:

`P2 component-action-card-obligation-matrix -> P3 implementation action cards -> action-card execution map -> service/repository/unit code`.

`business-behavior-authoring-plan` is not a second business-truth layer when `action-card-execution-map.json` exists. The default mainline must not emit it as a persisted review artifact or truth surface; any compatibility projection must stay in-memory and subordinate to the action-card spine. Renderer helper code may perform mechanical lookup, merge, and error mapping, but it must not independently infer business owner, state, audit, repository effect, or test obligation semantics outside the action-card spine.

Generated service/repository/unit outputs should be reviewable back to `action_card_id`, action-card step / operation, ACD level, source refs, and required tests. Do not delete action cards as a slimming tactic. Slim duplicated plan/helper narration around the action-card spine while preserving strict-runtime evidence and human Review.

## Pointer-Only Action-Card Surface Rule

For `WO-119F.12` / `v1.3.6.12`, the default persisted `action-card-execution-map.json` is a pointer-only action-card surface. `source_refs / required_tests must not be persisted in default map`; rich context stays in-memory for business-behavior compatibility projection and service/repository/unit scaffolding.

do not restore business-behavior-authoring-plan.json, do not restore the F.11 heavy execution map as the default review surface, and do not add another default persisted rich-context artifact. Generated quality still requires strict-runtime evidence and human Review; pointer-only slimming is not a material generated-quality claim.

## Agentic Semantic Authoring Rule

For `WO-119F.13` / `v1.3.6.13`, P3 default generation must create an in-memory Agentic semantic decision before service/repository/unit file write.

Workflow owns phase order, context assembly, file placement, and evidence commands. Agentic owns owner / aggregate / invariant / value-rule / failure-path / test-intent judgment. Templates / TVG may use `p3-agentic-semantic-authoring-question-set-v0.1.md` to ask depth questions, but must not provide answers. Evidence / Gates prove runtime/test closure and cap claims; they must not create content truth.

The default persisted surface remains F.12 pointer-only: do not restore `business-behavior-authoring-plan.json`, do not expand `action-card-execution-map.json` back into a rich context artifact, and do not add a replacement default rich artifact. `not-declared`, `review-bound`, and generic `business invariants` are not acceptable semantic answers; if context is insufficient, keep the item review-bound or return upstream instead of letting the script decide.

## Project Implementation Convention Rule

For `WO-119F.14` / `v1.3.6.14`, P3 default generation must synthesize in-memory project implementation conventions before F.13 semantic decisions and before service/repository/unit file write.

Inputs:

- P2 project-language handoff from source-backed P2 outputs
- `tech-stack-decision.yaml`
- action-card rich context in memory
- optional UI/UX surface context only when frontend/UI surfaces exist

The conventions guide naming, code, design, test, and optional UI/UX posture. They must not be persisted as a replacement rich truth artifact. Evidence / Gates may report `mechanical_owner_name_count`, `mechanical_aggregate_name_count`, `forbidden_name_residue_count`, convention drift, and claim ceilings, but must not generate naming answers.

## Agentic Module Implementation Brief Rule

For `WO-119F.15` / `v1.3.6.15`, P3 default generation must synthesize an in-memory `phase3-agentic-module-implementation-brief.v1` before service/repository/unit file write.

The module brief consumes action-card rich context, Agentic semantic decisions, project implementation conventions, OpenAPI/runtime specs, and selected stack context. Agentic owns module implementation strategy: module purpose, operation grouping, aggregate/invariant model, service-flow strategy, repository-effect strategy, transaction/audit/auth/error posture, and unit-test strategy.

Workflow/scripts may assemble context, render files, place traces, run verification, record metadata, and cap claims. Renderer helpers must stay mechanical; they must not independently decide service flow, repository effect, or unit-test intent when a module brief exists.

If quality becomes unstable, classify the failure before adding any fallback: context insufficiency, Agentic judgment issue, renderer mapping issue, evidence issue, or environment issue. A fallback is allowed only when evidence requires it, must be mechanical and deletion-conditioned, and must not decide business truth. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a default rich-context artifact, or restore F5/F6 selected-module gate stacks.

## Action Card Direct Implementation Driver Rule

For `WO-119F.16` / `v1.3.6.16`, P3 default generation must synthesize an in-memory `phase3-action-card-direct-implementation-driver.v1` before service/repository/unit file write.

Action Card Direct Implementation Driver means Action Card obligations directly drive service/repository/unit generation. Service bodies consume service execution steps, repository bodies consume repository effect steps, and unit tests consume unit assertion obligations. Failure mapping and audit/event posture should also come from the driver when present.

F.13/F.14/F.15 are supporting inputs. They may enrich owner / aggregate / invariant interpretation, project conventions, naming, code posture, module grouping, and implementation strategy, but they must not bypass or replace Action Card obligations as the primary business-obligation source.

The driver must not become a persisted default artifact. Do not restore `business-behavior-authoring-plan.json`, do not expand `action-card-execution-map.json`, do not add a replacement rich-context artifact, and do not restore F5/F6 selected-module gate stacks. Evidence may prove direct consumption, runtime behavior, quality score, and claim ceilings; it must not create business content.

## Repository Audit Event Domain Sharpening Rule

For `WO-119F.17` / `v1.3.6.17`, P3 default repository/audit/event generation must continue the F.16 Action Card direct-driver route and synthesize repository domain effects, state transition effects, audit/event effects, and failure effect boundaries before file write.

Agentic owns those domain-effect judgments from Action Card obligations, operation semantics, and runtime failure specs. Renderer helpers must mechanically place the effects in service/repository/unit files; they must not infer generic repository or audit/event language as the primary content truth.

For `WO-119F.17.2`, if `trigger_events`, `domain_event_models`, or `domain_event_catalog` are already present, P3 should consume them before fallback event-name synthesis. Generated comments may expose producer, consumer, trigger, payload, timing, and idempotency as `action-card-domain-event-modeling-effect`. P3 must not invent a new P2 event catalog or add a default persisted event-model artifact.

F.17 is not a performance optimization and not a P1/P2/P4 expansion. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a replacement repository/audit/event rich artifact, restore F5/F6 gate stacks, or add case-specific branches.

## Local Verification Question

`WO-119A.09` is complete if this document and the P3 skill mirror make clear that P3 closure is runnable value and evidence-backed behavior, not code or script completion.
