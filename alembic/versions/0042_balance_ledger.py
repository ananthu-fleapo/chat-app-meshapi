"""add balance_ledger table

Revision ID: 0042
Revises: 0041
Create Date: 2026-04-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "balance_ledger",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("txn_type", sa.Text(), nullable=False),
        sa.Column("amount_usd", sa.Numeric(12, 8), nullable=False),
        sa.Column("balance_before", sa.Numeric(12, 6), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 6), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_balance_ledger_user_id", "balance_ledger", ["user_id"])
    op.create_index(
        "ix_balance_ledger_user_created",
        "balance_ledger",
        ["user_id", "created_at"],
    )
    op.create_index("ix_balance_ledger_reference", "balance_ledger", ["reference_id"])
    op.create_index("ix_balance_ledger_txn_type", "balance_ledger", ["txn_type"])
    op.create_index("ix_balance_ledger_created_at", "balance_ledger", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_balance_ledger_created_at", table_name="balance_ledger")
    op.drop_index("ix_balance_ledger_txn_type", table_name="balance_ledger")
    op.drop_index("ix_balance_ledger_reference", table_name="balance_ledger")
    op.drop_index("ix_balance_ledger_user_created", table_name="balance_ledger")
    op.drop_index("ix_balance_ledger_user_id", table_name="balance_ledger")
    op.drop_table("balance_ledger")
