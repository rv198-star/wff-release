# wff-x-scan-code-baseline Skill Contract — scan-code-baseline

## 1. Skill Goal

- Extract the current codebase shape into a structured brownfield baseline.
- Make existing entrypoints, modules, dependency seams, technical stack, and runnability posture explicit before change work begins.
- In the Wave-2 baseline lane, align the authoritative baseline output primarily to P2; provide only limited P3 seed material, not ActionCards or implementation truth.

## 2. Inputs

- required:
  - accessible repository or code snapshot
  - build/runtime config when present
  - package manager or dependency manifests
- optional:
  - deployment scripts
  - architecture docs
  - API docs
  - incident notes or ops runbooks

## 2.1 Cannot Infer

- real module ownership from directory names alone
- runtime health from static code layout alone
- true production topology when only local code is visible
- business criticality unless source evidence or caller statement exists

## 2.2 Must Validate Before Exit

- entrypoints are listed
- major module or bounded directory groups are named
- primary stack/runtime choices are stated
- a `codebase_truth_packet` separates observed code evidence, inferred brownfield semantics, runnability evidence, explicit unknowns, and downstream truth implications
- P2-facing architecture constraints are explicit
- P3-facing material is marked as seed-only
- outward surfaces are enumerated where visible:
  - routes / API handlers
  - jobs / workers
  - CLI commands
  - scheduled tasks
- runnability posture is explicit:
  - runnable
  - partially-runnable
  - blocked
- for `technical-refactor` profile, observable refactor signals are captured without overstating redesign certainty

## 3. Outputs

- codebase baseline summary
- codebase truth packet:
  - observed code evidence
  - inferred brownfield semantics
  - runnability evidence
  - explicit unknowns
  - downstream truth implications
- module / directory map
- dependency hotspot list
- surface inventory
- runnability precheck
- third-party dependency scan
- P2 consumption packet
- P3 seed material
- known uncertainty register

## 4. Gate Conditions

- `PXG-01-1`: entrypoints, module map, and runtime stack inventory are all present
- `PXG-01-2`: runnability state is explicit as `runnable`, `partially-runnable`, or `blocked`
- `PXG-01-3`: major blind spots are recorded in the uncertainty register; third-party dependency scan is explicit as `none-detected`, `detected`, or `uncertain`, and `technical-refactor` runs also include refactor signals
- `PXG-01-4`: the truth packet makes code evidence, Agentic inference, and downstream implications reviewable without claiming unsupported full-system certainty
- `PXG-01-5`: P2-consumable architecture constraints are separated from non-authoritative P3 seed material

## 5. Acceptance Criteria

- a follow-on PhaseX or P2 step does not need to rediscover the same entrypoints and module boundaries from scratch
- the baseline clearly separates observed facts from inferred structure
- downstream consumers can tell which brownfield truths are observed, which are inferred, and which remain unknown
- external dependency hints are preserved early instead of being rediscovered manually in downstream phases
- P3 receives candidate slices or hotspots only as seed material; formal ActionCards still belong to P3
- missing visibility is recorded as uncertainty, not silently flattened into certainty

## 6. Boundaries

- no refactoring plan here
- no target architecture here
- no fake certainty about production behavior
- no requirement rewriting unless the user asked for bounded change decomposition
- no turning smell hints into architectural certainty without later validation

## 7. Flow Rules

- typical downstream:
  - P2 for architecture constraints and boundary review
  - `wff-x-scan-tech-health` for technical risk scoring
  - `wff-x-plan-test-protection` for safety-net planning
  - `wff-x-intake-target-driver` for bounded change packaging
