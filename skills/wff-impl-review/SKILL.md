---
name: wff-impl-review
description: Use when running the Phase-3 structural code review after tests are green and you need to inspect architecture consistency, contract drift, naming, duplication, and dependency direction.
---

# Phase-3 Code Review

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


## Scope

This skill owns the Stage-04 structural review after implementation evidence is already green.

It reviews quality, not feature correctness.
If the review finds a functional bug that should have been caught by contract, scenario, or replay tests, send the work back to S02/S03 instead of pretending review can absorb the gap.

## Reference Package

Read `reference-packages/phase3-implementation-delivery/wff-impl-review/` for the capability contract, SOP, output template, and source cards.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write findings, severity judgments, evidence summaries, remediation guidance, and final review conclusions in Chinese
- preserve code, file paths, commands, symbols, API/schema field names, trace ids, artifact ids, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only review reports or metrics commentary unless the user explicitly requests English

## Rules

- Review only against current run evidence, not against hoped-for intent.
- Contract drift, placeholder code, or scaffold-only entrypoints are structural findings, not cosmetic notes.
- Do not waive naming, dependency-direction, or error-envelope drift just because the build is green.
- If the code is still placeholder-heavy, stop the review from pretending the slice is stable.
- Every high or critical finding must point to concrete evidence in current files or generated reports.
- High-risk public operations require behavior cards before a business-depth pass can be claimed.
- Service/Domain/Repository/Adapter implementation must be covered by P2-authored implementation action cards; missing source material is `action_card_source_material_missing`, not a reviewer preference.
- Behavior-card and action-card trace authority must come from `wff-base-traceability-management`; a P3-only trace registry is not sufficient evidence of P1/P2 continuity.

Resolution matrix / discovery policy:

- P3 must consume `p1-value-to-p2-operation-resolution-matrix.json`, `implementation-component-catalog.json`, and `component-action-card-obligation-matrix.json` as canonical JSON bridge artifacts before claiming behavior/action-card source closure.
- The discovery policy is `canonical-json-first-markdown-diagnostic-only`: markdown sections may explain or diagnose missing bridge material, but they do not replace canonical JSON for green trace/action-card authority.
- Minimal operation resolution rows must carry `operation_id`, `api_endpoint`, `http_method`, `risk_tier`, concrete `P1-*` trace IDs, concrete `P2-*` contract/source IDs, `source_files`, `source_anchors`, and `source_requirement_status`.
- Classify missing bridge artifacts as `matrix_missing_from_p2`; classify markdown-only bridge material without canonical JSON as `matrix_present_loader_missed`; classify malformed rows or missing required fields as `matrix_present_invalid_shape`; classify rows without concrete P1 IDs as `matrix_present_no_p1_ids`.
- If the selected Phase-2 root lacks these bridge artifacts, P3 must return upstream or mark review-bound instead of inferring operation/action-card source authority from filenames, endpoint names, or P3-local trace files.
- Flag `component_action_card_obligation_missing`, `action_card_depth_mismatch`, `action_card_test_gap`, and `action_card_implementation_gap` when card-test-code closure breaks.
- If service/repository code does not implement behavior-card pseudocode steps, classify it as a `P3 implementation gap`.
- optional UI compiled bindings are not global OpenAPI authority; when `require_frontend_contract` is false, do not report OpenAPI authority drift merely because optional UI compiled bindings cover only a subset of backend operations.
- When `require_frontend_contract` is true, compiled bindings become the promoted contract authority and OpenAPI/types/client counts must align with them.
- payload typing review is scoped to backend implementation targets; frontend page helper `payload: unknown` is not backend implementation genericity.
- Flag backend genericity only when controller/service/repository targets keep generic `payload: unknown` execution instead of contract-derived typed inputs or behavior-card mapped context.


## Generated Test Quality Review

Review generated tests as code-level delivery artifacts, not only as green reports.

Keep three evidence layers separate:

1. `script pass` — the toolchain executed and produced reports.
2. `runtime pass` — tests ran against the intended runtime/API/DB path and passed.
3. `code-level test quality pass` — manual review confirms the tests contain meaningful assertions.

For each reviewed test family, ask:

- If this assertion failed, what concrete business/API/DB/scenario risk would it reveal?
- Does the test check domain fields, state transition, persistence evidence, permission boundary, error semantics, idempotency, replay continuity, or scenario outcome?
- Is any assertion only proving that a helper, mock, generated runtime, or wrapper exists?
- Are weak assertions only helper guards, or are they the main proof?
- Does a replay test honestly stay within handoff-continuity scope instead of claiming full E2E readiness?

Classify generated-test findings as:

- `blocker`: fake-green, helper/toolkit self-check as main proof, invocation-only test, shape-only core test, or failure-path mismatch
- `warning`: generic truthiness, low diagnostic precision, missing constraint detail, or thin but non-core assertions
- `allowed`: helper guard or continuity anchor that is paired with stronger semantic assertions
- `follow-up`: improvement that increases diagnosability without changing the current acceptance verdict

Do not declare code-level test quality pass from runtime reports alone.

## Required Inputs

Read:
- `docs/phases/phase-3/phase-3-skill-architecture-design-v0.1.md`
- the case `openapi.yaml` and any generated final OpenAPI candidate
- the Phase-2 `wff-base-traceability-management` registry (`.trace/trace.db`) and traceability report when present
- the case `phase-3-trace-registry.json` or `phase-3-trace-registry-final.json`
- the case `implementation-bindings.json`
- the case `phase3-wp-gate.json`
- the case `phase3-verification-ledger.json` when present
- the case `engineering-spec-pack.md` or glossary-bearing Phase-2 handoff
- the current implementation source tree and generated tests
- `checklists/structure-consistency.yaml`
- `checklists/naming-consistency.yaml`

## Required Outputs

- `code-review-report.md`
- `code-review-metrics.json`

## Primary Tool

- use the review playbook to produce `code-review-report.md` and `code-review-metrics.json`; optional code-review support mode is full-pack/source-tree only

## Review Playbook

Review in this order:

1. Behavior-card alignment for high-risk public operations:
   - list reviewed high-risk operations explicitly
   - confirm behavior-card pass before implementation-depth pass
   - confirm card/test/code consistency before declaring business-deep implementation
   - distinguish `script pass`, `runtime pass`, `test quality pass`, `behavior-card pass`, and `implementation-depth pass`
2. Trace truth:
   - Phase-2 `wff-base-traceability-management` registry is present, portable, and consumed as upstream authority
   - P3 trace files are derived implementation/test views, not a restarted trace identity system
   - unresolved trace subjects
   - missing implementation targets
   - contract drift from frozen OpenAPI
   - missing behavior-card binding for high-risk public operations
3. Implementation truth:
   - behavior-card pseudocode steps not visible in service/repository implementation
   - controller/service/repository files that still contain `TODO`, placeholder throws, or shell-only classes
   - generated tests that still contain `Implement ...` placeholder harnesses
   - runtime-truth scan: detect `generated-runtime`, `operation-support`, `runtime-support-kernel`, or equivalent mock-kernel dependencies in repository/adapter/core CRUD paths
4. Structural quality:
   - module structure versus frozen Phase-3 scaffold and P2 ownership model
   - stack consistency between `tech-stack-decision.yaml` and actual package dependencies
   - boundary erosion
   - naming drift
   - canonical response / error envelope consistency
   - per-function complexity pressure
   - duplication / dependency direction problems
5. Severity and disposition:
   - structural weakness with no user-facing impact yet -> medium or lower finding
   - contract drift, placeholder runtime paths, or broken dependency direction on core flow -> high or critical finding
   - mock-backed core CRUD or missing core frontend routes from the UI IA contract -> high or critical finding

## Completion Standard

Review is done only when:
- `code-review-report.md` and `code-review-metrics.json` are both generated
- reviewed target count is explicit
- placeholder or scaffold status is explicit
- contract drift status is explicit
- naming / complexity / duplication / dependency-direction checks are not silently skipped
- the final report makes clear whether the slice is structurally ready, blocked, or sent back to implementation
