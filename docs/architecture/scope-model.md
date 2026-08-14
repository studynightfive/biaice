# 作用域与隔离模型

租户业务对象统一保存 `tenant_id` 与 `data_domain_id`，再按资源保存 `project_id`、`decision_unit_id` 或显式 `scope_type/scope_id`。禁止为了方便伪造 DecisionUnit。

隔离必须同时落实于：PostgreSQL 复合外键与 RLS、MinIO 对象键、Redis broker/cache key、Celery payload、审计、血缘、导出、备份和日志字段。跨 scope 引用在数据库、服务策略和负向测试三层阻断。

首期唯一 PLATFORM 业务配置例外是 `ProviderCatalogVersion`：`tenant_id/data_domain_id` 为 NULL，位于独立 schema/RLS；租户只能读取 PUBLISHED/CURRENT 最小投影，不能写入或借此读取任何租户配置、Key、调用正文或内部网络信息。
