"""
Internal router — ops endpoints for internal tooling.

Protected by a static bearer token: Authorization: Bearer <INTERNAL_API_KEY>
Set INTERNAL_API_KEY in .env. Leave empty to disable (routes return 403).

Endpoints
---------
GET  /internal/users   List all users with balance and spend
"""

from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import verify_internal_key
from app.db.models import ApiKey, PaymentEvent, User, UserBalance, UsageEvent
from app.db.session import get_db_session

logger = structlog.get_logger()

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(verify_internal_key)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────


class UserSummary(BaseModel):
    user_id: str
    email: str | None = None
    display_name: str | None = None
    key_count: int
    active_key_count: int
    total_spent_usd: str
    balance_usd: str | None = None
    last_activity: str | None = None
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _build_user_summary(db: AsyncSession, owner: str, user: User) -> UserSummary:
    keys_q = await db.execute(
        select(
            func.count(ApiKey.id).label("key_count"),
            func.count(ApiKey.id).filter(ApiKey.status == "active").label("active_key_count"),
        ).where(ApiKey.owner == owner)
    )
    keys_row = keys_q.one()

    recharge_q = await db.execute(
        select(func.sum(PaymentEvent.amount_usd)).where(PaymentEvent.user_id == owner)
    )
    total_recharged = Decimal(str(recharge_q.scalar() or 0)) / 100

    activity_q = await db.execute(
        select(func.max(UsageEvent.created_at))
        .join(ApiKey, UsageEvent.key_id == ApiKey.id)
        .where(ApiKey.owner == owner)
    )
    last_activity = activity_q.scalar()

    bal_q = await db.execute(select(UserBalance).where(UserBalance.user_id == owner))
    bal = bal_q.scalar_one_or_none()

    balance = Decimal(str(bal.balance_usd)) if bal else Decimal(0)
    total_spent = max(total_recharged - balance, Decimal(0))

    return UserSummary(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        key_count=keys_row.key_count,
        active_key_count=keys_row.active_key_count,
        total_spent_usd=str(total_spent),
        balance_usd=str(bal.balance_usd) if bal else None,
        last_activity=last_activity.isoformat() if last_activity else None,
        created_at=user.created_at.isoformat(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """List all users enriched with balance and spend."""
    users_q = await db.execute(select(User))
    all_users = users_q.scalars().all()

    results = []
    for user in all_users:
        results.append(await _build_user_summary(db, user.id, user))

    results.sort(key=lambda x: x.last_activity or "", reverse=True)
    return results
