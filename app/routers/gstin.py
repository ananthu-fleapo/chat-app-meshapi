"""
GSTIN verification router — GET /v1/gstin/{gstin}

Proxies GSTIN lookup to the external verification API and returns a
structured subset of the response. Results are cached in Redis for 6 months
(GSTINs are stable; status changes are rare enough that a long TTL is fine).

Auth
----
Requires: Authorization: Bearer <Supabase JWT>
Same control-plane JWT guard used by templates, balance, and usage endpoints.
"""

import json

import httpx
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.control_plane import ControlPlaneIdentity, get_control_plane_user
from app.cache.redis_client import get_redis
from app.config import settings
from app.exceptions import RouterVError

router = APIRouter(prefix="/v1/gstin", tags=["gstin"])
logger = structlog.get_logger()

_SIX_MONTHS_TTL = 60 * 60 * 24 * 30 * 6  # seconds


class GstinResponse(BaseModel):
    valid: bool
    gstin: str
    legal_name: str
    trade_name: str
    status: str
    business_type: str
    taxpayer_type: str
    registration_date: str
    cancellation_date: str | None
    address: str


@router.get("/{gstin}", response_model=GstinResponse)
async def verify_gstin(
    gstin: str,
    _identity: ControlPlaneIdentity = Depends(get_control_plane_user),
) -> GstinResponse:
    """
    Verify a GSTIN via Cashfree's Verification Suite.

    POSTs to <cashfree_verify_api_url>/gstin with x-client-id / x-client-secret
    headers and maps the flat Cashfree response into the same GstinResponse
    shape returned by v1. Cached 6 months in Redis under the `gstin:v2:` prefix
    so v1 and v2 entries do not collide.
    """
    gstin = gstin.upper().strip()
    cache_key = f"gstin:{gstin}"

    # ── Cache hit ─────────────────────────────────────────────────────────────
    redis = get_redis()
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached is not None:
                logger.info("gstin_v2_cache_hit", gstin=gstin)
                return GstinResponse(**json.loads(cached))
        except Exception as exc:  # noqa: BLE001
            logger.warning("gstin_v2_cache_read_error", error=str(exc))

    # ── Cashfree call ─────────────────────────────────────────────────────────
    if not (
        settings.cashfree_verify_api_url
        and settings.cashfree_client_id
        and settings.cashfree_client_secret
    ):
        raise RouterVError(
            status_code=503,
            error_code="gstin_not_configured",
            message="Cashfree GSTIN verification is not configured.",
        )

    headers = {
        "x-client-id": settings.cashfree_client_id,
        "x-client-secret": settings.cashfree_client_secret,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{settings.cashfree_verify_api_url}/verification/gstin",
                headers=headers,
                json={"GSTIN": gstin},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("gstin_v2_fetch_failed", gstin=gstin, error=str(exc))
            raise RouterVError(
                status_code=502,
                error_code="gstin_fetch_error",
                message=f"Cashfree GSTIN verification request failed: {exc}",
            ) from exc

    payload = resp.json()

    result = GstinResponse(
        valid=payload.get("valid") is True,
        gstin=payload.get("GSTIN", gstin),
        legal_name=payload.get("legal_name_of_business", ""),
        trade_name=payload.get("trade_name_of_business", ""),
        status=payload.get("gstin_status", ""),
        business_type=payload.get("constitution_of_business", ""),
        taxpayer_type=payload.get("taxpayer_type", ""),
        registration_date=payload.get("date_of_registration", ""),
        cancellation_date=payload.get("date_of_cancellation") or None,
        address=payload.get("principal_place_address", ""),
    )

    logger.info("gstin_v2_verified", gstin=gstin, valid=result.valid, status=result.status)

    # ── Populate cache ────────────────────────────────────────────────────────
    if redis is not None:
        try:
            await redis.setex(cache_key, _SIX_MONTHS_TTL, result.model_dump_json())
        except Exception as exc:  # noqa: BLE001
            logger.warning("gstin_v2_cache_write_error", error=str(exc))

    return result
