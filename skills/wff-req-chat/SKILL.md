---
name: wff-req-chat
description: Use before wff-req when the user has a rough idea, existing business materials, current-system context, or scattered requirements and needs a truth-state-marked P1 source brief rather than a PRD.
---

# WFF Requirements Chat Intake

## Scope

`wff-req-chat` is a pre-Phase-1 conversational intake skill.

Use it to help a user describe what they want to build, submit existing materials, clarify missing context, and produce a `P1 source brief` that can be consumed by `wff-req`.

It is not a Phase-1 execution skill. It must not generate PRD, must not generate UPP, must not claim Phase-1 completion, and must not bypass the official `wff-req` runtime and gates.

## Default Output Language

Follow the repo-wide output language policy in `config/generated-output-policy.json` when available.
Unless a file format, protocol, or immutable upstream quote requires English, human-reviewed intake summaries and source briefs should follow the user's conversation language.

Preserve file paths, commands, API names, schema fields, trace ids, artifact ids, env vars, truth-state labels, route ids, and protocol keywords in their canonical form.

## User-Facing Start

Start plainly:

```text
Tell me what you want to build. You can also paste existing docs, spreadsheets,
screenshots, workflows, or notes. I will help turn them into a Phase-1 source brief.
```

Do not open by asking the user to fill a long form. Accept natural language and materials first, then classify the route and ask the highest-value next question.

## When To Use

Use when:

- the user has a rough idea but no stable Phase-1 source document
- the user has an existing business process that should become software
- the user has an existing software system that needs changes
- the user has old PRD / BRD / spec-like material that needs shaping before `wff-req`
- the user has an internal tool, automation, or operations utility request
- the user wants to proceed into P1 but the intake gaps should be visible first

Do not use when:

- the user already has a sufficient Phase-1 source brief and wants the official P1 run
- the user wants to run `wff-req`
- the user wants Phase-2, Phase-3, Phase-4, or Phase-X work
- the request is to write the final PRD / UPP directly

## Core Boundary

The output is a `P1 source brief`, not a PRD.

`wff-req-chat` may recommend a P1 profile or depth note, but `wff-req` owns official Phase-1 execution, stage artifact generation, PRD assembly, convergence gates, and execution reporting.

## 人话版使用说明

`wff-req-chat` 是进入 P1 前的对话入口。它不是 PRD 生成器，也不是 `wff-req` 的替代品。

`intake mode` 是先把事实收齐：你想做什么、谁会用、现在怎么做、已有材料在哪里、哪些内容已经确认、哪些只是推测。

`wff-office-hours mode` 是挑战这个想法值不值得进入 P1：问题是不是真的、用户 / 买方 / 操作者 / 评审者是不是清楚、现有替代方案是什么、最小有价值切片是什么、哪些声明还不能说满。

什么时候进入 `wff-req`：

- `ready-for-P1`：事实和挑战结果足够进入正式 P1。
- `provisional-ready-for-P1`：可以进入 P1，但必须带着明确的 review-bound 缺口和 claim ceiling。
- `not-admission-ready`：还不能当作正常 P1 输入，应该继续 intake 或只保留 provisional note。

`wff-office-hours mode` 不是一个新的默认入口 skill。它只是 `wff-req-chat` 里的第二阶段，用来让 source brief 更扎实。

## Two-Mode Protocol

`wff-req-chat` is one public pre-P1 entry skill with two internal modes:

1. `intake mode` gathers user intent, source materials, route pressure, and a first source brief seed.
2. `wff-office-hours mode` challenges product truth before admission into official Phase-1.

The default path is:

```text
wff-req-chat
  -> intake mode
  -> wff-office-hours mode
  -> Fresh-Context Review
  -> Admission Decision
  -> P1 source input packet
  -> wff-req
```

Workflow controls the order and packet contract. Agentic reasoning owns question selection, product-truth challenge, admission judgment, and gap routing. Evidence records truth state, reviewer concerns, and claim ceilings.

Do not expose `wff-office-hours mode` as a separate default skill in this version. It is the second mode inside `wff-req-chat`, not a second public entry path.

## Intake Mode

Use `intake mode` first when the user has rough intent, business materials, current-system context, or scattered requirements.

`intake mode` should establish:

- primary route and secondary pressures
- rough problem / opportunity
- rough target user / beneficiary
- source materials and evidence anchors
- first source brief seed
- initial truth-state ledger
- visible review-bound gaps

Do not ask the user to complete a long form. Ask one high-value question at a time, request source materials when useful, and stop intake when the main uncertainty shifts from "missing facts" to "whether the product premise is strong enough".

## Intake To Office-Hours Transition

Move from `intake mode` to `wff-office-hours mode` when:

- rough problem / opportunity exists
- rough target user / beneficiary exists
- a first source brief seed exists
- adding more intake facts has lower marginal value than challenging the product premise
- the main risk is product truth, not simple information absence

Use a plain transition prompt:

```text
I have enough to form a first source brief seed. The next step should not be
more feature collection; it should be wff-office-hours mode to challenge whether
the problem is real, who it is for, what the current substitute is, and what the
narrowest valuable wedge should be. Do you want to enter that mode?
```

Do not enter `wff-office-hours mode` when rough problem / opportunity or rough target user / beneficiary is missing. If the user asks to proceed anyway, use the Early Start Gate and mark readiness as `not-admission-ready`.

## wff-office-hours Mode

`wff-office-hours mode` is a bounded product-truth challenge mode. It should make the source better for P1 without becoming PRD authoring.

Challenge axes:

| Axis | Challenge Focus | Admission Impact |
|---|---|---|
| `Problem Reality` | Is this a real problem / opportunity, or only a desired feature? | Determines whether a product thesis can be admitted. |
| `User Specificity` | Who has the pain, who pays, who operates, and who reviews? | Determines whether the role model is usable by P1. |
| `Status Quo` | How is this handled today, and why are substitutes insufficient? | Determines whether the value mechanism is grounded. |
| `Value Mechanism` | What business, user, operational, or decision value would software create? | Determines whether acceptance meaning can be downstreamed. |
| `Narrowest Valuable Wedge` | What is the smallest version that still carries real value? | Determines MVP and scope cutline pressure. |
| `Evidence And Claim Ceiling` | What is confirmed, artifact-backed, inferred, or review-bound? | Determines truth state and formal claim ceiling. |

Stop Rule:

- each axis defaults to at most `1` main question plus `1` follow-up
- normal total challenge length is `6-10` questions
- high-risk or low-evidence cases may use at most `12` questions
- stop after two consecutive questions with no new source truth
- unresolved items become `Open Truth Gaps`
- if a missing fact can only be supplied by user material or external citation, ask for the material or mark it review-bound

Questions must affect admission. Do not ask ornamental questions, generic founder-coaching questions, or implementation-design questions that belong to P2/P3.

## Return To Intake

Return from `wff-office-hours mode` to `intake mode` when the challenge exposes missing source truth that must be collected before admission:

- rough target user / beneficiary is still unclear
- status quo is unknown
- current workflow, rule, source material, or business constraint is missing
- chosen wedge depends on unconfirmed constraints
- high-impact external facts need user-provided material or citation

Record the return explicitly:

```yaml
office_hours_return_to_intake:
  reason:
  missing_source_truth:
  next_best_material_request:
```

If the user refuses the necessary source truth and still wants to proceed, the admission state must remain `not-admission-ready` or `provisional-ready-for-P1` with clear `Open Truth Gaps`.

## Fresh-Context Review

Before producing the final packet, run one fresh-context review pass using only the source brief seed, `Product Truth Challenge Notes`, and admission draft. The reviewer should not rely on the full conversation transcript.

The review must look for:

- weak problem reality
- vague or mixed user / buyer / operator roles
- missing status quo or substitute pressure
- unclear value mechanism
- over-broad first wedge
- unsupported claims or hidden assumptions
- gaps that P1 must preserve instead of inventing away

Default review depth is one pass. Important or high-risk cases may use up to three bounded passes. Repeated unresolved issues go to `Reviewer Concerns` and `Open Truth Gaps`; do not loop indefinitely.

## P1 Source Input Packet

The normal output of the two-mode flow is a `P1 source input packet`. The packet contains the `P1 source brief` plus admission evidence for `wff-req`.

Use this packet structure:

```markdown
# P1 Source Input Packet: <project name>

## Intake Metadata

## Raw User Intent

## Source Materials

## P1 Source Brief

## Product Truth Challenge Notes

## Challenge Axis Coverage

## Truth-State Ledger

## Open Truth Gaps

## Reviewer Concerns

## Admission Decision

## Recommended P1 Profile / Depth Notes

## Handoff Note For wff-req
```

`Admission Decision` must be one of:

- `ready-for-P1`
- `provisional-ready-for-P1`
- `not-admission-ready`

`ready-for-P1` means the packet can enter `wff-req` normally.

`provisional-ready-for-P1` means `wff-req` may run only while preserving the named review-bound gaps and claim ceilings.

`not-admission-ready` means the output is a provisional intake note or return-to-intake record. It must not be treated as normal P1 source input.

## Intake Routes

Select one primary route. Routes guide the conversation; they are not hard gates. If the case is mixed, name the primary route and secondary pressures.

| Route | Use When | Collection Bias |
|---|---|---|
| `new-product-or-idea` | The user is starting from a new product, service, or feature idea. | target users, problem / opportunity, why now, substitutes, value hypothesis, success signals, MVP boundary, early evidence |
| `existing-business-systemization` | The user has a current offline or semi-manual business process to systemize. | SOPs, spreadsheets, reports, forms, screenshots, role handoffs, approvals, exceptions, current tools, habits that must not break |
| `existing-software-change` | The user wants to modify, extend, or repair an existing software system. | current capability, screenshots, code paths, issues, logs, API / DB docs, affected users, migration / compatibility constraints |
| `existing-requirements-strengthening` | The user already has PRD / BRD / spec-like material that needs review, shaping, or completion. | existing docs, meeting notes, requirement pools, prototypes, review comments, missing assumptions, unresolved decisions |
| `technical-or-internal-tool` | The request is an internal tool, developer tool, automation, operations utility, or backstage workflow. | operator, trigger, inputs, outputs, manual path today, permissions, audit, failure handling, integration boundaries |

Do not create a separate AI-specific primary route. If the case involves AI, use the AI / automation horizontal trigger while keeping the product route grounded in the user's business or workflow problem.

## Horizontal Triggers

Some concerns cross all routes. If detected, add targeted questions without changing the primary route.

| Trigger | Added Intake Questions |
|---|---|
| `ai-or-automation-involvement` | Is AI the user value or only an implementation means? Which actions can be automatic? Which require human confirmation? What is the error cost? What fallback, audit, and handoff are needed? |
| `regulated-or-high-risk` | What compliance, safety, approval, legal, financial, medical, or operational risk boundaries exist? Which claims require external evidence? |
| `multi-tenant-or-data-sensitive` | What tenant, permission, privacy, audit, retention, or data isolation rules are required? |
| `migration-or-brownfield` | What current system, data, workflow, users, integrations, and compatibility boundaries must be preserved? |

These triggers prevent P1 source material from hiding major product truth and evidence boundaries. They are not implementation design.

## Internal Intake Map

Maintain an internal map of what is known, missing, inferred, or review-bound.

The map covers:

- project route and secondary pressures
- business / user goal
- user, buyer, operator, reviewer, and decision roles
- current-state baseline or substitute path
- target workflow or decision loop
- business objects and data objects
- rules, states, exceptions, permissions, and approvals
- source materials and evidence anchors
- scope boundary: in, out, later
- constraints: time, budget, compliance, data, migration, security, operating limits
- AI / automation, risk, tenant, or migration triggers
- truth-state ledger
- P1 source-brief readiness

The user should not have to see the full map every turn. Show short progress summaries when useful.

## Questioning Discipline

- Ask one high-value question at a time.
- Offer a recommended answer or example when it reduces friction.
- If a user-provided artifact already answers a question, use the artifact and do not ask again.
- Prefer material requests when a route suggests that documents, screenshots, spreadsheets, flows, logs, or notes would be more useful than another conversational answer.
- Periodically summarize confirmed facts, artifact-backed facts, inferred assumptions, and review-bound gaps.
- Stop asking when another question is unlikely to materially improve the source brief.

This is structured agentic intake, not a rigid form and not open-ended interrogation.

## Truth State

Every meaningful source-brief claim should carry a truth state.

| State | Meaning |
|---|---|
| `user-confirmed` | The user explicitly stated it or confirmed the skill's summary. |
| `user-provided-artifact` | The claim comes from a user-provided document, screenshot, spreadsheet, workflow, log, or other material. |
| `external-cited` | The claim comes from an external source with a citation or supplied link. |
| `inferred` | The skill made a reasonable low-risk inference from available information, but the user has not confirmed it. |
| `review-bound` | The claim affects important product truth, scope, risk, success criteria, workflow, constraints, or evidence, and must not be treated as confirmed without review. |

Rules:

- AI inference must never be silently promoted to `user-confirmed`.
- Only explicit user confirmation or artifact evidence can upgrade a claim.
- High-impact inference must be marked `review-bound`, not merely `inferred`.
- Missing truth should remain visible rather than being filled with generic product language.

## Early Start Gate

The user may stop intake early by saying they want to start, proceed, or generate the P1 input now.

When this happens:

1. Stop normal questioning.
2. Generate an `Intake Readiness Snapshot`.
3. List confirmed information, artifact-backed information, inferred assumptions, key gaps, and likely P1 review-bound risks.
4. Ask for explicit confirmation before generating the source brief:

```text
Current source brief will enter P1 with these review-bound gaps. Confirm that I should generate the P1 source brief with these gaps visible?
```

5. Generate the `P1 source brief` only after confirmation.

If the request does not identify at least a rough problem / opportunity and a rough target user / beneficiary, the readiness state must be `not-admission-ready`. You may produce a provisional intake note, but must not present it as a normal P1 source brief.

If readiness is `not-admission-ready`, confirm a `provisional intake note`, not a normal `P1 source brief`.

## P1 Source Brief Contract

The main output is a `P1 source brief`.

Use this structure:

```markdown
# P1 Source Brief: <project name>

## Intake Metadata
- route:
- secondary_pressures:
- readiness_state: ready | provisional-ready | not-admission-ready
- source_language:
- created_at:

## Raw User Intent

## Source Materials

## Project Context

## Problem / Opportunity

## User, Buyer, Operator, And Decision Roles

## Current-State Baseline Or Substitute Path

## Desired Outcome And Success Signals

## Scope Boundary
- in_scope:
- out_of_scope:
- later:

## Constraints

## Key Workflows / Scenarios

## Business Objects / Data Objects

## Rules, Exceptions, Permissions, And Approvals

## AI / Automation / Risk / Data / Migration Notes

## Truth-State Ledger

## Review-Bound Gaps

## Recommended P1 Profile / Depth Notes

## Handoff Note For wff-req
```

Keep the source brief clean enough for `wff-req` to consume. Do not embed full conversation transcripts in the main body.

## Companion Log

You may emit an `intake-log` or appendix that records:

- questions asked
- user answers
- artifacts inspected
- summaries the user confirmed
- early-start confirmation text, when applicable

The log is for audit and recovery. It does not replace the source brief.

## Refusal And Return Conditions

Refuse to present an output as a normal P1 source brief when:

- the rough problem / opportunity is missing
- the rough target user / beneficiary is missing
- the user has not confirmed early-start gaps after requesting early start
- the user asks you to generate PRD / UPP directly
- high-risk external claims would be needed but no evidence or review-bound warning is allowed

In those cases, provide a provisional intake note or ask the next highest-value question.

## Handoff To wff-req

End with a short handoff note:

- whether the brief is `ready`, `provisional-ready`, or `not-admission-ready`
- which review-bound gaps `wff-req` must preserve
- which source materials should be treated as authority inputs
- suggested `wff-req` profile or depth note, when useful

Do not run `wff-req` unless the user explicitly asks to start official Phase-1 execution after the source brief is produced.
