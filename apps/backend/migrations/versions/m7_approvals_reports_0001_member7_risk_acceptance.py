"""M0 member-7 (FR-09b) risk acceptance table.

Revision ID: m7_approvals_reports_0001
Revises: None
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "m7_approvals_reports_0001"
down_revision = None
branch_labels = ("member-7",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_acceptance",
        sa.Column("risk_acceptance_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("validity", sa.String(length=20), nullable=False),
        sa.Column("risk", sa.String(length=200), nullable=False),
        sa.Column("metric", sa.String(length=200), nullable=False),
        sa.Column("acceptance_scope", sa.String(length=400), nullable=False),
        sa.Column("rationale", sa.String(length=2000), nullable=False),
        sa.Column("independent_approver_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_by", sa.Uuid(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.Column("revocation_reason", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("risk_acceptance_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_risk_acceptance_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_risk_acceptance_scope_unit_version",
        ),
    )
    op.create_index(
        "ix_risk_acceptance_scope_unit",
        "risk_acceptance",
        ["tenant_id", "data_domain_id", "decision_unit_id"],
    )
    op.create_index(
        "ix_risk_acceptance_scope_unit_valid",
        "risk_acceptance",
        ["tenant_id", "data_domain_id", "decision_unit_id", "valid_until"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_risk_acceptance_scope_unit_valid",
        table_name="risk_acceptance",
    )
    op.drop_index(
        "ix_risk_acceptance_scope_unit",
        table_name="risk_acceptance",
    )
    op.drop_table("risk_acceptance")

