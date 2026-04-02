"""Add currency_conversion_rates table

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            CREATE TABLE IF NOT EXISTS currency_conversion_rates (
                currency    TEXT NOT NULL,
                rate        NUMERIC(18, 10) NOT NULL,
                updated_at  TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                PRIMARY KEY (currency)
            )
        """)
    )

    op.execute(
        sa.text(
            "INSERT INTO currency_conversion_rates (currency, rate, updated_at)"
            " VALUES ('INR', 0.0120000000, now())"
            " ON CONFLICT (currency) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.drop_table("currency_conversion_rates")
