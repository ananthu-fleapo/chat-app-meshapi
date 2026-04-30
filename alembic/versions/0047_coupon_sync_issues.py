"""create coupon_sync_issues table

Revision ID: 0047
Revises: 0046
Create Date: 2026-04-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coupon_sync_issues",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "coupon_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("checkout_coupons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("coupon_code", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("issue_type", sa.Text(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Text(), nullable=True),
    )
    op.create_index("ix_coupon_sync_issues_coupon_id", "coupon_sync_issues", ["coupon_id"])
    op.create_index("ix_coupon_sync_issues_coupon_code", "coupon_sync_issues", ["coupon_code"])
    op.create_index("ix_coupon_sync_issues_status", "coupon_sync_issues", ["status"])


def downgrade() -> None:
    op.drop_index("ix_coupon_sync_issues_status", table_name="coupon_sync_issues")
    op.drop_index("ix_coupon_sync_issues_coupon_code", table_name="coupon_sync_issues")
    op.drop_index("ix_coupon_sync_issues_coupon_id", table_name="coupon_sync_issues")
    op.drop_table("coupon_sync_issues")
