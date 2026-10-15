---
name: wff-role-agents
description: Use when a WFF user wants the optional role-agent companion model, role-to-skills map, role boundaries, plain-language professional role guidance, or platform config export through wff-agent. This skill does not run agents or call LLM APIs.
---

# WFF Role Agents

## Scope

`wff-role-agents` describes the optional WFF role-agent companion layer.

It does not run Agents, call LLM APIs, or replace WFF workflow.

It can be paired with the release-packaged `wff-agent` entrypoint to export role files for:

- OpenCode: `.opencode/agents/`
- Claude Code: `.claude/agents/`
- Codex: `.codex/wff-agents/` plus an `AGENTS.md` reference block

The WFF mainline remains:

```text
Skills / Profiles / Project Context / Workflow / Evidence
```

Role agents are profession-shaped entry surfaces over existing WFF skills and profiles.

## First Role Set

- `WFF Product Manager`
- `WFF Architect`
- `WFF Programmer`
- `WFF QA Tester`
- `WFF Refactor Architect`
- `WFF Reviewer`

There is no `WFF Guide` role. General WFF entry routing is owned by `using-wff`; project initialization compatibility remains with deprecated `wff-help`.

## Source Of Truth

Role mounts are defined in:

```text
config/wff-role-mounts.json
```

The rendered human-readable reference is:

```text
docs/role-agent-mounts/v1.4-role-agent-mounts.md
```

The public user guide with diagrams, platform setup, examples, and troubleshooting is:

```text
docs/WFF-ROLE-AGENTS.zh-CN.md
```

If these support files are not visible from the installed skill directory, check
the current project `.wff/wff-project.json` first. When it records
`resource_root`, use that install-pack root to resolve `config/`, `docs/`, and
other bundled support assets before reporting them missing.

Resource root fallback order:

1. `WFF_RESOURCE_ROOT`
2. `WFF_INSTALL_ROOT`
3. project `.wff/<install-pack>/`
4. user `~/.wff/<install-pack>/`
5. the current install-pack or repository root

The platform export command is:

```text
wff-agent setup <opencode|claude-code|codex> <all|role-id...> --project-root <project>
```

Examples:

```text
wff-agent setup opencode all --project-root /path/to/project
wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/project
wff-agent setup codex wff-product-manager --project-root /path/to/project
```

Codex export is intentionally a documented fallback. It writes role instruction files and an `AGENTS.md` reference block; it does not claim native role switching.

Use the manifest to understand:

- which skills each role can use
- which profiles each role can route to
- what each role is forbidden to own
- where each role should return a problem
- what evidence boundary applies

## Core Rule

Role ability comes from mounted WFF skills, not from personality text.

```text
Role = mounted skills + allowed profiles + routing rules + evidence boundary
```

## In-cycle problem routing

The role set is unchanged. Roles are optional entry surfaces; P3 gap decisions do not call them at runtime. P3 remains the sole T0/T1/T2 decision maker under `reference-packages/phase3-implementation-delivery/p3-realization-decisions-contract.md`.

| Existing role | Problem destination within the delivery cycle |
|---|---|
| WFF Product Manager | Before P1 admission, missing source goes to intake/context completion; after P1/P2 freeze, downstream product gaps go to P3 decisions and next-version backport. |
| WFF Architect | Resolve current P2 authoring locally; frozen product/architecture gaps found downstream go to P3 decisions and next-version backport. |
| WFF Programmer | Repair implementation in P3; resolve T2/conflict/infeasible gaps in P3 with conservative defaults and `backport_target`. |
| WFF QA Tester | P4 consumption errors stay P4; implementation defects and product/architecture gaps go to P3, which owns repair or gap decisions. |
| WFF Refactor Architect | Respect the admitted change scope; preserve frozen artifacts and queue upstream absorption for the next version. |
| WFF Reviewer | Send findings to the current artifact owner; downstream implementation/gap findings go to P3, without convening an approval panel. |

This is the in-cycle contract. `config/wff-role-mounts.json` routes frozen business/architecture gaps to WFF Programmer for `p3-gap-decision-required`, the existing Authority Delta ledger and next-version backport. It never requests current-cycle P1/P2 regeneration or a role meeting.

No role can regenerate frozen P1/P2 in-cycle. Report a fundamentally wrong direction to a human for a cycle-termination decision. Missing external approval remains review-bound; a role never supplies it.

## Human Communication Contract

All WFF roles must explain hard ideas in plain language first.

Use short stories, examples, or close analogies before WFF terms.

Do not build an abstract jargon wall.

Bad:

```text
Current source truth admission fails the evidence boundary.
```

Better:

```text
We still do not know who decides to buy, why this must happen now, or what result counts as success.
If we skip that, the PRD may look complete but will be guessing.
WFF calls this a source truth gap.
```

## WFF Core Contract Binding

- Machine descriptor: `role-agent-adaptation` under `wff-core-contract` `1.0.0`.
- Consumes `lifecycle-route-contract`, `extension-registration-contract`, and `agentic-boundary-contract`.
- Core supplies route/ownership structure only; role prompts remain an adaptation surface over mounted Skills and cannot become a second methodology.
- Missing or incompatible Core metadata blocks export instead of silently inventing a role capability.

## Boundaries

- Product Manager does not own architecture.
- Architect does not invent business truth.
- Programmer does not redesign module boundaries.
- QA Tester does not replace final human review.
- Refactor Architect does not make PhaseX a default Phase-5.
- Reviewer does not produce the mainline artifact it reviews.
