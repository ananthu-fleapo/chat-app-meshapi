"""
Auto Router registry — fetches and caches candidate models per API type.

Two-level cache:
  L1  routerv:models:autorouter:{type}  — filtered list for this API type (300s TTL)
  L2  routerv:models:list               — full model list (managed by models router)

Warm path: single Redis GET.
Cold path: L2 hit (or DB) → in-memory filter → populate L1.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

import structlog

from app.cache.redis_client import get_redis

logger = structlog.get_logger()

AUTOROUTER_CACHE_TTL = 300  # seconds — matches models list TTL

# Separate Redis keys per API type so the auto-router never deserialises the
# full model list on every request — only the relevant filtered subset.
AUTOROUTER_CACHE_KEYS: dict[str, str] = {
    "completions": "routerv:models:autorouter:completions",
    "responses":   "routerv:models:autorouter:responses",
    "embeddings":  "routerv:models:autorouter:embeddings",
}

ApiType = Literal["completions", "responses", "embeddings"]


@dataclass
class CandidateModel:
    model_id: str
    name: str
    description: str  # pre-truncated to 80 chars at cache-population time


def _supports(model, api_type: ApiType) -> bool:
    """Return True if a ModelOut supports the given API type."""
    return {
        "completions": getattr(model, "supports_completions_api", False),
        "responses":   getattr(model, "supports_responses_api", False),
        "embeddings":  getattr(model, "supports_embeddings_api", False),
    }.get(api_type, False)


async def get_enabled_models(api_type: ApiType) -> list[CandidateModel]:
    """
    Return the list of enabled models that support *api_type*.

    The result is cached in Redis under AUTOROUTER_CACHE_KEYS[api_type].
    On a cache miss the full model list is fetched via _get_models() (which has
    its own Redis + DB fallback) and then filtered in memory.
    """
    # Deferred import to avoid circular dependency at module load time.
    from app.routers.models import _get_models

    cache_key = AUTOROUTER_CACHE_KEYS[api_type]
    redis = get_redis()

    # ── L1: per-api-type autorouter cache ────────────────────────────────────
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached is not None:
                return [CandidateModel(**m) for m in json.loads(cached)]
        except Exception as exc:
            logger.warning("autorouter_cache_read_failed", api_type=api_type, error=str(exc))

    # ── L2: full model list (own Redis + DB fallback) ─────────────────────────
    all_models = await _get_models()
    candidates = [
        CandidateModel(
            model_id=m.id,
            name=m.name,
            description=(m.description or "")[:80],
        )
        for m in all_models
        if _supports(m, api_type)
    ]

    # ── Populate L1 ───────────────────────────────────────────────────────────
    if redis is not None:
        try:
            await redis.setex(
                cache_key,
                AUTOROUTER_CACHE_TTL,
                json.dumps([asdict(c) for c in candidates]),
            )
        except Exception as exc:
            logger.warning("autorouter_cache_write_failed", api_type=api_type, error=str(exc))

    return candidates
