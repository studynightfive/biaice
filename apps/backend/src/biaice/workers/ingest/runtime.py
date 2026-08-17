"""Ingest worker runtime binding. Kept separate from Celery so the API can start without it."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from biaice.modules.documents.domain.models import ParseJob


class IngestWorkerRuntime(Protocol):
    def execute_parse_job_for_worker(
        self, *, job_id: UUID, request_id: str
    ) -> ParseJob: ...


_runtime: IngestWorkerRuntime | None = None


def bind_runtime(runtime: IngestWorkerRuntime) -> None:
    global _runtime
    _runtime = runtime


def require_runtime() -> IngestWorkerRuntime:
    if _runtime is None:
        raise RuntimeError(
            "ingest worker runtime is not configured; refusing to acknowledge work"
        )
    return _runtime
