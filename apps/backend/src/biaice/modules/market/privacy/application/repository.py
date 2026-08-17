"""Tenant-scoped process-local repositories for the unsigned M0 profile."""

from __future__ import annotations

import threading
from typing import Protocol, Sequence
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.core.errors import BiaiceError
from biaice.modules.market.privacy.domain.models import MarketResourceRecord


class MarketResourceRepository(Protocol):
    def save(
        self, *, scope: TenantScope, record: MarketResourceRecord
    ) -> MarketResourceRecord: ...

    def get(
        self, *, scope: TenantScope, resource_type: str, resource_id: UUID
    ) -> MarketResourceRecord | None: ...

    def list(
        self, *, scope: TenantScope, resource_type: str, state: str | None = None
    ) -> Sequence[MarketResourceRecord]: ...


class InMemoryMarketResourceRepository:
    """Synthetic/test adapter; it never claims durable or production storage."""

    def __init__(self) -> None:
        self._records: dict[
            tuple[UUID, UUID, str, UUID], MarketResourceRecord
        ] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _key(
        scope: TenantScope, resource_type: str, resource_id: UUID
    ) -> tuple[UUID, UUID, str, UUID]:
        return (
            scope.tenant_id,
            scope.data_domain_id,
            resource_type,
            resource_id,
        )

    def save(
        self, *, scope: TenantScope, record: MarketResourceRecord
    ) -> MarketResourceRecord:
        scope.assert_allows(
            tenant_id=record.tenant_id,
            data_domain_id=record.data_domain_id,
        )
        with self._lock:
            self._records[
                self._key(scope, record.resource_type, record.resource_id)
            ] = record
        return record

    def get(
        self, *, scope: TenantScope, resource_type: str, resource_id: UUID
    ) -> MarketResourceRecord | None:
        with self._lock:
            return self._records.get(self._key(scope, resource_type, resource_id))

    def list(
        self, *, scope: TenantScope, resource_type: str, state: str | None = None
    ) -> Sequence[MarketResourceRecord]:
        with self._lock:
            matches = [
                record
                for (tenant_id, data_domain_id, kind, _), record in self._records.items()
                if tenant_id == scope.tenant_id
                and data_domain_id == scope.data_domain_id
                and kind == resource_type
                and (state is None or record.state == state)
            ]
        return tuple(
            sorted(
                matches,
                key=lambda record: (record.created_at, str(record.resource_id)),
                reverse=True,
            )
        )


class InMemoryCommandJournal:
    """Replay journal scoped by tenant/domain and idempotency key."""

    def __init__(self) -> None:
        self._entries: dict[
            tuple[UUID, UUID, str], tuple[str, MarketResourceRecord]
        ] = {}

    def replay(
        self, *, scope: TenantScope, key: str, fingerprint: str
    ) -> MarketResourceRecord | None:
        entry = self._entries.get((scope.tenant_id, scope.data_domain_id, key))
        if entry is None:
            return None
        stored_fingerprint, response = entry
        if stored_fingerprint != fingerprint:
            raise BiaiceError("IDEMPOTENCY_CONFLICT")
        return response

    def record(
        self,
        *,
        scope: TenantScope,
        key: str,
        fingerprint: str,
        response: MarketResourceRecord,
    ) -> None:
        self._entries[(scope.tenant_id, scope.data_domain_id, key)] = (
            fingerprint,
            response,
        )

