from __future__ import annotations

from fastapi import Request

from biaice.core.audit import AuditWriter
from biaice.core.jobs import JobPort
from biaice.core.security.gates import GateService


def get_gate_service(request: Request) -> GateService:
    return request.app.state.gate_service


def get_job_port(request: Request) -> JobPort:
    return request.app.state.job_port


def get_audit_writer(request: Request) -> AuditWriter:
    return request.app.state.audit_writer
