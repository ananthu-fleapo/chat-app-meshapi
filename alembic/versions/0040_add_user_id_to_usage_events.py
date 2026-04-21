"""add user_id to usage_events

Revision ID: 0040
Revises: 0039
Create Date: 2026-04-21 12:13:59.216293+00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0040'
down_revision: str | None = '0039'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('usage_events', sa.Column('user_id', sa.Text(), nullable=True))
    op.create_index(op.f('ix_usage_events_user_id'), 'usage_events', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_usage_events_user_id'), table_name='usage_events')
    op.drop_column('usage_events', 'user_id')
