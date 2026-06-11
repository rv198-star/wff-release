# Artifact Traceability Minimum Rules（v0.1）

## 1. Purpose

This document provides the minimum operational rules for artifact-level traceability in the current manual-management mode.

It does NOT define a full traceability system. It defines:
- when to assign an artifact ID
- how to name it
- how to fill `depends_on` and `feeds`
- minimum validation at phase boundaries

---

## 2. When to assign an artifact ID

Assign an ID when a Stage output-template creates or significantly updates any of:
- a structured output document (the output-template itself)
- a diagram with structural meaning (boundary, flow, model)
- a decision record
- a handoff package

Do NOT assign IDs to:
- intermediate working notes
- chat logs or conversation artifacts
- draft content that will be replaced before stage exit

---

## 3. ID naming convention

Format: `{phase}-{stage}-{type}-{sequence}`

Examples:
- `P1-S01-OUT-001` — Phase-1, Stage-01, output document, first
- `P1-S02a-DIA-001` — Phase-1, Stage-02a, diagram, first
- `P1-S04-HND-001` — Phase-1, Stage-04, handoff package, first
- `P2-S01-OUT-001` — Phase-2, Stage-01, output document, first

Type codes:
- `OUT` — output document (the main stage output)
- `DIA` — diagram
- `DEC` — decision record
- `HND` — handoff package
- `PRD` — PRD main document (convergence artifact)

---

## 4. How to fill `depends_on`

List the artifact IDs that this artifact **directly consumed or built upon**.

Rules:
- only list direct dependencies, not transitive ones
- if an artifact depends on the entire output of a previous stage, reference that stage's main output ID
- example: `depends_on: [P1-S01-OUT-001, P1-S02a-DIA-001]`

---

## 5. How to fill `feeds`

List the artifact IDs (or expected downstream artifact type) that this artifact is **expected to feed into**.

Rules:
- if the downstream artifact doesn't exist yet, use the expected ID pattern: e.g. `feeds: [P1-S03-OUT-001 (expected)]`
- this field is aspirational at creation time and should be updated when the downstream artifact is actually created

---

## 6. Phase boundary validation

At each phase boundary (e.g. Phase-1 → Phase-2):
- the handoff package should list all artifact IDs produced in this phase
- Phase-2 Stage-01 intake should verify that referenced upstream IDs are resolvable (the referenced document exists and is findable)
- if an ID is referenced but the document cannot be found, flag it as a traceability gap

---

## 7. Current limitations

- This is a manual convention, not enforced by tooling
- ID uniqueness is not automatically checked
- `feeds` is aspirational and may be incomplete
- Full artifact-level traceability (automated, bidirectional, verified) is a future improvement tracked in the `wff-base-traceability-management` roadmap
