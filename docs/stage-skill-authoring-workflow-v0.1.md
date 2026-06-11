# Stage Skill Authoring Workflow（v0.1）

## 目的

这份文档用于定义一个 **专门适用于本仓库** 的 Stage Skill 编写流程。

如果需要一个更高层、贯穿“准备素材 → 编写 → 审计 → 复盘 → 交接”的项目级入口，参见：

- `skills/wff-meta-stage-skill-construction-lifecycle/SKILL.md`
- `docs/stage-skill-construction-lifecycle-reference-v0.1.md`

它要解决的问题不是“如何一般性地写一个 Skill”，而是：

- 面对 8 本已拆书素材 + 文档库素材 + PM Skills + Skill authoring 官方/基准参考源 + 高重复率 + 多约束条件时
- 如何避免即兴写作、素材堆砌、重复吸纳、规则漂移
- 如何把大量上游素材稳定地转成 Stage Skill，而不是被素材反向牵着走

这份流程文档的目标是：

> 让 Stage Skill 的编写变成 **目标驱动、选材受控、证据可追、规则先行、逐层收束** 的过程。

补充目标：

- 在需要人类审计时，允许为英文运行时主文件生成独立的中文审计镜像文件
- 但不把中英双语混进同一个运行时文件
- 并在发布阶段默认移除不必要的中文镜像文件

这不是单一 Stage Skill 的局部技巧，而是对项目级语言原则的执行：

- 英文优先服务 AI / runtime / stable canonical assets
- 中文优先服务 human audit / review / governance alignment

---

## 1. 为什么不能直接开始写

当前仓库的上游资产已经具有以下特征：

1. **素材量大**
   - 已有多本“阶段性完成”的拆书成果
   - 还有文档库抽取物与 merge / promotion / absorption 结果

2. **高重叠**
   - 多个主题包会同时覆盖：需求分析、用户研究、MVP、验证、协作边界
   - 同一能力点往往在不同书、不同模板、不同公司文档里重复出现

3. **参考源异质性强**
   - 有方法素材
   - 有企业文档库素材
   - 有 PM Skills 这种前台 intake / facilitation 参考
   - 还有 Skill authoring 官方/基准参考源（用于约束 SKILL 本身的结构和写法）

4. **约束强**
   - 不是写一篇方法总结，而是写带：
     - contract
     - gate / refusal
     - provisional inference
     - handoff
     - diagram evidence
      - provenance / verification
      的 Stage Skill

5. **人类审计需求真实存在**
   - 英文运行时主文件对结构稳定有利
   - 中文独立镜像文件对人类审计更友好
   - 发布包又不应被审计辅助文件无限膨胀

因此，Stage Skill 编写如果仍按“先看素材 → 边看边写”推进，几乎必然会出现：

- 看到素材多就想全收
- 重复内容混进正文
- 规则和方法混写
- 明明是 source card，却被写成 canonical rule
- 先写出漂亮结构，最后才发现 gate 对不上

---

## 2. 工作流总原则

Stage Skill 编写必须遵循：

> **先目标，后选材；先约束，后内容；先结构，后素材；先缺口记录，后补桥接。**

四个反方向都应避免：

- 不要先融合再定义 Skill
- 不要先汇总所有卡片再决定规则
- 不要先写“看起来完整”的正文再补 gate
- 不要因为素材重复就强行 over-merge

---

## 3. 标准编写流程（7 步）

> 每一步都应该产出一个中间文档或中间结果，避免“脑中完成”。

## Step 1：先冻结目标 Stage Skill

**建议中间产物：** `stage-charter.md`

先回答：

- 这个 Skill 属于哪个阶段？
- 它解决什么问题？
- 它的上游输入是什么？
- 它的下游 handoff 是谁？
- 它最重要的 gate / refusal / diagram evidence 落在哪里？

若以上问题仍答不清，不允许开始 source-card 级别选材。

> 目标 Skill 先行，素材只能服务 Skill，不允许 Skill 被素材倒推出来。

---

## Step 2：先绑定 policy stack，再碰素材

**建议中间产物：** `source-register.md`

这一步除了绑定 policy stack，还要把候选来源按层分级：

- Tier 1：repo policy / stage governance / hard constraints
- Tier 2：Skill authoring 官方/基准参考源
- Tier 3：直接相关的书本主题包 / 文档库素材 / PM Skills
- Tier 4：补充性背景 / supporting context

每个来源必须写清：

- why included
- expected role
- whether it can define hard rule / only reference

其中 Tier 2（Skill authoring 官方/基准参考源）主要包括：

- Anthropic / Claude Skills 官方格式与编写规范
- `skill-creator` 一类 authoring discipline 参考
- 已验证的 skill-authoring workflow 参考（如 PM Skills 的 authoring workflow）

这层来源不负责定义产品/需求方法内容，但负责约束：

- `SKILL.md` 应如何组织
- 触发语义 / frontmatter / section discipline
- 技能写作中哪些是 runtime instruction，哪些是 reference note

在任何 Stage Skill 正式编写前，先绑定现有约束文档：

- `docs/phases/phase-1/phase-1-reference-priority-and-intake-basis-v0.1.md`
- `docs/phases/phase-1/phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
- `docs/phases/phase-1/product-requirements-gates-and-minimum-admission-v0.1.md`
- `docs/phases/phase-1/product-requirements-diagram-evidence-rubric-v0.1.md`
- `docs/phases/phase-1/phase-1-skill-authoring-basis-v0.1.md`

这一步的意义是：

- 先冻结 intake / provisional / gate / handoff 的共性约束
- 防止作者一边看素材一边偷偷改规则

没有 “why included” 的来源，默认不进入后续作者视野。

---

## Step 3：按主题包选材，而不是按单卡撒网

**建议中间产物：** `rule-cards.md`

**REQUIRED META-SKILL:** Use `wff-meta-source-unit-coverage-ledger` before claiming source coverage is understood.

**建议中间产物（新增）：** `source-unit-coverage-ledger.md`

优先从主题包（bundle）选材，而不是从全仓单卡随手抓。

建议顺序：

1. 先选 **2–3 个最相关 source bundles**
2. 再进入 bundle 内部筛卡
3. 暂不把其余包拉进来

原因：

- 当前主题包已经被审查为“阶段性完成”的稳定参考资产
- 主题包级使用可以显著降低素材规模压制
- 可以避免“一开始就全拉进来导致结构失控”

进入 bundle 后，不要马上写 prose，而要先把候选内容压成“原子规则卡”：

- `rule_id`
- `statement`
- `type`（requirement / prohibition / heuristic / exception）
- `source`
- `source_tier`
- `confidence`
- `applies_to_stage`

规则卡必须尽量保持“单一断言”，避免一张卡塞入多个命题。

但要注意：

> `rule-cards.md` 不是素材库单元级 coverage ledger 的替代品。  
> 前者服务当前 Stage 的规则收束，后者服务“素材覆盖审计与遗漏理由”的独立判断。

推荐最小顺序调整为：

1. 先选最相关 source bundles
2. 再建立 `source-unit-coverage-ledger.md`
3. 再从 ledger 中抽 rule cards
4. 再进入 merge-decisions / binding-matrix / runtime prose

---

## Step 4：筛卡时必须做 4 类归属，不允许“全部有用就都放进去”

**建议中间产物：** `merge-decisions.md`

每张候选卡必须落入以下之一：

1. `contract-candidate`
   - 直接影响输入 / 输出 / 边界 / refusal / gate

2. `execution-support`
   - 适合进入 SOP / checklist / review checkpoint

3. `reference-only`
   - 有启发，但不应进入正式 Skill contract

4. `gap-signal`
   - 说明缺少 bridge / template / rule，但当前卡本身不能直接进入 Skill

这一步的本质是：

> **先做归类，再做吸纳。**

否则所有素材都会以“可能有用”的名义进入正文。

此外，这一步必须显式处理“重复”与“冲突”：

- 对语义重复的 rule-cards 做 cluster
- 记录哪些是 corroboration、哪些可以 keep-separate-but-linked
- 不允许因为“像”就强行 merge

并且：

- 在进入正文前，必须已经有素材库单元级 ledger 或等价判断
- 不允许只凭 bundle 级印象声称“这个来源已经覆盖”

推荐固定 precedence：

1. Repo policy
2. Skill authoring official / benchmark constraint
3. Document-library mandate / extracted governance constraint
4. Stage template contract
5. PM Skills interaction pattern / book-derived guidance
6. Stylistic preference

未解决冲突不得拖到正文阶段再临时决定；应在本步骤中变成：

- refusal clause
- provisional clause
- explicit split decision

---

## Step 5：缺口先记录，不立刻补文档

当发现现有素材不够时，默认动作不是马上写 bridge artifact，而是先记录：

- 缺什么接口
- 缺什么规则
- 缺什么模板字段
- 缺什么 handoff 定义

只有当该缺口**真实阻断 Stage Skill 编写**时，才允许：

- 新增 bridge artifact
- 新增 overlay package 内容
- 定向补抽或补融合

这条规则非常关键，因为当前最容易出现的反模式就是：

> 一写 Skill 就想顺手重构整个素材层。

如果缺口已足以阻断 Skill 编写，可以新增 bridge artifact；否则只记录，不补写。

---

## Step 6：固定编写顺序，不允许跳写

**建议中间产物：** `binding-matrix.md`

在真正写 `skill-contract.md / stage-sop.md / output-template.md / source-cards.md` 之前，先做绑定矩阵：

- 哪条 canonical rule 绑定到 artifact section
- 哪条绑定到 gate
- 哪条绑定到 refusal
- 哪条绑定到 provisional
- 哪条绑定到 handoff
- 哪条绑定到 diagram
- 哪条绑定到 skill-authoring structure / trigger / section wording

只有绑定矩阵完成后，才允许起草正式 Stage Skill 文档。

每个 Stage Skill 必须固定按以下顺序写：

1. `skill-contract.md`
2. `stage-sop.md`
3. `output-template.md`
4. `source-cards.md`
5. 如进入人类审计轮次，再生成对应 `*.zh-CN.md` 审计镜像文件

理由：

- contract 决定边界和 rule precedence
- SOP 决定过程状态流
- output-template 决定交付形态与 provenance
- source-cards 只在最后作为“方法资产绑定层”进入

如果倒过来写，就会出现：

- 先选了很多卡
- 再拼出很多内容
- 最后发现 contract / gate / refusal 根本对不上

在正式 drafting 时，应尽量使用规范性措辞：

- `MUST`
- `SHOULD`
- `MUST NOT`

减少模糊措辞（如“可以考虑”“通常建议”）在 hard gate 区域出现。

中文审计镜像文件的规则：

- 逐文件对应，不混写
- 用于解释与审计，不新增英文主文件不存在的硬规则
- 若中英语义冲突，以英文运行时主文件为准，并回到 authoring control 层修复镜像漂移

---

## Step 7：Stage Skill 不做 canonical 素材重写，只做受控吸纳

**建议中间产物：** `verification-report.md`

在 Skill 编写时，必须遵守以下边界：

- 不重写已“阶段性完成”的 source bundle
- 不全文复制 source cards 进入 Skill 正文
- 不把 reference-only 内容升级成 canonical gate rule
- 不把多个来源“看起来类似”的资产强行 merge 成一个规则
- 不把 PM Skills 或书本方法内容越级当成 Skill authoring 官方结构规范
- 不把中文审计镜像文件当成最终运行时 canonical 主文件

Stage Skill 的角色不是“再造一个大杂烩总文档”，而是：

> 把稳定上游资产，受控地映射为当前阶段的可执行 contract / SOP / output / source-cards。

写完后至少做 4 类验证场景：

1. missing-input case
2. overlap/conflict case
3. provisional inference case
4. handoff case

如果存在中英双轨文件，再加第 5 类验证：

5. bilingual audit parity case（中英镜像是否语义一致）

如果两个审查者面对同一输入会得到不同 gate 结论，应返回 Step 4 或 Step 6，而不是继续润色正文。

---

## 4. 本仓库特有的 Authoring Checkpoints

每次正式写一个 Stage Skill，都至少经过这 5 个检查点：

### Checkpoint A：目标冻结
- 问题域已定义
- 上下游已定义
- gate 焦点已定义

### Checkpoint B：选材受控
- 只选了最小相关 bundles
- 没有把所有已完成主题包都拉进来

### Checkpoint C：规则先行
- intake/provisional/gate/handoff 已绑定 policy stack
- 没有边写边改总规则

### Checkpoint D：缺口外置
- 缺口已记录
- 未因缺口失控地扩写桥接资产

### Checkpoint E：下游可消费
- output-template 的字段足以供下游阶段使用
- provisional 内容的边界清楚
- diagram evidence / handoff package 清楚

### Checkpoint F：规则可追溯
- 正文中的 hard rule 能回溯到明确的 rule card / binding
- 不存在“写的时候临时想到”的无来源硬规则

---

## 5. 禁止的反模式

### 反模式 1：把所有 source cards 摘要一遍
这只会制造“看起来努力了”的正文，不会提升 Stage Skill 的可执行性。

### 反模式 2：因为素材重复，就做大一统 over-merge
重复 ≠ 可以合并。很多重复只是“互相 corroborate”，不是“应该只剩一条”。

### 反模式 3：先凭经验写 Skill，再回头找素材背书
这会让 source cards 退化成装饰性引用。

### 反模式 4：看到缺口就重开方法治理工程
Stage Skill 编写阶段不是无限开新治理文档的阶段。

### 反模式 5：把 provisional / inferred 内容静默升级为 confirmed input
这是当前最危险的治理滑坡。

### 反模式 6：在 drafting 阶段才解决冲突
这说明 merge-decisions / binding-matrix 阶段没有做完。

---

## 6. 与已有文档的关系

本文件补的是“**如何可靠地写 Stage Skill**”，因此它与已有文档的关系如下：

- `phase-1-reference-priority-and-intake-basis-v0.1.md`
  - 定义参考法源优先级
- `phase-1-intake-state-machine-and-provisional-inference-policy-v0.1.md`
  - 定义 intake / blocked / provisional / review / gate-pass 状态
- `product-requirements-gates-and-minimum-admission-v0.1.md`
  - 定义每个子阶段的 required/optional/gate
- `phase-1-skill-authoring-basis-v0.1.md`
  - 定义第一阶段 4 个 Stage Skills 的共性编写基座
- **本文件**
  - 定义：在大量上游素材和高约束场景下，作者实际应按什么流程写 Skill

补充说明：

- `from-source-index-to-skill-design.md` 解决“如何从索引进入 Skill 设计”
- 本文件进一步解决“进入设计之后，如何在高重复率与强约束条件下可靠写出 Stage Skill”
- `findings.md` 中已记录：Anthropic `skill-creator` 与 PM Skills 的 `skill-authoring-workflow` 应视为 authoring discipline 参考源，而不是 runtime 方法内容源

---

## 7. 一句话结论

当前编写 Stage Skill 的正确方式不是：

> 看素材很多，于是边看边写、边写边融合。

而是：

> **先冻结目标与规则，再按主题包最小选材、四类筛卡、缺口外置、固定顺序编写，让素材服务 Skill，而不是让 Skill 被素材规模和重复率拖走。**
