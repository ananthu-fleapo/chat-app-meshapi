"""
Inference router — POST /v1/chat/completions

Phase additions per phase:
  Phase 1 → bare proxy (no auth)
  Phase 2 → get_authenticated_key, resolve_config
  Phase 3 → check_rate_limits (Redis fixed-window RPM + RPD)
  Phase 4 → template resolution + rendering, streaming disconnect detection
  Phase 5 → spend cap enforcement, usage logging (non-stream + SSE-parsed stream)
"""

import asyncio
import json
import time

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config_resolver import resolve_config
from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_rate_limits
from app.config import settings
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter
from app.schemas.chat import ChatCompletionRequest
from app.templates.renderer import render_template
from app.templates.resolver import resolve_template
from app.usage.logger import fire_usage_log
from app.usage.spend_cap import check_spend_cap

router = APIRouter()
logger = structlog.get_logger()


@router.post("/v1/chat/completions")
async def chat_completions(
    raw_body: ChatCompletionRequest,
    request: Request,
    key: ApiKey = Depends(get_authenticated_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    OpenAI-compatible chat completions endpoint.

    Auth:        Authorization: Bearer rsk_<ULID>
    Streaming:   set stream=true for SSE chunks
    Templates:   set template="name" + variables={...}
    Rate limits: RPM and RPD enforced per key via Redis fixed-window counters
    Spend cap:   enforced if key.spend_cap_usd is set (soft cap)
    """
    request_id = getattr(request.state, "request_id", "")

    # ── Phase 3: Rate limit ───────────────────────────────────────────────────
    await check_rate_limits(
        key_id=str(key.id),
        rpm_limit=key.rpm_limit,
        rpd_limit=key.rpd_limit,
        default_rpm=settings.default_rpm,
        default_rpd=settings.default_rpd,
    )

    # ── Phase 5: Spend cap ────────────────────────────────────────────────────
    if key.spend_cap_usd is not None:
        await check_spend_cap(str(key.id), key.spend_cap_usd, db)

    # ── Phase 4: Template resolution + rendering ──────────────────────────────
    template = None
    rendered_messages = None
    if raw_body.template:
        template = await resolve_template(raw_body.template, key.owner, db)
        rendered_messages = render_template(template, raw_body.variables)

    # ── Phase 2: Resolve model + params ───────────────────────────────────────
    body = resolve_config(raw_body, key, template, rendered_messages)

    log = logger.bind(
        model=body.model,
        stream=body.stream,
        request_id=request_id,
        key_owner=key.owner,
        template=raw_body.template,
    )
    # ── Phase 6: Resolve per-owner upstream API key ───────────────────────────
    upstream_key = await resolve_upstream_key(owner=key.owner, db=db)

    adapter = get_adapter(body.model)
    start = time.monotonic()
    template_id = str(template.id) if template else None

    # ── Streaming path ────────────────────────────────────────────────────────
    if body.stream:
        log.info("inference_stream_start")

        async def event_generator():
            """
            Proxies upstream SSE bytes to the client.

            Phase 4: detects client disconnect and exits early.
            Phase 5: parses SSE frames to extract the final usage chunk
                     (sent by OpenRouter when stream_options.include_usage=true),
                     then fires usage logging in the finally block.
            """
            usage_data: dict | None = None
            byte_count = 0
            buf = b""
            status = "success"
            error_code_val: str | None = None

            try:
                async for chunk in adapter.stream_chat_completion(
                    body, api_key=upstream_key, owner=key.owner
                ):
                    # Phase 4: early exit on client disconnect
                    if await request.is_disconnected():
                        log.info("stream_client_disconnected", bytes_sent=byte_count)
                        return

                    byte_count += len(chunk)
                    buf += chunk

                    # Phase 5: scan complete SSE frames for the usage metadata
                    # chunk. OpenRouter sends it as the last data frame before
                    # [DONE], with choices=[] and a usage={...} object.
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
                                # Usage chunk: choices is empty, usage is present
                                if obj.get("usage") and not obj.get("choices"):
                                    usage_data = obj["usage"]
                            except (json.JSONDecodeError, KeyError):
                                pass

                    yield chunk

            except Exception as exc:
                status = "error"
                error_code_val = getattr(exc, "error_code", "upstream_error")
                raise

            finally:
                latency_ms = int((time.monotonic() - start) * 1000)
                log.info(
                    "stream_complete",
                    bytes_sent=byte_count,
                    latency_ms=latency_ms,
                    status=status,
                    prompt_tokens=usage_data.get("prompt_tokens") if usage_data else None,
                    completion_tokens=usage_data.get("completion_tokens") if usage_data else None,
                )
                fire_usage_log(
                    key_id=str(key.id),
                    request_id=request_id,
                    model=body.model,
                    template_id=template_id,
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
        response_body = await adapter.chat_completion(body, api_key=upstream_key, owner=key.owner)
    except Exception as exc:
        status = "error"
        error_code_val = getattr(exc, "error_code", "upstream_error")
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = (response_body or {}).get("usage") or {}
        fire_usage_log(
            key_id=str(key.id),
            request_id=request_id,
            model=(response_body or {}).get("model", body.model),
            template_id=template_id,
            stream=False,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            upstream_cost=usage.get("cost"),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_val,
        )

    log.info(
        "inference_complete",
        latency_ms=latency_ms,
        model_used=response_body.get("model", body.model),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )

    return response_body
