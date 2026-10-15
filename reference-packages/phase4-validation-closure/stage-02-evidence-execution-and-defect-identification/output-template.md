# Stage-02 Output Template — evidence-execution-and-defect-identification

## 1. Document Metadata
- document_name:
- stage:
  - `evidence-execution-and-defect-identification`
- version:
- status:
  - `draft | provisional | review | approved`

## 1.1 Traceability Naming and Registry
- artifact_id:
- artifact_type:
  - `TEST | OUTPUT | EVIDENCE | DEFECT`
- depends_on:
- feeds:
- source_path:
- source_anchor:

## 2. Context and Objective
- execution_target:
- stage_objective:
- upstream_stage01_summary:
- assumptions:
- open_questions:

## 3. Core Structured Output
- execution_evidence_package:
  - upstream_stage01_reference:
  - execution_scope_completion_summary:
  - in_scope_scenarios_executed:
  - scenarios_not_executed_or_blocked:
- execution_result_summary:
  - pass_items:
  - fail_items:
  - blocked_items:
- evidence_summary:
  - execution_log_reference:
  - evidence_pointer_list:
  - operator_run_reference_if_used:
  - current_ui_product_review_request_reference_if_required:
  - current_ui_product_review_manifest_reference_if_supplied:
  - ui_product_review_findings_reference_if_any:
- defect_and_risk_log:
  - defect_record_reference:
  - unresolved_risks:
  - blocked_or_review_bound_items:
- stage03_handoff_summary:
  - closure_relevant_signals:
  - items_stage03_must_review_explicitly:

## 4. Acceptance and Flow
- minimum_acceptance:
  - execution scope completion summary exists
  - evidence summary exists
  - when current requested-frontend P3 browser evidence exists, subjective `ui-review` is current-bound to an independent Agentic UI/Product Review or remains explicit `review-bound` / `fail`; screenshot existence alone is not product-quality approval
  - defect / blocked / risk log exists
  - Stage-03 handoff summary exists
- handoff_to:
  - `validation-closure-and-delivery-readiness-judgment`
- handoff_decision:
  - `pass | pass-with-review-bound-items | return`
