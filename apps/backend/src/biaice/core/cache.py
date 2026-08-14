"""Tenant-safe Redis cache/rate-limit key construction."""

from __future__ import annotations

import re
from uuid import UUID

from biaice.core.auth import TenantScope

SAFE_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")


def scoped_cache_key(
    scope: TenantScope,
    namespace: str,
    resource_id: str | UUID,
    *,
    project_id: UUID | None = None,
    decision_unit_id: UUID | None = None,
) -> str:
    if not SAFE_SEGMENT.fullmatch(namespace):
        raise ValueError("cache namespace must be a fixed safe segment")
    scope.assert_allows(
        tenant_id=scope.tenant_id,
        data_domain_id=scope.data_domain_id,
        project_id=project_id,
        decision_unit_id=decision_unit_id,
    )
    project = str(project_id) if project_id else "_tenant"
    unit = str(decision_unit_id) if decision_unit_id else "_project"
    return f"biaice:{scope.tenant_id}:{scope.data_domain_id}:{project}:{unit}:{namespace}:{resource_id}"
