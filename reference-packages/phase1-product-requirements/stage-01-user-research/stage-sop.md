# Stage-01 SOP — requirements-user-research

## 1. Stage Positioning
- Stage name:
  - requirements-user-research
- Stage goal:
  - establish structured user understanding, problem understanding, and opportunity understanding
- Parent phase:
  - product / requirements
- Upstream dependency:
  - initial project background and opportunity clues
- Downstream target:
  - `requirements-structural-analysis` (Stage-02a)

## 2. Start Conditions
- Required inputs:
  - project background
  - business opportunity description
  - at least one evidence clue from feedback, data, observation, interview clue, or market input
- Optional inputs:
  - market context
  - competitor context
  - stakeholder context
- Pre-start checks:
  - is the research object explicit enough to examine?
  - is there a real opportunity statement rather than only a vague wish?
- Refusal rule:
  - refuse formal execution if research target or business opportunity is still undefined
- Clarification expansion rule:
  - ask clarification questions first; do not jump into solutioning
- Enter `Blocked` when:
  - non-inferable fields remain missing
- Enter `Provisional Inference` when:
  - the user explicitly requests a best-guess draft after being told the inputs are insufficient

## 2.1 Entry Mode Protocol

Before execution begins, explicitly select and record one of three entry modes:

- `Guided`:
  - one question at a time; use when ambiguity is high and the user can collaborate
  - clarification proceeds through the full question sequence in Step 2
- `Context Dump`:
  - accept large pasted context; ask only for what is materially missing
  - skip questions already answered by the context; proceed to Step 2 gap-check
- `Best Guess`:
  - infer missing details only when the user explicitly allows it
  - all inferred content must be labeled `AI-INFERRED DRAFT — UNVERIFIED`
  - assumptions must be preserved in assumptions_to_validate

Rule: the chosen entry mode must appear in the output under `entry_mode_record`.

## 2.2 Workflow / Context Boundary

- `workflow_certainty`:
  - medium-high for the Stage-01 shell; Steps 1-7, checkpoints, and state transitions stay fixed
- `context_certainty`:
  - low-to-medium until user evidence, scenario detail, and baseline calibration are strong enough
- `fixed_workflow_scope`:
  - entry-mode selection, clarification pacing, alternatives comparison, stress tests, evidence assembly, review/gate/handoff
- `agentic_scope`:
  - topology-profile routing, business-world deepening, substitute pressure judgment, thesis argument selection, scenario expansion, `why-this-not-that`, anti-demo review, baseline calibration
- `topology_profile_routing_rule`:
  - after minimal clarification and before deepening, build a `topology profile`, not a case label
  - choose one `topology_archetype`:
    - `execution-centric`
    - `decision-centric`
    - `hybrid`
  - choose one or more `primary_depth_axes`, plus optional `secondary_depth_axes`
  - record `misfit_risk_if_wrong`
- `topology_axis_rule`:
  - actual deepening pressure comes from the chosen axes, not the archetype label alone
  - first-wave reusable axes:
    - `operational-chain`
    - `exception-state`
    - `role-coordination`
    - `substitute-positioning`
    - `proof-evidence`
    - `buyer-budget-continuation`
  - if the fit is poor, add a new axis explicitly rather than forcing the case into the wrong existing axis
- `context_completion_policy`:
  - clarify first, then use bounded inference with explicit provenance; do not hide missing truth behind clean structure
- `external_evidence_policy`:
  - when ordinary real-world practice materially affects baseline sufficiency, add calibration/evidence before freeze
- `return-upstream rule`:
  - if critical business truth is still non-inferable, stop at `S2 Blocked` or `S6 Escalate` rather than laundering the gap
- `thesis_quality_rule`:
  - do not freeze a thesis merely because required fields are present
  - require plausible substitute pressure, user/buyer/operator value, continuation or closure proof, and architecture pressure before entering final requirements compression
  - scripts may flag weak signals, but Agentic reasoning must decide and rewrite the thesis

## 3. Standard Execution Steps

### Step 1 — Intake & Mode Selection
- Receive input materials and classify their completeness
- Select entry mode (`Guided` / `Context Dump` / `Best Guess`) per Section 2.1
- Record mode selection and rationale in output

### Step 2 — Guided Clarification Sequence
- Execute the following questions one at a time, adapting to the chosen entry mode:
  1. Who is the most commercially and behaviorally plausible first-wave user?
  2. What are they trying to achieve in outcome language, not feature language?
  3. What blocks them today?
  4. Why is this painful enough to matter now?
  5. Who looks adjacent but should NOT be first-wave focus?
- **Research question quality control** — before proceeding with answers, verify question framing:
  - **Reframe solution language into need language**: if any input describes "we need X feature", reframe to "why does the user need to solve Y problem?" — solutions are not research inputs, problems are
  - **Distinguish fact layer from interpretation layer**: mark each piece of evidence as `observed-fact` (user said/did this) vs. `interpretation` (we believe this means...) — do not let interpretations masquerade as facts
  - **Classify research mode**: is this inquiry exploratory (we don't know what we don't know) or problem-focused (we have a hypothesis to validate)? The research strategy differs:
    - exploratory: broad questions, divergent, looking for patterns
    - problem-focused: targeted questions, convergent, looking for confirmation/disconfirmation
  - Mark contradictions between evidence sources explicitly — contradictions are signals, not noise
- For `Context Dump` mode: check which questions are already answered; ask only for gaps
- For `Best Guess` mode: infer answers and label each as provisional
- Stop clarification when: (a) the main user boundary is explicit enough, (b) the main problem direction is explicit enough, (c) the main uncertainty is explicit enough
- Anti-patterns: dumping all questions at once; asking generic filler questions; continuing after uncertainty is bounded; accepting solution-language answers without reframing to need-language
- **Micro-checkpoint MC1**: Is the target user boundary explicit enough to proceed? Are fact vs. interpretation layers distinguished? If no → continue clarification or enter `S2 Blocked`

### Step 2.5 — Topology Profile Routing
- Before deepening the problem world further, build a `topology profile`:
  - choose one `topology_archetype`:
    - `execution-centric`
    - `decision-centric`
    - `hybrid`
  - choose `primary_depth_axes`
  - choose optional `secondary_depth_axes`
- Record:
  - why this profile fits the business shape
  - what depth pressure this creates for later passes
  - `misfit_risk_if_wrong`
  - what would force reclassification
- Routing criteria:
  - if the core depth risk is fake operating realism, lean `execution-centric`
  - if the core depth risk is fake economic decision logic, lean `decision-centric`
  - if both are material, lean `hybrid`
  - in all cases, pick depth axes explicitly rather than treating the archetype alone as sufficient routing
- **Micro-checkpoint MC1.5**: Is the topology profile explicit enough to determine what “ordinary real-world baseline” means here and which depth axes must be earned? If no → continue clarification instead of proceeding with generic deepening

### Step 3 — User Boundary & Segmentation with Alternatives
- Generate 2-3 candidate user segments (not just the obvious one)
- For each candidate, assess:
  - commercial value (willingness to pay, budget access)
  - behavioral reachability (can we reach them, will they adopt?)
  - evidence strength (how confident are we this segment exists and has this pain?)
  - risk (what could go wrong if we bet on this segment?)
  - cost-willingness signal (what would this user sacrifice to solve the problem — time, money, switching cost, workflow change? The stronger the cost-willingness, the more real the need)
- Produce a comparison table or structured comparison
- Select one primary segment with explicit `why-this-not-that` rationale
- Record non-chosen segments with deferral/exclusion reasoning
- **Micro-checkpoint MC2**: Does the output contain (a) at least 2 candidate segments, (b) a comparison, (c) a selection with rationale? If no → do not proceed to Step 4

### Step 4 — Problem-Framing Deepening
- **Insight synthesis** — before writing the empathy narrative, apply structured reasoning:
  - gather raw evidence markers from Step 2 (observed facts, interpretations, contradictions)
  - identify recurring patterns across evidence sources
  - form explanatory hypotheses: "the reason users struggle with X is because Y" — this is abductive reasoning (best explanation for observed patterns)
  - test each hypothesis: does it explain most of the evidence? does it predict behaviors we haven't observed yet? does it survive the "what if this is wrong" question?
  - bridge from research insight to product judgment: the insight is not just "users have problem X" but "problem X suggests the product should prioritize Y over Z because..."
- Produce a PM-style empathy narrative using this structure:
  - I am [specific user]
  - trying to [achieve outcome in user language]
  - but [what blocks them]
  - because [root friction or structural cause]
  - which makes me feel [emotional or practical cost]
- Compress the narrative into one strong, concise **final problem statement**
- If multiple problem framings are plausible, compare 2-3 framings and select one with rationale
- The stage cannot be considered analytically strong if it only lists problems but cannot produce a concise, shareable problem statement
- **Micro-checkpoint MC3**: Does the final problem statement survive a basic "so what?" test? (Would a customer recognize this as their problem? Is it specific, not generic?) If no → rewrite before proceeding

### Step 5 — Need-Framing Alternatives
- When ambiguity exists about how to frame the core need, compare at least 2 plausible need framings (e.g., monitoring-only vs. monitoring+actionability vs. monitoring+attribution)
- For each framing, assess: strengths, weaknesses, downstream implications for product shape
- Select the primary framing with explicit rationale
- When no meaningful ambiguity exists, document why the framing is unambiguous and skip comparison
- **Micro-checkpoint MC4**: Is there a documented `why-this-framing-not-that` decision? If no → produce one before proceeding

### Step 6 — Stress Tests
- **Customer-care stress test** (mandatory before output lock-in):
  1. Would the chosen user actually care about this problem enough to act?
  2. Is the problem specific enough that the user would recognize themselves in it?
  3. Is this a real problem, or just a feature wish / internal business wish?
  4. If someone said "so what?", do we have a strong answer?
  - Record verdict: `passed | failed | inconclusive` with reasoning
- **Positioning-pressure stress test** (mandatory before output lock-in):
  1. If this user/problem pair is true, what category would this product most likely belong to?
  2. What adjacent category might be tempting but misleading?
  3. What primary benefit would matter most to this user?
  4. What competing alternative would this user compare us against first?
  - Record verdict: `passed | failed | inconclusive` with reasoning
- **Feasibility-gate stress test** (mandatory before output lock-in):
  1. Is the proposed product direction technically feasible with known or available technology?
  2. Is the business model direction sustainable (can this be delivered at a cost users will pay)?
  3. Are there regulatory, legal, or compliance barriers that would block this direction?
  4. Does this direction require capabilities the team does not have and cannot reasonably acquire?
  - Record verdict: `passed | failed | inconclusive` with reasoning
  - Note: this is a directional feasibility check, not a detailed technical assessment — the goal is to catch obviously infeasible directions early
- **Micro-checkpoint MC5**: If any stress test verdict is `failed`, return to Step 3 (if user boundary is weak) or Step 4 (if problem framing is weak) or flag as `S6 Escalate` (if feasibility is the concern) before proceeding

### Step 7 — Evidence Assembly & Output Lock-in
- Assemble all reasoning evidence into the output template's Reasoning Evidence section
- Record which required method families from `source-cards.md` were actually activated during this run and where they changed the analysis
- Verify completeness of the 10 required evidence items:
  1. topology profile record with rationale
  2. chosen primary user boundary
  3. non-chosen adjacent user groups with rationale
  4. user focus choice rationale (including cost-willingness signal)
  5. final problem statement
  6. customer-care / so-what stress-test outcome
  7. positioning-pressure stress-test outcome
  8. feasibility-gate stress-test outcome
  9. primary need framing choice and rejected alternatives
  10. main assumptions to validate
- If any of the 10 items is missing, return to the relevant Step before lock-in
- If provisional content exists, route to user review (`S4 User Review`) before gate pass
- Produce the structured problem / opportunity list with evidence traces

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - capture the raw intent, select entry mode, and move to clarification
- `S1 Clarification Active`:
  - execute the Step 2 question sequence one-step-at-a-time
- `S2 Blocked`:
  - stop formal progression when core non-inferable fields are absent
- `S3 Provisional Inference`:
  - produce explicitly labeled provisional drafts only after explicit user continuation
- `S4 User Review`:
  - require accept / accept_with_corrections / reject_and_return behavior
- `S5 Gate Pass`:
  - allow Stage-02 handoff only when Stage-01 required outputs AND reasoning evidence are in place
- `S6 Escalate`:
  - escalate if the case requires real-world evidence beyond safe AI inference

## 3.2 Thinking Loop Integration

After the initial draft is produced (Steps 1-7), the stage enters a bounded deepening loop before final freeze.

### Mode boundary
- Default loop mode:
  - `baseline`
- `creative` mode:
  - allowed only when the parent Phase-1 run explicitly selected it and Stage-01 baseline sufficiency already exists

### Workflow / agentic boundary
- Steps 1-7 remain the fixed workflow shell.
- Deepening may strengthen specific artifact units inside that shell, but it may not skip required comparisons, stress tests, or evidence assembly.
- If an operationally rich domain is still below ordinary real-world baseline, add calibration/evidence before freeze rather than polishing the current draft.

### Round-value rule
- A new round is justified only when it is likely to create `positive_business_value_gain`, meaning at least one of:
  - more realistic ordinary baseline
  - thicker and more credible core scenarios
  - clearer `why-this-not-that` decision
  - less downstream invention of critical truth
  - removal of a demo-like omission

### Loop states
- `S-draft-structured`: initial output exists; fields are filled; reasoning may still be shallow
- `S-deepening-round-1`: first analytical deepening (clarification, alternatives, trade-offs, stress tests, rationale capture)
- `S-deepening-round-2`: second deepening (only high-value gaps exposed by round 1; no broad re-exploration)
- `S-deepening-round-3`: final deepening (integration of strongest reasoning improvements; tighten synthesis; no new broad exploration unless a true blocker is discovered)
- `S-review-bound-freeze`: good enough to freeze and hand off under explicit warning/review-bound semantics
- `S-return-remediate`: cannot responsibly freeze; targeted clarification or remediation required
- `S-blocked`: cannot continue without inventing non-inferable truth

### Default loop limit
- One structured draft + up to THREE deepening rounds
- After three rounds, the stage MUST exit to one of: `S-review-bound-freeze` / `S-return-remediate` / `S-blocked`

### Deepening round trigger conditions
A new round is justified only if at least one of these is true:
1. the current conclusion is still too generic
2. a meaningful alternative was not explored
3. the `why-this-not-that` rationale is weak
4. the customer-care / so-what stress test fails or is inconclusive
5. downstream usability (Stage-02 handoff quality) is still weak
6. a comparison replay revealed a better reasoning pattern worth absorbing
7. a specific artifact unit (user boundary, problem statement, need framing, assumptions) remains shallow or weakly justified

If none of these are true, do not loop again.

### Stage-01 specific deepening focus
Each round may improve only:
- topology-profile certainty and topology-matched depth pressure
- target user boundary sharpness
- problem-framing quality
- need-framing alternatives
- why-this-not-that clarity
- Stage-02 handoff usefulness

Not allowed in later rounds:
- endless expansion of user lists
- generic market brainstorming without decision pressure
- style-only rewriting

### Extra rule for round 3
Round 3 is allowed only when rounds 1 and 2 already improved the stage materially, the current artifact still lacks synthesis quality or downstream usability, and the expected work is integrative rather than exploratory.

### Per-round evidence requirement
Each round must record:
- what artifact unit was refined
- which alternative(s) were compared (if any)
- what trade-off was clarified
- whether the stress test outcome improved
- why the stage is now frozen / continued / returned / blocked

### Freeze criteria
The stage may enter `S-review-bound-freeze` when all of the following are true:
1. the core framing is explicit enough
2. at least one meaningful alternative has been considered when ambiguity was material
3. the main assumptions are explicit
4. downstream (Stage-02) can proceed without inventing core truth
5. another round is unlikely to create major analytical improvement
6. required method families were actually applied rather than merely listed in `source-cards.md`

### Method-activation rule
Stage-01 may not freeze at `PASS`-level quality if the run cannot show which source-card method families shaped:
- user-segmentation choice
- evidence synthesis
- problem framing
- need framing

If methods were nominally referenced but not materially applied, the stage should remain `WARNING` or continue deepening.

## 4. Process Checkpoints

### Structure checkpoints
- Checkpoint 1:
  - target user boundary is explicit
- Checkpoint 2:
  - business opportunity is explicit enough to justify continued work
- Checkpoint 3:
  - at least one User Case / User Story draft exists
- Checkpoint 4:
  - the output is structured, not a pile of notes
- Checkpoint 5:
  - a final problem statement exists and survives a basic customer-care / so-what stress test

### Reasoning quality checkpoints
- Checkpoint 6:
  - at least 2 candidate user segments were compared with explicit selection rationale (why-this-not-that)
- Checkpoint 7:
  - the customer-care stress test and positioning-pressure stress test both have recorded verdicts (passed / failed / inconclusive) with reasoning
- Checkpoint 8:
  - feasibility-gate stress test has a recorded verdict with reasoning
- Checkpoint 9:
  - all 10 required reasoning evidence items are present in the output (see Step 7 checklist)

### Confirmation and provisional rules
- Fields that require user confirmation:
  - target user boundary
  - high-level business goal direction
  - hard real-world constraints if present
- Fields allowed as provisional only:
  - proto-persona
  - first-pass User Case / User Story
  - first-pass problem / opportunity list

## 5. Referenced Method Assets
- Required cards:
  - use direct user research as the primary understanding posture
  - use fast user-group segmentation as the minimum grouping mechanism
  - use problem-framing / problem-statement thinking to force a shareable articulation of the user problem
  - `product-demand-fit` question-reframing-templates: reframe solution language into need language
  - `product-demand-fit` interview-funnel-evidence-check: distinguish fact layer vs. interpretation layer, mark contradictions
  - `product-demand-fit` exploratory-vs-problem-insight-framing: classify research mode (exploratory vs. problem-focused)
  - `product-demand-fit` need-vs-want-cost-test: assess cost-willingness signal in user segmentation
  - `product-demand-fit` abductive-insight-synthesis: from raw evidence → patterns → explanatory hypotheses → product judgment
  - `inspired` value-usability-feasibility-triad: feasibility-gate stress test
  - `inspired` opportunity-assessment: commercial opportunity evaluation framework
- Optional cards:
  - group psychology and opinion-leader perspective
  - product definition / exploration boundary perspective
  - `behind-the-scenes-product` user-research-to-product-judgment: bridge research findings to product direction decisions
  - `lean-product-development` useful-value-discovery-principle: validate value before building
- Boundary / anti-pattern cards:
  - avoid generic persona labels without evidence
  - avoid presenting inferred user facts as confirmed user truths
  - avoid accepting solution-language inputs without reframing to need-language
  - avoid treating interpretations as observed facts

## 6. Output Generation Rules
- Required outputs:
  - structured research summary
  - user-group boundary draft
  - first-pass User Case / User Story draft
  - final problem statement
  - structured problem / opportunity list
- Optional output:
  - stakeholder analysis table when multi-role decision chains materially affect the problem
- Minimum output rule:
  - the package must be directly consumable by Stage-02
- Prototype / diagram rule:
  - no hard diagram gate
  - if no diagram is used, a structured table must carry the equivalent segmentation meaning
- Provenance / assumptions marking rule:
  - any provisional content must include status, source, confidence, verification, assumptions_to_validate, and what_changes_if_wrong
- Reasoning capture rule:
  - when Stage-01 uses alternatives, stress tests, or rationale-heavy user/problem framing, preserve that reasoning in the output template's Section 3.2 (Reasoning Evidence)
  - the following items are REQUIRED, not optional:
    - entry mode record
    - user boundary alternatives comparison
    - problem narrative (empathy form + final statement)
    - need framing alternatives (when ambiguity exists)
    - stress test outcomes (customer-care, positioning-pressure, and feasibility-gate)
    - deepening loop log (even if only 0 deepening rounds were needed)
- Diagram obligation / fail action:
  - `diagram_obligation: optional`
  - if no structure is visible at all, fail back to clarification and re-structure the output

## 7. Stage Acceptance
- Minimum completion standard:
  - explicit user-group boundaries
  - at least one User Case / User Story draft
  - final problem statement exists
  - structured problem / opportunity list with evidence traces
  - handoff package consumable by Stage-02
  - reasoning evidence section is populated (Section 3.2 of output template)
  - at least one user-segment alternative was compared with why-this-not-that rationale
  - both stress tests (customer-care + positioning-pressure) have recorded verdicts
  - feasibility-gate stress test has recorded verdict
- Common failure signals:
  - only raw notes
  - user labels without boundaries
  - no evidence-linked opportunity statements
  - no clear final problem statement
  - inferred content silently treated as confirmed
  - conclusions presented without showing alternatives considered
  - stress tests absent or skipped without justification
  - no deepening loop log (even a "0 rounds needed" entry is required)
- Return path:
  - return to clarification if user / problem / opportunity framing is still unstable
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if continued progress would depend on real-world evidence the current context cannot safely substitute

## 8. Handoff Rules
- Handoff target:
  - `requirements-structural-analysis` (Stage-02a)
- Handoff package:
  - structured research summary
  - user-group boundary draft
  - first-pass User Case / User Story draft
  - final problem statement
  - structured problem / opportunity list
  - assumptions / open questions
  - reasoning evidence (user boundary alternatives, stress test outcomes, need framing rationale)
- Handoff explanation requirement:
  - explain the main opportunity, the main uncertainty, the main downstream risk, and the chosen user/problem framing rationale
  - include: which alternatives were considered and why they were not chosen
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound input, not as confirmed fact
