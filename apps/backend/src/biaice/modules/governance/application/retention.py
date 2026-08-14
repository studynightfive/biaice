"""Retention expiry transition: block formal use before physical disposition."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from biaice.modules.governance.domain.models import (
    RetentionDispositionJob,
    RetentionJobState,
)


class RetentionTransition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job: RetentionDispositionJob
    emit_retention_expired: bool
    request_physical_disposition: bool


def evaluate_retention_expiry(
    job: RetentionDispositionJob,
    *,
    trusted_now: datetime,
    active_legal_hold_count: int,
) -> RetentionTransition:
    if trusted_now < job.retention_expires_at:
        return RetentionTransition(
            job=job,
            emit_retention_expired=False,
            request_physical_disposition=False,
        )
    first_block = job.formal_use_blocked_at is None
    blocked_at = job.formal_use_blocked_at or trusted_now
    state = (
        RetentionJobState.WAITING_FOR_HOLD_RELEASE
        if active_legal_hold_count > 0
        else RetentionJobState.DISPOSITION_RUNNING
    )
    updated = RetentionDispositionJob.model_validate(
        {
            **job.model_dump(),
            "state": state,
            "formal_use_blocked_at": blocked_at,
            "legal_hold_count": active_legal_hold_count,
        }
    )
    return RetentionTransition(
        job=updated,
        emit_retention_expired=first_block,
        request_physical_disposition=active_legal_hold_count == 0,
    )
