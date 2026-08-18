"""M0 member-7 RiskAcceptance tenant RLS policy.

Revision ID: m7_approvals_reports_0002
Revises: m0_integration_0001
Create Date: 2026-08-18
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "m7_approvals_reports_0002"
down_revision = "m0_integration_0001"
branch_labels = None
depends_on = None

_POLICY = """
CREATE POLICY "risk_acceptance_tenant_domain_isolation" ON "risk_acceptance"
USING (
    tenant_id::text = current_setting('app.tenant_id', true)
    AND data_domain_id::text = current_setting('app.data_domain_id', true)
    AND (
        project_id IS NULL
        OR current_setting('app.all_projects', true) = 'true'
        OR project_id::text = ANY(string_to_array(current_setting('app.project_ids', true), ','))
    )
    AND (
        decision_unit_id IS NULL
        OR current_setting('app.all_decision_units', true) = 'true'
        OR decision_unit_id::text = ANY(
            string_to_array(current_setting('app.decision_unit_ids', true), ',')
        )
    )
)
WITH CHECK (
    tenant_id::text = current_setting('app.tenant_id', true)
    AND data_domain_id::text = current_setting('app.data_domain_id', true)
    AND (
        project_id IS NULL
        OR current_setting('app.all_projects', true) = 'true'
        OR project_id::text = ANY(string_to_array(current_setting('app.project_ids', true), ','))
    )
    AND (
        decision_unit_id IS NULL
        OR current_setting('app.all_decision_units', true) = 'true'
        OR decision_unit_id::text = ANY(
            string_to_array(current_setting('app.decision_unit_ids', true), ',')
        )
    )
)
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute('ALTER TABLE "risk_acceptance" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "risk_acceptance" FORCE ROW LEVEL SECURITY')
    op.execute(_POLICY)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        'DROP POLICY IF EXISTS "risk_acceptance_tenant_domain_isolation" ON "risk_acceptance"'
    )
    op.execute('ALTER TABLE "risk_acceptance" DISABLE ROW LEVEL SECURITY')
