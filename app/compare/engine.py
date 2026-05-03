"""
Fan-out orchestration and comparison synthesis for POST /v1/chat/compare.

_call_single_model()  — calls one model; never raises (all errors captured)
fan_out_completions() — calls all models concurrently via asyncio.gather
run_comparison()      — calls the comparison LLM; returns (text, usage) or (None, None)
"""

from __future__ import annotations

import asyncio
import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.compare.prompt import build_comparison_messages
from app.config import settings
from app.db.models import ApiKey
from app.exceptions import UnsupportedModelError
from app.providers.key_resolver import resolve_upstream_key
from app.providers.registry import get_adapter, resolve_routing
from app.providers.sse_utils import parse_sse_frame, scan_sse_buf
from app.schemas.chat import ChatCompletionRequest, Message
from app.schemas.compare import (
    CompareRequest,
    ModelCompareResult,
    ModelOverride,
    TokenUsage,
)
from app.usage.logger import fire_usage_log

logger = structlog.get_logger()


async def _call_single_model(
    *,
    model: str,
    messages: list[Message],
    base_request: CompareRequest,
    override: ModelOverride | None,
    key: ApiKey,
    db: AsyncSession,
    outer_request_id: str,
    comparison_id: str,
) -> ModelCompareResult:
    """
    Call one model and return a ModelCompareResult.  Never raises.
    All errors — timeout, unsupported model, upstream failures — are captured
    as result.error / result.error_code.
    """
    sub_request_id = f"{outer_request_id}::{model}"
    start = time.monotonic()

    # Initialise before try so finally block always has valid bindings
    provider = "unknown"
    status = "error"
    error_str: str | None = None
    error_code_str: str | None = None
    response_body: dict | None = None
    usage: TokenUsage | None = None
    content: str | None = None

    log = logger.bind(
        model=model,
        sub_request_id=sub_request_id,
        comparison_id=comparison_id,
        key_owner=key.owner,
    )

    try:
        provider, provider_model_id, _ = await resolve_routing(model, db)
        upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
        adapter = get_adapter(provider)

        # Apply per-model overrides on top of request-level defaults
        temperature = (override.temperature if override else None) or base_request.temperature
        max_tokens = (override.max_tokens if override else None) or base_request.max_tokens

        # Build messages — optionally prepend a per-model system prompt
        msg_dicts: list[dict] = []
        if override and override.system_prompt:
            msg_dicts.append({"role": "system", "content": override.system_prompt})
        msg_dicts.extend(m.model_dump() for m in messages)

        chat_req = ChatCompletionRequest(
            model=model,
            messages=[Message(**d) for d in msg_dicts],
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response_body = await asyncio.wait_for(
            adapter.chat_completion(
                chat_req,
                api_key=upstream_key,
                owner=key.owner,
                provider_model_id=provider_model_id,
            ),
            timeout=settings.compare_model_timeout_s,
        )

        # Extract content from first choice
        choices = (response_body or {}).get("choices") or []
        if choices:
            msg_obj = choices[0].get("message") or {}
            content = msg_obj.get("content")

        raw_usage = (response_body or {}).get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=raw_usage.get("prompt_tokens"),
            completion_tokens=raw_usage.get("completion_tokens"),
            total_tokens=raw_usage.get("total_tokens"),
        )
        status = "success"
        log.info("compare_model_success", latency_ms=int((time.monotonic() - start) * 1000))

    except TimeoutError:
        error_str = f"Model '{model}' timed out after {int(settings.compare_model_timeout_s)}s."
        error_code_str = "gateway_timeout"
        log.warning("compare_model_timeout", timeout_s=settings.compare_model_timeout_s)

    except UnsupportedModelError:
        error_str = f"Model '{model}' is not supported or has no pricing entry."
        error_code_str = "model_not_found"
        log.warning("compare_model_unsupported")

    except Exception as exc:
        error_str = getattr(exc, "message", str(exc)) or type(exc).__name__
        error_code_str = getattr(exc, "error_code", "upstream_error")
        log.warning(
            "compare_model_error",
            error_type=type(exc).__name__,
            error_repr=repr(exc),
        )

    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        raw_usage_final = (response_body or {}).get("usage") or {}
        fire_usage_log(
            owner=key.owner,
            provider=provider,
            key_id=str(key.id),
            request_id=sub_request_id,
            model=model,
            template_id=None,
            stream=False,
            prompt_tokens=raw_usage_final.get("prompt_tokens"),
            completion_tokens=raw_usage_final.get("completion_tokens"),
            cached_tokens=None,
            upstream_cost=raw_usage_final.get("cost"),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_str,
        )

    return ModelCompareResult(
        model=model,
        response_body=response_body,
        content=content,
        latency_ms=int((time.monotonic() - start) * 1000),
        error=error_str,
        error_code=error_code_str,
        usage=usage,
        request_id=sub_request_id,
    )


async def fan_out_completions(
    *,
    request: CompareRequest,
    key: ApiKey,
    db: AsyncSession,
    outer_request_id: str,
    comparison_id: str,
) -> list[ModelCompareResult]:
    """
    Call all models concurrently.  Results are returned in the same order as
    request.models.  Never raises — individual failures are captured per result.
    """
    override_map: dict[str, ModelOverride] = {}
    if request.model_overrides:
        for ov in request.model_overrides:
            override_map[ov.model] = ov

    tasks = [
        _call_single_model(
            model=model,
            messages=request.messages,
            base_request=request,
            override=override_map.get(model),
            key=key,
            db=db,
            outer_request_id=outer_request_id,
            comparison_id=comparison_id,
        )
        for model in request.models
    ]

    # gather preserves input order; _call_single_model never raises so
    # return_exceptions=False is safe here.
    results = await asyncio.gather(*tasks)
    return list(results)


async def _attempt_comparison(
    *,
    model: str,
    comp_messages: list[Message],
    key: ApiKey,
    db: AsyncSession,
    sub_request_id: str,
    comparison_id: str,
) -> tuple[str, TokenUsage] | None:
    """
    Try to run one comparison model.  Returns (text, usage) on success or None
    on any failure.  Always fires a usage log regardless of outcome.
    """
    start = time.monotonic()
    provider = "unknown"
    status = "error"
    error_code_str: str | None = None
    response_body: dict | None = None

    log = logger.bind(
        model=model,
        sub_request_id=sub_request_id,
        comparison_id=comparison_id,
        key_owner=key.owner,
    )

    try:
        provider, provider_model_id, _ = await resolve_routing(model, db)
        upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
        adapter = get_adapter(provider)

        chat_req = ChatCompletionRequest(
            model=model,
            messages=comp_messages,
            stream=False,
            temperature=0.3,
            max_tokens=2048,
        )

        response_body = await asyncio.wait_for(
            adapter.chat_completion(
                chat_req,
                api_key=upstream_key,
                owner=key.owner,
                provider_model_id=provider_model_id,
            ),
            timeout=settings.compare_model_timeout_s,
        )

        choices = (response_body or {}).get("choices") or []
        text: str | None = None
        if choices:
            text = (choices[0].get("message") or {}).get("content")

        raw_usage = (response_body or {}).get("usage") or {}
        usage = TokenUsage(
            prompt_tokens=raw_usage.get("prompt_tokens"),
            completion_tokens=raw_usage.get("completion_tokens"),
            total_tokens=raw_usage.get("total_tokens"),
        )
        status = "success"
        log.info("compare_synthesis_success", latency_ms=int((time.monotonic() - start) * 1000))
        return (text or "", usage)

    except TimeoutError:
        error_code_str = "gateway_timeout"
        log.warning(
            "compare_synthesis_timeout",
            timeout_s=settings.compare_model_timeout_s,
        )
        return None

    except UnsupportedModelError:
        error_code_str = "model_not_found"
        log.warning("compare_synthesis_unsupported_model")
        return None

    except Exception as exc:
        error_code_str = getattr(exc, "error_code", "upstream_error")
        log.warning(
            "compare_synthesis_error",
            error_type=type(exc).__name__,
            error_repr=repr(exc),
        )
        return None

    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        raw_usage_final = (response_body or {}).get("usage") or {}
        fire_usage_log(
            owner=key.owner,
            provider=provider,
            key_id=str(key.id),
            request_id=sub_request_id,
            model=model,
            template_id=None,
            stream=False,
            prompt_tokens=raw_usage_final.get("prompt_tokens"),
            completion_tokens=raw_usage_final.get("completion_tokens"),
            cached_tokens=None,
            upstream_cost=raw_usage_final.get("cost"),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_str,
        )


async def run_comparison(
    *,
    comparison_model: str,
    original_messages: list[Message],
    results: list[ModelCompareResult],
    custom_instructions: str | None,
    key: ApiKey,
    db: AsyncSession,
    outer_request_id: str,
    comparison_id: str,
) -> tuple[str | None, TokenUsage | None, str | None, bool]:
    """
    Try the primary comparison model, then each fallback in order.

    Returns (text, usage, model_used, fallback_used).
    All four values are None/False when every model in the chain fails.
    """
    fallback_models = settings.compare_fallback_models_list
    # Deduplicate: skip fallbacks that duplicate the primary
    candidates = [comparison_model] + [m for m in fallback_models if m != comparison_model]

    comp_messages_raw = build_comparison_messages(original_messages, results, custom_instructions)
    comp_messages = [Message(**m) for m in comp_messages_raw]

    log = logger.bind(comparison_id=comparison_id, candidates=candidates)

    for attempt, model in enumerate(candidates):
        is_fallback = attempt > 0
        if is_fallback:
            log.warning(
                "compare_synthesis_fallback",
                attempt=attempt,
                model=model,
            )
        sub_request_id = (
            f"{outer_request_id}::comparison"
            if not is_fallback
            else f"{outer_request_id}::comparison_fallback_{attempt}"
        )
        result = await _attempt_comparison(
            model=model,
            comp_messages=comp_messages,
            key=key,
            db=db,
            sub_request_id=sub_request_id,
            comparison_id=comparison_id,
        )
        if result is not None:
            text, usage = result
            return text, usage, model, is_fallback

    log.error("compare_synthesis_all_failed", candidates=candidates)
    return None, None, None, False


async def _stream_single_model_into_queue(
    *,
    model: str,
    messages: list[Message],
    base_request: CompareRequest,
    override: ModelOverride | None,
    key: ApiKey,
    db: AsyncSession,
    outer_request_id: str,
    comparison_id: str,
    queue: asyncio.Queue,
) -> None:
    """
    Streams one model's output into `queue` as (model, chunk | None, error | None) tuples.

    Each token chunk: (model, bytes, None)
    Clean end sentinel: (model, None, None)
    Error sentinel:     (model, None, error_str)

    Fires fire_usage_log on completion, parsing SSE frames for usage data.
    """
    sub_request_id = f"{outer_request_id}::{model}"
    start = time.monotonic()
    provider = "unknown"
    status = "error"
    error_str: str | None = None
    error_code_str: str | None = None
    buf = b""
    usage_data: dict | None = None

    log = logger.bind(
        model=model,
        sub_request_id=sub_request_id,
        comparison_id=comparison_id,
        key_owner=key.owner,
    )

    try:
        provider, provider_model_id, _ = await resolve_routing(model, db)
        upstream_key = await resolve_upstream_key(owner=key.owner, provider=provider, db=db)
        adapter = get_adapter(provider)

        temperature = (override.temperature if override else None) or base_request.temperature
        max_tokens = (override.max_tokens if override else None) or base_request.max_tokens

        msg_dicts: list[dict] = []
        if override and override.system_prompt:
            msg_dicts.append({"role": "system", "content": override.system_prompt})
        msg_dicts.extend(m.model_dump() for m in messages)

        chat_req = ChatCompletionRequest(
            model=model,
            messages=[Message(**d) for d in msg_dicts],
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async def _do_stream() -> None:
            nonlocal buf, usage_data
            async for chunk in adapter.stream_chat_completion(
                chat_req,
                api_key=upstream_key,
                owner=key.owner,
                provider_model_id=provider_model_id,
            ):
                buf += chunk
                while b"\n\n" in buf:
                    frame, buf = buf.split(b"\n\n", 1)
                    parsed = parse_sse_frame(frame)
                    if parsed is not None:
                        if parsed.get("usage"):
                            usage_data = parsed["usage"]
                        await queue.put((model, parsed, None))

        await asyncio.wait_for(_do_stream(), timeout=settings.compare_model_timeout_s)

        status = "success"
        log.info("compare_stream_model_success", latency_ms=int((time.monotonic() - start) * 1000))

    except TimeoutError:
        error_str = f"Model '{model}' timed out after {int(settings.compare_model_timeout_s)}s."
        error_code_str = "gateway_timeout"
        log.warning("compare_stream_model_timeout", timeout_s=settings.compare_model_timeout_s)

    except UnsupportedModelError:
        error_str = f"Model '{model}' is not supported or has no pricing entry."
        error_code_str = "model_not_found"
        log.warning("compare_stream_model_unsupported")

    except Exception as exc:
        error_str = getattr(exc, "message", str(exc)) or type(exc).__name__
        error_code_str = getattr(exc, "error_code", "upstream_error")
        log.warning(
            "compare_stream_model_error",
            error_type=type(exc).__name__,
            error_repr=repr(exc),
        )

    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        # drain any remaining partial frame from the buffer for usage
        if buf:
            usage_data, _ = scan_sse_buf(buf + b"\n\n", usage_data)
        fire_usage_log(
            owner=key.owner,
            provider=provider,
            key_id=str(key.id),
            request_id=sub_request_id,
            model=model,
            template_id=None,
            stream=True,
            prompt_tokens=(usage_data or {}).get("prompt_tokens"),
            completion_tokens=(usage_data or {}).get("completion_tokens"),
            cached_tokens=None,
            upstream_cost=(usage_data or {}).get("cost"),
            latency_ms=latency_ms,
            status=status,
            error_code=error_code_str,
        )
        await queue.put((model, None, error_str))
