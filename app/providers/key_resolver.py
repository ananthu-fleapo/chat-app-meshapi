"""
Per-request upstream API key resolver.

Resolves the actual upstream API key for a given owner + provider using
the priority chain:

  1. Owner's active ProviderKey row → GCP Secret Manager (Redis-cached, 5 min TTL)
  2. System default  →  settings.openrouter_api_key

Called once per inference request inside the router, before the upstream
HTTP call.  The resolved key is passed directly to the adapter so the
shared singleton client can override the Authorization header per-request.

Why not cache the DB lookup?
  The ProviderKey lookup is a single indexed row fetch.  Redis is already
  used for the Secret Manager response; adding another caching layer for
  the DB row offers diminishing returns and complicates invalidation.
  Phase 7 can add a short-TTL Redis layer here if profiling shows it matters.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ProviderKey
from app.providers.secret_manager import fetch_secret

logger = structlog.get_logger()


async def resolve_upstream_key(
    owner: str,
    provider: str = "openrouter",
    db: AsyncSession | None = None,
) -> str:
    """
    Return the upstream API key to use for this request.

    Parameters
    ----------
    owner:
        The ``api_key.owner`` label of the authenticated RouterV key.
    provider:
        The upstream provider slug.  Currently only "openrouter" is used.
    db:
        An active async database session.  When None (tests / admin paths),
        the function skips the DB lookup and returns the system default.

    Returns
    -------
    str
        Plaintext upstream API key.  Never empty — falls back to
        ``settings.openrouter_api_key`` if all other lookups fail.
    """
    if db is not None:
        provider_key = await _lookup_provider_key(owner, provider, db)
        if provider_key is not None:
            secret = await fetch_secret(provider_key.secret_ref)
            if secret:
                logger.debug(
                    "provider_key_resolved",
                    owner=owner,
                    provider=provider,
                    provider_key_id=str(provider_key.id),
                )
                return secret
            else:
                # Secret Manager unavailable or secret missing.
                # Fall through to system default rather than hard-failing —
                # the request will still work if the owner hasn't configured
                # their own key yet.
                logger.warning(
                    "provider_key_sm_fallback",
                    owner=owner,
                    provider=provider,
                    secret_ref=provider_key.secret_ref[:60],
                )

    logger.debug("provider_key_system_default", owner=owner, provider=provider)
    return settings.openrouter_api_key


async def _lookup_provider_key(
    owner: str, provider: str, db: AsyncSession
) -> ProviderKey | None:
    """Fetch the owner's active ProviderKey from DB (single indexed read)."""
    result = await db.execute(
        select(ProviderKey)
        .where(
            ProviderKey.owner == owner,
            ProviderKey.provider == provider,
            ProviderKey.is_active.is_(True),
        )
        .order_by(ProviderKey.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
