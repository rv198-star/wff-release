# Stage-02 技能契约 — evidence-execution-and-defect-identification

## 1. 技能目标
- 本技能在 Stage-01 输出的约束下执行有边界的 testing-validation 工作，并产出可供 Stage-03 closure 判断的执行证据。
- 它**不**重写 Stage-01 planning policy，不允许把 evidence 缺失伪装成完成，也不负责最终 release approval。

## 2. 输入项
- 必填输入：
  - Stage-01 validation planning package（`TEST-STG01-OUTPUT-*`）
  - acceptance checklist / coverage / gate / execution-control 引用
  - Stage-02 may-start 声明
- 可选输入：
  - 补充 execution clarifications
  - 已批准 waivers
  - operator-facing install/run guidance
- 缺失输入时如何处理：
  - 若 Stage-01 输出缺失或不可用，则拒绝或保持 blocked
  - 若 Stage-02 may-start 为 `no` 且无批准覆盖规则，则拒绝启动

## 3. 输出要求
- 必须输出：
  - execution evidence package
  - evidence summary
  - defect / blocked / unresolved-risk visibility
  - Stage-03 handoff summary

## 4. 边界提醒
- 本文件不是 closure judgment。
- 本文件也不是 release decision。
- 它只定义 Stage-02 的执行与证据边界。
