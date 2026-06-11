# Stage-03 阶段契约（审计镜像）— data-storage-and-interface-design

## 1. 这个文件是做什么的
- 这是 Stage-03 英文主契约文件对应的中文审计镜像。
- 它帮助评审者理解：这个阶段如何把分解结构转成数据、存储、接口和交互设计包。

## 2. 核心定义
- Stage-03 的目标不是做最终原型收敛，而是冻结数据归属、存储策略、接口契约和交互路径。
- 必填输出至少包括：数据模型摘要、数据归属图、存储策略、schema 草案、接口契约、API 端点草案、lifecycle / command consistency checks、public-boundary registry closure、交互流程、场景覆盖矩阵、安全架构提纲、技术栈与部署假设、技术选型评估矩阵、主导瓶颈假设、架构候选替代集、主流基线不足说明、约束主导的最优候选、容量与性能假设、关键权衡。
- 现在还必须补出：关键外部依赖 realizability、substitute-boundary plan、以及 downstream `may-assume / must-not-assume` 契约。
- 如果没有可用的 Stage-02 handoff，或 handoff 缺少概念 ER / 领域事件目录，必须拒绝或 blocked。
- 本阶段冻结的是 public boundary 上可见的契约与名字，不是内部实现类/方法。

## 3. 推演边界
- 不能推演：无归属依据的数据结构、没有失败语义的接口契约、无法由 owner 执行的生命周期/写路径、一个权威业务动作被多个命令边界重复承接、未定义也未 deferred 的 public-boundary 名称、伪装成已确定的质量约束、没有可得性依据的关键外部依赖承诺。
- 可以 provisional 推演：初版 schema / contract / interaction draft，以及 security / stack / performance 假设、关键依赖 realizability 初扫、substitute-boundary plan。

## 4. 输出要求
- 输出必须能直接供 Stage-04 收敛，且不要求 Stage-04 从零补造 schema、endpoint 或关键运行假设。
- 生命周期、写权限、命令边界和 public-boundary 名称必须在包内自洽闭合，不能把修补工作丢给 Stage-04。
- 所有已知业务场景都应被 coverage matrix 承接，但不要求在这一阶段为所有场景都画详细时序。
- 技术选型若依赖当前事实，必须显式引用外部证据，不能只依赖模型记忆。
- 关键外部依赖若不是 `confirmed`，必须显式给出 substitute-boundary 或 readiness downgrade，不能把猜测留给 Stage-04。
- 若主导约束表明主流架构可能只是“及格线”，必须继续展开替代候选与最优候选分析。
- unresolved quality / declaration-state 必须显式带下去。

## 5. 边界提醒
- 本文件不是操作流程。
- 本文件也不是最终交付版式。
- 它只定义 Stage-03 的边界合同。
- 本阶段可以给出 draft/outline/assumption，但不能用缺省代替这些关键设计项。
