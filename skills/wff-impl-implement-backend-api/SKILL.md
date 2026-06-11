---
name: wff-impl-implement-backend-api
description: Use when implementing Phase-3 backend/API slices after the contract pack and failing tests already exist, and the goal is to make frozen tests pass without drifting from the Phase-2 boundary.
---

# Phase-3 Backend API Implementation

## Scope

This skill owns backend implementation in S03.
It works inside the contract and test pack produced earlier by the orchestrator.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write backend packet notes, verification explanations, persistence truth summaries, and implementation-facing review text in Chinese
- preserve code, file paths, commands, API/schema field names, SQL identifiers, trace ids, artifact ids, env vars, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only backend handoff notes, packet summaries, or verification conclusions unless the user explicitly requests English

## Rules

- Treat `openapi.yaml`, migrations, shared types, and trace bindings as frozen inputs.
- Do not rewrite public contracts in controller code.
- Controller/BFF maps HTTP only.
- Application/service layer owns use-case behavior.
- Repository / adapter layer owns persistence and external boundaries.
- Behavior cards are the P3 enhanced interface contract: service, repository, unit, contract, and scenario generation must consume the same card-derived evidence, error, state, and source obligations.
- For `v1.3.6.10`, `business-behavior-authoring-plan` was the default P3 mainline pre-file-write authoring context for backend service/repository/unit bodies.
- Workflow supplies order/context/evidence: frozen contracts, source bridge inputs, file placement, strict-runtime execution, and claim ceilings.
- Agentic/default authoring owns business behavior plan: required context, state/conflict policy, repository decision load, invariant persistence, audit/event effect, semantic owner, response mapping, and unit-test obligations before renderer file write.
- Evidence caps claims through focused tests, strict-runtime proof, and human Review; the plan existing or renderer passing does not prove generated business quality by itself.
- Selected-module bundle remains non-default. Do not use `--module-synthesis-bundle`, selected-module synthesis, or F5/F6-style gate stacks as the backend mainline business-depth mechanism.
- Behavior-card evidence requirements must also be exposed on the public OpenAPI/API Docs surface. If a backend service rejects calls missing `trace_id`, aggregate ids, tenant ids, version anchors, or other evidence keys, those fields must be documented as required request/query fields and verified through an OpenAPI-consumer contract test.
- For v1.2.3, high-risk public operations require behavior cards before service/repository implementation.
- For v1.2.3 ACD, Service/Domain/Repository/Adapter work must also consume P2-authored implementation action cards from `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json`.
- Behavior cards and implementation action cards must inherit trace authority from `wff-base-traceability-management`; do not create or trust a separate P3-only trace identity system.
- P3 must not use TVG as a value-preservation layer; behavior/action cards, semantic guards, and runtime verification must expose quality gaps directly.
- Backend test sufficiency must be checked through `test-obligation-matrix.json` / `test-obligation-audit.json`; raw counts of contract, scenario, SQL, replay, or unit files are not enough.
- Backend test richness must be checked through the Workflow / Agentic / Evidence bridge: Workflow closes `test-obligation-audit.json`, Agentic reviews `test-richness-review.json` / `.md`, and Evidence caps release claims in `phase3-quality-check.json`.
- If Agentic richness review is still `required`, do not claim full backend service quality even when generated tests and obligation audits pass; the honest state is `review-bound`.
- Negative-path tests must construct real derivable conditions where possible: wrong tenant/role for permission, stale version/duplicate key for conflict, missing id/path for not-found, and dependency failure through an injectable boundary.
- Scenario tests that use error variants must also prove state invariance; replay tests must include idempotency / duplicate / second-pass stress; SQL tests must distinguish concrete FK/state probes from review-bound empty loops.
- For the v1.3.6.11 default mainline, backend service/repository/unit generation must follow the action-card spine: `P2 component-action-card-obligation-matrix -> P3 implementation action cards -> action-card execution map -> service/repository/unit code`. When the execution map exists, do not emit `business-behavior-authoring-plan` as a default review artifact or truth surface; any compatibility projection must stay in-memory and subordinate to the action-card spine.
- Generated backend code and unit tests should remain reviewable back to `action_card_id`, operation/action-card step, ACD level, source refs, and required tests. Shared renderer helpers may reduce mechanical duplication, but they must not infer business owner/state/audit/repository semantics outside the action-card spine.
- For WO-119F.12 / v1.3.6.12, the default persisted backend `action-card-execution-map.json` is a pointer-only action-card surface. `source_refs / required_tests must not be persisted in default map`; rich context stays in-memory for generation and compatibility projection. do not restore business-behavior-authoring-plan.json, the F.11 heavy map, or a new default rich-context artifact.
- For WO-119F.13 / v1.3.6.13, backend service/repository/unit generation must consume an in-memory Agentic semantic decision before file write. The decision owns owner / aggregate / invariant / value-rule / failure-path / test-intent. Renderer helpers may place files, normalize syntax, and carry evidence pointers, but must not decide those semantics through `not-declared`, `review-bound`, or generic `business invariants` defaults. Templates / TVG may ask required semantic-depth questions; Evidence / Gates prove runtime and cap claims only.
- For WO-119F.14 / v1.3.6.14, backend service/repository/unit generation must receive in-memory project implementation conventions before F.13 semantic decisions. Conventions are synthesized from P2 project-language handoff, `tech-stack-decision.yaml`, and action-card rich context. They guide domain service / aggregate / repository / test naming and stack-aware code posture, but must not become a persisted rich artifact or naming gate. Evidence may count `mechanical_owner_name_count`, `mechanical_aggregate_name_count`, and `forbidden_name_residue_count`; it must not generate names.
- For WO-119F.15 / v1.3.6.15, backend service/repository/unit generation must receive an in-memory `phase3-agentic-module-implementation-brief.v1` before file write. Agentic owns module implementation strategy: service flow, repository effect, unit-test intent, aggregate/invariant model, and transaction/audit/auth/error posture. Renderer helpers may assemble imports, syntax, paths, trace comments, and runtime harness wiring only; they must not restore renderer-local business strategy defaults as the primary source of truth.
- If the module brief causes quality instability, classify the failure first as context insufficiency, Agentic judgment issue, renderer mapping issue, evidence issue, or environment issue. Only then may the backend route add a minimum mechanical fallback, and that fallback must be evidence-backed, deletion-conditioned, and forbidden from deciding business truth. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a default rich-context artifact, or bring back F5/F6 selected-module gate stacks.
- For WO-119F.16 / v1.3.6.16, backend service/repository/unit generation must receive an in-memory `phase3-action-card-direct-implementation-driver.v1` before file write. Action Card Direct Implementation Driver means Action Card obligations directly drive service/repository/unit generation: service execution steps, repository effect steps, failure mapping, audit/event posture, and unit assertion obligations. F.13/F.14/F.15 are supporting inputs; they may enrich owner, aggregate, naming, module grouping, or implementation posture, but must not bypass Action Card obligations.
- The F.16 driver must stay non-persisted. Do not restore `business-behavior-authoring-plan.json`, do not expand `action-card-execution-map.json`, do not add a replacement rich-context artifact, and do not bring back F5/F6 selected-module gate stacks. Evidence may prove direct consumption, runtime, quality score, and claim ceilings; it must not create business content.
- For WO-119F.17 / v1.3.6.17, backend repository/audit/event generation must continue the F.16 direct-driver route and synthesize repository domain effects, state transition effects, audit/event effects, and failure effect boundaries before file write. Agentic owns those domain-effect judgments from Action Card obligations, operation semantics, and runtime failure specs; renderer helpers mechanically place them and must not infer generic audit/repository semantics as the primary truth.
- For WO-119F.17.2, if the direct-driver context contains `trigger_events`, `domain_event_models`, or `domain_event_catalog`, use those event names and event-model fields before fallback synthesis. Keep producer / consumer / trigger / payload / timing / idempotency as `action-card-domain-event-modeling-effect` generated evidence comments, not as a new gate or persisted planning artifact.
- F.17 is not a performance optimization and not a P1/P2/P4 expansion. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a replacement repository/audit/event rich artifact, bring back F5/F6 gate stacks, or add case-specific branches.

Detailed behavior-card/test boundary rules live in `docs/v1.2-p3-behavior-card-contract-boundary-v0.1.md`.

Resolution matrix / discovery policy:

- P3 must consume `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json` as canonical JSON bridge artifacts before claiming behavior/action-card source closure.
- The discovery policy is `canonical-json-first-markdown-diagnostic-only`: markdown sections may explain or diagnose missing bridge material, but they do not replace canonical JSON for green trace/action-card authority.
- Minimal operation resolution rows must carry `operation_id`, `api_endpoint`, `http_method`, `risk_tier`, concrete `P1-*` trace IDs, concrete `P2-*` contract/source IDs, `source_files`, `source_anchors`, and `source_requirement_status`.
- Classify missing bridge artifacts as `matrix_missing_from_p2`; classify markdown-only bridge material without canonical JSON as `matrix_present_loader_missed`; classify malformed rows or missing required fields as `matrix_present_invalid_shape`; classify rows without concrete P1 IDs as `matrix_present_no_p1_ids`.
- If the selected Phase-2 root lacks these bridge artifacts, P3 must return upstream or mark review-bound instead of inferring operation/action-card source authority from filenames, endpoint names, or P3-local trace files.
- Service code must implement behavior-card/action-card pseudocode steps, not merely satisfy response shape.
- Do not rely only on `buildBehaviorCardPayload` or similar test helpers for happy-path proof. At least one contract test per public operation must execute the OpenAPI-derived request directly, so API Docs drift fails before frontend or external integration work begins.
- Do not accept zero backend unit tests for service/domain/repository code. Unit tests should follow behavior-oriented, readable, isolated test design; use mocks only at external boundaries, not to self-certify business behavior.
- Do not accept keyword-only "unit" tests as unit evidence. Service tests need isolated repository doubles or equivalent boundary proof, and repository assertions need call/error mapping evidence rather than broad words like `repository`, `duplicate`, or `db error`.
- Scenario tests for core happy chains should include documented invalid-request, permission, and conflict variants when those failure modes exist on the bound operations.
- SQL tests for database-backed slices should include restore/reentry and rollback proof in addition to schema, insert-read, not-null, unique, and FK checks.
- When behavior-card implementation would still be thin, do not mask it with TVG. Strengthen the reusable behavior/action-card contract, deterministic gates, or runtime bridge so the gap becomes visible and fixable.
- `ACD-3` parent cards are `split-required`; do not implement them directly until decomposed into executable child cards.
- If the case needs orchestration, keep orchestration explicit instead of hiding it in controller or DAO code.
- `delivery-ready` is impossible without real verification evidence; exit-code-only or `echo`-style green is invalid.
- `generated-runtime.ts`, `operation-support.ts`, or passthrough delegates may exist during bootstrap, but they must not remain the primary execution path of a completed backend slice.
- optional UI compiled bindings are not global OpenAPI authority; do not delete or ignore backend API operations just because they are absent from optional frontend compiled bindings.
- `require_frontend_contract` is the promotion switch: only then may compiled bindings constrain the derived OpenAPI/types/client operation set.
- payload typing review is scoped to backend implementation targets; frontend page helper `payload: unknown` is not backend implementation genericity and must not be used to weaken backend typing requirements.

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `tech-stack-decision.yaml`
- the case `openapi.yaml`
- the case migrations
- the case `phase3-toolchain-bootstrap.json`
- the Phase-2 `wff-base-traceability-management` registry (`.trace/trace.db`) or an explicit review-bound reason why it is unavailable
- the case `implementation-bindings.json`
- the owning WP `work-package-packets/<wp-id>/execution-packet.md`
- the case `work-package-wave-plan.json`
- the assigned `worker-input-packets/wave-XX/backend-worker-input-packet.md`
- the case `dispatch-manifest.json` or `execution-runtime-state.json`
- the generated contract/scenario/replay tests
- the case `behavior-cards/<operationId>.behavior-card.md` for high-risk public operations
- the case work-package ordering

## Execution Playbook

Work one bounded packet at a time.

1. Read the assigned backend worker packet and extract:
   - `contract_operations`
   - `implementation_targets`
   - `test_targets`
   - `implementation_playbook.contract_to_code_map`
   - `environment_bootstrap.bootstrap_command`
2. If the workspace toolchain is not ready, bootstrap it first instead of interpreting missing binaries as implementation failure.
3. If the real backend runtime baseline is still missing, establish it before claiming packet completion:
   - framework bootstrap / HTTP server entrypoint
   - runtime package scripts (`dev`, `build`, `start`, migrations)
   - persistence driver or ORM wiring
   - health/readiness endpoint
   - Dockerfile / compose commands that start the backend instead of only building it
   - compose-specific env values that use container-internal service addresses, not host-local developer URLs
4. For each assigned operation, build the code path in this order:
   - `operationId -> controller method`
   - `controller method -> service method`
   - `service method -> repository / adapter`
   - `behavior-card source -> Trace Skill registry binding -> pseudocode step -> service/repository implementation step` for high-risk operations
   - if the behavior card only has P3-local trace evidence or markdown-guessed sources, stop and mark trace continuity review-bound before implementing depth
5. Implement the controller first as a thin HTTP mapper only.
6. Implement the service next with the actual use-case semantics from Phase-2:
   - validation and invariant checks
   - orchestration / state transitions
   - explicit error mapping
7. Create or complete repository / adapter boundaries only when the service actually needs persistence or an external call.
8. After one operation or thin vertical slice is implemented, run the packet's contract tests immediately.
9. Keep contract/scenario/replay as the primary verification surface for frozen interface truth; do not use unit tests to bypass a broken contract.
10. When the slice introduces non-trivial service/domain logic, complete packet-local unit tests before widening scope.
11. Only after targeted interface tests are green for the slice, accept unit-test green as meaningful completion evidence.
12. Keep changes packet-local. Do not absorb unrelated work packages into the same edit loop.

## Required Mapping

Every backend slice should be explainable as:

- `frozen contract`: request/response/error surface from `openapi.yaml`
- `controller`: request parsing + response envelope mapping
- `service`: use-case decision logic
- `repository / adapter`: DB, queue, cache, or external I/O
- `tests`: contract first, then scenario/replay

If that mapping is unclear, stop treating the packet as implementation-ready and repair the packet inputs before coding.

## Verification Rule

When you run verification:

- targeted tests must emit structured framework output and remain the primary completion evidence
- missing or unrecognized test reports count as failure
- green review/security/audit on placeholder code is invalid and must be treated as a blocked packet

## Completion Standard

Backend work is not done when code exists.
It is done when:
- relevant contract/scenario/replay tests pass
- relevant unit tests pass for the implemented service/domain logic
- relevant WP gate row is green
- types and lint pass
- no contract drift was introduced
- the owned slice no longer depends mainly on generated-runtime-backed execution
- at least one real SQL-backed write -> independent read/state-transition proof exists for each database-backed slice that owns persistence
- the backend still supports documented startup and container build commands on a server-capable environment
