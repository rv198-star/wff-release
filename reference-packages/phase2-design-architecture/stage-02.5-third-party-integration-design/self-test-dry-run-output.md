# Stage-02.5 Self-Test Dry-Run Output — active integration lane

## 1. Core Structured Output
- activation_decision:
  - stage_status:
    - `active`
  - decision_basis:
    - Phase-1 and Stage-02 both show material identity and LLM provider dependence
  - trigger_evidence:
    - provider-boundary behavior materially affects Stage-03 contracts and Phase-3 adapter work
- third_party_dependency_manifest:
  | dependency_id | dependency_type | capability | consuming_module | mvp_criticality | candidate_providers | known_constraints |
  |---|---|---|---|---|---|---|
  | DEP-IDENTITY | identity | workforce identity and session exchange | `geo.identity.access` | critical | WorkOS, Auth0 | workforce SSO, token lifecycle, tenant mapping |
  | DEP-LLM | capability | recommendation generation | `geo.recommend.adapter` | critical | OpenAI, Anthropic | quota, latency, prompt privacy |
- integration_decision_records:
  - idr_01:
    - idr_id: `IDR-IDENTITY-01`
    - dependency_id: `DEP-IDENTITY`
    - provider: `WorkOS`
    - integration_pattern: `adapter-layer`
    - internal_interface: `IdentitySessionPort`
    - authentication_method: `oauth2`
    - key_management: `server-side secrets manager with quarterly rotation`
    - timeout: `5s`
    - retry_policy: `bounded retry on token exchange network failure only`
    - fallback_strategy: `fail closed and keep pending sign-in visible to the caller`
    - data_boundary_note: workforce identity tokens stay server-side
    - replacement_posture: medium swap cost
  - idr_02:
    - idr_id: `IDR-LLM-01`
    - dependency_id: `DEP-LLM`
    - provider: `OpenAI`
    - integration_pattern: `adapter-layer`
    - internal_interface: `RecommendationCompletionPort`
    - authentication_method: `api-key`
    - key_management: `server-side secrets manager with monthly rotation review`
    - timeout: `20s`
    - retry_policy: `two retries with jitter for transient 429/5xx`
    - fallback_strategy: `return degraded review-bound response and queue retry when safe`
    - data_boundary_note: strip direct PII before provider calls
    - replacement_posture: low-medium swap cost
- integration_adapter_specifications:
  | dependency_id | internal_port | provider_endpoint | error_mapping | mock_strategy |
  |---|---|---|---|---|
  | DEP-IDENTITY | IdentitySessionPort | POST /oauth/token | oauth/network/forbidden -> INTERNAL_AUTH_* errors | sandbox + fixture |
  | DEP-LLM | RecommendationCompletionPort | POST /v1/responses | 429/5xx/timeout -> LLM_* errors | fixture + contract test |
- integration_test_strategy:
  | dependency_id | local_strategy | ci_strategy | staging_strategy | production_guardrail | negative_path_coverage |
  |---|---|---|---|---|---|
  | DEP-IDENTITY | fixture-based identity exchange | contract tests for token/error mapping | sandbox tenant | fail closed on auth drift | auth fail + tenant mismatch + timeout |
  | DEP-LLM | fixture-based mock completions | contract tests for payload/error mapping | sandbox or low-cost test key | budget cap + latency alert | rate limit + timeout + degraded mode |
- integration_risk_register:
  | risk_id | dependency_id | risk_description | impact | likelihood | mitigation | owner |
  |---|---|---|---|---|---|---|
  | IR-IDENTITY-01 | DEP-IDENTITY | IdP token exchange or tenant claim drift breaks login | high | medium | explicit token mapping tests + fail-closed posture | identity owner |
  | IR-LLM-01 | DEP-LLM | LLM latency or quota event delays recommendation flow | high | medium | jitter retry + degraded response + budget alerts | recommendation owner |

