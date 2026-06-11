# Stage-03 操作说明（审计镜像）— data-storage-and-interface-design

## 1. 这个文件是做什么的
- 这是 Stage-03 英文 SOP 的中文审计镜像。
- 它解释这个阶段如何从分解结果进入数据与接口设计，并保持 ownership / contract / flow 的清晰度。

## 2. 流程主线
- 先消费 Stage-02 的分解结构与依赖图。
- Stage-02 handoff 不应只给结构图，还应包含概念 ER 与领域事件目录。
- 先明确 ownership，再做 schema / storage / interface / interaction。
- 生命周期与写路径必须和 owner 对齐；一个权威业务动作只能有一个主命令边界，除非显式拆成非重叠多步。
- public-boundary 名称必须闭合落位，不能在 schema / contract / endpoint 之间漂移。
- 所有已知业务场景都要先过 coverage matrix，再决定哪些关键 public-boundary 场景值得画时序。
- 技术选型若涉及版本、LTS、license、安全公告、benchmark 等可变信息，必须联网或外部检索核实。
- 若关键外部依赖的可得性、owner、采购或契约前提不稳，必须显式给出 realizability 状态与 substitute-boundary plan。
- 先识别主导瓶颈，再决定是否必须跳出主流基线去评估更强架构模式。
- 在这一步同步补足 security posture、stack/deployment 和 capacity/performance 假设。
- handoff 前必须明确 downstream `may-assume / must-not-assume`，避免 Stage-04 或实现阶段把 review-bound 依赖当成已落地主路径。
- 如果边界矛盾尚未解决，必须 blocked。
- 只有数据 / 存储 / 接口包成形时，才允许 handoff 到 Stage-04。

## 3. 方法资产角色
- architecture references 负责 tradeoff 逻辑。
- diagram expression 负责数据与交互图表达。
- system/runtime reasoning 负责栈、部署与容量假设的收束。
- quality taxonomy 只作为 supporting lens。

## 4. 边界提醒
- 本文件不是边界合同，边界合同看 `skill-contract.md`。
- 本文件也不是最终交付版式，交付版式看 `output-template.md`。
- schema/API/security/stack/performance 可以是 draft，但不能在该阶段空缺。
- 内部类名 / 方法名不是该阶段的必填交付物。
- “主流可行”不等于“约束下最优”；必要时必须继续展开候选比较。
