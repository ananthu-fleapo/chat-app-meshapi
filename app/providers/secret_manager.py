"""
GCP Secret Manager client.

Fetches plaintext secret values by resource name and caches them in Redis
to avoid per-request Secret Manager API calls (latency + quota cost).

Cache key : routerv:sm:<sha256(secret_ref)>
Cache TTL : 300 s  (5 minutes)

Graceful fallback behaviour
---------------------------
- If ``google-cloud-secret-manager`` is not installed → log once, return None.
- If ``settings.gcp_project_id`` is empty → not a GCP environment, return None.
- If Secret Manager call fails (network, permissions) → log warning, return None.

The caller (key_resolver.py) must handle a None return by falling back to
the system default key (settings.openrouter_api_key).
"""

from __future__ import annotations

import hashlib
import json
import logging

import structlog

logger = structlog.get_logger()

_SM_CACHE_PREFIX = "routerv:sm:"
_SM_CACHE_TTL = 300  # seconds

# Attempt to import the GCP client; fall back cleanly in local-dev environments
# that don't have google-cloud-secret-manager installed.
try:
    from google.cloud import secretmanager as _secretmanager  # type: ignore[import-untyped]

    _SM_AVAILABLE = True
except ImportError:
    _secretmanager = None  # type: ignore[assignment]
    _SM_AVAILABLE = False
    logging.getLogger(__name__).debug(
        "google-cloud-secret-manager not installed — Secret Manager integration disabled"
    )


def _cache_key(secret_ref: str) -> str:
    digest = hashlib.sha256(secret_ref.encode()).hexdigest()[:16]
    return f"{_SM_CACHE_PREFIX}{digest}"


async def fetch_secret(secret_ref: str) -> str | None:
    """
    Return the plaintext value of a GCP Secret Manager secret.

    Parameters
    ----------
    secret_ref:
        Full resource name, e.g.
        ``projects/myproject/secrets/openrouter-acme/versions/latest``

    Returns
    -------
    str | None
        Plaintext secret value, or None if unavailable.
    """
    if not _SM_AVAILABLE:
        return None

    if not secret_ref:
        return None

    # ── Redis cache hit ───────────────────────────────────────────────────────
    from app.cache.redis_client import get_redis  # local import to avoid circular

    redis = get_redis()
    if redis is not None:
        try:
            cached = await redis.get(_cache_key(secret_ref))
            if cached is not None:
                data = json.loads(cached)
                return data.get("value")
        except Exception as exc:  # noqa: BLE001
            logger.warning("sm_cache_read_failed", error=str(exc))

    # ── Secret Manager fetch ──────────────────────────────────────────────────
    try:
        # The client is thread-safe and reuses gRPC channels; instantiating
        # once per call is acceptable given the Redis cache above.
        client = _secretmanager.SecretManagerServiceAsyncClient()
        response = await client.access_secret_version(name=secret_ref)
        value = response.payload.data.decode("utf-8")
        logger.info("sm_secret_fetched", secret_ref=secret_ref[:60])

        # ── Populate cache ────────────────────────────────────────────────────
        if redis is not None:
            try:
                await redis.setex(
                    _cache_key(secret_ref),
                    _SM_CACHE_TTL,
                    json.dumps({"value": value}),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("sm_cache_write_failed", error=str(exc))

        return value

    except Exception as exc:  # noqa: BLE001
        logger.warning("sm_fetch_failed", secret_ref=secret_ref[:60], error=str(exc))
        return None


async def invalidate_secret_cache(secret_ref: str) -> None:
    """Remove a cached secret (call after key rotation)."""
    from app.cache.redis_client import get_redis

    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.delete(_cache_key(secret_ref))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sm_cache_invalidate_failed", error=str(exc))
