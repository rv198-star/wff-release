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

## 2.1 当前前端 UI/Product Review 边界
- 当当前 P3 已存在 requested frontend 的真实 browser/runtime evidence 时，截图和 browser green 只证明“页面被真实观察/执行”，不能直接证明产品/UI质量。
- Stage-02 必须基于同一份当前 application/page authoring、P3 decision、UI IA、consumer journeys、terminal-role persona、business-data / clean-first-use、项目语言、screenshot / trace 证据执行**两轮相互隔离的 AI Review**。第一轮 **OMR（Open-ended Maturity Review）**先生成 `open-ended-maturity-review-request.json`：不预设评分维度、不提供后续 SQR 的分数/结论/finding，Reviewer 先自由发现具体问题，再给一个整体成熟度分；OMR 只有在总分至少 80 且没有 `critical` / `high` finding 时才可 PASS。第二轮 **SQR（Structured Qualification Review）**再生成 `ui-product-review-request.json`，按固定维度验收，维度包括 productness、首次进入/导航/任务连续性、终端角色真实性与最小权限、业务数据发现/read-model 充分性、Interaction Affordance & Task Efficiency、项目语言对齐、clean first use 与 reload/re-entry 上下文恢复、trust/history/provenance、Metadata Leakage、页面构图与信息层级、业务语言、状态/动作清晰度、desktop/mobile 可用性和 accessibility baseline；SQR 不得接收 OMR finding/分数作为输入。最后由 **RSG（Review Synthesis Gate）**合成：OMR PASS 且 SQR PASS 才可关闭 `ui-review`，两套分数不得平均、不得互相抵消。每个已接受终端角色都必须有独立最小权限 persona 资格证据，super-role 不能替代；需要 clean first use 时不得用业务 seed、fixture id、手输/随机 UUID 替代真实 write + read/discovery + 重新进入。consumer journey 是资格前提，AI 分数不能替代；事实可访问性/浏览器证据还必须证明 desktop/mobile Chromium 下不存在文档级横向 viewport overflow，仅有截图不能替代该事实 Gate。缺少相关事实证据时必须保持 review-bound，不能推断 PASS。有效 OMR finding 还必须被原样保留到 `open-ended-maturity-learning-candidates.json`，作为**非权威的后续学习候选**；Workflow 不得自动归纳问题模式、不得影响当前 OMR/SQR/RSG、也不得自动增加 SQR 维度。只有跨场景/跨版本重复出现、可形成稳定且业务无关 PASS/FAIL 知识的问题，才可由后续显式 Agentic/governance 决策提炼进入 SQR；单次 finding 不自动扩张 checklist，SQR 再成熟也不能替代 OMR。
- 目标、约束、设计理由、blueprint/region、operation/service-binding、Agent/authority 等工程元数据可以影响设计，但默认不能直接变成用户可见产品文案。
- Workflow 只校验 Review 是否覆盖完整且绑定当前证据；不得用关键词扫描替代 UI/Product 判断。

## 3. 输出要求
- 必须输出：
  - execution evidence package
  - evidence summary
  - defect / blocked / unresolved-risk visibility
  - 当前 requested frontend 存在时的 OMR request、OMR finding/整体分、`open-ended-maturity-learning-candidates.json` 非权威学习候选、SQR request、SQR 结构化评估/finding，以及 `review-synthesis-gate.json` RSG 结果
  - Stage-03 handoff summary

## 4. 边界提醒
- 本文件不是 closure judgment。
- 本文件也不是 release decision。
- 它只定义 Stage-02 的执行与证据边界。
