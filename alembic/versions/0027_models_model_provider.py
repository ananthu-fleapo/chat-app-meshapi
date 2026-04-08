"""Add brand column to models table

Backfill brand from model_id by extracting the text before '/'.
For example: 'anthropic/claude-haiku-4.5' → 'anthropic'.

Revision ID: 0027
Revises: 0026
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable first so the column can be added without a default
    op.add_column("models", sa.Column("brand", sa.Text(), nullable=True))

    # Backfill: extract text before the first '/'
    op.execute(
        """
        UPDATE models
        SET brand = split_part(model_id, '/', 1)
        WHERE model_id LIKE '%/%'
        """
    )

    # For rows without a '/' in model_id, use the whole model_id as brand
    op.execute(
        """
        UPDATE models
        SET brand = model_id
        WHERE model_id NOT LIKE '%/%'
        """
    )

    # Now enforce NOT NULL
    op.alter_column("models", "brand", nullable=False)


def downgrade() -> None:
    op.drop_column("models", "brand")
