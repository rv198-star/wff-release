# Stage-02 鲁棒性测试用例（审计镜像）— blocked / hidden-defect / fake-completion paths

## 1. 这个文件是做什么的
- 这是 Stage-02 英文 `robustness-test-case.md` 的中文审计镜像。
- 它说明：Stage-02 在 blocked、hidden-defect、fake-completion 防护上，应该抵抗哪些典型坏输入。

## 2. 核心关注点
- Stage-01 may-start 为 `no` 时不得偷偷启动。
- 不能把 defect 藏进 summary prose。
- 不能在缺失 evidence path 时伪装成执行已完成。

## 3. 边界提醒
- 这是规则层鲁棒性覆盖，不是完整执行系统仿真。
