"""Make discounts.user_id nullable (model-level global discounts)

Discount rows now support:
  - user_id=<id>,  model_id=NULL  → account-level per-user discount
  - user_id=<id>,  model_id=<id>  → model-level per-user discount
  - user_id=NULL,  model_id=<id>  → global discount for all users on a specific model

Constraint: at least one of user_id or model_id must be non-NULL (enforced at app level).

Revision ID: 0028
Revises: 0027
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "discounts",
        "user_id",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    # Rows with user_id=NULL would violate NOT NULL — delete them first or set a default.
    op.execute("DELETE FROM discounts WHERE user_id IS NULL")
    op.alter_column(
        "discounts",
        "user_id",
        existing_type=sa.Text(),
        nullable=False,
    )
