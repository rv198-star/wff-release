# Stage-03 鲁棒性测试用例（审计镜像）— hidden-risk / fake-closure / phase-boundary leakage paths

## 1. 这个文件是做什么的
- 这是 Stage-03 英文 `robustness-test-case.md` 的中文审计镜像。
- 它说明：Stage-03 在 fake-closure、hidden-risk、Stage-03/可选 Stage-04 boundary leakage 防护上，应该抵抗哪些典型坏输入。

## 2. 核心关注点
- 证据不全时不能给出虚假 closure pass。
- 不能隐藏 unresolved defects / residual risks。
- 不能把 Stage-03 closure judgment 越界成可选 Stage-04 final release approval。

## 3. 边界提醒
- 这是规则层鲁棒性覆盖，不是 live release workflow 仿真。
