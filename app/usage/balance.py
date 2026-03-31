"""
User balance management.

check_balance(owner, model, db)
    Pre-inference check. Raises PaymentRequiredError (402) if:
      - model is paid (not free in model_prices) AND
      - user's balance is <= 0

    Free models always pass regardless of balance.
    Models not in model_prices are treated as paid (safe default).

deduct_balance(owner, cost_usd)
    Post-inference deduction. Atomically decrements user_balances.balance_usd.
    Opens its own DB session — safe to call from background tasks.
    Silently logs on failure — never raises (must not affect response delivery).

credit_balance(user_id, amount_usd, db)
    Upserts user_balances, adding amount_usd to the current balance.
    Called by the payment webhook handler.
"""

from __future__ import annotations

from decimal import Decimal

import structlog
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import UTC, datetime

from app.db.engine import get_session_factory
from app.db.models import Discount, ModelPrice, UserBalance
from app.exceptions import PaymentRequiredError

logger = structlog.get_logger()


async def _is_model_free(model: str, db: AsyncSession) -> bool:
    """
    Return True when the model should not be billed.

    - is_free=True in model_prices → free
    - not in model_prices → free (no price configured = no charge)
    - is_free=False in model_prices → paid, requires balance
    """
    result = await db.execute(
        select(ModelPrice.is_free).where(ModelPrice.model_id == model)
    )
    row = result.one_or_none()
    if row is None:
        # Model not in price table — allow through (admin hasn't priced it yet).
        return True
    return row[0]


async def check_balance(owner: str, model: str, db: AsyncSession) -> None:
    """
    Raise PaymentRequiredError if the user has no balance and the model is paid.

    Parameters
    ----------
    owner   ApiKey.owner — used as user_balances.user_id lookup key.
    model   Requested model identifier.
    db      Active request DB session.
    """
    if await _is_model_free(model, db):
        return

    result = await db.execute(
        select(UserBalance.balance_usd).where(UserBalance.user_id == owner)
    )
    row = result.one_or_none()
    balance = row[0] if row else Decimal("0")

    logger.debug("balance_check", owner=owner, model=model, balance=str(balance))

    if balance <= 0:
        from app.metrics import BALANCE_BLOCKS
        BALANCE_BLOCKS.inc()
        raise PaymentRequiredError(
            "Insufficient balance. Top up your account to use paid models."
        )


async def deduct_balance(owner: str, cost_usd: Decimal) -> None:
    """
    Atomically deduct cost_usd from user_balances.

    Fire-and-forget — opens its own session, never raises.
    """
    if cost_usd <= 0:
        return
    try:
        async with get_session_factory()() as session:
            await session.execute(
                text(
                    "UPDATE user_balances "
                    "SET balance_usd = balance_usd - :cost, updated_at = now() "
                    "WHERE user_id = :owner"
                ),
                {"cost": cost_usd, "owner": owner},
            )
            await session.commit()
        logger.debug("balance_deducted", owner=owner, cost_usd=str(cost_usd))
    except Exception as exc:  # noqa: BLE001
        logger.error("balance_deduct_failed", owner=owner, cost_usd=str(cost_usd), error=str(exc))


async def get_active_discount(owner: str, model: str, db: AsyncSession) -> Decimal | None:
    """
    Return the discount_pct for this owner + model, or None if no active discount.

    Precedence (non-stackable):
      1. Model-level discount  (user_id=owner, model_id=model)
      2. Account-level discount (user_id=owner, model_id=NULL)

    A discount is active when:
      - is_active = True
      - valid_from <= now
      - valid_until IS NULL OR valid_until >= now
    """
    now = datetime.now(UTC)

    for model_filter in [model, None]:
        condition = [
            Discount.user_id == owner,
            Discount.is_active.is_(True),
            Discount.valid_from <= now,
        ]
        if model_filter is not None:
            condition.append(Discount.model_id == model_filter)
        else:
            condition.append(Discount.model_id.is_(None))

        result = await db.execute(
            select(Discount.discount_pct).where(*condition).limit(1)
        )
        row = result.one_or_none()
        if row is not None:
            # Check valid_until in Python (handles None cleanly)
            discount_row = await db.execute(
                select(Discount).where(*condition).limit(1)
            )
            d = discount_row.scalar_one_or_none()
            if d and (d.valid_until is None or d.valid_until.replace(tzinfo=UTC) >= now):
                logger.debug(
                    "discount_applied",
                    owner=owner,
                    model=model,
                    scope="model" if model_filter else "account",
                    pct=str(d.discount_pct),
                )
                return d.discount_pct

    return None


async def credit_balance(user_id: str, amount_usd: Decimal, db: AsyncSession) -> None:
    """
    Add amount_usd to user_balances, creating the row if it doesn't exist.

    Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for atomicity.
    """
    stmt = (
        insert(UserBalance)
        .values(user_id=user_id, balance_usd=amount_usd)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"balance_usd": UserBalance.balance_usd + amount_usd, "updated_at": text("now()")},
        )
    )
    await db.execute(stmt)
    logger.info("balance_credited", user_id=user_id, amount_usd=str(amount_usd))
