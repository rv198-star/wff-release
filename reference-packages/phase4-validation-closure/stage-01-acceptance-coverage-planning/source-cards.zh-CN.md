# Stage-01 来源卡（审计镜像）— acceptance-coverage-planning

## 1. 这个文件是做什么的
- 这是 Stage-01 英文 `source-cards.md` 的中文审计镜像。
- 它说明：Stage-01 应优先依赖哪些来源骨架来形成 acceptance、coverage 与 gate 语言。

## 2. 核心来源角色
- `testing-validation-external-intake-v1`：提供 acceptance/UAT、gate、coverage 字段骨架。
- `contract-spine`：提供 traceability 主骨架。
- `round-04-test-gate-cards`：提供 gate 语义的 PASS-grade 参考。

## 3. 边界提醒
- 不能把 source-card 内容原样抄进运行时输出。
- 如果关键字段没有来源支撑，应显式记录 gap，而不是 invent。
