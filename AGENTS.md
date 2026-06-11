# WFF Skills Install Pack Guide

This `AGENTS.md` is generated for this install pack. It is not the authoring repository's long work-control `AGENTS.md`.
Use it as the concise agent-facing guide for the WFF Skills shipped in this package.

## How To Use These Skills
- Install whole directories from `skills/`; do not copy only individual `SKILL.md` files.
- Keep this install-pack root visible to the agent runtime whenever skills reference bundled support assets.
- Keep bundled support directories available: `scripts/`, `docs/`, `templates/`, `reference-packages/`, `runtime-deps/`.
- Use `using-wff` first when the user is unsure where to start; use `wff-help` and `wff-init` only for project initialization compatibility.
- Use `wff-req-chat` only for rough or truth-uncertain intake; use `wff-req`, `wff-arch`, `wff-impl`, `wff-validation`, and `wff-x` for formal lifecycle work when those skills are included.
- Optional role agents must route back to WFF skills, profiles, and evidence boundaries; they do not replace lifecycle phases.
- Run network-dependent validation or deployment only where network, Docker Compose v2+, and the required toolchain are available; do not burn retries inside restricted sandboxes.

## Runtime Environment
- Before P3 / P4 / PX / release validation, check Python 3.10+, Node.js 18+ (Node 22 preferred), pnpm matching the generated P3 workspace `packageManager` field (currently `pnpm@9.0.0`), Docker with Compose v2+ (`docker compose`), and outbound network access.
- Install or upgrade missing tools before running validation; do not wait for predictable runtime failures.
- If the current sandbox blocks network, Docker Compose v2+, or dependency bootstrap, move to a capable environment before starting network-dependent validation.

## Entry Skills In This Pack
- `using-wff`
- `wff-help`
- `wff-req-chat`
- `wff-req`
- `wff-arch`
- `wff-impl`
- `wff-validation`
- `wff-x`
- `wff-role-agents`

## Boundaries
- WFF evidence supports development / pre-production claims unless a separate real-world approval record says otherwise.
- Do not claim real UAT, production release approval, owner sign-off, budget approval, or production risk acceptance from this pack alone.
- Do not copy the repository-level `AGENTS.md` into business projects or install packs; it is repository maintenance context, not released user guidance.

## Pack Identity
- pack_name: `wff-v1.5.3-skills-install-pack`
- install_set_id: `full-pack`
- source_revision: `274a13ab68caa447ee71d52a460b76b9a4fe037c`
