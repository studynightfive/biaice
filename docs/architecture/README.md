# M0 架构基线

状态：`CANDIDATE`。本基线允许成员 1 建立平台骨架；在组长签署 `docs/stage-gates/M0-foundation.md` 前，成员 2–7 只能实现静态壳、fixture 和经审阅的契约，不得自行发明正式业务 Schema。

## 不变量

1. 单仓库、模块化单体 API；API 与 Celery Worker 共用后端代码和镜像，通过不同命令运行。
2. 模块之间只通过 application port、OpenAPI 或 outbox 事件协作，禁止跨模块直接写表。
3. 所有租户业务对象、消息、缓存、对象键、审计与血缘携带 `tenant_id` 和 `data_domain_id`；project/unit 作用域按资源显式携带。
4. Pydantic handler/stub 是 OpenAPI 唯一来源；导出快照和生成 TypeScript 客户端只读，禁止手工编辑。
5. PostgreSQL 是业务真状态；Celery 至少一次投递，任务以 `job_id + input_hash` 幂等，outbox 与业务对象同事务写入。
6. 所有已发布决定、评估和报告不可覆盖；更正通过新版本或追加事件。
7. 未通过 Gate、状态未知、契约未冻结或审计不可用时，敏感/正式流程失败关闭。
8. Provider 只能由 `worker-provider` 经 `provider-egress-gateway` 访问；浏览器、Web、API 和其他 Worker 无直接出网。

## 公共契约

成员 1 提供 `IdentityContext`、`TenantScope`、`PermissionGuard`、`AuditWriter`、`StoragePort`、`JobPort`、`OutboxPort`、`Clock`、`Money`、`ProblemDetails`、`VersionMetadata` 和生成 API 客户端。

`SecretStorePort` 与低层 `ProviderEgressPort` 仅能注入成员 5 的 Provider 配置/调用模块，不是通用领域端口。成员 2/3/4/6/7 的生成式任务只能消费成员 5 的 `GovernedModelInvocationPort`。

## 数据与网络模式

- `synthetic_http`：默认；合成或脱敏数据，HTTP 可用，真实 Key 与 Provider 出网硬禁。
- `secure_https`：只有 `BYOK_SECRET_GATE=PASS/CURRENT` 后才允许真实 Key 和受限 Provider 路径。
- `real-data`：只有 `REAL_DATA_MODE=PASS/CURRENT` 的 12 项机器证据全部通过才允许启动；它不自动授权模型调用。
- `host-ingress`：只包含 gateway，用于 Docker Desktop 宿主端口发布；`front` 与 `back` 仍为内部网络。真实数据模式还须由宿主防火墙证明 gateway 不能主动访问公网。
- `maintenance-egress` 和 `observability` 都是显式 profile，默认关闭。
