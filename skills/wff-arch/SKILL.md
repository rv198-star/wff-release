---
name: wff-arch
description: Use when running or rerunning a real case through the official Phase-2 design/architecture flow and you need the stable entry, stage-pack navigation, execution report, traceability registry flow, runtime-hardening evidence, and implementation-facing convergence pack.
---

# Phase-2 Design / Architecture Orchestrator

## Overview

This is the **official execution entry skill** for the Phase-2 design / architecture flow in this repo.

It does not replace the four main Stage packs.
It turns them into one bounded execution path so Phase-2 output is not reduced to freewritten architecture prose or isolated manual template filling.

When the case has material external-provider dependence, it also activates the conditional `Stage-02.5 third-party-integration-architecture-design` lane between Stage-02 and Stage-03.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write Stage-01..04 narrative content, Engineering Spec Pack sections, implementation intake text, summaries, and execution-report prose in Chinese
- preserve code, file paths, commands, API/schema field names, trace ids, artifact ids, table names, env vars, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only architecture artifacts, wrapper reports, handoff notes, or audit conclusions unless the user explicitly requests English

## When to Use

Use when:
- the user wants to start a real Phase-2 case from a Phase-1 handoff
- the user wants to rerun or harden an existing Phase-2 case directory
- the output is intended to feed implementation planning or an Engineering Spec Pack
- you need the full phase entry skill, not only one Stage note

Do not use when:
- you are only patching one Stage artifact inside the authored package
- you are only reviewing Phase-2 docs without running a case
- you are only editing source-register / ledger governance docs

## Core Rule

Official Phase-2 delivery must not be treated as "fill four templates manually and stop".

It must explicitly use:
- the authored Phase-2 stage pack set
- the Phase-2 execution report
- wff-base-traceability-management for artifact identity / binding / validation
- runtime-hardening evidence surfaces
- the Engineering Spec Pack convergence target

Official delivery must also meet the Quality Measurement Standards defined in this skill. Output that fails any hard gate is flagged as `quality-gate-fail` in the execution report.

Phase-2 must be generated from Phase-1 trace units top-down, not only from PRD prose.
If a Phase-1 trace unit cannot be shown as explicitly absorbed by a Phase-2 design surface, treat the package as still incomplete even when the Stage artifacts look structurally rich.

A fully passing machine report is a structural integrity signal, not proof that the content is already excellent.
If ADR consequences are shallow, scenario acceptance criteria are unquantified, or diagrams rename core objects into vague aliases, treat the run as still incomplete even when the gate says `pass`.

## Workflow / Context Boundary

Treat Phase-2 as:

> `workflow-fixed design translation + bounded agentic design judgment`

- workflow certainty is high for fresh-root generation, Stage order, trace absorption, wrapper closure, and delivery packaging
- context certainty should be inherited from Phase-1 plus explicit declaration states; if core business truth is missing, return upstream rather than invent it in Phase-2
- agentic scope is limited to boundary options, decomposition alternatives, quality-attribute trade-offs, dependency realism, and targeted context completion
- no open-ended `creative` expansion mode is part of the default Phase-2 mainline
- run targeted loops only when a design artifact is weak, a trade-off is unclear, or downstream would otherwise need to invent key design truth

## v1.2.2 Runtime Protocol

`wff-arch` now follows the `v1.2.2` P2 architecture protocol:

1. consume `P1` truth as upstream truth, not as material for rediscovery
   - read `business/release truth` and `planning/control truth` as separate upstream packs
   - use business/release truth for architecture direction, ADRs, capability sequencing, risk posture, data ownership, and service boundaries
   - use planning/control truth for traceability, handoff, assumptions, dependency recording, and review-bound state
   - if missing truth is actually a P1 business/product problem, return upstream rather than inventing product truth inside P2
2. behave as a delivery-minded architect with ROI-gated extensibility
   - design enough architecture for first delivery and downstream implementation leverage
   - avoid both shortest-path implementation notes and maximal future-state architecture
   - allow forward-looking boundaries only when ROI justifies paying design cost now
   - prefer lightweight extension boundaries over premature full implementation
3. run focused design judgment at high-pressure points
   - architecture boundary choice
   - module/service decomposition
   - data ownership and invariants
   - interface and storage contracts
   - dependency and runtime realizability
   - delivery economics and complexity trade-offs
   - observability, rollout, and operational guardrails
4. classify significant forward-looking design choices into one lane
   - `Mainline Required`: required for first delivery or P3 would need to guess
   - `ROI-Justified Extension Boundary`: not fully required for first delivery, but a low-cost boundary now has clear ROI
   - `Optional / Expert Lane`: potentially valuable, but current ROI is insufficient for the default mainline
5. perform `Extensibility ROI Review` for major extension proposals
   - identify the source of extension pressure from P1 thesis, proof track, or explicit delivery risk
   - compare future migration cost against current reservation cost
   - choose the lightest credible boundary when the ROI is positive
   - reject extension proposals justified only by “maybe later”, local elegance, or enterprise appearance
6. perform `Anti-Overengineering Review` before freeze
   - check whether optional future-state architecture has entered the default path
   - check whether traceability volume is hiding weak design judgment
   - check whether service/module splits raise average implementation or cognitive cost without ROI
   - move attractive but low-ROI architecture into `Optional / Expert Lane`
7. freeze only when the ESP is sufficient, realizable, and ROI-extensible
   - P3 can start without inventing key design truth
   - major boundaries answer `why-this-boundary-not-that`
   - data/interface/storage/compliance/operational posture is explicit where relevant
   - realizability is honest
   - another loop is unlikely to materially improve implementation leverage, delivery economics, robustness, or ROI-justified extensibility

Hard boundaries:

- scripts may expose missing design surfaces, but must not manufacture architecture judgment
- local architecture elegance cannot override system-level delivery economics without ROI
- `P2` must not become a second broad product-discovery phase
- `P2` must not become a narrow implementation note that ignores known extension pressure

## Thinking Value-Gain Generation Strategy

For v1.2.3 exploratory runs, Phase-2 should be ready to apply `Thinking Value-Gain` across major P2 design artifact units after the Phase-1 full-use result proves useful enough to consume.

Use it to increase implementation leverage, not to make architecture more elaborate by default:

- define the design value exit gate before deepening each artifact unit
- strengthen practical value for implementation, test design, runtime evidence, review, reuse, or P3 handoff
- preserve P1 business truth as upstream authority; do not rediscover product value inside P2
- improve trade-off clarity, boundary rationale, API/data contract usefulness, and operation-source traceability
- stop when another round would not materially improve realizability, robustness, or handoff clarity
- move attractive but low-ROI extensions into optional / expert lanes instead of the mainline

P2 full-use targets include:

- engineering strategy posture and ADRs
- service/module/domain/repository boundaries
- API and data contracts
- operation flow / sequence / state / replay source material
- implementation-depth obligation and ACD source matrices
- P3 handoff readiness and review-bound gap statements

This strategy is gated by the P1 result. If P1 full-use produces inflated or lower-signal truth, do not propagate that noise into P2; revert to targeted P2 remediation loops.

## Iteration / Exit Rule

Treat Phase-2 loops as:

> `targeted design remediation loops`, not open-ended business brainstorming

- start another targeted loop only when at least one condition is true: a design artifact is still weak, a trade-off is still unresolved, trace absorption is still incomplete, or the downstream implementation/test phases would still need to invent key design truth
- keep each loop bounded to the affected design surface, such as service boundaries, module decomposition, data contracts, runtime/dependency realism, quality-attribute decisions, or integration posture
- freeze Phase-2 only when Phase-1 business truth is sufficiently inherited, key design decisions are either resolved or explicitly review-bound, wrapper/package closure can complete truthfully, and another round is unlikely to materially improve realizability, robustness, or handoff clarity
- return upstream when the missing truth is actually a Phase-1 problem, or when unresolved business semantics would force Phase-2 to guess product behavior rather than translate it
- mark the run `blocked` when required source artifacts, dependency facts, or design constraints are absent/contradictory enough that even a bounded design loop cannot resolve them honestly

## v1.3.1 Phase Review Breakpoint

At official Phase-2 completion, present a review opportunity before treating the architecture / ESP / implementation-facing handoff package as ready for Phase-3.

The breakpoint must surface the Phase-2 output root, primary artifacts, architecture value judgment, delivery path, constraint response, implementation-facing handoff readiness, open `review-bound` items, evidence basis, claim ceiling, recommended next step, and minimum rerun / return boundary.

Show human-facing review actions in Chinese: `批准`, `带保留项批准`, `要求修改`, `要求返回`, `提供干预输入`, or `明确跳过审核`. Structured records may also preserve stable protocol keys such as `approved` or `return-requested`. New decisions must be recorded as input and rerun or remediated through Phase-2; do not silently patch final artifacts or make human co-authoring the default model.

## v1.3.1 Value-Bearing Closure

Phase-2 closure must be an architecture and delivery judgment, not architecture artifact volume.

Before promoting the Phase-2 package to Phase-3, state whether architecture value, delivery value, evolution value, risk-control value, constraint response value, and implementation-facing handoff value are strong enough for implementation to consume. If P3 would still need to invent contracts, topology, source authority, data ownership, security posture, dependency posture, or implementation depth, return or keep the package review-bound instead of treating diagram count, ADR volume, wrapper pass, or script pass as closure.

If the P2 score is high but no Agentic design / implementation-leverage deepening target is selected, do not imply value gain by default. The closeout must either mark `stable-no-material-gain`, select a bounded high-value design target, or explain why another deepening round would not improve architecture / delivery value.

## v1.3.4 Cross-Phase Pattern Extension

When the active release line is `v1.3.4`, P2 may use the proven Agentic quality and slimming patterns only inside the Phase-2 architecture and handoff boundary.

P2 protected surfaces must remain visible:

- architecture decisions;
- traceability and source absorption;
- security/foundation decisions;
- risk posture;
- Engineering Spec Pack;
- Phase-3 implementation entry;
- operation/source obligation matrices;
- implementation-depth and component action-card obligations;
- quality check, verdict, scorecard, and claim ceiling.

If Review finds a large P2 artifact defect after a phase checkpoint, convert it into a bounded P2 architecture rewrite packet with:

- architecture defect statement and evidence;
- affected ADR / contract / trace / handoff surfaces;
- protected P1 truth that P2 must not reinterpret;
- rewrite scope and downstream consumer to recheck;
- local evidence gate before closure refresh.

Use consumer-aware profile directories only for diagnostic/review mirrors after resolver support exists. Do not move ESP, implementation entry, traceability JSON, source-obligation matrices, security/foundation decisions, or phase verdict surfaces out of normal visibility.

Do not use `v1.3.4` to rediscover product truth inside P2, lower traceability obligations, or replace design judgment with cleaner script output.

## WO-119F.14 P2 Project-Language Handoff

P2 must preserve project language for P3: domain glossary, bounded-context / aggregate candidates, component responsibility, architecture style constraints, and UI/UX intent when frontend surfaces exist.

P2 must not write stack-specific implementation conventions or final service/repository/test/page class names. The P2 role is source-backed language material and explicit missing-language gaps. P3 synthesizes project implementation conventions from this handoff and `tech-stack-decision.yaml`.

## v1.3.7 G.09 P2 Event Model Direct Driver

Before ESP / implementation-facing handoff, form an in-memory `p2-architecture-event-model-driver.v1`.

The driver must include:

- `domain_event_vocabulary`
- `domain_event_model_catalog`
- `producer / consumer / trigger / payload / timing / idempotency`
- `event_versioning_and_schema_posture`
- `p3_event_handoff`
- `review_bound_event_gaps`

Control boundary:

- Workflow keeps order and handoff placement.
- Agentic owns architecture/event-model judgment.
- Templates / TVG shape depth only.
- Evidence / Gates prove traceability and cap claims.

Hard rules:

- Schema checks must not generate architecture judgment.
- Do not create a default heavy event artifact.
- P3 consumes event models; P3 does not invent complete event architecture when P2 is silent.
- If P2 cannot resolve an event model, mark it in `review_bound_event_gaps` with owner, validation path, and downstream usage rule.

## v1.3.1 Runtime References

Use these release-facing references when applying the v1.3.1 Phase-2 control model:

- `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
- `docs/governance/v1.3-product-flow-control-boundary-v0.1.zh-CN.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.zh-CN.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.zh-CN.md`
- `docs/phases/phase-2/p2-value-bearing-artifact-closure-v0.1.md`
- `docs/phases/phase-2/p2-value-bearing-artifact-closure-v0.1.zh-CN.md`

## Release Validation Rule

When validating the released Phase-2 skill itself, use an isolated workspace/session with only the release bundle loaded.
Do not rely on repo-local `AGENTS.md` or unrelated working-context hints to fill missing runtime rules.
For the official retained `GEO + PetClinic` isolation flow, prefer `scripts/release/run_release_dual_case_eval.py` from the built release pack/bundle instead of running directly inside the authoring repo.

## Required Entry Assets

Read these first:
- `docs/phases/phase-2/phase-2-session-bootstrap.md`
- `docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md`
- `reference-packages/phase2-design-architecture/README.md`
- `docs/phases/phase-2/phase-2-execution-report-template.md`
- `docs/phases/phase-2/stage-2-traceability-baseline-v0.1.md`
- `docs/phases/phase-2/stage-2-runtime-hardening-targets-v0.1.md`
- `docs/phases/phase-2/engineering-spec-pack-v0.1.md`
- `docs/phases/phase-2/phase-2-evaluation-criteria-standard-v1.0.md`

Inside the Phase-1 PRD, read these two sections before drafting any Phase-2 content:
- `### Phase-2 Design Input Contract`
- `### Fine-Grained Trace Registry`

Also read `Chosen Business Thesis`, `Business Exploration Arena`, and `Business Proof Track` when present. Phase-2 must be thesis-driven, not merely thesis-aware:
- ADR context, consequences, and rejected alternatives should explain which choices support the thesis proof target.
- Service boundaries must prevent collapse into a read-only dashboard/report, record-only system, or isolated workflow fragment when the thesis requires action, evidence, review, or closure.
- Data models should carry proof artifacts, operational evidence, review decisions, exception closure, or equivalent business-proof objects when the thesis depends on them.
- The Engineering Spec Pack should state which capabilities are first because they support the commercial or operating proof, and which are deferred because they are lower-proof convenience.

Treat them as the machine-readable baseline for Phase-2 authoring.
Do not start from loose PRD prose and attempt to backfill trace ids later.

The four runtime Stage packs remain authoritative for:
- boundary and gate logic
- Stage SOP
- output surface
- method-asset selection

## Required Entrypoints

For an official fresh Phase-2 version, start with the deterministic first-pass generator:

```bash
python3 scripts/phase2/run_phase2_first_version.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <vN> \
  [--pure-prd-direct] \
  [--run-wrapper]
```

This runner:
- scaffolds the fresh case root
- synthesizes authored Stage-01..04 outputs from the Phase-1 authority inputs
- emits first-pass manifest / audit sidecars
- can optionally hand off to the official wrapper in the same run via `--run-wrapper`

Use the lower-level scaffold entry only when you intentionally need a manual/remediation-first authoring flow:

```bash
python3 scripts/phase2/scaffold_phase2_case.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <vN> \
  [--with-stage-02-5]
```

After Stage-01..04 are authored in that fresh case root, use the official closure wrapper:

```bash
python3 scripts/phase2/run_phase2_full_trial.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <rerun-vN> \
  --complexity-profile <auto|micro|standard|complex> \
  --profile <implementation-planning-ready-design-package> \
  [--stage-02-5 <stage-02.5-third-party-integration-architecture-design.md>]
```

Current first-pass generation scope:
- `scripts/phase2/run_phase2_first_version.py` is the official fresh-version synthesis runner
- it scaffolds the case root, authors Stage-01..04, emits `phase-2-first-pass-generation-manifest.md`, and persists `phase-2-first-pass-audit.json`
- it derives the first-pass package from Phase-1 authority inputs plus the official Stage packs rather than from prior Phase-2 prose
- when `--run-wrapper` is enabled, it hands the authored case root to `scripts/phase2/run_phase2_full_trial.py`

Canonical mainline rule:
- for the default official Phase-2 mainline, treat `scripts/phase2/run_phase2_first_version.py --run-wrapper` as the single canonical command surface
- treat `scripts/phase2/run_phase2_full_trial.py` as the closure wrapper over authored Stage outputs, primarily for manual/remediation-first flows or explicit rerun closure on an already-authored case root

Current wrapper scope:
- consumes authored Stage-01..04 output documents
- auto-detects the optional Stage-02.5 lane when it exists in the case root, or consumes it explicitly via `--stage-02-5`
- re-audits fresh first-pass case-root hygiene and emits `phase-2-first-pass-audit.json`
- blocks wrapper closure when Stage-01..04 are still scaffold-only stubs, and also blocks if a present Stage-02.5 file is still only a scaffold stub
- initializes/binds/registers/validates Phase-2 traceability
- emits the Phase-2 execution report
- emits the Engineering Spec Pack
- emits the Phase-3 implementation entry note

For standalone quality checks outside the wrapper, include the Phase-1 PRD so the coverage contract is enforced:

```bash
python3 scripts/phase2/phase2_quality_check.py \
  --phase1-prd <phase1-prd.md> \
  --stage-01 <stage-01.md> \
  --stage-02 <stage-02.md> \
  [--stage-02-5 <stage-02.5.md>] \
  --stage-03 <stage-03.md> \
  --stage-04 <stage-04.md> \
  --complexity-profile <micro|standard|complex> \
  --output <quality-check-report.json>
```

Complexity-profile rule:
- `auto` (recommended): runner reads the Phase-1 PRD, classifies `epic_count / requirement_count / external_integration_count / domain_count_hint`, and selects the suggested profile automatically
- manual override is allowed, but if the selected profile differs from the suggested one, provide `--complexity-override-justification <reason>`
- `micro`: preserve the same traceability and depth discipline, but allow smaller count-based minima where the case shape is genuinely simpler
- `standard`: current default; this preserves the historic Phase-2 minimums
- `complex`: raises the active minima for architecture decisions, events, schemas, APIs, scenarios, sequences, work packages, and observability surfaces when the case shape is materially deeper
- `complexity-profile` scales output thresholds; it does **not** by itself authorize a heavier deployment or infrastructure posture
- deployment/infrastructure posture is governed separately by `docs/phases/phase-2/phase-2-deployment-posture-tiering-rule-v0.2.md`; high-spec design discipline may remain constant across tiers, while AI must not silently upgrade runtime/infrastructure weight and human-forced override remains warning-bearing

The wrapper does **not** auto-generate Stage-01..04 content from scratch.
Official fresh first-pass generation now happens through `scripts/phase2/run_phase2_first_version.py`, which uses the Phase-1 authority inputs plus the official Stage packs to author a newly scaffolded Phase-2 case root.

## Official Working Root

Use the case-first local artifact layout:

- `tmp/local-artifacts/<case-name>/phase-1/`
- `tmp/local-artifacts/<case-name>/phase-2/`

Keep generated case outputs there rather than inside `reference-packages/` or `release-cases/`.

## Fresh First-Pass Rule

Every new Phase-2 version must begin in a fresh case directory.

That means:
- for official fresh runs, start with `scripts/phase2/run_phase2_first_version.py`
- for low-level manual flows, scaffold the new case root first and author Stage-01..04 into that directory
- run the wrapper only after the new Stage outputs exist

Do not treat a previous Phase-2 case directory as the editable baseline for a new version.
If an earlier Phase-2 case is consulted, treat it as a sidecar comparison source and restate reused claims from fresh evidence.

## Execution Sequence

1. Confirm the upstream Phase-1 handoff package and the canonical Phase-2 case root.
2. Read the PRD's `Phase-2 Design Input Contract` and turn it into a top-down absorption plan before drafting any Stage prose.
3. If this is a new official Phase-2 version, run `scripts/phase2/run_phase2_first_version.py` against a fresh case root; only drop to `scripts/phase2/scaffold_phase2_case.py` when you intentionally need manual/remediation-first authoring.
4. Audit the case root with `scripts/phase2/validate_fresh_first_pass_case.py`; if it still reports `scaffold-only`, do not run the wrapper yet.
5. If manual authoring/remediation is active, author or refresh Stage-01..04 using the existing authored Stage packs.
   If Phase-1 or Stage-01 / Stage-02 reveals material third-party dependencies, author Stage-02.5 between Stage-02 and Stage-03 in the same case root.
   For Stage-03, treat tradeoff-heavy reasoning as a closure bundle rather than a single comparison table: if technology selection or materially different alternatives are in scope, also author `baseline_insufficiency_note`, `constraint_dominant_optimum_candidate`, and `key_tradeoff_decisions`, or explicitly justify why the bundle does not apply.
6. Prefer `scripts/phase2/run_phase2_first_version.py --run-wrapper` as the official one-shot mainline. Run `scripts/phase2/run_phase2_full_trial.py` directly only when the Stage outputs already exist and the current task is explicit manual/remediation closure.
7. Either way, the wrapper will re-audit the case root and persist the audit artifact before closure.
8. Let the wrapper initialize the Phase-2 trace registry, bind the Stage outputs, register the coarse chain, validate it, and emit the reports/packs.

## Top-Down Absorption Rule

Before Stage-01, convert every Phase-1 contract row into a concrete Phase-2 absorption target:
- `primary-user-story` / `use-case`: bind explicitly in Stage-03 `scenario_coverage_matrix` and/or Stage-04 `verification_replay_evidence`
- `requirement`: bind explicitly in Stage-01 `decision_trace_registry`, Stage-03 `contract_trace_registry`, and Stage-04 `rbi_trace_registry` when implementation risk or intake control exists
- `acceptance-criteria`: bind explicitly in Stage-03 scenarios/contracts and Stage-04 replay evidence

Coverage hotspot rule:
- do not treat `return-for-clarification`, `boundary visibility`, or `navigation continuity` as implicitly covered by a generic happy path
- if Phase-1 includes trace units for clarification fallback, scope-boundary / non-goal visibility, or `overview -> findings -> tasks -> reports` continuity, bind them explicitly in a Stage-03 scenario/contract row and/or a Stage-04 replay row
- sequence diagrams alone are not enough for the coverage contract when the machine report only consumes scenario/contract/replay tables

Do not rely on fuzzy matching as the primary mechanism.
Inference exists only as remediation support for legacy artifacts that predate the contract.

## Phase-1 UI Artifact Preservation Rule

Phase-2 Stage-04 must preserve the following Phase-1 prototype-spec artifacts as authoritative inputs for Phase-3 frontend implementation:

1. `page_map`
   The page names, roles, and blueprint types defined in P1-S05 prototype-spec are the canonical surface definitions. Phase-2 may add engineering annotations, but it must not replace those page names with API-endpoint-derived labels.
2. `page_blueprint_type`
   Each page's blueprint type must be carried through to Phase-3 as a binding layout constraint, not a soft suggestion.
3. `prototype_generation_constraints`
   The constraints from P1-S05 §9 such as `must_present_as_business_product_not_demo_shell` and `must_not_render_demo_console_or_api_explorer` are Phase-3 disqualifiers, not optional style notes.
4. `prototype-prompt-pack.md`
   When present, this artifact must be referenced as supplementary UI design guidance because it preserves page-level interaction and visual intent that the engineering spec alone does not fully capture.

Stage-04 output requirements, in addition to the normal handoff:
- include `surface_provenance` as either `phase1-prototype-spec` or `api-endpoint-inferred`
- include `phase1_prototype_spec` as a path reference to the Phase-1 prototype-spec artifact
- keep `primary_surfaces` aligned to the P1 page map whenever that evidence exists
- include a surface-to-blueprint mapping so Phase-3 can preserve the intended layout pattern

Fine-grained Phase-2 document ids must preserve the prefixed form:
- `P2-DTR-*`
- `P2-CTR-*`
- `P2-RP-*`
- `P2-RT-*`

These ids are the stable handles that prove a specific Phase-1 trace unit was absorbed by a concrete Phase-2 design surface.

## Required Traceability Flow

Use:

```bash
python3 skills/wff-base-traceability-management/scripts/init_registry.py \
  --project-root <case-phase2-root> \
  --project-key <case-key>
```

Then bind artifacts and validate/report:

```bash
python3 skills/wff-base-traceability-management/scripts/bind_artifact.py ...
python3 skills/wff-base-traceability-management/scripts/register_phase2_pilot.py ...
python3 skills/wff-base-traceability-management/scripts/validate_registry.py ...
python3 skills/wff-base-traceability-management/scripts/report_registry.py ...
```

Do not leave `artifact_id / depends_on / feeds` as prose-only placeholders when the run is treated as official.

## Required Output Set

A valid official Phase-2 run should preserve:
- Stage-01 output
- Stage-02 output
- Stage-02.5 output when the optional lane is active
- Stage-03 output
- Stage-04 output
- Phase-2 execution report
- Engineering Spec Pack (self-contained; see ESP Content Requirements below)
- Phase-3 implementation entry note
- `phase-2-first-pass-audit.json`
- `phase-1-to-phase-2-coverage.json`
- traceability validation result
- traceability report summary
- `baseline-lock.json` (mandatory for reruns; recommended for initial runs)
- `quality-check-report.json` (generated by quality check tooling)

## Quality Measurement Standards

Every official Phase-2 run must produce output that meets the following minimum quantitative thresholds.
These thresholds are hard gates, but they are interpreted through the active `complexity-profile` rather than one global GEO-shaped floor.
`standard` keeps the historic minima below; `micro` may use reduced count-based thresholds where the architecture shape is truly smaller, while still preserving traceability, decision depth, and implementation realism; `complex` raises the active minima on larger platform-like cases.

### Stage-01 Minimum Thresholds
- architecture_decisions: ≥7 (using standard ADR format; see Architecture Decision Record Format below)
- thesis_driven_architecture_translation: when Phase-1 exposes a chosen thesis, Stage-01 must translate it into proof-supporting architecture choices, anti-collapse boundaries, proof-object modeling, and capability sequencing
- forbidden_assumptions: inherit all from Phase-1 (≥5)
- constraint_categories: all 4 (inherited / inferred / unknown / deferred)
- quality_attributes: ≥4 with quantified targets (P95 latency, SLA, etc.)
- capacity_estimates: ≥3 specific numbers (TPS/QPS, latency target, storage growth)
- mermaid_diagrams: ≥3 (C4Context required for system boundary + flowchart for capability map + sequenceDiagram for auth flow)
- security_architecture_sketch: explicit auth sequence diagram + token/session posture + key-management posture; generic RBAC wording alone does not satisfy Stage-01 depth

### Stage-02 Minimum Thresholds
- domains: ≥4 with core/support/generic classification
- modules: ≥4 business + ≥1 support
- service_candidates: ≥8
- canonical_object_structure: machine-readable rows covering every aggregate/object carried into Stage-03
- service_endpoint_mapping: ≥8 rows mapping Stage-02 services to Stage-03 endpoint/contract surfaces
- state_diagrams: ≥3 (Mermaid stateDiagram-v2 for key aggregates)
- domain_events: ≥10 with payload_shape, ordering_semantics, and idempotency_rule
- er_diagram: 1 (Mermaid erDiagram with ≥10 entities and aggregate root markers)


### Shared Operation Risk And Source Obligations

P2 must use the shared operation risk model in `docs/v1.2-operation-risk-tiering-and-source-obligations-v0.1.md`.

P2 is the source of truth for per-operation risk tier and required behavior-source types. For every public `P2-CTR-*` operation, P2 must emit a row containing:

- `operation_id`
- `risk_tier` (`HR-MUTATION`, `HR-BOUNDARY`, `HR-ORCHESTRATION`, `MR-READ-SENSITIVE`, or `LR-SIMPLE-READ`)
- `risk_triggers`
- `required_source_types`
- `bound_source_ids`
- `review_bound_missing_sources`
- `not_required_source_types`
- `classification_rationale`

High-risk operations must not be satisfied by diagram count alone. If `P2-FLOW-*`, `P2-SEQ-*`, or `P2-STATE-*` is required by the shared risk table, the source must be operation-bound and registered through `wff-base-traceability-management`, or the missing source must be explicitly review-bound. Abstract labels such as `P2-FLOW` / `P2-SEQ` / `P2-STATE` are source types, not implementation-ready source IDs; P2 must bind them to concrete `P2-FLOW-*`, `P2-SEQ-*`, `P2-STATE-*`, or `P2-RP-*` IDs before P3 may treat the source as available.

P3 must consume these P2-authored rows; therefore P2 must not leave risk tiering implicit in prose. If P2 does not emit the row, P3 must treat the operation as review-bound rather than inventing a local tier.

### Action Card Depth Coefficient Obligations

P2 is also the authoritative synthesis layer for `Action Card Depth Coefficient` (`ACD`). It must combine P1 business value signals with P2 engineering risk and implementation complexity.

P2 must emit the full bridge chain needed by P3 action cards, without local invention or silent downgrade:

- `p1_value_to_p2_operation_resolution_matrix` mapping P1 value signals to P2 operations
- `operation_source_obligation_matrix` for operation-bound source requirements
- `implementation_depth_obligation_matrix` combining `business_value_weight`, `engineering_risk_tier`, and `implementation_complexity` into authoritative `acd_level`
- `implementation_component_catalog` for Service / Domain / Repository / Adapter units
- `component_action_card_obligation_matrix` for implementation action-card obligations

Every component obligation row should contain:

- `component_id`
- `component_type` (`service | domain | repository | adapter`)
- `upstream_operation_ids`
- `upstream_p1_trace_ids`
- `business_value_weight`
- `engineering_risk_tier`
- `implementation_complexity` (`IC0 | IC1 | IC2 | IC3`)
- `acd_level` (`ACD-0 | ACD-1 | ACD-2 | ACD-3`)
- `required_card_type` (`slim | standard | deep | split-required`)
- `required_reason`
- `required_tests`
- `required_source_ids`
- `available_source_ids`
- `missing_source_types`
- `source_sufficiency_status` (`sufficient | partial | review-bound | blocked`)
- `review_bound_missing_sources`

P2 must not leave implementation-card depth implicit in prose. It must distinguish required depth from available design material. Missing P1 value signals, missing operation rows, missing concrete P2 source IDs, or missing component catalog rows are review-bound/blocking gaps, not `ACD-0`. P3 may only consume, validate, raise, or mark review-bound; it must not locally downgrade ACD or invent missing design material. Every component action-card obligation with `upstream_operation_ids` must carry non-empty `upstream_p1_trace_ids`; fallback propagation is allowed only when marked review-bound, because trace continuity is still better than a P3-local card with no P1 anchor.

### Stage-03 Minimum Thresholds
- schema_tables: ≥10 with summary rows plus per-table field registry (`field_name + data_type + nullable + constraints + index_hint`); field types must be implementation-facing rather than generic placeholders such as `string` / `number`
- access_pattern_and_index_strategy: ≥5 rows mapping hot query/access paths to proposed indexes with write-cost note + validation hook
- data_sensitivity_and_compliance_matrix: coverage for every schema table (`table_name + pii_level + sensitive_fields + masking/encryption + retention + audit access + compliance note`)
- api_endpoints: ≥10 with parseable JSON request/response examples
- api_failure_semantics: every endpoint must declare typed failure semantics with HTTP status code plus caller-visible meaning; mutating or dependency-heavy endpoints should usually expose ≥3 distinct failure outcomes, while simpler read endpoints may legitimately carry fewer when the risk model is narrower
- response_and_error_contract: canonical success/error contract with `business_error | system_error` split, retryability posture, caller action, and trace handle
- endpoint_error_controls: implementation-facing endpoints must declare `response_profile + retryability_policy + idempotency_rule`
- tech_selection_candidates: ≥5 with multi-dimensional comparison depth (reliability, performance/capacity, scalability, maintainability, cost, security/compliance, deployment complexity, evidence, decision)
- tech_selection_dimensions: ≥10
- tech_selection_long_term_ops_dimensions: every candidate must explicitly cover `operations_cost / TCO`, `ecosystem_maturity / community_support`, and `observability`; long-term operations cannot be left as implied familiarity
- tradeoff_closure_bundle: when technology selection / alternative evaluation is active, Stage-03 should also expose `baseline_insufficiency_note`, `constraint_dominant_optimum_candidate`, and `key_tradeoff_decisions`; do not stop at the matrix alone
- scenarios: ≥8 (including ≥2 failure path scenarios, ≥2 concurrent-conflict scenarios, and quantified acceptance criteria + measurement hook on every row)
- scenario_gwt_compatibility: warning rollout in the current cycle; target `>=50%` of scenario rows with explicit `given/when/then` columns or GWT wording inside `acceptance_criteria`
- scenario_upstream_trace_binding: every scenario row explicitly binds upstream Phase-1 trace ids via `upstream_trace_ids`
- mermaid_diagrams: ≥2 core diagrams (data ownership + deployment assumption); add a third trust/security diagram when external trust boundaries materially shape contract or deployment behavior
- storage_strategy: capacity estimate (initial/1year/3year) + partition strategy + archival rule
- security_outline: auth sequence, token posture, and key-management posture must be explicit and non-placeholder

### Stage-04 Minimum Thresholds
- sequence_diagrams: ≥3 (happy path + retry/clarification + governance block)
- work_packages: ≥4
- gantt_diagram: 1 (Mermaid gantt for implementation timeline)
- rbi_items: each with risk_level (H/M/L) + spike_wp binding + responsible_party
- observability_and_operational_readiness: ≥4 rows covering logs + metrics + alerts + SLO/threshold + owner + rollout guardrail
- replay_upstream_trace_binding: every replay row explicitly binds upstream Phase-1 trace ids via `upstream_trace_ids`
- convergence_diagram: 1 (C4Container for convergence architecture)
- design_verification: structured checklist (check_item / result [pass/fail/partial] / evidence / gap)

### Execution Report Minimum Thresholds
- deliverable_judgment_matrix: all `mandatory` deliverables plus all triggered `conditional` deliverables must be judged and mapped; do not force every case to fill the same fixed row count
- baseline_lock_dimensions: ≥18 with specific numeric values (see Baseline Lock Scorecard)
- regression_gate_dimensions: ≥10 with per-dimension comparison (baseline_value / rerun_value / delta)
- review_bound_ratio: computed numeric value (not "see source" or "not-computed")
- review_bound_ceiling: 30% — if exceeded, must justify or resolve top 3 items
- stage_summaries: each with specific strongest/weakest output references (not "see source stage output")
- cross_stage_consistency_check: performed and results recorded
- anti_gaming_semantic_sampling: deterministic sample of 1 ADR + 1 endpoint + 1 scenario after quantitative gates; in the current rollout this is a warning-calibration surface, not an automatic gate-fail by itself
- phase1_phase2_coverage_contract: every Phase-1 trace unit is either explicitly absorbed by Phase-2 design surfaces or the run fails with a machine-readable gap report
- Engineering Spec Pack implementation delta: include quick-start path, working glossary, implementation start order, schema/data migration focus, contract freeze/adapters, rollout guardrails, and identity/auth lifecycle posture
- Phase-3 implementation entry: include a structured intake checklist (≥6 rows), explicit start sequence, and onboarding snapshot/glossary

## Uncertainty Compression and Bounded Default Rule

Official Phase-2 quality is not improved by repeating `unknown`, `deferred`, or `review-bound` across every table.
The preferred outcome is a design package that preserves real uncertainty once, in the right place, while still choosing a bounded implementation posture everywhere else.

Apply these rules in every official run:
- Prefer a bounded default, policy-configurable guardrail, or substitute boundary when the missing fact does not change the architecture fork.
- Use `unknown` only when the missing fact would materially change boundary, ownership, storage, interface, or delivery shape.
- Use `deferred` only for an explicit out-of-scope seam. Record it once in the owning decision / seam registry / RBI entry, then reference it elsewhere without re-marking every row.
- Use `review-bound` only for a still-open architecture truth with an owner, validation path, and downstream usage rule.
- Workflow states such as `blocked`, `returned_for_clarification`, `retrying`, or policy-denied outcomes are normal domain semantics. They are not, by themselves, unresolved-truth markers.
- One unresolved fact should have one canonical home:
  - Stage-01 for boundary-shaping uncertainty
  - Stage-03 for contract/substitute-boundary realism notes that affect interface or storage shape
  - Stage-04 RBI table for implementation-intake ownership, spike binding, and deadline
- Do not duplicate the same unresolved fact across ownership maps, event catalogs, API tables, scenario matrices, handoff notes, and readiness labels. Reference the owning decision id or RBI id instead.
- Target a practical pre-gate budget of `<=20%` unresolved structured items per Stage. The `30%` ceiling is the hard stop, not the design target.

## Diagram Type Standard

All Phase-2 Mermaid diagrams must use the following syntax types.
Using a weaker syntax type (e.g. flowchart instead of C4Context) is a quality-gate failure.

| Diagram Purpose | Required Mermaid Syntax | Stage | Min Count |
|---|---|---|---|
| System context | `C4Context` | Stage-01 | 1 |
| Capability map | `flowchart TD` | Stage-01 | 1 |
| Authentication sequence | `sequenceDiagram` | Stage-01 | 1 |
| Decomposition/dependency | `flowchart LR` | Stage-02 | 1 |
| Conceptual ER | `erDiagram` | Stage-02 | 1 |
| Aggregate lifecycle | `stateDiagram-v2` | Stage-02 | ≥3 |
| Data ownership | `flowchart LR` with subgraph | Stage-03 | 1 |
| Deployment assumption | `flowchart LR` | Stage-03 | 1 |
| Convergence architecture | `C4Container` | Stage-04 | 1 |
| Critical interaction | `sequenceDiagram` | Stage-04 | ≥3 |
| Implementation timeline | `gantt` | Stage-04 | 1 |

Diagram quality rules:
- Node labels must be meaningful (no A/B/C placeholders)
- Edges must have text labels (no unlabeled arrows)
- ≥5 nodes per diagram, ≤25 nodes (split if larger)
- Must render without Mermaid syntax errors
- Stage-02 decomposition/dependency flowcharts must expose actual `module_map` names, not only business-friendly aliases
- Stage-03 data-ownership flowcharts must expose real `schema_draft` table labels, not only abstract nouns
- Stage-03 `schema_draft` must not stop at summary rows; the per-table field registry is part of the mandatory output, not optional elaboration
- Stage-03 `scenario_coverage_matrix` must not stop at failure notes; every row needs measurable acceptance language
- Stage-04 sequence participants that represent services must use the exact Stage-02 `service_candidates` names
- `scripts/phase2/run_phase2_full_trial.py` will request Mermaid render validation automatically when `mmdc` is installed; if `mmdc` is absent, renderability remains an open validation gap rather than proven correctness
- C4Context/C4Container are mandatory for the system-level views listed above; plain flowchart is not an equivalent substitute

## Self-Review Calibration Protocol

When self-reviewing a Phase-2 case:
- For every scored dimension or sub-dimension at `>=9.0`, provide at least one depth evidence example that points to a concrete section/table/diagram and explains why it meets the `9.5` bar, not merely why the section exists.
- For every dimension, check the `9.5` expectation explicitly. If a `9.5` requirement is not met, cap that dimension at `8.5` even if the structure is otherwise complete.
- Apply a `-0.3` calibration haircut when the content exists but the claimed depth still depends on inference, placeholder-like wording, or thin rows that only mirror the template.
- Do not treat a passing machine report as enough evidence for a `9.0+` self score. Machine pass proves structural integrity first; the self review must still prove depth.

## Engineering Spec Pack Content Requirements

The ESP must be self-contained — an implementation team should be able to understand
the full design context without repeatedly consulting the four Stage documents.

### Minimum Inline Content (not just pointers)

The ESP must inline at least:

1. **Architecture Summary** (≥200 words):
   - system boundary (1 paragraph + C4Context diagram reference)
   - architecture direction and key decisions (table of ≥7 decisions with status)
   - constraint posture summary (inherited + inferred count, key items)

2. **Schema Summary** (≥10 tables):
   - table name + key columns + data types + PK/FK
   - (full field-level detail remains in Stage-03, but the summary must include types)

3. **API Summary** (≥10 endpoints):
   - method + path + purpose + key request/response fields
   - (full JSON bodies remain in Stage-03, but the summary must include field names)

4. **Key Decisions Quick Reference** (table):
   - AD-ID + decision + rationale + status (1 row per decision)

5. **Risk Summary** (table):
   - RBI-ID + description + risk level + spike WP + responsible party

6. **Realizability Judgment**:
   - delivery_path_realism + substitute_boundary + realizability_judgment

7. **Implementation Delta Sections**:
   - implementation start order from work-package registry
   - schema/data migration focus for first build
   - contract freeze and adapter boundaries
   - operational rollout guardrails from RBI/WP bindings

An ESP that only contains section-to-source mappings without inline content
is graded as `quality-gate-fail` on D4.11.

### Minimum ESP Size
- ≥320 lines (pointer-only ESPs of ~73 lines are not acceptable)
- ≥6 substantive sections with inline content

## Phase-3 Implementation Entry Requirements

The Phase-3 implementation entry is not allowed to be a short "you may start" note only.

It must include:
- intake metadata and strongest supported readiness label
- a structured intake checklist with at least 6 rows
- an explicit Phase-3 start sequence that names the first work-package chain
- guardrails that preserve public contracts, RBI ownership, and traceability constraints

## Architecture Decision Record Format

All key architecture decisions (≥7 per Phase-2) must use this structured format
in Stage-01 and be carried forward into the ESP:

```
### AD-XX: [Decision Title]

- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: Why this decision is needed. What problem or constraint drives it.
- **Decision**: The specific choice made.
- **Alternatives Considered**:
  - Alternative A: [description] — rejected because [reason]
  - Alternative B: [description] — rejected because [reason]
- **Consequences**:
  - Positive: [list]
  - Negative: [list]
  - Risks: [list]
- **Evidence**: [URLs, benchmarks, or references supporting the decision]
```

Decisions that only have "decision + rationale" without context/alternatives/consequences
are graded below 8.0 on D1.6.

## Cross-Stage Consistency Validation

Before the execution report is finalized, the following cross-stage checks must be performed:

### Terminology Consistency
- Every domain name used in Stage-02 must appear in Stage-01's capability map
- Every module name in Stage-02 must be referenced in Stage-03's data ownership map
- Every service candidate in Stage-02 must have ≥1 API endpoint in Stage-03
- Every aggregate with a state lifecycle in Stage-02 must have a stateDiagram

### Decision Consistency
- No two Stages may contain contradictory architecture decisions
- Stage-04's convergence must reference all decisions from Stage-01

### Naming Consistency
- Public boundary names in Stage-03 must match the conceptual ER in Stage-02
- API endpoint names must be consistent with service candidate names
- Domain event names must match the event catalog in Stage-02
- Two-token fuzzy aliases are not sufficient when the distinguishing token carries meaning (for example `Snapshot`, `Payload`, `Contract`, or `Endpoint`)

### Quantitative Consistency
- Capacity estimates in Stage-01 must be reflected in Stage-03's storage strategy
- Schema table count must be ≥ aggregate count from Stage-02

If any inconsistency is found, it must be listed in the execution report's
Cross-Stage Consistency Check section with a resolution or justification.

## Rerun Rule

When rerunning an existing case, the following protocol is MANDATORY (not advisory):

### Step 1: Baseline Lock
Before any content is regenerated:
1. Read all prior Stage outputs
2. Compute the baseline scorecard covering at minimum:

| Dimension | Metric | How to Count |
|---|---|---|
| Stage-01 line count | `wc -l stage-01*.md` | total lines |
| Architecture decisions | count AD-XX entries | ≥7 required |
| Forbidden assumptions | count FA-XX entries | must equal Phase-1 total |
| Mermaid diagrams (by type) | count ` ```mermaid ` blocks | per type (C4Context, stateDiagram, sequenceDiagram, erDiagram, gantt) |
| Stage-02 domains | count domain entries | ≥4 required |
| Stage-02 state diagrams | count stateDiagram blocks | ≥3 required |
| Domain events | count event entries | ≥10 required |
| Stage-03 schema tables | count table entries | ≥10 required |
| Stage-03 API endpoints | count endpoint entries | ≥10 required |
| Stage-04 sequence diagrams | count sequenceDiagram blocks | ≥3 required |
| Stage-04 work packages | count WP entries | ≥4 required |
| RBI items | count RBI entries | with risk level |
| Scenario count | count scenario entries | ≥8 required |
| Public boundary names | count public name entries | all must be closed |

3. Write the scorecard to `baseline-lock.json` in the case directory

### Step 2: Regression Gate
After regeneration, compare every dimension:
- If any dimension is LOWER than baseline → BLOCKED
- The author must either:
  - (a) fix the regression, or
  - (b) provide explicit justification in the execution report's regression gate section
  - "Accidentally omitted" or "simplified for readability" without replacing the information is NOT acceptable

### Step 3: Mandatory Diff
The execution report must include a structured delta table comparing against the EARLIEST complete baseline (not just the previous rerun):

| dimension | baseline_value | rerun_value | delta | justification_if_negative |
|---|---|---|---|---|
| (each dimension from Step 1) | (specific number) | (specific number) | +N/-N | (required if negative) |

### Step 4: Review-Bound Ceiling
- Compute: review_bound_ratio = review_bound_items / total_structured_items
- Count unresolved-truth markers, not ordinary workflow failure-state words used inside state machines, API semantics, or scenario narration
- If ratio > 30%: the author must attempt to resolve the top 3 items or justify why resolution is blocked
- The computed ratio must appear in the execution report Section 7

### Step 5: No Unfinished Abandonment
- If a rerun produces fewer than 4/4 stages, it must either:
  - Complete all stages, or
  - Document why it was abandoned with a comparison verdict and a CLOSED status

Also apply:
- `skills/wff-meta-stage-skill-construction-lifecycle/SKILL.md`
- Phase 7 rerun / iteration protocol

## Runtime-Hardening Rule

Official Phase-2 reruns should preserve or regenerate:
- `runtime-decision-log.md`
- `state-transition-record.md`
- `failure-path-output.md`

for each Stage where runtime-hardening evidence is part of the current package baseline.

## Manual Mode Boundary

Manual single-Stage use is still allowed for:
- authoring
- debugging
- targeted remediation
- review of one weak artifact

But that is not the preferred official phase entry skill anymore.

## Quick Reference

| Need | Do This |
|---|---|
| Start an official Phase-2 case | open `docs/phases/phase-2/phase-2-session-bootstrap.md` + use this skill + `scripts/phase2/run_phase2_first_version.py --run-wrapper` |
| Run one authored Stage correctly | use that Stage pack under `reference-packages/phase2-design-architecture/` |
| Bind the run into controlled traceability | let `scripts/phase2/run_phase2_full_trial.py` call `wff-base-traceability-management` scripts |
| Produce implementation-facing closure | let `scripts/phase2/run_phase2_full_trial.py` emit the Engineering Spec Pack + implementation entry |
| Rerun without silent regression | apply lifecycle Phase 7 baseline lock + diff protocol |
