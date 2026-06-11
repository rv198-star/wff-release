# Stage-03 技能契约 — validation-closure-and-delivery-readiness-judgment

## 1. 技能目标
- 本技能把 Stage-02 的执行证据转换成一个可供下游使用的 validation closure judgment。
- 它**不**批准最终 release readiness，也不允许隐藏 unresolved defects / residual risks。

## 2. 输入项
- 必填输入：
  - Stage-02 execution evidence package（`TEST-STG02-OUTPUT-*`）
  - evidence summary
  - defect / blocked / residual-risk visibility
  - Stage-01 gate references
- 缺失输入时如何处理：
  - 若 Stage-02 输出不可用，则拒绝或保持 blocked
  - 若关键 gate evidence 缺失，则不得给出虚假 closure pass

## 3. 输出要求
- 必须输出：
  - closure judgment package
  - gate review result
  - unresolved defect / risk summary
  - downstream reliance boundary

## 4. 边界提醒
- 本文件不是可选 Stage-04 release approval。
- 它只定义 Phase-4 closure judgment 的边界合同。
