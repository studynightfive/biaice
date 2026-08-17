"""Alembic revision m4_evidence_commercial_0001 — member-4 independent head."""

import sqlalchemy as sa
from alembic import op

revision = "m4_evidence_commercial_0001"
down_revision = None
branch_labels = ("member-4",)
depends_on = None


def _versioned_columns():
    return [
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=20), nullable=False),
        sa.Column("review_state", sa.String(length=20), nullable=False),
        sa.Column("validity_state", sa.String(length=20), nullable=False),
        sa.Column("retention_state", sa.String(length=32), nullable=False, server_default="RETAIN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "requirement_version",
        sa.Column("requirement_id", sa.Uuid(), primary_key=True),
        *_versioned_columns(),
        sa.Column("rule_clause_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("statement", sa.String(length=4000), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.Column("etag", sa.String(length=66), nullable=False),
    )
    op.create_table(
        "company_evidence_version",
        sa.Column("evidence_id", sa.Uuid(), primary_key=True),
        *_versioned_columns(),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=2000), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "evidence_match_version",
        sa.Column("match_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("rationale", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "company_response_profile_version",
        sa.Column("profile_id", sa.Uuid(), primary_key=True),
        *_versioned_columns(),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "precheck_assessment_version",
        sa.Column("precheck_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("unmapped_mandatory_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "condition_requirement_version",
        sa.Column("condition_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("independent_reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocking_stage", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "cost_baseline_version",
        sa.Column("cost_baseline_id", sa.Uuid(), primary_key=True),
        *_versioned_columns(),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("exploration_only", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
    )
    op.create_table(
        "commercial_policy_version",
        sa.Column("policy_id", sa.Uuid(), primary_key=True),
        *_versioned_columns(),
    )
    op.create_table(
        "strategy_readiness_assessment_version",
        sa.Column("readiness_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("exploration_watermark", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table, cols in (
        ("requirement_version", ["tenant_id", "data_domain_id", "decision_unit_id"]),
        ("company_evidence_version", ["tenant_id", "data_domain_id", "decision_unit_id"]),
        ("evidence_match_version", ["tenant_id", "data_domain_id", "decision_unit_id"]),
        ("cost_baseline_version", ["tenant_id", "data_domain_id", "decision_unit_id"]),
    ):
        op.create_index(f"ix_{table}_scope_unit", table, cols)


def downgrade() -> None:
    for table in (
        "strategy_readiness_assessment_version",
        "commercial_policy_version",
        "cost_baseline_version",
        "condition_requirement_version",
        "precheck_assessment_version",
        "company_response_profile_version",
        "evidence_match_version",
        "company_evidence_version",
        "requirement_version",
    ):
        op.drop_table(table)
