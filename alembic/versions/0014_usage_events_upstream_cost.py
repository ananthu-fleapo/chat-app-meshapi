"""Add upstream_cost_usd to usage_events for margin reconciliation

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-31

Stores the raw USD cost reported by OpenRouter (usage.cost) alongside our
own billed cost_usd.  Useful for reconciliation: compare what we charged
the user (cost_usd, based on our model_prices) against what OpenRouter
actually billed us (upstream_cost_usd).

NULL for all historical rows and for any request where the upstream omits
the field.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usage_events",
        sa.Column("upstream_cost_usd", sa.Numeric(12, 8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usage_events", "upstream_cost_usd")
