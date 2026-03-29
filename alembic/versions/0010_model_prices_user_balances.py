"""Add model_prices and user_balances tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_prices",
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("prompt_usd_per_1k", sa.Numeric(12, 8), nullable=False),
        sa.Column("completion_usd_per_1k", sa.Numeric(12, 8), nullable=False),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("model_id"),
    )

    op.create_table(
        "user_balances",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "balance_usd",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_balances")
    op.drop_table("model_prices")
