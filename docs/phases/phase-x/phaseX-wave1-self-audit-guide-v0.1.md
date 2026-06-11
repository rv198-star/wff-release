# PhaseX Wave-1 Self-Audit Guide (v0.1)

## Purpose

This is the lightweight self-audit surface for the current PhaseX Wave-1 implementation.

It exists to answer one question before external review:

> does this PhaseX case look like a real brownfield/refactor package, or only like a scaffold plus generic technical-debt prose?

## Baseline Gate

Run:

```bash
python3 scripts/phasex/validate_phasex_case.py --output-dir <case-phasex-root>
```

Interpretation:

- `scaffold-only`: case root exists, but outputs were not authored yet
- `authored-invalid`: authored text exists, but mandatory Wave-1 content is still missing
- `authored-valid`: minimum profile-specific structure is present

`authored-valid` is the minimum entry ticket for human review.

## Reviewer Questions

### All profiles

- Is current-state truth clearly separated from recommendation?
- Are unknowns explicitly preserved rather than flattened into certainty?
- Does the chosen profile actually fit the case?
- Does `wff-x-scan-code-baseline` explicitly record `third_party_dependency_scan` as `none-detected`, `detected`, or `uncertain`?
- Does `wff-x-scan-code-baseline` include a `codebase_truth_packet` with observed code evidence, Agentic inference, runnability evidence, explicit unknowns, and downstream implications?
- Does the artifact show code evidence -> Agentic judgment -> route or protection consequence, or only table completion?
- Are claim ceilings explicit where commands, tests, production facts, or ownership evidence are missing?

### `technical-refactor`

- Is the behavior-preservation boundary explicit?
- Is the case truly refactor, not mixed feature+refactor disguised as cleanup?
- Are refactor candidates concrete enough to drive safety-net planning?
- Is the safety-net plan fast enough to support small-step change?
- If the change span is long-running, is Branch by Abstraction or an equivalent migration seam considered?
- Does `wff-x-scan-tech-health` include `brownfield_health_judgment`, `risk_to_action_map`, and `evidence_backed_score_rationale` so scorecards do not replace judgment?
- Does `wff-x-plan-test-protection` include `safety_net_strategy` and `go_no_go_protection_decision` tied to the highest-risk brownfield behavior?

### `target-driver`

- Is the bounded change point explicit?
- Does the constrained re-entry summary preserve `affected_modules`, `impacted_surfaces`, `acceptance_criteria`, and `recommended_route`?
- Are `brownfield_non_goals` explicit enough to stop scope re-expansion?
- If external integration is touched, is `third-party-dependency-manifest` carried forward with change type / compatibility hints?
- Are compatibility constraints concrete enough for downstream Phase-1 or Phase-3 consumption?
- Is the downstream route honest, or is the package pushing ambiguity downstream?
- Does `wff-x-intake-target-driver` include a `brownfield_handoff_packet` with separate Phase-1 notes, Phase-3 notes, compatibility claim ceiling, and route decision rationale?

## Current Review Boundary

Wave-1 currently validates:

- profile fit
- method-backbone presence
- mandatory authored sections
- constrained re-entry field presence for `target-driver`
- deprecated third-party field names are rejected in `wff-x-intake-target-driver`
- refactor-specific guardrails for `technical-refactor`
- explicit Wave-1 gate expectations such as `PXG-04-*`, `PXG-06-*`, and `PXG-07-*`
- v1.3.10 reviewable Agentic brownfield surfaces:
  - `codebase_truth_packet`
  - `risk_to_action_map`
  - `safety_net_strategy`
  - `go_no_go_protection_decision`
  - `brownfield_handoff_packet`

Wave-1 does not yet deeply validate:

- semantic quality of each refactor candidate
- correctness of smell interpretation
- realism of the safety-net execution cost
- cross-case generalization

## One-Line Summary

Use Wave-1 self-audit to block obvious thin-pass cases before sending them to human review; do not confuse that with a full quality review.
