"""In-memory FR-03 repository. SQLAlchemy adapter is a later member-1 lock-file PR."""

from __future__ import annotations

import threading
from typing import Protocol
from uuid import UUID

from biaice.core.auth import TenantScope
from biaice.modules.evidence.domain.models import (
    CompanyEvidence,
    CompanyResponseProfile,
    ConditionRequirement,
    EvidenceMatch,
    PrecheckAssessment,
    Requirement,
)


def _scope_matches(
    *,
    tenant_id: UUID,
    data_domain_id: UUID,
    project_id: UUID | None,
    decision_unit_id: UUID,
    scope: TenantScope,
) -> bool:
    if tenant_id != scope.tenant_id or data_domain_id != scope.data_domain_id:
        return False
    if (
        project_id is not None
        and not scope.all_projects
        and project_id not in scope.project_ids
    ):
        return False
    if (
        not scope.all_decision_units
        and decision_unit_id not in scope.decision_unit_ids
    ):
        return False
    return True


class EvidenceRepository(Protocol):
    def upsert_requirement(self, item: Requirement) -> None: ...
    def get_requirement(self, *, scope: TenantScope, requirement_id: UUID) -> Requirement | None: ...
    def list_requirements(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[Requirement, ...]: ...
    def upsert_evidence(self, item: CompanyEvidence) -> None: ...
    def get_evidence(self, *, scope: TenantScope, evidence_id: UUID) -> CompanyEvidence | None: ...
    def list_evidence(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[CompanyEvidence, ...]: ...
    def upsert_match(self, item: EvidenceMatch) -> None: ...
    def get_match(self, *, scope: TenantScope, match_id: UUID) -> EvidenceMatch | None: ...
    def list_matches(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[EvidenceMatch, ...]: ...
    def upsert_profile(self, item: CompanyResponseProfile) -> None: ...
    def get_profile(self, *, scope: TenantScope, profile_id: UUID) -> CompanyResponseProfile | None: ...
    def list_profiles(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[CompanyResponseProfile, ...]: ...
    def upsert_precheck(self, item: PrecheckAssessment) -> None: ...
    def get_precheck(self, *, scope: TenantScope, precheck_id: UUID) -> PrecheckAssessment | None: ...
    def list_prechecks(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[PrecheckAssessment, ...]: ...
    def upsert_condition(self, item: ConditionRequirement) -> None: ...
    def get_condition(self, *, scope: TenantScope, condition_id: UUID) -> ConditionRequirement | None: ...
    def list_conditions(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[ConditionRequirement, ...]: ...


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self._requirements: dict[UUID, Requirement] = {}
        self._evidence: dict[UUID, CompanyEvidence] = {}
        self._matches: dict[UUID, EvidenceMatch] = {}
        self._profiles: dict[UUID, CompanyResponseProfile] = {}
        self._prechecks: dict[UUID, PrecheckAssessment] = {}
        self._conditions: dict[UUID, ConditionRequirement] = {}
        self._lock = threading.Lock()

    def upsert_requirement(self, item: Requirement) -> None:
        with self._lock:
            self._requirements[item.requirement_id] = item

    def get_requirement(self, *, scope: TenantScope, requirement_id: UUID) -> Requirement | None:
        with self._lock:
            item = self._requirements.get(requirement_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_requirements(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[Requirement, ...]:
        with self._lock:
            items = [
                item
                for item in self._requirements.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.requirement_id)))
        return tuple(items)

    def upsert_evidence(self, item: CompanyEvidence) -> None:
        with self._lock:
            self._evidence[item.evidence_id] = item

    def get_evidence(self, *, scope: TenantScope, evidence_id: UUID) -> CompanyEvidence | None:
        with self._lock:
            item = self._evidence.get(evidence_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_evidence(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[CompanyEvidence, ...]:
        with self._lock:
            items = [
                item
                for item in self._evidence.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.evidence_id)))
        return tuple(items)

    def upsert_match(self, item: EvidenceMatch) -> None:
        with self._lock:
            self._matches[item.match_id] = item

    def get_match(self, *, scope: TenantScope, match_id: UUID) -> EvidenceMatch | None:
        with self._lock:
            item = self._matches.get(match_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_matches(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[EvidenceMatch, ...]:
        with self._lock:
            items = [
                item
                for item in self._matches.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.match_id)))
        return tuple(items)

    def upsert_profile(self, item: CompanyResponseProfile) -> None:
        with self._lock:
            self._profiles[item.profile_id] = item

    def get_profile(self, *, scope: TenantScope, profile_id: UUID) -> CompanyResponseProfile | None:
        with self._lock:
            item = self._profiles.get(profile_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_profiles(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[CompanyResponseProfile, ...]:
        with self._lock:
            items = [
                item
                for item in self._profiles.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.profile_id)))
        return tuple(items)

    def upsert_precheck(self, item: PrecheckAssessment) -> None:
        with self._lock:
            self._prechecks[item.precheck_id] = item

    def get_precheck(self, *, scope: TenantScope, precheck_id: UUID) -> PrecheckAssessment | None:
        with self._lock:
            item = self._prechecks.get(precheck_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_prechecks(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[PrecheckAssessment, ...]:
        with self._lock:
            items = [
                item
                for item in self._prechecks.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.precheck_id)))
        return tuple(items)

    def upsert_condition(self, item: ConditionRequirement) -> None:
        with self._lock:
            self._conditions[item.condition_id] = item

    def get_condition(self, *, scope: TenantScope, condition_id: UUID) -> ConditionRequirement | None:
        with self._lock:
            item = self._conditions.get(condition_id)
        if item is None or not _scope_matches(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            project_id=item.project_id,
            decision_unit_id=item.decision_unit_id,
            scope=scope,
        ):
            return None
        return item

    def list_conditions(self, *, scope: TenantScope, decision_unit_id: UUID) -> tuple[ConditionRequirement, ...]:
        with self._lock:
            items = [
                item
                for item in self._conditions.values()
                if _scope_matches(
                    tenant_id=item.tenant_id,
                    data_domain_id=item.data_domain_id,
                    project_id=item.project_id,
                    decision_unit_id=item.decision_unit_id,
                    scope=scope,
                )
                and item.decision_unit_id == decision_unit_id
            ]
        items.sort(key=lambda item: (item.created_at, str(item.condition_id)))
        return tuple(items)
