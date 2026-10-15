# Stage-02 输出模板（审计镜像）— evidence-execution-and-defect-identification

## 1. 这个文件是做什么的
- 这是 Stage-02 英文输出模板的中文审计镜像。
- 它帮助评审者理解：execution evidence package 至少要包含什么，才能供 Stage-03 做 closure review。

## 2. 最关键字段
- execution scope completion summary
- execution result summary
- evidence summary
- 当前 requested frontend 存在时的 UI/Product Review request / manifest / structured findings 引用
- defect / blocked / unresolved-risk log
- Stage-03 handoff summary

## 3. 交接要求
- 最终交给 Stage-03。
- handoff package 至少要包含：执行结果、证据摘要、缺陷/blocked/risk 可见性、closure review 所需摘要。
- 当前 P3 已有 requested frontend browser evidence 时，截图存在只能证明可观察性；没有 current-bound 的独立 UI/Product Review 时，主观 `ui-review` 必须保持 `review-bound`。
