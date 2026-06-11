# Stage-02 Runtime Decision Log — domain-module-service-decomposition

## 1. Pilot Scope

This file records a lightweight runtime-style decision trace for the Stage-02 pilot.

## 2. Case A — brownfield naming conflict but usable decomposition basis
- input summary:
  - Stage-01 package exists, boundary is stable, but a legacy `TaskService` name overlaps with the newly proposed `ReviewModule`
- entered state:
  - `S0 Intake Received`
- transition:
  - `S0 Intake Received` -> `S1 Clarification Active`
- decision reason:
  - decomposition can proceed, but ownership and name mapping must stay explicit
- next transition:
  - `S1 Clarification Active` -> `S3 Provisional Inference` -> `S4 User Review`
- gate outcome:
  - provisional pass allowed only with explicit name-mapping note and ownership non-overlap confirmation

## 3. Case B — hidden ownership overlap
- input summary:
  - request says "put review logic in every service so teams can stay flexible"
- entered state:
  - `S1 Clarification Active`
- transition:
  - `S1 Clarification Active` -> `S2 Blocked`
- decision reason:
  - hidden ownership overlap would make lifecycle closure and dependency boundaries non-defensible
- next transition:
  - remain blocked until one owning module / service boundary is made authoritative
- gate outcome:
  - no Stage-03 handoff allowed

## 4. Case C — review re-entry after ownerless lifecycle proposal
- input summary:
  - decomposition draft is structurally rich, but a read-only review module is still asked to write upstream truth
- entered state:
  - `S4 User Review`
- transition:
  - `S4 User Review` -> `S1 Clarification Active`
- decision reason:
  - package must re-enter decomposition clarification rather than overclaim completion
- next transition:
  - `S1 Clarification Active` -> `S5 Gate Pass` only after lifecycle/write ownership is remodeled
- gate outcome:
  - review re-entry required before pass
