"""M0 member-6 (FR-06/07/08/09a) simulation tables.

This is the first revision on the simulation branch; it sits parallel to the
``0001_core_governance`` revision (which targets the FR-11/governance branch).
Alembic treats multiple heads with ``down_revision = None`` as separate
branches. Downgrade is forward-only per the M0 policy.

Revision ID: m6_simulation_0001
Revises: None
Create Date: 2026-08-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "m6_simulation_0001"
down_revision = None
branch_labels = ("member-6",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decision_baseline",
        sa.Column("baseline_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("manifest_items", JSONB, nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_by", sa.Uuid(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", sa.Uuid(), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("baseline_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_decision_baseline_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_decision_baseline_scope_unit_version",
        ),
    )
    op.create_index(
        "ix_decision_baseline_scope_unit",
        "decision_baseline",
        ["tenant_id", "data_domain_id", "decision_unit_id"],
    )

    op.create_table(
        "candidate_search_space",
        sa.Column("search_space_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("baseline_version_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("dimension_axes", JSONB, nullable=False),
        sa.Column("candidate_count_lower_bound", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("search_space_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_candidate_search_space_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_candidate_search_space_scope_unit_version",
        ),
    )

    op.create_table(
        "scenario_set",
        sa.Column("scenario_set_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("baseline_version_id", sa.Uuid(), nullable=False),
        sa.Column("search_space_version_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_space_version_id", sa.Uuid(), nullable=True),
        sa.Column("stress_axes", JSONB, nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("scenario_set_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_scenario_set_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_scenario_set_scope_unit_version",
        ),
    )

    op.create_table(
        "scenario_set_member",
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_set_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_set_version_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_kind", sa.String(length=20), nullable=False),
        sa.Column("weight", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("params", JSONB, nullable=False),
        sa.PrimaryKeyConstraint("member_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "scenario_set_version_id",
            "scenario_id",
            name="uq_scenario_set_member_scope_version_scenario",
        ),
    )

    op.create_table(
        "simulation_batch",
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("baseline_version_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_set_version_id", sa.Uuid(), nullable=False),
        sa.Column("award_mode", sa.String(length=10), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("policy_threshold", sa.String(length=64), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("failure_reason_code", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("batch_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_simulation_batch_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_simulation_batch_scope_unit_version",
        ),
    )

    op.create_table(
        "simulation_candidate",
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("expected_cost", sa.String(length=64), nullable=False),
        sa.Column("expected_margin", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("candidate_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_simulation_candidate_scope_version",
        ),
    )

    op.create_table(
        "static_candidate_validation",
        sa.Column("validation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rule_codes", JSONB, nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("validation_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "candidate_id",
            "assessed_at",
            name="uq_static_candidate_validation_scope_candidate_assessed",
        ),
    )

    op.create_table(
        "scenario_outcome",
        sa.Column("outcome_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("feasible", sa.Boolean(), nullable=False),
        sa.Column("expected_payoff", sa.String(length=64), nullable=False),
        sa.Column("p_win", sa.String(length=64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_validity", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("outcome_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "candidate_id",
            "scenario_id",
            name="uq_scenario_outcome_scope_candidate_scenario",
        ),
    )

    op.create_table(
        "scenario_strategy_assessment",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("review_validity", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.String(length=400), nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("assessment_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "candidate_id",
            "scenario_id",
            name="uq_scenario_strategy_assessment_scope_candidate_scenario",
        ),
    )

    op.create_table(
        "optimization_run",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("award_mode", sa.String(length=10), nullable=False),
        sa.Column("objective_kind", sa.String(length=20), nullable=False),
        sa.Column("policy_threshold", sa.String(length=64), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_optimization_run_scope_version",
        ),
    )

    op.create_table(
        "strategy_plan",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("linked_run_version_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("award_mode", sa.String(length=10), nullable=False),
        sa.Column("objective_kind", sa.String(length=20), nullable=False),
        sa.Column("members", JSONB, nullable=False),
        sa.Column("p_minus", sa.String(length=64), nullable=False),
        sa.Column("p_plus", sa.String(length=64), nullable=False),
        sa.Column("coverage", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.Uuid(), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("plan_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_strategy_plan_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "run_id",
            "version_id",
            name="uq_strategy_plan_scope_run_version",
        ),
    )

    op.create_table(
        "strategy_plan_member",
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("linkage", sa.String(length=20), nullable=False),
        sa.Column("weight", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("member_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "plan_version_id",
            "candidate_id",
            name="uq_strategy_plan_member_scope_version_candidate",
        ),
    )

    op.create_table(
        "stress_test_assessment",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("axis", sa.String(length=20), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.String(length=400), nullable=False),
        sa.Column("stress_weight", sa.String(length=64), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("assessment_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "run_id",
            "assessment_id",
            name="uq_stress_test_assessment_scope_run",
        ),
    )

    op.create_table(
        "merge_assessment",
        sa.Column("merge_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("linkage", sa.String(length=20), nullable=False),
        sa.Column("tau_b", sa.String(length=64), nullable=False),
        sa.Column("tau_m", sa.String(length=64), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("blocked_reason_code", sa.String(length=120), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("merge_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "run_id",
            "plan_id",
            "assessed_at",
            name="uq_merge_assessment_scope_run_plan",
        ),
    )

    op.create_table(
        "recommendation_eligibility",
        sa.Column("eligibility_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("blocked_reason_codes", JSONB, nullable=False),
        sa.Column("upstream_validity", JSONB, nullable=False),
        sa.Column("baseline_version_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_version_id", sa.Uuid(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessed_by", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("eligibility_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_recommendation_eligibility_scope_version",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "decision_unit_id",
            "version_id",
            name="uq_recommendation_eligibility_scope_unit_version",
        ),
    )

    op.create_table(
        "simulation_assessment_snapshot",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("watermark", sa.String(length=40), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "version_id",
            name="uq_simulation_assessment_snapshot_scope_version",
        ),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Biaice production migrations are forward-only; restore a verified backup instead"
    )
