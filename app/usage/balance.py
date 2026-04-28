"""
User balance management.

check_balance(owner, model, db)
    Pre-inference check. Raises PaymentRequiredError (402) if:
      - model is paid (not free in model_prices) AND
      - user's balance is <= 0

    Free models always pass regardless of balance.
    Models not in model_prices are treated as paid (safe default).

deduct_balance(owner, cost_usd, *, usage_event_id)
    Post-inference deduction. Atomically decrements user_balances.balance_usd
    and appends a BalanceLedger row. Opens its own DB session — safe to call
    from background tasks. Silently logs on failure — never raises.

credit_balance(user_id, amount_usd, db, *, payment_event_id)
    Upserts user_balances, adding amount_usd to the current balance, and
    appends a BalanceLedger row within the caller's session.
    Called by the payment webhook handler.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import and_, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import UTC, datetime

from app.db.engine import get_session_factory
from app.db.models import BalanceLedger, Discount, ModelPrice, UserBalance
from app.exceptions import PaymentRequiredError
from app.pricing.resolver import PriceRow, get_default_price_row

logger = structlog.get_logger()


async def _lookup_model_price(model: str, db: AsyncSession) -> PriceRow | None:
    """
    Look up a price row with :free-suffix abuse prevention.

    Lookup order:
      1. Exact match on model — covers all normal cases.
      2. If model ends with ':free' and no exact row exists, check the base
         name (strip suffix).  If the base name IS a paid model it means the
         caller appended ':free' to bypass billing — return the paid row so
         the request is priced correctly.  If the base name is also free /
         unknown, return None (allow through).

    This keeps OpenRouter's legitimate ':free' variants working (they have
    their own exact rows in the price table) while closing the abuse vector.
    Routes to model_prices or model_pricing based on settings.pricing_v2.
    """
    row = await get_default_price_row(model, db)
    if row is not None:
        return row

    if model.endswith(":free"):
        base = model.removesuffix(":free")
        base_row = await get_default_price_row(base, db)
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


async def deduct_balance(
    owner: str,
    cost_usd: Decimal,
    *,
    usage_event_id: uuid.UUID | None = None,
) -> None:
    """
    Atomically deduct cost_usd from user_balances and append a ledger row.

    Fire-and-forget — opens its own session, never raises.
    """
    if cost_usd <= 0:
        return
    try:
        async with get_session_factory()() as session:
            # Lock row and read current balance for snapshot.
            result = await session.execute(
                select(UserBalance)
                .where(UserBalance.user_id == owner)
                .with_for_update()
            )
            existing = result.scalar_one_or_none()
            balance_before = existing.balance_usd if existing is not None else Decimal("0")
            balance_after = balance_before - cost_usd

            await session.execute(
                insert(UserBalance)
                .values(user_id=owner, balance_usd=balance_after)
                .on_conflict_do_update(
                    index_elements=["user_id"],
                    set_={"balance_usd": balance_after, "updated_at": text("now()")},
                )
            )
            session.add(BalanceLedger(
                user_id=owner,
                txn_type="debit",
                amount_usd=cost_usd,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_id=usage_event_id,
                reference_type="usage_event" if usage_event_id is not None else None,
            ))
            await session.commit()
        logger.debug(
            "balance_deducted",
            owner=owner,
            cost_usd=str(cost_usd),
            balance_before=str(balance_before),
            balance_after=str(balance_after),
            usage_event_id=str(usage_event_id) if usage_event_id is not None else None,
        )
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


async def credit_balance(
    user_id: str,
    amount_usd: Decimal,
    db: AsyncSession,
    *,
    payment_event_id: uuid.UUID | None = None,
) -> None:
    """
    Add amount_usd to user_balances and append a ledger row.

    Uses SELECT FOR UPDATE to capture balance_before, then upserts.
    Caller's session commits — the ledger row and balance update are atomic.
    """
    result = await db.execute(
        select(UserBalance)
        .where(UserBalance.user_id == user_id)
        .with_for_update()
    )
    existing = result.scalar_one_or_none()
    balance_before = existing.balance_usd if existing is not None else Decimal("0")
    balance_after = balance_before + amount_usd

    stmt = (
        insert(UserBalance)
        .values(user_id=user_id, balance_usd=balance_after)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"balance_usd": balance_after, "updated_at": text("now()")},
        )
    )
    await db.execute(stmt)
    db.add(BalanceLedger(
        user_id=user_id,
        txn_type="credit",
        amount_usd=amount_usd,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_id=payment_event_id,
        reference_type="payment_event" if payment_event_id is not None else None,
    ))
    logger.info(
        "balance_credited",
        user_id=user_id,
        amount_usd=str(amount_usd),
        balance_before=str(balance_before),
        balance_after=str(balance_after),
        payment_event_id=str(payment_event_id) if payment_event_id is not None else None,
    )
