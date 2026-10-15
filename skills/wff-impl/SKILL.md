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

Generation governance: `docs/governance/bounded-generation-run-governance-v1.md` (中文：`docs/governance/bounded-generation-run-governance-v1.zh-CN.md`). It bounds section generation and review without weakening factual runtime evidence.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- a completed Phase-2 handoff exists
- the case has an Engineering Spec Pack and implementation entry artifact
- the goal is runnable delivery with tests and evidence

Do not use when:
- no admitted frozen upstream input can be identified; declared content gaps are handled by P3 decisions
- the task is a tiny isolated code edit
- the user only wants post-implementation review or validation

## Core Rules

1. Treat Phase-2 contracts, topology, data model, API contracts, and work packages as frozen input.
2. Verify `p2-agentic-architecture-authority.json`, its application receipt, exact disposition ledger, semantic union, and the accepted P2 architecture decision resolved through the cross-phase surface policy (the current generated location is `.phase2-evidence/p2-agentic-architecture-decision.json`). Do not assume a root-level decision path or reconstruct the decision from downstream authority. If product/architecture truth is unresolved, classify T0/T1/T2 and use a recorded gap decision where required. If P3 evidence only sharpens implementation precision without contradicting frozen P1/P2 truth, record a P3 Authority Delta with `applied_upstream=false` and defer any upstream reconciliation until after P3 rather than mutating/rerunning upstream mid-cycle.
3. P3 has a strict pre-code order: `S1A Action Card generation -> S1B semantic convergence -> S2 Agentic implementation authority -> S3 code/test realization`. Before S2, require the authority-bound Action Card semantic-convergence report to pass with zero conflicts and preserve the full P2 component/contract/P1-trace denominator, aggregate/writer/topology truth, applicable NOR/state/failure/dependency context, accepted durable persistence command/identity/carrier/writer/replay truth, **terminal-role / visible-business-data / denial authority**, project guardrails, and claim ceilings. `system-continuation` operations must remain explicitly non-consumer rather than silently acquiring a terminal role. The S2 candidate must digest-bind that exact S1B card set, cover every Action Card component through direct operation/non-operation slices, keep project guardrails as context rather than fake component ownership, and prohibit invented service/aggregate identities. Only one current-snapshot accepted host-Agent S2 decision may authorize S3; candidate plans, Action Cards, templates, and deterministic enrichment are not implementation authority.
4. Generate or preserve failing tests before implementation.
5. Implement by bounded work package or packet, not by broad opportunistic coding.
6. Keep backend-first as the default mainline. Frontend, dispatch, hardening, and support lanes are optional unless explicitly activated.
7. Consume trace authority from `wff-base-traceability-management` and P2 bridge artifacts before claiming behavior/action-card source closure.
8. Preserve one exact tuple per accepted slice: `P2 contract + operation/non-operation realization + P3 implementation decision + code target + test/runtime evidence + confirmed Trace`. Shared files/tests may serve several tuples but cannot merge their identities.
9. Separate backend/runtime diagnostic, semantic realization, Human/AI review, and overall claim. A diagnostic score or scaffold pass cannot produce an overall PASS while semantic blocking is nonzero.
10. Cap formal state by the weakest missing semantic, runtime, infrastructure, UI, manual, or external evidence.
11. When semantic-consistency surfaces are present, do not trust persisted `semantic-commitment-union.json` by self-digest alone. Rebuild it from the accepted P1/P2 authority chain and authored P2 disposition ledger. Each exact-realization-required commitment must bind the same P2 contract and operation to the accepted P3 decision, implementation targets, tests/runtime evidence, and confirmed Trace, or remain return/review-bound. P3 must not satisfy one contract with another contract's same-named operation.
12. `p3-authority-delta-ledger.json` is a P3-local deferred-reconciliation sidecar, not a second canonical authority. Every delta must bind one P3 slice, preserve frozen upstream (`applied_upstream=false`), and stay `deferred-post-p3`. Product ambiguity may be resolved locally only through the gap-decision protocol. T0/T1 preserve explicit upstream facts; a T2/conflict/infeasible decision may locally supersede named facts with provenance and a claim ceiling, while frozen upstream bytes remain unchanged.
13. P3 must maintain the fixed project-level human knowledge artifact `<project-artifact-root>/p3-realization-decisions.md`, governed by `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md`. The machine Authority Delta ledger remains canonical; the Markdown must bind the same P3 decision and delta digest, retain every material realization decision (or explicitly index it as `implementation-only`), and always state that PRD/ESP backfill was not performed. Even when the canonical delta ledger is empty, the fixed Markdown must exist and explicitly state that no material realization decisions were added beyond frozen P1/P2 authority. This artifact is human/project knowledge for later P3/P4/change work and optional EKRI ingestion, not a Human Audit publication and not an upstream authority rewrite.

## T0 / T1 / T2 and one-directional gap decisions

T0 is an implementation detail that leaves business meaning unchanged; P3 decides and records material choices. T1 is a choice inferred from explicit P1/P2 facts; record `id / level / decision / basis / reasoning / alternatives / reversible / backport_target` in the existing realization-decisions/Authority Delta surfaces. T2 adds or changes business truth and requires a recorded gap decision.

Use the T2 checklist: new entities or meaningful fields, roles/permissions, rules/thresholds/prices/policies, states/transitions, external integrations, compliance/legal claims, real names/data, or API semantics. Explicit P1/P2 conflicts and infeasible upstream facts are the other two triggers. T0/T1 do not escalate for reassurance and cannot supersede explicit facts.

P3 is the sole decision maker; no runtime role meeting or new approval/storage/Authority path is introduced. Before implementing a slice, batch its triggered gaps into one small call: existing topic decision → upstream delegation rule → decision card only if neither matches. Read only relevant P1/P2 IDs/digests and their original content: include the P1 records named in each selected P2 basis record's `p1_refs`, rather than sending reference IDs alone. The existing dry-run fact comparison also checks every gap packet against these admitted originals. Workflow mechanically applies the seven conservative defaults, marks sensitive choices `confirmation_required = true`, and records all fifteen fields in the existing Authority Delta ledger. Reuse by topic, declare a per-run decision-call cap, and at the cap record conservative choices without another call. Use `scripts/phase3/p3_gap_decisions.py::resolve_slice_gaps` with the existing Journal and shared bounded transport; actual network resends count toward the declared decision-call cap. `load_interaction_gap_context` reads the SHA-bound D freeze and keeps unreviewed author sections as reference only. `p3_fact_registration.py` compares actual OpenAPI, SQL and consumed runtime configuration bytes/hashes with frozen source IDs and registered deltas. Extend the original OMR and isolated SQR subject with `bounded_challenge_binding.p3_gap_review_scope`; retain explicit T2 results and missing coverage using `p3_t2_sqr_metrics`, without another review round.

Follow `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md` for the full decision card, default rules, fifteen fields, merged view, and no-unregistered-new-facts check. Effective truth is frozen P1/P2 plus P3 decisions; only a recorded gap decision with `supersedes` can override an explicit fact locally. Preserve `upstream_reconciled = false`. P4/UAT/EKRI consume the derived merged view; existing OMR → isolated SQR also reviews T2 records. `backport_target` feeds the next upstream version, never regeneration in the current cycle. If the direction is fundamentally wrong, P3 reports it and a human decides whether to end the cycle.

## Primary Entrypoints

After S1B has passed, generate the exact S2 implementation candidate and decision template. `--action-card-root` may bind an already-reviewed S1B output; when omitted, the prepare path runs the Action Card preflight in the current output root before producing the candidate:

```bash
python3 scripts/phase3/agentic_implementation_authority.py prepare \
  --phase2-root <phase2-root> \
  --action-card-root <s1b-output-root> \
  --output-dir <phase3-s2-output>
```

The S2 host Agent decides implementation semantics, planned code/test targets and evidence intents for every exact operation/non-operation slice while preserving immutable S1B bindings and constraint IDs. S2 itself does not write those targets. Only after the accepted S2 authority is reviewed may S3 materialize backend code and test files.

For a **generation-only S3 stop** that must not execute generated tests/runtime/Trace, use:

```bash
python3 scripts/phase3/run_impl_realization.py \
  --phase2-root <phase2-root> \
  --action-card-root <s1b-output-root> \
  --agentic-implementation-decision <accepted-p3-decision.json> \
  --output-dir <phase3-s3-output> \
  --project-artifact-root <project-artifact-root>
```

The generation-only runner materializes every declared S2 implementation/test target, including non-operation realizations, groups shared targets instead of overwriting one slice with another, emits DB migration plus static schema-test support, and keeps generated Trace review-bound. Every S3 slice binding must carry the accepted structured durable persistence decision from S2 (`command`, identity components, carrier, field bindings, enforcement, writer, replay posture) instead of forcing Agentic code to parse `persistenceEffects` prose or infer persistence meaning from target names. When the P3 decision used a locally applicable Authority Delta, the binding also carries its delta ID for provenance; the delta never rewrites P1/P2. This binding is authority propagation only; S3 does not thereby own SQL lowering or runtime execution. Code ownership is explicit: MGET-qualified mechanical project/config/contract wiring stays Workflow/template-owned, while service/repository/policy executable bodies and unit/integration behavior assertions are Agentic-owned coarse blocks. On the first pass, unresolved Agentic blocks are emitted as bounded `@wff:agentic-begin/end` regions and the existing S3 receipt reports `authoring-required`; this is a handoff, not completed code realization. The Host Agent may edit only those marked regions in the same S3 root. Re-running the same command preserves materialized regions, rejects changes to the surrounding template shell, and may report `generated-not-executed` only after every required Agentic block is materialized. **Frontend page/test targets are the bounded exception to S3 source ownership:** accepted `apps/web/**` and `tests/unit/web/**` targets remain in the same P3 authority/binding denominator, but S3 delegates their source realization to `wff-impl-frontend` instead of writing a parallel generic module over the same path. The runner proves block-range/hash integrity, not writer identity or semantic correctness; Host-Agent/session evidence plus later typecheck/tests/S4 Review own those stronger claims. Do not introduce a selected-module bundle, parallel frontend authoring route, or persisted rich ownership-plan artifact. Runtime-dependent SQL execution tests remain owned by the later execution/verification stage because their backend/DB harness is not an S3 generation-only authority surface.

`scripts/phase3/run_impl.py` is the aggregate implementation path and may continue into verification/execution after generation. Do not use it when the requested stop point is S3 code/test generation only. In project/full-lifecycle runs, pass `--project-artifact-root <project-artifact-root>` so the fixed `p3-realization-decisions.md` sits at the project artifact-package root alongside the phase directories; direct P3 runs may use the P3 output root as the bounded fallback.

For clean-package **strict runtime closure** from a profile that carries the required runtime/assurance dependencies (notably `full-lifecycle` / `full-pack`), use the aggregate route rather than the legacy foundation runner:

```bash
python3 scripts/phase3/run_impl.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-root> \
  --agentic-implementation-decision <accepted-p3-decision.json> \
  --mainline-verification-mode strict-runtime \
  --authority-delta-ledger <current-p3-authority-delta-ledger.json> \
  --install-toolchain
```

When frontend is explicitly requested, the aggregate route may orchestrate the canonical focused frontend authoring owner and must receive the exact current UI IA contract:

```bash
python3 scripts/phase3/run_impl.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-root> \
  --agentic-implementation-decision <accepted-p3-decision.json> \
  --enable-frontend \
  --ui-ia-contract <exact-current-ui-ia-contract.json>
```

The first frontend pass may stop at `authoring-required`; the Host Agent materializes only the bounded frontend `@wff:agentic` regions and reruns the same decision/root or supplies a same-decision `--agentic-source-root`. `impl-frontend-report.json.authoring.status=materialized` is source-authoring evidence only.

For requested frontend **P3 runtime/browser evidence**, continue through the same aggregate/runtime-smoke owners rather than a frontend-specific lifecycle:

```bash
python3 scripts/phase3/run_impl.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-root> \
  --agentic-implementation-decision <accepted-p3-decision.json> \
  --enable-frontend \
  --ui-ia-contract <exact-current-ui-ia-contract.json> \
  --mainline-verification-mode strict-runtime \
  --run-runtime-smoke \
  --frontend-interaction-spec tests/e2e/<current-interaction>.spec.ts \
  --install-playwright-browser
```

Every requested current-ready compiled interaction must be covered by a current `tests/e2e/**` spec carrying its exact `@wff:frontend-runtime-evidence page_id=... interaction_id=...` marker **and the exact current UI-IA API endpoint**. Browser/network substitution (`page.route`, `route.fulfill`, `page.setContent`, and equivalents) is disallowed. Multi-role products require one independent least-privilege consumer journey per accepted terminal persona; a super-role cannot qualify them. When `business_data_requirements.clean_first_use_required=true`, current evidence must also include a clean-first-use journey that starts without business seed/fixture identity, performs a real write, uses the accepted read/discovery path when required, and proves reload/re-entry context recovery without hard-coded/random UUIDs. Write/mutation interaction evidence must isolate desktop/mobile data using the Playwright project identity (`testInfo.project.name`) so one viewport cannot pass or fail because another viewport already mutated the same record. The existing runtime smoke starts the generated API and Web services on the run-scoped API/Web/PostgreSQL/Redis ports, checks Web-to-API runtime proof, executes desktop/mobile Chromium evidence, and retains screenshots plus Playwright JSON/trace artifacts. Passing evidence is bound back to the current frontend authoring/decision identity as factual Evidence only; it remains `semantic_authority=false` and does not create P4/product approval or production/UAT claims.

If S3 emits unresolved `@wff:agentic` regions, stop at `authoring-required`; the Host Agent may materialize only those bounded regions, then rerun the same aggregate route or supply a same-decision `--agentic-source-root`. Strict-runtime Workflow owns only mechanical closure: current project/runtime scaffold support, toolchain/bootstrap, PostgreSQL preflight when the selected evidence requires persistence truth, selected test execution, runtime-evidence binding, Trace refresh, exact contract-operation-decision binding, and delivery-gate refresh. Before final Trace refresh, carry the accepted P2 `.trace/trace.db` identity source into the P3 workspace and project current confirmed P3 evidence into that carried database; a JSON trace registry without the carried/indexed identity source must remain claim-capped. Only tests reported passed by retained verification may enter runtime proof: concrete passed test paths belong in `runtime_test_refs`, while `runtime_evidence_refs` must point only to retained parseable verification JSON reports that prove those tests passed. Failed or suite-initialization-failed tests must never enter either proof set or confirm Trace. Passed scenario/replay evidence may be projected back to an original exact operation binding only when operation, accepted contract, implementation decision ID, and implementation decision digest match exactly. Accepted P2 non-operation realizations remain separate from public operations and contract Trace: their existing `non_operation_rows` may enter strict execution only through explicitly declared behavioral targets (for the current backend runtime, `tests/unit/api/**`), and semantic realization requires the exact non-operation realization ID, implementation target, passed behavioral test identity, retained JSON evidence, and implementation decision identity. Binding-shape tests such as `tests/s3-authority/**` alone must not satisfy a non-operation realization claim. A generated scenario/replay may cover several accepted operations: preserve that exact operation/authority-contract set as evidence-only identity, execute the source test, and confirm it only when every bound operation has implementation-target coverage and that exact test passes; never collapse a multi-operation scenario into one operation or use it to repair an exact contract identity. Mechanical OpenAPI/request/response examples shape executable test payloads and schemas but are not semantic literal truth: scenario/replay tests may assert exact business values only when an explicit authority-bearing source marks that literal; otherwise they prove shape, identity continuity, invariants, failure semantics, or bounded non-empty values. Validation-only runtime baseline fixtures may mechanically derive missing precondition values from accepted schema/OpenAPI evidence, but every emitted value must remain compatible with the accepted schema type; an incompatible mechanical example must fall back to a deterministic type-correct validation value rather than becoming runtime or product truth. Stateful strict validation preconditions that require a specific accepted business state must come from the accepted P3 realization or a validation-only sidecar bound to the exact accepted P3 decision ID and digest; the sidecar may establish operation-specific verification rows but cannot become product seed data, production truth, or a parallel semantic authority. Verification payload construction must also consume accepted path/query parameter metadata and must not choose invalid/missing fields by incidental serialized key order. Negative payload shaping must follow compiled contract status plus an exact failure-field hint: when an error-code token names a request field directly, prefer that semantic field over a compound field that merely contains the token (for example `invalid_decision` targets `decision`, not `decision_request_id`). Field-invalid caller errors may remove only that hinted field, while conflict/permission/not-found/dependency lanes keep their dedicated mechanics and must not be reclassified from error-code naming. Generated API routing must likewise preserve each operation's frozen OpenAPI `error_code -> HTTP status` mapping and resolve that operation-local contract before any generic error-name fallback; the same error code may legitimately carry a different status in another operation and must not become global runtime truth. Supplemental scenario `invalid request` variants and contract field-invalid failure cases must not execute when that exact hint cannot be resolved, because an unchanged valid payload is not executable negative evidence. Security assurance must preserve the same truth boundary: review-bound, deferred, provider-neutral, or explicitly unaccepted auth/token posture must not be promoted into an external-IdP or token-lifecycle requirement merely because those terms appear in guidance prose; explicit accepted security requirements remain blocking until proved. A current Authority Delta ledger may supply P3-local persistence/schema precision but never rewrites P1/P2. TVG flags on this route are recorded strategy inputs only; accepted Agentic implementation authority remains the semantic source of truth.

Missing, stale, incomplete, or unapplied S2 decisions stop at `agentic-decision-required`. Accepted S2 authority with unresolved executable code blocks stops at `authoring-required`. Completed Agentic blocks without executed test/runtime/Trace evidence remain `generated-not-executed` and cannot claim implementation correctness or runtime readiness.

Before an accepted P3 decision stands, run one bounded challenge over `exact-realization`; each implemented slice also requires `implementation-invariant`, and irreversible migration choices add `irreversible-migration`. The reviewer sees the exact P2 contract-operation slice, admitted implementation context, code/test target contract and explicit unknowns—not the preferred implementation or author reasoning.

Compatibility reading accepts frozen P2 decision/authority pairs carrying `bounded-challenge-integrity-v1`, `legacy-pre-bounded-challenge-v1`, or `p2-omr-sqr-integrity-v1`. Preserve their exact source identity/digests, expose missing integrity evidence and the resulting claim ceiling, and resolve content gaps in P3. A WFF format upgrade never requires a new upstream decision or regeneration of accepted frozen artifacts; compatibility does not fabricate current review proof. P3 consumes the interaction freeze through `load_frozen_interaction`. A bounded D review may contain multiple packet receipts inside each of the original OMR/SQR reviews; preserve their input/prompt/call bindings and explicit gaps. A complete-review v1 freeze requires both receipts. An explicitly authorized bounded v2 freeze preserves unchanged authored sections, actual receipts and T2 review gaps; `load_frozen_interaction` verifies its bindings without inventing review acceptance. P3 consumes its claim-capped delivery and resolves the gaps locally.

The P3 host Agent reconciles every material finding. Behavioral claims may use digest-bound TDD RED evidence instead of another reviewer pass, but a generated test that never failed against the prior behavior is not RED proof. Actionable findings require substantive code/decision/test changes and a new challenge over the changed unit. Default depth is one pass, maximum three; cross-model review is optional and per-invocation authorized. The reviewer never owns implementation truth.

Focused capability runners:
- `scripts/phase3/run_impl_action_cards.py`
- `scripts/phase3/run_impl_db_schema.py`
- `scripts/phase3/run_impl_api_docs.py`
- `scripts/phase3/run_impl_backend.py`
- `scripts/phase3/run_impl_frontend.py`
- `scripts/phase3/run_impl_realization.py`
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

P3 closure is value-bearing only when core paths are runnable, accepted P1/P2 commitments are exactly implemented or explicitly disposed, tests prove behavior beyond status/schema shape, runtime and persistence evidence are meaningful, and claim ceilings are explicit. `semantic-realization-ledger.json` remains the denominator-level consistency result, while `p3-exact-realization-binding-ledger.json` binds each exact contract-operation-decision tuple. Each is identity/evidence linkage, not an automated L2 score and not a substitute for Agentic semantic review.

## Required Inputs

Read or verify:
- Phase-2 root
- accepted `p2-agentic-architecture-authority.json`
- `p2-agentic-architecture-application-receipt.json`
- `p2-commitment-disposition-ledger.json`
- verified `semantic-commitment-union.json`
- `engineering-spec-pack.md`
- `phase-3-implementation-entry.md`
- Phase-2 trace registry or explicit review-bound reason
- implementation component catalog and action-card obligation matrix
- accepted API contracts and data model
- work-package ordering and risk posture

## WFF Core Contract Binding

- Machine descriptor: `implementation-delivery`, phase `P3`, route `phase-3`, under `wff-core-contract` `1.0.0`.
- Consumes `phase-contract`, `handoff-contract`, `artifact-identity-contract`, `evidence-contract`, and `claim-state-contract`.
- Core supplies structural identity and evidence/claim envelopes; Phase-3 Agentic work owns implementation meaning and runnable code decisions.
- Missing or incompatible Core metadata blocks execution rather than weakening the Phase-2 handoff contract.

## Execution Sequence

1. Verify the accepted Phase-2 authority/application/union and exact P3 realization slices.
2. Build the immutable P3 candidate snapshot and obtain one accepted host-Agent implementation decision.
3. Canonically apply the decision to code, tests, exact bindings, and Trace inputs before any readiness claim.
4. Generate implementation action cards and subordinate scaffolds without allowing them to rewrite accepted semantics.
5. Generate or refresh DB schema, API docs, backend, optional frontend, and verification packs.
6. Bootstrap the runtime toolchain and run targeted evidence by family: units, SQL, contracts, scenarios, replays, and runtime smoke where supported.
7. Confirm the same contract-operation-decision tuple in current-generation Trace; file/test presence alone is insufficient.
8. Publish separate backend/runtime, semantic-realization, review, and overall results. The weakest evidence controls the overall state.
9. Resolve product/architecture gaps in P3 under the gap-decision protocol, queue `backport_target` for the next upstream version, repair implementation/evidence locally, and route environment failures to their accepted owner.

## Evidence Standards

Delivery claims require meaningful evidence:
- high-risk public operations require behavior cards before service/repository implementation. Behavior Cards are read-only projections: canonical P1/P2 identities must be preserved exactly, including accepted semantic constraint lineage such as `P1-CON-*`; when one operation is backed by multiple P1 value/constraint resolution rows, preserve their union rather than overwriting earlier lineage. Sources explicitly marked `not_required` by the accepted P2 operation-source obligation must not create synthetic anchor gaps, and—when accepted P3 implementation authority is already available—private implementation/test paths plus persistence posture must be projected from its exact declared targets/slices rather than re-derived from route/module naming. A `read-only` operation must render read/no-mutation behavior steps and must not inherit command-oriented state-transition or durable-write language; command operations retain their mutation/persistence obligations. Missing required sources and missing accepted P3 targets remain visible; the card must not invent replacements.
- service code must implement behavior-card pseudocode steps, not merely satisfy response shape. Behavior-card pseudocode must be backed by executable implementation/test evidence. Marker comments such as `behavior-card-step: step-N` are not proof by themselves: when strict runtime has collected green contract/coverage evidence and every exact accepted operation binding has an implementation target, passed-test identity, and retained JSON evidence under one decision identity, that stronger evidence may close a marker-only step gap. Missing implementation, missing exact evidence, failed contract/coverage execution, or ambiguous identity remains a P3 gap.
- P3 must consume `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json` as canonical JSON bridge artifacts.
- Discovery policy is `canonical-json-first-markdown-diagnostic-only`; classify missing or malformed bridge material as `matrix_missing_from_p2`, `matrix_present_loader_missed`, or an equivalent review-bound source state using fields such as `source_requirement_status`.
- optional UI compiled bindings are not global OpenAPI authority. Use `require_frontend_contract` before letting compiled frontend bindings constrain backend OpenAPI/types/client operation authority.
- payload typing review is scoped to backend implementation targets; frontend page helper `payload: unknown` is not backend implementation genericity.
- API/contract tests must use documented request paths and assert the compiled OpenAPI contract exactly, not only helper-enriched payloads. They must not synthesize bearer/OIDC requirements or response-envelope fields that accepted P2/OpenAPI authority did not establish. Explicit external-auth hardening remains required when affirmative accepted auth authority exists. Generic test-only rollback backdoors are not product contract truth; transaction claims require real persistence/rollback evidence on an accepted runtime path.
- Security/evidence hardening remains authority-conditional: audit behavior evidence is mandatory when accepted P2 authority explicitly declares an audit/audit-log obligation; absence of accepted audit authority must not create a synthetic audit-surface defect merely because no test filename contains `audit`.
- SQL/persistence claims require real migration and write/read or state-transition proof.
- Scenario and replay tests must prove business outcomes, failure semantics, idempotency, or state invariance where relevant.
- Backend unit tests should verify non-trivial service/domain/repository behavior.
- Generated runtime or passthrough helpers may bootstrap work, but cannot be the final proof of implementation quality.
- UI/frontend claims need real routes and basic operable behavior, not a placeholder surface.

## P3 Agentic Repair Interrupts

Scorecard, delivery-gate, and human rough-review defects are repair triggers. When the reviewer says `要求修改`, `要求返回`, or `提供干预输入`, produce `agentic-repair-interrupt.json` and `agentic-repair-interrupt.md` with an Agentic repair packet, owning phase, minimum rerun boundary, and claim ceiling; do not treat final reports as the only output.

## P3 Agentic Quality Repair

Agentic generation-quality repair must be test-first and evidence-capped. When claiming quality gain, at least one generated code, test, or evidence unit must change; script pass alone does not prove quality gain. TVG is a generation value-gain tool, not a decision owner. WAE / EDSP / SELA own decision placement when workflow/agentic/evidence boundaries, fuzzy structure, or system-level trade-off must be judged.

Apply the Root-Cause Replacement Principle before implementing a repair: identify the earliest accepted owner of the wrong behavior, state the correct implementation invariant directly, replace that owning logic, and rerun dependent evidence. P3 repairs implementation truth owned by P3. The phrase “defects owned by P1/P2 return upstream” means next-version backport only: within this cycle, P3 resolves gaps through recorded decisions and leaves frozen upstream artifacts unchanged. Root-cause replacement of WFF skills/templates/scripts/contracts takes effect in the next WFF version. Boundary guards remain for genuine external, security, protocol, or compatibility boundaries around otherwise-correct logic.

Semantic invariant repair must use source-supported semantic invariant evidence. Review-bound source truth remains review-bound; do not turn it into confident implementation truth. No generated `/tmp` output edits, GEO-only hidden branches, PetClinic-only hidden branches, or error-type patches may be used to create a fake quality gain.

## P3 Authoring And Realization Boundary

Default backend generation follows the action-card spine: `P2 component-action-card-obligation-matrix -> P3 implementation action cards -> S2 accepted implementation authority -> S3 code/test realization`. The persisted `action-card-execution-map.json` remains a bounded pointer/evidence surface and must not become a second semantic authority.

Before file write, consume the accepted current-snapshot host-Agent S2 implementation authority. That authority owns owner / aggregate / invariant / value-rule / state/mutation / authorization / failure / persistence / integration and proof intent. `run_impl_realization.py` and `s3_code_realization.py` mechanically project the accepted slice decisions into declared code/test targets and bounded Agentic blocks; Workflow supplies order/context/evidence and Evidence / Gates verify and cap claims. Project implementation conventions may guide mechanical naming and stack posture only and remain subordinate to S2 authority. Legacy `business-behavior-authoring-plan`, `phase3-agentic-module-implementation-brief.v1`, and `phase3-action-card-direct-implementation-driver.v1` sources may remain as historical/evaluation material but are not default runtime inputs and must not be reintroduced as parallel authority or active CLI enrichment.

Repository/audit/event generation must synthesize repository domain effects, state transition effects, audit/event effects, failure effect boundaries, and existing `domain_event_models` or `domain_event_catalog` before file write. Generated comments may expose producer / consumer / trigger / payload / timing / idempotency as `action-card-domain-event-modeling-effect`. This is not a performance optimization and not a P1/P2/P4 expansion.

## Selected-Module And Diagnostic Boundaries

Default Phase-3 mainline execution must not prepare `.phase3-review/phase3-synthesis-brief.json` or inject `Synthesis intent` comments. If a synthesis-only path is explicitly used, keep it as experimental evidence behind a non-default opt-in.

Selected-module synthesis is retired from the active Phase-3 CLI and release-proof route. Historical `module_synthesis.py` sources and fixtures may remain for evaluation/forensics, but `--module-synthesis-bundle` must not be offered, packaged as an active maintainer capability, or reintroduced as a parallel authoring route. The accepted S2 authority and S3 realization path own current code/test generation.

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

After Phase-3 owns validated Action Cards, the built Release runtime queues the
localized Human Review sidecar and returns immediately. A complete reader set
may publish the unified dossier; missing, failed, or stale readers remain
sidecar findings and must not change Phase-3 or P4 state.

Stop with one of these states:
- `delivery-ready`: runnable implementation and required evidence are green under the declared environment boundary
- `implementation-in-progress`: accepted implementation semantics were applied, but exact evidence/Trace remains blocking
- `implementation-ready-with-claim-ceiling`: useful implementation and exact current-generation evidence exist, but named higher-order evidence is missing
- `p3-gap-decision-required`: a T2 fact, conflict, or infeasible upstream fact requires a recorded P3 decision, after which P3 continues
- `blocked`: required runtime, toolchain, dependency, or source evidence is unavailable

Do not call Phase-3 complete when the repository only contains scaffolds, generated-runtime passthroughs, exit-code-only green reports, or unreviewed fake-green tests.

The repository entry `scripts/phase3/run_bounded_p3.py dry-run|run` composes frozen admission, delivered D consumption, gap resolution, authors and original OMR/SQR. Its configuration supplies the scenario P3 `token_limit`; the second run may spend at most that limit minus the first run’s Journal charge. See `reference-packages/phase3-implementation-delivery/bounded-p3-run.md`. Declared P3 model calls use `common.bounded_model_call` and `common.bounded_response_stream`, shared with D, with Journal phase `P3`. Calibrated endpoint/model metering uses text delta events×1.02 plus1024 reasoning reserve and item framing, and ceil(prompt UTF-8 bytes/2)+4000 for requests; each completed call compares provider visible tokens and deviation>3% switches to bytes and reports. Recalibrate when endpoint/model changes; preserve provider usage for completion and charge request estimate+8000 for cutoff/transport error. The caller streams and closes at 8K estimated output including reasoning. An active cutoff is charged request upper bound + 8,000 and labeled conservative, not provider-measured. Simplify only the rejected section within at most two repairs; then retain T2 and continue other sections. HTTP/stream errors consume the full request upper bound + 8K reservation, recorded as `transport-error-upper-bound`; remote execution remains uncertain. Resend the same section at most once, counting every dispatch; two transport failures in a section leave T2 and other sections continue. The third transport error in the run stops dispatch and requires an Owner report. Declared call/token/wall caps still apply to resends; other unknown usage stops the run. This is finite network recovery, not an extra semantic review or a reset of the section repair limit. This enforces the existing limits without provider schema, hidden retries or upstream regeneration. Consumer authors and reviews receive actual dependencies; immutable findings consume existing repairs, stack deviations are preregistered, and complete schema comparisons preserve explicit identities and types. A non-string or empty realized fact ID is an explicit `invalid-fact-id` finding, never coerced to a string or treated as registered; continue checking other facts without a type-error crash. The referenced bounded-P3 contract defines this behavior without new roles, review rounds or higher claims.


T2 with `new_facts` requires `confirmation_required = true`. Bind isolated SQR verdicts to original records; mark rejected in effective views/backport and exclude their facts and accepted-resolution references.
List already-applied code surfaces; annotations do not undo code. Keep frozen historical records unchanged.
See the [p3-realization-decisions contract](../../reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md).

Shared D/P3 request calibration binds its measurement evidence: divide `ceil(prompt UTF-8 bytes/2)+4000` by1.4 and round up; lower the divisor to any smaller conservative-bound/provider-input ratio on every completed call, including after the initial three samples. Retain comparisons and provider charges; cutoff/transport errors cost the reserved estimate plus8000. Actual input<=60K/output<=8K and original cumulative caps still apply; changed endpoint/model requires recalibration.
Degraded upstream notices contain only section/T2 unavailability, with raw diagnostics retained separately. When one validation error class appears on first attempts in three distinct sections that still fail after bounded repairs (excluding successful or pending repairs), the operator calls `GenerationJournal.stop_authors`, retains already-issued responses and evidence, and completes funded reviews within the existing hard caps. Further runs require the active milestone authorization; the M3 second acceptance permits one extra run per approved scenario and no rerun.

For M3 second acceptance, `bind-p2` binds the complete current P2 freeze with unchanged P3/case author instructions.
Use same-case frozen M3 output for offline sizing and `protect_reviews=true` for planned OMR/SQR reservations. The A′ declaration fixes backend/frontend groups with recompute disabled and `protected_review_groups=[0]`; frontend reviews use remaining funds and missing reviews remain progress-unknown. See the bounded P3 run guide.
Human `GenerationJournal.stop_authors` preserves funded reviews. Bind current P2 by P1 relations minus per-family crosscut refs (fallback if empty); fields follow selected operations. Retain evidence and reject any empty original family. Apply the dispatch preconditions and recurrence rules in the bounded P3 run guide before dispatch; await audit release.
See `bounded-p3-run.md` for unchanged hard limits, measured comparisons and P1 relation/family selection evidence. Binding another P2 run resolves direct or SHA-bound inherited freeze manifests and retains lineage/transport counts; it also reselects every gap basis by its original P1 relations/families and validates current initial decision IDs/digests. Retain exact-basis records; reapply only existing sensitive conservative defaults. Explicitly exclude stale semantic decisions/inferences instead of relabeling their facts. Binding evidence stays outside model context. Demonstrate complete P3 dry runs against both real freezes before audit release. The post-M3 A′ Owner decision permits only one GEO P3 run after audit release, capped at 439,638 tokens/22 calls/3h, followed by result submission and a stop; no P2 rerun or PetClinic. Backend double-review acceptance plus existing backend schema/runtime acceptance opens M4; frontend results are progress only. WP4.1 may proceed now; WP4.2 scenarios await backend acceptance. See the bounded P3 run guide and #1203.
