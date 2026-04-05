"""upstream_pricing

Add upstream_prompt_usd_per_1k and upstream_completion_usd_per_1k to
model_prices so that we can calculate upstream_cost_usd for providers
that don't report it in their API response (Vertex AI, Bedrock, OpenAI Direct, Qwen).

NULL = not configured; logger skips upstream cost calculation for those rows.

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_prices",
        sa.Column("upstream_prompt_usd_per_1k", sa.Numeric(12, 8), nullable=True),
    )
    op.add_column(
        "model_prices",
        sa.Column("upstream_completion_usd_per_1k", sa.Numeric(12, 8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_prices", "upstream_completion_usd_per_1k")
    op.drop_column("model_prices", "upstream_prompt_usd_per_1k")
