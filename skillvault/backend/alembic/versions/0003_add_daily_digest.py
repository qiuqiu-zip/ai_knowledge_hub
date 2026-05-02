"""add daily digest

Revision ID: 0003_add_daily_digest
Revises: 0002_auto_sync_job_dedupe
Create Date: 2026-04-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_add_daily_digest"
down_revision = "0002_auto_sync_job_dedupe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE jobtype ADD VALUE IF NOT EXISTS 'daily_digest'")
    op.create_table(
        "daily_digest",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("digest_date", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("digest_date"),
    )
    op.create_index("ix_daily_digest_digest_date", "daily_digest", ["digest_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_digest_digest_date", table_name="daily_digest")
    op.drop_table("daily_digest")
