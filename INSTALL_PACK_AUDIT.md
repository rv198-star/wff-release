# Skills 安装包审计

## 标识
- 安装包名称: `wff-v1.10.0-skills-install-pack`
- pack_type: `skills-install-pack`
- profile_id: `full-pack`
- profile_status: `default`
- profile_claim: `default-full-pack`
- 源修订版本: `1ad24accaf96dcb5422dccd94140c32934d41c73`
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
- total_files: `766`
- total_bytes: `10746446`
- policy_findings: `0`
- 无
- top_level:
  - `AGENTS.md`: files=`1`, bytes=`7630`
  - `INSTALL-PACK-README.en.md`: files=`1`, bytes=`7574`
  - `INSTALL-PACK-README.md`: files=`1`, bytes=`7434`
  - `INSTALL-PACK-README.zh-CN.md`: files=`1`, bytes=`7434`
  - `INSTALL_PACK_AUDIT.md`: files=`1`, bytes=`5631`
  - `README.en.md`: files=`1`, bytes=`7574`
  - `README.md`: files=`1`, bytes=`7177`
  - `README.zh-CN.md`: files=`1`, bytes=`7177`
  - `SKILL_INSTALL_PACK_AUDIT.json`: files=`1`, bytes=`14655`
  - `SKILL_INSTALL_PACK_MANIFEST.json`: files=`1`, bytes=`55156`
  - `WFF-START-HERE.md`: files=`1`, bytes=`2885`
  - `WFF-START-HERE.zh-CN.md`: files=`1`, bytes=`2771`
  - `config`: files=`4`, bytes=`92520`
  - `docs`: files=`24`, bytes=`262004`
  - `reference-packages`: files=`184`, bytes=`770012`
  - `requirements.lock.txt`: files=`1`, bytes=`558`
  - `requirements.txt`: files=`1`, bytes=`84`
  - `runtime-deps`: files=`112`, bytes=`1057601`
  - `scripts`: files=`366`, bytes=`8003406`
  - `skills`: files=`59`, bytes=`423917`
  - `templates`: files=`1`, bytes=`2936`
  - `wff-agent`: files=`1`, bytes=`168`
  - `wff-init`: files=`1`, bytes=`142`

## Install-Pack AGENTS.md
- path: `AGENTS.md`
- exists: `True`
- line_count: `56`
- max_allowed_lines: `120`
- missing_required_phrases: `(none)`
- repo_level_markers: `(none)`

## Root Guidance / Context Boundary
- forbidden_manifest_root_files: `(none)`
- forbidden_path_leaks: `(none)`
- unexpected_root_guidance_files: `(none)`
- oversized_root_guidance_files: `0`
- repo_level_marker_hits: `0`
- checked `AGENTS.md`: `56` lines, markers=`(none)`
- checked `INSTALL-PACK-README.en.md`: `154` lines, markers=`(none)`
- checked `INSTALL-PACK-README.md`: `154` lines, markers=`(none)`
- checked `INSTALL-PACK-README.zh-CN.md`: `154` lines, markers=`(none)`
- checked `README.en.md`: `154` lines, markers=`(none)`
- checked `README.md`: `105` lines, markers=`(none)`
- checked `README.zh-CN.md`: `105` lines, markers=`(none)`
- checked `WFF-START-HERE.md`: `32` lines, markers=`(none)`
- checked `WFF-START-HERE.zh-CN.md`: `32` lines, markers=`(none)`

## Runtime SKILL.md Context Boundary
- max_phase_entry_lines: `300`
- findings: `0`
- 无

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
- phasex: `install-pack-ready`

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
- diagnostic_file_count: `0`
- missing_diagnostic_files: `(none)`
- compatibility_file_count: `0`
- missing_compatibility_files: `(none)`
- 帮助探针:
  - `scripts/phase1/run_phase1_source_to_prd.py --help` -> `pass`

### phase2
- 分类: `install-pack-ready`
- 必需文件数: `9`
- 缺失文件: `(none)`
- diagnostic_file_count: `3`
- missing_diagnostic_files: `scripts/phase2/run_phase2_manual_closure.py, scripts/phase2/validate_mermaid.py, scripts/phase2/cross_stage_consistency.py`
- compatibility_file_count: `1`
- missing_compatibility_files: `scripts/phase2/run_phase2_full_trial.py`
- 帮助探针:
  - `scripts/phase2/run_phase2_fresh_generation.py --help` -> `pass`
  - `scripts/phase2/run_phase2_existing_system_intake.py --help` -> `pass`
- diagnostic_help_probes:
  - `scripts/phase2/run_phase2_manual_closure.py --help` -> `skipped` (script not included in this install profile)
- compatibility_help_probes:
  - `scripts/phase2/run_phase2_full_trial.py --help` -> `skipped` (script not included in this install profile)

### phase3
- 分类: `install-pack-ready`
- 必需文件数: `4`
- 缺失文件: `(none)`
- diagnostic_file_count: `0`
- missing_diagnostic_files: `(none)`
- compatibility_file_count: `0`
- missing_compatibility_files: `(none)`
- 帮助探针:
  - `scripts/phase3/run_impl.py --help` -> `pass`

### phase4
- 分类: `install-pack-ready`
- 必需文件数: `9`
- 缺失文件: `(none)`
- diagnostic_file_count: `0`
- missing_diagnostic_files: `(none)`
- compatibility_file_count: `0`
- missing_compatibility_files: `(none)`
- 帮助探针:
  - `scripts/phase4/run_phase4_first_version.py --help` -> `pass`
  - `scripts/phase4/run_p1_p4_mainline_closure.py --help` -> `pass`

### phasex
- 分类: `install-pack-ready`
- 必需文件数: `8`
- 缺失文件: `(none)`
- diagnostic_file_count: `0`
- missing_diagnostic_files: `(none)`
- compatibility_file_count: `0`
- missing_compatibility_files: `(none)`
- 帮助探针:
  - `scripts/phasex/scaffold_phasex_case.py --help` -> `pass`
  - `scripts/phasex/validate_phasex_case.py --help` -> `pass`
  - `scripts/phasex/extract_mainline_reentry_packets.py --help` -> `pass`
