# M0 成员 4 交接说明：证据、预审与商业就绪（FR-03 / FR-04）

状态：`IMPLEMENTED / HUMAN_GATES_PENDING`

本次交付覆盖 FR-03/FR-04 P0 catalog 的全部 member-4 operation（含冻结的
`create_evidence_matche` / `get_commercial_policie` 等拼写）。前端
`features/evidence` 与 `features/commercial` 读取真实 API，空/加载/无权/错误态齐全。

## 交付范围

- `biaice.modules.evidence`：Requirement、CompanyEvidence、EvidenceMatch、
  ResponseProfile、Precheck、Condition（唯一 writer）。
- `biaice.modules.commercial`：CostBaseline、CommercialPolicy、StrategyReadiness。
- 模块路由与服务已实现；平台 `main.py` / `contract_stubs.py` / `core/auth.py` /
  `core/errors.py` 保持 `origin/main` 初始定义，避免与成员 3/7 合入冲突。
- 文档对接：消费 `app.state.document_read_port`（成员 3 刷新后的
  `get_released_document`）。未接线或未 RELEASED 时禁止引用，匹配不得自动满足。
- 条件命令端口：`app.state.condition_command_port`（satisfy/waive/fail/expire），
  供成员 7 使用；审批模块不得直写条件表。
- 就绪只读端口：`app.state.evidence_readiness_port` 供 FR-04 聚合；市场项消费
  `app.state.market_readiness_port`，缺失则为 UNKNOWN，不伪造先验。
- 迁移：`m4_evidence_commercial_0001`（独立 Alembic head）。

## 架构约束

1. 无证据 / 证据失效 / 强制项缺匹配行 → UNKNOWN，永不自动 SATISFIED。
2. Precheck 不读取成本、利润、市场或竞对。
3. 成本 `created_by != approved_by`；未批准 `exploration_only=true`。
4. 商业不通过使用 `commercial_not_procurement=true`，文案不得写成投标无效。
5. 不进入 documents/projects/simulation/approvals 目录。

## 平台接线（请组长 / 成员 1 合并后接线）

为避免 PR 冲突，本分支已把下列已有定义文件恢复为 `origin/main`：

`core/auth.py`、`core/errors.py`、`main.py`、`contract_stubs.py`、
`tests/contract/test_openapi.py` / `test_schemathesis.py`、
`packages/contracts/*generated*`。

合入后请成员 1：

1. 注册 `fr-03:*` / `fr-04:*` 权限（SYSTEM_ADMIN 仍不得读写成本/证据）。
2. 登记 FR-03/04 稳定错误码。
3. 在 `create_app` 中 `configure_evidence` → `configure_commercial`，并在
   `contract_stubs` 之前 `include_router`。
4. 运行 `python packages/contracts/scripts/generate_contracts.py`。

接线前，平台 `create_app()` 对 member-4 catalog 路由仍返回 501 CONTRACT_ONLY。

## 验证命令

```powershell
uv run --project apps/backend --extra test pytest apps/backend/tests/unit/test_evidence.py apps/backend/tests/unit/test_commercial.py apps/backend/tests/contract/test_evidence_commercial_api.py -v
npm --prefix apps/web test -- tests/components/evidence.test.tsx tests/components/commercial.test.tsx
```

## 交叉待确认（最终同步）

1. 成员 2 的 `rule_availability_port` 未接线，预审 `rules_available=null`，不能 PASS。
2. 成员 3 已合入 main 后，`document_read_port` 仍需成员 1 在 `create_app` 接线；未接线时带文档引用的证据创建失败关闭。
3. 成员 5 市场/模型 port 未接线，就绪市场/用途/模型为 UNKNOWN。
4. 成员 6 场景协议项固定 UNKNOWN。
5. 成员 7 应从 `app.state.condition_command_port` 关闭条件。
6. Catalog 冻结了 `evidence_matche` / `commercial_policie` 拼写，未擅自改 path。
