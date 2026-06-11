# Acceptance Checklist Template

## Purpose

This template is the canonical Stage-01 (`acceptance-coverage-planning`) acceptance checklist / catalog artifact for Phase-4.

It freezes acceptance claims in a reviewable, executable shape that preserves:

- `TEST-* -> API-* -> REQ-*` traceability
- expected vs actual outcome capture
- pass/fail/blocked status semantics

It is not a generic QA checklist.
It is the Phase-4 acceptance-facing control artifact that Stage-02 uses for execution and Stage-03 uses for closure review.

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
  - `TEST-STG01-ACCEPT-0001`
- artifact_type:
  - `CHECKLIST | ACCEPTANCE | TEST`
- depends_on:
  - `IMPL-STG03-HANDOFF-0001`
  - `CONTRACT-REGISTRY-0001`
- feeds:
  - `TEST-STG02-OUTPUT-0001`
  - `TEST-STG03-OUTPUT-0001`
- source_path:
- source_anchor:

---

## 2. Checklist scope

- acceptance_scope_summary:
- target_environment_summary:
- out_of_scope_items:
- review_bound_items:

---

## 3. Acceptance item table

| test_id | acceptance_type | acceptance_item | related_api_ids | related_req_ids | related_surface_or_ui_refs | scenario_prompt | expected_result | actual_result | expected_evidence | status | evidence_path | owner / executor | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TEST-0001 | `functional | ui-review | visual-evidence` |  | API-0001 | REQ-0001 |  |  |  |  | `vitest-json | screenshot | manual-review-note` | `pass | fail | review-bound | blocked | not-run` |  |  |  |

### Field guidance

- `test_id` should remain stable and unique within the checklist.
- `acceptance_type` should distinguish mandatory functional checks from UI/design review and explicit visual-evidence capture.
- `acceptance_item` should describe the business-facing validation claim, not an internal implementation task.
- `related_api_ids` may be empty only when no contract boundary is relevant.
- `related_req_ids` should remain explicit whenever a requirement exists.
- `related_surface_or_ui_refs` should name the route / screen / visual surface when the item is UI-facing.
- `scenario_prompt` should be executable but not over-scripted.
- `expected_result` should be concrete and reviewable.
- `actual_result` may remain blank during Stage-01 and should be filled during Stage-02.
- `expected_evidence` should make screenshot/video/manual review expectations explicit instead of implied.
- `evidence_path` may remain blank during Stage-01 and should be filled during Stage-02.

---

## 4. Entry / exit gate linkage

- entry_gate_reference:
- exit_gate_reference:
- pass_fail_rule_summary:
- blocked_state_rule:

---

## 5. Execution notes for Stage-02

- execution_environment_notes:
- evidence_capture_expectations:
  - functional items use executable evidence first
  - `ui-review` items may rely on manual walkthrough notes
  - `visual-evidence` items should point to screenshot / video / equivalent manual record when available
- defect_capture_linkage:
- retest_or_follow_up_rule:

---

## 6. Review / waiver model

- waiver_allowed:
  - `yes | no`
- waiver_recording_rule:
- mandatory_review_for_waivers:
- must_fix_before_stage03_conditions:
  - any non-pass `functional` item
