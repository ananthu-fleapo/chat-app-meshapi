"""Reusable SQLAlchemy column expressions for payment USD conversions.

These expressions reference PaymentEvent columns via correlated subqueries,
so they must only be used inside a query that selects from payment_events
(or a join that includes it).
"""

from __future__ import annotations

from sqlalchemy import case, func, select

from app.db.models import CurrencyConversionRate, PaymentEvent


def fx_rate_subquery():
    """Scalar correlated subquery: the FX rate in effect at each payment's created_at.

    Looks up the most recent currency_conversion_rates row whose created_at is
    at or before the payment row's created_at, matching on currency.  Uses the
    composite index ix_currency_conversion_rates_currency_created for efficient
    per-row lookups.

    Returns NULL when no rate exists for the currency (e.g. USD rows that need
    no conversion).  Callers should wrap with func.coalesce(..., 1.0) to treat
    those as a 1:1 rate.
    """
    return (
        select(CurrencyConversionRate.total_rate)
        .where(CurrencyConversionRate.currency == PaymentEvent.currency)
        .where(CurrencyConversionRate.created_at <= PaymentEvent.created_at)
        .order_by(CurrencyConversionRate.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )


def usd_amount_expr():
    """SQLAlchemy expression: gross USD value of a payment_events row.

    Priority:
      1. amount_usd column (pre-computed in cents at webhook ingestion time) —
         most accurate; captures the exact rate and GST deduction applied at
         payment time.
      2. Fallback for older rows where amount_usd IS NULL: divide the raw
         amount by the FX rate returned by fx_rate_subquery().  For already-USD
         rows the subquery returns NULL, which coalesce maps to 1.0 (no-op).
    """
    rate_sq = fx_rate_subquery()
    return case(
        (PaymentEvent.amount_usd.isnot(None), PaymentEvent.amount_usd / 100.0),
        else_=func.coalesce(PaymentEvent.amount, 0) / 100.0 / func.coalesce(rate_sq, 1.0),
    )


def discount_usd_expr():
    """SQLAlchemy expression: coupon discount value in USD for a payment_events row.

    Uses fx_rate_subquery() for FX conversion.  Returns 0.0 for rows with no
    discount_amount set.
    """
    rate_sq = fx_rate_subquery()
    return case(
        (
            PaymentEvent.discount_amount.isnot(None),
            PaymentEvent.discount_amount / 100.0 / func.coalesce(rate_sq, 1.0),
        ),
        else_=0.0,
    )
