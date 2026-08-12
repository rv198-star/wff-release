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

Do not use it to invent missing P1/P2 truth. Missing bridge artifacts or incomplete obligation rows must stay `review-bound`. When accepted P2 architecture authority exists, source-material sufficiency is not semantic completeness: every defined implementation component must retain its full accepted contract/P1-trace denominator plus applicable aggregate/writer/topology, component NOR/state/failure/dependency context, project guardrails, and claim ceilings. Global project guardrails and upstream dependencies are context only and must not be converted into false component prerequisites.

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

This skill is complete only when the report names the generated cards, validation status, execution-map path, human-audit packet path, and semantic-convergence result. For an authority-bound P2 handoff, `action-card-semantic-convergence.json` must pass with zero unresolved conflicts; defined component omission, accepted contract/P1-trace shrink, aggregate/writer/topology loss, NOR/state/failure/dependency loss, or missing semantic claim ceilings block the next P3 step. Non-operation components may have no public operation contract and must preserve their accepted aggregate/writer/NOR/state authority instead of being mislabeled as unresolved operations.

Passing Action Card generation still does not mean implementation quality is accepted; it means the P1/P2 semantic handoff is preserved and the cards are ready for human review and a separate P3 implementation-authority decision.
