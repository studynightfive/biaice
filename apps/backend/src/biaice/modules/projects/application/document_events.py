"""Consume member-3 public document events without importing documents/**."""

from __future__ import annotations

from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.core.outbox import EventEnvelope
from biaice.modules.projects.application.repository import Fr01Repository
from biaice.modules.projects.domain.models import DocumentIntakeRef, ResourceValidity

CONSUMED_DOCUMENT_EVENTS = frozenset(
    {
        "documents.source_document_released.v1",
        "documents.parse_completed.v1",
        "documents.document_quarantined.v1",
    }
)


def _as_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


class DocumentEventConsumer:
    """Idempotent inbox for FR-02 public events. Member 2 exclusive."""

    def __init__(self, repository: Fr01Repository) -> None:
        self.repository = repository

    def consume(self, envelope: EventEnvelope) -> DocumentIntakeRef | None:
        if envelope.event_type not in CONSUMED_DOCUMENT_EVENTS:
            return None
        scope = TenantScope(
            tenant_id=envelope.tenant_id,
            data_domain_id=envelope.data_domain_id,
            all_projects=True,
            all_decision_units=True,
        )
        existing = self.repository.get_document_ref(scope=scope, event_id=envelope.event_id)
        if existing is not None:
            return existing
        quarantined = envelope.event_type == "documents.document_quarantined.v1"
        item = DocumentIntakeRef(
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            tenant_id=envelope.tenant_id,
            data_domain_id=envelope.data_domain_id,
            project_id=envelope.project_id,
            decision_unit_id=envelope.decision_unit_id,
            document_id=_as_uuid(envelope.payload.get("document_id"))
            or (envelope.aggregate_id if envelope.aggregate_type == "SourceDocument" else None),
            parse_job_id=_as_uuid(envelope.payload.get("parse_job_id")),
            usable_for_formal_rules=not quarantined,
            validity_state=(
                ResourceValidity.INVALIDATED if quarantined else ResourceValidity.CURRENT
            ),
            occurred_at=envelope.occurred_at,
            request_id=envelope.request_id,
        )
        self.repository.upsert_document_ref(item)
        return item
