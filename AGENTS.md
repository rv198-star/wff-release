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

## Review and Historical Challenge Compatibility
- Current generation uses existing OMR -> isolated SQR: OMR is open-ended, SQR receives no OMR findings/results, and neither becomes generation self-evaluation or a repeated approval. P3 T2/conflict/infeasible gaps use one small decision call per triggered slice; do not run a challenge/re-challenge loop for gap decisions.
- Historical protocol description only: `CLAIM -> EXTRACT -> CHALLENGE -> RECONCILE -> STOP` records may contain a reviewer packet limit of `64 KiB, 20 contexts, 50 unknowns and 100 findings`. The historical constraint “Extra nested fields are rejected” describes those stored packet identities; it does not prescribe a new provider schema, review round, or runtime call in this cycle.
- Cross-model review is optional and requires explicit per-invocation authorization. It cannot add a standing role, approval round, or calls beyond the declared limit.
- Compatibility reading accepts frozen `bounded-challenge-integrity-v1` and `legacy-pre-bounded-challenge-v1` artifacts with their original identities/digests and explicit evidence/claim ceilings. Current P2 review uses `p2-omr-sqr-integrity-v1`. A WFF format upgrade never requires regeneration of frozen P1/P2 or fabricates new review proof. Historical challenge metadata is read-only evidence, not an instruction to rerun the old protocol.

## Generation and One-Directional Delivery
- Workflow owns global order, each stage's fixed generation route, and template instantiation/assembly; Agentic owns business judgment, pattern selection/parameters/trimming, bounded business slots, reasoned inference, and recorded gap decisions.
- Templates own reusable structure, fixed expression, and selectable patterns. They carry no business answers/defaults and never pad output to a quota. Evidence verifies identities and claims; upstream coverage is feedback, not a completeness gate.
- Within a cycle, P1 -> P2 -> P3 (-> P4) stays one-directional. Accepted P1/P2 remain frozen; P4 sends implementation defects and gaps to P3. T0 implementation detail and T1 reasoned inference stay in P3; T2 new facts, explicit conflicts, and infeasible facts use the existing Authority Delta protocol. Only a recorded gap decision with `supersedes` can override an explicit fact locally; `upstream_reconciled = false` remains mandatory.
- P3 alone decides triggered gaps once per slice before implementation: reuse existing topic decisions, then delegation rules, then a decision card. Workflow applies the approved conservative defaults and marks sensitive choices for confirmation. No role meeting, new Authority path/store, or extra review round is introduced. Queue next-version backport; only a human may end a cycle for a fundamentally wrong direction. In P3-capable profiles, use the bundled gap-decision runtime with the existing Journal and bounded transport. Count actual resends toward the declared cap, compare actual schema/config hashes against frozen IDs and registered deltas, and include T2 records in the original OMR and isolated SQR. Missing review remains explicit; it is not acceptance. P3-capable profiles can admit a SHA-bound partial frozen-input decision through the existing frontend entry; keep original IDs, inherited gaps and source claim ceilings in the canonical P3 authority. This selected execution does not create missing upstream review receipts or full-delivery authority. Realized-fact inventory follows the actual representation: resolve local OpenAPI references and JSON `contentSchema` fields; use the explicit `sqlite-ddl` format for supported SQLite tables, simple indexes and immutable-row triggers. Register each complete SQLite definition so constraints cannot disappear behind column parsing. Unsupported DDL remains an evidence gap. A consumed config may supply `x-wff-fact-id` to distinguish a representation from an original source ID, while preserving its runtime ID and meaning. Zero unregistered facts proves registration only; semantic review findings and runtime limitations remain authoritative.
- Keep calls within approximately 60K request tokens, 8K output tokens, and local schema depth three. Allow at most two diagnostic repairs per section, then deliver a T1/T2 gap and retain accepted sections. Split/simplify oversized sections; no budget/retry/rule expansion or model-written composition language. Development may use single-scenario single-section evidence; frozen batches and 3/3 apply only at formal exit.
- Follow the bundled phase contracts and `docs/governance/bounded-generation-run-governance-v1.md` when present for declared call/token caps, JSONL evidence, and human stop-loss. Two consecutive rounds without measurable progress or two failed acceptances stop for the Owner. No run-until-PASS or continued spending merely because budget remains.

## Boundaries
- WFF evidence supports development / pre-production claims unless a separate real-world approval record says otherwise.
- Do not claim real UAT, production release approval, owner sign-off, budget approval, or production risk acceptance from this pack alone.
- Do not copy the repository-level `AGENTS.md` into business projects or install packs; it is repository maintenance context, not released user guidance.

## Pack Identity
- pack_name: `wff-v1.10.0-skills-install-pack`
- install_set_id: `full-pack`
- source_revision: `1ad24accaf96dcb5422dccd94140c32934d41c73`
