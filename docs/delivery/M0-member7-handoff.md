# M0 成员 7 交接说明：RiskAcceptance（FR-09b MVP-B 切片）

状态：`IMPLEMENTED_SLICE / HUMAN_GATES_PENDING`

本次交付是成员 7 在 M0/MVP-B 的第一个可运行切片：`RiskAcceptanceVersion`
创建、列表、读取与撤销。它只开放 MVP-B 允许的 RiskAcceptance 能力，不开放
审批、授权、报告、提交或结果；Pilot 前这些能力仍由静态挂载点与 501 stub
承载。

## 交付范围

- `biaice.modules.approvals_reports`：冻结 Pydantic 模型、In-memory 仓储与
  `RiskAcceptanceService` 单写者。
- `biaice.api.approvals_reports`：4 个真实 handler
  （create/list/get/revoke_risk_acceptance），注册于 contract_stubs 之前。
- 权限：`fr-09b:read/create/revoke`；创建与撤销要求 MFA。
- 事件：`approvals_reports.risk_accepted.v1` 与
  `approvals_reports.risk_revoked.v1`。
- 迁移：`m7_approvals_reports_0001`（`risk_acceptance` 表）。
- 测试：单元 + 契约，覆盖空状态、幂等、maker-checker、有效期、撤销、权限、
  MFA 与 scope 隔离。

## 架构约束

1. **单写者**：只有 `RiskAcceptanceService` 写入 `RiskAcceptance`；成员 6 只能
   读取当前版本，不能创建同名对象。
2. **maker-checker**：`created_by != independent_approver_id`，
   `accepted_by == independent_approver_id`；否则返回
   `MAKER_CHECKER_REQUIRED`。
3. **追加不可变**：撤销产生 `REVOKED / INVALIDATED` 新版本，带撤销人、时间与
   原因；不覆盖历史。
4. **有效期**：`valid_until > valid_from`；读取时按当前时间投影
   `EXPIRED / EXPIRED`，不修改持久化历史。
5. **失败关闭**：已撤销或已过期对象拒绝再次撤销；未知/过期状态不会伪装成
   `CURRENT`。
6. **审计与事件**：create/revoke 均写 AuditEvent 和对应 outbox 事件，载荷只含
   去标识化 ID/状态，不携带正文或敏感材料。
7. **范围**：仓储按 tenant/data-domain/decision-unit scope 过滤，越界表现为
   404，不泄露存在性。

## 依赖与边界

- 成员 6 的 `RecommendationEligibility` 需要 `RiskAccepted` 作为上游输入；
  本切片是成员 7 对成员 6 的第一个真实契约。
- 条件核验仍由成员 4 独占；成员 7 只调用公开 command port，不直写条件表。
- 生命周期迁移仍由成员 2 独占；成员 7 只发 `DecisionUnitTransitionRequested`。
- 完整审批/报告/提交/结果继续按 Pilot Gate 顺序接入，本分支不开放。

## 已知限制

- In-memory 仓储用于 M0；SQLAlchemy adapter 与 RLS 策略需要后续 PR。
- `contract_stubs.py` 已跳过 4 个已实现 operation；OpenAPI/生成客户端仍由
  成员 1 在契约 PR 中重新导出，本分支不手改生成目录。
- 独立授权角色目前以 `independent_approver_id` 记录在创建请求中；真实
  approval step/maker-checker 工作流在 Pilot 阶段接入。

## 验证命令

```powershell
uv run --project apps/backend --extra test pytest apps/backend/tests/unit/test_risk_acceptance.py -v
uv run --project apps/backend --extra test pytest apps/backend/tests/contract/test_approvals_reports_api.py -v
```

## 回滚方法

1. `git revert <commit>` 回滚本 PR；不重写共享历史。
2. 数据库只追加 `m7_approvals_reports_0001`，未触及既有迁移；多 head 由成员 1
   合并。
3. 临时关闭真实路由：移除 `main.py` 中
   `app.include_router(approvals_reports.router)` 并恢复 contract_stubs 跳过
   集合，即回落到 501 stub。

