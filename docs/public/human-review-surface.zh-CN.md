# WFF AI / 外部 Review 阅读面

WFF 会保留很多机器证据、trace、诊断报告和日志。它们对可审计性很重要，但不是第一次 review 的入口。

阶段 runner 会额外生成一个加法目录：

```text
<phase-output>/
  human-review/
    INDEX.md
    manifest.json
    artifacts/
      primary/
      gate/
      review/
```

原有 canonical artifact 路径不移动、不改名，脚本、gate、trace 和历史 proof 仍以原路径为准。`human-review/` 只是把 review 主读文件复制出来并生成索引。
`human-review/` 是历史兼容路径名；当前语义是 AI review / external red-team review 的阅读面。AI 或外部评审者只要记录了具体代码、trace、测试、claim ceiling 等锚点，就可以承担这个 review 角色。

## 先看什么

优先打开：

```text
<phase-output>/human-review/INDEX.md
```

它会列出：

- 当前阶段主读文档；
- gate / verdict / 待审阅确认（机器值 `review-bound`）/ claim ceiling 入口；
- 复制到 `human-review/artifacts/` 的阅读副本；
- 原始 canonical source 路径；
- 哪些目录属于 AI / gate working evidence。

## 翻译与 fallback

如果 localized reader translation 已生成，`human-review/` 会优先复制 `*.reader.zh-CN.md`。

如果没有启动 reader translation，`human-review/` 会复制 canonical 原文档作为 fallback。这样 review 入口不会因为缺少翻译而消失。

## 边界

- `human-review/` 不替代 PRD、ESP、Action Card、phase verdict、gate report、trace registry 或 retained proof。
- `human-review/` 不提升 claim ceiling。
- 未填写或缺少锚点的 review 记录必须保持机器状态 `review-bound`，中文阅读面显示为“待审阅确认”，且不能被机器门禁自动升级。
- 如果上游产物变化，应重新运行对应 phase runner，或运行 `scripts/common/human_review_surface.py` 刷新阅读面。

## 中文术语约定

- 机器状态保持 `review-bound`，中文阅读面统一显示“待审阅确认”。
- 普通 `human reviewer` 统一显示“审阅人”；只有在明确区分人工与 AI/自动化时才使用“人工审阅者”。
- JSON 字段、schema、状态枚举和 claim ceiling 不因显示翻译而改变。

## Release HTML 旁路

正式 Release 包在 P1、P2、P3 各阶段完成后，异步启动中文阅读与人工审阅语义投影；主链只投递，不等待。中文 reader 保留 canonical 原件的完整可追溯翻译。独立的 Agentic 语义投影先生成结构化 review decision model，其中显式保留受影响对象、当前选择、理由、约束、风险、审阅问题和来源证据；确定性 renderer 再从已验收模型生成 PRD、ESP 和 Action Card Markdown/HTML，Markdown 不能成为第二份语义权威。完整 Trace、schema、组件、来源、测试和控制 identity 保存在 machine-only projection sidecar 与 canonical 原件中；人工审阅附录只解释关系、责任、证据、风险和待审阅确认事项的影响，不逐项铺开完整编号索引。P3 资料齐备后，旁路把人工审阅主文、P1/P2 图、语义附录与原件入口组装到：

```text
<case-root>/human-review/index.html
```

仓库开发态默认不启动，以避免反复跑批产生无必要的模型消耗；显式设置 `WFF_HUMAN_REVIEW_SIDECAR=1` 才开启。Release 包默认开启，也可用 `WFF_HUMAN_REVIEW_SIDECAR=0` 关闭。worker 最多尝试三次；源文件在生成期间发生变化时，旧结果不能覆盖当前 HTML。

Action Card 主读章节不是 `validation.json` 中每个底层组件卡的逐文件翻译。Agentic 投影会按业务/实施责任把组件组织为有限数量的人工审阅行动卡；每张卡先说明目标、实施判断与审阅证明。左侧导航和卡片标题使用人工审阅语义标题，`HAC-*` 只作为 trace identity 保留在 manifest/sidecar 中；完整组件和 operation 身份不作为导航或正文标题。

ESP 可选读取 `.wff/architecture-reconstruction/review-input.json`。该输入只携带来源绑定的架构树、责任图、实现意图、变更影响、保证机制归属和开放冲突；文件缺失时不阻断，不允许脚本自行恢复架构。文件存在时，每个开放冲突必须保留为结构化 evidence identity 和明确审阅问题，不能由确定性代码自动解决。

每份 PRD/ESP 主文和每张人工审阅行动卡都会生成独立的 `*.decision-quality.json` 审计报告，并汇总到 `human-review/decision-quality-audit.json` 与 `human-review/decision-quality-audit.md`。审计器不判断产品或架构答案是否正确，只检查审阅人是否拿到了来源支撑的具体对象、当前选择、理由/约束、风险/例外、证据以及明确可回答的审阅问题。首次非 `pass` 会把具体缺口反馈给 Agentic 做一次修复；第二次仍为 `fail` 时拒绝发布，仍为机器状态 `review-bound` 时在中文阅读面标记为“待审阅确认”，保留该质量上限，不能记录为内容质量通过。可通过 `python3 scripts/release/audit_human_review_decision_quality.py --case-root <case-root> --strict` 重新执行严格审计。

HTML 使用 `human-review-dossier-manifest.v1`，只是 P1/P2/P3 数据链的只读人工审阅投影，不参与 gate、Trace 真相或 claim ceiling 裁决。语义投影缺失、失真或来源过期时必须拒绝完整 dossier，不能退化为把机器数据链直接展示给审阅人。

手动刷新示例：

```bash
python3 scripts/common/human_review_surface.py --phase phase3 --output-dir <phase3-output-dir>
```
