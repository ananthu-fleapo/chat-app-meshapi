"""
API key cache — cache-aside pattern on top of Redis.

Stores a minimal projection of ApiKey (only fields needed at request time)
as JSON. The ORM model is reconstructed from the cached dict on a cache hit,
so no database round-trip is needed for auth on warm requests.

TTL
---
60 seconds (KEY_CACHE_TTL). Short enough that a key suspended via the admin
API propagates within a minute. Admin PATCH/DELETE also calls
invalidate_cached_key() for immediate propagation.

Key schema
----------
    routerv:key:{key_hash}   →  JSON string

Failure policy
--------------
All Redis calls are wrapped in try/except. On any Redis error the caller
falls back to Postgres — degraded performance, correct behaviour.
"""

import json
import uuid
from decimal import Decimal

import structlog

from app.cache.redis_client import get_redis
from app.db.models import ApiKey

logger = structlog.get_logger()

_PREFIX = "routerv:key:"
KEY_CACHE_TTL = 60  # seconds — configurable here, not in Settings for now


def _rk(key_hash: str) -> str:
    return f"{_PREFIX}{key_hash}"


# ── Serialization ─────────────────────────────────────────────────────────────

def _serialize(key: ApiKey) -> str:
    """
    Serialize only the fields needed at runtime.
    spend_cap_usd stored as string to survive JSON round-trip without loss.
    """
    return json.dumps({
        "id": str(key.id),
        "key_hash": key.key_hash,
        "owner": key.owner,
        "status": key.status,
        "default_model": key.default_model,
        "default_params": key.default_params,
        "rpm_limit": key.rpm_limit,
        "rpd_limit": key.rpd_limit,
        "spend_cap_usd": str(key.spend_cap_usd) if key.spend_cap_usd is not None else None,
        "tpm_limit": key.tpm_limit,
        "allowed_models": key.allowed_models,
        "model_limits": key.model_limits,
    })


def _deserialize(raw: str) -> ApiKey:
    """
    Reconstruct a detached (session-less) ApiKey instance from cached JSON.
    The instance is read-only — it is never added to a session.
    """
    data = json.loads(raw)
    key = ApiKey(
        id=uuid.UUID(data["id"]),
        key_hash=data["key_hash"],
        owner=data["owner"],
        status=data["status"],
        default_model=data.get("default_model"),
        default_params=data.get("default_params"),
        rpm_limit=data.get("rpm_limit"),
        rpd_limit=data.get("rpd_limit"),
        spend_cap_usd=Decimal(data["spend_cap_usd"]) if data.get("spend_cap_usd") else None,
        tpm_limit=data.get("tpm_limit"),
        allowed_models=data.get("allowed_models"),
        model_limits=data.get("model_limits"),
    )
    return key


# ── Public API ────────────────────────────────────────────────────────────────

async def get_cached_key(key_hash: str) -> ApiKey | None:
    """
    Return a cached ApiKey for key_hash, or None on miss / Redis error.
    """
    try:
        raw = await get_redis().get(_rk(key_hash))
        if raw is None:
            return None
        return _deserialize(raw)
    except Exception as exc:
        logger.warning("redis_unavailable", source="key_cache_get", error=str(exc))
        return None  # fall back to Postgres


async def set_cached_key(key: ApiKey) -> None:
    """
    Cache the key with KEY_CACHE_TTL. Silently ignores Redis errors.
    """
    try:
        await get_redis().setex(_rk(key.key_hash), KEY_CACHE_TTL, _serialize(key))
    except Exception as exc:
        logger.warning("redis_unavailable", source="key_cache_set", error=str(exc))


async def invalidate_cached_key(key_hash: str) -> None:
    """
    Immediately evict the cache entry. Called from admin PATCH / DELETE
    so changes propagate instantly rather than waiting for TTL expiry.
    """
    try:
        await get_redis().delete(_rk(key_hash))
        logger.debug("key_cache_invalidated", key_hash=key_hash[:16] + "...")
    except Exception as exc:
        logger.warning("redis_unavailable", source="key_cache_invalidate", error=str(exc))
