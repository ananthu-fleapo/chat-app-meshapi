"""batch_files: track uploaded files with their resolved model + provider

Revision ID: 0038
Revises: 0037
Create Date: 2026-04-16

Changes
-------
1. New table batch_files
   file_id   TEXT PK — upstream provider file ID
   owner     TEXT NOT NULL — owner label from the uploading API key
   key_id    UUID NOT NULL — API key that performed the upload
   model     TEXT NOT NULL — canonical model_id resolved from the JSONL
   provider  TEXT NOT NULL — upstream provider slug
   created_at TIMESTAMPTZ NOT NULL DEFAULT now()

   ix_batch_files_owner index for per-owner lookups.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "batch_files",
        sa.Column("file_id", sa.Text, primary_key=True),
        sa.Column("owner", sa.Text, nullable=False),
        sa.Column("key_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_batch_files_owner", "batch_files", ["owner"])


def downgrade() -> None:
    op.drop_index("ix_batch_files_owner", table_name="batch_files")
    op.drop_table("batch_files")
