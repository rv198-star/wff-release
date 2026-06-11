# P3 Value-Bearing Runnable Delivery（v0.1）

状态：`WO-119A.09` 本地验证记录
日期：2026-05-03
所属工单：`WO-119A.09`
控制边界：`docs/governance/v1.3-product-flow-control-boundary-v0.1.md`
Stage Judgment Lens：`docs/governance/v1.3-stage-judgment-lens-v0.1.md`
英文镜像：`docs/phases/phase-3/p3-value-bearing-runnable-delivery-v0.1.md`

## 目的

本文定义 `v1.3.1` Phase-3 implementation 的 closure expectation。

P3 closure 必须证明 runnable delivery value，而不是只证明 code generation、endpoint existence 或 script-green packaging。

## Closure Rule

P3 只有在输出对以下内容做出实质判断时，才可以 close：

- runnable delivery value；
- core path usability；
- accepted P1/P2 truth 内的 implementation completeness；
- test meaning 和 assertion quality；
- runtime evidence strength；
- downstream continuation value。

Code volume、generated runtime green、unit-count pass、API shape existence、delivery-gate file presence 或 script pass 都只是 support signals。它们本身不足以构成 closure。

## Required Closure Statement

P3 closeout surface 应说明：

- 哪条 core path runnable，以及它为什么重要；
- 哪些 business behavior 已实际实现；
- 哪些 accepted P2 contracts 已满足或仍 review-bound；
- tests 证明了什么超出 status codes 或 schema shape 的内容；
- 哪些 runtime、persistence、migration、API、UI 或 infrastructure evidence 支持该 claim；
- downstream developer 或 Agent 可以从哪里安全继续；
- 哪些 evidence 缺失，以及它如何封顶 formal state。

## Failure And Routing

Findings 路由如下：

- `源头事实缺口`（`source-truth-gap`）或 `产品/规格缺口`（`product-spec-gap`）-> 当 implementation 会被迫编造 business truth 时返回 P1 / pre-P1；
- `架构缺口`（`architecture-gap`）-> 当 implementation 需要 design changes 时返回 P2；
- `实现修补`（`implementation-patch`）-> P3 remediation；
- `证据缺口`（`evidence-gap`）-> 当 runtime/test evidence 缺失或薄弱时返回 P3。

如果 P4 还需要猜测 behavior 是否真实、assertions 是否 meaningful，或 runtime path 是否真的工作，则 P3 尚未 value-bearing closed。

## Agentic Implementation Loop Rule

即使 optional dispatch 被关闭，P3 也必须输出默认 Agentic implementation-loop surface：

- `agentic-implementation-loop.json`；
- `agentic-implementation-loop.md`。

这个 loop surface 必须选择 value / risk implementation slices，定义 bounded execution / remediation stop conditions，标出 service-boundary / test-meaning / runtime-evidence value 的 TVG checkpoints，并把 implementation bindings 连接到 runtime evidence expectations。

该 artifact 不替代 strict-runtime proof；strict-runtime proof 也不替代 Agentic implementation-value judgment。

## Default Business Behavior Authoring Rule

对 `v1.3.6.10`，`business-behavior-authoring-plan` 是 service / repository / unit business bodies 的 default P3 mainline pre-file-write authoring context。

Workflow supplies order/context/evidence：phase order、OpenAPI/runtime spec assembly、P1/P2 source bridge loading、file placement、strict-runtime execution 和 claim ceilings。Agentic/default authoring owns business behavior plan：operation intent、required context、read/write semantics、state/conflict policy、repository effects、audit/event effects、semantic owner、response mapping 和 unit-test obligations 必须在 renderer file write 前完成。

Evidence caps claims：必须通过 focused tests、GEO + PetClinic strict-runtime 和人工 Review 封顶 claim。plan 存在、generated files 存在或 script pass 都不足以证明 generated-artifact quality。

Selected-module bundle remains non-default。不得把 `--module-synthesis-bundle`、selected-module synthesis 或 F5/F6-style gate stacks 当成默认 P3 business-depth mechanism。

## 行动卡中心化主线规则

对 `v1.3.6.11`，默认 P3 code generation 必须使用以下主轴：

`P2 component-action-card-obligation-matrix -> P3 implementation action cards -> action-card execution map -> service/repository/unit code`。

当 `action-card-execution-map.json` 存在时，`business-behavior-authoring-plan` 不再是第二套 business-truth layer；默认主线不得把它作为持久 review artifact 或 truth surface 输出。任何 compatibility projection 都只能留在内存中，并从属于行动卡主轴。Renderer helper code 可以做机械 lookup、merge 和 error mapping，但不得脱离行动卡主轴独立推导 business owner、state、audit、repository effect 或 test obligation semantics。

生成的 service / repository / unit outputs 应能回溯到 `action_card_id`、action-card step / operation、ACD level、source refs 和 required tests。不得通过删除行动卡减负；减负对象是行动卡主轴周围重复的 plan/helper 叙事，同时必须保留 strict-runtime evidence 和人工 Review。

## Pointer-Only Action-Card Surface Rule

对 `WO-119F.12` / `v1.3.6.12`，默认持久 `action-card-execution-map.json` 是 pointer-only action-card surface。`source_refs / required_tests must not be persisted in default map`；rich context stays in-memory，用于 business-behavior compatibility projection 和 service / repository / unit scaffolding。

do not restore business-behavior-authoring-plan.json，不得恢复 F.11 重型 execution map 作为默认 review surface，也不得新增另一个默认持久 rich-context artifact。Generated quality 仍需要 strict-runtime evidence 和人工 Review；pointer-only slimming 本身不是 material generated-quality claim。

## Agentic Semantic Authoring Rule

对 `WO-119F.13` / `v1.3.6.13`，P3 默认生成必须在 service / repository / unit file write 前创建 in-memory Agentic semantic decision。

Workflow 负责 phase order、context assembly、file placement 和 evidence commands。Agentic 负责 owner / aggregate / invariant / value-rule / failure-path / test-intent 判断。Templates / TVG 可以使用 `p3-agentic-semantic-authoring-question-set-v0.1.zh-CN.md` 提出深度问题，但不得提供答案。Evidence / Gates 证明 runtime/test closure 并封顶 claims；不得创造内容真值。

默认持久面继续保持 F.12 pointer-only：不得恢复 `business-behavior-authoring-plan.json`，不得把 `action-card-execution-map.json` 重新扩成 rich context artifact，也不得新增替代性默认重型 artifact。`not-declared`、`review-bound` 和 generic `business invariants` 都不是可接受的语义答案；如果上下文不足，应保持 review-bound 或 return upstream，而不是让脚本决定。

## Project Implementation Convention Rule

对 `WO-119F.14` / `v1.3.6.14`，P3 默认生成必须在 F.13 semantic decisions 之前、service/repository/unit file write 之前，合成 in-memory project implementation conventions。

输入：

- 从 P2 source-backed outputs 派生的 P2 project-language handoff
- `tech-stack-decision.yaml`
- 内存中的 action-card rich context
- 仅在 frontend/UI surfaces 存在时使用的可选 UI/UX surface context

Conventions 指导 naming、code、design、test 和可选 UI/UX posture。它们不得持久化成替代性的 rich truth artifact。Evidence / Gates 可以报告 `mechanical_owner_name_count`、`mechanical_aggregate_name_count`、`forbidden_name_residue_count`、convention drift 和 claim ceiling，但不得产生命名答案。

## Agentic Module Implementation Brief Rule

对 `WO-119F.15` / `v1.3.6.15`，P3 默认生成必须在 service/repository/unit file write 前合成 in-memory `phase3-agentic-module-implementation-brief.v1`。

Module brief 消费 action-card rich context、Agentic semantic decisions、project implementation conventions、OpenAPI/runtime specs 和 selected stack context。Agentic 负责 module implementation strategy：module purpose、operation grouping、aggregate/invariant model、service-flow strategy、repository-effect strategy、transaction/audit/auth/error posture 和 unit-test strategy。

Workflow/scripts 只能装配 context、render files、放置 trace、执行 verification、记录 metadata 和封顶 claims。Renderer helper 必须保持 mechanical；当 module brief 存在时，不得独立决定 service flow、repository effect 或 unit-test intent。

如果质量失稳，必须先分类失败：context insufficiency、Agentic judgment issue、renderer mapping issue、evidence issue 或 environment issue。只有证据要求时，才允许增加最小 mechanical fallback；fallback 必须 evidence-backed、deletion-conditioned，且不得决定 business truth。不得恢复 `business-behavior-authoring-plan.json`，不得扩胖 `action-card-execution-map.json`，不得新增默认 rich-context artifact，也不得恢复 F5/F6 selected-module gate stack。

## Action Card Direct Implementation Driver Rule

对 `WO-119F.16` / `v1.3.6.16`，P3 默认生成必须在 service / repository / unit file write 前合成 in-memory `phase3-action-card-direct-implementation-driver.v1`。

Action Card Direct Implementation Driver 的含义是：Action Card obligations directly drive service/repository/unit generation。Service body 消费 service execution steps；repository body 消费 repository effect steps；unit tests 消费 unit assertion obligations。Failure mapping 和 audit/event posture 在存在时也应来自 driver。

F.13/F.14/F.15 are supporting inputs。它们可以补充 owner / aggregate / invariant 解释、project conventions、命名、代码姿态、module grouping 和 implementation strategy，但不得绕过或替代 Action Card obligations 作为 primary business-obligation source。

Driver 不得变成默认持久 artifact。不得恢复 `business-behavior-authoring-plan.json`，不得扩胖 `action-card-execution-map.json`，不得新增替代性的 rich-context artifact，也不得恢复 F5/F6 selected-module gate stack。Evidence 可以证明 direct consumption、runtime behavior、quality score 和 claim ceilings；不得创造 business content。

## Repository Audit Event Domain Sharpening Rule

对 `WO-119F.17` / `v1.3.6.17`，P3 默认 repository / audit / event 生成必须继续 F.16 的 Action Card direct-driver 路线，并在 file write 前合成 repository domain effects、state transition effects、audit/event effects 和 failure effect boundaries。

Agentic 从 Action Card obligations、operation semantics 和 runtime failure specs 中负责这些 domain-effect 判断。Renderer helper 只能把 effects 机械落位到 service/repository/unit files；不得把 generic repository 或 audit/event language 当作 primary content truth。

对 `WO-119F.17.2`，如果已有 `trigger_events`、`domain_event_models` 或 `domain_event_catalog`，P3 应优先消费它们，再使用 fallback event-name synthesis。Generated comments 可用 `action-card-domain-event-modeling-effect` 暴露 producer、consumer、trigger、payload、timing、idempotency。P3 不得发明新的 P2 event catalog，也不得新增默认持久 event-model artifact。

F.17 不是性能优化（not a performance optimization），也不是 P1/P2/P4 expansion（not a P1/P2/P4 expansion）。不得恢复 `business-behavior-authoring-plan.json`，不得扩胖 `action-card-execution-map.json`，不得新增 replacement repository/audit/event rich artifact，不得恢复 F5/F6 gate stacks，也不得添加 case-specific branches。

## 本地验证问题

如果本文和 P3 skill mirror 明确说明 P3 closure 是 runnable value 与 evidence-backed behavior，而不是 code 或 script completion，则 `WO-119A.09` 完成。
