# WFF Skills 安装包

这个压缩包是 WFF 的公网发布安装包。它小于内部项目导出 bundle，只包含正式发布的 skills，以及这些 skills 直接指向的脚本、文档、模板、参考包和运行依赖。

首次阅读：先打开 `WFF-START-HERE.zh-CN.md`，按短入口图选择任务路线，再展开完整安装包。

## 标识
- pack_name: `wff-v1.5.3-skills-install-pack`
- generated_at: `2026-06-11T16:20:26+00:00`
- source_revision: `f124ecb5dfaa60a355f5ba131d98585809ebda3b`

## 能力边界
- `Phase 1` 到 `Phase 4`：GA 主线能力。
- `PX`：面向已有系统接手、重构、迁移和扩容场景。
- Release-facing source governance 位于 `docs/source-registers/`；仓库本地工作记录不是用户运行资产。
- retained proof snapshots 保留在 authoring repo，不作为 install-pack payload。
- 本安装包保留生命周期顺序；产品、架构和实现里的不确定判断交给 Agent。
- 测试、运行结果和 Review 只说明它们有证据支持的结论。
- Phase 4 以单个 `wff-validation` 入口 skill 发布，acceptance、evidence 和 closure 职责保留在该入口 skill 内部。

## 产品入口边界
- Start New Work：`wff-req-chat` 把想法、材料或对话整理成 P1 source input packet，再进入 `wff-req`；它不声明 PRD 已生成、P1 已完成或下游已就绪。
- PX：`wff-x` 是 code-backed existing-system assessment。Related documents are supporting evidence；standalone documents are not enough。它用于有代码支撑的旧系统、运行态系统、重构、迁移或扩容。

## 安装模型
1. 优先安装 `skills/using-wff/` 作为用户选入口。
2. 安装 `skills/wff-base-traceability-management/` 作为项目追踪底座。
3. 只有需要退役项目初始化兼容时，才安装 `skills/wff-help/`。
4. 起点粗略、零散或产品真相不稳定时，才先安装并使用 `skills/wff-req-chat/`。
5. 再安装所需阶段编排器和支持技能。
6. Phase 3 建议直接使用 `implementation-delivery` 安装组合；安全审计和交付打包能力通常由 `wff-impl` 调用。
7. 当 skill 指向 `scripts/`、`docs/`、`templates/`、`reference-packages/`、`runtime-deps/` 时，确保这些目录也对代理运行环境可见。

安装单位是整个 skill 目录，不是单个 `SKILL.md` 文件。不要把所有 skill 文件拍平成一个目录，也不要只复制多个 `SKILL.md` 文件。

## 解压后的预期目录结构
```text
wff-v1.5.3-skills-install-pack/
├── AGENTS.md
├── README.md
├── wff-init
├── wff-agent
├── SKILL_INSTALL_PACK_MANIFEST.json
├── skills/
│   ├── using-wff/
│   ├── wff-base-traceability-management/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
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
│   └── SKILL.md
├── wff-req-chat/
└── ...
```

当 installed skill 引用支持目录时，仍需让运行环境能访问解压后的 install-pack 根目录，或访问这些支持目录的等价副本。WFF 会从项目 `.wff/<install-pack>/`、用户全局 `~/.wff/<install-pack>/`、`WFF_RESOURCE_ROOT` 或 `WFF_INSTALL_ROOT` 发现这个资源根。

## 两种常见项目布局
**方案 A：平台标准 skills 目录 + WFF 资源根**

```text
/Users/edy/project/party/
├── .claude/
│   └── skills/
│       ├── wff-base-traceability-management/
│       ├── wff-req-chat/
│       ├── wff-req/
│       └── wff-x/
├── .wff/
│   └── wff-v1.5.3-skills-install-pack/
│       ├── scripts/
│       ├── docs/
│       ├── templates/
│       ├── reference-packages/
│       └── runtime-deps/
└── ...
```

当代理平台只扫描固定目录时使用方案 A。不要把 WFF 支持脚本放进拼写错误或临时自造的目录，例如 `.claud/scripts`。

**方案 B：完整保留 install pack**

```text
/Users/edy/project/party/
└── wff-v1.5.3-skills-install-pack/
    ├── skills/
    ├── scripts/
    ├── docs/
    ├── templates/
    ├── reference-packages/
    └── runtime-deps/
```

方案 B 最不容易打断相对引用。

## 项目初始化
```bash
cd /path/to/your-project
/path/to/wff-v1.5.3-skills-install-pack/wff-init
```

`wff-init` 只创建或更新 `.wff/`，遇到冲突会停止。仅支持两个参数：

- `--project-root <path>`：目标业务项目目录，默认是当前目录。
- `--skills-root <path>`：已安装 WFF skills 的根目录，默认自动探测。

## Role-Agent 平台适配器
```bash
/path/to/wff-v1.5.3-skills-install-pack/wff-agent setup opencode all --project-root /path/to/your-project
/path/to/wff-v1.5.3-skills-install-pack/wff-agent setup claude-code wff-programmer wff-reviewer --project-root /path/to/your-project
/path/to/wff-v1.5.3-skills-install-pack/wff-agent setup codex wff-product-manager --project-root /path/to/your-project
```

`wff-agent` 导出角色配置，不调用 LLM，不运行独立 Agent runtime，也不会替代 WFF 生命周期技能和验证证据。角色说明见 `docs/WFF-ROLE-AGENTS.zh-CN.md`；全局路线图见 `docs/public/wff-orientation-map.zh-CN.md`。

## 运行提示
- 在执行 P3 / P4 / PX / 发布验证前，先检查 Python 3.10+、Node.js 18+（推荐 Node 22）、匹配生成 P3 workspace 的 pnpm、Docker 与 Compose v2+ 和外网访问。
- Phase 3 会生成 Node.js workspace，在 dispatch 执行前仍需要先完成依赖 bootstrap。
- 快速验证 / 聚焦验证（例如 `--validation-level fast`）只适合诊断和局部修复检查，不能替代发布证明。
- 严格运行验证前，先执行 `python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-output-dir> --install --strict --output <phase3-output-dir>/phase3-toolchain-bootstrap.json`。
- 等价的直接命令是：`pnpm install --dir <phase3-output-dir> --frozen-lockfile=false`。
- 更大的 `build_skill_release_bundle.py` 导出物继续保留给内部项目导出流程，不作为公网安装资产。

## 已包含的顶层目录
- `config`
- `docs`
- `reference-packages`
- `runtime-deps`
- `scripts`
- `skills`
- `templates`

## 说明
- 这里的 `docs/` 只是面向运行和支持的精简子集，不是完整仓库文档树。
- 对于 Phase-1，canonical check surface 是 `run_phase1_full_trial.py` / `run_phase1_convergence.py` 加 `stage_depth/quality/executability`；`assembly/analyze/section/consistency` 四个脚本当前仅作为 bundle internal compatibility scripts 保留。见 `docs/phases/phase-1/phase-1-gate-authority-map-v0.1.md`。
