# wff-x-intake-target-driver SOP — target-driver-intake

## 1. Positioning

- goal: turn a bounded brownfield change into a downstream-ready package
- upstream: change request plus `wff-x-scan-code-baseline`
- downstream: Phase-1 constrained re-entry, Phase-2 architecture sidecar, Phase-3 direct implementation, or `wff-x-plan-test-protection` first

## 2. Start Conditions

- required: a real local change point exists
- required: affected slice has baseline extraction
- blocked: requested change is too broad or too ambiguous for target-driver profile

## 3. Standard Execution Steps

1. define the bounded change point
2. identify affected modules, surfaces, and dependencies
3. record compatibility constraints and brownfield invariants
4. mark brownfield non-goals so unchanged legacy scope does not silently reopen
5. if third-party integration is touched, carry forward `integration_change_type` and compatibility requirements
6. separate product-level reframing from pure technical work
7. create `PX Handoff Cards` for each takeover unit; these are not P3 implementation ActionCards
8. create `PX-to-P1 existing-system-change packet` when product demand, business target, affected user/workflow, or acceptance pressure must return to P1
9. add `PX-to-P1 Demand Clarification Addendum` as optional demand clarification evidence when answers exist; missing answers must not block P1
10. create `PX-to-P2 existing-system-architecture-change packet` when architecture, data, interface, integration, deployment, performance, or compatibility pressure must enter P2
11. explain whether the bounded change should `return-to-P1`, `enter-P2`, `protect-first`, `direct-to-P3`, or `decision-required`
12. record Phase-1, Phase-2, and Phase-3 consumption notes separately so downstream consumers know how to use the package
13. recommend the next lifecycle entry point

## 4. Process Checkpoints

- bounded change point is specific
- affected module list is non-empty
- impacted surfaces and acceptance anchors are explicit in the re-entry summary
- brownfield non-goals are named
- PX Handoff Cards name current facts, target driver, gap, evidence, unknowns, route, required prework, and claim ceiling
- PX-to-P1 packet uses `packet_subtype: existing-system-change`
- PX-to-P1 Demand Clarification Addendum is answer-backed when available and review-bound when not answered
- PX-to-P2 packet uses `packet_subtype: existing-system-architecture-change`
- at least one compatibility rule or invariant is stated when legacy behavior matters
- route decision rationale and compatibility claim ceiling are explicit
- next route is explicit

## 5. Output Rules

- keep the package local to the affected slice
- preserve uncertainty instead of broadening scope to look complete
- write downstream guidance in operational terms, not abstract commentary
- do not present legacy constraints as optional greenfield preferences
- do not use PhaseX internal skill names as the handoff contract for P1 or P2
- do not turn PX Handoff Cards into coding tasks; P3 implementation ActionCards remain P3-owned
- do not make owner or human confirmation a required gate; if no owner is available, preserve review-bound truth and route conservatively
- do not turn demand clarification into an approval gate; it is optional demand clarification evidence for P1

## 6. Stage Acceptance

- downstream consumers know what is changing, what cannot break, and where the case should go next
- Phase-1, Phase-2, and Phase-3 consumers can see what they are allowed to decide and what brownfield truth they must preserve
