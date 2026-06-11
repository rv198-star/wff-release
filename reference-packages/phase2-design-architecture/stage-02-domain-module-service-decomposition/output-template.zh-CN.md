# Stage-02 输出模板（审计镜像）— domain-module-service-decomposition

## 1. 这个文件是做什么的
- 这是 Stage-02 英文输出模板的中文审计镜像。
- 它帮助评审者理解：分解产物需要交哪些字段，哪些地方要显式保留 unresolved / review-bound 内容。

## 2. 最关键字段
- 领域图
- 模块图
- 服务候选集合
- 责任矩阵
- 生命周期 ownership closure
- 依赖 / 协作图
- 概念实体关系图（Conceptual ER）
- 领域事件目录
- 分解决策
- `artifact_id / depends_on / feeds / source_path / source_anchor`
- `source / confidence_profile / verification`
- `upstream_declaration_states`
- `nfr_and_quality_state`
- `boundary_visibility_scope`
- `deferred_private_implementation_notes`

## 3. 图示要求
- Stage-02 强制要求结构图、依赖图，以及概念层的实体关系表达。
- 至少应表达：领域/模块/服务边界、ownership hints、dependency direction、核心对象关系线索。
- 只冻结模块间 / 应用间可见的边界信息，不冻结内部类名 / 方法名。
- 生命周期状态必须映射到声明的 owner writer，不能依赖下游只读消费者补闭环。

## 4. 交接要求
- 最终交给 Stage-03。
- handoff package 至少要包含：domain/module/service maps、责任矩阵、lifecycle ownership closure、dependency map、概念 ER、领域事件目录、分解决策、review-bound 项。
