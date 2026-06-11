# wff-x-plan-test-protection Source Cards — plan-test-protection

## Required source bundles

- `wff-x-scan-code-baseline` baseline extraction output

## Preferred source bundles

- `wff-x-scan-tech-health` health assessment
- current test suite
- API contracts or interface docs
- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/stage-guidance-draft.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/refactor-requires-self-testing-tests-and-fast-feedback-loop.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/keep-system-working-via-small-steps-avoid-debugging-by-design.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/cards-draft/branch-by-abstraction-for-long-running-refactors.md`
- `sources/books/extracted/the-art-of-unit-testing/stage-guidance-draft.md`

## Optional support

- defect history
- incident reports
- replay logs

## Anti-pattern cards

- proposing end-to-end tests for everything without prioritization
- calling a module protected because low-value tests exist
- ignoring contract or smoke coverage for high-blast-radius interfaces
- treating safety-net planning as a backlog instead of a go / no-go protection strategy
- starting refactor work without naming must-have protections first
- allowing a long-running replacement without any abstraction-based migration strategy
