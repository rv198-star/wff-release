# 第二阶段核心业务产物清单（v0.1）

## 目的

这份清单用于作为第二阶段（设计 / 架构）的统一业务产物基准。

它服务两个目标：

1. 作为 Phase-2 Skills 说明层的基准，回答“第二阶段走完到底应该产出什么”。
2. 作为各 Stage Skill 输出层的挂靠清单，回答“当前阶段产出覆盖了哪些核心业务产物”。

---

## 1. 使用原则

这份清单不是要求单个 Stage 一次产出全部内容。

而是：

- Phase-2 四个子阶段共同覆盖这份清单
- 每个 Stage 对其中一部分承担主责任
- Phase-2 默认只冻结 public boundary 可见的名字、契约和交互，不冻结 private implementation 的类名 / 方法名 / 文件结构，除非明确作为附录要求
- 技术选型若依赖版本、LTS、license、安全公告、benchmark 等可变事实，必须由外部证据支撑，不能只靠模型记忆
- 当主导约束非常强时，不能停在“主流可行”的安全基线，必须显式比较足够强的替代候选，并说明为何主流基线不足
- 审计时应能回答：
  - 哪些产物已形成
  - 哪些产物仍是 `draft / provisional`
  - 哪些产物尚未进入当前阶段

---

## 2. Phase-2 核心业务产物总表

### A. 架构边界与方向类

#### 1. 系统边界说明（System Boundary Statement）
- 说明：明确系统内、相邻系统、明确不在当前范围内的部分
- 主责任阶段：Stage-01

#### 2. 约束态势（Constraint Posture）
- 说明：继承约束、推演约束、未知约束、延后约束的结构化表达
- 主责任阶段：Stage-01

#### 3. 质量属性 / NFR 吸纳结构（Quality Attribute / NFR Absorption Structure）
- 说明：把上游 NFR 状态转成架构可消费的质量视角
- 主责任阶段：Stage-01

#### 4. 能力地图（Capability Map）
- 说明：后续分解前的能力结构基准
- 主责任阶段：Stage-01

#### 5. 架构方向（Architecture Direction）
- 说明：当前接受的总体架构走向
- 主责任阶段：Stage-01

#### 6. 关键架构决策（Key Architecture Decisions）
- 说明：影响后续分解与设计的重要决策及理由
- 主责任阶段：Stage-01

#### 6A. 安全架构草图（Security Architecture Sketch）
- 说明：在边界定义阶段先明确 trust boundary、认证授权姿态、敏感操作/数据边、审计敏感边
- 主责任阶段：Stage-01

#### 6B. 容量估算（Capacity Estimation）
- 说明：在边界定义阶段给出数量级吞吐/峰值/增长/新鲜度假设，避免下游在真空中继续设计
- 主责任阶段：Stage-01

---

### B. 领域 / 模块 / 服务分解类

#### 7. 领域边界图（Domain Map）
- 说明：主要领域边界与职责分区
- 主责任阶段：Stage-02

#### 8. 模块结构图（Module Map）
- 说明：模块划分及其关系
- 主责任阶段：Stage-02

#### 9. 服务候选集合（Service Candidates）
- 说明：候选服务及其边界角色
- 主责任阶段：Stage-02

#### 10. 责任矩阵（Responsibility Matrix）
- 说明：谁负责什么、哪里不能重叠
- 主责任阶段：Stage-02

#### 11. 依赖 / 协作关系图（Dependency / Collaboration Map）
- 说明：分解后各部分如何协作、依赖朝向如何
- 主责任阶段：Stage-02

#### 12. 分解决策说明（Decomposition Decisions）
- 说明：为何这样拆，不这样拆
- 主责任阶段：Stage-02

#### 13. 概念实体关系图（Entity Relationship Diagram, Conceptual）
- 说明：关键业务对象 / 聚合的关系、邻接和生命周期连接点
- 主责任阶段：Stage-02

#### 14. 领域事件目录（Domain Event Catalog）
- 说明：重要状态变化对应的领域事件、触发条件、主要生产者 / 消费者
- 主责任阶段：Stage-02

G.09 事件模型直驱规则：

- Domain event catalog is not checklist-only.
- 它是 `p2-architecture-event-model-driver.v1` 的 persisted/handoff-facing expression。
- 事件内容必须由 P2 Agentic architecture/event-model judgment 形成；schema、validator、清单字段只能证明结构和追溯，不能生成事件答案。
- 每个 event model 至少表达：
  - `event_name`
  - `domain_subject`
  - `operation_or_state_change`
  - `producer`
  - `consumer`
  - `trigger`
  - `payload_shape`
  - `timing`
  - `idempotency_rule`
  - `ordering_or_consistency_note`
  - `source_or_decision_refs`
  - `review_bound_gap`
- 如果 P2 无法解析事件模型，必须把缺口记录为 `review_bound_event_gaps`，并说明 owner、validation path、downstream usage rule。

---

### C. 数据 / 存储 / 接口设计类

#### 15. 数据模型摘要（Data Model Summary）
- 说明：关键数据实体与结构关系
- 主责任阶段：Stage-03

#### 16. 数据归属图（Data Ownership Map）
- 说明：哪些服务 / 模块拥有哪些数据与状态
- 主责任阶段：Stage-03

#### 17. 存储策略（Storage Strategy）
- 说明：存储方式、约束、权衡
- 主责任阶段：Stage-03

#### 18. Schema 草案（Schema Draft）
- 说明：表 / 集合 / 索引方向、关键字段、主外键或等价关系的初版结构
- 主责任阶段：Stage-03

#### 19. 接口契约集（Interface Contracts）
- 说明：输入输出边界、兼容性、错误行为
- 主责任阶段：Stage-03

#### 20. API 端点草案（API Endpoint Draft）
- 说明：端点 / 操作名、调用方式、request/response shape、失败语义
- 主责任阶段：Stage-03

#### 21. 交互流程（Interaction Flow）
- 说明：跨边界调用与数据流动路径
- 主责任阶段：Stage-03

#### 22. 安全架构提纲（Security Architecture Outline）
- 说明：trust boundary、认证授权姿态、审计记录、敏感数据处理的初版设计
- 主责任阶段：Stage-03

#### 23. 技术栈与部署假设（Technology Stack and Deployment Assumptions）
- 说明：运行时、持久层、集成风格、部署拓扑的初步假设
- 主责任阶段：Stage-03

#### 24. 技术选型评估矩阵（Technology Selection Evaluation Matrix）
- 说明：对关键技术方案进行多维比较，并记录证据来源、最终选择与淘汰理由
- 主责任阶段：Stage-03

#### 25. 主导瓶颈假设（Dominant Bottleneck Hypothesis）
- 说明：识别真正支配架构选型的主导约束或瓶颈，而不是把所有维度平均化处理
- 主责任阶段：Stage-03

#### 26. 架构候选替代集（Architecture Alternative Candidate Set）
- 说明：显式比较具备实质差异的候选路径，至少包括主流基线与更强约束导向候选
- 主责任阶段：Stage-03

#### 27. 主流基线不足说明（Baseline Insufficiency Note）
- 说明：当主流方案不够时，明确说明它在哪些约束下失效、退化或风险不可接受
- 主责任阶段：Stage-03

#### 28. 约束主导的最优候选（Constraint-Dominant Optimum Candidate）
- 说明：在当前已知约束下更优的候选方案，以及为此接受的代价和复杂度
- 主责任阶段：Stage-03

#### 29. 容量与性能假设（Capacity and Performance Assumptions）
- 说明：吞吐、延迟、增长、重试 / 背压等量化或半量化假设
- 主责任阶段：Stage-03

#### 30. 场景覆盖矩阵（Scenario Coverage Matrix）
- 说明：对所有已知业务场景进行实体、模块、public service、契约、失败语义的覆盖检查
- 主责任阶段：Stage-03

#### 31. 关键设计权衡（Key Tradeoff Decisions）
- 说明：数据/接口/存储层面的核心取舍
- 主责任阶段：Stage-03

---

### D. 收敛 / 交付衔接类

#### 32. 架构收敛摘要（Architecture Convergence Summary）
- 说明：Stage-01~03 如何在最终包里收口
- 主责任阶段：Stage-04

#### 33. 交付原型或等价结构表达（Prototype or Structured Delivery Expression）
- 说明：帮助下游开发理解设计的结构化交付表达
- 主责任阶段：Stage-04

#### 34. 关键交互时序集（Critical Interaction Sequence Set）
- 说明：只对关键 public-boundary 场景绘制的实体/服务/应用间时序表达
- 主责任阶段：Stage-04

#### 35. 最优性审查（Optimality Review）
- 说明：显式说明最终方案是“仅达到可接受”还是“已逼近主导约束下的更优解”，以及理由
- 主责任阶段：Stage-04

#### 36. 设计验证说明（Design Verification Notes）
- 说明：当前设计准备度与剩余限制
- 主责任阶段：Stage-04

#### 37. 未解决风险清单（Unresolved Risks and Review-Bound Items）
- 说明：不能被伪装成“已解决”的设计风险与不确定项
- 主责任阶段：Stage-04

#### 38. 面向实现阶段的 handoff 包（Implementation-Facing Handoff Package）
- 说明：交给开发 / 实现阶段的最终二阶段产物集合
- 主责任阶段：Stage-04

#### 39. 实现任务草图（Implementation Task Sketch）
- 说明：仅到 slice / module / work-package 粒度的实现切片与先后关系草图，不冻结 private implementation 细节
- 主责任阶段：Stage-04

---

## 3. 审计时的最小判断方式

对每个产物项，审计时至少判断：

- `missing`
- `draft`
- `provisional`
- `approved`
- `not-in-stage`

---

## 4. 当前结论

第二阶段的核心业务产物，不应只通过四个 Stage 的零散文档去隐式推断。

应统一以本清单为基准：

- 说明层引用它
- 输出层挂靠它
- 审计层检查它
