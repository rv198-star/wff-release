# Stage-02a SOP — requirements-structural-analysis

## 1. Stage Positioning
- Stage name:
  - requirements-structural-analysis
- Stage goal:
  - transform Stage-01 understanding into a structured requirements panorama with stakeholder analysis, business scenario depth, and persona/scenario construction
- Parent phase:
  - product / requirements
- Upstream dependency:
  - Stage-01 structured outputs
- Downstream target:
  - `requirements-specification-deepening` (Stage-02b) or `requirements-decomposition-and-mvp-slicing` (Stage-03)

## 2. Start Conditions
- Required inputs:
  - Stage-01 structured research summary
  - Stage-01 topology profile record
  - explicit user-group boundaries
  - structured problem / opportunity list
  - business/product goal direction
- Optional inputs:
  - market context
  - competitor context
  - stakeholder context
  - explicitly marked provisional notes
- Pre-start checks:
  - is there enough shared understanding to build a whole-picture structure?
  - are user and problem boundaries visible enough to avoid fake structure?
- Refusal rule:
  - return to Stage-01 if foundational research conclusions are missing
- Clarification expansion rule:
  - clarify missing user/problem structure before building analysis structure
- Enter `Blocked` when:
  - non-inferable upstream fields are absent and the structure would be fabricated
- Enter `Provisional Inference` when:
  - the team explicitly accepts a provisional structure draft based on still-review-bound upstream material

## 2.1 Workflow / Context Boundary
- `workflow_certainty`:
  - high for the Stage-02a shell; the required checkpoints, comparisons, and handoff rules are fixed
- `context_certainty`:
  - medium and inherited from Stage-01; weak upstream truth must stay visible
- `fixed_workflow_scope`:
  - handoff inspection, value-loop articulation, structure comparison, scenario/stakeholder analysis, stress tests, evidence assembly
- `agentic_scope`:
  - topology-profile carryover check, structure choice, scenario deepening, stakeholder-conflict reasoning, trade-off articulation, sliceability judgment
- `topology_profile_carryover_rule`:
  - inherit the Stage-01 `topology profile` before building structure
  - if the structure logic now points to a different profile, return upstream or explicitly reroute with rationale; do not silently drift
- `topology_axis_structure_rule`:
  - preserve the inherited `primary_depth_axes` in the panorama and scenario structure
  - preserve `secondary_depth_axes` where they materially affect sliceability, scenarios, or stakeholder logic
  - if none of the inherited axes fit the structure pressure anymore, name the new axis explicitly rather than flattening everything into generic categories
- `context_completion_policy`:
  - use narrow inference only after inherited uncertainty is recorded; if core business truth is missing, return to Stage-01
- `external_evidence_policy`:
  - add external/domain calibration only when it materially improves structure realism or stakeholder/business-process credibility
- `return-upstream rule`:
  - if the panorama would otherwise be fabricated from missing Stage-01 truth, do not proceed

## 3. Standard Execution Steps

### Step 1 — Upstream Handoff Inspection
- Check Stage-01 handoff completeness: topology profile, user boundary, problem statement, need framing, assumptions, reasoning evidence
- Classify uncertainty level: which Stage-01 outputs are confirmed vs. provisional vs. still-open?
- If Stage-01 reasoning evidence (Section 3.2) is present, use it to inform structure choices — especially the user boundary alternatives and stress test outcomes
- **Micro-checkpoint MC1**: Can a whole-picture structure be built without inventing core user/problem truth? If no → return to Stage-01 or enter `S2 Blocked`

### Step 2 — Value-Loop Identification (Before Structure)
- Before drawing any structure, articulate:
  - What is the real value loop? (what does the user do, what do they get back, why do they return?)
  - What user/problem framing from Stage-01 must be preserved in the structure?
  - What structure would look tidy but distort the real product shape?
- Topology-profile pressure:
  - identify which inherited `primary_depth_axes` the structure must preserve
  - identify which `secondary_depth_axes` still materially matter for handoff quality
  - call out any mismatch between the inherited profile and the emerging structure pressure
- This reasoning should drive structure design, not the other way around
- **Micro-checkpoint MC2**: Is the value loop articulated in user-outcome language (not feature language)? If no → rewrite before proceeding

### Step 2.5 — Stakeholder Identification & Analysis
- Before structuring requirements, identify who matters and how they influence the product:
  - **Identify stakeholders** using a systematic sweep:
    - direct users (who uses the product hands-on?)
    - indirect users (who is affected by the product's outputs without using it directly?)
    - decision makers (who approves budget, adoption, or cancellation?)
    - influencers (who shapes opinion — internal champions, detractors, domain experts?)
    - regulators / compliance bodies (if applicable)
  - **For each key stakeholder**, produce a stakeholder profile:
    - role and relationship to the product
    - key concerns and success criteria (what does this stakeholder care about most?)
    - potential resistance or adoption barriers
    - influence level (high / medium / low) and engagement strategy
    - conflict points with other stakeholders (if any)
  - **Identify adoption chain**: from research insight to organizational action — who must say yes, in what order, for the product to be adopted?
  - **Identify stakeholder conflicts**: where do stakeholder interests diverge? Which conflicts must be resolved before structure can be frozen?
- Produce a stakeholder list + key stakeholder profiles (simplified — not full dossiers, but enough to inform structure and priority decisions)
- **Micro-checkpoint MC2.5**: Are decision-chain roles identified? Are material stakeholder conflicts surfaced? If no → complete before proceeding to structure

### Step 3 — Structure Alternatives Comparison
- Generate 2-3 candidate panorama structures when ambiguity is material, for example:
  - monitoring-first structure (observe → report → recommend)
  - recommendation-first structure (analyze → recommend → track)
  - workflow-first structure (configure → observe → recommend → execute → review)
- For each candidate, assess:
  - clarity (is the backbone flow understandable?)
  - downstream sliceability (can Stage-03 cut an MVP from this without rebuilding?)
  - fit to the chosen customer problem (does it match the Stage-01 user/need framing?)
  - value-first realism (does the structure lead with value or with infrastructure?)
  - evidence strength (how much of this structure is supported vs. speculated?)
  - risk of forcing fake certainty into Stage-03
- Select one structure with explicit `why-this-structure-not-that` rationale
- **Micro-checkpoint MC3**: Does the output contain (a) at least 2 structure candidates, (b) a comparison, (c) a selection with rationale? If no → do not proceed to Step 4

### Step 4 — Backbone Flow, Story Map & Business Scenario Analysis
- Separate goal, backbone activities, tasks, and constraints
- Produce a story map or equivalent structure artifact (diagram obligation: required)
- The backbone should represent a product loop (not just a diagrammed feature list)
- Minimum elements: at least 3 backbone activities, at least 2 tasks per activity, one marked main flow, at least one boundary/exclusion, at least one high-risk validation point
- **Business process identification** — identify core business processes using boundary types:
  - main flow processes (the primary value-delivery path)
  - variant flow processes (alternative paths triggered by different conditions)
  - supporting processes (enable the main flow but are not user-facing value)
  - management/governance processes (monitoring, reporting, admin)
- **Business scenario decomposition** — for each backbone activity, decompose into discrete business scenarios using the pattern `[Role]: [Scenario verb-object]`:
  - each scenario is an independent unit of business behavior (not a UI screen)
  - identify trigger, precondition, main success path, and key exception paths
  - not all scenarios need full analysis — prioritize: high-value-first + high-risk scenarios get full scenario analysis, others get identification only
- **Key scenario deep analysis** — for the top 3-5 critical scenarios (high-value or high-risk), produce a scenario-challenge-solution structure:
  - scenario context: who, when, why this scenario is triggered
  - key challenges: what makes this scenario hard, uncertain, or failure-prone
  - solution direction: what the product must do (functional need, not UI specification)
  - success criteria: how do we know the scenario is handled well
- **Micro-checkpoint MC4**: (a) Does the backbone represent an actual user workflow loop, or is it just a categorized feature list? (b) Are at least 3 key business scenarios identified with scenario-challenge-solution depth? If either fails → restructure before proceeding

### Step 4.5 — Persona & Context Scenario Construction
- From Stage-01 user research outputs + Step 2.5 stakeholder analysis, construct **key user personas**:
  - a persona is a behavioral archetype with goals — not a demographic label
  - minimum per persona: name, role archetype, key goals (life goals → experience goals → end goals), behavioral patterns, pain points, mental model of the problem space
  - for each persona, mark: primary (drives core product decisions) vs. secondary (must be served but does not drive architecture) vs. negative (explicitly excluded user type)
  - minimum: 1 primary persona, 1 secondary persona. Maximum for Phase-1: 3 personas total (keep focused)
- Construct **context scenarios** for the primary persona:
  - a context scenario describes a day-in-the-life narrative: what situation triggers the need, what the user does (in user language, not feature language), what outcome they expect
  - context scenarios are NOT wireframes and NOT feature lists — they describe the desired experience without specifying UI
  - minimum: 1 context scenario per primary persona covering the main value loop
- Construct **key-path scenarios** for the top 3 critical interactions:
  - a key-path scenario is more specific than context: it traces a single end-to-end interaction with enough detail to derive design requirements
  - each key-path scenario should connect to at least one business scenario from Step 4
- **Design requirements extraction** — from personas and scenarios, extract design requirements:
  - design requirements describe what the interaction must achieve, not how the UI looks
  - pattern: "The system must enable [persona] to [accomplish goal] when [context/trigger] so that [outcome]"
  - design requirements are NOT features — "show a dashboard" is a feature; "enable the primary operator to assess current workflow status within 30 seconds of login" is a design requirement
- **Micro-checkpoint MC4.5**: (a) Do personas have behavioral goals (not just demographics)? (b) Do context scenarios describe experience in user language (not feature language)? (c) Are design requirements expressed as interaction outcomes (not UI specs)? If any fails → rewrite before proceeding

### Step 5 — Constraint Stress-Test
- For each major constraint, ask:
  - Is this constraint real, inferred, or only convenient for the current draft?
  - If this constraint is wrong, which parts of the structure would collapse first?
  - Does this belong in key_constraints, or only in assumptions_to_validate?
- For each major structure decision, ask:
  - Does this depend on evidence we do not really have?
  - Are we confusing a useful shape with validated truth?
- Record constraint interpretation rationale
- **Micro-checkpoint MC5**: Have constraints been stress-tested (not just listed)? If no → run the stress test before proceeding

### Step 5.5 — NFR Initial Identification
- Perform NFR initial identification: scan non-functional dimensions for relevance to this product.
- For each relevant dimension, record current information state and known signals from Stage-01 or current analysis.
- This is a lightweight scan — do NOT attempt full quality-scenario analysis (that belongs to Stage-02b if executed).
- The minimum requirement is: which dimensions matter and what do we currently know.
- **Micro-checkpoint MC5.5**: Does the output cover at least dimension relevance, information state, and Stage-02b dependency note? If no → complete the scan before proceeding

### Step 6 — Priority Split with Reasoning
- Produce an initial priority split: high-value-first / high-risk-to-validate / deferrable
- For each priority group, explain:
  - why something is high-value-first rather than merely visible
  - why something is high-risk-to-validate rather than simply "hard"
  - why something is deferrable without breaking first-loop viability
- Reject priority groups that read like arbitrary buckets, feature wishlists, or roadmap cosmetics without analytical basis
- **Micro-checkpoint MC6**: Does the priority split have analytical rationale (not just grouping)? If no → add reasoning before proceeding

### Step 7 — Structure Stress-Test & Evidence Assembly
- Before freezing, apply a structure stress-test:
  1. If Stage-03 received only this structure, could it slice without rebuilding the whole reasoning?
  2. Does the backbone flow actually represent a product loop, or only a diagrammed list?
  3. Does the structure still hold if one provisional assumption is weakened?
  4. Are we preserving upstream uncertainty honestly, or laundering it into a clean-looking panorama?
- Assemble all reasoning evidence into the output template's Reasoning Evidence section
- Verify completeness of required evidence items:
  1. inherited topology profile and any explicit rerouting rationale
  2. chosen panorama structure with alternatives comparison
  3. backbone flow rationale
  4. constraint stress-test outcomes
  5. priority split rationale
  6. high-risk validation point identification
  7. structure stress-test outcome
  8. stakeholder analysis summary (key stakeholders, conflicts, adoption chain)
  9. key business scenario analysis (at least 3 core scenarios with scenario-challenge-solution structure)
  10. key persona + scenario summary (primary persona with context scenario and key-path scenarios)
- Mark unresolved upstream uncertainty explicitly

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - capture the Stage-01 package, inspect structure/readiness, and check for Stage-01 reasoning evidence
- `S1 Clarification Active`:
  - clarify missing structure assumptions before analysis proceeds
- `S2 Blocked`:
  - stop if the panorama would rely on non-inferable missing fields
- `S3 Provisional Inference`:
  - allow only review-bound provisional structure drafting
- `S4 User Review`:
  - review unresolved upstream assumptions and the resulting structure choices
- `S5 Gate Pass`:
  - pass only when Stage-03 can consume the panorama safely AND reasoning evidence is in place
- `S6 Escalate`:
  - escalate if reliable structure cannot be built without external evidence or stakeholder decision

## 3.2 Thinking Loop Integration

After the initial draft is produced (Steps 1-7), the stage enters a bounded deepening loop.

### Mode boundary
- Default loop mode:
  - `baseline`
- `creative` mode:
  - allowed only when the parent Phase-1 run explicitly selected it and Stage-01 baseline truth is already stable

### Workflow / agentic boundary
- Steps 1-7 remain the fixed workflow shell.
- Deepening may strengthen structure, stakeholder, scenario, and priority reasoning inside that shell, but it may not skip the required comparisons or stress tests.
- If the weakness is really upstream business truth rather than Stage-02 structure quality, return to Stage-01 instead of broadening the loop here.

### Round-value rule
- A new round is justified only when it is likely to create `positive_business_value_gain`, meaning at least one of:
  - clearer and more realistic product-loop structure
  - stronger stakeholder/business-scenario realism
  - less Stage-03 truth invention
  - clearer trade-off or boundary reasoning
  - removal of fake certainty or demo-like simplification

### Loop states
- `S-draft-structured`: initial structure exists; may still be shallow
- `S-deepening-round-1`: first deepening (structure alternatives, constraint stress-test, priority reasoning)
- `S-deepening-round-2`: second deepening (only high-value gaps; no broad re-exploration)
- `S-deepening-round-3`: final deepening (integration and synthesis tightening only)
- `S-review-bound-freeze` / `S-return-remediate` / `S-blocked`

### Default loop limit
- One structured draft + up to THREE deepening rounds

### Stage-02a specific deepening focus
Each round may improve only:
- topology-profile carryover fidelity
- backbone flow clarity
- structure alternatives comparison
- boundary reasoning
- constraint realism
- Stage-03 sliceability
- stakeholder analysis depth (conflicts, adoption chain)
- business scenario analysis depth (scenario-challenge-solution)
- persona/scenario precision (goal clarity, scenario realism)

Not allowed in later rounds:
- adding new features to the panorama without decision pressure
- redrawing the entire structure from scratch
- adding new personas beyond the established set
- style-only rewriting

### Per-round evidence requirement
Each round must record: what was refined, alternatives compared, trade-offs clarified, stress test improvement, freeze/continue/return/block rationale

## 4. Process Checkpoints

### Structure checkpoints
- Checkpoint 1:
  - a whole-picture structure exists
- Checkpoint 2:
  - goals, activities, tasks, and constraints are distinct
- Checkpoint 3:
  - the main flow/backbone is visible
- Checkpoint 4:
  - at least one high-risk validation point is explicit

### Analysis depth checkpoints
- Checkpoint 5:
  - stakeholder list exists with key profiles and adoption chain
- Checkpoint 6:
  - at least 3 key business scenarios have scenario-challenge-solution analysis
- Checkpoint 7:
  - primary persona exists with behavioral goals and context scenario
- Checkpoint 8:
  - design requirements are expressed as interaction outcomes (not feature lists)

### Reasoning quality checkpoints
- Checkpoint 9:
  - chosen structure rationale exists and explains why meaningful alternatives were not selected
- Checkpoint 10:
  - constraints have been stress-tested (not just listed) with interpretation rationale
- Checkpoint 11:
  - priority split has analytical rationale (not just grouping)
- Checkpoint 12:
  - structure stress-test has been applied and passed (Stage-03 can slice without rebuilding)

### Confirmation and provisional rules
- Fields that require confirmation or explicit review-bound status:
  - user boundary assumptions inherited from Stage-01
  - goal direction assumptions that materially affect priority split
  - hard constraints if still weakly evidenced
- Fields allowed as provisional only:
  - first-pass priority grouping
  - first-pass structure around still-unconfirmed user assumptions

## 5. Referenced Method Assets
- Required cards:
  - whole-picture structure thinking
  - story-map construction
  - structured requirements-analysis pattern
  - value/evidence discipline before flattening into tasks
  - structure-alternative reasoning and boundary-choice discipline
  - `effective-requirements-analysis` ch4-5: stakeholder identification + stakeholder profile analysis
  - `effective-requirements-analysis` ch9-10: business process identification (main/variant/supporting/management flow boundaries)
  - `effective-requirements-analysis` ch12-13: business scenario identification + scenario-challenge-solution analysis
  - `about-face-4` persona construction: behavioral archetype with goals (life → experience → end goals), not demographic labels
  - `about-face-4` scenario construction: context scenarios (day-in-the-life) + key-path scenarios (end-to-end interaction traces)
  - `about-face-4` design-requirements-are-not-features: interaction outcomes, not UI specifications
- Optional cards:
  - consensus-building through exploration
  - user-story 3C support if needed for articulation
  - `product-demand-fit` insight-to-org-adoption: how research findings translate to organizational action
- Boundary / anti-pattern cards:
  - do not reduce the panorama into a card pile
  - do not confuse structure with validated truth
  - do not confuse personas with demographic segments — personas are behavioral archetypes
  - do not confuse scenarios with use cases — scenarios describe desired experience, not system behavior
  - do not confuse design requirements with features — "show a dashboard" is a feature; "assess current workflow status within 30s" is a design requirement

## 6. Output Generation Rules
- Required outputs:
  - structured requirements analysis note
  - story map or equivalent structure artifact
  - key constraints list
  - initial priority split
  - NFR initial identification scan
  - structure rationale
  - stakeholder list + key stakeholder profiles
  - key business scenario analysis (at least 3 scenarios with scenario-challenge-solution depth)
  - persona set (at least 1 primary, 1 secondary) with context scenarios
  - design requirements extracted from personas/scenarios
- Minimum output rule:
  - Stage-03 must be able to slice from this output without rebuilding the whole structure from scratch
- Prototype / diagram rule:
  - a structure artifact is required
  - valid types are `story-map` or `requirements-structure`
  - optional additional diagrams: `business-process-flow`, `business-scenario-map`
- Provenance / assumptions marking rule:
  - any provisional structure assumptions must keep status, source, confidence, verification, and assumptions_to_validate fields
- Reasoning capture rule:
  - when Stage-02 compares structure options, interprets constraints, or chooses a priority split, preserve that reasoning in the output template's Section 3.2 (Reasoning Evidence)
  - the following items are REQUIRED, not optional:
    - structure alternatives comparison (at least 2 candidates with assessment)
    - backbone flow rationale
    - constraint stress-test outcomes
    - priority split reasoning
    - structure stress-test outcome
    - deepening loop log
    - stakeholder analysis evidence (why these stakeholders matter, key conflicts)
    - business scenario analysis evidence (why these scenarios are critical, what other scenarios were deprioritized and why)
    - persona/scenario construction evidence (what research data supports this persona, what scenarios cover the critical paths)
- Diagram obligation / fail action:
  - `diagram_obligation: required`
  - fail back to Stage-02 step-1 or Stage-01 if the panorama cannot be justified from available understanding

## 7. Stage Acceptance
- Minimum completion standard:
  - whole-picture structure exists
  - main flow/backbone is visible
  - goals, activities, tasks, and constraints are distinct
  - key constraints list exists and constraints are stress-tested
  - NFR initial identification scan exists and covers at least dimension relevance and information state
  - initial priority split exists with analytical rationale
  - chosen structure rationale exists with alternatives comparison
  - reasoning evidence section is populated (Section 3.2 of output template)
  - structure stress-test has been applied
  - stakeholder analysis exists (key stakeholders identified with profiles and adoption chain)
  - key business scenarios have scenario-level analysis (at least 3 with scenario-challenge-solution)
  - primary persona exists with behavioral goals and context scenario
  - design requirements are extracted from personas/scenarios (not just feature lists)
  - Stage-02b-consumable or Stage-03-consumable handoff exists
- Common failure signals:
  - only stories/tasks with no panorama
  - no constraint visibility
  - pretty diagram without analytical structure
  - no explanation of why this structure was chosen over alternatives
  - Stage-01 provisional uncertainty silently disappears
  - constraints listed but not stress-tested
  - no NFR initial identification despite downstream dependency on NFR awareness
  - priority split without analytical reasoning
  - no deepening loop log
  - stakeholders listed but not analyzed (no profiles, no conflict identification)
  - business scenarios identified but not analyzed (no scenario-challenge-solution depth)
  - personas are demographic labels instead of behavioral archetypes with goals
  - scenarios describe features instead of user experience
  - design requirements are feature lists disguised as requirements
- Return path:
  - return to clarification or back to Stage-01 if shared understanding is not strong enough
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if no defensible whole-picture structure can be built under the current evidence boundary

## 8. Handoff Rules
- Handoff target:
  - `requirements-specification-deepening` (Stage-02b) if Stage-02b exists in the pipeline
  - `requirements-decomposition-and-mvp-slicing` (Stage-03) if Stage-02b is skipped
- Handoff package:
  - structured requirements analysis note
  - story map / equivalent structure artifact
  - key constraints list
  - initial priority split
  - NFR initial identification scan
  - structure rationale
  - high-risk validation point
  - stakeholder list + key stakeholder profiles
  - key business scenario analysis (scenario-challenge-solution)
  - persona set with context scenarios and key-path scenarios
  - design requirements extracted from personas/scenarios
  - assumptions / open questions where still needed
- Handoff explanation requirement:
  - explain the main flow, the main boundary, the main constraint, the highest-risk validation point, and why this structure was chosen
  - explain the primary persona and the main context scenario
  - explain which business scenarios received deep analysis and which were deferred
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound input, never as silently confirmed fact
