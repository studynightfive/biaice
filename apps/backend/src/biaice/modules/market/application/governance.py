"""FR-05 source review, deduplication and market-readiness policy."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, TypeVar, cast
from uuid import UUID, uuid4

from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext, Role
from biaice.core.clock import Clock, SystemClock
from biaice.core.errors import BiaiceError
from biaice.core.http import assert_etag, compute_etag
from biaice.modules.market.domain.models import (
    Competitor,
    CompetitorProfile,
    CompetitorSource,
    JointParticipationDistribution,
    MarketPriorVersion,
    MarketReadiness,
    PublicationState,
    SourceReviewState,
    SubjectDeduplicationRun,
    UnknownEntrantProfileVersion,
)


def _not_found(detail: str) -> BiaiceError:
    return BiaiceError("RESOURCE_NOT_FOUND", detail=detail)


def _state_conflict(detail: str) -> BiaiceError:
    return BiaiceError("IDEMPOTENCY_CONFLICT", detail=detail)


def _canonical_subject_key(value: str) -> str:
    normalized = "".join(value.casefold().split())
    if len(normalized) < 3:
        raise BiaiceError(
            "REQUEST_VALIDATION_FAILED",
            detail="Subject keys must contain at least three non-whitespace characters.",
        )
    return normalized


ResultT = TypeVar("ResultT")


class MarketGovernanceService:
    """Thread-safe policy service used until the PostgreSQL adapter is bound."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        audit_writer: AuditWriter | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._audit_writer = audit_writer
        self._competitors: dict[UUID, Competitor] = {}
        self._subject_index: dict[tuple[UUID, UUID, str], UUID] = {}
        self._sources: dict[UUID, CompetitorSource] = {}
        self._profiles: dict[UUID, CompetitorProfile] = {}
        self._priors: dict[UUID, MarketPriorVersion] = {}
        self._unknown_profiles: dict[UUID, UnknownEntrantProfileVersion] = {}
        self._deduplication_runs: dict[UUID, SubjectDeduplicationRun] = {}
        self._lock = threading.RLock()
        # ponytail: process-local replay is enough for this in-memory adapter;
        # replace it with the PostgreSQL idempotency port when persistence lands.
        self._idempotency_results: dict[tuple[UUID, UUID, str], tuple[str, object]] = {}

    @property
    def clock(self) -> Clock:
        return self._clock

    def execute_idempotent(
        self,
        *,
        identity: IdentityContext,
        idempotency_key: str,
        fingerprint: str,
        command: Callable[[], ResultT],
    ) -> ResultT:
        key = (
            identity.scope.tenant_id,
            identity.scope.data_domain_id,
            idempotency_key,
        )
        with self._lock:
            existing = self._idempotency_results.get(key)
            if existing is not None:
                previous_fingerprint, previous_result = existing
                if previous_fingerprint != fingerprint:
                    raise BiaiceError("IDEMPOTENCY_CONFLICT")
                return cast(ResultT, previous_result)
            result = command()
            self._idempotency_results[key] = (fingerprint, result)
            return result

    def _audit(
        self,
        *,
        identity: IdentityContext,
        action: str,
        object_type: str,
        object_id: UUID,
        object_version_id: UUID | None,
        request_id: str | None,
        reason_code: str,
        outcome: str,
    ) -> None:
        if self._audit_writer is None:
            return
        require_audit(self._audit_writer)
        if request_id is None:
            raise BiaiceError("INTERNAL_ERROR", detail="Audited writes require a request ID.")
        self._audit_writer.write(
            identity=identity,
            action=action,
            object_type=object_type,
            object_id=object_id,
            object_version_id=object_version_id,
            request_id=request_id,
            reason_code=reason_code,
            outcome=outcome,
        )

    def add_competitor(
        self,
        *,
        identity: IdentityContext,
        item: Competitor,
        request_id: str | None = None,
    ) -> Competitor:
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
        )
        key = (item.tenant_id, item.data_domain_id, item.canonical_subject_key)
        with self._lock:
            existing = self._subject_index.get(key)
            if existing is not None and existing != item.competitor_id:
                raise BiaiceError(
                    "IDEMPOTENCY_CONFLICT",
                    detail="The canonical subject is already registered as a named competitor.",
                )
            self._competitors[item.competitor_id] = item
            self._subject_index[key] = item.competitor_id
            quarantined_unknown_profiles = []
            for profile_id, profile in self._unknown_profiles.items():
                if (
                    profile.tenant_id != item.tenant_id
                    or profile.data_domain_id != item.data_domain_id
                    or item.canonical_subject_key in profile.excluded_subject_keys
                    or profile.state != PublicationState.PUBLISHED
                ):
                    continue
                quarantined = profile.model_copy(
                    update={
                        "version_id": uuid4(),
                        "state": PublicationState.QUARANTINED,
                        "actor_id": identity.subject_id,
                        "updated_at": item.updated_at,
                    }
                )
                self._unknown_profiles[profile_id] = quarantined
                quarantined_unknown_profiles.append(quarantined)
        self._audit(
            identity=identity,
            action="market.competitor.create",
            object_type="Competitor",
            object_id=item.competitor_id,
            object_version_id=item.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_CREATED",
            outcome="DRAFT",
        )
        for profile in quarantined_unknown_profiles:
            self._audit(
                identity=identity,
                action="market.unknown_entrant_profile.quarantine",
                object_type="UnknownEntrantProfileVersion",
                object_id=profile.profile_id,
                object_version_id=profile.version_id,
                request_id=request_id,
                reason_code="NAMED_COMPETITOR_CREATED",
                outcome=profile.state.value,
            )
        return item

    def list_competitors(self, *, identity: IdentityContext) -> tuple[Competitor, ...]:
        with self._lock:
            items = [
                item
                for item in self._competitors.values()
                if item.tenant_id == identity.scope.tenant_id
                and item.data_domain_id == identity.scope.data_domain_id
            ]
        return tuple(sorted(items, key=lambda item: item.created_at))

    def get_competitor(self, *, identity: IdentityContext, competitor_id: UUID) -> Competitor:
        with self._lock:
            item = self._competitors.get(competitor_id)
        if item is None:
            raise _not_found("Competitor was not found.")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
        )
        return item

    def update_competitor_draft(
        self,
        *,
        identity: IdentityContext,
        competitor_id: UUID,
        if_match: str,
        legal_name: str | None,
        canonical_subject_key: str | None,
        aliases: tuple[str, ...] | None,
        request_id: str,
    ) -> Competitor:
        with self._lock:
            item = self.get_competitor(identity=identity, competitor_id=competitor_id)
            if item.archived_at is not None:
                raise _state_conflict("Archived competitors cannot be edited.")
            assert_etag(compute_etag(item.model_dump(mode="json")), if_match)
            next_subject_key = (
                _canonical_subject_key(canonical_subject_key)
                if canonical_subject_key is not None
                else item.canonical_subject_key
            )
            next_index_key = (item.tenant_id, item.data_domain_id, next_subject_key)
            existing = self._subject_index.get(next_index_key)
            if existing is not None and existing != competitor_id:
                raise BiaiceError(
                    "IDEMPOTENCY_CONFLICT",
                    detail="The canonical subject is already registered as a named competitor.",
                )
            updated = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "legal_name": legal_name if legal_name is not None else item.legal_name,
                    "canonical_subject_key": next_subject_key,
                    "aliases": aliases if aliases is not None else item.aliases,
                    "actor_id": identity.subject_id,
                    "updated_at": self._clock.now(),
                }
            )
            if next_subject_key != item.canonical_subject_key:
                del self._subject_index[
                    (item.tenant_id, item.data_domain_id, item.canonical_subject_key)
                ]
            self._subject_index[next_index_key] = competitor_id
            self._competitors[competitor_id] = updated
            quarantined_unknown_profiles = []
            if next_subject_key != item.canonical_subject_key:
                for profile_id, profile in self._unknown_profiles.items():
                    if (
                        profile.tenant_id != item.tenant_id
                        or profile.data_domain_id != item.data_domain_id
                        or next_subject_key in profile.excluded_subject_keys
                        or profile.state != PublicationState.PUBLISHED
                    ):
                        continue
                    quarantined = profile.model_copy(
                        update={
                            "version_id": uuid4(),
                            "state": PublicationState.QUARANTINED,
                            "actor_id": identity.subject_id,
                            "updated_at": updated.updated_at,
                        }
                    )
                    self._unknown_profiles[profile_id] = quarantined
                    quarantined_unknown_profiles.append(quarantined)
        self._audit(
            identity=identity,
            action="market.competitor.update_draft",
            object_type="Competitor",
            object_id=updated.competitor_id,
            object_version_id=updated.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_DRAFT_UPDATED",
            outcome="DRAFT",
        )
        for profile in quarantined_unknown_profiles:
            self._audit(
                identity=identity,
                action="market.unknown_entrant_profile.quarantine",
                object_type="UnknownEntrantProfileVersion",
                object_id=profile.profile_id,
                object_version_id=profile.version_id,
                request_id=request_id,
                reason_code="NAMED_COMPETITOR_SUBJECT_CHANGED",
                outcome=profile.state.value,
            )
        return updated

    def archive_competitor(
        self,
        *,
        identity: IdentityContext,
        competitor_id: UUID,
        reason: str,
        request_id: str,
    ) -> Competitor:
        with self._lock:
            item = self.get_competitor(identity=identity, competitor_id=competitor_id)
            if item.archived_at is not None:
                raise _state_conflict("Competitor is already archived.")
            archived = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "actor_id": identity.subject_id,
                    "updated_at": self._clock.now(),
                    "archived_at": self._clock.now(),
                    "archive_reason": reason.strip(),
                }
            )
            self._competitors[competitor_id] = archived
        self._audit(
            identity=identity,
            action="market.competitor.archive",
            object_type="Competitor",
            object_id=archived.competitor_id,
            object_version_id=archived.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_ARCHIVED",
            outcome="ARCHIVED",
        )
        return archived

    def add_source(
        self,
        *,
        identity: IdentityContext,
        item: CompetitorSource,
        request_id: str | None = None,
    ) -> CompetitorSource:
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
        )
        with self._lock:
            if item.competitor_id is not None:
                competitor = self._competitors.get(item.competitor_id)
                if (
                    competitor is None
                    or competitor.tenant_id != item.tenant_id
                    or competitor.data_domain_id != item.data_domain_id
                    or competitor.archived_at is not None
                ):
                    raise _not_found("Competitor source target is not visible in scope.")
            if item.retention_expires_at <= self._clock.now():
                raise BiaiceError(
                    "RETENTION_EXPIRED",
                    detail="Competitor source retention must extend beyond creation time.",
                )
            self._sources[item.source_id] = item
        self._audit(
            identity=identity,
            action="market.competitor_source.create",
            object_type="CompetitorSource",
            object_id=item.source_id,
            object_version_id=item.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_SOURCE_CREATED",
            outcome=item.review_state.value,
        )
        return item

    def list_sources(
        self, *, identity: IdentityContext, competitor_id: UUID
    ) -> tuple[CompetitorSource, ...]:
        self.get_competitor(identity=identity, competitor_id=competitor_id)
        with self._lock:
            items = [
                item
                for item in self._sources.values()
                if item.competitor_id == competitor_id
                and item.tenant_id == identity.scope.tenant_id
                and item.data_domain_id == identity.scope.data_domain_id
            ]
        return tuple(sorted(items, key=lambda item: item.created_at))

    def get_source(self, *, identity: IdentityContext, source_id: UUID) -> CompetitorSource:
        with self._lock:
            item = self._sources.get(source_id)
        if item is None:
            raise _not_found("Competitor source was not found.")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
        )
        return item

    def review_source(
        self,
        *,
        identity: IdentityContext,
        source_id: UUID,
        resolved_competitor_id: UUID,
        reviewed_at: datetime,
        request_id: str | None = None,
    ) -> CompetitorSource:
        if not ({Role.PRIVACY_OFFICER, Role.LEGAL_PRIVACY} & identity.roles):
            raise BiaiceError("PERMISSION_DENIED")
        with self._lock:
            item = self._sources.get(source_id)
            competitor = self._competitors.get(resolved_competitor_id)
            if item is None or competitor is None:
                raise _not_found("Competitor source or resolved subject was not found.")
            identity.scope.assert_allows(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
            )
            if (
                competitor.tenant_id != item.tenant_id
                or competitor.data_domain_id != item.data_domain_id
            ):
                raise _not_found("Resolved competitor is not visible in source scope.")
            if item.retention_expires_at <= reviewed_at:
                raise BiaiceError(
                    "RETENTION_EXPIRED",
                    detail="Expired competitor material cannot be approved for formal use.",
                )
            if item.review_state != SourceReviewState.DRAFT:
                raise _state_conflict("Only draft competitor sources can be reviewed.")
            reviewed = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "competitor_id": competitor.competitor_id,
                    "subject_resolved": True,
                    "review_state": SourceReviewState.REVIEWED,
                    "reviewed_by": identity.subject_id,
                    "reviewed_at": reviewed_at,
                    "quarantine_reason": None,
                    "actor_id": identity.subject_id,
                    "updated_at": reviewed_at,
                }
            )
            self._sources[source_id] = reviewed
        self._audit(
            identity=identity,
            action="market.competitor_source.review",
            object_type="CompetitorSource",
            object_id=reviewed.source_id,
            object_version_id=reviewed.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_SOURCE_REVIEWED",
            outcome=reviewed.review_state.value,
        )
        return reviewed

    def quarantine_source(
        self,
        *,
        identity: IdentityContext,
        source_id: UUID,
        reason: str,
        request_id: str | None = None,
    ) -> CompetitorSource:
        if not ({Role.PRIVACY_OFFICER, Role.LEGAL_PRIVACY} & identity.roles):
            raise BiaiceError("PERMISSION_DENIED")
        if not reason.strip():
            raise BiaiceError(
                "REQUEST_VALIDATION_FAILED", detail="A quarantine reason is required."
            )
        with self._lock:
            item = self._sources.get(source_id)
            if item is None:
                raise _not_found("Competitor source was not found.")
            identity.scope.assert_allows(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
            )
            if item.review_state == SourceReviewState.QUARANTINED:
                raise _state_conflict("Competitor source is already quarantined.")
            now = self._clock.now()
            quarantined = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "review_state": SourceReviewState.QUARANTINED,
                    "quarantine_reason": reason.strip(),
                    "actor_id": identity.subject_id,
                    "updated_at": now,
                }
            )
            self._sources[source_id] = quarantined
            quarantined_profiles = []
            for profile_id, profile in self._profiles.items():
                if (
                    source_id not in profile.source_ids
                    or profile.state == PublicationState.QUARANTINED
                ):
                    continue
                quarantined_profile = profile.model_copy(
                    update={
                        "version_id": uuid4(),
                        "state": PublicationState.QUARANTINED,
                        "actor_id": identity.subject_id,
                        "updated_at": now,
                    }
                )
                self._profiles[profile_id] = quarantined_profile
                quarantined_profiles.append(quarantined_profile)
        self._audit(
            identity=identity,
            action="market.competitor_source.quarantine",
            object_type="CompetitorSource",
            object_id=quarantined.source_id,
            object_version_id=quarantined.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_SOURCE_QUARANTINED",
            outcome=quarantined.review_state.value,
        )
        for profile in quarantined_profiles:
            self._audit(
                identity=identity,
                action="market.competitor_profile.quarantine",
                object_type="CompetitorProfile",
                object_id=profile.profile_id,
                object_version_id=profile.version_id,
                request_id=request_id,
                reason_code="COMPETITOR_SOURCE_QUARANTINED",
                outcome=profile.state.value,
            )
        return quarantined

    def add_profile(
        self,
        *,
        identity: IdentityContext,
        item: CompetitorProfile,
        request_id: str | None = None,
    ) -> CompetitorProfile:
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
        )
        with self._lock:
            competitor = self._competitors.get(item.competitor_id)
            if (
                competitor is None
                or competitor.tenant_id != item.tenant_id
                or competitor.data_domain_id != item.data_domain_id
                or competitor.archived_at is not None
            ):
                raise _not_found("Competitor profile target is not visible in scope.")
            sources = [self._sources.get(source_id) for source_id in item.source_ids]
            now = self._clock.now()
            if any(
                source is None
                or source.review_state != SourceReviewState.REVIEWED
                or not source.subject_resolved
                or source.retention_expires_at <= now
                for source in sources
            ):
                raise BiaiceError(
                    "GATE_NOT_CURRENT",
                    detail="Every profile source must be reviewed, resolved and within retention.",
                )
            if any(source.competitor_id != item.competitor_id for source in sources if source):
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Profile sources must resolve to the same competitor.",
                )
            self._profiles[item.profile_id] = item
        self._audit(
            identity=identity,
            action="market.competitor_profile.build",
            object_type="CompetitorProfile",
            object_id=item.profile_id,
            object_version_id=item.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_PROFILE_BUILT",
            outcome=item.state.value,
        )
        return item

    def list_profiles(
        self, *, identity: IdentityContext, competitor_id: UUID
    ) -> tuple[CompetitorProfile, ...]:
        self.get_competitor(identity=identity, competitor_id=competitor_id)
        with self._lock:
            items = [
                item
                for item in self._profiles.values()
                if item.competitor_id == competitor_id
                and item.tenant_id == identity.scope.tenant_id
                and item.data_domain_id == identity.scope.data_domain_id
            ]
        return tuple(sorted(items, key=lambda item: item.created_at))

    def get_profile(self, *, identity: IdentityContext, profile_id: UUID) -> CompetitorProfile:
        with self._lock:
            item = self._profiles.get(profile_id)
        if item is None:
            raise _not_found("Competitor profile was not found.")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
        )
        return item

    def publish_profile(
        self,
        *,
        identity: IdentityContext,
        profile_id: UUID,
        published_at: datetime,
        request_id: str | None = None,
    ) -> CompetitorProfile:
        with self._lock:
            item = self._profiles.get(profile_id)
            if item is None:
                raise _not_found("Competitor profile was not found.")
            identity.scope.assert_allows(
                tenant_id=item.tenant_id,
                data_domain_id=item.data_domain_id,
            )
            if item.state != PublicationState.DRAFT:
                raise _state_conflict("Only draft competitor profiles can be published.")
            sources = [self._sources.get(source_id) for source_id in item.source_ids]
            if any(
                source is None
                or source.review_state != SourceReviewState.REVIEWED
                or not source.subject_resolved
                or source.retention_expires_at <= published_at
                for source in sources
            ):
                raise BiaiceError(
                    "GATE_NOT_CURRENT",
                    detail="A profile source is quarantined, expired or not reviewed.",
                )
            published = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": PublicationState.PUBLISHED,
                    "actor_id": identity.subject_id,
                    "updated_at": published_at,
                    "published_at": published_at,
                }
            )
            self._profiles[profile_id] = published
        self._audit(
            identity=identity,
            action="market.competitor_profile.publish",
            object_type="CompetitorProfile",
            object_id=published.profile_id,
            object_version_id=published.version_id,
            request_id=request_id,
            reason_code="COMPETITOR_PROFILE_PUBLISHED",
            outcome=published.state.value,
        )
        return published

    def add_market_prior(
        self,
        *,
        identity: IdentityContext,
        item: MarketPriorVersion,
        request_id: str | None = None,
    ) -> MarketPriorVersion:
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        if item.expires_at <= self._clock.now():
            raise BiaiceError(
                "RETENTION_EXPIRED",
                detail="Market prior validity must extend beyond creation time.",
            )
        with self._lock:
            self._priors[item.market_prior_id] = item
        self._audit(
            identity=identity,
            action="market.market_prior.create",
            object_type="MarketPriorVersion",
            object_id=item.market_prior_id,
            object_version_id=item.version_id,
            request_id=request_id,
            reason_code="MARKET_PRIOR_CREATED",
            outcome=item.state.value,
        )
        return item

    def list_market_priors(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[MarketPriorVersion, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        with self._lock:
            items = [
                item
                for item in self._priors.values()
                if item.decision_unit_id == decision_unit_id
                and item.tenant_id == identity.scope.tenant_id
                and item.data_domain_id == identity.scope.data_domain_id
            ]
        return tuple(sorted(items, key=lambda item: item.created_at))

    def get_market_prior(
        self, *, identity: IdentityContext, market_prior_id: UUID
    ) -> MarketPriorVersion:
        with self._lock:
            item = self._priors.get(market_prior_id)
        if item is None:
            raise _not_found("Market prior was not found.")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        return item

    def review_market_prior(
        self,
        *,
        identity: IdentityContext,
        market_prior_id: UUID,
        request_id: str,
    ) -> MarketPriorVersion:
        if not ({Role.PRIVACY_OFFICER, Role.LEGAL_PRIVACY} & identity.roles):
            raise BiaiceError("PERMISSION_DENIED")
        with self._lock:
            item = self.get_market_prior(
                identity=identity,
                market_prior_id=market_prior_id,
            )
            if item.state != PublicationState.DRAFT:
                raise _state_conflict("Only draft market priors can be reviewed.")
            now = self._clock.now()
            reviewed = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": PublicationState.REVIEWED,
                    "reviewed_by": identity.subject_id,
                    "reviewed_at": now,
                    "actor_id": identity.subject_id,
                    "updated_at": now,
                }
            )
            self._priors[market_prior_id] = reviewed
        self._audit(
            identity=identity,
            action="market.market_prior.review",
            object_type="MarketPriorVersion",
            object_id=reviewed.market_prior_id,
            object_version_id=reviewed.version_id,
            request_id=request_id,
            reason_code="MARKET_PRIOR_REVIEWED",
            outcome=reviewed.state.value,
        )
        return reviewed

    def publish_market_prior(
        self,
        *,
        identity: IdentityContext,
        market_prior_id: UUID,
        request_id: str,
    ) -> MarketPriorVersion:
        with self._lock:
            item = self.get_market_prior(
                identity=identity,
                market_prior_id=market_prior_id,
            )
            if item.state != PublicationState.REVIEWED:
                raise _state_conflict("Only reviewed market priors can be published.")
            now = self._clock.now()
            if item.expires_at <= now:
                raise BiaiceError("RETENTION_EXPIRED")
            published = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": PublicationState.PUBLISHED,
                    "actor_id": identity.subject_id,
                    "updated_at": now,
                    "published_at": now,
                }
            )
            self._priors[market_prior_id] = published
        self._audit(
            identity=identity,
            action="market.market_prior.publish",
            object_type="MarketPriorVersion",
            object_id=published.market_prior_id,
            object_version_id=published.version_id,
            request_id=request_id,
            reason_code="MARKET_PRIOR_PUBLISHED",
            outcome=published.state.value,
        )
        return published

    def add_unknown_profile(
        self,
        *,
        identity: IdentityContext,
        item: UnknownEntrantProfileVersion,
        request_id: str | None = None,
    ) -> UnknownEntrantProfileVersion:
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        if item.expires_at <= self._clock.now():
            raise BiaiceError(
                "RETENTION_EXPIRED",
                detail="Unknown entrant profile validity must extend beyond creation time.",
            )
        with self._lock:
            named_subjects = {
                competitor.canonical_subject_key
                for competitor in self._competitors.values()
                if competitor.tenant_id == item.tenant_id
                and competitor.data_domain_id == item.data_domain_id
                and competitor.archived_at is None
            }
            if not named_subjects.issubset(item.excluded_subject_keys):
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Unknown entrants must explicitly exclude every named competitor subject.",
                )
            self._unknown_profiles[item.profile_id] = item
        self._audit(
            identity=identity,
            action="market.unknown_entrant_profile.create",
            object_type="UnknownEntrantProfileVersion",
            object_id=item.profile_id,
            object_version_id=item.version_id,
            request_id=request_id,
            reason_code="UNKNOWN_ENTRANT_PROFILE_CREATED",
            outcome=item.state.value,
        )
        return item

    def list_unknown_profiles(
        self, *, identity: IdentityContext, decision_unit_id: UUID
    ) -> tuple[UnknownEntrantProfileVersion, ...]:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        with self._lock:
            items = [
                item
                for item in self._unknown_profiles.values()
                if item.decision_unit_id == decision_unit_id
                and item.tenant_id == identity.scope.tenant_id
                and item.data_domain_id == identity.scope.data_domain_id
            ]
        return tuple(sorted(items, key=lambda item: item.created_at))

    def get_unknown_profile(
        self, *, identity: IdentityContext, profile_id: UUID
    ) -> UnknownEntrantProfileVersion:
        with self._lock:
            item = self._unknown_profiles.get(profile_id)
        if item is None:
            raise _not_found("Unknown entrant profile was not found.")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        return item

    def publish_unknown_profile(
        self,
        *,
        identity: IdentityContext,
        profile_id: UUID,
        request_id: str,
    ) -> UnknownEntrantProfileVersion:
        with self._lock:
            item = self.get_unknown_profile(identity=identity, profile_id=profile_id)
            if item.state != PublicationState.DRAFT:
                raise _state_conflict("Only draft unknown entrant profiles can be published.")
            now = self._clock.now()
            if item.expires_at <= now:
                raise BiaiceError("RETENTION_EXPIRED")
            named_subjects = {
                competitor.canonical_subject_key
                for competitor in self._competitors.values()
                if competitor.tenant_id == item.tenant_id
                and competitor.data_domain_id == item.data_domain_id
                and competitor.archived_at is None
            }
            if not named_subjects.issubset(item.excluded_subject_keys):
                raise BiaiceError(
                    "REQUEST_VALIDATION_FAILED",
                    detail="Unknown entrants must exclude every current named competitor subject.",
                )
            published = item.model_copy(
                update={
                    "version_id": uuid4(),
                    "state": PublicationState.PUBLISHED,
                    "actor_id": identity.subject_id,
                    "updated_at": now,
                    "published_at": now,
                }
            )
            self._unknown_profiles[profile_id] = published
        self._audit(
            identity=identity,
            action="market.unknown_entrant_profile.publish",
            object_type="UnknownEntrantProfileVersion",
            object_id=published.profile_id,
            object_version_id=published.version_id,
            request_id=request_id,
            reason_code="UNKNOWN_ENTRANT_PROFILE_PUBLISHED",
            outcome=published.state.value,
        )
        return published

    def create_subject_deduplication_run(
        self,
        *,
        identity: IdentityContext,
        decision_unit_id: UUID,
        subject_keys: tuple[str, ...],
        request_id: str,
    ) -> SubjectDeduplicationRun:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        grouped: dict[str, list[str]] = {}
        for subject_key in subject_keys:
            canonical = _canonical_subject_key(subject_key)
            grouped.setdefault(canonical, []).append(subject_key)
        with self._lock:
            named_subjects = {
                competitor.canonical_subject_key
                for competitor in self._competitors.values()
                if competitor.tenant_id == identity.scope.tenant_id
                and competitor.data_domain_id == identity.scope.data_domain_id
                and competitor.archived_at is None
            }
            now = self._clock.now()
            item = SubjectDeduplicationRun(
                run_id=uuid4(),
                decision_unit_id=decision_unit_id,
                tenant_id=identity.scope.tenant_id,
                data_domain_id=identity.scope.data_domain_id,
                input_subject_keys=subject_keys,
                canonical_subject_keys=tuple(grouped),
                duplicate_groups={
                    key: tuple(values) for key, values in grouped.items() if len(values) > 1
                },
                named_subject_matches=frozenset(grouped).intersection(named_subjects),
                actor_id=identity.subject_id,
                created_at=now,
                completed_at=now,
            )
            self._deduplication_runs[item.run_id] = item
        self._audit(
            identity=identity,
            action="market.subject_deduplication_run.create",
            object_type="SubjectDeduplicationRun",
            object_id=item.run_id,
            object_version_id=None,
            request_id=request_id,
            reason_code="SUBJECT_DEDUPLICATION_SUCCEEDED",
            outcome=item.state.value,
        )
        return item

    def get_subject_deduplication_run(
        self, *, identity: IdentityContext, run_id: UUID
    ) -> SubjectDeduplicationRun:
        with self._lock:
            item = self._deduplication_runs.get(run_id)
        if item is None:
            raise _not_found("Subject deduplication run was not found.")
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        return item

    def readiness(
        self, *, identity: IdentityContext, decision_unit_id: UUID, at: datetime | None = None
    ) -> MarketReadiness:
        identity.scope.assert_allows(
            tenant_id=identity.scope.tenant_id,
            data_domain_id=identity.scope.data_domain_id,
            decision_unit_id=decision_unit_id,
        )
        at = at or datetime.now(timezone.utc)
        with self._lock:
            published_profile = any(
                profile.state == PublicationState.PUBLISHED
                and all(
                    (source := self._sources.get(source_id)) is not None
                    and source.review_state == SourceReviewState.REVIEWED
                    and source.subject_resolved
                    and source.retention_expires_at > at
                    for source_id in profile.source_ids
                )
                for profile in self._profiles.values()
                if profile.tenant_id == identity.scope.tenant_id
                and profile.data_domain_id == identity.scope.data_domain_id
            )
            published_prior = any(
                prior.decision_unit_id == decision_unit_id
                and prior.tenant_id == identity.scope.tenant_id
                and prior.data_domain_id == identity.scope.data_domain_id
                and prior.state == PublicationState.PUBLISHED
                and prior.valid_from <= at < prior.expires_at
                for prior in self._priors.values()
            )
        return (
            MarketReadiness.PROBABILISTIC
            if published_profile or published_prior
            else MarketReadiness.PRESSURE_ONLY
        )

    def validate_joint_distribution(
        self, *, identity: IdentityContext, item: JointParticipationDistribution
    ) -> JointParticipationDistribution:
        identity.scope.assert_allows(
            tenant_id=item.tenant_id,
            data_domain_id=item.data_domain_id,
            decision_unit_id=item.decision_unit_id,
        )
        with self._lock:
            visible_ids = {
                competitor.competitor_id
                for competitor in self._competitors.values()
                if competitor.tenant_id == item.tenant_id
                and competitor.data_domain_id == item.data_domain_id
                and competitor.archived_at is None
            }
        referenced_ids = set().union(
            *(scenario.named_competitor_ids for scenario in item.scenarios)
        )
        if not referenced_ids.issubset(visible_ids):
            raise BiaiceError(
                "TENANT_SCOPE_VIOLATION",
                detail="Joint distribution references an unknown or cross-scope competitor.",
            )
        return item


def new_competitor(
    *,
    identity: IdentityContext,
    legal_name: str,
    canonical_subject_key: str,
    aliases: tuple[str, ...] = (),
    now: datetime | None = None,
) -> Competitor:
    now = now or datetime.now(timezone.utc)
    return Competitor(
        competitor_id=uuid4(),
        version_id=uuid4(),
        tenant_id=identity.scope.tenant_id,
        data_domain_id=identity.scope.data_domain_id,
        canonical_subject_key=canonical_subject_key,
        legal_name=legal_name,
        aliases=aliases,
        actor_id=identity.subject_id,
        created_at=now,
        updated_at=now,
    )
