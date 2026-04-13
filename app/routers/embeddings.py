"""
Embeddings router — POST /v1/embeddings

Mirrors the chat request lifecycle where it still applies:
  auth, rate limits, spend cap, model/provider resolution, balance checks,
  upstream forwarding, and background usage logging.
"""

import time

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config_resolver import resolve_embeddings_config
from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_free_model_rate_limits, check_rate_limits
from app.config import settings
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.schemas.embeddings import EmbeddingsRequest
from app.usage.balance import check_balance
from app.usage.logger import fire_usage_log
from app.usage.spend_cap import check_spend_cap

router = APIRouter()
logger = structlog.get_logger()


@router.post("/v1/embeddings")
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

    return response_body
