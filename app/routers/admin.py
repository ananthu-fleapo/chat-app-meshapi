"""
Admin router — dev-only key management + usage reporting.

Available in ENV=dev only. In prod the router is not registered at all,
so every /admin/* URL returns 404 from the framework (no route match).
No ADMIN_SECRET needed: the ENV guard is the protection.

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

from app.cache.key_cache import invalidate_cached_key
from app.config import settings
from app.db.models import ApiKey, ProviderKey, UsageEvent
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
      3. Store plaintext in GCP Secret Manager → get secret_ref.
      4. Write a ProviderKey row and return it.

    Returns the new ProviderKey on success, or None when provisioning is
    unavailable (dev environment / management key not configured).
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

    # Create key on OpenRouter.
    provisioned: ProvisionedKey | None = await create_or_key(
        owner,
        limit_usd=float(spend_cap_usd) if spend_cap_usd is not None else None,
    )
    if provisioned is None:
        # Provisioner disabled or failed — key will use system default.
        return None

    # Store plaintext in Secret Manager.
    secret_id = f"openrouter-{owner.lower().replace(' ', '-').replace('_', '-')}"
    version_ref = await store_secret(
        secret_id=secret_id,
        value=provisioned.plaintext,
        project_id=settings.gcp_project_id,
    )

    if version_ref is None:
        # Secret Manager unavailable (local dev) — store a placeholder so the
        # ProviderKey row exists but resolver falls back to system default.
        # In a real GCP environment this path means SM is misconfigured.
        logger.warning(
            "auto_provision_sm_unavailable",
            owner=owner,
            hint="Secret Manager not configured — using system default key",
        )
        # Use a sentinel value that the resolver recognises as "no secret".
        secret_ref = ""
    else:
        # Always point to /versions/latest so future rotations are automatic.
        secret_ref = f"projects/{settings.gcp_project_id}/secrets/{secret_id}/versions/latest"

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

    # Auto-provision an upstream provider key for this owner if needed.
    provider_key = await _auto_provision_for_owner(body.owner, spend_cap, db)

    raw_key = _generate_key()
    key = ApiKey(
        key_hash=_hash_key(raw_key),
        owner=body.owner,
        default_model=body.default_model,
        default_params=body.default_params,
        meta=body.meta,
        rpm_limit=body.rpm_limit,
        rpd_limit=body.rpd_limit,
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


def _to_pk_out(
    pk: ProviderKey, *, secret_reachable: bool | None = None
) -> AdminProviderKeyOut:
    return AdminProviderKeyOut(
        id=str(pk.id),
        owner=pk.owner,
        provider=pk.provider,
        secret_ref=pk.secret_ref,
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
