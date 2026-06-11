# Stage-01 操作说明（审计镜像）— architecture-definition-and-boundary-setting

## 1. 这个文件是做什么的
- 这是 Stage-01 英文 SOP 的中文审计镜像。
- 它解释这个阶段应如何从 intake 走到边界冻结、约束吸纳、能力结构形成、review、gate-pass。

## 2. 流程主线
- 先确认上游 handoff 与 declaration states。
- 先做边界，不先进入分解。
- NFR 不完整时不能假装完整，只能显式保留 unknown / deferred / review-bound。
- 若关键边界依赖外部系统、采购能力或 brownfield owner，必须先做 realizability scan，并给出 substitute-boundary 候选或明确 `unknown/unavailable`。
- 在进入分解前，要先补出边界级安全姿态和数量级容量姿态，不能把这两项完全留给后续阶段现编。
- 在 handoff 前，还要明确 downstream `may-assume / must-not-assume`，避免 Stage-02 把 review-bound 依赖当成已落地事实。
- 只有当边界、约束态势、能力地图、架构方向都成形时，才允许 handoff 到 Stage-02。

## 3. 方法资产角色
- `ddd-reference`：边界与能力语言。
- `software-architecture-in-practice`：架构方向与质量视角。
- `diagram-expression`：图示表达纪律。
- supporting sources 只能补充，不替代主骨架。

## 4. 边界提醒
- 本文件不是边界合同，边界合同看 `skill-contract.md`。
- 本文件也不是最终交付版式，交付版式看 `output-template.md`。
