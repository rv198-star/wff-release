---
name: wff-impl-compose-verification-suites
description: Use when generating or extending the Phase-3 failing test pack, including contract tests, scenario tests, replay tests, fixtures, and trace-to-test coverage surfaces.
---

# Phase-3 Integration Testing

## Scope

This skill owns S02 and the replay-heavy parts of S04.

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
