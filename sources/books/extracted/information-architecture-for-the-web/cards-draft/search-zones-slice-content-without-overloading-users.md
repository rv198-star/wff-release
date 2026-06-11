# Search zones：切分索引提升相关性，但会增加交互复杂度

- 类型：方法
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Search Systems / Determining search zones）
- 摘要：通过内容类型/受众/主题等切分索引，减少 apples-and-oranges 结果；但 zones 也会增加用户操作负担。

## 输入条件
- 全局搜索结果混杂，相关性差

## 关键步骤
1. 识别可形成“同质集合”的 zones（内容类型/受众/部门等）。
2. 默认仍提供全局搜索；zones 作为二次筛选。
3. 测试 zones 的可理解性与使用意愿（不要堆太多）。

## 输出结果
- 分区索引策略 + UI 暴露策略

## 适用边界
- zones 过细会让用户忽略它们，反而失效。

## 常见错误
- 用技术结构（数据库/服务）切 zone，而不是用用户需求切

## 关联模板
- Search zone 设计表（purpose / inclusion / UI）

## 下游使用建议
- 用于 Stage-2：把 zones 作为“信息架构视图”，不是纯搜索配置。
