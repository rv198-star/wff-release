# Stage-04 Skill Contract — design-convergence-and-delivery-prototype

## 1. Skill Goal
- Converge Stage-01~03 outputs into a delivery-oriented design package with explicit readiness, unresolved risks, downstream handoff rules, and a coarse-grained implementation task sketch.

## 2. Inputs
- Required: Stage-01~03 outputs
- Required carryover detail:
  - Stage-03 scenario coverage matrix
  - Stage-03 technology selection evaluation matrix
  - Stage-03 dominant bottleneck hypothesis
  - Stage-03 architecture alternative candidate set
  - Stage-03 baseline insufficiency note
  - Stage-03 constraint-dominant optimum candidate
- Carryover fidelity rule:
  - each of the above Stage-03 carryover items must be referenced with at minimum: the core judgment or conclusion and the key evidence or reasoning it depends on; compressing any carryover item to a single-line conclusion without evidence basis = gate fail
  - Stage-04 convergence summary must not introduce optimality claims that lack Stage-03 evidence backing; any new claim introduced in Stage-04 must be explicitly marked as Stage-04 inference and not presented as inherited Stage-03 fact
- Optional: additional prototype/context constraints
- Missing-input handling: refuse/block when Stage-03 handoff is absent or unusable
- declaration-state rule: preserve `present | absent | unknown | deferred` semantics from upstream stages in the final convergence package

## 2.1 Intake and State Rules
- `cannot_infer`:
  - final delivery readiness without core design package evidence
  - final optimality claim without dominant-bottleneck and alternatives evidence
  - readiness wording that exceeds current verification, confidence, or realizability evidence
  - convergence closure while lifecycle ownership, command-boundary, or public-name contradictions remain unresolved
- `can_provisionally_infer`:
  - first-pass convergence summaries
  - coarse-grained implementation task slicing
- `must_validate_before_exit`:
  - downstream handoff consumability
  - multi-context P1 commitments disposed as exact operation sets retain explicit role/task-context coverage; any Agent-declared re-entry obligation has a role-visible read operation carrying the exact commitment authority
  - unresolved items visibility
  - structural contradictions across lifecycle ownership, command boundaries, and named public artifacts are resolved or explicitly downgraded in readiness judgment
  - all known business scenarios remain covered
  - critical public-boundary scenarios are explicit enough for implementation planning
  - critical_interaction_sequence_set is present with at minimum: one happy-path sequence and one blocked/failure-path sequence, each expressed as numbered step list, Mermaid sequence diagram, or equivalent structured form; narrative description alone does not satisfy this gate
  - every review-bound unresolved item is either: (a) assigned a named spike or validation work-package in implementation_task_sketch, or (b) explicitly annotated with "out of current phase scope" and a responsible party; floating unresolved items with no downstream ownership do not pass
  - implementation task sketch remains coarse-grained and public-boundary-consistent
  - implementation task sketch expresses effort realism with effort_basis, team assumption, and fte_breakdown rather than duration-only sizing
  - authentication / provider credential posture remains implementation-facing when auth vendor, token lifecycle, or secret rotation materially affect delivery realism
  - downstream onboarding support is explicit through a quick-start path and glossary/onboarding summary rather than assuming the next team already knows Phase-2 vocabulary
  - technology selection rationale and evidence trail remain visible
  - acceptable-vs-optimal review is explicit
  - chosen architecture is not just an unchallenged mainstream baseline
  - readiness claim is calibrated to verification, confidence, and realizability evidence
  - declaration-state and NFR truth boundary visibility
  - critical_interaction_sequence_set is present with at minimum: one happy-path sequence and one blocked/failure-path sequence, each expressed as a numbered step list, Mermaid sequence diagram, or equivalent structured form; narrative description alone does not satisfy this gate
  - every review-bound unresolved item is either: (a) assigned a named spike or validation work-package in implementation_task_sketch, or (b) explicitly annotated with "out of current phase scope" and a responsible party; floating unresolved items with no downstream ownership do not pass
  - at least one structured visual representation is present (Mermaid diagram, ASCII block diagram, or equivalent structured table view); if diagram_obligation=required and no visual representation exists, stage status must be downgraded to `blocked`, not `provisional` or `pass`

## 3. Execution Steps
1. aggregate Stage-01~03 outputs
2. resolve and record key design consistency points
3. consolidate scenario coverage across all known business scenarios
4. review dominant bottleneck, alternatives, and baseline insufficiency evidence
5. review technology selection rationale and evidence quality
6. produce delivery-prototype-oriented representation
7. produce critical interaction sequence set for key public-boundary scenarios
8. produce explicit optimality review
9. produce design verification notes
10. produce coarse-grained implementation task sketch plus staffing and rollback realism
11. close identity/auth vendor/token lifecycle posture where it changes implementation intake realism
12. assemble downstream handoff package and glossary/onboarding summary

## 4. Outputs
- converged design package
- prototype/structured convergence expression
- critical interaction sequence set
- optimality review
- verification notes
- realizability review with structural consistency gate and readiness calibration
- implementation task sketch
- identity and key management choice posture
- glossary or onboarding summary
- implementation-facing handoff package

## 5. Acceptance Criteria
- downstream can consume package without re-synthesizing Stage-01~03
- downstream can understand key public-boundary interactions without needing internal class/method design
- downstream can see a first-pass implementation slicing/work-package view without mistaking it for coding-level freeze
- downstream can see auth/vendor/token lifecycle posture when delivery realism depends on it
- downstream can onboard a new implementation squad without reverse-engineering Phase-2 terminology from scattered Stage outputs
- downstream can see why major technology choices were made and what evidence they depend on
- downstream can see why the chosen architecture beat the baseline rather than merely cleared the minimum bar
- downstream can see the strongest supported readiness level without overclaim beyond evidence
- unresolved and review-bound content is explicit
- declaration-state and NFR handling remain explicit in final handoff
- at least one structured visual representation is present (Mermaid diagram, ASCII block diagram, or equivalent structured table view); if diagram_obligation=required and no visual representation exists, stage status must be downgraded to `blocked`, not `provisional` or `pass`

## 6. Boundaries
- allow only coarse-grained implementation task sketch at slice/module/work-package level
- no coding-level breakdown
- no mandatory internal class, package, file, or method naming
- no readiness label stronger than the underlying verification/confidence/realizability evidence
- no silent carry-forward of lifecycle ownership, command-boundary, or public-name contradictions as if implementation-ready
- no silent fallback from stronger constraint-dominant candidate to mainstream baseline just because the baseline is easier to narrate
- no hiding unresolved design risks

## 7. Flow Rules
- handoff target: downstream implementation phase
- review-bound content consumption rule must be explicit
- preserve `present | absent | unknown | deferred` semantics in the implementation-facing package whenever ambiguity remains
- preserve the coarse-grained-only boundary for implementation task sketching whenever downstream detail is still intentionally open


## Stage-05 interaction handoff runtime

After the selected architecture/API inputs are frozen, use `scripts/phase2/interaction_generation.py` and the versioned neutral library, following `reference-packages/phase2-design-architecture/interaction-generation.md`. Generate the ten interaction sections independently from selected original IDs; keep explicit gaps, use at most two local diagnostic repairs, and preserve accepted sections. Code assembles patterns and provenance; the existing OMR then isolated SQR review the original subject. Retain the interaction-only freeze manifest SHA-256, call records, gaps and delegation rules for P3. This handoff neither certifies complete P2 nor permits current-cycle P1/P2 regeneration.


### Caller output limit and section repair

Use the shared D/P3 streaming call runtime (`common.bounded_model_call` and
`common.bounded_response_stream`). D prompts target about4,000 output tokens or less per section and brief reasoning; keep
60K request / 8K output / local schema depth at most three. Close at 8K estimated
output including reasoning; active cutoff is charged request upper bound + 8K,
with usage kind and estimator retained. Simplify a truncated section within at
most two repairs; still unsuccessful becomes T2 and other sections continue.
HTTP/stream errors consume the full request upper bound + 8K reservation, recorded
as `transport-error-upper-bound`; remote execution remains uncertain. Resend the
same section at most once, counting every dispatch; two transport failures in a
section leave T2 and other sections continue. The third transport error in the
run stops dispatch and requires an Owner report. Declared call/token/wall caps
still apply to resends; other unknown usage stops the run. This is finite network
recovery, not an extra semantic review or a reset of the section repair limit. Do not repeat reviewers or claim complete review after a rejected review; authorized bounded v2 closeout preserves explicit T2 review gaps.

When the complete interaction review would exceed 60K, `prepare_review_packets` keeps every accepted choice and explicit gap visible and batches the unchanged original facts by focus section. Execute all OMR packets, then the identical packets for isolated SQR. These are the existing two logical reviews; each packet is an actual call within the declared call/token/wall limits. Bind packet input and prompt digests plus every settled Journal call into the two receipts; code retains all findings and projects the review-bound verdict without another model judgment. The complete-review v1 freeze requires both original receipts. For an explicitly authorized bounded closeout, stop calls at the declared cap and use `freeze_bounded_interaction`: retain unchanged author sections and actual receipts, mark affected sections T2 for material findings or missing/rejected review coverage, and freeze v2 with explicit review gaps. No extra review, budget reset or accepted-section regeneration; this freeze does not claim completed review. P3 validates the same manifest and resolves retained gaps locally. Calibrated endpoint/model counting uses text delta events×1.02 plus1024 reasoning reserve and item framing; requests use ceil(UTF-8 bytes/2)+4000. Each completed call compares provider visible tokens; deviation>3% switches to bytes and reports. Changed endpoint/model requires recalibration. Completed usage is provider-measured; cutoff/transport error charges request estimate+8000.
