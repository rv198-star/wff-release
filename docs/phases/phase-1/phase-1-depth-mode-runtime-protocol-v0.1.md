# Phase-1 Depth-Mode Runtime Protocol（v0.1）

## Purpose

This document turns the current `v1.2` Phase-1 design decisions into an actual runtime / skill protocol.

It exists so `wff-req` stops being only:

- deep-stage generation
- PRD assembly
- convergence gates
- execution report

and becomes explicitly responsible for:

- depth-mode selection
- bounded deepening discipline
- anti-demo review
- real-world baseline calibration when needed
- honest freeze / return / blocked decisions

This is the first `v1.2` bridge between:

- design principles
- Phase-1 thinking docs
- actual skill/runtime behavior

Companion documents:

- `docs/v1.2-design-principles-v0.1.md`
- `docs/v1.2-phase-thinking-mode-split-v0.1.md`
- `docs/internal/improvement-reports/v1.2-business-depth-sufficiency-and-superpowers-inspired-agent-loop-v0.1.md`
- `docs/v1.2-mainline-scoring-and-acceptance-matrix-v0.1.md`

---

## 1. Activation Rule

Every official `wff-req` run must start by selecting one explicit depth mode.

Allowed modes:

- `baseline`
- `creative`

### `baseline`

This is the default.

Use when:

- the user did not explicitly ask for stronger creative exploration
- the main need is a strong, credible, implementation-ready product world

### `creative`

Use only when the user explicitly asks for:

- stronger ideation
- deeper value exploration
- new scenario or business-model discovery

Hard boundary:

> `creative` starts only after `baseline` sufficiency exists.

It does not bypass baseline.

## 1.1 Workflow / Context Certainty Rule

Treat `Phase-1` as:

- workflow-fixed at the outer shell
- context-uncertain at the business-truth layer

Therefore:

- workflow controls stage order, required passes, gates, and handoff surfaces
- agentic work controls scenario deepening, trade-off selection, anti-demo review, and real-world baseline calibration
- agentic work is also responsible for sharpening business value, not merely thickening business description
- user task/flow experience may be improved as a secondary objective, but it must stay subordinate to business value and decision leverage
- scripts must not flatten domain language or manufacture business certainty
- when baseline sufficiency depends on external reality, the runtime should prefer explicit evidence or calibration over generic self-generated completion
- for `commercial-decision` or `mixed` cases, the outer workflow may stay fixed while scenario content remains high-uncertainty work; runtime/gates must not treat generic business wording as a substitute for domain-specific commercial truth
- if the source brief already carries explicit business semantics such as buyer/budget chain, competitor context, typed recommendation payload, or continue / revise / pause consequence, compiled `P1` scenarios must preserve those semantics rather than collapsing them into generic scenario shells
- if business-value, budget, or decision-leverage checks can be satisfied by reusable template phrases alone, the runtime contract is too weak and should be treated as drift from the `Workflow controls process / Agentic resolves uncertainty` rule
- when `buyer/budget chain` is a live uncertainty, the runtime should explicitly materialize: `pain holder`, `continuation owner`, `spend at risk`, `proof artifact for continue`, and `continuation signal`; if these remain implicit, keep the chain review-bound and continue looping
- explicit field presence is necessary but not sufficient; `business_world_model`, `truth spine`, or `buyer_budget_chain` field completion alone does not prove business understanding
- do not freeze high-uncertainty business truth into structured fields before the business world has materially thickened and the value mechanism has become clearer
- truth surfaces such as `business_world_model`, `truth spine`, `buyer_budget_chain`, or `proof_artifact_for_continue` must compress business judgment; they must not devolve into repeated workflow chains, contract-noun spillover, or source recompilation dump
- if a structured truth surface becomes longer, more repetitive, or less decisive than the scenario reasoning it is supposed to summarize, treat that as `workflow creep`, not stronger agentic output
- the sequence may be workflow-controlled, but the work inside each pass must not be template-controlled; each pass still requires agentic comparison, deepening, calibration, and judgment rather than slot-filling alone
- in other words: `outer order may be procedural; inner business thinking must not become procedural`

## 1.1.1 P1 Product / Source Direct Driver

Before Stage / PRD authoring freezes the product argument, Phase-1 must build a compact in-memory driver:

```text
p1-product-source-direct-driver.v1
```

This driver is not a gate and not a new default heavy artifact. It is the Agentic product/source judgment surface that downstream P1 writers consume.

Required driver judgment units:

- `source_truth_admission`: what may enter P1, what remains review-bound, and the claim ceiling
- `product_judgment`: what product should exist, for whom, and why the current substitute is not enough
- `commercial_judgment`: who continues / revises / pauses and what proof changes that decision
- `business_feasibility`: the feasible business path under current evidence
- `mvp_wedge`: the narrowest valuable wedge and what stays deferred or review-bound
- `acceptance_meaning`: what acceptance should prove as business value, not just field or workflow completion
- `open_truth_gap_routing`: where missing truth must return if it changes product judgment
- `forbidden_downstream_assumptions`: what P2/P3/P4 must not invent or silently upgrade
- `value_deepening_targets`: bounded TVG / Agentic targets with explicit value exits
- `business_completeness_driver`: the compact business completeness judgment surface when source signals support one

`business_completeness_driver` must cover:

- `business_loss_chain`: the status quo, pain holder, business pressure, and outcome at risk
- `continuation_economics`: who decides continue / revise / pause and what time, budget, workflow-change, or review commitment is at risk
- `substitute_pressure_map`: why current substitutes, local tools, service workarounds, or manual support are not enough
- `proof_for_continue`: what source-grounded proof artifact can support the next continuation decision and what external evidence is still missing
- `commercial_claim_ceiling`: the evidence confidence state and forbidden upgrades
- `downstream_business_contract`: what P2/P3/P4 must preserve and must not invent

Runtime responsibilities:

- Workflow builds and threads the driver before stage, arena, thesis, PRD, depth artifacts, scoring, and reports consume it.
- Agentic owns the driver judgment. It must preserve source-native roles, objects, substitutes, pressure, and proof language instead of leading with generic product-world labels.
- TVG may deepen only named driver targets and must stop when another round no longer creates material value.
- Evidence/gates may report driver absence, fake confidence upgrade risk, and claim ceilings; they must not generate product truth or raise confidence.
- `partially-signal-backed` is allowed only when source/stage material contains concrete proof/evidence/validation/review/decision signals. It remains below external validation and must keep missing external evidence visible.

Hard boundaries:

- do not branch by named case
- do not edit generated outputs by hand to make the driver look present
- do not convert review-bound source facts into validated market truth, real owner approval, budget confirmation, production readiness, or go-live authority
- if PRD prose becomes cleaner but loses the driver’s source-native product / commercial judgment, treat that as regression

### 1.1.2 P1 Semantic Authoring Spine

When P1 receives a `P1 source input packet`, the runtime must build a `P1 Semantic Authoring Spine` after source admission and before Stage / PRD authoring.

This spine is a semantic placement layer, not a gate and not a case-specific enrichment table.

Control boundary:

- Workflow preserves source order, stage order, artifact contracts, and evidence retention.
- Agentic owns `semantic placement`: deciding whether a source fact belongs to workflow activity, state lifecycle, object/data record, role/decision owner, audit/compliance, dashboard/review/decision surface, metric/success signal, open truth gap, or deferred scope.
- Evidence preserves source excerpt, source section, truth state, placement target, and claim ceiling.

Runtime rules:

- the `P1 Source Brief` is the product fact surface
- process sections such as `Challenge Axis Coverage`, reviewer notes, and office-hours route evidence may inform claim ceilings but must not become confirmed product facts
- state lifecycle facts should feed state model / transition guard thinking
- audit / compliance facts should feed NFR, acceptance, risk, and evidence surfaces
- dashboard / review / decision surface facts should feed IA, review, and decision surfaces
- open gaps must remain review-bound unless new source evidence closes them

Hard boundary:

- must not flatten every source fact into workflow modules
- must not turn state, audit, role, dashboard, review, decision, or metric semantics into generic CRUD module names
- must not use packet-process evidence as a shortcut for missing source truth

### 1.1.3 Existing-System Change Source Input

P1 may receive a `P1 source input packet` whose `packet_subtype` is `existing-system-change`.

This subtype is a light compatibility contract for changes to an existing system. It is not a PhaseX-specific mode and must not create a parallel P1 route.

P1 owns only the demand and product-truth part of this input:

- what the current system appears to do
- what the user wants to change
- which observed business facts are source-backed
- which business meanings are inferred and still need review
- which legacy behaviors must be preserved
- which conflicts, unknowns, non-goals, and acceptance pressure must remain visible

Runtime rules:

- `Current State Summary` is background and source truth, not automatically future design.
- `Target Change Summary` is the main demand-convergence target.
- `Observed Business Facts` may enter the PRD fact base.
- `Inferred Business Semantics` must keep inference labels until confirmed.
- `Legacy Behaviors To Preserve` should become requirement constraints, acceptance boundaries, or review-bound preservation items.
- `Source Conflicts` must stay visible; P1 must not silently choose one source as truth.
- Missing target change must route back to intake or remain blocked; P1 must not invent the change request.
- Technical, database, interface, performance, and architecture facts are P2 clues or requirement pressures only.

P1 must run a light `Demand Change Evaluation` after source admission and before normal demand convergence.

This evaluation is a product-demand judgment, not a technical design step. It must capture:

- `change intent`: what the user wants to add, change, replace, improve, or narrow.
- `business impact`: what value, loss, risk, operating pressure, or acceptance pressure makes the change matter.
- `affected users / workflows`: which roles, users, workflows, reports, decisions, or service moments are affected.
- `non-goals`: what should stay outside this change even if it appears in the current system.
- `Proceed Decision`: `proceed-to-P1`, `return-to-intake`, or `review-bound-provisional`.

Use `return-to-intake` when P1 would need to invent the target change, affected user/workflow, or business impact. Use `review-bound-provisional` when the user accepts visible uncertainty and P1 can preserve it. Use `proceed-to-P1` when the demand is clear enough for product convergence. P1 must not judge architecture, database, code, or implementation plan.

Hard boundary:

- P1 must not consume raw PhaseX scan tables as product truth.
- P1 must not understand PhaseX internal skill names or scan structure.
- P1 must not judge code quality, database quality, architecture quality, or performance bottlenecks.
- P1 must not create P3 ActionCards from this input.

## 1.2 Business Exploration Arena And Chosen Thesis

Before bounded deepening begins, `Phase-1` must build a `Business Exploration Arena`, not just pick a named business class, standalone topology profile, or proof-track field set.

The arena must compare competing business theses, current-state substitutes, reusable substitute pressure classes, buyer/user/operator value, continuation or closure proof, and real-world density before any final PRD assembly.

After arena exploration, `Phase-1` drafts a `Commercial Argument Draft` before selecting a `Chosen Business Thesis`. The argument narrative is the primary reader-facing judgment; thesis fields, `Business Proof Track`, `business/release truth`, and compatibility `topology profile` are derived or trace views of that argument and arena, not the primary thinking engine.

The chosen thesis must be a business argument, not a category label. It must explain why the product deserves investment or operational commitment now, why plausible substitutes are insufficient, what evidence can support continue / revise / pause or closure confidence, and what architecture pressure Phase-2 must preserve. A field-complete but commercially weak thesis should trigger Agentic rewrite; scripts may record quality risk but must not manufacture the final judgment.

The PRD opening should be argument-first: start with compact natural-language business reasoning from the commercial argument draft, then expose structured bullets and traceable runtime fields.

### P1 Business Value Signal Registry

For v1.2.3 Action Card Depth Coefficient (`ACD`), the converged PRD must expose a `business_value_signal_registry` before Phase-2 consumes the PRD.

Required columns are:

- `value_signal_id`
- `upstream_trace_id`
- `business_value_weight`
- `business_value_reason`
- `anti_demo_risk`
- `core_success_path`
- `downstream_depth_hint`
- `evidence_or_review_bound`

Rules:

- `value_signal_id` must be stable, e.g. `BVS-001`, so P2 can join without semantic guessing.
- `upstream_trace_id` must bind to `P1-UC-*`, `P1-REQ-*`, or `P1-AC-*` unless the row is explicitly review-bound.
- `business_value_weight` uses only `BV0 | BV1 | BV2 | BV3`.
- `BV3` is reserved for critical continuation, irreversible, official-evidence, audit, closure, or core buyer/operator proof paths.
- `BV2` is for high-value core paths that materially affect adoption, continuation, or execution credibility.
- Missing evidence must remain `review-bound`; it must not be silently downgraded to `BV0`.
- P1 provides business value and anti-demo pressure only; P2 owns architecture/component mapping, and P3 must not invent missing P1 value signals.

`topology profile` is retained as routing metadata, but it is no longer the primary P1 depth module.

The track should contain:

- `proof_track`
- `dominant_proof_risk`
- `proof_questions`
- `substitute_pressure`
- `proof_artifact`
- `continuation_decision`

First-wave proof tracks:

- `economic-decision-proof`
  - default risk:
    - the product looks structured but still does not prove why someone should buy, continue, or prefer it over substitutes
- `operational-service-proof`
  - default risk:
    - the product looks fake when the operating world is too thin
- `mixed-proof`
  - default risk:
    - both execution realism and decision leverage materially shape product credibility, but one dominant proof risk must still be named

Compatibility routing metadata may still include:

The route hint should contain:

- `topology_archetype`
- `primary_depth_axes`
- `secondary_depth_axes`
- `misfit_risk_if_wrong`
- `ordinary_real_world_baseline_definition`

First-wave archetypes:

- `execution-centric`
  - default risk:
    - the product looks fake when the operating world is too thin
- `decision-centric`
  - default risk:
    - the product looks fake when the decision / economic proof loop is too thin
- `hybrid`
  - default risk:
    - both execution realism and decision leverage materially shape product credibility

First-wave depth axes:

- `operational-chain`
- `exception-state`
- `role-coordination`
- `substitute-positioning`
- `proof-evidence`
- `buyer-budget-continuation`

These axes are not a closed taxonomy.
They are the first reusable axis set.
If a case needs another axis, add it explicitly and justify it in the profile rather than forcing the case into the wrong existing bucket.

Hard rules:

- do not classify by case name
- do not treat `ordinary real-world baseline` as one universal concept across all topology profiles
- do not treat the first-wave archetypes or the first-wave axes as a closed routing taxonomy
- `Business Proof Track` owns the actual P1 depth route
- `archetype` should only steer the route; it must not replace proof questions
- if primary axes are decision-side, step-density by itself does not prove business depth
- if primary axes are execution-side, a sharper buyer/budget story does not compensate for a thin operating world
- if the chosen proof track materially changes what counts as sufficient depth, the run must record the track before freeze

## 1.3 Generic Skill Discipline

These rules are generic `Phase-1` runtime rules.

They are not permission to:

- tune named scenarios
- hide case-specific branches in released skills
- patch retained artifacts directly and call that a runtime fix

If one case exposes a weakness, first repair the reusable `runtime / assembly / scoring / prompt-contract` chain that caused it.

---

## 2. Stage Runtime Posture

`Phase-1` should no longer be treated as “one-pass enrich then freeze”.

Default runtime posture:

1. structured draft
2. bounded deepening
3. anti-demo review
4. real-world baseline calibration when the domain is operationally rich
5. integration and convergence
6. freeze / return-remediate / blocked

Short rule:

> `Phase-1` should be loop-heavy before freeze-heavy.

Ordered runtime meaning:

- the outer pass sequence is fixed so the run does not drift
- but each pass is only a container for thinking work, not a permission slip to emit generic completion language
- a pass is not complete merely because its template section exists; it is complete only when the targeted business truth for that pass has materially thickened

Business-depth order inside `Phase-1` should normally follow:

1. `Business Proof Track routing`
   - choose:
     - one `proof_track`
     - one `dominant_proof_risk`
     - concrete `proof_questions`
     - compatibility `topology_archetype` / `depth_axes` only as route hints
   - use this track to choose what kind of proof the next passes must establish
2. `business-world sufficiency`
   - deepen along the chosen primary axes first
   - typical execution-side axes:
     - `operational-chain`
     - `exception-state`
     - `role-coordination`
   - typical decision-side axes:
     - `substitute-positioning`
     - `proof-evidence`
     - `buyer-budget-continuation`
3. `value mechanism clarity`
   - then make clear why this thicker world creates real business value rather than a polished workflow shell
4. `buyer / budget / continuation chain`
   - only after the first two layers are credible, make explicit who feels the pain, who decides continued commitment, what is at risk, what proof artifact matters, and what triggers continue / revise / pause
5. `integration and convergence`
   - only then decide whether the current run is strong enough to freeze, remain review-bound, or return-remediate

Hard order dependency:

- `buyer/budget chain` must not be treated as the main tool for making a thin world look commercially stronger
- if `business-world sufficiency` is still weak, loop back to scenario / state / constraint / role / baseline deepening before trying to converge commercial judgment
- if `value mechanism clarity` is still weak, do not treat a sharper buyer/budget story as sufficient convergence
- do not prune high-potential value options too early with cost, budget, or implementation-effort language; surface and compare value first, then apply trimming during convergence

Truth-generation order:

1. grow the world
   - make the selected primary axes denser first:
   - execution-side examples:
     - scenarios
     - operating steps
     - states
     - exceptions
     - coordination
     - constraints
   - decision-side examples:
     - substitute options
     - decision loop
     - evidence artifacts
     - continuation logic
     - commercial thresholds
2. calibrate the ordinary real operating baseline against the topology profile
   - confirm whether the chosen `archetype + depth axes` still fits
   - this calibration exists to choose the right product-world frame and depth pressure, not to produce a generic industry paragraph
3. choose the product world
   - decide what kind of product the case actually is before compressing anything:
   - e.g. a `decision-ready service operations system`, `visibility intelligence + guided optimization`, or another source-grounded product world
4. sharpen the judgment
   - clarify `why-now`, `why-this-not-that`, value mechanism, and real decision leverage
5. compress into protected truth
   - only after the first four layers are credible, summarize them into `business/release truth` first
   - then derive `planning/control truth` as a separate downstream pack
   - `business_world_model` may remain as a compatibility/index layer, but it is not the only primary truth surface
6. render into the PRD
   - only then let the assembler distribute `business/release truth` into strategic/product sections
   - planning/control truth should feed handoff/control sections and later `P2` intake without re-defining category/value framing

Hard rule:

- do not start from `truth-spine field filling` and hope later passes will magically add insight
- do not let `buyer/budget chain` become the first place where business value appears
- do not let `planning/control truth` become the source of `category framing`, `value mechanism`, or `why-this-not-that`
- `core thesis`, `why now`, and `value mechanism` must not be generated by paraphrasing `entry -> exit`, `flow summary`, or scenario chain text
- if the rendered truth reads like a contract dump instead of a business judgment, the pass has not converged

---

## 3. Required Passes

### `baseline` mode

A valid official run must complete these passes in order:

1. `R0 structured draft`
   - current stage artifact exists in structured form
2. `R0a topology-profile pass`
   - record:
     - `topology_archetype`
     - `primary_depth_axes`
     - `secondary_depth_axes`
     - `misfit_risk_if_wrong`
   - if the profile is still too uncertain to trust, keep it review-bound and continue looping rather than pretending it is settled
3. `R1 scenario-set / world-thickness pass`
   - check whether the chosen world is too thin or too demo-like
   - this pass should deepen the business world itself rather than merely restate the source in cleaner prose
4. `R2 scenario-depth / anti-demo pass`
   - deepen key flows, states, exceptions, constraints, and why-this-not-that
4a. `R2b value-mechanism pass` when business value is materially uncertain
   - make explicit why the now-thickened world changes business outcomes or user outcomes in a way that matters
4b. `R2c buyer / budget / continuation pass` when commercial continuation matters
   - materialize `pain holder -> continuation owner -> spend at risk -> proof artifact -> continuation signal`
   - do not run this as a substitute for `R1` or `R2`
5. `R3 integration pass`
   - integrate the strongest improvements and decide freeze / return / blocked

Pass-completion rule:

- `R0a` is about choosing the right depth profile before deepening
- `R1` is about making the world thicker
- `R2` is about making the world more executable and less demo-like
- `R2b` is about making the value mechanism explicit
- `R2c` is about making the continuation logic explicit
- none of these passes should be considered complete only because a corresponding section header or checklist row now exists

### additional required pass for operationally rich domains

If the domain is operationally rich, add:

- `real-world baseline calibration pass`

Typical examples:

- healthcare / pet healthcare
- retail / restaurant
- logistics / warehouse
- finance / compliance
- manufacturing / inspection

### `creative` mode

After `baseline` is sufficient, `creative` mode may continue with:

- bounded additional rounds focused on new `positive business value gain`

But it must still preserve:

- baseline truth
- creative discoveries as a separate layer

---

## 4. No-Early-Exit Rule

`wff-req` must not freeze early just because:

- the structure looks complete
- the writing feels polished
- one or two rounds already happened

Do not freeze if any of these remain true:

- the chosen world is still visibly below ordinary real-world baseline
- the core scenario set is still too thin
- core scenarios are still title-level
- the topology profile is still implicit even though it changes what depth should mean
- selected primary axes are still unsatisfied in the current artifact
- a profile weighted toward `substitute-positioning`, `proof-evidence`, or `buyer-budget-continuation` still lacks substitute logic, proof artifacts, directional evidence, or continue / pause threshold clarity
- a profile weighted toward `operational-chain`, `exception-state`, or `role-coordination` still lacks operating density, exception handling, state transitions, or role-handoff realism
- `P2` would still need to invent critical product truth
- high-density domains still lack baseline calibration
- meaningful alternatives were not compared
- anti-demo review still exposes major invention pressure

## 4.1 Structural Anti-pattern Blockers

`Phase-1` must also refuse freeze when protected business truth is present but structurally degraded.

Treat the following as blocker-grade anti-patterns when they dominate:

- `explicit-but-thin truth`
  - sections or fields exist, but the business judgment is not sharper than before
- `flow-summary substitution`
  - `core thesis`, `why now`, or `value mechanism` merely restates `entry -> exit` flow or scenario chain text
- `chain literalization`
  - long workflow chains are repeated where business interpretation should appear
- `proof-artifact repetition`
  - the same proof artifact is rendered repeatedly across thesis, pricing, buyer-budget, and validation surfaces
- `contract noun spillover`
  - traceability nouns, object names, or contract fields crowd out business reasoning in strategic sections
- `generic growth seam leakage`
  - non-growth domains inherit `ROI`, `recommendation`, `attribution`, or similar growth-language seams without real source pressure

Protected surfaces include:

- `core thesis`
- `why now`
- `alternatives / why-this-not-that`
- `value mechanism`
- `pricing validation`
- `buyer / budget / continuation chain`

Resolution rule:

- if one of these anti-patterns is localized, `return-remediate`
- if they dominate multiple protected surfaces and the run cannot deepen inside the same pass, `blocked`

---

## 5. Exit Rule

`baseline` mode may freeze only when all of the following are true:

1. downstream handoff sufficiency exists
2. the chosen world is not materially below ordinary real-world baseline
3. top core scenarios are no longer title-level
4. key trade-offs are visible
5. high-risk unknowns are explicit
6. another round is unlikely to create new `positive business value gain` under the canonical repo definition
7. protected business truth is sharper after structuring, not merely more explicit
8. structured truth surfaces do not degrade into chain repetition, proof-artifact repetition, or contract dump behavior

`creative` mode may freeze only when:

- baseline is already sufficient
- creative discoveries are separated from baseline truth
- another round is unlikely to create more `positive business value gain` than complexity

Allowed terminal states:

- `freeze`
- `freeze-with-review-bound-warning`
- `return-remediate`
- `blocked`

---

## 6. Required Runtime Outputs

The protocol should leave explicit evidence of the deepening process.

First-wave required output posture:

- stage artifacts remain the primary output surface
- PRD remains the primary convergence deliverable
- execution report must record the selected depth mode

When the case materially uses deeper Phase-1 looping, the runtime should also preserve or externalize:

- scenario-depth judgment
- anti-demo findings
- real-world baseline calibration notes when applicable
- decision-options and trade-off notes
- unresolved truth / evidence ledger

In first-wave `v1.2`, these may remain embedded in stage outputs, PRD, and evidence memo rather than always becoming standalone files.

When business value is a major part of the case, the evidence should make visible whether the latest loop materially improved at least one of:

- value mechanism clarity
- buyer / budget judgment
- continue / revise / pause decision leverage
- category / packaging / pricing decision quality
- or, secondarily, user-task-path clarity / process-friction reduction that materially improves real user outcomes

---

## 7. Skill Embedding Rule For `wff-req`

`skills/wff-req/SKILL.md` should enforce:

- explicit `depth-mode` selection
- baseline default
- creative only on explicit user request
- explicit `workflow_certainty / context_certainty` posture
- explicit `fixed_workflow_scope` vs `agentic_scope`
- explicit `context_completion_policy` and external-calibration rule
- no-early-exit rule
- baseline-first freeze rule

The runtime entrypoint should therefore carry visible mode metadata, even before deeper internal enforcement is fully refactored.

That metadata is now part of the first-wave `v1.2` implementation.

---

## 8. First-Wave Implementation Scope

This protocol is intentionally phased.

Current first-wave goal:

- freeze the runtime rule
- bind it into `wff-req`
- make the main runner carry explicit mode metadata

Still pending in later waves:

- deeper enforcement inside stage generation
- stronger standalone deepening artifacts
- tighter coupling between scorecard and runtime evidence

---

## One-Line Rule

> `wff-req` should no longer behave like “generate everything, then gate it”; it should behave like “select depth mode, deepen the right artifact units, then freeze honestly.” 
