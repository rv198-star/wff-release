# Contract Spine Source Register（v0.1）

## Purpose

This register defines the initial source bundles for the cross-phase **Contract Spine Pack**.

It intentionally mixes:

- Tier-0: real-world templates/examples (fast-to-absorb, gateable fields)
- Tier-1: authoritative references (normalize field types and gate patterns)

---

## Source bundles

| source_container | source_type | primary_stage_focus | coverage_role | authoring_readiness | notes |
|---|---|---|---|---|---|
| `contract-registry-samples` | `template-bundle` | Phase-2 Stage-03; Phase-3 Stage-01; Phase-4 Acceptance | primary-bundle | draft | Minimal registry fields for `API-*` ownership, spec location, status, dependency, versioning policy pointer. |
| `openapi` | `official-spec-bundle` | Phase-2 Stage-03; Phase-3 | supporting-bundle | draft | OpenAPI spec as machine-readable contract; focus on diff/lint/compatibility thinking, not tool setup. |
| `asyncapi` | `official-spec-bundle` | Phase-2 Stage-03; Phase-3 | supporting-bundle | authoring-input-ready | Already present under `sources/web/asyncapi/` for async contract lanes. |
| `cloudevents` | `official-spec-bundle` | Phase-2 Stage-03; Phase-3 | supporting-bundle | authoring-input-ready | Already present under `sources/web/cloudevents/` for event envelope contracts. |
| `cdc-testing` | `external-method-bundle` | Phase-3 Stage-01/02 | primary-bundle | draft | Consumer-driven contracts as a gate: provider verification blocks merge/release if drift is detected. |
| `pact` | `tool-workflow-bundle` | Phase-3 Stage-01/02 | supporting-bundle | draft | Pact as a concrete CDC workflow example. Absorb workflow structure; keep tool specifics optional. |
| `error-model-samples` | `template-bundle` | Phase-2 Stage-03; Phase-3 | primary-bundle | draft | Structured errors are part of the contract; normalize fields and compatibility rules. |
| `compatibility-evolution-policy` | `policy-bundle` | Phase-2 Stage-03; Phase-3 | primary-bundle | draft | Prefer compatible extension; define versioning triggers and deprecation policy fields. |

---

## Immediate authoring targets

1) Contract Registry template (docs-first)
2) Contract Policy field-types (errors + compatibility + versioning triggers)
3) Phase-3 gate integration: `api_contract_smoke_cmd`
4) Phase-4 acceptance mapping fields: `TEST-* -> API-* -> REQ-*`

### Pointers

- Contract Registry template: `templates/contract-registry-template.md`
