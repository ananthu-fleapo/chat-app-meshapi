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

import hashlib
import uuid
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.auth.control_plane import get_admin_user
from app.cache.key_cache import invalidate_cached_key
from app.config import settings
from app.db.models import ApiKey, Discount, ModelPrice, ProviderKey, UsageEvent, UserBalance
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
    key_count: int
    active_key_count: int
    total_spent_usd: str
    balance_usd: str | None
    last_activity: str | None
    created_at: str


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all users derived from api_keys.owner, enriched with balance and spend.
    """
    # Aggregate per-owner stats from api_keys
    keys_q = await db.execute(
        select(
            ApiKey.owner.label("owner"),
            func.count(ApiKey.id).label("key_count"),
            func.count(ApiKey.id).filter(ApiKey.status == "active").label("active_key_count"),
            func.min(ApiKey.created_at).label("created_at"),
        ).group_by(ApiKey.owner)
    )
    key_rows = keys_q.all()

    # Spend per owner via api_keys join usage_events
    spend_q = await db.execute(
        select(
            ApiKey.owner.label("owner"),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("total_spent"),
            func.max(UsageEvent.created_at).label("last_activity"),
        )
        .outerjoin(UsageEvent, UsageEvent.key_id == ApiKey.id)
        .group_by(ApiKey.owner)
    )
    spend_by_owner = {r.owner: r for r in spend_q.all()}

    # Balance per user_id (owner == user_id for Supabase users)
    bal_q = await db.execute(select(UserBalance))
    bal_by_user = {str(b.user_id): b for b in bal_q.scalars().all()}

    results = []
    for r in key_rows:
        spend_row = spend_by_owner.get(r.owner)
        bal = bal_by_user.get(r.owner)
        results.append(UserSummary(
            user_id=r.owner,
            key_count=r.key_count,
            active_key_count=r.active_key_count,
            total_spent_usd=str(Decimal(str(spend_row.total_spent))) if spend_row else "0",
            balance_usd=str(bal.balance_usd) if bal else None,
            last_activity=spend_row.last_activity.isoformat() if spend_row and spend_row.last_activity else None,
            created_at=r.created_at.isoformat(),
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
    return [
        OwnerUsageRow(
            owner=r.owner,
            requests=r.requests,
            successful_requests=r.success,
            total_tokens=r.tokens if r.tokens else None,
            total_cost_usd=str(Decimal(str(r.cost))),
        )
        for r in rows.all()
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
    pk: ProviderKey, *, secret_reachable: bool | None = None
) -> AdminProviderKeyOut:
    return AdminProviderKeyOut(
        id=str(pk.id),
        owner=pk.owner,
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
    return [_to_pk_out(pk) for pk in result.scalars().all()]


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

class ModelPriceIn(BaseModel):
    model_id: str
    provider: str = "openrouter"
    is_default: bool = False
    prompt_usd_per_1k: float
    completion_usd_per_1k: float
    is_free: bool = False


class ModelPriceUpdateIn(BaseModel):
    prompt_usd_per_1k: float | None = None
    completion_usd_per_1k: float | None = None
    is_free: bool | None = None
    is_default: bool | None = None


class ModelPriceOut(BaseModel):
    model_id: str
    provider: str
    is_default: bool
    prompt_usd_per_1k: str
    completion_usd_per_1k: str
    is_free: bool
    updated_at: str


def _to_price_out(p: ModelPrice) -> ModelPriceOut:
    return ModelPriceOut(
        model_id=p.model_id,
        provider=p.provider,
        is_default=p.is_default,
        prompt_usd_per_1k=str(p.prompt_usd_per_1k),
        completion_usd_per_1k=str(p.completion_usd_per_1k),
        is_free=p.is_free,
        updated_at=p.updated_at.isoformat(),
    )


async def _clear_default(model_id: str, db: AsyncSession) -> None:
    """Clear is_default on all rows for model_id (called before setting a new default)."""
    result = await db.execute(
        select(ModelPrice).where(
            ModelPrice.model_id == model_id,
            ModelPrice.is_default.is_(True),
        )
    )
    for row in result.scalars().all():
        row.is_default = False


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
    from decimal import Decimal

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

    if price is None:
        price = ModelPrice(
            model_id=body.model_id,
            provider=body.provider,
            is_default=body.is_default,
            prompt_usd_per_1k=Decimal(str(body.prompt_usd_per_1k)),
            completion_usd_per_1k=Decimal(str(body.completion_usd_per_1k)),
            is_free=body.is_free,
        )
        db.add(price)
    else:
        price.is_default = body.is_default
        price.prompt_usd_per_1k = Decimal(str(body.prompt_usd_per_1k))
        price.completion_usd_per_1k = Decimal(str(body.completion_usd_per_1k))
        price.is_free = body.is_free

    await db.flush()
    await db.refresh(price)
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


@router.patch("/model-prices/{model_id}/{provider}", response_model=ModelPriceOut)
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
    from decimal import Decimal

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

    if body.prompt_usd_per_1k is not None:
        price.prompt_usd_per_1k = Decimal(str(body.prompt_usd_per_1k))
    if body.completion_usd_per_1k is not None:
        price.completion_usd_per_1k = Decimal(str(body.completion_usd_per_1k))
    if body.is_free is not None:
        price.is_free = body.is_free
    if body.is_default is not None:
        price.is_default = body.is_default

    await db.flush()
    await db.refresh(price)
    logger.info("model_price_updated", model_id=model_id, provider=provider)
    return _to_price_out(price)


@router.delete("/model-prices/{model_id}/{provider}", status_code=204)
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

        # Convert per-token → per 1k tokens
        prompt_per_1k = Decimal(str(round(prompt_per_token * 1000, 8)))
        completion_per_1k = Decimal(str(round(completion_per_token * 1000, 8)))
        is_free = prompt_per_token == 0 and completion_per_token == 0

        stmt = pg_insert(ModelPrice).values(
            model_id=model_id,
            provider="openrouter",
            is_default=True,
            prompt_usd_per_1k=prompt_per_1k,
            completion_usd_per_1k=completion_per_1k,
            is_free=is_free,
        )
        if overwrite:
            stmt = stmt.on_conflict_do_update(
                index_elements=["model_id", "provider"],
                set_={
                    "prompt_usd_per_1k": stmt.excluded.prompt_usd_per_1k,
                    "completion_usd_per_1k": stmt.excluded.completion_usd_per_1k,
                    "is_free": stmt.excluded.is_free,
                    "updated_at": func.now(),
                },
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=["model_id", "provider"])

        await db.execute(stmt)
        seeded_ids.append(model_id)

    await db.commit()
    logger.info("model_prices_seeded", count=len(seeded_ids), skipped=skipped, overwrite=overwrite)
    return SeedPricesResponse(seeded=len(seeded_ids), skipped=skipped, models=seeded_ids)


# ── Discounts ─────────────────────────────────────────────────────────────────

class DiscountIn(BaseModel):
    user_id: str
    model_id: str | None = None          # None = account-level
    discount_pct: float                  # 0–100
    valid_from: str | None = None        # ISO8601; defaults to now
    valid_until: str | None = None       # ISO8601; None = no expiry
    label: str | None = None


class DiscountUpdateIn(BaseModel):
    discount_pct: float | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    is_active: bool | None = None
    label: str | None = None


class DiscountOut(BaseModel):
    id: str
    user_id: str
    model_id: str | None
    discount_pct: str
    valid_from: str
    valid_until: str | None
    is_active: bool
    label: str | None
    created_at: str


def _to_discount_out(d: Discount) -> DiscountOut:
    return DiscountOut(
        id=str(d.id),
        user_id=d.user_id,
        model_id=d.model_id,
        discount_pct=str(d.discount_pct),
        valid_from=d.valid_from.isoformat(),
        valid_until=d.valid_until.isoformat() if d.valid_until else None,
        is_active=d.is_active,
        label=d.label,
        created_at=d.created_at.isoformat(),
    )


@router.post("/discounts", response_model=DiscountOut, status_code=201)
async def create_discount(
    body: DiscountIn,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a discount for a user. model_id=null = account-level (all models)."""
    from datetime import UTC, datetime
    from decimal import Decimal as D

    if not (0 <= body.discount_pct <= 100):
        raise HTTPException(status_code=422, detail="discount_pct must be between 0 and 100")

    valid_from = datetime.fromisoformat(body.valid_from) if body.valid_from else datetime.now(UTC)
    valid_until = datetime.fromisoformat(body.valid_until) if body.valid_until else None

    d = Discount(
        user_id=body.user_id,
        model_id=body.model_id,
        discount_pct=D(str(body.discount_pct)),
        valid_from=valid_from,
        valid_until=valid_until,
        label=body.label,
    )
    db.add(d)
    await db.flush()
    await db.refresh(d)
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
    return [_to_discount_out(d) for d in result.scalars().all()]


@router.patch("/discounts/{discount_id}", response_model=DiscountOut)
async def update_discount(
    discount_id: str,
    body: DiscountUpdateIn,
    db: AsyncSession = Depends(get_db_session),
):
    """Update discount percentage, dates, active state, or label."""
    import uuid as _uuid
    from decimal import Decimal as D

    result = await db.execute(select(Discount).where(Discount.id == _uuid.UUID(discount_id)))
    d = result.scalar_one_or_none()
    if d is None:
        raise NotFoundError(f"Discount '{discount_id}' not found.")

    if body.discount_pct is not None:
        if not (0 <= body.discount_pct <= 100):
            raise HTTPException(status_code=422, detail="discount_pct must be between 0 and 100")
        d.discount_pct = D(str(body.discount_pct))
    if body.valid_from is not None:
        from datetime import datetime
        d.valid_from = datetime.fromisoformat(body.valid_from)
    if body.valid_until is not None:
        from datetime import datetime
        d.valid_until = datetime.fromisoformat(body.valid_until)
    if body.is_active is not None:
        d.is_active = body.is_active
    if body.label is not None:
        d.label = body.label

    await db.flush()
    await db.refresh(d)
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
            ub.balance_usd,
            ub.updated_at,
            COALESCE(SUM(ue.cost_usd), 0)  AS total_spent_usd,
            MAX(ue.created_at)              AS last_activity
        FROM user_balances ub
        LEFT JOIN api_keys ak ON ak.owner = ub.user_id
        LEFT JOIN usage_events ue ON ue.key_id = ak.id AND ue.status = 'success'
        GROUP BY ub.user_id, ub.balance_usd, ub.updated_at
        ORDER BY ub.balance_usd ASC
    """))

    return [
        BalanceSummary(
            user_id=r.user_id,
            balance_usd=str(r.balance_usd),
            total_spent_usd=str(r.total_spent_usd),
            last_activity=r.last_activity.isoformat() if r.last_activity else None,
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
