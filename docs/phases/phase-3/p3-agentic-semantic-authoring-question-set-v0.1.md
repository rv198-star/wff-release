# P3 Agentic Semantic Authoring Question Set (v0.1)

Status: `WO-119F.13` / `v1.3.6.13` runtime-facing support reference
Date: 2026-05-07

This question set supports the P3 default mainline after `WO-119F.13`.

It is not a gate, schema, or answer template. It may shape depth before file write, but the Agentic semantic authoring path owns the answer.

## Control Boundary

- Workflow assembles the bounded action-card, contract, source, and runtime context.
- Agentic decides owner / aggregate / invariant / value-rule, failure path, and test intent before service/repository/unit file write.
- Templates / TVG may ask the questions below but must not provide default answers.
- Evidence / Gates prove generated code/test/runtime closure and cap claims.

## Required Questions

For each operation, answer before service/repository/unit body authoring:

1. Who owns this operation's business effect?
2. What aggregate boundary must remain coherent?
3. Which domain invariant must the generated code enforce?
4. What user or business value does the operation protect?
5. Which negative path proves the invariant?
6. For read/list/detail operations, what proves no durable mutation happened?
7. For write/command operations, what proves validation, persistence, audit/event, and read-back behavior happened?

## Anti-Answer Rule

The question set must not supply or bless generic answers:

- `not-declared` is not an owner.
- `review-bound` is not an aggregate.
- `business invariants` is not a domain invariant.
- a field existing in JSON is not proof of semantic ownership.
- a script pass is not proof that Agentic judgment happened.

If the context is insufficient, the output must keep a review-bound / return signal instead of letting a script default decide the content truth.

## F.12 Slimming Boundary

Do not restore:

- persisted `business-behavior-authoring-plan.json`;
- F.11 heavy `action-card-execution-map.json`;
- a new default rich-context artifact;
- F5/F6 selected-module gate stacks.

Agentic semantic decisions may exist in memory before file write. Evidence summaries may count decision and residue metrics, but must not become a new content-truth artifact.
