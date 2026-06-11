# wff-x-intake-target-driver Source Cards — target-driver-intake

## Required source bundles

- bounded change request
- `wff-x-scan-code-baseline` affected-slice baseline

## Optional support

- `wff-x-scan-tech-health` health assessment
- API contracts
- stakeholder constraints
- defect or incident history
- `docs/phases/phase-1/product-requirements-stage-package-v0.md` §8.1
- `docs/phases/phase-2/p2-stage-optional-third-party-integration-design-v0.md`
- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/define-refactoring-by-behavior-preservation-and-change-cost.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/two-hats-separate-feature-work-from-refactoring-work.md`

## Anti-pattern cards

- using target-driver profile to smuggle in a full-system redesign
- dropping compatibility constraints because they are inconvenient
- routing straight to implementation when product-level ambiguity remains
- treating route choice as a field value without explaining why P1, P3, or protect-first is the honest next move
- writing vague “affected area” prose instead of naming concrete modules or surfaces
- mixing feature change and structural cleanup without saying which boundary goes to which downstream phase
