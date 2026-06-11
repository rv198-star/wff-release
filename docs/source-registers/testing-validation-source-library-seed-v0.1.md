# 产品验收（Acceptance / UAT）阶段素材库启动建议（v0.1）

## 文档目的

这份文档用于回答：在正式启动第四阶段（产品验收 / Acceptance / UAT）Stage Skill family 建设前，应该准备哪些 **小而硬** 的验收清单、门禁与证据表达素材。

在当前项目方向下，Phase-4 **不要求 UI 自动化成熟**，也不把“测试执行流程”做成主链。

Phase-4 的目标是产出可审计、可拒绝、可收口的：

- 产品功能级验收用例清单（Acceptance checklist / TEST-* catalog）
- 验收入口/出口门禁（entry/exit gate）
- 验收证据要求（截图/录屏/日志/导出数据等）

并且在当前项目实践中，Phase-4 往往还需要交付：

- **安装部署手册 / 运行手册（operator-facing docs）**
  - 目的：让产品/验收方能在目标环境中把系统跑起来，或确认运行方式与已知限制
  - 注意：这不是“生产级 SRE runbook 全家桶”，而是最小可验收的安装与运行说明

---

## 一、Phase-4 当前最缺的是什么

从本 repo 的治理经验看，验收阶段最容易失败的不是“不会写用例”，而是：

1. **验收主张不可追踪**：REQ/FLOW/UI 到底由哪些验收项覆盖，证据在哪里
2. **验收门禁缺失**：什么时候可以进入验收、什么算通过/不通过不清晰
3. **证据形态不一致**：只有口头确认，没有可审计证据（截图/录屏/日志/导出）

---

## 二、第一批推荐 starter set（优先非书籍、真实模板；书籍/标准作为 backbone）

> 说明：Phase-4 的可执行性主要来自“真实验收清单 + entry/exit gate checklist + 证据纪律”。
>
> 所以推荐分两层：
> - **Tier-0（强推荐，最快落地）**：真实模板/清单/报告样例
> - **Tier-1（backbone）**：标准/书籍/研究，用来补齐结构语言与判断框架

### Tier-0：最快落地的来源（强推荐先收集）

1) **产品验收用例清单模板（来自 2 个不同项目/团队）**
- 目标：提炼“验收主张、预期结果、证据要求、签字/确认位”的结构 spine
- 对应：Acceptance catalog 的 output-template 字段

2) **测试入口/出口检查清单（真实可执行）**
- 目标：直接作为 Phase-4 Stage-03 的 gate artifact
- 对应：entry evidence / exit evidence 字段与阈值

3) **验收执行记录样例（UAT run log / 验收记录）**
- 目标：把“验收过”变成可审计证据（时间、环境、版本、结果、证据路径、执行者）

4) **问题/缺陷记录模板（含复现证据字段）**
- 目标：统一问题证据结构，能挂 trace

5) **验收总结/放行判断样例（go/no-go）**
- 目标：让放行判断可追溯、可解释（含风险接受）

6) **安装部署手册样例（强推荐）**
- 目标：沉淀最小“从零到可运行”的步骤、依赖、配置与常见故障排查
- 对应：Phase-4 的安装部署手册输出模板字段

> 有了 Tier-0，Phase-4 的 output-template 与 gate 结构可以快速落地；Tier-1 用于把这些模板“规范化为可复用的字段类型”。

### 1) Test Strategy / Risk-based Testing（覆盖规划的骨架）

**要吸收的能力：**
- 风险驱动的测试范围选择
- coverage 不等于用例数量；coverage 是“验证主张覆盖”

**将被转译成的 Phase-4 工件：**
- Stage-01 `acceptance-coverage-planning` 的覆盖说明字段
- `TEST-*` 的最小分类与优先级规则

### 2) Test Plan 模板（执行控制文件）（可选：仅在你们需要独立 QA 执行时启用）

**要吸收的能力：**
- 环境/工具/范围/完成标准/任务列表/流程 的结构化 spine
- completion criteria 必须是字段类型，不是公司特定阈值

**将被转译成的 Phase-4 工件：**
- `Test Plan` output template
- `Test Execution Record` 的结构字段

**推荐代表（候选）：**
- IEEE 829-2008（测试文档标准：可作为“证据类型/报告 spine”参考，但不强制按其全套文档落地）

### 3) Test Entry/Exit Gate（收口与放行判断）

**要吸收的能力：**
- entry evidence 与 exit evidence 必须显式可检查
- sign-off、重复测试条件、遗留风险接受

**将被转译成的 Phase-4 工件：**
- Stage-03 `validation-closure-and-delivery-readiness-judgment` 的 gate checklist
- 缺陷/风险接受说明模板

**推荐代表（候选）：**
- 本 repo 已抽取的 `card-test-entry-exit-gate`（结构强，gate evidence PASS）
- release readiness / go-no-go checklists（只吸收“证据字段”，避免 checklist theater）

### 4) Issue/Defect taxonomy / Evidence discipline（问题识别与证据化）

**要吸收的能力：**
- 缺陷分类、严重性、复现证据、影响面
- 与 traceability 对齐（关联 `REQ-* / MOD-* / TEST-*`）

**将被转译成的 Phase-4 工件：**
- `defect record template`
- `test report template`（包含证据路径）

**推荐代表（候选）：**
- Orthogonal Defect Classification（ODC, IBM）：用于问题分类与过程有效性信号（可选）

---

## 二点五、starter set → Phase-4 工件映射（摘要）

| source | 主要吸收点 | 对应 Phase-4 工件 |
|---|---|---|
| IEEE 829 | test plan / log / incident / summary 的文档 spine | Test Plan 模板；Execution Log；Test Summary |
| Kaner/Bach/Pettichord（Lessons Learned） | 策略与停止条件启发式 | coverage planning 的“策略字段”；closure judgment 的 reasoning 字段 |
| ODC (IBM) | defect taxonomy + trigger/containment 信号 | 缺陷记录分类字段；exit gate 的“缺陷分布信号” |
| release readiness / go-no-go | 收口判断的证据结构 | test closure checklist；risk acceptance note |
| risk-based testing | risk=likelihood×impact；按风险分层 exit criteria | coverage prioritization；risk-tiered exit gate |

---

## 三、推荐同时准备的“非书籍素材”（强推荐）

Phase-4 最有效的素材往往是“真实模板 + 真实 gate checklist”。

建议准备：

1. **测试计划模板（2 套来自不同项目的结构骨架）**
2. **测试入口/出口检查清单（可直接转为 gate artifact）**
3. **缺陷记录模板（带证据字段）**
4. **测试结论/收口建议模板（带风险接受字段）**

---

## 六、启动前“素材包清单”（建议先在仓库之外收集，再进 source-register）

在正式启动 Phase-4 authoring 前，建议至少收集到这些具体对象（真实样例优先）：

- 2 份产品验收用例清单模板（不同团队/项目）
- 1 份验收入口/出口 gate checklist
- 1 份问题/缺陷记录模板（含复现步骤/证据/影响面/关联模块字段）
- 1 份验收执行记录样例（UAT run log）
- 1 份验收总结/放行判断样例（go/no-go + 风险接受）

- 1 份安装部署手册样例（从零到运行 + 配置说明 + 常见问题）

有了这些，Phase-4 就能快速落成“产品验收 checklist + 放行 gate”，而不是停留在“测试理论”或押注 UI 自动化。

并且能补齐“验收可运行性”这一类经常被忽略的交付要素：安装部署手册。

---

## 四、当前不建议一开始重投入的方向

1. 把 ISTQB/术语大全当主骨架
   - 术语可做 sidecar，但主链要服务 gate/evidence。
2. 以工具（某测试平台/某云服务）文档当核心素材
   - 工具文档适合 lane optional；核心应是可迁移的 gate 与证据结构。

---

## 五、下一步落库动作（建议）

1. 建立 `testing-validation-source-index`（最小索引表）
2. 用 `source-unit-coverage-ledger` 给 starter set 建立 coverage ledger
3. 将源映射到 Phase-4 三个子阶段的 output-template 字段与 gate 条款
4. 再按真实 authoring 缺口定向补齐

---

## 一句话结论

Phase-4 的 starter 素材库要优先覆盖：

- risk-based test strategy（覆盖规划）
- test plan spine（执行控制）
- test entry/exit gate（收口判断）
- defect/evidence discipline（证据化与可追踪）
