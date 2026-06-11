# WFF 全局导航图

这份文档先回答一个问题：WFF 到底由哪些入口、路线和产物层组成。第一次实操时优先从 `using-wff` 开始，它是面向用户的顶层入场判断和路由入口。

WFF 对外只有三个入口：`wff-req-chat`、`wff-req`、`wff-x`。`wff-arch`、`wff-impl`、`wff-validation` 不是外部直达入口，它们只是在 WFF 上游产物已经成立时继续往下走。

如果你第一次看 WFF，或者让 AI Agent 扫描本仓库，先读这里。否则很容易只看到 P1-P4、只看到自动化脚本，或者被几百个生成物淹没。

## 一句话心智模型

WFF 不是一条只能自动跑到底的流水线。

它由四个层次组成：

| 层次 | 作用 | 不要误解成 |
|---|---|---|
| 入口路由 | `using-wff` 先判断当前起点，再推荐 WFF skill/profile | 必须先理解完整方法论 |
| 路线 | 决定项目走新项目主线，还是先走存量系统改造支线 | 只有 P1-P4 一条路 |
| Skills | 承载具体阶段能力和支持能力 | 单个 `SKILL.md` 就是完整安装单位 |
| Install Profiles | 按场景打包一组 skills、脚本、模板、参考包和资源 | 新的方法论或新的生命周期真相 |
| Role Agents | 用产品经理、架构师、程序员、QA、评审员等角色进入 WFF | 新的 LLM runtime 或替代阶段责任 |

真正的控制边界仍然是：路线决定顺序，skills 执行能力，证据限制声明，人工评审处理需要人类判断的结论。

## 路线图

### 新项目主线

当你从想法、材料、PRD 或设计开始，通常走 P1-P4：

```text
想法 / 材料
  -> wff-req-chat
  -> P1 / wff-req
  -> P2 / wff-arch
  -> P3 / wff-impl
  -> P4 / wff-validation
```

这条线不是“机械跑完就算完成”。每一步都要判断当前产物是否足够进入下一步。

### 存量系统改造支线

当你接手的是已有代码库、数据库、接口、线下流程或历史包袱，先不要直接把它当成新项目跑 P1-P4。

```text
旧系统代码 / 数据库 / 接口 / 线下流程
  -> PX / wff-x
  -> 现状基线、风险、安全网、目标变化
  -> 再决定回到 P1、P2、P3 或 P4
```

PX 的重点是先分清事实、推断和未知数。它不是默认的“第五阶段”，也不是马上重写系统。

### Skills 与安装组合

WFF 的使用入口通常不是单个文件，而是一组配套资源：

- `requirements-prd`：需求澄清和 PRD。
- `architecture-design`：架构与工程设计。
- `implementation-delivery`：实现、测试、API 文档和交付收口。
- `validation-closure`：证据验证和声明收口。
- `full-lifecycle`：P1-P4 新项目主线。
- 存量系统改造组合：面向旧系统接手、迁移、重构、扩容的打包组合。
- `role-agent-companion`：可选角色入口导出层。

安装组合只是打包方式。它不改变 P1/P2/P3/P4/PX 的责任边界。

### Role Agents

Role Agents 适合不想先记 skill 名的用户：

| 角色 | 主要入口 |
|---|---|
| WFF Product Manager | `wff-req-chat`、`wff-req` |
| WFF Architect | `wff-arch` |
| WFF Programmer | `wff-impl` |
| WFF QA Tester | `wff-validation` |
| WFF Refactor Architect | `wff-x` |
| WFF Reviewer | 产物评审、可接手性评审、reader review |

Role Agents 只是入口和适配层。它们不能脱离 WFF skills 单独承诺 PRD、架构、代码、验证、生产可用或人工批准。

## 入口选择表

| 你现在的情况 | 先走哪里 | 先看什么结果 |
|---|---|---|
| 不知道 WFF 应不应该介入 | `using-wff` | 是否进入 WFF、推荐入口、下一步和边界 |
| 只有一个想法，还说不清需求 | `wff-req-chat` | P1 输入包、关键问题、事实缺口 |
| 稳定需求材料已经存在，想生成 PRD | `wff-req` | PRD、评分、验收结果 |
| 接手有代码的旧系统、迁移、重构、扩容，或拿到存量代码项目及相关文档 | `wff-x` | 当前事实、推断、未知数、风险、安全网和回到 P1/P2/P3/P4 的建议 |
| 已有 WFF P1 accepted PRD，想继续系统设计 | `wff-arch` 内部续接 | `engineering-spec-pack.md`、`phase-3-implementation-entry.md` |
| 已有 WFF P2 handoff / ESP，想继续实现和测试 | `wff-impl` 内部续接 | 实现任务卡、代码、测试报告、交付检查 |
| 已有 WFF P3 evidence，想继续判断能不能收口 | `wff-validation` 内部续接 | closure summary、validation report、claim ceiling |
| 想按工作角色使用 | `wff-agent` | 平台本地角色文件和角色职责边界 |

如果不确定，先问两个问题：

1. 这是普通小修小改，还是需要 WFF 控制需求、设计、实现、验证边界？
2. 我现在手上的东西是粗想法、稳定需求、已有系统/半截产物，还是 WFF 原生上游产物？

## 人类产物三大类

WFF 实测可能生成很多文件。人第一次看结果时，不应该把所有文件同等对待。

### 1. 核心阅读文档

这是人应该先看的主文档，用来判断能不能进入下一步。

常见例子：

- P1：PRD、评分和验收结果。
- P2：`engineering-spec-pack.md`、`phase-3-implementation-entry.md`。
- P3：实现任务卡、评审包、API 文档、交付检查摘要。
- P4：closure summary、validation report。
- PX：代码基线、数据库基线、业务架构基线、目标架构和安全网计划。
- 如果运行产生 `human-review/` 或类似人类阅读入口，优先从那里读。

### 2. 证据 / 验证文档

这是用来支撑或限制声明的材料。它们回答“这句话凭什么能说”。

常见例子：

- gate 结果、scorecard、traceability validation。
- 测试报告、运行报告、smoke 证据。
- 读者翻译完整性检查、人类 Review 记录。
- 发布 proof snapshot 和保留验证材料。

这类文件很重要，但通常不是第一屏入口。先读核心文档，再用证据文档核对声明。

### 3. 诊断 / 机器辅助 / 审计文档

这是给脚本、维护者、审计或问题定位看的材料。

常见例子：

- JSON sidecar、manifest、timing report、diagnostics。
- 中间 trace、机器可读 registry、低层日志。
- 内部工作单、历史计划、维护者 closeout 记录。

这类文件不代表“用户都要读”。除非你在排错、审计、复盘或维护发布，否则不要从这里开始。

## 看到很多生成物时怎么读

按这个顺序读：

1. 先找 `human-review/`、README、summary、closure 或当前阶段主文档。
2. 再看对应阶段的证据 / 验证文件。
3. 最后才看 diagnostics、JSON sidecar、trace 和内部审计文件。

如果主文档已经暴露关键缺口，不要继续假装进入下一阶段。

## 常见误解

| 误解 | 正确理解 |
|---|---|
| WFF 只有 P1-P4 | WFF 还有 PX，用于存量系统接手、迁移、重构、扩容前的事实扫描和改造边界 |
| WFF 是自动化全链路脚本 | 自动化是执行面；skills、install profiles、Role Agents 和人工评审同样是使用面 |
| 文件越多越完整 | 文件多不等于结论强；先看核心阅读文档，再核验证据 |
| Role Agents 是新方法论 | Role Agents 只是入口适配层，仍要回到 WFF skills、证据和阶段边界 |
| P4 通过等于生产可用 | P4 只说明当前证据支持哪些声明，不等于真实 UAT、生产批准或 owner sign-off |

## 继续阅读

- [最小上手路径](getting-started.zh-CN.md)
- [WFF Role Agents 使用指南](../WFF-ROLE-AGENTS.zh-CN.md)
- [发布与安装指南](../RELEASE.zh-CN.md)
- [WFF 文档导航](../README.zh-CN.md)
