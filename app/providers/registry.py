"""
Provider routing registry.

Resolves which upstream adapter to use based on the provider slug stored
in model_prices.provider.  The model_prices table is the single source of
truth for provider selection — change the provider column (and flip is_default)
to route a model to a different upstream without any code changes.

resolve_provider(model, db)
    Queries model_prices for the row where (model_id=model, is_default=True).
    Falls back to any row for that model_id, then to "openrouter" if not found.

get_adapter(provider)
    Returns the singleton ProviderAdapter for the given provider slug.
    Raises UnsupportedModelError for unknown provider names.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import UnsupportedModelError
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
        raise UnsupportedModelError(
            f"No adapter registered for provider '{provider}'. "
            "Check that the required credentials are configured."
        )
    return cls.get()


async def resolve_provider(model: str, db: AsyncSession) -> str:
    """
    Return the provider slug to use for *model*.

    Lookup order:
      1. Row where (model_id=model, is_default=True)   — explicit default
      2. Any row where model_id=model                  — first available
      3. "openrouter"                                   — safe fallback

    Parameters
    ----------
    model : str
        Canonical RouterV model identifier (e.g. "openai/gpt-4o-mini").
    db : AsyncSession
        Active DB session from the request lifecycle.

    Returns
    -------
    str
        Provider slug, e.g. "openrouter", "vertex", "bedrock", "openai".
    """
    from app.db.models import ModelPrice

    # Prefer the is_default row
    result = await db.execute(
        select(ModelPrice.provider)
        .where(
            ModelPrice.model_id == model,
            ModelPrice.is_default.is_(True),
        )
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    # Fall back to any row for this model
    result = await db.execute(
        select(ModelPrice.provider)
        .where(ModelPrice.model_id == model)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        logger.debug(
            "provider_resolved_no_default",
            model=model,
            provider=row,
        )
        return row

    # Model not in price table — default to OpenRouter
    logger.debug("provider_resolved_fallback_openrouter", model=model)
    return "openrouter"
