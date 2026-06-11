# Stage-02.5 阶段契约（审计镜像）— third-party-integration-architecture-design

## 1. 核心作用
- 当项目存在实质第三方依赖时，把 provider 边界提前设计清楚，而不是留给 Stage-03 或实现阶段临场发挥。

## 2. 最小要求
- 必须先明确：`active` 还是 `skipped`
- 若 `skipped`，必须有 skip reason
- 若 `active`，必须补齐：
  - 第三方依赖清单
  - 每项依赖的 IDR
  - 适配器规格
  - 集成测试策略
  - 风险登记

## 3. 边界提醒
- 本阶段不写实现代码
- 但必须把 auth / key / timeout / retry / fallback / mock-sandbox posture 设计清楚

