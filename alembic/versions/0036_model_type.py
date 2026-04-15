"""Add model_type and modality columns to models table

Adds three columns to describe what type of model it is and what
inputs/outputs it accepts.

  model_type         TEXT    NOT NULL DEFAULT 'text'   -- primary output type
  input_modalities   TEXT[]  NOT NULL DEFAULT '{text}' -- accepted input types
  output_modalities  TEXT[]  NOT NULL DEFAULT '{text}' -- produced output types

model_type values: 'text' | 'embedding' | 'image' | 'audio' | 'video'
All existing rows default to model_type='text', both modality arrays='{text}'.

Revision ID: 0036
Revises: 0035
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "models",
        sa.Column("model_type", sa.Text(), nullable=False, server_default="text"),
    )
    op.add_column(
        "models",
        sa.Column(
            "input_modalities",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY['text']"),
        ),
    )

    op.add_column(
        "models",
        sa.Column(
            "output_modalities",
            sa.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY['text']"),
        ),
    )
    op.create_index("ix_models_model_type", "models", ["model_type"])
    op.create_index(
        "ix_models_input_modalities",
        "models",
        ["input_modalities"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_models_output_modalities",
        "models",
        ["output_modalities"],
        postgresql_using="gin",
    )
    op.create_check_constraint(
        "ck_models_model_type",
        "models",
        "model_type IN ('text', 'embedding', 'image', 'audio', 'video')",
    )


def downgrade() -> None:
    op.drop_index("ix_models_model_type", table_name="models")
    op.drop_column("models", "output_modalities")
    op.drop_column("models", "input_modalities")
    op.drop_column("models", "model_type")
    op.create_index(
        "ix_models_input_modalities",
        "models",
        ["input_modalities"],
        postgresql_using="gin",
    )

    op.create_index(
        "ix_models_output_modalities",
        "models",
        ["output_modalities"],
        postgresql_using="gin",
    )

    # Constraint
    op.create_check_constraint(
        "ck_models_model_type",
        "models",
        "model_type IN ('text', 'embedding', 'image', 'audio', 'video')",
    )
