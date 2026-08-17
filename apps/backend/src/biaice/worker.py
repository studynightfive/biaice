"""Shared Celery app; API and all workers use the same backend image."""

from celery import Celery

from biaice.core.config import get_settings

settings = get_settings()
celery_app = Celery("biaice", broker=settings.redis_broker_url)
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_backend=None,
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "biaice.governance.*": {"queue": "governance"},
        "biaice.ingest.*": {"queue": "ingest"},
        "biaice.simulation.*": {"queue": "simulation"},
        "biaice.provider.*": {"queue": "provider"},
    },
    beat_schedule={
        "governance-outbox-reconciliation": {
            "task": "biaice.governance.reconcile_outbox",
            "schedule": 30.0,
        },
        "governance-retention-due": {
            "task": "biaice.governance.process_retention_due",
            "schedule": 60.0,
        },
    },
    imports=("biaice.workers.governance.tasks", "biaice.workers.ingest.tasks"),
)
