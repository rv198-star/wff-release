# wff-x-scan-code-baseline Output Template — scan-code-baseline

## 1. Document Metadata

- document_name:
- skill_id: `wff-x-scan-code-baseline`
- skill_name: `scan-code-baseline`
- version:
- status: `draft | review | approved`
- source_status: `observed | mixed`

## 2. Traceability and Scope

- artifact_id:
- system_root:
- baseline_scope:
  - `full-repository | bounded-slice`
- downstream_profile:
  - `assessment-only | technical-refactor | target-driver`
- produced_for:
  - `PhaseX Wave-1 | PhaseX Wave-2 baseline lane`
- primary_downstream_consumer:
  - `P2`
- secondary_downstream_consumer:
  - `P3 seed material only`

## 3. Context and Objective

- extraction_objective:
- repository_summary:
- visible_constraints:
- explicit_unknowns:
- codebase_truth_packet:
  - observed_code_evidence:
    | evidence_id | code_reference | observed_fact | confidence |
    |---|---|---|---|
    |  |  |  | `high | medium | low` |
  - inferred_brownfield_semantics:
    | inference_id | inferred_meaning | supporting_evidence | uncertainty |
    |---|---|---|---|
    |  |  |  |  |
  - runnability_evidence:
    | command_or_check | result | evidence | claim_ceiling |
    |---|---|---|---|
    |  |  |  |  |
  - explicit_unknowns:
    | unknown_id | unknown | why_repo_does_not_prove_it | downstream_impact |
    |---|---|---|---|
    |  |  |  |  |
  - downstream_truth_implications:
    | truth_id | implication_for_p2 | implication_for_px04_px06_px07 | optional_p3_seed_follow_up |
    |---|---|---|---|
    |  |  |  |  |

## 4. Core Structured Output

- runtime_stack_inventory:
  | layer | selected_stack | evidence | confidence |
  |---|---|---|---|
  | language/runtime |  |  |  |
  | framework |  |  |  |
  | persistence |  |  |  |
  | async/queue |  |  |  |
  | deployment/tooling |  |  |  |

- entrypoint_inventory:
  | surface_id | surface_type | location | purpose | evidence | confidence |
  |---|---|---|---|---|---|
  |  | `http | worker | cli | cron | event-consumer` |  |  |  |  |

- module_map:
  | module_id | path | responsibility | key_dependencies | outward_surfaces | notes |
  |---|---|---|---|---|---|
  |  |  |  |  |  |  |

- existing_system_conventions:
  - coding_style:
    | convention_id | observed_convention | evidence | confidence | downstream_handling |
    |---|---|---|---|---|
    |  |  |  | `high | medium | low` | preserve as brownfield constraint unless P2 accepts migration |
  - naming_conventions:
    | convention_id | scope | observed_pattern | examples | confidence | downstream_handling |
    |---|---|---|---|---|---|
    |  | `module | package | class | function | field | event | migration | generated artifact` |  |  | `high | medium | low` |  |
  - api_route_conventions:
    | convention_id | route_or_surface | parameter_style | response_or_error_shape_hint | evidence | confidence |
    |---|---|---|---|---|---|
    |  |  |  |  |  | `high | medium | low` |
  - test_conventions:
    | convention_id | test_location_or_pattern | fixture_pattern | command_or_framework_hint | confidence | downstream_handling |
    |---|---|---|---|---|---|
    |  |  |  |  | `high | medium | low` | keep review-bound when no evidence exists |
  - claim_ceiling: observed existing-system convention hints only; not target architecture authority, rewrite permission, or full style-guide proof

- dependency_hotspots:
  | hotspot_id | dependency_or_framework | why_it_matters | blast_radius | evidence |
  |---|---|---|---|---|
  |  |  |  |  |  |

- third_party_dependency_scan:
  - scan_result:
    - `none-detected | detected | uncertain`
  - note: `preliminary-` indicates baseline-stage dependency hints only, not a finalized vendor selection or formal downstream manifest
  - preliminary-third-party-dependency-manifest:
    | dependency_hint_id | detected_surface | probable_capability | probable_provider_or_sdk | confidence | follow_up |
    |---|---|---|---|---|---|
    |  |  |  |  | `high | medium | low` |  |

- refactor_signal_register:
  | signal_id | location | observed_signal | likely_refactor_style | confidence | note |
  |---|---|---|---|---|---|
  |  |  |  | `small-step | preparatory-refactor | branch-by-abstraction | unclear` | `high | medium | low` |  |

- runnability_precheck:
  - runnability_state:
    - `runnable | partially-runnable | blocked`
  - startup_method:
  - missing_prerequisites:
  - observed_failures:
  - environment_notes:

- uncertainty_register:
  | unknown_id | unknown | why_unknown | impact_on_next_step |
  |---|---|---|---|
  |  |  |  |  |

- p2_consumption_packet:
  - architecture_constraints:
  - boundary_hints:
  - external_surface_constraints:
  - unresolved_architecture_questions:

- p3_seed_material:
  - candidate_work_areas:
  - hotspot_slices:
  - likely_action_card_candidates:
  - seed_material_claim_ceiling:

## 5. Recommended Next Move

- preferred_profile_exit:
  - `assessment-only | technical-refactor | target-driver | stop`
- rationale:

## 6. Verification and Confidence

- verification_method:
- confidence_profile:
  - codebase_shape_confidence:
    - `high | medium | low`
  - surface_inventory_confidence:
    - `high | medium | low`
  - runnability_confidence:
    - `high | medium | low`
  - p2_consumption_confidence:
    - `high | medium | low`
  - p3_seed_confidence:
    - `high | medium | low`
