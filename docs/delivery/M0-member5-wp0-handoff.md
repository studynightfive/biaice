# M0 成员 5 交接说明：FR-12 隐私与外部处理治理

状态：`FR12_PROVIDER_HANDLERS_IMPLEMENTED / SECURE_ADAPTERS_AND_HUMAN_GATES_PENDING`

本次交付把 FR-12 的 53 个 operation 从通用 `501 CONTRACT_ONLY` 切换为真实、可执行的合成数据 handler。用户清单中的 50 个 operation 已全部覆盖；契约目录另外包含 `processing-records` 的 list/create/get 3 个 operation，因此 FR-12 契约总数为 53。

本文件不代表真实个人信息、真实 API Key、Provider 出网、Pilot 或 Production 已获批准。

## 已实现范围

- 11 类资源的 list/create/get：处理活动、处理基础证据、告知/同意、PIA、跨境评估、Provider Policy、DSR Policy、负载档案、数据主体请求、事件政策与安全事件。
- 19 个生命周期动作：PIA 批准/撤销，跨境与 Provider Policy 批准/不适用/撤销/失效，DSR Policy 发布/归档，负载档案冻结，数据主体请求身份核验/流转/完成，事件政策批准，安全事件流转/关闭。
- `POST /api/v1/consent-withdrawals` 追加同意撤回事件。
- 明确的合成元数据请求 Schema，`extra=forbid`；客户端不能提交 tenant/data-domain、服务端状态字段或 secret 字段。
- 服务端身份作用域、RBAC、MFA、maker-checker、幂等重放/冲突、审计 fail-closed、状态机与 HMAC 签名游标。
- `state=null` 查询传输值归一化为空过滤；任意或篡改游标返回稳定 `INVALID_CURSOR`，合法游标绑定租户、资源类型与过滤条件。
- OpenAPI 中 53 个 operation 均为 `x-contract-only=false`、`x-schema-status=FROZEN`，并在共享 Schemathesis 实现分区中执行。
- 成员 5 的 FR-05/FR-12/FR-13 共 129 个 catalog operation 现均为真实 handler，catalog 与 OpenAPI 均显式 `FROZEN`，成员 5 范围内 `contract-only=0`。

## Provider 目录与配置路由

- FR-13 中原有 18 个 Provider catalog/configuration/invocation 501 路由已替换为严格 Schema 和真实 handler，均为 `x-contract-only=false`、`x-schema-status=FROZEN`。
- 平台目录支持草稿、独立 maker-checker 发布/撤销及租户最小公开投影；公开目录不暴露 `api_host`、adapter 或内部网络字段。
- 租户配置支持 list/create/get、If-Match 草稿更新、计划/泄露轮换、只写 Key、固定合成连接测试、激活、暂停、撤销及脱敏调用记录。
- Key 请求 Schema 标记 `writeOnly`；任何响应、调用记录和错误均不含 `api_key`、plaintext 或 Provider 正文。
- `create_app()` 仅接受注入的 `SecretStorePort` 与 `ProviderRuntimePort`。`byok_enabled=true` 时任一端口未绑定都会在启动阶段失败；仓库不会用内存明文 Key 或伪造出网替代。
- BYOK 中间件先无正文认证，再检查固定 HTTPS origin、PASS/CURRENT Gate 与审计；Gate 丢失仍允许暂停、撤销及紧急 credential 删除，避免安全控制反而阻断止损。

## 前端

- `features/market`：竞对清单和新建草稿已接 FR-05 真实 API，不再是静态占位页。
- `features/privacy-models`：11 类 FR-12 资源可创建、查询并执行当前状态允许的生命周期动作；同意撤回使用追加写入。
- `settings/ai-providers`：只消费公共 `BYOK_SECRET_GATE` 状态。只有未过期的 `PASS/CURRENT` 才启用后继轮换、写 Key、连接测试和激活；UNKNOWN/FAIL/STALE、请求失败或过期均禁用。暂停配置、撤销配置和紧急撤销 Key 不依赖 Gate，但仍由服务端鉴权、MFA、审计和删除编排约束。
- Key 输入默认空、`password` 类型、不回显；提交后清空。前端 Gate 不是安全边界，服务端仍必须在解析 secret body 前再次校验。

## 当前验证记录

```powershell
apps/backend/.venv/Scripts/python.exe -m pytest apps/backend/tests/contract/test_fr12_privacy_api.py apps/backend/tests/contract/test_openapi.py -q
apps/backend/.venv/Scripts/python.exe -m pytest apps/backend/tests/contract/test_schemathesis.py -q
apps/backend/.venv/Scripts/ruff.exe check apps/backend/src/biaice/modules/market/privacy apps/backend/src/biaice/api/market_privacy.py apps/backend/tests/contract/test_fr12_privacy_api.py apps/backend/tests/contract/test_schemathesis.py
apps/backend/.venv/Scripts/python.exe packages/contracts/scripts/generate_contracts.py --check
npm run lint --workspace @biaice/web
npm run typecheck --workspace @biaice/web
npm run test --workspace @biaice/web
npm run build --workspace @biaice/web
npm run test:e2e --workspace @biaice/web
```

当前 checkout 的实际结果：

- FR-12 + OpenAPI：13/13 通过。
- 共享 Schemathesis：175 个已实现 operation 节点全部通过。
- 全后端 pytest：302/302 通过（含共享 Schemathesis 175 个节点）；全后端 Ruff 通过。
- Web：22/22 Vitest、10/10 Playwright（桌面 Chromium + Pixel 7）通过；ESLint、typecheck、生产构建通过。
- 契约生成 `--check` 通过；状态报告为 369 个 operation，其中 174 个已实现、195 个仍为 contract-only。

上述结果证明当前合成/本地实现和契约一致，不等同于 PostgreSQL、Compose、安全 profile、真实个人信息或真实 Provider 的运行验收。

## 未关闭的交付 Gate

以下事项不能由代码或本成员代签，必须继续失败关闭：

1. `docs/stage-gates/M0-foundation.md` 仍为 `PENDING_GROUP_LEAD_SIGNATURE`，签署 YAML 仍是 `PENDING`。
2. `DEC-003`、`DEC-007`、`DEC-008` 仍为 `PENDING`；不得猜测来源白名单、Provider/model allowlist、跨境/训练/保留/预算或 DSR/事件/删除 SLA。
3. `BYOK_SECRET_GATE` 与 `REAL_DATA_MODE` 尚无已验证的 `PASS/CURRENT` 机器证据；HTTP/dev profile 不得接收真实 Key 或真实个人信息。
4. 18 个 Provider API handler 已解除 contract-only，但当前 checkout 仍没有获批的 OpenBao `SecretStorePort`、受控 ProviderRuntime/egress、远端副本删除 receipt 聚合或真实 Provider 验收；默认端口失败关闭，不能据此输入真实 Key。
5. 全项目另有 195 个其他 owner 的 operation 仍为 contract-only；它们不属于本成员实现范围，但会继续阻止全项目 M0 契约完成声明。
6. FR-12 与 Provider 元数据仓储当前为应用进程内存实现，只适用于合成/契约 profile；尚无 PostgreSQL 迁移、重启持久性、备份恢复或多实例一致性证据。

## 回滚方法

1. 使用审阅提交的 `git revert` 回滚，不重写共享历史。
2. 临时恢复 FR-12 合同占位时，移除 `main.py` 中 `market_privacy.router` 与服务配置，并恢复 `contract_stubs.py` 的 FR-12 stub 分区；同时重新生成契约产物。
3. 安全异常时保持 `BYOK_SECRET_GATE`/`REAL_DATA_MODE` 为 UNKNOWN/FAIL/STALE，并关闭 Provider 出网；不得通过前端解禁或测试豁免恢复能力。
