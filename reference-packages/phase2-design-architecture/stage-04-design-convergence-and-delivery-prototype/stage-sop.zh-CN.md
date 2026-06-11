# Stage-04 操作说明（审计镜像）— design-convergence-and-delivery-prototype

## 1. 这个文件是做什么的
- 这是 Stage-04 英文 SOP 的中文审计镜像。
- 它解释这个阶段如何把 Stage-01~03 聚合、校对、收敛并形成最终 handoff。

## 2. 流程主线
- 先聚合前序阶段结果。
- 先确认所有已知业务场景都有 coverage，再为关键 public-boundary 场景补详细时序。
- 技术选型矩阵与外部证据引用要一并带入收敛，不允许在 Stage-04 丢失。
- 主导瓶颈、主流基线不足说明、最优候选判断也必须带入收敛，不允许被压缩成一句推荐结论。
- 先识别冲突与未解决项，再做收敛摘要。
- 生命周期 ownership、命令边界和 public-name closure 的结构矛盾必须显式出现在收敛层，且会直接影响 readiness 定级。
- handoff 前要补出粗粒度 implementation task sketch，但不能越界冻结内部类 / 方法 / 文件。
- 不能把 unresolved risks 擦掉来换取“看起来完成”。
- 只有 handoff package 和 downstream usage rule 明确时，才允许 gate-pass。

## 3. 方法资产角色
- synthesis references 负责一致性与收敛逻辑。
- diagram expression 负责收敛视图表达。
- sequence reasoning 负责关键 public-boundary 场景的时序表达。
- optimality reasoning 负责 acceptable vs optimal 的最终审查。

## 4. 边界提醒
- 本文件不是边界合同，边界合同看 `skill-contract.md`。
- 本文件也不是最终交付版式，交付版式看 `output-template.md`。
- 详细时序图不是全场景强制项，内部类名 / 方法名也不是。
- readiness 措辞不能超过 package 自己的 verification / confidence / realizability 证据强度。
