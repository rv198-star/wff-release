# Stage-01 阶段契约（审计镜像）— acceptance-coverage-planning

## 1. 这个文件是做什么的
- 这是 Stage-01 英文主契约文件对应的中文审计镜像。
- 它帮助评审者理解：这个阶段到底要冻结什么、哪些内容必须显式、什么情况下不能继续到 Stage-02。

## 2. 核心定义
- Stage-01 的目标不是执行测试，而是把上游实现交接收束成可供 Stage-02 使用的 validation planning package。
- 必填输出至少包括：acceptance mapping、coverage rationale、gate posture、execution-control posture、Stage-02 may-start 声明。
- 如果没有可用的实现交接，或无法建立 `TEST-* -> API-* -> REQ-*` 映射，就必须拒绝或 blocked。

## 3. 推演边界
- 不能推演：没有 requirement/contract 依据的 acceptance claims、伪装成已满足的 gate posture、无依据的 Stage-02 可启动判断。
- 可以 provisional 推演：第一版 coverage prioritization、轻量 execution grouping、review-bound exclusions。
- 所有 provisional 内容都必须保留 review-bound 明示。

## 4. 输出要求
- 必须输出：
  - validation planning package
  - acceptance checklist linkage
  - coverage explanation linkage
  - gate / execution-control linkage
  - Stage-02 may-start 声明

## 5. 边界提醒
- 本文件不是操作流程。
- 本文件也不是最终输出版式。
- 它只定义 Stage-01 的边界合同。
