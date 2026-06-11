# Phase-2 First-Pass Generation Workflow v1.0

## Purpose

This workflow closes the gap between:

- a valid Phase-1 handoff
- the official Phase-2 Stage family
- a fresh Phase-2 case that can later be wrapped by `scripts/phase2/run_phase2_full_trial.py`

It exists to prevent "rename v5 to v6 and patch the prose" from being treated as a valid skill-first Phase-2 run.

## Canonical Mainline Surface

For the default official Phase-2 mainline, treat:

```bash
python3 scripts/phase2/run_phase2_first_version.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <vN> \
  --run-wrapper
```

as the canonical one-shot Phase-2 mainline surface.

Interpretation:

- `run_phase2_first_version.py`
  - official fresh-run entry
- `run_phase2_full_trial.py`
  - closure wrapper over authored Stage outputs
  - still valid when manual/remediation-first authoring is intentional

## Core Rule

Every new Phase-2 version must start as a fresh case root.

That means:

- scaffold a new Phase-2 case directory first
- author Stage-01..04 into that new directory
- run the official wrapper only after those fresh Stage outputs exist

Do not treat a previous Phase-2 case directory as the baseline document set for the new version.

## Workflow / Context Boundary

Treat the official Phase-2 mainline as:

- workflow-fixed for fresh-root generation, Stage order, trace absorption, wrapper closure, and delivery packaging
- bounded-agentic for architecture trade-offs, decomposition choices, quality-attribute reasoning, and dependency realism

Do not use Phase-2 as a second business-discovery phase.

If the missing truth is really:

- user world
- business model
- core product scenario
- upstream acceptance boundary

then return upstream instead of inventing it inside Phase-2.

No open-ended `creative` expansion mode is part of the default Phase-2 mainline.
Use only targeted loops tied to a weak design artifact or an unresolved trade-off.

## Allowed Inputs

Fresh first-pass generation may use:

- Phase-1 PRD main document
- Phase-1 prototype spec
- Phase-1 execution report
- official Phase-2 stage package assets in `reference-packages/phase2-design-architecture/`

Within the Phase-1 PRD, the `Phase-2 Design Input Contract` is the mandatory machine-readable baseline.
Fresh first-pass authoring should begin from those contract rows, not from unstructured PRD prose.

An earlier Phase-2 case may be consulted only as a sidecar comparison source.
If that happens:

- record the sidecar reference explicitly in the new authored outputs
- restate reused claims from fresh evidence instead of copying them forward as inherited truth

## Scaffold Step

Use:

```bash
python3 scripts/phase2/scaffold_phase2_case.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <vN>
```

If the target version must be a **pure direct baseline** derived from the Phase-1 PRD main document only, use:

```bash
python3 scripts/phase2/scaffold_phase2_case.py \
  --phase1-prd <phase1-prd.md> \
  --output-dir <case-phase2-root> \
  --version <vN> \
  --pure-prd-direct
```

The scaffold creates:

- `phase-2-first-pass-generation-manifest.md`
- Stage-01 stub
- Stage-02 stub
- Stage-03 stub
- Stage-04 stub

Each stub declares that it is a fresh first-pass target and forbids copying prior Phase-2 prose into the new output.
When `--pure-prd-direct` is used, the scaffold also records that:

- the Phase-1 PRD main document is the only authority input
- previous Phase-2 outputs and supplemental Phase-1 docs are not allowed as baseline sources
- later fixes must move to a follow-up version such as `v8-r1`, not overwrite the pure baseline

## Audit Step

Use the fresh-case audit to distinguish:

- scaffold-only case roots
- authored first-pass case roots
- wrapper-closed case roots

```bash
python3 scripts/phase2/validate_fresh_first_pass_case.py \
  --output-dir <case-phase2-root>
```

Interpretation:

- `scaffold-only`: stubs still remain; do not run the wrapper yet
- `authored-first-pass`: Stage-01..04 are no longer scaffold targets; wrapper may run
- `wrapper-closed`: first-pass authoring exists and wrapper outputs are already present

The official wrapper now reruns this audit automatically:

- it emits `phase-2-first-pass-audit.json`
- it blocks immediately if Stage-01..04 are still scaffold targets
- it may continue on legacy/remediation case roots, but those runs do not count as clean fresh first-pass evidence

## Authoring Sequence

1. Convert the PRD's `Phase-2 Design Input Contract` into a top-down absorption plan.
2. Stage-01: freeze boundary, constraints, capability map, architecture decisions, and first-pass security/capacity posture.
3. Stage-02: derive domain/module/service/event/entity structure from Stage-01 while preserving the object and naming surfaces needed by downstream contract rows.
4. Stage-03: derive storage/interface/schema/scenario/tech-selection outputs from Stage-02, explicitly bind Phase-1 trace units via `upstream_trace_ids`, keep schema migration posture visible when rollout sequencing matters, and when multi-candidate tradeoff evaluation is active, close the full tradeoff bundle (`matrix -> baseline insufficiency -> optimum candidate -> key tradeoff decisions`) instead of stopping at the comparison table.
5. Stage-04: converge the design into delivery slices, verification, readiness, Engineering Spec Pack input, auth/vendor/token lifecycle posture, and onboarding summary while preserving the upstream trace chain into replay and RBI rows.
6. For the canonical one-shot mainline, use `scripts/phase2/run_phase2_first_version.py --run-wrapper`.
7. Run `scripts/phase2/run_phase2_full_trial.py` directly only when Stage-01..04 are already authored and the current task is explicit closure / remediation.
8. Let the runner classify the case complexity from the Phase-1 PRD (`auto`) unless there is a documented reason to override; if override is necessary, carry the justification into the execution report.

## Wrapper Rule

`scripts/phase2/run_phase2_full_trial.py` is the official closure wrapper over already-authored Stage outputs.

It is not the canonical fresh-run mainline entry.
The canonical mainline entry is `scripts/phase2/run_phase2_first_version.py --run-wrapper`.

It is not the first-pass content generator.
Its job is to:

- re-audit fresh-first-pass case-root hygiene and emit `phase-2-first-pass-audit.json`
- block scaffold-only case roots before closure artifacts are generated
- bind and validate traceability
- run the quality / regression / consistency checks
- emit `phase-2-execution-report.md`
- emit `engineering-spec-pack.md`
- emit `phase-3-implementation-entry.md`

## Audit Rule

If a generated Phase-2 version claims to be "skill-first" or "fresh first-pass":

- the Stage files must live in a fresh case directory
- the manifest must exist
- the authored Stage outputs must not merely be edited copies of the previous version

For the default official mainline, the case should be generated and closed through `scripts/phase2/run_phase2_first_version.py --run-wrapper`.

If those conditions are not met, treat the run as remediation on an existing Phase-2 case, not as a fresh first-pass generation.

If a generated version additionally claims to be `pure-prd-direct`:

- the manifest should explicitly record that mode
- the Stage stubs / outputs should preserve the direct-baseline posture
- any post-review optimization should produce a new rerun/follow-up version label instead of silently rewriting the pure baseline
