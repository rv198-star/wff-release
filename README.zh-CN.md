# Waterfall Flow Framework（WFF）

> Vibe Coding 给速度，SPEC 给意图，Harness 给运行证据；WFF 给复杂应用所需的可维护交付闭环。

WFF 是给 AI Agent 用的软件生命周期框架。它解决的不是“怎么让 AI 更猛”，而是“怎么避免把 AI 用错”。

复杂应用不是一次超长 prompt 就能稳定完成的事。需求会变，模块会互相影响，设计会取舍，代码要扩展，测试要补强，最后还要有人接手和判断能不能交付。人和 AI 都不可能跳过设计与拆解，还长期准确记住每个需求、接口、边界和风险。

WFF 的做法很朴素：**把复杂问题拆小，把每一步留下证据，把每个产物接回原始需求和设计来源。**

## WFF 是什么

WFF 把复杂软件工作拆成一串小而清楚的任务。每一步都要说明：

- 输入来自哪里；
- 要产出什么；
- 产出对应哪条原始需求、设计材料或约束；
- 哪些测试、Harness 结果、Review 或 gate 能支撑它；
- 还有哪些结论现在不能说。

AI Agent 因而不必一次性理解整个系统，可以专注完成边界清楚的模块，再把结果接回完整证据链。复杂应用能持续长大，靠的不是硬扛更长上下文，而是让软件工程把上下文切小、切清楚、切得可追踪。

## 和你已经熟悉的东西有什么不同

- **Vibe Coding 很快，但复杂应用会失控。** 它适合探索和快速看到结果；项目变大后，需求边界和模块职责容易漂移，demo 有了，产品却难以维护。
- **SPEC 能把意图写清楚，但不能自动保证实现不跑偏。** 文档有依据，不等于代码、测试和交付声明会始终跟随它。
- **Harness 能提供运行证据，但运行通过不等于交付结论成立。** 还要回答行为对应哪条需求、覆盖了什么风险、遗漏了什么边界，以及现在能声明到什么程度。

WFF 用软件工程的方法拆解问题，让需求、设计、模块、代码、测试和证据一环扣一环，而不是继续把所有负担压给 AI 的记忆和注意力。

## WFF 的特点

- **每一步都有迹可循**：产物能回到原始需求、设计、约束或证据来源。
- **每个模块都能独立委派**：AI Agent 专注一个小边界，不在超长上下文里猜全局。
- **上下文失控被结构性避开**：通过拆解和交接减少遗忘、漂移和补丁冲突。
- **测试和 Harness 会回到交付语义**：不只问“跑没跑”，还问“证明了什么、没证明什么”。
- **声明有上限**：证据只够证明多少，结论就只能说到多少。

> WFF 不替 AI 吹牛。WFF 让 AI 交证据。

## 什么时候该用 WFF

第一次使用先从 `using-wff` 开始，让它根据现有材料判断入口。WFF 对外只有三个入口：`wff-req-chat`、`wff-req`、`wff-x`；`wff-arch`、`wff-impl`、`wff-validation` 不是外部直达入口，只能在已有 WFF 上游产物成立后续接。

### 只有想法、聊天记录或零散材料

`wff-req-chat` 是 P1 前的引导入口，负责整理需求来源、关键缺口、约束和待确认问题，不直接写代码，也不假装已有完整规格。建议路线：`using-wff -> wff-req-chat / wff-req`。

### 已有需求、规格、设计稿或接口材料

把已有材料变成可继续设计、实现、测试和追踪的工程输入，拆成后续 Agent 可以独立处理的小块。建议路线：`using-wff -> wff-req`。只有已有可接受的 WFF-native upstream artifacts 时，才可内部续接 `wff-arch`、`wff-impl`。

### 已有代码系统、历史包袱或迁移改造任务

先看真实代码、数据、接口和风险，分清事实、推断和未知数，再决定后续路线。`wff-x` 是 code-backed existing-system assessment；Related documents are supporting evidence；standalone documents are not enough。建议路线：`using-wff -> wff-x`。

## 你会看到什么

WFF 可能产生很多文件，用户不需要从机器日志开始读。优先看：

- 面向人的主读文档：需求、设计、实现任务、验证和收口摘要；
- 证据材料：测试报告、Harness 结果、gate 报告、AI Review、proof snapshot；
- 追踪关系：需求、设计、模块、代码、测试和证据之间的连接；
- 声明上限：哪些结论成立，哪些仍需真实环境、外部评审或业务负责人确认。

如果输出目录里有 `human-review/INDEX.md`，先看它。这个历史兼容路径当前是 AI / external review 阅读入口，不替代原始产物、trace registry 或 gate 报告，也不会提高 claim ceiling。

## 最快开始

1. 从 [GitHub Releases](https://github.com/rv198-star/wff-release/releases) 下载最新公开 install pack。
2. 解压后先读包内 `WFF-START-HERE.zh-CN.md` 和 `README.md`。
3. 在业务项目里运行 `wff-init`。
4. 用 `using-wff` 判断任务是否进入 WFF、从哪里进入。
5. 需要角色入口时运行：

```bash
wff-agent setup <opencode|claude-code|codex> all --project-root <你的项目目录>
```

之后可直接使用 `@wff-product-manager`、`@wff-architect`、`@wff-programmer`、`@wff-qa-tester` 或 `@wff-reviewer` 发起对应任务。

## 安装模型

WFF 的安装单位是完整 skill 目录和配套资源，不是单个 `SKILL.md`。可运行入口通常还需要 `scripts/`、`templates/`、`docs/`、`reference-packages/`、`runtime-deps/`、install profile 和角色入口配置。

安装包内的详细说明见 `INSTALL-PACK-README.zh-CN.md`，角色入口见 [WFF Role Agents 使用指南](docs/WFF-ROLE-AGENTS.zh-CN.md)。

## 当前状态与证据

当前公开安装包请以 [GitHub Releases](https://github.com/rv198-star/wff-release/releases) 为准。当前公开 Release 为 **`v1.9.2`**，主资产是 `wff-v1.9.2-skills-install-pack.zip`。

`v1.9.2` 是责任/分发减肥后的正式全链路发布：GEO / PetClinic / BrainyPal 三个新建项目场景完成 P1 -> P4，Invoice / Legacy Customer ID / Oracle DB change / Order scale 四个存量项目完成 PX -> P1 -> P2 -> P3 -> P4；Final AI Review 与两轮独立收尾审计均 PASS。正式 release notes 见 [source tag 上的 v1.9.2 release notes](https://github.com/rv198-star/software-lifecycle-skills/blob/v1.9.2/docs/v1.9.2-release-notes.zh-CN.md)。

同一 release commit 还发布独立产品 **EKRI v0.9.0**（tag `ekri/v0.9.0`）。EKRI 拥有自己的版本、CHANGELOG 与 GitHub Release 身份，但继续保持在 WFF 用户侧 Skills、install profiles、公开 install pack 和 P1-P4/PX runtime 之外。WFF 的公开运行包不会携带 EKRI。

完整全链路生成物继续保持为本地/独立 proof evidence，不把大体量生成快照重新并回 `main`。发布口径、验证摘要与 claim ceiling 统一收敛在公开 release notes 与 GitHub Release 正文中。

## 继续阅读

1. [WFF 全局导航图](docs/public/wff-orientation-map.zh-CN.md)
2. [WFF Role Agents 使用指南](docs/WFF-ROLE-AGENTS.zh-CN.md)
3. [AI / External Review Surface](docs/public/human-review-surface.zh-CN.md)
4. `INSTALL-PACK-README.zh-CN.md`

## License

This project is currently under active development. License terms will be specified in a future release.
