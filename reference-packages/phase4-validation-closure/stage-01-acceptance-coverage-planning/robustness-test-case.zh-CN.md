# Stage-01 鲁棒性测试用例（审计镜像）— refusal / blocked / false-certainty paths

## 1. 这个文件是做什么的
- 这是 Stage-01 英文 `robustness-test-case.md` 的中文审计镜像。
- 它说明：Stage-01 在 refusal / blocked / fake-readiness 防护上，应该抵抗哪些典型坏输入。

## 2. 核心关注点
- 没有实现交接时必须拒绝正式进入 Stage-01。
- 没有 defensible acceptance mapping basis 时必须 blocked。
- 不能把未成形的 gate posture 伪装成已满足。

## 3. 边界提醒
- 这是规则层鲁棒性覆盖，不是 live runtime 模拟。
