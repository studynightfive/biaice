"""Merge all M0 member migration heads after mainline integration.

Revision ID: m0_integration_0001
Revises: 0001_core_governance, m2_projects_rules_0001,
    m3_documents_0001, m4_evidence_commercial_0001,
    m6_simulation_0001, m7_approvals_reports_0001
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

revision = "m0_integration_0001"
down_revision: tuple[str, ...] = (
    "0001_core_governance",
    "m2_projects_rules_0001",
    "m3_documents_0001",
    "m4_evidence_commercial_0001",
    "m6_simulation_0001",
    "m7_approvals_reports_0001",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join the independent member branches without changing schema objects."""


def downgrade() -> None:
    """Split back to the independent heads without changing schema objects."""
