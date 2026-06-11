# Synonym ring 提升 recall，但可能降低 precision：要做界面与排序补偿

- 类型：方法
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Synonym Rings / precision vs recall）
- 摘要：用等价词扩展查询可显著提升召回，但会引入不含原词的结果与相关性下降。

## 输入条件
- 用户用错词/拼写变体导致“搜不到”

## 关键步骤
1. 从搜索日志与用户访谈收集词汇变体。
2. 建立 synonym ring（查询扩展）。
3. 用排序/提示平衡：精确匹配优先、或提供“扩展到相关词”。

## 输出结果
- 更高 recall + 可解释的检索行为

## 适用边界
- 过度扩展会污染结果；需要持续调参。

## 常见错误
- 在后台扩展但不告知，导致用户困惑

## 关联模板
- 词汇变体收集表（search log → ring）

## 下游使用建议
- Stage-2：把 synonym ring 视为 IA 资产，而不是搜索工程小技巧。
