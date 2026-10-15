# Stage-04 阶段契约（审计镜像）— design-convergence-and-delivery-prototype

## 1. 这个文件是做什么的
- 这是 Stage-04 英文主契约文件对应的中文审计镜像。
- 它帮助评审者理解：这个阶段如何把前 3 个阶段收口成面向实现的设计交付包。

## 2. 核心定义
- Stage-04 的目标不是直接生成开发任务，而是收敛设计并形成 implementation-facing handoff 与粗粒度 implementation task sketch。
- 必填输出至少包括：架构收敛摘要、交付原型/结构表达、关键交互时序集、最优性审查、设计验证说明、realizability / structural consistency / readiness calibration、未解决风险清单、handoff 包、粗粒度 implementation task sketch。
- 如果 Stage-03 handoff 不可用，必须拒绝或 blocked。
- 本阶段仍只冻结 public boundary 上需要交付给下游的交互，不冻结内部实现类/方法。

## 3. 推演边界
- 不能推演：伪装成已完成实现的设计结果、被抹掉的 unresolved risks、没有消费规则的 provisional 内容、超过 verification/confidence/realizability 证据强度的 readiness 表述、仍有结构矛盾却被写成已收敛的 handoff。
- 可以 provisional 推演：第一版 convergence summary 或 structured delivery expression。

## 4. 输出要求
- 输出必须能直接供 implementation phase 使用。
- 输出必须让下游看清关键 public-boundary 交互顺序，而不要求内部类/方法级设计。
- 输出还必须保留关键技术选型的理由与证据来源。
- 输出还必须说明为什么最终方案不是停在“主流可行”而是逼近约束下更优解。
- 输出还必须显式暴露生命周期 ownership、命令边界和 public-name closure 的结构矛盾，并据此校准 readiness 结论。
- review-bound 内容必须保留下游消费规则。
- 同一 P1 commitment 横跨多个角色/任务上下文且采用 exact operation set 收口时，必须保留逐 context 的角色与 operation coverage；Agent 判定需要重新进入/找回时，必须有该角色可见且明确承载该 commitment authority 的 read operation。
- implementation task sketch 只能到 slice / module / work-package 级，不能伪装成代码级拆解。

## 5. 边界提醒
- 本文件不是操作流程。
- 本文件也不是最终交付版式。
- 它只定义 Stage-04 的边界合同。


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
