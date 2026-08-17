"""M0 member-3 (FR-02) document intake tables.

Revision ID: m3_documents_0001
Revises: None
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

revision = "m3_documents_0001"
down_revision = None
branch_labels = ("member-3",)
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_upload_session",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("mime_category", sa.String(length=30), nullable=False),
        sa.Column("declared_sha256", sa.String(length=64), nullable=False),
        sa.Column("chunk_size_bytes", sa.Integer(), nullable=False),
        sa.Column("total_parts", sa.Integer(), nullable=False),
        sa.Column("received_parts", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("final_sha256", sa.String(length=64), nullable=True),
        sa.Column("final_size_bytes", sa.Integer(), nullable=True),
        sa.Column("quarantine_key", sa.String(length=1000), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        "ix_document_upload_session_scope",
        "document_upload_session",
        ["tenant_id", "data_domain_id", "status"],
    )
    op.create_table(
        "source_document",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("storage_locator_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("declared_content_type", sa.String(length=100), nullable=False),
        sa.Column("sniffed_content_type", sa.String(length=100), nullable=False),
        sa.Column("mime_category", sa.String(length=30), nullable=False),
        sa.Column("scan_result", sa.String(length=30), nullable=False),
        sa.Column("scan_signature_version", sa.String(length=100), nullable=True),
        sa.Column("scan_details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.Uuid(), nullable=True),
        sa.Column("upload_session_id", sa.Uuid(), nullable=False),
        sa.Column("source_filename", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("document_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "data_domain_id",
            "upload_session_id",
            name="uq_source_document_session",
        ),
    )
    op.create_index(
        "ix_source_document_scope_status",
        "source_document",
        ["tenant_id", "data_domain_id", "status"],
    )
    op.create_table(
        "document_parse_job",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("retryable", sa.String(length=50), nullable=True),
        sa.Column("failure_reason_code", sa.String(length=120), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("derived_asset_ids", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_document_parse_job_document",
        "document_parse_job",
        ["tenant_id", "data_domain_id", "document_id"],
    )
    op.create_table(
        "document_derived_asset",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=True),
        sa.Column("parse_job_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("storage_locator_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("fragment_ref", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("asset_id"),
    )
    op.create_table(
        "document_replica_location",
        sa.Column("replica_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("target_object_type", sa.String(length=50), nullable=False),
        sa.Column("target_object_id", sa.Uuid(), nullable=False),
        sa.Column("target_version_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("adapter_name", sa.String(length=120), nullable=False),
        sa.Column("adapter_owner", sa.String(length=60), nullable=False),
        sa.Column("locator_hash", sa.String(length=64), nullable=False),
        sa.Column("required_for_completion", sa.Boolean(), nullable=False),
        sa.Column("deletion_sla_seconds", sa.Integer(), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("replica_id"),
    )
    op.create_table(
        "document_link",
        sa.Column("link_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("data_domain_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("decision_unit_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("conflict_state", sa.String(length=30), nullable=False),
        sa.Column("confirmation_reason", sa.Text(), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detached_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("link_id"),
    )


def downgrade() -> None:
    raise RuntimeError("Biaice migrations are forward-only; use the verified restore runbook")
