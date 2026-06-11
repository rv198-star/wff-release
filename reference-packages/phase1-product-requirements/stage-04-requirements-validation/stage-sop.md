# Stage-04 SOP — requirements-validation-and-concept-proof

## 1. Stage Positioning
- Stage name:
  - requirements-validation-and-concept-proof
- Stage goal:
  - validate the key assumptions and MVP choices from Stage-03 and turn them into explicit conclusions and revision paths
- Parent phase:
  - product / requirements
- Upstream dependency:
  - Stage-03 MVP/slicing outputs
- Downstream target:
  - design / architecture

## 2. Start Conditions
- Required inputs:
  - MVP definition
  - slice explanation
  - key assumptions / risks / decision points
- Optional inputs:
  - low-fidelity prototype direction
  - review-bound provisional assumptions
- Pre-start checks:
  - is there an explicit assumption or decision to validate?
  - is the validation target tied to the actual MVP/slicing logic?
- Refusal rule:
  - refuse to start if no explicit validation target exists
- Clarification expansion rule:
  - clarify the validation target before choosing method or prototype
- Enter `Blocked` when:
  - the target is too vague to define a method/signal chain
- Enter `Provisional Inference` when:
  - the team explicitly accepts a provisional validation design built on still-review-bound assumptions

## 3. Standard Execution Steps
1. Identify the exact assumption / risk / decision to validate.
   - For each target, articulate: what changes if positive? What changes if negative?
   - **Micro-checkpoint**: Is the target specific enough that a method can be designed for it?
2. Compare plausible validation methods when ambiguity still matters and choose a lightweight validation method.
   - Generate 2-3 candidate methods; for each assess: fit to target, cost/speed, evidence quality
   - Select with explicit `why-this-method-not-that` rationale
   - **Micro-checkpoint**: Does the output contain method comparison + selection rationale?
3. Produce a low-cost prototype or equivalent validation artifact if needed.
   - **Prototype fidelity guidance** — choose the minimum fidelity that answers the validation question:
     - paper/sketch prototype: use when testing concept understanding, value proposition clarity, or workflow direction — lowest cost, fastest iteration
     - clickable prototype (e.g., Figma): use when testing interaction flow, navigation comprehension, or task completion — medium cost, good for usability signals
     - coded prototype: use when testing technical feasibility, performance perception, or data-dependent interactions — highest cost, only when lower fidelity cannot answer the question
   - The fidelity choice must be justified: "we chose [fidelity] because the validation target [X] requires [Y] level of realism to produce meaningful signals"
   - Anti-pattern: building a high-fidelity prototype when a sketch would answer the question
4. Record signals, feedback, and findings.
5. Derive Go / No-Go / Revise with explicit decision rationale.
   - Apply evidence-state honesty check: what is design-time inference vs. real evidence vs. unknown?
   - Apply maturity/confidence split: what is safe for downstream start vs. what still lacks evidence?
   - **Three-dimensional validation assessment** — the validation conclusion must address all three dimensions:
     - **Value**: do users find this valuable enough to use/pay for? (desirability)
     - **Usability**: can users accomplish the key tasks effectively? (interaction quality)
     - **Feasibility**: can this be built within the technical and resource constraints? (viability)
   - Each dimension gets its own verdict: `validated | partially-validated | not-validated | not-tested`
   - A dimension marked `not-tested` is not a failure — it's an explicit gap that downstream must be aware of
   - The overall Go/No-Go/Revise must account for all three dimensions, not just value
   - **Micro-checkpoint**: Is the decision state linked to actual evidence, not just optimistic interpretation? Are all three validation dimensions addressed?
6. Record revision consequences, not only revision suggestions.
   - Explicitly state what downstream must NOT assume
7. Feed the result back into MVP/slice/priority thinking.
8. Assemble reasoning evidence into output template Section 3.2.
   - **Declare PRD convergence readiness state**: after assembling reasoning evidence, declare the Unified Product Pack / PRD convergence readiness: `not-started | ready-to-converge | converged-post-stage`. This declaration feeds PRD §19 (Acceptance & Status).
   - **Declare maturity/confidence state**: explicitly declare `document_delivery_state`, `evidence_confidence_state`, `safe_start_scope`, and `blocked_commitments`.
9. Record which required method families from `source-cards.md` materially shaped the validation target, chosen method, and decision.

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - inspect the Stage-03 package and identify validation readiness
- `S1 Clarification Active`:
  - clarify the exact assumption and decision target before validation design starts
- `S2 Blocked`:
  - stop if the validation target is too vague to produce a defensible evidence chain
- `S3 Provisional Inference`:
  - allow only review-bound provisional validation design/conclusion drafts
- `S4 User Review`:
  - review hypothesis, method, result interpretation, and revision consequence
- `S5 Gate Pass`:
  - pass only when a usable validation conclusion and handoff package exist
- `S6 Escalate`:
  - escalate if no defensible validation plan or conclusion can be built under the current evidence boundary

## 4. Process Checkpoints
- Checkpoint 1:
  - validation target is explicit
- Checkpoint 2:
  - method matches the target
- Checkpoint 3:
  - result/feedback is captured explicitly
- Checkpoint 4:
  - decision state is explicit
- Checkpoint 5:
  - revision consequence is explicit
- Checkpoint 6:
  - chosen method rationale and decision-state rationale are explicit
- Checkpoint 7:
  - method-family activation is visible in the reasoning evidence
- Checkpoint 8:
  - delivery readiness and evidence confidence are both explicit
- Fields that require confirmation or explicit review-bound status:
  - any conclusion derived from still-unconfirmed upstream assumptions
  - any revision priority that depends on weak evidence
- Fields allowed as provisional only:
  - first-pass validation design
  - first-pass conclusion when evidence is still weak

## 5. Referenced Method Assets
- Required cards:
  - validated learning loop
  - build-measure-learn loop
  - prototype/validation linkage
  - method-fit reasoning and weak-evidence conclusion discipline
  - `inspired` value-usability-feasibility-triad: every validation conclusion must address desirability, usability, and feasibility
  - `inspired` product-validation-and-prototype-testing: prototype fidelity selection guidance (paper → clickable → coded)
- Optional cards:
  - discovery-before-definition support
  - product validation / prototype-testing support
- Boundary / anti-pattern cards:
  - do not test without a hypothesis
  - do not equate prototype existence with validation success
  - do not give a conclusion without revision consequences
  - do not build high-fidelity prototypes when low-fidelity would answer the question
  - do not claim "validated" when only one dimension (value/usability/feasibility) was tested

## 6. Output Generation Rules
- Required outputs:
  - validation record
  - validation conclusion
  - revision recommendation
  - validation rationale
- Optional output:
  - low-fidelity prototype or equivalent validation artifact
- Minimum output rule:
  - design/architecture must be able to understand what was tested, what was learned, and what changed
- Prototype / diagram rule:
  - a prototype is optional but recommended when it materially improves validation quality
  - a `validation-flow` is recommended if it helps make the evidence chain explicit
- Provenance / assumptions marking rule:
  - any provisional validation assumptions or conclusions must keep status, source, confidence, verification, and assumptions_to_validate fields
- Reasoning capture rule:
  - when Stage-04 chooses a method, interprets weak evidence, or derives a decision state, preserve that reasoning in the output template's Section 3.2 (Reasoning Evidence)
  - the following items are REQUIRED: validation target clarity, method-fit comparison, evidence state honesty check, decision state reasoning, deepening loop log
  - method activation evidence is also REQUIRED: identify which source-card method families materially shaped target selection, method choice, and decision interpretation
- Diagram obligation / fail action:
  - `diagram_obligation: recommended`
  - if the validation chain is unclear, return to hypothesis/method definition before concluding

## 7. Stage Acceptance
- Minimum completion standard:
  - validation target exists
  - validation record exists
  - decision state exists
  - revision recommendation exists
  - validation rationale exists
  - design/architecture-consumable handoff exists
- Common failure signals:
  - no explicit target
  - no clear method-result-decision chain
  - vague “positive feedback” with no decision consequence
  - no revision path
  - no explanation of why this method or decision was chosen
  - method bundles are named in source cards but leave no visible effect on the validation logic
  - unresolved uncertainty silently upgraded into certainty
- Return path:
  - return to target clarification, method choice, or upstream MVP/slice clarification as needed
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if no defensible validation conclusion can be formed with the available evidence

## 8. Handoff Rules
- Handoff target:
  - design / architecture
- Handoff package:
  - validation conclusion
  - validation record
  - prototype/equivalent validation artifact if used
  - validation rationale
  - revision recommendation
  - unresolved risks if any remain
- Handoff explanation requirement:
  - explain what was tested, why this method was chosen, what result emerged, what decision followed, and what must change next
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound design/architecture input, never as silently confirmed truth
