# WFF Skills 安装包

这个压缩包是 WFF 的公网发布安装包。

它刻意小于内部项目导出 bundle。
它只包含正式发布的 skills，以及这些 skills 直接指向的脚本、文档、模板、参考包和运行依赖。

首次阅读：先打开 `WFF-START-HERE.zh-CN.md`，按短入口图选择任务路线，再展开完整安装包。

## 标识
- pack_name: `wff-v1.5-skills-install-pack`
- generated_at: `2026-06-05T19:12:44+00:00`
- source_revision: `3bce26fd12fc9f68bce20cdd8315366535f50d7c`

## 能力边界
- `Phase 1` 到 `Phase 4`：GA 主线能力
- `PX`：面向已有系统接手、重构、迁移和扩容场景
- Release-facing source governance 位于 `docs/source-registers/`；仓库本地 `docs/internal/` 工作记录不是用户运行资产。
- retained proof snapshots 保留在 authoring repo，不作为 install-pack payload。
- 本安装包保留生命周期顺序；产品、架构和实现里的不确定判断交给 Agent。
- 测试、运行结果和 Review 只说明它们有证据支持的结论。
- Phase 4 以单个 `wff-validation` 入口 skill 发布，acceptance、evidence 和 closure 职责保留在该入口 skill 内部。

## 安装模型
1. 优先安装 `skills/wff-base-traceability-management/`。
2. 当用户安装 WFF Skills 后需要项目初始化指引时，安装 `skills/wff-help/`。
3. 只有当起点粗略、零散或产品真相不稳定时，才先安装并使用 `skills/wff-req-chat/`。
4. 再安装你需要的阶段编排器。
5. 再安装该阶段依赖的支持技能。Phase 3 建议直接使用 `implementation-delivery` 安装组合；安全审计和交付打包能力通常由 `wff-impl` 调用，不作为普通用户一级入口。
6. 当 skill 指向 `scripts/`、`docs/`、`templates/`、`reference-packages/`、`runtime-deps/` 时，确保这些目录也对代理运行环境可见。
   完整安装包可以放在项目 `.wff/<install-pack>/`，也可以放在用户全局 `~/.wff/<install-pack>/`。
   `examples/` 仅保留为退役指针。

安装单位是整个 skill 目录，不是单个 `SKILL.md` 文件。
不要把所有 skill 文件拍平成一个目录，也不要只复制多个 `SKILL.md` 文件。

## 解压后的预期目录结构
```text
wff-v1.5-skills-install-pack/
├── AGENTS.md
├── README.md
├── wff-init
├── wff-agent
├── SKILL_INSTALL_PACK_MANIFEST.json
├── skills/
│   ├── wff-base-traceability-management/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml    # 如果该技能提供该文件
│   ├── wff-help/
│   ├── wff-req-chat/
│   ├── wff-req/
│   ├── wff-arch/
│   ├── wff-impl/
│   ├── wff-validation/
│   └── wff-x/
├── scripts/
├── docs/
├── templates/
├── reference-packages/
└── runtime-deps/
```

## 安装到平台后的预期 skill 结构
平台托管目录取决于具体 AI agent 平台，但应保持每个 skill 一个目录：

```text
<platform-skills-root>/
├── wff-base-traceability-management/
│   ├── SKILL.md
│   └── agents/openai.yaml        # 如果你的平台会导入该文件
├── wff-req-chat/
│   └── SKILL.md
├── wff-req/
│   └── SKILL.md
└── ...
```

当 installed skill 引用 `scripts/`、`docs/`、`templates/`、`reference-packages/` 或 `runtime-deps/` 时，仍需让运行环境能访问解压后的 install-pack 根目录，或访问这些支持目录的等价副本。WFF 会从项目 `.wff/<install-pack>/`、用户全局 `~/.wff/<install-pack>/`、`WFF_RESOURCE_ROOT` 或 `WFF_INSTALL_ROOT` 发现这个资源根。

## 两种常见项目布局
**方案 A：平台标准 skills 目录 + WFF 资源根**

当你的代理平台只扫描固定目录时，使用这种方式。常见目录包括 Claude Code 的 `.claude/skills/`、Codex 的 `.agents/skills/`、OpenCode 的项目级 `.opencode/skills/` 和用户级 `~/.config/opencode/skills/`。OpenCode 还会自动扫描同一 HOME 下的 `~/.claude/skills/` 和 `~/.agents/skills/`，所以不要把同一套 WFF skills 同时装进多个用户级平台目录。

```text
/Users/edy/project/party/
├── .claude/
│   └── skills/
│       ├── wff-base-traceability-management/
│       ├── wff-req-chat/
│       ├── wff-req/
│       ├── wff-arch/
│       ├── wff-impl/
│       ├── wff-validation/
│       └── wff-x/
├── .wff/
│   └── wff-v1.5-skills-install-pack/
│       ├── scripts/
│       ├── docs/
│       ├── templates/
│       ├── reference-packages/
│       └── runtime-deps/
└── ...
```

在这个布局中，平台 skills 目录放复制或导入后的 skill 目录，`.wff/` 保留 WFF 支持资产。资源根也可以放在用户全局域，例如 `~/.wff/<install-pack>/`；`wff-init` 会把 `skills_root` 和 `resource_root` 写入 `.wff/wff-project.json`。不要把 WFF 支持脚本放进拼写错误或临时自造的目录，例如 `.claud/scripts`。

**方案 B：完整保留 install pack**

当你的代理平台可以从任意目录导入 skills，或可以直接注册安装包内的 `skills/*` 目录时，使用这种方式。

```text
/Users/edy/project/party/
└── wff-v1.5-skills-install-pack/
    ├── skills/
    ├── scripts/
    ├── docs/
    ├── templates/
    ├── reference-packages/
    └── runtime-deps/
```

方案 B 最不容易打断相对引用。方案 A 更适合有标准 skills 目录的平台，但仍然必须保留 WFF 资源根。

## 项目初始化
安装 WFF Skills 后，需要在每个目标业务项目中执行一次项目初始化，让 runtime wrapper 能从项目本地 `.wff/` 找到 WFF base skill：

```bash
cd /path/to/your-project
/path/to/wff-v1.5-skills-install-pack/wff-init
```

`wff-init` 对已有项目安全：它只创建或更新 `.wff/`，遇到冲突会停止，不会覆盖业务文件。它会在 `.wff/wff-project.json` 记录 `skills_root`，并在能找到完整安装包时记录 `resource_root`。

仅支持两个参数：

- `--project-root <path>`：目标业务项目目录，默认是当前目录。
- `--skills-root <path>`：已安装 WFF skills 的根目录，默认自动探测。

## Role-Agent 平台适配器
可选的 `wff-agent` 命令用于把 WFF 角色配置导出到目标项目。
它不会调用 LLM，不运行独立 Agent runtime，也不会替代 WFF 生命周期技能和验证证据。

```bash
/path/to/wff-v1.5-skills-install-pack/wff-agent setup opencode all --project-root /path/to/your-project
/path/to/wff-v1.5-skills-install-pack/wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/your-project
/path/to/wff-v1.5-skills-install-pack/wff-agent setup codex wff-product-manager --project-root /path/to/your-project
```

OpenCode 会导出到 `.opencode/agents/`。Claude Code 会导出到 `.claude/agents/`。Codex 会导出角色说明到 `.codex/wff-agents/` 并更新 `AGENTS.md`；这是明确的降级入口，不是假装 Codex 已有原生角色切换。

角色架构图、分平台使用例子、角色选择表和排障说明见 `docs/WFF-ROLE-AGENTS.zh-CN.md`。
全局路线图、入口层和人类产物三大类见 `docs/public/wff-orientation-map.zh-CN.md`。

## 运行提示
- 在执行 P3 / P4 / PX / 发布验证前，先检查 Python 3.10+、Node.js 18+（推荐 Node 22）、与生成 P3 workspace 的 `packageManager` 字段匹配的 pnpm（当前为 `pnpm@9.0.0`）、Docker 与 Compose v2+（`docker compose`）和外网访问。缺失或版本不够时先安装或升级，再开始验证。
- Phase 3 会生成一个 Node.js workspace，在 dispatch 执行前仍需要先完成依赖 bootstrap。
- 预期上，P3 严格运行验证会占据大部分运行时间。已保留的 v1.4 / v1.4.1 双案例发布证明显示，P3 约占已记录阶段耗时的 `96%`，因为它执行的是实现证明，不只是文档生成。
- P3 严格运行验证的主耗时来自全量目标测试里的 SQL / contract / scenario / replay 证据，尤其是 contract-heavy API / DB suite 会反复恢复运行态。Docker image build / compose startup 是运行冒烟验证内部的次级成本，不是 P3 总 wall-clock 的主因。
- 默认迭代可以先用 `--validation-level fast` 或 `--validation-level focused` 做快速验证 / 聚焦验证，避免很多必要场景每次都跑严格全量验证；这两个档位只跑关键目标证据，且不会自动执行运行冒烟验证，除非显式传入 `--run-runtime-smoke`。快速验证 / 聚焦验证只能证明局部或关键路径通过，不能替代发布证明。
- 如果要做严格运行验证，先执行 `python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-output-dir> --install --strict --output <phase3-output-dir>/phase3-toolchain-bootstrap.json`，再用 `scripts/phase3/phase3_delivery_gate.py` 消费已提供的运行证据；交付就绪还要求 `runtime-smoke-report.json` 和 `started-service-smoke-report.json`。
- 等价的直接命令是：`pnpm install --dir <phase3-output-dir> --frozen-lockfile=false`。
- 针对保留 source brief 的隔离 Release SKILLS 验证继续属于仓库 / release-proof profile 工作流，不作为默认公网安装包运行入口。

## 已包含的顶层目录
- `config`
- `docs`
- `reference-packages`
- `runtime-deps`
- `scripts`
- `skills`
- `sources`
- `templates`

## 说明
- 这个包才是公网 GitHub Release 资产。
- 更大的 `build_skill_release_bundle.py` 导出物继续保留给内部项目导出流程，不再作为公网安装资产。
- 这里的 `docs/` 只是面向运行和支持的精简子集，不是完整仓库文档树。
- v1.4 最终验证证据保留在 authoring repo 中，不包含在这个公网安装包内；它只证明开发 / 预生产生命周期闭环。
- 对于 Phase-1，canonical check surface 是 `run_phase1_full_trial.py` / `run_phase1_convergence.py` 加 `stage_depth/quality/executability`；`assembly/analyze/section/consistency` 四个脚本当前仅作为 bundle internal compatibility scripts 保留。见 `docs/phases/phase-1/phase-1-gate-authority-map-v0.1.md`。

## 元数据文件
- `SKILL_INSTALL_PACK_MANIFEST.json`
- `SKILL_INSTALL_PACK_AUDIT.json`
- `INSTALL_PACK_AUDIT.md`
