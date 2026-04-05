"""provider_model_id

Add provider_model_id column to model_prices so adapters can read the
exact upstream model ID from the DB instead of relying solely on hardcoded
_MODEL_MAP dicts.  NULL = not set; adapters fall back to their internal map.

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_prices",
        sa.Column("provider_model_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_prices", "provider_model_id")
