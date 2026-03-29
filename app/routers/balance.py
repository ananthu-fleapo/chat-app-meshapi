"""
Balance endpoint — GET /v1/balance

Returns the authenticated user's current credit balance.
Auth: Supabase JWT (control plane).
"""

from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.db.models import UserBalance
from app.db.session import get_db_session

router = APIRouter(prefix="/v1/balance", tags=["balance"])
logger = structlog.get_logger()


class BalanceOut(BaseModel):
    balance_usd: str
    updated_at: str | None


@router.get("", response_model=BalanceOut)
async def get_balance(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the authenticated user's current credit balance."""
    result = await db.execute(
        select(UserBalance).where(UserBalance.user_id == identity.owner)
    )
    row = result.scalar_one_or_none()

    if row is None:
        return BalanceOut(balance_usd="0.000000", updated_at=None)

    return BalanceOut(
        balance_usd=str(row.balance_usd),
        updated_at=row.updated_at.isoformat(),
    )
