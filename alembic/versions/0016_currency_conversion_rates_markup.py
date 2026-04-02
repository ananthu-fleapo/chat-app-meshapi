"""Add markup_fee and total_rate to currency_conversion_rates

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "currency_conversion_rates",
        sa.Column("markup_fee", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "currency_conversion_rates",
        sa.Column("total_rate", sa.Numeric(18, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("currency_conversion_rates", "total_rate")
    op.drop_column("currency_conversion_rates", "markup_fee")
