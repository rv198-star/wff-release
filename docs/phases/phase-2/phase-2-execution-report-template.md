# Phase-2 Execution Report Template (v0.3)

## 1. Runtime Metadata
- case_name:
- input_source_prd:
- run_owner:
- run_date:
- report_version:
- delivery_profile:
  - `review-bound-architecture-draft | implementation-planning-ready-design-package`
- case_complexity_profile:
  - `micro | standard | complex`
- deployment_posture_suggested:
  - `light | standard | heavy`
- deployment_posture_selected:
  - `light | standard | heavy`
- deployment_posture_selection_mode:
  - `default-light | trigger-backed | human-override-warning`
- deployment_posture_warning_class:
  - `none | constraint-backed-override | preference-driven-override`
- deployment_posture_override_source:
- deployment_posture_override_reason:
- deployment_posture_added_risks:
- current_overall_status:
  - `implementation-planning-ready | pass-with-review-bound-items | blocked`
- rerun_mode:
  - `initial | rerun`
- baseline_reference:
- engineering_spec_pack_reference:

## 1.1 Deployment / Infrastructure Posture Basis
- design_discipline_policy:
  - `high-spec design discipline stays fixed; deployment/infrastructure weight scales by need`
- deployment_posture_summary:

## 2. Stage Output Inventory
- stage_01_output:
- stage_02_output:
- stage_03_output:
- stage_04_output:
- phase_2_execution_report:
- engineering_spec_pack:
- phase_3_implementation_entry:
- first_pass_audit_report:
- architecture_traceability_report:
- trace_registry_validation_result:
- phase1_phase2_coverage_report:
- quality_check_report:
- mermaid_validation_report:
- cross_stage_consistency_report:

## 2.1 G.09 Event Direct-Driver Evidence

- event_direct_driver_status:
  - `present | present-with-review-bound-gaps | missing | not-applicable`
- event_vocabulary_refs:
- event_model_catalog_refs:
- p3_event_handoff_status:
  - `ready-for-P3-consumption | review-bound | blocked`
- review_bound_event_gaps:
  - (for each unresolved event model: owner, validation path, downstream usage rule)
- claim_ceiling:
  - (cap event-model claims to the weakest evidence above)

## 3. Deliverable Judgment Matrix

> **Mandatory**: this matrix must cover all `mandatory` deliverables and every `conditional` deliverable that is actually triggered by the active case shape.
> Do not force every case to fill the same fixed row count.

### 3.1 Mandatory Deliverables

| deliverable_name | verdict | evidence_reference | unresolved_truth | next_action |
|---|---|---|---|---|
| system boundary statement | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| constraint posture | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| quality attribute / NFR absorption | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| security architecture sketch | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| capacity estimation | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| capability map | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| architecture direction | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| key architecture decisions | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| domain map | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| module map | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| service candidates | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| responsibility matrix | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| dependency / collaboration map | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| decomposition decisions | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| conceptual entity relationship diagram | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| domain event catalog | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| data model summary | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| data ownership map | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| storage strategy | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| schema draft | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| interface contracts | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| API endpoint draft | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| interaction flow | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| security architecture outline | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| technology stack and deployment assumptions | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| technology selection evaluation matrix | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| dominant bottleneck hypothesis | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| architecture alternative candidate set | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| baseline insufficiency note | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| constraint-dominant optimum candidate | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| capacity and performance assumptions | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| scenario coverage matrix | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| key tradeoff decisions | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| architecture convergence summary | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| prototype or structured delivery expression | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| critical interaction sequence set | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| optimality review | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| design verification notes | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| unresolved risks and review-bound items | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| implementation handoff package | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |
| implementation task sketch | `pass | pass-with-review-bound | partial | fail | deferred` | | `none | review-bound | unknown | blocked` | |

### 3.2 Triggered Conditional Deliverables

| deliverable_name | verdict | trigger_reason | evidence_reference | unresolved_truth | next_action |
|---|---|---|---|---|---|

### 3.3 Not-Triggered Conditional Deliverables

| deliverable_name | trigger_status | trigger_reason |
|---|---|---|

## 3.4 Checklist Mapping Closure

> **Mandatory**: every triggered judgment-matrix row must map to exactly one checklist item from `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`.

- checklist_reference:
  - `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- mandatory_row_count:
- triggered_conditional_row_count:
- not_triggered_conditional_row_count:
- checklist_rows_expected_for_this_run:
- judgment_matrix_row_count_actual:
- mapping_status:
  - `complete | incomplete`

| checklist_id | stage | deliverable_name | matrix_verdict | evidence_reference |
|---|---|---|---|---|

## 4. Baseline Lock Scorecard

> **Mandatory**: all fields below must contain specific numeric values (not placeholders or "see source").
> For initial runs, record the values as the first baseline.
> For reruns, fill both baseline_value and current_value columns.

| dimension | baseline_value | current_value | delta | gate |
|---|---|---|---|---|
| stage_01_line_count | | | | |
| stage_02_line_count | | | | |
| stage_03_line_count | | | | |
| stage_04_line_count | | | | |
| architecture_decisions_count | | | | ≥7 |
| forbidden_assumptions_count | | | | = Phase-1 total |
| mermaid_C4Context_count | | | | ≥1 |
| mermaid_C4Container_count | | | | ≥1 |
| mermaid_stateDiagram_count | | | | ≥3 |
| mermaid_sequenceDiagram_count | | | | ≥3 |
| mermaid_erDiagram_count | | | | ≥1 |
| mermaid_gantt_count | | | | ≥1 |
| domain_count | | | | ≥4 |
| domain_event_count | | | | ≥10 |
| schema_table_count | | | | ≥10 |
| api_endpoint_count | | | | ≥10 |
| rbi_count | | | | ≥5 |
| scenario_count | | | | ≥8 |
| public_boundary_name_count | | | | all closed |
| work_package_count | | | | ≥4 |

## 5. Regression Gate Result

> **Mandatory for reruns**: compare EVERY dimension from the Baseline Lock Scorecard.
> Each dimension must have a per-dimension verdict. "Overall pass" without per-dimension evidence is not acceptable.

| dimension | baseline_value | rerun_value | delta | verdict | justification_if_negative |
|---|---|---|---|---|---|
| stage_01_line_count | | | | `pass | regressed | improved` | |
| stage_02_line_count | | | | `pass | regressed | improved` | |
| stage_03_line_count | | | | `pass | regressed | improved` | |
| stage_04_line_count | | | | `pass | regressed | improved` | |
| architecture_decisions_count | | | | `pass | regressed | improved` | |
| forbidden_assumptions_count | | | | `pass | regressed | improved` | |
| mermaid_C4Context_count | | | | `pass | regressed | improved` | |
| mermaid_stateDiagram_count | | | | `pass | regressed | improved` | |
| mermaid_sequenceDiagram_count | | | | `pass | regressed | improved` | |
| mermaid_erDiagram_count | | | | `pass | regressed | improved` | |
| mermaid_gantt_count | | | | `pass | regressed | improved` | |
| domain_count | | | | `pass | regressed | improved` | |
| domain_event_count | | | | `pass | regressed | improved` | |
| schema_table_count | | | | `pass | regressed | improved` | |
| api_endpoint_count | | | | `pass | regressed | improved` | |
| rbi_count | | | | `pass | regressed | improved` | |
| scenario_count | | | | `pass | regressed | improved` | |
| work_package_count | | | | `pass | regressed | improved` | |

- overall_regression_gate:
  - `pass | fail`
- regression_gate_reasoning:
  - (required: explain overall verdict referencing per-dimension results above)

## 6.1 vs-Baseline Mandatory Diff Table (Legacy Compatibility)

> This section is kept for backward compatibility. The primary regression data is in Section 5 above.
> For reruns, ensure Section 5 is fully populated.

## 7. Review-Bound Ratio Report

> **Mandatory**: all fields below must contain computed numeric values.
> `not-computed-by-wrapper` or `see source outputs` is NOT acceptable.

- total_structured_items:
  - (count: sum of all structured items across Stage-01..04 — decisions, constraints, FA items, NFR items, domains, modules, services, events, schema tables, API endpoints, scenarios, RBI items, WPs, etc.)
- review_bound_or_unknown_or_deferred_items:
  - (count: items marked `review-bound`, `unknown`, or `deferred` in any Stage output)
- ratio:
  - (computed: review_bound_items / total_structured_items × 100%)
- ceiling:
  - `30%`
- verdict:
  - `within-ceiling | over-uncertain | blocked`
- computation_method:
  - scan all Stage-01..04 markdown files for structured items (list entries under `## 3. Core Structured Output` sections) and count those with status markers containing `review-bound`, `unknown`, or `deferred`
- top_3_resolution_attempts_or_block_reasons:
  - (if ratio > 30%: list the top 3 review-bound items and for each: what was attempted to resolve it, or why resolution is blocked)

## 8. Traceability Runtime
- trace_registry_root:
- trace_db_path:
- allocation_mode:
  - `wff-base-traceability-management`
- canonical_artifacts_bound:
- zh_audit_mirrors_bound:
- coarse_link_chain_registered:
  - `yes | no`
- validation_result:
  - `pass | fail`
- runtime_contract_verdict:
  - `pass | fail`
- runtime_contract_issues:
  - (if fail: list missing or inconsistent runtime fields such as empty `trace_db_path` / `trace_registry_root`)
- validation_reference:
- registry_report_reference:

## 9. Stage Summaries

> **Mandatory**: each summary must reference SPECIFIC content from the Stage output.
> Generic placeholders like "see source stage output" or just the filename are NOT acceptable.
> `strongest_output` must cite a specific section or deliverable and explain WHY it is strong.
> `weakest_output` must cite a specific section or deliverable and explain WHAT is weak or missing.

### Stage-01 Summary
- outcome:
- strongest_output:
  - (cite specific section, e.g. "Section 3, forbidden assumptions registry — 7 items all mapped to architecture constraints with compliance evidence")
- weakest_output:
  - (cite specific gap, e.g. "capacity estimation lacks specific TPS numbers — only qualitative descriptions provided")
- dependency_realizability_scan_status:
- quality_gate_result:
  - (from quality check: pass / fail with specific gate failures listed)
- progression_judgment:

### Stage-02 Summary
- outcome:
- strongest_output:
  - (cite specific section with evidence)
- weakest_output:
  - (cite specific gap with evidence)
- brownfield_or_ownership_conflict_status:
- quality_gate_result:
- progression_judgment:

### Stage-03 Summary
- outcome:
- strongest_output:
  - (cite specific section with evidence)
- weakest_output:
  - (cite specific gap with evidence)
- substitute_boundary_and_dependency_realizability_status:
- quality_gate_result:
- progression_judgment:

### Stage-04 Summary
- outcome:
- strongest_output:
  - (cite specific section with evidence)
- weakest_output:
  - (cite specific gap with evidence)
- readiness_calibration_and_review_reentry_status:
- quality_gate_result:
- progression_judgment:

## 9.1 Cross-Stage Consistency Check Result

> **Mandatory**: verify naming, terminology, decision, and quantitative consistency across Stage-01..04.
> See SKILL.md "Cross-Stage Consistency Validation" for the full checklist.

| check_category | check_item | result | inconsistency_found | resolution_or_justification |
|---|---|---|---|---|
| terminology | Every Stage-02 domain appears in Stage-01 capability map | `pass | fail` | | |
| terminology | Every Stage-02 module referenced in Stage-03 data ownership | `pass | fail` | | |
| terminology | Every Stage-02 service has ≥1 API endpoint in Stage-03 | `pass | fail` | | |
| terminology | Every aggregate with lifecycle in Stage-02 has stateDiagram | `pass | fail` | | |
| decision | No contradictory decisions across Stages | `pass | fail` | | |
| decision | Stage-04 convergence references all Stage-01 decisions | `pass | fail` | | |
| naming | Stage-03 public boundary names match Stage-02 ER | `pass | fail` | | |
| naming | API endpoint names consistent with service candidate names | `pass | fail` | | |
| naming | Domain event names match Stage-02 event catalog | `pass | fail` | | |
| quantitative | Stage-01 capacity reflected in Stage-03 storage strategy | `pass | fail` | | |
| quantitative | Schema table count ≥ Stage-02 aggregate count | `pass | fail` | | |

- overall_consistency_verdict:
  - `consistent | minor-inconsistencies | major-inconsistencies`

## 9.2 Quality Self-Assessment

> **Mandatory**: score the overall output on at least 6 dimensions.

| dimension | score (0-10) | evidence | gap_to_9.5 |
|---|---|---|---|
| architecture_decision_depth | | | |
| domain_decomposition_clarity | | | |
| specification_completeness | | | |
| visual_representation_quality | | | |
| process_governance_rigor | | | |
| traceability_integrity | | | |

- aggregate_score:
- gap_analysis_to_9.5:
- top_3_improvement_actions:
- all three items must reflect the actual failing or remaining-gap signals from quality, Mermaid, consistency, and traceability results

## 10. Warnings
- list all `pass-with-review-bound` and `partial` items
- include warning-level semantic findings such as ADR depth, sampled endpoint/scenario thinness, and scenario GWT coverage gaps
- explain why they are not `fail`
- state what downstream may rely on
- state what downstream must not silently assume

## 11. Blockers
- list all blocked items
- map each blocker to remediation path
- identify which blocker prevents implementation-facing handoff

## 12. Admission Recommendation
- recommended_formal_state:
  - `pass | pass-with-review-bound-items | blocked`
- reasoning:
- implementation_forbidden_assumptions:
- unresolved_truth_to_preserve:

## 13. Convergence Conclusion
- design_package_assembled:
  - `yes | no`
- engineering_spec_pack_converged:
  - `yes | no`
- realizability_judgment:
- strongest_supported_readiness_label:
  - `implementation-planning-ready | pass-with-review-bound-items | blocked`
- next_round_focus:
- make this section conditional on the actual remaining gaps; do not list already-passed validators as open work
