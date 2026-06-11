# Phase-3 Skill 体系架构设计 v0.1

> **创建日期**: 2026-04-01
> **上游依赖**: P1 Skill v14, P2 Skill v14, `phase-2-completion-and-phase-3-guidance-v0.1.md`
> **设计原则**: 接口先行 → 测试先行 → 实现后置
> **目标**: 定义 Phase-3（实现/开发）的 Skill Family 结构、执行流程与质量门禁

> **当前纠偏补充**：在具备服务器环境时，后续 Phase-3 执行还必须遵守 [phase-3-runnable-delivery-correction-v0.1.zh-CN.md](phase-3-runnable-delivery-correction-v0.1.zh-CN.md) 中定义的“真实可运行交付”约束；generated runtime 只能作为 bootstrap 支架，不能再被当成完成态。
>
> **2026-04-20 v1.2 落地状态补充**：
> - `backend-first` 已成为当前 `P3` 默认主线口径。
> - `run_phase3_first_version.py` 默认只输出 `backend-first mainline`；`--enable-ui-fallback`、`--enable-dispatch-lane` 均为显式 optional lane。
> - `phase3_dispatch_runner.py` 作为 `dispatch / worker-packet / wave` 执行线保留，但不再代表默认主线。
> - `phase3_delivery_gate.py` 已内聚主线评估产物输出：`phase-mainline-scorecard.md`、`phase-acceptance-matrix.md`、`phase-verdict.json`。
> - foundation runner 与 dispatch post-refresh 的 delivery closure 已统一下沉到 `scripts/phase3/delivery_closure.py`，主线 verdict / report / metadata sync 不再各自重复实现。
> - foundation runner 的 shared bootstrap artifact assembly / bootstrap-stage wrapper 已进一步下沉到 `scripts/phase3/foundation_bootstrap.py`。
> - foundation runner 的 optional dispatch lane bootstrap 已下沉到 `scripts/phase3/dispatch_lane_bootstrap.py`；dispatch runner 的 runtime refresh / preflight / unlock ceiling 内核已下沉到 `scripts/phase3/dispatch_runtime.py`。
> - foundation runner 的 path resolution / workspace preparation / delivery finalization / summary emission 已进一步下沉到 `scripts/phase3/foundation_mainline.py`。
> - dispatch runner 的 cycle / loop execution 与 report markdown / JSON 落盘已进一步下沉到 `scripts/phase3/dispatch_execution.py`，runner 顶层继续收成 wrapper + CLI routing。

---

## 一、设计哲学

### 1.1 核心序：Contract → Test → Code

Phase-3 的执行纪律可以用一句话定义：

> **先冻结接口，再写测试证明接口的行为预期，最后写代码让测试变绿。**

这不是 TDD 的简单套用。它是把 Phase-2 建立的 **contract 体系**（ESP 中的 16 个 endpoint 合约、11 个场景、5 个 replay、14 张表的 schema）转化为 **可执行验证面** 的工程过程：

```
P2 ESP contracts (declarative)
    │
    ▼  S01: 冻结
Executable Contracts (OpenAPI spec + DB schema + type definitions)
    │
    ▼  S02: 验证定义
Test Suites (contract tests + scenario tests + replay tests + unit tests)
    │
    ▼  S03: 实现
Production Code (让测试变绿)
    │
    ▼  S04: 加固 + 交付
Audits + Docs + Deploy (在已验证代码上做终态检查)
```

### 1.2 为什么这个序是唯一正确的

| 传统序（实现 → 测试 → 审查） | 本框架序（接口 → 测试 → 实现） |
|---|---|
| 测试验证"代码做了什么" | 测试定义"代码应该做什么" |
| API 形状由实现自然涌现 | API 形状由 P2 合约冻结 |
| 接口不一致在审查阶段才暴露 | 接口不一致在测试编写阶段就暴露 |
| Code Review 是事后审计 | Code Review 是持续伴随（但终态审计仍在 S04）|
| 设计-实现漂移在集成时爆发 | 设计-实现漂移被合约测试持续阻断 |

### 1.3 与 Phase-1/2 的结构性延续

Phase-2 guidance §5 明确说：

> "越接近真实工程执行，越要把不确定性、边界、交接和验证前置为工程结构本身。"

Phase-3 的回应是：把 P2 的 declarative contracts 前置为 executable contracts + test expectations，然后让实现去满足它们。这就是"验证前置为工程结构"的具体化。

### 1.4 本期与二期边界

`docs/current-project-consensus.md` 已经明确采用“两期目标切分”：

- 一期优先级最高的目标是把跨阶段 package system 推进到 **runnable-project proof**
- 二期才进入 **adoption / productization**，包括 intent-first 入口、role-legible 导航、安装/注册、quickstart 等

因此，Phase-3 v0.1 必须服从同一条边界纪律：**本期优先完成 deterministic implementation + runnable project delivery，generated runtime / scaffold 只能作为实现前置与验证支架，不能替代完成态。**

#### 本期（纳入 v0.1）

- 落定 `Contract → Test → Code` 的实现主线
- 从 P2 冻结的数据库 / 缓存 / 队列 / Auth / CI-CD 选型出发，落出可运行实现而不止是可执行骨架
- 在 S01 就落出现实运行基线：后端入口、运行命令、持久化接线、Dockerfile、compose、环境契约
- 在真实实现过程中执行 unit tests + contract tests + scenario tests + replay tests
- 支持 Phase-3 执行层使用 AI Agent 协作实现
- 在架构上预留 `agent-ready` 扩展位，但不要求业务产品本体已经是 agent-native

#### 二期（明确记录，但暂不纳入本轮默认交付）

- adoption / productization：
  - intent-first 入口
  - role-legible 导航
  - install / register / quickstart packaging
- product runtime 的 `agent-native` 融合支持：
  - Agent Team / Agent / Skill / Tool 的正式运行时分层
  - provider adapter / prompt registry / tool registry / output schema registry
  - memory / state / retrieval contract
  - guardrail / HITL / escalation policy
  - eval / replay / adversarial benchmark 作为正式质量门
  - cost / latency / SLO / fallback 治理

#### 二期启用前提

如果未来要把产品本体升级为 `agent-native`，不能只在 Phase-3 临时补入，必须先回补 P1/P2：

- P1 明确 Agent 价值、边界与验收标准
- P2 明确 Agent topology、tool contract、memory contract、guardrail contract、eval rubric
- P3 再据此实现 `agentic` 或 `hybrid_agent_service` 拓扑

---

## 二、Stage 结构设计

### 2.1 四阶段总览

| Stage | 名称 | 一句话目标 | 核心纪律 |
|---|---|---|---|
| **S01** | 边界冻结与合约具化 | 把 P2 declarative contracts 转为可执行的 OpenAPI spec + DB migration + Type 定义 | **只冻结接口，不写业务逻辑** |
| **S02** | 验证定义（Test-First） | 为每个合约面写测试——测试先于实现存在 | **测试是 S02 的产出物，不是 S03 的** |
| **S03** | 核心实现 | 按 WP 顺序写代码，唯一目标是让 S02 的测试变绿 | **实现的完成标准 = 测试通过** |
| **S04** | 质量加固与交付收敛 | Code Review + 安全审计 + API 文档 + 部署就绪 | **在已通过测试的代码上做终态审计** |

### 2.2 关键序的不可倒置性

```
S01 ──→ S02 ──→ S03 ──→ S04
接口冻结    测试先行    实现后置    审计交付

  ┃        ┃        ┃        ┃
  ┃ gate:   ┃ gate:   ┃ gate:   ┃ gate:
  ┃ spec    ┃ tests   ┃ green   ┃ audit
  ┃ frozen  ┃ compile ┃ rate    ┃ clean
  ┃        ┃ (fail)  ┃ ≥95%   ┃ 0 crit
```

**不可倒置规则**:
- S02 不能在 S01 输出 OpenAPI spec 之前开始（测试需要编译目标）
- S03 不能在 S02 产出测试之前开始（没有测试就没有完成标准）
- S04 的审计只能在 S03 代码基本稳定后执行（否则审计结果立即过时）

**允许的重叠**:
- S02 和 S03 可以按 WP 粒度流水线：WP-01 的测试写完后可以开始 WP-01 的实现，同时 WP-02 的测试并行编写
- S04 中的 API 文档生成可以在 S03 过程中渐进式执行

---

## 三、每个 Stage 的详细设计

### 3.1 Stage-01: 边界冻结与合约具化

#### 目标
将 P2 ESP 中的 declarative contracts 转化为三个 **可执行合约面**：

1. **API 合约** → OpenAPI 3.1 specification
2. **数据合约** → SQL migration files + jsonb validation schemas
3. **类型合约** → TypeScript / Python type definitions (shared between client & server)

#### 输入
| 来源 | 文件 | 提取内容 |
|---|---|---|
| P2 ESP §6.2 | API Endpoint Draft | 16 endpoints → OpenAPI paths |
| P2 ESP §5.2 | Schema Draft | 14 tables → SQL migrations |
| P2 ESP §6.5-6.10 | Contracts (envelope, error, pagination) | → 共享 type 定义 |
| P2 ESP §3.6 | Architecture Decisions | → 技术选型确认/覆盖 |
| P2 Stage-04 | WP + RBI | → 实现规划骨架 |

#### 执行步骤

```
 ┌─────────────────────────────────────────────────────┐
 │ Step 1: 技术选型确认                                   │
 │   ESP 约束 + Default Stack → tech-stack-decision.yaml │
 │   允许通过 ADR 覆盖默认选型                              │
 └────────────────────┬────────────────────────────────┘
                      ▼
 ┌─────────────────────────────────────────────────────┐
 │ Step 2: API 合约冻结                                   │
 │   ESP 16 endpoints → openapi.yaml                     │
 │   含 request/response schema + error codes            │
 │   含 canonical envelope + pagination params           │
 │   这是 S02 测试和 S03 实现的唯一权威接口定义               │
 └────────────────────┬────────────────────────────────┘
                      ▼
 ┌─────────────────────────────────────────────────────┐
 │ Step 3: 数据合约冻结                                   │
 │   ESP 14 tables → 001_initial_schema.sql              │
 │   jsonb 字段 → JSON Schema validation files           │
 │   index + constraint 与 ESP 一致                       │
 └────────────────────┬────────────────────────────────┘
                      ▼
 ┌─────────────────────────────────────────────────────┐
 │ Step 4: 类型合约冻结                                   │
 │   OpenAPI spec → 生成 TypeScript types                 │
 │   → shared types package (前后端共用)                   │
 │   → API client SDK skeleton                           │
 └────────────────────┬────────────────────────────────┘
                      ▼
 ┌─────────────────────────────────────────────────────┐
 │ Step 5: 项目骨架 + CI/CD                               │
 │   monorepo scaffold (apps/api + apps/web + packages/) │
 │   docker-compose.dev.yml + docker-compose.prod.yml    │
 │   Dockerfile + .env.example + migration/start scripts │
 │   CI: lint → type-check → test → build                │
 │   确保基线项目能启动 runtime，而不只是完成 build          │
 └────────────────────┬────────────────────────────────┘
                      ▼
 ┌─────────────────────────────────────────────────────┐
 │ Step 6: 追踪链继承与绑定                                  │
 │   先加载 P2 `.trace/trace.db` / traceability report       │
 │   再派生 phase-3-trace-registry.json                    │
 │   每个 P2 trace ID → P3 合约/测试/实现面绑定              │
 └─────────────────────────────────────────────────────┘
```

#### 产出物
| 文件 | 性质 | 说明 |
|---|---|---|
| `tech-stack-decision.yaml` | 决策 | 技术选型 + 覆盖 ADR |
| `openapi.yaml` | **合约（S02/S03 的权威源）** | 从 ESP 精化的完整 API 规范 |
| `db/migrations/001_initial_schema.sql` | 合约 | 数据表定义 |
| `db/schemas/*.json` | 合约 | jsonb 字段的 JSON Schema |
| `packages/shared-types/` | 合约 | 前后端共享类型 |
| `packages/api-client/` | 合约骨架 | API 客户端 SDK（只有类型签名，无实现） |
| `.github/workflows/ci.yml` | 基础设施 | CI pipeline |
| `Dockerfile` + `docker-compose.dev.yml` + `docker-compose.prod.yml` | 基础设施 | 开发 / 生产容器与运行基线 |
| Phase-2 `.trace/trace.db` / traceability report | 治理（上游权威） | 由 `wff-base-traceability-management` 管理的 P1/P2 trace identity、binding、link integrity |
| `phase-3-trace-registry.json` | 治理（派生视图） | P2→P3 合约/测试/实现绑定视图，不得替代上游 Trace Skill registry |
| `implementation-bindings.json` | 治理 / 起步面 | trace/test → WP / 代码骨架建议绑定 |
| `work-package-packets/` | S03 执行面 | 每个 WP 的执行包，收敛 scope / tests / contract slice / target files |
| `work-package-wave-plan.json` | S03 执行面 | 机器可读的执行波次计划，定义依赖顺序 / 并行面 / 阻塞项 |
| `worker-input-packets/` + `execution-loop-plan.json` | S03 执行面 | 按 wave/lane 自动切分 backend / frontend / platform worker 输入包与调度主清单；每个 packet 含 `packet_id` / `done_criteria` / `trace_subject_ids` / verification commands |
| `execution-runtime-state.json` + `dispatch-manifest.json` | S03 运行态 | 当前可派工包、队列包、阻塞包与 gate 回写后的运行态视图 |
| `worker-run-report.json` | S03 运行态 | worker 开工 / 实现完成 / 失败 / 阻塞事件的规范化汇总输入 |
| `phase3-verification-ledger.json` | S03 运行态 | 累积 packet 级 verification 证据，支持同一 WP 被 backend/frontend 多 packet 分摊时的共享 gate 聚合 |
| `worker-runs/` + `dispatch-cycle-report.json` + `dispatch-loop-report.json` | S03 运行态 | 每次 packet 执行的 runbook / verification script / packet run report，以及 dispatch cycle / 多轮 dispatch loop 的执行摘要 |

#### S01 质量门禁
- [ ] `openapi.yaml` 覆盖 ESP 全部 16 个 endpoint，schema 与 ESP 一致
- [ ] `001_initial_schema.sql` 可在空 PostgreSQL 上执行成功，表数 = ESP 定义
- [ ] Shared types 编译通过 (tsc --noEmit)
- [ ] `docker compose up` 或等价方式可完成基线启动与健康检查
- [ ] `Dockerfile` 的最终运行语义是启动服务，而不是只做 build
- [ ] Phase-2 `wff-base-traceability-management` registry 可加载、路径可用、未被 P3 自建 trace 系统替代
- [ ] P3 trace registry 作为派生视图覆盖 P2 所有需要进入实现/测试的 trace IDs
- [ ] **openapi.yaml 被标记为 frozen——后续修改需走 ADR 流程**

---

### 3.2 Stage-02: 验证定义（Test-First）

#### 目标
**在一行业务代码都不写的情况下**，定义完整的验证面。测试是 S02 的产出物，它们定义了 S03 的完成标准。

#### 核心原则

> S02 结束时，所有测试必须 **能编译、能运行、全部 FAIL**。
> 这证明测试是独立于实现编写的，而非实现完成后的事后验证。

#### 测试层次

```
                    ┌─────────────────────┐
                    │  Verification Replay │  验收级
                    │  (P2 的 5 个 replay)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Scenario Tests     │  场景级
                    │  (P2 的 11 个场景)     │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────┐
              │       Contract Tests             │  合约级
              │  (OpenAPI endpoint × behavior)   │
              └────────────────┬────────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │            Schema / Migration Tests          │  基础级
        │  (table structure + constraint + index)       │
        └──────────────────────────────────────────────┘
```

#### 3.2.1 层-1: Schema / Migration Tests

验证数据合约的正确性。

```typescript
// tests/schema/001_initial_schema.test.ts
describe("Schema: initial migration", () => {
  it("creates all 14 tables defined in ESP", async () => { /* ... */ });
  it("tracked_scopes has tenant_id NOT NULL + unique constraint", async () => { /* ... */ });
  it("observation_runs has jsonb column with CHECK constraint", async () => { /* ... */ });
  // ... 每个 ESP table 的结构断言
});
```

#### 3.2.2 层-2: Contract Tests

**每个 OpenAPI endpoint** 有对应的 contract test，验证：
- 请求 schema 校验（必选字段缺失 → 400）
- 响应 schema 校验（返回格式匹配 OpenAPI 定义）
- 错误码匹配（ESP canonical envelope 定义的 business_error / system_error）
- Pagination 行为（cursor-based，含 deep pagination protection）
- Tenant isolation（跨租户访问 → 403）
- Idempotency（重复请求 → 幂等响应）

```typescript
// tests/contracts/create-tracked-scope.contract.test.ts
describe("Contract: POST /v1/scopes", () => {
  it("returns 201 with canonical envelope on valid input", async () => { /* ... */ });
  it("returns 400 business_error validation_failed when scope_key missing", async () => { /* ... */ });
  it("returns 409 business_error duplicate_scope_key on duplicate", async () => { /* ... */ });
  it("returns 403 business_error tenant_forbidden on cross-tenant", async () => { /* ... */ });
  it("is idempotent on retry with same idempotency_key", async () => { /* ... */ });
});
```

每个 test case 名称格式: `Contract: {METHOD} {path} — {behavior}`

#### 3.2.3 层-3: Scenario Tests

映射 P2 Stage-03 的 11 个 scenario (GWT 格式):

```typescript
// tests/scenarios/scn-01-happy-path.scenario.test.ts
describe("SCN-01: Happy path — scope to review", () => {
  it("Given a configured tracked scope, When observation run completes, Then findings are generated with scores", async () => { /* ... */ });
  // ... 每个 GWT step
});
```

| P2 Scenario | P3 Test File | 覆盖范围 |
|---|---|---|
| SCN-01 ~ SCN-11 | `tests/scenarios/scn-{01..11}.scenario.test.ts` | 跨模块业务流程 |

#### 3.2.4 层-4: Verification Replay Tests

映射 P2 Stage-04 的 5 个 replay，作为最高级别的验收测试:

```typescript
// tests/replays/rp-01-happy-full-cycle.replay.test.ts
describe("Replay RP-01: Full happy cycle", () => {
  // 完整的 scope → run → finding → rec → task → review 链路
  // 验证每个中间状态转换和数据一致性
});
```

| P2 Replay | 路径 | 测试类型 |
|---|---|---|
| RP-01 | Happy path | E2E (Playwright or API chain) |
| RP-02 | Denial path | API integration + auth mock |
| RP-03 | Uncertainty path | API integration + provider timeout mock |
| RP-04 | Boundary path | Load test scenario + pagination edge |
| RP-05 | Seam path | API integration + external failure mock |

#### S02 产出物
| 文件 | 数量 | 说明 |
|---|---|---|
| `tests/schema/*.test.ts` | ~14 | 每个 ESP table 一个 |
| `tests/contracts/*.contract.test.ts` | ~16 | 每个 ESP endpoint 一个 |
| `tests/scenarios/*.scenario.test.ts` | ~11 | 每个 ESP scenario 一个 |
| `tests/replays/*.replay.test.ts` | ~5 | 每个 P2 replay 一个 |
| `tests/unit/**/*.unit.test.ts` | 按模块 / 页面生成 | packet 绑定的 unit baseline，覆盖 service/domain/UI-state 逻辑入口 |
| `tests/fixtures/` | — | 测试数据 fixtures |
| `tests/helpers/` | — | 测试工具函数 |
| `test-coverage-plan.md` | 1 | 测试覆盖计划文档 |
| `test-trace-matrix.json` | 1 | P2 trace ID ↔ test case 映射 |

#### S02 质量门禁
- [ ] 所有测试文件编译通过 (`tsc --noEmit`)
- [ ] `contract/scenario/replay` 的验证预期已先于真实业务实现被定义；若存在 generated runtime / scaffold，其暂时性绿灯只证明 contract wiring，不得被解释为实现完成
- [ ] 每个 ESP endpoint 至少有 1 个 contract test
- [ ] 每个 ESP scenario 有对应 scenario test
- [ ] 每个 P2 replay 有对应 replay test
- [ ] 每个已绑定的模块 / 页面存在对应 unit baseline
- [ ] `test-trace-matrix.json` 覆盖 P2 所有 trace IDs
- [ ] **禁止在 S02 写任何 `src/` 目录下的业务代码**

---

### 3.3 Stage-03: 核心实现

#### 目标

写代码，让 S02 的测试从红变绿。

**完成标准不是"代码写完了"，而是"测试通过了"。**

#### 执行顺序: 按 WP 循环

```
for each WP in [WP-01, WP-02, WP-03, WP-04, WP-05, WP-06]:
    1. 实现 Backend（API controller + service + repository）
    2. 实现 Frontend（页面组件 + API 调用）
    3. 先运行该 WP 相关的 contract tests + scenario tests + replay tests
    4. 再运行该 WP 相关的 unit tests
    5. 全绿 → 下一个 WP
    6. 红灯 → 修实现（不改测试，除非 S01 合约需要 ADR 变更）
```

#### 3.3.1 后端实现

```
apps/api/src/
  modules/
    auth/              # WP-01: Auth + Tenant
      auth.controller.ts
      auth.service.ts
      auth.guard.ts
      tenant.middleware.ts
      dto/
    scope/             # WP-02: Scope + Observation
      scope.controller.ts
      scope.service.ts
      observation-run.service.ts
      dto/
    findings/          # WP-03: Finding + Recommendation
      finding.controller.ts
      finding.service.ts
      recommendation.service.ts
      dto/
    tasks/             # WP-04: Task
      task.controller.ts
      task.service.ts
      dto/
    review/            # WP-05: Review + Reporting
      review.controller.ts
      review.service.ts
      dto/
    seams/             # WP-06: External integration seams
      attribution.adapter.ts
      notification.adapter.ts
  common/
    envelope.ts        # Canonical response envelope
    pagination.ts      # Cursor-based pagination
    errors.ts          # Business/system error types
    idempotency.ts     # Idempotency middleware
```

每个 module 的实现规则：
- Controller 层 **只做 HTTP 映射和验证**，不含业务逻辑
- Service 层包含业务逻辑，**必须引用对应的 S02 contract test 中验证的行为**
- Repository 层封装数据访问，**使用 S01 生成的 shared types**
- 所有 endpoint 必须返回 canonical envelope 格式
- 每次 commit 后运行该 WP 的 contract tests

#### 3.3.2 前端实现

##### 路径选择（在 S01 决定）

| 条件 | 路径 | 说明 |
|---|---|---|
| 有 Figma 设计稿 | **Figma2HTML → 框架组件** | 从设计稿提取 design token + 组件结构 → 生成 HTML/CSS → 转为 React/Vue 组件 |
| 无设计稿 | **HTML2Code（直接生成）** | 从 ESP prototype surface 描述 + UI 库 → 直接生成框架组件 |

##### 前端结构

```
apps/web/
  app/                          # Next.js App Router / Nuxt pages
    (auth)/
      login/page.tsx
      callback/page.tsx
    (dashboard)/
      overview/page.tsx         # Surface 2: Findings overview
      findings/[id]/page.tsx    # Surface 3: Finding detail → recommendation
      tasks/page.tsx            # Surface 4: Task board
      review/page.tsx           # Surface 5: Review reports
    onboarding/page.tsx         # Surface 1: Scope setup
  components/
    ui/                         # UI 库组件 (shadcn/ui | Ant Design)
    domain/                     # 业务组件
  lib/
    api/                        # 使用 S01 生成的 api-client SDK
```

前端实现规则：
- API 调用 **只通过 S01 生成的 typed API client**，不直接构造 HTTP 请求
- 页面 5 个 surface 与 P2 ESP §10.4 prototype surfaces 一一对应
- 状态管理基于 server state (React Query / SWR / Nuxt useFetch)，不过度引入 client state
- 每个 surface 完成后运行对应的 scenario test / replay test

#### 3.3.3 执行循环（packet runtime）

这条 `dispatch / packet runtime` 线在 `v1.2` 当前口径中是 **显式 optional lane**。

默认 `backend-first mainline` 不要求先启用它；只有在交付上下文确实需要多 packet / multi-worker / repeat-until-stalled 调度时，才显式进入这条执行线。

S03 不应该让 backend / frontend worker 直接从整份 ESP 或整份 handoff 开工，而是只从当前可派工 packet 开工：

```
dispatch-manifest.json
    → phase3_dispatch_runner.py
    → 选择当前 ready packet
    → phase3_dispatch_runner.py --packet <packet-id>
       - 落 packet-context.json
       - 落 execution-runbook.md
       - 落 verification-commands.sh
       - 由 `scripts/phase3/worker_packet_runner.py` 内聚执行 lint / typecheck / targeted-tests / unit-tests / build
       - 落 verification-report.json + per-step logs / step reports
       - 回写 phase3-verification-ledger.json，累积跨 packet 的 targeted/unit green evidence
       - 记录 worker-run-report.json
       - 可选调用 `phase3_dispatch_runner.py --mode wp-gate-cycle`
       - 刷新 execution-runtime-state.json
```

当前 `v1.2` 实现里，dispatch cycle / repeat-until-stalled loop 的主体执行，以及 `dispatch-cycle-report.*` / `dispatch-loop-report.*` 的 markdown / JSON 落盘，已统一下沉到 `scripts/phase3/dispatch_execution.py`；`phase3_dispatch_runner.py` 顶层主要保留 CLI routing、依赖注入和兼容 patch 面。

这意味着 S03 已经不只是“静态切包”，而是具备了最小运行态闭环：
- ready packet 可以被正式选中
- 选中后会转为 `in-progress`
- verification commands 可以被真实执行并产出结构化 evidence
- `targeted-tests` 仍然是主验证面；其中后端 contract/interface evidence 是 P3 的硬门槛
- 后端 `tests/unit/api/*` 同样是硬门槛；`tests/unit/web/*` 与其余前端导向证据仍需跟踪，但可在 warning 下转入 Phase 4 跟踪
- wave 解锁仍然由 `worker-run-report + wp_gate` 驱动，而不是人工口头推进
- 同一 WP 若拆成 backend/frontend 多个 packet，gate 会通过 verification ledger 聚合前序已绿的测试证据，而不是只看本次 run
- packet 级执行证据可直接回灌到后续 hardening / delivery report

#### S03 质量门禁（per WP）
- [ ] 若该 WP 含后端责任，其对应的 **backend contract/interface tests 通过**
- [ ] 若该 WP 含非平凡后端逻辑，其对应的 **backend unit tests 通过**
- [ ] 该 WP 涉及的 scenario/replay 与 frontend unit evidence 已执行；若前端验证暂未闭环，必须以 warning / follow-up 形式显式记录
- [ ] 类型检查通过 (`tsc --noEmit`)
- [ ] Lint 通过 (0 errors)
- [ ] 前端页面可渲染且 API 调用连通

#### S03 终态质量门禁
- [ ] **全部 backend contract/interface tests 通过** (冻结 API 边界)
- [ ] **全部 backend unit tests 通过** (service/domain logic)
- [ ] scenario/replay 与 frontend unit/component evidence 已执行并纳入交付报告；未闭环项必须显式转入 Phase 4 跟踪
- [ ] 测试覆盖率 ≥ 80% (核心业务逻辑)
- [ ] 0 TypeScript errors, 0 lint errors

---

### 3.4 Stage-04: 质量加固与交付收敛

#### 目标
在已通过测试的代码上做终态审计、文档生成和部署准备。

**S04 不应发现功能性 bug** — 如果发现，说明 S02 的测试不够。此时应先补测试（回到 S02 纪律），再改实现。

#### 3.4.1 Code Review (`wff-impl-review`)

**定位**: 在已验证的代码上做结构性审查——不是验功能（那是测试的事），而是验质量。

| 审查维度 | 检查内容 | 方法 |
|---|---|---|
| **结构一致性** | 模块结构符合 S01 骨架定义 | 目录结构 diff |
| **API 合约一致性** | 实现与 `openapi.yaml` 无漂移 | OpenAPI diff 工具 |
| **命名一致性** | 代码命名与 ESP glossary 一致 | glossary checker |
| **错误处理一致性** | canonical envelope pattern 遵循度 | Lint rule + 抽查 |
| **复杂度** | cyclomatic complexity ≤ 10 per function | ESLint / SonarQube |
| **重复** | 无跨模块 copy-paste 逻辑 | jscpd / sonar duplicate |
| **依赖方向** | 模块依赖方向符合 P2 domain decomposition | 依赖图工具 |

产出: `code-review-report.md` + `code-review-metrics.json`

#### 3.4.2 Security Audit (`wff-impl-security`)

| 审计层 | 检查项 | 工具 |
|---|---|---|
| **Auth 实现** | OIDC 流程、token 过期处理、CSRF | OWASP checklist + 手动 |
| **Tenant 隔离** | 所有 SQL 含 tenant_id WHERE、middleware 注入验证 | 代码搜索 + 测试覆盖 |
| **输入验证** | 所有 API 入参有 Zod/Joi schema | schema 覆盖率 |
| **依赖安全** | npm audit / Snyk | 自动化扫描 |
| **密钥管理** | 无硬编码、.env 不入库 | grep + git log |
| **数据敏感度** | P2 data sensitivity matrix 对应字段的加密/脱敏 | 字段级审查 |
| **OWASP Top 10** | 逐项对照 | checklist |

产出: `security-audit-report.md` + `security-audit-checklist.json`

#### 3.4.3 API Documentation (`wff-impl-api-docs`)

**流程**:

```
S01 的 openapi.yaml (权威源)
    + S03 实现中的代码注解补充
    → 最终 openapi-final.yaml
    → 与 S01 原版 diff → consistency report
    → 文档网站生成 (Swagger UI / Redoc)
```

一致性规则：
- S01 openapi.yaml 中定义的 endpoint / schema / error code 不可被删除
- S03 可以 **增加** schema 字段（向后兼容），但不可修改已冻结字段
- 任何不一致必须有对应 ADR

产出: `openapi-final.yaml` + `api-doc-consistency-report.md` + `docs/api/`

#### 3.4.4 部署与交付

| 产出 | 说明 |
|---|---|
| `Dockerfile` + `docker-compose.prod.yml` | 生产部署配置 |
| `deploy-runbook.md` | 部署/回滚步骤 + 监控指标 + 告警规则 |
| `performance-baseline.json` | 关键 API p50/p95/p99 延迟 |
| `phase-3-acceptance-report.md` | 验收汇总（测试 + 审计 + 文档覆盖率）|
| `phase-3-execution-report.md` | 执行报告（含 gate 结果 + trace 统计）|
| `phase-mainline-scorecard.md` | 面向 `P3` 主交付物的主线评分卡，明确 backend mainline 是否达标 |
| `phase-acceptance-matrix.md` | 将关键交付项与验收状态映射成 reviewer 可读矩阵 |
| `phase-verdict.json` | 机器可读的 `P3` verdict / blockers / scores 汇总，用于后续阶段消费 |
| `phase-3-trace-registry-final.json` | P2→P3 追踪链终态 |

当前 `v1.2` 口径下，上述 closure / verdict / mainline assessment artifacts 统一由 `phase3_delivery_gate.py` 负责落出；foundation runner 与 dispatch post-refresh 共用 `phase3_support/delivery_closure.py` 完成多轮 delivery analyze / report rewrite / verdict 落盘，artifact 写入后的 metadata 同步由 `phase3_support/mainline_assessment.py` 内聚。

#### S04 质量门禁
- [ ] Code Review 无 Critical/High 未解决项
- [ ] Security Audit 无 Critical 漏洞
- [ ] API 文档与 S01 openapi.yaml 一致性 ≥ 95%
- [ ] Docker 镜像可构建 + 健康检查通过
- [ ] 性能基线 p95 < ESP 目标值
- [ ] Trace registry 终态覆盖 P2 所有 trace IDs
- [ ] **所有 S02 测试仍然通过**（无退化）

#### Phase-3 Formal State Ladder

| Formal State | 含义 | 进入条件 |
|---|---|---|
| `blocked` | Phase-3 无法继续推进 | S01/S02 bootstrap gate 未通过 |
| `foundation-ready` | contract pack + failing test pack + initial execution scaffold 已冻结，可开始实现 | `phase3-quality-check.json` = pass |
| `implementation-in-progress` | 已开始实现，但未完成全部实现 gate | 已有 build/lint/typecheck/coverage 信号，但 S03 gate 未全绿 |
| `implementation-ready` | 代码与测试层面已收敛，可进入终态审计/交付 | build + lint + typecheck + backend targeted interface evidence + backend unit tests 全绿；前端验证缺口若存在，必须显式转入 warning / Phase-4 follow-up |
| `delivery-ready` | P3 完整完成，可交付给部署/验收/Phase-4 | S04 审计、文档、部署、trace、验收 gate 全绿 |

判定原则：
- `implementation-ready` 之前，不得宣称 P3 “已完成”
- `delivery-ready` 才是严格意义上的 **Phase-3 Complete**
- 状态判定由聚合 gate 脚本给出，而不是由人工口径解释
- 缺失所需 runtime-validation environment 的 packet / lane 可以继续静态实现，但 ceiling 只能停在 `implementation-in-progress` 以下，直到 ledger 中记录的运行环境补齐
- 对 server / web lane，Docker 是默认 runtime-validation environment；对 iOS / Android / Flutter / Electron 等 lane，必须定义等价运行环境并显式登记缺口

---

## 四、Skill Family 结构

### 4.1 编排架构

```
wff-impl (入口 Skill)
  │
  ├── [S01] 自身执行: 合约冻结 + 骨架生成
  │
  ├── [S02] 自身执行: 验证定义 (test-first)
  │         调用: wff-impl-verification (测试框架 + fixture 设计)
  │
  ├── [S03] 编排:
  │   ├── wff-impl-backend        (后端实现)
  │   ├── wff-impl-frontend       (前端实现)
  │   │   ├── [path-a] Figma2HTML   (有设计稿)
  │   │   └── [path-b] HTML2Code    (无设计稿)
  │   ├── dispatch runner           (optional lane；当前 ready queue 调度 / repeat-until-stalled loop)
  │   └── WP 循环控制 (WP-01 → WP-06 顺序)
  │
  └── [S04] 编排:
      ├── wff-impl-review                 (代码审查)
      ├── wff-impl-security              (安全审计)
      ├── wff-impl-api-docs           (API 文档)
      ├── wff-impl-handoff    (部署 + 验收 + 交接)
      └── orchestrator 汇总最终 formal state
```

### 4.2 Skill 清单

| Skill | Stage 归属 | 可独立执行 | 说明 |
|---|---|---|---|
| `wff-impl` | S01, S02, S04 | ✓ | 入口 Skill，编排全流程 |
| `wff-impl-backend` | S03 | ✓ | 后端 API 实现（per WP 循环）|
| `wff-impl-frontend` | S03 | ✓ | 前端实现（含 Figma2HTML + HTML2Code）|
| `wff-impl-review` | S04 | ✓ | 代码审查 |
| `wff-impl-security` | S04 | ✓ | 安全审计 |
| `wff-impl-api-docs` | S04 | ✓ | API 文档生成 + 一致性验证 |
| `wff-impl-handoff` | S04 | ✓ | 部署、验收、交接与 final delivery gate |
| `wff-impl-verification` | S02 + S04 | ✓ | 测试框架 + 验收测试运行器 |

### 4.3 Skill 目录布局

```
skills/
  wff-impl/
    SKILL.md
    agents/
  wff-impl-backend/
    SKILL.md
    agents/
  wff-impl-frontend/
    SKILL.md
    templates/
      react-next/               # React + Next.js 模板
      vue-nuxt/                  # Vue 3 + Nuxt 模板
    agents/
  wff-impl-review/
    SKILL.md
    checklists/
      structure-consistency.yaml
      naming-consistency.yaml
    agents/
  wff-impl-security/
    SKILL.md
    checklists/
      owasp-top10.yaml
      tenant-isolation.yaml
    agents/
  wff-impl-api-docs/
    SKILL.md
    agents/
  wff-impl-verification/
    SKILL.md
    agents/
```

---

## 五、技术选型策略

### 5.1 Default Stack

| 层 | 默认选择 | 覆盖机制 |
|---|---|---|
| **后端语言** | TypeScript (Node.js) | S01 ADR |
| **后端框架** | NestJS | S01 ADR |
| **前端框架** | React + Next.js | S01 ADR (可覆盖为 Vue 3 + Nuxt) |
| **CSS/UI** | Tailwind + shadcn/ui | S01 ADR |
| **数据库** | PostgreSQL | 继承 P2 ESP (已冻结) |
| **缓存/队列** | Redis | 继承 P2 ESP (已冻结) |
| **Auth** | WorkOS / Auth0 | 继承 P2 Stage-04 (已缩窄) |
| **API 验证** | Zod | S01 ADR |
| **测试** | Vitest (unit/integration) + Playwright (E2E) | S01 ADR |
| **CI/CD** | GitHub Actions | S01 ADR |

### 5.2 覆盖语法

```yaml
# tech-stack-decision.yaml
defaults_inherited_from: "phase3-orchestrator-v0.1"
overrides:
  - target: frontend_framework
    value: vue3
    meta_framework: nuxt3
    reason: "team expertise in Vue ecosystem"
    adr_id: P3-ADR-02
```

Skill 检测 overrides 后自动切换模板目录和脚手架配置。

### 5.3 移动端（可选模块，v0.1 不实现）

| 平台 | Skill 名 | 定位 |
|---|---|---|
| iOS (Swift/SwiftUI) | `phase3-mobile-ios` | 可选 |
| Android (Kotlin/Compose) | `phase3-mobile-android` | 可选 |
| 跨平台 (React Native / Flutter) | `phase3-mobile-crossplatform` | 可选 |

预留接口：`tech-stack-decision.yaml` 中的 `mobile_targets: []` 字段。

---

## 六、Complexity Profile 继承

Phase-3 继承 P2 的 complexity classification:

| Profile | S02 测试规模 | S03 实现规模 | S04 审计深度 |
|---|---|---|---|
| **micro** | ≤ 20 contract tests, ≤ 3 scenarios | ≤ 5 endpoints, ≤ 3 pages | 轻量 review + 基础 checklist |
| **standard** | 40-80 contract tests, 8-12 scenarios | 10-20 endpoints, 5-10 pages | 完整 review + audit + API doc |
| **complex** | > 80 contract tests, > 12 scenarios | > 20 endpoints, > 10 pages | 深度 audit + 性能测试 + 合规 |

---

## 七、关键工具脚本设计

### 7.1 继承工具（来自 P1/P2）

| 脚本 | Phase-3 用途 |
|---|---|
| `gwt_format_checker.py` | S02 scenario test 命名格式验证 |
| `glossary_generator.py` | S04 代码命名一致性检查 |
| `complexity_classifier.py` | S01 profile 确认 |
| `wff-base-traceability-management` scripts | 加载并验证 Phase-2 `.trace/trace.db`，作为 P3 source authority 的 registry-first 入口 |

### 7.2 新增工具

| 脚本 | Stage | 用途 |
|---|---|---|
| `esp_to_openapi.py` | S01 | 从 ESP endpoint draft 生成 OpenAPI 3.1 spec |
| `esp_to_migration.py` | S01 | 从 ESP schema draft 生成 SQL migration |
| `openapi_to_types.py` | S01 | 从 OpenAPI spec 生成 TypeScript types |
| `api_client_scaffolder.py` | S01 | 从 OpenAPI spec 生成 typed API client 骨架 |
| `contract_test_scaffolder.py` | S02 | 从 OpenAPI spec 生成 contract test 骨架 |
| `scenario_test_scaffolder.py` | S02 | 从 ESP scenario matrix 生成 scenario test 骨架 |
| `replay_test_scaffolder.py` | S02 | 从 P2 replay 定义生成 replay test 骨架 |
| `test_trace_matrix_builder.py` | S02 | 构建 P2 trace ↔ test case 映射 |
| `openapi_diff_checker.py` | S04 | 比较 S01 spec 与最终 spec 的 diff |
| `phase3_stack_decision.py` | S01 | 从 P2 技术假设和选型矩阵生成 `tech-stack-decision.yaml` |
| `phase3_project_scaffold.py` | S01 | 生成 monorepo / CI / docker-compose.dev / env baseline |
| `schema_test_scaffolder.py` | S02 | 从 schema draft 生成 schema test 骨架 |
| `phase3_implementation_scaffolder.py` | S03-start | 生成 work-package plans、implementation bindings、backend/frontend stubs |
| `phase3_support/execution_loop_builder.py` | S03-start | 将 implementation bindings 收敛为每个 WP 可直接执行的 packet，基于 WP 依赖和 packet 状态生成 machine-readable wave plan，并进一步切分为 lane-specific worker input packets 和 execution loop plan |
| `phase3_dispatch_runner.py --packet/--wave/--lane` | S03-runtime | `optional lane` 的单 packet 执行入口；对单个 packet 落 runbook / verification script / packet run report，其 packet 执行内核已下沉到 `scripts/phase3/worker_packet_runner.py`，并内聚 packet verification command execution、worker-run ledger、verification ledger、runtime-cycle 刷新与 runtime dispatch state 生成能力，可记录 started / implemented / blocked / failed 事件 |
| `phase3_dispatch_runner.py` | S03-runtime | `optional lane` 的 dispatch cycle 入口；按 dispatch manifest 选择当前 ready packet 队列并执行一轮 dispatch cycle，或以 repeat-until-stalled 方式自动推进多个 wave；runner 顶层以 mode routing + orchestration 为主，runtime state refresh / preflight / unlock ceiling 已下沉到 support |
| `phase3_dispatch_runner.py --mode wp-gate-cycle` | S03-runtime | `optional lane` 的 WP gate 入口；内聚每个 WP 的 gate 判定逻辑，将 test/build/lint/typecheck 结果收敛为 `phase3-wp-gate.json` 并刷新 runtime；若存在 verification ledger，则自动聚合前序 packet 证据驱动下一 wave 解锁 |
| `phase3_support/post_execution_refresh.py` | S03-runtime + S04 bridge | 将 dispatch line 的 post-execution refresh / acceptance-report / execution-report / delivery-gate / mainline verdict 刷新逻辑下沉到 support 层；`phase3_dispatch_runner.py` 顶层仅保留兼容 wrapper |
| `phase3_support/delivery_closure.py` | S04 + cross-lane closure | 将 foundation runner 与 dispatch post-refresh 共用的 delivery analyze / acceptance-report / execution-report / `phase-verdict.json` / metadata sync 收敛成统一 helper，避免两条 closure 线重复演化 |
| `phase3_support/foundation_bootstrap.py` | S01/S02 shared bootstrap kernel | 将 foundation runner 与 bootstrap-stage 共用的 phase-2 source load、bootstrap artifact assembly、bootstrap summary 收敛成统一 helper，避免入口脚本继续承载大段编译骨架逻辑 |
| `phase3_support/dispatch_lane_bootstrap.py` | S03-start optional lane bootstrap | 将 foundation runner 中可选 dispatch lane 的 packet / wave / runtime bootstrap 收敛成统一 helper，避免 optional lane 逻辑回流默认主线 |
| `phase3_support/foundation_mainline.py` | S01/S02/S03-start mainline kernel | 将 foundation runner 的 path resolution、workspace preparation、delivery finalization、summary emission 收敛成统一 helper，避免默认主线 runner 顶层继续膨胀 |
| `phase3_support/dispatch_runtime.py` | S03-runtime optional lane kernel | 将 dispatch runner 的 runtime state refresh、toolchain preflight、frontend runtime ceiling 收敛成统一 helper，避免 dispatch runner 顶层继续承载内核细节 |
| `phase3_support/dispatch_execution.py` | S03-runtime optional lane kernel | 将 dispatch runner 的 cycle / loop 主体执行、dispatch report markdown / JSON 落盘收敛成统一 helper，避免 runner 顶层继续膨胀 |
| `phase3_support/trace_registry.py` | S01/S02 + S04 | 从上游 Trace Skill registry + test-trace-matrix 派生 `phase-3-trace-registry.json`，并在实现绑定后收敛为 `phase-3-trace-registry-final.json`；它是 P3 绑定视图，不是新的 trace identity system |
| `phase3_support/mainline_assessment.py` | S04 + cross-phase handoff | 将 `phase-mainline-scorecard.md` / `phase-acceptance-matrix.md` / `phase-verdict.json` 的 artifact 写入与 `phase3-run-metadata.json` 同步内聚成单一 helper，供 foundation runner 与 dispatch runner 共用 |
| `phase3_delivery_gate.py --mode api-docs` | S04 | 生成 `openapi-final.yaml`、API doc assets 与一致性报告 |
| `phase3_delivery_gate.py --mode coverage-collection` | S03/S04 | 收集 coverage 产物并执行 coverage + replay 门禁 |
| `phase3_delivery_gate.py --mode code-review` | S04 | 基于 trace / contract / implementation surface 生成结构化 code review 结论 |
| `phase3_delivery_gate.py --mode security-audit` | S04 | 基于 auth / tenant / error / audit surfaces 生成结构化安全审计结论 |
| `phase3_delivery_gate.py --mode delivery-handoff` | S04 | 生成 deploy runbook、Dockerfile、production compose、performance baseline |
| `phase3_delivery_gate.py` | S04 | 聚合 bootstrap / implementation / audit / deploy evidence，解析 formal state 与 phase-complete 结论，并生成 acceptance / execution closure reports，以及 `phase-mainline-scorecard.md` / `phase-acceptance-matrix.md` / `phase-verdict.json` |
| `phase3_quality_check.py` | S04 | 综合质量门禁 (D1-D6 for P3) |
| `run_phase3_first_version.py --mainline-stage bootstrap` | S01/S02 | 从完整 Phase-2 case root 一次性生成 OpenAPI + migration + shared types + api client + failing test pack + bootstrap 质量报告 |
| `run_phase3_first_version.py` | S01/S02/S03-start | 默认输出 `backend-first mainline` 的 Phase-3 foundation package first version；当前 runner 顶层已主要保留 parser、参数校验与 thin orchestration，bootstrap kernel 已下沉到 `scripts/phase3/foundation_bootstrap.py`，foundation mainline kernel 已下沉到 `scripts/phase3/foundation_mainline.py`；只有显式启用 flag 时才带上 `ui-fallback` / `dispatch` 这类 optional lane；该输出只能进入 `foundation-ready`，不能直接宣称 P3 完成 |

---

## 八、追踪链设计

### 8.1 P2 → P3 追踪链

P3 追踪链必须从 `wff-base-traceability-management` 的 Phase-2 registry 继承。`phase-3-trace-registry*.json` 只表达 P3 合约/测试/实现绑定状态，不重新分配或替代 P1/P2 identity。若 `.trace/trace.db` 缺失、路径陈旧、无法解析 source binding，必须先进入 review-bound，而不是用 markdown 猜测静默补齐。

```
P2 Trace ID                    P3 Binding Target
─────────────────────────────────────────────────
P2-DTR-01 (decision)     →     openapi.yaml + tech-stack-decision.yaml
P2-CTR-01 (contract)     →     openapi.yaml endpoint definition
P2-SCN-01 (scenario)     →     tests/scenarios/scn-01.scenario.test.ts
P2-RP-01  (replay)       →     tests/replays/rp-01.replay.test.ts
P2-DTR-xx (table design) →     db/migrations/001_initial_schema.sql
```

### 8.2 P3 内部追踪

P3 内部追踪只允许追加实现/测试证据，不允许重启 trace 命名体系。行为卡、测试、实现文件中的 trace 字段应能回到 Phase-2 Trace Skill registry 或明确的 review-bound 原因。

每个实现文件的模块头注释包含：

```typescript
/**
 * @module ScopeController
 * @traces P2-CTR-scope-boundary, P2-DTR-03
 * @wp WP-02
 * @tests tests/contracts/create-tracked-scope.contract.test.ts
 */
```

---

## 九、执行路线图

### 9.1 Skill 开发优先级

| 优先级 | Skill | 预计工时 | 理由 |
|---|---|---|---|
| **P0** | wff-impl | 4d | 入口 + S01/S02 执行 |
| **P0** | wff-impl-verification | 3d | S02 依赖它定义测试框架 |
| **P0** | wff-impl-backend | 4d | S03 核心 |
| **P1** | wff-impl-frontend (HTML2Code) | 3d | S03 前端路径 B |
| **P1** | wff-impl-review | 2d | S04 核心 |
| **P1** | wff-impl-security | 2d | S04 核心 |
| **P2** | wff-impl-api-docs | 1.5d | S04 辅助 |
| **P3** | wff-impl-frontend (Figma2HTML) | 3d | 增强路径 A |
| **P3** | phase3-mobile-* | 5d+ | 可选 |

### 9.2 首轮验证计划

使用 GEO WP-01 (Auth/Tenant) 走完 S01 → S02 → S03 → S04：

1. **S01**: 从 GEO ESP 提取 Auth 相关的 3 个 endpoint → 生成局部 OpenAPI spec + migration
2. **S02**: 为 3 个 endpoint 写 contract tests + 1 个 denial replay test
3. **S03**: 实现 Auth module，让测试变绿
4. **S04**: Code Review + Security Audit (重点: tenant isolation)

这验证了"Contract → Test → Code"序在真实案例中的可行性。

---

## 十、与 v0.1 版本的核心差异

| 维度 | v0.1 初版（已废弃） | v0.1 修订版（本文档） |
|---|---|---|
| **核心序** | 选型 → 实现 → 测试 → 审查 | **接口冻结 → 测试定义 → 实现 → 审查** |
| **测试定位** | S03 的质量加固活动 | **S02 的核心产出物** |
| **实现完成标准** | "代码写完了" | **"测试通过了"** |
| **Code Review 时机** | S03 并行 | **S04 终态审计** |
| **OpenAPI spec** | S04 事后生成 | **S01 作为合约源冻结** |
| **S02 的产出** | （不存在） | **全部测试文件（编译通过、全部 FAIL）** |
| **设计-实现漂移防护** | 事后 diff | **合约测试持续阻断** |

---

## 十一、一句话结论

> Phase-3 的核心纪律是 **"Code follows tests, tests follow contracts, contracts follow design"** — 每一层的正确性由上一层的冻结决策保证，实现的完成标准是测试通过而不是代码写完。

## P3 Test Quality Evidence Layers

P3 release-facing behavior must not collapse test execution into test quality.

Use three separate evidence layers:

1. `script pass`: deterministic tooling completed, reports exist, and artifact generation did not fail.
2. `runtime pass`: selected API, DB, scenario, and replay suites passed on the intended runtime path.
3. `code-level test quality pass`: human/agentic review confirms generated tests assert meaningful business, contract, persistence, failure, replay, or scenario semantics.

Workflow owns the first two layers through repeatable execution, reporting, and scan signals.
Agentic review owns the third layer by judging whether the assertions would catch real delivery risk.

Redlines:

- fake-green assertions are blockers
- runtime/toolkit self-checks cannot be main proof
- invocation-only tests cannot support delivery quality
- shape-only checks cannot substitute for business fields, error semantics, or persistence evidence on core paths

Allowed weak assertions are helper guards only when paired with stronger semantic assertions.
Backend/API/DB evidence must not be described as frontend E2E or full production readiness unless those lanes were explicitly executed and reviewed.

