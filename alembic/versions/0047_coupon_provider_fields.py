"""add provider sync fields to checkout_coupons

Revision ID: 0047
Revises: 0046
Create Date: 2026-04-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "checkout_coupons",
        sa.Column("currency", sa.Text(), nullable=False, server_default="INR"),
    )
    op.add_column(
        "checkout_coupons",
        sa.Column("stripe_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("checkout_coupons", "stripe_synced_at")
    op.drop_column("checkout_coupons", "currency")
