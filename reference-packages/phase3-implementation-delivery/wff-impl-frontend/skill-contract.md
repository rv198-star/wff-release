# wff-impl-frontend Skill Contract

## Responsibility

Generate optional frontend surfaces when P1/P2/P3 inputs contain enough UI intent.

## Inputs

- P1 interaction/prototype intent when present.
- P2 UI or interaction handoff.
- API contracts and backend surface.
- ActionCards touching user-facing behavior.

## Outputs

- frontend implementation surface.
- UI route/component notes.
- frontend verification or review-bound evidence.

## Boundaries

- Do not invent a rich frontend when upstream only claimed backend delivery.
- Do not treat generated UI as product design approval.
- Do not hide missing visual/manual evidence.

## Runtime

Use `scripts/phase3/run_impl_frontend.py`.
