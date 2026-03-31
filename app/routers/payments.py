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

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from decimal import Decimal

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.auth.dependencies import verify_webhook_key
from app.db.models import CurrencyConversionRate, PaymentEvent, UserBalance
from app.db.session import get_db_session
from app.usage.balance import credit_balance

router = APIRouter(prefix="/v1/payments", tags=["payments"])
logger = structlog.get_logger()


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class PaymentRequest(BaseModel):
    userId: str
    paymentId: str
    provider: str
    orderId: str | None = None
    currency: str | None = None
    amount: int | None = None


class PaymentEventOut(BaseModel):
    id: str
    userId: str
    paymentId: str
    provider: str
    orderId: str | None
    currency: str | None
    amount: int | None
    createdAt: str


class PaymentOut(BaseModel):
    received: bool


class PendingImporterPaymentOut(BaseModel):
    id: str
    userId: str
    paymentId: str
    orderId: str | None
    createdAt: str


class MetadataUpdateRequest(BaseModel):
    metadata: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_out(event: PaymentEvent) -> PaymentEventOut:
    return PaymentEventOut(
        id=str(event.id),
        userId=event.user_id,
        paymentId=event.payment_id,
        provider=event.provider,
        orderId=event.order_id,
        currency=event.currency,
        amount=event.amount,
        createdAt=event.created_at.isoformat(),
    )


def _to_pending_importer_out(event: PaymentEvent) -> PendingImporterPaymentOut:
    return PendingImporterPaymentOut(
        id=str(event.id),
        userId=event.user_id,
        paymentId=event.payment_id,
        orderId=event.order_id,
        createdAt=event.created_at.isoformat(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(
    body: PaymentRequest,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_webhook_key),
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

    # Resolve conversion rate and compute USD amount before persisting.
    amount_usd: Decimal | None = None
    if body.amount and body.amount > 0:
        currency = (body.currency or "USD").upper()
        if currency == "USD":
            # Amount is in cents; normalize to dollars.
            amount_usd = Decimal(body.amount) / 100
        else:
            rate_row = await db.get(CurrencyConversionRate, currency)
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
            # Amount is in the smallest unit (e.g. paise for INR).
            # Divide by 100 to get major units, then multiply by rate to get USD.
            amount_usd = (Decimal(body.amount) / 100) * rate_row.rate
            logger.info(
                "payment_currency_converted",
                currency=currency,
                rate=str(rate_row.rate),
                amount_original=body.amount,
                amount_usd=str(amount_usd),
                user_id=body.userId,
            )

    event = PaymentEvent(
        user_id=body.userId,
        payment_id=body.paymentId,
        provider=body.provider,
        order_id=body.orderId,
        currency=body.currency,
        amount=body.amount,
    )
    db.add(event)
    await db.flush()

    if amount_usd is not None and amount_usd > 0:
        await credit_balance(body.userId, amount_usd, db)

    return {"received": True}


@router.get("", response_model=list[PaymentEventOut])
async def list_payments(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
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

    logger.info("payments_listed", user_id=identity.sub, count=len(events))
    return [_to_out(e) for e in events]


@router.get("/pending-importer", response_model=list[PendingImporterPaymentOut])
async def list_pending_importer_payments(
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_webhook_key),
):
    """
    Return cashfree payment events for which importer details have not yet been submitted.

    Scoped to events created within the last 7 days but at least 5 minutes old,
    mirroring the time window used by the subscription/addon importer cron.

    Auth: Authorization: Bearer <WEBHOOK_API_KEY>
    """
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

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
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_webhook_key),
):
    """
    Merge the supplied metadata dict into the existing metadata of a payment event.

    Identified by payment_id (the provider-side payment / transaction ID).

    Auth: Authorization: Bearer <WEBHOOK_API_KEY>
    """
    result = await db.execute(
        select(PaymentEvent).where(PaymentEvent.payment_id == payment_id)
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Payment event not found")

    merged = {**(event.payment_metadata or {}), **body.metadata}
    event.payment_metadata = merged
    flag_modified(event, "payment_metadata")

    logger.info("payment_metadata_updated", payment_id=payment_id)
    return {"received": True}
