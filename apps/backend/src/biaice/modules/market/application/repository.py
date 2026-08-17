"""In-memory repository for the FR-12 processing records slice."""

from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.market.domain.models import MarketResourceRecord, ProcessingRecord


class MarketResourceRepository(Protocol):
    def upsert_resource_record(self, resource: str, item: MarketResourceRecord) -> None: ...

    def get_resource_record(
        self, *, resource: str, scope: TenantScope, resource_id: UUID
    ) -> MarketResourceRecord | None: ...

    def list_resource_records(
        self,
        *,
        resource: str,
        scope: TenantScope,
        related_ids: dict[str, UUID] | None = None,
    ) -> tuple[MarketResourceRecord, ...]: ...


class ProcessingRecordRepository(Protocol):
    def upsert_processing_record(self, item: ProcessingRecord) -> None: ...

    def get_processing_record(
        self, *, scope: TenantScope, processing_record_id: UUID
    ) -> ProcessingRecord | None: ...

    def list_processing_records(self, *, scope: TenantScope) -> tuple[ProcessingRecord, ...]: ...


def _scope_matches_resource(item: MarketResourceRecord, scope: TenantScope) -> bool:
    if item.tenant_id != scope.tenant_id or item.data_domain_id != scope.data_domain_id:
        return False
    if (
        item.project_id is not None
        and not scope.all_projects
        and item.project_id not in scope.project_ids
    ):
        return False
    if (
        item.decision_unit_id is not None
        and not scope.all_decision_units
        and item.decision_unit_id not in scope.decision_unit_ids
    ):
        return False
    return True


class InMemoryMarketResourceRepository:
    """Thread-safe in-memory store for generic member-5 resource slices."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, UUID], MarketResourceRecord] = {}
        self._lock = threading.Lock()

    def upsert_resource_record(self, resource: str, item: MarketResourceRecord) -> None:
        with self._lock:
            self._records[(resource, item.resource_id)] = item

    def get_resource_record(
        self, *, resource: str, scope: TenantScope, resource_id: UUID
    ) -> MarketResourceRecord | None:
        with self._lock:
            item = self._records.get((resource, resource_id))
        if item is None or not _scope_matches_resource(item, scope):
            return None
        return item

    def list_resource_records(
        self,
        *,
        resource: str,
        scope: TenantScope,
        related_ids: dict[str, UUID] | None = None,
    ) -> tuple[MarketResourceRecord, ...]:
        related_ids = related_ids or {}
        with self._lock:
            records = [
                item
                for (name, _), item in self._records.items()
                if name == resource and _scope_matches_resource(item, scope)
            ]
        if related_ids:
            records = [
                item
                for item in records
                if all(item.related_ids.get(key) == value for key, value in related_ids.items())
            ]
        records.sort(key=lambda item: item.created_at)
        return tuple(records)


def _scope_matches(item: ProcessingRecord, scope: TenantScope) -> bool:
    if item.tenant_id != scope.tenant_id or item.data_domain_id != scope.data_domain_id:
        return False
    if (
        item.project_id is not None
        and not scope.all_projects
        and item.project_id not in scope.project_ids
    ):
        return False
    if (
        item.decision_unit_id is not None
        and not scope.all_decision_units
        and item.decision_unit_id not in scope.decision_unit_ids
    ):
        return False
    return True


class InMemoryProcessingRecordRepository:
    """Thread-safe repository used by the contract-milestone M5 slice."""

    def __init__(self) -> None:
        self._processing_records: dict[UUID, ProcessingRecord] = {}
        self._lock = threading.Lock()

    def upsert_processing_record(self, item: ProcessingRecord) -> None:
        with self._lock:
            self._processing_records[item.processing_record_id] = item

    def get_processing_record(
        self, *, scope: TenantScope, processing_record_id: UUID
    ) -> ProcessingRecord | None:
        with self._lock:
            item = self._processing_records.get(processing_record_id)
        if item is None or not _scope_matches(item, scope):
            return None
        return item

    def list_processing_records(self, *, scope: TenantScope) -> tuple[ProcessingRecord, ...]:
        with self._lock:
            records = [
                item for item in self._processing_records.values() if _scope_matches(item, scope)
            ]
        records.sort(key=lambda item: item.created_at)
        return tuple(records)
