"""Convert currency_conversion_rates to append-only log

Remove the unique primary key on currency and replace it with a UUID primary
key + created_at timestamp so each scheduler call inserts a new snapshot row.
Readers resolve the latest rate with ORDER BY created_at DESC LIMIT 1.

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add id (UUID) and created_at columns
    op.add_column(
        "currency_conversion_rates",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,  # temporarily nullable so existing rows don't fail
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.add_column(
        "currency_conversion_rates",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,  # temporarily nullable for backfill
            server_default=sa.text("now()"),
        ),
    )

    # 2. Backfill existing rows
    op.execute(sa.text(
        "UPDATE currency_conversion_rates SET id = gen_random_uuid() WHERE id IS NULL"
    ))
    op.execute(sa.text(
        "UPDATE currency_conversion_rates SET created_at = now() WHERE created_at IS NULL"
    ))

    # 3. Set columns NOT NULL after backfill
    op.alter_column("currency_conversion_rates", "id", nullable=False)
    op.alter_column("currency_conversion_rates", "created_at", nullable=False)

    # 4. Swap primary key: drop the currency PK, add id PK
    op.drop_constraint("currency_conversion_rates_pkey", "currency_conversion_rates", type_="primary")
    op.execute(sa.text(
        "ALTER TABLE currency_conversion_rates ADD PRIMARY KEY (id)"
    ))

    # 5. Add indexes
    op.create_index(
        "ix_currency_conversion_rates_currency",
        "currency_conversion_rates",
        ["currency"],
    )
    op.create_index(
        "ix_currency_conversion_rates_created_at",
        "currency_conversion_rates",
        ["created_at"],
    )
    op.create_index(
        "ix_currency_conversion_rates_currency_created",
        "currency_conversion_rates",
        ["currency", "created_at"],
    )


def downgrade() -> None:
    # Restore the original schema (currency as PK, updated_at, no id/created_at)
    op.drop_index("ix_currency_conversion_rates_currency_created", "currency_conversion_rates")
    op.drop_index("ix_currency_conversion_rates_created_at", "currency_conversion_rates")
    op.drop_index("ix_currency_conversion_rates_currency", "currency_conversion_rates")

    op.execute(sa.text(
        "ALTER TABLE currency_conversion_rates DROP CONSTRAINT currency_conversion_rates_pkey"
    ))

    # Keep only the latest row per currency to restore uniqueness
    op.execute(sa.text("""
        DELETE FROM currency_conversion_rates a
        USING currency_conversion_rates b
        WHERE a.currency = b.currency AND a.created_at < b.created_at
    """))

    op.execute(sa.text(
        "ALTER TABLE currency_conversion_rates ADD PRIMARY KEY (currency)"
    ))

    op.drop_column("currency_conversion_rates", "created_at")
    op.drop_column("currency_conversion_rates", "id")
