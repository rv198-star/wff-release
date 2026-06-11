# The Art of Unit Testing — Index Map

## Scope

- Source file:
  - `sources/books/original/phase-03-development/the-art-of-unit-testing.md`
- Extraction depth:
  - `index-map -> knowledge-card-draft -> stage-guidance-draft`
- Book type judgment:
  - `method-heavy`
  - `system / engineering-governance support`
- Primary Stage focus:
  - `development`
  - `testing`
- Current downstream target:
  - Phase-3 implementation/development stage package
  - Phase-3 contract/testability/coding-baseline design

## Section map (organized by use)

| Section (by use) | Core problem solved | Stage | Type | Priority |
|---|---|---|---|---:|
| Unit test quality pillars | Defines what makes tests trustworthy, maintainable, readable | development | concept / checklist | very high |
| Breaking dependencies for testability | Shows how to make production code testable by extracting interfaces and injecting fakes | development | method / design-for-testability | very high |
| Mocks, stubs, and interaction boundaries | Clarifies when interaction testing helps and how overspecification creates brittle tests | development | boundary / anti-pattern | very high |
| Test organization and test API | Gives structure for mapping tests to code, build integration, and reusable test support code | development | method / organization | high |
| Legacy code test introduction | Provides entry strategies for adding tests before or during refactoring | development | method / risk | high |
| Design and testability | Turns testability into explicit design goals and tradeoffs | development | principle / boundary | very high |
| Org adoption of unit testing | Explains change-management patterns for adopting unit testing across teams | development | governance / rollout | medium |

## Planned card clusters

- good-unit-tests-have-trustworthy-maintainable-readable-pillars
- extract-interfaces-and-inject-dependencies-to-enable-unit-tests
- one-mock-per-test-helps-avoid-multi-concern-brittleness
- avoid-overspecification-and-test-logic-in-tests
- map-tests-by-speed-type-and-code-under-test
- add-tests-to-legacy-code-with-selection-strategy-and-pre-refactor-safety
- design-for-testability-by-avoiding-hard-wired-dependencies
