# M0 平台与契约签署单

状态：`PENDING_GROUP_LEAD_SIGNATURE`

本文件是可审阅签署单，不代表自动批准。组长填写姓名/GitHub handle、提交 SHA、日期与决定后才生效。签署前只允许平台骨架、静态 feature 壳、合成 fixture 与契约评审。

## A. OpenAPI 基线

- [ ] 公共与 FR-01 至 FR-13 的 P0 operation 均有唯一 method/path/operationId
- [ ] Pydantic stub 是接口源，OpenAPI 快照由代码导出且 CI 检查漂移
- [ ] 请求/响应、枚举、权限、幂等、ETag、错误码与 UI 字段可追踪
- [ ] 生成 TypeScript 客户端只读，成员不自建 mock Schema

## B. 状态与权限基线

- [ ] `docs/architecture/state-catalog.yaml` 的正交状态已评审
- [ ] DecisionUnit 生命周期、Condition、RiskAcceptance、报告和治理单写者已确认
- [ ] `docs/architecture/rbac-matrix.md` 的 maker-checker 与系统管理员默认拒绝已确认
- [ ] tenant/data-domain/project/unit scope 与 PLATFORM 例外已确认

## C. 目录与依赖

- [ ] 七名成员确认 `docs/architecture/ownership.yaml`
- [ ] 契约 PR 先于功能 PR；成员只追加自己的迁移
- [ ] 成员 6/7 的依赖顺序和 Pilot 前限制已确认

## D. 安全默认值

- [ ] 合成 profile 禁止真实 Key、Provider 出网和真实数据
- [ ] `BYOK_SECRET_GATE` 与 `REAL_DATA_MODE` 独立、机器可验证、禁止 waiver
- [ ] 未决项 UNKNOWN/FAIL/STALE 时正式流程失败关闭

## 决定

```yaml
decision: PENDING # APPROVE / REJECT
baseline_version: m0.1
commit_sha: PENDING
approved_by: PENDING
approved_at: PENDING
conditions: []
```

## 仍需另行签署（不能由代码代替）

1. MVP-A 首个试点制度、行业、采购方式、评标方法和规则范围；
2. `REAL_DATA_MODE` 12 项机器证据；
3. 平衡目标变量、Z 标准化边界/零方差、精确枚举上限、代理 CVaR；
4. Pilot 独立样本、基线、ECE 与统计非劣协议。
