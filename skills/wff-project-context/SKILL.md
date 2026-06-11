---
name: wff-project-context
description: Use when a WFF project needs project-level Agent context, PROJECT_CONTEXT.md review, durable context candidate triage, key reference curation, or conflict notes between human-maintained context and lifecycle artifacts.
---

# WFF Project Context

## Scope

`wff-project-context` maintains `.wff/PROJECT_CONTEXT.md`.

`.wff/PROJECT_CONTEXT.md` is project-level Agent context. It tells WFF agents the durable project facts, constraints, and reference entry points that humans may treat as obvious but AI agents can miss.

It is not a new lifecycle phase and not a formal truth artifact.

Authority boundary:

- It must not replace P1 product truth.
- It must not replace P2 architecture decisions.
- It must not replace P3 implementation or runtime evidence.
- It must not replace PX brownfield truth.
- It must not replace P4 claim ceilings.
- It must not silently override human-maintained context.

If project context conflicts with lifecycle artifacts, record the conflict in `Conflict / Review Notes` and route it to the responsible phase or human review.

## Default File

Default location:

```text
<project-root>/.wff/PROJECT_CONTEXT.md
```

Discovery:

1. Prefer `.wff/PROJECT_CONTEXT.md`.
2. Treat root `CONTEXT.md` or `project-context.md` only as import candidates.
3. If no project context exists, create a short template.

Do not use root `CONTEXT.md` as the default authority file.

## Template

Use this template for a new project context file:

```markdown
# WFF Project Context

## Context Authority

This file is project-level Agent context. It helps WFF agents make better default judgments, but it does not replace P1/P2/P3/PX/P4 lifecycle truth.

## Human Maintained Context

## Demand / Business Context

## Architecture / Design Context

## Code / Implementation Context

## Brownfield Context
<!-- only for brownfield / migration / refactor / change projects -->

## Key References

## Conflict / Review Notes
```

Empty sections may remain as one-line headings. Do not fill them with generic text.

## Admission Rules

Do include:

- Durable project facts that are likely to affect multiple phases or tasks.
- Context that is not common knowledge or generic best practices.
- Constraints that change product, architecture, implementation, review, cost, compliance, or operations judgment.
- Human-stated rules, with source and confidence when available.
- Short key references when the detailed source is high-impact and easy to miss.

Do not include:

- Generic best practices such as "write clear code" or "add tests".
- lifecycle artifact summaries copied from PRD, ESP, ActionCard, PX baseline, or validation reports.
- A project document directory.
- Temporary task instructions or debugging notes.
- Optimistic claims without source or claim ceiling.
- Facts an Agent can reliably infer from the code tree at low cost.

Rule of thumb:

> Add it only when not remind the Agent and the Agent is likely to miss it, and missing it would cause a bad durable judgment.

## Section Guidance

### Human Maintained Context

Use for team, organization, environment, operations, compliance, and delivery preferences that WFF must preserve. WFF may suggest changes, but must not overwrite this section automatically.

Examples:

- `Team implementation capacity is primarily Go / Java. Other backend languages require explicit architecture approval.`
- `Production database is paid Oracle; replacing it requires licensing, cost, and migration justification.`

### Demand / Business Context

Use for durable business constraints and user context. Do not copy the PRD.

Examples:

- `Customer industry has low profit margins; prefer low recurring cost and low manual operation burden.`
- `Current user base is approximately 90% female. Use this for accessibility, privacy, safety, and communication review; do not infer preferences from stereotypes.`

### Architecture / Design Context

Use for long-lived architecture direction, rejected options, integration boundaries, deployment constraints, and system trade-offs. Do not copy ESP content.

### Code / Implementation Context

Use for project-specific implementation rules, testing patterns, directory/module boundaries, runtime constraints, and anti-patterns. Do not copy ActionCards.

### Brownfield Context

Use only for brownfield / migration / refactor / change projects.

Record durable current-system facts, external interfaces, offline processes, compatibility constraints, technical debt, and explicit unknowns. Do not copy PX baseline content wholesale.

## Key References

Key References is not a document catalog.

Add a reference only when an Agent is likely to miss a high-impact source and the mistake would affect repeated decisions.

Default exclusions:

- PRD, ESP, ActionCard, PX baseline, and validation reports as whole documents.
- Ordinary README, API docs, and test reports.

If a standard artifact has a critical small passage, reference the passage, not the whole artifact.

Reference format should include a line range, heading anchor, or keyword locator when the source is long:

```markdown
- `<project-docs>/domain/billing-rules.md:42-68` - Required when changing refunds, coupons, or billing recalculation.
- `<project-docs>/adr/0007-db-choice.md#rejected-options` - Explains rejected database choices; do not reopen without changed constraints.
```

## Project Context Candidates

wff-req-chat captures candidates in the P1 source input packet. It must not write .wff/PROJECT_CONTEXT.md directly.

Candidate format:

```yaml
- candidate: Team backend capacity is primarily Go / Java.
  likely_section: Code / Implementation Context
  source: req-chat user statement
  decision_impact: affects backend language and maintainability choices
  confidence: user-stated
  durability: durable
  action: context-candidate
  needs_review: false
```

When reviewing candidates:

- accept durable, non-obvious, cross-phase context;
- reject one-off task facts;
- preserve `inferred` and `review-bound` state;
- write conflicts to `Conflict / Review Notes`;
- keep accepted entries short.

## Update Rules

- Preserve `Human Maintained Context` exactly unless the user explicitly asks to edit it.
- Keep WFF-managed entries concise and source-aware.
- Prefer a short inline rule plus a precise key reference over copying long source text.
- Do not treat a complete-looking context file as quality proof.
- Do not block P1/P2/P3/PX solely because project context is missing.
