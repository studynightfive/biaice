# 公开仓库安全基线

公开源代码不得依赖“仓库私有”保护 secret。所有凭据只在运行时通过本机安全初始化生成或由操作者输入到受控存储。

## 提交前检查

1. `git diff --cached` 不含 `.env`、token、密码、私钥、真实主机/IP、用户导出或业务资料。
2. 运行仓库敏感信息扫描；对任何命中先撤销/轮换，再清理历史。
3. Compose 只引用变量名/secret 文件路径，不包含真实值。
4. OpenBao root token 与 unseal/recovery share 不进入环境变量、Compose、Git、镜像或日志。
5. Keycloak seed 只含七个合成测试账户模板；首次登录强制改密/MFA，生产密码不在 seed 中。
6. `.env.example` 只提供无价值占位符，不能直接用于 secure/real-data profile。

## CI 最小门槛

敏感信息扫描、依赖审计、前后端测试、OpenAPI 漂移、Compose 校验和禁止 Cloudflare/Sites 依赖检查必须通过。Critical 漏洞以及 RCE、跨租户、数据外泄类 High 不允许 waiver。
