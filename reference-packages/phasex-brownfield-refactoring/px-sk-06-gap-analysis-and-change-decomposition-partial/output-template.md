# PX-SK-06 Output Template — gap-analysis-and-change-decomposition (partial)

## 1. Document Metadata

- document_name:
- skill_id: `PX-SK-06`
- skill_name: `gap-analysis-and-change-decomposition`
- mode: `partial`
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
  | question_id | question | blocking_level | owner_hint |
  |---|---|---|---|
  |  |  | `high | medium | low` |  |

- downstream_route_recommendation:
  - recommended_route:
    - `return-to-phase-1 | direct-to-phase-3 | protect-first-then-continue`
  - route_rationale:
  - handoff_requirements:

## 4. Verification and Confidence

- packaging_method:
- confidence_profile:
  - bounded_scope_confidence:
    - `high | medium | low`
  - compatibility_confidence:
    - `high | medium | low`
