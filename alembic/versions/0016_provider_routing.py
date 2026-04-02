"""provider_routing

Add provider + is_default to model_prices (composite PK),
and provider column to usage_events for per-request audit trail.

Revision ID: 0016
Revises: 0015
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── model_prices ──────────────────────────────────────────────────────────

    # 1. Add provider and is_default columns (nullable first so backfill works)
    op.add_column(
        "model_prices",
        sa.Column("provider", sa.Text(), nullable=True),
    )
    op.add_column(
        "model_prices",
        sa.Column("is_default", sa.Boolean(), nullable=True),
    )

    # 2. Backfill: existing rows were OpenRouter-only and are their own default
    op.execute("UPDATE model_prices SET provider = 'openrouter', is_default = true")

    # 3. Make columns NOT NULL now that all rows are populated
    op.alter_column("model_prices", "provider", nullable=False)
    op.alter_column("model_prices", "is_default", nullable=False)

    # 4. Drop the old single-column primary key
    op.execute("ALTER TABLE model_prices DROP CONSTRAINT model_prices_pkey")

    # 5. Add composite primary key (model_id, provider)
    op.execute(
        "ALTER TABLE model_prices ADD PRIMARY KEY (model_id, provider)"
    )

    # 6. Partial unique index: only one default provider per model_id
    op.execute(
        """
        CREATE UNIQUE INDEX ix_model_prices_one_default
            ON model_prices (model_id)
            WHERE is_default = true
        """
    )

    # ── usage_events ──────────────────────────────────────────────────────────

    # 7. Add provider column (nullable = safe for existing rows)
    op.add_column(
        "usage_events",
        sa.Column(
            "provider",
            sa.Text(),
            nullable=False,
            server_default="openrouter",
        ),
    )

    # 8. Index for provider-level analytics / filtering
    op.create_index(
        "ix_usage_events_provider",
        "usage_events",
        ["provider"],
    )


def downgrade() -> None:
    # ── usage_events ──────────────────────────────────────────────────────────
    op.drop_index("ix_usage_events_provider", table_name="usage_events")
    op.drop_column("usage_events", "provider")

    # ── model_prices ──────────────────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_model_prices_one_default")
    op.execute("ALTER TABLE model_prices DROP CONSTRAINT model_prices_pkey")
    op.execute("ALTER TABLE model_prices ADD PRIMARY KEY (model_id)")
    op.drop_column("model_prices", "is_default")
    op.drop_column("model_prices", "provider")
