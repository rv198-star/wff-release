# wff-x-intake-target-driver Output Template — target-driver-intake

## 1. Document Metadata

- document_name:
- skill_id: `wff-x-intake-target-driver`
- skill_name: `target-driver-intake`
- mode: `target-driver`
- version:
- status: `draft | review | approved`

## 2. Change Context

- change_point_statement:
- why_now:
- bounded_scope_definition:
- excluded_scope:
- brownfield_non_goals:
- brownfield_handoff_packet:
  - phase1_consumption_notes:
  - phase3_consumption_notes:
  - compatibility_claim_ceiling:
  - route_decision_rationale:

## 3. Core Structured Output

- px_handoff_cards:
  | card_id | title | source_scope | current_state_facts | target_driver | gap_summary | evidence_refs | inferred_semantics | explicit_unknowns | compatibility_constraints | protected_legacy_behaviors | risk_notes | recommended_route | required_prework | claim_ceiling |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | PX-HC-001 |  |  |  |  |  |  |  |  |  |  |  | `return-to-P1 | enter-P2 | protect-first | direct-to-P3 | decision-required` |  |  |

- px_to_p1_change_source_packet:
  - packet_type: `P1 Source Input Packet`
  - packet_subtype: `existing-system-change`
  - current_state_summary:
  - target_change_summary:
  - observed_business_facts:
  - inferred_business_semantics:
  - legacy_behaviors_to_preserve:
  - source_conflicts:
  - explicit_unknowns:
  - non_goals:
  - acceptance_pressure:
  - demand_change_evaluation:
    - change_intent:
    - business_impact:
    - affected_users_workflows:
    - non_goals_scope_boundaries:
    - proceed_decision:
      - `proceed-to-P1 | return-to-intake | review-bound-provisional`
  - demand_clarification_addendum:
    - clarification_status: `not-answered | answered`
    - response_source:
    - target_success_boundary:
    - acceptance_boundary:
    - priority_users_workflows:
    - scope_confirmation:
    - compatibility_confirmation:
    - conservative_default_if_unanswered:
    - remaining_review_bound_items:
  - claim_ceiling:

- px_to_p2_architecture_change_intake_packet:
  - packet_type: `P2 Existing-System Architecture Change Intake Packet`
  - packet_subtype: `existing-system-architecture-change`
  - as_is_boundary_map:
  - module_service_inventory:
  - data_storage_constraints:
  - interface_external_surface_constraints:
  - runtime_deployment_constraints:
  - compatibility_constraints:
  - technical_health_pressure:
  - target_architecture_pressure:
  - unresolved_architecture_questions:
  - architecture_change_impact_triage:
    - change_impact_level:
      - `AC-1 | AC-2 | AC-3 | AC-4`
    - compatibility_strategy:
    - migration_strategy:
    - rollback_strategy:
    - decision_gate_status:
  - evidence_state_ledger:
  - recommended_P2_entry_points:
    - `Stage-01 architecture boundary | Stage-02 module/domain decomposition | Stage-02.5 third-party integration | Stage-03 data/interface design`

- phase1_constrained_reentry_summary:
  - affected_modules:
  - impacted_surfaces:
  - acceptance_criteria:
  - recommended_route:
  - third-party-dependency-manifest:
    - dependency_id:
    - integration_change_type:
      - `add | replace | refactor-to-acl | deprecate | none`
    - compatibility_requirement:

- affected_module_register:
  | module_id | path_or_surface | why_affected | expected_change_type |
  |---|---|---|---|
  |  |  |  | `modify | extend | preserve-interface | investigate` |

- compatibility_constraints:
  | constraint_id | constraint | applies_to | break_risk | evidence |
  |---|---|---|---|---|
  |  |  |  | `high | medium | low` |  |

- brownfield_invariants:
  | invariant_id | invariant | protected_surface | why_it_matters |
  |---|---|---|---|
  |  |  |  |  |

- unresolved_questions:
  | question_id | question | blocking_level | owner_hint | owner_availability | fallback_handling |
  |---|---|---|---|---|---|
  |  |  | `high | medium | low` | `optional owner / unknown owner / no owner available` | `review-bound | conservative default | protect-first | enter-P1/P2` |

- downstream_route_recommendation:
  - recommended_route:
    - `return-to-P1 | enter-P2 | protect-first | direct-to-P3 | decision-required`
  - route_rationale:
  - handoff_requirements:

## 3.1 Owner Confirmation Policy

- Owner confirmation is optional evidence, not a required gate.
- If no owner or original maintainer is available, record `owner_availability: no owner available`, keep the affected truth review-bound, and choose a conservative compatibility-preserving route.
- Do not block P1/P2/P3 solely because owner confirmation is missing.

## 3.2 PX-to-P1 Demand Clarification Addendum

- `demand_clarification_addendum` is optional demand clarification evidence for P1.
- If answers are available, record the source, target success boundary, acceptance boundary, priority workflow, scope confirmation, compatibility confirmation, conservative default, and remaining review-bound items.
- If answers are not available, keep `clarification_status: not-answered`; missing answers must not block P1.
- The addendum improves P1 source truth, but it does not prove owner sign-off, UAT, market validation, production readiness, or production risk acceptance.
- Reviewer prompts / confirmation questions must be emitted as the sidecar `p1-demand-confirmation-checklist.md`, not embedded into the P1 source packet as requirement text.
- P1 may consume answered addendum facts and claim ceilings; it must not promote unanswered prompt text into product scope.

## 4. Verification and Confidence

- packaging_method:
- confidence_profile:
  - bounded_scope_confidence:
    - `high | medium | low`
  - compatibility_confidence:
    - `high | medium | low`
