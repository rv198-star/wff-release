# Stage-04 Charter — design-convergence-and-delivery-prototype

## 1. Authoring Goal
- Target Stage Skill: `design-convergence-and-delivery-prototype`
- Parent phase: design / architecture
- Goal: converge Stage-01~03 design outputs into a delivery-oriented architecture package, prototype expression, and coarse-grained implementation handoff sketch that is implementable, reviewable, and handoff-ready.

## 2. Problem This Stage Must Solve
- how to synthesize architecture/decomposition/data/interface outputs into one coherent package
- how to expose unresolved risks and review-bound assumptions clearly
- how to provide delivery-facing prototype/structure evidence without pretending implementation is complete
- how to preserve dominant-bottleneck reasoning and explain why the final architecture is better than the baseline
- how to sketch near-term implementation slices without freezing internal class, method, file, or ticket-level design

## 3. Upstream Inputs
- Stage-01~03 packages
- unresolved and review-bound items from prior substages

## 4. Downstream Handoff
- Downstream stage: `implementation-phase`
- Minimum handoff:
  - converged architecture package
  - delivery prototype summary
  - optimality review
  - design verification notes
  - coarse-grained implementation task sketch
  - implementation-facing handoff checklist

## 5. Gate Focus
- are Stage-01~03 outputs coherently converged?
- are conflicts/gaps explicit?
- is handoff package implementation-consumable?
- are declaration-state and NFR truth-boundary semantics still explicit in the final package?
- is the chosen architecture justified as stronger than the default baseline under the dominant constraint?
- does the implementation task sketch stay at work-package level rather than collapsing into coding-level freeze?

## 6. Diagram Focus
- Mermaid required
- minimum diagrams:
  - end-to-end architecture synthesis view
  - critical execution/interaction flow summary

## 7. Current Authoring Boundary
- this stage may provide only coarse-grained implementation task sketching
- this stage does not replace downstream implementation planning
- this stage does not hide unresolved design uncertainty
