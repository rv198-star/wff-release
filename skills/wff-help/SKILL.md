---
name: wff-help
description: Use when a user has installed WFF Skills and needs help initializing the current project, understanding where WFF runtime files should live, or recovering from project-level WFF install layout confusion. In v1.3.14 this skill only supports project init guidance.
---

# WFF Help

Use this skill when the user has installed WFF Skills but is not sure how to make a new or existing project runnable with WFF.

## Supported Task In v1.3.14

Only one task is supported:

- initialize or repair the current project's `.wff/` runtime attachment with `wff-init`

Do not present this skill as a general WFF doctor, global installer, lifecycle phase runner, or interactive onboarding assistant.

## Project Init Guidance

Tell the user that `wff-init` is safe for existing projects because it only creates or updates `.wff/` by default.

It must not modify:

- business source code
- `package.json`, `pyproject.toml`, or build files
- `.claude/`
- `.codex/`

It creates or updates:

- `.wff/skills/wff-base-traceability-management`
- `.wff/wff-project.json`
- `.wff/README.md`

## Default Command

If the user is already in the target project directory, use:

```bash
/path/to/wff-v1.3-skills-install-pack/wff-init
```

If the user is not in the target project directory, use:

```bash
/path/to/wff-v1.3-skills-install-pack/wff-init --project-root /path/to/your-project
```

If automatic skills discovery fails, use:

```bash
/path/to/wff-v1.3-skills-install-pack/wff-init --skills-root /path/to/installed/skills
```

## Supported Parameters

Only these two parameters are supported:

- `--project-root <path>`: target business project directory; defaults to the current directory.
- `--skills-root <path>`: installed WFF skills root; defaults to automatic discovery.

Do not suggest `--dry-run`, `--yes`, `--force`, `--mode`, global install commands, or business-project scaffolding for v1.3.14.

## Discovery Model

Explain that `wff-init` searches for installed skills in this order:

1. `--skills-root`
2. `WFF_SKILLS_ROOT`
3. project `.wff/skills`
4. project `.codex/skills`
5. project `.claude/skills`
6. user `~/.codex/skills`
7. user `~/.claude/skills`
8. install-pack or repo `skills/`

The required probe is:

```text
wff-base-traceability-management/scripts/init_registry.py
```

## Conflict Handling

If `.wff/skills/wff-base-traceability-management` already exists and is valid, `wff-init` skips it.

If it is a broken symlink, `wff-init` may replace it.

If it is a normal file or directory, `wff-init` stops and asks the user to remove or rename that path manually. Do not tell the user that WFF will overwrite it.

## Completion

After `wff-init` succeeds, tell the user that wrapper and mainline scripts can now resolve the WFF base traceability skill through the project-local `.wff/` attachment.
