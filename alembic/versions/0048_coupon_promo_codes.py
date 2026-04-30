"""add stripe_coupon_id to checkout_coupons for promo code rows

Revision ID: 0048
Revises: 0047
Create Date: 2026-04-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("checkout_coupons", sa.Column("stripe_coupon_id", sa.Text(), nullable=True))
    op.create_index(
        "ix_checkout_coupons_stripe_coupon_id", "checkout_coupons", ["stripe_coupon_id"]
    )
    # Existing Stripe-synced rows: code IS the Stripe coupon ID, so backfill to itself.
    op.execute(
        "UPDATE checkout_coupons SET stripe_coupon_id = code WHERE stripe_synced_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_checkout_coupons_stripe_coupon_id", table_name="checkout_coupons")
    op.drop_column("checkout_coupons", "stripe_coupon_id")
