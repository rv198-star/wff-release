# wff-x-scan-tech-health Output Template — scan-tech-health

## 1. Document Metadata

- document_name:
- skill_id: `wff-x-scan-tech-health`
- skill_name: `scan-tech-health`
- version:
- status: `draft | review | approved`
- based_on_artifact:

## 2. Assessment Context

- assessment_objective:
- assessed_scope:
- critical_unknowns:
- evidence_summary:
- brownfield_health_judgment:
  - current_change_safety:
    - `safe-enough | protect-first | assess-more | stop`
  - dominant_risk:
  - recommended_next_move:
    - `stop | assess-more | build-safety-net | proceed-technical-refactor | package-target-driver`
  - review_bound_decision:

## 3. Core Structured Output

- health_scorecard:
  | dimension | score_1_to_10 | weight | evidence | confidence | note |
  |---|---|---|---|---|---|
  | code_quality |  |  |  |  |  |
  | testability |  |  |  |  |  |
  | dependency_health |  |  |  |  |  |
  | coupling_blast_radius |  |  |  |  |  |
  | documentation_operability |  |  |  |  |  |

- top_debt_register:
  | debt_id | area | description | severity | likelihood | recommended_action | owner_hint |
  |---|---|---|---|---|---|---|
  |  |  |  | `high | medium | low` | `high | medium | low` |  |  |

- risk_matrix:
  | risk_id | risk | likelihood | impact | evidence | mitigation_direction |
  |---|---|---|---|---|---|
  |  |  | `high | medium | low` | `high | medium | low` |  |  |

- risk_to_action_map:
  | risk_id | evidence | action | why_this_action | claim_ceiling |
  |---|---|---|---|---|
  |  |  | `stop | assess-more | build-safety-net | proceed-technical-refactor | package-target-driver` |  |  |

- evidence_backed_score_rationale:
  | dimension | score_driver | supporting_evidence | uncertainty_or_ceiling |
  |---|---|---|---|
  |  |  |  |  |

- refactor_candidate_register:
  | candidate_id | hotspot_or_module | trigger_or_smell | proposed_style | required_safety_net | excluded_behavior_change |
  |---|---|---|---|---|---|
  |  |  |  | `small-step | preparatory-refactor | branch-by-abstraction | defer` |  |  |

- decision_recommendation:
  - recommended_next_move:
    - `stop | assess-more | build-safety-net | proceed-technical-refactor | package-target-driver`
  - why_now:
  - what_must_be_true_before_change:

- refactor_readiness_judgment:
  - change_mode:
    - `behavior-preserving-refactor | feature-change | mixed-change`
  - behavior_preservation_boundary:
  - two_hats_risk:
    - `low | medium | high`
  - small_steps_feasibility:
    - `yes | partial | no`
  - branch_by_abstraction_needed:
    - `yes | no | maybe`

- specialized_profile_overlays:
  - performance_profile:
    - enabled:
      - `yes | no`
    - baseline_metrics:
      | metric | value | source | threshold_or_symptom |
      |---|---|---|---|
      |  |  |  |  |
    - hotspot_evidence:
  - compliance_profile:
    - enabled:
      - `yes | no`
    - obligation_control_map:
      | obligation | current_control | evidence | coverage_status |
      |---|---|---|---|
      |  |  |  | `covered | partial | uncovered` |
    - uncovered_obligations:
  - coupling_profile:
    - enabled:
      - `yes | no`
    - coupling_metrics:
      | metric | value | source | threshold_or_rank |
      |---|---|---|---|
      | shared_tables |  |  |  |
      | dependency_cycles |  |  |  |
      | blast_radius_modules |  |  |  |

## 4. Brownfield Readiness Notes

- safe_change_without_protection:
  - `yes | no | partial`
- dominant_hotspot:
- blast_radius_summary:

## 5. Verification and Confidence

- scoring_method:
- confidence_profile:
  - overall_confidence:
    - `high | medium | low`
  - major_blindspots:
