# Stage-02 Charter — domain-module-service-decomposition

## 1. Authoring Goal
- Target Stage Skill: `domain-module-service-decomposition`
- Parent phase: design / architecture
- Goal: decompose Stage-01 boundary/capability outputs into domain, module, and service candidate structure with explicit responsibilities, dependencies, and decomposition-ready rationale.

## 2. Problem This Stage Must Solve
- how to partition capability structure into domain/module/service boundaries
- how responsibilities and dependencies are assigned without overlap
- how cross-boundary collaboration and ownership are explained
- how unresolved risks and review-bound items remain explicit

## 3. Upstream Inputs
- Stage-01 boundary/capability package
- Stage-01 constraints and architecture decisions
- upstream declaration states and NFR handling notes

## 4. Downstream Handoff
- Downstream stage: `data-storage-and-interface-design`
- Minimum handoff package:
  - domain map
  - module map
  - service candidates
  - dependency/collaboration map
  - decomposition decisions and rationale

## 5. Gate Focus
- is decomposition grounded in Stage-01 boundary/capability output?
- are responsibilities clear and non-duplicative?
- are dependency and ownership boundaries explicit?
- is decomposition usable for Stage-03 data/interface design?

## 6. Diagram Focus
- Mermaid is required.
- minimum diagrams:
  - domain/module/service structure view
  - dependency/collaboration view

## 7. Current Authoring Boundary
- this stage does not finalize data model details
- this stage does not finalize API contracts
- TOGAF/SOA-lite/SOMA/BPMN remain review/sidecar lenses only
