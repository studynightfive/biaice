# ADR-0001：模块化单体与本地优先部署

- 状态：Accepted for M0 scaffold
- 日期：2026-08-14
- 决策者：成员 1 技术基线；产品/安全 Gate 仍需组长签署

## 决定

使用单仓库、FastAPI 模块化单体和独立 Celery Worker。API 与 Worker 共用代码与容器镜像，通过启动命令区分。Next.js 使用标准 Node Runtime 自托管。Docker Compose 在组长电脑编排，`https://biaice.local:8443` 是真实数据模式的唯一 LAN 入口。

不使用 Sites、Cloudflare Worker Runtime、D1、R2、Wrangler、外部 CDN、远程字体或 ChatGPT 身份头。不部署本地生成式模型。

## 原因

七人团队需要可控的目录所有权、共享事务与契约、离线核心流程和可审计的单机恢复；七个微服务会放大迁移、部署、数据一致性和运维风险。

## 后果

- 模块边界必须通过 port/OpenAPI/outbox 强制，不能靠进程隔离兜底。
- PostgreSQL 是真状态，Redis 只承担 broker/cache。
- 只有 provider egress 可访问批准的模型域名；失败时人工路径仍可用。
- Production 高可用不在七人局域网项目的自动声明范围内。
