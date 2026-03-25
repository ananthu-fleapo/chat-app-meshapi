"""
Models API — GET /v1/models

Returns the list of models available through the upstream provider (OpenRouter),
augmented with a ``is_free`` flag.  The response is cached in Redis for
``MODELS_CACHE_TTL`` seconds to avoid hammering the OpenRouter models endpoint.

OpenRouter model pricing format:
  "pricing": {"prompt": "0.000005", "completion": "0.000015", ...}

A model is considered free when both prompt and completion prices are "0".

Endpoint
--------
GET /v1/models        List all models (no auth required — public info)
GET /v1/models/free   List only free-tier models
GET /v1/models/paid   List only paid models
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

import httpx
import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.cache.redis_client import get_redis
from app.config import settings

router = APIRouter(tags=["models"])
logger = structlog.get_logger()

_MODELS_CACHE_KEY = "routerv:models:list"
_MODELS_CACHE_TTL = 300  # seconds — refresh every 5 minutes


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class ModelPricing(BaseModel):
    prompt_usd_per_1k: str | None   # "0.000005" → multiply by 1 000
    completion_usd_per_1k: str | None
    image_usd_per_image: str | None = None


class ModelOut(BaseModel):
    id: str
    name: str
    context_length: int | None
    is_free: bool
    pricing: ModelPricing
    description: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_free(pricing: dict) -> bool:
    """Return True when both prompt and completion are priced at zero."""
    try:
        prompt = Decimal(pricing.get("prompt", "1"))
        completion = Decimal(pricing.get("completion", "1"))
        return prompt == 0 and completion == 0
    except (InvalidOperation, TypeError):
        return False


def _parse_model(raw: dict) -> ModelOut:
    pricing = raw.get("pricing") or {}
    # OpenRouter reports price per token; multiply by 1 000 to get per-1k.
    def _per_1k(field: str) -> str | None:
        val = pricing.get(field)
        if val is None:
            return None
        try:
            return str(Decimal(val) * 1000)
        except (InvalidOperation, TypeError):
            return str(val)

    return ModelOut(
        id=raw["id"],
        name=raw.get("name", raw["id"]),
        context_length=raw.get("context_length"),
        is_free=_is_free(pricing),
        pricing=ModelPricing(
            prompt_usd_per_1k=_per_1k("prompt"),
            completion_usd_per_1k=_per_1k("completion"),
            image_usd_per_image=_per_1k("image") if pricing.get("image") else None,
        ),
        description=raw.get("description"),
    )


async def _fetch_from_openrouter() -> list[dict]:
    """Fetch raw model list from OpenRouter /models endpoint."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{settings.openrouter_base_url}/models",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://routerv.com",
                "X-Title": "RouterV",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])


async def _get_models() -> list[ModelOut]:
    """
    Return the parsed model list, using Redis cache when available.

    Cache miss or Redis unavailable → fetch from OpenRouter → populate cache.
    On OpenRouter failure with a warm cache → return cached data (stale-while-error).
    On total failure → return empty list (never 500 the caller for a models listing).
    """
    redis = get_redis()

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if redis is not None:
        try:
            cached = await redis.get(_MODELS_CACHE_KEY)
            if cached is not None:
                raw_list = json.loads(cached)
                return [_parse_model(m) for m in raw_list]
        except Exception as exc:  # noqa: BLE001
            logger.warning("models_cache_read_failed", error=str(exc))

    # ── OpenRouter fetch ──────────────────────────────────────────────────────
    try:
        raw_list = await _fetch_from_openrouter()
        logger.info("models_fetched_from_upstream", count=len(raw_list))

        # Populate cache
        if redis is not None:
            try:
                await redis.setex(
                    _MODELS_CACHE_KEY,
                    _MODELS_CACHE_TTL,
                    json.dumps(raw_list),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("models_cache_write_failed", error=str(exc))

        return [_parse_model(m) for m in raw_list]

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "models_upstream_http_error",
            status=exc.response.status_code,
            body=exc.response.text[:200],
        )
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("models_upstream_failed", error=str(exc))
        return []


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/v1/models", response_model=list[ModelOut])
async def list_models(
    free: bool | None = Query(
        default=None,
        description="Filter: true = free models only, false = paid only, omit = all",
    ),
):
    """
    List available models from the upstream provider.

    Includes pricing per 1 000 tokens and a convenience ``is_free`` flag.
    Response is cached for 5 minutes — stale data is preferred over
    returning an error if OpenRouter is temporarily unreachable.

    Use ``?free=true`` for free-only models, ``?free=false`` for paid-only.
    """
    models = await _get_models()

    if free is True:
        models = [m for m in models if m.is_free]
    elif free is False:
        models = [m for m in models if not m.is_free]

    return models


@router.get("/v1/models/free", response_model=list[ModelOut])
async def list_free_models():
    """Shortcut: list only models with zero prompt + completion cost."""
    models = await _get_models()
    return [m for m in models if m.is_free]


@router.get("/v1/models/paid", response_model=list[ModelOut])
async def list_paid_models():
    """Shortcut: list only models that have a non-zero cost."""
    models = await _get_models()
    return [m for m in models if not m.is_free]
