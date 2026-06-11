# 第一阶段核心业务产物清单（v0.1）

## 目的

这份清单用于作为第一阶段（产品 / 需求）的统一业务产物基准。

它服务两个目标：

1. 作为 Phase-1 Skills 说明层的基准，回答“第一阶段走完到底应该产出什么”。
2. 作为各 Stage Skill 输出层的挂靠清单，回答“当前阶段产出覆盖了哪些核心业务产物”。

---

## 1. 使用原则

这份清单不是要求单个 Stage 一次产出全部内容。

而是：

- Phase-1 四个子阶段共同覆盖这份清单
- 每个 Stage 对其中一部分承担主责任
- 后续审计时应能回答：
  - 哪些产物已形成
  - 哪些产物仍是草案 / provisional
  - 哪些产物尚未进入当前阶段

---

## 2. Phase-1 核心业务产物总表

### A. 用户与问题理解类

#### 1. 目标用户边界（User Boundary）
- 说明：目标用户是谁、不是谁
- 主责任阶段：Stage-01

#### 2. 用户分组（User Groups / Segments）
- 说明：关键用户群或关键角色分层
- 主责任阶段：Stage-01

#### 3. 用户故事 / 用户案例（User Story / User Case）
- 说明：用户目标、场景与主要意图
- 主责任阶段：Stage-01

#### 4. 问题清单（Problem List）
- 说明：当前问题/痛点的结构化列表
- 主责任阶段：Stage-01

#### 5. 机会清单（Opportunity List）
- 说明：值得继续结构化或验证的机会点
- 主责任阶段：Stage-01

---

### B. 需求结构类

#### 6. 需求全景（Requirements Panorama）
- 说明：需求整体结构，不是孤立条目
- 主责任阶段：Stage-02

#### 7. 主干活动 / 主流程（Backbone Activities / Main Flow）
- 说明：用户主干路径、核心活动链条
- 主责任阶段：Stage-02

#### 8. 需求结构图 / 故事地图（Requirements Structure / Story Map）
- 说明：需求的结构证据
- 主责任阶段：Stage-02

#### 9. 关键约束清单（Key Constraints）
- 说明：限制条件、边界、排除项
- 主责任阶段：Stage-02

#### 10. 初版优先级分组（Initial Priority Split）
- 说明：高价值优先 / 高风险待验证 / 可延后 等分组
- 主责任阶段：Stage-02

#### 11. 高风险待验证点（High-Risk Validation Point）
- 说明：后续验证必须重点关注的高风险假设或关键点
- 主责任阶段：Stage-02

---

### C. MVP 与切片类

#### 12. 完整体验闭环（Complete Experience Loop）
- 说明：产品希望支持的完整用户体验链
- 主责任阶段：Stage-03

#### 13. 最小可用体验闭环（Minimum Viable Experience Loop）
- 说明：MVP 真正要验证的最小闭环
- 主责任阶段：Stage-03

#### 14. MVP 定义（MVP Definition）
- 说明：当前最小可行边界
- 主责任阶段：Stage-03

#### 15. 首批切片（First Slice）
- 说明：第一批必须进入 MVP 的能力边界
- 主责任阶段：Stage-03

#### 16. 后续切片（Later Slices）
- 说明：后续可推进的能力边界
- 主责任阶段：Stage-03

#### 17. 暂缓项（Deferred Items）
- 说明：明确先不做的内容及原因
- 主责任阶段：Stage-03

#### 18. 切片依据（Slice Rationale）
- 说明：value / risk / dependency 视角下的切片理由
- 主责任阶段：Stage-03

#### 19. 待验证关键假设（Key Assumptions to Validate）
- 说明：必须在验证阶段继续检查的核心假设
- 主责任阶段：Stage-03

---

### D. 验证与修订类

#### 20. 验证对象 / 假设（Validation Target / Hypothesis）
- 说明：明确要验证什么
- 主责任阶段：Stage-04

#### 21. 验证方式（Validation Method）
- 说明：如何验证
- 主责任阶段：Stage-04

#### 22. 原型或等价验证材料（Prototype or Equivalent Validation Artifact）
- 说明：用于支持验证的低成本材料
- 主责任阶段：Stage-04

#### 23. 反馈 / 信号 / 结果（Feedback / Signal / Result）
- 说明：验证得到的关键观察或信号
- 主责任阶段：Stage-04

#### 24. 验证结论（Validation Conclusion）
- 说明：基于验证得到的结论
- 主责任阶段：Stage-04

#### 25. 决策状态（Decision State）
- 说明：Go / No-Go / Revise
- 主责任阶段：Stage-04

#### 26. 修订建议（Revision Recommendations）
- 说明：应如何回灌前序阶段
- 主责任阶段：Stage-04

#### 27. 设计 / 架构 handoff 包
- 说明：交给 design / architecture 的最终产品/需求阶段输出包
- 主责任阶段：Stage-04

#### 28. Unified Product Pack
- 说明：在 Stage-04 完成后，把 Phase-1 分散产物收敛成一个 PRD-equivalent 的项目级产品包
- 主责任阶段：Phase-1 completion / post-Stage-04 convergence

---

## 3. User Flow 在这份清单中的位置

当前不单独把 `User Flow` 作为一个完全独立的固定产物文档。

它在当前体系中主要吸收在：

- `主干活动 / 主流程`
- `需求结构图 / 故事地图`
- `完整体验闭环`
- `最小可用体验闭环`

也就是说：

> User Flow 的语义已经存在，  
> 但目前作为结构证据和体验闭环的一部分来表达，而不是独立文件。

---

## 4. 审计时的最小判断方式

对每个产物项，审计时至少判断：

- `missing`
- `draft`
- `provisional`
- `approved`

如果某项当前阶段不负责正式形成，也应明确：

- `not-in-stage`

---

## 5. 当前结论

第一阶段的核心业务产物，不应再只通过各 Stage 的零散文档去隐式推断。

应该统一以本清单为基准：

- 说明层引用它
- 输出层挂靠它
- 审计层检查它
