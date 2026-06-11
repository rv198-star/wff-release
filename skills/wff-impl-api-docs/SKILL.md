---
name: wff-impl-api-docs
description: Use when generating or validating Phase-3 API documentation from the frozen OpenAPI contract and the implemented code, including consistency diffing against the S01 source.
---

# Phase-3 API Doc Generation

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


This skill owns final API documentation and contract consistency reporting.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-api-docs/` for the capability contract, SOP, output template, and source cards.

Primary capability runner:

```bash
python3 scripts/phase3/run_impl_api_docs.py \
  --baseline-openapi <phase3-output>/contracts/openapi.yaml \
  --output-dir <phase3-output>/api-docs \
  --title "Phase-3 API Documentation"
```

## Core Rule

S01 `openapi.yaml` remains the source of truth.

S03 may add compatible implementation detail, but must not silently change frozen public fields, paths, methods, envelopes, or status semantics.
Any incompatible diff must point back to an ADR or be treated as blocked.

For `v1.2.3` P3, API docs are not an endpoint list only. Core API documentation should expose evidence linkage:

- P1 business scenario / acceptance intent
- P2 contract, RBI, or work-package anchor
- executable test evidence
- evidence level, such as contract, unit, integration, or runtime-http
- infrastructure proof when persistence, cache, queue, or external components affect correctness
- review-bound / risk note when the API remains under review

If evidence linkage is missing for a core API, publication may still generate assets, but delivery readiness must remain capped until the missing proof is explicit.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write overview text, usage guidance, example explanations, caveats, and handoff-facing summaries in Chinese
- preserve code, file paths, commands, routes, API/schema field names, error codes, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only API documentation prose unless the user explicitly requests English

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `contracts/openapi.yaml`
- the case generated API client / shared types when present
- implementation evidence that may materialize a candidate final OpenAPI
- the latest code review / delivery state if the diff is ambiguous

## Execution Playbook

1. Generate the final public API artifact.
   Materialize `openapi-final.yaml` and doc assets from the frozen S01 contract unless there is explicit compatible implementation detail to merge in.
2. Diff final output against frozen truth.
   Run the consistency diff and classify changes into:
   - compatible additive detail
   - incompatible contract drift
3. Resolve publication state explicitly.
   If the diff is incompatible, do not publish silently.
   The run must either:
   - point to an approved ADR / contract-source update, or
   - stay blocked until the frozen source is corrected.

Primary outputs:
- final OpenAPI artifact
- consistency diff report
- generated API documentation site/assets
- evidence-linked API surface table when evidence metadata is available
- publication / escalation verdict embedded in the consistency report

Primary tools:
- `scripts/phase3/run_impl_api_docs.py`
- `scripts/phase3/phase3_delivery_gate.py --mode api-docs`
- `scripts/phase3/openapi_diff_checker.py`

## Completion Standard

This skill is done only when:
- `openapi-final.yaml` exists
- doc assets are generated from current truth
- diff status is explicit
- core API evidence linkage is present or the delivery gate records the missing linkage
- incompatible drift is either escalated with ADR linkage or treated as blocked
