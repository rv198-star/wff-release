# Stage-02.5 输出模板（审计镜像）— third-party-integration-architecture-design

## 1. 关键 block 名称
- `activation_decision`
- `third_party_dependency_manifest`
- `integration_decision_records`
- `integration_adapter_specifications`
- `integration_test_strategy`
- `integration_risk_register`

## 2. 评审重点
- 这些 block 名称必须保持稳定，因为脚本会直接消费它们
- active 时必须每项依赖都有 IDR / adapter / test strategy

