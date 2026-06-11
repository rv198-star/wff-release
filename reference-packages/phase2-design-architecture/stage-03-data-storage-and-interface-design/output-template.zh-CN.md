# Stage-03 输出模板（审计镜像）— data-storage-and-interface-design

## 1. 这个文件是做什么的
- 这是 Stage-03 英文输出模板的中文审计镜像。
- 它帮助评审者理解：这个阶段的交付物如何表达数据归属、存储、接口与交互设计。

## 2. 最关键字段
- 数据模型摘要
- 数据归属图
- 存储策略
- schema 草案
- 接口契约集
- API 端点草案
- lifecycle / command consistency checks
- public-boundary registry closure
- 交互流程
- 场景覆盖矩阵
- 安全架构提纲
- 关键外部依赖 realizability
- substitute-boundary plan
- 技术栈与部署假设
- 技术选型评估矩阵
- 主导瓶颈假设
- 架构候选替代集
- 主流基线不足说明
- 约束主导的最优候选
- 容量与性能假设
- 关键设计权衡
- `downstream_assumption_contract`
- `artifact_id / depends_on / feeds / source_path / source_anchor`
- `source / confidence_profile / verification`
- `upstream_declaration_states`
- `nfr_and_quality_state`
- `boundary_visibility_scope`
- `deferred_private_implementation_notes`

## 3. 图示要求
- Stage-03 强制要求数据结构图、接口/交互流图，并显式表达信任边界或部署锚点。
- 至少应表达 ownership boundaries、critical entities、interaction paths、failure hints、trust/deployment hints。
- 生命周期、写权限和命令边界必须自洽，不能让只读下游消费者回写上游 truth，也不能让两个 endpoint 争夺同一个权威动作。
- 所有已知业务场景都应被 coverage matrix 覆盖，但只需对关键 public-boundary 场景画详细时序。
- 技术选型若依赖版本、LTS、license、安全公告、性能基准等可变事实，必须外部核实，不能只靠模型记忆。
- 关键外部依赖若不是 `confirmed`，必须显式说明替代边界、契约差异、以及 readiness 影响。
- 若主导约束很强，不能停在“主流可行”方案，必须显式评估更强候选并说明主流基线为何不足。

## 4. 交接要求
- 最终交给 Stage-04。
- handoff package 至少要包含：数据模型摘要、数据归属图、存储策略、schema 草案、契约集、API 端点草案、lifecycle / command consistency checks、public-boundary registry closure、交互流、场景覆盖矩阵、安全提纲、关键依赖 realizability、substitute-boundary plan、技术栈/部署假设、技术选型评估矩阵、主导瓶颈假设、架构候选替代集、主流基线不足说明、约束主导的最优候选、容量/性能假设、downstream may-assume / must-not-assume、未解决项。
