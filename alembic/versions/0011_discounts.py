"""Add discounts table

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discounts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("discount_pct >= 0 AND discount_pct <= 100", name="discounts_pct_range"),
    )
    op.create_index("ix_discounts_user_id", "discounts", ["user_id"])
    op.create_index("ix_discounts_model_id", "discounts", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_discounts_model_id", table_name="discounts")
    op.drop_index("ix_discounts_user_id", table_name="discounts")
    op.drop_table("discounts")
