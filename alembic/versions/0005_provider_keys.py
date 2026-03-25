"""provider_keys table + api_keys.provider_key_id

Adds per-owner upstream provider key management.

  provider_keys: stores GCP Secret Manager references (one row per
    owner+provider combination). The actual API key lives in Secret Manager;
    this table just holds the reference path and metadata.

  api_keys.provider_key_id: nullable FK-style pointer from a RouterV key
    to the ProviderKey row its owner has configured. NULL → use system
    default (settings.openrouter_api_key).

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── provider_keys ─────────────────────────────────────────────────────────
    op.create_table(
        "provider_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner", sa.Text(), nullable=False),
        # "openrouter", "openai", "anthropic" — extensible for future adapters
        sa.Column("provider", sa.Text(), nullable=False),
        # GCP Secret Manager resource name:
        #   projects/<project>/secrets/<secret>/versions/latest
        # In dev you can point to any version; in prod always use "latest"
        # so rotation is automatic.
        sa.Column("secret_ref", sa.Text(), nullable=False),
        # Human label for display in admin UIs ("acme prod key", etc.)
        sa.Column("label", sa.Text(), nullable=True),
        # Soft-delete / rotation support: set False on old key before
        # creating a new one.
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_keys_owner", "provider_keys", ["owner"])
    op.create_index(
        "ix_provider_keys_owner_provider",
        "provider_keys",
        ["owner", "provider"],
    )

    # ── api_keys.provider_key_id ──────────────────────────────────────────────
    # Intentionally NOT a DB-level FK — avoids constraint headaches when
    # provider_keys are soft-deleted. Integrity enforced at app layer.
    op.add_column(
        "api_keys",
        sa.Column(
            "provider_key_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "provider_key_id")
    op.drop_index("ix_provider_keys_owner_provider", "provider_keys")
    op.drop_index("ix_provider_keys_owner", "provider_keys")
    op.drop_table("provider_keys")
