"""Add gstin_records table

Revision ID: 0023
Revises: 0022
Create Date: 2026-04-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gstin_records",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("payment_event_id", sa.UUID(), nullable=False),
        sa.Column("gstin", sa.Text(), nullable=True),
        sa.Column("gst_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["payment_event_id"],
            ["payment_events.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_gstin_records_payment_event_id",
        "gstin_records",
        ["payment_event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_gstin_records_payment_event_id", table_name="gstin_records")
    op.drop_table("gstin_records")
