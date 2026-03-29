"""
Usage analytics — GET /v1/usage

Control plane endpoint — requires a Supabase JWT.
All data is scoped to keys owned by the authenticated user.

Summary     GET /v1/usage               Aggregate stats (total tokens, cost, requests)
Events      GET /v1/usage/events        Paginated per-request history
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.db.models import ApiKey, UsageEvent
from app.db.session import get_db_session

router = APIRouter(prefix="/v1/usage", tags=["usage"])
logger = structlog.get_logger()


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class ModelBreakdown(BaseModel):
    model: str
    requests: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost_usd: str | None


class UsageSummary(BaseModel):
    total_requests: int
    successful_requests: int
    error_requests: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    total_cost_usd: str | None
    by_model: list[ModelBreakdown]


class UsageEventOut(BaseModel):
    id: str
    key_id: str
    request_id: str
    model: str
    stream: bool
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost_usd: str | None
    latency_ms: int | None
    status: str
    error_code: str | None
    created_at: str


class UsageEventsPage(BaseModel):
    events: list[UsageEventOut]
    total: int
    limit: int
    offset: int


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _owner_key_ids(db: AsyncSession, owner: str) -> list:
    result = await db.execute(
        select(ApiKey.id).where(ApiKey.owner == owner)
    )
    return [row[0] for row in result.all()]


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=UsageSummary)
async def get_usage_summary(
    since: str | None = Query(default=None, description="ISO 8601 start date, e.g. 2026-01-01"),
    until: str | None = Query(default=None, description="ISO 8601 end date, e.g. 2026-12-31"),
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Aggregate usage stats for the authenticated user across all their keys.

    Optionally filter by date range with `since` and `until` (ISO 8601).
    """
    key_ids = await _owner_key_ids(db, identity.owner)
    if not key_ids:
        return UsageSummary(
            total_requests=0, successful_requests=0, error_requests=0,
            prompt_tokens=None, completion_tokens=None, total_tokens=None,
            total_cost_usd=None, by_model=[],
        )

    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)

    # ── Aggregate totals ──────────────────────────────────────────────────────
    totals_q = select(
        func.count(UsageEvent.id).label("total"),
        func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
        func.count(UsageEvent.id).filter(UsageEvent.status == "error").label("errors"),
        func.sum(UsageEvent.prompt_tokens).label("prompt_tokens"),
        func.sum(UsageEvent.completion_tokens).label("completion_tokens"),
        func.sum(UsageEvent.total_tokens).label("total_tokens"),
        func.sum(UsageEvent.cost_usd).label("cost_usd"),
    ).where(UsageEvent.key_id.in_(key_ids))

    if since_dt:
        totals_q = totals_q.where(UsageEvent.created_at >= since_dt)
    if until_dt:
        totals_q = totals_q.where(UsageEvent.created_at <= until_dt)

    totals = (await db.execute(totals_q)).one()

    # ── Per-model breakdown ───────────────────────────────────────────────────
    breakdown_q = select(
        UsageEvent.model,
        func.count(UsageEvent.id).label("requests"),
        func.sum(UsageEvent.prompt_tokens).label("prompt_tokens"),
        func.sum(UsageEvent.completion_tokens).label("completion_tokens"),
        func.sum(UsageEvent.total_tokens).label("total_tokens"),
        func.sum(UsageEvent.cost_usd).label("cost_usd"),
    ).where(UsageEvent.key_id.in_(key_ids)).group_by(UsageEvent.model).order_by(
        func.count(UsageEvent.id).desc()
    )

    if since_dt:
        breakdown_q = breakdown_q.where(UsageEvent.created_at >= since_dt)
    if until_dt:
        breakdown_q = breakdown_q.where(UsageEvent.created_at <= until_dt)

    breakdown_rows = (await db.execute(breakdown_q)).all()

    logger.info(
        "usage_summary_fetched",
        owner=identity.owner,
        total=totals.total,
        since=since,
        until=until,
    )

    return UsageSummary(
        total_requests=totals.total or 0,
        successful_requests=totals.success or 0,
        error_requests=totals.errors or 0,
        prompt_tokens=totals.prompt_tokens,
        completion_tokens=totals.completion_tokens,
        total_tokens=totals.total_tokens,
        total_cost_usd=str(totals.cost_usd) if totals.cost_usd else None,
        by_model=[
            ModelBreakdown(
                model=row.model,
                requests=row.requests,
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                total_tokens=row.total_tokens,
                cost_usd=str(row.cost_usd) if row.cost_usd else None,
            )
            for row in breakdown_rows
        ],
    )


@router.get("/events", response_model=UsageEventsPage)
async def get_usage_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    since: str | None = Query(default=None, description="ISO 8601 start date"),
    until: str | None = Query(default=None, description="ISO 8601 end date"),
    model: str | None = Query(default=None, description="Filter by model id"),
    status: str | None = Query(default=None, description="Filter by status: success | error"),
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Paginated per-request event history for the authenticated user.

    Ordered by most recent first. Filter by date range, model, or status.
    """
    key_ids = await _owner_key_ids(db, identity.owner)
    if not key_ids:
        return UsageEventsPage(events=[], total=0, limit=limit, offset=offset)

    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)

    base = select(UsageEvent).where(UsageEvent.key_id.in_(key_ids))
    count_base = select(func.count(UsageEvent.id)).where(UsageEvent.key_id.in_(key_ids))

    if since_dt:
        base = base.where(UsageEvent.created_at >= since_dt)
        count_base = count_base.where(UsageEvent.created_at >= since_dt)
    if until_dt:
        base = base.where(UsageEvent.created_at <= until_dt)
        count_base = count_base.where(UsageEvent.created_at <= until_dt)
    if model:
        base = base.where(UsageEvent.model == model)
        count_base = count_base.where(UsageEvent.model == model)
    if status:
        base = base.where(UsageEvent.status == status)
        count_base = count_base.where(UsageEvent.status == status)

    total = (await db.execute(count_base)).scalar_one()

    events_q = base.order_by(UsageEvent.created_at.desc()).offset(offset).limit(limit)
    events = (await db.execute(events_q)).scalars().all()

    return UsageEventsPage(
        events=[
            UsageEventOut(
                id=str(e.id),
                key_id=str(e.key_id),
                request_id=e.request_id,
                model=e.model,
                stream=e.stream,
                prompt_tokens=e.prompt_tokens,
                completion_tokens=e.completion_tokens,
                total_tokens=e.total_tokens,
                cost_usd=str(e.cost_usd) if e.cost_usd else None,
                latency_ms=e.latency_ms,
                status=e.status,
                error_code=e.error_code,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
