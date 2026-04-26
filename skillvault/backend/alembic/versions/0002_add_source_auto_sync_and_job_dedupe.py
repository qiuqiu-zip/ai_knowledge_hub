"""add source auto sync and job dedupe

Revision ID: 0002_auto_sync_job_dedupe
Revises: 0001_init
Create Date: 2026-04-26 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_auto_sync_job_dedupe"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source",
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "source",
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="1440"),
    )
    op.add_column("source", sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source", sa.Column("next_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_source_next_sync_at", "source", ["next_sync_at"])

    op.add_column("sync_job", sa.Column("dedupe_key", sa.String(length=255), nullable=True))
    op.add_column(
        "sync_job",
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )
    op.create_index("ix_sync_job_dedupe_key", "sync_job", ["dedupe_key"])
    op.create_index("ix_sync_job_available_at", "sync_job", ["available_at"])
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_job_dedupe_pending_running
        ON sync_job (dedupe_key)
        WHERE dedupe_key IS NOT NULL AND status IN ('pending', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_sync_job_dedupe_pending_running")
    op.drop_index("ix_sync_job_available_at", table_name="sync_job")
    op.drop_index("ix_sync_job_dedupe_key", table_name="sync_job")
    op.drop_column("sync_job", "available_at")
    op.drop_column("sync_job", "dedupe_key")

    op.drop_index("ix_source_next_sync_at", table_name="source")
    op.drop_column("source", "next_sync_at")
    op.drop_column("source", "last_sync_at")
    op.drop_column("source", "sync_interval_minutes")
    op.drop_column("source", "auto_sync_enabled")
