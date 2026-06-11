# wff-x-scan-code-baseline Source Cards — scan-code-baseline

## Required source bundles

- repository tree
- dependency manifests
- runtime or build config

## Optional support

- README / ops docs
- deployment scripts
- API specs
- CI config
- secrets / env-var samples that hint at vendor integration
- SDK client wrappers or outbound HTTP utilities
- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/stage-guidance-draft.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/smell-to-action-trigger-sheet-for-refactoring-preparation.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/make-change-easy-then-make-easy-change-preparatory-refactoring.md`

## Downstream alignment cards

- P2 is the primary consumer for architecture constraints and boundary hints.
- P3 receives seed material only; formal ActionCards remain a P3 responsibility.

## Anti-pattern cards

- treating brownfield truth as a directory summary instead of observed code evidence plus Agentic interpretation plus explicit unknowns
- pretending module ownership is known because directory names look neat
- reporting runnability as pass without naming startup blockers
- mixing current-state facts with target-state recommendations
- omitting outward surfaces because extraction feels tedious
- escalating a smell hint into a redesign claim before `wff-x-scan-tech-health` validates it
- emitting ActionCards or implementation instructions from `wff-x-scan-code-baseline`
