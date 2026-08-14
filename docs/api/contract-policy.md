# API 契约策略

Pydantic router/stub 是唯一接口源。M0 按 `method + path + operationId + permission + request/response schema + errors + idempotency/ETag + UI mapping` 冻结；FastAPI 导出 `packages/contracts/openapi.generated.json`，再生成只读 TypeScript 客户端。

公共规则：

- API 前缀 `/api/v1`；健康检查位于 `/health/live` 与 `/health/ready`。
- 创建、命令和异步任务使用 `Idempotency-Key`。
- 可变草稿返回 ETag，更新要求 `If-Match`；已发布版本禁止 PATCH。
- 列表使用 cursor pagination、稳定排序与权限过滤。
- 异步操作返回 `202 + job_id + status_url + events_url`；SSE 为主、轮询降级。
- 错误使用 RFC 7807 `ProblemDetails` 和稳定 `error_code`，携带 `request_id`，不得泄露资源存在性或敏感值。
- tenant/data-domain/scope 从服务端身份获取，客户端字段不能覆盖。
- 导出物和生成目录禁止手改；CI 必须重新导出并检查无 diff。
