"""rate limits and spend cap columns on api_keys

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL means "use system default" (Settings.default_rpm / default_rpd).
    # spend_cap_usd is a schema peg for Phase 5 — column exists, enforcement
    # is added when usage_events is in place.
    op.add_column("api_keys", sa.Column("rpm_limit", sa.Integer(), nullable=True))
    op.add_column("api_keys", sa.Column("rpd_limit", sa.Integer(), nullable=True))
    op.add_column(
        "api_keys",
        sa.Column("spend_cap_usd", sa.Numeric(precision=12, scale=6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "spend_cap_usd")
    op.drop_column("api_keys", "rpd_limit")
    op.drop_column("api_keys", "rpm_limit")
