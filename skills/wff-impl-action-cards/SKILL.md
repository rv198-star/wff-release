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

Do not use it to invent missing P1/P2 truth. Missing bridge artifacts or incomplete obligation rows must stay `review-bound`.

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
- `action-card-report.json`

## Completion Standard

This skill is complete when the report names the generated cards, validation status, execution-map path, and human-audit packet path.
Passing generation does not mean implementation quality is accepted; it only means the action-card intake surface is ready for review and downstream implementation.
