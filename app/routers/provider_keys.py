"""
Provider key management — POST/GET/PATCH/DELETE /v1/provider-keys

Auth-gated, owner-scoped: a caller can only see and manage provider keys
for their own owner label (derived from their RouterV bearer key).

Each record stores a GCP Secret Manager reference (secret_ref) that points
to the actual upstream API key.  The key value is never stored in this DB —
only the path to it.

Endpoints
---------
POST   /v1/provider-keys               Register a new provider key
GET    /v1/provider-keys               List caller's active provider keys
GET    /v1/provider-keys/{id}          Get a single provider key
PATCH  /v1/provider-keys/{id}          Update label / secret_ref / is_active
DELETE /v1/provider-keys/{id}          Hard delete (also invalidates SM cache)
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_authenticated_key
from app.db.models import ApiKey, ProviderKey
from app.db.session import get_db_session
from app.exceptions import NotFoundError
from app.providers.secret_manager import fetch_secret, invalidate_secret_cache

router = APIRouter(prefix="/v1/provider-keys", tags=["provider-keys"])
logger = structlog.get_logger()


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class CreateProviderKeyRequest(BaseModel):
    provider: str = "openrouter"
    secret_ref: str
    """
    GCP Secret Manager resource name, e.g.:
      projects/myproject/secrets/openrouter-acme-prod/versions/latest

    In local dev without GCP this can be any string — the resolver will
    fall back to settings.openrouter_api_key if Secret Manager is
    unavailable.
    """
    label: str | None = None


class UpdateProviderKeyRequest(BaseModel):
    label: str | None = None
    secret_ref: str | None = None
    is_active: bool | None = None


class ProviderKeyOut(BaseModel):
    id: str
    owner: str
    provider: str
    # secret_ref is intentionally returned so callers can verify the path.
    # The actual secret value is never exposed via this API.
    secret_ref: str
    label: str | None
    is_active: bool
    created_at: str
    # Transient: whether the Secret Manager reference is currently reachable.
    # Populated on single-get; None on list (would be too slow).
    secret_reachable: bool | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid UUID: {value!r}")


def _to_out(pk: ProviderKey, *, secret_reachable: bool | None = None) -> ProviderKeyOut:
    return ProviderKeyOut(
        id=str(pk.id),
        owner=pk.owner,
        provider=pk.provider,
        secret_ref=pk.secret_ref,
        label=pk.label,
        is_active=pk.is_active,
        created_at=pk.created_at.isoformat(),
        secret_reachable=secret_reachable,
    )


async def _get_own_or_404(
    db: AsyncSession, pk_id: uuid.UUID, owner: str
) -> ProviderKey:
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.id == pk_id,
            ProviderKey.owner == owner,
        )
    )
    pk = result.scalar_one_or_none()
    if pk is None:
        raise NotFoundError("Provider key not found.")
    return pk


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=ProviderKeyOut, status_code=201)
async def create_provider_key(
    body: CreateProviderKeyRequest,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a GCP Secret Manager reference as a provider key for your owner.

    After creation, new inference requests by keys with the same owner will
    use this secret to authenticate upstream.  Existing Secret Manager cache
    entries for the same secret_ref are NOT pre-populated here — the first
    request will populate them.
    """
    if not body.provider:
        raise HTTPException(status_code=422, detail="provider must not be empty")
    if not body.secret_ref:
        raise HTTPException(status_code=422, detail="secret_ref must not be empty")

    pk = ProviderKey(
        owner=key.owner,
        provider=body.provider,
        secret_ref=body.secret_ref,
        label=body.label,
    )
    db.add(pk)
    await db.flush()
    await db.refresh(pk)

    logger.info(
        "provider_key_created",
        pk_id=str(pk.id),
        owner=pk.owner,
        provider=pk.provider,
    )
    return _to_out(pk)


@router.get("", response_model=list[ProviderKeyOut])
async def list_provider_keys(
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """List all provider keys belonging to your owner (active and inactive)."""
    result = await db.execute(
        select(ProviderKey)
        .where(ProviderKey.owner == key.owner)
        .order_by(ProviderKey.created_at.desc())
    )
    return [_to_out(pk) for pk in result.scalars().all()]


@router.get("/{pk_id}", response_model=ProviderKeyOut)
async def get_provider_key(
    pk_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a single provider key.

    Also probes Secret Manager to report whether the secret is currently
    reachable (``secret_reachable`` field).  Useful for verifying a newly
    created key before relying on it.
    """
    uid = _parse_uuid(pk_id)
    pk = await _get_own_or_404(db, uid, key.owner)

    # Probe Secret Manager (result already cached if previously fetched)
    secret = await fetch_secret(pk.secret_ref)
    reachable = secret is not None

    return _to_out(pk, secret_reachable=reachable)


@router.patch("/{pk_id}", response_model=ProviderKeyOut)
async def update_provider_key(
    pk_id: str,
    body: UpdateProviderKeyRequest,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update label, secret_ref, or is_active flag.

    Rotating a key: set ``secret_ref`` to the new Secret Manager path
    (or update the secret version in SM itself and keep the same path).
    The old cached value is evicted automatically on the next TTL expiry,
    or immediately when the ``secret_ref`` changes.
    """
    uid = _parse_uuid(pk_id)
    pk = await _get_own_or_404(db, uid, key.owner)

    old_secret_ref = pk.secret_ref

    if body.label is not None:
        pk.label = body.label
    if body.secret_ref is not None:
        pk.secret_ref = body.secret_ref
    if body.is_active is not None:
        pk.is_active = body.is_active

    await db.flush()
    await db.refresh(pk)

    # Evict cached secret when the reference changes (key rotation).
    if body.secret_ref is not None and body.secret_ref != old_secret_ref:
        await invalidate_secret_cache(old_secret_ref)

    logger.info("provider_key_updated", pk_id=str(pk.id), owner=pk.owner)
    return _to_out(pk)


@router.delete("/{pk_id}", status_code=204)
async def delete_provider_key(
    pk_id: str,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Hard-delete a provider key record and invalidate its Secret Manager cache.

    After deletion, inference requests by this owner will fall back to the
    system default key unless another active ProviderKey exists.
    """
    uid = _parse_uuid(pk_id)
    pk = await _get_own_or_404(db, uid, key.owner)

    # Evict cache before deletion so stale entries don't linger.
    await invalidate_secret_cache(pk.secret_ref)
    await db.delete(pk)

    logger.info("provider_key_deleted", pk_id=str(pk.id), owner=pk.owner)
