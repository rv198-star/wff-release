# WFF 首读入口

这是本安装包的低上下文首读文件。
先用它选择入口，再决定是否展开完整 README、skill 目录、scripts 或 docs 树。

## 先选入口
| 当前任务 | 先用 | 再看 |
|---|---|---|
| 判断是否应该使用 WFF 并选择入口 | `skills/using-wff/SKILL.md` | WFF 入场判断、三个外部入口之一，或普通非 WFF 处理路径 |
| Start New Work：只有想法、聊天记录或零散材料 | `skills/wff-req-chat/SKILL.md` | P1 source input packet；包含 `wff-req` 时再看 `skills/wff-req/SKILL.md` |
| 稳定需求 -> PRD | `skills/wff-req/SKILL.md` | 生成的 P1 PRD 和评分报告 |
| 内部续接：WFF P1 -> 工程设计，不是外部直达入口 | `skills/wff-arch/SKILL.md` | WFF P1 真相被接受后生成 P2 `engineering-spec-pack.md` 和 `phase-3-implementation-entry.md` |
| 内部续接：WFF P2 -> 实现和测试，不是外部直达入口 | `skills/wff-impl/SKILL.md` | WFF P2 handoff 后生成 P3 action cards、实现评审和验证报告 |
| 内部续接：WFF P3 -> 收口判断，不是外部直达入口 | `skills/wff-validation/SKILL.md` | WFF P3 evidence 存在后生成 P4 验证报告和 closure summary |
| 外部入口：code-backed existing-system assessment，用于有代码的旧系统、重构、迁移、扩容 | `skills/wff-x/SKILL.md` | PX 基线、真相状态、缺口、风险、目标包、安全网和路线建议；Related documents are supporting evidence，standalone documents are not enough |
| 按角色使用 | `docs/WFF-ROLE-AGENTS.zh-CN.md` | 角色适配输出，以及背后的 lifecycle skill |

## 首先只读三类文档
| 类别 | 先打开 | 用途 |
|---|---|---|
| 人类核心入口 | `README.md`、本文件；需要安装细节时读 `INSTALL-PACK-README.zh-CN.md`；使用角色时读 `docs/WFF-ROLE-AGENTS.zh-CN.md` | 理解 WFF、上手、选入口、判断任务路线 |
| 生成交接文档 | P1 PRD、P2 工程规格、P3 action cards / review、P4 closure summary、PX 基线/目标包 | 人通常需要关注的核心产物 |
| 证据和诊断 | 评分报告、验证台账、运行冒烟验证、目标测试报告、安装包审计 | 证明、排障和声明上限；按需读取 |

不要一开始就递归读取 `scripts/`、`docs/` 或 `reference-packages/` 下的全部文件。

## 包内文件
- `README.md`：面向用户的 WFF 公开首页。
- `INSTALL-PACK-README.zh-CN.md`：安装布局、根命令、支持目录规则和详细运行说明入口。
- `AGENTS.md`：面向 agent 的本安装包简短操作指引。
- `SKILL_INSTALL_PACK_MANIFEST.json`：准确列出包含的 skills、scripts、docs、references 和 profile metadata。
- pack_name: `wff-v1.5.3-skills-install-pack`
- install_set_id: `full-pack`
