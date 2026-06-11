# Stage-01 操作说明（审计镜像）— acceptance-coverage-planning

## 1. 这个文件是做什么的
- 这是 Stage-01 英文 SOP 的中文审计镜像。
- 它解释这个阶段应如何从实现交接走到 acceptance mapping、coverage freeze、gate freeze、execution-control freeze 与 Stage-02 start declaration。

## 2. 流程主线
- 先确认上游实现交接与 traceability basis。
- 先做 acceptance/coverage/gate，不先进入执行。
- gate posture 不完整时不能假装完整，只能显式保留 blocked / review-bound。
- 只有当 acceptance、coverage、gate、execution-control 都成形时，才允许 handoff 到 Stage-02。

## 3. 方法资产角色
- `testing-validation-external-intake-v1`：提供 checklist / defect / runbook / closure 字段骨架。
- `contract-spine`：提供 `TEST-* -> API-* -> REQ-*` 主脊梁。
- `round-04-test-gate-cards`：提供 PASS-grade gate shape。

## 4. 边界提醒
- 本文件不是边界合同，边界合同看 `skill-contract.md`。
- 本文件也不是最终交付版式，交付版式看 `output-template.md`。
