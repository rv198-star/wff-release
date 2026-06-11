# Skills 安装包审计

## 标识
- 安装包名称: `wff-v1.5-skills-install-pack`
- pack_type: `skills-install-pack`
- profile_id: `full-pack`
- profile_status: `default`
- profile_claim: `default-full-pack`
- 源修订版本: `3bce26fd12fc9f68bce20cdd8315366535f50d7c`
- 总体结论: `pass`

## 硬失败项
- 无

## 内部引用审计
- 断裂引用数: `0`
- 无

## 本地脚本引用审计
- 断裂引用数: `0`
- 无

## 排除路径泄漏审计
- pyc_files: `0`
- pycache_dirs: `0`
- test_dirs: `0`

## Content Inventory
- total_files: `1001`
- total_bytes: `8325374`
- policy_findings: `0`
- 无
- top_level:
  - `AGENTS.md`: files=`1`, bytes=`2458`
  - `README.en.md`: files=`1`, bytes=`10667`
  - `README.md`: files=`1`, bytes=`10455`
  - `README.zh-CN.md`: files=`1`, bytes=`10455`
  - `SKILL_INSTALL_PACK_MANIFEST.json`: files=`1`, bytes=`44468`
  - `WFF-START-HERE.md`: files=`1`, bytes=`2588`
  - `WFF-START-HERE.zh-CN.md`: files=`1`, bytes=`2819`
  - `config`: files=`3`, bytes=`74320`
  - `docs`: files=`123`, bytes=`1090051`
  - `reference-packages`: files=`369`, bytes=`978924`
  - `requirements.txt`: files=`1`, bytes=`12`
  - `runtime-deps`: files=`59`, bytes=`332481`
  - `scripts`: files=`269`, bytes=`5176973`
  - `skills`: files=`54`, bytes=`367992`
  - `sources`: files=`109`, bytes=`205390`
  - `templates`: files=`5`, bytes=`15011`
  - `wff-agent`: files=`1`, bytes=`168`
  - `wff-init`: files=`1`, bytes=`142`

## Install-Pack AGENTS.md
- path: `AGENTS.md`
- exists: `True`
- line_count: `38`
- max_allowed_lines: `120`
- missing_required_phrases: `(none)`
- repo_level_markers: `(none)`

## Root Guidance / Context Boundary
- forbidden_manifest_root_files: `(none)`
- forbidden_path_leaks: `(none)`
- unexpected_root_guidance_files: `(none)`
- oversized_root_guidance_files: `0`
- repo_level_marker_hits: `0`
- checked `AGENTS.md`: `38` lines, markers=`(none)`
- checked `README.en.md`: `184` lines, markers=`(none)`
- checked `README.md`: `185` lines, markers=`(none)`
- checked `README.zh-CN.md`: `185` lines, markers=`(none)`
- checked `WFF-START-HERE.md`: `36` lines, markers=`(none)`
- checked `WFF-START-HERE.zh-CN.md`: `38` lines, markers=`(none)`

## Release Eval Support
- official_input_root: ``
- official_runner: ``
- 缺失文件: `(none)`

## WFF Role-Agent Support
- launcher: `wff-agent`
- script: `scripts/release/wff_agent.py`
- role_manifest: `config/wff-role-mounts.json`
- 缺失文件: `(none)`
- help_probe `scripts/release/wff_agent.py --help` -> `pass`

## 阶段运行时分类
- phase1: `install-pack-ready`
- phase2: `install-pack-ready`
- phase3: `install-pack-ready`
- phase4: `install-pack-ready`
- phasex: `preview-install-pack-ready`

## Skill 完整性
### skills/wff-impl-review/SKILL.md
- 缺失标题: `(none)`
- 缺失文件: `(none)`
### skills/wff-impl-security/SKILL.md
- 缺失标题: `(none)`
- 缺失文件: `(none)`

## 阶段详情
### phase1
- 分类: `install-pack-ready`
- 必需文件数: `7`
- 缺失文件: `(none)`
- 帮助探针:
  - `scripts/phase1/run_phase1_full_trial.py --help` -> `pass`

### phase2
- 分类: `install-pack-ready`
- 必需文件数: `10`
- 缺失文件: `(none)`
- 帮助探针:
  - `scripts/phase2/run_phase2_first_version.py --help` -> `pass`
  - `scripts/phase2/run_phase2_full_trial.py --help` -> `pass`

### phase3
- 分类: `install-pack-ready`
- 必需文件数: `4`
- 缺失文件: `(none)`
- 帮助探针:
  - `scripts/phase3/run_impl.py --help` -> `pass`

### phase4
- 分类: `install-pack-ready`
- 必需文件数: `9`
- 缺失文件: `(none)`
- 帮助探针:
  - `scripts/phase4/run_phase4_first_version.py --help` -> `pass`
  - `scripts/phase4/run_p1_p4_mainline_closure.py --help` -> `pass`

### phasex
- 分类: `preview-install-pack-ready`
- 必需文件数: `8`
- 缺失文件: `(none)`
- 帮助探针:
  - `scripts/phasex/scaffold_phasex_case.py --help` -> `pass`
  - `scripts/phasex/validate_phasex_case.py --help` -> `pass`
  - `scripts/phasex/extract_mainline_reentry_packets.py --help` -> `pass`
