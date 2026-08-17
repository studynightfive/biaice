"""Services for member-5 market/privacy/model-provider governance slices."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from biaice.api.operation_catalog import OPERATION_CATALOG
from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.modules.market.application.governance import MarketGovernanceService
from biaice.modules.market.application.repository import (
    InMemoryMarketResourceRepository,
    InMemoryProcessingRecordRepository,
)
from biaice.modules.market.domain.models import (
    MarketResourceRecord,
    MarketResourceState,
    ProcessingRecord,
    ProcessingRecordState,
)

FR05_OPERATION_IDS = frozenset(
    operation.operation_id for operation in OPERATION_CATALOG if operation.fr == "FR-05"
)
PROCESSING_RECORD_OPERATION_IDS = frozenset(
    {
        "create_processing_record",
        "list_processing_records",
        "get_processing_record",
    }
)
MEMBER5_OPERATION_IDS = FR05_OPERATION_IDS | PROCESSING_RECORD_OPERATION_IDS


def _scope_kwargs(
    *, identity: IdentityContext, project_id: UUID | None, decision_unit_id: UUID | None
) -> None:
    identity.scope.assert_allows(
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
    )


def _related_to_scope_filter(
    related_ids: dict[str, UUID] | None,
) -> dict[str, UUID]:
    if not related_ids:
        return {}
    return {name: value for name, value in related_ids.items() if value is not None}


def _resolve_action_state(action: str) -> MarketResourceState:
    action_root = action.split("_", 1)[0]
    if action_root == "publish":
        return MarketResourceState.PUBLISHED
    if action_root == "freeze":
        return MarketResourceState.FROZEN
    if action_root == "revoke":
        return MarketResourceState.REVOKED
    if action_root in {"archive", "close", "expire", "suspend"}:
        return MarketResourceState.ARCHIVED
    if action.startswith("test_connection_"):
        return MarketResourceState.ACTIVE
    if action_root in {"approve", "decide", "activate", "complete", "transition"}:
        return MarketResourceState.ACTIVE
    if action.startswith("mark_not_required_"):
        return MarketResourceState.ARCHIVED
    return MarketResourceState.DRAFT


class MarketResourceService:
    """Generic create/list/get/action service for remaining member-5 operations."""

    def __init__(
        self,
        *,
        repository: InMemoryMarketResourceRepository,
        clock: Clock,
        audit_writer: AuditWriter,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._audit_writer = audit_writer

    def create(
        self,
        *,
        identity: IdentityContext,
        resource: str,
        payload: dict[str, Any] | None,
        request_id: str,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
        related_ids: dict[str, UUID] | None = None,
    ) -> MarketResourceRecord:
        require_audit(self._audit_writer)
        _scope_kwargs(
            identity=identity,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        now = self._clock.now()
        item = MarketResourceRecord(
            resource_id=uuid4(),
            version_id=uuid4(),
            resource=resource,
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
            actor_id=identity.subject_id,
            state=MarketResourceState.DRAFT,
            payload=dict(payload or {}),
            related_ids=_related_to_scope_filter(related_ids),
            created_at=now,
            updated_at=now,
        )
        self._repository.upsert_resource_record(resource=resource, item=item)
        self._audit_writer.write(
            identity=identity,
            action="market.resource.create",
            object_type="MarketResourceRecord",
            object_id=item.resource_id,
            request_id=request_id,
            reason_code="MARKET_RESOURCE_CREATED",
            outcome=item.state.value,
            object_version_id=item.version_id,
        )
        return item

    def list(
        self,
        *,
        identity: IdentityContext,
        resource: str,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
        related_ids: dict[str, UUID] | None = None,
    ) -> tuple[MarketResourceRecord, ...]:
        _scope_kwargs(
            identity=identity,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        return self._repository.list_resource_records(
            resource=resource,
            scope=identity.scope,
            related_ids=_related_to_scope_filter(related_ids),
        )

    def get(
        self, *, identity: IdentityContext, resource: str, resource_id: UUID
    ) -> MarketResourceRecord:
        item = self._repository.get_resource_record(
            resource=resource, scope=identity.scope, resource_id=resource_id
        )
        if item is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"{resource} {resource_id} not found in scope.",
            )
        return item

    def act(
        self,
        *,
        identity: IdentityContext,
        resource: str,
        action: str,
        request_id: str,
        resource_id: UUID | None = None,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
        related_ids: dict[str, UUID] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> MarketResourceRecord:
        require_audit(self._audit_writer)
        _scope_kwargs(
            identity=identity,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
        )
        action_payload = dict(payload or {})
        if resource_id is None:
            return self.create(
                identity=identity,
                resource=resource,
                payload=action_payload,
                request_id=request_id,
                project_id=project_id,
                decision_unit_id=decision_unit_id,
                related_ids=related_ids,
            )
        item = self.get(identity=identity, resource=resource, resource_id=resource_id)
        merged = dict(item.payload)
        merged.update(action_payload)
        next_state = _resolve_action_state(action)
        item = item.model_copy(
            update={
                "state": next_state,
                "last_action": action,
                "payload": merged,
                "updated_at": self._clock.now(),
            }
        )
        self._repository.upsert_resource_record(resource=resource, item=item)
        self._audit_writer.write(
            identity=identity,
            action=f"market.resource.{action}",
            object_type="MarketResourceRecord",
            object_id=item.resource_id,
            request_id=request_id,
            reason_code="MARKET_RESOURCE_ACTION",
            outcome=item.state.value,
            object_version_id=item.version_id,
        )
        return item


class ProcessingRecordService:
    """Minimal business policy for FR-12 processing records."""

    def __init__(
        self,
        *,
        repository: InMemoryProcessingRecordRepository,
        clock: Clock,
        audit_writer: AuditWriter,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._audit_writer = audit_writer

    def create(
        self,
        *,
        identity: IdentityContext,
        project_id: UUID | None,
        decision_unit_id: UUID | None,
        external_source_id: UUID | None,
        source_uri: str | None,
        evidence_refs: tuple[str, ...],
        legal_basis_ref: str,
        expires_at: datetime | None,
        notes: str | None,
        request_id: str,
    ) -> ProcessingRecord:
        require_audit(self._audit_writer)
        if decision_unit_id is not None:
            identity.scope.assert_allows(
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                decision_unit_id=decision_unit_id,
                project_id=project_id,
            )
        elif project_id is not None:
            identity.scope.assert_allows(
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                project_id=project_id,
            )

        now = self._clock.now()
        item = ProcessingRecord(
            processing_record_id=uuid4(),
            version_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            project_id=project_id,
            decision_unit_id=decision_unit_id,
            external_source_id=external_source_id,
            source_uri=source_uri,
            evidence_refs=tuple(evidence_refs),
            legal_basis_ref=legal_basis_ref,
            expires_at=expires_at,
            notes=notes,
            state=ProcessingRecordState.DRAFT,
            state_reason="draft-created",
            created_at=now,
            updated_at=now,
            actor_id=identity.subject_id,
        )
        self._repository.upsert_processing_record(item)
        self._audit_writer.write(
            identity=identity,
            action="market.processing_record.create",
            object_type="ProcessingRecord",
            object_id=item.processing_record_id,
            request_id=request_id,
            reason_code="PROCESSING_RECORD_CREATED",
            outcome=item.state.value,
            object_version_id=item.version_id,
        )
        return item

    def list(self, *, identity: IdentityContext) -> tuple[ProcessingRecord, ...]:
        return self._repository.list_processing_records(scope=identity.scope)

    def get(self, *, identity: IdentityContext, processing_record_id: UUID) -> ProcessingRecord:
        item = self._repository.get_processing_record(
            scope=identity.scope,
            processing_record_id=processing_record_id,
        )
        if item is None:
            raise BiaiceError(
                "RESOURCE_NOT_FOUND",
                detail=f"ProcessingRecord {processing_record_id} not found.",
            )
        return item


class MarketPrivacyServices:
    """Composition root for member-5 market/privacy/model slices."""

    def __init__(
        self,
        *,
        repository: InMemoryProcessingRecordRepository,
        market_repository: InMemoryMarketResourceRepository,
        clock: Clock,
        audit_writer: AuditWriter,
    ) -> None:
        self.processing_record = ProcessingRecordService(
            repository=repository,
            clock=clock,
            audit_writer=audit_writer,
        )
        self.market_resource = MarketResourceService(
            repository=market_repository,
            clock=clock,
            audit_writer=audit_writer,
        )
        self.fr05 = MarketGovernanceService(
            clock=clock,
            audit_writer=audit_writer,
        )


def configure_market_privacy_services(
    app,
    *,
    repository: InMemoryProcessingRecordRepository | None = None,
    market_repository: InMemoryMarketResourceRepository | None = None,
) -> MarketPrivacyServices:
    """Attach member-5 services to app state."""
    repository = repository or InMemoryProcessingRecordRepository()
    market_repository = market_repository or InMemoryMarketResourceRepository()
    services = MarketPrivacyServices(
        repository=repository,
        market_repository=market_repository,
        clock=SystemClock(),
        audit_writer=app.state.audit_writer,
    )
    app.state.market_repository = repository
    app.state.market_resource_repository = market_repository
    app.state.market_services = services
    return services
