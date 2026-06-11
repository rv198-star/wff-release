# Test Coverage Explanation Template

## Purpose

This template is the canonical Stage-01 (`acceptance-coverage-planning`) coverage rationale artifact for Phase-4.

It explains why the selected acceptance and validation scope is sufficient, prioritized, and reviewable.

It is not a numeric coverage report.
It is the explicit reasoning layer that connects risk, claims, and acceptance scope.

---

## 1. Document Metadata

- document_name:
- stage:
  - `acceptance-coverage-planning`
- version:
- status:
  - `draft | review | approved`

## 1.1 Traceability Naming and Registry

- artifact_id:
  - `TEST-STG01-COVERAGE-0001`
- artifact_type:
  - `RATIONALE | COVERAGE | TEST`
- depends_on:
  - `IMPL-STG03-HANDOFF-0001`
  - `TEST-STG01-ACCEPT-0001`
- feeds:
  - `TEST-STG02-OUTPUT-0001`
  - `TEST-STG03-OUTPUT-0001`
- source_path:
- source_anchor:

---

## 2. Coverage objective

- coverage_objective_summary:
- decision_basis:
  - `risk-based | claim-based | mixed`
- primary_business_or_delivery_risks:
- validation_focus_areas:

---

## 3. Scope coverage table

| scope_area | why_in_scope | related_req_ids | related_api_ids | planned_test_ids | priority | coverage_depth | notes |
|---|---|---|---|---|---|---|---|
|  |  | REQ-0001 | API-0001 | TEST-0001 | `high | medium | low` | `smoke | focused | deep` |  |

### Field guidance

- `scope_area` should describe a business or validation area, not just a screen or endpoint name.
- `why_in_scope` should tie the scope to risk, claim, or acceptance consequence.
- `planned_test_ids` should match the acceptance checklist rows.
- `coverage_depth` should remain qualitative unless a stricter local policy exists.

---

## 4. Explicit exclusions and trade-offs

- excluded_scope_areas:
- why_excluded:
- deferred_follow_up_areas:
- trade_off_notes:

---

## 5. Gate implications

- entry_gate_implications:
- exit_gate_implications:
- critical_fail_conditions:
- review_bound_conditions:

---

## 6. Downstream usage rule

- Stage-02 should execute against this rationale, not silently widen or narrow scope.
- Stage-03 should judge closure against this rationale, not against retrospective guesswork.
- Any major scope change should be recorded as a Stage-01 review or revision, not hidden in execution notes.
