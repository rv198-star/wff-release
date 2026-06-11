# Phase-1 Session Bootstrap

## 1. Purpose

This file is the live bootstrap and progress handoff for:

- 第一阶段：产品 / 需求
- Phase-1: product / requirements

Use it in every new session before official Phase-1 work starts.

Update it at the end of every Phase-1 working session so the next session can continue without re-discovery.

---

## 2. Current Phase Status

- current_phase:
  - `Phase-1 / 产品与需求`
- current_state:
  - `phase-1-official-execution-entry-aligned`
- repo_root:
  - `/Users/william/Github/software-lifecycle-skills`
- current_owner_mode:
  - `use the official Phase-1 execution skill plus full-trial runner; do not hand-fill Stage templates as final delivery`
- default_output_root:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-1/`

### 2.1 Preferred Local Artifact Layout

- preferred_layout:
  - case-first, repo-local, git-ignored
- canonical_pattern:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-1/`
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-2/`
- git_tracking_rule:
  - everything under `tmp/local-artifacts/` remains local-only and is ignored by git

---

## 3. Authority Inputs

### 3.1 Default read-only source input

- source input:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-inputs/phase1/GEO生成式引擎优化产品需求描述_实用版-v1.1-Phase1补齐版.md`

### 3.2 Current canonical local output reference

Use this as the default Phase-1 example output baseline:

- PRD main:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/geo-rpd-main-document.md`
- PRD zh-CN:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/geo-rpd-main-document.zh-CN.md`
- prototype spec:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/prototype-spec.md`
- execution report:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/phase-1-execution-report.md`

### 3.3 Supplemental validation reference

Do not use this as the default baseline.
Use it only when Phase-1 needs to inspect `02b-skip` handling semantics:

- `02b-skip` execution report:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/phase-1-execution-report.md`
- `02b-skip` PRD:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/geo-rpd-main-document.md`

---

## 4. Phase-1 Package Entry

### 4.1 Official execution skill

- Phase-1 official skill:
  - `/Users/william/Github/software-lifecycle-skills/skills/wff-req/SKILL.md`

### 4.2 Family README

- Phase-1 package README:
  - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase1-product-requirements/README.md`

### 4.3 Execution / governance references

- Phase-1 convergence driver:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-1/phase-1-convergence-driver-v0.1.md`
- Phase-1 execution report template:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-1/phase-1-execution-report-template-v0.1.md`
- Phase-1 PRD main document template:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-1/phase-1-prd-main-document-template-v0.1.md`
- Phase-1 core deliverables checklist:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-1/phase-1-core-business-deliverables-checklist-v0.1.md`

### 4.4 Current official runtime chain

1. `Stage-01 requirements-user-research`
2. `Stage-02a requirements-structural-analysis`
3. `Stage-02b requirements-specification-deepening`
4. `Stage-03 mvp-scope-and-slicing`
5. `Stage-04 validation-and-recommendation`

Optional side branch:

- `Stage-05 prototype-spec-bridging`
  - outside the default full-trial path unless explicitly requested

---

## 5. Working Rules For New Sessions

- Always open the official Phase-1 execution skill before treating a run as canonical.
- Official runs must go through `scripts/phase1/run_phase1_full_trial.py`.
- Use `scripts/phase1/run_phase1_convergence.py` directly only for recheck/remediation of an existing artifact set.
- Do not hand-fill Stage templates as the final official Phase-1 delivery.
- Keep the source document read-only.
- Preserve unresolved truth, blocked outputs, and review-bound carryover honestly; they can still be valid outputs.
- Put generated Phase-1 run artifacts under:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-1/`
- Stage-05 remains optional and does not enter the default full trial unless explicitly requested.
- If rerunning an existing case, also apply:
  - `skills/wff-meta-stage-skill-construction-lifecycle/SKILL.md`
  - baseline lock / regression gate / vs-baseline delta reporting

---

## 6. Copy-Paste Bootstrap Prompt For New Sessions

```text
我们现在开始第一阶段：产品 / 需求（Phase-1 product / requirements）。

项目仓库：
/Users/william/Github/software-lifecycle-skills

先不要手工逐 Stage 填模板，也不要脱离仓库现有 runtime 乱写 PRD。先把这次运行当作官方 full-trial run。

先打开：
- skills/wff-req/SKILL.md
- docs/phases/phase-1/phase-1-session-bootstrap.md
- reference-packages/phase1-product-requirements/README.md
- docs/phases/phase-1/phase-1-execution-report-template-v0.1.md

默认只读输入：
- /Users/william/Github/software-lifecycle-skills/tmp/local-inputs/phase1/GEO生成式引擎优化产品需求描述_实用版-v1.1-Phase1补齐版.md

先做这几件事：
1. 阅读 skills/wff-req/SKILL.md
2. 阅读 docs/phases/phase-1/phase-1-session-bootstrap.md
3. 阅读 reference-packages/phase1-product-requirements/README.md
4. 确认这次 full-trial 的 output root 和 profile
5. 给出本轮计划，然后直接开始落地

要求：
- 官方 run 必须通过 scripts/phase1/run_phase1_full_trial.py 或与其等价的完整链路
- 必须保留 Stage outputs、assembled PRD、converged PRD、evidence memo、execution report 与 gates
- 不得把手工逐 Stage 文档直接当成官方最终交付
- 必须诚实保留 unresolved truth / review-bound / blocked 信息
- 输出目录：
  /Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-1/
```

---

## 7. Current Progress Snapshot

- official `wff-req` entry exists
- official full-trial runner exists at:
  - `/Users/william/Github/software-lifecycle-skills/scripts/phase1/run_phase1_full_trial.py`
- canonical repo-local Phase-1 output root exists at:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/`
- current canonical output set includes:
  - PRD main document
  - zh-CN PRD audit mirror
  - execution report
  - prototype spec bridge artifact
- official `02b-skip` validation reference exists under:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/`
- Stage-05 prototype bridge exists, but remains outside the default full-trial path

---

## 8. Recommended First Action For Phase-1

- `use tmp/local-inputs/phase1/... as the default read-only source`
- `use tmp/local-artifacts/<case-name>/phase-1/ as the canonical Phase-1 output root`
- `enter through skills/wff-req/SKILL.md for official runs`

Reason:

- this keeps Phase-1 aligned with the case-first local artifact layout already used by Phase-2
- it preserves the existing runner as the real execution backbone
- it gives new sessions one stable human/agent bootstrap surface instead of scattered references

---

## 9. Current Open Questions

- Should Phase-1 adopt a registry-backed traceability pilot for official runs, or keep traceability at naming-block level for now?
- Should Stage-05 be enabled by profile in the full-trial runner, or remain a manual post-Phase-1 branch?
- Which second preserved local real Phase-1 case should be added next so the entry model is not dominated by GEO alone?

---

## 10. Session Log

### 2026-03-29

- status:
  - created the persistent Phase-1 bootstrap file
- aligned_entry_model:
  - Phase-1 now has an explicit skill + bootstrap + README entry surface, matching the Phase-2 entry model
- ready_next_step:
  - use the official skill plus full-trial runner for the next canonical Phase-1 run
