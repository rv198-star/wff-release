# WFF Role Agents 使用指南

WFF Role Agents 是 v1.4 的可选实验入口。

它的目标很简单：让用户先用“产品经理、架构师、程序员、测试、重构架构师、评审员”这类人话角色进入 WFF，而不是一开始就记住所有 skill 名和阶段名。

它不是新的 LLM runtime，也不替代 P1-P4 或 PX。角色只是把已有 WFF skills、安装组合、项目上下文和证据边界组织成更容易调用的入口。

## 最短用法

如果你已经有 WFF install pack，并且有一个目标业务项目：

```bash
cd /path/to/wff-v1.4-skills-install-pack
./wff-agent setup opencode all --project-root /path/to/your-project
```

然后在 Agent 平台里这样说：

```text
@wff-product-manager 帮我把这个想法整理成可以进入 P1 的输入。
@wff-programmer 根据 P3 实现任务卡实现后端 API 和测试。
@wff-refactor-architect 先扫描这个旧系统的扩容风险和安全网。
@wff-reviewer 评审这批产物能不能进入下一阶段。
```

如果平台不支持 `@role` 形式，就直接引用生成的角色文件，让当前 Agent 按该角色边界工作。

## 先选角色

| 你想做什么 | 选谁 | 常用 WFF 入口 |
|---|---|---|
| 想法很粗，需要问清需求 | WFF Product Manager | `wff-req-chat`、`wff-req` |
| 已有 PRD，需要系统设计 | WFF Architect | `wff-arch` |
| 已有设计，需要实现和测试 | WFF Programmer | `wff-impl` |
| 想判断证据是否足够 | WFF QA Tester | `wff-validation` |
| 接手旧系统、重构、迁移、扩容 | WFF Refactor Architect | `wff-x` |
| 只想审查产物质量和缺口 | WFF Reviewer | 产物评审、可接手性评审、reader review |

角色不是人格扮演。角色的能力来自它挂载了哪些 WFF skills，以及它被限制在什么职责边界内。

对 P3 来说，用户通常只需要找 WFF Programmer 或 `wff-impl`。安全审计和交付打包属于 P3 收口侧能力，安装组合会带上，角色会在需要时调用；普通用户不需要先记住收口技能名。

## 安装前提

你需要两样东西：

1. WFF install pack 或本仓库源码。
2. 一个真实存在的目标业务项目目录。

建议先在目标项目里初始化 WFF 运行面：

```bash
cd /path/to/your-project
/path/to/wff-v1.4-skills-install-pack/wff-init
```

只安装 `role-agent-companion` 可以导出角色文件，但通常不够完成生命周期工作。要真正跑 PRD、架构、实现、验证或 PX，还需要对应 WFF skills 和支持资源对 Agent 平台可见。

## 导出命令

安装包形式：

```bash
./wff-agent setup <opencode|claude-code|codex> <all|role-id...> --project-root /path/to/your-project
```

源码形式：

```bash
python3 scripts/release/wff_agent.py setup <platform> <all|role-id...> --project-root /path/to/your-project
```

常用例子：

```bash
./wff-agent setup opencode all --project-root /path/to/your-project
./wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/your-project
./wff-agent setup codex all --project-root /path/to/your-project
```

## OpenCode

导出全部角色：

```bash
./wff-agent setup opencode all --project-root /path/to/your-project
```

输出位置：

```text
/path/to/your-project/.opencode/agents/
```

典型使用：

```text
opencode run --agent wff-programmer "根据 P3 实现任务卡实现后端 API 和测试。"
@wff-product-manager 帮我把这个想法梳理成可以进入 P1 的输入。
@wff-programmer 根据 P3 实现任务卡实现后端 API 和测试。
@wff-reviewer 评审这批 P2/P3 产物是否可交给下一阶段。
```

OpenCode 导出的 WFF 角色使用 `mode: all`，既可以作为 `opencode run --agent ...` 的直接工作角色，也可以在会话中用 `@wff-*` 方式点名。

如果 OpenCode 没有显示角色，先检查 `.opencode/agents/` 是否生成，再按 OpenCode 自身的项目 agent 加载规则排查。

## Claude Code

只导出程序员和评审员：

```bash
./wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/your-project
```

输出位置：

```text
/path/to/your-project/.claude/agents/
```

典型使用：

```text
请用 WFF Programmer 的职责边界处理这批 P3 实现任务卡。
如果发现架构边界冲突，不要直接改架构，转给 WFF Architect。
```

或者：

```text
请用 WFF Reviewer 评审这份 PRD，重点看事实缺口、过度声明和下游可接手性。
```

如果平台没有自动切换角色，可以直接引用 `.claude/agents/wff-reviewer.md` 中的说明。

## Codex

Codex 适配是降级入口，不声明原生角色切换。

```bash
./wff-agent setup codex all --project-root /path/to/your-project
```

输出位置：

```text
/path/to/your-project/
├── AGENTS.md
└── .codex/
    └── wff-agents/
```

典型使用：

```text
请按 .codex/wff-agents/wff-refactor-architect.md 的 WFF Refactor Architect 角色工作。
目标：已有系统用户量从 100 并发提升到 1 万并发。
先扫描现状、风险和安全网，不要直接开始改代码。
```

或者：

```text
请按 .codex/wff-agents/wff-reviewer.md 的 WFF Reviewer 角色评审 P3 实现任务卡。
只给出可接手性、证据缺口、过度声明和评分，不要重写主文档。
```

## 三个常见例子

### 从想法到 PRD

用户说：

```text
我想做一个面向小门店的库存和会员系统。
```

推荐说法：

```text
@wff-product-manager 帮我把这个想法梳理成可以进入 P1 的输入。
先问关键问题，不要直接写完整 PRD。
```

角色应该先问目标用户、买方、核心场景、成功标准和真实证据。条件足够后，再形成 P1 输入包。

### 旧系统从 100 并发提升到 1 万并发

用户说：

```text
现有后台以前只考虑 100 并发，现在要考虑 1 万并发。
```

推荐说法：

```text
@wff-refactor-architect 先按 PX 扫描现状。
目标是找出扩容改造边界、风险、安全网和目标架构，不要直接开始改代码。
```

角色应该先看代码、数据库、接口、业务流程和外部依赖，区分观察到的事实、推断出的风险和仍未知的部分。

### 只评审一批实现任务卡

用户说：

```text
这批 P3 实现任务卡能不能交给程序员做？
```

推荐说法：

```text
@wff-reviewer 评审这些实现任务卡的可接手性。
按 0-100 给分，重点看是否能直接实施、是否缺架构/接口/测试信息、是否有过度声明。
```

角色应该评审，不代写。发现需求缺口转 Product Manager，发现架构缺口转 Architect，发现实现证据缺口转 Programmer 或 QA Tester。

## 角色边界

下面的矩阵是 `config/wff-role-mounts.json` 和 `docs/role-agent-mounts/v1.4-role-agent-mounts.md` 的人类阅读摘要。它只解释角色读写审查边界，不新增角色能力。

| 角色 | 主要读什么 | 主要产出什么 | 审查什么 | 不能声明什么 |
|---|---|---|---|---|
| WFF Product Manager | 用户想法、业务背景、买方/使用者线索、成功标准、已确认事实、项目上下文 | 澄清问题、source truth / gap 摘要、P1 输入包、PRD-ready 范围和成功标准 | 需求是否可进入 P1、价值/范围/证据缺口、下游可接手风险 | 市场验证、预算批准、owner sign-off、架构决策、实现完成、验证通过 |
| WFF Architect | 已接受 PRD/P1 产物、业务约束、项目上下文、需要进入设计的存量系统事实 | P2 架构边界、模块/API/数据责任、ADR、工程设计与 P3 handoff | 边界清晰度、所有权、API/数据契约风险、技术选择是否服务业务约束 | 缺失的业务事实、代码已实现、测试已通过、生产可用 |
| WFF Programmer | 已接受需求、P2/P3 action cards、现有代码、测试约定、项目上下文 | 代码、局部实现设计、测试、API 文档、验证和交付 handoff 证据 | 任务是否可实现、契约冲突、局部设计、测试覆盖和失败路径 | 产品目标变更、模块/API/数据边界重设、超出已执行证据的验证结论、生产批准 |
| WFF QA Tester | 验收标准、实现产物、测试、日志、验证报告、可复现证据 | 验证结果、失败路径、缺陷复现、claim ceiling、证据缺口和重跑建议 | 证据是否足够、失败路径是否覆盖、缺陷是否可复现、声明是否越界 | 生产批准、真实 UAT 通过、人工评审完成、owner sign-off、最终质量裁决 |
| WFF Refactor Architect | 旧系统代码、数据库/API/运行事实、运维约束、历史流程、目标改造压力 | PX 扫描、现状基线、变更边界、重构/迁移方案、安全网和目标架构输入 | 旧系统事实是否充分、变更风险、迁移顺序、安全网是否先行 | 绿地假设、未看现状就重写、无安全网改造、生产 readiness |
| WFF Reviewer | PRD、设计、实现任务卡、代码/测试证据、handoff 包、reader 文档 | 评审发现、评分、阻塞项、过度声明清单、返回路径建议 | 产物质量、边界漂移、证据缺口、可接手性、claim ceiling | 代写正在评审的主线产物、伪造证据、替代阶段责任、替代 owner/人工批准 |

如果角色发现自己不该做当前任务，应该返回正确角色或上游阶段。

## 常见问题

### 只安装 Role Agents 可以吗？

可以导出角色文件，但通常不够用。

Role Agents 像岗位说明书和入口导航。要真正跑 PRD、架构、实现、验证或 PX，还需要安装对应 WFF skills，并保留 install pack 中的支持资源。

### `project root does not exist` 是什么？

`--project-root` 指向的业务项目目录不存在。

先创建或选择真实项目目录：

```bash
mkdir -p /path/to/your-project
```

然后重跑 `wff-agent setup ... --project-root /path/to/your-project`。

### 导出了文件，但平台里看不到角色怎么办？

先检查文件是否生成：

- OpenCode：`.opencode/agents/*.md`
- Claude Code：`.claude/agents/*.md`
- Codex：`.codex/wff-agents/*.md` 和 `AGENTS.md`

如果文件存在但平台 UI 没显示，通常是平台自己的项目 agent 加载规则问题。此时可以直接把生成文件作为角色说明引用给当前 Agent。

### Codex 里能不能 `@wff-programmer`？

当前 WFF 适配层不声明 Codex 支持这种原生切换。

Codex 推荐显式引用角色说明：

```text
请按 .codex/wff-agents/wff-programmer.md 的 WFF Programmer 角色工作。
```

## 当前能说明什么

v1.4 的 WFF Role Agents 是实验性的可选入口和平台配置导出层。

可以声明：

- 可以导出 OpenCode、Claude Code、Codex 的项目本地角色文件。
- 可以把角色与 WFF skills、安装组合和证据边界对齐。
- 可以作为用户理解和使用 WFF 的低门槛入口。
- 本机 Codex CLI 可读取项目 `AGENTS.md` 中的 WFF Role Agents 引用块，并定位到 `.codex/wff-agents/wff-programmer.md`。
- 本机 OpenCode CLI 可发现 `.opencode/agents/` 下的 6 个 WFF 角色；OpenCode `1.15.10` + Codex NewAPI 配置下，`mode: all` 的 `wff-programmer` 可通过 `opencode run --agent wff-programmer --model newapi/gpt-5.5` 直接运行。
- 本机 Claude Code CLI `2.1.110` 可发现 `.claude/agents/wff-programmer.md`；经临时 Anthropic Messages -> GPT gateway 配置到 Codex NewAPI 后，`claude -p --agent wff-programmer --model gpt-5.5` 可读取 WFF role instruction 并返回 `ROLE-ID:wff-programmer`。

不能声明：

- 三个平台的所有版本都已完成真实 UI 端到端验收。
- OpenCode 的所有 WFF 角色都已经完成真实复杂任务执行验收。
- Claude Code 的所有 WFF 角色都已经完成真实复杂任务执行验收。
- Codex 已支持 `@wff-programmer` 这类原生角色切换。
- Role Agents 可以脱离 WFF skills 独立完成生命周期工作。
- Role Agents 可以替代 P1-P4、PX、证据检查或人工评审。
- Role Agents 证明了生产可用、上线批准或真实 UAT 通过。
