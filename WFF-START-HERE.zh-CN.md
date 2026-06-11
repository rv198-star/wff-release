# WFF 首读入口

这是本安装包的低上下文首读文件。
先读它，再决定是否需要展开完整 README、skill 目录、scripts 或 docs 树。

## 先选入口
| 当前任务 | 先用 | 再看 |
|---|---|---|
| 只有想法、聊天记录或零散材料 | `skills/wff-req-chat/SKILL.md` | 包含 `wff-req` 时再看 `skills/wff-req/SKILL.md` |
| 稳定需求 -> PRD | `skills/wff-req/SKILL.md` | 生成的 P1 PRD 和评分报告 |
| PRD -> 工程设计 | `skills/wff-arch/SKILL.md` | P2 `engineering-spec-pack.md` 和 `phase-3-implementation-entry.md` |
| 设计 -> 实现和测试 | `skills/wff-impl/SKILL.md` | P3 action cards、实现评审、验证报告 |
| 实现 -> 收口判断 | `skills/wff-validation/SKILL.md` | P4 验证报告和 closure summary |
| 已有系统改造、重构、迁移、扩容 | `skills/wff-x/SKILL.md` | PX 基线、风险、目标包和安全网 |
| 按角色使用 | `docs/WFF-ROLE-AGENTS.zh-CN.md` | 角色适配输出，以及背后的 lifecycle skill |

## 首先只读三类文档
| 类别 | 先打开 | 用途 |
|---|---|---|
| 人类核心入口 | `README.md`、本文件；使用角色时读 `docs/WFF-ROLE-AGENTS.zh-CN.md` | 上手、选入口、判断任务路线 |
| 生成交接文档 | P1 PRD、P2 工程规格、P3 action cards / review、P4 closure summary、PX 基线/目标包 | 人通常需要关注的核心产物 |
| 证据和诊断 | 评分报告、验证台账、运行冒烟验证、全量目标测试报告、安装包审计 | 证明、排障和声明上限；按需读取 |

不要一开始就递归读取 `scripts/`、`docs/` 或 `reference-packages/` 下的全部文件。

## 运行预期
- P3 严格运行验证预期会占据主要运行时间；已保留 v1.4/v1.4.1 发布证明中，P3 约占已记录阶段耗时的 `96%`。
- 主耗时来自全量目标测试里的 SQL / contract / scenario / replay 证据，不是 Docker build 单独造成。
- 默认迭代可以先用 `--validation-level fast` 或 `--validation-level focused` 做快速验证或聚焦验证；这两个档位只跑关键目标证据，且不会自动执行运行冒烟验证，除非显式传入 `--run-runtime-smoke`。
- 快速验证或聚焦验证只适合诊断和局部修复检查，不能替代发布证明所需的严格全量验证。
- 只有严格全量验证完成全量目标测试、运行冒烟验证、启动服务冒烟验证和交付门禁后，才可以支撑交付就绪或发布证明。

## 包内文件
- `README.md`：安装布局、根命令、运行提示和元数据。
- `AGENTS.md`：面向 agent 的本安装包简短操作指引。
- `SKILL_INSTALL_PACK_MANIFEST.json`：准确列出包含的 skills、scripts、docs、references 和 profile metadata。
- pack_name: `wff-v1.5-skills-install-pack`
- install_set_id: `full-pack`
