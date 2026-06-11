# Design / Architecture Stage Skill Package (Phase-2)

## 1. What this is

This directory is the current **Phase-2 (design / architecture) Stage Skill set** for this repository.

The official phase entry is now:

- `skills/wff-arch/`

It is no longer just a loose stage-outline draft. It now contains:

- 4 completed first-pass stage packages with aligned runtime, audit, verification, and support docs
- runtime core files for each stage
- design-time control artifacts for each stage
- happy-path self-test / dry-run / verification artifacts
- rule-level robustness coverage artifacts
- bilingual audit mirrors for runtime and verification assets
- Stage-2 deliverables / traceability / runtime-hardening support docs

In other words, this directory is currently:

> **the first-pass executable authored package for the design / architecture phase, with runtime, audit, verification, traceability, and support-side assets aligned**

The intended generation posture is now explicitly top-down:
Phase-2 should absorb Phase-1 trace units through named design surfaces, not merely restate PRD prose with richer architecture vocabulary.

---

## 2. The 4 substages in Phase-2

### Stage-01: architecture-definition-and-boundary-setting
Answers:
- what system boundary is really in scope
- what constraints and quality posture already exist versus remain unresolved
- what boundary-level security and capacity posture must already be visible before decomposition
- what capability structure and architecture direction should be handed into decomposition
- which boundary-visible names and interactions are frozen now versus deferred to private implementation

### Stage-02: domain-module-service-decomposition
Answers:
- how Stage-01 capability structure becomes domain/module/service structure
- how responsibilities and dependencies are partitioned
- what conceptual entity relationships and domain events Stage-03 may rely on
- which names belong to public boundary structure rather than internal implementation

### Stage-03: data-storage-and-interface-design
Answers:
- how decomposition becomes data ownership, storage strategy, interface contracts, and interaction boundaries
- how schema/API/security/runtime assumptions become explicit without overfreezing internals
- how all known business scenarios stay covered, including GWT-compatible acceptance structure for critical/failure/conflict paths
- how technology selection, external evidence, dominant bottleneck, stronger alternatives, and the tradeoff-closure chain are evaluated

### Stage-04: design-convergence-and-delivery-prototype
Answers:
- how prior-stage design outputs converge into an implementation-facing package
- how unresolved design risks remain visible in the handoff
- which critical public-boundary sequences must be made explicit
- what coarse-grained implementation slices/work packages should be handed off without freezing code-level design
- what auth/vendor/token lifecycle and onboarding/glossary posture the implementation team actually needs on day 1
- whether the chosen architecture is merely acceptable or actually stronger than the mainstream baseline

---

## 3. What assets each stage currently contains

Each Stage currently contains four layers of assets:

### A. Runtime Assets
- `skill-contract.md`
- `stage-sop.md`
- `output-template.md`
- `source-cards.md`

### B. Runtime-Hardening Evidence Assets
- `runtime-decision-log.md`
- `state-transition-record.md`
- `failure-path-output.md`

### C. Design / Audit / Verification Assets
- `stage-charter.md`
- `source-register.md`
- `rule-cards.md`
- `merge-decisions.md`
- `binding-matrix.md`
- `verification.md`
- `self-test-case.md`
- `self-test-dry-run-output.md`
- `self-test-verification-report.md`
- `robustness-test-case.md`
- `robustness-test-report.md`

### D. Chinese Audit Mirrors
- runtime mirrors: `skill-contract.zh-CN.md`, `stage-sop.zh-CN.md`, `output-template.zh-CN.md`, `source-cards.zh-CN.md`
- verification mirrors: `verification.zh-CN.md`, `self-test-*.zh-CN.md`, `robustness-test-*.zh-CN.md`

Phase-2 now also includes runtime and verification Chinese audit mirrors (`*.zh-CN.md`) for all four substages.

---

## 4. What Phase-2 currently adds beyond Phase-1

Phase-2 is not a simple continuation of product/requirements structure. Its special burden is:

- absorbing incomplete Phase-1 NFR information without silently flattening it into certainty
- freezing system/design boundaries before detailed decomposition begins
- freezing public-boundary-visible names/contracts/interactions without prematurely freezing private class or method design
- forcing lifecycle states to stay owner-realizable instead of depending on downstream read-only writeback
- forcing authoritative business mutations to keep one primary command boundary unless split semantics are explicit
- forcing public-boundary names to stay registry-closed across schema / contract / endpoint layers
- preserving cross-stage declaration states (`present | absent | unknown | deferred`)
- forcing boundary-level security and capacity posture to become explicit before Stage-02/03 deepen the design
- keeping all known business scenarios covered while only drawing detailed sequence views for critical public-boundary scenarios
- allowing only coarse-grained implementation task sketching in Stage-04 instead of coding-level freeze
- forcing time-sensitive technology choices to stay evidence-backed rather than memory-only
- forcing dominant-bottleneck and baseline-vs-optimum reasoning when strong constraints make a mainstream baseline insufficient
- forcing final readiness wording to stay calibrated to verification / confidence / realizability evidence
- preventing TOGAF / SOA-lite / SOMA / BPMN vocabulary from replacing the current four-stage execution backbone
- producing design-facing handoffs that are still usable even when some architecture truth remains review-bound

---

## 5. Current verification status

### Completed in this first pass
- Stage-01 self-test / dry-run / verification: present
- Stage-02 self-test / dry-run / verification: present
- Stage-03 self-test / dry-run / verification: present
- Stage-04 self-test / dry-run / verification: present

### Completed robustness coverage
- refusal-path intent coverage
- blocked-path intent coverage
- false-certainty / fake-readiness prevention coverage
- evidence-loss / baseline-regression prevention coverage for Stage-03 and Stage-04 convergence

### Current boundary
Phase-2 is now structurally complete as an authored package set and verification-complete in **first-pass package shape**, with bilingual audit coverage, deliverables-checklist attachment, coarse traceability baseline, registry-backed pilot integration, and minimum runtime-hardening evidence across all four substages.

It is **not yet**:
- fully runtime-hardened in a live orchestrator
- fully fine-grained registry-enforced end to end
- fully hardened for all contradictory/adversarial input paths
- broadly replay-proven across multiple equally deep local real cases

Current v0.2 runtime hardening / traceability level:
- Stage-01~04 runtime artifacts are present (`runtime-decision-log.md`, `state-transition-record.md`, `failure-path-output.md`)
- blocked / refusal / retry / review-reentry style evidence now exists across the authored stage-pack set at first-pass depth
- the Phase-2 coarse artifact chain can now be registered / validated / reported through `wff-base-traceability-management`

---

## 6. How to use this package right now

The recommended official use is now:

> **enter through `skills/wff-arch/`, then run the four authored Stage packs as one bounded stage-pack set**

That means:
- start from `docs/phases/phase-2/phase-2-session-bootstrap.md`
- if this is a new version, initialize a fresh case root with `scripts/phase2/scaffold_phase2_case.py`
- follow `docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md` for fresh first-pass generation
- read the Phase-1 PRD's `Phase-2 Design Input Contract` before authoring Stage-01 and keep the absorption chain explicit through `P2-DTR-*`, `P2-CTR-*`, `P2-RP-*`, and `P2-RT-*`
- use `scripts/phase2/run_phase2_full_trial.py` as the official closure wrapper once Stage-01..04 outputs are ready
- use this directory as the authoritative Stage pack set
- produce or update `docs/phases/phase-2/phase-2-execution-report-template.md`
- initialize / bind / validate / report the coarse trace chain with `wff-base-traceability-management`

Do not treat an older Phase-2 case directory as the primary editable baseline for a new version.

Manual per-Stage use is still valid, but it is now a secondary mode for:
- authoring one Stage pack
- debugging one weak artifact
- targeted remediation

When using a Stage manually:
- `skill-contract.md` defines the stage boundary
- `stage-sop.md` defines the execution order
- `output-template.md` defines the required artifact shape
- `source-cards.md` defines the preferred method/material inputs

Verification artifacts should be used as:
- examples of good-path dry-run structure
- checks for whether a real run is shape-correct
- reminders of refusal/blocked/fake-certainty boundaries
- the current required output shape for scenario coverage, evidence-backed tech selection, and optimality-review obligations

---

## 7. Most important differences from Phase-1

Phase-1 mainly turns ambiguous product intent into structured requirement outputs.

Phase-2 has extra design-specific risks:

- boundary mistakes are more expensive because they poison downstream decomposition
- NFR ambiguity becomes architecture debt if not kept explicit
- decomposition/data/interface work is easier to overreach or mix across stages
- convergence can falsely look “complete” even when unresolved risks remain

So the core discipline of this Phase-2 package is:

> **preserve design truth boundaries while still producing a usable downstream architecture handoff**

---

## 8. Supporting references to read next

If you want to extend or harden this package, read these first:

- `docs/plans/2026-03-13-design-architecture-stage-kickoff.md`
- `docs/phases/phase-2/design-architecture-stage-package-v0.md`
- `docs/phases/phase-2/design-architecture-source-library-seed-v0.1.md`
- `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md`
- `docs/phases/phase-2/stage-2-traceability-baseline-v0.1.md`
- `docs/phases/phase-2/stage-2-runtime-hardening-targets-v0.1.md`
- `docs/phases/phase-2/phase-2-session-bootstrap.md`
- `docs/phases/phase-2/phase-2-execution-report-template.md`
- `docs/phases/phase-2/phase-2-case-backed-validation-matrix-v0.1.md`
- `docs/phases/phase-2/design-architecture-case-backed-absorption-matrix-v0.1.md`
- `docs/governance/design-time-vs-runtime-artifacts-segregation-v0.1.md`
- `reference-packages/phase1-product-requirements/README.md`

---

## 9. One-sentence summary

This directory is now:

> **the current formal Stage Skill set for the design / architecture phase, entered officially through `skills/wff-arch/`, with runtime, control, audit, verification, checklist, traceability, and all-stage first-pass runtime-hardening assets present.**
