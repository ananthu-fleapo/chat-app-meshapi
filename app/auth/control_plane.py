"""
Control plane authentication — Supabase JWT verification.

Separation of concerns
----------------------
Data plane  (inference)  →  rsk_<ULID> keys via get_authenticated_key
Control plane (dashboard) →  Supabase JWTs via get_control_plane_user

AuthN is entirely Supabase's responsibility. RouterV only:
  1. Verifies the JWT signature using the shared HS256 secret.
  2. Checks standard claims (exp, aud, iss).
  3. Extracts the caller's owner label for DB scoping.

No network call is made — everything happens locally from the JWT payload.
Overhead is ~0 ms (HMAC-SHA256 verify on a small payload).

Owner resolution
----------------
RouterV scopes all control plane resources (templates, usage) by `owner`.
The owner label comes from the JWT claims in priority order:

  1. user_metadata.<supabase_owner_claim>  — e.g. user_metadata.routerv_owner
  2. app_metadata.<supabase_owner_claim>   — set via Supabase service role
  3. <supabase_owner_claim> (top-level)
  4. sub (Supabase user UUID) — always present, used as final fallback

This means a Supabase user whose user_metadata contains:
  { "routerv_owner": "acme-corp" }
will have owner="acme-corp" — matching the owner field on their rsk_ key.

If no custom claim is set (SUPABASE_OWNER_CLAIM=""), `sub` becomes the
owner. In that case, rsk_ keys must be created with owner=<supabase-sub>.

Dev bypass
----------
When SUPABASE_JWT_SECRET is empty:
  - Signature verification is skipped.
  - The raw bearer token string is used as the owner label.
  - This lets local dev work without a Supabase project.
  - Never active when SUPABASE_JWT_SECRET is set (env always wins in prod).
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.exceptions import UnauthorizedError

logger = structlog.get_logger()

# HTTPBearer with auto_error=False so we can return a clean RouterV 401
# instead of FastAPI's default 403 on missing credentials.
_bearer = HTTPBearer(auto_error=False)


@dataclass
class ControlPlaneIdentity:
    """
    Verified caller identity extracted from a Supabase JWT.

    Attributes
    ----------
    sub:    Supabase user UUID (always present after verification).
    owner:  RouterV owner label used for DB scoping. Derived from a
            custom claim when configured, otherwise equals sub.
    email:  User email from JWT, if present. Used for logging only —
            never stored or used for authZ decisions.
    """

    sub: str
    owner: str
    email: str | None = None


def _resolve_owner(claims: dict) -> str:
    """
    Extract the RouterV owner label from JWT claims.

    Checks custom claim in user_metadata → app_metadata → top-level,
    then falls back to sub.
    """
    claim = settings.supabase_owner_claim
    if claim:
        user_meta: dict = claims.get("user_metadata") or {}
        app_meta: dict = claims.get("app_metadata") or {}
        owner = (
            user_meta.get(claim)
            or app_meta.get(claim)
            or claims.get(claim)
        )
        if owner:
            return str(owner)

    # Always-present fallback — Supabase user UUID.
    return claims["sub"]


def _verify_jwt(token: str) -> dict:
    """
    Verify the JWT signature and standard claims.

    Returns the decoded payload dict.
    Raises UnauthorizedError on any verification failure.
    """
    decode_kwargs: dict = {
        "algorithms": ["HS256"],
        # Supabase sets aud="authenticated" on all user JWTs.
        "audience": "authenticated",
    }

    # Validate issuer only when supabase_url is configured.
    if settings.supabase_url:
        decode_kwargs["issuer"] = f"{settings.supabase_url.rstrip('/')}/auth/v1"

    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            **decode_kwargs,
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired.")
    except jwt.InvalidAudienceError:
        raise UnauthorizedError("Token audience invalid.")
    except jwt.InvalidIssuerError:
        raise UnauthorizedError("Token issuer invalid.")
    except jwt.DecodeError as exc:
        raise UnauthorizedError(f"Token decode failed: {exc}")
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(f"Invalid token: {exc}")


async def get_control_plane_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> ControlPlaneIdentity:
    """
    FastAPI dependency for control plane endpoints.

    Usage:
        @router.get("/v1/templates")
        async def list_templates(
            identity: ControlPlaneIdentity = Depends(get_control_plane_user),
        ): ...

    Raises UnauthorizedError (→ 401) when:
      - Authorization header is missing
      - Token signature is invalid
      - Token is expired
      - Audience / issuer mismatch (when supabase_url is configured)
    """
    if credentials is None:
        raise UnauthorizedError(
            "Authorization header required. "
            "Provide a valid Supabase session token: Authorization: Bearer <token>"
        )

    token = credentials.credentials

    # ── Dev bypass ────────────────────────────────────────────────────────────
    # When SUPABASE_JWT_SECRET is not set we are in local dev without a
    # Supabase project.  Accept any token and use its value as the owner
    # so developers can test with a simple: Authorization: Bearer acme-corp
    if not settings.supabase_jwt_secret:
        logger.debug(
            "control_plane_auth_bypass",
            hint="SUPABASE_JWT_SECRET not set — JWT verification skipped",
        )
        try:
            claims = jwt.decode(token, options={"verify_signature": True})
            sub = claims.get("sub", token)
            owner = _resolve_owner(claims) if claims.get("sub") else token
            email = claims.get("email")
        except jwt.DecodeError:
            sub = token
            owner = token
            email = None
        return ControlPlaneIdentity(sub=sub, owner=owner, email=email)

    # ── Production: verify JWT ────────────────────────────────────────────────
    claims = _verify_jwt(token)
    identity = ControlPlaneIdentity(
        sub=claims["sub"],
        owner=_resolve_owner(claims),
        email=claims.get("email"),
    )

    logger.debug(
        "control_plane_authed",
        sub=identity.sub[:8] + "...",
        owner=identity.owner,
    )
    return identity
