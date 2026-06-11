# Stage-02 阶段契约（审计镜像）— domain-module-service-decomposition

## 1. 这个文件是做什么的
- 这是 Stage-02 英文主契约文件对应的中文审计镜像。
- 它帮助评审者理解：这个阶段如何把 Stage-01 的能力与边界结果变成领域 / 模块 / 服务分解包。

## 2. 核心定义
- Stage-02 的目标不是做数据与接口细节，而是冻结分解结构。
- 必填输出至少包括：领域图、模块图、服务候选、责任矩阵、lifecycle ownership closure、依赖/协作图、概念 ER、领域事件目录、分解决策。
- 如果没有可用的 Stage-01 handoff，必须拒绝或 blocked。
- 本阶段冻结的是 public boundary，不是内部实现类/方法符号。

## 3. 推演边界
- 不能推演：无边界依据的领域划分、未说明理由的服务切分、隐藏的 ownership overlap、需要下游非 owner 模块回写才能闭合的生命周期状态。
- 可以 provisional 推演：候选模块/服务组合、初版依赖朝向、概念对象关系、领域事件候选。
- 所有 provisional 内容必须显式保留 review-bound 标记。

## 4. 输出要求
- 输出必须能直接供 Stage-03 进行数据/存储/接口设计，且不要求 Stage-03 从零补造核心对象关系或事件流。
- 聚合生命周期必须能由声明的 owner 闭合，不能靠只读下游模块回写上游状态。
- unresolved quality / declaration-state 不能在这里消失。

## 5. 边界提醒
- 本文件不是操作流程。
- 本文件也不是最终交付版式。
- 它只定义 Stage-02 的边界合同。
- 本阶段仍不能下沉到物理 schema、表字段或端点级 API。
