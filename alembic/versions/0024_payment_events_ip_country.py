"""Add ip_address and country to payment_events

Revision ID: 0024
Revises: 0023
Create Date: 2026-04-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payment_events", sa.Column("ip_address", sa.Text(), nullable=True))
    op.add_column("payment_events", sa.Column("country", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_events", "country")
    op.drop_column("payment_events", "ip_address")
