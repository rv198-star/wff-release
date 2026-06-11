# Phase-2 Session Bootstrap

## 1. Purpose

This file is the live bootstrap and progress handoff for:

- 第二阶段：技术方案设计
- Phase-2: design / architecture

Use it in every new session before Phase-2 work starts.

Update it at the end of every Phase-2 working session so the next session can continue without re-discovery.

---

## 2. Current Phase Status

- current_phase:
  - `Phase-2 / 技术方案设计`
- current_state:
  - `phase-2-official-execution-hardening`
- repo_root:
  - `/Users/william/Github/software-lifecycle-skills`
- current_owner_mode:
  - `use the official Phase-2 execution skill and treat scripts/phase2/run_phase2_first_version.py --run-wrapper as the canonical Phase-2 mainline bundle; drop to scripts/phase2/run_phase2_full_trial.py only for manual/remediation closure over already-authored Stage outputs`
- default_output_root:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-2/`

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

### 3.1 Default Phase-1 baseline for Phase-2

Use this as the default architecture-entry baseline:

- Phase-1 PRD main:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/geo-rpd-main-document.md`
- Phase-1 PRD zh-CN:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/geo-rpd-main-document.zh-CN.md`
- Phase-1 prototype spec:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/prototype-spec.md`
- Phase-1 execution report:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/phase-1-execution-report.md`

### 3.2 Supplemental validation reference

Do not use this as the default design baseline.
Use it only when Phase-2 needs to inspect `02b-skip` handling semantics:

- `02b-skip` execution report:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/phase-1-execution-report.md`
- `02b-skip` PRD:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/geo-rpd-main-document.md`
- `02b-skip` prototype spec:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/prototype-spec.md`

### 3.3 Original read-only source input

- source input:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-inputs/phase1/GEO生成式引擎优化产品需求描述_实用版-v1.1-Phase1补齐版.md`

---

## 4. Phase-2 Package Entry

### 4.1 Official execution skill

- Phase-2 official skill:
  - `/Users/william/Github/software-lifecycle-skills/skills/wff-arch/SKILL.md`

### 4.2 Family README

- Phase-2 package README:
  - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/README.md`

### 4.3 Execution / governance references

- Phase-2 first-pass generation workflow:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md`
- Phase-2 execution report template:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-2/phase-2-execution-report-template.md`
- Stage-2 traceability baseline:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-2/stage-2-traceability-baseline-v0.1.md`
- Stage-2 runtime hardening targets:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-2/stage-2-runtime-hardening-targets-v0.1.md`
- Phase-2 case-backed validation matrix:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-2/phase-2-case-backed-validation-matrix-v0.1.md`
- Stage-2 case-backed absorption matrix:
  - `/Users/william/Github/software-lifecycle-skills/docs/phases/phase-2/design-architecture-case-backed-absorption-matrix-v0.1.md`

### 4.4 Current four substages

1. `architecture-definition-and-boundary-setting`
   - path:
     - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/stage-01-architecture-definition-and-boundary-setting`
   - purpose:
     - freeze architecture entry boundary, constraints, capability map, and architecture direction
2. `domain-module-service-decomposition`
   - path:
     - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/stage-02-domain-module-service-decomposition`
   - purpose:
     - turn architecture direction into domain / module / service structure, public-boundary slices, conceptual ER, and domain-event handoff
3. `data-storage-and-interface-design`
   - path:
     - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/stage-03-data-storage-and-interface-design`
   - purpose:
     - define data ownership, storage, interface contracts, interaction boundaries, scenario coverage, and evidence-backed technology decisions
4. `design-convergence-and-delivery-prototype`
   - path:
     - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/stage-04-design-convergence-and-delivery-prototype`
   - purpose:
     - converge Stage-01~03 outputs into an implementation-facing handoff package with critical public-boundary sequences and explicit optimality review

### 4.5 Most important Stage-2 references

- Stage-01 charter:
  - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/stage-01-architecture-definition-and-boundary-setting/stage-charter.md`
- Stage-04 charter:
  - `/Users/william/Github/software-lifecycle-skills/reference-packages/phase2-design-architecture/stage-04-design-convergence-and-delivery-prototype/stage-charter.md`

---

## 5. Working Rules For New Sessions

- Always inspect the existing Phase-2 package before proposing any new structure.
- Always open the official Phase-2 execution skill before treating a run as the canonical family entry.
- Always read the Phase-1 PRD's `Phase-2 Design Input Contract` before drafting Stage-01 and treat it as the top-down absorption baseline.
- Every new Phase-2 version must start by scaffolding a fresh case root with `scripts/phase2/scaffold_phase2_case.py`.
- If the target is a pure baseline generated directly from the Phase-1 PRD main document, scaffold with `scripts/phase2/scaffold_phase2_case.py --pure-prd-direct` and treat any later fixes as a new rerun/follow-up version rather than patching the baseline.
- For the default official mainline, use `scripts/phase2/run_phase2_first_version.py --run-wrapper`.
- Use `scripts/phase2/run_phase2_full_trial.py` directly only after Stage-01..04 outputs are present and the task is explicit manual/remediation closure.
- Use the existing stage `skill-contract.md`, `stage-sop.md`, `output-template.md`, and `source-cards.md`.
- Do not re-run or rewrite Phase-1 unless the task explicitly requires it.
- Treat Phase-1 v4 as the default architecture-entry baseline.
- Treat Phase-1 v5 `02b-skip` run as a validation case, not the primary design baseline.
- Initialize / bind / validate the Phase-2 coarse trace chain through `wff-base-traceability-management` for official runs.
- Preserve explicit fine-grained ids such as `P2-DTR-*`, `P2-CTR-*`, `P2-RP-*`, and `P2-RT-*`; do not downgrade them into ad hoc local labels.
- Produce or update the Phase-2 execution report for official runs.
- Preserve review-bound / provisional / declaration-state semantics.
- Do not silently convert partial NFR input into fake certainty.
- Freeze only public-boundary-visible names, contracts, and interactions unless an explicit exception is stated.
- Stage-01 must already emit a lightweight security architecture sketch and capacity estimation; do not defer both entirely to Stage-03.
- Stage-01 must emit a first-pass dependency realizability scan, substitute-boundary candidates, and explicit downstream `may-assume / must-not-assume` rules.
- Keep all known business scenarios covered; draw detailed sequences only for critical public-boundary scenarios.
- Stage-03 must explicitly test critical external dependency realizability and define substitute-boundary handling before Stage-04 convergence.
- Stage-03 must close tradeoff-heavy reasoning as a bundle when active: technology matrix, alternative candidates, baseline insufficiency, optimum candidate, and key tradeoff decisions should travel together or carry an explicit omission reason.
- Stage-03 scenarios should stay GWT-compatible on the paths where preconditions materially affect implementation or replay: use explicit `given/when/then` columns or keep GWT wording inside `acceptance_criteria`.
- Stage-04 may emit only coarse-grained implementation task sketching at slice/module/work-package level; do not freeze class/method/file/ticket detail there.
- Stage-04 should carry day-1 implementation realism, including auth/vendor/token lifecycle posture, FTE-based work-package sizing, and a glossary/onboarding summary for the next team.
- Runner-level complexity choice should default to classifier-driven `auto`: derive `suggested_profile` from the Phase-1 PRD, accept manual override only with explicit justification, and keep the selected profile visible in the execution report.
- When technology selection depends on current facts such as versions, LTS/support windows, licenses, security notices, or benchmarks, require external evidence instead of memory-only claims.
- When dominant constraints are strong, compare materially different candidates and explain why a mainstream baseline is insufficient before selecting the stronger option.
- Put generated Phase-2 run artifacts under:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-2/`
- Do not create a new Phase-2 version by copying an older Phase-2 case forward and treating it as the primary authored baseline.

---

## 6. Copy-Paste Bootstrap Prompt For New Sessions

```text
我们现在开始第二阶段：技术方案设计（Phase-2 design / architecture）。

项目仓库：
/Users/william/Github/software-lifecycle-skills

先不要凭感觉输出，也不要重新做 Phase-1。先检查仓库里现有的 Phase-2 stage package，并严格基于现有 Skills / SOP / output-template 推进。

这次把 Phase-2 当作官方 family run，而不是只手工填四个模板。先打开：
- skills/wff-arch/SKILL.md
- docs/phases/phase-2/phase-2-session-bootstrap.md
- docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md
- reference-packages/phase2-design-architecture/README.md
- docs/phases/phase-2/phase-2-execution-report-template.md

默认官方主线 bundle 是：
- scripts/phase2/run_phase2_first_version.py --run-wrapper

若这是一个新的 Phase-2 版本，但你刻意走手动/补救式 authoring，先用：
- scripts/phase2/scaffold_phase2_case.py

若四个 Stage 输出已经存在，且当前是手动/补救闭口，closure wrapper 是：
- scripts/phase2/run_phase2_full_trial.py

本轮默认权威输入：
- Phase-1 PRD main:
  /Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/geo-rpd-main-document.md
- Phase-1 prototype spec:
  /Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/prototype-spec.md
- Phase-1 execution report:
  /Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/phase-1-execution-report.md
- 原始只读输入：
  /Users/william/Github/software-lifecycle-skills/tmp/local-inputs/phase1/GEO生成式引擎优化产品需求描述_实用版-v1.1-Phase1补齐版.md

补充说明：
- v5 的 02b-skip run 只用于参考 Admission Matrix skip handling，不作为默认架构基线：
  /Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-stage02b-skip/phase-1/phase-1-execution-report.md

先做这几件事：
1. 阅读 skills/wff-arch/SKILL.md
2. 阅读 docs/phases/phase-2/phase-2-session-bootstrap.md
3. 阅读 docs/phases/phase-2/phase-2-first-pass-generation-workflow-v1.0.md
4. 阅读 reference-packages/phase2-design-architecture/README.md
5. 从 Phase-1 PRD 中抽取 `Phase-2 Design Input Contract`，先列出 top-down absorption plan
6. 识别这轮应从 Phase-2 哪个 stage 开始
7. 给出本轮计划，然后直接开始落地

要求：
- 必须基于现有 Phase-2 stage package 输出
- 若是新版本，必须先 scaffold fresh Phase-2 case root，再产出 Stage-01..04
- 官方 run 必须补齐 traceability registry init / bind / validate / report 与 Phase-2 execution report
- 所有用于吸收 Phase-1 trace units 的 scenario / replay / RBI / decision / contract 行都必须显式填写并保留 `upstream_trace_ids`
- 官方主线应优先通过 scripts/phase2/run_phase2_first_version.py --run-wrapper 完成 fresh generation + closure；仅在手动/补救闭口时直接运行 scripts/phase2/run_phase2_full_trial.py
- 必须保留 review-bound / provisional / declaration-state 语义
- Stage-01 必须补出 security architecture sketch 与 capacity estimation
- Stage-01 必须补出 dependency realizability scan、substitute-boundary 候选、以及 downstream may-assume / must-not-assume 契约
- 只冻结 public boundary 可见的名字、契约和交互；不要在这个阶段强行冻结内部实现类/方法
- 所有已知业务场景都必须进入 coverage；只有关键 public-boundary 场景需要详细时序
- Stage-03 必须对关键外部依赖给出 realizability / substitute-boundary 判断
- Stage-03 若进入多候选技术/架构权衡，必须成套收口：technology matrix、alternative candidates、baseline insufficiency、optimum candidate、key tradeoff decisions 要一起出现，或显式写明为何不适用
- Stage-04 若输出 implementation task sketch，只能到 slice / module / work-package 粒度
- complexity-profile 默认应走 classifier 驱动的 `auto`：从 Phase-1 PRD 生成 `suggested_profile`，人工 override 必须附 justification，并在 execution report 中保留 suggested/selected 差异
- 技术选型若依赖当前事实，必须外部核实并保留证据引用
- 若存在强主导约束，不得停在主流可行基线；必须比较更强候选并说明主流基线为何不足
- 输出目录：
  /Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/<case-name>/phase-2/
```

---

## 7. Current Progress Snapshot

- Phase-1 mainline GEO run exists and is stable at:
  - `geo-generative-engine-optimization-mainline/phase-1`
- Phase-1 Stage-05 prototype bridging exists and is usable.
- Official `02b-skip` Phase-1 full trial has already been validated at:
  - `geo-generative-engine-optimization-stage02b-skip/phase-1`
- Phase-2 package family already exists in authored first-pass form.
- official Phase-2 execution entry now exists at:
  - `/Users/william/Github/software-lifecycle-skills/skills/wff-arch/SKILL.md`
- official Phase-2 compatibility/manual closure wrapper now exists at:
  - `/Users/william/Github/software-lifecycle-skills/scripts/phase2/run_phase2_full_trial.py`
- Canonical repo-local case-first GEO artifact root now exists at:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/`
- Stage-01 draft exists at:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-01-architecture-definition-and-boundary-setting.md`
- Stage-01 current frozen judgments:
  - architecture must explicitly respond to `reliability / usability / security-data-control / maintainability`
  - current MVP boundary is the tenant-scoped GEO workflow loop, not automation execution or advanced attribution
  - current architecture direction is `boundary-first modular monolith with explicit seams`
- Stage-02 draft exists at:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-02-domain-module-service-decomposition.md`
- Stage-02 current frozen judgments:
  - business decomposition follows the four domains `SG -> OS -> RT -> RR`
  - physical implementation remains a modular monolith with four business modules plus thin support modules
  - service candidates are logical/module-internal first, not an implicit microservice decision
- Stage-03 draft exists at:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-03-data-storage-and-interface-design.md`
- Stage-03 current frozen judgments:
  - business truth stays in module-owned aggregates; other modules consume snapshots/contracts only
  - storage direction is `primary transactional store + evidence artifact store + audit/trace store + durable job state + rebuildable projections`
  - interfaces are contract-first and version-aware, but not yet transport-final
- Stage-04 draft exists at:
  - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-04-design-convergence-and-delivery-prototype.md`
- Stage-04 current frozen judgments:
  - `AttributionSeamEnvelope` is `deferred-only, not-for-implementation`
  - `AuditTrailService` in shared-kernel is a shared abstraction/facade, not a business owner
  - `ReviewDecisionSnapshot -> SG` is read-only/reference-only, not a state writeback path
  - implementation handoff is now assembled around Slice-A~D with explicit review-bound consumption rules
- Package refinement judgments:
  - Stage-01 requires security architecture sketch and capacity estimation at architecture-entry level
  - Stage-01 requires dependency realizability scan, substitute-boundary candidates, and downstream assumption contract at architecture-entry level
  - Stage-03 requires scenario coverage matrix, evidence-backed technology selection, dominant bottleneck hypothesis, alternative set, baseline insufficiency note, and constraint-dominant optimum candidate
  - Stage-03 requires critical external dependency realizability and substitute-boundary handling before convergence
  - Stage-04 requires critical interaction sequence set, explicit optimality review, and coarse-grained implementation task sketch, while preserving public-boundary-only freeze discipline
  - official runs require traceability init/bind/register/validate/report plus a Phase-2 execution report

---

## 8. Recommended First Action For Phase-2

Continue from the canonical case-first GEO artifact root:

- `use tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-1/ as the default Phase-1 baseline`
- `use tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/ as the canonical Phase-2 package output root`
- `enter through skills/wff-arch/SKILL.md for official family runs`
- `use scripts/phase2/run_phase2_first_version.py --run-wrapper as the canonical Phase-2 mainline bundle`
- `use scripts/phase2/run_phase2_full_trial.py only when Stage-01..04 are already authored and the task is explicit manual/remediation closure`

Reason:

- Phase-1 and Phase-2 now share one repo-local parent directory by case.
- `tmp/local-artifacts/` is already git-ignored, so the layout is repo-local but not commit-tracked.
- New sessions should write only to the case-first layout under `tmp/local-artifacts/<case-name>/phase-1/` and `tmp/local-artifacts/<case-name>/phase-2/`.

---

## 9. Current Open Questions

- Will Phase-2 consume the HTML-oriented prototype-spec only as reference, or as a formal side input during Stage-01 / Stage-04?
- Do we want one canonical Phase-2 GEO run first, then a second run with a different domain as generalization test?
- Which second fully preserved local real case should be added next to deepen the case-backed validation matrix?
- Do we want Phase-2 traceability to stop at coarse stage artifacts, or start piloting finer sub-artifact registration in Stage-03 / Stage-04?
- Do we want to split implementation task sketch into multiple lanes or keep a single coarse work-package lane by default?

---

## 10. Session Log

### 2026-03-28

- status:
  - created the persistent Phase-2 bootstrap file
- confirmed_inputs:
  - Phase-1 v4 full run is the default baseline
  - Phase-1 v5 skip run is supplemental validation only
- confirmed_phase2_family:
  - 4-stage design / architecture package exists under `reference-packages/phase2-design-architecture/`
- ready_next_step:
  - begin GEO Phase-2 Stage-01 using the existing Phase-2 package
- session_update:
  - worked_stage:
    - `Stage-01 / architecture-definition-and-boundary-setting`
  - artifacts_produced:
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-01-architecture-definition-and-boundary-setting.md`
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/phase-2-execution-report.md`
  - decisions_frozen:
    - current boundary is the tenant-scoped GEO loop around `scope -> observation -> finding -> recommendation -> task -> review`
    - architecture must explicitly absorb `reliability / usability / security-data-control / maintainability`
    - current direction is `boundary-first modular monolith with explicit seams`
  - remaining_open:
    - retention / permission / audit contract detail
    - connector and task sink realism
    - trend stability threshold
    - B2B-first generalizability outside the current slice
  - exact_next_action:
    - start Stage-02 domain/module/service decomposition from the four subsystem boundaries and typed recommendation/task contract
- session_update_stage_02:
  - worked_stage:
    - `Stage-02 / domain-module-service-decomposition`
  - artifacts_produced:
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-02-domain-module-service-decomposition.md`
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/phase-2-execution-report.md`
  - decisions_frozen:
    - domain split is `Scope & Governance`, `Observation & Scoring`, `Recommendation & Tasking`, `Review & Reporting`
    - dependency direction is one-way and acyclic from `SG` toward `RR`
    - current physical direction is a modular monolith with `shared-kernel` and `integration-adapters` as non-owning support modules
  - remaining_open:
    - retention / permission / audit contract detail
    - connector and task sink realism
    - `Content Asset` boundary width
    - `Competitor Snapshot` boundary width
  - exact_next_action:
    - start Stage-03 data/storage/interface design from the ownership matrix, logical service candidates, and dependency map

### 2026-03-29

- session_update_stage_03:
  - worked_stage:
    - `Stage-03 / data-storage-and-interface-design`
  - artifacts_produced:
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-03-data-storage-and-interface-design.md`
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/phase-2-execution-report.md`
  - decisions_frozen:
    - only owner modules mutate business aggregates; cross-module consumers use contracts/snapshots only
    - first-wave storage direction is layered rather than all-in-one-table or early polyglot-per-service
    - Stage-03 contracts are logical/versioned contracts with failure semantics, not final transport APIs
  - remaining_open:
    - retention / deletion / audit immutability policy detail
    - connector and task sink protocol reality
    - observation evidence volume profile
    - long-term analytical projection depth
  - exact_next_action:
    - start Stage-04 convergence and delivery prototype handoff from the current Stage-01~03 package
- session_update_stage_04:
  - worked_stage:
    - `Stage-04 / design-convergence-and-delivery-prototype`
  - artifacts_produced:
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/stage-04-design-convergence-and-delivery-prototype.md`
    - `/Users/william/Github/software-lifecycle-skills/tmp/local-artifacts/geo-generative-engine-optimization-mainline/phase-2/phase-2-execution-report.md`
  - decisions_frozen:
    - `AttributionSeamEnvelope` lifecycle is `deferred-only, not-for-implementation`
    - `AuditTrailService` is a shared abstraction/facade and audit persistence is not business ownership
    - `ReviewDecisionSnapshot -> SG` is read-only/reference-only
    - Stage-03 step_2 timing is same-cycle after prioritized findings are persisted, not next-cycle
  - remaining_open:
    - retention / deletion / audit immutability policy detail
    - connector and task sink protocol reality
    - evidence volume profile
    - long-term analytical projection depth
  - exact_next_action:
    - audit the Phase-2 convergence package and decide whether to start implementation-phase intake

---

## 11. End-Of-Session Update Checklist

At the end of every Phase-2 session, update:

- `Current Phase Status`
- `Authority Inputs` if the baseline changes
- `Current Progress Snapshot`
- `Current Open Questions`
- `Session Log`

Minimum session-log fields to add each time:

- date
- what stage was worked on
- what files/artifacts were produced
- what decisions were frozen
- what remains blocked / open
- exact next action for the next session
