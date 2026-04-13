"""Add capability classification columns to models table

Adds three boolean flags that describe which inference APIs each model
supports and whether it has extended thinking/reasoning capability.

Defaults:
  supports_thinking         = false  (opt-in; only R1/o1/Claude-3.7-extended etc.)
  supports_completions_api  = true   (all existing models use this path)
  supports_responses_api    = false  (opt-in; newer OpenAI responses API format)

Revision ID: 0030
Revises: 0029
Create Date: 2026-04-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("models", "supports_responses_api")
    op.drop_column("models", "supports_completions_api")
    op.drop_column("models", "supports_thinking")
