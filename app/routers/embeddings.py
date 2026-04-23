"""
Embeddings router — POST /v1/embeddings

Mirrors the chat request lifecycle where it still applies:
  auth, rate limits, spend cap, model/provider resolution, balance checks,
  upstream forwarding, and background usage logging.
"""

import time

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config_resolver import resolve_embeddings_config
from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_free_model_rate_limits, check_rate_limits
from app.config import settings
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.exceptions import ModelCapabilityError
from app.pricing.resolver import get_price_row
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.schemas.embeddings import EmbeddingsRequest
from app.usage.balance import check_balance
from app.usage.logger import fire_usage_log
from app.usage.spend_cap import check_spend_cap

router = APIRouter()
logger = structlog.get_logger()


@router.post(
    "/v1/embeddings",
    responses={
        400: {
            "description": "Model does not support embeddings API",
            "content": {"application/json": {"example": {
                "error": {"code": "model_capability_not_supported", "message": "Model 'gpt-4o' does not support the embeddings API."},
                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            }}},
        },
        401: {
            "description": "Missing or invalid API key",
            "content": {"application/json": {"example": {
                "error": {"code": "unauthorized", "message": "Invalid or missing API key."},
                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            }}},
        },
        402: {
            "description": "Insufficient balance or spend cap reached",
            "content": {"application/json": {"examples": {
                "spend_cap_reached": {
                    "summary": "Per-key spend cap reached",
                    "value": {
                        "error": {"code": "spend_limit_exceeded", "message": "Spend cap of $10.0000 reached. Current spend: $10.0023. Contact your administrator to increase the cap."},
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    },
                },
                "no_balance": {
                    "summary": "Insufficient credit balance",
                    "value": {
                        "error": {"code": "spend_limit_exceeded", "message": "Insufficient balance. Top up your account to use paid models."},
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    },
                },
            }}},
        },
        403: {
            "description": "API key is suspended",
            "content": {"application/json": {"example": {
                "error": {"code": "forbidden", "message": "API key is suspended."},
                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            }}},
        },
        422: {
            "description": "Request validation failed",
            "content": {"application/json": {"example": {
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": [{"type": "missing", "loc": ["body", "input"], "msg": "Field required"}],
                },
                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            }}},
        },
        429: {
            "description": "Rate limit exceeded (RPM or RPD)",
            "content": {"application/json": {"examples": {
                "rpm_exceeded": {
                    "summary": "Requests-per-minute limit hit",
                    "value": {
                        "error": {"code": "rate_limit_exceeded", "message": "RPM limit of 60 req/min exceeded."},
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    },
                },
                "rpd_exceeded": {
                    "summary": "Requests-per-day limit hit",
                    "value": {
                        "error": {"code": "rate_limit_exceeded", "message": "RPD limit of 1000 req/day exceeded."},
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    },
                },
            }}},
        },
        500: {
            "description": "Upstream provider error or gateway timeout",
            "content": {"application/json": {"examples": {
                "upstream_error": {
                    "summary": "Upstream provider returned an error",
                    "value": {
                        "error": {
                            "code": "upstream_error",
                            "message": "Upstream provider returned an error.",
                            "upstream_detail": "{\"error\":{\"message\":\"Input too large for model\",\"code\":413}}",
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    },
                },
                "gateway_timeout": {
                    "summary": "Upstream timed out",
                    "value": {
                        "error": {"code": "gateway_timeout", "message": "Upstream provider did not respond in time."},
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    },
                },
                "internal_error": {
                    "summary": "Internal platform error (DB failure — FastAPI default format)",
                    "value": {"detail": "Internal Server Error"},
                },
            }}},
        },
        503: {
            "description": "Upstream provider not available — required credentials not configured on this server",
            "content": {"application/json": {"example": {
                "error": {"code": "provider_not_available", "message": "Provider 'vertex' is not available. The required credentials may not be configured on this server."},
                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            }}},
        },
    },
)
async def create_embeddings(
    raw_body: EmbeddingsRequest,
    request: Request,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    request_id = getattr(request.state, "request_id", "")

    await check_rate_limits(
        key_id=str(key.id),
        rpm_limit=key.rpm_limit,
        rpd_limit=key.rpd_limit,
        default_rpm=settings.default_rpm,
        default_rpd=settings.default_rpd,
        max_rpm=settings.max_rpm,
        max_rpd=settings.max_rpd,
    )

    if key.spend_cap_usd is not None:
        await check_spend_cap(str(key.id), key.spend_cap_usd, db)

    body = resolve_embeddings_config(raw_body, key)

    is_free_model = await check_balance(key.owner, body.model, db)
    if is_free_model:
        await check_free_model_rate_limits(
            key_id=str(key.id),
            free_rpm=settings.default_free_rpm,
            free_rpd=settings.default_free_rpd,
        )

    provider, provider_model_id, _ = await resolve_routing(body.model, db)

    # ── Capability check: model+provider must support embeddings ─────────────
    _price_row = await get_price_row(body.model, provider, db)
    if _price_row is not None and not _price_row.supports_embeddings_api:
        raise ModelCapabilityError(body.model, "embeddings")

    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
    adapter = get_adapter(provider)

    log = logger.bind(
        model=body.model,
        request_id=request_id,
        key_owner=key.owner,
    )
    start = time.monotonic()
    response_body: dict | None = None
    status = "success"
    error_code_val: str | None = None
    provider_latency_ms = 0

    provider_start = time.monotonic()
    try:
        response_body = await adapter.embeddings(
            body,
            api_key=upstream_key,
            owner=key.owner,
            provider_model_id=provider_model_id,
        )
    except Exception as exc:
        status = "error"
        error_code_val = getattr(exc, "error_code", "upstream_error")
        logger.exception(
            "embeddings_failed",
            exc_type=type(exc).__name__,
            error=str(exc),
        )
        raise
    finally:
        provider_latency_ms = int((time.monotonic() - provider_start) * 1000)
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = (response_body or {}).get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        fire_usage_log(
            owner=key.owner,
            key_id=str(key.id),
            request_id=request_id,
            model=(response_body or {}).get("model", body.model),
            provider=provider,
            template_id=None,
            stream=False,
            prompt_tokens=prompt_tokens,
            completion_tokens=0 if prompt_tokens is not None else None,
            cached_tokens=None,
            upstream_cost=usage.get("cost"),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_val,
        )

    log.info(
        "embeddings_complete",
        latency_ms=latency_ms,
        model_used=response_body.get("model", body.model),
        prompt_tokens=usage.get("prompt_tokens"),
    )

    return JSONResponse(
        content=response_body,
        headers={"X-Provider-Latency-Ms": str(provider_latency_ms)},
    )
