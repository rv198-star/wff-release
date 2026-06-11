# Artifact Traceability Layer（v0）

## 文档目的

这份文档用于把“追踪层”正式立起来。

目标不是立即给出最终技术规范，而是先明确：

1. 为什么这个项目需要 Traceability Layer
2. 这一层要追踪哪些对象
3. 文档、编号体系、SQLite 在其中分别扮演什么角色
4. 当前最小可行落地方式是什么

---

## 一、为什么需要 Traceability Layer

在传统 ALM / PLM / Rational 一类工具中，很多追踪关系本来是被工具隐式托底的：

- 需求能追到设计
- 设计能追到接口与模块
- 模块能追到测试
- 变更影响能被查询

而在当前这个 AI-first、docs-first 的项目中，如果不把这层显式设计出来，就会出现：

- 需求与原型断开
- 原型与接口设计断开
- 接口与模块设计断开
- 模块与测试断开
- 变更后影响面不可追踪

因此：

> Traceability Layer 是整个 Skills 项目的核心基础设施之一。

---

## 二、追踪层要解决的问题

当前至少要支持三类追踪：

### 1. 阶段级追踪
回答：
- 上一阶段交给下一阶段的是什么
- 哪些产物是 handoff 包的一部分
- 哪些阶段 gate 已完成

### 2. 产出物级追踪
回答：
- 一个 `REQ-*` 对应哪些 `UI-*`、`API-*`、`MOD-*`、`TEST-*`
- 某个 UI 或模块能否回溯到原始需求

### 3. 变更影响追踪
回答：
- 当某个需求或原型变化时，会影响哪些设计、模块、接口、测试

---

## 三、当前推荐的最小追踪对象

当前建议先追踪这些对象：

- `REQ-*`：需求项 / 需求单元
- `FLOW-*`：用户流程 / 关键场景
- `UI-*`：页面 / 模块 / UI 区块 / 状态
- `API-*`：接口 / 契约
- `MOD-*`：模块 / 服务 / 组件
- `TEST-*`：测试项 / 测试用例 / 验证点

如有需要，后续再扩展：
- `RISK-*`
- `ASSUME-*`
- `MILESTONE-*`

---

## 四、文档与编号体系的角色

### 结论

> 文档仍然应当是 Source of Truth。编号体系必须显式写在文档中。

也就是说：

- 每个关键产出物中都应出现稳定 ID
- 每个关键产出物中都应出现基础关系字段

### 最小建议字段
- `id`
- `type`
- `status`
- `implements`
- `verifies`
- `depends_on`
- `feeds`
- `related_ui`
- `related_api`
- `related_module`
- `related_test`

这些字段不需要所有文档一开始都写满，但后续关键工件应逐步显式化。

---

## 五、SQLite 的角色

### 结论

> SQLite 适合做每项目一个的轻量 trace index，但当前不应成为唯一真相源。

### 推荐定位
- 每个项目一个 `trace.db`（名称可后定）
- 由脚本从文档和结构化关系中生成
- 用于快速查询上下游关系和做一致性检查

### 不建议当前做法
- 不建议现在就把 `.db` 当作唯一主数据源
- 不建议文档和数据库双向随意编辑

原因：
- 二进制文件不利于版本控制
- 很容易形成双真相源
- 当前阶段项目仍在定义结构本身，不宜过早把 DB 做成核心系统

---

## 六、当前推荐架构：文档为主，SQLite 为派生索引层

### Source of Truth
- Markdown / 结构化文档
- Artifact IDs
- 关系字段

### Derived Layer
- SQLite
- 查询脚本
- 一致性校验脚本
- 报告导出（JSON / Markdown / report）

### 这样做的好处
- 人类仍然能直接读文档
- AI 可以快速查询关系
- 可以逐步引入，而不是一上来造一个 ALM 平台

---

## 七、Prototype Traceability Pack 在其中的位置

Prototype Traceability Pack 可以视为 Traceability Layer 的一个子集，重点解决：

- `REQ` ↔ `FLOW`
- `FLOW` ↔ `UI`
- `UI` ↔ `API`
- `API` ↔ `MOD`
- `MOD` ↔ `TEST`

它尤其适合放在：

> 设计阶段后段 / 开发阶段前段

作为“已确认 HTML 原型”和技术设计之间的桥接包。

---

## 八、最小可行实现（v0）

当前不建议立刻做完整系统，而是建议按以下顺序逐步推进：

### Step 1：先统一编号体系
- `REQ-*`
- `FLOW-*`
- `UI-*`
- `API-*`
- `MOD-*`
- `TEST-*`

### Step 2：在关键文档中显式写出追踪字段
先从：
- 需求产物
- 原型相关产物
- 接口设计
- 模块设计
- 测试设计
开始。

### Step 3：做一个最小 Traceability Matrix / Mapping Table
优先支持：
- `REQ ↔ UI`
- `REQ ↔ API`
- `REQ ↔ TEST`

### Step 4：再引入 SQLite 派生索引层
通过脚本将文档中显式关系写入 SQLite，提供查询和校验能力。

---

## 九、当前不建议做的事

- 不建议立刻把 SQLite 做成唯一真相源
- 不建议一开始就构建完整 ALM 替代系统
- 不建议在追踪关系尚未显式写入文档时，就先做数据库建模

---

## 十、当前判断

### 当前最稳的项目级结论是：

1. Traceability Layer 必须进入项目级设计
2. 编号体系必须显式化
3. 文档仍然是当前真相源
4. SQLite 非常值得做，但当前应作为“每项目一个、可再生成的轻量索引层”
5. Prototype Traceability Pack 应作为 Traceability Layer 的关键子集在后续阶段设计中明确出现

---

## 一句话总结

> Traceability Layer 是整个 Skills 项目的核心基础设施之一；当前最合理的实现方式是“文档为真相源，SQLite 为每项目的可再生成轻量索引层”。
