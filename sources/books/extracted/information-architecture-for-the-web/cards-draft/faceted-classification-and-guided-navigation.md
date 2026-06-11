# 分面分类（Faceted classification）与引导式导航（Guided navigation）

- 类型：方法
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Faceted classification and guided navigation）
- 摘要：从“把东西放哪”转为“如何描述它”。用多维分面支撑多路径浏览与检索，并作为长期稳定的 IA 底座。

## 输入条件
- 单一层级分类无法覆盖用户多样路径；用户需要组合条件找内容/商品

## 关键步骤
1. 识别内容的关键维度（facets），并为每个维度建立可治理的值域（词表）。
2. 允许多层级（polyhierarchy）：不同维度形成不同“纯分类”。
3. 在界面层引导组合分面（guided navigation），并持续测试/迭代。

## 输出结果
- 分面元数据 schema + 受控词表 + 可组合的浏览/筛选体验

## 适用边界
- 分面建设成本高，需要治理与持续运营；不要在无元数据能力时强上。

## 常见错误
- 把分面当 UI 组件，而不是底层描述与词表资产

## 关联模板
- 分面设计表（facet / values / governance / UI exposure）

## 下游使用建议
- Stage-2：当信息量大且组合查询常见时，优先考虑 faceted 作为“可演进底座”。
