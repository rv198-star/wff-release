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
- When accepted Product Interaction Semantics exist, preserve their exact semantic identity/digest but assign only component-owned implementation responsibility. Consumer-facing Service cards use responsibility `consumer-interaction-owner` and own discovery/context/free-form/bounded-choice/multi-value/error-cost interaction work; Repository cards use `persistence-context-only`, keep the same semantic rows as trace-only persistence context, and own only persistence-relevant cardinality/validation/sensitivity constraints. Resolve linked P1 task-frequency/low-step context when available and turn material interaction constraints into explicit verification obligations. These are semantic constraints, not concrete UI controls. If a retained P2 bridge matrix predates this projection, recompute the interaction slice from accepted P2 authority in P3 memory rather than rewriting frozen P2 evidence.
- Do not freeze `widget_type`, `control_type`, React components, interaction patterns, or equivalent P3 presentation choices in Action Cards unless presentation itself is explicitly source-authoritative.
- Do not implement backend/frontend code in this capability.
- Do not treat ActionCards as human approval or production authorization.

## Runtime

Use `scripts/phase3/run_impl_action_cards.py`.
