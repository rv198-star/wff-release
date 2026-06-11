# Stage-02 操作说明（审计镜像）— domain-module-service-decomposition

## 1. 这个文件是做什么的
- 这是 Stage-02 英文 SOP 的中文审计镜像。
- 它解释这个阶段应如何从 Stage-01 handoff 进入分解、澄清、blocked、provisional、review、gate-pass。

## 2. 流程主线
- 先消费 Stage-01 的边界与能力结构。
- 先做领域 / 模块 / 服务分解，不先下沉到数据与接口细节。
- 在结构分解完成后，补足概念 ER 与领域事件目录，供 Stage-03 承接。
- 生命周期状态要能由声明的 owner 模块完成，不能偷渡成下游只读消费者的回写责任。
- public boundary 要显式冻结，private implementation 不在本阶段定名。
- 如果分解依据不足，必须 blocked。
- 只有分解结构、责任和依赖图都清楚时，才允许 handoff 到 Stage-03。

## 3. 方法资产角色
- DDD 负责边界与上下文分解语言。
- architecture partitioning 负责模块与依赖纪律。
- diagram expression 负责结构图、依赖图与概念关系图表达。

## 4. 边界提醒
- 本文件不是边界合同，边界合同看 `skill-contract.md`。
- 本文件也不是最终交付版式，交付版式看 `output-template.md`。
- 本阶段输出的 ER / 事件信息必须保持概念层，不进入 schema / endpoint 细节。
- 若某个状态机闭合需要下游只读模块回写，上游分解应被视为未闭合。
