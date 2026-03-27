"""payment_events: drop addon_product_id and quantity columns

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("payment_events", "addon_product_id")
    op.drop_column("payment_events", "quantity")


def downgrade() -> None:
    op.add_column("payment_events", sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payment_events", sa.Column("addon_product_id", sa.Text(), nullable=False, server_default=""))
