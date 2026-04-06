"""
Lightweight Redis TTL cache for analytics endpoints.

Usage:
    cached = await get_analytics_cached(redis, "my_key")
    if cached is not None:
        return json.loads(cached)
    result = compute_result()
    await set_analytics_cached(redis, "my_key", json.dumps(result))
    return result
"""

from __future__ import annotations

from redis.asyncio import Redis

_DEFAULT_TTL = 300  # 5 minutes


async def get_analytics_cached(redis: Redis, key: str) -> str | None:
    """Return the cached JSON string for *key*, or None on miss."""
    try:
        return await redis.get(key)
    except Exception:
        return None


async def set_analytics_cached(redis: Redis, key: str, value: str, ttl: int = _DEFAULT_TTL) -> None:
    """Store *value* under *key* with a TTL (seconds). Silently ignores Redis errors."""
    try:
        await redis.set(key, value, ex=ttl)
    except Exception:
        pass
