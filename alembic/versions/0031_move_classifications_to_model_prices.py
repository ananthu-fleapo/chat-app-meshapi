"""Move capability classification columns from models to model_prices

Classifications are provider-specific: the same model may support different
APIs depending on the upstream provider routing it. Moving the three flags
from the model-level `models` table to the per-(model, provider) `model_prices`
table allows independent configuration per provider row.

Also adds responses_provider_model_id to model_prices so that providers
(e.g. Bedrock) can use a different model ID for the Responses API path
vs the completions/Converse path. NULL = fall back to provider_model_id.

Changes:
  - DROP supports_thinking, supports_completions_api, supports_responses_api
    from `models`
  - ADD those same columns to `model_prices` with identical defaults
  - ADD responses_provider_model_id (nullable Text) to `model_prices`

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove from models
    op.drop_column("models", "supports_responses_api")
    op.drop_column("models", "supports_completions_api")
    op.drop_column("models", "supports_thinking")

    # Add to model_prices
    op.add_column(
        "model_prices",
        sa.Column(
            "supports_thinking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "model_prices",
        sa.Column(
            "supports_completions_api",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "model_prices",
        sa.Column(
            "supports_responses_api",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "model_prices",
        sa.Column("responses_provider_model_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Remove from model_prices
    op.drop_column("model_prices", "responses_provider_model_id")
    op.drop_column("model_prices", "supports_responses_api")
    op.drop_column("model_prices", "supports_completions_api")
    op.drop_column("model_prices", "supports_thinking")

    # Restore to models
    op.add_column(
        "models",
        sa.Column(
            "supports_thinking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "models",
        sa.Column(
            "supports_completions_api",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "models",
        sa.Column(
            "supports_responses_api",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
