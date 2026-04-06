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
    Verify a GSTIN and return key business details from the GST portal.

    Results are cached for 6 months — GSTINs are stable identifiers and the
    underlying data (legal name, address, registration date) rarely changes.
    """
    gstin = gstin.upper().strip()
    cache_key = f"gstin:{gstin}"

    # ── Cache hit ─────────────────────────────────────────────────────────────
    redis = get_redis()
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached is not None:
                logger.info("gstin_cache_hit", gstin=gstin)
                return GstinResponse(**json.loads(cached))
        except Exception as exc:  # noqa: BLE001
            logger.warning("gstin_cache_read_error", error=str(exc))

    # ── External API call ─────────────────────────────────────────────────────
    if not settings.gstin_verify_api_url:
        raise RouterVError(
            status_code=503,
            error_code="gstin_not_configured",
            message="GSTIN verification is not configured.",
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{settings.gstin_verify_api_url}/{gstin}")
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("gstin_fetch_failed", gstin=gstin, error=str(exc))
            raise RouterVError(
                status_code=502,
                error_code="gstin_fetch_error",
                message=f"GSTIN verification API request failed: {exc}",
            ) from exc

    payload = resp.json()
    data = payload.get("data") or {}

    result = GstinResponse(
        valid=payload.get("flag") is True,
        gstin=data.get("gstin", gstin),
        legal_name=data.get("lgnm", ""),
        trade_name=data.get("tradeNam", ""),
        status=data.get("sts", ""),
        business_type=data.get("ctb", ""),
        taxpayer_type=data.get("dty", ""),
        registration_date=data.get("rgdt", ""),
        cancellation_date=data.get("cxdt") or None,
        address=(data.get("pradr") or {}).get("adr", ""),
    )

    logger.info("gstin_verified", gstin=gstin, valid=result.valid, status=result.status)

    # ── Populate cache ────────────────────────────────────────────────────────
    if redis is not None:
        try:
            await redis.setex(cache_key, _SIX_MONTHS_TTL, result.model_dump_json())
        except Exception as exc:  # noqa: BLE001
            logger.warning("gstin_cache_write_error", error=str(exc))

    return result
