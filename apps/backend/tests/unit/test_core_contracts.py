from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from conftest import DOMAIN_A, DOMAIN_B, TENANT_A, TENANT_B
from pydantic import ValidationError

from biaice.core.audit import (
    HashChainAuditWriter,
    InMemoryAppendOnlyAuditSink,
    verify_hash_chain,
)
from biaice.core.auth import IdentityContext, Permission, Role, TenantScope
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec, assert_etag, compute_etag
from biaice.core.money import Money
from biaice.core.outbox import EventEnvelope
from biaice.core.security.restricted_ports import SecretStorePort
from biaice.core.telemetry import TelemetryEnvelope


def test_money_rejects_binary_float_and_serializes_decimal_string() -> None:
    with pytest.raises(ValidationError):
        Money(amount=1.2, currency="CNY")
    money = Money(amount=Decimal("1.20"), currency="CNY")
    assert money.model_dump(mode="json") == {"amount": "1.20", "currency": "CNY"}


def test_tenant_scope_rejects_cross_tenant_and_cross_domain() -> None:
    scope = TenantScope(tenant_id=TENANT_A, data_domain_id=DOMAIN_A)
    with pytest.raises(BiaiceError) as error:
        scope.assert_allows(tenant_id=TENANT_B, data_domain_id=DOMAIN_A)
    assert error.value.code == "TENANT_SCOPE_VIOLATION"
    with pytest.raises(BiaiceError):
        scope.assert_allows(tenant_id=TENANT_A, data_domain_id=DOMAIN_B)


def test_empty_project_scope_is_no_access_not_wildcard() -> None:
    project_id = uuid4()
    scope = TenantScope(tenant_id=TENANT_A, data_domain_id=DOMAIN_A)
    with pytest.raises(BiaiceError):
        scope.assert_allows(
            tenant_id=TENANT_A, data_domain_id=DOMAIN_A, project_id=project_id
        )
    wildcard = scope.model_copy(update={"all_projects": True})
    wildcard.assert_allows(
        tenant_id=TENANT_A, data_domain_id=DOMAIN_A, project_id=project_id
    )


def test_signed_cursor_cannot_cross_scope_or_be_tampered() -> None:
    codec = CursorCodec(b"x" * 32)
    scope_a = TenantScope(tenant_id=TENANT_A, data_domain_id=DOMAIN_A)
    cursor = codec.encode(
        scope=scope_a, sort_key="2026-08-14T00:00:00Z", tie_breaker=str(uuid4())
    )
    assert codec.decode(cursor, scope=scope_a).sort_key == "2026-08-14T00:00:00Z"
    with pytest.raises(BiaiceError) as mismatch:
        codec.decode(
            cursor, scope=TenantScope(tenant_id=TENANT_B, data_domain_id=DOMAIN_A)
        )
    assert mismatch.value.code == "CURSOR_SCOPE_MISMATCH"
    with pytest.raises(BiaiceError) as tampered:
        codec.decode(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), scope=scope_a)
    assert tampered.value.code == "INVALID_CURSOR"


def test_etag_is_stable_and_compare_is_fail_closed() -> None:
    assert compute_etag({"b": 2, "a": 1}) == compute_etag({"a": 1, "b": 2})
    with pytest.raises(BiaiceError) as error:
        assert_etag(compute_etag({"a": 1}), compute_etag({"a": 2}))
    assert error.value.code == "ETAG_MISMATCH"


def test_system_admin_does_not_inherit_sensitive_content_or_cost_permissions(
    identity: IdentityContext,
) -> None:
    admin = identity.model_copy(update={"roles": frozenset({Role.SYSTEM_ADMIN})})
    assert Permission.SENSITIVE_CONTENT_READ not in admin.permissions
    assert Permission.COST_READ not in admin.permissions


def test_secret_store_public_contract_has_no_plaintext_read_or_list() -> None:
    members = set(SecretStorePort.__dict__)
    assert "read" not in members
    assert "list" not in members
    assert {"write", "rotate", "restrict_to_deletion", "destroy"}.issubset(members)


def test_event_and_telemetry_envelopes_reject_sensitive_payload_keys() -> None:
    common = {
        "event_id": uuid4(),
        "event_name": "safe.metric",
        "occurred_at": "2026-08-14T00:00:00Z",
        "request_id": "request-12345678",
    }
    with pytest.raises(ValidationError):
        TelemetryEnvelope(**common, attributes={"prompt": "do not log"})

    with pytest.raises(ValidationError):
        EventEnvelope(
            event_id=uuid4(),
            event_type="governance.deletion.requested.v1",
            schema_version=1,
            tenant_id=TENANT_A,
            data_domain_id=DOMAIN_A,
            aggregate_type="DeletionJob",
            aggregate_id=uuid4(),
            occurred_at="2026-08-14T00:00:00Z",
            request_id="request-12345678",
            correlation_id=uuid4(),
            payload={"nested": {"apiKey": "forbidden"}},
        )


def test_audit_hash_chain_detects_tampering(identity: IdentityContext) -> None:
    sink = InMemoryAppendOnlyAuditSink()
    writer = HashChainAuditWriter(sink)
    first = writer.write(
        identity=identity,
        action="object.read",
        object_type="SyntheticFixture",
        object_id=uuid4(),
        request_id="request-12345678",
        reason_code="TEST",
        outcome="ALLOWED",
    )
    second = writer.write(
        identity=identity,
        action="object.publish",
        object_type="SyntheticFixture",
        object_id=uuid4(),
        request_id="request-87654321",
        reason_code="TEST",
        outcome="ALLOWED",
    )
    assert verify_hash_chain((first, second)) == second.event_hash
    with pytest.raises(BiaiceError) as error:
        verify_hash_chain(
            (first, second.model_copy(update={"reason_code": "TAMPERED"}))
        )
    assert error.value.code == "AUDIT_INTEGRITY_FAILED"
