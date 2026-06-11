# Stage-01 Charter — architecture-definition-and-boundary-setting

## 1. Authoring Goal

- Target Stage Skill: `architecture-definition-and-boundary-setting`
- Parent phase: design / architecture
- Goal: convert the Phase-1 handoff into an explicit architecture entry package that freezes system boundary, inherited and inferred constraints, capability map, architecture direction, boundary-level security posture, capacity posture, and review-bound uncertainty for downstream decomposition.

## 2. Problem This Stage Must Solve

This stage does not perform domain/service decomposition yet. It is responsible for answering:

- what system boundary is in scope for the current delivery slice
- which upstream constraints are already evidenced versus still partial or unknown
- which capability structure best explains the intended system shape
- which architecture direction is acceptable enough to hand off into Stage-02
- which trust boundaries, sensitive edges, and access-control assumptions must already be visible at architecture-entry level
- which order-of-magnitude load and growth posture must already be visible so Stage-02 and Stage-03 do not inherit a scale vacuum
- which assumptions or open questions must stay review-bound instead of being flattened into false certainty

## 3. Upstream Inputs

- Phase-1 handoff package
- MVP boundary and validation conclusion
- key scenarios / main flow / experience loop summary
- known constraints and risks from Phase-1
- upstream declaration states for critical inputs, especially NFR state: `present | absent | unknown | deferred`

## 4. Downstream Handoff

- Downstream stage: `domain-module-service-decomposition`
- Minimum handoff package:
  - system boundary statement
  - inherited vs inferred constraints
  - security architecture sketch
  - capacity estimation
  - capability map
  - architecture direction and key decisions
  - Mermaid diagrams or explicitly marked placeholders
  - assumptions / open questions / review-bound items

## 5. Gate Focus

- Is the system boundary explicit rather than implied by product language alone?
- Are upstream declaration states consumed honestly instead of guessed over?
- Are NFR / quality concerns either inherited as evidenced constraints or expanded into architecture-facing structure, rather than silently treated as complete?
- Are boundary-level security posture and capacity posture explicit enough that later stages do not need to invent them from scratch?
- Does the output provide a decomposition-ready architecture entrypoint instead of jumping ahead into service/interface detail?

## 6. Diagram Focus

- Mermaid is required for Stage-01.
- Minimum diagram obligations:
  - one system-boundary/context representation
  - one capability-map or equivalent structured relationship view
- Placeholders are acceptable in dry-run/verification only when explicitly labeled as placeholders.

## 7. Current Authoring Boundary

- This round builds the Stage-01 control artifacts and runtime package.
- It does not yet author Stage-02 decomposition assets.
- It does not let TOGAF, SOMA, BPMN, or SOA-lite replace the current Stage-2 four-stage spine.
- It may reference sidecar/review lenses only where their boundary is made explicit.
