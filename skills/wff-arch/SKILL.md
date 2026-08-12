---
name: wff-arch
description: Use when running or rerunning a real case through the official Phase-2 design and architecture flow from an accepted Phase-1 handoff.
---

# Phase-2 Design / Architecture Orchestrator

## Overview

This is the official Phase-2 entry skill. It turns a Phase-1 handoff into a bounded architecture package, not freewritten design prose.

Phase-2 owns architecture translation, source absorption, risk posture, data/API contracts, and the implementation-facing handoff. It must not rediscover product truth or make Phase-3 invent missing architecture.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-2 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, table names, env vars, and protocol keywords in their canonical form.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- the user wants to start Phase-2 from an accepted Phase-1 PRD or handoff
- the output must feed implementation planning or an Engineering Spec Pack
- an existing Phase-2 case needs rerun, hardening, or closure
- an existing-system architecture-change intake packet must be consumed alongside the Phase-1 authority input

Do not use when:
- Phase-1 product truth is still unresolved
- the task is only a small edit to one design document
- the task is code implementation, validation, or deployment execution

## Core Rules

1. Consume Phase-1 truth as upstream authority. Do not invent business/product direction inside Phase-2.
2. Design for first delivery and downstream implementation leverage. Avoid both minimal notes and speculative enterprise architecture.
3. Keep trace absorption explicit from Phase-1 trace units into Stage outputs, ESP sections, contracts, risks, and handoff surfaces.
4. Use bounded agentic design judgment for boundary choices, module decomposition, data ownership, contracts, dependencies, rollout posture, and trade-offs.
5. Record unresolved architecture truth as `review-bound` with owner, validation path, and downstream impact.
6. Treat machine-pass as structural evidence only. Architecture value, handoff usefulness, and claim ceiling still require judgment.
7. Preserve the fixed commitment denominator as `ExplicitValid(P1) union ExplicitValid(P2)`: consume the accepted snapshot-bound P1 authority, require one current-snapshot host-Agent architecture decision, publish `p2-commitment-disposition-ledger.json`, and derive `semantic-commitment-union.json` from that authored ledger plus current claim/contract evidence. Every explicit P1 commitment needs one exact operation, operation-set, stable non-operation, return, repair, defer, exclusion, or review-bound disposition. Every explicit P2-only contract remains a P3 obligation. operation names, examples, templates, and inferred candidates must stay review-bound; Trace co-occurrence and generated lifecycle rows are also not disposition evidence.
8. Preserve the development / pre-production boundary. Do not imply production approval, owner sign-off, or UAT without supplied external evidence.
9. When accepted P2 authority exists, it is the canonical architecture denominator. Stage/ESP templates may not expand the accepted operation set, infer a different aggregate writer, manufacture lifecycle states/events, turn NOR/policy/invariant truth into endpoints, or replace accepted P1 topology with a generic workflow. `aggregate_and_writer_decisions`, accepted data/interaction decisions, `durable_persistence_identity_decisions`, dependency dispositions, and the P1 product-world handoff must survive canonical projection without a parallel architecture truth. An accepted data decision that explicitly declares a `table_name` plus concrete fields remains part of the canonical schema denominator even when it is a read-only/current-system materialization seam with no writer aggregate; project schema ownership from the accepted operation service for documentation, but do not manufacture `writer_service_id` or write authority. Stage-03 contract Trace must preserve each accepted public `contract_id` as the contract trace identity; a renderer-generated `P2-CTR-NN` identifier is allowed only outside accepted authority mode and must never replace an accepted contract identity. Every accepted operation must explicitly state whether it writes durable state, is read-only, or has no durable state, and must state the resulting persistence command kind (`insert` / `update` / `append` / `upsert` / `select-one` / `none`) so P3 does not rediscover that choice. Replay-safe operations must bind every replay identity component to an accepted durable carrier and an explicit enforcement posture. Templates must not invent idempotency keys, DB columns, unique constraints, dedup records, or conflict behavior from operation names, prose, examples, or field morphology. Stage-03 concurrent-conflict scenarios must be selected from operations whose accepted durable semantics actually reject a competing write; `replay-safe + return-existing` and read-only operations must not be relabeled as `409 version_conflict` merely to fill a scenario matrix.
10. Treat technology/deployment posture the same way: templates must not silently promote modular-monolith, cache/queue products, provider choices, token/key mechanics, numeric SLOs, retention durations, or scaling assumptions as accepted architecture. This applies to scenario coverage, verification, and handoff acceptance rows as well as the main technology sections. Such choices are canonical only when the current P2 Agentic decision explicitly accepts them; otherwise keep them review-bound.
11. Treat the P2→P3 component/action-card bridge as an authority projection, not a lossy summary. Every defined implementation component must remain represented; multi-operation components must union all accepted operation contracts and P1 traces; accepted aggregate/writer/topology and applicable NOR/state/failure/dependency/claim-ceiling truth must remain available to P3. A non-operation aggregate/repository component must not disappear merely because it has no public endpoint. A repository component created from an accepted table-backed read model must inherit that data decision's exact accepted `operation_id` / service / P1 trace path rather than become an orphan component, while still carrying no writer authority. Mechanical schema/operation token matching cannot override accepted aggregate or data-decision identity.

## Required Inputs

Read first:
- `docs/phases/phase-2/phase-2-session-bootstrap.md`
- `docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md`
- `reference-packages/phase2-design-architecture/README.md`
- the Phase-1 PRD sections `Phase-2 Design Input Contract` and `Fine-Grained Trace Registry`

For existing-system architecture changes, also consume the optional `P2 Existing-System Architecture Change Intake Packet`. It supplies current-system architecture facts and constraints; it does not replace Phase-1 demand truth.

The accepted `p1-agentic-product-authority.json`, its P1 application receipt,
P1 PRD, and `Phase-2 Design Input Contract` form the authority input. A PRD
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
handoff placement; Agentic owns architecture/event-model judgment; Templates /
TVG shape depth only; Evidence / Gates prove traceability and cap claims. Schema
checks must not generate architecture judgment. Do not create a default heavy
event artifact. P3 consumes event models; P3 does not invent complete event
architecture when P2 is silent.

## Thinking Value-Gain Generation Strategy

Use TVG after the Phase-1 full-use result proves useful enough to consume, not to make architecture more elaborate by default. Default `--thinking-value-gain-mode`
may stay off unless depth is needed; when enabled, expose
`--thinking-value-gain-output-profile` as `insight_dense | balanced | coverage_rich`.
Preserve Thinking Thickness and Value Density around operation flow / sequence / state / replay source material. If P1 full-use produces inflated or lower-signal truth, return or cap the claim instead of deepening architecture around it.

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

Before an accepted P2 decision stands, run one bounded fresh-context challenge over `architecture-ownership`, `contract-operation-identity`, `dependency-compatibility`, and `cross-phase-disposition`. The reviewer sees the candidate architecture artifact, exact P1/P2 contract identities, admitted context, dependency/unknown surfaces, and an issues-first instruction—not the owner's preferred architecture or reasoning journey.

A new P2 candidate may consume only a P1 decision/authority pair classified as `current-bound-authority` under `bounded-challenge-integrity-v1`. Historical `legacy-pre-bounded-challenge-v1` P1 proof remains readable for comparison and audit, but cannot be washed into a new architecture authority; return to P1 for a current snapshot-bound decision and exact challenge binding.

The P2 host Agent reconciles every material finding. A valid architecture defect changes the decision/artifact and requires a new pass over the changed unit; insufficient P1/context returns upstream; unresolved architecture truth remains review-bound with owner and P3 effect; non-applicable findings require rationale. Default depth is one pass, maximum three, and cross-model review is optional/per-invocation authorized. The accepted P2 authority carries the digest-bound challenge summary; the reviewer never owns architecture truth.

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
3. Obtain one accepted current-snapshot host-Agent architecture decision covering the portfolio, stable non-operation realizations, every P1 commitment disposition, dependency posture, durable persistence command/identity/replay posture for every accepted operation, and P3 handoff ceiling. When a request/result field constraint materially determines a valid positive contract example, encode it with the explicit machine-readable forms `const=<scalar>` or `allowed-values=<value1>|<value2>|...`; keep descriptive constraints as prose. Example projection may consume only those explicit forms and must not infer allowed values from free text, operation names, or domain vocabulary.
4. Run the fresh generation entrypoint with `--agentic-architecture-decision`; the existing canonical Stage/ESP writer first binds the accepted service/operation/contract/aggregate/writer/NOR/data/durable-persistence-command/topology/dependency decisions into its generation model, then renders Stage-01..04, claim-control, Trace, ESP, and P3 entry. Do not append authority after a conflicting generic architecture has already been accepted as canonical truth.
5. Verify `p2-canonical-authority-convergence.json` immediately after Stage generation. The report must bind the current authority digest, exact endpoint denominator, aggregate/writer/data/NOR projections, durable persistence identity denominator, P1 topology, and any activated dependency lane; any unresolved conflict blocks continuation.
6. If an existing-system architecture-change packet exists, apply its accepted impact/compatibility/rollback decisions without creating a second writer.
7. Route Stage-02.5 only from the accepted dependency decision: `activate`, `internal-local`, `defer`, `exclude`, `return`, or `review-bound`. Vocabulary may only suggest candidates. An accepted `activate` route must render the exact dependency IDs as an active provider-neutral lane unless the authority itself binds a concrete provider.
8. Run wrapper closure, rebuild the semantic commitment union, and re-run canonical convergence after ESP / P3-entry generation so wrapper composition cannot reintroduce generic architecture truth.
9. Require `p2-agentic-architecture-application-receipt.json` to bind the decision digest, `canonical_writer_id`, canonical-convergence report, Stage outputs, ESP, P3 entry, disposition/dependency evidence, and zero missing/unused applications. P2 claim-control lineage handed to P3 must be self-contained: preserve a P2-local portable snapshot of the accepted P1 claim-control surface and make generated P2 sidecars resolve that local surface rather than depending on the original P1 filesystem mount.
10. Promote only the resolved/bounded slices allowed by the accepted handoff; return missing product truth to P1 and missing architecture authoring to P2.

## Required Output Set

A valid Phase-2 package preserves:
- Stage-01 architecture definition
- Stage-02 domain/module decomposition
- Stage-02.5 third-party integration design, or an exact decision-bound skip/return receipt
- Stage-03 data/interface design
- Stage-04 convergence and delivery plan
- `p2-agentic-architecture-authority.json`
- `p2-commitment-disposition-ledger.json`
- `p2-dependency-routing-receipt.json`
- `p2-agentic-architecture-application-receipt.json`
- `p2-canonical-authority-convergence.json` with zero unresolved conflict
- Phase-2 execution report
- Engineering Spec Pack
- Phase-3 implementation entry
- traceability registry evidence
- quality check report
- explicit review-bound and claim-ceiling statements

## Quality Floor

Phase-2 is complete only when:
- every material Phase-1 trace unit is absorbed or explicitly review-bound
- architecture decisions explain why the chosen boundary is useful for delivery
- API, data, interaction, risk, and rollout surfaces are implementation-facing
- exact accepted operations/contracts/aggregate writers/NOR/data decisions are the canonical denominator; no generated CRUD/lifecycle/technology default overrides them
- source-defined P1 product topology survives P2; independent outcomes are not serialized by Stage-02 handoffs, Stage-03 flows, Stage-04 work packages/replays/sequences, or ESP composition
- activated dependency authority is represented by exact dependency IDs and bounded provider/error/test posture rather than vocabulary-derived provider guesses
- ESP is self-contained enough for Phase-3 to start without guessing
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
- `return-to-phase1`: missing product truth blocks honest architecture
- `blocked`: required source, dependency, or decision evidence is absent

Do not call Phase-2 complete when the package only has template shape, pointer-only handoff, or generic architecture language.
