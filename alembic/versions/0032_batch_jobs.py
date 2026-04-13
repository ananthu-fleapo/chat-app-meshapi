"""batch_jobs table — tracks OpenAI batch jobs for guaranteed usage billing

Revision ID: 0032
Revises: 0031
Create Date: 2026-04-10

Changes
-------
1. New table: batch_jobs
   - Stores every batch created through MeshAPI (owner, key_id, OpenAI IDs).
   - usage_synced flag guards against double-billing.
   - Background poller reads this table to sync usage even when the customer
     never polls or downloads through MeshAPI after creating the batch.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "batch_jobs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("batch_id", sa.Text, nullable=False),
        sa.Column("owner", sa.Text, nullable=False),
        sa.Column("key_id", UUID(as_uuid=True), nullable=False),
        sa.Column("usage_event_id", UUID(as_uuid=True), nullable=True),
        sa.Column("input_file_id", sa.Text, nullable=False),
        sa.Column("output_file_id", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="validating"),
        sa.Column("usage_synced", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_batch_jobs_batch_id",      "batch_jobs", ["batch_id"],      unique=True)
    op.create_index("ix_batch_jobs_owner",         "batch_jobs", ["owner"])
    op.create_index("ix_batch_jobs_output_file_id","batch_jobs", ["output_file_id"])


def downgrade() -> None:
    op.drop_index("ix_batch_jobs_output_file_id", table_name="batch_jobs")
    op.drop_index("ix_batch_jobs_owner",          table_name="batch_jobs")
    op.drop_index("ix_batch_jobs_batch_id",       table_name="batch_jobs")
    op.drop_table("batch_jobs")
