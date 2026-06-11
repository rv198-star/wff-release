# 组织方案：Exact vs Ambiguous（已知项检索 vs 探索式浏览）

- 类型：方法
- 适用阶段：架构定义
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Organization Systems / Exact vs Ambiguous）
- 摘要：精确组织适合已知项查找；模糊组织支持探索与联想学习，但更难设计维护。

## 输入条件
- 需要为同一内容同时支持“我知道我要什么”和“我还不确定”两类用户行为

## 关键步骤
1. 为已知项检索提供 exact schemes（字母/时间/地理等）。
2. 为探索与学习提供 ambiguous schemes（主题/任务/受众/混合）。
3. 组合多个组织方案，避免单一视角锁死。

## 输出结果
- 一套混合组织策略（多路径）

## 适用边界
- exact schemes 往往要求用户知道正确名字；对新手/跨文化场景可能失效。

## 常见错误
- 只做 exact（导致“不知道术语的人找不到”）或只做 ambiguous（导致维护成本爆炸）

## 关联模板
- 组织方案选择矩阵（用户意图×内容特性）

## 下游使用建议
- 用于 Stage-2 信息架构图审查：至少有一条已知项路径 + 一条探索路径。
