# WFF Skills 安装包

这个压缩包是 WFF 的公网发布安装包。

它刻意小于内部项目导出 bundle。
它只包含正式发布的 skills，以及这些 skills 直接指向的脚本、文档、模板、参考包和发布案例。

## 标识
- pack_name: `wff-v1.3.17-skills-install-pack`
- generated_at: `2026-05-19T15:05:56+00:00`
- source_revision: `abcc0798fa8f701d4ec258e26f83130515a57fe8`

## 能力边界
- `Phase 1` 到 `Phase 4`：GA 主线能力
- `Phase X`：Preview / Incubating
- v1.3 控制模型：Workflow shell + Agentic core + Evidence bridge
- 本安装包保留生命周期顺序，把高不确定性的产品 / 架构 / 实现判断交给 Agentic reasoning，并用 evidence / gates 封顶正式声明。

## 安装模型
1. 优先安装 `skills/wff-base-traceability-management/`。
2. 当用户安装 WFF Skills 后需要项目初始化指引时，安装 `skills/wff-help/`。
3. 只有当起点粗略、零散或产品真相不稳定时，才先安装并使用 `skills/wff-req-chat/`。
4. 再安装你需要的阶段编排器。
5. 再安装该阶段依赖的 worker 或 stage 技能。
6. 当 skill 指向 `scripts/`、`docs/`、`templates/`、`reference-packages/`、`release-cases/` 时，确保这些目录也对代理运行环境可见。
   `examples/` 仅保留为退役指针。

安装单位是整个 skill 目录，不是单个 `SKILL.md` 文件。
不要把所有 skill 文件拍平成一个目录，也不要只复制多个 `SKILL.md` 文件。

## 解压后的预期目录结构
```text
wff-v1.3.17-skills-install-pack/
├── README.md
├── wff-init
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
├── release-cases/
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

当 installed skill 引用 `scripts/`、`docs/`、`templates/`、`reference-packages/` 或 `release-cases/` 时，仍需让运行环境能访问解压后的 install-pack 根目录，或访问这些支持目录的等价副本。

## 两种常见项目布局
**方案 A：平台标准 skills 目录 + WFF 资源根**

当你的代理平台只扫描固定目录，例如 `.claude/skills/` 时，使用这种方式。

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
│   └── wff-v1.3.17-skills-install-pack/
│       ├── scripts/
│       ├── docs/
│       ├── templates/
│       ├── reference-packages/
│       ├── release-cases/
│       └── runtime-deps/
└── ...
```

在这个布局中，`.claude/skills/` 放复制或导入后的 skill 目录，`.wff/` 保留 WFF 支持资产。不要把 WFF 支持脚本放进拼写错误或临时自造的目录，例如 `.claud/scripts`。

**方案 B：完整保留 install pack**

当你的代理平台可以从任意目录导入 skills，或可以直接注册安装包内的 `skills/*` 目录时，使用这种方式。

```text
/Users/edy/project/party/
└── wff-v1.3.17-skills-install-pack/
    ├── skills/
    ├── scripts/
    ├── docs/
    ├── templates/
    ├── reference-packages/
    ├── release-cases/
    └── runtime-deps/
```

方案 B 最不容易打断相对引用。方案 A 更适合有标准 skills 目录的平台，但仍然必须保留 WFF 资源根。

## 项目初始化
安装 WFF Skills 后，需要在每个目标业务项目中执行一次项目初始化，让 runtime wrapper 能从项目本地 `.wff/` 找到 WFF base skill：

```bash
cd /path/to/your-project
/path/to/wff-v1.3.17-skills-install-pack/wff-init
```

`wff-init` 对已有项目安全：它只创建或更新 `.wff/`，遇到冲突会停止，不会覆盖业务文件。

仅支持两个参数：

- `--project-root <path>`：目标业务项目目录，默认是当前目录。
- `--skills-root <path>`：已安装 WFF skills 的根目录，默认自动探测。

## 运行提示
- Phase 3 会生成一个 Node.js workspace，在 dispatch 执行前仍需要先完成依赖 bootstrap。
- 如果要做 runtime closure，执行 `python3 scripts/phase3/run_phase3_first_version.py --mainline-verification-mode strict-runtime ...`，或先执行 `python3 scripts/phase3/phase3_toolchain_bootstrap.py --workspace-root <phase3-output-dir> --install --strict --output <phase3-output-dir>/phase3-toolchain-bootstrap.json`；`delivery-ready` 还要求 `runtime-smoke-report.json` 和 `started-service-smoke-report.json`。
- 等价的直接命令是：`pnpm install --dir <phase3-output-dir> --frozen-lockfile=false`。
- 如果要针对保留的 `GEO + PetClinic` source brief 做隔离的 Release SKILLS 验证，先执行 `python3 scripts/release/run_release_dual_case_eval.py --workspace-root <isolated-workspace> --prepare-only`，确认隔离 workspace 与命令计划后，再去掉 `--prepare-only` 执行实际跑数。实际执行默认将 `--case-workers` 设为本轮请求的 case 数；如需保留串行 case 执行，传入 `--case-workers 1`。

## 已包含的顶层目录
- `config`
- `docs`
- `reference-packages`
- `release-cases`
- `runtime-deps`
- `scripts`
- `skills`
- `sources`
- `templates`

## 说明
- 这个包才是公网 GitHub Release 资产。
- 更大的 `build_skill_release_bundle.py` 导出物继续保留给内部项目导出流程，不再作为公网安装资产。
- 这里的 `docs/` 只是面向运行和支持的精简子集，不是完整仓库文档树。
- v1.3 最终证据快照保留在 authoring repo 中，不包含在这个公网安装包内；它只证明开发 / 预生产生命周期闭环。
- 对于 Phase-1，canonical gate surface 是 `run_phase1_full_trial.py` / `run_phase1_convergence.py` 加 `stage_depth/quality/executability`；`assembly/analyze/section/consistency` 四个 gate 脚本当前仅作为 bundle internal compatibility scripts 保留。

## 元数据文件
- `SKILL_INSTALL_PACK_MANIFEST.json`
- `SKILL_INSTALL_PACK_AUDIT.json`
- `INSTALL_PACK_AUDIT.md`
