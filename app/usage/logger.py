"""
Usage event logger.

Design principles
-----------------
1. Never blocks the request path — always called via asyncio.create_task().
2. Opens its own DB session — the request session is already closed by the
   time the background task runs (especially for streaming responses).
3. Silently swallows all errors — usage logging must never take the API down.
   Failed events are logged at ERROR level for manual recovery if needed.

Cost resolution (Phase 6 update)
---------------------------------
The primary cost source is now ``upstream_cost`` — the ``usage.cost`` field
returned directly by OpenRouter in every response.  This is the actual USD
amount charged, including any cache discounts or surcharges applied by the
upstream provider.

The static pricing table (``app/usage/pricing.py``) is kept as a fallback
for cases where the upstream omits the cost field (older model versions or
non-OpenRouter adapters).

fire_usage_log(**kwargs)
    The only call-site function. Schedules log_usage_event() as a background
    task in the running event loop.

log_usage_event(**kwargs)
    Async coroutine: resolves cost, writes one UsageEvent row, commits.
"""

import asyncio
import uuid
from decimal import Decimal, InvalidOperation

import structlog

from app.db.engine import get_session_factory
from app.db.models import UsageEvent
from app.usage.pricing import calculate_cost

logger = structlog.get_logger()


async def log_usage_event(
    *,
    key_id: str,
    request_id: str,
    model: str,
    template_id: str | None,
    stream: bool,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_tokens: int | None = None,
    upstream_cost: float | None = None,   # usage.cost from upstream response
    latency_ms: int,
    status: str,                           # "success" | "error"
    error_code: str | None = None,
) -> None:
    cost: Decimal | None = None
    total_tokens: int | None = None

    if prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    # ── Cost resolution ───────────────────────────────────────────────────────
    # 1. Use upstream_cost (usage.cost) — actual charged amount from OpenRouter.
    # 2. Fall back to static pricing table for unknown models / other adapters.
    if upstream_cost is not None:
        try:
            cost = Decimal(str(upstream_cost)).quantize(Decimal("0.00000001"))
        except (InvalidOperation, ValueError):
            pass

    if cost is None and prompt_tokens is not None and completion_tokens is not None:
        cost = calculate_cost(model, prompt_tokens, completion_tokens)

    try:
        async with get_session_factory()() as session:
            event = UsageEvent(
                key_id=uuid.UUID(key_id),
                request_id=request_id,
                model=model,
                template_id=uuid.UUID(template_id) if template_id else None,
                stream=stream,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cached_tokens=cached_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                status=status,
                error_code=error_code,
            )
            session.add(event)
            await session.commit()

        logger.debug(
            "usage_logged",
            key_id=key_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached_tokens,
            cost_usd=str(cost) if cost is not None else None,
            latency_ms=latency_ms,
            status=status,
        )

    except Exception as exc:
        # Must never propagate — a DB blip should not affect response delivery.
        logger.error(
            "usage_log_failed",
            error=str(exc),
            key_id=key_id,
            request_id=request_id,
            model=model,
        )


def fire_usage_log(**kwargs) -> None:
    """
    Schedule log_usage_event as a fire-and-forget background task.
    Safe to call from inside async generators and route handlers.
    """
    asyncio.create_task(log_usage_event(**kwargs))
