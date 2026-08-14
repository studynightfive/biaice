# 安全 Gate 契约

## 共同证据模型

`GateAssessmentVersion` 是不可变版本，至少保存 `gate_id`、`result`、`validity_state`、`assessed_at`、`expires_at`、`assessor`、`evidence_refs`、`evidence_hash`、`load_profile_version`、`waiver_policy` 和 `reason_codes`。任一证据缺失、过期、无法验证或 hash 不一致，结果为 `UNKNOWN/STALE/FAIL`，不能沿用历史 PASS。

## BYOK_SECRET_GATE

真实 Key 写入、连接测试、读取供 egress 使用或 Provider 出网前必须 `PASS/CURRENT`。HTTP/dev/OpenBao-dev 在解析 credential body 前拒绝；`waiver_policy=PROHIBITED`。证据至少覆盖：受信 HTTPS/MFA/重认证、OpenBao 非 dev 与 2-of-3 仪式、write-only/exact-read 短期策略、审计、租户隔离、目录/egress hash、SSRF/DNS/redirect/TLS 防护、限额和泄漏负测。

## REAL_DATA_MODE

真实投标资料或个人信息进入前，PRD V1.3 的 12 项证据必须全部 `PASS/CURRENT`，无 waiver。该 Gate 可以在无 API Key 时通过，但不会授权外部模型调用。

## 每次 Provider 调用

每次调用原子复核 ACTIVE/CURRENT 配置、credential version、BYOK Gate、按输入分类决定是否要求 REAL_DATA Gate、Policy/PIA/跨境/训练禁用、最小化、预算/并发、审计/派生资产以及最终 egress host/IP/TLS/redirect。任一失败不得发送请求，并返回稳定 reason code 与人工路径。

## 连接测试

连接测试只接受配置 ID，不接受 prompt、文件、asset ref、project/unit 数据或 URL。服务端生成固定合成探针；成功只转 `VALID/VERIFIED`，绝不自动 ACTIVE。
