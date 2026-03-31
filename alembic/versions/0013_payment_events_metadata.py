"""Add metadata column to payment_events

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE payment_events ADD COLUMN IF NOT EXISTS metadata JSONB"
        )
    )


def downgrade() -> None:
    op.drop_column("payment_events", "metadata")
