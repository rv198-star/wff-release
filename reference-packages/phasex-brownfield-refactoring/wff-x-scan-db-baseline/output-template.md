# wff-x-scan-db-baseline Output Template — scan-db-baseline

## 1. Document Metadata

- document_name:
- skill_id: `wff-x-scan-db-baseline`
- skill_name: `scan-db-baseline`
- version:
- status: `draft | review | approved`
- source_status: `observed | mixed`

## 2. Traceability and Scope

- artifact_id:
- system_root:
- schema_source:
  - `database-connection | ddl | migration-files | orm-models | documentation | mixed`
- baseline_scope:
  - `full-database | bounded-schema | bounded-slice`
- produced_for:
  - `PhaseX Wave-2 first-tranche`
- primary_downstream_consumer:
  - `P2`
- secondary_downstream_consumer:
  - `P3 seed material only`

## 3. Context and Objective

- extraction_objective:
- visible_data_constraints:
- explicit_unknowns:
- database_truth_packet:
  - observed_data_evidence:
    | evidence_id | source_reference | observed_fact | confidence |
    |---|---|---|---|
    |  |  |  | `high | medium | low` |
  - inferred_schema_semantics:
    | inference_id | inferred_meaning | supporting_evidence | uncertainty |
    |---|---|---|---|
    |  |  |  |  |
  - migration_pressure:
    | pressure_id | surface | pressure_type | evidence | claim_ceiling |
    |---|---|---|---|---|
    |  |  | `schema-change | shared-table | data-volume | sensitive-data | external-sync | unknown` |  |  |
  - explicit_unknowns:
    | unknown_id | unknown | why_schema_does_not_prove_it | downstream_impact |
    |---|---|---|---|
    |  |  |  |  |
  - downstream_truth_implications:
    | truth_id | implication_for_p2 | optional_p3_seed_follow_up |
    |---|---|---|
    |  |  |  |

## 4. Core Structured Output

- table_entity_inventory:
  | table_or_collection | likely_entity | key_fields | owner_confidence | evidence |
  |---|---|---|---|---|
  |  |  |  | `high | medium | low` |  |

- relationship_constraint_map:
  | relationship_id | from_surface | to_surface | constraint_type | evidence | uncertainty |
  |---|---|---|---|---|---|
  |  |  |  | `foreign-key | logical-reference | unique | check | inferred | unknown` |  |  |

- index_and_query_risk_notes:
  | risk_id | table_or_query_surface | observed_signal | likely_risk | evidence |
  |---|---|---|---|---|
  |  |  |  |  |  |

- sensitive_data_register:
  | field_id | table_or_surface | sensitivity_hint | evidence | handling_uncertainty |
  |---|---|---|---|---|
  |  |  | `pii | payment | auth | health | location | unknown` |  |  |

- p2_consumption_packet:
  - data_constraints:
  - storage_boundary_hints:
  - interface_or_schema_invariants:
  - unresolved_data_questions:

- p3_seed_material:
  - migration_hotspots:
  - persistence_test_seed:
  - rollback_or_backout_risk_seed:

## 5. Recommended Next Move

- preferred_profile_exit:
  - `continue-to-biz-arch-scan | continue-to-target-arch-design | stop-for-review`
- rationale:

## 6. Verification and Confidence

- verification_method:
- confidence_profile:
  - schema_shape_confidence:
    - `high | medium | low`
  - relationship_confidence:
    - `high | medium | low`
  - production_data_confidence:
    - `high | medium | low`
  - migration_pressure_confidence:
    - `high | medium | low`
