# Phase-2 产出物评判标准 (v1.0)

> **创建日期**: 2026-03-29
> **适用范围**: Phase-2 设计/架构阶段的所有产出物 + 执行 SKILL 本身
> **目标**: 定义可量化、可验证的多维度评判标准，以 9.5/10 为卓越基准
> **上游依赖**:
> - `docs/phases/phase-2/stage-2-core-business-deliverables-checklist-v0.1.md` — 39 项核心业务产物定义
> - `docs/phases/phase-2/phase-2-execution-report-template.md` — 执行报告模板
> - `docs/phases/phase-2/engineering-spec-pack-v0.1.md` — ESP 最低内容要求
> - `docs/phases/phase-2/phase-2-realizability-architecture-review-rule-v0.1.md` — 可实现性审查规则
> - `docs/phases/phase-2/stage-2-runtime-hardening-targets-v0.1.md` — 运行时硬化目标

---

## 一、评判体系总览

### 1.1 六大评判维度

| 维度编号 | 维度名称 | 权重 | 评判对象 |
|---|---|---|---|
| **D1** | 架构完整性 | 20% | Stage-01 产出 |
| **D2** | 领域分解深度 | 15% | Stage-02 产出 |
| **D3** | 数据/接口/存储设计精度 | 20% | Stage-03 产出 |
| **D4** | 收敛与交付衔接 | 15% | Stage-04 + ESP + Phase-3 Entry |
| **D5** | 过程治理 | 15% | Execution Report + Traceability + Baseline Lock |
| **D6** | 图表与视觉表达 | 15% | 所有 Stage 的 Mermaid 图 |

### 1.2 分数等级定义

| 分数区间 | 等级 | 含义 |
|---|---|---|
| 9.5 - 10.0 | **卓越** | 可直接作为行业参考标杆，无实质性短板 |
| 8.5 - 9.4 | **优秀** | 结构完整且内容充实，有少量可改进空间 |
| 7.5 - 8.4 | **良好** | 框架合格但部分维度信息密度或精度不足 |
| 6.5 - 7.4 | **合格** | 基本结构存在但存在系统性弱点 |
| < 6.5 | **不合格** | 存在关键缺失或结构性缺陷 |

### 1.3 综合分计算

```
综合分 = Σ(维度分 × 维度权重)
```

9.5 分标准意味着：**没有任何维度低于 8.5**，且至少 3 个维度达到 9.5+。

---

## 二、D1 — 架构完整性 (20%)

### 2.1 子维度评分表

| 子维度编号 | 子维度 | 9.5 标准（必须全部满足） | 8.0 标准（至少满足） | 权重 |
|---|---|---|---|---|
| D1.1 | 系统边界定义 | C4 Context 图 + 表格化 in-scope / adjacent / out-of-scope + ≥3 adjacent system 说明 | flowchart + 表格 + 明确三区划分 | 15% |
| D1.2 | 约束态势结构 | ≥5 inherited + ≥3 inferred + ≥3 unknown（每项有解决计划和时间窗口） + ≥2 deferred | 4 类约束均有覆盖 | 12% |
| D1.3 | 质量属性/NFR 吸纳 | 每属性有 statement + architecture_implication + status + **量化目标**（P95 延迟、可用性 SLA 等） | 每属性有文字描述 + status | 12% |
| D1.4 | 安全架构草图 | trust boundary 图 + RBAC posture + sensitive data 分类 + audit edges + **认证流序列方向** + **密钥管理策略** | trust boundary + RBAC posture + sensitive data | 10% |
| D1.5 | 容量估算 | **具体数字**: TPS/QPS 目标值 + P95 延迟目标 + 存储增长预测(月/年) + 峰值倍数 + 并发估算 | 数量级描述 + 峰值模式 | 12% |
| D1.6 | 架构决策 | ≥7 项 AD + **标准 ADR 格式**（Status/Context/Decision/Consequences/Alternatives） | ≥5 项 + decision/rationale | 15% |
| D1.7 | 禁止假设注册 | 继承 Phase-1 全部 + 每项有 compliance_status + architecture_constraint_mapping + **验证证据引用** | 继承全部 + compliance_status | 10% |
| D1.8 | 能力地图 | Mermaid flowchart + **priority/maturity 标注** + rationale per group | Mermaid flowchart + rationale | 7% |
| D1.9 | 架构方向 | 选择 + ≥3 备选 + **结构化对比矩阵** + baseline insufficiency 说明 | 选择 + 理由 | 7% |

### 2.2 D1 维度分计算

```
D1 分 = Σ(D1.x 分 × D1.x 权重)
```

### 2.3 9.5 分硬性门禁（D1）

以下任一不满足，D1 最高只能得 8.5：
- [ ] C4 Context 图存在（不可用 flowchart 替代）
- [ ] 容量估算含至少 3 个具体数字（TPS、延迟目标、存储增长任选三）
- [ ] 架构决策 ≥7 项且含 ADR 表格
- [ ] 禁止假设继承 Phase-1 全部（不可遗漏）

---

## 三、D2 — 领域分解深度 (15%)

### 3.1 子维度评分表

| 子维度编号 | 子维度 | 9.5 标准 | 8.0 标准 | 权重 |
|---|---|---|---|---|
| D2.1 | 领域边界图 | ≥4 域 + **core/support/generic 分类标签** + owned objects + primary states + must_not_own | ≥4 域 + owned objects | 15% |
| D2.2 | 模块结构图 | 业务模块 + 支撑模块 + Mermaid 依赖图 + **每模块 responsibility matrix (owned / read-only / must-not-own)** | 模块 + 依赖图 | 12% |
| D2.3 | 服务候选 | ≥8 逻辑服务 + home_module + type + responsibility + **≥3 种服务类型分类** | ≥8 逻辑服务 + home_module | 12% |
| D2.4 | 聚合生命周期 | **≥3 个 Mermaid stateDiagram** + 每个有 ≥4 状态 + 转移触发条件 | 文字描述生命周期 | 15% |
| D2.5 | 领域事件目录 | ≥10 事件 + producer/consumer/trigger + **payload shape 描述** + **ordering/idempotency 语义** | ≥8 事件 + producer/consumer/trigger | 12% |
| D2.6 | 依赖方向无环 | 显式 anti_cycle_rules + Mermaid 单向流图 + **显式违反惩罚说明** | 单向图 + anti-cycle rules | 10% |
| D2.7 | 概念 ER | Mermaid erDiagram + ≥10 实体 + **关系基数标注** + **聚合根标识** | erDiagram + 核心实体 | 12% |
| D2.8 | 生命周期所有权闭合 | 所有聚合有闭合矩阵 + downstream read-only references + **冲突检测规则** | 所有权 + 下游规则 | 12% |

### 3.2 9.5 分硬性门禁（D2）

- [ ] ≥3 个 Mermaid stateDiagram 存在（不可仅用文字描述替代）
- [ ] 领域事件 ≥10 个
- [ ] erDiagram 含聚合根标识
- [ ] 所有域有 core/support/generic 分类

---

## 四、D3 — 数据/接口/存储设计精度 (20%)

### 4.1 子维度评分表

| 子维度编号 | 子维度 | 9.5 标准 | 8.0 标准 | 权重 |
|---|---|---|---|---|
| D3.1 | Schema 草案 | 所有核心聚合表 + **每表 ≥5 key columns** + **字段数据类型** (varchar/int/jsonb/timestamp) + PK/FK + **NOT NULL/UNIQUE 约束** + **索引方向假设** | key columns + PK/FK + ownership notes | 15% |
| D3.2 | 数据归属图 | 完整 ownership matrix + authoritative write / read-only / public contract + **变更传播路径** | ownership matrix | 8% |
| D3.3 | 存储策略 | ≥3 存储层分类 + why + **容量估算** (初始/1年/3年) + **分区策略** + **归档/清理规则** | 分类 + why | 8% |
| D3.3B | 索引优化策略 | ≥5 条 **access pattern -> index** 映射，覆盖热点过滤 / 排序 / join 路径，并含 write-cost note + validation hook | 仅在 schema 字段里出现 index_hint | 5% |
| D3.3A | 数据敏感度与合规标注 | 每张 schema 表都有 **PII level / sensitive fields / masking-or-encryption / retention / audit access** 标注 | 关键表有 PII 标注 | 6% |
| D3.4 | 接口契约 | ≥10 契约 + producer/consumer + **JSON Schema / TypeScript interface 形式的 content shape** + failure semantics + compatibility rule + **canonical response/error contract** (`business_error | system_error`, retryability, caller action) | 契约 + content shape 文字描述 | 10% |
| D3.5 | API 端点草案 | ≥10 端点 + method/path + **JSON request body 示例** + **JSON response body 示例** + **≥3 failure semantics (4xx/5xx + 语义)** + **限流/分页策略** + **response_profile / retryability / idempotency** | 端点 + method + request/response 文字描述 | 15% |
| D3.6 | 交互流程 | ≥5 步完整流程 + producer/consumer + write boundary + failure hint + **回滚/补偿路径** | 流程 + write boundary | 5% |
| D3.7 | 安全架构提纲 | trust boundaries + authn/authz posture + **认证序列方向** + **token 策略** + audit hooks + sensitive data | trust boundaries + authn/authz posture | 5% |
| D3.8 | 技术选型矩阵 | ≥5 候选 × ≥10 维度 + **所有 evidence 含 URL + 验证日期** + final decision/rejection reason | ≥3 候选 × ≥10 维度 + evidence URLs | 8% |
| D3.9 | 主导瓶颈假设 | 显式识别 + why_this_dominates + **量化验证计划** (如何测量、阈值、spike 范围) | 显式识别 + why | 5% |
| D3.10 | 架构替代集 | ≥4 候选 + 含 mainstream baseline + **结构化对比表** (优/劣/代价/适用场景) | ≥4 候选 + posture 描述 | 5% |
| D3.11 | 场景覆盖 | ≥8 场景 + 含 ≥2 失败路径场景 + **批量操作** + **并发冲突** + **数据迁移** | ≥6 场景 | 8% |
| D3.12 | 公共边界注册闭合 | 所有 public name 有 status/origin/closure note + **namespace 约定** | 所有 public name 有 status | 3% |
| D3.13 | 关键设计权衡 | ≥5 项 TD + decision + rationale + **备选方案视角** + **可逆性评估** | ≥5 项 + decision + rationale | 5% |

### 4.2 9.5 分硬性门禁（D3）

- [ ] Schema 含字段数据类型和约束标注（不可只有列名）
- [ ] 索引策略不是只有 DDL 名称，还要能回溯到 access pattern / hotspot rationale
- [ ] 每张 schema 表都有数据敏感度 / 合规标注（不可只在正文散点提及）
- [ ] API 含 JSON request/response body 示例（不可仅文字描述）
- [ ] 存在统一 response/error contract，且明确区分 `business_error` / `system_error`
- [ ] implementation-facing endpoint 声明 response_profile / retryability / idempotency
- [ ] 技术选型 ≥5 候选
- [ ] 场景覆盖 ≥8 个（含失败路径）

---

## 五、D4 — 收敛与交付衔接 (15%)

### 5.1 子维度评分表

| 子维度编号 | 子维度 | 9.5 标准 | 8.0 标准 | 权重 |
|---|---|---|---|---|
| D4.1 | 架构收敛摘要 | **C4 Container 图** + convergence spine + consistency resolutions | flowchart + convergence spine | 12% |
| D4.2 | 交付原型/结构表达 | ≥3 Slice + workflow anchor + primary modules + completion signal + **每 slice 的验收标准** | ≥3 Slice + workflow | 10% |
| D4.3 | 关键交互时序 | **≥3 条 Mermaid sequenceDiagram** (happy path + clarification/retry + governance block) | ≥2 条 sequenceDiagram | 15% |
| D4.4 | 最优性审查 | bottleneck + alternatives + baseline insufficiency + chosen strength + **可接受 vs 最优的显式判定** + **与 Stage-03 不重复** | bottleneck 重申 + alternatives | 8% |
| D4.5 | 设计验证说明 | **结构化验证清单** (每项有 check_item / result [pass/fail/partial] / evidence / gap) | 观察性验证描述 | 8% |
| D4.6 | 未解决风险清单 | ≥5 项 RBI + class + current state + why not blocked + downstream rule + **risk level (H/M/L)** + **spike WP 绑定** + **responsible party** | ≥5 项 + class + current state | 10% |
| D4.7 | 结构一致性门禁 | lifecycle/command/naming 三项验证 + **结果为 none/具体矛盾列表** | 三项验证有结果 | 5% |
| D4.8 | 就绪度校准 | 诚实校准 + **禁止过度宣称 ready-to-implement** + 明确 review-bound-items 列表 | 诚实校准 | 5% |
| D4.9 | 可实现性审查 | 依赖分类 + structural consistency gate + substitute boundary + **delivery_path_realism 判定** | 依赖分类 + substitute boundary | 7% |
| D4.10 | 实现任务草图 | ≥4 WP + sequencing + dependency notes + **Mermaid gantt 图** + **spike binding (每个 RBI 绑定到 spike WP)** | ≥4 WP + sequencing | 12% |
| D4.11 | Engineering Spec Pack | **自包含**: 内联架构摘要 + schema 摘要 + API 摘要 + 决策列表 + 风险列表（下游不需翻阅 Stage 文档即可理解核心上下文） | 索引/路由式指向 Stage 文档 | 8% |
| D4.12 | 可观测性与运维就绪 | 至少覆盖 4 个关键 surface，且每行有 **logs / metrics / alerts / SLO / owner / rollout guardrail** | 有日志/指标提及 | 8% |

### 5.2 9.5 分硬性门禁（D4）

- [ ] ≥3 条 sequenceDiagram（含 governance block 路径）
- [ ] Mermaid gantt 图存在
- [ ] ESP 是自包含的（非纯索引文件）
- [ ] 每个 RBI 有 risk level + spike WP 绑定
- [ ] Stage-04 含结构化 observability / operational readiness 表

---

## 六、D5 — 过程治理 (15%)

### 6.1 子维度评分表

| 子维度编号 | 子维度 | 9.5 标准 | 8.0 标准 | 权重 |
|---|---|---|---|---|
| D5.1 | 可追溯性链 | 完整 artifact registry + validation pass + coarse link chain + **JSON + text 双格式报告** | registry + validation pass | 10% |
| D5.2 | 逐项判定矩阵 | **≥35 项交付物逐项判定** (verdict / evidence_reference / unresolved_truth / next_action) + **映射到 39 项 checklist** | ≥30 项判定 | 25% |
| D5.3 | 基线锁定 | **具体基线数值表**: 每 Stage 行数 + 决策数 + 图表数(按类型) + 事件数 + schema 表数 + API 端点数 + FA 数 + RBI 数 | 提及 baseline + lock note | 15% |
| D5.4 | 回归门禁 | **逐维度对比表** (≥10 维度) + 每维度有 baseline_value / rerun_value / delta / justification_if_negative | 整体 pass/fail 判定 | 15% |
| D5.5 | Review-Bound 比例 | **量化计算**: total_structured_items (具体数字) / review_bound_items (具体数字) / ratio (百分比) + ceiling 30% + verdict | 指向 source outputs | 15% |
| D5.6 | Stage 摘要 | 每 Stage 有 outcome + **具体的** strongest_output (引用具体内容) + **具体的** weakest_output (引用具体短板) + 专项 status + progression_judgment | outcome + 文件名引用 | 10% |
| D5.7 | 文档版本语义 | 每 Stage 有 version + status + **变更说明**(相比前版的 delta) | version + status | 5% |
| D5.8 | 警告与阻塞项 | 所有 pass-with-review-bound 和 partial 项 + why not fail + **downstream 依赖影响分析** + **补救路径** | 列出 + why not fail | 5% |

### 6.2 9.5 分硬性门禁（D5）

- [ ] 逐项判定矩阵 ≥35 项（不可只做 wrapper-level 7 行判定）
- [ ] 基线锁定含具体数值（不可只有程序化语句）
- [ ] Review-bound 比例有量化计算结果（不可为 `not-computed-by-wrapper`）
- [ ] 回归门禁有逐维度对比（不可只有整体 pass/fail）

---

## 七、D6 — 图表与视觉表达 (15%)

### 7.1 图表类型标准

| 图表类型 | 所属 Stage | 9.5 标准 Mermaid 语法 | 最低数量 | 权重 |
|---|---|---|---|---|
| D6.1 系统上下文图 | Stage-01 | `C4Context` (不可用 flowchart 替代) | 1 | 15% |
| D6.2 能力地图 | Stage-01 | `flowchart TD` + priority/maturity 标注 | 1 | 8% |
| D6.3 分解/依赖图 | Stage-02 | `flowchart LR` + 方向标注 | 1 | 10% |
| D6.4 概念 ER 图 | Stage-02 | `erDiagram` + 关系基数 + 聚合根标识 | 1 | 10% |
| D6.5 状态机图 | Stage-02/03 | `stateDiagram-v2` | **≥3** | 15% |
| D6.6 数据归属图 | Stage-03 | `flowchart LR` + subgraph + 所有权标注 | 1 | 8% |
| D6.7 部署假设图 | Stage-03 | `flowchart LR` + trust boundary 标注 | 1 | 5% |
| D6.8 收敛架构图 | Stage-04 | `C4Container` (不可用 flowchart 替代) | 1 | 10% |
| D6.9 交互时序图 | Stage-04 | `sequenceDiagram` | **≥3** | 12% |
| D6.10 实施时间线 | Stage-04 | `gantt` | 1 | 7% |

### 7.2 图表质量标准

每张 Mermaid 图必须满足：
- 节点标签有意义（不可用 A/B/C 替代）
- 关系/边有文字说明（不可只有箭头无标签）
- 图表大小适中（≥5 节点 且 ≤25 节点，过大应拆分）
- 渲染无语法错误（Mermaid 语法正确可渲染）

### 7.3 9.5 分硬性门禁（D6）

- [ ] C4Context 图存在（Stage-01 系统上下文）
- [ ] C4Container 图存在（Stage-04 收敛架构）
- [ ] stateDiagram ≥3 个
- [ ] sequenceDiagram ≥3 条
- [ ] gantt 图存在
- [ ] 所有图渲染无语法错误

---

## 八、SKILL 自身评判标准

除产出物维度外，SKILL 本身也需要评估：

### 8.1 SKILL 评判维度

| 子维度 | 9.5 标准 | 权重 |
|---|---|---|
| SK.1 入口清晰度 | When to Use / Do not use + Required Entry Assets + Required Entrypoint 均明确 | 10% |
| SK.2 执行序列定义 | 有明确的步骤序列 + runner 脚本 + 每步的输入/输出/门禁 | 10% |
| SK.3 产出物定义 | 列出所有必需产出物 + 每项有最低内容要求 | 10% |
| SK.4 **质量度量嵌入** | **每个 Stage 的最低量化指标**（行数/决策数/图表数/字段数/事件数/场景数） | 15% |
| SK.5 **语义质量检查** | Runner 不仅验证文件存在性，还能**解析 markdown 统计结构化内容的数量/比例**，并做 **ADR / endpoint / scenario 的确定性语义抽查** | 15% |
| SK.6 Rerun 约束力 | 显式的 baseline lock + regression gate + mandatory diff + review-bound ceiling | 10% |
| SK.7 图表类型标准 | 明确指定每种图用什么 Mermaid 语法（C4/stateDiagram/sequenceDiagram/gantt） | 10% |
| SK.8 ESP 内容要求 | ESP 自包含性的最低内容清单 | 10% |
| SK.9 跨 Stage 验证 | 定义 Stage 间术语/命名/决策一致性的交叉验证规则 | 10% |

---

## 九、评判流程

### 9.1 何时评判

| 触发时机 | 评判范围 |
|---|---|
| 单个 Stage 完成时 | 对应维度 (D1/D2/D3/D4) + D6 相关图表 |
| `run_phase2_full_trial.py` 执行后 | D5 (过程治理) + 全维度复核 |
| Rerun 完成时 | 全六维度 + vs-baseline 回归检查 |
| SKILL 修改后 | SK 维度 |

### 9.2 评判方法

1. **自动化检查** (runner 可执行):
   - 文件存在性验证
   - Markdown section 计数
   - Mermaid 图块计数与类型识别
   - 表格行数统计
   - Review-bound 比例计算
   - 确定性 semantic sampling（ADR / endpoint / scenario 各抽 1 个做深度校验）

2. **语义审查** (需要 LLM/人工):
   - 决策质量评估（是否有 context/consequences/alternatives）
   - 内容实质性判断（是否为填充式文字）
   - 跨 Stage 一致性验证
   - 可实现性审查

### 9.3 评判输出格式

```markdown
## Phase-2 Quality Scorecard

| 维度 | 子维度 | 分数 | 硬性门禁 | 证据 | 差距描述 |
|---|---|---|---|---|---|
| D1 架构完整性 | D1.1 系统边界 | X.X | ✓/✗ | 文件:行号 | ... |
| ... | ... | ... | ... | ... | ... |

### 硬性门禁总览
- D1 门禁: X/4 通过
- D2 门禁: X/4 通过
- ...

### 综合分: X.XX / 10
### 卓越标准达标: 是/否 (需 ≥9.5 且所有硬性门禁通过)
```

---

## 十、从 v4 到 9.5 的差距快照

基于当前 phase-2-v4 的评估，主要差距分布：

| 维度 | 当前分 | 未通过硬性门禁 | 关键差距 |
|---|---|---|---|
| D1 | 7.9 | C4 Context (✗), 容量具体数字 (✗), ADR 表格 (✗) | 3 个门禁未通过 |
| D2 | 8.2 | stateDiagram (✗), core/support 分类 (✗) | 2 个门禁未通过 |
| D3 | 7.9 | Schema 类型/约束 (✗), API JSON body (✗), ≥5 候选 (✗) | 3 个门禁未通过 |
| D4 | 8.0 | ≥3 序列图 (✗), gantt (✗), ESP 自包含 (✗), RBI spike binding (✗) | 4 个门禁未通过 |
| D5 | 7.0 | 逐项判定 ≥35 (✗), 基线数值 (✗), RB 比例量化 (✗), 逐维度回归 (✗) | **全部** 4 个门禁未通过 |
| D6 | 6.6 | C4Context (✗), C4Container (✗), stateDiagram ≥3 (✗), sequenceDiagram ≥3 (✗), gantt (✗) | 5/6 门禁未通过 |

**总计**: 21 个硬性门禁中只有 **0 个** 完全通过 → 系统性差距，需要 SKILL 层面的结构性改进。

---

## 十一、版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-03-29 | 初始版本，基于 phase-2-v4 评估和历史质量审计报告建立 |
