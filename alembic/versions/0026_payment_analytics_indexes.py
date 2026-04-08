"""Payment analytics indexes: country column, provider column, drop JSONB index

Revision ID: 0026
Revises: 0025
Create Date: 2026-04-06

Changes
-------
1. payment_events.country — add ix_payment_events_country.
   get_payment_countries() now groups/orders by the direct TEXT column instead of
   extracting from the JSONB metadata field, so this index replaces the expression
   index created in 0022.

2. payment_events.provider — add ix_payment_events_provider.
   New get_payment_by_provider() endpoint groups by provider; this index covers
   the GROUP BY scan.
   
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Index for the direct country column
    op.create_index("ix_payment_events_country", "payment_events", ["country"])

    # 2. Index for provider grouping
    op.create_index("ix_payment_events_provider", "payment_events", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_payment_events_provider", table_name="payment_events")
    op.drop_index("ix_payment_events_country", table_name="payment_events")
