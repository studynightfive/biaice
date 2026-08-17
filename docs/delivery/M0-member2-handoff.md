# M0 成员 2 交接说明：项目、范围、规则与生命周期

状态：`IMPLEMENTED_SLICE / HUMAN_GATES_PENDING`

本次只交付成员 2 独占范围（FR-01）。没有修改成员 1 的 `main.py`、`core/**`、
`contract_stubs`、生成客户端、App Shell，也没有进入成员 3–7 目录。

## 独占范围

- 后端：`apps/backend/src/biaice/modules/projects/**`
- 后端：`apps/backend/src/biaice/modules/rules/**`
- 前端：`apps/web/src/features/projects/**`
- 前端：`apps/web/src/features/rules/**`

DecisionUnit 生命周期是成员 2 唯一 writer。其他成员只提交
`transition-commands`，不能直接追加 lifecycle event。

## 已实现

- 项目与 1–N 决策单元：创建草稿、列表、详情、草稿 PATCH、归档
- 生命周期：校验 transition command、追加写入、REOPENED 保存前态/后态/原因/依据/最早受影响阶段
- Scope / Regime / RuleSet / Clause / ComplianceReview / CrossLotConstraint
- 项目级继承与单元覆盖的确定性解析；冲突进入 `CONFLICT_REQUIRES_CONFIRMATION`
- PostgreSQL/SQLAlchemy 仓储（`infrastructure/sql_repository.py`）与 Alembic `m2_projects_rules_0001`
- 列表使用成员 1 的签名 cursor（`CursorCodec`）
- 文档事件消费骨架：`documents.source_document_released.v1` / `parse_completed.v1` / `document_quarantined.v1`
- 三个合成项目金标（公式、舍入、并列、冲突/阻断）
- 发布需要 maker ≠ checker；已发布条款不可 PATCH，纠正走 supersede
- BLOCKING 合规复核不能直接 CLOSED
- 多轮 → `MULTI_ROUND_UNSUPPORTED`；跨标段确认 → `PORTFOLIO_REVIEW_REQUIRED`
- 前端空 / 无权 / 冲突 / 过期边界，不显示默认 GO
- 追踪矩阵：`docs/traceability/projects.yaml`

事件（outbox 名称，载荷仍按现有 CONTRACT_ONLY 目录）：

- `rules.scope_assessment_published.v1`
- `rules.regime_published.v1`
- `rules.rule_set_published.v1`
- `rules.rule_set_revoked.v1`
- `rules.cross_lot_constraint_confirmed.v1`
- `rules.decision_unit_reopened.v1`
- `rules.decision_unit_lifecycle_advanced.v1`

## 成员 1 需要接入的一行（本分支不代改）

在 `create_app` 中、`contract_stubs` 之前：

```python
from biaice.modules.projects.application.services import configure_fr01
from biaice.modules.projects.http import router as projects_router
from biaice.modules.rules.http import router as rules_router

configure_fr01(app)
app.include_router(projects_router)
app.include_router(rules_router)
```

并在 `contract_stubs` 跳过已实现的 member-2 operation。OpenAPI / 生成客户端仍由成员 1 导出。

## 给成员 4 / 6 / 7

- 只读当前 `DecisionUnit.lifecycle_state`、已发布且 CURRENT 的 RuleSet/Clause
- 生命周期变化只发 `submit_decision_unit_transition_command`
- 草稿和未来生效规则不得当作正式输入
- BLOCKING 合规复核只允许探索

## 验证

```powershell
uv run --project apps/backend --extra test pytest apps/backend/tests/unit/test_fr01_projects.py apps/backend/tests/unit/test_fr01_gold.py -v
npm run test:web --workspace @biaice/web -- tests/components/projects.test.tsx tests/components/rules.test.tsx
```

## 回滚

删除本分支新增的 `modules/projects`、`modules/rules` 与对应 feature 文件即可。未改共享迁移历史，也未改 `main.py`。
