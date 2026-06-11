# Stage-02.5 操作说明（审计镜像）— third-party-integration-architecture-design

## 1. 流程主线
1. 判断本轮是否需要启用 Stage-02.5
2. 补齐依赖清单
3. 对每项依赖写 IDR
4. 定义 adapter/internal port
5. 定义本地/CI/Staging/生产测试姿势
6. 登记风险

## 2. 核心判断
- active 不能只写“接某某 API”，必须把 auth、fallback、negative path 写出来
- skipped 不能默认沉默

