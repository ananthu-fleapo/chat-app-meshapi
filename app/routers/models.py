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
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.cache.redis_client import get_redis
from app.config import settings
from app.db.session import get_db_session

router = APIRouter(tags=["models"])
logger = structlog.get_logger()

_MODELS_CACHE_KEY = "routerv:models:list"
_MODELS_CACHE_TTL = 300  # seconds — refresh every 5 minutes


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

    Internal OpenRouter routing models (openrouter/*) are filtered out so
    they are never exposed to RouterV users.
    """
    redis = get_redis()

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if redis is not None:
        try:
            cached = await redis.get(_MODELS_CACHE_KEY)
            if cached is not None:
                raw_list = json.loads(cached)
                return [
                    _parse_model(m) for m in raw_list
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
            _parse_model(m) for m in raw_list
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
    Enrich each model's pricing with the caller's active discount.

    Looks up account-level discount once, then checks model-level per model.
    Model-level takes priority over account-level (non-stackable).
    Free models are skipped — no discount needed when price is already zero.
    """
    from app.usage.balance import get_active_discount

    # Pre-fetch account-level discount (single DB call)
    account_discount = await get_active_discount(owner, "__account__", db)
    # get_active_discount with a dummy model falls through to account-level
    # Fetch it directly instead:
    from datetime import UTC, datetime
    from app.db.models import Discount
    from sqlalchemy import select as sa_select

    now = datetime.now(UTC)
    acct_row = await db.execute(
        sa_select(Discount.discount_pct).where(
            Discount.user_id == owner,
            Discount.model_id.is_(None),
            Discount.is_active.is_(True),
            Discount.valid_from <= now,
        ).limit(1)
    )
    acct_discount_row = acct_row.one_or_none()
    account_pct = Decimal(str(acct_discount_row[0])) if acct_discount_row else None

    result = []
    for m in models:
        if m.is_free:
            result.append(m)
            continue

        # Check model-level discount first
        model_row = await db.execute(
            sa_select(Discount.discount_pct).where(
                Discount.user_id == owner,
                Discount.model_id == m.id,
                Discount.is_active.is_(True),
                Discount.valid_from <= now,
            ).limit(1)
        )
        model_row_val = model_row.one_or_none()
        pct = Decimal(str(model_row_val[0])) if model_row_val else account_pct

        if pct is None:
            result.append(m)
            continue

        # Apply discount to pricing fields
        multiplier = 1 - pct / 100
        def _discount(val: str | None) -> str | None:
            if val is None:
                return None
            try:
                return str((Decimal(val) * multiplier).quantize(Decimal("0.00000001")))
            except InvalidOperation:
                return val

        m.pricing.discount_pct = str(pct)
        m.pricing.prompt_usd_per_1k_discounted = _discount(m.pricing.prompt_usd_per_1k)
        m.pricing.completion_usd_per_1k_discounted = _discount(m.pricing.completion_usd_per_1k)
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
