# Phase-1 Thinking Runtime Layer（v0.1）

## 1. Purpose

This document defines the **Phase-1 integration layer** for the repo's common reasoning kernel.

The generic kernel no longer lives only inside this document.
It is now distributed across:

- `runtime-deps/mindthus/source/skills/3l5s/SKILL.md`
- `runtime-deps/mindthus/source/skills/3l5s/resources/three-layer-recursive-loop.md`
- `runtime-deps/mindthus/source/skills/using-mindthus/SKILL.md`
- `docs/governance/evidence-and-uncertainty-protocol-v0.1.md`
- `docs/governance/deepening-and-freeze-protocol-v0.1.md`
- `docs/governance/handoff-and-convergence-protocol-v0.1.md`

Its purpose is to make Phase-1 behave less like:

- structured decomposition only
- template filling only
- gate-passing only

and more like:

- guided product/requirements thinking
- structured clarification
- alternatives and trade-off reasoning
- decision-rationale capture
- progressive analytical deepening before outputs are frozen

This layer is designed to bind those common modules onto the current Phase-1 Stage family, not replace it.

---

## 2. Scope boundary

This integration layer is explicitly scoped to:

- Stage-01 `requirements-user-research`
- Stage-02a `requirements-structural-analysis`
- Stage-02b `requirements-specification-deepening`
- Stage-03 `requirements-decomposition-and-mvp-slicing`
- Stage-04 `requirements-validation-and-concept-proof`

The generic reasoning modules themselves may be reused by other phases later.

This Phase-1 integration layer is **not yet**:

- a repo-wide thinking framework
- a Phase-2 thinking runtime
- a Phase-3 or Phase-4 abstraction

Some primitives are now intentionally shared, but the artifact mapping in this document remains **Phase-1-specific first**.

---

## 3. Relationship to existing Phase-1 assets

Current Phase-1 already has:

- stage contracts
- stage SOPs
- output templates
- gate / refusal logic
- warning / review-bound semantics
- convergence driver and execution report
- common reasoning-kernel protocols

This layer adds a missing runtime dimension:

> **how the agent thinks before it locks outputs into the existing artifact shapes.**

That thinking must be understood as:

> **method-guided reasoning, not free-floating inference.**

In architectural terms:

- common reasoning kernel = **public reasoning modules**
- current Stage family = **structure layer**
- convergence driver = **execution/reporting layer**
- this document = **Phase-1 integration layer**

## 3.1 Relationship to the common kernel

The public kernel defines reusable reasoning behaviors.
This document specializes them for:

- Phase-1 artifact units
- Phase-1 stage boundaries
- Phase-1 downstream consumers
- Phase-1 review-bound semantics

Phase-1 should therefore stop re-explaining the generic protocol in every stage pack.
Stage packs should call the common kernel and then narrow it with stage-local rules.
The same rule now applies to loop semantics:
Phase-1 should specialize the common loop, not silently own a parallel loop model.

---

## 4. Design principle

The central principle is:

> **Phase-1 outputs should be the result of guided analysis, not merely categorized extraction.**

That means every major Phase-1 output should be traceable back to:

- clarification questions
- alternatives considered
- trade-offs made
- stress tests applied
- rationale recorded

Another critical rule is:

> **Phase-1 thinking units should be decomposed by stage input/output artifacts, not by abstract perceived complexity.**

This means the runtime should not ask:

- “what else could we brainstorm?”

before it asks:

- “which artifact unit in this stage is still weak?”

For Phase-1, decomposition should follow the artifact surface of the current stage.

Examples:
- in Stage-01: target user boundary, problem narrative, need framing, user story, assumptions-to-validate
- in Stage-02a: backbone flow, requirements panorama, boundary choice, constraints, priority split
- in Stage-02b: NFR priorities, domain objects, subsystem boundaries, IA direction
- in Stage-03: complete loop, viable loop, slice choice, deferred items, validation assumptions
- in Stage-04: validation target, method fit, evidence state, decision state, revision consequences

The purpose of this rule is to keep analytical iteration anchored to actual downstream deliverables.

Another equally important rule is:

> **Phase-1 reasoning should be guided primarily by the repo’s method assets (required cards, optional cards, anti-pattern / boundary cards), not performed as unconstrained raw brainstorming.**

This means:

- templates define the required output surface
- SOPs define the execution discipline already embedded in the stage skill
- method cards define the actual thinking posture, heuristics, and anti-pattern boundaries

The runtime should combine all three.

---

## 4.1 Workflow certainty vs. context certainty

Phase-1 should be treated as:

- medium/high `workflow certainty` at the outer shell
- low/variable `context certainty` at the business-truth layer

That means:

- workflow fixes stage order, output contracts, state transitions, gates, and handoffs
- agentic reasoning resolves missing business truth, alternatives, trade-offs, scenario density, and real-world baseline sufficiency
- scripts may record uncertainty, but they must not replace business judgment with generic abstractions
- when context certainty is too low for safe inference, the runtime must clarify, calibrate against real-world evidence, or return-remediate rather than washing the gap away

Every Phase-1 stage skill should therefore expose, explicitly or by inherited template:

- `workflow_certainty`
- `context_certainty`
- `fixed_workflow_scope`
- `agentic_scope`
- `context_completion_policy`
- `loop_policy`
- `exit_criteria`

## 5. Core runtime protocol

## 5.0 Artifact-driven decomposition

Before starting a thinking pass or a new loop round, the runtime must first identify:

1. which current-stage artifact unit is being improved
2. whether that unit is:
   - missing
   - shallow
   - weakly justified
   - poorly handed off downstream
3. what specific reasoning operation is needed for that unit:
   - clarification
   - alternatives comparison
   - trade-off articulation
   - stress testing
   - rationale capture

### Rule
Do not open a new thinking thread unless it maps to a specific current-stage artifact unit.

### Why
This keeps the runtime from drifting into generic brainstorming and preserves compatibility with the Phase-1 output templates and convergence driver.

## 5.0.1 Method-asset-guided reasoning

Before deepening an artifact unit, the runtime should explicitly check which method assets apply.

At minimum, this means consulting:

- the stage’s required cards
- the stage’s optional cards when they materially improve the artifact
- the stage’s boundary / anti-pattern cards

Templates and SOPs still matter, but mainly as:

- output/shape constraints
- stage execution discipline

They are not the primary source of reasoning depth.

### Rule
Do not treat reasoning as purely self-generated intuition when a method card or anti-pattern card already exists that should shape the judgment.

### Intended effect
This prevents two opposite failures:

1. rigid template filling with no thinking
2. freeform thinking that ignores project methodology

The target is:

> **guided reasoning primarily driven by the project’s method assets, while remaining compatible with the stage’s existing template/SOP structure.**

## 5.1 Entry modes

Every Phase-1 run should begin in one of three explicit modes:

### `Guided`
- one question at a time
- use when ambiguity is high and the user can collaborate

### `Context dump`
- accept large pasted context
- ask only for what is materially missing

### `Best guess`
- infer missing details only when the user explicitly allows it
- assumptions must be labeled and preserved for review

### Rule
Mode choice must be visible in the run record.

---

## 5.2 Clarification pacing

Clarification is not an open-ended interview.

For Phase-1, use:

- one targeted question at a time
- bounded rounds
- explicit stop condition

### Default stop condition
Stop clarification when all of the following are true:

- the main user boundary is explicit enough
- the main product/problem direction is explicit enough
- the main uncertainty is explicit enough
- the current stage can proceed without fabricating non-inferable truth

### Clarification anti-patterns
- dumping 8-10 questions at once
- asking generic filler questions
- continuing to ask after the uncertainty is already bounded enough

---

## 5.3 Decision-point protocol

At major decision points, the runtime must not jump directly to a single answer.

Instead it should:

1. generate 2-3 plausible options
2. compare them
3. recommend one
4. explain why not the others

### Required comparison dimensions
- customer value
- evidence strength
- launch realism
- downstream dependency load
- uncertainty risk

### Output requirement
The chosen path must carry a visible `why-this-not-that` rationale.

---

## 5.4 Narrative stress-test protocol

Before converging a major Phase-1 decision, apply a customer-facing narrative stress test.

At minimum ask:

- would a customer care?
- is the problem obvious and specific?
- is the value outcome understandable?
- does this survive the “so what?” test?
- if this were described without feature jargon, would it still sound compelling?

This is especially important before:

- finalizing Stage-01 user/problem framing
- freezing Stage-02a requirement panorama
- freezing Stage-03 MVP boundary

---

## 5.5 Progressive validation inside a stage

The runtime should not wait until the end of each stage to check thinking quality.

Each stage should have **micro-checkpoints** where the agent asks:

- is the current conclusion clear enough?
- is it still too generic?
- are alternatives missing?
- has rationale been recorded?
- are we freezing structure too early?

This does not replace existing stage gates.

It prevents weak reasoning from being laundered into strong-looking artifacts.

---

## 5.6 Evidence left behind

The thinking runtime must leave behind evidence, not just final answers.

At minimum, every major Phase-1 run should preserve:

- assumptions-to-validate
- decision rationale
- rejected alternatives or non-chosen options
- trade-off notes
- narrative stress-test outcome

This evidence may live in:

- stage outputs
- PRD convergence evidence notes
- execution report additions
- or dedicated reasoning sections inside stage outputs

---

## 6. Stage-by-stage insertion points

## 6.1 Stage-01 — requirements-user-research

### Main thinking burden
- make the user/problem/opportunity explicit enough
- avoid generic segmentation
- avoid solution-smuggling
- make the output read like real product analysis rather than only an internal stage artifact

### Runtime additions

#### A. Guided clarification before user grouping
Ask one-step questions to sharpen:
- who exactly is in scope
- what they are trying to achieve
- what blocks them
- why the opportunity matters now

Default question sequence for Stage-01 should prefer:
1. who is the most commercially and behaviorally plausible first-wave user?
2. what are they trying to achieve in outcome language, not feature language?
3. what blocks them today?
4. why is this painful enough to matter now?
5. who looks adjacent but should not be first-wave focus?

#### B. Problem-framing deepening
Before output lock-in, force a PM-style problem narrative:
- who is blocked
- what they are trying to do
- what blocks them
- why it matters
- what emotional or practical cost exists

This should preferably use a compact narrative form equivalent to:
- I am
- trying to
- but
- because
- which makes me feel

Then force a **final problem statement** that compresses the narrative into one strong sentence.

The stage should not be considered analytically strong if it only lists problems but cannot produce a concise, shareable problem statement.

#### C. Alternatives checkpoint
When user boundary is still fuzzy, compare at least 2 plausible segments and explain:
- why this segment is primary
- why the others are deferred / secondary / out of scope

When relevant, also compare at least 2 different need framings for the same target user, for example:
- visibility-only framing
- visibility + actionability framing
- visibility + attribution framing

The runtime should explicitly decide which framing is primary for first-wave product definition.

#### D. Positioning-pressure checkpoint
Before freezing the Stage-01 output, pressure-test whether the chosen user/problem framing can support a plausible product positioning direction.

At minimum ask:
- if this user/problem pair is true, what category would this product most likely belong to?
- what adjacent category might be tempting but misleading?
- what primary benefit would matter most to this user?
- what competing alternative would this user compare us against first?

This does **not** mean Stage-01 must output a full positioning statement every time.

It means Stage-01 should leave enough reasoning so later Phase-1 work does not begin from a problem framing that already collapses under category/value pressure.

#### E. Customer-care / so-what stress test
Before finalizing user/problem/opportunity framing, ask:
- would the chosen user actually care about this problem enough to act?
- is the problem specific enough that the user would recognize themselves in it?
- is this a real problem, or just a feature wish / internal business wish?
- if someone said “so what?”, do we have a strong answer?

### Required evidence left behind
- chosen primary user boundary
- non-chosen adjacent user groups
- rationale for user focus choice
- final problem statement
- customer-care / so-what stress-test outcome
- primary need framing choice and rejected alternatives if multiple were considered
- main assumptions to validate

---

## 6.2 Stage-02a / Stage-02b — structural analysis + specification deepening

### Main thinking burden
- Stage-02a: turn Stage-01 understanding into a defensible whole-picture structure
- Stage-02a: avoid fake panorama and premature flattening
- Stage-02b: deepen the approved panorama into NFR / domain / IA constraints that later stages can actually consume
- make the Stage-02a/02b pack read like a justified product analysis model, not only a neatly arranged map

### Runtime additions

#### A. Structure-before-story-map reasoning
Before building a structure artifact, ask:
- what is the real backbone flow?
- what is core versus optional?
- what boundary would overreach?

This reasoning should be driven primarily by Stage-02a method assets, especially:
- whole-picture structure thinking
- story-map construction
- structured requirements-analysis pattern
- value/evidence discipline before flattening into tasks

The runtime should not start from “how do we draw the structure?”
It should start from:
- what value loop actually exists
- what user/problem framing from Stage-01 must be preserved
- what structure would falsely look tidy but distort the real product shape

#### B. Alternative panorama checkpoint
Generate 2-3 structure candidates when ambiguity is material, for example:
- monitoring-first structure
- recommendation-first structure
- workflow-first structure

Then compare them by:
- clarity
- downstream sliceability
- fit to the chosen customer problem

Also compare them by:
- value-first realism
- evidence strength
- risk of forcing fake certainty into Stage-03

The stage should leave behind an explicit **why-this-structure-not-that** rationale.

#### C. Constraint stress-test
For each major structure decision, ask:
- does this depend on evidence we do not really have?
- are we confusing a useful shape with validated truth?

Add a second question cluster:
- is this constraint real, inferred, or only convenient for the current draft?
- if this constraint is wrong, which parts of the structure would collapse first?
- does this belong in key constraints, or only in assumptions-to-validate?

This is where Stage-02a should enforce **value/evidence discipline before flattening into tasks**.

#### D. Priority-split reasoning checkpoint
Before finalizing the initial priority split, the runtime must explain:
- why something is high-value-first rather than merely visible
- why something is high-risk-to-validate rather than simply “hard”
- why something is deferrable without breaking first-loop viability

The runtime should reject priority groups that read like:
- arbitrary buckets
- feature wishlists
- roadmap cosmetics without analytical basis

#### E. Structure stress-test
Before freezing Stage-02a, ask:
- if Stage-03 received only this structure, could it slice without rebuilding the whole reasoning?
- does the backbone flow actually represent a product loop, or only a diagrammed list?
- does the structure still hold if one provisional assumption is weakened?
- are we preserving upstream uncertainty honestly, or laundering it into a clean-looking panorama?

#### F. Specification-deepening checkpoint (Stage-02b)
Before freezing Stage-02b, ask:
- which NFRs materially force or constrain the first slice?
- which domain objects and relationships must downstream stop inventing for itself?
- which subsystem or IA choices are still open, and which are now constrained enough to hand off?
- if Stage-03 ignored this specification layer, what false slicing or false handoff would likely occur?

### Required evidence left behind
- chosen panorama structure
- alternative structures considered
- why the chosen structure is better for Phase-1 and Stage-03 slicing
- high-risk validation point rationale
- priority-split rationale
- constraint interpretation rationale
- NFR prioritization rationale
- domain-model / object-chain rationale
- IA-direction rationale

---

## 6.3 Stage-03 — requirements-decomposition-and-mvp-slicing

### Main thinking burden
- define a real MVP loop rather than just a smaller scope
- explain why some capabilities stay out

### Runtime additions

#### A. Loop-identification before slicing
The runtime must first articulate:
- the full experience loop
- the minimum viable experience loop
- what makes the MVP still viable rather than just smaller

#### B. Slice-option comparison
At least 2 slicing options should be compared when meaningful, for example:
- monitoring + recommendations first
- monitoring only first
- workflow execution first

#### C. Trade-off reasoning
The slice recommendation must explicitly compare:
- user value speed
- evidence confidence
- dependency complexity
- validation leverage
- risk of overreach

#### D. Deferred-items honesty check
Ask:
- what are we not building and why?
- what would falsely make this look “more complete” but damage viability?

### Required evidence left behind
- why the chosen MVP loop is viable
- why the first slice is first
- why deferred items stay out
- what validation must later prove the slice right or wrong

---

## 6.4 Stage-04 — requirements-validation-and-concept-proof

### Main thinking burden
- define an honest validation chain
- avoid fake certainty
- connect result to revision consequence

### Runtime additions

#### A. Validation-target clarification
Before choosing method, force clarity on:
- what exact assumption / risk / decision is being tested
- what would change if the result is positive or negative

#### B. Method-fit reasoning
Compare plausible validation methods when needed, for example:
- interview
- prototype review
- signal observation
- workflow walkthrough

Explain why the chosen method fits the target better.

#### C. Weak-evidence conclusion discipline
If evidence is weak or absent, the runtime must still answer:
- what is only design-time inference?
- what is real evidence?
- what recommendation is still acceptable under warning-bearing conditions?

#### D. Revision consequence requirement
No validation conclusion is complete until it says:
- what changes next
- what stays review-bound
- what downstream must not assume

### Required evidence left behind
- exact validation target
- why the method was chosen
- what evidence exists versus does not exist
- why the decision state is Go / No-Go / Revise
- revision consequences

---

## 7. Runtime evidence model

The following evidence types should be considered first-class in Phase-1:

### A. Clarification evidence
- the key questions asked
- the critical answers that changed direction

### B. Alternative evidence
- options considered
- recommendation
- why not the others

### C. Stress-test evidence
- whether the current framing survived customer-value pressure tests

### D. Rationale evidence
- why a decision was made
- what would change it later

### E. Review-bound evidence
- what is still provisional
- what is allowed as warning-bearing carryover

---

## 8. What outputs must become richer

This layer should make the following outputs richer, not replace them:

- Stage-01 user-group boundary draft
- Stage-01 first-pass User Story / User Case
- Stage-02a structured requirements analysis note
- Stage-02b specification-deepening note
- Stage-03 release slicing explanation
- Stage-04 validation conclusion and revision recommendation
- Unified Product Pack convergence note
- Phase-1 execution report

The intended change is:

- from: “here is the structured answer”
- to: “here is the structured answer and the thinking path that produced it”

---

## 9. What this layer must not do

This layer must not:

- bypass current gate/refusal rules
- turn every run into an endless workshop
- replace structure with freeform prose
- fabricate evidence in order to sound deeper
- hide review-bound uncertainty behind confident storytelling

It is a thinking runtime, not a license for uncontrolled verbosity.

---

## 10. Immediate next use

The first practical use of this document should be:

1. choose one real Phase-1 case replay
2. replay Stage-01 or Stage-02a/02b using this thinking runtime
3. compare output depth versus the current rerun outputs
4. update only the smallest necessary docs after evidence emerges

This document is therefore:

- Phase-1-specific
- design-oriented
- safe to try in paper replay first

---

## 11. Summary sentence

> **Phase-1 should no longer only ask “what artifact shape is required?”; it should also ask “what thinking path must happen before this artifact is allowed to harden?”**
