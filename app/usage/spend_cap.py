"""
Spend cap enforcement.

Soft-cap model
--------------
We check the accumulated spend at the START of each request, before the
inference call. If the cap is already reached or exceeded, we raise 402.
This means a key's spend can overshoot the cap by at most one request's
cost (the last request that tips it over). This is standard practice —
we don't know completion token count before the call.

Performance note
----------------
Each request issues one aggregate query:
    SELECT COALESCE(SUM(cost_usd), 0) FROM usage_events WHERE key_id = ?

For Phase 5 this is fine (small table, indexed on key_id via the composite
ix_usage_events_key_created index). Phase 7 caches the running total in
Redis and increments it after each logged event — eliminating the DB round-
trip for spend cap checks entirely.

Unknown costs
-------------
Events with cost_usd = NULL (unknown model pricing) are excluded from the
SUM automatically by SQL aggregate semantics. The effective cap is therefore
conservative — we may undercount and allow more spend than intended when
using unpriced models. Phase 7's dynamic pricing fixes this.
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.db.models import UsageEvent
from app.exceptions import PaymentRequiredError

logger = structlog.get_logger()


async def check_spend_cap(
    key_id: str,
    spend_cap_usd: Decimal,
    db: AsyncSession,
) -> None:
    """
    Raise PaymentRequiredError (402) if the key has reached its spend cap.

    Parameters
    ----------
    key_id        UUID string of the ApiKey.
    spend_cap_usd The cap value from key.spend_cap_usd.
    db            Active request DB session (read-only query).
    """
    result = await db.execute(
        select(func.coalesce(func.sum(UsageEvent.cost_usd), 0)).where(
            UsageEvent.key_id == uuid.UUID(key_id)
        )
    )
    total: Decimal = result.scalar_one()

    logger.debug(
        "spend_cap_check",
        key_id=key_id,
        total_usd=str(total),
        cap_usd=str(spend_cap_usd),
    )

    if total >= spend_cap_usd:
        raise PaymentRequiredError(
            f"Spend cap of ${spend_cap_usd:.4f} reached. "
            f"Current spend: ${total:.4f}. "
            f"Contact your administrator to increase the cap."
        )
