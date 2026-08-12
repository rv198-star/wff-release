---
name: wff-impl-verification
description: Use when generating or extending the Phase-3 failing test pack, including contract tests, scenario tests, replay tests, fixtures, and trace-to-test coverage surfaces.
---

# Phase-3 Integration Testing

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns S02 and the replay-heavy parts of S04.

Primary capability runners:

```bash
python3 scripts/phase3/run_impl_verification.py \
  --mode generate-tests \
  --phase2-root <phase2-root> \
  --output-dir <phase3-output>
```

```bash
python3 scripts/phase3/run_impl_verification.py \
  --mode verify \
  --workspace-root <phase3-output>
```

`generate-tests` must not create backend or frontend application code. `verify` consumes an existing workspace and reports the current evidence ceiling.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-verification/` for the capability contract, SOP, output template, and source cards.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write test-planning notes, coverage explanations, replay rationale, and audit-facing verification summaries in Chinese
- preserve code, file paths, commands, test ids, API/schema field names, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only coverage plans, verification notes, or execution summaries unless the user explicitly requests English

## Core Rule

Tests are a primary delivery surface, not an implementation side-effect.

At S02 close:
- tests must compile
- tests must run
- tests should still fail because the implementation is not there yet

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `openapi.yaml`
- the case scenario / replay definitions from Phase-2
- the work-package ordering and trace registry

## Required Outputs

- schema test scaffolds
- contract test scaffolds
- scenario test scaffolds
- replay test scaffolds
- fixtures / helpers
- test coverage plan
- test trace matrix

Primary tools:
- `scripts/phase3/schema_test_scaffolder.py`
- `scripts/phase3/contract_test_scaffolder.py`
- `scripts/phase3/scenario_test_scaffolder.py`
- `scripts/phase3/replay_test_scaffolder.py`
- `scripts/phase3/test_trace_matrix_builder.py`

## Harness Rule

The failing scaffold is only the starting point.
When S03 starts, convert each placeholder test in this order:

1. contract test:
   - real request
   - real response envelope / error body assertion
2. scenario test:
   - real user flow or orchestration path
   - Given / When / Then assertions preserved
3. replay test:
   - preserved semantics from Phase-2 trace subject or RBI
4. data-fidelity test:
   - verify write -> independent read/state transition through the real persistence path
   - verify mock/simulation does not masquerade as persistence truth

Do not keep `throw new Error("Implement ...")` in a slice that is being presented as implemented.

### Runtime fixture identity rule

- Generated positive fixtures and persistence probes must preserve the accepted P2 field type for identifiers. Accepted P2 `data_and_interaction_decisions` type authority overrides OpenAPI types mechanically inferred from placeholder examples; OpenAPI is a fallback only when P2 has no accepted type. A genuine type conflict inside accepted P2 authority remains fail-closed / `mixed` rather than being repaired from OpenAPI. For durable update preconditions, a generated validation baseline must represent pre-update state: do not seed it from the update operation's post-update response. When an accepted create/insert operation owns the same aggregate/table, its accepted response may provide the stronger starting shape; do not copy that create request's replay/idempotency key into the baseline unless the update itself requires it. An accepted table-backed read model/current-system snapshot with no writer aggregate must still receive a validation-only baseline row when its exact operation is read-only; project request/response examples only through the accepted table fields, and never infer write authority or production-data truth from that seed. If a positive accepted insert/upsert request would collide with a validation-only baseline row on an accepted P2 unique request key, isolate only that matching baseline row before the first positive invocation in the current scenario; never perform this cleanup for negative/conflict evidence or again during replay. For caller-field negative evidence on a replay-safe write, the negative payload must not reuse a prior successful replay identity that would return-existing before validation; when the intentionally invalid field is not itself part of the replay key, vary only an accepted caller-request/idempotency identity component using a type-compatible validation value, while preserving required foreign/context identity and leaving explicit replay/conflict lanes unchanged. Persistence round-trip probes must choose columns whose accepted P2/schema types are compatible with the response identifier; fuzzy name similarity must never map a UUID identifier onto an integer/string column on another table.
- A field name ending in `_id` is not sufficient evidence that the value is a UUID.
- Normalize synthetic identifiers to deterministic UUIDs only when the accepted operation/schema field type is `uuid`.
- Preserve declared `string` and `integer` legacy/current-system identifiers so Brownfield compatibility fixtures do not silently diverge from their seeded current-state rows. Scenario success assertions must follow the frozen response scalar type as well: an identifier-shaped field name does not authorize a `String` assertion when the accepted/OpenAPI response is numeric.
- Use the same type-aware rule for request fixtures, not-found path fixtures, and persistence round-trip comparison; do not repair mismatches with scenario-specific fallback data. A not-found path probe must remain type-valid for the accepted identifier field (for example, a positive non-existing integer for an accepted integer id) so it tests not-found semantics instead of input validation. Negative version/conflict evidence must mutate the accepted version-like request field that actually exists (`expected_version`, `row_version`, `version`, or another accepted `*_version` field); do not manufacture a parallel camelCase/snake_case field that the implementation does not consume. Accepted `stale_version` is part of the conflict-family evidence vocabulary alongside explicit conflict/duplicate/idempotency codes.
- Full-suite SQL verification probes must use identities isolated from validation baseline rows already installed by the runtime harness. If a generated probe primary key would collide with a baseline/current-system seed, select a deterministic same-type probe identity instead; do not weaken uniqueness constraints, skip the SQL test, or delete accepted baseline evidence to make coverage collect.

### Generated kernel coverage rule

- The generated `tests/support/s3-realization-kernel.test.ts` must exercise every exported binding-selection/control primitive that is intentionally included in the API business-runtime coverage denominator, including exact binding selection and fail-closed unknown-slice behavior.
- Do not lower coverage thresholds or remove shared S3 runtime support from the denominator merely because a small one-operation project gives those shared functions more weight.

## Test Value Judgment Rule

A passing test suite is not automatically a high-value verification suite.

When composing or extending P3 tests, separate the responsibilities:

- `Workflow` must generate and run the required test families, collect reports, expose weak-assertion signals, and preserve traceability.
- `Agentic review` must judge whether the assertions would catch a real business, API, persistence, permission, error, replay, or scenario risk if they failed.

Do not count the following as strong evidence:

- `expect(true).toBe(true)` or equivalent tautologies
- assertions that only prove a helper/runtime toolkit is wired
- endpoint invocation with no response, state, error, or persistence assertion
- envelope or key-existence checks with no business field, failure semantic, or persistence evidence
- scenario/replay tests that lose P1/P2 intent and only walk an operation list

Allowed weak assertions are narrow guardrails only:

- helper-level null/object guards before deeper checks
- trace/linkage metadata existence checks when paired with business assertions
- shared upstream requirement/AC lineage across multiple P3 rows is not itself Trace identity abuse. Keep that lineage visible, but apply reuse/aliasing abuse checks only to the P3 row's own primary source/trace identity; a primary identity reused across incompatible read/write semantics or at suspicious frequency remains a real abuse signal.
- replay continuity anchors when the replay is explicitly scoped as handoff continuity
- array length guards when followed by item-level semantic assertions

A weak assertion may support a test, but must not be the main proof of the test.
If a test cannot name the risk it catches, mark it review-bound instead of counting it as delivery-quality evidence.

## Concurrency Honesty Rule

- Phase-3 concurrent/conflict scenarios default to `contract-level conflict-path validation`.
- Unless the packet explicitly runs real parallel workers, database contention harnesses, or equivalent runtime collision tooling, do not present these tests as proof of production race safety.
- When a scenario is simulated rather than truly parallel, keep the assertions focused on conflict handling semantics:
  - idempotency
  - optimistic-lock / version-conflict behavior
  - retry guidance
  - authoritative final state preservation
- Name and describe these tests honestly as conflict simulations if that is what they are.

## Guardrails

- Do not weaken tests to match unfinished code.
- If a contract changes, fix the contract source first, not the test names afterward.
