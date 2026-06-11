# 导航压力测试：跳过首页，空降到内部页

- 类型：检查清单
- 适用阶段：设计收敛
- 来源：`sources/books/original/phase-02-design-architecture/Information_Architecture_For_The_Web.md`（Navigation Systems / navigation stress test）
- 摘要：用“中途入场”检验导航：能否定位、能否预测链接、能否找到上级与下一步。

## 输入条件
- 需要验证 deep-link 现实下的可用性

## 关键步骤
1. 忽略首页，随机进入站点中间页面。
2. 判断当前位置：所在大区/父页面/与整体关系。
3. 预测下一步：链接是否足够描述、是否可区分。

## 输出结果
- 导航缺口清单（定位/预测/回退路径）

## 适用边界
- 需要覆盖不同类型页面（内容页/列表页/工具页）。

## 常见错误
- 只测 happy path，从首页按规划路径走

## 关联模板
- 压力测试记录表

## 下游使用建议
- 可作为 Stage-2 交付 gate：至少对 10 个内部页跑一轮。
