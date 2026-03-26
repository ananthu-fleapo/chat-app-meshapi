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

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.auth.dependencies import verify_webhook_key
from app.db.models import PaymentEvent
from app.db.session import get_db_session

router = APIRouter(prefix="/v1/payments", tags=["payments"])
logger = structlog.get_logger()


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class PaymentRequest(BaseModel):
    userId: str
    paymentId: str
    provider: str
    addonProductId: str
    quantity: int


class PaymentEventOut(BaseModel):
    id: str
    userId: str
    paymentId: str
    provider: str
    addonProductId: str
    quantity: int
    createdAt: str


class PaymentOut(BaseModel):
    received: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_out(event: PaymentEvent) -> PaymentEventOut:
    return PaymentEventOut(
        id=str(event.id),
        userId=event.user_id,
        paymentId=event.payment_id,
        provider=event.provider,
        addonProductId=event.addon_product_id,
        quantity=event.quantity,
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
    print(f"Received paymentId: {body.paymentId}")
    logger.info(
        "payment_received",
        user_id=body.userId,
        payment_id=body.paymentId,
        provider=body.provider,
        addon_product_id=body.addonProductId,
        quantity=body.quantity,
    )

    event = PaymentEvent(
        user_id=body.userId,
        payment_id=body.paymentId,
        provider=body.provider,
        addon_product_id=body.addonProductId,
        quantity=body.quantity,
    )
    db.add(event)
    await db.flush()

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
