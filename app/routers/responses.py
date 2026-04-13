"""
Responses router — POST /v1/responses

Proxies to the Responses API of the upstream provider resolved from the DB
(model_prices.provider), identical to how chat/completions routes.  Designed
for reasoning models (e.g. openai/o4-mini) with first-class reasoning, web
search, and structured output support.

The full operational pipeline (auth, rate limiting, spend cap, balance check,
usage logging) is identical to chat/completions. Key differences:
- Request schema uses `input` instead of `messages`, `max_output_tokens`
  instead of `max_tokens`, and adds `reasoning` / `plugins` fields.
- No template support in V1 (templates inject into `messages`; deferred).
- No stream_options injection (Responses API sends usage natively).
"""

import json
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config_resolver import resolve_responses_config
from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_free_model_rate_limits, check_rate_limits
from app.config import settings
from app.db.models import ApiKey, ModelPrice
from app.db.session import get_db_session
from app.exceptions import ModelCapabilityError
from app.providers.base import ProviderAdapter
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.schemas.responses import ResponsesRequest
from app.usage.balance import check_balance
from app.usage.logger import fire_usage_log
from app.usage.spend_cap import check_spend_cap

router = APIRouter()
logger = structlog.get_logger()


def _normalize_usage(raw: dict) -> dict:
    """
    Normalize provider-specific usage field names to RouterV canonical names.

    OpenAI Responses API uses input_tokens / output_tokens / input_tokens_details;
    OpenRouter uses the canonical prompt_tokens / completion_tokens / prompt_tokens_details.
    """
    u = dict(raw)
    if "input_tokens" in u and "prompt_tokens" not in u:
        u["prompt_tokens"] = u.pop("input_tokens")
    if "output_tokens" in u and "completion_tokens" not in u:
        u["completion_tokens"] = u.pop("output_tokens")
    if "input_tokens_details" in u and "prompt_tokens_details" not in u:
        u["prompt_tokens_details"] = u.pop("input_tokens_details")
    return u


@router.post("/v1/responses")
async def create_response(
    raw_body: ResponsesRequest,
    request: Request,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Responses API endpoint — provider resolved dynamically from DB.

    Auth:        Authorization: Bearer rsk_<ULID>
    Streaming:   set stream=true for SSE chunks
    Rate limits: RPM and RPD enforced per key via Redis fixed-window counters
    Spend cap:   enforced if key.spend_cap_usd is set
    Provider:    resolved from model_prices.provider (same as chat/completions)
    """
    request_id = getattr(request.state, "request_id", "")

    # ── Rate limit ────────────────────────────────────────────────────────────
    await check_rate_limits(
        key_id=str(key.id),
        rpm_limit=key.rpm_limit,
        rpd_limit=key.rpd_limit,
        default_rpm=settings.default_rpm,
        default_rpd=settings.default_rpd,
        max_rpm=settings.max_rpm,
        max_rpd=settings.max_rpd,
    )

    # ── Spend cap ─────────────────────────────────────────────────────────────
    if key.spend_cap_usd is not None:
        await check_spend_cap(str(key.id), key.spend_cap_usd, db)

    # ── Resolve model + params from key defaults ───────────────────────────────
    body = resolve_responses_config(raw_body, key)

    # ── Balance check + free-model rate limit ─────────────────────────────────
    is_free_model = await check_balance(key.owner, body.model, db)
    if is_free_model:
        await check_free_model_rate_limits(
            key_id=str(key.id),
            free_rpm=settings.default_free_rpm,
            free_rpd=settings.default_free_rpd,
        )

    # ── Provider routing (DB-driven, same as inference.py) ────────────────────
    provider, provider_model_id, responses_provider_model_id = await resolve_routing(body.model, db)
    effective_model_id = responses_provider_model_id or provider_model_id

    # ── Capability check: model+provider must support responses API ───────────
    _price_row = await db.get(ModelPrice, (body.model, provider))
    if _price_row is not None and not _price_row.supports_responses_api:
        raise ModelCapabilityError(body.model, "responses")

    logger.info(
        "responses_request_start", 
        model=body.model,
        stream=body.stream,
        request_id=request_id,
        key_owner=key.owner,
        provider=provider,
    )

    # ── Per-owner upstream key ─────────────────────────────────────────────────
    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
    adapter = get_adapter(provider)

    # ── Responses API capability guard ────────────────────────────────────────
    _needed = "stream_responses_create" if body.stream else "responses_create"
    if getattr(type(adapter), _needed) is getattr(ProviderAdapter, _needed):
        raise HTTPException(
            status_code=501,
            detail=f"{body.model} does not have support for Responses API.",
        )

    start = time.monotonic()

    # ── Streaming path ────────────────────────────────────────────────────────
    if body.stream:
        logger.info("responses_stream_start")

        async def event_generator():
            usage_data: dict | None = None
            byte_count = 0
            buf = b""
            status = "success"
            error_code_val: str | None = None

            try:
                async for chunk in adapter.stream_responses_create(
                    body, api_key=upstream_key, owner=key.owner,
                    provider_model_id=effective_model_id,
                ):
                    if await request.is_disconnected():
                        logger.info("responses_stream_client_disconnected", bytes_sent=byte_count)
                        status = "client_disconnected"
                        return

                    byte_count += len(chunk)
                    buf += chunk

                    # Parse complete SSE frames to extract the final usage chunk.
                    # The Responses API sends usage in a trailing chunk (same
                    # pattern as chat/completions with include_usage=true).
                    while b"\n\n" in buf:
                        frame, buf = buf.split(b"\n\n", 1)
                        for line in frame.split(b"\n"):
                            if not line.startswith(b"data: "):
                                continue
                            payload = line[6:].strip()
                            if payload == b"[DONE]":
                                continue
                            try:
                                obj = json.loads(payload)
                                # OpenRouter: usage at top level, no "choices"
                                if obj.get("usage") and not obj.get("choices"):
                                    usage_data = _normalize_usage(obj["usage"])
                                # OpenAI Responses API: usage in response.completed event
                                elif obj.get("type") == "response.completed":
                                    raw = (obj.get("response") or {}).get("usage") or {}
                                    if raw:
                                        usage_data = _normalize_usage(raw)
                            except (json.JSONDecodeError, KeyError):
                                pass

                    yield chunk

            except Exception as exc:
                status = "error"
                error_code_val = getattr(exc, "error_code", "upstream_error")
                msg = getattr(exc, "message", "An upstream error occurred.")
                logger.error("responses_stream_error", error_code=error_code_val, error=str(exc))
                err_payload = json.dumps({"error": {"code": error_code_val, "message": msg}})
                yield f"data: {err_payload}\n\ndata: [DONE]\n\n".encode()

            finally:
                latency_ms = int((time.monotonic() - start) * 1000)
                log_event = (
                    "responses_stream_disconnected"
                    if status == "client_disconnected"
                    else "responses_stream_complete"
                )
                logger.info(
                    log_event,
                    bytes_sent=byte_count,
                    latency_ms=latency_ms,
                    status=status,
                    prompt_tokens=usage_data.get("prompt_tokens") if usage_data else None,
                    completion_tokens=usage_data.get("completion_tokens") if usage_data else None,
                )
                fire_usage_log(
                    owner=key.owner,
                    key_id=str(key.id),
                    request_id=request_id,
                    model=body.model,
                    provider=provider,
                    template_id=None,
                    stream=True,
                    prompt_tokens=usage_data.get("prompt_tokens") if usage_data else None,
                    completion_tokens=usage_data.get("completion_tokens") if usage_data else None,
                    cached_tokens=(
                        (usage_data.get("prompt_tokens_details") or {}).get("cached_tokens")
                        if usage_data else None
                    ),
                    upstream_cost=usage_data.get("cost") if usage_data else None,
                    latency_ms=latency_ms,
                    status=status,
                    error_code=error_code_val,
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Request-Id": request_id,
            },
        )

    # ── Non-streaming path ────────────────────────────────────────────────────
    response_body: dict | None = None
    status = "success"
    error_code_val: str | None = None

    try:
        response_body = await adapter.responses_create(
            body, api_key=upstream_key, owner=key.owner,
            provider_model_id=effective_model_id,
        )
    except Exception as exc:
        status = "error"
        error_code_val = getattr(exc, "error_code", "upstream_error")
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = _normalize_usage((response_body or {}).get("usage") or {})
        fire_usage_log(
            owner=key.owner,
            key_id=str(key.id),
            request_id=request_id,
            model=(response_body or {}).get("model", body.model),
            provider=provider,
            template_id=None,
            stream=False,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            upstream_cost=usage.get("cost"),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_val,
        )

    logger.info(
        "responses_complete",
        latency_ms=latency_ms,
        model_used=(response_body or {}).get("model", body.model),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )

    return response_body
