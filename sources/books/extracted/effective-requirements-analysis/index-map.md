# 有效需求分析（第2版） Index Map

## Scope
- Source: `sources/books/original/有效需求分析（第2版）.md`
- Extraction depth: `index-map` -> `knowledge-card-draft` -> `stage-guidance-draft`
- Primary stage focus:
  - `requirements-analysis`
  - `product-discovery`
  - `architecture-governance`
  - `method-governance`
- Primary downstream use:
  - future stage skills for B 端需求分析、需求规格整理、业务建模、场景拆解、非功能需求分析、需求治理与裁剪

## Section map

| Section | Core problem solved | Stage | Type | Priority |
|---|---|---|---|---|
| 第1章 软件需求全景图 | 用价值需求 + 功能/数据/非功能三条主线建立 B 端需求分析总框架 | requirements-analysis | framework / boundary | very high |
| 第2章 日常需求分析 | 给出变更/优化需求的还原、补充、评估三步法与轻量模板 | requirements-analysis | method / template / anti-pattern | very high |
| 第3章 目标/愿景分析 | 将空洞目标转为问题/机会场景与问题卡片 | product-discovery | method / template | very high |
| 第4章 干系人识别 | 用相关度、影响度与风险识别关键干系人 | requirements-analysis | method / checklist / template | very high |
| 第5章 干系人分析 | 分析干系人关注点、阻力点与冲突，形成档案 | requirements-analysis | method / template / boundary | very high |
| 第6章 价值需求分析总结 | 把问题、干系人、负需求整合为价值需求分析整体流程 | requirements-analysis | framework / process | high |
| 第7章 业务子系统划分 | 用业务视角而非技术视角分解系统，控制复杂度 | requirements-analysis | method / boundary / template | very high |
| 第8章 业务接口分析 | 定义子系统间业务接口的 Why/What/约束，而非直接做技术接口设计 | requirements-analysis | method / template / boundary | very high |
| 第9章 业务场景梳理 | 串讲业务流程识别→流程分析→场景识别→优先级排序 | requirements-analysis | process / framework | high |
| 第10章 业务流程识别 | 用主/变/支/管与端到端边界识别流程 | requirements-analysis | method / checklist | very high |
| 第11章 业务流程分析与优化 | 对业务流程进行优化与规则识别，生成可落地图示 | requirements-analysis | method / process | high |
| 第12章 业务场景识别 | 把流程拆成“角色：场景（动宾）”的独立业务场景 | requirements-analysis | method / naming rule | high |
| 第13章 业务场景分析 | 用场景-挑战-方案结构细化功能需求 | requirements-analysis | template / method | very high |
| 第14章 管理需求分析 | 从管理场景/管控点出发而非从报表格式出发 | requirements-analysis | method / template / anti-pattern | high |
| 第15章 业务报表分析 | 对业务报表项、口径、格式进行细化描述 | requirements-analysis | template / method | medium |
| 第16章 维护需求分析 | 从维护场景而非功能实现角度识别运维需求 | requirements-analysis | method / template | high |
| 第17章 领域建模 | 从问题域数据实体关系出发构建领域模型 | requirements-analysis | method / framework | high |
| 第18章 业务数据分析 | 细化数据构成、数据窗口、数据使用特点 | requirements-analysis | template / method | high |
| 第19章 质量需求分析 | 用逆向思维与场景化方法识别关键质量属性与质量场景 | requirements-analysis | method / template / anti-pattern | very high |
| 第20章 业务规则分析 | 识别和分类业务规则，明确约束与例外 | requirements-analysis | method / template | medium |
| 第21章 约束分析 | 区分项目约束与设计约束并明示对需求/方案的影响 | architecture-governance | boundary / template | high |

## High-value extraction targets
- 业务驱动需求思想：问题级需求优先于方案级需求
- 日常需求分析三步法：还原需求→补充需求→评估需求
- 变更/优化型需求分析模板
- 问题卡片模板
- 干系人列表 / 干系人档案模板
- 业务子系统划分与业务接口分析模板
- 业务流程识别（主/变/支/管）与端到端边界规则
- 业务场景命名与场景分析模板
- 关键质量属性列表与目标-场景-决策表
- 模板裁剪规则：不是每栏必填，而是按问题特征选用

## Skip or low-value sections
- 大量故事化案例中的情绪铺垫
- 出版信息、作者简介、推荐性叙述
- 不能转化为模板/规则/方法的长篇案例细节

## Extraction strategy notes
- Treat this book as a `requirements-playbook + template-governance + B-end analysis method` source.
- Priority cards should be:
  - template cards
  - boundary cards
  - decision-rule cards
  - anti-pattern cards
- Avoid extracting it as generic “需求分析百科” summary.
