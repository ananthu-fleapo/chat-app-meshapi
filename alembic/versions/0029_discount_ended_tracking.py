"""Add ended_at/ended_reason to discounts, drop is_active

Retirement is now tracked via valid_until (set to now() when deactivating)
plus ended_at + ended_reason for audit. is_active is removed.

Revision ID: 0029
Revises: 0028
Create Date: 2026-04-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "discounts",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "discounts",
        sa.Column("ended_reason", sa.String(length=64), nullable=True),
    )

    # Back-fill: rows that were manually deactivated (is_active=false) but
    # don't yet have a valid_until in the past — expire them now as "disabled".
    op.execute("""
        UPDATE discounts
        SET
            valid_until = now(),
            ended_at    = now(),
            ended_reason = 'disabled'
        WHERE
            is_active = false
            AND (valid_until IS NULL OR valid_until > now())
    """)

    op.drop_column("discounts", "is_active")


def downgrade() -> None:
    op.add_column(
        "discounts",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # Restore is_active=false for rows that were ended
    op.execute("""
        UPDATE discounts
        SET is_active = false
        WHERE ended_at IS NOT NULL
    """)

    op.drop_column("discounts", "ended_reason")
    op.drop_column("discounts", "ended_at")
