# wff-impl-verification Skill Contract

## Responsibility

Generate and run verification surfaces for the Phase-3 implementation package.

## Inputs

- ActionCards and verification obligations.
- Backend/frontend/schema outputs.
- Test trace matrix.
- Runtime configuration.

## Outputs

- unit, schema, SQL, contract, scenario, and replay tests where applicable.
- verification reports and ledgers.
- runtime smoke evidence when requested by strict mode.

## Boundaries

- Do not treat skipped tests as proof.
- Do not replace P4 validation closure.
- Do not claim production readiness from development runtime evidence.
- Positive insert fixture isolation must preserve accepted FK/context identity; if a conflicting unique group contains only identifier fields, remove only the conflicting validation-only write-table row instead of inventing a new identifier.
- With Product Interaction Semantics, supplemental invalid-request fixtures may mutate only explicit user-input fields semantically bound to the documented error; do not corrupt workflow/auth/context fields to manufacture a negative test.

## Runtime

Use `scripts/phase3/run_impl_verification.py`.
