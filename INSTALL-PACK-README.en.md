# WFF Skills Install Pack

This archive is the public install pack for WFF skills. It is smaller than the internal project export bundle and contains only shipped skills plus directly referenced scripts, docs, templates, reference packages, and runtime dependencies.

First read: open `WFF-START-HERE.md` before scanning the full pack.

## Identity
- pack_name: `wff-v1.5.3-skills-install-pack`
- generated_at: `2026-06-11T17:03:49+00:00`
- source_revision: `9a00d94c96149a011092e182e28c79cfa5b3afb6`

## Capability Boundary
- `Phase 1` to `Phase 4`: GA mainline capability.
- `PX`: existing-system intake, refactoring, migration, and capacity-change scenarios.
- Release-facing source governance is under `docs/source-registers/`; repo-local work records are not user runtime assets.
- Retained proof snapshots stay in the authoring repository and are not install-pack payload.
- This pack preserves lifecycle order; uncertain product, architecture, and implementation judgment stays with the Agent.
- Tests, runtime results, and Review only support the conclusions they can actually prove.
- Phase 4 is published as a single `wff-validation` entry skill whose acceptance, evidence, and closure responsibilities stay inside that entry skill.

## Product Entry Boundary
- Start New Work: `wff-req-chat` turns ideas, materials, or conversation into a P1 source input packet before `wff-req`; it does not claim PRD generation, P1 completion, or downstream readiness.
- PX: `wff-x` is a code-backed existing-system assessment. Related documents are supporting evidence; standalone documents are not enough. Use it for code-backed legacy/live systems, refactors, migrations, and capacity work.

## Install Model
1. Install `skills/using-wff/` first for user-facing route selection.
2. Install `skills/wff-base-traceability-management/` for project traceability support.
3. Install `skills/wff-help/` only for deprecated project init compatibility.
4. Install `skills/wff-req-chat/` first only when the starting input is rough, scattered, or truth-uncertain.
5. Install the phase orchestrator and support skills required by your scenario.
6. For Phase 3, prefer the `implementation-delivery` install set; security audit and handoff packaging are usually invoked by `wff-impl`.
7. Keep `scripts/`, `docs/`, `templates/`, `reference-packages/`, and `runtime-deps/` visible when a skill points to them.

The installation unit is the whole skill directory, not just `SKILL.md`. Do not flatten all skills into one directory, and do not copy only the `SKILL.md` files.

## Expected Directory Shape After Unzip
```text
wff-v1.5.3-skills-install-pack/
├── AGENTS.md
├── README.md
├── wff-init
├── wff-agent
├── SKILL_INSTALL_PACK_MANIFEST.json
├── skills/
│   ├── using-wff/
│   ├── wff-base-traceability-management/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
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
Keep one directory per skill under the platform-managed folder:

```text
<platform-skills-root>/
├── wff-base-traceability-management/
│   └── SKILL.md
├── wff-req-chat/
└── ...
```

Installed skills still need access to the unpacked install-pack root or an equivalent copy of support directories. WFF can discover the resource root from project `.wff/<install-pack>/`, user-global `~/.wff/<install-pack>/`, `WFF_RESOURCE_ROOT`, or `WFF_INSTALL_ROOT`.

## Two Common Project Layouts
**Layout A: platform-standard skills directory plus WFF resource root**

```text
/Users/edy/project/party/
├── .claude/
│   └── skills/
│       ├── wff-base-traceability-management/
│       ├── wff-req-chat/
│       ├── wff-req/
│       └── wff-x/
├── .wff/
│   └── wff-v1.5.3-skills-install-pack/
│       ├── scripts/
│       ├── docs/
│       ├── templates/
│       ├── reference-packages/
│       └── runtime-deps/
└── ...
```

Use Layout A when the agent platform scans a fixed skills directory. Do not put WFF support scripts under a misspelled or ad hoc directory such as `.claud/scripts`.

**Layout B: keep the whole install pack intact**

```text
/Users/edy/project/party/
└── wff-v1.5.3-skills-install-pack/
    ├── skills/
    ├── scripts/
    ├── docs/
    ├── templates/
    ├── reference-packages/
    └── runtime-deps/
```

Layout B has the lowest risk of broken relative references.

## Project Init
```bash
cd /path/to/your-project
/path/to/wff-v1.5.3-skills-install-pack/wff-init
```

`wff-init` only creates or updates `.wff/` and stops on conflicts. Supported parameters:

- `--project-root <path>`: target business project directory; defaults to the current directory.
- `--skills-root <path>`: installed WFF skills root; defaults to automatic discovery.

## Role-Agent Platform Adapter
```bash
/path/to/wff-v1.5.3-skills-install-pack/wff-agent setup opencode all --project-root /path/to/your-project
/path/to/wff-v1.5.3-skills-install-pack/wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/your-project
/path/to/wff-v1.5.3-skills-install-pack/wff-agent setup codex wff-product-manager --project-root /path/to/your-project
```

`wff-agent` exports role-agent files. It does not call an LLM, run an agent runtime, or replace WFF lifecycle skills and validation evidence. Read `docs/WFF-ROLE-AGENTS.zh-CN.md` for role guidance and `docs/public/wff-orientation-map.zh-CN.md` for the global route map.

## Runtime Notes
- Check Python 3.10+, Node.js 18+ or preferred Node 22, pnpm matching the generated P3 workspace, Docker with Compose v2+, and outbound network access before P3 / P4 / PX / release validation.
- Phase 3 generates a Node.js workspace and needs dependency bootstrap before dispatch execution.
- Use `--validation-level fast` or `--validation-level focused` for diagnostics only; they do not replace release-proof strict evidence.
- For strict runtime validation, first run `python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-output-dir> --install --strict --output <phase3-output-dir>/phase3-toolchain-bootstrap.json`.
- Equivalent direct command: `pnpm install --dir <phase3-output-dir> --frozen-lockfile=false`.
- The larger `build_skill_release_bundle.py` export remains an internal project-export workflow, not the public install asset.

## Included Top-Level Dirs
- `config`
- `docs`
- `reference-packages`
- `runtime-deps`
- `scripts`
- `skills`
- `templates`

## Notes
- `docs/` here is a selected runtime/support subset, not the full repository docs tree.
- For Phase-1, the canonical check surface is `run_phase1_full_trial.py` / `run_phase1_convergence.py` plus `stage_depth/quality/executability`; the four assembly/analyze/section/consistency scripts remain only as bundle internal compatibility scripts for now. See `docs/phases/phase-1/phase-1-gate-authority-map-v0.1.md`.
