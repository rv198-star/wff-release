# 有效需求分析（第2版） Stage Guidance Draft

## Goal
- 将《有效需求分析（第2版）》中面向 B 端系统的需求分析方法、模板和裁剪规则，重组为可供阶段 Skill 直接消费的 requirements playbook。

## Recommended methods
- 先把需求从方案级拉回问题级，再进入需求分析
- 对日常变更需求优先使用轻量模板，而不是完整 SRS
- 用干系人列表/档案显式管理相关度、影响度、关注点与阻力点
- 先按业务划分子系统，再分析业务接口与业务场景
- 非功能需求必须场景化，避免空洞定性与伪量化
- 所有模板都允许剪裁，禁止模板僵尸化

## By stage

### 需求调研 / 需求入口治理
- 重点卡：
  - `problem-level-over-solution-level.md`
  - `daily-change-demand-three-step-flow.md`
  - `lightweight-change-demand-template.md`
  - `value-frequency-prioritization.md`
- 目标：
  - 先澄清真实问题，再治理输入需求质量
  - 为 Backlog 和后续分析建立可消费条目

### 价值需求分析
- 重点卡：
  - `problem-card-template.md`
  - `stakeholder-list-template.md`
  - `stakeholder-profile-template.md`
- 目标：
  - 把目标/愿景、关键干系人、关注点和阻力点组织成上游价值包
  - 为范围控制和项目方向提供明确锚点

### 详细需求分析 / 需求架构整理
- 重点卡：
  - `business-subsystem-decomposition.md`
  - `business-interface-analysis-template.md`
- 目标：
  - 从业务视角分解复杂系统
  - 为功能、数据、接口分析提供稳定边界

### 非功能需求分析
- 重点卡：
  - `quality-scenario-template.md`
- 目标：
  - 用关键质量属性与具体场景表达非功能需求
  - 为架构设计与专项设计提供可落地输入

### 方法治理 / 裁剪治理
- 重点卡：
  - `template-as-a-tool-not-master.md`
- 目标：
  - 避免模板驱动的假完整性
  - 让模板服务分析，而不是取代分析

## Key decision rules
- 没有把方案级需求转写为问题级需求前，不应进入正式分析
- 日常变更需求默认优先使用轻量模板，不应直接套厚重 SRS
- 没有关键干系人识别与冲突判断，不应过早宣称范围稳定
- 没有关键质量属性与场景表达，不应宣称非功能需求已完成
- 当系统复杂度不高时，应显式允许裁剪子系统划分等任务

## Common mistakes
- 用户一提方案，团队就开始设计实现
- 用厚重文档掩盖需求理解不足
- 从技术实现维度组织需求，而不是从业务维度组织
- 非功能需求只写“高性能、高扩展、高可靠”
- 误把模板完整性当需求分析质量

## Required / useful cards
- `problem-level-over-solution-level.md`
- `daily-change-demand-three-step-flow.md`
- `lightweight-change-demand-template.md`
- `value-frequency-prioritization.md`
- `problem-card-template.md`
- `stakeholder-list-template.md`
- `stakeholder-profile-template.md`
- `business-subsystem-decomposition.md`
- `business-interface-analysis-template.md`
- `quality-scenario-template.md`
- `template-as-a-tool-not-master.md`

## Related source books
- `sources/books/original/有效需求分析（第2版）.md`
