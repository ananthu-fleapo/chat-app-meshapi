"""
Provider-agnostic image generation dispatcher.

Callers import generate_images() and _SUPPORTED_PROVIDERS.  The dispatcher
routes to the correct provider-specific handler; unsupported providers get a
501 before any network call is made.
"""

from __future__ import annotations

from app.providers import image_handler_openai, image_handler_vertex
from app.providers.response_formatter import ImageGeneratedItem
from app.schemas.chat import ImageOptions

_SUPPORTED_PROVIDERS: frozenset[str] = frozenset({"openai", "vertex"})


async def generate_images(
    prompt: str,
    *,
    provider: str,
    provider_model_id: str,
    opts: ImageOptions,
    api_key: str | None,
) -> list[ImageGeneratedItem]:
    """
    Dispatch image generation to the correct provider handler.

    Raises HTTPException(501) for unsupported providers.
    Raises UpstreamError on provider-side failures.
    """
    from fastapi import HTTPException

    if provider == "openai":
        return await image_handler_openai.generate(
            prompt,
            provider_model_id=provider_model_id,
            opts=opts,
            api_key=api_key,
        )
    if provider == "vertex":
        return await image_handler_vertex.generate(
            prompt,
            provider_model_id=provider_model_id,
            opts=opts,
            api_key=api_key,
        )
    raise HTTPException(
        status_code=501,
        detail=f"Image generation is not supported for provider '{provider}'",
    )
