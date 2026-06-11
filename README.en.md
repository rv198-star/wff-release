# WFF Skills Install Pack

This archive is the public install pack for WFF skills.

It is intentionally smaller than the internal project export bundle.
It includes only shipped skills plus the scripts, docs, templates, reference packages, and release cases that those skills directly point to.

## Identity
- pack_name: `wff-v1.3.17-skills-install-pack`
- generated_at: `2026-05-19T15:05:56+00:00`
- source_revision: `abcc0798fa8f701d4ec258e26f83130515a57fe8`

## Capability Boundary
- `Phase 1` to `Phase 4`: GA mainline capability
- `Phase X`: Preview / Incubating
- v1.3 control model: Workflow shell + Agentic core + Evidence bridge
- This pack preserves lifecycle order, leaves high-uncertainty product / architecture / implementation judgment to Agentic reasoning, and uses evidence / gates to cap claims.

## Install Model
1. Install `skills/wff-base-traceability-management/` first.
2. Install `skills/wff-help/` when the user needs project init guidance after installing WFF Skills.
3. Install `skills/wff-req-chat/` first only when the starting input is rough, scattered, or truth-uncertain.
4. Install the phase orchestrator you need.
5. Install the companion worker or stage skills for that phase.
6. Keep bundled `scripts/`, `docs/`, `templates/`, `reference-packages/`, and `release-cases/` visible when a skill points to them.
   `examples/` is retained only as a retired pointer.

The installation unit is the whole skill directory, not just `SKILL.md`.
Do not flatten all skills into one directory, and do not copy only the `SKILL.md` files.

## Expected Directory Shape After Unzip
```text
wff-v1.3.17-skills-install-pack/
├── README.md
├── wff-init
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
├── release-cases/
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

Keep the unpacked install-pack root, or an equivalent copy of its support directories, accessible whenever installed skills refer to `scripts/`, `docs/`, `templates/`, `reference-packages/`, or `release-cases/`.

## Two Common Project Layouts
**Layout A: platform-standard skills directory plus WFF resource root**

Use this when your agent platform only scans a fixed directory such as `.claude/skills/`.

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
│   └── wff-v1.3.17-skills-install-pack/
│       ├── scripts/
│       ├── docs/
│       ├── templates/
│       ├── reference-packages/
│       ├── release-cases/
│       └── runtime-deps/
└── ...
```

In this layout, `.claude/skills/` contains copied or imported skill directories, while `.wff/` keeps the WFF support assets. Do not put WFF support scripts under a misspelled or ad hoc directory such as `.claud/scripts`.

**Layout B: keep the whole install pack intact**

Use this when your agent platform can import skills from an arbitrary directory or can register the pack's `skills/*` directories directly.

```text
/Users/edy/project/party/
└── wff-v1.3.17-skills-install-pack/
    ├── skills/
    ├── scripts/
    ├── docs/
    ├── templates/
    ├── reference-packages/
    ├── release-cases/
    └── runtime-deps/
```

Layout B has the lowest risk of broken relative references. Layout A better fits platforms with a standard skills folder, but you must still preserve the WFF resource root.

## Project Init
After installing WFF Skills, initialize each target business project so runtime wrappers can find the WFF base skill from project-local `.wff/`:

```bash
cd /path/to/your-project
/path/to/wff-v1.3.17-skills-install-pack/wff-init
```

`wff-init` is safe for existing projects: it only creates or updates `.wff/` and stops on conflicts instead of overwriting business files.

Supported parameters:

- `--project-root <path>`: target business project directory; defaults to the current directory.
- `--skills-root <path>`: installed WFF skills root; defaults to automatic discovery.

## Runtime Note
- Phase 3 generates a Node.js workspace that still needs dependency bootstrap before dispatch execution.
- For runtime closure, run `python3 scripts/phase3/run_phase3_first_version.py --mainline-verification-mode strict-runtime ...` or `python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-output-dir> --install --strict --output <phase3-output-dir>/phase3-toolchain-bootstrap.json`; delivery-ready also requires `runtime-smoke-report.json` and `started-service-smoke-report.json`.
- Equivalent direct command: `pnpm install --dir <phase3-output-dir> --frozen-lockfile=false`.
- For isolated Release SKILLS verification against the retained `GEO + PetClinic` source briefs, run `python3 scripts/release/run_release_dual_case_eval.py --workspace-root <isolated-workspace> --prepare-only` first, then rerun without `--prepare-only` when you want the actual execution. Actual execution defaults `--case-workers` to the requested case count; pass `--case-workers 1` to preserve sequential case execution.

## Included Top-Level Dirs
- `config`
- `docs`
- `reference-packages`
- `release-cases`
- `runtime-deps`
- `scripts`
- `skills`
- `sources`
- `templates`

## Notes
- This pack is the public GitHub Release asset.
- The larger `build_skill_release_bundle.py` export remains an internal project-export workflow, not the public install asset.
- `docs/` here is a selected runtime/support subset, not the full repository docs tree.
- The final v1.3 proof snapshot is retained in the authoring repository, not inside this public install pack; it proves development / pre-production lifecycle closure only.
- For Phase-1, the canonical gate surface is `run_phase1_full_trial.py` / `run_phase1_convergence.py` plus `stage_depth/quality/executability`; the four assembly/analyze/section/consistency gate scripts remain only as bundle-internal compatibility scripts for now.

## Metadata Files
- `SKILL_INSTALL_PACK_MANIFEST.json`
- `SKILL_INSTALL_PACK_AUDIT.json`
- `INSTALL_PACK_AUDIT.md`
