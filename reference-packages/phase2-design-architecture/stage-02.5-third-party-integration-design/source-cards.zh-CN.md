# Stage-02.5 方法资产引用（审计镜像）— third-party-integration-architecture-design

## 1. 优先输入
- P1 第三方依赖清单
- Stage-01 架构边界
- Stage-02 模块/服务分解
- Provider API/Auth/Sandbox 文档

## 2. 反模式
- provider 依赖存在，但 Stage-02.5 没有 activation decision
- 只有 happy path，没有 negative path
- adapter seam 没有 internal port 命名

