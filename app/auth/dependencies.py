"""
FastAPI auth dependency: validates a RouterV API key on every request.

Phase 3 flow (cache-aside)
--------------------------
1. Extract Bearer token from Authorization header  →  401 if missing/malformed
2. SHA-256(token)  →  key_hash
3. Redis GET routerv:key:{key_hash}
     HIT  → deserialize to ApiKey, check status, return   (no DB)
     MISS → Postgres SELECT by key_hash
              found     → populate Redis cache, check status, return
              not found → 401
4. status != "active"  →  403

The DB session is only opened on a Redis miss — warm requests never
touch Postgres.

Phase 3 note on cache invalidation
------------------------------------
Admin PATCH / DELETE calls invalidate_cached_key() immediately so changes
propagate in < 1 request. The 60s TTL is a safety net only.
"""

import hashlib

import structlog
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.key_cache import get_cached_key, set_cached_key
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.exceptions import ForbiddenError, UnauthorizedError

logger = structlog.get_logger()


def _extract_bearer(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Authorization header must be: Bearer <key>")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedError("Bearer token is empty.")
    return token


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _check_active(key: ApiKey, raw_key: str) -> None:
    if key.status != "active":
        logger.warning("auth_suspended_key", key_id=str(key.id), owner=key.owner)
        raise ForbiddenError("API key is suspended.")


async def get_authenticated_key(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> ApiKey:
    """
    Resolves and validates the caller's RouterV API key.
    Returns the ApiKey (may be a cache-reconstructed instance — read-only).
    """
    raw_key = _extract_bearer(authorization)
    key_hash = _hash_key(raw_key)

    # ── 1. Try Redis cache ────────────────────────────────────────────────────
    cached = await get_cached_key(key_hash)
    if cached is not None:
        logger.debug("auth_cache_hit", key_id=str(cached.id), owner=cached.owner)
        _check_active(cached, raw_key)
        return cached

    # ── 2. Cache miss → Postgres ──────────────────────────────────────────────
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    key = result.scalar_one_or_none()

    if key is None:
        logger.warning("auth_invalid_key", key_prefix=raw_key[:8] + "...")
        raise UnauthorizedError()

    _check_active(key, raw_key)

    # ── 3. Populate cache for next request ────────────────────────────────────
    await set_cached_key(key)
    logger.debug("auth_cache_miss_populated", key_id=str(key.id), owner=key.owner)

    return key
