"""
Model cache utilities.

Centralises the Redis cache key constants and the invalidation helper so that
both the models router and the auto-router registry can clear the cache in one
call without duplicating key names.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Shared with app/routers/models.py — must stay in sync.
MODELS_CACHE_KEY = "routerv:models:list"
MODELS_CACHE_TTL = 300  # 5 minutes


async def invalidate_models_cache() -> None:
    """
    Delete the models list cache + all per-api-type autorouter caches.

    Call this after any admin write to the `models` or `model_prices` tables.
    Failures are logged and swallowed — stale cache expires naturally in 5 min.
    """
    from app.auto_router.registry import AUTOROUTER_CACHE_KEYS
    from app.cache.redis_client import get_redis

    redis = get_redis()
    if redis is None:
        return

    try:
        keys = [MODELS_CACHE_KEY, *AUTOROUTER_CACHE_KEYS.values()]
        await redis.delete(*keys)
        logger.info("models_cache_invalidated", keys=keys)
    except Exception as exc:
        logger.warning("models_cache_invalidation_failed", error=str(exc))
