"""Public ports for FR-03. Downstream modules must not import repositories."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import IdentityContext, TenantScope
from biaice.modules.evidence.domain.models import (
    ConditionRequirement,
    MatchState,
    PrecheckDecision,
    ValidityState,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReleasedDocumentRef(FrozenModel):
    """Duck-typed projection of member-3 ReleasedDocumentView. No document body."""

    document_id: UUID
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: str
    parse_status: str | None = None
    fragment_refs: tuple[str, ...] = ()


class DocumentReadPort(Protocol):
    """Consumes member 3's `app.state.document_read_port` without importing documents."""

    def get_released_document(
        self, *, scope: TenantScope, document_id: UUID
    ) -> object | None: ...


class UnavailableDocumentReadPort:
    """Fail-closed adapter used until member 3 wires `document_read_port`."""

    def get_released_document(
        self, *, scope: TenantScope, document_id: UUID
    ) -> None:
        del scope, document_id
        return None


class RuleSetRef(FrozenModel):
    rule_set_id: UUID
    supported: bool
    current: bool


class RuleAvailabilityPort(Protocol):
    """Opaque member-2 port. Missing implementation cannot make Precheck PASS."""

    def current_supported_rule_set(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> RuleSetRef | None: ...


class UnavailableRuleAvailabilityPort:
    def current_supported_rule_set(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> None:
        del scope, decision_unit_id
        return None


class EvidenceReadinessView(FrozenModel):
    precheck_decision: PrecheckDecision | None
    precheck_validity: ValidityState | None
    response_profile_current: bool
    subject_qualification: MatchState | None
    unmapped_mandatory_count: int
    open_blocking_condition_count: int


class EvidenceReadinessPort(Protocol):
    def current_view(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> EvidenceReadinessView: ...


class ConditionCommandPort(Protocol):
    """Unique writer surface for member 7. Approvals must not write condition tables."""

    def satisfy(
        self,
        *,
        identity: IdentityContext,
        condition_id: UUID,
        reason: str,
        request_id: str,
    ) -> ConditionRequirement: ...

    def waive(
        self,
        *,
        identity: IdentityContext,
        condition_id: UUID,
        reason: str,
        request_id: str,
    ) -> ConditionRequirement: ...

    def fail(
        self,
        *,
        identity: IdentityContext,
        condition_id: UUID,
        reason: str,
        request_id: str,
    ) -> ConditionRequirement: ...

    def expire(
        self,
        *,
        identity: IdentityContext,
        condition_id: UUID,
        reason: str,
        request_id: str,
    ) -> ConditionRequirement: ...
