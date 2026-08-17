"""FR-02 ingest worker tasks. Durable parse progress lives in the document store."""

from __future__ import annotations

from uuid import UUID

from biaice.worker import celery_app
from biaice.workers.ingest.runtime import require_runtime


@celery_app.task(
    name="biaice.ingest.parse_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def parse_document(self, job_id: str, request_id: str = "ingest-worker") -> dict:
    del self
    job = require_runtime().execute_parse_job_for_worker(
        job_id=UUID(job_id), request_id=request_id
    )
    return {"status": job.status.value, "job_id": str(job.job_id)}


@celery_app.task(name="biaice.ingest.scan_document", bind=True, max_retries=0)
def scan_document(self, document_id: str) -> dict:
    del self
    require_runtime()
    return {"status": "accepted", "document_id": document_id}
