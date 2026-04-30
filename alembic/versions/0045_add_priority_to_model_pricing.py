"""add priority to model_pricing for provider failover ordering

Revision ID: 0045
Revises: 0044
Create Date: 2026-04-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("model_pricing", sa.Column("priority", sa.Integer(), nullable=True))
    op.create_index(
        "idx_model_pricing_active_priority",
        "model_pricing",
        ["model_id", "priority"],
        postgresql_where=sa.text("is_active = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("idx_model_pricing_active_priority", table_name="model_pricing")
    op.drop_column("model_pricing", "priority")
