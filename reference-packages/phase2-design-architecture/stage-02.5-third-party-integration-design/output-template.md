# Stage-02.5 Output Template — third-party-integration-architecture-design

## 1. Document Metadata
- document_name:
- stage: `third-party-integration-architecture-design`
- version:
- status: `draft | provisional | review | approved`
- source_status: `user-confirmed | provisional | mixed`

## 1.1 Traceability Naming and Registry
- artifact_id:
- artifact_type:
  - `ARCH | DEPENDENCY | INTEGRATION | ASSUME | RISK`
- depends_on:
- feeds:
- source_path:
- source_anchor:
- traceability_managed_by:
  - `wff-base-traceability-management`

## 2. Context and Objective
- stage_objective:
- upstream_dependency_signal_summary:
- upstream_stage_alignment:
  - Stage-01 boundary / constraint posture
  - Stage-02 consuming modules / services
- assumptions:
- explicit_non_goals:

## 3. Core Structured Output
- activation_decision:
  - stage_status:
    - `active | skipped`
  - decision_basis:
  - trigger_evidence:
  - skip_reason:
- third_party_dependency_manifest:
  - minimum_count: `>=1 when stage_status=active`
  - preferred_expression:
    - machine-readable table
  - required_table_template:
    - dependency_id:
    - dependency_type:
      - `capability | data | infrastructure | identity | platform`
    - capability:
    - consuming_module:
    - mvp_criticality:
      - `critical | important | optional`
    - candidate_providers:
    - known_constraints:
- integration_decision_records:
  - minimum_count: `>= dependency_count when stage_status=active`
  - required_record_template:
    - idr_id:
    - dependency_id:
    - provider:
    - integration_pattern:
      - `direct-call | sdk | adapter-layer | message-queue | webhook | gateway`
    - internal_interface:
    - authentication_method:
    - key_management:
    - timeout:
    - retry_policy:
    - fallback_strategy:
    - data_boundary_note:
    - replacement_posture:
- integration_adapter_specifications:
  - preferred_expression:
    - machine-readable table
  - required_table_template:
    - dependency_id:
    - internal_port:
    - provider_endpoint:
    - error_mapping:
    - mock_strategy:
- integration_test_strategy:
  - preferred_expression:
    - machine-readable table
  - required_table_template:
    - dependency_id:
    - local_strategy:
    - ci_strategy:
    - staging_strategy:
    - production_guardrail:
    - negative_path_coverage:
- integration_risk_register:
  - preferred_expression:
    - machine-readable table
  - required_table_template:
    - risk_id:
    - dependency_id:
    - risk_description:
    - impact:
    - likelihood:
    - mitigation:
    - owner:

## 4. Diagram / Structured Representation
- diagram_obligation: `optional but recommended`
- recommended_view:
  - one flowchart showing internal modules, adapter seams, and provider nodes

### 4.1 Mermaid Placeholder — Integration Boundary Overview

```mermaid
flowchart LR
    InternalModule[Internal Module] --> AdapterPort[Internal Port / Adapter]
    AdapterPort --> ProviderAPI[Third-Party Provider]
```

## 5. Provenance / Confidence / Verification
- source: `user | inferred | external | mixed`
- confidence_profile:
  - provider_posture_confidence: `confirmed | partially-confirmed | inferred`
  - auth_and_key_confidence: `confirmed | partially-confirmed | inferred`
  - fallback_confidence: `confirmed | provisional | review-bound`
- verification:
  - `required | waived | confirmed`
- assumptions_to_validate:
- what_changes_if_wrong:
