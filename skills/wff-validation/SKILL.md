---
name: wff-validation
description: Use when running or rerunning the official Phase-4 validation flow from a completed Phase-3 delivery root and you need a thin acceptance/coverage/closure flow rather than ad hoc QA notes.
---

# Phase-4 Validation Orchestrator

## Overview

This is the official Phase-4 entry skill.

Phase-4 is the thin read-only judgment layer after implementation.
It converts supplied Phase-3 evidence into explicit testing-validation closure, claim-ceiling, remediation-routing, and handoff-boundary artifacts.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` (env override: `WFF_OUTPUT_LOCALE`).
Unless a file format, protocol, or immutable upstream quote requires English, the current default for all human-reviewed outputs produced under this skill is Simplified Chinese (`zh-CN`).

Apply these rules:
- write acceptance text, execution summaries, closure judgments, UI review notes, and visual-evidence commentary in Chinese
- preserve code, file paths, commands, test ids, API/schema field names, trace ids, artifact ids, env vars, and protocol keywords in their canonical original form
- when an English technical term is needed for precision, introduce it once as `中文说明（English Term）`, then continue in Chinese
- do not emit English-only Phase-4 artifacts or QA conclusions unless the user explicitly requests English

## Use When

- the case already has a completed Phase-3 artifact root
- you need official validation outputs, not informal QA prose
- you need functional acceptance, UI review, and visual evidence to be tracked together without boundary drift

Do not use when:

- implementation work is still changing materially
- contracts or runtime behavior are still being redesigned
- the task is only deployment cutover execution rather than validation closure or optional development / pre-production release-readiness packaging

## Boundary

Phase-4 is not a second implementation phase.
Stage-03 is not release approval.
Phase-4 detects validation gaps, routes remediation, and caps downstream claims; it must not repair Phase-1 product truth, Phase-2 architecture truth, or Phase-3 implementation/runtime evidence by itself.
Phase-4 must read the supplied Phase-3 root as input and write Phase-4 outputs under its own output root. It must not mutate the supplied Phase-3 root.

Phase-4 is scoped to testing-validation closure over the supplied Phase-3 package and available development / pre-production evidence. It does not execute or claim real online UAT, production deployment, go-live approval, production rollback, production monitoring handover, real owner sign-off, or production risk acceptance.

External online / production / owner-signoff evidence may be consumed only when supplied. If it is absent, Stage-03 and optional Stage-04 outputs must cap their claims at development / pre-production readiness and state the missing external evidence explicitly.

Core rule:

1. `functional` acceptance is mandatory
2. `data-fidelity` acceptance is mandatory whenever Phase-3 claims real runtime/persistence truth
3. `ui-review` is explicit
4. `visual-evidence` is explicit
5. missing screenshot/manual capture must become `review-bound`, not fake green
6. critical-path UI/visual acceptance may require human sign-off even when automated evidence is green
7. high-priority Phase-2 identity decisions should bind to deny / cross-tenant / audit / token-lifecycle / secret-handling acceptance surfaces, or stay explicitly review-bound
8. release-readiness is treated as an optional Phase-4 Stage-04 extension, not a separate lifecycle phase and not production authorization

Remediation routing rule:

- P4 evidence-consumption defect -> fix P4 and rerun P4
- Phase-3 mainline evidence exists but lacks full targeted SQL / contract / scenario / replay evidence -> return to P3 with `missing-phase3-full-targeted-evidence`
- missing Phase-3 evidence -> return to P3 for evidence generation / runtime proof
- implementation violates the accepted Phase-2 contract -> return to P3 for implementation remediation
- Phase-2 contract or design is not valid enough to validate honestly -> return to P2
- Phase-1 / Phase-2 truth gap forces validation to invent product or design truth -> return upstream to the responsible phase
- UI / visual / manual-review evidence is absent but not backend-functional blocking -> keep it `review-bound`, not `return`

Every `return` must carry evidence references and the minimum rerun boundary. Do not make Phase-4 outputs silently depend on human memory of why a closure failed.

Agent-led Review routing for v1.3.1:

- classify findings with Chinese human-facing labels and stable keys: `源头事实缺口` (`source-truth-gap`), `产品/规格缺口` (`product-spec-gap`), `架构缺口` (`architecture-gap`), `实现修补` (`implementation-patch`), `证据缺口` (`evidence-gap`), or `延期/拒绝` (`defer-reject`)
- route source-truth and product/spec gaps to pre-P1 admission or P1; do not validate invented product truth
- route architecture gaps to P2; do not redesign contracts or topology inside P4
- route implementation patches and missing implementation/runtime/test evidence to P3
- route P4 evidence-consumption or closure-judgment defects to P4
- keep missing external production / owner-signoff / online UAT evidence outside default WFF authority unless supplied as external evidence
- include category, owning phase, evidence references, affected claim, required action, minimum rerun boundary, claim ceiling, and review-bound carryover in the routed finding

## Workflow / Agentic Boundary

Treat Phase-4 as:

> `workflow-dominant evidence closure + bounded agentic triage`

- workflow certainty is high for acceptance planning, evidence collection, closure states, and reliance-boundary reporting
- agentic scope is limited to defect triage, evidence interpretation, priority judgment, and targeted remediation routing when closure cannot be granted directly
- Phase-4 must not redesign product truth or architecture truth, and it must not wash missing evidence into an artificial pass
- Phase-4 must not mutate upstream artifacts to make the validation pass; concrete remediation remains owned by P1/P2/P3 according to the routed cause
- Phase-4 must not rerun or replace P3 integration suites by default; if P3 runtime evidence is missing or stale, route back to P3 with the minimum rerun boundary
- UI / visual / manual-review gaps stay explicit and review-bound when the required evidence surface cannot be truthfully closed
- the optional release-readiness extension remains subordinate to Stage-03 closure and must not overtake the core acceptance mainline

## v1.3.1 Phase Review Breakpoint

At official Phase-4 Stage-03 completion, present a review opportunity before treating testing-validation closure as a downstream reliance point or before optionally entering Stage-04.

The breakpoint must surface the Phase-4 output root, primary artifacts, validation closure judgment, risk exposure, evidence sufficiency, claim ceiling, return routing, open `review-bound` items, recommended next step, and minimum rerun / return boundary.

Show human-facing review actions in Chinese: `批准`, `带保留项批准`, `要求修改`, `要求返回`, `提供干预输入`, or `明确跳过审核`. Structured records may also preserve stable protocol keys such as `approved` or `return-requested`. The breakpoint must not mutate supplied Phase-3 artifacts, repair upstream truth, or imply production approval, real owner sign-off, go-live, rollback readiness, monitoring handover, or production risk acceptance without explicit external evidence.

## v1.3.1 Strict-Proof And Claim-Ceiling Closure

Phase-4 closure must be evidence judgment and routing under a claim ceiling, not production approval or upstream repair.

Before treating testing-validation as closed, state evidence sufficiency, validation risk, formal claim ceiling, delivery boundary, review-bound carryover, and return routing. Acceptance catalog completion, output-contract pass, strict-proof report existence, or Stage-03 pass wording are support signals only. If a defect belongs to P1/P2/P3, route it with evidence and a minimum rerun boundary; if external production / owner-signoff / online UAT evidence is missing, keep that outside default WFF authority unless supplied as external evidence.

## v1.3.4 Cross-Phase Pattern Extension

When the active release line is `v1.3.4`, P4 may use the proven slimming/clarity patterns only inside the read-only validation and routing boundary.

P4 remains read-only validation and routing. It must not implement software, rewrite P1/P2/P3 artifacts, repair upstream generated packages, approve production release, or create owner sign-off.

P4 protected surfaces must remain root-visible:

- claim ceiling;
- remediation routing;
- strict-proof judgment;
- delivery gate;
- handoff boundary;
- phase verdict, scorecard, and acceptance matrix.

P4 output-contract reports are contract evidence, but they must be resolver-visible without increasing the must-read root surface: keep `phase4-output-contract-report.json` under `.phase4-contract/` and `phase4-output-contract-report.md` under `.phase4-review/`.

If Review finds a validation defect, do not convert Review findings into upstream repair inside P4. Emit or refresh a routed finding with owning phase, evidence references, affected claim, minimum rerun boundary, and claim ceiling.

For slimming, P4 may profile review/contract sidecars when their resolver path remains stable. Do not move `phase4-delivery-gate.json`, `phase4-quality-check.json`, `phase4-run-metadata.json`, phase verdict, scorecard, or acceptance matrix out of root visibility. Do not add output-contract reports back to root merely for discoverability.

## v1.3.1 Runtime References

Use these release-facing references when applying the v1.3.1 Phase-4 control model:

- `docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
- `docs/governance/v1.3-product-flow-control-boundary-v0.1.zh-CN.md`
- `docs/governance/v1.3-autopilot-strict-proof-vocabulary-v0.1.md`
- `docs/governance/v1.3-autopilot-strict-proof-vocabulary-v0.1.zh-CN.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.md`
- `docs/governance/v1.3-phase-review-breakpoint-contract-v0.1.zh-CN.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.md`
- `docs/governance/v1.3-stage-judgment-lens-v0.1.zh-CN.md`
- `docs/governance/v1.3-script-gate-authority-classification-v0.1.md`
- `docs/governance/v1.3-script-gate-authority-classification-v0.1.zh-CN.md`
- `docs/phases/phase-4/p4-strict-proof-gate-and-claim-ceiling-v0.1.md`
- `docs/phases/phase-4/p4-strict-proof-gate-and-claim-ceiling-v0.1.zh-CN.md`

## Release Validation Rule

When validating the released Phase-4 skill itself, use an isolated workspace/session with only the release bundle loaded.
Do not rely on repo-local `AGENTS.md`, authoring-repo defaults, or incidental workspace state to fill missing runtime/testing rules.
For the official retained `GEO + PetClinic` release verification flow, prefer `scripts/release/run_release_dual_case_eval.py` from the built release pack/bundle instead of running directly inside the authoring repo.

## Required Inputs

Read first:

- `docs/phases/phase-4/phase-4-skill-architecture-design-v0.1.md`
- `docs/phases/phase-4/phase-4-output-contract-v0.1.md`
- `reference-packages/phase4-validation-closure/README.md`
- `templates/testing-validation-planning-package.md`
- `templates/acceptance-checklist.md`
- `templates/test-coverage-explanation.md`
- `templates/test-entry-exit-gate-checklist.md`
- `templates/test-execution-control-template.md`
- the case Phase-3 root

## Execution Sequence

1. Run Stage-01 planning from the frozen Phase-3 root.
2. Build the acceptance catalog, contract registry, coverage rationale, gate checklist, and execution-control artifact.
   Also pull Phase-2 decision posture from the inherited `phase2_root` when available.
   Identity / tenant / key-management decisions should map to explicit negative-path acceptance rather than only general happy-path coverage.
3. Run Stage-02 against real inherited evidence:
   - worker-run test reports
   - Phase-3 mainline backend verification reports
   - Phase-3 `full-targeted-tests` reports when mainline strict-runtime evidence is expected
   - Phase-3 verification ledger
   - Phase-3 delivery gate / code-review / mock-dependency runtime truth artifacts
   - runtime smoke and started-service smoke reports when present
   - frontend packet inputs
   - route files
   - optional external screenshot/video/manual artifacts
   - optional human sign-off manifest
4. Run Stage-03 closure judgment.
5. Validate the S1-S3 output contract and keep `phase4-output-contract-report.json` / `phase4-output-contract-report.md` resolver-visible under `.phase4-contract/` and `.phase4-review/`.
6. Stop at Stage-03 unless a release profile explicitly asks for the optional Stage-04 extension.
   Do not collapse Stage-03 judgment into release-ready by default.
7. When Stage-04 is explicitly requested, run it through the Phase-4 runner with `--enable-stage4`.
   Without an explicit release sign-off / risk-acceptance manifest, Stage-04 may package development / pre-production `go-with-conditions`, but it must not claim final production `go`, real owner approval, or production risk acceptance.

## Official Scripts

Use these first:

- `scripts/phase4/phase4_stage1_planning.py`
- `scripts/phase4/phase4_stage2_execution.py`
- `scripts/phase4/phase4_stage3_closure.py`
- `scripts/phase4/run_phase4_first_version.py`

For the first official fresh run, prefer:

- `scripts/phase4/run_phase4_first_version.py`

For optional release-readiness packaging, use the same runner with:

- `--enable-stage4`

Stage-04 artifacts are validated separately through `stage4-release-readiness-contract-report.json` and `stage4-release-readiness-contract-report.md`.

## Completion Standard

Phase-4 is complete only when:

- a Stage-01 acceptance model exists
- Stage-02 records actual per-item outcomes
- Stage-03 produces `pass`, `pass-with-review-bound-items`, or `return`
- downstream reliance boundaries are explicit
- the S1-S3 output contract report is present and passing
- any `return` includes a remediation packet with return target, cause class, evidence references, required action, minimum rerun boundary, and downstream validation requirement
- and if a release profile was explicitly requested, Stage-04 release-readiness artifacts and their contract report are added on top rather than implied by Stage-03

Phase-4 S1-S3 output-contract validation proves testing-validation closure integrity within the available development / pre-production evidence boundary; it does not approve production release or create final handoff packaging.

Do not present Phase-4 as complete if UI/visual gaps were silently omitted.
