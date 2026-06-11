# Brownfield / Refactoring Skill Package (PhaseX)

## 1. What this is

This directory is the current **PhaseX** authored package set for brownfield entry, legacy takeover, technical refactoring, and bounded change-on-existing-codebase work.

Wave-1 remains the runnable entry path. Wave-2 is now open as a staged package-expansion line, not as a replacement for Wave-1 or a default Phase-5.

Current Wave-1 includes only:

- `wff-x-scan-code-baseline scan-code-baseline`
- `wff-x-scan-tech-health scan-tech-health`
- `wff-x-plan-test-protection plan-test-protection`
- `wff-x-intake-target-driver target-driver-intake` as the `target-driver` profile

This package exists so the repository has a real, runnable PhaseX entry path instead of only planning prose.

## 1.1 Wave-2 expansion line

Wave-2 is split into practical tranches:

### First tranche: baseline completion

- `wff-x-scan-db-baseline scan-db-baseline`
- `wff-x-scan-biz-arch scan-biz-arch`

This tranche exists to complete AS-IS baseline coverage before target design, GAP, refactor strategy, or migration strategy are opened.

Output-contract alignment:

- `wff-x-scan-code-baseline / wff-x-scan-db-baseline` primarily align to P2. They may produce small P3 seed material, but not P3 ActionCards or implementation truth.
- `wff-x-scan-biz-arch` primarily aligns to P1. It may provide secondary P2 boundary and invariant hints.

### Later Wave-2 tranche queue

- `wff-x-design-target-arch design-target-arch`
- `wff-x-plan-refactor plan-refactor`
- `wff-x-plan-migration plan-migration`

`outer-boundary concern` is not a standalone target in the current v1.4 plan. Its useful outer-boundary / validation concerns are folded into `wff-x-design-target-arch` unless later case pressure proves a narrower separate slice is needed.

## 1.2 Method Backbone

Wave-1 is small, but it should still stand on explicit refactoring discipline rather than generic “debt cleanup” language.

Current backbone:

- `docs/source-registers/phaseX-source-library-seed-v0.1.md`
- `sources/books/extracted/refactoring-improving-the-design-of-existing-code/`
- `sources/books/extracted/the-art-of-unit-testing/`

The key absorbed ideas for the `technical-refactor` path are:

- refactoring means behavior-preserving structural change
- feature work and refactor work must not be mixed invisibly
- self-testing tests come before risky structural change
- long-running replacements need bounded strategies such as Branch by Abstraction

## 2. What each package answers

### wff-x-scan-code-baseline: scan-code-baseline

Answers:

- what codebase surfaces exist now
- how modules, routes, jobs, and entrypoints are currently shaped
- what technical stack and runnability posture the system has
- whether the codebase already hints at third-party dependencies that downstream stages must not rediscover manually
- what is observed code evidence, what is Agentic brownfield inference, and what must remain unknown
- what P2 can consume as architecture constraints and what P3 may treat only as seed material

### wff-x-scan-db-baseline: scan-db-baseline

Answers:

- what data architecture exists now
- which tables, entities, relationships, constraints, indexes, and sensitive fields are visible
- which database truths are observed, inferred, or unknown
- what P2 must preserve as data / storage / interface constraints
- which migration or persistence hotspots are only P3 seed material

### wff-x-scan-tech-health: scan-tech-health

Answers:

- where the technical risk is highest
- which debt items should be treated as immediate blockers
- whether the system is safe enough to change without more protection first
- which risk maps to which action, with evidence and claim ceiling

### wff-x-plan-test-protection: plan-test-protection

Answers:

- what must be protected before refactoring
- which tests should be added first
- how brownfield compatibility will be checked during change
- whether implementation is blocked, guarded, or protected enough to start

### wff-x-intake-target-driver: target-driver-intake

Answers:

- what the bounded change point is
- which modules and interfaces are affected
- which legacy scope is explicitly out of bounds for this round
- which PX Handoff Cards define the takeover units
- whether the next move should return to P1, enter P2, protect first, go directly to P3, or require an explicit recorded decision
- what P1, P2, and P3 should consume differently from the same brownfield handoff
- how the PX-to-P1 and PX-to-P2 packets avoid leaking PhaseX internal structure into the mainline

### wff-x-scan-biz-arch: scan-biz-arch

Answers:

- what business flows, roles, rules, exceptions, and domain vocabulary are visible now
- which business facts are observed, inferred, conflicting, or unknown
- what P1 can consume as brownfield source truth
- what P2 may consume only as secondary boundary or invariant hints

## 3. Asset shape

Each authored package contains the minimal 4-pack:

- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

PhaseX intentionally does not copy the full heavy control/audit stack used by mature Phase-1/2/3/4 tracks.

Wave-1 follows the v1.3.10 control boundary:

- Workflow controls profile, order, scaffold, output set, and minimum validation.
- Agentic controls brownfield meaning, risk judgment, safety-net strategy, and downstream route rationale.
- Evidence caps claims with code references, command/test evidence, unknowns, and confidence.

The validator checks that reviewable surfaces exist. It does not score or decide brownfield truth.

## 4. How to use it

Use the official entry skill:

- `skills/wff-x/`

For Wave-1, scaffold a fresh case root:

```bash
python3 scripts/phasex/scaffold_phasex_case.py \
  --system-root <existing-system-root> \
  --output-dir tmp/local-artifacts/<case-name>/phase-x \
  --profile <assessment-only|technical-refactor|target-driver> \
  --version <vN>
```

The Wave-1 scaffolded case root will include:

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

- `wff-x-scan-code-baseline`
- `wff-x-scan-tech-health`

### `technical-refactor`

Use:

- `wff-x-scan-code-baseline`
- `wff-x-scan-tech-health`
- `wff-x-plan-test-protection`

### `target-driver`

Use:

- `wff-x-scan-code-baseline`
- `wff-x-intake-target-driver`

## 6. Boundary

This package is not:

- a new default Phase-5
- a replacement for P1-P4
- a full migration-orchestration skill set

Its job is narrower:

> tell the truth about the current brownfield system, surface technical risk, protect the system before change, and produce a clean handoff back into the main lifecycle

## 7. One-line summary

This directory keeps PhaseX honest: Wave-1 remains the runnable brownfield entry path, while Wave-2 expands only the next needed package surfaces before broader orchestration is claimed.
