# 开发实现阶段素材库启动建议（v0.1）

## 文档目的

这份文档用于回答：在正式启动第三阶段（实现 / 开发）Stage Skill family 建设前，应该先准备哪些 **小而硬** 的参考源与素材库入口。

它的目标不是做“编码最佳实践大全”，而是为 Phase-3 产物提供可落到 **artifact / gate / refusal / evidence / traceability** 的来源支撑。

> 选择原则：**能被转译成可检查的 gate / 清单 / 证据要求的素材优先**；纯经验散文和语言细节教程降级为 lane optional。

---

## 一、Phase-3 当前最缺的是什么

Phase-3 的核心缺口通常不是“AI 不会写代码”，而是：

1. **实现入口的硬门槛**：没有可执行的 build/test/lint/typecheck baseline，就会出现“先写代码再补质量”的漂移。
2. **可审计的工程证据**：实现完成的主张需要对应证据（命令、报告、覆盖说明、缺陷/风险记录）。
3. **实现与上游契约一致性**：Phase-2 的 module map / interface contract / constraints 必须在实现阶段被尊重并能追踪。
4. **公共组件抽取治理**：避免“重构/抽取伪进度”，并明确 ownership 与抽取 gate。

---

## 二、第一批推荐 starter set（优先非书籍、真实模板；书籍/标准作为 backbone）

> 说明：Phase-3 最有效的来源通常不是书，而是“可直接被转译为 gate 字段与可执行命令”的真实模板与规约。
>
> 所以这里按优先级分两层：
> - **Tier-0（强推荐，最快落地）**：真实项目模板/规范/命令基线/检查清单
> - **Tier-1（backbone）**：书籍/公开工程实践文档，用于补齐结构语言与反模式

### Tier-0：最快落地的来源（强推荐先收集）

1) **CI Pipeline / build-test 脚本与配置（来自 1~2 个真实项目）**
- 目标：直接提炼 `build_cmd/unit_test_cmd/lint_cmd/typecheck_cmd` 的字段与阈值写法
- 产物：Stage-01 `Build/Test Gate Manifest` 的可执行样例

2) **Code Review Checklist（短版）+ 变更记录模板（来自团队实际）**
- 目标：把 review 从文化口号变成 gateable checklist + evidence 字段
- 产物：`Coding Baseline Contract` + `Implementation Evidence Pack` 字段

3) **仓库贡献指南/工程规范（若已有）**
- 目标：抽取“可检查规则”（目录结构、模块边界、依赖方向、生成代码处理）
- 产物：module boundary rules + dependency direction rules

4) **组件抽取/复用治理样例（哪怕是 1 页内部约定）**
- 目标：形成 `Shared Component Extraction Policy` 的 gate 条款与 ownership 字段

5) **一个真实的 release / rollback / hotfix 流程摘要（可很短）**
- 目标：让 Phase-3 的 change control 有最小证据结构，而不是“以后再说”

6) **开发/测试环境 bootstrap 脚本与说明（强推荐）**
- 目标：让 AI 能在默认 AI-first 模式下独立把环境跑起来，避免 gate 卡死
- 例子：`devcontainer`、`docker-compose`、`make dev/test`、一键初始化脚本、最小环境依赖清单
- 产物：Stage-01 的 `dev_environment_bootstrap` / `test_environment_bootstrap` 字段与 blocked-remediation 模式

> 如果 Tier-0 收集到位，Phase-3 的 Stage-01/02 就可以启动；书籍更多用于补“为什么这样 gate”和反模式。

### 1) CI/CD 与部署流水线（支撑 build/test gate 的结构化表达）

**要吸收的能力：**
- pipeline 的阶段化结构（build → test → quality checks → package）
- 质量门禁如何定义为可检查条件
- evidence/报告如何作为 gate evidence

**推荐代表（候选）：**
- Continuous Delivery: Reliable Software Releases Through Build, Test, and Deployment Automation（Humble/Farley）
- Accelerate: The Science of Lean Software and DevOps（Forsgren/Humble/Kim）
- Trunk-based development 相关资料（用于约束分支策略与集成节奏，作为 optional lane）

**将被转译成的 Phase-3 工件：**
- Stage-01 `Build/Test Gate Manifest`（命令/阈值/证据）
- Stage-02/03 的 entry/exit gate（可执行条件，而非口号）

### 2) Code Review / Engineering Practices（支撑实现证据与一致性防护）

**要吸收的能力：**
- 代码评审的最小可检查项（而不是文化口号）
- 变更规模控制、回滚策略、risk 标注

**推荐代表（候选）：**
- Google Engineering Practices（code review / change list / testing guidance）

**将被转译成的 Phase-3 工件：**
- `Coding Baseline Contract`（短、硬、可 gate）
- `Implementation Evidence Pack` 的字段与证据要求

### 3) 依赖与模块边界治理（支撑 Phase-2 → Phase-3 一致性）

**要吸收的能力：**
- module boundary / dependency direction 的治理模式
- 如何定义“允许/禁止的依赖方向”并可被工具检查

**推荐代表（候选）：**
- 架构守护/依赖约束相关资料（例如依赖规则、架构测试理念）

**将被转译成的 Phase-3 工件：**
- module boundary rules（与 Phase-2 module map 绑定）
- 禁止穿透的依赖方向规则 + 对应检查方式

### 4) 可测试性与单元测试纪律（支撑最小测试基线）

**要吸收的能力：**
- 单测的范围边界（什么该测/不该测）
- 失败时如何提供可复验证据

**推荐代表（候选）：**
- 测试金字塔 / 测试分层策略（作为可转译成 gate threshold 的来源；注意避免把比例当硬指标）
- TDD / xUnit patterns / testability 相关权威资料（lane optional，按团队实践选择）
- The Art of Unit Testing（Roy Osherove，可作为 unit testing discipline 的 backbone 代表源）

**将被转译成的 Phase-3 工件：**
- Stage-01 的 `unit_test_cmd` + 最小通过门槛
- Stage-02 的“实现必须绑定 TEST-*”的 traceability hook

#### 当前已吸收的第一轮抽取资产

`The Art of Unit Testing` 已完成第一轮项目内抽取，位于：

- `sources/books/extracted/the-art-of-unit-testing/index-map.md`
- `sources/books/extracted/the-art-of-unit-testing/cards-draft/`
- `sources/books/extracted/the-art-of-unit-testing/stage-guidance-draft.md`
- `sources/books/extracted/the-art-of-unit-testing/alignment-review.md`

当前最适合直接吸收到 Phase-3 的单元包括：

- testability seams（接口提取 / 依赖注入 / 避免硬编码依赖）
- trustworthy / maintainable / readable 三支柱
- one mock per test / avoid overspecification
- test organization / test API
- legacy code 的 pre-refactor safety net

#### 第一轮已确定的吸收去向

- **Stage-01 / Coding Baseline Contract**：
  - FICC 最小可测试性门槛
  - interface/seam extraction
  - 避免硬编码依赖 / static / 构造器逻辑
  - 测试公共契约而非私有实现

- **Stage-03 / implementation-audit-and-handoff-gate**：
  - trustworthy / maintainable / readable 三支柱
  - 避免测试逻辑
  - 一个测试一个 concern
  - 测试隔离
  - coverage 需结合 review / kill-check 思维
  - setup 不隐藏上下文
  - 命名规则

### 5) 组件抽取与复用治理（支撑 shared component extraction policy）

**要吸收的能力：**
- 什么时候抽取、抽取边界、ownership
- 抽取 gate：避免把“重构”当作交付

**推荐代表（候选）：**
- 内部规范/贡献指南类文档（最有效），其次才是书籍

#### 当前建议的阶段放置（已收敛）

采用 **方案 A**：

- **Phase-2**：只决定共享候选、ownership、no-go 边界与抽取条件
- **Phase-3 Stage-02**：在真实实现中执行抽取（如果满足 gate）
- **Phase-3 Stage-03**：只审计抽取是否合理，不把大规模重构作为主要活动

这样可以避免两种常见失败：

- 在设计阶段过早抽象，造成共享模块空转
- 在 review 阶段把“重构/抽取”当成主要产出，拖慢交接与放行

#### 进一步的结构预留

如果后续共享抽取/可复用性治理成为持续高频活动，更合理的长期演进可能是：

- 在未来单独升格一个 **Refactoring / Reuse Convergence Phase**

而不是继续把系统性重构压在 Phase-3 Stage-03 里。

---

## 二点五、starter set → Phase-3 工件映射（摘要）

| source | 主要吸收点 | 对应 Phase-3 工件 |
|---|---|---|
| Continuous Delivery | pipeline stage / gate / automation spine | Build/Test Gate Manifest；Stage-02 entry/exit gates |
| Accelerate | 可量化的交付与质量信号（DORA 等） | gate evidence 字段；变更失败/回滚证据结构 |
| Google Engineering Practices | 可检查的 code review / change discipline | Coding Baseline Contract；Implementation Evidence Pack 字段 |
| Traceability（见 repo traceability layer） | requirement→implementation→test link semantics | MOD/TEST trace hooks；evidence pointer 结构 |
| 测试金字塔/分层策略 | 单测/集成/E2E 的门禁化表达 | unit_test_cmd + 覆盖/耗时/稳定性阈值字段 |

**将被转译成的 Phase-3 工件：**
- `Shared Component Extraction Policy`

---

## 三、推荐同时准备的“非书籍素材”（更贴近可执行 gate）

Phase-3 的素材库不应只依赖书。

建议同步准备这些“可被引用/吸收”的工程素材模板（可直接作为 source units）：

1. **Build/Test/Lint/Typecheck 命令基线样例**（以 2~3 条 lane 为代表即可）
2. **Code review checklist（短版本）**
3. **变更记录模板**（变更范围、风险、回滚、证据路径）
4. **组件抽取提案模板**（候选、理由、影响面、owner、版本策略）

---

## 六、启动前“素材包清单”（建议你先收集到仓库之外，再进 source-register）

在正式启动 Phase-3 authoring 前，建议至少准备到这些具体对象（不要求完美，但要真实）：

- 1 个项目的 `CI pipeline config`（例如 GitHub Actions / GitLab CI / Jenkinsfile 任一）
- 1 个项目的 `build/test/lint/typecheck` 命令集合（可以是 Makefile/npm scripts/justfile/脚本）
- 1 份短版 code review checklist（10~20 条）
- 1 份变更记录模板（含风险/回滚/证据路径）
- 1 份组件抽取提案模板（含 ownership 与 gate 条款）

有了这些，Phase-3 Stage-01 就能把 D 默认的 gate manifest 写到“可执行”而不是“占位”。

---

## 四、当前不建议一开始重投入的方向

1. 多语言“编码规范大全”
   - 只会膨胀为教程，且很难 gate。
   - 更好的做法：以 D 模 gate manifest + lane optional 的方式承载。
2. 过早绑定具体框架生态
   - Phase-3 允许 D 默认；只有 Auto-C 才在 Stage-01 内形成 provisional stack lock。

---

## 补充说明：Phase-3 vs Phase-4 的测试边界（推荐）

为避免 Phase-3/Phase-4 职责重叠，建议采用如下边界（与你提出的“单测/接口测是否属于 Phase-3”对齐）：

### Phase-3（实现阶段）必须承担的测试证据

- **单元测试（unit）自动化**：作为编码完成的最小 DoD（配合 `unit_test_cmd` gate）
- **接口级/契约级 smoke（interface/contract smoke）自动化**：用于证明实现没有悄悄偏离 Phase-2 的接口契约/错误模型

并且建议将其明确写成 Phase-3 的“必须门禁”（不是建议项）：

- Stage-02 不允许进入“交接可用”状态，除非 `unit_test_cmd` 与 `interface/contract_smoke_cmd` 均可运行且通过

#### 关于“覆盖（coverage）”的建议定义

这里的覆盖不建议一开始绑定到单一百分比指标（容易变成指标游戏）。更可迁移的最小覆盖定义是：

1) **Claim coverage**：关键业务主张（来自 REQ/FLOW）至少有一个自动化验证点（TEST-*）
2) **Contract coverage**：关键接口契约（API-*/error model）至少有一个 smoke 验证
3) **Regression safety**：对高风险路径的回归用例可重复执行、可提供证据

> 它们属于“开发自检 + 交接证据”，因此归 Phase-3。

### Phase-4（测试验证阶段）承担的验证责任

- 覆盖规划（risk-based / claim-based coverage）
- 跨模块/跨系统验证（integration/system）
- 缺陷识别与证据化记录
- 收口与放行判断（entry/exit gate + risk acceptance）

> 它们属于“质量验证 + 交付判断”，因此归 Phase-4。

---

## 五、下一步落库动作（建议）

1. 建立 `development-implementation-source-index`（最小索引表）
2. 用 `source-unit-coverage-ledger` 给 starter set 建立 coverage ledger
3. 先把 `The Art of Unit Testing` 的关键 cards 映射到 Phase-3 Stage-01/02/03 的 artifact 字段与 gate 条款
4. 然后再按 Phase-3 authoring 的真实缺口，定向扩充 lane sources

---

## 一句话结论

Phase-3 的 starter 素材库应优先覆盖：

- CI/CD 与质量门禁（可执行 gate）
- code review / change discipline（证据与一致性）
- module boundary / dependency governance（约束落地）
- 最小测试纪律（unit test baseline）
- 组件抽取治理（避免伪进度）
