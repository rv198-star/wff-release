---
name: wff-arch
description: Use when running or rerunning a real case through the official Phase-2 design and architecture flow from an accepted Phase-1 handoff.
---

# Phase-2 Design / Architecture Orchestrator

## Overview

This is the official Phase-2 entry skill. It turns a Phase-1 handoff into a bounded architecture package, not freewritten design prose.

Phase-2 owns architecture translation, source absorption, risk posture, data/API contracts, and the implementation-facing handoff. It preserves frozen product truth and records architecture gaps for P3 inference or gap decisions without requiring upstream completeness.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-2 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, table names, env vars, and protocol keywords in their canonical form.

Generation governance: `docs/governance/bounded-generation-run-governance-v1.md` (中文：`docs/governance/bounded-generation-run-governance-v1.zh-CN.md`). It bounds section generation and review without weakening factual runtime evidence.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- the user wants to start Phase-2 from an accepted Phase-1 PRD or handoff
- the output must feed implementation planning or an Engineering Spec Pack
- an unfrozen Phase-2 case needs local authoring, hardening, or closure
- an existing-system architecture-change intake packet must be consumed alongside the Phase-1 authority input

Do not use when:
- no admitted frozen Phase-1 input can be identified; declared content gaps alone do not block P2
- the task is only a small edit to one design document
- the task is code implementation, validation, or deployment execution

## Core Rules

1. Consume Phase-1 truth as upstream authority. Do not invent business/product direction inside Phase-2.
2. Design for first delivery and downstream implementation leverage. Avoid both minimal notes and speculative enterprise architecture.
3. Keep trace absorption explicit from Phase-1 trace units into Stage outputs, ESP sections, contracts, risks, and handoff surfaces.
4. Use bounded agentic design judgment for boundary choices, module decomposition, data ownership, contracts, dependencies, rollout posture, and trade-offs.
5. Record unresolved architecture truth as `review-bound` with owner, validation path, and downstream impact.
6. Treat machine-pass as structural evidence only. Architecture value, handoff usefulness, and claim ceiling still require judgment.
7. Publish three bounded handoff surfaces: facts P3 must not invent without a recorded decision, high-decision-value architecture choices, and delegation/default policies. Cover what is practical; upstream coverage is feedback, not a completeness gate. Preserve `p2-commitment-disposition-ledger.json` and `semantic-commitment-union.json` as compatibility identity/provenance indexes where present. `ExplicitValid(P1) union ExplicitValid(P2)` names that legacy identity union only, not a requirement to dispose every P1 commitment or cover all content before continuation. Record exact identities for the choices actually made, retain unaddressed gaps, and do not require a single atomic architecture decision to cover every combination. operation names, examples, templates, and inferred candidates must stay review-bound; Trace co-occurrence and generated lifecycle rows are also not disposition evidence.
8. Preserve the development / pre-production boundary. Do not imply production approval, owner sign-off, or UAT without supplied external evidence.
9. When accepted P2 authority exists, it is the canonical architecture denominator. Stage/ESP templates may not expand the accepted operation set, infer a different aggregate writer, manufacture lifecycle states/events, turn NOR/policy/invariant truth into endpoints, or replace accepted P1 topology with a generic workflow. `aggregate_and_writer_decisions`, accepted data/interaction decisions, `durable_persistence_identity_decisions`, dependency dispositions, and the P1 product-world handoff must survive canonical projection without a parallel architecture truth. An accepted data decision that explicitly declares a `table_name` plus concrete fields remains part of the canonical schema denominator even when it is a read-only/current-system materialization seam with no writer aggregate; project schema ownership from the accepted operation service for documentation, but do not manufacture `writer_service_id` or write authority. Stage-03 contract Trace must preserve each accepted public `contract_id` as the contract trace identity; a renderer-generated `P2-CTR-NN` identifier is allowed only outside accepted authority mode and must never replace an accepted contract identity. For high-decision-value persistence choices, state whether an operation writes durable state, is read-only, or has no durable state, and record the selected command kind (`insert` / `update` / `append` / `upsert` / `select-one` / `none`). Preserve exact replay identity/carrier/enforcement choices when decided; undecided details become explicit delegated questions or gaps, not a global completeness blocker. Templates must not invent idempotency keys, DB columns, unique constraints, dedup records, or conflict behavior from operation names, prose, examples, or field morphology. Stage-03 concurrent-conflict scenarios must be selected from operations whose accepted durable semantics actually reject a competing write; `replay-safe + return-existing` and read-only operations must not be relabeled as `409 version_conflict` merely to fill a scenario matrix.
10. Treat technology/deployment posture the same way: templates must not silently promote modular-monolith, cache/queue products, provider choices, token/key mechanics, numeric SLOs, retention durations, or scaling assumptions as accepted architecture. This applies to scenario coverage, verification, and handoff acceptance rows as well as the main technology sections. Such choices are canonical only when the current P2 Agentic decision explicitly accepts them; otherwise keep them review-bound.
11. Treat the P2→P3 component/action-card bridge as an authority projection, not a lossy summary. Every defined implementation component must remain represented; multi-operation components must union all accepted operation contracts and P1 traces; accepted aggregate/writer/topology and applicable NOR/state/failure/dependency/claim-ceiling truth must remain available to P3. A non-operation aggregate/repository component must not disappear merely because it has no public endpoint. A repository component created from an accepted table-backed read model must inherit that data decision's exact accepted `operation_id` / service / P1 trace path rather than become an orphan component, while still carrying no writer authority. Mechanical schema/operation token matching cannot override accepted aggregate or data-decision identity.
12. Where role ownership is a high-decision-value choice, classify an authenticated operation's terminal-access posture in the Agentic architecture decision: `terminal-direct`, `system-continuation`, or `review-bound`. `terminal-direct` must name exact accepted P1 role commitments, bounded visible business objects, and denied behavior; it does not authorize P2 to invent IAM provider or credential mechanics. `system-continuation` is not a terminal-role action and must not be exposed merely because an HTTP operation exists. A distinct P1 role may not be merged into a convenience/super-role, and Frontend route hiding alone is never API authorization. The resulting role/operation/data boundary must survive the P2 bridge into P3 Action Cards and service-boundary evidence.
13. For material consumer-facing fields and decisions, P2 owns **Product Interaction Semantics**, not concrete UI presentation. Preserve `user_meaning`, `value_source`, `cardinality`, `editability`, `candidate_source`, `discovery_requirement`, `context_carryover`, `default_or_recent_semantics`, `usage_frequency`, `error_cost`, `validation_semantics`, `privacy_or_sensitivity`, `free_form_allowed`, `free_form_rationale`, `truth_state`, and `unresolved_interaction_gaps`. When fresh P1 authority carries `interaction_semantics_contract=product-interaction-semantics-v1`, every accepted P2 interaction `request_field_mapping` must have one exact `product_interaction_semantics` row bound to the same `interaction_id`, `contract_field`, and value source, plus any applicable P1 task-context refs. `candidate_source` must explicitly distinguish accepted / absent / review-bound / not-applicable source posture and identify whether authority comes from workflow context, existing business data, an accepted operation, accepted vocabulary, or user-defined business data. Required discovery with no accepted candidate source remains an explicit gap with a claim ceiling and P3 decision route; it cannot be represented as already resolved. Accepted vocabulary must carry accepted P1 authority refs or vocabulary-bearing P1 task-context refs; operation-backed candidates must name accepted P2 operation IDs. A business reference with no accepted workflow context, current business object, List/Search/Lookup operation, accepted vocabulary, or other candidate source is a discovery gap; it is not product-ready merely because its contract type is `string`. Keep `widget_type`, `control_type`, `react_component`, `html_input_type`, `use_multiselect`, and `component_type` out of accepted Product Interaction Semantics unless an external source makes presentation authoritative. Stage-05 may select product-level interaction patterns; it does not choose component implementation. P3 Action Cards project the accepted semantics into implementation obligations, while P3 Agentic realizes the accepted Stage-05 product interaction pattern and owns concrete control/component choice, page composition, progressive disclosure, and responsive/accessibility realization. See `docs/governance/v1.10-product-interaction-semantics-authority-boundary-v0.1.md`; `scripts/common/product_interaction_semantics.py` is the structural boundary helper and must not decide semantic values or widgets.
14. Treat **consumer outcome sufficiency and human recognizability** as architecture/data truth, not as a frontend polish afterthought. A terminal-facing read model is `sufficient` only when the target persona can both discover the durable object and distinguish the intended object using accepted human/business labels or context adequate for the next task; technical identity, status, or listability alone is not enough. Successful terminal operations must expose or resolve the business result needed to complete the accepted user outcome. A `*_ref`/identifier-shaped response field is not automatically consumer-readable content: if P2 cannot establish that it is itself human-readable, the accepted contract/read model must provide a resolver or consumer-readable projection, otherwise the outcome remains review-bound. File/image semantics must include an accepted materialization path that produces a backend/provider-readable resource reference; filenames, sizes, browser-local object descriptions, or synthetic pseudo-refs do not satisfy image/file authority. These rules constrain semantic sufficiency without selecting widgets or presentation.

## Coverage, one-directional flow, and delegation

Within a delivery cycle, P1 → P2 → P3 (→ P4) is one-directional. Accepted P1/P2 artifacts stay frozen. P2 specifies facts P3 must not invent silently, high-decision-value choices, and delegation/default policies; it covers what is practical without a full-content closure gate. Downstream gaps, contradictions, and infeasible facts are resolved through the existing P3 realization/Authority Delta protocol, then queued for the next upstream version.

Generate the **Delegation and Default Policies / 委托与默认策略** section from neutral templates. Each row names a stable rule ID, question category P3 may decide, applicability/basis IDs and digests, default action, boundaries, confirmation posture, and next-version backport target. Agentic selects and fills the bounded policies from accepted truth; templates provide structure, never business answers/defaults. Missing sensitive facts use the seven numbered conservative defaults in `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md`. P2 supplies architecture/interaction delegation with Stage-05; frozen P1 has no new delegation section until M4.

## Stage 01–04 and Engineering Spec Pack author slots

Use `scripts/phase2/architecture_templates.py` with `data/architecture-design-v1.json` for bounded flat author records. The versioned library provides neutral section concerns and selectable record cards; it carries no service, role, technology, lifecycle, capacity, retention, schedule, or review answer. Select original P1 IDs per section. Models supply flat service/object/operation/field/state/policy records and named gaps; the existing local schema and identity validator check structure, while OMR and isolated SQR assess decisions. Rendering numbers records and preserves source IDs without asserting acceptance.

The legacy Stage/ESP reader format keeps its headings and source identity projections. Its `architecture_slots` mapping supplies explicit stage decisions; absent values remain undecided or empty. Do not refill missing slots with inferred roles, padded rows, synthetic lifecycle transitions, arbitrary dates, numeric targets, or a fabricated verification pass. Keep raw author records for reviews; rendered Markdown is a reader surface. See `reference-packages/phase2-design-architecture/architecture-generation.md` for slots and compatibility.

## Stage-05 — Product Frontend Interaction Design / 产品前端交互设计

Inputs are the six-category ID/digest-bound P1 projection and accepted P2 architecture/API sections. Retain source identity and claim ceilings; an absent fact becomes a named gap. The section reduces downstream decision cost and does not demand complete coverage of every possible interaction.

Read the frozen P1 Authority with `python scripts/phase2/p1_input_projection.py --authority <authority.json> --expected-sha256 <frozen-sha256> --logical-id <frozen-package-id> --output-dir <new-directory>`. It writes a deterministic six-category `projection.json`, a next-version `backport-queue.json`, and a `volume-report.json` without a model call. Each projected item retains its original P1 identity, source pointer and digests; absent attributes stay absent. Validate against the frozen bytes before consumption and select the relevant original IDs separately for each D section. The complete projection is an offline source index, not a single-call prompt. The volume report labels token estimates and byte bounds explicitly; it is not provider usage.

| Section | Required content | Excludes |
|---|---|---|
| 1. Role working modes and task topology / 角色工作模式与任务拓扑 | Main tasks, frequency, entry points, and handoffs for each relevant role | Components |
| 2. Information architecture and navigation / 信息架构与导航 | Role workspaces/top-level areas, object hierarchy, navigation model | Visual styling |
| 3. Core task flows / 核心任务流 | Cross-view steps including first/clean use, success result and next action, failure recovery | Pixel-level flows |
| 4. View inventory / 视图清单 | Purpose, principal data, and actions of list/detail/queue/board/form views | Control-level specifications |
| 5. Key interaction patterns / 关键交互模式 | Pattern-card selection for discovery/selection, bulk action, irreversible confirmation, drafts, approvals, notifications | Component implementation |
| 6. View states / 视图状态 | First-use/empty, loading, error, denied, and partial data | Final copy |
| 7. Decision information / 决策所需信息 | Attributes needed at each decision and read-model sufficiency | — |
| 8. Language and terminology / 语言与术语 | Locale, glossary, tone | — |
| 9. Constraints and P3 freedom / 约束与 P3 自由清单 | Must-preserve choices versus matters P3 decides | — |
| 10. Delegation and default policies / 委托与默认策略 | Interaction/architecture categories P3 may decide and default behavior per category | New business facts |

Use D: project inputs → split by section skeleton → code selects relevant upstream IDs and candidate pattern cards → one flat model response per section → local permissive parsing and strict structural/identity validation → at most two diagnostic repairs of that section → code instantiates/trims/fills patterns, numbers, and cross-references → assemble → Agentic review → formal freeze when applicable. Unrepaired sections degrade to T1/T2 gaps; retain accepted sections. The model chooses patterns/parameters and bounded business slots; it never writes composition handles, nested compositions, or variant tags. Templates never supply business answers or business defaults.

Each call stays within approximately 60K request tokens and 8K output tokens; local schema depth is at most three and D does not use provider schema by default. The provisional whole-section budget is approximately 15–25K output tokens per scenario, calibrated from the first M1 measurement; it is not one atomic call. All ten subsections are delivered or carry explicit gap markers. Evaluate usefulness through downstream consumer outcomes and recorded gaps, not a completeness gate or widget quota. Use `scripts/phase2/interaction_generation.py` and the versioned `scripts/phase2/data/interaction-design-v1.json` library. The host supplies one plain-text transport callback per declared call; it must preserve raw text, measured request/output usage (including reasoning), and completion status. Read `reference-packages/phase2-design-architecture/interaction-generation.md` for the API, offline replay, accepted-section reuse, and OMR→isolated SQR freeze contract. An interaction-only freeze does not establish complete P2 acceptance.

## Required Inputs

Read first:
- `docs/phases/phase-2/phase-2-session-bootstrap.md`
- `docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md`
- `reference-packages/phase2-design-architecture/README.md`
- the Phase-1 PRD sections `Phase-2 Design Input Contract` and `Fine-Grained Trace Registry`

For existing-system architecture changes, also consume the optional `P2 Existing-System Architecture Change Intake Packet`. It supplies current-system architecture facts and constraints; it does not replace Phase-1 demand truth.

The accepted `p1-agentic-product-authority.json`, its P1 application receipt,
the P1 PRD and `Phase-2 Design Input Contract` remain the authority input. A PRD
without the accepted P1 authority is not sufficient for the fresh P2 mainline.
The `existing-system-architecture-change` side branch is not a new Phase-2 flow; it
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
handoff placement; Agentic owns architecture/event-model judgment; For event-model depth prompts, Templates / TVG shape depth only; reusable structure, fixed expression, and selectable patterns are their separate generation responsibilities; Evidence / Gates prove traceability and cap claims. Schema
checks must not generate architecture judgment. Do not create a default heavy
event artifact. P3 consumes event models; P3 does not invent complete event
architecture when P2 is silent.

## Thinking Value-Gain Generation Strategy

Use TVG after the Phase-1 full-use result proves useful enough to consume, not to make architecture more elaborate by default. Default `--thinking-value-gain-mode`
may stay off unless depth is needed; when enabled, expose
`--thinking-value-gain-output-profile` as `insight_dense | balanced | coverage_rich`.
Preserve Thinking Thickness and Value Density around operation flow / sequence / state / replay source material. If P1 full-use produces inflated or lower-signal truth, select the relevant ID-bound projection, cap claims, and queue next-version feedback rather than regenerating frozen P1.

## WFF Core Contract Binding

- Machine descriptor: `architecture-design`, phase `P2`, route `phase-2`, under `wff-core-contract` `1.0.0`.
- Consumes `phase-contract`, `handoff-contract`, `artifact-identity-contract`, `evidence-contract`, and `claim-state-contract`.
- Core validates identities and continuation structure; Phase-2 Agentic work remains the owner of architecture judgment and trade-offs.
- A missing or incompatible binding blocks architecture entry instead of allowing the runtime to infer upstream truth.

## Entrypoints

First prepare the current-snapshot architecture candidate and decision template:

```bash
python3 scripts/phase2/agentic_architecture_authority.py prepare \
  --phase1-prd <phase1-prd.md> \
  --candidate-out <p2-candidate.json> \
  --decision-template-out <p2-decision.template.json>
```

The host Agent must review the exact admitted P1 authority and submit an accepted
decision. The candidate packet and vocabulary hints are non-authoritative. Then
run fresh Phase-2 generation:

```bash
python3 scripts/phase2/run_phase2_fresh_generation.py \
  --phase1-prd <phase1-prd.md> \
  --agentic-architecture-decision <accepted-p2-decision.json> \
  --output-dir <case-phase2-root> \
  --version <version-label> \
  --run-wrapper
```

Missing, stale, incomplete, or unapplied decisions stop at
`agentic-decision-required`; deterministic Stage generation alone cannot close
architecture authority.

Use the existing OMR → isolated SQR review with `p2-omr-sqr-integrity-v1`. OMR is open-ended and precedes SQR; SQR receives the artifact and exact input identities, not OMR findings/results. Retain provenance, unknowns, and claim ceilings without an additional standing challenge or approval round.

When the complete interaction review would exceed 60K, `prepare_review_packets` keeps every accepted choice and explicit gap visible and batches the unchanged original facts by focus section. Execute all OMR packets, then the identical packets for isolated SQR. These are the existing two logical reviews; each packet is an actual call within the declared call/token/wall limits. Bind packet input and prompt digests plus every settled Journal call into the two receipts; code retains all findings and projects the review-bound verdict without another model judgment. The complete-review v1 freeze requires both original receipts. For an explicitly authorized bounded closeout, stop calls at the declared cap and use `freeze_bounded_interaction`: retain unchanged author sections and actual receipts, mark affected sections T2 for material findings or missing/rejected review coverage, and freeze v2 with explicit review gaps. No extra review, budget reset or accepted-section regeneration; this freeze does not claim completed review. P3 validates the same manifest and resolves retained gaps locally.

Compatibility reading accepts frozen P1 inputs under `bounded-challenge-integrity-v1` or `legacy-pre-bounded-challenge-v1`, including retained v1 inputs. Preserve IDs/digests, expose missing integrity evidence, and declare the resulting claim ceiling. Do not require a new P1 decision or regeneration because WFF formats changed. New P2 review records use `p2-omr-sqr-integrity-v1`; compatibility does not fabricate that review evidence for historical artifacts.

The P2 host Agent addresses findings in the affected unfrozen section within the declared run limits. Missing P1 facts and unresolved architecture questions remain explicit gaps for downstream P3 decisions and next-version backport; non-applicable findings carry rationale. Existing OMR/SQR review does not add a controller, Integrator, repeated approval, or generation self-evaluation. The accepted P2 authority retains digest-bound review evidence; the reviewer never owns architecture truth.

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

1. Verify the accepted P1 authority/application receipt and choose a fresh Phase-2 case root.
2. Build the architecture candidate/context snapshot. Mechanical service, operation, dependency, and naming candidates remain hints only.
3. Author bounded sections covering the facts P3 must preserve, high-decision-value choices, and delegation/default policies. Preserve accepted role, operation, dependency, persistence, and P1 context identities for each authored choice; unaddressed content stays a named gap. Do not demand every P1 commitment disposition, every combination, or a complete atomic answer. For selected `terminal-direct` choices bind `allowed_roles`, `visible_business_objects`, `denied_behavior`, and P1 `authority_refs`; `system-continuation` remains non-consumer. Use explicit `const=<scalar>` or `allowed-values=<value1>|<value2>|...` for genuinely accepted literal constraints; examples never infer values from names or domain vocabulary.
4. Run the fresh generation entrypoint with `--agentic-architecture-decision`; the existing canonical Stage/ESP writer first binds the accepted service/operation/contract/aggregate/writer/NOR/data/durable-persistence-command/topology/dependency decisions into its generation model, then renders Stage-01..04, claim-control, Trace, ESP, and P3 entry. Do not append authority after a conflicting generic architecture has already been accepted as canonical truth.
5. Verify `p2-canonical-authority-convergence.json` immediately after Stage generation. The report must bind the current authority digest, exact endpoint denominator, aggregate/writer/data/NOR projections, durable persistence identity denominator, P1 topology, and any activated dependency lane; identity/digest corruption must be fixed, while content conflicts remain explicit P3 gap-decision inputs.
6. If an existing-system architecture-change packet exists, apply its accepted impact/compatibility/rollback decisions without creating a second writer.
7. Route Stage-02.5 only from the accepted dependency decision: `activate`, `internal-local`, `defer`, `exclude`, `return`, or `review-bound`. Vocabulary may only suggest candidates. An accepted `activate` route must render the exact dependency IDs as an active provider-neutral lane unless the authority itself binds a concrete provider.
8. Run wrapper closure, rebuild the semantic commitment union, and re-run canonical convergence after ESP / P3-entry generation so wrapper composition cannot reintroduce generic architecture truth.
9. Require `p2-agentic-architecture-application-receipt.json` to bind the decision digest, `canonical_writer_id`, canonical-convergence report, Stage outputs, ESP, P3 entry, disposition/dependency evidence, and exact applications of the decisions actually accepted; content coverage gaps do not invalidate identity binding. P2 claim-control lineage handed to P3 must be self-contained: preserve a P2-local portable snapshot of the accepted P1 claim-control surface and make generated P2 sidecars resolve that local surface rather than depending on the original P1 filesystem mount.
10. Generate the Stage-05 product frontend interaction design from the P1 projection and accepted architecture/API sections using D below. Hand off useful sections with explicit gaps and claim ceilings. P3 owns downstream T0/T1 inference and T2/conflict/infeasible gap decisions; next-version backport never rewrites frozen P1/P2 in-cycle.

## Required Output Set

A valid Phase-2 package preserves:
- Stage-01 architecture definition
- Stage-02 domain/module decomposition
- Stage-02.5 third-party integration design, or an exact decision-bound skip/return receipt
- Stage-03 data/interface design
- Stage-04 convergence and delivery plan
- Stage-05 product frontend interaction design, including delegation/default policies and explicit gaps
- `p2-agentic-architecture-authority.json`
- `p2-commitment-disposition-ledger.json`
- `p2-dependency-routing-receipt.json`
- `p2-agentic-architecture-application-receipt.json`
- `p2-canonical-authority-convergence.json` with exact identity bindings and explicit content conflicts/gaps
- Phase-2 execution report
- Engineering Spec Pack
- Phase-3 implementation entry
- traceability registry evidence
- quality check report
- explicit review-bound and claim-ceiling statements

## Quality Floor

Phase-2 is complete only when:
- the must-preserve facts, high-decision-value choices, and delegation/default policies are explicit; coverage gaps remain visible feedback
- architecture decisions explain why the chosen boundary is useful for delivery
- API, data, interaction, risk, and rollout surfaces are implementation-facing
- exact accepted operations/contracts/aggregate writers/NOR/data decisions are the canonical denominator; no generated CRUD/lifecycle/technology default overrides them
- source-defined P1 product topology survives P2; independent outcomes are not serialized by Stage-02 handoffs, Stage-03 flows, Stage-04 work packages/replays/sequences, or ESP composition
- activated dependency authority is represented by exact dependency IDs and bounded provider/error/test posture rather than vocabulary-derived provider guesses
- ESP carries relevant upstream IDs/digests, decided architecture, and named gaps so P3 can start with recorded inference/decisions
- high-risk operations carry source obligations and implementation-depth obligations
- unresolved items have owners, validation paths, and downstream impact

## Completion Standard

After Phase-2 owns a stable output, the built Release runtime queues the
localized Human Review sidecar and returns immediately. The sidecar reads the
accepted ESP and structured component catalog only as review projections; it
must not alter architecture truth or Phase-3 admission.

Stop with one of these states:
- `ready-for-phase3`: architecture and handoff are sufficient for implementation
- `ready-with-review-bound-items`: implementation may proceed only with named ceilings
- `ready-with-gaps`: useful sections are delivered with T1/T2 gaps and a P3 decision route
- `blocked`: source identity or required mechanical evidence is invalid; content gaps alone do not block the whole package

Do not call Phase-2 complete when the package only has template shape, pointer-only handoff, or generic architecture language.


For declared D/P3 model calls, use the shared `common.bounded_model_call` and
`common.bounded_response_stream` runtime. It streams and closes at 8K estimated Calibrated endpoint/model metering uses text delta events×1.02 plus1024 reasoning reserve and item framing, and ceil((ceil(prompt UTF-8 bytes/2)+4000)/divisor) for requests; the approved evidence-bound divisor starts at1.4 and is reduced to the minimum conservative-bound/provider-input ratio observed in every completed call, including after the initial three samples; each completed call compares provider visible tokens and deviation>3% switches to bytes and reports. Recalibrate when endpoint/model changes; preserve provider usage for completion and charge request estimate+8000 for cutoff/transport error.
output, including a conservative reasoning allowance. An active cutoff is
charged as request upper bound + 8,000, explicitly distinguished from measured
usage. Simplify only the rejected section within at most two repairs, then keep
T2 and continue other sections. HTTP/stream errors consume the full request upper bound + 8K reservation, recorded
as `transport-error-upper-bound`; remote execution remains uncertain. Resend the
same section at most once, counting every dispatch; two transport failures in a
section leave T2 and other sections continue. The third transport error in the
run stops dispatch and requires an Owner report. Declared call/token/wall caps
still apply to resends; other unknown usage stops the run. This is finite network
recovery, not an extra semantic review or a reset of the section repair limit. See the D interaction generation runtime
guide for counting, evidence and isolated review behavior. No provider schema,
hidden retries, new review round or upstream regeneration is authorized.

For declared complete bounded P2, use `scripts/phase2/run_bounded_p2.py` for offline
prompt preparation and execution; see `architecture-generation.md` in this package.
It uses the existing author/review functions and shared Journal, with explicit compact
review groups, per-section conclusions and charged-plus-pending reservation accounting.
Experiment folders contain configuration, declarations and outputs only. Retain accepted
freeze lineage; a second declared run selects only unmet parts within the shared caps.


For the bounded repository entry, earlier architecture records are reference-only;
new section arrays must not redeclare them. Name exact dependencies in foreign keys
or policy scope so review packets can select their original record facts. If D review
never started, a second declared run may use the existing exact Journal replay for
structure-accepted authors with identical input/template bindings; failed or reviewed
rejected proposals are ineligible. Offline sizing covers both M1 surrogates and actual
reused answers. Unselected or unreviewed units retain T2 and limit acceptance claims.
M3 second-acceptance preflight uses same-case frozen M2/M3 raw outputs, measured differences and explicit scoped references from `architecture-generation.md`. Set `protect_reviews=true`: reserve all planned reviews before authors; author repairs cannot consume those slots. On the existing three-section first-attempt error stop, count only sections still failing after bounded repairs (not successful or pending repairs); use `GenerationJournal.stop_authors` so funded OMR/SQR still finishes. Include validated closed ID/family/role-label lists in P2 prompts. The Owner-authorized single extra GEO/PetClinic run needs audit verification and separately determined caps; no rerun or code changes during execution. M4, including WP4.1, remains paused until M3 second acceptance passes.
