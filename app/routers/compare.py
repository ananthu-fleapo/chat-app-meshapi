"""
Multi-model comparison router — POST /v1/chat/compare

Fans out a single conversation to N models in parallel, then (optionally)
calls a comparison LLM to synthesize a structured evaluation of all responses.

Non-streaming: waits for all results, returns CompareResponse JSON.
Streaming (SSE): two modes depending on skip_comparison:

  skip_comparison=False (default):
    Fan-out is non-streaming (full response per model), then comparison LLM
    is streamed token-by-token.
    SSE events: meta → model_chunk (per model) → model_done → comparison_chunk* → done

  skip_comparison=True:
    Each fan-out model is streamed in real-time concurrently (token-by-token).
    No comparison LLM call.
    SSE events: meta → model_chunk (raw tokens, tagged by model)
               → model_stream_done (per model) → done

"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_authenticated_key
from app.cache.rate_limiter import check_rate_limits, check_tpm_limit
from app.compare.engine import (
    _call_single_model,
    _stream_single_model_into_queue,
    fan_out_completions,
    run_comparison,
)
from app.compare.prompt import build_comparison_messages
from app.config import settings
from app.db.models import ApiKey
from app.db.session import get_db_session
from app.exceptions import UnprocessableEntityError
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.providers.sse_utils import parse_sse_frame, scan_sse_buf
from app.schemas.chat import ChatCompletionRequest, Message
from app.schemas.compare import CompareRequest, CompareResponse, ModelOverride
from app.usage.balance import check_balance
from app.usage.logger import fire_usage_log
from app.usage.spend_cap import check_spend_cap

router = APIRouter()
logger = structlog.get_logger()


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def _new_comparison_id() -> str:
    return f"cmp_{uuid.uuid4().hex[:20]}"


def _deduplicate_models(models: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in models:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


@router.post("/v1/chat/compare")
async def chat_compare(
    body: CompareRequest,
    request: Request,
    key: ApiKey = Depends(get_authenticated_key),  # noqa: B008
    db: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    comparison_id = _new_comparison_id()

    log = logger.bind(
        comparison_id=comparison_id,
        request_id=request_id,
        key_owner=key.owner,
        stream=body.stream,
    )

    # ── Deduplicate + validate models list ────────────────────────────────────
    models = _deduplicate_models(body.models)
    if len(models) < len(body.models):
        log.warning(
            "compare_models_deduplicated",
            original=body.models,
            deduplicated=models,
        )
    if len(models) > settings.compare_max_models:
        raise UnprocessableEntityError(
            f"Too many models. Maximum allowed is {settings.compare_max_models}."
        )

    # ── Resolve comparison model ──────────────────────────────────────────────
    comparison_model = body.comparison_model or settings.compare_default_model
    if not body.skip_comparison and not comparison_model:
        raise UnprocessableEntityError(
            "comparison_model is required. "
            "Either pass it in the request or configure COMPARE_DEFAULT_MODEL on the gateway."
        )

    log = log.bind(
        models=models,
        comparison_model=comparison_model,
        skip_comparison=body.skip_comparison,
    )
    log.info("compare_request_received")

    # ── Rate limits + spend cap + balance (same pattern as inference router) ──
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
    if key.spend_cap_usd is not None:
        await check_spend_cap(str(key.id), key.spend_cap_usd, db)
    if not body.skip_comparison:
        await check_balance(key.owner, comparison_model, db)

    # ── Rebind body with deduplicated models (immutable model, so use copy) ───
    body = body.model_copy(update={"models": models})

    fan_out_start = time.monotonic()

    if body.stream:
        return _build_streaming_response(
            body=body,
            models=models,
            comparison_model=comparison_model,
            comparison_id=comparison_id,
            request_id=request_id,
            key=key,
            db=db,
            fan_out_start=fan_out_start,
            log=log,
            request=request,
            skip_comparison=body.skip_comparison,
        )

    # ── Non-streaming path ────────────────────────────────────────────────────
    results = await fan_out_completions(
        request=body,
        key=key,
        db=db,
        outer_request_id=request_id,
        comparison_id=comparison_id,
    )

    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    if not successful:
        log.error("compare_all_models_failed", failed_count=len(failed))
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "all_models_failed",
                    "message": "All models returned errors.",
                    "details": [
                        {"model": r.model, "error": r.error, "error_code": r.error_code}
                        for r in failed
                    ],
                }
            },
        )

    comparison_text: str | None = None
    comparison_usage = None
    comparison_model_used: str | None = None
    comparison_fallback_used = False

    if len(successful) >= 2 and not body.skip_comparison:
        (
            comparison_text,
            comparison_usage,
            comparison_model_used,
            comparison_fallback_used,
        ) = await run_comparison(
            comparison_model=comparison_model,
            original_messages=body.messages,
            results=successful,
            custom_instructions=body.comparison_instructions,
            key=key,
            db=db,
            outer_request_id=request_id,
            comparison_id=comparison_id,
        )
    elif body.skip_comparison:
        log.info("compare_skip_comparison_requested")
    else:
        log.info("compare_single_model_no_synthesis")

    total_latency_ms = int((time.monotonic() - fan_out_start) * 1000)

    log.info(
        "compare_complete",
        total_latency_ms=total_latency_ms,
        successful=len(successful),
        failed=len(failed),
    )

    response = CompareResponse(
        comparison_id=comparison_id,
        created=int(datetime.now(UTC).timestamp()),
        models=models,
        results=results,
        comparison=comparison_text,
        comparison_model=comparison_model_used,
        comparison_usage=comparison_usage,
        comparison_fallback_used=comparison_fallback_used,
        total_latency_ms=total_latency_ms,
        partial=len(failed) > 0,
        skip_comparison=body.skip_comparison,
    )

    return JSONResponse(
        content=response.model_dump(),
        headers={"X-Request-Id": request_id},
    )


def _build_streaming_response(
    *,
    body: CompareRequest,
    models: list[str],
    comparison_model: str,
    comparison_id: str,
    request_id: str,
    key: ApiKey,
    db: AsyncSession,
    fan_out_start: float,
    log: structlog.stdlib.BoundLogger,
    request: Request,
    skip_comparison: bool = False,
) -> StreamingResponse:
    async def event_generator():
        # ── meta ─────────────────────────────────────────────────────────────
        yield _sse(
            "meta",
            {
                "comparison_id": comparison_id,
                "models": models,
                "comparison_model": comparison_model if not skip_comparison else None,
                "skip_comparison": skip_comparison,
            },
        )

        # ── skip_comparison path: per-model real-time streaming ───────────────
        if skip_comparison:
            override_map: dict[str, ModelOverride] = {}
            if body.model_overrides:
                for ov in body.model_overrides:
                    override_map[ov.model] = ov

            queue: asyncio.Queue = asyncio.Queue()
            tasks = [
                asyncio.ensure_future(
                    _stream_single_model_into_queue(
                        model=m,
                        messages=body.messages,
                        base_request=body,
                        override=override_map.get(m),
                        key=key,
                        db=db,
                        outer_request_id=request_id,
                        comparison_id=comparison_id,
                        queue=queue,
                    )
                )
                for m in models
            ]

            remaining = len(models)
            any_errors = False
            last_usage: dict[str, dict] = {}
            while remaining > 0:
                if await request.is_disconnected():
                    log.info("compare_stream_client_disconnected")
                    for t in tasks:
                        t.cancel()
                    return

                model_name, parsed, error = await queue.get()
                if parsed is not None:
                    if parsed.get("usage"):
                        last_usage[model_name] = parsed["usage"]
                    yield _sse(
                        "model_chunk",
                        {
                            "model": model_name,
                            "delta": parsed.get("delta"),
                            "finish_reason": parsed.get("finish_reason"),
                        },
                    )
                else:
                    if error:
                        any_errors = True
                    yield _sse(
                        "model_stream_done",
                        {
                            "model": model_name,
                            "finish_reason": None,
                            "usage": last_usage.get(model_name),
                            "error": error,
                        },
                    )
                    remaining -= 1

            total_latency_ms = int((time.monotonic() - fan_out_start) * 1000)
            log.info(
                "compare_complete",
                total_latency_ms=total_latency_ms,
                stream=True,
                skip_comparison=True,
            )
            yield _sse(
                "done",
                {
                    "comparison_id": comparison_id,
                    "total_latency_ms": total_latency_ms,
                    "partial": any_errors,
                    "skip_comparison": True,
                },
            )
            return

        # ── Fan-out: emit model_chunk events as each model finishes ──────────
        override_map: dict[str, ModelOverride] = {}
        if body.model_overrides:
            for ov in body.model_overrides:
                override_map[ov.model] = ov

        pending_tasks: dict[asyncio.Future, str] = {
            asyncio.ensure_future(
                _call_single_model(
                    model=m,
                    messages=body.messages,
                    base_request=body,
                    override=override_map.get(m),
                    key=key,
                    db=db,
                    outer_request_id=request_id,
                    comparison_id=comparison_id,
                )
            ): m
            for m in models
        }

        results_map: dict[str, object] = {}  # model -> ModelCompareResult

        for coro in asyncio.as_completed(list(pending_tasks)):
            if await request.is_disconnected():
                log.info("compare_stream_client_disconnected")
                for t in pending_tasks:
                    t.cancel()
                return

            result = await coro
            results_map[result.model] = result
            yield _sse(
                "model_chunk",
                {
                    "model": result.model,
                    "delta": result.content,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "error_code": result.error_code,
                    "usage": result.usage.model_dump() if result.usage else None,
                },
            )

        # Restore original order
        from app.schemas.compare import ModelCompareResult  # noqa: PLC0415

        results: list[ModelCompareResult] = [results_map[m] for m in models if m in results_map]  # type: ignore[assignment]

        yield _sse(
            "model_done",
            {
                "results": [r.model_dump() for r in results],
            },
        )

        # ── Comparison LLM streaming with fallback chain ──────────────────────
        successful = [r for r in results if r.error is None]

        stream_comparison_model_used: str | None = None
        stream_comparison_fallback_used = False

        if len(successful) >= 2:
            fallback_candidates = [comparison_model] + [
                m for m in settings.compare_fallback_models_list if m != comparison_model
            ]
            comp_messages_raw = build_comparison_messages(
                body.messages, successful, body.comparison_instructions
            )
            comp_messages = [Message(**m) for m in comp_messages_raw]

            for attempt, cand_model in enumerate(fallback_candidates):
                if attempt > 0:
                    log.warning(
                        "compare_stream_synthesis_fallback",
                        attempt=attempt,
                        model=cand_model,
                    )
                comp_start = time.monotonic()
                comp_provider = "unknown"
                comp_status = "error"
                comp_error_code: str | None = None
                comp_buf = b""
                comp_usage: dict | None = None
                comp_sub_id = (
                    f"{request_id}::comparison"
                    if attempt == 0
                    else f"{request_id}::comparison_fallback_{attempt}"
                )
                try:
                    comp_provider, provider_model_id, _ = await resolve_routing(cand_model, db)
                    upstream_key = await resolve_upstream_key(
                        owner=key.owner, provider=comp_provider, db=db
                    )
                    adapter = get_adapter(comp_provider)

                    comp_req = ChatCompletionRequest(
                        model=cand_model,
                        messages=comp_messages,
                        stream=True,
                        temperature=0.3,
                        max_tokens=2048,
                    )

                    async for chunk in adapter.stream_chat_completion(
                        comp_req,
                        api_key=upstream_key,
                        owner=key.owner,
                        provider_model_id=provider_model_id,
                    ):
                        if await request.is_disconnected():
                            log.info("compare_stream_comparison_disconnected")
                            return
                        comp_buf += chunk
                        while b"\n\n" in comp_buf:
                            frame, comp_buf = comp_buf.split(b"\n\n", 1)
                            parsed = parse_sse_frame(frame)
                            if parsed is not None:
                                if parsed.get("usage"):
                                    comp_usage = parsed["usage"]
                                if parsed.get("delta") is not None or parsed.get("finish_reason"):
                                    yield _sse(
                                        "comparison_chunk",
                                        {
                                            "delta": parsed["delta"],
                                            "finish_reason": parsed["finish_reason"],
                                        },
                                    )

                    comp_status = "success"
                    stream_comparison_model_used = cand_model
                    stream_comparison_fallback_used = attempt > 0
                    log.info(
                        "compare_stream_synthesis_success",
                        model=cand_model,
                        attempt=attempt,
                        latency_ms=int((time.monotonic() - comp_start) * 1000),
                    )
                    break  # success — stop trying fallbacks

                except Exception as exc:
                    comp_error_code = getattr(exc, "error_code", "upstream_error")
                    log.warning(
                        "compare_stream_comparison_error",
                        model=cand_model,
                        attempt=attempt,
                        error_type=type(exc).__name__,
                        error_repr=repr(exc),
                    )
                    # continue to next fallback

                finally:
                    comp_latency_ms = int((time.monotonic() - comp_start) * 1000)
                    if comp_buf:
                        comp_usage, _ = scan_sse_buf(comp_buf + b"\n\n", comp_usage)
                    fire_usage_log(
                        owner=key.owner,
                        provider=comp_provider,
                        key_id=str(key.id),
                        request_id=comp_sub_id,
                        model=cand_model,
                        template_id=None,
                        stream=True,
                        prompt_tokens=(comp_usage or {}).get("prompt_tokens"),
                        completion_tokens=(comp_usage or {}).get("completion_tokens"),
                        cached_tokens=None,
                        upstream_cost=(comp_usage or {}).get("cost"),
                        latency_ms=comp_latency_ms,
                        status=comp_status,
                        error_code=comp_error_code,
                    )

            if stream_comparison_model_used is None:
                log.error("compare_stream_synthesis_all_failed", candidates=fallback_candidates)
        else:
            log.info("compare_stream_single_model_no_synthesis")

        total_latency_ms = int((time.monotonic() - fan_out_start) * 1000)
        log.info("compare_complete", total_latency_ms=total_latency_ms, stream=True)

        yield _sse(
            "done",
            {
                "comparison_id": comparison_id,
                "total_latency_ms": total_latency_ms,
                "partial": any(r.error for r in results),
                "comparison_model": stream_comparison_model_used,
                "comparison_fallback_used": stream_comparison_fallback_used,
            },
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
