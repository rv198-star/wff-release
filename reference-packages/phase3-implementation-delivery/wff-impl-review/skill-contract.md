# wff-impl-review Skill Contract

## Responsibility

Review implementation structure, naming, consistency, and delivery readiness signals.

## Inputs

- Generated implementation package.
- ActionCards and source mappings.
- Code review checklists.
- Verification and delivery gate evidence.

## Outputs

- code review report.
- routed findings.
- review-bound carryover.

## Boundaries

- Do not rewrite implementation directly inside the review capability.
- Do not replace human review when required.
- Do not promote clean structure to production approval.

## Runtime

Use `scripts/phase3/phase3_delivery_gate.py --mode code-review`.
