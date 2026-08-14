# 安全策略

## 支持范围

当前仅支持 M0 合成/脱敏开发模式。真实数据、真实 API Key、Provider 出网与 Production 能力尚未获准，发现相关入口可绕过 Gate 应视为高优先级安全问题。

## 报告漏洞

不要在公开 Issue、Discussion、PR 日志或截图中披露漏洞利用步骤、密钥、个人信息或真实投标材料。请由仓库负责人建立私密沟通渠道后再发送最小必要信息；在渠道未建立前，仅通知负责人“存在安全问题”，不要附敏感载荷。

## 永不提交

- `.env`、真实密码、API Key、token、Cookie、证书私钥；
- OpenBao root token、unseal/recovery share、AppRole secret；
- Keycloak 管理员密码和真实用户导出；
- 真实采购文件、竞对资料、个人信息、成本明细、原始提示词/响应；
- PostgreSQL/MinIO/Redis 数据卷、备份、日志、trace 或抓包；
- 本地 CA 私钥和设备信任清单。

一旦误提交，立即停止使用并在 Provider/身份系统撤销或轮换；仅从 Git 历史删除字符串不能恢复密钥安全性。

## 安全默认值

- HTTP/dev profile 在解析 credential body 前拒绝真实 Key，并禁用 Provider 出网。
- `BYOK_SECRET_GATE` 与 `REAL_DATA_MODE` 任一证据 UNKNOWN/FAIL/STALE 时失败关闭。
- 只有 gateway 可发布局域网端口，管理面只绑定组长本机或受控管理网。
- 系统管理员默认无正文、成本和商家 Key 明文权限。
