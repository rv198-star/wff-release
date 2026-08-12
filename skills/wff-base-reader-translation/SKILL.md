---
name: wff-base-reader-translation
description: Reader-facing localized artifact translation skill for canonical WFF lifecycle documents. Preserves canonical source truth while producing human-reviewable localized reader editions.
---

# Reader Translation

## Installed Resource Resolution

If a required companion resource appears missing, first inspect project `.wff/wff-project.json`. When it records `resource_root`, treat that path as the WFF install-pack root before declaring the resource absent. This includes user-global installs under `~/.wff/<install-pack>/`.


This is the release-facing skill surface for localized reader artifacts. The packaged runtime entrypoint is `scripts/common/emit_reader_translation.py`; this skill defines the operating contract, quality rules, and review expectations for the reader translation lane.

## Overview

Translate a canonical English lifecycle document (PRD, architecture spec, action card, validation summary) into a reader-facing target-locale edition. The canonical source remains authoritative. The reader artifact is a review surface for human readers who should not need to consult the English original.

## Core Rule

**Produce a reader-facing edition, not a literal translation.** Natural target-locale prose for narrative, decisions, labels, and table cells. Preserve only true technical anchors unchanged.

## Immutable Tokens (whitelist)

These MUST remain exactly as they appear in the source:

- Trace IDs: `P1-...`, `P2-...`, `P3-...`, `P4-...`, `PX-...`, `ARCH-...`, `WP-...`, `RBI-...`, `AC-...`, `RQ-...`, `EP-...`, `BVS-...`, `DR-...`
- Artifact IDs and version strings
- File names and paths (e.g., `scripts/phase1/run_phase1_source_to_prd.py`, `engineering-spec-pack.md`)
- Code, API endpoints (`GET /api/...`), schema field names, database column names
- Object/class/domain identifiers (e.g., `TenantWorkspace`, `ActorRole`, `AuditRecord`, `TrackedScope`)
- Status enum values (`pass`, `fail`, `warn`, `review-ready`, `downstream-start-safe`, `review-bound`, `implementation-ready`)
- Dot-separated package/module/namespace identifiers (e.g., `geo.baseline.generation.and.query`)
- Version values and date stamps in technical contexts

## Translation Rules

### Prose
- Translate all headings, paragraphs, bullet values into natural target-locale language
- For `zh-CN`: use natural Simplified Chinese with local professional expression; avoid stiff literal translation
- Split long English sentences into shorter Chinese ones when facts remain intact
- Business roles, workflow descriptions, judgment labels, rationale prose — all are reader-facing and must be translated
- Snake_case labels used as document labels (not schema fields) must be translated: `document_delivery_state:` → `文档交付状态：`, `evidence_confidence_state:` → `证据置信状态：`

### Tables
- Preserve markdown table structure: pipes, alignment rows, column count, row count
- Translate all reader-facing table headers and cells
- Table headers like `story_or_use_case`, `requirement_class`, `unit_type`, `summary` are reader-facing — translate them
- Field-identifier headers like `requirement_id`, `trace_id`, `target_asset_id` may stay unchanged
- Acceptance criteria rows with Given/When/Then: translate the prose, preserve technical object names

### Terminology
- Choose one stable Chinese term for each recurring concept; use it consistently throughout
- Do not alternate between near-synonyms (评审/复盘/review, 建议/推荐/recommendation)
- After first introduction with English parenthetical, use Chinese-only for subsequent mentions
- Common lifecycle terms: workflow-first→工作流优先, review-bound→待审阅确认, human reviewer→审阅人, downstream-start-safe→可安全启动下游, tracked scope→跟踪范围, finding(s)→发现项, recommendation→建议, task→任务

### What NOT to do
- Do not delete rows, renumber IDs, or change facts
- Do not add external validation, sign-off, budget approval, UAT, or production readiness claims
- Do not leave long English natural-language fragments inside otherwise Chinese text
- Do not preserve English aliases for common roles (marketing owner, business owner, content operator — translate them)
- Do not add commentary, explanations, or meta-notes in the output

## Self-Review

After completing the translation, review it against these criteria:

1. **Reader-facing check (G1)**: Can a Chinese reader understand every section without consulting the English source? Are there any untranslated English prose fragments in reader-facing positions?
2. **Technical anchor check (G2)**: Are all immutable tokens (trace IDs, file paths, code, schema, status enums, versions) intact and unchanged?
3. **Fidelity check (G3)**: Are any facts, rows, claim ceilings, or decisions missing, changed, or upgraded?

## Fix Iteration

- If self-review finds issues, fix them in the same session
- Maximum 2 fix rounds (initial translation + 1 fix pass = 2 total outputs)
- If quality is still insufficient after 2 rounds, stop and note the remaining issues in the integrity section
- Each fix pass should address ALL found issues at once, not one-at-a-time

## Output Format

Return ONLY the translated markdown. No code fences, no commentary, no meta-notes.

The output must include an integrity appendix at the end:

```
> 本地化阅读版（localized reader artifact）
> canonical_of: `<source-filename>`
> target_locale: `<locale>`
> 规则: 保留 trace id、artifact id、状态枚举、文件路径、API/字段名和声明上限；如与 canonical 冲突，以 canonical 为准。
```

## Entrypoints

Executed by Python runtime script `scripts/common/emit_reader_translation.py`:

```bash
python3 scripts/common/emit_reader_translation.py \
  --canonical <canonical.md> \
  --target-locale zh-CN \
  --artifact-label "<label>" \
  --output <reader-output.md>
```

The Python script handles file paths, LLM invocation, recovery, and integrity verification. Agentic reasoning owns semantic segmentation: the planner receives content-derived headings, list-group, table, contract, and fence anchors, and an oversized segment is returned for focused Agentic replanning. Workflow validates coverage and budget, enforces a hard call deadline, and resumes exact completed segments under the accepted source and plan hashes; it must not replace the accepted plan with fixed-line or mid-table splitting. Within the detached reader lane, incomplete translation segments may run with bounded concurrency using one immutable document-level terminology context; completed segment records are checkpointed independently and final assembly always follows source order. `reader_translation.max_parallel_segments` controls the worker bound and does not alter P1-P4 execution or claim state. This skill is the release-facing contract for what the Agentic translation must preserve, translate, and self-review.

## Artifact Acceptance

Use `scripts/release/reader_translation_artifact_acceptance.py` to validate generated reader artifacts after the lane runs. The acceptance check is read-only: it verifies `reader-translation-manifest.json`, generated reader files, integrity JSON files, reader preambles, recomputed immutable-token integrity, and basic structure preservation. This acceptance evidence remains separate from P1-P4 lifecycle gates; missing or failed reader artifacts cap reader-evidence claims instead of blocking canonical lifecycle truth.

## Human Review HTML Sidecar

The built Release package dispatches localized review work after P1, P2, and
P3. Dispatch is detached and P1-P4 never waits for translation or HTML
assembly. Repository development runs default to disabled to avoid repeated
token cost; set `WFF_HUMAN_REVIEW_SIDECAR=1` for an explicit development run or
`WFF_HUMAN_REVIEW_SIDECAR=0` to disable it in a Release workspace.

The worker reuses current integrity-passing readers, makes at most three
attempts, and rejects a result when any source hash changed while work was in
flight. It assembles the accepted `human-review-dossier-manifest.v1`; it does
not create a second lifecycle truth or control lifecycle gates.

Chinese reader terminology is fixed: the machine value `review-bound` displays
as `待审阅确认`; ordinary `human reviewer` displays as `审阅人`; use
`人工审阅者` only when explicitly contrasting a person with AI or automation.
Machine enums, schema values, JSON field names, and claim ceilings remain
unchanged.

Reader translation preserves localized canonical originals. A separate
Agentic semantic-projection lane reorganizes P1 PRD, P2 ESP, and the P3 Action
Card set for human decision-making. Agentic output is an accepted structured
review decision model, not Markdown: each decision retains affected subjects,
rationale, constraints, risks, explicit review questions, and source-bound
evidence anchors. Deterministic code validates the model and renders Markdown;
rendered Markdown cannot replace or mutate the accepted model. Complete Trace, schema,
component, source, test, and control identity coverage belongs in a machine-only
projection sidecar and the canonical originals. Human appendices explain
relationships, responsibility, evidence, risk, and review-bound impact; they
must not reproduce complete ID indexes or naked identifier lists. The P3
projection groups implementation components into a bounded set of human Action
Cards instead of exposing one primary chapter per component, and each card keeps
its machine id separate from its human title. Deterministic code validates
source hashes, machine identity coverage, semantic topic coverage,
main/appendix boundaries, human-readable card titles, and stale-publication
rules; it must not write the semantic summary itself.

For ESP only, the lane may consume the optional
`.wff/architecture-reconstruction/review-input.json` contract. When present,
it carries a source-bound architecture tree, responsibility map, implementation
intent, change impact, assurance ownership, and open conflicts. Missing input
never blocks projection and never authorizes deterministic inference. Every
open conflict must remain visible as a review evidence identity and explicit
human question; deterministic code must not resolve it.

A decision-quality audit runs over every generated PRD/ESP primary section and
every human Action Card. It checks reviewability rather than business truth:
source-grounded named subjects, the current decision, rationale or constraints,
risks/exceptions, evidence obligations, and an explicit question a reviewer can
answer. A non-pass first attempt receives bounded deterministic feedback for one
Agentic repair. A second `fail` is rejected; a second `review-bound` result may
remain publishable only with its quality ceiling retained in
`*.decision-quality.json` and the semantic-projection manifest. Generic
principle-only prose must not be reported as decision-quality `pass`.

P1 business maps and P2 architecture maps are authored by an independent
Agentic review-map lane after the corresponding structured phase sources
exist. Translation does not author, segment, or transport map semantics. The
map lane publishes source-hash-bound rich bundles; deterministic code only
validates their contract and renders them. A missing, stale, or invalid map or
semantic projection must fail closed rather than publish translated machine
control surfaces as a human dossier.

Relevant packaged entrypoints:

- `scripts/common/human_review_sidecar.py`
- `scripts/common/human_review_architecture_reconstruction.py`
- `scripts/common/human_review_decision_model.py`
- `scripts/common/human_review_decision_quality.py`
- `scripts/common/run_human_review_sidecar_worker.py`
- `scripts/common/review_map_generation.py`
- `scripts/common/human_semantic_projection.py`
- `scripts/release/audit_human_review_decision_quality.py`
- `scripts/release/run_reader_translation_lane.py`
- `scripts/release/run_human_review_map_lane.py`
- `scripts/release/run_human_semantic_projection_lane.py`
- `scripts/release/assemble_v16_human_review_dossier.py`
- `scripts/release/render_human_review_dossier.py`

The final offline HTML is `<case-root>/human-review/index.html`. Its PRD, ESP,
Action Cards, appendices, and maps are read-only projections; source Markdown,
Trace and phase outputs remain authoritative.
