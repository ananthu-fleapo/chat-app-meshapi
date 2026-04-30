"""
User key management — POST/GET/DELETE /v1/keys

Control plane endpoint — requires a Supabase JWT (dashboard session).
All operations are scoped to the authenticated user's owner identity.

Create      POST   /v1/keys           Create a new inference key (plaintext returned once)
List        GET    /v1/keys           List all keys for the authenticated user
Deactivate  DELETE /v1/keys/{id}      Soft-delete: sets status to "suspended"
"""

import hashlib
import uuid

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.cache.key_cache import invalidate_cached_key
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.exceptions import NotFoundError
from app.routers.admin import _auto_provision_for_owner

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/keys", tags=["keys"])


# ── Pydantic I/O ──────────────────────────────────────────────────────────────

class CreateKeyRequest(BaseModel):
    label: str | None = None          # human name, stored in meta
    default_model: str | None = None
    rpm: int | None = None
    rpd: int | None = None
    tpm: int | None = None
    allowed_models: list[str] | None = None
    model_limits: dict | None = None


class CreateKeyResponse(BaseModel):
    id: str
    key: str          # plaintext — shown ONCE, never stored
    label: str | None
    status: str
    default_model: str | None
    created_at: str


class KeySummary(BaseModel):
    id: str
    label: str | None
    status: str
    default_model: str | None
    rpm_limit: int | None
    rpd_limit: int | None
    tpm_limit: int | None
    allowed_models: list[str] | None
    model_limits: dict | None
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_key() -> str:
    return f"rsk_{ULID()}"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _get_own_or_404(db: AsyncSession, key_id: str, owner: str) -> ApiKey:
    try:
        uid = uuid.UUID(key_id)
    except ValueError:
        raise NotFoundError(f"Key '{key_id}' not found.")

    result = await db.execute(
        select(ApiKey).where(ApiKey.id == uid, ApiKey.owner == owner)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise NotFoundError(f"Key '{key_id}' not found.")
    return key


def _to_summary(k: ApiKey) -> KeySummary:
    label = (k.meta or {}).get("label") if k.meta else None
    return KeySummary(
        id=str(k.id),
        label=label,
        status=k.status,
        default_model=k.default_model,
        rpm_limit=k.rpm_limit,
        rpd_limit=k.rpd_limit,
        tpm_limit=k.tpm_limit,
        allowed_models=k.allowed_models,
        model_limits=k.model_limits,
        created_at=k.created_at.isoformat(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=CreateKeyResponse, status_code=201)
async def create_key(
    body: CreateKeyRequest,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new RouterV inference key for the authenticated user.

    The plaintext key (rsk_...) is returned exactly once — store it securely.
    On the first key creation for this owner, a dedicated upstream provider
    key is auto-provisioned via the OpenRouter Management API (if configured).
    """
    # Auto-provision an upstream provider key for this owner if needed.
    provider_key = await _auto_provision_for_owner(identity.owner, None, db)

    raw_key = _generate_key()
    key = ApiKey(
        key_hash=_hash_key(raw_key),
        owner=identity.owner,
        default_model=body.default_model,
        meta={"label": body.label} if body.label else None,
        provider_key_id=provider_key.id if provider_key else None,
        rpm_limit=body.rpm,
        rpd_limit=body.rpd,
        tpm_limit=body.tpm,
        allowed_models=body.allowed_models or None,
        model_limits=body.model_limits or None,
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)

    logger.info(
        "user_key_created",
        key_id=str(key.id),
        owner=identity.owner,
        provisioned=provider_key is not None,
    )

    return CreateKeyResponse(
        id=str(key.id),
        key=raw_key,
        label=body.label,
        status=key.status,
        default_model=key.default_model,
        created_at=key.created_at.isoformat(),
    )


@router.get("", response_model=list[KeySummary])
async def list_keys(
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all inference keys belonging to the authenticated user."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.owner == identity.owner)
        .order_by(ApiKey.created_at.desc())
    )
    return [_to_summary(k) for k in result.scalars().all()]


@router.delete("/{key_id}", status_code=204)
async def deactivate_key(
    key_id: str,
    identity: ControlPlaneIdentity = Depends(get_control_plane_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Deactivate an inference key (soft delete — sets status to 'suspended').

    Suspended keys are immediately rejected at the inference layer.
    The key record is retained for audit purposes.
    Invalidates the Redis cache so the suspension takes effect instantly.
    """
    key = await _get_own_or_404(db, key_id, identity.owner)
    key.status = "suspended"
    await db.flush()

    await invalidate_cached_key(key.key_hash)

    logger.info("user_key_deactivated", key_id=str(key.id), owner=identity.owner)
