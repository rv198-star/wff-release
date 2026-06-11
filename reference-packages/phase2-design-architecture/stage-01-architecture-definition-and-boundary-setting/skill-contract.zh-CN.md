# Stage-01 阶段契约（审计镜像）— architecture-definition-and-boundary-setting

## 1. 这个文件是做什么的
- 这是 Stage-01 英文主契约文件对应的中文审计镜像。
- 它帮助评审者理解：这个阶段到底要冻结什么、什么情况下不能继续、哪些内容只能 provisional 处理。

## 2. 核心定义
- Stage-01 的目标不是做服务拆分，而是把上游产品/需求 handoff 收束成可供 Stage-02 使用的架构入口包。
- 必填输出至少包括：系统边界、约束态势、安全架构草图、容量估算、能力地图、架构方向、关键架构决策。
- 现在还必须补出：关键依赖 realizability scan、substitute-boundary 候选、以及 downstream `may-assume / must-not-assume` 契约。
- 如果没有可用的上游架构入口 handoff，必须拒绝或 blocked。

## 3. 推演边界
- 不能推演：没有依据的系统边界、伪装成已确认的 NFR 完整性、未说明来源的架构结论、没有可得性依据的关键外部依赖承诺。
- 可以 provisional 推演：初版能力结构、架构方向候选、质量属性吸纳草案、关键依赖 realizability 初扫、substitute-boundary 候选、边界级安全姿态草图、数量级容量姿态。
- 所有 provisional 内容都必须带来源、置信度、验证状态，并保留 review-bound 标记。

## 4. 输出要求
- 必须输出：
  - 系统边界说明
  - 继承 / 推演 / 未知 / 延后约束结构
  - 关键依赖 realizability scan
  - first-pass realization mode
  - substitute-boundary 候选
  - 安全架构草图
  - 容量估算
  - 能力地图
  - 架构方向与关键决策
  - downstream assumption contract
- 输出必须能直接供 Stage-02 使用。

## 5. 边界提醒
- 本文件不是操作流程。
- 本文件也不是最终交付版式。
- 它只定义 Stage-01 的边界合同。
