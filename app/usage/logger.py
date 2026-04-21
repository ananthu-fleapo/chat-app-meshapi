"""
Usage event logger.

Design principles
-----------------
1. Never blocks the request path — always called via asyncio.create_task().
2. Opens its own DB session — the request session is already closed by the
   time the background task runs (especially for streaming responses).
3. Postgres write is best-effort — failure is caught, logged, and does NOT
   block MongoDB write or balance deduction.
4. MongoDB is always written — immune to schema migrations. Provides a
   durable fallback when Postgres is unavailable or schema is behind.
5. Balance deduction is always attempted — NOT gated on Postgres success.
   Failures are logged to MongoDB balance_failures for manual recovery.

Cost resolution
---------------
Primary:  upstream_cost from the provider's response (OpenRouter reports cost directly).
Fallback: our model_prices table (upstream_*_usd_per_1k) for providers that don't
          report cost (Vertex AI, Bedrock, OpenAI Direct, Qwen).
Last:     static pricing table in app/usage/pricing.py.

fire_usage_log(**kwargs)
    The only call-site function. Schedules log_usage_event() as a background
    task in the running event loop.

log_usage_event(**kwargs)
    Async coroutine:
      1. Resolves cost (our price to user).
      2. Writes to Postgres usage_events (best-effort).
      3. Always writes to MongoDB usage_events.
      4. Always attempts balance deduction; logs failures to MongoDB.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import structlog
from app.db.engine import get_session_factory
from app.db.models import UsageEvent
from app.usage.pricing import calculate_cost

logger = structlog.get_logger()


async def _calc_upstream_cost(
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int = 0,
) -> Decimal | None:
    """
    Calculate upstream cost from model_prices.upstream_*_usd_per_1k.

    Used for providers that don't report cost in their API response
    (Vertex AI, Bedrock, OpenAI Direct, Qwen).  Returns None when upstream
    pricing is not configured for this (model, provider) pair.
    """
    try:
        from app.db.models import ModelPrice
        from sqlalchemy import select
        async with get_session_factory()() as session:
            result = await session.execute(
                select(ModelPrice).where(
                    ModelPrice.model_id == model,
                    ModelPrice.provider == provider,
                )
            )
            row = result.scalar_one_or_none()

        if row is None or row.upstream_prompt_usd_per_1k is None:
            return None

        prompt_cost = Decimal(str(row.upstream_prompt_usd_per_1k)) * prompt_tokens / 1000
        # Embedding models have no completion rate; treat missing/zero as 0 so
        # prompt-only cost still resolves rather than returning None.
        completion_rate = Decimal(str(row.upstream_completion_usd_per_1k or 0))
        completion_cost = completion_rate * completion_tokens / 1000
        return (prompt_cost + completion_cost).quantize(Decimal("0.00000001"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("upstream_cost_calc_failed", model=model, provider=provider, error=str(exc))
        return None


async def _our_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int = 0,
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
            completion_cost = Decimal(str(row.completion_usd_per_1k or 0)) * completion_tokens / 1000
            return (prompt_cost + completion_cost).quantize(Decimal("0.00000001"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("our_cost_lookup_failed", model=model, error=str(exc))

    # Static table fallback
    return calculate_cost(model, prompt_tokens, completion_tokens)


async def _deduct_with_fallback(
    *,
    owner: str,
    model: str,
    cost: Decimal,
    request_id: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    provider: str,
    status: str,
) -> None:
    """
    Attempt balance deduction. On failure, persist to MongoDB balance_failures
    so the unbilled amount can be identified and replayed manually.

    Never raises — deduction failure must not affect the response or caller.
    """
    from app.usage.balance import deduct_balance
    try:
        await deduct_balance(owner, cost)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "balance_deduction_failed",
            owner=owner,
            model=model,
            cost_usd=str(cost),
            request_id=request_id,
            error=str(exc),
        )
        # Persist to MongoDB so ops can replay the deduction
        try:
            from app.db.mongo import get_mongo_db, is_mongo_available
            if is_mongo_available():
                await get_mongo_db().balance_failures.insert_one({
                    "ts": datetime.now(UTC),
                    "owner": owner,
                    "model": model,
                    "provider": provider,
                    "cost_usd": float(cost),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "request_id": request_id,
                    "status": status,
                    "error": str(exc),
                    "replayed": False,
                })
        except Exception as mongo_exc:  # noqa: BLE001
            # Both Postgres and Mongo failed — structured log is the last resort
            logger.error(
                "balance_failure_log_mongo_failed",
                owner=owner,
                cost_usd=str(cost),
                request_id=request_id,
                error=str(mongo_exc),
            )


async def log_usage_event(
    *,
    key_id: str,
    owner: str,
    request_id: str,
    model: str,
    provider: str = "openrouter",
    template_id: str | None,
    stream: bool,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_tokens: int | None = None,
    upstream_cost: float | None = None,   # usage.cost from OpenRouter — reconciliation only
    latency_ms: int,
    status: str,                           # "success" | "error"
    error_code: str | None = None,
) -> None:
    cost: Decimal | None = None
    total_tokens: int | None = None

    if prompt_tokens is not None:
        total_tokens = prompt_tokens + (completion_tokens or 0)

    # ── Cost resolution — use our model_prices (what we charge the user) ──────
    if prompt_tokens is not None:
        cost = await _our_cost(model, prompt_tokens, completion_tokens or 0)

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

    # ── Upstream cost (for reconciliation, not billing) ───────────────────────
    upstream_cost_decimal: Decimal | None
    if upstream_cost is not None:
        upstream_cost_decimal = Decimal(str(upstream_cost)).quantize(Decimal("0.00000001"))
    elif prompt_tokens is not None:
        upstream_cost_decimal = await _calc_upstream_cost(
            model,
            provider,
            prompt_tokens,
            completion_tokens or 0,
        )
    else:
        upstream_cost_decimal = None

    # ── 1. Postgres write (best-effort) ───────────────────────────────────────
    postgres_ok = False
    try:
        async with get_session_factory()() as session:
            event = UsageEvent(
                key_id=uuid.UUID(key_id),
                user_id=owner,
                request_id=request_id,
                model=model,
                provider=provider,
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
        postgres_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "usage_log_postgres_failed",
            error=str(exc),
            key_id=key_id,
            request_id=request_id,
            model=model,
            cost_usd=str(cost) if cost is not None else None,
        )

    # ── 2. MongoDB write (always, regardless of Postgres result) ──────────────
    try:
        from app.db.mongo import get_mongo_db, is_mongo_available
        if is_mongo_available():
            await get_mongo_db().usage_events.insert_one({
                "_id": request_id,
                "ts": datetime.now(UTC),
                "key_id": key_id,
                "owner": owner,
                "model": model,
                "provider": provider,
                "template_id": template_id,
                "stream": stream,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "cost_usd": float(cost) if cost is not None else None,
                "upstream_cost_usd": float(upstream_cost_decimal) if upstream_cost_decimal is not None else None,
                "latency_ms": latency_ms,
                "status": status,
                "error_code": error_code,
                "postgres_written": postgres_ok,
            })
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "usage_log_mongo_failed",
            error=str(exc),
            request_id=request_id,
            model=model,
        )

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
        postgres_ok=postgres_ok,
    )

    # ── 3. Prometheus metrics ─────────────────────────────────────────────────
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

    # ── 4. Balance deduction (always attempted, independent of Postgres) ──────
    # Deduction is skipped for: errors, zero-cost, free models (cost == 0).
    # On failure: logged to MongoDB balance_failures for manual recovery.
    if status == "success" and cost is not None and cost > 0:
        await _deduct_with_fallback(
            owner=owner,
            model=model,
            cost=cost,
            request_id=request_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            provider=provider,
            status=status,
        )
    else:
        logger.warning("balance_deduction_skipped", status=status, cost=cost)


def fire_usage_log(*, owner: str, provider: str = "openrouter", **kwargs) -> None:
    """
    Schedule log_usage_event as a fire-and-forget background task.
    Safe to call from inside async generators and route handlers.
    """
    asyncio.create_task(log_usage_event(owner=owner, provider=provider, **kwargs))
