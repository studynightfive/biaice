"""FR-02 ports for blob storage, legal-hold queries, and downstream readers."""

from __future__ import annotations

from typing import Protocol, Sequence
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.documents.domain.models import (
    DerivedAsset,
    ReleasedDocumentView,
)
from biaice.modules.governance.domain.models import (
    LegalHoldRecord,
    LegalHoldState,
    ScopedObjectRef,
)


class LegalHoldQueryPort(Protocol):
    def list_active_holds(
        self, *, scope: TenantScope, target: ScopedObjectRef
    ) -> Sequence[LegalHoldRecord]: ...


class NoLegalHolds:
    def list_active_holds(
        self, *, scope: TenantScope, target: ScopedObjectRef
    ) -> tuple[LegalHoldRecord, ...]:
        del scope, target
        return ()


class InMemoryLegalHoldQuery:
    def __init__(self, holds: Sequence[LegalHoldRecord] = ()) -> None:
        self._holds = list(holds)

    def add(self, hold: LegalHoldRecord) -> None:
        self._holds.append(hold)

    def list_active_holds(
        self, *, scope: TenantScope, target: ScopedObjectRef
    ) -> tuple[LegalHoldRecord, ...]:
        return tuple(
            hold
            for hold in self._holds
            if hold.target.tenant_id == scope.tenant_id
            and hold.target.data_domain_id == scope.data_domain_id
            and hold.target.object_id == target.object_id
            and hold.target.object_type == target.object_type
            and hold.state is LegalHoldState.ACTIVE
        )


class DocumentReadPort(Protocol):
    """Stable refs for members 2/4/5. Never returns scan-failed bodies."""

    def get_released_document(
        self, *, scope: TenantScope, document_id: UUID
    ) -> ReleasedDocumentView | None: ...

    def get_fragment(
        self, *, scope: TenantScope, asset_id: UUID
    ) -> DerivedAsset | None: ...
