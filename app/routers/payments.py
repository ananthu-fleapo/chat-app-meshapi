"""
Payment webhook router — POST /v1/payments, GET /v1/payments/{user_id}

Auth
----
POST  — webhook key guard (verify_webhook_key): static secret from WEBHOOK_API_KEY env.
GET   — Supabase JWT (get_control_plane_user): userId extracted from sub claim.

Endpoints
---------
POST  /v1/payments               Ingest a payment event from a payment provider webhook.
GET   /v1/payments/{user_id}     List all payment events for a given user.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.auth.dependencies import verify_webhook_key
from app.db.models import (
    CheckoutCoupon,
    CouponSyncIssue,
    CurrencyConversionRate,
    GstinRecord,
    PaymentEvent,
)
from app.db.session import get_db_session
from app.usage.balance import credit_balance

from .coupon_utils import _normalize_coupon_code

router = APIRouter(prefix="/v1/payments", tags=["payments"])
logger = structlog.get_logger()


# ── Pydantic I/O ──────────────────────────────────────────────────────────────


class PaymentRequest(BaseModel):
    userId: str
    paymentId: str
    provider: str
    orderId: str | None = None
    couponCode: str | None = None
    couponDiscountAmount: int | None = None
    currency: str | None = None
    amount: int | None = None
    # Geographic context — populated by the webhook service from payment metadata.
    ipAddress: str | None = None
    country: str | None = None
    # GST fields — India-only. gstin is NULL when 18% GST was charged (no GSTIN
    # supplied). gstAmount is the GST component in INR major units (0 when waived).
    gstin: str | None = None
    gstAmount: float | None = None


class PaymentEventOut(BaseModel):
    id: str
    user_id: str
    payment_id: str
    provider: str
    order_id: str | None
    currency: str | None
    amount: int | None
    amount_usd: int | None
    credited_amount_raw: int | None = None
    credited_amount_display: str | None = None
    coupon_code: str | None = None
    coupon_name: str | None = None
    discount_amount_raw: int | None = None
    discount_amount_display: str | None = None
    discount_amount_usd_display: str | None = None
    created_at: str


class PaymentOut(BaseModel):
    received: bool
    coupon: dict | None = None


class PendingImporterPaymentOut(BaseModel):
    id: str
    user_id: str
    payment_id: str
    order_id: str | None
    created_at: str


class MetadataUpdateRequest(BaseModel):
    metadata: dict


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_out(event: PaymentEvent) -> PaymentEventOut:
    discount_amount_raw = _extract_discount_amount_raw(event)
    return PaymentEventOut(
        id=str(event.id),
        user_id=event.user_id,
        payment_id=event.payment_id,
        provider=event.provider,
        order_id=event.order_id,
        currency=event.currency,
        amount=event.amount,
        amount_usd=event.amount_usd,
        credited_amount_raw=event.amount_usd,
        credited_amount_display=_format_minor_amount(event.amount_usd),
        coupon_code=event.coupon_code,
        coupon_name=None,
        discount_amount_raw=discount_amount_raw,
        discount_amount_display=_format_minor_amount(discount_amount_raw),
        discount_amount_usd_display=_format_minor_amount(event.discount_amount_usd),
        created_at=event.created_at.isoformat(),
    )


def _to_pending_importer_out(event: PaymentEvent) -> PendingImporterPaymentOut:
    return PendingImporterPaymentOut(
        id=str(event.id),
        user_id=event.user_id,
        payment_id=event.payment_id,
        order_id=event.order_id,
        created_at=event.created_at.isoformat(),
    )


def _convert_amount_to_usd(amount_major: Decimal, effective_rate: Decimal) -> Decimal:
    if effective_rate <= 0:
        raise HTTPException(status_code=422, detail="Invalid conversion rate configured")
    if effective_rate < 1:
        return amount_major * effective_rate
    return amount_major / effective_rate


def _minor_to_major(amount_minor: int | float | None) -> Decimal:
    if amount_minor is None:
        return Decimal("0.00")
    return Decimal(str(amount_minor)) / 100


def _format_minor_amount(amount_raw: int | None) -> str | None:
    if amount_raw is None:
        return None
    return f"{Decimal(amount_raw) / Decimal('100'):.2f}"


def _compute_discount_amount_usd(
    discount_minor: int | float | None,
    currency: str,
    effective_rate: Decimal | None,
) -> int | None:
    """Compute discount_amount_usd (USD cents) from the original minor-unit discount.

    USD:  discount_minor is already cents — store as-is.
    INR:  discount_minor is paisa. Dividing paisa by the INR/USD rate yields USD cents
          directly (both scales are ×100, so they cancel).
          e.g. 85000 paisa / 85 (INR/USD) = 1000 USD cents = $10.00
    """
    if not discount_minor:
        return None
    if currency == "USD":
        return int(discount_minor)
    if effective_rate is None or effective_rate <= 0:
        return None
    return int((Decimal(str(discount_minor)) / effective_rate).quantize(Decimal("1")))


def _extract_discount_amount_raw(event: PaymentEvent) -> int | None:
    # Use the dedicated column if available (0034 migration)
    if event.discount_amount is not None:
        return event.discount_amount
    return None


async def _load_coupon_name_map(
    db: AsyncSession,
    coupon_codes: set[str],
) -> dict[str, str]:
    if not coupon_codes:
        return {}
    result = await db.execute(
        select(CheckoutCoupon.code, CheckoutCoupon.name).where(
            func.lower(CheckoutCoupon.code).in_([code.lower() for code in coupon_codes])
        )
    )
    return {
        normalized: name
        for code, name in result.all()
        if (normalized := _normalize_coupon_code(code)) is not None
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(
    body: PaymentRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: None = Depends(verify_webhook_key),  # noqa: B008
):
    """
    Ingest a payment event from a payment provider webhook.

    Auth: Authorization: Bearer <WEBHOOK_API_KEY>
    """

    logger.info(
        "payment_received",
        user_id=body.userId,
        payment_id=body.paymentId,
        provider=body.provider,
    )
    normalized_coupon_code = _normalize_coupon_code(body.couponCode)

    existing_payment = await db.execute(
        select(PaymentEvent).where(PaymentEvent.payment_id == body.paymentId).limit(1)
    )
    if existing_payment.scalar_one_or_none() is not None:
        logger.info(
            "payment_duplicate_ignored",
            user_id=body.userId,
            payment_id=body.paymentId,
            provider=body.provider,
        )
        return {"received": True, "coupon": None}

    # Resolve conversion rate and compute USD amount before persisting.
    amount_usd: Decimal | None = None
    effective_rate: Decimal | None = None
    if body.amount and body.amount > 0:
        currency = (body.currency or "USD").upper()
        charged_amount_major = _minor_to_major(body.amount)
        gst_amount_major = _minor_to_major(body.gstAmount)
        coupon_discount_major = _minor_to_major(body.couponDiscountAmount)
        credited_amount_major = charged_amount_major - gst_amount_major

        if currency == "USD":
            amount_usd = credited_amount_major
        else:
            rate_result = await db.execute(
                select(CurrencyConversionRate)
                .where(CurrencyConversionRate.currency == currency)
                .order_by(CurrencyConversionRate.created_at.desc())
                .limit(1)
            )
            rate_row = rate_result.scalar_one_or_none()
            if rate_row is None:
                logger.warning(
                    "payment_currency_rate_missing",
                    currency=currency,
                    user_id=body.userId,
                    payment_id=body.paymentId,
                )
                raise HTTPException(
                    status_code=422,
                    detail=f"No conversion rate found for currency '{currency}'",
                )
            # Amount is in the smallest unit (e.g. paise for INR). Convert to
            # major units, restore any coupon discount to the credited portion,
            # subtract GST, then convert to USD. Some local environments have
            # historical FX rows stored as INR-per-USD (>1) while others have
            # USD-per-INR (<1), so handle both directions defensively.
            effective_rate = rate_row.total_rate or rate_row.rate
            amount_usd = _convert_amount_to_usd(credited_amount_major, effective_rate)
            logger.info(
                "payment_currency_converted",
                currency=currency,
                total_rate=str(effective_rate),
                charged_amount_minor=body.amount,
                charged_amount_major=str(charged_amount_major),
                gst_amount=str(body.gstAmount),
                gst_amount_major=str(gst_amount_major),
                coupon_discount_amount=str(body.couponDiscountAmount),
                coupon_discount_major=str(coupon_discount_major),
                credited_amount_major=str(credited_amount_major),
                amount_usd=str(amount_usd),
                conversion_mode=("multiply_rate" if effective_rate < 1 else "divide_rate"),
                user_id=body.userId,
                amount_before_discount_major=str(body.amount),
            )
        if currency == "USD":
            logger.info(
                "payment_amount_resolved",
                currency=currency,
                charged_amount_minor=body.amount,
                charged_amount_major=str(charged_amount_major),
                gst_amount=str(body.gstAmount),
                gst_amount_major=str(gst_amount_major),
                coupon_discount_amount=str(body.couponDiscountAmount),
                coupon_discount_major=str(coupon_discount_major),
                credited_amount_major=str(credited_amount_major),
                amount_usd=str(amount_usd),
                user_id=body.userId,
                amount_before_discount_major=str(body.amount),
            )

    event = PaymentEvent(
        user_id=body.userId,
        payment_id=body.paymentId,
        provider=body.provider,
        order_id=body.orderId,
        currency=body.currency,
        amount=body.amount,
        amount_usd=int(amount_usd * 100) if amount_usd is not None else None,
        discount_amount_usd=_compute_discount_amount_usd(
            body.couponDiscountAmount,
            (body.currency or "USD").upper(),
            effective_rate,
        ),
        ip_address=body.ipAddress,
        country=body.country,
        coupon_code=normalized_coupon_code,
        discount_amount=body.couponDiscountAmount,
    )
    db.add(event)
    await db.flush()

    # Create a GST record for Indian payments.
    if body.country and body.country.upper() == "IN" and body.gstAmount is not None:
        gstin_record = GstinRecord(
            payment_event_id=event.id,
            gstin=body.gstin or None,
            gst_amount=Decimal(str(body.gstAmount)),
        )
        db.add(gstin_record)
        logger.info(
            "gstin_record_created",
            payment_event_id=str(event.id),
            gstin=body.gstin,
            gst_amount=str(body.gstAmount),
        )

    coupon_payload: dict | None = None
    if normalized_coupon_code:
        coupon_results = await db.execute(
            select(CheckoutCoupon).where(
                func.lower(CheckoutCoupon.code) == normalized_coupon_code.lower()
            )
        )

        coupons = coupon_results.scalars().all()
        coupon_payload = None

        for coupon in coupons:
            prior_usage = None

            if coupon.reuse_policy == "single_use":
                prior_usage_result = await db.execute(
                    select(PaymentEvent)
                    .where(PaymentEvent.user_id == body.userId)
                    .where(func.lower(PaymentEvent.coupon_code) == coupon.code.lower())
                    .where(PaymentEvent.payment_id != body.paymentId)
                    .limit(1)
                )
                prior_usage = prior_usage_result.scalar_one_or_none()

            if coupon.max_uses is None or coupon.used_count < coupon.max_uses:
                if coupon.reuse_policy != "single_use" or prior_usage is None:
                    coupon.used_count += 1

                    logger.info(
                        "coupon_consumed",
                        coupon_code=coupon.code,
                        user_id=body.userId,
                        payment_id=body.paymentId,
                        provider=body.provider,
                    )

                    # Auto-deactivate locally when the global usage limit is reached.
                    # No API calls are made to providers — the next cron sync will
                    # reflect the updated state, and admins are notified via sync issues.
                    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
                        coupon.is_active = False
                        logger.info(
                            "coupon_auto_deactivated",
                            coupon_code=coupon.code,
                            used_count=coupon.used_count,
                            max_uses=coupon.max_uses,
                        )
                        existing_issue = await db.scalar(
                            select(CouponSyncIssue).where(
                                CouponSyncIssue.coupon_id == coupon.id,
                                CouponSyncIssue.issue_type == "auto_deactivated",
                                CouponSyncIssue.status == "pending",
                            )
                        )
                        if existing_issue is None:
                            db.add(
                                CouponSyncIssue(
                                    coupon_id=coupon.id,
                                    coupon_code=coupon.code,
                                    provider="stripe",
                                    issue_type="auto_deactivated",
                                    details={
                                        "used_count": coupon.used_count,
                                        "max_uses": coupon.max_uses,
                                        "trigger": "webhook",
                                        "note": (
                                            "Coupon deactivated locally. "
                                            "Deactivate manually in the Stripe dashboard."
                                        ),
                                    },
                                )
                            )

                    # pick one payload (or last valid one)
                    coupon_payload = {
                        "code": coupon.code,
                        "name": coupon.name,
                        "description": coupon.description,
                        "discount_type": coupon.discount_type,
                        "discount_value": format(coupon.discount_value, "f"),
                    }
                else:
                    logger.warning(
                        "coupon_applied_by_gateway_but_rejected_locally",
                        reason="single_use_already_consumed",
                        coupon_code=coupon.code,
                        user_id=body.userId,
                        payment_id=body.paymentId,
                        provider=body.provider,
                    )
            else:
                logger.warning(
                    "coupon_applied_by_gateway_but_rejected_locally",
                    reason="usage_limit_reached",
                    coupon_code=coupon.code,
                    user_id=body.userId,
                    payment_id=body.paymentId,
                    provider=body.provider,
                )

    if amount_usd is not None and amount_usd > 0:
        logger.info(
            "payment_crediting_balance",
            user_id=body.userId,
            payment_id=body.paymentId,
            provider=body.provider,
            amount_usd=str(amount_usd),
            amount_usd_minor=int(amount_usd * 100),
        )
        await credit_balance(body.userId, amount_usd, db, payment_event_id=event.id)

    return {"received": True, "coupon": coupon_payload}


@router.get("", response_model=list[PaymentEventOut])
async def list_payments(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """
    List all payment events for the authenticated user, ordered by most recent first.

    The userId is extracted from the Bearer JWT (Supabase sub claim) —
    no path parameter needed.

    Auth: Authorization: Bearer <Supabase JWT>
    """
    result = await db.execute(
        select(PaymentEvent)
        .where(PaymentEvent.user_id == identity.sub)
        .order_by(PaymentEvent.created_at.desc())
    )
    events = result.scalars().all()
    coupon_name_map = await _load_coupon_name_map(
        db,
        {event.coupon_code for event in events if event.coupon_code},
    )

    logger.info("payments_listed", user_id=identity.sub, count=len(events))
    output = []
    for event in events:
        row = _to_out(event)
        normalized_code = _normalize_coupon_code(event.coupon_code)
        row.coupon_name = coupon_name_map.get(normalized_code) if normalized_code else None
        output.append(row)
    return output


@router.get("/pending-importer", response_model=list[PendingImporterPaymentOut])
async def list_pending_importer_payments(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: None = Depends(verify_webhook_key),  # noqa: B008
):
    """
    Return cashfree payment events for which importer details have not yet been submitted.

    Scoped to events created within the last 7 days but at least 5 minutes old,
    mirroring the time window used by the subscription/addon importer cron.

    Auth: Authorization: Bearer <WEBHOOK_API_KEY>
    """
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)

    result = await db.execute(
        select(PaymentEvent)
        .where(PaymentEvent.provider == "cashfree")
        .where(
            or_(
                PaymentEvent.payment_metadata.is_(None),
                PaymentEvent.payment_metadata["cashfree_importer_details_submitted"].is_(None),
            )
        )
        .where(PaymentEvent.created_at >= seven_days_ago)
        .where(PaymentEvent.created_at <= five_minutes_ago)
        .order_by(PaymentEvent.created_at.asc())
    )
    events = result.scalars().all()

    logger.info("pending_importer_payments_listed", count=len(events))
    return [_to_pending_importer_out(e) for e in events]


@router.patch("/{payment_id}/metadata", response_model=PaymentOut)
async def update_payment_metadata(
    payment_id: str,
    body: MetadataUpdateRequest,
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
    _: None = Depends(verify_webhook_key),  # noqa: B008
):
    """
    Merge the supplied metadata dict into the existing metadata of a payment event.

    Identified by payment_id (the provider-side payment / transaction ID).

    Auth: Authorization: Bearer <WEBHOOK_API_KEY>
    """
    result = await db.execute(select(PaymentEvent).where(PaymentEvent.payment_id == payment_id))
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Payment event not found")

    merged = {**(event.payment_metadata or {}), **body.metadata}
    event.payment_metadata = merged
    flag_modified(event, "payment_metadata")

    logger.info("payment_metadata_updated", payment_id=payment_id)
    return {"received": True}
