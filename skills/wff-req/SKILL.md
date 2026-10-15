---
name: wff-req
description: Use when running a real product case through Phase-1 to produce an official PRD, evidence memo, gates, and handoff package.
---

# Phase-1 Product Requirements Orchestrator

## Overview

This is the official Phase-1 entry skill. It turns source material into a reviewed product requirements package, not a manually filled template.

Phase-1 owns product truth, business pressure, scope boundaries, acceptance intent, and the handoff contract for design.

## Default Output Language

Follow `config/generated-output-policy.json` and `WFF_OUTPUT_LOCALE`.

For human-reviewed Phase-1 outputs, default to Simplified Chinese (`zh-CN`). Preserve code, paths, commands, API/schema fields, trace ids, artifact ids, env vars, and protocol keywords in their canonical form.

Generation governance: `docs/governance/bounded-generation-run-governance-v1.md` (中文：`docs/governance/bounded-generation-run-governance-v1.zh-CN.md`). It bounds section generation and review without weakening factual runtime evidence.

## Installed Resource Resolution

If a required companion resource appears missing, inspect `.wff/wff-project.json` first. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. Resource roots may also live under user-global `~/.wff/<install-pack>/`.

## When To Use

Use when:
- the user wants to turn source material into a PRD or requirements handoff
- downstream design, architecture, implementation, or validation will depend on the output
- the case enters through a `P1 source input packet` from `wff-req-chat`, PhaseX, or a human reviewer

Do not use when:
- the task is only editing one existing PRD section
- the user needs architecture, implementation, or validation instead
- the input is not ready and should return to intake

## Core Rules

1. Preserve source authority. Never overwrite an explicit source-defined product choice with a generic workflow, template preference, or world-knowledge assumption. When the source is materially thin, the P1 Agent may add non-conflicting ordinary-world knowledge as explicit `agentic-world-knowledge` backfill and decide whether to accept, review-bind, defer, or reject it.
2. Keep source-established facts, accepted world-knowledge backfill, candidates/hypotheses, owner-confirmed truth, unknowns, review-bound gaps, non-goals, and assumptions visibly separate.
3. Build top-down structure: epic, use case, requirement, acceptance criteria, and handoff trace.
4. Acceptance criteria must be actionable and should use Given / When / Then where it improves implementation clarity.
5. Existing-system change packets supply current-state context and demand pressure; they do not give P1 authority to decide architecture, database, code, or implementation plan.
6. Product outputs are evidence-capped. Missing owner sign-off, UAT, market validation, or production approval must remain explicit when absent.
7. Preserve **Interaction-relevant product context** when source evidence or accepted P1 Agentic judgment can establish it: user role/job, meaningful task and outcome, recurring/occasional or task-frequency posture, operator proficiency/context, user-visible business vocabulary, material friction/error consequences, and what the user expects the system to remember, carry forward, or default. Fresh P1 Agentic decisions publish this as `interaction_relevant_product_context`, with exact task-context identity, linked P1 commitments, truth/source/backfill provenance, unresolved items, and claim ceiling; the resulting accepted authority carries `interaction_semantics_contract=product-interaction-semantics-v1` into P2. P1 must not choose widgets, concrete controls/components, page composition, or interaction patterns merely to make P2/P3 deterministic. Unknown interaction-relevant product truth remains review-bound rather than being replaced by UI assumptions. See `docs/governance/v1.10-product-interaction-semantics-authority-boundary-v0.1.md`.

## Coverage and one-directional delivery / 覆盖与单向原则

P1 specifies the facts downstream must not invent silently and the decisions with high decision value. Cover as much as practical; content completeness and total coverage are not admission gates. Keep source truth, accepted decisions, and missing facts distinguishable.

Within a delivery cycle, P1 → P2 → P3 (→ P4) is one-directional. Accepted P1/P2 are frozen inputs. Downstream T0 implementation detail and T1 reasoned inference stay downstream; T2 new facts, explicit conflicts, and infeasible upstream facts follow the P3 gap-decision protocol in `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md`. Record next-version `backport_target`; do not rewrite or regenerate frozen inputs, including for WFF format upgrades. Only a human may end the cycle because its direction is fundamentally wrong.

## P1 → P2 projection interface — six minimum input categories

During P1 stage A, deterministically select these six categories by P1 ID from frozen artifacts, preserving each item's source ID and digest. Projection does not call a model, rewrite P1, or silently fill gaps. Repeating the same input must yield the same digest; report byte/token volume and queue P1 gaps for next-version backport.

| Category | Projected content |
|---|---|
| 1. Roles and responsibilities / 角色与职责 | Accepted roles, responsibilities, and provenance. |
| 2. Core tasks/journeys and successful outcomes / 核心任务或旅程及成功结果 | User tasks, relevant steps, and intended meaningful results. |
| 3. Business objects and key attributes / 业务对象及关键属性 | Canonical object identities and decision-relevant attributes. |
| 4. High-decision-value business rules / 有决策价值的业务规则 | Accepted constraints and rules that downstream must preserve. |
| 5. Language and terminology / 语言与术语 | Locale and accepted business vocabulary. |
| 6. Non-goals / 非目标 | Explicit exclusions and scope boundaries. |

A category may contain a declared gap. Frozen v1 inputs use compatible reading and explicit claim ceilings; they are not regenerated to resemble v2.

## Delegation and default policies / 委托与默认策略

The P1 delegation section is generated in M4, not retrofitted into frozen P1 during M1–M3. Before then, P3 consults existing decisions and the seven conservative-default rules; record observed rule use as input to the future delegation section.

Neutral templates define each row's rule ID, question category P3 may decide, applicability and source IDs/digests, default behavior, preserved boundaries, confirmation posture, and backport destination. Agentic fills policies from accepted product truth; templates carry neither business answers nor business defaults. The section delegates decisions without inventing product facts or requiring a standing reviewer/approval role. Architecture/interaction delegation comes from P2 Stage-05.

## Required Inputs

Read first:
- `docs/phases/phase-1/phase-1-session-bootstrap.md`
- `reference-packages/phase1-product-requirements/README.md`
- `docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- source material or `P1 source input packet`

When the input packet has `packet_subtype: existing-system-change`, also read:
- target change
- affected users/workflows
- legacy behaviors to preserve
- unknowns and source conflicts
- demand clarification addendum when present

When the input is a `P1 source input packet`, consume its `Admission Decision`,
`Open Truth Gaps`, and `Reviewer Concerns` before generation. P1 must preserve review-bound gaps and must not invent missing product truth. It may use ordinary-world knowledge to fill source-silent product-world gaps only through the explicit world-knowledge backfill decision; backfill must not masquerade as source truth or contradict an explicit source-defined product choice.

If the packet includes `Canonical Product Language Candidates`, P1 must treat terminology candidates as advisory labels for source-backed naming continuity. They may help avoid accidental relabeling, but they must not replace source materials, the P1 source brief, or the truth-state ledger. P1 must not promote review-bound terminology into confirmed product truth.

## Demand Change Evaluation

For `existing-system-change` packets, run a light Demand Change Evaluation
before normal PRD convergence:
- `Change Intent`: target change and non-goals.
- `Business Impact`: business pressure, value, risk, or urgency.
- `Affected Users / Workflows`: impacted user groups and workflow slices.
- `Proceed Decision`: `proceed-to-P1`, `return-to-intake`, or `review-bound-provisional`.

P1 evaluates demand clarity and business pressure only; it must not judge architecture, database, code, or implementation plan.

## P1 Agentic Product Authority

A formal fresh P1 run requires one current-snapshot host-Agent product/world decision.

Prepare the admitted source snapshot and non-authoritative candidate packet first:

```bash
python3 scripts/phase1/agentic_product_authority.py prepare \
  --source <phase1-input.md> \
  --candidate-output <candidate.json> \
  --decision-template-output <decision-template.json>
```

The candidate packet may extract source evidence and propose world/feature hints, but every interpretation remains `agentic-candidate`. It cannot claim confirmed domain truth, choose material scope, or create portable commitments.

The host Agent decision must explicitly decide context sufficiency, source-established world truth, optional world-knowledge backfill, the resulting product-world decision, material feature dispositions, portable commitments, product judgment, unresolved facts, and the bounded claim ceiling. Source-established, `agentic-world-knowledge`, Agentic candidate/hypothesis, owner-confirmed, and unresolved/review-bound truth must remain distinct. World-knowledge backfill is optional: a source-complete case may intentionally carry an empty backfill set.

`world_alignment` is the compatibility container for this transformation and must contain `source_established_world`, `world_knowledge_backfill`, `product_world_decision`, and the compact `accepted_world` summary. The product-world decision must state canonical `objects[]`, structured topology (`ordered-flow | independent-outcomes | mixed | review-bound`), and ownership posture (`source-defined | agentic-world-knowledge | mixed | review-bound`). Every accepted product-world object carries an exact object ID/name, commitment refs, source/backfill basis, and local claim ceiling; the canonical writer and P2 handoff must preserve those objects instead of substituting candidate feature IDs. When the Agent accepts a concrete role responsibility, `ownership.assignments[]` binds that role to exact accepted commitment IDs with source/backfill basis and a local claim ceiling; unassigned or review-bound responsibilities stay unresolved. Scripts and renderers must consume those structured values; they must not infer objects, topology, or ownership authority from keywords, role order, heading order, or generic workflow defaults.

Run the canonical writer only with an accepted decision bound to the exact current source snapshot. A missing, stale, incomplete, or unapplied decision stops at `agentic-decision-required`; lexical density, generic world structure, templates, and gates cannot substitute for it.

The accepted authority is `p1-agentic-product-authority.json` and current publication carries `world_knowledge_contract: p1-world-knowledge-backfill-v1`. The compiled claim surface is `.phase1-evidence/<prd-stem>.claim-surface.json`. PRD and Stage Markdown are lossless human-review projections. Claim-control and the P2 handoff must consume the accepted product-world decision, world-knowledge provenance, and portable commitments first; rendered prose and the historical generic claim spine cannot become parallel authority.

### P1 PRD Claim Authority Surface

The canonical compiled surface is `.phase1-evidence/<prd-stem>.claim-surface.json`; PRD Markdown is a rendered human-review view. A claim-control sidecar must prefer the compiled claim surface and may use a rendered PRD compatibility fallback only for historical inputs. That compatibility fallback must not become source authority.

The mechanical source parser produces candidate context only. Before Stage and PRD rendering, `build_decision_bound_direct_driver()` must replace its product judgment, business argument, semantic-authoring spine, scope, product-world topology/ownership posture, review-bound routing, and downstream assumptions with the accepted authority. Accepted world-knowledge backfill may enrich the canonical product world, but a conflicting or uncertain backfill cannot be promoted. The existing Stage/PRD renderer remains the only canonical writer; no second authority-specific PRD generator is allowed. After draft convergence, the lightweight canonical authority verifier must confirm exact commitment and backfill application, truth-state visibility, structured topology projection, review-bound preservation, and absence of unconfirmed ownership promotion. The final P1 Gate then runs without mechanical auto-rewrite, and `p1-agentic-product-application-receipt.json` retains the digest-bound `p1-canonical-authority-convergence.json` verification report. Merely appending an authority section or finding its IDs in the PRD is not application evidence.

## Bounded Doubt-Driven Challenge

Before an accepted P1 product/world decision stands, run one bounded challenge over `product-world-sufficiency` and `cross-phase-commitment`; include `candidate-world-semantics` whenever the accepted world remains an Agentic candidate/hypothesis **or** the decision accepts/review-binds material world-knowledge backfill. The owner writes the CLAIM but the reviewer sees only the exact candidate artifact, P1 authority contract, admitted source/context identities, explicit unknowns, and an issues-first instruction. The challenge must explicitly look for source-defined product choices being overwritten by backfill and for backfill being laundered into source/owner truth.

The P1 host Agent must reconcile each material finding. Source/context insufficiency returns to intake/context completion; actionable findings change the decision artifact and require a fresh pass over the changed unit; valid unresolved findings remain review-bound; non-applicable findings require a bounded rationale. Default depth is one pass and the maximum is three. The challenge record stays inside the accepted decision envelope and the authority carries only its digest-bound summary. Cross-model review is optional and per-invocation authorized.

Compatibility reading preserves frozen P1 authority carrying `decision_integrity_contract: bounded-challenge-integrity-v1` and historical pre-#888 v1 decisions marked `legacy-pre-bounded-challenge-v1`. Preserve the original snapshot and review bindings, expose absent evidence and the resulting claim ceiling, and allow downstream consumption without a new P1 decision or regeneration. This does not publish new P1 authority or fabricate stronger review proof.

## Phase Review And Value-Bearing Closure

Expose a Phase Review Breakpoint before promoting to Phase-2. Reviewers may approve (`批准`), require modification (`要求修改`), require return (`要求返回`), or provide intervention input (`提供干预输入`); the decision must preserve product-value and source-truth judgment, not only template completeness.

P1 closure is value-bearing only when product value, business pressure, user value, pain strength, narrowest valuable wedge, and source truth confidence are visible. P1 protected surfaces must remain visible to downstream phases; moving diagnostics is allowed only when the consumer path and resolver coverage stay explicit.

## Thinking Value-Gain Full-Use Generation Strategy

Use TVG across all major P1 artifact units as a value-preservation strategy, not as a length-expansion rule. Default to `coverage_rich` when the source is broad,
but keep Thinking Thickness and Value Density explicit: deepen only when it
improves grounded product judgment, source truth, acceptance pressure, or
handoff usefulness. Preserve `business_value_signal_registry` evidence and treat
over-design regression as a real failure mode.

## WFF Core Contract Binding

- Machine descriptor: `product-requirements`, phase `P1`, route `wff-req`, under `wff-core-contract` `1.0.0`.
- Consumes `phase-contract`, `handoff-contract`, `artifact-identity-contract`, `evidence-contract`, and `claim-state-contract`.
- Core owns admission/handoff structure and claim envelopes; Phase-1 Agentic work remains the owner of product and business truth.
- A missing or incompatible Core binding is a blocked entry, not permission to continue with a local default.

## Entrypoint

Run the official source-to-PRD path:

```bash
python3 scripts/phase1/run_phase1_source_to_prd.py \
  --source <phase1-input.md> \
  --agentic-product-decision <accepted-decision.json> \
  --output-dir <phase1-output-dir> \
  --version <version-label> \
  --profile <review-bound-starter-pack|implementation-ready-prd> \
  --depth-mode <baseline|creative>
```

Use `baseline` by default. Use `creative` only when the user explicitly asks for broader product exploration.

Use `scripts/phase1/run_phase1_convergence.py` for convergence/remediation over generated Phase-1 outputs.

## Execution Sequence

1. Confirm source readiness and admission state.
2. Generate the exact source snapshot and candidate packet; do not promote candidates.
3. Obtain one bounded host-Agent product/world and material-feature decision.
4. Validate decision freshness, owner, source evidence, truth states, dispositions, and portable commitment identities.
5. Apply the accepted decision through one canonical writer before Stage/PRD generation.
6. Generate and converge Stage/PRD projections without creating a parallel generic authority.
7. Rebuild claim-control, portable commitment authority, Trace, and the P2 handoff from the accepted decision.
8. Verify the application receipt, run gates, and present the review breakpoint and final claim ceiling.

## Required Output Set

A valid Phase-1 package preserves:
- stage outputs
- PRD
- evidence memo
- execution report
- gate JSON reports
- source/claim surface
- P1 Agentic candidate, accepted decision evidence, portable product authority, and application receipt
- Phase-2 design input contract
- fine-grained trace registry
- explicit review-bound and claim-ceiling statements

## Quality Floor

Phase-1 is complete only when:
- the product problem, target users, workflows, and success pressure are understandable
- requirements and acceptance criteria are specific enough for design
- review-bound gaps are not hidden as confident requirements
- existing-system facts stay labeled as current-state context unless confirmed as target behavior
- downstream Phase-2 can consume traceable demand truth without inventing scope

## Completion Standard

After Phase-1 owns a stable output, the built Release runtime queues the
localized Human Review sidecar and returns immediately. Repository authoring
defaults this sidecar off. Sidecar failure or absence must not alter the
Phase-1 result, Trace, or Phase-2 admission.

Stop with one of these states:
- `ready-for-phase2`: product truth is sufficient for architecture
- `ready-with-review-bound-items`: Phase-2 may proceed only with named ceilings
- `return-to-intake`: demand is too unclear for honest PRD generation
- `agentic-decision-required`: the current source snapshot lacks an accepted product/world decision
- `blocked`: required source, decision, or application evidence is invalid

Do not call Phase-1 complete when the PRD is only polished prose without traceable source authority and acceptance pressure.
