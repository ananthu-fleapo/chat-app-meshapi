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
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx
import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.cache.redis_client import get_redis
from app.config import settings
from app.db.engine import get_session_factory
from app.db.models import Discount, ModelPrice
from app.db.session import get_db_session

router = APIRouter(tags=["models"])
logger = structlog.get_logger()

_MODELS_CACHE_KEY = "routerv:models:list"
_MODELS_CACHE_TTL = 300           # 5 minutes — OpenRouter model list

_MODEL_PRICES_CACHE_KEY = "routerv:model_prices"
_MODEL_PRICES_CACHE_TTL = 86_400  # 24 hours — our billing prices


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class ModelPricing(BaseModel):
    prompt_usd_per_1k: str | None
    completion_usd_per_1k: str | None
    image_usd_per_image: str | None = None
    # Set when caller has an active discount for this model
    discount_pct: str | None = None
    prompt_usd_per_1k_discounted: str | None = None
    completion_usd_per_1k_discounted: str | None = None


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


def _parse_model(raw: dict, our_prices: dict[str, dict] | None = None) -> ModelOut:
    """
    Parse a raw OpenRouter model dict into ModelOut.

    our_prices — optional dict keyed by model_id from our model_prices table.
    When a row exists for this model, our prices + is_free flag override the
    OpenRouter values so that what users see matches what they are billed.
    """
    pricing = raw.get("pricing") or {}
    model_id = raw["id"]

    # OpenRouter reports price per token; multiply by 1 000 to get per-1k.
    def _per_1k(field: str) -> str | None:
        val = pricing.get(field)
        if val is None:
            return None
        try:
            return str(Decimal(val) * 1000)
        except (InvalidOperation, TypeError):
            return str(val)

    our = (our_prices or {}).get(model_id)
    if our:
        return ModelOut(
            id=model_id,
            name=raw.get("name", model_id),
            context_length=raw.get("context_length"),
            is_free=our["is_free"],
            pricing=ModelPricing(
                prompt_usd_per_1k=our["prompt"] if not our["is_free"] else "0",
                completion_usd_per_1k=our["completion"] if not our["is_free"] else "0",
                image_usd_per_image=_per_1k("image") if pricing.get("image") else None,
            ),
            description=raw.get("description"),
        )

    return ModelOut(
        id=model_id,
        name=raw.get("name", model_id),
        context_length=raw.get("context_length"),
        is_free=_is_free(pricing),
        pricing=ModelPricing(
            prompt_usd_per_1k=_per_1k("prompt"),
            completion_usd_per_1k=_per_1k("completion"),
            image_usd_per_image=_per_1k("image") if pricing.get("image") else None,
        ),
        description=raw.get("description"),
    )


async def _get_model_prices() -> dict[str, dict]:
    """
    Return our model_prices table as {model_id: {prompt, completion, is_free}}.
    Cached in Redis for 24 hours; falls back to DB on cache miss or Redis error.
    """
    redis = get_redis()
    if redis is not None:
        try:
            cached = await redis.get(_MODEL_PRICES_CACHE_KEY)
            if cached is not None:
                return json.loads(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("model_prices_cache_read_failed", error=str(exc))

    try:
        async with get_session_factory()() as session:
            result = await session.execute(select(ModelPrice))
            rows = result.scalars().all()
        prices = {
            r.model_id: {
                "prompt": str(r.prompt_usd_per_1k),
                "completion": str(r.completion_usd_per_1k),
                "is_free": r.is_free,
            }
            for r in rows
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("model_prices_db_fetch_failed", error=str(exc))
        return {}

    if redis is not None:
        try:
            await redis.setex(_MODEL_PRICES_CACHE_KEY, _MODEL_PRICES_CACHE_TTL, json.dumps(prices))
        except Exception as exc:  # noqa: BLE001
            logger.warning("model_prices_cache_write_failed", error=str(exc))

    return prices


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


def _is_internal_model(model_id: str) -> bool:
    """
    Return True for models that reveal our upstream provider identity.

    Users should not see openrouter/* routing shortcuts (openrouter/auto,
    openrouter/free) — these would expose that OpenRouter is our backend.
    """
    return model_id.startswith("openrouter/")


async def _get_models() -> list[ModelOut]:
    """
    Return the parsed model list, using Redis cache when available.

    Cache miss or Redis unavailable → fetch from OpenRouter → populate cache.
    On OpenRouter failure with a warm cache → return cached data (stale-while-error).
    On total failure → return empty list (never 500 the caller for a models listing).

    Pricing is sourced from our model_prices table (24 hr Redis cache) so
    that what users see matches what they are billed.  OpenRouter metadata
    (name, context_length, description) is still taken from the live list.

    Internal OpenRouter routing models (openrouter/*) are filtered out so
    they are never exposed to RouterV users.
    """
    redis = get_redis()
    our_prices = await _get_model_prices()

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if redis is not None:
        try:
            cached = await redis.get(_MODELS_CACHE_KEY)
            if cached is not None:
                raw_list = json.loads(cached)
                return [
                    _parse_model(m, our_prices) for m in raw_list
                    if not _is_internal_model(m.get("id", ""))
                ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("models_cache_read_failed", error=str(exc))

    # ── OpenRouter fetch ──────────────────────────────────────────────────────
    try:
        raw_list = await _fetch_from_openrouter()
        logger.info("models_fetched_from_upstream", count=len(raw_list))

        # Populate cache with the full list (filter at read time so cache
        # stays complete in case the filter logic changes).
        if redis is not None:
            try:
                await redis.setex(
                    _MODELS_CACHE_KEY,
                    _MODELS_CACHE_TTL,
                    json.dumps(raw_list),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("models_cache_write_failed", error=str(exc))

        return [
            _parse_model(m, our_prices) for m in raw_list
            if not _is_internal_model(m.get("id", ""))
        ]

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

async def _apply_discounts(
    models: list[ModelOut],
    owner: str,
    db: AsyncSession,
) -> list[ModelOut]:
    """
    Enrich each paid model's pricing with the caller's active discount.

    Fetches all active discounts for the owner in a single query, then applies
    them in memory — model-level overrides account-level (non-stackable).
    Free models are skipped.
    """
    now = datetime.now(UTC)

    result_rows = await db.execute(
        select(Discount.model_id, Discount.discount_pct)
        .where(
            Discount.user_id == owner,
            Discount.is_active.is_(True),
            Discount.valid_from <= now,
            or_(Discount.valid_until.is_(None), Discount.valid_until > now),
        )
    )
    model_discounts: dict[str, Decimal] = {}
    account_discount: Decimal | None = None
    for model_id, pct in result_rows.all():
        if model_id is None:
            account_discount = pct
        else:
            model_discounts[model_id] = pct

    result = []
    for m in models:
        if m.is_free:
            result.append(m)
            continue

        pct = model_discounts.get(m.id) or account_discount
        if pct is None:
            result.append(m)
            continue

        multiplier = 1 - pct / 100

        def _discounted(val: str | None) -> str | None:
            if val is None:
                return None
            try:
                return str((Decimal(val) * multiplier).quantize(Decimal("0.00000001")))
            except InvalidOperation:
                return val

        m.pricing.discount_pct = str(pct)
        m.pricing.prompt_usd_per_1k_discounted = _discounted(m.pricing.prompt_usd_per_1k)
        m.pricing.completion_usd_per_1k_discounted = _discounted(m.pricing.completion_usd_per_1k)
        result.append(m)

    return result


@router.get("/v1/models", response_model=list[ModelOut])
async def list_models(
    free: bool | None = Query(
        default=None,
        description="Filter: true = free models only, false = paid only, omit = all",
    ),
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List available models with per-user discounted pricing when applicable.

    Requires a valid dashboard session (Supabase JWT).
    Includes pricing per 1 000 tokens and a convenience ``is_free`` flag.
    If the caller has an active discount, discounted prices are included.
    Response is cached for 5 minutes.
    """
    models = await _get_models()

    if free is True:
        models = [m for m in models if m.is_free]
    elif free is False:
        models = [m for m in models if not m.is_free]

    return await _apply_discounts(models, identity.owner, db)


@router.get("/v1/models/free", response_model=list[ModelOut])
async def list_free_models(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Shortcut: list only models with zero prompt + completion cost."""
    models = [m for m in await _get_models() if m.is_free]
    return await _apply_discounts(models, identity.owner, db)


@router.get("/v1/models/paid", response_model=list[ModelOut])
async def list_paid_models(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Shortcut: list only models that have a non-zero cost."""
    models = [m for m in await _get_models() if not m.is_free]
    return await _apply_discounts(models, identity.owner, db)
