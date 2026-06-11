# wff-impl-handoff Skill Contract

## Responsibility

Package Phase-3 delivery handoff and implementation closure evidence.

## Inputs

- Generated implementation package.
- ActionCards and execution map.
- Verification, review, security, and delivery gate reports.
- Runtime smoke evidence when strict runtime is claimed.

## Outputs

- implementation handoff package.
- delivery gate state.
- downstream reliance boundaries and review-bound carryover.

## Boundaries

- Do not approve production release.
- Do not replace P4 validation closure.
- Do not hide missing external owner or UAT evidence.

## Runtime

Use `scripts/phase3/phase3_delivery_gate.py` with supplied handoff/runtime evidence in slim profiles; optional handoff report generation support is full-pack/source-tree only.
