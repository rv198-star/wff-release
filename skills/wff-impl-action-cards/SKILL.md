---
name: wff-impl-action-cards
description: Use when generating Phase-3 implementation action cards from Phase-2 component/action-card obligation matrices before backend or frontend code is written.
---

# Phase-3 Implementation Action Cards

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns the action-card capability inside P3.
It turns Phase-2 component obligations into implementation action cards, a pointer-only execution map, and a human audit packet.

Use it when:
- P2 has produced `implementation-component-catalog.json` and `component-action-card-obligation-matrix.json`
- you need implementation cards before backend/frontend work starts
- you want to review ACD depth, missing sources, and split-required components without running all of P3

Do not use it to invent missing P1/P2 truth. Missing bridge artifacts or incomplete obligation rows must stay `review-bound`. When accepted P2 architecture authority exists, source-material sufficiency is not semantic completeness: every defined implementation component must retain its full accepted contract/P1-trace denominator plus applicable aggregate/writer/topology, component NOR/state/failure/dependency context, project guardrails, and claim ceilings. When accepted **Product Interaction Semantics** exist, Action Cards must preserve the exact semantic identity/digest while assigning only component-owned obligations: consumer-facing Service cards own discoverability, multi-value preservation, existing-data reuse, no opaque-reference/storage-syntax entry, context carryover, free-form/bounded-choice, usage-friction, error-cost and related interaction obligations; Repository cards keep the semantic trace as persistence context and own only persistence-relevant cardinality/validation/sensitivity constraints. Resolve linked P1 task-frequency/low-step context instead of leaving `inherit P1` as an implementation instruction. Material interaction obligations must produce explicit verification obligations. An Action Card must not choose a widget, control type, React component, or other concrete P3 presentation merely to make implementation deterministic. Global project guardrails and upstream dependencies are context only and must not be converted into false component prerequisites.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-action-cards/` for the capability contract, SOP, output template, and source cards.

## Runner

Primary command:

```bash
python3 scripts/phase3/run_impl_action_cards.py \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output>
```

Primary outputs:
- `action-cards/*.md`
- `action-cards/validation.json`
- `.phase3-review/action-card-execution-map.json`
- `.phase3-review/action-card-human-audit-packet.json`
- `.phase3-review/action-card-semantic-convergence.json`
- `action-card-report.json`

## Completion Standard

This skill is complete only when the report names the generated cards, validation status, execution-map path, human-audit packet path, and semantic-convergence result. For an authority-bound P2 handoff, `action-card-semantic-convergence.json` must pass with zero unresolved conflicts; defined component omission, accepted contract/P1-trace shrink, aggregate/writer/topology loss, NOR/state/failure/dependency loss, missing semantic claim ceilings, or loss/change/invention of frozen Product Interaction Semantics blocks the next P3 step. When Product Interaction Semantics exist, each applicable card must retain the exact semantic identity/digest, declare whether the semantic row is `consumer-interaction-owner` or `persistence-context-only`, render only component-owned implementation obligations, resolve linked P1 frequency/low-step context where available, and emit verification obligations for material interaction constraints while leaving presentation authority explicitly unselected for P3 Agentic. The human card should be high-signal: keep complete trace/digest identity but do not repeat the same source list or generic obligation text merely for field-by-field verbosity. P3 may recompute this projection in memory from the accepted P2 authority when an older retained bridge matrix predates the projection capability; it must not rewrite the frozen P2 evidence to make the bridge appear current. Non-operation components may have no public operation contract and must preserve their accepted aggregate/writer/NOR/state authority instead of being mislabeled as unresolved operations.

Passing Action Card generation still does not mean implementation quality is accepted; it means the P1/P2 semantic handoff is preserved and the cards are ready for human review and a separate P3 implementation-authority decision.
