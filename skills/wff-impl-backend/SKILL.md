---
name: wff-impl-backend
description: Use when implementing Phase-3 backend/API slices after the contract pack and failing tests already exist, and the goal is to make frozen tests pass without drifting from the Phase-2 boundary.
---

# Phase-3 Backend API Implementation

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns backend implementation in S03.
It works inside the contract and test pack produced earlier by the orchestrator.

Primary P3-S3 generation-only runner after accepted S2 authority:

```bash
python3 scripts/phase3/run_impl_realization.py \
  --phase2-root <phase2-root> \
  --action-card-root <s1b-output-root> \
  --agentic-implementation-decision <accepted-p3-decision.json> \
  --output-dir <phase3-output>
```

This runner generates the complete backend mechanical workspace shell, declared implementation/test targets, DB migration support, and static schema-test source. MGET-qualified config/contract/wiring stays deterministic; executable service/repository/policy bodies and unit/integration behavior assertions are Agentic-owned coarse blocks. An unresolved block makes the existing S3 receipt `authoring-required`. The Host Agent writes only inside the emitted `@wff:agentic-begin/end` regions, then reruns this same runner against the same root; Workflow preserves materialized regions, verifies the surrounding template shell is unchanged, and only then may close the generation step as `generated-not-executed`. The runner proves bounded block materialization and hashes, not writer identity or semantic correctness; those require Host-Agent/session evidence and later verification. Do not revive selected-module bundles, parallel code-authoring routes, or rich persisted ownership maps. The runner still does **not** generate runtime-dependent SQL execution tests, execute generated tests, start the backend, or confirm Trace. SQL execution tests remain owned by later execution/verification because they require the backend/DB runtime harness. `scripts/phase3/run_impl_backend.py` remains the lower-level backend workspace/contract scaffold and is not by itself S3 realization proof. Neither runner may create `apps/web`; frontend delivery is owned by `wff-impl-frontend`.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-backend/` for the capability contract, SOP, output template, and source cards.

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
- When P2/S2 provides structured durable persistence authority, generated S3 bindings must carry the exact command kind, identity components, carrier, field bindings, enforcement, writer, and replay posture into repository/service Agentic blocks. Do not recover these semantics from operation names, repository filenames, prose, or generic CRUD assumptions. This propagation does not itself authorize SQL lowering or runtime persistence execution. If implementation evidence only sharpens a realization detail without contradicting frozen P1/P2 truth, keep the refinement in the P3 implementation decision and record its P3 Authority Delta ID; do not rewrite upstream authority mid-cycle. Genuine unresolved product/architecture ambiguity remains return/review-bound.
- Behavior cards are the P3 enhanced interface contract: service, repository, unit, contract, and scenario generation must consume the same card-derived evidence, error, state, and source obligations.
- Workflow supplies order/context/evidence: frozen contracts, source bridge inputs, file placement, strict-runtime execution, and claim ceilings.
- Agentic/default authoring owns behavior strategy: required context, state/conflict policy, repository decision load, invariant persistence, audit/event effect, semantic owner, response mapping, and unit-test obligations before renderer file write.
- Evidence caps claims through focused tests, strict-runtime proof, and human Review; an authoring plan existing or renderer passing does not prove generated business quality by itself.
- Selected-module synthesis is retired from the active backend CLI and release-proof route. Do not offer or pass `--module-synthesis-bundle`; historical source/fixtures may remain for evaluation only and must not become a parallel authoring route.
- Behavior-card evidence requirements must also be exposed on the public OpenAPI/API Docs surface. If a backend service rejects calls missing `trace_id`, aggregate ids, tenant ids, version anchors, or other evidence keys, those fields must be documented as required request/query fields and verified through an OpenAPI-consumer contract test.
- High-risk public operations require behavior cards before service/repository implementation. When accepted P3 authority marks an operation `read-only`, the Behavior Card and downstream service/test mapping must preserve read/no-mutation semantics; do not force state-transition, durable-write, audit-write, or command-only obligations onto a read path.
- Service/Domain/Repository/Adapter work must consume P2-authored implementation action cards from `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json`.
- Behavior cards and implementation action cards must inherit trace authority from `wff-base-traceability-management`; do not create or trust a separate P3-only trace identity system.
- P3 must not use TVG as a value-preservation layer; behavior/action cards, semantic guards, and runtime verification must expose quality gaps directly.
- Backend test sufficiency must be checked through `test-obligation-matrix.json` / `test-obligation-audit.json`; raw counts of contract, scenario, SQL, replay, or unit files are not enough.
- Backend test richness must be checked through the Workflow / Agentic / Evidence bridge: Workflow closes `test-obligation-audit.json`, Agentic reviews `test-richness-review.json` / `.md`, and Evidence caps release claims in `phase3-quality-check.json`.
- If Agentic richness review is still `required`, do not claim full backend service quality even when generated tests and obligation audits pass; the honest state is `review-bound`.
- Negative-path tests must construct real derivable conditions where possible: wrong tenant/role for permission, stale version/duplicate key for conflict, missing id/path for not-found, and dependency failure through an injectable boundary.
- Scenario tests that use error variants must also prove state invariance; replay tests must include idempotency / duplicate / second-pass stress; SQL tests must distinguish concrete FK/state probes from review-bound empty loops.
- Backend service/repository/unit generation must follow the action-card spine: `P2 component-action-card-obligation-matrix -> P3 implementation action cards -> action-card execution map -> service/repository/unit code`. When the execution map exists, do not emit `business-behavior-authoring-plan` as a default review artifact or truth surface; any compatibility projection must stay in-memory and subordinate to the action-card spine.
- Generated backend code and unit tests should remain reviewable back to `action_card_id`, operation/action-card step, ACD level, source refs, and required tests. Shared renderer helpers may reduce mechanical duplication, but they must not infer business owner/state/audit/repository semantics outside the action-card spine.
- The default persisted backend `action-card-execution-map.json` is a pointer-only action-card surface. Rich context stays in-memory for generation and compatibility projection.
- Backend service/repository/unit generation must consume the accepted current-snapshot S2 implementation authority before executable file realization. The accepted slice decisions own owner / aggregate / invariant / value-rule / failure-path / persistence / integration / test intent. Renderer and scaffold helpers may place files, normalize syntax, carry evidence pointers, and emit bounded Agentic regions, but must not decide those semantics through generic defaults.
- Project implementation conventions may guide mechanical naming and stack posture, but they remain subordinate context and must not become a persisted rich artifact, naming authority, or replacement for S2 decisions.
- `run_impl_realization.py` / `s3_code_realization.py` are the current pre-file-write realization path. They bind exact S2 decision digests, Action Card/constraint references, implementation targets, test targets, and bounded Agentic blocks. Legacy `phase3-agentic-module-implementation-brief.v1`, `phase3-action-card-direct-implementation-driver.v1`, and `business-behavior-authoring-plan` sources are historical/evaluation residue only; do not require or recreate them in the active backend route.
- If generation quality is unstable, classify the failure first as context insufficiency, Agentic judgment issue, renderer mapping issue, evidence issue, or environment issue. Only then may the backend route add a minimum mechanical fallback, and that fallback must be evidence-backed, deletion-conditioned, and forbidden from deciding business truth. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a default rich-context artifact, or bring back selected-module gate stacks.
- Backend repository/audit/event generation must synthesize repository domain effects, state transition effects, audit/event effects, and failure effect boundaries before file write. Agentic owns those domain-effect judgments from Action Card obligations, operation semantics, and runtime failure specs; renderer helpers mechanically place them and must not infer generic audit/repository semantics as the primary truth.
- If accepted authority or bound Action Card context contains `trigger_events`, `domain_event_models`, or `domain_event_catalog`, use those event names and event-model fields before fallback synthesis. Keep producer / consumer / trigger / payload / timing / idempotency as generated evidence comments, not as a new gate or persisted planning artifact.
- This realization route is not a performance optimization and not a P1/P2/P4 expansion. Do not add case-specific branches.

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

When `subagent_slice_packets` are present in the assigned backend worker packet, treat each slice as the smallest executable Action Card contract. A slice may be delegated to an independent SubAgent only within its `allowed_edit_files`, using its listed targeted/unit evidence commands and returning the declared `subagent_return_contract`. A blocked slice must be returned as blocked rather than widened into unrelated files, upstream truth edits, or broad packet implementation.

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
