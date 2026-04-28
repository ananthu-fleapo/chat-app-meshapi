"""
Model request management — POST/GET /v1/model-requests

Control plane endpoint — requires a Supabase JWT (dashboard session).
Users submit requests for new models to be added to the platform.

Submit  POST  /v1/model-requests          Submit a new model request
List    GET   /v1/model-requests          List the authenticated user's requests

Admin endpoints (mesh_api:admin permission required):
List    GET   /v1/model-requests/admin    List all requests across all users
Patch   PATCH /v1/model-requests/{id}     Update status (approve / reject)
"""

import time
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.control_plane import ControlPlaneIdentity, get_admin_user, get_control_plane_user
from app.cache.redis_client import get_redis
from app.db.models import ModelRequest, User
from app.db.session import get_db_session
from app.exceptions import NotFoundError, RateLimitError

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/model-requests", tags=["model-requests"])

# Submission limits — generous enough for real users, tight enough to stop spam.
_HOURLY_LIMIT = 10   # max 3 submissions per owner per hour
_DAILY_LIMIT = 30    # max 5 submissions per owner per day


async def _check_submit_rate_limit(owner: str) -> None:
    """Enforce per-owner hourly and daily caps on model request submissions.

    Fails open on Redis errors — a Redis blip should not block legitimate users.
    """
    redis = get_redis()
    if redis is None:
        return

    hour_bucket = int(time.time()) // 3600
    day_bucket = datetime.now(UTC).strftime("%Y%m%d")
    hour_key = f"routerv:mr:{owner}:h:{hour_bucket}"
    day_key = f"routerv:mr:{owner}:d:{day_bucket}"

    try:
        async with redis.pipeline(transaction=False) as pipe:
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)   # 2× window — safety margin
            pipe.incr(day_key)
            pipe.expire(day_key, 90000)   # ~25h
            results = await pipe.execute()
        hour_count: int = results[0]
        day_count: int = results[2]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "redis_unavailable", source="model_request_limiter", owner=owner, error=str(exc)
        )
        return

    if hour_count > _HOURLY_LIMIT:
        seconds_left = 3600 - (int(time.time()) % 3600)
        raise RateLimitError(
            f"Too many model requests. You can submit at most {_HOURLY_LIMIT} per hour.",
            limit_type="hour",
            retry_after=seconds_left,
        )

    if day_count > _DAILY_LIMIT:
        now = datetime.now(UTC)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_left = max(1, int((next_midnight - now).total_seconds()))
        raise RateLimitError(
            f"Too many model requests. You can submit at most {_DAILY_LIMIT} per day.",
            limit_type="day",
            retry_after=seconds_left,
        )


# ── Pydantic I/O ───────────────────────────────────────────────────────────────

class SubmitModelRequestBody(BaseModel):
    model_name: str
    use_case: str | None = None

    @field_validator("model_name")
    @classmethod
    def model_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model_name must not be blank")
        return v.strip()

    @field_validator("use_case")
    @classmethod
    def use_case_max_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 1000:
            raise ValueError("use_case must be 1000 characters or fewer")
        return v


class ModelRequestOut(BaseModel):
    id: str
    owner: str
    email: str | None
    model_name: str
    use_case: str | None
    status: str
    created_at: str


class UpdateModelRequestBody(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        allowed = {"pending", "approved", "rejected"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


def _fmt(req: ModelRequest, *, email: str | None = None) -> ModelRequestOut:
    return ModelRequestOut(
        id=str(req.id),
        owner=req.owner,
        email=email,
        model_name=req.model_name,
        use_case=req.use_case,
        status=req.status,
        created_at=req.created_at.isoformat(),
    )


# ── User endpoints ─────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def submit_model_request(
    body: SubmitModelRequestBody,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ModelRequestOut:
    await _check_submit_rate_limit(identity.owner)
    req = ModelRequest(
        owner=identity.owner,
        model_name=body.model_name,
        use_case=body.use_case or None,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    logger.info("model_request_submitted", owner=identity.owner, model_name=body.model_name)
    return _fmt(req)


@router.get("")
async def list_my_model_requests(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ModelRequestOut]:
    rows = await db.execute(
        select(ModelRequest)
        .where(ModelRequest.owner == identity.owner)
        .order_by(ModelRequest.created_at.desc())
    )
    return [_fmt(r) for r in rows.scalars()]


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/admin")
async def list_all_model_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    _identity: ControlPlaneIdentity = Depends(get_admin_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> list[ModelRequestOut]:
    q = select(ModelRequest).order_by(ModelRequest.created_at.desc())
    if status:
        q = q.where(ModelRequest.status == status)
    q = q.limit(limit).offset(offset)
    reqs = list((await db.execute(q)).scalars())

    email_by_owner: dict[str, str] = {}
    if reqs:
        owner_ids = list({r.owner for r in reqs})
        email_rows = await db.execute(
            select(User.id, User.email).where(User.id.in_(owner_ids))
        )
        email_by_owner = {row.id: row.email for row in email_rows.all()}

    return [_fmt(r, email=email_by_owner.get(r.owner)) for r in reqs]


@router.patch("/admin/{request_id}")
async def update_model_request_status(
    request_id: uuid.UUID,
    body: UpdateModelRequestBody,
    _identity: ControlPlaneIdentity = Depends(get_admin_user),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> ModelRequestOut:
    row = await db.get(ModelRequest, request_id)
    if row is None:
        raise NotFoundError("model_request", str(request_id))
    row.status = body.status
    await db.commit()
    await db.refresh(row)
    logger.info("model_request_updated", id=str(request_id), status=body.status)
    return _fmt(row)
