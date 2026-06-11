# wff-impl-backend Skill Contract

## Responsibility

Generate backend API/service/repository implementation inside the accepted P2 topology.

## Inputs

- ActionCards.
- P2 architecture and operation contracts.
- Database schema package when available.
- Project implementation conventions.

## Outputs

- backend modules, routes/controllers, services, repositories, and runtime support.
- backend verification evidence.
- implementation review-bound items.

## Boundaries

- Do not reopen product scope or architecture boundaries.
- Do not silently bypass ActionCard obligations.
- Do not claim delivery readiness without verification and delivery gate evidence.

## Runtime

Use `scripts/phase3/run_impl_backend.py`.
