# Stage-04 阶段契约（审计镜像）— design-convergence-and-delivery-prototype

## 1. 这个文件是做什么的
- 这是 Stage-04 英文主契约文件对应的中文审计镜像。
- 它帮助评审者理解：这个阶段如何把前 3 个阶段收口成面向实现的设计交付包。

## 2. 核心定义
- Stage-04 的目标不是直接生成开发任务，而是收敛设计并形成 implementation-facing handoff 与粗粒度 implementation task sketch。
- 必填输出至少包括：架构收敛摘要、交付原型/结构表达、关键交互时序集、最优性审查、设计验证说明、realizability / structural consistency / readiness calibration、未解决风险清单、handoff 包、粗粒度 implementation task sketch。
- 如果 Stage-03 handoff 不可用，必须拒绝或 blocked。
- 本阶段仍只冻结 public boundary 上需要交付给下游的交互，不冻结内部实现类/方法。

## 3. 推演边界
- 不能推演：伪装成已完成实现的设计结果、被抹掉的 unresolved risks、没有消费规则的 provisional 内容、超过 verification/confidence/realizability 证据强度的 readiness 表述、仍有结构矛盾却被写成已收敛的 handoff。
- 可以 provisional 推演：第一版 convergence summary 或 structured delivery expression。

## 4. 输出要求
- 输出必须能直接供 implementation phase 使用。
- 输出必须让下游看清关键 public-boundary 交互顺序，而不要求内部类/方法级设计。
- 输出还必须保留关键技术选型的理由与证据来源。
- 输出还必须说明为什么最终方案不是停在“主流可行”而是逼近约束下更优解。
- 输出还必须显式暴露生命周期 ownership、命令边界和 public-name closure 的结构矛盾，并据此校准 readiness 结论。
- review-bound 内容必须保留下游消费规则。
- implementation task sketch 只能到 slice / module / work-package 级，不能伪装成代码级拆解。

## 5. 边界提醒
- 本文件不是操作流程。
- 本文件也不是最终交付版式。
- 它只定义 Stage-04 的边界合同。
