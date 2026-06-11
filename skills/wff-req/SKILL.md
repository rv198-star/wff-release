---
name: wff-req
description: Use when running a real product case through Phase-1 and you need the official end-to-end output set via deep stage generation, PRD assembly/convergence, executable gates, and execution report.
---

# Phase-1 Product Requirements Orchestrator

## Overview

This is the **official execution skill** for a real Phase-1 case in this repo.

It does not replace the Phase-1 Stage packs.
It orchestrates them into one bounded, gate-driven runtime so the final output is not reduced to manual template filling.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write headings, narrative sections, analysis, summaries, checklists, conclusions, operator guidance, and audit-facing copy in Chinese
- preserve code, file paths, commands, API/schema field names, trace ids, artifact ids, env vars, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only Stage artifacts, PRD sections, convergence notes, evidence memos, or execution reports unless the user explicitly requests English

## When to Use

Use when:
- the user wants to run a real source document through Phase-1
- the output is intended for product review, design, architecture, or handoff
- you need the full official artifact set, not just one stage note

Do not use when:
- you are only authoring or revising one Stage pack
- you are doing source coverage/audit work for a Stage skill
- you only need to inspect one failing Stage artifact in isolation

## Core Rule

For official Phase-1 delivery, do **not** hand-fill Stage templates stage by stage and call that the result.

Official delivery must go through:
- deep Stage artifact generation
- PRD assembly
- PRD convergence
- executable gates
- execution report

Runtime surface split:
- official runtime entry = `scripts/phase1/run_phase1_full_trial.py`
- convergence/remediation engine = `scripts/phase1/run_phase1_convergence.py`

Top-down decomposition must stay explicit through the run:
- `Epic -> User Story / Use Case -> Requirement -> Acceptance Criteria`
- do not jump straight from PRD prose to isolated stories and then backfill the hierarchy later
- implementation-ready PRDs must express acceptance criteria in `Given / When / Then` form with visible boundary-condition coverage
- implementation-ready PRDs must include an `INVEST` quality pass for the primary story and supporting use cases
- the final converged PRD must preserve `Epic Decomposition`, `Story Quality Gate (INVEST)`, and structured `Acceptance Criteria` as explicit machine-readable sections rather than collapsing them into prose
- the final converged PRD must also preserve explicit `Competitive Landscape Summary` and `Pricing Validation Design` sections, even when those areas remain review-bound

## Required Entry Assets

Read these first:
- `docs/phases/phase-1/phase-1-session-bootstrap.md`
- `reference-packages/phase1-product-requirements/README.md`
- `docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- `docs/phases/phase-1/phase-1-execution-report-template-v0.1.md`
- `docs/phases/phase-1/phase-1-depth-mode-runtime-protocol-v0.1.md`

## Pre-P1 Packet Consumption

When the user enters through `wff-req-chat`, prefer a `P1 source input packet` over a bare source note.

Read these packet sections before official Phase-1 execution:

- `P1 Source Brief`
- `Product Truth Challenge Notes`
- `Truth-State Ledger`
- `Open Truth Gaps`
- `Reviewer Concerns`
- `Admission Decision`
- `Handoff Note For wff-req`

Consumption rules:

- `ready-for-P1`: run normally while preserving source authority, truth-state labels, and claim ceilings.
- `provisional-ready-for-P1`: run only if the user accepts the review-bound status; P1 must preserve review-bound gaps and must not invent missing product truth.
- `not-admission-ready`: do not treat the packet as normal Phase-1 source input. Return to intake or ask the user to explicitly accept a provisional note with visible gaps.

`wff-req` may deepen product and business judgment from the source, but it must preserve review-bound gaps, must preserve Reviewer Concerns when they affect downstream decisions, and must not invent missing product truth to make the PRD look complete.

Pre-P1 admission is not Phase-1 completion. The packet is an input contract and evidence bridge, not a PRD, UPP, owner sign-off, market validation proof, or production authorization.

### P1 Semantic Authoring Spine

When the input is a `P1 source input packet`, official P1 authoring must build and consume a `P1 Semantic Authoring Spine` before Stage / PRD rendering.

Purpose:

- preserve the `P1 Source Brief` as the fact surface for product authoring
- keep packet process sections such as `Challenge Axis Coverage` out of product fact generation
- let Agentic judgment perform `semantic placement` before workflow renders the artifacts
- retain evidence through source excerpts, truth-state labels, placement targets, and claim ceilings

The spine must distinguish at least:

- `state lifecycle`
- `audit / compliance`
- `dashboard / review / decision surface`
- role / actor / decision-owner semantics
- domain object / data-record semantics
- success metric / validation signal semantics
- open truth gaps and deferred / out-of-scope items

Hard boundary:

- must not flatten every source fact into workflow modules
- must not turn state, audit, role, dashboard, review, decision, or metric semantics into generic CRUD pages
- must not use process evidence from office-hours or challenge notes as confirmed product truth

## Required Entrypoint

Use:

```bash
python3 scripts/phase1/run_phase1_full_trial.py \
  --source <phase1-input.md> \
  --output-dir <trial-output-dir> \
  --version <trial-vN> \
  --profile <review-bound-starter-pack|implementation-ready-prd> \
  --depth-mode <baseline|creative>
```

`baseline` is the default.
Use `creative` only when the user explicitly asks for stronger creative exploration beyond baseline sufficiency.

### Thinking Value-Gain Full-Use Generation Strategy

For v1.2.3 exploratory runs, Phase-1 generation should apply `Thinking Value-Gain` across all major P1 artifact units, not only as a late review pass.

Use it as a bounded value-strengthening method, not as a length-expansion rule:

- define the value exit gate before each stage artifact is deepened
- strengthen practical value for decision, action, evidence, review, reuse, or downstream handoff
- prefer business-useful judgment over additional template structure
- stop when another round would not create meaningful positive value
- mark weak or unresolved value as review-bound instead of filling it with generic business language

P1 full-use targets include:

- `Business Exploration Arena`: improve real-world baseline, substitute pressure, buyer/user/operator value, and continuation proof
- `Commercial Argument Draft`: improve why-now, why-this-not-substitutes, investment/continuation logic, and proof artifact clarity
- `Chosen Business Thesis`: improve decision usefulness and downstream architecture pressure without becoming a category label
- `business_value_signal_registry`: improve P1-to-P2 value trace clarity and anti-demo pressure, not architecture ownership
- final PRD / evidence memo / execution report: improve reader decision value and handoff honesty without bloating narrative

This strategy is intentionally experimental and easy to roll back. If a full-use run becomes longer but not more decision-useful, treat that as over-design regression and revert to targeted TVG use.

Default expectation:
- source document stays read-only
- output directory is fresh and case-specific
- stage outputs, PRD, evidence memo, execution report, and gate JSON are all preserved
- auto-remediation remains enabled unless there is a debugging reason to disable it

## Official Working Root

Use the case-first local artifact layout:

- `tmp/local-artifacts/<case-name>/phase-1/`
- `tmp/local-artifacts/<case-name>/phase-2/`

Keep generated case outputs there rather than under ad hoc `/tmp` paths when the run is meant to become the canonical local baseline.

## Companion Assets

Use together with:
- `docs/phases/phase-1/phase-1-session-bootstrap.md`
- `reference-packages/phase1-product-requirements/README.md`
- `docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- `scripts/phase1/phase1_generate_deep_stage_outputs.py`
- `scripts/phase1/run_phase1_convergence.py`
- `scripts/phase1/phase1_prd_excellence_regression.py`

The Stage packs remain authoritative for:
- contract logic
- stage SOP
- output surface
- method-asset selection
- top-down decomposition depth, including epic grouping, story quality, and acceptance-boundary detail

But they are consumed through the full-trial runtime, not used as a manual final-delivery worksheet.

## v1.2 Runtime Protocol

`wff-req` now follows the first-wave `v1.2` runtime protocol:

1. select explicit `depth-mode`
   - `baseline` by default
   - `creative` only on explicit user request
2. build a `Business Exploration Arena` before deepening
   - explore the real business world, competing business thesis candidates, current-state substitutes, buyer/user/operator value, continuation chain, and real-world density before PRD assembly
   - identify substitute pressure by reusable substitute class, not by case name: read-only substitutes, human-service substitutes, fragmented-tool substitutes, system-of-record substitutes, and workflow-fragment substitutes
3. select a `Chosen Business Thesis`
   - choose by reusable business pressure, not by case name
   - first draft a `Commercial Argument Draft` from source-grounded evidence and arena context
   - the commercial argument narrative is the reader-facing judgment; structured thesis fields are trace support derived from it
   - write it as a business argument, not a label: why the user/buyer/operator needs it now, why substitutes are insufficient, what proof supports continued investment, what directional proof matters without exact ROI, and what value mechanism is created
   - record why-this-not-alternatives, current-state substitute to beat, substitute pressure types, proof target, review-bound truth, product boundary implication, and thesis quality risk signals
   - if the thesis is structurally complete but commercially weak, route to Agentic rewrite instead of freezing
4. derive `Business Proof Track` from the chosen thesis
   - topology is only a routing hint, not the main P1 depth module
   - choose one `proof_track`:
     - `economic-decision-proof`
     - `operational-service-proof`
     - `mixed-proof`
   - record `dominant_proof_risk`, `proof_questions`, `substitute_pressure`, `proof_artifact`, and `continuation_decision`
   - keep compatibility routing fields where useful:
     - `topology_archetype`:
     - `execution-centric`
     - `decision-centric`
     - `hybrid`
     - `primary_depth_axes` and optional `secondary_depth_axes`
   - route by business shape, not by remembered case name
3. generate structured stage artifacts
4. apply bounded deepening instead of one-pass freeze
5. run anti-demo review and Business-Proof-Track-matched real-world baseline calibration
6. converge into PRD + evidence + execution report
   - optional narrative compression may be applied only through an agent/operator-authored `prd-narrative-compression-rewrite.json`
   - workflow may validate and apply explicit replacements to allowed reader-facing narrative sections, but must not infer, deduplicate, or delete business evidence on its own
   - use this lane only when the main PRD is business-correct but narratively repetitive; if compression makes the output thinner, treat it as regression
7. freeze only when baseline sufficiency is actually established

Inside that runtime, preserve this truth order:
- `ordinary real operating baseline`
- `p1-product-source-direct-driver.v1`
- `product world selection`
- `business/release truth`
- `planning/control truth`

Release-facing implication:
- build `p1-product-source-direct-driver.v1` before Stage / PRD authoring; it is an in-memory Agentic judgment surface, not a new heavy default report
- the driver must answer source-truth admission, product judgment, commercial judgment, business feasibility, narrowest valuable MVP wedge, acceptance meaning, open truth-gap routing, forbidden downstream assumptions, and value-deepening targets
- the driver must also expose a compact `business_completeness_driver` when source signals allow it; this is the P1 commercial completeness judgment surface, not a score-gaming surface
- `business_completeness_driver` should preserve the business loss chain, continuation economics, substitute pressure, proof-for-continue, commercial claim ceiling, and downstream business contract
- `partially-signal-backed` may be used only when source/stage signals include concrete proof, evidence, validation, review, or decision signals; it still forbids claims of externally validated market truth, willingness-to-pay, owner sign-off, budget approval, or production readiness
- strategic/product sections must start from the driver-backed product and commercial judgment when present; topology/profile labels are supporting metadata, not the lead product argument
- `Thinking Value-Gain` may deepen driver-selected targets, but only with a named value exit; it must not become a generic instruction to add more detail
- strategic/product sections must prefer `business/release truth`
- control/handoff sections may consume `planning/control truth`
- `P2` intake must read these as separate packs rather than deriving category/value framing from control surfaces
- scoring and gates may expose missing driver-backed judgment, fake confidence upgrade risk, and claim ceilings; they must not manufacture product truth or raise source confidence
- if the source is review-bound, do not claim validated market truth, real owner approval, budget confirmation, production readiness, or go-live authority


### P1 Business Value Signals For Implementation Depth

P1 must not decide Service/Domain/Repository architecture, but it must identify which business truth cannot become thin downstream.

For v1.2.3 Action Card Depth Coefficient (`ACD`), P1 must emit a structured `business_value_signal_registry` for core scenarios, business rules, acceptance criteria, and anti-demo paths. Required fields:

- `value_signal_id`: stable join key such as `BVS-001`
- `upstream_trace_id`: `P1-UC-*`, `P1-REQ-*`, or `P1-AC-*` unless explicitly review-bound
- `business_value_weight`: `BV0 | BV1 | BV2 | BV3`
- `business_value_reason`
- `anti_demo_risk`: `low | medium | high | critical`
- `core_success_path`: `yes | no`
- `downstream_depth_hint`: `none | standard | deep | critical`
- `evidence_or_review_bound`

Depth semantics:

- `BV3`: critical continuation, irreversible, official evidence, audit, closure, or core buyer/operator proof path
- `BV2`: high-value core path materially affecting adoption, continuation, or execution credibility
- `BV1`: ordinary meaningful business behavior
- `BV0`: support/reference behavior only

Missing business evidence remains review-bound. Do not default missing value to `BV0`. These signals are inputs to P2 implementation-depth synthesis. P3 must not invent or downgrade them locally.


Hard boundaries:

- `creative` never bypasses `baseline`
- do not freeze early just because structure looks complete
- if the next phase would still need to invent critical truth, the run is not ready
- if `creative` is active, baseline truth and creative discoveries must stay separated

## Workflow / Context Boundary

Treat `wff-req` as:

> `workflow-fixed outer shell + agentic business deepening`

- workflow certainty is high for stage order, required passes, artifact contracts, gates, and preserved output set
- context certainty is often low at the business-world layer until clarification, evidence capture, and deepening finish
- scripts keep the run ordered; they must not overwrite domain language or manufacture business truth
- agentic scope covers scenario selection, business-value sharpening, secondary user-task/flow-experience sharpening, `why-this-not-that`, anti-demo review, real-world baseline calibration, and targeted context completion
- when the ordinary real operating baseline materially changes the right product category, the runtime must first build a `Business Proof Track` before compressing truth
- first-wave profile routing:
  - `proof_track` owns P1 depth routing:
    - `economic-decision-proof | operational-service-proof | mixed-proof`
  - `topology_archetype` is compatibility metadata and coarse routing only:
    - `execution-centric | decision-centric | hybrid`
  - actual deepening pressure comes from reusable `depth axes`
  - first-wave axes:
    - `operational-chain`
    - `exception-state`
    - `role-coordination`
    - `substitute-positioning`
    - `proof-evidence`
    - `buyer-budget-continuation`
  - the axis list is extensible; do not force every case into the current set if the fit is poor
- these are generic runtime rules; do not solve quality gaps by tuning named scenarios or by editing case outputs directly
- for `high workflow certainty + low context certainty` commercial-decision cases, keep the mainline loop fixed but leave scenario content, commercial semantics, buyer/budget truth, and decision logic to agentic deepening rather than script pre-baking
- generic marker language about business value, budget, pricing, or continue / revise / pause does not count as resolved business truth by itself; the runtime must preserve case-specific business nouns, causal chain, and decision stakes from the source world
- when buyer/budget truth matters, the runtime should explicitly materialize a reusable chain of `pain holder -> continuation owner -> spend at risk -> proof artifact -> continuation signal` rather than collapsing it into one generic commercial sentence
- if the active primary axes are decision-side, do not let “mainline clarity” or step-density stand in for economic decision-loop depth
- if the active primary axes are execution-side, do not let a sharper buyer/budget story stand in for thin operating-world truth
- do not let `planning/control truth` become the source of `category framing`, `value mechanism`, or `why-this-not-that`
- if a compiled `P1` artifact becomes cleaner but more abstract than the source brief on recommendation payloads, competitor context, buyer/budget chain, or continuation logic, treat that as regression even if gate scores remain green
- in commercial-decision domains, do not let generic `Scenario A / B / C` shells replace domain-specific scenario semantics that should remain explicit for downstream design and architecture
- outer order may be procedural, but the work inside each pass must not become procedural slot-filling
- do not let `core thesis`, `why now`, or `value mechanism` collapse into `entry -> exit` flow summary paraphrase
- do not use early cost / budget trimming as a substitute for surfacing and comparing higher-value business options first
- if outputs become cleaner but thinner, treat that as regression and continue looping or return-remediate
- P1 PRD opening should be argument-first: begin with the `Commercial Argument Draft` narrative, then expose structured bullets; keep runtime ledger field names out of the reader-facing lead when they would make the document feel like a field dump
- freeze only when another round is unlikely to create new material positive business value under the repo definition, including business value creation and decision leverage rather than description density alone

## v1.3.1 Phase Review Breakpoint

At official Phase-1 completion, present a review opportunity before treating the PRD / evidence / execution-report package as ready for Phase-2.

The breakpoint must surface the Phase-1 output root, primary artifacts, product / business / user / acceptance value judgment, source-truth confidence, open `review-bound` items, evidence basis, claim ceiling, recommended next step, and minimum rerun / return boundary.

Show human-facing review actions in Chinese: `批准`, `带保留项批准`, `要求修改`, `要求返回`, `提供干预输入`, or `明确跳过审核`. Structured records may also preserve stable protocol keys such as `approved` or `return-requested`. New source truth must be recorded as new input and rerun or remediated through Phase-1; do not silently patch final artifacts or treat the breakpoint as continuous human-led collaboration.

## v1.3.1 Value-Bearing Closure

Phase-1 closure must be a product-value and source-truth judgment, not PRD format completion.

Before promoting the Phase-1 package to Phase-2, state whether product value, business value, user/stakeholder value, pain strength, narrowest valuable wedge, acceptance meaning, source truth confidence, and open truth gaps are strong enough for architecture to consume. If P2 would still need to invent product goal, business value, user value, acceptance meaning, or status quo pressure, return or keep the package review-bound instead of treating convergence or script pass as closure.

If the P1 score is high but no Agentic deepening target is selected, do not imply value gain by default. The closeout must either mark `stable-no-material-gain`, select a bounded high-value deepening target, or explain why another deepening round would not create meaningful product / business value.

## v1.3.4 Cross-Phase Pattern Extension

When the active release line is `v1.3.4`, P1 may use the proven Agentic quality and slimming patterns only inside the Phase-1 artifact boundary.

P1 protected surfaces must remain visible:

- source truth;
- assumptions;
- open truth gaps;
- product decisions;
- admission evidence;
- PRD main document and Phase-2 design input contract;
- convergence evidence, phase verdict, scorecard, and claim ceiling.

If Review finds a large P1 artifact defect after a phase checkpoint, convert it into a bounded P1 artifact rewrite packet with:

- defect statement and evidence;
- affected P1 artifact units;
- protected source-truth surfaces that must not change;
- rewrite scope and stop condition;
- local evidence gate before closure refresh.

This is not `v1.3.5` source-truth admission hardening. New source truth must still enter as new input and rerun/remediate through Phase-1; do not silently patch final artifacts, do not invent missing source truth, and do not hide open truth gaps to make the package look cleaner.

For slimming, use consumer-aware profile directories only for diagnostic/review mirrors and intermediate evidence after resolver support exists. Do not move source truth, open truth gaps, PRD authority, convergence evidence, zh-CN human-review mirrors, or P2 intake surfaces out of normal visibility. The assembled PRD draft may live under `.phase1-evidence/` when the converged PRD main document, zh-CN audit mirror, and convergence evidence memo remain root-visible.

## v1.3.1 Runtime References

Use these release-facing references when applying the v1.3.1 Phase-1 control model:

- `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
- `docs/governance/v1.3-product-flow-control-boundary-v0.1.zh-CN.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.zh-CN.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.zh-CN.md`
- `docs/phases/phase-1/p1-value-bearing-artifact-closure-v0.1.md`
- `docs/phases/phase-1/p1-value-bearing-artifact-closure-v0.1.zh-CN.md`

## Release Validation Rule

When validating the released skill itself, use an isolated workspace/session that loads the release bundle without repo-level `AGENTS.md` assistance.
Otherwise dev-context rules may hide missing runtime instructions.
For the official retained `GEO + PetClinic` isolation flow, prefer `scripts/release/run_release_dual_case_eval.py` from the built release pack/bundle instead of running directly inside the authoring repo.

## Required Output Set

A valid run should preserve:
- Stage-01 output
- Stage-02a output
- Stage-02b output
- Stage-03 output
- Stage-04 output
- `real-world-baseline-calibration.md`
- `domain-baseline-scenario-map.md`
- `core-scenario-depth-matrix.md`
- `demo-risk-review.md`
- `decision-options-and-tradeoffs.md`
- `domain-assumption-and-evidence-ledger.md`
- `phase1-depth-runtime-summary.json`
- assembled PRD draft, root-visible or under `.phase1-evidence/` as intermediate convergence evidence
- converged PRD main document
- Phase-2 design input contract embedded in the PRD fine-grained trace section
- zh-CN PRD audit mirror
- convergence evidence memo
- execution report
- convergence gate result
- explicit depth-mode metadata in the run record

## Manual Mode Boundary

Manual Stage-by-Stage use is allowed only for:
- authoring
- audit
- debugging
- targeted remediation before rerunning the full trial

It is not valid as the official Phase-1 delivery path.

## Rerun Rule

When rerunning an existing case, also apply:
- `skills/wff-meta-stage-skill-construction-lifecycle/SKILL.md`
- baseline lock / regression gate / vs-baseline delta reporting

## Quick Reference

| Need | Do This |
|---|---|
| Run a real case end-to-end | `scripts/phase1/run_phase1_full_trial.py` |
| Recheck/fix an existing PRD candidate | `scripts/phase1/run_phase1_convergence.py` |
| Inspect why depth/regression is weak | read gate outputs + `phase1_prd_excellence_regression.py` |
| Fix one weak Stage | open that Stage pack, patch the weak artifact, rerun full trial |
