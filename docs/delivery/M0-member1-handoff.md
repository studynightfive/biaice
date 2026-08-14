# M0 成员 1（组长）交接说明

状态：`IMPLEMENTED_SCAFFOLD / HUMAN_GATES_PENDING`

本次交付建立七人并行开发所需的平台和强制契约，不包含成员 2–7 的领域业务实现，也不代表真实数据、真实 API Key、Pilot 或 Production 已获批准。

## 架构决定

- 标准 Next.js Node Web + FastAPI 模块化单体 + 四类 Celery Worker；PostgreSQL 是业务真状态。
- 仅 Caddy `gateway` 发布局域网端口；数据库、Redis、MinIO、Keycloak、OpenBao 和 ClamAV 只在内部网络。
- 浏览器认证和 `/api/v1/*` 必须经过 Web BFF；令牌只存 HttpOnly Cookie，FastAPI 不直接向浏览器签发会话。
- tenant、data-domain、project 和 decision-unit 作用域由服务端身份上下文决定；PostgreSQL 运行账户为 `NOSUPERUSER/NOBYPASSRLS`。
- Provider 出网 profile 默认关闭；Gate 证据必须 PASS/CURRENT、未过期、allowlist hash 一致且 HMAC 签名有效，每次 CONNECT 仍需原子单次授权。
- 真实数据与 BYOK 是两个独立、禁止 waiver 的 Gate。默认 `synthetic_http` 下二者均失败关闭。
- 依赖和容器镜像均锁定；Python 生产/测试 requirements 带完整传递 hash，第三方镜像使用不可变 digest。

详细决定见 `docs/adr/`、`docs/architecture/` 与 `docs/security/gates.md`。

## 运行方式

```powershell
git clone https://github.com/studynightfive/biaice.git
cd biaice
npm ci
uv sync --project apps/backend --locked --extra test
.\scripts\init.ps1
.\scripts\dev.ps1
```

默认地址是 `http://localhost:8080` 和 `http://biaice.local:8080`；脚本会动态显示 LAN 探测地址，不把本机 IP 写入仓库。停止使用 `.\scripts\stop.ps1`。

## 服务健康

| 范围 | 健康/就绪契约 | 当前结论 |
| --- | --- | --- |
| Web | `GET /api/health` | 构建镜像并实际返回 200 |
| API 进程 | `GET /health/live` | 已实现并测试 |
| API 依赖 | `GET /health/ready` | 检查迁移表、PostgreSQL、双 Redis、OIDC JWKS、MinIO、ClamAV 与审计状态；失败返回非就绪 |
| Keycloak | `/health/ready` | realm、7 个合成账号、PKCE 回调、首次改密、作用域令牌与注销已在真实 Compose/Chrome 验证；TOTP 仍待双设备人工验收 |
| gateway | `/_gateway/health` | Caddy 配置已实际 validate；宿主 `0.0.0.0:8080` 与唯一发布端口已实测 |
| OpenBao | 进程 health 与能力 Gate 分离 | 未初始化或 sealed 绝不等同 BYOK 可用 |
| provider egress | `/health` + 每次 Gate 重检 | 默认 profile 关闭；缺签名密钥或授权端点能力即退出/拒绝 |

## 公共契约版本

- 基线：`m0.1`，状态为 `CANDIDATE`，待组长与全体 owner 评审签署。
- OpenAPI：369 个唯一 operation；其中 16 个公共/平台基础 operation 有实现与测试，353 个成员领域 P0 operation 明确标记 `x-contract-only=true` 并返回 RFC 7807 `501 CONTRACT_ONLY`。
- Schemathesis 对 16 个已实现 operation 执行真实 ASGI 属性测试；353 个 contract-only operation 只由完整元数据分区和共享认证/幂等/501 行为测试覆盖，不冒充逐 operation 业务测试。
- 已生成 OpenAPI、错误目录、事件目录、traceability、manifest hash 和 TypeScript 客户端。
- CI 对导出漂移、向后不兼容变更、生成客户端编译、Schemathesis、权限负向用例、secret、依赖漏洞和拓扑执行失败关闭检查。

## 待接模块

- 成员 2–7：各自 feature 的字段级 Schema、handler、页面业务状态和测试；当前仅有静态挂载点与契约占位。
- 成员 3：本地文件、MinIO、解析副本及删除 receipt adapter。
- 成员 5：Provider 配置/调用业务、OpenBao adapter、原子单次 egress grant store 和外部副本删除 receipt adapter。
- 成员 6/7：仅在上游契约与对应 Stage Gate 冻结后接入正式评估和报告审批。

## 已知限制与人工 Gate

- 整套默认 Compose 已启动且全部长期服务健康；真实 Chrome 已完成非 MFA 合成账号的 PKCE 登录、首次改密、回调、`/api/v1/me`、注销和注销后 401。TOTP、两台设备并发、服务重启恢复及备份/恢复仍需现场演练，不能勾选对应最终验收项。
- OpenBao 2-of-3 份额分持、初始 root token 撤销/封存、审计设备和恢复仪式必须由至少两名人员现场执行，代码不能代签。
- append-only audit、MinIO、信封加密、OpenBao SecretStore 和 Provider egress 的真实 adapter 未配置时均失败关闭；这不是 Production 能力。
- Web、API、Keycloak 与 provider-egress 四个自建镜像均已在组长电脑实际构建；完整默认多服务启动和非 MFA OIDC 回调已有记录，TOTP 与故障恢复仍待人工记录。
- 本机尚未永久配置 `biaice.local` 解析；本次 Chrome smoke 使用临时 host resolver。双设备验收前必须由组长在受控 hosts/LAN DNS 中解析到组长机，不能把动态 IP 写入仓库。
- Docker Desktop 发布端口需要仅 gateway 使用的非内部 `host-ingress` bridge。真实数据 Gate 必须额外验证宿主防火墙阻断 gateway 主动公网连接；Provider 出网仍只能经默认关闭的专用 egress profile。
- `REAL_DATA_MODE` 12 项证据、BYOK 安全 Gate、MVP-A 试点范围、算法参数和 Pilot 统计协议均未签署。

## 验证入口

```powershell
npm run lint
npm run typecheck
npm run test:web
npm run test:e2e:ci --workspace @biaice/web
uv run --project apps/backend --extra test pytest apps/backend/tests
python packages/contracts/scripts/generate_contracts.py --check
python scripts/contracts/check_contract_status.py
python scripts/security/scan_secrets.py
python scripts/verify_no_legacy.py
.\scripts\test.ps1 -EnvFile .env.example -StaticOnly
```

本地收口记录：后端 59 项、Web Vitest 15 项、Playwright/axe 8 项均通过；跨 Python 3.12/3.13 契约确定性、依赖审计、Compose 拓扑、真实多服务健康及上述 Chrome OIDC 生命周期也均通过。测试的最终数量与 CI 链接仍以对应提交/PR 为准，不能用本文件替代运行记录。

## 回滚方法

1. 平台代码回滚使用已审阅提交的 `git revert`，不得重写共享历史或 force-push `main`。
2. 数据库只追加 Alembic revision；共享迁移不可修改。破坏性降级必须走恢复演练和精确双重确认。
3. 运行时版本回滚需同时回滚依赖锁、镜像 digest、OpenAPI 产物和 manifest hash，并重新执行完整 CI。
4. 安全能力异常时先关闭 `provider-egress`/真实数据开关并回到 `synthetic_http`；不得通过跳过 Gate 恢复服务。
5. 备份/恢复严格按 OpenBao/Caddy CA → Keycloak → 业务库 → 对象与审计 → 墓碑/outbox 顺序；缺少冻结/重放 adapter 时安全 profile 会拒绝继续。
