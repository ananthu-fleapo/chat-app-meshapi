"""
FastAPI auth dependency: validates a RouterV API key on every request.

Phase 3 flow (cache-aside)
--------------------------
1. Extract Bearer token from Authorization header  →  401 if missing/malformed
2. SHA-256(token)  →  key_hash
3. Redis GET routerv:key:{key_hash}
     HIT  → deserialize to ApiKey, check status, return   (no DB)
     MISS → Postgres SELECT by key_hash
              found     → populate Redis cache, check status, return
              not found → 401
4. status != "active"  →  403

The DB session is only opened on a Redis miss — warm requests never
touch Postgres.

Phase 3 note on cache invalidation
------------------------------------
Admin PATCH / DELETE calls invalidate_cached_key() immediately so changes
propagate in < 1 request. The 60s TTL is a safety net only.
"""

import hashlib
import hmac

import structlog
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.key_cache import get_cached_key, set_cached_key
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.exceptions import ForbiddenError, UnauthorizedError

from app.config import settings

_bearer = HTTPBearer(auto_error=False)

logger = structlog.get_logger()


def _extract_bearer(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Authorization header must be: Bearer <key>")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedError("Bearer token is empty.")
    return token


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _check_active(key: ApiKey, raw_key: str) -> None:
    if key.status != "active":
        logger.warning("auth_suspended_key", key_id=str(key.id), owner=key.owner)
        from app.metrics import AUTH_FAILURES
        AUTH_FAILURES.labels(reason="suspended").inc()
        raise ForbiddenError("API key is suspended.")


async def get_authenticated_key(
    request: Request,
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> ApiKey:
    """
    Resolves and validates the caller's RouterV API key.
    Returns the ApiKey (may be a cache-reconstructed instance — read-only).
    """
    raw_key = _extract_bearer(authorization)
    key_hash = _hash_key(raw_key)

    # ── 1. Try Redis cache ────────────────────────────────────────────────────
    cached = await get_cached_key(key_hash)
    if cached is not None:
        logger.debug("auth_cache_hit", key_id=str(cached.id), owner=cached.owner)
        _check_active(cached, raw_key)
        request.state.owner = cached.owner
        # Mirror to raw scope so RequestLoggingMiddleware (raw ASGI, inside
        # BaseHTTPMiddleware) can read it — scope["state"] is not reliably
        # propagated across BaseHTTPMiddleware boundaries.
        request.scope["_owner"] = cached.owner
        return cached

    # ── 2. Cache miss → Postgres ──────────────────────────────────────────────
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    key = result.scalar_one_or_none()

    if key is None:
        logger.warning("auth_invalid_key", key_prefix=raw_key[:8] + "...")
        from app.metrics import AUTH_FAILURES
        AUTH_FAILURES.labels(reason="invalid_key").inc()
        raise UnauthorizedError()

    _check_active(key, raw_key)

    # ── 3. Populate cache for next request ────────────────────────────────────
    await set_cached_key(key)
    logger.debug("auth_cache_miss_populated", key_id=str(key.id), owner=key.owner)

    # ── 4. Expose owner to RequestLoggingMiddleware ───────────────────────────
    # Stored on request.state so the ASGI middleware can include it in the
    # MongoDB request_log document without re-parsing the auth header.
    request.state.owner = key.owner
    request.scope["_owner"] = key.owner

    return key


async def get_any_auth_owner(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Flexible auth dependency that accepts either auth plane.

    Tries Supabase JWT (control plane) first; if that fails, falls back to
    rsk_ API key lookup (data plane). Returns the resolved owner string.

    Use this on endpoints that should be callable from both the dashboard
    (JWT) and directly via an API key (e.g. /v1/templates, /v1/models).
    """
    if credentials is None:
        raise UnauthorizedError(
            "Authorization header required. "
            "Provide a Supabase session token or a RouterV API key."
        )

    from app.auth.control_plane import get_control_plane_user

    # ── Try JWT first (no DB needed) ──────────────────────────────────────────
    try:
        identity = await get_control_plane_user(credentials)
        return identity.owner
    except UnauthorizedError:
        pass

    # ── Fall back to data-plane key ───────────────────────────────────────────
    token = credentials.credentials
    key_hash = _hash_key(token)

    cached = await get_cached_key(key_hash)
    if cached is not None:
        _check_active(cached, token)
        return cached.owner

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    key = result.scalar_one_or_none()
    if key is None:
        raise UnauthorizedError()

    _check_active(key, token)
    await set_cached_key(key)
    return key.owner


async def verify_webhook_key(
    authorization: str = Header(..., alias="Authorization"),
) -> None:
    """
    Validates inbound webhook requests against the static WEBHOOK_API_KEY setting.

    Expects: Authorization: Bearer <WEBHOOK_API_KEY>

    Returns nothing on success.
    Raises UnauthorizedError (401) if the header is missing, malformed, or wrong.
    Raises ForbiddenError   (403) if WEBHOOK_API_KEY is not configured on the server.
    """
    if not settings.webhook_api_key:
        logger.error("webhook_auth_not_configured")
        raise ForbiddenError("Webhook auth is not configured.")

    token = _extract_bearer(authorization)

    if not hmac.compare_digest(token, settings.webhook_api_key):
        logger.warning("webhook_auth_invalid_key")
        raise UnauthorizedError("Invalid webhook API key.")

    logger.debug("webhook_auth_ok")
