# WFF human-review 阅读面

WFF 会保留很多机器证据、trace、诊断报告和日志。它们对可审计性很重要，但不是第一次人工阅读的入口。

从本版本开始，阶段 runner 会额外生成一个加法目录：

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

原有 canonical artifact 路径不移动、不改名，脚本、gate、trace 和历史 proof 仍以原路径为准。`human-review/` 只是把人类主读文件复制出来并生成索引。

## 先看什么

优先打开：

```text
<phase-output>/human-review/INDEX.md
```

它会列出：

- 当前阶段主读文档；
- gate / verdict / review-bound / claim ceiling 入口；
- 复制到 `human-review/artifacts/` 的阅读副本；
- 原始 canonical source 路径；
- 哪些目录属于 AI / gate working evidence。

## 翻译与 fallback

如果 localized reader translation 已生成，`human-review/` 会优先复制 `*.reader.zh-CN.md`。

如果没有启动 reader translation，`human-review/` 会复制 canonical 原文档作为 fallback。这样人工入口不会因为缺少翻译而消失。

## 边界

- `human-review/` 不替代 PRD、ESP、Action Card、phase verdict、gate report、trace registry 或 retained proof。
- `human-review/` 不提升 claim ceiling。
- 如果上游产物变化，应重新运行对应 phase runner，或运行 `scripts/common/human_review_surface.py` 刷新阅读面。

手动刷新示例：

```bash
python3 scripts/common/human_review_surface.py --phase phase3 --output-dir <phase3-output-dir>
```
