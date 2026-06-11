# Phase-3 Implementation Delivery Reference Package

## 1. What this is

This directory is the Phase-3 method/reference package for implementation delivery.

It closes the structural gap between Phase-3 and the rest of WFF:

```text
skills/wff-impl* -> reference-packages/phase3-implementation-delivery/* -> scripts/phase3/*
```

The package is not a runtime rewrite. The executable implementation flow remains in `scripts/phase3/`.
The public Agent entry surfaces remain in `skills/wff-impl*`.

## 2. Package map

| Capability | Responsibility | Runtime entry |
|---|---|---|
| `wff-impl-action-cards` | Convert P2 handoff into auditable implementation ActionCards. | `scripts/phase3/run_impl_action_cards.py` |
| `wff-impl-db-schema` | Generate database schema artifacts from P2 data/storage contracts. | `scripts/phase3/run_impl_db_schema.py` |
| `wff-impl-api-docs` | Generate and check API documentation / OpenAPI handoff surfaces. | `scripts/phase3/run_impl_api_docs.py` |
| `wff-impl-backend` | Generate backend API/service/repository implementation. | `scripts/phase3/run_impl_backend.py` |
| `wff-impl-frontend` | Generate optional frontend surface when the P2/P3 input contains UI intent. | `scripts/phase3/run_impl_frontend.py` |
| `wff-impl-verification` | Generate and run verification pack surfaces. | `scripts/phase3/run_impl_verification.py` |
| `wff-impl-review` | Review implementation structure, naming, and delivery consistency. | `scripts/phase3/phase3_delivery_gate.py --mode code-review` |
| `wff-impl-security` | Review security posture and risk evidence. | `scripts/phase3/phase3_delivery_gate.py --mode security-audit` |
| `wff-impl-handoff` | Package delivery handoff and final implementation closure evidence. | `scripts/phase3/phase3_delivery_gate.py --mode delivery-handoff` |

Aggregate entry:

- `skills/wff-impl/`
- `scripts/phase3/run_impl.py`

Compatibility entry:

- `scripts/phase3/run_phase3_first_version.py`

## 3. Control boundary

Workflow owns:

- capability order;
- required inputs and outputs;
- script invocation;
- evidence capture;
- delivery gate state.

Agentic reasoning owns:

- implementation judgment inside the accepted P2 topology;
- bounded debugging and repair choices;
- code/test body authorship where scripts intentionally leave judgment room;
- review reasoning and handoff explanation.

Evidence/gates own:

- test/runtime proof;
- traceability closure;
- code review, security, coverage, and handoff reports;
- claim ceilings.

This package must not move product truth from P1 or architecture truth from P2 into P3.
If P3 cannot implement without inventing upstream truth, route back to the owning phase.

## 4. Claim ceiling

Phase-3 evidence is development / pre-production implementation evidence.
It does not claim production approval, go-live authorization, owner sign-off, production rollback readiness, or production risk acceptance.

## 5. One-line summary

This package gives P3 the same visible method layer as P1/P2/P4/PX while keeping the proven P3 runtime scripts unchanged.
