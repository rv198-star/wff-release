# wff-x-plan-test-protection Output Template — plan-test-protection

## 1. Document Metadata

- document_name:
- skill_id: `wff-x-plan-test-protection`
- skill_name: `plan-test-protection`
- version:
- status: `draft | review | approved`
- based_on_artifacts:

## 2. Safety-Net Context

- change_intent_summary:
- protected_scope:
- critical_invariants:
- existing_test_posture_summary:
- safety_net_strategy:
  - protected_behavior:
  - fastest_repeatable_feedback:
  - minimum_pre_change_protection:
  - change_blockers:
  - evidence_to_collect_before_change:

## 3. Core Structured Output

- safety_net_candidate_list:
  | candidate_id | protected_surface | risk_addressed | current_gap | test_type | priority |
  |---|---|---|---|---|---|
  |  |  |  |  | `unit | contract | integration | smoke` | `P0 | P1 | P2` |

- critical_path_protection_plan:
  | path_id | path_description | why_critical | minimum_protection | must_exist_before_change |
  |---|---|---|---|---|
  |  |  |  |  | `yes | no` |

- execution_order:
  | order | work_item | dependency | owner_hint | expected_evidence |
  |---|---|---|---|---|
  | 1 |  |  |  |  |

- effectiveness_criteria:
  | criterion_id | criterion | verification_method | pass_rule |
  |---|---|---|---|
  |  |  |  |  |

- go_no_go_protection_decision:
  - decision:
    - `blocked-until-protected | can-start-with-guardrails | protected-enough`
  - rationale:
  - claim_ceiling:

- refactoring_discipline_guardrails:
  - self_testing_feedback_loop:
    - `ready | partial | missing`
  - fastest_repeatable_protection:
  - small_step_execution_rule:
  - branch_by_abstraction_trigger:
  - behavior_preservation_boundary:

## 4. Go / No-Go Recommendation

- implementation_gate:
  - `blocked-until-protected | can-start-with-guardrails | protected-enough`
- rationale:
- remaining_review_bound_items:

## 5. Verification and Confidence

- protection_planning_method:
- confidence_profile:
  - hotspot_coverage_confidence:
    - `high | medium | low`
  - test_effectiveness_confidence:
    - `high | medium | low`
