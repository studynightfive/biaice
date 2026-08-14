from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from biaice.api.dependencies import get_audit_writer, get_job_port
from biaice.core.audit import AuditWriter, require_audit
from biaice.core.auth import IdentityContext, Permission, PermissionGuard
from biaice.core.errors import PROBLEM_RESPONSES, BiaiceError
from biaice.core.idempotency import require_idempotency_key
from biaice.core.jobs import JobPort, JobView

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    operation_id="get_job",
    response_model=JobView,
    responses=PROBLEM_RESPONSES,
)
def get_job(
    job_id: UUID,
    identity: IdentityContext = Depends(PermissionGuard(Permission.JOB_READ)),
    jobs: JobPort = Depends(get_job_port),
) -> JobView:
    job = jobs.get(scope=identity.scope, job_id=job_id)
    if job is None:
        raise BiaiceError("JOB_NOT_FOUND")
    return job


@router.get(
    "/{job_id}/events",
    operation_id="stream_job_events",
    response_class=StreamingResponse,
    responses=PROBLEM_RESPONSES,
)
def stream_job_events(
    job_id: UUID,
    after: int = 0,
    identity: IdentityContext = Depends(PermissionGuard(Permission.JOB_READ)),
    jobs: JobPort = Depends(get_job_port),
) -> StreamingResponse:
    if jobs.get(scope=identity.scope, job_id=job_id) is None:
        raise BiaiceError("JOB_NOT_FOUND")
    events = jobs.events(scope=identity.scope, job_id=job_id, after=after)

    def encode_events():
        for event in events:
            yield f"id: {event.sequence}\nevent: job\ndata: {json.dumps(event.model_dump(mode='json'), separators=(',', ':'))}\n\n"
        yield ": polling fallback is available at the job status URL\n\n"

    return StreamingResponse(encode_events(), media_type="text/event-stream")


@router.post(
    "/{job_id}/cancel",
    operation_id="cancel_job",
    response_model=JobView,
    responses=PROBLEM_RESPONSES,
)
def cancel_job(
    job_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.JOB_COMMAND)),
    idempotency_key: str = Depends(require_idempotency_key),
    jobs: JobPort = Depends(get_job_port),
    audit: AuditWriter = Depends(get_audit_writer),
) -> JobView:
    require_audit(audit)
    job = jobs.cancel(
        scope=identity.scope,
        job_id=job_id,
        actor_id=identity.subject_id,
        idempotency_key=idempotency_key,
    )
    if job is None:
        raise BiaiceError("JOB_NOT_FOUND")
    audit.write(
        identity=identity,
        action="job.cancel",
        object_type="Job",
        object_id=job_id,
        request_id=request.state.request_id,
        reason_code="USER_REQUEST",
        outcome="ACCEPTED",
    )
    return job


@router.post(
    "/{job_id}/retry",
    operation_id="retry_job",
    response_model=JobView,
    responses=PROBLEM_RESPONSES,
)
def retry_job(
    job_id: UUID,
    request: Request,
    identity: IdentityContext = Depends(PermissionGuard(Permission.JOB_COMMAND)),
    idempotency_key: str = Depends(require_idempotency_key),
    jobs: JobPort = Depends(get_job_port),
    audit: AuditWriter = Depends(get_audit_writer),
) -> JobView:
    require_audit(audit)
    job = jobs.retry(
        scope=identity.scope,
        job_id=job_id,
        actor_id=identity.subject_id,
        idempotency_key=idempotency_key,
    )
    if job is None:
        raise BiaiceError("JOB_NOT_FOUND")
    audit.write(
        identity=identity,
        action="job.retry",
        object_type="Job",
        object_id=job_id,
        request_id=request.state.request_id,
        reason_code="USER_REQUEST",
        outcome="ACCEPTED",
    )
    return job
