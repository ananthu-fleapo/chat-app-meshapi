"""Analytics performance indexes

Revision ID: 0022a
Revises: 0022
Create Date: 2026-04-06

Changes
-------
1. usage_events — add ix_usage_events_key_id (single-column).
   The composite ix_usage_events_key_created covers (key_id, created_at) for
   time-range analytics, but the JOIN in get_usage_by_owner() accesses key_id
   without a created_at predicate. A standalone index satisfies those JOIN scans.

2. usage_events — add ix_usage_events_status.
   Several analytics queries count events by status ('success' / 'error').
   A dedicated index enables efficient partial scans for those aggregations.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022a"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Single-column key_id index for JOIN queries without created_at filter
    op.create_index("ix_usage_events_key_id", "usage_events", ["key_id"])

    # 3. Status index for success/error count analytics
    op.create_index("ix_usage_events_status", "usage_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_status", table_name="usage_events")
    op.drop_index("ix_usage_events_key_id", table_name="usage_events")
