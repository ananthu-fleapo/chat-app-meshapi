"""
FX rates router — POST /internal/fx-rates/refresh

Called by an external scheduler to pull the latest USD→INR exchange rate
from exchangerate-api.com, apply a 0.2 % markup, and upsert the result
into currency_conversion_rates.

Auth
----
Requires: Authorization: Bearer <WEBHOOK_API_KEY>
Same static-secret guard used by the payment webhook.

Stored fields
-------------
rate        Raw INR-per-USD rate from the external API  (e.g. 93.8571)
markup_fee  0.2 % of rate  (rate * 0.002)
total_rate  Effective INR-per-USD rate charged to callers  (rate + markup_fee)
"""

from decimal import ROUND_DOWN, Decimal

import httpx
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import verify_webhook_key
from app.config import settings
from app.db.models import CurrencyConversionRate
from app.db.session import get_db_session
from app.exceptions import RouterVError

router = APIRouter(prefix="/v1/fx-rates", tags=["fx-rates"])
logger = structlog.get_logger()

_BASE_CURRENCY = "INR"
_MARKUP_PCT = Decimal("0.002")  # 0.2 %
_PRECISION = Decimal("0.0001")  # 4 decimal places


class FxRefreshResponse(BaseModel):
    currency: str
    rate: str
    markup_fee: str
    total_rate: str


@router.get("", response_model=FxRefreshResponse)
async def get_fx_rates(
    db: AsyncSession = Depends(get_db_session),
) -> FxRefreshResponse:
    """
    Return the current INR→USD conversion rate stored in the DB.
    Used by the frontend to show estimated USD credit for a given INR amount.
    """
    result = await db.execute(
        select(CurrencyConversionRate)
        .where(CurrencyConversionRate.currency == _BASE_CURRENCY)
        .order_by(CurrencyConversionRate.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()

    if row is None:
        raise RouterVError(
            status_code=404,
            error_code="fx_rate_not_found",
            message="FX rate not yet available. Please try again later.",
        )

    return FxRefreshResponse(
        currency=row.currency,
        rate=str(row.rate),
        markup_fee=str(row.markup_fee),
        total_rate=str(row.total_rate),
    )


@router.post("/refresh", response_model=FxRefreshResponse)
async def refresh_fx_rates(
    _: None = Depends(verify_webhook_key),
    db: AsyncSession = Depends(get_db_session),
) -> FxRefreshResponse:
    """
    Fetch the latest USD/INR rate, apply 0.2 % markup, and upsert the row.

    Called by an external scheduler (Cloud Scheduler, cron, etc.).
    Returns the values that were written so the caller can log/verify them.
    """
    # ── 1. Fetch rate from external API ──────────────────────────────────────
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(settings.exchange_rate_api_url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("fx_rate_fetch_failed", error=str(exc))
            raise RouterVError(
                status_code=502,
                error_code="fx_fetch_error",
                message=f"Failed to fetch exchange rate: {exc}",
            ) from exc

    payload = resp.json()
    if payload.get("result") != "success":
        logger.error("fx_rate_api_error", payload=payload)
        raise RouterVError(
            status_code=502,
            error_code="fx_api_error",
            message="Exchange rate API returned an error response.",
        )

    # ── 2. Derive stored values ───────────────────────────────────────────────
    # rate: exact INR-per-USD value from the API (e.g. 93.8571)
    # markup_fee: 0.2 % of rate
    # total_rate: effective INR-per-USD rate applied when crediting payments
    rate = Decimal(str(payload["conversion_rates"][_BASE_CURRENCY])).quantize(
        _PRECISION, rounding=ROUND_DOWN
    )
    markup_fee = (rate * _MARKUP_PCT).quantize(_PRECISION, rounding=ROUND_DOWN)
    total_rate = (rate + markup_fee).quantize(_PRECISION, rounding=ROUND_DOWN)

    logger.info(
        "fx_rate_computed",
        rate=str(rate),
        markup_fee=str(markup_fee),
        total_rate=str(total_rate),
    )

    # ── 3. Insert new snapshot row ────────────────────────────────────────────
    row = CurrencyConversionRate(
        currency=_BASE_CURRENCY,
        rate=rate,
        markup_fee=markup_fee,
        total_rate=total_rate,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info("fx_rate_updated", currency=_BASE_CURRENCY, total_rate=str(total_rate))

    return FxRefreshResponse(
        currency=_BASE_CURRENCY,
        rate=str(rate),
        markup_fee=str(markup_fee),
        total_rate=str(total_rate),
    )
