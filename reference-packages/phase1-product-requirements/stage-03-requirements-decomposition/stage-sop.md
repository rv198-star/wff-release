# Stage-03 SOP — requirements-decomposition-and-mvp-slicing

## 1. Stage Positioning
- Stage name:
  - requirements-decomposition-and-mvp-slicing
- Stage goal:
  - convert the Stage-02a structural panorama and Stage-02b specification deepening into an explainable MVP boundary and slicing set
- Parent phase:
  - product / requirements
- Upstream dependency:
  - Stage-02a structured analysis outputs (panorama, stakeholder analysis, business scenarios, persona/scenario set)
  - Stage-02b specification deepening outputs (NFR, domain model, IA direction) — if Stage-02b exists
- Downstream target:
  - `requirements-validation-and-concept-proof`

## 2. Start Conditions
- Required inputs:
  - Stage-02a structured analysis note
  - story-map / equivalent structure artifact
  - key constraints list
  - goal direction
  - key business scenario analysis (from Stage-02a)
  - persona/scenario set with design requirements (from Stage-02a)
- Optional inputs:
  - initial priority split
  - review-bound provisional assumptions
  - Stage-02b NFR / quality requirements summary
  - Stage-02b conceptual domain model
  - Stage-02b IA direction decisions
- Pre-start checks:
  - is there a defensible whole-picture structure to slice from?
  - is the intended experience loop visible enough to define a minimum viable loop?
- Refusal rule:
  - refuse slicing if no whole-picture structure exists
- Clarification expansion rule:
  - clarify unresolved structure assumptions before declaring slice boundaries
- Enter `Blocked` when:
  - the proposed MVP boundary would depend on non-inferable missing fields
- Enter `Provisional Inference` when:
  - the team explicitly accepts a provisional slicing draft built on still-review-bound upstream structure

## 3. Standard Execution Steps
1. Confirm the upstream panorama and its uncertainty boundary.
   - Check Stage-02a outputs: structural panorama, stakeholder analysis, business scenarios, persona/scenario set, design requirements
   - Check Stage-02b outputs (if available): NFR summary, domain model, IA direction
   - If Stage-02b is missing, record as gap: "NFR and domain model not available — slicing decisions will lack specification-grade constraints"
   - Identify which Stage-02b outputs (if present) materially constrain slicing decisions
   - **Micro-checkpoint**: Is the upstream panorama complete enough to slice from? Are Stage-02b gaps documented?
2. Identify the complete experience loop.
   - **Revalidate the value loop**: Before defining the complete experience loop, revalidate the value loop from Stage-02a in the context of slicing — does the value loop still hold when decomposed into sliceable activities? If the value loop from Stage-02a needs adjustment for slicing purposes, document the adjustment and rationale.
3. Cut the minimum viable experience loop.
   - **Micro-checkpoint**: Is the MVP a complete loop (not just reduced scope)? What would break viability if one more thing were removed?
4. Compare meaningful slice options when ambiguity still matters.
   - Generate 2-3 candidate slice strategies; for each assess: user value speed, evidence confidence, dependency complexity, validation leverage, risk of overreach
   - **NFR-aware slicing**: if Stage-02b NFR summary is available, check whether any quality attributes (e.g., security, data isolation, performance) force capabilities into the first slice or constrain slice ordering
   - **Value-frequency prioritization** (supplementary dimension): for capabilities competing for first-slice inclusion, assess both value (how important) and frequency (how often used) — high-value + high-frequency items are strongest first-slice candidates; high-value + low-frequency items may be deferred
   - Select with explicit `why-this-slice-not-that` rationale
   - **Micro-checkpoint**: Does the output contain at least 2 slice candidates + comparison + selection rationale? Are NFR constraints reflected in the slice decision?
5. Separate first slice, later slices, and deferred items.
   - For each deferred item, apply honesty check: why not in MVP? What would falsely make MVP look more complete? Impact of deferral?
6. Compile explicit epic decomposition.
   - Group first-wave stories/use cases under stable epics rather than leaving only a flat story list
   - Each epic must express the user value it protects and the downstream architecture pressure it creates
7. Run a story quality pass using `INVEST`.
   - Assess the primary story and supporting use cases for `Independent / Negotiable / Valuable / Estimable / Small / Testable`
   - Record visible risk/gap notes instead of silently assuming all stories are implementation-ready
8. Translate stories/use cases into explicit first-wave requirements.
   - Classify each requirement as `functional_requirement`, `governance_constraint`, or `quality_or_compliance_constraint`
   - Do not mix user-facing product behavior and governance guardrails into an undifferentiated requirement list
9. Compile acceptance-boundary coverage for implementation-facing stories.
   - Express key acceptance items in `Given / When / Then`
   - Mark critical-path or high-risk acceptance items as `anchor`; lighter supporting checks may remain `supporting`
   - Anchor ACs should carry an explicit `expected_outcome` or equivalent observable success signal
   - Make boundary cases explicit: permission edge, missing input, invalid state, threshold breach, recovery/retry, or equivalent domain edges
   - Do not let downstream implementation invent the first boundary-condition set from scratch
10. Compile a **Source Feature Carryover Ledger**.
   - For each detailed source feature that does not appear verbatim in the MVP boundary, classify it as:
     - `first-wave abstraction`
     - `later slice`
     - `deferred seam`
     - `explicit out-of-scope`
   - No important source feature may silently disappear once slicing begins.
11. Explain the slicing logic through value, risk, dependency, and why-this-not-that reasoning.
12. Preserve still-unresolved assumptions explicitly.
13. Assemble reasoning evidence into output template Section 3.2.
14. Record which required method families from `source-cards.md` were materially applied to choose the slice.

## 3.1 Intake / Clarification / Review State Flow
- `S0 Intake Received`:
  - inspect the Stage-02 package and identify slicing readiness
- `S1 Clarification Active`:
  - clarify unresolved structure or dependency assumptions before slicing locks in
- `S2 Blocked`:
  - stop if the slice boundary would be fabricated from non-inferable missing fields
- `S3 Provisional Inference`:
  - allow only review-bound provisional slicing drafts
- `S4 User Review`:
  - review slice boundaries, deferred items, and core assumptions
- `S5 Gate Pass`:
  - pass only when Stage-04 can validate the proposed MVP and assumptions coherently
- `S6 Escalate`:
  - escalate if the slicing decision cannot be defended under the current evidence boundary

## 4. Process Checkpoints
- Checkpoint 1:
  - the complete experience loop is explicit
- Checkpoint 2:
  - the MVP loop is smaller than the full experience but still viable
- Checkpoint 3:
  - at least two slices or equivalent first/later segmentation are explicit
- Checkpoint 4:
  - deferred items are explicit and justified
- Checkpoint 4b:
  - source feature carryover ledger exists and no critical source feature has silently vanished
- Checkpoint 4c:
  - epic decomposition exists and first-wave stories/use cases are not flat/unowned
- Checkpoint 4d:
  - `INVEST` evaluation exists for the primary story and supporting use cases
- Checkpoint 4e:
  - acceptance-boundary coverage exists with `Given / When / Then` and visible boundary cases
- Checkpoint 4f:
  - requirements are visibly classified instead of mixing functionality and governance into one flat list
- Checkpoint 4g:
  - anchor ACs are explicit for the critical path or highest-risk edges when implementation-ready depth is claimed
- Checkpoint 5:
  - key assumptions to validate are carried forward to Stage-04
- Checkpoint 6:
  - chosen slice rationale exists and explains why alternative slice strategies were not selected
- Checkpoint 7:
  - required slicing method families were materially applied and reflected in the rationale
- Fields that require confirmation or explicit review-bound status:
  - high-impact slice-order assumptions
  - dependencies that materially affect what can be in the first slice
  - value-priority assumptions inherited from Stage-02
- Fields allowed as provisional only:
  - first-pass slice boundaries
  - first-pass acceptance targets
  - first-pass epic grouping if still clearly marked review-bound

## 5. Referenced Method Assets
- Required cards:
  - MVP slicing by story-map
  - early-value delivery thinking
  - structured decomposition discipline
  - slice-option comparison and deferral-honesty discipline
  - `effective-requirements-analysis` value-frequency-prioritization: assess both value and frequency when comparing slice candidates
- Optional cards:
  - refinement/workshop support
  - value-flow efficiency support
  - `effective-requirements-analysis` quality-attribute-in-slicing: consider NFR constraints when drawing slice boundaries
- Boundary / anti-pattern cards:
  - do not confuse “smaller scope” with “minimum viable loop”
  - do not hide deferred items
  - do not pretend validation has already happened
  - do not ignore NFR constraints when they materially affect what must be in the first slice

## 6. Output Generation Rules
- Required outputs:
  - MVP definition
  - release slicing explanation
  - decomposition structure note
  - slice rationale
- Minimum output rule:
  - Stage-04 must be able to validate the proposed MVP and assumptions without re-deriving the slice logic from scratch
- Prototype / diagram rule:
  - a slice-map or equivalent slice structure artifact is required
  - it must show slices, boundaries, acceptance targets, and key dependencies
- Provenance / assumptions marking rule:
  - any provisional slicing assumptions must keep status, source, confidence, verification, and assumptions_to_validate fields
- Reasoning capture rule:
  - when Stage-03 compares slice options, justifies the MVP loop, or keeps items deferred, preserve that reasoning in the output template's Section 3.2 (Reasoning Evidence)
  - the following items are REQUIRED: slice alternatives comparison, MVP loop viability test, deferred items honesty check, deepening loop log
  - source feature carryover ledger is also REQUIRED whenever the source package contains detailed capability or page-function language
  - method activation evidence is also REQUIRED: identify which source-card method families shaped the slice choice and deferral logic
- Diagram obligation / fail action:
  - `diagram_obligation: required`
  - fail back to Stage-03 loop/slicing work; if the loop itself cannot be defended, return to Stage-02 structure clarification

## 7. Stage Acceptance
- Minimum completion standard:
  - a minimum viable experience loop exists
  - first / later / deferred items are explicit
  - source feature carryover ledger is explicit
  - slice logic is explainable
  - chosen slice rationale exists
  - slice-map evidence exists
  - Stage-04-consumable handoff exists
- Common failure signals:
  - only a phased backlog list
  - no viable loop, only reduced scope
  - no deferred items
  - source features silently disappear during slicing
  - no dependency logic
  - no explanation of why this slice boundary was chosen over alternatives
  - required method families are listed in `source-cards.md` but leave no trace in the actual slice rationale
  - unresolved uncertainty silently flattened into confidence
- Return path:
  - return to slicing clarification or upstream structure clarification if needed
- State return rule on failure:
  - go back to `S1 Clarification Active` or `S2 Blocked`
- Escalation rule:
  - escalate if no defensible MVP boundary can be formed under the current evidence boundary

## 8. Handoff Rules
- Handoff target:
  - `requirements-validation-and-concept-proof`
- Handoff package:
  - MVP definition
  - slice explanation
  - slice-map / equivalent structure artifact
  - slice rationale
  - key assumptions to validate
  - deferred items and rationale
- Handoff explanation requirement:
  - explain the minimum viable loop, why first-slice items were chosen, why deferred items stayed out, what alternatives were rejected, and what validation should focus on
- Provisional content in handoff:
  - allowed only if explicitly labeled
- Whether downstream may consume provisional content:
  - yes, but only as review-bound validation input, never as silently confirmed fact
