"""
Provider routing registry.

Resolves which upstream adapter to use based on the provider slug stored
in model_prices.provider.  The model_prices table is the single source of
truth for provider selection — change the provider column (and flip is_default)
to route a model to a different upstream without any code changes.

resolve_routing(model, db)
    Queries model_prices for the is_default row and returns both the provider
    slug AND the stored provider_model_id in a single DB round-trip.
    Falls back to ("openrouter", None) if the model has no price row.

resolve_provider(model, db)
    Thin wrapper around resolve_routing — returns only the provider slug.
    Kept for backward-compatibility.

get_adapter(provider)
    Returns the singleton ProviderAdapter for the given provider slug.
    Raises ProviderNotAvailableError for unknown provider names.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ProviderNotAvailableError
from app.providers.base import ProviderAdapter
from app.providers.openrouter import OpenRouterAdapter

logger = structlog.get_logger()

# Populated at startup by main.py as adapters are initialised.
# Only adapters whose credentials are configured will be registered.
_REGISTRY: dict[str, type[ProviderAdapter]] = {
    "openrouter": OpenRouterAdapter,
}


def register_adapter(provider: str, cls: type[ProviderAdapter]) -> None:
    """Register an adapter class under the given provider slug."""
    _REGISTRY[provider] = cls
    logger.info("provider_registered", provider=provider)


def get_adapter(provider: str) -> ProviderAdapter:
    """
    Return the singleton ProviderAdapter for *provider*.

    Raises UnsupportedModelError if no adapter is registered for this provider.
    """
    cls = _REGISTRY.get(provider)
    if cls is None:
        raise ProviderNotAvailableError(provider)
    return cls.get()


async def resolve_routing(
    model: str, db: AsyncSession
) -> tuple[str, str | None]:
    """
    Return (provider, provider_model_id) for *model* in a single DB query.

    provider_model_id is the exact upstream model ID stored in
    model_prices.provider_model_id (e.g. "us.anthropic.claude-3-haiku-20240307-v1:0").
    It is None when the column is unset — adapters fall back to their internal
    _MODEL_MAP translation in that case.

    Lookup order:
      1. Row where (model_id=model, is_default=True)   — explicit default
      2. Any row where model_id=model                  — first available
      3. ("openrouter", None)                          — safe fallback
    """
    from app.db.models import ModelPrice

    # Prefer the is_default row; fetch both columns in one round-trip
    result = await db.execute(
        select(ModelPrice.provider, ModelPrice.provider_model_id)
        .where(
            ModelPrice.model_id == model,
            ModelPrice.is_default.is_(True),
        )
        .limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        return row.provider, row.provider_model_id

    # Fall back to any row for this model
    result = await db.execute(
        select(ModelPrice.provider, ModelPrice.provider_model_id)
        .where(ModelPrice.model_id == model)
        .limit(1)
    )
    row = result.one_or_none()
    if row is not None:
        logger.debug(
            "provider_resolved_no_default",
            model=model,
            provider=row.provider,
        )
        return row.provider, row.provider_model_id

    # Model not in price table — default to OpenRouter
    logger.debug("provider_resolved_fallback_openrouter", model=model)
    return "openrouter", None


async def resolve_provider(model: str, db: AsyncSession) -> str:
    """
    Return the provider slug for *model*.
    Thin wrapper around resolve_routing kept for backward-compatibility.
    """
    provider, _ = await resolve_routing(model, db)
    return provider
