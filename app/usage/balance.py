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
from sqlalchemy import and_, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import UTC, datetime

from app.db.engine import get_session_factory
from app.db.models import Discount, ModelPrice, UserBalance
from app.exceptions import PaymentRequiredError

logger = structlog.get_logger()


async def _lookup_model_price(model: str, db: AsyncSession) -> ModelPrice | None:
    """
    Look up a ModelPrice row with :free-suffix abuse prevention.

    Lookup order:
      1. Exact match on model — covers all normal cases.
      2. If model ends with ':free' and no exact row exists, check the base
         name (strip suffix).  If the base name IS a paid model it means the
         caller appended ':free' to bypass billing — return the paid row so
         the request is priced correctly.  If the base name is also free /
         unknown, return None (allow through).

    This keeps OpenRouter's legitimate ':free' variants working (they have
    their own exact rows in model_prices) while closing the abuse vector.
    """
    result = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == model,
            ModelPrice.is_default.is_(True),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    if model.endswith(":free"):
        base = model.removesuffix(":free")
        result = await db.execute(
            select(ModelPrice).where(
                ModelPrice.model_id == base,
                ModelPrice.is_default.is_(True),
            )
        )
        base_row = result.scalar_one_or_none()
        # Only return the base row when it is a paid model — that means the
        # ':free' suffix was fabricated to evade the balance check.
        if base_row is not None and not base_row.is_free:
            logger.warning(
                "free_suffix_abuse_detected",
                requested=model,
                resolved=base,
                hint="Billing as paid model",
            )
            return base_row

    return None


async def _is_model_free(model: str, db: AsyncSession) -> bool:
    """
    Return True when the model should not be billed.

    - is_free=True in model_prices → free
    - not in model_prices → free (no price configured = no charge)
    - is_free=False in model_prices → paid, requires balance
    """
    row = await _lookup_model_price(model, db)
    if row is None:
        # Model not in price table — allow through (admin hasn't priced it yet).
        return True
    return row.is_free


async def check_balance(owner: str, model: str, db: AsyncSession) -> bool:
    """
    Raise PaymentRequiredError if the user has no balance and the model is paid.

    Returns True if the model is free (no balance check performed), False if
    the model is paid and the user passed the balance check.  The return value
    is used by the inference router to decide whether to apply the tighter
    free-model rate limit.

    Parameters
    ----------
    owner   ApiKey.owner — used as user_balances.user_id lookup key.
    model   Requested model identifier.
    db      Active request DB session.
    """
    if await _is_model_free(model, db):
        return True  # free model — no balance required

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

    return False  # paid model, balance OK


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
    Return the highest discount_pct for this owner + model, or None if no active discount.

    All three scopes are considered simultaneously (non-stackable):
      - User+Model  (user_id=owner, model_id=model)
      - User account-level (user_id=owner, model_id=NULL)
      - Global model (user_id=NULL, model_id=model)

    The discount with the highest percentage wins.
    Temporal validity (valid_from/valid_until) is enforced in the query.
    """
    now = datetime.now(UTC)

    result = await db.execute(
        select(Discount)
        .where(
            Discount.valid_from <= now,
            or_(Discount.valid_until.is_(None), Discount.valid_until > now),
            Discount.ended_at.is_(None),
            or_(
                and_(Discount.user_id == owner, Discount.model_id == model),
                and_(Discount.user_id == owner, Discount.model_id.is_(None)),
                and_(Discount.user_id.is_(None), Discount.model_id == model),
            ),
        )
        .order_by(Discount.discount_pct.desc())
        .limit(1)
    )
    d = result.scalar_one_or_none()
    if d is None:
        return None

    from structlog.contextvars import bind_contextvars
    bind_contextvars(owner=owner, model=model)
    logger.debug("discount_applied", owner=owner, model=model, pct=str(d.discount_pct))
    return d.discount_pct


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
