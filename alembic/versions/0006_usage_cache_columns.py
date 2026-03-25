"""usage_events cache columns + provider_keys or_key_hash

Adds OpenRouter prompt-caching visibility to usage_events:
  cached_tokens   — how many prompt tokens were served from cache
                    (from usage.prompt_tokens_details.cached_tokens)

Adds OpenRouter Management API metadata to provider_keys:
  or_key_hash     — the hash identifier returned by OpenRouter on key
                    creation; used for PATCH / DELETE via the Management API

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── usage_events ──────────────────────────────────────────────────────────
    # cached_tokens: prompt tokens served from the provider's cache.
    # Populated from usage.prompt_tokens_details.cached_tokens in the upstream
    # response.  NULL means no caching data was reported (not that caching was
    # absent — older model versions may not report it).
    op.add_column(
        "usage_events",
        sa.Column("cached_tokens", sa.Integer(), nullable=True),
    )

    # ── provider_keys ─────────────────────────────────────────────────────────
    # or_key_hash: the identifier assigned by OpenRouter when the key was
    # provisioned.  Required for Management API operations (disable / delete /
    # rotate).  NULL for keys that were registered manually (not auto-provisioned).
    op.add_column(
        "provider_keys",
        sa.Column("or_key_hash", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("provider_keys", "or_key_hash")
    op.drop_column("usage_events", "cached_tokens")
