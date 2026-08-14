# 事件、血缘与失效传播基线

## 事件信封

所有事件至少包含：`event_id`、`event_type`、`schema_version`、`occurred_at`、`tenant_id`、`data_domain_id`、`scope_type`、`scope_id`、`aggregate_type`、`aggregate_id`、`aggregate_version`、`correlation_id`、`causation_id`、`actor_id`、`payload_hash` 和最小化 payload。事件不得含正文、API Key、个人信息、成本明细或原始提示词/响应。

## 写入与投递

- 业务对象与 outbox event 在同一 PostgreSQL 事务写入。
- dispatcher 至少一次投递；消费者以 `event_id + handler_version` 幂等。
- 业务真状态只在 PostgreSQL，Redis 消息丢失后由 reconciliation 恢复。

## FR-11 传播

血缘边的 `dependency_type` 仅允许 `COMPUTATIONAL / EVIDENTIAL / POLICY / AUTHORIZATION / PRESENTATIONAL`。替代、撤销、过期、保留到期、删除与上游有效性变化按“事件 × 依赖类型”矩阵传播；重复事件不得重复生成正式版本。

`retention_expires_at` 到期立即停止正式使用并触发处置。有效 LegalHold 只阻止物理删除，不恢复业务有效性。全局 `DeletionCompleted` 只有在成员 3 本地副本 adapter 与成员 5 Provider 副本 adapter 的全部必需 receipt 均收齐后由成员 1 发布；备份恢复必须先重放 tombstone。

## 敏感 sink 失败关闭

AuditWriter 不可用或哈希链验证失败时，正文查看、下载、导出、发布、审批、授权、用途审批、解除隔离、保全解除、删除和 Provider 调用全部阻断。恢复后从可信锚点验证断点再解除阻断。
