# Phase-3 可运行交付纠偏方案 v0.1

English version: [phase-3-runnable-delivery-correction-v0.1.md](phase-3-runnable-delivery-correction-v0.1.md)

> 状态：当前生效的纠偏说明
> 适用场景：切换到具备运行环境的服务器后继续推进 Phase-3
> 目标：把 Phase-3 从“脚手架有效”纠正为“真实可运行交付”

## 1. 为什么要有这份文档

`r15` clean 端到端审计暴露了一个明确问题：

- 当前 Phase-3 流程可以产出质量很高的 contract-first scaffold
- 这套 scaffold 也可以通过大量结构性和契约性验证
- 但生成出来的后端，仍可能停留在运行时模拟内核，而不是真正可运行的业务应用

这个偏差在后续 Phase-3 里不能再被接受。

这份文档就是下一轮服务器侧继续开发前的纠偏基线。

## 2. 纠偏目标

后续 Phase-3 的目标必须是 **可运行交付包**，而不是仅仅契约合规的骨架。

这条要求应当按 packet / lane 粒度判断它所需的运行环境是否具备。
对于 server / web lane，默认运行验证环境是 Docker。
对于 iOS、Android、Flutter、Electron 等非 Docker 项目，必须先明确一个等价的 runtime-validation environment，相关 lane 才能宣称进入真正的可运行完成态。

在具备服务器环境的情况下，Phase-3 产出物应当把下面这些能力当成一等目标：

- 依赖 bootstrap
- `pnpm build`
- `pnpm start` 或等价运行命令
- 数据库 migration 执行
- 容器镜像构建
- 通过 `docker compose up` 拉起依赖与应用
- 基础运行态 smoke evidence，例如 health check
- 宿主端口绑定必须显式且可配置，不能静默假设 `5432`、`6379`、`3000` 这类默认端口一定空闲
- 如果 Phase-2 没有提供人工精调后的界面原型输入稿，P3 进入实现前必须先自动生成一版 fallback UI 原型作为缺省输入，而不是直接跳过 UI 输入层
- 如果界面原型输入和前端技术选型都缺失，P3 应启用默认可交付前端栈（`React + Vite + Ant Design + React Router + TanStack Query + React Hook Form + Zod`），保证实现可以继续推进到可操作 MVP

对于 backend / server lane，还必须明确满足下面这组最低可运行验证标准：

- 后端 contract / interface 验证必须打到真实启动后的 HTTP 服务，而不是只通过内存 helper 或 generated runtime shim
- 验证请求可以使用 `curl`、`fetch`、`supertest` 或等价 HTTP client，但必须穿过真实 request/response 边界
- 如果后端依赖 PostgreSQL 或其他数据库，运行中必须包含真实 migration 执行，以及基于真实 SQL 的持久化验证，而不能只停留在 schema 形状断言
- repository / data-access 证明必须包含真实数据库引擎上的写入 / 读取或状态迁移证据，而不是只验证 runtime-test-kit 之类的合成记录
- 后端服务边界测试与 SQL / 持久化测试都必须能追溯回 Phase-1 / Phase-2 的用户流程、接口契约、失败路径与状态迁移，而不是变成与产品语义脱节的技术性检查

## 3. 分阶段纠偏方向

### 3.1 S01 不能只出抽象脚手架，而要出真实运行基线

S01 仍然要坚持先冻结契约，但不能只停留在“结构长得像项目”。

生成出来的 workspace 至少要具备一套真实运行基线：

- 后端 HTTP 入口
- 来自 `tech-stack-decision.yaml` 的真实框架 / 运行时依赖
- `dev` / `build` / `start` / migration 等 package scripts
- 与所选数据库层对应的真实持久化接线
- `.env.example` 与环境变量契约
- 真正启动应用的 `Dockerfile`，而不是只做 `build`
- `docker-compose.dev.yml` 与 `docker-compose.prod.yml`
- compose 资产中的宿主端口绑定必须可配置，避免本地运行验证时默认撞到已有服务
- health/readiness endpoint 或等价启动探针
- UI 原型输入解析与兜底：
  - 若 Phase-2 已提供人工原型输入，直接沿用
  - 若缺失，则在 S01 生成 fallback 原型输入包（至少包含 `ui-prototype-fallback.md`、`ui-wireframes.html`、`ui-api-mapping.json`）
  - fallback 来源必须写入运行元数据，避免被误判为人工确认稿

### 3.2 S02 仍然测试先行，但要把运行态证据纳入视野

contract / scenario / replay / unit tests 仍然是最核心的证明面。

unit test coverage 可以作为次级质量信号，尤其适合约束那些与 Phase-2 功能切片对齐、且可环境隔离的 service/domain 模块；但它绝不能替代 migration 执行、SQL / 持久化真实性，或真实启动服务边界验证。

当 coverage 被采集到时，Phase-3 报告应直接公布 line / function / branch 等具体数字，而不是只折叠成一个泛化绿灯；如果本轮没有采集到 coverage，也必须在报告里显式标出这个缺口。

但在同一个 workspace 中，也应当把运行态证据纳入 Phase-3：

- install/bootstrap 检查
- migration smoke
- build smoke
- service startup smoke
- health endpoint probe
- container build smoke

这些证据不会替代 contract-first 验证。
它们补的是“接口形状正确”到“项目真的能跑起来”之间的那道断层。

同一轮运行中还应保留 `runtime-environment-ledger.json`，按 packet / lane 明确记录：

- 该 packet 需要哪种 runtime-validation environment
- 当前环境是否具备
- 缺失时会阻塞哪些能力
- 在没有运行环境时最多允许推进到什么程度

对于 server / backend packet，只要 Docker 或等价运行环境可用，就应把下面这些内容视为最低验证门槛：

- HTTP contract tests 必须命中真实启动后的服务端 endpoint
- service startup smoke 必须证明 API 进程能通过 HTTP 被访问
- migrations 必须在真实数据库引擎上执行
- 每个 backend work package family 至少要有一条真实持久化路径完成 SQL-backed 的写入 / 读取或状态迁移验证
- 若该 work package 依赖唯一约束、关联完整性或等价持久化不变量，则这些规则也必须被真实验证

后端验证顺序也应明确固定为：

1. 真实 migration 执行
2. 与 P1 / P2 用例状态模型对齐的 SQL / 持久化验证
3. 面向真实启动服务的 service-boundary contract / scenario 验证

这样可以保证 service 层测试不会把底层 repository / database 的问题掩盖掉。

对于 frontend/web lane，还应补充最低可运行验证语义：

1. 至少一条来自 P1/P2 用户流的端到端交互可操作（不仅是页面可访问）
2. 页面必须展示真实 API 数据路径的加载/错误/空态之一，不能只返回占位文案
3. 若 UI 输入来自 fallback 原型，报告必须显式标注其边界与待人工精调点

### 3.3 S03 必须把 generated runtime 从主路径上替换掉

`generated-runtime.ts`、`operation-support.ts`、passthrough delegates 之类的兼容层，在 bootstrap 阶段或过渡阶段可以暂时存在。

但它们不能继续作为一个完成态后端切片的主执行路径。

每个实现完成的 packet，目标终态应当是：

- controller 只负责 HTTP 映射
- service 承担 use-case 规则与状态迁移
- repository / adapter 承担真实持久化或外部 I/O
- 该切片的业务行为不再主要依赖 generated runtime 内核

### 3.4 S04 的 `delivery-ready` 必须意味着可部署，而不只是文档齐全

`delivery-ready` 应当意味着运行准备度成立，而不只是各种报告都生成了。

交付加固至少应覆盖：

- 与代码保持一致的 runtime startup commands
- 容器镜像构建命令
- 环境/bootstrap 说明
- migration 与 rollback 说明
- deploy runbook
- 来自真实环境的 runtime smoke evidence

## 4. 必须纠正的 Gate 语义

未来 Phase-3 的完成判定中，以下任一情况存在时，都不应判为 `delivery-ready`：

- 后端入口仍是占位实现
- 主要业务行为仍主要通过 generated runtime delegate 执行
- Docker 镜像定义只做构建，不负责启动服务
- 选定技术栈没有真实 persistence / migration 路径
- backend contract tests 只验证了内存 helper，而没有命中真实启动后的 HTTP 服务
- 数据库相关验证只检查 schema 形状或 generated records，而没有在选定数据库引擎上执行真实 SQL
- 测试变绿只验证了模拟运行态
- 没有任何 server/runtime smoke evidence
- 对缺失运行环境的 packet 没有显式记录 runtime-environment gap
- frontend 仅提供“可访问占位页”，但没有可操作用户流
- 缺少人工原型输入时也没有生成 fallback 原型输入包

## 5. 服务器侧推荐执行流

如果本机缺少稳定的 Node / Docker / 部署依赖环境，本机可以负责 foundation work；最终实现和运行证据，应转到服务器环境完成。

如果一个混合项目只为部分模块具备运行环境，那么 Phase-3 也应按 packet / lane 继续推进：

- 已具备运行环境的 lane 可以继续进入完整实现与 runtime validation 循环
- 缺失运行环境的 lane 仍可继续 contract/test/scaffold/static implementation
- 但这些缺环境 lane 不得宣称 verified / implementation-ready / delivery-ready

推荐流程：

1. 从已完成的 Phase-2 root 生成 Phase-3 workspace。
2. bootstrap workspace toolchain。
3. 执行 worker packets 或 dispatch loop。
4. 逐个把 generated-runtime-backed 切片替换成真实后端 / 前端实现。
5. 按 packet 粒度运行 targeted tests 和 unit tests。
6. 构建 runtime image，并验证容器启动。
7. 对已启动后端执行最小 authenticated started-service API smoke。
8. 基于得到的可运行包，再进入 Phase-4 验证。

示意命令：

```bash
python3 scripts/phase3/run_phase3_first_version.py --phase2-root <phase2-root> --output-dir <phase3-root> --mainline-verification-mode strict-runtime
python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-root> --install --strict
python3 scripts/phase3/phase3_dispatch_runner.py --output-dir <phase3-root> --mode execute-and-apply-gate --repeat-until-stalled
pnpm --dir <phase3-root> build
docker build -t <image-name> <phase3-root>
docker compose -f <phase3-root>/docker-compose.prod.yml up -d --build
python3 scripts/phase3/phase3_started_service_smoke.py --workspace-root <phase3-root> --service-url <started-service-url> --output <phase3-root>/started-service-smoke-report.json
```

具体运行命令可以随技术选型变化，但生成出来的交付包必须支持同一类能力。

## 6. 本机与服务器的职责边界

如果本机无法稳定运行 Node、容器或部署依赖：

- 本机工作可以停在 `foundation-ready` 或 packet 级局部验证
- 服务器环境应承担 `implementation-ready` 与 `delivery-ready` 的最终判断
- 缺失的 runtime environment 必须明确列出，不能只写成笼统的 follow-up

这样是可以接受的，前提是边界说清楚。
不能接受的是把仅有 scaffold 的输出，包装成最终可运行交付。

---

## 7. v1.2.3 可溯源业务行为卡

当高风险业务实现仍然偏薄时，仅仅可运行还不够。

在 v1.2.3 中，高风险 public operation 必须先产出行为卡，再进入测试和 service/repository 实现。

行为卡必须绑定：

- P1/P2 trace IDs
- P2 contract / flow / state source
- human-readable pseudocode
- error trigger table
- state and persistence effects
- test mapping
- implementation mapping
- review-bound items

该规则必须出现在 release-facing surface 中；不能只依赖 AGENTS.md。

Service code must implement behavior-card pseudocode steps, not merely satisfy response shape.
Review must classify missing implementation as a `P3 implementation gap`.
