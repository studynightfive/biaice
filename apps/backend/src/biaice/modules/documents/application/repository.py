"""In-memory document repository for the M0 member-3 intake slice."""

from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.documents.domain.models import (
    DerivedAsset,
    DocumentLink,
    ParseJob,
    SourceDocument,
    UploadSession,
)
from biaice.modules.documents.infrastructure.storage import InMemoryObjectStore
from biaice.modules.governance.domain.models import ReplicaLocation


class DocumentsRepository(Protocol):
    def upsert_session(self, item: UploadSession) -> None: ...

    def get_session(self, *, scope: TenantScope, session_id: UUID) -> UploadSession | None: ...

    def put_chunk(self, *, session_id: UUID, part_number: int, data: bytes) -> None: ...

    def get_chunk(self, *, session_id: UUID, part_number: int) -> bytes | None: ...

    def compose_chunks(self, *, session_id: UUID, total_parts: int) -> bytes: ...

    def drop_chunks(self, *, session_id: UUID) -> None: ...

    def upsert_document(self, item: SourceDocument) -> None: ...

    def get_document(self, *, scope: TenantScope, document_id: UUID) -> SourceDocument | None: ...

    def list_documents(
        self,
        *,
        scope: TenantScope,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
    ) -> tuple[SourceDocument, ...]: ...

    def find_by_content_hash(
        self, *, scope: TenantScope, content_hash: str
    ) -> SourceDocument | None: ...

    def put_blob(self, key: str, data: bytes) -> str: ...

    def get_blob(self, key: str) -> bytes | None: ...

    def delete_blob(self, key: str) -> bool: ...

    def blob_exists(self, key: str) -> bool: ...

    def key_for_locator(self, locator_hash: str) -> str | None: ...

    def upsert_parse_job(self, item: ParseJob) -> None: ...

    def get_parse_job(self, *, scope: TenantScope, job_id: UUID) -> ParseJob | None: ...

    def upsert_derived_asset(self, item: DerivedAsset) -> None: ...

    def get_derived_asset(self, *, scope: TenantScope, asset_id: UUID) -> DerivedAsset | None: ...

    def list_derived_assets(
        self, *, scope: TenantScope, document_id: UUID
    ) -> tuple[DerivedAsset, ...]: ...

    def upsert_link(self, item: DocumentLink) -> None: ...

    def get_link(self, *, scope: TenantScope, link_id: UUID) -> DocumentLink | None: ...

    def list_active_links(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[DocumentLink, ...]: ...

    def upsert_replica(self, item: ReplicaLocation) -> None: ...

    def list_replicas(self, *, scope: TenantScope) -> tuple[ReplicaLocation, ...]: ...


def _session_in_scope(item: UploadSession, scope: TenantScope) -> bool:
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


def _document_in_scope(item: SourceDocument, scope: TenantScope) -> bool:
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


def _tenant_scoped(tenant_id: UUID, data_domain_id: UUID, scope: TenantScope) -> bool:
    return tenant_id == scope.tenant_id and data_domain_id == scope.data_domain_id


class InMemoryDocumentsRepository:
    """Thread-safe in-memory store; SQLAlchemy adapter lands in a later PR."""

    def __init__(self, store: InMemoryObjectStore | None = None) -> None:
        self._sessions: dict[UUID, UploadSession] = {}
        self._chunks: dict[tuple[UUID, int], bytes] = {}
        self._documents: dict[UUID, SourceDocument] = {}
        self._parse_jobs: dict[UUID, ParseJob] = {}
        self._assets: dict[UUID, DerivedAsset] = {}
        self._links: dict[UUID, DocumentLink] = {}
        self._replicas: dict[UUID, ReplicaLocation] = {}
        self._store = store or InMemoryObjectStore()
        self._lock = threading.Lock()

    def upsert_session(self, item: UploadSession) -> None:
        with self._lock:
            self._sessions[item.session_id] = item

    def get_session(self, *, scope: TenantScope, session_id: UUID) -> UploadSession | None:
        with self._lock:
            item = self._sessions.get(session_id)
        if item is None or not _session_in_scope(item, scope):
            return None
        return item

    def put_chunk(self, *, session_id: UUID, part_number: int, data: bytes) -> None:
        with self._lock:
            self._chunks[(session_id, part_number)] = data

    def get_chunk(self, *, session_id: UUID, part_number: int) -> bytes | None:
        with self._lock:
            return self._chunks.get((session_id, part_number))

    def compose_chunks(self, *, session_id: UUID, total_parts: int) -> bytes:
        with self._lock:
            parts = [
                self._chunks.get((session_id, part_number))
                for part_number in range(1, total_parts + 1)
            ]
        if any(part is None for part in parts):
            raise KeyError(session_id)
        return b"".join(parts)  # type: ignore[arg-type]

    def drop_chunks(self, *, session_id: UUID) -> None:
        with self._lock:
            stale = [key for key in self._chunks if key[0] == session_id]
            for key in stale:
                del self._chunks[key]

    def upsert_document(self, item: SourceDocument) -> None:
        with self._lock:
            self._documents[item.document_id] = item

    def get_document(self, *, scope: TenantScope, document_id: UUID) -> SourceDocument | None:
        with self._lock:
            item = self._documents.get(document_id)
        if item is None or not _document_in_scope(item, scope):
            return None
        return item

    def list_documents(
        self,
        *,
        scope: TenantScope,
        project_id: UUID | None = None,
        decision_unit_id: UUID | None = None,
    ) -> tuple[SourceDocument, ...]:
        with self._lock:
            items = [
                item
                for item in self._documents.values()
                if _document_in_scope(item, scope)
                and (project_id is None or item.project_id == project_id)
                and (decision_unit_id is None or item.decision_unit_id == decision_unit_id)
            ]
        items.sort(key=lambda item: (item.uploaded_at, str(item.document_id)))
        return tuple(items)

    def find_by_content_hash(
        self, *, scope: TenantScope, content_hash: str
    ) -> SourceDocument | None:
        with self._lock:
            matches = [
                item
                for item in self._documents.values()
                if _document_in_scope(item, scope) and item.content_hash == content_hash
            ]
        matches.sort(key=lambda item: item.uploaded_at)
        return matches[0] if matches else None

    def put_blob(self, key: str, data: bytes) -> str:
        return self._store.put(key, data)

    def get_blob(self, key: str) -> bytes | None:
        return self._store.get(key)

    def delete_blob(self, key: str) -> bool:
        return self._store.delete(key)

    def blob_exists(self, key: str) -> bool:
        return self._store.exists(key)

    def key_for_locator(self, locator_hash: str) -> str | None:
        return self._store.key_for_locator(locator_hash)

    def upsert_parse_job(self, item: ParseJob) -> None:
        with self._lock:
            self._parse_jobs[item.job_id] = item

    def get_parse_job(self, *, scope: TenantScope, job_id: UUID) -> ParseJob | None:
        with self._lock:
            item = self._parse_jobs.get(job_id)
        if item is None or not _tenant_scoped(item.tenant_id, item.data_domain_id, scope):
            return None
        return item

    def get_parse_job_unscoped(self, job_id: UUID) -> ParseJob | None:
        with self._lock:
            return self._parse_jobs.get(job_id)

    def upsert_derived_asset(self, item: DerivedAsset) -> None:
        with self._lock:
            self._assets[item.asset_id] = item

    def get_derived_asset(self, *, scope: TenantScope, asset_id: UUID) -> DerivedAsset | None:
        with self._lock:
            item = self._assets.get(asset_id)
        if item is None or not _tenant_scoped(item.tenant_id, item.data_domain_id, scope):
            return None
        return item

    def list_derived_assets(
        self, *, scope: TenantScope, document_id: UUID
    ) -> tuple[DerivedAsset, ...]:
        with self._lock:
            items = [
                item
                for item in self._assets.values()
                if _tenant_scoped(item.tenant_id, item.data_domain_id, scope)
                and item.source_document_id == document_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.asset_id)))
        return tuple(items)

    def upsert_link(self, item: DocumentLink) -> None:
        with self._lock:
            self._links[item.link_id] = item

    def get_link(self, *, scope: TenantScope, link_id: UUID) -> DocumentLink | None:
        with self._lock:
            item = self._links.get(link_id)
        if item is None or not _tenant_scoped(item.tenant_id, item.data_domain_id, scope):
            return None
        return item

    def list_active_links(
        self, *, scope: TenantScope, decision_unit_id: UUID
    ) -> tuple[DocumentLink, ...]:
        with self._lock:
            items = [
                item
                for item in self._links.values()
                if _tenant_scoped(item.tenant_id, item.data_domain_id, scope)
                and item.decision_unit_id == decision_unit_id
                and item.detached_at is None
            ]
        items.sort(key=lambda item: (-item.priority, item.created_at))
        return tuple(items)

    def upsert_replica(self, item: ReplicaLocation) -> None:
        with self._lock:
            self._replicas[item.replica_id] = item

    def list_replicas(self, *, scope: TenantScope) -> tuple[ReplicaLocation, ...]:
        with self._lock:
            items = [
                item
                for item in self._replicas.values()
                if item.target.tenant_id == scope.tenant_id
                and item.target.data_domain_id == scope.data_domain_id
            ]
        items.sort(key=lambda item: str(item.replica_id))
        return tuple(items)
