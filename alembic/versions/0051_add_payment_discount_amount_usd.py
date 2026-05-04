"""Add discount_amount_usd to payment_events

Revision ID: 0051
Revises: 0050
Create Date: 2026-05-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payment_events", sa.Column("discount_amount_usd", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_events", "discount_amount_usd")
