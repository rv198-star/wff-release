# Stage-04 操作说明（审计镜像）— design-convergence-and-delivery-prototype

## 1. 这个文件是做什么的
- 这是 Stage-04 英文 SOP 的中文审计镜像。
- 它解释这个阶段如何把 Stage-01~03 聚合、校对、收敛并形成最终 handoff。

## 2. 流程主线
- 先聚合前序阶段结果。
- 先确认所有已知业务场景都有 coverage，再为关键 public-boundary 场景补详细时序。
- 技术选型矩阵与外部证据引用要一并带入收敛，不允许在 Stage-04 丢失。
- 主导瓶颈、主流基线不足说明、最优候选判断也必须带入收敛，不允许被压缩成一句推荐结论。
- 先识别冲突与未解决项，再做收敛摘要。
- 生命周期 ownership、命令边界和 public-name closure 的结构矛盾必须显式出现在收敛层，且会直接影响 readiness 定级。
- handoff 前要补出粗粒度 implementation task sketch，但不能越界冻结内部类 / 方法 / 文件。
- 不能把 unresolved risks 擦掉来换取“看起来完成”。
- 只有 handoff package 和 downstream usage rule 明确时，才允许 gate-pass。

## 3. 方法资产角色
- synthesis references 负责一致性与收敛逻辑。
- diagram expression 负责收敛视图表达。
- sequence reasoning 负责关键 public-boundary 场景的时序表达。
- optimality reasoning 负责 acceptable vs optimal 的最终审查。

## 4. 边界提醒
- 本文件不是边界合同，边界合同看 `skill-contract.md`。
- 本文件也不是最终交付版式，交付版式看 `output-template.md`。
- 详细时序图不是全场景强制项，内部类名 / 方法名也不是。
- readiness 措辞不能超过 package 自己的 verification / confidence / realizability 证据强度。


## Stage-05 交互交接运行入口

选定的架构/API 输入冻结后，按 `reference-packages/phase2-design-architecture/interaction-generation.md` 使用 `scripts/phase2/interaction_generation.py` 及版本化中性模板库。按原始 ID 为十个交互小节分别选取输入；缺口显式保留，每段最多两次本地诊断修复，已接受段可复用。代码组装模式和来源，现有 OMR 与隔离的 SQR 依次评审原始主体。向 P3 交接仅限交互设计的冻结清单及 SHA-256、调用记录、缺口和委托规则；这不证明完整 P2 验收，也不授权本周期重生成 P1/P2。


### 调用方输出上限与单段修复

D/P3 共用 `common.bounded_model_call` 与 `common.bounded_response_stream`。
D内容提示以每节约4,000输出token以内及简短推理为设计目标，不设填充配额；60K 请求 / 8K 输出 / 本地 schema ≤3 层不变。
流式累计含推理的保守估算到 8K 主动断开，按请求上界 + 8K 记账，保留用量类型与估算细节。
截断只拒绝本段，简化后在同段最多两次修复内重做；仍失败标 T2，其余段继续。
HTTP/流式错误按请求上界 + 8K 的完整预占保守计费，标 `transport-error-upper-bound`，不冒称远端执行已知。
同段最多重发一次，每次均计调用/预占；同段两次传输失败留 T2，其余段继续。全轮第三次传输错误停止并报 Owner。
重发仍受申报次数/token/墙钟限制；其他未知用量仍停止整轮。有限网络恢复不新增语义评审轮次、不重置本段内容修复次数。
不追加评审轮次，不将未接受的评审宣称为完成；获授权的v2限额冻结保留显式T2评审缺口。

整份交互评审请求超过60K时，`prepare_review_packets` 保留全部已接受设计与显式缺口可见，按焦点小节分批附上未改写的原始事实。先执行全部OMR包，再将相同原始包交给隔离SQR；仍是原有两个逻辑评审，每包均计入申报的实际调用/token/墙钟上限。两份回执绑定包输入、prompt摘要及每个已结算Journal调用；代码保留全部发现并机械汇总review-bound标记，不另加模型裁决。完整评审的v1冻结仍须两份原始回执。明确获授权的限额收尾在申报额度到顶时停止调用，使用 `freeze_bounded_interaction`：保留未改写的原始作者小节和真实回执，将有实质发现或缺失/未接受评审覆盖的小节标为T2，以显式评审缺口冻结v2。不追加评审、不重置额度、不重生成已接受小节，也不声称评审已完成；P3校验同一清单并在本地解决保留缺口。 已标定通道/模型按文本delta事件数×1.02计输出，加1024推理预留与既有框架余量；请求为ceil(UTF-8字节/2)+4000。每次完成调用比对provider可见token，偏差>3%回到字节法并报告；换通道或模型须重新标定，完成调用按实测、截断/传输错误按请求估算+8000记账。
