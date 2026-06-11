# wff-impl-api-docs Skill Contract

## Responsibility

Generate API documentation and API consistency evidence from accepted P2/P3 contract surfaces.

## Inputs

- P2 interface contracts.
- Generated backend route/controller surfaces.
- OpenAPI or API contract material.
- ActionCards for operation behavior.

## Outputs

- API documentation.
- OpenAPI consistency evidence.
- API handoff notes and review-bound gaps.

## Boundaries

- Do not redesign APIs after P2 freeze.
- Do not treat documentation presence as runtime proof.
- Do not hide route/contract mismatches.

## Runtime

Use `scripts/phase3/run_impl_api_docs.py`.
