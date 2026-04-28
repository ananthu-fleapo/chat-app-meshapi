"""
User settings — GET /v1/settings, PATCH /v1/settings

Control plane endpoint — requires a Supabase JWT.
Scoped to the authenticated user (identity.sub as the User.id PK).
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.cache.zdr_cache import invalidate_zdr_cache
from app.db.models import User
from app.db.session import get_db_session

router = APIRouter(prefix="/v1/settings", tags=["settings"])
logger = structlog.get_logger()


class UserSettingsResponse(BaseModel):
    zero_data_retention: bool


class UpdateSettingsRequest(BaseModel):
    zero_data_retention: bool | None = None


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> UserSettingsResponse:
    result = await db.execute(select(User).where(User.id == identity.sub))
    user = result.scalar_one_or_none()
    return UserSettingsResponse(
        zero_data_retention=user.zero_data_retention if user else False
    )


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    body: UpdateSettingsRequest,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> UserSettingsResponse:
    result = await db.execute(select(User).where(User.id == identity.sub))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.zero_data_retention is not None:
        user.zero_data_retention = body.zero_data_retention
    await db.flush()
    # Invalidate cache so next request sees the new value immediately.
    # Use identity.owner (not sub) — matches the owner string the middleware uses.
    await invalidate_zdr_cache(identity.owner)
    logger.info(
        "zdr_updated",
        owner=identity.owner,
        zero_data_retention=user.zero_data_retention,
    )
    return UserSettingsResponse(zero_data_retention=user.zero_data_retention)
