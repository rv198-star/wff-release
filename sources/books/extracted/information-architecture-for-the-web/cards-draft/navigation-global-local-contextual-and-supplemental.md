# 导航系统：Global / Local / Contextual + Supplemental（地图、索引、指南…）

- 类型：模式
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Navigation Systems / Types of navigation systems）
- 摘要：嵌入式导航提供位置感与可达性；补充导航（sitemap/index/guide）提供替代路径与总览。

## 输入条件
- 大型信息环境中用户“迷路”或只能靠搜索

## 关键步骤
1. Global：每页可回到关键区域（含搜索入口）。
2. Local：支持探索当前区域（subsite）。
3. Contextual：基于关系的“see also”，支持联想学习。
4. Supplemental：sitemap/index/guide/wizard 等作为第二条路。

## 输出结果
- 多层导航体系（主路+辅路）

## 适用边界
- 过多导航工具会造成杂乱，需要节制并用数据迭代。

## 常见错误
- 只做 global，放弃 local 导致子站不一致

## 关联模板
- 导航系统分层图

## 下游使用建议
- 在 Stage-2 原型中要求至少覆盖 global/local/contextual 三类的最小实现。
