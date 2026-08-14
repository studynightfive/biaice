# Windows 本地开发手册

## 1. 准备

安装 Docker Desktop、Node.js 22+、Python 3.12 与 Git。克隆仓库后运行 `scripts/init.ps1`，由脚本生成被 Git 忽略的 `.env.local` 和七个合成测试账户密码文件；不得填入真实 API Key、OpenBao root token 或真实账户密码。

合成账号首次使用后，如需重新执行首次改密/TOTP 流程，只显式轮换这七个账号的临时密码，再运行幂等 Keycloak 初始化；该开关不会轮换数据库、Redis 或其他基础设施凭据：

```powershell
.\scripts\init.ps1 -EnvFile .env.local -RotateSyntheticPasswords
docker compose --env-file .env.local --profile init run --rm keycloak-init
```

## 2. 安装与静态验证

```powershell
npm ci
uv sync --project apps/backend --locked --extra test
npm run contracts:check
python scripts/validate_compose_topology.py
```

## 3. 启动

```powershell
.\scripts\dev.ps1
```

默认启动 `synthetic_http` 合成数据 profile 并显示本机 URL 与统一 LAN 名称。开发 HTTP 模式必须保持 `BYOK_SECRET_GATE`、Provider egress 和真实数据关闭。

## 4. 测试与停止

```powershell
.\scripts\test.ps1
.\scripts\stop.ps1
```

## 5. 局域网接入

组长为 `biaice.local` 建立统一 DNS/hosts 解析；不得把临时 IP 写进业务配置。`host-ingress` 仅允许 gateway 加入并承担宿主端口发布；真实数据 Gate 还必须以宿主防火墙证明 gateway 无主动公网出口。secure profile 使用 Caddy local CA，根证书只通过受控渠道分发并记录设备安装、续期、吊销和移除。

## 6. 备份/恢复

仅使用 `scripts/backup.ps1` 与 `scripts/restore.ps1`。备份不得包含 OpenBao root token/unseal share；恢复顺序先恢复密钥可用性和墓碑，再恢复数据并验证删除对象未复活。任何恢复演练都只能使用合成数据，直至 `REAL_DATA_MODE` 正式签署。
