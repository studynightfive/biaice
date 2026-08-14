"""Version metadata shared by immutable and draft resources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VersionMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version_id: UUID
    version_number: int = Field(ge=1)
    created_at: datetime
    created_by: UUID
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    supersedes_version_id: UUID | None = None
