"""Independent append-only audit writer with hash-chain semantics."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from datetime import datetime
from typing import Protocol, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from biaice.core.auth import IdentityContext, TenantScope
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audit_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    actor_id: UUID
    actor_roles: tuple[str, ...]
    action: str
    object_type: str
    object_id: UUID
    object_version_id: UUID | None = None
    request_id: str
    reason_code: str
    outcome: str
    trusted_at: datetime
    previous_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    event_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class AuditSink(Protocol):
    @property
    def available(self) -> bool: ...

    def latest_hash(self, scope: TenantScope) -> str | None: ...

    def append(self, event: AuditEvent) -> None: ...

    def list_events(self, scope: TenantScope) -> Sequence[AuditEvent]: ...


class AuditWriter(Protocol):
    @property
    def available(self) -> bool: ...

    def write(
        self,
        *,
        identity: IdentityContext,
        action: str,
        object_type: str,
        object_id: UUID,
        request_id: str,
        reason_code: str,
        outcome: str,
        object_version_id: UUID | None = None,
    ) -> AuditEvent: ...


class AuditAnchorPort(Protocol):
    """Independent trust-domain anchor; implementations must be append-only."""

    def record(self, *, scope: TenantScope, event_hash: str, trusted_at: datetime) -> str: ...

    def verify(self, *, scope: TenantScope, event_hash: str, anchor_reference: str) -> bool: ...


class UnavailableAuditWriter:
    @property
    def available(self) -> bool:
        return False

    def write(self, **kwargs: object) -> AuditEvent:
        del kwargs
        raise BiaiceError("AUDIT_UNAVAILABLE")


class InMemoryAppendOnlyAuditSink:
    """Synthetic/test sink only; secure profiles must use an independent adapter."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._available = True
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self._available

    def set_available(self, value: bool) -> None:
        self._available = value

    def latest_hash(self, scope: TenantScope) -> str | None:
        matches = [
            event
            for event in self._events
            if event.tenant_id == scope.tenant_id and event.data_domain_id == scope.data_domain_id
        ]
        return matches[-1].event_hash if matches else None

    def append(self, event: AuditEvent) -> None:
        if not self.available:
            raise BiaiceError("AUDIT_UNAVAILABLE")
        with self._lock:
            self._events.append(event)

    def list_events(self, scope: TenantScope) -> Sequence[AuditEvent]:
        return tuple(
            event
            for event in self._events
            if event.tenant_id == scope.tenant_id and event.data_domain_id == scope.data_domain_id
        )


class HashChainAuditWriter:
    GENESIS_HASH = "0" * 64

    def __init__(self, sink: AuditSink, clock: Clock | None = None) -> None:
        self.sink = sink
        self.clock = clock or SystemClock()
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.sink.available

    def write(
        self,
        *,
        identity: IdentityContext,
        action: str,
        object_type: str,
        object_id: UUID,
        request_id: str,
        reason_code: str,
        outcome: str,
        object_version_id: UUID | None = None,
    ) -> AuditEvent:
        if not self.available:
            raise BiaiceError("AUDIT_UNAVAILABLE")
        with self._lock:
            previous_hash = self.sink.latest_hash(identity.scope) or self.GENESIS_HASH
            unsigned = {
                "audit_id": str(uuid4()),
                "tenant_id": str(identity.scope.tenant_id),
                "data_domain_id": str(identity.scope.data_domain_id),
                "actor_id": str(identity.subject_id),
                "actor_roles": sorted(role.value for role in identity.roles),
                "action": action,
                "object_type": object_type,
                "object_id": str(object_id),
                "object_version_id": str(object_version_id) if object_version_id else None,
                "request_id": request_id,
                "reason_code": reason_code,
                "outcome": outcome,
                "trusted_at": self.clock.now().isoformat(),
                "previous_hash": previous_hash,
            }
            event_hash = hashlib.sha256(
                json.dumps(
                    unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
            ).hexdigest()
            event = AuditEvent(**unsigned, event_hash=event_hash)
            self.sink.append(event)
            return event


def require_audit(writer: AuditWriter) -> None:
    if not writer.available:
        raise BiaiceError("AUDIT_UNAVAILABLE")


def verify_hash_chain(events: Sequence[AuditEvent]) -> str:
    """Verify one tenant/domain chain and return its final hash."""

    previous_hash = HashChainAuditWriter.GENESIS_HASH
    expected_scope: tuple[UUID, UUID] | None = None
    for event in events:
        scope = (event.tenant_id, event.data_domain_id)
        if expected_scope is None:
            expected_scope = scope
        if scope != expected_scope or event.previous_hash != previous_hash:
            raise BiaiceError("AUDIT_INTEGRITY_FAILED")
        unsigned = {
            "audit_id": str(event.audit_id),
            "tenant_id": str(event.tenant_id),
            "data_domain_id": str(event.data_domain_id),
            "actor_id": str(event.actor_id),
            "actor_roles": list(event.actor_roles),
            "action": event.action,
            "object_type": event.object_type,
            "object_id": str(event.object_id),
            "object_version_id": str(event.object_version_id) if event.object_version_id else None,
            "request_id": event.request_id,
            "reason_code": event.reason_code,
            "outcome": event.outcome,
            "trusted_at": event.trusted_at.isoformat(),
            "previous_hash": event.previous_hash,
        }
        calculated = hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()
        if not hmac.compare_digest(calculated, event.event_hash):
            raise BiaiceError("AUDIT_INTEGRITY_FAILED")
        previous_hash = event.event_hash
    return previous_hash
