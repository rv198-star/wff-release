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

It also records the WFF install-pack resource root when one can be found. This matters when skills live in a platform directory but companion support resources live under project `.wff/<install-pack>/` or user `~/.wff/<install-pack>/`.

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
4. project `.wff/<install-pack>/skills`
5. project `.agents/skills`
6. project `.opencode/skills`
7. project `.codex/skills`
8. project `.claude/skills`
9. user `~/.wff/skills`
10. user `~/.wff/<install-pack>/skills`
11. user `~/.agents/skills`
12. user `~/.config/opencode/skills`
13. user `~/.codex/skills`
14. user `~/.claude/skills`
15. install-pack or repo `skills/`

The required probe is:

```text
wff-base-traceability-management/scripts/init_registry.py
```

For OpenCode, prefer one user-level WFF install directory per HOME. OpenCode also auto-loads `~/.claude/skills/` and `~/.agents/skills/`, so installing the same WFF skill set into multiple user-level platform directories can produce duplicate-skill warnings.

## Resource Root Model

Do not treat `skills_root` and `resource_root` as the same thing:

- `skills_root` points to installed skill directories.
- `resource_root` points to the whole WFF install pack that contains companion support directories.

When WFF says a companion resource is missing, first check `.wff/wff-project.json`. If it contains `resource_root`, use that install-pack root before claiming the resource is absent.

Automatic resource-root discovery checks:

1. `WFF_RESOURCE_ROOT`
2. `WFF_INSTALL_ROOT`
3. project `.wff/<install-pack>/`
4. user `~/.wff/<install-pack>/`
5. the current install-pack or repo root

## Conflict Handling

If `.wff/skills/wff-base-traceability-management` already exists and is valid, `wff-init` skips it.

If it is a broken symlink, `wff-init` may replace it.

If it is a normal file or directory, `wff-init` stops and asks the user to remove or rename that path manually. Do not tell the user that WFF will overwrite it.

## Completion

After `wff-init` succeeds, tell the user that wrapper and mainline scripts can now resolve the WFF base traceability skill through the project-local `.wff/` attachment. If `.wff/wff-project.json` records `resource_root`, also tell them WFF can use that root to find companion support resources, including a global user-domain install pack under `~/.wff/<install-pack>/`.
