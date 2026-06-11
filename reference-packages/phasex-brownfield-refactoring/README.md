# Brownfield / Refactoring Skill Package (PhaseX Wave-1)

## 1. What this is

This directory is the current **PhaseX Wave-1** authored package set for brownfield entry, legacy takeover, technical refactoring, and bounded change-on-existing-codebase work.

It is intentionally narrower than the full `PhaseX` 10-skill blueprint.

Current Wave-1 includes only:

- `PX-SK-01 codebase-baseline-extraction`
- `PX-SK-04 technical-health-assessment`
- `PX-SK-07 safety-net-test-construction`
- `PX-SK-06 gap-analysis-and-change-decomposition` in `partial` mode

This package exists so the repository has a real, runnable PhaseX entry path instead of only planning prose.

## 1.1 Method Backbone

Wave-1 is small, but it should still stand on explicit refactoring discipline rather than generic “debt cleanup” language.

Current backbone:

- `docs/phases/phase-x/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/`
- `sources/books/extracted/the-art-of-unit-testing/`

The key absorbed ideas for the `technical-refactor` path are:

- refactoring means behavior-preserving structural change
- feature work and refactor work must not be mixed invisibly
- self-testing tests come before risky structural change
- long-running replacements need bounded strategies such as Branch by Abstraction

## 2. What each package answers

### PX-SK-01: codebase-baseline-extraction

Answers:

- what codebase surfaces exist now
- how modules, routes, jobs, and entrypoints are currently shaped
- what technical stack and runnability posture the system has
- whether the codebase already hints at third-party dependencies that downstream stages must not rediscover manually
- what is observed code evidence, what is Agentic brownfield inference, and what must remain unknown

### PX-SK-04: technical-health-assessment

Answers:

- where the technical risk is highest
- which debt items should be treated as immediate blockers
- whether the system is safe enough to change without more protection first
- which risk maps to which action, with evidence and claim ceiling

### PX-SK-07: safety-net-test-construction

Answers:

- what must be protected before refactoring
- which tests should be added first
- how brownfield compatibility will be checked during change
- whether implementation is blocked, guarded, or protected enough to start

### PX-SK-06 partial: gap-analysis-and-change-decomposition

Answers:

- what the bounded change point is
- which modules and interfaces are affected
- which legacy scope is explicitly out of bounds for this round
- whether the next move should re-enter Phase-1 or go directly to Phase-3
- what P1 and P3 should consume differently from the same brownfield handoff

## 3. Asset shape

Each Wave-1 package currently contains the minimal runtime 4-pack:

- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

Wave-1 intentionally does not copy the full heavy control/audit stack used by mature Phase-1/2/3/4 tracks.

Wave-1 follows the v1.3.10 control boundary:

- Workflow controls profile, order, scaffold, output set, and minimum validation.
- Agentic controls brownfield meaning, risk judgment, safety-net strategy, and downstream route rationale.
- Evidence caps claims with code references, command/test evidence, unknowns, and confidence.

The validator checks that reviewable surfaces exist. It does not score or decide brownfield truth.

## 4. How to use it

Use the official entry skill:

- `skills/wff-x/`

Then scaffold a fresh case root:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir tmp/local-artifacts/<case-name>/phase-x \
  --profile <assessment-only|technical-refactor|partial-change> \
  --version <vN>
```

The scaffolded case root will include:

- `phasex-wave1-manifest.md`
- one markdown target per selected Wave-1 package

After authoring, validate the case root:

```bash
python3 scripts/phasex/validate_phasex_case.py \
  --output-dir tmp/local-artifacts/<case-name>/phase-x
```

Review guidance:

- `docs/phases/phase-x/phaseX-wave1-self-audit-guide-v0.1.md`

## 5. Profile mapping

### `assessment-only`

Use:

- `PX-SK-01`
- `PX-SK-04`

### `technical-refactor`

Use:

- `PX-SK-01`
- `PX-SK-04`
- `PX-SK-07`

### `partial-change`

Use:

- `PX-SK-01`
- `PX-SK-06 partial`

## 6. Boundary

This package is not:

- a new default Phase-5
- a replacement for P1-P4
- a full migration-orchestration skill set

Its job is narrower:

> tell the truth about the current brownfield system, surface technical risk, protect the system before change, and produce a clean handoff back into the main lifecycle

## 7. One-line summary

This directory is the minimum useful PhaseX package set: honest brownfield entry without pretending every legacy case already deserves a full 10-skill orchestration stack.
