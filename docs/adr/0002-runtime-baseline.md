# ADR-0002：M0 运行时版本基线

- 状态：Proposed（待依赖锁和镜像摘要验证后 Accepted）
- 日期：2026-08-14

## 已锁定架构族

| 层 | 基线 |
|---|---|
| Web | Next.js 16、React 19、TypeScript 5.9、Tailwind CSS 4 |
| API | Python 3.12、FastAPI、Pydantic v2、SQLAlchemy 2、Alembic |
| 数据 | PostgreSQL 16、Redis broker/cache、MinIO |
| 任务 | Celery；ingest/simulation/governance/provider + scheduler |
| 身份/网关/密钥 | Keycloak、Caddy local CA、OpenBao 非 dev |
| 文件/观测 | ClamAV、Poppler/PaddleOCR/LibreOffice；OpenTelemetry/Prometheus/Grafana/Loki |

精确 npm/Python patch 以提交的 lock file 为准；容器 tag 与 digest 以 `infra/versions.lock` 为准。升级、替换基础组件或改变兼容边界必须新增 ADR，不能直接改写本文件或共享历史。
