# PX-SK-01 Source Cards — codebase-baseline-extraction

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
- `docs/phases/phase-x/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/stage-guidance-draft.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/smell-to-action-trigger-sheet-for-refactoring-preparation.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/make-change-easy-then-make-easy-change-preparatory-refactoring.md`

## Anti-pattern cards

- treating brownfield truth as a directory summary instead of observed code evidence plus Agentic interpretation plus explicit unknowns
- pretending module ownership is known because directory names look neat
- reporting runnability as pass without naming startup blockers
- mixing current-state facts with target-state recommendations
- omitting outward surfaces because extraction feels tedious
- escalating a smell hint into a redesign claim before `PX-SK-04` validates it
