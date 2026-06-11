# PX-SK-01 Output Template — codebase-baseline-extraction

## 1. Document Metadata

- document_name:
- skill_id: `PX-SK-01`
- skill_name: `codebase-baseline-extraction`
- version:
- status: `draft | review | approved`
- source_status: `observed | mixed`

## 2. Traceability and Scope

- artifact_id:
- system_root:
- baseline_scope:
  - `full-repository | bounded-slice`
- downstream_profile:
  - `assessment-only | technical-refactor | partial-change`
- produced_for:
  - `PhaseX Wave-1`

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
    | truth_id | implication_for_px04_px06_px07 | required_follow_up |
    |---|---|---|
    |  |  |  |

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

## 5. Recommended Next Move

- preferred_profile_exit:
  - `assessment-only | technical-refactor | partial-change | stop`
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
