# Stage-04 输出模板（审计镜像）— design-convergence-and-delivery-prototype

## 1. 这个文件是做什么的
- 这是 Stage-04 英文输出模板的中文审计镜像。
- 它帮助评审者理解：最终二阶段交付包应如何表达收敛结果、风险和下游消费规则。

## 2. 最关键字段
- 架构收敛摘要
- 交付原型或等价结构表达
- 关键交互时序集
- 最优性审查
- 设计验证说明
- 未解决风险与 review-bound 项
- implementation-facing handoff package
- implementation task sketch（仅粗粒度）
- structural consistency gate
- readiness claim calibration
- `artifact_id / depends_on / feeds / source_path / source_anchor`
- `source / confidence_profile / verification`
- `upstream_declaration_states`
- `nfr_and_quality_state`
- `boundary_visibility_scope`
- `deferred_private_implementation_notes`

## 3. 图示要求
- Stage-04 强制要求收敛视图或关键流程视图。
- 至少应表达：key boundary slices、critical interactions、critical public-boundary sequence steps、high-risk unresolved areas。
- 收敛包应显式回答 chosen architecture 为什么优于主流基线，而不是只给推荐结论。
- 若生命周期 ownership、命令边界或 public-name closure 仍有结构矛盾，必须显式降级 readiness，不能继续写成 ready-to-implement。

## 4. 交接要求
- 最终交给 `implementation-phase`。
- downstream usage rule 必须明确说明 provisional / review-bound 内容如何被消费。
- implementation task sketch 只能到 slice / module / work-package 级，不能下沉到类 / 方法 / 文件 / ticket 级。
- 所有已知业务场景应有 coverage 依据，但详细时序只要求关键 public-boundary 场景。
- 关键技术选型应保留评估矩阵与外部证据引用，不能在收敛阶段变成“无来源结论”。
- readiness 结论必须和 verification / confidence / realizability 证据一致，不能过度宣称。
