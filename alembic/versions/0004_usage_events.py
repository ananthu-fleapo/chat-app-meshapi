"""usage_events table

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # No FK on key_id — append-only table, app-layer integrity.
        sa.Column("key_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stream", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Composite: per-key time-range queries (primary access pattern for billing / analytics)
    op.create_index(
        "ix_usage_events_key_created",
        "usage_events",
        ["key_id", "created_at"],
    )
    # Standalone created_at for system-wide time-range queries
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])
    # Model index for cross-key model analytics
    op.create_index("ix_usage_events_model", "usage_events", ["model"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_model", "usage_events")
    op.drop_index("ix_usage_events_created_at", "usage_events")
    op.drop_index("ix_usage_events_key_created", "usage_events")
    op.drop_table("usage_events")
