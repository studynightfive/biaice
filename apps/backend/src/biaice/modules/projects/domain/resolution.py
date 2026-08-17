"""Deterministic project inheritance vs decision-unit override (member 2)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from biaice.modules.projects.domain.models import ResourceLifecycle, ResourceValidity
from biaice.modules.rules.domain.models import (
    ResolutionStatus,
    RuleClause,
    RuleScopeLevel,
    RuleSet,
    RuleResolution,
)


def rule_set_is_effective(rule_set: RuleSet, *, now: datetime) -> bool:
    if rule_set.validity_state is not ResourceValidity.CURRENT:
        return False
    if rule_set.effective_from is not None and rule_set.effective_from > now:
        return False
    if rule_set.effective_until is not None and rule_set.effective_until <= now:
        return False
    return True


def clause_participates(clause: RuleClause, *, formal: bool) -> bool:
    if clause.validity_state is not ResourceValidity.CURRENT:
        return False
    if formal:
        return clause.lifecycle_state is ResourceLifecycle.PUBLISHED
    return clause.lifecycle_state in {ResourceLifecycle.DRAFT, ResourceLifecycle.PUBLISHED}


def _expression(clause: RuleClause) -> str:
    return clause.structured_expression or clause.original_text


def _winner(clauses: Sequence[RuleClause]) -> RuleClause:
    return sorted(clauses, key=lambda item: (item.priority, str(item.rule_clause_id)))[0]


def _conflict(key: str, clauses: Sequence[RuleClause], detail: str) -> RuleResolution:
    return RuleResolution(
        coverage_key=key,
        status=ResolutionStatus.CONFLICT_REQUIRES_CONFIRMATION,
        winning_clause_id=None,
        conflicting_clause_ids=tuple(item.rule_clause_id for item in clauses),
        detail=detail,
    )


def resolve_inherited_clauses(
    *,
    clauses: Sequence[RuleClause],
    rule_sets: Sequence[RuleSet],
    now: datetime,
    formal: bool = True,
) -> tuple[RuleResolution, ...]:
    """Resolve coverage keys without last-write-wins.

    Project-level CURRENT clauses are inherited. A decision-unit override wins
    only when its structured expression matches the inherited one, or when no
    project clause exists. Disagreeing expressions require confirmation.
    Draft and future-dated versions are excluded from formal resolution.
    """

    sets = {item.rule_set_id: item for item in rule_sets}
    grouped: dict[str, list[tuple[RuleClause, RuleSet]]] = {}
    for clause in clauses:
        rule_set = sets.get(clause.rule_set_id)
        if rule_set is None:
            continue
        if not rule_set_is_effective(rule_set, now=now):
            continue
        if formal and rule_set.lifecycle_state is not ResourceLifecycle.PUBLISHED:
            continue
        if not formal and rule_set.lifecycle_state not in {
            ResourceLifecycle.DRAFT,
            ResourceLifecycle.PUBLISHED,
        }:
            continue
        if not clause_participates(clause, formal=formal):
            continue
        grouped.setdefault(clause.coverage_key, []).append((clause, rule_set))

    resolutions: list[RuleResolution] = []
    for key in sorted(grouped):
        pairs = grouped[key]
        project = [clause for clause, rule_set in pairs if rule_set.scope_level is RuleScopeLevel.PROJECT]
        unit = [
            clause
            for clause, rule_set in pairs
            if rule_set.scope_level is RuleScopeLevel.DECISION_UNIT
        ]
        if project and len({_expression(item) for item in project}) > 1:
            resolutions.append(
                _conflict(key, project, "Project-level clauses disagree; last-write-wins is forbidden.")
            )
            continue
        if unit and len({_expression(item) for item in unit}) > 1:
            resolutions.append(
                _conflict(key, unit, "Unit-level clauses disagree; last-write-wins is forbidden.")
            )
            continue
        if project and unit:
            inherited = _winner(project)
            override = _winner(unit)
            if _expression(inherited) != _expression(override):
                resolutions.append(
                    _conflict(
                        key,
                        (inherited, override),
                        "Unit override disagrees with project inheritance; last-write-wins is forbidden.",
                    )
                )
                continue
            resolutions.append(
                RuleResolution(
                    coverage_key=key,
                    status=ResolutionStatus.RESOLVED,
                    winning_clause_id=override.rule_clause_id,
                    conflicting_clause_ids=(),
                    detail="Unit override matches inherited project clause.",
                )
            )
            continue
        if unit:
            winner = _winner(unit)
            resolutions.append(
                RuleResolution(
                    coverage_key=key,
                    status=ResolutionStatus.RESOLVED,
                    winning_clause_id=winner.rule_clause_id,
                    conflicting_clause_ids=(),
                    detail="Resolved from decision-unit rule set.",
                )
            )
            continue
        winner = _winner(project)
        resolutions.append(
            RuleResolution(
                coverage_key=key,
                status=ResolutionStatus.RESOLVED,
                winning_clause_id=winner.rule_clause_id,
                conflicting_clause_ids=(),
                detail="Inherited from project-level rule set.",
            )
        )
    return tuple(resolutions)
