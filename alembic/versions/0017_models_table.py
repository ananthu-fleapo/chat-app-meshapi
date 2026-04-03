"""models_table

Add models table as the canonical whitelist for model metadata.
Only models with a row here (and is_enabled=true) are returned by GET /v1/models.
model_prices continues to own pricing and provider routing independently.

Revision ID: 0017
Revises: 0016a
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0017"
down_revision = "0016a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "models",
        sa.Column("model_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Index for fast enabled-model scans (the hot path for GET /v1/models)
    op.create_index("ix_models_is_enabled", "models", ["is_enabled"])


def downgrade() -> None:
    op.drop_index("ix_models_is_enabled", table_name="models")
    op.drop_table("models")
