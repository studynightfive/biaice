"""Durable PostgreSQL-backed job contract (port plus transport schemas)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from biaice.core.auth import TenantScope
from biaice.core.db import Base, TenantScopedMixin


class JobState(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"


TERMINAL_JOB_STATES = frozenset(
    {JobState.CANCELLED, JobState.SUCCEEDED, JobState.FAILED_TERMINAL}
)


class JobRecord(Base, TenantScopedMixin):
    __tablename__ = "job"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "idempotency_key",
            name="uq_job_scope_idempotency",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    queue_name: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    cancellation_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class JobView(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: UUID
    job_type: str
    queue_name: str
    state: JobState
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    attempt: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None
    recoverable: bool = False
    status_url: str
    events_url: str


class JobAccepted(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: UUID
    status_url: str
    events_url: str


class JobCommandEnvelope(BaseModel):
    """Broker payload envelope; Redis/Celery never infers tenant scope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: UUID
    tenant_id: UUID
    data_domain_id: UUID
    project_id: UUID | None = None
    decision_unit_id: UUID | None = None
    job_type: str
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    payload: dict

    def scope(self) -> TenantScope:
        return TenantScope(
            tenant_id=self.tenant_id,
            data_domain_id=self.data_domain_id,
            project_ids=frozenset({self.project_id})
            if self.project_id
            else frozenset(),
            decision_unit_ids=frozenset({self.decision_unit_id})
            if self.decision_unit_id
            else frozenset(),
        )


class JobEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(ge=0)
    occurred_at: datetime
    state: JobState
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    code: str | None = None


class JobPort(Protocol):
    def get(self, *, scope: TenantScope, job_id: UUID) -> JobView | None: ...

    def cancel(
        self,
        *,
        scope: TenantScope,
        job_id: UUID,
        actor_id: UUID,
        idempotency_key: str,
    ) -> JobView | None: ...

    def retry(
        self,
        *,
        scope: TenantScope,
        job_id: UUID,
        actor_id: UUID,
        idempotency_key: str,
    ) -> JobView | None: ...

    def events(
        self, *, scope: TenantScope, job_id: UUID, after: int = 0
    ) -> Sequence[JobEvent]: ...


class UnavailableJobPort:
    def get(self, *, scope: TenantScope, job_id: UUID) -> JobView | None:
        del scope, job_id
        return None

    def cancel(
        self, *, scope: TenantScope, job_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> JobView | None:
        del scope, job_id, actor_id, idempotency_key
        return None

    def retry(
        self, *, scope: TenantScope, job_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> JobView | None:
        del scope, job_id, actor_id, idempotency_key
        return None

    def events(
        self, *, scope: TenantScope, job_id: UUID, after: int = 0
    ) -> Sequence[JobEvent]:
        del scope, job_id, after
        return ()
