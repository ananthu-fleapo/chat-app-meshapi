"""
OpenAI image generation handler.

Calls POST /v1/images/generations and normalises the result to
list[ImageGeneratedItem].  Reuses the singleton httpx client from
OpenAIDirectAdapter so we don't open extra connections.
"""

from __future__ import annotations

import structlog

from app.exceptions import _classify_openai_error
from app.providers.response_formatter import ImageGeneratedItem, ImageGenerationResult
from app.schemas.chat import ImageOptions

logger = structlog.get_logger()


async def generate(
    prompt: str,
    *,
    provider_model_id: str,
    opts: ImageOptions,
    api_key: str | None,
) -> ImageGenerationResult:
    """
    Call OpenAI /v1/images/generations and return normalised results.

    Raises UpstreamError (via _classify_openai_error) on non-2xx responses.
    """
    from app.providers.openai_direct import OpenAIDirectAdapter

    adapter = OpenAIDirectAdapter.get()
    log = logger.bind(provider_model_id=provider_model_id, n=opts.n)

    # dall-e-2 / dall-e-3 accept response_format; newer models (gpt-image-*) do not
    _legacy_dalle = provider_model_id.startswith("dall-e")

    payload: dict = {
        "model": provider_model_id,
        "prompt": prompt,
        "n": opts.n,
        "size": opts.size,
        "quality": opts.quality,
    }
    if _legacy_dalle:
        payload["response_format"] = opts.response_format

    log.debug("openai_image_generate_request", size=opts.size, quality=opts.quality)

    response = await adapter._client.post(
        "/images/generations",
        json=payload,
        headers=adapter._auth_headers(api_key),
    )

    if response.status_code >= 400:
        raw = response.text[:500]
        try:
            err = response.json().get("error") or {}
        except Exception:  # noqa: BLE001
            err = {}
        level = "error" if response.status_code >= 500 else "warning"
        log.msg(
            "openai_image_http_error",
            _level=level,
            status=response.status_code,
            error_type=err.get("type"),
            error_code=err.get("code"),
            error_message=err.get("message"),
            body=raw,
        )
        _classify_openai_error(response.status_code, raw)

    body = response.json()
    data: list[dict] = body.get("data", [])
    usage: dict = body.get("usage", {})
    log.info(
        "openai_image_generate_ok",
        count=len(data),
        usage=usage,
        top_level_keys=list(body.keys()),
    )

    return ImageGenerationResult(
        items=[
            ImageGeneratedItem(url=item.get("url"), b64_json=item.get("b64_json")) for item in data
        ],
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        total_tokens=usage.get("total_tokens"),
    )
