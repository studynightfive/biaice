"""Runnable FR-01 gold seeds: three synthetic projects, not live tenant data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from biaice.core.auth import TenantScope
from biaice.core.versioning import VersionMetadata
from biaice.modules.projects.application.repository import Fr01Repository
from biaice.modules.projects.domain.lifecycle import DecisionUnitLifecycleState
from biaice.modules.projects.domain.models import (
    DecisionUnit,
    ProcurementProject,
    ResourceLifecycle,
    ResourceValidity,
    canonical_hash,
)
from biaice.modules.rules.domain.models import (
    RoundKind,
    RuleClause,
    RuleClauseKind,
    RuleScopeLevel,
    RuleSet,
    ScopeAssessment,
    ScopeSupport,
)

NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)
FORMULA_EXPR = "weighted_sum:tech=0.4,price=0.6"
ROUNDING_HALF_UP = "half_up:2"
ROUNDING_TRUNC = "trunc:2"
TIE_EXPR = "order:score_desc,price_asc,bid_time_asc"


@dataclass(frozen=True)
class GoldProject:
    key: str
    project: ProcurementProject
    unit: DecisionUnit
    sibling: DecisionUnit | None
    formula: str | None
    rounding: str | None
    tie: str | None


def _version(actor_id: UUID, payload: dict) -> VersionMetadata:
    return VersionMetadata(
        version_id=uuid4(),
        version_number=1,
        created_at=NOW,
        created_by=actor_id,
        content_hash=canonical_hash(payload),
    )


def _project(*, tenant_id: UUID, domain_id: UUID, actor_id: UUID, name: str) -> ProcurementProject:
    return ProcurementProject(
        project_id=uuid4(),
        tenant_id=tenant_id,
        data_domain_id=domain_id,
        name=name,
        purchaser_name="合成采购人",
        timezone="Asia/Shanghai",
        lifecycle_state=ResourceLifecycle.PUBLISHED,
        validity_state=ResourceValidity.CURRENT,
        version=_version(actor_id, {"name": name}),
    )


def _unit(*, project: ProcurementProject, actor_id: UUID, name: str) -> DecisionUnit:
    return DecisionUnit(
        decision_unit_id=uuid4(),
        project_id=project.project_id,
        tenant_id=project.tenant_id,
        data_domain_id=project.data_domain_id,
        name=name,
        timezone="Asia/Shanghai",
        lifecycle_state=DecisionUnitLifecycleState.RULES_PENDING_CONFIRMATION,
        resource_lifecycle=ResourceLifecycle.PUBLISHED,
        validity_state=ResourceValidity.CURRENT,
        version=_version(actor_id, {"name": name}),
        gap_summary="金标合成单元",
    )


def _rule_set(
    *,
    unit: DecisionUnit,
    actor_id: UUID,
    title: str,
    scope_level: RuleScopeLevel,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
    lifecycle: ResourceLifecycle = ResourceLifecycle.PUBLISHED,
    validity: ResourceValidity = ResourceValidity.CURRENT,
) -> RuleSet:
    return RuleSet(
        rule_set_id=uuid4(),
        decision_unit_id=unit.decision_unit_id,
        project_id=unit.project_id,
        tenant_id=unit.tenant_id,
        data_domain_id=unit.data_domain_id,
        title=title,
        scope_level=scope_level,
        lifecycle_state=lifecycle,
        validity_state=validity,
        version=_version(actor_id, {"title": title}),
        effective_from=effective_from or NOW,
        effective_until=effective_until,
        confirmed_by=actor_id,
        confirmed_at=NOW,
    )


def _clause(
    *,
    rule_set: RuleSet,
    actor_id: UUID,
    kind: RuleClauseKind,
    coverage_key: str,
    expression: str,
    priority: int,
    text: str,
    lifecycle: ResourceLifecycle = ResourceLifecycle.PUBLISHED,
    validity: ResourceValidity = ResourceValidity.CURRENT,
) -> RuleClause:
    return RuleClause(
        rule_clause_id=uuid4(),
        rule_set_id=rule_set.rule_set_id,
        decision_unit_id=rule_set.decision_unit_id,
        project_id=rule_set.project_id,
        tenant_id=rule_set.tenant_id,
        data_domain_id=rule_set.data_domain_id,
        kind=kind,
        coverage_key=coverage_key,
        priority=priority,
        original_text=text,
        structured_expression=expression,
        confidence=1,
        lifecycle_state=lifecycle,
        validity_state=validity,
        version=_version(actor_id, {"coverage_key": coverage_key, "expression": expression}),
        confirmed_by=actor_id,
        confirmed_at=NOW,
    )


def seed_gold_projects(
    repository: Fr01Repository,
    *,
    scope: TenantScope,
    actor_id: UUID,
) -> dict[str, GoldProject]:
    scoring = _project(
        tenant_id=scope.tenant_id,
        domain_id=scope.data_domain_id,
        actor_id=actor_id,
        name="综合评分法合成项目",
    )
    scoring_unit = _unit(project=scoring, actor_id=actor_id, name="标段 A")
    project_set = _rule_set(
        unit=scoring_unit,
        actor_id=actor_id,
        title="项目级评分规则",
        scope_level=RuleScopeLevel.PROJECT,
    )
    unit_set = _rule_set(
        unit=scoring_unit,
        actor_id=actor_id,
        title="单元覆盖（与项目一致）",
        scope_level=RuleScopeLevel.DECISION_UNIT,
    )
    repository.upsert_project(scoring)
    repository.upsert_unit(scoring_unit)
    repository.upsert_rule_set(project_set)
    repository.upsert_rule_set(unit_set)
    for spec in (
        (RuleClauseKind.FORMULA, "score.formula", FORMULA_EXPR, 10, "综合评分 = 0.4技术 + 0.6价格"),
        (RuleClauseKind.ROUNDING, "price.rounding", ROUNDING_HALF_UP, 20, "四舍五入到分"),
        (RuleClauseKind.TIE, "score.tie", TIE_EXPR, 30, "得分高优先，同分低价，再早递交"),
        (RuleClauseKind.QUALIFICATION, "qual.license", "required:license", 40, "具备相应资质"),
        (RuleClauseKind.SCORING, "score.tech_weight", "weight:tech=0.4", 50, "技术分权重 40%"),
    ):
        kind, key, expr, priority, text = spec
        repository.upsert_clause(
            _clause(
                rule_set=project_set,
                actor_id=actor_id,
                kind=kind,
                coverage_key=key,
                expression=expr,
                priority=priority,
                text=text,
            )
        )
    repository.upsert_clause(
        _clause(
            rule_set=unit_set,
            actor_id=actor_id,
            kind=RuleClauseKind.ROUNDING,
            coverage_key="price.rounding",
            expression=ROUNDING_HALF_UP,
            priority=5,
            text="单元确认：四舍五入到分",
        )
    )

    lowest = _project(
        tenant_id=scope.tenant_id,
        domain_id=scope.data_domain_id,
        actor_id=actor_id,
        name="最低评标价法合成项目",
    )
    lowest_unit = _unit(project=lowest, actor_id=actor_id, name="标段 B")
    lowest_set = _rule_set(
        unit=lowest_unit,
        actor_id=actor_id,
        title="最低价规则",
        scope_level=RuleScopeLevel.DECISION_UNIT,
    )
    repository.upsert_project(lowest)
    repository.upsert_unit(lowest_unit)
    repository.upsert_rule_set(lowest_set)
    for spec in (
        (
            RuleClauseKind.SUBSTANTIVE,
            "substantive.delivery",
            "must:delivery_days<=30",
            10,
            "交货期实质性要求",
        ),
        (
            RuleClauseKind.ABNORMALLY_LOW,
            "price.abnormally_low",
            "flag:below_80pct_mean",
            20,
            "异常低价识别",
        ),
        (
            RuleClauseKind.VALID_SUPPLIER_COUNT,
            "supplier.valid_count",
            "min:3",
            30,
            "有效供应商不少于 3",
        ),
    ):
        kind, key, expr, priority, text = spec
        repository.upsert_clause(
            _clause(
                rule_set=lowest_set,
                actor_id=actor_id,
                kind=kind,
                coverage_key=key,
                expression=expr,
                priority=priority,
                text=text,
            )
        )

    conflict = _project(
        tenant_id=scope.tenant_id,
        domain_id=scope.data_domain_id,
        actor_id=actor_id,
        name="规则冲突与阻断合成项目",
    )
    conflict_unit = _unit(project=conflict, actor_id=actor_id, name="标段 C")
    sibling = _unit(project=conflict, actor_id=actor_id, name="标段 D")
    inherited = _rule_set(
        unit=sibling,
        actor_id=actor_id,
        title="项目级舍入（创建在兄弟单元）",
        scope_level=RuleScopeLevel.PROJECT,
    )
    override = _rule_set(
        unit=conflict_unit,
        actor_id=actor_id,
        title="单元舍入覆盖",
        scope_level=RuleScopeLevel.DECISION_UNIT,
    )
    future = _rule_set(
        unit=conflict_unit,
        actor_id=actor_id,
        title="未来生效草稿不得传播",
        scope_level=RuleScopeLevel.DECISION_UNIT,
        effective_from=NOW + timedelta(days=30),
        lifecycle=ResourceLifecycle.PUBLISHED,
    )
    repository.upsert_project(conflict)
    repository.upsert_unit(conflict_unit)
    repository.upsert_unit(sibling)
    repository.upsert_rule_set(inherited)
    repository.upsert_rule_set(override)
    repository.upsert_rule_set(future)
    repository.upsert_clause(
        _clause(
            rule_set=inherited,
            actor_id=actor_id,
            kind=RuleClauseKind.ROUNDING,
            coverage_key="price.rounding",
            expression=ROUNDING_HALF_UP,
            priority=10,
            text="项目级四舍五入到分",
        )
    )
    repository.upsert_clause(
        _clause(
            rule_set=override,
            actor_id=actor_id,
            kind=RuleClauseKind.ROUNDING,
            coverage_key="price.rounding",
            expression=ROUNDING_TRUNC,
            priority=1,
            text="单元改为截断到分",
        )
    )
    repository.upsert_clause(
        _clause(
            rule_set=future,
            actor_id=actor_id,
            kind=RuleClauseKind.TIE,
            coverage_key="score.tie",
            expression="order:random",
            priority=1,
            text="未来并列规则不得使正式结果过期",
        )
    )
    repository.upsert_scope(
        ScopeAssessment(
            scope_assessment_id=uuid4(),
            decision_unit_id=conflict_unit.decision_unit_id,
            project_id=conflict.project_id,
            tenant_id=conflict.tenant_id,
            data_domain_id=conflict.data_domain_id,
            support=ScopeSupport.MULTI_ROUND_UNSUPPORTED,
            round_kind=RoundKind.MULTI_ROUND,
            cross_lot=True,
            reason_codes=("MULTI_ROUND", "CROSS_LOT"),
            lifecycle_state=ResourceLifecycle.PUBLISHED,
            validity_state=ResourceValidity.CURRENT,
            version=_version(actor_id, {"support": "MULTI_ROUND_UNSUPPORTED"}),
            effective_from=NOW,
            confirmed_by=actor_id,
            confirmed_at=NOW,
        )
    )

    return {
        "comprehensive_scoring": GoldProject(
            key="comprehensive_scoring",
            project=scoring,
            unit=scoring_unit,
            sibling=None,
            formula=FORMULA_EXPR,
            rounding=ROUNDING_HALF_UP,
            tie=TIE_EXPR,
        ),
        "lowest_evaluated_price": GoldProject(
            key="lowest_evaluated_price",
            project=lowest,
            unit=lowest_unit,
            sibling=None,
            formula=None,
            rounding=None,
            tie=None,
        ),
        "conflict_and_blocks": GoldProject(
            key="conflict_and_blocks",
            project=conflict,
            unit=conflict_unit,
            sibling=sibling,
            formula=None,
            rounding=None,
            tie=None,
        ),
    }
