"""batch_jobs: add model + provider columns for multi-provider routing

Revision ID: 0037
Revises: 0036
Create Date: 2026-04-14

Changes
-------
1. batch_jobs.model  (Text, NOT NULL, default "unknown")
   The model name supplied by the customer at batch creation time
   (e.g. "openai/gpt-4o-mini"). Stored for billing lookup and audit.

2. batch_jobs.provider  (Text, NOT NULL, default "openai")
   The upstream provider slug resolved from model_prices at creation time
   (e.g. "openai"). Used by the background poller and file endpoints to route
   to the correct adapter without the customer ever specifying a provider.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "batch_jobs",
        sa.Column("model", sa.Text, nullable=False, server_default="unknown"),
    )
    op.add_column(
        "batch_jobs",
        sa.Column("provider", sa.Text, nullable=False, server_default="openai"),
    )
    op.create_index("ix_batch_jobs_provider", "batch_jobs", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_batch_jobs_provider", table_name="batch_jobs")
    op.drop_column("batch_jobs", "provider")
    op.drop_column("batch_jobs", "model")
