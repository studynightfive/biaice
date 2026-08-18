# M0 成员 6（仿真 / 决策基线 / 推荐资格）交接说明

状态：`IMPLEMENTED / HUMAN_GATES_PENDING`

本交接覆盖 FR-06/07/08/09a（决策基线、候选搜索空间、场景集、仿真批次、
优化运行、压力测试、方案合并、推荐资格、SHADOW_PILOT_LOCKED 快照）。
所有改动均复用 M0 既有 `biaice.core.*` 公共契约、`biaice.core.audit`
哈希链 AuditWriter、`biaice.core.outbox.EventEnvelope`、`biaice.core.clock`
、`biaice.core.db` 等基座；不引入新依赖、不修改既有成员 1-5 / 7 模块、
不动前端页面、不修改依赖锁或镜像锁。

## 架构约束

1. **路由优先级**：成员 6 的 36 个 `operationId` 由
   `apps/backend/src/biaice/api/simulation.py` 实现，`create_app` 在
   `app.include_router(contract_stubs.router)` **之前**注册
   `app.include_router(simulation.router)`，FastAPI first-match-wins
   保证命中真实 handler。`contract_stubs.py` 已跳过 `owner == "member-6"`
   的 operation（带注释说明成员 6 已在 simulation.router 提供实现）。
2. **不可变模型**：domain 全部使用 `ConfigDict(frozen=True, extra="forbid")`，
   13 个枚举（BaselineState / SearchSpaceState / ScenarioSetState /
   ScenarioKind / BatchState / OptimizationState / PlanState /
   EligibilityState / SnapshotState / AwardMode / ReviewValidity /
   ObjectiveKind / StressAxis）由 `biaice.modules.simulation.domain.models`
   提供。所有金额字段为 `DecimalStr`（pattern `^-?\d+(\.\d+)?$`，禁止
   binary float）。
3. **场景独立性**：`scenarios.freeze_scenarios` 强制 SEARCH/EVALUATION
   同时存在、权重归一化、搜索与评估空间版本不同、搜索空间必须先冻结；
   `stress.run_stress_tests` 拒绝任何 `stress_weight > 0` 的场景，
   保持 stress 轴永不进入概率分母。
4. **概率与 N_eff**：`probability.coverage` / `mc_ci` / `p_minus` / `p_plus` /
   `q_award_normalize` 全部返回 `is_undefined` 标志，denominator <
   threshold 时直接 `DENOMINATOR_BELOW_THRESHOLD` 而非伪造数字。
5. **方案合并**：`merge.merge_assessments` 仅接受 complete-linkage，
   强制 `tau_b / tau_m ∈ [0, 1]`、`tau_b + tau_m > 1` 时阻断为
   `PLAN_MERGE_BLOCKED`，禁止链式跨 tau_b / tau_m 合并。
6. **快照水印**：`snapshot.create_snapshot` 强制写入
   `SHADOW_PILOT_LOCKED` 水印，payload hash 与序列化结果必须一致，
   否则抛 `SNAPSHOT_PAYLOAD_HASH_MISMATCH`。
7. **推荐资格 fail-closed**：`eligibility.assess_eligibility` 在任一
   输入非 CURRENT 时返回 INDETERMINATE / INELIGIBLE；服务层在结束时
   调用 `assert_eligibility_for_recommendation`，不满足 ELIGIBLE 时抛
   `ELIGIBILITY_INPUT_UNKNOWN`。
8. **审计 / Outbox / Job**：所有写动作完成后 `await audit_writer.append`，
   并通过 `outbox_port.append` 写入对应 envelope；仿真批次 / 优化 /
   资格 / 快照任务通过 `biaice.worker.celery_app` 注册到 `biaice.simulation.*`
   队列，路由键已在 `biaice.worker.celery_app.task_routes` 中预置。
9. **真实状态**：`InMemorySimulationRepository` 是单一状态写入者（dict +
   `threading.Lock`），SQLAlchemy adapter 留作后续 PR。测试通过 fixture 注入。

## 独占目录

```
apps/backend/src/biaice/modules/simulation/
  __init__.py                  # re-export 子模块
  domain/__init__.py           # 纯函数与冻结模型
  domain/models.py             # 13 个枚举 + 不可变 Pydantic 模型
  domain/manifest.py           # 输入清单 SHA-256 + 基线陈旧检测
  domain/scenarios.py          # SEARCH/EVALUATION/STRESS 冻结 + 独立性
  domain/referee.py            # 确定性裁判 + review-pending 分离
  domain/static_validation.py  # 静态候选校验 + INDETERMINATE 阻断
  domain/probability.py        # p_minus / p_plus / coverage / mc_ci / n_eff
  domain/optimization.py       # 生成 / 排名 / 选择 (0-4 个方案)
  domain/stress.py             # stress 轴 + STRESS_AXIS_VIOLATED
  domain/merge.py              # complete-linkage + 链式阻断
  domain/eligibility.py        # 6 输入 → ELIGIBLE/INDETERMINATE/INELIGIBLE
  domain/snapshot.py           # SHADOW_PILOT_LOCKED 快照
  application/__init__.py      # 仓储 + 7 个 service 导出
  application/repository.py    # InMemorySimulationRepository
  application/services.py      # BaselineService / SearchSpaceService /
                               # ScenarioSetService / SimulationBatchService /
                               # OptimizationService / EligibilityService /
                               # SnapshotService

apps/backend/src/biaice/workers/simulation/
  tasks.py                     # biaice.simulation.* Celery 任务
  runtime.py                   # SimulationWorkerRuntime Protocol + Default

apps/backend/src/biaice/api/simulation.py   # 36 个真实 handler
apps/backend/migrations/versions/m6_simulation_0001_member6_simulation.py
apps/backend/tests/unit/test_simulation_models.py
apps/backend/tests/unit/test_simulation_probability.py
apps/backend/tests/unit/test_simulation_referee.py
apps/backend/tests/unit/test_simulation_optimization.py
apps/backend/tests/unit/test_simulation_eligibility.py
apps/backend/tests/unit/test_simulation_snapshot.py
apps/backend/tests/contract/test_simulation_api.py
docs/delivery/M0-member6-handoff.md
docs/traceability/simulation.yaml
```

## 可发布事件（outbox）

| 事件 | 触发动作 | 订阅者 |
|---|---|---|
| `simulation.decision_baseline_frozen.v1` | `freeze_decision_baseline` | 成员 1 治理、审计 |
| `simulation.scenario_sets_frozen.v1` | `freeze_scenario_set` | 治理、审计 |
| `simulation.simulation_started.v1` | `create_simulation_batch` | 治理、队列调度 |
| `simulation.simulation_failed.v1` | 失败终结 | 治理告警 |
| `simulation.simulation_assessed.v1` | 评估产出 | 审计、推荐资格 |
| `simulation.strategy_plans_finalized.v1` | `finalize_optimization_run` | 审计 |
| `simulation.eligibility_assessed.v1` | `assess_eligibility` | 审计、推荐资格 |
| `simulation.simulation_snapshot_created.v1` | `create_simulation_assessment_snapshot` | 审计 |

## Stage Gate 依赖

- 上游契约冻结：`ScopeAssessment / Regime / RuleSet / ComplianceReview` 必须
  处于 PUBLISHED（成员 2 拥有）。
- `CostBaselinePublished` 与 `CommercialPolicyPublished`（成员 4）必须
  FROZEN 后才能 freeze_decision_baseline。
- `ProviderPolicyApproved`（成员 5）必须 CURRENT 才能将 LLM 评分场景
  纳入概率分母；缺失时场景进入 review-pending 集合。
- `RiskAccepted`（成员 7）必须存在才能使 `recommendation_eligibility`
  进入 ELIGIBLE。

## 已知限制

- In-memory 仓储仅用于 M0 阶段；PostgreSQL adapter 与 RLS 策略
  （与成员 1 治理 schema 对齐）需要单独 PR。
- 真实物理仿真由 `DefaultSimulationRuntime` 实现确定性 stub；
  接入 NumPy / OR-Tools / OptiCL 后保持 Protocol 不变。
- SHADOW_PILOT_LOCKED 水印永久固化，不允许生产模式覆盖；
  MVP-A / Pilot 范围必须由组长与全体 owner 重新评审并出 AD。
- 不修改 `apps/backend/src/biaice/core/*`，不复写 `auth.py` / `errors.py`。

## 验证命令

```powershell
py -3.12 -m pip install --user pydantic-settings pyjwt redis psycopg sqlalchemy alembic celery
cd apps/backend
PYTHONPATH=src py -3.12 -m pytest tests/unit/test_simulation_models.py tests/unit/test_simulation_probability.py tests/unit/test_simulation_referee.py tests/unit/test_simulation_optimization.py tests/unit/test_simulation_eligibility.py tests/unit/test_simulation_snapshot.py -v
PYTHONPATH=src py -3.12 -m pytest tests/contract/test_simulation_api.py -v
PYTHONPATH=src py -3.12 -m pytest tests -q -k simulation
```

期望：33 项单元测试 + 5 项契约测试全部通过。

## 回滚方法

1. `git revert <commit>` 回滚本成员 6 PR；不要重写共享历史。
2. 数据库只追加 Alembic revision `m6_simulation_0001`，未触及既有
   `0001_core_governance`，downgrade 由 forward-only 守卫阻断；
   如需恢复，按 `infra/backup/restore-materials.sh` 顺序从 OpenBao →
   Keycloak → 业务库 → 对象与审计 → 墓碑/outbox 回滚。
3. 路由注册顺序在 `biaice.main.create_app` 中显式注释；如需临时关闭
   成员 6 真实路由，将 `simulation.router` 注释恢复 501 stub：
   `app.include_router(simulation.router)` 改为 `app.include_router(contract_stubs.router)`
   即可再次落入 stub（不要回滚 `contract_stubs.py` 的 skip 逻辑以免
   双重注册）。
4. 安全能力异常时：关闭 `provider-egress` / 真实数据开关并回到
   `synthetic_http`，按既有事故 runbook 处理。

## 待后续 PR 的人工 Gate

- REAL_DATA_MODE 12 项机器证据（REAL_DATA_MODE 当前依赖成员 1 平台）。
- TOTP MFA 双设备并发（成员 1 + 成员 6 共同验收）。
- ProviderPolicyApproved 完整链路（成员 5）。
- 数据库 SQLAlchemy adapter + RLS 策略。
- 真实物理仿真 NumPy / OptiCL adapter。
- 真实审计 sink（PostgreSQL `audit_event` 表 + 独立信任域 anchor）。
