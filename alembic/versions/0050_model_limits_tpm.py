"""add model limits, tpm_limit to api_keys

Revision ID: 0050
Revises: 0049
Create Date: 2026-04-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("allowed_models", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column("api_keys", sa.Column("model_limits", postgresql.JSONB(), nullable=True))
    op.add_column("api_keys", sa.Column("tpm_limit", sa.Integer(), nullable=True))

    # Speeds up check_model_limits() aggregate query per (key_id, model)
    op.create_index("ix_usage_events_key_model", "usage_events", ["key_id", "model"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_key_model", table_name="usage_events")
    op.drop_column("api_keys", "tpm_limit")
    op.drop_column("api_keys", "model_limits")
    op.drop_column("api_keys", "allowed_models")
