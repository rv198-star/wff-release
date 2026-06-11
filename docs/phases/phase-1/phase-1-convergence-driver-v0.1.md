# Phase-1 Convergence Driver（v0.1）

## 1. Purpose

This document defines the missing project-level control artifact needed to turn the existing Phase-1 Stage Skill family from a **manual stage runtime pack set** into a **coherent Phase-1 execution system**.

The driver is responsible for one business-case run from:

- one Phase-1 input package / PRD-like source document
- through Stage-01 / Stage-02a / Stage-02b / Stage-03 / Stage-04 execution
- into one audit-rich assembled PRD draft
- then into one converged PRD main document plus convergence evidence memo
- plus one explicit execution report

It is a **runtime control artifact**, not a replacement for the four existing Stage Skills.

---

## 2. Why it is needed

Current repo assets already provide:

- Stage contracts
- Stage SOPs
- output templates
- gate / refusal logic
- handoff rules
- Unified Product Pack convergence definition
- unresolved-truth handling rules

However, current Phase-1 usage still relies on:

> **manual stage-by-stage runtime-pack execution**

This leaves an important gap:

- no single control surface decides which stage should run next
- no standardized execution report summarizes what passed, what is partial, and what is still missing
- no shared verdict layer translates stage-level gate semantics into a project-level review output
- no project-level runtime loop repeatedly routes missing or weak outputs back into clarification / review / evidence collection

This gap explains why current real-case outputs can look structurally correct but still feel shallow.

---

## 3. Non-goal

The Phase-1 Convergence Driver is **not**:

- a full live orchestrator platform
- a registry/install/distribution mechanism
- a replacement for Stage-01 / 02 / 03 / 04 runtime packs
- a promise that all Phase-1 runs will end in `PASS`

Its job is narrower and more important:

> **run one Phase-1 case honestly, preserve uncertainty honestly, and produce a convergence result plus explicit review report.**

---

## 4. Inputs

### Required
- one Phase-1 input package, such as:
  - product requirement draft
  - opportunity brief
  - project intake note
  - existing PRD-equivalent source document

### Optional
- external evidence notes
- stakeholder notes
- market notes
- competitor notes
- previous review comments

### Input boundary
The driver must not assume:

- complete truth
- validated demand
- complete evidence
- complete constraints

It must classify missing truth using the project’s unresolved-truth handling rules.

---

## 5. Core output set

One Phase-1 execution run should produce at minimum:

1. Stage-01 output
2. Stage-02a output (requirements-structural-analysis)
3. Stage-02b output (requirements-specification-deepening)
4. Stage-03 output
5. Stage-04 output
6. Audit-rich assembled PRD draft, root-visible or retained under `.phase1-evidence/` as intermediate convergence evidence
7. Converged PRD main document
8. Converged PRD zh-CN audit mirror for human review
9. PRD convergence evidence memo
10. Phase-1 execution report

The execution report is mandatory.

Note: the Unified Product Pack concept is preserved but converges **into** the PRD main document rather than existing as a separate lightweight summary. See `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md` for the target document structure.

### 5.1 Delivery Profile (Required)

Each run must explicitly declare one delivery profile:

- `review-bound-starter-pack`:
  - suitable for Phase-1 review and design/architecture exploration kickoff
  - allows review-bound uncertainty with explicit carryover
- `implementation-ready-prd`:
  - stricter profile for design/architecture execution kickoff
  - requires executable process/IA/flow specification depth in the PRD
  - requires all executable gates (including executability and artifact consistency) to pass

If no delivery profile is declared, the run is invalid.

---

## 6. Driver state model

The driver sits above the existing Phase-1 intake state machine.

### Runtime states
- `R0 Input Registered`
- `R1 Stage-01 Running`
- `R2 Stage-01 Review`
- `R3a Stage-02a Running`
- `R3b Stage-02a Review`
- `R4a Stage-02b Running`
- `R4b Stage-02b Review`
- `R5 Stage-03 Running`
- `R6 Stage-03 Review`
- `R7 Stage-04 Running`
- `R8 Stage-04 Review`
- `R9 PRD Assembly (audit-rich)`
- `R9a PRD Convergence`
- `R9b Executable Gate Evaluation`
- `R9c Remediation Loop Decision`
- `R10 Admission Review Ready`
- `R11 Return / Remediation Needed`
- `R12 Blocked`

### Rule
The driver may not silently jump from stage execution to downstream progression.

After every stage it must perform:

1. output existence check
2. required-field check
3. unresolved-truth classification
4. downstream-consumability judgment
5. execution-report update

---

## 6.5 PRD Assembly + Convergence Rule

After all stage outputs are produced and reviewed, the driver first assembles an **audit-rich PRD draft** following `docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`, and then converges it into the downstream-consumable PRD main document.

This is not a copy-paste operation. It is a **synthesis** that:
- draws content from the correct stage outputs
- consolidates reasoning evidence into a unified decision rationale section
- synthesizes an executive summary from cross-stage conclusions
- declares handoff state and source artifacts

It is also a **deep-compilation step**, not merely an assembly step.
If the audit-rich PRD remains mostly a section-by-section mirror of stage outputs, the driver must treat it as insufficiently converged.

### Convergence preservation rules

The convergence step may compress runtime residue, but it must **not** compress away machine-usable delivery structure.

- within `§5 Strategic Context`, `Competitive Landscape Summary` must remain explicit even when exact competitor names or prices are still review-bound
- within `§12 MVP Definition & Scope`, `Acceptance Criteria` must remain a structured `Given / When / Then` artifact with visible boundary coverage; do not downgrade it to prose-only bullets
- within `§14 User Stories, Use Cases, and Requirements`, `Epic Decomposition` and `Story Quality Gate (INVEST)` must remain dedicated sections, not be absorbed into generic requirement prose
- within `§13 Validation Strategy & Current Conclusion`, `Pricing Validation Design` must remain explicit even when pricing evidence is incomplete
- if convergence would remove one of the above blocks, the driver must treat that as a regression and fail the convergence candidate rather than silently emitting a thinner PRD

### Runtime layering rule

The driver must keep three distinct artifacts:

1. `assembled_prd_draft`
   - audit-rich
   - may retain runtime/deep-loop residue that helps intermediate inspection
   - may be stored under `.phase1-evidence/` when the converged PRD, zh-CN audit mirror, and convergence evidence memo remain root-visible
2. `converged_prd_main_document`
   - final downstream-facing PRD
   - should preserve product/design/architecture-consumable depth
   - should not inline large runtime-only material-ingestion traces
3. `prd_convergence_evidence_memo`
   - carries externalized delta ledger and runtime trace residue
   - preserves auditability without polluting the final PRD

Suggested script chain:

```bash
python3 scripts/phase1/phase1_assemble_prd.py ...
python3 scripts/phase1/phase1_converge_prd.py \
  --assembled-prd <prd-main-document-assembled.md> \
  --output <prd-main-document.md> \
  --evidence-output <prd-main-document-convergence-evidence.md>
python3 scripts/phase1/phase1_localize_prd_zh.py \
  --canonical-prd <prd-main-document.md> \
  --output <prd-main-document.zh-CN.md>
```

Acceptance-layer rule:

- the converged PRD must preserve a dedicated warning / pending external confirmation area
- it must allow the artifact to score high on document maturity without pretending business completeness is equally high
- it must make safe current use and stronger-commitment blockers visible in the PRD body, not only in the execution report
- when human review is in scope, emit a `*.zh-CN.md` PRD audit mirror whose key domain/state terminology stays bilingual

### Source mapping

| PRD Section | Primary Source | If Absent |
|---|---|---|
| §1 Executive Summary | Synthesize: Stage-01 problem + Stage-02a direction + Stage-03 MVP + Stage-04 decision | Required |
| §2 Problem Statement | Stage-01: `final_problem_statement`, evidence status | Required |
| §3 Target Users & Key Roles | Stage-01: `target_user_groups` + Stage-02a: `persona_scenario_set` | Required |
| §4 Stakeholder Analysis | Stage-02a: `stakeholder_analysis` (profiles + adoption chain) | WARNING |
| §5 Strategic Context | Stage-01: `business_opportunity` + `primary_need_framing_choice` + explicit alternative / competitor pressure; must preserve `Competitive Landscape Summary` | Required |
| §6 Product Direction Overview | Stage-01: `need_framing` + Stage-02a: `value_loop` | Required |
| §7 Business Scenarios | Stage-02a: `key_business_scenarios` (at least 3 with scenario-challenge-solution) | WARNING |
| §8 Requirements Structure | Stage-02a: `panorama` + `backbone_flow` + `key_constraints` + `priority_split` | Required |
| §9 NFR / Quality Requirements | Stage-02b: `nfr_quality_requirements` + quality-scenario tables | Required |
| §10 Domain Model | Stage-02b: `domain_model_direction` + ER diagram + data characteristics | Required |
| §11 Information Architecture Direction | Stage-02b: `information_architecture_direction` | Required |
| §12 MVP Definition & Scope | Stage-03: `complete_experience_loop` + `minimum_viable_experience_loop` + slices + `nfr_slice_impact` | Required |
| §13 Validation Strategy & Current Conclusion | Stage-04: targets + method + `validation_dimensions_covered` + evidence honesty + decision state + `Pricing Validation Design` | Required |
| §14 User Stories, Use Cases, and Requirements | Stage-01: `first_pass_user_case_or_user_story` + Stage-02a: key-path scenarios + Stage-03: epic / INVEST / acceptance structure that must remain machine-readable | Required |
| §15 Out of Scope | Stage-03: `deferred_items` + Stage-02a: `explicit_exclusions` | Required |
| §16 Dependencies, Risks, and Review-Bound Truth | All stages: `assumptions_to_validate` + `open_questions` + unresolved-truth classification | Required |
| §17 Key Decision Rationale Summary | Consolidated from each stage's Section 3.2 `why_this_not_that` | Required |
| §18 Handoff to Design / Architecture | Stage-04: `handoff_package` + NFR state from Stage-02b + domain model state from Stage-02b | Required |
| §19 Acceptance & Status | Execution report: `admission_recommendation` + maturity/confidence ledger + warning/pending-confirmation ledger | Required |
| §20 Source Artifacts | File references to all stage outputs + execution report | Required |

### 6.5.1 PRD Deep Compilation Loop

After the first assembled PRD draft exists, the driver must run a bounded deep-compilation loop before freeze and before converging the final PRD.

#### Loop states
- `P0 assembled-audit-rich`
  - all required sections exist, but runtime residue may still be inline
- `P1 deepening-round-1`
  - expand the most decision-critical thin sections first
- `P2 deepening-round-2`
  - strengthen cross-section coherence and downstream consumability
- `P3 deepening-round-3`
  - final synthesis tightening only; no broad re-exploration
- `P4 converged-candidate`
  - final PRD produced and ready for executable gates
- `P5 review-bound-freeze`
  - deep enough to hand off under explicit warning/review-bound semantics
- `P6 return-remediate`
  - a specific upstream stage artifact is too thin and must be improved before PRD freeze
- `P7 blocked`
  - the PRD cannot be responsibly deepened without inventing critical truth

#### Default loop limit
- one assembled draft + up to THREE deepening rounds + one convergence pass

#### Round trigger conditions
A PRD deepening round is justified only if at least one of the following is true:
1. one or more required PRD sections remain summary-only rather than consumable narrative
2. the product mechanism is still unclear across sections
3. user / workflow / object / slice logic is fragmented rather than synthesized
4. design or architecture would still need to infer core product logic not stated in the PRD
5. stage-local reasoning exists but has not yet been translated into main-document decisions
6. alternatives were compared in stage outputs but not yet reflected in the PRD
7. the assembled PRD materially compresses the high-value detail from the structured input or stage outputs without replacing it with denser synthesis

#### Allowed deepening focus
Each round may improve only:
- cross-section synthesis quality
- product mechanism articulation
- role / workflow / object linkage
- slice rationale clarity
- design / architecture consumability
- review-bound truth honesty and forbidden assumptions
- preservation and recompilation of high-value source detail

Not allowed:
- broad new ideation unrelated to existing stage outputs
- fake certainty upgrades
- style-only rewriting
- compression that removes high-value source detail without stronger replacement synthesis

#### Per-round evidence requirement
Each round must record:
- which PRD sections were deepened
- what consumer problem was improved (`product-review | design | architecture | handoff`)
- what method or stage reasoning was absorbed
- whether the PRD became more consumable without inventing new core truth
- why the PRD is now frozen / returned / blocked

### 6.5.2 Section Depth Rule

The PRD must not be accepted as "assembled" merely because all section headers are present.

A section is too shallow if it is primarily:
- a heading plus short bullet labels with no explanatory content
- a mirror of an upstream field name without synthesis
- a generic restatement that does not clarify decisions, trade-offs, or downstream meaning
- a compressed paraphrase that discards high-value business detail from upstream source material

Sections that are especially depth-sensitive and must be expanded beyond summary form:
- §2 Problem Statement
- §3 Target Users & Key Roles
- §6 Product Direction Overview
- §7 Business Scenarios
- §8 Requirements Structure
- §12 MVP Definition & Scope
- §13 Validation Strategy & Current Conclusion
- §18 Handoff to Design / Architecture

If any of these sections remains summary-only, the PRD main document assembled row in the execution report must not exceed `WARNING`.

### 6.5.2a Anti-Compression Preservation Rule

The PRD is not allowed to become a "shorter but cleaner" version of the input unless it demonstrably produces denser and more decision-useful synthesis.

When the structured input package already contains high-value detail, the driver must preserve and recompile that detail rather than silently compress it away.

Examples of high-value detail that must usually be preserved or recompiled:
- target segment differences and economic signals
- feature/capability clusters when they imply product module responsibility
- metric definitions and interpretation logic
- explicit in-scope / out-of-scope boundaries
- validation targets, thresholds, and decision conditions
- workflow steps and state transitions
- priority groupings (P0/P1/P2 or equivalent)
- page/module-level hints that materially affect design or architecture

Acceptable transformation:
- raw source detail is reorganized, merged, or re-expressed into a deeper, more consumable structure

Unacceptable transformation:
- raw source detail disappears and is replaced by thinner generalization

If high-value source detail is lost without stronger recompilation, the PRD depth / anti-summary row must not exceed `WARNING`.

### 6.5.3 Downstream Consumability Rule

The PRD assembly/convergence step must explicitly judge whether the document is strong enough for downstream use.

Minimum downstream-consumability questions:
- Can design derive the key workflow, primary screens/modules, and interaction priorities without inventing the main product loop?
- Can architecture derive the main domain objects, key dependencies, and first-wave system boundary assumptions without inventing the product mechanism?
- Can product review understand why this slice, not another one, was chosen?
- Can downstream tell which truths are review-bound and must not be silently promoted?
- Can downstream still see the high-value source detail that materially affects decisions, rather than only compressed abstractions?

If the answer to any question is "no", the driver must either run another deep-compilation round or return to the relevant stage output for remediation.

### 6.5.4 Executable Gate Hook

For runs where structured source input and PRD main document are both available as files, the driver should run the canonical executable mainline gates:

```bash
python3 scripts/phase1/phase1_stage_artifact_depth_gate.py \
  --source <structured-input.md> \
  --stage <stage-01-output.md> \
  --stage <stage-02a-output.md> \
  --stage <stage-02b-output.md> \
  --stage <stage-03-output.md> \
  --stage <stage-04-output.md>

python3 scripts/phase1/phase1_prd_quality_gate.py \
  --source <structured-input.md> \
  --prd <prd-main-document.md> \
  --require-non-shrinking

python3 scripts/phase1/phase1_prd_executability_gate.py \
  --prd <prd-main-document.md> \
  --profile <review-bound-starter-pack|implementation-ready-prd>

python3 scripts/phase1/run_phase1_convergence.py \
  --source <structured-input.md> \
  --report <phase-1-execution-report.md> \
  --prd-candidate <prd-main-document.md> \
  --max-rounds 1
```

Interpretation rule:
- canonical mainline gate surface is:
  - `stage_artifact_depth_gate`
  - `quality_gate`
  - `executability_gate`
  - `prd_mainline_gate_bundle`
- `prd_mainline_gate_bundle` internally covers:
  - `assembly_integrity_gate`
  - `analysis_delta_gate`
  - `section_scoring_gate`
  - `artifact_consistency_gate`
- all canonical gates `FINAL: PASS` -> convergence-depth/preservation/executability/consistency gate may proceed
- any canonical gate `FINAL: BLOCKED` -> PRD must return to deep-compilation/remediation before formal pass
- `phase1_stage_artifact_depth_gate.py` specifically blocks:
  - Stage-01/02a/02b/03/04 文档过薄（例如 1KB 级别摘要）
  - 阶段产物对 source 的覆盖比例过低
  - 阶段关键信号（用户边界/流程骨架/NFR/切片/验证）缺失
- within `prd_mainline_gate_bundle`, `phase1_prd_assembly_integrity_gate.py` specifically blocks:
  - source全文直接附录拼接
  - PRD 缺失 stage artifact 来源链
  - source 与 PRD 的超长镜像拷贝块

### 6.5.5 Executable Driver Command

For a full real-case run from source document to final artifact bundle, the preferred Phase-1 entrypoint is:

```bash
python3 scripts/phase1/run_phase1_full_trial.py \
  --source <structured-input.md> \
  --output-dir <trial-output-dir> \
  --version <trial-vN> \
  --profile <review-bound-starter-pack|implementation-ready-prd>
```

Use `scripts/phase1/run_phase1_convergence.py` directly only when a PRD candidate plus execution-report context already exists and you are evaluating/remediating that existing artifact set.

Driver surface rule:

- `scripts/phase1/run_phase1_full_trial.py`
  - official runtime entry for one complete Phase-1 mainline run
- `scripts/phase1/run_phase1_convergence.py`
  - convergence/remediation engine used inside the mainline and for explicit recheck of an existing artifact set
- `phase-1-execution-report.md`
  - must record these two surfaces separately; do not collapse them into one generic `driver` field

For direct gate/remediation runs, use:

```bash
python3 scripts/phase1/run_phase1_convergence.py \
  --source <structured-input.md> \
  --prd <prd-main-document.md> \
  --report <phase-1-execution-report.md> \
  --profile <review-bound-starter-pack|implementation-ready-prd>
```

Driver rule:
- official Phase-1 delivery is invalid if it skips full-trial orchestration and only hand-fills stage output templates
- if any gate fails, runtime state must move to `R11 Return / Remediation Needed` or `R12 Blocked`
- no human summary override may promote the run to formal pass while executable gates are blocked

### §1 Executive Summary synthesis rule

Combine in one paragraph:
- **target user**: from Stage-01 `target_user_groups` primary segment
- **core problem**: from Stage-01 `final_problem_statement`
- **proposed first-wave solution direction**: from Stage-02a `value_loop` + Stage-03 `first_slice`
- **expected product/business impact**: from Stage-04 `decision_state` + Stage-01 success signals

### §17 Decision Rationale assembly rule

For each stage that performed alternatives comparison, extract and summarize:

1. **User boundary choice** (Stage-01): chosen segment + why-this-not-that + deferred segments rationale
2. **Need framing choice** (Stage-01): chosen framing + why-this-framing-not-that
3. **Structure choice** (Stage-02a): chosen panorama + why-this-structure-not-that
4. **NFR priority rationale** (Stage-02b, if present): why these quality attributes are most critical
5. **Slice strategy rationale** (Stage-03): chosen slice + why-this-slice-not-that
6. **Validation method rationale** (Stage-04): chosen method + why-this-method-not-that

Each entry should state: the decision, what alternatives were considered, and the rationale for selection.

### §18 Handoff assembly rule

Assemble from:
- Stage-04 `handoff_package` (validation conclusion, revision recommendations, forbidden downstream assumptions)
- Stage-02b NFR state declaration: `present-with-quality-scenarios | present-identification-only | absent | deferred`
- Stage-02b domain model state declaration: `present-with-ER | absent | deferred`
- Handoff type: what kind of handoff this is (e.g., design-ready, architecture-ready, review-bound)

### §18 Handoff minimum depth rule

The PRD handoff section must not stop at status labels alone.
It must also state:
- what design can safely start from now
- what architecture can safely start from now
- what both must not assume yet
- what specific validation or remediation should happen next if the package is still review-bound

---

The project already uses phase-level admission semantics:

- `PASS`
- `PASS with constrained/review-bound conditions`
- `BLOCKED`

The driver should preserve these as the **formal admission layer**.

However, the execution report needs a more granular review vocabulary for humans.

### Recommended report-level verdict taxonomy
- `PASS`
  - requirement/deliverable exists and is strong enough for current purpose
- `WARNING`
  - requirement/deliverable exists but remains provisional, thin, or evidence-light
- `SKIP`
  - not produced in this run because it was genuinely optional, explicitly deferred, or not yet applicable
- `BLOCKED`
  - required output missing or unusable; downstream progression must not pretend otherwise

### Mapping rule
- many `PASS` + no material blockers → phase admission may become `PASS`
- `WARNING` allowed → phase admission may become `PASS with constrained/review-bound conditions`
- any unresolved Class C blocker → phase admission becomes `BLOCKED`

### Important interpretation rule
It is valid for a run to have:

- many deliverables marked `PASS`
- several deliverables marked `WARNING`
- no single deliverable row marked `BLOCKED`

and still end in formal admission `BLOCKED`.

This happens when:

- the remaining weakness is not “missing structure” but **missing evidence basis for closure**
- or another Class C unresolved truth means the next phase would still have to invent critical truth

In that situation:

> **deliverable-level verdicts remain useful, and formal phase admission becomes `BLOCKED` only when the unresolved item truly forces downstream invention of critical truth.**

This means:

> **PASS / WARNING / SKIP / BLOCKED is the execution-report layer**

while:

> **PASS / PASS-with-constrained-review-bound / BLOCKED remains the formal phase-admission layer**

---

## 8. Missing-evidence semantics

One of the key gaps revealed by real-case testing is that Stage-04 often has:

- validation target
- validation method
- thresholds/signals

but not yet:

- real feedback
- real signal
- real validation record
- real validation conclusion backed by observed evidence

The driver must not flatten this into false success.

### v0.1 rule
The following may be absent in a real run:

- real feedback
- real signal
- real validation record
- real conclusion backed by real-world evidence

but only when all of the following are true:

1. the missing item is explicitly reported
2. the item receives `WARNING`, not `PASS`
3. the Unified Product Pack preserves this as unresolved or review-bound truth
4. the final admission recommendation is downgraded accordingly

In other words:

> **missing evidence is allowed as warning-bearing incompleteness, not as silent equivalence to success.**

### Important v0.1 clarification
Missing real feedback / signal / validation record / evidence-backed conclusion does **not automatically** become Class C.

Default reading in v0.1:

- if the case still has explicit user boundary,
- explicit scope / constraints,
- explicit decision state,
- and an honest review-bound handoff candidate,

then the missing real-evidence layer should default to:

- `WARNING`
- review-bound carryover
- downgraded admission confidence

and the formal admission recommendation may still be:

- `PASS with constrained/review-bound conditions`

Only escalate missing evidence to Class C / `BLOCKED` when its absence would force the next phase to invent:

- core user truth
- core scope truth
- core constraint truth
- or fake a closure judgment that the next phase critically depends on

---

## 9. Unresolved-truth classification rule

The driver must classify unresolved items using:

- Class A — acceptable carryover
- Class B — downstream-risk-amplifying carryover
- Class C — must-resolve-before-next-phase

### Required behavior

#### Class A
- may remain as warning or explicit review-bound note

#### Class B
- must appear in:
  - stage output assumptions/open questions
  - Unified Product Pack unresolved section
  - execution report warning section
  - downstream usage restrictions

#### Class C
- must trigger either:
  - `BLOCKED`
  - or `Return / Remediation Needed`

The driver must never let a Class C unresolved truth disappear into prose.

---

## 10. Driver execution loop

## Step 1 — Register input case
- identify source document
- record case name
- record execution date
- record run owner

## Step 2 — Run Stage-01
- produce Stage-01 output using current runtime pack
- classify:
  - deliverables complete?
  - user boundary explicit?
  - problem/opportunity structured?

If not enough for Stage-02a:
- return to clarification/remediation

## Step 3a — Run Stage-02a
- produce requirements structural analysis: panorama / backbone / stakeholder analysis / business scenarios / persona-scenario set / constraints / priority split
- classify whether Stage-02b and Stage-03 can consume without inventing panorama truth

## Step 3b — Run Stage-02b
- produce specification deepening: NFR / quality requirements / domain model / IA direction / subsystem boundaries
- Stage-02b deepens Stage-02a with NFR, domain, and IA constraints that Stage-03 must consume
- do not skip Stage-02b in the current runtime, because current PRD convergence and executability gates assume those inputs exist
- classify whether Stage-03 can slice with specification-grade awareness

## Step 4 — Run Stage-03
- produce experience loops, MVP boundary, slice logic, deferred items
- classify whether Stage-04 can validate without inventing product direction

## Step 5 — Run Stage-04
- produce validation target, method, evidence state, decision state, revision recommendation, design/architecture handoff candidate
- explicitly distinguish:
  - evidence-backed result
  - design-only validation plan

## Step 6 — Assemble Audit-Rich PRD Draft
- assemble from Stage-01..04 outputs using the PRD Assembly Rule (§6.5)
- follow the PRD main document template (`docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`)
- synthesize §1 Executive Summary using the synthesis rule
- consolidate §17 Key Decision Rationale using the assembly rule
- assemble §18 Handoff using the handoff assembly rule
- preserve unresolved truth explicitly in §16
- preserve explicit downstream forbidden assumptions in §13 and §18
- list all source artifacts in §20

## Step 7 — Converge Final PRD
- run `scripts/phase1/phase1_converge_prd.py`
- externalize delta ledger and runtime-only trace residue into a convergence evidence memo
- keep the final PRD deep, but remove large stage-SOP/material-ingestion trace bundles from inline sections
- ensure the final PRD still preserves source artifacts and downstream-consumable decision detail

## Step 8 — Emit execution report
- summarize deliverable-level verdicts
- summarize unresolved truth classes
- summarize admission recommendation

## Step 9 — Decide final run status
- `admission-review-ready`
- `review-bound-but-not-ready`
- `blocked`

---

## 11. Phase-1 execution report

The driver must generate:

- `phase-1-execution-report.md`

### Report minimum sections

#### A. Run metadata
- case name
- source input
- run owner
- run date
- current overall status

#### B. Deliverable verdict matrix
At minimum include these rows:

- target user boundary
- user groups
- user story / user case
- problem list
- opportunity list
- requirements panorama
- main flow
- requirements structure / story map
- key constraints
- priority split
- complete experience loop
- minimum viable experience loop
- MVP definition
- first slice
- later slices
- deferred items
- key assumptions to validate
- validation target
- validation method
- prototype/equivalent artifact
- feedback / signal / result
- validation conclusion
- decision state
- revision recommendations
- design/architecture handoff package
- PRD convergence evidence state

Each row should contain:
- verdict: `PASS | WARNING | SKIP | BLOCKED`
- reason
- unresolved class if applicable: `A | B | C | none`
- next action

#### C. Stage summary
- Stage-01 summary
- Stage-02a summary
- Stage-02b summary
- Stage-03 summary
- Stage-04 summary

#### D. Warning summary
- grouped list of all warning-bearing items

#### E. Blocker summary
- grouped list of all blocked / must-remediate items

#### F. Admission recommendation
- recommended formal state:
  - `PASS`
  - `PASS with constrained/review-bound conditions`
  - `BLOCKED`
- explanation

The recommendation must be allowed to choose `BLOCKED` even when the matrix itself contains only `PASS` and `WARNING`, if Class C unresolved truth remains at closure level.

---

## 12. PRD Main Document and Unified Product Pack relationship

The driver produces a **PRD main document** as the primary convergence artifact.

The Unified Product Pack concept is preserved but converges **into** the PRD main document:

- Stage outputs are produced first
- an audit-rich PRD draft is assembled first
- the final PRD main document is then converged from that draft
- the PRD main document IS the converged product-facing document
- the convergence evidence memo preserves delta ledger and runtime residue outside the final PRD
- execution report explains whether the PRD is:
  - strong enough for admission review
  - still too warning-heavy
  - blocked by Class C unresolved truth

This avoids a common failure mode:

> the pack looks polished, but its truth-state is still weak.

---

## 13. v0.1 design principle

The first version should be:

- markdown-first
- manual-runtime-pack compatible
- report-driven
- honest about missing evidence
- able to run outside the repo in a business-project workspace

It should **not** wait for:

- full orchestrator infrastructure
- registry-enforced traceability runtime
- installable command distribution

---

## 14. Immediate implication for current Phase-1 work

The next high-value move is not to rewrite all four Phase-1 Stage Skills.

It is to add:

1. one Phase-1 Convergence Driver control doc
2. one Phase-1 Execution Report template
3. one real-case replay against a business-case input

This is the smallest addition most likely to transform:

- `method-complete but runtime-incomplete`

into:

- `case-runnable and reviewable`

---

## 15. Current status

This is a design/control artifact for the next hardening slice.

It should be treated as:

- a project-level runtime-control proposal
- a basis for implementation planning
- a reference for future real-case pressure tests

It is not yet:

- a live orchestrator
- a finalized template set
- a completed runtime policy across all four phases
