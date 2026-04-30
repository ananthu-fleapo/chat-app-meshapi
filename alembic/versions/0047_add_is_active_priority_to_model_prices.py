"""add is_active and priority to model_prices (v1) for provider failover

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
        "model_prices",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column("model_prices", sa.Column("priority", sa.Integer(), nullable=True))
    op.create_index(
        "idx_model_prices_active_priority",
        "model_prices",
        ["model_id", "priority"],
        postgresql_where=sa.text("is_active = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("idx_model_prices_active_priority", table_name="model_prices")
    op.drop_column("model_prices", "priority")
    op.drop_column("model_prices", "is_active")
