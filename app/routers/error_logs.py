"""
Error log router — GET /admin/usage/errors

Returns recent error usage_events for admin inspection.
Protected by the same admin JWT guard as the rest of the /admin prefix.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import get_admin_user
from app.db.models import UsageEvent
from app.db.session import get_db_session

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


class ErrorLogRow(BaseModel):
    id: str
    request_id: str
    model: str
    provider: str
    error_code: str | None
    prompt_tokens: int | None
    latency_ms: int | None
    created_at: str


@router.get("/usage/errors", response_model=list[ErrorLogRow])
async def get_error_logs(
    db: AsyncSession = Depends(get_db_session),
    limit: int = 100,
):
    """Recent error usage_events, newest first."""
    rows = await db.execute(
        select(UsageEvent)
        .where(UsageEvent.status == "error")
        .order_by(UsageEvent.created_at.desc())
        .limit(limit)
    )
    return [
        ErrorLogRow(
            id=str(r.id),
            request_id=r.request_id,
            model=r.model,
            provider=r.provider,
            error_code=r.error_code,
            prompt_tokens=r.prompt_tokens,
            latency_ms=r.latency_ms,
            created_at=r.created_at.isoformat(),
        )
        for r in rows.scalars().all()
    ]
