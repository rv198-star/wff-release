# PX-SK-06 Source Cards — gap-analysis-and-change-decomposition (partial)

## Required source bundles

- bounded change request
- `PX-SK-01` affected-slice baseline

## Optional support

- `PX-SK-04` health assessment
- API contracts
- stakeholder constraints
- defect or incident history
- `docs/phases/phase-1/product-requirements-stage-package-v0.md` §8.1
- `docs/phases/phase-2/p2-stage-optional-third-party-integration-design-v0.md`
- `docs/phases/phase-x/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`

## Anti-pattern cards

- using partial mode to smuggle in a full-system redesign
- dropping compatibility constraints because they are inconvenient
- routing straight to implementation when product-level ambiguity remains
- treating route choice as a field value without explaining why P1, P3, or protect-first is the honest next move
- writing vague “affected area” prose instead of naming concrete modules or surfaces
- mixing feature change and structural cleanup without saying which boundary goes to which downstream phase
