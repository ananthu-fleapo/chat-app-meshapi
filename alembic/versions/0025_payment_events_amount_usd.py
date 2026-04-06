"""Add amount_usd to payment_events

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payment_events", sa.Column("amount_usd", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_events", "amount_usd")
