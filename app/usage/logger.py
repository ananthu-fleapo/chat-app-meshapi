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


async def _our_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal | None:
    """
    Resolve cost using our model_prices table (what we charge the user).

    Uses _lookup_model_price which handles the ':free' suffix abuse vector —
    if a paid model was sent with a fake ':free' suffix it still gets billed
    at the paid rate.

    Falls back to static pricing table, then None.
    """
    try:
        from app.usage.balance import _lookup_model_price
        async with get_session_factory()() as session:
            row = await _lookup_model_price(model, session)

        if row is not None:
            if row.is_free:
                return Decimal("0")
            prompt_cost = Decimal(str(row.prompt_usd_per_1k)) * prompt_tokens / 1000
            completion_cost = Decimal(str(row.completion_usd_per_1k)) * completion_tokens / 1000
            return (prompt_cost + completion_cost).quantize(Decimal("0.00000001"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("our_cost_lookup_failed", model=model, error=str(exc))

    # Static table fallback
    return calculate_cost(model, prompt_tokens, completion_tokens)


async def log_usage_event(
    *,
    key_id: str,
    owner: str,
    request_id: str,
    model: str,
    template_id: str | None,
    stream: bool,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_tokens: int | None = None,
    upstream_cost: float | None = None,   # usage.cost from OpenRouter — stored for reconciliation, not used for billing
    latency_ms: int,
    status: str,                           # "success" | "error"
    error_code: str | None = None,
) -> None:
    cost: Decimal | None = None
    total_tokens: int | None = None

    if prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    # ── Cost resolution — use our model_prices (what we charge the user) ──────
    # Falls back to static table, then None.
    if prompt_tokens is not None and completion_tokens is not None:
        cost = await _our_cost(model, prompt_tokens, completion_tokens)

    # ── Apply discount if one is active for this owner + model ───────────────
    if cost is not None and cost > 0:
        try:
            async with get_session_factory()() as _disc_session:
                from app.usage.balance import get_active_discount
                discount_pct = await get_active_discount(owner, model, _disc_session)
            if discount_pct:
                cost = (cost * (1 - discount_pct / 100)).quantize(Decimal("0.00000001"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("discount_lookup_failed", owner=owner, model=model, error=str(exc))

    try:
        upstream_cost_decimal = Decimal(str(upstream_cost)).quantize(Decimal("0.00000001")) if upstream_cost is not None else None

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
                upstream_cost_usd=upstream_cost_decimal,
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
            upstream_cost_usd=str(upstream_cost_decimal) if upstream_cost_decimal is not None else None,
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
        return

    # ── Prometheus metrics ────────────────────────────────────────────────────
    try:
        from app.metrics import record_inference
        record_inference(
            model=model,
            status=status,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=float(cost) if cost is not None else None,
        )
    except Exception:  # noqa: BLE001
        pass  # metrics must never affect the response path

    # ── Deduct from user balance (post-deduction model) ───────────────────────
    # Only deduct on success with a known cost. Errors are not billed.
    if status == "success" and cost is not None and cost > 0:
        from app.usage.balance import deduct_balance
        await deduct_balance(owner, cost)


def fire_usage_log(*, owner: str, **kwargs) -> None:
    """
    Schedule log_usage_event as a fire-and-forget background task.
    Safe to call from inside async generators and route handlers.
    """
    asyncio.create_task(log_usage_event(owner=owner, **kwargs))
