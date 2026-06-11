# wff-impl-action-cards Skill Contract

## Responsibility

Create the implementation ActionCard set from accepted Phase-2 handoff material.

## Inputs

- Phase-2 Engineering Spec Pack.
- Phase-3 implementation entry.
- P2 operation/source obligation matrices when available.
- Traceability registry or explicit review-bound reason when unavailable.

## Outputs

- `action-cards/*.md`
- `action-card-report.json`
- action-card audit material under `.phase3-review/`

## Boundaries

- Do not invent P1 product truth or P2 architecture truth.
- Do not implement backend/frontend code in this capability.
- Do not treat ActionCards as human approval or production authorization.

## Runtime

Use `scripts/phase3/run_impl_action_cards.py`.
