"""Improve indexes: discounts composite, drop redundant templates index, payment_events composite

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-31

Changes
-------
1. discounts — add composite (user_id, is_active, model_id) index.
   get_active_discount fires on every paid inference request; this covers all
   three WHERE predicates in a single index scan instead of filtering in memory.

2. templates — drop ix_templates_name (standalone).
   The unique composite constraint uq_templates_owner_name already creates an
   index on (owner, name); the standalone name index is never more selective
   and adds write overhead with no read benefit.

3. payment_events — add composite (user_id, created_at) index.
   Covers the payment-history query pattern:
     WHERE user_id = $1 ORDER BY created_at DESC
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. discounts — composite covering (user_id, is_active, model_id)
    op.create_index(
        "ix_discounts_user_active_model",
        "discounts",
        ["user_id", "is_active", "model_id"],
    )

    # 2. templates — drop the redundant standalone name index
    op.drop_index("ix_templates_name", table_name="templates")

    # 3. payment_events — composite (user_id, created_at)
    op.create_index(
        "ix_payment_events_user_created",
        "payment_events",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_events_user_created", table_name="payment_events")
    op.create_index("ix_templates_name", "templates", ["name"])
    op.drop_index("ix_discounts_user_active_model", table_name="discounts")
