# 元数据与受控词表是系统胶水：把搜索、导航、标签粘在一起

- 类型：概念
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Thesauri, Controlled Vocabularies, and Metadata）
- 摘要：在大型信息环境中，受控词表与元数据统一语言与关系，支撑更连贯的导航与检索。

## 输入条件
- 搜索/导航/标签各说各话，用户词与系统词无法映射

## 关键步骤
1. 将“放哪”转为“怎么描述”（metadata-first mindset）。
2. 选用受控词表的合适形态：synonym ring / authority file / classification scheme / thesaurus。
3. 让词表关系（等价/层级/关联）服务于检索与浏览。

## 输出结果
- 统一语义层（vocabulary layer）

## 适用边界
- 词表建设需要治理与演进，不能一次性完工。

## 常见错误
- 只做页面分类，不做内容描述与词表管理

## 关联模板
- 元数据字段表 + 词表关系表

## 下游使用建议
- 作为 Stage-2：当系统跨多子站/多团队时，优先引入词表作为一致性底座。
