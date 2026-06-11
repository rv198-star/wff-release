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

There is no `WFF Guide` role. Entry help remains owned by `wff-help`.

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

## Boundaries

- Product Manager does not own architecture.
- Architect does not invent business truth.
- Programmer does not redesign module boundaries.
- QA Tester does not replace final human review.
- Refactor Architect does not make PhaseX a default Phase-5.
- Reviewer does not produce the mainline artifact it reviews.
