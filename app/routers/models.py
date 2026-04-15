"""
Models API — GET /v1/models

Returns only models registered in the `models` table (is_enabled=true),
joined with their default pricing row from `model_prices`.

This is a pure DB read — no upstream provider calls are made.
The result is cached in Redis for 5 minutes (short TTL acceptable because
the data source is an in-house Postgres instance, not an external API).
Discount enrichment is applied per-request from the `discounts` table
and is never cached (user-specific).

Endpoints
---------
GET /v1/models              List all enabled models (auth required)
GET /v1/models/free         List only free-tier models
GET /v1/models/paid         List only paid models
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_any_auth_owner
from app.cache.redis_client import get_redis
from app.db.engine import get_session_factory
from app.db.models import Discount, Model, ModelPrice
from app.db.session import get_db_session

router = APIRouter(tags=["models"])
logger = structlog.get_logger()

# In-house DB — 5-minute TTL is a safe balance between freshness and DB load.
# Admin writes to `models` or `model_prices` invalidate this key immediately.
_MODELS_CACHE_KEY = "routerv:models:list"
_MODELS_CACHE_TTL = 300  # 5 minutes


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

def _per_1m(per_1k: Decimal | None) -> str | None:
    """Convert a per-1K price to per-1M. Pure Decimal arithmetic — no precision loss."""
    if per_1k is None:
        return None
    return str((per_1k * 1000).quantize(Decimal("0.00000001")))


class ModelPricing(BaseModel):
    prompt_usd_per_1k: str | None
    completion_usd_per_1k: str | None
    prompt_usd_per_1m: str | None = None
    completion_usd_per_1m: str | None = None
    image_usd_per_image: str | None = None
    # Set when caller has an active discount for this model
    discount_pct: str | None = None
    prompt_usd_per_1k_discounted: str | None = None
    completion_usd_per_1k_discounted: str | None = None
    prompt_usd_per_1m_discounted: str | None = None
    completion_usd_per_1m_discounted: str | None = None


class ModelOut(BaseModel):
    id: str
    name: str
    context_length: int | None
    is_free: bool
    pricing: ModelPricing
    description: str | None = None
    supports_thinking: bool
    supports_completions_api: bool
    supports_responses_api: bool
    model_type: str
    input_modalities: list[str]
    output_modalities: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_model_out(m: Model, mp: ModelPrice) -> ModelOut:
    """Map a (Model, ModelPrice) ORM pair to the public ModelOut schema."""
    if mp.is_free:
        pricing = ModelPricing(
            prompt_usd_per_1k="0",
            completion_usd_per_1k="0",
            prompt_usd_per_1m="0",
            completion_usd_per_1m="0",
        )
    else:
        pricing = ModelPricing(
            prompt_usd_per_1k=str(mp.prompt_usd_per_1k),
            completion_usd_per_1k=str(mp.completion_usd_per_1k),
            prompt_usd_per_1m=_per_1m(mp.prompt_usd_per_1k),
            completion_usd_per_1m=_per_1m(mp.completion_usd_per_1k),
        )

    return ModelOut(
        id=m.model_id,
        name=m.name,
        context_length=m.context_length,
        is_free=mp.is_free,
        pricing=pricing,
        description=m.description,
        supports_thinking=mp.supports_thinking,
        supports_completions_api=mp.supports_completions_api,
        supports_responses_api=mp.supports_responses_api,
        model_type=m.model_type,
        input_modalities=m.input_modalities,
        output_modalities=m.output_modalities,
    )


async def _get_models() -> list[ModelOut]:
    """
    Return enabled models joined with their default pricing row.

    Cache hit  → deserialise from Redis (5-min TTL).
    Cache miss → query Postgres, populate cache, return results.
    DB failure → return empty list (never 500 the caller for a listing).

    Discounts are NOT included here — they are applied per-user at request
    time by _apply_discounts() and must not be cached.
    """
    redis = get_redis()

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if redis is not None:
        try:
            cached = await redis.get(_MODELS_CACHE_KEY)
            if cached is not None:
                return [ModelOut(**m) for m in json.loads(cached)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("models_cache_read_failed", error=str(exc))

    # ── DB query ──────────────────────────────────────────────────────────────
    try:
        async with get_session_factory()() as session:
            result = await session.execute(
                select(Model, ModelPrice)
                .join(
                    ModelPrice,
                    (ModelPrice.model_id == Model.model_id)
                    & ModelPrice.is_default.is_(True),
                )
                .where(Model.is_enabled.is_(True))
                .order_by(Model.model_id)
            )
            rows = result.all()

        models = [_row_to_model_out(m, mp) for m, mp in rows]
        logger.info("models_fetched_from_db", count=len(models))

    except Exception as exc:  # noqa: BLE001
        logger.warning("models_db_fetch_failed", error=str(exc))
        return []

    # ── Populate cache ────────────────────────────────────────────────────────
    if redis is not None:
        try:
            await redis.setex(
                _MODELS_CACHE_KEY,
                _MODELS_CACHE_TTL,
                json.dumps([m.model_dump() for m in models]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("models_cache_write_failed", error=str(exc))

    return models


# ── Routes ────────────────────────────────────────────────────────────────────

async def _apply_discounts(
    models: list[ModelOut],
    owner: str,
    db: AsyncSession,
) -> list[ModelOut]:
    """
    Enrich each paid model's pricing with the caller's active discount.

    Fetches all active user-level discounts in a single query and applies
    the best matching one per model (model-specific wins over account-level).
    Free models are skipped.
    """
    now = datetime.now(UTC)

    result_rows = await db.execute(
        select(Discount.model_id, Discount.discount_pct)
        .where(
            or_(Discount.user_id == owner, Discount.user_id == None),
            Discount.valid_from <= now,
            or_(Discount.valid_until.is_(None), Discount.valid_until > now),
            Discount.ended_at.is_(None),
        )
    )
    rows = result_rows.all()
    model_discounts: dict[str, Decimal] = {}
    account_discount: Decimal | None = None
    for model_id, pct in rows:
        if model_id is None:
            account_discount = max(account_discount or Decimal(0), pct)
        else:
            existing = model_discounts.get(model_id)
            model_discounts[model_id] = max(existing or Decimal(0), pct)
    result = []
    for m in models:
        if m.is_free:
            result.append(m)
            continue

        candidates = [v for v in [model_discounts.get(m.id), account_discount] if v is not None]
        if not candidates:
            result.append(m)
            continue
        pct = max(candidates)

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
        m.pricing.prompt_usd_per_1m_discounted = _discounted(m.pricing.prompt_usd_per_1m)
        m.pricing.completion_usd_per_1m_discounted = _discounted(m.pricing.completion_usd_per_1m)
        result.append(m)

    return result


@router.get("/v1/models", response_model=list[ModelOut])
async def list_models(
    free: bool | None = Query(
        default=None,
        description="Filter: true = free models only, false = paid only, omit = all",
    ),
    type: str | None = Query(
        default=None,
        description="Filter by model_type: text, embedding, image, audio, video",
    ),
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List available models with per-user discounted pricing when applicable.

    Only models registered in the `models` table with is_enabled=true are
    returned. Accepts either a dashboard JWT or an API key.
    Includes pricing per 1 000 tokens and a convenience ``is_free`` flag.
    If the caller has an active discount, discounted prices are included.
    Response is cached for 5 minutes; admin writes invalidate the cache immediately.
    """
    models = await _get_models()

    if free is True:
        models = [m for m in models if m.is_free]
    elif free is False:
        models = [m for m in models if not m.is_free]

    if type is not None:
        models = [m for m in models if m.model_type == type]

    return await _apply_discounts(models, owner, db)


@router.get("/v1/models/free", response_model=list[ModelOut])
async def list_free_models(
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Shortcut: list only models with zero prompt + completion cost."""
    models = [m for m in await _get_models() if m.is_free]
    return await _apply_discounts(models, owner, db)


@router.get("/v1/models/paid", response_model=list[ModelOut])
async def list_paid_models(
    owner: str = Depends(get_any_auth_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Shortcut: list only models that have a non-zero cost."""
    models = [m for m in await _get_models() if not m.is_free]
    return await _apply_discounts(models, owner, db)
