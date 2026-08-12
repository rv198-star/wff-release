# WFF Skills Install Pack Guide

This `AGENTS.md` is generated for this install pack. It is not the authoring repository's long work-control `AGENTS.md`.
Use it as the concise agent-facing guide for the WFF Skills shipped in this package.

## How To Use These Skills
- Install whole directories from `skills/`; do not copy only individual `SKILL.md` files.
- Keep this install-pack root visible to the agent runtime whenever skills reference bundled support assets.
- Keep bundled support directories available: `scripts/`, `docs/`, `templates/`, `reference-packages/`, `runtime-deps/`.
- Use `using-wff` first when the user is unsure where to start.
- `scripts/wff_core` is the shared WFF Core 1.0.0 semantic runtime. It defines lifecycle, handoff, evidence, and claim envelopes; it is not a plugin SDK, lifecycle phase, or owner of product/architecture/implementation truth.
- Use `wff-help` for packaged support guidance; use `wff-init` for project initialization compatibility.
- Use `wff-req-chat` only for rough or truth-uncertain intake.
- For formal lifecycle work in this pack, use `wff-req`, `wff-arch`, `wff-impl`, `wff-validation`, and `wff-x` when that phase is in scope.
- Optional role agents must route back to WFF skills, profiles, and evidence boundaries; they do not replace lifecycle phases.
- Run network-dependent validation or deployment only where network, Docker Compose v2+, and the required toolchain are available; do not burn retries inside restricted sandboxes.

## Runtime Environment
- Before P3 / P4 / PX / release validation, check Python 3.12, Node.js 18+ (Node 22 preferred), pnpm matching the generated P3 workspace `packageManager` field (currently `pnpm@9.0.0`), Docker with Compose v2+ (`docker compose`), and outbound network access.
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

## Bounded Agentic Challenge
- Use `CLAIM -> EXTRACT -> CHALLENGE -> RECONCILE -> STOP` only for the explicit high-risk triggers named by the current P1/P2/P3/P4 Skill. It is not a global Gate or a new lifecycle stage.
- Keep the owner's preferred CLAIM and reasoning out of the reviewer packet. Provide only exact artifact/contract/context identity + digest rows, bounded unknowns, and an issues-first instruction. Extra nested fields are rejected. The review packet is capped at 64 KiB, 20 contexts, 50 unknowns and 100 findings per cycle; decompose larger units before review.
- The phase Agentic owner reconciles every material finding and remains the decision owner. Actionable findings require substantive change and re-challenge of the changed unit; review-bound findings remain visible.
- Default depth is one pass and maximum depth is three. TDD RED may directly challenge behavioral claims. Cross-model review is optional and requires explicit per-invocation authorization; failures or skips remain visible.
- New authority publication requires `bounded-challenge-integrity-v1` and an exact decision/evidence challenge binding. `legacy-pre-bounded-challenge-v1` artifacts remain readable historical proof only; rerun the owning phase before using them to publish new downstream authority.

## Boundaries
- WFF evidence supports development / pre-production claims unless a separate real-world approval record says otherwise.
- Do not claim real UAT, production release approval, owner sign-off, budget approval, or production risk acceptance from this pack alone.
- Do not copy the repository-level `AGENTS.md` into business projects or install packs; it is repository maintenance context, not released user guidance.

## Pack Identity
- pack_name: `wff-v1.9.2-skills-install-pack`
- install_set_id: `full-pack`
- source_revision: `fab0cee6f9ef7346469a858dbc75724adf06069b`
