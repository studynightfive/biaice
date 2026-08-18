"""DecisionUnit lifecycle state machine. Member 2 is the only writer."""

from __future__ import annotations

from enum import StrEnum

from biaice.core.errors import BiaiceError


class DecisionUnitLifecycleState(StrEnum):
    DRAFT = "DRAFT"
    DOCUMENTS_PARSING = "DOCUMENTS_PARSING"
    REGIME_AND_SCOPE_PENDING = "REGIME_AND_SCOPE_PENDING"
    PORTFOLIO_REVIEW_REQUIRED = "PORTFOLIO_REVIEW_REQUIRED"
    MULTI_ROUND_UNSUPPORTED = "MULTI_ROUND_UNSUPPORTED"
    RULES_PENDING_CONFIRMATION = "RULES_PENDING_CONFIRMATION"
    EVIDENCE_MATCHING = "EVIDENCE_MATCHING"
    PRECHECK_PENDING = "PRECHECK_PENDING"
    PRECHECK_BLOCKED = "PRECHECK_BLOCKED"
    PRECHECK_UNKNOWN = "PRECHECK_UNKNOWN"
    PRECHECK_PASSED = "PRECHECK_PASSED"
    PRECHECK_CONDITIONAL = "PRECHECK_CONDITIONAL"
    REMEDIATION = "REMEDIATION"
    STRATEGY_READINESS_PENDING = "STRATEGY_READINESS_PENDING"
    NOT_READY = "NOT_READY"
    STRATEGY_READY = "STRATEGY_READY"
    STRATEGY_READY_WITH_CONDITIONS = "STRATEGY_READY_WITH_CONDITIONS"
    COMPUTING = "COMPUTING"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    NO_FEASIBLE_STRATEGY = "NO_FEASIBLE_STRATEGY"
    RECOMMENDATION_REVIEW = "RECOMMENDATION_REVIEW"
    ELIGIBILITY_PENDING = "ELIGIBILITY_PENDING"
    INELIGIBLE = "INELIGIBLE"
    INDETERMINATE = "INDETERMINATE"
    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_ACCEPTED_RISK = "ELIGIBLE_WITH_ACCEPTED_RISK"
    ELIGIBLE_WITH_CONDITIONS = "ELIGIBLE_WITH_CONDITIONS"
    APPROVAL_PACKAGE_FROZEN = "APPROVAL_PACKAGE_FROZEN"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    REJECTED = "REJECTED"
    PACKAGE_INVALIDATED = "PACKAGE_INVALIDATED"
    APPROVED_CONDITIONAL = "APPROVED_CONDITIONAL"
    CONDITION_CLOSURE = "CONDITION_CLOSURE"
    SUBMISSION_AUTHORIZED = "SUBMISSION_AUTHORIZED"
    DECISION_FROZEN = "DECISION_FROZEN"
    EXTERNAL_SUBMISSION_PENDING = "EXTERNAL_SUBMISSION_PENDING"
    SUBMISSION_DECLARED = "SUBMISSION_DECLARED"
    SUBMISSION_MISMATCH = "SUBMISSION_MISMATCH"
    SUBMISSION_FAILED = "SUBMISSION_FAILED"
    SUBMISSION_VERIFIED = "SUBMISSION_VERIFIED"
    OUTCOME_PENDING = "OUTCOME_PENDING"
    OUTCOME_UNVERIFIED = "OUTCOME_UNVERIFIED"
    OUTCOME_CONFLICTING = "OUTCOME_CONFLICTING"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    AWARDED = "AWARDED"
    LOST = "LOST"
    DISQUALIFIED = "DISQUALIFIED"
    NO_BID = "NO_BID"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"
    PROCUREMENT_FAILED = "PROCUREMENT_FAILED"
    REWORK = "REWORK"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


REOPENED_EVENT = "REOPENED"

TERMINAL_STATES: frozenset[DecisionUnitLifecycleState] = frozenset(
    {
        DecisionUnitLifecycleState.AWARDED,
        DecisionUnitLifecycleState.LOST,
        DecisionUnitLifecycleState.DISQUALIFIED,
        DecisionUnitLifecycleState.NO_BID,
        DecisionUnitLifecycleState.WITHDRAWN,
        DecisionUnitLifecycleState.CANCELLED,
        DecisionUnitLifecycleState.PROCUREMENT_FAILED,
        DecisionUnitLifecycleState.CLOSED,
        DecisionUnitLifecycleState.ARCHIVED,
    }
)

_SPINE: tuple[DecisionUnitLifecycleState, ...] = (
    DecisionUnitLifecycleState.DRAFT,
    DecisionUnitLifecycleState.DOCUMENTS_PARSING,
    DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING,
    DecisionUnitLifecycleState.RULES_PENDING_CONFIRMATION,
    DecisionUnitLifecycleState.EVIDENCE_MATCHING,
    DecisionUnitLifecycleState.PRECHECK_PENDING,
    DecisionUnitLifecycleState.PRECHECK_PASSED,
    DecisionUnitLifecycleState.STRATEGY_READINESS_PENDING,
    DecisionUnitLifecycleState.STRATEGY_READY,
    DecisionUnitLifecycleState.COMPUTING,
    DecisionUnitLifecycleState.RECOMMENDATION_REVIEW,
    DecisionUnitLifecycleState.ELIGIBILITY_PENDING,
    DecisionUnitLifecycleState.ELIGIBLE,
    DecisionUnitLifecycleState.APPROVAL_PACKAGE_FROZEN,
    DecisionUnitLifecycleState.APPROVAL_PENDING,
    DecisionUnitLifecycleState.SUBMISSION_AUTHORIZED,
    DecisionUnitLifecycleState.DECISION_FROZEN,
    DecisionUnitLifecycleState.EXTERNAL_SUBMISSION_PENDING,
    DecisionUnitLifecycleState.SUBMISSION_DECLARED,
    DecisionUnitLifecycleState.SUBMISSION_VERIFIED,
    DecisionUnitLifecycleState.OUTCOME_PENDING,
    DecisionUnitLifecycleState.OUTCOME_VERIFIED,
)

_BRANCHES: dict[DecisionUnitLifecycleState, frozenset[DecisionUnitLifecycleState]] = {
    DecisionUnitLifecycleState.DRAFT: frozenset(
        {
            DecisionUnitLifecycleState.DOCUMENTS_PARSING,
            DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING,
        }
    ),
    DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.PORTFOLIO_REVIEW_REQUIRED,
            DecisionUnitLifecycleState.MULTI_ROUND_UNSUPPORTED,
            DecisionUnitLifecycleState.RULES_PENDING_CONFIRMATION,
        }
    ),
    DecisionUnitLifecycleState.PORTFOLIO_REVIEW_REQUIRED: frozenset(
        {DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING}
    ),
    DecisionUnitLifecycleState.MULTI_ROUND_UNSUPPORTED: frozenset(
        {DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING}
    ),
    DecisionUnitLifecycleState.PRECHECK_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.PRECHECK_BLOCKED,
            DecisionUnitLifecycleState.PRECHECK_UNKNOWN,
            DecisionUnitLifecycleState.PRECHECK_PASSED,
            DecisionUnitLifecycleState.PRECHECK_CONDITIONAL,
        }
    ),
    DecisionUnitLifecycleState.PRECHECK_BLOCKED: frozenset(
        {DecisionUnitLifecycleState.REMEDIATION, DecisionUnitLifecycleState.PRECHECK_PENDING}
    ),
    DecisionUnitLifecycleState.PRECHECK_UNKNOWN: frozenset(
        {DecisionUnitLifecycleState.REMEDIATION, DecisionUnitLifecycleState.PRECHECK_PENDING}
    ),
    DecisionUnitLifecycleState.PRECHECK_CONDITIONAL: frozenset(
        {DecisionUnitLifecycleState.STRATEGY_READINESS_PENDING}
    ),
    DecisionUnitLifecycleState.REMEDIATION: frozenset(
        {
            DecisionUnitLifecycleState.PRECHECK_PENDING,
            DecisionUnitLifecycleState.RULES_PENDING_CONFIRMATION,
        }
    ),
    DecisionUnitLifecycleState.STRATEGY_READINESS_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.NOT_READY,
            DecisionUnitLifecycleState.STRATEGY_READY,
            DecisionUnitLifecycleState.STRATEGY_READY_WITH_CONDITIONS,
        }
    ),
    DecisionUnitLifecycleState.NOT_READY: frozenset(
        {DecisionUnitLifecycleState.STRATEGY_READINESS_PENDING}
    ),
    DecisionUnitLifecycleState.STRATEGY_READY_WITH_CONDITIONS: frozenset(
        {DecisionUnitLifecycleState.COMPUTING}
    ),
    DecisionUnitLifecycleState.COMPUTING: frozenset(
        {
            DecisionUnitLifecycleState.SIMULATION_FAILED,
            DecisionUnitLifecycleState.NO_FEASIBLE_STRATEGY,
            DecisionUnitLifecycleState.RECOMMENDATION_REVIEW,
        }
    ),
    DecisionUnitLifecycleState.SIMULATION_FAILED: frozenset(
        {DecisionUnitLifecycleState.COMPUTING, DecisionUnitLifecycleState.REWORK}
    ),
    DecisionUnitLifecycleState.NO_FEASIBLE_STRATEGY: frozenset(
        {DecisionUnitLifecycleState.REWORK, DecisionUnitLifecycleState.COMPUTING}
    ),
    DecisionUnitLifecycleState.ELIGIBILITY_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.INELIGIBLE,
            DecisionUnitLifecycleState.INDETERMINATE,
            DecisionUnitLifecycleState.ELIGIBLE,
            DecisionUnitLifecycleState.ELIGIBLE_WITH_ACCEPTED_RISK,
            DecisionUnitLifecycleState.ELIGIBLE_WITH_CONDITIONS,
        }
    ),
    DecisionUnitLifecycleState.INELIGIBLE: frozenset({DecisionUnitLifecycleState.REWORK}),
    DecisionUnitLifecycleState.INDETERMINATE: frozenset(
        {DecisionUnitLifecycleState.ELIGIBILITY_PENDING, DecisionUnitLifecycleState.REWORK}
    ),
    DecisionUnitLifecycleState.ELIGIBLE_WITH_ACCEPTED_RISK: frozenset(
        {DecisionUnitLifecycleState.APPROVAL_PACKAGE_FROZEN}
    ),
    DecisionUnitLifecycleState.ELIGIBLE_WITH_CONDITIONS: frozenset(
        {DecisionUnitLifecycleState.APPROVAL_PACKAGE_FROZEN}
    ),
    DecisionUnitLifecycleState.APPROVAL_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.REJECTED,
            DecisionUnitLifecycleState.PACKAGE_INVALIDATED,
            DecisionUnitLifecycleState.APPROVED_CONDITIONAL,
            DecisionUnitLifecycleState.SUBMISSION_AUTHORIZED,
        }
    ),
    DecisionUnitLifecycleState.REJECTED: frozenset({DecisionUnitLifecycleState.REWORK}),
    DecisionUnitLifecycleState.PACKAGE_INVALIDATED: frozenset(
        {DecisionUnitLifecycleState.REWORK, DecisionUnitLifecycleState.APPROVAL_PACKAGE_FROZEN}
    ),
    DecisionUnitLifecycleState.APPROVED_CONDITIONAL: frozenset(
        {
            DecisionUnitLifecycleState.CONDITION_CLOSURE,
            DecisionUnitLifecycleState.SUBMISSION_AUTHORIZED,
        }
    ),
    DecisionUnitLifecycleState.CONDITION_CLOSURE: frozenset(
        {DecisionUnitLifecycleState.SUBMISSION_AUTHORIZED, DecisionUnitLifecycleState.REWORK}
    ),
    DecisionUnitLifecycleState.EXTERNAL_SUBMISSION_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.SUBMISSION_DECLARED,
            DecisionUnitLifecycleState.SUBMISSION_FAILED,
        }
    ),
    DecisionUnitLifecycleState.SUBMISSION_DECLARED: frozenset(
        {
            DecisionUnitLifecycleState.SUBMISSION_VERIFIED,
            DecisionUnitLifecycleState.SUBMISSION_MISMATCH,
            DecisionUnitLifecycleState.SUBMISSION_FAILED,
        }
    ),
    DecisionUnitLifecycleState.SUBMISSION_MISMATCH: frozenset(
        {DecisionUnitLifecycleState.EXTERNAL_SUBMISSION_PENDING, DecisionUnitLifecycleState.REWORK}
    ),
    DecisionUnitLifecycleState.SUBMISSION_FAILED: frozenset(
        {DecisionUnitLifecycleState.EXTERNAL_SUBMISSION_PENDING, DecisionUnitLifecycleState.REWORK}
    ),
    DecisionUnitLifecycleState.OUTCOME_PENDING: frozenset(
        {
            DecisionUnitLifecycleState.OUTCOME_UNVERIFIED,
            DecisionUnitLifecycleState.OUTCOME_CONFLICTING,
            DecisionUnitLifecycleState.OUTCOME_VERIFIED,
        }
    ),
    DecisionUnitLifecycleState.OUTCOME_UNVERIFIED: frozenset(
        {DecisionUnitLifecycleState.OUTCOME_PENDING, DecisionUnitLifecycleState.OUTCOME_VERIFIED}
    ),
    DecisionUnitLifecycleState.OUTCOME_CONFLICTING: frozenset(
        {DecisionUnitLifecycleState.OUTCOME_PENDING}
    ),
    DecisionUnitLifecycleState.OUTCOME_VERIFIED: frozenset(
        {
            DecisionUnitLifecycleState.AWARDED,
            DecisionUnitLifecycleState.LOST,
            DecisionUnitLifecycleState.DISQUALIFIED,
        }
    ),
    DecisionUnitLifecycleState.REWORK: frozenset(
        {
            DecisionUnitLifecycleState.RULES_PENDING_CONFIRMATION,
            DecisionUnitLifecycleState.EVIDENCE_MATCHING,
            DecisionUnitLifecycleState.PRECHECK_PENDING,
            DecisionUnitLifecycleState.STRATEGY_READINESS_PENDING,
        }
    ),
}

_EARLY_EXIT = frozenset(
    {
        DecisionUnitLifecycleState.CANCELLED,
        DecisionUnitLifecycleState.NO_BID,
        DecisionUnitLifecycleState.WITHDRAWN,
        DecisionUnitLifecycleState.PROCUREMENT_FAILED,
    }
)

_REOPEN_FROM = frozenset(
    {
        DecisionUnitLifecycleState.CANCELLED,
        DecisionUnitLifecycleState.WITHDRAWN,
        DecisionUnitLifecycleState.NO_BID,
        DecisionUnitLifecycleState.PROCUREMENT_FAILED,
        DecisionUnitLifecycleState.CLOSED,
        DecisionUnitLifecycleState.MULTI_ROUND_UNSUPPORTED,
        DecisionUnitLifecycleState.PORTFOLIO_REVIEW_REQUIRED,
    }
)

_DEFAULT_REOPEN_STATE = DecisionUnitLifecycleState.REGIME_AND_SCOPE_PENDING


def _spine_successor(state: DecisionUnitLifecycleState) -> DecisionUnitLifecycleState | None:
    try:
        index = _SPINE.index(state)
    except ValueError:
        return None
    if index + 1 >= len(_SPINE):
        return None
    return _SPINE[index + 1]


def allowed_targets(current: DecisionUnitLifecycleState) -> frozenset[DecisionUnitLifecycleState]:
    targets: set[DecisionUnitLifecycleState] = set(_BRANCHES.get(current, frozenset()))
    successor = _spine_successor(current)
    if successor is not None:
        targets.add(successor)
    if current not in TERMINAL_STATES:
        targets.update(_EARLY_EXIT)
        targets.add(DecisionUnitLifecycleState.REWORK)
    if current in {
        DecisionUnitLifecycleState.AWARDED,
        DecisionUnitLifecycleState.LOST,
        DecisionUnitLifecycleState.DISQUALIFIED,
        DecisionUnitLifecycleState.NO_BID,
        DecisionUnitLifecycleState.WITHDRAWN,
        DecisionUnitLifecycleState.CANCELLED,
        DecisionUnitLifecycleState.PROCUREMENT_FAILED,
        DecisionUnitLifecycleState.OUTCOME_VERIFIED,
    }:
        targets.add(DecisionUnitLifecycleState.CLOSED)
    if current is DecisionUnitLifecycleState.CLOSED:
        targets.add(DecisionUnitLifecycleState.ARCHIVED)
    return frozenset(targets)


def resolve_transition(
    current: DecisionUnitLifecycleState,
    command: str,
    *,
    resume_state: DecisionUnitLifecycleState | None = None,
) -> tuple[DecisionUnitLifecycleState, bool]:
    """Return (next_state, is_reopened_event).

    REOPENED is an append-only event, never a persisted lifecycle state.
    """
    token = command.strip().upper()
    if token == REOPENED_EVENT:
        if current not in _REOPEN_FROM:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail=f"{current.value} cannot be reopened.",
            )
        nxt = resume_state or _DEFAULT_REOPEN_STATE
        if nxt in TERMINAL_STATES:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="REOPENED cannot resume into a terminal state.",
            )
        return nxt, True
    try:
        target = DecisionUnitLifecycleState(token)
    except ValueError as exc:
        raise BiaiceError(
            "REQUEST_VALIDATION_FAILED",
            detail=f"Unknown transition command {command}.",
        ) from exc
    if target not in allowed_targets(current):
        raise BiaiceError(
            "REQUEST_VALIDATION_FAILED",
            detail=f"{current.value} cannot transition to {target.value}.",
        )
    return target, False
