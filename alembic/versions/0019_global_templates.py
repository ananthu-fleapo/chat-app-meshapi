"""global templates: make owner nullable, add partial unique index for global templates

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make owner nullable (global templates have owner = NULL)
    op.alter_column("templates", "owner", nullable=True)

    # Partial unique index to enforce name uniqueness among global templates.
    # Standard UNIQUE(owner, name) allows duplicate (NULL, 'foo') rows because
    # NULL != NULL in Postgres — we need this partial index instead.
    op.create_index(
        "uq_templates_global_name",
        "templates",
        ["name"],
        unique=True,
        postgresql_where=sa.text("owner IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_templates_global_name", "templates")
    op.alter_column("templates", "owner", nullable=False)
