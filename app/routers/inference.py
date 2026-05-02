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
import uuid
from decimal import ROUND_HALF_UP, Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config_resolver import resolve_config
from app.auth.dependencies import get_authenticated_key
from app.auto_router.service import (
    AutoRouteResult,
    _auto_route_headers,
    _inject_auto_route_meta,
    _is_auto,
    resolve_auto_model,
)
from app.cache.rate_limiter import (
    check_free_model_rate_limits,
    check_rate_limits,
    check_tpm_limit,
    increment_tpm_counter,
)
from app.config import settings
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.exceptions import ModelCapabilityError, UnprocessableEntityError
from app.pricing.resolver import get_price_row
from app.providers.image_handler import _SUPPORTED_PROVIDERS, generate_images
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.providers.response_formatter import format_image_as_chat_completion
from app.schemas.chat import ChatCompletionRequest, ContentPart, ImageOptions, Message
from app.templates.renderer import render_template
from app.templates.resolver import resolve_template
from app.usage.balance import check_balance
from app.usage.logger import fire_usage_log
from app.usage.model_limits import check_allowed_models, check_model_limits
from app.usage.spend_cap import check_spend_cap

router = APIRouter()
logger = structlog.get_logger()


def _augment_usage_chunk(chunk: bytes, classifier_usages: list) -> bytes:
    """
    If chunk is an SSE usage frame, add classifier token counts to the usage object
    and adjust the totals before forwarding to the client.
    """
    if not classifier_usages or b'"usage"' not in chunk:
        return chunk
    classifier_prompt = sum(cu.prompt_tokens or 0 for cu in classifier_usages)
    classifier_completion = sum(cu.completion_tokens or 0 for cu in classifier_usages)
    try:
        lines = chunk.split(b"\n")
        new_lines = []
        for line in lines:
            if line.startswith(b"data: "):
                payload = line[6:].strip()
                if payload and payload != b"[DONE]":
                    obj = json.loads(payload)
                    if obj.get("usage"):
                        u = obj["usage"]
                        u["classifier_prompt_tokens"] = classifier_prompt
                        u["classifier_completion_tokens"] = classifier_completion
                        u["classifier_tokens"] = classifier_prompt + classifier_completion
                        u["prompt_tokens"] = (u.get("prompt_tokens") or 0) + classifier_prompt
                        u["completion_tokens"] = (
                            u.get("completion_tokens") or 0
                        ) + classifier_completion
                        u["total_tokens"] = u["prompt_tokens"] + u["completion_tokens"]
                        line = b"data: " + json.dumps(obj).encode()
            new_lines.append(line)
        return b"\n".join(new_lines)
    except (json.JSONDecodeError, KeyError):
        return chunk


def _scan_sse_buf(buf: bytes, current_usage: dict | None) -> tuple[dict | None, bytes]:
    """
    Process all complete SSE frames (\n\n-delimited) in buf.

    Returns (updated_usage, remaining_buf).  Regular streaming chunks carry
    "usage": null which is falsy, so only a real usage object updates the
    return value.  The caller should not filter on choices — some providers
    (e.g. Claude via OpenRouter) bundle usage with a non-empty choices array
    in the final content chunk.
    """
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
                if obj.get("usage"):
                    current_usage = obj["usage"]
            except (json.JSONDecodeError, KeyError):
                pass
    return current_usage, buf


def _extract_completions_content(messages: list[Message]) -> str:
    user_msgs = [msg for msg in messages if msg.role == "user"]

    if not user_msgs:
        return ""

    last_msgs = user_msgs[-2:]  # last 2 user messages

    parts = []
    for msg in last_msgs:
        if isinstance(msg.content, str):
            parts.append(msg.content)
        elif isinstance(msg.content, list):
            parts.append(
                " ".join(
                    p.text
                    for p in msg.content
                    if isinstance(p, ContentPart) and p.type == "text" and p.text
                )
            )

    return " ".join(parts)[:2000]


def _compute_audio_cost(usage: dict, price_row) -> float | None:
    """
    Calculate the total cost for a response that may contain audio tokens.

    Text tokens and audio tokens are billed at separate rates.  Text token
    count is derived by subtracting audio tokens from the totals reported by
    the provider.  Audio costs use the raw per-unit columns (audio_input_cost /
    audio_output_cost) with the same divisor as the image handler.
    """
    if price_row is None or not usage:
        return None

    pricing_unit = price_row.pricing_unit
    if pricing_unit not in ("per_1k_tokens", "per_1m_tokens"):
        return None

    divisor = Decimal(1_000_000) if pricing_unit == "per_1m_tokens" else Decimal(1_000)

    # OpenAI nests audio token counts inside *_tokens_details sub-objects.
    # Top-level input_audio_tokens / output_audio_tokens are not returned.
    audio_in = Decimal((usage.get("prompt_tokens_details") or {}).get("audio_tokens") or 0)
    audio_out = Decimal((usage.get("completion_tokens_details") or {}).get("audio_tokens") or 0)
    text_in = Decimal(max(0, (usage.get("prompt_tokens") or 0) - int(audio_in)))
    text_out = Decimal(max(0, (usage.get("completion_tokens") or 0) - int(audio_out)))

    cost = (
        (price_row.prompt_usd_per_1k or Decimal(0)) * text_in / divisor
        + (price_row.completion_usd_per_1k or Decimal(0)) * text_out / divisor
        + (price_row.audio_input_cost or Decimal(0)) * audio_in / divisor
        + (price_row.audio_output_cost or Decimal(0)) * audio_out / divisor
    )
    return float(cost.quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP))


@router.post(
    "/v1/chat/completions",
    responses={
        400: {
            "description": "Model does not support chat completions API",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "model_capability_not_supported",
                            "message": "Model 'text-embedding-3-small' does not support"
                            " the chat/completions API.",
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    }
                }
            },
        },
        401: {
            "description": "Missing or invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "unauthorized",
                            "message": "Invalid or missing API key.",
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    }
                }
            },
        },
        402: {
            "description": "Insufficient balance or spend cap reached",
            "content": {
                "application/json": {
                    "examples": {
                        "spend_cap_reached": {
                            "summary": "Per-key spend cap reached",
                            "value": {
                                "error": {
                                    "code": "spend_limit_exceeded",
                                    "message": (
                                        "Spend cap of $10.0000 reached. Current spend: $10.0023."
                                        " Contact your administrator to increase the cap."
                                    ),
                                },
                                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            },
                        },
                        "no_balance": {
                            "summary": "Insufficient credit balance",
                            "value": {
                                "error": {
                                    "code": "spend_limit_exceeded",
                                    "message": "Insufficient balance."
                                    " Top up your account to use paid models.",
                                },
                                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            },
                        },
                    }
                }
            },
        },
        403: {
            "description": "API key is suspended",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "forbidden",
                            "message": "API key is suspended.",
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    }
                }
            },
        },
        404: {
            "description": "Prompt template not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "not_found",
                            "message": "Template '01ARZ3NDEKTSV4RRFFQ69G5FAV' not found.",
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    }
                }
            },
        },
        422: {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "validation_error",
                            "message": "Request validation failed.",
                            "details": [
                                {
                                    "type": "missing",
                                    "loc": ["body", "model"],
                                    "msg": "Field required",
                                }
                            ],
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    }
                }
            },
        },
        429: {
            "description": "Rate limit exceeded (RPM or RPD)",
            "content": {
                "application/json": {
                    "examples": {
                        "rpm_exceeded": {
                            "summary": "Requests-per-minute limit hit",
                            "value": {
                                "error": {
                                    "code": "rate_limit_exceeded",
                                    "message": "RPM limit of 60 req/min exceeded.",
                                },
                                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            },
                        },
                        "rpd_exceeded": {
                            "summary": "Requests-per-day limit hit",
                            "value": {
                                "error": {
                                    "code": "rate_limit_exceeded",
                                    "message": "RPD limit of 1000 req/day exceeded.",
                                },
                                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Upstream provider error or gateway timeout",
            "content": {
                "application/json": {
                    "examples": {
                        "upstream_error": {
                            "summary": "Upstream provider returned an error",
                            "value": {
                                "error": {
                                    "code": "upstream_error",
                                    "message": "Upstream provider returned an error.",
                                    "upstream_detail": (
                                        '{"error":{"message":"No endpoints found that'
                                        ' match your data policy","code":400}}'
                                    ),
                                },
                                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            },
                        },
                        "gateway_timeout": {
                            "summary": "Upstream timed out",
                            "value": {
                                "error": {
                                    "code": "gateway_timeout",
                                    "message": "Upstream provider did not respond in time.",
                                },
                                "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                            },
                        },
                        "internal_error": {
                            "summary": "Internal platform error"
                            " (DB failure — FastAPI default format)",
                            "value": {"detail": "Internal Server Error"},
                        },
                    }
                }
            },
        },
        503: {
            "description": "Upstream provider not available —"
            " required credentials not configured on this server",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "provider_not_available",
                            "message": "Provider 'vertex' is not available."
                            " The required credentials may not be configured on this server.",
                        },
                        "request_id": "req_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    }
                }
            },
        },
    },
)
async def chat_completions(
    raw_body: ChatCompletionRequest,
    request: Request,
    key: ApiKey = Depends(get_authenticated_key),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
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
        max_rpm=settings.max_rpm,
        max_rpd=settings.max_rpd,
    )

    if key.tpm_limit is not None:
        await check_tpm_limit(str(key.id), key.tpm_limit)

    # ── Phase 5: Spend cap (per-key hard limit, optional) ────────────────────
    if key.spend_cap_usd is not None:
        await check_spend_cap(str(key.id), key.spend_cap_usd, db)

    # ── Phase 4: Template resolution + rendering ──────────────────────────────
    template = None
    rendered_messages = None
    if raw_body.template:
        template = await resolve_template(raw_body.template, key.owner, db)
        rendered_messages = render_template(template, raw_body.variables)

    # ── Phase 2: Resolve model + params ───────────────────────────────────────
    # Must happen before balance check so we have the final resolved model name.
    body = resolve_config(raw_body, key, template, rendered_messages)

    # ── Auto Router: resolve model="auto" to a concrete model ID ─────────────
    auto_route_result: AutoRouteResult | None = None
    if _is_auto(body.model):
        if not settings.auto_router_enabled:
            raise UnprocessableEntityError(
                "model='auto' is not supported. The Auto Router is disabled on this gateway.",
                status_code=400,
            )
        user_content = _extract_completions_content(body.messages)
        auto_route_result = await resolve_auto_model(
            user_content, "completions", db=db, request_id=request_id, owner=key.owner
        )
        body = body.model_copy(update={"model": auto_route_result.resolved_model_id})
        for _cu in auto_route_result.classifier_usages:
            fire_usage_log(
                owner=key.owner,
                key_id=str(key.id),
                request_id=request_id,
                model=_cu.model_id,
                provider=_cu.provider,
                template_id=None,
                stream=False,
                prompt_tokens=_cu.prompt_tokens,
                completion_tokens=_cu.completion_tokens,
                cached_tokens=None,
                upstream_cost=_cu.cost,
                latency_ms=None,
                status="success",
                error_code=None,
            )
    # ─────────────────────────────────────────────────────────────────────────
    if not body.model:
        raise UnprocessableEntityError("'model' is required.", status_code=422)

    # ── Phase 7: Model access control + per-model usage caps ─────────────────
    check_allowed_models(body.model, key.allowed_models)
    if key.model_limits:
        await check_model_limits(str(key.id), body.model, key.model_limits, db)

    # ── Balance check + free-model rate limit ────────────────────────────────
    is_free_model = await check_balance(key.owner, body.model, db)
    if is_free_model:
        await check_free_model_rate_limits(
            key_id=str(key.id),
            free_rpm=settings.default_free_rpm,
            free_rpd=settings.default_free_rpd,
        )

    log = logger.bind(
        model=body.model,
        stream=body.stream,
        request_id=request_id,
        key_owner=key.owner,
        template=raw_body.template,
    )
    # ── Phase 6: Resolve provider + per-owner upstream API key ───────────────
    provider, provider_model_id, _ = await resolve_routing(body.model, db)

    # ── Capability check: model+provider must support chat/completions ────────
    _price_row = await get_price_row(body.model, provider, db)

    # ── Image generation path ─────────────────────────────────────────────────
    # Auto-detect image modality from the DB when the client doesn't set it:
    # any model whose pricing row has "image" in modality and does not support
    # the completions API is treated as an image-generation model.
    _is_image_model = (
        _price_row is not None
        and "image" in (_price_row.modality or [])
        and not _price_row.supports_completions_api
    )
    if body.modality == "image" or _is_image_model:
        if provider not in _SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=501,
                detail=f"Provider '{provider}' does not support image generation",
            )

        # Async job mode — return immediately, no upstream call yet
        if body.async_mode:
            job_id = f"imgjob-{uuid.uuid4().hex[:12]}"
            return JSONResponse({"job_id": job_id, "status": "pending"})

        # Extract and aggregate all user turn text as the prompt
        prompt_parts: list[str] = []
        for m in body.messages:
            if m.role != "user":
                continue
            if isinstance(m.content, str):
                prompt_parts.append(m.content)
            elif isinstance(m.content, list):
                prompt_parts.append(
                    " ".join(p.text for p in m.content if p.type == "text" and p.text)
                )
        prompt = "\n".join(p for p in prompt_parts if p.strip())
        if not prompt:
            raise HTTPException(status_code=422, detail="No text content found in user messages")

        upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
        opts = body.image or ImageOptions()
        start = time.monotonic()

        gen = await generate_images(
            prompt,
            provider=provider,
            provider_model_id=provider_model_id or (body.model or "").split("/")[-1],
            opts=opts,
            api_key=upstream_key,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        # Cost calculation:
        # - per_image / per_request models  → image_output_cost or request_cost × n
        # - per_1k/per_1m token models      → use token counts returned by the provider
        image_cost_usd: float | None = None
        if _price_row is not None:
            _is_token_priced = _price_row.pricing_unit in ("per_1k_tokens", "per_1m_tokens")
            if _is_token_priced:
                if gen.input_tokens is not None or gen.output_tokens is not None:
                    # Input: text tokens — prompt_usd_per_1k is already normalised to per-1k
                    _in = (
                        (_price_row.prompt_usd_per_1k or Decimal(0))
                        * Decimal(gen.input_tokens or 0)
                        / 1000
                    )
                    # Output: image tokens — use image_output_cost (raw per-1M/1K column)
                    # if set, otherwise fall back to the text output rate.
                    _img_out_rate = _price_row.image_output_cost or _price_row.completion_usd_per_1k
                    _out_divisor = (
                        Decimal(1_000_000)
                        if _price_row.pricing_unit == "per_1m_tokens"
                        else Decimal(1_000)
                    )
                    _out = (
                        (_img_out_rate or Decimal(0))
                        * Decimal(gen.output_tokens or 0)
                        / _out_divisor
                    )
                    image_cost_usd = float(
                        (_in + _out).quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_UP)
                    )
                # else: token-priced but provider didn't return token counts → cost unknown
            else:
                # per_image / per_request pricing: flat rate per image generated
                _per_img = _price_row.image_output_cost or _price_row.request_cost
                if _per_img is not None:
                    image_cost_usd = float(
                        (_per_img * Decimal(opts.n)).quantize(
                            Decimal("0.0000000001"), rounding=ROUND_HALF_UP
                        )
                    )

        fire_usage_log(
            owner=key.owner,
            key_id=str(key.id),
            request_id=request_id,
            model=body.model,
            provider=provider,
            template_id=str(template.id) if template else None,
            stream=False,
            prompt_tokens=gen.input_tokens,
            completion_tokens=gen.output_tokens,
            cached_tokens=None,
            upstream_cost=image_cost_usd,
            latency_ms=latency_ms,
            status="success",
            error_code=None,
        )

        result = format_image_as_chat_completion(
            gen,
            model_id=body.model or provider_model_id or "",
            cost_usd=image_cost_usd,
        )
        log.info("image_generation_complete", count=len(gen.items), latency_ms=latency_ms)
        return JSONResponse(result)

    # ── Audio capability guard ────────────────────────────────────────────────
    _has_audio_input = any(
        isinstance(m.content, list) and any(p.type == "input_audio" for p in m.content)
        for m in body.messages
    )
    _wants_audio_output = body.modalities is not None and "audio" in body.modalities
    if (_has_audio_input or _wants_audio_output) and _price_row is not None:
        if "audio" not in (_price_row.modality or []):
            raise ModelCapabilityError(body.model, "audio")

    # Streaming audio output only supports pcm16 — WAV/MP3/etc. require a
    # file header that cannot be prepended to an already-started SSE stream.
    if body.stream and _wants_audio_output and body.audio is not None:
        if body.audio.format != "pcm16":
            raise UnprocessableEntityError(
                f"Audio format '{body.audio.format}' is not supported for streaming. "
                "Use format='pcm16' when stream=true."
            )

    # Skip completions_api guard for image modality (handled above);
    # enforce it for all other modalities.
    if _price_row is not None and not _price_row.supports_completions_api:
        raise ModelCapabilityError(body.model, "chat/completions")

    upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)

    adapter = get_adapter(provider)
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
                    body,
                    api_key=upstream_key,
                    owner=key.owner,
                    provider_model_id=provider_model_id,
                ):
                    # Phase 4: early exit on client disconnect
                    if await request.is_disconnected():
                        log.info("stream_client_disconnected", bytes_sent=byte_count)
                        return

                    byte_count += len(chunk)
                    buf += chunk

                    # Phase 5: scan complete SSE frames for usage metadata.
                    usage_data, buf = _scan_sse_buf(buf, usage_data)

                    if auto_route_result is not None:
                        chunk = _augment_usage_chunk(chunk, auto_route_result.classifier_usages)
                    yield chunk

            except Exception as exc:
                status = "error"
                error_code_val = getattr(exc, "error_code", "upstream_error")
                msg = getattr(exc, "message", "An upstream error occurred.")
                log.exception(
                    "stream_error",
                    error_code=error_code_val,
                    error_type=type(exc).__name__,
                    error_repr=repr(exc),
                    error_message=msg,
                    upstream_status=getattr(exc, "status_code", None),
                    upstream_body=getattr(exc, "body", None),
                )
                # Headers (200 + text/event-stream) already sent — can't change
                # status code. Yield an SSE error frame so clients can handle it.
                err_payload = json.dumps({"error": {"code": error_code_val, "message": msg}})
                yield f"data: {err_payload}\n\ndata: [DONE]\n\n".encode()

            finally:
                latency_ms = int((time.monotonic() - start) * 1000)
                log.info(
                    "stream_complete",
                    bytes_sent=byte_count,
                    latency_ms=latency_ms,
                    status=status,
                    prompt_tokens=(usage_data.get("prompt_tokens") if usage_data else None),
                    completion_tokens=(usage_data.get("completion_tokens") if usage_data else None),
                )
                _stream_cost = (
                    _compute_audio_cost(usage_data, _price_row)
                    if usage_data and (_has_audio_input or _wants_audio_output)
                    else (usage_data.get("cost") if usage_data else None)
                )
                fire_usage_log(
                    owner=key.owner,
                    key_id=str(key.id),
                    request_id=request_id,
                    model=body.model,
                    provider=provider,
                    template_id=template_id,
                    stream=True,
                    prompt_tokens=(usage_data.get("prompt_tokens") if usage_data else None),
                    completion_tokens=(usage_data.get("completion_tokens") if usage_data else None),
                    cached_tokens=(
                        (usage_data.get("prompt_tokens_details") or {}).get("cached_tokens")
                        if usage_data
                        else None
                    ),
                    upstream_cost=_stream_cost,
                    latency_ms=latency_ms,
                    status=status,
                    error_code=error_code_val,
                )
                if key.tpm_limit is not None:
                    _stream_tokens = usage_data.get("total_tokens") if usage_data else None
                    asyncio.create_task(increment_tpm_counter(str(key.id), _stream_tokens))

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Request-Id": request_id,
                **(_auto_route_headers(auto_route_result) if auto_route_result is not None else {}),
            },
        )

    # ── Non-streaming path ────────────────────────────────────────────────────
    response_body: dict | None = None
    status = "success"
    error_code_val: str | None = None
    provider_latency_ms = 0

    provider_start = time.monotonic()
    try:
        response_body = await adapter.chat_completion(
            body,
            api_key=upstream_key,
            owner=key.owner,
            provider_model_id=provider_model_id,
        )
    except Exception as exc:
        status = "error"
        error_code_val = getattr(exc, "error_code", "upstream_error")
        raise
    finally:
        provider_latency_ms = int((time.monotonic() - provider_start) * 1000)
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = (response_body or {}).get("usage") or {}
        _nonstream_cost = (
            _compute_audio_cost(usage, _price_row)
            if usage and (_has_audio_input or _wants_audio_output)
            else usage.get("cost")
        )
        fire_usage_log(
            owner=key.owner,
            key_id=str(key.id),
            request_id=request_id,
            model=body.model,
            provider=provider,
            template_id=template_id,
            stream=False,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            upstream_cost=_nonstream_cost,
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_val,
        )
        if key.tpm_limit is not None:
            asyncio.create_task(increment_tpm_counter(str(key.id), usage.get("total_tokens")))

    log.info(
        "inference_complete",
        latency_ms=latency_ms,
        model_used=(response_body or {}).get("model") or body.model,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )

    if auto_route_result is not None and response_body is not None:
        _inject_auto_route_meta(response_body, auto_route_result)
        if auto_route_result.classifier_usages and isinstance(response_body.get("usage"), dict):
            classifier_prompt = sum(
                cu.prompt_tokens or 0 for cu in auto_route_result.classifier_usages
            )
            classifier_completion = sum(
                cu.completion_tokens or 0 for cu in auto_route_result.classifier_usages
            )
            u = response_body["usage"]
            u["classifier_prompt_tokens"] = classifier_prompt
            u["classifier_completion_tokens"] = classifier_completion
            u["classifier_tokens"] = classifier_prompt + classifier_completion
            u["prompt_tokens"] = (u.get("prompt_tokens") or 0) + classifier_prompt
            u["completion_tokens"] = (u.get("completion_tokens") or 0) + classifier_completion
            u["total_tokens"] = u["prompt_tokens"] + u["completion_tokens"]

    return JSONResponse(
        content=response_body,
        headers={"X-Provider-Latency-Ms": str(provider_latency_ms)},
    )
