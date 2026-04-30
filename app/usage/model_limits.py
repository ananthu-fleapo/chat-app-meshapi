"""
Model-level access control and per-model usage cap enforcement.

Two concerns:

check_allowed_models()  — synchronous, no DB hit. Raises ForbiddenError (403)
                          if the resolved model is not in key.allowed_models.
                          No-op when allowed_models is None (unrestricted).

check_model_limits()    — async DB aggregate. For each cap in key.model_limits
                          for the resolved model, sums usage_events for
                          (key_id, model) and raises PaymentRequiredError (402)
                          if any cap is reached.

Soft-cap model: checked before the request, same as spend_cap. Can overshoot
by at most one request's worth, which is acceptable for LLM workloads.

model_limits JSONB schema (per model entry):
  max_cost_usd     — lifetime cost cap for this (key, model) pair
  max_tokens       — lifetime total_tokens cap
  max_requests     — lifetime request count cap
"""

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsageEvent
from app.exceptions import ForbiddenError, PaymentRequiredError

logger = structlog.get_logger()


def check_allowed_models(model: str, allowed_models: list[str] | None) -> None:
    """Raise ForbiddenError (403) if model is not in the allowed list."""
    if allowed_models is None:
        return
    if model not in allowed_models:
        raise ForbiddenError(
            f"Model '{model}' is not permitted for this API key."
        )


async def check_model_limits(
    key_id: str,
    model: str,
    model_limits: dict | None,
    db: AsyncSession,
) -> None:
    """Raise PaymentRequiredError (402) if any per-model cap is reached."""
    if not model_limits:
        return

    limits = model_limits.get(model)
    if not limits:
        return

    max_cost = limits.get("max_cost_usd")
    max_tokens = limits.get("max_tokens")
    max_requests = limits.get("max_requests")

    if max_cost is None and max_tokens is None and max_requests is None:
        return

    result = await db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("total_tokens"),
            func.count(UsageEvent.id).label("total_requests"),
        ).where(
            UsageEvent.key_id == uuid.UUID(key_id),
            UsageEvent.model == model,
        )
    )
    row = result.one()

    logger.debug(
        "model_limits_check",
        key_id=key_id,
        model=model,
        total_cost=str(row.total_cost),
        total_tokens=row.total_tokens,
        total_requests=row.total_requests,
    )

    if max_cost is not None and Decimal(str(row.total_cost)) >= Decimal(str(max_cost)):
        raise PaymentRequiredError(
            f"Cost cap of ${max_cost} for model '{model}' reached. "
            f"Current spend: ${row.total_cost:.6f}."
        )
    if max_tokens is not None and row.total_tokens >= max_tokens:
        raise PaymentRequiredError(
            f"Token cap of {max_tokens:,} for model '{model}' reached. "
            f"Current usage: {row.total_tokens:,} tokens."
        )
    if max_requests is not None and row.total_requests >= max_requests:
        raise PaymentRequiredError(
            f"Request cap of {max_requests:,} for model '{model}' reached. "
            f"Current count: {row.total_requests:,} requests."
        )
