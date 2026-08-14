# M0 成员 1 追踪矩阵

状态说明：`IMPLEMENTED` 表示有可运行骨架和测试；`SCAFFOLDED` 表示接口/失败关闭已建立但依赖后续 owner adapter；`BLOCKED_BY_GATE` 表示按设计不可启用；`PENDING_HUMAN_SIGNATURE` 不能由代码自动完成。

| 需求 | 负责人 | 产物 | 验证 | 状态 |
|---|---|---|---|---|
| 标准 Next.js Node 与 App Shell | M1 | `apps/web` | lint/typecheck/test/build | IMPLEMENTED |
| 公共 API/错误/身份/scope | M1 | backend core + OpenAPI | pytest + contract drift | IMPLEMENTED |
| Job/outbox/reconciliation 基座 | M1 | backend core/workers | 幂等/状态测试 | SCAFFOLDED |
| append-only AuditWriter/哈希链 | M1 | governance audit | 断链与 sink 故障负测 | SCAFFOLDED |
| FR-11 血缘/失效/保留/保全/删除 | M1 | governance modules/worker | receipt 聚合与幂等测试 | SCAFFOLDED |
| 成员 3 本地副本 adapter | M3 | documents adapter | M3 PR | BLOCKED_BY_OWNER |
| 成员 5 Provider 副本 adapter | M5 | model governance adapter | M5 PR | BLOCKED_BY_OWNER |
| Compose 本地拓扑 | M1 | `compose*.yaml`, `infra/**` | compose config/端口检查 | IMPLEMENTED |
| Windows 启停/测试/备份恢复 | M1 | `scripts/*.ps1` | PowerShell 静态/合成演练 | IMPLEMENTED |
| BYOK_SECRET_GATE | M1 平台 + M5 消费 | core middleware/network switch | 负向测试 | BLOCKED_BY_GATE |
| REAL_DATA_MODE | M1 | startup predicate/evidence | 12 项机器证据 | BLOCKED_BY_GATE |
| OpenBao 2-of-3/root token 仪式 | M1 + 人工双控 | `infra/openbao`, runbook | 现场演练记录 | PENDING_HUMAN_SIGNATURE |
| 七台设备 CA/MFA/LAN 验收 | M1 + 七名成员 | Caddy/Keycloak/runbook | 两设备并发后扩展七台 | PENDING_HUMAN_SIGNATURE |
| M0 OpenAPI/状态/权限签署 | 组长 | `docs/stage-gates/M0-foundation.md` | 签名+commit SHA | PENDING_HUMAN_SIGNATURE |

本矩阵不把未完成的成员 2–7 领域功能标记为已交付。
