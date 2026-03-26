"""payment_events table

Append-only log of inbound payment webhook events.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("payment_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("addon_product_id", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("payment_id", name="uq_payment_events_payment_id"),
    )
    op.create_index("ix_payment_events_user_id", "payment_events", ["user_id"])
    op.create_index("ix_payment_events_created_at", "payment_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_payment_events_created_at", table_name="payment_events")
    op.drop_index("ix_payment_events_user_id", table_name="payment_events")
    op.drop_table("payment_events")
