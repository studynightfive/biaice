"""FR-12 synthetic-safe CRUD, lifecycle, audit, and pagination policy."""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec
from biaice.modules.market.privacy.application.repository import (
    InMemoryCommandJournal,
    InMemoryMarketResourceRepository,
    MarketResourceRepository,
)
from biaice.modules.market.privacy.domain.models import (
    MarketActionCommand,
    MarketResourcePage,
    MarketResourceRecord,
)

INITIAL_STATES: dict[str, str] = {
    "processing_record": "DRAFT",
    "legal_basis_evidence": "CURRENT",
    "notice_consent_record": "CURRENT",
    "pia_record": "DRAFT",
    "cross_border_assessment": "DRAFT",
    "provider_policy": "DRAFT",
    "dsr_policy": "DRAFT",
    "load_profile": "DRAFT",
    "data_subject_request": "RECEIVED",
    "incident_policy": "DRAFT",
    "incident": "OPEN",
    "consent_withdrawal": "RECORDED",
}

FIXED_TRANSITIONS: dict[tuple[str, str], dict[str, str]] = {
    ("pia_record", "approve"): {"DRAFT": "APPROVED"},
    ("pia_record", "revoke"): {"APPROVED": "REVOKED"},
    ("cross_border_assessment", "approve"): {"DRAFT": "APPROVED"},
    ("cross_border_assessment", "mark-not-required"): {"DRAFT": "NOT_REQUIRED"},
    ("cross_border_assessment", "revoke"): {
        "APPROVED": "REVOKED",
        "NOT_REQUIRED": "REVOKED",
    },
    ("cross_border_assessment", "expire"): {
        "APPROVED": "EXPIRED",
        "NOT_REQUIRED": "EXPIRED",
    },
    ("provider_policy", "approve"): {"DRAFT": "APPROVED"},
    ("provider_policy", "mark-not-required"): {"DRAFT": "NOT_REQUIRED"},
    ("provider_policy", "revoke"): {
        "APPROVED": "REVOKED",
        "NOT_REQUIRED": "REVOKED",
    },
    ("provider_policy", "expire"): {
        "APPROVED": "EXPIRED",
        "NOT_REQUIRED": "EXPIRED",
    },
    ("dsr_policy", "publish"): {"DRAFT": "PUBLISHED"},
    ("dsr_policy", "archive"): {"PUBLISHED": "ARCHIVED"},
    ("load_profile", "freeze"): {"DRAFT": "FROZEN"},
    ("data_subject_request", "verify-identity"): {"RECEIVED": "IDENTITY_VERIFIED"},
    ("data_subject_request", "complete"): {
        "IN_PROGRESS": "COMPLETED",
        "READY_TO_COMPLETE": "COMPLETED",
    },
    ("incident_policy", "approve"): {"DRAFT": "APPROVED"},
    ("incident", "close"): {"RESOLVED": "CLOSED"},
}

DYNAMIC_TRANSITIONS: dict[str, dict[str, frozenset[str]]] = {
    "data_subject_request": {
        "IDENTITY_VERIFIED": frozenset({"IN_PROGRESS", "REJECTED"}),
        "IN_PROGRESS": frozenset({"WAITING_FOR_INFORMATION", "READY_TO_COMPLETE", "REJECTED"}),
        "WAITING_FOR_INFORMATION": frozenset({"IN_PROGRESS", "REJECTED"}),
        "READY_TO_COMPLETE": frozenset({"IN_PROGRESS"}),
    },
    "incident": {
        "OPEN": frozenset({"TRIAGED", "CONTAINED"}),
        "TRIAGED": frozenset({"CONTAINED", "REMEDIATING"}),
        "CONTAINED": frozenset({"REMEDIATING"}),
        "REMEDIATING": frozenset({"RESOLVED"}),
    },
}

INDEPENDENT_CHECKER_ACTIONS = frozenset({"approve", "mark-not-required", "publish", "freeze"})


def _fingerprint(operation_id: str, body: dict[str, Any]) -> str:
    encoded = json.dumps(
        {"operation_id": operation_id, "body": body},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _cursor_sort_key(*, resource_type: str, state: str | None, created_at: datetime) -> str:
    return json.dumps(
        {
            "resource_type": resource_type,
            "state": state,
            "created_at": created_at.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


class MarketResourceService:
    """Process-local FR-12 service for synthetic/contract profiles only."""

    def __init__(
        self,
        *,
        repository: MarketResourceRepository,
        journal: InMemoryCommandJournal,
        cursor_codec: CursorCodec,
        audit_writer: AuditWriter,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._journal = journal
        self._cursor_codec = cursor_codec
        self._audit_writer = audit_writer
        self._clock = clock or SystemClock()
        self._command_lock = threading.RLock()

    def create(
        self,
        *,
        identity: IdentityContext,
        resource_type: str,
        payload: dict[str, Any],
        operation_id: str,
        idempotency_key: str,
        request_id: str,
    ) -> MarketResourceRecord:
        if resource_type not in INITIAL_STATES:
            raise BiaiceError("NOT_IMPLEMENTED")
        fingerprint = _fingerprint(operation_id, payload)
        with self._command_lock:
            replay = self._journal.replay(
                scope=identity.scope,
                key=idempotency_key,
                fingerprint=fingerprint,
            )
            if replay is not None:
                return replay
            require_audit(self._audit_writer)
            now = self._clock.now()
            record = MarketResourceRecord(
                resource_id=uuid4(),
                resource_type=resource_type,
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                state=INITIAL_STATES[resource_type],
                state_version=1,
                payload=payload,
                status_reason="CREATED",
                created_at=now,
                created_by=identity.subject_id,
                updated_at=now,
                updated_by=identity.subject_id,
            )
            self._repository.save(scope=identity.scope, record=record)
            self._audit_writer.write(
                identity=identity,
                action=operation_id,
                object_type=resource_type,
                object_id=record.resource_id,
                request_id=request_id,
                reason_code="FR12_RESOURCE_CREATED",
                outcome=record.state,
            )
            self._journal.record(
                scope=identity.scope,
                key=idempotency_key,
                fingerprint=fingerprint,
                response=record,
            )
            return record

    def get(
        self,
        *,
        identity: IdentityContext,
        resource_type: str,
        resource_id: UUID,
    ) -> MarketResourceRecord:
        record = self._repository.get(
            scope=identity.scope,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        if record is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return record

    def list(
        self,
        *,
        identity: IdentityContext,
        resource_type: str,
        limit: int,
        cursor: str | None,
        state: str | None,
    ) -> MarketResourcePage:
        items = tuple(
            self._repository.list(
                scope=identity.scope,
                resource_type=resource_type,
                state=state,
            )
        )
        start = 0
        if cursor is not None:
            decoded = self._cursor_codec.decode(cursor, scope=identity.scope)
            try:
                bound = json.loads(decoded.sort_key)
                if bound != {
                    "resource_type": resource_type,
                    "state": state,
                    "created_at": bound.get("created_at"),
                }:
                    raise ValueError("cursor filters changed")
                marker = next(
                    index
                    for index, item in enumerate(items)
                    if str(item.resource_id) == decoded.tie_breaker
                    and item.created_at.isoformat() == bound["created_at"]
                )
            except (KeyError, StopIteration, TypeError, ValueError) as exc:
                raise BiaiceError("INVALID_CURSOR") from exc
            start = marker + 1
        page_items = items[start : start + limit]
        has_more = start + len(page_items) < len(items)
        next_cursor = None
        if has_more and page_items:
            tail = page_items[-1]
            next_cursor = self._cursor_codec.encode(
                scope=identity.scope,
                sort_key=_cursor_sort_key(
                    resource_type=resource_type,
                    state=state,
                    created_at=tail.created_at,
                ),
                tie_breaker=str(tail.resource_id),
            )
        return MarketResourcePage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def action(
        self,
        *,
        identity: IdentityContext,
        resource_type: str,
        resource_id: UUID,
        action: str,
        command: MarketActionCommand,
        operation_id: str,
        idempotency_key: str,
        request_id: str,
    ) -> MarketResourceRecord:
        fingerprint = _fingerprint(
            operation_id,
            {
                "resource_id": str(resource_id),
                **command.model_dump(mode="json"),
            },
        )
        with self._command_lock:
            replay = self._journal.replay(
                scope=identity.scope,
                key=idempotency_key,
                fingerprint=fingerprint,
            )
            if replay is not None:
                return replay
            current = self.get(
                identity=identity,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            if action in INDEPENDENT_CHECKER_ACTIONS and current.created_by == identity.subject_id:
                raise BiaiceError("MAKER_CHECKER_REQUIRED")
            next_state = self._next_state(
                resource_type=resource_type,
                current_state=current.state,
                action=action,
                command=command,
            )
            require_audit(self._audit_writer)
            updated = current.model_copy(
                update={
                    "state": next_state,
                    "state_version": current.state_version + 1,
                    "status_reason": command.reason_code or operation_id.upper(),
                    "updated_at": self._clock.now(),
                    "updated_by": identity.subject_id,
                }
            )
            self._repository.save(scope=identity.scope, record=updated)
            self._audit_writer.write(
                identity=identity,
                action=operation_id,
                object_type=resource_type,
                object_id=updated.resource_id,
                request_id=request_id,
                reason_code=command.reason_code or "FR12_STATE_TRANSITION",
                outcome=updated.state,
            )
            self._journal.record(
                scope=identity.scope,
                key=idempotency_key,
                fingerprint=fingerprint,
                response=updated,
            )
            return updated

    @staticmethod
    def _next_state(
        *,
        resource_type: str,
        current_state: str,
        action: str,
        command: MarketActionCommand,
    ) -> str:
        if action == "mark-not-required" and command.reason_code is None:
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED",
                detail="mark-not-required requires a verified reason_code.",
            )
        if action == "transition":
            target = command.target_state
            allowed = DYNAMIC_TRANSITIONS.get(resource_type, {}).get(current_state, frozenset())
            if target is None or target not in allowed:
                raise BiaiceError("INVALID_STATE_TRANSITION")
            return target
        transition = FIXED_TRANSITIONS.get((resource_type, action), {})
        try:
            return transition[current_state]
        except KeyError as exc:
            raise BiaiceError("INVALID_STATE_TRANSITION") from exc


def configure_market_privacy_services(app: Any) -> MarketResourceService:
    """Bind the synthetic-only FR-12 adapter to one FastAPI application."""

    configured = app.state.settings.cursor_hmac_key
    raw_secret = (
        configured.get_secret_value().encode("utf-8")
        if configured is not None
        else secrets.token_bytes(32)
    )
    service = MarketResourceService(
        repository=InMemoryMarketResourceRepository(),
        journal=InMemoryCommandJournal(),
        cursor_codec=CursorCodec(hashlib.sha256(raw_secret).digest()),
        audit_writer=app.state.audit_writer,
    )
    app.state.fr12_market_resource_service = service
    return service


def get_market_resource_service(request: Request) -> MarketResourceService:
    return request.app.state.fr12_market_resource_service
