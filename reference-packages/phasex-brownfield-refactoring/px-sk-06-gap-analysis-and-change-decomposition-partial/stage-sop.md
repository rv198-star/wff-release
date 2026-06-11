# PX-SK-06 SOP — gap-analysis-and-change-decomposition (partial)

## 1. Positioning

- goal: turn a bounded brownfield change into a downstream-ready package
- upstream: change request plus `PX-SK-01`
- downstream: Phase-1 constrained re-entry, Phase-3 direct implementation, or `PX-SK-07` first

## 2. Start Conditions

- required: a real local change point exists
- required: affected slice has baseline extraction
- blocked: requested change is too broad or too ambiguous for partial mode

## 3. Standard Execution Steps

1. define the bounded change point
2. identify affected modules, surfaces, and dependencies
3. record compatibility constraints and brownfield invariants
4. mark brownfield non-goals so unchanged legacy scope does not silently reopen
5. if third-party integration is touched, carry forward `integration_change_type` and compatibility requirements
6. separate product-level reframing from pure technical work
7. explain whether the bounded change should return to Phase-1, go direct to Phase-3, or protect first
8. record Phase-1 and Phase-3 consumption notes separately so downstream consumers know how to use the package
9. recommend the next lifecycle entry point

## 4. Process Checkpoints

- bounded change point is specific
- affected module list is non-empty
- impacted surfaces and acceptance anchors are explicit in the re-entry summary
- brownfield non-goals are named
- at least one compatibility rule or invariant is stated when legacy behavior matters
- route decision rationale and compatibility claim ceiling are explicit
- next route is explicit

## 5. Output Rules

- keep the package local to the affected slice
- preserve uncertainty instead of broadening scope to look complete
- write downstream guidance in operational terms, not abstract commentary
- do not present legacy constraints as optional greenfield preferences

## 6. Stage Acceptance

- downstream consumers know what is changing, what cannot break, and where the case should go next
- Phase-1 and Phase-3 consumers can both see what they are allowed to decide and what brownfield truth they must preserve
