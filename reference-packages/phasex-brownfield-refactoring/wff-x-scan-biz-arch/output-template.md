# wff-x-scan-biz-arch Output Template — scan-biz-arch

## 1. Document Metadata

- document_name:
- skill_id: `wff-x-scan-biz-arch`
- skill_name: `scan-biz-arch`
- version:
- status: `draft | review | approved`
- source_status: `observed | mixed | inference-heavy`

## 2. Traceability and Scope

- artifact_id:
- system_root:
- business_source_scope:
  - `docs | code-behavior | stakeholder-notes | support-history | mixed`
- baseline_scope:
  - `full-business-system | bounded-domain | bounded-flow`
- produced_for:
  - `PhaseX Wave-2 first-tranche`
- primary_downstream_consumer:
  - `P1`
- secondary_downstream_consumer:
  - `P2`

## 3. Context and Objective

- discovery_objective:
- current_business_context:
- explicit_unknowns:
- business_truth_packet:
  - observed_business_evidence:
    | evidence_id | source_reference | observed_business_fact | confidence |
    |---|---|---|---|
    |  |  |  | `high | medium | low` |
  - inferred_business_semantics:
    | inference_id | inferred_meaning | supporting_evidence | uncertainty |
    |---|---|---|---|
    |  |  |  |  |
  - source_conflict_notes:
    | conflict_id | source_a | source_b | conflict | claim_ceiling |
    |---|---|---|---|---|
    |  |  |  |  |  |
  - explicit_unknowns:
    | unknown_id | unknown | why_available_sources_do_not_prove_it | downstream_impact |
    |---|---|---|---|
    |  |  |  |  |
  - downstream_truth_implications:
    | truth_id | implication_for_p1 | secondary_implication_for_p2 |
    |---|---|---|
    |  |  |  |

## 4. Core Structured Output

- role_and_actor_inventory:
  | role_id | role_or_actor | observed_actions | authority_or_permission_hint | evidence | confidence |
  |---|---|---|---|---|---|
  |  |  |  |  |  | `high | medium | low` |

- process_and_workflow_map:
  | flow_id | flow_name | priority | actors | trigger | outcome | evidence |
  |---|---|---|---|---|---|---|
  |  |  | `P0 | P1 | P2 | unknown` |  |  |  |  |

- flow_priority_rationale:
  | flow_id | role_weight | frequency_signal | business_or_operational_risk | priority_rationale |
  |---|---|---|---|---|
  |  |  |  |  |  |

- business_rule_register:
  | rule_id | rule | source | applies_to | confidence | unresolved_question |
  |---|---|---|---|---|---|
  |  |  |  |  | `high | medium | low` |  |

- exception_and_edge_case_register:
  | exception_id | exception_or_edge_case | observed_handling | evidence | uncertainty |
  |---|---|---|---|---|
  |  |  |  |  |  |

- p1_consumption_packet:
  - source_truths:
  - inferred_truths:
  - explicit_unknowns:
  - source_conflicts:
  - claim_ceiling:

- p2_consumption_packet:
  - boundary_hints:
  - invariant_hints:
  - role_permission_constraints:
  - unresolved_architecture_questions:

## 5. Recommended Next Move

- preferred_profile_exit:
  - `return-to-p1 | continue-to-target-arch-design | stop-for-review`
- rationale:

## 6. Verification and Confidence

- verification_method:
- confidence_profile:
  - role_confidence:
    - `high | medium | low`
  - flow_confidence:
    - `high | medium | low`
  - rule_confidence:
    - `high | medium | low`
  - source_truth_confidence:
    - `high | medium | low`
