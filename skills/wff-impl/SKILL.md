---
name: wff-impl
description: Use when running or rerunning the official Phase-3 implementation flow from a completed Phase-2 handoff and you need the contract-first, test-first, work-package-driven execution path rather than ad hoc coding.
---

# Phase-3 Implementation Orchestrator

## Overview

This is the official Phase-3 entry skill.

It does not replace backend, frontend, testing, review, security, or API-doc work.
It freezes their working order so Phase-3 delivery does not collapse into "start coding and fix drift later".

Primary aggregate runner:

```bash
python3 scripts/phase3/run_impl.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output>
```

Compatibility runner:

```bash
python3 scripts/phase3/run_phase3_first_version.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output>
```

The aggregate runner is capability-composed: action cards, DB schema, verification test generation, backend, optional frontend, API docs, and verify-only closure run as separate P3 capability steps.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/README.md` before running or rerunning P3.
Use the capability packages under `reference-packages/phase3-implementation-delivery/` for contract, SOP, output-template, and source-card guidance.
The reference package is the method layer; `scripts/phase3/` remains the runtime layer.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write acceptance/execution/handoff reports, runtime guidance, audit notes, fallback UI copy, and operator-facing summaries in Chinese
- preserve code, file paths, commands, API/schema field names, trace ids, artifact ids, env vars, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only Phase-3 reports, delivery notes, review conclusions, or fallback artifact prose unless the user explicitly requests English

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.

## When to Use

Use when:
- the user wants to start Phase-3 from a completed Phase-2 handoff
- the case already has an Engineering Spec Pack and implementation entry artifact
- the goal is runnable project delivery, not only implementation notes

Do not use when:
- you are only editing one backend/frontend module in isolation
- you are only reviewing code after implementation
- Phase-2 boundary or topology decisions are still unresolved

## Core Rule

Phase-3 is not `Code -> Test -> Review`.
It is:

1. `Contract -> Stack Freeze`
2. `Failing Tests -> Coverage Plan`
3. `Implementation by Work Package`
4. `Hardening / Review / Security / Docs / Delivery`

No business implementation starts before:
- the implementation topology is frozen from Phase-2
- the contract pack exists
- the failing test pack exists
- the Phase-2 `wff-base-traceability-management` registry is loaded or explicitly declared unavailable with a review-bound reason

## Workflow / Agentic Boundary

Treat Phase-3 as:

> `workflow-dominant delivery mainline + bounded agentic execution loops`

- workflow certainty is high for contract freeze, test-first order, work-package boundaries, delivery gates, and required evidence
- agentic scope is limited to targeted implementation decisions, bounded rewrites, debugging, hardening, and review loops inside the frozen Phase-2 topology
- Phase-3 must not reopen Phase-1 business truth or Phase-2 architecture truth; if those are missing, return upstream instead of improvising new product/design direction here
- optional packet / wave / dispatch / frontend fallback lanes are bounded support lanes; they must not overtake the backend-first mainline unless that lane was explicitly activated
- the default backend-first mainline must still emit an `agentic-implementation-loop` artifact, even when optional dispatch is disabled; this artifact selects value/risk implementation slices, defines the bounded implementation/remediation loop, records TVG checkpoints for service-boundary/test-meaning/runtime-evidence value, and links P1/P2 value rows to runtime evidence expectations
- optional dispatch may execute or packetize the loop, but it is not the source of Agentic implementation judgment; P3 must not treat "dispatch disabled" as "implementation loop absent"
- generated adapters or helper runtimes may accelerate progress, but they must not become the unexamined execution truth of a completed delivery package

## Development / Pre-Production Boundary

Phase-3 delivery evidence is scoped to the available development, isolated, or pre-production runtime environment.

By default, `implementation-ready` and `delivery-ready` mean readiness under that verified environment boundary. They do not mean production deployment approval, go-live approval, production rollback approval, production monitoring handover, real business-owner sign-off, or production risk acceptance.

External staging / production / owner-signoff evidence may be consumed only when supplied. If it is absent, cap the formal state at the development / pre-production evidence level and name the missing external evidence in closeout wording.

## v1.2.3 Runtime Protocol

`wff-impl` now follows the `v1.2.3` P3 backend delivery protocol:

### Mandatory Trace Skill Continuity

P3 must continue the project-level trace system from `wff-base-traceability-management`.

Standard flow:

1. Locate the Phase-2 `.trace/trace.db` and traceability report before generating P3 behavior cards, tests, implementation bindings, or code-review evidence.
2. Resolve P1/P2 source authority registry-first: `P2-CTR-*`, `P2-DTR-*`, `P2-RP-*`, `P2-RT-*`, and their upstream `P1-*` links come from the Trace Skill registry or its authored bridge fields.
3. Use markdown scanning only as fallback diagnostics, never as the primary source of trace truth when the registry is present.
4. Treat `phase-3-trace-registry.json`, `phase-3-trace-registry-final.json`, and `test-trace-matrix.json` as P3 implementation/test binding views derived from upstream trace authority, not as a new trace identity system.
5. If the registry is missing, stale, copied with invalid paths, or cannot answer an operation-level source question, mark the item `review-bound` with a precise reason before implementation depth is claimed.

Failure to follow this is a P3 process defect: it breaks the P1/P2→behavior-card→test→implementation chain and risks falling back into Vibe Coding.

Resolution matrix / discovery policy:

- P3 must consume `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json` as canonical JSON bridge artifacts before claiming behavior/action-card source closure.
- The discovery policy is `canonical-json-first-markdown-diagnostic-only`: markdown sections may explain or diagnose missing bridge material, but they do not replace canonical JSON for green trace/action-card authority.
- Minimal operation resolution rows must carry `operation_id`, `api_endpoint`, `http_method`, `risk_tier`, concrete `P1-*` trace IDs, concrete `P2-*` contract/source IDs, `source_files`, `source_anchors`, and `source_requirement_status`.
- Classify missing bridge artifacts as `matrix_missing_from_p2`; classify markdown-only bridge material without canonical JSON as `matrix_present_loader_missed`; classify malformed rows or missing required fields as `matrix_present_invalid_shape`; classify rows without concrete P1 IDs as `matrix_present_no_p1_ids`.
- If the selected Phase-2 root lacks these bridge artifacts, P3 must return upstream or mark review-bound instead of inferring operation/action-card source authority from filenames, endpoint names, or P3-local trace files.

1. consume accepted P2 contracts as implementation truth
   - do not silently rewrite service boundaries, data contracts, API contracts, storage posture, or interaction flows during implementation
   - if a contract is incomplete, contradictory, or non-buildable, record it as review-bound / bounded return instead of hiding the change in code
2. use `Public Contract Skeleton` and behavior cards before private implementation for high-risk public services/APIs
   - skeleton first defines public method / endpoint signature, input/output contract, preconditions, postconditions, state effects, persistence effects, error semantics, permission boundary, idempotency/replay rule, evidence expectation, and review-bound items
   - high-risk public operations require behavior cards that bind P1/P2 trace IDs, P2 contract/flow/state sources, human-readable pseudocode, test mapping, implementation mapping, and review-bound items
   - behavior cards must use `wff-base-traceability-management` as the authoritative upstream trace registry; do not invent parallel trace IDs or treat `phase-3-trace-registry*.json` as a replacement for the Phase-1/Phase-2 trace registry
   - P3 trace artifacts are downstream implementation/test bindings; they may enrich the trace graph but must not restart the identity system
   - then write contract/interface/scenario tests against public behavior
   - only then implement private methods and internal logic
   - service code must implement behavior-card pseudocode steps, not merely satisfy response shape
   - when risk is unclear, classify the public service/API as high-risk for skeleton purposes
3. classify public service/API risk before choosing skeleton depth
   - use the shared P2/P3 operation risk model in `docs/v1.2-operation-risk-tiering-and-source-obligations-v0.1.md`
   - P2-authored `risk_tier`, `risk_triggers`, `required_source_types`, and `not_required_source_types` are the source of truth for P3 behavior-card source requirements
   - if P3 recomputes risk, it is only a consistency check; mismatches must be reported as `risk_tier_mismatch`, not silently used to downgrade source requirements
   - P3 must not use a private risk model to convert missing P2 flow/sequence/state sources into `not_required`; if the P2 row is missing or ambiguous, mark `p2_operation_risk_row_missing` / review-bound
   - high-risk tiers are `HR-MUTATION`, `HR-BOUNDARY`, and `HR-ORCHESTRATION`; `MR-READ-SENSITIVE` and `LR-SIMPLE-READ` are lighter only when P2 classified them that way from the shared rule
4. generate implementation action cards from P2-authored ACD obligations before writing private code
   - required card families are `Service Action Card`, `Domain Action Card`, `Repository Action Card`, and `Adapter Action Card` where applicable
   - P3 must consume the full P1/P2 bridge: `p1_value_to_p2_operation_resolution_matrix`, `implementation_component_catalog`, and `component_action_card_obligation_matrix`
   - missing bridge artifacts are blocking/review-bound: `p1_value_to_p2_operation_resolution_matrix_missing`, `implementation_component_catalog_missing`, or `component_action_card_obligation_missing`
   - P3 must report `action_card_depth_mismatch` if local observation disagrees with P2 depth
   - P3 may raise depth or mark review-bound, but must not locally downgrade `ACD`
   - if source material required by the P2 card depth is missing, mark `action_card_source_material_missing` instead of inventing behavior
   - if a card has operations but no P1 trace, mark `action_card_p1_trace_missing`; if it only carries abstract labels like `P2-FLOW` instead of concrete `P2-FLOW-*` source IDs, mark `action_card_concrete_source_id_missing`
   - service/domain/repository code must implement action-card steps, not merely satisfy API response shape
5. make tests business-scenario-grounded
   - P1 decides test value
   - P2 decides test landing point through service boundary, data object, interface contract, and interaction flow
   - P3 proves runtime behavior
   - generate and audit `test-obligation-matrix.json` before trusting test volume; the matrix must derive obligations from OpenAPI, behavior cards, action cards, P1/P2 scenarios, replay rows, and DB schema
   - generate `test-richness-review.json` / `test-richness-review.md` as the Workflow / Agentic / Evidence bridge for test meaning: Workflow may close obligations, but Agentic must judge whether assertions prove business behavior
   - if `test-richness-review.json` says Agentic review is still required, `phase3-quality-check.json` may pass mechanical gates but must cap `recommended_formal_state` at `review-bound`
5. run `Assertion Deepening` before trusting test suites
   - tests should prove state, persisted data, permissions, error semantics, idempotency, replay, and boundary effects where relevant
   - do not count tests that only prove HTTP 200, endpoint existence, or schema shape as strong delivery evidence
   - do not count forced-error-only permission/conflict/dependency branches or keyword-only unit tests as business-rich proof
   - scenario negative variants must prove the failed action leaves relevant state unchanged, not only that an error envelope is returned
   - replay tests must include explicit idempotency / duplicate / second-pass stress or stay review-bound
   - SQL FK/state obligations require concrete probes; empty FK probe loops or state-update-by-title only are review-bound / weak evidence
6. use evidence-driven TDD
   - contract / migration / persistence / scenario evidence outranks isolated unit coverage
   - unit coverage remains useful but cannot replace real migration, SQL/persistence, started-service, queue/cache/auth/storage, or scenario evidence
7. produce an evidence-linked API surface for core APIs
   - link API docs to P1 scenario, P2 contract, endpoint, request/response/error semantics, test evidence, evidence level, and review-bound status
   - provide bounded API scenario call chains for core flows and high-risk paths
   - do not generate a full API graph by default
   - API Docs must be executable by an external consumer without knowing internal behavior-card test helpers
   - if service behavior requires behavior-card evidence keys, those keys must appear in OpenAPI request bodies or query parameters as required consumer contract fields
   - contract tests must include a documented OpenAPI request execution path that uses the generated OpenAPI payload directly, not only a behavior-card-enriched payload
8. prove infrastructure capabilities separately from mock-backed business tests
   - DB claims require migration plus core write/read or state-transition proof
   - cache claims require set/get/TTL/invalidation proof when correctness depends on cache behavior
   - queue claims require publish/consume/retry/failure-boundary proof when async behavior matters
   - auth claims require at least one allowed path and one denied path
   - development-only auth context headers must be default-off and may run only behind an explicit opt-in such as `PHASE3_ALLOW_AUTH_CONTEXT_HEADER=true`; they must not be treated as delivery-ready auth
   - storage/scheduler/external dependency claims require real proof or explicit substitute boundary plus review-bound status
9. enforce reentrant persistence testing
   - persistent-state tests must declare state isolation, reentry policy, and rerun proof
   - init / seed / cleanup / restore discipline is required before persistence proof can support delivery-ready claims
10. classify evidence levels explicitly
   - suggested levels: `mock-backed unit`, `in-process integration`, `started-service contract`, `SQL-backed persistence`, `cache-backed`, `queue-backed`, `containerized runtime`, `external-substitute-boundary`
11. run DB/API evidence suites with family-split sequential execution
   - tests that use real Postgres, `initializeDatabase`, `restoreScenario`, local API servers, or shared runtime ports must not be executed as one large mixed concurrent Vitest batch
   - split execution by evidence family first, at minimum `sql`, `contracts`, `scenarios`, and `replays`
   - within each family, run files sequentially unless the suite has explicit isolation proof for safe parallelism
   - each family needs its own report, timeout/stop boundary, and failure classification so a long or stuck family does not hide progress from other evidence lanes
   - do not treat a giant green mixed batch as better evidence than smaller family reports; observability, reentry, and diagnosability are part of P3 delivery quality
   - DB/API preflight and the corresponding test execution must use the same execution permission path; if default sandbox returns `EPERM 127.0.0.1`, classify it as execution-permission error and rerun through the approved local-DB access path before judging DB/test quality
12. triage failures before fixes
   - classify failures as implementation bug, weak/wrong test assertion, environment/bootstrap issue, P2 contract/design gap, P1 business ambiguity, or external dependency unavailable
   - do not hide failures by weakening assertions, replacing real paths with mocks, silently changing accepted contracts, or adding wrapper-green reports over runtime-red behavior

13. separate test evidence layers before release judgment
   - `strict-runtime` P3 runs full SQL / contract / scenario / replay targeted evidence by default before P4 validation
   - `critical-targeted-tests` is an explicit fast sampling lane via `--critical-targeted-evidence-only`, not the release-default integration proof
   - when `full-targeted-tests` runs, it is the canonical targeted evidence report and must not be duplicated by a default critical-targeted run
   - `script pass` means the runner/toolchain completed; it does not prove runtime truth or assertion quality
   - `test obligation pass` means the Workflow coverage floor was met; it does not prove business richness
   - `test richness review pass` means Agentic review found the assertions business-meaningful and non-virtual; without it, the run is `review-bound`
   - `runtime pass` means the selected API/DB/scenario/replay families passed on the intended execution path; it does not prove the tests are meaningful
   - `code-level test quality pass` requires manual review that the generated tests have business/API/DB/scenario value and are not fake-green
   - release or closeout wording must cite these layers separately and state the ceiling when frontend E2E, started-service proof, external staging proof, or production-readiness evidence is outside scope

Hard boundaries:

- P3 is backend-first by default; frontend, fallback UI, dispatch, and extra hardening stay optional unless explicitly promoted
- generated runtime can bootstrap P3, but cannot certify implementation-ready or delivery-ready
- formal state is capped by the weakest missing runtime or infrastructure proof
- API docs and tests must carry evidence value, not just volume
- artifact-green does not imply runtime-green; if runtime smoke, started-service API execution, migration, SQL/persistence, or infrastructure evidence is absent, the verdict must state the exact ceiling instead of inferring readiness

OpenAPI / payload authority boundaries:

- optional UI compiled bindings are not global OpenAPI authority; they are frontend-lane evidence unless `require_frontend_contract` explicitly promotes them to a blocking frontend contract
- when `require_frontend_contract` is false, keep the backend OpenAPI surface complete from Phase-2 API contracts and do not shrink endpoints to the optional UI compiled-binding subset
- when `require_frontend_contract` is true, generated OpenAPI/types/client artifacts must state compiled-bindings authority and their operation counts must match the promoted compiled-binding contract
- payload typing review is scoped to backend implementation targets; frontend page helper `payload: unknown` is not backend implementation genericity
- `implementation_payloads_still_generic` is valid only when backend service/controller/repository targets still expose generic payload execution instead of typed contract-derived inputs

Quality backtrace rule:

When review finds a fake-green or weak generated artifact, use `Review -> Gate -> Red Test -> Generator Fix -> Dual-case Rerun -> Manual Review`.
Do not fix quality by editing one generated case output, adding named-case branches, weakening gates, or lowering assertions to pass.
Backtrace the reusable cause to generator, handoff, gate, prompt contract, runtime evidence, or verdict wording, then rerun at least two representative cases before promoting the rule.

## Iteration / Exit Rule

Treat Phase-3 loops as:

> `bounded execution/remediation loops`, not deep business or architecture thinking

- start another loop only when the current frozen slice still has unresolved execution truth, such as failing tests, contract drift, runtime/bootstrap gaps, mock-kernel dependence, missing persistence proof, or delivery-gate failures
- keep each loop bounded to the current work package, packet, or hardening surface; do not reopen unrelated topology or product-scope questions inside an implementation retry
- continue looping only while each round removes a concrete delivery risk or increases verification truth on the real runtime path
- stop and promote state when the relevant formal-state bar is actually met; do not keep looping once the remaining gap is only optional polish rather than runnable-delivery truth
- return upstream when the blocker is an upstream Phase-1/Phase-2 truth gap rather than an implementation defect
- mark the run `blocked` when the required runtime environment, contract baseline, or topology truth is unavailable, or when contract mismatch remains unresolved enough that honest implementation-ready claims cannot be made

Protocol labels `A`, `B`, and `C` below are internal Phase-3 control slices, not release versions.
They replace the older version-shaped labels while preserving the same runtime contract.

## A Phase Review Breakpoint

At official Phase-3 completion, present a review opportunity before treating the runnable delivery / handoff package as ready for Phase-4 validation.

The breakpoint must surface the Phase-3 output root, primary artifacts, runnable delivery value, core-path usability, implementation completeness, test meaning, runtime evidence, open `review-bound` items, claim ceiling, recommended next step, and minimum rerun / return boundary.

Show human-facing review actions in Chinese: `批准`, `带保留项批准`, `要求修改`, `要求返回`, `提供干预输入`, or `明确跳过审核`. Structured records may also preserve stable protocol keys such as `approved` or `return-requested`. New behavior or evidence must be recorded as input and rerun or remediated through Phase-3; do not silently patch final artifacts, lower assertions, or treat reviewer optimism as runtime proof.

## A Value-Bearing Runnable Closure

Phase-3 closure must be runnable value and evidence-backed behavior, not code or script completion.

Before promoting the Phase-3 package to Phase-4, state whether runnable delivery value, core-path usability, implementation completeness inside accepted P1/P2 truth, test meaning, runtime evidence strength, and downstream continuation value are strong enough for validation to consume. If P4 would still need to guess whether behavior is real, assertions are meaningful, or the runtime path actually works, return or keep the package review-bound instead of treating code volume, endpoint existence, generated runtime green, delivery-gate files, or script pass as closure.

The default P3 run must include `agentic-implementation-loop.json` and `agentic-implementation-loop.md`. These files are the reviewable Agentic value-loop surface; they do not replace strict-runtime proof, and strict-runtime proof does not replace their implementation-value judgment.

## B Agentic Test-First Generation Repair Loop

The default P3 run must also include `agentic-generation-quality-loop.json` and `agentic-generation-quality-loop.md`.

This loop is the B Agentic generated-quality surface. It selects concrete behavior units from `implementation-bindings.json`, attaches baseline refs, creates test obligations, emits code/test/evidence change packets, and keeps evidence-capped claims until runtime evidence and human quality review support a stronger statement.

Rules:

- Minimum depth is `L3: generation/change-loop intervention`.
- WAE / EDSP / SELA own decision placement.
- TVG is a generation value-gain tool, not a decision owner.
- At least one generated code, test, or evidence unit must change before B can claim generated-artifact quality gain.
- `script pass alone does not prove quality gain`; compare against v1.2.4 and A baselines and keep unresolved items review-bound.
- Do not use this loop to reopen P1 business truth, redesign P2 architecture, start C script slimming, or edit generated `/tmp` proof outputs by hand.

## P3 Agentic Repair Interrupts

The default P3 assessment must emit `agentic-repair-interrupt.json` and `agentic-repair-interrupt.md` next to `phase-verdict.json`.

Scorecard, delivery-gate, and human rough-review defects are repair triggers, not final-report-only findings. If a blocker or material rough-review defect appears, P3 must generate an Agentic repair packet before closeout language is raised.

Human rough-review actions stay Chinese-facing: `批准`, `带保留项批准`, `要求修改`, `要求返回`, `提供干预输入`, and `明确跳过审核`.

Rules:

- `要求修改`, `要求返回`, and `提供干预输入` are material repair interrupts when they identify runnable-delivery, business-correctness, test-meaning, runtime-proof, or P4-consumability defects.
- 大阶段完成后，由人工 Review 判定是否需要返工。Material human Review defects must include concrete defect records and become `human-review-module-rewrite` packets or upstream returns; do not place human feedback only in the final report.
- Each Agentic repair packet must state owner phase, defect source, repair route, code/test/evidence change-unit types, minimum rerun boundary, and claim ceiling.
- Workflow controls checkpoint order, packet shape, and rerun boundary; Agentic controls repair judgment; evidence caps claims.
- If the defect belongs to P1 or P2, route upstream with evidence instead of repairing source truth or architecture truth inside P3.
- If the defect belongs to P3, repair code, tests, runtime evidence, or handoff as needed, then rerun the smallest gate that can prove the claim.
- If the repair loop exhausts its bounded rounds, keep the formal state capped and do not treat final reports as the only output.
- The existence of `agentic-repair-interrupt.*` proves the repair surface exists; it does not prove material quality gain or strict-runtime closure by itself.

## B Semantic Invariant Repair

When P3 sees owner, aggregate, lifecycle, mutation-scope, or state-set drift, it must use source-supported semantic invariant records before generating blocking repairs.

Rules:

- A `source-supported semantic invariant` may create semantic-owner, semantic-aggregate, semantic-lifecycle-event, semantic-mutation-scope, or state-set RED tests.
- `review-bound source truth` must stay review-bound or return upstream; P3 must not invent owner, aggregate, lifecycle, or mutation truth locally.
- Semantic drift that is source-supported must become a `semantic-invariant-repair` packet with source operation id, invariant type, affected generated units, RED test targets, repair route, minimum rerun boundary, and claim ceiling.
- Generated unit tests should prove owner guards before repository access, such as wrong `expectedOwnerService` returning `forbidden` without calling repository methods.
- No generated `/tmp` output edits are allowed. Change reusable project logic, SKILL / runner / prompt / packet contracts, or scaffolding first, then regenerate outputs.
- GEO may validate the mechanism, but released behavior must not contain GEO-only hidden branches or case-tuned output patches.

## C P3 Script De-Weighting

Default P3 output should keep mandatory quality/evidence surfaces visible while moving diagnostic-only explanatory material out of the root package surface.

Rules:

- Protected B quality-floor surfaces stay mandatory: runtime smoke, started-service smoke, phase verdict, delivery gate, verification ledger, WP gate, full-targeted evidence, Agentic generation quality loop, repair interrupt, semantic invariant support, and evidence-capped closure language.
- P1/P2 are read-only upstream pressure-audit inputs inside C; do not modify P1 source-truth generation or P2 architecture generation from this slice.
- Diagnostic-only material may move under `.phase3-diagnostics/` when tests prove the canonical evidence path remains intact.
- `generated-runtime-positioning.md` is diagnostic in C and should be emitted as `.phase3-diagnostics/generated-runtime-positioning.md`, not as a root-level formal-state surface.
- Hard removal requires a separate classification record and focused tests proving P3 closure and P4 consumption do not read the removed surface.
- No generated `/tmp` output edits, GEO-only hidden branches, PetClinic-only hidden branches, or quality-floor downgrades are allowed.

### C.R1 P3 Aggressive Surface Profiles

When P3 aggressive slimming is enabled by the released generator, non-canonical root surfaces should move into profile directories while canonical evidence stays root-level.

Rules:

- `.phase3-diagnostics/` may contain diagnostic/support surfaces such as `generated-runtime-positioning.md`, `api-doc-consistency-report.md`, and `phase3-timing-report.json`.
- `.phase3-review/` may contain human/Agentic review Markdown such as `code-review-report.md`, `security-audit-report.md`, `test-obligation-matrix.md`, `test-obligation-audit.md`, and `test-richness-review.md`.
- Keep P4-consumed and canonical evidence root-level: `phase-verdict.json`, `phase3-delivery-gate.json`, `phase3-run-metadata.json`, `phase-mainline-scorecard.md`, `phase-acceptance-matrix.md`, `phase-3-acceptance-report.md`, `phase-3-execution-report.md`, `code-review-metrics.json`, and `mock-dependency-manifest.json`.
- Use the generated surface policy resolver instead of hard-coded root paths when reading profiled surfaces.
- This is a P3-only output-profile rule; do not infer P1/P2/P4 slimming from it without a separate work-control update.
- R-series slimming must end with a final human quality Review that checks generated artifact quality, evidence completeness, reviewability, and root/must-read reduction value against accepted baselines.
- Do not promote P3 slimming patterns to P1/P2/P4 before that Review passes with `slimming-pass-no-regression` or an explicitly accepted `slimming-pass-review-bound`.

### C.R2/R3 Strict-Runtime And Final Review

The aggressive P3 surface-profile pattern is accepted for P3 after strict-runtime proof and final Review, but it remains a P3-only rule.

Rules:

- `strict-runtime-pass with claim ceiling` requires release-packaged dual-case Phase-3 strict-runtime evidence, full-targeted evidence, runtime smoke, started-service smoke, and delivery-ready closure.
- `slimming-pass-no-regression` requires final human quality Review against accepted quality baselines, including generated artifact quality, evidence completeness, reviewability, and actual root/must-read reduction.
- Keep the claim ceiling explicit: R2/R3 prove quality-floor preservation and root/must-read reduction, not generated business implementation quality improvement.
- The P3 surface-profile pattern is eligible for future `v1.3.4` cross-phase consideration only after explicit work-control update and phase-specific consumer review.
- Do not automatically promote the P3 pattern to P1/P2/P4, do not move consumer-facing or operator-facing root surfaces merely to reduce count, and do not weaken P4-consumed evidence paths.

### C.R4 Slimming Success Patterns

Use C as a P3 pattern library, not as a mechanical cross-phase patch.

Rules:

- Slim only after a protected quality floor exists.
- Classify every candidate surface by consumer first: gate, P4, runtime closure, trace closure, handoff, operator review, diagnostic-only, or review-only.
- Prefer profile directories over deletion when a surface still carries diagnostic or review value.
- Add resolver coverage before moving paths that tools or downstream phases may read.
- Escalate evidence before no-regression claims: focused tests -> install-pack audit -> release-packaged candidate generation -> strict-runtime dual-case proof -> human Review.
- Do not chase root file count alone; strict-runtime evidence may legitimately add root surfaces.
- Cross-phase extension requires a separate work-control update and phase-specific consumer review.

## v1.3.5 Failed Route Residue

`WO-119E.R5` closed the v1.3.5 pre-generation synthesis route as `failed-route-not-promoted`. Do not continue R5-style patching. Do not open `WO-119F`.

Default Phase-3 mainline execution must not prepare `phase3-synthesis-brief.json` / `phase3-synthesis-brief.md`, must not generate `.phase3-review/phase3-synthesis-brief.json`, and must not inject `Synthesis intent` comments into generated service/test bodies. R4.09 found `Synthesis intent comments only`, which is failed-route residue rather than quality gain.

The old R4 synthesis boundary may remain only as explicit experimental evidence behind a non-default opt-in. It is not a release-facing mainline, not a quality-gain proof, and not a basis for WO-119F.

Rules:

- Workflow owns order, schema, file placement, and bounded handoff.
- Agentic synthesis must not be counted as progress if it only creates comments, sidecars, or reports.
- Evidence caps claims through source IDs, implementation/test targets, runtime evidence refs, strict-runtime gates, and later human Review.
- Do not revive R1 stage packets, R2 artifact compiler, `--agentic-artifact-compiler`, or any post-generation compiler route.
- Do not use GEO/PetClinic-specific hidden branches or hand-edit generated proof outputs.
- P1/P2/P4 synthesis expansion and P1 source-truth admission hardening require separate work-control updates.

## v1.3.6.2 P3 Module Synthesis Candidate

`--module-synthesis-bundle` is an explicit Phase-3 opt-in for `phase3-module-synthesis-bundle.v1`. It is a route-candidate mechanism, not the default mainline.

When supplied, the bundle may own exactly one selected API module's service, repository, and module unit-test file bodies. Workflow still owns phase order, source/P2 intake, path validation, assembly, evidence, runtime gates, and claim ceilings. Unselected modules stay on the default renderer path.

The bundle must be bound to the generic `phase3-module-authoring-context.v1` packet through `authoring_context_sha256`. That context packet is assembled from OpenAPI/runtime specs, behavior-card obligations, trace/source references, selected-module ownership, contract-test targets, and WAE / TVG / BTGSB method guidance. It is a general authoring sufficiency surface, not a GEO/PetClinic branch and not an error-type patch. If the hash is absent or stale, reject the bundle before generation.

This route must not be counted as success when it produces only comments, sidecars, reports, packet visibility, or post-generation payload text. Evidence must include `authoring-context.json`, renderer-bypass proof under `.phase3-review/module-synthesis/`, generated file substance, runtime/test status, and human Review before any value claim.

Do not promote the route beyond P3 or into default execution until GEO and PetClinic Gate 1 evidence exists and at least one strict-runtime proof or an honest direction-only closure has been recorded.

## WO-119F.15 v1.3.6.15 Agentic Module Implementation Brief

Default P3 backend generation must synthesize an in-memory `phase3-agentic-module-implementation-brief.v1` before service / repository / unit file write.

The brief is the default Agentic module implementation strategy surface. It consumes action-card rich context, Agentic semantic decisions, project implementation conventions, OpenAPI/runtime specs, and selected stack context. Agentic owns module purpose, operation grouping, aggregate/invariant model, service-flow strategy, repository-effect strategy, transaction/audit/auth/error posture, and unit-test strategy.

Workflow/scripts may assemble context, render files, place traces, run verification, record metadata, and cap claims. Renderer helpers must stay mechanical; they may handle syntax, imports, path placement, trace comments, runtime harness wiring, and minimum fallback only after evidence-backed failure classification. They must not restore renderer-local service-flow, repository-effect, or unit-test-intent defaults as the primary source of content truth.

If quality becomes unstable, classify the failure first as context insufficiency, Agentic judgment issue, renderer mapping issue, evidence issue, or environment issue. Only then may a minimum mechanical fallback be added, and it must be deletion-conditioned and forbidden from deciding business truth. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a default rich-context artifact, or revive F5/F6 selected-module gate stacks.

## WO-119F.16 v1.3.6.16 Action Card Direct Implementation Driver

Default P3 backend generation must synthesize an in-memory `phase3-action-card-direct-implementation-driver.v1` before service / repository / unit file write.

Action Card Direct Implementation Driver means Action Card obligations directly drive service/repository/unit generation. Service bodies consume service execution steps; repository bodies consume repository effect steps; unit tests consume unit assertion obligations. Failure mapping and audit/event posture also come from the driver when present.

F.13/F.14/F.15 are supporting inputs. They may enrich owner / aggregate / invariant interpretation, project language, naming/code conventions, and module grouping strategy, but they must not bypass or replace Action Card obligations as the primary business-obligation source.

The F.16 driver is non-persisted. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a replacement default rich-context artifact, or revive F5/F6 selected-module gate stacks. Evidence may prove direct consumption, runtime, quality score, and claim ceilings; it must not create business content.

## WO-119F.17 v1.3.6.17 Repository Audit Event Domain Sharpening

Default P3 backend generation must keep the F.16 Action Card direct-driver route and sharpen repository / audit / event semantics before file write.

The in-memory `phase3-action-card-direct-implementation-driver.v1` should synthesize repository domain effects, state transition effects, audit/event effects, and failure effect boundaries from Action Card obligations, operation semantics, and runtime failure specs. Agentic owns those domain-effect judgments; renderer helpers mechanically place them in service/repository/unit files.

The `WO-119F.17.2` follow-up also makes the driver consume existing `trigger_events`, `domain_event_models`, or `domain_event_catalog` before fallback event-name synthesis. Generated comments may expose `action-card-domain-event-modeling-effect` with producer, consumer, trigger, payload, timing, and idempotency. Do not create a new P2 event catalog, add a gate, or add a default persisted event-model artifact.

F.17 is not a performance optimization and not a P1/P2/P4 expansion. Do not restore `business-behavior-authoring-plan.json`, expand `action-card-execution-map.json`, add a replacement repository/audit/event rich artifact, revive F5/F6 gate stacks, or add case-specific branches. Evidence proves direct consumption, runtime floor, human Review score, and claim ceilings; it must not create business content.

## WO-119F.4 v1.3.6.4 TVG-gated selected-module synthesis

`WO-119F.4` keeps `--module-synthesis-bundle` explicit opt-in and P3 selected-module-only. It adds TVG-gated selected-module synthesis preflight rather than default route promotion.

The authoring context must expose `public_surface`, `behavior_obligations`, `evidence_obligations`, and `method_obligations` before a bundle can be treated as context-sufficient. The bundle must include `tvg_quality_loop` with `behavior-depth`, `evidence-depth`, `failure-depth`, a value-gain round, an exit gate, an Agentic exit audit, and `exit_state=agentic-exit-ready`.

Thin or missing-TVG bundles must fail before selected service/repository/unit-test file bodies are written. Failure writes `phase3-module-tvg-quality-audit.v1` and `phase3-module-rewrite-packet.v1` under `.phase3-review/module-synthesis/`; the rewrite packet is an upstream bounded Agentic rewrite instruction, not a generated-output hand edit.

TVG is a value-gain tool for generation quality, not the decision owner. Scripts only verify evidence shape: isolated-unit marker, repository-double marker, repository double/mock collaborator, repository call assertion, negative branch, repository-not-called assertion, and repository error translation or declared failure mapping.

Focused tests only prove the preflight is wired. Do not promote or otherwise not promote `--module-synthesis-bundle` to default, claim full P3 closure, claim material generated-artifact quality gain, expand to P1/P2/P4, or add GEO/PetClinic-specific branches without separate work control and dual-case runtime plus human Review evidence.

## WO-119F.5 v1.3.6.5 Module behavior plan selected-module audit

`WO-119F.5` keeps `--module-synthesis-bundle` P3-only, selected-module-only, explicit opt-in, and non-default. It closes the F.4 gap where unit-test richness improved but selected service/repository bodies could still remain thin generic delegation.

When a `phase3-module-authoring-context.v1` is available, the scaffolder derives `phase3-module-behavior-plan.v1` as `module_behavior_plan` from operation steps, operation semantics, request required fields, failure cases / error codes, state transitions, invariants, persistence effects, transaction rules, audit effects, and evidence obligations. The review evidence must include `.phase3-review/module-synthesis/module-behavior-plan.json` alongside `tvg-quality-audit.json` and, on failure, `module-rewrite-packet.json`.

The behavior-depth audit must inspect selected service and repository bodies against `module_behavior_plan`. A bundle with non-empty behavior obligations must fail before selected file write if service/repository bodies show only generic delegation. Missing behavior signals include `service_behavior_flow`, `service_contract_validation`, `service_state_conflict_policy`, `service_invariant_guard`, `service_audit_event`, `repository_decision_load`, `repository_invariant_persistence`, `repository_audit_effect`, and `repository_readback_or_runtime_bridge`.

Failure produces a bounded rewrite packet that instructs Agentic regeneration of the selected service/repository behavior depth from `module_behavior_plan`. It is not a full workflow rerun, not a generated-output hand edit, and not permission to weaken `test-obligation`, `test-richness`, runtime proof, or formal claim ceilings.

Focused tests prove `module_behavior_plan` derivation, service/repository behavior-depth audit, evidence-path emission, and failure-before-file-write only. `WO-119F.5R` later accepted only a bounded selected-module behavior-depth gain over F.4 after R6 release-packaged GEO/PetClinic P3 strict-runtime passed and Review compared the selected modules against C / v1.2 baselines.

Do not claim broad generated-artifact quality gain, C / v1.2 baseline parity, route promotion, P1/P2/P4 applicability, material project slimming, or broad `WO-119F / v1.3.6 Agent-led Mainline Full Reconstruction` from F.5 evidence. The route remains explicit opt-in, selected-module-only, and non-default.

## WO-119F.6 v1.3.6.6 Obligation consumption audit

`WO-119F.6` keeps `--module-synthesis-bundle` P3-only, selected-module-only, explicit opt-in and non-default. It closes the F.5 gap where `module_behavior_plan` could carry useful operation obligations while generated service/repository/unit bodies still substituted generic profile semantics.

When the selected-module route is used, exact obligation consumption is required before selected file write. The quality evidence must include `phase3-module-obligation-consumption-audit.v1` at `.phase3-review/module-synthesis/obligation-consumption-audit.json` alongside `module-behavior-plan.json`, `tvg-quality-audit.json`, and any `module-rewrite-packet.json`.

The audit is an evidence bridge, not a business-truth generator. It may compare generated bodies against `phase3-module-behavior-plan.v1` for operation-specific owner, required context, declared audit event, read-only/no-mutation, repository decision-load, invariant persistence, and read-back/runtime bridge consumption. It must not invent missing product truth, patch generated proof outputs by hand, add named GEO/PetClinic branches, or weaken runtime/test obligations.

generic profile substitution must fail. If a generated body replaces a source-backed owner, audit event, required field, or read-only boundary with a generic `OperationProfile` value or invented semantic, the route must emit a bounded rewrite packet with operation id, exact source obligation, expected surface, observed failure, and forbidden actions.

Focused F.6 tests only prove the evidence bridge and failure-before-file-write behavior. Do not claim broad generated-artifact quality gain, baseline parity with C / v1.2.4, default route promotion, P1/P2/P4 applicability, or material project slimming until release-packaged dual-case strict-runtime evidence and human Review support that stronger claim.

## WO-119F.7 v1.3.6.7 Route withdrawal and residue governance

F5/F6 selected-module synthesis is withdrawn as a mainline route candidate. It remains historical/diagnostic evidence only unless a retained surface is explicitly classified by the F.7 residue map.

Any retained selected-module machinery is residue-governed, explicit opt-in, internal/experimental, and non-default. This includes `--module-synthesis-bundle`, `phase3-module-synthesis-bundle.v1`, `phase3-module-tvg-quality-audit.v1`, `phase3-module-behavior-plan.v1`, `phase3-module-obligation-consumption-audit.v1`, `.phase3-review/module-synthesis/*`, and selected-route tests.

Do not continue by adding another selected-module audit or gate as a substitute for Agentic generation judgment. Future work must first name the generation boundary where workflow stops deciding content truth, name old script-control surfaces to delete or demote before implementation starts, and explain why the next action is not another gate-stacking route rescue.

Default selected-module synthesis remains not allowed. Do not claim broad generated-artifact quality gain, C / v1.2.4 baseline parity, material project slimming, P1/P2/P4 applicability, route promotion, production authorization, release approval, or broad `WO-119F / v1.3.6 Agent-led Mainline Full Reconstruction` from F5/F6 evidence.

## WO-119F.8 v1.3.6.8 P3 Agentic body mainline accepted boundary

The default P3 backend mainline now moves service/repository/unit body authoring forward before file write. Workflow still controls phase order, source/context assembly, file placement, runtime evidence, and claim ceilings. The Agentic body authoring kernel shapes default service/repository/unit bodies from OpenAPI/runtime specs, behavior-card/source context, and operation evidence obligations before strict evidence runs.

This is not selected-module route promotion. `--module-synthesis-bundle`, `module_behavior_plan`, TVG quality audit, and obligation-consumption audit remain F5/F6 residue unless a future work order explicitly reuses them. Do not solve F.8 quality by adding another post-generation gate or audit. If quality work starts adding F5/F6-style gates instead of moving generation control forward, treat it as route drift.

Default generated service bodies should expose operation-specific validation, decision load, state/conflict policy, invariant persistence, audit/read-back, declared failure mapping, and frozen response mapping. Default generated repositories should expose decision-load, invariant persistence, read-back/runtime bridge, and operation-specific runtime execution surfaces. Default module unit tests should still prove repository doubles and behavior meaning.

For detail-read and list-read operations, default service/repository bodies must remain read-only. In other words, detail-read and list-read operations must remain read-only. They may validate inputs, load/project existing state, and map frozen responses; they must not create durable persist/audit/write paths such as list/detail/get `persist*`, `append*`, or `write*` flows. Write/command operations still retain persistence, audit, invariant, and runtime bridge behavior.

F.8 release-packaged R2 evidence accepted this boundary after GEO and PetClinic P3 strict-runtime passed from the default route with selected-module mode disabled. The accepted F.8 claim is bounded: default P3 body authoring moved forward, read/list pseudo-write burden was reduced, and the strict-runtime floor held. Do not claim broad material generated-artifact quality gain, C / v1.2.4 baseline superiority, P1/P2/P4 applicability, production authorization, or release approval from F.8 evidence.

## WO-119F.10 v1.3.6.10 P3 business behavior authoring plan

For `v1.3.6.10`, `business-behavior-authoring-plan` was the default P3 mainline pre-file-write authoring context for service/repository/unit business bodies.

Workflow supplies order/context/evidence: phase order, OpenAPI/runtime spec assembly, P1/P2 source bridge loading, file placement, strict-runtime execution, and claim ceilings. Agentic/default authoring owns business behavior plan: operation intent, required context, read/write semantics, state/conflict policy, repository effects, audit/event effects, semantic owner, response mapping, and unit-test obligations before renderer file write. Evidence caps claims through focused tests, GEO + PetClinic strict-runtime, and human Review; script pass or plan existence is not generated-artifact quality proof.

Selected-module bundle remains non-default. Do not pass `--module-synthesis-bundle`, promote selected-module synthesis, revive F5/F6-style gate stacks, or solve F.10 quality by adding post-generation audits instead of moving business behavior authoring before generation.

## WO-119F.11 v1.3.6.11 P3 action-card-centered mainline

Default P3 code generation is action-card-centered. The required spine is:

`P2 component-action-card-obligation-matrix -> P3 implementation action cards -> action-card execution map -> service/repository/unit code`.

`business-behavior-authoring-plan` must not operate as a second business-truth layer. When `action-card-execution-map.json` exists, the default mainline must not emit `business-behavior-authoring-plan` as a persisted review artifact or truth surface; any compatibility projection must stay in-memory and subordinate to the action-card spine. Renderer helper code may perform mechanical lookup, merge, and error mapping, but it must not independently infer business owner, state, audit, repository effect, or test obligation semantics outside the action-card spine.

Generated service/repository/unit outputs should be reviewable back to `action_card_id`, action-card step / operation, ACD level, source refs, and required tests. Do not delete action cards to reduce surface area; slim duplicated plan/helper narration around the action-card spine. Do not restore F5/F6-style selected-module gate stacks, pass `--module-synthesis-bundle`, hand-edit generated `/tmp` outputs, or claim material generated-artifact quality gain before GEO + PetClinic strict-runtime and human Review support it.

## WO-119F.12 v1.3.6.12 P3 pointer-only action-card surface

Default P3 keeps the F.11 action-card spine, but the persisted `action-card-execution-map.json` is now a pointer-only action-card surface. `source_refs / required_tests must not be persisted in default map`; those rich generation details belong to the in-memory action-card rich context.

The rich context stays in-memory for business-behavior compatibility projection and service/repository/unit scaffolding. do not restore business-behavior-authoring-plan.json, do not restore the F.11 heavy execution map as the default review surface, and do not add a new default heavy rich-context artifact as a replacement.

## WO-119F.13 v1.3.6.13 P3 Agentic semantic authoring

Default P3 generation must create an in-memory Agentic semantic decision before service/repository/unit file write.

Workflow assembles action-card, contract, source, and runtime context; places files; and runs evidence commands. Agentic owns owner / aggregate / invariant / value-rule / failure-path / test-intent judgment. Templates / TVG may use `docs/phases/phase-3/p3-agentic-semantic-authoring-question-set-v0.1.md` to ask required semantic-depth questions, but must not provide default answers. Evidence / Gates prove claims and cap formal state only.

The Phase-3 runner exposes `--thinking-value-gain-mode off|full-use` and
`--thinking-value-gain-output-profile insight_dense | balanced | coverage_rich`.
Keep mode `off` unless a work item explicitly enables full-use; when enabled,
prefer the default `coverage_rich` profile for long implementation handoff /
Action Card quality work. TVG is not the decision owner and must not replace
the action-card spine, Agentic semantic judgment, or runtime evidence gates.

Do not restore `business-behavior-authoring-plan.json`, do not expand the pointer-only `action-card-execution-map.json` back into a rich default artifact, and do not add a replacement default rich-context artifact. `not-declared`, `review-bound`, and generic `business invariants` are not content truth. If context is insufficient, keep the item review-bound or return upstream instead of letting renderer defaults decide semantics.

## WO-119F.14 v1.3.6.14 P3 project implementation conventions

Before default service/repository/unit generation, P3 must synthesize in-memory project implementation conventions from P2 project-language handoff, `tech-stack-decision.yaml`, action-card rich context, and optional UI/UX surface context.

The convention object guides naming, code, design, test, and optional UI/UX posture before F.13 semantic decisions. It must not become a persisted replacement rich artifact. Evidence / Gates may report mechanical owner/aggregate residue, convention drift, and claim ceilings; they must not generate naming answers or restore F5/F6-style gate stacks.

## P3 Checkpoint Repair Loop

When consuming `agentic-repair-interrupt.json`, start from the existing Phase-3 output root. Do not re-enter the release dual-case runner as the repair path, because that regenerates P1/P2/P3 and turns repair into a full rerun.

Use `scripts/phase3/agentic_repair_loop.py prepare` to copy the current P3 root into a repair workspace, preserve the original generated output, and split packets into local `repair-in-phase` work versus upstream returns. Use `run-targeted-gate` from the repair workspace after Agentic code / test / evidence edits. This command reruns the P3 backend targeted gate only; it must not run Phase-1, Phase-2, or `scripts/release/run_release_dual_case_eval.py`.

Critical-targeted mode is the default fast repair smoke. If the command passes but the work-package gate remains incomplete, classify the result as `sample-pass-review-bound`, not P3 closure. Use full-targeted or stricter evidence plus `--refresh-closure` before claiming a repair has closed P3 blockers, because gate evidence alone does not rewrite the formal `phase-verdict.json`.

The release dual-case runner remains useful for candidate inclusion, regression, and release proof. It is not the default mechanism for in-flow P3 repair.

## Runtime References

Use these release-facing references when applying the A Phase-3 control model:

- `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
- `docs/governance/v1.3-product-flow-control-boundary-v0.1.zh-CN.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.zh-CN.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.zh-CN.md`
- `docs/phases/phase-3/p3-value-bearing-runnable-delivery-v0.1.md`
- `docs/phases/phase-3/p3-value-bearing-runnable-delivery-v0.1.zh-CN.md`

Release proof / version closeout should use `scripts/release/run_release_dual_case_eval.py` with the default Phase-3 strict proof profile: `strict-runtime`, toolchain install, and runtime smoke. Use `if-ready` only as an explicit diagnostic downgrade and do not treat it as release closeout evidence.

## Release Validation Rule

When validating the released Phase-3 skill itself, use an isolated workspace/session with only the release bundle loaded.
Do not rely on repo-local `AGENTS.md`, authoring-repo defaults, or incidental workspace state to fill missing runtime instructions.
For the official retained `GEO + PetClinic` release verification flow, prefer `scripts/release/run_release_dual_case_eval.py` from the built release pack/bundle instead of running directly inside the authoring repo.

## Required Inputs

Read these first:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- `docs/phases/phase-2/phase-2-completion-and-phase-3-guidance-v0.1.md`
- the case `engineering-spec-pack.md`
- the case `phase-3-implementation-entry.md`

## Execution Sequence

1. Freeze the implementation topology from Phase-2.
   Default stance: `deterministic + agent-ready`.
   Do not switch to `agent-native` unless Phase-1 and Phase-2 explicitly define that runtime.
2. Generate the S01 contract pack:
   - `tech-stack-decision.yaml`
   - `openapi.yaml`
   - `db/migrations/*.sql`
   - project scaffold + CI/dev baseline
   - real runtime baseline: backend entrypoint, runtime scripts, persistence wiring, env contract, Dockerfile, compose files
   - when the stack ships `Dockerfile` / compose assets, treat container startup as the default runnable-delivery proof path rather than an optional extra
   - toolchain bootstrap report / install command
   - shared types / client skeleton
   - `phase-3-trace-registry.json`
   - UI prototype input resolution:
     - if Phase-2 already provides a human-refined UI prototype input, keep it as the primary UI source
     - default `v1.2` mainline is `backend-first`; do not activate fallback UI generation unless the frontend lane is explicitly requested or frontend contract evidence is explicitly required
     - if the frontend lane is explicitly active and prototype input is missing, generate a fallback UI prototype pack before implementation starts (minimum: `ui-prototype-fallback.md`, `ui-wireframes.html`, `ui-api-mapping.json`, `ui-ia-contract.json`)
     - when the frontend lane is active and both prototype input and frontend stack choice are missing, activate the default fallback frontend stack (`React + Vite + Ant Design + React Router + TanStack Query + React Hook Form + Zod`) and record it in artifacts
     - mark fallback origin explicitly in run metadata so it is not confused with a human-approved design
     - whenever the frontend lane is active, the following Phase-1 artifacts MUST be consumed as binding constraints rather than optional references:
       - P1 `prototype-spec.md` §4 Page Map: authoritative page names, routes, and blueprint types
       - P1 `prototype-spec.md` §6 Page Briefs: page goals, core actions, and state variants
       - P1 `prototype-spec.md` §9 Prototype Generation Constraints: disqualifying rules
       - P1 `prototype-prompt-pack.md`: supplementary interaction and visual intent when it exists
     - the fallback generator MUST use P1 page_map page names as route slugs, not P2 `primary_surfaces` labels, whenever prototype-spec evidence exists
     - the fallback generator MUST propagate `page_blueprint_type` from P1 into `ui-ia-contract.json`
     - `ui-ia-contract.json` fields must carry visibility tags so agent-internal metadata cannot be mistaken for user-facing copy
3. Bootstrap the workspace toolchain before real execution:
   - verify `node` + `pnpm`
   - verify Docker engine + Docker compose are installed and reachable
   - for server/web lanes, if Docker is missing, compose is missing, or the daemon is unavailable, refuse to continue those runtime-validated lanes on that environment
   - when Docker/compose assets are emitted, provide a compose-specific env example whose DB/cache URLs use container-internal service names; do not rely on host-local `.env.example` values for container startup
   - if the optional dispatch / packet lane is active, emit `runtime-environment-ledger.json` for packet/lane runtime requirements; if a packet runtime is missing, allow only static implementation progress and refuse verified / implementation-ready / delivery-ready claims for that lane
   - install workspace dependencies when `node_modules` is absent
   - when runtime closure is the requested objective, use strict runtime mode so missing `node_modules`, skipped install, or unreachable Docker daemon remains a blocker instead of a soft warning
   - do not interpret `command not found` as an implementation failure
4. Generate the S02 failing test pack:
   - schema / migration tests
   - contract tests as the primary frozen-interface verification surface
   - for backend/server lanes, contract tests must be designed to run against a real started HTTP service once the runtime environment exists; runtime-test-kit or in-memory helpers may bootstrap scaffolding but do not satisfy the final backend interface proof bar
   - each public operation must include an API Docs consumer contract test: build the request only from the OpenAPI-derived payload/parameters and execute it against the backend boundary
   - behavior-card-enriched payload tests may remain, but they must not be the only happy-path contract proof
   - `test-obligation-audit.json` must flag missing pure OpenAPI consumer tests, missing backend unit tests, and weak SQL transaction/reentry evidence before formal state is raised
   - scenario tests
   - scenario scaffolds for core happy-path chains should add invalid-request, permission, and conflict variants when those errors are documented by the bound operations
   - replay tests
   - unit test baselines bound to owned backend/frontend targets
   - database verification planning for backend lanes must include real migration execution plus SQL-backed read/write or state-transition proof against the chosen database engine; schema-shape-only checks are not enough for final runnable claims
   - SQL tests must prove restore/reentry and rollback discipline where a database is claimed; a one-shot insert/read does not satisfy the final persistence evidence floor
   - backend contract tests and SQL/persistence tests must both map back to Phase-1/Phase-2 user flows, contracts, failure paths, and state transitions instead of becoming detached technical-only checks
   - `test-coverage-plan.md`
   - `test-trace-matrix.json`
   - do not let provisional scaffold green be interpreted as implementation completion
5. Only then start S03 implementation.
   Default `v1.2` mainline is backend-first:
   - implement the backend delivery package directly from the frozen contract pack, scaffold, and failing tests
   - do not enable packet / wave / dispatch / worker-cycle complexity unless the optional multi-worker lane is explicitly requested
   If the optional multi-worker lane is active:
   - generate per-WP execution packets, a machine-readable wave plan, and lane-specific worker input packets first so each worker starts from a bounded packet instead of the full handoff
   - when you need to materialize execution, use a packet runner for one bounded worker packet or a dispatch runner for the current ready queue, rather than improvising directly from the whole handoff
   Generated runtime adapters may help bootstrap verification, but they must not remain the primary backend execution path of a completed packet.
   For backend/server lanes, verification should be layered in this order once the environment exists: migration execution -> SQL/persistence verification -> real service-boundary contract/scenario verification.
   S03 gate resolution must scan repository/adapter execution paths for `generated-runtime`, `operation-support`, `runtime-support-kernel`, or equivalent mock-kernel imports; if core CRUD still depends on them, cap the state below `implementation-ready`.
   S03 output must also emit `mock-dependency-manifest.json` when any mock-backed execution path remains.
6. Finish with S04 hardening:
   - code review
   - security audit
   - API docs
   - deployment / acceptance / handoff
   - runtime startup, container build, and environment/bootstrap evidence
   - compose local-validation command should reference the compose-specific env example explicitly, instead of requiring operators to infer env vars through retry
   - default delivery proof should include `docker build`, `docker compose up`, migration execution, health/readiness evidence, and minimal authenticated started-service API smoke when Docker assets exist; otherwise require an explicit equivalent runtime-validation contract
   - final delivery gate resolution

## Formal States

Use these states explicitly:
- `foundation-ready`: S01/S02 and initial execution scaffolds are frozen; implementation may start
- `implementation-in-progress`: implementation has started but S03 gate is not fully green
- `implementation-ready`: runnable implementation code exists within the verified development / pre-production boundary, the runtime entrypoint is startable, build + lint + typecheck + backend targeted interface evidence + backend unit tests are green, and any remaining frontend verification gap is explicit Phase-4 follow-up rather than hidden debt
- `delivery-ready`: S04 audit/docs/deploy/trace/acceptance are all green within the verified development / pre-production boundary and the package includes a real deploy/start path rather than build-only scaffolds
- `delivery-ready` is stricter than `implementation-ready`: if the case ships Docker assets, containerized runtime evidence is the default proof surface, not an optional appendix
- packets/lane entries without their required runtime validation environment may still progress through static implementation work, but their ceiling remains below verified / implementation-ready / delivery-ready until that environment exists

For backend/server lanes, do not use `implementation-ready` or `delivery-ready` unless all of the following are true:
- backend interface verification hits a real started service boundary rather than only generated runtime helpers or in-process stubs
- the chosen database engine has real migration execution evidence
- at least one real SQL-backed persistence path per backend work-package family has write/read or state-transition proof
- persistence invariants that matter to the packet, such as uniqueness or relational integrity, are verified through the real database path when applicable
- those SQL/persistence proofs are traceable to the P1/P2 use-case/state model and are executed before the final service-boundary verification claim for that backend slice

For frontend/web lanes, do not use `implementation-ready` or `delivery-ready` unless all of the following are true:
- Phase-2 human prototype input exists, or a Phase-3 fallback prototype pack has been generated explicitly as the default input
- the delivered UI is not a reachability-only placeholder page; all core pages/routes from the frozen Phase-2 or fallback UI IA contract must exist with basic operable behavior
- the run records whether UI design was human-authored or fallback-generated, plus the resulting validation boundary

Treat unit-test coverage as a secondary quality gate:
- prefer isolated unit tests that align to P2 module/function boundaries
- when coverage is collected, use it to pressure weak AI-authored unit suites toward better line/function/branch depth
- Phase-3 acceptance/execution/handoff reports should carry the collected coverage data when available, and should mark it explicit as missing rather than silently dropping it when unavailable
- do not let unit coverage substitute for real migration, SQL/persistence, or started-service verification evidence

Do not call Phase-3 complete before `delivery-ready`.

## Required Scripts

Default backend-first mainline:
- `scripts/phase3/esp_to_openapi.py`
- `scripts/phase3/esp_to_migration.py`
- `scripts/phase3/phase3_stack_decision.py`
- `scripts/phase3/phase3_project_scaffold.py`
- `scripts/phase3/phase3_toolchain_bootstrap.py`
- `scripts/phase3/openapi_to_types.py`
- `scripts/phase3/api_client_scaffolder.py`
- `scripts/phase3/schema_test_scaffolder.py`
- `scripts/phase3/contract_test_scaffolder.py`
- `scripts/phase3/scenario_test_scaffolder.py`
- `scripts/phase3/replay_test_scaffolder.py`
- `scripts/phase3/test_trace_matrix_builder.py`
- `scripts/phase3/phase3_implementation_scaffolder.py`
- `scripts/phase3/phase3_delivery_gate.py --mode delivery-handoff`
- `scripts/phase3/phase3_runtime_smoke.py`
- `scripts/phase3/phase3_started_service_smoke.py`
- `scripts/phase3/phase3_quality_check.py`
- `scripts/phase3/phase3_delivery_gate.py`
- `scripts/phase3/run_phase3_first_version.py`

Optional lanes:
- frontend fallback lane:
  - `scripts/phase3/run_phase3_first_version.py --enable-ui-fallback`
- multi-worker / dispatch lane:
  - `scripts/phase3/phase3_dispatch_runner.py --packet <packet-id>`
  - `scripts/phase3/phase3_dispatch_runner.py`
  - `scripts/phase3/phase3_dispatch_runner.py --mode wp-gate-cycle`
- hardening / side review lane:
  - `scripts/phase3/phase3_delivery_gate.py --mode api-docs`
  - `scripts/phase3/phase3_delivery_gate.py --mode code-review`
  - `scripts/phase3/phase3_delivery_gate.py --mode security-audit`
  - `scripts/phase3/phase3_delivery_gate.py --mode coverage-collection`
  - `scripts/phase3/run_phase3_first_version.py --mainline-stage bootstrap`

If those outputs drift from Phase-2 truth, treat the run as blocked until the contract mismatch is resolved.

## Output Boundary

Official Phase-3 delivery should preserve:
- contract pack
- failing test pack
- implementation outputs
- audit outputs
- execution report
- trace registry final state
- runtime environment ledger
- `mock-dependency-manifest.json`

Final completion claim requires:
- runnable implementation code
- an executable runtime entrypoint and startup command for the chosen stack
- real persistence/migration wiring for the chosen backend path
- runnable targeted interface evidence (`contract/scenario/replay`) as the primary verification surface, with backend interface truth green
- for backend/server lanes, runnable targeted interface evidence must traverse the real started service boundary declared by the stack; in-memory contract shims are not sufficient as final proof
- runnable backend unit tests for non-trivial service/domain logic, with required gates green
- for database-backed backend lanes, runnable delivery proof must include real migration execution and real SQL-backed persistence verification, not only schema-shape tests or generated-runtime record assertions
- mock-backed core CRUD paths, auth downgrades, and missing core frontend routes must remain explicit and must block `implementation-ready` / `delivery-ready` claims
- frontend unit/component and scenario/replay evidence should be executed where relevant; any remaining gap must stay explicit as Phase-4 follow-up rather than being silently ignored
- structured verification evidence for targeted tests; exit-code-only green is not enough
- Dockerfile / compose assets that start services instead of only building artifacts
- when Docker assets exist, runnable delivery evidence should be captured against that containerized environment by default; alternative runtime forms must be explicitly justified
- documented server-side bootstrap, image build, and runtime smoke expectations
- final audit/doc/deploy assets
- a `delivery-ready` result from the delivery gate

For the first Phase-3 foundation package, prefer:
- `scripts/phase3/run_phase3_first_version.py`
- for runtime-closure validation, use `scripts/phase3/run_phase3_first_version.py --mainline-verification-mode strict-runtime`; this attempts install, blocks skipped toolchain states, runs full targeted SQL / contract / scenario / replay backend evidence by default, runs Docker runtime smoke, and requires `started-service-smoke-report.json` before delivery-ready can be claimed

Runtime-cost expectation:
- Phase-3 strict-runtime is expected to be the longest lifecycle validation segment. Retained v1.4/v1.4.1 dual-case proof evidence showed P3 at about `96%` of recorded phase-step time because it proves implementation behavior, not only generated document structure.
- The main cost driver is full-targeted SQL / contract / scenario / replay evidence, especially contract-heavy API / DB suites that repeatedly restore runtime state between tests. Docker image build / compose startup is a secondary runtime-smoke cost, not the main P3 wall-clock driver.
- RestoreV2 may optimize the generated backend test harness by using an observable baseline-fixture restore path with per-stage `duration_ms` reset events. This is a runtime-state restoration optimization only: it must keep the same SQL / contract / scenario / replay evidence, must fall back to legacy truncate+seed restore when fixture restore is unavailable or fails, and must not be described as a lower-cost replacement for strict-runtime proof.
- RestoreV3 may optimize first-clean-baseline cost with a run-scoped Postgres template database and worker database clone path. It must keep worker database isolation, full-targeted evidence, V2 baseline-fixture restore, per-stage reset events, and fallback to the V2 rebuild path. Operators may set `PHASE3_TEMPLATE_DATABASE_RESTORE=0` to disable template clone during rollback diagnostics.
- RestoreV4 may cache baseline-fixture restore plans after capture to avoid repeated column and sequence metadata queries. It must still perform full truncate, baseline insert, sequence synchronization, and fallback on each restore path; do not treat plan caching as compensating-operation restore.
- When `PHASE3_VITEST_MAX_FORKS=1`, the generated Vitest config should enter low-resource single-fork mode so multiple test files share one fork during serial diagnostics. This reduces repeated first-baseline rebuilds without changing the default parallel mode or reducing strict-runtime evidence.
- Generated compensating-operation restore（反操作恢复）belongs to a later high-confidence optimization lane. Do not silently replace full scenario restore with generated compensating operations until before/after restore verification and fallback behavior are proven.
- Use `--validation-level fast` or `--validation-level focused` for diagnostics and narrow repair checks only; these run critical targeted evidence and do not auto-run runtime smoke unless `--run-runtime-smoke` is explicitly requested. Do not lower strict-runtime evidence, skip full-targeted evidence, skip runtime smoke, or treat a fast-path pass as `delivery-ready` / release-proof closure.
- 中文用户提示应优先使用：快速验证、聚焦验证、严格全量验证、全量目标测试、运行冒烟验证、启动服务冒烟验证、声明上限、交付就绪、发布证明。默认迭代可以先做快速验证或聚焦验证，避免很多必要场景每次都跑严格全量验证；但声明上限必须明确低于交付就绪 / 发布证明。

For runtime execution after the foundation exists, prefer:
- `scripts/phase3/phase3_dispatch_runner.py --packet <packet-id>` for one selected packet; its packet execution kernel now lives in `scripts/phase3/worker_packet_runner.py`, and still owns structured verification command execution, cumulative verification-ledger accumulation, and runtime dispatch refresh
- `scripts/phase3/phase3_dispatch_runner.py` for the current dispatchable queue, or `--repeat-until-stalled` when you need the queue to keep advancing wave by wave without manual re-entry; after execution it should refresh final trace closure, acceptance/execution reports, and the delivery gate
- `scripts/phase3/phase3_dispatch_runner.py --mode wp-gate-cycle` to convert real test/build/lint/typecheck results into wave-unlocking runtime state

Do not present Phase-3 as complete if the repository only contains foundation scaffolds or generated-runtime passthrough code without visible implementation and verification evidence.
