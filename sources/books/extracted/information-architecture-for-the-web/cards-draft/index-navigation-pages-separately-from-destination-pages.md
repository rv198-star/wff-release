# 区分 navigation pages 与 destination pages：避免结果集被导航页淹没

- 类型：方法
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Search Systems / Navigation versus destination）
- 摘要：用户搜索通常要去目的内容页；把导航页混进索引会污染结果。

## 输入条件
- 搜索结果充斥列表页/分类页/索引页，用户找不到具体内容

## 关键步骤
1. 定义 destination 与 navigation 的边界（允许少量重叠）。
2. 将 navigation 页降权、分区或不纳入默认结果。
3. 上线前用真实查询回放测试（避免 80% 噪声）。

## 输出结果
- 更高的精确度与更快的到达路径

## 适用边界
- 某些导航页也有价值（如“总览”页），需以数据校准。

## 常见错误
- 简单“全站全文索引”且无治理

## 关联模板
- 搜索结果质量审计表

## 下游使用建议
- 作为 Stage-2 搜索上线 gate：必须提供 destination 优先策略。
