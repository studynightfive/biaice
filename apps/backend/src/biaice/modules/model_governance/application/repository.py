"""Thread-safe synthetic repository for the FR-13 lifecycle slice."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar, cast
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.core.errors import BiaiceError
from biaice.modules.model_governance.domain.models import (
    DeploymentState,
    ModelDeploymentVersion,
    ScopedVersion,
)

ResourceT = TypeVar("ResourceT", bound=ScopedVersion)


@dataclass(frozen=True, slots=True)
class ExternalModelReference:
    """Published Provider catalog evidence supplied by the owning integration."""

    tenant_id: UUID
    data_domain_id: UUID
    catalog_id: UUID
    catalog_hash: str
    provider_id: str
    provider_model_id: str
    provider_configuration_ids: frozenset[UUID]
    current: bool = True


@dataclass(frozen=True, slots=True)
class IdempotentResult:
    request_fingerprint: str
    response: ScopedVersion


def _scope_matches(item: ScopedVersion, scope: TenantScope) -> bool:
    return item.tenant_id == scope.tenant_id and item.data_domain_id == scope.data_domain_id


class InMemoryModelLifecycleRepository:
    """In-process M0 store; production persistence is a separate adapter."""

    def __init__(self) -> None:
        self._collections: dict[str, dict[UUID, ScopedVersion]] = {}
        self._history: dict[tuple[str, UUID], list[ScopedVersion]] = {}
        self._idempotency: dict[tuple[UUID, UUID, str, str], IdempotentResult] = {}
        self._external_models: dict[tuple[UUID, UUID, UUID, str, str], ExternalModelReference] = {}
        self._lock = threading.RLock()

    def register_external_model_reference(self, reference: ExternalModelReference) -> None:
        """Bind owner-published catalog/config evidence for tests or an adapter."""
        key = (
            reference.tenant_id,
            reference.data_domain_id,
            reference.catalog_id,
            reference.provider_id,
            reference.provider_model_id,
        )
        with self._lock:
            self._external_models[key] = reference

    def get_external_model_reference(
        self,
        *,
        scope: TenantScope,
        catalog_id: UUID,
        provider_id: str,
        provider_model_id: str,
    ) -> ExternalModelReference | None:
        with self._lock:
            return self._external_models.get(
                (
                    scope.tenant_id,
                    scope.data_domain_id,
                    catalog_id,
                    provider_id,
                    provider_model_id,
                )
            )

    def upsert(self, *, collection: str, resource_id: UUID, item: ScopedVersion) -> None:
        with self._lock:
            self._collections.setdefault(collection, {})[resource_id] = item
            self._history.setdefault((collection, resource_id), []).append(item)

    def get(
        self,
        *,
        scope: TenantScope,
        collection: str,
        resource_id: UUID,
        expected_type: type[ResourceT],
    ) -> ResourceT | None:
        with self._lock:
            item = self._collections.get(collection, {}).get(resource_id)
        if item is None or not isinstance(item, expected_type) or not _scope_matches(item, scope):
            return None
        return item

    def list(
        self,
        *,
        scope: TenantScope,
        collection: str,
        expected_type: type[ResourceT],
    ) -> tuple[ResourceT, ...]:
        with self._lock:
            items = [
                item
                for item in self._collections.get(collection, {}).values()
                if isinstance(item, expected_type) and _scope_matches(item, scope)
            ]
        items.sort(key=lambda item: (item.created_at, str(item.version_id)))
        return tuple(cast(ResourceT, item) for item in items)

    def find_active_deployment(
        self, *, scope: TenantScope, deployment_slot: str
    ) -> ModelDeploymentVersion | None:
        deployments = self.list(
            scope=scope,
            collection="model_deployments",
            expected_type=ModelDeploymentVersion,
        )
        return next(
            (
                item
                for item in reversed(deployments)
                if item.deployment_slot == deployment_slot and item.state is DeploymentState.ACTIVE
            ),
            None,
        )

    def execute_idempotent(
        self,
        *,
        scope: TenantScope,
        operation_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        expected_type: type[ResourceT],
        command: Callable[[], ResourceT],
    ) -> ResourceT:
        key = (
            scope.tenant_id,
            scope.data_domain_id,
            operation_id,
            idempotency_key,
        )
        with self._lock:
            stored = self._idempotency.get(key)
            if stored is not None:
                if stored.request_fingerprint != request_fingerprint:
                    raise BiaiceError(
                        "IDEMPOTENCY_CONFLICT",
                        detail="The idempotency key was already used with a different request.",
                    )
                if not isinstance(stored.response, expected_type):
                    raise BiaiceError("INTERNAL_ERROR", detail="Stored response type mismatch.")
                return stored.response
            response = command()
            self._idempotency[key] = IdempotentResult(
                request_fingerprint=request_fingerprint,
                response=response,
            )
            return response
