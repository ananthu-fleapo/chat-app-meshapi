"""
Admin router — key management + usage reporting.

Protected by JWT auth: the caller must present a valid Supabase JWT whose
app_metadata.permissions list contains "mesh_api:admin".
Always enforced — no dev bypass.

Endpoints
---------
POST   /admin/keys                       Create a key (plaintext returned ONCE)
GET    /admin/keys                       List all keys (no hashes, no plaintext)
PATCH  /admin/keys/{id}                  Update status / defaults / rate limits
DELETE /admin/keys/{id}                  Hard delete (dev clean-up)
GET    /admin/keys/{id}/usage            Per-key usage summary (Phase 5)
GET    /admin/usage/summary              System-wide usage summary (Phase 5)

POST   /admin/provider-keys              Create a provider key record
GET    /admin/provider-keys              List all provider keys (all owners)
DELETE /admin/provider-keys/{id}         Hard delete

Phase 3: rpm_limit, rpd_limit, spend_cap_usd on create/update + cache invalidation
Phase 5: usage reporting endpoints
Phase 6: admin provider key management
"""

import asyncio
import hashlib
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

import structlog
from structlog.contextvars import bind_contextvars
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select, text, update
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.auth.control_plane import get_admin_user
from app.cache.key_cache import invalidate_cached_key
from app.cache.redis_client import get_redis
from app.config import settings
from app.db.models import ApiKey, CurrencyConversionRate, Discount, Model, ModelPrice, PaymentEvent, ProviderKey, Template, UsageEvent, UserBalance, User
from app.cache.analytics_cache import get_analytics_cached, set_analytics_cached
from app.routers.usage import UsageEventOut, UsageEventsPage, _parse_dt, _split_model, _tokens_per_second
from app.db.session import get_db_session
from app.exceptions import NotFoundError
from app.providers.provisioner import (
    ProvisionedKey,
    create_or_key,
    delete_or_key,
    disable_or_key,
)
from app.providers.secret_manager import fetch_secret, invalidate_secret_cache, store_secret 

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


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

def _clamp_rate_limits(rpm: int | None, rpd: int | None) -> tuple[int | None, int | None]:
    """Clamp rpm/rpd to system maximums. Raises 422 if a value exceeds the cap."""
    if rpm is not None and rpm > settings.max_rpm:
        raise HTTPException(
            status_code=422,
            detail=f"rpm_limit cannot exceed system maximum of {settings.max_rpm}.",
        )
    if rpd is not None and rpd > settings.max_rpd:
        raise HTTPException(
            status_code=422,
            detail=f"rpd_limit cannot exceed system maximum of {settings.max_rpd}.",
        )
    return rpm, rpd


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
    email: str | None
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

async def _auto_provision_for_owner(
    owner: str,
    spend_cap_usd: Decimal | None,
    db: AsyncSession,
) -> ProviderKey | None:
    """
    Provision a dedicated OpenRouter key for an owner if one doesn't exist yet.

    Steps:
      1. Check if the owner already has an active provider_keys row — skip if so.
      2. Call OpenRouter Management API to create a key.
      3. Store plaintext in GCP Secret Manager if available, else store inline.
      4. Write a ProviderKey row and return it.

    Raises RouterVError (500) if the OpenRouter Management API call fails.
    Returns None if the owner already has a key (idempotent).
    """
    # Skip if owner already has a provider key configured.
    existing = await db.execute(
        select(ProviderKey).where(
            ProviderKey.owner == owner,
            ProviderKey.provider == "openrouter",
            ProviderKey.is_active.is_(True),
        ).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        logger.debug("auto_provision_skipped_existing", owner=owner)
        return None

    # Create key on OpenRouter — hard fail if provisioning is unavailable.
    provisioned: ProvisionedKey | None = await create_or_key(
        owner,
        limit_usd=float(spend_cap_usd) if spend_cap_usd is not None else None,
    )
    if provisioned is None:
        logger.error("auto_provision_failed", owner=owner)
        from app.exceptions import RouterVError
        raise RouterVError("Key provisioning failed. Please try again or contact support.")

    # Prefer GCP Secret Manager; fall back to storing the plaintext inline.
    # Inline storage (secret_ref starts with "sk-") is handled by the resolver.
    secret_ref: str
    secret_id = f"openrouter-{owner.lower().replace(' ', '-').replace('_', '-')}"
    version_ref = await store_secret(
        secret_id=secret_id,
        value=provisioned.plaintext,
        project_id=settings.gcp_project_id,
    )
    if version_ref is not None:
        secret_ref = f"projects/{settings.gcp_project_id}/secrets/{secret_id}/versions/latest"
        logger.info("auto_provision_stored_sm", owner=owner, secret_id=secret_id)
    else:
        # Secret Manager not configured — store plaintext directly in the row.
        # The resolver detects inline keys by the "sk-" prefix and returns them
        # without a Secret Manager lookup.
        secret_ref = provisioned.plaintext
        logger.info("auto_provision_stored_inline", owner=owner)

    pk = ProviderKey(
        owner=owner,
        provider="openrouter",
        secret_ref=secret_ref,
        or_key_hash=provisioned.or_hash,
        label=f"auto-provisioned for {owner}",
    )
    db.add(pk)
    await db.flush()
    await db.refresh(pk)
    logger.info("auto_provision_complete", owner=owner, pk_id=str(pk.id))
    return pk


@router.post("/keys", response_model=CreateKeyResponse, status_code=201)
async def create_key(
    body: CreateKeyRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new RouterV API key.

    On first key creation for an owner, auto-provisions a dedicated upstream
    provider key via the OpenRouter Management API (if configured).
    The plaintext RouterV key is returned exactly once — store it securely.
    """
    spend_cap = Decimal(str(body.spend_cap_usd)) if body.spend_cap_usd is not None else None
    rpm, rpd = _clamp_rate_limits(body.rpm_limit, body.rpd_limit)

    # Auto-provision an upstream provider key for this owner if needed.
    provider_key = await _auto_provision_for_owner(body.owner, spend_cap, db)

    raw_key = _generate_key()
    key = ApiKey(
        key_hash=_hash_key(raw_key),
        owner=body.owner,
        default_model=body.default_model,
        default_params=body.default_params,
        meta=body.meta,
        rpm_limit=rpm,
        rpd_limit=rpd,
        spend_cap_usd=spend_cap,
        provider_key_id=provider_key.id if provider_key else None,
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)

    logger.info(
        "admin_key_created",
        key_id=str(key.id),
        owner=key.owner,
        provisioned=provider_key is not None,
    )

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
    keys = result.scalars().all()
    owner_ids = list({k.owner for k in keys})
    email_by_owner: dict[str, str] = {}
    if owner_ids:
        email_q = await db.execute(select(User.id, User.email).where(User.id.in_(owner_ids)))
        email_by_owner = {row.id: row.email for row in email_q.all()}
    return [_to_summary(k, email=email_by_owner.get(k.owner)) for k in keys]


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
    if body.rpm_limit is not None or body.rpd_limit is not None:
        rpm, rpd = _clamp_rate_limits(body.rpm_limit, body.rpd_limit)
        if rpm is not None:
            key.rpm_limit = rpm
        if rpd is not None:
            key.rpd_limit = rpd
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

class KeyModelBreakdown(BaseModel):
    model: str
    requests: int
    cost_usd: float


class KeyUsageSummary(BaseModel):
    key_id: str
    owner: str
    total_requests: int
    successful_requests: int
    error_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    spend_cap_usd: str | None
    spend_cap_remaining_usd: str | None
    model_breakdown: list[KeyModelBreakdown]


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
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(UsageEvent.completion_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
            func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
            func.count(UsageEvent.id).filter(UsageEvent.status == "error").label("errors"),
        ).where(UsageEvent.key_id == uid)
    )
    r = row.one()

    breakdown_rows = await db.execute(
        select(
            UsageEvent.model,
            func.count(UsageEvent.id).label("requests"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
        )
        .where(UsageEvent.key_id == uid)
        .group_by(UsageEvent.model)
        .order_by(func.count(UsageEvent.id).desc())
    )

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
        total_input_tokens=r.input_tokens,
        total_output_tokens=r.output_tokens,
        total_cost_usd=float(total_cost),
        spend_cap_usd=str(key.spend_cap_usd) if key.spend_cap_usd else None,
        spend_cap_remaining_usd=str(remaining) if remaining is not None else None,
        model_breakdown=[
            KeyModelBreakdown(model=b.model, requests=b.requests, cost_usd=float(b.cost))
            for b in breakdown_rows.all()
        ],
    )


# ── Users list ────────────────────────────────────────────────────────────────

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


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all users from the users table, enriched with balance and spend.
    """
    users_q = await db.execute(select(User))
    all_users = users_q.scalars().all()

    if not all_users:
        return []

    user_ids = [u.id for u in all_users]

    # Aggregate key stats per user
    keys_q = await db.execute(
        select(
            ApiKey.owner.label("owner"),
            func.count(ApiKey.id).label("key_count"),
            func.count(ApiKey.id).filter(ApiKey.status == "active").label("active_key_count"),
        )
        .where(ApiKey.owner.in_(user_ids))
        .group_by(ApiKey.owner)
    )
    keys_by_user = {r.owner: r for r in keys_q.all()}

    # Total recharged per user via payment_events (amount_usd is in cents, always set)
    recharge_q = await db.execute(
        select(
            PaymentEvent.user_id.label("owner"),
            func.sum(PaymentEvent.amount_usd).label("total_recharged_cents"),
        )
        .where(PaymentEvent.user_id.in_(user_ids))
        .group_by(PaymentEvent.user_id)
    )
    recharge_by_user = {r.owner: r.total_recharged_cents for r in recharge_q.all()}

    # Last activity per user via usage_events
    activity_q = await db.execute(
        select(
            ApiKey.owner.label("owner"),
            func.max(UsageEvent.created_at).label("last_activity"),
        )
        .outerjoin(UsageEvent, UsageEvent.key_id == ApiKey.id)
        .where(ApiKey.owner.in_(user_ids))
        .group_by(ApiKey.owner)
    )
    activity_by_user = {r.owner: r.last_activity for r in activity_q.all()}

    # Balance per user
    bal_q = await db.execute(select(UserBalance).where(UserBalance.user_id.in_(user_ids)))
    bal_by_user = {str(b.user_id): b for b in bal_q.scalars().all()}

    results = []
    for u in all_users:
        keys_row = keys_by_user.get(u.id)
        bal = bal_by_user.get(u.id)
        total_recharged = Decimal(recharge_by_user.get(u.id) or 0) / 100
        balance = Decimal(str(bal.balance_usd)) if bal else Decimal(0)
        total_spent = max(total_recharged - balance, Decimal(0))
        last_activity = activity_by_user.get(u.id)
        results.append(UserSummary(
            user_id=u.id,
            email=u.email,
            display_name=u.display_name,
            key_count=keys_row.key_count if keys_row else 0,
            active_key_count=keys_row.active_key_count if keys_row else 0,
            total_spent_usd=str(total_spent),
            balance_usd=str(bal.balance_usd) if bal else None,
            last_activity=last_activity.isoformat() if last_activity else None,
            created_at=u.created_at.isoformat(),
        ))

    results.sort(key=lambda x: x.last_activity or "", reverse=True)
    return results

# ── Usage breakdowns ──────────────────────────────────────────────────────────

class ModelUsageRow(BaseModel):
    model: str
    requests: int
    successful_requests: int
    total_tokens: int | None
    total_cost_usd: str


class OwnerUsageRow(BaseModel):
    owner: str
    email: str | None = None
    requests: int
    successful_requests: int
    total_tokens: int | None
    total_cost_usd: str


@router.get("/usage/by-model", response_model=list[ModelUsageRow])
async def get_usage_by_model(
    db: AsyncSession = Depends(get_db_session),
):
    """Usage breakdown grouped by model, sorted by cost descending."""
    rows = await db.execute(
        select(
            UsageEvent.model,
            func.count(UsageEvent.id).label("requests"),
            func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
        ).group_by(UsageEvent.model).order_by(func.sum(UsageEvent.cost_usd).desc().nulls_last())
    )
    return [
        ModelUsageRow(
            model=r.model,
            requests=r.requests,
            successful_requests=r.success,
            total_tokens=r.tokens if r.tokens else None,
            total_cost_usd=str(Decimal(str(r.cost))),
        )
        for r in rows.all()
    ]


@router.get("/usage/by-owner", response_model=list[OwnerUsageRow])
async def get_usage_by_owner(
    db: AsyncSession = Depends(get_db_session),
):
    """Usage breakdown grouped by key owner, sorted by cost descending."""
    rows = await db.execute(
        select(
            ApiKey.owner,
            func.count(UsageEvent.id).label("requests"),
            func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
        )
        .outerjoin(UsageEvent, UsageEvent.key_id == ApiKey.id)
        .group_by(ApiKey.owner)
        .order_by(func.sum(UsageEvent.cost_usd).desc().nulls_last())
    )
    usage_rows = rows.all()
    owner_ids = list({r.owner for r in usage_rows})
    email_by_owner: dict[str, str] = {}
    if owner_ids:
        email_q = await db.execute(select(User.id, User.email).where(User.id.in_(owner_ids)))
        email_by_owner = {row.id: row.email for row in email_q.all()}
    return [
        OwnerUsageRow(
            owner=r.owner,
            email=email_by_owner.get(r.owner),
            requests=r.requests,
            successful_requests=r.success,
            total_tokens=r.tokens if r.tokens else None,
            total_cost_usd=str(Decimal(str(r.cost))),
        )
        for r in usage_rows
    ]


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


def _to_summary(k: ApiKey, *, email: str | None = None) -> KeySummary:
    return KeySummary(
        id=str(k.id),
        owner=k.owner,
        email=email,
        status=k.status,
        default_model=k.default_model,
        default_params=k.default_params,
        rpm_limit=k.rpm_limit,
        rpd_limit=k.rpd_limit,
        spend_cap_usd=str(k.spend_cap_usd) if k.spend_cap_usd is not None else None,
        created_at=k.created_at.isoformat(),
        updated_at=k.updated_at.isoformat(),
    )


# ── Admin: provider key management ───────────────────────────────────────────
# Dev-only convenience endpoints — no bearer auth needed here because the
# entire admin router is gated behind ENV=dev.

class AdminCreateProviderKeyRequest(BaseModel):
    owner: str
    provider: str = "openrouter"
    secret_ref: str
    label: str | None = None


class AdminProviderKeyOut(BaseModel):
    id: str
    owner: str
    email: str | None = None
    provider: str
    secret_ref: str
    label: str | None
    is_active: bool
    created_at: str
    secret_reachable: bool | None = None


def _mask_secret_ref(ref: str) -> str:
    if len(ref) > 15:
        return f"{ref[:10]}**********{ref[-5:]}"
    return ref


def _to_pk_out(
    pk: ProviderKey, *, email: str | None = None, secret_reachable: bool | None = None
) -> AdminProviderKeyOut:
    return AdminProviderKeyOut(
        id=str(pk.id),
        owner=pk.owner,
        email=email,
        provider=pk.provider,
        secret_ref=_mask_secret_ref(pk.secret_ref),
        label=pk.label,
        is_active=pk.is_active,
        created_at=pk.created_at.isoformat(),
        secret_reachable=secret_reachable,
    )


@router.post("/provider-keys", response_model=AdminProviderKeyOut, status_code=201)
async def admin_create_provider_key(
    body: AdminCreateProviderKeyRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a provider key record for any owner (dev admin convenience).
    In prod, owners manage their own keys via POST /v1/provider-keys.
    """
    pk = ProviderKey(
        owner=body.owner,
        provider=body.provider,
        secret_ref=body.secret_ref,
        label=body.label,
    )
    db.add(pk)
    await db.flush()
    await db.refresh(pk)
    logger.info("admin_provider_key_created", pk_id=str(pk.id), owner=pk.owner)
    return _to_pk_out(pk)


@router.get("/provider-keys", response_model=list[AdminProviderKeyOut])
async def admin_list_provider_keys(
    db: AsyncSession = Depends(get_db_session),
):
    """List all provider keys across all owners."""
    result = await db.execute(
        select(ProviderKey).order_by(ProviderKey.created_at.desc())
    )
    pks = result.scalars().all()
    owner_ids = list({pk.owner for pk in pks})
    email_by_owner: dict[str, str] = {}
    if owner_ids:
        email_q = await db.execute(select(User.id, User.email).where(User.id.in_(owner_ids)))
        email_by_owner = {row.id: row.email for row in email_q.all()}
    return [_to_pk_out(pk, email=email_by_owner.get(pk.owner)) for pk in pks]


@router.get("/provider-keys/{pk_id}", response_model=AdminProviderKeyOut)
async def admin_get_provider_key(
    pk_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a single provider key by ID and probe its Secret Manager reference."""
    uid = _parse_uuid(pk_id)
    result = await db.execute(select(ProviderKey).where(ProviderKey.id == uid))
    pk = result.scalar_one_or_none()
    if pk is None:
        raise NotFoundError("Provider key not found.")

    secret = await fetch_secret(pk.secret_ref)
    return _to_pk_out(pk, secret_reachable=secret is not None)


@router.delete("/provider-keys/{pk_id}", status_code=204)
async def admin_delete_provider_key(
    pk_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Hard-delete a provider key and evict its Secret Manager cache."""
    uid = _parse_uuid(pk_id)
    result = await db.execute(select(ProviderKey).where(ProviderKey.id == uid))
    pk = result.scalar_one_or_none()
    if pk is None:
        raise NotFoundError("Provider key not found.")

    await invalidate_secret_cache(pk.secret_ref)
    await db.delete(pk)
    logger.info("admin_provider_key_deleted", pk_id=str(pk.id), owner=pk.owner)


@router.post("/provider-keys/{pk_id}/rotate", response_model=AdminProviderKeyOut)
async def admin_rotate_provider_key(
    pk_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Zero-downtime rotation of a provider key.

    Steps:
      1. Create a new key on OpenRouter (Management API).
      2. Store new plaintext in GCP Secret Manager (new version).
      3. Update provider_keys.secret_ref to point to new version.
      4. Evict Redis cache for old secret_ref.
      5. Delete old key from OpenRouter.

    The Secret Manager path uses /versions/latest, so step 3 is only needed
    when the secret_id changes.  If you just add a new SM version under the
    same secret name, existing requests will pick it up at next TTL expiry.
    """
    uid = _parse_uuid(pk_id)
    result = await db.execute(select(ProviderKey).where(ProviderKey.id == uid))
    pk = result.scalar_one_or_none()
    if pk is None:
        raise NotFoundError("Provider key not found.")

    # 1. Create replacement key on OpenRouter.
    new_provisioned = await create_or_key(pk.owner)
    if new_provisioned is None:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter provisioning unavailable — management key not configured.",
        )

    # 2. Store new plaintext in Secret Manager.
    secret_id = f"openrouter-{pk.owner.lower().replace(' ', '-').replace('_', '-')}"
    new_version_ref = await store_secret(
        secret_id=secret_id,
        value=new_provisioned.plaintext,
        project_id=settings.gcp_project_id,
    )

    old_secret_ref = pk.secret_ref
    old_or_hash = pk.or_key_hash

    # 3. Update the row — /versions/latest always resolves to newest version.
    if new_version_ref:
        pk.secret_ref = (
            f"projects/{settings.gcp_project_id}/secrets/{secret_id}/versions/latest"
        )
    pk.or_key_hash = new_provisioned.or_hash

    await db.flush()
    await db.refresh(pk)

    # 4. Evict old cached secret so next request fetches the new version.
    await invalidate_secret_cache(old_secret_ref)

    # 5. Delete old OpenRouter key (fire-and-forget — failure is non-fatal).
    if old_or_hash:
        await delete_or_key(old_or_hash)

    logger.info("admin_provider_key_rotated", pk_id=str(pk.id), owner=pk.owner)
    return _to_pk_out(pk)


# ── Admin: model pricing ──────────────────────────────────────────────────────

def _per_1m(per_1k: Decimal | None) -> str | None:
    """Convert a stored per-1K price to per-1M for API responses. Exact Decimal arithmetic."""
    if per_1k is None:
        return None
    return str((per_1k * 1000).quantize(Decimal("0.00000001")))


def _resolve_per_1k(per_1k: float | None, per_1m: float | None, field: str) -> Decimal | None:
    """
    Resolve the effective per-1K Decimal from either input unit.
    Converts via str() to avoid binary float imprecision.
    Raises ValueError if both units are supplied for the same field.
    """
    if per_1k is not None and per_1m is not None:
        raise ValueError(f"Provide {field} in either per-1K or per-1M, not both")
    if per_1k is not None:
        return Decimal(str(per_1k))
    if per_1m is not None:
        return (Decimal(str(per_1m)) / 1000).quantize(Decimal("0.00000001"))
    return None


class ModelPriceIn(BaseModel):
    model_id: str
    provider: str = "openrouter"
    is_default: bool = False
    # Supply price in either per-1K or per-1M — not both for the same field.
    prompt_usd_per_1k: float | None = None
    completion_usd_per_1k: float | None = None
    prompt_usd_per_1m: float | None = None
    completion_usd_per_1m: float | None = None
    is_free: bool = False
    # Optional: create a model-level discount (applies to all users) in the same request.
    discount_pct: float | None = None   # 0–100; None = no discount created
    # What the upstream provider charges us — used to calculate upstream_cost_usd
    # in usage_events for providers that don't report cost in their API response
    # (Vertex AI, Bedrock, OpenAI Direct, Qwen).  Leave unset for OpenRouter
    # (it reports upstream cost directly in the response).
    upstream_prompt_usd_per_1k: float | None = None
    upstream_completion_usd_per_1k: float | None = None
    upstream_prompt_usd_per_1m: float | None = None
    upstream_completion_usd_per_1m: float | None = None

    @model_validator(mode="after")
    def _validate_pricing_consistency(self) -> "ModelPriceIn":
        # Reject supplying the same price field in both per-1K and per-1M units.
        for field, per_1k, per_1m in [
            ("prompt", self.prompt_usd_per_1k, self.prompt_usd_per_1m),
            ("completion", self.completion_usd_per_1k, self.completion_usd_per_1m),
            ("upstream_prompt", self.upstream_prompt_usd_per_1k, self.upstream_prompt_usd_per_1m),
            ("upstream_completion", self.upstream_completion_usd_per_1k, self.upstream_completion_usd_per_1m),
        ]:
            if per_1k is not None and per_1m is not None:
                raise ValueError(
                    f"Provide '{field}' price in either per-1K or per-1M, not both"
                )
        # Enforce is_free invariant: non-zero explicit prices are forbidden on a free model.
        if self.is_free:
            for field, per_1k, per_1m in [
                ("prompt", self.prompt_usd_per_1k, self.prompt_usd_per_1m),
                ("completion", self.completion_usd_per_1k, self.completion_usd_per_1m),
            ]:
                val = per_1k if per_1k is not None else per_1m
                if val is not None and val != 0:
                    raise ValueError(
                        f"Cannot set non-zero '{field}' price when is_free=True"
                    )
        return self

    def resolved_prompt(self) -> Decimal:
        v = _resolve_per_1k(self.prompt_usd_per_1k, self.prompt_usd_per_1m, "prompt")
        if v is None:
            raise ValueError("prompt price is required (provide prompt_usd_per_1k or prompt_usd_per_1m)")
        return v

    def resolved_completion(self) -> Decimal:
        v = _resolve_per_1k(self.completion_usd_per_1k, self.completion_usd_per_1m, "completion")
        if v is None:
            raise ValueError("completion price is required (provide completion_usd_per_1k or completion_usd_per_1m)")
        return v

    def resolved_upstream_prompt(self) -> Decimal | None:
        return _resolve_per_1k(self.upstream_prompt_usd_per_1k, self.upstream_prompt_usd_per_1m, "upstream_prompt")

    def resolved_upstream_completion(self) -> Decimal | None:
        return _resolve_per_1k(self.upstream_completion_usd_per_1k, self.upstream_completion_usd_per_1m, "upstream_completion")


class ModelPriceUpdateIn(BaseModel):
    # Supply price in either per-1K or per-1M — not both for the same field.
    prompt_usd_per_1k: float | None = None
    completion_usd_per_1k: float | None = None
    prompt_usd_per_1m: float | None = None
    completion_usd_per_1m: float | None = None
    is_free: bool | None = None
    is_default: bool | None = None
    upstream_prompt_usd_per_1k: float | None = None
    upstream_completion_usd_per_1k: float | None = None
    upstream_prompt_usd_per_1m: float | None = None
    upstream_completion_usd_per_1m: float | None = None

    @model_validator(mode="after")
    def _validate_dual_units(self) -> "ModelPriceUpdateIn":
        # Reject supplying the same price field in both per-1K and per-1M units.
        for field, per_1k, per_1m in [
            ("prompt", self.prompt_usd_per_1k, self.prompt_usd_per_1m),
            ("completion", self.completion_usd_per_1k, self.completion_usd_per_1m),
            ("upstream_prompt", self.upstream_prompt_usd_per_1k, self.upstream_prompt_usd_per_1m),
            ("upstream_completion", self.upstream_completion_usd_per_1k, self.upstream_completion_usd_per_1m),
        ]:
            if per_1k is not None and per_1m is not None:
                raise ValueError(
                    f"Provide '{field}' price in either per-1K or per-1M, not both"
                )
        # Body-level is_free guard (full enforcement against existing DB row happens in handler).
        if self.is_free is True:
            for field, per_1k, per_1m in [
                ("prompt", self.prompt_usd_per_1k, self.prompt_usd_per_1m),
                ("completion", self.completion_usd_per_1k, self.completion_usd_per_1m),
            ]:
                val = per_1k if per_1k is not None else per_1m
                if val is not None and val != 0:
                    raise ValueError(
                        f"Cannot set non-zero '{field}' price when is_free=True"
                    )
        return self

    def resolved_prompt(self) -> Decimal | None:
        return _resolve_per_1k(self.prompt_usd_per_1k, self.prompt_usd_per_1m, "prompt")

    def resolved_completion(self) -> Decimal | None:
        return _resolve_per_1k(self.completion_usd_per_1k, self.completion_usd_per_1m, "completion")

    def resolved_upstream_prompt(self) -> Decimal | None:
        return _resolve_per_1k(self.upstream_prompt_usd_per_1k, self.upstream_prompt_usd_per_1m, "upstream_prompt")

    def resolved_upstream_completion(self) -> Decimal | None:
        return _resolve_per_1k(self.upstream_completion_usd_per_1k, self.upstream_completion_usd_per_1m, "upstream_completion")


class ModelPriceOut(BaseModel):
    model_id: str
    provider: str
    is_default: bool
    prompt_usd_per_1k: str
    completion_usd_per_1k: str
    prompt_usd_per_1m: str
    completion_usd_per_1m: str
    is_free: bool
    upstream_prompt_usd_per_1k: str | None
    upstream_completion_usd_per_1k: str | None
    upstream_prompt_usd_per_1m: str | None
    upstream_completion_usd_per_1m: str | None
    updated_at: str


def _to_price_out(p: ModelPrice) -> ModelPriceOut:
    return ModelPriceOut(
        model_id=p.model_id,
        provider=p.provider,
        is_default=p.is_default,
        prompt_usd_per_1k=str(p.prompt_usd_per_1k),
        completion_usd_per_1k=str(p.completion_usd_per_1k),
        prompt_usd_per_1m=_per_1m(p.prompt_usd_per_1k),
        completion_usd_per_1m=_per_1m(p.completion_usd_per_1k),
        is_free=p.is_free,
        upstream_prompt_usd_per_1k=str(p.upstream_prompt_usd_per_1k) if p.upstream_prompt_usd_per_1k is not None else None,
        upstream_completion_usd_per_1k=str(p.upstream_completion_usd_per_1k) if p.upstream_completion_usd_per_1k is not None else None,
        upstream_prompt_usd_per_1m=_per_1m(p.upstream_prompt_usd_per_1k),
        upstream_completion_usd_per_1m=_per_1m(p.upstream_completion_usd_per_1k),
        updated_at=p.updated_at.isoformat(),
    )


_MODELS_CACHE_KEY = "routerv:models:list"


async def _invalidate_models_cache() -> None:
    """
    Evict the public models list cache so the next request fetches fresh data.

    Called after any admin write to `models` or `model_prices` so that
    changes are visible within seconds rather than waiting for the 5-min TTL.
    """
    redis = get_redis()
    if redis is not None:
        try:
            await redis.delete(_MODELS_CACHE_KEY)
        except Exception as exc:  # noqa: BLE001
            logger.warning("models_cache_invalidation_failed", error=str(exc))


async def _clear_default( model_id: str, db: AsyncSession) -> None:
    """Clear is_default on all provider rows for the given model_id."""
    await db.execute(
        update(ModelPrice)
        .where(ModelPrice.model_id == model_id, ModelPrice.is_default.is_(True))
        .values(is_default=False)
    )


@router.post("/model-prices", response_model=ModelPriceOut, status_code=201)
async def create_model_price(
    body: ModelPriceIn,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create or replace pricing for a (model_id, provider) pair.

    Setting is_default=true atomically clears the flag on any other provider
    row for this model_id so exactly one default exists per model.
    """
    existing = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == body.model_id,
            ModelPrice.provider == body.provider,
        )
    )
    price = existing.scalar_one_or_none()

    # If making this the default, clear any existing default first
    if body.is_default:
        await _clear_default(body.model_id, db)

    if body.is_free:
        # is_free rows must always store zero prices — never retain billable values.
        effective_prompt = Decimal("0")
        effective_completion = Decimal("0")
        up_prompt: Decimal | None = None
        up_completion: Decimal | None = None
    else:
        effective_prompt = body.resolved_prompt()
        effective_completion = body.resolved_completion()
        up_prompt = body.resolved_upstream_prompt()
        up_completion = body.resolved_upstream_completion()

    if price is None:
        price = ModelPrice(
            model_id=body.model_id,
            provider=body.provider,
            is_default=body.is_default,
            prompt_usd_per_1k=effective_prompt,
            completion_usd_per_1k=effective_completion,
            is_free=body.is_free,
            upstream_prompt_usd_per_1k=up_prompt,
            upstream_completion_usd_per_1k=up_completion,
        )
        db.add(price)
    else:
        price.is_default = body.is_default
        price.prompt_usd_per_1k = effective_prompt
        price.completion_usd_per_1k = effective_completion
        price.is_free = body.is_free
        price.upstream_prompt_usd_per_1k = up_prompt
        price.upstream_completion_usd_per_1k = up_completion

    await db.flush()
    await db.refresh(price)

    # Optionally create a model-level discount (user_id=None = all users) in the same transaction.
    if body.discount_pct is not None:
        from datetime import UTC, datetime as _dt
        if not (0 <= body.discount_pct <= 100):
            raise HTTPException(status_code=422, detail="discount_pct must be between 0 and 100")
        _now = _dt.now(UTC)
        existing_result = await db.execute(
            select(Discount).where(
                Discount.user_id.is_(None),
                Discount.model_id == body.model_id,
                or_(Discount.valid_until.is_(None), Discount.valid_until > _now),
                Discount.ended_at.is_(None),
            )
        )
        existing_discounts = existing_result.scalars().all()
        for d_old in existing_discounts:
            d_old.valid_until = _now
            d_old.ended_at = _now
            d_old.ended_reason = "replaced"
            logger.info("discount_expired_before_replace", model_id=body.model_id, discount_id=str(d_old.id))
        discount = Discount(
            user_id=None,
            model_id=body.model_id,
            discount_pct=Decimal(str(body.discount_pct)),
            valid_from=_now,
            label=f"Auto-created with model price for {body.model_id}",
        )
        db.add(discount)
        await db.flush()
        bind_contextvars(model_id=body.model_id)
        logger.info("discount_created_with_price", model_id=body.model_id, pct=body.discount_pct)

    await _invalidate_models_cache()
    logger.info(
        "model_price_set",
        model_id=body.model_id,
        provider=body.provider,
        is_default=body.is_default,
        is_free=body.is_free,
    )
    return _to_price_out(price)


@router.get("/model-prices", response_model=list[ModelPriceOut])
async def list_model_prices(
    db: AsyncSession = Depends(get_db_session),
):
    """List all model prices (all providers per model)."""
    result = await db.execute(
        select(ModelPrice).order_by(ModelPrice.model_id, ModelPrice.provider)
    )
    return [_to_price_out(p) for p in result.scalars().all()]



@router.patch("/model-prices/{model_id:path}/{provider}", response_model=ModelPriceOut)
async def update_model_price(
    model_id: str,
    provider: str,
    body: ModelPriceUpdateIn,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update pricing fields for an existing (model_id, provider) row.

    Setting is_default=true atomically clears the flag on any other provider
    row for this model_id.
    """
    result = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == model_id,
            ModelPrice.provider == provider,
        )
    )
    price = result.scalar_one_or_none()
    if price is None:
        raise NotFoundError(f"Model price for '{model_id}/{provider}' not found.")

    if body.is_default is not None and body.is_default:
        await _clear_default(model_id, db)

    resolved_prompt = body.resolved_prompt()
    resolved_completion = body.resolved_completion()
    resolved_up_prompt = body.resolved_upstream_prompt()
    resolved_up_completion = body.resolved_upstream_completion()

    # Determine the effective is_free after applying the patch body.
    final_is_free = body.is_free if body.is_free is not None else price.is_free

    if final_is_free:
        # Free rows must never carry billable prices — clear regardless of input.
        price.prompt_usd_per_1k = Decimal("0")
        price.completion_usd_per_1k = Decimal("0")
        price.upstream_prompt_usd_per_1k = None
        price.upstream_completion_usd_per_1k = None
    else:
        if resolved_prompt is not None:
            price.prompt_usd_per_1k = resolved_prompt
        if resolved_completion is not None:
            price.completion_usd_per_1k = resolved_completion
        if resolved_up_prompt is not None:
            price.upstream_prompt_usd_per_1k = resolved_up_prompt
        if resolved_up_completion is not None:
            price.upstream_completion_usd_per_1k = resolved_up_completion
        # If any stored price is non-zero ensure is_free stays False.
        if price.prompt_usd_per_1k > 0 or price.completion_usd_per_1k > 0:
            final_is_free = False

    price.is_free = final_is_free
    if body.is_default is not None:
        price.is_default = body.is_default

    await db.flush()
    await db.refresh(price)
    await _invalidate_models_cache()
    logger.info("model_price_updated", model_id=model_id, provider=provider)
    return _to_price_out(price)


@router.delete("/model-prices/{model_id:path}/{provider}", status_code=204)
async def delete_model_price(
    model_id: str,
    provider: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Remove a (model_id, provider) row from the price table."""
    result = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == model_id,
            ModelPrice.provider == provider,
        )
    )
    price = result.scalar_one_or_none()
    if price is None:
        raise NotFoundError(f"Model price for '{model_id}/{provider}' not found.")
    await db.delete(price)
    await _invalidate_models_cache()
    logger.info("model_price_deleted", model_id=model_id, provider=provider)


class SeedPricesResponse(BaseModel):
    seeded: int
    skipped: int
    models: list[str]


@router.post("/model-prices/seed", response_model=SeedPricesResponse)
async def seed_model_prices(
    db: AsyncSession = Depends(get_db_session),
    overwrite: bool = False,
):
    """
    Fetch live pricing from OpenRouter's /api/v1/models and upsert into
    model_prices.

    OpenRouter returns pricing in USD per token; we store USD per 1k tokens.
    Models with prompt=0 and completion=0 are marked is_free=True.

    Set overwrite=true to update existing rows; default skips already-priced models.
    """
    import httpx
    from decimal import Decimal
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch OpenRouter models: {exc}")

    models_data = data.get("data", [])
    seeded_ids: list[str] = []
    skipped = 0

    for model in models_data:
        model_id: str = model.get("id", "")
        pricing = model.get("pricing") or {}

        try:
            prompt_per_token = float(pricing.get("prompt") or 0)
            completion_per_token = float(pricing.get("completion") or 0)
        except (ValueError, TypeError):
            skipped += 1
            continue

        if not model_id:
            skipped += 1
            continue

        # Convert per-token → per 1k tokens (Decimal-safe: avoid float * 1000 imprecision)
        prompt_per_1k = (Decimal(str(prompt_per_token)) * 1000).quantize(Decimal("0.00000001"))
        completion_per_1k = (Decimal(str(completion_per_token)) * 1000).quantize(Decimal("0.00000001"))
        is_free = prompt_per_token == 0 and completion_per_token == 0

        # ── Seed model_prices ──────────────────────────────────────────────
        price_stmt = pg_insert(ModelPrice).values(
            model_id=model_id,
            provider="openrouter",
            is_default=True,
            prompt_usd_per_1k=prompt_per_1k,
            completion_usd_per_1k=completion_per_1k,
            is_free=is_free,
        )
        if overwrite:
            price_stmt = price_stmt.on_conflict_do_update(
                index_elements=["model_id", "provider"],
                set_={
                    "prompt_usd_per_1k": price_stmt.excluded.prompt_usd_per_1k,
                    "completion_usd_per_1k": price_stmt.excluded.completion_usd_per_1k,
                    "is_free": price_stmt.excluded.is_free,
                    "updated_at": func.now(),
                },
            )
        else:
            price_stmt = price_stmt.on_conflict_do_nothing(index_elements=["model_id", "provider"])

        await db.execute(price_stmt)

        # ── Seed models (metadata) ─────────────────────────────────────────
        # name/context_length/description from OpenRouter; is_enabled=true by default.
        model_name: str = model.get("name") or model_id
        context_length: int | None = model.get("context_length")
        description: str | None = model.get("description")

        model_stmt = pg_insert(Model).values(
            model_id=model_id,
            name=model_name,
            context_length=context_length,
            description=description,
            is_enabled=True,
        )
        if overwrite:
            model_stmt = model_stmt.on_conflict_do_update(
                index_elements=["model_id"],
                set_={
                    "name": model_stmt.excluded.name,
                    "context_length": model_stmt.excluded.context_length,
                    "description": model_stmt.excluded.description,
                    "updated_at": func.now(),
                },
            )
        else:
            # Never overwrite is_enabled — admin may have toggled it deliberately
            model_stmt = model_stmt.on_conflict_do_nothing(index_elements=["model_id"])

        await db.execute(model_stmt)
        seeded_ids.append(model_id)

    await db.commit()
    await _invalidate_models_cache()
    logger.info("model_prices_seeded", count=len(seeded_ids), skipped=skipped, overwrite=overwrite)
    return SeedPricesResponse(seeded=len(seeded_ids), skipped=skipped, models=seeded_ids)


# ── Admin: model registry ─────────────────────────────────────────────────────

class ModelIn(BaseModel):
    model_id: str
    name: str
    brand: str | None = None
    context_length: int | None = None
    description: str | None = None
    is_enabled: bool = True


class ModelUpdateIn(BaseModel):
    name: str | None = None
    context_length: int | None = None
    description: str | None = None
    is_enabled: bool | None = None


class ModelRegistryOut(BaseModel):
    model_id: str
    name: str
    brand: str
    context_length: int | None
    description: str | None
    is_enabled: bool
    created_at: str
    updated_at: str
    prices: list[ModelPriceOut] = []
    max_discount_pct: str | None = None


def _to_model_out(
    m: Model,
    prices: list[ModelPrice] | None = None,
    max_discount_pct: str | None = None,
) -> ModelRegistryOut:
    return ModelRegistryOut(
        model_id=m.model_id,
        name=m.name,
        brand=m.brand,
        context_length=m.context_length,
        description=m.description,
        is_enabled=m.is_enabled,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
        prices=[_to_price_out(p) for p in (prices or [])],
        max_discount_pct=max_discount_pct,
    )


@router.post("/models", response_model=ModelRegistryOut, status_code=201)
async def create_model(
    body: ModelIn,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a model in the discovery whitelist.

    The model_id must match the identifier used in model_prices so that
    GET /v1/models can join the two tables. Creating a model here does not
    automatically create pricing — use POST /admin/model-prices for that.
    """
    existing = await db.get(Model, body.model_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Model '{body.model_id}' already exists.")

    model = Model(
        model_id=body.model_id,
        name=body.name,
        brand=body.brand or body.model_id.split("/")[0],
        context_length=body.context_length,
        description=body.description,
        is_enabled=body.is_enabled,
    )
    db.add(model)
    await db.flush()
    await db.refresh(model)
    await _invalidate_models_cache()
    logger.info("model_created", model_id=body.model_id, is_enabled=body.is_enabled)
    return _to_model_out(model)


@router.get("/models", response_model=list[ModelRegistryOut])
async def list_models_admin(
    db: AsyncSession = Depends(get_db_session),
):
    """List all models (including disabled) with their pricing rows. For the public listing use GET /v1/models."""
    result = await db.execute(
        select(Model, ModelPrice)
        .outerjoin(ModelPrice, ModelPrice.model_id == Model.model_id)
        .order_by(Model.model_id, ModelPrice.provider)
    )
    models_map: dict[str, tuple[Model, list[ModelPrice]]] = {}
    for m, mp in result.all():
        if m.model_id not in models_map:
            models_map[m.model_id] = (m, [])
        if mp is not None:
            models_map[m.model_id][1].append(mp)

    now = datetime.now(timezone.utc)
    active_filter = [
        Discount.is_active.is_(True),
        Discount.valid_from <= now,
        or_(Discount.valid_until.is_(None), Discount.valid_until > now),
    ]

    # Max discount per specific model
    model_rows = await db.execute(
        select(Discount.model_id, func.max(Discount.discount_pct).label("max_pct"))
        .where(Discount.model_id.is_not(None), *active_filter)
        .group_by(Discount.model_id)
    )
    max_discounts: dict[str, Decimal] = {r.model_id: r.max_pct for r in model_rows.all()}

    # Max account-level discount (no model_id) — applies to every model
    account_row = await db.execute(
        select(func.max(Discount.discount_pct).label("max_pct"))
        .where(Discount.model_id.is_(None), *active_filter)
    )
    global_max: Decimal | None = account_row.scalar_one_or_none()

    def _best(model_id: str) -> str | None:
        candidates = [v for v in [max_discounts.get(model_id), global_max] if v is not None]
        return str(max(candidates)) if candidates else None

    return [
        _to_model_out(m, prices, max_discount_pct=_best(m.model_id))
        for m, prices in models_map.values()
    ]


@router.patch("/models/{model_id:path}", response_model=ModelRegistryOut)
async def update_model(
    model_id: str,
    body: ModelUpdateIn,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update model metadata or toggle visibility.

    Setting is_enabled=false hides the model from GET /v1/models immediately
    (cache is invalidated). Existing API keys using this model continue to
    work — only discovery is affected.
    """
    model = await db.get(Model, model_id)
    if model is None:
        raise NotFoundError(f"Model '{model_id}' not found.")

    if body.name is not None:
        model.name = body.name
    if body.context_length is not None:
        model.context_length = body.context_length
    if body.description is not None:
        model.description = body.description
    if body.is_enabled is not None:
        model.is_enabled = body.is_enabled

    await db.flush()
    await db.refresh(model)
    await _invalidate_models_cache()
    logger.info("model_updated", model_id=model_id, is_enabled=model.is_enabled)
    return _to_model_out(model)


@router.delete("/models/{model_id:path}", status_code=204)
async def delete_model(
    model_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Hard-delete a model from the registry.

    This does NOT remove model_prices rows — pricing and routing data are
    retained for historical usage_events reconciliation. Consider using
    PATCH /admin/models/{model_id} with is_enabled=false instead.
    """
    model = await db.get(Model, model_id)
    if model is None:
        raise NotFoundError(f"Model '{model_id}' not found.")
    await db.delete(model)
    await _invalidate_models_cache()
    logger.info("model_deleted", model_id=model_id)


# ── Discounts ─────────────────────────────────────────────────────────────────


class DiscountEndedReason(str, Enum):
    DISABLED = "disabled"  # Admin manually deactivated via "Expire Now"
    REPLACED = "replaced"  # Admin expired to create a replacement discount
    EXPIRED = "expired"    # Discount reached its valid_until timestamp


class DiscountIn(BaseModel):
    user_id: str | None = None           # None = applies to all users for the given model
    model_id: str | None = None          # None = account-level (all models for this user)
    discount_pct: float                  # 0–100
    valid_from: datetime | None = None   # ISO8601 with timezone; defaults to now() if omitted
    valid_until: datetime | None = None  # ISO8601 with timezone; None = no expiry
    label: str | None = None

    @field_validator("valid_from", "valid_until", mode="after")
    @classmethod
    def require_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (include UTC offset)")
        return v


class DiscountUpdateIn(BaseModel):
    discount_pct: float | None = None
    valid_from: datetime | None = None   # ISO8601 with timezone; only editable for future discounts
    valid_until: datetime | None = None  # ISO8601 with timezone
    ended_reason: DiscountEndedReason | None = None
    label: str | None = None

    @field_validator("valid_from", "valid_until", mode="after")
    @classmethod
    def require_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (include UTC offset)")
        return v


class DiscountOut(BaseModel):
    id: str
    user_id: str | None
    email: str | None
    model_id: str | None
    discount_pct: str
    valid_from: str
    valid_until: str | None
    ended_at: str | None
    ended_reason: DiscountEndedReason | None
    label: str | None
    created_at: str


def _to_discount_out(d: Discount, *, email: str | None = None) -> DiscountOut:
    return DiscountOut(
        id=str(d.id),
        user_id=d.user_id,
        email=email,
        model_id=d.model_id,
        discount_pct=str(d.discount_pct),
        valid_from=d.valid_from.isoformat(),
        valid_until=d.valid_until.isoformat() if d.valid_until else None,
        ended_at=d.ended_at.isoformat() if d.ended_at else None,
        ended_reason=DiscountEndedReason(d.ended_reason) if d.ended_reason else None,
        label=d.label,
        created_at=d.created_at.isoformat(),
    )


@router.post("/discounts", response_model=DiscountOut, status_code=201)
async def create_discount(
    body: DiscountIn,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a discount. model_id=null = all models; user_id=null = all users.
    Returns 409 if an active (non-expired) discount already exists for the same scope key."""
    from datetime import UTC, datetime
    from decimal import Decimal as D

    if not (0 <= body.discount_pct <= 100):
        raise HTTPException(status_code=422, detail="discount_pct must be between 0 and 100")

    now = datetime.now(UTC)

    # Conflict check — only one active discount per (user_id, model_id) scope key
    conflict_result = await db.execute(
        select(Discount).where(
            Discount.user_id == body.user_id,
            Discount.model_id == body.model_id,
            or_(Discount.valid_until.is_(None), Discount.valid_until > now),
        )
    )
    conflicts = conflict_result.scalars().all()
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Active discount already exists for this scope. Expire the existing discount first.",
                "conflicts": [_to_discount_out(c).model_dump() for c in conflicts],
            },
        )

    d = Discount(
        user_id=body.user_id,
        model_id=body.model_id,
        discount_pct=D(str(body.discount_pct)),
        valid_from=body.valid_from or now,
        valid_until=body.valid_until,
        label=body.label,
    )
    db.add(d)
    await db.flush()
    await db.refresh(d)
    bind_contextvars(user_id=body.user_id, model_id=body.model_id)
    logger.info("discount_created", user_id=body.user_id, model_id=body.model_id, pct=body.discount_pct)
    return _to_discount_out(d)


@router.get("/discounts", response_model=list[DiscountOut])
async def list_discounts(
    user_id: str | None = None,
    model_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List discounts. Filter by ?user_id= or ?model_id=."""
    q = select(Discount).order_by(Discount.created_at.desc())
    if user_id:
        q = q.where(Discount.user_id == user_id)
    if model_id:
        q = q.where(Discount.model_id == model_id)
    result = await db.execute(q)
    discounts = result.scalars().all()
    uid_set = list({d.user_id for d in discounts})
    email_by_user: dict[str, str] = {}
    if uid_set:
        email_q = await db.execute(select(User.id, User.email).where(User.id.in_(uid_set)))
        email_by_user = {row.id: row.email for row in email_q.all()}
    return [_to_discount_out(d, email=email_by_user.get(d.user_id)) for d in discounts]


@router.patch("/discounts/{discount_id}", response_model=DiscountOut)
async def update_discount(
    discount_id: str,
    body: DiscountUpdateIn,
    db: AsyncSession = Depends(get_db_session),
):
    """Update discount percentage, expiry, or label.
    Setting valid_until to now-or-past retires the discount and stamps ended_at/ended_reason."""
    import uuid as _uuid
    from datetime import UTC, datetime
    from decimal import Decimal as D

    result = await db.execute(select(Discount).where(Discount.id == _uuid.UUID(discount_id)))
    d = result.scalar_one_or_none()
    if d is None:
        raise NotFoundError(f"Discount '{discount_id}' not found.")

    now = datetime.now(UTC)

    # Update only the fields provided in the request
    update_data = body.model_dump(exclude_unset=True)

    # discount_pct and valid_from are immutable once a discount has started
    if d.valid_from <= now:
        if "discount_pct" in update_data:
            raise HTTPException(
                status_code=422,
                detail="discount_pct cannot be changed after a discount has started.",
            )
        if "valid_from" in update_data:
            raise HTTPException(
                status_code=422,
                detail="valid_from cannot be changed after a discount has started.",
            )

    if "discount_pct" in update_data:
        val = update_data["discount_pct"]
        if not (0 <= val <= 100):
            raise HTTPException(status_code=422, detail="discount_pct must be between 0 and 100")
        d.discount_pct = D(str(val))

    if "valid_from" in update_data:
        d.valid_from = update_data["valid_from"]

    if "valid_until" in update_data:
        d.valid_until = update_data["valid_until"]
        # If valid_until is set to a past date, stamp audit fields
        if d.valid_until is not None and d.valid_until <= now:
            d.ended_at = now
            d.ended_reason = (body.ended_reason or DiscountEndedReason.DISABLED).value

    # Persist ended_reason whenever supplied, even without retiring the discount
    if body.ended_reason is not None and d.ended_at is None:
        d.ended_reason = body.ended_reason.value

    if "label" in update_data:
        d.label = update_data["label"]

    await db.flush()
    await db.refresh(d)
    bind_contextvars(discount_id=discount_id)
    logger.info("discount_updated", discount_id=discount_id)
    return _to_discount_out(d)


@router.delete("/discounts/{discount_id}", status_code=204)
async def delete_discount(
    discount_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Hard delete a discount."""
    import uuid as _uuid
    result = await db.execute(select(Discount).where(Discount.id == _uuid.UUID(discount_id)))
    d = result.scalar_one_or_none()
    if d is None:
        raise NotFoundError(f"Discount '{discount_id}' not found.")
    await db.delete(d)
    logger.info("discount_deleted", discount_id=discount_id)


# ── Balance monitoring ────────────────────────────────────────────────────────

class BalanceSummary(BaseModel):
    user_id: str
    email: str | None
    balance_usd: str
    total_spent_usd: str
    last_activity: str | None
    updated_at: str


class BalanceDetail(BaseModel):
    user_id: str
    balance_usd: str
    updated_at: str
    total_spent_usd: str
    by_model: list[dict]   # [{model, requests, cost_usd}]


@router.get("/balances", response_model=list[BalanceSummary])
async def list_balances(db: AsyncSession = Depends(get_db_session)):
    """
    List all user balances with total spend and last activity.
    Sorted by balance ascending (lowest first — easy to spot who needs top-up).
    """
    from sqlalchemy import cast, Float, literal_column, text as sa_text

    rows = await db.execute(sa_text("""
        SELECT
            ub.user_id,
            u.email,
            ub.balance_usd,
            ub.updated_at,
            GREATEST((COALESCE(SUM(pe.amount_usd), 0) / 100.0) - ub.balance_usd, 0) AS total_spent_usd
        FROM user_balances ub
        LEFT JOIN users u ON u.id = ub.user_id
        LEFT JOIN payment_events pe ON pe.user_id = ub.user_id
        GROUP BY ub.user_id, u.email, ub.balance_usd, ub.updated_at
        ORDER BY ub.balance_usd ASC
    """))

    return [
        BalanceSummary(
            user_id=r.user_id,
            email=r.email,
            balance_usd=str(r.balance_usd),
            total_spent_usd=str(r.total_spent_usd),
            last_activity=None,
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/balances/{user_id}", response_model=BalanceDetail)
async def get_balance(user_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Detailed balance for a specific user: current balance + spend broken down by model.
    """
    from sqlalchemy import text as sa_text

    balance_row = await db.execute(
        select(UserBalance).where(UserBalance.user_id == user_id)
    )
    balance = balance_row.scalar_one_or_none()
    if balance is None:
        raise NotFoundError(f"No balance record found for user '{user_id}'.")

    by_model_rows = await db.execute(sa_text("""
        SELECT
            ue.model,
            COUNT(*)                        AS requests,
            COALESCE(SUM(ue.cost_usd), 0)  AS cost_usd
        FROM api_keys ak
        JOIN usage_events ue ON ue.key_id = ak.id
        WHERE ak.owner = :user_id AND ue.status = 'success'
        GROUP BY ue.model
        ORDER BY cost_usd DESC
    """), {"user_id": user_id})

    total_spent = sum(r.cost_usd for r in by_model_rows)

    # Re-run (rows consumed above)
    by_model_rows2 = await db.execute(sa_text("""
        SELECT
            ue.model,
            COUNT(*)                        AS requests,
            COALESCE(SUM(ue.cost_usd), 0)  AS cost_usd
        FROM api_keys ak
        JOIN usage_events ue ON ue.key_id = ak.id
        WHERE ak.owner = :user_id AND ue.status = 'success'
        GROUP BY ue.model
        ORDER BY cost_usd DESC
    """), {"user_id": user_id})

    return BalanceDetail(
        user_id=user_id,
        balance_usd=str(balance.balance_usd),
        updated_at=balance.updated_at.isoformat(),
        total_spent_usd=str(total_spent),
        by_model=[
            {"model": r.model, "requests": r.requests, "cost_usd": str(r.cost_usd)}
            for r in by_model_rows2
        ],
    )


# ── Global Templates ──────────────────────────────────────────────────────────
#
# Global templates have owner=NULL. They are seeded by admins and are readable
# by all keys via the resolver's name-based fallback lookup.

_SYSTEM_OWNER = None  # NULL owner = global template


class GlobalTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    system: str | None = None
    messages: list[dict] | None = None
    model: str | None = None
    params: dict | None = None
    variables: list[str] | None = None


class GlobalTemplateUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    system: str | None = None
    messages: list[dict] | None = None
    model: str | None = None
    params: dict | None = None
    variables: list[str] | None = None


class GlobalTemplateSummary(BaseModel):
    id: str
    name: str
    description: str | None
    system: str | None
    messages: list[dict] | None
    model: str | None
    params: dict | None
    variables: list[str] | None
    created_at: str
    updated_at: str


def _global_template_to_summary(t: Template) -> GlobalTemplateSummary:
    return GlobalTemplateSummary(
        id=str(t.id),
        name=t.name,
        description=t.description,
        system=t.system,
        messages=t.messages,
        model=t.model,
        params=t.params,
        variables=t.variables,
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
    )


async def _get_global_or_404(db: AsyncSession, template_id: str) -> Template:
    try:
        uid = uuid.UUID(template_id)
    except ValueError:
        raise NotFoundError(f"Template '{template_id}' not found.")
    result = await db.execute(
        select(Template).where(Template.id == uid, Template.owner.is_(None))
    )
    t = result.scalar_one_or_none()
    if t is None:
        raise NotFoundError(f"Template '{template_id}' not found.")
    return t


@router.post("/templates", response_model=GlobalTemplateSummary, status_code=201)
async def create_global_template(
    body: GlobalTemplateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a global template (owner=NULL) usable by all API keys."""
    from sqlalchemy.exc import IntegrityError

    template = Template(
        name=body.name,
        owner=_SYSTEM_OWNER,
        description=body.description,
        system=body.system,
        messages=body.messages,
        model=body.model,
        params=body.params,
        variables=body.variables,
    )
    db.add(template)
    try:
        await db.flush()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A global template named '{body.name}' already exists.",
        )

    logger.info("global_template_created", template_id=str(template.id), name=template.name)
    return _global_template_to_summary(template)


@router.get("/templates", response_model=list[GlobalTemplateSummary])
async def list_global_templates(
    db: AsyncSession = Depends(get_db_session),
):
    """List all global templates."""
    result = await db.execute(
        select(Template)
        .where(Template.owner.is_(None))
        .order_by(Template.created_at.desc())
    )
    return [_global_template_to_summary(t) for t in result.scalars().all()]


@router.patch("/templates/{template_id}", response_model=GlobalTemplateSummary)
async def update_global_template(
    template_id: str,
    body: GlobalTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a global template."""
    from sqlalchemy.exc import IntegrityError

    template = await _get_global_or_404(db, template_id)

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.system is not None:
        template.system = body.system
    if body.messages is not None:
        template.messages = body.messages
    if body.model is not None:
        template.model = body.model
    if body.params is not None:
        template.params = body.params
    if body.variables is not None:
        template.variables = body.variables

    try:
        await db.flush()
        await db.refresh(template)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"A global template named '{body.name}' already exists.",
        )

    logger.info("global_template_updated", template_id=str(template.id), name=template.name)
    return _global_template_to_summary(template)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_global_template(
    template_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Hard delete a global template."""
    template = await _get_global_or_404(db, template_id)
    await db.delete(template)
    logger.info("global_template_deleted", template_id=str(template.id), name=template.name)
# ── Test & register models ─────────────────────────────────────────────────────

class TestModelItem(BaseModel):
    model_id: str
    """Canonical RouterSVC model ID, e.g. 'anthropic/claude-3-haiku'."""
    provider_model_id: str | None = None
    """
    Exact upstream model ID the provider expects, e.g.
    'us.anthropic.claude-3-haiku-20240307-v1:0' for Bedrock.
    If omitted, the adapter falls back to its internal _MODEL_MAP translation.
    Stored in model_prices.provider_model_id on success.
    """
    input_token_cost_per_1k: float | None = None
    output_token_cost_per_1k: float | None = None


class TestModelsRequest(BaseModel):
    is_dry_run: bool = True

    provider: str
    """
    Provider slug to test against: openrouter | vertex | bedrock | openai | qwen.
    Credentials are read from server config — no keys in the request body.
    """
    models: list[TestModelItem]
    """List of models to test."""
    prompt: str = "Reply with just the word OK and nothing else."
    timeout: float = 30.0


def _derive_model_name(model_id: str) -> str:
    """Derive a human-readable display name from a canonical model ID."""
    slug = model_id.split("/", 1)[-1]
    return slug.replace("-", " ").replace("_", " ").replace(".", " ").title()


async def _test_models_stream(body: TestModelsRequest) -> AsyncGenerator[bytes, None]:
    """
    Async generator that tests each model against the provider, writes results
    to the DB, and yields SSE events.

    Per-model DB logic
    ------------------
    models row       — INSERT if not exists (is_enabled=false); on pass → SET is_enabled=true
    model_prices row — INSERT if not exists (price=0, is_default=false); on pass →
                       if no other row for this model_id has is_default=true → SET is_default=true
    Both inserts use ON CONFLICT DO NOTHING — existing rows are never overwritten.
    """
    from app.db.engine import get_session_factory
    from app.providers.registry import get_adapter
    from app.schemas.chat import ChatCompletionRequest, Message

    # Validate provider has a registered adapter before streaming anything
    try:
        adapter = get_adapter(body.provider)
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n".encode()
        return

    session_factory = get_session_factory()
    passed = failed = 0

    for item in body.models:
        model_id              = item.model_id
        provider_model_id     = item.provider_model_id
        prompt_usd_per_1k     = item.input_token_cost_per_1k
        completion_usd_per_1k = item.output_token_cost_per_1k
        t0                    = time.monotonic()
        status                = "fail"
        error: str | None     = None

        # ── Test the model ─────────────────────────────────────────────────
        req = ChatCompletionRequest(
            model=model_id,
            messages=[Message(role="user", content=body.prompt)],
            max_tokens=32,
            stream=False,
        )
        try:
            resp = await asyncio.wait_for(
                adapter.chat_completion(
                    req, api_key=None, owner=None,
                    provider_model_id=provider_model_id,
                ),
                timeout=body.timeout,
            )
            # Verify the model responded — check content OR finish_reason
            # (reasoning models like gpt-5 may return null content)
            choice = (resp.get("choices") or [{}])[0]
            text = (choice.get("message", {}).get("content") or "").strip()
            finish_reason = choice.get("finish_reason") or ""
            if text or finish_reason:
                status = "pass"
            else:
                status = "fail"
                error  = "Empty response content"
        except asyncio.TimeoutError:
            status = "timeout"
            error  = f"Timed out after {body.timeout:.0f}s"
        except Exception as exc:  # noqa: BLE001
            status = "fail"
            error  = str(exc)[:200]

        latency_ms   = int((time.monotonic() - t0) * 1000)
        test_passed  = status == "pass"
        is_default   = False

        if test_passed:
            passed += 1
        else:
            failed += 1

        # ── DB writes (only on pass) ────────────────────────────────────────
        if test_passed and not body.is_dry_run:
            name = _derive_model_name(model_id)
            try:
                async with session_factory() as db:
                    # 1. Insert model row if it doesn't exist (disabled by default)
                    await db.execute(
                        pg_insert(Model).values(
                            model_id=model_id,
                            name=name,
                            context_length=None,
                            brand=model_id.split("/")[0],
                            description=None,
                            is_enabled=False,
                        ).on_conflict_do_nothing(index_elements=["model_id"])
                    )

                    # 2. Insert model_prices row if (model_id, provider) not present
                    await db.execute(
                        pg_insert(ModelPrice).values(
                            model_id=model_id,
                            provider=body.provider,
                            provider_model_id=provider_model_id,
                            is_default=False,
                            prompt_usd_per_1k=prompt_usd_per_1k,
                            completion_usd_per_1k=completion_usd_per_1k,
                            is_free=False,
                        ).on_conflict_do_nothing(index_elements=["model_id", "provider"])
                    )

                    if test_passed:
                        # 3. Enable the model
                        await db.execute(
                            update(Model)
                            .where(Model.model_id == model_id)
                            .values(is_enabled=True)
                        )

                        # 4. Clear any existing default, then set this provider as default
                        await db.execute(
                            update(ModelPrice)
                            .where(ModelPrice.model_id == model_id)
                            .values(is_default=False)
                        )
                        await db.execute(
                            update(ModelPrice)
                            .where(
                                ModelPrice.model_id == model_id,
                                ModelPrice.provider == body.provider,
                            )
                            .values(
                                is_default=True,
                                prompt_usd_per_1k=prompt_usd_per_1k,
                                completion_usd_per_1k=completion_usd_per_1k,
                            )
                        )
                        is_default = True

                    await db.commit()
            except Exception as db_exc:  # noqa: BLE001
                logger.exception(
                    "test_models_db_error",
                    model_id=model_id,
                    provider=body.provider,
                    error=str(db_exc),
                )

        # ── Yield SSE event ────────────────────────────────────────────────
        event = {
            "model_id":   model_id,
            "status":     status,
            "latency_ms": latency_ms,
            "is_default": is_default,
            "error":      error,
        }
        yield f"data: {json.dumps(event)}\n\n".encode()

    # Invalidate models cache so GET /v1/models reflects new state immediately
    try:
        redis = await get_redis()
        await redis.delete("routerv:models:list")
    except Exception:  # noqa: BLE001
        pass

    # Final summary event
    yield f"data: {json.dumps({'type': 'summary', 'total': len(body.models), 'passed': passed, 'failed': failed, 'is_dry_run': body.is_dry_run})}\n\n".encode()
    yield b"data: [DONE]\n\n"


# ── User detail analytics ─────────────────────────────────────────────────────

class UserDetailSummary(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None
    key_count: int
    active_key_count: int
    api_calls: int
    total_spent_usd: str
    total_paid_usd: str | None = None
    balance_usd: str | None
    last_activity: str | None
    created_at: str


class UsageTimeSeries(BaseModel):
    bucket: str   # ISO 8601 datetime string
    requests: int
    cost_usd: str


def _range_since(range_: str) -> datetime:
    now = datetime.now(timezone.utc)
    if range_ == "24h":
        return now - timedelta(hours=24)
    if range_ == "7d":
        return now - timedelta(days=7)
    return now - timedelta(days=30)  # default: 30d


@router.get("/users/{user_id}/summary", response_model=UserDetailSummary)
async def get_user_summary(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Per-user summary card data. Cached for 5 minutes."""
    redis = get_redis()
    cache_key = f"routerv:analytics:user_summary:{user_id}"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return UserDetailSummary(**json.loads(cached))

    # Keys owned by this user
    keys_result = await db.execute(
        select(
            func.count(ApiKey.id).label("key_count"),
            func.count(ApiKey.id).filter(ApiKey.status == "active").label("active_key_count"),
            func.min(ApiKey.created_at).label("created_at"),
        ).where(ApiKey.owner == user_id)
    )
    keys_row = keys_result.one()

    key_ids_result = await db.execute(
        select(ApiKey.id).where(ApiKey.owner == user_id)
    )
    key_ids = [r[0] for r in key_ids_result.all()]

    if key_ids:
        activity_result = await db.execute(
            select(
                func.count(UsageEvent.id).label("api_calls"),
                func.max(UsageEvent.created_at).label("last_activity"),
            ).where(UsageEvent.key_id.in_(key_ids))
        )
        activity_row = activity_result.one()
        api_calls = activity_row.api_calls or 0
        last_activity = activity_row.last_activity.isoformat() if activity_row.last_activity else None
    else:
        api_calls = 0
        last_activity = None

    bal_result = await db.execute(
        select(UserBalance.balance_usd).where(UserBalance.user_id == user_id)
    )
    bal = bal_result.scalar_one_or_none()

    recharge_result = await db.execute(
        select(func.coalesce(func.sum(PaymentEvent.amount_usd), 0))
        .where(PaymentEvent.user_id == user_id)
    )
    total_recharged = Decimal(recharge_result.scalar_one() or 0) / 100
    balance = bal if bal is not None else Decimal(0)
    total_spent = max(total_recharged - balance, Decimal(0))

    user_result = await db.execute(
        select(User.email, User.display_name).where(User.id == user_id)
    )
    user_rec = user_result.one_or_none()

    # Total paid by this user, using accurate per-payment USD conversion
    paid_result = await db.execute(
        select(func.coalesce(func.sum(_usd_amount_expr()), 0).label("total_paid"))
        .where(PaymentEvent.user_id == user_id)
    )
    total_paid_raw = paid_result.scalar_one()
    total_paid_usd = str(Decimal(str(total_paid_raw)).quantize(Decimal("0.0001")))

    result = UserDetailSummary(
        user_id=user_id,
        email=user_rec.email if user_rec else None,
        display_name=user_rec.display_name if user_rec else None,
        key_count=keys_row.key_count or 0,
        active_key_count=keys_row.active_key_count or 0,
        api_calls=api_calls,
        total_spent_usd=str(total_spent),
        total_paid_usd=total_paid_usd,
        balance_usd=str(bal) if bal is not None else None,
        last_activity=last_activity,
        created_at=keys_row.created_at.isoformat() if keys_row.created_at else datetime.now(timezone.utc).isoformat(),
    )

    if redis is not None:
        await set_analytics_cached(redis, cache_key, result.model_dump_json())

    return result


@router.get("/users/{user_id}/usage", response_model=list[UsageTimeSeries])
async def get_user_usage_timeseries(
    user_id: str,
    range: str = "7d",
    db: AsyncSession = Depends(get_db_session),
):
    """
    Requests + cost grouped by hour (24h) or day (7d/30d) for a single user.
    Cached for 5 minutes.
    """
    redis = get_redis()
    cache_key = f"routerv:analytics:user_usage:{user_id}:{range}"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [UsageTimeSeries(**r) for r in json.loads(cached)]

    since = _range_since(range)
    group_by = "hour" if range == "24h" else "day"

    key_ids_result = await db.execute(
        select(ApiKey.id).where(ApiKey.owner == user_id)
    )
    key_ids = [r[0] for r in key_ids_result.all()]

    if not key_ids:
        return []

    trunc_unit = text(f"'{group_by}'")
    rows = await db.execute(
        select(
            func.date_trunc(trunc_unit, UsageEvent.created_at).label("bucket"),
            func.count(UsageEvent.id).label("requests"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost_usd"),
        )
        .where(UsageEvent.key_id.in_(key_ids))
        .where(UsageEvent.created_at >= since)
        .group_by(func.date_trunc(trunc_unit, UsageEvent.created_at))
        .order_by(func.date_trunc(trunc_unit, UsageEvent.created_at))
    )

    result = [
        UsageTimeSeries(
            bucket=r.bucket.isoformat(),
            requests=r.requests,
            cost_usd=str(Decimal(str(r.cost_usd))),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


@router.get("/users/{user_id}/models", response_model=list[ModelUsageRow])
async def get_user_model_breakdown(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Model usage breakdown for a single user. Cached for 5 minutes."""
    redis = get_redis()
    cache_key = f"routerv:analytics:user_models:{user_id}"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [ModelUsageRow(**r) for r in json.loads(cached)]

    key_ids_result = await db.execute(
        select(ApiKey.id).where(ApiKey.owner == user_id)
    )
    key_ids = [r[0] for r in key_ids_result.all()]

    if not key_ids:
        return []

    rows = await db.execute(
        select(
            UsageEvent.model,
            func.count(UsageEvent.id).label("requests"),
            func.count(UsageEvent.id).filter(UsageEvent.status == "success").label("success"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost"),
        )
        .where(UsageEvent.key_id.in_(key_ids))
        .group_by(UsageEvent.model)
        .order_by(func.sum(UsageEvent.cost_usd).desc().nulls_last())
    )

    result = [
        ModelUsageRow(
            model=r.model,
            requests=r.requests,
            successful_requests=r.success,
            total_tokens=r.tokens if r.tokens else None,
            total_cost_usd=str(Decimal(str(r.cost))),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


@router.get("/users/{user_id}/events", response_model=UsageEventsPage)
async def get_user_events(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    since: str | None = None,
    until: str | None = None,
    model: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Paginated usage event log for a single user (admin-scoped)."""
    key_ids_result = await db.execute(
        select(ApiKey.id, ApiKey.meta).where(ApiKey.owner == user_id)
    )
    key_rows = key_ids_result.all()
    key_map = {row[0]: (row[1] or {}).get("label") for row in key_rows}
    key_ids = list(key_map)

    if not key_ids:
        return UsageEventsPage(events=[], total=0, limit=limit, offset=offset)

    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until, end_of_day=True)

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
    events = (await db.execute(
        base.order_by(UsageEvent.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()

    return UsageEventsPage(
        events=[
            UsageEventOut(
                id=str(e.id),
                key_id=str(e.key_id),
                key_label=key_map.get(e.key_id),
                request_id=e.request_id,
                model=e.model,
                model_name=_split_model(e.model)[0],
                model_provider=_split_model(e.model)[1],
                stream=e.stream,
                prompt_tokens=e.prompt_tokens,
                completion_tokens=e.completion_tokens,
                total_tokens=e.total_tokens,
                cost_usd=str(e.cost_usd) if e.cost_usd else None,
                latency_ms=e.latency_ms,
                tokens_per_second=_tokens_per_second(e.completion_tokens, e.latency_ms),
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


# ── System-wide usage time-series ─────────────────────────────────────────────

@router.get("/usage/timeseries", response_model=list[UsageTimeSeries])
async def get_usage_timeseries(
    range: str = "7d",
    db: AsyncSession = Depends(get_db_session),
):
    """
    System-wide requests + cost grouped by hour (24h) or day (7d/30d).
    Cached for 5 minutes.
    """
    redis = get_redis()
    cache_key = f"routerv:analytics:usage_timeseries:{range}"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [UsageTimeSeries(**r) for r in json.loads(cached)]

    since = _range_since(range)
    group_by = "hour" if range == "24h" else "day"

    trunc_unit = text(f"'{group_by}'")
    rows = await db.execute(
        select(
            func.date_trunc(trunc_unit, UsageEvent.created_at).label("bucket"),
            func.count(UsageEvent.id).label("requests"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("cost_usd"),
        )
        .where(UsageEvent.created_at >= since)
        .group_by(func.date_trunc(trunc_unit, UsageEvent.created_at))
        .order_by(func.date_trunc(trunc_unit, UsageEvent.created_at))
    )

    result = [
        UsageTimeSeries(
            bucket=r.bucket.isoformat(),
            requests=r.requests,
            cost_usd=str(Decimal(str(r.cost_usd))),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


# ── Payment analytics ─────────────────────────────────────────────────────────

def _usd_amount_expr():
    """
    Returns a SQLAlchemy expression for the USD value of a payment_events row.

    Priority:
      1. amount_usd column (pre-computed in cents at webhook ingestion time) — most
         accurate because it captures the exact rate used at payment time.
      2. Fallback for older rows where amount_usd IS NULL: divide the raw amount by
         the FX rate that was in effect at or before the payment's created_at.
         Uses a time-bounded correlated subquery with the composite index
         ix_currency_conversion_rates_currency_created.
    """
    from sqlalchemy import case as sa_case

    time_bounded_rate_sq = (
        select(CurrencyConversionRate.total_rate)
        .where(CurrencyConversionRate.currency == PaymentEvent.currency)
        .where(CurrencyConversionRate.created_at <= PaymentEvent.created_at)
        .order_by(CurrencyConversionRate.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    return sa_case(
        (PaymentEvent.amount_usd.isnot(None), PaymentEvent.amount_usd / 100.0),
        else_=func.coalesce(PaymentEvent.amount, 0) / 100.0 / func.coalesce(time_bounded_rate_sq, 1.0),
    )


class PaymentSummary(BaseModel):
    total_revenue: str
    today_revenue: str
    month_revenue: str
    total_transactions: int = 0
    avg_transaction_usd: str | None = None


class PaymentTransactionOut(BaseModel):
    id: str
    user_id: str
    payment_id: str
    provider: str
    order_id: str | None
    currency: str | None
    amount_raw: int | None
    amount_display: str | None
    amount_usd_display: str | None   # pre-computed USD at payment time; None for older records
    created_at: str


class PaymentTransactionsPage(BaseModel):
    transactions: list[PaymentTransactionOut]
    total: int
    limit: int
    offset: int


class RevenueTimeSeries(BaseModel):
    date: str        # ISO 8601 date string
    amount: str      # USD, e.g. "12.50"
    currency: str


class CountryBreakdown(BaseModel):
    country: str     # ISO 3166-1 alpha-2 or "Unknown"
    count: int
    amount: str      # USD


@router.get("/payments/summary", response_model=PaymentSummary)
async def get_payment_summary(
    db: AsyncSession = Depends(get_db_session),
):
    """Total, today, and this-month revenue from payment_events. Cached for 5 minutes."""
    redis = get_redis()
    cache_key = "routerv:analytics:payment_summary"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return PaymentSummary(**json.loads(cached))

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    usd_amount = _usd_amount_expr()

    total_result = await db.execute(
        select(func.coalesce(func.sum(usd_amount), 0).label("total"))
    )
    today_result = await db.execute(
        select(func.coalesce(func.sum(usd_amount), 0).label("total"))
        .where(PaymentEvent.created_at >= today_start)
    )
    month_result = await db.execute(
        select(func.coalesce(func.sum(usd_amount), 0).label("total"))
        .where(PaymentEvent.created_at >= month_start)
    )
    count_result = await db.execute(
        select(func.count(PaymentEvent.id).label("total"))
    )

    def _to_usd_str(raw: Decimal | float) -> str:
        return str(Decimal(str(raw)).quantize(Decimal("0.0001")))

    total_rev_raw = total_result.scalar_one()
    total_transactions = count_result.scalar_one() or 0
    avg_transaction_usd: str | None = None
    if total_transactions > 0:
        avg_transaction_usd = _to_usd_str(Decimal(str(total_rev_raw)) / total_transactions)

    summary = PaymentSummary(
        total_revenue=_to_usd_str(total_rev_raw),
        today_revenue=_to_usd_str(today_result.scalar_one()),
        month_revenue=_to_usd_str(month_result.scalar_one()),
        total_transactions=total_transactions,
        avg_transaction_usd=avg_transaction_usd,
    )

    if redis is not None:
        await set_analytics_cached(redis, cache_key, summary.model_dump_json())

    return summary


@router.get("/payments/revenue", response_model=list[RevenueTimeSeries])
async def get_payment_revenue(
    range: str = "30d",
    db: AsyncSession = Depends(get_db_session),
):
    """Daily revenue in USD (all currencies converted). Cached for 5 minutes."""
    redis = get_redis()
    cache_key = f"routerv:analytics:payment_revenue:{range}"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [RevenueTimeSeries(**r) for r in json.loads(cached)]

    now = datetime.now(timezone.utc)
    if range == "7d":
        since = now - timedelta(days=7)
    elif range == "90d":
        since = now - timedelta(days=90)
    else:
        since = now - timedelta(days=30)

    usd_amount = _usd_amount_expr()

    day_unit = text("'day'")
    rows = await db.execute(
        select(
            func.date_trunc(day_unit, PaymentEvent.created_at).label("date"),
            func.coalesce(func.sum(usd_amount), 0).label("amount"),
        )
        .where(PaymentEvent.created_at >= since)
        .group_by(func.date_trunc(day_unit, PaymentEvent.created_at))
        .order_by(func.date_trunc(day_unit, PaymentEvent.created_at))
    )

    result = [
        RevenueTimeSeries(
            date=r.date.isoformat(),
            amount=str(Decimal(str(r.amount)).quantize(Decimal("0.0001"))),
            currency="USD",
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


@router.get("/payments/countries", response_model=list[CountryBreakdown])
async def get_payment_countries(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Revenue grouped by the country column on payment_events.
    Rows without a country are bucketed as 'Unknown'. Cached for 5 minutes.
    """
    redis = get_redis()
    cache_key = "routerv:analytics:payment_countries"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [CountryBreakdown(**r) for r in json.loads(cached)]

    country_expr = func.coalesce(PaymentEvent.country, "Unknown")
    usd_amount = _usd_amount_expr()

    rows = await db.execute(
        select(
            country_expr.label("country"),
            func.count(PaymentEvent.id).label("count"),
            func.coalesce(func.sum(usd_amount), 0).label("amount"),
        )
        .group_by(country_expr)
        .order_by(func.sum(usd_amount).desc().nulls_last())
    )

    result = [
        CountryBreakdown(
            country=r.country,
            count=r.count,
            amount=str(Decimal(str(r.amount)).quantize(Decimal("0.0001"))),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


@router.get("/payments/top-users", response_model=list[OwnerUsageRow])
async def get_payment_top_users(
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    """Top users by total payment amount. Cached for 5 minutes."""
    redis = get_redis()
    cache_key = f"routerv:analytics:payment_top_users:{limit}"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [OwnerUsageRow(**r) for r in json.loads(cached)]

    usd_amount = _usd_amount_expr()

    rows = await db.execute(
        select(
            PaymentEvent.user_id.label("owner"),
            func.count(PaymentEvent.id).label("requests"),
            func.count(PaymentEvent.id).label("success"),  # all payments are successful
            func.coalesce(func.sum(usd_amount), 0).label("cost"),
        )
        .group_by(PaymentEvent.user_id)
        .order_by(func.sum(usd_amount).desc().nulls_last())
        .limit(limit)
    )

    result = [
        OwnerUsageRow(
            owner=r.owner,
            requests=r.requests,
            successful_requests=r.success,
            total_tokens=None,
            total_cost_usd=str(Decimal(str(r.cost)).quantize(Decimal("0.0001"))),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


class ProviderBreakdown(BaseModel):
    provider: str
    transaction_count: int
    total_amount_usd: str


class CurrencyBreakdown(BaseModel):
    currency: str
    transaction_count: int
    total_amount_usd: str


@router.get("/payments/by-provider", response_model=list[ProviderBreakdown])
async def get_payment_by_provider(
    db: AsyncSession = Depends(get_db_session),
):
    """Revenue grouped by payment provider/gateway. Cached for 5 minutes."""
    redis = get_redis()
    cache_key = "routerv:analytics:payment_by_provider"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [ProviderBreakdown(**r) for r in json.loads(cached)]

    usd_amount = _usd_amount_expr()
    rows = await db.execute(
        select(
            PaymentEvent.provider.label("provider"),
            func.count(PaymentEvent.id).label("count"),
            func.coalesce(func.sum(usd_amount), 0).label("total"),
        )
        .group_by(PaymentEvent.provider)
        .order_by(func.sum(usd_amount).desc().nulls_last())
    )

    def _to_usd_str(raw) -> str:
        return str(Decimal(str(raw)).quantize(Decimal("0.0001")))

    result = [
        ProviderBreakdown(
            provider=r.provider,
            transaction_count=r.count,
            total_amount_usd=_to_usd_str(r.total),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


@router.get("/payments/by-currency", response_model=list[CurrencyBreakdown])
async def get_payment_by_currency(
    db: AsyncSession = Depends(get_db_session),
):
    """Transaction count and USD total grouped by original currency. Cached for 5 minutes."""
    redis = get_redis()
    cache_key = "routerv:analytics:payment_by_currency"

    if redis is not None:
        cached = await get_analytics_cached(redis, cache_key)
        if cached is not None:
            return [CurrencyBreakdown(**r) for r in json.loads(cached)]

    usd_amount = _usd_amount_expr()
    currency_expr = func.coalesce(PaymentEvent.currency, "Unknown")
    rows = await db.execute(
        select(
            currency_expr.label("currency"),
            func.count(PaymentEvent.id).label("count"),
            func.coalesce(func.sum(usd_amount), 0).label("total"),
        )
        .group_by(currency_expr)
        .order_by(func.sum(usd_amount).desc().nulls_last())
    )

    def _to_usd_str(raw) -> str:
        return str(Decimal(str(raw)).quantize(Decimal("0.0001")))

    result = [
        CurrencyBreakdown(
            currency=r.currency,
            transaction_count=r.count,
            total_amount_usd=_to_usd_str(r.total),
        )
        for r in rows.all()
    ]

    if redis is not None:
        await set_analytics_cached(redis, cache_key, json.dumps([r.model_dump() for r in result]))

    return result


def _payment_to_out(e: PaymentEvent) -> PaymentTransactionOut:
    return PaymentTransactionOut(
        id=str(e.id),
        user_id=e.user_id,
        payment_id=e.payment_id,
        provider=e.provider,
        order_id=e.order_id,
        currency=e.currency,
        amount_raw=e.amount,
        amount_display=f"{e.amount / 100:.2f}" if e.amount is not None else None,
        amount_usd_display=f"{e.amount_usd / 100:.2f}" if e.amount_usd is not None else None,
        created_at=e.created_at.isoformat(),
    )


@router.get("/users/{user_id}/payments", response_model=PaymentTransactionsPage)
async def get_user_payments(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
):
    """Paginated payment transactions for a single user, newest first."""
    total_result = await db.execute(
        select(func.count(PaymentEvent.id)).where(PaymentEvent.user_id == user_id)
    )
    total = total_result.scalar_one() or 0

    rows = await db.execute(
        select(PaymentEvent)
        .where(PaymentEvent.user_id == user_id)
        .order_by(PaymentEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return PaymentTransactionsPage(
        transactions=[_payment_to_out(e) for e in rows.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/payments/transactions", response_model=PaymentTransactionsPage)
async def get_payment_transactions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
):
    """Paginated list of all payment transactions across all users, newest first."""
    total_result = await db.execute(select(func.count(PaymentEvent.id)))
    total = total_result.scalar_one() or 0

    rows = await db.execute(
        select(PaymentEvent)
        .order_by(PaymentEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return PaymentTransactionsPage(
        transactions=[_payment_to_out(e) for e in rows.scalars().all()],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/test-models", summary="Test models against a provider and register results")
async def test_models(body: TestModelsRequest) -> StreamingResponse:
    """
    Test each model in the list against the specified provider using server-side
    credentials, then register the results in the DB.

    Streams SSE events — one per model — as they complete, followed by a summary.

    **SSE event format (per model)**
    ```json
    {"model_id": "anthropic/claude-3-haiku", "status": "pass", "latency_ms": 342, "is_default": true, "error": null}
    ```

    **SSE summary event**
    ```json
    {"type": "summary", "total": 5, "passed": 4, "failed": 1}
    ```

    **DB behaviour**
    - `models` row: inserted with `is_enabled=false` if new; set to `is_enabled=true` on pass
    - `model_prices` row: inserted with `price=0, is_default=false` if new (model_id, provider) pair;
      `is_default` set to `true` on pass only if no other provider already holds the default
    - Existing rows are never overwritten (ON CONFLICT DO NOTHING)
    """
    return StreamingResponse(
        _test_models_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
