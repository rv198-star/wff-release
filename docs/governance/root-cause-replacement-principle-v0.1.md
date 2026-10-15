# Root-Cause Replacement Principle v0.1

## Purpose

This principle defines the default WFF repair posture for repository development and WFF lifecycle implementation.

> Fix the owning cause with the correct logic. State the intended valid behavior directly. Let downstream artifacts project that corrected logic.

It is an engineering principle, not a new lifecycle phase, review ritual, or extra approval gate.

Scope: it governs how WFF repairs its own skills, templates, scripts, contracts, and runtime/tooling, effective in the next WFF version. It does not authorize in-cycle regeneration of frozen project artifacts. Inside a delivery cycle, project-level gaps follow the one-directional flow in `AGENTS.md`: they are resolved downstream, recorded with provenance and a claim ceiling, and become input to the next upstream version.

## Core Rule

When a WFF defect is found, identify the earliest authoritative WFF layer that creates the wrong behavior and repair that owner directly:

- source/product truth handling -> P1 skill, templates, and contracts;
- architecture, contract, ownership, interaction, or read-model truth handling -> P2 skill, templates, and contracts;
- implementation realization -> P3 skill, templates, and contracts;
- evidence interpretation and claim ceiling -> P4 skill and contracts;
- repository/tooling mechanics -> the owning runtime/tooling module.

The repair defines the correct invariant, contract, model, or control rule at that layer and takes effect in the next WFF version. New project runs project the corrected logic. Project artifacts already frozen in a running delivery cycle are not regenerated; a WFF format or contract upgrade reads them compatibly with a declared claim ceiling.

## Positive Rule Expression

Rules should describe the valid state or behavior that the system must produce.

Prefer:

- `Only concrete HTTP failure records are parsed as failure codes.`
- `Clean-first-use evaluates transactional/result data while authority-approved master/reference data remains valid starting context.`
- `Every accepted role/task re-entry obligation maps to a role-visible read model.`
- `A generated repository realizes the same S3SliceBinding contract consumed by its service port.`

These statements make the intended model executable and testable without preserving an incorrect model through layered exceptions.

## Boundary Guards

A guard or exception is appropriate when it protects a real boundary around an already-correct model, for example:

- malformed or untrusted external input;
- authentication and authorization boundaries;
- protocol/version compatibility;
- explicitly accepted legacy compatibility surfaces;
- irreversible safety boundaries.

A new guard should identify the invariant it protects and the boundary that justifies it. If the guard exists only because an upstream model, contract, or ownership decision is wrong, repair that owner instead.

## Repair Sequence

1. Identify the observed defect and retained evidence.
2. Locate the earliest authority/control owner that makes the behavior wrong.
3. State the correct behavior as one affirmative invariant or contract.
4. Replace the owning logic with that invariant.
5. Rerun the affected WFF tests and evidence; apply the corrected logic to new project runs and the next project version, not to artifacts frozen in a running cycle.
6. Keep only guards that protect genuine external or compatibility boundaries.

## WFF Application

This principle complements the Workflow / Agentic / Evidence boundary:

- Workflow routes the repair to the owning WFF layer and reruns dependent WFF validation; inside a project cycle it keeps the one-directional flow and routes downstream decisions to the backport queue.
- Agentic judgment defines the corrected semantic or implementation rule when uncertainty exists.
- Evidence proves that the defect is removed and that the corrected behavior survives downstream execution.

A green gate proves the corrected behavior only when the owning logic and relevant runtime evidence are both aligned; a compensating downstream pass does not replace upstream correctness. A recorded downstream decision under the one-directional flow is not a compensating pass: it is the intended in-cycle behavior and carries its own claim ceiling.
