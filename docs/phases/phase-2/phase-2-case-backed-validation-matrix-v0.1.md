# Phase-2 Case-Backed Validation Matrix（v0.1）

## Purpose

This file records the current **case-backed validation surface** for Phase-2 so the family is not judged only by one self-test lane or one historical trial memory.

It does not claim that all cases are equally deep.
It defines the current repeatable validation baseline and the next case-expansion target.

## Case Matrix

| case | case_type | current_location | Phase-2 evidence status | main value to Phase-2 |
|---|---|---|---|---|
| `geo-generative-engine-optimization-mainline` | real local case | `tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/` | Stage-01..04 outputs + execution report present | brownfield boundary control, strong constraints, public-boundary-only freeze, implementation handoff realism |
| `restaurant-owner-ai-reply-assistant` | historical real case | `docs/plans/2026-03-17-phase-1-to-4-end-to-end-trial-findings.md` + `docs/phases/phase-2/phase-2-realizability-architecture-review-rule-v0.1.md` + `docs/phases/phase-2/phase-2-external-dependency-feasibility-rule-v0.1.md` | historical Phase-2 evidence retained through review/bridge docs; external raw bundle may no longer be local | external dependency realism, substitute boundary honesty, realization-path calibration |
| `ai-meeting-assistant` | structured packaged self-test case | `reference-packages/phase2-design-architecture/stage-01-architecture-definition-and-boundary-setting/self-test-dry-run-output.md` and downstream Stage-02..04 self-test outputs | full packaged dry-run coverage in authored family | package-shape integrity, field completeness, handoff continuity, verification shape |

## Coverage Judgment

### What is now covered
- at least one real local Phase-2 case with full four-stage outputs
- at least one historical real case that already forced rule repair in realizability / dependency handling
- one packaged self-test lane that keeps the authored family regression-resistant

### What this still does not mean
- three equally deep real business cases are permanently preserved in-repo
- every external bundle is still locally present
- Phase-2 can stop adding new cases

## Interim Handling When No Second Local Real Case Exists

If the repo does not currently contain a second fully preserved local Phase-2 case directory, use the following rule:

- do **not** fabricate a fake second case just to satisfy the maturity narrative
- keep the current local full-trial lane anchored on the preserved GEO case
- treat `restaurant-owner-ai-reply-assistant` as a **historical corrective lane**, not as a second local full-trial lane
- keep the packaged `ai-meeting-assistant` outputs as a regression lane, not as business-domain generalization proof

Therefore:

- Phase-2 may continue improving its `SKILL`, gates, and portfolio evidence without pausing
- maturity claims must explicitly distinguish:
  - `structural portfolio pass`
  - `historical corrective coverage`
  - `second local real-case proof still missing`

This means a missing second local case is a **tracked maturity gap**, not a reason to weaken the honesty of the evidence model.

## Immediate Rule

From this point onward, claims about Phase-2 maturity should reference **all three validation lanes together**:
- real local execution lane
- historical real-case corrective lane
- packaged self-test regression lane

Do not treat one lane alone as the full maturity proof.

## Next Expansion Target

The next meaningful validation upgrade is:
- add one more fully preserved real local Phase-2 case directory under `tmp/local-artifacts/<case-name>/phase-2/`
- keep the execution report, traceability report, and Engineering Spec Pack convergence output together
- once that case exists, update portfolio evidence so `distinct_case_family_proof` and `distinct_phase1_prd_proof` can move from `fail` to `pass`
