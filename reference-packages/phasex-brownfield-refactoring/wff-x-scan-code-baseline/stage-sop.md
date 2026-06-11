# wff-x-scan-code-baseline SOP — scan-code-baseline

## 1. Positioning

- goal: capture the current technical shape of the existing system
- upstream: accessible codebase
- downstream: P2 architecture constraint consumption, `wff-x-scan-tech-health`, `wff-x-plan-test-protection`, `wff-x-intake-target-driver`, or direct human decision

## 2. Start Conditions

- required: repository or code snapshot is available
- optional but helpful: dependency manifests, startup instructions, deployment material
- blocked: source is inaccessible or too partial to identify even the main runtime surfaces

## 3. Standard Execution Steps

1. identify repository type and primary language/runtime stack
2. list visible entrypoints and execution surfaces
3. group major directories/modules and summarize responsibilities
4. capture dependency and framework signals
5. scan for third-party SDK / API / IdP / SaaS dependency hints and record a preliminary manifest or explicit uncertainty
6. record refactor signals or smell hints when they are directly observable
7. record runnability posture and major blockers
8. inspect file paths, entrypoints, config, tests, and run commands before drawing brownfield conclusions
9. separate observed code evidence from inferred brownfield semantics
10. record explicit unknowns when repository evidence does not prove a claim
11. create a P2 consumption packet for architecture constraints and boundary review
12. create P3 seed material only as candidate hotspots or affected slices, not ActionCards
13. explain which codebase truths affect health assessment, target-driver handoff, or safety-net planning
14. hand off the baseline for scoring, safety-net planning, bounded change packaging, or P2 consumption

## 4. Process Checkpoints

- primary runtime and framework are named
- entrypoint list is not empty
- major module groups are present
- at least one outward surface inventory exists when detectable
- third-party dependency scan is explicit as `none-detected`, `detected`, or `uncertain`
- `technical-refactor` runs capture refactor signals as hints, not verdicts
- `codebase_truth_packet` is present and separates observed evidence, inference, runnability evidence, unknowns, and downstream implications
- `p2_consumption_packet` is present
- `p3_seed_material` is present or explicitly empty
- uncertainty is explicit

## 5. Output Rules

- prefer machine-readable tables for surfaces and modules
- label low-confidence inferences explicitly
- keep current-state truth separate from recommendations
- do not turn directory names, route names, or package names into business truth without evidence
- do not generate P3 ActionCards in `wff-x-scan-code-baseline`

## 6. Stage Acceptance

- another engineer can understand the current system shape without rereading the full repository first
- PhaseX has enough baseline truth to decide whether to assess, protect, or decompose change next
- P2 can consume architecture constraints without treating P3 seed material as implementation truth
