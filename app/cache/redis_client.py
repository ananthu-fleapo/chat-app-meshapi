"""
Redis singleton — one connection pool for the process lifetime.

Lifecycle
---------
init_redis(url)  called in app lifespan (startup). Pings Redis to fail fast
                 if the URL is wrong or the server is unreachable.
close_redis()    called in app lifespan (shutdown).

GCP production note
-------------------
Memorystore for Redis runs inside the same VPC as Cloud Run.
No TLS needed on the internal network; use:
    REDIS_URL=redis://10.x.x.x:6379/0
where 10.x.x.x is the Memorystore instance's private IP.

If Redis is unreachable at runtime:
  - Key cache: falls back to Postgres (degraded but correct).
  - Rate limiter: fails open (requests are allowed through) and logs a warning.
    This is a deliberate choice — a Redis blip should not take the API down.
"""

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


async def init_redis(url: str) -> aioredis.Redis:
    global _redis
    _redis = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    await _redis.ping()   # fail fast at startup if Redis is unreachable
    # Mask credentials in the logged URL (e.g. redis://:password@host → redis://***@host)
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    safe_url = urlunparse(parsed._replace(password="***")) if parsed.password else url
    logger.info("redis_ready", url=safe_url)
    return _redis


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() in lifespan.")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("redis_closed")
