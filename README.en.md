# WFF Skills Install Pack

This archive is the public install pack for WFF skills.

It is intentionally smaller than the internal project export bundle.
It includes only shipped skills plus the scripts, docs, templates, reference packages, and runtime dependencies that those skills directly point to.

First read: open `WFF-START-HERE.md` for the short entry map before scanning the full pack.

## Identity
- pack_name: `wff-v1.4.2-skills-install-pack`
- generated_at: `2026-06-01T21:47:33+00:00`
- source_revision: `3fe263b1bd3e28bf4164181e37655caf9c2e37dc`

## Capability Boundary
- `Phase 1` to `Phase 4`: GA mainline capability
- `PX`: existing-system intake, refactoring, migration, and capacity-change scenarios
- Release-facing source governance is shipped under `docs/source-registers/`; repo-local `docs/internal/` work records are not user runtime assets.
- Retained proof snapshots remain in the authoring repository and are not install-pack payload.
- This pack preserves lifecycle order; uncertain product, architecture, and implementation judgment stays with the Agent.
- Tests, runtime results, and Review only support the conclusions they can actually prove.
- Phase 4 is published as a single `wff-validation` entry skill whose acceptance, evidence, and closure responsibilities stay inside the entry skill.

## Install Model
1. Install `skills/wff-base-traceability-management/` first.
2. Install `skills/wff-help/` when the user needs project init guidance after installing WFF Skills.
3. Install `skills/wff-req-chat/` first only when the starting input is rough, scattered, or truth-uncertain.
4. Install the phase orchestrator you need.
5. Install the support skills required by that phase. For Phase 3, prefer the `implementation-delivery` install set; security audit and handoff packaging are usually invoked by `wff-impl`, not chosen as first-level user entries.
6. Keep bundled `scripts/`, `docs/`, `templates/`, `reference-packages/`, and `runtime-deps/` visible when a skill points to them.
   The full install pack may live under project `.wff/<install-pack>/` or user-global `~/.wff/<install-pack>/`.
   `examples/` is retained only as a retired pointer.

The installation unit is the whole skill directory, not just `SKILL.md`.
Do not flatten all skills into one directory, and do not copy only the `SKILL.md` files.

## Expected Directory Shape After Unzip
```text
wff-v1.4.2-skills-install-pack/
├── AGENTS.md
├── README.md
├── wff-init
├── wff-agent
├── SKILL_INSTALL_PACK_MANIFEST.json
├── skills/
│   ├── wff-base-traceability-management/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml    # when provided by that skill
│   ├── wff-help/
│   ├── wff-req-chat/
│   ├── wff-req/
│   ├── wff-arch/
│   ├── wff-impl/
│   ├── wff-validation/
│   └── wff-x/
├── scripts/
├── docs/
├── templates/
├── reference-packages/
└── runtime-deps/
```

## Expected Platform-Side Skill Shape
The exact managed folder depends on the AI agent platform, but preserve one directory per skill:

```text
<platform-skills-root>/
├── wff-base-traceability-management/
│   ├── SKILL.md
│   └── agents/openai.yaml        # if your platform imports it
├── wff-req-chat/
│   └── SKILL.md
├── wff-req/
│   └── SKILL.md
└── ...
```

Keep the unpacked install-pack root, or an equivalent copy of its support directories, accessible whenever installed skills refer to `scripts/`, `docs/`, `templates/`, `reference-packages/`, or `runtime-deps/`. WFF can discover this root from project `.wff/<install-pack>/`, user-global `~/.wff/<install-pack>/`, `WFF_RESOURCE_ROOT`, or `WFF_INSTALL_ROOT`.

## Two Common Project Layouts
**Layout A: platform-standard skills directory plus WFF resource root**

Use this when your agent platform only scans a fixed directory. Common directories include Claude Code `.claude/skills/`, Codex `.agents/skills/`, OpenCode project `.opencode/skills/`, and OpenCode user `~/.config/opencode/skills/`. OpenCode also auto-loads `~/.claude/skills/` and `~/.agents/skills/`, so avoid installing the same WFF skill set into multiple user-level platform directories under one HOME.

```text
/Users/edy/project/party/
├── .claude/
│   └── skills/
│       ├── wff-base-traceability-management/
│       ├── wff-req-chat/
│       ├── wff-req/
│       ├── wff-arch/
│       ├── wff-impl/
│       ├── wff-validation/
│       └── wff-x/
├── .wff/
│   └── wff-v1.4.2-skills-install-pack/
│       ├── scripts/
│       ├── docs/
│       ├── templates/
│       ├── reference-packages/
│       └── runtime-deps/
└── ...
```

In this layout, the platform skills directory contains copied or imported skill directories, while `.wff/` keeps the WFF support assets. The resource root may also live in the user-global domain, for example `~/.wff/<install-pack>/`; `wff-init` records `skills_root` and `resource_root` in `.wff/wff-project.json`. Do not put WFF support scripts under a misspelled or ad hoc directory such as `.claud/scripts`.

**Layout B: keep the whole install pack intact**

Use this when your agent platform can import skills from an arbitrary directory or can register the pack's `skills/*` directories directly.

```text
/Users/edy/project/party/
└── wff-v1.4.2-skills-install-pack/
    ├── skills/
    ├── scripts/
    ├── docs/
    ├── templates/
    ├── reference-packages/
    └── runtime-deps/
```

Layout B has the lowest risk of broken relative references. Layout A better fits platforms with a standard skills folder, but you must still preserve the WFF resource root.

## Project Init
After installing WFF Skills, initialize each target business project so runtime wrappers can find the WFF base skill from project-local `.wff/`:

```bash
cd /path/to/your-project
/path/to/wff-v1.4.2-skills-install-pack/wff-init
```

`wff-init` is safe for existing projects: it only creates or updates `.wff/` and stops on conflicts instead of overwriting business files. It records `skills_root` and, when found, `resource_root` in `.wff/wff-project.json`.

Supported parameters:

- `--project-root <path>`: target business project directory; defaults to the current directory.
- `--skills-root <path>`: installed WFF skills root; defaults to automatic discovery.

## Role-Agent Platform Adapter
The optional `wff-agent` command exports WFF role-agent files into a target project.
It does not call an LLM, run an agent runtime, or replace WFF lifecycle skills and validation evidence.

```bash
/path/to/wff-v1.4.2-skills-install-pack/wff-agent setup opencode all --project-root /path/to/your-project
/path/to/wff-v1.4.2-skills-install-pack/wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/your-project
/path/to/wff-v1.4.2-skills-install-pack/wff-agent setup codex wff-product-manager --project-root /path/to/your-project
```

OpenCode exports project agents under `.opencode/agents/` with `mode: all`, so they can be used as direct primary agents or @-mentioned subagents. Claude Code exports subagents under `.claude/agents/`. Codex exports role instruction docs under `.codex/wff-agents/` and updates `AGENTS.md`; this is a documented fallback, not native role switching.

For role diagrams, platform-specific usage examples, role selection guidance, and troubleshooting, read `docs/WFF-ROLE-AGENTS.zh-CN.md`.
For the global route map, entry-surface model, and human artifact taxonomy, read `docs/public/wff-orientation-map.zh-CN.md`.

## Runtime Note
- Before P3 / P4 / PX / release validation, check Python 3.10+, Node.js 18+ (Node 22 preferred), pnpm matching the generated P3 workspace `packageManager` field (currently `pnpm@9.0.0`), Docker with Compose v2+ (`docker compose`), and outbound network access. Install or upgrade missing tools before running validation.
- Phase 3 generates a Node.js workspace that still needs dependency bootstrap before dispatch execution.
- Expect Phase 3 strict runtime validation to dominate total runtime cost. Retained v1.4/v1.4.1 dual-case proof evidence shows P3 at about `96%` of recorded phase-step time because it runs implementation proof, not only document generation.
- P3 strict-runtime cost is dominated by full-targeted SQL / contract / scenario / replay evidence, especially contract-heavy API / DB suites that repeatedly restore runtime state. Docker image build / compose startup is a secondary runtime-smoke cost, not the main P3 wall-clock driver. Use `--validation-level fast` or `--validation-level focused` for diagnostics only; these profiles run critical targeted evidence and do not auto-run runtime smoke unless explicitly requested. Do not treat them as release-proof substitutes.
- For strict runtime validation, run `python3 scripts/phase3/run_phase3_first_version.py --mainline-verification-mode strict-runtime ...` or `python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-output-dir> --install --strict --output <phase3-output-dir>/phase3-toolchain-bootstrap.json`; delivery-ready also requires `runtime-smoke-report.json` and `started-service-smoke-report.json`.
- Equivalent direct command: `pnpm install --dir <phase3-output-dir> --frozen-lockfile=false`.
- For isolated Release SKILLS verification against retained source briefs, provide an explicit case-input root under the selected release root, run `python3 scripts/release/run_release_dual_case_eval.py --case-input-root <case-input-root> --workspace-root <isolated-workspace> --prepare-only` first, then rerun without `--prepare-only` when you want the actual execution. Actual execution defaults `--case-workers` to the requested case count; pass `--case-workers 1` to preserve sequential case execution.

## Included Top-Level Dirs
- `config`
- `docs`
- `reference-packages`
- `runtime-deps`
- `scripts`
- `skills`
- `sources`
- `templates`

## Notes
- This pack is the public GitHub Release asset.
- The larger `build_skill_release_bundle.py` export remains an internal project-export workflow, not the public install asset.
- `docs/` here is a selected runtime/support subset, not the full repository docs tree.
- The final v1.4 validation evidence is retained in the authoring repository, not inside this public install pack; it proves development / pre-production lifecycle closure only.
- For Phase-1, the canonical check surface is `run_phase1_full_trial.py` / `run_phase1_convergence.py` plus `stage_depth/quality/executability`; the four assembly/analyze/section/consistency scripts remain only as bundle-internal compatibility scripts for now. See `docs/phases/phase-1/phase-1-gate-authority-map-v0.1.md`.

## Metadata Files
- `SKILL_INSTALL_PACK_MANIFEST.json`
- `SKILL_INSTALL_PACK_AUDIT.json`
- `INSTALL_PACK_AUDIT.md`
