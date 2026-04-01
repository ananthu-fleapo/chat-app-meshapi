"""
Unit tests for app/cache/rate_limiter.py

Covers:
  _rpm_bucket_key         — correct format
  _rpd_bucket_key         — correct format
  _seconds_until_next_minute — returns value in [1, 60]
  _seconds_until_next_day    — returns positive value
  check_rate_limits          — within limit, RPM exceeded, RPD exceeded,
                               None per-key limit uses default, Redis fail-open
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

KEY_ID = "00000000-0000-0000-0000-000000000001"


def _make_redis_mock(rpm_count: int, rpd_count: int):
    """Build a Redis mock whose pipeline returns the given counter values."""
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[rpm_count, True, rpd_count, True])

    pipeline_cm = MagicMock()
    pipeline_cm.__aenter__ = AsyncMock(return_value=pipe)
    pipeline_cm.__aexit__ = AsyncMock(return_value=False)

    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipeline_cm)
    return redis


# ── Bucket key helpers ─────────────────────────────────────────────────────────

class TestBucketKeyHelpers:

    def test_rpm_bucket_key_format(self):
        from app.cache.rate_limiter import _rpm_bucket_key
        key = _rpm_bucket_key(KEY_ID)
        assert key.startswith(f"routerv:rl:{KEY_ID}:rpm:")
        # suffix is an integer (unix timestamp // 60)
        suffix = key.split(":")[-1]
        assert suffix.isdigit()

    def test_rpd_bucket_key_format(self):
        from app.cache.rate_limiter import _rpd_bucket_key
        key = _rpd_bucket_key(KEY_ID)
        assert key.startswith(f"routerv:rl:{KEY_ID}:rpd:")
        # suffix is a date string YYYYMMDD
        suffix = key.split(":")[-1]
        assert len(suffix) == 8
        assert suffix.isdigit()


# ── Time helpers ───────────────────────────────────────────────────────────────

class TestTimeHelpers:

    def test_seconds_until_next_minute_in_range(self):
        from app.cache.rate_limiter import _seconds_until_next_minute
        val = _seconds_until_next_minute()
        assert 1 <= val <= 60

    def test_seconds_until_next_day_positive(self):
        from app.cache.rate_limiter import _seconds_until_next_day
        val = _seconds_until_next_day()
        assert val > 0
        assert val <= 86400


# ── check_rate_limits ─────────────────────────────────────────────────────────

class TestCheckRateLimits:

    async def test_within_limits_does_not_raise(self):
        """Both counters below limits → no exception."""
        from app.cache.rate_limiter import check_rate_limits

        redis = _make_redis_mock(rpm_count=5, rpd_count=50)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis):
            await check_rate_limits(KEY_ID, None, None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)

    async def test_rpm_exceeded_raises_rate_limit_error(self):
        """RPM counter > limit → RateLimitError with limit_type='rpm'."""
        from app.cache.rate_limiter import check_rate_limits
        from app.exceptions import RateLimitError

        redis = _make_redis_mock(rpm_count=61, rpd_count=50)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis), \
             patch("app.metrics.RATE_LIMIT_HITS", MagicMock()):
            with pytest.raises(RateLimitError) as exc_info:
                await check_rate_limits(KEY_ID, None, None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)
        assert exc_info.value.limit_type == "rpm"

    async def test_rpd_exceeded_raises_rate_limit_error(self):
        """RPD counter > limit → RateLimitError with limit_type='rpd'."""
        from app.cache.rate_limiter import check_rate_limits
        from app.exceptions import RateLimitError

        redis = _make_redis_mock(rpm_count=5, rpd_count=1001)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis), \
             patch("app.metrics.RATE_LIMIT_HITS", MagicMock()):
            with pytest.raises(RateLimitError) as exc_info:
                await check_rate_limits(KEY_ID, None, None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)
        assert exc_info.value.limit_type == "rpd"

    async def test_rpm_checked_before_rpd(self):
        """When both limits are exceeded, RPM error is raised first."""
        from app.cache.rate_limiter import check_rate_limits
        from app.exceptions import RateLimitError

        redis = _make_redis_mock(rpm_count=61, rpd_count=1001)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis), \
             patch("app.metrics.RATE_LIMIT_HITS", MagicMock()):
            with pytest.raises(RateLimitError) as exc_info:
                await check_rate_limits(KEY_ID, None, None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)
        assert exc_info.value.limit_type == "rpm"

    async def test_per_key_rpm_limit_used_over_default(self):
        """Explicit per-key rpm_limit overrides the system default."""
        from app.cache.rate_limiter import check_rate_limits
        from app.exceptions import RateLimitError

        # 25 requests against a per-key limit of 20, default would allow 60
        redis = _make_redis_mock(rpm_count=25, rpd_count=50)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis), \
             patch("app.metrics.RATE_LIMIT_HITS", MagicMock()):
            with pytest.raises(RateLimitError) as exc_info:
                await check_rate_limits(KEY_ID, rpm_limit=20, rpd_limit=None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)
        assert exc_info.value.limit_type == "rpm"

    async def test_none_per_key_limit_uses_default(self):
        """rpm_limit=None falls back to default_rpm."""
        from app.cache.rate_limiter import check_rate_limits

        # 59 requests, default allows 60 → no exception
        redis = _make_redis_mock(rpm_count=59, rpd_count=50)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis):
            await check_rate_limits(KEY_ID, rpm_limit=None, rpd_limit=None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)

    async def test_redis_unavailable_fails_open(self):
        """Redis error → request proceeds (fail-open), no exception raised."""
        from app.cache.rate_limiter import check_rate_limits

        with patch("app.cache.rate_limiter.get_redis", side_effect=Exception("Redis down")):
            # Must not raise
            await check_rate_limits(KEY_ID, None, None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)

    async def test_retry_after_is_positive_integer(self):
        """RateLimitError carries a positive retry_after value."""
        from app.cache.rate_limiter import check_rate_limits
        from app.exceptions import RateLimitError

        redis = _make_redis_mock(rpm_count=100, rpd_count=50)
        with patch("app.cache.rate_limiter.get_redis", return_value=redis), \
             patch("app.metrics.RATE_LIMIT_HITS", MagicMock()):
            with pytest.raises(RateLimitError) as exc_info:
                await check_rate_limits(KEY_ID, None, None, default_rpm=60, default_rpd=1000, max_rpm=100, max_rpd=7500)
        assert exc_info.value.retry_after > 0
        assert isinstance(exc_info.value.retry_after, int)
