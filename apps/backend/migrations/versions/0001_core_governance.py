"""M0 core jobs, outbox and FR-11 governance baseline.

Revision ID: 0001_core_governance
Revises: None
"""

from alembic import op

from biaice.core.db import Base
from biaice.core.jobs import JobRecord  # noqa: F401
from biaice.core.outbox import OutboxEventRecord  # noqa: F401
from biaice.modules.governance.infrastructure import models as governance_models  # noqa: F401

revision = "0001_core_governance"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)
    if bind.dialect.name != "postgresql":
        return
    for table in Base.metadata.sorted_tables:
        if "tenant_id" not in table.c or "data_domain_id" not in table.c:
            continue
        table_name = table.name.replace('"', '""')
        policy_name = f"{table.name}_tenant_domain_isolation".replace('"', '""')
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'''CREATE POLICY "{policy_name}" ON "{table_name}"
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
                        OR decision_unit_id::text = ANY(string_to_array(current_setting('app.decision_unit_ids', true), ','))
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
                        OR decision_unit_id::text = ANY(string_to_array(current_setting('app.decision_unit_ids', true), ','))
                    )
                )'''
        )


def downgrade() -> None:
    raise RuntimeError("Biaice migrations are forward-only; use the verified restore runbook")
