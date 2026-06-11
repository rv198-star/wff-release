# Stage-01 鲁棒性测试案例（审计镜像）— architecture-definition-and-boundary-setting

## 1. 这个文件是做什么的
- 这是 Stage-01 英文 `robustness-test-case.md` 的中文审计镜像。
- 它说明：当前阶段重点要防哪些 refusal / blocked / false-certainty 路径。

## 2. 关注点
- 没有 handoff 时必须拒绝/阻塞
- 边界无法成立时必须 blocked
- NFR 不完整时不能伪装成完整
- 安全姿态不能被完全延后
- 容量姿态不能因为“数字不准”而直接留空
