# Stage-02 自测案例（审计镜像）— 从 Stage-01 provisional handoff 到结构化需求全景

## 1. 测试目标

用 Stage-01 那份餐馆老板案例的 provisional handoff 来验证 Stage-02 是否能够：

- 保留上游不确定性
- 形成真正的需求全景，而不是平铺条目
- 满足 hard diagram / structure gate
- 给 Stage-03 提供可切片的 handoff，而不是伪结构输入

---

## 2. 模拟上游输入

沿用 Stage-01 dry-run 的输出，包括：

- 用户群边界草案
- User Case / User Story 初稿
- 结构化问题/机会清单
- assumptions / open questions
- provisional 状态保留

---

## 3. 预期 Stage-02 行为

### 3.1 预期分析焦点
- 建立产品/需求全景
- 区分目标、活动、任务、约束
- 输出一个“整体结构”，而不是只整理故事条目
- 至少识别一个后续验证重点

### 3.2 预期 provisional 行为
- 不能把上游未确认的主要用户边界静默升级成确认事实。
- 如果结构建立依赖这些不确定假设，必须显式保留。

### 3.3 预期图示行为
- 必须有 `story-map` 或 `requirements-structure`。
- 若没有结构图示或结构仍是平的，应判 FAIL。

---

## 4. 预期最小输出结构

至少应包括：

- 目标
- 主干活动
- 任务结构
- 关键约束
- 初版优先级分组
- 高风险验证点
- 图示 / 结构证据元数据
- 若仍有不确定性，则要保留 assumptions / open questions / provenance

---

## 5. 预期验收判断

### PASS 条件
- 有整体结构
- Stage-03 能据此继续切片
- 上游 provisional 不确定性被保留

### FAIL 条件
- 只是条目清单
- 没有结构证据
- 缺关键约束
- provisional 假设被静默当成确认事实
