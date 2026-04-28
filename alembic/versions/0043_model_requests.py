"""add model_requests table

Revision ID: 0043
Revises: 0042
Create Date: 2026-04-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("use_case", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_requests_owner", "model_requests", ["owner"])
    op.create_index("ix_model_requests_status", "model_requests", ["status"])
    op.create_index("ix_model_requests_created_at", "model_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_requests_created_at", table_name="model_requests")
    op.drop_index("ix_model_requests_status", table_name="model_requests")
    op.drop_index("ix_model_requests_owner", table_name="model_requests")
    op.drop_table("model_requests")
