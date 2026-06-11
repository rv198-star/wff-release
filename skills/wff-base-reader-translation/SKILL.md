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
- File names and paths (e.g., `scripts/phase1/run_phase1_full_trial.py`, `engineering-spec-pack.md`)
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
- Common lifecycle terms: workflow-first→工作流优先, review-bound→受评审约束, downstream-start-safe→可安全启动下游, tracked scope→跟踪范围, finding(s)→发现项, recommendation→建议, task→任务

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

The Python script handles file paths, LLM invocation, segmentation, and integrity verification. This skill is the release-facing contract for what the Agentic translation must preserve, translate, and self-review.

## Artifact Acceptance

Use `scripts/release/reader_translation_artifact_acceptance.py` to validate generated reader artifacts after the lane runs. The acceptance check is read-only: it verifies `reader-translation-manifest.json`, generated reader files, integrity JSON files, reader preambles, recomputed immutable-token integrity, and basic structure preservation. This acceptance evidence remains separate from P1-P4 lifecycle gates; missing or failed reader artifacts cap reader-evidence claims instead of blocking canonical lifecycle truth.
