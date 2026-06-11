---
name: using-wff
description: Use when a user wants to start using WFF, decide whether WFF should be used at all, choose one of the three external WFF entry routes, or continue from WFF-native upstream artifacts without first knowing P1/P2/P3/P4/PX terminology.
---

# Using WFF

## Scope

`using-wff` is the top-level WFF admission gate and usage router.

It answers two questions, in this order:

1. Should this work use WFF at all?
2. If yes, which WFF entry or continuation route fits the current state?

`using-wff` routes to existing WFF skills. It must not generate PRDs, architecture packs, code, validation packs, proof snapshots, or lifecycle artifacts itself.

## Core Rule

`using-wff` is an admission gate before it is a router. It may decide that WFF should not be used.

For external work, there are only three external WFF entry routes:

- `wff-req-chat`
- `wff-req`
- `wff-x`

`wff-arch`, `wff-impl`, and `wff-validation` are internal continuation routes, not external entry routes. They may be recommended only when the user already has WFF-native upstream artifacts accepted by the prior phase.

## When To Wake This Skill

Use `using-wff` when the user explicitly asks about WFF, WFF install/profile choice, lifecycle phase routing, claim ceilings, phase handoff, existing artifacts, existing systems, or confused WFF startup.

Do not wake WFF for ordinary local engineering work when the task is already clear, small, and does not need lifecycle control. Examples include a focused bug fix, a local refactor, a single test repair, or a direct implementation request with no requirement/design/validation ambiguity.

If `using-wff` is already awake and the work is ordinary engineering, say so and route out of WFF instead of forcing a WFF phase.

## Admission Decisions

| User state | Decision | Route |
|---|---|---|
| Ordinary clear coding task, small bug fix, local refactor, or direct instruction | Do not use WFF | Handle as normal engineering work |
| Rough idea, chat history, scattered notes, unstable facts, or unclear business intent | Use WFF intake | `wff-req-chat` |
| Stable demand, source brief, accepted input packet, or direct PRD generation need | Use WFF P1 | `wff-req` |
| Existing codebase, code-backed existing system, live/legacy runtime, brownfield change, refactor, migration, capacity work, or unclear current-state risk | Use WFF assessment | `wff-x` |
| Standalone non-WFF PRD / demand material | Use WFF intake | `wff-req-chat` or `wff-req`; treat it as source material, not accepted WFF P1 truth |
| Standalone non-WFF technical design, implementation package, or test report | Do not use WFF downstream | Use normal-review unless it is tied to an existing codebase/runtime or WFF-native upstream evidence |
| Existing codebase/system plus related PRD/design/API/DB/ops/test docs | Use WFF assessment | `wff-x`; Related documents are supporting evidence, standalone documents are not enough |

## External Entry Routes

These are the only external WFF entry routes.

| External starting point | Route to | Why |
|---|---|---|
| Rough idea, chat history, scattered notes, or unstable facts | `wff-req-chat` | Turn loose input into a usable P1 source/input package before formal PRD work. |
| Stable demand, source brief, accepted input packet, or direct PRD generation need | `wff-req` | Produce P1 requirements artifacts while preserving source truth and review-bound gaps. |
| Existing codebase, code-backed existing-system assessment, live/legacy runtime, historical system package, brownfield change, refactor, migration, capacity work, or unclear current-state risk | `wff-x` | Establish current baseline, truth state, gaps, risks, safety net, claim ceiling, and reentry path before forcing P1-P4. Related documents are supporting evidence; standalone documents are not enough. |

Non-WFF artifacts are external material, not phase handoff. A standalone non-WFF PRD is demand source material for `wff-req-chat` / `wff-req`, not accepted P1 truth. A standalone technical design, standalone implementation package, or standalone test report is not enough for PX and must not be treated as accepted P2/P3/P4 evidence. PX may use related documents only when a code-backed existing-system assessment has repo/runtime/system facts to inspect.

## Internal Continuation Routes

These routes are available only inside an already-admitted WFF chain. They are not external entry routes.

| WFF-native upstream artifacts | Internal continuation | Required boundary |
|---|---|---|
| Accepted WFF P1 PRD or accepted WFF business truth package | `wff-arch` | P2 may design from accepted P1 truth; it must not invent missing demand truth. |
| Accepted WFF P2 handoff / ESP / `phase-3-implementation-entry.md` | `wff-impl` | P3 may implement from accepted design; it must return upstream if topology, contracts, or behavior are not frozen enough. |
| WFF P3 implementation output and evidence package | `wff-validation` | P4 may judge evidence and claim ceilings; it must not create missing implementation evidence. |

If the artifact was not produced by WFF or accepted through a WFF upstream gate, treat it as external material and route through admission again.

## Support Routes

| User starting point | Route to | Boundary |
|---|---|---|
| User wants PM/Architect/Programmer/QA/Reviewer-style entry surfaces | `wff-role-agents` | Role agents are entry wrappers over WFF skills, not a separate lifecycle runtime. |
| Project is not initialized, WFF resources cannot be found, or install layout is confusing | `wff-init`; use `wff-help` only as deprecated init-only compatibility guidance | Init support does not own lifecycle artifacts. |

## Scenario Acceptance Cases

Use these examples as concrete routing acceptance cases. Match the user's actual state, not just the nouns in the request.

| ID | User signal | Decision | Route | Expected boundary |
|---|---|---|---|---|
| S01 | User asks for a focused bug fix, such as fixing a null-pointer bug in one function. | Do not use WFF | normal-engineering | Treat as a focused bug fix; do not wake lifecycle routing. |
| S02 | User asks for a local refactor, such as splitting one module while preserving tests. | Do not use WFF | normal-engineering | Treat as local refactor unless requirement/design/validation ambiguity appears. |
| S03 | User has a rough idea and wants to talk it through before requirements exist. | Use WFF intake | wff-req-chat | Produce or refine P1-ready input material, not a full PRD yet. |
| S04 | User brings chat history, scattered notes, or mixed business background for structuring. | Use WFF intake | wff-req-chat | Stabilize source material before formal P1 generation. |
| S05 | User provides a stable brief and asks for PRD generation. | Use WFF P1 | wff-req | Generate P1 requirements artifacts with evidence and review-bound gaps. |
| S06 | User provides a P1 input packet and asks to continue to PRD. | Use WFF P1 | wff-req | Treat the packet as P1 source input, not as accepted downstream truth. |
| S07 | User is taking over a legacy system and asks to understand current state and risk before changes. | Use WFF assessment | wff-x | Establish baseline, risks, safety net, and route recommendation before edits. |
| S08 | User brings a standalone non-WFF PRD and asks whether architecture can consume it. | Use WFF intake | wff-req-chat | Treat it as demand source material; must not route to `wff-x` or `wff-arch`. |
| S09 | User brings a standalone non-WFF design and asks whether implementation can consume it. | Do not use WFF downstream | normal-review | It is not a WFF P2 handoff and standalone documents are not enough for PX. |
| S10 | User brings a standalone non-WFF implementation or test package and asks whether it can close. | Do not use WFF downstream | normal-review | It is not WFF P3 evidence and standalone documents are not enough for PX or P4. |
| S11 | User provides a WFF P1 accepted PRD and asks to continue design. | Use WFF continuation | wff-arch | Name the WFF P1 artifact that permits P2 continuation. |
| S12 | User provides a WFF P2 handoff / ESP / phase-3 implementation entry and asks to implement. | Use WFF continuation | wff-impl | Name the WFF P2 handoff that permits P3 continuation. |
| S13 | User provides WFF P3 evidence and asks for closure judgment. | Use WFF continuation | wff-validation | Name the WFF P3 evidence that permits P4 continuation. |
| S14 | User says WFF is installed but project resources or `.wff/` metadata cannot be found. | Use support route | wff-init | Repair or explain init/resource lookup; `wff-help` remains init-only compatibility. |
| S15 | User wants role-based entry through PM/Architect/Programmer/QA/Reviewer-style usage instead of skill names. | Use support route | wff-role-agents | Explain role wrappers without treating them as a separate lifecycle runtime. |
| S16 | User brings an existing repo/runtime plus code-backed docs such as PRD, design, API, DB, ops, or test notes. | Use WFF assessment | wff-x | Run code-backed existing-system assessment; Related documents are supporting evidence, standalone documents are not enough. |

## Negative Route Guards

These cases protect the three-entry boundary from drifting back into direct internal phase routing.

| ID | User signal | Safe route | Guard |
|---|---|---|---|
| N01 | focused bug fix or direct small code change | normal-engineering | Do not use WFF; handle as normal engineering work. |
| N02 | standalone non-WFF PRD asks to enter architecture | wff-req-chat | External material must not route to `wff-x` or `wff-arch` until WFF P1 truth is accepted. |
| N03 | standalone non-WFF design asks to enter implementation | normal-review | External material must not route to `wff-x` or `wff-impl` until tied to code/system facts or WFF P2 handoff exists. |
| N04 | standalone non-WFF implementation asks to enter validation | normal-review | External material must not route to `wff-x` or `wff-validation` until tied to repo/runtime facts or WFF P3 evidence exists. |
| N05 | standalone non-WFF test report asks to prove release closure | normal-review | External material must not route to `wff-x` or `wff-validation`; assess evidence and claim ceiling first outside WFF unless tied to repo/runtime facts. |

## Choosing A Profile

When the user asks what to install, prefer scenario profiles over raw skill lists:

| Situation | Profile direction |
|---|---|
| First-time user, unsure where to begin | `full-lifecycle` or the smallest scenario profile matching the current task |
| Demand or PRD work | `requirements-prd` |
| Architecture/design continuation from WFF P1 | `architecture-design` |
| Implementation/delivery continuation from WFF P2 | `implementation-delivery` |
| Validation/closure continuation from WFF P3 | `validation-closure` |
| Existing-system or existing-artifact assessment | `brownfield-change`; `phasex-preview` remains a supported compatibility profile for minimal PX packaging |
| Role setup only | `role-agent-companion` |
| Maintainer init/trace tooling only | `support-tooling`; this keeps `wff-help` as init-only compatibility, not a public general entry |

## Plain-Language Routing Pattern

Use this pattern:

```text
Decision: <Use WFF / Do not use WFF>
Start with: <skill/profile or normal engineering path>
Reason: <one or two plain-language sentences>
Next step: <specific first action>
Boundary: <what this route cannot prove or should not claim>
```

If the recommended route is `wff-arch`, `wff-impl`, or `wff-validation`, explicitly name the WFF-native upstream artifact that makes that continuation valid.

## Boundary

`using-wff` may explain admission, routes, and trade-offs, but it does not own lifecycle artifacts or upgrade evidence.

Do not claim:

- a PRD is complete unless `wff-req` evidence supports it
- architecture is accepted unless WFF P2 outputs and review allow it
- implementation is done unless WFF P3 evidence supports it
- validation or release readiness unless WFF P4 evidence supports it
- production approval, owner sign-off, budget approval, real UAT, or production risk acceptance from WFF artifacts alone

## Ambiguity Handling

If the user gives a vague request such as "help me use WFF" or "where do I start", ask one short question or choose the safest route from visible context.

Prefer these questions:

- Is this new work, existing work, or an ordinary local engineering task?
- What do you already have: rough idea, stable demand material, existing system, existing artifact, WFF P1 PRD, WFF P2 handoff, or WFF P3 evidence?
- Are you trying to clarify, generate PRD, assess existing work, continue a WFF chain, initialize resources, or validate claims?
