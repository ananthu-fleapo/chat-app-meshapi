"""
Model → adapter routing registry.

Phase 1: all models route to OpenRouter (single upstream).
OpenRouter accepts both OpenRouter-namespaced strings ("openai/gpt-4o") and
plain OpenAI-style strings ("gpt-4o"), so we pass them through as-is.

Phase 6+: this table moves to Postgres so new models/providers can be added
without a redeploy. For now, a prefix-match table is sufficient.
"""

import structlog

from app.exceptions import UnsupportedModelError
from app.providers.base import ProviderAdapter
from app.providers.openrouter import OpenRouterAdapter

logger = structlog.get_logger()

# All known model prefixes that OpenRouter supports.
# Order matters: more specific prefixes should come first.
_OPENROUTER_PREFIXES: tuple[str, ...] = (
    # Namespaced (OpenRouter canonical form)
    "openai/",
    "anthropic/",
    "google/",
    "meta-llama/",
    "mistralai/",
    "cohere/",
    "perplexity/",
    "deepseek/",
    "qwen/",
    # Plain (OpenAI-compatible shorthand — OpenRouter also accepts these)
    "gpt-",
    "o1",
    "o3",
    "claude-",
    "gemini-",
    "mistral-",
    "llama",
    "command-",
    "sonar-",
)


def get_adapter(model: str) -> ProviderAdapter:
    """
    Resolve a model string to its provider adapter.
    Raises UnsupportedModelError if no adapter matches.
    """
    for prefix in _OPENROUTER_PREFIXES:
        if model.startswith(prefix):
            return OpenRouterAdapter.get()

    # Default: attempt OpenRouter for unknown/future models rather than hard-failing.
    # OpenRouter will return a 404 if it doesn't know the model, which propagates
    # as an UpstreamError with a clear message.
    logger.debug("unknown_model_prefix_fallback_openrouter", model=model)
    return OpenRouterAdapter.get()
