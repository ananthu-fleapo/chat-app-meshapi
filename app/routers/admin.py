"""
Admin router — dev-only key management + usage reporting.

Available in ENV=dev only. In prod the router is not registered at all,
so every /admin/* URL returns 404 from the framework (no route match).
No ADMIN_SECRET needed: the ENV guard is the protection.

Endpoints
---------
POST   /admin/keys                  Create a key (plaintext returned ONCE)
GET    /admin/keys                  List all keys (no hashes, no plaintext)
PATCH  /admin/keys/{id}             Update status / defaults / rate limits
DELETE /admin/keys/{id}             Hard delete (dev clean-up)
GET    /admin/keys/{id}/usage       Per-key usage summary (Phase 5)
GET    /admin/usage/summary         System-wide usage summary (Phase 5)

Phase 3: rpm_limit, rpd_limit, spend_cap_usd on create/update + cache invalidation
Phase 5: usage reporting endpoints
"""

import hashlib
import uuid
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.cache.key_cache import invalidate_cached_key
from app.db.models import ApiKey, UsageEvent
from app.db.session import get_db_session
from app.exceptions import NotFoundError

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_key() -> str:
    return f"rsk_{ULID()}"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid UUID: {value!r}")


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    owner: str
    default_model: str | None = None
    default_params: dict | None = None
    meta: dict | None = None
    rpm_limit: int | None = None
    rpd_limit: int | None = None
    spend_cap_usd: float | None = None


class CreateKeyResponse(BaseModel):
    id: str
    key: str          # plaintext — shown ONCE, not stored
    owner: str
    status: str
    default_model: str | None
    rpm_limit: int | None
    rpd_limit: int | None


class KeySummary(BaseModel):
    id: str
    owner: str
    status: str
    default_model: str | None
    default_params: dict | None
    rpm_limit: int | None
    rpd_limit: int | None
    spend_cap_usd: str | None   # Decimal serialised as string to avoid float precision loss
    created_at: str
    updated_at: str


class UpdateKeyRequest(BaseModel):
    status: str | None = None
    default_model: str | None = None
    default_params: dict | None = None
    meta: dict | None = None
    rpm_limit: int | None = None
    rpd_limit: int | None = None
    spend_cap_usd: float | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/keys", response_model=CreateKeyResponse, status_code=201)
async def create_key(
    body: CreateKeyRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new RouterV API key.
    The plaintext key is returned exactly once — store it securely.
    """
    raw_key = _generate_key()
    key = ApiKey(
        key_hash=_hash_key(raw_key),
        owner=body.owner,
        default_model=body.default_model,
        default_params=body.default_params,
        meta=body.meta,
        rpm_limit=body.rpm_limit,
        rpd_limit=body.rpd_limit,
        spend_cap_usd=Decimal(str(body.spend_cap_usd)) if body.spend_cap_usd is not None else None,
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)

    logger.info("admin_key_created", key_id=str(key.id), owner=key.owner)

    return CreateKeyResponse(
        id=str(key.id),
        key=raw_key,
        owner=key.owner,
        status=key.status,
        default_model=key.default_model,
        rpm_limit=key.rpm_limit,
        rpd_limit=key.rpd_limit,
    )


@router.get("/keys", response_model=list[KeySummary])
async def list_keys(
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return [_to_summary(k) for k in result.scalars().all()]


@router.patch("/keys/{key_id}", response_model=KeySummary)
async def update_key(
    key_id: str,
    body: UpdateKeyRequest,
    db: AsyncSession = Depends(get_db_session),
):
    key = await _get_or_404(db, key_id)

    if body.status is not None:
        if body.status not in ("active", "suspended"):
            raise HTTPException(status_code=422, detail="status must be 'active' or 'suspended'")
        key.status = body.status
    if body.default_model is not None:
        key.default_model = body.default_model
    if body.default_params is not None:
        key.default_params = body.default_params
    if body.meta is not None:
        key.meta = body.meta
    if body.rpm_limit is not None:
        key.rpm_limit = body.rpm_limit
    if body.rpd_limit is not None:
        key.rpd_limit = body.rpd_limit
    if body.spend_cap_usd is not None:
        key.spend_cap_usd = Decimal(str(body.spend_cap_usd))

    await db.flush()
    await db.refresh(key)

    # Invalidate Redis cache immediately — don't wait for TTL.
    await invalidate_cached_key(key.key_hash)

    logger.info("admin_key_updated", key_id=str(key.id), owner=key.owner)
    return _to_summary(key)


@router.delete("/keys/{key_id}", status_code=204)
async def delete_key(
    key_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    key = await _get_or_404(db, key_id)

    # Invalidate before delete so the cache key is gone even if delete fails.
    await invalidate_cached_key(key.key_hash)
    await db.delete(key)
    logger.info("admin_key_deleted", key_id=str(key.id), owner=key.owner)


# ── Usage reporting (Phase 5) ─────────────────────────────────────────────────

class KeyUsageSummary(BaseModel):
    key_id: str
    owner: str
    total_requests: int
    successful_requests: int
    error_requests: int
    total_tokens: int | None
    total_cost_usd: str | None
    spend_cap_usd: str | None
    spend_cap_remaining_usd: str | None


class SystemUsageSummary(BaseModel):
    total_requests: int
    successful_requests: int
    total_tokens: int | None
    total_cost_usd: str | None
    unique_models: int
    unique_keys: int


@router.get("/keys/{key_id}/usage", response_model=KeyUsageSummary)
async def get_key_usage(
    key_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Lifetime usage summary for a single key."""
    key = await _get_or_404(db, key_id)
    uid = _parse_uuid(key_id)

    row = await db.execute(
        select(
            func.count(UsageEvent.id).label("total"),
            func.coalesce(
                func.sum(UsageEvent.total_tokens), 0
            ).label("tokens"),
            func.coalesce(
                func.sum(UsageEvent.cost_usd), 0
            ).label("cost"),
            func.count(UsageEvent.id).filter(
                UsageEvent.status == "success"
            ).label("success"),
            func.count(UsageEvent.id).filter(
                UsageEvent.status == "error"
            ).label("errors"),
        ).where(UsageEvent.key_id == uid)
    )
    r = row.one()

    total_cost = Decimal(str(r.cost))
    remaining = (
        (key.spend_cap_usd - total_cost)
        if key.spend_cap_usd is not None
        else None
    )

    return KeyUsageSummary(
        key_id=key_id,
        owner=key.owner,
        total_requests=r.total,
        successful_requests=r.success,
        error_requests=r.errors,
        total_tokens=r.tokens if r.tokens else None,
        total_cost_usd=str(total_cost) if total_cost else None,
        spend_cap_usd=str(key.spend_cap_usd) if key.spend_cap_usd else None,
        spend_cap_remaining_usd=str(remaining) if remaining is not None else None,
    )


@router.get("/usage/summary", response_model=SystemUsageSummary)
async def get_usage_summary(
    db: AsyncSession = Depends(get_db_session),
):
    """System-wide lifetime usage summary across all keys."""
    row = await db.execute(
        select(
            func.count(UsageEvent.id).label("total"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
            func.count(UsageEvent.id).filter(
                UsageEvent.status == "success"
            ).label("success"),
            func.count(func.distinct(UsageEvent.model)).label("models"),
            func.count(func.distinct(UsageEvent.key_id)).label("keys"),
        )
    )
    r = row.one()
    total_cost = Decimal(str(r.cost))

    return SystemUsageSummary(
        total_requests=r.total,
        successful_requests=r.success,
        total_tokens=r.tokens if r.tokens else None,
        total_cost_usd=str(total_cost) if total_cost else None,
        unique_models=r.models,
        unique_keys=r.keys,
    )


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, key_id: str) -> ApiKey:
    uid = _parse_uuid(key_id)
    result = await db.execute(select(ApiKey).where(ApiKey.id == uid))
    key = result.scalar_one_or_none()
    if key is None:
        raise NotFoundError("API key not found.")
    return key


def _to_summary(k: ApiKey) -> KeySummary:
    return KeySummary(
        id=str(k.id),
        owner=k.owner,
        status=k.status,
        default_model=k.default_model,
        default_params=k.default_params,
        rpm_limit=k.rpm_limit,
        rpd_limit=k.rpd_limit,
        spend_cap_usd=str(k.spend_cap_usd) if k.spend_cap_usd is not None else None,
        created_at=k.created_at.isoformat(),
        updated_at=k.updated_at.isoformat(),
    )
