"""M0 member-2 (FR-01) project, decision-unit, scope and rule tables.

Revision ID: m2_projects_rules_0001
Revises: None
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

revision = "m2_projects_rules_0001"
down_revision = None
branch_labels = ("member-2",)
depends_on = None


def _scope_columns(*, project: bool = True, unit: bool = True) -> tuple[sa.Column, ...]:
    columns = [
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
    ]
    if project:
        columns.append(sa.Column("project_id", sa.Uuid(), nullable=True))
    if unit:
        columns.append(sa.Column("decision_unit_id", sa.Uuid(), nullable=True))
    return tuple(columns)


def upgrade() -> None:
    op.create_table(
        "procurement_project",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        *_scope_columns(project=False, unit=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_index(
        "ix_procurement_project_scope_created",
        "procurement_project",
        ["tenant_id", "data_domain_id", "created_at"],
    )
    op.create_table(
        "decision_unit",
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        *_scope_columns(project=True, unit=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("decision_unit_id"),
    )
    op.create_index(
        "ix_decision_unit_scope_project",
        "decision_unit",
        ["tenant_id", "data_domain_id", "project_id"],
    )
    op.create_table(
        "decision_unit_lifecycle_event",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "sequence",
            name="uq_lifecycle_event_sequence",
        ),
    )
    op.create_table(
        "scope_assessment",
        sa.Column("scope_assessment_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("scope_assessment_id"),
    )
    op.create_table(
        "applicable_regime",
        sa.Column("applicable_regime_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("applicable_regime_id"),
    )
    op.create_table(
        "rule_set",
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("scope_level", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("rule_set_id"),
    )
    op.create_table(
        "rule_clause",
        sa.Column("rule_clause_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.Column("coverage_key", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("rule_clause_id"),
    )
    op.create_index("ix_rule_clause_rule_set_id", "rule_clause", ["rule_set_id"])
    op.create_table(
        "compliance_review",
        sa.Column("compliance_review_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("compliance_review_id"),
    )
    op.create_table(
        "cross_lot_constraint",
        sa.Column("cross_lot_constraint_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("cross_lot_constraint_id"),
    )
    op.create_table(
        "document_intake_ref",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        *_scope_columns(),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("document_intake_ref")
    op.drop_table("cross_lot_constraint")
    op.drop_table("compliance_review")
    op.drop_index("ix_rule_clause_rule_set_id", table_name="rule_clause")
    op.drop_table("rule_clause")
    op.drop_table("rule_set")
    op.drop_table("applicable_regime")
    op.drop_table("scope_assessment")
    op.drop_table("decision_unit_lifecycle_event")
    op.drop_index("ix_decision_unit_scope_project", table_name="decision_unit")
    op.drop_table("decision_unit")
    op.drop_index("ix_procurement_project_scope_created", table_name="procurement_project")
    op.drop_table("procurement_project")
