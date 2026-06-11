# IA 解剖：Top-down / Bottom-up / Invisible IA

- 类型：概念
- 适用阶段：架构定义
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（The Anatomy of an Information Architecture）
- 摘要：IA 既存在于“从上到下的结构”，也存在于“内容自身的结构与元数据”，并且大量 IA 决策对用户不可见但决定体验。

## 输入条件
- 团队默认“用户从首页进入”，忽略 deep-link 与搜索入口

## 关键步骤
1. Top-down：用全局分类/导航回答“我能在这里做什么”。
2. Bottom-up：通过内容结构、chunking、tagging 支持在深处也能找到路。
3. Invisible IA：把检索配置、索引范围、停用词、人工精选等当作 IA 决策管理。

## 输出结果
- IA 设计覆盖面清单（可见+不可见）

## 适用边界
- 过度依赖 bottom-up 会导致“标签泥潭”；过度依赖 top-down 会导致“深链迷路”。

## 常见错误
- 把搜索结果中的“人工编辑/精选”当作与 IA 无关的运营动作

## 关联模板
- Deep-link 入口检查表

## 下游使用建议
- 与导航压力测试卡组合：验证 deep-link 入场时仍可定位与探索。
