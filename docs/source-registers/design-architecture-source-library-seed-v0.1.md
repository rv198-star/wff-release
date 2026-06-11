# 设计 / 架构阶段素材库启动建议（v0.1）

## 文档目的

这份文档用于回答：

- 当前第二阶段最缺的到底是什么
- 应该先补模板，还是先补素材库
- 如果先补素材库，第一批最值得纳入哪些参考源

---

## 一、当前判断

当前第二阶段的主要缺口**不是模板数量**，而是：

> 缺少一套像 Phase-1 那样可被引用、可被筛选、可被吸收的设计 / 架构阶段素材库与索引层。

现状是：

- 设计 / 架构阶段已有 `v0` 包草案
- handoff / contract / template 思维已经较强
- 但仍缺少可系统支撑 Stage-2 的参考源入口与抽取资产

补充更新：

- 当前仓库已经不再停留在“只有 starter 想法”的状态
- `docs/source-registers/design-architecture-stage-source-unit-coverage-ledger-v0.1.md` 已提供单元级 ledger
- `docs/phases/phase-2/design-architecture-case-backed-absorption-matrix-v0.1.md` 已提供 case-backed absorption 视角
- 现在的主要缺口，已经从“有没有 starter library”转为“有没有更多真实案例反复压实这些 source units”

因此当前更合理的优先级是：

1. 先建立一个**小而硬**的 starter source library
2. 再决定是否继续扩充 SOA / DDD / BPMN / TOGAF 等方法资产

---

## 二、第一批推荐 starter set

### 1. DDD Strategic Reference

优先建议：
- Eric Evans `Domain-Driven Design Reference`

主要用途：
- 系统边界
- bounded context
- context mapping
- 模块 / 领域 / 服务边界讨论

采用原则：
- 优先吸收 strategic patterns
- tactical patterns 不应直接绑定为本项目默认实现结构

### 2. Quality Attribute / Quality Scenario Reference

优先建议：
- arc42 quality scenarios 相关资料
- ISO/IEC 25010 质量模型概览

主要用途：
- 把 NFR 从泛化“约束”提升为更明确的质量属性表达
- 为第二阶段的设计决策提供质量权衡语言
- 为 design handoff 提供更可消费的质量说明

### 3. Service Boundary / Domain Analysis Reference

优先建议：
- 现代 domain analysis / tactical DDD 类实践参考

主要用途：
- 服务候选
- 模块依赖
- 能力边界
- 领域拆分

说明：
- 这里的目标不是直接拥抱微服务
- 而是借其边界分析方法帮助 Stage-2 做更稳的 decomposition

### 4. Lightweight Interface Design Reference

优先建议：
- 一份轻量 API / interface design best-practice 参考

主要用途：
- 接口契约
- versioning / error model / pagination / resource boundary
- 把接口设计从“有字段说明”提升到“有一致契约思维”

---

## 三、当前不建议一开始重投入的方向

### 1. TOGAF 作为主骨架

当前不建议把 TOGAF 四层直接改写成 Stage-2 的主阶段结构。

更合适的定位是：

> TOGAF `business / application / data / technology` 作为 review lens / completeness lens 使用。

### 2. 大规模 SOA 企业治理素材

当前不建议一开始引入大量偏企业治理、偏大组织框架化的 SOA 资料。

原因：
- 容易让 Stage-2 过早企业架构化
- 会把阶段骨架拉向框架 adoption，而不是交付导向设计
- 当前更需要的是边界拆分与服务候选分析，不是完整 SOA 治理体系

### 3. 过大而过重的 architecture bookshelf

当前不建议一开始把第二阶段扩成一个大而全架构书单项目。

更合理的做法是：
- 先纳入 3~4 个高价值核心源
- 再按 Stage-2 authoring 真实缺口定向补充

---

## 四、建议的后续动作

1. 建立 `design-architecture-source-index` 草案
2. 持续扩充 `source-unit coverage ledger`
3. 把 case-backed absorption matrix 跟随真实案例一起更新
4. 明确每个 source 支撑 Stage-2 哪个子阶段
5. 再决定 BPMN / SOMA / TOGAF / SOA 的具体挂接点

---

## 五、一句话结论

第二阶段已经补上了 starter source library 的台账骨架；当前最值得继续补的，是把这些 source units 用更多真实案例反复跑实。

建议先从：
- DDD strategic reference
- quality scenario / quality model
- service-boundary/domain-analysis reference
- lightweight interface design reference

这四类开始。
