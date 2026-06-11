# Stage-01 输出模板（审计镜像）— architecture-definition-and-boundary-setting

## 1. 这个文件是做什么的
- 这是 Stage-01 英文输出模板的中文审计镜像。
- 它帮助评审者理解：最终架构入口产物长什么样、哪些字段必须显式表达不确定性与上下游关系。

## 2. 最关键字段
- 系统边界说明
- 继承 / 推演 / 未知 / 延后约束
- `upstream_nfr_state`
- `critical_dependency_realizability_scan`
- `first_pass_realization_mode`
- `substitute_boundary_candidates`
- security architecture sketch
- capacity estimation
- 能力地图
- 架构方向
- 关键架构决策
- `downstream_assumption_contract`
- `artifact_id / depends_on / feeds / source_path / source_anchor`
- `source / confidence_profile / verification`

## 3. 图示要求
- Stage-01 强制要求 Mermaid。
- 至少应有：系统边界/上下文图、能力地图或等价结构图。
- 若关键依赖尚未完全可实现，图示或说明中必须保留 substitute-boundary / review-bound 标记，不能伪装成已落地主路径。

## 4. 交接要求
- 最终交给 Stage-02。
- handoff package 至少要包含：系统边界、约束态势、关键依赖 realizability、substitute-boundary 候选、安全架构草图、容量估算、能力地图、架构方向、关键架构决策、downstream may-assume / must-not-assume、review-bound 项。
