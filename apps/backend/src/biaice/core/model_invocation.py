"""Only public generative-model port available to business modules."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from biaice.core.auth import IdentityContext
from biaice.core.jobs import JobAccepted


class GovernedModelInvocationCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: UUID
    decision_unit_id: UUID
    purpose: str
    input_asset_ids: tuple[UUID, ...]
    idempotency_key: str


class GovernedModelInvocationPort(Protocol):
    def submit(
        self,
        *,
        identity: IdentityContext,
        command: GovernedModelInvocationCommand,
    ) -> JobAccepted: ...
