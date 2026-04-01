"""
Fixed-window rate limiter backed by Redis.

Two windows per key
-------------------
RPM  requests-per-minute  →  burst protection
RPD  requests-per-day     →  daily quota

Algorithm: fixed window counter
--------------------------------
INCR  routerv:rl:{key_id}:rpm:{YYYYMMDDHHMM}
EXPIRE ... 90s   (1.5× the window — safety margin so the key doesn't vanish
                  mid-window on a busy server)

Both counters are incremented in a single pipeline (one round-trip).
The check is not strictly atomic — two concurrent requests can both pass
the check and briefly exceed the limit by 1–2. This is acceptable for
LLM rate limits; use a Lua script if strict atomicity is ever needed.

Failure policy
--------------
If Redis is unreachable, the rate limiter fails OPEN (requests are allowed
through) and logs a warning. A Redis blip should not take down the API.

Why fixed window over sliding window?
--------------------------------------
Sliding window (sorted set + Lua) is more accurate but adds complexity and
Redis memory proportional to request volume. The fixed-window "boundary
burst" problem (up to 2× rate at window edges) is irrelevant for LLM
workloads where each request takes 100ms–3s. Revisit if this causes issues.

Free model rate limiting
------------------------
check_free_model_rate_limits() uses a separate Redis key namespace
(routerv:rl:{key_id}:free:rpm / :free:rpd) so free-model usage is
counted independently of paid requests. The counter is shared across
ALL free models for a given key — rotating across free model IDs does
not reset the bucket.
"""

import time
from datetime import datetime, timezone, timedelta

import structlog

from app.cache.redis_client import get_redis
from app.exceptions import RateLimitError

logger = structlog.get_logger()

_PREFIX = "routerv:rl"


def _rpm_bucket_key(key_id: str) -> str:
    """Key resets every calendar minute (UTC)."""
    bucket = int(time.time()) // 60
    return f"{_PREFIX}:{key_id}:rpm:{bucket}"


def _rpd_bucket_key(key_id: str) -> str:
    """Key resets every calendar day (UTC)."""
    bucket = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{_PREFIX}:{key_id}:rpd:{bucket}"


def _free_rpm_bucket_key(key_id: str) -> str:
    bucket = int(time.time()) // 60
    return f"{_PREFIX}:{key_id}:free:rpm:{bucket}"


def _free_rpd_bucket_key(key_id: str) -> str:
    bucket = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{_PREFIX}:{key_id}:free:rpd:{bucket}"


def _seconds_until_next_minute() -> int:
    return 60 - (int(time.time()) % 60)


def _seconds_until_next_day() -> int:
    now = datetime.now(timezone.utc)
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1, int((next_midnight - now).total_seconds()))


async def check_rate_limits(
    key_id: str,
    rpm_limit: int | None,
    rpd_limit: int | None,
    default_rpm: int,
    default_rpd: int,
    max_rpm: int,
    max_rpd: int,
) -> None:
    """
    Increment both counters and raise RateLimitError if either is exceeded.

    Parameters
    ----------
    key_id       UUID string of the ApiKey (used as part of the Redis key).
    rpm_limit    Per-key override; falls back to default_rpm if None.
    rpd_limit    Per-key override; falls back to default_rpd if None.
    default_rpm  System default from Settings.
    default_rpd  System default from Settings.
    max_rpm      Hard ceiling — effective RPM is clamped to this regardless
                 of per-key override.
    max_rpd      Hard ceiling — effective RPD is clamped to this regardless
                 of per-key override.
    """
    effective_rpm = min(rpm_limit if rpm_limit is not None else default_rpm, max_rpm)
    effective_rpd = min(rpd_limit if rpd_limit is not None else default_rpd, max_rpd)

    rpm_key = _rpm_bucket_key(key_id)
    rpd_key = _rpd_bucket_key(key_id)

    try:
        r = get_redis()
        async with r.pipeline(transaction=False) as pipe:
            pipe.incr(rpm_key)
            pipe.expire(rpm_key, 90)       # 1.5 × 60s window
            pipe.incr(rpd_key)
            pipe.expire(rpd_key, 90000)    # ~25h — covers the full UTC day + buffer
            results = await pipe.execute()

        rpm_count: int = results[0]
        rpd_count: int = results[2]

    except Exception as exc:
        # Redis unavailable — fail open, log warning.
        logger.warning("redis_unavailable", source="rate_limiter", key_id=key_id, error=str(exc))
        return

    if rpm_count > effective_rpm:
        retry = _seconds_until_next_minute()
        logger.info(
            "rate_limit_rpm_exceeded",
            key_id=key_id,
            count=rpm_count,
            limit=effective_rpm,
            retry_after=retry,
        )
        from app.metrics import RATE_LIMIT_HITS
        RATE_LIMIT_HITS.labels(limit_type="rpm").inc()
        raise RateLimitError(
            f"RPM limit of {effective_rpm} req/min exceeded.",
            limit_type="rpm",
            retry_after=retry,
        )

    if rpd_count > effective_rpd:
        retry = _seconds_until_next_day()
        logger.info(
            "rate_limit_rpd_exceeded",
            key_id=key_id,
            count=rpd_count,
            limit=effective_rpd,
            retry_after=retry,
        )
        from app.metrics import RATE_LIMIT_HITS
        RATE_LIMIT_HITS.labels(limit_type="rpd").inc()
        raise RateLimitError(
            f"RPD limit of {effective_rpd} req/day exceeded.",
            limit_type="rpd",
            retry_after=retry,
        )


async def check_free_model_rate_limits(
    key_id: str,
    free_rpm: int,
    free_rpd: int,
) -> None:
    """
    Rate-limit free-model requests using separate Redis counters.

    Counted per key, shared across all free models — rotating through
    different free model IDs does not reset the bucket.

    Fails open on Redis errors (same policy as check_rate_limits).
    """
    rpm_key = _free_rpm_bucket_key(key_id)
    rpd_key = _free_rpd_bucket_key(key_id)

    try:
        r = get_redis()
        async with r.pipeline(transaction=False) as pipe:
            pipe.incr(rpm_key)
            pipe.expire(rpm_key, 90)
            pipe.incr(rpd_key)
            pipe.expire(rpd_key, 90000)
            results = await pipe.execute()

        rpm_count: int = results[0]
        rpd_count: int = results[2]

    except Exception as exc:
        logger.warning("redis_unavailable", source="free_rate_limiter", key_id=key_id, error=str(exc))
        return

    if rpm_count > free_rpm:
        retry = _seconds_until_next_minute()
        logger.info(
            "free_rate_limit_rpm_exceeded",
            key_id=key_id,
            count=rpm_count,
            limit=free_rpm,
            retry_after=retry,
        )
        from app.metrics import RATE_LIMIT_HITS
        RATE_LIMIT_HITS.labels(limit_type="free_rpm").inc()
        raise RateLimitError(
            f"Free model RPM limit of {free_rpm} req/min exceeded.",
            limit_type="rpm",
            retry_after=retry,
        )

    if rpd_count > free_rpd:
        retry = _seconds_until_next_day()
        logger.info(
            "free_rate_limit_rpd_exceeded",
            key_id=key_id,
            count=rpd_count,
            limit=free_rpd,
            retry_after=retry,
        )
        from app.metrics import RATE_LIMIT_HITS
        RATE_LIMIT_HITS.labels(limit_type="free_rpd").inc()
        raise RateLimitError(
            f"Free model RPD limit of {free_rpd} req/day exceeded.",
            limit_type="rpd",
            retry_after=retry,
        )
