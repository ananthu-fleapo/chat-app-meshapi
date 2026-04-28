"""
ZDR (Zero Data Retention) flag cache — Redis-backed, per-owner.

Key schema
----------
    routerv:zdr:{owner}   →  b"1" (enabled) or b"0" (disabled)

TTL
---
300 seconds (5 minutes). ZDR is toggled infrequently; 5 min propagation lag
is acceptable. PATCH /v1/settings also calls invalidate_zdr_cache() for
immediate propagation after a change.

Failure policy
--------------
All Redis and DB calls are wrapped in try/except. On any error, returns
False (fail-open) — consistent with the fail-open policy used by key_cache
and rate_limiter. A Redis blip means bodies may be logged for at most the
TTL window (5 min) for an owner who has ZDR enabled.
"""

import structlog

from app.cache.redis_client import get_redis
from app.db.engine import get_session_factory

logger = structlog.get_logger(__name__)

_PREFIX = "routerv:zdr:"
ZDR_CACHE_TTL = 300  # seconds


def _rk(owner: str) -> str:
    return f"{_PREFIX}{owner}"


async def get_owner_zdr(owner: str) -> bool:
    """
    Return True if ZDR is enabled for owner.
    Checks Redis first; falls back to Postgres on cache miss or Redis error.
    Never raises — returns False as the safe default.
    """
    try:
        raw = await get_redis().get(_rk(owner))
        if raw is not None:
            return raw == b"1"
    except Exception as exc:
        logger.warning("redis_unavailable", source="zdr_cache_get", error=str(exc))

    # Cache miss or Redis error — fall back to DB
    try:
        from sqlalchemy import select

        from app.db.models import User

        async with get_session_factory()() as session:
            result = await session.execute(
                select(User.zero_data_retention).where(User.id == owner)
            )
            row = result.scalar_one_or_none()
            flag = bool(row) if row is not None else False

        await _set_zdr_cache(owner, flag)
        return flag
    except Exception as exc:
        logger.warning("db_unavailable", source="zdr_cache_fallback", error=str(exc))
        return False


async def _set_zdr_cache(owner: str, enabled: bool) -> None:
    try:
        await get_redis().setex(_rk(owner), ZDR_CACHE_TTL, b"1" if enabled else b"0")
    except Exception as exc:
        logger.warning("redis_unavailable", source="zdr_cache_set", error=str(exc))


async def invalidate_zdr_cache(owner: str) -> None:
    """Evict cache entry immediately. Called from PATCH /v1/settings."""
    try:
        await get_redis().delete(_rk(owner))
    except Exception as exc:
        logger.warning("redis_unavailable", source="zdr_cache_invalidate", error=str(exc))
