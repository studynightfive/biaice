"""Fail-closed Provider catalog, configuration and redacted invocation orchestration."""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeVar, cast
from uuid import UUID, uuid4

from fastapi import FastAPI
from pydantic import BaseModel, SecretStr

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec, assert_etag, compute_etag
from biaice.core.security.gates import GateName, GateService
from biaice.core.security.restricted_ports import (
    CredentialUsageScope,
    SecretReference,
    SecretStorePort,
)
from biaice.modules.market.privacy.application.services import MarketResourceService
from biaice.modules.model_governance.application.repository import (
    ExternalModelReference,
    InMemoryModelLifecycleRepository,
)
from biaice.modules.model_governance.domain.provider_models import (
    AIProviderConfiguration,
    ProviderActionCommand,
    ProviderActivationState,
    ProviderCatalogCreate,
    ProviderCatalogDecision,
    ProviderCatalogPublicEntry,
    ProviderCatalogState,
    ProviderCatalogVersion,
    ProviderConfigurationCreate,
    ProviderConfigurationPage,
    ProviderConfigurationSuccessorCreate,
    ProviderConfigurationUpdate,
    ProviderConnectionTestResult,
    ProviderCredentialMetadata,
    ProviderCredentialReceipt,
    ProviderCredentialState,
    ProviderCredentialWrite,
    ProviderDeletionAccepted,
    ProviderHealth,
    ProviderInvocationPage,
    ProviderInvocationRecord,
    ProviderInvocationState,
    ProviderRotationMode,
    ProviderValidity,
    PublishedProviderCatalog,
)

ResponseT = TypeVar("ResponseT", bound=BaseModel)
PLATFORM_CATALOG_ROLES = frozenset({Role.SYSTEM_ADMIN, Role.GOVERNANCE_ADMIN})
PLATFORM_CATALOG_CHECKER_ROLES = frozenset({Role.PRIVACY_OFFICER, Role.LEGAL_PRIVACY})
TENANT_PROVIDER_READ_ROLES = frozenset(
    {
        Role.TENANT_AI_ADMIN,
        Role.GOVERNANCE_ADMIN,
        Role.PRIVACY_OFFICER,
        Role.LEGAL_PRIVACY,
        Role.AUDITOR,
    }
)


@dataclass(frozen=True, slots=True)
class ProviderConnectionOutcome:
    state: ProviderInvocationState
    reachable: bool
    authenticated: bool
    model_available: bool
    rate_limited: bool
    provider_health: ProviderHealth
    request_hash: str
    response_hash: str | None = None
    cost_minor: int = 0
    stable_error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderDeletionJob:
    job_id: UUID
    status_url: str


class ProviderRuntimePort(Protocol):
    """Approved catalog sync, fixed probe and deletion orchestration boundary."""

    def catalog_is_synced(self, *, catalog_id: UUID, catalog_hash: str) -> bool: ...

    def test_connection(
        self,
        *,
        scope: TenantScope,
        configuration: AIProviderConfiguration,
        credential: SecretReference,
    ) -> ProviderConnectionOutcome: ...

    def enqueue_deletion(
        self,
        *,
        scope: TenantScope,
        configuration: AIProviderConfiguration,
        credential: SecretReference | None,
        reason_code: str,
        idempotency_key: str,
    ) -> ProviderDeletionJob: ...


class UnavailableProviderRuntime:
    def catalog_is_synced(self, *, catalog_id: UUID, catalog_hash: str) -> bool:
        del catalog_id, catalog_hash
        return False

    def test_connection(self, **kwargs: Any) -> ProviderConnectionOutcome:
        del kwargs
        raise BiaiceError("EGRESS_AUTHORIZATION_UNAVAILABLE")

    def enqueue_deletion(self, **kwargs: Any) -> ProviderDeletionJob:
        del kwargs
        raise BiaiceError("JOB_STORE_UNAVAILABLE")


class UnavailableSecretStore:
    """Default adapter: reject without retaining or exposing the supplied secret."""

    def _unavailable(self) -> None:
        raise BiaiceError("SECRET_STORE_UNAVAILABLE")

    def write(self, **kwargs: Any) -> SecretReference:
        del kwargs
        self._unavailable()

    def rotate(self, **kwargs: Any) -> SecretReference:
        del kwargs
        self._unavailable()

    def restrict_to_deletion(self, **kwargs: Any) -> SecretReference:
        del kwargs
        self._unavailable()

    def authorize_business(self, **kwargs: Any) -> SecretReference:
        del kwargs
        self._unavailable()

    def destroy(self, **kwargs: Any) -> None:
        del kwargs
        self._unavailable()


@dataclass(frozen=True, slots=True)
class IdempotentEntry:
    fingerprint: str
    response: BaseModel


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _catalog_hash(command: ProviderCatalogCreate) -> str:
    return _fingerprint(
        [item.model_dump(mode="json") for item in command.entries]
    )


def _credential_reference(configuration: AIProviderConfiguration) -> SecretReference | None:
    metadata = configuration.credential
    if metadata is None:
        return None
    return SecretReference(
        reference_id=metadata.credential_reference_id,
        credential_version=metadata.credential_version,
        fingerprint=metadata.fingerprint,
        last_four=metadata.last_four,
        usage_scope=configuration.credential_usage_scope,
        created_at=metadata.created_at,
        expires_at=metadata.expires_at,
    )


def configuration_etag(configuration: AIProviderConfiguration) -> str:
    return compute_etag(configuration.model_dump(mode="json"))


class ProviderManagementService:
    """In-process metadata store with injected secure-secret and egress boundaries."""

    def __init__(
        self,
        *,
        audit_writer: AuditWriter,
        gate_service: GateService,
        privacy_service: MarketResourceService,
        model_repository: InMemoryModelLifecycleRepository,
        cursor_codec: CursorCodec,
        secret_store: SecretStorePort | None = None,
        runtime: ProviderRuntimePort | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._audit = audit_writer
        self._gates = gate_service
        self._privacy = privacy_service
        self._model_repository = model_repository
        self._cursor_codec = cursor_codec
        self._secret_store = secret_store or UnavailableSecretStore()
        self._runtime = runtime or UnavailableProviderRuntime()
        self._clock = clock or SystemClock()
        self._catalogs: dict[UUID, ProviderCatalogVersion] = {}
        self._published_catalog_id: UUID | None = None
        self._configurations: dict[UUID, AIProviderConfiguration] = {}
        self._invocations: dict[UUID, ProviderInvocationRecord] = {}
        self._idempotency: dict[tuple[str, str, str, str], IdempotentEntry] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _require_role(
        identity: IdentityContext,
        allowed: frozenset[Role],
        *,
        mfa: bool = False,
    ) -> None:
        if mfa and not identity.mfa_verified:
            raise BiaiceError("MFA_REQUIRED")
        if identity.roles.isdisjoint(allowed):
            raise BiaiceError("PERMISSION_DENIED")

    @staticmethod
    def _scope_key(identity: IdentityContext) -> tuple[str, str]:
        return str(identity.scope.tenant_id), str(identity.scope.data_domain_id)

    def _execute_idempotent(
        self,
        *,
        identity: IdentityContext,
        operation_id: str,
        idempotency_key: str,
        fingerprint: str,
        expected_type: type[ResponseT],
        command: Callable[[], ResponseT],
    ) -> ResponseT:
        tenant, domain = self._scope_key(identity)
        key = (tenant, domain, operation_id, idempotency_key)
        stored = self._idempotency.get(key)
        if stored is not None:
            if stored.fingerprint != fingerprint:
                raise BiaiceError("IDEMPOTENCY_CONFLICT")
            if not isinstance(stored.response, expected_type):
                raise BiaiceError("INTERNAL_ERROR", detail="Idempotent response type mismatch.")
            return cast(ResponseT, stored.response)
        response = command()
        self._idempotency[key] = IdempotentEntry(fingerprint=fingerprint, response=response)
        return response

    def _write_audit(
        self,
        *,
        identity: IdentityContext,
        operation_id: str,
        object_type: str,
        object_id: UUID,
        request_id: str,
        reason_code: str,
        outcome: str,
    ) -> None:
        self._audit.write(
            identity=identity,
            action=operation_id,
            object_type=object_type,
            object_id=object_id,
            request_id=request_id,
            reason_code=reason_code,
            outcome=outcome,
        )

    def list_catalog(self, *, identity: IdentityContext) -> PublishedProviderCatalog:
        del identity
        with self._lock:
            catalog = (
                self._catalogs.get(self._published_catalog_id)
                if self._published_catalog_id is not None
                else None
            )
        if catalog is None or catalog.state is not ProviderCatalogState.PUBLISHED:
            return PublishedProviderCatalog()
        return PublishedProviderCatalog(
            catalog_id=catalog.catalog_id,
            catalog_hash=catalog.catalog_hash,
            published_at=catalog.published_at,
            items=tuple(
                ProviderCatalogPublicEntry(
                    provider_id=item.provider_id,
                    provider_legal_name=item.provider_legal_name,
                    provider_model_id=item.provider_model_id,
                    display_name=item.display_name,
                    capabilities=item.capabilities,
                    regions=item.regions,
                    allowed_purposes=item.allowed_purposes,
                    max_input_tokens=item.max_input_tokens,
                    redaction_policy_summary=item.redaction_policy_summary,
                    training_use=item.training_use,
                    retention_days=item.retention_days,
                )
                for item in catalog.entries
            ),
        )

    def create_catalog(
        self,
        *,
        identity: IdentityContext,
        command: ProviderCatalogCreate,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderCatalogVersion:
        self._require_role(identity, PLATFORM_CATALOG_ROLES, mfa=True)
        fingerprint = _fingerprint(command.model_dump(mode="json"))
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="create_ai_provider_catalog_version",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=ProviderCatalogVersion,
                command=lambda: self._create_catalog(identity, command, request_id),
            )

    def _create_catalog(
        self,
        identity: IdentityContext,
        command: ProviderCatalogCreate,
        request_id: str,
    ) -> ProviderCatalogVersion:
        require_audit(self._audit)
        now = self._clock.now()
        catalog = ProviderCatalogVersion(
            catalog_id=uuid4(),
            version_number=len(self._catalogs) + 1,
            state=ProviderCatalogState.DRAFT,
            catalog_hash=_catalog_hash(command),
            entries=command.entries,
            created_at=now,
            created_by=identity.subject_id,
            reason_code=command.reason_code,
        )
        self._write_audit(
            identity=identity,
            operation_id="create_ai_provider_catalog_version",
            object_type="provider_catalog",
            object_id=catalog.catalog_id,
            request_id=request_id,
            reason_code=command.reason_code,
            outcome=catalog.state,
        )
        self._catalogs[catalog.catalog_id] = catalog
        return catalog

    def get_catalog(
        self, *, identity: IdentityContext, catalog_id: UUID
    ) -> ProviderCatalogVersion:
        self._require_role(
            identity,
            PLATFORM_CATALOG_ROLES | PLATFORM_CATALOG_CHECKER_ROLES,
        )
        with self._lock:
            catalog = self._catalogs.get(catalog_id)
        if catalog is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return catalog

    def decide_catalog(
        self,
        *,
        identity: IdentityContext,
        catalog_id: UUID,
        action: str,
        command: ProviderCatalogDecision,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderCatalogVersion:
        self._require_role(identity, PLATFORM_CATALOG_CHECKER_ROLES, mfa=True)
        fingerprint = _fingerprint(
            {"catalog_id": str(catalog_id), "action": action, **command.model_dump(mode="json")}
        )
        operation_id = f"{action}_ai_provider_catalog_version"
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id=operation_id,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=ProviderCatalogVersion,
                command=lambda: self._decide_catalog(
                    identity, catalog_id, action, command, request_id
                ),
            )

    def _decide_catalog(
        self,
        identity: IdentityContext,
        catalog_id: UUID,
        action: str,
        command: ProviderCatalogDecision,
        request_id: str,
    ) -> ProviderCatalogVersion:
        current = self._catalogs.get(catalog_id)
        if current is None:
            raise BiaiceError("RESOURCE_NOT_FOUND")
        if current.created_by == identity.subject_id:
            raise BiaiceError("MAKER_CHECKER_REQUIRED")
        require_audit(self._audit)
        now = self._clock.now()
        if action == "publish":
            if current.state is not ProviderCatalogState.DRAFT:
                raise BiaiceError("INVALID_STATE_TRANSITION")
            updated = current.model_copy(
                update={
                    "state": ProviderCatalogState.PUBLISHED,
                    "published_at": now,
                    "published_by": identity.subject_id,
                    "approval_evidence_hash": command.approval_evidence_hash,
                }
            )
            self._published_catalog_id = catalog_id
        elif action == "revoke":
            if current.state is not ProviderCatalogState.PUBLISHED:
                raise BiaiceError("INVALID_STATE_TRANSITION")
            updated = current.model_copy(
                update={
                    "state": ProviderCatalogState.REVOKED,
                    "revoked_at": now,
                    "revoked_by": identity.subject_id,
                    "revocation_reason": command.reason_code,
                }
            )
            if self._published_catalog_id == catalog_id:
                self._published_catalog_id = None
        else:
            raise BiaiceError("INVALID_STATE_TRANSITION")
        operation_id = f"{action}_ai_provider_catalog_version"
        self._write_audit(
            identity=identity,
            operation_id=operation_id,
            object_type="provider_catalog",
            object_id=catalog_id,
            request_id=request_id,
            reason_code=command.reason_code,
            outcome=updated.state,
        )
        self._catalogs[catalog_id] = updated
        return updated

    def _published_catalog(self, catalog_id: UUID, catalog_hash: str) -> ProviderCatalogVersion:
        catalog = self._catalogs.get(catalog_id)
        if (
            catalog is None
            or catalog.state is not ProviderCatalogState.PUBLISHED
            or self._published_catalog_id != catalog_id
            or catalog.catalog_hash != catalog_hash
        ):
            raise BiaiceError("PROVIDER_CATALOG_NOT_CURRENT")
        return catalog

    @staticmethod
    def _catalog_entry(
        catalog: ProviderCatalogVersion,
        provider_id: str,
        provider_model_id: str,
    ):
        entry = next(
            (
                item
                for item in catalog.entries
                if item.provider_id == provider_id
                and item.provider_model_id == provider_model_id
            ),
            None,
        )
        if entry is None:
            raise BiaiceError("PROVIDER_CATALOG_NOT_CURRENT")
        return entry

    def create_configuration(
        self,
        *,
        identity: IdentityContext,
        command: ProviderConfigurationCreate,
        idempotency_key: str,
        request_id: str,
    ) -> AIProviderConfiguration:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        fingerprint = _fingerprint(command.model_dump(mode="json"))
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="create_ai_provider_configuration",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=AIProviderConfiguration,
                command=lambda: self._create_configuration(identity, command, request_id),
            )

    def _create_configuration(
        self,
        identity: IdentityContext,
        command: ProviderConfigurationCreate,
        request_id: str,
    ) -> AIProviderConfiguration:
        catalog = self._published_catalog(command.catalog_id, command.catalog_hash)
        entry = self._catalog_entry(catalog, command.provider_id, command.provider_model_id)
        if command.purpose not in entry.allowed_purposes or command.retention_days > entry.retention_days:
            raise BiaiceError("PROVIDER_POLICY_NOT_CURRENT")
        require_audit(self._audit)
        now = self._clock.now()
        configuration = AIProviderConfiguration(
            config_id=uuid4(),
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            version_number=1,
            current=True,
            **command.model_dump(),
            activation_state=ProviderActivationState.INACTIVE,
            credential_state=ProviderCredentialState.MISSING,
            credential_usage_scope=CredentialUsageScope.NONE,
            provider_health=ProviderHealth.UNKNOWN,
            validity_state=ProviderValidity.CURRENT,
            state_version=1,
            created_at=now,
            created_by=identity.subject_id,
            updated_at=now,
            updated_by=identity.subject_id,
        )
        self._write_audit(
            identity=identity,
            operation_id="create_ai_provider_configuration",
            object_type="provider_configuration",
            object_id=configuration.config_id,
            request_id=request_id,
            reason_code="PROVIDER_CONFIGURATION_CREATED",
            outcome=configuration.activation_state,
        )
        self._configurations[configuration.config_id] = configuration
        return configuration

    def _configuration(
        self, identity: IdentityContext, config_id: UUID
    ) -> AIProviderConfiguration:
        item = self._configurations.get(config_id)
        if (
            item is None
            or item.tenant_id != identity.scope.tenant_id
            or item.data_domain_id != identity.scope.data_domain_id
        ):
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def get_configuration(
        self, *, identity: IdentityContext, config_id: UUID
    ) -> AIProviderConfiguration:
        self._require_role(identity, TENANT_PROVIDER_READ_ROLES)
        with self._lock:
            return self._configuration(identity, config_id)

    def list_configurations(
        self,
        *,
        identity: IdentityContext,
        limit: int,
        cursor: str | None,
    ) -> ProviderConfigurationPage:
        self._require_role(identity, TENANT_PROVIDER_READ_ROLES)
        with self._lock:
            items = tuple(
                sorted(
                    (
                        item
                        for item in self._configurations.values()
                        if item.tenant_id == identity.scope.tenant_id
                        and item.data_domain_id == identity.scope.data_domain_id
                    ),
                    key=lambda item: (item.created_at, str(item.config_id)),
                )
            )
        page_items, next_cursor, has_more = self._page(
            identity=identity,
            items=items,
            cursor=cursor,
            limit=limit,
            collection="provider-configurations",
            item_id=lambda item: item.config_id,
            created_at=lambda item: item.created_at,
        )
        return ProviderConfigurationPage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def update_configuration(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderConfigurationUpdate,
        if_match: str,
        request_id: str,
    ) -> AIProviderConfiguration:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        with self._lock:
            current = self._configuration(identity, config_id)
            if current.activation_state not in {
                ProviderActivationState.INACTIVE,
                ProviderActivationState.VERIFIED,
            }:
                raise BiaiceError("INVALID_STATE_TRANSITION")
            assert_etag(configuration_etag(current), if_match)
            changes = command.model_dump(exclude_none=True, exclude_unset=True)
            catalog = self._published_catalog(current.catalog_id, current.catalog_hash)
            entry = self._catalog_entry(catalog, current.provider_id, current.provider_model_id)
            purpose = changes.get("purpose", current.purpose)
            retention_days = changes.get("retention_days", current.retention_days)
            if purpose not in entry.allowed_purposes or retention_days > entry.retention_days:
                raise BiaiceError("PROVIDER_POLICY_NOT_CURRENT")
            require_audit(self._audit)
            updated = current.model_copy(
                update={
                    **changes,
                    "state_version": current.state_version + 1,
                    "updated_at": self._clock.now(),
                    "updated_by": identity.subject_id,
                }
            )
            self._write_audit(
                identity=identity,
                operation_id="update_ai_provider_configuration",
                object_type="provider_configuration",
                object_id=config_id,
                request_id=request_id,
                reason_code="PROVIDER_CONFIGURATION_UPDATED",
                outcome=updated.activation_state,
            )
            self._configurations[config_id] = updated
            return updated

    def create_successor(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderConfigurationSuccessorCreate,
        idempotency_key: str,
        request_id: str,
    ) -> AIProviderConfiguration:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        fingerprint = _fingerprint(
            {"config_id": str(config_id), **command.model_dump(mode="json")}
        )
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="create_ai_provider_configuration_successor",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=AIProviderConfiguration,
                command=lambda: self._create_successor(
                    identity, config_id, command, idempotency_key, request_id
                ),
            )

    def _create_successor(
        self,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderConfigurationSuccessorCreate,
        idempotency_key: str,
        request_id: str,
    ) -> AIProviderConfiguration:
        current = self._configuration(identity, config_id)
        if current.activation_state is not ProviderActivationState.ACTIVE:
            raise BiaiceError("PROVIDER_CREDENTIAL_ROTATION_REQUIRES_SUCCESSOR")
        conflict = any(
            item.supersedes_config_id == config_id
            and item.activation_state not in {ProviderActivationState.REVOKED}
            for item in self._configurations.values()
        )
        if conflict:
            raise BiaiceError("PROVIDER_ROTATION_CONFLICT")
        require_audit(self._audit)
        now = self._clock.now()
        if command.rotation_mode is ProviderRotationMode.COMPROMISE:
            compromised_reference = _credential_reference(current)
            if compromised_reference is not None:
                self._secret_store.destroy(
                    scope=identity.scope,
                    reference=compromised_reference,
                )
            current = current.model_copy(
                update={
                    "current": False,
                    "activation_state": ProviderActivationState.REVOKED,
                    "credential_state": ProviderCredentialState.REVOKED,
                    "credential_usage_scope": CredentialUsageScope.NONE,
                    "state_version": current.state_version + 1,
                    "updated_at": now,
                    "updated_by": identity.subject_id,
                    "gate_reason_codes": ("PROVIDER_CREDENTIAL_COMPROMISED",),
                }
            )
            self._configurations[current.config_id] = current
            self._runtime.enqueue_deletion(
                scope=identity.scope,
                configuration=current,
                credential=None,
                reason_code=command.reason_code,
                idempotency_key=idempotency_key,
            )
            self._write_audit(
                identity=identity,
                operation_id="revoke_ai_provider_configuration",
                object_type="provider_configuration",
                object_id=current.config_id,
                request_id=request_id,
                reason_code=command.reason_code,
                outcome=ProviderActivationState.REVOKED,
            )
        successor = current.model_copy(
            update={
                "config_id": uuid4(),
                "version_number": current.version_number + 1,
                "current": False,
                "activation_state": ProviderActivationState.INACTIVE,
                "credential_state": ProviderCredentialState.MISSING,
                "credential_usage_scope": CredentialUsageScope.NONE,
                "credential": None,
                "provider_health": ProviderHealth.UNKNOWN,
                "supersedes_config_id": current.config_id,
                "rotation_mode": command.rotation_mode,
                "state_version": 1,
                "created_at": now,
                "created_by": identity.subject_id,
                "updated_at": now,
                "updated_by": identity.subject_id,
                "last_tested_at": None,
            }
        )
        self._write_audit(
            identity=identity,
            operation_id="create_ai_provider_configuration_successor",
            object_type="provider_configuration",
            object_id=successor.config_id,
            request_id=request_id,
            reason_code=command.reason_code,
            outcome=successor.activation_state,
        )
        self._configurations[successor.config_id] = successor
        return successor

    def set_credential(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderCredentialWrite,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderCredentialReceipt:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        self._gates.require(GateName.BYOK_SECRET_GATE)
        secret_hash = hashlib.sha256(
            command.api_key.get_secret_value().encode("utf-8")
        ).hexdigest()
        fingerprint = _fingerprint({"config_id": str(config_id), "secret_hash": secret_hash})
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="set_ai_provider_credential",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=ProviderCredentialReceipt,
                command=lambda: self._set_credential(
                    identity, config_id, command.api_key, request_id
                ),
            )

    def _set_credential(
        self,
        identity: IdentityContext,
        config_id: UUID,
        plaintext: SecretStr,
        request_id: str,
    ) -> ProviderCredentialReceipt:
        current = self._configuration(identity, config_id)
        if current.activation_state is ProviderActivationState.ACTIVE:
            raise BiaiceError("PROVIDER_CREDENTIAL_ROTATION_REQUIRES_SUCCESSOR")
        if current.activation_state in {
            ProviderActivationState.SUSPENDED,
            ProviderActivationState.REVOKED,
        }:
            raise BiaiceError("INVALID_STATE_TRANSITION")
        require_audit(self._audit)
        previous = _credential_reference(current)
        reference = (
            self._secret_store.rotate(
                scope=identity.scope,
                old_reference=previous,
                plaintext=plaintext,
            )
            if previous is not None
            else self._secret_store.write(
                scope=identity.scope,
                provider_id=current.provider_id,
                purpose=current.purpose,
                plaintext=plaintext,
            )
        )
        if reference.usage_scope is not CredentialUsageScope.TEST_ONLY:
            self._secret_store.destroy(scope=identity.scope, reference=reference)
            raise BiaiceError("PROVIDER_CREDENTIAL_USAGE_NOT_ALLOWED")
        metadata = ProviderCredentialMetadata(
            credential_reference_id=reference.reference_id,
            credential_version=reference.credential_version,
            fingerprint=reference.fingerprint,
            last_four=reference.last_four,
            created_at=reference.created_at,
            expires_at=reference.expires_at,
        )
        updated = current.model_copy(
            update={
                "activation_state": ProviderActivationState.INACTIVE,
                "credential_state": ProviderCredentialState.UNVERIFIED,
                "credential_usage_scope": CredentialUsageScope.TEST_ONLY,
                "credential": metadata,
                "provider_health": ProviderHealth.UNKNOWN,
                "state_version": current.state_version + 1,
                "updated_at": self._clock.now(),
                "updated_by": identity.subject_id,
                "last_tested_at": None,
            }
        )
        try:
            self._write_audit(
                identity=identity,
                operation_id="set_ai_provider_credential",
                object_type="provider_configuration",
                object_id=config_id,
                request_id=request_id,
                reason_code="PROVIDER_CREDENTIAL_SET",
                outcome=updated.credential_state,
            )
        except Exception:
            self._secret_store.destroy(scope=identity.scope, reference=reference)
            raise
        self._configurations[config_id] = updated
        return ProviderCredentialReceipt(
            **metadata.model_dump(),
            credential_state=updated.credential_state,
            credential_usage_scope=updated.credential_usage_scope,
        )

    def test_connection(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderConnectionTestResult:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        self._gates.require(GateName.BYOK_SECRET_GATE)
        fingerprint = _fingerprint({"config_id": str(config_id)})
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="test_ai_provider_connection",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=ProviderConnectionTestResult,
                command=lambda: self._test_connection(identity, config_id, request_id),
            )

    def _test_connection(
        self,
        identity: IdentityContext,
        config_id: UUID,
        request_id: str,
    ) -> ProviderConnectionTestResult:
        current = self._configuration(identity, config_id)
        if current.activation_state not in {
            ProviderActivationState.INACTIVE,
            ProviderActivationState.VERIFIED,
        }:
            raise BiaiceError("INVALID_STATE_TRANSITION")
        if current.credential_state not in {
            ProviderCredentialState.UNVERIFIED,
            ProviderCredentialState.VALID,
        }:
            raise BiaiceError("PROVIDER_CREDENTIAL_MISSING")
        if current.credential_usage_scope is not CredentialUsageScope.TEST_ONLY:
            raise BiaiceError("PROVIDER_CREDENTIAL_USAGE_NOT_ALLOWED")
        credential = _credential_reference(current)
        if credential is None:
            raise BiaiceError("PROVIDER_CREDENTIAL_MISSING")
        self._published_catalog(current.catalog_id, current.catalog_hash)
        if not self._runtime.catalog_is_synced(
            catalog_id=current.catalog_id,
            catalog_hash=current.catalog_hash,
        ):
            raise BiaiceError("PROVIDER_EGRESS_BLOCKED")
        require_audit(self._audit)
        outcome = self._runtime.test_connection(
            scope=identity.scope,
            configuration=current,
            credential=credential,
        )
        now = self._clock.now()
        invocation = ProviderInvocationRecord(
            invocation_id=uuid4(),
            tenant_id=current.tenant_id,
            data_domain_id=current.data_domain_id,
            config_id=current.config_id,
            provider_id=current.provider_id,
            provider_model_id=current.provider_model_id,
            purpose="CONNECTION_TEST",
            state=outcome.state,
            attempt=1,
            started_at=now,
            completed_at=now,
            request_hash=outcome.request_hash,
            response_hash=outcome.response_hash,
            cost_minor=outcome.cost_minor,
            currency=current.currency,
            stable_error_code=outcome.stable_error_code,
        )
        authenticated = outcome.authenticated and outcome.model_available
        credential_state = (
            ProviderCredentialState.VALID
            if authenticated
            else ProviderCredentialState.INVALID
            if outcome.stable_error_code in {
                "PROVIDER_CREDENTIAL_INVALID",
                "PROVIDER_CREDENTIAL_REVOKED",
            }
            else current.credential_state
        )
        activation_state = (
            ProviderActivationState.VERIFIED
            if authenticated
            else ProviderActivationState.INACTIVE
        )
        updated = current.model_copy(
            update={
                "activation_state": activation_state,
                "credential_state": credential_state,
                "provider_health": outcome.provider_health,
                "state_version": current.state_version + 1,
                "updated_at": now,
                "updated_by": identity.subject_id,
                "last_tested_at": now,
                "gate_reason_codes": ()
                if authenticated
                else tuple(filter(None, (outcome.stable_error_code,))),
            }
        )
        self._write_audit(
            identity=identity,
            operation_id="test_ai_provider_connection",
            object_type="provider_invocation",
            object_id=invocation.invocation_id,
            request_id=request_id,
            reason_code=outcome.stable_error_code or "PROVIDER_CONFIGURATION_VERIFIED",
            outcome=outcome.state,
        )
        self._configurations[config_id] = updated
        self._invocations[invocation.invocation_id] = invocation
        return ProviderConnectionTestResult(
            invocation_id=invocation.invocation_id,
            reachable=outcome.reachable,
            authenticated=outcome.authenticated,
            model_available=outcome.model_available,
            rate_limited=outcome.rate_limited,
            provider_health=outcome.provider_health,
            stable_error_code=outcome.stable_error_code,
            tested_at=now,
        )

    def _assert_governance_current(
        self,
        *,
        identity: IdentityContext,
        configuration: AIProviderConfiguration,
    ) -> None:
        requirements = (
            ("legal_basis_evidence", configuration.legal_basis_evidence_id, {"CURRENT"}),
            ("provider_policy", configuration.provider_policy_id, {"APPROVED"}),
            ("pia_record", configuration.pia_record_id, {"APPROVED"}),
            (
                "cross_border_assessment",
                configuration.cross_border_assessment_id,
                {"APPROVED", "NOT_REQUIRED"},
            ),
        )
        for resource_type, resource_id, allowed_states in requirements:
            record = self._privacy.get(
                identity=identity,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            if record.state not in allowed_states:
                raise BiaiceError("PROVIDER_POLICY_NOT_CURRENT")
            if resource_type != "legal_basis_evidence" and record.updated_by == configuration.created_by:
                raise BiaiceError("MAKER_CHECKER_REQUIRED")

    def activate_configuration(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        idempotency_key: str,
        request_id: str,
    ) -> AIProviderConfiguration:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        self._gates.require(GateName.BYOK_SECRET_GATE)
        fingerprint = _fingerprint(
            {"config_id": str(config_id), **command.model_dump(mode="json")}
        )
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="activate_ai_provider_configuration",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=AIProviderConfiguration,
                command=lambda: self._activate_configuration(
                    identity, config_id, command, request_id
                ),
            )

    def _activate_configuration(
        self,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        request_id: str,
    ) -> AIProviderConfiguration:
        current = self._configuration(identity, config_id)
        if current.activation_state is not ProviderActivationState.VERIFIED:
            raise BiaiceError("PROVIDER_CREDENTIAL_UNVERIFIED")
        if current.credential_state is not ProviderCredentialState.VALID:
            raise BiaiceError("PROVIDER_CREDENTIAL_INVALID")
        if current.credential_usage_scope is not CredentialUsageScope.TEST_ONLY:
            raise BiaiceError("PROVIDER_CREDENTIAL_USAGE_NOT_ALLOWED")
        self._published_catalog(current.catalog_id, current.catalog_hash)
        if not self._runtime.catalog_is_synced(
            catalog_id=current.catalog_id,
            catalog_hash=current.catalog_hash,
        ):
            raise BiaiceError("PROVIDER_EGRESS_BLOCKED")
        self._assert_governance_current(identity=identity, configuration=current)
        other_active = next(
            (
                item
                for item in self._configurations.values()
                if item.config_id != current.config_id
                and item.tenant_id == current.tenant_id
                and item.data_domain_id == current.data_domain_id
                and item.provider_id == current.provider_id
                and item.provider_model_id == current.provider_model_id
                and item.purpose == current.purpose
                and item.activation_state is ProviderActivationState.ACTIVE
            ),
            None,
        )
        predecessor = (
            self._configuration(identity, current.supersedes_config_id)
            if current.supersedes_config_id is not None
            else None
        )
        if other_active is not None and (
            predecessor is None or other_active.config_id != predecessor.config_id
        ):
            raise BiaiceError("PROVIDER_ROTATION_CONFLICT")
        require_audit(self._audit)
        if predecessor is not None:
            previous_secret = _credential_reference(predecessor)
            if previous_secret is not None:
                restricted = self._secret_store.restrict_to_deletion(
                    scope=identity.scope,
                    reference=previous_secret,
                )
                predecessor = predecessor.model_copy(
                    update={
                        "credential_usage_scope": restricted.usage_scope,
                        "activation_state": ProviderActivationState.SUSPENDED,
                        "current": False,
                        "state_version": predecessor.state_version + 1,
                        "updated_at": self._clock.now(),
                        "updated_by": identity.subject_id,
                    }
                )
        current_secret = _credential_reference(current)
        if current_secret is None:
            raise BiaiceError("PROVIDER_CREDENTIAL_MISSING")
        promoted = self._secret_store.authorize_business(
            scope=identity.scope,
            reference=current_secret,
        )
        if promoted.usage_scope is not CredentialUsageScope.BUSINESS_AND_DELETION:
            raise BiaiceError("PROVIDER_CREDENTIAL_USAGE_NOT_ALLOWED")
        now = self._clock.now()
        updated = current.model_copy(
            update={
                "activation_state": ProviderActivationState.ACTIVE,
                "credential_usage_scope": promoted.usage_scope,
                "current": True,
                "state_version": current.state_version + 1,
                "updated_at": now,
                "updated_by": identity.subject_id,
                "gate_reason_codes": (),
            }
        )
        self._write_audit(
            identity=identity,
            operation_id="activate_ai_provider_configuration",
            object_type="provider_configuration",
            object_id=config_id,
            request_id=request_id,
            reason_code=command.reason_code,
            outcome=updated.activation_state,
        )
        if predecessor is not None:
            self._configurations[predecessor.config_id] = predecessor
        self._configurations[config_id] = updated
        self._model_repository.register_external_model_reference(
            ExternalModelReference(
                tenant_id=updated.tenant_id,
                data_domain_id=updated.data_domain_id,
                catalog_id=updated.catalog_id,
                catalog_hash=updated.catalog_hash,
                provider_id=updated.provider_id,
                provider_model_id=updated.provider_model_id,
                provider_configuration_ids=frozenset({updated.config_id}),
                current=True,
            )
        )
        return updated

    def suspend_configuration(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        idempotency_key: str,
        request_id: str,
    ) -> AIProviderConfiguration:
        return self._stop_configuration(
            identity=identity,
            config_id=config_id,
            command=command,
            idempotency_key=idempotency_key,
            request_id=request_id,
            action="suspend",
        )

    def _stop_configuration(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        idempotency_key: str,
        request_id: str,
        action: str,
    ) -> AIProviderConfiguration:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        fingerprint = _fingerprint(
            {"config_id": str(config_id), "action": action, **command.model_dump(mode="json")}
        )
        operation_id = f"{action}_ai_provider_configuration"
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id=operation_id,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=AIProviderConfiguration,
                command=lambda: self._apply_stop(
                    identity, config_id, command, request_id, action
                ),
            )

    def _apply_stop(
        self,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        request_id: str,
        action: str,
    ) -> AIProviderConfiguration:
        current = self._configuration(identity, config_id)
        target = (
            ProviderActivationState.SUSPENDED
            if action == "suspend"
            else ProviderActivationState.REVOKED
        )
        if current.activation_state is target:
            return current
        if current.activation_state is ProviderActivationState.REVOKED:
            raise BiaiceError("INVALID_STATE_TRANSITION")
        require_audit(self._audit)
        now = self._clock.now()
        updated = current.model_copy(
            update={
                "activation_state": target,
                "current": False if target is ProviderActivationState.REVOKED else current.current,
                "credential_usage_scope": CredentialUsageScope.DELETION_ONLY
                if current.credential is not None
                else CredentialUsageScope.NONE,
                "state_version": current.state_version + 1,
                "updated_at": now,
                "updated_by": identity.subject_id,
                "gate_reason_codes": (f"PROVIDER_CONFIGURATION_{action.upper()}",),
            }
        )
        self._configurations[config_id] = updated
        self._write_audit(
            identity=identity,
            operation_id=f"{action}_ai_provider_configuration",
            object_type="provider_configuration",
            object_id=config_id,
            request_id=request_id,
            reason_code=command.reason_code,
            outcome=target,
        )
        reference = _credential_reference(current)
        if reference is not None:
            self._secret_store.restrict_to_deletion(
                scope=identity.scope,
                reference=reference,
            )
        return updated

    def revoke_configuration(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderDeletionAccepted:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        fingerprint = _fingerprint(
            {"config_id": str(config_id), **command.model_dump(mode="json")}
        )
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="revoke_ai_provider_configuration",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=ProviderDeletionAccepted,
                command=lambda: self._revoke_configuration(
                    identity, config_id, command, idempotency_key, request_id
                ),
            )

    def _revoke_configuration(
        self,
        identity: IdentityContext,
        config_id: UUID,
        command: ProviderActionCommand,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderDeletionAccepted:
        stopped = self._apply_stop(identity, config_id, command, request_id, "revoke")
        reference = _credential_reference(stopped)
        job = self._runtime.enqueue_deletion(
            scope=identity.scope,
            configuration=stopped,
            credential=reference,
            reason_code=command.reason_code,
            idempotency_key=idempotency_key,
        )
        return ProviderDeletionAccepted(
            job_id=job.job_id,
            status_url=job.status_url,
            credential_state=stopped.credential_state,
            credential_usage_scope=stopped.credential_usage_scope,
        )

    def revoke_credential(
        self,
        *,
        identity: IdentityContext,
        config_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderDeletionAccepted:
        self._require_role(identity, frozenset({Role.TENANT_AI_ADMIN}), mfa=True)
        fingerprint = _fingerprint({"config_id": str(config_id)})
        with self._lock:
            return self._execute_idempotent(
                identity=identity,
                operation_id="revoke_ai_provider_credential",
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                expected_type=ProviderDeletionAccepted,
                command=lambda: self._revoke_credential(
                    identity, config_id, idempotency_key, request_id
                ),
            )

    def _revoke_credential(
        self,
        identity: IdentityContext,
        config_id: UUID,
        idempotency_key: str,
        request_id: str,
    ) -> ProviderDeletionAccepted:
        current = self._configuration(identity, config_id)
        reference = _credential_reference(current)
        if reference is None:
            raise BiaiceError("PROVIDER_CREDENTIAL_MISSING")
        require_audit(self._audit)
        now = self._clock.now()
        restricted = self._secret_store.restrict_to_deletion(
            scope=identity.scope,
            reference=reference,
        )
        updated = current.model_copy(
            update={
                "activation_state": ProviderActivationState.SUSPENDED,
                "credential_usage_scope": restricted.usage_scope,
                "state_version": current.state_version + 1,
                "updated_at": now,
                "updated_by": identity.subject_id,
                "gate_reason_codes": ("PROVIDER_CREDENTIAL_REVOCATION_PENDING",),
            }
        )
        self._configurations[config_id] = updated
        self._write_audit(
            identity=identity,
            operation_id="revoke_ai_provider_credential",
            object_type="provider_configuration",
            object_id=config_id,
            request_id=request_id,
            reason_code="PROVIDER_CREDENTIAL_REVOCATION_REQUESTED",
            outcome=updated.activation_state,
        )
        job = self._runtime.enqueue_deletion(
            scope=identity.scope,
            configuration=updated,
            credential=restricted,
            reason_code="PROVIDER_CREDENTIAL_REVOCATION_REQUESTED",
            idempotency_key=idempotency_key,
        )
        return ProviderDeletionAccepted(
            job_id=job.job_id,
            status_url=job.status_url,
            credential_state=updated.credential_state,
            credential_usage_scope=updated.credential_usage_scope,
        )

    def list_invocations(
        self,
        *,
        identity: IdentityContext,
        limit: int,
        cursor: str | None,
    ) -> ProviderInvocationPage:
        self._require_role(identity, TENANT_PROVIDER_READ_ROLES)
        with self._lock:
            items = tuple(
                sorted(
                    (
                        item
                        for item in self._invocations.values()
                        if item.tenant_id == identity.scope.tenant_id
                        and item.data_domain_id == identity.scope.data_domain_id
                    ),
                    key=lambda item: (item.started_at, str(item.invocation_id)),
                )
            )
        page_items, next_cursor, has_more = self._page(
            identity=identity,
            items=items,
            cursor=cursor,
            limit=limit,
            collection="provider-invocations",
            item_id=lambda item: item.invocation_id,
            created_at=lambda item: item.started_at,
        )
        return ProviderInvocationPage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_invocation(
        self, *, identity: IdentityContext, invocation_id: UUID
    ) -> ProviderInvocationRecord:
        self._require_role(identity, TENANT_PROVIDER_READ_ROLES)
        with self._lock:
            item = self._invocations.get(invocation_id)
        if (
            item is None
            or item.tenant_id != identity.scope.tenant_id
            or item.data_domain_id != identity.scope.data_domain_id
        ):
            raise BiaiceError("RESOURCE_NOT_FOUND")
        return item

    def _page(
        self,
        *,
        identity: IdentityContext,
        items: tuple[ResponseT, ...],
        cursor: str | None,
        limit: int,
        collection: str,
        item_id: Callable[[ResponseT], UUID],
        created_at: Callable[[ResponseT], Any],
    ) -> tuple[tuple[ResponseT, ...], str | None, bool]:
        start = 0
        if cursor is not None:
            decoded = self._cursor_codec.decode(cursor, scope=identity.scope)
            prefix = f"{collection}|"
            if not decoded.sort_key.startswith(prefix):
                raise BiaiceError("INVALID_CURSOR")
            timestamp = decoded.sort_key.removeprefix(prefix)
            marker = next(
                (
                    index
                    for index, item in enumerate(items)
                    if str(item_id(item)) == decoded.tie_breaker
                    and created_at(item).isoformat() == timestamp
                ),
                None,
            )
            if marker is None:
                raise BiaiceError("INVALID_CURSOR")
            start = marker + 1
        page_items = items[start : start + limit]
        has_more = start + len(page_items) < len(items)
        next_cursor = None
        if has_more and page_items:
            tail = page_items[-1]
            next_cursor = self._cursor_codec.encode(
                scope=identity.scope,
                sort_key=f"{collection}|{created_at(tail).isoformat()}",
                tie_breaker=str(item_id(tail)),
            )
        return page_items, next_cursor, has_more


def configure_provider_management(
    app: FastAPI,
    *,
    secret_store: SecretStorePort | None = None,
    runtime: ProviderRuntimePort | None = None,
    clock: Clock | None = None,
) -> ProviderManagementService:
    configured = app.state.settings.cursor_hmac_key
    raw_secret = (
        configured.get_secret_value().encode("utf-8")
        if configured is not None
        else secrets.token_bytes(32)
    )
    service = ProviderManagementService(
        audit_writer=app.state.audit_writer,
        gate_service=app.state.gate_service,
        privacy_service=app.state.fr12_market_resource_service,
        model_repository=app.state.model_lifecycle_repository,
        cursor_codec=CursorCodec(hashlib.sha256(raw_secret).digest()),
        secret_store=secret_store,
        runtime=runtime,
        clock=clock,
    )
    app.state.provider_management_service = service
    return service
