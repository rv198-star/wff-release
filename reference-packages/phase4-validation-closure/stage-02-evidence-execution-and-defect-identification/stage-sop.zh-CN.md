# Stage-02 操作说明（审计镜像）— evidence-execution-and-defect-identification

## 1. 这个文件是做什么的
- 这是 Stage-02 英文 SOP 的中文审计镜像。
- 它解释这个阶段应如何在 Stage-01 controls 下执行 bounded validation，并形成 evidence / defect / unresolved-risk 可见性。

## 2. 流程主线
- 先确认 Stage-01 may-start 与 execution-control。
- 执行 in-scope 场景。
- 对每个关键结果保留 evidence path。
- 对当前 requested frontend，若 P3 已有真实 browser/runtime evidence，则执行两轮相互隔离的 AI Review。**Round 1 OMR** 先生成 `open-ended-maturity-review-request.json`，不预设维度、不提供 SQR 分数/finding，Reviewer 自由发现产品问题并先写 finding、最后才给整体成熟度分；总分至少 80 且没有 `critical`/`high` finding 才可 PASS。**Round 2 SQR** 再生成 `ui-product-review-request.json`，固定检查 productness、首次进入/导航/任务连续性、终端角色真实性与最小权限、业务数据发现/read-model 充分性、Interaction Affordance & Task Efficiency、项目语言对齐、clean first use 与 reload/re-entry 上下文恢复、trust/history/provenance、Metadata Leakage、页面构图/层级、业务语言、状态/动作、desktop/mobile 可用性和 accessibility baseline；SQR 不接收 OMR finding/分数。最后 **RSG** 只合成 verdict，不平均分：OMR 与 SQR 必须同时 PASS。super-role、fixture id、手输/随机 UUID、截图存在、结构检查或任一 AI 分数都不能替代真实 consumer qualification。事实可访问性/浏览器证据必须另外证明 desktop/mobile Chromium 下不存在文档级横向 viewport overflow，仅有截图不能替代该事实 Gate；缺少相关事实证据时必须保持 review-bound。有效 OMR finding 必须另外保留到 `open-ended-maturity-learning-candidates.json`，只作为非权威学习候选，不改变当前 verdict、不自动归纳、不回灌当前 OMR/SQR。OMR 中反复出现的跨场景/跨版本、稳定且业务无关的通用问题，只有在后续显式 Agentic/governance 决策后才可提炼进 SQR；OMR 永远保留为 discovery layer。
- 对 fail / blocked / unresolved-risk 保持显式，而不是压进总结叙事；UI/Product finding 应返回当前 frontend authoring，若缺的是上游产品/API/state authority 则返回对应 authority owner。
- 最终产出 Stage-03 可消费的 execution evidence package。

## 3. 边界提醒
- 本文件不是 closure judgment。
- 本文件也不是最终发布判断。
